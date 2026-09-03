# Changelog

All notable changes to this project are documented in this file.

## 2026-09-03 (CI concurrency fix)

### Fixed
- **A queued deploy silently stopped CI.** `concurrency: deploy-pi` was declared at workflow level, which gates the whole run rather than just the deploy. After #18 merged, its deploy job sat queued waiting for a self-hosted runner that had not been registered yet — and the next push (#19) produced a run stuck at `pending` with **zero jobs created**, tests included. Nothing reported a failure; CI just stopped happening. Moved the concurrency group onto the `deploy` job, so tests always run and only deploys serialize. Documented in `docs/DEPLOYMENT.md` with a note not to move it back.

## 2026-09-03 (pH probe health, and the probe that died quietly)

### Added
- **`growlab sensor ph-slope`** — reports the EZO-pH `Slope,?` figures: acid and base slope percentages plus the zero-point offset in millivolts, with a verdict. Thresholds are the datasheet's (V6.1, "Understanding pH slope", pp. 68–70), not our judgement: a new probe is >95% slope with an offset within ±5 mV, and past 10 mV it warns of "noticeable performance issues". Slope is the manufacturer's own end-of-life indicator, which makes "recondition or replace" a measurement rather than a guess.
- **`EZOBase.query()`** — send a non-reading command (`Slope,?`, `Status`, `i`) and get its ASCII response, at the datasheet's 300 ms settle rather than the 900 ms a measurement needs. Returns None on any non-success status so a syntax error cannot be read as data.
- **`ProbeSlope` and `parse_slope()`** in `pi/drivers/ezo_ph.py`, with the pre-calibration default (100, 100, 0) recognised as *uncalibrated* rather than as a flawless probe. 26 tests.
- **Part numbers, prices and links** for every Atlas item in `BOM.md` and `SENSOR_STACK.md` — pH probe (ENV-40-pH), EC probe (ENV-40-EC-K1.0), both EZO circuits, storage and calibration solutions, reconditioning kit. Previously the docs named manufacturers but nothing was re-orderable without a search.
- **A pH probe maintenance section** in `BOM.md`: never store dry or in plain/distilled water, slope is the health metric, slope only updates on calibration, and a bad slope can mean contaminated solution rather than a bad probe.

### Recorded
- **A dead pH electrode reads pH 7, not garbage.** A failed probe outputs near 0 mV whatever it is in, which the circuit converts to roughly its isopotential point — pH 7.00 for the ENV-40-pH. So it returns a plausible mid-scale number indefinitely. This is how the summer 2026 failure hid: a flat 8.69 for eight days, read as a real measurement of a neglected reservoir. Moved to pH 4.00 buffer it settled at 6.7–6.8 and drifted up, which is the isopotential point rather than the buffer. **A stable, plausible pH reading is not evidence of a working probe.**

## 2026-09-03 (CI and deploy to the Pi)

### Added
- **`.github/workflows/deploy.yml`** — the repo's first CI, and a path for merged work to reach the hardware. Tests run on a GitHub-hosted runner; deploy runs on a self-hosted runner on the Pi with `needs: [test]`, so the box only ever runs code whose tests passed. Triggers on push to `main` and on manual dispatch.
- **`deploy/github-runner/setup.sh`** — one-time runner install, with a sudoers rule narrowed to restart/start/stop/journalctl on `growlab` and `growlab-dashboard` and nothing else, validated with `visudo -c` before it is installed. A self-hosted runner executes whatever a workflow says, so its privileges are the blast radius.
- **`docs/DEPLOYMENT.md`** — how it works, how to operate it, and why the security choices are what they are.

### Notes
- The deploy job deliberately does not `actions/checkout`. It advances the live clone at `/home/jared/grow-lab`, which is what the systemd units run from and where the gitignored `config.toml` and `.venv` live; a fresh checkout would ship a tree with no configuration. Fast-forward only, so a diverged branch fails loudly.
- It refuses to deploy over a dirty working tree. Anything showing in `git status` there is a hand edit made on the box, and discarding it silently on a machine nobody can shell into is how you lose a fix made during a bring-up.
- Health check polls `/api/system/status`, which opens the database and reports migration state — the thing most likely to break on a schema change. **429 counts as alive**: the API is rate limited at 60/min and a rejected request still proves the server is up. Treating it as failure would have rolled back healthy deploys.
- A failed health check resets to the previous SHA, reinstalls, restarts and fails loudly, so a bad deploy leaves the Pi on the last good revision rather than dark.
- No `pull_request` trigger, by design: a fork PR against a self-hosted runner would execute attacker-authored code on the Pi, on the LAN, before any review.
- Verified the test job passes from a clean venv with only the `[dev]` extras — 698 tests, no `pi` extra, since `RPi.GPIO` and `picamera2` do not build off-Pi and every driver that needs them imports lazily inside `connect()`.

## 2026-09-03 (instrument head emulator)

### Added
- **`/panel` — a digital twin of the instrument head's acrylic face.** True proportion, four candidate layouts, and needles that move the way the movements would. Built to answer two questions before anything is cut: does the arrangement read as an instrument, and is deviation-about-centre actually legible.
- **The needles run the hardware's own maths.** `pi/dashboard/static/panel/meter-math.js` mirrors `normalise`, `apply_calibration`, `ease_alpha` and `differential_codes`, and `tests/unit/test_panel_math_parity.py` runs it under node against the Python across a sweep that includes the endpoints and the exact-half cases where `Math.round` disagrees with Python's round-half-to-even. Verified the test fails when the JS is deliberately drifted. Without that, the emulator would be a drawing — it would happily show a layout that reads well while the real panel read differently.
- **Three sources.** Synthetic generators (drift, step, noise, pegged, dropout) for failure modes that have not happened yet; live from the bench; and **scrub**, which replays real history on a shared bucket grid so both needles move in step. Scrub is the honest test — invented drift can be made to look however you like.
- **Live scale controls.** Centre and span per channel, changing the dial's engraved numbers as you drag. This is the tool for the open EC question: centre is mechanical zero, so where it goes decides where the needle rests in normal operation.
- **`pi/dashboard/panel_geometry.py`** — the face as data, in inches, origin bottom-left, one source for the emulator and for regenerating the hole schedule. Every layout is asserted collision-free and inside the stock, so an unbuildable candidate cannot reach the screen.
- **The Inky window renders**, 800 x 480 in its own reflective register, so a layout is judged as dials-plus-screen together rather than dials beside a grey rectangle.
- 59 tests. Rendered the page in Chromium and fixed three defects found only by looking: a y-flip mirroring every arc and tick, an e-ink waveform sampling 96 frames at 60 Hz (1.6 seconds, so it read flat), and `display:flex` outranking the `[hidden]` attribute.

### Fixed
- **`docs/INSTRUMENT_HEAD_PLANS.md` and `UI_UX_DESIGN_REFERENCE.md` specified the wrong meters.** Both still said Simpson Wide-Vue 1327 and "pH + moisture"; the build uses Weston 301 centre-zero movements and reads pH + EC. The head plans also still carried the retracted milliamp figures (5-0-5 mA / 30-0-30 mA) and a Simpson order table it was possible to order from. Reconciled: correct movements, correct series resistors, op-amp stage gone, and the Simpson cut and stud pattern marked **pending calipers** rather than left standing as if they applied.

