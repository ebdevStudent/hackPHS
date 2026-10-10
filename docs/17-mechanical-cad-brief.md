# Mechanical CAD and PETG printing brief

**CAD update — 2026-10-08:** Both vendor/provisional Fusion designs were regenerated and reviewed. See [the CAD checks and current estimates](../cad/apex2-cage/README.md) and [the geometric review/evidence](../cad/apex2-cage/review-2026-10-08/README.md). P1B frame-slot travel now clears its foam pad; nominal rigid prop checks pass. Local pivot-region reserves are only 0.32–0.36 mm, and the 1100 mAh P1B accounted estimate leaves 9.75 g for unweighed items. Strap/wire routing, battery service access, printed fits, loaded clearance, strength, actual weight and thrust remain pending. The user requested P1B CAD ahead of the fixed-cage gate; that gate still controls physical P1B adoption.

Adapted 2026-10-07 from the [supplied mechanical brief](sources/mechanical-brief-2026-10-07/README.md), the [CAD plan](03-cad.md) and the user-provided Thingiverse ZIPs. This document defines a future CAD task; adding it does not create models, authorize physical testing or establish printable outputs.

## Scope and upstream reference

The mechanical task covers CAD, dimensions, tolerances, PETG printability, assembly, weight and physical fit/contact tests. Software, electronics design, flight-control code, vision, radio, simulation, networking and firmware are outside this mechanical task. Model their physical envelopes where needed for fit and clearance.

