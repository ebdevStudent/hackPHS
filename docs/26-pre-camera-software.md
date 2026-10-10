# Pre-camera navigation software implementation

Historical implementation record for work authorized 2026-10-09, including automatic D435 station registration from surveyed AprilTags. **Current decision (2026-10-09): D435 room mapping will not be done for this project/demo. Preserve this existing implementation and evidence, but do not continue or depend on that workflow.** The active pre-hardware work is described in [portable visual missions](27-portable-visual-missions-plan.md). Passing software checks do not establish physical operation.

## Delivery checklist

| Stage | Deliverable | Status and evidence |
| --- | --- | --- |
| 1 | Independent synthetic depth/RGB/checkerboard scenes; versioned registration, calibration-quality, heading, arrival and mission contracts | Implemented. Generated schemas and an example mission are checked in under `software/examples/navigation/`. |
| 2 | Real image calibration/detection tests, quality diagnostics, shared camera-pose geometry, independent accuracy/uncertainty checks | Implemented with synthetic raster images and held-out geometry checks. No physical calibration claim. |
| 3 | Automatic RGB-tag D435 registration with depth/color extrinsics, stable acquisition, movement/loss rejection, offline and fake-SDK adapters | Implemented in `software/ball_demo/registration.py` and `mapping.py`; `nav-register-d435` and surveyed-tag capture option are wired into the CLI. |
| 4 | Distinct-station mapper regressions, independent geometry oracle, partial-capture failures, bounded resource reports | Implemented and regression-tested. Unknown, missing, occluded and out-of-range depth stays unknown. |
| 5 | Heading/visibility/occlusion-aware routes with continuous segment and turn checks, conservative clearance and work budgets | Implemented. The route keeps at least two surveyed tags in both raw sensor and rectified detector views; occupied/unknown space and resource limits reject the route. |
| 6 | Uncertainty-aware arrival, configurable heading/dwell, fresh-observation-only progression, loss/goal/bundle reset | Implemented in `arrival.py` and `mission.py`; progression uses distinct accepted estimates and cancels pending evidence on loss. |
| 7 | Strict inspection missions, operator-only dry run/synthetic snapshots, native/browser state and record/replay | Implemented. Requested frames are saved to private session storage. Mission actions remain advisory and cannot command aircraft output. |
| 8 | Bounded mock turning/acceleration/braking, delayed/noisy image feedback and loss, separate truth and estimated state | Implemented. The synthetic follower checks every swept envelope and stops at a final target awaiting operator confirmation. |
| 9 | Complete CLI-to-engine/API/native/browser synthetic capture→registration→map→bundle→localization→mission→replay checks | Implemented with generated RGB images and an injected fake D435 SDK; Node validates the browser payload. This is not a real camera workflow test. |
| 10 | Current-source verification/coverage, preserved failures, manifests/seeds/environment, maintained documentation | Core and Qt desktop profiles passed against the current source. Earlier failed attempts remain preserved. Verification outputs are under `evidence/verification/`. |
| 11 | Backend high-level mission commands/status, auth, idempotent reconciliation and explicit capability gates | Implemented as a non-actuating API contract. Physical follow, landing, stop and abort remain unavailable. Core/desktop regressions and module coverage pass; see the current verification record below. |

## Implemented boundaries

- Startup and restart remain MANUAL, assistance-disabled and mock by default. The Mega sketch is internal-state-only; its host rejects a firmware-reported `PPM_YAW` handshake. No trainer/GPIO output is enabled until the protocol and electrical path are verified.
- Navigation advice requires a validated map, camera calibration, tag survey and pose. Recovery after loss requires deliberate operator restoration.
- The mapper combines stationary registered D435 captures. Tag-based station registration estimates the RGB camera pose in the surveyed map, composes the factory color-from-depth transform, and checks that the scanner remains still. It does not implement handheld SLAM.
- Route visibility uses the calibrated lens model, requires two surveyed tags at every sampled position and yaw, and rejects unknown space. A planned route remains geometric advice, not proof that the video feed will detect those tags.
- Arrival and mission completion are estimated from fresh vision poses. Snapshots document the selected frame; they do not prove a physical inspection or aircraft location.
- The high-level command ledger is bounded and process-local. Exact retries return their recorded rejection, conflicting reuse of a request ID returns 409, and an evicted/post-restart result is unknown. Current mission commands cannot actuate hardware.
- Losing the inspection target's surveyed tag resets arrival. Status reports target wait and reacquisition before new arrival samples count; this is not moving-person tracking.
- Synthetic truth, estimates, clocks and physical acceptance are separately labeled. The mock plant does not share control with the aircraft.
- Existing control/ACK freshness limits and coverage gates remain unchanged.

## Offline registration and capture commands

Offline image registration does not need the RealSense SDK. The input manifest supplies a versioned RGB camera model, surveyed tag poses, factory `color_from_depth` geometry, a station template, hashes and timestamps for stationary RGB PNGs:

```sh
.venv/bin/python -m ball_demo.cli nav-register-d435 \
  --input runs/corner/registration/input.json \
  --output runs/corner/registered-station
```

The output includes `registration.json`, a station file with the estimated depth-camera transform, and a completion/hash report. The capture command can independently register and monitor a fixed station while it records depth:

```sh
.venv/bin/python -m ball_demo.cli nav-capture-d435 \
  --station runs/corner/registered-station/station.json \
  --registration-survey runs/corner/survey.json \
  --frames 30 --output runs/corner/capture-a
```

