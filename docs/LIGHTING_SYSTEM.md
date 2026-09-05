


# Lighting System

The lighting system provides controlled illumination for plant growth while serving as a visible technological element of the GROWLAB installation.

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

For installed GrowLab nodes, PPFD can be estimated from the fixed-position
AS7341 using a fixture-specific bench commissioning — see **AS7341 PPFD
Commissioning** below. It is intended for repeatable operation and education,
not as a universal research instrument.

---

# AS7341 PPFD Commissioning

The upward-facing AS7341 reports raw spectral counts, not PPFD. Turning counts into a µmol/m²/s figure takes a **fixture-specific bench commissioning** against a borrowed PAR meter. The goal is a consistent, repeatable, inspectable estimate for a school demo — not a laboratory instrument. "Good enough" is: the estimate tracks dimmer changes smoothly, repeats close to itself at the same setup, and holds RMSE under ~20 µmol/m²/s with median absolute error under ~15. Commissioning targets, not certification limits.

## Fix the geometry first

The housing, diffuser and shroud are part of the calibration condition.

• mount the AS7341 in its final installed position, upward-facing  
• fit the final diffuser and shroud, and leave them fitted afterwards  
• fixed standoff height and a repeatable canopy reference plane  
• no loose or rotating sensor board, no cable strain twisting it  
• do not commission on a breadboard and then run it inside a housing  

## Hold the sensor settings fixed

Set the AS7341 gain, integration time and `astep` before the first capture and do not touch them again — not mid-session, not afterwards. Changing them invalidates the result as surely as moving the sensor.

## PAR meter placement and capture grid

Put the PAR meter head at the canopy reference plane and keep it in that same plane for every point. Warm the fixture 2–3 minutes before the first capture, let the light settle briefly at each step, and use a dark cloth to cut stray room light.

A practical bench grid, not a lab marathon:

• dimmer levels: 20, 35, 50, 65, 80, 100 %  
• three fixture-to-canopy distances  
• centre position, optionally one or two lateral offsets  
• **18–30 points total**, averaging ~5 sensor reads per point  

Record per point: dimmer %, distance, lateral offset, gain/integration, the PAR meter reading, and the ten AS7341 channels.

## Hold-out split

Reserve **4–6 points as held-out validation** and fit on the rest. Judge the fit on the held-out rows — RMSE, MAE, median absolute error, R², residual range. Reject a fit with wild low-light residuals or a non-monotonic response to dimmer level even if one headline metric looks good. If a single point looks obviously wrong, retake it rather than trusting luck.

## Recommission when anything optical changes

Fixture model or replacement, fixture height range or installed geometry, diffuser, shroud, sensor placement or orientation, or the AS7341 gain and integration settings. Also after visible fixture aging, or a long downtime with unknown mechanical changes.

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

# Summary

The lighting system is one of the primary drivers of plant growth and a central visual element of GROWLAB.

The V0 implementation prioritizes:

• reliable high-efficiency white LED lighting  
• software-controlled intensity  
• stable thermal performance  
• modular expandability

This provides a strong foundation for both plant growth and future lighting experimentation.
