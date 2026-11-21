#!/bin/sh
# The revised queue (README "The plan to conclude", 2026-11-20). Every step is resumable: a finished subject call,
# verdict or audit is skipped, so running this again continues where it stopped. Run from anywhere.
#
#   1  round 4   A-single and D-enumerated-only again, on the harness's Codex isolation       (R6, R7, R1)
#   2  round 5   F-guarded, L-lenses-once, and P-shiploop-spec (the released stage's own text) (R8, R9, R14)
#   3  judges    round 4 judged twice more: Opus again (@r2), gpt-6.2-astra (@gpt)            (R12, R13)
#   4  audits    every C-n clause of rounds 4 and 5 put in one class                            (R10)
#
# A leak found in a round's streams stops the whole queue: nothing after it would mean what it claims.
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE" || exit 2
LOG="${SPEC_ELAB_WORK:-$HOME/e2e-runs/spec-elaboration-20261120}/queue-3.log"
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

step "waiting for the round-4 calls the first queue left in flight"
while pgrep -f "run.py round-4" > /dev/null 2>&1; do sleep 15; done

subjects round-4 A-single,D-enumerated-only
subjects round-5 F-guarded,L-lenses-once,P-shiploop-spec
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

step "clause audit: round-4"
run python3 -I grade.py audit round-4 --parallel=3
run python3 -I grade.py audit round-4 --parallel=3
run python3 -I grade.py audit-board round-4
step "clause audit: round-5 (the arms that write C-n clauses)"
run python3 -I grade.py audit round-5 --arms=F-guarded,L-lenses-once --parallel=3
run python3 -I grade.py audit round-5 --arms=F-guarded,L-lenses-once --parallel=3
run python3 -I grade.py audit-board round-5
step "queue finished"
