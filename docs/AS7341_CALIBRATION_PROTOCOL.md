# AS7341 Calibration Protocol

## Why We Are Calibrating

GrowLab uses one upward-facing AS7341 per node as an installed multispectral light sensor. The AS7341 is useful, but it is not a universal scientific quantum sensor out of the box. For this project, calibration exists to turn it into a **fixture-specific PPFD estimator** that is:

- consistent
- repeatable
- easy to recommission
- transparent to inspect later

The goal is not laboratory-grade perfection. The goal is stable, teachable, actionable light data for a school demo art installation.

## What "Good Enough" Means

For GrowLab V0, "good enough" means:

- the estimated PPFD tracks dimmer changes smoothly
- repeated measurements at the same setup land close together
- a given node behaves consistently over time
- commissioning can be repeated by a careful builder at a bench

Guidance thresholds for this project:

- RMSE under `20 umol/m2/s` is very good
- median absolute error under `15 umol/m2/s` is very good
- no wild low-light instability
- no obvious discontinuities across dimmer levels

These are commissioning targets, not scientific certification limits.

## Project Philosophy

This protocol follows the same posture as the rest of GrowLab:

- reliable core function over unnecessary complexity
- simple inspectable models over clever opaque ones
- physical consistency matters as much as software calibration
- future refinement is welcome, but V0 should stay sane

## Physical Assumptions

The calibration is only valid under these assumptions:

- the AS7341 is mounted **upward-facing**
- mounting geometry is **fixed per node**
- the housing, diffuser, and shroud are part of the calibration condition
- runtime gain/integration settings stay fixed after commissioning
- the fixture family and installed geometry do not change without recalibration

Changing any of the following may invalidate the profile:

- fixture model
- diffuser material
- shroud or baffle geometry
- mount height
- sensor position
- sensor orientation
- runtime sensor settings

## Physical Mounting Requirements

Before calibration:

- mount the AS7341 in its final installed position
- keep the sensor upward-facing
- do not calibrate with a temporary breadboard orientation if runtime will use a housing
- keep the final diffuser installed during both calibration and runtime
- keep the shroud or light baffle installed during both calibration and runtime
- keep cable strain from twisting the sensor board

Recommended mounting discipline:

- fixed standoff height
- repeatable canopy reference plane
- no loose rotating sensor board
- no exposed reflective surfaces added later near the sensor

## Required Test Setup

Required:

- GrowLab node with the installed AS7341 enabled
- rented handheld PAR meter
- final grow fixture
- final diffuser and shroud
- fixed ruler or tape for canopy distance
- commissioning spreadsheet or terminal at the bench

Recommended:

- dark cloth or shroud to reduce stray room light
- stable room conditions
- 2-3 minutes of warmup for the fixture before first capture

## Default Commissioning Matrix

Use a practical bench matrix, not a lab marathon.

Recommended default:

- dimmer levels: `20, 35, 50, 65, 80, 100`
- `3` fixture-to-canopy distances
- center position
- optional one or two lateral offsets

Target capture size:

- `18-30` total points

This is enough for a stable first-pass fixture-specific linear model without turning commissioning into a science fair.

## CSV Capture Schema

Session CSV columns:

- `timestamp`
- `node_id`
- `fixture_id`
- `fixture_model`
- `calibration_profile_id`
- `operator`
- `sensor_board_id`
- `gain`
- `integration_time`
- `astep`
- `led_pwm_percent`
- `fixture_distance_cm`
- `lateral_offset_cm`
- `reference_ppfd`
- `split`
- `notes`
- `as7341_415nm`
- `as7341_445nm`
- `as7341_480nm`
- `as7341_515nm`
- `as7341_555nm`
- `as7341_590nm`
- `as7341_630nm`
- `as7341_680nm`
- `as7341_clear`
- `as7341_nir`

Notes:

- `split` should usually be `train`
- mark a few rows as `validate` if you want explicit held-out validation
- if no `validate` rows are marked, the tooling performs a deterministic holdout split

