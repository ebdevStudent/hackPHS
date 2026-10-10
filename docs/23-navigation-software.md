# Navigation software and repeatable D435 corner mapping

Updated **2026-10-09**. This is a retained runbook for already implemented mapped-navigation and D435 software. **D435 room mapping will not be done for this project/demo; do not follow the capture/rebuild steps as current demo work. The code remains intact; the historical record is retained with this scope note.** The active software plan is [portable visual missions](27-portable-visual-missions-plan.md). The pre-camera navigation software and non-actuating backend mission/status contract have synthetic/offline checks; real calibration, Pi measurements and aircraft behavior remain unverified. [Implementation record](26-pre-camera-software.md) · [Earlier stage plan](20-semi-autonomous-navigation.md) · [Hardware worksheet](13-hardware-arrival.md) · [Verification](15-verification.md).

## Equipment and authority

The user identifies **Raspberry Pi 5, Intel RealSense D435, Arduino Mega 2560, Specter F411/ELRS AIO with onboard VTX, RadioMaster Pocket ELRS, the linked Caddx Ant camera and composite USB capture adapter**. Use the **RC832 receiver** from the TS832/RC832 pair; the Specter already provides the transmitter. Exact RAM/OS/Python, installed FC/EdgeTX/ELRS firmware, capture chipset/format/buffering and trainer interface remain pending. These are user-reported identities, not delivered-device or electrical checks.

Navigation supplies **advice**. Pilot retains roll, pitch, throttle, ARM/DISARM and independent takeover. Existing computer assistance remains yaw-only. No navigation module writes to the bridge; the mock follower has no serial/firmware interface. Internal ACKs are accepted software state, never evidence of aircraft output. Preserve fixed-cage-first, the ten-contact/three-minute/manual-recovery gimbal gate, $200 contingency/$30 reserve, 48-hour feature freeze and deferred Pico audio/toImplement.

## Launch and replay

Use this machine's active checkout. Its `software/` and `tools/` are maintained; do not edit `simulation/software/` or `simulation/docs/` duplicates. The independent Three.js application is locally under `simulation/`; upstream puts that game at repository root.

```sh
cd /Users/devk/Documents/HackPHS26/software
# Existing Python >=3.13 environment; source entry points load current edits.
.venv/bin/python -m ball_demo.cli serve
```

Open `http://127.0.0.1:8080/`. This preserves synthetic/mock, MANUAL, disabled startup and the existing loss/deadline behavior. Qt remains optional. Navigation is not imported when absent.

```sh
# Invented calibration, survey, map, observation session and JSON schemas:
.venv/bin/python -m ball_demo.cli nav-fixtures --output runs/navigation-fixtures
# Deterministic observation replay, without opening a bridge:
.venv/bin/python -m ball_demo.cli nav-replay runs/navigation-fixtures/synthetic-session.json --output runs/navigation-replay.json
# Estimated-vision mock waypoint follower, with loss and deliberate restoration:
.venv/bin/python -m ball_demo.cli nav-demo runs/navigation-fixtures/synthetic-session.json --output runs/navigation-demo.json
# Paced replay alongside the unchanged tracking application:
.venv/bin/python -m ball_demo.cli serve --nav-replay runs/navigation-fixtures/synthetic-session.json
```

In **Mapped guidance → Inspect navigation replay**, load either export. Playback stays in the browser and never posts a command. The XY chart distinguishes observed free, occupied and unknown space; collision checking uses full 3D geometry. Simulation truth and mock velocity are distinct export fields, not physical telemetry. The native workstation can inspect a configured server using File → Connect to Pi / server; its mapped-guidance dock shows pose and route. Tools → Import navigation bundle is operator-only.

For a real camera, use a measured bundle and an independently measured **worst-case acquisition-delay bound**, not the example:

```sh
.venv/bin/python -m ball_demo.cli serve --camera /dev/video0 --camera-backend v4l2 --nav-bundle runs/corner/bundle.json
```

