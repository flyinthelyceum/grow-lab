# V1 Physical Build

## Objective

Move the working bench prototype into a real, planted object: one cinder-block
vessel, a runoff-to-tray drip loop off a bucket reservoir, the full sensor stack
online, lights on a photoperiod, camera pointed. Get something growing, then refine
and align with the final concept.

Build order and bench tests: [V1_STATION_BUILD_PROCEDURE.md](V1_STATION_BUILD_PROCEDURE.md).
This doc is the specification; that one is the sequence.

Visual companion (layout, harness, plumbing): the build-map artifact —
`https://claude.ai/code/artifact/cffe52dc-dda8-4a47-ba48-083386d48a31`

## Vessel

- **Standard CMU (cinder block).** The block's own center web divides the two cores —
  no divider to build. Corm 1 (Julia) in one core, corm 3 (Jared) in the other.
- **Seal / line each core.** Raw CMU leaches lime and drives pH sharply alkaline,
  hostile to the reservoir and the plant. Line with food-safe pond liner or planter
  inserts so media and roots never touch bare cement. The seal is invisible; the
  block stays honest.
- **Media:** coco coir + perlite. Mesh screen over each drain hole.

## Water loop (runoff-to-tray, no recirculation)

V1 does **not** recirculate. This matches the locked canon in IRRIGATION_SYSTEM.md and
keeps the failure modes simple: a recirculation leak or a dead pump kills the plant,
and the piece exists to keep the wolves at bay, so v1 is robust. Recirculation is
deferred to a later version.

Reservoir sits **below** the vessel so one pump lifts feed; runoff falls to a tray.

1. **Source** — 2.5 gal bucket + lid. Holds solution, pump, and the pH / EC / water-temp
   probes. Small volume: pH/EC swing faster, top-off more often. Fine for one CMU.
   Probes sit in **still water** — off the walls and out of the pump's turbulence.
2. **Lift** — SICCE Micra Plus, 158 GPH, submersible, set to its **lowest flow**.
   Two emitters need ~2 GPH; the pump is ~79× oversized, so it has to be tamed.
3. **Filter** — inline, on the lift side, before the emitters (reservoir feed carries
   particulates that clog drippers).
4. **Tame** — bypass tee + small valve returns **excess unused solution** to the bucket.
   Bypassing unused feed is not recirculating runoff; the solution never touches media.
5. **Distribute** — main line up to an overhead manifold, split to two lines.
6. **Deliver** — two **pressure-compensating drip emitters (~1 GPH each)**, one per core.
   Pressure-compensating emitters deliver rated flow regardless of pump pressure, so
   lowest-flow + bypass + emitters give a predictable dose.
7. **Pulse** — the pump runs in **short timed pulses** (IrrigationService), not continuously.
8. **Drain** — media runoff → **catch tray**. Discarded / manually managed. **Not**
   returned to the reservoir.

Fallback if the SICCE still over-feeds after the above: right-size to a small pump
(IRRIGATION_SYSTEM.md target 200–400 L/hr).

## Lighting decision

- **V1 runs the two white LM301H boards** (via the Meanwell PWM-120-24, ESP32-dimmed).
  LM301H white full-spectrum is an excellent grow light; the plant will thrive.
- **The LED boards mount to an aluminum heatsink with free airflow.** Thermal is
  LED-life critical; no bare-board mounting.
- **The red/blue color-register has no hardware and is deferred.** The concept
  (blue = dormancy/moon, amber = flowering/fire) can't be expressed by a fixed white
  board — it's dimmable, not tunable in hue.
- **Concept-alignment path (later rev):** add independently-dimmed 660nm deep-red +
  450nm royal-blue supplement channels. White LM301H stays the growth workhorse; R/B
  carries the temporal/emotional register. This gives the canon real hardware without
  compromising the grow.
- **Budget check RESOLVED (2026-09-02):** one board measures 0.72 A at 24 V (~17 W) warm
  at full PWM, so two boards draw ~1.4 A / 33 W against the driver's 5 A / 120 W. Wire
  both in parallel; no derating needed. The driver is ~4x oversized, leaving headroom if
  the lighting is expanded later.

## Airflow

- **Noctua NF-A12x25 PWM chromax.black.swap** — 120mm, 4-pin PWM, 12V, ~0.06A.
- Driven by **25 kHz PWM on Pi GPIO18** (FanService, temperature-triggered ramp) —
  **not a relay**. The V0 bench ran the fan always-on through a relay on GPIO6; V1
  retires that relay. WIRING_&_BUSES.md and SYSTEM_ARCHITECTURE.md now agree on PWM.
