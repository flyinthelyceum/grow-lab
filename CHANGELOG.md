# Changelog

All notable changes to this project are documented in this file.

## 2026-03-24

### Added
- **AS7341 spectral light sensor driver** (`pi/drivers/as7341.py`) — fixed-address I2C spectral sensor at `0x39`. Emits `as7341_lux` plus `as7341_415nm`, `as7341_445nm`, `as7341_480nm`, `as7341_515nm`, `as7341_555nm`, `as7341_590nm`, `as7341_630nm`, `as7341_680nm`, `as7341_clear`, and `as7341_nir` in a single poll cycle. Unit tests cover availability, read success, and failure handling.
- **AS7341 config & registry** — sensor entry in `config.example.toml` (disabled by default), I2C address map, and auto-registration in `build_registry()`.
- **Lighting PWM logging** — `LightingScheduler._log_reading()` saves PWM values as `light_pwm` sensor readings on transitions, enabling dashboard chart history.
- **ESP32 reconnect & self-healing** — `ESP32Serial.reconnect()` method. `LightingScheduler` tracks consecutive failures and auto-reconnects after 3, preventing silent light-off on serial port loss.
- **systemd service for main process** (`deploy/systemd/growlab.service`) — `Type=notify` with `WatchdogSec=300`, start limits, dependency ordering with dashboard service.
- **Systemd watchdog heartbeat** in `pi/main.py` — sends `READY=1` on startup, `WATCHDOG=1` every 120s via `NOTIFY_SOCKET`.
- **Decoupled lighting scheduler** — creates independent ESP32 serial connection when pump uses GPIO relay, preventing serial port conflicts.

### Fixed
- **Dashboard LIGHT panel** — now displays live PWM data from `light_pwm` sensor readings (was showing stale/nonexistent data). Dynamic unit label (`lx` vs `PWM`) in HTML template. Cache-busting `?v=2` on `observatory.js`.
- **Light chart** — auto-detects AS7341 lux vs PWM data: smooth CatmullRom curve for lux, StepAfter for PWM. Dynamic Y-axis scaling and hover tooltips.
- **Lighting failure handling** — `_set_pwm` no longer updates `_current_pwm` on failure, forcing retry on next scheduler tick instead of silently accepting the failure.
- **Dashboard service hardening** — added `After=growlab.service`, `Restart=always`, start limits.

### Docs
- AS7341 added to BOM, SENSOR_STACK I2C address table, and WIRING_&_BUSES I2C device list.

## 2026-03-20

### Added
- **Dream Mode** (`/dream`) — Anadol-inspired WebGL particle visualization using Three.js. 50K additive-blended point sprites driven by a 3D curl noise flow field. Sensor data modulates visuals in real time: temperature→particle color (blue→teal→amber), humidity→particle density, pressure→flow amplitude, irrigation→cyan burst events. UnrealBloomPass post-processing for glow. Auto-orbit perspective camera. 60fps animation loop with visibility pause. Auto-downscales particle count on weaker GPUs.
- `/dream` route added to dashboard. Nav links from Observatory and Art views.
- 7 new e2e tests for Dream Mode page.

### Fixed
- **Dream Mode temperature conversion** — BME280 reports unit as `°C`, not `"celsius"`. Conversion logic now assumes Celsius unless unit is explicitly `°F` or `"fahrenheit"`.

### Validated (Phase 3 Hardware)
- Atlas EZO-pH circuit online at I2C 0x63 via i3 InterLink HAT. 3-point calibration: pH 4.00→3.998, 7.00→6.995, 10.00→10.011. Polling every 300s.
- Atlas EZO-EC circuit online at I2C 0x64 via i3 InterLink HAT. 2-point calibration: 12,880 µS/cm and 80,000 µS/cm. Polling every 300s.
- EZO circuits switched from UART to I2C mode via PGND-TX pin short (no USB-UART adapter needed).
- Reservoir baseline: pH 8.3, EC 1,529 µS/cm in plain water.
- All 4 sensors passing `growlab sensor validate-all`: BME280, DS18B20, EZO-pH, EZO-EC.

### Infrastructure
- **Tailscale** installed on grow-lab Pi (100.77.46.126). SSH and dashboard accessible from anywhere.
- `httpx` added to Pi venv (required by NotificationService at runtime).

## 2026-03-19

