# V1 Go-Live Runbook

## Objective

Transition from bench prototype to a working grow station with a live plant. All sensors online, irrigation plumbed to a planted container, lighting on photoperiod, and the system running unattended.

This runbook covers the physical build, sensor integration, and full-system validation for April 1, 2026.

## Current State (as of March 31, 2026)

### Operational

- Raspberry Pi 4 on RSP-GPIO-8 breakout board.
- BME280 (air temp, humidity, pressure) at I2C 0x76. Polling every 120s.
- DS18B20 (reservoir temp) on 1-Wire GPIO4.
- Atlas EZO-pH at I2C 0x63. 3-point calibration complete.
- Atlas EZO-EC at I2C 0x64. 2-point calibration complete.
- Pi Camera Module 3. Pump-triggered captures working.
- SH1106 OLED display. 4-page rotation.
- ESP32-S3 connected via USB. Firmware v0.2.1.
- Samsung LM301H LED strip + Mean Well PWM-120-24 driver installed and wired to ESP32 PWM.
- Noctua NF-A12x25 fan running always-on via relay.
- Submersible pump + relay on GPIO17. Schedule: 08:00, 14:00, 20:00 UTC, 10s pulses.
- 5-gallon reservoir with plain water. pH 8.3, EC 1,529 µS/cm baseline.
- Tailscale remote access at 100.77.46.126.
- systemd services for growlab and growlab-dashboard.
- Dashboard live: Observatory, Art Mode, Dream Mode.

### Just Received (March 30)

- DFRobot SEN0308 capacitive soil moisture sensor.
- Adafruit AS7341 10-channel spectral light sensor.

### Nutrients On Hand

- General Hydroponics Flora Series trio (FloraMicro, FloraGrow, FloraBloom) — 32 oz each.
- General Hydroponics pH Control Kit (pH Up, pH Down, test indicator, test tube, eyedropper, pH chart).

### Plant Material

- Ranunculus corms.

### Picking Up Tonight

- Coco coir + perlite.
- 1/2" to 1/4" barb adapter (pump outlet to drip tubing).
- Grow bin / nursery pot (3-5 gallon).

---

## Pre-Build Checklist

Confirm these are on hand before starting. Check off tonight.

- [ ] Coco coir
- [ ] Perlite
- [ ] Nursery pot (3-5 gallon) with drainage holes
- [ ] Drain tray / catch basin
- [ ] 1/2" to 1/4" barb adapter
- [ ] Drip emitter or drip stake (1 GPH)
- [ ] Enough 1/4" tubing for final station layout
- [ ] Mesh screen for drainage holes (optional, prevents media clog)
- [ ] Zip ties or clips for tubing runs
- [ ] SEN0308 soil moisture sensor
- [ ] AS7341 spectral light sensor
- [ ] ADS1115 ADC breakout (required for SEN0308)
- [ ] Ranunculus corms
- [ ] GH Flora Series nutrients
- [ ] GH pH Control Kit

---

## Phase A: Physical Build (~1-2 hours)

Goal: a planted container receiving water from the reservoir with proper drainage.

### A.1 Prepare Growing Media

- Hydrate coco coir per package instructions (expand block in water, break apart, drain excess).
- Mix coco coir and perlite at approximately 70/30 ratio.
- Fill nursery pot, leaving 1-2 inches below rim.

### A.2 Plant Ranunculus Corms

- Pre-soak corms in room temperature water for 3-4 hours (they expand significantly).
- Plant 1-2 inches deep, claws facing down.
- Space corms 3-4 inches apart.
- Light cover of media on top. Do not pack tightly.

### A.3 Plumb the Station

- Connect barb adapter to pump outlet (1/2" to 1/4").
- Run 1/4" tubing from pump to nursery pot.
- Attach drip emitter or stake at the pot end, positioned near corm zone.
- Place nursery pot on drain tray.
- Secure tubing with zip ties. Route with drip loops where tubing crosses electrical.

### A.4 Verify Flow

```bash
growlab pump pulse 10
```

- Confirm water flows from reservoir through tubing to emitter to media.
- Check for leaks at every connection point.
- Confirm drainage exits pot into tray.
- Verify pump relay clicks off after pulse.

---

## Phase B: Sensor Integration (~1-2 hours)

Goal: SEN0308 and AS7341 online, all sensors reporting.

### B.1 SEN0308 Soil Moisture Sensor

The SEN0308 outputs analog voltage. It connects through an ADS1115 ADC on the I2C bus.

1. Wire ADS1115 to Pi I2C bus:
   - VDD → 3.3V
   - GND → GND
   - SDA → GPIO2 (I2C SDA)
   - SCL → GPIO3 (I2C SCL)
2. Wire SEN0308 signal to ADS1115 channel A0.
3. Wire SEN0308 power (3.3-5V) and ground.
4. Insert SEN0308 probe into the planted media.

```bash
sudo i2cdetect -y 1
# expect 0x48 (ADS1115) alongside existing devices
```

5. Enable in `config.toml`:

```toml
[sensors.soil_moisture]
enabled = true
```

6. Verify:

```bash
growlab sensor validate-all
growlab sensor read soil_moisture
```

Expected: value that changes when media is wet vs dry.

### B.2 AS7341 Spectral Light Sensor

1. Wire AS7341 to Pi I2C bus:
   - VIN → 3.3V
   - GND → GND
   - SDA → GPIO2
   - SCL → GPIO3
2. Mount at canopy height, facing the LED strip.

```bash
sudo i2cdetect -y 1
# expect 0x39 (AS7341)
```

3. Enable in `config.toml`:

```toml
[sensors.as7341]
enabled = true
```

