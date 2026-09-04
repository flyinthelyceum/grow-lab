# cad/ — the V1 station in build123d

The plinth, tray, mast, instrument head and fixture, modelled parametrically
and exported as STEP for finishing in Fusion.

```bash
pip install -e ".[cad]"      # build123d + the OCP kernel, ~150 MB
python cad/build.py          # writes cad/out/
python cad/build.py --check  # build and report, write nothing
pytest tests/unit/test_cad_*.py
```

## What it is

`growlab_cad/params.py` holds every dimension, in inches, each cited to the
document it came from. Values that appear in no document are marked `CHOICE`
— design decisions made to produce a buildable model, and the person finishing
this in Fusion should treat them as proposals.

| Module | Builds |
|---|---|
| `plinth.py` | Carcass on a recessed base: sides, full-height rear panel, floor, the rail at 24 the tray sits on, wet/dry divider, adjustable reservoir shelf, front panel |
| `tray.py` | 16 ga stainless pan nesting inside the carcass top, with pad cutouts and the mast notch; and the four pads |
| `mast.py` | 2 × 3 HSS from the carcass floor to 46, bolted through the rear panel; the 1/4 in flange |
| `head.py` | Five-sided acrylic box plus removable face, from `INSTRUMENT_HEAD_PLANS.md` |
| `cmu.py` | The block, at actual size with two cores — reference |
| `fixture.py` | LED fixture envelope and arm — reference |
| `assembly.py` | Everything, labelled, plus the interference check |

Every part is built in world coordinates — floor at Z = 0, plinth width
centred on X, front face at Y = 0 — so assembly is composition and the tests
can check heights against the docs' table directly.

## The face comes from the emulator's geometry

`head.py` does not restate the hole schedule. It reads
`pi/dashboard/panel_geometry.py` — the same module the `/panel` emulator
draws from. The acrylic that gets cut, the emulator on the dashboard, and the
schedule in the docs are one set of numbers.

## What is deliberately not modelled

**The dial cut diameter.** The Weston 301 bezels are pending calipers, and the
schedule's Ø 2.79 is a Simpson figure. The face carries a witness ring at the
bezel OD, engraved from the back, and no hole. Set `params.DIAL_CUT_DIAMETER`
after measuring and the holes appear.

**The dial mounting studs and Inky standoffs.** Same reason for the studs; the
plans say to transfer the Inky's from the board in hand.

**The LED fixture.** Two LM301H boards on a heatsink with no published
dimensions. An envelope, at the right place, so the assembly reads.

**Bend radii, chamfers, hardware.** Fusion's job.

## One thing the model resolved

The docs say the fixture cantilevers "~10 in forward" of the mast. That number
came from the section drawing, which put the mast *behind* the cabinet. The
docs also say the tray is "notched to clear" the mast — which puts it *inside*
the footprint, against the rear panel. Those are incompatible.

The model goes inside: it is the stiffer mount and the one the notch implies.
The cantilever is then whatever the geometry says — mast centreline to block
centreline, **4.75 in** — and `params.FIXTURE_CANTILEVER` derives it rather
than restating the 10.

## Into Fusion

STEP is tagged in millimetres and built at true size; set the document units
to inches after import to read dimensions as the docs give them. Parts arrive
as named components. The tray and head panels are flat plates in place; lay
them out for the laser from there.

## Tests

`test_cad_params.py` holds `params.py` against the docs' height table with no
kernel needed. `test_cad_geometry.py` builds every part and asserts where it
sits, that nothing fabricated interferes, that the face reads the panel
geometry, and that the dial is a witness mark until a cut is supplied. It
skips cleanly without build123d.
