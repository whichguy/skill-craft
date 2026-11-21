#!/bin/sh
# The queue after round 4's leak check stopped queue-3.sh (README "Round 4 as it turned out", 2026-11-20).
# Every step is resumable. Run from anywhere.
#
#   1  round 4    judged as it ran: Sonnet clean (the noise floor), Sol a second draw with the skills shown   (R6)
#   2  round 4c   A-single and D-enumerated-only on Sol again, user-level skills turned off and proved off      (R7, R1)
#   3  round 5    F-guarded, L-lenses-once, P-shiploop-spec, both drivers                                      (R8, R9, R14)
#   4  judges     round 4 judged twice more: Opus again (@r2), gpt-6.2-astra (@gpt)                            (R12, R13)
#   5  audits     every C-n clause of the clean specifications of rounds 4, 4c and 5                             (R10)
#
# From round 4c on a round refuses to start unless a no-model render shows a Codex session none of the user's
# skills, and a leak found afterwards in a round's streams stops the whole queue.
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE" || exit 2
LOG="${SPEC_ELAB_WORK:-$HOME/e2e-runs/spec-elaboration-20261120}/queue-4.log"
mkdir -p "$(dirname "$LOG")"
step() { printf '\n===== %s  %s =====\n' "$(date '+%H:%M:%S')" "$1" >> "$LOG"; }
run() { "$@" >> "$LOG" 2>&1; code=$?; printf -- '--- exit %s: %s\n' "$code" "$*" >> "$LOG"; return $code; }

grade() {  # round
    step "round $1: counts, judge, board"
    run python3 -I grade.py counts "$1"
    run python3 -I grade.py judge "$1" --parallel=3
    run python3 -I grade.py judge "$1" --parallel=3     # a second invocation picks up any verdict the first lost
    run python3 -I grade.py board "$1"
}

subjects() {  # round, arms, drivers
    step "round $1: subjects ($2 on $3)"
    if ! run python3 -I run.py "$1" "--arms=$2" "--drivers=$3" --parallel=4 --timeout=2700; then
        step "STOPPED: round $1 did not start or did not finish (see the lines above)"
        exit 4
    fi
    step "round $1: leak check"
    if ! run python3 -I grade.py leaks "$1"; then
        step "STOPPED: a session in $1 reached outside its own directory and profile"
        exit 3
    fi
    grade "$1"
}

step "round 4, as it ran: the leak report again (paths that do not exist no longer count), then its verdicts"
run python3 -I grade.py leaks round-4
grade round-4

subjects round-4c A-single,D-enumerated-only sol-medium
subjects round-5 F-guarded,L-lenses-once,P-shiploop-spec sonnet-high,sol-medium
run python3 -I timeline.py round-4 round-4c round-5

step "judge checks on round 4: a second Opus draw, and gpt-6.2-astra (calibrated on cal-1 first)"
run python3 -I grade.py judge cal-1 --tag=gpt --judge=astra --parallel=2
run python3 -I grade.py judge round-4 --tag=r2 --parallel=3
run python3 -I grade.py judge round-4 --tag=r2 --parallel=3
run python3 -I grade.py judge round-4 --tag=gpt --judge=astra --parallel=3
run python3 -I grade.py judge round-4 --tag=gpt --judge=astra --parallel=3
run python3 -I grade.py board round-4 --tag=r2
run python3 -I grade.py board round-4 --tag=gpt
run python3 -I grade.py agree round-4 --tags=r2,gpt

step "clause audit: the clean specifications (round 4 Sonnet, round 4c Sol, round 5 F and L)"
run python3 -I grade.py audit round-4 --drivers=sonnet-high --parallel=3
run python3 -I grade.py audit round-4 --drivers=sonnet-high --parallel=3
run python3 -I grade.py audit-board round-4
run python3 -I grade.py audit round-4c --parallel=3
run python3 -I grade.py audit round-4c --parallel=3
run python3 -I grade.py audit-board round-4c
run python3 -I grade.py audit round-5 --arms=F-guarded,L-lenses-once --parallel=3
run python3 -I grade.py audit round-5 --arms=F-guarded,L-lenses-once --parallel=3
run python3 -I grade.py audit-board round-5
step "queue finished"
