#!/bin/bash
# run_test41.sh REPO N OUT: run the one test N times from the checkout REPO, count how many runs print the cleanup
# diagnostic.
# Read-only for the repo: the test works in its own temporary folder.
set -u
R=$1; N=$2; OUT=$3
: > "$OUT"
printed=0; failed=0
for i in $(seq 1 "$N"); do
  log=$(cd "$R" && PYTHONDONTWRITEBYTECODE=1 python3 -B test/test-groups.test.py SuiteGroupOwnershipTest.test_timeout_grace_interrupt_finishes_owned_group_before_escape 2>&1)
  code=$?
  line=0
  case "$log" in *"suite cleanup:"*) line=1; printed=$((printed+1));; esac
  [ "$code" = "0" ] || failed=$((failed+1))
  echo "run $i exit $code diagnostic $line" >> "$OUT"
  if [ "$line" = "1" ] && [ "$printed" = "1" ]; then printf '%s\n' "--- first run that printed it:" "$log" >> "$OUT.first"; fi
done
echo "runs $N, printed the diagnostic $printed, failed $failed, load $(sysctl -n vm.loadavg)" >> "$OUT"
tail -1 "$OUT"
