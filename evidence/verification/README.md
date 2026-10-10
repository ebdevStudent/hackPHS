# Automated verification — 2026-10-04

## Backend mission/status extension — current Linux source, 2026-10-09

| Profile | Results | Combined coverage | Evidence |
| --- | --- | --- | --- |
| Core, UBSan | 4,175 passed; 0 failures/errors/skips | 98.51% | [Report](20261009-mission-status-core-05/report.json) · [pytest](20261009-mission-status-core-05/pytest.txt) |
| Qt desktop, UBSan | 4,560 passed; 0 failures/errors/skips | 97.98% | [Report](20261009-mission-status-desktop-01/report.json) · [pytest](20261009-mission-status-desktop-01/pytest.txt) |

Both reports use source hash `facd5b4f3329549072d9c631777008201c74c6d97d0aefe3abc5ca49e31f72e1`, pass every configured module floor (`engine.py` 99.40%, `mission_control.py` 100%), and pass the portable firmware and Mega line-framing UBSan checks. An intermittent default ASan process exit is preserved in [core-04](20261009-mission-status-core-04/report.json); the exact portable C sanitizer command was rebuilt and passed directly. See the [direct sanitizer record](20261009-mission-status-direct-sanitizers/README.md). The Mega sketch is internal-state-only; no Arduino compile was run because `arduino-cli` is unavailable. No physical device or aircraft behavior is implied.

## Current source — 2026-10-08 (fallback, lease, camera, Mega and audit fixes)

[Report](20261008T211848Z/report.json) · [JUnit](20261008T211848Z/junit.xml) · [assertions/coverage](20261008T211848Z/pytest.txt) · [Mega compile](20261008T211848Z/mega-compile.txt) · [line-reader C](20261008T211848Z/firmware-line-reader.txt). 4,405 tests (adds the Pi acceptance tests). Earlier passes [20261008T210658Z](20261008T210658Z/report.json) and [20261008T203158Z](20261008T203158Z/report.json) had 4,398.

- **Result:** 4,398 tests passed, with zero failures, errors or skips.
- **Coverage:** 98.15 % combined (98.93 % statements, 95.46 % branches). Every module gate passed, including `video_health.py`, `color_pick.py`, `latency.py` and `session.py` at 100 %, `engine.py` at 99.5 % and `desktop.py` at 95.76 %.
- **Firmware:** the C core and the Mega line reader pass under UBSan, and the Arduino Mega 2560 sketch compiles with no warnings in project files.
- **Fingerprint:** the source fingerprint, which now includes browser assets and deploy scripts, was unchanged during the run.

The earlier run [20261008T203005Z](20261008T203005Z/report.json) is kept as a failure. Its tests and gates all passed, but `tools/sync_to_repo.sh` was created while it ran, so the unchanged-source check correctly failed.

## GitHub publication snapshot — 2026-10-08

The integrated publishing checkout passed **4,395 desktop tests**, zero failures/errors/skips, **98.15%** combined statement/branch coverage, all configured module gates, UBSan and internal-state-only Mega compilation. [Publication report](github-publish-mac-2026-10-08/report.json) · [JUnit](github-publish-mac-2026-10-08/junit.xml) · [Assertions/coverage](github-publish-mac-2026-10-08/pytest.txt).

This snapshot includes the latest project/test-tool changes as well as navigation; tested-source manifest **`b5ff78968c08a1c77d7b2a09df4bf249d5794b227afc246571a709ffc622ad6e`** remained unchanged during verification. Simulator Node physics assertions also pass. This is Mac/offscreen/fake-device software evidence; no Pi/D435 device or aircraft acceptance is implied. Earlier navigation results below retain their original source hashes.

## Navigation implementation — current Mac source, 2026-10-08

