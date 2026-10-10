# Pre-hardware software preparation status

Updated 2026-10-04. This is the implementation record for the user's 64-step preparation plan. Source Google Doc tabs remain separate; this supplemental record does not replace them.

## Scope and roles

Additional user-directed work: [native desktop workstation for Mac and Pi](14-desktop-app.md), with [its own evidence](../../../evidence/desktop/README.md). The earlier stage/test results below are not a native GUI endurance check.

Latest verification: **4,059 tests pass on Mac and Linux ARM64**, with zero skipped tests and matching tested source manifests. Combined statement/branch coverage is 99.58% / 99.63%; controller/detector/source code coverage is 100%. Expanded API, native Qt, process-lifecycle, virtual serial, fake-camera and verification-runner checks are documented in the [verification guide](15-verification.md) and [saved results](../../../evidence/verification/README.md). Portable C assertions pass UBSan on Mac and ASan + UBSan on Linux. The rebuilt Mac app passes signature and short offscreen startup/shutdown checks. These checks do not replace actual Pi/device testing or native endurance measurement. The preceding 350-, 260- and 146-test passes are preserved separately. The latest pass adds 3,709 cases: exhaustive yaw/session-byte/ACK-order domains, vision/color/geometry matrices, reference controller trajectories, strict API types, desktop queue/validation cases, log round trips and injected-clock deadlines. The core profile passes 3,697 tests with 99.50% combined coverage.

Pi 5: processing, bounded yaw calculations and browser server. Mac: development/rehearsal and independent 3D simulation. Visitors: read shared status and use browser-local sandbox playback. Provisional Pico/RP2040: portable C core and compiled USB scaffold, no trainer output. Both hotspot and shared-network profiles are prepared. CAD remains deferred.

## Ordered stage handoff

| Stage / plan steps | Delivered artifacts and behavior | Evidence / limit |
| --- | --- | --- |
| A / 1–7 | Current docs, Python 3.13 venv and locked dependencies, pyserial/Playwright, Pico SDK/toolchain, CLI commands, ignored runtime storage, Mac simulation smoke. | [Fresh install](../../../evidence/fresh-install.txt), [simulation smoke](../../../evidence/simulation-smoke.json), [versions](../../../evidence/firmware/toolchain.txt). |
| B / 8–15 | 17 deterministic scene types, motion/difficult detection/loss/timing faults, ground truth CSV+JSON, AVI fixtures, recorded adapter with normal EOF, sample-recording guide. | [Fixture report](../../../evidence/fixtures.json); regenerate files using `fixtures`; actual camera pending. |
| C / 16–26 | HSV/morphology/blob rejection, continuity selection, normalized error/quality heuristic, four states, acquisition/loss, proportional smoothing/deadband/clamp/slew, direct neutral, independent freshness checks, software response model. | [Python checks](../../../evidence/python-tests.txt), [fixture accuracy](../../../evidence/fixtures.json). Software defaults are not tuned flight gains. |
| D / 27–35 | [Protocol spec](../../../firmware/PROTOCOL.md), mock transport, PTY peer+real pyserial tests, injected faults, portable C tests, Pico SDK USB CDC scaffold and UF2/ELF. | [C host tests](../../../evidence/firmware-host-tests.txt), [Pico build](../../../evidence/pico-build.txt). Compiled, not flashed/electrically verified. |
| E / 36–44 | Responsive local dashboard, source badges, operator token/settings/actions, shared cached JPEG/latest-only delivery, isolated trace sandbox, replay import, stale/reconnect display. | [Browser report](../../../evidence/browser-checks.json), [desktop](../../../evidence/dashboard-desktop.png), [phone](../../../evidence/dashboard-phone.png). |
| F / 45–50 | Config/version/environment, sample CSV, event JSONL and summary, mock-only replay export/import, named scenarios, recorded walkthrough and demo script. | [Sample session](../../../evidence/demonstration-session/summary.json), [replay](../../../evidence/demonstration-replay.json), [walkthrough](../../../evidence/walkthrough.webm), [runbook](12-demo-runbook.md). |
| G / 51–59 | Headless Pi installer, explicit 64-bit/Python profile, ARM64 Docker check, systemd startup, port 8080, NetworkManager hotspot/shared switching, active-IP card generator, local assets and Mac multi-viewer rehearsal. | [ARM64 output](../../../evidence/arm64-smoke.txt); [rehearsal status](../../../evidence/README.md). Actual Pi installation/AP/USB/throughput remain pending. |
| H / 60–64 | Startup/recovery/demo checklists, [arrival worksheet](13-hardware-arrival.md), separate current tab docs and decision log. | Optional read-only simulation linking remains deferred P4; standalone demo needs no link. |

## Acceptance coverage

| Pre-hardware acceptance | Recorded status |
| --- | --- |
| Fresh environment / documented commands | Runtime locked install, bridge and actual API/vision/logging smoke in a new Mac venv; ARM64 image independently installs the package. |
| Synthetic and recorded input | Tested scene library and OpenCV AVI EOF path. |
| Clear target ≤5 px ground-truth error | Passed; see per-scene fixture report. Difficult occlusion/distraction scenes are reported separately. |
| Bounds / disabled/lost/fault zero | Passed Python and C checks. Neutral bypasses slew. |
| Frozen input / missing ACK timeout | Passed live engine tests and visible browser checks. Deadline observed at next 20 Hz tick; no hard real-time claim. |
| Invalid/duplicate messages do not refresh watchdog | Passed C tests and Python protocol tests; PTY exercises host serial framing/partial/invalid replies. |
| Restart/reconnect require deliberate enable | Passed browser stream disconnect/restart and controller/recovery tests. |
| C core pass / Pico compile | Passed. Trainer output absent; not flashed. |
| Operator + five viewers for 30 minutes | [Passed 1800.16 seconds](../../../evidence/mac-rehearsal.json), six Chromium contexts, zero recorded responsiveness failures. Three injected ACK faults and one unplanned stale frame neutralized correctly; actual session processing 18.62 FPS. Mac baseline/load scope. |
| Sandbox isolation | Passed API/browser/rehearsal checks; playback has no operator mutation call. |
| Logs reproduce sequence without serial | Replay export check passed; saved demonstration session/replay available. |
| Local assets without event internet | Passed browser check with external requests denied. Mac network configuration was not changed. |
| Linux ARM64 installation/synthetic/API/logging | Passed in a Colima ARM64 container; not a Pi/device performance test. |
| Startup guide, recording, report, worksheet | Delivered locally, with actual environment labels. |

## Remaining hardware dependencies and next integration step

When equipment arrives, install the synthetic/mock package on the Pi first and record throughput, thermals and real browser/network behavior. Then verify receiver capture and Pico USB. Confirm the exact transmitter interface before adding any trainer output. Follow [hardware worksheet](13-hardware-arrival.md) and the separate [physical readiness gates](10-build-and-test.md).

No recorded software result establishes cage mechanics, measured flight/contact behavior, end-to-end radio latency, pilot physical override or flight-ready controller gains.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Pre-rewrite archive index](README.md) — identifies this file as historical context, not current instruction.
- [Maintained document](../../11-pre-hardware-status.md) — current requirements and status.
- This citation note is external to the preserved pre-rewrite text.