### Notes
- Dial cut diameter is deliberately absent from the geometry module rather than estimated. Bezel OD of 3.50 in is nominal for the size class and safe to draw; the cut is a fabrication number, and inventing one would have put a second wrong dimension into the drawings next to the Simpson figures.
- Needle sweep angle is unmeasured too, so it is a control rather than a constant — 90 degrees is typical for the class and it visibly changes legibility.
- A stacked-dial column does not fit the stock: 3.50 + 3.50 for the movements plus 3.78 for the window plus roughly 1.5 of rail is 12.28 in against 12.00 in of face. Drawn, discarded, and asserted in a test so it cannot creep back.
- In the Schedule layout the band between the window's lower edge and the rail is 1.845 in of empty acrylic — the largest void on the face, and now visible.

## 2026-09-03 (cross-process control channel)

### Fixed
- **`POST /api/fan/override` now works.** It never has in production. `create_app` accepted a `fan_service`, but the only caller that builds the app — `growlab dashboard` — never passed one, and the orchestrator never builds an app at all, so `app.state.fan_service` was always None on the Pi and every real request returned 503. CI was green because the tests injected a mock. The endpoint now writes to the control table instead of reaching for a service object that was never there.

### Added
- **`control_state` table (schema v3)** — the channel between the two systemd units. Desired state, not a command queue: one row per control, overwritten in place, NULL meaning "follow the automatic behaviour". Idempotent, restart-safe, nothing to replay. Verified upgrading a populated v2 database in place, since the Pi has one.
- **`ControlService`** (`pi/services/control.py`) — polls the table in the orchestrator and pushes changes into `FanService` and `MeterService`. Edge-triggered, so a steady row does not fight an override set at the bench with `growlab fan set`; change the row and the database wins again.
- **Override expiry.** `[control] override_ttl_seconds` (default one hour) bounds a manual override. This is a safety bound, not a convenience: without it a fan set to 0% from a browser stays there through a hot afternoon. An expired row reads as auto everywhere — the reconciler, `/api/control`, and `/api/meters/status`.
- **`POST /api/meters/override`** — pin a needle from the web, or release it. Admin-gated like the fan override. Lets a movement be checked without stopping the service to run `growlab meter set`.
- **`GET /api/control`** — every control, its effective value, who set it and when it lapses. Read-only, so public alongside the other status endpoints.
- **`[control]` config section**, and `/api/meters/status` now reports an active override so the page and the panel cannot disagree about why a needle is where it is.
- 54 tests. The one that matters is `tests/e2e/test_control_channel.py`: a real FastAPI app holding no service objects, a real `ControlService` holding no web server, two separate repository connections to one database — asserting a click in the process that cannot see the hardware reaches the process that can.

## 2026-09-03 (meters on the dashboard)

### Added
- **`GET /api/meters/status`** — what the two physical needles are pointing at, in JSON. Reports value, unit, reading age, deflection (-1.0 left, 0.0 on target, +1.0 right) and a fault flag for each movement, so the web view and the panel tell the same story.
- **`meters_config` wired through `create_app`** and passed by `growlab dashboard`, so the endpoint sees the real `[meters]` block rather than defaults.
- 9 endpoint tests, including one asserting the endpoint's deflection equals `pi.services.meters.normalise` so the two mappings cannot drift apart.

### Notes
- The dashboard and the orchestrator are separate systemd units — separate processes — sharing only the database. The dashboard therefore cannot hold a reference to the live `MeterService`. This endpoint sidesteps that by recomputing needle position from the same two inputs the service uses: the meter config and the latest reading. It is read-only by construction; commanding a needle from the web would need a channel between the processes that does not exist yet.
- Stale readings read as faulted at centre here, matching how the service eases a stale needle home rather than freezing it.

## 2026-09-03 (meter driver)

### Added
- **MCP4728 quad DAC driver** (`pi/drivers/mcp4728.py`). Fast Write for the animation path — one eight-byte transaction moves both needles — and Sequential Write for the EEPROM power-on defaults, so both needles centre through boot, reset and power-down rather than parking against a stop. Command formats taken from DS22187E section 5.6 rather than from memory. `differential_codes()` turns a normalised deflection into a channel pair, which is the whole of the centre-zero maths and is pure and testable.
- **Meter service** (`pi/services/meters.py`). Reads pH and EC from the repository, maps each to deviation about its target, eases the needle with an exponential time constant at ~30 Hz, and writes both differential pairs together. Faults ease the needle home and raise a flag rather than driving it into a stop. Per-meter five-point piecewise-linear calibration, since the two movements share neither gain nor linearity.
- **`growlab meter` CLI** — `centre`, `set`, `sweep`, `save-centre`, `status`. `sweep` walks the five calibration points so the actual dial readings can be recorded as the `calibration` table; `save-centre` is the one-time commissioning write of the EEPROM power-on state.
- **`[meters]` config** with `[meters.ph]` and `[meters.ec]` blocks, wired through the loader and `main.py`. Disabled by default, per the rule of not enabling a device before it is wired. The EC block carries an inline warning that its `centre` is unresolved pending the target-versus-baseline question.
- 39 unit tests across the driver and service: byte-level assertions on both command formats, the differential maths, calibration interpolation, easing, EC unit scaling, fault-to-centre, override, per-meter channel routing and invert.

## 2026-09-03 (meters verified from the dials)

### Fixed
- **Both meters are MICROAMPERES, confirmed from the printed dials: Weston 301 30-0-30 µA and 100-0-100 µA.** The purchase listings said "milliamperes" and were wrong. Yesterday's cross-check trusted those listing titles over the hardware and propagated the error into a milliamp design — retracting it. The Weston handoff spec was right about the units throughout, and its own instruction ("arrival verification is mandatory: read the lettering on the actual meter") is what caught this.
- **Retracted: the claim that the handoff's resistor table was 1000× wrong.** 56.2 kΩ per leg for ±30 µA and 16.9 kΩ for ±100 µA are correct, and land just under full scale by design so no DAC fault state can overdrive a historic movement.
- **Retracted: the claim that the MCP4728 cannot drive these meters.** That holds for milliamp movements; at tens of microamps the DAC drives each meter directly through fixed series resistors with enormous margin.
- **Op-amp stage dropped from the meter path.** The MCP6004 voltage-to-current stage and the emitter-follower buffer were both answers to a milliamp problem that does not exist. Direct differential DAC drive is simpler and inherently fault-limited. Channel allocation returns to A/B = pH pair, C/D = EC pair, all four in use.
- **Characterisation rig resized, in the other direction.** The handoff's method is right but its 220 kΩ fixed leg reaches only ~6.8 µA, too little to record the endpoint currents the procedure asks for. Sized to approach full scale: 47 kΩ + 1 MΩ pot for the 30 µA movement, 15 kΩ + 1 MΩ pot for the 100 µA.

### Unaffected by the correction
- Sensing stays on the Pi; the DAC is a display peripheral on its I²C bus. The ESP32 re-host would still break a working path and orphan the i3.
- The i3 InterLink's two isolated EZO slots still make separate isolated carriers a redundant purchase.
- The EC dial is still blocked on reconciling an 800–1,200 µS/cm target against a 1,529 µS/cm plain-water baseline, and centring at 2.0 mS/cm would still leave the needle resting well left of centre in normal operation.
- The firmware practices adopted from the handoff stand: midpoint EEPROM startup, five-point per-meter calibration, damped motion, faults easing to centre, hardware current limiting, no trimmer reaching zero series resistance.

