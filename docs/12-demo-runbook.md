# Demo runbook — assisted route and manual fallback

Updated 2026-10-10. The accepted physical fallback is **manual flight/contact plus live target tracking**. The user-selected flight-bridge board is the Freenove ESP32-S3 WROOM; prefer physical yaw assistance only after the complete ESP32-S3-to-radio path, override and signal-loss/failsafe gates are verified.

## Choose the route before rehearsal

| Condition | Presentation |
| --- | --- |
| Physical bridge, override and failsafes fully verified | Assisted route; manual fallback remains ready |
| Physical steering unverified or unreliable | Manual-contact/live-tracking route; explicitly state steering is unavailable |
| Physical flight or live video unavailable | Saved footage/software/game presentation; disclose the limitation. This does not establish the physical fallback's success. |

Never select a route by a mock ACK, source-code test count or simulated behavior.

## Required manual-fallback screen

Show actual **live FPV video**, a **colored-target bounding box**, a **center/error indicator**, and the status:

> Manual steering — computer steering unavailable

Simulation footage is separate from live FPV. Synthetic yaw, virtual motion and mock bridge state must not appear as aircraft telemetry.

**Where it is (2026-10-08):** open `http://<pi-or-mac>:8080/fallback` on the presentation screen. It is read-only, so it is safe for a visitor display. The native app has the same view under **View → Manual fallback view** (Ctrl+Shift+F). Non-camera input is labelled "not live FPV". Stalled video shows *Video stale*. Confirm the full screen with the real RC832 capture before judging. The one-page [judge script](24-judge-script.md) gives roles, timing, failure branches and the three-run record.

## Physical manual-contact/live-tracking sequence

1. Explain the protective cage and that the pilot controls the aircraft.
2. Confirm manual ARM/DISARM and takeover; take off manually.
3. Make a deliberate low-energy foam/cardboard contact and recover.
4. Move the colored target while showing the live tracking box and center/error.
5. Explain that computer steering is unavailable; pilot remains responsible for all flight commands.
6. Land manually.
7. Show measured evidence, then the separate industrial application game.

No fixed cage is built (P1A CAD-only, 2026-10-08). If the gimbal misbehaves, zip-tie the rings to the cage and fly it as a fixed cage. This fallback is untested until tried during the first hovers.

## Preferred assisted sequence

