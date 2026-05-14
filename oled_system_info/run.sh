#!/usr/bin/with-contenv bashio

bashio::log.info "Starting OLED System Info Display..."

if [ ! -e "/dev/i2c-1" ]; then
    bashio::log.error "I2C device /dev/i2c-1 not found!"
    exit 1
fi

bashio::log.info "Scanning I2C bus..."
i2cdetect -y 1

BOARD_TYPE=$(bashio::config 'board_type')
CHIP_TYPE=$(bashio::config 'chip_type')

export BLINKA_FORCEBOARD="${BOARD_TYPE}"
export BLINKA_FORCECHIP="${CHIP_TYPE}"

bashio::log.info "Board: ${BOARD_TYPE}, Chip: ${CHIP_TYPE}"
bashio::log.info "Starting OLED display script..."

python3 /system_info.py