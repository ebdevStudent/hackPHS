# Ball Drone bridge protocol, version 1

This protocol communicates **accepted internal command state**. Nothing in version 1 proves a transmitter signal or radio channel output. The provisional Pico executable has no trainer/GPIO signal generator. The ESP32-S3 sketch can *report* PPM trainer yaw output (`PPM_YAW`), but the radio mapping, pilot override and signal-loss behavior are not physically verified.

## Transport and framing

USB serial at **115200 baud**. On the ESP32-S3 bridge this is the board's CH343 USB-UART port (UART0, the USB-C port next to BOOT; Linux `/dev/ttyACM*`, prefer `/dev/serial/by-id/`), so the baud rate is real on the wire and the sketch's `Serial0.begin()` must match the host's `--baud` (default 115200). At 115200 a worst-case CMD (53 B) takes ~4.6 ms and an ACK (58 B) ~5 ms per 50 ms period; at 9600 a single CMD (~55 ms) is longer than the period, so 9600 cannot carry the control rate (`tests/test_esp32_bridge.py`). ASCII only. One frame per LF; CRLF accepted. Single spaces between fields, no leading/trailing spaces. Maximum **128 bytes including LF**. Session: 1–32 ASCII letters, digits, `_` or `-`. Integers are decimal; no plus sign, fractional value, leading zeros or overflow. A new host connection uses a fresh random session.

| Message | Fields / example | Meaning |
| --- | --- | --- |
| HELLO | `HELLO 1 abcd` | Reset bridge to disabled, yaw zero, sequence zero. |
| READY | `READY 1 abcd NO_OUTPUT` | Version/session accepted, internal state only. |
| READY | `READY 1 abcd PPM_YAW` | ESP32-S3 only, arming jumper fitted: accepted yaw is reported as PPM trainer output (CH4). Not physically verified. |
| CMD | `CMD 1 abcd 1 1 -200` | Version, session, seq, enable, yaw. |
| ACK | `ACK 1 abcd 1 1 -200 NONE` | Echo seq and accepted enable/yaw with fault code. |

The host talks to the ESP32-S3 bridge directly over its USB-UART port (`--serial`). It treats a `PPM_YAW` bridge as ready only when the operator also passes `--trainer-output`; otherwise that READY is ignored, no CMD is sent, and the host stays unready. The output mode is fixed by the first accepted READY of a session: a replayed READY cannot change it, and a resync drops it until the new session's READY reports it again.

Sequence range 1–2147483647, strictly increasing per session. Start a new HELLO/session before exhaustion. Enable is `0` or `1`; yaw is −1000…+1000. Disabled commands must carry yaw zero. The host sends a valid command every 50 ms, including neutral commands while disabled.

## Errors and timing

- Unsupported versions, malformed fields, unknown session, excessive length and invalid ranges are rejected without an ACK or watchdog refresh. The host reaches its missing-ACK fault deadline.
- Duplicate/out-of-order commands return ACK with `SEQUENCE`, reporting the previously accepted enable/yaw (which may have become zero through watchdog expiry). They do not refresh the watchdog.
- Fresh valid commands return ACK `NONE`. ACK is **not** an assertion of physical output.
- Host ignores ACKs from another session, unknown sequence, inconsistent values, non-NONE faults and replies 250 ms or more after the corresponding send.
- Bridge watchdog: at least 250 ms without a fresh valid CMD → disabled, yaw zero, internal `WATCHDOG`. A subsequent valid CMD may clear that watchdog fault; the host separately requires deliberate operator re-enablement after its fault.
- HELLO resets state but does not arm assistance. The host repeats HELLO (same session) every 0.5 s until READY, because opening the bridge's USB port can reset the board and input is lost while it boots (ESP32-S3: DTR/RTS auto-reset and ROM boot messages on UART0; host-side parsing ignores the non-protocol lines. Historical Mega: the bootloader discards the first ~1.5 s). The Pico resets its session and neutral state on detected USB disconnect. Partial Pico input expires after 250 ms; discard it through the next LF. Overlong input is also discarded through LF.
- Host state/control ticks at 20 Hz. Thus a 250 ms application deadline is observed on the next control tick (nominally within another 50 ms). This is ordinary OS scheduling, not a hard real-time guarantee.

The C core receives explicit 32-bit millisecond time and uses unsigned subtraction for clock rollover. The Python emulator uses monotonic seconds. No wall-clock changes affect either watchdog.

## Emulators

```sh
cd /Users/devk/Documents/HackPHS26/software
.venv/bin/python -m ball_demo.cli bridge-check
.venv/bin/python -m ball_demo.serial_emulator --fault partial
# Second terminal, using the virtual device path printed above:
.venv/bin/python -m ball_demo.cli serve --port 8082 --serial /dev/ttysXXX
```

Available PTY faults: `none`, `partial`, `invalid`, `missing_ack`, `delayed_ack`, `disconnect`. PTY checks exercise the actual pyserial host adapter without a USB board. A received USB command still never enables trainer output in the scaffold.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Firmware implementation](README.md) — Current parser/watchdog status and limits.
- [Arduino Mega 2560 official board page](https://docs.arduino.cc/hardware/mega-2560/) — Board reference; project-specific trainer output has not been implemented.
- [Pico SDK documentation](https://www.raspberrypi.com/documentation/microcontrollers/c_sdk.html) — Historical RP2040 build foundation.
