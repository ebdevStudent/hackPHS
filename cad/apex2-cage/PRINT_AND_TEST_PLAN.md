# Print and test plan — Monoprice Voxel + Creality PETG

**Printing T3 or production parts now? Use the [final package](print_ready_p1b/README.md). Earlier tests and recorded results are in [`print_now/CHECKLIST.md`](print_now/CHECKLIST.md)**, which has exact FlashPrint-MP 3.23.3 settings for the Voxel profile. It has the T0–T2 files, exact FlashPrint settings, the checks and a results form.

**Build decision (user, 2026-10-08): only the gimbal version (P1B) is built.** The fixed cage (P1A) is not printed or flown. Its generator still produces the T1 socket strip and rod jig, which both versions share.

This is the order to print and test the Ball Drone cage. Do the tests in order: each one sets values that the next prints depend on. After each test, send the results (the "Report back" lines) and the CAD is updated and regenerated before you print the next stage.

All settings below are **starting points**, not tested settings for your printer. Adjust them from your first prints.

**Bed limit:** your Voxel's bed reaches **60 °C** (Monoprice's guide says 100 °C, but your printer is the reference). PETG prints at 60 °C, but adhesion needs care: glue stick, a slow first layer, no fan on the first layers, brims, and a closed, heat-soaked enclosure. T1 doubles as an adhesion test. If its parts lift or come loose mid-print, fix adhesion before printing anything else.

## 1. Printer and filament setup

