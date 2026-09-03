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

Runoff falls to a tray, so — unlike the old recirculating design — **the reservoir no
longer has to sit below the vessel.** Nothing returns by gravity. That freedom is not
optional here: **the reservoir must be raised** or the pump cannot reach the emitters.
See "Station geometry" below for the resolved heights.

1. **Source** — **stainless half-size steam table pan, 6 in deep** (12.8 x 10.4 x 5.9 in,
   ~13 L to the brim), with lid. 2.5 gal sits at ~4.3 in depth with freeboard.
   **Not a tall bucket** — 2.5 gal is 577 in³, only 5.1 in deep in a 12 in bucket, so a
   tall vessel spends cabinet height on air and costs lift you cannot spare. 304 stainless
   matches the tray, is opaque (better algae exclusion than translucent plastic), and its
   lid can be drilled cleanly for the pump cord, feed line and probe leads.
   Holds solution, pump, and the pH / EC / water-temp probes. Small volume: pH/EC swing
   faster, top-off more often. Fine for one CMU. Probes sit in **still water** — off the
   walls and out of the pump's turbulence, which also avoids any fringe effect from the
   metal vessel. Do not bond the pan to ground; the EZO isolators already handle stray
   voltage paths.
2. **Lift** — SICCE Micra Plus, submersible. Read its curve, not its headline: **158 GPH
   at zero head, 0 GPH at 2.8 ft** (its shutoff). Like most aquarium pumps it is
   high-flow / low-pressure — built to circulate inside a tank, not to lift.
   Against two small orifices the pump sits near shutoff and develops ~1.2 PSI.

   **Lift budget — a hard fabrication constraint.** Shutoff is where flow reaches zero,
   not where it is usable; near it the curve goes vertical, so any added restriction (a
   fouling filter, a partly blocked emitter, a kink) drops delivery to nothing. Standard
   practice is to work at half to two-thirds of shutoff:

   | Static lift | Verdict |
   |---|---|
   | ≤ 1.4 ft (17 in) | Design target. Robust to fouling. |
   | 1.4–1.9 ft | Workable, increasingly sensitive. |
   | 1.9–2.8 ft | Fragile. Avoid. |
   | > 2.8 ft | Zero flow. |

   **Measure from the LOW water line, not full.** As the reservoir drains its surface
   drops and lift grows — design for nearly-empty.
3. **Filter** — inline, on the lift side, before the emitters (reservoir feed carries
   particulates that clog drippers).
4. **Bypass** — tee + small valve returning **unused solution** to the bucket. Its job is
   to stop the pump deadheading against two tiny orifices, not to "tame" flow — the
   emitters already limit delivery. Bypassed feed never touches media, so this is not
   recirculation. Open it only as far as the pump needs; every PSI bled is one you do not
   have.
5. **Distribute** — up inside the mast, branching out **just above the media**, not at the
   fixture. Only the LED and its cable continue to the top; carrying water that high would
   spend lift for nothing. Keep the two runs **symmetric** — same length, same height —
   since that, not pressure compensation, is what splits the flow evenly here.
6. **Deliver** — two **~1 GPH drip emitters**, one per core. Note these will **not**
   pressure-compensate: PC emitters need 7.25–10 PSI to regulate and only ~1.2 PSI is
   available, so they act as fixed orifices. That is fine at two emitters side by side at
   equal height — compensation exists to even out many emitters across differing
   elevations and distances, which this is not. Delivery rate is therefore **empirical**:
   measure it (build procedure Stage 0.2) rather than assuming the rated figure.
7. **Pulse** — the pump runs in **short timed pulses** (IrrigationService), not continuously.
8. **Drain** — media runoff → **catch tray**. Discarded / manually managed. **Not**
   returned to the reservoir.

Fallback if measured delivery is unusable: raise the reservoir further, or fit a
higher-head pump (a 12V diaphragm pump reaches 40+ PSI, at the cost of audible ticking —
a real consideration for a gallery piece, where the submersible is near-silent).

