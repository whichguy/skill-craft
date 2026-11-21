#!/bin/sh
# The follow-ups registered in README.md on 2026-11-20, in order. Every step is resumable: a finished subject call,
# verdict or audit is skipped, so running this again continues where it stopped. Run from anywhere.
#
#   1  round 4   A-single and D-enumerated-only again, on the harness's Codex isolation      (R6, R7, R1)
#   2  round 5   F-guarded, L-lenses-once, S-sectioned                                      (R8, R9, R11)
#   3  judges    round 4 judged twice more: Opus again (@r2), gpt-6.2-astra (@gpt)           (R12, R13)
#   4  audits    every clause of rounds 4, 5 and 1 put in one class                           (R10)
#
# A leak found in a round's streams stops the whole queue: nothing after it would mean what it claims.
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE" || exit 2
LOG="${SPEC_ELAB_WORK:-$HOME/e2e-runs/spec-elaboration-20261120}/queue-2.log"
mkdir -p "$(dirname "$LOG")"
step() { printf '\n===== %s  %s =====\n' "$(date '+%H:%M:%S')" "$1" >> "$LOG"; }
run() { "$@" >> "$LOG" 2>&1; code=$?; printf -- '--- exit %s: %s\n' "$code" "$*" >> "$LOG"; return $code; }

subjects() {  # round, arms
    step "round $1: subjects ($2)"
    run python3 -I run.py "$1" "--arms=$2" --parallel=4 --timeout=2700
    step "round $1: leak check"
    if ! run python3 -I grade.py leaks "$1"; then
        step "STOPPED: a session in $1 reached outside its own directory and profile"
        exit 3
    fi
    step "round $1: counts, judge, board"
    run python3 -I grade.py counts "$1"
    run python3 -I grade.py judge "$1" --parallel=3
    run python3 -I grade.py judge "$1" --parallel=3     # a second invocation picks up any verdict the first lost
    run python3 -I grade.py board "$1"
}

subjects round-4 A-single,D-enumerated-only
subjects round-5 F-guarded,L-lenses-once,S-sectioned
run python3 -I timeline.py round-4 round-5

step "judge checks on round 4: a second Opus draw, and gpt-6.2-astra (calibrated on cal-1 first)"
run python3 -I grade.py judge cal-1 --tag=gpt --judge=astra --parallel=2
run python3 -I grade.py judge round-4 --tag=r2 --parallel=3
run python3 -I grade.py judge round-4 --tag=r2 --parallel=3
run python3 -I grade.py judge round-4 --tag=gpt --judge=astra --parallel=3
run python3 -I grade.py judge round-4 --tag=gpt --judge=astra --parallel=3
run python3 -I grade.py board round-4 --tag=r2
run python3 -I grade.py board round-4 --tag=gpt
run python3 -I grade.py agree round-4 --tags=r2,gpt

for round in round-4 round-5 round-1; do
    step "clause audit: $round"
    run python3 -I grade.py audit "$round" --parallel=3
    run python3 -I grade.py audit "$round" --parallel=3
    run python3 -I grade.py audit-board "$round"
done
step "queue finished"
