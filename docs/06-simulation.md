# Simulation — application visualizer and presentation fallback

Source: Google Doc **Simulation**, read 2026-10-07. [Source snapshot](sources/google-doc-2026-10-07/06-simulation.md). User decision: keep the simulator illustrative; matching physical geometry is not required work.

## Purpose and priority

Run a small 3D browser game on the Mac to illustrate industrial inspection and search/rescue with a contact-tolerant cage. It is an application visualizer and Plan B alongside the physical demonstration.

Prioritize **one stable, polished industrial map** and the physical build. Rescue-map additions follow only after the physical demo and industrial map are stable. The existing repository already contains both maps; their presence does not require expanding either.

Show game footage separately from live FPV. Virtual battery, motion, yaw, detection and collision behavior are simulation values, not measured aircraft telemetry.

## Source design

Three.js handles browser rendering, world geometry, drone/cameras, lighting, effects and most gameplay. HTML/CSS/JavaScript supplies the interface. A Python FastAPI/Flask backend is optional for mission state, scoring or live-data exchange; Python does not render the 3D scene. Rapier.js/Cannon-es are optional physics approaches, not required migrations.

Chrome/browser is primary. PyWebView may package the same game; Electron/Tauri are source alternatives. Avoid a large backend built only for presentation.

Expected features: flying/turning, wall contact/bounce/slide/roll, chase and optional FPV cameras, camera-view target detection, collision handling, HUD, objectives, timer, score and virtual battery.

| Scenario | Mission |
| --- | --- |
| Industrial inspection | Navigate machines, shelves, pipes and narrow passages; identify leak/overheat/blockage markers; inspect all points and return |
| Search and rescue | Navigate a damaged building/debris, find trapped-person markers, mark locations and exit |

## Existing checkout and geometry

