# Claude handoff — flight controller, Motor 1 fault, and complete Ball Drone pipeline

Date: **2026-10-11, America/New_York**. Prepared by Codex for Claude **on this same Linux laptop**.

## 0. Read this first: objective and current physical state

**Immediate objective: diagnose why Motor 1 starts, stops, and restarts while Betaflight's motor command stays constant. Obtain a repeatable, continuous, props-off bench spin before proceeding with the other motors or flight.**

This is not a request to start autonomous flight, flash firmware, reconnect every GUI, or finish the trainer trials first. The user is installing Claude on this laptop. The FC, serial tools, local source checkouts and evidence already exist here. Prefer the shortest dependable route; do not reinstall software merely because this is a new assistant session.

Latest known state, not a fresh physical inspection:

- FC is connected to this laptop by USB and its stable device alias exists.
- Only **Motor 1** is electrically connected. The other three motors are mounted on the frame but have loose, unsoldered phase wires.
- User confirmed the Motor 1 propeller was **completely removed** before the motor tests. The earlier photo was taken before they temporarily installed that propeller; it is not evidence of the later test state. Keep all props removed for troubleshooting.
- User planned to hold the frame down because they have no bench clamp. Fingers must stay clear of the motor; the loose FC and wires need support without conductive contact or cable strain.
- FC is **not mounted in its final orientation**. Recalibrate its accelerometer after final mounting, **not now**.
- Battery was connected for the tests. Last verified motor commands were all **1000 = stop**. Whether the battery has since been unplugged is unknown.
- Pocket SA/AUX1 was off, FC was disarmed. Actual throttle readbacks were about **1293–1294**, despite earlier user belief that throttle was fully down. Resolve this before eventual normal arming; it does not explain the direct disarmed motor command.
- ESP32 **GPIO5 jumper is deliberately disconnected from the breadboard ground rail**. Leave it disconnected during motor diagnosis. A fresh ESP session independently returned `NO_OUTPUT` earlier in this chat.
- No further physical checks or 1040 pulse have happened since the user's final report of intermittent spin.

**Confirmed failure:** the second monitored 10-second run physically spun, stopped, spun, stopped, spun, then stopped, according to the user. Its FC command readbacks stayed `[1020,1000,1000,1000]` throughout. Do not call that a successful continuous-spin test.

## 1. Evidence labels and authority

Use these distinctions in every report:

| Label | Meaning |
| --- | --- |
| Actual laptop measurement | A command and reply were observed on this laptop connected to the real FC |
| User observation | The human reported physical movement or hardware assembly; no RPM sensor confirmation |
| Claude handoff report | The earlier Claude session reported measurements; Codex read and adopted that handoff but did not repeat all of them |
| Source inspection | Code was read/compared; this does not prove a flashed binary, wiring or physical behavior |
| Pending | Not established; never silently convert this to passed |

This handoff records later user decisions and bench results. Older repo documents describing an unavailable Mega, no-output-only ESP firmware, or universal pushing to `main` are stale for this adopted trainer branch. Preserve those historical records rather than pretending they describe current hardware.

The user asked to publish this handoff and the direct USB code. That authorizes this publication, not arbitrary future firmware flashes, trainer weight changes, flight, or pushes to another repository. Work proactively within the requested task. Ask concise physical-status questions when needed, rather than repeating broad permission requests.

## 2. Repository and paths — use the right source

| Item | Exact location / state |
| --- | --- |
| Active GitHub repo | `https://github.com/ebdevStudent/hackPHS` |
| Active branch | **`esp32-trainer-ppm`** |
| Source baseline adopted before this handoff | `df186f4865aedc61bad246e535e8a785855fa750` |
| Active local checkout | `/home/chessdroid108/Documents/ChatGPT/hackPHS-esp32-trainer` |
| Old chat checkout, preserve | `/home/chessdroid108/Documents/ChatGPT/hackPHS` |
| Superseded old origin | `chessdroid108/HackPHS` |
| Original Claude trainer handoff | `/home/chessdroid108/Downloads/codex-handoff-esp32-trainer.md` |
| This handoff, standalone copy | `/home/chessdroid108/Downloads/claude-flight-controller-handoff-2026-10-11.md` |
| Optional new USB helper | `tools/betaflight_motor_bench.py` in the active checkout |
| Exact scripts used during real tests | `docs/sources/bench-handoff-2026-10-11/*.py.txt` |

The active repo has unrelated history to the older repo: `0d9974d` initial commit, then `df186f4` trainer overlay. At adoption, its `main` was still the older initial commit. **Use the trainer branch; do not merge to `main` unless the user requests it.** Current source will additionally include the handoff publication commit.

Source adoption checks already completed:

- Branch HEAD matched the exact earlier handoff commit.
- Three ESP tools matched the handoff's verbatim files after newline normalization.
- Sketch `src/core.c`, `core.h`, `line_reader.c`, `line_reader.h` matched their shared originals byte for byte.
- `software/ball_demo/cli.py` contains both serial/trainer flags and portable-demo/calibration/delay flags; do not overwrite one feature set with the other.
- GitHub account had pull/push permission. No merge into main was performed.
- Old checkout had an unrelated local modification under `evidence/verification/20261009-ui-audit-01/emulator-boot.txt`; it was left alone.

Read `docs/README.md` and current branch instructions before source changes. Active application code is top-level `software/`, firmware is `firmware/`, verification tooling is top-level `tools/`. Older `simulation/software/` and `simulation/docs/` copies are not the active source.

## 3. Entire system, with three separate paths

### A. Pilot and optional computer assistance — the flight control path

```text
Pilot sticks + SA ARM switch on RadioMaster Pocket
                          |
Pi vision/yaw software -> USB serial -> ESP32-S3
                                      |
                           GPIO4 CPPM, breadboard/resistors
                                      |
                           Pocket DSC trainer 3.5 mm jack
                                      |
                    EdgeTX adds bounded yaw only, SD override
                                      |
                      Pocket internal 2.4 GHz ExpressLRS TX
                                      | radio link
                    FC built-in SPI ExpressLRS receiver
                                      |
                       Betaflight stabilization + mixer
                                      |
                           DShot300 -> onboard ESCs
                                      |
                                  four motors
```

The ESP32 does **not** connect directly to FC motor pads or replace Betaflight. It supplies trainer yaw to the Pocket. The Pocket sends the resulting channels over ELRS. Pilot retains throttle, roll, pitch, ARM/DISARM and physical override. V1 computer authority is yaw only.

### B. FPV and vision — an independent video path

```text
Aircraft FPV camera -> analog video transmitter (VTX)
          -> 5.8 GHz RF -> RC832 video receiver
          -> composite video cable -> VIXLW USB video capture adapter
          -> Raspberry Pi USB / V4L2 -> preview + tracking software
          -> bounded yaw calculation -> path A, only after its gates pass
```

**RC832 is a video receiver, not the ELRS control receiver.** VIXLW is a video capture device, not the ESP serial adapter. Their USB enumeration proves adapter detection, not that a live camera/video RF link works.

### C. Current bench motor test — bypasses the radio assistance path

```text
This Linux laptop -> USB serial -> FC MSP protocol
                                  -> disarmed Motor 1 command
2S battery -> FC/AIO ESC power bus -> onboard ESC 1 -> Motor 1
```

This path is how the recent motor tests were run. It did not send ESP commands, enable GPIO5, arm via the radio, or test computer yaw.

In the assembled drone, the FC normally runs from its battery; its saved Betaflight settings survive removal of the laptop USB cable. The flight control link remains Pocket -> ELRS -> FC. A permanent laptop USB connection is not required for normal flight.

## 4. Same laptop: software already available and serial access

Read-only inventory checked while preparing this file:

