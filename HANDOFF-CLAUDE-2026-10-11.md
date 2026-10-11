# HANDOFF FOR THE NEXT CLAUDE SESSION — 2026-10-11 (~07:00 EDT)

> **This is an explicit handoff.** If you are a Claude session that just pulled this branch, read
> this whole file before doing anything. It is the newest state of the project and supersedes
> older assumptions in other docs where they conflict. Also read
> [docs/30-claude-session-summary-2026-10-11.md](docs/30-claude-session-summary-2026-10-11.md)
> (the parallel bench session that got FPV working).

Branch: `ebdevStudent/hackPHS` **`esp32-trainer-ppm`** (source of truth; `chessdroid108` fork is no
longer used). Hackathon is **today, Oct 10–11, 2026**. Goal right now: **make the drone physically fly.**

---

## 1. Status at a glance

| Link / subsystem | State | Notes |
| --- | --- | --- |
| Pi → ESP32-S3 → RadioMaster trainer (PPM yaw on CH4) | **Works** | Verified earlier with `firmware/esp32/tools/esp_term.py` + `ppm_probe.py` |
| Radio (RadioMaster Pocket) → ELRS → FC | **Works** | AETR, SA → CH5 = ARM |
| FPV video: drone camera → FC's AIO VTX → RC832 → MS210x capture card → Pi | **Works** | VTX on Raceband ch 8 = **5917 MHz**, 25 mW. Pi streamer on port 8090 (`tools/pi/`) |
| ESP32 → TS832 analog test-pattern video | **Dropped / not needed** | Was only a link test. Real FPV now works via the AIO VTX. Don't spend more time here. |
| Motor positions + directions | **Verified** after remap (`motor_output_reordering = 2,0,3,1`), FC arrow = nose | M1 RR CW, M2 FR CCW, M3 RL CCW, M4 FL CW. CW props on M1/M4, CCW on M2/M3 |
| FC mounted in frame / board alignment | **Not done** | |
| ANGLE (self-level) mode | **Parked** | Enable once assembled (see §2 step 4) |
| Failsafe | **Not verified** | Must pass before props-on |
| First props-on hover | **Not done** | |
| AprilTag tracking on live FPV | **Not wired** | See §4 |
| Computer yaw from vision | Only from the **HSV colored-ball** detector | AprilTags never drive yaw |

## 2. Flight checklist (do in this order)

1. **Charge a pack.** OSD showed 7.36 V (`BATT < FULL`). Full 2S = 8.4 V.
2. **Props OFF, USB in, Betaflight → Motors tab.** Spin each motor alone. Confirm it is at the corner
   the diagram shows AND spins the direction the diagram shows (M1/M4 CW, M2/M3 CCW from above).
   Wrong order/direction = instant flip on liftoff.
3. **Mount the FC, arrow forward.** Setup tab: tilt the drone by hand, the 3D model must tilt the same
   way. If off by 90°/180°, fix with board alignment yaw.
4. **Enable ANGLE mode**: CLI `aux 1 1 0 900 2100 0 0` then `save`. Put drone on a level surface →
   Calibrate Accelerometer. Model should sit level.
5. **Props still OFF**: Receiver tab — each stick moves its bar. Arm with SA → motors idle. **Turn the
   radio off → motors must stop (failsafe).** Do not fly until this passes.
6. **Props on**, each matching its motor's spin direction (leading edge leads).
7. **First hover**: USB unplugged, **no ESP32 trainer**, pilot-only. In the cage/clear area. Arm, throttle
   up slowly to ~30 cm, land. Flips/shoots sideways on liftoff → disarm instantly; recheck steps 2, 3, 6.

The user OK'd this plan: "on table, propellers off, usb plugged in, do bs on betaflight, unplug usb, fly."

