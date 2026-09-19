#!/usr/bin/env bash
# Mutant: behavior appears correct but the owned temporary directory leaks.
set -euo pipefail

audit=$1
probe=$2
workspace=$(mktemp -d "${TMPDIR:-/tmp}/shiploop-bash-pipeline.XXXXXX")
printf '%s\n' "$workspace" >"$audit"

if "$probe" | cat >/dev/null; then
  printf 'unexpected-success\n'
  exit 0
else
  status=$?
  printf 'handled-pipeline-status=%s\n' "$status"
  exit "$status"
fi