| Item | Actual state |
| --- | --- |
| OS / user | Pop!_OS 22.04 LTS / `chessdroid108` |
| System Python | `/usr/bin/python3`, **3.10.12** |
| pyserial | **3.5**, import succeeds; Debian package `python3-serial 3.5-1` |
| Chrome | `/usr/bin/google-chrome`; installed package `152.0.7977.82-1` |
| FFmpeg / ffprobe | `/usr/bin/ffmpeg`, `/usr/bin/ffprobe`; laptop FFmpeg package `7:4.4.2-0ubuntu0.22.04.1` |
| GitHub CLI | `/usr/bin/gh` |
| Betaflight GUI | Working browser application at `https://app.betaflight.com/`; both Chrome and Codex's visible in-app browser were used |
| ExpressLRS Configurator | User explicitly reported installation on this computer; exact installed version/path not inventoried here |
| Arduino CLI / picocom / esptool on laptop PATH | Not found by this inventory; do not assume absent from every venv, and do not install them for FC MSP tests |

**Python 3.10 works for the standalone MSP helper. The main project package documents Python >=3.13. Do not reinstall the whole application into system Python 3.10 or assume its environment matches the standalone script.**

FC device on **laptop**:

```text
/dev/serial/by-id/usb-Betaflight_Betaflight_STM32F411_0x8000000-if00
    -> /dev/ttyACM0
```

Its current ownership is `root:dialout`, with an explicit ACL granting `chessdroid108` read/write. This shell's `id` output does not include dialout. Account membership changes need a new login/process group context; that was the reason earlier advice mentioned logout/login. No logout is required to use the present working ACL.

If reconnecting USB drops the ACL, check the actual node, then restore user access if needed:

```bash
ls -l /dev/serial/by-id/
getfacl -p /dev/ttyACM0
sudo setfacl -m u:chessdroid108:rw /dev/ttyACM0
```

The user already authorized local access and supplied credentials in the conversation. **Passwords are not stored in this GitHub handoff.** Use available authenticated access; never put passwords in committed source, terminal transcripts, or command arguments.

Only one program should own FC USB at a time. Disconnect Betaflight before direct MSP work; close serial terminals before the GUI connects. Do not leave two browser windows trying to own the same device. An external Chrome launch used earlier was:

```bash
sg dialout -c 'google-chrome --user-data-dir="$HOME/.config/betaflight-browser" https://app.betaflight.com/'
```

The separate profile started a fresh Chrome process with the updated group context. It does not flash or change the FC.

### Current browser issue — don't waste time repeating it

After the first successful direct pulse, Codex spent too long trying to restore the in-app browser connection. The user objected. It repeatedly failed with **“No configuration received within 10 seconds, communication failed.”**

The device was present, no other process held it after failure, and a direct MSP API request still returned valid API 1.45 data. Direct motor commands subsequently worked. Thus, a failed browser reconnect did not establish a broken FC USB connection.

Last known Codex browser was disconnected on Welcome. The user wants a visible browser if it is used, but **does not require it for motor tests**. Claude may use Chrome, its own tools, a different serial client, or an improved MSP tool. Do not spend minutes navigating a GUI just to recreate a known command.

## 5. Raspberry Pi: different machine, different serial device

| Item | Last verified / reported |
| --- | --- |
| Pi | Raspberry Pi 5, hostname `raspberrypi` |
| Current network address | **`172.16.240.48`**, SSH worked in this chat |
| SSH username | **`hackphs`**, lowercase |
| Older addresses | `172.16.241.67`, `192.168.86.116`; historical, not current endpoints |
| ESP stable port on Pi | `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5876079136-if00` -> `/dev/ttyACM0` |
| ESP USB adapter | CH343, VID:PID `1a86:55d3`; Linux uses `cdc_acm` here |
| ESP terminal tools | `~/esp32-bridge/esp_term.py`, `ppm_probe.py`; hashes matched adopted branch |
| Existing server process | `/opt/ball-drone/software/.venv/bin/python -m ball_demo.cli serve --host 0.0.0.0 --port 8080` |

**Laptop `/dev/ttyACM0` is the FC; Pi `/dev/ttyACM0` is the ESP. Never confuse them.** The old Windows `COM3` name is irrelevant to current Linux connections.

The Pi server had **no serial argument** and did not own the ESP device when inspected. Do not silently restart it with trainer output or auto-enable assistance. Startup/restart stays MANUAL, disabled and mock unless deliberately configured for a separately verified session.

Example connection, not a command to run automatically:

```bash
ssh -t hackphs@172.16.240.48
cd ~/esp32-bridge
python3 esp_term.py --port /dev/serial/by-id/usb-1a86_USB_Single_Serial_5876079136-if00
```

`-t` provides the interactive terminal required by `esp_term.py`. If its Python lacks `serial`, the earlier Claude handoff reports `~/esp32-bridge/venv/bin/python` and esptool there. Existing binaries/backups reported on Pi: `ball_bridge_esp32.merged.bin`, `backup_before_flash.bin` (8 MB), and one-off `esp_bench.py`, `esp_disarm.py`, `esp_pulse.py`. Those latter scripts are not canonical repo tools; inspect before use.

Fresh HELLO checks in this chat, with GPIO5 reportedly out, returned:

```text
READY ... NO_OUTPUT
ACK ... 0 0 NONE
```

This establishes session state reported over serial. It does not prove the physical wire position, inspect oscilloscope output, or hash the running ESP image. No trainer enable was sent during motor work.

## 6. FC and ESC identity, firmware and saved configuration

Observed firmware identity:

```text
Betaflight / STM32F411 (S411) 4.4.2
Jul 3 2023 / 01:49:11
git 23d066d08
MSP API 1.45
board_name HGLRCF411SX1280V2
manufacturer_id HGLR
```

The board matches the **HGLRC Specter F411 10A 1–2S ELRS AIO / 400 mW VTX** target/product. Actual installed ESC firmware/version has **not been read**. The vendor describes Bluejay/BLHeli_S hardware; that is not proof of the particular flashed version or settings.

Relevant last observed/pasted settings:

| Setting | Value / status |
| --- | --- |
| Mixer | QUADX |
| Motor protocol | `DSHOT300` |
| `dshot_idle_value` | `1000` = UI motor idle **10%** |
| Bidirectional DShot | Off |
| ESC sensor | Off |
| 3D motor mode | Off |
| MOTOR_STOP | Observed off/disabled with AIRMODE in Motors UI |
| Current scaling | `ibata_scale = 470`; actual current accuracy unverified |
| Receiver mode/provider | SPI RX / EXPRESSLRS |
| ELRS UID | `44,106,241,247,157,34` after binding update |
| Channel map | AETR1234 |
| ARM range | AUX1, **1800–2100** |
| VTX | Raceband band 5, channel 8, **5917 MHz** |
| VTX power index | 4; supplied labels map this to **100 mW**, not proof of measured RF power |
| VTX low power disarm | ON |

The old pre-binding `diff -all` also contained `feature -RX_SERIAL`, `feature -SOFTSERIAL`, `feature -TELEMETRY`, `serial 0 2048 115200 57600 0 115200`, ELRS rate index 3 and HYBRID switch mode. It had an earlier, now superseded UID. **Do not restore that old diff wholesale.**

Original local backup: `/home/chessdroid108/Documents/betaflight-backup.txt`, also preserved if present in the dated source folder. It is from before final binding/ARM changes, not a current backup. The GUI Save-to-file download was confusing; user supplied CLI output instead. Copy/paste of the complete CLI `diff all` output into a text file is a valid configuration backup. A `diff` is differences from defaults, not a full `dump` and not a firmware image. Get a fresh backup before configuration/ESC changes.

