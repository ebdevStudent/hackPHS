# Ball Drone decision log

Append dated entries with the decision, basis, affected docs, and evidence. Record changes to the current design in the relevant doc as well.

## 2026-10-04 — Initialize the Ball Drone workspace

**Decision:** Use this folder for the HackPHS 2026 Ball Drone idea and its current documentation.

**Basis:** User instruction on 2026-10-04 and the [project Google Doc](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit). A [dated tab snapshots](../google-doc-2026-10-04/README.md) records the source.

**Current scope:** 85 mm quad; lightweight protective cage; fixed-cage P1A first; removable gimbal P1B after that; yaw-only V1 computer assistance; pilot throttle, roll, pitch, ARM/DISARM, and physical override. Pitch assistance, inspection tags, and minimal state sync remain later stages.

**Status:** Planning baseline. No hardware selection, CAD fit, or test outcome is verified by this entry.

**Affected files:** Project README, AGENTS instructions, current docs, CAD workspace README, and source snapshot.

## 2026-10-04 — Import the simulation repository

**Decision:** Put the user-supplied [WasimVorvoi/HackPHS repository](https://github.com/WasimVorvoi/HackPHS) inside the project at `simulation/` as an independent Git clone.

**Basis:** User instruction on 2026-10-04. The checkout is branch `main`, commit `f472e4fcf0ed1e19141bcfb42f1afa4ac302e7e3`, with origin `https://github.com/WasimVorvoi/HackPHS.git`.

**Status:** Source checkout verified. No dependencies installed, application launched, or runtime tests performed during this import. Source code and repository history were preserved.

**Affected files:** `simulation/`, root README and AGENTS instructions, documentation index, and software/simulation guidance.

## 2026-10-04 — Assign Mac and Raspberry Pi demo roles

**Decision:** Run the simulation on the user's Mac. Use the Raspberry Pi to host the demo server and browser interface so compatible devices can connect over the demo network.

**Basis:** User instruction on 2026-10-04 specifying the Mac for simulation and the Raspberry Pi as a demo server that devices can connect to.

**Status:** Confirmed deployment requirement. Pi model, network configuration, server startup, and client connectivity remain unimplemented and unverified. The location of future live vision and RC bridge processes is not established by this hosting decision.

**Affected files:** Root README and AGENTS instructions, documentation index, and the demo deployment section of the software/simulation doc.

## 2026-10-04 — Organize documentation by Google Doc tab

**Decision:** Give each of the nine Google Doc tabs its own maintained Markdown file: Idea, BOM, CAD, Software, Hardware, Simulation, refs, future, and Further Improvement / Feedback. Keep the build/test checklist and decision log as supplemental project files.

**Basis:** User request to split every tab into a separate file, explicitly separating Software from Simulation. Tab titles and IDs were confirmed through the Google Docs connector.

**Source preservation:** Split the dated text snapshot into nine files under `docs/../google-doc-2026-10-04/`. Each preserved tab body was checked against the original combined snapshot before that file was removed. Source wording and the source revision were retained.

**Current requirements:** The user's Mac runs the simulation. The Raspberry Pi hosts the demo server for browser clients. Yaw-only V1 assistance, pilot authority, provisional targets, and unverified runtime/physical status remain in the relevant current docs.

**Affected files:** Maintained docs and navigation, source snapshots, root README and AGENTS instructions, and CAD workspace navigation.

## 2026-10-04 — Implement the pre-hardware software demonstration

**Decision:** Raspberry Pi 5 runs tracking, yaw calculations and the offline demo server on port 8080. The Mac develops/rehearses software and runs the separate port-8765 simulation. Prepare both BallDrone-Demo hotspot and shared-network profiles, an isolated visitor playback sandbox, and provisional RP2040/Pico firmware. CAD stays deferred.

**Basis:** User's explicit 64-step implementation plan, including all numerical software defaults and requested acceptance checks. This refines the earlier server-only Pi assignment; preserved source tabs and earlier entries remain historical evidence.

**Implementation:** `software/` contains capture/detection/control/bridge/logging/API/local frontend, deterministic fixtures, recorded/camera adapters and deployment package. `firmware/` contains the ASCII protocol, portable C core and USB scaffold without trainer output. [Preparation status](11-pre-hardware-status.md), [runbook](12-demo-runbook.md) and [hardware worksheet](13-hardware-arrival.md) map the handoff.

**Recorded checks:** [Python, C, browser, fresh installation, Pico compile, Linux ARM64 and Mac simulation evidence](../../../evidence/README.md). The [long Mac rehearsal](../../../evidence/mac-rehearsal.json) passed 1800.16 seconds with one operator/five viewers and zero failures. It exercised the initial runnable baseline; final edge-case guards were separately checked through the final unit/browser/fresh/ARM64 runs. Physical device, electrical, radio and flight behavior remain pending.

**Corrections made during implementation:** Module/installation entry paths were corrected and checked in a fresh venv. A recovered mock bridge initially raced the host freshness deadline; recovery now obtains a genuine neutral ACK and stays disabled. Delayed ACKs are rejected by age. Pico integer parsing now rejects overflow explicitly on a 32-bit target. Browser reconnection is checked through a real server disconnect because the browser automation offline toggle did not close an existing SSE connection. No failed preliminary run is counted as a passing check.

**Affected files:** Current tab guidance, root README/AGENTS, supplemental docs, software, firmware, tools and local evidence. Simulation source/Git commit remains unchanged; runtime smoke writes only ignored data.

## 2026-10-04 — Complete the Mac software rehearsal

**Result:** One operator and five visitor browser contexts remained responsive for 1800.16 seconds. No recorded failures or browser page errors; state API p95 4.81 ms and maximum 26.77 ms. The run exercised shared previews/state, browser-local sandbox actions, operator token enforcement and repeated mock disconnect/recovery.

**Evidence:** [Measured report](../../../evidence/mac-rehearsal.json), [session summary](../../../evidence/rehearsal-session/summary.json), [CSV](../../../evidence/rehearsal-session/samples.csv), [events](../../../evidence/rehearsal-session/events.jsonl). Actual Mac processing throughput is in the summary; target 20 Hz is not presented as a measured Pi result.

**Scope:** Initial runnable Mac baseline; final loss/unplug/parser guards have their separate final automated checks. No Pi, receiver, Pico USB, trainer electrical or flight test is claimed.

**Timing finding:** Session processing averaged 18.62 FPS against the 20 Hz target. In addition to three intentional ACK faults, one unplanned stale-frame deadline occurred at 1720.70 seconds under concurrent build/browser load. It requested zero yaw and latched assistance disabled. Browser responsiveness still passed; this finding remains in the report and does not establish physical deadline performance.

## 2026-10-04 — Revise dashboard after design feedback

**Decision:** Replace the decorative dark presentation layout with a compact light monitoring interface. Put operational readouts and controls beside the video, give the sandbox a separate tab and fold tuning/fault controls into expandable sections. Remove slogan, numbered promotional sections, neon accents and oversized cards.

**Basis:** User feedback that the dashboard looked vibecoded. The browser script was also reformatted into named functions; unlocked form values now load the current server settings.

**Evidence:** [Monitor](../../../evidence/dashboard-revision/monitor.png), [operator view](../../../evidence/dashboard-revision/operator.png), [sandbox](../../../evidence/dashboard-revision/sandbox.png) and [phone view](../../../evidence/dashboard-revision/phone.png) rendered and visually inspected. Browser/rehearsal tools were adjusted for the new tab and expandable fault controls. This pass did not rerun the automated suites; earlier test/rehearsal reports describe the preceding interface.

## 2026-10-04 — Add native desktop operator software for Mac and Pi

**Decision:** Use a native Qt Widgets workstation, with no browser embedded in the operator window. Support local Mac/Pi sessions and Mac connection to the existing headless Pi service. Keep the browser for visitor/shared monitoring and isolated sandbox playback. Keep Qt optional for headless installation.

**Basis:** User said the dashboard still looked vibecoded, requested software, and explicitly selected **Desktop app for Mac and Pi**.

**Implementation:** Dockable native video/control/measurement/event workspace, yaw history, native settings/file dialogs, isolated fixture playback, token-authenticated remote connection and a desktop-owned mock server. That server runs in a separate process after the initial same-process prototype triggered freshness faults during Mac window initialization. No deadlines were relaxed and no trainer output was added.

**Delivery:** Apple Silicon app in `/Users/devk/Applications/Ball Drone.app`, source/dependency locks, reproducible builder, Pi desktop installer/menu launcher and Linux ARM64 render profile. [Desktop guide](14-desktop-app.md).

**Evidence:** [Native launch, packaged Mac render/signature, button-action walkthrough and Linux ARM64 offscreen rendering](../../../evidence/desktop/README.md). The walkthrough observed LOCKED → missing-ACK FAULT with zero yaw → recovered MANUAL/disabled. Original browser/50-test/endurance reports are not native GUI test results. Actual Pi display/drivers/performance and hardware remain unverified.

**Corrections:** Hidden Qt plugin flags required metadata-free source-launch copies. PySide network errors require explicit enum comparison. Mac code signing required staging outside the file-provider project folder. Linux desktop dependencies required libglib/libGL. These findings are recorded in AGENTS implementation notes and the desktop evidence.

**Remaining limit:** A disconnected remote operator window does not itself neutralize a still-running remote backend with fresh source/bridge. Close/switch requests disable and requires confirmation, but physical authority and network-loss failover still need hardware integration work.

## 2026-10-04 — Expand tests and preserve reproducible verification

**Decision:** Add API contract, native Qt, real mock-server lifecycle, CLI/PTY and verification-runner regression suites. Use `tools/verify.py` to preserve environment, commands, JUnit, statement/branch coverage, C sanitizer output and before/after source fingerprints in a new evidence directory. Missing dependencies, failures, skipped checks, coverage below configured gates or changed inputs make the run fail. Keep historical failures.

**Basis:** User requested more tests and a more verifiable implementation. The previous Python baseline had 50 tests; the current suite has **146**, including seven self-tests of the verification harness. Seeded controller assertions cover 6,000 operations; portable C assertions cover 10,000 arbitrary byte frames plus valid command boundaries.

**Corrections found by tests:** Nonfinite settings now return serializable validation errors. Concurrent desktop servers have separate private per-port token files. A neutral request queued behind an in-flight enable is retained and cannot be replaced by a queued enable. Invalid snapshots do not refresh state; imported traces validate all samples before playback; closed trace windows stop their timers. Fractional controller settings use native double spin boxes. A repeated workstation close does not attempt another disable against its stopped owned server.

**Recorded outcome:** [Current verification evidence](../../../evidence/verification/README.md): 146 tests, zero failures/errors/skips on Mac ARM64 Python 3.13.12 and Linux ARM64 container Python 3.13.16. Identical source manifest on both. Combined statement/branch coverage **82.13% / 84.81%**, controller **100%**. Portable C UBSan passes on Mac; ASan + UBSan pass on Linux. The rebuilt Mac app passes strict deep ad hoc signature verification and a short offscreen launch/shutdown smoke with 106 frames and zero faults.

**Preserved failures:** The initial Mac ASan trial stalled before C test execution; default Mac sanitizer checks use UBSan. The first Linux C sanitizer link failed for missing runtime libraries; the verification image now installs them. Neither failed overall report is counted as passing.

**Scope:** Software-only, synthetic/recorded fixtures and local virtual serial. Offscreen Qt and ARM64 container results are not actual Pi GUI/device/performance checks. The existing browser endurance report is not native endurance. Queued neutral guarantees request ordering, not a physical response deadline; remote operator disconnect still is not a lease. No transmitter output or flight readiness is established.

**Affected files:** Software tests/runtime/configuration, portable C tests, verification tooling/image, Mac app and handoff evidence, current software/desktop/status/verification docs, evidence index and AGENTS implementation notes. Preserved Google Doc sources and simulation repository remain unchanged.

## 2026-10-04 — Close hardware-free coverage gaps

**Decision:** Add 114 further regression cases for native validation/dialog/render/launch paths, streaming APIs, fake camera failures, source generation races, serial framing and emulator cleanup. Raise the verifier's default overall combined statement/branch gate from 80% to 95%, and extend module gates. Do not exclude uncovered code to inflate the result.

**Basis:** User asked whether the remaining coverage could be improved without hardware, following the 146-test Mac 82.13% / Linux 84.81% baseline.

**Corrections found:** A replaced source's blocked read could raise later and incorrectly fault the new input; source-generation checks now guard errors as well as frames. Serial host and emulator buffers cleared after oversize without remembering the invalid frame; they now discard through the next newline so an ACK/CMD-looking suffix cannot be accepted as a fresh message. The portable Pico scaffold already discarded oversized input until newline; no trainer output was added.

**Mac instrumentation:** Python 3.13 skipped this venv's UF_HIDDEN coverage startup `.pth`. Verification temporarily unhides it and restores the flag on success/error, with dedicated self-tests. `PYTHONPATH` explicitly selects current software source before any installed copy during early subprocess startup. Actual emulator CLI subprocess execution is now measured on Mac. An isolated verifier-test run also exposed reliance on cached platform metadata; the harness self-test now isolates that dependency explicitly.

**Recorded outcome:** [Current results](../../../evidence/verification/README.md): **260 tests pass with zero failures/errors/skips** on Mac and Linux ARM64; identical tested source hashes. Combined statement/branch coverage **99.38% / 99.42%**, statement coverage **99.82%** on both, branch coverage **97.66% / 97.90%**. Controller, detector, sources and API reach 100% combined coverage; desktop reaches 99.78%. Mac core profile passes 158 tests with 98.91% combined coverage, explicitly excluding UI tests. Portable C sanitizer checks still pass on both platforms.

**Delivery:** Rebuilt and strictly verified the ad hoc signed Apple Silicon app; short offscreen smoke records 101 frames, zero faults and no physical output. Refreshed installable package, documentation and handoff archive. Earlier evidence/build hashes remain historical records.

**Limits:** Fake capture/serial, deterministic IO doubles, offscreen Qt and local subprocesses exercise software contracts. They do not verify actual Pi display/network/performance, physical receiver/radio output, electrical levels, pilot override or flight. Three statements and a few branch outcomes remain uncovered; coverage gaps are visible and are not described as requiring hardware. No native endurance result or remote-operator lease is added.


## 2026-10-04 — Add protocol parity and deeper failure regressions

**Decision:** Add 90 tests after the 260-test baseline. Compile the actual portable C core into a host shared library and compare replies/state with Python across 4,800 seeded operations. Add exact watchdog boundary cases, ACK-order/replayed-handshake/wire-fragmentation cases, nested desktop validation/auth/close cases, coordinated late capture shutdown/open cases, a real desktop module subprocess and verification-runner compile/timeout/missing-report cases. Keep Qt optional in the headless profile.

**Corrections found:** Accept serial ACKs only in increasing accepted-sequence order; repeated READY cannot refresh command-ACK freshness. Account for one-nanosecond floating-point rounding at an exact 250 ms watchdog deadline. Require explicit boolean operator authorization and validate nested numeric/detection/trace values before widgets receive them. Close/switch requires a complete disabled/requested-zero snapshot; it does not establish physical output or a fresh bridge ACK. C firmware production code and transmitter output remain unchanged.

**Recorded outcome:** [Full reports](../../../evidence/verification/README.md): **350 passed**, zero failures/errors/skips on Mac and Linux ARM64 with matching source manifests. Combined statement/branch coverage **99.58% / 99.63%**; Mac core **208 passed / 99.41%**. Portable C UBSan passes on Mac, ASan + UBSan on Linux. [Partial development regressions](../../../evidence/verification/robustness-development-2026-10-04/README.md) preserve failures before fixes without claiming full verification provenance.

**Delivery:** Rebuilt installed Apple Silicon app, strict deep ad hoc signature verification passed; six-second offscreen smoke **102 frames, zero faults**, physical output false. Refreshed wheel, current documentation and handoff archive. Previous 260-/146-test evidence remains historical.

**Limits:** Mac statement coverage 99.94%, Linux 100%; branch coverage 98.25%, so uncovered paths remain reported. Host parity is limited to generated cases and is not Pico timing validation. No physical devices, actual Pi display/performance/network, native endurance, remote operator lease or flight readiness are established. Source tabs and independent simulation are preserved.


## 2026-10-04 — Expand exhaustive domains and reference-model tests

**Decision:** Add **3,709 cases** in seven files: 2,364 exhaustive protocol/ACK-order cases; 478 vision/fixture cases; 272 controller reference/state-model cases; 175 API input/mutation cases; 220 native schema/queue cases; 150 injected-clock engine deadline cases; 50 session evidence round-trip cases. No subagents or physical devices were used.

**Basis:** User asked for substantially more tests after the 350-test pass. Test count represents parameterized cases, not features or seeded operations. Domains include all 2,001 permitted yaw values, all 180 OpenCV hue values, all 120 arrival orders of five ACKs and all 32 five-command assistance queue sequences. Reference state/calculation models check 12,000 seeded controller actions and 480 API mutations in addition to the earlier corpora.

**Corrections:** Operator models now use strict types and reject unknown fields with 422. Strings such as "yes" could previously enable assistance; numeric settings accepted booleans/strings and extra fields were ignored. Correctly typed existing native/browser requests remain valid. Weighted-average smoothing preserves input exactly at 1.0; subtraction cancellation had moved errors at the inclusive deadband boundary into nonzero output. Wire protocol and C production core are unchanged.

**Recorded outcome:** [Current full reports](../../../evidence/verification/README.md): **4,059 passed**, zero failures/errors/skips on Mac ARM64 and Linux ARM64 with matching source manifest. Combined coverage **99.58% / 99.63%**; core profile **3,697 passed / 99.50%**. Portable C UBSan on Mac and ASan + UBSan on Linux pass. [Partial development output](../../../evidence/verification/matrix-development-2026-10-04/README.md) preserves 114 failing assertions before fixes and 3,559 passing new cases after, plus the 150 deadline checks; partial runs lack full provenance manifests.

**Delivery:** Rebuilt installed Mac app, strict deep ad hoc signature passed; six-second offscreen smoke **97 frames / 0 faults**, physical output false. Refreshed wheel, docs, lessons in AGENTS and handoff archive. Old source/evidence hashes remain historical.

**Limits:** Exhaustive domains are limited to enumerated values and host software behavior. Coverage gaps stay visible. These runs do not verify Pi display/performance/networking, physical receiver/Pico/radio, native endurance, remote operator leases, electrical output, physical override or flight. Independent simulation and source tab snapshots are preserved.

## 2026-10-05 — Keep the desktop status address visible

**Decision:** Show the operator workstation's session URL as a permanent status line that does not shrink under the macOS resize grip. Treat the wait for the desktop-owned server as "starting," and use the connection-lost overlay only after a live session goes stale. Draw the yaw history on the same dark field as the video.

**Basis:** A live Mac source launch on 2026-10-05 (`python -m ball_demo.desktop`, loopback port 8091) served a real preview JPEG and a MANUAL / disabled / yaw-zero state while the window was open. The same window's status line was clipped to `http://127.0.0.1:809`, and a grab at 2.5 seconds — before that server had answered — painted "Connection lost · preview is stale." Assistance stayed disabled and transmitter output stayed unimplemented; those defaults were left in place.

**Affected files:** `software/ball_demo/desktop.py`, `software/tests/test_desktop.py`, [desktop guide](14-desktop-app.md). The installed `.app` was not rebuilt.

## 2026-10-05 — Keep workstation panels inside the window

**Decision:** Remove the dock Float control so a panel cannot become its own window. Fit the green zoom button to the visible screen. Keep the event log, measurements and yaw legend inside the client area with aligned columns.

**Basis:** On the live Mac workstation, the dock title control described as "Undocks and re-attaches the dock widget" turned Live measurements into a separate window at 929,85 sized 291×562. The same grab clipped the event header to "ime" and the transport value at the right edge. The user called the result unprofessional. Assistance, mock output and the separate server process stay as they are.

**Affected files:** `software/ball_demo/desktop.py`, `software/tests/test_desktop.py`, [desktop guide](14-desktop-app.md). The installed `.app` was not rebuilt and is stale relative to this source.

## 2026-10-05 — Show a 16:9 silent preview

**Decision:** The operator video well letterboxes a 16:9 plate and reads "No signal". It does not draw the synthetic moving target, tracking box, grid, or scenario caption. The synthetic source still runs in the backend. The next entry keeps its numbers off the operator window.

**Basis:** The live preview was a tall picture of the synthetic scene, with dark side margins and the wrong aspect for the well. The user asked for an analog-FPV 16:9 frame and for the moving graphic to be removed.

**Affected files:** `software/ball_demo/desktop.py`, `software/tests/test_desktop_edges.py`, [desktop guide](14-desktop-app.md). The installed `.app` was not rebuilt.

## 2026-10-05 — Placeholder telemetry until a real source

**Decision:** The operator window does not display synthetic scene pixels or numbers derived from them. Measurements are em dashes, the yaw plot has axes only, and the session log says "No events". Recorded video and a camera may fill the measurements. Mock bridge text is not shown as a live value.

**Basis:** The user rejected the populated synthetic panel: invented yaw, error, quality, ages, frame counts, a zero command line, and a "SYNTHETIC · assistance disabled" event. Assistance stays disabled and the backend may still generate synthetic frames for tests.

**Affected files:** `software/ball_demo/desktop.py`, `software/tests/test_desktop.py`, `software/tests/test_desktop_edges.py`, [desktop guide](14-desktop-app.md). The installed `.app` was not rebuilt.

## 2026-10-05 — Give the source column one primary action

**Decision:** Restyle the source column so Enable yaw assistance is the only filled control. Disable and Apply are outline actions. Detector settings is a text disclosure. The state word is a normal label, and the column ends on a footer instead of an empty pit.

**Basis:** The user called the left column ugly: identical gray bars, an oversized MANUAL title, uneven boxes, and a dead area under the controls.

**Affected files:** `software/ball_demo/desktop.py`, [desktop guide](14-desktop-app.md). The installed `.app` was not rebuilt. Button meanings are unchanged.

## 2026-10-07 — Document Fusion MCP connections for Cursor and Antigravity

**Decision:** Save copyable connection prompts for Cursor and Antigravity that reuse the existing Fusion MCP endpoint at `http://127.0.0.1:27182/mcp`.

**Basis:** User requested that the prompts from this chat be added to `docs/`. Claude's existing configuration supplied the endpoint; the running server completed an MCP handshake, and Codex successfully queried open documents after registration. Cursor uses `url`; Antigravity uses `serverUrl`, with the active configuration path determined for the installed version.

**Status:** Codex connection verified on this Mac; Fusion reported zero open documents. The Cursor and Antigravity prompts have not been executed or verified in those apps. No CAD geometry was changed.

**Affected files:** [Connection prompts](16-fusion-mcp.md), documentation index, and this decision log.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Pre-rewrite archive index](README.md) — identifies this file as historical context, not current instruction.
- [Maintained document](../../decisions.md) — current requirements and status.
- This citation note is external to the preserved pre-rewrite text.
