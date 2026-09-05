# V1 Physical Build

## Objective

Move the working bench prototype into a real, planted object: one cinder-block
vessel, a runoff-to-tray drip loop off a stainless pan reservoir, the full sensor stack
online, lights on a photoperiod, camera pointed. Get something growing, then refine
and align with the final concept.

Build order and bench tests: [V1_STATION_BUILD_PROCEDURE.md](V1_STATION_BUILD_PROCEDURE.md).
This doc is the specification; that one is the sequence.

Visual companion (layout, harness, plumbing): the build-map artifact —
`https://claude.ai/code/artifact/cffe52dc-dda8-4a47-ba48-083386d48a31`

## Vessel

- **Standard CMU (cinder block).** The block's own center web divides the two cores —
  no divider to build. Corm 1 (Julia) in one core, corm 3 (Jared) in the other.
- **Seal each core — no liners.** Raw CMU leaches lime and drives pH sharply alkaline,
  hostile to the reservoir and the plant. Leach the block, then coat the core interiors
  then plant in it and let the runoff pH say whether anything more is needed. See *Note on
  the cores* below. If it does drift, a nursery pot in each core is the cheap answer and a
  potable-rated epoxy the thorough one; the block stays honest either way.
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
   metal vessel. Do not bond the pan to ground; the i3's isolated EZO slots already handle stray
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
4. **Bypass** — tee + small valve returning **unused solution** to the pan. Its job is
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

## Station geometry (console layout, 2026-09-04)

Model: `cad/` (build123d → STEP); `viewer.html` in the `growlab-v1-station-cad` CI artifact.
Supersedes the mast-and-head layout of 2026-09-03 (section drawing
`https://claude.ai/code/artifact/fe1e9c0e-2688-4afb-bc32-4b36c4d76261`), kept for the record.

**The instrument panel is in the front face of the cabinet.** Behind it a shallow dry
console bay; behind that the reservoir (wet bay, viewer's left) and the mast (dry bay,
right) side by side. Access is from the **rear**: a door behind the wet bay for the pan.
The cabinet is as tall as that stack needs. The mast is the 2 x 3 hollow section as drawn,
and carries only the LED fixture, the drip line and the LED cable.

| Element | Height from floor |
|---|---|
| Floor to the cabinet's underside (steel frame) | 0–6 in |
| Instrument face — bottom edge | 22.2 in |
| Reservoir shelf | 28 in |
| **Panel centre** | **28.2 in** — read standing, looking down |
| Water surface — low (design case) | 30.0 in |
| Water surface — full | 32.1 in |
| Instrument face — top edge | 34.2 in |
| Cabinet top / tray floor | 36 in |
| CMU underside (on 0.75 in pads) | 36.75 in |
| Tray upstand | 38 in |
| Media surface | 42.9 in |
| **Emitter discharge** | **43.0 in** |
| CMU top | 44.4 in |
| LED fixture (underside) | 57.9 in |
| Mast cap / top of the piece | 59.4 in (59.9 with the arm) |
| **Static lift, low water → emitters** | **13.0 in · 1.08 ft** |

Plan: cabinet **20 x 16 in**. Front to back: front panel 0.75, console bay **3.00 clear**
(INSTRUMENT_HEAD_PLANS.md: meters, Inky, i3 and Pi "both fit inside 3.00 clear"), partition
0.5, clearance 0.25, pan 10.4, rear panel / door 0.75 — **15.65 of 16.00, +0.35 in**. Wet bay
13.0 wide for the 12.8 pan; dry bay ~5 wide with the mast in its rear corner beside the
divider, PSU and driver alongside. CMU 15.625 x 7.625 actual, centred in the tray.

Why this arrangement, in three numbers:

- **Depth.** The pan and the mast no longer share an X, so the 2026-09-03 conflict (pan
  10.4 + mast 3.0 in a 14 in cabinet, 1.15 in short) is gone. 16 in is what the console bay
  in front of the pan costs.
- **Lift.** With the pan *behind* the console rather than under it, the shelf rises to 28
  and the lift falls from 17 in to **13 in** on the same pump — inside the SICCE's design
  target with margin. Putting the pan under a console deck would have pushed the lift to
  ~28 in (2.3 ft: "fragile, avoid"), so that arrangement was not built.