No Betaflight flash, motor direction change, ESC startup-power change or idle change was made during the recent direct tests. The scripts do not call EEPROM save or calibrate sensors.

### What these electronics do

- FC reads gyro/accelerometer and receiver channels, runs Betaflight's stabilization and motor mixer.
- Four onboard ESC channels convert battery power into three-phase drive for four brushless motors.
- Each motor has three phase wires; connecting all three to one designated motor pad group is necessary.
- Battery powers the AIO ESC bus. **USB alone powers configuration electronics here; it does not supply motor drive power.**
- There is no software switch to physically supply battery power to only one ESC pad group. Select only Motor 1's command while leaving the other motor commands stopped. Insulate unsoldered wires.
- DShot is digital. Do not perform analog PWM throttle-endpoint calibration to troubleshoot DShot.
- A numerical motor test command such as 1020 is **not RPM**, a guaranteed speed, or a measurement of thrust/current.
- `dshot_idle_value` for normal armed operation is a different setting from the direct disarmed MSP motor test value. Changing idle is not an automatic fix for this bench symptom.

## 7. Pocket / ExpressLRS setup already completed

The user installed **ExpressLRS Configurator on the computer**. Installing that application alone does not flash the transmitter or receiver. In this chat the working RF configuration was established without a new FC flash:

- Pocket ExpressLRS screen showed **3.3.1 ISM2G4**.
- Pocket packet rate **plain 250 Hz**, Model Match **Off (ID:0)**.
- Binding phrase **`aahan`**, yielding UID **`44,106,241,247,157,34`** on both Pocket and FC.
- Betaflight **SPI RX** receiver mode and **EXPRESSLRS** SPI provider, saved/rebooted.
- After reboot/power cycling, user confirmed the Betaflight Receiver bars moved with the sticks.
- Betaflight 4.4's SPI ELRS receiver and ELRS v3 transmitter are the relevant compatibility pair. Do not update one arbitrarily while fixing the motor.

Mode 2 stick mapping physically confirmed by user:

| Control | Function |
| --- | --- |
| Left stick up/down | Throttle; down is minimum |
| Left stick left/right | Yaw |
| Right stick left/right | Roll |
| Right stick up/down | Pitch |
| SA -> radio CH5 -> Betaflight AUX1 | ARM switch; low ~1000 off, high ~2000 in ARM range |

Receiver bars in failsafe earlier were Roll/Pitch/Yaw 1500, throttle 885. Those were failsafe values, not live reception. Once binding matched, ordinary stick reception worked.

The Modes page can show **ARM (DISABLED)** even while AUX1 is inside its range because USB/MSP or another arming-disable reason prevents actual arming. Range selection is not proof the aircraft is armed, and a grey Save button can simply mean no pending changes remain.

Radio-loss check was done **while disarmed and USB connected**: failsafe indication and fallback channels appeared when radio was off, and normal reception returned afterward. Last reviewed failsafe settings were Stage 2 **Drop**, Stage 1 delay **1.5 s**, throttle-low delay **10 s**, channel auto/AUX hold. This does **not** prove an armed in-flight failsafe. Never substitute trainer command-loss neutralization for the independent RF-loss failsafe.

Pocket “Shut down? Model still powered on” warning means it still sees a powered receiver/model. Powering it off during an intentional disarmed failsafe check is different from powering it off with an armed aircraft.

## 8. ESP32, breadboard and trainer cable — adopted Claude details

Board is **Freenove ESP32-S3 WROOM**, not ESP32-S2, and the team does **not** have an Arduino Mega 2560. Pico/RP2040 and Mega artifacts are historical source evidence, not the currently connected bridge.

The board has **two USB-C ports**. USB-C describes connector shape; USB-UART and USB-OTG describe functions. Use the **USB-UART / CH343 port next to BOOT**, as established in the earlier handoff. ESP is connected to Pi USB, not directly to FC.

### Header orientation and exact wiring

From the earlier Claude handoff: components facing up, USB-C connectors pointing toward you. Count header positions from the far end (**1**) to the USB end (**20**). Identify the actual silkscreen on this exact board before moving wires.

| Relevant position | Function |
| --- | --- |
| Left header position 3 | **GPIO4**, PPM output |
| Left header position 4 | **GPIO5**, output safety jumper input |
| Right header position 20 | **GND**, correct common ground |
| Left header position 20 | **5V**, leave empty in this trainer circuit |

**“GPIO5” is a GPIO label, not header position 5.** In this orientation GPIO5 is left header position 4. The user's “pin 5 off the rail” referred to GPIO5.

An earlier wrong connection from the ESP's **5V** header to the ground rail reportedly triggered Pi USB overcurrent protection. Do not recreate it. Camera ribbon is unplugged because GPIO4/5 are shared with camera SCCB on this board.

Current cable plan: an ordinary **stereo 3.5 mm TRS AUX cable**, with one end stripped into a pigtail and the other plugged into the Pocket's recessed **DSC Trainer** jack. User does **not** have the proposed mono screw-terminal adapter. They are using breadboard/jumpers, not adding secure terminal blocks.

Identify conductors by continuity to plug contacts, with power off. Do not assume colors. Tip is the end contact, ring is the middle band, sleeve is the contact nearest the cable. This connector carries control pulses, not audio. A mono plug recommendation does not remove the ring-detect issue for the stereo plug actually being used.

Use only the available **2 kΩ resistors** in this adopted circuit:

| From | Via | To | Role |
| --- | --- | --- | --- |
| ESP right header pos.20 GND | Jumper | Breadboard − rail | Common ground |
| ESP left header pos.3 GPIO4 | Jumper to a free connected row A | Row A | PPM source |
| Row A | **2 kΩ series resistor** | Separate free connected row B | Series signal resistor |
| Row B | Jumper / identified cable wire | Plug **tip** | Radio PPM input |
| Plug **ring** wire | Separate row C, then **2 kΩ** | − rail | Active-low cable detection |
| Plug **sleeve** wire | Jumper | − rail | Trainer ground |
| ESP left header pos.4 GPIO5 | Removable jumper | − rail **only when deliberately enabling a trainer session** | Output safety input |
| ESP USB-UART USB-C | USB cable | Pi USB | Serial + power |
| ESP left header pos.20 5V | **Nothing** | **Nothing** | Leave empty |

Rows A/B/C mean distinct electrical breadboard strips, not arbitrary numeric rows. Confirm how the breadboard rails are split before relying on rail continuity. No metal clips or loose strands should bridge powered pads.

**For the motor issue now, GPIO5 remains OUT. Do not rebuild or enable this circuit as a motor fix.**

Claude reported Pocket jack measurements: tip = PPM input with about 3 kΩ loading to ground; ring = cable-detect pull-up about 2.98 V, active low; sleeve = ground. Ring must be grounded through the 2 kΩ resistor for this TRS setup or the Pocket ignores trainer input.

Reported meter readings with radio on and cable inserted: ring 0.01–0.07 V, signal tip about 2.0 V idle / 1.8 V streaming. These are loaded/averaged values, not the actual waveform amplitude/timing. A meter alone cannot prove PPM timing.

### No oscilloscope available — existing alternate check

Earlier session decoded PPM using Pi GPIO17 and `ppm_probe.py`:

- Signal row B -> **another 2 kΩ** -> Pi **GPIO17 / physical header pin 11**.
- Pi **GND physical pin 39** -> shared − rail.
- Both GPIO logic domains are 3.3 V; never put 5 V into a Pi GPIO.
- `ppm_probe.py`'s old docstring says 1 kΩ and GND pin 6. The handoff says actual bench used 2 kΩ and pin 39; use that documented bench wiring.
- Script locates the Pi 5 RP1 GPIO chip and decodes falling edges. It is not an oscilloscope.

