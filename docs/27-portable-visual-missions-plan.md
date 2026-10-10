# Portable visual missions — software plan

Updated **2026-10-10** from the user's portable-missions handoff and follow-up decision. This plan covers software work that can be advanced before the aircraft camera and flight-control path are usable. It does not authorize physical control changes or claim hardware validation.

## Current decision and boundary

The demo is intended to work in a **controlled, previously unmapped space**, using the aircraft's FPV camera and visible AprilTags. **RealSense D435 room mapping will not be done for this project/demo.** Keep the existing D435 capture, registration and mapping code intact, and retain its historical implementation record with this scope note; do not build further work on that path or make it a demo prerequisite. This plan does not require a map, room survey, SLAM, or obstacle map.

The physical environment must be kept clear and controlled. A forward-facing analog FPV camera cannot establish dependable obstacle distance or coverage, so there is no obstacle-avoidance capability or UI toggle in this plan. The pilot keeps the transmitter and immediate manual takeover. No joystick/axis controls are added to the app. The existing physical authority remains MANUAL, disabled at startup, yaw-only if separately verified, and no-follow/no-landing until the flight-control path and safety gates are verified.

**Exclude handoff item 5 (speaking and two-way audio) entirely for this plan.** No audio device, transport, TTS, microphone, or audio UI work is scheduled here. Existing Flutter visual designs are reused; this plan has no UI redesign task. Connecting the existing mission screens to a backend contract is included only after backend behavior is testable.

## What exists today

- `software/ball_demo/localization.py` detects `tag36h11` and estimates a camera/aircraft pose against a **fixed surveyed tag set and map bundle**. It is not a moving-person tracker and should not receive moving target observations.
- FPV/OpenCV sources, frame-health and fault handling, calibration contracts, target-color tracking, mission status, typed high-level command requests, operator authentication, bounded request reconciliation, and the existing browser/native client paths are present.
- `software/ball_demo/mission_control.py` rejects every physical follow/landing request. It has no accepted physical mission lifecycle or actuator implementation. Stop/abort are not motor-stop or disarm operations.
- `software/flutter_operator/` defines roster, follow, stop/abort, current-position landing, tag/point landing, and capability/state concepts. The Python service now implements the visual/mission portion of its `/api/ui/v1` contract; WebRTC/audio and physical aircraft behavior remain unavailable. UI fixtures and screenshots are not backend behavior.
- Existing inspection/navigation and D435 code are separate from the portable target-follow problem. The portable follow path must not require a loaded navigation bundle or D435-derived map.

## Implementation status — 2026-10-10

The pre-hardware software work is connected end to end in the active top-level `software/` tree. `--portable-demo` runs generated AprilTag pixels through an independent pose worker into the shared mock mission ledger and existing Flutter API. No control tick or source truth metadata supplies target visibility. Stale, missing, late and stalled observations neutralize simulated desired motion. See the [completion and evidence record](28-hardware-free-completion.md). This is software/generated-image evidence only.

| Plan item | Implemented | Remaining boundary |
| --- | --- | --- |
| Versioned contracts and roster | Strict person/pad assignments, `tag36h11` IDs and measured sizes, role separation, bounded private JSON loader, one shared mission ledger, authenticated mutations, idempotent request reconciliation and explicit supported/ready states. | The operator must prepare measured tag sizes and keep the roster file private. |
| Relative target tracking | Shared AprilTag detector; map-independent relative person/pad pose, capture/host-read timing provenance, quality checks and acquire/loss/reacquire trackers. Generated marker/projection regressions exercise it. | It requires a calibration for the final FPV capture dimensions and a measured camera-to-aircraft transform. It is not yet configured against the actual aircraft feed. |
| Mission lifecycle | Mock follow, stop, abort, current-position landing and tag-pad landing share one bounded ledger. Stop can cancel pending starts; landing reaches `landed` only after an explicit simulator touchdown event. Legacy/physical requests remain rejected. | Mock lifecycle is not aircraft control. The live camera path cannot start a follow or landing mission. |
| Follow/landing simulation | Deterministic bounded follower with noisy/delayed/lost observations, override latch, speed/acceleration/approach/area limits, plus synthetic descent/touchdown/impact behavior. | Simulated outputs are not flight telemetry and do not establish aircraft response. |
| Flutter API adapter | `/api/ui/v1` serves typed snapshots, read-only camera stills/JPEG frames, command submission and request lookup through the existing engine ledger. Anonymous reads report `operator_authorized: false`; commands require the bearer token. Audio is explicitly unavailable. | No WebRTC/media-offer endpoint or live flight-control authority is implemented. Actual Pi/browser/CORS performance still needs device verification. |
| Tests and evidence | Focused tests cover strict contracts, generated tags, pose/loss/reacquisition, mock mission races, bounds, API authentication/idempotency and physical-output isolation. Real Dart REST gateway and phone/desktop render tests exercise a separate Python HTTP backend, alongside the existing client suite. | Synthetic image tests do not validate the RC832/FPV camera path, recognition range or motion blur. |

