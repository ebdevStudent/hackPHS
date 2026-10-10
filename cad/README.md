# Ball Drone CAD workspace

Use [CAD guidance](../docs/03-cad.md) for the design scope and missing measurements.

Generated vendor/provisional models in [apex2-cage](apex2-cage/README.md): current Apex-2 (~95 mm wheelbase) aircraft envelope with 2-inch prop disks, battery and camera; a 245–250 mm outer cage; one adjustable aircraft carrier; interchangeable P1A fixed supports and P1B removable two-ring gimbal supports. Reuse the aircraft carrier and cage attachment interfaces across both configurations.

The [Thingiverse reference package](references/thingiverse-408519/README.md) preserves the two user-supplied ZIPs, original attribution/license and inspected mesh inventory. Upstream means kert’s Thingiverse design only. Adapted project geometry is generated separately; reference meshes remain original reference-only parts. See the [2026-10-08 Fusion review](apex2-cage/review-2026-10-08/README.md) for verified geometry and outstanding physical checks. Keep future generated models separate from references and record origin, units, revision and verification status.

The [CAD kit](kit/README.md) reads the generators without changing them. It provides:

- the arrival measurement form and checker;
- the rod/hub bend-test pieces, jig and pin cutting gauge;
- the cage-opening probe (objects under ~84 mm can reach the props);
- the P1B mass options against 175 g;
- the settled pin, bonding and camera-tilt decisions.

Use measured hardware dimensions before finalizing sockets, pivots, bearings, or mounts. Check the full reachable prop-clearance envelope and estimated mass before printing.

Use [the mechanical CAD/printing brief](../docs/17-mechanical-cad-brief.md) for modular Voxel-sized PETG parts, calibrated fits, print orientation, assembly documentation and P1A-first sequencing. Retain the established 1 mm carbon-rod baseline.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Current CAD plan](../docs/03-cad.md) — P1A-first geometry and clearance requirements.
- [Thingiverse reference archive](references/thingiverse-408519/README.md) — User-supplied ZIP inventory, attribution and file checksums.
- [Thingiverse 408519](https://www.thingiverse.com/thing:408519) — Only upstream CAD design named by the user.
