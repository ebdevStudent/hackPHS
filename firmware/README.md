# Bridge firmware

## Actual bench status — 2026-10-11

See the [complete laptop handoff](../docs/29-claude-flight-controller-handoff-2026-10-11.md) and [dated source records](../docs/sources/bench-handoff-2026-10-11/README.md). The earlier Claude handoff reports real Pi PPM timing and Pocket trainer/mix/SD-override checks; Codex inspected the matching source and Pi tools and independently observed a fresh `NO_OUTPUT` serial session with GPIO5 out. Those reported physical measurements supersede the older table below only in their stated ESP-to-radio scope. **The 20 disarmed trainer-to-FC trials and Linux suites remain pending in this session.**

Direct USB FC motor work is a separate path. User confirmed Motor 1 rotation in short pulses but intermittent spin/stop during a 10-second command at 1020 despite steady MSP command readback. Actual ESC firmware/settings, RPM, direction, loaded current and continuous reliable rotation are unverified. The optional Python helper does not change this ESP firmware. No board was flashed while preparing this handoff.

## Current selected board: Freenove ESP32-S3 WROOM

The user selected this board on 2026-10-10 because the team does not have the previously planned Arduino Mega 2560. Connect the Pi through the board's **USB-UART** interface for a direct serial link; the VIXLW capture adapter is a separate USB device for video. Freenove documents USB-UART as the board's USB-to-serial path and distinguishes it from USB-OTG in its [USB guide](https://docs.freenove.com/projects/fnk0085/en/latest/fnk0085/codes/C/35_USB.html).

Sketch: [`esp32/ball_bridge_esp32/`](esp32/ball_bridge_esp32/). It runs the same tested protocol core as the other bridges (`src/` is a byte-identical copy of `firmware/core.*` and `line_reader.*`; `tests/test_esp32_bridge.py` fails on drift). It generates a CPPM trainer signal for **yaw only**. That output is compiled and checked in a host simulation, **not yet physically verified** on the radio. Terminal tools (flash, drive, probe): [`esp32/tools/`](esp32/tools/).

### Output behaviour

- Link: `Serial0` at 115200 (CH343 USB-UART, UART0). The host default `--baud` matches.
- Arming jumper: GPIO 5 to GND. It is sampled at each HELLO. READY reports `PPM_YAW` only if the jumper was in at that HELLO; otherwise `NO_OUTPUT` and no pulses. The host accepts a `PPM_YAW` bridge only with `serve --trainer-output`.
- Pulling the jumper disarms at once, for the rest of the session. Refitting it needs a new HELLO.
- While armed, GPIO 4 streams CPPM continuously: 8 channels, 22.5 ms frames, every channel 1500 µs except CH4 (yaw) = 1500 ± 150 µs, scaled from protocol yaw ±1000.
- Disabled, watchdog-expired or stale (main loop stalled more than 5 frames) → CH4 1500 µs. The stream keeps running, because EdgeTX holds the last trainer value for about 1 s after the signal stops.
- Disarm → 3 neutral frames, then the line idles HIGH and the radio drops the trainer input.
- GPIO 4/5 are also the camera SCCB pins. Leave the camera ribbon unplugged.

### Build and flash

Arduino-ESP32 core 3.x (2.x also compiles via the version switch in `ppm.cpp`). Board: `ESP32S3 Dev Module`.

```sh
arduino-cli compile --fqbn esp32:esp32:esp32s3 --warnings all firmware/esp32/ball_bridge_esp32
arduino-cli upload  --fqbn esp32:esp32:esp32s3 -p <port> firmware/esp32/ball_bridge_esp32
```

Use the USB-C port next to the BOOT button (CH343, VID:PID `1a86:55d3`); on Linux it is `/dev/ttyACM*`, stable as `/dev/serial/by-id/usb-1a86_*`. If upload does not start, hold BOOT, tap RST, release BOOT.

Then on the Pi: `python -m ball_demo.cli serve --serial /dev/serial/by-id/<id> --trainer-output` (omit `--trainer-output` for an internal-state-only bridge). Startup stays MANUAL and disabled.

### Checks (2026-10-10, no board attached)

| Check | Result |
| --- | --- |
| `arduino-cli compile --warnings all` (esp32 core 3.x, ESP32S3 Dev Module) | Clean; 285,273 B flash (21%), 22,392 B RAM |
| Host simulation `esp32/test/test_ppm.cpp` (EdgeTX-style decode: 22.5 ms frames, 4–19 ms sync, non-yaw 1500 µs, yaw cap, neutral on disable/stall, 3-frame tail then idle, no start-up glitch) | PASS |
| `test_core.c` incl. per-HELLO output latch; `test_line_reader.c` | PASS |
| Flashed to the board, CPPM measured on a scope, EdgeTX trainer channel monitor, props-off 20/20 | **Not done**: needs hardware |

Rebuild the simulation from `firmware/esp32/test`: `c++ -std=c++17 -Wall -Wextra -Werror -I stubs -I ../ball_bridge_esp32 test_ppm.cpp && ./a.out`.

The historical Mega and Pico artifacts below do not establish ESP32-S3 behaviour.

## Historical Arduino Mega 2560 sketch

[`mega/ball_bridge_mega/`](mega/ball_bridge_mega/ball_bridge_mega.ino) speaks [protocol version 1](PROTOCOL.md) over the Mega's USB serial port at 115200 baud. It uses the same portable parser/watchdog (`core.c`) as the Pico scaffold and a shared line-framing module (`line_reader.c`). **It drives no pins: there is no trainer, PPM or channel output.** ACKs report accepted internal state only. Output waits for the verified transmitter trainer protocol, voltage, connector pinout and channel mapping in the [arrival worksheet](../docs/13-hardware-arrival.md), followed by the props-off override and signal-loss checks.

The sketch's `src/` folder holds byte-identical copies of `core.c/.h` and `line_reader.c/.h`. The Arduino build only compiles files inside the sketch folder. After editing the originals, copy them again; `software/tests/test_mega_bridge.py` fails if the copies differ.

```sh
# Compile (arduino-cli with the arduino:avr core installed)
arduino-cli compile --fqbn arduino:avr:mega:cpu=atmega2560 --warnings all firmware/mega/ball_bridge_mega
# Upload once the board is connected (port name differs per machine)
arduino-cli upload --fqbn arduino:avr:mega:cpu=atmega2560 -p /dev/ttyACM0 firmware/mega/ball_bridge_mega
# Host-side protocol use, internal state only
cd software && .venv/bin/python -m ball_demo.cli serve --serial /dev/ttyACM0
```

Opening the Mega's USB port resets the board; its bootloader ignores input for about 1.5 s. The host therefore repeats `HELLO` every 0.5 s until `READY`. During that time the software shows a missing-acknowledgement fault and stays disabled; enable deliberately once READY has arrived. If the host stops sending, the 250 ms watchdog returns the internal state to neutral.

| Check (2026-10-08) | Result | Scope |
| --- | --- | --- |
| `arduino-cli` 1.5.1, `arduino:avr` 1.8.8 compile | 5,456 B flash (2 %), 600 B RAM (7 %); no warnings from project files | Build only, not flashed |
| `avr-gcc` 7.3 `-mmcu=atmega2560 -Wall -Wextra -Werror -pedantic -Wconversion` on `core.c`, `line_reader.c` | Clean | Compiler only |
| [`test_line_reader.c`](test_line_reader.c) as ATmega2560 firmware in simavr 1.6 | Passed: framing, CRLF, partial-frame expiry, oversize discard, sequence limits, watchdog at 32-bit rollover, 4,000 random bytes. A forced-failure build is reported as failed by the same simulator run | Simulated CPU with 16-bit `int`; no USB-serial chip, board or radio |
| Same tests on Linux ARM64 with ASan + UBSan, and on Mac with UBSan | Passed | Host |

[Simulator evidence](../evidence/firmware/mega-avr-simulation-2026-10-08.txt) · reproduce with `tools/mega_avr_check.sh` (Docker). Not yet done on hardware: flashing, USB enumeration, reset timing, and everything about trainer output.

## Provisional RP2040 / Pico bridge (historical)

Portable C parser/watchdog and a Pico USB CDC scaffold. **Compiled, not flashed or electrically verified.** No trainer output, GPIO waveform or channel mapping is implemented.

## Host checks (Mac or Linux)

```sh
cd /Users/devk/Documents/HackPHS26
mkdir -p firmware/build-host
clang -std=c11 -Wall -Wextra -Werror firmware/core.c firmware/test_core.c -o firmware/build-host/test_core
firmware/build-host/test_core
```

Checks include bounds, session reset, duplicate/invalid command rejection without watchdog refresh, disabled zero, and 32-bit timer rollover. Time is injected; no board or sleeps are needed.

## Pico SDK build

The recorded build uses **official Pico SDK 2.2.0**, commit `a1438dff1d38bd9c65dbd693f0e5db4b9ae91779`, and **Arm GNU Toolchain 14.3.Rel1** for Darwin ARM64, including newlib. Homebrew's `arm-none-eabi-gcc` formula alone lacked the C runtime needed here; the complete official Arm toolchain was downloaded instead.

```sh
export PICO_SDK_PATH=/Users/devk/.cache/ball-drone/pico-sdk
export PICO_TOOLCHAIN_PATH=/Users/devk/.cache/ball-drone/arm-gnu-toolchain-14.3.rel1-darwin-arm64-arm-none-eabi
cmake -S firmware -B firmware/build -DPICO_BOARD=pico
cmake --build firmware/build -j4
```

For a fresh machine, clone `https://github.com/raspberrypi/pico-sdk.git` at tag `2.2.0`, initialize `lib/tinyusb`, install a complete Arm GNU embedded toolchain and CMake, and set the two paths to their local locations. Build does not require a Pico.

The USB scaffold polls input, validates complete messages, updates the internal watchdog and replies with accepted state. Output writes have a short timeout so a missing USB reader does not indefinitely block the watchdog loop. Actual scheduling must be checked on a board.

[Protocol](PROTOCOL.md) · [compiled UF2](../evidence/firmware/ball_bridge.uf2) · [ELF](../evidence/firmware/ball_bridge.elf) · [recorded compiler/SDK](../evidence/firmware/toolchain.txt) · [build log](../evidence/pico-build.txt) · [host tests](../evidence/firmware-host-tests.txt).

Physical work remains: exact transmitter/trainer protocol, voltage levels, connector/pins, channel mapping, pilot override and measured latency. See the [arrival worksheet](../docs/13-hardware-arrival.md).

References: [official Pico SDK USB stdio](https://www.raspberrypi.com/documentation/pico-sdk/runtime.html), [official Arm toolchain](https://developer.arm.com/Tools%20and%20Software/GNU%20Toolchain).


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Protocol definition](PROTOCOL.md) — Message semantics and USB-only scope.
- [Pico SDK documentation](https://www.raspberrypi.com/documentation/microcontrollers/c_sdk.html) — Historical build target.
- [Saved firmware evidence](../evidence/README.md) — Build/test artifacts and no trainer-output caveat.
