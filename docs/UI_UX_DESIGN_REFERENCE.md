# UI_UX_DESIGN_REFERENCE.md
GROWLAB — Data Visualization as Embodied Art

> **Register update 2026-09-02:** Dark backgrounds are ABANDONED across every surface (screen,
> e-ink, physical panel). The house register is the light **Transparent / Material Non-Artifice**
> language (warm gray ground, ghosted glass, hairline strokes, one earned accent). **Art Mode is
> RETIRED** to preserve the piece's intransitivity. See `V1_PHYSICAL_BUILD.md` and the fabrication
> design-language canon. Where older text below said "dark," read "light" — corrected inline.

---

## 1. Purpose

The **GROWLAB interface** is not a monitoring dashboard.

It is a **translation layer** that renders invisible biological processes visible.

The system observes:

- light cycles
- humidity rhythms
- nutrient drift
- irrigation pulses
- plant growth

The UI converts these processes into **legible visual forms**.

The interface therefore operates as:

scientific instrument  
+ environmental observatory  
+ living artwork

The design language must express:

- clarity
- calmness
- precision
- temporal awareness

Avoid:

- consumer smart-home aesthetics
- busy dashboards
- bright colors
- gamified UI
- **dark-mode dashboards** (abandoned 2026-09-02)

Preferred aesthetic:

- scientific instrumentation
- minimalist industrial design
- calm data landscapes
- **light, reflective-calm surfaces** (Transparent register)

---

## 2. Core Design Principles

### Data as Rhythm

Plants live in cycles.

The UI should visualize **time patterns**, not static values.

Bad:

Humidity: 48%

Good:

24-hour humidity waveform

The **e-ink display carries the rhythm** (sparkline / waveform, phase, trend). The **analog VU
meters express the same idea in a different register** — the live instrument reading as an object,
the CERN/Leica "number as object." Instrument (now) + record (rhythm) together.

---

### Environmental Subsystems

All UI components should map to real system architecture.

Primary subsystems:

- LIGHT
- WATER
- AIR
- ROOT
- PLANT

Each subsystem displays:

- current state
- recent trend
- event history

The physical panel's two vitals map here: **pH = ROOT, moisture = PLANT.**

---

### Calm Interface

The dashboard must feel like a **scientific instrument**, not an app.

Rules:

- **light backgrounds** (warm gray, reflective-calm — NOT dark mode)
- minimal color
- large typography
- slow movement

---

### Temporal Awareness

Every dashboard screen should contain **historical context**.

Example windows:

- 1 hour
- 24 hours
- 7 days

Historical context reveals environmental patterns.

---

## 3. Visual Inspiration

### Hans Haacke — Real-Time Systems with Stakes

Haacke's *Condensation Cube* (1963), *Grass Grows* (1969), and *Rhine Water Purification Plant* (1972) proposed that a biological or physical process, made visible through real-time monitoring, can be the work itself rather than a representation of it.

Lessons:

- the apparatus and the process are continuous; the system is the artwork, not its illustration
- meaning is structural, not aesthetic
- the data is the biography of what is being kept alive, not material to render beautiful
- if the work has stakes, those stakes are inseparable from the cycles being measured

Use environmental data as the actual record of sustained care.

Examples:

- humidity oscillations as the trace of breathing
- irrigation pulses as the rhythm of attention
- light cycles as the geometry of presence

---

### Newton & Helen Mayer Harrison — Ecological Feedback as Form

The Harrison Studio's *Making Earth* and adjacent projects from the early 1970s onward used data collection and life-support systems for living ecologies as primary artistic material, decades before the technology was practical.

Lessons:

- life support apparatus is form, not infrastructure to hide
- the work runs across time scales the viewer cannot compress
- caring for the system over months is the medium

---

### CERN Control Room — Scientific Visualization

These systems monitor **invisible physical processes**.

Design lessons (structure kept; palette flipped to light):

- **light backgrounds** with thin, precise ink lines (was: dark backgrounds, luminous lines)
- multi-panel layouts
- temporal graphs
- subsystem organization

Your installation mirrors this structure.

---

### NASA Mission Control — System Health Interfaces

NASA interfaces emphasize:

- situational awareness
- system hierarchy
- signal clarity
- alert visibility

Colors used sparingly (semantic, on light):

- green = healthy
- yellow = caution
- red = critical

---

### Leica Interface Design

Characteristics:

- strong typography
- minimal layout
- extreme clarity
- high contrast

Numbers are treated as **objects of importance**.

Example:

PH      6.14  
EC      1.82  
TEMP    72.7°F  
RH      48%

---

### Giorgia Lupi — Data Humanism

Data can be:

- expressive
- poetic
- personal

Applications:

- seasonal patterns
- growth arcs
- irrigation rhythms
- nutrient drift

---

## 4. Dashboard Architecture

The web interface is served by FastAPI at `http://<pi-ip>:8000`. **Light theme** (dark abandoned).

### Observatory View (`/`)