Use only after [physical assistance acceptance](10-build-and-test.md#physical-assistance-gate):

1. Manual takeoff → controlled contact → recovery.
2. Deliberately enable yaw assistance.
3. Show real target centering and bounded commands.
4. Pilot uses the physical override.
5. Deliberately re-enable.
6. Cover target; computer commands return neutral.
7. Pilot lands.

If steering, capture or any failsafe becomes unverified, return to the rehearsed manual route. Do not automatically re-enable after recovery.

## Mac software startup

The existing software can rehearse synthetic/recorded behavior independently of aircraft output.

```sh
cd /Users/devk/Documents/HackPHS26/software
.venv/bin/python -m ball_demo.cli serve
```

Open `http://127.0.0.1:8080/`. Startup is synthetic, mock, MANUAL, disabled and requested yaw zero. Read the private `runs/operator-token` locally for operator controls; keep it out of visitor links/screenshots. A synthetic run is a software demonstration.

For source native operation, use [desktop instructions](14-desktop-app.md). The installed `/Users/devk/Applications/Ball Drone.app` can be stale relative to source; verify/rebuild before presenting its behavior.

Find the capture device with `ball-demo cameras`, then start on it: `.venv/bin/python -m ball_demo.cli serve --camera /dev/video0` (an index such as `0` on the Mac). Startup stays MANUAL and disabled. Click **Pick target colour from video** and then the target to set the detector colours. `ball-demo latency --camera /dev/video0 --trigger screen` measures flash-to-detection latency. The checked-in Mega serial sketch is historical and has no trainer output; current host/firmware integration for the selected ESP32-S3 board is not implemented or verified. Do not use `--serial` as physical assistance until that port and all trainer gates are verified.

If assistance is enabled from a browser or native window, keep that window open. Closing it or losing the network stops the heartbeats; after 1.5 s the server falls to neutral with *operator connection lost*.

The game source is under `simulation/` on this machine (at the repository root in the published GitHub checkout). Install its `requirements.txt` in a dedicated environment (the software venv also works), then:

```sh
cd /Users/devk/Documents/HackPHS26/simulation
python server.py --no-browser
```

Open `http://127.0.0.1:8765/`; choose the industrial map. The game is illustrative, with its documented geometry mismatch.

## Actual Pi installation and network checks

Use **64-bit Raspberry Pi OS based on Trixie** (Python 3.13) on a Pi 4 or Pi 5. Bookworm's Python 3.11 cannot install the locked numpy/OpenCV, and 32-bit images have no wheels. The installer runs a preflight first and stops before changing anything if the board, OS, architecture or Python is unsuitable:

```sh
bash software/deploy/pi-preflight.sh      # optional on its own
bash software/deploy/install-pi.sh
```

On the real board, run `bash software/deploy/pi-acceptance.sh` after installing. It checks the preflight, service, groups, health, fallback page, a 30 s processing rate against 20 Hz, CPU temperature and throttling, and video/serial devices, and writes a report to save under `evidence/physical/`. The installer adds the service account to the `video` and `dialout` groups (capture adapter and serial bridge). The service cannot read home directories, so put recordings in `/var/lib/ball-drone/recordings`. Checked 2026-10-08 in ARM64 containers: [Trixie install passes](../evidence/pi-install-2026-10-08/trixie-arm64-container.txt), [Bookworm is refused](../evidence/pi-install-2026-10-08/bookworm-arm64-container.txt). That is not a real Pi; capture, thermals and performance still need the board.

Prepared paths: `/opt/ball-drone/software`, runtime `/var/lib/ball-drone`, service `ball-demo.service`, private environment `/etc/ball-drone/operator.env`. Check service logs and `http://127.0.0.1:8080/api/health`; confirm synthetic/mock/MANUAL/disabled startup before devices are added. [Previous detailed deployment instructions](sources/local-docs-before-rework-2026-10-07/12-demo-runbook.md) preserve the original setup steps.

From the Pi console, use an actual saved NetworkManager profile:

```sh
sudo bash software/deploy/network.sh shared '<saved-profile-name>'
bash software/deploy/network.sh status
```

Or switch locally to the prepared hotspot:

```sh
sudo bash software/deploy/network.sh hotspot
bash software/deploy/network.sh status
```

The hotspot is `BallDrone-Demo`; switching the single Wi-Fi adapter can disconnect SSH. Visitors use the actual active Pi IP with port 8080, or reachable hostname/mDNS on a shared network. Generate a card with:

```sh
bash software/deploy/connection-card.sh ./visitor-card          # add a port if the server is not on 8080
```

Verify peer access, disconnect/reconnect, five real clients and RF coexistence. Monitoring Wi-Fi must not enter the local vision/control path. Camera and serial device access require deliberate actual-device configuration.

## Reliability rehearsal

| Check | Required observation |
| --- | --- |
| Target disappears | Direct neutral for assisted operation; live screen truthfully shows loss |
| Capture stops/freezes | Assistance disabled; stale information visibly cleared |
| Serial/radio/control signal loss | Verified physical failsafe/neutral behavior |
| Operator override | Pilot takes authority independently of vision |
| App restarts | MANUAL, disabled; no automatic assistance |
| Visitor disconnects | Reconnect is read-only and does not enable steering |
| Simulator fails | Physical/manual presentation remains independent |

For software-only rehearsals, use loss/freeze scenarios and mock disconnect/recovery, labeling them synthetic/mock. They do not pass physical tests.

## Freeze and final preparation

Stop new hardware/features **48 hours before the first judged demo**. Final **24 hours**: reliability tests, batteries, evidence/screenshots/logs and **at least three consecutive complete rehearsals**. Only fixes restoring working core functionality are allowed.

Prepare manual and conditional assisted scripts, spare/charged packs, known-good capture/power cables, local game assets and measured evidence. Additional purchases stay within $200, with at least $30 reserved for rework. Pico audio/`toImplement` remains deferred.

[Build and test](10-build-and-test.md) · [Hardware worksheet](13-hardware-arrival.md) · [Evidence](07-refs.md).


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [HackPHS 2026 Google Doc](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit) — Follow-up user decisions set the manual fallback and conditional assisted route.
- [Software launch guide](../software/README.md) — Current source command and startup behavior.
- [Build/test acceptance](10-build-and-test.md) — Physical and rehearsal gates.
