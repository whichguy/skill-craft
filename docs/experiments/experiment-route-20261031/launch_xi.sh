#!/bin/bash
# XI's live runs (README.md, "XI"), one lane on port 4180: each run waits until no harness holds that port's lease, then runs
# to its end. Arguments: ARM SAMPLE [SAMPLE ...]; ARM A runs this checkout's run.py (ShipLoop as on main), ARM B the
# candidate checkout named by XI_CANDIDATE. A sample whose result.json exists is skipped, so a rerun resumes.
set -u
ARM=$1; shift
HERE=$(cd "$(dirname "$0")" && pwd)
CHECKOUT=$(cd "$HERE/../../.." && pwd)
[ "$ARM" = B ] && CHECKOUT=${XI_CANDIDATE:?the candidate checkout}
RUNS=$HOME/e2e-runs-xr/20261031
LEASE=${XDG_STATE_HOME:-$HOME/.local/state}/shiploop-e2e/leases/port-4180.lock
mkdir -p "$RUNS"
for SAMPLE in "$@"; do
  OUT=$RUNS/$ARM-ticket-import-s$SAMPLE
  if [ -f "$OUT/result.json" ]; then echo "SKIP $ARM s$SAMPLE (has a result)"; continue; fi
  while :; do
    HOLDER=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("pid",""))' "$LEASE" 2>/dev/null)
    if [ -n "$HOLDER" ] && kill -0 "$HOLDER" 2>/dev/null; then sleep 60; continue; fi
    break
  done
  echo "START $ARM s$SAMPLE $(date '+%H:%M:%S') from $CHECKOUT"
  SHIPLOOP_E2E_RUNS_ROOT=$HOME/e2e-runs-xr python3 -B "$CHECKOUT/test/shiploop_e2e/run.py" --case ticket-import --host codex \
    --model gpt-6.1-terra --effort high --source checkout --timeout 7200 --permission-mode auto --output "$OUT" \
    > "$OUT.log" 2>&1
  echo "END $ARM s$SAMPLE rc=$? $(date '+%H:%M:%S')"
done
