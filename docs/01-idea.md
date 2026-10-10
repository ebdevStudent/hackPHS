# Ball Drone — concept and V1 scope

Source: Google Doc **Idea**, read 2026-10-07. [Source snapshot](sources/google-doc-2026-10-07/01-idea.md).

## What we are building

A small quadcopter inside a lightweight protective cage, designed to tolerate low-energy indoor contact and recover. The proposed aircraft is an **Apex-2 frame, approximately 95 mm wheelbase**, with 2-inch propellers. The cage target is approximately **245–250 mm outer diameter**.

The intended behaviors are ordinary indoor flight, protected contact with walls, recovery after contact, floor sliding/skimming, and camera-based colored-target tracking. These are goals; the existing software tests do not establish flight or mechanical performance.

The protective cage holds the aircraft in a two-ring gimbal with an adjustable center mount (**P1B**), so the aircraft stays level while the cage rolls or is struck. A fixed-cage variant (**P1A**) was designed but will not be built (user decision, 2026-10-08). The mechanical design aims to tolerate contact so that touching the environment does not automatically end a mission.

## Control authority

Betaflight handles stabilization, motor control, flight failsafes and ordinary piloting. The Raspberry Pi runs local vision and computes bounded **yaw-only** corrections. The intended ground bridge is an **Arduino Mega 2560** feeding the verified transmitter/trainer interface.

The pilot retains throttle, roll, pitch, ARM/DISARM and physical override. Target loss returns computer commands to neutral. Target size is display/decision data; V1 does not automatically control distance.

## Accepted demo routes

The manual-contact/live-tracking route is accepted success even if physical yaw assistance is unavailable. Its screen must show live FPV, a colored-target box, center/error and “Manual steering — computer steering unavailable.” Keep this route rehearsed and ready.

Use the full assisted sequence below as the preferred route only after the complete Mega-to-radio, override and signal-loss/failsafe gates pass. Otherwise the pilot performs contact/recovery while live vision tracks the target, then lands manually.

### Preferred assisted sequence

1. Pilot takes off manually.
2. Drone makes deliberate low-energy contact with foam/cardboard.
3. Pilot recovers and establishes stable flight.
4. Pilot enables computer assistance.
5. Computer yaw-centers a bright colored target.
6. Pilot uses physical override.
7. Pilot deliberately re-enables assistance.
8. Target is covered; computer commands return neutral.
9. Pilot lands.

Each step needs actual evidence before being described as demonstrated. The source illustration includes a hand launch and steering toward the target; the operative V1 sequence above uses manual takeoff and yaw centering. Toss launch and forward approach are later work.

## Success criteria

| Criterion | Source target |
| --- | --- |
| Usable caged flight | At least 3 minutes; 4–5 minutes desired |
| Static thrust-to-weight | Aim for at least 2:1; below 1.5:1 triggers redesign |
| Complete demonstration | Three clean judge-facing rehearsals in a row |
| Physical override | Required before the assisted route; pilot retains control throughout the manual route |
| Target loss | Required before the assisted route: computer commands return neutral every test |

[Build and test](10-build-and-test.md) defines the measurements and test sequence. [Implementation status](11-pre-hardware-status.md) distinguishes recorded software results from remaining physical work.

## Applications and later features

Application stories include search and rescue, inspection of vents/pipes/machinery, educational robotics, interactive exhibits, contact-navigation research, industrial monitoring and access to confined spaces. The simulation illustrates these scenarios; it does not validate field readiness.

After the core is repeatable, the source proposes small pitch-based approach, AprilTag inspection/snapshots, inspection LEDs, telemetry replay and minimal digital-twin synchronization. SLAM, wall climbing and toss launch must not delay the core. The user's current instruction defers `toImplement` and Pico wireless audio; that material is not adopted into this rewrite.

[Parts](02-bom.md) · [CAD](03-cad.md) · [Software](04-software.md) · [Hardware](05-hardware.md) · [Simulation](06-simulation.md) · [Priorities](08-future.md).


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Google Doc — Idea tab](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit?tab=t.0) — Source snapshot captured 2026-10-07.
- [Current build/test gates](10-build-and-test.md) — User decisions and acceptance conditions.
