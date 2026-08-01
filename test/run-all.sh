#!/usr/bin/env bash
# Run hermetic skill-craft tests (no network, stubbed host CLIs).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$root"

fail=0
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

run skill-interop-hygiene bash test/skill-interop-hygiene.test.sh
run sync-plugin-views bash test/sync-plugin-views.test.sh
run skill-frontmatter node test/skill-frontmatter.test.js
run scaffold-skill bash test/scaffold-skill.test.sh
run marketplace-run bash test/marketplace-run.test.sh
run install-targets bash test/install-targets.test.sh
run install-arbitrary-skill bash test/install-arbitrary-skill.test.sh
run hermes-binding bash test/hermes-binding.test.sh

if [[ "$fail" -ne 0 ]]; then
  printf 'run-all.sh: FAILED\n' >&2
  exit 1
fi
printf 'run-all.sh: PASS (all skill-craft hermetic tests)\n'