## Station geometry (resolved 2026-09-03)

Section drawing: `https://claude.ai/code/artifact/fe1e9c0e-2688-4afb-bc32-4b36c4d76261`

Cabinet plinth at **24 in**, CMU on standoffs in a lift-out tray, mast at the back.

| Element | Height from floor |
|---|---|
| Recessed base / shadow gap | 0–2 in |
| Reservoir shelf | 12 in |
| Water surface — low (design case) | 14.0 in |
| Water surface — full | 16.1 in |
| Cabinet top / tray floor | 24 in |
| Tray upstand | 26 in |
| CMU underside (on 0.75 in pads) | 24.75 in |
| Media surface | 30.9 in |
| **Emitter discharge** | **31.0 in** |
| CMU top | 32.4 in |
| LED fixture | ~46 in |
| **Static lift, low water → emitters** | **17.0 in · 1.42 ft** |

Plan: cabinet **20 x 14 in** (depth set by the reservoir, not the block); CMU 15.625 x
7.625 actual. The reservoir pan at 12.8 x 10.4 leaves ~7 in of cabinet width for the dry
bay.

**Tray is a flush rebate**, not a raised collar — it drops into the cabinet's top frame and
becomes the top surface, flush with the sides. One clean volume, no step.

**Build the reservoir shelf adjustable** — slotted supports. 1.42 ft is comfortable on
paper, but Stage 0.2 decides it, and moving the shelf an inch afterwards should not mean
rebuilding the cabinet.

Wet bay (reservoir) and dry bay (Pi, ESP32, driver, PSU, relay) hard-divided, wet bay
vented — an open reservoir in a sealed box makes a humid box.

### Tray and block interface

- **304 stainless.** Fertiliser salts pit aluminium, and this pan sits in dilute nutrient
  permanently.
- **Do not paint the wetted surface.** Paint in constant salt contact lifts at the edges
  and creeps. Bare bead-blast inside; white powder-coat the **outer** face only, which
  never touches water.
- **The tray carries water, never weight.** Pads rise from the cabinet rail through
  cutouts in the tray floor so the block bears on the carcass. ~50 lb on 16 ga sheet would
  dimple it and destroy the drain fall.
- **The block sits above its own runoff** on 0.75 in pads. Standing in it wicks salts back
  up and defeats the point of runoff-to-tray.
- **No glued-on grate.** Media is retained by the mesh over each core's drain hole, inside
  the liner. Runoff falls clear; lift the tray straight out and nothing moves. An adhesive
  joint in a permanently wet salty seam would fail anyway.
- Size for the worst case: a full `max_runtime_seconds` pulse, not a normal event.

### Mast

Bolts to the **cabinet carcass** — not the tray, not the block — with the tray notched to
clear. Hollow section so tubing and cable run inside. The fixture cantilevers ~10 in
forward of the mast centreline, so the base wants a full-height rear panel in the carcass
rather than a couple of screws.

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

**On hand:** 2x LM301H boards, PWM-120-24 driver, SICCE Micra Plus pump, Pi, ESP32,
i3 InterLink, BME280, EZO-pH, EZO-EC, DS18B20, SEN0308+ADS1115, camera, OLED,
Noctua NF-A12x25, aluminium heatsinks, 1/4" drip tubing + main line, 1 GPH
pressure-compensating emitters x2, bypass tee + throttle valve, measuring jugs.

**Bought:** stainless half-size steam table pans x2 with lids (reservoir + mixing spare).

**Fabricating in-house:** catch tray (304 stainless), cabinet / plinth, mast.

### To buy

- [ ] **Inline filter** — DIG P11-200, 3/4" MPT, **200 mesh stainless screen**, flush cap.
      200 mesh (not 120) because 1 GPH emitter orifices are small. Rated 13 GPM against a
      ~2 GPH need, so it is enormously oversized — which is the point: negligible pressure
      drop when clean, and a long interval before a clog can starve a system that only has
      ~1.2 PSI to give. Flush cap cleans it without disassembly. Needs adapters from
      3/4" MPT down to the main line.
