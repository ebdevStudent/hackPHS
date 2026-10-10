# Navigation — current implementation handoff

Updated **2026-10-09**. This is a historical handoff for the earlier mapped-navigation work. The current demo will not use D435 room mapping; keep the existing code and records, but follow the [portable visual missions plan](27-portable-visual-missions-plan.md) for active work. [Historical runbook](23-navigation-software.md) · [Verification](15-verification.md).

## Delivered software

Top-level `software/ball_demo/` contains camera calibration/distortion correction, OpenCV AprilTag detection and pose solving, strict versioned map/survey/calibration contracts, freshness/ambiguity/outlier/reacquisition checks, conservative 3D advisory planning, independent navigation worker, existing-engine/API/browser/native integration, session recording and deterministic replay. The optional waypoint follower uses inferred synthetic vision pose and mock velocity only. `nav-simulate` accepts a D435-map bundle through an explicitly labeled in-memory simulation copy; the source map/calibration/survey remain intact.

The repeatable D435 path records registered **stationary** views, raw BAG/RGB/z16/metric depth, factory camera metadata, distinct device/host clock provenance and content hashes. `nav-map` combines matching registered scans and reconstructs observed-free/occupied/unknown volume deterministically. It does not infer handheld camera motion, fill depth holes or declare unknown space free. Examples and schemas under `software/examples/navigation/` are invented software fixtures, not hardware measurements.

Physical channel authority remains **yaw-only**. Pilot retains roll, pitch, throttle, ARM/DISARM and independent takeover. No navigation code writes the bridge; no trainer output or firmware flash was enabled. ACKs prove internal accepted state only. Full autonomous movement is demonstrated in simulation; physical translation/height require a separately established authority change and verified sensing, stopping/output and takeover gates.

## Equipment and unresolved measurements

User reports Pi **5**, Raspberry Pi OS (exact release/RAM/Python pending), RealSense **D435**, Mega 2560, Specter F411/ELRS AIO with integrated VTX, RadioMaster Pocket ELRS, linked FPV camera/antenna/composite capture adapter. Video uses Specter VTX → **RC832 receiver** → USB composite capture → Pi; the TS832 transmitter is redundant here. A small corner of the hacking area is the proposed test zone, with no measured dimensions yet.

Still needed: actual OS/Python/SDK installation, camera/USB format/buffering/latency, measured final-path FPV calibration and camera mount, full tag poses/sizes/IDs, D435 station registration, permitted-zone survey and uncertainty bounds, FC/EdgeTX/ELRS firmware and trainer interface. Current pyrealsense2 release lacks a CPython-3.13 ARM64/macOS wheel; use a supported capture host or verify a Pi SDK build. Do not lower the project's Python requirement to assume compatibility.

## Continue from evidence

[Navigation evidence](../evidence/navigation/README.md) and [verification index](../evidence/verification/README.md) distinguish Mac/offscreen/browser/synthetic/fake-SDK results from Pi and physical acceptance. Historical failed runs are preserved. Installed app/old wheel packaging may predate navigation; launch current source using the runbook.

The active software/docs/tools are at workspace root. The independent Three.js simulator is locally `simulation/`; upstream places it at its root. Avoid its older copied `software/` and `docs/` directories. Preserve existing yaw tracking, disabled/mock startup, deadlines and manual fallback.

## Copyable continuation prompt

```text
Continue HackPHS26 navigation from its implemented software, not the old planning-only handoff.
Read AGENTS.md, docs/README.md, docs/20-semi-autonomous-navigation.md,
docs/23-navigation-software.md, docs/13-hardware-arrival.md and docs/15-verification.md.
Inspect current top-level software/ball_demo/ and recorded verification source hashes.

First run the smallest props-off real capture/survey experiment in doc 23:
measured tags/aircraft holdout poses, final FPV checkerboard/clip/timing and one
surveyed stationary D435 scan. Rebuild saved scans twice, compare hashes and
unknown coverage, then replay and evaluate measured pose error/latency on Pi 5.
Do not invent a room map/calibration/registration or substitute device timestamps
for synchronized camera exposure. Keep estimated vision, simulation truth and
physical telemetry distinct. Do not treat internal serial ACKs as aircraft output.

Physical authority remains yaw-only; pilot owns roll, pitch, throttle, ARM/DISARM
and independent takeover. No trainer enabling, firmware flashing or automatic
translation/height without separately established physical prerequisites and an
explicit authority change. Use nav-simulate for automatic movement demonstration.
Keep the P1B flight gate (no fixed cage is built), budget/reserve/freeze rules and deferred Pico
audio/toImplement. Preserve manual-contact/live-tracking as the accepted fallback.

Implement measured-input fixes as needed, add meaningful regressions and run
fresh traceable verification. Report software/replay, Pi and physical results
separately, update maintained docs and append decisions.md.
```
