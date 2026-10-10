# Simulation

Source: Google Doc **Simulation** tab, read 2026-10-04. [Preserved tab text](../google-doc-2026-10-04/06-simulation.md). Current user decisions are recorded in [decisions.md](decisions.md).

## Mac deployment

The user will run the simulation on their Mac. The Raspberry Pi 5 runs tracking/control and hosts the separate demo server/browser interface for connected devices; its deployment is covered in [Software](04-software.md#demo-deployment).

## Existing repository

The existing [simulation repository](https://github.com/WasimVorvoi/HackPHS#wasims-existing-ball-drone-flight-sim) lives in `simulation/`. It was cloned from [WasimVorvoi/HackPHS](https://github.com/WasimVorvoi/HackPHS) on branch `main` at commit `f472e4fcf0ed1e19141bcfb42f1afa4ac302e7e3`.

The source includes a Three.js frontend, industrial and rescue maps, custom collision handling, camera target detection, HUD, mission scoring, a FastAPI backend, telemetry endpoints, and a PyWebView desktop wrapper. A short playable smoke now confirms both maps, movement/camera inputs and pause/resume without browser errors; see [Mac evidence](../../../evidence/simulation-smoke.json). It does not establish complete mission playthroughs or physical model accuracy.

Run instructions are in the simulation README: install `requirements.txt`, then run `python server.py` from `simulation/` for the browser version at `http://127.0.0.1:8765`. `python desktop.py` is the desktop alternative. The browser server was launched on the Mac using the software environment's FastAPI/uvicorn. The desktop wrapper was not tested. From the project root: `software/.venv/bin/python simulation/server.py --no-browser`.

The simulation README describes a roughly 372 mm cage and 4-inch propellers. The physical build plan uses a roughly 220–230 mm cage and 2-inch propellers. Treat the virtual geometry as presentation geometry until explicitly reconciled with measured hardware.

Use the simulation for presentation and a hardware fallback. Future enhancements should follow the physical core's priorities. The imported repository retains its own Git metadata and remote; manage its changes within `simulation/`.

## Intended demonstration

The source tab describes industrial inspection and search-and-rescue scenarios, contact/bounce/slide/roll behavior, FPV and chase cameras, target detection, objectives, timer, score, and battery display. The imported repository includes both maps; prioritize reliability before adding more presentation scope.

Use the physical demo to establish mechanical behavior and the simulation to illustrate applications or provide a presentation fallback. Any future real-to-virtual link should initially mirror only MANUAL/AUTO, target captured, and mission complete. It remains a P4 upgrade.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Pre-rewrite archive index](README.md) — identifies this file as historical context, not current instruction.
- [Maintained document](../../06-simulation.md) — current requirements and status.
- This citation note is external to the preserved pre-rewrite text.
