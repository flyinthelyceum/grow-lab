# V1 Physical Build

## Objective

Move the working bench prototype into a real, planted object: one cinder-block
vessel, a recirculating drip loop off a bucket reservoir, the full sensor stack
online, lights on a photoperiod, camera pointed. Get something growing, then refine
and align with the final concept.

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

## Water loop (recirculating drip)

Reservoir sits **below** the vessel so one pump lifts feed and gravity returns it —
no siphon, no second pump.

1. **Source** — 2.5 gal bucket + lid. Holds solution, pump, and the pH / EC / water-temp
   probes. Small volume: pH/EC swing faster, top-off more often. Fine for one CMU.
2. **Lift** — SICCE Micra Plus, 158 GPH, submersible. Flow far exceeds two emitters.
3. **Tame** — bypass tee back to the bucket bleeds excess flow for a gentle drip.
4. **Filter** — inline, on the lift side, before the emitters (recirculating feed clogs drippers).
5. **Distribute** — main line up to an overhead manifold, split to two spaghetti emitters.
6. **Deliver** — one drip stake per core.
7. **Return** — drain hole per core → gravity back to the bucket, air gap at the return.

## Lighting decision

- **V1 runs the two white LM301H boards** (via the Meanwell PWM-120-24, ESP32-dimmed).
  LM301H white full-spectrum is an excellent grow light; the plant will thrive.
- **The red/blue color-register has no hardware and is deferred.** The concept
  (blue = dormancy/moon, amber = flowering/fire) can't be expressed by a fixed white
  board — it's dimmable, not tunable in hue.
- **Concept-alignment path (later rev):** add independently-dimmed 660nm deep-red +
  450nm royal-blue supplement channels. White LM301H stays the growth workhorse; R/B
  carries the temporal/emotional register. This gives the canon real hardware without
  compromising the grow.
- **Open spec:** confirm two 96-LED boards fit the PWM-120-24's 120W budget before
  wiring both in parallel.

## Enclosure

Dry electronics box, custom — to be designed and 3D-printed / laser-cut in acrylic.

- One box, mounted **above the water line and to the side** — never over the reservoir.
- **Cable glands** on every penetration; drip loops on all external cables.
- **Mains and DC/signal separated** inside; keep EZO isolator leads clean.
- **Ventilation** for PSU + LED-driver heat, drawn away from the wet zone.
- Houses: Raspberry Pi, ESP32, relay board, PSU (5V), PWM-120-24 driver, OLED on the face.

## Electrical constraints

- **Isolate the EZO probes.** Inline voltage isolator on each of pH and EC — the EC
  circuit corrupts pH in shared water. Pump/solenoid grounds off the sensor path.
- **GFCI** on mains.
- **Drip loops** on every cable into the wet zone.

## Sourcing checklist

On hand: 2× LM301H boards, PWM-120-24 driver, SICCE Micra Plus pump, Pi, ESP32,
BME280, EZO-pH, EZO-EC, DS18B20, SEN0308+ADS1115, camera, OLED.

To buy:

- [ ] Standard CMU (cinder block)
- [ ] Food-safe liner / planter inserts (×2 cores)
- [ ] Coco coir + perlite
- [ ] Mesh screen (drain holes)
- [ ] 2.5 gal bucket + lid
- [ ] 1/4" drip tubing + main line
- [ ] Drip stakes / emitters (×2)
- [ ] Bypass tee + small valve
- [ ] Inline filter
- [ ] Atlas EZO inline voltage isolators (×2) — pH + EC
- [ ] GFCI outlet / adapter
- [ ] Cable glands (assorted)
- [ ] TSL2591 lux breakout (if not already on hand)
- [ ] Canopy circulation fan
- [ ] Acrylic stock for the enclosure (fabricate in-house)
- [ ] pH / EC calibration solutions

## Open items

- Two-board 120W budget check (may need reduced current or a second driver).
- Red/blue supplement channels — concept-alignment decision, deferred.
- Enclosure design — its own print/laser task.

---

## v1 revisions — 2026-09-02 (supersede the "Water loop" and fan/power notes above)

**Irrigation: runoff-to-tray, NO recirculation in v1** — matches the locked canon in
IRRIGATION_SYSTEM.md. Recirculation deferred to a later version for simpler failure modes (a recirc
leak or pump death kills the plant; the piece exists to keep the wolves at bay, so v1 is robust).
- Feed: reservoir (2.5 gal) → SICCE Micra Plus at LOWEST flow → inline filter → **bypass tee returns
  excess UNUSED solution to the reservoir** → main line → **2 pressure-compensating drip emitters
  (~1 GPH each)** into the media. The bypass sheds the pump's overflow — 158 GPH vs the ~2 GPH two
  emitters need is 79× too much. Bypassing unused feed is NOT recirculating runoff.
- **Pump runs in short timed pulses.**
- Drainage: media runoff → **catch tray**, discarded / manually managed, NOT returned to reservoir.
- Pump-GPH note: pressure-compensating emitters deliver rated flow regardless of pump pressure;
  lowest-flow setting + bypass + short pulses tame the SICCE. Fallback if it still over-feeds:
  right-size to a small pump (doc target 200–400 L/hr).

**Fan: Noctua NF-A12x25 PWM chromax.black.swap (120mm, 4-pin PWM, 12V, ~0.06A).**
- Driven by **25 kHz PWM** (ESP32 PWM channel, or Pi GPIO18) — NOT a relay. Resolves the doc
  conflict (WIRING GPIO6 relay vs SYSTEM_ARCHITECTURE GPIO18 PWM) in favor of PWM.
- Adds a **12V rail** (small buck from 24V, or a 12V PSU). Power domains become:
  mains / 24V (LED only) / 12V (fan) / 5V (logic) / 3.3V (sensors). Optional tach wire for RPM.

**Constraints surfaced from the doc scan (honor in the build):**
- pH/EC probes must NOT touch reservoir walls or sit in pump turbulence — place in still water.
- LED strip MUST mount to an aluminum heatsink with free airflow (thermal, LED-life critical).
- Atlas EZO boards ship in UART mode — switch to I²C before bus use.
- Inky e-ink likely carries an EEPROM ~0x50 (free in the current I²C map) — verify on the bus.
- Lighting: confirm ×2 LM301H + PWM-120-24 part numbers (Jared believes specced correctly, 2026-09-02).
