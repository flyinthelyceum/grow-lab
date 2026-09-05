# V1 Station Build Procedure

## Objective

Take the running bench station (nursery pot, 5 gal reservoir, relay fan) to the V1
object described in [V1_PHYSICAL_BUILD.md](V1_PHYSICAL_BUILD.md): CMU vessel with two
leached cores, 2.5 gal reservoir, runoff-to-tray drip with pressure-compensating emitters,
PWM canopy fan on a 12V rail, dry enclosure to the side.

`V1_PHYSICAL_BUILD.md` says *what the station is*. This says *what order to build it in*.

## Relationship to the April runbook

[V1_GO_LIVE_RUNBOOK.md](V1_GO_LIVE_RUNBOOK.md) covered the April 1 go-live — first plant,
nursery pot, single emitter. That build is done and its system has been running since.
It stays as the record of that milestone. This procedure covers the rebuild into the
CMU station and supersedes the April runbook's plumbing and fan steps.

## Where this actually stands — 2026-09-05

Read this before the stages. The bench is **not** a running grow:

- **There is no plant.** No corms are planted and nothing is being watered.
- **The pump sits in a bucket with no tubing.** The drip line, emitters, filter, bypass
  tee and manifold are on hand but not assembled, so nothing can be dosed and Stage 0.2
  cannot be run as written until they are.
- **The sensor stack is live and logging** — BME280, DS18B20, EZO-pH, EZO-EC, SEN0308 +
  ADS1115, AS7341, camera — and that telemetry is the thing worth not breaking.
- **The pH probe is failing.** Last calibration gives acid slope 85.2 %, base slope 77.3 %
  (healthy ≥ 95) and a zero offset of −34.78 mV against a ±10 degraded limit. It reads a
  steady 7.00, which is what a dead electrode does. **EC is swinging**, with the pump in
  the same bucket as the probes. Neither is trustworthy until Phase A below.

Earlier versions of this document asserted a growing plant and an irrigating rig. That was
inherited from the April runbook and never revised; it is corrected here rather than in the
historical record, which stays as written.

## The plan, in phases

The six stages below are the procedure. This is the order to do them in given where things
actually stand, what each one is waiting on, and what it costs.

| Phase | What | Stages | Blocked on | Buy |
|---|---|---|---|---|
| **A** | **Instrument triage** — get the probes trustworthy | — | nothing | nothing |
| **B** | **Plumbing + dose calibration** — assemble the drip line, measure real delivery | 0.2 | filter adapters | adapters |
| **C** | **Fan rail** — 12V rail, PWM, gust field on hardware | 1 | nothing | nothing |
| **D** | **Vessel** — leach, drain screens, media, wet test, plant | 2 | **Phase A**, corms | perlite, mesh, corms |
| **E** | **Assembly and go-live** — plumb to the block, migrate, soak | 3, 4, 6 | B, C, D | nothing |
| **F** | **Enclosure** — cabinet, tray, panel, harness | 5 | caliper the meters | acrylic, glands |

**A comes first and it is not optional.** Phase D's gate is *runoff pH within ~0.3 of a
control*. That gate is meaningless read through a failing electrode, and the pH probe is
currently failing its slope check while EC swings with the pump in the same bucket. Doing D
before A means measuring a block with a broken ruler and believing the answer.

**A, B and C are independent of each other** and none of them needs a plant, so they can be
done in any order or in parallel as parts arrive. E needs all three. F is genuinely
deferred — the station runs without it, and it is gated on measurements that need the
Weston movements in hand.

### Phase A — instrument triage

Everything downstream is measurement, so fix the instruments first. No purchases.

1. **Unplug the pump and watch EC for five minutes.** A submersible pump in the same vessel
   as the probes puts both electrical noise and fine bubbles into the water, and EC is a
   conductivity measurement across two electrodes in that water — isolation on the circuit
   side does not help with interference in the solution. If EC settles, that was the whole
   story.
2. **Confirm the DS18B20 is in the same water as the EC probe.** Conductivity moves ~2 %/°C
   and the driver compensates from that reading; a probe dangling in air makes the
   compensation wrong. This causes drift, not wild swings, so check it after step 1.
