# Changelog

All notable changes to this project are documented in this file.

## 2026-03-13

### Fixed
- ESP32 serial timeout resolved: PlatformIO board profile updated from `esp32dev` to `esp32-s3-devkitc-1` with USB CDC build flags (`ARDUINO_USB_CDC_ON_BOOT=1`, `ARDUINO_USB_MODE=1`).
- LEDC PWM driver updated to new ESP32 Arduino core API (`ledcAttach` replaces deprecated `ledcSetup`/`ledcAttachPin`).
- Default serial port changed from `/dev/ttyUSB0` to `/dev/ttyACM0` (native USB CDC path for ESP32-S3).

### Notes
- Firmware rebuild and flash required on Pi to activate the fix.
- Validate with `miniterm` raw serial test, then `growlab light status`.

## 2026-03-12

### Added
- Configurable irrigation pump backend via `irrigation.pump_controller` (`gpio` or `esp32`) with validation and tests.
- Explicit pump-controller guidance in irrigation and V0 runbook docs.
- Phase 1 blocker notes documenting current ESP32-S3-N16R8 serial runtime issue.
- Additional config tests for pump backend parsing and validation.
- End-of-day handoff logging sections in V0/Phase 1 docs, including a saved March 12, 2026 status snapshot and next-session priority.

### Changed
- `growlab pump` controller selection now follows config instead of implicit fallback behavior.
- Phase 1 setup instructions now use Pi extras install (`pip install -e ".[pi]"`) to ensure `RPi.GPIO` availability.
- ESP32 serial connection adds a short post-open delay for USB CDC stability.
- ESP32 firmware startup no longer blocks indefinitely waiting for `Serial` readiness.

### Notes
- ESP32 flashing is confirmed, but runtime serial command responses remain unresolved on tested ESP32-S3-N16R8 USB paths.
- Phase 1 execution should proceed on DS18B20 + GPIO relay pump path while ESP32 serial profile is finalized in Phase 2.
