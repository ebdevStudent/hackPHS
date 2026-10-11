#!/usr/bin/env bash
# Run on the Raspberry Pi after install-pi.sh. Records what containers cannot show: the board, the running
# service, device access, real processing rate and temperature. Writes a report for evidence/physical/.
# Usage: bash software/deploy/pi-acceptance.sh [report-file] [sample-seconds]
# BALL_URL / BALL_ROOT override the service address and the inspected filesystem (tests only).
set -uo pipefail
report=${1:-pi-acceptance-$(date +%Y%m%dT%H%M%S).txt}
seconds=${2:-30}
url=${BALL_URL:-http://127.0.0.1:8080}
root=${BALL_ROOT:-}
failures=0
exec > >(tee "$report") 2>&1
pass() { echo "PASS  $*"; }
warn() { echo "WARN  $*"; }
fail() { echo "FAIL  $*"; failures=$((failures + 1)); }

echo "Ball Drone Pi acceptance — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
bash "$(dirname "$0")/pi-preflight.sh" || fail "preflight"
if systemctl is-active --quiet ball-demo; then pass "ball-demo service active"; else fail "ball-demo service not active (systemctl status ball-demo)"; fi
groups_line=$(id ball-demo 2>/dev/null || true)
[[ $groups_line == *"(video)"* && $groups_line == *"(dialout)"* ]] && pass "service account has video and dialout" || fail "service account groups: ${groups_line:-missing}"

health=$(curl -sf "$url/api/health" || true)
if [[ -n $health ]] && python3 -c 'import json,sys; h=json.loads(sys.argv[1]); sys.exit(0 if h.get("ok") is True and h.get("state")=="MANUAL" and h.get("physical_output") is False else 1)' "$health"; then
  pass "health ok, MANUAL, no physical output"
else
  fail "health: ${health:-no answer from $url}"
fi
curl -sf "$url/fallback" | grep -q "Manual steering — computer steering unavailable" && pass "fallback screen served" || fail "fallback screen missing"

first=$(curl -sf "$url/api/state" || true); sleep "$seconds"; second=$(curl -sf "$url/api/state" || true)
if [[ -n $first && -n $second ]]; then
  rate=$(python3 -c 'import json,sys; a,b=json.loads(sys.argv[1]),json.loads(sys.argv[2]); print("%.1f" % ((b["frames"]-a["frames"])/float(sys.argv[3])))' "$first" "$second" "$seconds")
  python3 -c 'import sys; sys.exit(0 if float(sys.argv[1]) >= 18 else 1)' "$rate" && pass "processing ${rate} frames/s over ${seconds} s (target 20)" || warn "processing ${rate} frames/s over ${seconds} s is below the 20 Hz target"
  python3 -c 'import json,sys; s=json.loads(sys.argv[1]); print("      state", s["state"], "| source", s["source_label"], "| decision_ms", s.get("decision_ms"), "| processing_ms", s.get("processing_ms"))' "$second"
else
  fail "could not sample /api/state"
fi

if command -v vcgencmd >/dev/null; then
  temp=$(vcgencmd measure_temp | sed 's/[^0-9.]//g')
  python3 -c 'import sys; sys.exit(0 if float(sys.argv[1]) < 75 else 1)' "$temp" && pass "CPU ${temp} °C" || warn "CPU ${temp} °C: add cooling before long runs"
  throttled=$(vcgencmd get_throttled | cut -d= -f2)
  [[ $throttled == 0x0 ]] && pass "no under-voltage or throttling" || warn "get_throttled=$throttled (check the power supply and cooling)"
else
  warn "vcgencmd not found: temperature and throttling not recorded"
fi

shopt -s nullglob
cams=("$root"/dev/video*); serial=("$root"/dev/ttyACM* "$root"/dev/ttyUSB*)
(( ${#cams[@]} )) && pass "video devices: ${cams[*]#$root}" || warn "no /dev/video*: connect the capture adapter"
(( ${#serial[@]} )) && pass "serial devices: ${serial[*]#$root}" || warn "no /dev/ttyACM*: connect the ESP32-S3 USB/UART port if testing the bridge"

if (( failures )); then echo "Pi acceptance: $failures failure(s). Report: $report"; exit 1; fi
echo "Pi acceptance passed. Report: $report"
