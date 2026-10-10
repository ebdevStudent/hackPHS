# Ball Drone software demonstration

Synthetic/recorded video → OpenCV detector → four-state yaw controller → mock/serial bridge → offline browser dashboard. No transmitter output is implemented. The Pi 5 is the planned processing/server host; the Mac develops this software and runs the separate 3D simulation.

## Start on the Mac

**Native app:** open `/Users/devk/Applications/Ball Drone.app`. For source development, install `requirements-desktop.lock` in the venv and run `.venv/bin/python -m ball_demo.desktop`. It starts an independent mock session with native video/controls; visitor browsers can still connect. [Mac/Pi desktop guide](../docs/14-desktop-app.md).

The commands below start the separate headless/browser server. To operate a server already running on Pi, use the native app's **File → Connect to Pi / server** rather than starting another local session.

Python 3.13 or newer is required. Run from this directory:

```sh
cd /Users/devk/Documents/HackPHS26/software
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-deps .
.venv/bin/python -m ball_demo.cli serve
```

Open **http://127.0.0.1:8080/**. Startup is MANUAL, disabled, synthetic moving target, mock transport. The private operator token is saved to `runs/operator-token` with mode 0600. Read it locally and enter it in **Operator access**. It is never placed in visitor URLs, logs, QR cards or browser persistent storage. A restart generates a new token unless `BALL_OPERATOR_TOKEN` was supplied in the environment.

For another device on your trusted demo network, pass `--host 0.0.0.0` and use this Mac's actual reachable IP. Browser devices do not need Python. The simulation remains on port 8765. The demo is a local network application; do not expose its plain HTTP operator traffic to the public internet.

## Commands

```sh
# Reproducible synthetic clips, ground truth and isolated traces:
.venv/bin/python -m ball_demo.cli fixtures --output runs/fixtures
# Recorded input: assistance still starts disabled; normal EOF returns MANUAL; plays at the file's frame rate:
.venv/bin/python -m ball_demo.cli serve --recorded runs/fixtures/moving.avi
# Live camera (index on the Mac, /dev/videoN on Linux, Video4Linux2 chosen automatically):
.venv/bin/python -m ball_demo.cli cameras
.venv/bin/python -m ball_demo.cli serve --camera 0
# Camera-to-decision latency with a full-screen flash (or --trigger gpio on a Pi LED):
.venv/bin/python -m ball_demo.cli latency --camera 0 --trigger screen --trials 20
# Check the latency tool itself against a simulated 80 ms camera:
.venv/bin/python -m ball_demo.cli latency --simulated-delay-ms 80 --trials 5
# Internal bridge handshake/watchdog exercise:
.venv/bin/python -m ball_demo.cli bridge-check
# Real pyserial through a virtual serial peer:
.venv/bin/python -m ball_demo.serial_emulator --fault partial
# Recorded session replay export; import JSON in the visitor sandbox:
.venv/bin/python -m ball_demo.cli replay runs/<session-id> --output runs/replay.json
# Visitor connection card: use the active server address, never an operator token:
.venv/bin/python -m ball_demo.cli connection-card --url http://127.0.0.1:8080/ --network 'Mac local preview'
# Unit/integration checks:
PYTHONPATH=. .venv/bin/python -m pytest tests -q
```

For source-code development, use `python -m ball_demo.cli` from `software/` so edits are loaded directly. After edits, reinstall with `pip install --no-deps .` before using an installed `ball-demo` console script elsewhere. Do not reuse an old process when testing code changes.

## Optional navigation and D435 mapping

[Navigation runbook](../docs/23-navigation-software.md) documents the retained mapped-navigation implementation. **D435 room mapping is not part of the current project/demo workflow**; its existing code and records are retained without further extension. For the portable mission scope, see the [portable visual missions plan](../docs/27-portable-visual-missions-plan.md). The D435 capture and navigation commands below are historical/optional tooling only and are not prerequisites for the current demo. The actual Python requirement stays >=3.13; do not assume RealSense wheels support Pi ARM64/macOS.

```sh
.venv/bin/python -m ball_demo.cli nav-fixtures --output runs/navigation-fixtures
.venv/bin/python -m ball_demo.cli nav-replay runs/navigation-fixtures/synthetic-session.json --output runs/navigation-replay.json
.venv/bin/python -m ball_demo.cli nav-demo runs/navigation-fixtures/synthetic-session.json --output runs/navigation-demo.json
.venv/bin/python -m ball_demo.cli serve --nav-replay runs/navigation-fixtures/synthetic-session.json
```

Use the browser's **Mapped guidance** replay input for exports; it cannot mutate the shared bridge. Examples are invented test data, not a completed corner map. Real captures use independently registered stationary D435 poses; reconstruction never fills holes as free space. `nav-simulate --bundle PATH --start X Y Z --goal X Y Z` runs mock waypoint feedback against a labeled simulation copy, including a real mapped bundle, with original geometry/evidence untouched.

## Portable visual mission backend

