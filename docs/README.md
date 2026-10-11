# Ball Drone documentation

**AprilTag follow / landing guidance (2026-10-11):** [how to make, print, load and use tags](31-apriltags-and-tracking.md); Pi `drone-mode fpv|track|assist`.

**>>> LATEST CLAUDE HANDOFF (2026-10-11, read first): [HANDOFF-CLAUDE-2026-10-11.md](../HANDOFF-CLAUDE-2026-10-11.md)** — flight checklist, current status of every link, AprilTag status, audit fixes, camera-feature next steps.

**2026-10-11 Claude bench session:** [summary](30-claude-session-summary-2026-10-11.md): Motor 1 fixed (test value too low), FPV video working end to end, VTX on R8 5917 MHz, Angle-mode settings staged, motor dashboard with Camera tab.

**2026-10-11 actual bench handoff:** [Flight controller, Motor 1 fault, and full Pi/ESP32/Pocket/FPV pipeline](29-claude-flight-controller-handoff-2026-10-11.md). This dated record supersedes older no-output/Mega/source-location assumptions for the adopted `ebdevStudent/hackPHS` `esp32-trainer-ppm` branch. Motor 1 starts but stops/restarts at command 1020; continuous reliable rotation is not verified. The optional direct USB helper is `tools/betaflight_motor_bench.py`; exact executed scripts and the earlier Claude source handoff are preserved under `docs/sources/bench-handoff-2026-10-11/`. Full trainer-to-FC trials remain pending.

**P1B print package — 2026-10-09:** [Start printing](../cad/apex2-cage/print_now/START_HERE.md). All final plates, profiles, native model and assembly/validation records are in `cad/apex2-cage/print_now/FINAL_P1B/`; the ZIP is alongside that folder. Print T3 first, then qualify section retention and strength.

Updated **2026-10-10** (combined CAD print delivery, Flutter/portable mission software, and ESP32-S3 bridge-board selection; source snapshot remains 2026-10-07) from [HackPHS 2026](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit) and the user's follow-up decisions.

## Current baseline

Build an **Apex-2 (~95 mm wheelbase) quad with 2-inch props** inside a lightweight **245–250 mm cage**. The cage carries the aircraft in a **two-ring gimbal (P1B)**. That is the only version being built (user decision, 2026-10-08); the fixed-cage variant (P1A) stays in CAD as a reference.

Betaflight owns normal flight/stabilization. The Pi4/5 plan runs local FPV/HSV tracking and monitoring. The user-selected flight-assistance bridge board is the **Freenove ESP32-S3 WROOM**, through a verified trainer/radio/ELRS path; the team does not have the previously planned Mega 2560. A no-output ESP32-S3 USB-UART protocol port is implemented; Mega and Pico artifacts remain historical compatibility evidence. No board-specific trainer output or aircraft channel behavior is verified.

A manual-contact/live-tracking demo is accepted success. Prefer yaw assistance only when the complete physical bridge, override and signal-loss/failsafe gates pass. Keep the manual route rehearsed and available. Simulation stays a separate, illustrative Mac application demo.

**Flutter operator client:** distinct Flutter desktop/web and Android layouts are implemented and inspected. The Python backend now serves the visual mission contract; WebRTC/audio and physical aircraft integration remain unavailable. See the [client](../software/flutter_operator/README.md) and [backend handoff](../software/flutter_operator/BACKEND_HANDOFF.md). Audio/TTS is outside the current portable-missions plan. The Pico-specific wireless implementation path and the ninth Google Doc tab, `toImplement`, remain deferred. See the [Flutter UI development plan](../UIDEVPLAN.md).

The current mission direction is **portable visual interaction in a controlled, unmapped space**, using FPV and AprilTags. **D435 room mapping will not be done for this project/demo.** Its existing code remains in the repository intact, and its historical records are retained with current-scope notes; they are not active tasks or prerequisites. The [portable missions software plan](27-portable-visual-missions-plan.md) now records the implemented mock mission backend, relative pose services and Flutter API adapter, plus the remaining camera calibration and device gates. The [navigation runbook](23-navigation-software.md), [staged navigation plan](20-semi-autonomous-navigation.md), and [pre-camera implementation record](26-pre-camera-software.md) document the earlier mapped-navigation work and should not be treated as the current demo plan. Current implementation does not establish physical acceptance or expand yaw-only authority.

## Start here

