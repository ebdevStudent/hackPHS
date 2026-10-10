# Mechanical CAD and printing review — 2026-10-07

**2026-10-09 follow-up:** [Final digital P1B plates and assembly guide](../cad/apex2-cage/print_ready_p1b/README.md) now pass source, mesh, inventory, bed and native-interface checks. Only P1B is built, superseding the fixed-cage-first sequence below. User-reported coupons are applied; physical retention, actual-frame fit, loaded clearances, mass, thrust and flight gates are still open.

**2026-10-08 historical follow-up:** This 2026-10-07 source review remains historical. Generated vendor/provisional CAD has since been inspected and corrected; see [the new Fusion review](../cad/apex2-cage/review-2026-10-08/README.md). Its geometric checks do not close the physical findings below. Detailed P1B CAD was requested early by the user; the P1A gate still governs flying it.

Scope: current CAD/printing docs, related BOM/hardware/build/arrival/priorities guidance, supplied mechanical brief and the two preserved Thingiverse ZIPs. This is a source/documentation review. It does not assess the whole software implementation or certify an aircraft.

## Findings, ordered by practical impact

| Priority | Finding and consequence | Documentation action | Remaining evidence |
| --- | --- | --- | --- |
| P1 | No measured added-structure mass allowance. A print can fit the bed and still exceed the aircraft's thrust/endurance budget. | Added a pack-specific mass worksheet and pre-batch review condition. | Bare/pack masses, thrust at stated voltage, slicer/weighed mass and flown endurance. |
| P1 | A 1 mm rod choice is not validated by the original 3 mm design. The ordered listing gives no rod strength/modulus data. Flex, buckling, socket pullout or joint slip could erase nominal prop clearance. | Keep 1 mm as a prototype baseline; add a sourced comparative calculation and specify a representative load/deflection/retention test before the cage batch. | Actual rod construction/lot, load case, loaded/residual deflection, retention and clearance under recorded conditions. |
| P1 | Checking cage/ring/wire self-interference does not show that cage openings intercept an outside object. A narrow edge can bypass an open cage. | Added intended-object/probe checks and limited protection claims to tested geometry. | Recorded obstacle/probe dimensions, approach directions and minimum separation. |
| P1 | “Ten low-energy contacts” lacked a repeatable setup and explicit damage inspection. Changing conditions could make successive results incomparable. | Added contact protocol fields, per-contact inspection and reset criteria. | Defined setup, footage, inspection records and repeatable manual recovery evidence. |
| P2 | X/Y adjustment was described as aligning CG with the gimbal-axis intersection. It cannot correct an unknown vertical offset. | Corrected the plan to retain X/Y adjustment and measure 3D CG/axis offset per pack before P1B. | Actual vertical offset, carrier/axis placement, friction, retention and balance checks. |
| P2 | The outside cage diameter was not defined precisely enough to infer interior clearance. Faces and hubs can lie inside the maximum vertex/span envelope. | Defined target as maximum assembled outside span and required minimum internal-envelope measurements. | Parametric geometry and full loaded clearance review. |
| P2 | Repeated disassembly and replaceable hubs were not reconciled with the provisional epoxy purchase. Bonded pieces may be replaceable only as a unit. | Separated service joints from bonded subassemblies and required a documented replacement unit. | Selected fastening/bonding method and repeated-assembly/retention checks. |

P1 findings should be resolved before a complete cage print/flight claim. Future-gimbal findings apply before P1B. Fixing documentation does not close the physical findings.

## Why rod diameter needs testing

For a solid circular rod, the second moment of area is I = πd⁴/64. Under equal material assumptions, 1 mm has 1/81 of the 3 mm section's bending stiffness EI; 1.5 mm has about 5.06 times the 1 mm section's EI. As an illustration only, applying the Easy Composites lengthwise modulus range for its own pultruded rod to a pinned 66.5 mm unsupported member gives ideal Euler buckling estimates of 3.1–4.4 N (1 mm), 15.5–22.2 N (1.5 mm) and 248–355 N (3 mm). The 66.5 mm length is from the Thingiverse README; the material properties are from a different manufacturer's product and must not be assigned to the ordered VictorsHome rods. These estimates assume a straight ideal member with pinned ends and do not predict the complete cage or impact response. The actual joints, fiber layup, effective span and load path can change results substantially. See [the full comparison and sourced assumptions](19-cad-reference-research.md#structural-question-is-1-mm-rod-enough).

## Checks completed

- Both preserved ZIP checksums match the inventory; archive CRC checks pass.
- Every inventoried file's checksum matches its ZIP entry.
- All 18 STLs have consistent binary lengths, finite vertex data and reproduced raw bounding-box extents.
- Part 2 adds images rather than new STLs. Two original filenames explicitly say DO_NOT_PRINT and remain reference-only.
- Source README/license and the supplied mechanical brief remain unchanged.
- The maintained docs preserve Apex-2/~95 mm, 2-inch props, 245–250 mm cage, fixed-cage-first, the exact gimbal gate, manual demo fallback, contingency/freeze and deferred audio/toImplement.
- PETG settings and fit gaps are labeled prototype trials; the [Voxel specification](https://monopricesupport.kayako.com/article/283-buyers-guide-voxel) does not establish successful PETG printing on this actual device.

These mesh checks do not test watertightness, printable orientation, assembled ring axes, bearing fits, material strength or swept collisions.

## Recommended next mechanical step

Record delivered aircraft/prop/battery/rod dimensions and masses, then make a small socket/connector coupon and one representative cage section. Use those results to set fit, retention and flex allowances. Complete the mass worksheet and fixed-cage clearance model before a full print batch. Keep detailed gimbal work behind the agreed P1A gate.

**Assessment:** The documented architecture is a reasonable prototype direction. It is not yet a dimensioned, print-ready or flight-validated design. The biggest unknowns are mass margin and loaded protection/clearance.

**Rod answer:** Axial tensile strength by itself does not answer whether 1 mm is enough. The purchased listing has no engineering rating, and thin members may be governed by bending, buckling or joint retention. Keep 1 mm as a test candidate only; the representative test results must decide whether the chosen spans and hubs preserve clearance.

[CAD plan](03-cad.md) · [Mechanical brief](17-mechanical-cad-brief.md) · [Build/test](10-build-and-test.md) · [Arrival measurements](13-hardware-arrival.md) · [Original Thingiverse package](../cad/references/thingiverse-408519/README.md).


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [CAD reference research](19-cad-reference-research.md) — Sourced comparison and simplified rod-stiffness/buckling assumptions.
- [Thingiverse 408519](https://www.thingiverse.com/thing:408519) — User-designated upstream reference.
- [Easy Composites 1 mm rod data](https://www.easycomposites.co.uk/1mm-carbon-fibre-rod) — Properties apply only to this other supplier product.
- [Pultrusion technical datasheet](https://media.easycomposites.co.uk/datasheets/EC-TDS-Carbon-Fibre-Pultrusions.pdf) — Source for the illustrative lengthwise modulus range.
