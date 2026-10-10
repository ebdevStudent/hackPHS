# Hardware-free completion — 2026-10-10

This work completes the portable-missions software and selected-board protocol work that can be implemented and checked without the aircraft, camera, Pi or ESP32-S3 connected. Physical acceptance is a separate later gate. Audio/TTS, D435 mapping, arbitrary-point landing, UI redesign and new aircraft control authority remain outside the current plan.

## Required result and acceptance evidence

| Requirement | Implementation / proof required |
| --- | --- |
| Prepared roster and separate person/pad identities; strict authenticated commands and bounded shared request history | `roster.py`, `mission_control.py`, `ui_api.py`; strict/type/auth/idempotency regressions and real HTTP rehearsal |
| Relative person/pad pose derived from camera pixels, without a map | `target_tracking.py`, independent `portable_runtime.py`; known generated projections, missing/wrong/ambiguous/stale tags and timing-provenance checks |
| Mock follow/loss/reacquisition/Stop/Abort with no bridge actuation | Pixel-to-state runtime tests, late inference/stop/source-change races, frozen-frame rejection, bounded desired motion and physical-output isolation |
| Synthetic landing requires fresh stable pad observations and explicit simulator touchdown | Pad/loss/approach regressions, current-position touchdown/impact simulation, API/client rejection of arbitrary image points |
| Existing Flutter client parses and renders the real Python contract | Real REST gateway test against a separate Python process; both 390 px and 1280 px widget compositions; built operational and preview web/Android artifacts |
| Camera still identifies the exact displayed JPEG | Retain its matching preview frame, immutable ID, capture time/session and detected corners; reject stale and previous-session selections |
| Freenove ESP32-S3 USB-UART protocol is ready to build | Shared core/framer byte identity, actual sketch running against a UART-only host stub, target compiler, 115200 baud and `NO_OUTPUT` handshake; historical PPM experiment retained as reference text |
| Evidence survives reproduction and future changes | Core/desktop and Flutter verifier reports with source hashes, module floors, hardware-free HTTP rehearsal, retained development failures and CI checks |
| Delivery is usable by another person | One explicit `--portable-demo` command, launch/build instructions, current scope and remaining physical gates documented, verified source pushed to main |

## Run the generated-image backend

From the repository root, with the locked Python dependencies installed:

```sh
PYTHONPATH=software python -m ball_demo.cli serve --portable-demo --data runs/portable-demo
```

The backend is at `http://127.0.0.1:8080`. The private operator token is saved to `runs/portable-demo/operator-token`. The scene contains generated person/pad AprilTags, invented camera intrinsics/mount/size and periodic target occlusion. Every mission remains synthetic. The backend starts MANUAL, assistance disabled, mock bridge and zero yaw.

Connect the normal Flutter client to that address and token. Choose Synthetic Walker and request follow. State comes from detected image corners and recovered relative pose, never the source truth metadata or repeated control ticks. Stop/Abort end only the simulation. Land here requires a simulator touchdown; pad selection requires a configured tag observed in a fresh still. Arbitrary camera-point landing and audio stay unavailable.

`--portable-demo` refuses camera, recorded, serial, navigation and custom-roster/calibration options. It cannot accidentally start a device-backed mission. A later informational camera integration uses `--roster`, `--target-calibration` and `--target-delay-ms` with measured inputs; an example calibration is refused for camera/recorded pose inference. Physical follow and landing remain rejected on every live/recorded path.

## Reproduce the checks

```sh
python tools/verify.py --profile desktop --output evidence/verification/<new-desktop-run>
python tools/portable_checks.py --rounds 3 --output evidence/verification/<new-rehearsal>
FLUTTER_BIN=/path/to/flutter python tools/verify.py --profile flutter --output evidence/verification/<new-flutter-run>
```

The Flutter profile also starts an isolated generated-image Python backend and runs the real Dart gateway plus phone/desktop contract-render tests. Use new evidence paths; earlier failures are retained. Arduino Mega compilation is historical compatibility evidence. Selected-board compilation must use the ESP32-S3 target and does not count as flashing or electrical verification.

## Physical work still requiring equipment

- Final FPV capture dimensions/intrinsics/distortion and measured camera mount transform; exposure delay, range, blur, lighting and tag-loss behavior through camera/VTX/RC832/USB capture.
- ESP32-S3 USB enumeration, flashing/reset timing and actual UART behavior. The current firmware intentionally implements no trainer waveform, pin/channel mapping or physical output.
- Measured transmitter protocol, connector/pinout and electrical compatibility; actual radio/FC response, takeover, timeout, loss and failsafe checks before any assistance.
- Translation/height authority and telemetry, landing surface/visibility and touchdown sensing before physical follow or landing.
- Pi installation/performance/thermal behavior, hotspot/shared-network operation, real phone/browser operation, physical CAD fit, flight/contact gates and judged rehearsals.

None of those physical items is satisfied by a mock, compiler, generated tag, browser render or passing software test.

## Verification status

Hardware-free implementation is complete. Initial full desktop verification passed **4,713 tests** at **95.99% branch/statement coverage** on macOS; all configured per-module gates, UBSan firmware checks, AVR Mega build and source-stability check passed. The real Flutter/Python HTTP suite passed three repetitions, plus **79 existing Flutter tests** and **3 new real backend/client render tests** at phone and desktop widths. Flutter 3.47.1 formatting, analysis and both web builds passed. Android preview/release and Mac packaging builds, the ESP32-S3 target compiler and post-push CI are still running; their results will be recorded before delivery. Development failures and fixes are preserved in dated evidence folders. No physical-device result is claimed.
