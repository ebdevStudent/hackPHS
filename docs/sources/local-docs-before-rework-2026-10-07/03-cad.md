# CAD

Source: Google Doc **CAD** tab, read 2026-10-04. [Preserved tab text](../google-doc-2026-10-04/03-cad.md). Current user decisions are recorded in [decisions.md](decisions.md).

All geometry targets are provisional.

## Cage and mounts

The source names [Thingiverse 408519](https://www.thingiverse.com/thing:408519) as a CAD reference. Its geometry and license have not been inspected in this local project.

- Provisional outer diameter: about 220–230 mm.
- Source proposal: scale the reference to roughly 70% overall, then resize hardware interfaces independently.
- Candidate cage: 30 straight rods and 12 five-way hubs.
- Candidate rods: 1 mm carbon fiber or fiberglass; reinforce selected locations with 1.5 mm only if testing justifies the mass.
- Candidate hubs: TPU 95A, with hub volume minimized.
- Start with a fixed center mount; make gimbal rings removable.
- Allow X/Y adjustment of the quad and battery for balancing.
- Use a strap battery mount that accommodates the planned test packs.
- Size sockets, bearings, pivots, and mounts from the actual parts.

## CAD checkpoints

1. Establish an axis convention and measured component envelopes.
2. Model the bare quad, prop disks, battery, camera, and wiring.
3. Build the fixed cage and adjustable center mount.
4. Check prop separation, camera view, battery access, airflow, and mass estimate.
5. Add removable gimbal rings and pivots.
6. Sweep the full mechanically reachable motion; require zero prop intrusion from cage, rings, or wires.
7. Review manufacturing geometry against measured hardware before printing.

## Missing inputs

- Exact component CAD or measured dimensions, mounting-hole patterns, and masses.
- Cage reference files and license review.
- Bearing/pivot sizes, gimbal geometry, manufacturing constraints, and material choices.
- Bare-aircraft mass/thrust data and the cage/gimbal mass budget.

See [hardware](05-hardware.md) for component/interface unknowns and [BOM](02-bom.md) for purchasing candidates. No finished CAD model or clearance result exists in this workspace.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Pre-rewrite archive index](README.md) — identifies this file as historical context, not current instruction.
- [Maintained document](../../03-cad.md) — current requirements and status.
- This citation note is external to the preserved pre-rewrite text.
