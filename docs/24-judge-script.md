# Judge script and rehearsal checklist (one page)

Updated 2026-10-08. Choose the route **before** each rehearsal using the [runbook](12-demo-runbook.md#choose-the-route-before-rehearsal). Physical yaw assistance is used only after the [physical assistance gate](10-build-and-test.md#physical-assistance-gate) passes. Otherwise run the manual route; it counts as success.

## Roles

| Role | Holds | Owns |
| --- | --- | --- |
| Pilot | Transmitter | ARM/DISARM, every flight command, the call to abort |
| Presenter | Laptop or Pi screen | Talking, the fallback screen, evidence slides, the game |
| Spotter | Timer, spare pack, safety glasses | Clear area, foam/cardboard target, timekeeping, landing call at 3:30 flight time |

## Screens

**Live:** `http://<pi-ip>:8080/fallback`. The native app's **View → Manual fallback view** shows the same content. It must show:

- live FPV with the target box;
- the centre/error indicator;
- **"Manual steering — computer steering unavailable"**.

The simulator (`http://127.0.0.1:8765/`, industrial map) runs on the Mac on its own screen. It is never presented as live aircraft data.

## Manual route — about 5 minutes

| Time | Pilot | Presenter says / shows |
| --- | --- | --- |
| 0:00 | Disarmed, props visible | "A small drone inside a 248 mm cage, so touching walls need not end the flight. The pilot flies everything." |
| 0:30 | ARM, manual takeoff to 1 m | Fallback screen: live FPV, status line in yellow |
| 1:00 | Low-energy contact with the foam/cardboard wall, recover | "That was a deliberate contact; the cage took it and the pilot recovered." |
| 1:45 | Hover; spotter moves the coloured target | "The Pi tracks the target live — box, centre line, error. The computer is not steering." |
| 3:00 | Land, DISARM | Measured evidence: mass, thrust, contacts passed, endurance |
| 3:45 | — | Industrial game on the Mac: "where this goes — inspection in plants and rubble" |
| 4:45 | — | Questions |

## Assisted route (only when the assistance gate passed)

Replace 1:45–3:00:

1. Pilot holds a stable hover.
2. The operator enables yaw assistance.
3. The aircraft centres the target.
4. The pilot overrides on the sticks.
5. The operator re-enables.
6. The spotter covers the target, and the screen shows neutral.

The pilot lands; the operator disables.

## Failure branches (decide before the run, not during it)

| If… | Then |
| --- | --- |
| Video lost or frozen (screen says *Video stale*) | Keep flying manually, land; show saved footage and say so |
| Tracking jumps or loses target | Expected: screen shows *Target not found*; continue the manual route |
| Any doubt about assistance | Disable (neutral), continue manual — never re-enable in front of judges after a fault |
| Contact leaves a cracked part or rod out | Land, DISARM, swap in the spare cage section or switch to the game and evidence |
| Low battery warning | Land immediately; spare pack is with the spotter |
| Aircraft cannot fly at all | Game plus recorded evidence; say plainly that the physical demo is not running |

## Before every rehearsal (tick all)

- [ ] Packs charged; each pack's label and voltage logged ([battery log](25-test-records.md#battery-log))
- [ ] Props, cage, rods and pins inspected; no loose hubs
- [ ] Transmitter failsafe tested with props off
- [ ] Pi service healthy: `curl http://<pi-ip>:8080/api/health` reports `ok: true`, MANUAL
- [ ] Fallback screen shows live FPV, box, error indicator and the status text
- [ ] Simulator open on the industrial map
- [ ] Foam/cardboard contact wall placed; area clear; safety glasses on

## Three-run record (need three consecutive complete runs)

| Run | Date/time | Route | Pack | Completed? | Problem / fix | Consecutive count |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |

Any failure resets the count. Only fixes that restore already-working functions are allowed in the last 24 hours; no new features from 48 hours before the first judged demo.
