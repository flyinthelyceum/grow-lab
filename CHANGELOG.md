# Changelog

All notable changes to this project are documented in this file.

## 2026-03-12

### Added
- Configurable irrigation pump backend via `irrigation.pump_controller` (`gpio` or `esp32`) with validation and tests.
- Explicit pump-controller guidance in irrigation and V0 runbook docs.
- Phase 1 blocker notes documenting current ESP32-S3-N16R8 serial runtime issue.
- Additional config tests for pump backend parsing and validation.

### Changed
- `growlab pump` controller selection now follows config instead of implicit fallback behavior.
- Phase 1 setup instructions now use Pi extras install (`pip install -e ".[pi]"`) to ensure `RPi.GPIO` availability.
- ESP32 serial connection adds a short post-open delay for USB CDC stability.
- ESP32 firmware startup no longer blocks indefinitely waiting for `Serial` readiness.

### Notes
- ESP32 flashing is confirmed, but runtime serial command responses remain unresolved on tested ESP32-S3-N16R8 USB paths.
- Phase 1 execution should proceed on DS18B20 + GPIO relay pump path while ESP32 serial profile is finalized in Phase 2.
