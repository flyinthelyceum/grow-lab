# Instrument Head Plans — Rev C (2026-09-04)

**Rev C: the face is the front plate of a white steel instrument case, behind a clear
acrylic fascia in the cabinet's front.** See V1_PHYSICAL_BUILD.md § Mast → *The console*.
What stands from Rev A: the face hole schedule (now cut in 1/8 in mild steel), the depth
stack, the dial-face conversion, and the layout candidates. What is superseded: the acrylic
box, the corner blocks, the flange, the mast loom pass, the 46–58 height stack, and Rev B's
ply lip. The plate is the front of a 9.50 × 12.00 × 2.75 folded 16 ga box (`cad/case.py`);
F1–4 fasten the plate to the box's front flanges. The case sits 0.1 in behind the fascia,
which has holes only for the two knob shafts. Panel centre **28.2 in**. **White
(2026-09-05): DTM acrylic, satin**, the same paint as every other metal part in the piece.
No powder-coating in V1. The plate is ferrous, which is what DTM acrylic is formulated
for — scuff and degrease, no primer.
Reverse-engraving no longer applies; the witness rings are scribe lines on the back of the
plate.

Fabrication schedules for the instrument face. Drawings (Rev A, head-on-mast):
`https://claude.ai/code/artifact/f1a197ae-7692-4219-a686-0100183e3f0b`
Design study: `https://claude.ai/code/artifact/c18075c9-9ca8-4f42-8ba3-2066474b21b6`
**These tables are the authority; the drawings illustrate them.**

- Units: inches unless marked mm. Origin: panel bottom-left, X right, Y up.
- Material (Rev C): plate 1/8 in **mild steel**, box 16 ga **mild steel**, both in white
  DTM acrylic (black until 2026-09-05 — the whole metal register went white, then went
  aluminium-free; see V1_PHYSICAL_BUILD.md § *The white register*). Steel rather than the
  aluminium first drawn: **2.9x the bending stiffness at the same 1/8 in**, which is the
  right direction for a plate carrying two movements, at 2.9x the weight — 4.05 lb rather
  than 1.40. **The plate will mark.** DTM is softer than powder and this plate is handled
  at every service. Accepted: one paint across the whole piece matters more, and a mark
  touches up. The fascia in front of them is 1/4 in **cast** acrylic, clear
  (not extruded — it crazes).
- Meters: **Weston 301, 3-1/2 in centre-zero**, two — 30-0-30 uA and 100-0-100 uA.
  The Simpson Wide-Vue 1327 this schedule was drawn for is **not** what is being
  built. Bezel OD 3.50 in is nominal for the size class; **the panel cut and stud
  pattern below are Simpson figures and do not apply** — recut this schedule from
  calipered bezels before drilling. See the emulator at `/panel`.
- Face: **9.50 W x 12.00 H**, in the cabinet front. Clear behind: 3.00 (the console bay).
- Height stack (Rev B): face 22.2–34.2 in; panel centre **28.2 in**. (Rev A: 46–58, centre 52.)

## Face — hole schedule

| ID | X | Y | Cut | For |
|---|---|---|---|---|
| M1 | 2.750 | 9.500 | Ø **pending calipers** (was Ø 2.79) | Weston 301 — pH |
| M1a–d | *pending* | *pending* | Ø 0.125 thru ×4 | M1 studs — pattern was Simpson 2.25 sq |
| M2 | 6.750 | 9.500 | Ø **pending calipers** (was Ø 2.79) | Weston 301 — EC |
| M2a–d | *pending* | *pending* | Ø 0.125 thru ×4 | M2 studs — pattern was Simpson 2.25 sq |
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

## Depth stack (front to back)

| Zone | Element | Depth behind face |
|---|---|---|
| Upper | Weston 301 body + terminal studs — **pending measurement** (Simpson 1327 was 1.22 + 0.70 = 1.92) | ? |
| Middle | Inky (standoff 0.25 + board ~0.25) + i3 (~0.93) + Pi (~0.80) | ~2.2 |
| Back panel | Meter driver (MCP4728 only — the MCP6004 stage was dropped when the movements proved to be microamperes), ESP32, terminal block | on the back |

Both fit inside 3.00 clear. Confirm the i3's 23.6 mm datasheet height includes its header; if
not, add it and re-check.

## Material and finish

- Plan the loom and terminal-block layout before assembly.
- One earned accent: no coloured acrylic, no warm interior LEDs. The lit jewel is the only
  warm thing.

## Meters — sourced

Already purchased; this is no longer an order table.

| Use | Movement | Series resistor per leg |
|---|---|---|
| pH | Weston 301, 30-0-30 µA centre-zero | 56.2 kΩ |
| EC | Weston 301, 100-0-100 µA centre-zero | 16.9 kΩ |

**Caliper both bezels on arrival** and recut the face hole schedule from the measurement.
Matched faces were the point of the hunt; the 100-0-100 ring reads chunkier in the seller's
photos, so confirm the two are the same size before committing to a symmetric pair.

The Simpson Wide-Vue 1327 order table this section used to hold (catalog 04380 / 04381,
0-50 µA, 40.96 kΩ R_sense) is superseded and has been removed to stop it being ordered from.

