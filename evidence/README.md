# Hardware-free software evidence

Current 2026-10-08 [navigation evidence](navigation/README.md): 4,380 desktop/3,997 core passes, fresh source hashes, real-browser guidance, deterministic replay and repeatable synthetic depth-map → autonomous mock goal. A real Pi 5 preflight, app install/service check and capture probe are recorded below. The service workers/health endpoint are healthy, but the camera session is in FAULT because `/dev/video0` returned uniformly black frames; live RC832 video remains unverified. D435, Mega, radio and aircraft behavior are also unverified. Historical entries below retain their original scope.

## Manual fallback, deployment, Mega and simulator — 2026-10-08

| Check | Evidence | Outcome and scope |
| --- | --- | --- |
| Manual-fallback screen and operator fixes in Chromium | [report](fallback-2026-10-08/browser-fallback-checks.json), [fallback screen](fallback-2026-10-08/fallback-screen.png), [monitor](fallback-2026-10-08/fallback-monitor.png) | 11/11 pass. Fallback page shows status, server video with box and centre/error. Stale video is marked separately from the connection. Invalid replay is rejected. A disable is never overtaken by a slow enable. Lock goes neutral first. Click-to-pick sets the hue from the video. Closing the operator page lapses the lease to neutral. No page errors or external requests. Synthetic source and mock bridge. |
| Pi installer in ARM64 userland containers | [Trixie](pi-install-2026-10-08/trixie-arm64-container.txt), [Bookworm](pi-install-2026-10-08/bookworm-arm64-container.txt) | Trixie: real installer completes. The service account gets `video` and `dialout`, the token file is 0600, the service command starts healthy in MANUAL, and `/fallback` is served. Bookworm: refused by the preflight before any change. Containers, stubbed systemd; not a Pi. |
| Raspberry Pi 5 preflight, install, service and capture probe over SSH | [report](physical/pi-preflight-2026-10-08.txt) | Pi 5 / aarch64 / Trixie / Python 3.13 / 4045 MB; preflight passes, app installed, service enabled/active and health endpoint is good in MANUAL/mock. OpenCV reads `/dev/video0`, but 30 frames are uniformly black; live RC832 picture remains unverified. Mega serial device absent. |
| Mega bridge as AVR firmware | [simavr run](firmware/mega-avr-simulation-2026-10-08.txt) | Line framing, sequence limits, watchdog at rollover and random bytes pass on a simulated ATmega2560; Linux ASan + UBSan pass. The sketch also compiles with `arduino-cli` (5,456 B flash, 600 B RAM). Not flashed. |
| Full verification, current source | [report](verification/20261008T211848Z/report.json) | **4,405 passed**, zero failures/errors/skips; combined coverage **98.15 %** (statements 98.93 %, branches 95.46 %); every module gate including the new video-health, colour-pick, latency and session modules at 100 %; Mac UBSan for the C core and the Mega line reader; `arduino-cli` Mega compile clean. The preceding run, [20261008T203005Z](verification/20261008T203005Z/report.json), failed only because a tool file was added during it, and is kept. |
| Rebuilt Mac app | [packaged run](desktop/mac-packaged-2026-10-08/README.md) | Strict signature verification passed. The offscreen launch was healthy, served `/fallback`, ran 13.3 s / 249 frames / 0 faults, and saved its summary. |
| Simulator smoke | [report](simulation-smoke.json), [industrial](simulation-industrial.png) | Three maps, fixed-step flight, power/camera/pause, telemetry shown as text, failed-level recovery, no page errors, offline. Software WebGL. |

Recorded 2026-10-04. Mac environment: **macOS 26.6.2, Apple Silicon ARM64, Python 3.13.12**. Browser checks use Playwright Chromium. Linux check: **ARM64 Colima VM / Docker container, Python 3.13.16**. No aircraft, Raspberry Pi or Pico hardware was connected.

| Check | Evidence | Outcome and scope |
| --- | --- | --- |
| Expanded desktop/API/process/serial/verification regressions | [Current verification results](verification/README.md), [reproduction guide](../docs/15-verification.md) | 4,059 tests pass on Mac and Linux ARM64; zero skips. Combined statement/branch coverage 99.58% / 99.63%; controller/detector/source code 100%. C UBSan on Mac and ASan + UBSan on Linux pass. Offscreen/mock/fake-device/PTY only. |
| Python detector/controller/protocol/engine/PTY/replay/API | [test output](python-tests.txt) | 50 passing tests; one upstream FastAPI/Starlette test-client deprecation warning. |
| Deterministic scenes / accuracy | [fixture results](fixtures.json) | 17 scenes; clear-target accuracy gate ≤5 px passed; difficult scenes separately reported. |
| Fresh Mac environment | [install output](fresh-install.txt), [fresh startup](fresh-smoke.json) | Locked packages installed into a new venv; installed command completed handshake/watchdog plus API/vision/logging smoke. |
| Portable C core | [host output](firmware-host-tests.txt) | Parser, bounds, disabled zero, session/sequence/watchdog and time rollover pass with host Clang. |
| Pico SDK compile | [build log](pico-build.txt), [toolchain](firmware/toolchain.txt) | Official SDK 2.2.0, Arm GNU 14.3.Rel1; RP2040/Pico USB CDC scaffold compiled. |
| Firmware artifacts | [UF2](firmware/ball_bridge.uf2), [ELF](firmware/ball_bridge.elf), [SHA256](firmware/SHA256SUMS) | Compiled, not flashed or electrically verified; no trainer output. |
| Responsive browser / auth / faults / reconnection / sandbox | [browser report](browser-checks.json) | Desktop and 390px phone view; no page errors. Real server disconnect/restart reconnects disabled. |
| Offline application assets | [browser report](browser-checks.json) | Browser external requests blocked; only localhost requests; no CDN/cloud assets. Mac internet was not physically disabled. |
| Linux ARM64 install/startup/vision/API/logs | [smoke output](arm64-smoke.txt), [image build](arm64-build.txt) | Passed package/import/20 Hz synthetic operation/API/summary checks; not Pi throughput or USB support. |
| Existing Mac simulation | [simulation report](simulation-smoke.json) | Re-recorded 2026-10-08 for the free-flight game (see the section above). Short smoke, not full flight playthrough. |
| Six-browser Mac rehearsal | [rehearsal report](mac-rehearsal.json), [progress](mac-rehearsal-progress.txt), [session summary](rehearsal-session/summary.json) | Passed 1800.16 seconds with one operator + five viewers; no failures/page errors. State API p95 4.81 ms, maximum 26.77 ms. |