- **Access.** The pan slides out of the rear door at 28 in — working height, not a stoop.

**`PLINTH_H` is the one knob.** Raising the cabinet raises the panel, the block and the
light together; the lift does not change with it. **36 is decided** (2026-09-04, from the
viewer's stand-in-front view): panel centre 28.2 in.

**Tray is a flush rebate**, not a raised collar — it drops into the cabinet's top frame and
becomes the top surface, flush with the sides. One clean volume, no step.

**Build the reservoir shelf adjustable** — slotted supports. 1.08 ft is comfortable on
paper, but Stage 0.2 decides it, and moving the shelf an inch afterwards should not mean
rebuilding the cabinet. The shelf can go up ~0.8 in before the pan no longer clears the
rail, and down as far as the lift allows.

Wet bay (reservoir) and dry bay (mast, PSU, driver) hard-divided behind the console
partition; console bay (Pi, i3, meters, Inky, meter driver) in front of both. Wet bay vented
high in the left side — an open reservoir in a sealed box makes a humid box — and the
console bay vented low in the right side for PSU heat, away from the wet zone.

**Access.** The rear door is the wet bay's full width and height, so the pan comes straight
out. The front panel, with the face in it, is one removable piece: unscrew it and the
console bay is open; the partition stops at the divider, so the dry bay behind it is
reached the same way. The face itself is removable on its own (F1–4) for the instruments.

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
  each core. Runoff falls clear; lift the tray straight out and nothing moves. An adhesive
  joint in a permanently wet salty seam would fail anyway.
- Size for the worst case: a full `max_runtime_seconds` pulse, not a normal event.

### Mast — a shaft for the light, and the console it no longer carries

Study (mast-and-head, superseded): `https://claude.ai/code/artifact/c18075c9-9ca8-4f42-8ba3-2066474b21b6`

The instrument head is gone from the top of the mast; the panel is in the cabinet's front
(§ Station geometry). What remains of the mast is the part that had a structural job.

- **Shaft:** 2 x 3 in hollow section, the 3 in dimension front-to-back — where the
  fixture's moment is. Stands on the carcass floor in the dry bay, bolts through its back
  wall into the **full-height rear panel** (4 x 5/16 through-bolts) beside the divider,
  passes up through a notch in the rail and the tray, and ends at a welded cap at 59.4 in.
  Drip line and LED cable inside; they enter through a grommeted Ø 0.75 pass in the side
  wall over the pan's rim, through a matching pass in the divider. **The sensor loom never
  leaves the cabinet** — probes in the tray and the pan, Pi in the console bay.
- **Fixture:** hangs from the cap. An arm runs forward from the cap over the fixture's back
  edge and a cross bar along that edge carries the fixture, centred over the block; the
  block is centred and the mast is off to the side, so the bar spans the offset. Moment arm
  at the mast, centreline to centreline: **5.75 in** (derived in `cad/`, not asserted).
  Fixture underside 15 in above the media, the same light-to-canopy distance as before.
- **Verify the shaft in bending.** Its section is sized by what it carries, not by
  structure; the load is now the fixture alone rather than the fixture plus a head, and the
  moment goes into a rear panel rather than a flange.
- Bolts to the **cabinet carcass** — not the tray, not the block — with the tray notched to
  clear.

**The console — the instrument behind glass (decided 2026-09-04).** Reference: the
Transparent speaker — a glass box, black metal components, the wiring in view. Ours,
inverted from the first fascia candidate:

- **Fascia: clear 1/4 in cast acrylic**, a band across the whole front from 21.2 to 35.2 in,
  recessed 0.15 in behind the front plane, between 0.5 in chamfers on the cabinet's corners.
  The only holes in it are two for the knob shafts; the dials and the e-ink are read through
  it. Screws through its margins into the sides' front edges and the ledge. Removable.
- **Instrument case: black aluminium**, 9.50 x 12.00 x 2.75. A 1/8 in front plate carrying
  INSTRUMENT_HEAD_PLANS.md's hole schedule (dials, window, jewel, amber, knobs, F1–4), and
  a 16 ga folded box behind it the meters, Inky, i3, Pi and meter driver mount in, closed at
  the back with a Ø 0.75 grommeted loom pass. The plate sits 0.1 in behind the acrylic; the
  case sits on a ply **ledge** and pulls straight out forward once the fascia and the knob
  caps are off — the whole apparatus on a bench, unplugged at one terminal block.
- **What shows beside the case:** a black sheet on the partition (the backplate), the ply
  ledge as a sill, and the loom dropping behind the case through the chase to the PSU and
  driver below, which stay behind the removable lower ply front. Cable discipline is
  visible; plan the runs.
- **How the plate fastens:** the case's side walls carry 0.5 in return flanges folded inward
  at their front edges, tapped M3 on the plate's own F1–4 centres. There is no flange on the
  top and bottom walls — one would reach 0.5625 in behind the plate's edge and foul the
  OFFSET layout's high dial. The side flanges clear every layout the emulator offers.
- **How the fascia is held:** it is not drilled anywhere it would have to reach the carcass
  sides. The band is wider than the front panel, so its side edges are simply captured in
  the sides' rebate; the load is taken by two rows of five M3 countersunk screws — the top
  row into a 0.75 in **ply header** left standing behind the band's top edge, the bottom row
  into the **console ledge**. Edge distance in the acrylic is 0.375 top, 0.875 bottom.
- Console bay 3.00 in clear; 0.44 in behind the case for the loom to turn down. Vent the
  bay (the right-side holes) — the Pi and meter backlights still dissipate.

INSTRUMENT_HEAD_PLANS.md's face schedule, dial-face conversion and layout candidates
stand, on metal now; its acrylic box, flange and mast loom pass are superseded. The plate
is emulated at `/panel`.

**Head internals — checked against datasheets and the running code (2026-09-03):**

- **i3 InterLink + Inky Impression stack cleanly.** The i3 datasheet: it uses only SCL, SDA,
  GND and 3V3, and "all Raspberry Pi pins (including the ones used by i3 InterLink) are still
  available" — it has a pass-through header. The Inky driver uses SPI0 (BCM 8/10/11) plus
  BCM 17 (BUSY), 22 (DC), 27 (RESET), and buttons on 5/6/16/24 per Pimoroni's pinout. Zero
  overlap with the i3. Stack the Inky on the i3's pass-through.
- **The one real pin collision is with our own config, not the i3:** `relay_gpio = 17` drives
  the pump relay, and the Inky hard-wires BCM17 as its BUSY input. **When the Inky is
  installed, move the pump relay to a free GPIO** — GPIO23 (pin 16) is plain, unused, and
  clear of PWM (12/13/18/19), SPI (8-11) and the Inky buttons. One config line; until then
  the bench keeps running on 17 (code takes precedence; the Inky is not on the bench yet).
- **Console depth is 3.00 clear** (the old head's inside dimension). The figures this was
  sized on (a Simpson 1327 at 1.92 in behind the panel) no longer apply — the movements are
  **Weston 301s, and their depth is pending measurement on arrival**. Pi + stacked HATs
  ~1.5 in sit beside the movements, not behind. The console bay is full width, so there is
  room beside the face if the Westons run deep; confirm before cutting the partition.
- **Meters: Weston 301, 3-1/2", centre-zero — 30-0-30 µA and 100-0-100 µA.** The face is
  9.50 wide for two 3.50 in bezels with margins, and the e-ink (6.85 board, 6.30 window)
  sits inside that span. Face height 12.00. **The panel cut and stud pattern in
  INSTRUMENT_HEAD_PLANS.md are still Simpson figures — caliper the Weston bezels and recut
  the schedule before drilling.** The face is emulated at `/panel` on the dashboard.

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

Adding the fan adds a **12V rail** — the fan's own 12V adapter, or a
dedicated 12V PSU. The domains are:

| Domain | Source | Loads |
|--------|--------|-------|
| Mains | GFCI outlet | PWM-120-24, 5V PSU, 12V fan adapter |
| 24V | PWM-120-24 | LED boards **only** |
| 12V | 12V adapter | Noctua fan |
| 5V | Pi PSU | Pi, ESP32, relay board logic |
| 3.3V | Pi / ESP32 regulators | sensors |

## Enclosure

The console bay of the cabinet (§ Station geometry) is the dry electronics box: the front
slice behind the instrument face, partitioned from the wet bay.

- **In front of the water, never over it** — the partition is the wet/dry line, and the
  console bay's vents are on the far side from the wet bay's.
- **Cable glands** on every penetration; drip loops on all external cables.
- **Mains and DC/signal separated** inside; keep the EZO probe leads clean.
- **Ventilation** for PSU + LED-driver heat, drawn away from the wet zone.
- Houses: Raspberry Pi, ESP32, relay board, PSU (5V), 12V fan adapter, PWM-120-24 driver,
  meter driver — behind the face and below it; the dry bay behind the partition takes
  what does not fit beside the mast.

## Electrical constraints

- **Isolate the EZO probes.** pH and EC seat in the i3 InterLink's two isolated slots —
  the EC circuit corrupts pH in shared water. Pump/solenoid grounds off the sensor path.
  **Seating is unverified — confirm before go-live.**
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

Finalised 2026-09-05. Confirmed on hand: CMU, coco coir, GFCI outlet, calibration
solutions, plus everything in the *On hand* list above. Ordered by what blocks a phase —
see *The plan, in phases* in V1_STATION_BUILD_PROCEDURE.md.

**Order now — these block phases B and D:**

- [ ] **Adapters, 3/4" MPT down to 1/4" main line**, for the Rain Bird filter. The filter
      is bought and cannot be plumbed without them. *Blocks Phase B, which blocks
      everything downstream of dose calibration.*
- [ ] **Perlite.** Coco coir is on hand; perlite is not. ~70/30 coir/perlite.
- [ ] **Stainless mesh screen, ~20 mesh**, for the core drain holes — coarse enough to
      drain freely, fine enough to hold perlite. Stainless so it survives nutrient
      solution. A layer of coarse perlite at the bottom of each core does the real
      filtering.
- [ ] **Ranunculus corms x2.** There is no plant. Nothing downstream of Phase D can be
      tested without one, and corms are seasonal — order early or accept a substitute.

**Conditional — do not order until the measurement says so:**

- [ ] **pH probe replacement** (~$100, Atlas ENV-40-pH) — only if the probe fails its
      slope check *after* fresh calibration in Phase A. It is currently failing on
      six-month-old calibration, which is not the same thing. Long lead; decide at Phase A,
      not at Phase D.
- [ ] **Core barrier — buy nothing yet.** Leach, plant, watch runoff pH. Only if it
      drifts: a nursery pot per core (~$2), or PPG AquataPoxy A-6 (1 qt, ~$91) if you want
      the block sealed and the cores bare. See *Note on the cores*.
- [ ] **Fresh buffers** — only if the ones on hand are open and old. pH 10 drifts fastest,
      from CO2 absorption. A stale buffer reads exactly like a dying probe, so this is
      worth being sure about before spending $100 on the probe above.

**Deferred to Phase F (the enclosure) — do not order yet:**

- [ ] **Acrylic stock** for the fascia (fabricate in-house).
- [ ] **Cable glands**, sized to actual cable OD. Sealed pass-throughs that clamp round a
      cable where it enters the enclosure, so water cannot track along the jacket and
      follow it in. Sizes are unknowable until the loom exists.

### Struck from the list

- ~~Atlas EZO inline voltage isolators x2~~ — **not needed.** The i3 InterLink already
  carries **two isolated EZO circuit slots** plus one non-isolated, and the isolated pair
  is specified for exactly EZO-pH / ORP / DO / EC. pH and EC are the two circuits that need
  it. **Action instead: verify both are seated in the isolated slots, not the non-isolated
  one.** That check replaces a ~$56 purchase.
- ~~12V buck module~~ — the fan already runs from a 12V adapter; a buck would only
  consolidate mains cords inside the enclosure.
- ~~TSL2591 lux breakout~~ — **resolved: AS7341 is the V1 sensor**, on the rule that code
  takes precedence over docs because the bench version is already running. The AS7341 has a
  driver, a config section and emits `as7341_lux`; TSL2591 has none of those and claims the
  same 0x39 address.
- ~~2.5 gal bucket + lid~~ — replaced by the stainless pans.

### Note on the cores — sealed, not lined

**No liners.** A bag in a hole is the wrong answer for a piece whose block is meant to stay
honest. Leach the block instead and let the runoff pH decide whether it needs more; any
barrier that does prove necessary goes inside the cores, where it is invisible and the CMU
still reads as CMU.

The problem being solved is unchanged: raw CMU leaches free lime and drives pH sharply
alkaline, which would poison both the plant and the chemistry data the piece exists to make
legible. Two steps, in order:

1. **Leach it first.** Soak the block in a dilute vinegar solution (~1/4 cup per gallon)
   for half an hour, then flush repeatedly with water over a week or two — several rinses a
   day. This pulls out the bulk of the free lime and surface alkalinity. Free, and it works
   on the whole block rather than a coating.
2. **Then plant in it and measure.** Do not coat anything yet. A yard-aged block that has
   been leached has already shed most of its free alkalinity, and the station monitors
   reservoir and runoff pH continuously — which is the whole point of having the
   instrument. Let it tell you whether there is a problem instead of paying to prevent one
   that may not exist. Sources genuinely conflict on how much lime an aged CMU keeps
   shedding; this is cheaper to settle by measurement than by reading.

3. **Only if runoff pH actually drifts**, in ascending order of effort:
   - **A nursery pot in each core**, ~$2 the pair. A 1 gal plastic pot or a fabric pot
     (247Garden 1.5 gal square, 8 x 7 in, food-safe, ~$0.25) drops straight into a core.
     Nothing to cure, reversible, and the plants lift out for inspection.
   - **A potable-rated epoxy** if you want the block itself sealed and the cores bare:
     PPG AquataPoxy A-6, 1 qt, ~$91, NSF/ANSI 61 and rated for damp concrete, which
     matters because the leach leaves the block saturated for weeks. Two coats, ~8 h
     between. This is the spec-grade answer and it is priced like one.

   Note what a permeable liner does and does not do: cloth is a filter, not a barrier, so
   it will not stop lime leaching, and a fabric pot pressed against damp concrete loses the
   air-pruning that justifies fabric pots in the first place. A plastic pot is the honest
   cheap barrier; cloth is neither barrier nor pruning here.

**The existing gate still validates it.** Stage 2's wet test — 24 h with the filled block,
runoff pH compared against a plain-water control, within ~0.3 — tests whatever method you
use. Fail it and leach longer or add a second coat before planting.

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

- **Weston 301 depth and bezel** — caliper on arrival; sets `DIAL_CUT_DIAMETER` and confirms
  the 3.00 console depth.
- **Frame fabrication.** 1 x 1 HSS or solid square bar; welded or bolted at the corners;
  levelling feet in the legs. Whether the mast is welded to the ring or bolted through it
  is a fabricator's call — welded is stiffer, bolted lets the cabinet come off the frame.
- **Case fabrication.** The development is drawn: one 15.50 x 17.00 blank in 16 ga, six
  bends, `cad/out/fab/case_body.dxf`. Powder-coat or anodise black. Confirm the shop is
  happy with folded corners or wants them welded.
- **Fascia edge finish.** Polished or flame-polished edges on the acrylic, and whether the
  two knob holes want a chamfer.
- Verify the SICCE at lowest flow + bypass actually holds ~2 GPH at the emitters;
  otherwise right-size the pump.
- **Irrigation dose must be measured, not derived.** Two small emitters on a low-pressure
  pump deliver far less than the old unrestricted single-emitter rig, so the bench schedule
  (10 s pulses under a `max_runtime_seconds = 30` cap that silently clamps) almost
  certainly waters too little. How much less is an empirical question — calibrate per
  Stage 0.2 before planting.
- **Confirm the lift before plumbing.** Reservoir water line to the highest point of the
  tubing must stay under the pump's 2.8 ft shutoff, and well under it for usable flow. The
  console layout puts it at 13 in on paper.
- Reservoir cadence: runoff-to-tray returns nothing, so the 2.5 gal reservoir needs
  topping every ~3-10 days depending on dose. Consider a larger reservoir if it lands
  under about four days.

## Revision log

See [CHANGELOG.md](../CHANGELOG.md) — it is longer, more specific, and records the
rejected alternatives this log omitted.
