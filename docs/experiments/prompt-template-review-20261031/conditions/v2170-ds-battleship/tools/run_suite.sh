#!/bin/bash
# Usage: run_suite.sh <workdir> <outfile>   -> exit 0 only if all three suites pass
W="$1"; OUT="$2"; : > "$OUT"; rc=0
cd "$W" || exit 99
for cmd in "node --test" "node --test browser-check/page.js" "node --test system-check/system.js"; do
  echo "### $cmd" >> "$OUT"
  timeout 240 $cmd >> "$OUT" 2>&1
  e=$?
  echo "### exit=$e" >> "$OUT"
  if [ $e -ne 0 ]; then rc=1; fi
done
exit $rc
