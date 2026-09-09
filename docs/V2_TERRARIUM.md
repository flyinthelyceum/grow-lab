# GROWLAB V2 — Terrarium edition

**A new object, not a conversion.** V2 is built from new components and is its
own terrarium. **Object A stays Object A** — V1 is not cannibalised, converted or
superseded, and `V1_PHYSICAL_BUILD.md` remains the record of a finished design.
What V2 inherits is the *software*, the *instrument language* and the *method*.
No V1 hardware moves.

**Status: brief. No geometry exists yet.** `params.py` and `cad/` are untouched.
Numbers get provenance before they get geometry.

---

## Where this stands — paused 2026-09-09

**Every design decision is closed. Nothing has been built and no geometry
exists.** Work stopped here deliberately to return to V1; this section is the
resumption point.

| | |
|---|---|
| Decided | Species, form, dimensions, glazing, climate strategy, lighting, staging, substrate approach |
| Written | This document, and only this document |
| Not started | `params_v2.py`, any CAD, any V2 code, any purchase |
| V1 impact | **None.** No V1 file, part or decision was changed for V2 |

**To resume:** the next step is `params_v2.py` and a CAD package, built the way
V1's was — every number traceable to the height stack in *Dimensions* below, and
`CHOICE` marked where a number is invented rather than derived. The viewer takes
a second station without modification; `cad/VIEWER.md` explains how variants work.

**Three things must be verified before any hardware is bought**, and they are
listed in full under *Open decisions*: the induction temperature requirement read
in the primary papers, the fruiting band confirmed with the actual spawn
supplier, and the air curtain tuned on the built chamber. The first of those is
load-bearing — it is the claim that puts a cooling system in the piece at all.

---

## The organism

**_Agaricus subrufescens_** — almond mushroom, sun mushroom, *cogumelo do sol*;
also sold as *A. blazei* / *A. brasiliensis*. Legal, edible, cultivated
commercially. Same genus as the button mushroom, and that family resemblance
drives everything below.

| | | Consequence |
|---|---|---|
| Substrate | **Composted** straw/manure; a secondary decomposer, not a wood-rotter | Standard *A. bisporus* compost works — see below |
| Casing layer | **Required** — peat + limestone + fine sand | The casing surface is the visible ground plane and the thing being lit. **Deeper casing measurably improves yield and time to fruiting** |
| Spawn run | 68–82 °F | The house at 79 °F is already in band — no intervention |
| **Induction** | **Temperature must be LOWERED below 77 °F**; some sources say 68 °F | **The house is too warm to pin. This needs cooling** |
| Fruiting | 73–79 °F | |
| RH, growing air | **75–85%** | Corrected from 80–90 |
| RH, compost | 60–70% | Wetness of the substrate, not the air |
| Light | **Not required — fruits in darkness** | Lighting is a display decision, free of horticulture |
| FAE | Needed to drop CO₂ for pinning | |
| Habit | 4–8 in tall, tan scaly cap, distinct ring | Upright, not a shelf |
| Aroma | Almond / marzipan | |

**Provenance note, and it matters.** The first two versions of this brief got the
thermal design wrong in opposite directions, both times because the numbers came
from recollection. They now come from cultivation literature and supplier
documentation, cited at the foot. **The induction requirement is the single
load-bearing claim in this document** — it decides whether a cooling subsystem
exists — and it should be read in the primary papers, not taken from here, before
any hardware is bought.

---

## Climate: the house is not a constant, and that decides everything

**Phoenix, in a hundred-year-old house with drafts both directions.** 79 °F is
the summer figure; the winter minimum is about **60 °F**. The design target is
therefore not a setpoint offset from ambient — it is a chamber that holds its own
setpoint across a **60–79 °F** room, with an AC-failure case at 95 °F that should
not destroy a crop.

That range is narrower and warmer than the 50–90 °F this section first assumed,
and it makes the whole envelope comfortable.

This section has been wrong twice. The first draft specified heating as "the
largest new subsystem"; the second removed it entirely on the grounds that the
room was already at the setpoint. Both errors have the same cause: computing a
single operating point instead of the range. **A drafty house is a range**, and
every number below is computed across the real one.

### Why cooling is mandatory, not optional

The induction step is the reason. Fruiting is not triggered by holding a
temperature; it is triggered by **lowering** it, together with RH and CO₂:

| Phase | Chamber | Against a 79 °F house |
|---|---|---|
| Spawn run | 68–82 °F | Passive. Floats about 1.5 °F over ambient |
| **Induction** | **below 77 °F, some sources 68 °F** | **Unreachable without cooling** |
| Fruiting | 73–79 °F | Reachable in winter, not in summer |

A chamber that floats with a 79 °F room sits at 80.5 °F and **never pins**. This
is the finding that brings the thermal subsystem back, and it is why it must
cool rather than heat.

### One device, both directions

A **thermoelectric (Peltier) assembly**: reversing polarity turns cooling into
heating, so a single unit covers the whole envelope, with no compressor, no
refrigerant and nothing moving but two fans.

**Glaze only what you look through** — a front and a top, not six glass faces.
The other four are cork-faced insulated panel, which is both the thermal envelope
and the set; see *Staging* below. With a curtained single pane and 0.5 in cork
over 1 in foam, the 20 × 18 × 22 in internal volume comes to **UA 3.20 W/K**:

| Case | Room → chamber | Load |
|---|---|---|
| Winter minimum, spawn run | 60 °F → 80 °F | 31.6 W heating |
| Summer, induction | 79 °F → 72 °F | 16.5 W cooling |
| **AC failure, induction** | 95 °F → 72 °F | **44.9 W cooling — the sizing case** |

A 60 W module carries all three. The insulated faces are what make that true;
all-glass would be 4.73 W/K and a refrigeration problem.

**Where it crosses the envelope:** low in the **back** panel, cold side in, hot
side finned into the base with its own fan and a path out the back. It crosses an
opaque face, never a glazed one.

### Glazing: single, and here is how it stays clear

**Reversed 2026-09-09, and this is the third position this spec has taken.** The
earlier reasoning was sound but lazy: single glazing fogs at the 60 °F winter
minimum, so I reached for a second pane instead of asking *why the inner surface
was cold*. Two answers, either of which nearly solves it and which together
settle it.

**1. The spawn run does not need humid air.** Colonisation happens *inside* the
compost, which sits at 60–70% moisture; the air only has to be humid at fruiting.
Run the spawn-run air at 65% and the dew point falls far enough that a single
pane is clear even on the coldest night.

**2. A gentle air curtain down the inside of the glass.** Still air against glass
forms an insulating boundary layer, and it is that layer — not the glass — that
lets the surface fall below the dew point. Moving air across it drags the surface
back up toward the chamber's own temperature. This is exactly what a supermarket
display fridge does to keep its doors clear.

| Phase | Chamber | RH | Room | Still air | With a curtain |
|---|---|---|---|---|---|
| Spawn run | 80 °F | 80% | 60 °F | 71.2 °F **−2.1 fogs** | 75.2 °F +1.9 |
| Spawn run, drier air | 80 °F | 65% | 60 °F | 71.2 °F +4.0 | 75.2 °F +8.0 |
| Fruiting | 72 °F | 85% | 60 °F | 66.7 °F **−0.5 fogs** | 69.1 °F +1.9 |
| Fruiting | 72 °F | 85% | 70 °F | 71.1 °F +3.9 | 71.5 °F +4.3 |
| Fruiting | 72 °F | 85% | 79 °F | 75.1 °F +7.8 | 73.7 °F +6.4 |

**Every phase is clear in every condition.** Single 1/4 in cast acrylic.

**The curtain must be aimed at the glass, not at the bed.** A slot along the top
of the pane blowing down its inner face and returning low — a drift, not a
breeze. Airflow across a casing layer dries it out, and a dry casing is the
classic reason a cased bed refuses to pin. This is the one detail in the whole
enclosure where getting the direction wrong costs a crop.

It also costs a little: thinning the inside film raises U_glass from 3.53 to
4.80, and the loads above already include it.

### Nothing hot or wet inside the glass — this still holds

At small deltas the glazing sheds very little, so internal equipment dominates.
Fogger, light and fan inside a sealed chamber settle it above 92 °F. The fogger
therefore lives in the base and is piped in; the light lives outside the glazing;
the Pi, PSU, driver and pump were always going to be in the base. Internal load
stays near 4 W, and the Peltier is then sizing against the enclosure rather than
against its own equipment.

## Form: a vitrine, and no mast

