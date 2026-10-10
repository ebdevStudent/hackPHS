#!/usr/bin/env bash
# Run the real headless installer inside a Debian/Raspberry Pi OS userland container (ARM64).
# Usage: tools/pi_container_check.sh [debian:trixie-slim] [output-file]
# Containers have no systemd: systemctl is stubbed and the service command is started by hand.
# This checks installer steps, packages, groups and startup; it is not Pi hardware, camera or thermal evidence.
set -euo pipefail
image=${1:-debian:trixie-slim}
output=${2:-/dev/stdout}
root=$(cd "$(dirname "$0")/.." && pwd)
docker run --rm --platform linux/arm64 -v "$root/software":/src:ro "$image" bash -c '
set -euo pipefail
apt-get update -qq >/dev/null && apt-get install -y -qq sudo curl >/dev/null
printf "#!/bin/sh\necho \"systemctl \$*\" >> /tmp/systemctl.log\n" > /usr/local/bin/systemctl && chmod +x /usr/local/bin/systemctl
cp -R /src /tmp/software && rm -rf /tmp/software/.venv /tmp/software/.venv-desktop /tmp/software/runs /tmp/software/build
echo "== installer"
bash /tmp/software/deploy/install-pi.sh 2>&1 | grep -E "PASS|WARN|FAIL|Preflight|Check:|Recordings" || true
echo "== stubbed systemctl calls"; cat /tmp/systemctl.log
echo "== service account groups"; id ball-demo
echo "== service files"; ls -l /etc/systemd/system/ball-demo.service /etc/ball-drone/operator.env; stat -c "%a %U" /etc/ball-drone/operator.env
grep -E "SupplementaryGroups|ExecStart" /etc/systemd/system/ball-demo.service
echo "== start service command as ball-demo"
set -a; . /etc/ball-drone/operator.env; set +a
cd /opt/ball-drone/software
sudo -u ball-demo env BALL_DATA_DIR=/var/lib/ball-drone BALL_OPERATOR_TOKEN="$BALL_OPERATOR_TOKEN" \
  /opt/ball-drone/software/.venv/bin/python -m ball_demo.cli serve --host 0.0.0.0 --port 8080 >/tmp/serve.log 2>&1 &
for i in $(seq 1 100); do curl -sf http://127.0.0.1:8080/api/health >/tmp/health.json && break; sleep .2; done
cat /tmp/health.json; echo
python3 - <<PY
import json; h = json.load(open("/tmp/health.json"))
assert h["ok"] is True and h["state"] == "MANUAL" and h["physical_output"] is False, h
print("health ok, MANUAL, no physical output")
PY
curl -sf http://127.0.0.1:8080/fallback | grep -o "Manual steering — computer steering unavailable"
sudo -u ball-demo /opt/ball-drone/software/.venv/bin/python -m ball_demo.cli cameras --max-index 1
echo "PI CONTAINER CHECK PASSED"
' 2>&1 | tee "$output"
