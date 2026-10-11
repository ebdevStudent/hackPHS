# Codex handoff: ESP32-S3 → RadioMaster Pocket trainer (yaw only), HackPHS Ball Drone

Written 2026-10-11 by Claude Code (the session that built and bench-tested this). Read all of it once before you act. Sections 1–3 are the rules. Section 10 is your actual job.

---

## 0. TL;DR

- **Everything up to the radio works and was measured on real hardware.**
  - The ESP32-S3 makes correct CPPM.
  - The RadioMaster Pocket receives it on its trainer jack.
  - The Pocket mixes it into the rudder (yaw) channel at 30%. Switch SD cuts it off.
- **Nothing has been checked past the radio yet.** That means ELRS → flight controller → Betaflight.
- **Your job:**
  1. Run the 20 props-off trials in Betaflight Configurator (section 10). Record the results.
  2. Run the software tests on Linux (section 11).
  3. Report honestly.

---

## 1. Repo: use ebdevStudent/hackPHS, nothing else

**The best course of action, if you can:**

1. Pull **`https://github.com/ebdevStudent/hackPHS`**, branch **`esp32-trainer-ppm`** (head commit `df186f4`).
2. Analyze that repo state.
3. Treat it as the **single, universal source of truth**.
4. **Stop committing to, pushing to, or reasoning from `chessdroid108/HackPHS`.** It has a copy of the same work, but it is not the repo going forward.

```sh
git clone -b esp32-trainer-ppm https://github.com/ebdevStudent/hackPHS.git
# or, in an existing clone:
git fetch origin esp32-trainer-ppm && git checkout esp32-trainer-ppm
```

Things to know about that repo:

- **Use the branch, not `main`.**
  - `main` on ebdevStudent/hackPHS still has the older firmware. That firmware answers `NO_OUTPUT` and has **no PPM output**.
  - Only `esp32-trainer-ppm` has the firmware that is actually flashed on the board.
  - Don't merge into `main` unless the user asks.
- ebdevStudent/hackPHS has its own unrelated history: one "Initial commit", `0d9974d`. The PPM work sits on top of it as one overlay commit, `df186f4`.
  - `software/ball_demo/cli.py` was hand-merged. It keeps both sets of flags: `--serial` / `--baud` / `--trainer-output`, and `--portable-demo` / `--target-calibration` / `--target-delay-ms`.
  - `engine.py` was a clean 3-way merge.
- **Stale docs, ignore them:**
  - `docs/28-esp32-trainer-wiring.md` (not on this branch anyway).
  - Any "todo" / "checklist" / "real HackPHS" style doc.
  - Everything those docs had that was worth keeping is rewritten in this handoff. **This handoff wins over any doc in the repo.**
  - The "Verification" table in `firmware/README.md` is out of date. It still says "not done" for things that are now done (section 8). Update it after your trials.
- The three tool files are pasted verbatim in section 13, because your GitHub integration may not fetch them. If the repo and section 13 disagree, tell the user. Don't silently pick one.

---

## 2. The control chain (new layer: you are on the laptop, the ESP is on the Pi)

```
YOU (Codex, on the user's home laptop; Betaflight Configurator is also on this laptop)
  │  ssh
  ▼
Raspberry Pi 5   user: hackphs (all lowercase; "hackPHS" fails auth). You already know the password.
  │  USB cable
  ▼
ESP32-S3 board   appears on the Pi as /dev/ttyACM0
  │  GPIO4 → 2 kΩ → 3.5 mm plug (breadboard)
  ▼
RadioMaster Pocket trainer jack → ELRS RF → ELRS receiver → flight controller
  │  USB cable
  ▼
Betaflight Configurator on the laptop (Receiver tab)
```

**Which machine runs what:**

| Thing | Runs on | Notes |
|---|---|---|
| `esp_term.py`, `ppm_probe.py`, any ESP script | **Pi** (over ssh) | The ESP is plugged into the Pi, not the laptop. |
| Flashing the ESP | **Pi**, with esptool | `flash.ps1` is Windows-only. It is NOT used in this chain. |
| Compiling the firmware | The laptop (arduino-cli), or the Pi if you install arduino-cli + esp32 core 3.3.12 there | The firmware is **already flashed**. You should not need to reflash. |
| Betaflight Configurator | **Laptop** | The flight controller is plugged into the laptop over USB. |
| Software tests (`pytest`) | **Pi** (Linux, has compilers) | See section 11. |

**Pi address:**

- It changes per network.
- At the hackathon it was `172.16.241.67`.
- On the user's home network it was previously `192.168.86.116`.
- If neither answers, ask the user, or scan the LAN.
- The Pi is **currently powered off** (it was running hot). The user has to power it on first.

**Serial port on the Pi:**

- It is `/dev/ttyACM0`. The stable alias is `/dev/serial/by-id/usb-1a86_*`.
- The board's USB-UART is a CH343 (VID:PID `1a86:55d3`). `esp_term.py` auto-detects it.
- **Do not** use `COM3`. That was the Windows name.

**What already exists in `~/esp32-bridge/` on the Pi:**

