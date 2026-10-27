# P1 — the first-install prototype

**Status: designed 2026-10-27, not built.** Branched from V1 to get an elegant,
working piece built and photographed without the station's cabinet, mast, steel
case and tray. V1 is parked, not deleted. The electronics and software are the
ones that have run a plant since the April 1 go-live; P1 is almost entirely a
physical build.

Geometry: `cad/growlab_cad/proto.py`. Cut files: `python cad/proto_build.py` →
`cad/out/proto/`. Tests: `tests/unit/test_cad_proto.py`.

## The piece

- **The planter.** A CMU lying on the floor as it was made, coir straight in
  its two cores, standing on four printed pads in a full-size steam table pan
  that catches the runoff. The sensor case sits on its top between the plants.
- **The instrument.** A second CMU **stood on end**, a solid face shell to the
  viewer. The two Weston dials and the e-ink are **cored into that face**: two
  Ø 2.75 holes across the upper half, a 6.30 × 3.78 window in the lower. Stood
  on end, the block's cores become two horizontal tunnels behind the face, open
  only at the sides; the hardware stack lives in them behind four laser-cut caps.
- **The crook.** One stick of 3/4 EMT on a hand bender: a stub into the lower
  tunnel, up the block's side on clamp backs, a back-to-back over the top to the
  planter, and a second down to the light. Three 90s in one plane, and the LED
  cable's raceway. The marks are in `cad/out/proto/bend_sheet.md`.
- **The light.** A white oak beam. The two aluminium heatsink bars sit **flush
  in its top**, so they shed heat to the room exactly as bare bars do (33 W
  measured for both, about 40 W/m); the LEDs are recessed 1.7 in up inside it,
  so nobody standing beside it sees a die. Its +X end block is the **camera's
  bay**: Camera Module 3, tilted 30° at the plants, under a printed lid. Its
  cable runs in a groove along the top of the spine to the hub.
- **The telescope.** The light's height adjusts: **12 to 24 in over the media**.
  A 1/2 EMT inner tube carries the beam and slides inside the crook's 3/4 drop.
  A 3/4 set-screw coupling on the drop's end locks it, bearing through a slot in
  a printed sleeve that centres the 1/2 in the coupling. A printed bushing on
  the inner tube's top end is the second guide. Loosen, slide, tighten. The 1/2
  lands in the beam's printed hub through a set-screw connector.
- **The ground plate.** 1/4 steel under both, set back half an inch from every
  visible edge. Free-standing, the instrument block tips at about 2.6 lb of side
  push at the beam. Bolted to the plate, with the light hanging inside the
  plate's footprint and the wet planter standing on it, it cannot.

The pump and the reservoir are in a bucket a couple of feet away, out of shot.
The pH and EC probes go with them.

## Start today: leach the planter block

Media straight in the cores means raw concrete against the root zone, and raw
CMU drives the pH alkaline. Soak the planter block in dilute vinegar (about
1/4 cup per gallon) for half an hour, then rinse several times a day for one
to two weeks (V1_PHYSICAL_BUILD.md, *Note on the cores*). **This is the long
pole.** Everything else below fits inside it.

## Measure first

Coring is the one step that cannot be undone, and the block's shells and web
are typical figures, not this block's. Caliper, then re-run `proto_build.py`:

- [ ] **The instrument block:** overall size; face-shell, end-shell and web
      thickness; where the web sits. Then lay `face_template.dxf` against the
      block's side and check that its tunnel lines land on the real web.
- [x] **The Weston flange OD** -- 3.510, calipered 2026-10-27, in the components
      library. The holes are set so the two flanges just clear each other.
- [ ] **The Inky board**, to check it fits behind the window.
- [ ] **The EMT**, 3/4 and 1/2, OD and bore, and **your bender's take-up**, which
      is stamped on the shoe (`EMT_OD`, `INNER_OD`, `TAKE_UP`). The marks follow
      from the take-up.
- [ ] **The 3/4 set-screw coupling**, length and OD, before printing the sleeve.
- [ ] **The camera and its CSI-to-HDMI adapter**, before printing anything for
      the bay; and the micro-HDMI plug, to check it passes the 1/2 bore.
- [ ] **The steam pan**, top and floor, before cutting the plate.

## Buy