3. **Recalibrate both probes with fresh solution.** Contaminated buffer reads exactly like a
   dying probe, so this has to happen before condemning anything. pH 4.00 / 7.00 / 10.00 and
   the EC 12,880 uS standard.
4. **Re-run `growlab sensor ph-slope`.** It reports the *last* calibration, so only now does
   the number mean anything.
5. **If pH still fails**, recondition (`docs/BOM.md`, pH probe maintenance) or replace.
   Budget ~$100 and a lead time; decide here rather than discovering it at Phase D.

**Gate:** both probes calibrated within datasheet limits, EC stable with the pump running.

---

## Build doctrine: don't break the instrument

The telemetry is the asset. Every hour the stack is torn down is a hole in the record, and
the sensor chain is the part that took months to get working.

So: **build and prove every new subsystem at the bench, beside the running stack, before
disturbing anything.** Only Stage 4 touches the live system, and it should be a single
short window with everything already tested. Stages 0–3 are non-disruptive. Stage 5 can
happen weeks later while the station runs.

---

## Safety — read this before any stage puts power on

Folded here from the Phase 1 walkthrough, which this document replaces. It is at the
front because it is the only stop-work procedure in the repository and it is worthless
filed at the back.

**Bench prep, before power reaches the pump.** Separate the work into two zones and keep
them separate:

- **Electrical zone** — Pi, relay, breadboard, power supplies.
- **Wet zone** — reservoir, tubing, vessel and media, drain tray.

Then confirm, every time:

- Pi and relay sit physically **above** any water path.
- Every cable crossing between zones has a **drip loop**.
- **No exposed mains wiring near the wet zone.**
- The fan is powered and spinning.

Pass condition: the bench is dry, organised and safe to proceed.

**Stop/abort conditions.** Stop immediately and power down if any of these occur:

- relay stuck ON
- continuous pump run beyond the expected pulse
- visible leak near the electrical zone
- unstable power or a reset loop on the Pi

**When in doubt: disconnect pump power first, then debug.**

---

## Stage 0 — Resolve the open specs at the bench (non-disruptive)

Two open items gate the build. Both are answered by measurement, not by more reading.

### 0.1 LED two-board budget — **RESOLVED 2026-09-02**

**Result:** one board draws **0.72 A at 24 V (~17 W)** warm at full PWM. Two boards ≈
**1.4 A / 33 W** against 5 A / 120 W. Both fit in parallel, no derating. The conclusion is
insensitive to whether the PWM was truly at 255 — even at a pessimistic 1 A per board the
pair uses 40% of the driver.

**The two rules that outlive the measurement.** The PWM-120-24 is a **constant-voltage**
24 V supply. Before applying it to any board, confirm the board is the constant-voltage
type with onboard current limiting: **a constant-current board driven from a CV supply
will run away and destroy itself.** And when first powering a board, **abort if the
current climbs and keeps climbing** rather than settling within a second or two — that is
the constant-current case, and it will not stop on its own.

The full DMM procedure is in git history; this question is closed with 4× margin.

### 0.2 Emitter dose calibration — **read this before setting any schedule**

**This is the biggest behavioural change in the rebuild, and it must be measured rather
than derived.** The old rig ran one emitter on an unrestricted line; V1 runs two small
emitters on a pump with almost no pressure. Delivery drops by a large but *unknown* factor.

Do not compute it from the spec sheet. The pump's 158 GPH is free-flow at zero head; its
shutoff is 2.8 ft (~1.2 PSI). Against two small orifices it operates near shutoff, and no
datasheet gives you the delivered rate at your geometry. An earlier version of this doc
divided the free-flow rating by the emitter rating to get a "158× reduction" — that
compared two numbers that are never true at the same operating point. Ignore it; measure.

**Pressure compensation will not happen here.** PC emitters need 7.25–10 PSI to regulate
and ~1.2 PSI is available, so they act as fixed orifices passing an unknown rate. This is
fine at two emitters side by side at equal height — compensation exists to even out many
emitters across differing elevations and distances. **Symmetric plumbing** does that job
here, so keep the run lengths and heights equal and verify the split in step 3 below.

