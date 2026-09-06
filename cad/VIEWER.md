# `cad/viewer.py` — handoff

A standalone brief for anyone (or any agent) picking this up cold. It assumes
no context beyond "there is a repo called grow-lab with a `cad/` package in it".

---

## What it is

A build step that turns the parametric CAD model into **one self-contained HTML
file** you open in a browser. No server, no install, no network. It exists so a
layout decision can be looked at from the positions a person will actually
occupy — standing in front of the panel, leaning over the block — before anyone
commits stock to it.

    python cad/viewer.py            # → cad/out/viewer.html   (~1.5 MB)

Open the file. That is the whole workflow.

The page gives you: orbit/zoom/pan, six stock views plus an eye-height "stand in
front" view, a per-part visibility toggle, a section cut on any axis, the design's
height stack drawn as labelled datums, and a segmented control to flip between
*variants* — the same station rebuilt with different parameters.

It is also published as a hosted page so it opens on a phone. See
**Hosting** below; that copy is a snapshot and does not track `main`.

---

## The two files

| File | What |
|---|---|
| `cad/viewer.py` | The build step. Tessellates every part, base64s the buffers, and injects them into the template. ~220 lines. |
| `cad/viewer_template.html` | The page: CSS, the control rail's markup, and the three.js app. ~570 lines, no build tooling, no framework. |

Nothing else is involved. There is no bundler, no npm, no CSS preprocessor.

---

## How the build works

1. **`main()`** decides which variants to build (see *Variants* below).
2. **`build_variants()`** runs `cad/viewer.py --dump <tmp.json>` **in a
   subprocess, once per variant**, with that variant's `GROWLAB_*` environment
   variables set.
   *Why a subprocess:* `cad/growlab_cad/params.py` reads its knobs from the
   environment **at import time**. Re-importing in-process would not re-read
   them. A fresh interpreter is the only way to get a clean `params` module per
   variant. Do not "optimise" this into a loop with `importlib.reload`.
3. **`_dump()`** (the child) builds `assembly.fabricated()` + `assembly.reference()`,
   calls `part.tessellate(tolerance, angular)` on each, and writes a JSON blob:
   per-part `positions` (Float32) and `indices` (Uint32) as **base64,
   little-endian**, plus the variant's headline dimensions and its full height
   stack. Coordinates are converted **mm → inches** here; the page is in inches
   throughout.
4. **`render_html()`** builds one JSON payload — `{sha, materials, variants}` —
   and substitutes it into the template by replacing the literal string
   `/*__STATION_DATA__*/null`. It also inlines three.js (below).
5. The result is written to `cad/out/viewer.html`. `cad/out/` is **gitignored**;
   CI regenerates it and attaches it to the CAD workflow's artifact.

### three.js is inlined, deliberately

`_three_js()` fetches three.js r128 from cdnjs **once**, caches it at
`cad/out/_three.min.js`, and `render_html()` swaps it into the page in place of
the `<script src=…>` tag.

This is not incidental. The viewer is advertised as one file you open with
nothing installed, and for a long time it was not: it pulled three.js from a
CDN, so offline — on a plane, at a bench with no wifi, from the CI artifact — it
opened as a **blank page with two console errors and no canvas**. Inlining costs
~600 KB and makes the claim true.

If the fetch fails the CDN `<script>` tag stays and the build **prints a
warning** saying what that costs. There is an `assert THREE_TAG in html` guarding
the substitution, so if anyone edits the tag in the template the build fails
loudly rather than silently shipping a network-dependent page.

**The one remaining external request** is the Google Fonts stylesheet in the
template's `<link>`. It degrades to system fonts and nothing breaks. Removing it
would make the page *fully* offline; that has not been done because the fonts
are part of how the page reads.

---

## Variants

A "variant" is the whole station rebuilt with different parameters, presented as
a segmented control at the top of the rail. Switching is instant — every variant's
geometry is already in the file.

Three ways to choose them:

```bash
python cad/viewer.py                              # DEFAULT_VARIANTS
python cad/viewer.py --heights 36 40 44           # a PLINTH_H sweep
python cad/viewer.py --variant "Tall=PLINTH_H:44" # explicit; repeatable
```

`DEFAULT_VARIANTS` (top of `viewer.py`) is currently the canopy's travel: the
light parked 12 in over the media, mid travel, and full lift at 33 in. It used
to be the form candidates (fascia vs box, frame vs plinth); those flags were
removed once the design was decided, which briefly left the toggle with one
entry and nothing to do.

### Gotcha: only two knobs actually exist

`_parse_variant()` will happily turn `Foo=ANYTHING:9` into
`GROWLAB_ANYTHING=9`, and `params.py` will **silently ignore it**. Only two
parameters are wired as knobs:

- `GROWLAB_PLINTH_H`
- `GROWLAB_FIXTURE_ABOVE_MEDIA`

Everything else in `params.py` is a fixed number with a provenance. If you need
to sweep something new, wrap it in `_knob()` in `params.py` first. There is no
error message if you forget — you will just get N identical variants.

### Gotcha: exported knobs leak into the test suite

`params.py` reads `GROWLAB_*` at import, and the CAD tests import it at module
scope to assert the design as documented. A knob left exported in your shell
after a sweep would rebuild the station and fail those tests for a reason
unrelated to your change. `tests/conftest.py` scrubs every `GROWLAB_*` variable
before any test module loads. Do not remove that.

---

## Inside the page

Plain ES5-ish JavaScript in one `<script>`. No modules, no framework.

- **Rendering is on demand.** There is no continuous animation loop burning
  frames. `needs()` sets a `dirty` flag; `frame()` renders only when it is set.
  Any code that changes what is on screen must call `needs()` or the change
  will not appear.
