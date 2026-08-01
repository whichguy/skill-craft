#!/usr/bin/env bash
# Hermetic smoke for review-coverage skill package.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLI="$ROOT/skills/review-coverage/scripts/review-coverage"
PASS=0
FAIL=0

ok() { echo "PASS $1"; PASS=$((PASS + 1)); }
bad() { echo "FAIL $1"; FAIL=$((FAIL + 1)); }

[[ -f "$ROOT/skills/review-coverage/SKILL.md" ]] && ok skill_md || bad skill_md
[[ -f "$ROOT/skills/review-coverage/references/review_coverage.md" ]] && ok template || bad template
head -1 "$ROOT/skills/review-coverage/references/review_coverage.md" | grep -q '^## Review Coverage' && ok h2 || bad h2
! grep -q '^## Post-Implementation Residual Loop' "$ROOT/skills/review-coverage/references/review_coverage.md" && ok no_legacy_h2 || bad no_legacy_h2

python3 "$CLI" check-install >/dev/null && ok check_install || bad check_install

TMP=$(mktemp)
cat >"$TMP" <<'EOF'
## Review Coverage

| Field | Value |
|-------|--------|
| Base ref | abcdef1234567890deadbeef |
| Target paths | src/foo.ts |
| Test command | npm test |
| Materiality bar | material (P0/P1) |
| Driver | review-converge under /goal |

1. Forward audit of specs to code.
2. Reverse audit of code vs base.
two consecutive clean residual rounds with green suite
EOF
if python3 "$CLI" validate "$TMP" >/dev/null; then ok validate_ok; else bad validate_ok; fi
if python3 "$CLI" goal-body --plan "$TMP" | grep -q 'Base ref:'; then ok goal_body; else bad goal_body; fi
rm -f "$TMP"

if ! echo '# bare' | python3 "$CLI" validate - >/dev/null 2>&1; then ok validate_missing; else bad validate_missing; fi

if [[ -f "$ROOT/plugins/review-coverage/.claude-plugin/plugin.json" ]]; then ok plugin_json; else bad plugin_json; fi
if "$ROOT/scripts/sync-plugin-views.sh" --check review-coverage 2>/dev/null \
  || "$ROOT/scripts/sync-plugin-views.sh" --check 2>/dev/null | grep -q review-coverage; then
  # --check may be global; ensure plugin skill tree exists
  [[ -f "$ROOT/plugins/review-coverage/skills/review-coverage/SKILL.md" ]] && ok plugin_synced || bad plugin_synced
else
  [[ -f "$ROOT/plugins/review-coverage/skills/review-coverage/SKILL.md" ]] && ok plugin_synced || bad plugin_synced
fi

echo "======== review-coverage: PASS=$PASS FAIL=$FAIL ========"
[[ "$FAIL" -eq 0 ]]
