#!/usr/bin/env bash
# Require the three Cursor-imported skills and run each skill's test suite.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
fail=0

require_skill() {
  local name="$1"
  local path="$HOME/.cursor/skills/$name"
  if [[ ! -f "$path/SKILL.md" ]]; then
    echo "FAIL missing imported skill: $path/SKILL.md" >&2
    fail=1
    return 1
  fi
  echo "PASS imported_$name"
}

require_skill advisors
require_skill review-plan
require_skill review-coverage

if [[ "$fail" -ne 0 ]]; then
  echo "cursor-imported-skills: missing imports" >&2
  exit 1
fi

run() {
  local name="$1"
  shift
  printf '==> %s\n' "$name"
  if "$@"; then
    printf 'OK  %s\n' "$name"
  else
    printf 'FAIL %s\n' "$name" >&2
    fail=1
  fi
}

run advisors bash "$root/test/advisors.test.sh"
run review-plan bash "$root/test/review-plan.test.sh"
run review-coverage-source bash "$root/test/review-coverage.test.sh"

CURSOR_CLI="$HOME/.cursor/skills/review-coverage/scripts/review-coverage"
if python3 "$CURSOR_CLI" check-install >/dev/null; then
  echo "PASS review-coverage_cursor_cli"
else
  echo "FAIL review-coverage_cursor_cli" >&2
  fail=1
fi

if [[ "$fail" -ne 0 ]]; then
  echo "cursor-imported-skills: FAILED" >&2
  exit 1
fi
echo "cursor-imported-skills: PASS"