| Need | Document |
| --- | --- |
| Run and verify the completed hardware-free software | [Hardware-free completion](28-hardware-free-completion.md) |
| Understand V1 and success criteria | [Idea](01-idea.md) |
| Plan Flutter Android/desktop screens and the backend handoff | [Flutter UI development plan](../UIDEVPLAN.md) |
| Check ordered plan, source links and $200 contingency | [BOM](02-bom.md) |
| Adapt cage/gimbal geometry | [CAD](03-cad.md) |
| Understand intended control path and existing-code gaps | [Software](04-software.md) |
| Assemble/identify actual equipment | [Hardware](05-hardware.md) |
| Run the industrial application game | [Simulation](06-simulation.md) |
| Find source images and evidence | [References](07-refs.md) |
| Decide what can be added and when | [Priorities](08-future.md) |
| Apply physical build gates | [Build and test](10-build-and-test.md) |
| Check what is actually delivered/verified | [Implementation status](11-pre-hardware-status.md) |
| Rehearse the manual or conditional assisted demo | [Demo runbook](12-demo-runbook.md) |
| Fill in actual measurements and trainer interface | [Hardware arrival](13-hardware-arrival.md) |
| Operate the existing native app | [Desktop workstation](14-desktop-app.md) |
| Reproduce software checks and separate physical acceptance | [Verification](15-verification.md) |
| Connect Fusion MCP clients | [Fusion MCP](16-fusion-mcp.md) |
| Plan modular Voxel/PETG parts and inspect original Thingiverse files | [Mechanical CAD and printing brief](17-mechanical-cad-brief.md) |
| Review mechanical gaps and remaining validation | [Mechanical review](18-mechanical-review.md) |
| Print and test the cage on the Monoprice Voxel (settings, print order, fit tests, measurements, thrust test) | [Print and test plan](../cad/apex2-cage/PRINT_AND_TEST_PLAN.md) |
| Hover/rolling throttle, thrust-to-weight, rolling physics, speed, endurance, gimbal torques and contact energy (estimates) | [Motion physics](22-motion-physics.md) |
| Generated P1A/P1B CAD, parts, checks and assembly | [CAD workspace README](../cad/apex2-cage/README.md) |
| Compare similar cage and gimbal CAD projects | [CAD reference research](19-cad-reference-research.md) |
| Inspect retained mapped-navigation/D435 implementation (not current demo work) | [Navigation software](23-navigation-software.md) |
| Track the authorized pre-camera software implementation | [Pre-camera implementation](26-pre-camera-software.md) |
| Plan portable FPV/AprilTag missions without requiring a camera or room map | [Portable visual missions software plan](27-portable-visual-missions-plan.md) |
| Review staged ground-Pi vision, localization and mapped guidance | [Semi-autonomous navigation plan](20-semi-autonomous-navigation.md) |
| Give the navigation context to another Codex session | [Navigation handoff prompt](21-navigation-codex-handoff.md) |
| Run the judged demo: roles, timing, failure branches, three-run record | [Judge script and rehearsal checklist](24-judge-script.md) |
| Record static thrust, batteries and the 10-contact gate | [Physical test records](25-test-records.md) |
| Enter arrival measurements, print the bend test, check cage openings and P1B mass | [CAD kit](../cad/kit/README.md) |

## Adopted Google Doc tabs

| Source tab | Maintained document |
| --- | --- |
| Idea | [01-idea.md](01-idea.md) |
| BOM | [02-bom.md](02-bom.md) |
| CAD | [03-cad.md](03-cad.md) |
| Software | [04-software.md](04-software.md) |
| Hardware | [05-hardware.md](05-hardware.md) |
| Simulation | [06-simulation.md](06-simulation.md) |
| refs | [07-refs.md](07-refs.md) |
| future | [08-future.md](08-future.md) |
| toImplement | **Deferred by user; no new maintained task document** |

The old ninth-tab file, [Further Improvement / Feedback](09-further-improvement-feedback.md), is historical reference retained for existing links.

## Decisions governing the rewrite