- `esp_term.py` and `ppm_probe.py`: copies of the repo tools.
- `esp_bench.py`, `esp_disarm.py`, `esp_pulse.py`: one-off bench scripts. Not in the repo.
- `ball_bridge_esp32.merged.bin`: the flashed image.
- `backup_before_flash.bin`: full 8 MB backup taken before the first flash.
- `venv/`: created with `--system-site-packages`, has esptool.

**Running things on the Pi:**

- Earlier runs used `cd ~/esp32-bridge && python3 <script>`.
- If `import serial` fails, use `~/esp32-bridge/venv/bin/python` instead.
- `lgpio` (used by `ppm_probe.py`) is a system package.
- It's fine to clone the ebdevStudent repo onto the Pi (it has internet) and run the tools from `firmware/esp32/tools/`.

**Interactive use over ssh:**

- `esp_term.py` is an interactive prompt, so it needs a TTY: `ssh -t hackphs@<ip>`, then run it.
- If you can't drive an interactive prompt well, write a small non-interactive script that imports `esp_term.Bridge` (template in section 10.4). That is how every bench test so far was run.

**Flashing (only if you really must):**

- Command: `~/esp32-bridge/venv/bin/esptool -b 921600 write-flash 0x0 <file>.merged.bin`
- **Always pass `-b 921600`.** The default 115200 is painfully slow (reading 8 MB took about 25 minutes).
- If it won't connect: hold BOOT, tap RST, release BOOT, then retry.
- The image is built with the Windows `arduino-cli compile --fqbn esp32:esp32:esp32s3 --warnings all` and the esp32 core **3.3.12**. Copy the `*.merged.bin` from the build output to the Pi.

---

## 3. The user's rules (they will be annoyed if you break these)

- **No oscilloscope.** Don't suggest one. PPM is verified by decoding on a Pi GPIO (`ppm_probe.py`) and on the radio's own screens.
- **No Arduino IDE GUI. No `ball_demo/bridge.py`. No "the app" (the desktop app).** Flash and drive everything from the terminal with the tools in section 13.
- **Breadboard plus ground-rail wiring.**
- **The team has only 2 kΩ resistors.** Every resistor in every instruction is 2 kΩ.
- **Give wiring as a full table from scratch**, using the ESP header pin positions in section 4.
  - Never say "row 17", or refer to a previous setup. Assume the breadboard has been stripped.
- **Explain every command you ask the user to type,** in plain words. Example: "`y 500` means set yaw to +500 out of ±1000, which puts CH4 at 1575 µs."
- Be concise, specific and honest. If something wasn't tested, say "not tested". If you get something wrong, correct it plainly.
- When the user only asks a question, answer it and do nothing else.

---

## 4. Hardware facts

### ESP32-S3 board (Freenove ESP32-S3 WROOM, 8 MB flash, CH343 USB-UART)

Hold the board flat, components up, **USB-C connectors pointing toward you**. Pins are counted from the far end (pin 1) to the end nearest you (pin 20).

| Pos | Left header | Right header |
|---|---|---|
| 1 (far end) | 3V3 | TX |
| 2 | EN | RX |
| 3 | **GPIO4 = CPPM out** | 1 |
| 4 | **GPIO5 = arming input** | 2 |
| 5 | 6 | 42 |
| 6 | 7 | 41 |
| 7 | 15 | 40 |
| 8 | 16 | 39 |
| 9 | 17 | 38 |
| 10 | 18 | 37 |
| 11 | 8 | 36 |
| 12 | 3 | 35 |
| 13 | 46 | 0 |
| 14 | 9 | 45 |
| 15 | 10 | 48 |
| 16 | 11 | 47 |
| 17 | 12 | 21 |
| 18 | 13 | 20 |
| 19 | 14 | 19 |
| 20 (USB end) | **5V: NEVER CONNECT ANYTHING** | **GND** |

- **The 5V pin (left header, pin 20) must stay empty.** A wire from it into the ground rail shorted USB 5V and tripped the Pi's USB over-current protection for every port.
- **The correct GND is right header, pin 20.** It sits on the same end as 5V, on the other side.
- GPIO4 and GPIO5 double as the camera SCCB pins. **Leave the camera ribbon unplugged.**
- Use the USB-C port labelled for USB-UART (next to the BOOT button). That is the CH343.

### RadioMaster Pocket trainer jack (3.5 mm)

Measured with a meter, and cross-checked against EdgeTX `radio/src/boards/hw_defs/pocket.json`: `trainer_in` PC8 (TIM3 CH3), `trainer_detect` PA8 (pull-up, active-low).

| Plug part | Function | Measured |
|---|---|---|
| **Tip** | PPM signal **into** the radio | 0 V open. The radio input loads it at about 3 kΩ to GND. |
| **Ring** | "Cable plugged in" detect, active-low | 2.98 V open. Must be pulled to GND or **the radio ignores the trainer input.** |
| **Sleeve** | GND | — |

- The plug is stereo (TRS), so the ring has to go to GND through 2 kΩ.
- A mono plug would ground the ring automatically, but we're using stereo.

### Meter

- Cen-Tech-style meter. Use the **DCV 20** range, with the probes in **COM** and **VΩmA**.
- The probes don't fit the breadboard holes. Touch a spare jumper pin pushed into the same row, or the solder joint.
- For every reading, put the black probe on the − rail.

