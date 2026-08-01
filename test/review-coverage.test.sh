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
| Repo | /tmp/review-coverage-repo |
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
if [[ "$GBO" == quality\ review\ changes\ and\ consider\ improvements,* ]]; then ok goal_body_static_start; else bad goal_body_static_start; fi
if printf '%s\n' "$GBO" | grep -q 'complete when only trivial changes remain for 2 consecutive cycles'; then ok goal_body_static_complete; else bad goal_body_static_complete; fi
if printf '%s\n' "$GBO" | grep -q "Plan: $TMP"; then ok goal_body_plan; else bad goal_body_plan; fi
if printf '%s\n' "$GBO" | grep -q 'Base ref: abcdef1234567890deadbeef'; then ok goal_body_base; else bad goal_body_base; fi
if printf '%s\n' "$GBO" | grep -q 'Repo: /tmp/review-coverage-repo'; then ok goal_body_repo; else bad goal_body_repo; fi
if printf '%s\n' "$GBO" | grep -q 'Paths: src/foo.ts'; then ok goal_body_paths; else bad goal_body_paths; fi
if printf '%s\n' "$GBO" | grep -q 'Test: npm test'; then ok goal_body_test; else bad goal_body_test; fi
if printf '%s\n' "$GBO" | grep -q 'Driver: one /review-converge per turn'; then ok goal_body_driver; else bad goal_body_driver; fi
if printf '%s\n' "$GBO" | grep -q 'Max rounds: 12'; then ok goal_body_max_default; else bad goal_body_max_default; fi
if ! printf '%s\n' "$GBO" | grep -q 'FINITE residual\|S1)'; then ok goal_body_no_legacy_procedure; else bad goal_body_no_legacy_procedure; fi
GBO_SLASH=$(python3 "$CLI" goal-body --plan "$TMP" --slash)
if [[ "$GBO_SLASH" == /goal\ quality\ review\ changes* ]]; then ok goal_body_slash; else bad goal_body_slash; fi
if [[ "$(python3 "$CLI" goal-body --plan "$TMP" --slash | head -c 28)" == /goal\ quality\ review\ changes* ]]; then ok goal_body_slash_head; else bad goal_body_slash_head; fi
if [[ "$GBO" != /goal\ * ]]; then ok goal_body_no_slash; else bad goal_body_no_slash; fi
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
rm -f "$TMPM"

if ! echo '# bare' | python3 "$CLI" validate - >/dev/null 2>&1; then ok validate_missing; else bad validate_missing; fi

# Unfilled template (incl. example waiver line) must NOT validate as ok
TERR=$(python3 "$CLI" validate "$ROOT/skills/review-coverage/references/review_coverage.md" 2>&1 >/dev/null || true)
if ! python3 "$CLI" validate "$ROOT/skills/review-coverage/references/review_coverage.md" >/dev/null 2>&1; then
  ok template_not_valid_plan
else
  bad template_not_valid_plan
fi
# Shipped templates fail closed via placeholder fields and/or unfenced placeholder waiver
if printf '%s\n' "$TERR" | grep -qiE 'placeholder|missing .+ field'; then ok template_placeholder_stderr; else bad template_placeholder_stderr; fi
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
# waived path must not print the static goal body (only error)
if ! printf '%s\n' "$gbo" | grep -q 'quality review changes and consider improvements'; then ok waiver_no_goal_body; else bad waiver_no_goal_body; fi
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

# Field-table values must win over fenced /goal command examples (no pollution)
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

### /goal command (test fixture)

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
if printf '%s\n' "$POL_GB" | grep -q 'Test: npm test'; then ok field_table_wins_cmd; else bad field_table_wins_cmd; fi
# Driver is fixed by the canonical binding trailer, not rebuilt from the field.
if printf '%s\n' "$POL_GB" | grep -q 'Driver: one /review-converge per turn'; then
  ok driver_fixed_canonical
else
  bad driver_fixed_canonical
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

if grep -q '^version: 0.2.1$' "$ROOT/skills/review-coverage/SKILL.md"; then ok skill_version; else bad skill_version; fi
if grep -q -- 'goal-body --plan /path/to/plan.md --slash' "$ROOT/skills/review-coverage/SKILL.md"; then ok skill_slash_docs; else bad skill_slash_docs; fi

