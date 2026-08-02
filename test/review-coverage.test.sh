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
TMP_ABS=$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$TMP")
# Exact STATIC from CLI constant (never hand-copy older wording)
STATIC=$(python3 -c "
import runpy, sys
m = runpy.run_path(sys.argv[1], run_name='rc')
print(m['STATIC_GOAL_LOGIC'], end='')
" "$CLI")
if [[ "$GBO" == "$STATIC".* ]]; then ok goal_body_static_exact; else bad goal_body_static_exact; fi
if [[ "$GBO" == quality\ review\ changes\ and\ consider\ improvements,* ]]; then ok goal_body_static_start; else bad goal_body_static_start; fi
if printf '%s\n' "$GBO" | grep -q 'complete when only trivial findings remaining for 2 consecutive cycles'; then ok goal_body_static_complete; else bad goal_body_static_complete; fi
if printf '%s\n' "$GBO" | grep -q 'git commit between each iteration with a verbose message with key learnings'; then ok goal_body_commit_each_iteration; else bad goal_body_commit_each_iteration; fi
if printf '%s\n' "$GBO" | grep -q 'review the last 10 git commit messages for learnings'; then ok goal_body_review_git_learnings; else bad goal_body_review_git_learnings; fi
if printf '%s\n' "$GBO" | grep -q "Plan: $TMP_ABS"; then ok goal_body_plan_absolute; else bad goal_body_plan_absolute; fi
if printf '%s\n' "$GBO" | grep -q 'Base ref: abcdef1234567890deadbeef'; then ok goal_body_base; else bad goal_body_base; fi
if printf '%s\n' "$GBO" | grep -q 'Repo: /tmp/review-coverage-repo'; then ok goal_body_repo; else bad goal_body_repo; fi
if printf '%s\n' "$GBO" | grep -q 'Target paths: src/foo.ts'; then ok goal_body_paths; else bad goal_body_paths; fi
if printf '%s\n' "$GBO" | grep -q 'Test command: npm test'; then ok goal_body_test; else bad goal_body_test; fi
if printf '%s\n' "$GBO" | grep -q 'Driver: one /review-converge per turn'; then ok goal_body_driver; else bad goal_body_driver; fi
if printf '%s\n' "$GBO" | grep -q 'Max review-converge rounds: 12'; then ok goal_body_max_default; else bad goal_body_max_default; fi
if printf '%s\n' "$GBO" | grep -q 'stopped (max-cycles).*EXIT HALT.*same-error ×3.*no-progress ×3'; then ok goal_body_halt_rules; else bad goal_body_halt_rules; fi
if printf '%s\n' "$GBO" | grep -q 'Ledger: REVIEW_CONVERGE.md.*Log landed'; then ok goal_body_ledger_landed; else bad goal_body_ledger_landed; fi
if printf '%s\n' "$GBO" | grep -q 'only trivial findings remaining'; then ok goal_body_clean_trivial; else bad goal_body_clean_trivial; fi
if ! printf '%s\n' "$GBO" | grep -q 'zero material findings'; then ok goal_body_no_zero_material; else bad goal_body_no_zero_material; fi
if ! printf '%s\n' "$GBO" | grep -qE '(^|[. ])Paths:|(^|[. ])Test:|Max rounds:'; then ok goal_body_no_legacy_labels; else bad goal_body_no_legacy_labels; fi
if ! printf '%s\n' "$GBO" | grep -q 'FINITE residual\|S1)'; then ok goal_body_no_legacy_procedure; else bad goal_body_no_legacy_procedure; fi
GBO_SLASH=$(python3 "$CLI" goal-body --plan "$TMP" --slash)
if [[ "$GBO_SLASH" == "/goal $GBO" ]]; then ok goal_body_slash_exact; else bad goal_body_slash_exact; fi
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
if printf '%s\n' "$GBO8" | grep -q 'Max review-converge rounds: 8'; then ok goal_body_custom_max; else bad goal_body_custom_max; fi
rm -f "$TMPM"

if ! echo '# bare' | python3 "$CLI" validate - >/dev/null 2>&1; then ok validate_missing; else bad validate_missing; fi

# preflight and run-card operate on a real local repository without network access.
PREF_REPO=$(mktemp -d)
git -C "$PREF_REPO" init -q
git -C "$PREF_REPO" -c user.name=review-coverage -c user.email=review@example.invalid commit --allow-empty -qm initial
PREF_BASE=$(git -C "$PREF_REPO" rev-parse HEAD)
PREF_PLAN=$(mktemp)
cat >"$PREF_PLAN" <<EOF
## Review Coverage

| Field | Value |
|-------|--------|
| Base ref | $PREF_BASE |
| Repo | $PREF_REPO |
| Target paths | src/foo.ts |
| Test command | npm test |
| Materiality bar | material (P0/P1) |
| Driver | review-converge under /goal |
| Plan contract | $PREF_PLAN |
| Max review-converge rounds | 7 |

1. Forward audit of specs to code.
2. Reverse audit of code vs base.
two consecutive clean residual rounds with green suite
EOF
PREF_ABS=$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$PREF_PLAN")
PREF_OUT=$(python3 "$CLI" preflight --plan "$PREF_PLAN" 2>&1)
if [[ "$PREF_OUT" == *'preflight: ok'* && "$PREF_OUT" == *"plan: $PREF_ABS"* \
  && "$PREF_OUT" == *'validate: ok'* && "$PREF_OUT" == *'waived: no'* \
  && "$PREF_OUT" == *"base ref: ok ($PREF_BASE)"* \
  && "$PREF_OUT" == *'ledger: absent'* && "$PREF_OUT" == *'next: scripts/review-coverage run-card --plan'* ]]; then
  ok preflight_ok
else
  bad preflight_ok
fi
PREF_MISSING_EC=$(python3 "$CLI" preflight --plan "/nonexistent/preflight-plan-$$.md" >/dev/null 2>&1; echo $?)
if [[ "$PREF_MISSING_EC" -eq 2 ]]; then ok preflight_missing; else bad preflight_missing; fi
PREF_WAIVED=$(mktemp)
cat >"$PREF_WAIVED" <<'EOF'
## Review Coverage

None — residual loop waived: docs-only plan
EOF
PREF_WAIVED_OUT=$(python3 "$CLI" preflight --plan "$PREF_WAIVED" 2>&1 || true)
PREF_WAIVED_EC=$(python3 "$CLI" preflight --plan "$PREF_WAIVED" >/dev/null 2>&1; echo $?)
if [[ "$PREF_WAIVED_EC" -eq 1 ]]; then ok preflight_waived; else bad preflight_waived; fi
if printf '%s\n' "$PREF_WAIVED_OUT" | grep -q 'waived: yes'; then ok preflight_waived_line; else bad preflight_waived_line; fi
CARD=$(python3 "$CLI" run-card --plan "$PREF_PLAN" --preflight)
PREF_GOAL=$(python3 "$CLI" goal-body --plan "$PREF_PLAN" --slash)
CARD_GOAL=$(printf '%s\n' "$CARD" | awk '/^### 1\. Open host goal$/{found=1; next} /^### 2\. Each turn$/{exit} found && NF {print; exit}')
if [[ "$CARD_GOAL" == "$PREF_GOAL" ]]; then ok run_card_goal_matches_goal_body; else bad run_card_goal_matches_goal_body; fi
if [[ "$CARD" == *'Target paths: src/foo.ts'* && "$CARD" == *'Test command: npm test'* \
  && "$CARD" == *"Base ref: $PREF_BASE"* && "$CARD" == *'Max review-converge rounds: 7'* ]]; then
  ok run_card_fields
else
  bad run_card_fields
fi
# failed preflight must not emit a run card body
CARD_FAIL=$(python3 "$CLI" run-card --plan "$PREF_WAIVED" --preflight 2>&1 || true)
if ! printf '%s\n' "$CARD_FAIL" | grep -q '### 1. Open host goal'; then ok run_card_preflight_fail_no_card; else bad run_card_preflight_fail_no_card; fi
rm -f "$PREF_PLAN" "$PREF_WAIVED"
rm -rf "$PREF_REPO"

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
if printf '%s\n' "$DERR" | grep -qi 'Driver must mention review-converge'; then ok bad_driver_stderr; else bad bad_driver_stderr; fi
rm -f "$TMPD"

# improve-loop-only Driver rejected (MVP honesty — goal-body hard-codes review-converge)
TMPI2=$(mktemp)
cat >"$TMPI2" <<'EOF'
## Review Coverage

| Field | Value |
|-------|--------|
| Base ref | abcdef1234567890deadbeef |
| Target paths | src/foo.ts |
| Test command | npm test |
| Materiality bar | material (P0/P1) |
| Driver | improve-loop under /goal |

1. Forward audit of specs to code.
2. Reverse audit of code vs base.
two consecutive clean residual rounds with green suite
EOF
if ! python3 "$CLI" validate "$TMPI2" >/dev/null 2>&1; then ok improve_loop_driver_rejects; else bad improve_loop_driver_rejects; fi
rm -f "$TMPI2"

# Max rounds: unlimited / 0 fail closed; valid 12 hard cap ok
TMPU=$(mktemp)
cat >"$TMPU" <<'EOF'
## Review Coverage

| Field | Value |
|-------|--------|
| Base ref | abcdef1234567890deadbeef |
| Target paths | src/foo.ts |
| Test command | npm test |
| Materiality bar | material (P0/P1) |
| Driver | review-converge under /goal |
| Max review-converge rounds | unlimited |

1. Forward audit of specs to code.
2. Reverse audit of code vs base.
two consecutive clean residual rounds with green suite
EOF
if ! python3 "$CLI" validate "$TMPU" >/dev/null 2>&1; then ok max_rounds_unlimited_rejects; else bad max_rounds_unlimited_rejects; fi
rm -f "$TMPU"

TMP0=$(mktemp)
cat >"$TMP0" <<'EOF'
## Review Coverage

| Field | Value |
|-------|--------|
| Base ref | abcdef1234567890deadbeef |
| Target paths | src/foo.ts |
| Test command | npm test |
| Materiality bar | material (P0/P1) |
| Driver | review-converge under /goal |
| Max review-converge rounds | 0 |

1. Forward audit of specs to code.
2. Reverse audit of code vs base.
two consecutive clean residual rounds with green suite
EOF
if ! python3 "$CLI" validate "$TMP0" >/dev/null 2>&1; then ok max_rounds_zero_rejects; else bad max_rounds_zero_rejects; fi
rm -f "$TMP0"

# pathspec clause in goal-body
if printf '%s\n' "$GBO" | grep -qi 'never git add -A\|Pathspec commits only'; then ok goal_body_pathspec; else bad goal_body_pathspec; fi

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
if printf '%s\n' "$POL_GB" | grep -q 'Test command: npm test'; then ok field_table_wins_cmd; else bad field_table_wins_cmd; fi
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

if grep -q '^version: 0.2.4$' "$ROOT/skills/review-coverage/SKILL.md"; then ok skill_version; else bad skill_version; fi
# Skill-first invoke (primary); CLI remains optional helper
if grep -qE '/review-coverage|## Invocation' "$ROOT/skills/review-coverage/SKILL.md" \
  && grep -qiE 'not the primary|optional CLI helpers|not a script-first' "$ROOT/skills/review-coverage/SKILL.md"; then
  ok skill_invoke_docs
else
  bad skill_invoke_docs
fi
if grep -q -- 'goal-body --plan /path/to/plan.md --slash' "$ROOT/skills/review-coverage/SKILL.md"; then ok skill_slash_docs; else bad skill_slash_docs; fi
if grep -qiE 'goal-body --plan.*--slash|Prefer CLI when available' "$ROOT/skills/review-coverage/SKILL.md" \
  && grep -qi 'hard stop' "$ROOT/skills/review-coverage/SKILL.md"; then
  ok skill_phase_b_cli_prefer
else
  bad skill_phase_b_cli_prefer
fi

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

# Skill-first compose example must match CLI exit wording (no "zero material findings")
if ! grep -q 'zero material findings' "$ROOT/skills/review-coverage/SKILL.md"; then
  ok skill_md_no_zero_material
else
  bad skill_md_no_zero_material
fi
if grep -q 'only trivial findings remaining this cycle' "$ROOT/skills/review-coverage/SKILL.md"; then
  ok skill_md_trivial_findings_ledger
else
  bad skill_md_trivial_findings_ledger
fi
if grep -q 'Post-Implementation Residual Loop' "$ROOT/skills/review-coverage/SKILL.md" \
  && grep -qiE 'rewrite|migrate|legacy' "$ROOT/skills/review-coverage/SKILL.md"; then
  ok skill_md_migrate_legacy_h2
else
  bad skill_md_migrate_legacy_h2
fi

echo "======== review-coverage: PASS=$PASS FAIL=$FAIL ========"
[[ "$FAIL" -eq 0 ]]
