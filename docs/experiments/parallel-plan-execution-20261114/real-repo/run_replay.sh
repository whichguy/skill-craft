#!/usr/bin/env bash
# run_replay.sh HOST OUTROOT: the eight trials of E18 for one host, one after another, in the order registered for that host (README Amendment A15).
# Run the three hosts side by side, one script each; never two trials of one host at a time. The oracle is NOT run here (PPE_DEFER_ORACLE=1): it would load the
# machine while another host's trial is timed. When every host has finished, run score_replay.sh.
#
# A trial seeds E17's last failed integration of the host (real-repo/replay-states/HOST: main with the landing and the other two features, and the failed
# attempt's branch) and offers the failed step again to one fresh worker under one rule. f = the fix rule (the failed branch with main merged in, markers
# left), r = the redo rule (main as it is). Draw i of the two rules is a pair; the first rule of a pair alternates so that neither is always first.
#
# Profiles are the owner's: Claude Sonnet 5.5 --effort high, Grok 4.6 xhigh, Codex Sol 6.1 medium (the launcher's defaults for the last two).
set -u
HOST=${1:?host: claude, grok or codex}
OUT=${2:?a folder for the trial folders}
shift 2   # optional: the trials to run (for example a rerun of an apparatus fault, `f3`), instead of the registered order
HERE="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$OUT"
export PPE_DEFER_ORACLE=1
EXTRA=()
if [ "$HOST" = "claude" ]; then EXTRA=(--effort high --budget 6); fi
case "$HOST" in
  claude) ORDER="f1 r1 r2 f2 f3 r3 r4 f4" ;;
  grok)   ORDER="r1 f1 f2 r2 r3 f3 f4 r4" ;;
  codex)  ORDER="r1 f1 f2 r2 r3 f3 f4 r4" ;;
  *) echo "unknown host $HOST"; exit 2 ;;
esac

if [ $# -gt 0 ]; then ORDER="$*"; fi

for cell in $ORDER; do
  case "${cell:0:1}" in
    f) rule=fix ;;
    r) rule=redo ;;
  esac
  python3 "$HERE/launch.py" --host "$HOST" --plan tickets3 --timeout 1800 ${EXTRA[@]+"${EXTRA[@]}"} --arm A3s --workspace isolated \
    --seed-state "$HERE/real-repo/replay-states/$HOST" --seed-rule "$rule" --out "$OUT/e18-$HOST-$cell"
done
