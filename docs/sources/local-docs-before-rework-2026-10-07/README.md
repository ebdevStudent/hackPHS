# Ball Drone project documentation

The HackPHS 2026 project is a contact-tolerant indoor drone: an 85 mm quad inside a lightweight cage, with ground-computer visual target detection and optional yaw assistance. The current demo target is Pi 5 processing/server, with Mac development and simulation.

## Google Doc tabs

Each Google Doc tab has a separate maintained Markdown file and a separate dated source snapshot.

| Google Doc tab | Current file |
| --- | --- |
| Idea | [01-idea.md](01-idea.md) |
| BOM | [02-bom.md](02-bom.md) |
| CAD | [03-cad.md](03-cad.md) |
| Software | [04-software.md](04-software.md) |
| Hardware | [05-hardware.md](05-hardware.md) |
| Simulation | [06-simulation.md](06-simulation.md) |
| refs | [07-refs.md](07-refs.md) |
| future | [08-future.md](08-future.md) |
| Further Improvement / Feedback | [09-further-improvement-feedback.md](09-further-improvement-feedback.md) |

Supplemental files: [physical build and test](10-build-and-test.md), [pre-hardware preparation status](11-pre-hardware-status.md), [demo runbook](12-demo-runbook.md), [hardware-arrival worksheet](13-hardware-arrival.md), [recorded evidence](../../../evidence/README.md), and [decision log](decisions.md).

[Native desktop app for Mac and Pi](14-desktop-app.md): operator workstation, standalone Mac application, Pi desktop installation and remote connection to a headless Pi. Visitor browser access remains available.

[Software verification](15-verification.md): repeatable test command, acceptance-to-test mapping, coverage gates and provenance reports.

[Fusion MCP connection prompts](16-fusion-mcp.md): connect Cursor and Antigravity to the existing Fusion server used by Claude and Codex.

[CAD workspace](../../../cad/README.md).

[Simulation repository and run instructions](https://github.com/WasimVorvoi/HackPHS#wasims-existing-ball-drone-flight-sim).

**Demo deployment:** the simulation runs on the user's Mac. The Raspberry Pi 5 runs tracking/control calculations and the demo server, accessible through a browser on either BallDrone-Demo hotspot or a shared network. Mac software and Linux ARM64 checks are recorded; actual Pi/network/device operation remains unverified. See [software deployment](04-software.md#demo-deployment).

## Source and current status

- **S1:** [HackPHS 2026 Google Doc](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit), read on 2026-10-04.
- [Separate text snapshots of all nine source tabs](../google-doc-2026-10-04/README.md).
- **S2:** [WasimVorvoi/HackPHS](https://github.com/WasimVorvoi/HackPHS), cloned to `simulation/` on 2026-10-04. Branch `main`, commit `f472e4fcf0ed1e19141bcfb42f1afa4ac302e7e3`. Source checkout and short playable browser smoke confirmed for both maps; see [simulation evidence](../../../evidence/simulation-smoke.json).

These files document the current idea, intended physical build and a runnable hardware-free software demonstration. Tested software/controller/firmware-foundation evidence is present; physical control-path and flight results are not established by this folder. Component choices, dimensions, endurance, thrust margin, and delivery expectations remain targets or candidates until checked.

The source contains detailed review notes alongside concise final rules. The maintained docs follow the explicit V1/final rules: fixed-cage P1A first, removable gimbal P1B later, and yaw-only V1 assistance. Pitch assistance is a later upgrade. Source passages discussing yaw plus pitch do not authorize adding pitch to V1.

Vendor links in the snapshot were reported as checked on October 3. Recheck availability, compatibility, and checkout delivery dates before ordering.

## Keeping these docs current

1. Update the relevant current document when scope, geometry, component selection, or a result changes.
2. Append a dated decision entry with the reason and evidence link.
3. Save new evidence or source snapshots under `docs/sources/` with an origin and date.
4. Distinguish **source statement**, **provisional target**, **planned work**, and **verified result**. A planning document is not evidence that a build or test passed.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Current documentation index](../../README.md) — governing maintained scope.
- [Current Google Doc snapshot](../google-doc-2026-10-07/README.md) — later source; user deferred its `toImplement` tab.
- This citation note is an annotation to the historical archive index.
