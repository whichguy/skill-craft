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
GBO=$(python3 "$CLI" goal-body --plan "$TMP")
if printf '%s\n' "$GBO" | grep -q 'Base ref:'; then ok goal_body; else bad goal_body; fi
if printf '%s\n' "$GBO" | grep -q 'FINITE residual'; then ok goal_body_finite; else bad goal_body_finite; fi
if printf '%s\n' "$GBO" | grep -q 'complete+landed'; then ok goal_body_success_exit; else bad goal_body_success_exit; fi
if printf '%s\n' "$GBO" | grep -q 'stopped (max-cycles)'; then ok goal_body_max_cycles; else bad goal_body_max_cycles; fi
if printf '%s\n' "$GBO" | grep -qi 'residual×2\|residualx2\|two consecutive clean'; then ok goal_body_residual_x2; else bad goal_body_residual_x2; fi
if printf '%s\n' "$GBO" | grep -qE 'stopped\s*\(\.\.\.\)\+landed'; then ok goal_body_stopped_halt; else bad goal_body_stopped_halt; fi
if printf '%s\n' "$GBO" | grep -q 'Never unlimited ralph'; then ok goal_body_no_unlimited_ralph; else bad goal_body_no_unlimited_ralph; fi
rm -f "$TMP"

# Custom Max review-converge rounds must flow into goal-body (not always default 12)
TMPM=$(mktemp)
cat >"$TMPM" <<'EOF'
## Review Coverage

| Field | Value |
|-------|--------|
| Base ref | abcdef1234567890deadbeef |
| Target paths | src/foo.ts |
| Test command | npm test |
| Materiality bar | material (P0/P1) |
| Driver | review-converge under /goal |
| Max review-converge rounds | 8 hard cap |

1. Forward audit of specs to code.
2. Reverse audit of code vs base.
two consecutive clean residual rounds with green suite
EOF
GBO8=$(python3 "$CLI" goal-body --plan "$TMPM")
if printf '%s\n' "$GBO8" | grep -q 'Max rounds: 8'; then ok goal_body_custom_max; else bad goal_body_custom_max; fi
if printf '%s\n' "$GBO8" | grep -q 'rounds ≥ 8'; then ok goal_body_custom_max_branch; else bad goal_body_custom_max_branch; fi
rm -f "$TMPM"

if ! echo '# bare' | python3 "$CLI" validate - >/dev/null 2>&1; then ok validate_missing; else bad validate_missing; fi

# Unfilled template (incl. example waiver line) must NOT validate as ok
TERR=$(python3 "$CLI" validate "$ROOT/skills/review-coverage/references/review_coverage.md" 2>&1 >/dev/null || true)
if ! python3 "$CLI" validate "$ROOT/skills/review-coverage/references/review_coverage.md" >/dev/null 2>&1; then
  ok template_not_valid_plan
else
  bad template_not_valid_plan
fi
if printf '%s\n' "$TERR" | grep -qi 'placeholder waiver'; then ok template_placeholder_stderr; else bad template_placeholder_stderr; fi
if ! python3 "$CLI" validate "$ROOT/skills/review-coverage/references/review_coverage.short.md" >/dev/null 2>&1; then
  ok short_template_not_valid_plan
else
  bad short_template_not_valid_plan
fi

# Real waiver (non-placeholder reason) validates; goal-body refuses with clear err
TMPW=$(mktemp)
cat >"$TMPW" <<'EOF'
## Review Coverage

None — residual loop waived: docs-only one-liner plan
EOF
if python3 "$CLI" validate "$TMPW" >/dev/null; then ok waiver_validate; else bad waiver_validate; fi
# goal-body exits 1 on waiver; capture stderr+stdout without pipefail masking the grep
gbo=$(python3 "$CLI" goal-body --plan "$TMPW" 2>&1 || true)
if printf '%s\n' "$gbo" | grep -qi 'waived'; then ok waiver_goal_body_msg; else bad waiver_goal_body_msg; fi
# waived path must not print a goal body (only error)
if ! printf '%s\n' "$gbo" | grep -q 'FINITE residual'; then ok waiver_no_goal_body; else bad waiver_no_goal_body; fi
rm -f "$TMPW"

