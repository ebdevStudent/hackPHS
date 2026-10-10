# HackPHS 2026 — Ball Drone

This repository combines the current Ball Drone project with Wasim Vorvoi's existing flight simulator. Start with the [project documentation](docs/README.md) for requirements, build gates, CAD research, software and saved evidence.

## Physical project plan

The current aircraft plan is an Apex-2 (~95 mm wheelbase), four Specter 1202.5 11000KV motors, 2-inch props, and a 245–250 mm protective cage. The two-ring gimbal cage (P1B) is the only physical build (user decision, 2026-10-08); the fixed cage (P1A) stays CAD-only. P1B must pass ten consecutive low-energy contacts without damage or prop strikes, at least three minutes of usable caged flight, and repeatable manual recovery before demo use.

The user reports six batteries in inventory: four OVONIC 450 mAh packs and two OVONIC 2S, 7.6 V, 60C XT30 1100 mAh packs. The 1100 mAh product listing contains conflicting configuration/dimension fields, and the Apex-2 seller recommends 200–650 mAh. Measure the packs and confirm their labels, charge limits, fit, mass, center of gravity, and thrust margin before considering them for flight.

Manual piloting with live FPV target tracking is an accepted demo route. Use computer yaw assistance only if the complete Mega-to-radio bridge, pilot override, and signal-loss/failsafe checks pass. Keep simulation footage separate from live FPV. Pico wireless audio and the Google Doc's `toImplement` tab remain deferred.

| Directory | Contents |
| --- | --- |
| `static/`, `server.py`, `desktop.py` | Wasim's existing illustrative simulator and desktop wrapper |
| `docs/` | Current project plan, source snapshots, historical source copies, CAD research and runbooks |
| `software/` | Tracking, optional AprilTag localization/3D advisory navigation, browser/native operator UI, recording/replay and mock autonomous demo |
| `firmware/` | Internal-state-only Mega sketch and historical Pico parser/USB foundation; no verified trainer output |
| `cad/` | Cage generators, exports, print/assembly instructions, model checks and reference archive; physical fit/contact/endurance unverified |
| `evidence/` | Saved verification reports with their original dates and environments |
| `tools/` | Simulator utilities plus tracking verification/rehearsal tools |

## Navigation and repeatable D435 mapping

The user identifies **Raspberry Pi 5 and RealSense D435**. The D435 scans the zone **before** the demo; its registered map is saved and the scanner can be disconnected. During mapped guidance, the Pi uses the aircraft FPV feed and surveyed AprilTags. Updated obstacles/layout require map review/resurvey; a saved scan cannot detect new obstacles.

The implementation includes final-path camera calibration/distortion correction, tag/camera/aircraft pose, strict versioned imports, freshness/ambiguity/outlier guards, conservative full-cage 3D routes through observed free space, independent navigation worker, browser/native guidance, session recording and deterministic replay. Registered stationary D435 captures rebuild reproducibly. Automatic waypoint movement uses estimated synthetic vision and a mock plant; computer physical authority remains yaw-only, with the pilot retaining roll/pitch/throttle/ARM-DISARM and takeover. Real Pi/D435 capture, calibration/survey and aircraft output acceptance remain pending.

```sh
cd software
python -m pip install -r requirements.lock
python -m ball_demo.cli nav-replay examples/navigation/synthetic-session.json --output runs/navigation-replay.json
python -m ball_demo.cli nav-demo examples/navigation/synthetic-session.json --output runs/navigation-demo.json
python -m ball_demo.cli serve --nav-replay examples/navigation/synthetic-session.json
```

Use Python **>=3.13**. Open `http://127.0.0.1:8080/` and inspect the exported demo using the browser-local replay picker. Default bridge/yaw startup remains mock/MANUAL/disabled. [Complete navigation/D435 runbook](docs/23-navigation-software.md) · [Schemas/examples](software/examples/navigation/) · [Verification/evidence](evidence/navigation/README.md).

## Run the simulator

From the repository root, install the simulator dependencies and launch the local server:

```sh
python -m pip install -r requirements.txt
python server.py --no-browser
```

Open `http://127.0.0.1:8765/`. Running `python server.py` opens a browser automatically. `python desktop.py` launches the optional desktop wrapper. The simulator uses port 8765; the separate tracking/demo app uses port 8080.

### Simulator controls

