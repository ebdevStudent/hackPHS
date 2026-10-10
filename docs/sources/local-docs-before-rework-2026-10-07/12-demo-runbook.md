# Software demo startup, presentation and recovery

Scope: the live demo runs synthetic/recorded vision and yaw decisions. No radio output or measured aircraft telemetry. Pi deployment files are prepared; an actual Pi, hotspot and USB devices still need verification.

## Mac startup

For native operation, open `/Users/devk/Applications/Ball Drone.app`; see the [desktop guide](14-desktop-app.md). It owns a separate local mock server unless started in remote-connection mode. For a headless Pi, connect the Mac workstation to the existing Pi server. The following CLI instructions still apply to browser/headless operation.

1. Open Terminal in `/Users/devk/Documents/HackPHS26/software`.
2. Create/install the Python environment using [software README](../../../software/README.md). Dependencies are pinned in `requirements.lock` and `requirements-dev.lock` from the verified Python 3.13 environment.
3. Run `.venv/bin/python -m ball_demo.cli serve`.
4. Open `http://127.0.0.1:8080/`. Confirm **SYNTHETIC**, **MANUAL**, yaw **0**, fresh frames/ACKs and **MOCK**.
5. Read `runs/operator-token` locally; enter it in Operator access. Keep it separate from visitor instructions.
6. Enable assistance; observe three detections before LOCKED. Visitors only need the ordinary URL.
7. In another terminal from the project root run `software/.venv/bin/python simulation/server.py --no-browser`. Open `http://127.0.0.1:8765/` on the Mac and choose either map. Simulation controls and scope remain in [Simulation](06-simulation.md).
8. To offer Mac-hosted rehearsal access on a shared network, start the demo with `--host 0.0.0.0` and use the Mac's actual LAN address plus `:8080`. This does not move the simulation to the Pi.

## Short demonstration script

1. **Explain the split:** “The Mac runs the 3D simulation. The Pi will run tracking and this demo server. This screen currently uses synthetic video and a mock command bridge.”
2. **Acquire:** moving target, enable, observe SEARCHING → LOCKED, bounded yaw and normalized center error.
3. **Lose the target:** choose `loss`, re-enable, watch SEARCHING and zero yaw on the first processed missing-target frame.
4. **Stale source:** choose `freeze`, re-enable; after the freshness deadline show FAULT and zero yaw. Host timestamp is intentionally frozen by this fixture.
5. **Disconnect bridge:** reset, enable, expand Bridge fault demonstration and apply disconnect; show missing-ACK FAULT. Recover mock bridge; assistance remains disabled until you choose enable again.
6. **Visitor exploration:** a phone opens the Sandbox tab, selects a scene and plays/resets its own trace. Shared source/settings/bridge remain untouched.
7. **Close with evidence:** session CSV/events/summary, [test report](../../../evidence/README.md), and [walkthrough recording](../../../evidence/walkthrough.webm). Do not call synthetic response-model centering aircraft performance.

## Pi installation profile (prepared, hardware execution pending)

Target **Raspberry Pi 5, 64-bit Raspberry Pi OS Trixie, Python ≥3.13**. Older Python versions do not meet the locked dependency profile. The measured ARM64 container uses Python 3.13 and checks software compatibility only.

1. Install the OS and set a known hostname (for example `ball-drone`), locale/regulatory country, admin user, and shared Wi-Fi credentials using Raspberry Pi Imager. Record the actual hostname.
2. Copy this project to the Pi (the simulation can remain on the Mac; it is not a demo-server dependency).
3. From the copied project run `bash software/deploy/install-pi.sh`. This installs the environment under `/opt/ball-drone/software`, runtime data under `/var/lib/ball-drone`, a dedicated service user and `ball-demo.service`.
4. Check `systemctl status ball-demo`, `journalctl -u ball-demo`, and `curl http://127.0.0.1:8080/api/health`. Confirm fresh synthetic input, MANUAL, zero yaw, mock output, a new session after each restart.
5. Operator environment is `/etc/ball-drone/operator.env` (root-only mode 0600). The service also saves its active token in `/var/lib/ball-drone/operator-token`. Retrieve locally with appropriate permissions; do not put either in visitor cards.
6. Actual camera/Pico access will require deliberate service permission/group changes after devices are identified. The installed service deliberately starts without a physical device argument.

### Shared network

Use an existing NetworkManager profile on the Pi. If none exists, create one locally using `sudo nmcli --ask device wifi connect '<SSID>'`. Password entry remains private.

