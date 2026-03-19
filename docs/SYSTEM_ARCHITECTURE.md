# System Architecture

## Overview

GROWLAB is a modular plant growth platform composed of five primary subsystems:

1. Lighting
2. Irrigation
3. Sensors
4. Compute & Control
5. Airflow

Each subsystem is designed to operate independently but integrate through the central compute system.

The architecture prioritizes:

- modular hardware
- reliable biological support
- observable data collection
- future extensibility

Subsystem details: [LIGHTING_SYSTEM.md](LIGHTING_SYSTEM.md), [IRRIGATION_SYSTEM.md](IRRIGATION_SYSTEM.md), [SENSOR_STACK.md](SENSOR_STACK.md)

---

# Data Flow

Sensors → Raspberry Pi → SQLite → Dashboard / Art Mode

- Sensor drivers poll hardware on configurable intervals (1–15 min)
- Readings stored in SQLite with timestamps
- REST API serves downsampled history (`/api/readings/<sensor>/downsampled?window=24h`) to both dashboard views
- WebSocket (`/ws/updates`) pushes live values to connected clients (poll-response) and server-push alert events via ConnectionManager broadcast

See [DATA_ARCHITECTURE.md](DATA_ARCHITECTURE.md) for storage format, schema, and visualization strategy.

# Control Flow

Raspberry Pi → Actuators

- Pi → irrigation pump relay (GPIO17, active-low SunFounder 8-channel board)
- Pi → LED dimming control (via ESP32 serial, LightingScheduler with photoperiod ramps)
- Pi → camera capture 3s after pump activation (captures relay LED to confirm operation)
- Pi → fan PWM (GPIO18, Noctua NF-A12x25, 25kHz, temp-triggered linear ramp 70–85°F)

## Background Services

All services run as async tasks within `growlab start` and shut down cleanly on SIGINT/SIGTERM:

| Service | Condition | Interval | Purpose |
|---------|-----------|----------|---------|
| PollingService | Always | Per-sensor config | Read sensors, store to DB |
| IrrigationService | Pump available | 30s schedule check | Timed pump pulses with safety limits |
| AlertService | Always | 60s | Threshold monitoring with deduplication; fires NotificationService on transitions |
| NotificationService | Alert callback | On alert | Webhook POST + SMTP email dispatch with per-sensor cooldown |
| FanService | `fan.enabled` | 30s | Temperature → PWM duty ramp (supports manual override via API) |
| LightingScheduler | ESP32 connected | 30s | Photoperiod schedule with sunrise/sunset ramps |
| DisplayService | `display.enabled` | 5s page rotation | OLED status pages |
| CameraCaptureService | `camera.enabled` | On pump events | Captures during pump active window |

Initial V0 system uses manual parameter tuning. Future versions may implement automated feedback loops.

---

# Web Dashboard

FastAPI application serving two views:

## Observatory (`/`)

5-panel scientific dashboard showing live and historical sensor data:

| Panel | Sensors | Chart Type |
|-------|---------|------------|
| LIGHT | PWM level | StepAfter area with photoperiod band |
| WATER | Irrigation events | EKG pulse timeline |
| AIR | BME280 temp + humidity | Dual-axis CatmullRom spline |
| ROOT | EZO-pH + EZO-EC | Stacked sparklines with target bands |
| PLANT | Soil moisture + camera | D3 arc gauge + latest image |

Alert history timeline strip between banner and grid shows warning/critical events as color-coded dots on a time axis with hover tooltips.

Time window selector: 1H / 24H / 7D. Historical charts query downsampled REST endpoints; current values update live via WebSocket. Alert events push to clients in real time via ConnectionManager server-push.

## Art Mode (`/art`)

Full-screen generative visualization rendering 24h environmental data as a radial composition:

- **Pressure atmosphere** — colored radial gradient with isobar rings
- **Thermal ring** — temperature mapped to color-graded wedges (blue → teal → amber)
- **Humidity ring** — breathing teal-cyan band with sinusoidal opacity
- **Water pulses** — bright cyan markers at irrigation event angles
- **Ambient particles** — 120 drifting particles with lifecycle animation

Center disc shows context-sensitive detail on hover (priority: water > humidity > temperature).

Design references: [UI_UX_DESIGN_REFERENCE.md](UI_UX_DESIGN_REFERENCE.md)

## Embedded OLED Display

SH1106 128×64 OLED on I²C 0x3C. Rotates through 4 pages every 5 seconds:

1. Current sensor values (Fahrenheit, human labels)
2. System overview (uptime, subsystem status)
3. Irrigation schedule with last pump event
4. Sparkline trend chart

---

# Compute Architecture

## Primary Controller: Raspberry Pi

- sensor polling
- data logging
- dashboard interface
- irrigation scheduling
- threshold alerting with webhook/email notifications
- fan PWM control
- system orchestration

## Secondary Controller: ESP32

- PWM lighting control
- peripheral IO expansion

This separation keeps timing-sensitive lighting control off the Raspberry Pi.

## Web Server: FastAPI

- Dashboard routes (`/`, `/art`)
- REST API (`/api/readings/`, `/api/events`, `/api/alerts`, `/api/fan/`)
- WebSocket (`/ws/updates`) with ConnectionManager for server-push broadcasts
- Static file serving (D3.js charts, art mode modules, CSS)

See [WIRING_&_BUSES.md](WIRING_&_BUSES.md) for pin assignments, bus layout, and power domains.

---

# Modularity

Each subsystem can be replaced or upgraded independently:

- Lighting
- Irrigation
- Sensors
- Compute
- Structural frame

This modular design allows rapid iteration without redesigning the entire system.
