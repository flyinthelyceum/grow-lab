# V0 Bench Prototype

## Objective

Bring the hardware online in a safe, incremental sequence that matches actual part availability, while using the existing software stack exactly as implemented.

This runbook replaces the older software-build-first commissioning flow.

## Current Software Reality

- Core stack is already built and tested (`284` tests passing locally).
- Drivers/services available now: DS18B20, GPIO relay pump, BME280, ESP32 serial, camera, OLED, polling/irrigation/lighting/capture/display services, dashboard, CLI.
- Intentionally pending for Phase 3: `ezo_ph`, `ezo_ec`, and `soil_moisture` drivers.
- Pump control for V0 stays on Pi GPIO relay. ESP32 handles LED PWM only.

### Known Blocker (as of March 12, 2026) — RESOLVED March 13

- **Root causes (3):**
  1. PlatformIO used `board = esp32dev` — wrong toolchain and board defaults for ESP32-S3.
  2. Arduino `Serial` targets UART0/HWCDC, not the USB-Serial/JTAG controller used by the Freenove board. Firmware rewritten with `JtagSerial` wrapper using low-level FIFO.
  3. pyserial's default DTR assertion resets the S3 into download mode. Driver now opens with `dtr=False, rts=False`.
- **Fix verified:** All serial commands (`STATUS`, `LIGHT`, `PUMP`) working on Pi via `/dev/ttyACM0`.
- **Flash note:** After flashing via esptool, the ESP32 enters download mode. Unplug/replug USB to boot into application firmware. BOOT/RESET buttons on this board are unresponsive.

### Session Handoff (end of day: March 13, 2026)

- Completed:
  - ESP32-S3 serial blocker fully resolved (3 root causes — see changelog).
  - Firmware v0.2.1 flashed and validated on Pi. Heartbeat LED (GPIO48) confirms firmware alive.
  - All serial commands working: STATUS, LIGHT, PUMP.
  - Python driver updated with DTR/RTS fix.
  - Phase 1 and Phase 2 serial prerequisite cleared.
  - DS18B20 reading stable (~22°C reservoir temp).
  - GPIO17 relay tested — 3× consecutive 5s pump wet tests passed.
  - `growlab start` soak running on Pi (PID 4484, log at `~/growlab-soak.log`).
    - 34 readings logged in first ~4 hours, no errors.
    - Irrigation scheduler active (08:00, 14:00, 20:00 — 10s pulses).
- Hardware note:
  - Board is Freenove ESP32-S3 WROOM N8R8 (8MB flash, 8MB PSRAM), not N16R8 as previously noted.
  - BOOT/RESET buttons unresponsive — power cycle via USB cable for resets.

### Session Handoff (end of day: March 14, 2026)

- Completed:
  - Pi rewired to RSP-GPIO-8 breakout board.
  - March 13 soak failure diagnosed: IrrigationService not wired into main.py at time of launch. Fixed in commit `1ae9f9f`.
  - Phase 2 hardware brought online: BME280, OLED (SH1106), Pi Camera Module 3, 8-channel relay.
  - OLED driver fixed: GME12864 uses SH1106 controller (not SSD1306). Added configurable `controller` field, `persist=True`.
  - Camera driver fixed: Pi OS Bookworm uses `rpicam-still` not `libcamera-still`.
  - GPIO relay driver fixed: SunFounder 8-channel board uses active-low logic.
  - Display service wired into main loop with 4 rotating pages (values, system, irrigation, sparkline).
  - Display shows human-readable labels and Fahrenheit (Air, Humidity, H2O Temp).
  - Camera capture triggers after each pump pulse (no fixed timer).
  - Full preflight passed: all sensors, pump relay, camera, OLED verified.
  - Pump-triggered camera capture verified end-to-end.
  - Overnight soak #2 launched (PID 5199, log at `~/growlab-soak.log`).
- Pi access: `ssh jared@10.80.1.161`, user `jared`, venv at `~/grow-lab/.venv`.
- Config on Pi: `~/grow-lab/config.toml` (camera enabled, display enabled with `controller = "sh1106"`).
- Next session priorities:
  1. Check soak #2 results: `tail -100 ~/growlab-soak.log` and `growlab db info`.
  2. Verify pump fired at 08:00, 14:00, 20:00 UTC with camera captures in `~/grow-lab-data/images/`.
  3. Review BME280 data for stability — compare air temp vs water temp trends.
  4. Check Phase 2 exit criteria boxes.
  5. Remaining Phase 2 work: ESP32 LED PWM (waiting on LED strips/Mean Well driver).
  6. Begin Phase 3 planning if Phase 2 exit criteria met (minus LED, which is hardware-blocked).

