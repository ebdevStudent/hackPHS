#!/usr/bin/env bash
# Commit and push any changes in the game repo every 10 minutes (skips quiet intervals).
# Run:  bash tools/autocommit.sh        Stop: Ctrl+C, or kill the process / remove tools/.autocommit.pid
cd "$(dirname "$0")/.." || exit 1
echo $$ > tools/.autocommit.pid
INTERVAL=${INTERVAL:-600}
while true; do
  if [ -n "$(git status --porcelain)" ]; then
    git add -A
    # Never publish credentials or runtime data, even if an ignore rule is missing.
    private=$(git diff --cached --name-only | grep -E '(^|/)(operator-token[^/]*|\.env[^/]*)$|(^|/)runs/' || true)
    if [ -n "$private" ]; then
      git reset -q
      echo "[$(date '+%H:%M')] skipped: private/runtime files staged: ${private}"
      sleep "$INTERVAL"; continue
    fi
    files=$(git diff --cached --name-only | head -8 | tr '\n' ' ')
    git commit -q -m "Auto-commit $(date '+%Y-%m-%d %H:%M'): ${files}" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" \
      && git push -q origin main 2>&1 | tail -2
    echo "[$(date '+%H:%M')] committed: ${files}"
  else
    echo "[$(date '+%H:%M')] no changes"
  fi
  sleep "$INTERVAL"
done
