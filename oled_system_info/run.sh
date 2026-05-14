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
DISPLAY_ROTATION=$(bashio::config 'display_rotation')
REFRESH_INTERVAL=$(bashio::config 'refresh_interval')
PAGE_DURATION=$(bashio::config 'page_duration')
STARTUP_DELAY=$(bashio::config 'startup_delay')
SHOW_DETAILS_PAGE=$(bashio::config 'show_details_page')
SHOW_GRAPH_PAGE=$(bashio::config 'show_graph_page')

export BLINKA_FORCEBOARD="${BOARD_TYPE}"
export BLINKA_FORCECHIP="${CHIP_TYPE}"
export OLED_DISPLAY_ROTATION="${DISPLAY_ROTATION}"
export OLED_REFRESH_INTERVAL="${REFRESH_INTERVAL}"
export OLED_PAGE_DURATION="${PAGE_DURATION}"
export OLED_STARTUP_DELAY="${STARTUP_DELAY}"
export OLED_SHOW_DETAILS_PAGE="${SHOW_DETAILS_PAGE}"
export OLED_SHOW_GRAPH_PAGE="${SHOW_GRAPH_PAGE}"

bashio::log.info "Board: ${BOARD_TYPE}, Chip: ${CHIP_TYPE}"
bashio::log.info "Rotation: ${DISPLAY_ROTATION}, Refresh: ${REFRESH_INTERVAL}s, Page: ${PAGE_DURATION}s"
bashio::log.info "Starting OLED display script..."

python3 /system_info.py