#!/bin/bash
# The F31 live check (README.md in this folder, registered before any run). Arm A runs ShipLoop from F31_A (a detached
# worktree at the registration commit), arm B from F31_B (the candidate commit, whose parent is the registration
# commit), both on Codex Terra 6.1 xhigh, the owner's runner. Part 1: slices seeded at test-spec that stop once implement
# is accepted, on the two seeded cases. Part 2: whole csv-report deliveries. Order fixed below, at most LANES at once. A
# run whose result file exists is skipped, so a rerun resumes.
set -u
: "${F31_A:?arm A checkout}" "${F31_B:?arm B checkout}"
RUNS=${F31_RUNS:-$HOME/e2e-runs-f31/20261101}
LANES=${LANES:-5}
mkdir -p "$RUNS"

slice() {  # arm case sample
  local CHECKOUT=$F31_A; [ "$1" = B ] && CHECKOUT=$F31_B
  local OUT=$RUNS/$1-$2-s$3
  if [ -f "$OUT/slice-result.json" ]; then echo "SKIP $1 $2 s$3"; return; fi
  echo "START $1 $2 s$3 $(date '+%H:%M:%S')"
  python3 -B "$CHECKOUT/test/shiploop_e2e/slice.py" --case "$2" --host codex --model gpt-6.1-terra --effort xhigh \
    --seed-at test-spec --stop-after implement --timeout 3600 --permission-mode auto --output "$OUT" > "$OUT.log" 2>&1
  echo "END $1 $2 s$3 rc=$? $(date '+%H:%M:%S')"
}

delivery() {  # arm sample
  local CHECKOUT=$F31_A; [ "$1" = B ] && CHECKOUT=$F31_B
  local OUT=$RUNS/$1-csv-report-s$2
  if [ -f "$OUT/result.json" ]; then echo "SKIP $1 csv-report s$2"; return; fi
  echo "START $1 csv-report s$2 $(date '+%H:%M:%S')"
  SHIPLOOP_E2E_RUNS_ROOT=$HOME/e2e-runs-f31 python3 -B "$CHECKOUT/test/shiploop_e2e/run.py" --case csv-report \
    --host codex --model gpt-6.1-terra --effort xhigh --source checkout --timeout 7200 --permission-mode auto \
    --output "$OUT" > "$OUT.log" 2>&1
  echo "END $1 csv-report s$2 rc=$? $(date '+%H:%M:%S')"
}

QUEUE=()
for CASE in tickets-assign stand-in-rules; do
  QUEUE+=("slice A $CASE 1" "slice B $CASE 1" "slice B $CASE 2" "slice A $CASE 2"
          "slice A $CASE 3" "slice B $CASE 3" "slice B $CASE 4" "slice A $CASE 4")
done
QUEUE+=("delivery A 1" "delivery B 1" "delivery B 2" "delivery A 2" "delivery A 3" "delivery B 3")
for entry in "${QUEUE[@]}"; do
  while [ "$(jobs -rp | wc -l)" -ge "$LANES" ]; do sleep 5; done
  $entry &
  sleep 2
done
wait
echo "ALL DONE $(date '+%H:%M:%S')"
