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
**2 boards on hand (192 LEDs total)**

**Measured 2026-09-02:** one board draws **0.72 A at 24 V (~17 W)** warm, at full PWM.
Two boards ≈ **1.4 A / 33 W** against the driver's 5 A / 120 W — both fit in parallel with
roughly 4x headroom. RESOLVED: wire both in parallel, no derating needed. (Cold draw was
0.69 A, rising as the junction warmed and the forward voltage fell — expected on a
constant-voltage rail, and it converged rather than running away.)

Driver

Meanwell PWM-120-24 LED Driver  
24V  
120W  
5A max output

Note: at the measured 33 W for both boards the driver is ~4x oversized. Headroom is
available if the lighting is ever expanded (more white boards, or the deferred red/blue
supplement channels), though separate channels would need their own dimming control.

Mounting

Aluminum bar heatsink  
thermal adhesive or screws  
Thermal load is modest at the measured draw — ~17 W per 400mm board (~40 W/m), so a
standard extruded LED channel/bar is sufficient. Still mandatory: LEDs must not run
unheatsinked.

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

**Stainless steam table pan, half size x 6 in deep, with lid** — 12.8 x 10.4 x 5.9 in
(325 x 265 x 150 mm), ~13 L to the brim. 2.5 gal sits at ~4.3 in with freeboard.
Sits on an adjustable shelf at 12 in; holds solution, probes, pump.  
**Not a tall bucket** — 2.5 gal is 577 in³, only 5.1 in deep in a 12 in bucket, so a tall
vessel spends cabinet height on air and costs pump lift.  
304 stainless matches the tray, is opaque (better algae exclusion than translucent
plastic), and its lid drills cleanly for pump cord, feed line and probe leads.
**Buy a 2-pack** — mix fresh solution in the spare and swap it in rather than mixing in
place around live probes.  
Small volume swings pH/EC faster and needs frequent top-off — acceptable for one CMU

Pump

**SICCE Micra Plus Compact — submersible (fresh/salt)**  
Curve, not headline: **158 GPH at zero head, 0 GPH at 2.8 ft shutoff** — high flow, low
pressure, like most aquarium pumps. Two consequences: **2.8 ft is a hard ceiling on
manifold height**, and against two small orifices the pump sits near shutoff at ~1.2 PSI.
Has a built-in intake sponge filter (first-stage filtration, keep it clean).
A **bypass tee + throttle valve** stops it deadheading; open it only as far as needed,
since bled pressure is pressure the emitters lose. Delivery rate is empirical — measure it
(build procedure Stage 0.2). Fallback if flow proves unusable: raise the reservoir to cut
the lift, or fit a higher-head pump.

Filter

**Rain Bird RBY075MPTX — 3/4" MPT x MPT inline Y filter, 200 mesh (75 micron) stainless
element, o-ring sealed cap.** Rated 150 PSI, 0.20–12.0 GPM. Mounted on the
**emitter branch after the bypass tee**, so it passes only the trickle headed to the
emitters. 200 mesh rather than 120 because 1 GPH emitter orifices are small. Rated 13 GPM
against a ~2 GPH need — enormously oversized on purpose: negligible pressure drop when
clean, and a long interval before a clog can starve a system with only ~1.2 PSI to give.
The cap unthreads for cleaning. Needs adapters from 3/4" MPT down to the main line. The
pump's intake sponge is stage one.

**Note on the low-flow duty:** at ~2 GPH the system runs far below the filter's stated
0.20 GPM minimum. That is fine for a passive screen — the rating describes its design
envelope, not a failure threshold — but there is no scouring velocity, so debris will sit
on the screen rather than sweeping to the cap. **Flush it manually on a schedule** instead
of expecting it to self-clear.

Tubing

1/4" drip irrigation tubing + main line to overhead manifold

Emitters

**~1 GPH drip emitters ×2** — one per CMU core. On hand as pressure-compensating, but
**they will not compensate here**: PC emitters need 7.25–10 PSI and only ~1.2 PSI is
available, so they behave as fixed orifices. Harmless at this scale — compensation evens
out many emitters across differing elevations, and these are two side by side at equal
height. **Symmetric plumbing** (equal run lengths and heights) is what splits flow evenly.

