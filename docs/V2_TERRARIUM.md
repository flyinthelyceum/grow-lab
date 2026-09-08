# GROWLAB V2 — Terrarium edition

**A new object, not a conversion.** V2 is built from new components and is its
own terrarium. **Object A stays Object A** — V1 is not cannibalised, converted or
superseded, and `V1_PHYSICAL_BUILD.md` remains the record of a finished design.
What V2 inherits is the *software*, the *instrument language* and the *method*.
No V1 hardware moves.

**Status: brief. No geometry exists yet.** `params.py` and `cad/` are untouched.
Numbers get provenance before they get geometry.

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

A **thermoelectric (Peltier) assembly** is the answer: reversing polarity turns
cooling into heating, so a single unit covers the whole envelope, with no
compressor, no refrigerant and nothing moving but two fans.

**Glaze only what you look through.** The chamber needs a front and a top, not
six glass faces. Double-glazing those two and insulating the back, sides and
floor with 1 in of rigid foam gives **UA = 1.70 W/K** for the 20 × 14 × 22 in
internal volume derived below:

| Case | Room → chamber | Load |
|---|---|---|
| Winter minimum, spawn run | 60 °F → 80 °F | **14.9 W heating** |
| Summer, induction | 79 °F → 72 °F | **10.6 W cooling** |
| AC failure, induction | 95 °F → 72 °F | 25.8 W cooling |

A 60 W module carries all three with better than 2× margin. The insulated faces
are what make that true — all-glass would have put the same chamber at 4.73 W/K
and turned this into a refrigeration problem.

**Where it crosses the envelope:** low in the **back** insulated panel, cold side
in so its air falls onto the bed rather than blowing across the caps, hot side
finned into the base with its own fan and a path out the back. It crosses an
opaque face, never a glazed one.

### Glazing: double, and 60 °F is what decides it

Inner-surface temperature against the chamber's dew point, chamber at 80 °F /
80% RH (dew point 73.3 °F):

| Room | Single | | Double | |
|---|---|---|---|---|
| **60 °F — winter minimum** | 71.2 °F | **−2.1 fogs** | 74.8 °F | **+1.5 ok** |
| 62 °F | 72.1 °F | −1.2 fogs | 75.3 °F | +2.0 |
| 65 °F | 73.4 °F | +0.1 | 76.1 °F | +2.8 |
| 79 °F — summer | 79.6 °F | +6.3 | 79.7 °F | +6.5 |

**Single glazing fogs on the coldest nights of a Phoenix winter and double does
not.** +1.5 °F is a real but modest margin, so expect the front to mist briefly
on a cold morning during the spawn run, when the chamber is at its warmest and
wettest. It clears as the room warms. During induction and fruiting the chamber
is *cooler* than the room and the glass is warmer than the air inside it, so
there is no interior condensation at all — the fruiting phase, the one you
actually look at, is the clear one.

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
- **The case** is the growing volume and nothing else: substrate, casing surface,
  the mushrooms, air. **Double-glazed on the front and top; insulated panel on
  the back, sides and floor.** Doored, drained, fly-screened. The asymmetry is
  not a compromise — it halves the climate load and it gives the piece a front.
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

Case internal **20 W × 14 D × 22 H in**. The bed is **18 × 12 in**, leaving a 1 in
air margin all round so the casing never touches the glass.

| | |
|---|---|
| Compost | 0.88 cu ft — 25 L, about 31 lb damp |
| Casing mix | 0.25 cu ft — 7 L |
| Spawn | The bed is **9% of what one 5 lb bag covers**. One bag does ~11 beds, and spawn keeps six months at room temperature |

The substrate column is 9.0 in: 3.5 in of compost, spawn, 3.5 in more, then 2.0 in
of casing. Casing is at the top of the documented range deliberately — depth
measurably improves both yield and time to fruiting.

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
3. **Check the front pane with an IR thermometer** on the built chamber during a
   cold-morning spawn run. +1.5 °F is a real margin but not a generous one, and
   edges run colder than pane centres.

Settled: new build, own object, Object A untouched · mast deleted · vitrine on a
base · casing surface at 48 in, top of piece 62.5 in · case internal
20 × 14 × 22 in · double glazing front and top, 1 in foam elsewhere · cove
down-light in the top frame · bidirectional Peltier through the back panel, low ·
buy spawn, supply compost.

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
