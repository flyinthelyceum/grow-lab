GROWLAB

A hybrid plant sculpture combining controlled horticulture with visible technical architecture.

This project explores how biological systems and engineered systems coexist — and makes both legible through data.

## Architecture

**Raspberry Pi** — sensor polling, data logging, irrigation scheduling, web dashboard, system orchestration.
**ESP32** — PWM lighting control and peripheral IO expansion.

Sensors: BME280 (air temp, humidity, pressure), DS18B20 (reservoir temp), Atlas EZO-pH, Atlas EZO-EC, ADS1115 + capacitive soil moisture, Pi Camera Module 3.

Actuators: GPIO relay pump, fan relay, ESP32 LED dimmer.

## Web Dashboard

FastAPI serves two views at `http://<pi-ip>:8000`:

- **Observatory** (`/`) — 5-panel layout (LIGHT, WATER, AIR, ROOT, PLANT) with D3.js charts, live WebSocket values, time window selection (1H / 24H / 7D), and per-subsystem range indicators.
- **Art Mode** (`/art`) — full-screen generative visualization. 24h environmental data rendered as a radial composition: thermal ring, humidity breathing ring, water pulse markers, pressure atmosphere, and ambient particle field. Hover reveals context-sensitive detail in the center disc.

Data stored in SQLite on the Pi. Dashboard queries downsampled history via REST API and receives live values over WebSocket.

## OLED Display

SH1106 128×64 OLED mounted on the installation. Rotates 4 pages: sensor values, system overview, irrigation schedule, sparkline trend chart.

## Documentation

- [System Architecture](docs/SYSTEM_ARCHITECTURE.md)
- [Data Architecture](docs/DATA_ARCHITECTURE.md)
- [Sensor Stack](docs/SENSOR_STACK.md)
- [Wiring & Buses](docs/WIRING_&_BUSES.md)
- [Irrigation System](docs/IRRIGATION_SYSTEM.md)
- [Lighting System](docs/LIGHTING_SYSTEM.md)
- [UI/UX Design Reference](docs/UI_UX_DESIGN_REFERENCE.md)
- [BOM](docs/BOM.md)
- [V0 Bench Prototype](docs/V0_BENCH_PROTOTYPE.md)
- [Phase 1 Walkthrough](docs/PHASE1_RASPBERRY_PI_WALKTHROUGH.md)
- [Changelog](CHANGELOG.md)