### Session Handoff (end of day: March 17, 2026)

- Completed:
  - Dashboard demo path tightened around the current `GROWLAB` UI.
  - Route/browser test expectations updated from the older dashboard branding and `p5` assumptions to the current Canvas-based implementation.
  - Dashboard camera panel now handles empty and file-missing states more gracefully.
  - ROOT and PLANT panels now explain pending instrumentation instead of presenting unexplained blanks.
  - Art Mode now exposes lightweight live readouts for temperature, humidity, and last water event to support walkthroughs.
- Demo checklist:
  - Observatory route `/` remains the main scientific dashboard.
  - Art route `/art` renders the radial Canvas visualization.
  - WebSocket/API behavior stays unchanged for existing clients.
  - Latest camera image is now served through the dashboard API rather than an assumed static directory.
- Current blocker:
  - Remaining pH, EC, and soil moisture hardware is still in shipping transit, so ROOT/PLANT completeness is intentionally deferred.
  - In this workspace, no `config.toml` is present and the default CLI database path is empty, so local demo commands need the real Pi config/database to show live data.
- Last known-good commands:
  - `growlab dashboard --host 0.0.0.0 --port 8000`
  - `pytest tests/unit/test_dashboard_app.py tests/unit/test_dashboard_api.py tests/unit/test_dashboard_api_downsampled.py tests/unit/test_dashboard_ws.py tests/e2e/test_dashboard_pages.py -q`
  - `pytest tests/browser/test_browser_dashboard.py -v`
- Next first step:
  - Run the dashboard on the Pi with the real `config.toml`, open `/` and `/art`, and capture a short punch-list of anything still awkward in the live demo.

### Session Handoff (end of day: March 18, 2026)

- Completed:
  - Full repo audit pass completed for off-hardware work.
  - Default `pytest -q` baseline restored and now passes locally again.
  - `growlab start --config <path>` now respects the provided config path.
  - Observatory history fetches now use the documented downsampled API path.
  - Added `config.demo.toml` for isolated local dashboard/art review using repo-local demo data under `./.demo-data/`.
  - Retired standalone `demo.html` and `art-demo.html` snapshots in favor of the real app-backed demo workflow.
- Current blocker:
  - No Pi network access from the current location, so live deployment, service inspection, and hardware validation are paused until the next on-network session.
- Last known-good commands:
  - `growlab --config config.demo.toml db seed-demo --hours 24`
  - `growlab --config config.demo.toml dashboard --host 127.0.0.1 --port 8000`
  - `pytest -q`
- Next first step:
  - Use the local demo profile to continue observatory/art review loops and screenshot-driven refinement without touching the Pi database.

## Phase 1 (Today): Pi + DS18B20 + Relay + Pump + Fan

Hardware on hand: Pi 4, DS18B20, 5V relay, Micra Plus pump, Noctua fan.

### 1.1 Bench Layout (Dry)

- Separate into electrical and wet zones.
- Keep Pi/relay above any water path.
- Route drip loops on cables crossing zones.
- Run Noctua fan always-on (no software control in V0).

### 1.2 Pi Setup + Deploy

```bash
sudo raspi-config
# Enable I2C + 1-Wire, then reboot

ls /dev/i2c-1
ls /sys/bus/w1/devices/

git clone <repo> grow-lab
cd grow-lab
python -m venv .venv
source .venv/bin/activate
pip install -e ".[pi]"
# If extras are unavailable in your environment, install GPIO directly:
# pip install RPi.GPIO
cp config.example.toml config.toml
```

Update `config.toml` for Phase 1:

Verify relay GPIO is configured (GPIO pump control is the default behavior):
```toml
[irrigation]
relay_gpio = 17
```

Set these to `enabled = false`:
- `sensors.bme280`
- `sensors.ezo_ph`
- `sensors.ezo_ec`
- `sensors.soil_moisture`
- `camera`
- `display`

```bash
growlab sensor scan
```

### 1.3 DS18B20 Wiring + Verify