---

## 5. Wiring, from scratch (bare breadboard, 2 kΩ only)

Use a breadboard with a − (blue) rail. "Free row" means any row that nothing else uses.

| # | From | Via | To | Purpose |
|---|---|---|---|---|
| 1 | ESP **right header pin 20 (GND)** | jumper | **− rail** | Common ground |
| 2 | ESP **left header pin 3 (GPIO4)** | jumper into free row A | row A | PPM out |
| 3 | Row A | **2 kΩ** across to free row B | row B | Series resistor |
| 4 | Row B | jumper | **plug Tip** wire | PPM into the radio |
| 5 | **Plug Ring** wire | into free row C, then **2 kΩ** from row C | **− rail** | Tells the radio a cable is in |
| 6 | **Plug Sleeve** wire | jumper | **− rail** | Radio ground |
| 7 | ESP **left header pin 4 (GPIO5)** | jumper | **− rail** | **ARM.** Wire in = PPM allowed. Wire out = no output. |
| 8 | ESP USB-C (USB-UART port) | USB cable | **Pi USB port** | Power + serial |
| — | ESP **left header pin 20 (5V)** | **nothing** | — | Never |

Then plug the 3.5 mm plug into the Pocket's trainer jack.

**Expected meter readings** (DCV 20, black on − rail, radio ON, plug in):

| Probe point | Expect | If not |
|---|---|---|
| Ring wire (row C) | **0.01–0.07 V** | 2–3 V means the 2 kΩ isn't seated. Reseat it. Earlier, 0 V across the resistor showed it wasn't connected. |
| Tip wire (row B), ESP idle, no session | about **2.0 V** | 0 V: check GPIO4 and the resistor. |
| Tip wire while streaming | about **1.8 V** (meter averages the pulses) | — |

These levels are below 3.3 V because the radio loads the line through the 2 kΩ. The radio decodes this level fine (proven in section 8).

**Optional Pi decode wiring** (bench check without the radio). This is how the numbers in section 8 were measured. Add these jumpers:

- Row B → **2 kΩ** → **Pi GPIO17 (header pin 11)**.
- **Pi pin 39 (GND)** → − rail.

`ppm_probe.py`'s docstring still says "1 kOhm" and "Pi pin 6". That's stale: use 2 kΩ, and either Pi GND pin works.

---

## 6. Firmware behaviour (what's flashed)

Sketch: `firmware/esp32/ball_bridge_esp32/` (`.ino`, `ppm.cpp/.h`, `src/core.*`, `src/line_reader.*`).

**Signal:**

- Pin: GPIO4. Idle **HIGH**.
- CPPM, 8 channels, **22.5 ms frame**, **300 µs LOW separators**.
- **Only CH4 (yaw) carries data:** `CH4 µs = 1500 + yaw*150/1000` (C integer truncation). So yaw ±1000 → 1350…1650 µs.
- CH1–3 and CH5–8 are always 1500 µs.

**Arming (GPIO5):**

- GPIO5 uses `INPUT_PULLUP`. Wire to GND = armed.
- It is **sampled at each HELLO**:
  - Armed → `READY … PPM_YAW`, and the ESP streams PPM.
  - Not armed → `READY … NO_OUTPUT`, and there is no output at all for that session.
- Pulling the wire mid-session disarms for the rest of that session: 3 neutral frames, then the line idles HIGH.
- It stays disarmed even if commands keep arriving. A new HELLO (with the wire back in) is needed to re-arm.

**Safety:**

- **Watchdog:** no valid CMD for 250 ms → yaw goes to 0 (CH4 1500). Streaming continues.
- A main-loop stall longer than 5 frames also forces neutral.

**Serial protocol:**

- 115200 8N1, lines end in LF.
- Full spec: `firmware/PROTOCOL.md`.

| Host → ESP | ESP → host |
|---|---|
| `HELLO 1 <session>` | `READY 1 <session> PPM_YAW` or `NO_OUTPUT` |
| `CMD 1 <session> <seq> <enable 0/1> <yaw>` | `ACK 1 <session> <seq> <en> <yaw> NONE` (or a fault code instead of NONE) |

- The host sends a CMD every 50 ms.
- `seq` must strictly increase.
- Disabled commands must carry yaw 0.

**Radio side:** the Pocket's EdgeTX treats PPM sync gaps of about 4–19 ms as frame breaks. The frame timing is designed to sit inside that window (host simulation `firmware/esp32/test/test_ppm.cpp` checks this).

---

## 7. Radio configuration (already set on the Pocket; EdgeTX, B&W screen)

**SYS → Trainer page:**

| Row | Mode | Weight | Source |
|---|---|---|---|
| Rud | `+=` (add to stick) | **30** | ch4 |
| Ele | OFF | | |
| Thr | OFF | | |
| Ail | OFF | | |

- Below the rows are **Multiplier** and **Cal**.
- The Cal row shows four live numbers. **The rightmost one is the raw trainer CH4 input.**
  - It ignores switch SD.
  - It shows ±29 for yaw ±1000. That is the raw ±150 µs input on a ±100 scale, before the 30% weight.

