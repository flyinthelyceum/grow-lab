# Parts BOM

This document tracks hardware used in GROWLAB. V0 targeted the bench prototype;
the V1 physical build moves that electronics stack into a real cinder-block vessel
with a living plant. Physical-build parts (vessel, reservoir, pump, enclosure) and
the loop design live in [V1_PHYSICAL_BUILD.md](V1_PHYSICAL_BUILD.md).

For detailed specifications see: [LIGHTING_SYSTEM.md](LIGHTING_SYSTEM.md), [IRRIGATION_SYSTEM.md](IRRIGATION_SYSTEM.md), [SENSOR_STACK.md](SENSOR_STACK.md), [WIRING_&_BUSES.md](WIRING_&_BUSES.md)

---

# Lighting System

LED Strip

Samsung LM301H based grow strip  
400mm Sun Board strip  
96 LEDs per board  
**2 boards on hand (192 LEDs total)** — confirm both fit the driver's 120W budget before wiring in parallel

Driver

Meanwell PWM-120-24 LED Driver  
24V  
120W  
5A max output

Mounting

Aluminum bar heatsink  
thermal adhesive or screws

Electrical

WAGO connectors  
18–20 AWG wire  
AC power cord  
ESP32 PWM dimming control

Note

Boards are **white full-spectrum** (LM301H). The red/blue color-register in the
piece's concept has no hardware yet; see the lighting decision in
[V1_PHYSICAL_BUILD.md](V1_PHYSICAL_BUILD.md).

---

# Compute System

Primary Controller

Raspberry Pi (Model 3 / 4 / 5 acceptable)

Accessories

MicroSD card  
Pi power supply  
WiFi network access

Secondary Controller

ESP32 development board

Used for

PWM dimming  
IO expansion

---

# Sensor Stack

Temperature / Humidity

BME280 or SHT31 sensor module

Reservoir Temperature

DS18B20 waterproof probe

Electrical Conductivity (EC)

Atlas Scientific EZO-EC probe + interface (I2C 0x64)  
**Inline voltage isolator required** — see Electrical Safety

pH

Atlas Scientific EZO-pH probe + interface (I2C 0x63)  
**Inline voltage isolator required** — see Electrical Safety

Media Moisture

**Active: DFRobot SEN0308 (IP65 capacitive) + ADS1115 16-bit ADC (I2C 0x48)**  
Retired: Adafruit STEMMA Soil Sensor (0x36) — replaced 2026-04-14

Calibration

pH calibration solutions  
EC calibration solution

---

# Camera System

Camera

Raspberry Pi Camera Module 3 (Standard or Wide)  
Sony IMX708 sensor  
11.9 MP  
CSI ribbon cable interface

Accessories

Extended ribbon cable (300mm or 500mm)  
Fixed mount or small tripod for consistent framing

---

# Display (Optional)

SH1106 OLED module  
128x64 pixels  
I2C interface (address 0x3C)  
physical status display on installation

---

# Irrigation System

Reservoir

**2.5 gallon bucket + lid** (below the vessel; holds solution, probes, pump)  
Small volume swings pH/EC faster and needs frequent top-off — acceptable for one CMU

Pump

**SICCE Micra Plus Compact — 158 GPH, submersible (fresh/salt)**  
Flow far exceeds two emitters; run a **bypass tee back to the reservoir** to bleed
excess and leave a gentle drip. Pump adjustable as well.

Filter

Inline filter on the lift side, before the emitters (recirculating feed clogs drippers)

Tubing

1/4" drip irrigation tubing + main line to overhead manifold

Emitters

Drip stakes — one per CMU core (2 total)

Drainage / Return

Drain hole per core → gravity return to reservoir, with an air gap at the return

Control

Relay module for pump switching

---

# Plant Media & Vessel

Vessel

**Standard CMU (cinder block)** — the block's own center web divides the two cores  
Cores lined (food-safe pond liner / planter insert) so media and roots never touch
raw cement — raw CMU leaches lime and drives pH alkaline

Growing Media

Coco coir  
Perlite

Drainage

Drain hole + mesh screen per core

---

# Enclosure

**Dry electronics enclosure — custom, to be 3D-printed / laser-cut acrylic**

- One box, mounted above the water line and to the side — never over the reservoir
- Cable glands on every penetration; drip loops on all external cables
- Mains and DC/signal wiring separated inside
- Ventilation for PSU + LED-driver heat, drawn away from the wet zone
- Houses: Raspberry Pi, ESP32, relay board, PSU (5V), PWM-120-24 driver, OLED on the face

Design lives with the physical-build doc; fabricate via the print/laser pipeline.

---

# Airflow

Fan

Small circulation fan  
USB or 12V powered

Purpose

prevent stagnant canopy air

---

# Electrical Safety

GFCI outlet on mains — required

**Atlas EZO inline voltage isolators ×2** — one each on pH and EC.
pH and EC share the same water; the EC circuit injects noise that corrupts pH
readings without isolation. Pumps/solenoids bleed micro-voltage into the water too —
keep their grounds off the sensor path.

Drip loops on all cables

Cable management separating wet systems from electrical components

---

# Light Measurement

Ambient Light / Lux

**Active: TSL2591 high-dynamic-range lux sensor (I2C 0x39)** — new driver, canopy height  
Present but disabled: Adafruit AS7341 10-channel spectral breakout (I2C 0x39)

Mount at canopy height, facing the grow light. Provides closed-loop verification
that the LED is on, how canopy light shifts over time, and whether output is
drifting as the fixture ages.

---

# Future Hardware (Not Required for V1)

Lighting (concept alignment)

Independently-dimmed 660nm deep-red + 450nm royal-blue supplement channels, so the
white LM301H stays the growth workhorse while R/B carries the piece's temporal color
register (see [V1_PHYSICAL_BUILD.md](V1_PHYSICAL_BUILD.md))

Light measurement

Quantum PAR sensor (Apogee SQ-520 or similar) for true µmol/m²/s PPFD

Environmental control

Humidity sensor network  
CO₂ sensor

Reservoir automation

Dosing pumps  
Level sensors

Structural

Custom aluminum frame  
Integrated cable routing
