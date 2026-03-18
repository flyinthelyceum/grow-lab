# Changelog

All notable changes to this project are documented in this file.

## 2026-03-18

### Fixed
- Default `pytest -q` collection restored by aligning display tests to the current `render_system_page` API instead of the removed `render_status_page` name.
- `growlab start --config <path>` now honors the provided config path instead of reloading defaults.
- Observatory history fetches now use the documented downsampled REST endpoint rather than the raw readings route.

### Added
- `config.demo.toml` for safe off-hardware dashboard work with repo-local demo data under `./.demo-data/`.

### Changed
- README and architecture docs now describe the current local demo workflow, browser-test requirements, and the downsampled-history data path used by both dashboard views.
- Retired standalone `demo.html` and `art-demo.html` snapshots in favor of the real FastAPI-backed demo workflow.

## 2026-03-17

### Added
- **Web Dashboard (Observatory view)** — 5-panel layout (LIGHT, WATER, AIR, ROOT, PLANT) with live sensor values, D3.js charts, and WebSocket updates.
  - LIGHT panel: StepAfter chart with photoperiod band.
  - WATER panel: EKG-style pulse timeline of irrigation events.
  - AIR panel: dual-axis CatmullRom chart (temperature + humidity overlaid).
  - ROOT panel: stacked sparklines for pH and EC with target range bands.
  - PLANT panel: soil moisture D3 arc gauge + camera feed.
  - Time window selector: 1H / 24H / 7D.
  - Per-panel optimal range indicators and human-readable timestamps.
  - Footer with WebSocket status, sensor count, and ART mode link.
- **Art Mode (generative visualization)** — full-screen Canvas 2D radial visualization driven by live sensor data.
  - Radial thermal ring: 24h temperature mapped to color-graded wedges with radial gradients.
  - Humidity breathing ring: teal-cyan band with sinusoidal opacity modulation.
  - Water pulse markers: bright cyan dots at irrigation event angles with pulsing halos.
  - Pressure atmosphere: colored radial gradient background with isobar rings.
  - Ambient particle system: 120 particles with lifecycle fade, sine-wave drift, breathing opacity.
  - Cross-layer hover system: center disc shows context-sensitive info with priority routing (water > humidity > temperature).
  - WebSocket integration for live temperature, pressure, and irrigation updates.
  - Re-fetches 24h history every 5 minutes.
- **EZO-pH driver** — Atlas Scientific EZO-pH I²C driver with calibration support.
- **EZO-EC driver** — Atlas Scientific EZO-EC I²C driver with temperature compensation.
- **ADS1115 soil moisture driver** — 16-bit ADC driver for DFRobot SEN0308 capacitive sensor.
- CSS typography scaling with fluid `clamp()` values, panel accent colors, value transitions, and responsive breakpoints.

### Changed
- Dashboard header renamed to "GROWLAB".
- All temperature values displayed in Fahrenheit across dashboard and art mode.
- All sensor labels use plain English names (Air, Humidity, H₂O Temp) instead of raw IDs.
- Dashboard camera panel now explains missing/stale capture states more clearly and loads the latest image via API-served file URLs instead of assuming a static captures mount.
- ROOT and PLANT panels now show sensor-availability notes so hardware-blocked fields read as pending instrumentation instead of silent blanks.
- Art Mode now includes a lightweight live readout for temperature, humidity, and last irrigation timing to make on-device walkthroughs easier.
- Art Mode thermal ring geometry now uses a calmer, more centered soft wobble with reduced radial deformation and stronger smoothing.

### Fixed
- Dashboard image serving path aligned with stored camera capture records through `/api/images/<filename>/file`.
- Dashboard route/browser tests updated to the current `GROWLAB` branding and Canvas-based art mode implementation.

### Added
- `growlab db seed-demo` command for generating synthetic 24h-friendly dashboard data, irrigation events, and a demo camera capture while hardware is still in transit.
- `deploy/systemd/growlab-dashboard.service` for running the dashboard persistently on the Pi via `systemd`.

## 2026-03-14

