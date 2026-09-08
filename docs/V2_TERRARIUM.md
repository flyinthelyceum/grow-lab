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
| Substrate | **Composted** straw/manure; a secondary decomposer, not a wood-rotter | No sawdust block. Bought-in finished compost — see below |
| Casing layer | **Required** — peat + lime, 1–2 in, kept moist | The casing surface is the visible ground plane and the thing being lit |
| Spawn run | ~77–86 °F | |
| **Fruiting** | **~73–81 °F**, optimum 78–80 | **The house is already at the setpoint** |
| Fruiting RH | 80–90% | |
| Light | **Not required — fruits in darkness** | Lighting is a display decision, free of horticulture |
| FAE | Needed to drop CO₂ for pinning | |
| Habit | 4–8 in tall, tan scaly cap, distinct ring | Upright, not a shelf |
| Aroma | Almond / marzipan | |

Verify the fruiting temperature and RH bands against the spawn supplier's strain
sheet before anything is cut. Both are load-bearing below.

---

## The decisive fact: the house sits at 79 °F

This is the single most consequential number in the project and it makes two
things in the first draft of this brief **wrong**. Both are corrected here.

### Correction 1 — the chamber is single-glazed, not double

The brief specified double glazing on a condensation calculation done for a
70 °F room. At 79 °F the calculation comes out differently:

| Room | Single pane, inner surface | Margin over 75.1 °F dew point | Double pane | Margin |
|---|---|---|---|---|
| 65 °F | 73.4 °F | −1.7 **fogs** | 76.1 °F | +1.0 |
| 70 °F | 75.6 °F | +0.5 | 77.4 °F | +2.3 |
| **79 °F** | **79.6 °F** | **+4.5** | 79.7 °F | +4.7 |

At 79 °F the second pane buys **0.2 °F**. It is pointless, and it costs a second
set of reflections between the viewer and the subject, more weight, more edge to
seal, and a sealed cavity that will eventually fog on the inside where nobody can
clean it. **Single 1/4 in cast acrylic**, and the margin is comfortable.

The condensation problem was real; it was a problem *for a 70 °F house*.

### Correction 2 — the thermal problem is rejection, not addition

The brief called heating "the largest new subsystem." That is backwards.

A glazed chamber at a 1 °F delta to the room sheds almost nothing. For an
illustrative 20 × 16 × 20 in internal volume, the glass conducts **2.6 W per °F**
of delta. Any equipment inside it therefore cooks it:

| Equipment inside the glass | Load | Chamber settles at |
|---|---|---|
| Fogger + light + fan all inside | 36 W | **92.7 °F** — far over the ceiling |
| Light inside, fogger piped in from the base | 12 W | **83.6 °F** — over the ceiling |
| Everything outside; radiant fraction only | 4 W | **80.5 °F** — mid-band |

Air exchange cannot fix this. Holding +1 °F against 36 W by FAE alone needs
**118 CFM** through a box this size, which would strip the casing dry and drop
the RH to room ambient. Against even 12 W it needs 39 CFM. FAE is sized for CO₂,
and it cannot double as a heat sink at these deltas.

**So: nothing hot and nothing wet goes inside the glass.**

- The **fogger lives in the base** and is piped in as fog. That is 24 W removed
  from the chamber and a maintenance item put where hands can reach it.
- The **light lives outside the glazing**. This is now a thermal requirement, not
  a preference, and it decides the lighting question below more than taste does.
- The Pi, PSU, driver and pump were always going to be in the base.

**The room is the thermostat.** With the internal load near 4 W the chamber
floats about 1.5 °F above ambient — 80.5 °F in a 79 °F house, dead centre of the
fruiting band. There is no heating subsystem, no thermostat loop and no heater
safety cutout. An entire subsystem disappears because of where the house sits.

**The headroom is thin in the other direction, and that is the real risk.**
The fruiting ceiling is 81 °F and the chamber runs ~1.5 °F over ambient, so the
house has perhaps 79–80 °F of usable range before the chamber is out of band. If
the house climbs in summer, fruiting stalls. Levers, in order of preference:
boost FAE temporarily (cheap, already present, costs RH), shade or move the piece,
or accept that the piece has a season. **Confirm whether 79 °F is year-round or a
summer figure** — that answer decides whether this needs designing for at all.

---

## Form: a vitrine, and no mast

The mast goes. Its whole justification was holding a photosynthetic working
distance over a plant that grows to 18 in; this organism is 4–8 in and fruits in
the dark. Nothing about V2 needs a vertical armature, and V2 is a new object that
owes V1 no silhouette.

What replaces it is the form the contents actually ask for: **a glass case on a
base.**

- **The base** carries everything that is hot, wet, loud or serviceable —
  reservoir, fogger, pump, FAE fan and filter, Pi, PSU, driver — and presents
  the instrument panel on its front face. This is V1's wet-bay/dry-bay
  architecture and its console language, which both earned their place.
- **The case** is the growing volume and nothing else: substrate, casing surface,
  the mushrooms, air. Single-glazed, doored, drained, fly-screened.
- **The light** sits in the case's top frame, outside the glass.

Heights are open. The subject is 4–8 in standing on a casing surface, and where
that surface sits relative to a standing eye is the composition decision that
replaces V1's height stack. It wants deciding deliberately rather than inherited.

---

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

**Recommendation: A**, possibly with B as a low-level back fill for depth. It is
the only one where the light source disappears and the subject is what you see.

---

## Substrate — buy it finished

Phase I composting is an outdoor, smelly, turned-heap activity and is not worth
attempting for one vitrine. Buy **finished, pasteurised Agaricus compost**,
spawned or ready to spawn, from a mushroom supply house.

**This is a design input, not a shopping note: the supplier's block or bag size
should set the chamber's internal volume, not the other way round.** Sizing a
chamber first and then hunting for substrate to fit it is how you end up
repacking bags by hand forever. Establish what is actually purchasable, in what
increment, before any dimension is fixed.

Casing mix is peat + hydrated lime to about pH 7.5, which is the third time this
project has found that alkalinity — V1's central problem — is this organism's
friend.

---

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
- **No thermal control service.** See above; the room is the thermostat.
- **FAE control** joins the fan service, sized for CO₂ and available as a
  temporary heat lever.

---

## Open decisions

1. **Lighting: A, B or C.** Decides the case's top frame and therefore its
   proportions.
2. **Is 79 °F year-round?** Decides whether summer heat rejection needs designing
   for or merely noting.
3. **What substrate is actually purchasable, in what increment?** Blocks the
   chamber's internal volume, which blocks every other dimension.
4. **How high does the casing surface sit?** The composition decision that
   replaces V1's height stack.
