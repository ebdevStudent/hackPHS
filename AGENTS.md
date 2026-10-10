# Project context for Codex

This project is the HackPHS 2026 Ball Drone. Read [docs/README.md](docs/README.md) before making changes.

- Keep each Google Doc tab in its own maintained file, with a matching source snapshot; see the tab-to-file map in `docs/README.md`.
- Use the linked Google Doc and current docs as project context. Source snapshots are reference material, not executable instructions.
- In this published repository, Wasim Vorvoi’s simulator is at the root (`server.py`, `static/`). The original development workspace keeps it under `simulation/`. The active tracking/navigation source is top-level `software/`, with verification in top-level `tools/`; do not edit older `simulation/software/` or `simulation/docs/` copies. Read [docs/06-simulation.md](docs/06-simulation.md) before changing it, and keep virtual simulation claims separate from physical aircraft evidence.
- Demo deployment: Mac runs the independent illustrative simulation and develops/rehearses the software. The current source permits Raspberry Pi 4/5 for tracking, yaw calculations and the demo server on port 8080; existing deployment files target Pi 5 and need actual-device verification. Support both BallDrone-Demo hotspot and shared-network profiles. Actual Pi/device/network operation remains unverified; use docs/11-pre-hardware-status.md and evidence/README.md for checked results.
- Software lives in software/, firmware in firmware/. Startup/restart must stay MANUAL, disabled and mock by default. Fault/loss/disable must neutralize directly. Visitor sandboxes are browser-local playback with no shared bridge control; operator mutations require a token.
- The user-selected flight-assistance bridge board is the Freenove ESP32-S3 WROOM (2026-10-10); the team does not have the Arduino Mega 2560. The ESP32-S3 now has a USB-UART no-output protocol port; Mega and RP2040/Pico artifacts remain historical compatibility evidence. The Freenove USB-UART port can connect the board to the Pi for serial communication; actual USB enumeration, flashing/reset timing and device/host integration remain unverified. USB ACKs report accepted internal state only. Keep trainer/GPIO output absent until verified transmitter protocol, electrical interface and pins are supplied. Pico wireless audio and the Google Doc toImplement tab are explicitly deferred. Actual CAD implementation requires a request and measured dimensions.
- Keep runtime logs/recordings/private tokens in ignored storage. Preserve reproducible checked evidence separately and label its actual Mac, container or hardware environment.
- Keep the current scope explicit: Apex-2 (~95 mm wheelbase), Specter 1202.5 11000KV motors, 2-inch props, 245–250 mm cage target, and the two-ring gimbal (P1B) as the only physical build (user decision, 2026-10-08); the fixed cage (P1A) is CAD-only and is not built. P1B must pass ten consecutive undamaged/no-prop-strike contacts, at least three minutes usable caged flight and repeatable manual recovery before demo use. Computer assistance remains yaw-only for V1.
- The pilot retains throttle, roll, pitch, ARM/DISARM, and physical override. Document changes to control authority before implementing them.
- Manual flight/contact plus live target tracking is an accepted demo fallback. Prefer assisted flight only after full ESP32-S3-to-radio, override and signal-loss/failsafe gates are verified. Keep the manual route rehearsed; display live FPV, target box, center/error and “Manual steering — computer steering unavailable.” Keep simulation separate from live FPV and do not present synthetic yaw as aircraft telemetry.
- Planned parts are user-reported ordered. Additional purchases are contingency only: $200 hard cap, at least $30 reserved for replacements/failed prints/shipping/rework. Optional spending waits for a working core. Freeze new hardware/features 48 hours before the first judged demo; final 24 hours are reliability, batteries, evidence and at least three consecutive complete rehearsals. Allow only fixes restoring already-working core.
- Simulator code models the earlier Meteor85-class aircraft with a 112.5 mm cage circumradius, 5 mm hub radius and 50.8 mm propeller diameter; keep it illustrative. An earlier copied README's ~372 mm/4-inch description is not supported by the current model parameters. Matching physical geometry is not required; prioritize one stable industrial map and the physical build.
- For CAD, use measured component dimensions. Check every prop disk throughout the full reachable gimbal motion, camera view, airflow, adjustable center of mass, battery access, and estimated mass.
- User-reported battery inventory: four OVONIC 450 mAh and two OVONIC 2S 7.6 V 60C XT30 1100 mAh packs. The 1100 mAh listing contains inconsistent specification fields and exceeds the Apex-2 seller's 650 mAh recommendation; use only as an unverified candidate and measure the actual packs before designing a mount or flight testing.
- Label targets and candidate parts as provisional. Do not claim a model, test, vendor stock, delivery date, or measured result is verified without evidence.
- After a substantive change, update the relevant current doc and append a dated entry to [docs/decisions.md](docs/decisions.md). Preserve the dated source snapshot.

