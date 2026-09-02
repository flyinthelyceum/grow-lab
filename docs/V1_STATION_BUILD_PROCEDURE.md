# V1 Station Build Procedure

## Objective

Take the running bench station (nursery pot, 5 gal reservoir, relay fan) to the V1
object described in [V1_PHYSICAL_BUILD.md](V1_PHYSICAL_BUILD.md): CMU vessel with two
lined cores, 2.5 gal reservoir, runoff-to-tray drip with pressure-compensating emitters,
PWM canopy fan on a 12V rail, dry enclosure to the side.

`V1_PHYSICAL_BUILD.md` says *what the station is*. This says *what order to build it in*.

## Relationship to the April runbook

[V1_GO_LIVE_RUNBOOK.md](V1_GO_LIVE_RUNBOOK.md) covered the April 1 go-live — first plant,
nursery pot, single emitter. That build is done and its system has been running since.
It stays as the record of that milestone. This procedure covers the rebuild into the
CMU station and supersedes the April runbook's plumbing and fan steps.

## Build doctrine: the system is alive

A plant is growing and the rig is watering it. Every hour the station is torn down is an
hour the plant is not being watered and the telemetry has a hole in it.

So: **build and prove every new subsystem at the bench, beside the running rig, before
disturbing anything.** Only Stage 4 touches the live system, and it should be a single
short window with everything already tested. Stages 0–3 are non-disruptive. Stage 5 can
happen weeks later while the station runs.

---

## Stage 0 — Resolve the open specs at the bench (non-disruptive)

Two open items gate the build. Both are answered by measurement, not by more reading.

### 0.1 LED two-board budget

**Question:** do both LM301H boards fit the PWM-120-24's 120W / 5A budget in parallel?

The PWM-120-24 is a **constant-voltage** 24V supply. Before applying it, confirm the
boards are the constant-voltage type with onboard current limiting. A constant-current
board driven from a CV supply will run away and destroy itself.

1. Wire **one** board to the driver. Nothing else on the rail.
2. Meter DC current in series with the board's positive lead.
3. `growlab light set 255` (full PWM), let it settle 60 s, read the current.

| One board draws | Verdict |
|---|---|
| ≤ 2.3 A | Both boards fit with margin. Wire in parallel. |
| 2.3 – 2.5 A | Fits with no headroom. Cap `intensity` below 255, or add a second driver. |
| > 2.5 A | Two boards exceed 5 A. Second driver, or run one board in V1. |

Record the measured figure in `BOM.md`. Also check heatsink temperature after 15 minutes
at full power — the boards must be on aluminium with free airflow before this test.

### 0.2 Emitter dose calibration — **read this before setting any schedule**

**This is the biggest behavioural change in the rebuild.** Pressure-compensating emitters
hold ~1 GPH each *regardless of pump pressure*. That is the point of them, and it cuts
delivery to the plant by ~158× versus the unrestricted SICCE.

| Path | Flow to the media |
|---|---|
| SICCE 158 GPH, unrestricted (old rig) | ~166 mL/s |
| 1 GPH pressure-compensating emitter (V1) | ~1.05 mL/s per core |

Per-core dose by pulse length, at 1 GPH:

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
schedule and the cap must change, or the plant is not watered.

**Calibrate rather than guess:**

1. Assemble reservoir → pump (lowest setting) → filter → bypass tee → manifold → both
   emitters, discharging into two measuring jugs.
2. Open the bypass valve until the emitters are dripping steadily, not spraying.
3. `growlab pump pulse 60`, then measure each jug. Expect ~60 mL per core; the two should
   be within about 10 % of each other. A wide split means an emitter is partly blocked.
4. Measure the lined core's usable media volume (fill the liner with water, pour into a jug).
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

1. Bring up the 12V rail: buck module from the driver's 24V output, or a 12V PSU.
   Verify **12V under load** before the fan is connected. The buck taps the 24V output
   only; it must not touch the dimming input.
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
2. Line each core with food-safe pond liner or a planter insert. **No media or root may
   touch bare cement** — raw CMU leaches lime and drives pH alkaline. Check the liner for
   pinholes; it is the whole reason the block is safe to plant in.
3. Measure and record the lined usable volume per core (needed by 0.2 step 4).
4. Hydrate coco coir, mix ~70/30 with perlite, fill both cores to 1–2 in below the rim.
5. Leave the filled block to sit wet for a day. Check runoff pH against a plain-water
   control. Drifting alkaline means the liner is leaking — fix before planting.

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
3. Transplant the corms from the nursery pot into the two lined cores. Keep the root ball
   intact; plant at the depth they were at, claws down.
4. Move the reservoir to the 2.5 gal bucket. Mix to the same pH/EC as the old reservoir —
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

The station runs without this. Do it once the plant is stable.

- Fabricate the acrylic box; mount above the water line and to the side, never over the
  reservoir.
- Cable glands on every penetration, drip loops on every cable into the wet zone.
- Mains separated from DC and signal inside; EZO isolator leads kept clean.
- GX16 bulkheads per run so the station can be disassembled without cutting wire.
- Front panel (meters, e-ink, knobs, pilot) on the door — see the panel and meter-driver docs.
- Ventilation for PSU and driver heat, drawn away from the wet zone.

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
| `[[irrigation.schedules]] duration_seconds` | 10 | from 0.2, order of minutes | PC emitters cut flow ~158× |
| `[irrigation] max_runtime_seconds` | 30 | just above the largest pulse | silently clamps the dose otherwise |
| `[irrigation] min_interval_minutes` | 60 | keep 60 unless events go closer | stuck-schedule guard |
| `[fan] enabled` | absent | `true` | fan moves to GPIO18 PWM |
| `[fan] min_duty` | 20 | per-unit stall floor from Stage 1 | Noctua stall point varies |

---

## What Not To Do

- Do not tear down the running rig before Stages 0–3 pass. The plant is on it.
- Do not set a schedule without doing 0.2. A 10 s pulse waters nothing now.
- Do not raise `max_runtime_seconds` arbitrarily to compensate. It is the stuck-pump
  guard, and the catch tray has to hold whatever it allows.
- Do not put media or roots against bare CMU. Line the cores.
- Do not apply the constant-voltage driver to the boards before confirming they are the
  CV type with onboard current limiting.
- Do not move the plant and change reservoir chemistry on the same day.
- Do not let the pH/EC probes rest against the reservoir wall or sit in pump turbulence.