For reference, *if* an emitter did hold its 1 GPH rating, per-core dose by pulse length
would be:

| Pulse | Dose per core |
|---|---|
| 10 s (current schedule) | 10.5 mL |
| 30 s (current `max_runtime_seconds`) | 31.5 mL |
| 150 s | 158 mL |
| 300 s | 315 mL |
| 600 s | 631 mL |

**The existing 10 s schedule delivers about 10 mL per core — effectively nothing.** And
`IrrigationService.pulse()` silently clamps to `max_runtime_seconds` (`pi/services/irrigation.py:103`),
so with the cap at 30 s no schedule change alone can dose more than ~32 mL. Both the
schedule and the cap must change, or a plant put in this vessel will not be watered.

**Calibrate:**

0. **Measure the lift first** — reservoir **low** water line to the highest point the
   tubing reaches (design for nearly-empty; the surface drops as it drains). Target
   ≤ 1.4 ft; 1.4–1.9 ft is workable but sensitive; above 2.8 ft nothing flows at all.
   The resolved geometry puts this at **13 in / 1.08 ft** — see "Station geometry" in
   V1_PHYSICAL_BUILD.md. Since V1 does not recirculate, the reservoir does not sit below
   the vessel; it sits on a shelf at 28 in, behind the console bay rather than under it,
   which is what buys the lift back. **Build that shelf adjustable** so this can be
   tuned by an inch or two once measured.
1. Assemble reservoir → pump (lowest setting) → bypass tee → filter → manifold → both
   emitters, discharging into two measuring jugs. Keep both runs the same length and height.
2. Open the bypass only as far as the pump needs to avoid deadheading. Every PSI bled is
   one the emitters lose.
3. Run the pump 5 minutes, then measure each jug. **Do not assume ~1 GPH** — the measured
   figure is the real one. The two jugs should be within ~10 % of each other; a wider split
   means asymmetric plumbing or a partly blocked emitter.
4. Measure the core's usable media volume (fill the core with water, pour into a jug).
5. Target roughly 5–15 % of media volume per event, aiming for 10–20 % runoff.
6. Pulse seconds = target mL ÷ your measured mL-per-second.

Then set `duration_seconds` per schedule entry and raise `max_runtime_seconds` to just
above the largest intended pulse — high enough to dose, low enough to still be a
stuck-pump guard. Do not set it arbitrarily high.

**Two consequences to size for now:**

- **Catch tray capacity.** A stuck pump runs until the cap. At `max_runtime_seconds = 700`
  that is ~1.5 L across both cores. Buy a tray that holds **at least 3 L**, not a drip saucer.
- **Reservoir cadence.** Runoff-to-tray returns nothing, so consumption is real. At three
  events a day the 2.5 gal reservoir runs down in:

  | Dose per core | Daily use | 2.5 gal lasts |
  |---|---|---|
  | 150 mL | 0.9 L | ~10 days |
  | 300 mL | 1.8 L | ~5 days |
  | 450 mL | 2.7 L | ~3.5 days |

  Plan on topping off the reservoir and emptying the tray on that cadence. If it lands
  under about four days, consider a larger reservoir before finalising the enclosure.

---

## Stage 1 — 12V rail and fan PWM (bench, non-disruptive)

Goal: the Noctua running under software speed control on the new rail, off the relay.

> **The SH1106 OLED stays through this stage.** Ruled 2026-09-05: the subtract pass
> proposed removing the OLED display subsystem, and it is gated rather than cut, because
> until the Inky Impression is in hand it is the station's **only physical readout** —
> removing it would leave nothing to look at but a browser. Retire it when the Inky is
> installed and its driver works, not before. The pin collision that move creates is
> already recorded below in Stage 5 (the Inky hard-wires BCM17, which is the pump relay).

**The fan is for canopy strength, not cooling.** Air movement thickens stems
(thigmomorphogenesis). It takes no temperature input at all: duty comes from a gust
field over time, blowing in spells of a few minutes and falling to nothing in between,
because intermittent loading is what a stem responds to. Overnight it drops to a stir
rather than stopping — still wet air grows mould. `calm_threshold` in `[fan]` is the
knob: raise it for longer lulls and a quieter piece, lower it for more constant air.
When you sweep the fan in step 4 below you are testing the hardware, not the control
law; `growlab fan status` prints where the gust field is at this moment.

