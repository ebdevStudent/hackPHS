# First test prints — T0, T1, T2 (final)

**Current files:** use [START_HERE.md](START_HERE.md) for all twelve final plates, profiles, replacement parts and the complete ZIP. Print T3 next.

Printer: Monoprice Voxel. Filament: Creality PETG. Slicer: **FlashPrint-MP 3.23.3** (Monoprice's build of FlashPrint, installed in `/Applications`; the app's Info panel may still say 3.23.1). It is an unsigned Intel app that runs under Rosetta. If macOS blocks it, right-click it and choose **Open**.

In FlashPrint-MP, pick printer type **Voxel**. It ships only **Voxel PLA** and **Voxel ABS** materials, with no PETG preset, so choose **Voxel PLA** and override the settings below in **Expert Mode**.

These three files are copies of the generated plates. `SHA256SUMS` records their checksums and where each came from. If the CAD changes, the files are regenerated; don't print an old copy.

| Order | File | What it tests | Time (est.) | Filament |
| --- | --- | --- | --- | --- |
| 1 | `T0_stringing_towers.stl` | Stringing and bed adhesion: tunes your settings | 15–30 min | 1.5 g |
| 2 | `T1_socket_strip_and_rod_jig.stl` | Rod socket fit, M2 screw pilot holes; also the 44.50 / 37.83 mm rod cutting jig | 1–1.5 h | 12 g |
| 3 | `T2_gimbal_fit_coupon.stl` | Bearing seat fit and pin press fit | 1–1.75 h | 13 g |

**Production update — 2026-10-09:** use [print_ready_p1b](../print_ready_p1b/README.md) for current centered production plates and saved FINAL profiles. All T1B/T2 fits are applied; pins are now cut to 11.00 mm. T3 is the next physical section test. The starter profiles below are preserved historical settings.

## Saved Expert Mode profiles — 2026-10-08

All 14 named profiles for T0–T4, H1/H2, G1a/G1b/G2 and the four CAD-kit fixtures are saved in FlashPrint-MP. Choose them in **Print (Expert Mode) → Select Profile**. The [profile guide and backups](profiles/README.md) map every profile to its STL and list the checked settings. T1 and T2 each have their own profile; the earlier shared starter profile remains too.

**Mode correction:** the six-tab window described below is Basic Mode, even with More Options expanded. For first-layer maximum speed, retraction and full controls, use **File → Preferences → Print → Printing Window Type → Expert Mode**. Expert controls are in General (layers, temperatures, speeds, retraction), Perimeter (shell count), Infill (solid layers, density, pattern), Supports, Raft, Additions (brim), Cooling (fan height), and Others (dimensional adjustments). Saved profiles use 235 °C / 1.5 mm as untested starter values; update them after T0. Profiles do not set STL scale or orientation.

## Before each print

**T4 checked file — 2026-10-09:** use [T4_carrier_and_arms_checked.stl](T4_carrier_and_arms_checked.stl), already centered for a 5 mm brim. All four parts, brim and purge fit the Voxel bed in the offline slicer check. Choose **Voxel PETG T4 carrier arms** and override first-layer maximum to **10 mm/s**, brim **on / 5 mm / one layer / 25% speed**; keep 0.20 mm layers, 35 mm/s, three shells and four top/bottom layers. Confirm your successful temperature/retraction settings. Follow the [T4 fit guide](T4_FIT_CHECK.md) for foam reliefs, ≤2.6 mm underside protrusion and actual frame checks. Physical fit and strength are pending.

1. **Dry the filament** if the spool has been open more than a few days: 60–65 °C for 4–6 h.
2. **Clean the bed.** Take the removable Voxel bed out, then either:
   - wipe it with **rubbing alcohol** (isopropyl, 70 % or 91 %); or
   - wash it with **dish soap and warm water**, rinse, and **dry completely**.

   **Don't use hand sanitizer.** Its glycerin and gel leave a slippery film. Don't touch the print area with your fingers.
3. Apply a **thin, even coat of glue stick** over the middle of the bed. Put the bed back, seated flat with no lip, and remove any old blobs.
4. **Load the PETG** (Voxel touchscreen):
   1. **Tools → Filament.** If old filament is in the printer, **Unload** it first.
   2. Choose **Load**. If it asks for a filament type, pick **ABS**: it loads hotter, closer to what PETG needs. PLA is too cool. If it shows a temperature, set **235 °C**.
   3. Snip the PETG tip at an angle, straighten the first ~10 cm, and push it into the top of the extruder until the gears grab it.
   4. Wait until a **steady thread of clean PETG** comes out of the nozzle. Pull it away with tweezers; don't touch the nozzle.
