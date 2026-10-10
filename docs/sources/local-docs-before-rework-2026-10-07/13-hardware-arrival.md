# Hardware-arrival worksheet

Prepared software is a demonstration foundation. Fill in this worksheet with actual measurements before connecting the software to a transmitter. The Pico build currently produces **no trainer output**.

## Equipment identification

| Item | Actual model / revision / firmware | Evidence and date |
| --- | --- | --- |
| Pi 5 / RAM / power supply / cooling | Pending | Pending |
| Raspberry Pi OS / architecture / Python | Pending | Pending |
| USB FPV receiver / capture backend | Pending | Pending |
| Camera / lens / analog format | Pending | Pending |
| Transmitter / firmware / ELRS module | Pending | Pending |
| Trainer connector and protocol | Pending | Pending |
| Bridge board (provisional Pico/RP2040) | Pending | Pending |
| Flight controller / firmware / receiver | Pending | Pending |

## Trainer interface — complete before implementing output

- Pin numbers and connector orientation, with a photograph and vendor reference: **pending**.
- Signal voltage, tolerated levels, polarity and ground reference: **pending**.
- Protocol (PPM, serial or another verified interface), frame timing and channel count: **pending**.
- Yaw channel, center/min/max encoding, positive direction and transmitter mixes: **pending**.
- Computer input authority and physical takeover/disable behavior: **pending**.
- Power arrangement, electrical isolation/level shifting if required, cable strain relief: **pending**.
- Instrument used and measured waveforms/latency: **pending**.

Do not infer these from the USB ASCII ACK. Its values describe accepted memory state only.

## Ordered arrival checks

1. Install the prepared package on the Pi, start synthetic/mock in MANUAL. Record package versions and startup logs.
2. Rehearse 20 Hz processing and five browser viewers on the actual Pi. Record throughput, missed deadlines, CPU/RAM/temperature, power and cooling. Mac/container results do not replace this.
3. Check shared Wi-Fi, hotspot switching, active address/card, mDNS/IP fallback, peer isolation and visitor reconnects.
4. Connect the video receiver. Confirm device enumeration, color conversion, resolution, frame rate, lighting and frozen/disconnected receiver behavior.
5. Flash the provisional Pico only after confirming the board target. Exercise USB handshake, command validation, disconnect and watchdog, with trainer output still absent.
6. Verify the transmitter interface from its actual documentation and measurements. Implement board-specific output only after the rows above are complete.
7. Props off: verify yaw direction, center/endpoints, channel mapping, command loss, app crash, USB disconnect, pilot override and ARM/DISARM authority. Record every outcome.
8. Measure complete camera-to-trainer latency/jitter and actual zero/override latency, not merely frame-processing time.
9. Establish manual aircraft operation and supervised bounded-yaw behavior, tune gains using those measurements, then follow physical gates in [build and test](10-build-and-test.md).

## Measurement log template

| Check | Configuration | Measured value / outcome | Evidence file | Date / reviewer |
| --- | --- | --- | --- | --- |
| Pi throughput / thermal | Pending | Pending | Pending | Pending |
| Capture / complete latency | Pending | Pending | Pending | Pending |
| Command direction / channel | Pending | Pending | Pending | Pending |
| Watchdog / target loss | Pending | Pending | Pending | Pending |
| Physical override | Pending | Pending | Pending | Pending |
| Manual / assisted flight | Pending | Pending | Pending | Pending |

Pilot retains throttle, roll, pitch, ARM/DISARM and physical override. This version only calculates yaw assistance. CAD remains deferred until requested and component dimensions are available.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Pre-rewrite archive index](README.md) — identifies this file as historical context, not current instruction.
- [Maintained document](../../13-hardware-arrival.md) — current requirements and status.
- This citation note is external to the preserved pre-rewrite text.
