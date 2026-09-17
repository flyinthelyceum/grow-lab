# Mounting & Cabling

`WIRING_&_BUSES.md` says what connects to what. This says **where it physically
bolts, what it plugs into, and how the cable gets there.** The two are meant to be
read together: that one is the schematic, this one is the chassis.

Written 2026-09-12, against a bench prototype that works electrically and is a
mess physically. The goal is not tidiness for its own sake. It is that this piece
puts its apparatus behind glass on a white ground, so the wiring is finish work,
and that the instrument case is meant to come out on a bench in under a minute,
which only happens if someone designed the disconnect.

---

## The one fact that governs everything: there are two standards, not one

The console bay sits behind a clear acrylic band across the whole cabinet front,
on a white backplate. `V1_PHYSICAL_BUILD.md` already names the consequence —
"cable discipline is visible, and on white it is unforgiving." A dark cable that
vanished against a dark ground is now the highest-contrast object in the piece.

So hold two different standards and know which one you are working to:

| | Inside the instrument case | In the console bay, the mast, the wet bay |
|---|---|---|
| Who sees it | Nobody, until it is opened | Everybody, always, through the glass |
| Optimise for | Service speed, labelling, density | Looks first, then service |
| Acceptable | Ferruled screw terminals, visible board edges, service loops | Planned straight runs, laced, sleeved white/grey |
| Not acceptable | Dupont jumpers, unlabelled conductors, unrelieved cables | Anything black, any slack, any zip tie |

Almost every mistake in bench-to-station migration is applying the first standard
to the second zone.

---

## Where everything lives

Six zones. Each has one environment, one access method, and one cable discipline.

| Zone | Contents | Access | Environment |
|---|---|---|---|
| **1 — Plate assembly** | 2 × Weston 301, Inky + i3 + Pi stack, jewel, amber, 2 pots | Remove fascia, knob caps, F1–4 | Dry, warm |
| **2 — Case back panel** | MCP4728 meter driver, ESP32, terminal block | Through the front, plate off | Dry, warm |
| **3 — Console bay** | Nothing mounted. The loom crosses it | Fascia off | Dry, on show |
| **4 — Lower cabinet** | PWM-120-24 driver, 5 V PSU, 12 V adapter, pump relay | Removable lower ply front | Dry, hot |
| **5 — Wet bay** | Pan, pump, pH / EC / DS18B20 probes | Rear door | **Wet** |
| **6 — Lightbox** | LED boards + heatsinks, camera, gust fans | Ladder, collar released | Dry, high, hard to reach |
| **7 — The block** | AS7341, BME280, ADS1115, moisture probe | Lift the printed bar off | Damp, drip, lit |

Two consequences worth stating plainly.

**Zone 1 is the heavy one and it is the one that moves.** The plate is 4.05 lb of
steel before anything is hung on it, and the Pi/i3/Inky stack hangs off its back.
Every service operation lifts that assembly out through the front.

**Zone 6 is the expensive one to get wrong.** Anything that needs re-terminating up
there needs a ladder and a released clamp collar. Terminate it once, properly, with
more strain relief than feels necessary.

---

## Mounting method, by class of thing

### PCBs — standoffs on a defined thread, never anything else

No hot glue, no board resting on its own connectors, no board held by the
stiffness of its wiring. Each board gets four standoffs and four screws.

One exception, argued rather than assumed: the ADS1115 inside the canopy sensor
case is **taped**, because its outline comes from a vendor listing rather than a
caliper and a printed fence sized to a wrong number is a board that will not go
in. Tape tolerates a millimetre; a fence does not. That reasoning does not
extend to anything whose dimensions are known — and it stopped covering the
BME280 the moment it was hung upside down, since tape is not what holds an
inverted board. It has two bosses on its own mounting holes now, like the
AS7341.

| Board | Thread | Notes |
|---|---|---|
| Raspberry Pi | M2.5 | 58 × 49 mm pattern. Brass standoffs; the Pi wants its grounds common |
| Inky Impression 7.3" | M2 | Holes **transfer from the board in hand** — do not pre-cut (per `INSTRUMENT_HEAD_PLANS.md`) |
| i3 InterLink | — | Seats on the Pi's header, supported by the Pi's standoffs. Verify it is not cantilevered on the header alone |
| MCP4728 breakout | M2.5 | Nylon. Keeps the DAC's ground off the case |
| ESP32 dev board | M3 or M2.5 | Check the specific board; Freenove boards vary |
| ADS1115 | M2.5 | Nylon |

Use **nylon** where the board's ground should not meet the case, **brass or steel**
where it should. Decide per board and write it down; a board that is grounded by
accident through one metal standoff is a fault that takes a day to find.

### The 16 ga tapped-hole problem — use clinch nuts

`V1_PHYSICAL_BUILD.md` specifies the case's side return flanges as "tapped M3" in
16 ga. At 1.6 mm of material and 0.5 mm pitch that is about three threads — right on
the usual minimum, carrying a 4 lb plate that is removed at every service. It will
strip, and it will strip on the service where you are already annoyed.