Drainage

Drain hole + mesh screen per core → **catch / drip tray**, 304 stainless, 16 ga, 2 in
upstand, lift-out. Bare bead-blast inside; white powder-coat the outer face only (paint in
permanent salt contact lifts). Floor cutouts pass load pads from the cabinet rail so the
tray carries water, never the block's ~50 lb. No glued-on grate — the mesh inside each
core retains the media. Runoff-to-tray, **no recirculation in v1** — runoff is discarded /
manually managed. A pump-return loop is deferred to a later version.

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

**The instrument enclosure and the plinth are two different objects. Do not merge them.**

The plinth is furniture: it holds the reservoir, hides what is ugly, and should recede.
The enclosure is the instrument — it carries the front panel described under
"Aliveness / Front Panel" below, and it should declare itself.

**Dry electronics enclosure — custom, 3D-printed / laser-cut acrylic**

Acrylic is not an arbitrary material here. A transparent or translucent body is the
**Transparent / Material Non-Artifice** register made literal: the apparatus stays legible
rather than being hidden inside painted casework. Substituting opaque cabinetry does not
just change the finish, it discards what the material was doing.

- Mounted above the water line and to the side — never over the reservoir
- Cable glands on every penetration; drip loops on all external cables
- Mains and DC/signal wiring separated inside
- Ventilation for PSU + LED-driver heat, drawn away from the wet zone
- Houses: Raspberry Pi, ESP32, relay board, PSU (5V), PWM-120-24 driver, meter driver
- **Front panel on its face** — NOS jewel pilot lamp, two analog meters, e-ink, knobs

**RESOLVED 2026-09-03: integrated into the mast.** Design study:
`https://claude.ai/code/artifact/c18075c9-9ca8-4f42-8ba3-2066474b21b6`

The mast is thin where it carries only a drip line and a sensor loom (2 x 3 in section) and
thickens into an **instrument head** where the apparatus lives — the same
byproduct-of-function logic the front panel is already specced under. The head is 9 x 11.5 x
3.5 in because that is what a 174 x 123 mm e-ink board and two meter movements measure, not
because a size was chosen.

| Element | Height / size |
|---|---|
| Shaft section | 2 x 3 in |
| LED fixture, hung from the head underside ~10 in forward | 46 in |
| Head | 9 x 11.5 x 3.5 in |
| Panel centre — read standing, while tending | 52 in |
| Overall height | 57.5 in |

The fixture hangs from the head's **underside**, not off the shaft, so the cantilever's
moment lands over the column rather than bending it.

**Split:** heavy, hot and mains stay in the plinth (PWM-120-24 driver, 5V PSU, relay board,
GFCI); the instrument and its brains go in the head (panel, Pi + i3, ESP32, meter driver).
24V runs up the shaft. Keeps the cantilever light and line voltage far from the panel.

**One earned accent:** the object is cool throughout — transparent body, hairline engraving,
grey ground. The single warm thing is the lit jewel. No amber in the e-ink palette, no warm
wash on the acrylic, no second indicator competing. One point of fire reads; two is
decoration.

---

# Airflow

Fan

**Noctua NF-A12x25 PWM chromax.black.swap** — 120mm, 4-pin PWM, 12V, ~0.06A  
Driven at **25 kHz PWM from Pi GPIO18** (FanService temperature ramp) — not a relay  
Optional tach wire for RPM

12V rail

**Small buck module (24V → 12V)** off the LED driver, or a dedicated 12V PSU  
Adds a fourth low-voltage domain: 24V (LED only) / 12V (fan) / 5V (logic) / 3.3V (sensors)

Purpose

prevent stagnant canopy air; pull heat off the LED heatsink

---

# Electrical Safety

GFCI outlet on mains — required

**Isolation is already covered by the i3 InterLink — do not buy separate isolators.**
The i3 carries two isolated EZO circuit slots (specified for EZO-pH / ORP / DO / EC) plus
one non-isolated slot. pH and EC are exactly the two circuits that need it, so seat them
in the isolated pair and the requirement is met. Verify seating before go-live.

