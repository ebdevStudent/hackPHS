#!/usr/bin/env bash
set -euo pipefail
project_root=$(cd "$(dirname "$0")/.." && pwd)
# Pi 4 or Pi 5 with 64-bit Raspberry Pi OS Trixie; stops before changing anything otherwise.
bash "$project_root/deploy/pi-preflight.sh"
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip libglib2.0-0 libgl1 network-manager
python3 -c 'import sys; assert sys.version_info >= (3, 13), "Python 3.13+ required (Raspberry Pi OS Trixie)"'
sudo useradd --system --create-home --home-dir /var/lib/ball-drone ball-demo 2>/dev/null || id ball-demo
# Camera (/dev/video*) and ESP32-S3 bridge serial (/dev/ttyACM*) access for the service account.
sudo usermod -a -G video,dialout ball-demo
# The service cannot read home directories (ProtectHome); put recordings here instead.
sudo mkdir -p /opt/ball-drone/software /etc/ball-drone /var/lib/ball-drone/recordings
sudo cp -R "$project_root/ball_demo" "$project_root/pyproject.toml" "$project_root/requirements.lock" /opt/ball-drone/software/
sudo python3 -m venv /opt/ball-drone/software/.venv
sudo /opt/ball-drone/software/.venv/bin/pip install -r /opt/ball-drone/software/requirements.lock
sudo /opt/ball-drone/software/.venv/bin/pip install --no-deps /opt/ball-drone/software
if ! sudo test -f /etc/ball-drone/operator.env; then
  sudo /opt/ball-drone/software/.venv/bin/python - <<'PY'
import os, secrets
fd = os.open('/etc/ball-drone/operator.env', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as f: f.write('BALL_OPERATOR_TOKEN=' + secrets.token_urlsafe(24) + '\n')
PY
fi
sudo chown -R ball-demo:ball-demo /var/lib/ball-drone
sudo cp "$project_root/deploy/ball-demo.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ball-demo
echo 'Check: systemctl status ball-demo; curl http://127.0.0.1:8080/api/health'
echo 'Visitor URL: http://<active-Pi-IP>:8080/ or http://<actual-hostname>.local:8080/'
echo 'Recordings for the service: /var/lib/ball-drone/recordings (home directories are not readable by it).'
