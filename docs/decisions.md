# Ball Drone decision log

Append dated entries with the decision, basis, affected docs, and evidence. Record changes to the current design in the relevant doc as well.

Current authority: [2026-10-07 documentation baseline](README.md#authority-and-history). Older entries below retain their original scope, hardware and test dates; they are history, not instructions to restore the older 85 mm/Pico plan.

## 2026-10-04 — Initialize the Ball Drone workspace

**Decision:** Use this folder for the HackPHS 2026 Ball Drone idea and its current documentation.

**Basis:** User instruction on 2026-10-04 and the [project Google Doc](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit). A [dated tab snapshots](sources/google-doc-2026-10-04/README.md) records the source.

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

**Source preservation:** Split the dated text snapshot into nine files under `docs/sources/google-doc-2026-10-04/`. Each preserved tab body was checked against the original combined snapshot before that file was removed. Source wording and the source revision were retained.

**Current requirements:** The user's Mac runs the simulation. The Raspberry Pi hosts the demo server for browser clients. Yaw-only V1 assistance, pilot authority, provisional targets, and unverified runtime/physical status remain in the relevant current docs.

**Affected files:** Maintained docs and navigation, source snapshots, root README and AGENTS instructions, and CAD workspace navigation.

## 2026-10-04 — Implement the pre-hardware software demonstration

**Decision:** Raspberry Pi 5 runs tracking, yaw calculations and the offline demo server on port 8080. The Mac develops/rehearses software and runs the separate port-8765 simulation. Prepare both BallDrone-Demo hotspot and shared-network profiles, an isolated visitor playback sandbox, and provisional RP2040/Pico firmware. CAD stays deferred.

**Basis:** User's explicit 64-step implementation plan, including all numerical software defaults and requested acceptance checks. This refines the earlier server-only Pi assignment; preserved source tabs and earlier entries remain historical evidence.

**Implementation:** `software/` contains capture/detection/control/bridge/logging/API/local frontend, deterministic fixtures, recorded/camera adapters and deployment package. `firmware/` contains the ASCII protocol, portable C core and USB scaffold without trainer output. [Preparation status](11-pre-hardware-status.md), [runbook](12-demo-runbook.md) and [hardware worksheet](13-hardware-arrival.md) map the handoff.

**Recorded checks:** [Python, C, browser, fresh installation, Pico compile, Linux ARM64 and Mac simulation evidence](../evidence/README.md). The [long Mac rehearsal](../evidence/mac-rehearsal.json) passed 1800.16 seconds with one operator/five viewers and zero failures. It exercised the initial runnable baseline; final edge-case guards were separately checked through the final unit/browser/fresh/ARM64 runs. Physical device, electrical, radio and flight behavior remain pending.

**Corrections made during implementation:** Module/installation entry paths were corrected and checked in a fresh venv. A recovered mock bridge initially raced the host freshness deadline; recovery now obtains a genuine neutral ACK and stays disabled. Delayed ACKs are rejected by age. Pico integer parsing now rejects overflow explicitly on a 32-bit target. Browser reconnection is checked through a real server disconnect because the browser automation offline toggle did not close an existing SSE connection. No failed preliminary run is counted as a passing check.

**Affected files:** Current tab guidance, root README/AGENTS, supplemental docs, software, firmware, tools and local evidence. Simulation source/Git commit remains unchanged; runtime smoke writes only ignored data.

## 2026-10-04 — Complete the Mac software rehearsal

**Result:** One operator and five visitor browser contexts remained responsive for 1800.16 seconds. No recorded failures or browser page errors; state API p95 4.81 ms and maximum 26.77 ms. The run exercised shared previews/state, browser-local sandbox actions, operator token enforcement and repeated mock disconnect/recovery.

**Evidence:** [Measured report](../evidence/mac-rehearsal.json), [session summary](../evidence/rehearsal-session/summary.json), [CSV](../evidence/rehearsal-session/samples.csv), [events](../evidence/rehearsal-session/events.jsonl). Actual Mac processing throughput is in the summary; target 20 Hz is not presented as a measured Pi result.

**Scope:** Initial runnable Mac baseline; final loss/unplug/parser guards have their separate final automated checks. No Pi, receiver, Pico USB, trainer electrical or flight test is claimed.

**Timing finding:** Session processing averaged 18.62 FPS against the 20 Hz target. In addition to three intentional ACK faults, one unplanned stale-frame deadline occurred at 1720.70 seconds under concurrent build/browser load. It requested zero yaw and latched assistance disabled. Browser responsiveness still passed; this finding remains in the report and does not establish physical deadline performance.

## 2026-10-04 — Revise dashboard after design feedback

**Decision:** Replace the decorative dark presentation layout with a compact light monitoring interface. Put operational readouts and controls beside the video, give the sandbox a separate tab and fold tuning/fault controls into expandable sections. Remove slogan, numbered promotional sections, neon accents and oversized cards.

**Basis:** User feedback that the dashboard looked vibecoded. The browser script was also reformatted into named functions; unlocked form values now load the current server settings.

**Evidence:** [Monitor](../evidence/dashboard-revision/monitor.png), [operator view](../evidence/dashboard-revision/operator.png), [sandbox](../evidence/dashboard-revision/sandbox.png) and [phone view](../evidence/dashboard-revision/phone.png) rendered and visually inspected. Browser/rehearsal tools were adjusted for the new tab and expandable fault controls. This pass did not rerun the automated suites; earlier test/rehearsal reports describe the preceding interface.

## 2026-10-04 — Add native desktop operator software for Mac and Pi

**Decision:** Use a native Qt Widgets workstation, with no browser embedded in the operator window. Support local Mac/Pi sessions and Mac connection to the existing headless Pi service. Keep the browser for visitor/shared monitoring and isolated sandbox playback. Keep Qt optional for headless installation.

**Basis:** User said the dashboard still looked vibecoded, requested software, and explicitly selected **Desktop app for Mac and Pi**.

**Implementation:** Dockable native video/control/measurement/event workspace, yaw history, native settings/file dialogs, isolated fixture playback, token-authenticated remote connection and a desktop-owned mock server. That server runs in a separate process after the initial same-process prototype triggered freshness faults during Mac window initialization. No deadlines were relaxed and no trainer output was added.

**Delivery:** Apple Silicon app in `/Users/devk/Applications/Ball Drone.app`, source/dependency locks, reproducible builder, Pi desktop installer/menu launcher and Linux ARM64 render profile. [Desktop guide](14-desktop-app.md).

**Evidence:** [Native launch, packaged Mac render/signature, button-action walkthrough and Linux ARM64 offscreen rendering](../evidence/desktop/README.md). The walkthrough observed LOCKED → missing-ACK FAULT with zero yaw → recovered MANUAL/disabled. Original browser/50-test/endurance reports are not native GUI test results. Actual Pi display/drivers/performance and hardware remain unverified.

**Corrections:** Hidden Qt plugin flags required metadata-free source-launch copies. PySide network errors require explicit enum comparison. Mac code signing required staging outside the file-provider project folder. Linux desktop dependencies required libglib/libGL. These findings are recorded in AGENTS implementation notes and the desktop evidence.

**Remaining limit:** A disconnected remote operator window does not itself neutralize a still-running remote backend with fresh source/bridge. Close/switch requests disable and requires confirmation, but physical authority and network-loss failover still need hardware integration work.

## 2026-10-04 — Expand tests and preserve reproducible verification

**Decision:** Add API contract, native Qt, real mock-server lifecycle, CLI/PTY and verification-runner regression suites. Use `tools/verify.py` to preserve environment, commands, JUnit, statement/branch coverage, C sanitizer output and before/after source fingerprints in a new evidence directory. Missing dependencies, failures, skipped checks, coverage below configured gates or changed inputs make the run fail. Keep historical failures.

**Basis:** User requested more tests and a more verifiable implementation. The previous Python baseline had 50 tests; the current suite has **146**, including seven self-tests of the verification harness. Seeded controller assertions cover 6,000 operations; portable C assertions cover 10,000 arbitrary byte frames plus valid command boundaries.

**Corrections found by tests:** Nonfinite settings now return serializable validation errors. Concurrent desktop servers have separate private per-port token files. A neutral request queued behind an in-flight enable is retained and cannot be replaced by a queued enable. Invalid snapshots do not refresh state; imported traces validate all samples before playback; closed trace windows stop their timers. Fractional controller settings use native double spin boxes. A repeated workstation close does not attempt another disable against its stopped owned server.

**Recorded outcome:** [Current verification evidence](../evidence/verification/README.md): 146 tests, zero failures/errors/skips on Mac ARM64 Python 3.13.12 and Linux ARM64 container Python 3.13.16. Identical source manifest on both. Combined statement/branch coverage **82.13% / 84.81%**, controller **100%**. Portable C UBSan passes on Mac; ASan + UBSan pass on Linux. The rebuilt Mac app passes strict deep ad hoc signature verification and a short offscreen launch/shutdown smoke with 106 frames and zero faults.

**Preserved failures:** The initial Mac ASan trial stalled before C test execution; default Mac sanitizer checks use UBSan. The first Linux C sanitizer link failed for missing runtime libraries; the verification image now installs them. Neither failed overall report is counted as passing.

**Scope:** Software-only, synthetic/recorded fixtures and local virtual serial. Offscreen Qt and ARM64 container results are not actual Pi GUI/device/performance checks. The existing browser endurance report is not native endurance. Queued neutral guarantees request ordering, not a physical response deadline; remote operator disconnect still is not a lease. No transmitter output or flight readiness is established.

**Affected files:** Software tests/runtime/configuration, portable C tests, verification tooling/image, Mac app and handoff evidence, current software/desktop/status/verification docs, evidence index and AGENTS implementation notes. Preserved Google Doc sources and simulation repository remain unchanged.

## 2026-10-04 — Close hardware-free coverage gaps

**Decision:** Add 114 further regression cases for native validation/dialog/render/launch paths, streaming APIs, fake camera failures, source generation races, serial framing and emulator cleanup. Raise the verifier's default overall combined statement/branch gate from 80% to 95%, and extend module gates. Do not exclude uncovered code to inflate the result.

**Basis:** User asked whether the remaining coverage could be improved without hardware, following the 146-test Mac 82.13% / Linux 84.81% baseline.

**Corrections found:** A replaced source's blocked read could raise later and incorrectly fault the new input; source-generation checks now guard errors as well as frames. Serial host and emulator buffers cleared after oversize without remembering the invalid frame; they now discard through the next newline so an ACK/CMD-looking suffix cannot be accepted as a fresh message. The portable Pico scaffold already discarded oversized input until newline; no trainer output was added.

**Mac instrumentation:** Python 3.13 skipped this venv's UF_HIDDEN coverage startup `.pth`. Verification temporarily unhides it and restores the flag on success/error, with dedicated self-tests. `PYTHONPATH` explicitly selects current software source before any installed copy during early subprocess startup. Actual emulator CLI subprocess execution is now measured on Mac. An isolated verifier-test run also exposed reliance on cached platform metadata; the harness self-test now isolates that dependency explicitly.

**Recorded outcome:** [Current results](../evidence/verification/README.md): **260 tests pass with zero failures/errors/skips** on Mac and Linux ARM64; identical tested source hashes. Combined statement/branch coverage **99.38% / 99.42%**, statement coverage **99.82%** on both, branch coverage **97.66% / 97.90%**. Controller, detector, sources and API reach 100% combined coverage; desktop reaches 99.78%. Mac core profile passes 158 tests with 98.91% combined coverage, explicitly excluding UI tests. Portable C sanitizer checks still pass on both platforms.

**Delivery:** Rebuilt and strictly verified the ad hoc signed Apple Silicon app; short offscreen smoke records 101 frames, zero faults and no physical output. Refreshed installable package, documentation and handoff archive. Earlier evidence/build hashes remain historical records.

**Limits:** Fake capture/serial, deterministic IO doubles, offscreen Qt and local subprocesses exercise software contracts. They do not verify actual Pi display/network/performance, physical receiver/radio output, electrical levels, pilot override or flight. Three statements and a few branch outcomes remain uncovered; coverage gaps are visible and are not described as requiring hardware. No native endurance result or remote-operator lease is added.


## 2026-10-04 — Add protocol parity and deeper failure regressions

**Decision:** Add 90 tests after the 260-test baseline. Compile the actual portable C core into a host shared library and compare replies/state with Python across 4,800 seeded operations. Add exact watchdog boundary cases, ACK-order/replayed-handshake/wire-fragmentation cases, nested desktop validation/auth/close cases, coordinated late capture shutdown/open cases, a real desktop module subprocess and verification-runner compile/timeout/missing-report cases. Keep Qt optional in the headless profile.

**Corrections found:** Accept serial ACKs only in increasing accepted-sequence order; repeated READY cannot refresh command-ACK freshness. Account for one-nanosecond floating-point rounding at an exact 250 ms watchdog deadline. Require explicit boolean operator authorization and validate nested numeric/detection/trace values before widgets receive them. Close/switch requires a complete disabled/requested-zero snapshot; it does not establish physical output or a fresh bridge ACK. C firmware production code and transmitter output remain unchanged.

**Recorded outcome:** [Full reports](../evidence/verification/README.md): **350 passed**, zero failures/errors/skips on Mac and Linux ARM64 with matching source manifests. Combined statement/branch coverage **99.58% / 99.63%**; Mac core **208 passed / 99.41%**. Portable C UBSan passes on Mac, ASan + UBSan on Linux. [Partial development regressions](../evidence/verification/robustness-development-2026-10-04/README.md) preserve failures before fixes without claiming full verification provenance.

**Delivery:** Rebuilt installed Apple Silicon app, strict deep ad hoc signature verification passed; six-second offscreen smoke **102 frames, zero faults**, physical output false. Refreshed wheel, current documentation and handoff archive. Previous 260-/146-test evidence remains historical.

**Limits:** Mac statement coverage 99.94%, Linux 100%; branch coverage 98.25%, so uncovered paths remain reported. Host parity is limited to generated cases and is not Pico timing validation. No physical devices, actual Pi display/performance/network, native endurance, remote operator lease or flight readiness are established. Source tabs and independent simulation are preserved.


## 2026-10-04 — Expand exhaustive domains and reference-model tests

**Decision:** Add **3,709 cases** in seven files: 2,364 exhaustive protocol/ACK-order cases; 478 vision/fixture cases; 272 controller reference/state-model cases; 175 API input/mutation cases; 220 native schema/queue cases; 150 injected-clock engine deadline cases; 50 session evidence round-trip cases. No subagents or physical devices were used.

**Basis:** User asked for substantially more tests after the 350-test pass. Test count represents parameterized cases, not features or seeded operations. Domains include all 2,001 permitted yaw values, all 180 OpenCV hue values, all 120 arrival orders of five ACKs and all 32 five-command assistance queue sequences. Reference state/calculation models check 12,000 seeded controller actions and 480 API mutations in addition to the earlier corpora.

**Corrections:** Operator models now use strict types and reject unknown fields with 422. Strings such as "yes" could previously enable assistance; numeric settings accepted booleans/strings and extra fields were ignored. Correctly typed existing native/browser requests remain valid. Weighted-average smoothing preserves input exactly at 1.0; subtraction cancellation had moved errors at the inclusive deadband boundary into nonzero output. Wire protocol and C production core are unchanged.

**Recorded outcome:** [Current full reports](../evidence/verification/README.md): **4,059 passed**, zero failures/errors/skips on Mac ARM64 and Linux ARM64 with matching source manifest. Combined coverage **99.58% / 99.63%**; core profile **3,697 passed / 99.50%**. Portable C UBSan on Mac and ASan + UBSan on Linux pass. [Partial development output](../evidence/verification/matrix-development-2026-10-04/README.md) preserves 114 failing assertions before fixes and 3,559 passing new cases after, plus the 150 deadline checks; partial runs lack full provenance manifests.

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

## 2026-10-07 — Rewrite current docs from the revised Google Doc

**Decision:** Rework the maintained documentation from the current eight adopted tabs of HackPHS 2026: Idea, BOM, CAD, Software, Hardware, Simulation, refs and future. The ninth tab is now `toImplement`; the user explicitly deferred its adoption and Pico wireless audio. Retain the old Further Improvement / Feedback file as historical reference.

**Source:** [2026-10-07 tab snapshot](sources/google-doc-2026-10-07/README.md), with revision/tab metadata, tables, vendor links and five embedded images. Preserve the [2026-10-04 source](sources/google-doc-2026-10-04/README.md) and [pre-rewrite local docs](sources/local-docs-before-rework-2026-10-07/README.md).

**Current hardware plan:** Apex-2 approximately 95 mm wheelbase; Specter 1202.5 11000KV motors; 2-inch props; 245–250 mm cage; RC832 composite output through a USB capture adapter to Raspberry Pi 4/5; Arduino Mega 2560 through a verified trainer/radio/ELRS path. Existing Pi deployment targets Pi5; existing Pico parser/USB artifacts are historical software evidence, not an implemented Mega bridge.

**User-confirmed demo decisions:** Manual flight/contact plus live target tracking is accepted success; physical yaw assistance is not required. Prefer the assisted route only after complete Mega-to-radio, override and signal-loss/failsafe verification. Keep the manual route rehearsed regardless. Its screen must show live FPV, colored-target box, center/error and “Manual steering — computer steering unavailable.” Separate simulation footage from live FPV; never present synthetic yaw/motion as aircraft telemetry.

**User-confirmed gimbal gate:** Ten consecutive low-energy contacts with no damage or prop strikes, at least three minutes usable caged flight, and repeatable manual recovery. Keep the working fixed cage as fallback.

**User-confirmed ordering/budget:** All currently planned parts have been ordered, per the user. Additional purchases are contingency only, capped at $200 with at least 15% ($30) reserved for replacements, failed prints, shipping issues and rework. Optional spending waits until the core works. Ordering is not verified delivery/compatibility.

**User-confirmed simulation/time decisions:** Keep the simulator illustrative; matching physical dimensions is not required. The user's response referred to the then-described ~372 mm/4-inch geometry. Subsequent review of the current repository code found different parameters; see the 2026-10-07 correction below. Prioritize the physical build and one stable industrial map. Freeze new hardware/features 48 hours before the first judged demo. Final 24 hours are reliability, battery preparation, evidence and at least three consecutive complete rehearsals; allow only fixes restoring working core functionality.

**Status and evidence boundary:** The rewrite found no measured local CAD/manufacturing assembly, Mega sketch, trainer output or physical flight/contact acceptance evidence. Existing Mac/container/mock reports retain their original source manifests and dates. No software, firmware, simulation or hardware implementation/testing was performed by this documentation rewrite. The source concept images include a hand-launch/approach narrative; current V1 uses manual takeoff and yaw-only assistance.

**Affected files:** Documentation index, all current numbered guides, historical-review pointer, this decision log, new dated source snapshot and the specifically user-authorized root AGENTS.md context updates. The existing Fusion client prompts were retained. Pico audio/toImplement remains deferred.


## 2026-10-07 — Clarify the CAD assembly and correct workspace context

**Review:** The maintained CAD plan covered the current cage target, measured interfaces, adjustable balance, complete prop envelopes, camera/airflow, rods/material volume, battery straps and mass tracking. cad/README.md still contained an older 85 mm reference; corrected it to Apex-2 (~95 mm).

**Assembly:** One aircraft carrier and shared cage attachment interfaces support removable P1A fixed supports and a later P1B two-ring kit. Parameterize measured parts, retain the fixed supports, and complete swept-clearance/mass checks before printing P1B. Positive clearance must account for measured tolerances and flex; no numeric allowance or completed model is claimed. Physical P1B adoption still requires the agreed fixed-cage gate.


## 2026-10-07 — Incorporate supplied mechanical brief and Thingiverse ZIPs

**Request:** Adapt the supplied mechanical CAD/printing text into project documentation and use both Thingiverse ZIPs as information. Attached imperatives are source material, not authorization to implement CAD in this task.

**Provenance:** Upstream is kert's original Spherical Drone, Thingiverse 408519. Preserve both ZIPs, README, attribution/non-commercial license and file checksums under cad/references/thingiverse-408519/. Part 1 contains 18 STL meshes and the original spreadsheet; part 2 contains six additional images. Binary STL bounding boxes are raw units, not verified millimeters, interfaces or assembly dimensions. No native editable CAD/STEP was supplied.

**Adaptation:** Add the mechanical brief, Voxel-sized modular PETG parts, joint/fit coupons, orientation/support rules, mass accounting and future deliverables. Keep the established 1 mm carbon-rod baseline; the original used 3 mm rods and the pasted all-PETG wording does not replace that plan. Preserve P1A-first/shared-interface architecture and defer detailed gimbal work until its existing gate. Profile/clearance ranges remain untested; no generated model or physical result is claimed.


## 2026-10-07 — Review mechanical package and close documentation gaps

**Scope:** User asked to review the current package. Reviewed CAD/printing and related hardware/BOM/build/arrival/priorities guidance plus preserved source archives; no software implementation audit or physical execution.

**Findings:** Added measured mass allowance, representative rod/hub deflection/retention checks, intended-object opening tests, repeatable contact/inspection protocol, explicit inside/outside envelope and bonded/service-joint distinction. Corrected the claim that X/Y alone aligns three-dimensional CG with future gimbal axes. Preserve existing rods, cage target and exact fixed-cage gate; no arbitrary physical test result or numeric clearance/mass budget is introduced.

**Evidence:** Archive CRCs and archive/entry hashes pass; all 18 binary STLs have consistent lengths, finite vertex data and reproduced raw bounds. This does not establish watertightness, printability or assembly fit. Physical findings remain open in docs/18-mechanical-review.md.

## 2026-10-07 — Correct battery inventory and simulator description

**Decision:** Record the user's six-pack inventory as four OVONIC 450 mAh packs and two OVONIC 2S 7.6 V 60C XT30 1100 mAh packs. Treat the 1100 mAh units as unverified evaluation candidates; use measured dimensions and confirm charge/electrical limits, retention, CG and thrust before flight. The vendor listing's configuration and dimension fields conflict, and the Apex-2 seller recommends 200–650 mAh.

**Correction:** Replace stale ~372 mm/4-inch simulator descriptions with values read from the current code: 112.5 mm cage circumradius, 5 mm hub radius and 50.8 mm propeller diameter. The simulation is illustrative and does not validate the physical build. The earlier ~372 mm/4-inch wording is retained as historical context for the user's no-match decision; the code-audited values govern current simulator documentation.

**Repository placement:** Publish the project at the root of Wasim Vorvoi's `HackPHS` repository alongside the existing simulator files. The 2026-10-04 `simulation/` clone entry records the earlier local wrapper layout and is superseded by this integration.

**Affected files:** BOM, hardware, CAD, arrival, build/test, simulator, README, AGENTS instructions and this decision log. Battery identity is user-reported; chemistry/maximum charge voltage, dimensions, mass and flight suitability remain pending physical verification.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [HackPHS 2026 Google Doc](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit) — Primary project source; current tab IDs/revision are in the dated snapshot.
- [Current documentation index](README.md) — Adopted plan and current status.
- [Saved evidence index](../evidence/README.md) — Evidence links for recorded implementation/test changes.

## 2026-10-07 — Generate P1A cage stages 1–3 in Fusion (placeholder geometry)

**Request:** User designated the two Thingiverse 408519 download folders as the reference to scale down and asked for CAD stages 1–3.

**Implementation:** Fusion project `HackPHS Ball Drone`, design `Apex2 Ball Cage P1A`, generated by `cad/apex2-cage/build_stages_1_3.py` (since superseded by `build_p1a.py`). Stage 1 user parameters (placeholders labelled MEASURE/FIT COUPON); stage 2 placeholder Apex-2 envelope with four full prop disks, camera view cone and 450/1100 mAh battery boxes; stage 3 truncated-icosahedron skeleton scaled to a 248 mm span with the original hub arrangement (50 three-way, 10 four-way, 2 pole five-way; 90 + 10 rods). Sockets were re-derived for 1 mm rods from measured original hub proportions rather than scaled uniformly.

**Recorded nominal results:** 248.0 mm span; 49.03 mm hub spacing; rod cut lengths 44.53 mm × 90 and 37.86 mm × 10; ~5.3 g of rod; 44.4 mm minimum prop-disk-to-structure distance. These use placeholder aircraft dimensions, no flex and envelope hubs; they are not measured fit, clearance or mass results. See [cad/apex2-cage/README.md](../cad/apex2-cage/README.md).

## 2026-10-07 — Add printable hubs, fit strip and removable supports (stages 4–5); stage 6 measurement path

**Request:** User asked for stage 4 (real hubs and a socket-clearance test strip), stage 5 (adjustable aircraft mount, battery strap, removable supports) and stage 6 (measured values and re-checks).

**Implementation:** `cad/apex2-cage/build_p1a.py` replaces the stage 1–3 script. Hubs are generated per unique arm layout and placed at all 62 nodes: `hub_3way` × 46, `hub_3way_mount_A` × 4, `hub_4way` × 10, `hub_pole_5way` × 2. Each prints flat on its outer face without supports. `socket_fit_strip` tests 0.05–0.30 mm per-side socket clearance and 1.6–1.8 mm M2 pilots. Stage 5: carrier plate with ±5 mm fore-aft frame slots, ±4 mm lateral support slots and strap slots; two support arms along ±X between the props; two X brackets screwed to bosses on the four hubs of the ±X equator edges. These are a provisional shared interface for a later P1B pivot. STLs are exported to `cad/apex2-cage/exports/`.

**Recorded nominal checks (placeholder aircraft, no flex):** 248.0 mm span; Fusion interference analysis found no rod/hub, support/hub or support/rod interference, and rods clear hub material by 0.147 mm. Brackets sit flush on the bosses. Prop disks are 43.9 mm from the cage and 12.6 mm from the supports. Ten of 62 hub nodes fall inside a 120° placeholder camera cone. Added mass is about 53 g upper bound (solid volume). Mass budget is pending.

**Stage 6 status:** No measurements supplied yet. `cad/apex2-cage/measurements.json` holds null placeholders; filling it and re-running applies the values and repeats the clearance, camera and mass checks. No print, fit or physical test result is claimed.

## 2026-10-07 — Apply vendor-spec placeholders, print plates and mass/thrust requirement

**Change:** `cad/apex2-cage/vendor_specs.json` records published reseller/vendor dimensions and masses with sources (frame, Specter 1202.5 motor, Gemfan 2015, OVONIC 450/1100 mAh, Specter AIO; camera FOV low confidence). `build_p1a.py` applies them before `measurements.json`, so measured values always win. Strap slots now stay outboard of the frame-screw slots. `make_plates.py` arranges the exports into four Voxel plates; exported meshes are watertight.

**Recorded nominal results:** prop disks 44.4 mm from the cage and 9.5 mm from the supports; 19 of 62 hubs inside a 165° camera cone. Interference analysis finds no collisions apart from the two alternative battery boxes overlapping each other. The bare-aircraft component sum is 44.8 g. All-up mass is ~129 g with a 450 mAh pack and ~146 g with an 1100 mAh pack, so 2:1 needs ≥258 g and ≥292 g of static thrust. No thrust table was found, so thrust remains to be measured. These are vendor-data estimates, not measurements of delivered parts.

## 2026-10-07 — Add rod cutting jig and assembly guide

`build_p1a.py` now also generates `rod_cutting_jig`, with grooves, end stops and blade slots at the derived edge (44.53 mm) and pole (37.86 mm) rod lengths; it prints on plate 1 with the fit strip. `cad/apex2-cage/README.md` adds an assembly guide covering fit testing, rod cutting, hub placement and orientation, cap-and-ring build order, aircraft mounting and a props-off clearance check. No physical assembly has been performed.

## 2026-10-07 — CAD the P1B two-ring gimbal in a separate design (user request)

**Decision:** The user asked for the complete gimbal version in a separate file, referencing the Thingiverse 408519 folders. The gimbal was therefore modelled before the P1A gate. That gate (ten undamaged contacts, ≥3 min caged flight, repeatable recovery) still governs flying P1B; the P1A design stays the fallback.

**Implementation:** Fusion design `Apex2 Ball Cage P1B Gimbal`, generated by `cad/apex2-cage/build_p1b.py`. It follows the original kinematics (cage–Z–outer ring–Y–inner ring–X–aircraft) and segmentation: flat quarter rings joined by junction blocks at the pivots. Pivots are MR52ZZ bearings on 2 mm pins. Ring radii are derived from the aircraft's swept radius plus 4 mm. The aircraft is raised 2.5 mm to put the estimated 450 mAh CG on the pivot axes, and ±6 mm slots allow height balancing. The P1A cage, hubs and carrier are reused; only the two pole hubs gain pin bosses. `vendor_specs.json` now includes the user-supplied published values (450 mAh pack 62.8 × 16.4 × 13.8 mm, 26 g; 1100 mAh pack 56.56 × 23.50 × 18.40 mm, ~48 g; 12.5 mm strap; ~9 mm prop height). The 1 mm rod size is recorded as a listing value pending calipers.

**Corrections found:** Occurrence transforms set after creation are ignored in these parametric designs. This had left the outer ring flat and the P1A rod jig at the origin. All transforms are now set at creation, and verification was re-run on the corrected layout. The P1B pole-hub pin boss had partly filled the pole-rod sockets, so the sockets are now re-cut after the boss is added.

**Recorded nominal checks:** P1B static interference shows only the intended pin press fits. 420 sampled joint poses show 0 collisions. The radial budget runs 74.7 → 79–85 → 90–96 → ~115 mm. Added mass is ~93 g upper bound, so 2:1 needs ≥327 g of thrust with the 450 mAh pack. P1A was rebuilt and shows 0 interferences across 80 bodies. All exported meshes are watertight. These are vendor-data CAD checks, not fit or flight results.

## 2026-10-07 — Record researched part specifications, weight ceiling and deferred decisions

**Parts:** The user supplied Amazon links for the BOM parts and the larger battery (B0D318NL5W). Its Amazon title reads OVONIC 2S 1100 mAh 7.6 V 60C XT30 "High Voltage", 2 per package. The user called it 1150 mAh, so the label must be checked. Published dimensions are recorded in a new [BOM specification table](02-bom.md#researched-part-specifications-2026-10-07) and `cad/apex2-cage/vendor_specs.json`. The camera listing is a Caddx Ant 1200TVL 1.8 mm, so the CAD view cone now uses ~160° horizontal. The pins are 2 × 16 mm stainless steel and the screw kit is VGBUY M2 × 4–20 mm. These are listing values, not measurements.

**User constraints and answers:** All-up mass must not exceed **175 g**. **Both** battery types will be used. Pin length, rod bonding and camera uptilt are deferred and listed as open decisions in [cad/apex2-cage/README.md](../cad/apex2-cage/README.md#open-decisions-deferred-by-the-user). The weight breakdown shows P1B at ~93 g added (upper bound), so it exceeds 175 g with the 1100 mAh pack. Lightening options are recorded for later.

## 2026-10-07 — Full Amazon listing read for part dimensions

Every BOM Amazon page was read in full, not just its title. Confirmed:
- 450 mAh pack: 62.8 × 16.4 × 13.8 mm, 26 g.
- 1100 mAh pack: 56.56 × 23.50 × 18.40 mm, ~48 g. The listing says 1100 mAh, not 1150.
- Both listings say to stop charging at 4.2 V/cell, despite the "High Voltage" title.
- Frame: 20 mm columns; the seller recommends 200–650 mAh.
- Motor: 80 mm wires; ships with 2 × M2×7 and 4 × M2×5 screws.
- Pins: 304 stainless, Ø2 mm +0/−0.02 mm, 0.4 g, chamfered ends.
- Bearings: MR52ZZ, 2 × 5 × 2.5 mm, chrome steel.
- Strap: nylon, 12.5 × 200 mm.

Not published on any listing: frame centre-plate width, prop hub size, strap thickness, bearing tolerance, cable lengths and 2-inch-prop thrust. HGLRC's table gives 222 g per motor with a larger Gemfan 65 mm prop at 2S, which is an upper reference only. The assembled prop height also needs measuring. These remain caliper/test items.

## 2026-10-07 — Apply provisional dimensions and thrust estimate

**Provisional values (user research, labelled in `vendor_specs.json`):**
- Apex-2 centre plate ~33 mm (photo-based; no drawing).
- Prop underside 8.9 mm above the frame; prop envelope modelled to 14 mm.
- Prop hub ~5 mm OD × 4–5 mm.
- 2 mm strap allowance, giving a 2.5 mm slot.
- MR52ZZ bearings confirmed ABEC-1.
- Battery leads are 20 AWG with XT30 and JST-XHR-3P; lead lengths are unpublished.

Both designs were rebuilt. P1A has 0 interferences; P1B has 420 swept poses with 0 collisions and only the intended pin press fits.

**Thrust finding:** The estimated 220–300 g total static thrust gives the following thrust-to-weight ratios:
- P1A: 1.78–2.42 (450 mAh) and 1.51–2.06 (1100 mAh).
- P1B: 1.35–1.84 (450 mAh) and 1.19–1.62 (1100 mAh).

At this thrust, 2:1 caps all-up mass at ~110–150 g, which is tighter than the 175 g user ceiling. A static thrust test is now the highest-priority measurement. HGLRC's 222 g/motor (65 mm prop) is not used.

## 2026-10-07 — Revise thrust estimate upward

The user revised the thrust estimate to ~70–100 g per motor (~280–400 g total) on 2S with the Gemfan 2015, planning with 350 g total until bench-tested. The earlier 55–75 g/motor figure is withdrawn. At 350 g the estimated thrust-to-weight ratios are:
- P1A: 2.82 (450 mAh) and 2.40 (1100 mAh).
- P1B: 2.15 (450 mAh) and 1.89 (1100 mAh).

P1B with the 1100 mAh pack remains ~10 g over the 175 g ceiling, so lightening is still needed. The values are recorded in `vendor_specs.json` and the CAD README. This is still an estimate pending a static thrust test.

## 2026-10-07 — Finish CAD: antenna mount, gimbal fit coupon, print-mass estimate and lightening pass

**Added:**
- The VTX antenna element is now part of the aircraft envelope, with a rear antenna sleeve on the shared carrier. It stays clear of the props and inside the gimbal sweep.
- `gimbal_fit_coupon`: bearing seats 4.95–5.15 mm, and pin press holes 1.80–2.00 mm in both print orientations.
- A print-mass estimate (1.2 mm walls + 25 % infill). It showed that the thin parts print essentially solid, so infill alone cannot reduce mass.

**Lightening pass** (new defaults; existing documents updated):
- Hub keels narrowed to 1.6 mm.
- Carrier 2.5 mm thick with a centre window.
- Ring bands reduced from 6 × 3.5 to 5 × 3 mm.
- One M2 per splice side instead of two (28 screws instead of 44 in P1B).
- Outer pole junctions slimmed to a bearing-width post.

Added structure fell from ~53 → 44.7 g (P1A) and ~93 → 70.2 g (P1B). Estimated all-up: P1A 116/138 g and P1B 141/163 g (450/1100 mAh). At the 350 g planning thrust that gives 3.03/2.55 : 1 and 2.48/2.15 : 1, all within the 175 g ceiling. Ring radii are now 79–84 and 89–94 mm.

**Checks after the changes:** P1A static interference 0. P1B shows only the intended pin press fits, and 420 swept poses give 0 collisions. All exported meshes are watertight, and the P1A and P1B plates were regenerated.

`cad/apex2-cage/README.md` was rewritten to cover both designs, all parts, the plates, the checks, the weight/thrust table, the rolling estimate and a P1B assembly guide. Stiffness of the lightened parts, all fits and the thrust remain unverified until printed and tested.

## 2026-10-07 — Fix disconnected outer-ring pole junction (user-reported)

The user saw that the outer ring was not joined at the bottom. Confirmed: the second `outer_junction_Z_bearing` sat at x = +99.8 mm instead of z = −99.8 mm. The outer ring was therefore open at the bottom and not pinned to the bottom pole hub. The cause was child occurrence transforms placed under a rotated parent. Ring parts now receive their full world transform under an identity holder.

The earlier checks only detected collisions, so a misplaced part that hit nothing passed. A connectivity check now requires:
- each junction to touch two quarters;
- each pin to engage its press part and pass through its bearing;
- each bearing to sit in its seat.

After the fix: connectivity passes, 420 swept poses give 0 collisions, and static interference shows only the six intended pin press fits.

## 2026-10-07 — Independently inspect Fusion P1B version 7

User requested a screenshot-driven review of the actual Fusion design, treating the attached images as reference material. Inspected the live saved version 7 of Apex2 Ball Cage P1B Gimbal. Saved the [report, screenshots, scripts and raw measurements](../cad/apex2-cage/review-2026-10-07/README.md).

**Confirmed defects:** +4 mm X and +5 mm Y balancing offsets followed by −15° X rotation create 49.013782 mm³ of prop-keepout / inner-quarter overlap. The generator sizes and checks centered aircraft geometry, omitting allowed adjustment travel. The modeled 20° camera centerline intersects an outer-ring quarter about 57.9–62.8 mm ahead of the lens.

**Additional findings:** Native Fusion joints/as-built joints/rigid groups are absent. All bodies use Steel, and native mass includes analysis envelopes; use the separately qualified structure estimate. Nominal underside M2 cap heads would overlap the 1100 mAh battery under the stated fastening assumption; actual fastening and wiring remain unmodeled. Physical fits, rod/ring strength, mass and thrust remain unverified.

**Passed checks:** Nominal static interferences are only the six intended pin press fits. All eight junctions and six pivot interfaces have expected geometric contacts, including the repaired bottom outer-ring connection. The maximum assembly span is 248 mm. Fourteen part STLs and four print plates pass closed-edge/manifold-edge/winding checks; plates fit 140 × 140 mm. The before/after model inventory matched.

Updated the CAD README to remove the blanket clearance guarantee and identify these open issues before a P1B structural print batch. No CAD solid or parameter changes were saved. Temporary diagnostic graphics were removed, but their display set Fusion's modified indicator; saved cloud version remains 7.

## 2026-10-07 — Address the P1B Fusion review (v7)

**Review:** `cad/apex2-cage/review-2026-10-07/README.md`. The generator hashes matched the reviewed source, and all five findings were accepted.

**Changes:**
1. **Prop clearance with balancing travel.** Ring radii and swept checks now include every travel extreme. The P1B travel is reduced to ±2 mm across, ±3 mm along the arms and ±5 mm vertical; battery fore-aft sliding under the strap still adds adjustment. The rings grew to 84–89 / 94–99 mm with 16 mm to the cage. 612 sampled poses, including all travel corners, give 0 collisions.
2. **Camera centreline.** The gimbal axes are reassigned so the aircraft pivots on Y (fore-aft): cage–Z–outer ring (XZ)–X–inner ring (XY)–Y–aircraft. This is the only perpendicular layout with no ring in the straight-ahead view at the nominal pose. The centreline is clear at nominal, and a ring crosses it in ~2 % of sampled free-gimbal orientations. The P1B support arms now run fore-aft, the carrier has a P1B variant, and the antenna moves to the frame top.
3. **1100 mAh pack vs fasteners.** M2 nut and screw-tail envelopes are modelled under the carrier, and a 3 mm foam battery pad was added, giving 0.4 mm clearance. CG and sweep include the pad.
4. **Kinematics.** The cage is grounded, the moving groups are rigid groups, and three as-built revolute joints are added. Pins and bearings live in the groups that carry them. Drive-tested at several angles and reset.
5. **Mass.** Materials are assigned: PETG 1.27, carbon 1.55, a massless envelope material, 304 stainless pins and 440C bearings. Component masses are meaningful; the P1A root also counts 13.8 g of hidden reference meshes.

**Results:** P1B added structure 72.5 g. All-up is ~143 g (450 mAh) and ~165 g (1100 mAh), giving 2.44 and 2.12 : 1 at the 350 g planning thrust. P1A is unchanged in mass, with 0 interferences including the pad and nuts. All 31 exported and plate meshes are watertight. Strength, fits, thrust and real CG remain physical tests.

## 2026-10-08 — Correct foam-pad clearance at P1B frame travel extremes

**Evidence:** In saved P1B v14, translating frame nuts ±2 mm in X while leaving the carrier pad fixed produces 24.529076 mm³ overlap. The old sweep translated both together. The pad width is now derived from nut reach plus frame travel: 19.881 → 15.881 mm for P1B; P1A remains 19.881 mm. A separate relative-motion gate gives zero overlap and ≥0.50 mm nominal clearance. A reconstructed old pad and excessive 3 mm travel are rejected by the regression checks. No allowed travel value was changed.

## 2026-10-08 — Exclude references and fixtures from native aircraft structure mass

**Evidence/change:** Hidden imported Thingiverse hub copies contributed 13.8214 g, P1A fixtures 12.0906 g and the P1B fit coupon 11.0886 g to native root totals. Their Fusion copies now use the near-zero-density analysis material. Root mass is about 40.73 g (P1A) / 67.62 g (P1B); it excludes the placeholder aircraft and unmodeled M2 hardware. Original archives and historical reviews remain untouched. Material gates catch non-aircraft bodies carrying substantial native mass.

## 2026-10-08 — Add geometric acceptance gates and report local pivot reserves

**Change/evidence:** Generators now reject unexpected intersections, failed Booleans, disconnected printable bodies, failed connectivity, blocked nominal camera and over-budget accounted mass. Continuous face bounds cover prop/support translation; origin-centred radial containment covers the rotating printed structures and all allowed prop offsets. Actual radial reserves including junctions are 0.321 mm inner/outer and 0.359 mm outer/cage, rather than the 5/16 mm ring-band-only distances. Prop-to-inner reserve is 4.389 mm. Eight driven joint configurations have only six intended press fits, all connectivity checks pass and angles reset. Positive rigid-CAD gaps do not establish printed or loaded clearance; coupons and representative load tests remain required.

## 2026-10-08 — Make exported parts and plates reproducible per design

**Evidence/change:** A missing P1B carrier export previously silently selected the different P1A carrier. Selected-design-only loading now fails explicitly. Generator manifests record hashes, native volumes and counts; plate manifests record source hashes, orientations, placements and physical part counts. Missing/stale/changed sources and open/nonfinite meshes fail. Both sets were regenerated: 23 part STLs and eight plates are closed, finite, consistently wound and within 140 × 140 mm plate bounds. This does not validate slicer/toolpaths or physical printing.

## 2026-10-08 — Qualify mass, fit labels and remaining decisions

**Correction:** Accounted estimates are P1A 115.51/137.51 g and P1B 143.25/165.25 g (450/1100). The P1B/1100 estimate leaves 9.75 g for excluded/unweighed items; 10 g more would exceed 175 g. Modeled solid bearing hardware instead of the 0.20 g allowance gives about 166.0 g before other extras. No actual mass/thrust pass is claimed. Both generators now preserve measured bare-aircraft/thrust overrides in the relevant mass report.

**Fit labels:** A 5.05 mm seat on a nominal 5.00 mm bearing is CAD clearance, not a proven press fit. The full 16 mm pin layout is unverified; the current model uses 10.5 mm pins. Cutting/deeper seats, rod bonding and camera tilt remain deferred. Documentation masses, P1B X/Y assembly directions and review status were corrected. Fusion saves are P1A v18 / P1B v17; the detailed report includes before/after hashes and evidence.

**Unchanged scope:** Apex-2, 2-inch props, 245–250 mm cage, fixed-cage-first physical gate, yaw-only assistance, accepted manual/live-tracking demo and deferred Pico audio/toImplement. Required physical work includes strap routing/access, screw-stack protrusion, wiring slack, rod/ring stiffness/retention, pack-specific CG, actual weight and thrust.

## 2026-10-08 — Independent verification of the 2026-10-08 review changes

I checked the review's fixes without reusing its scripts. The source hashes match the review's final hashes, and I read the full diffs for both generators, `make_plates.py` and the new `validation.py`.

**Confirmed:**
- **Static interference:** Fusion's own interference engine finds only the six intended pin press fits in P1B and 0 in P1A.
- **Pad defect was real:** the old 19.881 mm pad, rebuilt, overlaps the nuts by 24.527 mm³ at ±2 mm X.
- **Pad fix:** the new 15.881 mm P1B pad has 0 overlap and a 0.50 mm gap at ±2/±1/0 mm. P1A's 19.881 mm pad stays clear (0.50 mm) across ±5 mm Y.
- **Native mass:** P1A 40.729 g and P1B 67.615 g, with fixtures and reference meshes at 0 g.
- **Joints:** six new random P1B joint configurations give no non-press interference, every pin stays in its bearing, and the joints reset to 0°.
- **Regeneration:** a clean regeneration of both designs passed every new gate and produced byte-identical exports. The manifests match, and the plates regenerate byte-identically.
- **Plate gates:** on a throwaway copy, the plate tool rejected a missing P1B export and an altered export.
- **Local reserves:** the 0.32–0.36 mm "local reserves" are the coaxial pivot running faces (inner X pin junction to outer X bearing junction 0.41 mm; outer Z post to pole hub 0.50 mm). The ring bands are 9.5 mm apart.

**Additional concern:** the 1100 mAh pack sits only 0.40 mm below the M2 nut envelopes, with the gap provided by a 3 mm foam pad. Strap tension that compresses the foam by more than 0.4 mm would press nut corners into the LiPo pouch. Before using the 1100 mAh pack, use a firm pad, add a thin rigid shield, or increase `battery_gap`.

**Notes:**
- The exports record hashes of both generators, so editing either one requires regenerating both designs before plating.
- Run each generator in its own MCP call: running both in one call exceeded the tool timeout.

## 2026-10-08 — Plan ground-Pi navigation and prepare a Codex handoff

**User request:** inspect how autonomous navigation could work, evaluate FPV-to-ground-Pi processing and an offered Intel depth-camera area map, then put the discussion and implementation plan in the docs for another session.

**Added:** [navigation plan](20-semi-autonomous-navigation.md) and [copyable handoff](21-navigation-codex-handoff.md), linked from the index/software/priorities/simulation docs. The arrival worksheet now records pending navigation hardware, calibration and capture/survey questions.

**Plan:** N0 hardware/milestone selection; N1 measured live Pi capture; N2 verified yaw-only output; N3 calibrated marker/map localization without flight commands; N4 mapped guidance while the pilot flies; N5 optional later automatic movement with a documented authority decision and sensing/controller/physical-loss gates. N3/N4 advisory work can proceed without a complete physical bridge.

**Source findings:** current code implements HSV image-error tracking and bounded yaw, with no aircraft pose/velocity or verified trainer output. Camera timestamps reflect host read; existing latency tooling excludes downstream response. The simulation's velocity/altitude controller uses exact virtual state. A room scan does not provide live aircraft localization. Recommend a small surveyed AprilTag experiment and metric map registration; exact Pi/Intel-camera/FC firmware and map files remain pending. MSP override is an unselected research alternative with version-dependent loss behavior and no implemented transport.

**Scope:** documentation/planning only; no runtime/firmware/CAD change, flight-authority expansion or hardware acceptance. Preserve the manual/live-tracking demo, P1A-first physical gates, contingency reserve, freeze and deferred Pico audio/toImplement. Source snapshots and prior evidence remain unchanged.

## 2026-10-08 — Nut shield, test plates and print/test plan

**Battery protection:** The 1100 mAh pack sat 0.40 mm below the M2 nut envelopes, held off only by compressible foam. A printed 0.8 mm PETG `nut_shield_plate` (24.5 × 63.8 mm, 1.59 g) now sits between the foam pad and the pack in both designs (`battery_shield_t`). The nuts sit 0.40 mm above the shield, so a fully squashed pad lets the nuts reach only the shield. The 1100 mAh pack is now 1.2 mm from the nuts with the shield between them. The packs moved down 0.8 mm; CG and swept radius include it. P1A regenerated with 0 interferences. P1B regenerated with every gate passed: 612 swept poses with 0 collisions, connectivity, camera clear at nominal, and only the six pin press fits. Estimated accounted mass: P1A 117.10/139.10 g, P1B 144.87/166.87 g (450/1100); P1B/1100 has 8.13 g headroom.

**Printing:** Hub plates now use 7 mm part spacing so 3 mm brims do not merge. A new `plate_T_cage_section_test` (10 three-way hubs) supports a hexagon + pentagon test before the full hub batch. `cad/apex2-cage/PRINT_AND_TEST_PLAN.md` gives the print order, FlashPrint starting settings for the Monoprice Voxel with Creality PETG, step-by-step tests with provisional pass criteria, the measurement list and a thrust-test procedure. Monoprice's Voxel guide lists a 240 °C extruder maximum, a 100 °C bed maximum and FlashPrint-only `.gx` files. PLA/ABS are its recommended materials, so treat PETG settings as untested starting points.

## 2026-10-08 — Voxel bed limited to 60 °C (user)

The user reports that their Monoprice Voxel bed reaches only 60 °C. Monoprice's guide lists 100 °C, but the user's machine governs. `PRINT_AND_TEST_PLAN.md` now uses a 60 °C bed for Creality PETG. It compensates with glue stick on an IPA-cleaned plate, a 10–15 mm/s first layer at 240 °C with slightly more squish, the fan off for the first 3 layers, 3–5 mm brims (including the ring quarters), and a closed enclosure heat-soaked for 5–10 min. T1 doubles as an adhesion test before any further printing. No CAD geometry changed.

## 2026-10-08 — Complete the measurement and test coverage

Every generator parameter marked MEASURE, FIT COUPON or SETUP was cross-checked against `PRINT_AND_TEST_PLAN.md`. The plan was missing several items, now added:
- **Aircraft:** motor bell size, prop top height, frame plate thickness, arm width, column height and hole pitch, camera bracket size, VTX antenna element and its mount location, battery lead lengths and pin length.
- **Weights:** printed parts, strap, foam and screws, plus the finished drone with each pack.
- **Fit mapping:** an explicit table mapping T0–T3 results to CAD values (`rod_bore_clear`, `m2_tap`, `bearing_seat_clear`, `pin_press_d`, `socket_depth`).
- **Decisions:** a section for the three user decisions (pins, rod bonding, camera tilt).
- **Post-build tests:** the P1A contact/endurance gate, gimbal ring stiffness and free spin, gimbal balance and rolling.

Only `cam_hfov` remains a published value (not practical to measure). The assumed densities are calibrated by weighing printed parts.

## 2026-10-08 — Motion physics and throttle estimates

Added `cad/apex2-cage/motion_physics.py` (numpy only) and [docs/22-motion-physics.md](22-motion-physics.md). It computes:
- hover throttle, T:W, climb, tilt, acceleration, speed and endurance for P1A/P1B with both packs;
- P1B ground rolling from the convex hull of the actual 62 hub positions (tip angles 20.5–23.3° on hexagons, 16.1–19.7° on pentagons, 4–12° on pole triangles), using the start condition T/W ≥ sin α / sin(θ + α);
- gimbal torques and contact energy.

Planning results at 350 g thrust (throttle assuming thrust ∝ throttle^1.3–2):
- **Hover throttle:** P1A + 450 43–58 %; P1B + 450 51–64 %; P1B + 1100 57–69 %.
- **P1B rolling at 30° tilt:** 29–49 % throttle to start, 11–26 % to keep rolling; it lifts off above 57–74 %.
- **Endurance:** P1B + 450 estimated at 2.9–5.9 min, so the 3-minute gate is not assured.
- **Contacts:** a glancing 1 m/s contact can rotate P1A about 75° before the FC stops it, while P1B passes only bearing friction to the aircraft.

All values are estimates. The static thrust curve, weighed mass, measured hover throttle and floor friction replace the inputs.

## 2026-10-08 — Rolling dynamics, and a fix to the gimbal fit coupon

**Rolling physics.** Added `cad/apex2-cage/rolling_physics.py` and §2.2–2.3 of `docs/22-motion-physics.md`. The model:
- simulates the real 62-hub cage tipping face to face, with inelastic hub impacts and hop/skid detection;
- covers coasting, slopes, steps, turning and rolling power;
- adds a constraint-torque model of the two rings while the cage rolls.

Estimated findings:
- **Clean rolling happens only in a narrow band just above the tipping threshold** (about k = 0.50 at 30° tilt). It reaches 0.4–0.6 m/s within about 12 cm, then skids, because thrust unloads the hubs.
- **Above the band it slides and tumbles and keeps accelerating**, so speed is controlled by the pilot.
- Each landing loses about 48 % of the kinetic energy and jolts the centre about 0.25–0.3 m/s. The path wanders 20–40°.
- Rolling at 0.5 W uses about 35 % of hover power.
- **Gimbal coupling:** typical ring torque on the aircraft is small (0.1–1.3 N·mm at 0.3–1 m/s). However, 25–45 % of cage revolutions pass near gimbal lock with a peak above the aircraft's ~48 N·mm control authority. Ring inertia is comparable to the aircraft's, so expect twitches; roll at ≤0.5 m/s. All of this is unmeasured; verify with blackbox gyro logs during the P1B rolling test.

**Coupon defect** (found from the user's screenshot). The `gimbal_fit_coupon` vertical pin holes (top step, 6 mm deep from z = 10) ran into the horizontal pin holes (z = 5), so neither tested its full press depth. Fixed:
- step raised to 13 mm;
- horizontal holes at z = 4, vertical holes ending at z = 7, leaving a 2 mm wall.

P1B was regenerated (all gates passed: 612 poses with 0 collisions, connectivity, materials) and saved. `plates_p1b` was rebuilt. A ray-cast check of the exported STL confirms solid material between every hole pair. The coupon is now 47 × 22 × 13 mm, 12.9 g.

## 2026-10-08 — Edge rods set to exactly 44.50 mm (user)

The user asked for a round rod length. `rod_cut_len` is now the **driving parameter at 44.50 mm**, and the cage size is derived from it:
- cage_edge = rod + 2 × (hub_arm_len − socket_depth) + 2 × rod_end_gap = 49.00 mm;
- cage_vertex_r = 49.00 × 2.4780 = 121.42 mm;
- cage_outer_dia = 247.85 mm (target 245–250).

Previously the rod length was an output of the 248 mm target (44.53 mm).

The pole rods follow from the geometry at **37.83 mm** (previously 37.86). `migrate_parameters()` rewrites the stored expression chain in existing documents in an order that never forms a circular reference.

Both designs were regenerated with every gate passing:
- **P1A:** 0 interferences; continuous prop-to-cage bound 34.55 mm.
- **P1B:** 612 poses with 0 collisions; connectivity and materials pass; pivot reserves unchanged at 0.321/0.359 mm; pole posts adapted (tip at 113.42 mm).
- **Mass:** P1A 117.08/139.08 g, P1B 144.86/166.86 g.

P1A was exported a second time because a comment edit to `build_p1b.py` after the first export invalidated its provenance hash. The plate tool caught it as designed.

All plates were rebuilt. The jig STL blade slots measure 44.50 and 37.83 mm from the stop wall. The motion-physics inputs were updated (cage radius 123.92 mm); the results change by under 0.1 mm or 0.1 %.


## 2026-10-08 — Implement navigation and repeatable D435 mapping (user)

The user explicitly authorized software implementation, superseding the previous navigation handoff’s planning-only wording, and requested repeatable mapping toward an autonomous demo. Implemented N3/N4 software in active top-level `software/`: calibration/distortion correction, AprilTag/aircraft pose, versioned validation, freshness/ambiguity/outlier/reacquisition guards, conservative swept-envelope 3D planning, independent worker, engine/API/browser/native guidance, session recording and deterministic replay. Automatic waypoint movement is an estimated-vision **mock** plant, including loss/reacquisition/deliberate restore, bounded speed and continuous clearance. A labeled simulation copy lets it use a rebuilt real-map bundle without modifying that source artifact.

D435 mapping uses registered stationary captures and explicit surveyed camera transforms. Saved depth manifests, hashes/settings and conservative observed-free/occupied/unknown reconstruction support repeatable rebuilding. Continuous clearance checks the union of adjacent observed-free boxes, avoiding the false rejection caused by individually eroding thin reconstructed voxel slabs; any unknown fragment still blocks the swept envelope, with fragmentation/work limits. No handheld SLAM/unknown-space filling, invented calibration, station pose, hardware measurement or completed room map was added. Invented fixtures and schemas are explicit. Real capture/holdout experiments and physical N3/N4 acceptance remain pending; commands/contracts are in [doc 23](23-navigation-software.md).

The user corrected the equipment to **Raspberry Pi 5 and Intel RealSense D435**, and clarified the Specter onboard VTX supplies transmission, with the **RC832 receiver** feeding composite capture. Remaining hardware/firmware/capture/trainer details stay in the arrival worksheet. Python >=3.13 remains required; the inspected pinned pyrealsense2 release has no CPython-3.13 ARM64/macOS wheel. SDK/device use is optional and requires a supported capture host or verified Pi build, not an assumed install.

Physical computer authority stays yaw-only; pilot owns roll/pitch/throttle/ARM-DISARM and independent takeover. Navigation has no bridge output path. No trainer output, flashing or new physical channel authority was enabled; internal ACKs remain internal state. Preserve existing deadlines/disabled/mock startup/manual fallback, fixed-cage-first gates, $200/$30 budget rule, feature freeze and deferred Pico audio/toImplement. Current source tests/evidence are linked in [verification](15-verification.md) and [navigation evidence](../evidence/navigation/README.md); Mac/offscreen/synthetic/fake SDK results are separate from unperformed Pi/D435/aircraft checks.


Navigation completion evidence for this decision: **4,380 Mac desktop tests / 98.15% combined coverage**, **3,997 Mac headless tests / 99.13%**, zero failures/errors/skips, all module gates and unchanged-source checks. There are 178 navigation/mapping/latency-stimulus cases. Chromium operator/isolation and desktop/phone checks pass; replay and saved synthetic depth-map reconstruction/demo are byte-identical across two runs. The synthetic map-backed mock reaches its goal with loss/reacquisition/restoration exercised. No Pi/D435 device or physical check was performed. [Completion audit](../evidence/navigation/software-final-2026-10-08/completion-audit.json) and failed development coverage history are preserved.

## 2026-10-08 — Build only the P1B gimbal cage; P1A stays CAD-only (user)

**Decision.** The user will not build the fixed cage (P1A) and will build the two-ring gimbal version (P1B). P1A remains in Fusion and in its generator as a reference. Its generator still produces the shared T1 socket fit strip and rod jig.

**Gate.** The former fixed-cage gate (ten consecutive low-energy contacts without damage or prop strikes, at least three minutes usable caged flight, repeatable manual recovery) now applies to P1B before demo use. Updated accordingly:
- `AGENTS.md`;
- docs README, 01, 03, 05, 08, 10, 11, 12, 13, 15, 17, 20, 21-handoff, 22 and 25;
- the CAD README and `PRINT_AND_TEST_PLAN.md`.

**Consequences, for the record:**
- There is no fixed-cage fallback.
- The first flights are on the heavier configuration: an estimated 144.9/166.9 g, T:W 2.42/2.10 at the 350 g planning thrust, 8 g of headroom with the 1100 mAh pack.
- The free gimbal adds the gimbal-lock coupling risk described in docs/22 §2.3.
- Recommended (not yet decided): fly the first hovers with the rings zip-tied to the cage (equivalent to a fixed cage), then free them.

**Plates.** `make_plates.py p1b` now also produces `p1b_plate_T_cage_section_test`, `p1b_plate_hubs_3way_a` (36 hubs) and `p1b_plate_hubs_mixed` (10 three-way, 4 mount, 10 four-way). With the junctions plate's 2 pivot pole hubs, that is all 62 hubs. The new print order is T0, T1, T2, T3 (P1B), T4 (the real P1B carrier/arms plate), H1, H2, G1 ×4 and G2: about 8.5–15 h and 90 g.

## 2026-10-07 — Pack count and Amazon sourcing (merged from the repository copy, 2026-10-08)

Two decisions recorded only in the `simulation/` git copy (commits `bb37b70`, `d31a780`) are now in the maintained docs as well.

- **Pack count:** the 1100 mAh product title says one package includes two batteries, matching the two physical 1100 mAh packs in the six-pack inventory. Keep package quantities separate from battery counts.
- **Sourcing:** the BOM is complete and planned purchases come from Amazon. Amazon links are sourcing references pending listing, price, stock and order checks. The HGLRC Specter AIO row has no Amazon ASIN until an exact match is confirmed.

## 2026-10-08 — Manual fallback screen, operator safety, camera tools, Mega sketch, CAD kit and demo records (user goal)

**Requested:** clean up the repository and docs, build the demo software, port the bridge to the Mega, prepare CAD measurement and test tools, fix the simulator checks, and write the judging and test records. The main CAD generators and their inputs were not to be changed. A pasted audit of 54 findings was folded in where it applied outside those files.

**Software (top-level `software/`):**

- **Fallback screen:** `/fallback` and the native **Manual fallback view** show the video with the target box, a centre/error indicator and the server's `steering_status`, "Manual steering — computer steering unavailable". The text stays until a bridge declares verified physical output; none does.
- **Live video in the app:** the native workstation never displayed camera or recorded video before this fix (`show_signal` was never set). Stale video is now marked separately from the server connection.
- **Operator lease:** API-enabled assistance falls to FAULT/neutral 1.5 s after the last heartbeat. Browser commands are serialised so a disable cannot be overtaken, and Lock requests neutral first.
- **Camera faults:** frozen (bit-identical) or blank camera pictures for 0.5 s are a source fault, and unplugged cameras are reopened without re-enabling.
- **Detection safety:** target jumps restart acquisition, detections made with replaced settings are dropped, and logging failures never stop control.
- **Worker health:** `/api/health` reports worker liveness.
- **Session data:** session timing is per processed frame; summaries and replays record the final source, settings and source kinds.
- **Recordings:** they play at their own frame rate.
- **Visitor sandbox:** one trace is generated at a time.
- **Camera tools:** `serve --camera`, `cameras`, click-to-pick HSV thresholds and a flash-to-detection `latency` tool.
- **Mega handshake:** HELLO is repeated until READY, because opening the Mega's port resets it.

**Mega bridge:** [`firmware/mega/ball_bridge_mega`](../firmware/README.md) reuses the C core plus a new shared line reader.

- It compiles for the ATmega2560 (5,456 B flash, 600 B RAM).
- Its tests pass as simulated AVR firmware (simavr) and under Linux ASan + UBSan.
- It drives no pins and has no trainer output.

**Deployment:**

- Supported OS is 64-bit Raspberry Pi OS Trixie on a Pi 4 or 5. Bookworm cannot install the locked numpy, which needs Python 3.12 or newer.
- A preflight stops the installers before any change.
- The service account gets the camera and serial groups, and recordings live in `/var/lib/ball-drone/recordings`.
- The real installer passed in a Trixie ARM64 container and was refused on Bookworm. That is not a Pi.

**CAD kit** ([cad/kit](../cad/kit/README.md)), which reads the generators without changing them:

- the measurement form and checker (rejects unknown names, units and ranges);
- bend-test blocks, jig, load hook and pin gauge reproducing the 35.03 mm exposed span;
- the opening probe: objects under ~84 mm pass a hexagon and can reach the props, and a 90 mm object stops 2.9 mm from the P1A props;
- P1B mass options: 166.9 g accounted with the 1100 mAh pack, so 174.9–176.9 g with unweighed extras. **Recommendation: fly P1B on the 450 mAh pack.**

**Open CAD decisions settled** ([note](../cad/kit/decisions-2026-10-08.md)), each matching the current model and open to override:

- **Pins:** cut to 10.5 mm. A full 16 mm pin would reach within 0.5 mm of the outer ring.
- **Rods:** dry fit, bonding only joints that fail.
- **Camera:** keep 20° uptilt.

**Simulator:**

- The smoke test is rewritten for the free-flight game.
- The physics runner asserts its results; the Node deprecation is removed.
- Telemetry is rendered as text, and a failed level load returns to the working level.
- The industrial map has numbered leak/overheat/blockage inspection markers. Frame rate is unchanged (Apple M4: 30–37 fps before, 35–37 after).

**Demo and records:** [judge script](24-judge-script.md) and [physical test records](25-test-records.md), with `tools/thrust_log.py`, `tools/gate_check.py` and CSV forms. The recovery rule is a proposal: every counted contact must be recovered.

**Repository:**

- `tools/sync_to_repo.sh` copies this folder's maintained directories into the `simulation/` git checkout, excluding runtime data, tokens and virtual environments. It does not commit or push.
- `.gitignore` covers `runs/` and operator tokens anywhere.
- The simulator's auto-commit refuses to stage private files.
- Verification fingerprints cover browser assets and deploy scripts.

**Not changed, by instruction:** the main CAD files. Audit items that need them stay open:

- unknown measurement names silently ignored inside the generators (the kit checker covers the input side);
- the exact 1 mm rod gate in `validation.py`;
- regeneration deleting components before inputs are validated;
- P1A exporting before its mass gate;
- export manifests without effective parameter values.

**Evidence:** [fallback browser checks](../evidence/fallback-2026-10-08/browser-fallback-checks.json), [Pi containers](../evidence/pi-install-2026-10-08/), [Mega simulation](../evidence/firmware/mega-avr-simulation-2026-10-08.txt), [simulator smoke](../evidence/simulation-smoke.json) and the [verification index](../evidence/verification/README.md). Nothing here was run on a Pi, camera, Mega board, radio or aircraft.


## 2026-10-08 — Publish the completed project to GitHub (user)

The user requested pushing all changes to the existing `WasimVorvoi/HackPHS` repository. Prepare an isolated publishing checkout from current `origin/main`, preserve the simulator at repository root and its local fixes, and integrate maintained top-level software/firmware/docs/CAD/evidence/tools. Keep the original development workspace and older copies intact. Preserve simulator README instructions alongside the new navigation runbook. Exclude credentials, runtime runs, environments and build caches; include checksummed verification artifacts even when generated HTML ignore rules would omit them.

The user confirmed the D435 only scans before the demo; the scanner may be disconnected after map registration. During mapped guidance, FPV/AprilTags supply localization. The integrated publishing snapshot passes 4,395 Mac desktop tests (98.15% combined coverage; no failures/errors/skips), module/source-integrity gates, UBSan and internal-only Mega compilation; simulator Node physics checks pass. Physical channel authority, trainer gates, fixed-cage-first, budget/freeze and deferred scope remain unchanged. No firmware flashing or physical output was enabled.

## 2026-10-08 — Ring quarters: one plate per ring

The user asked whether 4 quarters fit on the Voxel. Measured on the exported meshes, thin arcs nest when stacked along the arc bisector: 4 inner quarters take 106 mm and 4 outer quarters 116 mm at a 4 mm part gap. All 8 would take 141 mm, beyond the 140 mm usable area. `make_plates.py` therefore stacks each ring's quarters at a 13 mm step (`DIAGONAL`):
- `p1b_plate_inner_ring_4_quarters` is 109 × 109 mm;
- `p1b_plate_outer_ring_4_quarters` is 119 × 119 mm;
- the measured gap between neighbouring quarters is 5.2–5.3 mm.

These two plates replace `p1b_plate_ring_quarters_PRINT_4X`, which had to be printed four times. The print plan now lists G1a and G1b.

## 2026-10-08 — P1B mass breakdown, realistic all-up estimate and glue guidance

Recorded in the CAD README (the "P1B build" weight section and open decision 3), docs/22 and the print plan.

**Accounted CAD mass** is 144.9 g (450 mAh) and 166.9 g (1100 mAh):

| Group | Mass |
| --- | --- |
| Aircraft listing | 44.8 g |
| Cage | 24.8 g |
| Rings and junctions | 25.3 g |
| Mount | 15.7 g |
| Hardware allowance | 8.4 g |

The generator counts screws at 0.20 g each and leaves out nuts, washers, strap, foam, XT30 lead, antenna and extra wiring.

**Realistic estimate** (unweighed): about 154–160 g with the 450 mAh pack, and about 176–182 g with the 1100 mAh pack, likely over the 175 g limit.

**Ways to save weight** (all untested):
- nylon M2 screws on the 16 ring splices (about −4 g);
- shortest screws (about −0.07 g each);
- pins cut to 10.5 mm (about −0.8 g);
- a lighter strap.

Steel screws stay on the carrier, frame and arms.

**Glue guidance** for open decision 3 (still the user's choice):
- Build T3 dry. Leave the cage unglued if it passes the pull-out and drop tests.
- Otherwise use medium CA or 5-minute epoxy with the next-looser socket. Glue adds about 1–2 g over 200 rod ends.
- Replace hubs rather than trying to remove glue. Heat and acetone soften PETG.

The print plan now asks for 10 screws and 10 nuts to be weighed together.

## 2026-10-08 — Hover/roll T:W minimums, flight time and impact survivability (estimates)

Added to [docs/22-motion-physics.md](22-motion-physics.md) §1 and new §5, with the impact numbers reproducible in `motion_physics.py`.

**Thrust-to-weight:**
- **Hover:** 1.0 is the theoretical floor, ~1.5 the practical minimum (redesign trigger), 2.0 the target.
- **Roll (P1B):** 0.40 × weight at best tilt (sin 23.3°), 0.49 at 30° tilt; 0.10–0.14 keeps it rolling.

**Flight time** with realistic mass:
- 450 mAh: about 2.6–5.2 min hovering, ~7–15 min mostly rolling.
- 1100 mAh: about 5.1–10.5 / ~14–29 min.

**Impact (assumed carbon rod at 120 GPa / 1500 MPa / 1.25 %, PETG yield ~50 MPa):**
- A rod breaks at about 13–26 N side load (27–82 mJ); the cage absorbs ~0.08–0.74 J near a struck hub.
- Deceleration in a drop ≈ drop height ÷ stopping distance.
- The inner ring stays level with the aircraft, so flat landings bend it out of plane. It is estimated to yield above ~12 g, i.e. flat drops of about 25–35 cm onto a hard floor. This corrects an earlier chat estimate of 0.5–1 m.
- Side hits stay below yield to about 36 g.
- Expected results: ≤1 m/s contacts survive; 2–3 m/s risks sockets, rods and splices; ≥1 m drops likely cause damage.

**Advice:** ≤1–1.5 m/s near walls and gentle landings.

**Tests added to the print plan:** a 50 cm T3 drop; a full-cage drop with a ~110 g dummy weight from 10/20/30/50 cm; stepped contact speeds after the gate.

**If the rings prove weak:** `ring_t` 3 → 4 mm (about 1.8× out-of-plane strength, +4–5 g).

## 2026-10-08 — Follow-up: P1B weight decision, solid clash check, simulated bend test, Pi acceptance

**User decision:** no lightening of P1B. It keeps the current design and both packs; the user judged the 1100 mAh configuration only slightly past the target (about 2.1:1 thrust-to-weight at the 350 g planning thrust). Pin length, rod bonding and camera tilt keep the recommended defaults in [`cad/kit/decisions-2026-10-08.md`](../cad/kit/decisions-2026-10-08.md) until the user confirms or overrides them.

- **Solid clash check** ([`cad/kit/clash_check.py`](../cad/kit/clash_check.py)): built from the 62 exported hub meshes and 100 rods. The cage never intersects the travel-grown P1A prop volumes (nearest 38.1 mm) or the P1B swept sphere. Balls up to 84 mm pass a hexagon and reach the props; a 90 mm ball rests 3.05 mm from them (rod-only model: 2.9 mm, conservative). Every size tested can touch the P1B outer ring.
- **Simulated bend test** ([`cad/kit/bend_simulation.py`](../cad/kit/bend_simulation.py)): the jig assembly passes a solid fit check. It found and fixed a load hook too tall for the jig; the channel is now deeper, giving 8 mm of deflection room. Predicted 200 g readings are 0.22–1.28 mm (fixed to pinned) at most 44 % of typical strength.
- **T3 and the jig:** the other session's T3 cage-section plate is complementary — T3 for pull-out and drops, the jig for measured stiffness and set. The jig's 100 g prediction (≤ 0.64 mm) sits well inside T3's 3 mm sag limit.
- **Mega in simavr:** the run now includes the forced-failure self-test, which the simulator reported as failed, as it should ([evidence](../evidence/firmware/mega-avr-simulation-2026-10-08.txt)).
- **Pi:** Raspberry Pi-specific Docker base images are no longer published, so ARM64 Trixie containers remain the furthest check possible without a board. `software/deploy/pi-acceptance.sh` records the on-device checks when the Pi 4/5 is available.
- **Design change absorbed:** the kit now follows the 44.50 mm rod change from the parallel session (35.00 mm exposed span, 49.00 mm hub spacing). 39 kit tests pass.

**User confirmations (2026-10-08, later):** rod joints are dry fit, bonding only joints that fail the T3/bend tests. Camera uptilt stays at 20°, the angle the P1B centreline check passed. The merged commits in `simulation/` stay local; the user pushes when ready. The pin choice is open: cut the 16 mm stock to 10.5 mm, or buy 2 × 10 mm dowels.

**User confirmations (2026-10-08, final):**

- **Pivot pins:** cut the 16 mm stock to 10.5 mm, as the CAD models them, using the printed gauge and the method in [the decision note](../cad/kit/decisions-2026-10-08.md).
- **Rod/hub tests:** keep both T3 (pull-out and drops) and the bend-test jig (measured stiffness and permanent set).

All three open CAD decisions are now settled: 10.5 mm pins, dry-fit rods, 20° camera.

## 2026-10-08 — Merged project pushed to GitHub (user)

At the user's request, the merged project was pushed to `WasimVorvoi/HackPHS` `main` (merge `e64aab1`). The remote held a newer commit, `cbf864d`, which was an earlier snapshot of this folder. It was merged, not overwritten:

- **Maintained folders** take the current versions, including the P1B-only scope decision.
- **`README.md` and `AGENTS.md`** keep the published-repository wording. `tools/sync_to_repo.sh` no longer copies `AGENTS.md`.
- **Tests:** 4,405 tests, the simulator physics checks and 39 CAD-kit tests pass on the merged tree.

## 2026-10-08 — Raspberry Pi preflight script line endings

Using key-authenticated SSH, the actual Pi was identified as a Raspberry Pi 5 Model B Rev 1.0 running aarch64 Raspberry Pi OS/Debian Trixie, Python 3.13, with 4045 MB detected. The home-directory copy of `pi-preflight.sh` had CRLF line endings; `bash -n` reproduced the `in\r` syntax error. A timestamped backup was retained and trailing carriage returns were removed. Five other transferred deployment scripts also had CRLF; each was backed up and normalized. All deployment scripts passed `bash -n`. A root `.gitattributes` rule now enforces LF for shell scripts, and the current Windows deployment-script working copies were normalized to LF. The preflight passed; the installer completed, `ball-demo.service` is enabled/active, and `/api/health` is healthy in MANUAL/mock mode. As `ball-demo`, OpenCV/V4L2 read 30 640x480 frames from `/dev/video0`, all uniformly black. The app reported FAULT/stale frame while disabled at yaw zero; therefore capture-device access works but a live RC832 picture remains unverified. No Mega serial device was present. See [Pi evidence](../evidence/physical/pi-preflight-2026-10-08.txt).

## 2026-10-09 — Flutter operator UI scope and backend handoff (user)

**Decision:** Plan Flutter desktop and Android operator apps with distinct layouts, replacing the current browser and native Qt operator interfaces when ready. The app is an operational client, not a judge-only demo or simulator. The screen map, UI decisions, lifecycle states, and backend contract are in [UIDEVPLAN.md](../UIDEVPLAN.md).

**User-confirmed UI scope:** camera streaming; two-way audio and ElevenLabs TTS; prepared-roster person selection for AprilTag following; high-level follow Start/Stop/Abort; landing-target selection from live video, including an arbitrary visible point and AprilTag-aided mode when supported. The operator selects a prepared roster entry rather than entering a free-text name. Flutter has no direct joystick, axis, or continuous position controls; the pilot retains transmitter control.

**Audio clarification:** audio is part of the intended Flutter integration despite older broad deferral language. One audio device handles mic/speaker and possibly LED functions, but ESP32/Pico/Pi Zero, power, transport, and backend are unresolved. The initial UI plan uses push-to-talk plus incoming audio and a TTS composer; this interaction can be revisited after the hardware and transport are selected. This does not claim working audio hardware or a completed backend.

**Scope boundaries and conflicts:** the current source documents only yaw-only verified assistance and advisory navigation; following and landing are planned UI missions that need explicit control-authority documentation and physical safety gates before aircraft execution. The separate industrial simulator stays separate. Collision-tolerance behavior is undefined, and interactive CAD is a later TODO pending measured geometry and a request. The Pico-specific wireless implementation path and `toImplement` source tab remain deferred; the audio UI requirement does not select Pico or imply that the hardware feature is implemented.

**Affected files:** `UIDEVPLAN.md`, `docs/README.md`, `docs/04-software.md`, and `docs/14-desktop-app.md`. This is a new authored plan, not a Google Doc tab, so it has no source snapshot.

## 2026-10-09 — Flutter screen planning and visual review

**Decision:** Use text-first annotated compositions and explicit interaction/state walkthroughs as the Flutter UI source of truth. Flutter renders at real window constraints will validate hierarchy and responsive behavior; generated images may inform art direction only. Keep phone and desktop compositions distinct while sharing typed state and task behavior.

**Design rules:** Apply the user's UI dossier: restrained tokens and surfaces, clear action hierarchy, contextual controls, useful failure/recovery states, concise operational copy, accessible input, and no unsupported metrics or decorative filler. Record state and backend ownership before polishing.

**Affected file:** [Flutter UI development plan](../UIDEVPLAN.md), including responsive review, state walkthroughs, and anti-vibe acceptance checks.

## 2026-10-09 — Implement pre-camera navigation software plan

**Decision:** Implement the software work that can be advanced without the camera, including the user's requested automatic D435 station registration from surveyed AprilTags. Keep work advisory-only and keep physical camera/Pi/aircraft acceptance pending.

**Basis:** User approved the implementation plan and specifically chose automatic tag-based station registration. The project `AGENTS.md` retains manual startup, disabled/mock defaults, direct neutralization on fault/loss, and no trainer/GPIO output before protocol/electrical verification.

**Result:** Added synthetic depth/RGB/checkerboard data; shared calibrated camera pose and automatic stationary D435 registration; map/route/arrival/mission integration; private snapshot saving; native/browser actions; a bounded estimated-vision mock follower; and a CLI-to-app offline workflow. The software route remains advisory and requires two surveyed tags throughout the view path.

**Evidence:** The Qt desktop profile passed 4,547 tests with zero failures, errors or skips and 97.95% overall coverage; all configured module floors and both firmware sanitizer checks passed. The report is [`20261009-pre-camera-desktop-02`](../evidence/verification/20261009-pre-camera-desktop-02/report.json). The final core profile passed 4,162 tests with zero failures, errors or skips and 98.50% overall coverage; all configured module floors and sanitizer checks passed. Its report is [`20261009-pre-camera-core-04`](../evidence/verification/20261009-pre-camera-core-04/report.json). One intervening run recorded a portable firmware sanitizer exit `-11` with no diagnostic; a direct rebuild/run and the later full profile passed, and the failed report is retained. Arduino Mega compilation was unavailable because `arduino-cli` is not installed. See the [implementation record](26-pre-camera-software.md) for exact status.

**Limits:** No D435, Pi, transmitter, aircraft or flight test was used. Real registration, room mapping, FPV calibration, Pi performance and any physical flight assistance remain pending. The source Google Doc snapshot was not overwritten.

**Affected files:** Active top-level `software/`, generated navigation schemas/examples, `docs/23-navigation-software.md`, `docs/26-pre-camera-software.md`, verification evidence, and this log.

## 2026-10-09 — Extend backend mission and status behavior (user)

**Decision:** Add the non-UI backend contract for mission readiness, high-level follow/landing requests, and result reconciliation. Keep every physical mission operation disabled until its sensing, control, override and failsafe path is verified.

**Result:** Added read-only `/api/mission/status`, bearer-token-protected command and result routes, strict request validation, bounded process-local idempotency, explicit capability/subsystem status, and clear rejected outcomes. Inspection missions now surface designated AprilTag loss and reacquisition while resetting arrival progress. Their marker-based status remains separate from person-follow and physical missions. Full verification exposed a mismatch with the project instructions: the Mega sketch contained an unverified PPM generator. Restored the shared internal-state-only protocol core, removed the Mega PPM generator, and made the serial host reject `PPM_YAW`; the mission-status capability stays unverified until physical checks. No aircraft command path was added.

**Evidence:** Focused mission/runtime/bridge/Mega regressions: 120 tests passed; `mission_control.py` statement/branch coverage is 100%. Final core profile: 4,175 tests, zero failures/errors/skips, 98.51% coverage. Final Qt desktop profile: 4,560 tests, zero failures/errors/skips, 97.98% coverage. `engine.py` is 99.40%; `mission_control.py` is 100%. Both final profiles pass all module gates and UBSan checks with unchanged source hash. A default ASan profile attempt exited `-11` without a diagnostic; the exact portable core check passed directly, with its evidence and the intermittent line-reader runtime behavior preserved separately. See [verification](15-verification.md) and [implementation record](26-pre-camera-software.md).

**Affected files:** Active backend/API and mission state, browser/native mission-state validators, Mega bridge/firmware no-output boundary, focused regressions, the verification coverage gate, and the maintained navigation/software documentation. The Google Doc source snapshot was not modified.
## 2026-10-09 — Push completed work directly to main (user)

The user requires all completed work, including UIDEVPLAN.md and future Flutter changes, to be pushed directly to `main`. Integrate existing remote work without requiring the user to manage branches or merges.

## 2026-10-09 — Flutter operator app implemented and audited (user)

**Authorization:** execute the complete UI workflow; finish code before browser/emulator inspection; audit and improve the rendered UI; push completed work directly to main. The emulator stays visible for final inspection.

**Result:** Android and desktop/web use distinct compositions and shared typed state/commands. Implemented prepared-roster follow/stop/abort, current-location and captured-point/tag landing review, audio controls/WebRTC client, speech composer/playback states, system/session views, strict auth/freshness/provenance and delayed/unknown outcome handling. Normal startup is disconnected. CAD is a later TODO; simulator/direct flight controls and a judge-only flow are absent.

**Audit:** compact desktop task action, pinned audio dock, clearer camera hierarchy, fewer duplicate labels, focus/keyboard resizing, captured-frame recovery, pending/unknown follow cancellation, retained uncertain outcomes across reauthorization and separate client lease scopes. All choices are in [UIDEVPLAN.md](../UIDEVPLAN.md).

**Evidence:** [build profile](../evidence/verification/20261009-flutter-05/report.json) passes analysis, 79 tests, web, x64 Android and universal phone APK builds. [UI audit](../evidence/verification/20261009-ui-audit-01/README.md) records actual browser checks, a passing emulator workflow and preserved failures/repairs. Real backend, Pi, media devices, ElevenLabs and aircraft operation remain unverified.

**Hosting:** the current plan blocks GitHub Pages for the private source repository. chessdroid108/hackphs-operator-web hosts compiled website files only, on main. Source CI verifies/builds/uploads the web artifact. Source visibility and account plan are preserved.

## 2026-10-09 — Published Flutter web app verified

The operational client and labelled development preview are live at https://chessdroid108.github.io/hackphs-operator-web/ and its preview/ path. Source main commit 8844b2a passes CI 37998164572; compiled-site main commit 11f86dd passes Pages deployment 37998272856. Both routes were opened in the internal browser. Only compiled website files are in the public deployment repository; project source remains private.

## 2026-10-09 — Keep guided D435 room capture separate

**Decision:** Make the room-capture workflow a standalone, me-facing utility. It is not part of the native operator workstation, the visitor UI, or the judged demo.

**Result:** Added a separate Qt app runnable as `python room_mapper.py` from `software/` (also installed as `ball-room-mapper`). It guides the operator through room bounds and tag-survey entry, printable 1:1 AprilTag sheets with a scale check, live D435 preview/marker feedback, one-click 30-frame captures at still positions, automatic tag-based station registration, and map reconstruction/report saving. Each capture and saved manifest remains in a new scan folder. Shared D435 capture callbacks provide the preview/progress/registration updates. The existing native workstation has no mapper menu or dependency on this app.

**Limits:** The app still needs multiple stationary views to cover occluded areas, with at least two surveyed tags visible in each capture. It does not track a moving handheld camera or perform SLAM. The GUI, camera SDK and physical D435/Pi capture have not been verified on hardware. The existing Python SDK/platform compatibility caveat remains; the D435 and app must share a supported capture host. The saved survey is operator-entered and is not independently checked.

**Verification:** 62 focused tests passed. The full desktop profile ran 4,581 tests with zero failures/errors/skips and 96.26% total coverage, but is retained as failed because the Mega line-reader ASan/UBSan process exited `-11` with an empty log; the portable firmware sanitizer passed. See [the preserved report](../evidence/verification/20261009-room-mapper-standalone/report.json) and [implementation record](26-pre-camera-software.md). No physical D435/Pi check was possible.

**Affected files:** standalone launcher and app, D435 capture callbacks, focused tests, [navigation runbook](23-navigation-software.md), [software README](../software/README.md), [pre-camera software record](26-pre-camera-software.md), and this log. The native workstation guide is unchanged. The Google Doc snapshot remains unchanged.

## 2026-10-09 — Use portable visual missions; do not do D435 room mapping

**Decision:** The project/demo will operate in a controlled, previously unmapped space using aircraft FPV and visible AprilTags. The D435 room-mapping workflow will not be done. Preserve the existing D435 app, capture, registration and mapping code plus its evidence, but do not extend it or require it for the demo. The handoff plan's audio item (#5) is excluded from the current software plan.

**Software direction:** Before camera/flight-control hardware is functional, plan server-owned prepared-roster/tag contracts, relative moving-tag tracking using synthetic/recorded data, explicit non-actuating follow and landing lifecycles, deterministic bounded simulation, and later contract wiring to the existing Flutter mission client. Keep arbitrary image-point landing unavailable until ground geometry and sensing exist. Do not add obstacle avoidance or alter physical control authority. The current MANUAL/disabled/yaw-only boundary stays in force.

**Affected files:** [Portable visual missions plan](27-portable-visual-missions-plan.md), documentation index and current scope, plus notices on the retained mapped-navigation plan/runbook/implementation record. No product code or tests were changed; D435 implementation files remain intact. This authored plan is not a Google Doc tab and has no source snapshot.

## 2026-10-09 — Implement portable visual mission software plan (user)

**Scope:** Implement software work possible without functional FPV/flight hardware. Exclude handoff item #5 (audio/TTS), UI redesign, and D435 room mapping. Preserve all existing D435 code. Keep startup MANUAL/disabled, pilot authority unchanged, and all physical follow/landing output unavailable.

**Implementation:** Added a strict private server-owned person/landing-site roster (`roster.py`) and shared AprilTag36h11 detector (`tag_detector.py`). Added map-independent relative tag/pad pose estimation with quality and timing provenance, freshness/loss/reacquisition trackers, and generated-image processing (`target_tracking.py`); refactored fixed localization to share the detector. Added deterministic bounded synthetic follow motion (`follow_simulation.py`) and descent/touchdown/impact modeling (`landing_simulation.py`). Extended the single bounded mission ledger to accept only labeled synthetic lifecycles, cancel pending starts, require reacquisition after loss, and require an explicit synthetic touchdown event. Added optional roster loading to the headless server and mock mission ticking to the existing engine.

Added the versioned Flutter backend adapter in `ui_api.py` over the shared engine/mission ledger. It serves snapshots, bounded immutable still/JPEG frames, request submission and lookup; read-only calls support anonymous access and report authorization false, while commands require the bearer token. It validates strict payloads and frame/session freshness, keeps live follow/landing and image-point landing unavailable, labels mock status and source, and reports audio as unavailable. CORS permits the published GitHub Pages origin by default and accepts configured origins through `BALL_OPERATOR_ORIGINS`.

Updated the portable-missions plan with implementation state and remaining calibration/device gates; clarified the software README, Flutter backend handoff and project index; preserved the retained D435 workflow as out of scope. No Flutter UI files or D435 implementation files were changed.

**Verification:** Focused current suite: 92 passed, 0 failures, with one Starlette/httpx deprecation warning. The preserved full core attempt ran 4,248 tests successfully but failed the coverage gate at 92.75%, missed the then-current `sources.py` and `mission_control.py` module floors, and had an ASan/UBSan portable firmware process exit `-11` without diagnostics. Subsequent focused regressions were added, but the full core profile was not rerun. See [the preserved report](../evidence/verification/20261009-portable-missions-core-01/report.json) and [verification record](15-verification.md).

**Remaining:** Final FPV calibration and exposure-delay bounds, live RC832/capture validation, Pi/browser integration and all physical follow/landing gates. Relative pose services have only generated-image evidence. No autonomous flight or real camera detection is claimed.

## 2026-10-10 — Select the Freenove ESP32-S3 WROOM bridge board (user correction)

**Decision:** The team does not have the previously planned Arduino Mega 2560. The user selected the **Freenove ESP32-S3 WROOM** as the flight-assistance bridge board instead. The Pi-to-board development/serial connection is a separate USB link from the VIXLW video-capture connection; use the board's USB-UART interface.

**Boundary:** This changes the selected hardware only. The existing Mega sketch and Pico scaffold remain historical artifacts. ESP32-S3 firmware/host integration, trainer output, pinout, electrical compatibility, channel mapping, pilot override, watchdog and signal-loss behavior are not implemented or verified. Keep startup MANUAL/disabled/mock, pilot control authority, and all physical assistance gates unchanged.

**Affected files:** [Project index](README.md), [software plan](04-software.md), [hardware plan](05-hardware.md), [BOM](02-bom.md), [reference index](07-refs.md), [build gates](10-build-and-test.md), [implementation status](11-pre-hardware-status.md), [demo runbook](12-demo-runbook.md), [arrival worksheet](13-hardware-arrival.md), [desktop guide](14-desktop-app.md), [firmware README](../firmware/README.md), root `AGENTS.md`, and this decision log. The dated Google Doc source snapshot remains unchanged.


## 2026-10-09 — Whole P1B regenerated with selected coupon fits

User requested finalizing all gimbals/adapters as print-ready artifacts and committing substantive steps. Created baseline commit `aaa7de6` before changing the CAD. `fit_results.json` now supplies coupon-selected print compensation after vendor/measured inputs: rod bore 1.275 mm, M2 pilot 2.00 mm, bearing seat 5.30 mm, horizontal pin hole 2.15 mm and vertical pin hole 2.25 mm. Added orientation-specific pin parameters and explicit mapping: inner X junction horizontal, arm pivot block and pole boss vertical according to their final print transforms. Five focused mapping regressions pass.

The first regeneration exposed an old validation assumption that pin/seat engagement must create nominal solid interference. FDM compensation-selected holes have nominal CAD clearance, so replaced that assumption with exact cylindrical-axis, specified hole diameter and full engagement-depth checks for all six pins and six bearings. Retained ring-to-quarter contact, pin-through-bearing, static collision, prop/support travel and continuous radial checks. Preserved the failed report. Missing or misaligned seats still fail; geometric engagement is distinguished from printed retention.

Modeled the four arm nuts under the carrier and cut their full adjustment envelopes out of the hand-cut foam reference. Both frame and arm nut sets now pass foam and battery clearance tests across adjustment extrema. Full P1B regeneration passed, including 612 swept-motion cases with zero collisions and continuous rigid-CAD radial clearance checks. Saved the Fusion document and native baseline/final archives, exported every part with fit-input source provenance, and regenerated raw P1B plates. Native evidence is in `cad/apex2-cage/review-2026-10-09-finalization/`. Print plates/profiles and final verification remain in progress. Physical caliper dimensions, retention, strength, wiring and flight gates remain pending.

## 2026-10-09 — Increased final pivot running reserve; selected 11 mm cut pins

The fit-only native audit left just 0.32–0.36 mm continuous radial reserve near the pivots. For print tolerance, set the P1B designed axial running gap to 1.00 mm instead of 0.50 mm and regenerated every affected part. Final native validation passes: inner/outer radial reserve 0.911 mm, outer/cage reserve 0.860 mm and prop-envelope/inner-ring reserve 4.315 mm. All 612 swept-motion cases still pass with no collisions, six pin seats engage 6 mm and six bearings seat 2.5 mm. These are ideal rigid-CAD bounds, not measured loaded clearances.

The matching pin stack is now 6 mm press depth + 1 mm gap + 2.5 mm bearing + 1.5 mm tip overhang = **11.00 mm**. Adopt cutting six 2 × 16 mm stock dowels to 11 mm; full-length stock is not the checked geometry. The final guide and cut gauge must use this value. Saved native model and archived the earlier fit-only passing evidence before this change. Raw plates were regenerated; brim-safe final plates are the next step. Physical retention, deformation, hardware dimensions and flight still require validation.

### 2026-10-09 — refresh T3 for the selected T1B fit and save its final profile

User selects T1B rod socket #2 (1.275 mm drawn bore) and M2 pilot #5 (2.00 mm). Refreshed T3 native export from the current P1B parameters; ten hubs in two rows of five pass socket, solid, bed-contact and offline FlashPrint checks. The minimum conservative depositing-path margin is 13.48 mm with a 5 mm brim. Added **Voxel PETG T3 socket 2 FINAL**, preserving the original starter, with 10 mm/s first-layer maximum and 25% brim speed. Installed and backup values pass native Qt readback. T3 has no screw holes. Actual angled-socket retention and section strength remain physical tests.

### 2026-10-09 — complete centered P1B production plates and profiles

All fourteen production designs are packaged as 84 parts on seven plates: H1 split 25+11, H2 mixed, G1a/G1b, G2 adapters/pole hubs and T4 carrier/arms. Added T3 and four regenerated fixtures; the pin gauge now uses 11.00 mm. Every plate is centered, retains native dimensions/orientation, has positive base contact and separate bodies, and passes offline FlashPrint slicing with a package minimum conservative edge margin of 7.59 mm including brim/purge. Twelve additional FINAL profile files are installed and backed up, verified with Qt; original starter profiles remain. All sixteen native ring-splice screw passages are coaxial through the 5 mm joined stack. T4 evidence and the previous checked file are refreshed for the shortened final arms, with prior versions retained. The package verifier compares each placed source mesh, exact quantities, source hashes, slice identity and installed settings. CAD-kit tests pass 45/45; the old 10.5 mm expectation failure is preserved. Corrected T3's shared-edge section count to nine hubs and ten rods (6 + 5 − 1 edges). Physical strength, screw grip, actual-frame fit, head/washer/wire/strap motion and flight acceptance remain open.

### 2026-10-09 — synchronize the illustrative simulator with final CAD

The local model builder now resolves top-level `cad/` and rejects stale native source/export hashes. It includes selected fit provenance and regenerates the final support/ring/hub meshes. Motion mass estimates derive from current native part volumes using the generator's PETG/carbon and hardware allowances; the regenerated asset matches 144.68 / 166.68 g accounted totals within 0.001 g. No physical measurement is added. Headless checks pass after correcting a fixture that placed a wall in the unobstructed-speed case; the wall remains in the separate collision case and numerical assertions are unchanged. Old failure evidence is retained. Browser performance and real aircraft acceptance were not rerun.

### 2026-10-09 — confirm T1B screw-coupon identity

The user confirms #5 was on the combined refinement strip with seven screw holes, so its selected drawn pilot is **2.00 mm**. The alternate standalone five-hole scratch coupon has a different numbering map and is not the source of this selection. The existing final P1B pilot setting therefore remains correct. T3 has no screw pilots. Actual screw grip under load remains a physical gate.

### 2026-10-09 — T4 print readiness rechecked

For the user’s immediate T4 print, reran the source/placement/profile verifier and carrier interface audit: both pass. The final T4 plate contains four flat, separate parts and its matching offline slice retains at least 17.6 mm clearance including the 5 mm brim. The installed **Voxel PETG FINAL T4** profile matches its backup. Corrected the physical-fit procedure to load the final plate/profile consistently rather than the legacy 0.20 mm alternative. Actual frame fit remains a cold assembly check; no printer job was started.

### 2026-10-09 — place the complete final package in print_now

At the user’s request, added `print_now/FINAL_P1B/` containing all twelve checked plates, fourteen replacement designs, regenerated fixtures, twelve profile backups, native model, assembly instructions and validation records. `START_HERE.md` provides direct STL/profile mappings and identifies T3 as the next test. `FINAL_P1B.zip` contains the complete package and start guide. Copy checks preserve verified plate hashes, all file checksums pass, and ZIP CRC passes; diagnostic generic-startup G-code is excluded. Added a repeatable copy/ZIP script. Physical fit and strength gates remain pending.

### 2026-10-09 — final print package published to GitHub

Published the current CAD sources, calibrated native/export geometry, complete `print_now/FINAL_P1B` package, ZIP, profiles, assembly guides and evidence to `DeviDeviDeviKanumilli/HackPHS` main at **19d215bd1069698a71056e0103654f49ade8a521**. The remote branch SHA was verified after upload. All 476 authoritative CAD files matched the publication index; 105 delivery checksums, guide links and ZIP CRC passed. Publication used an isolated checkout, preserving unrelated local work and the nested simulator index. The published simulator runtime remains unchanged; the local CAD refresh is retained as evidence. The first HTTP upload failed; retry with a per-command larger HTTP buffer and HTTP/1.1 succeeded. Physical qualification remains pending.

## 2026-10-10 — Combine both HackPHS repositories through PR #1 (user)

**Decision:** Finish PR #1 from `chessdroid108/HackPHS` into `DeviDeviDeviKanumilli/HackPHS`, resolving conflicts while preserving both repositories' work.

**Integration:** Merge the destination's CAD sources, final P1B print package, profiles, assembly guides and delivery history into the contributor's Flutter client, portable mission backend, retained mapping tools, firmware history and software evidence. The only overlapping conflicts are the documentation index and this append-only decision log; retain both histories and the newer project scope. No dated source snapshots or local uncommitted development work are replaced. Software verification for the combined tree is recorded in `docs/15-verification.md` before completion.

## 2026-10-10 — Complete the hardware-free portable mission path

User instruction: “tell me what you can achive right now without hardware. do it. finish it properly.” Connected generated AprilTag pixels through an independent relative-pose worker to the existing shared mock mission ledger/API. Frozen frames, delayed/stalled inference, target loss, Stop/Abort and source/settings changes cannot retain simulated motion. Added explicit --portable-demo, exact JPEG/frame association, real Python HTTP/Dart client rehearsals and phone/desktop render checks. Physical follow/landing, audio/TTS, D435 work, arbitrary point landing and UI redesign remain outside scope.

Replaced the active ESP32 PPM experiment with a no-output ESP32-S3 USB-UART protocol port at 115200 using the shared core/watchdog/framer; original experiment preserved as text under docs/sources. Added sketch host execution tests, selected-target compilation and CI/build/evidence gates. Hardware-free completion record: [docs/28](28-hardware-free-completion.md). No compiler/test result establishes actual USB, GPIO, radio or aircraft behavior.


## 2026-10-11 — Adopt trainer branch and publish full Claude hardware handoff (user)

**Decision:** Use `ebdevStudent/hackPHS`, branch `esp32-trainer-ppm`, baseline
`df186f4865aedc61bad246e535e8a785855fa750`, rather than the old `chessdroid108/HackPHS`
checkout. User requested a comprehensive handoff for Claude on this same laptop and
publication of the direct USB motor-control code. Publish this work on the adopted branch;
no main merge or unrelated source changes.

**Actual findings:** Ordinary Pocket ELRS binding and sticks were established. Earlier
Claude reports ESP-to-Pocket timing/mix/override checks; full 20 trainer-to-FC trials remain
pending. Codex observed fresh ESP NO_OUTPUT sessions with GPIO5 out. Actual FC firmware
is Betaflight 4.4.2 / API 1.45. Motor 1 at command 1020 physically spun in short pulses,
but the user reported stop/restart during a monitored 10-second run while MSP commands
remained 1020 for Motor 1 and 1000 for the others. All commands read back stopped afterward.
Continuous rotation, actual RPM, ESC firmware/settings and flight readiness are unverified.
1040 for 2 seconds is a proposed diagnostic after physical/supply checks, not a completed test.

**Delivery:** Added `docs/29-claude-flight-controller-handoff-2026-10-11.md`, optional
`tools/betaflight_motor_bench.py`, exact inert script/source snapshots and pointers from the
index/firmware README. Preserved earlier records rather than rewriting them as passed tests.
The helper is import-safe, requires explicit movement flags and adds voltage sampling;
Claude may choose another solution. Its syntax was inspected without importing it. No
new hardware pulse, installation, firmware flash, calibration, automated test suite or
trainer enable was performed while preparing this handoff.

## 2026-10-11 — Motor 1 "intermittent spin" resolved: test value was below ESC sync range

**Root cause:** Betaflight 4.4 maps a disarmed motor-test value of 1001–2000 linearly to
DShot 48–2047. The earlier 1020 command was therefore **~1.9 % throttle**, about one fifth
of this FC's armed idle (`dshot_idle_value` 1000 = 10 %, motor-test equivalent ~1100, read
over MSP: DSHOT300, 14 poles, bidir off). At ~2 % an unloaded 1202.5 11000KV motor gives
too little back-EMF for the BLHeli_S ESC to hold sync, so it starts, desyncs and restarts.

**Actual laptop measurement + user observation:** with a fresh pack (7.61 V resting),
Motor 1 = 1100 (9.9 %) for 2 s then 5 s, twice; commands held `[1100,1000,1000,1000]`,
voltage 7.61→7.58 V, stop confirmed after each run. User observed **smooth continuous
rotation for the full 2 s and 5 s**. No ESC/FC settings were changed; no flash.

**Tool:** `tools/betaflight_motor_bench.py` now allows motors 1–4 up to 1150 (~15 %),
reports the DShot throttle %, adds read-only `config` and read-only `esc-info` (BLHeli 4-way
passthrough, EEPROM read only; not yet run on hardware), and gates voltage at 6.8–8.45 V.
Remaining: solder motors 2–4, verify numbering/direction per motor, fix RC throttle
reading ~1293 at stick-low before arming, final-mount accelerometer calibration.

## 2026-10-11 — Local motor web dashboard

Added `tools/motor_dashboard.py` + `tools/motor_dashboard.html`: a stdlib HTTP server
(127.0.0.1:8765 by default) that owns the FC USB port and drives disarmed MSP motor-test
commands from browser sliders. Starts disabled; enable needs a props-removed attestation;
0.5 s heartbeat dead-man, STOP/Space, tab hide/close, USB loss, FC armed or battery
<6.4 V all stop and disable; reconnect always comes back disabled; normal arming is
blocked over MSP while connected; slider ceiling 1300 (~30 %) unless `--max` is raised.
Verified against a mock MSP FC on a pty (clamping, heartbeat timeout, stop, malformed
requests rejected, disconnect handling) and rendered in headless Chrome. **Not yet run
against the real FC.**

## 2026-10-11 — Per-motor ESC direction from the dashboard / bench tool

User reported motors spinning the same direction. Added ESC spin-direction setting via
`MSP2_SEND_DSHOT_COMMAND` (0x3003, confirmed present in BF 4.4.2 `msp.c`): blocking
DShot `SPIN_DIRECTION_1/2` (7/8) + `SAVE_SETTINGS` (12) to one motor, which Betaflight
repeats 10x; motors are stopped and verified at 1000 first. Exposed as
`betaflight_motor_bench.py direction --motor N normal|reversed` and dashboard Normal /
Reversed buttons. MSPv2 framing verified against the real FC (API 1.45 readback); the
DShot payloads were verified on the mock FC only. **Physical direction change pending user
observation.** No soldering change needed; props-in default is M1/M4 CW, M2/M3 CCW.

## 2026-10-11 — Angle mode always on, 35° tilt limit (beginner pilots, P1B gimbal)

User (first-time FC team) approved. Pre-change `diff all` preserved at
`docs/sources/bench-handoff-2026-10-11/betaflight-diff-all-before-angle-mode.txt`.
Applied over CLI and saved: `aux 1 1 0 900 2100 0 0` (ANGLE on AUX1 across its whole
range = always active) and `set level_limit = 35` (profile 0; BF 4.4 name for the angle
limit). `small_angle` stays 25. Readback after reboot confirms both; MSP mode flags show
ANGLE active. Readback also showed `acc_trim_pitch = 2` (0.2°), set by a Pocket stick trim
command, not by Claude. Live throttle at stick-bottom now reads **995**, so the earlier
1293 was the stick not being fully down. Accelerometer calibration is deferred until the
FC is mounted in the gimbal and level (the board currently sits at an arbitrary angle).

**Update (same day): Angle mode parked until the drone is assembled.** At the user's request
ANGLE is stored but inactive: `aux 1 1 0 900 900 0 0` (empty range). The aircraft is in Acro
until the user says it is built/mounted; then enable with `aux 1 1 0 900 2100 0 0` + `save`,
and do the accelerometer calibration level in the gimbal. Readback also showed stick
commands had switched the active PID profile 0→2 (BF: throttle low + yaw left + right-stick
direction selects profile), which made `level_limit` read 55. `level_limit = 35` is now set
in all four profiles 0–3 and profile 0 re-selected; verified by `diff all` after reboot.

**Update: Angle-mode stick expo.** User approved gentler small-stick response for speed
control (no true speed cap is possible: no GPS/optical flow). BF 4.4 Angle mode uses
`getLevelModeRcDeflection`, so ordinary rate expo does not apply; set the 4.4 Angle-only
`roll_level_expo = 40` and `pitch_level_expo = 40` in all four rate profiles (0–3).
Half stick ≈ 12° and quarter stick ≈ 5.5° of lean instead of 17.5°/8.75°; full stick still
35°. Pre-change `diff all` kept at `~/Documents/betaflight-diff-all-20261011-054332-before-level-expo.txt`;
`diff all` after reboot confirms all eight values. Active rate profile is 1 (stick input had
moved it from 2; all rate profiles are otherwise default). Angle mode itself remains parked.

## 2026-10-11 — VTX was never on 5917 MHz; fixed band, 25 mW, no low-power-disarm

MSP_VTX_CONFIG readback showed SmartAudio VTX ready but **`vtx_band` = 0 (user-frequency
mode) with frequency 0**: only `vtx_channel = 8` had been saved, so Betaflight never
commanded R8/5917 as the earlier handoff claimed. User approved: `vtx_band = 5`,
`vtx_channel = 8` (Raceband 5917 MHz), `vtx_power = 3` (table label "25"),
`vtx_low_power_disarm = OFF` for bench video without arming. Pre-change backup
`~/Documents/betaflight-diff-all-20261011-063631-before-vtx.txt`; readback: band 5, ch 8,
5917 MHz, power index 3, pit off, ready. Pi capture of `/dev/video0` (MS210x) is still
all-zero RGB (40 frames, std 0, no OSD), so RC832 reception or RC832→capture cabling is
unverified. Live FPV remains pending.

## 2026-10-11 — FPV capture fixed by re-enumeration; Pi streamer + dashboard Camera tab

The MS210x capture stick (534d:0021) returned all-zero frames until it was re-enumerated
(USB `authorized` 0→1); afterwards RC832 snow/blank screens arrived, proving the
RC832→capture→Pi path. Added `tools/pi/fpv_stream.py` (OpenCV, MJPEG on :8090, status with
PICTURE/SNOW/FLAT/NO INPUT classification, auto-reset after 4 s of all-zero frames),
`tools/pi/reset-capture` (installed to `/usr/local/bin`, with a NOPASSWD sudoers rule for
that script only), and `fpv-stream.service` (enabled on the Pi). The motor dashboard has a
Camera tab (`--fpv-url`, default http://172.16.240.48:8090) that embeds the stream only
while visible. Deployed and rendered; a live drone picture is still pending (the drone
battery was unplugged during the test). The streamer holds /dev/video0, so stop it before
ball_demo uses the camera.

**Live FPV verified (actual Pi capture).** With the drone battery connected (FC 7.36 V), the Pi
streamer reported PICTURE continuously at ~15 fps and a captured frame shows the real room
plus Betaflight OSD text ("BATT < FULL"): camera → AIO SmartAudio VTX (R8 5917 MHz, 25 mW)
→ RC832 (5-8) → MS210x capture → Pi → dashboard Camera tab. Frame saved at
`evidence/physical/fpv-first-live-frame-2026-10-11.jpg`. Earlier intermittent flat-grey
video happened on USB power only (FC ~2.2 V): the VTX carrier was received but the camera
had no proper supply. Flat grey = carrier without video; snow = no carrier.

## 2026-10-11 — Dashboard "video on/off" (VTX pit mode) to save battery

Camera tab button toggles VTX pit mode via `MSP_SET_VTX_CONFIG` (keeps band/channel/power,
runtime only, not saved; refused while armed; stops motors first). SmartAudio confirms
asynchronously, so the tool polls MSP_VTX_CONFIG up to 8 s. Measured on the bench (FC current
sensor, uncalibrated `ibata_scale`): ~0.46 A video on vs ~0.36 A pit mode, about 0.1 A saved.
The camera itself is hard-wired and stays powered. Pit mode still emits a weak signal, so an
RC832 right next to the drone may keep showing the picture.

## 2026-10-11 — Motor corners and directions verified

Props off, each motor alone at 1100 (and 1060 for M2/M3): M1/M2/M3/M4 sit at the
Betaflight QUADX corners when the **M2/M4 side is the nose** (the frame was first viewed
rotated 90°; no rewiring or board-alignment change, because the mixer positions are fixed to the
FC pads). M2 was CW, so it was set to ESC direction NORMAL (`direction --motor 2 normal`) and
re-checked: **final, user-observed M1 CW, M2 CCW, M3 CCW, M4 CW**. Stored ESC settings: M1 and M3
REVERSED, M2 NORMAL, M4 default. Next: mount the FC with its arrow toward the M2/M4 side.

## 2026-10-11 — AprilTag follow and landing guidance on the existing yaw path

User asked for software-side AprilTag support (follow; landing likely) while hardware is unavailable.
Implemented `target_mode` (`color`/`tag`/`landing`) feeding the unchanged Controller (yaw-only,
watchdogs, loss→neutral). Landing is pilot guidance only, so authority is unchanged. Tag kit CLI (wizard,
exact-size PDF, detection test), roster reload API/UI, Pi `drone-mode` switcher (deployed; Pi left in
`fpv` mode), roster push script, dashboard Camera tab auto-switching to the tracking preview in track
mode. Rahul's audit fixes (B3) arrived separately in 15d2f04. Range estimates are uncalibrated.
`--trainer-output`/`assist` remains a team decision. Verified on: laptop Python 3.13 venv (18 new tests,
4305 existing pass) and Pi deployment smoke test (track mode starts with the mock bridge when the ESP32
is absent). Live tag detection on real FPV is pending hardware.

## 2026-10-11 — Motor positions remapped in software (motor_output_reordering = 2,0,3,1)

After mounting, with the **FC arrow as the nose**, outputs 1–4 spun at front-right, front-left,
rear-right, rear-left. Betaflight QUADX needs M1 rear-right, M2 front-right, M3 rear-left, M4 front-left,
so `set motor_output_reordering = 2,0,3,1,4,5,6,7` + save (backup:
`~/Documents/betaflight-diff-all-20261011-082836-before-motor-reorder.txt`). Readback confirmed; user
re-test: **all four corners correct**. Spin directions must be re-checked: ESC direction settings belong
to the physical ESC/output, and a 90° change swaps the needed CW/CCW at every corner. Supersedes the
earlier "nose = M2/M4 side" note.

**Directions after the remap — verified.** Set per logical motor via DShot commands: M1 normal,
M2 normal, M3 reversed, M4 reversed (ESC on outputs 3, 1, 4, 2 respectively). User-observed at 1060,
FC arrow = nose: **M1 rear-right CW, M2 front-right CCW, M3 rear-left CCW, M4 front-left CW.**
Props: CW props on M1/M4, CCW props on M2/M3.