Isolation matters because pH and EC share the same water; the EC circuit injects noise that
corrupts pH readings without it. Pumps/solenoids bleed micro-voltage into the water too —
keep their grounds off the sensor path.

Drip loops on all cables

Cable management separating wet systems from electrical components

---

# Light Measurement

Ambient Light / Lux

**RESOLVED 2026-09-03 — AS7341, on the rule that code takes precedence over docs because
the bench version is already running.**

**Active: Adafruit AS7341 10-channel spectral breakout (I2C 0x39)** — `pi/drivers/as7341.py`
emits `as7341_lux` plus ten spectral channels; `config.example.toml` carries
`[sensors.as7341]`. Mount at canopy height, facing the grow light.

TSL2591 is struck: no driver, no config section, and it claims the same 0x39 address so the
two could never share the bus. The earlier "TSL2591 active" line in this doc was aspirational
and never implemented.

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

Hero (buildable): Simpson Wide-Vue raw DC panel meter — rammeter.com, ~$70-140 ea by size. Raw movement = drive directly with an op-amp scaler off sensor voltage. Add a warm LED behind the dial. Archetypal American instrument face.

**From the Simpson Wide-Vue datasheet (Rev. 10-25) — dimensions in inches:**

| Size | Model | Bezel | Panel cutout | Behind panel | Bezel proud | Mtg holes | Terminals |
|---|---|---|---|---|---|---|---|
| 2-1/2" | 1227 | 2.47 × 2.47 | Ø 2.22 | 1.15 body + 0.70 studs = 1.85 | 0.48 | (4) Ø.125 on 1.88 × 1.88 | (2) 1/4-28, 1.00 apart |
| 3-1/2" | 1327 | 3.25 × 3.25 | Ø 2.79 | 1.22 + 0.70 = 1.92 | 0.62 | (4) Ø.125 on 2.25 × 2.25 | (2) 1/4-28, 1.50 apart |
| 4-1/2" | 1329 | 4.70 × 4.70 | Ø 2.81 | 1.20 + 0.70 = 1.90 | 0.64 | (4) Ø.156 on 4.00 × 4.00 | (2) 1/4-28, 1.50 apart |

Scale length: 2.30" (1227), 3.14" (1327), 3.93" (1329). Response ≤1.5 s. Overload 10× FS for 1 s, 1.5× continuous.

**DC microammeter movements (self-shielding), catalog no. by size 1227 / 1327 / 1329:**
0-50 µA, 1800 Ω — **04310 / 04380 / 04480**. 0-100 µA, 1800 Ω — 04320 / 04390 / 04490. 0-1 mA, 43 Ω — 06175 / 06310 / 06470.
Taut-band (no pivot friction, better linearity) 0-50 µA, 960 Ω — 04311 / 04381 / 04481.
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
- **R_sense (×2):** precision metal-film, R = V_DAC(FS) / I_meter(FS). With the MCP4728 on its internal 2.048 V reference: **40.96 kΩ for a 0-50 µA movement, 2.048 kΩ for 0-1 mA.** Coil resistance does not enter this equation (meter-in-feedback makes needle current independent of the coil) — it only sets op-amp headroom: I_FS × (R_sense + R_coil) = 50 µA × (41 k + 1.8 k) = 2.14 V, or 1 mA × (2.05 k + 43) = 2.1 V. Both comfortably inside a 5 V rail. Put part of R_sense as a **multiturn cermet trimmer** (Bourns 3296, ~$1.50 ea) for full-scale calibration against a known input.
- **Dial backlight (×2):** warm-white LED behind each meter dial + series resistor, steady on +5V. Not dimmed, not an effect.
- **Decoupling:** 0.1µF ceramic per IC; optional small cap across the meter to slow needle settle if desired.
- **Software:** Pi maps pH 4.0–9.0 → 0–FS and moisture 0–100% → 0–FS, writes MCP4728 over I²C. Print the dial scales to match the mapping.

Movement data above is from the Simpson datasheet; R_sense is now fixed by it. Remaining leads (jewel, VCC indicator, Sifam, Weston) are still researched-not-verified — check listing, price and stock before buying.
