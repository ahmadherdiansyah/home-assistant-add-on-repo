# OLED System Info Display Documentation

Complete documentation for installing and configuring the OLED System Info Display add-on for Home Assistant.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Hardware Setup](#hardware-setup)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Configuration](#advanced-configuration)

---

## Prerequisites

### Enable I2C on Home Assistant OS

The OLED display requires I2C to be enabled on your Raspberry Pi. Choose one of the methods below.

#### Part A: Enable SSH Access to Port 22222

This SSH access is to the **host system**, not the Home Assistant container.

##### 1. Install SSH Configurator Add-on

1. Add repository (if not already done):
   - **Settings** → **Add-ons** → **Add-on Store** → **⋮** → **Repositories**
   - Add: `https://github.com/adamoutler/HassOSConfigurator`

2. Install "HassOS SSH port 22222 Configurator"

##### 2. Generate SSH Key Pair

On your computer (Linux/Mac/Windows with Git Bash):

```bash
# Generate SSH key pair
ssh-keygen -t rsa -b 4096 -f ~/.ssh/homeassistant -C "homeassistant-key"

# This creates two files:
# ~/.ssh/homeassistant (private key - keep this safe!)
# ~/.ssh/homeassistant.pub (public key - paste into add-on)
```

If asked for a passphrase, you can leave it empty or set one for extra security.

##### 3. Get Your Public Key

```bash
# Display the public key
cat ~/.ssh/homeassistant.pub

# Example output:
# ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC... homeassistant-key
```

Copy the entire output (starts with `ssh-rsa`).

##### 4. Configure SSH Add-on

1. Go to the SSH add-on **Configuration** tab
2. Paste your public key in the authorized keys field
3. Click **Save**
4. Go to the **Info** tab
5. Turn **OFF** "Protection mode"
6. Click **Start**
7. Check **Log** tab - should say "SSH is now active on port 22222"

##### 5. Reboot Home Assistant

**Settings** → **System** → **Reboot System**

##### 6. Connect via SSH

After reboot, from your computer:

```bash
# Using hostname
ssh -i ~/.ssh/homeassistant -p 22222 root@homeassistant.local

# OR using IP address (replace with your IP)
ssh -i ~/.ssh/homeassistant -p 22222 root@192.168.1.100
```

If successful, you'll see a command prompt like:
```
Welcome to HassOS
homeassistant:~#
```

#### Part B: Enable I2C and SPI in config.txt

Once connected via SSH:

##### 1. Edit Boot Configuration

```bash
vi /mnt/boot/config.txt
```

##### 2. Add I2C and SPI Configuration

Scroll to the end of the file, press `i` (for insert mode) and add:

```
# Enable I2C for OLED display
dtparam=i2c_arm=on
dtparam=i2c1=on

# Enable SPI
dtparam=spi=on
```

##### 3. Save and Exit

- Press `Escape` to leave insert mode
- Press `:wq`
- Press `Enter` to confirm

##### 4. Load I2C Kernel Module

```bash
mkdir -p /mnt/boot/CONFIG/modules
echo "i2c-dev" > /mnt/boot/CONFIG/modules/rpi-i2c.conf
```

##### 5. Reboot

```bash
reboot
```

Your SSH session will disconnect. Wait 1-2 minutes for reboot.

##### 6. Verify I2C is Enabled

Reconnect via SSH:

```bash
ssh -i ~/.ssh/homeassistant -p 22222 root@homeassistant.local
```

Check I2C device exists:

```bash
ls /dev/i2c-*
```

Expected output: `/dev/i2c-1`

Scan I2C bus (after wiring OLED):

```bash
i2cdetect -y 1
```

Expected output (with OLED connected at address 0x3C):
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:                         -- -- -- -- -- -- -- -- 
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
30: -- -- -- -- -- -- -- -- -- -- -- -- 3c -- -- -- 
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
70: -- -- -- -- -- -- -- --
```

The `3c` shows your OLED is detected!

---

## Hardware Setup

### Required Components

- **SSD1306 OLED Display (128x64, I2C)**
- **Jumper wires** - Female-to-female recommended

### Wiring Connections

#### OLED Display (I2C)

| OLED Pin | Connect To | Raspberry Pi Pin | GPIO # | Notes |
|----------|-----------|------------------|--------|-------|
| VCC      | 3.3V Power | 1 | - | **Important: Use 3.3V, NOT 5V!** |
| GND      | Ground | 14 | - | Any ground pin works |
| SDA      | I2C Data | 3 | GPIO 2 | Do not swap with SCL |
| SCL      | I2C Clock | 5 | GPIO 3 | Do not swap with SDA |

**Critical Notes:**
- Use **3.3V power** only. 5V may damage some OLED modules.
- SDA and SCL must connect to the designated I2C pins (GPIO 2 and GPIO 3)

**Complete Wiring:**
For detailed wiring diagrams with resistor placement, see the [original project](https://github.com/leelooauto/system_info).

### GPIO Pinout Reference

```
    3.3V [ 1] [ 2] 5V
SDA/GPIO2 [ 3] [ 4] 5V
SCL/GPIO3 [ 5] [ 6] GND
   GPIO 4 [ 7] [ 8] GPIO 14
      GND [ 9] [10] GPIO 15
  GPIO 17 [11] [12] GPIO 18
  GPIO 27 [13] [14] GND          <- OLED GND
  GPIO 22 [15] [16] GPIO 23      <- LED
      3V3 [17] [18] GPIO 24
  GPIO 10 [19] [20] GND
   GPIO 9 [21] [22] GPIO 25
  GPIO 11 [23] [24] GPIO 8
      GND [25] [26] GPIO 7
   GPIO 0 [27] [28] GPIO 1
   GPIO 5 [29] [30] GND
   GPIO 6 [31] [32] GPIO 12
  GPIO 13 [33] [34] GND
  GPIO 19 [35] [36] GPIO 16
  GPIO 26 [37] [38] GPIO 20      <- Button
      GND [39] [40] GPIO 21      <- Button GND
```

---

## Installation

### 1. Add Add-on Repository

1. Go to **Settings** → **Add-ons** → **Add-on Store**
2. Click **⋮** (three dots) → **Repositories**
3. Paste your repository URL
4. Click **Add**
5. Click **Close**

### 2. Install the Add-on

1. Refresh the add-on store if needed
2. Find "OLED System Info Display" in the list
3. Click on it
4. Click **Install**
5. Wait for installation (may take 10-15 minutes depending on Pi model)

### 3. Start the Add-on

1. Click **Start**
2. Check the **Log** tab for any errors
3. If successful, you should see messages like:
   - "Starting OLED System Info Display..."
   - "I2C device detected at 0x3C"
   - "OLED initialized successfully"

### 4. Enable Auto-start

1. In the **Info** tab:
   - Enable **Start on boot**
   - Enable **Watchdog** (optional - auto-restarts on crash)

---

## Configuration

### Board Type Selection

You must configure your Raspberry Pi model before starting the add-on.

#### Available Options

| Board Type | Description | Chip Type |
|-----------|-------------|-----------|
| `RASPBERRY_PI_ZERO` | Raspberry Pi Zero (v1.x) | `BCM2835` |
| `RASPBERRY_PI_ZERO_W` | Raspberry Pi Zero W (with WiFi) | `BCM2835` |
| `RASPBERRY_PI_2B` | Raspberry Pi 2 Model B | `BCM2836` |
| `RASPBERRY_PI_3B` | Raspberry Pi 3 Model B | `BCM2837` |
| `RASPBERRY_PI_3B_PLUS` | Raspberry Pi 3 Model B+ | `BCM2837` |
| `RASPBERRY_PI_3A_PLUS` | Raspberry Pi 3 Model A+ | `BCM2837` |
| `RASPBERRY_PI_4B` | Raspberry Pi 4 Model B | `BCM2711` |
| `RASPBERRY_PI_5` | Raspberry Pi 5 | `BCM2712` |
| `RASPBERRY_PI_CM4` | Compute Module 4 | `BCM2711` |

#### How to Configure

1. Go to the add-on page
2. Click the **Configuration** tab
3. Select your board from the **board_type** dropdown
4. Select the corresponding **chip_type** dropdown
5. Click **Save**

**Example for Raspberry Pi 4:**
```yaml
board_type: RASPBERRY_PI_4B
chip_type: BCM2711
display_rotation: 0
refresh_interval: 1
page_duration: 10
page_order: summary,entities,details,graph
startup_delay: 5
show_details_page: true
show_graph_page: true
entity_ids: sensor.living_room_temperature,sensor.office_humidity
show_alert_page: true
alert_cpu_threshold: 95
alert_temp_threshold: 75
alert_disk_threshold: 90
night_mode_enabled: false
night_mode_start: "22:00"
night_mode_end: "07:00"
```

**Example for Raspberry Pi Zero W:**
```yaml
board_type: RASPBERRY_PI_ZERO_W
chip_type: BCM2835
```

---

## Usage

### Display Behavior

**On Startup:**
1. Display shows the Home Assistant startup logo for the configured `startup_delay`
2. Display begins refreshing system information automatically

**Page Rotation:**
1. The summary page is always enabled
2. Optional details, entities, and graph pages can be enabled or disabled in the add-on configuration
3. `page_order` controls the rotation order for enabled pages
4. The display switches pages using the configured `page_duration`

### System Information Shown

```
NAME: homeassistant
IP  : 192.168.1.100
CPU : 25% | MEM: 45%
```

- **NAME**: Your Home Assistant hostname
- **IP**: Current IP address
- **CPU**: Current CPU usage percentage
- **MEM**: Current memory usage percentage

Additional optional pages can show:
- Temperature
- Disk usage
- Uptime
- Home Assistant entity states
- CPU history graph
- Alert page when configured limits are exceeded

### Display Options

| Option | Default | Description |
|--------|---------|-------------|
| `display_rotation` | `0` | Rotates the OLED output. Use `2` for 180-degree mounting. |
| `refresh_interval` | `1` | Refresh interval in seconds. |
| `page_duration` | `10` | How long each page stays visible before rotating. |
| `page_order` | auto | Comma-separated page order using `summary`, `details`, `entities`, and `graph`. |
| `startup_delay` | `5` | How long the startup message remains on screen. |
| `show_details_page` | `true` | Enables the temperature, disk, and uptime page. |
| `show_graph_page` | `true` | Enables the CPU history graph page. |
| `entity_ids` | empty | Comma-separated Home Assistant entity IDs shown on the entities page. |
| `show_alert_page` | `true` | Displays a full-screen alert page when thresholds are exceeded. |
| `alert_cpu_threshold` | `95` | CPU percentage that triggers an alert. |
| `alert_temp_threshold` | `75` | Temperature in Celsius that triggers an alert. |
| `alert_disk_threshold` | `90` | Disk usage percentage that triggers an alert. |
| `night_mode_enabled` | `false` | Enables scheduled display blanking. |
| `night_mode_start` | `22:00` | Quiet-hours start time in 24-hour format. |
| `night_mode_end` | `07:00` | Quiet-hours end time in 24-hour format. |

---

## Troubleshooting

### I2C Not Detected

**Symptom:** Add-on logs show "I2C device /dev/i2c-1 not found"

**Solution:**

1. Connect via SSH:
   ```bash
   ssh -i ~/.ssh/homeassistant -p 22222 root@homeassistant.local
   ```

2. Check if I2C device exists:
   ```bash
   ls /dev/i2c-*
   ```

3. If not found, check config.txt:
   ```bash
   cat /mnt/boot/config.txt | grep i2c
   ```

4. Should show:
   ```
   dtparam=i2c_arm=on
   dtparam=i2c1=on
   ```

5. If missing, add them:
   ```bash
   nano /mnt/boot/config.txt
   # Add the lines above
   # Save: Ctrl+X, Y, Enter
   ```

6. Load module and reboot:
   ```bash
   mkdir -p /mnt/boot/CONFIG/modules
   echo "i2c-dev" > /mnt/boot/CONFIG/modules/rpi-i2c.conf
   reboot
   ```

### OLED Not Responding

**Check I2C bus:**

```bash
ssh -i ~/.ssh/homeassistant -p 22222 root@homeassistant.local
i2cdetect -y 1
```

**Expected:** Device shown at address `3c`

**If no device:**
1. Power off Raspberry Pi completely
2. Check all 4 OLED connections:
   - VCC to 3.3V (pin 1)
   - GND to Ground (pin 14)
   - SDA to GPIO 2 (pin 3)
   - SCL to GPIO 3 (pin 5)
3. Verify connections are secure
4. Try different jumper wires
5. Test OLED on another device if possible

### Display Shows Garbage/Random Pixels

**Possible causes:**
- Loose connections
- Electromagnetic interference
- Wrong I2C address
- Faulty OLED module

**Solutions:**
1. Re-seat all connections
2. Use shorter jumper wires
3. Add 4.7K pull-up resistors on SDA/SCL (advanced)
4. Try another OLED module

### Wrong Board Type

**Symptom:** Add-on starts but display doesn't work, logs show board detection errors

**Solution:**
1. Go to add-on **Configuration** tab
2. Verify board type matches your Raspberry Pi
3. Save and restart add-on

### Add-on Won't Build/Install

**Check architecture:**
The add-on supports: `armhf`, `armv7`, `aarch64`

**Force rebuild:**
1. Go to add-on page
2. Click **Rebuild**
3. Watch logs for build errors
4. Wait 10-15 minutes for completion

### Add-on Crashes/Restarts

**Check logs:**
1. Settings → Add-ons → OLED System Info Display
2. Click **Log** tab
3. Look for Python errors or module not found

**Common fixes:**
- Rebuild the add-on
- Check I2C is still enabled
- Verify wiring hasn't come loose

---

## Advanced Configuration

### Changing GPIO Pins

To use different GPIO pins, you need to modify the source code.

1. Fork the repository
2. Edit `system_info.py`:
   ```python
   INFO_BTN = 20  # Change to your button GPIO
   LED = 23       # Change to your LED GPIO
   ```
3. Rebuild add-on from your fork

### Adjusting Display Timeout

Edit `system_info.py`:
```python
DISP_TIMEOUT = 15  # Seconds until display sleeps
```

### Modifying Reboot/Shutdown Timing

Edit `system_info.py`:
```python
REBOOT_TIMEOUT = 5    # Seconds to hold for reboot
SHUTDOWN_TIMEOUT = 10  # Additional seconds for shutdown
```

### Using Different I2C Address

If your OLED uses a different address (some use 0x3D):

Edit `system_info.py`:
```python
i2c = busio.I2C(board.SCL, board.SDA)
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3D)  # Change 0x3C to 0x3D
```

Then rebuild the add-on.

---

## Removing/Uninstalling

### Remove OLED Add-on

1. Settings → Add-ons → OLED System Info Display
2. Stop the add-on
3. Click **Uninstall**

### Remove SSH Access

1. Settings → Add-ons → HassOS SSH port 22222 Configurator
2. Stop the add-on
3. Click **Uninstall**

### Disable I2C (Optional)

If you no longer need I2C:

```bash
ssh -i ~/.ssh/homeassistant -p 22222 root@homeassistant.local
nano /mnt/boot/config.txt

