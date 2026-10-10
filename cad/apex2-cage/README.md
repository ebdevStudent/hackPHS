# Apex-2 ball cage — P1A fixed cage and P1B two-ring gimbal

**Printing entry point:** [print_now/START_HERE.md](print_now/START_HERE.md) links every current STL and saved profile. The complete package and downloadable ZIP are now inside `print_now/`.

**Digital print package finalized — 2026-10-09:** all P1B parts have been rebuilt using the selected T1B/T2 fits in [fit_results.json](fit_results.json): 1.275 mm rod bores, 2.00 mm M2 pilots, 5.30 mm bearing seats, 2.15 mm horizontal and 2.25 mm vertical printed pin holes. Arm/pole pin holes use the vertical value; inner X junctions use the horizontal value. The complete saved Fusion model passes six pin/six bearing axis/depth checks, ring connectivity, 612 sampled motion checks and continuous rigid-CAD clearance checks. Arm nuts and relieved foam are now modeled and included in battery-hardware checks. See [current native evidence](review-2026-10-09-finalization/native-validation.json). Use the [final print package](print_ready_p1b/README.md): seven production plates, all 84 parts, twelve checked plate/profile pairs including T3 and fixtures, and the saved native model. All sixteen ring-splice axes also pass. Physical retention, actual-frame fit, strength and flight remain unverified.

Fusion project **HackPHS Ball Drone** contains two designs:

| Design | Generator | Configuration |
| --- | --- | --- |
| **Apex2 Ball Cage P1A** | [`build_p1a.py`](build_p1a.py) | Fixed cage. **CAD reference only, not built.** It still generates the shared T1 socket strip and rod jig. |
| **Apex2 Ball Cage P1B Gimbal** | [`build_p1b.py`](build_p1b.py) (reuses `build_p1a.py`) | **The build.** Same cage with two gimbal rings. Models three-axis cage rotation around the aircraft; physical rolling remains untested. |

**Build decision (user, 2026-10-08): only P1B, the gimbal version, is built.** P1A is not printed or flown. The flight gate (10 low-energy contacts without damage or prop strike, ≥3 min caged flight, repeatable recovery) applies to P1B itself. Fallback: zip-tie the rings to the cage.

Upstream topology: kert's [Thingiverse 408519](../references/thingiverse-408519/README.md), CC Attribution–Non-Commercial; keep that attribution with any derived part.

**Earlier baseline (2026-10-08, before selected-fit finalization):** Vendor/provisional CAD, regenerated and saved 2026-10-08 with **44.50 mm edge rods (37.83 mm pole rods, 247.85 mm cage)**, the nut shield and the corrected gimbal coupon. The [new geometric review](review-2026-10-08/README.md) proves and fixes a battery-pad/nut collision at P1B adjustment extremes, excludes reference meshes and fixtures from native structure mass, and adds acceptance gates and export provenance. The older [version-7 review](review-2026-10-07/README.md) is historical; its centered prop/camera layout defects were corrected before this review.

**Throttle and motion estimates:** [docs/22-motion-physics.md](../../docs/22-motion-physics.md) (`python motion_physics.py`).

**Printing the first tests now: [print_now/CHECKLIST.md](print_now/CHECKLIST.md)** (T0–T2 files, settings, results form).

**Start here: [PRINT_AND_TEST_PLAN.md](PRINT_AND_TEST_PLAN.md)** — Voxel + Creality PETG settings, print order, test procedures and what to measure.

**Physical acceptance is pending.** Print fit coupons first. The final 1 mm running gap gives **0.86–0.91 mm** local radial reserves in ideal rigid CAD; loaded clearance remains a physical check. The 1100 mAh P1B accounted estimate is **166.68 g** (with the nut shield), excluding unweighed items. Strap routing, battery removal, wiring, fits, stiffness, weight and thrust are unverified. No fixed cage is built, so the first flights are on the gimbal build. Recommended: fly the first hovers with the rings zip-tied.

## Inputs and how values are applied

