

# Sensor Stack

This document defines the environmental sensing architecture for GROWLAB.

The goal of the sensor stack is to provide reliable, continuous measurements of the environmental variables that affect plant health and growth.

The system is designed around **shared reservoir instrumentation** and **modular environmental sensing**, allowing future expansion without redesigning the core architecture.

---

# Sensor Philosophy

The sensor system follows several guiding principles:

• **Biological relevance** – measure variables that actually affect plant growth  
• **Reliability over novelty** – proven sensors over experimental modules  
• **Shared instrumentation** – reservoir chemistry is measured once, not per plant bin  
• **Modularity** – sensors can be added or replaced without redesigning the system  

The V0 prototype prioritizes **stable core measurements** rather than exhaustive sensing.

---

# V0 Sensor Overview

The V0 system measures six primary domains:

1. Air environment
2. Reservoir chemistry
3. Reservoir temperature
4. Media moisture
5. Visual growth record (camera)
6. System events (derived data)

---

# Air Environment Sensors

## BME280

Measures:

• Air temperature  
• Relative humidity  
• Atmospheric pressure (optional)

Purpose:

Monitor the canopy environment surrounding the plants.

Typical installation location:

• mounted near canopy height  
• shielded from direct grow light exposure  
• positioned away from fan airflow blast

Communication:

I²C

Connected to:

Raspberry Pi I²C bus.

Sampling frequency:

1–5 minutes.

---

# Reservoir Sensors

Reservoir sensors monitor the chemistry and temperature of the nutrient solution feeding the plants.

These sensors are **shared across all plant bins**.

## pH Measurement

Sensor system:

Atlas Scientific **EZO-pH circuit**  
Atlas Scientific **Lab Grade pH probe**

Purpose:

Monitor acidity/alkalinity of nutrient solution.

Typical hydroponic range:

5.5 – 6.5

Connection:

I²C to Raspberry Pi.

Calibration:

Three-point calibration:

• pH 4  
• pH 7  
• pH 10

Maintenance:

Monthly recalibration recommended.

Probe location:

Submerged in reservoir using a probe holder or bridge mount.

Probe tips must:

• remain submerged  
• avoid contact with reservoir walls  
• avoid strong pump turbulence

---

## Electrical Conductivity (EC)

Sensor system:

Atlas Scientific **EZO-EC circuit**  
Atlas Scientific **K1.0 conductivity probe**

Purpose:

Measure nutrient concentration of the solution.

Typical hydroponic ranges:

Seedlings: 0.5–1.0 mS/cm  
Vegetative: 1.0–2.0 mS/cm  
Flowering plants: 1.5–2.5 mS/cm

Connection:

I²C to Raspberry Pi.

Calibration:

Using standard conductivity solution (e.g., 1413 µS).

Probe mounting guidelines identical to pH probe.

---

# Reservoir Temperature

## DS18B20 Waterproof Temperature Probe

Purpose:

Monitor reservoir temperature.

Target range:

18–22°C (65–72°F)

Temperature affects:

• oxygen availability  
• nutrient uptake  
• microbial growth

Connection:

1-Wire bus to Raspberry Pi.

Installation:

Probe submerged in reservoir water but not touching pump or container walls.

---

# Media Moisture

## Adafruit STEMMA Soil Sensor (Primary)

Product: Adafruit STEMMA Soil Sensor (Product 4026)

Purpose:

Measure moisture content in the coco coir + perlite media to inform irrigation decisions. This is the most actionable data point for answering: does this plant need water right now?

Sensor type:

Capacitive — measures dielectric permittivity of surrounding media. No DC current flows through the media, so no galvanic corrosion.

Specifications:

• Interface: I²C (Seesaw protocol)
• Default I²C address: 0x36 (configurable: 0x36–0x39 via solder jumpers)
• Voltage: 3.3–5V
• Output range: ~200 (dry air) to ~2000 (submerged), practical range in media ~300–500
• Onboard MCU: ATSAMD10
• Bonus: built-in temperature sensor (~+/-2°C accuracy)
• Price: ~$7.50

Known issues and mitigations:

