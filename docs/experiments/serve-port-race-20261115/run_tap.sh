#!/bin/bash
# Run calibration suites unmodified with a tap on serve.py (tap/sitecustomize.py), 4 at a time as the CI shard does, and count how many
# times each starts a candidate through serve.py and how those runs ended (2026-11-15).
#   bash run_tap.sh CHECKOUT OUT_DIR [SUITE ...]       SUITE: the file name without test/shiploop-e2e- and .test.py
# OUT_DIR gets tap-SUITE.jsonl (one line per serve.py run), SUITE.log (the suite's own output) and tap-summary.txt (tap_summary.py's table).
S=$(cd "$(dirname "$0")" && pwd); X=${1:?a checkout}; OUT=${2:?an output folder}; shift 2
SUITES=${*:-"ticket-comments ticket-sla user-chain user-directory brownfield brownfield-tickets resources"}
mkdir -p "$OUT"; rm -f "$OUT"/tap-*.jsonl
run_one() {
  suite=$1; start=$(date +%s)
  (cd "$X" && SERVE_TAP_FILE="$OUT/tap-$suite.jsonl" PYTHONPATH="$S/tap" PYTHONDONTWRITEBYTECODE=1 CLAUDECODE=1 \
     CLAUDE_CODE_SESSION_ID=ci-stand-in OLLAMA_URL=http://127.0.0.1:9 SHIPLOOP_PROGRESS=off \
     nice -n 10 python3 -B "test/shiploop-e2e-$suite.test.py" > "$OUT/$suite.log" 2>&1); rc=$?
  echo "$suite: exit $rc in $(( $(date +%s) - start )) s: $(grep -E '^(Ran |OK|FAILED)' "$OUT/$suite.log" | tr '\n' ' ' | sed 's/ *$//')"
}
export -f run_one; export S X OUT
printf '%s\n' $SUITES | xargs -P 4 -I{} bash -c 'run_one {}' | tee "$OUT/tap-summary.txt"
python3 -I "$S/tap_summary.py" "$OUT" $SUITES | tee -a "$OUT/tap-summary.txt"