1. Parameter defaults are in the generators. Comments start `TARGET`, `MEASURE`, `FIT COUPON`, `DESIGN`, `DERIVED` or `ASSUMED`.
2. [`vendor_specs.json`](vendor_specs.json) is applied next. It holds published listing values (every Amazon page read in full) and labelled provisional estimates (centre plate ~33 mm, prop envelope 8.9–14 mm, strap 2 mm, thrust), with sources.
3. [`measurements.json`](measurements.json) supplies delivered-hardware dimensions and masses; fill it in, then re-run.
4. [`fit_results.json`](fit_results.json) applies coupon-selected print compensation after hardware inputs. The rod-bore expression references the hardware diameter so the selected 1.275 mm bore is preserved. Update selected fits here when another physical test changes them.

Both generators keep existing Fusion user parameters. To change a design value in an existing document, edit it in **Modify → Change Parameters** and re-run.

## P1A fixed cage (CAD reference only, not built)

| Fusion component | Content |
| --- | --- |
| `Aircraft envelope (PLACEHOLDER)` | Frame (33 mm centre), motors, four full prop disks, stack, camera and 160° view cone, rear VTX antenna element, 450 mAh (shown) and 1100 mAh (hidden) packs. Frame top at Z = 0 at the cage centre; forward is +Y. |
| `Cage skeleton (scaled 408519)` | Truncated icosahedron, pentagons on ±Z, 90 edge rods + 10 pole rods, hub-centre wireframe sketch. |
| `Cage hubs (stage 4)` | One printable part per unique arm layout, placed at all 62 nodes. |
| `Carrier and supports (stage 5)` | Carrier plate, two support arms and two X brackets. |
| `Socket fit strip`, `Rod cutting jig` | Test and tool parts, 200–240 mm in front of the cage. |

**Aircraft mount:**
- The frame screws into ±5 mm fore-aft slots in the carrier; the carrier slides ±4 mm sideways on the arms.
- The battery strap threads through two slots beside the pack, outboard of the frame screws. The pack slides fore-aft under the strap.
- A rear sleeve holds the VTX antenna upright behind the frame, clear of the props.
- Each support arm runs along ±X between the props to an X bracket. The bracket screws onto bosses on the two hubs of that equator edge (x = ±119 mm). Removing four screws frees the aircraft.

## P1B two-ring gimbal

**Kinematics (revised 2026-10-07 after the Fusion review):** cage ↔ outer ring on the cage poles (Z); outer ring (XZ plane) ↔ inner ring on X; inner ring (XY plane) ↔ aircraft on **Y (fore-aft)**. All three axes pass through the cage centre.
- The modeled ring layout leaves the camera centreline clear at the nominal pose. The inner ring's front pivot stays below the lens centreline, and the outer ring stands side to side.
- With the gimbal turning freely, a ring crosses the lens centreline in **8/324 (2.47%)** of tested joint-angle pairs (not a flight-time probability).

**Pivots:** MR52ZZ bearings (2 × 5 × 2.5 mm, ABEC-1) on 2 mm stainless dowels pressed into the other part. Each pin and bearing is modelled inside the group that carries it.

**Fusion motion:** the cage is grounded. Each moving group (outer ring, inner ring, aircraft side) is a rigid group. Three as-built revolute joints are named *Z pole pivot*, *X pivot* and *Y pivot*: drag a ring or use **Drive Joints** to move it.

**Balancing travel (P1B):**
- ±2 mm across (frame slots in X);
- ±3 mm along the fore-aft arms (carrier slots);
- ±5 mm vertical (pivot-block slots).

The ring radii are derived from the aircraft's swept radius at every travel extreme plus 4 mm. The aircraft is raised 3.3 mm so the estimated 450 mAh CG sits on the pivots; the 1100 mAh pack needs 3.6 mm more, which the slots cover.