| Profile | Passed / failures / errors / skips | Combined statement/branch coverage | Evidence |
| --- | --- | --- | --- |
| Mac ARM64 desktop, offscreen Qt | **4,380 / 0 / 0 / 0** | **98.15%** | [Report](mac-navigation-complete-2026-10-08/report.json), [pytest](mac-navigation-complete-2026-10-08/pytest.txt), [JUnit](mac-navigation-complete-2026-10-08/junit.xml) |
| Mac ARM64 core, GUI explicitly excluded | **3,997 / 0 / 0 / 0** | **99.13%** | [Report](mac-navigation-core-2026-10-08/report.json), [pytest](mac-navigation-core-2026-10-08/pytest.txt) |

Both use Python 3.13.12/OpenCV 5.0.0.93 and tested-source SHA256 **`cb6494447105b8172316f82edfabc5ceafa92c041709afd4b351471d48de57b9`**. All configured module gates, portable C UBSan, Mega line-framing UBSan, internal-only Mega compile and unchanged-source checks pass. No source coverage exclusions were added. Added navigation modules each retain a 95% gate. No Pi, D435 device, trainer waveform, physical output, packaged-app rebuild or endurance test is implied.

The [navigation evidence index](../navigation/README.md) covers browser, deterministic replay and repeatable synthetic depth-map → mock autonomous goal artifacts. The [failed development run](mac-navigation-development-2026-10-08/report.json) remains: 4,359 tests passed but latency.py coverage was 80.597%, below its 90% gate. Headless stimulus and actual offscreen flash checks repaired the coverage gap. Earlier passing [first full](mac-navigation-2026-10-08/report.json), [capture/timing](mac-navigation-final-2026-10-08/report.json) and [import audit](mac-navigation-audit-2026-10-08/report.json) runs describe their own source, before the final free-box-union clearance change. Do not substitute them for the final manifests.


Latest desktop runs tested identical source manifest `4e2b485055f7c94c9c8ada3675e69b79a495be885df6056d6f0a0a5835cd2386`. Both passed with **4,059 tests, zero failures/errors/skips**. This adds **3,709 parameterized regression cases** to the previous 350-test pass. Synthetic, local-process, PTY, fake-device and offscreen Qt checks only; no physical devices.

## Current results

| Environment | Python tests | Combined statement/branch coverage | Portable C core | Evidence |
| --- | --- | --- | --- | --- |
| Mac ARM64, macOS 26.6.2, Python 3.13.12 | 4,059 passed | 99.58% | UBSan passed | [Report](mac-matrix-2026-10-04/report.json), [assertions](mac-matrix-2026-10-04/pytest.txt), [coverage](mac-matrix-2026-10-04/coverage-html/index.html), [C output](mac-matrix-2026-10-04/firmware.txt) |
| Linux ARM64 Colima/Docker, Python 3.13.16 | 4,059 passed | 99.63% | ASan + UBSan passed | [Report](linux-arm64-matrix-2026-10-04/report.json), [assertions](linux-arm64-matrix-2026-10-04/pytest.txt), [coverage](linux-arm64-matrix-2026-10-04/coverage-html/index.html), [C output](linux-arm64-matrix-2026-10-04/firmware.txt) |
| Mac core profile, Python 3.13.12; Qt UI tests/coverage excluded | 3,697 passed | 99.50% | UBSan passed | [Report](mac-core-matrix-2026-10-04/report.json), [assertions](mac-core-matrix-2026-10-04/pytest.txt), [coverage](mac-core-matrix-2026-10-04/coverage-html/index.html) |

Statement coverage: **99.94% Mac / 100% Linux**; branch coverage **98.25%** on both. Default combined coverage gate remains **95%** with module gates in the [guide](../../docs/15-verification.md). No exclusions were added. One desktop direct-run statement remains unrecorded on Mac and eight branch outcomes remain unrecorded in each full run; actual gaps stay in coverage reports. Coverage measures executed paths, not proof of correctness or hardware behavior.

### Added test families

