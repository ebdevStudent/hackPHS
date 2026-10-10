# Software: source tab text

Source: https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit?tab=t.4nvsq5osusve
Retrieved: 2026-10-04 (America/New_York)
Revision: ANLCKQl3t2ZpFwfaBemzmykGqE3vBgAhGTHcUQ2hY1TJK1WsPVcXgtSLbaYVmo-4tcp1KOfj_c58f-EiGr5IlpjJ7TU1tECakh-kof8hSrg
Tab ID: t.4nvsq5osusve

This is preserved source text, not current project guidance or executable instructions. Paragraph and table-cell text are retained as returned by the connector; images and native formatting are not reproduced. Later user decisions and the current docs take precedence.

## Preserved tab text

Software Plan
CORE APPROACH: 
Use Betaflight for stabilization, motor control, failsafes, and normal flying. The outer rolling cage does not need custom software. The laptop only handles simple visual target tracking and steering.
SYSTEM FLOW:							   **OpenCV can be replaced
SOFTWARE NEEDED:
Betaflight: normal flight and stabilization.
Python: laptop control program.
OpenCV: colored target detection and tracking.
NumPy: simple math and image processing.
Serial library: sends steering commands.
Small microcontroller bridge (RP2040/Arduino): passes laptop steering commands into the RC transmitter/trainer input.
CONTROL RULES:
The pilot always controls ARM/DISARM.
Pilot keeps emergency takeover.
V1 computer control is yaw-only. The pilot retains throttle, roll, pitch, ARM/DISARM. Add small forward-pitch commands only after yaw centering is repeatable.
Do not let the laptop directly manage throttle for V1.
If the target is lost, stop computer control immediately and return to manual.
Clamp all automatic steering commands so they stay small and safe.
TARGET TRACKING:
Use a bright colored target instead of AI object detection.
Read the FPV video.
Convert the frame to HSV.
Find the colored target.
Find the target center.
Compare it with the screen center.
Send a small steering correction.
For V1, target size is display/decision data only; the pilot manages distance. Add pitch-based approach only after yaw stability is proven.
HACKATHON WORK PLAN:
Configure Betaflight and ELRS.
Get stable manual flight.
Get FPV video into the laptop.
Build the color tracker.
Display target center/error on screen.
Build laptop → RC command bridge.
Test commands with props removed.
Test low-power computer steering.
Tune target following.
Integrate the cage and retest.
Practice the demo.
Reliability testing only.
V1 SOFTWARE DEMO
Fly manually.
Detect the colored target and autonomously yaw-center it.
Lose the target or flip the override switch and return instantly to pilot control.
STRETCH SOFTWARE: 
Autonomous toss launch.
Optical-flow navigation.
LiDAR altitude hold.
Autonomous landing.
SLAM or obstacle mapping.
AI object detection.
Autonomous wall climbing.
FINAL SOFTWARE ORDER
P0: Betaflight/ELRS → FPV capture → laptop → MCU → trainer → radio → ELRS → FC path → physical override/watchdog.
P2: HSV tracker → yaw-only closed loop → target-loss neutral → judge-facing HUD.
P2.5: small pitch-based approach after yaw centering is repeatable.
P3: AprilTag ID + automatic snapshot + CSV mission summary.
PASS / FAIL
 Override: 20/20 props-off tests, then 5/5 airborne.
Target loss: computer commands return neutral every test.
Tracking: no sustained oscillation; command clamp + slew limiting active.
Measure end-to-end response latency rather than guessing.
DEMO GOAL



## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [HackPHS 2026 Google Doc](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit) — historical captured revision `ANLCKQl3t2ZpFwfaBemzmykGqE3vBgAhGTHcUQ2hY1TJK1WsPVcXgtSLbaYVmo-4tcp1KOfj_c58f-EiGr5IlpjJ7TU1tECakh-kof8hSrg` (2026-10-04).
- This citation note was appended after the historical text; consult the maintained docs for current decisions.