5. **Close the door** and let it heat-soak for 5–10 minutes.
6. In FlashPrint-MP: printer **Voxel** → **Load** the STL. **Don't move, rotate, scale or auto-arrange it**; it is already laid out flat.

## FlashPrint-MP settings, field by field

Click **Print** to open the Print dialog. The six tabs (**Layer Height, Shells, Infill, Speed, Temperature, Others**) are the expanded Basic Mode settings. **More Options >>** shows the rest. Change only the fields listed; leave everything else at its default.

**Top of the Print dialog**

| Field | T0 | T1 | T2 |
| --- | --- | --- | --- |
| Machine Type | Voxel | Voxel | Voxel |
| Material | **Voxel PLA** (no PETG preset exists; the values below override it) | same | same |
| Supports / Raft / Brim | **off / off / off** | off / off / off | off / off / off (brim only if corners lift) |
| Resolution | Standard (the tabs override it) | same | same |

**Tabs**

| Tab → field | T0 | T1 | T2 | Slicer default |
| --- | --- | --- | --- | --- |
| Layer Height → Layer Height | 0.20 mm | **0.15 mm** | **0.15 mm** | 0.18 |
| Layer Height → First Layer Height | **0.27 mm** | 0.27 mm | 0.27 mm | 0.27 |
| Shells → Perimeter Shells | 3 | 3 | 3 | 2 |
| Shells (or Infill) → Top / Bottom Solid Layers | 4 / 4 | 5 / 5 | 5 / 5 | 3 / 3 |
| Infill → Fill Density | 25 % | 25 % | 25 % | 15 % |
| Infill → Fill Pattern | **Hexagon** | Hexagon | Hexagon | Hexagon |
| Infill → Combine Infill | default | default | default | — |
| Speed → Print Speed | **40 mm/s** | **35 mm/s** | **35 mm/s** | 80 (too fast for PETG) |
| Speed → Travel Speed | 100 mm/s | 100 | 100 | 120 |
| Temperature → Extruder Target | **235 °C** | your T0 value | same | ~200 |
| Temperature → Platform Target | **60 °C** | 60 °C | 60 °C | — |
| Others → Cooling Fan Controls | **turn on at a preset height, 0.6 mm** | same | same | on after raft |
| Others → Pause at heights (if shown) | none | none | none | — |

**More Options >>**

| Field | T0 | T1 | T2 | Slicer default |
| --- | --- | --- | --- | --- |
| First Layer Maximum Speed | **15 mm/s** | 15 | 15 | 20 |
| First Layer Maximum Travel Speed | default | default | default | 70 |
| Retraction Length | **1.5 mm** | your T0 value | same | 1.3 |
| Retraction Speed | 30 mm/s | 30 | 30 | 30 |
| Dimension / XY compensation | **off** (default) | off | off | off |

The **First Layer Height is 0.27 mm**, the Voxel's own value. The first T0 attempt at 0.20 mm moved the nozzle against the bed for 3 minutes without extruding.

**Save the profile.** If the dialog offers **Save As / Save profile**, save it as **Voxel PETG** and pick it next time.

Notes for this version:
- There is **no separate first-layer temperature**. If the T0 feet won't stick at 235 °C, use 240 °C for the whole print, the Voxel's maximum.
- There is **no "avoid crossing outlines" option**. Fast travel (100 mm/s) and correct retraction do that job.
- Leave **Dimension / XY compensation off**. The tests measure how your printer really prints holes.

## Slice, send and watch

1. Click **OK** to slice. FlashPrint shows the estimated time and material (T0: about **32 minutes, 0.47 m**), then a **Print** button.
2. Click **Print** only when the PETG is loaded and flowing, the bed is clean with glue stick, and the door is closed.
3. FlashPrint sends the job to the Voxel over **Wi-Fi**. Pick the Voxel if asked; or save the `.gx` file to a USB stick and start it from the touchscreen.
4. The printer heats first: bed 60 °C, nozzle 235 °C. This takes a few minutes.
5. **Watch the first minute of motion.** You should see plastic coming out: a line at the edge, then the parts' first layer, flat and stuck.