| Test file | Added cases | What is asserted |
| --- | --- | --- |
| [Protocol exhaustive](../../software/tests/test_protocol_exhaustive.py) | 2,364 | All 2,001 permitted yaw values in Python and real compiled C, disabled/stale-state preservation; 192 invalid session bytes; 51 numeric spellings; all 120 permutations of five ACKs and replay rejection. |
| [Vision matrix](../../software/tests/test_vision_matrix.py) | 478 | All 180 OpenCV hue values, 80 scale/position/size combinations, 24 exact contour-area gates, 170 deterministic fixture/timestamp cases and 24 continuity-forgetting cases. |
| [Controller model](../../software/tests/test_control_model.py) | 272 | 192 reference trajectories across gain/smoothing/sign/acquisition/timing; 80 seeded 150-action sequences checked against an independent state-machine model. |
| [API matrix](../../software/tests/test_api_matrix.py) | 175 | Strict numeric/boolean request types, unknown fields, malformed JSON/body shapes, atomic rejection and 16 seeded 30-action mutation sequences. |
| [Desktop matrix](../../software/tests/test_desktop_matrix.py) | 220 | Nested schema/type/timing/label/state validation, required keys, trace domains and all 32 five-command assistance queue sequences. |
| [Engine deadlines](../../software/tests/test_engine_deadlines.py) | 150 | Source/ACK deadlines and fault priority at 249/250/251 ms on five clock origins, initially enabled or disabled; enable requests use the same thresholds. |
| [Session matrix](../../software/tests/test_session_matrix.py) | 50 | Deterministic CSV/JSONL/config/summary round trips, fault/sample/frame counts, ordered events, percentiles, disabled output and closed resources. |

Cases use explicit expected values or independent state/calculation models. Iterations within a case are not extra pytest counts. Exhaustive domains are limited to the stated values; arbitrary inputs, physical latency and flight behavior are not established.

New regressions exposed accepted coercible operator fields and silently ignored unknown fields. Request models now require correctly typed JSON and reject extra fields with 422. Existing native/browser clients send typed values. Controller smoothing now uses the weighted-average form, preserving the input exactly at smoothing 1.0 rather than moving inclusive deadband boundaries through subtraction cancellation. [Development output](matrix-development-2026-10-04/README.md) preserves failing assertions and passing corrections separately from these full reports.

## Previous 350-test verification baseline

| Environment | Python tests | Combined statement/branch coverage | Portable C core | Evidence |
| --- | --- | --- | --- | --- |
| Mac ARM64, macOS 26.6.2, Python 3.13.12 | 350 passed | 99.58% | UBSan passed | [Report](mac-robustness-2026-10-04/report.json), [assertions](mac-robustness-2026-10-04/pytest.txt), [coverage](mac-robustness-2026-10-04/coverage-html/index.html), [C output](mac-robustness-2026-10-04/firmware.txt) |
| Linux ARM64 Colima/Docker, Python 3.13.16 | 350 passed | 99.63% | ASan + UBSan passed | [Report](linux-arm64-robustness-2026-10-04/report.json), [assertions](linux-arm64-robustness-2026-10-04/pytest.txt), [coverage](linux-arm64-robustness-2026-10-04/coverage-html/index.html), [C output](linux-arm64-robustness-2026-10-04/firmware.txt) |
| Mac core profile, Python 3.13.12; Qt UI tests/coverage excluded | 208 passed | 99.41% | UBSan passed | [Report](mac-core-robustness-2026-10-04/report.json), [assertions](mac-core-robustness-2026-10-04/pytest.txt), [coverage](mac-core-robustness-2026-10-04/coverage-html/index.html) |

That pass added 90 tests, including 4,800 Python/C operations, ACK ordering, watchdog-boundary, desktop-response-validation and capture shutdown regressions. Its source manifest was `ae667464efdfae78fab03d4144c9c39f3b8a3f365d01222884d3702d2e2573ac`; historical evidence remains intact. Mac core coverage was 99.41%. It fixed older ACK overwrites, repeated READY refreshing ACK freshness, float watchdog-boundary rounding and malformed desktop responses.

## Previous 260-test verification baseline