**Fit M3 self-clinching nuts (PEM S/SO type) into the flanges instead of tapping
them.** They press in cold, they give full thread engagement, and they cost pennies.
If clinch nuts are not available, form-tap (roll-tap) rather than cut-tap — it
extrudes material into the thread instead of removing it — or extrude-dimple each
hole first. Do not simply cut M3 threads in 16 ga and hope.

The same rule applies anywhere a board mounts directly to the case: clinch standoffs,
rivnuts, or through-bolt with a nut. Not tapped sheet.

### Service loops are a mounting requirement, not a nicety

When F1–4 come out, the plate carries the Pi stack with it and has to **lie down
beside the case, face up, still connected**, or the disconnect has to be undone
blind through a 9.5 in opening. That means every conductor between Zone 1 and Zone 2
needs enough slack to let the plate travel forward and rotate flat — call it **8 in
of free length beyond the taut path**, dressed into a service loop that is retained
by a P-clip so it does not sag onto the meter terminals when the case is upright.

This is the single easiest thing to get wrong and the most annoying to fix later,
because the fix is re-terminating everything.

### Panel-mount components

Jewel, amber indicator and the two pots mount through the 1/8 in plate and are
captured by their own nuts — nothing extra needed. Two points:

- **The pots need their own anti-rotation provision.** A 3/8-32 bushing tightened
  hard against painted steel will turn eventually and take the wiring with it.
  Use the lock washer with the locating tab if the pot has one, or a spot of
  thread-lock on the nut.
- **The DTM will mark under every washer.** Accepted already for the plate face;
  just do not torque a panel nut down onto fresh paint and expect it to look new.

### Zone 4 — put the power on DIN rail

This is the zone that currently looks worst on any bench and cleans up the fastest.

Run a length of **35 mm DIN rail** across the back of the lower cabinet, and mount to
it: DC distribution terminals, fuse holders, the pump relay in a DIN carrier, and (if
you take Path B below) the supplies themselves. The Mean Well PWM-120-24 screws to
the cabinet floor or back on its own flanges; it does not need the rail.

The rail is what turns "four things cable-tied to a board" into equipment. It also
means the 5 V bus exists in exactly one place, which is what stops the spaghetti
coming back.

### Never mount anything to the tray or the pan — and one exception on the block

Load path and wet zone both. The tray carries water, never hardware; the pan
carries the probes and nothing else. Anything that needs to be near them mounts
to the carcass and reaches in.

**The block is the exception, and it is deliberate.** The canopy sensor case
sits on the CMU's centre-rear, because that is the only place on the piece that
is both unshaded and invisible — see *The canopy sensor case* below. It is held
by three dabs of silicone, drills nothing, and adds about 40 g to a 50 lb
block. The rule that stands is the one underneath it: nothing
structural, nothing wet, nothing that cannot be lifted straight off.

---

## Connectors — the standard

**The single highest-value change: no Dupont jumpers anywhere in the station.**
They have no retention, no strain relief, no keying and no label, they back out
under thermal cycling, and they are the reason bench builds look like bench builds.
They are fine for the next twenty minutes of prototyping and disqualified from
anything that gets closed up.

| Class | Connector | Why |
|---|---|---|
| I²C at each sensor | **Nothing — the branch lands in the bus block** | Struck 2026-09-15. The three canopy boards are soldered to one Cat5e, the probes are BNC and the camera is HDMI, so a pigtail connector had two places left to go, and both of those land in the four-rail push-in block with a ferrule, which releases tool-free. A crimp tool for two connectors was a tool in search of a job |
| I²C distribution | **A four-rail bus: SDA / SCL / 3V3 / GND** | No usable off-the-shelf hub exists for 0.1 in boards; every Qwiic hub assumes JST-SH. Four multi-way push-in blocks on the case back panel, one feed in from the Pi, every branch landing with ferrules. ~$12, and adding a sensor later is four push-ins |
| Atlas pH / EC probes | **Nothing — the i3 already has BNCs** | Three BNCs are soldered to the i3's own board edge, one per EZO slot. The probe mates directly. It is the cleanest termination in the build |
| Pi GPIO to discrete loads | **Screw terminal breakout + bootlace ferrules** | The RSP-GPIO-8 is already in the build. Ferrules are what make it look made |
| Case ↔ station umbilical | **One multipin, side wall, right-angle hood** — see below | Makes "unplugged at one terminal block" literally true |
| pH and EC probes | **A gland, not a bulkhead** — see *Open items* | Settled 2026-09-12: the i3 has its own BNCs on its board edge. Bulkheading both through one steel panel would bond the two isolated domains; the probe cables gland through and plug straight in |
| DC power distribution | **WAGO 221 lever splices**, or DIN terminals | Already in the BOM. Reusable, no crimp tool, visibly deliberate |
| Camera | CSI ribbon, its own slot and clamp | Cannot pass through any connector above |
| Mains | Factory cordsets only in V1 — see *Power* | Do not hand-terminate mains in this build |

