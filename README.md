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

- **Observatory** (`/`) — 5-panel layout (LIGHT, WATER, AIR, ROOT, PLANT) with D3.js charts backed by downsampled history, live WebSocket values, time window selection (1H / 24H / 7D), and per-subsystem range indicators.
- **Art Mode** (`/art`) — full-screen generative visualization. 24h environmental data rendered as a radial composition: thermal ring, humidity breathing ring, water pulse markers, pressure atmosphere, and ambient particle field. Hover reveals context-sensitive detail in the center disc.

Data stored in SQLite on the Pi. Observatory and art mode both query downsampled history via REST API and receive live values over WebSocket.

## OLED Display

SH1106 128×64 OLED mounted on the installation. Rotates 4 pages: sensor values, system overview, irrigation schedule, sparkline trend chart.

## Pi Ops

Launch the dashboard on the Pi:

```bash
cd ~/grow-lab
source .venv/bin/activate
growlab dashboard --host 0.0.0.0 --port 8000
```

Seed demo-friendly dashboard data when hardware is still in transit:

```bash
cd ~/grow-lab
source .venv/bin/activate
growlab db seed-demo --hours 24
```

Install the included `systemd` service for persistent dashboard hosting:

```bash
sudo cp deploy/systemd/growlab-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now growlab-dashboard
sudo systemctl status growlab-dashboard
```

## Working Away From Hardware

Use the tracked demo profile for local dashboard iteration without touching the Pi database:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
growlab --config config.demo.toml db seed-demo --hours 24
growlab --config config.demo.toml dashboard --host 127.0.0.1 --port 8000
```

The demo profile writes to `./.demo-data/` and keeps hardware polling/display disabled.

Good local-only tasks:

- observatory and art-mode UI/UX refinement
- seeded-data review loops and screenshot critique
- docs, tests, and CLI/config cleanup
- browser coverage once Playwright is installed

Still Pi-dependent:

- live sensor validation
- service and camera-path debugging
- hardware bus discovery and ESP32 runtime verification

Browser tests are optional and require both `playwright` and `pytest-playwright`:

```bash
pip install pytest-playwright playwright
playwright install chromium
pytest tests/browser/test_browser_dashboard.py -v
```

## Documentation

- [System Architecture](docs/SYSTEM_ARCHITECTURE.md)
- [Data Architecture](docs/DATA_ARCHITECTURE.md)
- [Sensor Stack](docs/SENSOR_STACK.md)
- [AS7341 Calibration Protocol](docs/AS7341_CALIBRATION_PROTOCOL.md)
- [Wiring & Buses](docs/WIRING_&_BUSES.md)
- [Irrigation System](docs/IRRIGATION_SYSTEM.md)
- [Lighting System](docs/LIGHTING_SYSTEM.md)
- [UI/UX Design Reference](docs/UI_UX_DESIGN_REFERENCE.md)
- [BOM](docs/BOM.md)
- [V0 Bench Prototype](docs/V0_BENCH_PROTOTYPE.md)
- [Phase 1 Walkthrough](docs/PHASE1_RASPBERRY_PI_WALKTHROUGH.md)
- [Changelog](CHANGELOG.md)
