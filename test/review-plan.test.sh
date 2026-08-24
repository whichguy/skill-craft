#!/usr/bin/env bash
# Hermetic tests for the imported review-plan skill + plan-oversight query seam.
set -euo pipefail

PASS=0
FAIL=0
ok() { echo "PASS $1"; PASS=$((PASS + 1)); }
bad() { echo "FAIL $1"; FAIL=$((FAIL + 1)); }

resolve_skill() {
  local candidate
  for candidate in \
    "${REVIEW_PLAN_SKILL:-}" \
    "$HOME/.cursor/skills/review-plan" \
    "$HOME/.claude/plugins/cache/claude-craft/review-suite/0.2.4/skills/review-plan"
  do
    if [[ -n "$candidate" && -f "$candidate/SKILL.md" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

resolve_oversight() {
  local candidate
  for candidate in \
    "${PLAN_OVERSIGHT_ROOT:-}" \
    "$HOME/src/plan-oversight"
  do
    if [[ -n "$candidate" && -f "$candidate/plan_review_status.py" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

SKILL="$(resolve_skill || true)"
PO="$(resolve_oversight || true)"

if [[ -z "$SKILL" && -z "$PO" ]]; then
  echo "SKIP review-plan (skill and plan-oversight not present)"
  exit 0
fi

if [[ -n "$SKILL" ]]; then
  SKILL_MD="$SKILL/SKILL.md"
  [[ -f "$SKILL_MD" ]] && ok skill_md || bad skill_md
  grep -q '^name: review-plan' "$SKILL_MD" && ok frontmatter_name || bad frontmatter_name
  grep -q 'plan_review_status.py' "$SKILL_MD" && ok seam_command || bad seam_command
  grep -q '`0`' "$SKILL_MD" && grep -q '`3`' "$SKILL_MD" && grep -q '`4`' "$SKILL_MD" \
    && ok exit_codes_documented || bad exit_codes_documented
  grep -q 'queued` / `running' "$SKILL_MD" && ok exit3_inflight || bad exit3_inflight
  grep -q 'none / `unavailable' "$SKILL_MD" && ok exit4_none || bad exit4_none
  grep -q 'Do not dispatch your own cross-model reviewers' "$SKILL_MD" \
    && ok no_in_turn_dispatch || bad no_in_turn_dispatch
  grep -F -q '**zero** blocking' "$SKILL_MD" && grep -q 'PASS' "$SKILL_MD" \
    && ok severity_zero_pass || bad severity_zero_pass
  grep -F -q '**exactly one** blocking' "$SKILL_MD" && grep -q 'NEEDS_UPDATE' "$SKILL_MD" \
    && ok severity_one_needs_update || bad severity_one_needs_update
  grep -F -q '**two or more** blocking' "$SKILL_MD" && grep -q 'NOT READY' "$SKILL_MD" \
    && ok severity_two_not_ready || bad severity_two_not_ready
  grep -q 'TRIVIAL' "$SKILL_MD" && ok trivial_na || bad trivial_na
  grep -q 'Reviewer Coverage' "$SKILL_MD" && ok reviewer_coverage || bad reviewer_coverage
  grep -q 'Do not write a `.review-ready' "$SKILL_MD" && ok no_retired_sentinel || bad no_retired_sentinel
  grep -q 'plan-oversight/templates/residual_loop.md' "$SKILL_MD" \
    && ok residual_template_cited || bad residual_template_cited
  if [[ -L "$HOME/.cursor/skills/review-plan" ]]; then
    target="$(readlink "$HOME/.cursor/skills/review-plan")"
    [[ -f "$target/SKILL.md" || -f "$HOME/.cursor/skills/review-plan/SKILL.md" ]] \
      && ok cursor_import_resolves || bad cursor_import_resolves
  else
    ok cursor_import_resolves
  fi
else
  echo "SKIP review-plan skill card (not imported)"
fi

if [[ -n "$PO" ]]; then
  STATUS="$PO/plan_review_status.py"
  TMP="$(mktemp -d "${TMPDIR:-/tmp}/review-plan-test.XXXXXX")"
  cleanup() { rm -rf "$TMP"; }
  trap cleanup EXIT
  export PLAN_OVERSIGHT_STATE_DIR="$TMP/state"
  export PLAN_OVERSIGHT_LOG_DIR="$TMP/logs"
  export PLAN_OVERSIGHT_LEGACY_LOG_DIR="$TMP/legacy"
  export PLAN_OVERSIGHT_SESSIONS_ROOT="$TMP/sessions"
  export PLAN_OVERSIGHT_REVIEWS_DIR="$TMP/reviews"
  export CLAUDE_PLANS_DIR="$TMP/claude-plans"
  export CURSOR_PLANS_DIR="$TMP/cursor-plans"
  mkdir -p "$PLAN_OVERSIGHT_STATE_DIR" "$PLAN_OVERSIGHT_LOG_DIR" \
    "$PLAN_OVERSIGHT_REVIEWS_DIR" "$CLAUDE_PLANS_DIR" "$CURSOR_PLANS_DIR"
  PLAN="$TMP/sample.plan.md"
  cat >"$PLAN" <<'EOF'
# Sample plan

## Scope
Update src/auth.py and tests/test_auth.py.

## Steps
1. Preserve the current token parser.
2. Add an expired-token branch and a regression test.

## Open Unknowns
None — no load-bearing unknowns.
- **Decision:** Existing token format remains authoritative.

## Plan verification / Spec anchors
| ID | Directive | Verify by | Status |
|----|-----------|-----------|--------|
| V1 | Expired tokens keep the existing error | pytest tests/test_auth.py | pending |
EOF

  set +e
  python3 "$STATUS" "$TMP/missing.md" >/dev/null 2>&1
  rc=$?
  set -e
  [[ "$rc" -eq 4 ]] && ok seam_missing_plan_exit4 || bad seam_missing_plan_exit4

  set +e
  out="$(python3 "$STATUS" "$PLAN" 2>&1)"
  rc=$?
  set -e
  [[ "$rc" -eq 4 ]] && ok seam_no_review_exit4 || bad seam_no_review_exit4
  printf '%s\n' "$out" | grep -q '^state:' && ok seam_no_review_state || bad seam_no_review_state

  python3 - "$PO" "$PLAN" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from core import plan_hash, write_review_status
plan = Path(sys.argv[2])
ph = plan_hash(plan.read_text(encoding="utf-8"))
write_review_status(plan, ph, "queued", note="worker spawn pending", update_latest=False)
PY
  set +e
  python3 "$STATUS" "$PLAN" >/dev/null 2>&1
  rc=$?
  set -e
  [[ "$rc" -eq 3 ]] && ok seam_queued_exit3 || bad seam_queued_exit3

  python3 - "$PO" "$PLAN" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from core import plan_hash, write_review_artifact
plan = Path(sys.argv[2])
text = plan.read_text(encoding="utf-8")
ph = plan_hash(text)
write_review_artifact(
    plan,
    ph,
    "seats=opus,sol\n\n- [BLOCKING] (opus) Steps: add a pre-read of src/auth.py.\n",
    note="fixture",
)
PY
  set +e
  out="$(python3 "$STATUS" "$PLAN" 2>&1)"
  rc=$?
  set -e
  [[ "$rc" -eq 0 ]] && ok seam_completed_exit0 || bad seam_completed_exit0
  printf '%s\n' "$out" | grep -q 'seats=opus,sol' && ok seam_completed_body || bad seam_completed_body
  printf '%s\n' "$out" | grep -q '\[BLOCKING\] (opus)' && ok seam_completed_finding || bad seam_completed_finding

  python3 - "$PO" "$PLAN" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from core import plan_hash, write_review_artifact
plan = Path(sys.argv[2])
ph = plan_hash(plan.read_text(encoding="utf-8"))
write_review_artifact(plan, ph, "seats=opus\n\nNO FINDINGS (opus)\n", degraded=True)
PY
  set +e
  out="$(python3 "$STATUS" "$PLAN" 2>&1)"
  rc=$?
  set -e
  [[ "$rc" -eq 0 ]] && ok seam_degraded_exit0 || bad seam_degraded_exit0
  printf '%s\n' "$out" | grep -qi 'degraded' && ok seam_degraded_flag || bad seam_degraded_flag

  python3 - "$PO" "$PLAN" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from core import plan_hash, write_review_status, review_path
plan = Path(sys.argv[2])
ph = plan_hash(plan.read_text(encoding="utf-8"))
rev = review_path(plan, ph)
rev.parent.mkdir(parents=True, exist_ok=True)
rev.write_text("stale body\n", encoding="utf-8")
write_review_status(plan, ph, "superseded", note="replaced", review_file=rev, update_latest=False)
PY
  set +e
  python3 "$STATUS" "$PLAN" >/dev/null 2>&1
  rc=$?
  set -e
  [[ "$rc" -eq 4 ]] && ok seam_superseded_exit4 || bad seam_superseded_exit4

  [[ -f "$PO/templates/residual_loop.md" ]] && ok residual_template_exists || bad residual_template_exists
  grep -q 'Post-Implementation Residual Loop' "$PO/templates/residual_loop.md" \
    && ok residual_template_h2 || bad residual_template_h2
else
  echo "SKIP review-plan query seam (plan-oversight not present)"
fi

echo "======== review-plan: PASS=$PASS FAIL=$FAIL ========"
[[ "$FAIL" -eq 0 ]]