No D435 mapping code was removed or extended by this work. The mapper remains outside this project's current demo workflow. Audio item #5, UI redesign, arbitrary image-point landing, obstacle avoidance, autonomous flight and every unverified physical output remain out of scope.

## Work that can be implemented before hardware is functional

### 1. Freeze the portable backend contract

Define and validate versioned server-side contracts before changing command behavior:

- Prepared roster entry: stable `person_id`, display name, AprilTag family/ID, measured printed black-square size, and whether the entry is enabled. Validate uniqueness, supported family/ID range, finite positive size, and edits while a mission is active.
- Tag roles: moving person tags, landing-pad tags, and fixed localization tags are distinct concepts. A moving target must never be inserted into the fixed surveyed-map localizer. A landing marker is not a person target.
- Target observation: tag identity, sequence, capture/receipt timing and provenance, corners, relative pose in camera coordinates and aircraft coordinates, range, bearing/lateral offset, quality/error, validity reason, and source label (`synthetic`, `recorded`, or `live`). Do not call a host-read timestamp an exposure timestamp.
- Mission command/result: strict payloads, request ID, stable mission ID, accepted/rejected/unknown disposition, current phase, reason, and capability/readiness. Repeated identical IDs return the original outcome; conflicting reuse is rejected. Keep operator-only mutations authenticated.
- Capability states distinguish implemented (`supported`) from currently usable (`ready`). `live` camera, `mock` simulation, stale/lost video, unknown flight-controller state, and unverified output must remain explicit.

Choose one adapter between the existing Python API and the Flutter contract. Do not implement two mission ledgers or two independent capability sources. Keep the ledger bounded and process-local unless persistence becomes a concrete requirement; after restart, an absent command result remains unknown.

**Checkpoint:** schema and route tests prove strict types, unknown-field rejection, roster/tag uniqueness, authentication, idempotency, conflicting request handling, and mock/live source labeling.

### 2. Add relative AprilTag target tracking

Create a target-tracking layer that shares the AprilTag detector where practical but returns relative tag pose rather than a map-frame pose. It uses the selected roster entry's tag ID and measured size plus a versioned calibration for the final FPV capture dimensions. It has no dependency on D435, map bundle, fixed-tag survey, or mission UI.

Use generated marker images and synthetic calibrated projections now. Add recorded-video replay when a representative clip exists. The tracker should:

- reject unassigned, wrong-family, wrong-ID, malformed, duplicate, stale, out-of-frame, low-quality, or geometrically implausible observations;
- report relative range/bearing and pose quality with clear timing provenance;
- model acquiring, tracking, temporarily lost, and reacquiring states with thresholds supplied as configuration rather than hidden constants;
- preserve target-loss as an event so a latest-frame mailbox cannot overwrite the loss/neutralization decision;
- distinguish target tracking from fixed-tag localization and from the existing HSV colored-target tracker.

Do not claim that generated bitmaps establish detection range or recognition through the actual camera, VTX, RC832 and USB capture path.

**Checkpoint:** known synthetic tag projections recover relative pose within test tolerances; wrong-ID and stale observations are rejected; occlusion/loss/reacquisition transitions are deterministic; no test invokes bridge or firmware output.

### 3. Build a non-actuating follow mission state machine

Implement lifecycle and cancellation semantics in a service that has no physical actuator path. At minimum, model `idle`, `accepted/acquiring`, `following`, `temporarily_lost`, `reacquiring`, `stopping`, `stopped`, `completed`, `aborting/aborted`, and `fault` with explicit legal transitions and reasons.

- A start request binds to a prepared roster identity, not a free-text name. Reject a person without an enabled, measured tag assignment.
- Follow only uses a fresh, valid relative target observation. Loss, stale video, invalid geometry, target identity changes, backend restart, or a simulated safety limit must stop simulated motion and enter the appropriate state. Reacquisition requires fresh consecutive observations and must not silently restore physical authority.
- Stop must cancel a pending start as well as an active simulated mission, so a delayed start cannot reactivate after Stop. Abort has documented mission semantics and is explicitly not an emergency motor stop or disarm.
- Keep one high-level mission active at a time. Preserve exact-request idempotency and make late, duplicate and reordered results harmless.
- Never report `following` from an accepted button request alone; the active snapshot must show the state transition. Never report `landed` from a landing request alone.

For now, “follow” means a testable simulated mission. The current backend must continue to reject physical follow until physical translation/height authority and pilot-takeover gates are satisfied and control authority is explicitly updated.