Set a metric XYZ goal and **Restore guidance** after valid pose acquisition. Changing source/map/goal, loss, stale data or planner failure suppresses guidance. Recovery does not automatically restore it. Navigation never enables yaw assistance.

## Repeatable capture and map reconstruction

The D435 is used **before the demo** to scan and register the room. Save the map and disconnect the scanner; during mapped guidance, the Pi localizes from the aircraft FPV feed and surveyed AprilTags. Recheck/resurvey changed layouts; the stored map supplies no live obstacle sensing.

Start with a small **suggested 2 × 2 m corner**, scaled to the actual permitted area; this is an experiment size, not a measured map. Secure the D435 at fixed, surveyed stations. Do not walk it around and assign every frame the same transform. The mapper does not estimate a handheld trajectory or implement SLAM.

1. Mark the origin, three right-handed axes and permitted volume in metres. Include floor, ceiling/overhangs, people exclusion, obstacles and pilot access. Pick and measure tag IDs and the black detection-square side length; retain tag orientation as well as its centre. Place at least two tags with broad coverage of the room and visibility from the camera positions.
2. Survey each tag's center and face direction in the room frame. The standalone guided mapper estimates the stationary depth-camera pose from those RGB observations and the D435 factory depth-to-color extrinsic. For CLI capture without a tag survey, measure the full `map_from_depth` transform yourself. A repeatable tripod mark alone does not establish 6-DoF registration. Record the measurement method and uncertainty; never guess a transform.
3. Launch the **separate D435 Room Mapper** with `.venv/bin/python room_mapper.py` from `software/` (install `requirements-desktop.lock` first if needed). Enter the room extent, voxel size and measured tags, then use the live preview to check for at least two visible surveyed tags. Click **Capture this view** while the camera is still; repeat from positions that see areas hidden from earlier views. **Build map from captured views** combines them. The app saves the survey, raw BAG, RGB/depth frames, scan manifests, map and report to a new folder. It does not launch or change the operator workstation or demo server. The equivalent CLI workflow below remains available for repeatable automation.
4. Keep the zone unchanged during the scan. Native rectified depth is used, with no hole filling; preserve raw BAG, RGB, z16 depth, metric depth, intrinsics, device/firmware/SDK metadata and timestamps. Zero/missing returns remain unknown. Mask or physically exclude reflective/glass/poorly sensed objects; background returns through glass do not prove free space.
5. Capture multiple registered stationary views if one cannot see the entire route. All combined scans must share frame, map/version, extent, voxel resolution and uncertainty settings. Moving a station requires a new measured transform. Moving tags/obstacles requires a new map/survey version.

The standalone app records 30 frames for each stationary view and reports tag visibility/registration quality. You still need multiple still viewpoints to cover areas hidden from earlier views; it does not infer a handheld trajectory, so do not walk while capturing. The app, D435, and supported RealSense SDK must run on the same computer. For an unsupported or headless capture host, the CLI workflow remains available on a supported SDK host:

```sh
# Optional SDK only; this does not install/enable aircraft control.
.venv/bin/python -m pip install 'pyrealsense2==2.58.4.10922'
.venv/bin/python -m ball_demo.cli nav-capture-d435 --station runs/corner/station-a.json --frames 30 --output runs/corner/capture-a
.venv/bin/python -m ball_demo.cli nav-capture-d435 --station runs/corner/station-b.json --frames 30 --output runs/corner/capture-b
.venv/bin/python -m ball_demo.cli nav-map runs/corner/capture-a/scan.json runs/corner/capture-b/scan.json --output runs/corner/rebuild-1
.venv/bin/python -m ball_demo.cli nav-map runs/corner/capture-a/scan.json runs/corner/capture-b/scan.json --output runs/corner/rebuild-2
```

The new output directory prevents overwriting capture/reconstruction history. Identical saved inputs/settings produce identical map content and map hash. Reports retain source manifests/hashes and free/occupied/unknown voxel counts. Registration and uncertainty settings are inputs, not quantities the mapper invents. For repeat capture, retain station marks/photos, full measured transforms, device/stream settings and uncertainty records; resurvey moved stations. A new capture is a new artifact/version and may differ due to sensor noise or changed geometry. Compare coverage/occupied boundaries against independent checks within your measured error budget; byte-identical reconstruction applies to the same saved data, not two physical scans.

