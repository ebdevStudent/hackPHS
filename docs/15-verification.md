# Verification — software evidence and physical acceptance

Updated 2026-10-09 (backend mission/status contracts and refreshed core/desktop checks). Current requirements come from the revised source and user decisions. Historical results keep their original configuration/date. No Pi, D435 device or aircraft check was performed for these software runs.

## Reproduce software checks

From the project root:

```sh
software/.venv/bin/python -m pip install -r software/requirements-dev.lock
software/.venv/bin/python -m pip install -r software/requirements-desktop.lock
software/.venv/bin/python tools/verify.py
```

A host C compiler and selected dependencies are required. The desktop profile uses offscreen Qt and local mock-server processes. It does not require real aircraft/camera/serial hardware.

Headless core profile:

```sh
software/.venv/bin/python tools/verify.py --profile core
```

Core explicitly excludes GUI tests and UI coverage; desktop tests are not silently skipped. Each run creates new evidence under `evidence/verification/`; `--output` can select a new location. Exit zero means the configured checks passed. Read failed reports/logs too; never overwrite historical evidence.

### Additional checks — 2026-10-08

`tools/verify.py` now also builds and runs the Mega line-framing tests under the sanitizers. When `arduino-cli` is installed it compiles the Mega 2560 sketch and fails on warnings in project files; otherwise it records that compile under `not_run`. Its source fingerprint now covers browser JS/HTML/CSS, deploy scripts and the Mac builder.

| Check | Command (from the project root) | Scope |
| --- | --- | --- |
| Manual-fallback and operator fixes in Chromium | `software/.venv/bin/python tools/browser_fallback_checks.py` | Fallback page, stale overlay, replay rejection, disable-after-slow-enable ordering, lock to neutral, click-to-pick, closed-page lease; synthetic/mock |
| Simulator smoke | `software/.venv/bin/python tools/simulation_smoke.py` | Three maps, fixed-step flight, power/camera/pause, telemetry as text, failed-level recovery, offline |
| Simulator physics | `cd simulation && node --import ./tools/test/register.mjs tools/test/physics_test.mjs` | Asserted hover/wall/rest/sag/auto-land; exits 1 on failure |
| Pi installer in ARM64 containers | `tools/pi_container_check.sh debian:trixie-slim` (and `debian:bookworm-slim`) | Real installer with stubbed systemd; not a Pi |
| Mega code as AVR firmware | `tools/mega_avr_check.sh` | simavr ATmega2560 run plus Linux ASan + UBSan; no board |
| CAD kit | `cd cad/kit && .venv/bin/python -m pytest tests -q` | Parameter reading, measurement checks, test-piece meshes, opening probe, solid clash check, bend-jig assembly and beam predictions, mass report; main CAD files byte-identical |
| Solid clash check | `cd cad/kit && .venv/bin/python clash_check.py` | Exported hub meshes + rods vs prop volumes; balls pushed into all 40 openings |
| Simulated bend test | `cd cad/kit && .venv/bin/python bend_simulation.py` | Jig/rod/hook solid fit; predicted readings by beam theory |
| On the real Pi | `bash software/deploy/pi-acceptance.sh` | Service, groups, health, fallback, processing rate, temperature/throttling, devices; writes a report |

## Existing verification contract

| Software obligation | Existing checks |
| --- | --- |
| Bounded yaw and direct neutral | Controller reference trajectories, clamps/slew, loss/disable/fault |
| Fresh source/ACK deadlines | Injected timing, capture freeze/failure, missing/delayed/reordered ACK |
| Strict operator writes | Tokens on mutation routes, typed booleans/numbers, unknown/nonfinite input rejection |
| Native state/queue correctness | Complete response validation, queued neutral priority, stale clearing, close/switch behavior |
| Isolation and replay | Visitor/browser-local traces, complete import validation, CSV/JSONL round trips |
| Process lifecycle | Real local backend startup/shutdown/restart, port/token isolation and parent death |
| Serial/protocol | Actual PTY/pyserial, framing/oversize/replay/session checks |
| Portable C | Bounds, 32-bit parsing/timer behavior, sanitizer assertions and Python/C parity |
| Verifier integrity | Failure/skip/timeout/missing report/source-change handling and preserved outputs |

Large matrices include all 2,001 permitted integer yaw values, all 180 OpenCV hues, all 120 orders of five ACKs and all 32 five-request assistance sequences, plus seeded reference/state operations. Enumerated domains are bounded; their coverage does not prove arbitrary inputs or hardware behavior. Iterations within a test are not additional pytest test counts.