## If something goes wrong

| What you see | Do this |
| --- | --- |
| **The nozzle moves or scrapes but nothing comes out** (more than about a minute) | **Cancel.** Reload: Tools → Filament → Load (ABS / 235 °C), and push by hand until a steady thread comes out. Check First Layer Height is **0.27 mm**, re-slice, clear the bed and print again. |
| The filament won't go into the extruder | Unload, snip the tip at an angle, straighten it, and reload while pushing firmly until the gears grab it |
| The filament goes in but nothing comes out of a hot nozzle | Possible clog (from scraping). Push firmly at 235 °C. If it still won't flow, stop and report. |
| It scrapes on **one side** of the bed only | The bed is out of level: run the Voxel's levelling routine (paper test) |
| The first layer curls up or drags | Cancel, add more glue stick, slow the first layer to 10 mm/s, or raise the extruder to 240 °C |
| Lots of strings | See T0 below: lower the temperature and raise retraction, one change at a time |

## T0 — stringing towers (≈20 min)

Look at the gap between the two towers.
- **Fine wisps or nothing:** good. Keep these settings.
- **Many strings:** lower the Extruder Target to 230 °C, then 225 °C, then try 2.0 and 2.5 mm retraction. Change one thing per reprint.
- **Feet lifted or popped off:** more glue stick, a slower first layer (10 mm/s), Extruder Target 240 °C, or turn the brim on.

Use the final settings for T1 and T2.

## T1 — socket strip and rod jig

**Socket strip.** Six stubs; the dots next to each stub (1–6) give the socket size.
1. Push a 1 mm carbon rod into each stub socket by hand, all the way (5 mm deep).
2. Pick the **best stub**: the rod goes in with firm finger pressure, stays put when you shake it, and comes out with a firm pull. The rods are dry-fit, so this stub sets every hub socket. Also note the next looser stub, used for any joint that later needs epoxy.

**Pilot holes.** Three holes in the end block, left to right drawn 1.6 / 1.7 / 1.8 mm. Drive an M2 screw into each. Pick the hole where the screw threads in firmly without cracking the plastic and holds when wiggled.

**Earlier T1 result — superseded by T1B below:** the fourth socket counted from the user's left was too snug, while the third was too loose. These positional descriptions did not establish a diameter; the subsequent T1B dot selections now do.

Follow-up: the user tentatively identifies the snug socket as having **three dots** ("I think"). They report that none of the screws fit; whether they attempted hand threading or only insertion, the screw size actually used, and the failure mode are not yet confirmed. No final diameter is selected from this report.

Later clarification: the user **turned the M2 × 4 mm screw with an Allen key; none would start**. A larger-pilot refinement coupon is prepared below. The socket dimple identification remains tentative.

For the pilot test, use an **M2 × 4 mm socket-head screw** from the supplied assortment, without a nut or washer. The CAD end block is 7 mm tall with holes ending at Z = 2 mm, giving a nominal 5 mm blind-hole depth. Turn the screw slowly by hand; stop for cracking, excessive resistance, or bottoming. Compare the three holes using the same screw size.

**Rod jig.**
1. Cut 3 rods in the 1-dot groove: rod end against the stop wall, blade in the slot, roll to score, then snap.
2. Measure them with calipers. Target **44.50 ± 0.3 mm**.
3. Cut one in the 2-dot groove. Target **37.83 ± 0.3 mm**.

## T1B — socket and screw refinement (prepared 2026-10-09)

Load **[T1B_socket_and_screw_refinement.stl](T1B_socket_and_screw_refinement.stl)**. It contains two strips, with seven rod sockets (1.250–1.400 mm drawn diameters) and seven larger screw pilots (1.80–2.20 mm). The **58 × 35 mm** layout fits comfortably with a 5 mm brim; keep 100% scale and the supplied flat orientation. The old cutting jig is not reprinted.

Use **Voxel PETG T1 sockets**, checking 0.15 mm layers, 0.27 mm first layer, 35 mm/s print speed, **10 mm/s first-layer maximum**, and **5 mm / 1-layer / 25% speed brim**. Keep the temperature, retraction and thin glue coat that worked for T1. Saved starter profiles may still have brim disabled; inspect these fields before slicing.

