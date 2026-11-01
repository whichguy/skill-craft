#!/bin/bash
# SP2, the step-plan slice A/B of the focused-ID rule (docs/shiploop-step-plan-review-2026-11-01.md §7, pre-registered
# there before any slice).  Arm B runs slice.py from SP_BASE (a detached worktree of origin/main at this branch's base,
# e81fdb55), arm T from SP_CHECKOUT (this branch), both on Codex Terra 6.1 xhigh (the owner's runner, 2026-11-01).  Each slice is seeded at step-plan and stops once test-spec is
# accepted (or sent back and redone).  Order B T T B per case, 4 lanes; a slice whose slice-result.json exists is skipped.
set -u
: "${SP_BASE:?arm B checkout}" "${SP_CHECKOUT:?arm T checkout}"
RUNS=$HOME/e2e-runs-sp/20261101/sp2-xhigh
mkdir -p "$RUNS"

one() {  # arm case sample
  local CHECKOUT=$SP_CHECKOUT; [ "$1" = B ] && CHECKOUT=$SP_BASE
  local OUT=$RUNS/$1-$2-s$3
  if [ -f "$OUT/slice-result.json" ]; then echo "SKIP $1 $2 s$3"; return; fi
  echo "START $1 $2 s$3 $(date '+%H:%M:%S')"
  python3 -B "$CHECKOUT/test/shiploop_e2e/slice.py" --case "$2" --host codex --model gpt-6.1-terra --effort xhigh \
    --stop-after test-spec --timeout 3600 --permission-mode auto --output "$OUT" > "$OUT.log" 2>&1
  echo "END $1 $2 s$3 rc=$? $(date '+%H:%M:%S')"
}

QUEUE=()
for CASE in tickets-assign stand-in-rules; do
  QUEUE+=("B $CASE 1" "T $CASE 1" "T $CASE 2" "B $CASE 2" "B $CASE 3" "T $CASE 3" "T $CASE 4" "B $CASE 4")
done
for entry in "${QUEUE[@]}"; do
  while [ "$(jobs -rp | wc -l)" -ge 4 ]; do sleep 5; done
  one $entry &
done
wait
