#!/bin/bash
# One lane of the replication R3 (README.md, "Design"): the shared-expenses case, the listed runs one after the other, each from its
# own arm's checkout so that --source checkout builds that arm.  A run token is ARM:SAMPLE (A:3 is the third run of arm A).  A launch
# the harness refuses writes no output folder, so a lane retries it every 90 seconds for up to 40 minutes and appends each refusal
# to OUT/refusals.txt; a run that started is never repeated here.  A lane appends one "<run> exit=<code> attempts=<n>" line per run
# to OUT/lanes.txt.  Usage: lanes.sh LANE OUT CHECKOUT_A CHECKOUT_B ARM:SAMPLE...
set -u
lane=$1
out=$2
checkout_a=$3
checkout_b=$4
shift 4
for token in "$@"; do
  arm=${token%%:*}
  sample=${token##*:}
  if [ "$arm" = A ]; then checkout=$checkout_a; else checkout=$checkout_b; fi
  run="$out/$arm-shared-expenses-s$sample"
  attempt=0
  while :; do
    attempt=$((attempt + 1))
    (cd "$checkout" && python3 -B test/shiploop_e2e/run.py --case shared-expenses --host codex --model gpt-6.1-terra \
       --effort high --source checkout --timeout 4800 --output "$run" > "$run.log" 2>&1)
    code=$?
    if [ -d "$run" ] || [ "$attempt" -ge 27 ]; then break; fi
    echo "$lane $arm-s$sample attempt $attempt refused: $(tail -n 1 "$run.log" | cut -c1-200)" >> "$out/refusals.txt"
    sleep 90
  done
  echo "$arm-shared-expenses-s$sample exit=$code attempts=$attempt" >> "$out/lanes.txt"
done
