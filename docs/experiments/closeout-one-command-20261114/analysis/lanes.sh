#!/usr/bin/env bash
# Round 2 lanes (README "Round 2: whole deliveries"): bash lanes.sh X|Y
# Lane X: csv-report B, then shared-expenses T. Lane Y: shared-expenses B, then csv-report T.
set -u
OUT="$HOME/e2e-runs-sp/20261114/closeout-whole"
B=/Users/dadleet/src/skill-craft/.claude/worktrees/closeout-base-6c2ac4   # detached at 3474addc6a2a40c0a13313c3409841831252fe12
T=/Users/dadleet/src/skill-craft/.claude/worktrees/closeout-7dc9de        # branch feat/closeout-7dc9de
run_one() {  # arm checkout case
  echo "=== $(date -u +%FT%TZ) start $1-$3 from $2 ($(git -C "$2" rev-parse HEAD))"
  python3 "$2/test/shiploop_e2e/run.py" --case "$3" --host codex --model gpt-6.1-sol --effort medium \
    --source checkout --output "$OUT/$1-$3" --timeout 5400 --baseline "$OUT/baselines.jsonl"
  echo "=== $(date -u +%FT%TZ) end $1-$3 exit $?"
}
case "${1:-}" in
  X) run_one B "$B" csv-report; run_one T "$T" shared-expenses ;;
  Y) run_one B "$B" shared-expenses; run_one T "$T" csv-report ;;
  *) echo "usage: lanes.sh X|Y" >&2; exit 2 ;;
esac
