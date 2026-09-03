# Instrument Head Plans — Rev A (2026-09-03)

Fabrication schedules for the mast's instrument head. Drawings:
`https://claude.ai/code/artifact/f1a197ae-7692-4219-a686-0100183e3f0b`
Design study: `https://claude.ai/code/artifact/c18075c9-9ca8-4f42-8ba3-2066474b21b6`
**These tables are the authority; the drawings illustrate them.**

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

## Dial faces — converting to pH and moisture

A NOS meter arrives reading "MICROAMPERES D.C." The job is not relabelling it: the dial is a
separate flat plate held to the movement frame (typically two small screws — confirm on the
unit), and you **replace the plate**.

### Two facts that make this easier than it looks

**1. Hunt for matching faces, not matching movements.** Each channel has its own R_sense, so
a 50 µA meter and a 100 µA meter sit side by side and read identically. Only the *faces* have
to match — same diameter, same arc, same typographic character, similar patina. Two
mismatched dials read as a flea market; two different movements behind matched dials read as
an instrument. This widens the hunt considerably.

**2. The scale law is software, so the dial does not have to be linear.** The Pi computes the
DAC value from the sensor reading; nothing about the movement forces a linear scale. Design
the dial the way the instrument should read, then write the mapping to match it.

**No meter driver code exists yet** (`pi/drivers/` has no DAC module), so nothing constrains
this. Order of operations: **design the dial first, write the mapping to fit it.** Not the
reverse.

### The pH scale decision

Mapping pH 4.0–9.0 linearly across the arc puts the 5.8–6.2 target band at 8% of full scale —
on a ~90° arc, about 7°. Visible, but a poor use of the instrument, since almost all of the
dial covers water this system will never hold.

Mapping 5.0–7.0 linearly gives the target band ~18°, far more legible, but the meter pegs
during fill and top-off (plain water measured pH 8.3 in March) — exactly when you most want
to watch it move.

**Recommended: a non-linear scale, expanded around the working band.** For example
4.0–5.5 across the first 20°, 5.5–6.5 across the middle 45°, 6.5–9.0 across the last 25°.
The target band gets the same ~18° as the narrow linear scale, and pH 8.3 still reads on
the dial instead of slamming the stop. Print a fine band at 5.8–6.2 so drift is legible
without reading numbers at all.

Moisture stays linear 0–100%; there is no reason to distort it. Mark the working band.

### Making the plate

1. **Both meters in hand before anything is cut.** Do not commit a design to a meter you have
   not got.
2. **Scan each original dial flat at 600 dpi or better with a rule in frame**, before removing
   anything. Photograph the pointer at rest against the original scale — that rest position is
   the mechanical zero the new scale must honour.
3. **Trace in vector from the scan**: pivot centre, scale radius, arc start/end angles, and
   the plate's own mounting holes and outline. Derive the geometry from the original; do not
   compute it from scratch, or the pointer will not sweep the scale you drew.
4. **Draw the new face** in that geometry — scale, numerals, legend (`pH` / `MOISTURE %`),
   band markings.
5. **Print on matte stock and match the cream.** A bright white face behind an aged Bakelite
   ring looks wrong; sample the colour off the scan. Mount to the original backing plate if it
   survives stripping, otherwise to new aluminium of the same thickness.
6. **Test-fit before final assembly.** Refit the plate, inject current, sweep the pointer end
   to end, and check it tracks the printed scale over the whole arc.
7. **Calibrate to the print, not to the spec.** The Bourns 3296 trimmer in R_sense sets full
   scale, so the printed maximum is the target — trim the needle onto it.

**Or send it out.** Several firms do exactly this work, including replicating old dial artwork:
[Weschler Meter Modification](https://www.weschler.com/services/meter-mods/),
[Meter Sales](https://www.metersales.com/custommeters), and Ram Meter print dials in house.
Worth pricing against your own time — the geometry tracing is the fiddly part, and they have
done it before.

### Handling

- The pointer is the fragile part. Work over a soft cloth, and never force the plate past it —
  on some designs the plate slides out sideways clear of the pointer, on others the pointer
  must be lifted. Confirm which before applying any pressure.
- Do not touch the hairsprings or move the zero adjuster.
- Keep the original glass and bezel ring; they are most of what you are buying.
- Keep the original dial plate whole even after replacement. It is the only record of the
  geometry if the new one has to be redrawn.

## Before cutting acrylic

1. Test-cut the face in card at full scale; offer up both meters and the Inky.
2. Have the boards in hand for standoff holes (face: Inky M2 ×4; back: driver, ESP32).
3. Pump relay moves to GPIO23 the day the Inky goes on the Pi (BCM17 is its BUSY line).
4. Confirm the i3 stack height against the 3.00 in clear.