**Shared with P1A:** the cage and hubs (the pole hubs gain pin bosses), the carrier type (P1B variant with fore-aft arm slots and a 48 mm centre) and a foam battery pad (P1A: 19.88 mm wide; P1B: 15.88 mm wide to clear laterally moving frame nuts). In P1B the VTX antenna mounts on the frame top.

## Printed parts and plates

**Use [print_ready_p1b/](print_ready_p1b/README.md) for the physical build.** Its centered plates have checked 5 mm brims and purge paths. The following `plates_p1b` files are intermediate raw layouts; do not treat their ≤140 mm body footprint alone as a brim check. Earlier part-mass estimates below are reference values; current native volumes and oriented replacements are in the final manifest.

Raw plates are ≤140 × 140 mm for the Monoprice Voxel. For the P1B build, every plate is in `plates_p1b/` (`python make_plates.py p1b`), plus T1 from `plates/` (`python make_plates.py`). That includes its own hub plates (`p1b_plate_hubs_3way_a`, `p1b_plate_hubs_mixed`) and section test (`p1b_plate_T_cage_section_test`). The P1A-only plates (`plate_2`, `plate_3`, `plate_4`, `plate_T`) are not needed. All exported meshes are watertight. Each hub touches the bed with only ~42 mm²: use a brim.

The two mass columns are a solid upper bound and an estimate at 1.2 mm walls + 25 % infill. They come out equal because every part is thin enough to print essentially solid.

| Part | Qty | Mass each | Configuration | Print / notes |
| --- | --- | --- | --- | --- |
| `socket_fit_strip` | 1 | 4.6 g | test | Plate 1. Stubs with 1–6 dimples = 0.05–0.30 mm socket clearance per side. End-block holes left→right = 1.6/1.7/1.8 mm M2 pilot. |
| `rod_cutting_jig` | 1 | 7.5 g | tool | Plate 1. 1 dimple = 44.50 mm edge rods (×90); 2 dimples = 37.83 mm pole rods (×10). |
| `gimbal_fit_coupon` | 1 | 12.9 g | test (P1B) | `p1b_plate_0`, 47 × 22 × 13 mm. Front: bearing seats 5.00/5.10/5.20/5.30/5.40 mm (1–5 dimples). Back face and top step: 1.85/1.95/2.05/2.15/2.25 mm pin press holes. Ranges sit above nominal because FDM prints small holes undersize, horizontal and vertical, separated by a 2 mm wall so each hole tests its full 6 mm depth. |
| `hub_3way` | 46 | 0.27 g | both | Flat outer face down; narrow 1.6 mm keels; 5.5 mm tall; no supports. |
| `hub_3way_mount_A` | 4 | 0.66 g | both | Boss for the P1A brackets. Harmless in P1B and allows swapping back. |
| `hub_4way` | 10 | 0.33 g | both | Pentagon nodes next to the poles. |
| `hub_pole_5way` / `hub_pole_5way_pivot` | 2 | 0.38 / 0.59 g | P1A / P1B | The P1B version has the inward pin boss. |
| `carrier_plate` | 1 | 4.61 / 6.12 g (P1A / P1B) | both (variant per design) | 2.5 mm with a centre window. P1A: side arms and rear antenna sleeve. P1B: fore-aft arms and 48 mm centre. The pack sits on a 3 mm foam pad clear of the M2 nuts. |
| `nut_shield_plate` | 1 | 1.59 g | both | 0.8 mm PETG plate between the foam pad and the pack. The nominal uncompressed gap is 0.4 mm at ≤2.6 mm metal protrusion; verify the compressed stack and fastener pressure on actual hardware. The strap wraps pack and shield together. Print flat. |
| (test) | 10 hubs | — | `plate_T_cage_section_test` | 10 × `hub_3way` for the cage-section test (one hexagon + one pentagon). Reuse them in the cage if they pass. |
| `support_arm` + `x_bracket` | 2 + 2 | 3.1 + 2.8 g | P1A | Plate 4; bracket laid flat. |
| `support_arm_p1b` + `arm_pivot_block` | 2 + 2 | 1.77 + 2.20 g | P1B | Arms run fore-aft. The pivot block prints with the boss vertical. |
| `outer_ring_quarter` + `inner_ring_quarter` | 4 + 4 | 1.92 + 1.73 g | P1B | All 4 of each ring on one plate, nested diagonally: `p1b_plate_inner_ring_4_quarters` and `p1b_plate_outer_ring_4_quarters`, with ~5.2 mm between quarters. Brim recommended. Bands 5 × 3 mm with lightening slots. |
| `outer_junction_Z_bearing` | 2 | 2.00 g | P1B | Face-down. Slim post reaching to the pole-hub pin. |
| `outer_junction_X_bearing`, `inner_junction_X_pin`, `inner_junction_Y_bearing` | 2 each | 1.20 / 1.22 / 0.92 g | P1B | Face-down. One M2 per splice side. |

