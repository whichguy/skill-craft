#!/usr/bin/env bash
# Fail if monorepo re-introduces a leaf that skill-craft-market pins externally.
# Current external pin: lennox-s40 → whichguy/lennox-s40 (standalone wins).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
fail() { printf 'dual-body-guard.test.sh: FAIL %s\n' "$*" >&2; exit 1; }

# Names that must not appear under skills/ or plugins/ in this monorepo.
external_leaves=(lennox-s40)

for leaf in "${external_leaves[@]}"; do
  [[ ! -e "$root/skills/$leaf" ]] || fail "skills/$leaf must not exist (external SoT)"
  [[ ! -e "$root/plugins/$leaf" ]] || fail "plugins/$leaf must not exist (external SoT)"
done

printf 'dual-body-guard.test.sh: PASS\n'