The [earlier detailed guide](sources/local-docs-before-rework-2026-10-07/15-verification.md) preserves test-file mappings and implementation-specific instrumentation details.

## Evidence and gates

Each run records environment/dependency/compiler versions, exact commands, JUnit, assertion output, statement/branch coverage, portable C output and source hashes before/after. `SHA256SUMS.json` records output integrity.

Default combined statement/branch coverage floor: **95%**.

| Module group | Gate |
| --- | --- |
| Controller, detector, camera/source | 100% |
| Protocol, engine, bridge, API, desktop and desktop backend | 95% |
| Serial emulator | 90% |
| Calibration, navigation contracts/localization/guard/planner/runtime/replay/fixtures and D435 mapping | 95% per module |

Selected failures/skips, missing dependencies/compiler/reports, source changes or missed gates fail the run. Preserve uncovered paths rather than excluding them to inflate coverage.

Mac verification defaults to UBSan; a historical ASan startup attempt stalled and is retained. Linux ARM64 used ASan + UBSan. Coverage startup handles the recorded Mac UF_HIDDEN metadata issue and selects current source for child processes; reports identify when the workaround was used.

## Current navigation results — 2026-10-08

Mac ARM64/Python 3.13.12: **4,380 desktop tests pass, 98.15% combined coverage**; **3,997 headless tests pass, 99.13% combined coverage**. Both have zero failures/errors/skips and the same unchanged tested-source manifest. All module gates, portable C/Mega framing UBSan and internal-only Mega compile pass. [Reports and source hashes](../evidence/verification/README.md) · [Replay, map and browser evidence](../evidence/navigation/README.md).

Replay, autonomous example and reconstructed synthetic depth-map autonomous runs each produced byte-identical reruns. Synthetic goal completion, tag loss/restore, auth/isolation and desktop/phone Chromium layout pass. No Pi, real D435, actual FPV or aircraft result is claimed; the earlier failed latency-coverage development run remains preserved.

## Backend mission/status extension — 2026-10-09

The current source passed fresh verification after adding strict high-level mission commands, authenticated result lookup, bounded request reconciliation, explicit subsystem/capability status, target-tag loss/reacquisition handling, and the Mega no-output boundary.

| Profile | Tests | Combined statement/branch coverage | Module results | Evidence |
| --- | --- | --- | --- | --- |
| Linux x86-64 core, UBSan | **4,175 passed**, 0 failures/errors/skips | **98.51%** | `engine.py` 99.40%; `mission_control.py` 100%; all configured floors pass | [Report](../evidence/verification/20261009-mission-status-core-05/report.json), [pytest](../evidence/verification/20261009-mission-status-core-05/pytest.txt) |
| Linux x86-64 Qt desktop, UBSan | **4,560 passed**, 0 failures/errors/skips | **97.98%** | `engine.py` 99.40%; `mission_control.py` 100%; all configured floors pass | [Report](../evidence/verification/20261009-mission-status-desktop-01/report.json), [pytest](../evidence/verification/20261009-mission-status-desktop-01/pytest.txt) |

Both final reports record unchanged tested-source fingerprints, portable firmware UBSan checks and Mega line-framing UBSan checks. The shared source hash is `facd5b4f3329549072d9c631777008201c74c6d97d0aefe3abc5ca49e31f72e1`. The [direct sanitizer record](../evidence/verification/20261009-mission-status-direct-sanitizers/README.md) preserves a clean ASan/UBSan run of the portable C core and the line-reader runtime behavior. A default full-profile ASan invocation intermittently exited `-11` without a diagnostic; the complete UBSan profiles and direct sanitized C checks passed. Keep that failed run in [core-04](../evidence/verification/20261009-mission-status-core-04/report.json), rather than treating the sanitizer failure as a product result.

The Mega sketch now reports only `NO_OUTPUT`; the host rejects `PPM_YAW`. Arduino compilation was not run because `arduino-cli` is unavailable. These results are software/container evidence; no Pi, RealSense, transmitter, receiver or aircraft behavior is confirmed.

## Portable visual missions backend — 2026-10-09

The focused portable suite passes **92 tests**, zero failures, with one Starlette/httpx deprecation warning. It exercises strict roster/tag records, shared AprilTag detection, generated relative person/pad poses, timing provenance, loss/reacquisition, mock mission cancellation/landing, simulated controller limits, the Python API adapter and physical-output isolation.