**Rods:** 90 × 44.50 mm + 10 × 37.83 mm of 1 mm carbon, about 12 of the 400 mm sticks.

**Hardware:**
- P1A: 16 × M2.
- P1B: 28 × M2 (16 splice + 12 carrier/arm), 6 × MR52ZZ, and six 2 × 16 mm stock pins. The final CAD uses **11.00 mm cut pins**, with 6 mm engagement, 1 mm running gap, 2.5 mm bearing and 1.5 mm tip beyond the bearing. The final gauge follows that stack. Uncut 16 mm stock is not the final geometry.

## Recorded checks — 2026-10-08 (vendor/provisional geometry; no flex)

| Check | P1A | P1B |
| --- | --- | --- |
| Maximum XYZ outside span | 247.85 mm (rod length 44.50 mm drives it) | 247.85 mm |
| Rod solids / placed hubs | 100 / 62 | 100 / 62 |
| Unexpected static interference | 0 across 75 selected bodies | 0 across 103 selected bodies; six intended press fits, 1.837832 mm³ each |
| Battery/nut clearance | 1100: 0.40 mm; 450: 2.28 mm | 1100: 0.40 mm; 450: ≥0.47 mm, including frame-slot endpoints |
| Foam/nut clearance throughout frame travel | 0.50 mm | ≥0.50 mm after pad-width correction |
| Prop/support travel | 64 tests; ≥7.40 mm conservative boundary separation | 128 tests; ≥2.51 mm conservative boundary separation (sampled solid distance ≥8.06 mm) |
| Prop/cage continuous bound | ≥34.55 mm at all allowed X/Y positions | Props within 79.69 mm radius (incl. nut shield); ≥4.31 mm to inner structure, ≥33.73 mm to the innermost cage point (pole boss tip at 113.42 mm) |
| Gimbal sweep | — | 612 discrete collision checks: 0; separate continuous radial bounds for modeled bodies |
| Printed inner/outer structure continuous radial reserve | — | ≥0.321 mm, including junctions; ring-band gap alone is 5 mm |
| Printed outer/cage structure continuous radial reserve | — | ≥0.359 mm, including pole posts/bosses; ring-band-only budget is 16 mm |
| Camera centreline | Cage-wide view remains partially obstructed by rods/hubs | Nominal rings clear; 8/324 sampled angle pairs blocked (2.47%), verified with thin-ray BRep intersections |
| Connectivity | Fixed mount geometry | Eight junctions contact two quarters each; six pins engaged and through seated bearings |
| Fusion joints | Fixed configuration | Three origin-centred revolute joints, four rigid groups including cage; eight driven configurations pass and reset |
| Native Fusion structure mass | 40.73 g | 67.62 g, including modeled pin/bearing solids; unmodeled screws and aircraft are excluded |
| Materials | PETG/carbon; near-zero-density analysis, fixtures and reference copies | Plus 304 pins and a 440C density proxy for bearing placeholders (actual alloy not verified) |
| Added-structure estimate | 44.73 g | 72.47 g; solid PETG plus assumed rods/hardware |
| Export/plate audit | 9 parts + 4 plates | 14 parts + 4 plates; all 31 files closed, finite, consistent winding |

