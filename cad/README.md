# cad/ — the V1 station in build123d

The cabinet with the instrument face in its front, the tray, the mast and the
fixture, modelled parametrically and exported as STEP for finishing in Fusion.

```bash
pip install -e ".[cad]"      # build123d + the OCP kernel, ~150 MB
python cad/build.py          # writes cad/out/
python cad/build.py --check  # build and report, write nothing
python cad/render.py         # front / side / plan elevations as SVG
pytest tests/unit/test_cad_*.py
```

## What it is

`growlab_cad/params.py` holds every dimension, in inches, each cited to the
document it came from. Values that appear in no document are marked `CHOICE`
— design decisions made to produce a buildable model, and the person finishing
this in Fusion should treat them as proposals. Its docstring says why the
station is arranged the way it is.

| Module | Builds |
|---|---|
| `plinth.py` | Carcass on a recessed base: sides, floor, full-height rear panel with the wet-bay door opening, the removable front panel with the face pocketed into it, the rail under the tray, the console partition, the wet/dry divider, the adjustable reservoir shelf. Also the rear door, and the reservoir and console-electronics envelopes |
| `face.py` | The 1/4 in acrylic instrument face, from `INSTRUMENT_HEAD_PLANS.md` and `panel_geometry.py` |
| `tray.py` | 16 ga stainless pan nesting inside the carcass top, with pad cutouts and the mast notch; and the four pads |
| `mast.py` | 2 × 3 HSS from the carcass floor to its cap, in the dry bay, bolted through the rear panel |
| `fixture.py` | The arm and cross bar from the mast's cap, and the LED fixture envelope — reference |
| `cmu.py` | The block, at actual size with two cores — reference |
| `assembly.py` | Everything, labelled, plus the interference and design-conflict checks |

Every part is built in world coordinates — floor at Z = 0, plinth width
centred on X, front face at Y = 0 — so assembly is composition and the tests
can check heights against the docs' table directly.

## The face comes from the emulator's geometry

`face.py` does not restate the hole schedule. It reads
`pi/dashboard/panel_geometry.py` — the same module the `/panel` emulator
draws from — and `plinth.py` cuts the front panel's pocket and opening from
the same numbers. The acrylic that gets cut, the hole it sits in, the
emulator on the dashboard, and the schedule in the docs are one set of
numbers.

## What is deliberately not modelled

**The dial cut diameter.** The Weston 301 bezels are pending calipers, and the
schedule's Ø 2.79 is a Simpson figure. The face carries a witness ring at the
bezel OD, engraved from the back, and no hole. Set `params.DIAL_CUT_DIAMETER`
after measuring and the holes appear.

**The dial mounting studs and Inky standoffs.** Same reason for the studs; the
plans say to transfer the Inky's from the board in hand.

**The LED fixture.** Two LM301H boards on a heatsink with no published
dimensions. An envelope, at the right place, so the assembly reads.

**Bend radii, chamfers, hinges, hardware.** Fusion's job.

## What the model decided

The first pass (2026-09-04, morning) built the docs' mast-and-head layout and
found the reservoir pan and the mast could not both fit a 14 in cabinet. The
answer was a different arrangement rather than a deeper box: panel into the
cabinet's front, doors to the rear, cabinet to the height that needs. With
the pan *behind* the console bay instead of under it, the shelf rises and
the static lift falls from 17 in to 13 in on the same pump; putting the pan
under a console deck would have pushed it to ~28 in, off the pump's curve.
`params.DEPTH` and `params.HEIGHTS` carry the arithmetic; `build.py` prints
it.

`PLINTH_H` is the one knob. It moves the panel, the block and the light
together and leaves the lift alone.

## Into Fusion

STEP is tagged in millimetres and built at true size; set the document units
to inches after import to read dimensions as the docs give them. Parts arrive
as named components. The front panel, the face and the door are flat plates
in place; lay them out for the laser or the saw from there.

## Tests

`test_cad_params.py` holds `params.py` against the docs' height table with no
kernel needed, and checks every emulator layout's elements clear the front
panel's lip. `test_cad_geometry.py` builds every part and asserts where it
sits, that nothing fabricated interferes, that no reference envelope meets a
fabricated part, that the pan sweeps straight out through the rear door, that
the face reads the panel geometry, and that the dial is a witness mark until a
cut is supplied. It skips cleanly without build123d.