## 2026-09-03 (handoff reconciled)

### Changed
- **Second meter reads EC, not soil moisture**, per the Weston handoff spec. EC pairs with pH far better: both are reservoir chemistry from EZO circuits in the same water, sharing the same isolation story, so the two needles read one body of liquid. Moisture is a media value on a different rhythm.
- **Adopted from the handoff:** midpoint DAC codes in EEPROM so needles stay centred through boot and reset; five-point per-meter calibration stored independently of Atlas probe calibration; damped 20–50 Hz motion with a 1.5–3 s time constant; faults ease the needle to centre rather than driving an endpoint; hardware current limiting with no trimmer able to reach zero series resistance; validation under real pump and grow-light switching. These are better than what the BOM carried.
- **Movement characterisation rig resized.** The handoff's method is right — a fixed resistor sets a fault floor below full scale — but its values (220 kΩ from 1.5 V) are for µA movements and yield ~7 µA, which would not visibly move a milliamp needle and could read as a dead meter. Corrected to 300 Ω + 5 kΩ pot for the 5-0-5 mA and 47 Ω + 1 kΩ pot for the 30-0-30 mA.

### Blocked
- **The EC dial cannot be drawn until this project's own EC numbers are reconciled.** `V1_GO_LIVE_RUNBOOK.md` targets 800–1,200 µS/cm while recording the plain-water baseline at 1,529 µS/cm — already above target before nutrients. Either the target is wrong for this tap water or the build needs RO makeup water. The resolved target is the dial's mechanical centre, so this gates the artwork. Centring at 2.0 mS/cm on an 0–4 face, as the handoff proposes, would leave the needle resting 40–60% left of centre in normal operation and defeat the centre-zero concept entirely.

### Rejected from the handoff
- **Moving pH/EC sensing to an ESP32-S3.** The Pi owns the EZO circuits today via `pi/drivers/ezo_ph.py` and `ezo_ec.py` at 0x63/0x64 on the i3 InterLink, logging to SQLite and serving the dashboard, and has since March. Re-hosting sensing on an ESP32 would either break that path or add a relay hop back to the Pi for no gain, and would orphan the i3. Code takes precedence: sensing stays on the Pi, and the MCP4728 goes on the Pi's I²C bus at 0x60 as a display peripheral.
- **Buying two isolated EZO carrier boards.** The i3 InterLink already provides two isolated EZO slots, specified for exactly EZO-pH and EZO-EC. The purchase is only needed on the rejected ESP32 path.
- **Direct DAC-to-meter drive through series resistors.** Sound for the µA movements the handoff assumed; not for the milliamp meters actually bought. Per DS22187E the MCP4728's short-circuit current is 15 mA typical / 24 mA max and ±25 mA is an *Absolute Maximum Rating*, against a characterisation load of 5 kΩ. It cannot drive 30 mA at all, and 5 mA is five times its characterised load. The op-amp stage stays, with an emitter-follower on the 30 mA channel.
- **The handoff's resistor table.** 56.2 kΩ per leg is correct for a ±30 µA movement and 1000× too high for the ±30 mA movement in hand — it would cap the needle at 0.1% of full scale.

## 2026-09-03 (meters sourced)

### Changed
- **Meters sourced: Weston 301 centre-zero milliammeters, 5-0-5 mA and 30-0-30 mA.** Not the end-zero microammeters the driver was drawn for. The needle rests mid-scale and cannot be converted to end-zero without rebuilding the movement — so the dials become **deviation-from-target** instruments. Centre means on target and drift reads as asymmetry, which is the better instrument for tending and settles the pH scale: centre is 6.0, span ±1.0 pH.
- **Meter driver rewritten for bipolar drive.** The unipolar topology could only push current one way. The meter now floats between two op-amp outputs — one buffering a mid-reference, one driven by the DAC — giving signed current on a single 5V rail with no negative supply. The reference is taken from the MCP4728 itself (channel C at 1.024 V) so reference drift is common-mode and cancels; a separate divider would reintroduce it. Channel allocation A = pH, B = moisture, C = V_ref, D spare; 3 of 4 op-amp sections used.
- **R_sense recalculated:** 204.8 Ω for the 5-0-5 mA movement, 34.1 Ω for the 30-0-30 mA, at |V_DAC − V_ref| = 1.024 V full scale.

### Found
- **The MCP6004 cannot drive the 30-0-30 meter to full scale.** From DS20001733L: output short-circuit current ≈25 mA at 5V, and the ±30 mA "Current at Output and Supply Pins" figure is an *Absolute Maximum Rating*, not an operating point. 30 mA full-scale deflection is above the former and at the latter. That channel needs a complementary emitter-follower inside the feedback loop (feedback taken after the buffer, so V_BE drops out); the 5-0-5 channel drives directly with 5× margin. Future meter purchases should prefer 1–5 mA or µA movements, which need no buffer.

## 2026-09-03 (plans)

### Added
- **`docs/INSTRUMENT_HEAD_PLANS.md` — Rev A fabrication schedules for the mast head.** Face hole schedule with laser coordinates (two Simpson 1327 cutouts and their stud holes, the 6.30 × 3.78 in e-ink window, jewel, indicator, two pots, four face fixings), panel schedule for a 9.50 × 12.00 × 3.50 in cast-acrylic box, depth stack, structure, material and finish, and the meter order. Everything on the face sits on the grid the meters set: the rail's jewel and outer knob on the meters' outer mounting-hole columns, indicator and inner knob on the meter centres.
- **Structure:** the acrylic holds instruments, not loads. The shaft ends in a 1/4 in steel flange; the head's bottom panel bolts onto it and the fixture arm attaches to the same plate, so the cantilever's moment goes steel-to-steel and never through the box.

### Decided
- **Meters: Simpson Wide-Vue 3-1/2", Model 1327, 0-50 µA (catalog 04380; taut-band 04381 as the quieter alternative).** Two. Head grows to 9.5 × 12 × 3.5 in to give the 3.25 in bezels a 0.75 in gap and 1.125 in margins; overall height 58 in, panel centre still 52 in.
- **Face: clear cast acrylic, reverse-engraved**, so labels read as frosted marks in glass and the apparatus stays visible through the front. Light-grey opaque as the fallback, decided on the test piece.

### Before cutting
- Test-cut the face in card and offer up the boards. The e-ink is off-centre on its board and its edge tolerance is unpublished; the window and the rail clearance both get confirmed on the test piece, not on paper. Inky standoff holes transfer from the board; they are not pre-cut.

## 2026-09-03 (verified)