- 3 CMUs (8 × 8 × 16 stretchers): planter, instrument, and one to practise the
  coring on. They are about $2 each.
- 1 full-size 2-1/2 in steam table pan.
- 2 × 10 ft 3/4 EMT (one to practise on); 1 × 10 ft 1/2 EMT; a 3/4 set-screw
  coupling; a 1/2 set-screw connector and locknut; a 3/4 insulating bushing for
  the stub's end; 2 one-hole straps with clamp backs; 3/16 Tapcons.
- An HDMI cable with a **micro-HDMI** plug at one end (about 3 m) and a
  micro-HDMI-female to HDMI-A adapter: the micro end is the one pulled through
  the conduit.
- A 2-3/4 in diamond core bit and a 1/2 in masonry bit; a diamond blade for the grinder.
- White oak, 10/4 (or two 5/4 glued) for an 18 × 5 in blank.
- 3 mm matte white cast acrylic for the caps; 1/8 ply or acrylic for the template.
- 1/4 steel for the plate; a 3/8-16 flat-head bolt, nut and fender washer.
- Already on hand: the boards and heatsinks, the driver, the dials, the Inky,
  the Pi stack, the sensor case, the pump, and the coir. Perlite and mesh are
  on V1's buy list.

## Build, in order

1. **Leach the planter block** (above). Meanwhile:
2. **Cut and print.** Laser the template and the caps; print the hub and the pads
   in PETG (no supports); plasma the plate and countersink its bolt hole underneath.
3. **Mill the beam.** Two setups on the router: `beam_top.dxf` (the bar pockets,
   0.525 deep, and the hub pilots), then flip end for end and run
   `beam_bottom.dxf` (the two light channels, through to the pockets inside a
   1/8 ledge, and the camera's lens window). Setup 1 also cuts the camera bay,
   its lid's rebate and the cable groove. The 1/4 wire hole goes through the
   spine at the middle. Finish it with oil, then fit the bars (LEDs down), the
   camera and the lid, and screw on the hub.
4. **Core the instrument block.** Practise on the spare first. Hold the template
   square to the face and drill the pilots through it. Core the two dial holes
   wet, with the 2-3/4 bit and no hammer. For the window, drill the four corners
   with the 1/2 in bit, then join them with the grinder: the corners come out
   round and there is no overcut. Drill the 3/8 bolt hole through the bottom end
   shell.
5. **Bend the crook** from the bend sheet. Practise the stub and one back-to-back
   on the spare stick first; then bend the real one, laying it flat between
   bends to check it hasn't dog-legged. Cut the drop and ream it. Cut the 1/2
   inner tube (step 5 of the sheet), press the printed bushing on its top end,
   and slide it up into the drop. Fit the coupling and the sleeve.
6. **Set it out.** Lay the plate down, then the pan on it, then the pads and the
   planter. Bolt the instrument block down through the lower tunnel. Swing the
   crook's stub in through the lower right opening and strap the riser on its
   clamp backs into the back face shell's edge. Pull the camera's micro-HDMI end
   through first, then the LED pair. Then hang the beam on the inner tube and
   set the height.
7. **Fit the stack.** Upper tunnel: the dial bodies at the front, set in the
   holes with neutral-cure silicone; the Pi and i3 behind them. Lower tunnel: the
   Inky behind its window, and the LED driver and supplies along the back, clear
   of the stub. The LED pair goes up the crook. The sensor case's Cat5e and the
   probe leads come across the floor behind the pan and into the lower left cap.
8. **Plant, run, photograph.** The software is unchanged.

## Parked for P1

- V1's cabinet, mast, carriage, steel case, fascia and tray: parked, with their
  files and tests intact.
- The canopy fan.

## Known risks

- **The crook is about 58 in tall.** The telescope needs 12 in of travel plus
  2-1/2 in of overlap in a straight piece of the drop, short of the last bend.
  That sets how high the run goes.
- **Dial-hole edges.** There is 0.6 in of concrete between each dial hole and
  the block's free edge. Practise on the spare block.
- **The window's reveal is 1.25 in deep**, the face shell's thickness. Looking
  down on it from standing height, its top edge hides the top of the e-ink. If
  that matters, chamfer the top edge with the grinder.
- **The stub's bend leaves the lower tunnel at the bender's radius**, about 4 to
  6 in up the right-hand opening, so the lower right cap is notched there.