1. Bring up the 12V rail from the fan's own 12V adapter. Verify **12V under load**
   before the fan is connected.
2. Wire the fan's 4-pin connector — GND to common ground, +12V to the rail, PWM to
   **GPIO18 (pin 12)**, tach optional. The fan takes 3.3V PWM directly; no level shifter.
   Fan ground and Pi ground must be common or the PWM has no reference.
3. Enable the fan in `config.toml` (the `[fan]` block is now in `config.example.toml`):

```toml
[fan]
enabled = true
gpio_pin = 18
frequency = 25000
```

4. Sweep it and confirm the response:

```bash
sudo systemctl stop growlab      # FanService owns GPIO18; stop it for a clean sweep
growlab fan status               # config + the duty the ramp would command
growlab fan sweep --dwell 10     # steps 0 / 20 / 40 / 60 / 80 / 100 %, then off
growlab fan set 40               # hold a duty while you measure
sudo systemctl start growlab
```

Watch and listen at each step. Confirm the fan actually stops at 0 and does not stall or
buzz at the lowest non-zero step. If it does, raise `min_duty` — the stall floor varies
unit to unit. Once the service is back up, `/api/fan/status` reports the same picture, and
`POST /api/fan/override` overrides it (admin session required — log in at `/admin/login`).

5. Retire the GPIO6 relay leg. GPIO6 is now free; note it in `WIRING_&_BUSES.md` if reused.

**Gate:** fan responds across the whole range and holds a commanded duty for 10 minutes.

---

## Stage 2 — Vessel preparation (offline, non-disruptive)

1. Drill or confirm a drain hole per core; mesh screen over each.
2. **Leach the block. Coat nothing yet.** Soak it in dilute vinegar (~1/4 cup per gallon)
   for half an hour, then flush repeatedly over a week or two. That pulls out the bulk of
   the free lime, costs nothing, and treats the whole block rather than a surface. Raw CMU
   drives pH alkaline; a leached, yard-aged block has usually shed most of it already.
   **Whether a barrier is needed at all is decided by the gate in step 5, not in advance** —
   see *Note on the cores* in V1_PHYSICAL_BUILD.md for the two options if it fails.
3. Measure and record the usable media volume per core (needed by 0.2 step 4).
4. Hydrate coco coir, mix ~70/30 with perlite, fill both cores to 1–2 in below the rim.
5. Leave the filled block to sit wet for a day. Check runoff pH against a plain-water
   control. Drifting alkaline means the block is still shedding lime — add a barrier and
   re-test before planting (nursery pot per core, or epoxy; see *Note on the cores*).

**Gate:** runoff pH from the filled block tracks the control within ~0.3.

---

## Stage 3 — Plumbing dry run (bench, non-disruptive)

Run the whole water path with **plain water and no plant** for 24 hours.

1. Assemble per `V1_PHYSICAL_BUILD.md`: reservoir → pump (lowest) → inline filter →
   bypass tee and valve → main line → overhead manifold → two PC emitters → cores →
   catch tray.
2. Set the schedule and `max_runtime_seconds` to the Stage 0.2 figures.
3. Run a full day of scheduled events into the tray.
4. Check every joint for weeping, not just dripping. Check the bypass return is quiet and
   below the water line so it does not aerate or splash.
5. Confirm the tray catches all runoff with no overshoot at the edges, and measure how
   full it gets in 24 hours.
6. Probe placement: pH, EC and DS18B20 in **still water**, off the reservoir walls and out
   of the pump's turbulence. Wall contact and turbulence both corrupt readings.

**Gate:** 24 hours, zero leaks, tray comfortably containing a day of runoff.

---

## Stage 4 — Migration window (the only disruptive stage)

Do this in one sitting, with Stages 0–3 already passed. Budget 2–3 hours.

