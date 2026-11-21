#!/bin/sh
# Rounds 7 and 8: the two-sentence cue inside the stage text against the stage text without it, as same-round pairs
# (README "The smaller attempt: re-aimed before it ran"; readings R16 to R19). Every step is resumable. Run from anywhere.
#
#   0  the item sets and their bands exist (label.py), fixed before any subject call
#   1  round 7   M-shiploop-spec-members and P-shiploop-spec, both drivers; leak check; counts
#   2  round 8   the same again, while round 7 is read by both judges
#   3  judges    round 8 by both judges
#   4  readings  label.py pair over the two rounds
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE" || exit 2
LOG="${SPEC_ELAB_WORK:-$HOME/e2e-runs/spec-elaboration-20261120}/queue-6.log"
mkdir -p "$(dirname "$LOG")"
ARMS=M-shiploop-spec-members,P-shiploop-spec
step() { printf '\n===== %s  %s =====\n' "$(date '+%H:%M:%S')" "$1" >> "$LOG"; }
run() { "$@" >> "$LOG" 2>&1; code=$?; printf -- '--- exit %s: %s\n' "$code" "$*" >> "$LOG"; return $code; }

for needed in labels/opus.json labels/astra.json labels/sets.json labels/bands.json; do
    if [ ! -s "$needed" ]; then
        step "STOPPED: $needed is missing; the item sets and bands are fixed before any subject call"
        exit 5
    fi
done

subjects() {
    step "round $1: subjects ($ARMS on sonnet-high,sol-medium)"
    if ! run python3 -I run.py "$1" --arms="$ARMS" --drivers=sonnet-high,sol-medium --parallel=4 --timeout=2700; then
        step "STOPPED: $1 did not start or did not finish (see the lines above)"
        exit 4
    fi
    step "round $1: leak check"
    if ! run python3 -I grade.py leaks "$1"; then
        step "STOPPED: a session in $1 read outside its own directory and profile, or named the held-out material"
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

subjects round-7
judges round-7 &
JUDGING=$!
subjects round-8
wait "$JUDGING"
judges round-8

step "readings R16 to R19"
mkdir -p evidence/round-8
run python3 -I label.py split round-7,round-8
run python3 -I label.py split round-7,round-8 --tag=gpt
run python3 -I label.py pair --rounds=round-7,round-8 --arm=M-shiploop-spec-members --control=P-shiploop-spec --out=evidence/round-8/readings.txt
step "queue finished"