Two of these need the reasoning spelled out, because getting them wrong is expensive.

### The umbilical goes on the case's **side** wall, not the back

The docs imply a rear disconnect — a Ø 0.75 grommeted loom pass in the back panel,
with the loom landing on a terminal block inside. That works, but it means you must
open the case before you can free it, and it cannot become a plug.

It cannot become a rear plug either, because **there is under half an inch behind the
case.** Console bay 3.00 in clear, case 2.75 in deep; `V1_PHYSICAL_BUILD.md` puts the
gap at 0.44 in "for the loom to turn down". A mated D-sub with a hood needs roughly
an inch. A rear connector does not fit, at any pin count.

The side wall does. The bay is the full 20 in of cabinet width and the case is 9.50 in
wide, so there is roughly **5 in of clear bay either side** — more than enough for a
mated connector with a right-angle hood that turns the cable straight down toward the
chase, which is where the loom already goes.

Two things follow. First, this is a change to `cad/case.py` and to the case body DXF,
so it needs modelling before the blank is cut. Second, **it is visible through the
fascia**, so choose hardware that reads as instrument hardware rather than as a
compromise: a metal-hooded D-sub or a screw-collar circular connector both look
correct on the flank of a white instrument case. That visibility is not a problem to
hide; it is the piece saying it is serviceable.

**Size it at DB-25.** The schedule below comes to 19 conductors, not the "about 22" an earlier draft counted, with the 5 V and ground pins already doubled. DB-25 leaves six spare, which covers a second fan or a moved sensor; the moisture probe already rides the block's I²C and adds nothing. A DB-37 was headroom for a count that had been added up wrong.

### The probe BNCs must be **isolated** bulkheads

`BOM.md` struck the ~$56 inline isolators on the grounds that the i3 InterLink already
carries two isolated EZO slots, and pH and EC are exactly the two circuits that need
them. That reasoning is right, and it is fragile in one specific way.

The isolation works by keeping each probe's reference out of common with the other and
with system ground. **If both probe coaxes are bulkheaded through the steel case with
standard, panel-grounding BNC connectors, both shields bond to the case and therefore
to each other — which is precisely the condition the isolated slots exist to prevent.**
You would pay for isolation, fit it correctly, and then short it out with two $3
connectors. The symptom is the classic one: pH that moves when EC is read, and a week
of chasing it in software.

So either:

- fit **insulated / isolated bulkhead BNCs** (the shield floats from the panel), or
- pass each probe cable **uninterrupted** through its own gland and land it directly
  on the i3, accepting that the case cannot then be fully unplugged.

The first is better and is what lab instruments do. Verify the i3's probe termination
(on-board BNC versus flying leads) before buying either — it is not confirmed in the
docs and it decides the jumper on the inside.

### Ferrules on every stranded conductor

Bootlace ferrules into every screw terminal, without exception. A crimper and an
assorted box is about $25. It stops strands splaying and bridging, it stops the screw
crushing and work-hardening the conductor, and it is most of the visual difference
between a terminal block that looks professional and one that looks improvised. There
is no argument against it.

---

## What actually crosses the case boundary

This is the schedule the umbilical is sized from. **Treat it as a draft to verify
against the boards in hand, not as authority** — the face hole schedule earned that
status by being cut from calipered parts, and this has not been yet.

| # | Function | Conductors | To | Notes |
|---|---|---|---|---|
| 1 | Pi supply | 5 V, GND (×2 each) | Zone 4 PSU | 18 AWG. Double the pins |
| 2 | Pump relay | GPIO, 5 V, GND | Zone 4 relay | **GPIO23, not 17** — see below |
| 3 | LED driver dim | PWM, GND | Zone 4 driver | From the ESP32, in the case |
| 4 | Gust fans | PWM, TACH, GND | Zone 6 | In the lightbox. 12 V reaches them from Zone 4, not through the case |
| 5 | Block I²C | SDA, SCL, 3V3, GND | Zone 7 | **One run.** AS7341, BME280 and ADS1115 all live in the block's printed bar |
| 6 | Reservoir temp | DATA, 3V3, GND | Zone 5 | DS18B20, 4.7 kΩ pull-up stays at the Pi end |
| 7 | pH probe | coax | Zone 5 | Plugs straight into the i3's own BNC — gland it through, don't bulkhead |
| 8 | EC probe | coax | Zone 5 | Same. Bulkheading both would bond the two isolated domains |
| 9 | Camera | HDMI | Zone 6 | Arducam CSI-over-HDMI pair. **Own path** — no connector above carries this |

19 conductors plus two coax plus one HDMI. Hence a DB-25 on the side wall, two glands
for the probe coax, and the HDMI's own path — a legible, buildable back-of-instrument face.

**The pump relay moves to GPIO23 when the Inky is installed.** The Inky hard-wires
BCM17 as BUSY and `config.example.toml` still has `relay_gpio = 17`. This is already
recorded in `V1_PHYSICAL_BUILD.md`; it is repeated here because it is a wiring fact
and this is the wiring document. One config line, and the terminal must be labelled
for 23 the day it is built, not the day it is debugged.

