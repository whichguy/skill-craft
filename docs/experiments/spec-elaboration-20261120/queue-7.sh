#!/bin/sh
# Rounds 9 and 10: the review's replacement for one sentence of duty 4 (arm G), the same without its "keep the bound
# open" sentence (arm H, a contrast), and the released stage (P), as same-round pairs (README "A filter round for the
# review's wording"; readings R20 to R23). Every step is resumable. Run from anywhere.
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE" || exit 2
LOG="${SPEC_ELAB_WORK:-$HOME/e2e-runs/spec-elaboration-20261120}/queue-7.log"
mkdir -p "$(dirname "$LOG")"
ARMS=G-shiploop-spec-duty4-bounds,H-shiploop-spec-duty4-no-open,P-shiploop-spec
step() { printf '\n===== %s  %s =====\n' "$(date '+%H:%M:%S')" "$1" >> "$LOG"; }
run() { "$@" >> "$LOG" 2>&1; code=$?; printf -- '--- exit %s: %s\n' "$code" "$*" >> "$LOG"; return $code; }

for needed in labels/limits-opus.json labels/limits-astra.json labels/bands-2.json; do
    if [ ! -s "$needed" ]; then
        step "STOPPED: $needed is missing; the limit sets and their bands are fixed before any subject call"
        exit 5
    fi
done

subjects() {
    step "round $1: subjects ($ARMS on sonnet-high,sol-medium)"
    if ! run python3 -I run.py "$1" --arms="$ARMS" --drivers=sonnet-high,sol-medium --parallel=6 --timeout=2700; then
        step "STOPPED: $1 did not start or did not finish (see the lines above)"
        exit 4
    fi
    step "round $1: leak check"
    if ! run python3 -I grade.py leaks "$1"; then
        step "STOPPED: the scan of $1 flagged a session (a path outside its own directory and profile, or a held-out name)"
        exit 3
    fi
    run python3 -I grade.py counts "$1"
}

judges() {
    step "round $1: both judges"
    run python3 -I grade.py judge "$1" --parallel=3
    run python3 -I grade.py judge "$1" --parallel=3
    run python3 -I grade.py judge "$1" --tag=gpt --judge=astra --parallel=3
    run python3 -I grade.py judge "$1" --tag=gpt --judge=astra --parallel=3
    run python3 -I grade.py board "$1"
    run python3 -I grade.py board "$1" --tag=gpt
    run python3 -I grade.py agree "$1" --tags=gpt
    step "round $1: judged"
}

subjects round-9
judges round-9 &
JUDGING=$!
subjects round-10
wait "$JUDGING"
judges round-10

step "readings R20 to R23"
mkdir -p evidence/round-10
run python3 -I label.py split round-9,round-10
run python3 -I label.py split round-9,round-10 --tag=gpt
for arm in G-shiploop-spec-duty4-bounds H-shiploop-spec-duty4-no-open; do
    run python3 -I label.py pair --rounds=round-9,round-10 --arm="$arm" --control=P-shiploop-spec --target=N1 --bands=bands-2.json --out="evidence/round-10/readings-${arm%%-*}.txt"
done
step "queue finished"
