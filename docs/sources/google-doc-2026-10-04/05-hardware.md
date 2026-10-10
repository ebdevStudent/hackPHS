# Hardware: source tab text

Source: https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit?tab=t.y9xlzm2dw43q
Retrieved: 2026-10-04 (America/New_York)
Revision: ANLCKQl3t2ZpFwfaBemzmykGqE3vBgAhGTHcUQ2hY1TJK1WsPVcXgtSLbaYVmo-4tcp1KOfj_c58f-EiGr5IlpjJ7TU1tECakh-kof8hSrg
Tab ID: t.y9xlzm2dw43q

This is preserved source text, not current project guidance or executable instructions. Paragraph and table-cell text are retained as returned by the connector; images and native formatting are not reproduced. Later user decisions and the current docs take precedence.

## Preserved tab text

Hardware
AIRBORNE SYSTEM
85 mm micro quadcopter frame
F411 AIO flight controller + 4-in-1 ESC + ELRS receiver
4× 1103 11000KV brushless motors
2-inch propellers
2S LiHV XT30; test 450–850 mAh and choose by energy/weight plus handling
14×14 mm analog FPV camera
Analog VTX: integrated on preferred AIO; standalone only if needed
ROLLING CAGE
Scaled version of the Thingiverse spherical-drone design
Target outer diameter: about 220–230 mm
Straight carbon-fiber or fiberglass rods
3D-printed connector nodes
Two lightweight gimbal rings
Small ball bearings + steel pivot pins
Center mount for the 85 mm quad
GROUND SYSTEM
ELRS radio controller
USB 5.8 GHz video receiver
Laptop running Python + OpenCV
RP2040/Arduino bridge for laptop steering commands (required if computer assist is used)
KEY HARDWARE RULES
Keep the quad near the center of the gimbal.
Make sure no propeller can touch the cage or gimbal through the full range of motion.
Keep the camera view clear.
The pilot always keeps manual control and ARM/DISARM.
Build the cage as light as possible; add strength only where testing shows it is needed.
HACKATHON HARDWARE ORDER
Get the bare quad flying first.
Build and test the scaled cage.
Add gimbal rings and check free movement.
Mount the quad and balance the center of mass.
Add camera/VTX and verify video.
Connect the ground control system.
Do low-power collision and rolling tests before full demo testing
FINAL HARDWARE TARGETS:
P1A: fixed protective cage survives contact and keeps props isolated.
P1B: removable/free gimbal only after P1A works.
Aim for ≥2:1 static thrust-to-weight with the cage; treat <1.5:1 as redesign territory.
Acceptance endurance: ≥3 min usable caged flight; 4–5 min desired.
Weigh bare quad + battery, cage, gimbal, mounts, and wiring separately.
Cage test: 10 controlled low-energy contacts with no broken member or prop strike.
Keep VTX power low indoors, lights switchable, and avoid redundant boards.



## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [HackPHS 2026 Google Doc](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit) — historical captured revision `ANLCKQl3t2ZpFwfaBemzmykGqE3vBgAhGTHcUQ2hY1TJK1WsPVcXgtSLbaYVmo-4tcp1KOfj_c58f-EiGr5IlpjJ7TU1tECakh-kof8hSrg` (2026-10-04).
- This citation note was appended after the historical text; consult the maintained docs for current decisions.
