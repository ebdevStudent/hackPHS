# Software

Source: Google Doc **Software** tab, read 2026-10-04. [Preserved tab text](../google-doc-2026-10-04/04-software.md). The user-approved pre-hardware implementation plan assigns Pi processing as well as server hosting; [decisions](decisions.md) records this newer decision.

## Demo deployment

The operator interface is now a **native Qt desktop application for Mac and Pi**, as selected by the user. It can own a local mock server or connect to the Pi service; visitor browsers remain supported. A Pi without a display runs headlessly and can be operated from the Mac. [Desktop startup, capabilities and limits](14-desktop-app.md).

| Device | Current assignment |
| --- | --- |
| Raspberry Pi 5 | Tracking, yaw calculations and demo server on port 8080. Hardware operation pending. |
| User's Mac | Development/rehearsal for this application and independent 3D simulation on port 8765. |
| Visitor phones/tablets/laptops | Read shared dashboard and play isolated browser-local sandbox traces. |
| RP2040/Pico (provisional) | Portable C bridge core + compiled USB CDC scaffold. No trainer output. |

Prepared profiles: **BallDrone-Demo** Pi hotspot and **shared network**, using explicit NetworkManager switching. Local assets require no CDN or event internet after installation. The Pi package targets 64-bit Raspberry Pi OS Trixie/Python 3.13+. Mac and ARM64 container checks are recorded separately from Pi/device checks.

[Application and commands](../../../software/README.md) · [startup, network and recovery runbook](12-demo-runbook.md) · [implementation status](11-pre-hardware-status.md) · [evidence](../../../evidence/README.md).

## Implemented processing path

Video source → HSV detector → stable target selection → four-state machine → bounded yaw controller → mock/serial bridge → status and logs.

Capture/vision has its own worker and latches requested zero immediately for every detected target loss, even if the latest-frame mailbox later changes. A separate 20 Hz control worker checks frame freshness and ACK freshness even if capture blocks. Preview frames are JPEG-encoded once, cached and shared; each viewer receives only the latest preview without an application-level queue. HTTP streaming is independent of the control loop. This is a software architecture with measured Mac/container behavior, not a hard real-time guarantee.

Sources: deterministic synthetic scenes with ground truth, recorded video, and an OpenCV camera adapter. Recorded EOF returns MANUAL/disabled/zero. Synthetic fixtures include movement, approach, edges, brightness, distractions, small targets, occlusion, blur/noise, loss/reappearance and frozen/delayed/stopped capture. Timing faults are injected by the synthetic adapter. A successful live camera read receives a host timestamp; actual receiver buffering/content freezes and physical latency require hardware measurements.

Detector: configurable HSV thresholds, morphology, blob-size rejection; largest target for acquisition, then prefer spatial continuity. Horizontal error is `(x - (width-1)/2) / ((width-1)/2)`, clamped −1…+1. Quality uses visible blob size/continuity and is explicitly a **heuristic, not a probability of safe flight**.

## Software demonstration defaults

These are repeatable software values, not calibrated flight settings.

| Setting | Default |
| --- | --- |
| Processing image / target rate | 640 × 480 / 20 Hz |
| Control / shared viewer preview | 20 Hz / maximum 10 Hz |
| Acquisition | Three consecutive valid detections |
| Loss | Immediate requested neutral on the first processed missing-target frame; SEARCHING |
| Stale frame / missing ACK | 250 ms deadline, observed on next control tick |
| Bridge watchdog | 250 ms since fresh valid CMD |
| Gain / smoothing / deadband | 700 / 0.35 / 0.04 |
| Maximum yaw / slew / direction | 650 / 1800 units per second / +1 |
| HSV hue / minimum saturation / minimum value | 35–85 / 100 / 80 |
| Blob area | 100–50000 pixels² |
| Startup and restart | MANUAL, disabled, synthetic input, mock bridge |

Controller applies proportional gain, smoothing, deadband, magnitude clamp and slew limit. Disable/loss/fault sets zero directly and resets the filter; zero does not wait for slew. Settings/source changes disable assistance. Faults disable assistance; recovery/reconnect never automatically re-enable it. Explicit serial or recorded CLI choices still start disabled.

## States and command authority

| State | Trigger / behavior |
| --- | --- |
| MANUAL | Startup, operator disable, normal EOF or recovered mock bridge; zero requested yaw. |
| SEARCHING | Deliberate enable awaiting three valid frames, or target loss; zero yaw. |
| LOCKED | Three consecutive valid detections; bounded yaw correction. |
| FAULT | Stale frame, missing ACK, capture/bridge failure; disabled and zero yaw. |

