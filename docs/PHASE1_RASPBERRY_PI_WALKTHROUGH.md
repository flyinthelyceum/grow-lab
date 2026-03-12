# Phase 1 Raspberry Pi Walkthrough (Pi + DS18B20 + Relay + Pump + Fan)

Use this as the live checklist on the Pi terminal. Run steps in order. Do not skip safety checks.

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
pip install -e .
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
