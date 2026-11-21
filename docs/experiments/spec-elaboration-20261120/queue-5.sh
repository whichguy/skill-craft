#!/bin/sh
# Round 6 and the second judge on the deciding rounds (README "The draft, and the one arm past the stop rule").
# Every step is resumable. Run from anywhere.
#
#   1  round 6   Q-shiploop-spec-lenses (the draft) and a second draw of P-shiploop-spec, both drivers     (R15)
#   2  judges    rounds 4c, 5 and 6 read by gpt-6.2-astra as well, beside the registered verdicts           (R13)
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE" || exit 2
LOG="${SPEC_ELAB_WORK:-$HOME/e2e-runs/spec-elaboration-20261120}/queue-5.log"
mkdir -p "$(dirname "$LOG")"
step() { printf '\n===== %s  %s =====\n' "$(date '+%H:%M:%S')" "$1" >> "$LOG"; }
run() { "$@" >> "$LOG" 2>&1; code=$?; printf -- '--- exit %s: %s\n' "$code" "$*" >> "$LOG"; return $code; }

step "round round-6: subjects (Q-shiploop-spec-lenses,P-shiploop-spec on sonnet-high,sol-medium)"
if ! run python3 -I run.py round-6 --arms=Q-shiploop-spec-lenses,P-shiploop-spec --drivers=sonnet-high,sol-medium --parallel=4 --timeout=2700; then
    step "STOPPED: round-6 did not start or did not finish (see the lines above)"
    exit 4
fi
step "round round-6: leak check"
if ! run python3 -I grade.py leaks round-6; then
    step "STOPPED: a session in round-6 read outside its own directory and profile, or named the held-out material"
    exit 3
fi
step "round round-6: counts, judge, board"
run python3 -I grade.py counts round-6
run python3 -I grade.py judge round-6 --parallel=3
run python3 -I grade.py judge round-6 --parallel=3
run python3 -I grade.py board round-6

for round in round-5 round-6 round-4c; do
    step "second judge (gpt-6.2-astra) on $round"
    run python3 -I grade.py judge "$round" --tag=gpt --judge=astra --parallel=3
    run python3 -I grade.py judge "$round" --tag=gpt --judge=astra --parallel=3
    run python3 -I grade.py board "$round" --tag=gpt
    run python3 -I grade.py agree "$round" --tags=gpt
done
step "queue finished"
