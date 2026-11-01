#!/bin/bash
# SP3, the check of 45153684's wording fix (docs/shiploop-step-plan-review-2026-11-01.md §7, pre-registered there before
# any slice): stand-in-rules, 4 step-plan slices from SP_CHECKOUT (this branch) on Codex Terra 6.1 xhigh, the SP2 slice
# line, all at once; read by score_sp2.py (arm T).  A slice whose slice-result.json exists is skipped.
set -u
: "${SP_CHECKOUT:?the checkout to run}"
RUNS=$HOME/e2e-runs-sp/20261101/sp3-xhigh
mkdir -p "$RUNS"
for SAMPLE in 1 2 3 4; do
  OUT=$RUNS/T-stand-in-rules-s$SAMPLE
  if [ -f "$OUT/slice-result.json" ]; then echo "SKIP s$SAMPLE"; continue; fi
  (
    echo "START T stand-in-rules s$SAMPLE $(date '+%H:%M:%S')"
    python3 -B "$SP_CHECKOUT/test/shiploop_e2e/slice.py" --case stand-in-rules --host codex --model gpt-6.1-terra \
      --effort xhigh --stop-after test-spec --timeout 3600 --permission-mode auto --output "$OUT" > "$OUT.log" 2>&1
    echo "END T stand-in-rules s$SAMPLE rc=$? $(date '+%H:%M:%S')"
  ) &
done
wait
