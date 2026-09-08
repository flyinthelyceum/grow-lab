# GROWLAB V2 — Terrarium edition

**Status: brief. No geometry has changed.** This document establishes what the
organism demands and what that costs the piece. `params.py` and `cad/` follow
once the open decisions at the bottom are settled — the project's rule is that
numbers have provenance before they have geometry, and V2 does not get to skip
it just because it is new.

**V1 is not deleted.** `V1_PHYSICAL_BUILD.md` and its procedure stay as written.
This is a second configuration of the same station, not a replacement, and the
V1 record is worth keeping intact — it is the only account of why the cabinet is
the shape it is.

---

## The organism

**_Agaricus subrufescens_** — almond mushroom, sun mushroom, *cogumelo do sol*;
also sold as *A. blazei* and *A. brasiliensis*. Legal, edible, cultivated
commercially. Same genus as the supermarket button mushroom, and that family
resemblance drives almost everything below.

| | | Consequence for the piece |
|---|---|---|
| Substrate | **Composted** straw/manure. A secondary decomposer, not a wood-rotter | No sawdust block. Compost, and the smell that implies |
| Casing layer | **Required** — peat + lime, 1–2 in, kept moist | Pinning happens at the casing surface, which becomes the visible ground plane |
| Spawn run | ~77–86 °F | Heating, not cooling |
| **Fruiting** | **~73–81 °F**, optimum around 78–80 | Warmer than nearly every other cultivated mushroom |
| Fruiting RH | 80–90% | V1's *critical-high* alarm is this species' setpoint |
| Light | **Not required — fruits in darkness** | The grow light stops being a grow light |
| FAE | Needed to drop CO₂ for pinning | The fan returns |
| Habit | 4–8 in tall, tan scaly cap, distinct ring | Tall and upright, not a shelf |
| Aroma | Almond / marzipan | Genuinely pleasant, unlike the substrate |

**Verify these against your spawn supplier's strain sheet before anything is
cut.** Ranges vary by strain and source; the ones that matter structurally are
the fruiting temperature band and the RH band, and both are load-bearing below.

---

## The finding: the mast's reason to exist evaporates

This is the biggest single consequence and it is worth stating before the
enclosure.

V1's mast is **81.4 in** tall. That number is not a style choice — it is derived.
`FIXTURE_ABOVE_MEDIA_MAX = 33.0` was set to hold 15 in of working clearance over
a mature 18 in ranunculus, and the whole armature follows from it: fixture top of
travel at 75.9, plus the fixture, plus half the collar, plus the head. Change the
33 and the mast shortens with it. That was designed in deliberately.

*A. subrufescens* is **4–8 in tall and fruits in the dark.**

So both halves of the justification are gone at once. There is no photosynthetic
working distance to hold, because there is no photosynthesis. There is no 18 in
plant to clear. The light becomes **purely a display element** — it exists to let
a person see the mushrooms, not to feed them.

Illustratively, if the top of travel came down to 18 in over the media — generous
for lighting and viewing an 8 in mushroom — the mast lands near **66 in** instead
of 81.4, and the piece loses about fifteen inches of height. That is not a
proposal; it is a demonstration that the number is now free. What actually sets it
is a lighting and composition decision, and it should be made as one rather than
inherited.

**The canopy mechanism itself still earns its place.** Adjustability is more
useful here, not less: the casing surface is the thing being lit, flushes change
the subject's height, and the light is now doing photographic work rather than
horticultural work. Keep the collar and the travel; re-derive the numbers.

---

## The enclosure, and the problem that decides its spec

The growing volume has to become an enclosed, humidified, glazed chamber. This
is the new object, and it is the terrarium.

**Condensation is the binding constraint, and it is tighter than it looks.**
At the fruiting setpoint — 80 °F, 85% RH — the dew point is **75.1 °F**. Any
interior surface below that fogs, and a fogged chamber is a chamber you cannot
see into, which defeats the entire brief.

Computed for a 70 °F room, natural convection both sides:

| Glazing | Inner surface | Margin over dew point | |
|---|---|---|---|
| Single 1/4 in cast acrylic | 75.6 °F | **+0.5 °F** | fogs in practice |
| Double 1/4 in, 1/2 in air gap | 77.4 °F | +2.3 °F | workable |

Half a degree is not a margin. A cooler room, a draft, a cold spot at a corner,
or an RH excursion to 90% puts single glazing under the dew point and keeps it
there. **V2 is double-glazed**, and that is a specification, not a preference.

Even at +2.3 °F the margin is thin enough to want checking with an IR
thermometer on the real chamber before the piece is called finished. Corners and
edges run colder than the middle of a pane.

