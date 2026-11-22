#!/bin/bash
# Launch one wave of real deliveries of the candidate, each beside its stand-in requester.
#
#   launch_wave.sh REPO COMMIT ROOT NAME:CASE:MODE [NAME:CASE:MODE ...]
#
# REPO    the repository whose COMMIT is built (a detached copy of it is made once under ROOT, so later edits of the
#         branch never change a run in flight)
# ROOT    the folder the runs are written under; a session sees its own folder's path, so ROOT and NAME are neutral
# MODE    reply   the stand-in sends the requester's reply when a printed row is about the case's point
#         silent  the stand-in reads and records what was printed and sends nothing
#         none    no stand-in
#
# Every run is Codex with gpt-6.2-sol at medium, built from the checkout, as the archive it is read against.  Its row
# of the harness's baseline ledger goes to ROOT/baselines.jsonl, never to the repository's own ledger.
# The script waits for all of them and writes each run's exit code to ROOT/NAME.exit.
set -u
REPO=$1; COMMIT=$2; ROOT=$3; shift 3
APP="$ROOT/apparatus-$(printf '%s' "$COMMIT" | cut -c1-12)"
HERE_IN_REPO=docs/experiments/ratchet-pilot-20261120/shiploop-defaults
mkdir -p "$ROOT"
if [ ! -d "$APP" ]; then
  git -C "$REPO" worktree add --detach "$APP" "$COMMIT" > "$ROOT/apparatus.log" 2>&1 || { echo "no apparatus copy; see $ROOT/apparatus.log"; exit 2; }
fi
[ "$(git -C "$APP" rev-parse HEAD)" = "$COMMIT" ] || { echo "the apparatus copy is not at $COMMIT"; exit 2; }
for cell in "$@"; do   # every folder is checked before anything starts, so a refusal leaves no run behind
  [ -e "$ROOT/${cell%%:*}" ] && { echo "$ROOT/${cell%%:*} exists; a run needs a new folder"; exit 2; }
done
for cell in "$@"; do
  name=${cell%%:*}; rest=${cell#*:}; case_name=${rest%%:*}; mode=${rest#*:}
  out="$ROOT/$name"
  (
    cd "$APP" || exit 2
    python3 test/shiploop_e2e/run.py --source checkout --case "$case_name" --host codex --model gpt-6.2-sol \
      --effort medium --output "$out" --baseline "$ROOT/baselines.jsonl" --quiet > "$ROOT/$name-log.txt" 2>&1
    echo $? > "$ROOT/$name.exit"
  ) &
  echo "$name run $!" >> "$ROOT/pids.txt"
  if [ "$mode" = reply ] || [ "$mode" = silent ]; then
    flag=""; [ "$mode" = reply ] && flag="--reply"
    (
      cd "$APP" || exit 2
      # shellcheck disable=SC2086
      python3 "$HERE_IN_REPO/requester.py" --out "$out" --case "$case_name" $flag > "$ROOT/$name-requester-log.txt" 2>&1
    ) &
    echo "$name requester $!" >> "$ROOT/pids.txt"
  fi
  date "+%H:%M:%S launched $name ($case_name, $mode)"
done
wait
date "+%H:%M:%S wave finished"
for cell in "$@"; do
  name=${cell%%:*}
  echo "$name exit $(cat "$ROOT/$name.exit" 2>/dev/null || echo '?')"
done