Helper tools (laptop, FC on USB): `tools/betaflight_motor_bench.py` (status/config/direction/pulse ≤1150)
and `tools/motor_dashboard.py` (http://127.0.0.1:8765, Motors + Camera tabs, Space = STOP).
Offer to read back motor directions, board alignment, ANGLE aux, failsafe and voltage over MSP so the
user only checks physical things.

## 3. Control path in flight (no USB)

USB on the FC is **only** for Betaflight setup on the bench, props off. In flight:
`Pi → USB serial → ESP32-S3 → RadioMaster trainer port (PPM) → radio → ELRS → FC`.
The pilot keeps throttle/roll/pitch/arm and can override; computer assist is yaw-only (V1).
Add the ESP32 trainer only after manual hover is reliable.

## 4. AprilTag follow / landing — IMPLEMENTED 2026-10-11 (see docs/31-apriltags-and-tracking.md)

- `ball_demo/tag_target.py`: `target_mode` = `color` | `tag` | `landing`. Tag detections use the ball's
  detection schema and feed the SAME `Controller` (watchdogs, loss → neutral, yaw-only). No calibration
  needed; range is an approximate fisheye estimate. Landing = pilot cues (SEARCH/ALIGN/APPROACH/DESCEND/
  OVER PAD), never throttle.
- `ball_demo/tag_kit.py` / `ball-demo tags …`: wizard, add/remove/list, exact-size printable PDF with a
  5 cm scale check, detect from image/URL/camera. Roster = existing `Roster` (people + landing_sites).
- Monitor: Target/Tag ID/descend range/FOV settings, AprilTags roster panel + live reload
  (`POST /api/operator/roster/reload`), guidance line under the video, overlay on the preview.
- Pi: `/usr/local/bin/drone-mode fpv|track|assist [color|tag|landing]|status` (systemd drop-in; deployed).
  `tools/pi/push-roster.sh` installs the laptop roster at /var/lib/ball-drone/roster.json and reloads.
  `assist` (= `--trainer-output`) still needs the team's decision; it asks for YES.
- 18 tests in `software/tests/test_apriltag_targets.py`; full suite 4305 passed (only pre-existing
  env failures: C++ `cassert` missing for the PPM host sim, Qt-less desktop collection).
- The older calibrated 3D tag tracking (`target_tracking.py`, `--target-calibration`) is unchanged and
  still display-only.

### Preflight (laptop dashboard, FC on USB)
`tools/motor_dashboard.py` → **Preflight** tab: one read-only button checks FC (battery, ELRS link, ARM range,
ANGLE aux, max tilt, board alignment, throttle/ARM switch, arming blockers, failsafe, VTX, motor protocol)
and Pi (fpv/track mode, video, bridge) → GO / CHECK / NO-GO, plus the manual checklist. Logic in
`tools/preflight_checks.py` (tests: `software/tests/test_preflight_checks.py`).

## 5. Software audit fixes — PUSHED (commit after the handoff commit, same branch)

A Sonnet compat audit found four software issues; they are implemented and pushed:
1. **Capture mode never set/checked** → `sources.py` `OpenCVSource.negotiate_capture_mode` requests
   YUYV 720x480@30, reads back, raises on size/fourcc mismatch, warns on fps. New `Settings`
   `capture_width/height/fps/fourcc`; CLI `--capture-mode WxH@FPS`, `--capture-fourcc`.
2. **Silent synthetic fallback** (no `--camera` → fake video, no warning) → startup warnings, red
   on-frame bar "SYNTHETIC - NO CAMERA CONFIGURED - NOT LIVE VIDEO", UI banner, mock-bridge warning.
3. **Opening the serial port could reset the ESP32-S3** (DTR/RTS → EN/BOOT) → `bridge.py` opens with
   DTR/RTS deasserted first (same as `esp_term.py`).
4. **OpenCV drift** (Pi venv 5.0.0, Pi system 4.10, laptop 4.12) → venv pinned 5.0.0.93 in
   `requirements.lock`; note in `pyproject.toml`; server logs `cv2.__version__`.
Tests: +14 in `software/tests/test_hardware_compat.py`; suite 45F/1852P → 44F/1867P (remaining failures
are pre-existing Windows-only). Repo `software/deploy/ball-demo.service` was changed to pass
`--camera /dev/video0 --camera-backend v4l2 --capture-mode 720x480@30 --serial /dev/serial/by-id/usb-1a86_USB_Single_Serial_5876079136-if00`
— **NOT deployed to the Pi.** `--trainer-output` was deliberately left OUT (user hasn't decided; add it
only on their OK). Deploying this file makes `ball-demo` claim `/dev/video0`, so `fpv-stream.service`
must be stopped/disabled first.

## 6. Raspberry Pi 5 state

- Event-network IP **172.16.240.48** (changes per network), user `hackphs` (lowercase). Password: ask
  the user — do not commit it.
- `ball-demo.service` currently runs `serve --host 0.0.0.0 --port 8080` with **no args** → synthetic
  video + mock bridge (not live).
- `fpv-stream.service` (port 8090) holds the capture card for the live FPV view.
- MS210x capture card (USB `534d:0021`): modes YUYV 720x576@25 and 720x480@30. **Flat Y=16, U=V=128 =
  the card's own black when it has no sync lock** (not noise). If it stalls at 0 frames, USB unbind/bind
  the device (or `tools/pi/reset-capture`). On Windows, OpenCV `CAP_DSHOW` index 1 = card, 0 = webcam.

## 7. Lessons from this session (don't repeat)

- ESP_8_BIT composite library is broken on arduino-esp32 core 3.3.12 (wrong frame timing → capture card
  never locks → black). Core **2.0.17** with the **unpatched** library gives 59.9 fps NTSC. Only relevant
  if anyone revisits ESP32 analog video.
- Trick without a scope: the capture card's **audio** input picks up a composite signal's 15.7 kHz line
  rate via FFT — proves a video signal exists on a wire.
- A thin 0.64 mm jumper pin does not make contact inside a female RCA center.
- Flaky ESP32 USB (COM port disappears): always re-check the port is present before testing.

## 8. How to work with this user (Rahul)

- Plain, concise, honest. If they only ask a question, answer only that. No vague or convoluted plans,
  no hardware they don't have. Hackathon pressure: be fast and decisive.
- Always give **full wiring tables**. Identify ESP pins by the **printed label** (on the ideaspark ESP32,
  D33 sits between D26 and D25 — tell them to read labels). Refer to TS832 wires as part of the
  **2-pin plug** (power) or **3-pin plug** (video).
- They have no oscilloscope; work from the terminal (no Arduino IDE GUI). Only 2 kΩ resistors on hand.
- Run Pi commands yourself over SSH when you have access, rather than asking them to.
- Commit/push only with their OK. Never put credentials in the repo.

## 9. Camera-feature next steps (proposed to the user, not started)

Computer authority is **yaw only**, so true obstacle avoidance (stop/back off/climb) is impossible by
design; the cage is the obstacle strategy. The repo's mapped navigation (`mapping.py` D435 static scans +
`navigation.py` A* + wall-tag `localization.py`) is advisory-only, has no live obstacle sensing, and needs
a D435 survey + measured mount — not realistic during the hackathon. Recommended order:
1. **Colored-ball → yaw** (already wired): stop `fpv-stream.service`, run `ball_demo serve --camera
   /dev/video0 --camera-backend v4l2 --serial <port>` (+ `--trainer-output` only on user OK), tune HSV on
   real FPV, props-off CH4 check.
2. **"Follow tag" → yaw** (new, ~1 h): add a tag mode to the detector that feeds the tag's center x into
   the SAME `Controller` path the ball uses (keeps watchdog / blank-video / loss → neutral). No calibration
   needed for yaw. Needs big printed 36h11 tags (≥10 cm).
3. **Tag-as-obstacle demo** (~30 min on top of 2): a designated "avoid" tag that is large in frame (close)
   yaws the drone away from it. Pilot still stops the drone.
4. Full calibrated tag display (`--target-calibration`/`--target-delay-ms`/`--roster`, `nav-calibrate`
   needs a bundle with a measured mount) — display only; skip unless judges need distance readouts.
The user was asked for tag size and follow/avoid IDs before coding 2–3. First manual hover comes first.