**MODEL → Special Functions:**

- **SF1: SD↓ → Trainer → Rud**, enabled.
- So the trainer yaw is applied **only while switch SD is down**.
- **SD up = pilot only**, and the computer has no effect.

**Switches on the Pocket:**

- SA and SD are 2-position; SB and SC are 3-position; SE is momentary.
- Notation: `SD↑` (up), `SD↓` (down).

**Channel Monitor:**

- It's a **home-screen view, not a SYS page.**
- To get there: press RTN until you're on the home screen, then PAGE> / PAGE< to cycle views until the channel bars show.
- This is where the 30% mix and the SD switch actually show up. The SYS→Trainer Cal row does not show them.

**Danger, already fixed once:** a new special function defaults to "Override CH1 0", which overrides the *aileron* channel. If you or the user ever add a special function, double-check the action.

---

## 8. What has been tested and passed (real hardware, numbers)

**A. ESP bench, decoded on Pi GPIO17 by `ppm_probe.py` and helper scripts (2026-10-10):**

| Check | Result |
|---|---|
| yaw 0 / +500 / −1000 → CH4 | **1500 / 1576 / 1349 µs** (expected 1500 / 1575 / 1350; ±1 µs is Pi timestamp jitter) |
| Other channels | 1500 µs |
| LOW separator width | **299.3 µs** (expect 300) |
| Frame period | **22500.2 µs** (expect 22500) |
| Polarity | Separators LOW, idle HIGH: correct |
| Watchdog (`pause`) | CH4 → 1500 |
| Pull GPIO5 wire while streaming yaw +500 | CH4 1575 → one 1501 frame (neutral tail) → line idle HIGH. **Stayed idle 3 s while enabled CMDs kept arriving.** |
| New HELLO with wire out | `NO_OUTPUT` |
| Faults over the disarm run | 205 ACKs, **0 faults** |

**B. Pocket jack pinout:** measured as in section 4.

**C. Radio receive (SYS→Trainer Cal row, rightmost number):** `y 0` → 0; `y 1000` → 29; `y -1000` → −29; `y 0` → 0. **PASS.**

**D. Mix + SD override (home-screen Channel Monitor, Rud channel):**

| Input | Rud channel |
|---|---|
| SD↑, y 1000 | **0** (cut off: PASS) |
| SD↓, y 1000 | **+7** |
| SD↓, y −1000 | **−8** |
| y 0 | **0** |

**PASS.** About ±8% is what you'd expect: ±29% raw × 30% weight ≈ ±8.7%.

**E. Software tests:** they were only run on Windows, so they are **not run on Linux yet**. Section 11 has the details.

**Not yet tested, so don't claim it:**

- Anything after the Pocket's RF output: ELRS → receiver → FC → Betaflight.
- The yaw direction as the flight controller sees it.
- What the Pocket does on screen or audibly when the trainer signal stops.
- Weight above 30%.
- Any props-on or flight test.

---

## 9. Setup for the Betaflight session

