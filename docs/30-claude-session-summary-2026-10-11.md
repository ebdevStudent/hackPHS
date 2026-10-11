# Claude session summary — 2026-10-11

Bench session on branch `esp32-trainer-ppm`. Details, readbacks and before/after backups are
in [decisions.md](decisions.md); this page is the short version.

## Fixed / verified

| Area | Result | Evidence |
| --- | --- | --- |
| Motor 1 "intermittent spin" | Not a fault. Test value 1020 = ~2 % DShot throttle (ESC loses sync). At 1100 (= 10 % armed idle) it spins smoothly | Laptop MSP readback + user observation |
| Motor corners + directions | **Verified** (user-observed): M1 CW, M2 CCW, M3 CCW, M4 CW with the M2/M4 side as the nose. ESCs: M1, M3 reversed; M2 normal; M4 default | Bench spin test |
| Throttle reading 1293 | Not a fault: the stick wasn't fully down. Reads 989–995 at the bottom | Live RC readback |
| Pocket ↔ FC link | ELRS link live; Pocket SD config matches FC (AETR, SA→CH5 ARM) | SD card read + live RC |
| FPV video | **Working end to end**: camera → AIO VTX → RC832 (5-8) → MS210x capture → Pi → dashboard | `evidence/physical/fpv-first-live-frame-2026-10-11.jpg` |

## Betaflight changes (all backed up first, verified by readback)

| Setting | Value | Why |
| --- | --- | --- |
| `vtx_band` / `vtx_channel` | 5 / 8 = **Raceband 5917 MHz** | Band was never set (frequency 0), so the VTX wasn't on the documented channel |
| `vtx_power`, `vtx_low_power_disarm` | 3 (25 mW), OFF | Bench video without arming; cool indoors |
| `level_limit` (all PID profiles) | 35° | Max Angle-mode tilt for rolling/indoor flight |
| `roll/pitch_level_expo` (all rate profiles) | 40 | Gentler small-stick leans (no true speed cap without GPS/optical flow) |
| ANGLE mode | **Parked** (`aux 1 1 0 900 900 0 0`) | User decision: enable only when the drone is built and mounted in the gimbal |

Backups: `~/Documents/betaflight-diff-all-2026101*-*.txt` on the laptop; the pre-Angle-mode
copy is also in `docs/sources/bench-handoff-2026-10-11/`.

## New tools

- `tools/betaflight_motor_bench.py`: status, config, ESC info, direction, pulse (max 1150).
- `tools/motor_dashboard.py` + `.html`: local web dashboard at http://127.0.0.1:8765.
  - Motors tab: sliders, test buttons, direction buttons, arming-block readout, "Allow radio arming".
  - Camera tab: live FPV, plus a video on/off switch (VTX pit mode, ~0.1 A saved).
  - Safety: dead-man heartbeat, Space = STOP.
- Dashboard **Preflight** tab: read-only GO / NO-GO from FC + Pi, plus the manual checklist.
- AprilTag follow + landing guidance, tag kit and Pi `drone-mode`: see [31-apriltags-and-tracking.md](31-apriltags-and-tracking.md).
- `tools/pi/`: FPV streamer (`fpv-stream.service`, port 8090) with capture-stick auto-reset, installed on the Pi.

## Next steps

1. Confirm motor directions (M1/M4 CW, M2/M3 CCW from above) and corner numbering.
2. Mount the FC in the frame/gimbal, then set board orientation if needed.
3. Enable ANGLE mode (`aux 1 1 0 900 2100 0 0`), then calibrate the accelerometer level in the gimbal
   (stick command: left stick up-left + right stick down, disarmed).
4. Charge packs (the OSD shows `BATT < FULL` at 7.36 V), check failsafe, then the first props-on hover.
5. Remaining 20 ESP32 trainer/yaw trials; the switch from FPV streamer to tracking app on the Pi.