Two of either. At tens of microamperes the DAC drives each movement directly through a
fixed series resistor per leg — 56.2 kΩ for the 30 µA movement, 16.9 kΩ for the 100 µA —
landing just under full scale by design, so no DAC fault state can overdrive a historic
movement. Coil resistance does not enter.
Taut-band tracks a slowly drifting pH without stiction and is the better choice for an
instrument that mostly sits still.

## Dial faces — converting to pH and EC

**The sourced meters are centre-zero** (Weston 301, **30-0-30 µA and 100-0-100 µA** — the
printed dials read MICROAMPERES; the purchase listings said milliamperes and were wrong).
The pointer
rests mid-scale and the movement's hairsprings are balanced for that; it cannot be converted
to end-zero without rebuilding the movement, and should not be. Design the dials as
**deviation-from-target** instruments: needle dead centre means on target, and drift reads as
asymmetry without anyone reading a number. That is the better instrument for tending, and it
settles the pH scale question below — centre is simply 6.0.

A NOS meter arrives reading "MICROAMPERES D.C." The job is not relabelling it: the dial is a
separate flat plate held to the movement frame (typically two small screws — confirm on the
unit), and you **replace the plate**.

### Two facts that make this easier than it looks

**1. Hunt for matching faces, not matching movements.** Each channel has its own series
resistor, so a 30 µA meter and a 100 µA meter sit side by side and read identically. Only
the *faces* have
to match — same diameter, same arc, same typographic character, similar patina. Two
mismatched dials read as a flea market; two different movements behind matched dials read as
an instrument. This widens the hunt considerably.

**2. The scale law is software, so the dial does not have to be linear.** The Pi computes the
DAC value from the sensor reading; nothing about the movement forces a linear scale. Design
the dial the way the instrument should read, then write the mapping to match it.

**No meter driver code exists yet** (`pi/drivers/` has no DAC module), so nothing constrains
this. Order of operations: **design the dial first, write the mapping to fit it.** Not the
reverse.

### The pH scale, on a centre-zero dial

Centre is 6.0 — the target — so the question is only the span. **±1.0 pH (5.0 to 7.0)** puts
the 5.8–6.2 band at ±20% of half-scale, plainly legible, with a fine band printed at its
edges. Water above 7.0 pegs right during fill and top-off, but on a centre-zero dial a pegged
needle still reads correctly as "far too alkaline" rather than as a number you have to
interpret. Widen to ±1.5 if you would rather see the 8.3 fill water on-scale.

The scale law is still arbitrary, so it can be expanded around centre if ±1.0 proves coarse.

**Moisture** deflects wet-right, dry-left from a centred target. Size the span from the real
data rather than guessing: the SEN0308 has logged since April, so query the actual daily
wet-to-dry swing and set the scale so a normal irrigation cycle uses most of the arc without
pegging. The needle then breathes visibly with the watering rhythm.

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
   survives stripping, otherwise to new **aluminium** of the same thickness. This is the
   one place aluminium is still specified, and for a reason: it sits inside a moving-coil
   movement, where a ferrous backing plate would be in the field of the magnet. Non-magnetic
   is the requirement; brass or thin plastic do the job equally well if aluminium is awkward.

   **Check it against the finished plate, not only against the meter.** This instruction was
   written when the plate was black, where the cream face was the bright thing and the dark
   ring vanished into the panel. On a white plate that inverts: the ring becomes the dark
   thing and the cream face sits a few points off the plate around it. Matching the cream is
   still right for the meter's own internal look. Whether the pair reads on white cannot be
   settled from a scan — hold a proof print in the meter against the coated plate before
   committing the print run.
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
3. Confirm the i3 stack height against the 3.00 in clear.

## Layout candidates

The face is emulated at `/panel` on the dashboard, at true proportion and with the
needles running the same maths and the same `[meters]` config as the hardware. Four
arrangements are held in `pi/dashboard/panel_geometry.py`, which is the source this
schedule should be regenerated from once a layout is chosen:

| Layout | Dials | Argument |
|---|---|---|
| **Schedule** | 2.750 / 6.750 at Y 9.500 | This table. Tight matched pair reading as one instrument; every rail element on a meter-derived column |
| Wide pair | 2.375 / 7.125 at Y 9.500 | Air between the movements, less at the margins; risks reading as two instruments |
| Offset pair | 2.750 at 10.000, 6.750 at 9.000 | Asymmetry as intent rather than symmetry as default; risks reading as an error |
| Inverted | Y 4.400, window above at 9.100 | Slow e-ink face reads first, needles second — the opposite of what this table asserts |

A stacked column of both dials was drawn and discarded: 3.50 + 3.50 for the movements,
3.78 for the window and roughly 1.5 of rail is 12.28 in against 12.00 in of face. It
does not fit at any spacing. Asserted in `tests/unit/test_panel_geometry.py` so it
cannot creep back in.

**Dead space to decide.** In the Schedule layout the band between the window's lower
edge (Y 3.470) and the rail (Y 1.625) is 1.845 in of empty acrylic — the largest void
on the face. Visible in the emulator; either deliberate breathing room or an argument
for the Inverted layout.