- [ ] **Stainless mesh screen** for the core drain holes, ~20 mesh — coarse enough to drain
      freely, fine enough to hold perlite; a layer of coarse perlite at the bottom of each
      core does the real filtering. Stainless so it does not corrode in nutrient solution.
- [ ] **Core liners x2** — see note below.
- [ ] Standard CMU (cinder block)
- [ ] Coco coir + perlite
- [ ] GFCI outlet / adapter
- [ ] Cable glands (size to actual cable OD)
- [ ] **Fresh pH 4.00 / 7.00 / 10.00 buffers and EC 12,880 uS standard.** The probes were
      calibrated in March; opened buffers drift (pH 10 especially, from CO2 absorption).
      Re-calibrate before go-live rather than trusting six-month-old solution.

### Struck from the list

- ~~Atlas EZO inline voltage isolators x2~~ — **not needed.** The i3 InterLink already
  carries **two isolated EZO circuit slots** plus one non-isolated, and the isolated pair
  is specified for exactly EZO-pH / ORP / DO / EC. pH and EC are the two circuits that need
  it. **Action instead: verify both are seated in the isolated slots, not the non-isolated
  one.** That check replaces a ~$56 purchase.
- ~~TSL2591 lux breakout~~ — the AS7341 already emits `as7341_lux`.
- ~~12V buck module~~ — the fan already runs from a 12V adapter; a buck would only
  consolidate mains cords inside the enclosure.
- ~~Acrylic stock for the enclosure~~ — superseded by the fabricated cabinet.
- ~~2.5 gal bucket + lid~~ — replaced by the stainless pans.

### Note on core liners

Nothing off-the-shelf fits a CMU core well (~5.6 x 5.6 in tapering, 7.6 in deep): nursery
pots are either too wide or too short. Options, in order of preference:

1. **Fabricate them in stainless** to match the tray and pans, with the drain hole and mesh
   built in rather than improvised. Best result and one material through the whole wet
   path — but a 5.6 x 5.6 x 7 in open box is deep and narrow, so check it against the
   brake's throat before committing. A rolled sleeve with a welded base is the easier
   variant.
2. **Food-grade polyethylene sheet** (6 mil FDA) folded into each core. Cheap, conforms,
   invisible below the media surface. The pragmatic v1 answer.
3. Pond liner — workable, but most is fish-safe rather than food-grade certified.

## Deferred to v2

- **Rain from overhead.** Emitters raining across the canopy is wanted as a visual effect
  but forces too many departures at once: two ~1 GPH emitters read as a leak rather than
  rain, a multi-outlet bar needs pressure the SICCE cannot make, lift to fixture height
  runs 2.1-2.7 ft (fragile to dead), the tray must grow to catch splash and drift, and
  overhead water on ranunculus invites botrytis and powdery mildew — every source advises
  watering at the base. The v2 path, if taken: a higher-head pump (>=6 ft), a second
  circuit on a solenoid so rain is a brief scheduled event separate from the irrigation
  that keeps the plant alive, timed for morning so foliage dries across the photoperiod,
  with the fan ramping after.
- Red/blue supplement channels (see Lighting decision).
- Recirculation of runoff (see Water loop).

## Open items

- Enclosure design — its own print/laser task.
- 12V rail: buck off 24V vs. separate PSU (buck is one fewer mains cord).
- Verify the SICCE at lowest flow + bypass actually holds ~2 GPH at the emitters;
  otherwise right-size the pump.
- **Irrigation dose must be measured, not derived.** Two small emitters on a low-pressure
  pump deliver far less than the old unrestricted single-emitter rig, so the bench schedule
  (10 s pulses under a `max_runtime_seconds = 30` cap that silently clamps) almost
  certainly waters too little. How much less is an empirical question — calibrate per
  Stage 0.2 before planting.
- **Confirm the lift before plumbing.** Reservoir water line to the highest point of the
  tubing must stay under the pump's 2.8 ft shutoff, and well under it for usable flow.
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
