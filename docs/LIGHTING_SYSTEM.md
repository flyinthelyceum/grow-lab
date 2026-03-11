


# Lighting System

The lighting system provides controlled illumination for plant growth while serving as a visible technological element of the Living Light System installation.

The design emphasizes:

• high-quality horticultural light  
• controllable intensity  
• thermal stability  
• modular expansion  
• aesthetic integration with the sculptural installation  

The lighting subsystem is treated as both a **biological driver** and a **visible design element** within the larger artwork.

---

# Lighting Philosophy

The system prioritizes **high-efficiency white-spectrum LEDs** rather than highly complex multi-spectrum arrays.

Reasons:

• modern white LEDs already contain sufficient spectrum for plant growth  
• simpler systems are more reliable  
• color rendering remains visually pleasant in a public space  
• intensity control matters more than spectral complexity

Spectral tuning may be explored in future versions.

---

# V0 Lighting Overview

The V0 prototype uses a single high-efficiency horticultural LED strip mounted to an aluminum heatsink and powered by a dimmable driver.

Primary components:

• Samsung LM301H LED strip (GrowDaddy)  
• Mean Well PWM-120-24 LED driver  
• aluminum heatsink bar  
• ESP32-based PWM dimming control  

This configuration provides stable plant illumination while allowing software-based intensity control.

---

# LED Source

## Samsung LM301H

The LM301H is a high-efficiency horticultural LED widely used in professional grow systems.

Advantages:

• extremely high efficiency  
• excellent plant growth spectrum  
• stable thermal performance  
• long lifespan

Color temperature used in V0:

3500K or similar broad-spectrum white.

White LEDs provide a balanced spectrum appropriate for most plant stages.

---

# Electrical Architecture

The LED strip operates at:

24V DC constant voltage.

The Mean Well driver provides regulated power to the strip.

```
AC mains
   ↓
Mean Well PWM driver
   ↓
24V DC output
   ↓
LED strip
```

The driver also supports dimming control.

---

# Dimming Control

Lighting intensity is controlled through PWM dimming.

Controller:

ESP32 microcontroller.

The ESP32 generates a PWM signal which controls the Mean Well driver dimming input.

Benefits:

• software-controlled intensity  
• programmable lighting schedules  
• future automation capability  
• stable LED color output

The Raspberry Pi communicates with the ESP32 to coordinate lighting behavior.

---

# Light Intensity

Light intensity is controlled primarily through **dimming** and **distance from canopy**.

Typical target intensity ranges:

Seedlings  
100–200 PPFD

Vegetative growth  
200–400 PPFD

Flowering plants  
400–600 PPFD

Exact intensity values may be adjusted experimentally.

---

# Mounting and Thermal Management

LED strips must be mounted to aluminum heatsinks.

Purpose:

• dissipate heat  
• extend LED lifespan  
• stabilize light output

Recommended configuration:

• aluminum bar or extrusion  
• thermal adhesive or mechanical fasteners  
• free airflow around heatsink

Temperature stability significantly improves LED lifetime.

---

# Light Positioning

The light assembly is positioned above the plant canopy.

Height should remain adjustable.

Reasons:

• accommodate plant growth  
• allow intensity tuning  
• prevent light stress

In the final installation the light may be suspended on a pulley or sliding mount system.

---

# Photoperiod Control

The photoperiod defines the daily light cycle.

Typical cycles:

Vegetative plants  
16 hours light / 8 hours dark

Flowering plants  
12 hours light / 12 hours dark

The Raspberry Pi will eventually control lighting schedules automatically.

For V0, lighting may be manually scheduled.

---

# Airflow Interaction

Lighting produces heat which interacts with the airflow system.

A canopy fan provides gentle horizontal airflow to:

• prevent heat buildup  
• strengthen plant stems  
• reduce fungal risk

Lighting and airflow should always be considered together.

---

# Future Lighting Expansion

Future system versions may include:

• multiple lighting zones  
• independent bin lighting control  
• supplemental red spectrum LEDs  
• spectral experimentation  
• automated PPFD regulation

However, the V0 system intentionally remains simple to validate the core biological and technical architecture.

---

# Summary

The lighting system is one of the primary drivers of plant growth and a central visual element of the Living Light System.

The V0 implementation prioritizes:

• reliable high-efficiency white LED lighting  
• software-controlled intensity  
• stable thermal performance  
• modular expandability

This provides a strong foundation for both plant growth and future lighting experimentation.