**The upstream reference is only [Spherical Drone, Thingiverse 408519, by kert](https://www.thingiverse.com/thing:408519).** Use the [preserved ZIP package and mesh inventory](../cad/references/thingiverse-408519/README.md). Wasim's simulator is an illustration, not upstream CAD or a dimension source. Google Doc illustrations supply project intent, not manufacturing geometry.

Preserve original upstream files and attribution separately from project adaptations. Part 1 supplies 18 STL meshes and a parts spreadsheet; part 2 supplies additional images. Neither archive contains native parametric CAD or STEP files. The original design has a rod-and-hub cage and quarter-segment hoops; its center, 3 mm rod interfaces and historical hardware list do not fit our plan by default.

## Current hardware and target

- Apex-2 aircraft, approximately 95 mm wheelbase, with nominal 2-inch propellers. Planned hardware is user-reported ordered. Adapt mounts around the actual hardware; do not redesign purchased parts.
- Cage outer envelope: 245–250 mm maximum assembled outside-span target, adjustable as measured clearance and mass require. Also record the minimum internal envelope at faces/edges/hubs; maximum width alone is not a clearance measurement.
- Printer: Monoprice Voxel, nominal 150 × 150 × 150 mm build volume, 0.4 mm nozzle, 1.75 mm filament and heated bed. These dimensions are supported by [Monoprice's Voxel guide](https://monopricesupport.kayako.com/article/283-buyers-guide-voxel).
- PETG for prototype printed structural parts. Retain the current **1 mm carbon-rod baseline**, with 1.5 mm reinforcement only where testing shows flex. PETG applies to hubs, brackets, connectors and any printed members; it does not turn the existing plan into an all-PETG cage. A printed-member alternative requires a separate mass/stiffness comparison.

The 1 mm diameter is a user-selected prototype baseline, not a verified strength specification. The ordered listing does not supply a mechanical datasheet, and the Thingiverse reference uses 3 mm rods. Review the [comparative stiffness/buckling estimate](19-cad-reference-research.md#structural-question-is-1-mm-rod-enough) and use a representative section test before committing to a full print.

## P1A modular fixed cage

Start from the reference's rod/hub concept and build a fixed cage. Do not create a monolithic 245–250 mm print or inherit the original aircraft center.

Use individually replaceable hubs/members, keyed connectors, aircraft mounting adapters and contact pieces. Four front/rear/left/right sections are a possible assembly breakdown, not a required count. Prefer symmetric/reversible parts and fewer unique pieces where practical. Rod-and-hub sections need not be four solid printed quadrants.

Every printed part, including supports and brim, must fit the usable Voxel volume with margin in its intended orientation. Avoid depending on the absolute bed diagonal. Printed future rings larger than the usable area must be segmented; determine each ring's actual diameter from clearance rather than assuming it equals cage diameter.

| Component | Mechanical requirement |
| --- | --- |
| Cage sections / rod hubs | Rounded contact geometry, low mass, replaceable pieces, sufficient stiffness to retain prop clearance |
| Cage connectors | Mechanical alignment and twist resistance; keyed overlap/sleeve/tongue joints with accessible fastening where appropriate |
| Aircraft carrier / fixed supports | Separate replaceable adapters, X/Y quad adjustment, shared attachment interfaces for the later gimbal |
| Battery support | Strap mounting, independent X/Y adjustment where useful, retention and tool-free access for the measured 2S 450 mAh packs and two user-reported 1100 mAh candidates. The frame seller recommends 200–650 mAh; measure the 1100 mAh packs and review mass/CG/thrust/electrical compatibility before flight. |
| Contact pieces | Optional small replaceable bumpers; do not add mass without an identified contact/load need |
| Camera/accessory brackets | Separate protective parts; maintain useful field of view and avoid tying cage geometry to one accessory |

Do not rely on PETG snap-fit flexibility alone without repeated assembly/load tests. Cheap connectors may provide sacrificial behavior during a severe impact, but must survive the normal low-energy contact gate and retain the aircraft safely. Keep all fasteners, connectors and possible deflection away from props. Check the failed/deformed connector condition so a sacrificial part cannot release a rod or loose piece into a prop disk.

Distinguish removable service joints from bonded subassemblies. Epoxy remains provisional; if a rod is bonded into a hub, document that the combined unit is replaced together. Repeated assembly/disassembly claims apply only to joints designed and tested for that operation.

## Parametric dimensions and clearance

Keep major parameters in one clear configuration section. Include cage envelope, measured motor-center coordinates, full prop diameter, clearance allowance, member section, rod/socket fit, connector length, mating clearances, mount spacing, battery envelopes, adjustment travel, screws/nut traps, bearing dimensions, pivots, ring diameters and segment count.

Measure frame and mounting holes, prop sweep, camera/lens, battery range, component/antenna envelopes, standoffs, screws, rods and bearings with calipers when delivered. Label unknowns as placeholders. Wheelbase is not total aircraft width. Scale cage geometry deliberately; rebuild hardware interfaces to measured dimensions rather than uniformly scaling STL holes.

For P1B, record three-dimensional center of gravity relative to the gimbal axes for each actual pack, including vertical offset. X/Y adjustment alone is not proof of three-dimensional balance. Verify axis alignment, free movement, friction and retention with the measured assembly; decide any carrier-height change from those results.

Model all four full prop disks and the complete mechanically reachable cage/ring/aircraft relationship. No cage, ring, wire, antenna or fastener may enter a prop disk. Reserve positive clearance for measured tolerance, flex and wire movement. Protect camera view and prop inflow/outflow. Any future travel stops must be modeled and tested rather than used to hide an unexamined pose.

Separately define the intended contact surface/edge geometries and approach directions. With props removed, use the modeled prop envelope and representative probes to check whether an object can enter an opening and contact a prop before touching protective structure. Record the smallest object/edge tested and limit protection claims to those conditions.

## PETG prototype settings and fit coupons

These are **untested starting ranges from the supplied brief**, not a validated Voxel profile:

| Setting | Initial trial / requirement |
| --- | --- |
| Layer height | Around 0.20 mm |
| Structural walls | 3–4 perimeters, then tune from observed loading and mass |
| Infill | Around 20–35%; avoid solid structural parts without a load-based reason |
| Nozzle | About 230–240°C only if allowed by the exact filament and installed nozzle |
| Bed | About 55–70°C only if allowed by the printer, surface and filament |
| Close mating fit | Trial clearance 0.2–0.3 mm **per side** |
| Removable/sliding fit | Trial clearance 0.3–0.5 mm **per side** |

Monoprice's [Voxel guide](https://monopricesupport.kayako.com/article/283-buyers-guide-voxel) lists a 240°C maximum extruder temperature. Confirm the actual installed nozzle and printer settings; successful PETG printing on this device remains unverified. Fit clearances are initial experiments, not verified socket or bearing tolerances. Two opposed 0.25 mm clearances mean 0.50 mm total dimensional allowance. Calibrate screw holes, rod sockets and bearing seats independently; do not apply a sliding-joint gap indiscriminately to every interface.

Print small clearance ladders, rod sockets, connector sections and hole/fastener coupons before committing to the cage. Record actual printed dimensions, assembly force, retention, repeated-fit behavior and failure direction.

## Orientation, supports, fasteners and mass

Specify the orientation of every structural part. Prefer long printed members lying down with load paths along their length; avoid depending on weak layer separation in impact or screw loading. Evaluate connector loading in more than one direction.

Favor self-supporting chamfers, roughly 45-degree transitions and suitable teardrop horizontal holes. Split difficult geometry instead of relying on extensive supports. Record supports and brim in each part's build-volume check.

Use available small nuts/bolts or suitable inserts with tool access and adequate edge distance. Keep fastener dimensions parametric. Early removable joints may use nuts and through-bolts; do not assume upstream M3 quantities apply to the Apex-2 assembly.

Use ribs, curved sections and local reinforcement rather than blanket thickness. Estimate PETG mass from material volume using roughly 1.25–1.30 g/cm³ until actual filament data is known. CAD solid volume is not automatically slicer extrusion volume for infilled parts. Compare slicer estimates and weighed prints, and include rods, screws, straps and all hardware in separate P1A/P1B totals before a print batch.

## Measured mass budget

Before the complete P1A print batch, fill this worksheet for each actual pack. Values are pending; an attractive CAD estimate does not establish flyability.

| Input / result | Definition | Current status |
| --- | --- | --- |
| T_available | Measured total static thrust at recorded battery voltage and motor/prop configuration, expressed as equivalent supported mass in grams | Pending |
| R_target | Planned thrust-to-weight target, at least 2 | Target only |
| M_bare | Bare aircraft with its actual airborne equipment, excluding battery and added cage/mount structure | Pending |
| M_pack | Actual tested battery mass | Pending |
| M_added | Cage, mounts, straps, extra fasteners/wiring and, for P1B, rings/pivots/bearings | Pending |
| Added-mass allowance | min(T_available / R_target, 175 g user ceiling) − M_bare − M_pack | Pending; current CAD estimates in [cad/apex2-cage](../cad/apex2-cage/README.md#weight-budget-user-limit-175-g-all-up-maximum) |
| Margin | Added-mass allowance − M_added | Pending |

Use consistent units: gram-force-equivalent thrust with gram masses, or force divided by weight throughout. A negative allowance or margin requires redesign before claiming the target is met. Include the uncertainty of estimates and measurements. The allowance is a planning check, not evidence of ≥3-minute endurance, thermal performance, contact tolerance or flown thrust margin. The source's redesign threshold below 1.5:1 remains documented in [build/test](10-build-and-test.md).

## Development order and gimbal gate

1. Inspect the reference and establish parameters/unknown measurements.
2. Print and measure joint/socket/fastener coupons.
3. Design, print and mechanically test one representative hub/member section and connector using the planned rod length/diameter. Record rod lot/diameter, unsupported span, load direction/magnitude/duration, loaded and residual deflection, rod retention, socket pullout, joint slip and visible damage. Set the pass limit from the measured prop-clearance budget; show that the loaded deflection fits before a full cage batch.
4. Refine only demonstrated weak areas, then assemble the full P1B CAD (P1A is CAD-only, not built; 2026-10-08).
5. Check fit without props installed; inspect the modeled full prop envelope before powered work.
6. Print/assemble/weigh P1B and record fit, clearance, camera access, ring freedom, balance and contact behavior.
7. Meet the flight gate on P1B: **10 consecutive low-energy contacts without damage or prop strikes, at least three minutes usable caged flight and repeatable manual recovery**.
8. Recommended: fly the first hovers with the rings zip-tied, then free them.
9. Make later outer/inner rings, cage adapters, bearing/pivot interfaces, retainers/stops and connectors removable. Complete full reachable-motion clearance and mass checks before printing P1B.

Manual flight is used for the mechanical flight/contact acceptance. Do not make an unverified assistance bridge a prerequisite for P1B success. Flight checks follow the existing [physical build plan](10-build-and-test.md).

## Future CAD deliverables

The chosen workflow is **Fusion driven by Python generators** with centralized user parameters: [`cad/apex2-cage/build_p1a.py`](../cad/apex2-cage/build_p1a.py) and [`build_p1b.py`](../cad/apex2-cage/build_p1b.py) generate the P1A fixed cage and the P1B two-ring gimbal, with STL exports, Voxel print plates and fit coupons. [`cad/kit/`](../cad/kit/README.md) adds, without changing the generators:

- the arrival measurement form and its checker;
- the rod/hub bend-test pieces and jig;
- the cage-opening probe analysis;
- the P1B mass options.

Future deliverables: editable source, full P1A assembly, individual printable exports, STEP where supported, calibration coupons, mechanical-only print/hardware BOM and an assembly README. Keep derived models outside `cad/references/`. Use names such as `cage_hub`, `cage_connector`, `cage_airframe_mount`, `cage_bumper` and `tolerance_test`; use directional names only when parts genuinely differ.

For each printable part, record quantity, revision, material, estimated/measured mass, dimensions, orientation, supports/brim, walls/infill, hardware, assembly order and unresolved measurements. Priority: prop protection and clearance, reliable assembly, low mass, impact tolerance, repair, reliable printability, low material/time use and appearance.

**Current status (2026-10-08):** parametric P1A and P1B models exist ([CAD README](../cad/apex2-cage/README.md)). They use vendor and provisional dimensions; no part has been printed, fitted, weighed or load-tested. No print profile is verified. This brief still defines the physical tests that must close those gaps.

See [the mechanical review](18-mechanical-review.md) for findings, completed source checks and unresolved physical evidence.

See [CAD reference research](19-cad-reference-research.md) for comparable projects and their source/license limits. Thingiverse 408519 remains the sole upstream design.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Google Doc — CAD tab](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit?tab=t.ri12fpw0hdp1) — Project geometry and final CAD rules.
- [Thingiverse 408519](https://www.thingiverse.com/thing:408519) — Only user-designated upstream CAD reference.
- [Monoprice Voxel buyer guide](https://monopricesupport.kayako.com/article/283-buyers-guide-voxel) — Nominal printer volume/nozzle reference; confirm actual machine configuration.
- [CAD comparison research](19-cad-reference-research.md) — Comparable public designs, measured reference limits and rod analysis.
- [OVONIC 2S 1100 mAh 60C XT30 two-pack listing](https://us.ovonicshop.com/products/2-ovonic-rebel-2-0-60c-2s-1100mah-lipo-battery-lihv-7-6v-pack-with-xt30-plug-for-size-100mm-to-140mm-brushless-drones-long-range-drone-fpv) — Candidate pack dimensions must be measured because the listing fields conflict.