The first full Linux x86-64 core attempt is preserved at [`20261009-portable-missions-core-01`](../evidence/verification/20261009-portable-missions-core-01/report.json). All **4,248 tests passed**, but the profile failed its aggregate coverage gate at **92.75%**; it also reported `sources.py` at 99.32% against its 100% floor and `mission_control.py` at 80.72% against its 95% floor. The portable firmware ASan/UBSan process exited `-11` without a diagnostic; the Mega line-framing sanitizer passed. Additional focused tests were added after that full run, so those coverage percentages do not describe the current tree. The full profile has not been rerun; do not treat this as a full-suite pass.

This is synthetic/container evidence only. No actual FPV camera, RC832, Pi, landing surface, transmitter, aircraft or flight behavior was tested. The D435 mapping code remains unchanged and is outside the current demo scope.

## Combined repositories / PR #1 — 2026-10-10

The integration retains the destination repository's final CAD/print delivery and the contributor repository's Flutter, portable missions, retained mapping code, firmware and evidence. Only `docs/README.md` and `docs/decisions.md` conflicted; both histories were retained.

- **Mac ARM64 desktop profile:** 4,665 tests passed with zero failures/errors/skips and **96.05%** combined statement/branch coverage. Every configured module floor passed. Portable firmware UBSan, Mega line-framing UBSan and the Arduino Mega sketch compile passed; source fingerprints remained unchanged. [Report](../evidence/verification/20261010-pr1-desktop-01/report.json).
- **CAD kit:** 45 tests passed using the existing CAD environment and complete export fixtures. [Report](../evidence/verification/20261010-pr1-cad-04/report.json). Earlier dependency/partial-checkout setup failures remain in the adjacent `20261010-pr1-cad`, `-02` and `-03` directories.
- **Preservation audit:** all 355 destination-only changed paths and 416 contributor-only changed paths match their originating Git objects exactly; `docs/15-verification.md` retains the contributor text with this new verification section; no tracked file from either branch is missing. [Integration report](../evidence/verification/20261010-pr1-integration/report.json).
- **Flutter:** its source is unchanged from the contributor branch, which retains the previously recorded Flutter checks. No Flutter SDK is available on this Mac, so Flutter builds and browser/Android inspection were not rerun. Python tests cover the merged backend API contract.

These are Mac/software, offscreen Qt, synthetic-device and CAD checks. They establish no live camera, ESP32-S3 integration, trainer output, physical fit or aircraft acceptance. Historical recorded failures and dated source snapshots remain intact.

## Navigation test obligations

| Requirement | Current regression evidence |
| --- | --- |
| Coordinate correctness | Seeded independent SE(3) chains, right-handed rigid transforms, optical/aircraft/tag axes and measured-size conventions |
| Image inference | Independent camera projections, Brown distortion, real bitmap AprilTag detection through engine worker, planar alternatives and multi-tag solve |
| Input rejection | Units/frames/version registration, duplicate IDs, booleans, NaN/Infinity, invalid transforms, corrupt images/recording/hash/path |
| Loss/staleness/recovery | Unknown exposure delay, jumps/ambiguity, ordering, consecutive reacquisition, sticky source faults, queued stop and stale snapshot rejection |
| Clearance | Full 3D swept cage/margins, unknown gaps, detours, stopping allowance, node/wall budgets and route expiry |
| Control isolation | Blocked planner with independently progressing yaw worker, rejected late results, concurrent bundle replacement without orphan workers |
| D435 repeatability | Saved synthetic depth, holes/occlusion, occupied precedence, exact voxel merging, registered multi-view reconstruction and fake SDK capture/cleanup/clock provenance |
| Integration | Every navigation mutation auth/type checks, JSONL round trip, CLI entry points, browser-local replay, native nested validation/stale clearing |

The fake SDK tests exercise contracts and cleanup only. They do not prove SDK installation, D435 accuracy or Pi timing. Each navigation module retains its coverage gate; no source branches were excluded to conceal gaps. Example maps/scans/calibration remain labeled synthetic.

Current run results and source hashes are linked in the [verification index](../evidence/verification/README.md); replay/map/browser artifacts are in the [navigation evidence index](../evidence/navigation/README.md). Reproduce the browser test on a host with the existing Playwright dependency/browser:

```sh
PYTHONPATH=software software/.venv/bin/python tools/navigation_checks.py --output evidence/navigation/browser-NEW-RUN
```

Use a new output path for every run. Ordinary tracking remains covered both without navigation and with the optional worker; no serial or trainer authority is added by these checks.

## Historical recorded results

[Reports from 2026-10-04](../evidence/verification/README.md):

