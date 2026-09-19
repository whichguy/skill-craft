#!/usr/bin/env bash
# Mutant: pipefail is present, but direct execution prevents recovery reporting.
set -euo pipefail

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

"$probe" | cat >/dev/null
status=$?
printf 'handled-pipeline-status=%s\n' "$status"
exit "$status"
