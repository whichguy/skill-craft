#!/usr/bin/env bash
# Run all or one group of hermetic tests (no installed host or live engine).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$root"

group=all
list_only=0
usage() {
  printf 'Usage: bash test/run-all.sh [--group all|core|shiploop] [--list]\n'
  printf 'Default: all hermetic groups. External tests: bash test/run-integration.sh --help\n'
}
while [[ $# -gt 0 ]]; do
  case "$1" in
    --group)
      [[ $# -ge 2 ]] || { usage >&2; exit 64; }
      group="$2"
      shift 2
      ;;
    --list) list_only=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 64 ;;
  esac
done
case "$group" in
  all|core|shiploop) ;;
  *) usage >&2; exit 64 ;;
esac

fail=0
run() {
  local suite_group="$1" name="$2"
  shift 2
  [[ "$group" == all || "$group" == "$suite_group" ]] || return 0
  if [[ "$list_only" -eq 1 ]]; then
    printf '%s\t%s\t' "$suite_group" "$name"
    printf '%q ' "$@"
    printf '\n'
    return 0
  fi
  printf '==> %s\n' "$name"
  if "$@"; then
    printf 'OK  %s\n' "$name"
  else
    printf 'FAIL %s\n' "$name" >&2
    fail=1
  fi
}

# One explicit catalog drives both listing and execution. Keep external host
# integrations out of this catalog; an unavailable host is not a skipped pass.
run core test-groups python3 test/test-groups.test.py
run core integration-boundaries python3 test/integration-boundaries.test.py
run core skill-interop-hygiene bash test/skill-interop-hygiene.test.sh
run core sync-plugin-views bash test/sync-plugin-views.test.sh
run core native-marketplace-adapters bash test/native-marketplace-adapters.test.sh
run core skill-frontmatter node test/skill-frontmatter.test.js
run core scaffold-skill bash test/scaffold-skill.test.sh
run core marketplace-run bash test/marketplace-run.test.sh
run core install-targets bash test/install-targets.test.sh
run core install-arbitrary-skill bash test/install-arbitrary-skill.test.sh
run core hermes-binding bash test/hermes-binding.test.sh
run core install-status-uninstall bash test/install-status-uninstall.test.sh
run core devloop-run bash test/devloop-run.test.sh
run core evidence-gates bash test/evidence-gates.test.sh
run core improve bash test/improve.test.sh
run core improve-plugin python3 test/improve-plugin.test.py
run core shiploop-testkit bash test/shiploop-testkit.test.sh
run core review-coverage bash test/review-coverage.test.sh
run core dual-body-guard bash test/dual-body-guard.test.sh
# shiploop.test.sh owns the full action walk. The old walk-journal entrypoint
# remains available for direct calls, but must not run again in this aggregate.
run shiploop shiploop bash test/shiploop.test.sh

[[ "$list_only" -eq 0 ]] || exit 0

if [[ "$fail" -ne 0 ]]; then
  printf 'run-all.sh: FAILED\n' >&2
  exit 1
fi
printf 'run-all.sh: PASS (%s hermetic group selection)\n' "$group"
