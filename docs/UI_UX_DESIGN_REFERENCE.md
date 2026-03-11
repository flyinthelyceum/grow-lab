
# UI_UX_DESIGN_REFERENCE.md
Living Light — Data Visualization as Embodied Art

---

## 1. Purpose

The **Living Light system interface** is not a monitoring dashboard.

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

### Refik Anadol — Data as Living System

Refik Anadol treats data as **dynamic material**.

Lessons:

- data should flow
- patterns should breathe
- information should feel alive

Use environmental data to create visual rhythms.

Examples:

- humidity oscillations
- irrigation pulses
- light cycles

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

## 4. Dashboard Architecture

The system web interface is structured as a **Living Observatory**.

Primary panels:

- LIGHT
- WATER
- AIR
- ROOT
- PLANT

Each panel displays:

- current state
- 24h trend
- event pulses

Example layout:

-------------------------------------
Living Light Observatory
-------------------------------------

LIGHT  
PPFD        620  
Photoperiod 16h  

[ 24h light curve ]

-------------------------------------

WATER  
Last Irrigation: 32 min ago  
Reservoir Level: 78%  

[ irrigation pulse timeline ]

-------------------------------------

ROOT  
pH  6.10  
EC  1.82  

[ pH drift curve ]  
[ EC drift curve ]

-------------------------------------

AIR  
Temp 22.8C  
RH   48%  

[ humidity waveform ]

-------------------------------------

PLANT  
Latest Image  
Growth Timelapse

---

## 5. Embedded OLED Interface

Small OLED display embedded in installation.

Purpose:

make the system legible to observers

Hardware recommendation:

SSD1306 OLED  
128x64  
I2C

Screen Example:

LIVING LIGHT

PH     6.12  
EC     1.78  
TEMP   22.9C  
RH     47%

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

Backend:

- Python
- FastAPI
- SQLite

Frontend:

- D3.js
- Chart.js
- optional p5.js for generative visuals

Live updates:

- WebSockets

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

Include an **artistic visualization mode**.

Examples:

- light cycle rendered as solar arcs
- irrigation events as pulses
- humidity breathing waveforms
- pH drift as tidal motion

Designed for:

- gallery viewing
- projection
- installation display

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

Living Light Observatory

Alternatives:

- Plant System Monitor
- Living Garden Instrument
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
