# Implementation status and remaining physical work

Updated 2026-10-10 with the user's ESP32-S3 bridge-board selection. The actual Pi 5 app service and worker health endpoint are healthy; the saved camera check returned black frames, while the user's newer V4L2 output identifies a USB video capture node and supported formats. Live RC832 picture, ESP32 serial integration, survey and physical output remain pending.

## Current plan versus delivered foundation

| Area | Current intended plan | Existing artifact / limit |
| --- | --- | --- |
| Aircraft | Apex-2 ~95 mm, Specter 1202.5 motors, 2-inch props | Planned parts user-reported ordered; delivery/fit/flight not established here |
| Cage | 245–250 mm target; P1B gimbal is the only build (P1A CAD-only, 2026-10-08) | Parametric P1A/P1B generators, exports and plates ([CAD](../cad/apex2-cage/README.md)); [CAD kit](../cad/kit/README.md) adds the arrival form, bend-test pieces, opening probe and mass options. Openings let objects under ~84 mm reach the props; P1B + 1100 mAh sits at the 175 g limit. Physical fit/contact/endurance unverified |
| Vision | RC832 composite via USB capture to Pi 5 | OpenCV/V4L2 opens `/dev/video0` and reads frames as `ball-demo`, but observed frames are uniformly black; live FPV, HSV tuning and useful camera latency remain pending |
| Ground bridge | User-selected Freenove ESP32-S3 WROOM → verified trainer/radio | No-output USB-UART protocol port implemented and host-tested; target build evidence in docs/28. Actual serial enumeration, flashing and trainer output remain unverified. Mega/Pico are historical |
| Monitoring | Live vision/HUD and separate Wi-Fi preview | Manual-fallback screen implemented (`/fallback`, native fallback view) with operator lease, stale-video and frozen/blank-picture faults; needs live-FPV acceptance |
| Simulation | Illustrative Mac industrial demo | Free-flight Three.js game with three maps; industrial inspection markers; asserting smoke and physics checks; larger virtual geometry |
| Navigation | Repeatable D435 corner map, N3/N4 advisory and automatic mock movement | Software, schemas, replay, UI/planner and registered-depth reconstruction implemented; physical acceptance pending |
| Pico wireless audio / ninth tab | Deferred | No adoption or implementation authorized by this rewrite |

Software defaults remain MANUAL/disabled/mock at startup. Synthetic yaw, mock ACKs and game motion are not physical aircraft telemetry.

## Current navigation delivery

[Runbook](23-navigation-software.md) gives exact launch/replay/capture/rebuild commands. [Navigation evidence](../evidence/navigation/README.md) and [fresh verification](../evidence/verification/README.md) cover current Mac source, independent worker/control tests, browser/native guidance, synthetic autonomous completion and deterministic map reconstruction. The Pi 5 identity and installation are now verified on-device; `/dev/video0` reads frames, but the selected session faults on the uniformly black capture. The live RC832 picture and D435 station/tag survey remain pending. Historical handoff archives may predate navigation.

## Saved software evidence

[Verification records](../evidence/verification/README.md) dated **2026-10-04** report:

| Environment / profile | Python results | Combined statement/branch coverage |
| --- | --- | --- |
| Mac ARM64 desktop | 4,059 passed; zero failures/errors/skips | 99.58% |
| Linux ARM64 container desktop | 4,059 passed; zero failures/errors/skips | 99.63% |
| Mac core, Qt UI excluded | 3,697 passed | 99.50% |

Portable C checks used UBSan on Mac and ASan + UBSan on Linux. Results apply to their recorded source manifests, synthetic/fake devices, local processes/PTY and offscreen Qt. Later interface edits and the present documentation rewrite are not automatically covered by those results.

Other saved evidence: fixture checks, fresh-install/ARM64 smoke, browser walkthrough, a **1800.16-second Mac browser rehearsal**, and [simulation smoke](../evidence/simulation-smoke.json). The browser rehearsal recorded zero responsiveness failures, three injected ACK faults and one unplanned stale-frame event; processing averaged 18.62 FPS against the 20 Hz target. It was not native-desktop endurance or Pi/flight validation.

A historical Pico UF2 and Mega sketch were compiled, not flashed/electrically verified for aircraft output. Neither provides verified trainer output. The selected ESP32-S3 now has a separate no-output protocol port.

## Prepared deployment

The existing installers target **Pi 5, 64-bit OS/Python 3.13+**. On 2026-10-08 the actual Pi 5/Trixie/Python 3.13 passed preflight; the app installed, and `ball-demo.service` is enabled/active with healthy workers in MANUAL/mock mode. OpenCV can read 640x480 frames from `/dev/video0`, but 30 measured frames were uniformly black and the app entered FAULT/disabled. Live RC832 image, throughput under useful video, thermal behavior, networking and desktop display remain unverified. See the [physical Pi report](../evidence/physical/pi-preflight-2026-10-08.txt).

Mac develops/rehearses and runs the separate port-8765 game. The monitoring backend uses port 8080 by default; the native workstation can connect to a headless Pi. Hotspot/shared-network scripts and visitor cards are prepared, not evidence of physical network success.

The installed Mac app was rebuilt from current source on 2026-10-08 ([packaged run](../evidence/desktop/mac-packaged-2026-10-08/README.md)). Rebuild after later source edits; source UI and packaged UI must still be distinguished.

## Immediate readiness path

1. Identify delivered parts and record dimensions/masses/actual board and radio variants.
2. Establish manual Betaflight/ELRS flight and RC832 capture to the Pi.
3. Make the manual fallback screen meet its required live-video/box/error/status content.
4. Build and test P1B against the exact contact/endurance/recovery gate.
5. Implement/verify the ESP32-S3 trainer path separately; choose assisted presentation only after full gates.
6. Preserve a rehearsed manual route and one stable industrial game.
7. Apply the $200 contingency and 48-hour freeze.

No saved result here establishes actual cage-contact/endurance, trainer electrical output, physical override or complete aircraft latency. Physical yaw assistance is optional for success; truthful live manual/vision capability is mandatory for the accepted fallback.

[Build gates](10-build-and-test.md) · [Arrival worksheet](13-hardware-arrival.md) · [Software](04-software.md) · [Runbook](12-demo-runbook.md).


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Saved evidence index](../evidence/README.md) — Recorded environments, manifests and limitations.
- [Automated verification results](../evidence/verification/README.md) — Specific software-only test runs.
- [Hardware arrival worksheet](13-hardware-arrival.md) — Open physical verification items.
