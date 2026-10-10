# T4 — checked geometry and physical fit procedure

Updated for final geometry: **2026-10-09**, on this Mac. The live Fusion P1B design and current exported T4 files were inspected without changing the model. **The printed geometry and nominal fastener alignment pass the checks below. Physical frame fit and strength are not yet established.**

**Recommended:** [final T4 plate](../print_ready_p1b/plates/T4.stl) and **Voxel PETG FINAL T4**, with 0.15 mm layers, five top/bottom layers and saved 10 mm/s first-layer / 5 mm slow brim. That revised layout is 98 × 102 × 16 mm; all four parts pass offline slicing with ≥17.6 mm path clearance.

**Alternative refreshed 0.20 mm layout: load this centered copy:** [T4_carrier_and_arms_checked.stl](T4_carrier_and_arms_checked.stl). It contains the carrier, thin nut shield and two support arms at 100% scale in their original print orientations. Only the complete layout's X/Y position changed; original exports are preserved. Choose **Voxel PETG T4 carrier arms**, then override first-layer maximum to **10 mm/s** and enable a **5 mm, one-layer brim at 25% speed**. The original saved profile still has brim off and first-layer maximum 15 mm/s.

## What was checked

| Check | Result |
| --- | --- |
| Current source and export checksums | Match the manifests |
| Live Fusion parameters and native T4 volumes | Match the current generators and export manifest |
| Carrier, shield, two identical support arms | Four watertight, consistently oriented solids in the plate |
| Print bases | All at Z = 0, supplied orientations retained |
| Nominal frame attachment | 25.5 × 25.5 mm pattern; four 2 mm screw paths open at center and ±2 mm lateral travel |
| Arm attachment | Both arms' screw paths align with carrier slots through ±3 mm arm travel |
| Flange holes | Both nominal 2 mm screw paths open in each identical arm |
| Strap openings | Nominal 12.5 mm wide × 2 mm thick strap passage is open |
| Plate footprint | 123.5 × 94 mm, 16 mm maximum height |
| 5 mm brim, with complete layout centered | 133.5 × 104 mm footprint; 8.25 mm / 23 mm edge clearance on a 150 mm bed |

The original packed STL starts at X/Y = −70 mm and needs centering for a brim. **The checked copy is already centered** (translated +8.25 mm X, +23 mm Y). No scaling, rotation or rearrangement is needed. Its mesh bounds are X = ±61.75 mm, Y = ±47 mm, Z = 0–16 mm. Verified all four parts retain their original dimensions and volumes, have positive base contact, and do not intersect.

**Offline slicer check:** the bundled FlashPrint engine successfully sliced the checked copy at 0.20 mm layers, 0.27 mm first layer, 35 mm/s base speed, three shells, four top/bottom layers, 25% hexagon and a 5 mm brim. All four parts have first-layer shell/infill paths. All 33,635 depositing segments, including brim and purge, stay inside the 150 mm square bed; allowing a conservative 0.8 mm half-width for every path gives edge margins **7.85 / 7.85 / 21.6 / 22.6 mm**. The first layer and brim are capped at 10 mm/s. See the [actual first-layer path image](T4_sliced_first_layer.png).

This offline output uses generic engine startup and is **diagnostic only**. Load the STL and slice in FlashPrint with printer **Voxel** to generate the actual print job; do not print `t4-diagnostic-only.g`. The offline config is separate from installed profiles and does not confirm a live FlashPrint scene or any printer connection.

## Foam and fastener detail found in the audit

The final native model includes the narrow **3 mm foam pad**, four frame nuts and four arm nuts. Its foam reliefs clear both nut sets throughout modeled adjustment travel. **Cut reliefs in the foam around the arm nuts and screw tails.** Do not force the nuts into compressed foam or clamp them through the battery shield. The foam is cut by hand, not printed.