---

## Routing the loom

### Keep the three groups apart — physically, not just conceptually

`WIRING_&_BUSES.md` already names the groups (power, logic, sensor leads) and says not
to bundle them. In the station that means:

- **Separate runs, not one bundle with internal discipline.** Three paths down the
  chase, spaced across its width.
- **Cross at right angles** where they must cross. Never run mains or pump power
  parallel to a probe coax for any distance.
- **The probe coaxes are the sensitive ones.** They carry a ~100 MΩ source. Give them
  the run furthest from the driver and the pump, and do not coil the slack — a coil is
  an antenna. Fold excess flat in a long S.

### The run out to the block is the risky one

I²C was designed to cross a PCB, not a room. The run from the case to the block's printed
bar is roughly a metre. It will probably work; it is the leg most likely to produce
intermittent sensor dropouts that look like software bugs.

It got shorter and simpler when the sensors moved into the block: the AS7341, BME280 and
ADS1115 share one bar, so they daisy-chain locally and **one four-conductor cable** leaves
it. Three runs collapsed into one, and the moisture probe's analog lead now stays short,
which is worth more than it sounds — analog over a long lead is the fragile part.

**Do this one first: remove two of the three pull-up pairs.** Generic GY boards each
carry their own SDA/SCL pull-ups, and the Pi has 1.8 kΩ of its own on SDA1/SCL1. Three
boards at 4.7 kΩ in parallel with the Pi's give 0.84 kΩ, which sinks 3.46 mA at 3.3 V —
over the I²C spec's 3 mA, which is the current every device's low-level voltage is
guaranteed at. It still decodes; what it spends is the noise margin the metre of Cat5e
needs. Unsolder the pull-up pair on the ADS1115 and on the BME280, and keep the AS7341's
— it is at the far end of the run, which is where a pull-up does the most good. That
leaves 1.3 kΩ and 2.2 mA, with a rise time around 170 ns at 150 pF: comfortable at
400 kHz and trivial at 100.

Then the mitigations, in the order to try them:

1. Run the bus at **100 kHz**, not 400.
2. Use **Cat5e for the long leg** — SDA with a ground in one pair, SCL with a ground in
   another. The pairing is what buys the margin.
3. If it still misbehaves, fit an active extender (LTC4311 or P82B715) rather than
   lowering the clock further.

Do not diagnose this in software. If `as7341` drops out intermittently, suspect the
cable before the driver.

**What is on each end, and what is in between.** At the case: bare wire, soldered. A
JST-XH housing is 7.0 mm tall mated and the headroom over the ADS1115 is 5.8, so the
Cat5e's conductors solder straight to the pads — four of eight, SDA and SCL each paired
with a ground — and the boards daisy-chain on wire. Use **stranded** Cat5e (patch, not
riser): solid core work-hardens at a solder joint and snaps the first time the case is
lifted. At the cabinet: one **JST-XH 4-pin** crimped on where the cable reaches the
four-rail bus, which is the only connector on this leg and the only place it unplugs.

The route between them is **proposed, not yet built**: out of the notch in the case's
rear wall, down the block's rear face — held by the zip tie at the top and a dab of the
same neutral-cure silicone at the foot — along the tray's rear edge, then **down beside
the mast through the notch the mast already makes in the tray**, so the tray gains no
second penetration, and across the dry bay to the bus. Two things to confirm before it is
written as fact: that the notch's gasketed collar passes a 5.5 mm cable beside a Ø 1.5
tube, and that the cable clears the pan's rim on the way past the line pass.

### Sleeving and lacing — the visible runs

Where a run crosses the open field of the console bay, it is finish work.

- **White or light grey expandable sleeving** over each of the three groups, heatshrunk
  at both ends so no braid frays. `V1_PHYSICAL_BUILD.md` already calls for this.
- **Lace it, do not zip-tie it.** Waxed flat lacing twine, spot-tied every 1.5–2 in.
  It lies flat against the backplate where a zip tie stands proud and casts a shadow,
  it is adjustable, and it is exactly what is inside the instruments this piece is
  quoting. A spool is about $10 and the knot takes ten minutes to learn.
- **No slack in the visible field.** Any excess is dressed out in the chase, behind the
  case, or in the lower cabinet — never looped where it can be seen.

Zip ties are fine inside the case and in Zone 4. They are not fine behind glass.

### Strain relief at both ends of everything

Every cable is relieved **twice**: at the penetration (gland or connector backshell)
and again within about 2 in of its termination (P-clip, adhesive base, or a lacing
anchor). No conductor should ever take mechanical load at a screw terminal or a solder
joint. This is what stops the slow failure where a cable is tugged at service after
service until one strand is doing all the work.

**Drip loops on every cable entering the wet zone** — already canon in three documents,
restated because it is the one that gets skipped when you are tired.

---

## The canopy sensor case