The mast goes. Its whole justification was holding a photosynthetic working
distance over a plant that grows to 18 in; this organism is 4–8 in and fruits in
the dark. Nothing about V2 needs a vertical armature, and V2 is a new object that
owes V1 no silhouette.

What replaces it is the form the contents actually ask for: **a glass case on a
base.**

- **The base** carries everything hot, wet, loud or serviceable — reservoir,
  fogger, pump, FAE fan and filter, Peltier hot side, Pi, PSU, driver — and
  presents the instrument panel on its front face. This is V1's wet-bay/dry-bay
  architecture and its console language, both of which earned their place.
- **The case** is the growing volume and the staged scene it sits in. **Single-
  glazed on the front and top; cork-faced insulated panel on the back, sides and
  floor.** Doored, drained, fly-screened. The asymmetry is not a compromise — it
  halves the climate load, it gives the piece a front, and the opaque faces are
  what the scene is built against.
- **The light** sits in the case's top frame, outside the glass.
- **The Peltier assembly** breaches one insulated face, cold side in, hot side
  finned into the base with its own fan. It is the one component that must cross
  the envelope, and it should cross an opaque face rather than a glazed one.

The height stack is derived below.

## Dimensions — derived 2026-09-08

Heights were delegated, so they are derived rather than chosen. Two things drive
everything: the **substrate column**, which the literature fixes, and the **angle
you look down at the casing surface**, which is the composition decision.

### What sets the casing surface

The casing surface is the ground plane of the piece — the thing the mushrooms
stand on and the thing the cove light falls on. Too low and you look down *into*
a box; too high and the surface disappears and you see only stems. At a standing
eye of 62 in and a comfortable approach of 33 in:

| Casing surface | Look-down angle | |
|---|---|---|
| 42 in | 31.2° | looking down into it |
| 46 in | 25.9° | works |
| **48 in** | **23.0°** | **chosen — surface reads as ground, caps read in profile** |
| 52 in | 16.9° | |
| 56 in | 10.3° | surface disappears |

### The stack

| Element | Height from floor |
|---|---|
| Floor to base underside — shadow gap | 5.0 in |
| **Instrument panel centre** | **28.0 in** — V1's own figure, read standing |
| Base top; the case sits here | 37.5 in |
| Case internal floor | 39.0 in |
| Compost, lower layer | → 42.5 in |
| Compost, upper layer (spawn between) | → 46.0 in |
| **Casing surface — the ground plane** | **48.0 in** |
| A mature 8 in cap | 56.0 in |
| Case internal ceiling / top pane | 61.0 in |
| **Top of the piece** | **62.5 in** |

Base 32.5 in tall, case 22.0 in internal, **5.0 in clear above a mature cap.**

For comparison: V1 is 81.4 in with its mast and was 59.9 in before it. V2 lands
between them — a vitrine on a plinth, with the glass occupying the top third.

### Footprint and what it consumes

Case internal **20 W × 18 D × 22 H in**. The bed is **18 × 12 in**, sitting
forward with a 1 in air margin at the front and sides so the casing never touches
the glass; the 5 in behind it is staged background, not substrate.

| | |
|---|---|
| Compost | 0.88 cu ft — 25 L, about 31 lb damp |
| Casing mix | 0.25 cu ft — 7 L |
| Spawn | The bed is **9% of what one 5 lb bag covers**. One bag does ~11 beds, and spawn keeps six months at room temperature |

The substrate column is 9.0 in: 3.5 in of compost, spawn, 3.5 in more, then 2.0 in
of casing. Casing is at the top of the documented range deliberately — depth
measurably improves both yield and time to fruiting.

## Staging — a planted scene, not a compost tray

The brief was never "grow mushrooms indoors"; it was that spartan mushroom
growing is exactly what this must not look like. So the interior is staged as a
terrarium, and one decision makes that cheap.

### The envelope and the set are the same part

**Cork bark faces the insulated panels.** Cork is the standard vivarium
background material, it is rot-resistant in permanent humidity, it looks like
forest floor, and it is a genuine insulator — so the thermal requirement and the
scenic one are answered by one material.

| Build | U |
|---|---|
| 1 in cork alone | 1.13 W/m²K |
| 0.5 in cork + 0.5 in foam | 1.01 |
| **0.5 in cork + 1.0 in foam** | **0.71 — chosen** |