**Checkpoint:** transition-table tests cover every valid and invalid transition, loss/stop/abort races, duplicate/reordered requests, restart/unknown outcomes, and fault recovery. All physical-output fields remain false and the existing bridge is unreachable from the mission service.

### 4. Add a bounded follow-controller simulation

Use relative target pose to calculate a bounded *simulated desired motion* that tries to maintain a configured distance and bearing. This controller is for behavior exploration and tests only; it does not send commands to the Mega, transmitter, receiver, or flight controller. Keep its simulated aircraft/target truth separate from camera-derived estimates.

Build deterministic target trajectories covering walking pace, turns/target-facing-away, occlusion, partial tags, crossings with another tag, range changes, image noise, latency, dropped/frozen frames, reacquisition, pilot-override events, and mission stop/abort. Enforce configured speed, acceleration, approach-distance and operating-area limits in the simulated output. If estimates are stale or uncertain, simulated motion stops and status explains why.

**Checkpoint:** independent expected trajectories and invariants verify limits, stopping on loss, no unwanted restart after reacquisition, and deterministic replay. Mock results remain labeled `synthetic` and cannot be presented as aircraft telemetry.

### 5. Specify landing behavior without claiming physical landing

Implement pure contracts and a non-actuating simulator for the first two handoff modes; keep arbitrary-point landing unavailable:

1. **Current-position landing:** explicit request, readiness gates, simulated descent, simulated touchdown evidence, abort/fault behavior, and a terminal landed state that requires an explicit touchdown event. The physical capability remains unavailable until verified altitude/vertical-control/landing-mode feedback and failsafe behavior exist.
2. **AprilTag landing pad:** validated pad identity, measured tag size, configured pad footprint/orientation and acceptable approach geometry; use the same calibrated relative-pose pipeline but a landing-pad role. Require a fresh, stable, correctly identified observation throughout the simulated approach. The physical capability remains unavailable until the camera view, surface/clearance, descent control and loss response are established.
3. **Arbitrary point selected in an image:** do not convert pixels into a physical landing command. Keep this capability explicitly unavailable. A future implementation would need calibrated image-to-ground geometry, aircraft attitude/height or depth, target-surface validation, target persistence through descent, and physical acceptance.

**Checkpoint:** request alone never advances a landing to `landed`; unsupported/unready paths return a reason; all simulated landing traces are visibly synthetic and isolated from physical output.

### 6. Connect the existing Flutter mission client after contracts stabilize

Do not redesign screens. Adapt its existing `OperatorGateway` contract to the Python backend (or add a thin, versioned adapter) for prepared roster, capability/status snapshot, follow, stop/abort and landing requests/results. Keep unavailable actions disabled with backend reasons; show mock data as mock. Audio is outside this work and must not become a prerequisite or silently appear operational. Preserve authenticated access, one mission at a time, explicit unknown outcomes, and stop availability while a follow request is pending.

**Checkpoint:** contract tests use a local mock backend and the real Python API; phone/desktop layouts parse the same typed mission lifecycle; timeouts reconcile the same request ID rather than resend a new mission. No real camera or flight-control action is required for this integration check.

### 7. Maintain verification and documentation

Add focused software tests for generated tag detection/relative pose, target-loss events, mission lifecycle and cancellation, follower/landing simulation bounds, command auth/idempotency, API/client schema agreement, and source separation. Use `tools/verify.py` as required by the repository instructions when implementation begins; keep failed reports, source hashes, seeds and environment labels. Keep synthetic/recorded/physical evidence separate.

Keep MANUAL, disabled startup, pilot transmitter control and no verified physical output as invariants. Before any later physical follow/landing work, revise the control-authority documentation first and pass appropriate hardware-specific gates; a passing software suite does not satisfy them.

## Explicitly outside this pre-hardware plan

Record these as later external validation gates; do not simulate them as completed:

- Final FPV calibration and live-feed format, latency, dropped-frame, disconnect/recovery and detection-range measurements on the Pi through the aircraft camera → VTX → RC832 → capture path.
- Actual moving-target detection reliability under judging-room lighting, blur, angle and motion.
- A verified flight-control/telemetry path for translation and height, pilot takeover, command timeout, stopping behavior and camera/tag/link-loss response. Current yaw-only authority does not enable autonomous following or landing.
- Props-off, bench, restrained and controlled flight validation of follow; current-position landing; AprilTag-pad visibility and landing; confirmed-touchdown sensing; and full rehearsal evidence.
- Arbitrary-point landing, obstacle avoidance, D435 room mapping, all audio/TTS/audio UI/backend work, and any new physical authority or hardware feature not explicitly authorized.

The active demo target is **portable visual interaction in a controlled, unmapped space**. Until the physical gates pass, the honest demonstration is manual piloting with live target observation/status, plus clearly labeled synthetic mission simulation—not autonomous flight.