Modelled in `cad/growlab_cad/sensor_case.py`; CI writes STLs to `cad/out/print/`.
**60 × 27 × 18.5 mm**, matte white, on the CMU's centre-rear. Two printed parts.

Rev H is Rev G with every estimate replaced by the calipered value out of the
components library, and two of them moved far enough to redraw the case.

**The STEMMA QT sockets are 4.7 mm tall, not 2.9.** Rev G read that height off a
photo and typed a 3.2 mm drop under the ceiling — "the sockets plus 0.3" — which
put the ceiling 1.5 mm *inside* them. That is the same failure as Rev E's, one
revision later: Rev E hung the sensor face 2.0 under the ceiling and the sockets
would have hit the lid. The drop is 5.0 now and it is an expression,
`SC_AS7341_QT_H + SC_QT_CLEAR`, not a number anyone types.

**The board's mounting holes are Ø2.29, not the Ø2.5 Adafruit publishes.** An
M2.5 does not pass through them, so the board hangs on M2 × 4 into Ø1.9 pilots.
The plate keeps M2.5: those screws pass through printed material at both ends
and nothing caps them at M2. Rev G's one-size-for-the-whole-case is gone, and a
test now asserts the two sizes are different on purpose so the plate cannot
quietly follow the board down.

The 1.8 mm the board dropped had to be paid for twice. **Downward**, it left only
1.76 mm between the plate boards and the underside of the hanging AS7341, so the
case is 0.5 mm taller. **Upward**, it lengthened the tube from the sensor to the
diffuser and took the field half-angle from 46° to 36° — at which point the
detector sees a spot on the disc rather than the disc. That tube is
`SC_WALL + SC_BAFFLE_DROP − SC_PORT_DEPTH − SC_AS7341_PKG_H` and is independent
of the case height, so the only lever is the bore: **Ø9.2 now, not Ø6.5**, with
the collar at Ø11.4. That restores 45.4° and still sits inside the LED's 6.5 mm
offset, which is the constraint that set the bore in the first place.

Everything else of Rev G stands. The board hangs on all four holes; the collar
is a light stop and stops 1.5 mm clear of the board. At 25.68 mm long it fills
the upper level, so the BME280 sits taped on the plate at the −X end, sensor up
beside an inlet slot, with the ADS1115 shifted 6.5 mm the other way.

**One row is still un-calipered: the board's width.** Its two independent
estimates disagree — the measured length came in 0.28 mm *over* Adafruit's
published 25.4, arguing the board runs large, while the sensor sitting 8.76 mm
from the LED edge argues for 17.52 if the window is truly centred. Nothing is
inferred from that; the published 17.78 stands as the estimate until a caliper
settles it. It decides how much board is left under the collar on the header
side, so measure it before printing.

Rev E is what five adversarial reviews left standing, and the short version is
that Rev D would not have printed. Four of its features were not attached to the
part: the baffle collar hung over a hole wider than itself, the lip touched the
body along a single edge, the four insert bosses floated below the ceiling
tangent to the walls, and the "countersink" was a counterbore leaving 0.3 mm of
bridged plate under each screw head. The geometry tests passed on all four,
because they compared bounding boxes and volumes and a bounding box cannot tell
a part from a pile of parts. The test that now catches every one of them at once
is that each half is **one solid**.

| | |
|---|---|
| Material | Matte white PETG. Not PLA — it creeps under a warm fixture. ASA if it will ever see sun |
| Orientation | **Both parts top-face-down.** The body's show face is then the bed face, and a textured sheet gives a matte nothing else matches. The plate that way up has no overhang at all |
| Extrusion width | **0.50 mm**, so the 2.0 walls and 2.5 plate land on whole lines |
| Layer height | 0.15 mm. The side walls are visible; that is what layer lines show on |
| Supports | **None**, and the tests say so from the solid rather than from the parameters: the only downward faces in either part are the disc's 3 mm ledge and seven vent roofs of 5.5 mm |
| Elephant's foot | Set the slicer's first-layer compensation. The bed face is the one on show |
| Inserts | **None.** Rev E used four M2 heat-set inserts; they were a soldering-iron step with an alignment risk on the one face that has to seat flat, for a box that opens a few times a year. The plate screws form their own thread in the corner bosses instead |
| Screws | **Two sizes, both thread-forming, each for a stated reason.** Plate: 4 × M2.5 × 6 countersunk into Ø2.3 pilots, up through a true 90° cone 1.1 deep (1.4 of plate left under each head) and 4.0 into the corner bosses. Board: 4 × **M2 × 4** pan into Ø1.9 pilots, up through the AS7341's own Ø2.29 holes, 3.5 into its bosses — an M2.5 will not pass that hole. Nothing screws the BME280 or the ADS1115: both are taped to the plate |
| Diffuser | Ø12 × 1 mm **etched** PTFE disc, etched face down, bonded with **neutral-cure (alkoxy/oxime)** silicone. See below — this is the one place the old sheet was quietly wrong |
| Feet | 3 × neutral-cure silicone, **cast in place** in the plate's recesses. Three points never rock |
| Interior | Paint matte black before assembly if the dark-period reading has to be zero. White PETG at 1 mm is a diffuser, not a shield |

