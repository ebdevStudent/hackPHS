#!/usr/bin/env bash
# Make simulation/ (the WasimVorvoi/HackPHS git checkout) carry the current project from this folder.
# Usage: tools/sync_to_repo.sh            dry run: list what would change
#        tools/sync_to_repo.sh --apply    copy, then show `git status` (nothing is committed or pushed)
#
# This folder is the working copy for docs/, software/, firmware/, cad/, evidence/ and the shared tools/;
# simulation/ owns the simulator itself (server.py, desktop.py, static/, its README and simulator-only tools).
# Runtime data, private tokens, virtual environments and build output are never copied.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
repo="$root/simulation"
[[ -d $repo/.git ]] || { echo "No git checkout at $repo"; exit 1; }
mode=(--dry-run --itemize-changes)
[[ ${1:-} == --apply ]] && mode=(--itemize-changes)
excludes=(--exclude '.DS_Store' --exclude '__pycache__/' --exclude '.pytest_cache/' --exclude '.venv/' --exclude '.venv-*/'
          --exclude 'runs/' --exclude 'build/' --exclude 'build-*/' --exclude 'dist/' --exclude '*.egg-info/' --exclude '.coverage*'
          --exclude 'evidence/raw/' --exclude 'raw/' --exclude 'operator-token*' --exclude '.env' --exclude '.env.*' --exclude 'htmlcov/'
          --exclude '*.backup-*.json')
# Directories this folder owns: mirror them exactly (files removed here are removed in the repo).
for dir in docs software firmware cad evidence; do
  rsync -a --delete "${mode[@]}" "${excludes[@]}" "$root/$dir/" "$repo/$dir/"
done
# tools/: shared tools are updated; simulator-only tools in the repo are kept.
rsync -a "${mode[@]}" "${excludes[@]}" "$root/tools/" "$repo/tools/"
# AGENTS.md and README.md stay repository-specific (the simulator sits at the repository root there).
if [[ ${1:-} == --apply ]]; then
  git -C "$repo" status --short | head -50
  echo "Copied. Review, then commit in $repo yourself; nothing was pushed."
else
  echo "Dry run only. Re-run with --apply to copy."
fi