The conservative mapper marks a voxel free only when **all pixels covering the projected 3D cell have valid farther depth**, beyond the cell and uncertainty bound. It marks observed surface-return cells occupied; occupied wins across views. Off-screen, occluded, missing-return and behind-surface cells stay unknown. Exact adjacent free cells merge into boxes without filling gaps. Clearance may reject safe but poorly observed corridors; add verified coverage rather than lowering margins to force a path. Bounds: 100,000 voxels, 1,000 frames and 1,000 free/occupied boxes; shrink the zone or inspect fragmented data when a bound is exceeded.

## Pre-camera implementation — 2026-10-09

The authorized [pre-camera implementation](26-pre-camera-software.md) is complete
for work that can proceed from synthetic images, generated depth and offline
manifests. The shared camera solver, stationary tag-based D435 registration,
map reconstruction regressions, visibility-aware routes, estimated arrival,
inspection missions, private snapshot persistence, native/browser actions and
delayed/noisy mock follower are integrated through the CLI, engine, API and replay.
The [implementation record](26-pre-camera-software.md) lists the stages, commands,
test evidence and work reserved for camera availability.

The offline `nav-register-d435` command estimates a stationary scanner pose from
hash-checked RGB PNGs and surveyed AprilTags without importing the RealSense SDK.
`nav-capture-d435 --registration-survey survey.json` can also estimate and monitor
that pose during a live fixed-station capture, composing the RGB pose with the
factory color-from-depth transform. Both paths check tag visibility/quality and
scanner motion; they do not estimate a handheld trajectory. Tests use generated
images and an injected fake SDK. They do not verify a physical D435, RealSense
runtime, Raspberry Pi or room scan.

The current routes require at least two surveyed AprilTags to remain in the
calibrated raw sensor view and the rectified detector view through motion and yaw
changes. Planning blocks unknown space and stops on its time, node or cache budget.
Mission arrival, dwell and requested snapshots are software estimates. They do not
enable physical control or claim a completed aircraft inspection. The mock
simulation remains separate from live FPV and aircraft telemetry.

The core software profile passed on the Linux x86-64 container; the passing report
and the first preserved failed report are linked in the [implementation record](26-pre-camera-software.md).
The final core and Qt desktop profiles passed with native mission UI coverage; see the [implementation record](26-pre-camera-software.md) for exact reports and the retained nonreproducing sanitizer failure.
No hardware or physical flight acceptance is claimed.

## Backend mission commands and status

`GET /api/mission/status` reports video freshness, bridge trust, localization,
flight-controller telemetry and mission capabilities. `supported` means the
software path exists; `ready` means its present prerequisites are met. The
response starts in `MANUAL`, has advisory-only authority, reports no active
physical mission and keeps `physical_output:false`. Synthetic and recorded
video are labeled separately from live camera input. A firmware-reported
output mode is shown as `output_mode_reported`, but bridge state and physical
yaw-assistance readiness remain unverified until transmitter, pilot override
and failsafe behavior pass physical checks. Controller state stays `unknown`
until measured telemetry is connected. The Mega host accepts only the
internal-state `NO_OUTPUT` handshake.

The public status contains capability and subsystem state, not operator
command history. Operator command routes require the existing bearer token:

- `POST /api/operator/mission-commands` accepts strict `follow`,
  `land_current`, `land_site`, `stop` and `abort` requests with a unique
  `request_id`.
- `GET /api/operator/mission-commands/{request_id}` retrieves a recorded
  result. An exact retry returns its original result; reusing the ID for a
  different payload returns 409. The bounded ledger is process-local, so an
  evicted or post-restart request is unknown.