- `3.3V` -> Pin 1
- `GND` -> Pin 6
- `DATA` -> GPIO4 (Pin 7)
- 4.7k resistor between GPIO4 and 3.3V

```bash
ls /sys/bus/w1/devices/28-*
growlab sensor scan
growlab sensor read ds18b20_<device_id>
```

Expected: plausible room/reservoir temp; avoid persistent `85C` reading (usually wiring/pull-up issue).

### 1.4 Relay Dry Test (No Pump Load)

- GPIO17 (Pin 11) -> relay IN
- 5V (Pin 2) -> relay VCC
- GND (Pin 9) -> relay GND

```bash
growlab pump on --max-seconds 5
growlab pump off
```

Expected: audible relay click and `Using GPIO relay on pin 17`.

### 1.5 Pump Wet Test

- Wire pump power through relay switch contacts.
- Fill reservoir with plain water.
- Route tubing through emitter -> media -> drain tray.
- Submerge DS18B20 probe in reservoir.

```bash
growlab pump pulse 5
growlab sensor read ds18b20_<device_id>
growlab pump schedule
```

### 1.6 Start + Soak

```bash
growlab start
```

After soak period:

```bash
growlab db info
growlab db export --type readings --sensor ds18b20_<device_id> --limit 100
# optional: growlab db export --type readings --format csv --output /tmp/ds18b20.csv

growlab dashboard
```

### Phase 1 Exit Criteria

- [x] Bench layout is physically safe (zones + drip loops).
- [x] DS18B20 detected and reading plausible values.
- [x] Relay switches reliably in CLI tests.
- [x] Pump circulates water with no leaks.
- [x] `growlab start` runs for hours without crashing.
- [x] DS18B20 data present in DB/dashboard.

## Phase 2 (Days 2-4): BME280, ESP32+LEDs, OLED, Camera

Rule: add one device at a time, verify, then continue.

### 2.1 BME280

```bash
sudo i2cdetect -y 1
# expect 0x76 (or configured address)
```

Set `sensors.bme280.enabled = true`.

```bash
growlab sensor scan
growlab sensor read bme280
```

### 2.2 ESP32 + LED PWM

- Flash firmware from `firmware/esp32/`.
- Connect ESP32 over USB serial.
- Wire ESP32 PWM pin to LED driver dimming input.

```bash
ls /dev/ttyUSB0 /dev/ttyACM0
growlab light set 50
growlab light set 200
growlab light set 0
growlab light status
```

Decision lock: pump remains GPIO relay controlled.
If ESP32 serial control is not responding, keep `lighting` disabled and continue non-ESP32 tasks until the board profile/runtime serial path is finalized.

### 2.3 OLED

Wire OLED onto I2C bus (with BME280), usually `0x3C`.

```bash
sudo i2cdetect -y 1
# expect 0x3C plus sensor addresses
```

Set `display.enabled = true`.

```bash
growlab display status
growlab display test
```

### 2.4 Pi Camera

Attach CSI ribbon cable, set `camera.enabled = true`.

```bash
growlab camera capture
growlab camera list
growlab camera status
```

### 2.5 24-Hour Integrated Soak (No Plant)

```bash
growlab start
```

Monitor for sensor stability, leaks, LED heat, and service reliability.

### Phase 2 Exit Criteria