## 9. ESP firmware and Pocket trainer behavior

Active sketch: `firmware/esp32/ball_bridge_esp32/` (`.ino`, `ppm.cpp/.h`, `src/core.*`, `src/line_reader.*`). Earlier Claude reported it already flashed, built with Arduino-ESP32 core **3.3.12**, 8 MB flash. Codex inspected matching source and Pi terminal tools, but did not reflash or hash the running binary.

| Behavior | Exact implementation / scope |
| --- | --- |
| Serial | `Serial0`, **115200 8N1**, newline-delimited protocol v1 |
| Output | GPIO4 CPPM, idle **HIGH**, **300 µs LOW separators** |
| Frame | **8 channels**, **22,500 µs / 22.5 ms** (~44 Hz) |
| Data channel | CH4 only: `1500 + yaw*150/1000` µs, C integer truncation |
| Yaw range | Protocol ±1000 -> CH4 **1350–1650 µs** |
| Other channels | CH1–3 and CH5–8 fixed **1500 µs** |
| GPIO5 | INPUT_PULLUP, ground = output permitted; sampled on each HELLO |
| READY | `PPM_YAW` if grounded at HELLO, otherwise `NO_OUTPUT` for that session |
| Jumper removed | Latched session disarm; **3 neutral frames**, then idle HIGH; reinsertion alone does not resume |
| New session | Requires another HELLO after grounding GPIO5 |
| Command watchdog | No valid command for **250 ms** -> yaw neutral; stream continues while output session is armed |
| Loop stale guard | Stale for **5 frames** (~112.5 ms) -> neutral |

Protocol:

```text
HELLO 1 <session>
READY 1 <session> PPM_YAW          # or NO_OUTPUT
CMD 1 <session> <strictly-increasing-seq> <enable-0-or-1> <yaw>
ACK 1 <session> <seq> <accepted-enable> <accepted-yaw> NONE
```

Fault code can replace NONE. Disabled commands carry yaw 0. An ACK is accepted **internal state**, not measured radio/FC output. `esp_term.py` sends every **50 ms**, defaults disabled/yaw 0, and deasserts DTR/RTS to avoid USB-UART reset/bootloader entry.

Terminal commands: `on` enables computer yaw, `off` disables/zeros, `y 1000` requests positive limit, `y -1000` negative limit, `y 0` neutral, `pause` stops commands for watchdog testing, `resume` resumes, `hello` restarts session/re-reads jumper, `status` prints reported state, `quit` sends disabled frames then exits.

Known open bug: `esp_term.py` closes serial while its reader thread may still be reading. Earlier handoff called the exit exception cosmetic; cleanup still deserves a reader stop/join before close if this tool is maintained. Do not confuse it with successful physical neutralization.

Pocket configuration reported by earlier Claude:

| Setting | Value |
| --- | --- |
| Wired trainer mode | Master/Jack input path |
| SYS -> Trainer -> Rud | **`+=`, weight 30, source CH4** |
| Trainer Ele / Thr / Ail | OFF |
| MODEL -> Special Functions | **SD down -> Trainer -> Rud**, enabled |
| SD up | Pilot only, trainer yaw cut off |

The rightmost SYS Trainer calibration number is raw CH4 and ignores SD; home-screen **Channel Monitor** shows the actual mixed channel. A new special function may default to “Override CH1 0”; do not leave that accidental aileron override in place.

Earlier Claude measured (not repeated in this Codex motor session):

- Pi decode CH4 yaw 0/+500/−1000 = **1500/1576/1349 µs**, separator **299.3 µs**, frame **22500.2 µs**.
- Watchdog returned CH4 to neutral.
- Pulling GPIO5 gave neutral tail then idle, remained idle 3 s despite continued enabled commands; 205 ACKs, 0 faults in that reported run.
- Pocket raw trainer CH4 = 0/+29/−29 for yaw 0/+1000/−1000.
- Pocket mixed Rud = 0 with SD up; about **+7/−8** with SD down at weight 30.
- These establish the reported ESP-to-radio bench stage, not the complete computer-to-FC path.

Do not raise trainer weight or expand control authority as part of motor troubleshooting. No new ESP flash is needed for direct FC MSP tests. If flashing later becomes necessary, the earlier handoff reports Pi esptool with `-b 921600`; inspect image/version and preserve backups first. `flash.ps1` is Windows-only, not this Linux workflow.

## 10. RC832 / VIXLW: actual detection, black video and remaining work

User's actual Pi output showed:

```text
lsusb: 534d:0021 MacroSilicon MS210x Video Grabber [EasierCAP]
v4l2-ctl --list-devices:
  USB Video: USB Video
    /dev/video0
    /dev/video1
    /dev/media3
```

`/dev/video0` was **Video Capture + Streaming**, driver **uvcvideo**, serial **20200909**, 720×576 YUYV at 25 fps when inspected. `/dev/video1` was **UVC metadata**, not a second usable camera feed. Pi's `pispbe` `/dev/video20...35` and HEVC `/dev/video19` were unrelated internal devices.

Reported formats included YUYV 720×576 at 25 fps, 720×480 and 640×480 at 30 fps; MJPEG listings included larger formats. These are adapter-advertised modes, not proof that the analog source has corresponding true optical resolution/frame rate.

On Pi, `v4l-utils 1.30.1-1` and FFmpeg `8:7.1.5-0+deb13u1+rpt2` were already installed. `picocom 3.1-4+b1` was installed for ESP serial use. User ran:

```bash
sudo picocom -b 115200 /dev/serial/by-id/usb-1a86_USB_Single_Serial_5876079136-if00
```

It showed ESP-ROM esp32s3 boot output. That proved serial/boot traffic then, not project firmware or PPM. Exit picocom with Ctrl+A then Ctrl+X so it releases the port.

Video was black because the user said the FPV camera was not yet set up. Earlier project Pi capture also saved uniformly black frames. **Live FPV, a real camera scene, target tracking from that scene and RF video quality remain unverified.** Do not treat USB capture enumeration or black frames as proof RC832 RF reception works.

When returning to video, verify camera power/video wiring, VTX antenna and correct supply, RC832 power/antenna, matching RF channel (last FC VTX setting R8 / 5917 MHz), RC832 composite video output into capture video input, then a changing real scene on Pi `/dev/video0`. Current RC832 knob/channel/power settings were not freshly inventoried.

Example local Pi desktop preview after checking device format:

```bash
ffplay -f v4l2 -input_format yuyv422 -video_size 720x576 -framerate 25 -i /dev/video0
```

This opens a window only in a usable desktop/display session. Plain headless SSH does not magically put a window on the laptop. Do not use the literal placeholder `/dev/videoN`; user tried it and got “No such file.” A headless capture to an image/video is a different operation and needs no preview window.

## 11. Motor test history — exact settings, results and limits

No props-on tests, full-aircraft arming, lift tests or flight occurred. Only Motor 1 has been driven. Direction, real RPM, thrust, current draw, winding integrity and continuous reliable startup are not established.

| Attempt | FC command / method | Measured electrical replies | Physical outcome |
| --- | --- | --- | --- |
| Battery initially connected | No intentional spin command; FC already on USB | No repeating full boot tune reported | User heard one beep about every 2 s; motor twitched only with beep |
| Browser keyboard attempt | Tried keyboard on Motors slider; keyboard invokes GUI stop | All displayed commands stayed 1000; risk toggle later unchecked | Not a valid successful run |
| Direct pulse ~0.7 s | MSP214 Motor1=1020, others=1000; independent 0.8 s stop timer | Battery **7.46 V**, `armed=false`; during `[1020,1000,1000,1000]`, after all1000 | User later explicitly confirmed **brief spin ~0.7 s** |
| Direct sequence 2 s then10 s | Same1020, stop between pulses, no5 s stage | Battery **7.31/7.30 V**, both readbacks correct, after each all1000 | User confirmed2 s; unsure whether10 s continuous or bursts |
| Direct monitored10 s retry | Same1020; read MSP104 about every0.5 s | Battery **7.03 V** before run; every sample ~0.64–9.87 s was `[1020,1000,1000,1000]`; final all1000 | **User confirmed intermittent rotation: spin/stop repeated** |