Cork veneer over a foam core insulates *better* than the plain foam originally
specified, and the face you see is bark.

### Stage the periphery, keep the bed clear

The rule that makes this work horticulturally:

- **Cork bark walls** — back and sides, textured and vertical, rising behind the
  bed.
- **Moss on the margins and up the walls.** Sheet and cushion moss want precisely
  what this chamber provides — 85% RH, low indirect light, no soil depth. It is
  the one companion organism whose requirements are the mushroom's requirements.
- **A piece or two of hardscape** — wood or stone — to break the plane and give
  the eye a middle distance.
- **The casing bed stays open in the centre.** A clearing. That is where the
  mushrooms erupt, and it is where you water, ruffle and harvest.

**Never stage on the casing itself.** Moss or decor over the fruiting surface
blocks pinning and gas exchange, and the casing has to be reachable — it gets
watered, ruffled at induction, and picked. Staging goes *around* the bed, not on
it.

### The depth is for the scene

Internal depth goes **14 → 18 in**. The bed stays 18 × 12, so the extra four
inches are not substrate — they are background. Depth is the difference between a
landscape and a diorama pressed against the glass: foreground bed, middle
hardscape, mossed cork bank behind. It costs 0.36 W/K and about 4 W at the
extremes, which the module has.

### What staging costs, honestly

**Contamination risk goes up, and this is not a small caveat.** A cased bed is a
semi-sterile environment whose whole defence is that the casing colonises before
anything else arrives. Moss, wood and stone carry competitors — *Trichoderma*
above all. Bake or soak the hardscape, use cleaned moss, and accept that a staged
piece will occasionally lose a flush to something green. That is the price of it
not looking like a plastic tub.

**Companion plants are a later question.** Ferns, fittonia and selaginella would
love the humidity, but they need more light than a display level provides, want
their own drained soil pocket, and are a third contamination vector. **Moss only
for V2**, and revisit once the environment has proven itself over a couple of
flushes.

## Lighting — three options, all outside the glass

The thermal finding eliminates in-chamber lighting. What remains:

**A. Cove down-light in the top frame.** A strip concealed in the case's top
rail, outside the glazing, throwing down through a clear top. Source invisible,
modelling on the caps, heat rejected to the room. Closest to how a good vitrine
is lit. Risk: the top pane collects condensate on its inside face, which diffuses
the light — which may be a feature.

**B. Backlit diffuser wall.** One face of the case is an illuminated white panel.
The mushrooms read in silhouette with soft fill; the chamber becomes a lightbox.
Graphic and unusual. Risk: flattens the caps' texture, and the piece reads more
as a sign than an object.

**C. External gallery spot.** A separate arm outside the case entirely, lighting
it as a museum object. Keeps the chamber absolutely pure and is the only option
that preserves anything mast-like. Risk: reintroduces the vertical element V2
just removed, and puts a fixture in the room.

**Decided 2026-09-08: A — cove down-light in the top frame.** The source
disappears and the subject is what you see. The top pane will collect condensate
on its inside face in cold weather and diffuse the light; treat that as weather,
not a fault.

---

## Substrate — what is actually purchasable

Researched 2026-09-08. Two corrections to the first draft.

**There is no ready-to-fruit product for this species.** Unlike oysters or lion's
mane, nobody in the US sells a colonised, ready-to-case *A. subrufescens* block.
The supply chain sells **sawdust spawn**, and you supply the compost. So the
earlier instruction — "the supplier's block size sets the chamber volume" — has no
referent. The chamber can be sized freely, which is better news than it sounds.

**Pasteurisation is not required**, contrary to the first draft. North Spore say
so explicitly, and it is one of this species' advantages over the button mushroom
it resembles.

| | |
|---|---|
| Spawn | Sawdust spawn in 5 lb bags. **One bag covers 4 × 4 ft** — vastly more than a vitrine needs |
| Substrate | Fully finished compost. Standard *A. bisporus* compost (wheat straw + horse manure) is documented to work |
| Bed depth | 3–4 in compost, spawn, then 3–4 in more on top |
| Casing | Lime-treated peat, or peat + limestone + fine sand. **Deeper casing measurably improves both yield and time to fruiting** |
| Timing | Case ~13 days after spawning; fruiting ~40 days after inoculation |

