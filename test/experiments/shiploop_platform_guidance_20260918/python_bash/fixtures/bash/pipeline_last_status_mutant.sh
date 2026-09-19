#!/usr/bin/env bash
# Mutant: without pipefail, a successful final command hides probe failure.
set -eu

audit=$1
probe=$2
workspace=

# shellcheck disable=SC2329 # The EXIT trap invokes cleanup.
cleanup() {
  if [ -n "${workspace:-}" ] && [ -d "$workspace" ]; then
    rm -rf -- "$workspace"
  fi
}

trap cleanup EXIT
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
