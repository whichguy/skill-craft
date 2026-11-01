#!/bin/bash
# The calibration suite, old logic against new logic, alternating, same ambient conditions, low priority (2026-11-01).
#   bash compare_flake.sh OLD_CHECKOUT NEW_CHECKOUT [N]
S=$(cd "$(dirname "$0")" && pwd); OLD=${1:?old checkout}; NEW=${2:?new checkout}; n=${3:-5}
for i in $(seq 1 $n); do
  for arm in old new; do
    tree=$OLD; [ $arm = new ] && tree=$NEW
    log=$S/cmp-$arm-$i.log; start=$(date +%s)
    (cd $tree && CLAUDECODE=1 CLAUDE_CODE_SESSION_ID=ci-stand-in OLLAMA_URL=http://127.0.0.1:9 SHIPLOOP_PROGRESS=off PYTHONDONTWRITEBYTECODE=1 \
       nice -n 10 python3 -B test/shiploop-e2e-brownfield-tickets.test.py > $log 2>&1); rc=$?
    echo "$(date +%H:%M:%S) $arm $i: exit $rc in $(( $(date +%s) - start )) s . $(grep -E '^(Ran |OK|FAILED)' $log | tr '\n' ' ') . load $(uptime | sed 's/.*load averages*: //' | cut -d, -f1) . failing: $(grep -E '^(FAIL|ERROR):' $log | sed 's/ (__main__.*//' | tr '\n' ',' | cut -c1-200)"
  done
done
