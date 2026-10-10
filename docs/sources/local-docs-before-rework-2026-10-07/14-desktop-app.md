# Native desktop application

Updated 2026-10-05. User selected **Desktop app for Mac and Pi** after reviewing the browser dashboard. The installed `/Users/devk/Applications/Ball Drone.app` is older than this source until it is rebuilt.

## What it is

The operator workstation uses Qt Widgets (PySide6), with native menus, fixed source, measurement and event panels, video rendering, a yaw history plot, source controls, detector/controller settings, mock fault controls, session events and file dialogs. Panels do not undock. The green zoom button fits the window to the visible screen instead of letting the frame or a panel draw past it. It does not embed a browser. Visitor phones/tablets still use the locally served browser page and their isolated sandbox.

| Mode | Processing and logs | Operator workstation |
| --- | --- | --- |
| Mac standalone | Desktop-owned mock server on the Mac | Mac window |
| Pi standalone with display | Desktop-owned mock server on Pi 5 | Pi window |
| Pi headless | Existing Pi service | Mac window connects to Pi, or visitor browser |

Desktop-owned processing runs in a separate process so Qt rendering cannot hold the Python control threads. Capture/control and viewer delivery retain the existing backend behavior. Startup is synthetic moving input, mock output, MANUAL and disabled. Loss/fault/disable still requests zero. Starting another instance selects the first available port from 8080–8089. The status line keeps that URL on the left of the status bar, with a pad before the window resize grip, so the port stays visible. The operator preview is a 16:9 plate letterboxed in the video well. It reads "No signal" and does not draw the synthetic target, grid, or scenario caption. While the source is synthetic, measurements, the yaw trace, and the session log stay placeholders: em dashes, an empty plot, and "No events". Recorded video or a camera can fill those fields. Mock transport is not shown as a live measurement. The tracker still runs behind the window. In the source column, Enable yaw assistance is the filled action, Disable and Apply are outline actions, and detector settings is a text disclosure. The state word is a normal label. Until the owned server answers, the status line says the local session is starting. "Connection lost" is reserved for a session that was live and then stopped updating. Mac simulation stays independent on port 8765.

## Mac application

Built app: `/Users/devk/Applications/Ball Drone.app`. Double-click it in Finder or run:

```sh
open '/Users/devk/Applications/Ball Drone.app'
```

This app bundles Python, Qt, OpenCV and the demo backend; a terminal or development venv is not needed to launch it. It is an Apple Silicon build, ad hoc signed locally, not Apple Developer notarized or a tested Intel build.

For source development:

```sh
cd /Users/devk/Documents/HackPHS26/software
.venv/bin/python -m pip install -r requirements-desktop.lock
.venv/bin/python -m ball_demo.desktop
```

Build using the same Mac venv, with PyInstaller 6.22.3 installed:

```sh
.venv/bin/python desktop/build-mac.py
```

The builder stages in `/tmp` and installs into the user's Applications folder. It only replaces a same-named app carrying this project's bundle identifier. The project directory's file-provider Finder metadata caused signature verification failures; staging outside it corrected this. Hidden Qt plugin flags in this Mac's venv required a metadata-free temporary plugin copy for source launches. Both corrections are in the launch/build code.

## Raspberry Pi desktop

Requires a **64-bit Raspberry Pi OS Trixie desktop session**, Python 3.13+, a display, and the project's software folder. The pinned ARM64 Qt wheel requires glibc 2.39 or newer. Use the headless installation for Raspberry Pi OS Lite without a display.

```sh
bash software/deploy/install-desktop-pi.sh
```

The installer creates a separate `.venv-desktop` and a Ball Drone application-menu launcher. It does not enable a second system service. Launching that shortcut starts a local mock server; if the existing port-8080 service is running, the desktop's new session uses another port. To operate the existing service instead, connect through **File → Connect to Pi / server** or:

```sh
software/.venv-desktop/bin/ball-desktop \
  --connect http://127.0.0.1:8080 --token-file /path/to/private/operator-token
```

Keep operator tokens out of screenshots, visitor URLs and shared files. The service token is owned by its service account; explicitly provision a private readable copy for the chosen operator if needed. No token is needed for read-only viewing.

## Connecting a Mac to Pi

