#!/bin/bash
# Rerun one trial (same prompt) until it returns a real plan: at least 150 words, up to 3 attempts.
cd "${EXP_DIR:-$(pwd)}"
f="out/$1_$2.md"
for a in 1 2 3; do
  [ "$(wc -w < "$f" 2>/dev/null || echo 0)" -ge 150 ] && break
  ./run.sh "$1" "$2"
done
echo "$1_$2 $(wc -w < "$f")"