## Demonstration artifacts

- [Native desktop app evidence](desktop/README.md): Mac source/packaged launch, Cocoa controls, native operator walkthrough and Linux ARM64 offscreen rendering. This is a separate interface revision; earlier tests/endurance results do not validate native GUI endurance.

- [Desktop dashboard](dashboard-desktop.png), [phone dashboard](dashboard-phone.png), [visible fault](dashboard-fault.png).
- [Software walkthrough video](walkthrough.webm): synthetic tracking, target loss, stale source, missing ACK, recovery and restart. No physical aircraft footage.
- [Demonstration summary](demonstration-session/summary.json), [config](demonstration-session/config.json), [CSV samples](demonstration-session/samples.csv), [JSONL events](demonstration-session/events.jsonl).
- [Browser-importable replay](demonstration-replay.json): event/sample timeline; replay never opens a serial device.
- [Example visitor QR](connection-card/visitor-qr.png), [card text](connection-card/visitor.txt): points to **Mac loopback preview**, not a real Pi address. Generate an actual card from the active Pi profile on arrival. No operator token included.

## Reproduction and limits

Run commands from [software README](../software/README.md), [firmware README](../firmware/README.md) and [runbook](../docs/12-demo-runbook.md). Tests inject deterministic ground truth/time where appropriate; browser tests and rehearsal use real host processes and clocks. Runtime source videos and private credentials live in ignored `software/runs/`, not here.

Mac and ARM64 container results do not verify Pi thermals/FPS, hotspot/client hardware, receiver timestamps, physical USB behavior, trainer electrical signals, command direction/channel mapping, physical pilot override, complete video-to-radio latency or aircraft response. Those remain [arrival checks](../docs/13-hardware-arrival.md). CAD evidence is in [cad/apex2-cage](../cad/apex2-cage/README.md) reviews and the [CAD kit](../cad/kit/README.md); it is vendor-dimension geometry, not printed or fitted parts.

The 30-minute run exercised the initial runnable baseline while final edge-case guards were developed. That baseline separately passed 50 tests, browser checks, fresh startup and Linux ARM64 smoke. The latest desktop/runtime revision has its own 4,059-test results linked above; the 350-, 260- and 146-test passes are retained as history. The long run measures Mac multi-viewer responsiveness; it is not a release timing guarantee or a physical control-path measurement.

### Rehearsal timing finding

The session logged three deliberately injected missing-ACK faults and **one unplanned stale-frame fault** at 1720.70 seconds during concurrent build/browser workloads. Requested yaw was zero at every fault; assistance remained disabled after the unplanned stale frame. Browser responsiveness checks still passed. Session throughput was **18.62 processed frames/s** against a 20 Hz target, processing-only p95 **1.406 ms**. This is a Mac scheduling/load observation, not measured end-to-end hardware latency. Verify deadlines under the intended Pi workload before physical integration.

## Local handoff package

[Source/docs/firmware/evidence archive](ball-drone-software-0.1.0.zip) · [archive checksum](handoff-sha256.txt) · [file manifest](package-manifest.json) · [installable Python wheel](wheels/ball_drone_demo-0.1.0-py3-none-any.whl). The independent simulation repository, SDK/compiler, Python environment, runtime videos/logs and private tokens are excluded; the selected demonstration/rehearsal evidence is included.

## Dashboard design revision

After user feedback, the dashboard was revised into a light compact monitor with a separate Sandbox tab and expandable tuning controls. [Monitor](dashboard-revision/monitor.png), [operator](dashboard-revision/operator.png), [sandbox](dashboard-revision/sandbox.png) and [phone](dashboard-revision/phone.png) captures were visually inspected. Automated reports and the walkthrough above remain evidence of the preceding interface; those suites were not rerun in this styling pass.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Automated verification report index](verification/README.md) — Current source manifests and environment-specific outcomes.
- [Software run guide](../software/README.md) — Reproduction entry points.
- [Hardware arrival checks](../docs/13-hardware-arrival.md) — Physical/device claims not covered by saved evidence.