### Resolved
- **i3 InterLink / Inky Impression: no conflict.** Read the i3 datasheet: it uses only SCL/SDA/GND/3V3 and passes every Pi pin through. The Inky driver uses SPI0 (BCM 8/10/11) plus 17/22/27 and buttons 5/6/16/24. Zero overlap — stack the Inky on the i3. The earlier "confirm no pin conflict" note was a question that should have been answered, not asked.
- **The real collision is ours: `relay_gpio = 17` vs Inky BUSY on BCM17.** When the Inky is installed, move the pump relay to GPIO23. One config line. The bench keeps running on 17 until then — the Inky is not on it yet.
- **Simpson Wide-Vue dimensions pulled from the Rev. 10-25 datasheet** and recorded in `BOM.md`: 2-1/2" Model 1227 is a 2.47 in bezel, Ø2.22 cutout, 1.85 in behind the panel; 3-1/2" Model 1327 is 3.25 / Ø2.79 / 1.92; 4-1/2" Model 1329 is 4.70 / Ø2.81 / 1.90. Catalog numbers for 0-50 µA (1800 Ω), 0-100 µA and 0-1 mA (43 Ω) movements, and the taut-band 0-50 µA (960 Ω).
- **R_sense is now fixed by the movement data, not pending it:** 40.96 kΩ for 0-50 µA or 2.048 kΩ for 0-1 mA on the MCP4728's 2.048 V reference. Coil resistance only sets op-amp headroom, ~2.1 V either way — fine on 5 V.
- **Head depth (3.5 in) and panel width (9 in) confirmed against real bezels.** 2-1/2" or 3-1/2" meters both fit the face; 4-1/2" would not. Meter depth is 1.85–1.92 in, so 3.5 in is comfortable.

## 2026-09-03 (enclosure)

### Decided
- **The electronics enclosure is integrated into the mast.** The mast is thin where it carries only a drip line and a sensor loom (2 x 3 in) and thickens into an instrument head where the apparatus lives — the same byproduct-of-function logic the front panel is already specced under. The head is 9 x 11.5 x 3.5 in because that is what a 174 x 123 mm Inky Impression 7.3" board and two meter movements measure, not because a size was picked. Fixture at 46 in hangs from the head's *underside* rather than off the shaft, so the cantilever's moment lands over the column instead of bending it. Panel centre at 52 in, overall height 57.5 in. Design study artifact linked from `BOM.md` and `V1_PHYSICAL_BUILD.md`.
- **Split settled:** heavy, hot and mains stay in the plinth (PWM-120-24 driver, 5V PSU, relay board, GFCI); the instrument and its brains go in the head (panel, Pi + i3, ESP32, meter driver). 24V runs up the shaft. Keeps the cantilever light and line voltage far from the panel, and lets the head be only as deep as a meter movement.
- **Panel composition:** meters on top (the instrument — *now*), e-ink beneath (the record — *rhythm*), control rail at the bottom with the jewel where a tube amp puts it. That pairing is what `UI_UX_DESIGN_REFERENCE.md` already asks for, in two registers.
- **One earned accent:** the object is cool throughout — transparent body, hairline engraving, grey ground — and the single warm thing is the lit jewel. No amber in the e-ink palette, no warm wash on the acrylic, no competing second indicator.
- **Lux sensor conflict resolved: AS7341**, on the rule that code takes precedence over docs because the bench version is already running. It has a driver, a config section and emits `as7341_lux`. TSL2591 has none of those and claims the same 0x39 address, so the two could never have shared the bus; the "TSL2591 active" line was aspirational and never implemented.

### Open
- The Inky Impression and the i3 InterLink both mount on the Pi's 40-pin header. Electrically they may coexist (Inky is SPI plus an I2C EEPROM, the i3 is I2C) but physically they collide — resolve with a stacking header or a ribbon extension, and confirm no pin conflict before committing to the head's internal depth.
- Meter movement size drives the panel. Drawn at 2.5 in; going to 3.5 in pushes the meter row past the e-ink's width and the face needs re-proportioning. Pull exact bezel and cutout dimensions from the Simpson datasheet before cutting acrylic.
- Verify the shaft in bending, vent the head, and plan the visible cable runs before assembly.

## 2026-09-03 (corrections)

### Fixed
- **Retracted the acrylic-enclosure strike.** The previous BOM pass struck the acrylic on the grounds that the fabricated cabinet superseded it. That collapsed two objects with opposite jobs: the plinth is furniture and should recede, while the instrument enclosure carries the front panel — jewel pilot lamp, analog meters, e-ink — and should declare itself. Acrylic was also not an arbitrary material: a transparent body is the **Transparent / Material Non-Artifice** register made literal, keeping the apparatus legible rather than hidden in painted casework. The enclosure is restored as a distinct designed object, with its placement relative to the plinth recorded as an open question to settle before the plinth is fabricated (one candidate changes its width).
- **Retracted the TSL2591 strike.** It was struck citing the AS7341, without noting that `BOM.md` explicitly calls TSL2591 the *active* sensor and the AS7341 disabled. The code says the opposite — `pi/drivers/as7341.py` exists and emits `as7341_lux`, there is no TSL2591 driver, and `config.example.toml` carries only `[sensors.as7341]`. Both claim I2C 0x39 and so cannot share the bus. The conflict is now flagged in both docs rather than silently resolved.

### Changed
- **Filter specced as the Rain Bird RBY075MPTX** — 3/4" MPT x MPT, 200 mesh (75 micron) stainless element, o-ring sealed cap, 0.20–12.0 GPM. Equivalent to the DIG part and better documented. Adds the low-flow caveat: at ~2 GPH there is no scouring velocity, so it needs manual flushing rather than self-clearing.
- **Core liners replaced with sealing the block.** No liners — a bag in a hole is wrong for a piece whose block is meant to stay honest. Instead: leach the block first (dilute vinegar soak, then repeated flushing over a week or two), then seal the core interiors with fish-safe / aquarium-grade epoxy, with solvent-free raw linseed oil as the natural alternative. The problem is unchanged — raw CMU drives pH alkaline and would poison both the plant and the chemistry data — and Stage 2's existing wet test still validates whichever method is used.

## 2026-09-03 (BOM pass)