- [x] BME280 detected and stable.
- [ ] ESP32 controls LED PWM smoothly. *(blocked — waiting on LED strips and Mean Well driver)*
- [x] OLED reachable and renders test screen.
- [x] Camera captures valid images.
- [ ] Full 24-hour no-plant soak completes cleanly. *(soak #2 running overnight — check March 15)*

## Phase 3 (Days 4-7): Atlas pH/EC + STEMMA Soil

Hardware: Atlas EZO-pH + probe, Atlas EZO-EC + probe, STEMMA soil sensor.

### 3.0 Build Missing Drivers Just-in-Time

Build only when hardware is present and testable:

1. `pi/drivers/stemma_soil.py`
2. `pi/drivers/ezo_ph.py`
3. `pi/drivers/ezo_ec.py`

For each driver:
- Write tests first.
- Implement driver.
- Wire into `build_registry()`.

### 3.0.1 i3 InterLink Installation

The Atlas Scientific i3 InterLink is a Pi HAT carrier board that provides 5 EZO circuit slots (2 electrically isolated, 3 non-isolated) over I2C. It passes through all GPIO pins.

1. **Power off the Pi** before installing.
2. Seat the i3 InterLink onto the Pi's 40-pin GPIO header.
3. Snap EZO-pH and EZO-EC circuits into the isolated slots (isolation prevents sensor cross-talk in shared nutrient solution).
4. Power on and verify the carrier is detected:

```bash
sudo i2cdetect -y 1
# The i3 InterLink itself doesn't have an address — look for
# the EZO circuits at their configured addresses (default UART mode
# won't show; switch to I2C first)
```

### 3.1 Atlas UART -> I2C Mode Switch

Atlas EZO circuits ship in UART mode; switch each to I2C before use. The `growlab sensor ezo-setup` CLI automates this:

```bash
# Connect EZO circuit to USB-UART adapter (or use i3 InterLink UART header)
growlab sensor ezo-setup --sensor ph --port /dev/ttyUSB0
growlab sensor ezo-setup --sensor ec --port /dev/ttyUSB0

# Verify on I2C bus
sudo i2cdetect -y 1
# expect 0x63 (pH) and/or 0x64 (EC)
```

Alternative manual method:
```bash
minicom -D /dev/serial0 -b 9600
# send per-board command, e.g. I2C,99 or I2C,100
```

### 3.2 pH Calibration

- Calibrate with pH 4.0 / 7.0 / 10.0 buffers.
- Rinse probe between buffers.
- Keep probe wet in storage solution.

```bash
growlab sensor read ezo_ph
```

### 3.3 EC Calibration

- Calibrate with known reference conductivity solution.

```bash
growlab sensor read ezo_ec
```

### 3.4 STEMMA Soil

Wire on I2C (typically `0x36`) and verify wet/dry response.

```bash
growlab sensor read soil_moisture
```

### Phase 3 Exit Criteria

- [ ] Soil moisture driver built/tested and sensor reading changes with moisture.
- [ ] EZO-pH driver built/tested and calibrated readings are within tolerance.
- [ ] EZO-EC driver built/tested and calibrated readings match reference.
- [ ] Registry reports all three sensors available when connected.

## Phase 4 (Days 7-10): Full Integration, Nutrients, Plant

### 4.1 Full 24-Hour Water-Only Soak

```bash
growlab start
```

Run with all hardware enabled. Watch for pH/EC drift, grounding noise, and service stability.

### 4.2 Nutrient Introduction

- Mix mild nutrient solution.
- Target pH 5.8-6.2.
- Confirm pH/EC stability for at least 4 hours before adding plant.

### 4.3 Plant Introduction

- Start conservative (moderate light, standard irrigation).
- Adjust one variable at a time during the first week.

### Phase 4 Exit Criteria

- [ ] Full-system 24-hour soak passes with all devices online.
- [ ] Nutrient reservoir remains stable in target pH/EC range.
- [ ] Plant shows no stress in first 48 hours.
- [ ] System can run unattended with stable telemetry.

## Remote Access: Tailscale Setup

Install Tailscale on the Pi to enable SSH and dashboard access from home (or anywhere) without port forwarding or router changes.

### On the Pi

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Follow the browser link to authenticate. The Pi gets a stable `100.x.x.x` Tailscale IP.

### On your Mac

```bash
brew install tailscale
```

Or install the macOS app from tailscale.com/download. Authenticate with the same account.

### Usage

```bash
# SSH from anywhere
ssh jared@<pi-tailscale-ip>

# Dashboard from anywhere
open http://<pi-tailscale-ip>:8000
```

Tailscale uses WireGuard encryption, works behind NAT on both sides, and is free for personal use (up to 100 devices). MagicDNS gives the Pi a hostname like `growlab-pi.tail<net>.ts.net` so you don't need to memorize IPs.

## Key Decisions (Locked)

- Pump controller: GPIO relay for V0.
- ESP32 role: LED PWM only.
- Driver timing: build pH/EC/soil drivers only when hardware arrives.
- Nutrients: only after pH/EC validation.
- Fan control: always-on in V0.

## What Not To Do

- Do not pre-build untestable hardware drivers.
- Do not move pump control to ESP32 in V0.
- Do not enable hardware in config that is not physically connected.
- Do not add nutrients before pH/EC sensors are validated.
- Do not add multiple new devices at the same time during bring-up.
