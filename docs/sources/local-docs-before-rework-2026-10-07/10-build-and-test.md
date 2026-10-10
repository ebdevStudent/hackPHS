# Build sequence and evidence

Source: [S1](README.md#source-and-current-status), read 2026-10-04. Physical stages below remain planned. The separate [pre-hardware software status](11-pre-hardware-status.md) records completed software checks.

## Ordered stages

| Stage | Work | Evidence needed before proceeding |
| --- | --- | --- |
| P0 — platform and control | Confirm components, configure bare quad/ELRS/FPV, prototype Pi-to-radio path with props removed | Stable manual flight; verified control channel mapping, physical override, watchdog, and target-loss neutral |
| P0 — mass and endurance | Weigh bare aircraft and packs; establish thrust and mass budget | Measured component masses and available thrust margin |
| P1A — fixed cage | Build cage and adjustable center mount; check camera, airflow, battery access, and prop separation | Cage mass, fit checks, and controlled contact results |
| P1B — removable gimbal | Add rings, bearings, and pivots after P1A succeeds | Free motion, balance, and full prop-clearance envelope |
| P2 — core assistance | HSV tracking, yaw-only correction, command limits, loss behavior, and clear HUD | Stable centering and consistent pilot takeover |
| Demo readiness | Integrate and rehearse the full sequence | Three complete judge-facing runs in a row |
| P2.5 / P3 | Pitch assistance, tags, snapshots, lighting, and telemetry upgrades | Core remains reliable after each addition |
| P4 | Minimal real-to-virtual state synchronization | Physical demo and presentation already work |

## Acceptance targets from the source

- Physical override: 20/20 props-off checks, then 5/5 airborne checks.
- Target loss: computer commands return neutral every check.
- Tracking: no sustained oscillation; clamps and slew limits active.
- Cage: ten controlled low-energy contacts without broken members or a prop strike.
- Endurance: at least 3 minutes of usable caged flight; 4–5 minutes desired.
- Static thrust-to-weight: aim for at least 2:1; below 1.5:1 calls for redesign.
- Demo: three complete rehearsals in a row.

These are proposed gates, not completed test results. Airborne work depends on the prior mechanical/control checks and a suitable operating environment.

## Measurements to record

- Bare quad, pack, cage, gimbal, mounts, and wiring mass separately.
- Battery capacity/model, all-up mass, flight time, starting/ending voltage, and hover throttle.
- Compare a light baseline, mid-capacity pack, and higher-capacity 2S pack.
- Propeller choice and optional lighting effects after establishing a baseline.
- End-to-end command latency, communication loss, target loss, and override behavior.
- Contact damage, cage flex, gimbal friction, camera obstruction, and any prop intrusion.
- Photos, clips, and notes linked to the tested configuration.

## Presentation fallback

If a flight demonstration is unavailable, use recorded contact/flight evidence and the live software/simulation. If the command bridge is incomplete, present live vision/HUD with manual steering and state its actual control capability accurately.

## Current evidence

[Software evidence](../../../evidence/README.md) records hardware-free tracking/control, browser, protocol and firmware-build checks. These do not satisfy the physical gates above. No completed flight, cage-contact, endurance or electrical trainer-path result is recorded.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Pre-rewrite archive index](README.md) — identifies this file as historical context, not current instruction.
- [Maintained document](../../10-build-and-test.md) — current requirements and status.
- This citation note is external to the preserved pre-rewrite text.