• Reading saturation at ~1016–1017 — use relative thresholds (wet/dry), not absolute values
• Noisy signal — add 200ms minimum delay between reads, average multiple samples
• No waterproofing on electronics — apply conformal coating (MG Chemicals 422B or equivalent)
• Not specifically tested for soilless media — calibrate for your coco+perlite ratio

Communication:

I²C. Connects to the Pi's existing I²C bus (GPIO 2 SDA, GPIO 3 SCL) alongside BME280 and Atlas EZO sensors. No address conflicts.

Sampling frequency:

5–15 minutes.

## Alternative: DFRobot SEN0308 (IP65 Waterproof) + ADS1115

Choose this if long-term durability is the top priority.

• DFRobot SEN0308: IP65 waterproof, analog output, ~$14.50
• ADS1115 ADC: I²C at 0x48, 16-bit, 4 channels, ~$3–10
• Total: ~$25 per channel
• Better long-term reliability but requires an extra component (ADC)

## Calibration for Coco Coir + Perlite

Standard soil moisture calibrations do not apply to soilless media. Substrate-specific calibration is required.

Method:

1. Fill pot with dry coco coir + perlite mix (same ratio as production)
2. Insert sensor at ~2/3 pot depth, away from pot wall and drip emitter
3. Record sensor reading (dry baseline)
4. Add known volumes of water incrementally (100 mL at a time)
5. Wait 5 minutes after each addition for water to distribute
6. Record sensor reading at each step
7. Define two thresholds: dry (trigger irrigation) and wet (skip irrigation)

For irrigation decisions, relative readings are sufficient — you do not need absolute volumetric water content.

## Avoid: Generic "Capacitive Soil Moisture Sensor v1.2"

The $1–3 generic sensors on Amazon/AliExpress are not reliable for continuous use. Uncoated PCB edges wick moisture, causing drift and failure within months. Do not use these.

---

# Camera System

## Raspberry Pi Camera Module 3

Purpose:

Capture periodic still images for timelapse generation, growth tracking, and correlation with environmental sensor data.

Recommended variant:

Camera Module 3 Standard (~$25). Choose Wide (~$35) if mounting close to the plant.

Specifications:

• Sensor: Sony IMX708
• Resolution: 11.9 MP (4608 x 2592)
• Focus: Phase Detection Autofocus (PDAF), motorized
• FoV: 75° standard, 120° wide
• Interface: CSI ribbon cable (15-pin for Pi 3/4, 22-pin for Pi 5)
• Weight: ~14 g
• Max exposure: 112 seconds
• Ships with cables for both Pi connector types

Variants:

• Standard (75° FoV, IR filter) — general purpose
• Wide (120° FoV, IR filter) — full installation capture
• NoIR (75°, no IR filter) — dark period capture with IR lighting
• Wide NoIR (120°, no IR filter) — wide-angle night capture

Software:

• picamera2 (Python library) — native Pi camera control
• Legacy raspistill/raspivid are not supported with Camera Module 3
• libcamera-still CLI tool for scripted capture

Timelapse notes:

• Lock focus manually after mounting (set AfMode.Manual with fixed LensPosition in picamera2)
• Allow ~60 seconds warm-up before locking focus
• Disable HDR for full 12 MP stills (HDR caps at ~3 MP)
• Mount securely — the AF mechanism shifts with orientation changes

Ribbon cable:

Stock is 200mm. Extended cables available at 300mm and 500mm for remote mounting.

Storage:

At 10-minute capture intervals (~500 KB/frame): ~72 MB/day, ~2.2 GB/month. A 128 GB SD card or USB drive handles months of footage.

Timelapse assembly:

```
ffmpeg -framerate 30 -pattern_type glob -i '*.jpg' -c:v libx264 timelapse.mp4
```

Integration:

• Timestamp each image for correlation with sensor logs
• Display latest frame on the web dashboard alongside live sensor data
• Future: OpenCV canopy area measurement for quantitative growth tracking

---

# Derived System Measurements

Some system values are derived rather than directly measured.

These include:

• irrigation events  
• light intensity setting (PWM level)  
• fan runtime  
• nutrient solution changes

These values are logged alongside sensor measurements to enable system analysis.

---

# Sensor Bus Architecture