| Item | Setting | Why / source |
| --- | --- | --- |
| Slicer | **FlashPrint-MP 3.23.3** (Monoprice's build; the Voxel only accepts `.gx` files). Full field-by-field settings are in [`print_now/CHECKLIST.md`](print_now/CHECKLIST.md) | [Monoprice Voxel guide](https://monopricesupport.kayako.com/article/283-buyers-guide-voxel) |
| Printer profile | Machine Type **Voxel**, material **Voxel PLA** (no PETG preset), overridden in Expert Mode | — |
| Nozzle temperature | **235 °C** (Extruder Target). FlashPrint-MP has no separate first-layer temperature; use 240 °C for the whole print if adhesion fails. Never above 240 °C, the Voxel's maximum. | Voxel max 240 °C; Creality PETG ~230–250 °C ([Creality table](https://store.creality.com/au/blog/creality-filaments-parameter-reference-table)) |
| Bed temperature | **60 °C** (your Voxel's maximum) | PETG normally prefers 70–80 °C, so adhesion needs the extra steps below |
| Bed surface | Clean with rubbing alcohol, or dish soap and water (rinse and dry); **not hand sanitizer**, which leaves a film. Then a thin, even coat of **glue stick** (or blue painter's tape if glue stick isn't enough) | Glue stick improves grip at 60 °C and stops PETG from welding to the plate |
| Print speed | **35–40 mm/s** (Voxel PLA default 80 is too fast); First Layer Maximum Speed **10 mm/s**; travel **100 mm/s** | A slow first layer is the biggest help on a cooler bed |
| Layer height | **0.15 mm for every FINAL production/profile plate** (historical T0 used 0.20 mm); **first layer 0.27 mm**, the Voxel default (0.20 mm caused no extrusion on the first T0 try) | — |
| Walls / shells | **3** (1.2 mm) | Thin parts print essentially solid |
| Top / bottom layers | **5 / 5 for FINAL profiles** | — |
| Infill | **25 %, Hexagon** (hubs and coupons end up solid anyway) | — |
| Cooling fan | Cooling Fan Controls: **turn on at a preset height of 0.6 mm** (about layer 3) | Fan on early layers cools the bottom and causes lifting on a 60 °C bed |
| Retraction | Start **1.5 mm at 30 mm/s** (the Voxel is direct drive); raise slightly if it strings | — |
| Brim | **On, 5 mm, one layer, 25% speed for all FINAL plates.** | Retains the successful slow first layer; native offline paths verified against the bed |
| Supports / raft | **None** (all parts are designed support-free) | — |
| Enclosure | Keep the door **closed** and let the bed heat-soak **5–10 minutes** before printing | The warm enclosure partly makes up for the 60 °C bed limit |
| First layer | **0.27 mm** at 10 mm/s; watch the first minute and cancel if nothing comes out | Better grip without a hotter bed |
| Loading PETG | Voxel touchscreen: Tools → Filament → Load, choosing **ABS** if asked (PLA loads too cool), or 235 °C; push until a steady clean thread comes out | — |
| Filament | Keep dry. If you hear popping or see heavy stringing, dry it at 60–65 °C for 4–6 hours | PETG absorbs moisture |

When FlashPrint loads a plate STL, keep the arrangement as-is: the parts are already laid out flat and spaced. Do not let it auto-arrange or rotate.

## 2. Print order

| Step | File | Contents / gate |
| --- | --- | --- |
| T0–T2 / T1B | `print_now/` | Historical coupons and successful fit reports; originals preserved |
| **T3 — print next** | [`T3_cage_section_socket_2_checked.stl`](print_now/T3_cage_section_socket_2_checked.stl) | Ten selected #2 hubs; test nine hubs with ten rods |
| T4 | [`T4.stl`](print_ready_p1b/plates/T4.stl) | Actual-frame fit test; independent of T1B sockets |
| H1-01 | [`H1-01.stl`](print_ready_p1b/plates/H1-01.stl) | 25 ordinary hubs; after T3 passes |
| H1-02 | [`H1-02.stl`](print_ready_p1b/plates/H1-02.stl) | 11 ordinary hubs; after T3 passes |
| H2 | [`H2.stl`](print_ready_p1b/plates/H2.stl) | 10 ordinary, 4 mount and 10 four-way hubs |
| G1a | [`G1a.stl`](print_ready_p1b/plates/G1a.stl) | Four inner quarters; confirm M2 #5 grip |
| G1b | [`G1b.stl`](print_ready_p1b/plates/G1b.stl) | Four outer quarters; confirm M2 #5 grip |
| G2 | [`G2.stl`](print_ready_p1b/plates/G2.stl) | Eight junctions, two arm blocks, two pole hubs; selected T2 fits |

All FINAL profiles use 0.15 mm layers, five top/bottom layers, 35 mm/s, 10 mm/s first-layer maximum and 5 mm slow brims. The package supplies all 84 production parts plus ten T3 hubs and optional fixtures. Use FlashPrint estimates for the actual revised layouts; the earlier 8.5–15 hour total was a rough estimate for older settings. About 60.2 g solid PETG is the native production-parts estimate before brims/purge; weigh the output. [Full plate/specification chart](print_ready_p1b/README.md).

**Fit dependencies clarified — 2026-10-09:** T3 contains plain three-way hubs and must use the selected T1B **rod socket** size; it does not use the M2 pilot parameter. T4 contains the carrier, shield and support arms, which use **M2 clearance holes/slots and nuts**, not rod sockets or screw pilots. T4 can be printed independently of T1B for the actual frame fit test. The bearing/pin pivot blocks are on **G2**, so the reported T2 fits do not require changing T4's hole sizes. The sequence above groups preparation tasks; it is not a blanket dependency gate for T4.

## 3. Tests and what to report

### T0 — Stringing and adhesion test (do this first)

PETG strings more than PLA, and the plates have many small parts with lots of travel between them.
1. **Dry the filament first** (60–65 °C for 4–6 hours) if the spool has been open more than a few days. Wet PETG is the main cause of stringing and popping.
2. In FlashPrint-MP (3.23.1, which has no *avoid crossing outlines* option), set **Travel Speed** to 100 mm/s and **Print Speed** to 35–40 mm/s. The Voxel PLA default of 80 mm/s is too fast for PETG.
3. Print the two towers at 235 °C with 1.5 mm retraction. Look at the gap between the towers.
4. If it strings: lower the temperature to 230 °C, then 225 °C (keep 240 °C on the first layer). Then try 2.0 → 2.5 mm retraction. Change one thing at a time.
5. Check the feet stayed flat on the 60 °C bed.

**Pass:** only a few fine wisps that a quick heat-gun pass removes; feet flat.
**Report back:** final temperature and retraction.

**Cleaning fit parts:** trim loose strings and brims carefully. Do not enlarge selected sockets or bearing seats with a drill: that changes the fit being qualified. In particular the selected T1B/T3 socket is 1.275 mm, smaller than the previously suggested 1.3 mm drill.

### T1 — Socket fit strip and M2 pilot holes

1. Cut 3 rods with the jig (see T1b) or cut a few 50 mm test pieces.
2. Push a rod into each of the 6 stubs. Count the dimples: 1 = 0.05 mm clearance per side … 6 = 0.30 mm.
3. Pick the **snuggest stub that the rod enters fully by hand** and that holds the rod when you shake the strip. If you plan to glue the rods, pick one step looser (glue needs room).
4. On the end block, drive an M2 screw into each hole (left → right: 1.6 / 1.7 / 1.8 mm). Pick the one that **bites firmly without splitting the plastic**.

**Pass:** at least one stub fits as described and at least one pilot hole holds a screw. Also check adhesion: the strip and jig stayed flat with no lifted corners or ends.
**Report back:** best stub dimple count; best pilot hole; whether you plan to glue.

**T1B results — 2026-10-09:** the user printed the refinement and selected **rod socket #2 (1.275 mm bore)** and **M2 pilot #5 (2.00 mm)**. Recorded in [fit_results.json](fit_results.json). The T3 plate and complete current P1B exports use rod socket #2. The original rod jig is preserved; physical section qualification remains pending. T3 does not use the screw pilot; accepting a screw does not by itself establish sustained thread retention for later parts.

### T1b — Rod cutting jig

1. Butt a rod against the end stop in the groove with 1 dimple and cut at the blade slot (fine saw or rotary cutting wheel). Wear the respirator: carbon dust.
2. Measure 3 cut rods with calipers.

**Pass:** 44.50 mm ± 0.3 mm (edge rods). The groove with 2 dimples is for the 37.83 mm pole rods.
**Report back:** the three lengths; the rod diameter measured at 2–3 points.

### T2 — Gimbal fit coupon (bearings and pins)

1. Front face: press an MR52ZZ bearing into each of the 5 seats (dimples 1–5 = 5.00 / 5.10 / 5.20 / 5.30 / 5.40 mm as drawn; they print slightly smaller). Pick the seat that **holds the bearing without it falling out, and without cracking the plastic**. Use a vise or flat clamp, not a hammer.
2. Back face (horizontal holes) and top step (vertical holes): press a pin into each hole, 1.85 → 2.25 mm as drawn (left to right = 1 to 5). Pick the hole that **grips the pin firmly** in each orientation.
3. Put a pin through a seated bearing and check it spins freely.

**Pass:** one seat and one pin size work in each orientation.
**Report back:** best seat (dimples); best horizontal pin hole; best vertical pin hole; whether the bearing spins freely.

**Recorded user results — 2026-10-09 — T2 passed by user report:** bearing seat **4 dots → 5.30 mm drawn diameter**; back/horizontal pin hole **4 dots → 2.15 mm**; top/vertical pin hole **5 dots → 2.25 mm**. These are preferred coupon fits, not measured printed diameters. The user confirms free bearing rotation on the pin and secure selected fits without cracking. No instrumented retention test is implied. See the [recorded T2 results](print_now/CHECKLIST.md#recorded-t2-results--2026-10-09). T1B selections are now recorded and all affected P1B CAD/STLs are regenerated. Separate print-orientation pin parameters apply 2.15 mm to inner X junctions and 2.25 mm to arm/pole holders. Loaded retention remains a physical check.

### T3 — Cage section test (after the CAD is updated with T1)

**Ready — 2026-10-09:** use [T3_cage_section_socket_2_checked.stl](print_now/T3_cage_section_socket_2_checked.stl), with the selected 1.275 mm bore. Native Fusion hub generation, exported socket paths, ten flat solids and offline brim/purge bed fit pass. [T3 guide](print_now/T3_README.md) lists settings and evidence. Use the checked centered STL and **Voxel PETG T3 socket 2 FINAL**, which saves 10 mm/s first-layer maximum and 5 mm / one layer / 25% speed brim. Production plates are prepared; start those after the section passes.

1. Print T3 and cut 10 edge rods.
2. Build it **dry, with no glue** (decided: dry fit, bonding only joints that fail). Build **one hexagon and one pentagon that share an edge** (9 hubs, 10 rods), with every hub flat face outward. On a 3-way hub, the two arms 108° apart go along the pentagon.
3. **Pull-out:** hang about **300 g** (a full 300 ml water bottle in a bag) from one rod, with the hub held. It must not slide out within 1 minute.
4. **Stiffness:** support the section on its two far hubs. Hang **100 g** from the middle of one rod and measure how far it sags. Remove the weight and check it springs back fully.
5. **Drop:** drop the section flat from about 30 cm onto a hard floor 5 times. Check for cracked hubs, loose rods or bent rods.
6. **Harder drop (finds the margin):** if step 5 passed, drop it once from **50 cm** (about 3.1 m/s). Record what happens; this is information, not a pass/fail.

**Pass (provisional thresholds):** no pull-out at 300 g; sag under 100 g is less than 3 mm and recovers fully; no damage after 5 drops.
**Report back:** pull-out result; sag in mm; any damage (30 cm and 50 cm); your impression of stiffness. If 1 mm rods are too flexible, the fix is local 1.5 mm reinforcement in the CAD, not a guess.

### T4 — Gimbal carrier fit on the real frame

**Audit — 2026-10-09:** the live Fusion model and exported T4 plate pass mesh, source provenance, nominal screw-path and arm-alignment checks. Use the [centered checked copy](print_now/T4_carrier_and_arms_checked.stl); original shapes and print orientations are unchanged. Offline FlashPrint slicing confirms all four parts, brim and purge fit the bed with at least 7.85 mm conservative clearance. See the [T4 audit and fit guide](print_now/T4_FIT_CHECK.md), including first-layer 10 mm/s and 5 mm brim overrides for the existing saved profile. Actual-frame dimensions remain unmeasured. The current native model includes both frame and arm nuts with foam reliefs checked through their full adjustment travel. Hand-cut those reliefs and verify actual nut/tail/foam clearances. Keep all underside protrusion ≤2.6 mm and check the actual shield/battery separation.

1. Put the M2 frame screws through the frame bottom plate and carrier (nuts underneath).
2. Check the holes line up with the frame's 25.5 mm pattern, and that the frame slides through the slot travel (±2 mm across, ±3 mm along the fore-aft arms).
3. Stick the 3 mm foam pad under the carrier, put the **nut shield** under the pad, and strap a battery underneath. Try both battery sizes.
4. Check the strap threads through the slots and holds the pack firmly, and that you can remove the battery without tools.

**Pass:** holes align; frame adjusts; strap holds both packs; nuts do not touch the battery.
**Report back:** anything that doesn't fit, with measurements.

## 4. Measurements to take when parts arrive

Put them in `measurements.json` (values with units, for example `"motor_diag": "94.6 mm"`), or just send them in chat. Measure with the parts **assembled as they will fly** where noted.

**Aircraft**

| What | Key in `measurements.json` | How |
| --- | --- | --- |
| Motor centre diagonal | `motor_diag` | Centre of one motor shaft to the diagonally opposite one |
| Motor bell diameter / height | `motor_od`, `motor_h` | Calipers; height from the arm top to the bell top |
| Prop diameter | `prop_dia` | Tip to tip |
| Prop **underside** height | `prop_z` | Frame top surface to the lowest point of the prop, motor and prop mounted |
| Prop **top** height | `prop_disk_h` = top − underside | Frame top to the highest point of the prop/hub; enter the difference |
| Frame bottom plate thickness | `frame_t` | Calipers |
| Frame arm width | `arm_w` | Calipers, at the narrowest point |
| Frame centre plate width | `stack_w` | Calipers, across the centre plate |
| Frame column height | `frame_column_h` | Bottom plate top to top plate underside |
| FC mounting hole pitch | `frame_hole_pitch` | Hole centre to hole centre (expected 25.5 mm) |
| Stack height | `stack_h` | Frame top to the top of the AIO stack, dampers fitted |
| Camera body / bracket | `cam_size` | Width of the camera **including its bracket** as mounted (14 or 19 mm) |
| Camera position / tilt | `cam_y`, `cam_z`, `cam_tilt` | Lens centre forward of frame centre; lens centre height above frame top; uptilt angle (also your decision) |
| Camera field of view | `cam_hfov` | Not practical to measure; the published ~160° (Caddx Ant 1.8 mm) is used. Only affects the view check. |
| VTX antenna element | `antenna_len`, `antenna_d` | Length and diameter of the stiff part that sticks out; also say **where it can mount** (frame top plate, rear?) |
| Battery sizes | `batt450_l`, `batt450_w`, `batt450_h`, `batt1100_l`, `batt1100_w`, `batt1100_h` | L × W × H of each pack body (not the leads) |
| Battery leads | (send in chat) | Length of the XT30 lead and balance lead on each pack |

**Cage and gimbal hardware**

| What | Key | How |
| --- | --- | --- |
| Rod diameter | `rod_dia` | Calipers, 2–3 points |
| Strap | `strap_w`, `strap_slot_t` | Width; thickness + 0.5 mm |
| Bearing | `bearing_od`, `bearing_w` | Calipers; also confirm 2 mm bore, no flange, spins smoothly |
| Pin | `pin_d`, `pin_len` | Calipers |

**Test-print results → CAD values** (you can just send the dot counts; they are converted for you)

| Test result | CAD value |
| --- | --- |
| T1 best socket stub (1–6 dimples) | `rod_bore_clear` = 0.05 × dimples mm (one step looser if you will glue) |
| T1 best pilot hole (left/middle/right) | `m2_tap` = 1.6 / 1.7 / 1.8 mm |
| T2 best bearing seat (1–5 dots) | `bearing_seat_clear` = 0 / +0.10 / +0.20 / +0.30 / +0.40 mm |
| T2 best pin hole (1–5), horizontal and vertical | Drawn diameter = 1.85 / 1.95 / 2.05 / 2.15 / 2.25 mm; record each orientation separately. Current `pin_press_d` is shared and must be split if the selected diameters differ |
| T3 pull-out passes at 300 g | Confirms `socket_depth` (5 mm); if rods pull out, depth or bonding changes |
| T0 final temperature / retraction | Recorded for all later prints (not a CAD value) |

**Weights** (in grams; under `masses_g`)

| What | Key |
| --- | --- |
| Bare aircraft, fully built, **without** battery, strap, foam or cage | `bare_aircraft_g` |
| One 450 mAh pack / one 1100 mAh pack | `pack_450_g`, `pack_1100_g` |
| Strap + foam pad + all M2 screws/nuts you will use | (send in chat) |
| 10 M2 screws of each length you use, and 10 nuts, weighed together | (send in chat). Gives the per-piece mass; the CAD assumes 0.20 g per screw, real ones are likely 0.25–0.35 g |
| Printed parts after printing: the hub set, carrier + shield + arms, each ring with its junctions | (send in chat) — calibrates the assumed PETG/rod densities and print mass |
| Finished drone in its cage, with each pack | (send in chat) — the real number against the 175 g limit |

## Settled decisions (user, 2026-10-08)

1. **Pins:** cut the 16 mm stock to **11.00 mm** with the updated `print_ready_p1b/fixtures/pin_cut_gauge.stl` gauge ([cutting method](../kit/decisions-2026-10-08.md)).
2. **Rods:** dry fit; bond only joints that fail T3, the bend test or the contact gate.
3. **Camera tilt:** 20°. Measure the mounted angle; a different angle means regenerating P1B.

## 5. Static thrust test (most important number)

1. Remove nothing; props on. Strap the drone **upside down** to a sturdy block on a kitchen scale, so the props blow upward away from the scale. Keep fingers and loose items clear.
2. Tare the scale with the drone and a fresh 450 mAh pack on it.
3. In a safe open area, arm and go to **full throttle for 2–3 seconds**; read the reading change (it goes negative as thrust pulls up). That is the total static thrust in grams.
4. Repeat 3 times and use the average. Note the battery voltage.

**Target:** at least **2 × all-up weight**. That is about 290–335 g for the gimbal version (2 × 145–167 g). Record it as `thrust_total_g`.

## 6. Tests after the gimbal cage is built

These cannot be done before assembly, and no CAD check replaces them.

- **Ring test (after G1a/G1b/G2):** assemble each ring. Twist it gently by hand: it should not feel floppy or creak at the splices. Spin each pivot: it should turn freely without rubbing at the 0.5 mm pivot gaps. If a ring is floppy, `ring_t` can go from 3 to 4 mm (about +4–5 g).
- **Balance:** with each pack fitted, adjust the slots until the drone hangs level in the gimbal with the motors off, at any cage orientation. Record the slot positions. The CG height is only an estimate in the CAD.
- **First hovers with the rings locked (recommended):** zip-tie both rings to the cage so it flies as a fixed cage while you check hover throttle, balance and control. Then free the rings.
- **Cage drop test with dummy weight (before the drone goes in):** hang a ~110 g dummy weight from the carrier in place of the drone, then drop the whole cage flat onto a hard floor from **10, 20, 30 and 50 cm**. Inspect the inner ring (slots and splices), junctions, pivots and hubs after each drop, and stop at the first damage. The estimate is that flat drops above about 25–35 cm may bend the inner ring ([motion physics §5](../../docs/22-motion-physics.md)).
- **Flight gate (applies to P1B, since no fixed cage is built):** 10 low-energy contacts in a row (about 1 m/s or less) with no damage or prop strike, at least 3 minutes of caged flight with each pack you plan to use, and repeatable manual recovery. Record flight time, damage and any prop marks. After the gate, raise contact speed in small steps and stop at the first damage. Keep to about 1–1.5 m/s near walls and land gently: don't cut throttle above the floor.
- **Rolling test:** on a smooth floor, ease in throttle with gentle tilt; the drone should stay level while the cage rolls. Record blackbox gyro data to catch gimbal-lock twitches ([motion physics §2.3](../../docs/22-motion-physics.md)).

## 7. After the tests

Send the results and measurements. The CAD is then updated, the designs regenerated with every check re-run, and the plates re-exported. Then:
- Print H1, H2, G1a, G1b and G2, then build the **gimbal cage** around the T4 carrier.
- Pass the flight gate on the gimbal build: **10 low-energy contacts in a row with no damage or prop strike, at least 3 minutes of caged flight, and repeatable manual recovery**.
