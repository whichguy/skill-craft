#!/usr/bin/env bash
# score_replay.sh OUTROOT: the oracle pass of E18, after every host's timed trials have finished (README Amendment A15). For each trial folder it scores the
# trial with the oracle on (the final tree's per-feature behavior and held-out acceptance checks, the whole tree's own-tests checks, I1 to I5), requires that
# the oracle really ran (a deferred score is not evidence), then exports its compact evidence into evidence/. One trial at a time, on a machine with no timed
# trial running. PPE_RERUN_HANG=1 makes the oracle run a whole-tree check again, at most twice, when the delivery's own test run did not end (A15); a tree that is
# still unjudged after those tries (a check whose output still shows `(rc None)`) is scored again on its retained tree, up to twice more, each earlier pass kept as
# score.pass1.json and score.pass2.json, and the last pass is the trial's verdict. The exit code is 1 when any trial failed to score or export; a failed trial is
# named, not skipped silently.
set -u
OUT=${1:?the folder that holds the trial folders}
HERE="$(cd "$(dirname "$0")/.." && pwd)"
unset PPE_DEFER_ORACLE
export PPE_RERUN_HANG=1
failed=0
for trial in "$OUT"/e18-*; do
  [ -d "$trial" ] || continue
  echo "== $(basename "$trial")"
  ok=1
  python3 "$HERE/score.py" "$trial" || ok=0
  pass=1
  while [ "$ok" -eq 1 ] && python3 "$HERE/replay.py" hung "$trial" && [ "$pass" -lt 3 ]; do
    echo "the whole-tree check did not end in any of its tries: scoring the retained tree again (pass $((pass + 1)) of 3)"
    cp "$trial/score.json" "$trial/score.pass$pass.json"
    sleep 30
    python3 "$HERE/score.py" "$trial" || ok=0
    pass=$((pass + 1))
  done
  if [ "$ok" -eq 1 ] \
     && python3 -c 'import json, sys; o = ((json.load(open(sys.argv[1] + "/score.json")).get("write") or {}).get("oracle") or {}); sys.exit(0 if ("valid" in o and not o.get("deferred")) else 1)' "$trial" \
     && python3 "$HERE/export.py" "$trial"; then
    :
  else
    echo "SCORING OR EXPORT OF $(basename "$trial") FAILED (no oracle verdict or an error above); score it again before anything is read from it"
    failed=$((failed + 1))
  fi
done
echo "score_replay.sh: $failed trial(s) failed"
[ "$failed" -eq 0 ]