### Fixed
- **Irrigation pump safety** — pump state flags (`_pump_active`, `_last_activation`) now set only after hardware confirms success. `try/finally` ensures pump-off even if a DB write fails mid-pulse. Concurrent pulse guard rejects overlapping activations.
- **Fan error visibility** — fan control loop exceptions upgraded from `debug` to `error` with traceback. Silent fan failure on a grow system is a plant-killing heat event.
- **XSS in alert timeline** — tooltip switched from D3 `.html()` to safe DOM construction (`.textContent`). Alert descriptions no longer interpreted as HTML.
- **EZO UART port safety** — `serial.Serial` constructor moved into `with` context manager so port-open failures don't cause `NameError` in cleanup.
- **SMTP password leak** — `EmailConfig.__repr__` now redacts `smtp_password` so logging the config object doesn't expose credentials.
- **GPIO.setmode collision** — extracted shared `_gpio.py` module; `setmode(BCM)` called once and cached instead of repeated per-call in both `fan_pwm.py` and `gpio_relay.py`.
- **Service start() guards** — `AlertService` and `FanService` use `is_running` property instead of `_task is not None`, allowing restart after a crashed task.
- **Alert logging** — rule evaluation errors and `on_alert` callback exceptions upgraded from `debug` to `warning` so they appear in production logs.
- **Notification service** — shared `httpx.AsyncClient` (was creating one per webhook call); `raise_for_status()` on webhook responses (was treating 4xx/5xx as success); cooldown recorded on attempt not success (prevents notification storm on repeated failures).
- **WebSocket interval leak** — art mode `setInterval` for WS updates now cleared on close before reconnect, preventing accumulated duplicate intervals.
- **Midnight sliver gap** — radial and humidity rings add 0.003 radian overlap per wedge to eliminate sub-pixel rendering gaps at midnight boundary.

### Added
- **Art view distance-based hover** — when mouse is in the overlap zone between temperature and humidity rings, the closer ring wins hover priority instead of humidity always dominating. Water markers still take top priority.
- **Observatory chart hover** — crosshair + tooltip on all data graphs (air temp/humidity, pH, EC, light). Vertical guide line with colored dots on data lines and auto-positioned tooltip showing time and values. Shared `chart-hover.js` utility supports single and dual-axis charts.

### Added
- **Fan duty override** — `POST /api/fan/override` accepts `{"duty": 0-100}` for manual control or `{"mode": "auto"}` to resume temperature ramp. FanService tracks override state; control loop skips temp calculation when override is active. Returns 503 when fan service is unavailable (standalone dashboard mode).
- **WebSocket server-push for alerts** — new `ConnectionManager` maintains active WebSocket connections and broadcasts alert events in real time. AlertService accepts an `on_alert` async callback, fired on every warning/critical transition. Dashboard JS handles `{"type": "alert"}` push messages alongside existing poll responses.
- **Alert history timeline** — D3.js horizontal dot timeline strip between alert banner and main grid. Warning dots in amber, critical in red, with hover tooltips showing description and timestamp. Fetches `/api/alerts?limit=100`, refreshes every 60s.
- **Gallery lightbox** — clicking a capture thumbnail opens a full-screen overlay instead of replacing the camera feed inline. Close by clicking outside or the CLOSE button.
- **Gallery empty state** — "No captures yet" placeholder shown when no images are available.
- 18 new unit tests: fan override (6), connection manager (6), alert callback (2), API endpoint (4).
- **Notification service** — `NotificationService` dispatches alert events via webhook (POST JSON) and email (SMTP) channels with per-sensor cooldown to prevent notification storms. Configured via `[notifications]`, `[notifications.webhook]`, and `[notifications.email]` in config.
- **EZO UART mode-switch driver** — `ezo_uart.py` sends `I2C,<addr>` command over UART to switch Atlas EZO sensors from UART to I2C mode.
- **`growlab sensor ezo-setup`** CLI command — interactive UART→I2C mode switch for EZO pH/EC sensors with automatic I2C bus verification after reboot.
- **`growlab sensor validate-all`** CLI command — scans all hardware buses, reads every detected sensor, and reports pass/fail with human-readable values (temperatures in °F).
- 23 new unit tests: EZO UART driver (7), notification service (16).

### Changed
- `create_app()` now accepts optional `fan_service` and `connection_manager` parameters for runtime wiring.
- WebSocket route registers/unregisters connections with ConnectionManager on connect/disconnect.
- `main.py` wires alert callback from AlertService to ConnectionManager broadcast and NotificationService dispatch.
- AlertService now passes `sensor_id` as event metadata for per-sensor notification cooldown.
- `httpx` moved from dev to core dependencies (used by webhook notifications at runtime).

## 2026-03-18

### Added
- **AlertService** wired into `growlab start` — monitors BME280 temperature, humidity, EZO-pH, and EZO-EC against configurable threshold rules. Logs `alert_warning` and `alert_critical` system events on state transitions with automatic deduplication (fires once per transition, not per poll). First live alert caught immediately: humidity critical at 26.1%.
- **FanService** wired into `growlab start` behind `fan.enabled` config flag — polls air temperature every 30s and adjusts Noctua NF-A12x25 PWM duty cycle along a linear ramp (20–100% across 70–85°F). Validated live on Pi at GPIO 18 with 12V supply.
- **LightingScheduler** wired into `growlab start` as a background service — runs photoperiod schedule with sunrise/sunset ramps when ESP32 is the pump controller (provides LED PWM). Logs info message when ESP32 is not connected.
- Camera capture timing changed from `on_pulse_complete` (after pump off) to `on_pulse_start` with 3-second delay (while relay LED is still lit). Confirmed via camera capture showing relay LED active.
- `on_pulse_start` callback and `pulse_start_delay` parameter added to `IrrigationService.pulse()` with error isolation — callback failure does not prevent pump shutoff.
- 4 new tests for pulse-start callback: fires during active window, skipped for short pulses, error isolation, coexistence with `on_pulse_complete`.

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
