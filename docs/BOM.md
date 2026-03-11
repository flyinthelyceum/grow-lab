# Parts BOM

This document tracks hardware used in the Living Light System. The initial build targets the V0 Bench Prototype.

For detailed specifications see: [LIGHTING_SYSTEM.md](LIGHTING_SYSTEM.md), [IRRIGATION_SYSTEM.md](IRRIGATION_SYSTEM.md), [SENSOR_STACK.md](SENSOR_STACK.md), [WIRING_&_BUSES.md](WIRING_&_BUSES.md)

---

# Lighting System

LED Strip

Samsung LM301H based grow strip  
400mm Sun Board strip  
96 LEDs

Driver

Meanwell PWM-120-24 LED Driver  
24V  
120W  
5A max output

Mounting

Aluminum bar heatsink  
thermal adhesive or screws

Electrical

WAGO connectors  
18–20 AWG wire  
AC power cord
ESP32 PWM dimming control

---

# Compute System

Primary Controller

Raspberry Pi (Model 3 / 4 / 5 acceptable)

Accessories

MicroSD card  
Pi power supply  
WiFi network access

Secondary Controller

ESP32 development board

Used for

PWM dimming  
IO expansion

---

# Sensor Stack

Temperature / Humidity

BME280 or SHT31 sensor module

Reservoir Temperature

DS18B20 waterproof probe

Electrical Conductivity (EC)

Atlas Scientific EC probe + interface  
or equivalent hydroponic EC sensor

pH

Atlas Scientific pH probe + interface  
or equivalent hydroponic pH sensor

Media Moisture

Adafruit STEMMA Soil Sensor (Product 4026)
I2C interface (address 0x36)
capacitive, no corrosion

Alternative: DFRobot SEN0308 (IP65 waterproof) + ADS1115 ADC

Calibration

pH calibration solutions
EC calibration solution

---

# Camera System

Camera

Raspberry Pi Camera Module 3 (Standard or Wide)
Sony IMX708 sensor
11.9 MP
CSI ribbon cable interface

Accessories

Extended ribbon cable (300mm or 500mm)
Fixed mount or small tripod for consistent framing

---

# Display (Optional)

SSD1306 OLED module
128x64 pixels
I2C interface (address 0x3C or 0x3D)
physical status display on installation

---

# Irrigation System

Reservoir

5 gallon bucket or plastic container

Pump

Small submersible water pump  
(200–400 L/hr recommended)

Tubing

1/4" drip irrigation tubing

Emitters

Drip emitters or drip stakes

Drainage

Plant tray or catch basin

Control

Relay module for pump switching

---

# Plant Media

Container

3–5 gallon nursery pot

Growing Media

Coco coir  
Perlite

Optional

mesh screen for pot drainage holes

---

# Airflow

Fan

Small circulation fan  
USB or 12V powered

Purpose

prevent stagnant canopy air

---

# Electrical Safety

GFCI outlet recommended

Drip loops on all cables

Cable management for separating wet systems and electrical components

---

# Future Hardware (Not Required for V0)

Light measurement

PAR meter

Environmental control

Humidity sensor network  
CO₂ sensor

Reservoir automation

Dosing pumps  
Level sensors

Structural

Custom aluminum frame  
Integrated cable routing