Other enclosure requirements:

- **Fine mesh on the FAE intake.** Casing layers attract sciarid and phorid
  flies. This is the most common way an indoor casing job goes wrong and it is
  cheap to prevent at the design stage.
- **Access for casing, watering and harvest**, without dropping the chamber's
  RH every time. Argues for a door rather than a lift-off lid.
- **A drain.** Casing gets watered; water goes somewhere. The tray already
  exists and already drains.

---

## What survives, what dies, what is new

**Survives unchanged:** cabinet, base frame, tray, reservoir, mast and canopy
collar (re-dimensioned, not redesigned), instrument case and its whole console,
the Pi, the Weston meters, the Inky, the dashboard, the deploy pipeline, the
entire software architecture.

**Survives with a new job:**

| Part | Was | Becomes |
|---|---|---|
| Lightbox | Photosynthesis, 12–33 in over media | Display lighting, dimmed hard. The PWM dimming is already there |
| Pump + reservoir | Drip irrigation to the media | Casing irrigation and/or humidification supply |
| BME280 | One channel among many | The primary instrument. Everything is air now |
| CMU | A vessel that had to be leached because lime poisons plants | A vessel whose lime is an asset — casing layers are *deliberately* limed |

**Dies:**

- **pH and EC probes.** Substrate chemistry matters at compost preparation, not
  as live telemetry. Two probes, two services, two dial faces and a chunk of
  config all lose their subject. This is a subtract pass waiting to happen, and
  it should be run as one rather than left to rot.
- **Drip emitters at the media surface**, in their current form and position.

**New:**

- **The glazed chamber** — double-glazed, sealed, doored, drained, fly-screened.
- **Heat.** V1 has *no* thermal control of any kind. An 80 °F setpoint in a
  ~70 °F house needs a heat source, a temperature loop and a safety cutout. This
  is the largest new subsystem and it did not exist in any form before.
- **Humidification** — ultrasonic fogger or misting, fed from the reservoir.
- **FAE** — a small fan, ducted, filtered, on a schedule or a CO₂ trigger.

### The fan comes back, and this time it can be hidden

The fan was cut on 2026-09-05 because a 120 mm black axial part dominated the
most-looked-at volume in the piece. That objection was about a fan hanging in
open air over the block. Inside a sealed chamber it is ducted through a wall,
sized for air changes rather than canopy movement, and never seen. The visual
argument that killed it does not apply to the thing V2 needs.

Its software survives, disabled — see the 2026-09-05 changelog. That was the
right call for a reason nobody anticipated.

---

## Software

Small compared to the physical work, and mostly re-pointing existing machinery.

- **Invert the humidity rule.** `pi/services/alerts.py` currently has humidity
  warning-high 70% and **critical-high 80%** — thresholds written when damp meant
  botrytis and powdery mildew on a ranunculus. The fruiting band is 80–90%, so
  today's critical alarm is tomorrow's setpoint. Config-shaped, not architectural.
- **Widen and re-centre the temperature rule.** Currently warns outside 65–80 °F
  and criticals outside 60–85. The fruiting band sits at the top of that, so the
  piece would sit permanently in warning.
- **Retire the pH and EC rules** with their probes.
- **Add a thermal control service**, alongside the existing fan service pattern.
- **The dial faces change subject.** The two Weston movements are currently pH
  and moisture. Air temperature and humidity are the two numbers that matter now,
  and they are the two that move. `INSTRUMENT_HEAD_PLANS.md` § Making the plate
  has not been executed yet, which is lucky — nothing has been printed.

---

## Open decisions

1. **Does V2 replace V1 on the hardware, or is the station reconfigurable?**
   Everything above assumes one physical station that becomes the terrarium.
   A reconfigurable piece — swap the chamber, swap the block — is a much harder
   brief and would change the cabinet.
2. **Where does the light live** now that it is not a grow light? On the mast as
   now, on top of the chamber, or inside it? This decides the mast height, and
   the mast height is the piece's silhouette.
3. **How is the compost handled?** Phase I composting is not a living-room
   activity. Buying finished, pasteurised substrate is the obvious answer and
   should be confirmed before the chamber is sized around a substrate volume.
4. **Does the casing surface sit in the CMU cores, or in a tray inside the
   chamber?** The cores are the stronger image and keep the piece's identity.
   A tray is easier to case, water, harvest and replace.
5. **How much does condensation actually get managed versus accepted?** +2.3 °F
   is workable, not comfortable. Warmed glazing, a larger air gap, or a lower RH
   setpoint at the cost of yield are all levers.

Nothing below the first two can be usefully answered until they are.