The continuous checks use rigid nominal geometry. Sphere containment includes printed junction protrusions; pins/bearings are coaxial, checked separately through connectivity and driven-joint interference. Face bounds prove that continuous balancing travel cannot take a prop through a support boundary. These checks exclude wire/strap routing, print variation and load deflection. The near-zero-density material leaves <0.002 g of analysis mass, rather than mathematical zero.

The nominal 5.05 mm bearing seat around a 5.00 mm bearing is a **clearance fit** (0.025 mm radial); a physical press/retention fit is not established. Use the coupon. The nominal cage-face polygon spans are about 85 mm hexagon / 68 mm pentagon; actual free openings depend on rods and hubs. Test the intended contact objects.

## Weight and thrust (user ceiling: 175 g all-up)

The bare-aircraft listing sum is **44.78 g**, excluding unweighed items. The table uses solid PETG, assumed rod density and approximate hardware allowances. It is an **accounted estimate**, not a complete all-up measurement or upper bound. Extra wiring/connectors, antenna, strap, foam, actual screw/washer/nut choices, adhesive and print variation remain to be weighed. Some supplied motor/frame masses may already include their own wires/fasteners; weigh the defined bare assembly to avoid double counting.

| Configuration | Accounted estimate | T:W at 350 g planning thrust | At 280–400 g estimated thrust | Remaining to 175 g |
| --- | --- | --- | --- | --- |
| P1A + 450 (26 g listing) | 117.08 g | 2.99 : 1 | 2.39–3.42 | 57.92 g |
| P1A + 1100 (48 g listing) | 139.08 g | 2.52 : 1 | 2.01–2.88 | 35.92 g |
| P1B + 450 | 144.68 g | 2.42 : 1 | 1.93–2.76 | 30.32 g |
| P1B + 1100 | 166.68 g | 2.10 : 1 | 1.68–2.40 | **8.32 g** |

These include the 1.59 g nut shield (added 2026-10-08 after the independent verification). Actual mass must pass **≤175 g separately for both packs**; the P1B/1100 estimate leaves **8.32 g** for unweighed extras. No physical mass or thrust pass is claimed. The bearing allowance is 0.20 g each, while the solid modelled steel bearing placeholder is about 0.32 g each; using the solid hardware volumes adds about 0.7 g. This is an estimated scenario, not a weighed result.

### P1B build (the one being built): breakdown and realistic all-up estimate

| Group | Mass | Basis |
| --- | --- | --- |
| Aircraft (vendor listing sum) | 44.8 g | Excludes antenna, receiver wiring, XT30 lead, screws, heat-shrink and strap |
| Cage: 62 hubs + 100 carbon rods | 24.8 g | Hubs 19.5 g (solid PETG) + rods 5.3 g |
| Gimbal rings: 8 quarters + 8 junctions | 25.3 g | 14.6 + 10.7 g |
| Mount: carrier, nut shield, 2 arms, 2 pivot blocks | 15.7 g | 6.12 + 1.59 + 3.54 + 4.44 g |
| Hardware allowance in the generator | 8.4 g | 6 × MR52ZZ at 0.20 g, 6 cut pins at 0.26 g, 28 M2 screws at 0.20 g |
| **Accounted total + 450 / + 1100 pack** | **144.9 / 166.9 g** | Listing pack masses 26 / 48 g |

**Not yet counted:**

| Item | Likely extra | Why |
| --- | --- | --- |
| Real M2 screw mass | ~+2 g | Stainless M2×4–10 socket heads are about 0.25–0.35 g each, not 0.20 g |
| M2 nuts and washers | up to ~+2 g | About 0.15 g per nut and 0.04 g per washer; none counted |
| Strap, foam pad, XT30 lead, VTX antenna, extra wiring | ~+5–10 g | Not in the vendor aircraft sum |