```sh
sudo bash software/deploy/network.sh shared '<saved-profile-name>'
bash software/deploy/network.sh status
```

Visitor URL: `http://<actual-hostname>.local:8080/`; if name discovery or network peer access fails, use `http://<active-Pi-IP>:8080/`. Some shared networks block device-to-device traffic; use the hotspot profile if needed.

### Pi-hosted hotspot

Run from the Pi console because switching the single Wi-Fi adapter can disconnect SSH. The script creates **BallDrone-Demo**, prompts for its separate Wi-Fi password and activates the profile. No simultaneous client Wi-Fi connection is assumed.

```sh
sudo bash software/deploy/network.sh hotspot
bash software/deploy/network.sh status
```

Visitors join `BallDrone-Demo` and open the Pi's **actual active IP** on port 8080. Internet access is unnecessary once dependencies are installed. The script does not change the Mac's Wi-Fi or start a hotspot here.

### Connection cards

On the Pi, `bash software/deploy/connection-card.sh ./visitor-card` reads the active NetworkManager address/profile and generates the visitor URL, QR PNG and connection text. Set `BALL_WIFI_DEVICE` if the adapter differs from `wlan0`. Share the Wi-Fi password separately if needed. These cards contain no operator token.

The [NetworkManager approach follows official Raspberry Pi networking guidance](https://www.raspberrypi.com/documentation/computers/configuration.html#enable-hotspot). Actual AP/client switching, mDNS, regulatory settings and five physical visitors remain Pi hardware checks.

## Linux ARM64 smoke check

```sh
docker build --platform linux/arm64 -f software/deploy/Dockerfile -t ball-drone-demo:arm64 software
docker run --rm --platform linux/arm64 -v "$PWD/software/deploy/arm64_smoke.py:/check.py:ro" ball-drone-demo:arm64 python /check.py
```

The development Mac used a separate Colima ARM64 VM/container. This verifies package installation/imports, synthetic accuracy/bounds, startup/API and summary output. It does not test Raspberry Pi thermal behavior, camera backends, NetworkManager hotspot or USB electrical operation.

## Recovery checklist

| Problem | Recovery | Required observation |
| --- | --- | --- |
| Application stopped | Restart the command or `sudo systemctl restart ball-demo`. | New session, MANUAL, disabled, mock output. |
| Visitor stale/disconnected | Restore network/server, wait for automatic stream reconnect; reload if needed. | Fresh snapshot; reconnect did not enable assistance. |
| Frozen/stopped source | Disable; select a fresh synthetic or recorded source/reset. | Fresh frames before deliberate enable. |
| Camera cannot open | Select synthetic input; check OS permissions/device only after identifying it. | No invented camera or aircraft telemetry. |
| Serial device absent | Stop serial instance; restart without `--serial`. | MOCK badge, disabled state, new session. |
| Missing/delayed ACKs | Disable, resolve transport, restart/re-handshake if needed. | Fresh accepted replies; deliberate enable afterward. |
| Shared Wi-Fi blocks access | Switch Pi locally to hotspot, regenerate active-IP card. | Visitors reach `/api/health` and dashboard. |
| Live demo unreliable | Use generated recorded video and isolated sandbox; show saved walkthrough. | RECORDED/SYNTHETIC label stays visible. |

## Optional sample-recording guide

When a camera is available, record a green target centered, moving left/right, near the edges, approaching, then hidden and reappearing; repeat with dim lighting, a similar-colored distraction and blur. Keep recordings local under `software/runs/recordings/`, note camera/resolution/FPS/lighting, and provide the absolute path through the operator's recorded-source control. Recordings are not required for the hardware-free baseline. The current live camera adapter timestamps successful host reads; repeated identical images from a malfunctioning receiver require separate physical diagnosis.

## Handoff package

The [local archive](../../../evidence/ball-drone-software-0.1.0.zip) contains software, firmware, preserved source tabs, maintained docs, tools and selected evidence. It excludes environments/private runtime storage and the independent simulation clone. Use the existing simulation on the Mac. On another machine, clone that repository separately if you also need its presentation. The [wheel](../../../evidence/wheels/ball_drone_demo-0.1.0-py3-none-any.whl) installs after the locked runtime dependencies.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Pre-rewrite archive index](README.md) — identifies this file as historical context, not current instruction.
- [Maintained document](../../12-demo-runbook.md) — current requirements and status.
- This citation note is external to the preserved pre-rewrite text.
