# Software verification

Updated 2026-10-04. This describes the automated verification added after the native desktop app, including additional protocol-parity, shutdown-race and malformed-response regressions. Simulation and physical flight are separate scopes.

## Run it yourself

From the project root, with the development venv prepared:

```sh
software/.venv/bin/python -m pip install -r software/requirements-dev.lock
software/.venv/bin/python -m pip install -r software/requirements-desktop.lock
software/.venv/bin/python tools/verify.py
```

The default desktop profile includes offscreen native Qt tests and real local mock-server processes. It does not open camera/physical serial devices or require aircraft hardware. A host C compiler is required. Runtime/fixtures/tokens use temporary storage.

For a headless development environment without Qt:

```sh
software/.venv/bin/python tools/verify.py --profile core
```

The core profile explicitly excludes the four desktop GUI test modules and their GUI coverage; desktop dependencies are not silently skipped. The default desktop profile requires Qt and fails if any selected test is skipped.

Every run gets a new directory under `evidence/verification/`. Use `--output /path/to/new-directory` for an explicit location. Existing evidence is never overwritten. Exit code **0** means all checks passed; nonzero means failure. Read `report.json` and `pytest.txt` even when a run fails.

## What the report proves

| Claim | Checks |
| --- | --- |
| Bounded software yaw; direct neutral | Existing controller tests plus 6,000 seeded controller operations, acquisition after loss, and neutral despite a tiny ordinary slew limit. |
| Source/bridge failure disables output | Live capture freeze/delay/stop, target loss, disconnect/missing/delayed ACK, and native operator fault/recovery against a real mock-server process. |
| Auth guards every operator write | Missing/wrong tokens tested on assistance, source, settings, fault injection and reset. Viewer Qt controls stay disabled. |
| Settings reject bad input without partial changes | Boundary/crossed-range tests; NaN/Infinity produce JSON 422 responses rather than server errors. |
| Native client handles failure truthfully | Actual Qt signals/widgets; malformed state is not fresh, old connection replies are ignored, redirects do not receive forwarded credentials, stale readouts are cleared, reconnection does not enable assistance. |
| Disable survives an in-flight enable | Queued neutral is sent after the outstanding request completes and cannot be replaced by a queued enable. This is an ordering guarantee, not a physical latency guarantee. |
| Native local/remote close behavior | Owned process shutdown requests neutral and saves summary; remote close confirms disabled state without stopping the remote server. Repeated close is harmless. |
| Process lifecycle is reviewable | Restart generates a new session/token; port conflicts use a fallback; concurrent token files are private and distinct; killing a parent triggers child neutral/shutdown/summary. |
| Sandbox stays isolated | Native play/pause/reset/close produces no shared commands; closing stops playback; all imported samples are validated before playback. Browser results remain separately recorded. |
| Fixtures/replay/serial emulator really work | Generated AVI decoding, truth/trace files, replay sequence, actual PTY + pyserial and emulator CLI under six bridge conditions. No physical serial device. |
| Portable firmware parsing holds up | C parsing/bounds/session/sequence/watchdog/clock-wrap assertions, 10,000 seeded arbitrary byte frames, command-boundary sweep and host sanitizer run. No GPIO/trainer output. |
| Verification failures remain visible | Runner self-tests inject dependency/compiler/compile/run/timeout/missing-report/test/skip/coverage/source-change failures and confirm nonzero exit, saved failed evidence and refusal to overwrite existing results. |
| Desktop failure paths and rendering | Invalid snapshot/trace fields, connection origin validation, cancelled/rejected dialogs, session-folder behavior, bounded event history, actual offscreen video/plot pixels and startup/cleanup wiring. |
| Camera adapter failure and source switching | Fake camera open/read failures, requested capture properties, camera loss distinct from recorded EOF, and late frames/errors from a replaced source. No physical camera. |
| Stream delivery drops obsolete previews | SSE state framing, MJPEG framing/deduplication and generator shutdown, tested directly through the application's stream generators. |
| Python and compiled C protocol agree | 4,800 seeded operations compare actual replies and internal state; ten clock origins check the 249/250 ms watchdog boundary. ASCII session constraints are tested. These are host software checks, not Pico timing measurements. |
| ACK order and handshake replay | Reordered ACKs cannot replace newer accepted neutral state; duplicate READY cannot refresh command-ACK freshness. Eight seeded chunkings exercise framing and malformed replies. |
| Complete desktop replies are required | Nested nonfinite/invalid detections, settings and trace fields are rejected; operator access requires explicit boolean true. Close/switch requires a validated disabled snapshot with requested yaw zero, not proof of physical output. |
| Shutdown discards late capture completion | Coordinated threads return frame/error/EOF after stop; replaced openers return errors/EOF without faulting the new source. Shutdown remains neutral and saves its final event. |
| Oversized serial framing stays invalid | Host adapter and emulator discard through the next newline after an oversized incomplete frame; a suffix resembling a valid ACK/CMD cannot refresh state. Split frames and valid recovery are tested. |

Test files: `software/tests/test_core.py`, `test_contracts.py`, `test_desktop.py`, `test_desktop_edges.py`, `test_desktop_robustness.py`, `test_protocol_parity.py`, `test_desktop_backend.py`, `test_cli.py`, `test_serial.py`, `test_bridge_edges.py`, `test_emulator_edges.py`, `test_io_edges.py`, `test_replay.py`, `test_verify_runner.py`, `test_protocol_exhaustive.py`, `test_vision_matrix.py`, `test_control_model.py`, `test_api_matrix.py`, `test_session_matrix.py`, `test_engine_deadlines.py`, `test_desktop_matrix.py`; portable C assertions in `firmware/test_core.c`.

