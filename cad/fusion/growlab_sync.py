"""GROWLAB → Fusion 360: import the latest station STEP as a new version.

Run from Fusion: UTILITIES → ADD-INS → Scripts and Add-Ins → + (green plus)
→ pick this folder → Run. Or copy the folder into Fusion's Scripts directory.

What it does, every time you run it
-----------------------------------
1. Asks for the STEP (defaults to the last one you picked). Point it at
   ``growlab_v1_station.step`` from the ``growlab-v1-station-cad`` CI
   artifact, unzipped.
2. Imports it into a new document, units set to inches.
3. Names the parts' appearances by what they are (ply, stainless, steel,
   acrylic, concrete), matched on the component names the STEP carries.
4. Saves it into the project ``GROWLAB`` → folder ``Station imports`` under
   the fixed name ``growlab_v1_station``. Saving under the same name in the
   same folder makes a **new version** of the same design, so the version
   history in the Data Panel is the history of the CAD in the repo, and
   anything that *inserts* this design (your finishing file) gets an
   "out of date" flag and a one-click update.

What it does not do
-------------------
Touch your finishing design. Keep manual work (fillets, hinges, hardware,
drawings, CAM) in a separate design that inserts this one as a linked
component — see README.md — so re-running this never overwrites it.

This script was written against the Fusion API reference and cannot be run
in the environment that wrote it. If a call fails, the message box says
which one; the fix is usually a renamed appearance or a moved folder.
"""

import os
import traceback

import adsk.core
import adsk.fusion

PROJECT_NAME = "GROWLAB"
FOLDER_NAME = "Station imports"
DESIGN_NAME = "growlab_v1_station"

# Component name (from the STEP's labels) → appearance in the Fusion 360
# Appearance Library. Matched by substring, first hit wins.
APPEARANCES = [
    ("carcass", "Plywood, Birch"),
    ("front_panel", "Plywood, Birch"),
    ("rear_door", "Plywood, Birch"),
    ("top_rail", "Plywood, Birch"),
    ("bay_divider", "Plywood, Birch"),
    ("console_partition", "Plywood, Birch"),
    ("reservoir_shelf", "Plywood, Birch"),
    ("plinth_base", "Paint - Enamel Glossy (Black)"),
    ("cmu_pads", "Plywood, Birch"),
    ("tray", "Steel - Satin"),
    ("mast", "Steel - Satin"),
    ("fixture", "Aluminum - Anodized Glossy (Grey)"),
    ("instrument_face", "Acrylic (Clear)"),
    ("cmu_vessel", "Concrete"),
    ("media", "Soil"),
    ("reservoir", "Glass (Blue)"),
    ("console_electronics", "Plastic - Translucent Matte (Green)"),
]

_last_path_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".last_step_path")


def _remember(path):
    try:
        with open(_last_path_file, "w") as f:
            f.write(path)
    except OSError:
        pass


def _recall():
    try:
        with open(_last_path_file) as f:
            return f.read().strip()
    except OSError:
        return ""


def _pick_step(ui):
    dlg = ui.createFileDialog()
    dlg.title = "GROWLAB — pick growlab_v1_station.step"
    dlg.filter = "STEP files (*.step;*.stp)"
    last = _recall()
    if last and os.path.isdir(os.path.dirname(last)):
        dlg.initialDirectory = os.path.dirname(last)
    if dlg.showOpen() != adsk.core.DialogResults.DialogOK:
        return None
    _remember(dlg.filename)
    return dlg.filename


def _project(app):
    hub = app.data.activeHub
    projects = hub.dataProjects
    for i in range(projects.count):
        if projects.item(i).name == PROJECT_NAME:
            return projects.item(i)
    return projects.add(PROJECT_NAME)


def _folder(project):
    root = project.rootFolder
    existing = root.dataFolders.itemByName(FOLDER_NAME)
    return existing if existing else root.dataFolders.add(FOLDER_NAME)


def _appearance_for(app, name):
    lib = app.materialLibraries.itemByName("Fusion 360 Appearance Library")
    if lib is None:
        lib = app.materialLibraries.itemByName("Fusion Appearance Library")
    if lib is None:
        return None
    lowered = name.lower()
    for key, appearance_name in APPEARANCES:
        if key in lowered:
            return lib.appearances.itemByName(appearance_name)
    return None


def _apply_appearances(app, design):
    root = design.rootComponent
    applied, missed = 0, []
    occs = root.allOccurrences
    for i in range(occs.count):
        comp = occs.item(i).component
        appearance = _appearance_for(app, comp.name)
        if appearance is None:
            missed.append(comp.name)
            continue
        bodies = comp.bRepBodies
        for j in range(bodies.count):
            bodies.item(j).appearance = appearance
            applied += 1
    return applied, missed


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        step = _pick_step(ui)
        if not step:
            return

        options = app.importManager.createSTEPImportOptions(step)
        options.isViewFit = True
        doc = app.importManager.importToNewDocument(options)
        if doc is None:
            ui.messageBox("Import returned no document. Is the STEP intact?", "GROWLAB")
            return

        design = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
        design.fusionUnitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.InchDistanceUnits

        applied, missed = _apply_appearances(app, design)

        folder = _folder(_project(app))
        description = "Imported by growlab_sync.py from " + os.path.basename(step)
        ok = doc.saveAs(DESIGN_NAME, folder, description, "")
        if not ok:
            ui.messageBox("saveAs returned False — the document is open but not saved.", "GROWLAB")
            return

        msg = (
            "Imported and saved as a new version of\n"
            f"{PROJECT_NAME} / {FOLDER_NAME} / {DESIGN_NAME}\n\n"
            f"Appearances applied to {applied} bodies."
        )
        if missed:
            msg += "\nNo appearance rule for: " + ", ".join(sorted(set(missed)))
        msg += "\n\nIf your finishing design inserts this one, it now shows an update badge."
        ui.messageBox(msg, "GROWLAB")
    except Exception:
        if ui:
            ui.messageBox("growlab_sync failed:\n{}".format(traceback.format_exc()), "GROWLAB")
