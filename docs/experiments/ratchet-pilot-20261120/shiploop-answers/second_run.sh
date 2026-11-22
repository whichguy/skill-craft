#!/bin/bash
# Launch second ShipLoop runs, each on the project an earlier delivery left, with the owner's ruling as the request.
#
#   second_run.sh REPO COMMIT ROOT NAME=PRIOR [NAME=PRIOR ...]
#
# REPO    the repository whose COMMIT is built (a detached copy of it is made once under ROOT, or reused, so later edits
#         of the branch never change a run in flight)
# ROOT    the folder the runs are written under; a session sees its own folder's path, so ROOT and NAME are neutral
# PRIOR   an earlier delivery's output folder: the new run starts in a copy of PRIOR/work (second_run.py, run.py
#         --continue-from), which must be a Git checkout with nothing uncommitted; PRIOR itself is never written to
#
# second_run.py builds run.py's arguments: the request (late-notes.json notes.start, the owner's ruling word for word)
# and the eight checks of ticket-due-times.  No stand-in requester runs.  Every run is Codex with gpt-6.2-sol at medium
# unless the environment names another driver: HOST, MODEL and EFFORT (for example HOST=claude
# MODEL=claude-sonnet-5-5).  RUN_ARGS, when set, is added to run.py's arguments as words (for example
# RUN_ARGS="--max-budget-usd 40").  Its row of the harness's baseline ledger goes to ROOT/baselines.jsonl, never to the
# repository's own ledger.  ROOT/NAME-prior.txt holds PRIOR/work's HEAD and the PRIOR path.  The script waits for all
# of them, writes each run's exit code to ROOT/NAME.exit, and says for each whether PRIOR/work is as it was.
set -u
REPO=$1; COMMIT=$2; ROOT=$3; shift 3
HOST=${HOST:-codex}; MODEL=${MODEL:-gpt-6.2-sol}; EFFORT=${EFFORT:-medium}
APP="$ROOT/apparatus-$(printf '%s' "$COMMIT" | cut -c1-12)"
HERE_IN_REPO=docs/experiments/ratchet-pilot-20261120/shiploop-answers
mkdir -p "$ROOT"
if [ ! -d "$APP" ]; then
  git -C "$REPO" worktree add --detach "$APP" "$COMMIT" > "$ROOT/apparatus.log" 2>&1 || { echo "no apparatus copy; see $ROOT/apparatus.log"; exit 2; }
fi
[ "$(git -C "$APP" rev-parse HEAD)" = "$COMMIT" ] || { echo "the apparatus copy is not at $COMMIT"; exit 2; }
for file in second_run.py late-notes.json; do
  [ -f "$APP/$HERE_IN_REPO/$file" ] || { echo "the apparatus copy at $COMMIT has no $HERE_IN_REPO/$file"; exit 2; }
done
for cell in "$@"; do   # every cell is checked before anything starts, so a refusal leaves no run behind
  name=${cell%%=*}; prior=${cell#*=}
  [ "$name" != "$cell" ] && [ -n "$name" ] && [ -n "$prior" ] || { echo "$cell: a cell is NAME=PRIOR"; exit 2; }
  [ -e "$ROOT/$name" ] && { echo "$ROOT/$name exists; a run needs a new folder"; exit 2; }
  [ -e "$prior/work/.git" ] || { echo "$prior/work has no .git; nothing was started"; exit 2; }
  [ -z "$(git -C "$prior/work" status --porcelain)" ] || { echo "$prior/work has uncommitted changes; nothing was started"; exit 2; }
done
for cell in "$@"; do
  name=${cell%%=*}; prior=${cell#*=}
  printf '%s\n%s\n' "$(git -C "$prior/work" rev-parse HEAD)" "$prior" > "$ROOT/$name-prior.txt"
  (
    cd "$APP" || exit 2
    # shellcheck disable=SC2086
    python3 -B "$HERE_IN_REPO/second_run.py" --prior "$prior" --output "$ROOT/$name" --baseline "$ROOT/baselines.jsonl" \
      --host "$HOST" --model "$MODEL" --effort "$EFFORT" ${RUN_ARGS:-} > "$ROOT/$name-log.txt" 2>&1
    echo $? > "$ROOT/$name.exit"
  ) &
  echo "$name run $!" >> "$ROOT/pids.txt"
  date "+%H:%M:%S launched $name (second run on $prior, $HOST $MODEL $EFFORT)"
done
wait
date "+%H:%M:%S wave finished"
for cell in "$@"; do
  name=${cell%%=*}; prior=${cell#*=}
  before=$(head -n 1 "$ROOT/$name-prior.txt")
  if [ "$(git -C "$prior/work" rev-parse HEAD)" = "$before" ] && [ -z "$(git -C "$prior/work" status --porcelain)" ]; then
    state="prior unchanged"
  else
    state="PRIOR CHANGED"
  fi
  echo "$name exit $(cat "$ROOT/$name.exit" 2>/dev/null || echo '?'); $state"
done
