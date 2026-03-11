# V0 Bench Prototype

## Objective

Build a functional test platform for the living plant system.

The goal is to validate core subsystems before designing the sculptural installation.

## Subsystems

V0 includes: LED lighting, dimmable driver, Raspberry Pi control, ESP32 PWM, drip irrigation, reservoir, airflow fan, environmental sensors, soil moisture sensor, Pi camera, and data logging.

For component details see: [LIGHTING_SYSTEM.md](LIGHTING_SYSTEM.md), [IRRIGATION_SYSTEM.md](IRRIGATION_SYSTEM.md), [SENSOR_STACK.md](SENSOR_STACK.md), [BOM.md](BOM.md)

## Success Criteria

V0 is successful if:

• light system runs reliably  
• irrigation runs without leaks  
• sensors log stable data  
• plant grows normally for multiple weeks

---

## Deployment Runbook

This runbook outlines the step‑by‑step process for commissioning the V0 bench prototype. The goal is to bring each subsystem online safely and validate that the integrated system operates reliably before introducing a plant.

### Phase 1 — Bench Layout (Dry Setup)

Separate the workspace into zones:

• **Electrical zone:** Raspberry Pi, ESP32, driver, relay, breadboard  
• **Lighting zone:** LED strip mounted to heatsink  
• **Wet zone:** reservoir bucket, pump, tubing, pot, tray  
• **Sensor staging zone:** probes and environmental sensors

Ensure the LED driver and all compute hardware are mounted **above any water path** and that all cables include **drip loops**.

---

### Phase 2 — Lighting Bring‑Up

1. Mount the LED strip securely to the aluminum heatsink.
2. Wire the LED strip to the Meanwell PWM driver output.
3. Connect AC input to the driver using safe connectors and strain relief.
4. Power on and confirm:
   - LEDs illuminate
   - no flicker or overheating
   - heatsink remains within safe temperature

5. Test dimming via ESP32 PWM control.

Goal: stable light output with smooth dimming.

---

### Phase 3 — Raspberry Pi Setup

1. Boot Raspberry Pi and connect to network.
2. Enable required interfaces:
   - I²C
   - 1‑Wire (for DS18B20)
3. Install required software packages.
4. Confirm SSH access.
5. Create basic logging scripts for sensor data.

Goal: Pi operates as the central data and control node.

---

### Phase 4 — Sensor Commissioning

Bring sensors online one at a time.

1. Connect **BME280** (I²C).
2. Verify temperature and humidity readings.
3. Connect **DS18B20** and confirm reservoir temperature readings.
4. Connect **Atlas EZO‑pH** circuit via I²C.
5. Connect **Atlas EZO‑EC** circuit via I²C.

Perform calibration procedures:

• pH probe calibration (4 / 7 / 10 solutions)  
• EC calibration using conductivity reference solution

Goal: stable, repeatable sensor readings logged by the Pi.

---

### Phase 5 — Irrigation System Test (Water Only)

1. Fill reservoir with plain water.
2. Install pump and connect tubing to drip emitter.
3. Place pot filled with coco/perlite in drain tray.
4. Trigger pump manually.

Verify:

• emitter flow rate  
• even media wetting  
• clean drainage  
• no leaks  
• pump shuts off cleanly

Next, connect pump to relay and test Pi‑controlled pump pulses.

---

### Phase 6 — Integrated System Test

Install sensors in their operational locations:

• BME280 near canopy but out of direct light  
• DS18B20 submerged in reservoir  
• pH and EC probes mounted in reservoir using probe holder

Run the full system with **no plant** for 24 hours.

System conditions:

• lighting schedule active  
• fan running continuously  
• irrigation pulses scheduled  
• sensors logging

Observe for:

• leaks  
• sensor drift  
• electrical noise  
• overheating

---

### Phase 7 — Nutrient Solution

Replace plain water with a mild nutrient solution.

Initial targets:

• pH ≈ 5.8–6.2  
• EC appropriate for plant type

Allow solution to circulate and confirm stable readings.

---

### Phase 8 — Plant Introduction

Add the first plant to the pot.

Set conservative initial conditions:

• moderate light intensity  
• fan airflow across canopy  
• limited irrigation pulses

Observe plant response over several days before making adjustments.

---

### Phase 9 — First Week Stabilization

Monitor daily:

• leaf posture  
• moisture levels  
• runoff behavior  
• pH drift  
• EC drift  
• environmental temperature and humidity

Adjust **only one variable at a time** (light intensity, watering frequency, or nutrient strength).

Record baseline system settings once stable.