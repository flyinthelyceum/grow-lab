# Fusion 360 — the iteration loop

The model lives in code (`cad/growlab_cad/`). Fusion is where you look at it,
finish it by hand, draw it and cut it. The loop is built so that a change on
either side never destroys work on the other.

## One-time setup

1. **Get the script into Fusion.** UTILITIES → ADD-INS → *Scripts and Add-Ins*
   → the green **+** next to *My Scripts* → pick this folder (`cad/fusion/`).
   `growlab_sync` appears in the list. (Or copy the folder into Fusion's
   scripts directory: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/`
   on macOS, `%APPDATA%\Autodesk\Autodesk Fusion 360\API\Scripts\` on Windows.)

2. **Run it once.** It asks for a STEP; give it `growlab_v1_station.step`
   from the CI artifact (below). It creates the project **GROWLAB**, the
   folder **Station imports**, and saves the design **growlab_v1_station**
   there, units in inches, appearances set by material. That design is the
   *import target*: never edit it by hand.

3. **Make your finishing design.** New design in **GROWLAB** → save it as
   `growlab_v1_finish` (any name; not in *Station imports*). In the Data
   Panel, right-click **growlab_v1_station** → *Insert into Current Design*.
   It arrives as a **linked** component (chain-link badge). Ground it. All
   manual work — fillets, the door's hinges, hardware, joints, drawings,
   CAM — goes in this file, on top of or beside the linked import, never
   inside it.

## Every iteration

**Code side (me):** change `params.py` or a part module → PR → merge. The
`CAD` workflow builds and publishes `cad/out/` as the artifact
**growlab-v1-station-cad** on that run (Actions → CAD → the run → Artifacts).
It also builds `viewer.html`, the in-browser model, so most looks never need
Fusion at all.

**Fusion side (you):** download the artifact, unzip, run **growlab_sync**,
point it at the new `growlab_v1_station.step`. Because it saves under the
same name in the same folder, Fusion records a **new version** of
`growlab_v1_station` — the Data Panel's version history is the repo's history.
Open `growlab_v1_finish`; the linked import shows an *out of date* badge;
right-click → *Get Latest*. Your finishing features stay.

## What survives an update and what does not

Fusion re-derives the linked component from the new STEP. Anything **inside**
that component is replaced. Anything in `growlab_v1_finish` that references
the import by **joint or position** survives. Features that reference the
import's **faces** (a fillet on an imported edge, a sketch projected from an
imported face) may lose their reference when the underlying geometry changes,
and Fusion flags them yellow. So:

- **Do in code:** anything dimensional, anything that has to stay true to the
  docs, anything you would want re-derived when a parameter moves. Hole
  schedules, notches, pockets, clearances. Ask and it moves.
- **Do in Fusion:** what has no parameter — cosmetic fillets, the choice of
  hinge, hardware from McMaster, the drawing sheets, the CAM setups. Attach
  by joint to the linked import, not by feature on it.
- **When a parameter needs to move**, say so rather than dragging a face:
  a dragged face in the finishing file is a second source of truth, and the
  next update overwrites it anyway.

## Parts and appearances

The STEP carries the component names from the code (`carcass_shell`,
`front_panel_removable`, `rear_door_wet_bay`, `tray_304_16ga`,
`mast_shaft_2x3_hss`, `instrument_face_acrylic`, …). `growlab_sync` matches
those names to appearances in the *Fusion 360 Appearance Library* by
substring — the table is at the top of `growlab_sync.py`. Reference parts
(the block, media, pan, fixture envelope, console electronics) come in too,
so the composition reads; they are the bought or undimensioned things and
are not for fabrication.

## Units

STEP is unit-tagged in millimetres and built at true size. The script sets
the document's display units to inches so dimensions read as the docs give
them. Nothing is scaled.

## If the script fails

The message box names the call. The usual causes: an appearance renamed in a
Fusion update (edit the table), or the **GROWLAB** project moved to another
hub (the script uses the active hub). The script has not been run by the
person who wrote it — there is no Fusion in the environment that produced
it — so the first run is the test. Report what it says and it gets fixed.