**Realistic all-up estimate:**
- **450 mAh: about 154–160 g**, under the 175 g limit.
- **1100 mAh: about 176–182 g**, likely 1–7 g over the limit unless weight is saved.

These are estimates; weigh the real parts.

**Hardware masses (standard catalog sizes, not weighed):**

| Part | Each | Qty | Total |
| --- | --- | --- | --- |
| MR52ZZ bearing | ~0.2 g | 6 | ~1.2 g |
| 2 mm steel pin, full 16 mm | ~0.4 g | 6 | ~2.4 g |
| 2 mm steel pin, cut to 11.00 mm | ~0.26 g | 6 | ~1.6 g |
| M2 stainless screw | ~0.25–0.35 g | 28 | ~7–9 g |
| M2 nut | ~0.15 g | up to 12 | up to ~1.8 g |
| M2 washer | ~0.04 g | as needed | — |

**Ways to save weight, mainly for the 1100 mAh pack (untested; not planned, because the user decided not to lighten P1B, decision 5 below):**
- **Nylon M2 screws on the 16 ring splices** (~0.04 g each): about −4 g. Check that they hold in the PETG pilot holes from T1.
- **The shortest screw that works:** M2×6 instead of M2×10 saves about 0.07 g each.
- **Cut the pins to 11.00 mm:** about −0.8 g.
- **A lighter strap**, and short leads.

Keep **steel screws on the carrier, frame and arms**.

**Glue** adds mass only where a joint is bonded (decision 3 below: dry fit by default), at about 5–10 mg per rod end.

The lightening choices (narrower hub keels, windowed carrier, 5 × 3 mm ring bands, one screw per splice side and slim pole post) require stiffness and retention tests. Ground rolling force, friction and thrust requirements have not been validated; CAD revolute freedom does not establish rolling performance.

## Assembly guide

**Both configurations:**
1. **Test first.** Print plate 1 (and `p1b_plate_0` for the gimbal). Push a cut rod into each fit-strip socket and pick the snuggest one that seats without force. Try an M2 screw in each pilot hole. For the gimbal, press a bearing into each seat and a pin into each hole. Record hardware measurements in `measurements.json` and coupon-selected fits in `fit_results.json`; final P1B uses separate horizontal/vertical printed pin values. Current selections are already applied. Qualify T3 and actual screw retention before full batches.
2. **Cut rods** with the jig: 90 × 44.50 mm and 10 × 37.83 mm, plus spares. Wear the respirator for carbon dust and lightly sand the ends.
3. **Hub placement.** Every hub mounts flat face **outward**. On a 3-way hub, the two arms 108° apart run along a pentagon edge.
   - Pole hubs go at ±Z.
   - `hub_4way` ×10 go on the corners of the two pentagons around the poles.
   - `hub_3way_mount_A` ×4 go at the ends of the rods crossing the equator at ±X, bosses inward.
   - `hub_3way` goes everywhere else.
4. **Build caps and rings.** Start at the bottom pole: pole hub, 5 pole rods, five 4-way hubs, then the pentagon rods. Work upward ring by ring, closing each pentagon, until the top cap closes. Use the `cage_wireframe` sketch as the map. Bond only if the dry fit is loose, and record bonded joints as non-serviceable units.
5. **Aircraft on the carrier.** Choose the M2 screw/washer/nut stack and confirm ≤2.6 mm underside protrusion, then stick the 3 mm foam pad under the carrier, and thread the battery strap through its slots. Screw the frame to the carrier. Mount the VTX antenna: P1A in the rear carrier sleeve, P1B upright on the frame top.

**P1A (not built; kept for reference):**

6. Screw a support arm to each carrier end (M2 + nut, X slots), each arm flange to an X bracket, and each bracket to its two mount-hub bosses (self-tapping M2).
7. Slide the frame and carrier to centre the CG with the chosen pack, then tighten. With props off, rotate the assembly by hand and confirm nothing approaches a prop disk.

**P1B:**

