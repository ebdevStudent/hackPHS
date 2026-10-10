# Priorities and later features

Source: Google Doc **future**, read 2026-10-07. [Exact matrix](sources/google-doc-2026-10-07/08-future.md). Difficulty estimates are source planning judgments, not measured implementation effort.

## Scope and spending rules

P0–P2 is the core build. Manual contact/recovery plus live target tracking is an accepted fallback; physical yaw assistance is preferred only after complete bridge/override/failsafe verification.

Only the P1B gimbal cage is built (user decision, 2026-10-08). It must pass **ten consecutive low-energy contacts without damage/prop strikes, at least three minutes usable caged flight, and repeatable manual recovery** before demo use. P1A stays CAD-only.

P2.5/P3 additions require a working core and three clean rehearsals. P4/P5 cannot delay the physical demo. Pico wireless audio and the entire `toImplement` adoption remain explicitly deferred.

All planned parts are user-reported ordered. Additional spending is capped at **$200**, with at least **$30 reserved for replacements/rework**. Optional features receive no spending until the core works.

Freeze new hardware and feature additions **48 hours before the first judged demo**. Use the final **24 hours** for reliability, battery preparation, evidence and at least three consecutive complete rehearsals. During that period allow only fixes restoring already-working core functionality.

## Source feature matrix

| Feature | Value | Difficulty | Source priority |
| --- | --- | --- | --- |
| Battery endurance matrix | Compare real energy/weight and handling | 1/5 | P0 |
| Four-state RGB indicator | Show MANUAL / SEARCH / LOCK / FAULT | 1/5 | P2 |
| Forward inspection LEDs | Illustrate inspection in dark spaces | 1/5 | P3 |
| Fixed-cage fallback | Protect the demo if gimbal integration fails. Not planned: P1A is CAD-only (user decision, 2026-10-08); zip-tied rings are the interim fallback | 2/5 | P1A (not built) |
| Yaw-only visual autonomy | Bounded closed-loop target centering | 2/5 | P2 |
| Quick-release battery / adjustable center mount | Faster testing and CG adjustment | 2/5 | P1 |
| CSV telemetry + post-run summary | Evidence, debugging and presentation | 2/5 | P3 |
| Small pitch-based target approach | Forward motion after yaw lock | 3/5 | P2.5 |
| AprilTag/ArUco inspection + automatic snapshot | Target identity and inspection action | 3/5 | P3 |
| Minimal digital-twin state sync | Mirror key mission states | 4/5 | P4 |
| Modular payload MCU / sensor port | Future mission sensors | 4/5 | P4/P5 |
| Two-way audio | Rescue communication concept; deferred | 4/5 | P5 |
| Blackbox collision analytics | Quantify contact events | 3/5 | P4 |
| Autonomous landing | Later end-of-mission autonomy | 4/5 | P5 |
| Optical flow / LiDAR / mapping | Positioning/ranging/environment maps | 5/5 | P5 |
| Wall climbing / toss recovery | High-uncertainty mobility experiments | 5/5 | P5 |
| Multiple simulation maps | Broader presentation after one polished map | 2/5 | P5 |

The existing simulator already includes industrial and rescue maps. Prioritize a stable industrial demonstration; geometry matching to the aircraft is not required. The existing software already writes CSV/replay data, but an aircraft mission summary still requires real input and evidence.

A source-listed future feature is not an authorization to implement or buy it. Promote work only after its prerequisites, available time and the freeze rule are satisfied.

## Ground-Pi navigation planning — 2026-10-08

The user requested that the video/navigation discussion be planned and documented for another Codex session. See the [navigation plan](20-semi-autonomous-navigation.md) and [handoff prompt](21-navigation-codex-handoff.md).

Recommended sequence: real FPV/timing → verified yaw assistance → calibrated marker localization → mapped guidance while the pilot flies → optional later automatic movement. Localization/guidance can be explored with commands disabled while the bridge remains incomplete. An Intel depth-camera scan is offered, but exact hardware and scan/calibration files are pending. Begin with one small test zone rather than assuming a complete-area scan is necessary.

This is planning approval; the source priority matrix remains historical context. It does not select translation/altitude authority, fund optional purchases or authorize physical output. Yaw-only scope, the accepted manual demo, core-build gates, contingency reserve, freeze and deferred Pico/audio/toImplement remain in effect.

[Build gates](10-build-and-test.md) · [Demo runbook](12-demo-runbook.md) · [Budget](02-bom.md).


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Google Doc — future tab](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit?tab=t.9zl6mz9qzdr6) — Source snapshot captured 2026-10-07.
- [Deferred source tab](sources/google-doc-2026-10-07/09-to-implement.md) — Preserved for reference; adoption is deferred by user instruction.