Every current command is reported as `state:"rejected"` with a reason and
`physical_output:false`. Follow/landing have no verified implementation or
actuator path. Stop/abort apply only to a future accepted physical mission;
they do not stop motors or disarm. This response means the backend understood
the request and refused it, not that a flight action succeeded. Existing
inspection missions are a separate advisory workflow. When their designated
survey tag disappears from accepted poses, arrival resets and status becomes
`waiting_for_target`; reacquisition returns through `reacquiring_target`
before fresh arrival observations count again. This marker visibility does
not implement person-follow.

## Dependency compatibility

The actual project requires **Python >=3.13**. Baseline OpenCV/NumPy/Pydantic suffice for localization and replay; AprilTags use OpenCV's optional `aruco` capability checked at use, without installing a conflicting OpenCV distribution. The checked lock uses OpenCV 5.0.0.93. Unsupported tag capability produces an explicit navigation error while HSV still runs.

The [RealSense wheel release](https://pypi.org/project/pyrealsense2/) inspected on 2026-10-08 includes CPython 3.13 Windows/Linux x86-64 wheels, but **no CPython 3.13 ARM64 or macOS wheel** in that release. Do not assume `pip install` works on this Mac or the Pi 5. Use a supported capture workstation, or build/verify librealsense bindings for the actual Pi Python/OS; bring the saved capture directory to the Python-3.13 navigation host. The optional SDK import never blocks map rebuilding/replay. No SDK/device test was performed on the D435 or Pi.

## FPV calibration, survey and bundle

Calibrate the **final aircraft-camera → Specter VTX → RC832 → USB capture → resized image** path. D435 factory intrinsics cannot replace FPV calibration. Save at least 10–20 varied checkerboard PNG views at the exact configured width/height, including corners, different ranges and tilts, with independently measured internal-corner spacing. Hold the aircraft camera rigid to the aircraft, not the rotating cage. Save raw video separately; image-only calibration does not establish exposure freshness.

```sh
.venv/bin/python -m ball_demo.cli nav-calibrate --bundle runs/corner/template-bundle.json --images runs/corner/checkerboard --columns 7 --rows 5 --square-m 0.025 --output runs/corner/calibration.json
.venv/bin/python -m ball_demo.cli nav-bundle --map runs/corner/rebuild-1/map.json --survey runs/corner/survey.json --calibration runs/corner/calibration.json --policy runs/corner/policy.json --id corner-v1 --output runs/corner/bundle.json
```

`7 × 5` internal corners and `0.025 m` are command examples; use your measured board. The template supplies separately measured `aircraft_from_camera`; calibration updates only intrinsics/distortion/RMS. Review its calibration ID, evidence and example flag. An output RMS is a fit residual, not independent aircraft-pose accuracy.

Contracts reject wrong units, frames, version/ID mismatches, duplicate tags, invalid/nonfinite numbers, boolean numeric coercion, nonrigid/reflected transforms, unknown fields and unsupported camera sizes/models. `T_A_from_B` converts coordinates in B to A. Map is right-handed Z up; aircraft FLU is forward/left/up; optical camera is right/down/forward; tag is right/up/out of printed face, with corners TL/TR/BR/BL. Aircraft pose is:

`T_map_from_tag × inverse(T_camera_from_tag) × inverse(T_aircraft_from_camera)`.

Tag solving uses Brown distortion, positive-depth checks, both planar alternatives and a global pose candidate. Reprojection error, ambiguity, metric bounds, position/angular jumps and consecutive reacquisition are checked separately. The reported uncertainty is a **provisional geometric bound**, not a calibrated covariance or confidence probability. Replace thresholds/bounds using independently measured holdout positions before claiming physical N3/N4 acceptance.

## From a rebuilt D435 map to the autonomous mock demo

After surveying tags and calibrating the aircraft video path, `nav-bundle` registers those artifacts with the reconstructed map and policy. Choose start/goal positions inside observed envelope clearance, with surveyed tags visible from the proposed initial heading. Run:

```sh
# Coordinates/heading below are examples; replace with your measured zone values.
.venv/bin/python -m ball_demo.cli nav-simulate --bundle runs/corner/bundle.json --start 1.7 0.8 1.2 --goal 2.2 1.5 1.3 --yaw-deg 90 --frames 600 --output runs/corner/autonomous-mock-demo.json
```

The follower synthesizes visible AprilTag observations using the registered geometry and camera model, estimates pose through the same solver/guard, plans through the same cleared volume and advances a bounded kinematic mock plant. It injects tag loss and explicitly restores guidance after reacquisition. Each plant step gets a swept-envelope clearance check. It stops when the goal is reached or the frame budget expires; failure/no visible tags/blocked space is reported, not hidden by moving through unknown volume. Its sensor observations and plant are synthetic even when the source map is measured. It is not a dynamics, braking, sensor-latency or physical flight validation.

The export carries the source bundle SHA256 and a labeled simulation copy, separate `simulation_truth_position_m` and `mock_velocity_m_s` fields, and `physical_output:false`. Load it through the browser's local replay picker. A real room map cannot supply missing aircraft velocity/height sensors or an unverified radio output path.

## Timing, planning and logs

Camera reads carry `host_read` provenance. They never become exposure timestamps. A known exposure must be in the same documented monotonic domain; a recorded timeline and synthetic timeline are explicitly separate. Without a measured acquisition-delay upper bound, camera guidance is rejected. Pose age includes that bound. Timestamps from D435 device and host clocks remain separate in capture files; capture does not infer a synchronized exposure timestamp.

Localization/planning run on an independent worker. The control worker reads a short cached snapshot and can invalidate it without waiting for detection, planning or recording. Epochs reject late results; skipped frames cause conservative reacquisition, and source faults publish persistent invalidation. A separate snapshot freshness check suppresses guidance when the worker stalls. Existing yaw control, frame/ACK/operator deadlines and neutral fallback remain intact.

The 3D planner checks the complete swept segment using an enclosing cage sphere conservatively bounded by a box. It expands occupied/unknown boundaries by:

`cage radius + flex margin + map uncertainty + pose uncertainty + speed × delay bound + speed²/(2 × deceleration)`.

Defaults are provisional example settings, including target 0.125 m cage radius; replace with the measured **entire** cage/hubs/deflection envelope. The planner checks the exact union of adjacent free boxes, so thin voxel slabs can jointly contain the entire cage without filling unknown gaps. Bounded box subtraction tests remaining unknown fragments against the continuous swept box; fragment and wall budgets stop excessive work. A* has node/time budgets and route TTL. A prior map supplies no dynamic obstacle detection; advisory use requires a controlled, rechecked zone. Neutral yaw is not braking, hovering or landing.

Each configured engine session records bundle metadata/hash in existing events and self-contained `navigation-*.jsonl` inputs on the navigation worker. Raw runtime files/tokens stay under ignored `runs/`. Complete imports validate before playback:

```sh
.venv/bin/python -m ball_demo.cli nav-replay runs/SESSION/navigation-RECORDING.jsonl --output runs/corner/session-replay.json
```

Replay uses logical event time and deterministic geometry/node limits. Live execution additionally enforces wall time. Intake and camera timing remain distinct even when a replay worker falls behind. This replay is software evidence; it contains neither physical telemetry nor serial activation.

## Smallest next real experiment and remaining gates

With props removed, record a **30–60 second FPV clip** in the small corner: two measured tags, three independently measured static aircraft poses, a short hand-carried path, several seconds of tag occlusion, then reacquisition. Capture 10–20 checkerboard views at the final resized size. Save camera mount measurements, tag full poses, tape-check dimensions, raw clip, timing flash test and capture configuration. Take 30 stationary D435 frames from one measured station; add a second only if the route volume is occluded. Rebuild twice and compare map hashes/unknown coverage.

Measure held-out position/orientation error and actual coverage/latency on the Pi 5, including camera disconnect/freeze, planner load and viewer load. Fill FC/radio firmware and trainer electrical/protocol rows. Physical yaw needs the complete output/override/failsafe tests; automatic translation/height needs a separately established authority change, verified velocity/height inputs, stopping controller/interface, bench/HIL and constrained physical tests. The accepted manual-contact/live-tracking demo remains available throughout.
