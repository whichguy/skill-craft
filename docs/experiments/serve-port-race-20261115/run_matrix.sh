#!/bin/bash
# The rate matrix of the study, run in one go (2026-11-15). One JSON line per row is appended to OUT.
#   bash run_matrix.sh DELIVERY_DIR OUT [ROWS]
# ROWS: "all" (default) or a space-separated list of row tags. Each row is serve_race_probe.py's CALLS WORKERS TAG and its churn.
S=$(cd "$(dirname "$0")" && pwd); DELIVERY=${1:?a built ticket-comments reference delivery}; OUT=${2:?an output file}; ROWS=${3:-all}
P="python3 -I $S/serve_race_probe.py $DELIVERY"
run() { tag=$1; shift; if [ "$ROWS" = all ] || [[ " $ROWS " == *" $tag "* ]]; then $P "$@" >> "$OUT"; fi; }
run w2        2000 2  w2
run w8        4000 8  w8
run w16       6000 16 w16
run test4     1000 2  test4  --churn node-test:4
run test16    1000 2  test16 --churn node-test:16
run py1000    3000 2  py1000 --churn py-bind:1000:30
run py5000    2000 2  py5000 --churn py-bind:5000:30
run node2000  2000 2  node2000 --churn node-listen:2000:30
