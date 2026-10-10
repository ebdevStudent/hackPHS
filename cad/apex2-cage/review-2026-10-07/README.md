# Fusion review — Apex2 Ball Cage P1B Gimbal

Reviewed 2026-10-07 in the live Fusion document **Apex2 Ball Cage P1B Gimbal**, saved version **7**, project **HackPHS Ball Drone**. File ID: `urn:adsk.wipprod:dm.lineage:nGruekfrQUWIfdoI339dEA`.

**Resolve the prop-envelope collision and centered camera obstruction before printing the P1B structural batch.** The checks below use the current Fusion BRep geometry. The supplied images helped identify the design; they supplied no dimensions or acceptance evidence. This review evaluates the CAD and its exported files; physical strength, fits and flight remain untested.

![Current Fusion model](/Users/devk/Documents/HackPHS26/cad/apex2-cage/review-2026-10-07/00-current-fusion-model.png)

| Finding | Status | Consequence |
| --- | --- | --- |
| Allowed X/Y balancing travel creates prop/inner-ring overlap | Confirmed in the current CAD | Violates the required zero intrusion into prop keepouts |
| Outer ring crosses the modeled camera centerline | Confirmed at the nominal pose | Central target visibility needs a layout decision |
| 1100 mAh pack overlaps nominal underside M2 heads | Confirmed under the stated fastener assumption | Complete the battery/fastener interface |
| Fusion joints and rigid groups are absent | Confirmed | Named groups have no constrained CAD motion |
| Native Fusion mass includes steel analysis bodies | Confirmed | Native Properties mass cannot represent aircraft weight |
| Socket/bearing/pin fits and 1 mm rod strength | Unverified physically | Fit coupons and representative structural tests remain required |

**1. Prop clearance fails after permitted balancing adjustments.**

The screenshots suggested limited space around the inner ring. I tested the hypothesis that the ring was sized for the centered aircraft rather than its permitted adjustment range.

The current slots permit **±4 mm X** carrier adjustment and **±5 mm Y** frame adjustment. Translating the prop envelopes by **+4 mm X, +5 mm Y**, then rotating them **−15° around the X pivot**, produces **49.013782 mm³** of intersection between `PROP_DISK_FR_keepout` and `inner_ring_quarter:1`. The keepout is the model's 50.8 mm diameter, 5.1 mm thick swept disk; it is not an individually modeled blade.

A 360-case test covered five X/Y settings with X rotation in 5° increments. It found 12 intersecting cases at the two combined X/Y offsets. The centered setting had zero intersections in its 72 sampled rotations. A single intersecting permitted pose is sufficient to invalidate unrestricted clearance.

The actual cause is in [aircraft_radius](/Users/devk/Documents/HackPHS26/cad/apex2-cage/build_p1b.py:84): it uses the centered motor radius and prop radius. It omits `adj_x`, `adj_y` and the vertical adjustment range. The existing [verification sweep](/Users/devk/Documents/HackPHS26/cad/apex2-cage/build_p1b.py:474) also rotates centered geometry. Its reported zero collisions therefore cannot establish clearance at all allowed balancing positions.

Current inner-ring radius is **79 mm**. A prop-only bound using the present ±4/±5/±6 mm X/Y/Z travel is **82.332 mm**. Retaining the requested 4 mm reserve suggests a starting inner radius of **87 mm**, followed by regeneration and checks of all rings, junctions, hardware and wiring. This is a proposed sizing calculation, not a tested replacement design. Restricting travel is another possible design choice if the measured balance requirement supports it.

![Adjusted prop keepout crosses inner ring: orange is prop envelope, cyan is ring](/Users/devk/Documents/HackPHS26/cad/apex2-cage/review-2026-10-07/03-adjusted-prop-collision-detail-isolated.png)

The isolated red solid below is the **actual Boolean intersection volume**, displayed separately so the overlapping surfaces do not hide it.