The “armed false” state above means FC was disarmed. Initial RC readbacks were `[1505,1500,1500,1293,1000]`; retry throttle1294. Command order is Roll, Pitch, Yaw, Throttle, AUX1.

First battery-only twitch/beep could be ESC beacon behavior because ESC beeps are generated through motor windings. Exact installed beacon delay/strength has not been read. It was not a sustained-spin test. A motor making the beep can move slightly without proving normal commutation.

USB first, then battery is a normal bench arrangement. When user unplugged battery, FC briefly disconnected/reconnected. A supply handover reset is plausible, but not established as harmless or faulty here. If full startup melody repeatedly occurs during a commanded run, or USB resets under drive, inspect power/connectors/solder and measure voltage before blaming low speed.

### Why direct USB and what it actually controls

We used **MSP binary serial**, not the text Betaflight CLI and not GUI navigation. Already installed Python+pyserial is sufficient. The intended nonzero value is sent once; FC's inspected 4.4.2 motor handler assigns `motor_disarmed[]`, and its mixer uses that state while disarmed. We did not intentionally program 2-second bursts during a10 s run or repeatedly send stop commands before its deadline.

Motor command feedback is not RPM feedback. Bidirectional DShot/RPM telemetry was off. Stable MSP104 values narrow the problem but do not prove the ESC kept commutating, rule out every brief supply fault, or certify physical rotation between samples.

Protocol used:

| MSP ID | Purpose |
| --- | --- |
|1|API version; actual1.45|
|3|FC version; actual4.4.2|
|99 payload `01 00`|Block normal arming via MSP; retain runaway prevention|
|101|Status; mode bits combined with BOXIDS to determine ARM|
|104|Motor output command readback|
|105|RC channels|
|110|Analog; actual voltage `uint16` offset7 divided100 for API1.45|
|119|Mode/BOX IDs; ARM ID0|
|214|Set disarmed motor commands, little-endian `uint16` values|

MSPv1 request is `$M<` + payload length byte + command byte + payload + XOR checksum. Replies use `$M>` or `$M!`; check length, command and checksum. Recent scripts supplied8 motor values, first4 meaningful, unused remaining at1000. They never sent RC overrides or an ARM command.

**Temporary normal-arming block was deliberately left in place.** Exiting Python is not a command to re-enable normal arming. Before eventual normal flight, inspect arming-disable flags and perform deliberate safe reconnect/power cycle/configurator handling; do not silently clear arming blocks with a propeller fitted.

## 12. Immediate troubleshooting plan — in this order

### Step1: stop, power off, inspect the actual motor path

1. Unplug battery, then USB before touching solder or motor wiring. Keep props removed.
2. Check motor and ESC temperature after cooling enough to touch safely. Record unusual heat/smell/discoloration; do not continue driving a hot/stalled motor.
3. Inspect all **three Motor1 solder joints** for a detached wire, poor wetting, stray strand, bridge to adjacent pads, or lifted pad. The prior photo did not resolve the solder quality. A closeup is helpful but was never made a mandatory prerequisite.
4. Insulate disconnected motor wires so they cannot contact FC pads, USB shell or carbon frame.
5. With no power, rotate the motor bell gently. Magnetic notches are normal; scraping, rubbing, substantial binding or a screw contacting a winding is not. Verify motor mounting screws do not reach windings.
6. Check XT30/battery leads and mechanical strain on the loose FC; don't solve an intermittent joint by holding bare powered contacts.

### Step2: check the supply rather than assuming the label proves it

Battery user label: **450 mAh,100C,2S1P,7.6 V,3.42 Wh**. This is a2-cell LiHV-style nominal label; it is not the actual charged voltage. Latest measured total was7.03 V and had fallen from earlier7.46 V. Do not infer per-cell balance or health from the total.

- Check resting total and, if equipment exists, each cell. Use a correctly prepared2S pack and the correct charger chemistry/settings.
- Board vendor gives1–2S; explicit permission for **8.7 V fully charged LiHV** was not established. Keep diagnosis within the known conservative **<=8.4 V** supply envelope unless the exact board specification is independently resolved. Do not prescribe4.35 V/cell charging from the7.6 V sticker.
- Observe voltage during a short run. Old scripts sampled voltage before each pulse, **not continuously throughout it**. The new wrapper adds voltage sampling, but has not been exercised on hardware.

### Step3: one short, slightly higher diagnostic pulse

Only after physical/supply checks pass, the proposed next test is **Motor1=1040 for2 s**, with all other outputs1000, SA off, props removed, GPIO5 out. **This test has not yet been run.** Tell user when it starts so they can watch and be ready to disconnect battery if stop fails.

1020 is a very low command near the stopped endpoint; insufficient low-throttle startup/commutation power is a **plausible hypothesis**, not an established diagnosis. A modest short increase can distinguish that from inability to run at all.1040 is not a guaranteed RPM or a guaranteed “very slow” speed. Do not jump to high output or another long stalled10 s run.

If1040 is steady, record observed startup/continuous rotation/stop and voltage, then evaluate whether lower startup threshold or installed ESC startup settings are the cause. If1040 still stops/restarts, stop escalating and inspect wiring, motor and ESC/supply. No flight until consistent behavior is demonstrated.

### Step4: inspect actual ESC firmware/settings before changing them

- Make a fresh FC backup first.
- Read actual ESC1 firmware/version and settings through an appropriate existing ESC passthrough/configuration tool if available. ExpressLRS Configurator is for RF firmware, not ESC settings. Betaflight app is FC configuration, not proof of ESC flash identity.
- Do not assume Bluejay is installed solely from the product page. If it is, inspect PWM frequency, minimum/maximum startup power, timing/demag/ramp-up and motor direction. Preserve a before-state.
- Bluejay documentation specifically notes that small motors can need more startup power at low throttle. That is a candidate diagnosis; blindly copying settings or reflashing all ESCs is not the first action.
- If USB resets or full boot melody repeats, prioritize power interruption/sag. If motor stutters without FC command changes, inspect phase connection/mechanical load/startup/ESC desync possibilities. A motor or ESC substitution can isolate a faulty component once wiring and bench setup allow it, but is not yet performed.
- DShot300 itself does not require endpoint calibration. Do not use “calibrate ESC” as a vague substitute for identifying the symptom.

## 13. Finishing FC/motor configuration after this fault is resolved

The full aircraft is incomplete. Do the following with props removed, and label physical results:

