#!/bin/sh
D="${EXP_DIR:-$(pwd)}"
fx=$(echo $1 | cut -d_ -f2)
cd "$D/fx/$fx" && claude -p --model sonnet --tools Read Grep Glob --allowedTools Read Grep Glob \
  --add-dir "${SHIPLOOP_ROOT:?set SHIPLOOP_ROOT to skills/shiploop}" --output-format stream-json --verbose \
  < "$D/$1.txt" > "$D/out2/$1_$2.jsonl" 2> "$D/out2/$1_$2.err"