### Changed
- **Inline filter specced** — DIG P11-200, 3/4" MPT, 200 mesh stainless screen with flush cap, on the emitter branch after the bypass tee. 200 mesh rather than 120 because 1 GPH emitter orifices are small. Rated 13 GPM against a ~2 GPH need, deliberately oversized: negligible pressure drop when clean, and a long interval before a clog can starve a system with only ~1.2 PSI available.
- **Sourcing checklist rewritten** to match reality — on-hand, bought, and in-house-fabricated items separated from what is actually left to buy. Several entries had gone stale as parts were acquired or superseded.
- **Core liners** given options rather than a vague "food-safe liner": fabricate in stainless to match the tray and pans (best, but check the brake's throat against a 5.6 x 5.6 x 7 in box), food-grade 6 mil polyethylene as the pragmatic v1 answer, or pond liner with the caveat that most is fish-safe rather than food-grade.
- **Calibration solutions** flagged for replacement rather than reuse — the probes were calibrated in March and opened buffers drift, pH 10 especially from CO2 absorption.

### Removed
- **Atlas EZO inline voltage isolators x2 — struck; they are not needed.** The i3 InterLink already carries two isolated EZO circuit slots (specified for EZO-pH / ORP / DO / EC) alongside one non-isolated slot, and pH and EC are exactly the two circuits requiring isolation. The action is to verify both are seated in the isolated pair, which replaces a ~$56 purchase the BOM had been carrying since before the i3 was in the build.
- **TSL2591 lux breakout** — the AS7341 already emits `as7341_lux`.
- **Acrylic stock for the enclosure** — superseded by the fabricated cabinet.

## 2026-09-03 (later)

### Changed
- **Reservoir specced as a stainless half-size steam table pan, 6 in deep** (12.8 x 10.4 x 5.9 in, ~13 L; 2.5 gal sits at ~4.3 in). Replaces the generic "shallow tub". 304 stainless matches the tray, is opaque so it excludes light better than translucent plastic, and its lid drills cleanly for the pump cord, feed line and probe leads. Geometry is unchanged — water full at 16.3 in, low at 14 in on the 12 in shelf, lift still 1.42 ft.
- **Tray confirmed as a flush rebate**, not a raised collar: it drops into the cabinet's top frame and becomes the top surface, flush with the sides.

### Deferred to v2
- **Rain from overhead.** Wanted as a visual effect, but it forces too many simultaneous departures: two ~1 GPH emitters read as a leak rather than rain; a multi-outlet bar needs pressure the SICCE cannot make; lift to fixture height runs 2.1-2.7 ft, fragile to dead; the tray must grow to catch splash and drift; and overhead watering on ranunculus invites botrytis and powdery mildew, which every source advises against. The v2 path is recorded in `V1_PHYSICAL_BUILD.md`: a >=6 ft head pump plus a second circuit on a solenoid, so rain is a brief scheduled morning event separate from the irrigation that keeps the plant alive.

### Notes
- Checked whether a metal reservoir would disturb the EC probe. Atlas designs its conductivity probes specifically against "fringe effect" — readings shifting near a nearby object — so the stainless pan is fine. Keep probes off the walls as already specced and do not bond the pan to ground; the EZO isolators cover stray voltage paths.

## 2026-09-03

### Added
- **Station geometry resolved** — plinth at 24 in, CMU on 0.75 in pads in a lift-out tray, mast at the back, full height stack recorded in `V1_PHYSICAL_BUILD.md` with a dimensioned section drawing. Cabinet 20 x 14 in, depth set by the reservoir rather than the block.
- **Pump lift budget** — shutoff (2.8 ft) is where flow reaches zero, not where it is usable. Design target ≤1.4 ft, workable to 1.9 ft, fragile beyond, **measured from the LOW water line** since the surface drops as the reservoir drains. The resolved geometry lands at 17 in / 1.42 ft.
- **Tray and block interface spec** — 304 stainless (salts pit aluminium); bare inside, powder-coat the outer face only, since paint in permanent salt contact lifts; load pads rise from the cabinet rail through tray cutouts so the tray carries water and never the block's ~50 lb; block sits above its own runoff; **no glued-on grate**, as the mesh inside each core already retains media.

### Changed
- **Reservoir is a shallow tub, not a tall bucket.** 2.5 gal is 577 in³ — only 5.1 in deep in a 12 in bucket, so a tall vessel spends cabinet height on air and costs lift that is not available. A ~14 x 10 x 6 in tub of the same volume sits on a higher shelf and slides out rather than lifting overhead. This is the difference between a comfortable 1.42 ft lift and a marginal 1.75 ft one.
- **Reservoir shelf must be adjustable** (slotted supports) — the lift figure is settled by the Stage 0.2 measurement, and tuning it should not mean rebuilding the cabinet.
- **Drip line branches just above the media**, not at the fixture. Only the LED and its cable run to the top of the mast; carrying water that high spends lift for nothing.

## 2026-09-02

### Changed
- **Retracted the "pump is ~79x/158x oversized" reasoning.** It divided the SICCE's free-flow rating (158 GPH at zero head) by the emitters' rated draw — two figures that are never true at the same operating point. Replaced across `V1_PHYSICAL_BUILD.md`, `BOM.md`, `IRRIGATION_SYSTEM.md` and the build procedure with the pump's actual curve: 158 GPH at zero head, **0 GPH at 2.8 ft shutoff**, i.e. high-flow / low-pressure. Two real constraints follow, replacing the imaginary one: the manifold has a **hard 2.8 ft ceiling** above the reservoir water line, and at ~1.2 PSI **pressure-compensating emitters cannot reach their 7.25–10 PSI regulating range** — they act as fixed orifices. Harmless at two emitters of equal height, where symmetric run lengths do the same job, so the on-hand emitters stay. Delivery rate is now explicitly an empirical measurement (Stage 0.2), not a derived figure.
- **Reservoir height is no longer constrained.** It sat below the vessel to allow gravity return; V1 does not recirculate, so nothing returns. Raising the reservoir is now the cheapest remedy if measured flow is marginal. Recorded in the build doc and as step 0 of the Stage 0.2 calibration.
- **Inline filter spec revised** to 120–155 mesh, physically oversized, mounted on the emitter branch **after** the bypass tee rather than on the pump outlet — it then passes only the emitter trickle, so its pressure drop is negligible. Pressure, not filtration, is the scarce resource. Notes the pump's built-in intake sponge as first-stage.

### Validated (V1 bench)
- **LED two-board budget closed** — one LM301H board measures **0.72 A at 24 V (~17 W)** warm at full PWM (Fluke 115, series DC). Two boards ≈ 1.4 A / 33 W against the PWM-120-24's 5 A / 120 W, so both wire in parallel with no derating and ~4x headroom. Cold draw was 0.69 A, rising as junction temperature climbed and forward voltage fell — expected on a constant-voltage rail, and it converged. Recorded in `BOM.md`; the open item is struck from `V1_PHYSICAL_BUILD.md`.

### Docs
- **Build procedure Stage 0.1** — spelled out the DC-current measurement (series insertion, A-jack/COM, the Fluke 11x AC-default gotcha, returning the lead to VΩ) and dropped the "let it settle 60 s" instruction, which assumed a meter without a duty-cycle limit on its high-current range. Records the bench meter as a Fluke 115 (10 A continuous, so no time limit at the ~2 A expected), notes that an AC-only clamp cannot make this measurement at all, and adds a wall-wattmeter fallback that answers the same question comparatively.

### Added
- **`growlab fan` CLI** (`pi/cli/fan_control.py`) — `set`, `sweep`, and `status` subcommands for canopy-fan bring-up at the bench. `sweep` steps 0/20/40/60/80/100% with a configurable dwell to verify PWM control and find the per-unit stall floor, then returns to 0 and releases the pin. Fills the gap where the fan was the only actuator with no CLI. 8 e2e tests.
- **`[fan]` section in `config.example.toml`** — the fan stack (config, driver, service, API, tests) existed end to end but the example config never carried the block, so a Pi provisioned from it got no fan control. Values match the `FanConfig` defaults (GPIO18, 25 kHz), left `enabled = false` per the rule of not enabling a device before it is wired.
- **`docs/V1_STATION_BUILD_PROCEDURE.md`** — build order for the CMU station: bench-resolve the open specs (LED two-board budget, emitter dose calibration), 12V rail and fan PWM bring-up, vessel prep, 24h plumbing dry run, a single migration window, then enclosure and soak. Records that pressure-compensating emitters cut delivery ~158x, so the bench schedule (10 s pulses under a 30 s `max_runtime_seconds` cap that silently clamps) must be recalculated before planting, and sizes the catch tray and reservoir cadence off that.

### Fixed
- **Dashboard app route tests** — Starlette >=1.6 keeps included routers in `app.routes` as opaque `_IncludedRouter` entries instead of flattening their `Route` objects, so `[route.path for route in app.routes]` raised `AttributeError` and three tests failed on a fresh install. The app is unaffected (all 20 routes register and serve); the tests now assert served behaviour — OpenAPI paths, a `TestClient` GET on `/`, and a real websocket connect on `/ws/updates`.

### Docs
- **V1 irrigation locked as runoff-to-tray** — no recirculation in V1 (deferred). SICCE Micra Plus tamed with lowest-flow setting, bypass tee returning unused feed, short pulses, and pressure-compensating ~1 GPH emitters ×2. Folded into `V1_PHYSICAL_BUILD.md`, `BOM.md`, and `IRRIGATION_SYSTEM.md`.
- **Fan moves from relay to PWM** — Noctua NF-A12x25 PWM on Pi GPIO18 at 25 kHz (matches `FanService` / `fan_pwm.py`), fed from a new 12V rail (buck off 24V or 12V PSU). `WIRING_&_BUSES.md` fan-relay section, power domains, and pin map rewritten; GPIO6 relay retired. Resolves the WIRING (GPIO6 relay) vs SYSTEM_ARCHITECTURE (GPIO18 PWM) conflict.
- Build constraints from the doc scan recorded in the build doc: pH/EC probes in still water off the reservoir walls, LED boards on an aluminum heatsink, EZO boards switched UART→I²C before bus use, Inky e-ink EEPROM likely at 0x50.

## 2026-04-14

### Added
- **Soil moisture sensor online** — DFRobot SEN0308 (IP65 capacitive) via ADS1115 16-bit ADC. Polling every 300s, emits `soil_moisture` reading in %. Driver maps ADS1115 raw voltage linearly: ~3.0V → 0%, ~1.1V → 100%. Registered at I²C 0x48 (ADS1115, ADDR→GND), SEN0308 analog output on A0.

### Fixed
- **Pi `config.toml`** — corrected `[sensors.soil_moisture]` address from `0x36` (stale STEMMA reference) to `0x48`, and set `enabled = true`.

### Docs
- `SENSOR_STACK.md` — replaced STEMMA Soil Sensor (0x36) with DFRobot SEN0308 + ADS1115 (0x48) as the active media moisture sensor. Updated I²C address table and summary.
- `WIRING_&_BUSES.md` — updated I²C device list, bus topology, and Pi pin map to reflect ADS1115 + SEN0308.

## 2026-03-24

### Added
- **AS7341 spectral light sensor driver** (`pi/drivers/as7341.py`) — fixed-address I2C spectral sensor at `0x39`. Emits `as7341_lux` plus `as7341_415nm`, `as7341_445nm`, `as7341_480nm`, `as7341_515nm`, `as7341_555nm`, `as7341_590nm`, `as7341_630nm`, `as7341_680nm`, `as7341_clear`, and `as7341_nir` in a single poll cycle. Unit tests cover availability, read success, and failure handling.
- **AS7341 config & registry** — sensor entry in `config.example.toml` (disabled by default), I2C address map, and auto-registration in `build_registry()`.
- **Lighting PWM logging** — `LightingScheduler._log_reading()` saves PWM values as `light_pwm` sensor readings on transitions, enabling dashboard chart history.
- **ESP32 reconnect & self-healing** — `ESP32Serial.reconnect()` method. `LightingScheduler` tracks consecutive failures and auto-reconnects after 3, preventing silent light-off on serial port loss.
- **systemd service for main process** (`deploy/systemd/growlab.service`) — `Type=notify` with `WatchdogSec=300`, start limits, dependency ordering with dashboard service.
- **Systemd watchdog heartbeat** in `pi/main.py` — sends `READY=1` on startup, `WATCHDOG=1` every 120s via `NOTIFY_SOCKET`.
- **Decoupled lighting scheduler** — creates independent ESP32 serial connection when pump uses GPIO relay, preventing serial port conflicts.

### Fixed
- **Dashboard LIGHT panel** — now displays live PWM data from `light_pwm` sensor readings (was showing stale/nonexistent data). Dynamic unit label (`lx` vs `PWM`) in HTML template. Cache-busting `?v=2` on `observatory.js`.
- **Light chart** — auto-detects AS7341 lux vs PWM data: smooth CatmullRom curve for lux, StepAfter for PWM. Dynamic Y-axis scaling and hover tooltips.
- **Lighting failure handling** — `_set_pwm` no longer updates `_current_pwm` on failure, forcing retry on next scheduler tick instead of silently accepting the failure.
- **Dashboard service hardening** — added `After=growlab.service`, `Restart=always`, start limits.

### Docs
- AS7341 added to BOM, SENSOR_STACK I2C address table, and WIRING_&_BUSES I2C device list.

## 2026-03-20

### Added
- **Dream Mode** (`/dream`) — WebGL particle visualization using Three.js. Phase A live-data ancestor of dream mode's eventual self-referential form (where the system metabolizes its own biography across accumulated sensor history). 50K additive-blended point sprites driven by a 3D curl noise flow field. Sensor data modulates visuals in real time: temperature→particle color (blue→teal→amber), humidity→particle density, pressure→flow amplitude, irrigation→cyan burst events. UnrealBloomPass post-processing for atmospheric depth. Auto-orbit perspective camera. 60fps animation loop with visibility pause. Auto-downscales particle count on weaker GPUs.
- `/dream` route added to dashboard. Nav links from Observatory and Art views.
- 7 new e2e tests for Dream Mode page.

### Fixed
- **Dream Mode temperature conversion** — BME280 reports unit as `°C`, not `"celsius"`. Conversion logic now assumes Celsius unless unit is explicitly `°F` or `"fahrenheit"`.

### Validated (Phase 3 Hardware)
- Atlas EZO-pH circuit online at I2C 0x63 via i3 InterLink HAT. 3-point calibration: pH 4.00→3.998, 7.00→6.995, 10.00→10.011. Polling every 300s.
- Atlas EZO-EC circuit online at I2C 0x64 via i3 InterLink HAT. 2-point calibration: 12,880 µS/cm and 80,000 µS/cm. Polling every 300s.
- EZO circuits switched from UART to I2C mode via PGND-TX pin short (no USB-UART adapter needed).
- Reservoir baseline: pH 8.3, EC 1,529 µS/cm in plain water.
- All 4 sensors passing `growlab sensor validate-all`: BME280, DS18B20, EZO-pH, EZO-EC.

### Infrastructure
- **Tailscale** installed on grow-lab Pi (100.77.46.126). SSH and dashboard accessible from anywhere.
- `httpx` added to Pi venv (required by NotificationService at runtime).

## 2026-03-19

### Fixed
- **Irrigation pump safety** — pump state flags (`_pump_active`, `_last_activation`) now set only after hardware confirms success. `try/finally` ensures pump-off even if a DB write fails mid-pulse. Concurrent pulse guard rejects overlapping activations.
- **Fan error visibility** — fan control loop exceptions upgraded from `debug` to `error` with traceback. Silent fan failure on a grow system is a plant-killing heat event.
- **XSS in alert timeline** — tooltip switched from D3 `.html()` to safe DOM construction (`.textContent`). Alert descriptions no longer interpreted as HTML.
- **EZO UART port safety** — `serial.Serial` constructor moved into `with` context manager so port-open failures don't cause `NameError` in cleanup.
- **SMTP password leak** — `EmailConfig.__repr__` now redacts `smtp_password` so logging the config object doesn't expose credentials.
- **GPIO.setmode collision** — extracted shared `_gpio.py` module; `setmode(BCM)` called once and cached instead of repeated per-call in both `fan_pwm.py` and `gpio_relay.py`.
- **Service start() guards** — `AlertService` and `FanService` use `is_running` property instead of `_task is not None`, allowing restart after a crashed task.
- **Alert logging** — rule evaluation errors and `on_alert` callback exceptions upgraded from `debug` to `warning` so they appear in production logs.
- **Notification service** — shared `httpx.AsyncClient` (was creating one per webhook call); `raise_for_status()` on webhook responses (was treating 4xx/5xx as success); cooldown recorded on attempt not success (prevents notification storm on repeated failures).
- **WebSocket interval leak** — art mode `setInterval` for WS updates now cleared on close before reconnect, preventing accumulated duplicate intervals.
- **Midnight sliver gap** — radial and humidity rings add 0.003 radian overlap per wedge to eliminate sub-pixel rendering gaps at midnight boundary.

### Added
- **Art view distance-based hover** — when mouse is in the overlap zone between temperature and humidity rings, the closer ring wins hover priority instead of humidity always dominating. Water markers still take top priority.
- **Observatory chart hover** — crosshair + tooltip on all data graphs (air temp/humidity, pH, EC, light). Vertical guide line with colored dots on data lines and auto-positioned tooltip showing time and values. Shared `chart-hover.js` utility supports single and dual-axis charts.

### Added
- **Fan duty override** — `POST /api/fan/override` accepts `{"duty": 0-100}` for manual control or `{"mode": "auto"}` to resume temperature ramp. FanService tracks override state; control loop skips temp calculation when override is active. Returns 503 when fan service is unavailable (standalone dashboard mode).
- **WebSocket server-push for alerts** — new `ConnectionManager` maintains active WebSocket connections and broadcasts alert events in real time. AlertService accepts an `on_alert` async callback, fired on every warning/critical transition. Dashboard JS handles `{"type": "alert"}` push messages alongside existing poll responses.
- **Alert history timeline** — D3.js horizontal dot timeline strip between alert banner and main grid. Warning dots in amber, critical in red, with hover tooltips showing description and timestamp. Fetches `/api/alerts?limit=100`, refreshes every 60s.
- **Gallery lightbox** — clicking a capture thumbnail opens a full-screen overlay instead of replacing the camera feed inline. Close by clicking outside or the CLOSE button.
- **Gallery empty state** — "No captures yet" placeholder shown when no images are available.
- 18 new unit tests: fan override (6), connection manager (6), alert callback (2), API endpoint (4).
- **Notification service** — `NotificationService` dispatches alert events via webhook (POST JSON) and email (SMTP) channels with per-sensor cooldown to prevent notification storms. Configured via `[notifications]`, `[notifications.webhook]`, and `[notifications.email]` in config.
- **EZO UART mode-switch driver** — `ezo_uart.py` sends `I2C,<addr>` command over UART to switch Atlas EZO sensors from UART to I2C mode.
- **`growlab sensor ezo-setup`** CLI command — interactive UART→I2C mode switch for EZO pH/EC sensors with automatic I2C bus verification after reboot.
- **`growlab sensor validate-all`** CLI command — scans all hardware buses, reads every detected sensor, and reports pass/fail with human-readable values (temperatures in °F).
- 23 new unit tests: EZO UART driver (7), notification service (16).

### Changed
- `create_app()` now accepts optional `fan_service` and `connection_manager` parameters for runtime wiring.
- WebSocket route registers/unregisters connections with ConnectionManager on connect/disconnect.
- `main.py` wires alert callback from AlertService to ConnectionManager broadcast and NotificationService dispatch.
- AlertService now passes `sensor_id` as event metadata for per-sensor notification cooldown.
- `httpx` moved from dev to core dependencies (used by webhook notifications at runtime).

## 2026-03-18

### Added
- **AlertService** wired into `growlab start` — monitors BME280 temperature, humidity, EZO-pH, and EZO-EC against configurable threshold rules. Logs `alert_warning` and `alert_critical` system events on state transitions with automatic deduplication (fires once per transition, not per poll). First live alert caught immediately: humidity critical at 26.1%.
- **FanService** wired into `growlab start` behind `fan.enabled` config flag — polls air temperature every 30s and adjusts Noctua NF-A12x25 PWM duty cycle along a linear ramp (20–100% across 70–85°F). Validated live on Pi at GPIO 18 with 12V supply.
- **LightingScheduler** wired into `growlab start` as a background service — runs photoperiod schedule with sunrise/sunset ramps when ESP32 is the pump controller (provides LED PWM). Logs info message when ESP32 is not connected.
- Camera capture timing changed from `on_pulse_complete` (after pump off) to `on_pulse_start` with 3-second delay (while relay LED is still lit). Confirmed via camera capture showing relay LED active.
- `on_pulse_start` callback and `pulse_start_delay` parameter added to `IrrigationService.pulse()` with error isolation — callback failure does not prevent pump shutoff.
- 4 new tests for pulse-start callback: fires during active window, skipped for short pulses, error isolation, coexistence with `on_pulse_complete`.

### Fixed
- Default `pytest -q` collection restored by aligning display tests to the current `render_system_page` API instead of the removed `render_status_page` name.
- `growlab start --config <path>` now honors the provided config path instead of reloading defaults.
- Observatory history fetches now use the documented downsampled REST endpoint rather than the raw readings route.

### Added
- `config.demo.toml` for safe off-hardware dashboard work with repo-local demo data under `./.demo-data/`.

### Changed
- README and architecture docs now describe the current local demo workflow, browser-test requirements, and the downsampled-history data path used by both dashboard views.
- Retired standalone `demo.html` and `art-demo.html` snapshots in favor of the real FastAPI-backed demo workflow.

## 2026-03-17

### Added
- **Web Dashboard (Observatory view)** — 5-panel layout (LIGHT, WATER, AIR, ROOT, PLANT) with live sensor values, D3.js charts, and WebSocket updates.
  - LIGHT panel: StepAfter chart with photoperiod band.
  - WATER panel: EKG-style pulse timeline of irrigation events.
  - AIR panel: dual-axis CatmullRom chart (temperature + humidity overlaid).
  - ROOT panel: stacked sparklines for pH and EC with target range bands.
  - PLANT panel: soil moisture D3 arc gauge + camera feed.
  - Time window selector: 1H / 24H / 7D.
  - Per-panel optimal range indicators and human-readable timestamps.
  - Footer with WebSocket status, sensor count, and ART mode link.
- **Art Mode (generative visualization)** — full-screen Canvas 2D radial visualization driven by live sensor data.
  - Radial thermal ring: 24h temperature mapped to color-graded wedges with radial gradients.
  - Humidity breathing ring: teal-cyan band with sinusoidal opacity modulation.
  - Water pulse markers: bright cyan dots at irrigation event angles with pulsing halos.
  - Pressure atmosphere: colored radial gradient background with isobar rings.
  - Ambient particle system: 120 particles with lifecycle fade, sine-wave drift, breathing opacity.
  - Cross-layer hover system: center disc shows context-sensitive info with priority routing (water > humidity > temperature).
  - WebSocket integration for live temperature, pressure, and irrigation updates.
  - Re-fetches 24h history every 5 minutes.
- **EZO-pH driver** — Atlas Scientific EZO-pH I²C driver with calibration support.
- **EZO-EC driver** — Atlas Scientific EZO-EC I²C driver with temperature compensation.
- **ADS1115 soil moisture driver** — 16-bit ADC driver for DFRobot SEN0308 capacitive sensor.
- CSS typography scaling with fluid `clamp()` values, panel accent colors, value transitions, and responsive breakpoints.

### Changed
- Dashboard header renamed to "GROWLAB".
- All temperature values displayed in Fahrenheit across dashboard and art mode.
- All sensor labels use plain English names (Air, Humidity, H₂O Temp) instead of raw IDs.
- Dashboard camera panel now explains missing/stale capture states more clearly and loads the latest image via API-served file URLs instead of assuming a static captures mount.
- ROOT and PLANT panels now show sensor-availability notes so hardware-blocked fields read as pending instrumentation instead of silent blanks.
- Art Mode now includes a lightweight live readout for temperature, humidity, and last irrigation timing to make on-device walkthroughs easier.
- Art Mode thermal ring geometry now uses a calmer, more centered soft wobble with reduced radial deformation and stronger smoothing.

### Fixed
- Dashboard image serving path aligned with stored camera capture records through `/api/images/<filename>/file`.
- Dashboard route/browser tests updated to the current `GROWLAB` branding and Canvas-based art mode implementation.

### Added
- `growlab db seed-demo` command for generating synthetic 24h-friendly dashboard data, irrigation events, and a demo camera capture while hardware is still in transit.
- `deploy/systemd/growlab-dashboard.service` for running the dashboard persistently on the Pi via `systemd`.

## 2026-03-14

### Fixed
- OLED driver switched from SSD1306 to SH1106 controller (GME12864 modules). Added configurable `controller` field in DisplayConfig with `persist=True` to hold display content after process exit.
- Camera driver updated from `libcamera-still` to `rpicam-still` (Pi OS Bookworm naming). Falls back to legacy command for older OS versions.
- GPIO relay driver updated to support active-low relay modules (SunFounder 8-channel board). Initial pin state set correctly to prevent relay click on startup.
- Display sensor labels changed from raw IDs to human-readable names ("Air", "Humidity", "H2O Temp"). DS18B20 lookup uses prefix matching to handle serial-numbered sensor IDs.
- All temperature readings converted from Celsius to Fahrenheit on OLED display.
- OLED header renamed from "LIVING LIGHT" to "GROWLAB".
- Pump soak failure root cause identified: IrrigationService was not wired into `main.py` during the March 13 overnight run (fix committed same day but after soak launched).

### Added
- OLED display service wired into `main.py` startup/shutdown. Rotates through 4 pages every 5s: sensor values, system overview (uptime + subsystem status), irrigation schedule with last pump event, sparkline trend chart.
- Camera capture triggered after each pump pulse via `on_pulse_complete` callback in IrrigationService. No fixed-interval timer — captures only on irrigation events.
- `luma.oled` added to `[pi]` optional dependencies in `pyproject.toml`.
- MJPEG streaming server for camera aiming (`/tmp/mjpeg_server.py` — temporary, not committed).

### Validated (Phase 2 Hardware)
- BME280 detected and polling at 0x76 (air temp, humidity, pressure).
- DS18B20 stable at ~19.75°C (67.6°F).
- OLED (SH1106, GME12864) displaying on I²C 0x3C with all 4 page rotations confirmed.
- Pi Camera Module 3 (IMX708) capturing at 2304×1296 and 4608×2592 via rpicam-still.
- SunFounder 8-channel relay (active-low) switching pump on GPIO17.
- Pump-triggered camera capture verified end-to-end (pump fires → camera captures → image saved to DB).
- Overnight soak #2 launched: all sensors polling, irrigation at 08:00/14:00/20:00 UTC, camera on pump events, OLED rotating.

### Hardware Notes
- Rewired Pi to RSP-GPIO-8 breakout board (cleaner breadboard layout).
- GME12864 OLED confirmed as SH1106 controller, not SSD1306 — both init without error at 0x3C but only SH1106 renders pixels.
- SunFounder 8-channel relay uses active-low logic (LOW = relay ON). JD-VCC jumper must bridge to VCC for coil power from Pi 5V rail.
- Noctua NF-A12x25 PWM fan control deferred — runs at full speed through relay for V0. PWM/tach wires can connect directly to Pi GPIO when ready (3.3V logic compatible).
- User has thousands of ESP32-WROOM-32U modules available; current build uses ESP32-S3 N8R8 for native USB convenience but 32U is a drop-in replacement with UART bridge.

## 2026-03-13

### Fixed
- ESP32-S3 serial timeout fully resolved. Three root causes identified and fixed:
  1. PlatformIO board profile updated from `esp32dev` to `esp32-s3-devkitc-1`.
  2. Firmware rewritten to use USB-Serial/JTAG low-level FIFO (`usb_serial_jtag_ll`) instead of Arduino `Serial` (which targets UART0/HWCDC, not the JTAG CDC port).
  3. Python driver opens serial without DTR/RTS assertion to prevent the S3 from resetting into download mode.
- Default serial port changed from `/dev/ttyUSB0` to `/dev/ttyACM0` (native USB CDC path for ESP32-S3).
- Board default `ARDUINO_USB_MODE=1` overridden to `0` to prevent Arduino core from disabling USB-Serial/JTAG controller.

### Added
- `jtag_serial.h` — Stream-compatible wrapper for ESP32-S3 USB-Serial/JTAG hardware FIFO.
- Heartbeat blink on ESP32 onboard RGB LED (GPIO48) — dim green pulse every 2s confirms firmware is running.

### Changed
- `commands.cpp` refactored to accept a `Print&` output parameter instead of hardcoded `Serial`.
- Firmware version bumped to `0.2.1`.

### Validated (Phase 1 Hardware)
- DS18B20 reading stable at ~22°C (reservoir temp).
- GPIO17 relay switching reliably — audible click, pump runs on command.
- Pump wet test passed (3× consecutive 5-second runs, no issues).
- `growlab start` soak initiated — DS18B20 polling every 120s, irrigation scheduler active, data logging to SQLite on Pi.

## 2026-03-12

### Added
- Configurable irrigation pump backend via `irrigation.pump_controller` (`gpio` or `esp32`) with validation and tests.
- Explicit pump-controller guidance in irrigation and V0 runbook docs.
- Phase 1 blocker notes documenting current ESP32-S3-N16R8 serial runtime issue.
- Additional config tests for pump backend parsing and validation.
- End-of-day handoff logging sections in V0/Phase 1 docs, including a saved March 12, 2026 status snapshot and next-session priority.

### Changed
- `growlab pump` controller selection now follows config instead of implicit fallback behavior.
- Phase 1 setup instructions now use Pi extras install (`pip install -e ".[pi]"`) to ensure `RPi.GPIO` availability.
- ESP32 serial connection adds a short post-open delay for USB CDC stability.
- ESP32 firmware startup no longer blocks indefinitely waiting for `Serial` readiness.

### Notes
- ESP32 flashing is confirmed, but runtime serial command responses remain unresolved on tested ESP32-S3-N16R8 USB paths.
- Phase 1 execution should proceed on DS18B20 + GPIO relay pump path while ESP32 serial profile is finalized in Phase 2.