1. Finish soldering all four motors; inspect pad groups/phase joints, loose strands, battery pads, insulation, shorts to the carbon frame. Connect each motor to its own pad group.
2. Mount FC on the intended insulated/soft supports, establish the aircraft nose and board orientation; route antenna/cables away from prop disks and gimbal travel. Do not use bare metal helping-hand clips on powered board pads as a permanent mount.
3. In Betaflight Setup, move the physical aircraft in roll/pitch/yaw and verify the3D model follows correctly. Configure board alignment if the board's orientation differs from aircraft orientation; don't mistake accelerometer calibration for board alignment.
4. With aircraft level and still in final mounted attitude, **recalibrate accelerometer**. Prior loose-board calibration (~pitch−0.2°,roll0°) only cleared a bench warning. User explicitly said recalibration is needed later.
5. Confirm QUADX and DShot300 persist. Inspect actual motor idle and ESC settings; keep deliberate changes documented rather than “fixing” everything at once.
6. Use Betaflight's actual QUADX motor diagram to identify physical positions. **Motor1 electrical connection was user-confirmed, not independently tied to its final frame corner.** Command each motor individually and verify the correct physical one responds. Current scripts intentionally support only Motor1; don't use master/all-motors control to determine numbering.
7. Verify each motor's physical rotation against the selected props-in/props-out configuration. Set direction with the appropriate supported ESC/DShot tool if necessary. Neither direction nor prop orientation has been verified here.
8. Recheck AETR channels, true minimum throttle, center/endpoints, SA ARM range and any intended mode switch. Center ~1500 and endpoints near1000/2000 are targets to measure, not guarantees.
9. Check actual failsafe setup and RF-loss behavior with a properly assembled props-off aircraft. A disarmed channel-loss indication from earlier is not the full flight gate.
10. Recheck normal arming-disable reasons safely after MSP motor testing. USB/MSP/CLI arming inhibition is expected during bench configuration. Never defeat an inhibition merely to make ARM turn green.
11. Only after motor order/direction, assembly, failsafe, battery and pilot controls are sound should props be installed for a separate controlled flight readiness step. The single-motor setup cannot stabilize or fly as a quad.

Original user shorthand “ABCD” referred to an earlier4-step FC checklist, but the precise earlier assistant definitions are not retained reliably in this handoff. **Use explicit task names instead of inventing what those letters meant.**

### Current capacity questions

Vendor rating: onboard ESCs **10 A continuous /13 A for10 s**,1–2S. User's motor plan: Specter1202.5 **11000KV**,2-inch props, Apex-2 ~95 mm frame. Actual motor+prop2S current draw has not been measured; compatibility is not proven by idle bench rotation.

450 mAh×100C gives a nominal marketed discharge figure of45 A, but that is not a measurement of the pack's real usable current, voltage sag or health. It also does not raise each ESC's10 A limit. Excess load can overheat ESC/motor, sag the battery, reset electronics or damage components. Start with props-off diagnosis; a future loaded-current/thrust check is separate.

User also reported four450 mAh packs and two OVONIC2S7.6 V60C XT30 **1100 mAh** packs. The larger listing is inconsistent and exceeds the frame seller's650 mAh recommendation; those packs remain unverified candidates, not approved replacements for this motor test or a measured CAD mount.

## 14. Optional direct USB helper and exact original code

**Claude is free to use a better solution.** This is a convenience tool, not a required architecture or an instruction to bypass checks. It accesses FC MSP directly; it does not navigate browser controls.

### Original scripts that actually ran

| Laptop temporary file | Published exact inert snapshot | What it did |
| --- | --- | --- |
| `/tmp/hackphs_motor1_pulse.py` | `docs/sources/bench-handoff-2026-10-11/hackphs_motor1_pulse.py.txt` |1020 for~0.7 s,0.8 s independent stop timer|
| `/tmp/hackphs_motor1_2_then_10.py` | `docs/sources/bench-handoff-2026-10-11/hackphs_motor1_2_then_10.py.txt` |2 s then10 s at1020, verified stop between|
| `/tmp/hackphs_motor1_10_monitor.py` | `docs/sources/bench-handoff-2026-10-11/hackphs_motor1_10_monitor.py.txt` |10 s at1020; command samples~0.5 s apart|

**Do not import or run those temporary scripts to inspect them. They open USB and start the test at top level.** Read them as text. The committed `.py.txt` snapshots are deliberately inert. They include Ctrl+C/SIGTERM stop handling, a finally stop path, a separate stop timer, voltage/ARM gates and stop readback. They do not protect against every host crash, kill−9, USB cable removal or MCU fault. If software stop is unconfirmed and motor moves, disconnect battery.

### New optional reusable wrapper

File: `tools/betaflight_motor_bench.py`. Same already-installed pyserial dependency. Import-safe; requires an explicit `status`, `stop` or `pulse` subcommand. Supports Motor1 only and limits this diagnostic implementation to value1001–1040 and one/two durations up to10 s each. Requires explicit `--props-removed` attestation for movement.

Compared with the exact old scripts, it additionally polls voltage during the pulse and uses a more conservative **6.8–8.4 V** diagnostic gate (old scripts used6.4–8.4 V). It verifies the known BF4.4.2/API1.45 before a pulse and checks ARM/command state. It keeps the normal-arming block after stop. Its thread timer is a best-effort host cleanup, **not an independent hardware failsafe**.

**This wrapper was prepared for this handoff; no hardware pulse or automated test was run against the new wrapper. Only the original scripts have the real bench execution evidence above.** Review it before use. `status` does not deliberately mutate the FC; `stop` blocks normal arming and commands stop; `pulse` is a physical action.

From the active checkout, examples only:

```bash
# Read firmware, voltage, receiver channels and motor commands; no pulse.
python3 tools/betaflight_motor_bench.py status

# Block normal arming and send all motor outputs to stop.
python3 tools/betaflight_motor_bench.py stop

# PHYSICAL ACTION: proposed next diagnostic, only after physical checks pass.
python3 tools/betaflight_motor_bench.py pulse --value 1040 --seconds 2 --props-removed

# PHYSICAL ACTION: reproduce earlier low-setting sequence if deliberately needed.
python3 tools/betaflight_motor_bench.py pulse --value 1020 --seconds 2 10 --props-removed
```

Global `--port` must appear before the subcommand when overriding the stable alias. Keep logs in ignored runtime storage, e.g. `runs/motor-bench/`, and preserve selected reviewable summaries separately. Do not include tokens or credentials in logs.

Full wrapper code is included at the end of the standalone file so the handoff works even before Claude opens the checkout.

## 15. Remaining complete trainer verification — after motor issue, not instead of it

Ordinary Pocket-to-FC binding/stick motion has passed. **The20 disarmed computer-yaw end-to-end trials are still pending.** Earlier Claude's original handoff asked for them and Linux tests; neither was completed while the motor issue took priority.

For each of20 props-off, disarmed trials, record BF version/channel map/RC baseline, measured Yaw values, all other axes/AUX and Pocket messages:

1. Enable a deliberately armed PPM session only when ready; SD down, yaw0. Check neutral and pilot sticks.
2. Send yaw+1000,−1000,0. At weight30 expect about **±40 µs** around the actual stick-centered FC Yaw, with an allowance about±10 µs. This is an expected range, not a passed measurement. Record sign; positive should consistently increase FC Yaw.
3. Check combined stick extremes for clipping/wrap/glitches; authority must stay bounded.
4. SD up must remove trainer yaw immediately in the displayed channel; SD down restores permitted contribution.
5. `pause` commands: ESP250 ms watchdog neutralizes. Measure timing where possible; GUI “within a blink” is qualitative, not a precise latency result. Resume restores intended input.
6. Remove GPIO5: neutral tail then no PPM, yaw stays pilot-only; another HELLO with jumper out must returnNO_OUTPUT. Record trainer-lost message/sound.
7. Reground GPIO5 and newHELLO, on, yaw0: PPM_YAW resumes correctly.
8. **No crosstalk:** throttle/roll/pitch/AUX/ARM never move due to ESP actions. Vary± order; include a fresh ESP power-cycle trial.

First failure: stop, save actual values and report. Do not silently fix and label20/20. Weight remains30 until deliberate scope decision and repeated override/loss checks. Channel tests do not prove correct physical steering direction under flight dynamics.