## Large regression matrices

The additional matrices expand behavior checks across documented domains:

- Every permitted integer yaw (−1000 through +1000) round-trips through Python and the actual compiled C core, then disables and rejects a stale sequence without changing neutral state.
- Every byte outside the ASCII session alphabet is rejected; malformed integer spellings are compared in both implementations.
- All 120 permutations of five ACKs must preserve the latest accepted sequence/state; duplicates cannot refresh ACK freshness.
- All 180 OpenCV hue values, four image widths, target positions/sizes, exact contour-area gates, fixture timestamps and continuity forgetting thresholds have geometric assertions.
- Controller trajectories compare against a discrete reference across gain/smoothing/direction/acquisition/timing settings; randomized event sequences use a separate state-machine model.
- API request types, unknown fields, malformed bodies and mixed valid/invalid mutation sequences check atomicity and disabled output. Operator schemas require correctly typed JSON fields; strings and booleans are not accepted as numeric tuning values, and assistance requires a JSON boolean. Unknown fields return 422 rather than being ignored.
- Native snapshots, traces and all five-request assistance queue sequences check validation and neutral priority. Session CSV/JSONL/summary round trips independently check counts, ordering and timing percentiles.
- Injected-clock engine ticks and enable requests check 249/250/251 ms source/ACK boundaries, fault priority and zero command output.

Parameterized cases count as individual pytest tests; seeded operations inside a case do not. A large test count indicates domain coverage, not a corresponding number of features, proof of all inputs, hardware correctness or flight readiness. Fixture pixels and expected values are constructed independently where possible. Failed development assertions are preserved separately from full verification reports.

## Evidence files and gates

- `report.json`: environment, Python/dependency/compiler versions, exact commands, outcomes, duration, scope limits and source SHA256 manifests before/after the run.
- `junit.xml`: individual test names, failures/errors/skips and timings for CI/review tools.
- `pytest.txt`: complete assertion output, warnings and missing coverage paths.
- `coverage.json` and `coverage-html/index.html`: measured statement/branch paths, including gaps.
- `firmware.txt`: compiler/run output from the portable C checks.
- `SHA256SUMS.json`: file hashes for checking evidence integrity.

The runner fails if source inputs change during the run, any test fails/skips, a required dependency/compiler is missing, or coverage falls below its gate. Default overall combined statement/branch coverage floor: **95%**. Module floors: controller/camera-source/detector **100%**; protocol/engine/bridge/API/desktop/desktop backend **95%**; serial emulator **90%**. The source manifest enumerates runtime Python, tests, portable firmware, tools, package configuration and dependency locks; it is not a Git commit or hardware certification. The core profile omits the desktop UI module only.

Subprocess/multiprocessing instrumentation is enabled in the coverage configuration using [Coverage.py's process guidance](https://coverage.readthedocs.io/en/latest/subprocess.html). Abruptly killed processes or uninstrumented command-line children can leave coverage gaps even when their functional tests pass; uncovered paths remain visible. Coverage never replaces an assertion about behavior.

Mac correction: Python 3.13 skips the coverage startup `.pth` when this venv's file-provider metadata marks it UF_HIDDEN. The runner temporarily clears that flag and restores it on completion/error. Self-tests check restoration. It also prepends the project's `software/` to `PYTHONPATH`, so early coverage startup and child imports resolve current source before an installed copy. The report records whether the flag workaround was used. These changes restored measured execution in the actual emulator CLI subprocess tests; code is not excluded to raise coverage.

## Results and limits

See [recorded verification results](../../../evidence/verification/README.md). The Mac desktop run and Linux ARM64 container run identify their actual environments. Offscreen Qt is an automated interface/logic check, not a visual approval or an actual Pi display test. Mac package launch/signature checks are separate from source-suite results.

The Mac AddressSanitizer trial stalled during runtime initialization before executing C tests; its failed report is preserved. Mac verification defaults to UBSan. Linux verification defaults to ASan plus UBSan. `--sanitizers address,undefined` explicitly requests both on a supported host; a timeout or error fails the run.

Outstanding: actual Pi desktop/display, camera receiver, USB/Pico/radio interface, physical pilot override, complete latency, throughput/thermal endurance and flight behavior. Remote client connection loss is still not an operator lease: a remote backend with fresh capture/bridge continues until disabled or a backend fault occurs. The prior 30-minute browser rehearsal is not a native application endurance result.

## Linux ARM64 reproduction

Build the existing ARM64 headless and desktop images, then the verification profile:

```sh
docker build --platform linux/arm64 -t ball-drone-demo:arm64 -f software/deploy/Dockerfile software
docker build --platform linux/arm64 -t ball-drone-desktop:arm64 -f software/deploy/Dockerfile.desktop software
docker build --platform linux/arm64 -t ball-drone-verification:arm64 -f software/deploy/Dockerfile.verify software
```

Run that image with read-only project inputs mounted at `/work/software/ball_demo`, `/work/software/tests`, `/work/software/pyproject.toml`, each `requirements*.lock`, `/work/tools` and `/work/firmware`. Mount a writable evidence directory at `/evidence`. The recorded [ARM64 command](../../../evidence/verification/arm64-command.sh) shows the exact mounts and new output location used here. Builds need package access; the tests use local synthetic input and local sockets. No claim is made that an ARM64 container has Pi hardware behavior.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Pre-rewrite archive index](README.md) — identifies this file as historical context, not current instruction.
- [Maintained document](../../15-verification.md) — current requirements and status.
- This citation note is external to the preserved pre-rewrite text.