1. **Laptop:** plug the flight controller in over USB. Open Betaflight Configurator, Connect, go to the **Receiver** tab.
   - Props OFF.
   - **Don't arm the FC.** The Receiver tab shows live channels while disarmed. The drone isn't fully assembled, and only the FC and ELRS receiver are needed.
   - The receiver is already bound to the Pocket, and that link is known-good.
   - If the receiver gets no power over USB alone (some FCs don't power the 5 V rail from USB), tell the user. Don't guess.
2. **Note the Receiver tab's channel map** (for example `AETR1234`). With the Pocket's default AETR output, **Betaflight's "Yaw" bar must be radio CH4 (Rud).** If the Yaw bar doesn't respond to the rudder stick, fix the mapping first and tell the user what you changed.
3. **Pocket:** powered on, the model bound to this receiver, SD↑ to start. The plug is in the trainer jack, wired as in section 5.
4. **Pi:** powered on, ESP plugged in. ssh in.
5. **Baseline (sticks centred, ESP not running):** write down Betaflight's Roll / Pitch / Yaw / Throttle and the AUX values. Use these as the "neutral" reference.

**Expected numbers at weight 30%:**

- About ±8% of a ±512 µs half-range is roughly **±40 µs** at the FC.
- So with sticks centred and SD↓: `y 1000` should give Yaw ≈ **1540**, and `y -1000` ≈ **1460**. Allow about ±10 µs for ELRS rounding.
- Positive yaw should **increase** the Yaw value.
  - Betaflight convention: >1500 = yaw right / clockwise seen from above.
  - Whether "positive yaw = turn toward the ball" is set later in the software (`software/ball_demo/config.py`, `direction: int = 1`). It's not part of these trials, but record the sign you see.

---

## 10. YOUR NEXT STEP: 20 props-off Betaflight trials

### 10.1 One trial = these steps, in order

Everything is watched in the Betaflight Receiver tab. "Stick yaw" is the Yaw value with the rudder stick centred, from the baseline.

| Step | Action | Pass if |
|---|---|---|
| 1. Neutral at rest | ESP session armed (`READY … PPM_YAW`), enabled, `y 0`. Flip SD↓. Then move each stick in turn. | With sticks centred, Yaw = stick yaw (±5 µs). Thr/Roll/Pitch follow only the sticks. |
| 2. Direction + size | SD↓, `y 1000`, then `y -1000`, then `y 0` | +1000 → Yaw ≈ stick+40; −1000 → ≈ stick−40; 0 → back to stick yaw. The sign is the same every trial. |
| 3. Cap | SD↓, rudder stick full right, then full left, with `y 1000` / `y -1000` | Nothing glitches or wraps. The trainer offset never exceeds ±40 µs at 30%. |
| 4. SD override | Keep `y 1000`, flip **SD↑** | Yaw returns to the pure stick value immediately (as fast as you can see). Flip SD↓ and the offset comes back. |
| 5. Watchdog | SD↓, `y 1000`, then `pause` (the ESP stops receiving CMDs) | Yaw returns to stick yaw within a blink. The ESP enforces 250 ms, and that was measured on the bench. `resume` → offset returns. |
| 6. Disarm | SD↓, `y 1000`, then **pull the GPIO5 wire off the − rail** | Yaw returns to stick yaw and stays there. Then `hello` → must print `NO_OUTPUT`. Note any Pocket message or sound (for example "trainer lost"). |
| 7. Re-arm | Push the GPIO5 wire back onto the − rail, `hello`, `on`, `y 0` | `PPM_YAW` again, Yaw = stick yaw. |
| All steps: no crosstalk | — | **Throttle, Roll, Pitch and all AUX never move because of anything the ESP does.** |

- Any single failure = that trial fails.
- On the first failure: **stop, record exactly what you saw, and report it to the user.** Don't "fix and continue" silently.
- Vary the order of ± between trials. Do at least one trial right after a fresh ESP power cycle (unplug and replug its USB on the Pi).

### 10.2 Results table (fill in and give to the user)

| # | 1 Neutral | 2 Dir (+1000 / −1000 values) | 3 Cap | 4 SD | 5 Watchdog | 6 Disarm | 7 Re-arm | Crosstalk | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | | | |
| … | | | | | | | | | |
| 20 | | | | | | | | | |

Also record:

- Betaflight version.
- The channel map.
- Baseline stick values.
- The exact Yaw numbers seen for ±1000.
- Any Pocket messages.

### 10.3 Only after 20/20

- Ask the user before raising the Trainer Rud weight. Then step it up (for example 30 → 50 → 100), checking that ±1000 scales as expected (100% ≈ ±150 µs, i.e. Yaw ≈ 1350–1650 with stick centred).
- Rerun at least steps 2, 4, 5, 6 at each new weight.
- Update `firmware/README.md`'s verification table with the real results, on the ebdevStudent branch only. Ask the user before committing.

### 10.4 Driving the ESP during trials

Interactive, in an `ssh -t` session on the Pi (from the folder holding `esp_term.py`):

```sh
python3 esp_term.py --port /dev/ttyACM0
# prints READY ... mode=PPM_YAW if the GPIO5 wire is on the − rail
> on          # allow computer yaw (starts disabled)
> y 1000      # yaw +1000 -> CH4 1650 us out of the ESP
> y -1000     # CH4 1350 us
> y 0         # CH4 1500 us
> pause       # stop sending commands (watchdog test)
> resume
> hello       # new session; re-reads the GPIO5 wire
> status
> quit        # sends disabled commands, then closes
```

Known cosmetic bug: `quit` closes the port while the reader thread is mid-read, so a thread exception prints on exit. It's harmless. Fixing it is a small open item (join the reader thread before `ser.close()`).

Non-interactive pattern (this is how the bench tests ran):

```python
# run from the folder containing esp_term.py
import threading, time
import esp_term

b = esp_term.Bridge('/dev/ttyACM0', 115200)
threading.Thread(target=b.reader, daemon=True).start()
if not b.hello() or b.mode != 'PPM_YAW':
    b.quit(); raise SystemExit('not armed: put the GPIO5 wire on the - rail and retry')
threading.Thread(target=b.sender, daemon=True).start()   # CMD every 50 ms
for yaw in (0, 1000, -1000, 0):
    b.yaw, b.enable = yaw, True
    print(f'yaw {yaw:+d} -> CH4 {1500 + int(yaw * 150 / 1000)} us; read Betaflight Yaw now', flush=True)
    time.sleep(5)
b.sending = False; print('paused: watchdog should neutralise', flush=True); time.sleep(3)
b.sending = True
print(f'acks={b.ack_count} faults={b.fault_count}')
b.quit()
```

**Coordinate with the user.** They read Betaflight and flip SD; you drive the ESP. Tell them before each step what they should see.

---

## 11. Software tests (no app needed)

These exist on the ebdevStudent branch. Run them **on the Pi** (Linux, which has `cc`/`clang`, `c++`, and working `select` on pipes):

```sh
cd <repo>/software
python3 -m pytest tests/test_esp32_bridge.py tests/test_protocol_exhaustive.py \
  tests/test_protocol_parity.py tests/test_serial.py tests/test_follow_simulation.py -v
```

| Test file | What it checks |
|---|---|
| `test_esp32_bridge.py` (6 tests) | The sketch's `src/` copies are identical to `firmware/core.*` / `line_reader.*`. Serial0 and arming-only-for-PPM session behaviour. A PPM host simulation (needs `c++` or `clang++`). Sketch baud == host default. Worst-case frames fit at the 50 ms rate. 9600 baud can't carry the rate. |
| `test_protocol_exhaustive.py` (4) | Protocol edge cases. |
| `test_protocol_parity.py` (3) | Python protocol matches the C core. Compiles `core.c` with `clang`/`cc`. |
| `test_serial.py` (1), `test_follow_simulation.py` (9) | Serial layer, follow-control simulation. |

Firmware-level tests:

```sh
cd <repo>/firmware/esp32/test
c++ -std=c++17 -Wall -Wextra -Werror -I stubs -I ../ball_bridge_esp32 test_ppm.cpp && ./a.out

cd <repo>
mkdir -p firmware/build-host
cc -std=c11 -Wall -Wextra -Werror firmware/core.c firmware/test_core.c -o firmware/build-host/test_core && firmware/build-host/test_core
cc -std=c11 -Wall -Wextra -Werror firmware/core.c firmware/line_reader.c firmware/test_line_reader.c -o firmware/build-host/test_line_reader && firmware/build-host/test_line_reader
```

(The `line_reader` build line is inferred from its includes, because the README only gives the `test_core` command. If it fails to link, read the includes and adjust. It is not a firmware bug.)

**Status:**

- These have only been run on Windows. There, a fixed set fails **for environment reasons only**: no C++ compiler, `select()` on pipes (WinError 10038), missing `qrcode`, a Linux `/dev/video` test, and parity tests needing a C compiler.
- The identical set failed on the untouched original tree, so the merge didn't cause them.
- **Linux results: unknown.** Run them and report the real output. Install `pyserial` / `pytest` into a venv if missing.
- If a test that only touches the ESP or protocol fails on Linux, that's a real finding. Report it.

---

## 12. Open items (in priority order)

1. 20 props-off Betaflight trials (section 10).
2. Run the software and firmware tests on Linux (section 11).
3. Fix the `esp_term.py` `quit()` reader-thread exception.
4. Fix the stale `ppm_probe.py` docstring: "1 kOhm" → 2 kΩ, and "pin 6" → any Pi GND (pin 39 was used).
5. Update `firmware/README.md`'s verification table (section 8 + your results).
6. After 20/20, and with the user's OK: raise the trainer weight. Then decide `direction` / gain in software. Any props-on test is a separate, user-approved step.

Commit only to `ebdevStudent/hackPHS` `esp32-trainer-ppm`, and only when the user asks.

---

## 13. The three tool files, verbatim

They live in the repo at `firmware/esp32/tools/` on `ebdevStudent/hackPHS`, branch `esp32-trainer-ppm`. The same files are also on `chessdroid108/HackPHS` branch `esp32-trainer-ppm`, but don't use that repo.

```
firmware/
├── PROTOCOL.md
├── README.md
├── core.c / core.h / line_reader.c / line_reader.h   (shared C core)
└── esp32/
    ├── ball_bridge_esp32/        (the flashed sketch: .ino, ppm.cpp/.h, src/)
    ├── test/                     (test_ppm.cpp + stubs/)
    └── tools/
        ├── esp_term.py           ← interactive/terminal driver (run on the Pi)
        ├── ppm_probe.py          ← decode CPPM on Pi GPIO17 (run on the Pi)
        └── flash.ps1             ← Windows-only compile+flash; NOT used in the Pi chain
```

### 13.1 `firmware/esp32/tools/esp_term.py`

```python
"""Terminal control for the ESP32-S3 bridge, without ball_demo/bridge.py.

Opens the CH343 USB-UART port, repeats HELLO until READY, then sends a CMD every 50 ms so the
bridge's 250 ms watchdog stays fed.  Starts DISABLED with yaw 0.  Type commands at the prompt:

  on            enable (computer yaw allowed)
  off           disable (yaw forced to 0)
  y <n>         set yaw, -1000..1000 (only sent while enabled)
  pause         stop sending CMDs (watchdog test: bridge must drop to neutral in 250 ms)
  resume        start sending CMDs again
  hello         start a new session (re-samples the GPIO 5 arming jumper)
  status        print current state and the last ACK
  quit          send disabled commands, then exit

Usage:  python esp_term.py [--port COM5 | /dev/ttyACM0] [--baud 115200]
"""
import argparse
import secrets
import sys
import threading
import time

import serial
from serial.tools import list_ports

CH343_VID, CH343_PID = 0x1A86, 0x55D3
PROTOCOL_VERSION = 1
CMD_PERIOD_S = 0.05
HELLO_RETRY_S = 0.5
HELLO_TIMEOUT_S = 10.0
YAW_LIMIT = 1000
QUIT_NEUTRAL_FRAMES = 5


def find_port():
    for p in list_ports.comports():
        if p.vid == CH343_VID and p.pid == CH343_PID:
            return p.device
    return None


class Bridge:
    def __init__(self, port, baud):
        # DTR/RTS drive the board's EN/BOOT auto-reset; hold both deasserted so opening the port
        # does not reset it or drop it into the bootloader.
        self.ser = serial.Serial(None, baud, timeout=0.1)
        self.ser.dtr = False
        self.ser.rts = False
        self.ser.port = port
        self.ser.open()
        self.lock = threading.Lock()
        self.session = None
        self.mode = None
        self.seq = 0
        self.enable = False
        self.yaw = 0
        self.sending = True
        self.running = True
        self.last_ack = None
        self.ack_count = 0
        self.fault_count = 0

    def write(self, line):
        self.ser.write((line + "\n").encode("ascii"))

    def hello(self):
        """Repeat HELLO until READY. The port open may reset the board, so early lines are boot noise."""
        with self.lock:
            self.session = secrets.token_hex(4)
            self.mode = None
            self.seq = 0
            self.enable = False
            self.yaw = 0
        deadline = time.monotonic() + HELLO_TIMEOUT_S
        while time.monotonic() < deadline and self.mode is None:
            self.write(f"HELLO {PROTOCOL_VERSION} {self.session}")
            time.sleep(HELLO_RETRY_S)
        if self.mode is None:
            print(f"! no READY within {HELLO_TIMEOUT_S:.0f} s (wrong port, baud or firmware?)")
            return False
        print(f"READY session={self.session} mode={self.mode}"
              + ("  <- GPIO5 jumper was OUT, no PPM output" if self.mode == "NO_OUTPUT" else "  <- PPM streaming"))
        return True

    def reader(self):
        while self.running:
            try:
                raw = self.ser.readline()
            except serial.SerialException as exc:
                print(f"\n! serial error: {exc}")
                self.running = False
                return
            if not raw:
                continue
            line = raw.decode("ascii", errors="replace").strip()
            parts = line.split(" ")
            if parts[0] == "READY" and len(parts) == 4 and parts[2] == self.session:
                self.mode = parts[3]
            elif parts[0] == "ACK" and len(parts) == 7 and parts[2] == self.session:
                self.last_ack = line
                self.ack_count += 1
                if parts[6] != "NONE":
                    self.fault_count += 1
                    print(f"\n! {line}")
            elif line:
                print(f"\n< {line}")

    def sender(self):
        while self.running:
            if self.mode is not None and self.sending:
                with self.lock:
                    self.seq += 1
                    en = 1 if self.enable else 0
                    yaw = self.yaw if self.enable else 0
                    line = f"CMD {PROTOCOL_VERSION} {self.session} {self.seq} {en} {yaw}"
                self.write(line)
            time.sleep(CMD_PERIOD_S)

    def quit(self):
        with self.lock:
            self.enable, self.yaw = False, 0
        time.sleep(CMD_PERIOD_S * QUIT_NEUTRAL_FRAMES)
        self.running = False
        self.ser.close()


def handle(bridge, text):
    words = text.split()
    if not words:
        return True
    cmd = words[0].lower()
    if cmd == "on":
        bridge.enable = True
        print(f"ENABLED, yaw={bridge.yaw}")
    elif cmd == "off":
        with bridge.lock:
            bridge.enable, bridge.yaw = False, 0
        print("DISABLED, yaw=0")
    elif cmd == "y" and len(words) == 2:
        try:
            val = int(words[1])
        except ValueError:
            print("! yaw must be an integer")
            return True
        if not -YAW_LIMIT <= val <= YAW_LIMIT:
            print(f"! yaw must be within -{YAW_LIMIT}..{YAW_LIMIT}")
            return True
        bridge.yaw = val
        print(f"yaw={val} ({1500 + int(val * 150 / 1000)} us on CH4 while enabled)"
              + ("" if bridge.enable else "  [not sent: disabled, type 'on']"))
    elif cmd == "pause":
        bridge.sending = False
        print("CMDs PAUSED, bridge watchdog should neutralise yaw within 250 ms")
    elif cmd == "resume":
        bridge.sending = True
        print("CMDs resumed")
    elif cmd == "hello":
        bridge.hello()
    elif cmd == "status":
        print(f"session={bridge.session} mode={bridge.mode} seq={bridge.seq} enable={bridge.enable} "
              f"yaw={bridge.yaw} sending={bridge.sending} acks={bridge.ack_count} faults={bridge.fault_count}\n"
              f"last: {bridge.last_ack}")
    elif cmd in ("quit", "exit", "q"):
        return False
    else:
        print("commands: on | off | y <n> | pause | resume | hello | status | quit")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", help="serial port; default: auto-detect the CH343 (1a86:55d3)")
    ap.add_argument("--baud", type=int, default=115200)
    args = ap.parse_args()

    port = args.port or find_port()
    if not port:
        sys.exit("! no CH343 port found. Plug in the USB-C port next to BOOT, or pass --port.")
    bridge = Bridge(port, args.baud)
    print(f"opened {port} @ {args.baud}")
    threading.Thread(target=bridge.reader, daemon=True).start()
    threading.Thread(target=bridge.sender, daemon=True).start()
    if not bridge.hello():
        bridge.quit()
        sys.exit(1)
    print("starts DISABLED. type 'help' for commands.")
    try:
        while bridge.running and handle(bridge, input("> ")):
            pass
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        print("sending disabled commands and closing")
        bridge.quit()


if __name__ == "__main__":
    main()
```

### 13.2 `firmware/esp32/tools/ppm_probe.py`

```python
"""Decode the ESP32's CPPM output on a Raspberry Pi 5 GPIO (no scope needed).

Wiring: ESP32 GPIO4 -> 1 kOhm -> Pi GPIO17 (header pin 11); ESP32 GND -> Pi GND (pin 6).
Both sides are 3.3 V logic.

Each channel is the time between consecutive falling edges; a gap over SYNC_MIN_US ends a frame.
Usage: python3 ppm_probe.py [--gpio 17] [--seconds 2]
"""
import argparse
import statistics
import time

import lgpio

SYNC_MIN_US = 3000
CHANNELS = 8


def open_header_chip():
    """Pi 5 header GPIOs live on the RP1 chip; its gpiochip number differs between kernels."""
    for n in (0, 4):
        try:
            h = lgpio.gpiochip_open(n)
        except lgpio.error:
            continue
        if "rp1" in lgpio.gpio_get_chip_info(h)[3]:  # [status, lines, name, label]
            return h
        lgpio.gpiochip_close(h)
    raise SystemExit("! RP1 gpiochip not found")


def capture(gpio, seconds):
    h = open_header_chip()
    falls = []
    lgpio.gpio_claim_alert(h, gpio, lgpio.FALLING_EDGE)
    cb = lgpio.callback(h, gpio, lgpio.FALLING_EDGE, lambda _c, _g, _l, tick: falls.append(tick))
    time.sleep(seconds)
    level = lgpio.gpio_read(h, gpio)
    cb.cancel()
    lgpio.gpiochip_close(h)
    return falls, level


def decode(falls_ns):
    """Split falling-edge timestamps into frames of channel widths in microseconds."""
    gaps = [(b - a) / 1000 for a, b in zip(falls_ns, falls_ns[1:])]
    frames, cur = [], None
    for g in gaps:
        if g > SYNC_MIN_US:
            if cur is not None and len(cur) == CHANNELS:
                frames.append(cur)
            cur = []
        elif cur is not None:
            cur.append(g)
    return frames


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpio", type=int, default=17)
    ap.add_argument("--seconds", type=float, default=2.0)
    args = ap.parse_args()

    falls, level = capture(args.gpio, args.seconds)
    if not falls:
        state = "HIGH (idle: disarmed / no session)" if level else "LOW (stuck low or not wired?)"
        print(f"no edges in {args.seconds:.1f} s; line is {state}")
        return
    frames = decode(falls)
    print(f"{len(falls)} falling edges, {len(frames)} complete 8-channel frames in {args.seconds:.1f} s")
    if not frames:
        return
    period_ms = (falls[-1] - falls[0]) / 1e6 / max(1, len(falls) - 1) * (CHANNELS + 1)
    print(f"frame period ~{period_ms:.1f} ms (expect 22.5)")
    for ch in range(CHANNELS):
        vals = [f[ch] for f in frames]
        flag = "  <- yaw" if ch == 3 else ""
        print(f"CH{ch + 1}: mean {statistics.mean(vals):7.1f} us  min {min(vals):7.1f}  max {max(vals):7.1f}{flag}")


if __name__ == "__main__":
    main()
```

### 13.3 `firmware/esp32/tools/flash.ps1` (Windows only, for reference)

```powershell
# Compile and flash ball_bridge_esp32 from the terminal (no Arduino IDE window).
# Uses the arduino-cli bundled with Arduino IDE 2 unless arduino-cli is on PATH.
#   .\flash.ps1            auto-detect the CH343 port (1a86:55d3)
#   .\flash.ps1 -Port COM5
param([string]$Port)
$ErrorActionPreference = 'Stop'

$cli = (Get-Command arduino-cli -ErrorAction SilentlyContinue).Source
if (-not $cli) { $cli = "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe" }
if (-not (Test-Path $cli)) { throw "arduino-cli not found" }

$sketch = Join-Path $PSScriptRoot '..\ball_bridge_esp32'
$fqbn = 'esp32:esp32:esp32s3'

if (-not $Port) {
    $dev = Get-CimInstance Win32_PnPEntity | Where-Object { $_.DeviceID -match 'VID_1A86&PID_55D3' -and $_.Name -match '\((COM\d+)\)' }
    if (-not $dev) { throw "No CH343 port found. Plug in the USB-C port next to BOOT, or pass -Port COMx." }
    $Port = [regex]::Match($dev[0].Name, 'COM\d+').Value
}
Write-Host "Flashing $sketch to $Port"

& $cli compile --fqbn $fqbn --warnings all $sketch
if ($LASTEXITCODE -ne 0) { throw "compile failed" }
& $cli upload --fqbn $fqbn -p $Port $sketch
if ($LASTEXITCODE -ne 0) { throw "upload failed. Hold BOOT, tap RST, release BOOT, then rerun." }
Write-Host "Done. Control it with: python $PSScriptRoot\esp_term.py --port $Port"
```

On the Pi, the equivalent of `flash.ps1`'s upload step is:
`~/esp32-bridge/venv/bin/esptool -b 921600 write-flash 0x0 ball_bridge_esp32.merged.bin`
