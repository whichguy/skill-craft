#!/bin/sh
# usage: run1.sh <prompt-stem> <k>
D="${EXP_DIR:-$(pwd)}"
SK="${SHIPLOOP_ROOT:?set SHIPLOOP_ROOT to skills/shiploop}"
case "$1" in
  *current-linked*) cd "$SK" && claude -p --model sonnet --tools Read Grep Glob --allowedTools Read Grep Glob \
       --output-format stream-json --verbose < "$D/prompts/$1.txt" > "$D/out/$1_$2.jsonl" 2> "$D/out/$1_$2.err";;
  *) cd "$D" && claude -p --model sonnet --tools "" < "$D/prompts/$1.txt" > "$D/out/$1_$2.md" 2> "$D/out/$1_$2.err";;
esac