Reported Linux test commands from original handoff are retained in its source snapshot. They include `test_esp32_bridge.py`, `test_protocol_exhaustive.py`, `test_protocol_parity.py`, `test_serial.py`, `test_follow_simulation.py`, PPM C++ host simulation and shared C core/line-reader tests. **Linux results for this adopted branch are not established by this chat.** Use the proper project interpreter/compiler environment; do not mistake older Windows/Mac/container evidence or system Python3.10 for a current actual-Pi check. When comprehensive verification is requested, follow `tools/verify.py`/current docs and preserve failed reports.

## 16. Main application, scope and demo constraints

- Pi4/5 tracking/server support is planned in current source; actual connected device here is Pi5. Existing deployed path is `/opt/ball-drone/software/.venv` and port8080. No claimed end-to-end live camera/automatic steering acceptance.
- Host pipeline is video capture -> detector/tracker -> bounded yaw controller -> versioned serial bridge. Capture loss, ACK loss, disable and faults must directly neutralize rather than leave stale yaw.
- `serve --serial ... --baud115200 --trainer-output` accepts PPM_YAW mode only by explicit opt-in. No serial argument means the existing mock/manual path. Don't enable this server while independently driving `esp_term.py` on the same port.
- Flutter desktop/web/Android client and portable visual mission backend exist. Relative tracking/AprilTags/synthetic follow/landing are software work; **physical autonomous follow/landing remains unavailable**. Audio/TTS, WebRTC audio, D435 room mapping and Pico wireless audio are deferred/out of scope.
- Native Qt workstation is optional; it is not needed for motor testing. Do not make the user reinstall Qt or use an Arduino GUI.
- Wasim's root `server.py`/`static/` simulator is illustrative and separate from live FPV; its older Meteor85 model is not physical telemetry from this quad.
- Physical build target is Apex-2 (~95 mm), Specter1202.5 11000KV,2-inch props,245–250 mm cage and **P1B two-ring gimbal**. Fixed P1A cage is CAD-only.
- Physical acceptance target: ten consecutive undamaged/no-prop-strike contacts, at least3 minutes usable caged flight, repeatable manual recovery. None established here.
- Manual flight/contact plus live target tracking is an accepted fallback. Display “Manual steering — computer steering unavailable” if assisted path isn't ready. Pilot authority stays intact.
- NoGPS requested. Do not add GPS while diagnosing the motor.
- Extra hardware contingency cap$200 with at least$30 reserve; prioritize working core. Freeze new hardware/features48 h before first judged demo, final24 h reliability/batteries/evidence/rehearsals. No new purchases are required for the direct USB helper.
- Linux runnable files need no special extension: Python `.py` uses an interpreter; executable scripts need permissions/shebang; this does not require creating a Windows `.exe`.

## 17. Evidence files and screenshots on this laptop

| File | What it contains / caveat |
| --- | --- |
| `/home/chessdroid108/Downloads/codex-github-source-review-2026-10-11.md` | Repo adoption/source comparisons, before later motor work |
| `/home/chessdroid108/Downloads/motor1-usb-test-2026-10-11.md` | First0.7 s command result; still says user observation pending because it predates confirmation; this handoff records confirmation |
| `/home/chessdroid108/Downloads/PXL_20261011_060719736.mp4` | Earlier user video,5.1328 s,854×480,30 fps; twitching, not sustained rotation proof |
| `/tmp/hackphs-motor-video-20261011/contact-sheet.png` | Extracted visual review; motor stationary most frames with angular twitches around1.5/4.5 s |
| `/tmp/betaflight-failsafe-2026-10-10.jpg` | Disarmed RF-loss state |
| `/tmp/betaflight-accelerometer-calibrated-2026-10-10.jpg` | Loose bench calibration, not final mounting |
| `/tmp/betaflight-receiver-precheck-2026-10-11.jpg` | Receiver state before motor work |
| `/tmp/betaflight-throttle-arm-verification-2026-10-11.jpg` | Throttle/ARM check |
| `/tmp/betaflight-motor-power-check-2026-10-11.jpg` | Motor power check |
| `/tmp/betaflight-reconnected-stopped-2026-10-11.jpg` | Earlier stopped state |
| `/tmp/betaflight-after-direct-motor1-test-2026-10-11.jpg` | Disconnected Welcome UI after reconnect failure; **not a motor telemetry screenshot** |

`/tmp` files may disappear on reboot. Exact script text and selected source records are now committed as dated snapshots. Raw videos/screenshots and runtime tokens were not bulk-published. This handoff is a session reconstruction, not an independent instrument log for every statement.

## 18. Primary references