The bridge's enable field is true only in LOCKED. A displayed ACK describes previously accepted memory state and can lag one update; it never claims physical trainer output.

## Bridge and firmware

[Protocol version 1](../../../firmware/PROTOCOL.md): newline ASCII `HELLO`, `READY`, `CMD`, `ACK`; fresh session identifier, increasing sequence, enable and integer yaw −1000…+1000. Malformed/duplicate frames do not refresh the bridge watchdog. Delayed/unmatched ACKs cannot refresh host freshness.

Implemented transports: in-process emulator with fault injection; actual pyserial USB adapter; PTY serial emulator exercising that adapter without a board. [Portable C core and Pico scaffold](../../../firmware/README.md) implement parsing, session/sequence validation and watchdog. The compiled UF2 is **compiled, not flashed or electrically verified**. There is no trainer/GPIO output implementation.

Eventual physical path: **Pi → USB serial → verified bridge/trainer interface → transmitter → ELRS → Betaflight**. Betaflight retains stabilization and motor control. V1 assistance remains yaw-only; pilot retains throttle, roll, pitch, ARM/DISARM and physical override. Exact transmitter, protocol, voltages, pins, mixes, latency and channel mapping are still [hardware inputs](13-hardware-arrival.md).

## Browser capabilities

This browser UI remains the visitor/shared monitor. The [native workstation](14-desktop-app.md) provides the desktop operator interface; its preview uses the additional read-only `/api/preview.jpg` cached-frame endpoint. Headless installation does not require Qt.

Public read endpoints: `/api/health`, `/api/state`, `/api/events` (SSE), `/api/preview` (MJPEG), `/api/scenarios`, `/api/sandbox/{scenario}`. The dashboard uses a compact light monitor layout: video and state/yaw/error readouts on the left, session status and unlocked operator controls on the right. Sandbox playback has a separate tab. Controller/detector tuning and bridge fault controls sit in expandable sections. Source labels, freshness, accepted yaw and faults stay visible; decorative hero text and promotional panels were removed. Unknown aircraft telemetry stays unavailable.

Operator request bodies use strict JSON types: assistance requires true/false, numeric tuning fields require numbers (integer fields require integers), and unknown fields return 422. Existing desktop/browser controls already send typed fields. Smoothing uses a weighted average so a 1.0 setting preserves the input exactly at the inclusive deadband boundary.

Operator controls require an Authorization bearer token: access check, source, validated settings, assistance, mock fault injection and reset. Token is local/private and not part of visitor URLs/cards. Ordinary HTTP is for a trusted local demo network; remote public hosting is outside this implementation.

Visitor sandbox uses precomputed traces generated by the same detector/controller. Playback selection/play/pause/reset lives only in each browser and cannot write to the shared bridge. No extra live vision pipeline runs per visitor. Disconnects display stale status; EventSource reconnects and refreshes the current snapshot without enabling assistance.

## Logs, replay and evidence

Current automated regression coverage and reproducible checks: [verification guide](15-verification.md) and [new run reports](../../../evidence/verification/README.md). These distinguish native Qt, real local subprocesses/PTY, portable host firmware and actual hardware work.

Ignored runtime directories hold config/version/environment, source/settings events, transition/fault/command/ACK JSONL, sample CSV, and JSON summary with duration/FPS/processing timings/fault count. Replay export reconstructs samples and events and has no serial activation path. Imported replay is browser-local. Synthetic response-model motion illustrates controller error reduction; it is not measured aircraft dynamics.

[Recorded checks](../../../evidence/README.md) distinguish Mac browser/Python, portable C, compiled Pico, Linux ARM64 and still-pending physical results. See [runbook](12-demo-runbook.md) for demo scenarios and recorded-source fallback.

## Later work

Camera receiver compatibility, Pi throughput/thermals, physical hotspot/network clients, USB board timing, transmitter electrical interface, pilot override and flight tuning remain hardware-arrival work. CAD is deferred. Pitch assistance, tags and any read-only Mac simulation adapter remain optional later upgrades; the standalone loop works independently.

Simulation implementation stays in its [separate document](06-simulation.md) and independent Git repository.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Pre-rewrite archive index](README.md) — identifies this file as historical context, not current instruction.
- [Maintained document](../../04-software.md) — current requirements and status.
- This citation note is external to the preserved pre-rewrite text.
