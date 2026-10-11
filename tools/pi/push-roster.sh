#!/usr/bin/env bash
# Copy the laptop AprilTag roster (made with `ball-demo tags wizard`) to the Pi and reload it live.
#   tools/pi/push-roster.sh [roster.json] [user@pi]
set -euo pipefail
roster=${1:-${BALL_ROSTER_FILE:-$HOME/.config/ball-drone/roster.json}}
pi=${2:-hackphs@172.16.240.48}
[ -f "$roster" ] || { echo "No roster at $roster - run: ball-demo tags wizard" >&2; exit 1; }
scp -q "$roster" "$pi:/tmp/roster.json"
ssh "$pi" 'sudo install -o ball-demo -g ball-demo -m 640 /tmp/roster.json /var/lib/ball-drone/roster.json && rm /tmp/roster.json
token=$(sudo sed -n "s/^BALL_OPERATOR_TOKEN=//p" /etc/ball-drone/operator.env)
if curl -sf -X POST -H "Authorization: Bearer $token" http://127.0.0.1:8080/api/operator/roster/reload >/dev/null; then
  echo "Roster installed and reloaded on the Pi."
else
  echo "Roster installed; the running service did not reload it (restart: drone-mode <mode>)."
fi'
