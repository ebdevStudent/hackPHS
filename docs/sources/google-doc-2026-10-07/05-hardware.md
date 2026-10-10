# Source snapshot — Hardware

Source: https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit?tab=t.y9xlzm2dw43q

Read: 2026-10-07. Tab order: 4; parent: none. 

---

# Hardware



AIRBORNE SYSTEM

- Apex-2 frame (~95 mm wheelbase)



- F411 AIO flight controller + 4-in-1 ESC + ELRS receiver

- 4× HGLRC Specter 1202.5 11000KV brushless motors (9 mm M2 mount)

- 2-inch propellers

- 2S LiHV XT30; test 450–850 mAh and choose by energy/weight plus handling

- 14×14 mm analog FPV camera

- Analog VTX: integrated on preferred AIO; standalone only if needed



ROLLING CAGE

- Scaled version of the Thingiverse spherical-drone design

- Target outer diameter: about 245–250 mm



- Straight carbon-fiber or fiberglass rods

- 3D-printed connector nodes

- Two lightweight gimbal rings

- Small ball bearings + steel pivot pins

- Adjustable center mount for the Apex-2





GROUND SYSTEM

- ELRS radio controller

- RC832 5.8 GHz analog FPV receiver

- Raspberry Pi 4/5 running Linux + Python + OpenCV

- Arduino Mega 2560 bridge for Raspberry Pi steering commands (required if computer assist is used)





GROUND VIDEO / COMPUTE PATH

RC832 5.8 GHz analog FPV receiver.

Yellow RCA composite-video cable from RC832 video output.

USB composite-video capture adapter with Linux V4L2/UVC support (VIXLW BR116 is the current low-cost candidate; verify that it appears as /dev/video0 on the Pi).

Raspberry Pi 4 or 5 running Linux, Python, and OpenCV.

Stable power for the Raspberry Pi plus the required 12 V supply for the RC832 receiver.

Raspberry Pi Wi-Fi connection for remote preview/telemetry only; autonomous vision and control stay local on the Pi.



KEY HARDWARE RULES

- Keep the quad near the center of the gimbal.

- Make sure no propeller can touch the cage or gimbal through the full range of motion.

- Keep the camera view clear.

- The pilot always keeps manual control and ARM/DISARM.

- Build the cage as light as possible; add strength only where testing shows it is needed.



HACKATHON HARDWARE ORDER

- Get the bare quad flying first.

- Build and test the scaled cage.

- Add gimbal rings and check free movement.

- Mount the quad and balance the center of mass.

- Add camera/VTX and verify video.

- Connect the ground control system.

- Do low-power collision and rolling tests before full demo testing



FINAL HARDWARE TARGETS:

- P1A: fixed protective cage survives contact and keeps props isolated.

- P1B: removable/free gimbal only after P1A works.

- Aim for ≥2:1 static thrust-to-weight with the cage; treat <1.5:1 as redesign territory.

- Acceptance endurance: ≥3 min usable caged flight; 4–5 min desired.

- Weigh bare quad + battery, cage, gimbal, mounts, and wiring separately.

- Cage test: 10 controlled low-energy contacts with no broken member or prop strike.

- Keep VTX power low indoors, lights switchable, and avoid redundant boards.







## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Google Doc — Hardware tab](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit?tab=t.y9xlzm2dw43q) — source revision `ANLCKQnLVBOUgYbF9xiV7-InTsia-NHBAIK6uRHga-e4J5upeOn-tJgL1FVO9wv0_COaZWscwb-pNlIDnIFEctx2nWF87sQFyqftuH4YmVg`, captured 2026-10-07.
- This citation note was appended after the captured text; it is not part of the source tab.
