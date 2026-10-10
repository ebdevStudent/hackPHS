# Hardware

Source: Google Doc **Hardware** tab, read 2026-10-04. [Preserved tab text](../google-doc-2026-10-04/05-hardware.md). Current user decisions are recorded in [decisions.md](decisions.md).

## Airborne system

- 85 mm micro quadcopter frame.
- F411 AIO flight controller, ESC, ELRS receiver, and analog VTX where supported by the selected board.
- Four 1103 11000KV class motors and 2-inch propellers.
- 2S LiHV XT30 battery; test roughly 450–850 mAh packs.
- 14 × 14 mm analog FPV camera; standalone VTX only when needed.

Exact purchased models and compatibility remain unconfirmed. The [BOM](02-bom.md) lists candidates and purchasing inputs.

## Mechanical system

Provisional cage diameter is 220–230 mm. Use straight rods and lightweight printed hubs. Build the fixed protective cage and adjustable center mount first (P1A), then add removable/free gimbal rings (P1B).

Keep the quad near the gimbal center, balance the aircraft and battery, protect the camera view and propeller airflow, and check every prop disk throughout the reachable mechanical motion. [CAD](03-cad.md) contains the design checkpoints.

## Ground and demo equipment

The physical-control plan calls for an ELRS transmitter, USB FPV receiver, a computer running vision/control software, and an provisional RP2040/Pico bridge to the verified transmitter interface.

The confirmed roles are the user's Mac for development/simulation and Raspberry Pi 5 for tracking, yaw calculations and the browser demo server. The portable Pico bridge is compiled with no trainer output. Actual Pi, receiver, radio and USB operation remains unverified; fill in [hardware-arrival worksheet](13-hardware-arrival.md). See [software deployment](04-software.md#demo-deployment).

## Integration order and targets

Establish bare-quad manual flight and prototype the complete control/override path before cage integration. Then validate cage structure, gimbal movement, balance, prop clearance, FPV, and controlled contact behavior. Detailed stages and checks are in [build and test](10-build-and-test.md).

- Aim for at least 2:1 static thrust-to-weight; below 1.5:1 triggers redesign.
- Target at least 3 minutes of usable caged flight; 4–5 minutes desired.
- Weigh the bare quad/battery, cage, gimbal, mounts, and wiring separately.
- Target ten controlled low-energy contacts without cage damage or a prop strike.
- Use low indoor VTX power, switchable lighting, and minimal redundant electronics.

These are provisional targets, not measured results.

## Missing inputs

Exact hardware models, component dimensions/masses, trainer-port protocol and electrical levels, cable/bridge wiring, manufacturing constraints, and measured mass/thrust/endurance data remain unconfirmed.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Pre-rewrite archive index](README.md) — identifies this file as historical context, not current instruction.
- [Maintained document](../../05-hardware.md) — current requirements and status.
- This citation note is external to the preserved pre-rewrite text.
