# System Architecture

## Overview

The Living Light System is a modular plant growth platform composed of five primary subsystems:

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

Sensors → Raspberry Pi → Data Logging → Visualization

See [DATA_ARCHITECTURE.md](DATA_ARCHITECTURE.md) for storage format, schema, and visualization strategy.

# Control Flow

Raspberry Pi → Actuators

- Pi → irrigation pump relay
- Pi → LED dimming control (via ESP32)

Initial V0 system uses manual parameter tuning. Future versions may implement automated feedback loops.

---

# Compute Architecture

## Primary Controller: Raspberry Pi

- sensor polling
- data logging
- dashboard interface
- irrigation scheduling
- system orchestration

## Secondary Controller: ESP32

- PWM lighting control
- peripheral IO expansion

This separation keeps timing-sensitive lighting control off the Raspberry Pi.

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
