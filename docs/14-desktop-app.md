# Desktop workstation — existing software and live-demo requirements

Updated 2026-10-10. The native workstation adds optional mapped guidance alongside existing tracking. The Mega sketch is historical and accepts internal state only; the selected ESP32-S3 bridge and trainer output remain unimplemented/unverified.

## Flutter replacement direction — 2026-10-09

The user plans to replace the existing browser and native Qt operator interfaces with Flutter desktop and Android apps that use distinct layouts. This document describes the current native implementation until that replacement is built. The Flutter screen plan and backend contract are in [UIDEVPLAN.md](../UIDEVPLAN.md). Flutter remains an operator UI client; the Pi server and physical-control work are separate. The independent industrial simulator stays outside the app.

## Role and modes

The PySide6/Qt Widgets operator application supports local processing and connection to a remote Pi backend. It does not embed the 3D browser simulation.

| Mode | Processing | Operator |
| --- | --- | --- |
| Mac rehearsal | Separate local mock backend process | Mac native window |
| Pi with display | Local backend | Pi native window, actual-device checks pending |
| Headless Pi | Existing Pi service | Mac connects to actual Pi address |
| Visitors | Shared Pi/Mac monitor | Browser reads and isolated trace playback |

The Mac game remains separate on port 8765. The monitoring backend defaults to 8080; desktop-owned sessions choose an available port in 8080–8089. Keep the actual address visible.

## Source launch and packaged app

```sh
cd /Users/devk/Documents/HackPHS26/software
.venv/bin/python -m pip install -r requirements-desktop.lock
.venv/bin/python -m ball_demo.desktop
```

The installed Apple Silicon app is `/Users/devk/Applications/Ball Drone.app`:

```sh
open '/Users/devk/Applications/Ball Drone.app'
```

It was rebuilt from current source on 2026-10-08, including the 10-05 UI changes, the fallback overlays and the operator lease. Rebuild after any later source edit; a package does not follow the source by itself. The source builder is:

```sh
.venv/bin/python desktop/build-mac.py
```

It stages outside the file-provider project directory and installs into the user's Applications folder. Historical signing checks were local ad hoc checks, not Apple notarization or Intel testing. This rewrite does not run the builder.

## Prepared Pi desktop installation

The prepared installer targets 64-bit Raspberry Pi OS/Python 3.13+ and the pinned Qt runtime. The source hardware plan permits Pi4/5; actual installation/display/performance needs verification. The recorded Qt wheel expects glibc 2.39+.

From the project root:

```sh
bash software/deploy/install-desktop-pi.sh
```

It creates `.venv-desktop` and a menu launcher. A local desktop session owns a separate mock backend. To operate an already-running server, connect through **File → Connect to Pi / server** or:

```sh
software/.venv-desktop/bin/ball-desktop \
  --connect http://127.0.0.1:8080 --token-file /path/to/private/operator-token
```

Read-only users need no operator token. Keep tokens private and outside visitor URLs/screenshots. Local desktop sessions use separate per-port token files; headless service tokens remain on the processing device.

## Existing interface behavior

The source has fixed native panels, source controls, settings, measurements, video, yaw plot, events and isolated playback. The 16:9 video well says **No signal** for synthetic input; synthetic measurements/events/yaw remain placeholders. Recorded/camera sources can populate measurements. Mock transport is not real telemetry.

Startup/restart remains synthetic/mock/MANUAL/disabled. Disable, loss and fault request zero; recovery requires deliberate re-enable. New settings/source choices disable assistance.

Choose recordings via local file picker. For remote processing, recordings must exist on the Pi; the remote path field does not upload a Mac recording. Source/interface behavior is documented in the [preserved earlier desktop guide](sources/local-docs-before-rework-2026-10-07/14-desktop-app.md).

## Optional mapped guidance

The configured server's navigation dock shows estimated XYZ, pose age/provisional uncertainty, route/next waypoint, localization status and explicit pilot/advisory authority. It validates nested pose transforms/timestamps/source/route before widgets read them. Stale/disconnected state clears route/readouts and disables guidance actions.

Connect to a server launched with `--nav-bundle` or `--nav-replay`. **Tools → Import navigation bundle**, metric goal, Restore guidance and Stop guidance require operator authorization. Changing goal or losing pose disables guidance; reacquisition requires deliberate restoration. Stop cannot be overwritten by a pending restore in the operator queue. These commands never enable yaw assistance. Browser-local navigation playback is available from the browser UI; the independent 3D game remains separate. See [navigation commands](23-navigation-software.md).

Current native coverage uses offscreen Qt on Mac, alongside real-browser evidence. No new packaged app, actual Pi display or physical camera was tested.

## Required live manual-fallback display

Acceptance now requires **live FPV video**, target bounding box, center/error indicator and:

> Manual steering — computer steering unavailable

**Implemented 2026-10-08.** For a recorded or camera source, the video well now shows the server's picture with the target box and centre line. (Before this fix it never showed any picture.) The synthetic scene stays hidden behind "No signal".

Over the picture the workstation draws:

- the steering status banner, which is always shown;
- a centre/error indicator with the numeric error;
- "Target tracked" or "Target not found".

When frames stop arriving, the well says *Video stale · no fresh frames* even while the server still answers. **View → Manual fallback view** (Ctrl+Shift+F) hides the panels for presentation. **Pick target colour from video** (operator only, live sources only) sets the detector colours from a click on the target.

Verify this with the real RC832 capture before judging. Keep simulation and game visuals separate.

## Remote authority and known limit

Remote credentials stay in memory; redirects are disabled. Stale state clears live readouts and blocks new control/settings actions. Reconnect does not enable assistance.

Closing/switching a controlled remote session requests disable and requires a validated disabled/requested-zero response. That response is software state, not proof of transmitter output or a new bridge ACK.

**Operator lease (closed 2026-10-08):** an authorized workstation sends a heartbeat every 0.3 s. Assistance enabled through the API falls to FAULT/neutral (*operator connection lost*) 1.5 s after heartbeats stop: on a window close, crash, frozen UI or network loss. Recovery never re-enables. This is a software lease. Physical assisted presentation still needs independently verified radio override and failsafes.

## Evidence and presentation

The installed `/Users/devk/Applications/Ball Drone.app` was **rebuilt from current source on 2026-10-08** ([packaged run](../evidence/desktop/mac-packaged-2026-10-08/README.md)). Rebuild again after later source edits.

[Desktop evidence](../evidence/desktop/README.md) and [2026-10-04 verification](../evidence/verification/README.md) cover their recorded Mac/container/offscreen configurations. They do not verify ESP32-S3 trainer output, actual Pi display/capture, current packaged UI or native endurance.

Use the [runbook](12-demo-runbook.md) for manual/conditional assisted routes, and [verification guide](15-verification.md) for current-source checks. Never present synthetic yaw as aircraft telemetry.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Software source and startup](../software/README.md) — Current app package and launch instructions.
- [Native desktop evidence](../evidence/desktop/README.md) — Recorded app/environment checks and their limits.
- [Current verification guide](15-verification.md) — Reproduction commands and source provenance.

## Flutter client implementation — 2026-10-09

The [Flutter client](../software/flutter_operator/README.md) implements distinct desktop/web and Android screens. It is compiled and inspected with labelled fixtures. The [backend handoff](../software/flutter_operator/BACKEND_HANDOFF.md) defines the separately owned integration; the current Python server has no operator API. See [UIDEVPLAN.md](../UIDEVPLAN.md) for all behavior and the audit.