| Environment | Python tests | Combined statement/branch coverage | Portable C core | Evidence |
| --- | --- | --- | --- | --- |
| Mac ARM64, macOS 26.6.2, Python 3.13.12 | 260 passed | 99.38% | UBSan passed | [Report](mac-gaps-closed-2026-10-04/report.json), [assertions](mac-gaps-closed-2026-10-04/pytest.txt), [coverage](mac-gaps-closed-2026-10-04/coverage-html/index.html), [C output](mac-gaps-closed-2026-10-04/firmware.txt) |
| Linux ARM64 Colima/Docker, Python 3.13.16 | 260 passed | 99.42% | ASan + UBSan passed | [Report](linux-arm64-gaps-closed-2026-10-04/report.json), [assertions](linux-arm64-gaps-closed-2026-10-04/pytest.txt), [coverage](linux-arm64-gaps-closed-2026-10-04/coverage-html/index.html), [C output](linux-arm64-gaps-closed-2026-10-04/firmware.txt) |
| Mac core profile, Python 3.13.12; Qt UI tests/coverage excluded | 158 passed | 98.91% | UBSan passed | [Report](mac-core-gaps-closed-2026-10-04/report.json), [assertions](mac-core-gaps-closed-2026-10-04/pytest.txt), [coverage](mac-core-gaps-closed-2026-10-04/coverage-html/index.html) |

The preceding pass added 114 tests and found late replaced-source errors and oversized serial suffix acceptance. Its statement coverage was 99.82% on both platforms; combined desktop coverage 99.78%. Historical results and manifests are preserved.

## Previous 146-test verification baseline

| Environment | Python tests | Combined statement/branch coverage | Portable C core | Evidence |
| --- | --- | --- | --- | --- |
| Mac ARM64, macOS 26.6.2, Python 3.13.12 | 146 passed | 82.13% | UBSan passed | [Report](mac-desktop-verified-2026-10-04/report.json), [assertions](mac-desktop-verified-2026-10-04/pytest.txt), [coverage](mac-desktop-verified-2026-10-04/coverage-html/index.html), [C output](mac-desktop-verified-2026-10-04/firmware.txt) |
| Linux ARM64 Colima/Docker, Python 3.13.16 | 146 passed | 84.81% | ASan + UBSan passed | [Report](linux-arm64-verified-2026-10-04/report.json), [assertions](linux-arm64-verified-2026-10-04/pytest.txt), [coverage](linux-arm64-verified-2026-10-04/coverage-html/index.html), [C output](linux-arm64-verified-2026-10-04/firmware.txt) |
| Mac core profile, Python 3.13.12; Qt UI tests/coverage excluded | 114 passed | 86.86% | UBSan passed | [Report](mac-core-verified-2026-10-04/report.json), [assertions](mac-core-verified-2026-10-04/pytest.txt), [coverage](mac-core-verified-2026-10-04/coverage-html/index.html) |

In that baseline, controller statement and branch coverage was **100%** on both platforms. Mac statement coverage alone was 84.43%, branch coverage 73.08%; Linux statement coverage was 86.87%, branch coverage 76.68%. The native UI module's combined coverage was 75.47%; Mac serial-emulator subprocess coverage was not captured despite passing functional PTY tests. The current pass addresses these gaps. Combined coverage counts executed statements and branch outcomes together; uncovered code is retained in both reports.

The suite includes 6,000 seeded randomized controller operations and the C corpus includes 10,000 seeded arbitrary byte frames. Those iterations are assertions inside tests, not additional pytest test counts. Portable host sanitizers do not prove Pico hardware behavior.

## How to reproduce and review

Follow the [verification guide](../../docs/15-verification.md). One command from the project root runs Python tests, coverage gates, C sanitizer assertions and unchanged-source checks:

```sh
software/.venv/bin/python tools/verify.py
```

The runner records exact commands, dependency/compiler versions, before/after source hashes and JUnit results. It fails on selected skipped tests, missed coverage gates or changed inputs. Self-tests check that these failure paths remain failures and that existing evidence cannot be overwritten. Each run includes a `SHA256SUMS.json` integrity manifest; hashes detect changes, not authorship.

For ARM64, [the mount/run script](arm64-command.sh) uses the same read-only source mounts as the recorded run and creates a new output directory. [Image build output](arm64-image-build.txt) records the verification dependencies. The script defaults to the existing `colima-ball-drone` Docker context; set `BALL_DOCKER_CONTEXT` for another ARM64 context.

