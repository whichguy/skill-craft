#!/usr/bin/env bash
# Counterexample: -e is ignored within a function used as an if condition.
set -euo pipefail

audit=$1

case $- in
  *e*) ;;
  *) exit 70 ;;
esac
case $- in
  *u*) ;;
  *) exit 71 ;;
esac
if set -o | grep -E '^pipefail[[:space:]]+on$' >/dev/null; then
  :
else
  exit 72
fi

conditional_function() {
  false
  printf 'continued-after-false\n' >"$audit"
}

if conditional_function; then
  printf 'if-branch-success\n'
else
  printf 'if-branch-failure\n'
fi