- **Ordering:** all currently planned parts have been ordered, per the user. Delivery and compatibility still need evidence.
- **Battery inventory:** user reports four OVONIC 450 mAh and two OVONIC 2S 7.6 V 60C XT30 1100 mAh packs. The 1100 mAh listing contains inconsistent configuration/dimension fields; the packs exceed the Apex-2 seller's 650 mAh recommendation and remain flight-unverified. Use measured pack dimensions for CAD.
- **Contingency:** extra purchases have a $200 hard cap; reserve at least $30 (15%) for replacements, failed prints, shipping issues and rework. Optional purchases wait for a working core.
- **Flight gate (on the P1B gimbal build):** ten consecutive low-energy contacts without damage/prop strikes, at least three minutes usable caged flight and repeatable manual recovery. No fixed cage is built; the fallback is flying P1B with its rings zip-tied to the cage.
- **Assisted route:** conditional on full physical ESP32-S3/radio, override and failsafe verification. Physical yaw assistance is not required for success.
- **Manual screen:** live FPV, colored-target box, center/error indicator and “Manual steering — computer steering unavailable.”
- **Simulation:** verified code parameters describe the earlier Meteor85-class model with a 112.5 mm cage circumradius, 5 mm hub radius and 50.8 mm (2-inch) props. An earlier copied README says ~372 mm/4-inch, which does not match those code parameters. Simulation remains illustrative; matching the physical plan is not required.
- **Freeze:** no new hardware/features starting 48 hours before the first judged demo. Final 24 hours are reliability, batteries, evidence and at least three complete consecutive rehearsals; only fixes restoring working core functionality.
- **Deferred:** `toImplement` and Pico wireless audio.

## Authority and history

The **2026-10-07 source plus the user's clarifications** govern the current plan. Source estimates and vendor descriptions are not measured results. New user decisions refine the source: a manual-contact/live-tracking fallback counts as success, portable visual missions use no room map, D435 mapping will not be done for this project/demo, the ESP32-S3 WROOM replaces the unavailable Mega as the selected bridge board, and ordering/budget/gimbal/freeze rules are explicit.

- [Current source snapshot](sources/google-doc-2026-10-07/README.md): all nine tabs captured, with original text/tables/links, tab/revision metadata and five images. The ninth is reference capture only.
- [Earlier Google Doc snapshot](sources/google-doc-2026-10-04/README.md): preserved historical baseline.
- [Local docs before rewrite](sources/local-docs-before-rework-2026-10-07/README.md): preserved originals, including earlier 85 mm/Pico descriptions.
- [Decision log](decisions.md): dated history plus this rewrite.
- [Recorded evidence](../evidence/README.md): results retain their original environments, source manifests and limits.

The source's updated CAD concept is not a manufacturing drawing. Generated vendor/provisional Fusion models and the [2026-10-08 geometric review](../cad/apex2-cage/review-2026-10-08/README.md) are now available; physical acceptance remains pending. No measured local CAD or actual trainer/flight acceptance was found. Software tests are primarily Mac/container/mock evidence; existing Mega and Pico firmware have no verified trainer output and establish no physical ESP32-S3 behavior. The Pi 5 Trixie install/service check passed on the actual board, but its saved capture returned uniformly black frames. Live RC832 input, Pi performance, ESP32 serial integration and physical control remain unverified; see the [Pi evidence](../evidence/physical/pi-preflight-2026-10-08.txt).

## Maintaining the docs

Keep each adopted source tab in its own file. Save new dated source captures rather than overwriting older ones. Update working requirements and append a decision when scope or evidence changes.

Label source claims, planned work, user-reported status and measured results distinctly. Never turn a mock ACK, synthetic trace, game animation or hardware-free test into an aircraft claim. Keep private tokens/runtime logs in ignored storage and save reviewable evidence separately.

[CAD workspace](../cad/README.md) · [Wasim's simulator at the repository root](https://github.com/WasimVorvoi/HackPHS#wasims-existing-ball-drone-flight-sim) · [Software source](../software/README.md).


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [HackPHS 2026 Google Doc](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit) — Current source revision is recorded in the snapshot metadata.
- [OVONIC 2S 1100 mAh 60C XT30 two-pack listing](https://us.ovonicshop.com/products/2-ovonic-rebel-2-0-60c-2s-1100mah-lipo-battery-lihv-7-6v-pack-with-xt30-plug-for-size-100mm-to-140mm-brushless-drones-long-range-drone-fpv) — Vendor identity/specification reference; inconsistent fields require physical verification.
- [Apex-2 frame listing](https://speedyfpv.com/products/apex-2-2-inch-95mm-carbon-fiber-drone-frame-kit?variant=46334350164182) — Seller battery recommendation, not a manufacturer performance guarantee.
- [2026-10-07 source snapshot](sources/google-doc-2026-10-07/README.md) — All nine tabs and revision metadata.
- [Decision log](decisions.md) — User decisions and change history.
