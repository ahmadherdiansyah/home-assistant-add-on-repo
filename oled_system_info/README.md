# OLED System Info Display

Displays system information on a 128x32 SSD1306 OLED screen connected to Raspberry Pi GPIO.

## Features
- Real-time system information display (IP address, hostname, CPU, memory, temperature, disk usage, uptime)
- Always-on display refresh
- Automatic page rotation every 10 seconds
- Compact CPU history graph
- Configurable for different Raspberry Pi models
- Auto-starts with Home Assistant

## Hardware Requirements
- Raspberry Pi (any model with GPIO pins)
- SSD1306 OLED Display (128x32, I2C)
- Jumper wires

## Wiring

### OLED Display (I2C)
| OLED Pin | Raspberry Pi Pin | Pin Number |
|----------|------------------|------------|
| VCC      | 3.3V             | 1          |
| GND      | Ground           | 14         |
| SDA      | GPIO 2 (SDA)     | 3          |
| SCL      | GPIO 3 (SCL)     | 5          |

Only the OLED I2C wiring above is required for this add-on.

## Prerequisites: Enable I2C on Home Assistant OS

**IMPORTANT:** I2C must be enabled before this add-on will work.

### Method 1: Using HassOS I2C Configurator (Recommended - Easiest)

1. Add the HassOSConfigurator repository:
   - Go to **Settings** → **Add-ons** → **Add-on Store**
   - Click **⋮** (three dots) → **Repositories**
   - Add: `https://github.com/adamoutler/HassOSConfigurator`

2. Install **HassOS I2C Configurator**
   - Find it in the add-on store
   - Click **Install**

3. Configure and run:
   - Turn **OFF** "Protection mode" in the Info tab
   - Click **Start**
   - Watch the logs for success

4. **Reboot** your system:
   - **Settings** → **System** → **Reboot System**

5. Verify I2C is enabled (optional):
   - Install "Terminal & SSH" add-on
   - Run: `ls /dev/i2c-*` (should show `/dev/i2c-1`)

6. Uninstall the configurator (optional):
   - Once I2C works, you can uninstall HassOS I2C Configurator

### Method 2: Manual Configuration via SSH

If the configurator doesn't work or you prefer manual configuration:

#### Step 1: Enable SSH Access

1. Add the HassOSConfigurator repository (if not already added):
   - **Settings** → **Add-ons** → **Add-on Store** → **⋮** → **Repositories**
   - Add: `https://github.com/adamoutler/HassOSConfigurator`

2. Install **HassOS SSH port 22222 Configurator**

3. Generate SSH key pair on your computer:
   ```bash
   # On Linux/Mac:
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/homeassistant
   
   # This creates two files:
   # ~/.ssh/homeassistant (private key)
   # ~/.ssh/homeassistant.pub (public key)
   ```

4. Copy your **public key** content:
   ```bash
   cat ~/.ssh/homeassistant.pub
   ```

5. Configure the SSH add-on:
   - Go to the **Configuration** tab
   - Paste your public key
   - Turn **OFF** "Protection mode"
   - Click **Save**

6. Start the add-on and check logs for success

7. **Reboot** Home Assistant:
   - **Settings** → **System** → **Reboot System**

8. Connect via SSH (after reboot):
   ```bash
   ssh -i ~/.ssh/homeassistant -p 22222 root@homeassistant.local
   ```

#### Step 2: Enable I2C and SPI Manually

Once connected via SSH:

1. Edit the boot configuration:
   ```bash
   vi /mnt/boot/config.txt
   ```

2. Add these lines at the end of the file:
   ```
   # Enable I2C
   dtparam=i2c_arm=on
   dtparam=i2c1=on

   # Enable SPI
   dtparam=spi=on
   ```

3. Save and exit:
   - Press `Ctrl+X`
   - Press `Y` to confirm
   - Press `Enter`

4. Load the I2C kernel module:
   ```bash
   mkdir -p /mnt/boot/CONFIG/modules
   echo "i2c-dev" > /mnt/boot/CONFIG/modules/rpi-i2c.conf
   ```

5. Reboot:
   ```bash
   reboot
   ```

6. Verify I2C is working (after reboot, reconnect via SSH):
   ```bash
   ls /dev/i2c-*
   # Should show: /dev/i2c-1
   
   i2cdetect -y 1
   # Should show device at address 3c
   ```

## Installation

### 1. Add This Repository

- Go to **Settings** → **Add-ons** → **Add-on Store**
- Click **⋮** (three dots) → **Repositories**
- Add your repository URL
- Click **Close**

### 2. Install the Add-on

- Refresh the add-on store
- Find "OLED System Info Display" in the list
- Click **Install**
- Wait for installation to complete (may take 10-15 minutes on first build)

### 3. Configure Board Type

Before starting, configure your Raspberry Pi model:

- Go to the **Configuration** tab
- Select your **Board Type** (e.g., `RASPBERRY_PI_4B`)
- Select your **Chip Type** (e.g., `BCM2711`)
- Click **Save**

**Common configurations:**
- **Raspberry Pi 4**: Board: `RASPBERRY_PI_4B`, Chip: `BCM2711` (default)
- **Raspberry Pi 3B+**: Board: `RASPBERRY_PI_3B_PLUS`, Chip: `BCM2837`
- **Raspberry Pi Zero W**: Board: `RASPBERRY_PI_ZERO_W`, Chip: `BCM2835`
- **Raspberry Pi 5**: Board: `RASPBERRY_PI_5`, Chip: `BCM2712`

See the **Configuration** tab for the complete list.

### 4. Start the Add-on

- Go to the **Info** tab
- Click **Start**
- Check the **Log** tab for any errors
- Enable **Start on boot**
- Enable **Watchdog** (optional)

## Usage

### Display Information

The OLED displays:
- Hostname and IP address
- CPU usage percentage
- Memory usage percentage

The display refreshes system information automatically once per second.

## Troubleshooting

### Display Not Working

**Check I2C is enabled:**
```bash
ls /dev/i2c-*
```
Expected: `/dev/i2c-1`

**Detect OLED device:**
```bash
i2cdetect -y 1
```
Expected: Device shown at address `3c`

**Solutions:**
- Verify I2C is enabled using one of the methods above
- Check wiring connections (especially VCC, GND, SDA, SCL)
- Ensure OLED is getting 3.3V power (not 5V)
- Try reseating connections

### Add-on Won't Start

1. Check add-on logs (**Log** tab)
2. Common issues:
   - I2C not enabled → Follow prerequisite steps
   - Wrong board type configured → Update in Configuration tab
   - Wiring issues → Verify connections

### I2C Device Not Detected

If `i2cdetect -y 1` shows no device at `3c`:
- Power off completely (unplug power)
- Check all OLED connections
- Verify OLED works (test on another device if possible)
- Check for loose connections
- Try different jumper wires

## Uninstalling

To remove SSH access after setup:
1. Uninstall "HassOS SSH port 22222 Configurator" if installed
2. The OLED add-on will continue working

To disable I2C (if needed):
1. SSH into your system
2. Edit `/mnt/boot/config.txt`
3. Comment out the I2C lines:
   ```
   #dtparam=i2c_arm=on
   #dtparam=i2c1=on
   ```
4. Reboot

## Credits

- Based on the original project by [leelooauto](https://github.com/leelooauto/system_info)
- Uses [HassOSConfigurator](https://github.com/adamoutler/HassOSConfigurator) for system configuration

## Support

For issues with this add-on, please open an issue on the repository.

For SSH/I2C configuration help, see the [HassOSConfigurator support forum](https://community.home-assistant.io/t/hassos-i2c-configurator/264167).

## License

MIT License