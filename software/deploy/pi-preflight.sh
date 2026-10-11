#!/usr/bin/env bash
# Check that this Raspberry Pi can run the Ball Drone software before installing anything.
# Supported: Raspberry Pi 4 or 5 with 64-bit Raspberry Pi OS "Trixie" (Debian 13, Python 3.13).
# Bookworm (Python 3.11) cannot install the locked numpy/OpenCV wheels. Exit 1 on any FAIL.
# BALL_PREFLIGHT_ROOT / _ARCH / _PYTHON override the inspected system for tests only.
set -uo pipefail
root=${BALL_PREFLIGHT_ROOT:-}
arch=${BALL_PREFLIGHT_ARCH:-$(uname -m)}
python_version=${BALL_PREFLIGHT_PYTHON:-$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo none)}
failures=0
pass() { echo "PASS  $*"; }
warn() { echo "WARN  $*"; }
fail() { echo "FAIL  $*"; failures=$((failures + 1)); }

model=$(tr -d '\0' < "$root/proc/device-tree/model" 2>/dev/null || echo unknown)
case "$model" in
  *"Raspberry Pi 5"*) pass "Board: $model (active cooler recommended for sustained vision load)" ;;
  *"Raspberry Pi 4"*) pass "Board: $model (fit a heatsink; measure frame rate under load, the Pi 4 is slower than the Pi 5)" ;;
  unknown) warn "Board model not readable; this does not look like a Raspberry Pi" ;;
  *) warn "Board: $model is not a Pi 4/5; the software is untested here" ;;
esac

if [[ $arch == aarch64 ]]; then pass "64-bit ARM ($arch)"
else fail "Architecture $arch: install the 64-bit Raspberry Pi OS image (32-bit has no OpenCV/numpy wheels)"; fi

codename=$( (. "$root/etc/os-release" 2>/dev/null && echo "${VERSION_CODENAME:-unknown}") || echo unknown)
case "$codename" in
  trixie) pass "OS: Debian/Raspberry Pi OS trixie" ;;
  bookworm) fail "OS: bookworm ships Python 3.11; reflash with Raspberry Pi OS (64-bit) based on Trixie" ;;
  *) warn "OS codename '$codename' is untested; Trixie is the supported release" ;;
esac

major=${python_version%%.*}; minor=${python_version#*.}
if [[ $python_version == none && $codename == trixie ]]; then warn "python3 not installed yet; the installer adds Trixie's Python 3.13"
elif [[ $python_version != none && $major -eq 3 && $minor -ge 13 ]]; then pass "Python $python_version"
else fail "Python $python_version: 3.13 or newer is required by the locked dependencies"; fi

memory_kb=$(awk '/MemTotal/ {print $2}' "$root/proc/meminfo" 2>/dev/null || echo 0)
if (( memory_kb >= 1800000 )); then pass "Memory $((memory_kb / 1024)) MB"
elif (( memory_kb > 0 )); then warn "Memory $((memory_kb / 1024)) MB: 2 GB or more recommended for capture, vision and the server"
else warn "Memory size not readable"; fi

shopt -s nullglob
cameras=("$root"/dev/video*)
serials=("$root"/dev/ttyACM* "$root"/dev/ttyUSB*)
if (( ${#cameras[@]} )); then pass "Video devices: ${cameras[*]#$root}"; else warn "No /dev/video* yet: plug in the USB capture adapter, then run 'ball-demo cameras'"; fi
if (( ${#serials[@]} )); then pass "Serial devices: ${serials[*]#$root}"; else warn "No /dev/ttyACM*/ttyUSB* yet: the ESP32-S3 bridge (USB/UART port) appears as /dev/ttyACM0 when connected"; fi

if (( failures )); then echo "Preflight failed with $failures problem(s); nothing was installed."; exit 1; fi
echo "Preflight passed."
