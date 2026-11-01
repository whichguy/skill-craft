#!/bin/bash
# SP1, the live check of the focused-ID rule (docs/shiploop-step-plan-review-2026-11-01.md §7, pre-registered there
# before any run): ShipLoop from the checkout in SP_CHECKOUT (this branch), Codex Terra 6.1 high, the run.py line FX
# used.  csv-report and hello hold no fixed port and start at once; the ticket-import samples run one at a time on
# port 4180's lane and wait while another harness holds its lease.  A sample whose result.json exists is skipped, so a
# rerun resumes.
set -u
: "${SP_CHECKOUT:?the checkout to run}"
RUNS=$HOME/e2e-runs-sp/20261101
LEASE=${XDG_STATE_HOME:-$HOME/.local/state}/shiploop-e2e/leases/port-4180.lock
mkdir -p "$RUNS"

one() {  # case sample
  local OUT=$RUNS/$1-s$2
  if [ -f "$OUT/result.json" ]; then echo "SKIP $1 s$2 (has a result)"; return; fi
  echo "START $1 s$2 $(date '+%H:%M:%S')"
  SHIPLOOP_E2E_RUNS_ROOT=$HOME/e2e-runs-sp python3 -B "$SP_CHECKOUT/test/shiploop_e2e/run.py" --case "$1" --host codex \
    --model gpt-6.1-terra --effort high --source checkout --timeout 7200 --permission-mode auto --output "$OUT" \
    > "$OUT.log" 2>&1
  echo "END $1 s$2 rc=$? $(date '+%H:%M:%S')"
}

one csv-report 1 &
one csv-report 2 &
one hello 1 &
for SAMPLE in 1 2 3; do
  while :; do
    HOLDER=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("pid",""))' "$LEASE" 2>/dev/null)
    if [ -n "$HOLDER" ] && kill -0 "$HOLDER" 2>/dev/null; then sleep 60; continue; fi
    break
  done
  one ticket-import "$SAMPLE"
done
wait
