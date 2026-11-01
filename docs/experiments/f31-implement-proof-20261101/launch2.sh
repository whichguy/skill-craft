#!/bin/bash
# Round 2 of the F31 live check (README.md in this folder, amendment 2, registered before any run of it). Arms: A from
# F31_A (the registration commit), B from F31_B (the first wording, 97667d22), V from F31_V (the revised wording, its
# child). Part 3: hollow-Proof slices of tickets-assign, seeded at test-spec with S1's Proof replaced by `npm test`
# (hollow-proof-seed.json), 4 per arm. Part 4: arm V on the original seeds (4 tickets-assign, 4 stand-in-rules) and 3
# csv-report deliveries. After each run its folder's observers are stopped (lifecycle.py cleanup), because a finished
# slice's observer made run.py refuse round 1's deliveries. At most LANES at once; a run with a result file is skipped.
set -u
: "${F31_A:?arm A checkout}" "${F31_B:?arm B checkout}" "${F31_V:?arm V checkout}"
HERE=$(cd "$(dirname "$0")" && pwd)
RUNS=${F31_RUNS:-$HOME/e2e-runs-f31/20261101-r2}
LANES=${LANES:-5}
mkdir -p "$RUNS"

checkout() { case "$1" in A) echo "$F31_A";; B) echo "$F31_B";; V) echo "$F31_V";; esac; }
tidy() { python3 "$F31_A/test/shiploop_e2e/lifecycle.py" cleanup "$1" > /dev/null 2>&1 || true; }

slice() {  # arm case sample [seed]
  local CHECKOUT; CHECKOUT=$(checkout "$1")
  local NAME=$2; local SEED=()
  if [ "${4:-}" = hollow ]; then NAME=hollow-$2; SEED=(--seed-records "$HERE/hollow-proof-seed.json"); fi
  local OUT=$RUNS/$1-$NAME-s$3
  if [ -f "$OUT/slice-result.json" ]; then echo "SKIP $1 $NAME s$3"; return; fi
  echo "START $1 $NAME s$3 $(date '+%H:%M:%S')"
  python3 -B "$CHECKOUT/test/shiploop_e2e/slice.py" --case "$2" --host codex --model gpt-6.1-terra --effort xhigh \
    --seed-at test-spec --stop-after implement "${SEED[@]}" --timeout 3600 --permission-mode auto --output "$OUT" \
    > "$OUT.log" 2>&1
  local rc=$?; tidy "$OUT"
  echo "END $1 $NAME s$3 rc=$rc $(date '+%H:%M:%S')"
}

delivery() {  # arm sample
  local CHECKOUT; CHECKOUT=$(checkout "$1")
  local OUT=$RUNS/$1-csv-report-s$2
  if [ -f "$OUT/result.json" ]; then echo "SKIP $1 csv-report s$2"; return; fi
  echo "START $1 csv-report s$2 $(date '+%H:%M:%S')"
  SHIPLOOP_E2E_RUNS_ROOT=$HOME/e2e-runs-f31 python3 -B "$CHECKOUT/test/shiploop_e2e/run.py" --case csv-report \
    --host codex --model gpt-6.1-terra --effort xhigh --source checkout --timeout 7200 --permission-mode auto \
    --output "$OUT" > "$OUT.log" 2>&1
  local rc=$?; tidy "$OUT"
  echo "END $1 csv-report s$2 rc=$rc $(date '+%H:%M:%S')"
}

QUEUE=("slice A tickets-assign 1 hollow" "slice B tickets-assign 1 hollow" "slice V tickets-assign 1 hollow"
       "slice V tickets-assign 2 hollow" "slice A tickets-assign 2 hollow" "slice B tickets-assign 2 hollow"
       "slice B tickets-assign 3 hollow" "slice V tickets-assign 3 hollow" "slice A tickets-assign 3 hollow"
       "slice A tickets-assign 4 hollow" "slice V tickets-assign 4 hollow" "slice B tickets-assign 4 hollow"
       "delivery V 1" "delivery V 2" "delivery V 3")
for CASE in tickets-assign stand-in-rules; do
  for N in 1 2 3 4; do QUEUE+=("slice V $CASE $N"); done
done
for entry in "${QUEUE[@]}"; do
  while [ "$(jobs -rp | wc -l)" -ge "$LANES" ]; do sleep 5; done
  $entry &
  sleep 2
done
wait
echo "ALL DONE $(date '+%H:%M:%S')"
