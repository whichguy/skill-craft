#!/usr/bin/env bash
# score_cells.sh OUTROOT: the oracle pass of E17, after every host's timed cells have finished (README Amendment A14). For each trial folder it scores the
# trial with the oracle on (the final tree, each first branch alone, the whole tree's own-tests checks, I1 to I5, and the exact tree of every attempted
# integration), then exports its compact evidence into evidence/. One trial at a time, on a machine with no timed cell running.
set -u
OUT=${1:?the folder that holds the trial folders}
HERE="$(cd "$(dirname "$0")/.." && pwd)"
unset PPE_DEFER_ORACLE
for trial in "$OUT"/e17-*; do
  [ -d "$trial" ] || continue
  echo "== $(basename "$trial")"
  python3 "$HERE/score.py" "$trial" && python3 "$HERE/export.py" "$trial" || echo "scoring or export of $(basename "$trial") failed"
done