- **Geometry** is decoded from base64 into `Float32Array`/`Uint32Array` and fed
  straight into `BufferGeometry`. Normals are computed in the browser
  (`computeVertexNormals`), which is why the tessellation tolerance matters —
  see *Tuning* below.
- **Materials** come from `viewer.py`'s `MATERIALS` dict: label, colour,
  opacity, and a `group` of `fabricated` or `reference`. Transparent parts get
  a `renderOrder` so the fascia draws last.
- **The section cut** is a three.js clipping plane. The axis `<select>` picks
  the normal, the range slider positions it within a per-axis range derived
  from the current variant's own dimensions. It keeps the half on the viewer's
  side.
- **Datums** are dashed lines at each height in `current.heights`, with HTML
  labels absolutely positioned over the canvas by projecting the line's end
  point through the camera each frame (`placeLabels`). `DATUM_NAMES` maps the
  parameter key to the label text; a height with no entry there is not drawn.
- **Camera framing derives from the piece's height**, not from constants. The
  ratios in `VIEWS` were hand-tuned for a 59.9 in station and are divided by
  that height, so framing is unchanged for a piece of the original size and
  still correct now that the mast takes it to 81.4 in. Before that, every stock
  view ran the mast off the top of the screen.
- **`setView('stand')`** is the one that matters for design decisions: eye at
  62 in, 36 in in front of the face, looking at the panel centre.
- **The rail offsets the projection**, not the viewport: `camera.setViewOffset`
  shifts the frustum so the model centres in the *free* area rather than the
  window. On narrow screens the rail moves to the bottom and `railInset()`
  switches axes.
- **Theme.** Light and dark palettes are CSS custom properties; the WebGL
  background, grid and datum colours are read from JS separately (`palette()`,
  `dark()`). Both a `prefers-color-scheme` listener and a `MutationObserver` on
  `data-theme` rebuild the ground and datums on a theme change. A white piece
  reads very differently on the two grounds — check both.

---

## The one test, and why it exists

`tests/unit/test_cad_geometry.py::TestTheViewerKnowsEveryPart` asserts that
`viewer.MATERIALS` and the assembly's part names **cover each other exactly**.

This is not pedantry. Four parts once went into the assembly during the canopy
work and the materials table was never updated, so they had no label, no colour
and no toggle: the model was right and the picture of it was quietly incomplete.
If you add a part to `assembly.py`, this test fails until you give it a material.
That is the intended behaviour — do not loosen it to a subset check.

Nothing else about the page is tested. There is no browser test, no snapshot.
**Verification is opening the file in a browser and looking at it** — every bug
this viewer has had was found that way and none of them by a test.

---

## Known warts

- **`makeMaterial()` picks metalness by comparing colour strings.**
  `spec.colour === '#4A4F55' || spec.colour === '#C4C9CC' ? 0.5 : 0.05`.
  `#4A4F55` was the mast's colour when the mast was black; it is white now, so
  **that half of the condition is dead code** and only the stainless tray still
  matches. The *result* is defensible — painted steel should not read metallic —
  but the mechanism is fragile. The fix is to make `metalness` a field in
  `MATERIALS` alongside `colour` and `opacity`. Left alone deliberately: it
  changes how the render looks, which is a design call, not a cleanup.
- **`loadVariant()` hides part toggles for parts a variant lacks**
  (`label[data-part]`, `l.hidden = …`). This dates from when variants differed
  in *which parts existed* (frame vs plinth). All current variants have the same
  parts, so it is inert — but correct, and worth keeping if per-form variants
  ever come back.
- **The page is ~1.5 MB**, of which ~600 KB is three.js and the rest is three
  copies of the same geometry at different fixture heights. Adding variants is
  roughly linear in file size. `--tolerance` is the lever.

---

## Tuning

`--tolerance` (mm, default 0.6) and `--angular` (radians, default 0.35) go
straight to `part.tessellate()`. Lower means more triangles, a smoother render
and a bigger file. The current defaults put the whole station at roughly 9,600
triangles per variant, which is nothing for any GPU — the constraint is file
size, not frame rate. Since the mast became a round tube there are curved
surfaces in the model, so a very coarse tolerance is now visible as faceting on
the tube and the collar.

---

## Hosting

The generated file is **already artifact-shaped**: `viewer_template.html` has no
doctype and no `<html>`/`<head>`/`<body>` wrapper, it starts with `<title>` and
an inline `<style>`, and three.js is inlined. It can therefore be published to a
hosted URL as-is, with no conversion step.

The current hosted copy is
`https://claude.ai/code/artifact/63885d8d-4d40-4814-aa53-0f2135c84a8e`.

**It is a snapshot, not a build output.** Nothing republishes it when `cad/`
changes. The viewer prints its **commit SHA under the title** — check that
against `main` before trusting a hosted copy for anything that gets cut.

If you keep this property, keep it deliberately: adding a `<!DOCTYPE html>` to
the template would break publishing, and adding any external `<script src>`
would break both offline use and the host's content-security policy.

---

## If you change something

- **Adding a part to the model** → add it to `MATERIALS` or the test fails.
- **Editing the three.js `<script>` tag** → the inlining assert fires. Update
  `THREE_TAG` in `viewer.py` to match.
- **Adding a variant knob** → wrap the parameter in `_knob()` in `params.py`
  first, or your sweep silently produces identical variants.
- **Changing anything visual** → open the file in a browser, in **both** themes.
  There is no test that will catch you.
- **Renaming `/*__STATION_DATA__*/null`** → it is a literal string match in
  `render_html()`. It will produce a page whose `DATA` is `null` and a blank
  screen, with no build error.