So the substrate column is roughly **8–10 in deep** — 6–8 of compost plus 1.5–2 of
casing — and that, not a supplier's bag, sets the case's internal height below the
growing surface.

**One honest caveat.** Every US supplier positions this as an *outdoor bed* crop.
Mushroom Mountain say trays, tubs and buckets work indoors, but their indoor guide
is "coming soon". Small-scale indoor cultivation is well documented in the
cultivation literature and is the standard commercial method in Brazil and Asia —
it is simply not the beaten path in the US hobby supply chain. Expect to work from
papers rather than from a supplier's instruction card.

## Software

Mostly re-pointing existing machinery. V2 runs the same stack.

- **Invert the humidity rule.** `pi/services/alerts.py` has humidity warning-high
  70% and critical-high 80%, written when damp meant botrytis on a ranunculus.
  The fruiting band is 80–90%: today's critical alarm is tomorrow's setpoint.
- **Re-centre the temperature rule** on 73–81 °F. The current 65–80 warning band
  would sit permanently in warning.
- **Retire pH and EC** with their probes. Two probes, two services, two dial
  faces and a chunk of config lose their subject. Run it as a subtract pass.
- **The two Weston movements change subject** — air temperature and humidity are
  the numbers that matter now, and they are the two that move. Nothing has been
  printed yet, which is lucky.
- **A thermal control service**, and it is the largest new piece of software.
  Bidirectional: drive the Peltier's polarity and duty from a setpoint that
  changes by phase — 80 °F through the spawn run, then a commanded *drop* to
  induce. Induction is a scheduled state change, not a steady-state hold, which
  is unlike anything V1 does.
- **Phase state.** V1 had one regime. V2 has spawn run → casing → induction →
  fruiting → rest, each with its own temperature, RH and FAE setpoints. That is a
  state machine, and it is the piece's actual subject.
- **FAE control** joins the fan service, sized for CO₂ and available as a
  temporary heat lever.

---

## Open decisions

Design decisions are closed. What remains is verification, and it is all
empirical:

1. **Read the induction requirement in the primary papers** before buying a
   Peltier. It is the claim that brings the entire climate subsystem into
   existence, and it is here on the strength of search summaries.
2. **Confirm the fruiting band with the spawn supplier** for the strain actually
   bought. 73–79 °F is the literature; strains vary.
3. **Tune the air curtain on the built chamber.** It has to be strong enough to
   keep the pane clear at the 60 °F winter minimum and gentle enough not to dry
   the casing. Those are the two failure modes and they pull in opposite
   directions; an IR thermometer on the glass and a finger on the casing settle
   it, not a calculation.

Settled: new build, own object, Object A untouched · mast deleted · vitrine on a
base · casing surface at 48 in, top of piece 62.5 in · case internal
20 × 18 × 22 in · **single** glazing front and top with an internal air curtain ·
cork-faced foam on the other four faces, doubling as the set · staged periphery
with a clear bed, moss only · cove down-light in the top frame · bidirectional
Peltier through the back panel, low · buy spawn, supply compost.

---

## Sources

Cultivation parameters come from the following and should be read directly before
hardware is committed — the induction requirement in particular, since it is what
brings the cooling subsystem into existence.

- [Optimization of cultivation techniques improves the agronomic behavior of *Agaricus subrufescens*](https://www.nature.com/articles/s41598-020-65081-2) — Scientific Reports
- [*Agaricus subrufescens*: A review](https://www.sciencedirect.com/science/article/pii/S1319562X12000046) — ScienceDirect
- [Optimization of the cultivation conditions … European wild strains and Brazilian cultivars](https://pubmed.ncbi.nlm.nih.gov/23633302/) — PubMed
- [North Spore — Almond Agaricus sawdust spawn](https://northspore.com/products/almond-agaricus-sawdust-spawn) — bed depth, casing, no pasteurisation, 4 × 4 ft per bag
- [Field & Forest — Almond Agaricus](https://fieldforest.net/almond-agaricus-agaricus-subrufescens-sawdust-spawn/) — mycelial range, greenhouse suitability, 5 lb bags
- [Mushroom Mountain — Almond Portabella](https://shop.mushroommountain.com/products/almond-portabella-sawdust-spawn-agaricus-blazei-a-braziliensis-5lb) — indoor trays/tubs, 70–90 °F fruiting
