# V0 Bench Prototype

## Objective

Bring the hardware online in a safe, incremental sequence that matches actual part availability, while using the existing software stack exactly as implemented.

This runbook replaces the older software-build-first commissioning flow.

## Current Software Reality

- Core stack is already built and tested (`284` tests passing locally).
- Drivers/services available now: DS18B20, GPIO relay pump, BME280, ESP32 serial, camera, OLED, polling/irrigation/lighting/capture/display services, dashboard, CLI.
- Intentionally pending for Phase 3: `ezo_ph`, `ezo_ec`, and `soil_moisture` drivers.
- Pump control for V0 stays on Pi GPIO relay. ESP32 handles LED PWM only.

### Known Blocker (as of March 12, 2026)

- ESP32-S3-N16R8 flashing succeeds from the Pi, but runtime serial command responses are still timing out.
- `growlab light status` / `growlab light set` currently fail with `no response (timeout)` on tested USB ports.
- V0 execution continues with DS18B20 + GPIO relay pump path in Phase 1 while ESP32 serial profile is resolved in Phase 2.

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

- [ ] Bench layout is physically safe (zones + drip loops).
- [ ] DS18B20 detected and reading plausible values.
- [ ] Relay switches reliably in CLI tests.
- [ ] Pump circulates water with no leaks.
- [ ] `growlab start` runs for hours without crashing.
- [ ] DS18B20 data present in DB/dashboard.

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

- [ ] BME280 detected and stable.
- [ ] ESP32 controls LED PWM smoothly.
- [ ] OLED reachable and renders test screen.
- [ ] Camera captures valid images.
- [ ] Full 24-hour no-plant soak completes cleanly.

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

### 3.1 Atlas UART -> I2C Mode Switch

Atlas boards ship in UART mode; switch each board before I2C use.

```bash
minicom -D /dev/serial0 -b 9600
# send per-board command, e.g. I2C,99 or I2C,100
sudo i2cdetect -y 1
# expect 0x63 (pH) and/or 0x64 (EC)
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
