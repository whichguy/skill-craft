#!/usr/bin/env bash
# Run all or one group of hermetic tests (no installed host or live engine).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$root"

group=all
list_only=0
usage() {
  printf 'Usage: bash test/run-all.sh [--group all|smoke|core|shiploop|shiploop-1|shiploop-2|shiploop-3] [--list]\n'
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
  all|smoke|core|shiploop|shiploop-1|shiploop-2|shiploop-3) ;;
  *) usage >&2; exit 64 ;;
esac

fail=0
run() {
  local suite_group="$1" name="$2"
  shift 2
  if [[ "$suite_group" == smoke || "$suite_group" == shiploop-[123] ]]; then
    # Subset/scheduling aliases are excluded from all, whose shiploop entry
    # remains the one full serial runner.
    [[ "$group" == "$suite_group" ]] || return 0
  else
    [[ "$group" == all || "$group" == "$suite_group" ||
       ( "$group" == smoke && "$suite_group" == core ) ]] || return 0
  fi
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
run core ask-agent-worktree-harness python3 test/ask-agent-worktree-harness.test.py
run core skill-interop-hygiene bash test/skill-interop-hygiene.test.sh
run core sync-plugin-views bash test/sync-plugin-views.test.sh
run core native-marketplace-adapters bash test/native-marketplace-adapters.test.sh
run core marketplace-package python3 test/marketplace-package.test.py
run core marketplace-host-isolation python3 test/marketplace-host-isolation.test.py
run core installed-skill-invocation python3 test/installed-skill-invocation.test.py
run core prompt-marketplace-contract python3 test/prompt-marketplace-contract.test.py
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
run smoke shiploop-smoke bash test/shiploop.test.sh --smoke
# These aliases are CI scheduling targets. They derive from the same ordered
# inventory as the full runner and are deliberately excluded from all.
run shiploop-1 shiploop-1 bash test/shiploop.test.sh --shard 1/3
run shiploop-2 shiploop-2 bash test/shiploop.test.sh --shard 2/3
run shiploop-3 shiploop-3 bash test/shiploop.test.sh --shard 3/3

[[ "$list_only" -eq 0 ]] || exit 0

if [[ "$fail" -ne 0 ]]; then
  printf 'run-all.sh: FAILED\n' >&2
  exit 1
fi
printf 'run-all.sh: PASS (%s hermetic group selection)\n' "$group"