- Optional tach wire back to a Pi GPIO for RPM.

## Power domains

Adding the fan adds a **12V rail** — a small buck off the 24V LED supply, or a
dedicated 12V PSU. The domains are:

| Domain | Source | Loads |
|--------|--------|-------|
| Mains | GFCI outlet | PWM-120-24, 5V PSU (and 12V PSU if not bucked) |
| 24V | PWM-120-24 | LED boards **only** |
| 12V | buck from 24V, or 12V PSU | Noctua fan |
| 5V | Pi PSU | Pi, ESP32, relay board logic |
| 3.3V | Pi / ESP32 regulators | sensors |

## Enclosure

Dry electronics box, custom — to be designed and 3D-printed / laser-cut in acrylic.

- One box, mounted **above the water line and to the side** — never over the reservoir.
- **Cable glands** on every penetration; drip loops on all external cables.
- **Mains and DC/signal separated** inside; keep EZO isolator leads clean.
- **Ventilation** for PSU + LED-driver heat, drawn away from the wet zone.
- Houses: Raspberry Pi, ESP32, relay board, PSU (5V), 12V buck, PWM-120-24 driver,
  meter driver, front panel on the door.

## Electrical constraints

- **Isolate the EZO probes.** Inline voltage isolator on each of pH and EC — the EC
  circuit corrupts pH in shared water. Pump/solenoid grounds off the sensor path.
- **Atlas EZO boards ship in UART mode** — switch to I²C before putting them on the bus.
- **Inky e-ink likely carries an EEPROM at ~0x50** (free in the current I²C map) —
  verify on the bus before assigning that address to anything else.
- **GFCI** on mains.
- **Drip loops** on every cable into the wet zone.

## Sourcing checklist

On hand: 2× LM301H boards, PWM-120-24 driver, SICCE Micra Plus pump, Pi, ESP32,
BME280, EZO-pH, EZO-EC, DS18B20, SEN0308+ADS1115, camera, OLED, Noctua NF-A12x25.

To buy:

- [ ] Standard CMU (cinder block)
- [ ] Food-safe liner / planter inserts (×2 cores)
- [ ] Coco coir + perlite
- [ ] Mesh screen (drain holes)
- [ ] 2.5 gal bucket + lid
- [ ] 1/4" drip tubing + main line
- [ ] Pressure-compensating drip emitters, ~1 GPH (×2)
- [ ] Bypass tee + small throttle/ball valve
- [ ] Inline filter
- [ ] Catch tray — **≥3 L**, fits under the CMU (must hold a full `max_runtime_seconds` pulse; see the build procedure, Stage 0.2)
- [ ] Aluminum heatsink stock for the LED boards
- [ ] 12V buck module (24V → 12V) or small 12V PSU
- [ ] Atlas EZO inline voltage isolators (×2) — pH + EC
- [ ] GFCI outlet / adapter
- [ ] Cable glands (assorted)
- [ ] TSL2591 lux breakout (if not already on hand)
- [ ] Acrylic stock for the enclosure (fabricate in-house)
- [ ] pH / EC calibration solutions

## Open items

- Red/blue supplement channels — concept-alignment decision, deferred.
- Enclosure design — its own print/laser task.
- 12V rail: buck off 24V vs. separate PSU (buck is one fewer mains cord).
- Verify the SICCE at lowest flow + bypass actually holds ~2 GPH at the emitters;
  otherwise right-size the pump.
- **Irrigation dose must be recalculated for pressure-compensating emitters.** They cut
  delivery ~158x versus the unrestricted pump, so the bench schedule (10 s pulses, and
  `max_runtime_seconds = 30`, which silently clamps) now waters almost nothing. Calibrate
  per Stage 0.2 of the build procedure before planting.
- Reservoir cadence: runoff-to-tray returns nothing, so the 2.5 gal reservoir needs
  topping every ~3-10 days depending on dose. Consider a larger reservoir if it lands
  under about four days.

## Revision log

- **2026-09-02** — LED two-board budget measured and closed: 0.72 A per board at 24 V,
  ~33 W for the pair, comfortably inside the PWM-120-24.
- **2026-09-02** — v1 is runoff-to-tray (recirculation deferred). Pump tamed with
  lowest-flow + bypass + pressure-compensating emitters + short pulses. Fan moves from
  GPIO6 relay to GPIO18 25 kHz PWM on a new 12V rail. Doc-scan constraints (probe
  placement, LED heatsink, EZO UART→I²C, e-ink EEPROM) folded into the sections above.