Use **File → Connect to Pi / server**, enter the Pi's actual reachable address (for example `http://<Pi-IP>:8080`) and an operator token for control. Blank token gives read-only viewing. Remote credentials remain in memory, with automatic redirects disabled. Source recordings must exist on the processing device: the remote-source field accepts a Pi path and does not upload a Mac video.

Switching away from a controlled remote server requires acknowledgement that assistance is disabled. Closing a remote operator window also requests disable and remains open if neutral cannot be confirmed. Network loss marks preview/readouts stale, disables new assistance/settings actions and reconnects reads; it never re-enables assistance.

**Limit:** loss of the desktop client's connection does not itself stop a remote server whose video/bridge remain fresh. The backend's 250 ms deadlines cover source and bridge freshness, not an operator-client lease. This remains a mock/recorded software demo; physical operator authority and radio failover remain hardware integration work.

## Operation

1. Select a synthetic scenario and **Apply source**. That source does not fill the preview or the measurements. Recorded video uses a native file picker in local mode; camera adapter needs actual-device verification.
2. Deliberately enable assistance. With a recorded or camera source, watch state, error, requested yaw and accepted internal yaw. Synthetic stays at placeholders.
3. Choose Loss/Freeze scenarios or a mock bridge condition to inspect neutralization and faults.
4. Recover the mock bridge with Normal and Apply, then explicitly re-enable only when ready.
5. Use **Tools → Play isolated scenario** for independent trace playback. It has no bridge/client mutation reference. The drawing reconstructs target truth/detection; blur, noise and lighting effects are not replayed as original pixels.
6. Use **File → Open session folder** for local CSV/JSONL/config. Summary is saved on shutdown. Remote logs remain on the server.
7. Visitor page: **File → Open visitor page**. Other devices use the host's actual reachable IP and the status-bar port. The default local server listens on all interfaces; pass `--listen 127.0.0.1` for Mac-only use.

## Evidence and limits

The native app now has [automated regression verification](15-verification.md), including real Qt/client/server integration, shutdown and parent-death checks. Desktop-owned private tokens use `operator-token-<port>` inside the data directory so concurrent sessions do not overwrite them. The headless CLI's token remains `operator-token`.

The latest hardware-free pass runs **4,059 tests** on both Mac and Linux ARM64, with **99.58% / 99.63% combined statement/branch coverage** and **99.58% / 99.79% for the desktop module**. It includes actual widget rendering assertions, validation/dialog error paths, launch wiring and mock camera/serial failures. The Mac app was rebuilt with strict operator input validation and the exact smoothing/deadband correction. [Current evidence](../../../evidence/verification/README.md) preserves the older 350-, 260- and 146-test baselines separately.

Imported traces are validated in full before playback, closing stops their timers, and malformed server state does not refresh client freshness. A disable queued during a pending enable is sent after that request completes; queued enable cannot replace pending neutral. Close/switch requires a complete validated snapshot with assistance disabled and requested yaw zero. This confirms backend software state; it does not confirm a physical transmitter output or even a new bridge ACK. Operator authorization requires explicit boolean true. Nested snapshot/trace detection and numeric settings fields are validated before delivery to widgets. Client/network ordering is not a physical neutralization deadline.

See [desktop evidence](../../../evidence/desktop/README.md). Mac native launch/render and Linux ARM64 offscreen render are separate results. Container rendering does not verify Pi display drivers, throughput, thermals, camera/USB, networking or flight behavior. Existing 50-test and 30-minute browser results describe earlier software; they are not native-desktop endurance results.

Implementation: `software/ball_demo/desktop.py`, `desktop_backend.py`; optional desktop dependency lock and Pi installer. Headless dependencies remain separate. `/api/preview.jpg` serves the backend's existing cached JPEG to desktop clients without another encoding pipeline.

Primary references: [Qt for Python](https://doc.qt.io/qtforpython-6/gettingstarted.html), [PyInstaller Mac bundle guidance](https://pyinstaller.org/en/stable/usage.html#building-macos-app-bundles).


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Pre-rewrite archive index](README.md) — identifies this file as historical context, not current instruction.
- [Maintained document](../../14-desktop-app.md) — current requirements and status.
- This citation note is external to the preserved pre-rewrite text.
