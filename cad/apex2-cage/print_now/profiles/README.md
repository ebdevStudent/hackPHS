# Saved Voxel PETG profiles

Saved in FlashPrint-MP Expert Mode on 2026-10-08. Select the matching name in **Print → Select Profile**. These are untested starting settings; update nozzle temperature and retraction after T0 and use the regenerated CAD after T1/T2.

All profiles: Voxel, PETG, 235 °C nozzle, 60 °C bed, 0.27 mm first layer, 15 mm/s first-layer maximum, 100 mm/s travel, 3 shells, 25% hexagon infill, 1.5 mm retraction at 30 mm/s, cooling fan starts at 0.6 mm. Supports, raft, and dimensional adjustments are off. The supplied STL orientations and dimensions are separate from slicer profiles: keep 100% scale and the supplied orientation.

| Profile | STL | Layers | Speed | Top / bottom | Brim |
| --- | --- | --- | --- | --- | --- |
| Voxel PETG T0 | [T0_stringing_towers.stl](../T0_stringing_towers.stl) | 0.20 mm | 40 mm/s | 4 / 4 | 0 mm |
| Voxel PETG T1 sockets | [T1_socket_strip_and_rod_jig.stl](../T1_socket_strip_and_rod_jig.stl) | 0.15 mm | 35 mm/s | 5 / 5 | 0 mm |
| Voxel PETG T2 gimbal coupon | [T2_gimbal_fit_coupon.stl](../T2_gimbal_fit_coupon.stl) | 0.15 mm | 35 mm/s | 5 / 5 | 0 mm |
| Voxel PETG T3 cage section | [p1b_plate_T_cage_section_test.stl](../../plates_p1b/p1b_plate_T_cage_section_test.stl) | 0.15 mm | 35 mm/s | 5 / 5 | 5 mm |
| Voxel PETG T4 carrier arms | [p1b_plate_carrier_arms.stl](../../plates_p1b/p1b_plate_carrier_arms.stl) | 0.20 mm | 35 mm/s | 4 / 4 | 0 mm |
| Voxel PETG H1 three-way hubs | [p1b_plate_hubs_3way_a.stl](../../plates_p1b/p1b_plate_hubs_3way_a.stl) | 0.15 mm | 35 mm/s | 5 / 5 | 5 mm |
| Voxel PETG H2 mixed hubs | [p1b_plate_hubs_mixed.stl](../../plates_p1b/p1b_plate_hubs_mixed.stl) | 0.15 mm | 35 mm/s | 5 / 5 | 5 mm |
| Voxel PETG G1a inner ring | [p1b_plate_inner_ring_4_quarters.stl](../../plates_p1b/p1b_plate_inner_ring_4_quarters.stl) | 0.20 mm | 35 mm/s | 4 / 4 | 3 mm |
| Voxel PETG G1b outer ring | [p1b_plate_outer_ring_4_quarters.stl](../../plates_p1b/p1b_plate_outer_ring_4_quarters.stl) | 0.20 mm | 35 mm/s | 4 / 4 | 3 mm |
| Voxel PETG G2 junctions pivots | [p1b_plate_junctions_pivots.stl](../../plates_p1b/p1b_plate_junctions_pivots.stl) | 0.15 mm | 35 mm/s | 5 / 5 | 0 mm |
| Voxel PETG bend blocks | [bend_test_block.stl](../../../kit/test-pieces/bend_test_block.stl) | 0.15 mm | 35 mm/s | 5 / 5 | 5 mm |
| Voxel PETG bend jig | [bend_test_jig.stl](../../../kit/test-pieces/bend_test_jig.stl) | 0.15 mm | 35 mm/s | 5 / 5 | 5 mm |
| Voxel PETG load hook | [load_hook.stl](../../../kit/test-pieces/load_hook.stl) | 0.15 mm | 35 mm/s | 5 / 5 | 5 mm |
| Voxel PETG pin cut gauge | [pin_cut_gauge.stl](../../../kit/test-pieces/pin_cut_gauge.stl) | 0.15 mm | 35 mm/s | 5 / 5 | 5 mm |

Installed copies are in `/Users/devk/.FlashPrint-MP/slice_profile/`. This folder contains backup `.profile` files and a manifest with the checked saved values and SHA-256 checksums. The earlier shared `Voxel PETG T1-T2 starter` profile remains available too.

The 0.15 mm profiles use five top/bottom layers to keep approximately the same skin thickness as four layers at 0.20 mm. T3/H1/H2 use 5 mm brims; the ring-quarter profiles use 3 mm brims. The four kit fixtures use hub settings, including 5 mm brims, following `cad/kit/test_pieces.py`. No test result is implied by saving these profiles.

## Qualified-fit T3 profile — 2026-10-09

Use **Voxel PETG T3 socket 2 FINAL** with `../T3_cage_section_socket_2_checked.stl`. It saves 0.15 mm layers, 0.27 mm first layer, 35 mm/s printing, 10 mm/s first-layer maximum and a 5 mm / one-layer / 25% brim. Remaining values match the starter above. Both installed and backup files were verified through Qt QSettings; see `final-profile-manifest.json`. Existing profiles are preserved. This verifies settings storage, not printed retention or strength.
