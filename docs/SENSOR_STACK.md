

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

Atlas Scientific **EZO-pH circuit** (I²C 0x63)
Atlas Scientific **Lab Grade pH Probe** — [ENV-40-pH](https://atlas-scientific.com/probes/ph-probe/), $99.99

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

Monthly recalibration recommended. **Between uses the probe lives in storage
solution — never dry, never in plain or distilled water.** Check health with
`growlab sensor ph-slope` after each calibration: >95% slope, offset within
±5 mV. A dead electrode reads near its pH 7.00 isopotential point regardless
of solution, so a plausible number is not proof of a working probe. See
[BOM.md](BOM.md) → pH probe maintenance.

Probe location:

Submerged in reservoir using a probe holder or bridge mount.

Probe tips must:

• remain submerged  
• avoid contact with reservoir walls  
• avoid strong pump turbulence

---

## Electrical Conductivity (EC)

Sensor system:

Atlas Scientific **EZO-EC circuit** (I²C 0x64)
Atlas Scientific **Conductivity Probe K 1.0** — [ENV-40-EC-K1.0](https://atlas-scientific.com/probes/conductivity-probe-k-1-0/), $139.99, range 5 – 200,000 µS/cm

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

EC probes outlast pH probes but need periodic cleaning, and the same wet-storage
rule applies — see [BOM.md](BOM.md) → pH probe maintenance.

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

## DFRobot SEN0308 + ADS1115 ADC

Product: DFRobot SEN0308 Capacitive Soil Moisture Sensor (IP65) + ADS1115 16-bit ADC

Purpose:

Measure moisture content in the coco coir + perlite media to inform irrigation decisions. This is the most actionable data point for answering: does this plant need water right now?

Sensor type:

Capacitive — measures dielectric permittivity of surrounding media. No DC current flows through the media, so no galvanic corrosion.

Specifications:

• SEN0308: IP65 waterproof, analog voltage output, 3.3–5V, ~$14.50
• ADS1115: 16-bit I²C ADC, 4 channels, I²C address 0x48 (ADDR→GND), ~$3–10
• Output voltage range: ~3.0V dry air → ~1.1V fully submerged
• Driver maps voltage linearly to 0–100% moisture
• Total cost: ~$25 per channel

Wiring (SEN0308 → ADS1115):

• Red → VDD
• Black (bundled) → GND
• Yellow → A0
• Black (separate/shield) → GND

ADS1115 → Pi: VDD→3.3V, GND→GND, SDA→GPIO2, SCL→GPIO3, ADDR→GND

Communication:

I²C via ADS1115 at 0x48. Connects to the Pi's existing I²C bus alongside BME280 and Atlas EZO sensors. No address conflicts.

Sampling frequency:

5 minutes (300s interval).

## Avoid: Generic "Capacitive Soil Moisture Sensor v1.2"

The $1–3 generic sensors on Amazon/AliExpress are not reliable for continuous use. Uncoated PCB edges wick moisture, causing drift and failure within months. Do not use these.

---

# Camera System

## Raspberry Pi Camera Module 3

Purpose:

Capture periodic still images for timelapse generation, growth tracking, and correlation with environmental sensor data.

Timelapse notes:

• Lock focus manually after mounting (set AfMode.Manual with fixed LensPosition in picamera2)
• Allow ~60 seconds warm-up before locking focus
• Disable HDR for full 12 MP stills (HDR caps at ~3 MP)
• Mount securely — the AF mechanism shifts with orientation changes

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

Devices, addresses and ADDR-pin strap conditions: [WIRING_&_BUSES.md](WIRING_&_BUSES.md) → I²C Bus. Atlas EZO boards ship in UART mode and will not appear on the bus until switched; that procedure is in the same document.

## 1-Wire Bus

Devices:

• DS18B20 temperature probe

## CSI Interface

Devices:

• Raspberry Pi Camera Module 3
