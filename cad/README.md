# cad/ — the V1 station in build123d

The cabinet with the instrument face in its front, the tray, the mast and the
fixture, modelled parametrically and exported as STEP for finishing in Fusion.

```bash
pip install -e ".[cad]"      # build123d + the OCP kernel, ~150 MB
python cad/build.py          # writes cad/out/
python cad/build.py --check  # build and report, write nothing
python cad/render.py         # front / side / plan elevations as SVG
python cad/viewer.py         # one-file 3D viewer with the design candidates
python cad/fabrication.py    # DXFs and a cut list, into cad/out/fab/
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
| `face.py` | The instrument plate — the hole schedule from `INSTRUMENT_HEAD_PLANS.md` and `panel_geometry.py`, in 1/8 in aluminium (or 1/4 in acrylic in the box form) |
| `case.py` | The black aluminium instrument case: the plate plus the folded box behind it |
| `tray.py` | 16 ga stainless pan nesting inside the carcass top, with pad cutouts and the mast notch; and the four pads |
| `mast.py` | 2 × 3 HSS from the carcass floor to its cap, in the dry bay, bolted through the rear panel |
| `fixture.py` | The arm and cross bar from the mast's cap, and the LED fixture envelope — reference |
| `cmu.py` | The block, at actual size with two cores — reference |
| `assembly.py` | Everything, labelled, plus the interference and design-conflict checks |
| `viewer.py` + `viewer_template.html` | Tessellates every part at several `PLINTH_H` and writes one HTML file: orbit, part toggles, section cut, datums, a stand-in-front eye-height view |
| `fabrication.py` | The pack you cut from: plate, case development, fascia and backplate as DXFs in inches, plus a cut list derived from the same params |
| `fusion/` | The Fusion 360 script and the iteration loop — see `fusion/README.md` |

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
together and leaves the lift alone. **36 is decided.**

## The design

A plywood box with an acrylic window is a plywood box. The design (decided
2026-09-04, reference: the Transparent speaker) puts the instrument behind
glass:

- **Fascia** — a clear acrylic band across the whole front, recessed behind
  the front plane, over an open console bay, between chamfered corners. Two
  holes in it, for the knob shafts; everything else is read through it.
- **Instrument case** (`case.py`) — black aluminium: a 1/8 in plate carrying
  the hole schedule, the front of a folded box the electronics live in. It
  sits on a ply ledge 0.1 in behind the glass and pulls out forward as one
  unit. A black backplate on the partition behind it; the loom drops through
  the chase behind the ledge to the PSU below.

- **Steel base frame** — the cabinet floats 6 in on a welded 1 × 1 frame,
  legs inset an inch so it overhangs, and the mast runs to the floor as one
  of its members. Legs, ring, mast, fixture arm and case are one black
  register; the ply body is the other.

`GROWLAB_FRAME=0` puts it back on a recessed plinth and `GROWLAB_FASCIA=0`
rebuilds the plain box, both for the record; `python cad/viewer.py` builds
all three. The lift, the shelf and the block do not move between them, which
`test_cad_forms.py` asserts.

## Looking at it

`viewer.html` (in `cad/out/` and in the CI artifact) is the model in a
browser, no install: orbit, toggle parts, cut a section on any axis, read
the height datums, flip between cabinet heights, and stand where a person
stands — eye at 62 in, 36 in in front of the face — to judge the panel. It
is the fast way to look before deciding; `PLINTH_H` variants are built by
setting `GROWLAB_PLINTH_H` in the environment, which `params.py` honours for
that one knob.

## The fabrication pack

`python cad/fabrication.py` writes `cad/out/fab/` — see its own README. Two
things worth knowing before you open a DXF:

**They are inches, and that is checked.** build123d's DXF exporter writes a
unit into the header but does not convert the coordinates, exactly like its
SVG exporter. The flat patterns are therefore authored directly in inch
coordinates rather than through `_shapes` (which multiplies by `IN`), and
`test_cad_fabrication` reads the files back to assert that the header and the
geometry agree. Do not "tidy" that by reusing the solid model's helpers.

**Bends carry no allowance.** The blank is the sum of the flat faces and the
bend lines sit at the theoretical fold; the K-factor is the fabricator's.
Send the STEP alongside so they can develop it their own way if they prefer.

## Into Fusion

STEP is tagged in millimetres and built at true size; the sync script sets
the document units to inches so dimensions read as the docs give them. Parts
arrive as named components. The front panel, the face and the door are flat
plates in place; lay them out for the laser or the saw from there.

The loop — a Fusion project with the import as a versioned design, a
separate finishing design that links it, and a script that turns "new
artifact" into "new version" — is in `fusion/README.md`.

## Tests

`test_cad_params.py` holds `params.py` against the docs' height table with no
kernel needed, and checks every emulator layout's elements clear the front
panel's lip. `test_cad_geometry.py` builds every part and asserts where it
sits, that nothing fabricated interferes, that no reference envelope meets a
fabricated part, that the pan sweeps straight out through the rear door, that
the face reads the panel geometry, and that the dial is a witness mark until a
cut is supplied. It skips cleanly without build123d.