5-panel grid layout with header (title, time controls, system clock) and footer (WebSocket status, sensor count).

| Panel | Live Value | Chart | Meta |
|-------|-----------|-------|------|
| LIGHT | PWM level | StepAfter area + photoperiod band | Mode, schedule |
| WATER | Last event | EKG pulse timeline | Time since last |
| AIR | Temp °F | Dual-axis CatmullRom (temp + humidity) | Humidity %, pressure hPa |
| ROOT | pH | Stacked sparklines (pH + EC) with target bands | EC µS/cm, reservoir temp °F |
| PLANT | Soil moisture % | D3 arc gauge | Camera feed, capture count |

Time window selector: **1H / 24H / 7D**. Values update live via WebSocket at 3-second intervals.

**Art Mode is retired — the footer ART link is removed.** (See Section 8.)

---

## 5. Physical & Embedded Displays

### e-ink — the quiet face (primary)

Pimoroni **Inky Impression 7.3"** (7-colour e-paper), on the enclosure door. Reflective and light by
nature — aligns with the abandoned-dark decision.

Shows, slow and unlabeled (holds its frame unpowered):

- **temporal sparkline / waveform** (the rhythm — Data as Rhythm)
- current phase (vigil / flowering / dormancy)
- last-tended time, next event
- ambient °F

### Analog VU meters — the vitals (physical panel)

Two **Weston 301 3-1/2 in centre-zero** movements (30-0-30 uA and 100-0-100 uA), driven
directly from an MCP4728 quad DAC through fixed series resistors — one differential pair per
meter. No op-amp stage: that was an answer to a milliamp problem these microampere movements
do not have.

**pH (ROOT) + EC (ROOT).** Not moisture — the sensors that exist are pH and EC.

Centre means on target, so drift reads as asymmetry and the instrument is legible without
reading numbers. A stale reading eases the needle home and raises a flag rather than freezing
or slamming it. "Numbers as objects," the same idea as the e-ink rhythm in a different
register.

The face is emulated at `/panel` — true proportion, four candidate layouts, and the needles
on the same maths and config as the hardware, so a layout and the encoding can both be judged
before acrylic is cut. See [INSTRUMENT_HEAD_PLANS.md](INSTRUMENT_HEAD_PLANS.md).

### OLED (legacy / optional)

SH1106 128×64 at I2C 0x3C — from the bench build. Superseded by the e-ink for the art piece;
keep only if useful for a compact status readout. If used, mirror the light register conceptually
(OLED is emissive, so treat as a secondary readout, not the face).

---

## 6. Web Visualization Technology

Backend (implemented):

- Python 3.12
- FastAPI (routes: pages, API, WebSocket)
- SQLite (sensor readings, events, images)

Frontend (implemented):

- D3.js v7 (all charts: StepAfter, CatmullRom, sparklines, arc gauge)
- Vanilla JS (no framework)

Live updates (implemented):

- WebSocket at `/ws/updates` (3-second polling)
- REST API at `/api/readings/<sensor>/downsampled?window=<window>`

Note: the Canvas 2D art-mode renderer is retired (Section 8).

---

## 7. Timelapse Integration

Hardware: Raspberry Pi Camera Module 3. Capture interval: 10 minutes. Images timestamped and correlated with sensor logs.

Example queries:

- show plant when pH < 5.5
- show plant after irrigation
- show plant at peak humidity

---

## 8. Art Mode — RETIRED (2026-09-02)

The full-screen generative Canvas 2D visualization (radial rings, breathing bands, water-pulse
markers, particle field) is **retired**. It read as gallery-projection data-spectacle — the
Anadol-adjacent, transitive move the art canon explicitly rejects. The piece is **intransitive**:
it does not perform for an audience.

The Haacke / Harrison intent survives without the spectacle — through the **honest instrument**
(the meters, the pilot lamp, the wiring shown not hidden) and **the record** (the e-ink rhythm,
the sensor history as the biography of sustained care). The interface reveals rhythm; it is not a
show. If a "look-in" ever returns, it must be derived from live state, unlabeled, and for the
tender — not choreographed for viewers.

**Executed in code 2026-09-05.** Until now this was a ruling the codebase had not caught up with.
Removed: the `GET /art` route, `templates/art.html`, `static/art.js`, and the whole `static/art/`
module directory (`art-core`, `radial-ring`, `humidity-ring`, `ph-ring`, `ec-ring`, `water-pulses`,
`pressure-field`, `ambient-particles`); the ART nav links in the observatory header and footer; the
`/art` row in the dashboard's public-surface table; and the Art Mode passages in `README.md`,
`SYSTEM_ARCHITECTURE.md`, and `DATA_ARCHITECTURE.md`. Its sibling Dream Mode went the same way on
2026-09-04. The decision text above is unchanged and stays here as its only written record.

---

## 9. Typography

