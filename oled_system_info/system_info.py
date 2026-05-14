#!/usr/bin/env python3
"""
OLED System Info Display
Displays system information on SSD1306 OLED
Uses smbus2 for container compatibility
"""

import time
import subprocess
import os
from collections import deque
from smbus2 import SMBus, i2c_msg
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
import psutil
import requests


API_CACHE = {}
PAGE_TRANSITION_STEPS = 4
PAGE_TRANSITION_DELAY = 0.03


def get_env_int(name, default, minimum=None, maximum=None):
    """Read an integer from the environment with bounds."""
    value = os.getenv(name, str(default))
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default

    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def get_env_bool(name, default):
    """Read a boolean from the environment."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def get_env_choice(name, default, allowed_values):
    """Read a string option from the environment with validation."""
    value = os.getenv(name, default)
    normalized = str(value).strip().lower()
    if normalized in allowed_values:
        return normalized
    return default


def get_env_csv(name):
    """Read a comma-separated list from the environment."""
    value = os.getenv(name, '')
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


def get_env_clock_minutes(name, default):
    """Read a HH:MM value from the environment as minutes since midnight."""
    value = os.getenv(name, default)
    try:
        hours_text, minutes_text = value.split(':', 1)
        hours = int(hours_text)
        minutes = int(minutes_text)
        if 0 <= hours <= 23 and 0 <= minutes <= 59:
            return (hours * 60) + minutes
    except (AttributeError, TypeError, ValueError):
        pass

    default_hours, default_minutes = default.split(':', 1)
    return (int(default_hours) * 60) + int(default_minutes)


def log(message):
    """Print log message with timestamp"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def supervisor_api(endpoint, cache_ttl=0):
    """Call Home Assistant Supervisor API"""
    now = time.monotonic()
    cached = API_CACHE.get(endpoint)
    if cache_ttl > 0 and cached and now < cached['expires_at']:
        return cached['value']

    try:
        response = requests.get(
            f'http://supervisor/{endpoint}',
            headers={'Authorization': f'Bearer {os.getenv("SUPERVISOR_TOKEN")}'},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if cache_ttl > 0:
                API_CACHE[endpoint] = {
                    'expires_at': now + cache_ttl,
                    'value': data,
                }
            return data
    except Exception as e:
        log(f"API Error ({endpoint}): {e}")

    if cache_ttl > 0 and cached:
        return cached['value']
    return None


class I2CAdapter:
    """SMBus adapter for Adafruit CircuitPython libraries"""
    
    def __init__(self, bus_number=1):
        self.bus = SMBus(bus_number)
        self._locked = False
    
    def try_lock(self):
        if not self._locked:
            self._locked = True
            return True
        return False
    
    def unlock(self):
        self._locked = False
    
    def writeto(self, address, buffer, *, start=0, end=None):
        if end is None:
            end = len(buffer)
        
        length = end - start
        if length == 0:
            try:
                self.bus.read_byte(address)
            except:
                pass
            return
        
        data = bytes(buffer[start:end])
        msg = i2c_msg.write(address, data)
        self.bus.i2c_rdwr(msg)
    
    def readfrom_into(self, address, buffer, *, start=0, end=None):
        if end is None:
            end = len(buffer)
        
        length = end - start
        msg = i2c_msg.read(address, length)
        self.bus.i2c_rdwr(msg)
        
        for i, byte in enumerate(msg):
            buffer[start + i] = byte


def get_temperature(os_info):
    """Retrieve host temperature with multiple fallbacks."""
    try:
        if os_info and 'data' in os_info:
            temperature = os_info['data'].get('temperature')
            if temperature is not None:
                return f"{float(temperature):.0f}C"
    except Exception:
        pass

    try:
        temperatures = psutil.sensors_temperatures()
        for entries in temperatures.values():
            for entry in entries:
                current = getattr(entry, 'current', None)
                if current is not None:
                    return f"{current:.0f}C"
    except Exception:
        pass

    for path in (
        '/host/sys/class/thermal/thermal_zone0/temp',
        '/sys/class/thermal/thermal_zone0/temp',
    ):
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as temp_file:
                    value = temp_file.read().strip()
                if value:
                    return f"{int(value) / 1000:.0f}C"
        except Exception:
            pass

    return "N/A"


def get_disk_usage():
    """Retrieve disk usage percentage, preferring mounted host storage."""
    for path in ('/host', '/data', '/'):
        try:
            if os.path.exists(path):
                return f"{psutil.disk_usage(path).percent:2.0f}"
        except Exception:
            pass

    return "N/A"


def get_uptime():
    """Return a compact uptime string."""
    try:
        uptime_seconds = max(0, int(time.time() - psutil.boot_time()))
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, _ = divmod(remainder, 60)
        if days > 0:
            return f"{days}d {hours:02}h"
        return f"{hours:02}h {minutes:02}m"
    except Exception:
        return "N/A"


def parse_metric_value(value):
    """Parse a numeric metric value from formatted text."""
    cleaned = ''.join(character for character in str(value) if character.isdigit() or character in '.-')
    if not cleaned or cleaned in {'-', '.', '-.'}:
        return None

    try:
        return float(cleaned)
    except ValueError:
        return None


def is_night_mode_active(enabled, start_minutes, end_minutes):
    """Return whether the current local time falls inside the configured quiet window."""
    if not enabled or start_minutes == end_minutes:
        return False

    now = time.localtime()
    current_minutes = (now.tm_hour * 60) + now.tm_min

    if start_minutes < end_minutes:
        return start_minutes <= current_minutes < end_minutes
    return current_minutes >= start_minutes or current_minutes < end_minutes


def fit_text(value, max_chars=21):
    """Trim text to fit the 128px wide display."""
    text = str(value)
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars - 1]}~"


