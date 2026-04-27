
# UI_UX_DESIGN_REFERENCE.md
GROWLAB — Data Visualization as Embodied Art

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

Preferred aesthetic:

- scientific instrumentation
- minimalist industrial design
- calm data landscapes

---

## 2. Core Design Principles

### Data as Rhythm

Plants live in cycles.

The UI should visualize **time patterns**, not static values.

Bad:

Humidity: 48%

Good:

24-hour humidity waveform

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

---

### Calm Interface

The dashboard must feel like a **scientific instrument**, not an app.

Rules:

- dark backgrounds
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

Design lessons:

- dark backgrounds
- thin luminous lines
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

Colors used sparingly:

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
TEMP    22.7°C  
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

## 4. Dashboard Architecture (Implemented)

The web interface is served by FastAPI at `http://<pi-ip>:8000`.

### Observatory View (`/`)

5-panel grid layout with header (title, time controls, system clock) and footer (WebSocket status, sensor count, ART link).

| Panel | Live Value | Chart | Meta |
|-------|-----------|-------|------|
| LIGHT | PWM level | StepAfter area + photoperiod band | Mode, schedule |
| WATER | Last event | EKG pulse timeline | Time since last |
| AIR | Temp °F | Dual-axis CatmullRom (temp + humidity) | Humidity %, pressure hPa |
| ROOT | pH | Stacked sparklines (pH + EC) with target bands | EC µS/cm, reservoir temp °F |
| PLANT | Soil moisture % | D3 arc gauge | Camera feed, capture count |

Time window selector: **1H / 24H / 7D**. Values update live via WebSocket at 3-second intervals.

### Art Mode (`/art`)

Full-screen generative visualization. See Section 8 for details.

---

## 5. Embedded OLED Interface

Small OLED display embedded in installation.

Purpose:

make the system legible to observers

Hardware (implemented):

SH1106 OLED (GME12864)
128x64
I2C at 0x3C

Screen rotation (5-second cycle):

**Page 1 — Sensor Values:**

GROWLAB

Air      72.4°F
Humidity  48%
H2O Temp  67.6°F

**Page 2 — System Overview:**

Uptime, subsystem status

**Page 3 — Irrigation Schedule:**

Next/last pump events

**Page 4 — Sparkline Trend Chart**

Alternate screen:

SYSTEM STATUS

LIGHT   ████████  
WATER   ████  
AIR     █████  
ROOT    █████

Trend screen:

PH TREND

6.4 ─────  
6.3 ────  
6.2 ───  
6.1 ──

Use sparklines to represent trends.

---

## 6. Web Visualization Technology

Backend (implemented):

- Python 3.12
- FastAPI (routes: pages, API, WebSocket)
- SQLite (sensor readings, events, images)

Frontend (implemented):

- D3.js v7 (all charts: StepAfter, CatmullRom, sparklines, arc gauge)
- Canvas 2D (art mode: radial ring, humidity, water pulses, pressure, particles)
- Vanilla JS (no framework)

Live updates (implemented):

- WebSocket at `/ws/updates` (3-second polling)
- REST API at `/api/readings/<sensor>/downsampled?window=<window>`

---

## 7. Timelapse Integration

Recommended hardware:

Raspberry Pi Camera Module v3

Capture interval:

10 minutes

Images timestamped and correlated with sensor logs.

Example queries:

- show plant when pH < 5.5
- show plant after irrigation
- show plant at peak humidity

---

## 8. Dashboard as Artwork

The system includes a dedicated **Art Mode** (`/art`) — a full-screen generative Canvas 2D visualization.

### Implemented Layers

1. **Pressure atmosphere** — colored radial gradient shifting blue-purple (low) to warm (high), with 4 isobar rings.
2. **Radial thermal ring** — 24h temperature data mapped to color-graded wedges (blue 60°F → teal 70°F → amber 80°F+). Radial gradient fills per wedge for depth. Glow line at outer edge.
3. **Humidity breathing ring** — teal-cyan (0,200,220) band at 0.82–1.12× maxRadius. Sinusoidal opacity modulation (base 0.20 + amplitude 0.12).
4. **Water pulse markers** — bright cyan (30,210,255) dots at irrigation event angles. Ghost markers with pulsing halos. Brightness decays with age.
5. **Ambient particle field** — 120 particles spread across full canvas. Size 0.8–2.8px, alpha 0.04–0.16. Sine-wave drift wobble, lifecycle fade-in/out.

### Center Disc

Single information surface with priority-based hover routing:

- **Water event** (highest priority): irrigation time, age in minutes, "IRRIGATION" label.
- **Humidity**: value in %RH, timestamp.
- **Temperature** (default): current °F value.

### Data Pipeline

- Fetches 24h downsampled temperature + humidity history on load.
- Fetches irrigation events.
- WebSocket for live temperature, pressure, and irrigation updates.
- Re-fetches all history every 5 minutes.

### Design Intent

Designed for gallery viewing, projection, and installation display. Applies principles from:

- **Hans Haacke**: real-time systems where the apparatus and the biological process are the work
- **Harrison Studio**: ecological feedback loops as form, life support as medium
- **Giorgia Lupi**: data can be poetic and expressive
- **CERN/NASA**: thin luminous lines, signal clarity, dark backgrounds
- **Leica**: numbers as objects of importance

---

## 9. Typography

Preferred fonts:

- Inter
- IBM Plex
- Space Mono
- Söhne

Guidelines:

- large numeric values
- generous spacing
- aligned columns

---

## 10. Color System

Primary palette:

- black background
- white text
- soft grey grid lines

Accent colors:

- cyan = water
- amber = light
- green = plant health
- red = alert

Use color sparingly.

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

## 13. Key Takeaway

The UI is not a dashboard.

It is a **window into the metabolism of a living system**.

The interface should reveal:

- rhythms
- cycles
- patterns

that would otherwise remain invisible.