![Actual 49.013782 mm3 intersection solid](/Users/devk/Documents/HackPHS26/cad/apex2-cage/review-2026-10-07/05-collision-intersection-witness.png)

**2. The modeled camera centerline is blocked by an outer-ring quarter.**

The wide view cone suggested obstruction, but cone overlap alone would not establish a central blockage. I tested the modeled optical centerline directly.

At the current **20° uptilt**, the lens origin is **(0, 29, 11.249) mm** and its direction is **(0, 0.939693, 0.342020)**. Exact point-containment checks along this line found points inside `outer_ring_quarter:1` from **57.9 to 62.8 mm** ahead of the lens. A separate narrow-cylinder intersection agreed.

This result does not depend on the 160° cone approximation. The outer ring occupies the central view in the current nominal layout. Camera position/aim and the ring arrangement need to be assessed together, then checked throughout the permitted gimbal motion. Define the acceptable moving-ring occlusion and verify usable target visibility; the current layout cannot be described as preserving an unobstructed central view.

In this Fusion capture, cyan is the actual outer ring, the yellow block is the camera placeholder, and the yellow line follows its modeled optical axis. The line was thickened to 0.6 mm only for visibility.

![Modeled camera centerline crosses the outer ring](/Users/devk/Documents/HackPHS26/cad/apex2-cage/review-2026-10-07/04-camera-centerline-obstruction-isolated.png)

**3. The 1100 mAh battery needs a complete fastener interface.**

The battery placeholders sit flush against the carrier underside, and the four frame mounting positions are at **X/Y = ±12.75 mm**. The native assembly contains no mounting screws, nuts or washers.

I introduced temporary **3.8 mm diameter × 2 mm high** nominal M2 cap-head envelopes directly below those mounting positions. Each overlaps the modeled 1100 mAh pack by **4.10828 mm³**; the four heads have zero overlap with the modeled 450 mAh pack. These head dimensions are a stated standard-size assumption from the local vendor-spec notes, not measurements of the supplied kit.

This is a confirmed conditional conflict. The exact installed orientation, heads, nuts, washers and any battery pad/spacer remain undecided. Model that fastening layout and battery leads before approving the 1100 mAh mount. Any added spacer also changes the battery height, CG and swept envelope.

**4. Kinematics are represented by positions and names.**

The live design contains **zero joints, zero as-built joints and zero rigid groups**. All occurrence grounding flags were false. The intended Z cage-to-outer, Y outer-to-inner and X inner-to-aircraft axes are described in the generator, but Fusion has no assembly constraints enforcing them.

Add the correct rigid membership, grounded reference and revolute relationships before using native joint motion to demonstrate mechanical freedom. Temporary mathematical rotations can identify collisions, as above, but cannot establish bearing friction, looseness or physical balance.

**5. Mass and fit information still need qualification.**

All current BRep bodies have material **Steel**. The root includes the large camera cone, prop keepouts, both pack placeholders and the fit fixture; its native mass reads **261.763 kg**. That number has no aircraft meaning.

An independent sum of the actual structural volumes gives **56.54 g** of solid PETG at the assumed 1.27 g/cm³ and **5.34 g** of rods at the assumed 1.55 g/cm³. Adding the generator's approximately 8.36 g hardware allowance reproduces the **~70.24 g** structure estimate. These are assumed-density calculations; they do not verify printed mass, aircraft mass, thrust or the all-up ceiling.

| Interface | Current modeled dimensions | Interpretation |
| --- | --- | --- |
| Carbon rod / socket | 1.00 / 1.30 mm diameter | 0.15 mm radial clearance; retention needs an actual fit/bond choice |
| MR52ZZ / bearing seat | 5.00 / 5.05 mm diameter | Nominal CAD clearance, despite the press-fit label; qualify with the coupon |
| Dowel / press hole | 2.00 / 1.90 mm diameter | Intended interference; print behavior is untested |
| Pins | 10.5 mm modeled, 16 mm stock parameter | The documented cutting operation or a revised full-length layout is required |
| Rod engagement | 4.75 mm | Includes the 0.25 mm floor gap |
| Main exposed rod span | ~35.03 mm | Useful test specimen length; strength is unverified |

