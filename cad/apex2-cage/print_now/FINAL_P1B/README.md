# P1B final print package — 2026-10-09

**Start with T3.** The selected fits are applied throughout the saved P1B Fusion model and all production parts. This package contains seven production plates, **84 parts in 14 unique designs**, plus T3 and four fixture plates. Digital checks pass; physical section strength, screw retention, actual-frame fit and flight acceptance remain pending.

Use the STL in `plates/` and its matching **Voxel PETG FINAL …** profile. Profiles are installed in `/Users/devk/.FlashPrint-MP/slice_profile/` and backed up in `profiles/`; Qt readback verifies their settings. If a new name is absent in an already-open dialog, reopen the dialog or import the `.profile`. Keep **100% scale, supplied orientation and arrangement**. Slice in FlashPrint with **Voxel** selected to produce the printer job. The files in `checks/` are offline diagnostics with generic startup, not printable Voxel jobs.

The original named profiles remain available. The T3-only equivalent is `../T3_cage_section_socket_2_checked.stl` with **Voxel PETG T3 socket 2 FINAL**.

## Plate chart

Print T3 first; T4 can be checked independently for frame fit. Start the full cage batches after the T3 section passes. Before assembling G1/G2, confirm M2 pilot #5 grips securely and the T2 bearing/pin fits retain under load. The rings, carrier and adapters are production candidates, not flight-qualified parts.

| Plate | File | Contents | Footprint × height (mm) | Minimum sliced edge clearance | Profile |
| --- | --- | --- | --- | --- | --- |
| H1-01 | [H1-01.stl](plates/H1-01.stl) | hub_3way × 25 | 112.29 × 115.81 × 5.48 | 10.74 mm | Voxel PETG FINAL H1-01 |
| H1-02 | [H1-02.stl](plates/H1-02.stl) | hub_3way × 11 | 112.29 × 64.68 × 5.48 | 13.48 mm | Voxel PETG FINAL H1-02 |
| H2 | [H2.stl](plates/H2.stl) | hub_3way × 10, hub_3way_mount_A × 4, hub_4way × 10 | 124.06 × 115.81 × 8.88 | 7.59 mm | Voxel PETG FINAL H2 |
| G2 | [G2.stl](plates/G2.stl) | inner_junction_X_pin × 2, inner_junction_Y_bearing × 2, outer_junction_Z_bearing × 2, outer_junction_X_bearing × 2, hub_pole_5way_pivot × 2, arm_pivot_block × 2 | 111.38 × 121.54 × 16.00 | 7.84 mm | Voxel PETG FINAL G2 |
| T4 | [T4.stl](plates/T4.stl) | carrier_plate × 1, nut_shield_plate × 1, support_arm_p1b × 2 | 98.00 × 102.00 × 16.00 | 17.60 mm | Voxel PETG FINAL T4 |
| G1a | [G1a.stl](plates/G1a.stl) | inner_ring_quarter × 4 | 109.29 × 109.29 × 3.00 | 13.98 mm | Voxel PETG FINAL G1a |
| G1b | [G1b.stl](plates/G1b.stl) | outer_ring_quarter × 4 | 119.29 × 119.29 × 3.00 | 8.97 mm | Voxel PETG FINAL G1b |
| T3 | [T3.stl](plates/T3.stl) | hub_3way × 10 | 112.30 × 39.12 × 5.48 | 13.48 mm | Voxel PETG FINAL T3 |
| KIT-bend_test_block | [KIT-bend_test_block.stl](plates/KIT-bend_test_block.stl) | bend_test_block × 2 | 46.00 × 10.00 × 9.00 | 45.60 mm | Voxel PETG FINAL KIT-bend_test_block |
| KIT-bend_test_jig | [KIT-bend_test_jig.stl](plates/KIT-bend_test_jig.stl) | bend_test_jig × 1 | 76.20 × 30.60 × 13.00 | 30.50 mm | Voxel PETG FINAL KIT-bend_test_jig |
| KIT-load_hook | [KIT-load_hook.stl](plates/KIT-load_hook.stl) | load_hook × 1 | 2.00 × 5.00 × 6.00 | 66.10 mm | Voxel PETG FINAL KIT-load_hook |
| KIT-pin_cut_gauge | [KIT-pin_cut_gauge.stl](plates/KIT-pin_cut_gauge.stl) | pin_cut_gauge × 1 | 24.00 × 10.00 × 18.00 | 56.60 mm | Voxel PETG FINAL KIT-pin_cut_gauge |

H1 is split into 25 and 11 hubs to leave room for brims. H2 includes the other ten ordinary hubs, four mount hubs and ten four-way hubs; the two pole hubs are on G2. T3 adds ten hubs beyond the complete 84-part inventory. Passing T3 hubs can be reused, or kept as spares. The printed fixture parts are not mounted on the aircraft.

**Time:** use FlashPrint's estimate after slicing each final plate. Earlier estimates for the raw layouts and 0.20 mm rings do not establish times for these 0.15 mm / slow-brim plates. Native solid-PETG production estimate is about 60.2 g, excluding brims, purge and fixtures.

## Saved settings — every FINAL plate