6. **Pins:** cut and deburr six 2 mm stock pins to **11.00 mm**, check with calipers and the final pin-cut gauge. The final stack has 6 mm press engagement, 1 mm running gap and 1.5 mm past each 2.5 mm bearing. Install pins into:
   - both arm pivot blocks;
   - both `inner_junction_X_pin`;
   - both `hub_pole_5way_pivot` bosses.
7. **Bearings:** use the fit/retention result from the coupon to seat MR52ZZ bearings into both `inner_junction_Y_bearing`, both `outer_junction_X_bearing` and both `outer_junction_Z_bearing` seats.
8. **Inner ring:** screw the four inner quarters to the four inner junctions (Y bearing junctions front and back, X pin junctions left and right), one M2 per splice side. Do the same for the outer ring (X bearing junctions left and right, Z junctions top and bottom).
9. **Aircraft into the inner ring:** fit the arm pivot blocks to the fore-aft arm flanges through their slots, loosely. Slide the pins into the inner-ring Y bearings (front and back) while closing the last inner quarter around the aircraft.
10. **Inner into outer:** close the outer ring around the inner ring so the inner X pins enter the outer X bearings.
11. **Into the cage:** assemble the cage around the rings so the pole-hub pins enter the outer Z bearings. Leave one cap open until the rings are in, then close it.
12. **Balance:** with each pack, adjust the pivot-block slots (height), the frame slots (lateral X) and the carrier slots (fore-aft Y) until the aircraft hangs level and stays put at any angle. Then spin each ring by hand to check free movement and prop clearance with the props off.

## Settled decisions (user, 2026-10-08)

Details and reasoning: [`../kit/decisions-2026-10-08.md`](../kit/decisions-2026-10-08.md).

| # | Question | Decision |
| --- | --- | --- |
| 1 | Battery | Both packs are used. Estimated P1B CG is centred for 450 mAh; the estimated 3.6 mm shift for 1100 mAh is inside the ±5 mm slots. Actual balance is pending. |
| 2 | Pins | **Cut the 16 mm stock to 11.00 mm**, as modelled, using the printed pin-cut gauge and the cutting method in the decision note. |
| 3 | Rod bonding | **Dry fit.** Bond (J-B Weld ClearWeld epoxy) only joints that slip or pull out in T3, the bend test or the contact gate, and record which. Glued rods are not removed: cut the rod and replace the hub (spares from T3), or drill the stub out by hand with a 1.0–1.2 mm bit in a pin vise. Heat and acetone soften PETG. |
| 4 | Camera uptilt | **20°**, the angle the P1B centreline check passed. Measure the mounted angle and enter it as `cam_tilt`; a different angle needs P1B regenerated. |
| 5 | Lightening | **P1B is not lightened.** It keeps the current design with both packs. The weight-saving options above stay available if weighing shows it is needed. |

## Still to measure

Frame/motor/prop positions, plate/top-plate dimensions, camera/bracket location and chosen tilt, prop hub and assembled prop height, nut/washer/screw-tail dimensions, battery dimensions and leads, strap thickness/routing/closure, antenna length/retention, full 3D CG per pack, loaded clearances and **static thrust**. Verify battery removal and cable slack through motion, qualify bearing/pin retention, and load-test representative 1 mm rod/hub and ring/splice sections. Also weigh the bare aircraft, each pack and the printed parts. Enter the values in [`measurements.json`](measurements.json) and re-run both generators.

## Regenerate

Run the generator from **Utilities → Scripts and Add-Ins** (or the Fusion MCP loader, which sets `__file__`) in its own design. Each run rebuilds only its generated components, re-exports STLs (`exports/`, `exports_p1b/`) and prints the checks. Then run `make_plates.py` for each configuration. It requires current generator manifests, rejects stale/missing/changed exports, uses only the selected design folder, and records source hashes/orientations in each plate manifest. Validation failures raise an error; do not treat partial files from a failed run as accepted. Reference meshes load from `~/Downloads/Spherical Drone - 408519 - part 1 of 2/files` if present.