The model contains 100 solid rods, so the sketch-like appearance was not missing rod geometry. It does not establish whether 1 mm rods can withstand the intended contacts. Bending, joint slip and pullout need representative rod/hub tests tied to the measured prop-clearance budget. The two lightened rings and their splices also need load testing.

Every physical measurement and mass override in `measurements.json` is currently null. Aircraft frame details, lens/mount, fastener heads, strap and wires are incomplete placeholders or absent. The fit coupons are a useful first print; a complete P1B print batch is premature.

**Checks that passed.**

- The structural assembly's bounding span is **245.991 × 243.208 × 248.000 mm**; its maximum span meets the 245–250 mm target.
- The current cage has **62 placed hubs and 100 rod solids**, consistent with the adopted truncated-icosahedral topology plus pole rods.
- The nominal static check examined 107 visible bodies and 233 bounding-box candidate pairs. It found only the six intended 2 mm pin / 1.9 mm press-hole overlaps.
- Each of the eight ring junctions touches its two intended quarters, and all six modeled pins engage their press parts and bearings with seated-bearing shoulder contact. The current bottom outer-ring junction is connected correctly. This establishes geometric contact only.
- All 112 timeline items reported healthy state.
- All 14 P1B part STLs and four plate STLs passed binary-length, finite-coordinate, closed-edge, manifold-edge and winding checks. The four plates start at Z = 0 and fit within 140 × 140 mm.
- Part STL bounds differ from native Fusion bounds by at most **0.0032 mm**; their approximate volumes differ by less than **0.095%**, consistent with tessellation.

These mesh checks exclude self-intersections, slicer behavior, supports, layer adhesion and physical fit. The discrete sweep does not certify every continuous pose.

**Upstream and evidence.**

The sole upstream design remains kert's **Thingiverse 408519**, preserved in [the reference package](/Users/devk/Documents/HackPHS26/cad/references/thingiverse-408519/README.md). The current Apex-2 assembly is a procedural adaptation with rebuilt interfaces. All current occurrences are local, with no external component reference; P1A/P1B share generator code and inputs rather than a live Fusion assembly link. Regenerate both designs after shared input changes. The reference photos show the historical aircraft and supply no measured Apex-2 geometry.

Evidence is stored beside this report: [model inventory](/Users/devk/Documents/HackPHS26/cad/apex2-cage/review-2026-10-07/model-inventory-before.json), [adjustment results](/Users/devk/Documents/HackPHS26/cad/apex2-cage/review-2026-10-07/adjustment-sweep.json), [static/optical/mass results](/Users/devk/Documents/HackPHS26/cad/apex2-cage/review-2026-10-07/static-optics-mass.json), [connectivity results](/Users/devk/Documents/HackPHS26/cad/apex2-cage/review-2026-10-07/connectivity.json), [fit/hardware/envelope results](/Users/devk/Documents/HackPHS26/cad/apex2-cage/review-2026-10-07/fit-hardware-envelope.json), [export audit](/Users/devk/Documents/HackPHS26/cad/apex2-cage/review-2026-10-07/export-audit.json), [source hashes](/Users/devk/Documents/HackPHS26/cad/apex2-cage/review-2026-10-07/source-sha256.json) and the inspection/diagnostic Python scripts.

No solid geometry or parameters were changed or saved. Temporary diagnostic graphics were removed, and the before/after body inventory, occurrence transforms, parameters and timeline matched. Fusion did set the document's modified indicator during the temporary graphics display; the saved cloud version remains 7. Diagnostic screenshots use translated copies of the measured geometry to isolate the issues.