- [Betaflight4.4.2 MSP motor handler](https://github.com/betaflight/betaflight/blob/4.4.2/src/main/msp/msp.c#L2845): assigns the disarmed command state.
- [Betaflight4.4.2 mixer source](https://github.com/betaflight/betaflight/blob/4.4.2/src/main/flight/mixer.c): disarmed motor outputs use that state.
- [Betaflight Motors tab](https://betaflight.com/docs/wiki/app/motors-tab): props-off motor testing, individual controls, USB-disconnect limitations.
- [Bluejay settings](https://github.com/bird-sanctuary/bluejay/wiki/Settings): startup power, timing, beacon and heat cautions; installedESC identity still pending.
- [HGLRC Specter10A product](https://www.hglrc.com/products/hglrc-specter-10a-1-2s-elrs-aio-vtx-400mw-f411-flight-control-10a-bl_s-5-in-1-fc): vendor ratings, not measured installed firmware/current.
- [ELRS SPI receivers](https://www.expresslrs.org/hardware/spi-receivers/), [pre-first-flight checks](https://www.expresslrs.org/quick-start/pre-1stflight/), [WebUI](https://www.expresslrs.org/quick-start/webui/).
- [Betaflight sensor calibration](https://betaflight.com/docs/wiki/app/sensors-tab), [FC orientation](https://betaflight.com/docs/wiki/guides/current/Flight-Controller-Orientation), [Linux USB permissions](https://betaflight.com/docs/wiki/guides/current/USB-Flashing).
- [Freenove USB guide](https://docs.freenove.com/projects/fnk0085/en/latest/fnk0085/codes/C/35_USB.html): USB-UART versus USB-OTG.

## 19. How Claude should work with the user

- Be concise in chat; keep detailed evidence in files. State action, duration and setting before physical movement.
- Be fast without skipping stop verification. Direct MSP is available; browser navigation is optional. No routine reinstallations, GUI reconnection loops or unrelated feature work.
- User has authorized device access and is frustrated by repeated permission prompts. Required missing physical facts can still be requested succinctly. A handoff statement is not a live temperature/wiring/prop check.
- Never call an output ACK “motor spinning.” The user observes rotation; command feedback and RPM sensing are different evidence.
- Don't repeat1020 ten-second runs indefinitely after known intermittent spin. Follow section12.
- Don't change ESP wiring/enable trainer while troubleshooting Motor1. Keep SA off and GPIO5 out; reconcile throttle reading before normal arming.
- Stop immediately and arrange battery disconnection if a commanded stop isn't physically achieved, USB fails while moving, or motor/ESC overheats.
- Capture the next finding in a clear summary: exact command, duration, voltage, physical outcome, stop verified/not verified, configuration changes if any.
- Do not flashFC/ESC/ESP, claim all motors configured, claim20/20 trainer trials, or call the aircraft flight-ready based on this chat.

**First message to the user should identify the actual priority: Motor1 intermittently spins at a steady1020 command; inspect the unpowered hardware/supply, then one short1040 diagnostic if those checks pass.**


## Appendix A. Full optional USB helper source

This is a convenience implementation, not a requirement for Claude. It was not executed against hardware during handoff preparation.

```python
#!/usr/bin/env python3
"""Optional direct-USB bench helper for the known Betaflight 4.4.2 FC.

No browser automation and no installation step. Uses existing pyserial.
Importing this module does not open USB or move a motor. See the dated handoff.
Output readbacks are commands, not measured RPM or proof of physical rotation.
"""

import argparse
import json
import signal
import struct
import sys
import threading
import time

import serial


DEFAULT_PORT = '/dev/serial/by-id/usb-Betaflight_Betaflight_STM32F411_0x8000000-if00'
STOP = struct.pack('<8H', *([1000] * 8))


def report(**fields):
    print(json.dumps(fields), flush=True)


class FC:
    def __init__(self, port):
        self.ser = serial.Serial(port, 115200, timeout=0.02,
                                 write_timeout=0.1, exclusive=True)
        self.buf = bytearray()
        self.write_lock = threading.Lock()
        self.ser.reset_input_buffer()

    def write(self, command, payload=b''):
        body = bytes([len(payload), command]) + payload
        checksum = 0
        for value in body:
            checksum ^= value
        frame = b'$M<' + body + bytes([checksum])
        with self.write_lock:
            if self.ser.write(frame) != len(frame):
                raise IOError('Incomplete serial write')

    def request(self, command, payload=b'', timeout=0.4):
        self.write(command, payload)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.buf.extend(self.ser.read(self.ser.in_waiting or 1))
            while True:
                pos = self.buf.find(b'$M')
                if pos < 0:
                    if len(self.buf) > 2:
                        del self.buf[:-2]
                    break
                if pos:
                    del self.buf[:pos]
                if len(self.buf) < 6:
                    break
                if self.buf[2] not in (ord('>'), ord('!')):
                    del self.buf[0]
                    continue
                length = self.buf[3] + 6
                if len(self.buf) < length:
                    break
                frame = bytes(self.buf[:length])
                del self.buf[:length]
                checksum = 0
                for value in frame[3:-1]:
                    checksum ^= value
                if checksum != frame[-1] or frame[4] != command:
                    continue
                if frame[2] == ord('!'):
                    raise RuntimeError(f'MSP {command} rejected')
                return frame[5:-1]
        raise TimeoutError(f'MSP {command} reply timeout')

    def motors(self):
        data = self.request(104)
        if len(data) < 8 or len(data) % 2:
            raise RuntimeError('Invalid motor reply')
        return list(struct.unpack('<' + 'H' * (len(data) // 2), data))[:4]

    def status(self):
        version = list(self.request(3))
        api = list(self.request(1))
        analog = self.request(110)
        if not analog:
            raise RuntimeError('Missing voltage reply')
        volts = (struct.unpack_from('<H', analog, 7)[0] / 100
                 if len(analog) >= 9 else analog[0] / 10)
        data = self.request(105)
        if len(data) < 10 or len(data) % 2:
            raise RuntimeError('Missing RC channels')
        rc = list(struct.unpack('<' + 'H' * (len(data) // 2), data))
        status = self.request(101)
        ids = list(self.request(119))
        if len(status) < 10 or 0 not in ids:
            raise RuntimeError('Cannot determine ARM status')
        flags = struct.unpack_from('<I', status, 6)[0]
        armed = bool(flags & (1 << ids.index(0)))
        return dict(firmware=version, api=api, voltage=volts,
                    rc=rc, armed=armed, motor_commands=self.motors())

    def stop(self):
        errors = []
        for _ in range(3):
            try:
                self.write(214, STOP)
            except Exception as exc:
                errors.append(str(exc))
            time.sleep(0.025)
        if errors:
            report(stop_write_errors=errors,
                   action='If the motor is moving, disconnect the battery immediately')


def gate(state):
    if state['firmware'] != [4, 4, 2] or state['api'] != [0, 1, 45]:
        raise RuntimeError('Pulse helper is restricted to the inspected BF 4.4.2 / API 1.45')
    # Conservative diagnostic stop threshold; not a cell-balance or battery-health check.
    if not 6.8 <= state['voltage'] <= 8.4:
        raise RuntimeError('Battery voltage outside 6.8–8.4 V diagnostic range')
    if state['armed'] or state['rc'][4] >= 1800:
        raise RuntimeError('FC must be disarmed and AUX1/SA off')
    if state['motor_commands'] != [1000] * 4:
        raise RuntimeError('Motor commands are not all stopped')


def pulse(fc, seconds, value):
    gate(fc.status())
    desired = [value, 1000, 1000, 1000]
    payload = struct.pack('<8H', *(desired + [1000] * 4))
    timer = threading.Timer(seconds + 0.15, fc.stop)
    start = time.monotonic()
    timer.start()
    try:
        fc.request(214, payload)
        report(event='pulse_started', seconds=seconds, motor_commands=desired)
        while time.monotonic() - start < seconds:
            commands = fc.motors()
            analog = fc.request(110)
            if len(analog) < 9:
                raise RuntimeError('Missing full voltage reply during pulse')
            voltage = struct.unpack_from('<H', analog, 7)[0] / 100
            report(elapsed=round(time.monotonic() - start, 3),
                   motor_commands=commands, voltage=voltage)
            if commands != desired:
                raise RuntimeError('Motor command changed during pulse')
            if not 6.8 <= voltage <= 8.4:
                raise RuntimeError('Voltage crossed diagnostic stop threshold')
            time.sleep(min(0.2, max(0, seconds - (time.monotonic() - start))))
    finally:
        fc.stop()
        timer.cancel()
        timer.join()
    commands = fc.motors()
    report(event='pulse_finished', motor_commands=commands)
    if commands != [1000] * 4:
        raise RuntimeError('Stop readback failed; disconnect battery')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', default=DEFAULT_PORT)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('status', help='Read-only firmware, voltage, RC and command readbacks')
    sub.add_parser('stop', help='Block normal arming and send all outputs to stop')
    p = sub.add_parser('pulse', help='PHYSICAL ACTION: Motor 1 only; not an aircraft ARM')
    p.add_argument('--value', type=int, default=1020)
    p.add_argument('--seconds', type=float, nargs='+', required=True)
    p.add_argument('--props-removed', action='store_true', required=True,
                   help='Explicitly attest that all propellers are removed')
    args = parser.parse_args()
    if args.action == 'pulse':
        if not 1001 <= args.value <= 1040:
            parser.error('This diagnostic helper limits Motor 1 to 1001–1040')
        if len(args.seconds) > 2 or any(not 0 < n <= 10 for n in args.seconds):
            parser.error('One or two finite durations in (0, 10] seconds only')

    fc = FC(args.port)
    mutating = args.action != 'status'

    def interrupted(signum, frame):
        raise KeyboardInterrupt(f'Signal {signum}')

    old_signals = {s: signal.signal(s, interrupted)
                   for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        state = fc.status()
        report(**state)
        if args.action == 'status':
            return 0
        if args.action == 'pulse':
            gate(state)
        # Blocks normal arming. Second byte 0 retains runaway prevention.
        # Do not silently clear this temporary block when exiting.
        fc.request(99, b'\x01\x00')
        fc.stop()
        if args.action == 'pulse':
            for seconds in args.seconds:
                pulse(fc, seconds, args.value)
        return 0
    finally:
        try:
            if mutating:
                fc.stop()
                try:
                    commands = fc.motors()
                    report(event='final_stop', motor_commands=commands)
                    if commands != [1000] * 4:
                        raise RuntimeError('Stop unconfirmed; disconnect battery')
                except Exception:
                    print('STOP UNCONFIRMED: disconnect battery if motor is moving',
                          file=sys.stderr, flush=True)
                    raise
        finally:
            fc.ser.close()
            for sig, handler in old_signals.items():
                signal.signal(sig, handler)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (Exception, KeyboardInterrupt) as exc:
        print(f'Bench helper stopped: {exc}', file=sys.stderr, flush=True)
        sys.exit(1)
```
