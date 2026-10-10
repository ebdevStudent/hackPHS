# CAD kit: measurements, test pieces and checks

Tools for measuring, inspecting and preparing the Apex-2 cage. Most inspection tools read the generators; `finalize_p1b_fusion.py` explicitly rebuilds/saves the authorized main design. Each one *reads* `cad/apex2-cage/build_p1a.py`, `build_p1b.py`, `vendor_specs.json`, `measurements.json` and the P1B export manifest through [`cage_model.py`](cage_model.py), so every number follows the design. Local mesh/test tools do not require Fusion; native finalization and interface inspection do. Final production geometry is exported from Fusion and packaged without scaling.

```sh
cd cad/kit
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests -q              # kit tests
```

| Tool | Purpose | Output |
| --- | --- | --- |
| [`measurement-form.csv`](measurement-form.csv) + [`apply_measurements.py`](apply_measurements.py) | What to measure on arrival, how, and a checked path into `measurements.json` | Validated JSON (only with `--write`) |
| [`test_pieces.py`](test_pieces.py) | Rod/hub bend-test blocks, jig, load hook, pin cutting gauge | [`test-pieces/`](test-pieces/manifest.json) STLs |
| [`t1_refinement.py`](t1_refinement.py) | Finer T1 rod sockets and larger M2 screw pilots, based on the reported first coupon fit | [`T1B guide`](../apex2-cage/print_now/T1B_README.md), STL and manifest |
| [`export_t3_fusion.py`](export_t3_fusion.py), [`prepare_t3.py`](prepare_t3.py), [`slice_t3_check.py`](slice_t3_check.py) | Native Fusion T3 candidate with user-selected T1B #2 socket; center ten hubs and check exported sockets and offline bed fit | [`Updated T3 file and guide`](../apex2-cage/print_now/T3_README.md), manifests and slice report |
| [`audit_t4.py`](audit_t4.py) | Current T4 STL integrity, frame/arm/strap screw paths, packing and foam/nut clearance | [`T4 fit guide`](../apex2-cage/print_now/T4_FIT_CHECK.md) and [geometry report](reports/t4-audit-2026-10-09.json) |
| [`prepare_t4.py`](prepare_t4.py) | Audit and center a T4 copy; verify flat bases, unchanged dimensions and 5 mm brim fit | [`Checked T4 STL`](../apex2-cage/print_now/T4_carrier_and_arms_checked.stl) and [manifest](../apex2-cage/print_now/T4_checked_manifest.json) |
| [`slice_t4_check.py`](slice_t4_check.py) | Offline bundled FlashPrint engine check of all depositing paths against the Voxel bed; system Python with Pillow | [Slice report](reports/t4-slice-check-2026-10-09.json) and [first-layer image](../apex2-cage/print_now/T4_sliced_first_layer.png); diagnostic G-code is not print-ready |
| [`analyse_bend.py`](analyse_bend.py) | Pass/fail for the bend-test log | JSON verdict |
| [`opening_probe.py`](opening_probe.py) | Which objects can pass a cage opening and reach a prop (fast rod model) | [`reports/opening-probe.md`](reports/opening-probe.md) |
| [`clash_check.py`](clash_check.py) | Solid check with the exported hub meshes and rods: cage vs props, and balls pushed into each opening | [`reports/clash-check.json`](reports/clash-check.json) |
| [`bend_simulation.py`](bend_simulation.py) | Jig assembly fit with solids and predicted bend-test readings | [`reports/bend-simulation.json`](reports/bend-simulation.json) |
| [`p1b_mass_options.py`](p1b_mass_options.py) | P1B budget against 175 g and the value of each lightening option | [`reports/p1b-mass-options.json`](reports/p1b-mass-options.json) |
| [`decisions-2026-10-08.md`](decisions-2026-10-08.md) | Settled pin length, rod bonding and camera tilt | — |

## Arrival measurements

1. Copy `measurement-form.csv`. Fill the `value` column using the method in each row; leave unknowns blank. Use the `unit` given.
2. `.venv/bin/python apply_measurements.py my-form.csv` checks every row:
   - it rejects unknown names, which the generators would otherwise silently ignore;
   - it rejects wrong units, non-numbers and implausible values;
   - it warns about values more than 10 % from the vendor figure, prop overlap, and thrust-to-weight below 2:1 before any cage is added.
