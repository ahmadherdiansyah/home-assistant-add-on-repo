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
PAGE_DURATION_SUMMARY=$(bashio::config 'page_duration_summary')
PAGE_DURATION_DETAILS=$(bashio::config 'page_duration_details')
PAGE_DURATION_CLOCK=$(bashio::config 'page_duration_clock')
PAGE_DURATION_ENTITIES=$(bashio::config 'page_duration_entities')
PAGE_DURATION_GRAPH=$(bashio::config 'page_duration_graph')
PAGE_DURATION_ALERT=$(bashio::config 'page_duration_alert')
PAGE_ORDER=$(bashio::config 'page_order')
STARTUP_DELAY=$(bashio::config 'startup_delay')
SHOW_DETAILS_PAGE=$(bashio::config 'show_details_page')
SHOW_CLOCK_PAGE=$(bashio::config 'show_clock_page')
SHOW_GRAPH_PAGE=$(bashio::config 'show_graph_page')
ENTITY_IDS=$(bashio::config 'entity_ids')
ENTITY_CACHE_TTL=$(bashio::config 'entity_cache_ttl')
SHOW_ALERT_PAGE=$(bashio::config 'show_alert_page')
ALERT_PAGE_POSITION=$(bashio::config 'alert_page_position')
ALERT_CPU_THRESHOLD=$(bashio::config 'alert_cpu_threshold')
ALERT_TEMP_THRESHOLD=$(bashio::config 'alert_temp_threshold')
ALERT_DISK_THRESHOLD=$(bashio::config 'alert_disk_threshold')
SUPERVISOR_CACHE_TTL=$(bashio::config 'supervisor_cache_ttl')
NIGHT_MODE_ENABLED=$(bashio::config 'night_mode_enabled')
NIGHT_MODE_START=$(bashio::config 'night_mode_start')
NIGHT_MODE_END=$(bashio::config 'night_mode_end')

export BLINKA_FORCEBOARD="${BOARD_TYPE}"
export BLINKA_FORCECHIP="${CHIP_TYPE}"
export OLED_DISPLAY_ROTATION="${DISPLAY_ROTATION}"
export OLED_REFRESH_INTERVAL="${REFRESH_INTERVAL}"
export OLED_PAGE_DURATION="${PAGE_DURATION}"
export OLED_PAGE_DURATION_SUMMARY="${PAGE_DURATION_SUMMARY}"
export OLED_PAGE_DURATION_DETAILS="${PAGE_DURATION_DETAILS}"
export OLED_PAGE_DURATION_CLOCK="${PAGE_DURATION_CLOCK}"
export OLED_PAGE_DURATION_ENTITIES="${PAGE_DURATION_ENTITIES}"
export OLED_PAGE_DURATION_GRAPH="${PAGE_DURATION_GRAPH}"
export OLED_PAGE_DURATION_ALERT="${PAGE_DURATION_ALERT}"
export OLED_PAGE_ORDER="${PAGE_ORDER}"
export OLED_STARTUP_DELAY="${STARTUP_DELAY}"
export OLED_SHOW_DETAILS_PAGE="${SHOW_DETAILS_PAGE}"
export OLED_SHOW_CLOCK_PAGE="${SHOW_CLOCK_PAGE}"
export OLED_SHOW_GRAPH_PAGE="${SHOW_GRAPH_PAGE}"
export OLED_ENTITY_IDS="${ENTITY_IDS}"
export OLED_ENTITY_CACHE_TTL="${ENTITY_CACHE_TTL}"
export OLED_SHOW_ALERT_PAGE="${SHOW_ALERT_PAGE}"
export OLED_ALERT_PAGE_POSITION="${ALERT_PAGE_POSITION}"
export OLED_ALERT_CPU_THRESHOLD="${ALERT_CPU_THRESHOLD}"
export OLED_ALERT_TEMP_THRESHOLD="${ALERT_TEMP_THRESHOLD}"
export OLED_ALERT_DISK_THRESHOLD="${ALERT_DISK_THRESHOLD}"
export OLED_SUPERVISOR_CACHE_TTL="${SUPERVISOR_CACHE_TTL}"
export OLED_NIGHT_MODE_ENABLED="${NIGHT_MODE_ENABLED}"
export OLED_NIGHT_MODE_START="${NIGHT_MODE_START}"
export OLED_NIGHT_MODE_END="${NIGHT_MODE_END}"

bashio::log.info "Board: ${BOARD_TYPE}, Chip: ${CHIP_TYPE}"
bashio::log.info "Rotation: ${DISPLAY_ROTATION}, Refresh: ${REFRESH_INTERVAL}s, Page: ${PAGE_DURATION}s"
bashio::log.info "Page durations: summary=${PAGE_DURATION_SUMMARY}, details=${PAGE_DURATION_DETAILS}, clock=${PAGE_DURATION_CLOCK}, entities=${PAGE_DURATION_ENTITIES}, graph=${PAGE_DURATION_GRAPH}, alert=${PAGE_DURATION_ALERT}"
bashio::log.info "Clock page: ${SHOW_CLOCK_PAGE}, Details: ${SHOW_DETAILS_PAGE}, Graph: ${SHOW_GRAPH_PAGE}"
bashio::log.info "Entity cache TTL: ${ENTITY_CACHE_TTL}s, Supervisor cache TTL: ${SUPERVISOR_CACHE_TTL}s"
bashio::log.info "Page order: ${PAGE_ORDER}, Alert position: ${ALERT_PAGE_POSITION}, Night mode: ${NIGHT_MODE_ENABLED} (${NIGHT_MODE_START}-${NIGHT_MODE_END})"
bashio::log.info "Starting OLED display script..."

python3 /system_info.py