| Setting | Value |
| --- | --- |
| Printer / material | Monoprice Voxel / PETG |
| Layer height / first layer | 0.15 / 0.27 mm |
| Shells / top / bottom | 3 / 5 / 5 |
| Infill | 25%, Hexagon |
| Print / first-layer maximum / travel | 35 / 10 / 100 mm/s |
| Brim | On, 5 mm, one layer, 25% speed (8.75 mm/s requested; diagnostic engine uses up to 10 mm/s) |
| Nozzle / bed | 235 / 60 °C starter; retain your successful T1B nozzle temperature |
| Retraction | 1.5 mm at 30 mm/s starter; retain successful T1B values |
| Fan | Off until 0.6 mm, then on |
| Supports / raft / XY compensation | Off / off / off |
| Model | 100% scale; keep supplied flat bases and orientations |

Use the bed preparation that succeeded on T1B. Check adhesion at the start. Ring-quarter brims can merge in the nested layout; remove connecting brim material after cooling without altering ring ends or screw holes. Part bodies remain separate. Check the FlashPrint preview after any change to material settings or arrangement.

## Selected interfaces

| Interface | Drawn dimension | Evidence / affected parts |
| --- | --- | --- |
| Carbon rod sockets | **1.275 mm**, 5 mm deep | T1B #2; all hub types |
| M2 screw pilots | **2.00 mm** | T1B #5; ring quarters and mount-hub bosses; grip when tightened still needs confirmation |
| M2 clearance passages | **2.30 mm** | Junction splices, carrier/arm slots and flange paths; use screws and nuts where specified |
| MR52ZZ seats | **5.30 mm**, 2.5 mm seating | T2 front #4; all three bearing-junction types |
| Horizontal printed pin hole | **2.15 mm**, 6 mm press depth | T2 back #4; `inner_junction_X_pin` |
| Vertical printed pin hole | **2.25 mm**, 6 mm press depth | T2 top #5; `arm_pivot_block` and `hub_pole_5way_pivot` |
| Metal pins | Six 2 mm pins cut to **11.00 mm** | 6 mm press + 1 mm running gap + 2.5 mm bearing + 1.5 mm past bearing; deburr and measure the cuts |

Coupon dimensions compensate for printed-hole shrinkage; they are not caliper measurements of the rods, bearings or pins. Preserve the print orientations because horizontal and vertical pin fits differ. The older 10.5 mm gauge is superseded by `KIT-pin_cut_gauge` here.

## Assembly and hardware

See [ASSEMBLY.md](ASSEMBLY.md) for what connects where, hardware counts and cold-fit checks. The native model is [P1B_final.f3d](P1B_final.f3d). Individual oriented replacement parts are in `parts/`; their original native-body volumes and exact production quantities are in [manifest.json](manifest.json).

**T3 uses nine hubs and ten 44.50 mm rods**, forming a hexagon and pentagon sharing an edge; one printed hub is spare. The shared edge is counted once: 6 + 5 − 1 = 10. Use the two hub arms 108° apart along the pentagon. Follow the T3 load/sag/drop procedure in `../../PRINT_AND_TEST_PLAN.md` and report results before printing the cage batch.

## Verification and limits

- All 14 production source STLs are closed, consistently wound, single solids and agree with native volumes within 0.1%.
- Every final plate preserves its source triangles after rigid placement, has flat positive-contact bases and no part intersections; the production inventory totals exactly 84.
- All twelve plates pass offline FlashPrint slicing. Expected first-layer part counts are present; every depositing path, brim and purge stays inside the 150 mm bed, including a conservative 0.8 mm line half-width. The package minimum edge margin is **7.59 mm**.
- The saved native P1B model passes all six pin and six bearing axes/depth checks, sixteen coaxial ring-splice passages, ring connectivity, 612 sampled collision checks, continuous rigid-body radial bounds and battery/arm-nut/relieved-foam checks. Ideal minimum inner/outer and outer/cage radial reserves are **0.911 / 0.860 mm**. The nominal prop-envelope reserve to inner structure is **4.315 mm**.
- The continuous bounds cover modeled rigid bodies. Actual screw heads/washer stacks, wires, straps, print error and load flex still need physical inspection. They do not establish a loaded clearance or a strength pass. Camera centerline is clear at the nominal ring pose; some ring orientations obstruct it, and real supports/wires can affect the image.
- Frame spacing **25.5 × 25.5 mm**, battery dimensions, motor layout and thrust remain vendor/provisional. The accounted mass scenarios are **144.68 / 166.68 g** for 450/1100 packs, excluding unweighed extras. Weigh and bench-test the actual aircraft. The 1100 pack remains flight-unverified.

See [verification.json](verification.json), [slice-verification.json](slice-verification.json), `profiles/manifest.json`, and `previews/`. Current native evidence is copied into `native-evidence/`; prior passing and failed stages are preserved in the repository under `../../review-2026-10-09-finalization/`. The CAD-kit suite passes 45 tests. Simulator geometry was refreshed from the authoritative CAD and remains illustrative, not hardware evidence.

After source or fit changes, regenerate the native exports and rerun package preparation, profile saving and slice checks; the verification scripts reject stale sources. Do not rescale parts to resolve a hardware mismatch.

**Attribution:** derived topology from kert's Thingiverse **408519** (https://www.thingiverse.com/thing:408519), under its supplied Attribution–NonCommercial license. The original README and license are included as `UPSTREAM_README.txt` and `UPSTREAM_LICENSE.txt`.
