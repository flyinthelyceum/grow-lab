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

---

# Aliveness / Front Panel (v1, non-color)

The tube-amp soul of the piece: byproduct-of-function, intransitive, for the tender.
All parts below are RESEARCHED LEADS (2026-09-01) — **verify listing, price, and stock before buying.**
Shaft rule resolved: D-shaft pots/encoders take SET-SCREW knobs; true collet knobs need a plain-round-shaft pot + collet bushing. v1 uses D-shaft + set-screw to avoid the collet dependency.

## Pilot lamp — "the fire is lit"

Hero (one-off soul): NOS Dialco/Dialight 1" amber diamond-cut jewel + chrome ring — eBay, ~$15-30, 1" hole, incandescent. Real cut glass, facet depth no modern part matches. Stock rotates.
Repeatable fallback: Amp Repair Parts amber jewel JL-115A + LH-124 chrome holder + #47 6.3V bulb (or LED-47 warm retrofit) — amprepairparts.com, ~$14, ~0.5" hole. The Fender jewel lineage.
Secondary status: Bulgin 0067 amber filament, chrome bezel — Mouser/RS, ~$6-9, Ø12.7mm. True tungsten, warmest color temp, in production.

## Amber "tend me" indicator

VCC 1092 Series amber, polished bezel — Amazon/Mouser, ~$5-8, 0.5"/12.7mm, 12V. Semi-dome amber = attention without alarm-spectacle. Reserved solely for the tend-me state.

## Analog VU meters — the vitals (×2: e.g. pH + moisture)

Hero (buildable): Simpson Wide-Vue raw DC panel meter, order in µA/mA full-scale (e.g. 0-1mA) — rammeter.com, ~$70-140 ea by size (2.5"/3.5"/4.5"). Raw movement = drive directly with an op-amp scaler off sensor voltage. Add a warm LED behind the dial. Archetypal American instrument face.
Soul upgrade (one-off): Weston NOS microammeter (Model 1/301/1921), 0-100µA/0-1mA — eBay, ~$50-150, ~3.5" cream Bakelite face, engraved serif scale. Pre-war patina no repro touches.
Hi-fi look (audio-cal, backlit): Sifam Tinsley AL29WF Presentor — don-audio.com, ~$65, 46×40mm, built-in overhead LED. The Urei 1176 meter; order to a sensitivity or bypass the cal resistor to drive as DC.
Each raw DC meter needs a small op-amp current-driver stage (design later).

## Rotary controls — THE FEEL (v1 = 3 controls)

Photoperiod hours (detented): Bourns PEC11H-4225F-S0024 — Mouser, ~$3-4, 6mm D-shaft, 24-pos endless encoder, HIGH-detent (~210 gf-cm, 3× the standard PEC11R). Crisp weighted snap every 15°, no mush; reads position (no wiper wear).
  Splurge-feel alt (discrete positions): ELMA 04-series rotary switch — Newark, ~$27-58, steel shaft, 30° detent, up to 20 Ncm. A heavy mechanical "chunk," the boutique reference. True switch: each position needs its own wired contact.
Setpoint trims (smooth ×2): ALPS RK27 "Blue Velvet" — theaudiocrafts/eBay, ~$15-25, 6mm knurled or D-shaft. The DIY-audio reference for buttery, scratch-free, medium-light glide.
  Showpiece upgrade (one trim): TKD 2CP-601 — PartsConnexion, ~$100-160, 6mm round, conductive plastic. Heavier, viscous, damped — rated above Alps for tactile refinement.

## Knobs (set-screw, to pair with D-shaft pots/encoders)

Hero: ELMA K1 metal knob series — don-audio.com, ~$7-8, turned satin-anodized aluminum, SET-SCREW sized to 6mm/D. Real machined weight — the "expensive click" of high-end consoles.
Tube-amp register: Davies Molding 1900H — Mouser, ~$2-4, phenolic skirted pointer, 6mm/¼" set-screw. The literal Fender/Marshall knob.
Synth look: Rogan RB-67 — Amplified Parts, USA-made, spun-aluminum inlay in a dark skirt, ¼" set-screw. The Buchla knob.
NOTE: true ELMA Classic Collet knobs are gorgeous but need a plain-round-shaft pot + collet bushing — NOT compatible with the D-shaft PEC11H/RK27 above. Choose collet-shaft pots if collet knobs become non-negotiable.

## e-ink — the quiet face

Pimoroni Inky Impression 7.3" (7-colour) — already in the standards; slow unlabeled state transitions, holds frame unpowered.

## Still to design
- Op-amp current-driver stage for the raw DC meters (scale sensor → meter full-scale).
- Which two "vitals" the meters show (default: pH + moisture — confirm with Jared).
- Panel material/finish + engraving (Material Non-Artifice, Transparent light register).

## Meter driver stage (drives the two vitals meters)

Signal path: Pi → I²C DAC → op-amp voltage-to-current (meter in feedback) → meter. Needle current = V_DAC / R_sense, coil-independent. Schematic artifact: https://claude.ai/code/artifact/c26c99e8-57c9-4675-a6e6-072a2d88ecf5

- **DAC:** Microchip MCP4728, quad 12-bit I²C (Adafruit #4470 breakout, ~$8, or bare SOIC). Addr 0x60 — no conflict with EZO 0x63/0x64, ADS1115 0x48, lux 0x39, OLED 0x3c. 2 channels used (A=pH, B=moisture), 2 spare (future 3rd meter / R+B light).
- **Op-amp:** Microchip MCP6004 quad, rail-to-rail, single +5V (~$0.50; DIP-14 or SOIC). 2 of 4 used.
- **R_sense (×2):** precision metal-film sized to the Simpson movement's full-scale current — ~2.05kΩ for 1mA FS, ~41kΩ for 50µA FS (finalize when the meter is chosen). Put part of it as a **multiturn cermet trimmer** (Bourns 3296, ~$1.50 ea) for full-scale calibration against a known input.
- **Dial backlight (×2):** warm-white LED behind each meter dial + series resistor, steady on +5V. Not dimmed, not an effect.
- **Decoupling:** 0.1µF ceramic per IC; optional small cap across the meter to slow needle settle if desired.
- **Software:** Pi maps pH 4.0–9.0 → 0–FS and moisture 0–100% → 0–FS, writes MCP4728 over I²C. Print the dial scales to match the mapping.

All RESEARCHED LEADS — verify listings/values before buying; R_sense value pending the meter full-scale spec.

## v1 irrigation + fan revisions (2026-09-02)

- **Emitters:** pressure-compensating drip emitters ×2 (~1 GPH) — deliver rated flow regardless of pump pressure; tames the oversized pump.
- **Bypass tee + throttle/ball valve** — sheds SICCE excess flow back to the reservoir (unused feed, not runoff).
- **Catch tray / drip tray** — runoff collection. Runoff-to-tray, NO recirculation in v1 (recirc pump-return loop DEFERRED to a later version).
- **Fan:** Noctua NF-A12x25 PWM chromax.black.swap (120mm, 4-pin PWM, 12V, ~0.06A) — driven at 25 kHz PWM (ESP32 or Pi GPIO18), not a relay.
- **12V rail** for the fan (small buck from 24V, or a 12V PSU). Adds a 4th LV domain.
- Reservoir note: keep pH/EC probes off the walls and out of pump turbulence (still water).
