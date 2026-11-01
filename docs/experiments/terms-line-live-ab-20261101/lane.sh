#!/bin/bash
# One lane of the live A/B (README.md, "Design"): one case, runs A-s1, B-s1, A-s2, B-s2 one after the other, each run from
# its own arm's checkout so that --source checkout builds that arm.  A lane writes one "<run> exit=<code>" line per run to
# OUT/lanes.txt.  Usage: lane.sh CASE ARM_A_CHECKOUT ARM_B_CHECKOUT OUT
set -u
case_name=$1
checkout_a=$2
checkout_b=$3
out=$4
for sample in 1 2; do
  for arm in A B; do
    if [ "$arm" = A ]; then checkout=$checkout_a; else checkout=$checkout_b; fi
    run="$out/$arm-$case_name-s$sample"
    (cd "$checkout" && python3 -B test/shiploop_e2e/run.py --case "$case_name" --host codex --model gpt-6.1-terra \
       --effort high --source checkout --timeout 4800 --output "$run" > "$run.log" 2>&1)
    echo "$arm-$case_name-s$sample exit=$?" >> "$out/lanes.txt"
  done
done