The Python service implements the existing Flutter visual/mission contract at `/api/ui/v1`: snapshot polling, immutable captured stills and JPEG frames, follow/stop/abort and landing request handling, plus request-result lookup. Reads work without a token and return `operator_authorized: false`; command mutations require the operator bearer token. Configure allowed browser origins with `BALL_OPERATOR_ORIGINS` (comma-separated; the published GitHub Pages origin is the default).

An optional server-owned roster can be loaded with `serve --roster PATH` or `BALL_ROSTER_FILE`. Keep this file under ignored runtime storage; it contains operator-prepared assignments and measured printed-tag sizes. Schema version 1 has `people` and `landing_sites` arrays. Person records require `person_id`, `display_name`, `tag_family: "tag36h11"`, `tag_id`, and measured `tag_size_m`. Landing sites additionally require `site_id`, measured footprint `width_m` and `length_m`; `pad_from_tag` records the measured pad-center transform when the tag is offset. Enabled tag IDs must be unique across roles.

Run a complete generated-image rehearsal without hardware:

```sh
PYTHONPATH=software python -m ball_demo.cli serve --portable-demo --data runs/portable-demo
```

Run that command from the repository root. Connect Flutter to `http://127.0.0.1:8080` with the private token in `runs/portable-demo/operator-token`. Follow Synthetic Walker, observe periodic tag loss/reacquisition, Stop/Abort, and rehearse synthetic touchdown. The invented camera/roster/scene are explicitly labelled synthetic. [Complete instructions and evidence](../docs/28-hardware-free-completion.md).

Only the explicitly synthetic video source can accept simulated missions. The follow lifecycle, follower trajectory simulator and landing descent simulator never send output to the bridge. Live-camera follow/landing, point-picked physical landing, audio/TTS, and WebRTC media negotiation remain unavailable. Relative target/pad pose estimation has generated-image coverage but needs calibration from the final FPV capture path before it can report aircraft-relative live pose. No hardware validation is implied by the API or mock status.

## Browser and rehearsal checks

For the current source/desktop/portable-firmware verification, run `software/.venv/bin/python tools/verify.py` from the project root. It saves JUnit, branch/statement coverage HTML/JSON, compiler results, dependency versions and source/evidence hashes in a new evidence folder. Headless profile: add `--profile core`. [Verification guide](../docs/15-verification.md).

```sh
.venv/bin/python -m playwright install chromium
cd /Users/devk/Documents/HackPHS26
software/.venv/bin/python tools/browser_checks.py
# Start the ordinary server separately before the measured 30-minute run:
software/.venv/bin/python tools/rehearse.py --seconds 1800
software/.venv/bin/python tools/simulation_smoke.py  # simulation server must be running
```

Browser checks use port 8081, create their own session/token, verify desktop/phone layout, source and bridge faults, visitor isolation, reconnection/restart and external-request blocking, and save a walkthrough. Rehearsal uses six actual Chromium contexts, preview and event streams, operator commands, viewer sandbox controls, and periodic fault injection. Both scripts output evidence under the root `evidence/` directory. They do not need aircraft hardware.

## Layout and storage

| Path | Responsibility |
| --- | --- |
| `ball_demo/config.py` | Software demonstration defaults. |
| `sources.py`, `vision.py` | Capture adapters, deterministic scenes, HSV/continuity detector. |
| `control.py`, `engine.py` | State transitions, bounds, separate capture/control clocks. |
| `protocol.py`, `bridge.py`, `serial_emulator.py` | Version 1 internal-state protocol, transports and PTY peer. |
| `session.py`, `fixtures.py` | CSV/JSONL/summary, deterministic replay/traces/ground truth. |
| `api.py`, `static/` | Authenticated operator actions (assist, heartbeat lease, colour pick, source, settings), public reads, local browser assets including the read-only `/fallback` screen. |
| `video_health.py`, `color_pick.py`, `latency.py` | Frozen/blank live-picture faults, click-to-pick HSV thresholds, flash-to-detection latency tool. |
| `deploy/` | ARM64 container check, Pi installer, service, network and connection cards. |
| `runs/` (ignored) | Session directories, private token, fixture videos and exported replay. |

`BALL_DATA_DIR` selects another runtime location. No user recording or local credential is committed. Checked evidence is intentionally preserved in root `evidence/`, separate from runtime logs. Camera adapter is present but not physically verified; selecting it may prompt macOS camera permission. Recorded files are decoded at the configured processing rate, not their original playback clock. Synthetic timing faults are generated by the adapter rather than encoded in an AVI file.

[Architecture and defaults](../docs/04-software.md) · [runbook / deployment](../docs/12-demo-runbook.md) · [pre-hardware status](../docs/11-pre-hardware-status.md) · [hardware arrival](../docs/13-hardware-arrival.md) · [firmware](../firmware/README.md).


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Current software verification](../docs/15-verification.md) — Reproduction and interpretation of checks.
- [Saved evidence index](../evidence/README.md) — Reports, environment and limits.
- [OpenCV documentation](https://docs.opencv.org/) — Vision library reference.
