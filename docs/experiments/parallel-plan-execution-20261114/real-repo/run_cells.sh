#!/usr/bin/env bash
# run_cells.sh HOST OUTROOT: the five registered cells of E17 for one host, one after another, in the order registered for that host
# (README Amendment A14). Run the three hosts side by side, one script each; never two cells of one host at a time. The oracle is NOT run here
# (PPE_DEFER_ORACLE=1): it would load the machine while another host's cell is timed. When every host has finished, run score_cells.sh.
#
#   s   one context does the three features in turn in one checkout
#   qs  fresh sub-agents one at a time (capacity one), a git worktree each, the re-test after each merge, the fix rule
#   q0  fresh sub-agents three at a time, a git worktree each, the re-test after each merge, the fix rule
#   qp  q0 and the teammate's change landing on main before the first merge
#   qr  qp with the redo rule (E13's: abort and offer the task again from main's current head)
#
# Profiles are the owner's: Claude Sonnet 5.5 --effort high, Grok 4.6 xhigh, Codex Sol 6.1 medium (the launcher's defaults for the last two).
set -u
HOST=${1:?host: claude, grok or codex}
OUT=${2:?a folder for the trial folders}
HERE="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$OUT"
export PPE_DEFER_ORACLE=1
EXTRA=()
if [ "$HOST" = "claude" ]; then EXTRA=(--effort high --budget 20); fi
case "$HOST" in
  claude) ORDER="s qs q0 qp qr" ;;
  grok)   ORDER="qp qr s q0 qs" ;;
  codex)  ORDER="qr q0 qs s qp" ;;
  *) echo "unknown host $HOST"; exit 2 ;;
esac

run() {
  local cell=$1; shift
  python3 "$HERE/launch.py" --host "$HOST" --plan tickets3 --timeout 3600 ${EXTRA[@]+"${EXTRA[@]}"} --out "$OUT/e17-$HOST-$cell" "$@"
}

for cell in $ORDER; do
  case "$cell" in
    s)  run s  --arm A0  --workspace shared ;;
    qs) run qs --arm A3s --workspace isolated --on-failure fix ;;
    q0) run q0 --arm A3  --workspace isolated --on-failure fix  --capacity 3 ;;
    qp) run qp --arm A3  --workspace isolated --on-failure fix  --capacity 3 --land ;;
    qr) run qr --arm A3  --workspace isolated --on-failure redo --capacity 3 --land ;;
  esac
done