3. When it reports no errors, run it again with `--write`. A timestamped backup of the old `measurements.json` is kept.
4. In Fusion, run `build_p1a.py` in the P1A design and `build_p1b.py` in the P1B design. P1B-only rows (bearings, pins, coupon fits) apply only there. Then run `make_plates.py` and `make_plates.py p1b`.

A measured rod diameter other than 1.00 mm stops regeneration today: `validation.py` enforces the adopted 1 mm baseline exactly. The tool warns about this; changing that gate is a design decision outside this kit.

## Rod and hub bend test

The test pieces have the generator's exact hub-arm socket: 3.2 mm arm, socket for a 1.0 mm rod with 0.15 mm per side, 5 mm deep. The jig holds two of them so the exposed rod span equals the cage's, **35.00 mm**. Cut the test rod to **44.50 mm**, the real edge-rod length (the rod-cutting jig cuts this length).

1. Print two `bend_test_block`, one `bend_test_jig` and one `load_hook` in PETG, with hub settings.
2. Thread the load hook (rod through its upper hole) onto the rod and a string through its lower hole and the jig's slot to a cup below the bench; slide the hook to mid-span, push the rod into both sockets, and seat the blocks in the jig pockets, pushed toward the middle. Mark the rod at each socket mouth with a fine pen.
3. Read the rod's mid-span position against the scale (0.5 mm steps, a deep groove every 2 mm). A macro phone photo with the rod and scale in focus works best. This is the zero.
4. Hang loads from the hook: 20, 50, 100 and 200 g. Water in a cup counts 1 g per ml. Read mid-span deflection at each load. Hold 200 g for 30 s, then read again (`hold`). Remove the load and read the residual (`unload`).
5. Record the largest mark movement at either socket as `slip_mm`. Note any crack, whitening or pull-out in `notes`.
6. Fill [`bend-test-log.csv`](bend-test-log.csv), using one specimen letter per rod/block set. Run `.venv/bin/python analyse_bend.py bend-test-log.csv`.

**Pass:**

- no joint slip over 0.5 mm;
- residual deflection no more than 0.25 mm (no visible permanent set);
- no visible damage at 200 g.