**Silicone does not bond to PTFE.** Untreated PTFE is the reference non-stick
surface — about 18 mN/m of surface energy — and nothing in a workshop wets it.
The old sheet called the diffuser joint "the only one that has to keep water
out" and then specified a joint that cannot form: retention would have been a
0.15 mm fillet in shear against a surface with no grip on it, running from the
top face straight down to the sensor. Buy the disc as **one-side chemically
etched PTFE** (sold for bonding) and put the etched face down. Opal cast acrylic
1 mm is the alternative that any silicone will hold. Either way the recess is
Ø12.5 for a Ø12.0 disc, because its mouth is on the bed where elephant's foot
and hole shrink both eat into it, and PTFE does not compress.

**Conformal coating: mask first.** "Conformal-coat the boards" as written would
end the humidity channel permanently. The BME280's element is a metal lid with a
pinhole and it cannot be coated; neither can the AS7341's window. IPA-clean the
flux first — no-clean residue is hygroscopic and it is where the coating lifts —
then a Kapton dot over the BME280's lid and one over the AS7341's window, two
thin coats, dots off.

**It is vented, not sealed** — deliberately, because the BME280 has to sample
the air and a sealed box in a humid, lit, thermally cycling place collects the
water it was meant to exclude. **Both openings are in the rear wall**: inlets low,
outlets high, and the lid warming under the fixture drives the exchange. Nothing
opens in the plate. Rev D put the inlets there, facing the block — and the block
is a planter whose top face stays damp for weeks after a leach, so the case would
have breathed the block's own boundary layer and dewed on the diffuser every time
the lamp went off.

**The baffle is not decoration.** The breakout carries an illumination LED a few
millimetres from the sensor, pointing the same way. The collar round the sensor
shadows it, sets the field stop, and is the standoff that fixes sensor-to-diffuser
distance — one feature doing the optical job and the mechanical one. The bore runs
through the top wall at the collar's own diameter, so the collar sits on a full
ring of wall and the field stop is a plain tube: 6.5 across, 2.95 tall, 48° half
angle, wide enough that the sensor sees the whole disc. **The firmware now puts
the LED out on every read** (`pi/drivers/as7341.py`), which is the first line;
the baffle is the second, and at 1 mm of white PETG it attenuates rather than
blocks.

**Fixing:** three dabs of neutral-cure silicone in the plate's foot recesses,
pressed onto the brushed dry block and cured under the case's own weight. It
bonds to concrete and to PETG, fills the block's texture, holds over a newton
per foot against a case that weighs a quarter of one, and cuts free with a
blade. That is the whole fixing.

**There is no lip any more, and there should not have been one for two
revisions.** It started as the entire fixing — a fin off the plate's rear edge,
down the block's rear face, holding the case by weight and friction. The
silicone feet replaced that, and from then on the fin held nothing; what it
still did was set the datum, pushing the case 2 mm proud of the block's rear
face so a 2 mm fin had room to hang. A feature with no job was deciding where
the whole part went.

It was also in the way of where this is going. Mortised into the block, a
straight-sided pocket in the top face is one cut; a pocket plus a slot down the
outside of the rear face shell is two, the second of them a visible scar on the
face you see from behind, and it gets worse the deeper the case sinks. **The
case's outline in plan is now the outline of the pocket** — 58 × 27, flush at
the back, nothing overhanging and nothing below the block's top face.

**The strain relief is a zip tie cinched on the jacket just outside the rear
wall.** Its head stands about 4 mm proud of a 5.5 mm cable and the notch is
5.3 wide, so it cannot be drawn back through: a pull stops at the wall instead
of reaching the solder joints. A stiff Cat5e pushes about 0.24 N at that corner
and the case weighs 0.25 N, so the tie matters — it is just that it does not
need a lip to pass through.

**When the mortise happens, it will be an open-backed pocket.** The rear face
shell is 31.75 and the case is 27 wide, which leaves 4.75 mm of concrete to
split between the two sides of the pocket. Two walls of 2.4 mm are crumbs, not
walls, so the pocket breaks out at the rear face and the case's own rear face
finishes flush with the block's. Nothing of that is visible from the front, and
it is the easier cut of the two.

**What the AS7341 actually measures.** The block's centre is the open spot
between the two cores, which is why the case is there — but ranunculus clumps
reach 25–35 cm across and meet over the web at around week eight. From then on
the port is under leaves and the reading is **under-canopy light**, not fixture
output. That is a real quantity and the logs are labelled for it; what it is not
is a substitute for the commissioning fit, which is made against a PAR meter
before there is a canopy. If fixture output is what you want to track, that
sensor has to see the fixture, and no position on the block does.

