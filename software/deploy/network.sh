#!/usr/bin/env bash
# Run locally on the Pi console: switching the single Wi-Fi adapter may disconnect SSH.
set -euo pipefail
profile=${1:-status}
device=${BALL_WIFI_DEVICE:-wlan0}
case "$profile" in
  hotspot)
    if ! nmcli -g NAME connection show | grep -Fxq BallDrone-Demo; then
      read -rsp 'Hotspot password (8+ characters): ' ap_password; echo
      [[ ${#ap_password} -ge 8 ]] || { echo 'Password too short'; exit 1; }
      nmcli device wifi hotspot ifname "$device" con-name BallDrone-Demo ssid BallDrone-Demo password "$ap_password"
      nmcli connection modify BallDrone-Demo connection.autoconnect no
    else
      nmcli connection up BallDrone-Demo
    fi
    ;;
  shared)
    shared_name=${2:?Pass the existing shared-network connection name}
    if nmcli -g GENERAL.STATE connection show BallDrone-Demo 2>/dev/null | grep -q activated; then
      nmcli connection down BallDrone-Demo
    fi
    nmcli connection up "$shared_name" ifname "$device"
    ;;
  status) nmcli device status; nmcli -g IP4.ADDRESS device show "$device" ;;
  *) echo 'Usage: network.sh hotspot | shared <saved-profile-name> | status'; exit 1 ;;
esac
echo 'Use the active IP above; do not assume the hotspot address.'
nmcli -g IP4.ADDRESS device show "$device"