This command requires a supported RealSense SDK/device and measured RGB/depth calibration. The injected SDK used by tests does not establish that the actual D435 or Pi can run this path. Preserve the station still during capture; movement, tag loss, calibration change or nonadvancing sensor timestamps aborts the capture and leaves an incomplete marker.

## After camera availability — recorded only

Real D435 SDK/device and BAG compatibility; physical station registration and room coverage; final FPV path and aircraft-mount calibration; tag detection range and angle; measured uncertainty, visibility, arrival and latency settings; regressions from real recorded data; Pi load, timing and thermal behavior; live snapshot validation. Aircraft state estimation or flight-assistance work remains gated on verified sensors/interfaces and an explicit control-authority decision.

## Verification record

- **Final core run:** [`20261009-pre-camera-core-04/report.json`](../evidence/verification/20261009-pre-camera-core-04/report.json). Linux x86-64 container, Python 3.13.14; 4,162 tests, zero failures/errors/skips; 98.50% overall coverage; all configured module floors; both portable firmware and line-reader address/undefined-behavior sanitizer checks passed. The verification runner reported the source fingerprint unchanged. The suite emitted one Starlette deprecation warning from `fastapi.testclient`. Arduino Mega compilation was not run because `arduino-cli` was unavailable.
- **Earlier passing core run:** [`20261009-pre-camera-core-02/report.json`](../evidence/verification/20261009-pre-camera-core-02/report.json) predates the final lens-distortion visibility refinement; 4,160 tests and all gates passed.
- **Nonreproducing sanitizer failure retained:** [`20261009-pre-camera-core-03/report.json`](../evidence/verification/20261009-pre-camera-core-03/report.json) recorded 4,162 passing tests and all coverage floors, but its portable firmware sanitizer process exited `-11` with an empty log. Rebuilding and running that exact check directly passed, and the subsequent full core-04 run passed both sanitizer checks. The core-03 report remains preserved for audit.
- **Earlier failed attempt retained:** [`20261009-pre-camera-core-01/report.json`](../evidence/verification/20261009-pre-camera-core-01/report.json). It exposed missing navigation coverage and an absent optional Qt dependency; it is retained as development history, not a passing result.
- **Qt desktop first attempt retained:** [`20261009-pre-camera-desktop-01/report.json`](../evidence/verification/20261009-pre-camera-desktop-01/report.json) recorded a brittle pixel assertion and an unmet `desktop.py` coverage floor; it is retained as development history.
- **Passed Qt desktop run:** [`20261009-pre-camera-desktop-02/report.json`](../evidence/verification/20261009-pre-camera-desktop-02/report.json). Linux x86-64 container, Python 3.13.14, Qt 6.9.3; 4,547 tests, zero failures/errors/skips; 97.95% overall coverage and all configured module floors. Both portable firmware sanitizer checks passed, and the verification runner reported the source fingerprint unchanged. Arduino Mega compilation was not run because `arduino-cli` was unavailable.

No real D435, Raspberry Pi, transmitter, aircraft or flight was used. These checks establish software behavior only.

## Backend mission/status extension — 2026-10-09

- **Core:** 4,175 tests passed, zero failures/errors/skips, 98.51% combined coverage; all module floors passed, including `engine.py` 99.40% and `mission_control.py` 100%. Portable C and Mega line-framing UBSan checks passed. [Report](../evidence/verification/20261009-mission-status-core-05/report.json).
- **Qt desktop:** 4,560 tests passed, zero failures/errors/skips, 97.98% combined coverage; the same module floors and UBSan checks passed. [Report](../evidence/verification/20261009-mission-status-desktop-01/report.json).
- **Sanitizer anomaly:** a default full-profile portable C ASan/UBSan run exited `-11` with no diagnostic. Rebuilding and running that exact core check directly passed; line-reader ASan/UBSan passed with verbose runtime initialization, while two silent direct invocations also exited `139`. Preserve these as sanitizer-runtime instability, not as passing full-profile evidence: [report](../evidence/verification/20261009-mission-status-core-04/report.json) · [direct runs](../evidence/verification/20261009-mission-status-direct-sanitizers/README.md). The final full profiles used UBSan.
- **Firmware boundary:** the Mega sketch was restored to internal-state-only protocol handling, its PPM generator was removed, and the host rejects `PPM_YAW`. Arduino compilation was not run because `arduino-cli` is unavailable. No physical output, Pi or aircraft acceptance is claimed.

## Standalone D435 room mapper — 2026-10-09

The separate, me-facing Qt utility is launched with `python room_mapper.py` from `software/`; it does not open or control the operator workstation or demo server. It guides tag survey, still-view capture and map reconstruction. Multiple stationary views are still required; no handheld SLAM is implemented. The window and mocked capture path passed the focused room-mapper, D435 mapping and desktop-navigation suites (62 tests).

The full desktop profile ran 4,581 tests with no failures, errors or skips and 96.26% total coverage; all configured module floors passed. Its report is [`20261009-room-mapper-standalone/report.json`](../evidence/verification/20261009-room-mapper-standalone/report.json). The profile is recorded as failed because the Mega line-reader ASan/UBSan process exited `-11` with an empty log. This matches the already documented intermittent sanitizer-runtime failure; the failed report is preserved. The profile's portable firmware sanitizer passed. The run did not use a physical D435 or Pi, and Arduino Mega compilation was unavailable because `arduino-cli` was not installed.