- **Bricolage Grotesque** — display headings (the committed register's characterful face)
- IBM Plex Sans — body / structure
- IBM Plex Mono / Space Mono — the machine layer, numerics, engraved labels
- Inter, Söhne — acceptable UI alternates

Guidelines:

- large numeric values
- generous spacing
- aligned columns

---

## 10. Color System

Primary palette (light):

- **light background** (warm gray ~#ccd0cd, Transparent register)
- dark ink text
- soft grey grid lines

Accent colors (used sparingly, semantic):

- cyan = water
- amber = light
- green = plant health
- red = alert

Note: the **physical panel** stays monochrome + one warm accent (amber jewel / warm dial backlight);
the **screen** may use the semantic accents on the light ground. Use color sparingly everywhere.

---

## 11. Motion Rules

Animations must be:

- slow
- continuous
- calm

Avoid:

- rapid blinking
- high-frequency updates
- UI jitter

Recommended update cadence:

1–5 seconds

---

## 12. Naming

Suggested title:

GROWLAB

Alternatives:

- Plant System Monitor
- GROWLAB Instrument
- Bio‑Environmental Console

---

## 12b. Nothing in the piece moves any more — 2026-09-05

A standing critique, recorded because it was arrived at by accumulation and nobody chose it.

GROWLAB was conceived with an atmosphere: rain simulators working in the canopy, and a fan
animating the plants. Both are now gone. Overhead rain was deferred to v2 on a sound
horticultural argument (`V1_PHYSICAL_BUILD.md` — overhead water on ranunculus invites
botrytis and powdery mildew). The fan was cut on 2026-09-05 because a 120 mm axial part
dominated the visual field and no placement, mechanism, concealment or styling survived
review. **Each decision was defensible on its own. Their sum was never put to anyone.**

What is left that moves: the two Weston needles on the front panel, easing at ~30 Hz, and
the light going on and off. Nothing in the growing volume itself moves at all. For a piece
whose charter is a *living* plant sculpture where biology and engineered systems coexist
visibly, that is a real loss and it should be treated as an open wound rather than a
settled state.

This is the mirror of the failure `SUBTRACT_PASS.md` was written to catch. That brief warns
that generative work only ever adds, and that each addition is individually justified while
the accumulation is invisible. Subtraction has exactly the same failure mode: eight
defensible cuts in one day, and a dimension of the work quietly gone. **Counting lines
removed does not measure what a piece lost.**

The fan's software survives, disabled, so this is reversible without rewriting anything.
What does not survive is the assumption that motion is optional.

## 12c. Everything metal goes white — 2026-09-05

Everything structural in the piece was black: the steel base frame, the instrument case, the
backplate. Warm ply was the other register, and the two of them were the whole palette,
consistent enough that it read as a rule rather than as a series of choices.

The mast went white first, and that raised the question rather than answering it. A black
tube 81 in tall is a heavy vertical stroke through the middle of the composition, and the
thing the fan taught is that a dark object in the growing volume dominates whatever leverage
it has; a white mast reads as a drawn line, closer to a copy stand or a lab armature than to
structure. But one white object among black ones reads as an error. One departure from a
consistent rule is a mistake; a whole register is a decision.

**So the whole register goes white.** Frame, mast, carriage, arm, case, plate, backplate.
One white DTM acrylic over all of it, steel and aluminium alike. The ply is unchanged and the
palette is still two registers — it is the same structure with the value inverted.

**What that costs is not in the CAD, and it is worth naming here rather than in the build
doc, because it is a design cost and not a fabrication one.**

The console inverts. The reference was the Transparent speaker: black metal components with
the wiring in view, the apparatus legible instead of hidden in painted casework. The
casework is now the light thing and the apparatus is the dark thing inside it. That is
arguably a *stronger* reading of the same idea — the Pi, the i3, the meter driver and every
cable now declare themselves against a light ground instead of receding into a dark one, and
"material non-artifice" is better served by components you cannot help seeing. It is also
much harder to keep honest. A dark cable on a dark backplate was nearly invisible; on white
it is the highest-contrast object behind the glass. **Cable discipline stops being a nicety
and becomes part of the composition.**

And the meters change relationship. The Weston 301s are aged Bakelite — dark rings, cream
faces. On a black plate the cream face was the bright thing and the ring disappeared into
the panel. On white the ring becomes the dark thing and the cream face sits only a few
points off the plate around it. The needles still read; whether the *pair* reads is a
question that cannot be answered from a scan, and § *Making the plate* now says to hold a
proof print in the meter against the coated plate before committing the print run.

**What is not resolved by this.** § 12b's complaint stands, unchanged and unaddressed:
nothing in the growing volume moves. The head is adjustable, not animate — a person moves it
twice in a season. Painting the piece white is a decision about how it reads standing still.

---

## 13. Key Takeaway

The UI is not a dashboard.

It is a **window into the metabolism of a living system**.

The interface should reveal:

- rhythms
- cycles
- patterns

that would otherwise remain invisible — as an instrument, for the tender, not a show.