# --- Verification rows (e)–(h): section-scoped fence-aware waiver ---
FILLED_CORE=$(cat <<'EOF'
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
)

# (e) filled section + fenced waiver example inside section → NOT waived
TMPE=$(mktemp)
cat >"$TMPE" <<EOF
$FILLED_CORE

### Waiver examples (do not activate)

\`\`\`text
None — residual loop waived: example only ignore me
\`\`\`
EOF
if python3 "$CLI" validate "$TMPE" >/dev/null; then ok row_e_validate; else bad row_e_validate; fi
EGB=$(python3 "$CLI" goal-body --plan "$TMPE" 2>&1) || true
if python3 "$CLI" goal-body --plan "$TMPE" >/dev/null 2>&1; then ok row_e_goal_body; else bad row_e_goal_body; fi
if printf '%s\n' "$EGB" | grep -q 'quality review changes and consider improvements'; then ok row_e_body_text; else bad row_e_body_text; fi
if ! printf '%s\n' "$EGB" | grep -qi 'waived'; then ok row_e_not_waived; else bad row_e_not_waived; fi
rm -f "$TMPE"

# (f) waiver with no Review Coverage section → missing section, not waived
TMPF=$(mktemp)
cat >"$TMPF" <<'EOF'
# some plan

None — residual loop waived: docs-only without a section
EOF
FERR=$(python3 "$CLI" validate "$TMPF" 2>&1 >/dev/null || true)
if ! python3 "$CLI" validate "$TMPF" >/dev/null 2>&1; then ok row_f_validate; else bad row_f_validate; fi
if printf '%s\n' "$FERR" | grep -qi 'missing ## Review Coverage'; then ok row_f_missing_msg; else bad row_f_missing_msg; fi
FGB=$(python3 "$CLI" goal-body --plan "$TMPF" 2>&1 || true)
if ! python3 "$CLI" goal-body --plan "$TMPF" >/dev/null 2>&1; then ok row_f_goal_body; else bad row_f_goal_body; fi
if printf '%s\n' "$FGB" | grep -qi 'missing ## Review Coverage\|missing filled Review Coverage'; then ok row_f_gb_missing; else bad row_f_gb_missing; fi
if ! printf '%s\n' "$FGB" | grep -qi 'residual waived'; then ok row_f_not_waived_msg; else bad row_f_not_waived_msg; fi
rm -f "$TMPF"

# (g) fenced waiver outside section, plan otherwise filled → not a waiver
TMPG=$(mktemp)
cat >"$TMPG" <<EOF
# plan intro

\`\`\`text
None — residual loop waived: out of section fence
\`\`\`

$FILLED_CORE
EOF
if python3 "$CLI" validate "$TMPG" >/dev/null; then ok row_g_validate; else bad row_g_validate; fi
if python3 "$CLI" goal-body --plan "$TMPG" >/dev/null 2>&1; then ok row_g_goal_body; else bad row_g_goal_body; fi
GGB=$(python3 "$CLI" goal-body --plan "$TMPG")
if printf '%s\n' "$GGB" | grep -q 'quality review changes and consider improvements'; then ok row_g_body; else bad row_g_body; fi
rm -f "$TMPG"

# (h) unfenced in-section waiver AND filled fields → conflict
TMPH=$(mktemp)
cat >"$TMPH" <<EOF
$FILLED_CORE

None — residual loop waived: should conflict with filled fields
EOF
HERR=$(python3 "$CLI" validate "$TMPH" 2>&1 >/dev/null || true)
if ! python3 "$CLI" validate "$TMPH" >/dev/null 2>&1; then ok row_h_validate; else bad row_h_validate; fi
if printf '%s\n' "$HERR" | grep -qi 'conflict'; then ok row_h_conflict_msg; else bad row_h_conflict_msg; fi
if ! python3 "$CLI" goal-body --plan "$TMPH" >/dev/null 2>&1; then ok row_h_goal_body; else bad row_h_goal_body; fi
HGB=$(python3 "$CLI" goal-body --plan "$TMPH" 2>&1 || true)
if printf '%s\n' "$HGB" | grep -qi 'conflict'; then ok row_h_gb_conflict; else bad row_h_gb_conflict; fi
rm -f "$TMPH"

# --- Rows (i)–(j): unreadable input exit 2 ---
MISS="/nonexistent/review-coverage-plan-$$.md"
IERR=$(python3 "$CLI" validate "$MISS" 2>&1 >/dev/null || true)
IEC=$(python3 "$CLI" validate "$MISS" >/dev/null 2>&1; echo $?)
if [[ "$IEC" -eq 2 ]]; then ok row_i_validate_exit2; else bad row_i_validate_exit2; fi
if printf '%s\n' "$IERR" | grep -q "error: cannot read $MISS:"; then ok row_i_validate_msg; else bad row_i_validate_msg; fi
if ! printf '%s\n' "$IERR" | grep -qi Traceback; then ok row_i_no_traceback; else bad row_i_no_traceback; fi
IGEC=$(python3 "$CLI" goal-body --plan "$MISS" >/dev/null 2>&1; echo $?)
if [[ "$IGEC" -eq 2 ]]; then ok row_i_goal_body_exit2; else bad row_i_goal_body_exit2; fi

# directory path
DIRF=$(mktemp -d)
JERR=$(python3 "$CLI" validate "$DIRF" 2>&1 >/dev/null || true)
JEC=$(python3 "$CLI" validate "$DIRF" >/dev/null 2>&1; echo $?)
if [[ "$JEC" -eq 2 ]]; then ok row_j_validate_exit2; else bad row_j_validate_exit2; fi
if printf '%s\n' "$JERR" | grep -q "error: cannot read $DIRF:"; then ok row_j_validate_msg; else bad row_j_validate_msg; fi
if ! printf '%s\n' "$JERR" | grep -qi Traceback; then ok row_j_no_traceback; else bad row_j_no_traceback; fi
rmdir "$DIRF"

# --- Row (k): H2-only heading contract ---
TMPH1=$(mktemp)
cat >"$TMPH1" <<'EOF'
# Review Coverage

| Field | Value |
|-------|--------|
| Base ref | abcdef1234567890deadbeef |
| Target paths | src/foo.ts |
| Test command | npm test |
| Materiality bar | material (P0/P1) |
| Driver | review-converge under /goal |

1. Forward audit
2. Reverse audit
two consecutive clean residual rounds
EOF
if ! python3 "$CLI" validate "$TMPH1" >/dev/null 2>&1; then ok row_k_h1_rejects; else bad row_k_h1_rejects; fi
rm -f "$TMPH1"

TMPH3=$(mktemp)
cat >"$TMPH3" <<'EOF'
### Review Coverage

| Field | Value |
|-------|--------|
| Base ref | abcdef1234567890deadbeef |
| Target paths | src/foo.ts |
| Test command | npm test |
| Materiality bar | material (P0/P1) |
| Driver | review-converge under /goal |

1. Forward audit
2. Reverse audit
two consecutive clean residual rounds
EOF
if ! python3 "$CLI" validate "$TMPH3" >/dev/null 2>&1; then ok row_k_h3_rejects; else bad row_k_h3_rejects; fi
rm -f "$TMPH3"

# Exit-code contract documented in SKILL.md
if grep -qE 'exit code 0|exits 0|exit 0' "$ROOT/skills/review-coverage/SKILL.md" \
  && grep -qE 'exit code 1|exits 1|exit 1' "$ROOT/skills/review-coverage/SKILL.md" \
  && grep -qE 'exit code 2|exits 2|exit 2' "$ROOT/skills/review-coverage/SKILL.md"; then
  ok skill_exit_codes_docs
else
  bad skill_exit_codes_docs
fi
if grep -q '## Review Coverage' "$ROOT/skills/review-coverage/SKILL.md" \
  && grep -qi 'H2\|level-2\|only.*## ' "$ROOT/skills/review-coverage/SKILL.md"; then
  ok skill_h2_contract_docs
else
  bad skill_h2_contract_docs
fi

echo "======== review-coverage: PASS=$PASS FAIL=$FAIL ========"
[[ "$FAIL" -eq 0 ]]