**Before printing, caliper these.** The caliper sheet (an artifact, in inches,
saved as you type) has a row for each. On the AS7341: outline, hole grid and
hole size, the sensor window from the −X and LED edges, the LED from its edge,
and above all the **STEMMA QT socket height** — `SC_AS7341_QT_H`, which sets the
drop. They are scaled off a photo by the header-pad pitch and checked against
Adafruit's published outline; they agree to half a millimetre, which is not the
same as measured. On the BME280 and ADS1115: outline and tallest part only —
neither is located by anything now. Fit no headers to any of the three boards:
a 10-pin header on the ADS1115 stands 13.6 mm tall and the AS7341 hangs at 11.2.


## Colour code and labelling

Fix these now and write them on the inside of the lower cabinet front. An undocumented
colour code is worse than none, because it will be trusted.

| Conductor | Colour |
|---|---|
| +24 V | Brown |
| +12 V | Yellow |
| +5 V | Red |
| +3.3 V | Orange |
| GND (all domains) | Black |
| SDA | Blue |
| SCL | Green |
| 1-Wire data | White |
| PWM / control | Violet |

Ground is black in every domain and the domains share a common ground — do not
invent per-domain ground colours, it reads as isolation that is not there.

**Every conductor gets a label at both ends**, with the same designator used in the
schedule above. Printed heat-shrink is best; a Dymo wrap is acceptable; a Sharpie on
tape is not, because it is unreadable in two years and this piece is meant to outlast
the person who built it.

Then tape a **laminated wiring card** inside the lower cabinet front: the conductor
schedule, the colour code, the I²C address map, the GPIO map. The station should be
debuggable by someone who has not read this repository.

---

## Power distribution — two paths, and V1 takes the first

The bench currently has three wall adapters, which is three cords, three lumps, and
the ugliest thing in the build. There are two ways out, and they carry very different
amounts of responsibility.

### Path A — V1. Commercial supplies, mounted, DC on rail

Keep every mains-to-DC conversion inside its **sealed factory adapter**. Screw a short
power strip to the cabinet floor, plug the three adapters into it, retain each one so
it cannot hang by its plug, and run **one cord to the GFCI outlet**. Distribute only
DC on the DIN rail.

You hand-terminate nothing at mains potential. The look is 90 % of Path B for none of
the risk, and it is the right answer for V1.

### Path B — later. IEC inlet and DIN supplies

One fused, switched **IEC C14 inlet** on the cabinet, feeding DIN-rail supplies
(Mean Well HDR or MDR series in 5 V and 12 V) alongside the PWM-120-24. One cord, no
wall warts, everything on the rail.

This is genuinely better and it is genuinely more responsibility: hand-terminated
mains inside a metal cabinet next to 13 litres of water. If you take it, then insulated
ferrules on every mains conductor, fully enclosed terminals with no exposed metal,
and **protective earth bonded to every metal part of the structure** — frame, mast,
carriage, case, plate. Have someone competent look at it before it is closed up and
before it goes anywhere public.

**The pan is the deliberate exception and it stays floating.** `V1_PHYSICAL_BUILD.md`
is explicit: do not bond the pan to ground, because the i3's isolated slots handle
stray voltage paths and earthing the solution defeats them. Bond the structure; leave
the water alone. If that distinction ever feels arbitrary at 1 a.m., re-read this
paragraph rather than improvising.

### Fuse the DC rails

Not currently specified anywhere. A DIN fuse holder per rail, sized just above the
measured draw: 5 V at the Pi's requirement, 12 V at well under an amp for the fan,
24 V at ~2 A for the measured 1.4 A of LED boards. This piece is meant to run
unattended for months with a plant depending on it.

---

## What to buy

Red-teamed 2026-09-15 against the decisions in this document; the first draft was
both redundant and over-specced. Nothing here blocks a phase; all of it is Phase F
(the enclosure) except the first two lines, which the sensor case needs before it
is printed. Rough figures.

| Item | Approx. | Note |
|---|---|---|
| White acrylic sheet, 1 mm | $8 | The diffuser disc. Etched PTFE does not exist at 1 mm from any stock supplier; acrylic is the alternative any silicone holds |
| Neutral-cure silicone, 20 g tube | $10 | Bonds the disc and casts the three feet. Not acetoxy — it off-gasses acetic acid into a closed box |
| M2.5 × 6 countersunk, M2 × 4 pan | $10 | Two sizes: the plate takes M2.5, the board takes M2 because its own holes are Ø2.29. M2.5 pans from the earlier sheet do **not** substitute — they do not pass the board |
| Acrylic conformal coat, aerosol | $25 | Three boards in a vented box under a warm fixture. Mask the BME280 lid and the AS7341 window with any tape |
| Bootlace ferrule kit + crimper | $25 | Non-negotiable. Buy first |
| 35 mm DIN rail, 12 in, + push-in terminal block kit with end stops and jumpers | $35 | Zone 4 and the four-rail I²C bus, on one rail. Jumper bars make the rails |
| DB-25 solder-cup pair, right-angle hood on the cable end | $12 | One pair. 19 conductors, six spare |
| Arducam CSI-to-HDMI extender pair | $28 | Ships as a set of two, which is one link |
| Waxed lacing twine, 1 spool | $10 | Replaces zip ties behind glass |
| P-clips, nylon, white | $10 | Strain relief, second point, inside the cabinet |
| M2.5 / M2 standoff kit | $12 | The Pi, the DAC, the ESP32 on the back panel |
| Cable glands, assorted | $20 | **Size after the loom exists** |