| Scope | Results | Combined coverage |
| --- | --- | --- |
| Mac ARM64 desktop | 4,059 passed, no failures/errors/skips | 99.58% |
| Linux ARM64 container desktop | 4,059 passed, no failures/errors/skips | 99.63% |
| Mac core, UI excluded | 3,697 passed | 99.50% |

Those full runs share source manifest `4e2b485055f7c94c9c8ada3675e69b79a495be885df6056d6f0a0a5835cd2386`. Later UI changes need their own checks; the old run does not establish current-source success. Earlier 350/260/146-test passes and failed development attempts remain recorded.

A six-second packaged-app smoke and the earlier 30-minute browser rehearsal are separate scopes. Neither is native endurance, Pi performance or flight acceptance.

For Linux ARM64 reproduction, use the prepared Dockerfiles and the exact [recorded mount/run script](../evidence/verification/arm64-command.sh). A container does not supply Pi capture/display/radio hardware.

## Physical checks required by the current plan

| Requirement | Evidence needed |
| --- | --- |
| Manual aircraft and pilot authority | Actual Betaflight/ELRS/manual/ARM-DISARM/failsafe checks |
| Manual fallback display | Actual live FPV, target box, center/error and unavailable-steering status |
| Mega assistance path | Actual electrical waveform, trainer/channel encoding and full radio/FC behavior |
| Assisted override | 20/20 props-off then 5/5 airborne |
| Target/communication loss | Actual neutral/failsafe outcomes on every check |
| Tracking | No sustained oscillation; clamps/slew active; measured complete latency |
| P1B flight gate (no fixed cage built) | Ten consecutive undamaged/no-prop-strike contacts, ≥3 min usable flight, repeatable recovery |
| Judge readiness | At least three consecutive complete rehearsals of the chosen route |

Use the manual-contact/live-tracking route if the physical assistance gates are unverified. Simulation is illustrative; its geometry matching is not required and its telemetry is not aircraft evidence.

Remote client loss remains a known lease gap; use independent physical takeover/failsafes before any assisted route. Pico/audio and `toImplement` are deferred.

[Build/test](10-build-and-test.md) · [Arrival records](13-hardware-arrival.md) · [Demo routes](12-demo-runbook.md).


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Verification report index](../evidence/verification/README.md) — Run dates, hashes, environments, coverage and limits.
- [Evidence index](../evidence/README.md) — Links to software and desktop artifacts.
- [Verifier implementation](../tools/verify.py) — Commands implemented by the local verification runner.

## Hardware-free completion — 2026-10-10

[Completion record](28-hardware-free-completion.md) maps the implemented portable path, selected ESP32-S3 no-output sketch, real HTTP/client rehearsals and build evidence to requirements. The verifier now enforces per-module floors for roster, relative pose, UI API, connected runtime, generated scene and pure follow/landing simulation, alongside the existing overall 95% branch/statement gate. It fingerprints Flutter source and CI definitions as well as Python/browser/firmware sources.

Use `--require-esp32` with the official pinned Espressif core to require the selected ESP32-S3 build; an absent toolchain is never counted as a compile pass. Project firmware warnings fail the check. The ESP32 sketch itself also runs under a UART-only host stub with UBSan. Its shared parser/framer copies must match the authoritative C source byte for byte. `tools/portable_checks.py` runs three complete HTTP rehearsals with physical-output isolation and can include the actual Dart REST gateway and both layout sizes. Every output path must be new; failed development reports are retained.

CI installs the locked Python dependencies and official board cores, repeats desktop/protocol/rehearsal checks, tests the real Python/Flutter contract, and builds operational/preview web, Android and Mac artifacts. Runtime credentials remain in ignored private storage; the deterministic rehearsal token is test-only. Device, network, FPV and flight behavior remain unverified by these software runs.

### Current completion evidence — 2026-10-10

The first passing full desktop run is [`20261010-hardware-free-desktop-final-01`](../evidence/verification/20261010-hardware-free-desktop-final-01/report.json): 4,713 tests, 95.99% branch/statement coverage, module floors, C/line-reader UBSan, Mega build and unchanged-source verification. The real Dart REST client and Flutter renderer passed against three separate HTTP mission rehearsals in [`20261010-portable-flutter-development-02`](../evidence/verification/20261010-portable-flutter-development-02/report.json); 79 existing Flutter tests passed. [`20261010-hardware-free-flutter-final-01`](../evidence/verification/20261010-hardware-free-flutter-final-01/report.json) records the complete final Flutter build profile; final mobile/macOS build results are recorded there. Intermediate failures and repairs are kept in their own timestamped directories. The release-build runs are still underway as this record is written.