1. Photograph the running rig's wiring before disturbing it.
2. `sudo systemctl stop growlab` — stop the scheduler so nothing fires mid-move.
3. Transplant the corms into the two prepared cores. Keep the root ball
   intact; plant at the depth they were at, claws down.
4. Move the reservoir to the 2.5 gal stainless pan. Mix to the same pH/EC as the old one —
   the plant should not get a chemistry step change and a physical move on the same day.
5. Move the probes across; still water, off the walls.
6. Move the soil moisture probe into one core, at root depth. Note which core — the
   reading now represents that core only.
7. Update `config.toml`: schedule `duration_seconds` and `max_runtime_seconds` from 0.2,
   `[fan] enabled = true`.
8. `sudo systemctl start growlab`, then:

```bash
growlab sensor validate-all
growlab pump pulse 60     # watch it, both cores, then check the tray
curl -s localhost:8000/api/fan/status
```

9. Watch one full scheduled event end to end before leaving it.

**Gate:** all sensors reporting, both cores wetting evenly, fan ramping, no leaks.

---

## Stage 5 — Enclosure and harness (deferred, non-blocking)

The station runs without this. Do it once the planting is established.

- Fabricate the cabinet per "Station geometry" in V1_PHYSICAL_BUILD.md: 20 x 16 x 36 in,
  wet bay and dry bay hard-divided, wet bay vented, reservoir on an adjustable shelf at
  28 in. `cad/` is the authority on every dimension here; `python cad/fabrication.py`
  writes the cut list.
- Electronics mount above the water line and to the side, never over the reservoir.
- **When the Inky Impression goes on the Pi:** it hard-wires BCM17 as BUSY, which is the
  pump relay pin. Set `[irrigation] relay_gpio = 23` (pin 16) and move the relay wire
  before powering up the display. Stack the Inky on the i3 InterLink's pass-through header;
  the two share no pins.
- GX16 bulkheads per run so the station can be disassembled without cutting wire.
- Front panel (meters, e-ink, knobs, pilot) set into the cabinet's **front face**, behind
  the clear fascia; service doors are at the **rear**. See the panel and meter-driver docs.

---

## Stage 6 — Soak and exit criteria

Watch it for 72 hours before calling V1 built.

- [ ] Both cores wetting evenly; soil moisture recovering after each event and drying between.
- [ ] Runoff fraction roughly 10–20 % of dose. Much more is waste; much less risks salt build-up.
- [ ] Reservoir pH holding 5.8–6.2, EC 800–1,200 µS/cm.
- [ ] Fan ramping with canopy temperature, not pinned or stalled.
- [ ] LED heatsink stable at photoperiod temperature.
- [ ] Tray emptied and reservoir topped on the cadence from 0.2 — measure the real rate.
- [ ] No leaks after 72 hours.
- [ ] Telemetry unbroken across the migration; no sensor dropouts in the Observatory.

---

## Appendix A — config delta at migration

| Key | Bench value | V1 value | Why |
|---|---|---|---|
| `[[irrigation.schedules]] duration_seconds` | 10 | from the Stage 0.2 measurement | two low-pressure emitters deliver far less than the old single unrestricted one |
| `[irrigation] max_runtime_seconds` | 30 | just above the largest pulse | silently clamps the dose otherwise |
| `[irrigation] min_interval_minutes` | 60 | keep 60 unless events go closer | stuck-schedule guard |
| `[fan] enabled` | absent | `true` | fan moves to GPIO18 PWM |
| `[fan] min_duty` | 20 | per-unit stall floor from Stage 1 | Noctua stall point varies |

---

## What Not To Do

- Do not tear down the running stack before Stages 0–3 pass. The telemetry record is on it.
- Do not set a schedule without doing 0.2. A 10 s pulse waters nothing now.
- Do not raise `max_runtime_seconds` arbitrarily to compensate. It is the stuck-pump
  guard, and the catch tray has to hold whatever it allows.
- Do not put media or roots against bare CMU. Line the cores.
- Do not apply the constant-voltage driver to the boards before confirming they are the
  CV type with onboard current limiting.
- Do not move the plant and change reservoir chemistry on the same day.
- Do not let the pH/EC probes rest against the reservoir wall or sit in pump turbulence.
