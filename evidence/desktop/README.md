# Native desktop evidence — 2026-10-04

These results describe the native Qt application added after the browser design feedback. No drone, Pi, camera receiver, radio or Pico hardware was connected. Prior Python/browser/endurance reports are separate.

This page preserves the initial native-app evidence. The current source/app revision has [260-test verification and a rebuilt-app smoke](../verification/README.md), with explicit source/artifact hashes. Earlier renders and executable checksums describe their original builds.

| Environment/check | Recorded evidence | Result and limit |
| --- | --- | --- |
| Mac source launch | [Native window](mac-native.png) | Cocoa window, native controls, real cached preview/state. Final process-separated version starts MANUAL, disabled. |
| Apple Silicon packaged application | [Packaged window](mac-packaged.png), [build output](mac-build.txt), [session summary](mac-packaged-summary.json) | App executable launches without a venv, reports live state/video, shuts down and saves summary. Strict deep code-signature verification passed after local ad hoc signing. No Apple notarization/Intel build claim. |
| Native operator walkthrough on Mac | [Captured states](native-walkthrough.json), [locked](locked.png), [fault](fault.png), [recovered](recovered.png) | Native button actions: LOCKED/yaw 215, injected missing ACK → FAULT/disabled/yaw 0, recovery → MANUAL/disabled/yaw 0. Scripted short walkthrough, not an endurance run or full regression suite. |
| Native settings and isolated playback | [Settings](settings.png), [trace](trace.png) | Dialogs rendered and visually inspected; trace reconstructs truth/detection, without replaying camera effects or sending shared bridge commands. |
| Linux ARM64 container | [Rendered window](linux-arm64.png), [build](arm64-build.txt), [run output](arm64-run.txt), [summary](linux-arm64-summary.json) | Qt dependency install, offscreen window, synthetic processing, API preview/state and graceful summary save. Debian Trixie / glibc 2.41 / Python 3.13.16. Not actual Pi display, throughput, thermals or device validation. |

Mac: macOS 26.6.2 ARM64, Python 3.13.12, PySide6/Qt 6.9.3, PyInstaller 6.22.3. Final short packaged session recorded zero faults, ~18.45 processing FPS across 6.23 seconds under concurrent development/container work; this is not a 20 Hz guarantee. The final ARM64 session recorded zero faults and ~19.13 FPS across 6.38 seconds. GUI screenshots were captured at ~2.5 seconds and shutdown after seven seconds.

## Corrections made

1. Mac's venv plugin files carried UF_HIDDEN flags. Qt skipped them. The source launcher uses a temporary metadata-free plugin copy; final bundled plugins are visible. A temporary Qt upgrade/downgrade alone did not solve the flag issue.
2. PySide enum `NoError` was truthy; comparing explicitly to `QNetworkReply.NetworkError.NoError` corrected false network-error reports.
3. The project folder's file-provider FinderInfo metadata broke strict signature verification. Build/stage outside that folder and install the clean app in the user's Applications folder. Verification passed there.
4. Initial Linux renders lacked libglib/libGL. The final desktop Docker/installer profiles include these graphics/runtime libraries.
5. The initial same-process backend hit stale/ACK faults during native window initialization. The final app runs its owned server in a separate process, preserving the configured freshness deadlines. Parent loss also requests server shutdown through a process watchdog. Final captures/results above are from the corrected version.

Failed preliminary starts are not counted as passing results. The portable firmware and earlier 50 tests were not rerun for this interface change. Physical trainer output remains absent. Remote-client disconnection is not an operator lease; see the [desktop guide](../../docs/14-desktop-app.md).


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Desktop application guide](../../docs/14-desktop-app.md) — Current launch behavior and known limits.
- [Current test report index](../verification/README.md) — Source hashes and later application checks.
- [Software evidence index](../README.md) — Parent evidence index.
