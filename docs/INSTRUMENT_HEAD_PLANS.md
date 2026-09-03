# Instrument Head Plans — Rev A (2026-09-03)

Fabrication schedules for the mast's instrument head. Drawings:
`https://claude.ai/code/artifact/` (see CHANGELOG for the current link). **These tables are the
authority; the drawings illustrate them.**

- Units: inches unless marked mm. Origin: panel bottom-left, X right, Y up.
- Material: 1/4 in **cast** acrylic throughout (not extruded — it crazes at solvent joints).
- Meters: **Simpson Wide-Vue 3-1/2", Model 1327**, two.
- Head external: **9.50 W x 12.00 H x 3.50 D**. Clear inside: 3.00.
- Height stack: head bottom at 46 in (fixture level), top at **58 in**; panel centre **52 in**.

## Face — hole schedule

| ID | X | Y | Cut | For |
|---|---|---|---|---|
| M1 | 2.750 | 9.500 | Ø 2.79 thru | Simpson 1327 — pH |
| M1a–d | 1.625 / 3.875 | 8.375 / 10.625 | Ø 0.125 thru ×4 | M1 #4-40 studs, 2.25 sq |
| M2 | 6.750 | 9.500 | Ø 2.79 thru | Simpson 1327 — moisture |
| M2a–d | 5.625 / 7.875 | 8.375 / 10.625 | Ø 0.125 thru ×4 | M2 #4-40 studs, 2.25 sq |
| W | 4.750 | 5.360 | 6.30 × 3.78 rect, r 0.02 | Inky Impression 7.3" active area (160 × 96 mm) |
| J | 1.625 | 1.625 | Ø 1.00 thru | NOS Dialco 1" jewel pilot |
| A | 2.750 | 1.625 | Ø 0.50 thru | VCC 1092 amber — tend-me |
| K1 | 6.750 | 1.625 | Ø 0.375 thru | Pot, 3/8-32 bushing, D-shaft |
| K2 | 7.875 | 1.625 | Ø 0.375 thru | Pot, 3/8-32 bushing, D-shaft |
| F1–4 | 0.375 / 9.125 | 0.375 / 11.625 | Ø 0.135 c'sunk ×4 | M3 flat-head — removable face |

Grid logic: jewel and outer knob sit on the meters' outer mounting-hole columns (1.625, 7.875);
indicator and inner knob on the meter centres (2.750, 6.750). Nothing is placed by eye.

**Window W — cut a test first.** 6.30 × 3.78 equals the stated active area, but the screen is
not centred on its 174.2 × 123.2 board and edge tolerance is unpublished. Test-cut in card,
offer up the board, shift ±0.5 mm before cutting acrylic. Under-cutting hides the display
border for a few pixels; over-cutting shows a hairline of border. Decide on the test piece.
**Inky standoff holes (M2 ×4) transfer from the board in hand — do not pre-cut.**

**Rail clearance.** The off-centre display means the board's lower edge may reach Y ≈ 2.40
behind the panel. Jewel rear body tops at 2.125, pots at 1.81 — ~0.275 in clear. Confirm
before final cut; if it intrudes, drop the whole rail to Y = 1.50.

## Panel schedule

| Part | Qty | W | H | Features | Joins |
|---|---|---|---|---|---|
| Face | 1 | 9.50 | 12.00 | Hole schedule above | Removable, 4 × M3 c'sunk into corner blocks |
| Back | 1 | 9.50 | 12.00 | Standoff holes for meter driver, ESP32, terminal block — transfer from boards | Solvent-welded |
| Side | 2 | 3.00 | 12.00 | Plain | Solvent-welded |
| Top | 1 | 9.00 | 3.00 | Vent: 8 slots 2.00 × 0.125 at 0.75 pitch, centred | Solvent-welded |
| Bottom | 1 | 9.00 | 3.00 | Vent as top; 4 × Ø 0.257 on 2.00 × 1.50 for flange bolts; Ø 0.75 loom pass, grommeted | Solvent-welded; bolts to flange |
| Corner block | 4 | 0.75 | 0.75 | Acrylic, tapped M3 or brass insert | Welded into front corners |
| Flange | 1 | 6.00 | 4.00 | **1/4 steel.** Shaft welded on; 4 × M6 tapped; arm boss | Structural |

Sizes assume 1/4 in stock and butt joints: sides fit between face and back (3.50 − 0.50), top
and bottom between the sides (9.50 − 0.50). For tab-and-slot, keep external 9.50 × 12.00 × 3.50.

## Depth stack (front to back)

| Zone | Element | Depth behind face |
|---|---|---|
| Upper | Simpson 1327: 1.22 body + 0.70 terminal studs | 1.92 |
| Middle | Inky (standoff 0.25 + board ~0.25) + i3 (~0.93) + Pi (~0.80) | ~2.2 |
| Back panel | Meter driver (MCP4728 + MCP6004), ESP32, terminal block | on the back |

Both fit inside 3.00 clear. Confirm the i3's 23.6 mm datasheet height includes its header; if
not, add it and re-check.

## Structure

**The acrylic holds instruments, not loads.** The 2 × 3 in shaft ends in the 1/4 in steel
flange. The head's bottom panel bolts down onto the flange; the LED fixture arm attaches to the
same plate. The cantilever's moment goes steel-to-steel and never through the box.

## Material and finish

- Face: **clear, reverse-engraved** — scale text, labels and the three band dividers engraved
  from the back, reading as frosted marks in glass; apparatus visible through the front.
  Fallback if too busy against the boards: light-grey opaque. Decide on the test piece.
- Sides, top, bottom, back: clear. Plan the loom and terminal-block layout before assembly.
- Solvent weld (Weld-On 4 or 16) for the five-sided box. Face on screws for service.
- One earned accent: no coloured acrylic, no warm interior LEDs. The lit jewel is the only
  warm thing.

## Meters — order

| Use | Model | Movement | Catalog | R_sense |
|---|---|---|---|---|
| pH, moisture | 1327 | 0-50 µA, 1800 Ω, self-shielding | **04380** | 40.96 kΩ |
| alt, taut-band | 1327T | 0-50 µA, 960 Ω, no pivot friction | 04381 | 40.96 kΩ |

Two of either. R_sense = 2.048 V (MCP4728 internal ref) / 50 µA; coil resistance does not enter.
Taut-band tracks a slowly drifting pH without stiction and is the better choice for an
instrument that mostly sits still.

## Before cutting acrylic

1. Test-cut the face in card at full scale; offer up both meters and the Inky.
2. Have the boards in hand for standoff holes (face: Inky M2 ×4; back: driver, ESP32).
3. Pump relay moves to GPIO23 the day the Inky goes on the Pi (BCM17 is its BUSY line).
4. Confirm the i3 stack height against the 3.00 in clear.
