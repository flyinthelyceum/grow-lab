# Irrigation System

The irrigation system delivers water and nutrients from a central reservoir to the plant media in controlled pulses.

In the Living Light System, irrigation is treated as both a **biological support system** and a **controlled mechanical subsystem** that can be monitored and automated.

The design prioritizes:

• reliability  
• simplicity  
• repeatable watering events  
• compatibility with sensor instrumentation  
• modular expansion for multiple plant bins

---

# Irrigation Philosophy

The V0 system uses a **media-based drip irrigation approach** rather than a fully recirculating hydroponic system.

Reasons:

• easier to stabilize for early experiments  
• tolerant of environmental variability  
• closer to traditional horticulture practices  
• simpler failure modes  

The goal of V0 is to validate plant growth, sensor stability, and system reliability before exploring more complex irrigation strategies.

---

# System Architecture

The irrigation system is composed of five primary elements:

1. Reservoir
2. Pump
3. Distribution tubing
4. Emitters
5. Drainage

System flow:

```
Reservoir
   ↓
Submersible Pump
   ↓
Distribution Tubing
   ↓
Drip Emitter
   ↓
Plant Media
   ↓
Drain Tray / Runoff
```

Each irrigation event moves water from the reservoir into the plant container, saturating the media before draining excess solution.

---

# Reservoir

The reservoir stores the nutrient solution that feeds the irrigation system.

Recommended configuration:

• 5 gallon HDPE bucket with lid  
• placed below plant containers  
• protected from light to prevent algae growth  

The reservoir also houses:

• pH probe  
• EC probe  
• reservoir temperature probe  

These sensors monitor the chemistry and temperature of the nutrient solution.

---

# Pump

A small **submersible pump** moves water from the reservoir to the plant emitter.

Typical pump specification:

Flow rate: 200–400 L/hr

Reasons for moderate flow rate:

• sufficient pressure for drip emitters  
• prevents excessive turbulence  
• compatible with small reservoirs

Pump operation is controlled via a **relay module connected to the Raspberry Pi**.

This allows irrigation pulses to be scheduled programmatically.

---

# Distribution Tubing

Water is transported through **¼ inch irrigation tubing**.

Typical configuration:

Reservoir → pump outlet → tubing → emitter.

Future versions may introduce:

• manifolds  
• multi-bin distribution  
• flow balancing valves

For V0, a single emitter line is sufficient.

---

# Emitters

Emitters regulate the rate at which water enters the plant media.

Recommended type:

1 GPH drip emitter  
or  
adjustable drip stake.

Purpose:

• prevent media disturbance  
• ensure gradual infiltration  
• reduce channeling in coco/perlite

The emitter should be positioned near the plant root zone.

---

# Plant Media Interaction

The plant container contains a mix of:

• coco coir  
• perlite

This medium provides:

• good drainage  
• high oxygen availability  
• stable moisture retention

Water should soak through the media and exit via drainage holes.

---

# Drainage

Drainage is critical to prevent root oxygen deprivation.

V0 configuration:

• nursery pot placed in plant tray  
• runoff collected in tray

Future versions may return runoff to the reservoir.

However, for early testing it is acceptable to discard runoff to reduce contamination risk.

---

# Irrigation Control

The pump is controlled by the Raspberry Pi through a relay module.

Control pattern:

```
Pi GPIO
   ↓
Relay
   ↓
Pump power
```

Irrigation events are defined by **pump runtime duration**.

Example event:

Pump ON → 10 seconds → Pump OFF

This allows repeatable irrigation pulses.

---

# Pump Controller Configuration

The pump backend is selected explicitly via `config.toml`:

```toml
[irrigation]
pump_controller = "gpio"   # "gpio" or "esp32"
relay_gpio = 17
```

**V0:** `pump_controller = "gpio"` (default). The Pi drives the relay directly on GPIO17. No ESP32 involvement in pump control.

**Future:** `pump_controller = "esp32"` routes pump commands through the ESP32 serial link. This is reserved for configurations where the relay is wired to the ESP32 rather than the Pi.

The ESP32 remains connected for LED PWM lighting control but does not handle pump commands in V0.

If RPi.GPIO is unavailable (missing package, permissions, or running off-Pi), the `growlab pump` commands will report the specific error rather than silently falling back to a different backend.

---

# Irrigation Scheduling

Initial V0 schedule should be conservative.

Example starting schedule:

2–4 irrigation pulses per day.

Adjustments should be based on:

• media moisture  
• plant response  
• environmental conditions

Overwatering is more damaging than slight dryness in early tests.

---

# Failure Modes

Common irrigation risks include:

• clogged emitters  
• pump failure  
• tubing leaks  
• reservoir depletion

Mitigation strategies:

• visual inspection during early operation  
• secure tubing connections  
• accessible pump placement  
• reservoir volume monitoring

Future versions may include automatic reservoir level sensing.

---

# Future Expansion

Later versions of the system may incorporate:

• multi-bin irrigation manifolds  
• independent watering zones  
• automated nutrient dosing  
• reservoir recirculation loops  
• runoff recovery systems

The V0 irrigation system intentionally remains simple to validate plant growth and system stability.

---

# Summary

The irrigation system provides controlled delivery of water and nutrients to the plant media.

The V0 implementation prioritizes:

• simple and reliable drip irrigation  
• centralized reservoir chemistry monitoring  
• Raspberry Pi controlled irrigation events  
• easy expansion to multi-bin systems

This architecture provides a robust foundation for future experimentation and automation.