### Fixed
- OLED driver switched from SSD1306 to SH1106 controller (GME12864 modules). Added configurable `controller` field in DisplayConfig with `persist=True` to hold display content after process exit.
- Camera driver updated from `libcamera-still` to `rpicam-still` (Pi OS Bookworm naming). Falls back to legacy command for older OS versions.
- GPIO relay driver updated to support active-low relay modules (SunFounder 8-channel board). Initial pin state set correctly to prevent relay click on startup.
- Display sensor labels changed from raw IDs to human-readable names ("Air", "Humidity", "H2O Temp"). DS18B20 lookup uses prefix matching to handle serial-numbered sensor IDs.
- All temperature readings converted from Celsius to Fahrenheit on OLED display.
- OLED header renamed from "LIVING LIGHT" to "GROWLAB".
- Pump soak failure root cause identified: IrrigationService was not wired into `main.py` during the March 13 overnight run (fix committed same day but after soak launched).

### Added
- OLED display service wired into `main.py` startup/shutdown. Rotates through 4 pages every 5s: sensor values, system overview (uptime + subsystem status), irrigation schedule with last pump event, sparkline trend chart.
- Camera capture triggered after each pump pulse via `on_pulse_complete` callback in IrrigationService. No fixed-interval timer — captures only on irrigation events.
- `luma.oled` added to `[pi]` optional dependencies in `pyproject.toml`.
- MJPEG streaming server for camera aiming (`/tmp/mjpeg_server.py` — temporary, not committed).

### Validated (Phase 2 Hardware)
- BME280 detected and polling at 0x76 (air temp, humidity, pressure).
- DS18B20 stable at ~19.75°C (67.6°F).
- OLED (SH1106, GME12864) displaying on I²C 0x3C with all 4 page rotations confirmed.
- Pi Camera Module 3 (IMX708) capturing at 2304×1296 and 4608×2592 via rpicam-still.
- SunFounder 8-channel relay (active-low) switching pump on GPIO17.
- Pump-triggered camera capture verified end-to-end (pump fires → camera captures → image saved to DB).
- Overnight soak #2 launched: all sensors polling, irrigation at 08:00/14:00/20:00 UTC, camera on pump events, OLED rotating.

### Hardware Notes
- Rewired Pi to RSP-GPIO-8 breakout board (cleaner breadboard layout).
- GME12864 OLED confirmed as SH1106 controller, not SSD1306 — both init without error at 0x3C but only SH1106 renders pixels.
- SunFounder 8-channel relay uses active-low logic (LOW = relay ON). JD-VCC jumper must bridge to VCC for coil power from Pi 5V rail.
- Noctua NF-A12x25 PWM fan control deferred — runs at full speed through relay for V0. PWM/tach wires can connect directly to Pi GPIO when ready (3.3V logic compatible).
- User has thousands of ESP32-WROOM-32U modules available; current build uses ESP32-S3 N8R8 for native USB convenience but 32U is a drop-in replacement with UART bridge.

## 2026-03-13

### Fixed
- ESP32-S3 serial timeout fully resolved. Three root causes identified and fixed:
  1. PlatformIO board profile updated from `esp32dev` to `esp32-s3-devkitc-1`.
  2. Firmware rewritten to use USB-Serial/JTAG low-level FIFO (`usb_serial_jtag_ll`) instead of Arduino `Serial` (which targets UART0/HWCDC, not the JTAG CDC port).
  3. Python driver opens serial without DTR/RTS assertion to prevent the S3 from resetting into download mode.
- Default serial port changed from `/dev/ttyUSB0` to `/dev/ttyACM0` (native USB CDC path for ESP32-S3).
- Board default `ARDUINO_USB_MODE=1` overridden to `0` to prevent Arduino core from disabling USB-Serial/JTAG controller.

### Added
- `jtag_serial.h` — Stream-compatible wrapper for ESP32-S3 USB-Serial/JTAG hardware FIFO.
- Heartbeat blink on ESP32 onboard RGB LED (GPIO48) — dim green pulse every 2s confirms firmware is running.

### Changed
- `commands.cpp` refactored to accept a `Print&` output parameter instead of hardcoded `Serial`.
- Firmware version bumped to `0.2.1`.

### Validated (Phase 1 Hardware)
- DS18B20 reading stable at ~22°C (reservoir temp).
- GPIO17 relay switching reliably — audible click, pump runs on command.
- Pump wet test passed (3× consecutive 5-second runs, no issues).
- `growlab start` soak initiated — DS18B20 polling every 120s, irrigation scheduler active, data logging to SQLite on Pi.

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
