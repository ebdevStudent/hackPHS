# Start printing here — final P1B files

**Print T3 next.** Load its STL and select the matching saved profile in FlashPrint with **Voxel** selected. All twelve current plates, fourteen individual production designs, fixtures, saved profiles, native CAD, assembly instructions and validation records are in **FINAL_P1B/**. The older files alongside this guide are earlier coupons or layouts; use the FINAL files for production.

| Print | Load this STL | Select this profile |
| --- | --- | --- |
| T3 | [T3.stl](FINAL_P1B/plates/T3.stl) | **Voxel PETG FINAL T3** |
| T4 | [T4.stl](FINAL_P1B/plates/T4.stl) | **Voxel PETG FINAL T4** |
| KIT-bend_test_block | [KIT-bend_test_block.stl](FINAL_P1B/plates/KIT-bend_test_block.stl) | **Voxel PETG FINAL KIT-bend_test_block** |
| KIT-bend_test_jig | [KIT-bend_test_jig.stl](FINAL_P1B/plates/KIT-bend_test_jig.stl) | **Voxel PETG FINAL KIT-bend_test_jig** |
| KIT-load_hook | [KIT-load_hook.stl](FINAL_P1B/plates/KIT-load_hook.stl) | **Voxel PETG FINAL KIT-load_hook** |
| KIT-pin_cut_gauge | [KIT-pin_cut_gauge.stl](FINAL_P1B/plates/KIT-pin_cut_gauge.stl) | **Voxel PETG FINAL KIT-pin_cut_gauge** |
| H1-01 | [H1-01.stl](FINAL_P1B/plates/H1-01.stl) | **Voxel PETG FINAL H1-01** |
| H1-02 | [H1-02.stl](FINAL_P1B/plates/H1-02.stl) | **Voxel PETG FINAL H1-02** |
| H2 | [H2.stl](FINAL_P1B/plates/H2.stl) | **Voxel PETG FINAL H2** |
| G1a | [G1a.stl](FINAL_P1B/plates/G1a.stl) | **Voxel PETG FINAL G1a** |
| G1b | [G1b.stl](FINAL_P1B/plates/G1b.stl) | **Voxel PETG FINAL G1b** |
| G2 | [G2.stl](FINAL_P1B/plates/G2.stl) | **Voxel PETG FINAL G2** |

Keep **100% scale and the supplied orientation/layout**. FINAL settings are 0.15 mm layers, 0.27 mm first layer, three shells, five top/bottom layers, 25% hexagon, 35 mm/s print, 10 mm/s first-layer maximum, and a 5 mm one-layer brim at 25% speed. Use the successful T1B temperature/retraction and bed preparation; the saved starters are 235 °C nozzle, 60 °C bed, 1.5 mm retraction at 30 mm/s. Supports, raft and XY compensation are off. Slice in FlashPrint to create the actual printer job and read its time estimate.

[Full settings and plate inventory](FINAL_P1B/README.md) · [Assembly and hardware](FINAL_P1B/ASSEMBLY.md) · [Profile backups](FINAL_P1B/profiles/) · [Individual replacement parts](FINAL_P1B/parts/) · [Native Fusion model](FINAL_P1B/P1B_final.f3d) · [Download the entire final package](FINAL_P1B.zip)

T3 prints ten hubs. Assemble nine with **ten 44.50 mm rods**, leaving one hub spare, then check socket retention and the section load/sag/drop tests before the full cage batches. T4 can be checked independently against the actual frame. M2 #5 is **2.00 mm on the combined seven-hole T1B strip**; rod #2 is **1.275 mm**. Physical strength, hardware grip, actual-frame fit and flight acceptance remain pending.

Earlier test coupons, if a retest is needed: [T0](T0_stringing_towers.stl), [T1](T1_socket_strip_and_rod_jig.stl), [combined T1B](T1B_socket_and_screw_refinement.stl), [T2](T2_gimbal_fit_coupon.stl). The standalone five-hole scratch coupon uses different numbering and was not the source of the selected M2 fit.

Regenerate this folder with `python3 cad/kit/prepare_print_now.py` after the final source package has passed its checks. Diagnostic generic-startup G-code is excluded from this folder and ZIP.