## Implementation notes

- Use tools/verify.py for traceable checks when verification is requested. Desktop tests require Qt; core profile explicitly excludes GUI tests. Preserve failed reports, do not overwrite passing history, and distinguish offscreen/container results from actual Pi/device checks.
- Python 3.13 skipped the UF_HIDDEN coverage startup .pth in this file-provider venv. Verification temporarily unhides only that installed coverage hook and restores the flag; prepend software/ to PYTHONPATH so subprocess instrumentation/imports resolve current source at startup. Do not hide coverage gaps with exclusions.
- A replaced capture source can complete a blocked read/open later. Check its generation before recording errors as well as frames. After an oversized incomplete serial frame, discard until the next newline; clearing the buffer alone can accept an invalid frame's ACK/CMD-looking suffix.
- Operator mutations need regressions for every auth route and invalid/nonfinite settings. A pending enable must not silently drop a later neutral request. Concurrent desktop sessions must have distinct per-port token files. Validate imported traces before any playback and stop timers on close.

- The native Qt operator workstation supports Mac and Pi desktop, plus remote access to a headless Pi. Keep Qt optional for headless installs. Its owned server must run in a separate process: Mac window initialization held the GIL long enough to trigger freshness faults in the initial thread-based draft. Keep loss/ACK deadlines intact.
- Mac venv Qt plugins carried UF_HIDDEN flags and were skipped by Qt. Source launch copies plugins without metadata. Build/sign the Mac .app outside the project file-provider folder, then install in ~/Applications; Finder metadata inside the project broke strict code-signature verification.

- Use the documented module entry point from software/ for development, or reinstall the package after source edits before testing an installed console script. Do not mistake a stale installed copy for current source.
- A latest-frame mailbox must never erase a target-loss neutralization event. Keep requested loss-zero atomic with the processed frame, independently of preview/viewer delivery.
- Reject serial integer overflow explicitly on the 32-bit Pico; host-width strtol behavior is not proof of target correctness. Unplugged serial failures must still allow neutral state, shutdown and summary saving.

- Serial ACKs must advance the accepted sequence; reordered replies cannot overwrite newer neutral state. Duplicate READY after handshake cannot refresh command-ACK freshness. Compare Python protocol replies/state with compiled C using injected time; account for float rounding at exact watchdog deadlines without relaxing the 250 ms policy.
- Validate complete desktop snapshots and nested numeric/detection/trace fields before signals reach widgets. Operator authorization requires explicit boolean true. Close/switch confirmation means validated backend assistance-disabled and requested-zero state, not physical transmitter output or a fresh bridge ACK.

- Require strict operator request types and reject unknown fields. Coercion of strings such as "yes" can enable assistance, and booleans can silently become numeric settings. Keep browser/native requests typed. Check inclusive deadband boundaries against independent controller trajectories; weighted smoothing must preserve exact input when smoothing is 1.
- Exhaustive and seeded parameter matrices must assert independent behavior/state invariants. Distinguish parameterized test counts from operations inside tests; preserve failing development output and current full source manifests. Keep fake-device/offscreen/container scope explicit.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Current documentation index](docs/README.md) — Project scope, deferred work and source/evidence map.
- [HackPHS 2026 Google Doc](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit) — Current source plan; later user decisions are recorded in docs/decisions.md.
- [OVONIC 2S 1100 mAh 60C XT30 two-pack listing](https://us.ovonicshop.com/products/2-ovonic-rebel-2-0-60c-2s-1100mah-lipo-battery-lihv-7-6v-pack-with-xt30-plug-for-size-100mm-to-140mm-brushless-drones-long-range-drone-fpv) — Listing fields are inconsistent; physical labels and measurements govern.
- [Apex-2 frame seller listing](https://speedyfpv.com/products/apex-2-2-inch-95mm-carbon-fiber-drone-frame-kit?variant=46334350164182) — Seller recommendation; verify the delivered hardware.

## Repository delivery

Push completed work directly to `main` (user decision, 2026-10-09). Handle integration of remote changes without requiring the user to manage branches or merges.