## Calibration Workflow

1. Mount the AS7341 in its final physical position.
2. Install the final diffuser and shroud.
3. Confirm the fixture and sensor geometry match intended runtime.
4. Fix AS7341 gain/integration settings. Do not tune them mid-session.
5. Place the PAR meter at the canopy reference plane.
6. Warm the light for a few minutes.
7. Create a new session CSV:

```bash
growlab calibration as7341 init-session --output data/examples/my_as7341_session.csv
```

8. Step through dimmer level and distance combinations.
9. At each point, let the light settle briefly, read the PAR meter, then capture:

```bash
growlab calibration as7341 capture \
  --session data/examples/my_as7341_session.csv \
  --operator "Jared" \
  --pwm-percent 50 \
  --distance-cm 35 \
  --reference-ppfd 242 \
  --samples 5 \
  --split train
```

10. Reserve a few captures as `--split validate` if you want explicit held-out checks.
11. Fit a profile:

```bash
growlab calibration as7341 fit \
  --session data/examples/my_as7341_session.csv \
  --profile-out config/calibration/node-a.json
```

12. Validate it:

```bash
growlab calibration as7341 validate \
  --session data/examples/my_as7341_session.csv \
  --profile config/calibration/node-a.json \
  --report-out data/examples/node-a-validation.md
```

13. If the profile looks sane, set it active in `config.toml`:

```toml
[calibration]
enabled = true
profile_dir = "./config/calibration"
active_profile = "node-a.json"
```

## Validation Workflow

Validation should answer:

- does the profile generalize across the commissioning points?
- does the prediction behave smoothly?
- is low-light behavior stable enough for the demo?

Validation steps:

1. Load the session and profile.
2. Use explicit `validate` rows if present, otherwise a deterministic holdout split.
3. Review:
   - RMSE
   - MAE
   - median absolute error
   - R2
   - residual range
4. Reject profiles with obvious instability even if one metric looks good.

Practical pass guidance:

- RMSE under `20` is very good
- median absolute error under `15` is very good
- residuals should not swing wildly at low light
- output should increase smoothly as dimmer level increases

## Recommended Sample Counts

Per capture:

- default `5` AS7341 reads averaged together

Per commissioning session:

- minimum `18` rows
- preferred `24-30` rows

Held-out validation:

- at least `4-6` rows if you are explicitly tagging validation rows

## Operator Notes and Pitfalls

- Do not calibrate bare-sensor and then run enclosed-sensor.
- Do not change gain or integration after commissioning.
- Do not move the sensor board after calibration.
- Avoid room light contamination during captures.
- Keep the PAR meter plane consistent.
- Record notes whenever something about the setup is unusual.
- If one point looks obviously wrong, retake it instead of trusting luck.

## When Recalibration Is Required

Recalibrate if any of these change:

- fixture model
- fixture height range or installed geometry
- diffuser
- shroud
- sensor placement
- sensor orientation
- runtime AS7341 gain/integration settings
- node hardware rebuild affecting optics

Also consider recalibration after:

- visible fixture aging or replacement
- long downtime with unknown mechanical changes
- persistent residual drift during spot-checks

## Runtime Behavior

At runtime GrowLab:

- continues logging raw AS7341 channels
- computes `estimated_ppfd` when an active profile is available
- attaches calibration metadata to the emitted AS7341 readings

This keeps the raw data available for future model refinement while giving the dashboard/data stack an immediately useful PPFD estimate.

## V0 vs Future Versions

V0:

- fixture-specific linear model
- fixed sensor settings
- fixed geometry
- manual commissioning with rented PAR meter
- emphasis on consistency and teachability

Future versions may add:

- ridge-based default fitting for noisy installs
- drift checks
- recalibration reminders
- fixture-family base models with per-install correction
- more advanced offline model refinement

The rule should stay the same: only add sophistication when it clearly improves reliability.