For the current nominal geometry, a central foam strip is approximately **15.9 × 62.8 × 3 mm**. Two centered end notches, approximately **5.62 mm wide × 8.21 mm deep**, through the 3 mm pad, clear the conservative arm-nut envelopes throughout ±3 mm adjustment. The equivalent modeled relief rectangles extend past the foam ends. Those are CAD guide dimensions using standard nut sizes; mark the actual nuts and check your real hardware before cutting. The audit checks that these modeled reliefs remove the foam overlap. Keep foam clear of all fasteners at the final adjustment.

Stack order beneath the carrier: **foam → printed 0.8 mm shield → battery**. Nuts and screw tails must project no more than **2.6 mm below the carrier underside**, leaving only **0.4 mm nominal clearance** above the shield. Check the actual stack, including washers, nut engagement, screw length and compressed foam. Frame + carrier are nominally **5 mm** thick; arm + carrier are **6.5 mm** thick before washers/nuts. An arbitrary screw length is not automatically suitable for both. Choose washers or shorten a screw as needed while retaining full nut engagement; measure the assembled protrusion.

## What to verify on your actual frame

1. **Before printing:** measure the accessible attachment holes center-to-center across and front-to-back. The current carrier assumes **25.5 × 25.5 mm**, with lateral adjustment only; it does not automatically fit every alternate mounting pattern. Confirm the holes can be used without disrupting flight-controller mounts or wiring. Measure actual bottom-plate thickness (CAD: 2.5 mm).
2. **Print:** load [final T4.stl](../print_ready_p1b/plates/T4.stl), keep the supplied arrangement at 100% scale and choose **Voxel PETG FINAL T4** with printer **Voxel**. This profile already saves 0.15 mm layers, 35 mm/s print speed, 10 mm/s first-layer maximum and a 5 mm, one-layer brim at 25% speed. It uses 235 °C nozzle / 60 °C bed; retain your successful T1B material settings if different. Use the bed preparation that worked for T1B. Check the FlashPrint preview contains all four parts and all of the brim stays inside the bed, then slice in FlashPrint for the actual Voxel print job.
3. **Cold fit, battery disconnected and props removed:** seat the frame flat on the carrier. All four screws must align and pass through without forcing or modifying holes. Use screws with nuts, not the T1B pilot threading test. Verify full nut engagement and the underside protrusion limit.
4. Attach both support arms with M2 screws and nuts. Check the slots permit the intended adjustment, then tighten gently. No cracking, whitening, persistent wobble or joint slip is acceptable. The arms must not interfere with wiring or frame components.
5. Cut and fit the relieved foam; install the shield and strap. Fit each battery you plan to use. Confirm no metal contacts or presses against the battery, the shield lies flat, the strap holds securely, and battery/lead access remains usable.
6. Report the frame spacing, screw lengths/washer stacks, fit results and any crack, blocked hole, rubbing or movement. These determine whether T4 can be retained as the final carrier or needs revision.

G2 supplies the separate arm-end pivot blocks. They are required before checking complete pivot motion and prop clearances. A static T4 fit check does not certify dynamic load strength; final loaded assembly, ring/splice checks and the project's contact/flight gates still apply.

## Evidence and reproduction

- [Geometry report](../../kit/reports/t4-audit-2026-10-09.json)
- [Read-only Fusion inspection](../../kit/reports/t4-fusion-inspection-2026-10-09.json)
- [Audit script](../../kit/audit_t4.py)
- [Centered STL manifest](T4_checked_manifest.json)
- [Slice verification report](../../kit/reports/t4-slice-check-2026-10-09.json)
- [Centering script](../../kit/prepare_t4.py) and [offline slice check](../../kit/slice_t4_check.py)

From the project root:

```sh
cad/kit/.venv/bin/python cad/kit/audit_t4.py
cad/kit/.venv/bin/python cad/kit/prepare_t4.py
python3 cad/kit/slice_t4_check.py
```

The script reads the current STLs and source manifests, checks their closed meshes and nominal interfaces, and writes a report only. It compares against the saved live Fusion inspection; a later model edit requires a fresh inspection. No print or physical assembly was performed by this audit.
