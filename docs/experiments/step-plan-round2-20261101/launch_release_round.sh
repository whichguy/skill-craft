#!/bin/bash
# The round's release round (README.md, "Release round"): whole deliveries of ShipLoop from the checkout in SP_CHECKOUT (the
# branch with every change that met its rule), Codex Terra 6.1 xhigh (the owner's runner), the run.py line SP1 used.
# shared-expenses and csv-report start from an empty base and hold no fixed port, so they reach A1, A2a and D at once
# (A2b was reverted in 68985caf, before the release round).
# A sample whose result.json exists is skipped, so a rerun resumes. At most LANES deliveries at once (default 3).
set -u
: "${SP_CHECKOUT:?the checkout to run}"
RUNS=${RUNS:-$HOME/e2e-runs-sp/20261101/round2-release}
LANES=${LANES:-3}
mkdir -p "$RUNS"
echo "$(date -u +%FT%TZ) checkout=$SP_CHECKOUT head=$(git -C "$SP_CHECKOUT" rev-parse HEAD) lanes=$LANES" >> "$RUNS/launch.log"

one() {  # case sample
  local OUT=$RUNS/$1-s$2
  if [ -f "$OUT/result.json" ]; then echo "SKIP $1 s$2 (has a result)"; return; fi
  echo "START $1 s$2 $(date '+%H:%M:%S')"
  SHIPLOOP_E2E_RUNS_ROOT=$HOME/e2e-runs-sp python3 -B "$SP_CHECKOUT/test/shiploop_e2e/run.py" --case "$1" --host codex \
    --model gpt-6.1-terra --effort xhigh --source checkout --timeout 7200 --permission-mode auto --output "$OUT" \
    > "$OUT.log" 2>&1
  echo "END $1 s$2 rc=$? $(date '+%H:%M:%S')"
}

lane() { for job in "$@"; do one ${job%:*} ${job#*:}; done; }
case $LANES in
  2) lane shared-expenses:1 csv-report:1 shared-expenses:3 & lane csv-report:2 shared-expenses:2 csv-report:3 & ;;
  *) lane shared-expenses:1 csv-report:3 & lane csv-report:1 shared-expenses:3 & lane shared-expenses:2 csv-report:2 & ;;
esac
wait
