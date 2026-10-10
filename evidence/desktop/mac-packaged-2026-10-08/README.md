# Rebuilt Mac app — 2026-10-08

`software/desktop/build-mac.py` rebuilt `/Users/devk/Applications/Ball Drone.app` from current source (manual-fallback overlays, operator lease heartbeats, live-video fix, colour picking, navigation). Strict deep ad hoc signature verification passed. An offscreen launch (`--listen 127.0.0.1 --port 8095 --quit-after 14`) served `/api/health` with both workers alive and `/fallback` with the steering status. It started MANUAL, disabled, lease 1500 ms, and saved its session summary on exit.

[Render](render.png) · [health](health.json) · [session summary](summary.json) · [build output tail](build-tail.txt) · [run log](run.txt) · [executable hash](executable-sha256.txt).

Local ad hoc signing only (no notarization or Intel build). Synthetic source, mock bridge, offscreen Qt; no camera, Pi or radio.