Test at least three specimens from different rods. Keep the measured stiffness (g/mm) with the record. If 1 mm rods fail, follow the [CAD research](../../docs/19-cad-reference-research.md#structural-question-is-1-mm-rod-enough): change geometry or reinforce locally, then retest.

**Simulated beforehand (`bend_simulation.py`).**

- **Assembly with solids:** the 44.50 mm rod seats in both sockets with the 0.25 mm end gaps and touches no bore or jig material. The blocks fit their pockets, the rod has 8 mm of room to deflect, and the hook hangs 4 mm above the channel floor. (This check found and fixed an earlier hook too tall for the jig.)
- **Expected readings:** for a 1 mm solid rod over 35.00 mm, using the 28–40 GPa modulus published for a different supplier's pultruded rod:

| Load | Loose sockets (pinned) | Tight sockets (fixed) | Peak stress |
| --- | --- | --- | --- |
| 100 g | 0.45–0.64 mm | 0.11–0.16 mm | 22 % of typical strength |
| 200 g | 0.89–1.28 mm | 0.22–0.32 mm | 44 % |

Readings well above these ranges suggest a softer rod or a loose joint; check the slip marks. Readings at the fixed end of the range mean the sockets grip well.

**How this fits with T3.** The [print and test plan](../apex2-cage/PRINT_AND_TEST_PLAN.md#t3--cage-section-test-after-the-cad-is-updated-with-t1) has its own T3 cage-section test: nine real hubs, a hexagon plus a pentagon. The two tests are complementary:

- **T3** decides joint retention and toughness: 300 g pull-out, sag under 100 g below 3 mm, and drops.
- **This jig** measures one member precisely: stiffness, permanent set and slip, with a 0.5 mm scale.

**Decision (user, 2026-10-08): keep both.** Use the jig's 100 g reading to check T3's sag figure. The prediction above (≤ 0.64 mm) is well inside T3's 3 mm limit. Use T3's 300 g hang for pull-out.

These pieces test the rod/socket joint and one member. The P1B ring quarters and splices still need their own load check before the gimbal batch.

## What the opening check found (vendor dimensions, 1 mm rods, hubs ignored)

| Opening | Count | Largest object that passes through |
| --- | --- | --- |
| Hexagon | 20 | ~84 mm diameter |
| Pentagon | 10 | ~66 mm |
| Pole triangle | 10 | ~22 mm |

Any round object under about 84 mm — a ball, a pole end, a finger, a cable, a box corner — can pass a hexagon and reach the props, in both P1A and P1B. A 90 mm object pushed into a hexagon stops 28.6 mm below the rods, only 2.9 mm from the P1A prop envelope (props grown by the full balancing travel). In P1B, every object up to 150 mm can touch the turning gimbal ring. That is a jam risk, not a prop strike. The lateral grid is 1 mm and always includes each opening's centre.

**Consequence:** the cage protects against walls, floors and large objects only. Keep demo contacts to flat surfaces and large padded objects, and say so when presenting. Narrow objects and edges are not protected against. The [full table](reports/opening-probe.md) lists 5–150 mm objects.

## Solid clash check

`clash_check.py` builds the cage from the 62 exported hub meshes and 100 rods (247.85 mm span):

- **Cage alone:** never intersects the P1A prop volumes, even grown by full balancing travel (nearest 38.1 mm), and never enters the P1B swept aircraft sphere.
- **Balls up to 84 mm:** pushed into each of the 40 openings, they pass a hexagon and reach the props in P1A and P1B. Real hub material does not close the opening.
- **90 mm ball:** rests 3.05 mm from the P1A props. The rod-only analysis gave 2.9 mm, so its simplification is conservative.
- **Gimbal ring:** objects of every size tested can touch the turning outer ring in P1B.

## P1B weight against 175 g

With the current exports (they now include the nut shield):

- **P1B + 1100 mAh:** about **166.9 g** accounted, before the 8–10 g of unweighed wiring, antenna, XT30 lead and screws. That is **174.9–176.9 g**, at or over the limit.
- **P1B + 450 mAh:** about 144.9 g, leaving 20–22 g of margin after the same extras.

| Option | Saves | Cost / risk |
| --- | --- | --- |
| Fly P1B with the 450 mAh pack only | 22 g | Shorter flights; no CAD change |
| Nylon M2 screws on the 16 ring splices | ~2.6 g | Check splice slip with a load test |
| Ring band 3.0 → 2.5 mm | ~2.4 g | Out-of-plane stiffness −42 %; load-test a quarter |
| Pocket pivot blocks and Z junction posts | ~2.5 g | Keep material around pins and seats |
| Larger carrier window | ~1.2 g | Carrier twist with heavy pack |

**Decision (user, 2026-10-08): no lightening.** P1B keeps the current design and both packs. The user judged the 1100 mAh configuration only slightly past the target: about 2.1:1 thrust-to-weight at the 350 g planning thrust. The options above stay on record and are not applied. Weigh the real aircraft first; a measured `bare_aircraft_g` replaces the 44.8 g vendor sum and settles the actual margin.

## Final P1B package — 2026-10-09

[Package and assembly chart](../apex2-cage/print_ready_p1b/README.md). Current fixtures use the selected 1.275 mm rod bore and 11.00 mm pin cut. Original fixtures and dated decisions remain historical; use the regenerated package copies. Reproduction, from the project root, after refreshing native exports:

```sh
cad/kit/.venv/bin/python cad/kit/prepare_final_package.py
software/.venv/bin/python cad/kit/save_final_profiles.py
python3 cad/kit/slice_final_package.py
software/.venv/bin/python cad/kit/verify_final_package.py
```

The saved native model and reports are in `cad/apex2-cage/review-2026-10-09-finalization/`. `inspect_final_interfaces_fusion.py` reads the live design to verify sixteen coaxial splice passages and refresh T4 evidence. All 45 CAD-kit tests pass after updating the previous 10.5 mm gauge expectation to the finalized 11.00 mm stack; the old failure is preserved. Saving profiles does not select a live dialog or send a print job.

After final-package verification, run `python3 cad/kit/prepare_print_now.py` to copy the complete deliverable into `print_now/FINAL_P1B`, write the start guide and produce the CRC-checked download ZIP. The copy retains exact verified STL/profile bytes and adjusts guide links for the new folder.
