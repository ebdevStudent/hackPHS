#!/usr/bin/env bash
set -euo pipefail
software_root=$(cd "$(dirname "$0")/.." && pwd)
bash "$software_root/deploy/pi-preflight.sh"
sudo apt-get update
sudo apt-get install -y python3 python3-venv libglib2.0-0 libgl1 libegl1 libdbus-1-3 libfontconfig1 libxkbcommon0 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-shape0 libxcb-xinerama0
python3 -c 'import sys; assert sys.version_info >= (3, 13), "Python 3.13+ required (Raspberry Pi OS Trixie)"'
python3 -m venv "$software_root/.venv-desktop"
"$software_root/.venv-desktop/bin/pip" install -r "$software_root/requirements-desktop.lock"
"$software_root/.venv-desktop/bin/pip" install --no-deps "$software_root"
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/ball-drone.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Ball Drone
Comment=Native tracking and yaw demonstration
Exec="$software_root/.venv-desktop/bin/ball-desktop"
Path=$software_root
Icon=$software_root/ball_demo/static/desktop-icon.png
Terminal=false
Categories=Education;Science;
EOF
printf '%s\n' 'Ball Drone added to the application menu. A graphical desktop/display is required.' 'For a Pi running the existing headless service, use ball-desktop --connect http://127.0.0.1:8080 --token-file <private-token-file>.'