# Invalid Driver must fail validate with clear stderr
TMPD=$(mktemp)
cat >"$TMPD" <<'EOF'
## Review Coverage

| Field | Value |
|-------|--------|
| Base ref | abcdef1234567890deadbeef |
| Target paths | src/foo.ts |
| Test command | npm test |
| Materiality bar | material (P0/P1) |
| Driver | some-other-tool-only |

1. Forward audit of specs to code.
2. Reverse audit of code vs base.
two consecutive clean residual rounds with green suite
EOF
DERR=$(python3 "$CLI" validate "$TMPD" 2>&1 >/dev/null || true)
if ! python3 "$CLI" validate "$TMPD" >/dev/null 2>&1; then ok bad_driver_rejects; else bad bad_driver_rejects; fi
if printf '%s\n' "$DERR" | grep -qi 'Driver must mention'; then ok bad_driver_stderr; else bad bad_driver_stderr; fi
rm -f "$TMPD"

# Missing forward/reverse instructions must fail validate
TMPFR=$(mktemp)
cat >"$TMPFR" <<'EOF'
## Review Coverage

| Field | Value |
|-------|--------|
| Base ref | abcdef1234567890deadbeef |
| Target paths | src/foo.ts |
| Test command | npm test |
| Materiality bar | material (P0/P1) |
| Driver | review-converge under /goal |

two consecutive clean residual rounds with green suite
EOF
if ! python3 "$CLI" validate "$TMPFR" >/dev/null 2>&1; then ok missing_forward_reverse; else bad missing_forward_reverse; fi
rm -f "$TMPFR"

# Fenced-only ## Review Coverage example must not count as a filled section
TMPF=$(mktemp)
cat >"$TMPF" <<'EOF'
# plan

```markdown
## Review Coverage
| Base ref | abcdef1234567890deadbeef |
```
EOF
if ! python3 "$CLI" validate "$TMPF" >/dev/null 2>&1; then ok fenced_only_rejects; else bad fenced_only_rejects; fi
rm -f "$TMPF"

# incomplete plan: goal-body fails closed with clear error (not waived)
TMPI=$(mktemp)
echo '# bare plan no section' >"$TMPI"
IBODY=$(python3 "$CLI" goal-body --plan "$TMPI" 2>&1 || true)
if printf '%s\n' "$IBODY" | grep -qi 'missing filled Review Coverage\|missing ## Review Coverage'; then ok incomplete_goal_body_err; else bad incomplete_goal_body_err; fi
rm -f "$TMPI"

# template subcommand prints real SoT H2
if python3 "$CLI" template | head -1 | grep -q '^## Review Coverage'; then ok template_cmd; else bad template_cmd; fi
if python3 "$CLI" template --short | head -1 | grep -q '^## Review Coverage'; then ok template_short_cmd; else bad template_short_cmd; fi

if [[ -f "$ROOT/plugins/review-coverage/.claude-plugin/plugin.json" ]]; then ok plugin_json; else bad plugin_json; fi
if "$ROOT/scripts/sync-plugin-views.sh" --check review-coverage 2>/dev/null \
  || "$ROOT/scripts/sync-plugin-views.sh" --check 2>/dev/null | grep -q review-coverage; then
  # --check may be global; ensure plugin skill tree exists
  [[ -f "$ROOT/plugins/review-coverage/skills/review-coverage/SKILL.md" ]] && ok plugin_synced || bad plugin_synced
else
  [[ -f "$ROOT/plugins/review-coverage/skills/review-coverage/SKILL.md" ]] && ok plugin_synced || bad plugin_synced
fi
# Content equality: plugin view must match source for skill leaf files
if diff -q "$ROOT/skills/review-coverage/scripts/review-coverage" \
  "$ROOT/plugins/review-coverage/skills/review-coverage/scripts/review-coverage" >/dev/null; then
  ok plugin_script_match
