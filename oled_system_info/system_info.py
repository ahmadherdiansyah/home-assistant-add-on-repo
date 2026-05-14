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


def log(message):
    """Print log message with timestamp"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def supervisor_api(endpoint):
    """Call Home Assistant Supervisor API"""
    try:
        response = requests.get(
            f'http://supervisor/{endpoint}',
            headers={'Authorization': f'Bearer {os.getenv("SUPERVISOR_TOKEN")}'},
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        log(f"API Error ({endpoint}): {e}")
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


def fit_text(value, max_chars=21):
    """Trim text to fit the 128px wide display."""
    text = str(value)
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars - 1]}~"


def draw_cpu_graph(draw, history, width, height, cpu, mem, temp):
    """Render a compact CPU history graph for the OLED."""
    title = f"CPU {cpu}% MEM {mem}%"
    subtitle = f"TEMP {temp}"
    draw.text((0, -2), fit_text(title), fill=255)
    draw.text((0, 6), fit_text(subtitle), fill=255)

    graph_top = 16
    graph_height = height - graph_top - 1
    graph_width = width

    draw.line((0, graph_top + graph_height, graph_width - 1, graph_top + graph_height), fill=255)

    if not history:
        return

    values = list(history)[-graph_width:]
    start_x = graph_width - len(values)

    for index, value in enumerate(values):
        bar_height = max(1, int((value / 100) * graph_height)) if value > 0 else 0
        x = start_x + index
        if bar_height > 0:
            draw.line(
                (x, graph_top + graph_height, x, graph_top + graph_height - bar_height),
                fill=255,
            )


def get_system_info():
    """Retrieve HOST system information via Supervisor API"""
    # Get host info
    host_info = supervisor_api('host/info')
    network_info = supervisor_api('network/info')
    os_info = supervisor_api('os/info')
    
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
    }


def main():
    log("Initializing OLED System Info Display")

    display_rotation = get_env_int('OLED_DISPLAY_ROTATION', 0, 0, 3)
    refresh_interval = get_env_int('OLED_REFRESH_INTERVAL', 1, 1, 60)
    page_duration = get_env_int('OLED_PAGE_DURATION', 10, 3, 120)
    startup_delay = get_env_int('OLED_STARTUP_DELAY', 5, 0, 30)
    show_details_page = get_env_bool('OLED_SHOW_DETAILS_PAGE', True)
    show_graph_page = get_env_bool('OLED_SHOW_GRAPH_PAGE', True)

    enabled_pages = ['summary']
    if show_details_page:
        enabled_pages.append('details')
    if show_graph_page:
        enabled_pages.append('graph')

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
    current_page = 0
    last_page_switch = time.monotonic()

    # Startup message
    log("Displaying startup message")
    draw.rectangle((0, 0, disp.width, disp.height), outline=0, fill=0)
    draw.text((x, top), "OLED Infoscreen", font=font, fill=255)
    draw.text((x, top + 12), "SSD1306 128x64", font=font, fill=255)
    draw.text((x, top + 24), "Starting service...", font=font, fill=255)
    draw.text((x, top + 36), "Please wait", font=font, fill=255)
    disp.image(image)
    disp.show()
    time.sleep(startup_delay)
    
    log("Entering main loop")

    try:
        while True:
            draw.rectangle((0, 0, disp.width, disp.height), outline=0, fill=0)

            if len(enabled_pages) > 1 and time.monotonic() - last_page_switch >= page_duration:
                current_page = (current_page + 1) % len(enabled_pages)
                last_page_switch = time.monotonic()
                log(f"Display page changed to {enabled_pages[current_page]}")

            info = get_system_info()

            try:
                cpu_value = max(0, min(100, int(float(str(info['cpu']).strip()))))
            except Exception:
                cpu_value = 0

            history.append(cpu_value)

            page_name = enabled_pages[current_page]

            if page_name == 'summary':
                draw.text((x, top), fit_text(f"NAME: {info['hostname']}"), font=font, fill=255)
                draw.text((x, top + 12), fit_text(f"IP  : {info['ip']}"), font=font, fill=255)
                draw.text((x, top + 24), fit_text(f"CPU : {info['cpu']}% MEM: {info['mem']}%"), font=font, fill=255)
                draw.text((x, top + 36), fit_text(f"TMP : {info['temp']} DISK:{info['disk']}%"), font=font, fill=255)
                draw.text((x, top + 48), fit_text(f"UP  : {info['uptime']}"), font=font, fill=255)
            elif page_name == 'details':
                draw.text((x, top), fit_text("SYSTEM DETAILS"), font=font, fill=255)
                draw.text((x, top + 12), fit_text(f"HOST: {info['hostname']}"), font=font, fill=255)
                draw.text((x, top + 24), fit_text(f"IP  : {info['ip']}"), font=font, fill=255)
                draw.text((x, top + 36), fit_text(f"TEMP: {info['temp']}"), font=font, fill=255)
                draw.text((x, top + 48), fit_text(f"DISK: {info['disk']}% UP:{info['uptime']}"), font=font, fill=255)
            else:
                draw_cpu_graph(draw, history, disp.width, disp.height, info['cpu'], info['mem'], info['temp'])

            disp.image(image)
            disp.show()

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