4. Verify:

```bash
growlab sensor validate-all
growlab sensor read as7341
```

Expected: spectral channel values and lux estimate. Values should change when LED strip is on vs off.

### B.3 Full Sensor Validation

```bash
growlab sensor validate-all
```

All 6 sensors should pass: BME280, DS18B20, EZO-pH, EZO-EC, soil_moisture, AS7341.

---

## Phase C: Lighting Validation (~30 minutes)

Goal: ESP32 LED PWM confirmed with spectral feedback from AS7341.

### C.1 Test LED Control

```bash
growlab light set 50
growlab light set 200
growlab light set 0
growlab light status
```

Confirm LED strip responds to PWM commands. Check heatsink temperature after a few minutes at full power.

### C.2 Enable Photoperiod Schedule

Update `config.toml`:

```toml
[lighting]
enabled = true
mode = "veg"
on_hour = 6
off_hour = 22
intensity = 200
ramp_minutes = 15
```

16-hour photoperiod (06:00-22:00) is appropriate for ranunculus vegetative growth.

### C.3 Confirm AS7341 Under Light

```bash
growlab sensor read as7341
```

With LED on: expect elevated values across visible channels, particularly 445nm (blue) and 630nm (red) for a full-spectrum grow light. Lux estimate should be meaningfully above ambient.

---

## Phase D: Nutrient Introduction (~30 minutes)

Goal: reservoir mixed to target range, stable before plant uptake begins.

### D.1 Mix Nutrient Solution

Follow General Hydroponics Flora Series directions for seedling/early growth strength:

- Start at 1/4 to 1/2 recommended concentration.
- Add FloraMicro first, stir. Then FloraGrow, stir. Then FloraBloom, stir.
- Target EC: 800-1,200 µS/cm (mild for establishing corms).
- Target pH: 5.8-6.2.

### D.2 Adjust pH

Use GH pH Down (phosphoric acid) to lower from the ~8.3 baseline.

- Add small amounts, stir, wait 5 minutes, recheck.
- Use the GH test indicator for quick spot checks.
- Use the EZO-pH sensor for precision:

```bash
growlab sensor read ezo_ph
```

### D.3 Confirm Stability

Let the reservoir sit for 30-60 minutes after mixing. Recheck pH and EC:

```bash
growlab sensor read ezo_ph
growlab sensor read ezo_ec
```

pH should hold within 0.2 of target. EC should be stable.

---

## Phase E: Full System Go-Live (~30 minutes)

### E.1 Final Config

Ensure all sensors enabled, irrigation schedule set, lighting enabled in `config.toml`.

### E.2 Restart Services

```bash
sudo systemctl restart growlab
sudo systemctl restart growlab-dashboard
```

### E.3 Dashboard Verification

Open `http://100.77.46.126:8000` (Tailscale) or `http://<local-ip>:8000`.

- LIGHT panel: AS7341 lux or PWM values charting.
- WATER panel: pH and EC values in range.
- AIR panel: BME280 temp, humidity, pressure.
- ROOT panel: soil moisture value.
- PLANT panel: camera captures.

### E.4 Confirm All Services

```bash
growlab sensor validate-all
sudo systemctl status growlab
sudo systemctl status growlab-dashboard
```

### E.5 Camera Test

```bash
growlab camera capture
```

Verify image shows the planted container under grow light.

---

## Phase F: Documentation Update (~15 minutes)

- Update Phase 2 exit criteria: mark LED PWM complete.
- Update Phase 3 exit criteria: mark soil moisture complete.
- Update BOM with SEN0308, AS7341, nutrients, and grow media.
- Update SENSOR_STACK with SEN0308 wiring and calibration notes.
- Commit all changes.

---

## Post Go-Live Monitoring (First 48 Hours)

- Check pH drift morning and evening. Adjust with pH Down as needed.
- Watch soil moisture readings — confirm irrigation schedule keeps media in target range.
- Monitor reservoir EC — rising EC means plant is drinking water faster than nutrients (dilute). Falling EC means nutrient uptake is high (top up).
- Check LED heatsink temperature.
- Confirm no leaks after 24 hours of irrigation cycles.
- Review Observatory dashboard for any sensor dropouts or anomalies.

### Phase 4 Exit Criteria

- [ ] All 6 sensors reporting on dashboard.
- [ ] Nutrient reservoir stable in target pH (5.8-6.2) and EC (800-1,200 µS/cm) range.
- [ ] Irrigation delivering water to planted media on schedule.
- [ ] LED strip running on photoperiod with AS7341 confirming output.
- [ ] Plant shows no stress in first 48 hours.
- [ ] System runs unattended with stable telemetry.

---

## Key Decisions (Locked)

- Nutrient strength: start at 1/4 to 1/2 Flora Series recommended dose. Increase only after corms show root growth.
- Irrigation frequency: keep existing 3x/day schedule (08:00, 14:00, 20:00 UTC). Adjust based on soil moisture sensor feedback.
- Photoperiod: 16 hours (06:00-22:00) for vegetative ranunculus growth.
- Drainage: runoff-to-tray, no recirculation in V1.
- pH management: manual adjustment with GH pH Down. Automated dosing is a future upgrade.

## What Not To Do

- Do not start at full nutrient concentration. Corms are sensitive before root establishment.
- Do not skip the pre-build checklist. Missing a barb adapter or drain tray will block the entire build.
- Do not enable sensors in config before they are physically wired and verified with i2cdetect.
- Do not adjust pH and nutrients simultaneously. Change one, wait, measure.
- Do not leave the system unmonitored for the first 48 hours. Check twice daily minimum.
