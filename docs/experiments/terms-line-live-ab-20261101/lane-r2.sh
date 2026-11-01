#!/bin/bash
# One lane of the replication R2 (README.md, "Round 1 as read"): the hello case, one arm, the given samples one after the other, each run
# from the arm's own checkout so that --source checkout builds that arm.  A lane writes one "<run> exit=<code>" line per run to
# OUT/lanes.txt.  Usage: lane-r2.sh ARM CHECKOUT OUT SAMPLE...
set -u
arm=$1
checkout=$2
out=$3
shift 3
for sample in "$@"; do
  run="$out/$arm-hello-s$sample"
  (cd "$checkout" && python3 -B test/shiploop_e2e/run.py --case hello --host codex --model gpt-6.1-terra \
     --effort high --source checkout --timeout 4800 --output "$run" > "$run.log" 2>&1)
  echo "$arm-hello-s$sample exit=$?" >> "$out/lanes.txt"
done
