#!/bin/sh
D="${EXP_DIR:-$(pwd)}"
fx=$(echo $1 | cut -d_ -f1)
cd "$D/fx7/$fx" && claude -p --model sonnet --tools Read Grep Glob --allowedTools Read Grep Glob \
  --add-dir "${SHIPLOOP_ROOT:-${SHIPLOOP_ROOT:-../../../../skills/shiploop}}" --output-format stream-json --verbose \
  < "$D/prompts7/$1.txt" > "$D/out7/$1_$2.jsonl" 2> "$D/out7/$1_$2.err"
