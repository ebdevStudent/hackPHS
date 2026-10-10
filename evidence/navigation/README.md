# Navigation evidence — 2026-10-08

The later integrated [GitHub publication check](../verification/github-publish-mac-2026-10-08/report.json) passes **4,395 desktop tests / 98.15%** with zero failures/errors/skips. It includes the latest project/test-tool changes; the navigation-only completion and replay artifacts below retain their original manifests.

Current scope: **Mac ARM64 software/offscreen Qt/Chromium, synthetic observation and depth inputs, fake SDK**. No Pi, D435 device, video receiver, radio or aircraft was tested. Invented fixtures are labeled; no completed real room map/calibration/survey is claimed. [Runbook](../../docs/23-navigation-software.md) · [Verification](../../docs/15-verification.md).

| Result | Evidence | Limit |
| --- | --- | --- |
| Desktop verification: **4,380 passed**, 0 failures/errors/skips, **98.15%** combined coverage | [Report](../verification/mac-navigation-complete-2026-10-08/report.json), [assertions/coverage](../verification/mac-navigation-complete-2026-10-08/pytest.txt) | Offscreen Qt, synthetic/fake-device/PTY; no packaged-app/endurance/hardware claim |
| Headless verification: **3,997 passed**, 0 failures/errors/skips, **99.13%** combined coverage | [Report](../verification/mac-navigation-core-2026-10-08/report.json) | GUI tests/coverage explicitly excluded; no silently skipped checks |
| Real-browser navigation smoke | [Report](browser-complete-2026-10-08/report.json), [route](browser-complete-2026-10-08/route.png), [desktop](browser-complete-2026-10-08/desktop.png), [phone](browser-complete-2026-10-08/phone.png) | Local authenticated mock backend; read-only local replay; no Pi/browser endurance |
| Deterministic observation replay and autonomous mock routes | [Results/commands](software-final-2026-10-08/report.json), [replay](software-final-2026-10-08/replay-1.json), [example autonomous demo](software-final-2026-10-08/autonomous-example-1.json) | Twice byte-identical; 14 replay inputs; mock goal reached in 93 samples, 0.04604 m final plant error; synthetic vision/camera/geometry only |
| Reconstructed depth → cleared mock route | [Synthetic depth manifest](software-final-2026-10-08/synthetic-depth-scan.json), [map](software-final-2026-10-08/map-rebuild-1/map.json), [autonomous depth-map demo](software-final-2026-10-08/autonomous-depth-map-1.json) | Invented pinhole depth plane; 57 mock samples, goal reached with 0.04003 m plant error; no depth-device or dynamics accuracy claim |
| Repeatable reconstruction | [First report](software-final-2026-10-08/map-rebuild-1/report.json), [second map](software-final-2026-10-08/map-rebuild-2/map.json), [checksums](software-final-2026-10-08/SHA256SUMS.json) | Same saved synthetic data: identical maps; 556 free/100 occupied/844 unknown voxels; source bundle unchanged |

The full suite includes **178 navigation/mapping/latency-stimulus cases** (parameterized pytest cases, not iterations inside tests). They cover independent transforms and camera projections, actual generated AprilTag bitmap detection through the engine, strict registration/units/finite values, ambiguity/outliers, freshness/loss/reacquisition, planner stalls/control isolation, continuous cage clearance through a union of adjacent free boxes, unknown gaps, auth/import/record/replay, CLI/native/browser integration, and fake-SDK clock/format/cleanup handling.

Desktop and core share tested-source manifest **`cb6494447105b8172316f82edfabc5ceafa92c041709afd4b351471d48de57b9`**, unchanged during each run. Controller/detector/source/video-health/color-pick remain at 100%; every added navigation module meets its 95% gate. Portable C and Mega line-framing UBSan checks and the existing internal-state-only Mega sketch compile pass; no firmware was flashed and no pins/trainer output were enabled. The completion audit verifies current source against those manifests.

## Reproduce the saved software demonstrations

```sh
cd /Users/devk/Documents/HackPHS26/software
.venv/bin/python -m ball_demo.cli nav-replay examples/navigation/synthetic-session.json --output runs/navigation-replay.json
.venv/bin/python -m ball_demo.cli nav-demo examples/navigation/synthetic-session.json --output runs/navigation-demo.json
.venv/bin/python -m ball_demo.cli nav-simulate --bundle ../evidence/navigation/software-final-2026-10-08/synthetic-depth-bundle.json --start 1 0.9 1 --goal 1 1.4 1 --yaw-deg 90 --output runs/navigation-depth-demo.json
.venv/bin/python -m ball_demo.cli serve --nav-replay examples/navigation/synthetic-session.json
```

Open `http://127.0.0.1:8080/`, then use **Inspect navigation replay** to load an export. Playback stays local and makes no shared mutation; backend yaw stays MANUAL/disabled/zero. The synthetic depth fixture was generated from the independent mapper test's plane/camera transform, using deliberately wide invented intrinsics. Its manifest and NPZ are preserved so CLI reconstruction requires no device.

```sh
.venv/bin/python -m ball_demo.cli nav-map ../evidence/navigation/software-final-2026-10-08/synthetic-depth-scan.json --output runs/navigation-map-rebuilt
```

Fresh physical captures may differ; deterministic hashes concern repeated reconstruction of the same saved inputs/settings. Real station registration, tag survey, calibration and error characterization are required before importing hardware artifacts.

## History and unfinished hardware gates

Preserve [failed development verification](../verification/mac-navigation-development-2026-10-08/report.json): 4,359 tests passed, but latency coverage missed its 90% gate. A headless Qt stimulus contract plus actual offscreen flash test closed that gap; no coverage threshold/exclusion was relaxed. Earlier passing navigation runs ([first full](../verification/mac-navigation-2026-10-08/report.json), [capture/timing](../verification/mac-navigation-final-2026-10-08/report.json), [import audit](../verification/mac-navigation-audit-2026-10-08/report.json)) and [development browser](browser-development-2026-10-08/report.json)/[layout browser](browser-final-2026-10-08/report.json) describe their earlier source manifests.

**Pi/D435 results: not performed. Physical results: not performed.** Pending: actual Python/SDK/USB capture installation, measured host/exposure delay, FPV calibration/mount, full tag/station survey, small-corner map coverage, Pi load/thermal/FPS/error tests, FC/radio/trainer waveform/channel/override/loss verification. Translation/height require a separately established authority change and verified sensing/stopping/output. Existing fixed-cage/manual gates, budget/freeze and deferred audio/toImplement remain intact. [Smallest next real experiment](../../docs/23-navigation-software.md#smallest-next-real-experiment-and-remaining-gates).
