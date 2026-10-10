# Idea — Ball Drone

Source: Google Doc **Idea** tab, read 2026-10-04. [Preserved tab text](../google-doc-2026-10-04/01-idea.md). Current user decisions are recorded in [decisions.md](decisions.md).

## Mission

Build a small indoor drone that can contact a prepared obstacle, recover, and continue flying. A lightweight protective cage isolates the propellers. A camera and ground computer support colored-target detection and yaw centering. The current demonstration assigns tracking/control/server processing to Pi 5 and development plus simulation to the Mac.

Inspection, search and rescue, education, and navigation research are intended applications. The hackathon demo establishes a narrow mechanical and control proof; these applications are not verified capabilities.

## Core build

- 85 mm micro quad with Betaflight stabilization and ELRS radio control.
- Lightweight protective cage around the aircraft.
- P1A: fixed cage with an adjustable center mount.
- P1B: removable two-ring gimbal after the fixed-cage build works.
- Analog FPV capture to the Pi processing host (receiver compatibility remains unverified).
- HSV colored-target tracker and judge-facing HUD.
- Optional enabled computer assistance limited to yaw in V1.
- Pilot retains throttle, roll, pitch, ARM/DISARM, and physical override.

## Intended demo

Manual takeoff → deliberate low-energy foam/cardboard contact → recovery → enable assistance → yaw-center on a colored target → physical override → re-enable assistance → cover the target to demonstrate target-loss neutral → manual landing.

The source requests three complete rehearsals in a row before relying on the live demo.

## Provisional success targets

- At least 3 minutes of usable caged flight; 4–5 minutes desired.
- Aim for at least 2:1 static thrust-to-weight; below 1.5:1 triggers redesign.
- Ten controlled low-energy contacts without a broken cage member or prop strike.
- Computer commands neutralize on target loss or communication failure.
- Physical pilot override works consistently.

## Later scope

After the core works: small pitch assistance, AprilTag inspection and snapshots, telemetry summaries/replay, and switchable inspection lighting.

Minimal real-to-virtual state sync is P4. SLAM, wall climbing, toss launch, advanced navigation, and two-way audio are outside the core hackathon build.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Pre-rewrite archive index](README.md) — identifies this file as historical context, not current instruction.
- [Maintained document](../../01-idea.md) — current requirements and status.
- This citation note is external to the preserved pre-rewrite text.