The V0 system uses two communication buses plus the CSI camera interface.

## I²C Bus

Devices, addresses, and strap conditions:

| Device | I²C Address | Address Selection | Function |
|--------|-------------|-------------------|----------|
| STEMMA Soil Sensor | 0x36 | Default. A0/A1 solder jumpers for 0x37–0x39 | Media moisture |
| SSD1306 OLED (optional) | 0x3C | SA0→GND. SA0→VCC for 0x3D | Physical status display |
| BME280 | 0x76 | SDO→GND. SDO→VCC for 0x77 | Air temp + humidity + pressure |
| Atlas EZO-pH | 0x63 (99 decimal) | Set via `I2C,99` command during mode switch | Reservoir pH |
| Atlas EZO-EC | 0x64 (100 decimal) | Set via `I2C,100` command during mode switch | Reservoir EC |
| AS7341 | 0x39 | Fixed (not configurable) | Canopy spectral light |
| ADS1115 (if used) | 0x48 | ADDR→GND. See datasheet for 0x49–0x4B | ADC for analog sensors |

No address conflicts in this configuration.

Note: Atlas EZO boards ship in UART mode by default. Use `growlab sensor ezo-setup --sensor ph|ec` to switch via UART, or see [WIRING_&_BUSES.md](WIRING_&_BUSES.md) for the manual procedure. After setup, `growlab sensor validate-all` confirms all sensors are reading correctly.

## 1-Wire Bus

Devices:

• DS18B20 temperature probe

## CSI Interface

Devices:

• Raspberry Pi Camera Module 3

---

# Sampling Strategy

Sensors are not polled continuously.

Typical logging intervals:

Air sensors  
every 1–5 minutes

Reservoir chemistry  
every 5–15 minutes

Reservoir temperature  
every 1–5 minutes

Event logging  
on occurrence

This reduces noise and extends sensor lifespan.

---

# Future Sensor Expansion

Possible additions in later system versions:

• ~~Light measurement (PAR / PPFD sensors)~~ → AS7341 spectral sensor added (V0)
• CO₂ concentration
• Leaf temperature
• Reservoir level sensing
• Nutrient dosing monitoring

The sensor architecture is designed so these sensors can be added without altering existing systems.

---

# Sensor Placement Principles

All sensors should follow these guidelines:

• avoid direct light exposure  
• avoid direct airflow blasts  
• avoid electrical noise sources  
• remain accessible for calibration and maintenance  

Proper placement dramatically improves measurement stability.

---

# Calibration and Maintenance

## pH Probe

• Calibrate monthly using 3-point calibration (pH 4, 7, 10)
• Lifespan: 12–18 months with regular use. pH probes are consumables — budget ~$50–80/year for replacement.
• Log a `probe_age` field in the events table when a new probe is installed. This allows long-term drift to be interpreted correctly against probe age.
• Never allow the probe to dry out. Use storage solution (KCl) when the probe is removed from the system.
• If the system is powered off for more than a few days, remove the probe and store it wet.

## EC Probe

• Calibrate using standard conductivity solution (e.g., 1413 µS) after installation and periodically thereafter
• EC probes last longer than pH probes but need periodic cleaning
• Same wet-storage rule applies

## BME280 / SHT31

• No calibration required for V0
• If readings seem off, check placement: direct light, airflow blasts, and electrical noise all affect readings
• BME280 may drift at sustained >70% RH. If this becomes an issue, swap to SHT31 (one-file change in sensor interface)

## Soil Moisture Sensor

• See calibration procedure in the Media Moisture section above
• Re-calibrate if you change the coco/perlite ratio or pot size

---

# Summary

The V0 sensor stack provides reliable monitoring of the variables most important to plant growth:

• air temperature + humidity (BME280)
• nutrient solution pH (Atlas EZO-pH)
• nutrient concentration EC (Atlas EZO-EC)
• reservoir temperature (DS18B20)
• media moisture (STEMMA Soil Sensor)
• visual growth record (Pi Camera Module 3)

These measurements allow GROWLAB to function not just as a grow platform, but as a **biological instrumentation system** capable of recording and analyzing the interaction between plants and their engineered environment.