[WasimVorvoi/HackPHS](https://github.com/WasimVorvoi/HackPHS) is the existing simulator that this project joins. On this machine it is under `simulation/` (`server.py`, `static/`, `tools/`). In the published integrated repository those simulator files remain at the repository root. The maintained navigation source on this machine is top-level `software/`, not the older copied `simulation/software/`. Review the current [repository README](https://github.com/WasimVorvoi/HackPHS#wasims-existing-ball-drone-flight-sim) for the original run instructions; the older local source checkout is not a separate project subdirectory in the published repository.

The current game is **free flight with no objectives, scoring or target detection** (those were removed in the simulator's "Free-flight simulator core" commit). It has Three.js rendering with post-processing, three maps (industrial bay, rescue site and a physics test bay), rigid-body contact on the gimbal's outer ring (no cage since 2026-10-11, see below), a battery/voltage-sag model, a telemetry HUD and minimap, FastAPI and a PyWebView wrapper.

The industrial map now marks the three inspection points this tab names. Numbered yellow placards make a judge route: **1** the steam leak on the pipe run, **2** an overheating CNC 2 (pulsing red beacon on its stack light), **3** a carton jammed at the conveyor end (2026-10-08). They are visual markers, not objectives.

**Geometry mismatch:** the integrated simulator source models the earlier Meteor85-class aircraft. Its parameters set a 112.5 mm cage circumradius, 5 mm hub radius (a 235 mm outer contact envelope), and 50.8 mm propeller diameter (2 inches). The current physical plan is Apex-2 (~95 mm wheelbase) with a 245–250 mm cage and 2-inch props. The prop size matches; frame and cage geometry do not. An earlier copied README says 372 mm/4-inch; the checked `static/js/spec.js` and `static/js/drone.js` values do not support that description. User explicitly accepts the simulator as illustrative and defers matching it. Neither virtual collisions nor the rendered gimbal establish physical strength, clearance or endurance.

The [recorded smoke](../evidence/simulation-smoke.json) (`tools/simulation_smoke.py`, 2026-10-08) loads all three maps and checks, with no page errors or off-machine requests:

- fixed-step flight through the game's `__game.fly` test API;
- the motor power toggle, the camera cycle, and pause/resume;
- that posted telemetry is shown as text, not HTML;
- that a level which fails to load returns to the previous working level.

The headless physics check `node --import ./tools/test/register.mjs tools/test/physics_test.mjs` now asserts its results and exits non-zero on failure:

- hover holds 1 m;
- the wall stops the outer gimbal ring;
- rolling on the floor spins the gimbal up, and each ring turns only about its own pivot axis;
- a passive drone rests on the outer ring's envelope (102 mm);
- a discharged pack sags;
- auto-land happens after a plausible time.

Industrial-map frame rate on this Mac (Apple M4, Chromium with Metal, 1280 × 800, post-processing on) measured **30–37 fps before and 35–37 fps after** the inspection markers, under heavy background load. Neither check is a full flight playthrough, a desktop-wrapper test or validation of physical dynamics.

## Run on the Mac

Install the simulator's `requirements.txt` into a dedicated environment. For this local checkout, launch from `simulation/`; in the published GitHub checkout launch from its repository root:

```sh
cd /Users/devk/Documents/HackPHS26/simulation
python server.py --no-browser
```

Open `http://127.0.0.1:8765/`. Running `python server.py` opens the browser automatically; `python desktop.py` is the optional wrapper. Port 8765 is separate from the monitoring application's port 8080.

| Key | Current game action |
| --- | --- |
| W/S | Forward/back |
| A/D | Turn (yaw) left/right |
| Q/E | Strafe left/right |
| Space/Shift | Climb/descend; hold Shift on the floor to land |
| P | Motor power on/off |
| V / C | Swap FPV inset and main view / cycle chase, FPV and orbit |
| B | Cycle the simulated 450/550/650/850 mAh packs |
| L | Inspection lights |
| 1/2/3 | Industrial / rescue / physics test bay |
| T / G | Physics vectors / graphics quality (Low default, High) |
| N / I | Minimap / telemetry panel |
| R, Esc, F11 | Reset, pause, fullscreen |
| M / H | Mute / help |

The source labels Q/E “strafe or yaw”; the game uses strafe.

## Presentation and future integration

The physical drone demonstrates actual contact/recovery and live vision. The game illustrates potential use in factories, warehouses and damaged buildings. A game-only presentation does not establish the accepted physical manual-contact/live-tracking result.

Minimal digital-twin synchronization is **P4**, limited initially to MANUAL/AUTO, target captured and mission complete. Do not activate the repository's fake telemetry as a claim of a live aircraft link.

### Navigation caveat — 2026-10-08

The controller in `static/js/drone.js` uses exact simulated horizontal/vertical velocity for movement and altitude feedback; `static/js/main.js` supplies keyboard commands. `server.py` accepts/display telemetry but is not an aircraft command interface. These capabilities do not supply missing physical pose/velocity sensing or navigation controllers. For future navigation experiments, explicitly distinguish exact simulation state from estimated vision measurements with delay, noise and loss. Physical geometry matching remains deferred.

The independent [navigation mock follower](23-navigation-software.md) uses rendered/noisy surveyed-tag observations, with separate simulation truth, pose loss/reacquisition and bounded mock velocity. It can use a labeled simulation copy of a D435 map bundle. It does not control this Three.js game or the aircraft; exact game telemetry remains illustrative.

[Ground-Pi navigation plan](20-semi-autonomous-navigation.md) · [Next-session handoff](21-navigation-codex-handoff.md).

[Demo routes](12-demo-runbook.md) · [Current priorities](08-future.md) · [References/evidence](07-refs.md).


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Google Doc — Simulation tab](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit?tab=t.5xh0imufqx1q) — Source snapshot captured 2026-10-07.
- [WasimVorvoi/HackPHS](https://github.com/WasimVorvoi/HackPHS) — Existing simulator repository.
- [Simulation parameters](https://github.com/WasimVorvoi/HackPHS/blob/main/static/js/spec.js) — Current model parameters; these are illustrative values.
- [Simulation contact/flight model](https://github.com/WasimVorvoi/HackPHS/blob/main/static/js/drone.js) — Current implementation, not physical validation.
- [Recorded simulation smoke](../evidence/simulation-smoke.json) — Short software-only check.

## Final CAD print package — 2026-10-09

The final print package and selected fit data are in [print_now](../cad/apex2-cage/print_now/START_HERE.md). A refreshed local simulator builder/model and headless check are preserved as [CAD finalization evidence](../cad/apex2-cage/review-2026-10-09-finalization/simulator-refresh/README.md), with 144.68 / 166.68 g accounted estimates. This CAD publication does not replace the published simulator runtime. The refreshed local simulator remains illustrative and does not establish physical strength, mass, clearance or flight performance.

## Cage removed, lighter graphics, visible gimbal — 2026-10-11

User request: remove the cage, make the game lighter to render, and make the gimbal more realistic and easier to see.

- **No cage.** The icosahedral cage is no longer drawn or simulated, and its rods and hubs are out of the mass budget. Contact uses the outer ring's envelope: a 102 mm sphere covering the ring and its yaw bearings. Each contact gets an impulse with normal restitution, PETG Coulomb friction (μ 0.3) and a small rolling resistance, so the drone still bumps, slides and rolls.
- **P1B gimbal, procedural.** The outer ring is orange (96.5 mm, 16.5 g) and the inner ring blue (86.5 mm, 14.8 g), from §2.3 of [motion physics](22-motion-physics.md). Every pivot has dark bearing blocks, steel MR52ZZ races and Ø2 mm pins. The chain in three.js axes is: free support →Y (yaw)→ outer →X→ inner →Z (fore-aft)→ aircraft. Ring angles come from a ZXY split of the aircraft and support attitudes. White-tabbed hubs on the yaw pins show the yaw rotation, which the rings themselves cannot show. The CAD aircraft's old X-axis pivot arms are hidden; new arms run along Z, under the props. Both rings stay clear of the prop disks, whose tips reach at most 70 mm.
- **Graphics quality (G).** Low is the default:
  - no GTAO, bloom or SMAA (the composer is built only for High);
  - pixel ratio 1 with MSAA;
  - one 1024² hard-PCF shadow (sun or moon), and shadow maps drawn once per frame, not again for the FPV inset;
  - 60 % particle rates in a 3000-particle pool;
  - a render scale that drops to 0.85 / 0.7 while the frame rate stays under 40 fps.

  High restores the earlier effects. `?quality=high` or the saved choice overrides the default.
- **Measured on an Intel UHD (TGL GT1) laptop GPU**, headless Chrome at 1280 × 800, industrial map: 16 fps before the change, 28 fps on Low at full scale, about 41 fps on Low after dynamic scaling, 18 fps on High. Rescue and lab hold 60 fps on Low.