# Comment out these lines:
#dtparam=i2c_arm=on
#dtparam=i2c1=on

# Save and reboot
reboot
```

---

## Support and Resources

### Getting Help

- **This Add-on Issues**: Open an issue on the add-on repository
- **Original Script**: [leelooauto/system_info](https://github.com/leelooauto/system_info)
- **SSH/I2C Config**: [HassOSConfigurator](https://github.com/adamoutler/HassOSConfigurator)
- **Home Assistant Community**: [Community Forums](https://community.home-assistant.io/)

### Useful Links

- [Home Assistant Add-on Documentation](https://developers.home-assistant.io/docs/add-ons)
- [Raspberry Pi GPIO Pinout](https://pinout.xyz/)
- [I2C Tools Documentation](https://i2c.wiki.kernel.org/index.php/I2C_Tools)
- [SSD1306 Datasheet](https://cdn-shop.adafruit.com/datasheets/SSD1306.pdf)

---

## Appendix

### SSH Key Management

**View your public key:**
```bash
cat ~/.ssh/homeassistant.pub
```

**Copy to clipboard (Linux):**
```bash
cat ~/.ssh/homeassistant.pub | xclip -selection clipboard
```

**Copy to clipboard (Mac):**
```bash
cat ~/.ssh/homeassistant.pub | pbcopy
```

**Windows PowerShell:**
```powershell
Get-Content $env:USERPROFILE\.ssh\homeassistant.pub | clip
```

### Understanding I2C

**What is I2C?**
- Inter-Integrated Circuit communication protocol
- Uses 2 wires: SDA (data) and SCL (clock)
- Supports multiple devices on same bus
- Each device has unique address (OLED typically 0x3C or 0x3D)

**I2C Bus Speed:**
By default, Raspberry Pi I2C runs at 100kHz. To increase speed:

```bash
nano /mnt/boot/config.txt

# Change this line:
dtparam=i2c_arm=on

# To this:
dtparam=i2c_arm=on,i2c_arm_baudrate=400000
```

This sets 400kHz (faster, but may cause issues with cheap cables).

### Testing I2C Without Add-on

```bash
# Install tools
apk add i2c-tools python3 py3-smbus

# Scan bus
i2cdetect -y 1

# Read byte from OLED
i2cget -y 1 0x3c 0x00

# Write byte to OLED (careful!)
i2cset -y 1 0x3c 0x00 0x00
```

---

## License

MIT License - See [LICENSE.md] for full license text.

## Version History

- **1.0.0**: Initial release
  - Support for Raspberry Pi 2, 3, 4, 5, Zero
  - I2C OLED display support
  - Auto-start on boot