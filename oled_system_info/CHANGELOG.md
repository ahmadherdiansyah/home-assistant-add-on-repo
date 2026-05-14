# Changelog

## [2.3.0] - 2026-05-14

### Changed
- Minor version bump

## [2.2.1] - 2026-05-14

### Fixed
- Updated display rendering for SSD1306 128x64 resolution
- Expanded text layout to use full 64px display height

## [2.2.0] - 2026-05-14

### Added
- Configurable display rotation
- Configurable refresh interval, page duration, and startup delay
- Optional toggles for the details page and CPU graph page

## [2.1.0] - 2026-05-14

### Added
- Rotating display pages that switch every 10 seconds
- Additional system stats for temperature, disk usage, and uptime
- Compact CPU history graph on the OLED display

## [2.0.2] - 2025-02-04

### Fixed
- Linting issues

## [2.0.0] - 2025-02-04

### Removed
- Removed deprecated architectures

## [1.0.1] - 2025-02-04

### Added
- Logo and icon

### Fixed
- Linting issues

## [1.0.0] - 2025-02-03

### Added
- Initial release
- Support for SSD1306 OLED display (128x32)
- System information display (IP, hostname, CPU, memory)
- GPIO button control
- Reboot functionality (long press ~8 seconds)
- Shutdown functionality (long press ~12 seconds)
- LED indicator support
- Auto-start on boot