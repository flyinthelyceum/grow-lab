

# Wiring & Buses

This document defines the electrical wiring strategy and communication bus layout for the V0 bench prototype of GROWLAB.

The goal is to make the hardware:

• legible  
• debuggable  
• electrically stable  
• safe around water  
• expandable into V1  

The system separates **power distribution**, **sensor communication**, and **actuator control** into distinct layers.

---

# System Overview

The V0 bench prototype contains five electrical subsystems:

1. AC mains power  
2. LED lighting power  
3. Low‑voltage logic power  
4. Sensor communication buses  
5. Pump and actuator switching  

High level structure:

AC Mains  
→ LED Driver  
→ Raspberry Pi Power Supply  
→ Pump Power Supply  
→ 12V fan rail (the fan's own 12V adapter)  

Raspberry Pi  
→ I²C Bus (BME280 + Atlas sensors)  
→ 1‑Wire Bus (DS18B20 temperature probe)  
→ GPIO Pump Relay  
→ GPIO18 hardware PWM → canopy fan  
→ Serial / WiFi communication with ESP32  

ESP32  
→ PWM dimming signal for LED driver

---

# Power Domains

The system has four distinct power domains: mains, 24V lighting, 12V fan, and low-voltage logic.

## 1. AC Mains

Used for:

• LED driver input  
• Raspberry Pi power supply  
• pump power supply  
• 12V fan adapter  

Guidelines:

• keep AC wiring physically separated from sensor wiring  
• use grounded outlets  
• include drip loops where wires enter cabinet spaces  
• mount AC components above potential water exposure

---

## 2. 24V Lighting Power

Lighting is powered by the Mean Well LED driver.

Power path:

AC → Mean Well PWM‑120‑24 → LED grow strips

This power path should only supply the LED strips.

Do not share this supply with sensors or logic.

---

## 3. Low Voltage Logic

Low voltage logic powers:

• Raspberry Pi  
• ESP32  
• sensor circuits  
• relay logic side

Typical voltages:

5V – Raspberry Pi / relay board  
3.3V – sensors / ESP32 logic

Keep these wires separate from pump and lighting wiring.

---

## 4. 12V Fan Rail

The Noctua canopy fan is a 12V, 4-pin PWM part (~0.06A).

Power path:

12V wall adapter → fan +12V / GND

Guidelines:

• fan GND must share a common ground with the Pi so the PWM signal has a reference  
• the fan's PWM input is a 3.3V-tolerant logic line — do not put 12V on it  

---

# Raspberry Pi Role

The Raspberry Pi acts as the **system brain**.

Responsibilities:

• polling sensors  
• logging environmental data  
• controlling irrigation  
• scheduling lighting states  
• communicating with ESP32

The Pi should be mounted in a dry electronics area.

---

# ESP32 Role

The ESP32 handles real‑time PWM lighting control.

Responsibilities:

• LED dimming control  
• future lighting automation  
• expansion IO if needed

This separation keeps timing‑sensitive lighting control off the Raspberry Pi.

---

# I²C Bus

The I²C bus connects environmental sensors and the status display.

Devices on the bus:

| Device | I²C address | Address selection | Function |
|---|---|---|---|
| BME280 | 0x76 | SDO→GND. SDO→VCC for 0x77 | Air temperature + humidity + pressure |
| SSD1306 OLED (128x64) | 0x3C | SA0→GND. SA0→VCC for 0x3D | Physical status display |
| Atlas EZO‑pH (Phase 3) | 0x63 (99 decimal) | Set via `I2C,99` during the UART→I²C mode switch | Reservoir pH |
| Atlas EZO‑EC (Phase 3) | 0x64 (100 decimal) | Set via `I2C,100` during the UART→I²C mode switch | Reservoir EC |
| AS7341 | 0x39 | Fixed (not configurable) | Canopy spectral light |
| ADS1115 + DFRobot SEN0308 | 0x48 | ADDR→GND. ADDR→VDD/SDA/SCL for 0x49–0x4B | Media moisture (analog input) |

No address conflicts in this configuration.

Raspberry Pi pins:

SDA → GPIO 2 (Pin 3)
SCL → GPIO 3 (Pin 5)
3.3V → Pin 1
GND → Pin 6

Topology:

Pi SDA
→ BME280
→ OLED
→ EZO‑pH
→ EZO‑EC
→ ADS1115 (SEN0308)
→ AS7341

Pi SCL
→ BME280
→ OLED
→ EZO‑pH
→ EZO‑EC
→ ADS1115 (SEN0308)
→ AS7341

All devices share a common ground.

Notes:

• keep I²C wires short
• route away from pump power wires
• Atlas EZO boards ship in UART mode — must be switched to I²C mode before use

This table is the full I²C address map. For what each sensor measures and how it is installed: [SENSOR_STACK.md](SENSOR_STACK.md)

---

# 1‑Wire Bus

Reservoir temperature uses a DS18B20 sensor.

Pin mapping:

Data → GPIO 4 (Pin 7)  
3.3V → Pin 1  
Ground → Pin 6

A **4.7kΩ pull‑up resistor** is required between:

GPIO4 and 3.3V.

Topology:

Pi GPIO4 → DS18B20 Data  
Pi 3.3V → DS18B20 VCC  
Pi GND → DS18B20 GND

---

# Atlas Sensor Wiring

Atlas EZO circuits must be configured for **I²C mode** before connecting to the bus.

## UART → I²C Mode Switching (Bring-Up Ritual)

EZO boards ship in UART mode by default. They will not appear on the I²C bus until switched.

Two methods:

**Command-based (via UART first):**
Connect to the EZO board via UART (TX/RX), then send: `I2C,<address>` where address is in decimal (e.g., `I2C,99` for pH, `I2C,100` for EC). The board reboots into I²C mode at that address.

**Manual hardware method:**
Short the designated pins during power-up to force I²C mode and restore the default address. See Atlas Scientific EZO datasheet for the specific pin procedure per board.

**Troubleshooting rule:** If a device is not detected on the I²C bus, verify protocol mode first, then verify address.

## Physical Wiring

Each circuit requires:

• VCC
• GND
• SDA
• SCL

Mount the EZO boards in the dry electronics compartment.

Route probe cables neatly to the reservoir.

Important:

• probes should not touch container walls
• probes should not sit directly in pump turbulence

---

# Pump Relay Wiring

Irrigation pump control uses a relay module.

Recommended Pi GPIO:

GPIO17 (Pin 11)

Logic wiring:

Pi GPIO17 → Relay IN  
5V → Relay VCC  
GND → Relay GND

Power wiring:

Pump power is routed through the relay switch.

Control path:

Pi GPIO17 → Relay → Pump Power

Ensure the relay is rated for the pump voltage.

---

# Pi ↔ ESP32 Communication

The Raspberry Pi communicates with the ESP32 via **serial UART over USB**.

Configuration:

• Baud rate: 115200
• Framing: newline-delimited text commands (`\n` terminated)
• Physical: USB cable connecting Pi to ESP32 dev board
• Pi device: `/dev/ttyACM0` (USB-Serial/JTAG on Freenove ESP32-S3)

V0 command set:

```
LIGHT <0..255>    Set LED PWM duty cycle (0 = off, 255 = full)
PUMP <0|1>        Pump relay state (0 = off, 1 = on)
STATUS            Request current state (ESP32 responds with PWM level)
```

This protocol is intentionally minimal. The key property is auditability — every command can be tested with a serial terminal.

---

# LED Dimming Wiring

The Mean Well driver supports PWM dimming.

The ESP32 provides the PWM signal.

Suggested ESP32 pin:

GPIO18

Signal path:

ESP32 PWM → Mean Well dimming input

Guidelines:

• verify dimming polarity in the driver datasheet  
• test dimming at low power first

---

# Fan PWM Wiring

The 12V canopy fan (Noctua NF-A12x25 PWM, 4-pin) is speed-controlled by **25 kHz hardware PWM from the Pi** — not a relay. This is what `FanService` / `pi/drivers/fan_pwm.py` drive (`[fan] gpio_pin = 18`, `frequency = 25000`).

Recommended Pi GPIO:

GPIO18 (Pin 12, hardware PWM0)

Fan connector (4-pin, Intel PWM pinout):

Pin 1 — GND → common ground
Pin 2 — +12V → 12V fan rail
Pin 3 — TACH → optional, any free Pi GPIO with pull-up (RPM sense)
Pin 4 — PWM → Pi GPIO18

Control path:

Pi GPIO18 (25 kHz, 0–100 % duty) → fan PWM input

The fan accepts a 3.3V PWM signal directly; no level shifter or transistor is needed. Duty comes from the gust field in `config.toml` (`day_start_hour` / `day_end_hour` / `night_factor` / `calm_threshold`) — the fan is for canopy strength, not cooling, so it takes no temperature input — or from a manual override via `/api/fan/`.

**V0 note:** the bench prototype ran this fan always-on through a relay on GPIO6. V1 retires that relay; GPIO6 is free.

## 5V Pi Fan

The small Pi cooling fan runs always-on from the Pi 5V/GND pins. No relay or software control needed.

---

# Grounding Strategy

pH and EC probes are sensitive to electrical noise.

Guidelines:

• keep sensor cables away from AC wiring  
• keep probe wires away from LED driver input wires  
• avoid running sensor wires parallel to pump wires

Noise in pH readings is often caused by poor wiring layout.

---

# Physical Wire Routing

Organize wires into three groups.

Power:

• AC mains  
• pump power  
• LED driver input

Logic:

• I²C wires  
• 1‑Wire sensor line  
• relay control wire

Sensor leads:

• pH probe cable  
• EC probe cable  
• reservoir temperature probe

Do not bundle these groups together.

---

# Recommended Pin Map

All Pi GPIO connections route through the RSP-GPIO-8 breakout board (screw terminals).

## Raspberry Pi

| Pin | GPIO | Function | Device |
|-----|------|----------|--------|
| 1 | — | 3.3V | DS18B20 VCC, BME280 VCC, OLED VCC, ADS1115 VDD |
| 2 | — | 5V | Pump relay VCC |
| 3 | GPIO2 | I²C SDA | BME280 + OLED (shared bus) |
| 5 | GPIO3 | I²C SCL | BME280 + OLED (shared bus) |
| 6 | — | GND | Common ground (all devices) |
| 7 | GPIO4 | 1-Wire Data | DS18B20 (+ 4.7kΩ pull-up to 3.3V) |
| 11 | GPIO17 | Relay IN | Pump relay signal |
| 12 | GPIO18 | PWM0 | Noctua fan PWM (25 kHz) |
| CSI | — | Ribbon cable | Pi Camera Module 3 |
| USB-A | — | Serial | ESP32-S3 (/dev/ttyACM0) |

## ESP32

GPIO18 → LED PWM dimming
GPIO48 → Onboard RGB heartbeat LED

---

# Bring‑Up Sequence

Recommended order for first system power‑up:

1. power Raspberry Pi  
2. verify I²C bus with BME280  
3. add DS18B20 sensor  
4. connect Atlas pH circuit  
5. connect Atlas EC circuit  
6. power ESP32 and test PWM output  
7. connect LED driver dimming  
8. add pump relay  
9. test irrigation cycle  
10. bring up the 12V rail and sweep the fan PWM 0 → 100 %

This staged process makes debugging much easier.

---

# Summary

The wiring architecture is designed to keep power, sensing, and control clearly separated.

This structure makes the system:

• safer  
• easier to debug  
• easier to expand

It also ensures sensitive probes and sensors remain electrically stable while the rest of the system operates.