**User-reported T1B selections — 2026-10-09:** rod socket **#2 = 1.275 mm bore**, M2 pilot **#5 = 2.00 mm**. Saved in [fit_results.json](../fit_results.json). Rod and M2 selections are applied to the current P1B production exports. Thread retention for screw-bearing parts and T3 section strength remain to be qualified. The [T1B guide](T1B_README.md) retains the coupon mapping and test method.

## T3 — ready with socket #2

Load [T3_cage_section_socket_2_checked.stl](T3_cage_section_socket_2_checked.stl), ten hubs centered in two rows of five. Use **Voxel PETG T3 socket 2 FINAL**, 0.15 mm layers, 35 mm/s, three shells, five top/bottom layers and 25% hexagon. The new FINAL profile saves first-layer maximum **10 mm/s** and brim **5 mm / one layer / 25% speed**. Keep successful T1B temperature/retraction, 0.27 mm first layer and 60 °C bed. [Full settings and assembly guide](T3_README.md).

All ten hubs and their brim/purge paths pass geometry and offline bed-fit checks. Do not use the older T3 plate. After printing, assemble nine hubs with ten 44.50 mm rods into the shared-edge hexagon/pentagon and run section tests; the tenth hub is spare.

## T2 — gimbal fit coupon

The dots on top number the columns 1–5 from left to right.
1. **Bearing seats (front face).** Drawn 5.00 / 5.10 / 5.20 / 5.30 / 5.40 mm; they print a bit smaller. Press an MR52ZZ bearing into each with a vise or flat clamp, never a hammer. Pick the seat that **holds the bearing without it falling out and without cracking the plastic**.
2. **Horizontal pin holes (back face) and vertical pin holes (top step).** Drawn 1.85 / 1.95 / 2.05 / 2.15 / 2.25 mm. Press a 2 mm pin into each. Pick the hole in each row that **grips the pin firmly**: it needs a clamp to go in and doesn't turn by hand.
3. Put a pin through a seated bearing and spin it. It should turn freely.

If every hole in a row is too tight or too loose, say so. That is still a useful result: the range gets shifted and only T2 is reprinted.

### Recorded T2 results — 2026-10-09

User-reported preferred fits on the printed coupon:

| Test | Selected dot count | Nominal CAD hole diameter |
| --- | --- | --- |
| Front/lower bearing seat | **4** | **5.30 mm** (5.00 mm bearing OD + 0.30 mm diametral allowance) |
| Back horizontal pin hole | **4** | **2.15 mm** |
| Top vertical pin hole | **5** | **2.25 mm** |

These are the coupon's drawn diameters, not measurements of the printed holes or hardware. **T2 passed by user report — 2026-10-09:** the user confirms that the bearing spins freely on the pin and the selected fits hold securely without cracking. No instrumented retention test or hardware dimensional measurement is implied.

The final P1B generator now applies separate selected diameters according to print orientation: **2.15 mm** for inner X junctions, **2.25 mm** for the arm blocks and pole hubs. Current native CAD and production STLs are regenerated with these fits and the T1B selections. Physical load qualification remains pending.

## Send back (copy, fill in and paste in chat)

```
T0: final nozzle temp ___ °C, retraction ___ mm, stringing (none/light/heavy) ___, feet flat (y/n) ___
T1: best socket stub (1-6 dots) ___, next looser ___, rods slide out when shaken? ___
T1: best pilot hole (1.6 / 1.7 / 1.8) ___, any cracking? ___
T1: three 44.50 rods measured ___ / ___ / ___ mm, 37.83 rod ___ mm, rod diameter ___ mm
T2: best bearing seat (1-5) ___, did any seat crack? ___
T2: best horizontal pin hole (1-5) ___, best vertical pin hole (1-5) ___
T2: bearing spins freely on pin (y/n) ___
Bearing OD / bore / width ___ / ___ / ___ mm, flanged (y/n) ___, pin diameter ___ mm
Anything that looked wrong (warping, stringing in holes, layer gaps) ___
```

Next, the affected CAD parts are updated and regenerated with their checks re-run. **T3 (10 plain three-way hubs) requires the selected T1B rod socket fit, but not the screw-pilot result. T4 (carrier, nut shield and support arms) does not use the T1B socket or screw-pilot parameters and can be printed independently for a frame fit test.** T4 uses M2 clearance holes with nuts; the bearing/pin pivot blocks are on G2, not T4. The full plan, including later steps, is in [`../PRINT_AND_TEST_PLAN.md`](../PRINT_AND_TEST_PLAN.md).