| Key | Action |
| --- | --- |
| W / S | Forward / back |
| A / D | Yaw left / right |
| Q / E | Strafe left / right |
| Space / Shift | Climb / descend; hold Shift on the floor to land |
| P | Toggle motor power |
| V | Swap FPV inset and chase view |
| C | Cycle chase, FPV and orbit cameras |
| B | Cycle the simulator's 450, 550, 650 and 850 mAh battery models |
| L | Toggle simulated inspection lights |
| 1 / 2 / 3 | Industrial, rescue and physics-test maps |
| T | Toggle physics vectors |
| G | Toggle post-processing |
| N | Toggle minimap |
| I | Toggle telemetry panel |
| H | Toggle help; M mutes audio |
| R | Reset; Esc pauses; F11 toggles fullscreen |

### Simulator maps

| Map | Virtual environment |
| --- | --- |
| Industrial plant | Production bay with pallet racks, CNC machines, a conveyor, pipes and a leak marker |
| Rescue site | Collapsed-building scene with rubble, voids and rescue markers |
| Physics test bay | Ramp, wall, pipe, pole and crawl gap for trying the simulated contact behavior |

The simulator tests can be run with `node --import ./tools/test/register.mjs tools/test/physics_test.mjs` when Node and the repository's required modules are available.

Models under `static/assets/` and the scripts in `tools/blender/` are game visuals. They are not the current project's manufacturing CAD or proof of component fit.

## Simulator scope and geometry

The simulator is an application visualizer, not a model of the current physical build. The code describes an earlier Meteor85-class aircraft with a stated 87.7 mm wheelbase. Current parameters in [`static/js/spec.js`](static/js/spec.js) set a 112.5 mm cage circumradius, 5 mm hub radius (about 235 mm across the hub contact envelope), and 50.8 mm prop diameter (2 inches). These values do not represent the Apex-2 frame or the planned 245–250 mm cage. The physical and simulation prop sizes happen to match.

Battery options, masses, thrust, hover time, contact response, and telemetry shown by the simulator are model inputs or calculated outputs. They are not measurements of the physical aircraft. Its battery menu uses simulated 450/550/650/850 mAh packs; it does not include the user's two 1100 mAh packs. The graphics, collision handling and physics code are approximations and do not establish structural strength, prop clearance, endurance, or safe flight. See [simulation context and limitations](docs/06-simulation.md).

The `POST /api/telemetry` endpoint can feed data into the simulator HUD, but the endpoint does not create a physical radio or sensor connection. `python tools/telemetry_sim.py` sends synthetic test input. Do not present its values as live aircraft telemetry.

## Project references

- [Project documentation index](docs/README.md)
- [Build and verification gates](docs/10-build-and-test.md)
- [Current hardware and battery checks](docs/05-hardware.md)
- [CAD requirements](docs/03-cad.md)
- [CAD comparison research and 1 mm rod analysis](docs/19-cad-reference-research.md)
- [User-designated upstream CAD reference: Thingiverse 408519](cad/references/thingiverse-408519/README.md)
- [Software setup](software/README.md)
- [Demo runbook](docs/12-demo-runbook.md)
- [Recorded evidence and its limitations](evidence/README.md)

## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [HackPHS 2026 Google Doc](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit) — Planning source; user decisions and current tab revision are recorded in `docs/decisions.md` and `docs/sources/google-doc-2026-10-07/`.
- [WasimVorvoi/HackPHS](https://github.com/WasimVorvoi/HackPHS) — Existing simulator source.
- [Simulator parameters](static/js/spec.js) and [contact/flight model](static/js/drone.js) — Code values only; not physical validation.
- [OVONIC 2S 1100 mAh 60C XT30 two-pack listing](https://us.ovonicshop.com/products/2-ovonic-rebel-2-0-60c-2s-1100mah-lipo-battery-lihv-7-6v-pack-with-xt30-plug-for-size-100mm-to-140mm-brushless-drones-long-range-drone-fpv) — Vendor product reference; internally inconsistent specification fields require physical checks.
- [Apex-2 frame seller listing](https://speedyfpv.com/products/apex-2-2-inch-95mm-carbon-fiber-drone-frame-kit?variant=46334350164182) — Seller recommendation and frame specifications.
- [Thingiverse 408519](https://www.thingiverse.com/thing:408519) — The only user-designated upstream CAD reference; other designs in the research doc are comparison-only.