## Rebuilt Mac application

The Apple Silicon app at `/Users/devk/Applications/Ball Drone.app` was rebuilt with the latest strict-request and smoothing/deadband fixes. Strict deep ad hoc signature verification passed. Its separate offscreen launch/preview/state/shutdown smoke recorded **97 frames and 0 faults**, with physical output false.

- [Build output](mac-matrix-app-2026-10-04/build.txt), [launch output](mac-matrix-app-2026-10-04/run.txt), [session summary](mac-matrix-app-2026-10-04/summary.json), [artifact/provenance](mac-matrix-app-2026-10-04/report.json), [render](mac-matrix-app-2026-10-04/render.png).
- Previous 350-test app: [artifact](mac-robustness-app-2026-10-04/report.json), [build](mac-robustness-app-2026-10-04/build.txt), [summary](mac-robustness-app-2026-10-04/summary.json). Its hash describes the replaced build.
- Previous 260-test app: [artifact](mac-gaps-app-2026-10-04/report.json), [build](mac-gaps-app-2026-10-04/build.txt), [summary](mac-gaps-app-2026-10-04/summary.json). Its hash describes the replaced build.
- Prior 146-test pass: [build](mac-app-build.txt), [launch](mac-app-run.txt), [summary](mac-app-summary.json), [artifact](mac-app.json), [render](mac-packaged-2026-10-04.png). Its recorded executable checksum describes the previous build, which has since been replaced in Applications.

The smoke is about six seconds, not a native endurance run. The signature is local ad hoc signing, not Apple notarization. No physical camera, serial device, Pi display or trainer connection was checked.

## Preserved earlier attempts

- [Initial Mac run](mac-desktop-2026-10-04/report.json): 137 Python tests passed; the overall run failed because ASan stalled during runtime initialization before C assertions. Mac defaults to UBSan; the failure remains recorded.
- [Earlier ARM64 run](linux-arm64-final-2026-10-04/report.json): 139 Python tests passed; the overall run failed at C linking because sanitizer runtime libraries were absent. The verification image now installs `libclang-rt-dev`; the latest run passes ASan + UBSan.
- [Earlier passing Mac desktop run](mac-desktop-final-2026-10-04/report.json): 139 tests before the seven verification-runner self-tests were added.
- [Earlier core-only Mac run](mac-core-2026-10-04/report.json): 107 tests, 86.86% combined coverage, before the verification-runner self-tests. It explicitly excludes Qt UI tests/coverage.
- [Intermediate gap pass](mac-gap-pass1-2026-10-04/report.json): 246 tests, 95.80% combined coverage, before current-source subprocess selection, emulator regressions and the higher gates.
- [Development regression assertions](gap-development-2026-10-04/README.md): preserved partial failures showing the old-source race and serial suffix acceptance, plus targeted corrections. These partial runs lack full source manifests and are not complete verification evidence.

- [Additional regression development](robustness-development-2026-10-04/README.md): protocol/ACK/watchdog and nested desktop validation failures before fixes, plus passing targeted checks. These partial runs lack full source manifests.

- [Matrix development assertions](matrix-development-2026-10-04/README.md): failures before strict API and smoothing corrections, plus passing targeted matrices. Partial results do not have full manifests.

Original browser, walkthrough and 30-minute browser rehearsal results remain in the [evidence index](../README.md). They are historical results for their stated interfaces and sources; this suite does not turn them into a native desktop endurance claim.

## Remaining verification

Actual Raspberry Pi installation/display, performance/thermals, networking, receiver capture, Pico USB, transmitter output, physical override and complete control latency remain pending. Remote operator disconnection is not a lease: a healthy remote backend can continue until disabled or faulted. Source-suite success and coverage do not establish aircraft behavior or flight readiness.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Verification guide](../../docs/15-verification.md) — Reproduction commands and coverage rules.
- [Verification source](../../tools/verify.py) — Current runner implementation; historic runs preserve their original source hashes.
- [Evidence index](../README.md) — Related hardware-free results.
