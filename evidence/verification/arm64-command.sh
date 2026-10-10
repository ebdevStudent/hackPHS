#!/usr/bin/env bash
set -euo pipefail
# Same mounts used for the recorded ARM64 run; choose a fresh evidence name.
project_root=$(cd "$(dirname "$0")/../.." && pwd)
run_name=${1:-linux-arm64-$(date -u +%Y%m%dT%H%M%SZ)}
docker_context=${BALL_DOCKER_CONTEXT:-colima-ball-drone}
docker --context "$docker_context" run --rm --platform linux/arm64 \
  -v "$project_root/software/ball_demo:/work/software/ball_demo:ro" \
  -v "$project_root/software/tests:/work/software/tests:ro" \
  -v "$project_root/software/pyproject.toml:/work/software/pyproject.toml:ro" \
  -v "$project_root/software/requirements.lock:/work/software/requirements.lock:ro" \
  -v "$project_root/software/requirements-dev.lock:/work/software/requirements-dev.lock:ro" \
  -v "$project_root/software/requirements-desktop.lock:/work/software/requirements-desktop.lock:ro" \
  -v "$project_root/firmware:/work/firmware:ro" \
  -v "$project_root/tools:/work/tools:ro" \
  -v "$project_root/evidence/verification:/evidence" \
  ball-drone-verification:arm64 python /work/tools/verify.py --output "/evidence/$run_name"
