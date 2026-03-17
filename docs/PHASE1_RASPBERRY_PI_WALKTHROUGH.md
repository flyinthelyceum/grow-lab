# Phase 1 Raspberry Pi Walkthrough (Pi + DS18B20 + Relay + Pump + Fan)

Use this as the live checklist on the Pi terminal. Run steps in order. Do not skip safety checks.

## Current Blocker Note (as of March 12, 2026)

- ESP32-S3-N16R8 is currently not returning runtime serial responses to `growlab` commands after flashing.
- This does not block Phase 1. Continue with DS18B20 + GPIO relay pump bring-up.
- Defer ESP32 lighting control verification to Phase 2 blocker resolution.

## 0) Safety and Bench Prep (No Power to Pump Yet)

1. Separate bench into:
- Electrical zone: Pi, relay, breadboard, power supplies.
- Wet zone: reservoir, tubing, pot/media, drain tray.

2. Confirm:
- Pi and relay are physically above any water path.
- Cables crossing zones have drip loops.
- No exposed mains wiring near wet zone.
- Noctua fan is powered and spinning continuously.

Pass condition: bench is dry, organized, and safe to proceed.

## 1) Pi Interface Enablement

On the Pi:

```bash
sudo raspi-config
```

Enable:
- `Interface Options` -> `I2C` -> Enable
- `Interface Options` -> `1-Wire` -> Enable

Reboot:

```bash
sudo reboot
```

After reconnecting:

```bash
ls /dev/i2c-1
ls /sys/bus/w1/devices/
```

Pass condition:
- `/dev/i2c-1` exists
- `/sys/bus/w1/devices/` exists

## 2) Project Setup

```bash
cd ~
git clone <repo-url> grow-lab
cd grow-lab
python -m venv .venv
source .venv/bin/activate
pip install -e ".[pi]"
# If extras are unavailable in your environment, install GPIO directly:
# pip install RPi.GPIO
cp config.example.toml config.toml
```

Edit config for Phase 1:

```bash
nano config.toml
```

Set these blocks to `enabled = false`:
- `[sensors.bme280]`
- `[sensors.ezo_ph]`
- `[sensors.ezo_ec]`
- `[sensors.soil_moisture]`
- `[camera]`
- `[display]`

Keep enabled:
- `[sensors.ds18b20]`
- `[irrigation]`

Sanity check CLI:

```bash
growlab --help
growlab sensor scan
```

Pass condition: command runs; no crash.

## 3) DS18B20 Wiring and Validation

Power off Pi before wiring.

Wire DS18B20:
- Red -> `3.3V` (Pin 1)
- Black -> `GND` (Pin 6)
- Data -> `GPIO4` (Pin 7)
- Add 4.7k resistor between GPIO4 and 3.3V

Boot Pi and validate:

```bash
ls /sys/bus/w1/devices/28-*
growlab sensor scan
```

Grab the DS18B20 id from scan output and read it:

```bash
growlab sensor read ds18b20_<device_id>
```

Pass condition:
- sensor is detected
- temperature is plausible (not stuck at `85C`)

If `85C` persists: recheck resistor value and data wire continuity.

## 4) Relay Dry Test (Pump NOT Connected to Relay Contacts)

Power off Pi before wiring.

Wire relay control side:
- Pi GPIO17 (Pin 11) -> Relay IN
- Pi 5V (Pin 2) -> Relay VCC
- Pi GND (Pin 9) -> Relay GND

Boot and test:

```bash
growlab pump on --max-seconds 5
growlab pump off
```

Pass condition:
- audible click on ON/OFF
- output indicates GPIO path (for example, `Using GPIO relay on pin 17`)

Stop if relay does not switch reliably.

## 5) Pump Wet Test

Now connect pump power through relay switch contacts (COM/NO as intended).

Wet-side prep:
- Fill reservoir with plain water
- Place pump in reservoir
- Connect tubing -> emitter -> pot/media -> drain tray
- Submerge DS18B20 probe in reservoir water

Test pulse:

```bash
growlab pump pulse 5
growlab sensor read ds18b20_<device_id>
growlab pump schedule
```

Pass condition:
- water flows from emitter
- no leaks in lines/fittings
- pump stops cleanly after pulse
- DS18B20 still reads normally

## 6) Start and Soak

Start system:

```bash
growlab start
```

Let it run for several hours. In a second terminal:

```bash
cd ~/grow-lab
source .venv/bin/activate
growlab db info
growlab db export --type readings --sensor ds18b20_<device_id> --limit 100
growlab dashboard
```

If you need a non-interactive dashboard process over SSH:

```bash
nohup bash -lc 'source .venv/bin/activate && growlab dashboard --host 0.0.0.0 --port 8000' > ~/growlab-dashboard.log 2>&1 < /dev/null &
tail -f ~/growlab-dashboard.log
```

If the remaining sensors are still in shipping transit, you can seed a design/demo dataset:

```bash
growlab db seed-demo --hours 24
```

Pass condition:
- service remains up
- DS18B20 readings accumulate in DB
- dashboard displays sensor data

## 7) Phase 1 Exit Checklist

- [ ] Physical bench layout safe (zones + drip loops)
- [ ] DS18B20 stable and plausible readings
- [ ] Relay dry test passes repeatedly
- [ ] Pump wet test passes with zero leaks
- [ ] `growlab start` survives multi-hour soak
- [ ] Data visible in DB and dashboard

## 8) Stop/Abort Conditions

Stop immediately and power down if any of the following occur:
- relay stuck ON
- continuous pump run beyond expected pulse
- visible leak near electrical zone
- unstable power/reset loop on Pi

When in doubt: disconnect pump power first, then debug.

## 9) End-of-Day Handoff Template

Use this quick template at session end:

- Date:
- Hardware connected:
- What passed today:
- Current blocker:
- Last known-good commands:
- Next first step:

Current saved handoff (March 12, 2026):

- Date: March 12, 2026
- Hardware connected: Pi 4, DS18B20, GPIO relay, ESP32-S3-N16R8
- What passed today: DS18B20 read path, GPIO relay CLI control
- Current blocker: ESP32 runtime serial command responses time out
- Last known-good commands:
  - `growlab sensor read ds18b20_28-00000070dac6`
  - `growlab pump on --max-seconds 2`
  - `growlab pump off`
- Next first step: connect ESP32 directly to development computer and validate runtime serial protocol before returning to Pi integration