else
  bad plugin_script_match
fi
if diff -q "$ROOT/skills/review-coverage/SKILL.md" \
  "$ROOT/plugins/review-coverage/skills/review-coverage/SKILL.md" >/dev/null; then
  ok plugin_skill_match
else
  bad plugin_skill_match
fi
if diff -q "$ROOT/skills/review-coverage/references/review_coverage.md" \
  "$ROOT/plugins/review-coverage/skills/review-coverage/references/review_coverage.md" >/dev/null; then
  ok plugin_template_match
else
  bad plugin_template_match
fi

# Field-table values must win over fenced Objective paste examples (no pollution)
TMPPOL=$(mktemp)
cat >"$TMPPOL" <<'EOF'
## Review Coverage

| Field | Value |
|-------|--------|
| Base ref | abcdef1234567890deadbeef |
| Target paths | src/foo.ts |
| Test command | npm test |
| Materiality bar | material (P0/P1) |
| Driver | review-converge under /goal |

### Objective (paste into /goal)

```text
Base ref: <BASE_REF>.
Test command: <CMD>.
Driver: review-converge under /goal — exactly ONE review-converge round per turn
Forward specs→code.
Reverse diff vs base.
two consecutive clean residual rounds
```
EOF
if python3 "$CLI" validate "$TMPPOL" >/dev/null; then ok field_table_wins_validate; else bad field_table_wins_validate; fi
POL_GB=$(python3 "$CLI" goal-body --plan "$TMPPOL")
if printf '%s\n' "$POL_GB" | grep -q 'Base ref: abcdef1234567890deadbeef'; then ok field_table_wins_base; else bad field_table_wins_base; fi
if printf '%s\n' "$POL_GB" | grep -q 'Test command: npm test'; then ok field_table_wins_cmd; else bad field_table_wins_cmd; fi
# Driver must not double-append the ONE-round phrase
if ! printf '%s\n' "$POL_GB" | grep -q 'exactly ONE review-converge round per turn — exactly ONE'; then
  ok driver_no_double_append
else
  bad driver_no_double_append
fi
rm -f "$TMPPOL"

# Angle-bracket placeholders with trailing punctuation are still placeholders
TMPP=$(mktemp)
cat >"$TMPP" <<'EOF'
## Review Coverage

| Field | Value |
|-------|--------|
| Base ref | <BASE_REF>. |
| Target paths | src/foo.ts |
| Test command | <CMD>. |
| Materiality bar | material (P0/P1) |
| Driver | review-converge under /goal |

1. Forward audit of specs to code.
2. Reverse audit of code vs base.
two consecutive clean residual rounds with green suite
EOF
if ! python3 "$CLI" validate "$TMPP" >/dev/null 2>&1; then ok placeholder_trailing_punct; else bad placeholder_trailing_punct; fi
PERR=$(python3 "$CLI" validate "$TMPP" 2>&1 >/dev/null || true)
if printf '%s\n' "$PERR" | grep -qi 'placeholder'; then ok placeholder_trailing_punct_stderr; else bad placeholder_trailing_punct_stderr; fi
rm -f "$TMPP"

# Full/short shipped templates must fail closed (never validate ok as filled plans)
if ! python3 "$CLI" validate "$ROOT/skills/review-coverage/references/review_coverage.md" >/dev/null 2>&1; then
  ok full_template_fail_closed
else
  bad full_template_fail_closed
fi
if ! python3 "$CLI" validate "$ROOT/skills/review-coverage/references/review_coverage.short.md" >/dev/null 2>&1; then
  ok short_template_fail_closed
else
  bad short_template_fail_closed
fi
# goal-body on templates must fail (not emit polluted placeholders)
if ! python3 "$CLI" goal-body --plan "$ROOT/skills/review-coverage/references/review_coverage.md" >/dev/null 2>&1; then
  ok full_template_no_goal_body
else
  bad full_template_no_goal_body
fi

echo "======== review-coverage: PASS=$PASS FAIL=$FAIL ========"
[[ "$FAIL" -eq 0 ]]
