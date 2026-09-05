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
- AS7341 emits the ten raw spectral channels and `as7341_lux`. PPFD estimation was removed with the calibration pipeline; the bench method is in `LIGHTING_SYSTEM.md`
- REST API serves downsampled history (`/api/readings/<sensor>/downsampled?window=24h`) to both dashboard views
- WebSocket (`/ws/updates`) pushes live values to connected clients (poll-response). Alerts reach the browser through the 3-second poll, not a server push.

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
| NotificationService | Alert callback | On alert | ntfy webhook POST with per-sensor cooldown |
| FanService | `fan.enabled` | 30s | Temperature → PWM duty ramp |
| MeterService | `meters.enabled` | ~30 Hz | Eases the two centre-zero panel needles toward pH and EC deviation via the MCP4728 |
| ControlService | `control.enabled` and a service to drive | 2s | Reconciles the fan and meters toward desired state written by the dashboard |
| LightingScheduler | ESP32 connected | 30s | Photoperiod schedule with sunrise/sunset ramps |
| DisplayService | `display.enabled` | 5s page rotation | OLED status pages |
| CameraCaptureService | `camera.enabled` | On pump events | Captures during pump active window |

Initial V0 system uses manual parameter tuning. Future versions may implement automated feedback loops.

### The two-process split, and the control channel

`growlab` and `growlab-dashboard` are **separate systemd units** — separate
processes sharing only the SQLite file. The orchestrator owns every piece of
hardware: the GPIO, the I²C bus, the DAC, the serial link. The dashboard owns
none of it.

That is a deliberate split — a crashed web server must not take the irrigation
scheduler down with it — but it means the dashboard cannot call a method on a
running service. An override clicked in a browser has to cross a process
boundary, and the only thing both processes touch is the database.

The `control_state` table is that crossing. It holds **desired state, not a
command queue**: one row per control, overwritten in place, with NULL meaning
"follow the automatic behaviour". `ControlService` polls it and pushes changes
into the live services.

Three properties follow from desired state rather than a queue:

- **Idempotent.** Re-reading a row does nothing. A missed poll costs latency,
  not correctness.
- **Restart-safe.** Nothing accumulates while the orchestrator is down and
  nothing replays twice when it returns; an override set before a restart is
  simply still true after it.
- **Edge-triggered.** A value is applied only when it changes, so a steady row
  does not fight an override set at the bench with `growlab fan set`.

Overrides carry an expiry (`[control] override_ttl_seconds`, default one hour)
so a manual duty left on by accident lapses back to automatic instead of
holding the fan at 0% through a hot afternoon.

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

All data charts support crosshair hover: vertical guide line with colored dots on data lines and auto-positioned tooltip showing time and values at the cursor position. Dual-axis charts (AIR) show both series in the tooltip.

Time window selector: 1H / 24H / 7D. Historical charts query downsampled REST endpoints; current values update live via WebSocket. Alerts arrive on the 3-second poll.

## Art Mode (`/art`)

Full-screen generative visualization rendering 24h environmental data as a radial composition:

- **Pressure atmosphere** — colored radial gradient with isobar rings
- **Thermal ring** — temperature mapped to color-graded wedges (blue → teal → amber)
- **Humidity ring** — breathing teal-cyan band with sinusoidal opacity
- **Water pulses** — bright cyan markers at irrigation event angles
- **Ambient particles** — 120 drifting particles with lifecycle animation

Center disc shows context-sensitive detail on hover. Distance-based priority: water markers always win, then whichever ring (temperature or humidity) the mouse is physically closer to.

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
- threshold alerting with ntfy webhook notifications
- fan PWM control
- system orchestration

## Secondary Controller: ESP32

- PWM lighting control
- peripheral IO expansion

This separation keeps timing-sensitive lighting control off the Raspberry Pi.

## Web Server: FastAPI

- Dashboard routes (`/`, `/art`)
- REST API (`/api/readings/`, `/api/events`, `/api/alerts`, `/api/fan/`, `/api/meters/`, `/api/control`)
- The override endpoint (`POST /api/fan/override`) writes desired state to `control_state`; it never touches hardware directly, because this process cannot
- WebSocket (`/ws/updates`) for live values
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
