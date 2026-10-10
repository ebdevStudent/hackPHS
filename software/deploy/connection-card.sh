#!/usr/bin/env bash
set -euo pipefail
device=${BALL_WIFI_DEVICE:-wlan0}
active_ip=$(nmcli -g IP4.ADDRESS device show "$device" | head -n 1 | cut -d/ -f1)
active_network=$(nmcli -g GENERAL.CONNECTION device show "$device")
[[ -n "$active_ip" ]] || { echo 'No active IPv4 address on the selected adapter'; exit 1; }
python_bin=${BALL_PYTHON:-/opt/ball-drone/software/.venv/bin/python}
output_dir=${1:-./connection-card}
# Use the port of the server visitors should see; a desktop session may run on 8081-8089.
port=${2:-${BALL_PORT:-8080}}
[[ $port =~ ^[0-9]+$ ]] || { echo 'Port must be a number'; exit 1; }
"$python_bin" -m ball_demo.cli connection-card --url "http://$active_ip:$port/" --network "$active_network" --output "$output_dir"