def get_logical_page_name(page_name):
    """Collapse expanded page IDs to their logical page name."""
    return page_name.split(':', 1)[0]


def expand_page_name(page_name, entity_count):
    """Expand logical pages into concrete display pages."""
    if page_name != 'entities' or entity_count <= 0:
        return [page_name]

    page_count = max(1, (entity_count + 3) // 4)
    return [f"entities:{page_number}/{page_count}" for page_number in range(1, page_count + 1)]


def build_enabled_pages(page_order, show_details_page, show_clock_page, show_graph_page, entity_ids):
    """Build the final page list, preserving user order where valid."""
    available_pages = ['summary']
    if show_details_page:
        available_pages.append('details')
    if show_clock_page:
        available_pages.append('clock')
    if entity_ids:
        available_pages.append('entities')
    if show_graph_page:
        available_pages.append('graph')

    enabled_pages = []
    entity_count = len(entity_ids)
    selected_pages = set()
    for page in page_order:
        page_name = page.lower()
        if page_name in available_pages and page_name not in selected_pages:
            enabled_pages.extend(expand_page_name(page_name, entity_count))
            selected_pages.add(page_name)

    for page_name in available_pages:
        if page_name not in selected_pages:
            enabled_pages.extend(expand_page_name(page_name, entity_count))
            selected_pages.add(page_name)

    return enabled_pages


def draw_centered_text(draw, y, width, text, font, fill=255):
    """Draw centered text on the OLED."""
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    text_width = right - left
    x = max(0, (width - text_width) // 2)
    draw.text((x, y), text, font=font, fill=fill)


def draw_clock_header_icon(draw, x, y, fill):
    """Draw a compact clock icon in the page header."""
    draw.ellipse((x, y, x + 8, y + 8), outline=fill)
    draw.line((x + 4, y + 4, x + 4, y + 2), fill=fill)
    draw.line((x + 4, y + 4, x + 6, y + 5), fill=fill)


def draw_entities_header_icon(draw, x, y, fill):
    """Draw a compact entities icon in the page header."""
    draw.rectangle((x, y + 1, x + 3, y + 4), outline=fill)
    draw.rectangle((x + 5, y + 1, x + 8, y + 4), outline=fill)
    draw.rectangle((x + 2, y + 5, x + 6, y + 8), outline=fill)


def draw_page_header(draw, font, width, title, icon_name=None):
    """Draw a consistent filled page header with an optional icon."""
    draw.rectangle((0, 0, width - 1, 11), outline=255, fill=255)

    if icon_name == 'clock':
        draw_clock_header_icon(draw, 4, 1, fill=0)
    elif icon_name == 'entities':
        draw_entities_header_icon(draw, 4, 1, fill=0)

    draw_centered_text(draw, 2, width, title, font, fill=0)


def animate_page_transition(disp, previous_image, next_image, steps=PAGE_TRANSITION_STEPS, frame_delay=PAGE_TRANSITION_DELAY):
    """Animate a short dissolve transition between two OLED pages."""
    if previous_image is None or steps <= 1:
        disp.image(next_image)
        disp.show()
        return

    previous_pixels = previous_image.load()
    next_pixels = next_image.load()
    width, height = next_image.size

    for step in range(1, steps + 1):
        frame = Image.new("1", next_image.size)
        frame_pixels = frame.load()
        for y in range(height):
            for x in range(width):
                pattern = (x * 3 + y * 5) % steps
                frame_pixels[x, y] = next_pixels[x, y] if pattern < step else previous_pixels[x, y]

        disp.image(frame)
        disp.show()
        if step < steps:
            time.sleep(frame_delay)


def draw_cpu_graph(draw, history, width, height, cpu, mem, temp):
    """Render a cleaner CPU history line graph for the OLED."""
    draw.text((0, 0), fit_text(f"CPU {cpu}% MEM {mem}%"), fill=255)
    draw.text((0, 8), fit_text(f"TEMP {temp}"), fill=255)

    chart_left = 0
    chart_top = 18
    chart_right = width - 1
    chart_bottom = height - 1
    draw.rectangle((chart_left, chart_top, chart_right, chart_bottom), outline=255)

    inner_left = chart_left + 1
    inner_top = chart_top + 1
    inner_right = chart_right - 1
    inner_bottom = chart_bottom - 1
    inner_width = max(1, inner_right - inner_left + 1)
    inner_height = max(1, inner_bottom - inner_top + 1)

    # Draw dashed guide lines at 25%, 50%, and 75%.
    for percent in (25, 50, 75):
        y = inner_bottom - int((percent / 100) * (inner_height - 1))
        for x in range(inner_left, inner_right + 1, 4):
            draw.point((x, y), fill=255)

    if not history:
        draw.text((34, 36), "Collecting...", fill=255)
        return

    raw_values = [max(0, min(100, int(v))) for v in list(history)[-inner_width:]]

    # Smooth values to reduce jitter and make the trend easier to read.
    values = []
    for index in range(len(raw_values)):
        start = max(0, index - 2)
        window = raw_values[start:index + 1]
        values.append(sum(window) / len(window))

    start_x = inner_right - (len(values) - 1)
    points = []
    for index, value in enumerate(values):
        x = start_x + index
        y = inner_bottom - int((value / 100) * (inner_height - 1))
        points.append((x, y))

    for index in range(1, len(points)):
        x1, y1 = points[index - 1]
        x2, y2 = points[index]
        draw.line((x1, y1, x2, y2), fill=255)

    latest_x, latest_y = points[-1]
    draw.rectangle((latest_x - 1, latest_y - 1, latest_x + 1, latest_y + 1), fill=255)


def draw_entities_page(draw, font, entities, page_number, page_count):
    """Render configured Home Assistant entity states."""
    title = "ENTITIES"
    if page_count > 1:
        title = f"ENTITIES {page_number}/{page_count}"
    draw_page_header(draw, font, 128, title, icon_name='entities')

    if not entities:
        draw.text((0, 24), "No entities set", font=font, fill=255)
        draw.text((0, 36), "Configure entity_ids", font=font, fill=255)
        return

    start = (page_number - 1) * 4
    visible_entities = entities[start:start + 4]

    for index, entity in enumerate(visible_entities):
        line = fit_text(f"{entity['name']}: {entity['value']}", 21)
        draw.text((0, 12 + (index * 12)), line, font=font, fill=255)


def draw_alert_icon(draw, x, y, severity):
    """Draw a simple severity icon for the alert screen."""
    if severity == 'critical':
        points = [(x + 10, y), (x + 20, y + 10), (x + 10, y + 20), (x, y + 10)]
        draw.polygon(points, outline=255)
        draw.line((x + 10, y + 4, x + 10, y + 12), fill=255)
        draw.point((x + 10, y + 16), fill=255)
        return

    points = [(x + 10, y), (x + 20, y + 18), (x, y + 18)]
    draw.polygon(points, outline=255)
    draw.line((x + 10, y + 5, x + 10, y + 11), fill=255)
    draw.point((x + 10, y + 14), fill=255)


def draw_alert_page(draw, font, width, height, alerts):
    """Render a dedicated alert page when thresholds are exceeded."""
    highest_severity = 'critical' if any(alert['severity'] == 'critical' for alert in alerts) else 'warning'
    header_text = 'CRITICAL ALERT' if highest_severity == 'critical' else 'WARNING ALERT'
    primary_alert = alerts[0]
    extra_alerts = alerts[1:3]

    draw.rectangle((0, 0, width - 1, height - 1), outline=255, fill=0)
    draw.rectangle((0, 0, width - 1, 11), outline=255, fill=255)
    draw_centered_text(draw, 2, width, header_text, font, fill=0)

    draw_alert_icon(draw, 4, 16, highest_severity)
    draw.text((30, 16), fit_text(primary_alert['title'], 16), font=font, fill=255)
    draw.text((30, 28), fit_text(primary_alert['detail'], 16), font=font, fill=255)
    draw.line((2, 40, width - 3, 40), fill=255)

    for index, alert in enumerate(extra_alerts):
        prefix = '!!' if alert['severity'] == 'critical' else '! '
        draw.text((2, 44 + (index * 10)), fit_text(f"{prefix}{alert['title']}", 20), font=font, fill=255)

    if len(alerts) > 3:
        draw.text((2, height - 10), fit_text(f"+{len(alerts) - 3} more alerts", 20), font=font, fill=255)


def draw_startup_logo(draw, x, top, font):
    """Draw a compact Home Assistant-style ASCII logo for startup."""
    logo_lines = [
        "      /\\      ",
        "     /  \\     ",
        "    /----\\    ",
        "   / |  | \\   ",
        "  /  |  |  \\  ",
        " /___|__|___\\ ",
        "   HOME ASSIST ",
    ]

    for index, line in enumerate(logo_lines):
        draw.text((x, top + (index * 8)), line, font=font, fill=255)


def draw_clock_page(draw, font, width, uptime):
    """Render a dedicated date and time page."""
    now = time.localtime()
    time_text = time.strftime('%H:%M:%S', now)
    date_text = time.strftime('%a %d %b %Y', now)

    draw_page_header(draw, font, width, 'CLOCK', icon_name='clock')
    draw_centered_text(draw, 18, width, time_text, font, fill=255)
    draw_centered_text(draw, 32, width, date_text, font, fill=255)
    draw_centered_text(draw, 46, width, f"UP {uptime}", font, fill=255)


def get_custom_entities(entity_ids, cache_ttl):
    """Fetch configured Home Assistant entity states."""
    if not entity_ids:
        return []

    all_states = supervisor_api('core/api/states', cache_ttl=cache_ttl)
    states_by_id = {}
    if isinstance(all_states, list):
        states_by_id = {
            item.get('entity_id'): item
            for item in all_states
            if isinstance(item, dict) and item.get('entity_id')
        }

    entities = []
    for entity_id in entity_ids:
        entity_state = states_by_id.get(entity_id)
        if not isinstance(entity_state, dict):
            entities.append({
                'name': entity_id.split('.', 1)[-1].replace('_', ' '),
                'value': 'unavail',
            })
            continue

        attributes = entity_state.get('attributes', {})
        name = attributes.get('friendly_name') or entity_id.split('.', 1)[-1].replace('_', ' ')
        state = str(entity_state.get('state', 'unknown'))
        unit = attributes.get('unit_of_measurement') or ''

        if unit and state not in {'unknown', 'unavailable'}:
            value = f"{state}{unit}"
        else:
            value = state

        entities.append({
            'name': name,
            'value': value,
        })

    return entities


def build_alerts(info, cpu_threshold, temp_threshold, disk_threshold):
    """Build alert messages from the current system state."""
    alerts = []

    cpu_value = parse_metric_value(info['cpu'])
    temp_value = parse_metric_value(info['temp'])
    disk_value = parse_metric_value(info['disk'])

    if cpu_value is not None and cpu_value >= cpu_threshold:
        severity = 'critical' if cpu_value >= min(100, cpu_threshold + 5) else 'warning'
        alerts.append({
            'severity': severity,
            'title': 'CPU LOAD HIGH',
            'detail': f"{info['cpu']}% >= {cpu_threshold}%",
        })
    if temp_value is not None and temp_value >= temp_threshold:
        severity = 'critical' if temp_value >= temp_threshold + 5 else 'warning'
        alerts.append({
            'severity': severity,
            'title': 'TEMP HIGH',
            'detail': f"{info['temp']} >= {temp_threshold}C",
        })
    if disk_value is not None and disk_value >= disk_threshold:
        severity = 'critical' if disk_value >= min(100, disk_threshold + 5) else 'warning'
        alerts.append({
            'severity': severity,
            'title': 'DISK NEAR FULL',
            'detail': f"{info['disk']}% >= {disk_threshold}%",
        })
    if info['ip'] in {'0.0.0.0', '', 'N/A'}:
        alerts.append({
            'severity': 'warning',
            'title': 'IP UNAVAILABLE',
            'detail': 'No LAN address found',
        })
    if not info['supervisor_ok']:
        alerts.append({
            'severity': 'critical',
            'title': 'SUPERVISOR DOWN',
            'detail': 'API not responding',
        })

    alerts.sort(key=lambda alert: 0 if alert['severity'] == 'critical' else 1)

    return alerts


def get_system_info(entity_ids, entity_cache_ttl, supervisor_cache_ttl):
    """Retrieve HOST system information via Supervisor API"""
    # Get host info
    host_info = supervisor_api('host/info', cache_ttl=supervisor_cache_ttl)
    network_info = supervisor_api('network/info', cache_ttl=supervisor_cache_ttl)
    os_info = supervisor_api('os/info', cache_ttl=supervisor_cache_ttl)
    
    # Hostname
    if host_info and 'data' in host_info:
        hostname = host_info['data'].get('hostname', 'unknown')
    else:
        hostname = subprocess.check_output("hostname", shell=True).decode('UTF-8').strip()
    
    # IP address - try to get primary network interface
    ip = "0.0.0.0"
    if network_info and 'data' in network_info:
        interfaces = network_info['data'].get('interfaces', [])
        for iface in interfaces:
            if iface.get('primary', False) and iface.get('ipv4'):
                ip = iface['ipv4'].get('address', ['0.0.0.0'])[0].split('/')[0]
                break
        # Fallback to first interface with an IP
        if ip == "0.0.0.0":
            for iface in interfaces:
                if iface.get('ipv4') and iface['ipv4'].get('address'):
                    ip = iface['ipv4']['address'][0].split('/')[0]
                    if not ip.startswith('172.'):  # Skip docker networks
                        break
    
    if ip == "0.0.0.0":
        try:
            ip = subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True).decode('UTF-8').strip()
        except:
            pass
    
    # CPU and Memory - use host /proc if mounted, otherwise container stats
    try:
        # Try to read from host /proc
        if os.path.exists('/host/proc/stat'):
            # We'd need to parse /proc/stat manually - complex
            # For now, fall back to psutil on container
            cpu = f"{psutil.cpu_percent():3.0f}"
        else:
            cpu = f"{psutil.cpu_percent():3.0f}"
    except:
        cpu = "N/A"
    
    try:
        # Try to read from host /proc/meminfo
        if os.path.exists('/host/proc/meminfo'):
            with open('/host/proc/meminfo', 'r') as f:
                meminfo = {}
                for line in f:
                    parts = line.split(':')
                    if len(parts) == 2:
                        meminfo[parts[0].strip()] = int(parts[1].strip().split()[0])
                
                total = meminfo.get('MemTotal', 0)
                available = meminfo.get('MemAvailable', 0)
                if total > 0:
                    used_percent = ((total - available) / total) * 100
                    mem = f"{used_percent:2.0f}"
                else:
                    mem = f"{psutil.virtual_memory().percent:2.0f}"
        else:
            mem = f"{psutil.virtual_memory().percent:2.0f}"
    except:
        mem = "N/A"

    return {
        'hostname': hostname,
        'ip': ip,
        'cpu': cpu,
        'mem': mem,
        'temp': get_temperature(os_info),
        'disk': get_disk_usage(),
        'uptime': get_uptime(),
        'entities': get_custom_entities(entity_ids, entity_cache_ttl),
        'supervisor_ok': any(item is not None for item in (host_info, network_info, os_info)),
    }


def build_page_durations(default_duration):
    """Resolve per-page durations, falling back to the shared default."""
    durations = {}
    for page_name in ('summary', 'details', 'clock', 'entities', 'graph', 'alert'):
        override = get_env_int(f'OLED_PAGE_DURATION_{page_name.upper()}', 0, 0, 300)
        durations[page_name] = override or default_duration
    return durations


def get_active_pages(enabled_pages, show_alert_page, alerts, alert_page_position):
    """Return the currently eligible pages, including conditional alert display."""
    if show_alert_page and alerts:
        if alert_page_position == 'back':
            return list(enabled_pages) + ['alert']
        return ['alert'] + list(enabled_pages)
    return list(enabled_pages)


def main():
    log("Initializing OLED System Info Display")

    display_rotation = get_env_int('OLED_DISPLAY_ROTATION', 0, 0, 3)
    refresh_interval = get_env_int('OLED_REFRESH_INTERVAL', 1, 1, 60)
    page_duration = get_env_int('OLED_PAGE_DURATION', 10, 3, 120)
    page_durations = build_page_durations(page_duration)
    page_order = get_env_csv('OLED_PAGE_ORDER')
    startup_delay = get_env_int('OLED_STARTUP_DELAY', 5, 0, 30)
    show_details_page = get_env_bool('OLED_SHOW_DETAILS_PAGE', True)
    show_clock_page = get_env_bool('OLED_SHOW_CLOCK_PAGE', True)
    show_graph_page = get_env_bool('OLED_SHOW_GRAPH_PAGE', True)
    entity_ids = get_env_csv('OLED_ENTITY_IDS')
    show_alert_page = get_env_bool('OLED_SHOW_ALERT_PAGE', True)
    alert_cpu_threshold = get_env_int('OLED_ALERT_CPU_THRESHOLD', 95, 1, 100)
    alert_temp_threshold = get_env_int('OLED_ALERT_TEMP_THRESHOLD', 75, 1, 120)
    alert_disk_threshold = get_env_int('OLED_ALERT_DISK_THRESHOLD', 90, 1, 100)
    alert_page_position = get_env_choice('OLED_ALERT_PAGE_POSITION', 'front', {'front', 'back'})
    entity_cache_ttl = get_env_int('OLED_ENTITY_CACHE_TTL', 5, 0, 300)
    supervisor_cache_ttl = get_env_int('OLED_SUPERVISOR_CACHE_TTL', 3, 0, 300)
    night_mode_enabled = get_env_bool('OLED_NIGHT_MODE_ENABLED', False)
    night_mode_start = get_env_clock_minutes('OLED_NIGHT_MODE_START', '22:00')
    night_mode_end = get_env_clock_minutes('OLED_NIGHT_MODE_END', '07:00')

    enabled_pages = build_enabled_pages(page_order, show_details_page, show_clock_page, show_graph_page, entity_ids)

    # Display configuration
    log("Initializing I2C and OLED display")
    i2c = I2CAdapter(1)
    disp = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)
    disp.rotation = display_rotation
    disp.fill(0)
    disp.show()
    log(
        "OLED display initialized "
        f"(rotation={display_rotation}, refresh={refresh_interval}s, "
        f"page_duration={page_duration}s, pages={','.join(enabled_pages)})"
    )
    
    # Drawing setup
    image = Image.new("1", (disp.width, disp.height))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    
    # Display constants
    padding = 0
    x = 0
    top = padding
    history = deque(maxlen=128)
    current_page_name = enabled_pages[0]
    last_page_switch = time.monotonic()
    last_night_mode_state = None
    last_rendered_page_name = None
    last_rendered_image = None

    # Startup message
    log("Displaying startup message")
    draw.rectangle((0, 0, disp.width, disp.height), outline=0, fill=0)
    draw_startup_logo(draw, x, top, font)
    disp.image(image)
    disp.show()
    time.sleep(startup_delay)
    
    log("Entering main loop")

    try:
        while True:
            draw.rectangle((0, 0, disp.width, disp.height), outline=0, fill=0)

            night_mode_active = is_night_mode_active(night_mode_enabled, night_mode_start, night_mode_end)
            if night_mode_active != last_night_mode_state:
                log(f"Night mode {'enabled' if night_mode_active else 'disabled'}")
                last_night_mode_state = night_mode_active

            if night_mode_active:
                last_page_switch = time.monotonic()
                last_rendered_page_name = None
                last_rendered_image = None
                disp.image(image)
                disp.show()
                time.sleep(refresh_interval)
                continue

            info = get_system_info(entity_ids, entity_cache_ttl, supervisor_cache_ttl)
            alerts = build_alerts(info, alert_cpu_threshold, alert_temp_threshold, alert_disk_threshold)

            active_pages = get_active_pages(enabled_pages, show_alert_page, alerts, alert_page_position)
            if current_page_name not in active_pages:
                current_page_name = active_pages[0]
                last_page_switch = time.monotonic()

            current_page_duration = page_durations.get(
                get_logical_page_name(current_page_name),
                page_duration,
            )
            if len(active_pages) > 1 and time.monotonic() - last_page_switch >= current_page_duration:
                current_index = active_pages.index(current_page_name)
                current_page_name = active_pages[(current_index + 1) % len(active_pages)]
                last_page_switch = time.monotonic()
                log(f"Display page changed to {current_page_name}")

            try:
                cpu_value = max(0, min(100, int(float(str(info['cpu']).strip()))))
            except Exception:
                cpu_value = 0

            history.append(cpu_value)

            page_name = current_page_name
            page_image = Image.new("1", (disp.width, disp.height))
            page_draw = ImageDraw.Draw(page_image)

            if page_name == 'alert':
                draw_alert_page(page_draw, font, disp.width, disp.height, alerts)
            elif page_name == 'summary':
                page_draw.text((x, top), fit_text(f"NAME: {info['hostname']}"), font=font, fill=255)
                page_draw.text((x, top + 12), fit_text(f"IP  : {info['ip']}"), font=font, fill=255)
                page_draw.text((x, top + 24), fit_text(f"CPU : {info['cpu']}% MEM: {info['mem']}%"), font=font, fill=255)
                page_draw.text((x, top + 36), fit_text(f"TMP : {info['temp']} DISK:{info['disk']}%"), font=font, fill=255)
                page_draw.text((x, top + 48), fit_text(f"UP  : {info['uptime']}"), font=font, fill=255)
            elif page_name == 'details':
                page_draw.text((x, top), fit_text("SYSTEM DETAILS"), font=font, fill=255)
                page_draw.text((x, top + 12), fit_text(f"HOST: {info['hostname']}"), font=font, fill=255)
                page_draw.text((x, top + 24), fit_text(f"IP  : {info['ip']}"), font=font, fill=255)
                page_draw.text((x, top + 36), fit_text(f"TEMP: {info['temp']}"), font=font, fill=255)
                page_draw.text((x, top + 48), fit_text(f"DISK: {info['disk']}% UP:{info['uptime']}"), font=font, fill=255)
            elif page_name == 'clock':
                draw_clock_page(page_draw, font, disp.width, info['uptime'])
            elif page_name.startswith('entities:'):
                entity_page = page_name.split(':', 1)[1]
                page_number_text, page_count_text = entity_page.split('/', 1)
                draw_entities_page(
                    page_draw,
                    font,
                    info['entities'],
                    int(page_number_text),
                    int(page_count_text),
                )
            else:
                draw_cpu_graph(page_draw, history, disp.width, disp.height, info['cpu'], info['mem'], info['temp'])

            if page_name != last_rendered_page_name:
                animate_page_transition(disp, last_rendered_image, page_image)
            else:
                disp.image(page_image)
                disp.show()

            image = page_image
            last_rendered_image = page_image.copy()
            last_rendered_page_name = page_name

            time.sleep(refresh_interval)

    except KeyboardInterrupt:
        log("Received keyboard interrupt")
    except Exception as e:
        log(f"ERROR: {e}")
        raise
    finally:
        log("Shutdown complete")


if __name__ == "__main__":
    main()