Roughly **$200**. Struck from the first draft, with the reason: JST-XH kit and crimp tool
(two connectors, both replaced by the bus block); isolated bulkhead BNCs (the i3's own
BNCs, settled 2026-09-12); WAGO 221s (already in the BOM; the DIN blocks are the bus);
sleeving (the only exposed run is white Cat5e already); Kapton (any tape masks a spray);
M3 clinch nuts (they need an arbor press — decide by tool, and rivnuts if there is none);
DIN fuse holders (every rail comes off a supply with its own current limit; revisit when
the rail is built and the draws are measured); M2 heat-set inserts and M2 screws (the
closure is thread-forming M2.5 now). Cat5e, foam tape and PETG are "if not on the shelf".

## Getting out of the mess without a big bang

The bench version is running and `code takes precedence because the bench version is
already running`. Do not tear it down. Convert it a bus at a time, verifying after
each step, so there is never a day where nothing works.

1. **Label what exists, before touching it.** Every conductor, both ends, today. The
   current wiring is only fully understood while it is in front of you.
2. **Build the four-rail I²C bus** on the DIN rail — push-in blocks, jumper bars for
   SDA / SCL / 3V3 / GND — and land every branch in it with a ferrule. The three boards
   in the canopy sensor case daisy-chain on soldered wire inside the case and arrive as
   one Cat5e. Biggest visual win, lowest risk, entirely reversible. `i2cdetect` proves
   it before and after.
3. **Ferrule every screw terminal** on the GPIO breakout. An hour's work.
4. **Build the Zone 4 rail** on the bench as a standalone assembly and swap the power
   over to it in one session. It is the only step with a real down-window.
5. **Populate the case back panel as a sub-assembly** — DAC, ESP32, terminal block on
   the panel, wired and labelled and tested, before it ever goes in the case.
6. **Build the plate assembly separately** and only then marry the two, with the
   service loops dressed in as designed rather than as discovered.
7. **Lace the visible runs last**, once nothing will move again.

Steps 1–3 can happen this week and will change how the bench looks more than
everything after them.

---

## Open items

Things this document raises that it cannot settle.

- **The umbilical is a CAD change.** A side-wall connector cutout does not exist in
  `cad/case.py` and the Ø 0.75 rear grommet pass may be redundant once it does.
  Model before the case blank is cut.
- ~~**The i3's probe termination is unverified.**~~ **Settled 2026-09-12** from the
  datasheet drawings: **three BNCs soldered to the board edge**, one per EZO slot, with
  the circuits on 3-pin headers and a 40-pin pass-through along the top. The probe mates
  directly — nothing to design. It also makes the isolation warning concrete rather than
  theoretical: the barrier sits *upstream* of those BNCs, so bulkheading both through a
  common steel panel bonds the two isolated domains to each other. **Gland the probe
  cables through instead** and let them plug straight into the board.
- **The i3's isolated slot seating is unverified.** Already flagged in `BOM.md` and
  still open. It is the whole basis for striking the inline isolators.
- ~~**"The sensor loom never leaves the cabinet" is no longer true.**~~ **Resolved by
  moving the sensors, not the sentence.** The AS7341, BME280 and ADS1115 now live in a
  printed bar on the block's centre-rear, and the camera lives inside the lightbox. The
  mast carries only fixture services. No sensor is mounted on the mast, and the canopy
  gained no visible hardware.
- **The case flange fixing method** (tapped versus clinch nuts) contradicts what
  `V1_PHYSICAL_BUILD.md` currently specifies. Resolve before the flanges are made.
- **Conductor count is a draft.** Verify against the boards in hand before buying a
  connector.
- **Slack inside the mast bore is not proven.** At the bottom of travel there is ~21 in
  of spare cable inside a 1.37 in bore. This project already has history with something
  jamming in that bore — the counterweight. **Mock it up with the real cables before the
  slot is cut**, and use thin, flexible stock: ultra-slim HDMI, silicone-jacket 18 AWG.
- **Keep drip-line joints out of 34–45 in.** Below the slot the bore is shared between the
  drip line and three electrical runs. A joint that weeps inside a tube full of cable is
  the one failure this arrangement invites.

---

See also: [WIRING_&_BUSES.md](WIRING_&_BUSES.md) (topology, addresses, pin map),
[V1_PHYSICAL_BUILD.md](V1_PHYSICAL_BUILD.md) (the cabinet and the console),
[INSTRUMENT_HEAD_PLANS.md](INSTRUMENT_HEAD_PLANS.md) (the plate and its depth stack),
[BOM.md](BOM.md) (what is bought).
