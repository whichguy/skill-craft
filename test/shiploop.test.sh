#!/usr/bin/env bash
# Hermetic shiploop session-harness tests (no network).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cli="$root/skills/shiploop/scripts/shiploop"
fix="$root/test/fixtures/shiploop"
export SHIPLOOP_BACKCHAIN_ROOT="$fix/backchain-leaf"
# shellcheck source=shiploop-testkit.sh
source "$root/test/shiploop-testkit.sh"

fail() {
  printf 'shiploop.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

[[ -f "$root/skills/shiploop/SKILL.md" ]] || fail "missing SKILL.md"
[[ ! -d "$root/skills/shiploop/prompts" ]] || fail "prompts/ must not exist"
grep -q 'kind: script-backed' "$root/skills/shiploop/SKILL.md" || fail "frontmatter kind"
grep -q 'name: shiploop' "$root/skills/shiploop/SKILL.md" || fail "frontmatter name"
grep -q 'shiploop — session harness' "$root/skills/shiploop/SKILL.md" || fail "banner"
if grep -q 'DEFINE → PROVE → BUILD' "$root/skills/shiploop/SKILL.md"; then
  fail "SKILL.md must not own DEFINE/PROVE/BUILD"
fi
if grep -RqiE 'devloop' --exclude-dir=__pycache__ \
  "$root/skills/shiploop" "$root/agents/shiploop.md"; then
  fail "shiploop skill must not mention DevLoop"
fi
if grep -Fq 'commit + merge' "$root/agents/shiploop.md"; then
  fail "agents/shiploop.md closer still always-commits"
fi
grep -q 'leftover commit' "$root/agents/shiploop.md" \
  || fail "agents/shiploop.md closer missing leftover commit"
if grep -E 'shiploop capture|devloop-run' "$root/skills/shiploop/references/activities/implement.md"; then
  fail "implement activity still captures a foreign runner"
fi
grep -q 'echo the printed' "$root/skills/shiploop/SKILL.md" \
  || fail "SKILL.md missing echo You are here / Diagnosis"
grep -q 'Goal until' "$root/skills/shiploop/SKILL.md" \
  || fail "SKILL.md missing Goal until paste"
grep -q 'Improve' "$root/skills/shiploop/SKILL.md" \
  || fail "SKILL.md missing Improve paste"
grep -q 'do not nest' "$root/skills/shiploop/SKILL.md" \
  || fail "SKILL.md missing do not nest"
grep -q 'Do not nest' "$root/skills/shiploop/references/activities/implement.md" \
  || fail "implement.md missing Do not nest"
if grep -Fq 'HOST FLAG — extra folder' \
  "$root/skills/shiploop/references/activities/implement.md"; then
  fail "implement.md re-clones HOST FLAG (SoT is print_packet envelope)"
fi
if grep -Fq 'two consecutive only-trivial' \
  "$root/skills/shiploop/references/activities/implement.md"; then
  fail "implement.md re-clones Improve cycle"
fi
if grep -Fq 'max 12' "$root/skills/shiploop/references/activities/implement.md"; then
  fail "implement.md re-clones Improve max 12"
fi
impl_git_n="$(grep -cF 'Implement git' \
  "$root/skills/shiploop/references/activities/implement.md" || true)"
[[ "$impl_git_n" -eq 0 ]] || fail "implement.md re-clones Implement git (count $impl_git_n; SoT is print_implement_git)"
if grep -Fq 'Key learnings:' "$root/skills/shiploop/references/activities/plan.md"; then
  fail "plan.md re-clones implement git contract into plan-time Next"
fi
grep -q 'status --human' "$root/skills/shiploop/SKILL.md" \
  || fail "SKILL.md missing status --human"
grep -q 'PATH/.shiploop' "$root/skills/shiploop/SKILL.md" \
  || fail "SKILL.md missing init --repo run-dir default"
grep -q 'working directory' "$root/skills/shiploop/references/host-matrix.md" \
  || fail "host-matrix.md missing CLI working directory"
[[ -f "$root/skills/shiploop/references/host-matrix.md" ]] || fail "missing host-matrix.md"
[[ -f "$root/skills/shiploop/references/ledger-contract.md" ]] || fail "missing ledger-contract.md"
grep -q 'copied, not imported' "$root/skills/shiploop/references/ledger-contract.md" || fail "ledger-contract copy note"
grep -q 'VALIDATE_SPEC_PATH' "$root/skills/shiploop/references/activities/validate-spec.md" \
  && fail "validate-spec.md must not mention VALIDATE_SPEC_PATH"
for tok in prep "intermediate deploy" cleanup; do
  grep -q "$tok" "$root/skills/shiploop/references/activities/plan.md" || fail "plan.md missing $tok"
done
grep -q 'outer-loop' "$root/skills/shiploop/references/activities/plan.md" \
  || fail "plan.md missing outer-loop publish placement"
grep -q 'Deploy preparation before the walk' "$root/skills/shiploop/references/activities/validate-spec.md" \
  || fail "validate-spec.md missing deploy-prep question"
grep -q 'Deploy / publish after the walk' "$root/skills/shiploop/references/activities/validate-spec.md" \
  || fail "validate-spec.md missing deploy/publish question"
grep -q 'Quality test/fix on outer-loop completion' "$root/skills/shiploop/references/activities/validate-spec.md" \
  || fail "validate-spec.md missing quality /goal question"
grep -q '/goal' "$root/skills/shiploop/references/activities/validate-spec.md" \
  || fail "validate-spec.md missing /goal in quality question"
grep -q 'Quality test/fix' "$root/skills/shiploop/references/activities/residual.md" \
  || fail "residual.md missing quality /goal closer"
grep -q 'Outer-loop deploy/publish' "$root/skills/shiploop/references/activities/residual.md" \
  || fail "residual.md missing outer-loop deploy/publish"
chmod +x "$cli"

le_docs="$root/docs/LOOP-ENGINEERING.md"
le_skill="$root/skills/devloop/references/loop-engineering.md"
diff -q "$le_docs" "$le_skill" >/dev/null || fail "LOOP-ENGINEERING copies drifted"
grep -q 'ShipLoop session' "$le_docs" || fail "LOOP-ENGINEERING missing ShipLoop session track"
grep -q '/shiploop next' "$le_docs" || fail "LOOP-ENGINEERING missing /shiploop next"
grep -q '/shiploop complete' "$le_docs" || fail "LOOP-ENGINEERING missing /shiploop complete"
grep -q 'research practices' "$le_docs" || fail "LOOP-ENGINEERING missing practices research"
grep -q 'recap.html' "$le_docs" || fail "LOOP-ENGINEERING missing recap.html"
grep -q 'quality test-and-fix' "$le_docs" || fail "LOOP-ENGINEERING missing quality /goal"
grep -q 'outer-loop' "$le_docs" || fail "LOOP-ENGINEERING missing outer-loop publish"
grep -q 'Best-practice research' "$root/skills/shiploop/references/activities/validate-spec.md" \
  || fail "validate-spec.md missing practices job"
grep -q 'best-practice' "$root/skills/shiploop/references/survey.md" \
  || fail "survey.md missing practices research"
grep -Fq 'Deeply research those MCP servers' \
  "$root/skills/shiploop/references/activities/validate-spec.md" \
  || fail "validate-spec.md missing Deeply research those MCP servers"
grep -Fiq 'reuse before add' \
  "$root/skills/shiploop/references/activities/validate-spec.md" \
  || fail "validate-spec.md missing reuse before add"
grep -Fq 'Do not duplicate, conflict with, or arbitrarily add' \
  "$root/skills/shiploop/references/activities/validate-spec.md" \
  || fail "validate-spec.md missing arbitrarily add"
grep -q 'repo_root' "$root/skills/shiploop/references/survey.md" \
  || fail "survey.md missing repo_root reuse search"
grep -q 'destination' "$root/skills/shiploop/references/survey.md" \
  || fail "survey.md missing destination reuse search"
grep -Fq 'arbitrarily add' "$root/skills/shiploop/references/survey.md" \
  || fail "survey.md missing arbitrarily add"
if grep -RqiE 'mcp-gas-deploy|commonjs' --exclude-dir=__pycache__ \
  "$root/skills/shiploop/references" \
  "$root/skills/shiploop/scripts/shiploop"; then
  fail "shiploop must not mandate a vendor MCP server or module format"
fi
if grep -RqiE 'mcp-gas-deploy|common-js|HtmlService|doGet|/play' \
  "$root/skills/shiploop/references/activities" \
  "$root/skills/shiploop/references/survey.md"; then
  fail "shiploop destination discovery must stay vendor-free"
fi
if grep -RqiE 'frontend-design|HtmlService|GAS|mcp-gas-deploy|common-js|doGet|/play' \
  "$root/skills/shiploop/references/activities" \
  "$root/skills/shiploop/references/survey.md"; then
  fail "shiploop surface planning must stay vendor-free"
fi
if grep -q '{{' "$root/skills/shiploop/references/survey.md"; then
  fail "survey.md must not contain interpolation tokens (Look-here is not interpolated)"
fi
if grep -qE '^## ' "$root/skills/shiploop/references/activities/"*.md; then
  fail "activity files must not use packet-level H2 (## ) — Next is H2-bounded"
fi
grep -q 'must not use packet-level H2' \
  "$root/skills/shiploop/references/turn-packet.md" \
  || fail "turn-packet.md missing packet-level H2 Next contract"
grep -q 'must not use packet-level H2' \
  "$root/skills/shiploop/README.md" \
  || fail "README missing packet-level H2 Next contract"
grep -q '^### 2. Best-practice research' \
  "$root/skills/shiploop/references/activities/validate-spec.md" \
  || fail "validate-spec.md job 2 heading is not ###"
grep -Fq '### Surfaces' "$root/skills/shiploop/references/activities/validate-spec.md" \
  || fail "validate-spec.md missing Surfaces job"
grep -Fq 'highly interactive' "$root/skills/shiploop/references/activities/validate-spec.md" \
  || fail "validate-spec.md missing surface quality bar"
for title in 'How to use this MCP' 'Library / runtime systems it imposes' \
  'Conventions — reserved vs product' 'How a user actually hits'; do
  grep -Fq "$title" "$root/skills/shiploop/references/activities/validate-spec.md" \
    || fail "validate-spec.md missing destination discovery question: $title"
done
for needle in "Don't write:" 'routing-level probe' 'live acceptance'; do
  grep -Fq "$needle" "$root/skills/shiploop/references/activities/plan.md" \
    || fail "plan.md missing destination seed contract: $needle"
done
grep -Fq 'early design' "$root/skills/shiploop/references/activities/plan.md" \
  || fail "plan.md missing early design seed"
grep -Fq -- '--inner-loop goal|parent' "$root/skills/shiploop/README.md" \
  || fail "README missing implement complete --inner-loop"
grep -Fq -- '--inner-loop goal|parent' \
  "$root/skills/shiploop/references/turn-packet.md" \
  || fail "turn-packet.md missing implement complete --inner-loop"
grep -q 'practice references' "$root/skills/shiploop/references/activities/plan.md" \
  || fail "plan.md missing practice references in step prompts"
grep -q 'researches applicable practices' "$root/skills/shiploop/README.md" \
  || fail "README missing practices research"
grep -Fq 'files, not the three Next jobs' "$root/skills/shiploop/README.md" \
  || fail "README missing Look-here file vs Next-job ordinals"
grep -q '__pycache__/' "$root/skills/shiploop/README.md" \
  || fail "README missing --check bytecode ignore"
pyc_pin="$root/skills/shiploop/scripts/__pycache__"
cleanup_pyc_pin() { rm -rf "$pyc_pin"; }
trap cleanup_pyc_pin EXIT
mkdir -p "$pyc_pin"
printf 'x' >"$pyc_pin/pin.pyc"
set +e
out_pyc="$(bash "$root/scripts/sync-plugin-views.sh" --check shiploop 2>&1)"
rc_pyc=$?
set -e
cleanup_pyc_pin
trap - EXIT
[[ "$rc_pyc" -eq 0 ]] || fail "leaf-only __pycache__ should not fail --check: $out_pyc"
grep -q 'recap.html' "$root/skills/shiploop/README.md" \
  || fail "README missing recap.html"
if grep -q 'Any working phase can dest' "$root/skills/shiploop/README.md"; then
  fail "README must not claim intake dest blocked"
fi
grep -q 'Every working phase after intake can dest' "$root/skills/shiploop/README.md" \
  || fail "README missing after-intake dest blocked"
grep -q 'Each seed `prompt` must cite every `references\[\].path`' \
  "$root/skills/shiploop/README.md" \
  || fail "README citation gate looser than dag_gaps"
grep -q 'host-owned' "$root/skills/shiploop/references/activities/done.md" \
  || fail "done.md missing host-owned quality"
if grep -q 'already ran' "$root/skills/shiploop/references/activities/done.md"; then
  fail "done.md must not claim quality already ran"
fi
grep -q '`success`' "$root/skills/shiploop/references/state-files.md" \
  || fail "state-files.md missing terminal success"
grep -q '`waived`' "$root/skills/shiploop/references/state-files.md" \
  || fail "state-files.md missing terminal waived"
grep -q '`halted`' "$root/skills/shiploop/references/state-files.md" \
  || fail "state-files.md missing terminal halted"
v=$(sed -n 's/^version: *//p' "$root/skills/shiploop/SKILL.md" | head -n1)
grep -q "^VERSION = \"$v\"$" "$cli" || fail "script VERSION != SKILL.md"
grep -q "^version: $v$" "$root/skills/shiploop/SKILL.md" || fail "SKILL.md version self-check"
grep -Fq "Version: **$v**" "$root/skills/shiploop/README.md" || fail "README version != SKILL.md"
grep -q 'exclusive writer' "$root/skills/shiploop/references/survey.md" \
  || fail "survey.md missing exclusive writer question"
grep -q 'conflicts, not as backups' "$root/skills/shiploop/references/survey.md" \
  || fail "survey.md missing conflicts, not as backups"
grep -q 'libraries' "$root/skills/shiploop/references/survey.md" \
  || fail "survey.md missing libraries"
grep -q 'platform preconditions' "$root/skills/shiploop/references/survey.md" \
  || fail "survey.md missing platform preconditions"
grep -q 'Probe enablement before' "$root/skills/shiploop/references/survey.md" \
  || fail "survey.md missing probe enablement before initiation create"
grep -q 'dest-writes can succeed now' "$root/skills/shiploop/references/survey.md" \
  || fail "survey.md missing dest-writes in-bounds rule"
grep -q 'do not omit the designated writer' "$root/skills/shiploop/references/survey.md" \
  || fail "survey.md missing do not omit designated writer from tools/mcp"
grep -q 'platform preconditions' "$root/skills/shiploop/references/activities/validate-spec.md" \
  || fail "validate-spec.md missing platform preconditions"
grep -q 'enablement' "$root/skills/shiploop/README.md" \
  || fail "README missing enablement in exclusive-writer job 2"
grep -q 'exclusive' "$root/skills/shiploop/references/state-files.md" \
  || fail "state-files.md missing exclusive writer map"
grep -Fq 'ENV_RECOVERY' "$cli" || fail "script missing ENV_RECOVERY"
grep -Fq 'DEST_BLOCKED_LINE' "$cli" || fail "script missing DEST_BLOCKED_LINE"
grep -Fq 'in-flight runs: dest blocked → validate-spec; rewrite environment.md; → plan (do not hand-edit backchain/plan.json)' \
  "$cli" || fail "script missing ENV_RECOVERY sentence"
blocked_line='If the writer above fails, stop and invoke /shiploop complete --blocked --reason … — do not switch writers.'
grep -Fq "$blocked_line" "$cli" || fail "script missing dest-blocked Frozen sentence"
grep -Fq "$blocked_line" "$root/skills/shiploop/references/survey.md" \
  || fail "survey.md missing dest-blocked sentence"
grep -Fq "$blocked_line" "$root/skills/shiploop/references/activities/implement.md" \
  || fail "implement.md missing dest-blocked sentence"
grep -q 'Use:' "$root/skills/shiploop/commands/shiploop-inject.md" \
  || fail "shiploop-inject.md missing Use: for exclusive discovered prompts"
grep -q 'exclusive\[\].use' "$root/skills/shiploop/commands/shiploop-inject.md" \
  || fail "shiploop-inject.md missing exclusive[].use on Use:"
grep -q 'Use:' "$root/skills/shiploop/references/activities/implement.md" \
  || fail "implement.md missing Use: for exclusive discovered prompts"
grep -q 'exclusive\[\].use' "$root/skills/shiploop/references/activities/implement.md" \
  || fail "implement.md missing exclusive[].use on Use:"
grep -Fq "$blocked_line" "$root/skills/shiploop/references/turn-packet.md" \
  || fail "turn-packet.md missing dest-blocked sentence"
grep -Fq "$blocked_line" "$root/skills/shiploop/README.md" \
  || fail "README missing dest-blocked sentence"
if grep -q '| `playbook.md` |' "$root/skills/shiploop/README.md" \
  "$root/skills/shiploop/references/state-files.md"; then
  fail "playbook.md must not be a SoT row"
fi
if grep -nE 'clasp|(^|[^a-z])gas([^a-z]|$)|google' "$cli"; then
  fail "Python must not name clasp/GAS/google"
fi
if grep -q 'write `.shiploop/playbook.md`' "$root/skills/shiploop/README.md" \
  "$root/skills/shiploop/references/survey.md" \
  "$root/skills/shiploop/references/activities/validate-spec.md"; then
  fail "host must not be instructed to write playbook.md"
fi
grep -q 'Use: git' "$root/skills/shiploop/references/activities/plan.md" \
  || fail "plan.md Tools Use is not git"
grep -q 'def print_stored_prompt' "$cli" || fail "script missing print_stored_prompt"
if grep -q 'print(str(step.get("prompt") or "").rstrip())' "$cli"; then
  fail "print_packet still rstrip stored prompt"
fi
grep -q 'next — claimed' "$cli" || fail "cmd_next missing claimed event line"
grep -q 'next — reprint' "$cli" || fail "cmd_next missing reprint event line"
if grep -q 'Banner (first line of any invoke)' "$root/skills/shiploop/SKILL.md"; then
  fail "SKILL.md still claims banner is first line of any invoke"
fi
grep -q 'Purpose of the plan' "$root/skills/shiploop/references/activities/plan.md" \
  || fail "plan.md missing purpose vs setup split"
grep -q 'new repo' "$root/skills/shiploop/references/activities/plan.md" \
  || fail "plan.md missing new repo example"
grep -q 'Database' "$root/skills/shiploop/references/activities/plan.md" \
  || fail "plan.md missing database example"
grep -Fq 'Never empty `unresolved` by inventing `initial_state`.' \
  "$root/skills/shiploop/references/activities/plan.md" \
  || fail "plan.md missing never-invent initial_state"
grep -Fq 'Several matches' "$root/skills/shiploop/references/survey.md" \
  || fail "survey.md missing Several matches -> ask"
grep -Fq 'resolved_facts' "$root/skills/shiploop/references/activities/plan.md" \
  || fail "plan.md missing resolved_facts"
grep -Fq 'Do not audit the persisted DAG for new experiments' \
  "$root/skills/shiploop/references/activities/plan.md" \
  || fail "plan.md missing no post-persist experiment audit"
grep -Fq 'dependency review' "$root/skills/shiploop/references/activities/plan.md" \
  || fail "plan.md missing dependency review"
grep -Fq 'access established' "$root/skills/shiploop/references/activities/blocked.md" \
  || fail "blocked.md missing access established"
grep -q 'done_sentence' "$root/skills/shiploop/references/activities/validate-spec.md" \
  || fail "validate-spec.md missing done_sentence on hatch"
grep -q 'done_sentence' "$root/skills/shiploop/references/survey.md" \
  || fail "survey.md hatch missing done_sentence"
grep -q 'Do this activity until these conditions are met:' "$cli" \
  || fail "script missing UNTIL_HEAD"
n_ret="$(grep -c 'assert_transition_return ' "$root/test/shiploop-walk-journal.test.sh" || true)"
[[ "$n_ret" -ge 20 ]] || fail "walk-journal must call assert_transition_return (got $n_ret)"
[[ -f "$root/test/fixtures/shiploop/setup-once.json" ]] \
  || fail "missing setup-once.json"
[[ -f "$root/test/fixtures/shiploop/single.json" ]] \
  || fail "missing single.json"
grep -Fq '"exclusive": []' "$fix/transitions/artifacts/environment.md" \
  || fail "sample environment.md missing exclusive []"
grep -q 'def journal_mark' "$cli" || fail "script missing journal_mark"
grep -Fq 'same glyphs' "$root/skills/shiploop/README.md" \
  || fail "README missing walk rail same glyphs as session rail"
grep -Fq 'same glyphs' "$root/skills/shiploop/references/turn-packet.md" \
  || fail "turn-packet.md missing walk rail same glyphs"
if grep -E 'walk\.md|journal\.md' "$cli"; then
  fail "scripts/shiploop must not write walk.md or journal.md"
fi
[[ -f "$root/test/shiploop-walk-journal.test.sh" ]] \
  || fail "missing test/shiploop-walk-journal.test.sh"
grep -q 'init --force --prompt' "$root/skills/shiploop/SKILL.md" \
  || fail "SKILL.md missing three-branch init --force --prompt"
grep -q 'init --force --prompt' "$root/skills/shiploop/README.md" \
  || fail "README missing Session B init --force --prompt"
grep -q '/shiploop complete --reason' "$root/skills/shiploop/SKILL.md" \
  || fail "SKILL.md missing blocked resume complete --reason"
grep -q '/shiploop complete --reason' "$root/skills/shiploop/README.md" \
  || fail "README missing blocked resume complete --reason"
if grep -F 'update --to <resume_to>' \
  "$root/skills/shiploop/SKILL.md" \
  "$root/skills/shiploop/README.md" \
  "$le_docs" "$le_skill"; then
  fail "stale blocked resume update --to <resume_to>"
fi
if grep -q '{{PLAN_JSON}}' "$root/skills/shiploop/references/activities/plan.md"; then
  fail "plan activity still interpolates retired PLAN_JSON"
fi
if grep -q 'plan.json.done_sentence' "$root/skills/shiploop/README.md"; then
  fail "README still treats wrapper done_sentence as a surface"
fi
if grep -q 'four surfaces' "$root/skills/shiploop/README.md"; then
  fail "README still says four done_sentence surfaces"
fi
grep -q 'Same sentence, three surfaces' "$root/skills/shiploop/README.md" \
  || fail "README missing three-surface done_sentence sentence"
grep -q 'Do not write a `plan.json` wrapper' "$root/skills/shiploop/README.md" \
  || fail "README missing do-not-write plan.json wrapper"
grep -q 'Do not write a `plan.json` wrapper' \
  "$root/skills/shiploop/references/activities/plan.md" \
  || fail "plan activity missing do-not-write plan.json wrapper"
if grep -E 'Write order: DAG → receipts → wrapper' "$root/skills/shiploop/README.md"; then
  fail "README inject write-order still stamps wrapper"
fi
grep -q 'Leftover `plan.json` wrappers are inert' \
  "$root/skills/shiploop/references/state-files.md" \
  || fail "state-files.md missing leftover plan.json inert"
grep -q 'at dest implement' "$root/skills/shiploop/references/state-files.md" \
  || fail "state-files.md missing dest-implement plan.md equality"
grep -q '1. survey —' "$root/skills/shiploop/README.md" \
  || fail "README Look-here matrix missing ordinal survey why"
grep -q '2. spec —' "$root/skills/shiploop/README.md" \
  || fail "README Look-here matrix missing ordinal spec why"
grep -Fq '## How skill logic works' "$root/skills/shiploop/README.md" \
  || fail "README missing How skill logic works H2"
grep -Fq 'Look here is **not interpolated**' "$root/skills/shiploop/README.md" \
  || fail "README missing Look-here not interpolated"
grep -Fq 'Next **is interpolated**' "$root/skills/shiploop/README.md" \
  || fail "README missing Next is interpolated"
grep -Fq '## Files the skill uses' "$root/skills/shiploop/README.md" \
  || fail "README missing Files the skill uses H2"
grep -Fq 'bound_plan_hash' "$root/skills/shiploop/README.md" \
  || fail "README missing bound_plan_hash"
grep -Fq 'bound_plan_hash' "$root/skills/shiploop/references/state-files.md" \
  || fail "state-files.md missing bound_plan_hash"
grep -Fq '## Git sequence (harness vs host)' "$root/skills/shiploop/README.md" \
  || fail "README missing Git sequence H2"
grep -Fq 'git worktree add' "$root/skills/shiploop/README.md" \
  || fail "README missing git worktree add"
grep -Fq 'merge --no-ff --no-edit' "$root/skills/shiploop/README.md" \
  || fail "README missing merge --no-ff --no-edit"
grep -Fq '.git/info/exclude' "$root/skills/shiploop/README.md" \
  || fail "README missing .git/info/exclude"
grep -Fq 'Never `git add -A`' "$root/skills/shiploop/README.md" \
  || fail "README missing Never git add -A"
grep -Fq 'Key learnings:' "$root/skills/shiploop/README.md" \
  || fail "README missing Key learnings:"
if grep -Fq 'When the `/goal` is done: **you** commit on the worktree, then merge' \
  "$root/skills/shiploop/README.md"; then
  fail "README closer still always-commit (want leftover-only)"
fi
if grep -Fq 'Host commits on the worktree, then' \
  "$root/skills/shiploop/README.md"; then
  fail "README mermaid still always-commit (want leftover-only)"
fi
grep -Fq 'leftover uncommitted' "$root/skills/shiploop/README.md" \
  || fail "README missing leftover uncommitted closer"
grep -Fq 'log -10' "$root/skills/shiploop/README.md" \
  || fail "README missing log -10"
grep -Fq 'Key learnings:' "$root/skills/shiploop/commands/shiploop-complete.md" \
  || fail "shiploop-complete.md missing Key learnings:"
grep -Fq 'log -10' "$root/skills/shiploop/commands/shiploop-complete.md" \
  || fail "shiploop-complete.md missing log -10"
grep -Fq 'Implement git' "$root/skills/shiploop/SKILL.md" \
  || fail "SKILL.md missing Implement git paste"
grep -Fq 'Do not paste HOST FLAG' "$root/skills/shiploop/SKILL.md" \
  || fail "SKILL.md missing Do not paste HOST FLAG"
if grep -Fq 'Do not paste worktree, branch, or HOST FLAG' \
  "$root/skills/shiploop/SKILL.md" \
  "$root/skills/shiploop/README.md" \
  "$root/skills/shiploop/references/activities/implement.md" \
  "$root/skills/shiploop/references/turn-packet.md"; then
  fail "paste rule still forbids worktree/branch (Implement git is pasted)"
fi
grep -Fq 'write labeled done_sentence equal to spec' "$root/skills/shiploop/README.md" \
  || fail "README Look-here plan row missing create-why"
grep -Fq 'dest-scoped' "$root/skills/shiploop/README.md" \
  || fail "README Missing not dest-scoped"
grep -Fq 'forward_dest()' "$root/skills/shiploop/README.md" \
  || fail "README Missing missing forward_dest"
grep -Fq 'dest-scoped' "$root/skills/shiploop/references/turn-packet.md" \
  || fail "turn-packet.md Missing not dest-scoped"
if grep -Fq 'Same gaps `update` would refuse' "$root/skills/shiploop/README.md"; then
  fail "README Missing still equates reprint to update dest"
fi
if grep -Fq 'same validator as `update`' "$root/skills/shiploop/references/turn-packet.md"; then
  fail "turn-packet.md Missing still equates reprint to update dest"
fi
if grep -Fq "Host cd's into" "$root/skills/shiploop/README.md"; then
  fail "README mermaid still says Host cd's into worktree"
fi
if grep -Fq 'git merge --no-ff into session HEAD' "$root/skills/shiploop/README.md"; then
  fail "README mermaid still has bare git merge --no-ff"
fi
if grep -Fq '(`git merge --no-ff`)' "$root/skills/shiploop/README.md"; then
  fail "README §4 still has bare git merge --no-ff"
fi
grep -Fq 'git -C <session-checkout> merge --no-ff --no-edit' \
  "$root/skills/shiploop/README.md" \
  || fail "README §4 missing session-checkout merge"
grep -Fq 'git -C <session-checkout> merge --no-ff --no-edit' \
  "$root/skills/shiploop/references/activities/implement.md" \
  || fail "implement.md missing session-checkout merge"
if grep -Fq '`cd` there before pasting' \
  "$root/skills/shiploop/references/activities/implement.md"; then
  fail "implement.md still says cd there before pasting"
fi
if grep -E 'ENV_JSON|SPEC_JSON|IMPLEMENT_JSON|PLAN_JSON|goal_line' "$cli" \
  "$root/skills/shiploop/references/activities/"*.md \
  "$root/skills/shiploop/references/turn-packet.md"; then
  fail "dropped interpolators or goal_line leaked back in"
fi
[[ -f "$fix/existing-app/app.py" ]] || fail "missing existing-app fixture"
[[ -f "$fix/existing-app/README.md" ]] || fail "missing existing-app README"
python3 - "$cli" "$root/skills/shiploop/references/transitions.json" <<'PY' || fail "forbidden phase name"
import ast, json, sys
from pathlib import Path
banned = {"survey", "setup", "initiation", "inject"}
mod = ast.parse(Path(sys.argv[1]).read_text(encoding="utf-8"))
for node in mod.body:
    if not isinstance(node, ast.Assign):
        continue
    for t in node.targets:
        if isinstance(t, ast.Name) and t.id in ("PHASES", "MAP_PHASES"):
            vals = set(ast.literal_eval(node.value))
            leak = banned & vals
            if leak:
                raise SystemExit(f"{t.id} contains {sorted(leak)}")
tj = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
leak = banned & set(tj.get("phases") or [])
if leak:
    raise SystemExit(f"transitions.json phases contains {sorted(leak)}")
phases = tuple(tj.get("phases") or [])
py_phases = None
py_map = None
py_resume = None
for node in mod.body:
    if not isinstance(node, ast.Assign):
        continue
    for t in node.targets:
        if not isinstance(t, ast.Name):
            continue
        if t.id == "PHASES":
            py_phases = tuple(ast.literal_eval(node.value))
        elif t.id == "MAP_PHASES":
            py_map = tuple(ast.literal_eval(node.value))
        elif t.id == "RESUME_PHASES":
            py_resume = tuple(ast.literal_eval(node.value))
if py_phases != phases:
    raise SystemExit(f"PHASES {py_phases!r} != json phases {phases!r}")
expect_map = tuple(p for p in phases if p not in ("halted", "blocked"))
if py_map != expect_map:
    raise SystemExit(f"MAP_PHASES {py_map!r} != {expect_map!r}")
blocked_to = []
seen = set()
for e in tj.get("edges") or []:
    if e.get("from") == "blocked":
        dest = e.get("to")
        if dest not in seen:
            seen.add(dest)
            blocked_to.append(dest)
if py_resume != tuple(blocked_to):
    raise SystemExit(f"RESUME_PHASES {py_resume!r} != blocked edges {tuple(blocked_to)!r}")
for e in tj.get("edges") or []:
    for key in ("from", "to"):
        if e.get(key) in banned:
            raise SystemExit(f"transitions.json edge {key}={e.get(key)}")
src = Path(sys.argv[1]).read_text(encoding="utf-8")
start = src.index("def resolve_dep_roots")
end = src.index("\n\n", start)
body = src[start:end]
for tok in ("frontend-design", "web-design-guidelines", "environment-analyst"):
    if tok in body:
        raise SystemExit(f"resolve_dep_roots names {tok}")
PY
grep -q 'RECAP_HTML' "$root/skills/shiploop/references/activities/residual.md" \
  || fail "residual.md missing RECAP_HTML"
grep -q 'RECAP_HTML' "$root/skills/shiploop/references/activities/residual-waived.md" \
  || fail "residual-waived.md missing RECAP_HTML"
grep -q 'waived' "$root/skills/shiploop/references/activities/residual-waived.md" \
  || fail "residual-waived.md missing waived"
grep -q 'RECAP_HTML' "$root/skills/shiploop/references/activities/done.md" \
  || fail "done.md missing RECAP_HTML"
if grep -q '/speckit' "$root/skills/shiploop/references/survey.md" \
  "$root/skills/shiploop/references/activities/validate-spec.md" \
  "$root/skills/shiploop/references/activities/plan.md"; then
  fail "survey/validate-spec/plan must not name /speckit"
fi
grep -q 'does not rewrite the spec' "$le_docs" || fail "LOOP-ENGINEERING missing no-spec-rewrite"
if grep -qi 'c-plan' <<<"$(sed -n '/^## Compose graph$/,/^## Practices$/p' "$le_docs")"; then
  fail "compose graph must not name c-plan"
fi
grep -q 'emits a `/goal`' "$le_docs" || fail "LOOP-ENGINEERING missing emits a /goal"
grep -q 'Per-step worktree (ShipLoop)' "$le_docs" || fail "LOOP-ENGINEERING missing ShipLoop worktree row"
grep -q 'must not import' "$le_docs" || fail "LOOP-ENGINEERING missing no worktree.py import"
[[ -f "$root/skills/shiploop/README.md" ]] || fail "missing skill README"
[[ -f "$root/skills/shiploop/commands/shiploop.md" ]] || fail "missing commands/shiploop.md"
[[ -f "$root/skills/shiploop/commands/shiploop-next.md" ]] || fail "missing commands/shiploop-next.md"
[[ -f "$root/skills/shiploop/commands/shiploop-complete.md" ]] || fail "missing commands/shiploop-complete.md"
[[ -f "$root/skills/shiploop/scripts/shiploop-next" ]] || fail "missing scripts/shiploop-next"
[[ -f "$root/skills/shiploop/scripts/shiploop-complete" ]] || fail "missing scripts/shiploop-complete"
[[ ! -d "$root/skills/steer" ]] || fail "old steer leaf still present"
[[ ! -d "$root/skills/steer-next" ]] || fail "steer-next sibling still present"
[[ ! -d "$root/skills/steer-complete-next" ]] || fail "steer-complete-next sibling still present"

bash "$root/test/shiploop-testkit.test.sh" \
  || fail "shiploop-testkit.test.sh"
shiploop_suite_begin shiploop
tmpdir="$SUITE_TMP"

HEADINGS='## You are here
## Progress
## Reminder
## Look here
## Next prompt
## When done invoke
## Missing'

HOST_FLAG_LINES='HOST FLAG — extra folder (do not re-root):
ShipLoop creates another folder: a per-step worktree under <repo>/.worktrees/shiploop/<run_id>/<id> on branch shiploop/<run_id>/<id>.
Implementation work happens IN that worktree, not in the session checkout.
Do not move_agent_to_root / re-root the host chat into that folder or the product repo unless the user asked.
The session checkout stays the merge dest; do not edit it during implement.
After /shiploop complete, the harness merges the kept branch into session HEAD and prints Git ran; the next packet names the next worktree.'

assert_host_flag() {
  local haystack="$1" label="$2"
  while IFS= read -r line; do
    printf '%s\n' "$haystack" | grep -qF "$line" || fail "$label missing host flag line: $line"
  done <<<"$HOST_FLAG_LINES"
}

assert_host_flag "$(cat "$root/skills/shiploop/SKILL.md")" "SKILL.md"
assert_host_flag "$(cat "$root/skills/shiploop/references/turn-packet.md")" "turn-packet.md"
script_flag="$(python3 - "$cli" <<'PY'
import ast, sys
from pathlib import Path
mod = ast.parse(Path(sys.argv[1]).read_text(encoding="utf-8"))
for node in mod.body:
    if not isinstance(node, ast.Assign):
        continue
    for t in node.targets:
        if isinstance(t, ast.Name) and t.id == "HOST_WORKTREE_FLAG":
            print("\n".join(ast.literal_eval(node.value)), end="")
            raise SystemExit(0)
raise SystemExit("HOST_WORKTREE_FLAG missing")
PY
)"
[[ "$script_flag" == "$HOST_FLAG_LINES" ]] || fail "HOST_WORKTREE_FLAG != HOST_FLAG_LINES"

assert_headings() {
  local out="$1"
  local prev=""
  while IFS= read -r h; do
    printf '%s\n' "$out" | grep -qxF "$h" || fail "missing heading $h"
    if [[ -n "$prev" ]]; then
      awk -v a="$prev" -v b="$h" '
        $0==a {seen=1; next}
        seen && $0==b {found=1; exit}
        END {exit found?0:1}
      ' <<<"$out" || fail "heading order: $prev then $h"
    fi
    prev="$h"
  done <<<"$HEADINGS"
}

python3 - "$root/skills/shiploop/references/turn-packet.md" "$cli" <<'PY' \
  || fail "turn-packet heading list drifted from print_packet"
import ast, re, sys
from pathlib import Path
doc = Path(sys.argv[1]).read_text(encoding="utf-8")
script = Path(sys.argv[2]).read_text(encoding="utf-8")
match = re.search(r"```text\n((?:## [^\n]+\n)+)```", doc)
assert match, "turn-packet H2 fence missing"
want = re.findall(r"^## .+$", match.group(1), flags=re.M)
tree = ast.parse(script)
packet = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "print_packet")
got = [
    node.args[0].value
    for node in ast.walk(packet)
    if isinstance(node, ast.Call)
    and isinstance(node.func, ast.Name)
    and node.func.id == "print"
    and node.args
    and isinstance(node.args[0], ast.Constant)
    and isinstance(node.args[0].value, str)
    and node.args[0].value.startswith("## ")
]
assert got == want, (got, want)
PY

python3 - "$root/skills/shiploop/references/ledger-contract.md" "$cli" <<'PY' \
  || fail "ledger-contract regex source drifted from shiploop"
import sys
from pathlib import Path
contract = Path(sys.argv[1]).read_text(encoding="utf-8")
script = Path(sys.argv[2]).read_text(encoding="utf-8")
needles = (
    r"(?im)\bStatus\b[^\n]*(?P<state>stopped\s*\([^\n)]*\)|complete\b|active\b)",
    r"(?im)^\*\*Plan contract:\*\*\s*`?(?P<path>[^`\n]+?)`?\s*$",
    r"(?im)^\*\*Plan hash:\*\*\s*`?(?P<hash>[0-9a-fA-F]{64})`?",
    r"(?im)^\*\*Committed:\*\*\s*yes\b",
    r"(?im)(?:review-converge|grok-review-converge):\s*round\s+\d+\s*—",
)
for needle in needles:
    assert needle in contract, needle
    assert needle in script, needle
PY

assert_absent() {
  local out="$1" pat="$2" msg="$3"
  if printf '%s\n' "$out" | grep -q -- "$pat"; then
    fail "$msg"
  fi
}

assert_no_wrapper_lookhere() {
  local look="$1" msg="$2"
  local hits
  hits="$(printf '%s\n' "$look" | grep -E '^(required|if-needed)  .+/plan.json' | grep -v '/backchain/plan.json' || true)"
  [[ -z "$hits" ]] || fail "$msg: $hits"
}

run_cli() { python3 "$cli" "$@"; }

complete_ok() {
  local run="$1" sid="$2"
  commit_step_work "$run" "$sid"
  merge_step_branch "$run" "$sid"
  run_cli complete-step --run-dir "$run" --id "$sid" >/dev/null
}

DS='result.txt contains exactly one line: ok'

write_spec() {
  local run="$1"
  printf 'done_sentence: %s\ncheckable: true\n' "$DS" >"$run/spec.md"
  rm -f "$run/spec.json"
}

write_recap() {
  local run="$1"
  cat >"$run/recap.html" <<'HTML'
<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>ShipLoop recap</title></head>
<body>
<h1>Walk-back</h1>
<h2>Intent</h2><p>Create result.txt with one line ok.</p>
<h2>Accomplished</h2><p>The increment shipped.</p>
<h2>Materially changed</h2><p>result.txt and the session DAG.</p>
<h2>Outcome</h2><p>done_sentence holds.</p>
<h2>Verified</h2><p>shiploop hermetic layers plus the bound test command.</p>
</body></html>
HTML
}

write_environment() {
  local run="$1"
  local kind="${2:-greenfield}"
  local augment="${3:-false}"
  cat >"$run/environment.md" <<MD
Session survey brief for the test harness.

## machine
\`\`\`json
{"kind": "$kind", "augment": $augment, "references": [], "tools": [], "mcp": [],
 "mcp_considered": "none(no read-capable session tool matched done-sentence)",
 "handles": [], "initiation": "none", "ui": false, "ui_craft": "none(no UI in scope)",
 "exclusive": []}
\`\`\`
MD
}

write_machine() {
  local run="$1"
  local json="$2"
  cat >"$run/environment.md" <<MD
Session survey brief for the test harness.

## machine
\`\`\`json
${json}
\`\`\`
MD
}

fresh_vs() {
  local run="$1" repo="$2"
  mkdir -p "$repo"
  init_git_repo "$repo"
  run_cli init --prompt "create result.txt containing exactly one line: ok" \
    --run-dir "$run" --bound-plan "$planf" --repo "$repo" >/dev/null
  run_cli update --run-dir "$run" --to validate-spec >/dev/null
  write_spec "$run"
}

write_plan_md() {
  local run="$1"
  printf 'done_sentence: %s\n' "$DS" >"$run/plan.md"
}

install_dag() {
  local run="$1" fixture="$2"
  mkdir -p "$run/backchain"
  cp "$fix/$fixture" "$run/backchain/plan.json"
  write_plan_md "$run"
}

advance_to_plan() {
  local run="$1" repo="$2" planf="$3"
  init_git_repo "$repo"
  run_cli init --prompt "create result.txt containing exactly one line: ok" \
    --run-dir "$run" --bound-plan "$planf" --repo "$repo" >/dev/null
  run_cli update --run-dir "$run" --to validate-spec >/dev/null
  write_environment "$run"
  write_spec "$run"
  run_cli update --run-dir "$run" --to plan >/dev/null
}

# --- non-host implementer refused; host default ---
set +e
out_dl="$(run_cli init --implementer other --run-dir "$tmpdir/nope" 2>&1)"
rc_dl=$?
set -e
[[ "$rc_dl" -eq 2 ]] || fail "non-host implementer want 2 got $rc_dl: $out_dl"
printf '%s\n' "$out_dl" | grep -qi 'implementer must be host' || fail "non-host implementer message: $out_dl"
printf 'LAYER: non-host implementer refused OK\n'

# --- init + packet headings ---
repo="$tmpdir/repo"
init_git_repo "$repo"
planf="$tmpdir/bound.plan.md"
cat >"$planf" <<'MD'
# Bound

## Review Coverage
filled for later waiver tests
MD
run="$repo/.shiploop"
out_init="$(run_cli init --prompt "create result.txt containing exactly one line: ok" \
  --run-dir "$run" --bound-plan "$planf" --repo "$repo")"
printf '%s\n' "$out_init" | grep -q 'initialized' || fail "init: $out_init"
assert_headings "$out_init"
printf '%s\n' "$out_init" | grep -q 'intake: current' || fail "map current intake"
printf '%s\n' "$out_init" | grep -q 'validate-spec: todo' || fail "map todo"
printf '%s\n' "$out_init" | grep -q 'prompt\.md' || fail "look here intake prompt.md path"
printf '%s\n' "$out_init" | grep -q 'invoke /shiploop complete' || fail "when done closer"
printf '%s\n' "$out_init" | grep -q 'shiploop — session harness' || fail "init missing harness banner"
assert_absent "$out_init" 'DevLoop' "init banner named a foreign product"
printf '%s\n' "$out_init" | grep -qF 'Reference only — not the next action.' || fail "look here missing reference-only line"
printf '%s\n' "$out_init" | grep -qF 'Use this prompt as much as possible.' || fail "next prompt missing banner line"
assert_absent "$out_init" 'shiploop update --run-dir' "init When done leaked update argv"
python3 - "$run/state.json" <<'PY'
import json, sys
from pathlib import Path
d = json.loads(Path(sys.argv[1]).read_text())
arts = d.get("artifacts") or {}
assert "plan_json" not in arts, arts
assert "plan_md" in arts, arts
assert "backchain" in arts, arts
PY
printf '%s\n' "$out_init" | grep -q 'Ask: create result.txt' || fail "reminder ask"
printf '%s\n' "$out_init" | grep -qx 'Diagnosis' || fail "init missing Diagnosis"
printf '%s\n' "$out_init" | grep -q 'spec       (not written)' || fail "init spec stand"
printf '%s\n' "$out_init" | grep -q 'now' || fail "init diagnosis now"
printf '%s\n' "$out_init" | grep -q 'intake  record the original ask' || fail "init now intake"
awk '/^Diagnosis$/{d=1} d && /^## Reminder$/{found=1} END{exit found?0:1}' <<<"$out_init" \
  || fail "Diagnosis must precede Reminder"
printf '%s\n' "$out_init" | grep -qx '## Progress' || fail "init missing Progress"
printf '%s\n' "$out_init" | grep -q 'Beginning this phase:' || fail "init Progress missing begin"
printf '%s\n' "$out_init" | grep -q 'Finish this phase:' || fail "init Progress missing finish"
printf '%s\n' "$out_init" | grep -q 'session checkout' || fail "init Progress missing checkout"
assert_host_flag "$out_init" "init Progress"
printf 'LAYER: init packet OK\n'

# --- init --repo defaults run dir to PATH/.shiploop ---
othercwd="$tmpdir/other-cwd"
mkdir -p "$othercwd"
repodef="$tmpdir/repodefault/repo"
init_git_repo "$repodef"
(
  cd "$othercwd"
  python3 "$cli" init --prompt "x" --repo "$repodef" >/dev/null
)
[[ -f "$repodef/.shiploop/state.json" ]] || fail "init --repo did not write PATH/.shiploop"
[[ ! -d "$othercwd/.shiploop" ]] || fail "init --repo wrote cwd/.shiploop"
printf 'LAYER: init --repo run-dir default OK\n'

# --- status --human compact rail ---
out_h="$(run_cli status --run-dir "$run" --human)"
printf '%s\n' "$out_h" | grep -q '## You are here' || fail "status --human missing You are here: $out_h"
printf '%s\n' "$out_h" | grep -qx 'Diagnosis' || fail "status --human missing Diagnosis: $out_h"
printf '%s\n' "$out_h" | grep -q 'now' || fail "status --human missing now: $out_h"
printf '%s\n' "$out_h" | grep -q 'pending' || fail "status --human missing pending: $out_h"
assert_absent "$out_h" '"phase"' "status --human printed JSON"
out_sj="$(run_cli status --run-dir "$run")"
printf '%s\n' "$out_sj" | grep -q '"phase"' || fail "status default missing JSON phase"
printf 'LAYER: status --human OK\n'

# --- init reuse vs force ---
out_re="$(run_cli init --run-dir "$run")"
printf '%s\n' "$out_re" | grep -q 'reused' || fail "reuse: $out_re"
run_cli init --force --prompt "second" --run-dir "$run" --bound-plan "$planf" --repo "$repo" >/dev/null
grep -q 'second' "$run/prompt.md" || fail "force did not reset prompt"
run_cli init --force --prompt "create result.txt containing exactly one line: ok" \
  --run-dir "$run" --bound-plan "$planf" --repo "$repo" >/dev/null
printf 'LAYER: reuse vs force OK\n'

# --- init does not adopt ancestor .shiploop ---
mkdir -p "$tmpdir/tree/child"
python3 "$cli" init --prompt "parent" --run-dir "$tmpdir/tree/.shiploop" >/dev/null
(
  cd "$tmpdir/tree/child"
  python3 "$cli" init --prompt "child-only" >/dev/null
)
[[ -f "$tmpdir/tree/child/.shiploop/state.json" ]] || fail "child init missing"
grep -q 'child-only' "$tmpdir/tree/child/.shiploop/prompt.md" || fail "child used ancestor"
printf 'LAYER: init no ancestor adopt OK\n'

# --- package-root write refuse ---
set +e
out_pkg="$(run_cli init --prompt x --run-dir "$root/skills/shiploop/.shiploop" 2>&1)"
rc_pkg=$?
set -e
[[ "$rc_pkg" -eq 2 ]] || fail "package write want 2 got $rc_pkg: $out_pkg"
printf 'LAYER: package-root refuse OK\n'

# --- update walks cwd .shiploop ---
(
  cd "$repo"
  run_cli update --to validate-spec >/dev/null
)
empty_cwd="$tmpdir/no-shiploop-cwd"
mkdir -p "$empty_cwd"
set +e
out_urd="$(cd "$empty_cwd" && run_cli update --to validate-spec 2>&1)"
rc_urd=$?
set -e
[[ "$rc_urd" -ne 0 ]] || fail "update without .shiploop should fail: $out_urd"
printf 'LAYER: update walks cwd OK\n'

# --- intake -> validate-spec ---
out_vs="$(run_cli next --run-dir "$run")"
assert_headings "$out_vs"
printf '%s\n' "$out_vs" | grep -q 'intake: done' || fail "intake done"
printf '%s\n' "$out_vs" | grep -q 'validate-spec: current' || fail "vs current"
printf '%s\n' "$out_vs" | grep -q '1. survey — write this first (create)' \
  || fail "validate-spec Look-here missing ordinal survey create: $out_vs"
printf '%s\n' "$out_vs" | grep -q '2. spec — write after environment.md (create)' \
  || fail "validate-spec Look-here missing ordinal spec create: $out_vs"
assert_absent "$out_vs" 'not written yet' "validate-spec Look-here still used exists/absent not written yet"
miss_vs="$(packet_section "$out_vs" "## Missing")"
printf '%s\n' "$miss_vs" | grep -q 'missing ' || fail "validate-spec Missing empty: $miss_vs"
printf '%s\n' "$miss_vs" | grep -q 'environment.md' \
  || fail "validate-spec Missing missing environment.md: $miss_vs"
printf '%s\n' "$miss_vs" | grep -q 'spec.md' \
  || fail "validate-spec Missing missing spec.md: $miss_vs"
assert_absent "$out_vs" 'VALIDATE_SPEC_PATH' "packet leaked VALIDATE_SPEC_PATH"
assert_absent "$out_vs" 'missing dep_roots.devloop' "devloop required at validate-spec"
assert_absent "$out_vs" '/goal ' "validate-spec packet emitted implement /goal"
printf '%s\n' "$out_vs" | grep -q 'references/survey.md' \
  || fail "validate-spec packet missing interpolated SURVEY_GUIDE path"
printf '%s\n' "$out_vs" | grep -q 'environment.md' \
  || fail "validate-spec packet missing interpolated ENV_MD path"
printf '%s\n' "$out_vs" | grep -qF "$(cd "$repo" && pwd -P)" \
  || fail "validate-spec packet missing interpolated REPO_ROOT"
assert_absent "$out_vs" '{{SURVEY_GUIDE}}' "packet leaked {{SURVEY_GUIDE}}"
assert_absent "$out_vs" '{{ENV_MD}}' "packet leaked {{ENV_MD}}"
assert_absent "$out_vs" '{{REPO_ROOT}}' "packet leaked {{REPO_ROOT}}"
printf '%s\n' "$out_vs" | grep -q 'references/state-files.md' \
  || fail "validate-spec packet missing interpolated STATE_FILES path"
assert_absent "$out_vs" '{{STATE_FILES}}' "packet leaked {{STATE_FILES}}"
assert_absent "$out_vs" '`references/state-files.md`' "validate-spec leaked relative state-files"
next_vs="$(packet_section "$out_vs" "## Next prompt")"
printf '%s\n' "$next_vs" | grep -Fq 'Deeply research those MCP servers' \
  || fail "validate-spec Next missing Deeply research: $next_vs"
printf '%s\n' "$next_vs" | grep -Fiq 'reuse before add' \
  || fail "validate-spec Next missing reuse before add: $next_vs"
printf '%s\n' "$next_vs" | grep -Fq 'Do not duplicate, conflict with, or arbitrarily add' \
  || fail "validate-spec Next missing arbitrarily add: $next_vs"
printf '%s\n' "$next_vs" | grep -q '^### 2. Best-practice' \
  || fail "validate-spec Next missing ### job 2 heading: $next_vs"
printf '%s\n' "$next_vs" | grep -q '^### 3. Spec' \
  || fail "validate-spec Next missing ### job 3 heading: $next_vs"
if printf '%s\n' "$next_vs" | grep -E '^## '; then
  fail "validate-spec Next leaked packet-level H2: $next_vs"
fi
look_vs="$(packet_section "$out_vs" "## Look here")"
printf '%s\n' "$look_vs" | grep -q 'references/survey.md' \
  || fail "validate-spec Look-here missing survey.md: $look_vs"
if printf '%s\n' "$look_vs" | grep -Fq 'Deeply research those MCP servers'; then
  fail "validate-spec Look-here leaked job 2 research: $look_vs"
fi
python3 - "$next_vs" "$run" "$repo" <<'PY' || fail "validate-spec Next job-2 slice missing interpolated ENV_MD/REPO_ROOT"
from pathlib import Path
import sys
text, run, repo = sys.argv[1], sys.argv[2], sys.argv[3]
i = text.find("### 2. Best-practice")
j = text.find("### 3. Spec")
assert i != -1 and j > i, (i, j)
s = text[i:j]
env_raw = str(Path(run) / "environment.md")
env_res = str((Path(run) / "environment.md").resolve())
assert env_raw in s or env_res in s, s[:400]
root_raw = str(Path(repo))
root_res = str(Path(repo).resolve())
assert root_raw in s or root_res in s, s[:400]
PY
printf 'LAYER: intake->validate-spec OK\n'

# --- validate-spec Look-here uses load_environment / load_spec gaps ---
printf 'brief only, no machine heading\n' >"$run/environment.md"
out_envstub="$(run_cli next --run-dir "$run")"
printf '%s\n' "$out_envstub" | grep -q "1. survey — environment.md missing a '## machine' section" \
  || fail "env stub Look-here missing ## machine gap: $out_envstub"
printf '%s\n' "$out_envstub" | grep -q '2. spec — write after environment.md (create)' \
  || fail "env stub still lists spec as write-after-env: $out_envstub"
assert_absent "$out_envstub" 'not written yet' "env stub Look-here used not written yet"
write_environment "$run"
out_envok="$(run_cli next --run-dir "$run")"
printf '%s\n' "$out_envok" | grep -q '1. survey — written' \
  || fail "complete env Look-here missing written: $out_envok"
printf '%s\n' "$out_envok" | grep -q '2. spec — write after environment.md (create)' \
  || fail "complete env + missing spec Look-here: $out_envok"
printf 'body\n' >"$run/spec.md"
out_specgap="$(run_cli next --run-dir "$run")"
printf '%s\n' "$out_specgap" | grep -q '1. survey — written' \
  || fail "spec-gap Look-here lost written env: $out_specgap"
printf '%s\n' "$out_specgap" | grep -q '2. spec — spec.md missing labeled done_sentence' \
  || fail "spec-gap Look-here missing load_spec why: $out_specgap"
printf '%s\n' "$out_specgap" | grep -q 'spec.md missing labeled checkable' \
  || fail "spec-gap Look-here missing checkable why: $out_specgap"
printf '' >"$run/environment.md"
out_emptyenv="$(run_cli next --run-dir "$run")"
printf '%s\n' "$out_emptyenv" | grep -q '1. survey — environment.md is empty' \
  || fail "empty env Look-here: $out_emptyenv"
write_environment "$run"
write_spec "$run"
out_both="$(run_cli next --run-dir "$run")"
printf '%s\n' "$out_both" | grep -q '1. survey — written' \
  || fail "both-written Look-here env: $out_both"
printf '%s\n' "$out_both" | grep -q '2. spec — written' \
  || fail "both-written Look-here spec: $out_both"
miss_both="$(packet_section "$out_both" "## Missing")"
printf '%s\n' "$miss_both" | grep -qx '(none)' \
  || fail "both-written dest plan Missing should be none: $miss_both"
rm -f "$run/spec.md" "$run/environment.md"
printf 'LAYER: validate-spec Look-here load_* gaps OK\n'

# --- empty spec.md rejected (no labels at all) ---
printf 'body\n' >"$run/spec.md"
set +e
out_es="$(run_cli update --run-dir "$run" --to plan 2>&1)"
rc_es=$?
set -e
[[ "$rc_es" -eq 2 ]] || fail "empty spec want 2: $out_es"
printf 'LAYER: empty spec.md reject OK\n'

# --- duplicate done_sentence label rejected ---
printf 'done_sentence: alpha\ncheckable: true\ndone_sentence: beta\n' >"$run/spec.md"
out_dup="$(run_cli next --run-dir "$run")"
printf '%s\n' "$out_dup" | grep -q '2. spec — spec.md labeled done_sentence: must appear exactly once' \
  || fail "duplicate spec Look-here: $out_dup"
set +e
out_mm="$(run_cli update --run-dir "$run" --to plan 2>&1)"
rc_mm=$?
set -e
[[ "$rc_mm" -eq 2 ]] || fail "mismatch want 2: $out_mm"
printf '%s\n' "$out_mm" | grep -qi 'done_sentence' || fail "mismatch message: $out_mm"
printf 'LAYER: labeled once-only reject OK\n'

# --- checkable false -> blocked (dest blocked hatch does not require environment.md) ---
rm -f "$run/environment.md"
printf 'done_sentence: need a checkable done\ncheckable: false\nask_user: what is the oracle?\n\nmore spec prose that must not be dumped later\n' >"$run/spec.md"
out_hatch="$(run_cli next --run-dir "$run")"
printf '%s\n' "$out_hatch" | grep -q '1. survey — write this first (create)' \
  || fail "hatch Look-here missing survey-first: $out_hatch"
printf '%s\n' "$out_hatch" | grep -q '2. spec — written' \
  || fail "hatch Look-here spec should be written: $out_hatch"
printf '%s\n' "$out_hatch" | grep -q 'validate-spec: current' \
  || fail "hatch still validate-spec: $out_hatch"
printf '%s\n' "$out_hatch" | grep -q 'complete --blocked' \
  || fail "hatch When done missing --blocked: $out_hatch"
run_cli update --run-dir "$run" --to blocked --reason "what is the oracle?" --resume-to validate-spec >/dev/null
out_blk="$(run_cli next --run-dir "$run")"
printf '%s\n' "$out_blk" | grep -q 'blocked: current' || fail "blocked current: $out_blk"
printf '%s\n' "$out_blk" | grep -q 'complete --reason' || fail "blocked When done missing complete --reason: $out_blk"
assert_absent "$out_blk" 'complete --blocked' "already-blocked packet printed --blocked"
assert_absent "$out_blk" '/shiploop update' "blocked packet named slash update"
assert_absent "$out_blk" 'more spec prose that must not be dumped later' "reminder dumped spec body"
set +e
out_jumpvs="$(run_cli update --run-dir "$run" --to implement 2>&1)"
rc_jumpvs=$?
set -e
[[ "$rc_jumpvs" -eq 2 ]] || fail "blocked validate-spec resume jumped to implement: $out_jumpvs"
run_cli complete --run-dir "$run" --reason "user answered" >/dev/null
python3 - "$run" <<'PY'
import json, sys
from pathlib import Path
d = json.loads((Path(sys.argv[1]) / "state.json").read_text())
assert d["phase"] == "validate-spec", d["phase"]
PY
printf 'LAYER: checkable false -> blocked OK\n'

# --- missing environment.md blocks dest plan even with a checkable spec ---
write_spec "$run"
set +e
out_noenv="$(run_cli update --run-dir "$run" --to plan 2>&1)"
rc_noenv=$?
set -e
[[ "$rc_noenv" -eq 2 ]] || fail "missing environment.md want 2: $out_noenv"
printf '%s\n' "$out_noenv" | grep -qi 'environment.md' || fail "missing environment.md message: $out_noenv"
printf 'LAYER: missing environment.md blocks plan OK\n'

# --- handle resolve=list/ask blocks dest plan; create is dest-plan-legal ---
cat >"$run/environment.md" <<'MD'
Brief.

## machine
```json
{"kind": "greenfield", "augment": false, "references": [], "tools": [], "mcp": [],
 "mcp_considered": "none(no read-capable session tool matched done-sentence)",
 "handles": [{"source": "gh", "need": "repo id", "resolve": "list", "value": ""}],
 "initiation": "none", "ui": false, "ui_craft": "none(no UI in scope)"}
```
MD
set +e
out_handle="$(run_cli update --run-dir "$run" --to plan 2>&1)"
rc_handle=$?
set -e
[[ "$rc_handle" -eq 2 ]] || fail "handle list blocks plan want 2: $out_handle"
printf '%s\n' "$out_handle" | grep -qi 'blocks dest plan' || fail "handle block message: $out_handle"
cat >"$run/environment.md" <<'MD'
Brief.

## machine
```json
{"kind": "greenfield", "augment": false, "references": [], "tools": [], "mcp": [],
 "mcp_considered": "none(no read-capable session tool matched done-sentence)",
 "handles": [{"source": "gh", "need": "repo id", "resolve": "create", "value": ""}],
 "initiation": "needed", "ui": false, "ui_craft": "none(no UI in scope)",
 "exclusive": []}
```
MD
run_cli update --run-dir "$run" --to plan >/dev/null
printf 'LAYER: handle resolve gates OK\n'

# --- happy spec + thin plan cannot implement ---
out_plan="$(run_cli next --run-dir "$run")"
assert_headings "$out_plan"
assert_absent "$out_plan" '/goal ' "plan packet emitted implement /goal"
printf '%s\n' "$out_plan" | grep -q 'After it finishes: dest implement' \
  || fail "plan-before-DAG dest should be implement: $out_plan"
printf '%s\n' "$out_plan" | awk '/^## When done invoke$/,/^## Missing$/' \
  | grep -q 'complete --blocked' \
  && fail "plan-before-DAG When done dest blocked: $out_plan"
printf '%s\n' "$out_plan" | grep -qx 'invoke /shiploop complete' \
  || fail "plan-before-DAG When done should be complete: $out_plan"
assert_absent "$out_plan" '{{PLAN_JSON}}' "plan packet leaked retired PLAN_JSON"
look_plan="$(packet_section "$out_plan" "## Look here")"
printf '%s\n' "$look_plan" | grep -q 'plan.md' || fail "plan Look-here missing plan.md: $look_plan"
printf '%s\n' "$look_plan" | grep -q 'write labeled done_sentence equal to spec (create)' \
  || fail "plan Look-here missing plan.md create why: $look_plan"
printf '%s\n' "$look_plan" | grep -q 'backchain' \
  || fail "plan Look-here missing DAG: $look_plan"
assert_no_wrapper_lookhere "$look_plan" "plan Look-here listed retired wrapper"
prog_plan="$(packet_section "$out_plan" "## Progress")"
printf '%s\n' "$prog_plan" | grep -q 'write plan.md' \
  || fail "plan Progress missing write plan.md: $prog_plan"
assert_absent "$prog_plan" 'plan.json wrapper' "plan Progress still names plan.json wrapper"
miss_plan="$(packet_section "$out_plan" "## Missing")"
printf '%s\n' "$miss_plan" | grep -q 'plan.md' \
  || fail "plan Missing missing plan.md: $miss_plan"
printf '%s\n' "$miss_plan" | grep -q 'backchain' \
  || fail "plan Missing missing backchain DAG: $miss_plan"
assert_absent "$miss_plan" 'plan.json.done_sentence' "plan Missing named wrapper field"
printf '{not-json' >"$run/plan.json"
out_plan_left="$(run_cli next --run-dir "$run")"
look_left="$(packet_section "$out_plan_left" "## Look here")"
assert_no_wrapper_lookhere "$look_left" "plan Look-here listed leftover wrapper"
rm -f "$run/plan.json"
printf 'LAYER: plan-before-DAG dest implement OK\n'
printf 'done_sentence: %s\n\nsteps: write file\n' "$DS" >"$run/plan.md"
set +e
out_thin="$(run_cli update --run-dir "$run" --to implement 2>&1)"
rc_thin=$?
set -e
[[ "$rc_thin" -eq 2 ]] || fail "thin plan want 2: $out_thin"
printf 'LAYER: thin plan reject OK\n'

# --- dest implement names a missing HEAD on a git repo with no commits ---
eh="$tmpdir/empty-head"
mkdir -p "$eh"
git -C "$eh" init >/dev/null
git -C "$eh" config user.email "shiploop-test@example.com"
git -C "$eh" config user.name "ShipLoop Test"
git -C "$eh" config commit.gpgsign false
run_cli init --prompt "create result.txt containing exactly one line: ok" \
  --run-dir "$eh/.shiploop" --repo "$eh" >/dev/null
write_spec "$eh/.shiploop"
write_environment "$eh/.shiploop"
run_cli update --run-dir "$eh/.shiploop" --to validate-spec >/dev/null
run_cli update --run-dir "$eh/.shiploop" --to plan >/dev/null
install_dag "$eh/.shiploop" linear.json
set +e
out_eh="$(run_cli update --run-dir "$eh/.shiploop" --to implement 2>&1)"
rc_eh=$?
set -e
[[ "$rc_eh" -eq 2 ]] || fail "empty HEAD want 2: $out_eh"
printf '%s\n' "$out_eh" | grep -q 'repo has no HEAD commit' \
  || fail "empty HEAD message: $out_eh"
printf 'LAYER: empty HEAD dest implement message OK\n'

# --- dest implement: plan.md vs spec; leftover plan.json inert ---
runpj="$tmpdir/planjson-retired/.shiploop"
repopj="$tmpdir/planjson-retired/repo"
mkdir -p "$repopj"
advance_to_plan "$runpj" "$repopj" "$planf"
install_dag "$runpj" linear.json
[[ ! -f "$runpj/plan.json" ]] || fail "install_dag wrote retired plan.json wrapper"
printf '%s\n' "{\"done_sentence\":\"WRONG\",\"step_ids\":[\"S1\"]}" >"$runpj/plan.json"
run_cli update --run-dir "$runpj" --to implement >/dev/null
[[ -f "$runpj/plan.json" ]] || fail "leftover plan.json should stay on disk"
python3 - "$runpj/plan.json" <<'PY'
import json, sys
from pathlib import Path
d = json.loads(Path(sys.argv[1]).read_text())
assert d.get("done_sentence") == "WRONG", d
assert d.get("step_ids") == ["S1"], d
PY
out_pj="$(run_cli next --run-dir "$runpj")"
printf '%s\n' "$out_pj" | grep -q 'S1: running' || fail "leftover wrapper hid S1: $out_pj"
look_pj="$(packet_section "$out_pj" "## Look here")"
assert_no_wrapper_lookhere "$look_pj" "implement Look-here listed leftover wrapper"
printf '%s\n' "$look_pj" | grep -q 'plan.md' || fail "implement Look-here missing if-needed plan.md"
printf 'done_sentence: mutated after bind\n' >"$runpj/plan.md"
set +e
out_post="$(run_cli next --run-dir "$runpj" 2>&1)"
rc_post=$?
set -e
[[ "$rc_post" -eq 0 ]] || fail "post-bind plan.md edit should not fail-closed: $out_post"
printf '%s\n' "$out_post" | grep -q 'S1: running' || fail "post-bind plan.md edit lost S1: $out_post"
look_post="$(packet_section "$out_post" "## Look here")"
assert_absent "$look_post" 'plan.md labeled done_sentence must equal spec.md' \
  "implement Look-here re-litigated dest-implement equality after allowed drift"

runbad="$tmpdir/planjson-bad/.shiploop"
repobad="$tmpdir/planjson-bad/repo"
mkdir -p "$repobad"
advance_to_plan "$runbad" "$repobad" "$planf"
install_dag "$runbad" linear.json
printf '{' >"$runbad/plan.json"
run_cli update --run-dir "$runbad" --to implement >/dev/null
out_bad="$(run_cli next --run-dir "$runbad")"
printf '%s\n' "$out_bad" | grep -q 'S1: running' || fail "malformed leftover wrapper blocked dest: $out_bad"
out_injbad="$(run_cli inject-step --run-dir "$runbad" --statement "mid bind" --prompt $'/goal\nDo this activity until these conditions are met:\n- mid exists' --produces "mid exists" --before S2 --id S3)"
printf '%s\n' "$out_injbad" | grep -q 'injected S3' || fail "inject with malformed leftover wrapper: $out_injbad"
python3 - "$runbad/plan.json" <<'PY'
from pathlib import Path
import sys
raw = Path(sys.argv[1]).read_text()
assert raw == "{", raw
PY

runds="$tmpdir/planmd-drift/.shiploop"
repods="$tmpdir/planmd-drift/repo"
mkdir -p "$repods"
advance_to_plan "$runds" "$repods" "$planf"
install_dag "$runds" linear.json
out_okpl="$(run_cli next --run-dir "$runds")"
look_okpl="$(packet_section "$out_okpl" "## Look here")"
printf '%s\n' "$look_okpl" | grep -q 'sequence plan pointer' \
  || fail "valid plan.md Look-here missing pointer: $look_okpl"
assert_absent "$look_okpl" 'plan.md empty' "valid plan.md Look-here named empty"
printf '' >"$runds/plan.md"
out_emptypl="$(run_cli next --run-dir "$runds")"
printf '%s\n' "$(packet_section "$out_emptypl" "## Look here")" | grep -q 'plan.md empty' \
  || fail "empty plan.md Look-here missing gap: $out_emptypl"
printf 'steps only, no label\n' >"$runds/plan.md"
out_unlab="$(run_cli next --run-dir "$runds")"
printf '%s\n' "$(packet_section "$out_unlab" "## Look here")" \
  | grep -q 'plan.md labeled done_sentence missing' \
  || fail "unlabeled plan.md Look-here missing gap: $out_unlab"
printf '%s\n' "$(packet_section "$out_unlab" "## Missing")" \
  | grep -q 'plan.md labeled done_sentence missing' \
  || fail "unlabeled plan.md Missing missing gap: $out_unlab"
printf 'done_sentence: other sentence\n' >"$runds/plan.md"
out_driftpl="$(run_cli next --run-dir "$runds")"
printf '%s\n' "$(packet_section "$out_driftpl" "## Look here")" \
  | grep -q 'plan.md labeled done_sentence must equal spec.md' \
  || fail "drifted plan.md Look-here missing equality gap: $out_driftpl"
set +e
out_dsd="$(run_cli update --run-dir "$runds" --to implement 2>&1)"
rc_dsd=$?
set -e
[[ "$rc_dsd" -eq 2 ]] || fail "drifted plan.md want 2: $out_dsd"
printf '%s\n' "$out_dsd" | grep -q 'plan.md labeled done_sentence must equal spec.md' \
  || fail "drifted plan.md message: $out_dsd"
assert_absent "$out_dsd" 'plan.json.done_sentence' "drifted plan.md still named wrapper field"
rm -f "$runds/plan.md"
set +e
out_mdp="$(run_cli update --run-dir "$runds" --to implement 2>&1)"
rc_mdp=$?
set -e
[[ "$rc_mdp" -eq 2 ]] || fail "missing plan.md want 2: $out_mdp"
printf '%s\n' "$out_mdp" | grep -q 'missing ' || fail "missing plan.md message: $out_mdp"
printf '%s\n' "$out_mdp" | grep -q 'plan.md' || fail "missing plan.md named the file: $out_mdp"
assert_absent "$out_mdp" 'plan.json.done_sentence' "missing plan.md still named wrapper field"
printf '' >"$runds/plan.md"
set +e
out_mde="$(run_cli update --run-dir "$runds" --to implement 2>&1)"
rc_mde=$?
set -e
[[ "$rc_mde" -eq 2 ]] || fail "empty plan.md want 2: $out_mde"
printf '%s\n' "$out_mde" | grep -q 'plan.md empty' || fail "empty plan.md message: $out_mde"
printf 'steps only, no label\n' >"$runds/plan.md"
set +e
out_mdl="$(run_cli update --run-dir "$runds" --to implement 2>&1)"
rc_mdl=$?
set -e
[[ "$rc_mdl" -eq 2 ]] || fail "unlabeled plan.md want 2: $out_mdl"
printf '%s\n' "$out_mdl" | grep -q 'plan.md labeled done_sentence missing' \
  || fail "unlabeled plan.md message: $out_mdl"
printf 'done sentence: %s\n' "$DS" >"$runds/plan.md"
set +e
out_mdsp="$(run_cli update --run-dir "$runds" --to implement 2>&1)"
rc_mdsp=$?
set -e
[[ "$rc_mdsp" -eq 2 ]] || fail "done-sentence space label want 2: $out_mdsp"
printf '%s\n' "$out_mdsp" | grep -q 'plan.md labeled done_sentence missing' \
  || fail "done-sentence space label message: $out_mdsp"
printf 'done_sentence: %s\ndone_sentence: %s\n' "$DS" "$DS" >"$runds/plan.md"
set +e
out_mdd="$(run_cli update --run-dir "$runds" --to implement 2>&1)"
rc_mdd=$?
set -e
[[ "$rc_mdd" -eq 2 ]] || fail "duplicate plan.md labels want 2: $out_mdd"
printf '%s\n' "$out_mdd" | grep -q 'plan.md labeled done_sentence must appear exactly once' \
  || fail "duplicate plan.md labels message: $out_mdd"

runfence="$tmpdir/planmd-fence/.shiploop"
repofence="$tmpdir/planmd-fence/repo"
mkdir -p "$repofence"
advance_to_plan "$runfence" "$repofence" "$planf"
install_dag "$runfence" linear.json
cat >"$runfence/plan.md" <<MD
intro

\`\`\`text
done_sentence: WRONG
\`\`\`

done_sentence: $DS
MD
run_cli update --run-dir "$runfence" --to implement >/dev/null
out_fence="$(run_cli next --run-dir "$runfence")"
printf '%s\n' "$out_fence" | grep -q 'S1: running' || fail "fenced WRONG + labeled spec dest: $out_fence"

runfo="$tmpdir/planmd-fence-only/.shiploop"
repofo="$tmpdir/planmd-fence-only/repo"
mkdir -p "$repofo"
advance_to_plan "$runfo" "$repofo" "$planf"
install_dag "$runfo" linear.json
cat >"$runfo/plan.md" <<MD
intro

\`\`\`text
done_sentence: $DS
\`\`\`
MD
set +e
out_fence_only="$(run_cli update --run-dir "$runfo" --to implement 2>&1)"
rc_fence_only=$?
set -e
[[ "$rc_fence_only" -eq 2 ]] || fail "fenced-only plan.md want 2: $out_fence_only"
printf '%s\n' "$out_fence_only" | grep -q 'plan.md labeled done_sentence missing' \
  || fail "fenced-only plan.md message: $out_fence_only"

rungoal="$tmpdir/goal-mismatch/.shiploop"
repogoal="$tmpdir/goal-mismatch/repo"
mkdir -p "$repogoal"
advance_to_plan "$rungoal" "$repogoal" "$planf"
install_dag "$rungoal" linear.json
python3 - "$rungoal/backchain/plan.json" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
d = json.loads(p.read_text())
d["goal"] = "not the spec sentence"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
set +e
out_goal="$(run_cli update --run-dir "$rungoal" --to implement 2>&1)"
rc_goal=$?
set -e
[[ "$rc_goal" -eq 2 ]] || fail "DAG goal mismatch want 2: $out_goal"
printf '%s\n' "$out_goal" | grep -q 'backchain.goal must equal spec.done_sentence' \
  || fail "DAG goal mismatch message: $out_goal"
assert_absent "$out_goal" 'plan.md labeled done_sentence must equal spec.md' \
  "DAG goal mismatch blamed plan.md"
printf 'LAYER: leftover plan.json inert + plan.md vs spec OK\n'

# --- linear DAG implement + /goal + frozen ---
install_dag "$run" linear.json
if grep -Fq 'Improve (paste as /goal B' "$run/backchain/plan.json"; then
  fail "linear.json stored prompts must not carry Improve envelope"
fi
if grep -Fq 'last 7 git commit' "$run/backchain/plan.json"; then
  fail "linear.json stored prompts must not carry Improve last-7 schema"
fi
[[ ! -f "$run/plan.json" ]] || fail "happy-path dest implement wrote plan.json"
run_cli update --run-dir "$run" --to implement >/dev/null
out_imp="$(run_cli next --run-dir "$run")"
assert_headings "$out_imp"
printf '%s\n' "$out_imp" | grep -q 'implement: current' || fail "implement current"
printf '%s\n' "$out_imp" | grep -q 'frozen' || fail "spec not frozen"
printf '%s\n' "$out_imp" | grep -q '/goal ' || fail "missing /goal"
printf '%s\n' "$out_imp" | grep -q 'from initial_state' || fail "goal missing initial_state"
assert_absent "$out_imp" 'from None' "/goal leaked Python None"
assert_absent "$out_imp" 'refine the spec' "implement said refine"
assert_absent "$out_imp" 'steps: write file' "dumped plan body"
printf '%s\n' "$out_imp" | grep -q 'S1: running' || fail "S1 not running"
printf '%s\n' "$out_imp" | grep -q 'S2: todo' || fail "S2 should wait"
printf '%s\n' "$out_imp" | grep -q 'Session  ● intake' || fail "session rail missing intake done"
printf '%s\n' "$out_imp" | grep -q '▶ implement' || fail "session rail missing implement current"
printf '%s\n' "$out_imp" | grep -q '○ residual' || fail "session rail missing residual left"
printf '%s\n' "$out_imp" | grep -q '▶ S1  write the file' || fail "walk rail missing S1 statement"
printf '%s\n' "$out_imp" | grep -q '○ S2  confirm the file' || fail "walk rail missing S2 statement"
printf '%s\n' "$out_imp" | grep -q 'waiting on S1 write the file' || fail "walk rail missing waiting-on"
if printf '%s\n' "$out_imp" | grep -E '^  \[[xX ]\] S[0-9]' >/dev/null; then
  fail "walk rail still uses checkbox marks on a step id"
fi
printf '%s\n' "$out_imp" | grep -q 'Finish S1: write the file' || fail "labeled Finish S1 missing"
printf '%s\n' "$out_imp" | grep -q 'S1 worktree — cwd here — write the file' || fail "look here missing S1 statement"
printf '%s\n' "$out_imp" | grep -qx 'Diagnosis' || fail "implement missing Diagnosis"
printf '%s\n' "$out_imp" | grep -q 'stand      implement — 0/2 steps done' || fail "implement stand"
printf '%s\n' "$out_imp" | grep -q 'serving frozen spec' || fail "implement stand missing spec insight"
printf '%s\n' "$out_imp" | grep -A20 '^Diagnosis$' | grep -q 'S1  write the file' || fail "now missing S1"
printf '%s\n' "$out_imp" | grep -A20 '^Diagnosis$' | grep -q '(running)' || fail "now missing running"
printf '%s\n' "$out_imp" | grep -A20 '^Diagnosis$' | grep -q 'S2  confirm the file' || fail "pending missing S2"
printf '%s\n' "$out_imp" | grep -q 'invoke /shiploop complete' || fail "when done missing /shiploop complete"
printf '%s\n' "$out_imp" | awk '/^## When done invoke$/,/^## Missing$/' \
  | grep -Fq -- '--inner-loop goal|parent' \
  || fail "implement when done missing --inner-loop: $out_imp"
assert_absent "$out_imp" 'complete-step --' "when done leaked complete-step argv"
assert_absent "$out_imp" '--id S1' "when done leaked --id S1"
printf '%s\n' "$out_imp" | grep -q 'commit on the worktree' || fail "when done missing commit"
printf '%s\n' "$out_imp" | awk '/^## When done invoke$/,/^## Missing$/' | grep -q 'Key learnings:' \
  || fail "when done missing Implement git schema"
printf '%s\n' "$out_imp" | grep -q 'merge --no-ff' || fail "when done missing host merge"
printf '%s\n' "$out_imp" | grep -qx '## Progress' || fail "implement missing Progress"
printf '%s\n' "$out_imp" | grep -Eq '^(Beginning|Continuing) step S1 of 2' \
  || fail "implement Progress missing S1 begin/continue"
printf '%s\n' "$out_imp" | grep -q 'Work in this worktree folder' || fail "implement Progress missing worktree"
printf '%s\n' "$out_imp" | grep -q 'Finish S1:' || fail "implement Progress missing finish S1"
printf '%s\n' "$out_imp" | awk '/^## Progress$/,/^## Reminder$/' | grep -q 'Finish S1:' \
  || fail "implement Progress missing Finish S1:"
printf '%s\n' "$out_imp" | awk '/^## Progress$/,/^## Reminder$/' | grep -q 'leftover uncommitted' \
  || fail "implement Progress missing leftover-only"
printf '%s\n' "$out_imp" | awk '/^## Progress$/,/^## Reminder$/' | grep -q 'Key learnings:' \
  || fail "implement Progress missing Key learnings:"
if printf '%s\n' "$out_imp" | awk '/^## Progress$/,/^## Reminder$/' \
  | grep -Fq 'when the /goal is done, commit on that worktree'; then
  fail "implement Progress still always-commit"
fi
printf '%s\n' "$out_imp" | grep -q 'Do not edit the session checkout' || fail "implement next missing checkout guard"
assert_host_flag "$out_imp" "implement packet"
flag_n="$(printf '%s\n' "$out_imp" | grep -cF 'HOST FLAG — extra folder (do not re-root):' || true)"
[[ "$flag_n" -ge 2 ]] || fail "implement packet should print HOST FLAG in Progress and Next envelope (got $flag_n)"
printf '%s\n' "$out_imp" | grep -Eq 'required  .+/environment.md' \
  || fail "implement Look here missing required environment.md"
printf '%s\n' "$out_imp" | grep -q 'mcp-considered: none(no read-capable session tool matched done-sentence)' \
  || fail "implement Next missing frozen mcp-considered: $out_imp"
printf '%s\n' "$out_imp" | grep -q 'tools: (none)' || fail "implement Next missing tools: (none)"
printf '%s\n' "$out_imp" | grep -q 'mcp: (none)' || fail "implement Next missing mcp: (none)"
printf '%s\n' "$out_imp" | grep -q 'Exclusive: (none)' || fail "implement Next missing Exclusive: (none)"
printf '%s\n' "$out_imp" | grep -q 'Implement git (paste into /goal with Frozen' \
  || fail "implement Next missing Implement git"
printf '%s\n' "$out_imp" | grep -q 'Goal until (this stored prompt is /goal A' \
  || fail "implement Next missing Goal until"
printf '%s\n' "$out_imp" | grep -q 'Until (exit; do not loop):' \
  || fail "implement Next missing Until (exit; do not loop)"
printf '%s\n' "$out_imp" | grep -Fiq 'do not nest' \
  || fail "implement Next missing do not nest"
printf '%s\n' "$out_imp" | grep -q 'Improve (paste as /goal B after produces is true' \
  || fail "implement Next missing Improve"
printf '%s\n' "$out_imp" | grep -q 'last 7 git commit' \
  || fail "implement Next missing last 7 git commit"
printf '%s\n' "$out_imp" | grep -q '2 consecutive' \
  || fail "implement Next missing 2 consecutive"
printf '%s\n' "$out_imp" | grep -q 'Max 12 improve cycles' \
  || fail "implement Next missing Max 12"
if printf '%s\n' "$out_imp" | grep -qx '## Goal until'; then
  fail "Goal until became an H2"
fi
if printf '%s\n' "$out_imp" | grep -qx '## Improve'; then
  fail "Improve became an H2"
fi
printf '%s\n' "$out_imp" | grep -q 'Key learnings:' \
  || fail "implement Next missing Key learnings:"
printf '%s\n' "$out_imp" | grep -q 'log -10 --format=full' \
  || fail "implement Next missing log -10"
printf '%s\n' "$out_imp" | grep -q 'See: <full sha>' \
  || fail "implement Next missing See: sha template"
printf '%s\n' "$out_imp" | grep -q 'Worktree: ' \
  || fail "implement Next Implement git missing Worktree:"
printf '%s\n' "$out_imp" | grep -q 'Session checkout (repo_root main tree' \
  || fail "implement Next missing session checkout definition"
printf '%s\n' "$out_imp" | python3 -c "
import sys
text = sys.stdin.read()
i = text.find('Frozen session environment')
j = text.find('Implement git (paste into /goal with Frozen')
u = text.find('Goal until (this stored prompt is /goal A')
k = text.find('/goal\n')
if k < 0:
    k = text.find('/goal')
imp = text.find('Improve (paste as /goal B after produces is true')
assert i != -1 and j != -1 and u != -1 and k != -1 and imp != -1, (i, j, u, k, imp)
assert i < j < u < k < imp, (i, j, u, k, imp)
assert 'result.txt exists' in text[u:k]
frozen = text[i:j]
assert 'Deeply research those MCP servers' not in frozen, 'job-2 research leaked into Frozen'
assert 'Improve (paste as /goal B after produces is true' not in frozen
assert 'HOST FLAG' not in frozen
" || fail "envelope order Frozen, Implement git, Goal until, stored /goal, Improve"
assert_absent "$out_imp" 'do not implement the product through MCP' \
  "Frozen still forbids implementing through MCP"
python3 -c '
import sys
p = sys.argv[1]
host = p.find("HOST FLAG — extra folder")
# last HOST FLAG is the Next envelope (Progress prints one first)
host = p.rfind("HOST FLAG — extra folder")
mcp = p.find("mcp-considered:", host)
prompt = p.find("/goal", host)
assert host != -1 and mcp != -1 and prompt != -1 and host < mcp < prompt, (host, mcp, prompt)
' "$out_imp" || fail "envelope order: HOST FLAG then mcp-considered then stored prompt"
printf '%s\n' "$out_imp" | grep -q 'checkable=true' || fail "implement reminder checkable"
assert_absent "$out_imp" '--to residual' "mid-graph residual present"
set +e
out_midres="$(run_cli update --run-dir "$run" --to residual 2>&1)"
rc_midres=$?
set -e
[[ "$rc_midres" -eq 2 ]] || fail "mid-graph --to residual want 2: $out_midres"
printf 'LAYER: linear implement packet OK\n'

# --- S2 waits for S1 ---
set +e
out_s2="$(run_cli complete-step --run-dir "$run" --id S2 2>&1)"
rc_s2=$?
set -e
[[ "$rc_s2" -eq 2 ]] || fail "S2 complete before S1 want 2: $out_s2"
complete_ok "$run" S1
out_mid="$(run_cli next --run-dir "$run")"
printf '%s\n' "$out_mid" | grep -q 'S1: done' || fail "S1 not done"
printf '%s\n' "$out_mid" | grep -q '● S1  write the file' || fail "walk rail missing ● S1"
printf '%s\n' "$out_mid" | grep -q '▶ S2  confirm the file' || fail "walk rail missing ▶ S2"
printf '%s\n' "$out_mid" | grep -q 'S2: running' || fail "S2 not claimed"
printf '%s\n' "$out_mid" | grep -q 'stand      implement — 1/2 steps done' || fail "mid stand"
printf '%s\n' "$out_mid" | awk '/^  completed$/,/^  now$/' | grep -q 'S1  write the file' \
  || fail "completed missing S1"
printf '%s\n' "$out_mid" | awk '/^  now$/,/^  pending$/' | grep -q 'S2  confirm the file' \
  || fail "now missing S2"
printf '%s\n' "$out_mid" | grep -q '/goal ' || fail "S2 missing /goal"
run_cli complete-step --run-dir "$run" --id S1 >/dev/null 2>&1 && fail "duplicate complete should fail" || true
set +e
out_dup="$(run_cli complete-step --run-dir "$run" --id S1 2>&1)"
rc_dup=$?
set -e
[[ "$rc_dup" -eq 2 ]] || fail "duplicate complete want 2"
complete_ok "$run" S2
out_dr="$(run_cli next --run-dir "$run")"
printf '%s\n' "$out_dr" | grep -q 'invoke /shiploop complete' || fail "drained missing closer"
printf '%s\n' "$out_dr" | grep -q 'drained — next residual' || fail "drained stand"
printf '%s\n' "$out_dr" | grep -q 'After it finishes: dest residual — run bound review-coverage Phase B' \
  || fail "drained dest residual default stand: $out_dr"
printf '%s\n' "$out_dr" | grep -q 'waived closer' \
  || fail "drained Next prompt missing waiver hatch: $out_dr"
assert_absent "$out_dr" '/goal ' "drained implement still emitted /goal"
assert_absent "$out_dr" 'Implement git (paste into /goal with Frozen' \
  "drained implement still emitted Implement git"
assert_absent "$out_dr" 'Goal until (this stored prompt is /goal A' \
  "drained implement still emitted Goal until"
assert_absent "$out_dr" 'Improve (paste as /goal B after produces is true' \
  "drained implement still emitted Improve"
assert_absent "$out_dr" 'shiploop update --run-dir' "drained leaked update argv"
run_cli update --run-dir "$run" --to residual >/dev/null
printf 'LAYER: linear drain OK\n'

# --- dest residual binds empty bound_plan or fails closed ---
runub="$tmpdir/unbound-res/.shiploop"
repoub="$tmpdir/unbound-res/repo"
init_git_repo "$repoub"
run_cli init --prompt "create result.txt containing exactly one line: ok" \
  --run-dir "$runub" --repo "$repoub" >/dev/null
run_cli update --run-dir "$runub" --to validate-spec >/dev/null
write_environment "$runub"
write_spec "$runub"
run_cli update --run-dir "$runub" --to plan >/dev/null
install_dag "$runub" linear.json
run_cli update --run-dir "$runub" --to implement >/dev/null
run_cli next --run-dir "$runub" >/dev/null
complete_ok "$runub" S1
run_cli next --run-dir "$runub" >/dev/null
complete_ok "$runub" S2
out_dr_ub="$(run_cli next --run-dir "$runub")"
printf '%s\n' "$out_dr_ub" | grep -q 'bound_plan empty' \
  || fail "drained unbound Missing missing bound_plan empty: $out_dr_ub"
set +e
out_ub="$(run_cli update --run-dir "$runub" --to residual 2>&1)"
rc_ub=$?
set -e
[[ "$rc_ub" -eq 2 ]] || fail "unbound dest residual want 2: $out_ub"
printf '%s\n' "$out_ub" | grep -qi 'bound_plan empty' || fail "unbound residual message: $out_ub"
printf '\n## Review Coverage\nauto-bind this session plan\n' >>"$runub/plan.md"
out_dr_h2="$(run_cli next --run-dir "$runub")"
assert_absent "$out_dr_h2" 'bound_plan empty' \
  "drained H2 still listed bound_plan empty"
out_bd="$(run_cli update --run-dir "$runub" --to residual)"
printf '%s\n' "$out_bd" | grep -q 'residual: current' || fail "auto-bind dest residual: $out_bd"
python3 - "$runub" <<'PY'
import json, sys
from pathlib import Path
run = Path(sys.argv[1])
d = json.loads((run / "state.json").read_text())
assert d["phase"] == "residual", d["phase"]
assert d.get("bound_plan"), d
assert Path(d["bound_plan"]).resolve() == (run / "plan.md").resolve()
assert d.get("bound_plan_hash")
PY
printf 'LAYER: dest residual bound_plan bind OK\n'

# last-step complete with no Review Coverage: receipt complete, dest residual rc 2
runlast="$tmpdir/last-unbound/.shiploop"
repolast="$tmpdir/last-unbound/repo"
init_git_repo "$repolast"
run_cli init --prompt "create result.txt containing exactly one line: ok" \
  --run-dir "$runlast" --repo "$repolast" >/dev/null
run_cli update --run-dir "$runlast" --to validate-spec >/dev/null
write_environment "$runlast"
write_spec "$runlast"
run_cli update --run-dir "$runlast" --to plan >/dev/null
install_dag "$runlast" linear.json
run_cli update --run-dir "$runlast" --to implement >/dev/null
run_cli next --run-dir "$runlast" >/dev/null
complete_ok "$runlast" S1
run_cli next --run-dir "$runlast" >/dev/null
commit_step_work "$runlast" S2
set +e
out_last="$(run_cli complete --run-dir "$runlast" --id S2 --inner-loop parent 2>&1)"
rc_last=$?
set -e
[[ "$rc_last" -eq 2 ]] || fail "last-step unbound complete want 2: $out_last"
printf '%s\n' "$out_last" | grep -Fq \
  'bound_plan empty: add ## Review Coverage to .shiploop/plan.md or pass --bound-plan' \
  || fail "last-step unbound gap: $out_last"
python3 - "$runlast" <<'PY'
import json, sys
from pathlib import Path
run = Path(sys.argv[1])
d = json.loads((run / "state.json").read_text())
assert d["phase"] == "implement", d["phase"]
rec = json.loads((run / "steps" / "S2.json").read_text())
assert rec["status"] == "complete", rec
PY
printf '\n## Review Coverage\nauto-bind\n' >>"$runlast/plan.md"
out_fix="$(run_cli complete --run-dir "$runlast")"
printf '%s\n' "$out_fix" | grep -q 'residual: current' || fail "recovery complete dest residual: $out_fix"

# init --bound-plan missing path still dests residual
runbpm="$tmpdir/bound-missing/.shiploop"
repobpm="$tmpdir/bound-missing/repo"
init_git_repo "$repobpm"
run_cli init --prompt "create result.txt containing exactly one line: ok" \
  --run-dir "$runbpm" --bound-plan "$tmpdir/no-such-shiploop-plan.md" --repo "$repobpm" >/dev/null
run_cli update --run-dir "$runbpm" --to validate-spec >/dev/null
write_environment "$runbpm"
write_spec "$runbpm"
run_cli update --run-dir "$runbpm" --to plan >/dev/null
install_dag "$runbpm" linear.json
run_cli update --run-dir "$runbpm" --to implement >/dev/null
run_cli next --run-dir "$runbpm" >/dev/null
complete_ok "$runbpm" S1
run_cli next --run-dir "$runbpm" >/dev/null
complete_ok "$runbpm" S2
out_bpm="$(run_cli complete --run-dir "$runbpm")"
printf '%s\n' "$out_bpm" | grep -q 'residual: current' \
  || fail "missing --bound-plan still dest residual: $out_bpm"
printf 'LAYER: last-step residual gate + bound-plan precedence OK\n'

# --- capture is not a verb (argparse usage) ---
[[ ! -f "$run/implement.json" ]] || fail "shiploop must not write implement.json"
set +e
out_cap="$(run_cli capture --run-dir "$run" -- echo hi 2>&1)"
rc_cap=$?
set -e
[[ "$rc_cap" -eq 2 ]] || fail "capture want 2: $out_cap"
printf '%s\n' "$out_cap" | grep -qi 'invalid choice' || fail "capture message: $out_cap"
printf 'LAYER: capture usage OK\n'

# --- residual ledger tests ---
cat >"$repo/REVIEW_CONVERGE.md" <<'MD'
**Status:** complete
**Plan contract:** `/other/plan.md`
**Plan hash:** `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`

### Round 1 —
**Committed:** yes
review-converge: round 1 —
MD
set +e
out_for="$(run_cli update --run-dir "$run" --to done 2>&1)"
rc_for=$?
set -e
[[ "$rc_for" -eq 2 ]] || fail "foreign complete want 2: $out_for"
printf '%s\n' "$out_for" | grep -qi 'foreign\|unbound' || fail "foreign message: $out_for"
printf 'LAYER: foreign ledger refuse OK\n'

bhash="$(python3 -c "import hashlib,pathlib; print(hashlib.sha256(pathlib.Path('$planf').read_bytes()).hexdigest())")"
cat >"$repo/REVIEW_CONVERGE.md" <<MD
**Status:** complete
**Plan contract:** \`$planf\`
**Plan hash:** \`$bhash\`

### Round 1 —
**Committed:** no
review-converge: round 1 —
MD
set +e
out_ul="$(run_cli update --run-dir "$run" --to done 2>&1)"
rc_ul=$?
set -e
[[ "$rc_ul" -eq 2 ]] || fail "unlanded want 2: $out_ul"
printf 'LAYER: unlanded complete refuse OK\n'

# --- false landed: round 2 committed yes, subject only in round 1 ---
cat >"$repo/REVIEW_CONVERGE.md" <<MD
**Status:** complete
**Plan contract:** \`$planf\`
**Plan hash:** \`$bhash\`

### Round 1 —
review-converge: round 1 —
**Committed:** yes

### Round 2 —
**Committed:** yes
MD
set +e
out_fl="$(run_cli update --run-dir "$run" --to done 2>&1)"
rc_fl=$?
set -e
[[ "$rc_fl" -eq 2 ]] || fail "false landed want 2: $out_fl"
printf 'LAYER: latest-round landed OK\n'

# --- latest round may land from the matching git subject alone ---
git -C "$repo" commit --allow-empty -m 'review-converge: round 2 —' >/dev/null
cat >"$repo/REVIEW_CONVERGE.md" <<MD
**Status:** complete
**Plan contract:** \`$planf\`
**Plan hash:** \`$bhash\`

### Round 2 —
**Committed:** yes
MD
rm -f "$run/recap.html"
out_git_landed="$(run_cli update --run-dir "$run" --to done)"
printf '%s\n' "$out_git_landed" | grep -q 'updated residual -> done' \
  || fail "git subject should land latest round: $out_git_landed"
python3 - "$run" <<'PY' || fail "git subject latest round did not dest done"
import json, sys
from pathlib import Path
assert json.loads((Path(sys.argv[1]) / "state.json").read_text())["phase"] == "done"
PY
python3 - "$run" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1]) / "state.json"
data = json.loads(p.read_text())
data["phase"] = "residual"
data["terminal"] = None
p.write_text(json.dumps(data, indent=2) + "\n")
PY
printf 'LAYER: git-log latest-round landed OK\n'

cat >"$repo/REVIEW_CONVERGE.md" <<MD
**Status:** complete
**Plan contract:** \`$planf\`
**Plan hash:** \`$bhash\`

### Round 2 —
review-converge: round 2 —
**Committed:** yes
MD
rm -f "$run/recap.html"
out_res_miss="$(run_cli next --run-dir "$run")"
assert_absent "$out_res_miss" 'missing recap.html' \
  "residual packet demanded recap.html the harness writes"
printf 'not html\n' >"$run/recap.html"
out_nr="$(run_cli update --run-dir "$run" --to done 2>&1)"
printf '%s\n' "$out_nr" | grep -q 'updated residual -> done' || fail "dest done should write recap: $out_nr"
[[ -f "$run/recap.html" ]] || fail "dest done did not write recap.html"
grep -q '<html' "$run/recap.html" || fail "generated recap is not HTML"
grep -qi 'Original spec' "$run/recap.html" || fail "generated recap missing Original spec"
grep -qi 'End result' "$run/recap.html" || fail "generated recap missing End result"
grep -qi 'Intent' "$run/recap.html" || fail "generated recap missing Intent"
grep -q 'result.txt contains exactly one line: ok' "$run/recap.html" \
  || fail "generated recap missing frozen done_sentence"
grep -q 'write the file' "$run/recap.html" || fail "generated recap missing S1 statement"
grep -q 'confirm the file' "$run/recap.html" || fail "generated recap missing S2 statement"
grep -q 'writer: shiploop.recap' "$run/recap.html" || fail "generated recap missing writer stamp"
grep -qi 'Key accomplishments' "$run/recap.html" || fail "generated recap missing Key accomplishments"
grep -qi 'Implementation outcomes' "$run/recap.html" || fail "generated recap missing outcomes diagram"
grep -q 'class="river"' "$run/recap.html" || fail "generated recap missing river diagram"
grep -q 'Made true:' "$run/recap.html" || fail "generated recap missing made-true accomplishments"
grep -q 'update:residual-&gt;done' "$run/recap.html" \
  || fail "generated recap history missing dest done event"
grep -q 'review-coverage complete and landed' "$run/recap.html" \
  || fail "generated recap missing review-coverage complete line"
grep -q 'host-owned' "$run/recap.html" \
  || fail "generated recap missing host-owned quality line"
grep -q 'not a harness-verified claim' "$run/recap.html" \
  || fail "generated recap still treats done_sentence as harness-verified"
grep -q 'Contracted end result — not harness-verified' "$run/recap.html" \
  || fail "generated recap reveal still presents done_sentence as achieved"
printf 'LAYER: dest done writes recap.html OK\n'
out_done="$(run_cli next --run-dir "$run")"
printf '%s\n' "$out_done" | grep -q 'stop — no update' || fail "done stop: $out_done"
printf '%s\n' "$out_done" | grep -q 'quality/publish were host-owned' \
  || fail "done Diagnosis missing host-owned quality: $out_done"
printf '%s\n' "$out_done" | grep -q 'recap.html' || fail "done Look here missing recap.html: $out_done"
python3 - "$run" <<'PY'
import json, sys
from pathlib import Path
d = json.loads((Path(sys.argv[1]) / "state.json").read_text())
assert d["phase"] == "done", d["phase"]
assert d["terminal"] == "success", d.get("terminal")
PY
printf 'LAYER: bound complete+landed OK\n'

# --- stopped -> halted ---
python3 - "$run" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1]) / "state.json"
d = json.loads(p.read_text())
d["phase"] = "residual"
d["terminal"] = None
p.write_text(json.dumps(d, indent=2) + "\n")
PY
cat >"$repo/REVIEW_CONVERGE.md" <<MD
**Status:** stopped (max-cycles)
**Plan contract:** \`$planf\`
**Plan hash:** \`$bhash\`

### Round 3 —
review-converge: round 3 —
**Committed:** yes
MD
run_cli update --run-dir "$run" --to halted >/dev/null
python3 - "$run" <<'PY'
import json, sys
from pathlib import Path
d = json.loads((Path(sys.argv[1]) / "state.json").read_text())
assert d["phase"] == "halted", d["phase"]
assert d["terminal"] == "halted"
PY
grep -q 'HALTED' "$run/recap.html" || fail "halted recap missing HALTED stamp"
grep -qi 'End result' "$run/recap.html" || fail "halted recap missing End result"
grep -q 'update:residual-&gt;halted' "$run/recap.html" \
  || fail "halted recap history missing dest halted event"
grep -q 'host-owned' "$run/recap.html" \
  || fail "halted recap missing host-owned quality line"
out_halted="$(run_cli next --run-dir "$run")"
assert_absent "$out_halted" '{{RECAP_HTML}}' "halted packet leaked {{RECAP_HTML}}"
assert_absent "$out_halted" '{{LEDGER_PATH}}' "halted packet leaked {{LEDGER_PATH}}"
printf '%s\n' "$out_halted" | grep -q 'recap.html' \
  || fail "halted Look here missing recap.html: $out_halted"
printf '%s\n' "$out_halted" | grep -q 'spec.md' \
  || fail "halted Look here missing spec.md: $out_halted"
printf '%s\n' "$out_halted" | grep -q 'REVIEW_CONVERGE.md' \
  || fail "halted Look here missing REVIEW_CONVERGE: $out_halted"
printf '%s\n' "$out_halted" | grep -q 'stop — no update' \
  || fail "halted stop: $out_halted"
printf 'LAYER: stopped -> halted OK\n'

# --- plan H2 waiver accept ---
python3 - "$run" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1]) / "state.json"
d = json.loads(p.read_text())
d["phase"] = "residual"
d["terminal"] = None
p.write_text(json.dumps(d, indent=2) + "\n")
PY
cat >"$planf" <<'MD'
# Bound

## Review Coverage
None — residual loop waived: demo fixture only
MD
newhash="$(python3 -c "import hashlib,pathlib; print(hashlib.sha256(pathlib.Path('$planf').read_bytes()).hexdigest())")"
python3 - "$run" "$newhash" "$planf" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1]) / "state.json"
d = json.loads(p.read_text())
d["bound_plan_hash"] = sys.argv[2]
d["bound_plan"] = sys.argv[3]
p.write_text(json.dumps(d, indent=2) + "\n")
PY
out_waive="$(run_cli next --run-dir "$run")"
printf '%s\n' "$out_waive" | grep -q 'residual waived — quality/publish then dest done' \
  || fail "waived residual Diagnosis missing waived stand: $out_waive"
assert_absent "$out_waive" 'run bound review-coverage Phase B' \
  "waived residual still said run Phase B"
printf '%s\n' "$out_waive" | grep -q 'Review-coverage is waived on the bound plan' \
  || fail "waived residual Progress missing waived begin: $out_waive"
printf '%s\n' "$out_waive" | awk '/^## Next prompt$/,/^## When done invoke$/' \
  | grep -q 'run review-coverage Phase B' \
  && fail "waived residual Next prompt still ran Phase B: $out_waive"
printf '%s\n' "$out_waive" | grep -q 'residual-waived.md' \
  || fail "waived residual Look here missing residual-waived.md: $out_waive"
cat >"$repo/REVIEW_CONVERGE.md" <<'MD'
**Status:** active
**Plan contract:** `/nope`
MD
write_recap "$run"
out_waive_done="$(run_cli update --run-dir "$run" --to done)"
python3 - "$run" <<'PY'
import json, sys
from pathlib import Path
d = json.loads((Path(sys.argv[1]) / "state.json").read_text())
assert d["terminal"] == "waived", d
PY
grep -q 'review-coverage waived: demo fixture only' "$run/recap.html" \
  || fail "waived recap missing review-coverage waived line"
grep -q 'host-owned' "$run/recap.html" \
  || fail "waived recap missing host-owned quality line"
grep -q 'WAIVED' "$run/recap.html" \
  && fail "waived recap still stamps WAIVED as if the session was abandoned"
printf '%s\n' "$out_waive_done" | grep -q 'residual waived; quality/publish were host-owned' \
  || fail "waived dest done Diagnosis missing host-owned stand: $out_waive_done"
printf 'LAYER: plan H2 waiver accept OK\n'

# --- ledger-local waiver refuse ---
python3 - "$run" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1]) / "state.json"
d = json.loads(p.read_text())
d["phase"] = "residual"
d["terminal"] = None
d["bound_plan_hash"] = ""
p.write_text(json.dumps(d, indent=2) + "\n")
PY
cat >"$planf" <<'MD'
# Bound

## Review Coverage
Target paths: x
MD
cat >"$repo/REVIEW_CONVERGE.md" <<MD
**Status:** complete
**Plan contract:** \`$planf\`
None — residual loop waived: not a plan H2

### Round 1 —
**Committed:** no
MD
set +e
out_lw="$(run_cli update --run-dir "$run" --to done 2>&1)"
rc_lw=$?
set -e
[[ "$rc_lw" -eq 2 ]] || fail "ledger waiver want 2: $out_lw"
printf 'LAYER: ledger-local waiver refuse OK\n'

# --- two-root organic claim / in-flight / start-step twice ---
run2="$tmpdir/two/.shiploop"
repo2="$tmpdir/two/repo"
mkdir -p "$repo2"
advance_to_plan "$run2" "$repo2" "$planf"
install_dag "$run2" two-root.json
run_cli update --run-dir "$run2" --to implement >/dev/null
out_tr="$(run_cli next --run-dir "$run2")"
printf '%s\n' "$out_tr" | grep -q 'S1: running' || fail "two-root S1"
printf '%s\n' "$out_tr" | grep -q 'S2: running' || fail "two-root S2"
printf '%s\n' "$out_tr" | grep -c '^/goal' | grep -qx 4 || fail "want two stored /goal plus two Improve /goal"
printf '%s\n' "$out_tr" | grep -c 'mcp-considered:' | grep -qx 2 \
  || fail "two-root want two mcp-considered envelopes"
printf '%s\n' "$out_tr" | grep -cF 'Implement git (paste into /goal with Frozen' | grep -qx 2 \
  || fail "two-root want two Implement git blocks"
printf '%s\n' "$out_tr" | python3 -c '
import sys
head = "Implement git (paste into /goal with Frozen"
parts = sys.stdin.read().split(head)
assert len(parts) == 3, len(parts)
wts, brs = [], []
for block in parts[1:]:
    lines = block.splitlines()
    wts.append(next(ln for ln in lines if ln.startswith("Worktree: ")))
    brs.append(next(ln for ln in lines if ln.startswith("Branch: ")))
assert wts[0] != wts[1], wts
assert brs[0] != brs[1], brs
' || fail "two-root Implement git Worktree/Branch not distinct"
set +e
out_ss="$(run_cli start-step --run-dir "$run2" --id S1 2>&1)"
rc_ss=$?
set -e
[[ "$rc_ss" -eq 2 ]] || fail "double start want 2: $out_ss"
commit_step_work "$run2" S1
merge_step_branch "$run2" S1
out_tr_c="$(run_cli complete --run-dir "$run2" --id S1 --inner-loop parent)"
printf '%s\n' "$out_tr_c" | grep -q 'In flight' \
  || fail "complete --id S1 did not keep S2 in-flight: $out_tr_c"
printf '%s\n' "$out_tr_c" | grep -q 'Continuing' \
  || fail "complete --id S1 Progress did not Continuing S2: $out_tr_c"
printf '%s\n' "$out_tr_c" | grep -q 'S1: done' || fail "complete --id S1 S1 not done"
printf '%s\n' "$out_tr_c" | grep -cF 'Implement git (paste into /goal with Frozen' | grep -qx 1 \
  || fail "after S1 complete want one Implement git for S2"
printf '%s\n' "$out_tr_c" | grep -cF 'Improve (paste as /goal B after produces is true' | grep -qx 1 \
  || fail "after S1 complete want one Improve for S2"
out_tr2="$(run_cli next --run-dir "$run2")"
printf '%s\n' "$out_tr2" | grep -q 'In flight' || fail "S2 not labeled in-flight"
printf '%s\n' "$out_tr2" | grep -q 'S1: done' || fail "S1 should stay done"
printf '%s\n' "$out_tr2" | grep -c '^/goal' | grep -qx 2 || fail "reprint should keep stored /goal plus Improve"
set +e
out_ns="$(run_cli complete-step --run-dir "$run2" --id S9 2>&1)"
rc_ns=$?
set -e
[[ "$rc_ns" -eq 2 ]] || fail "unknown id want 2"
# never-started: clear S2 then complete without next
run_cli clear-step --run-dir "$run2" --id S2 >/dev/null
set +e
out_nv="$(run_cli complete-step --run-dir "$run2" --id S2 2>&1)"
rc_nv=$?
set -e
[[ "$rc_nv" -eq 2 ]] || fail "never-started want 2: $out_nv"
out_retry="$(run_cli next --run-dir "$run2")"
printf '%s\n' "$out_retry" | grep -q 'S2: running' || fail "clear+next should re-claim S2"
printf 'LAYER: two-root claim/in-flight OK\n'

# --- concurrent two-root complete-step ---
run3="$tmpdir/conc/.shiploop"
repo3="$tmpdir/conc/repo"
mkdir -p "$repo3"
advance_to_plan "$run3" "$repo3" "$planf"
install_dag "$run3" two-root.json
run_cli update --run-dir "$run3" --to implement >/dev/null
run_cli next --run-dir "$run3" >/dev/null
commit_step_work "$run3" S1
commit_step_work "$run3" S2
merge_step_branch "$run3" S1
merge_step_branch "$run3" S2
python3 "$cli" complete-step --run-dir "$run3" --id S1 >"$tmpdir/shiploop-c1.out" 2>&1 &
p1=$!
python3 "$cli" complete-step --run-dir "$run3" --id S2 >"$tmpdir/shiploop-c2.out" 2>&1 &
p2=$!
wait "$p1" || fail "concurrent S1"
wait "$p2" || fail "concurrent S2"
[[ ! -f "$run3/implement.json" ]] || fail "concurrent complete-step wrote implement.json"
python3 - "$run3" <<'PY'
import json, sys
from pathlib import Path
run = Path(sys.argv[1])
for sid in ("S1", "S2"):
    rec = json.loads((run / "steps" / f"{sid}.json").read_text())
    assert rec["status"] == "complete", rec
PY
printf 'LAYER: concurrent complete-step OK\n'

# --- residual-risk / empty / cycle / unsafe / goal mismatch / inv-7 ---
reject_dag() {
  local name="$1"
  local r="$tmpdir/rej-$name/.shiploop"
  local rp="$tmpdir/rej-$name/repo"
  mkdir -p "$rp"
  advance_to_plan "$r" "$rp" "$planf"
  install_dag "$r" "$name.json"
  set +e
  local out rc
  out="$(run_cli update --run-dir "$r" --to implement 2>&1)"
  rc=$?
  set -e
  [[ "$rc" -eq 2 ]] || fail "$name want 2: $out"
}
reject_dag unresolved-residual
reject_dag empty-steps
reject_dag cycle
reject_dag unsafe-id
reject_dag goal-mismatch
reject_dag missing-initial
reject_dag goal-not-string
printf 'LAYER: DAG rejects OK\n'

# --- hash drift ---
runh="$tmpdir/hash/.shiploop"
repoh="$tmpdir/hash/repo"
mkdir -p "$repoh"
advance_to_plan "$runh" "$repoh" "$planf"
install_dag "$runh" linear.json
run_cli update --run-dir "$runh" --to implement >/dev/null
printf 'done_sentence: %s\nmutated\n' "$DS" >"$runh/spec.md"
set +e
out_hd="$(run_cli next --run-dir "$runh" 2>&1)"
rc_hd=$?
set -e
[[ "$rc_hd" -eq 2 ]] || fail "spec drift want 2: $out_hd"
write_spec "$runh"
# restore matching spec bytes... --to plan set hash of original pair; we rewrote spec.md then restored
# recompute: restored spec.md+json should match if write_spec is identical
out_ok="$(run_cli next --run-dir "$runh")"
printf '%s\n' "$out_ok" | grep -q '/goal ' || fail "restored spec should next"
python3 - "$runh/backchain/plan.json" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
d = json.loads(p.read_text())
d["steps"][0]["statement"] = "mutated statement"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
set +e
out_pd="$(run_cli next --run-dir "$runh" 2>&1)"
rc_pd=$?
set -e
[[ "$rc_pd" -eq 2 ]] || fail "plan drift want 2: $out_pd"
# restore DAG; a leftover, irrelevant spec.json must not affect the spec.md-only hash
python3 - "$runh/backchain/plan.json" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
d = json.loads(p.read_text())
d["steps"][0]["statement"] = "write the file"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
printf '%s\n' '{"leftover":"from a pre-0.7 run","note":"irrelevant now"}' >"$runh/spec.json"
out_leftover="$(run_cli next --run-dir "$runh")"
printf '%s\n' "$out_leftover" | grep -q '/goal ' || fail "leftover spec.json should not cause drift: $out_leftover"
rm -f "$runh/spec.json"
printf 'LAYER: hash drift OK\n'

# --- environment.md drift is fail-closed once frozen ---
runenv="$tmpdir/envdrift/.shiploop"
repoenv="$tmpdir/envdrift/repo"
mkdir -p "$repoenv"
advance_to_plan "$runenv" "$repoenv" "$planf"
install_dag "$runenv" linear.json
run_cli update --run-dir "$runenv" --to implement >/dev/null
printf 'mutated brief.\n\n## machine\n```json\n{"kind": "greenfield"}\n```\n' >"$runenv/environment.md"
set +e
out_envd="$(run_cli next --run-dir "$runenv" 2>&1)"
rc_envd=$?
set -e
[[ "$rc_envd" -eq 2 ]] || fail "environment drift want 2: $out_envd"
printf '%s\n' "$out_envd" | grep -qi 'environment' || fail "environment drift message: $out_envd"
printf 'LAYER: environment hash drift OK\n'

# --- empty environment_sha256 is grandfathered (pre-0.7 run) ---
rungf="$tmpdir/envgf/.shiploop"
repogf="$tmpdir/envgf/repo"
mkdir -p "$repogf"
advance_to_plan "$rungf" "$repogf" "$planf"
install_dag "$rungf" linear.json
run_cli update --run-dir "$rungf" --to implement >/dev/null
python3 - "$rungf" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1]) / "state.json"
d = json.loads(p.read_text())
d["environment_sha256"] = ""
p.write_text(json.dumps(d, indent=2) + "\n")
PY
rm -f "$rungf/environment.md"
out_gf="$(run_cli next --run-dir "$rungf")"
printf '%s\n' "$out_gf" | grep -q '/goal ' || fail "grandfathered empty environment_sha256 should not drift: $out_gf"
printf 'LAYER: environment grandfather OK\n'

# --- A21 leftover spec.json pair-hash + empty environment_sha256 ---
runv2="$tmpdir/pairhash/.shiploop"
repov2="$tmpdir/pairhash/repo"
mkdir -p "$repov2"
advance_to_plan "$runv2" "$repov2" "$planf"
install_dag "$runv2" linear.json
run_cli update --run-dir "$runv2" --to implement >/dev/null
write_spec "$runv2"
printf '%s\n' "{\"done_sentence\":\"$DS\",\"checkable\":true}" >"$runv2/spec.json"
python3 - "$runv2" <<'PY'
import hashlib, json, sys
from pathlib import Path
run = Path(sys.argv[1])
md = (run / "spec.md").read_bytes()
js = (run / "spec.json").read_bytes()
pair = hashlib.sha256(md + b"\0" + js).hexdigest()
md_only = hashlib.sha256(md).hexdigest()
assert pair != md_only, "pair hash must differ from md-only"
state = json.loads((run / "state.json").read_text())
state["spec_sha256"] = pair
state["environment_sha256"] = ""
(run / "state.json").write_text(json.dumps(state, indent=2) + "\n")
PY
out_v2="$(run_cli next --run-dir "$runv2")"
printf '%s\n' "$out_v2" | grep -q '/goal ' || fail "pair-hash grandfather next: $out_v2"
run_cli update --run-dir "$runv2" --to blocked --resume-to validate-spec --reason "rebind pair hash" >/dev/null
run_cli update --run-dir "$runv2" --to validate-spec --reason "rebind pair hash" >/dev/null
write_spec "$runv2"
write_environment "$runv2"
run_cli update --run-dir "$runv2" --to plan >/dev/null
python3 - "$runv2" <<'PY'
import hashlib, json, sys
from pathlib import Path
run = Path(sys.argv[1])
want = hashlib.sha256((run / "spec.md").read_bytes()).hexdigest()
state = json.loads((run / "state.json").read_text())
assert state["spec_sha256"] == want, (state["spec_sha256"], want)
assert state["environment_sha256"] == hashlib.sha256(
    (run / "environment.md").read_bytes()
).hexdigest()
PY
printf 'LAYER: leftover spec.json pair-hash OK\n'

# --- init --force cannot reuse prior DAG ---
runf="$tmpdir/force/.shiploop"
repof="$tmpdir/force/repo"
mkdir -p "$repof"
advance_to_plan "$runf" "$repof" "$planf"
install_dag "$runf" linear.json
run_cli update --run-dir "$runf" --to implement >/dev/null
run_cli next --run-dir "$runf" >/dev/null
ridf="$(python3 -c "import json; print(json.load(open('$runf/state.json'))['run_id'])")"
[[ -d "$repof/.worktrees/shiploop/$ridf/S1" ]] || fail "force fixture missing S1 worktree"
git -C "$repof" rev-parse --verify "shiploop/$ridf/S1" >/dev/null || fail "force fixture missing S1 branch"
write_recap "$runf"
printf 'playbook body\n' >"$runf/playbook.md"
set +e
out_ef="$(run_cli init --force --run-dir "$runf" --bound-plan "$planf" --repo "$repof" 2>&1)"
rc_ef=$?
set -e
[[ "$rc_ef" -eq 2 ]] || fail "empty --force want 2: $out_ef"
[[ -f "$runf/recap.html" ]] || fail "empty --force wiped recap.html"
[[ -d "$repof/.worktrees/shiploop/$ridf/S1" ]] || fail "empty --force wiped worktree"
printf '%s\n' '{"done_sentence":"leftover"}' >"$runf/plan.json"
run_cli init --force --prompt "fresh" --run-dir "$runf" --bound-plan "$planf" --repo "$repof" >/dev/null
[[ ! -f "$runf/backchain/plan.json" ]] || fail "force left backchain"
[[ ! -f "$runf/plan.json" ]] || fail "force left leftover plan.json"
[[ ! -f "$runf/recap.html" ]] || fail "force left recap.html"
[[ ! -f "$runf/playbook.md" ]] || fail "force left playbook.md"
[[ ! -d "$runf/steps" ]] || [[ -z "$(ls -A "$runf/steps" 2>/dev/null || true)" ]] || fail "force left steps"
[[ ! -d "$repof/.worktrees/shiploop/$ridf" ]] || fail "force left run worktrees"
if git -C "$repof" rev-parse --verify "shiploop/$ridf/S1" >/dev/null 2>&1; then
  fail "force left S1 branch"
fi
set +e
out_fi="$(run_cli update --run-dir "$runf" --to implement 2>&1)"
rc_fi=$?
set -e
[[ "$rc_fi" -eq 2 ]] || fail "force then implement want 2: $out_fi"
set +e
out_fcs="$(run_cli complete-step --run-dir "$runf" --id S1 2>&1)"
rc_fcs=$?
set -e
[[ "$rc_fcs" -eq 2 ]] || fail "force then complete-step want 2: $out_fcs"
printf 'LAYER: init --force wipe OK\n'

# --- injection ---
runi="$tmpdir/inj/.shiploop"
repoi="$tmpdir/inj/repo"
mkdir -p "$repoi"
advance_to_plan "$runi" "$repoi" "$planf"
install_dag "$runi" two-root.json
python3 - "$runi/backchain/plan.json" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
d = json.loads(p.read_text())
d["steps"][0]["statement"] = "bad\n/devloop hijack"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
write_plan_md "$runi"
set +e
out_inj="$(run_cli update --run-dir "$runi" --to implement 2>&1)"
rc_inj=$?
set -e
[[ "$rc_inj" -eq 2 ]] || fail "injection --to implement want 2: $out_inj"
printf '%s\n' "$out_inj" | grep -qi 'newline\|control\|slash\|statement' || fail "injection message: $out_inj"
printf 'LAYER: injection reject OK\n'

# --- blocked CLI + residual -> blocked + resume reclaim ---
runb="$tmpdir/blk/.shiploop"
repob="$tmpdir/blk/repo"
mkdir -p "$repob"
advance_to_plan "$runb" "$repob" "$planf"
install_dag "$runb" two-root.json
run_cli update --run-dir "$runb" --to implement >/dev/null
run_cli next --run-dir "$runb" >/dev/null
run_cli update --run-dir "$runb" --to blocked --resume-to implement --reason "host failed" >/dev/null
set +e
out_bb="$(run_cli complete --run-dir "$runb" --blocked --reason x 2>&1)"
rc_bb=$?
set -e
[[ "$rc_bb" -eq 2 ]] || fail "complete --blocked while blocked want 2: $out_bb"
printf '%s\n' "$out_bb" | grep -q 'complete --reason' \
  || fail "already-blocked --blocked missing complete --reason: $out_bb"
set +e
out_bcs="$(run_cli complete-step --run-dir "$runb" --id S1 2>&1)"
rc_bcs=$?
set -e
[[ "$rc_bcs" -eq 2 ]] || fail "complete while blocked want 2: $out_bcs"
set +e
out_jump="$(run_cli update --run-dir "$runb" --to residual --reason x 2>&1)"
rc_jump=$?
set -e
[[ "$rc_jump" -eq 2 ]] || fail "blocked jump to residual want 2"
run_cli update --run-dir "$runb" --to implement --reason "resume" >/dev/null
out_reclaim="$(run_cli next --run-dir "$runb")"
printf '%s\n' "$out_reclaim" | grep -q 'S1: running' || fail "reclaim S1"
printf '%s\n' "$out_reclaim" | grep -q 'S2: running' || fail "reclaim S2"
# residual -> blocked
# drain first
complete_ok "$runb" S1
complete_ok "$runb" S2
run_cli update --run-dir "$runb" --to residual >/dev/null
run_cli update --run-dir "$runb" --to blocked --resume-to residual --reason "not green" >/dev/null
python3 - "$runb" <<'PY'
import json, sys
from pathlib import Path
d = json.loads((Path(sys.argv[1]) / "state.json").read_text())
assert d["phase"] == "blocked"
assert d["resume_to"] == "residual"
PY
run_cli update --run-dir "$runb" --to residual --reason "suite green" >/dev/null
python3 - "$runb" <<'PY'
import json, sys
from pathlib import Path
d = json.loads((Path(sys.argv[1]) / "state.json").read_text())
assert d["phase"] == "residual", d["phase"]
PY
printf 'LAYER: blocked CLI + reclaim OK\n'

# --- missing backchain blocks implement; refresh ---
runm="$tmpdir/miss/.shiploop"
repom="$tmpdir/miss/repo"
mkdir -p "$repom"
(
  unset SHIPLOOP_BACKCHAIN_ROOT
  export HOME="$tmpdir/empty-home-miss"
  mkdir -p "$HOME"
  init_git_repo "$repom"
  python3 "$cli" init --prompt "x" --run-dir "$runm" --bound-plan "$planf" --repo "$repom" >/dev/null
  python3 "$cli" update --run-dir "$runm" --to validate-spec >/dev/null
  write_environment "$runm"
  write_spec "$runm"
  python3 "$cli" update --run-dir "$runm" --to plan >/dev/null
  install_dag "$runm" linear.json
  set +e
  out_mb="$(python3 "$cli" update --run-dir "$runm" --to implement 2>&1)"
  rc_mb=$?
  set -e
  [[ "$rc_mb" -eq 2 ]] || fail "missing backchain want 2: $out_mb"
  printf '%s\n' "$out_mb" | grep -q 'dep_roots.backchain' || {
    out_pkt="$(python3 "$cli" next --run-dir "$runm")"
    printf '%s\n' "$out_pkt" | grep -q 'dep_roots.backchain' || fail "missing backchain not reported: $out_mb $out_pkt"
  }
)
export SHIPLOOP_BACKCHAIN_ROOT="$fix/backchain-leaf"
run_cli update --run-dir "$runm" --to implement >/dev/null
printf 'LAYER: backchain missing + refresh OK\n'

# --- plan -> blocked ---
runp="$tmpdir/pblock/.shiploop"
repop="$tmpdir/pblock/repo"
mkdir -p "$repop"
advance_to_plan "$runp" "$repop" "$planf"
run_cli update --run-dir "$runp" --to blocked --resume-to plan --reason "no backchain checkout" >/dev/null
python3 - "$runp" <<'PY'
import json, sys
from pathlib import Path
d = json.loads((Path(sys.argv[1]) / "state.json").read_text())
assert d["phase"] == "blocked"
assert d["resume_to"] == "plan"
PY
printf 'LAYER: plan -> blocked OK\n'

# --- no DevLoop leaf required ---
(
  export HOME="$tmpdir/empty-home-nodev"
  mkdir -p "$HOME"
  unset SHIPLOOP_DEVLOOP_ROOT
  export SHIPLOOP_BACKCHAIN_ROOT="$fix/backchain-leaf"
  r="$tmpdir/nodev/.shiploop"
  rp="$tmpdir/nodev/repo"
  init_git_repo "$rp"
  python3 "$cli" init --prompt "x" --run-dir "$r" --bound-plan "$planf" --repo "$rp" >/dev/null
  python3 "$cli" update --run-dir "$r" --to validate-spec >/dev/null
  write_environment "$r"
  write_spec "$r"
  python3 "$cli" update --run-dir "$r" --to plan >/dev/null
  install_dag "$r" linear.json
  python3 "$cli" update --run-dir "$r" --to implement >/dev/null
)
printf 'LAYER: no DevLoop sibling OK\n'

# --- replan clears receipts; wrapper step_ids not SoT ---
runr="$tmpdir/replan/.shiploop"
repor="$tmpdir/replan/repo"
mkdir -p "$repor"
advance_to_plan "$runr" "$repor" "$planf"
install_dag "$runr" linear.json
run_cli update --run-dir "$runr" --to implement >/dev/null
run_cli next --run-dir "$runr" >/dev/null
ridr="$(python3 -c "import json; print(json.load(open('$runr/state.json'))['run_id'])")"
complete_ok "$runr" S1
git -C "$repor" rev-parse --verify "shiploop/$ridr/S1" >/dev/null || fail "complete should keep S1 branch"
run_cli update --run-dir "$runr" --to blocked --resume-to plan --reason "replan" >/dev/null
run_cli update --run-dir "$runr" --to plan --reason "replan" >/dev/null
[[ ! -e "$runr/steps/S1.json" ]] || fail "replan left S1 receipt"
if git -C "$repor" rev-parse --verify "shiploop/$ridr/S1" >/dev/null 2>&1; then
  fail "replan left S1 branch"
fi
# leftover wrapper step_ids are not SoT: stale list must not hide S2
runsot="$tmpdir/sot/.shiploop"
reposot="$tmpdir/sot/repo"
mkdir -p "$reposot"
advance_to_plan "$runsot" "$reposot" "$planf"
install_dag "$runsot" linear.json
run_cli update --run-dir "$runsot" --to implement >/dev/null
printf '%s\n' "{\"done_sentence\":\"$DS\",\"step_ids\":[\"S1\"]}" >"$runsot/plan.json"
run_cli next --run-dir "$runsot" >/dev/null
complete_ok "$runsot" S1
out_sot="$(run_cli next --run-dir "$runsot")"
printf '%s\n' "$out_sot" | grep -q 'S2: running' || fail "stale wrapper step_ids hid S2"
printf 'LAYER: replan clears receipts OK\n'

# --- string produces still accepted ---
runs="$tmpdir/strprod/.shiploop"
repos="$tmpdir/strprod/repo"
mkdir -p "$repos"
advance_to_plan "$runs" "$repos" "$planf"
python3 - "$runs" "$DS" <<'PY'
import json, sys
from pathlib import Path
run = Path(sys.argv[1])
ds = sys.argv[2]
(run / "backchain").mkdir(exist_ok=True)
doc = {
  "goal": ds,
  "initial_state": ["repo exists"],
  "steps": [{
    "id": "S1",
    "statement": "write the file",
    "prompt": "/goal\nDo this activity until these conditions are met:\n- result.txt exists\n\nAssume already true (do not repeat): repo exists.\nPurpose of the plan (do not re-execute as this step): result.txt contains exactly one line: ok\n\nTools:\nWatch with: none(no read-capable session tool matched done-sentence)\nUse: git\nDon't use: none\nAssume: test harness",
    "produces": "result.txt exists",
    "origin": "seed",
    "inputs": [{"need": "repo exists", "from": None}],
  }],
  "parallel_groups": [],
  "unresolved": [],
}
(run / "backchain" / "plan.json").write_text(json.dumps(doc, indent=2) + "\n")
(run / "plan.md").write_text("done_sentence: %s\n" % ds)
PY
run_cli update --run-dir "$runs" --to implement >/dev/null
out_sp="$(run_cli next --run-dir "$runs")"
printf '%s\n' "$out_sp" | grep -q '/goal ' || fail "string produces /goal"
printf 'LAYER: string produces dual-type OK\n'

# --- drift still allows --to blocked ---
rund="$tmpdir/driftblk/.shiploop"
repod="$tmpdir/driftblk/repo"
mkdir -p "$repod"
advance_to_plan "$rund" "$repod" "$planf"
install_dag "$rund" linear.json
run_cli update --run-dir "$rund" --to implement >/dev/null
run_cli next --run-dir "$rund" >/dev/null
printf 'done_sentence: %s\nmutated-again\n' "$DS" >"$rund/spec.md"
set +e
out_dn="$(run_cli next --run-dir "$rund" 2>&1)"
rc_dn=$?
set -e
[[ "$rc_dn" -eq 2 ]] || fail "drift next want 2"
run_cli update --run-dir "$rund" --to blocked --resume-to validate-spec --reason "spec drifted" >/dev/null
python3 - "$rund" <<'PY'
import json, sys
from pathlib import Path
d = json.loads((Path(sys.argv[1]) / "state.json").read_text())
assert d["phase"] == "blocked", d["phase"]
assert d["resume_to"] == "validate-spec"
PY
python3 - "$rund/backchain/plan.json" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
d = json.loads(p.read_text())
d["steps"][0]["statement"] = "also-mutated-dag"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
run_cli update --run-dir "$rund" --to validate-spec --reason "rebind after dual drift" >/dev/null
python3 - "$rund" <<'PY'
import json, sys
from pathlib import Path
d = json.loads((Path(sys.argv[1]) / "state.json").read_text())
assert d["phase"] == "validate-spec", d["phase"]
assert not d.get("spec_sha256")
assert not d.get("plan_sha256")
assert not d.get("environment_sha256")
PY
printf 'LAYER: drift --to blocked OK\n'

# --- clear-step invalidates descendants ---
runc="$tmpdir/desc/.shiploop"
repoc="$tmpdir/desc/repo"
mkdir -p "$repoc"
advance_to_plan "$runc" "$repoc" "$planf"
install_dag "$runc" linear.json
run_cli update --run-dir "$runc" --to implement >/dev/null
run_cli next --run-dir "$runc" >/dev/null
complete_ok "$runc" S1
run_cli next --run-dir "$runc" >/dev/null
complete_ok "$runc" S2
run_cli clear-step --run-dir "$runc" --id S1 >/dev/null
[[ ! -e "$runc/steps/S1.json" ]] || fail "S1 receipt remained"
[[ ! -e "$runc/steps/S2.json" ]] || fail "descendant S2 receipt remained"
set +e
out_clr="$(run_cli update --run-dir "$runc" --to residual 2>&1)"
rc_clr=$?
set -e
[[ "$rc_clr" -eq 2 ]] || fail "clear then residual want 2: $out_clr"
printf 'LAYER: clear-step descendants OK\n'

# --- checkable:false spec.md cannot --to plan, even on a blocked rebind ---
runcf="$tmpdir/checkimpl/.shiploop"
repocf="$tmpdir/checkimpl/repo"
mkdir -p "$repocf"
advance_to_plan "$runcf" "$repocf" "$planf"
install_dag "$runcf" linear.json
run_cli update --run-dir "$runcf" --to blocked --resume-to plan --reason "rebind uncheckable" >/dev/null
printf 'done_sentence: need a checkable done\ncheckable: false\nask_user: what is the oracle?\n' >"$runcf/spec.md"
set +e
out_cf="$(run_cli update --run-dir "$runcf" --to plan --reason "rebind" 2>&1)"
rc_cf=$?
set -e
[[ "$rc_cf" -eq 2 ]] || fail "checkable false plan rebind want 2: $out_cf"
printf '%s\n' "$out_cf" | grep -qi 'checkable' || fail "checkable message: $out_cf"
printf 'LAYER: checkable false plan rebind refuse OK\n'

# --- missing frozen files fail closed; --to blocked still works ---
runmf="$tmpdir/missfiles/.shiploop"
repomf="$tmpdir/missfiles/repo"
mkdir -p "$repomf"
advance_to_plan "$runmf" "$repomf" "$planf"
install_dag "$runmf" linear.json
run_cli update --run-dir "$runmf" --to implement >/dev/null
run_cli next --run-dir "$runmf" >/dev/null
rm -f "$runmf/spec.md"
set +e
out_ms="$(run_cli next --run-dir "$runmf" 2>&1)"
rc_ms=$?
set -e
[[ "$rc_ms" -eq 2 ]] || fail "missing spec.md want 2: $out_ms"
write_spec "$runmf"
rm -f "$runmf/backchain/plan.json"
set +e
out_mp="$(run_cli next --run-dir "$runmf" 2>&1)"
rc_mp=$?
set -e
[[ "$rc_mp" -eq 2 ]] || fail "missing backchain/plan.json want 2: $out_mp"
printf '%s\n' "$out_mp" | grep -q 'backchain/plan.json' \
  || fail "missing DAG message: $out_mp"
run_cli update --run-dir "$runmf" --to blocked --resume-to plan --reason "files gone" >/dev/null
printf 'LAYER: missing frozen files fail-closed OK\n'

# --- planted S2 running without S1 complete is supplier-not-ready ---
runsup="$tmpdir/supplier/.shiploop"
reposup="$tmpdir/supplier/repo"
mkdir -p "$reposup"
advance_to_plan "$runsup" "$reposup" "$planf"
install_dag "$runsup" linear.json
run_cli update --run-dir "$runsup" --to implement >/dev/null
run_cli next --run-dir "$runsup" >/dev/null
python3 - "$runsup" <<'PY'
import json, sys
from pathlib import Path
run = Path(sys.argv[1])
st = json.loads((run / "state.json").read_text())
rec = {
    "writer": "shiploop.start-step",
    "run_id": st["run_id"],
    "id": "S2",
    "status": "running",
    "plan_sha256": st["plan_sha256"],
}
(run / "steps" / "S2.json").write_text(json.dumps(rec, indent=2) + "\n")
PY
set +e
out_sup="$(run_cli complete-step --run-dir "$runsup" --id S2 2>&1)"
rc_sup=$?
set -e
[[ "$rc_sup" -eq 2 ]] || fail "supplier-not-ready want 2: $out_sup"
printf '%s\n' "$out_sup" | grep -qi 'supplier' || fail "supplier message: $out_sup"
# hash-mismatch running receipt
python3 - "$runsup" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1]) / "steps" / "S1.json"
d = json.loads(p.read_text())
d["plan_sha256"] = "0" * 64
p.write_text(json.dumps(d, indent=2) + "\n")
PY
set +e
out_hm="$(run_cli complete-step --run-dir "$runsup" --id S1 2>&1)"
rc_hm=$?
set -e
[[ "$rc_hm" -eq 2 ]] || fail "hash-mismatch complete want 2: $out_hm"
printf 'LAYER: supplier-not-ready + hash-mismatch OK\n'

# --- symlink escape on canonical DAG ---
runsy="$tmpdir/symlink/.shiploop"
reposy="$tmpdir/symlink/repo"
mkdir -p "$reposy"
advance_to_plan "$runsy" "$reposy" "$planf"
install_dag "$runsy" linear.json
rm -f "$runsy/backchain/plan.json"
ln -s /etc/hosts "$runsy/backchain/plan.json"
set +e
out_sy="$(run_cli update --run-dir "$runsy" --to implement 2>&1)"
rc_sy=$?
set -e
[[ "$rc_sy" -eq 2 ]] || fail "symlink DAG want 2: $out_sy"
printf '%s\n' "$out_sy" | grep -qi 'symlink' || fail "symlink message: $out_sy"
printf 'LAYER: symlink escape OK\n'

# --- per-step worktree isolation ---
runwt="$tmpdir/wt/.shiploop"
repowt="$tmpdir/wt/repo"
advance_to_plan "$runwt" "$repowt" "$planf"
install_dag "$runwt" two-root.json
run_cli update --run-dir "$runwt" --to implement >/dev/null
out_wt="$(run_cli next --run-dir "$runwt")"
printf '%s\n' "$out_wt" | grep -q '.worktrees' || fail "goal missing .worktrees: $out_wt"
printf '%s\n' "$out_wt" | grep -q 'shiploop/' || fail "goal missing shiploop/ path or branch"
printf '%s\n' "$out_wt" | grep -q 'worktree — cwd here' || fail "look here missing cwd isolate instruction"
printf '%s\n' "$out_wt" | grep -q 'merge --no-ff --no-edit' \
  || fail "when-done missing session checkout merge instruction"
assert_host_flag "$out_wt" "worktree isolation packet"
ridwt="$(python3 -c "import json; print(json.load(open('$runwt/state.json'))['run_id'])")"
wt1="$(python3 -c "import json; print(json.load(open('$runwt/steps/S1.json'))['worktree'])")"
wt2="$(python3 -c "import json; print(json.load(open('$runwt/steps/S2.json'))['worktree'])")"
[[ -n "$wt1" && -n "$wt2" && "$wt1" != "$wt2" ]] || fail "receipt worktrees not distinct"
printf '%s\n' "$out_wt" | grep -F -q "$wt1" || fail "look here missing S1 worktree path"
printf '%s\n' "$out_wt" | grep -F -q "$wt2" || fail "look here missing S2 worktree path"
assert_absent "$out_wt" "^/goal .*\\.worktrees" "worktree path spliced into /goal prompt line"
[[ -d "$wt1" ]] || fail "S1 worktree missing"
[[ -d "$wt2" ]] || fail "S2 worktree missing"
if [[ -f "$repowt/.gitignore" ]] && grep -q '.worktrees' "$repowt/.gitignore"; then
  fail "tracked .gitignore dirtied with .worktrees"
fi
exclwt="$(git -C "$repowt" rev-parse --git-path info/exclude)"
[[ "$exclwt" == /* ]] || exclwt="$repowt/$exclwt"
[[ -f "$exclwt" ]] || fail "missing info/exclude"
grep -q '.worktrees/' "$exclwt" || fail "info/exclude missing .worktrees/"
[[ "$wt1" != "$wt2" ]] || fail "worktrees not distinct"
git -C "$repowt" rev-parse --verify "shiploop/$ridwt/S1" >/dev/null || fail "S1 branch missing"
git -C "$repowt" rev-parse --verify "shiploop/$ridwt/S2" >/dev/null || fail "S2 branch missing"
complete_ok "$runwt" S1
[[ ! -d "$wt1" ]] || fail "complete-step left S1 checkout"
git -C "$repowt" rev-parse --verify "shiploop/$ridwt/S1" >/dev/null || fail "complete-step deleted S1 branch"
python3 - "$runwt" <<'PY'
import json, sys
from pathlib import Path
rec = json.loads((Path(sys.argv[1]) / "steps" / "S1.json").read_text())
assert rec["status"] == "complete", rec
assert rec.get("worktree") in ("", None)
assert str(rec.get("branch") or "").startswith("shiploop/"), rec
PY
run_cli clear-step --run-dir "$runwt" --id S2 >/dev/null
[[ ! -d "$wt2" ]] || fail "clear-step left S2 checkout"
if git -C "$repowt" rev-parse --verify "shiploop/$ridwt/S2" >/dev/null 2>&1; then
  fail "clear-step left S2 branch"
fi

runng="$tmpdir/nogit/.shiploop"
repong="$tmpdir/nogit/repo"
mkdir -p "$repong"
run_cli init --prompt "create result.txt containing exactly one line: ok" \
  --run-dir "$runng" --bound-plan "$planf" --repo "$repong" >/dev/null
run_cli update --run-dir "$runng" --to validate-spec >/dev/null
write_environment "$runng"
write_spec "$runng"
run_cli update --run-dir "$runng" --to plan >/dev/null
install_dag "$runng" linear.json
set +e
out_ng="$(run_cli update --run-dir "$runng" --to implement 2>&1)"
rc_ng=$?
set -e
[[ "$rc_ng" -eq 2 ]] || fail "non-git implement want 2: $out_ng"
printf '%s\n' "$out_ng" | grep -qi 'git\|worktree' || fail "non-git message: $out_ng"

runlb="$tmpdir/leftover-branch/.shiploop"
repolb="$tmpdir/leftover-branch/repo"
advance_to_plan "$runlb" "$repolb" "$planf"
install_dag "$runlb" linear.json
run_cli update --run-dir "$runlb" --to implement >/dev/null
run_cli next --run-dir "$runlb" >/dev/null
ridlb="$(python3 -c "import json; print(json.load(open('$runlb/state.json'))['run_id'])")"
complete_ok "$runlb" S1
git -C "$repolb" rev-parse --verify "shiploop/$ridlb/S1" >/dev/null || fail "leftover-branch fixture missing S1"
rm -f "$runlb/steps/S1.json"
set +e
out_lb="$(run_cli next --run-dir "$runlb" 2>&1)"
rc_lb=$?
set -e
[[ "$rc_lb" -eq 2 ]] || fail "reclaim over leftover branch want 2: $out_lb"
git -C "$repolb" rev-parse --verify "shiploop/$ridlb/S1" >/dev/null || fail "failed reclaim deleted complete branch"

runempty="$tmpdir/empty-complete/.shiploop"
repoempty="$tmpdir/empty-complete/repo"
advance_to_plan "$runempty" "$repoempty" "$planf"
install_dag "$runempty" linear.json
run_cli update --run-dir "$runempty" --to implement >/dev/null
run_cli next --run-dir "$runempty" >/dev/null
set +e
out_ec="$(run_cli complete-step --run-dir "$runempty" --id S1 2>&1)"
rc_ec=$?
set -e
[[ "$rc_ec" -eq 2 ]] || fail "empty complete want 2: $out_ec"
printf '%s\n' "$out_ec" | grep -qi 'commit' || fail "empty complete message: $out_ec"
printf 'LAYER: worktree isolation OK\n'

# --- complete without prior host merge lands the branch ---
runum="$tmpdir/unmerged/.shiploop"
repoum="$tmpdir/unmerged/repo"
advance_to_plan "$runum" "$repoum" "$planf"
install_dag "$runum" linear.json
out_claim="$(run_cli update --run-dir "$runum" --to implement)"
printf '%s\n' "$out_claim" | awk 'NR==1 {print; exit}' | grep -q 'updated .* implement' \
  || fail "dest implement line1: $out_claim"
printf '%s\n' "$out_claim" | awk '/^## Missing$/,0' | grep -q '^Git ran:' \
  || fail "Git ran not after Missing: $out_claim"
if printf '%s\n' "$out_claim" | grep -qx '## Git ran'; then
  fail "Git ran became an H2"
fi
printf '%s\n' "$out_claim" | awk '/^Git ran:/,0' | grep -q 'worktree add' \
  || fail "claim Git ran missing worktree add: $out_claim"
if printf '%s\n' "$out_claim" | awk '/^Git ran:/,0' | grep -qE 'rev-parse|merge-base|rev-list'; then
  fail "claim Git ran printed probe git"
fi
commit_step_work "$runum" S1
out_um="$(run_cli complete-step --run-dir "$runum" --id S1)"
printf '%s\n' "$out_um" | grep -q 'completed S1' || fail "harness-merge complete: $out_um"
printf '%s\n' "$out_um" | grep -q 'Git ran:' || fail "complete missing Git ran: $out_um"
printf '%s\n' "$out_um" | grep -q 'merge --no-ff --no-edit' || fail "Git ran missing merge: $out_um"
[[ -f "$repoum/S1.txt" ]] || fail "harness merge did not land S1.txt"
printf 'LAYER: harness merge complete OK\n'

# --- dirty worktree complete refuse ---
rundirty="$tmpdir/dirty/.shiploop"
repodirty="$tmpdir/dirty/repo"
advance_to_plan "$rundirty" "$repodirty" "$planf"
install_dag "$rundirty" linear.json
run_cli update --run-dir "$rundirty" --to implement >/dev/null
run_cli next --run-dir "$rundirty" >/dev/null
commit_step_work "$rundirty" S1
wtdirty="$(python3 -c "import json; print(json.load(open('$rundirty/steps/S1.json'))['worktree'])")"
printf 'leftover\n' >"$wtdirty/extra.txt"
set +e
out_dirty="$(run_cli complete-step --run-dir "$rundirty" --id S1 2>&1)"
rc_dirty=$?
set -e
[[ "$rc_dirty" -eq 2 ]] || fail "dirty complete want 2: $out_dirty"
printf '%s\n' "$out_dirty" | grep -q 'extra.txt' || fail "dirty Git ran missing extra.txt: $out_dirty"
[[ ! -f "$repodirty/S1.txt" ]] || fail "dirty complete merged anyway"
printf 'LAYER: dirty complete refuse OK\n'

# --- merge conflict complete refuse ---
runconf="$tmpdir/conflict/.shiploop"
repoconf="$tmpdir/conflict/repo"
advance_to_plan "$runconf" "$repoconf" "$planf"
install_dag "$runconf" linear.json
run_cli update --run-dir "$runconf" --to implement >/dev/null
run_cli next --run-dir "$runconf" >/dev/null
commit_step_work "$runconf" S1
printf 'session\n' >"$repoconf/S1.txt"
git -C "$repoconf" add S1.txt
git -C "$repoconf" commit -m 'session S1 clash' >/dev/null
set +e
out_conf="$(run_cli complete-step --run-dir "$runconf" --id S1 2>&1)"
rc_conf=$?
set -e
[[ "$rc_conf" -eq 2 ]] || fail "conflict complete want 2: $out_conf"
printf '%s\n' "$out_conf" | grep -q 'merge --no-ff --no-edit' || fail "conflict missing merge argv: $out_conf"
printf '%s\n' "$out_conf" | grep -qi 'CONFLICT\|Automatic merge failed' \
  || fail "conflict missing git conflict text: $out_conf"
wtconf="$(python3 -c "import json; print(json.load(open('$runconf/steps/S1.json'))['worktree'])")"
[[ -d "$wtconf" ]] || fail "conflict complete removed worktree"
printf 'LAYER: conflict complete refuse OK\n'

# --- two running + no --id from session cwd ---
run2r="$tmpdir/tworun/.shiploop"
repo2r="$tmpdir/tworun/repo"
advance_to_plan "$run2r" "$repo2r" "$planf"
install_dag "$run2r" two-root.json
run_cli update --run-dir "$run2r" --to implement >/dev/null
run_cli next --run-dir "$run2r" >/dev/null
set +e
out_2r="$(cd "$repo2r" && run_cli complete 2>&1)"
rc_2r=$?
set -e
[[ "$rc_2r" -eq 2 ]] || fail "two-running complete want 2: $out_2r"
printf '%s\n' "$out_2r" | grep -qi 'multiple running' || fail "two-running message: $out_2r"
wt2s1="$(python3 -c "import json; print(json.load(open('$run2r/steps/S1.json'))['worktree'])")"
commit_step_work "$run2r" S1
merge_step_branch "$run2r" S1
out_cwd="$(cd "$wt2s1" && run_cli complete --inner-loop parent)"
printf '%s\n' "$out_cwd" | grep -q 'completed S1' || fail "cwd worktree did not complete S1: $out_cwd"
python3 - "$run2r" <<'PY'
import json, sys
from pathlib import Path
rec = json.loads((Path(sys.argv[1]) / "steps" / "S1.json").read_text())
assert rec["status"] == "complete", rec
PY
printf 'LAYER: two-running inference OK\n'

# --- implement completion requires and records inner-loop attestation ---
runil="$tmpdir/inner-loop/.shiploop"
repoil="$tmpdir/inner-loop/repo"
advance_to_plan "$runil" "$repoil" "$planf"
install_dag "$runil" linear.json
run_cli update --run-dir "$runil" --to implement >/dev/null
run_cli next --run-dir "$runil" >/dev/null
commit_step_work "$runil" S1
merge_step_branch "$runil" S1
set +e
out_il_missing="$(run_cli complete --run-dir "$runil" --id S1 2>&1)"
rc_il_missing=$?
set -e
[[ "$rc_il_missing" -eq 2 ]] || fail "implement complete without inner-loop want 2: $out_il_missing"
printf '%s\n' "$out_il_missing" | grep -Fq -- '--inner-loop goal|parent' \
  || fail "implement complete missing inner-loop message: $out_il_missing"
out_il_parent="$(run_cli complete --run-dir "$runil" --id S1 --inner-loop parent)"
printf '%s\n' "$out_il_parent" | grep -q 'completed S1' \
  || fail "parent inner-loop complete did not complete S1: $out_il_parent"
python3 - "$runil" <<'PY' || fail "inner-loop parent receipt missing"
import json, sys
from pathlib import Path
rec = json.loads((Path(sys.argv[1]) / "steps" / "S1.json").read_text())
assert rec.get("inner_loop") == "parent", rec
PY
python3 - "$cli" "$runil" <<'PY' || fail "recap inner-loop attestation missing"
import importlib.machinery, importlib.util, json, sys
from pathlib import Path
loader = importlib.machinery.SourceFileLoader("shiploop_inner", sys.argv[1])
spec = importlib.util.spec_from_loader("shiploop_inner", loader)
mod = importlib.util.module_from_spec(spec)
loader.exec_module(mod)
run = Path(sys.argv[2])
html = mod.render_recap_html(run, json.loads((run / "state.json").read_text()), dest="done")
assert "Inner loop attestation" in html and "S1: parent" in html, html
PY
printf 'LAYER: implement inner-loop attestation OK\n'

# --- closer-walk: complete only (no --id / --to) ---
runw="$tmpdir/walk/.shiploop"
repow="$tmpdir/walk/repo"
init_git_repo "$repow"
run_cli init --prompt "create result.txt containing exactly one line: ok" \
  --run-dir "$runw" --bound-plan "$planf" --repo "$repow" >/dev/null
out_w1="$(cd "$repow" && run_cli complete)"
printf '%s\n' "$out_w1" | grep -q 'validate-spec: current' || fail "closer walk not validate-spec: $out_w1"
printf '%s\n' "$out_w1" | grep -q 'invoke /shiploop complete' || fail "closer walk missing skill"
write_environment "$runw"
write_spec "$runw"
out_w2="$(run_cli complete --run-dir "$runw")"
printf '%s\n' "$out_w2" | grep -q 'plan: current' || fail "closer walk not plan: $out_w2"
install_dag "$runw" linear.json
out_w3="$(run_cli complete --run-dir "$runw")"
printf '%s\n' "$out_w3" | grep -q 'implement: current' || fail "closer walk not implement: $out_w3"
printf '%s\n' "$out_w3" | grep -q 'S1: running' || fail "closer walk did not claim S1"
printf '%s\n' "$out_w3" | grep -q 'from initial_state' || fail "closer walk /goal None"
commit_step_work "$runw" S1
wt_s1="$(python3 -c "import json; print(json.load(open('$runw/steps/S1.json'))['worktree'])")"
s1sha="$(git -C "$wt_s1" rev-parse HEAD)"
[[ -n "$s1sha" ]] || fail "closer walk missing S1 commit sha"
merge_step_branch "$runw" S1
out_w4="$(run_cli complete --run-dir "$runw" --inner-loop parent)"
printf '%s\n' "$out_w4" | grep -q 'completed S1' || fail "closer walk S1: $out_w4"
printf '%s\n' "$out_w4" | grep -q 'S2: running' || fail "closer walk did not claim S2"
printf '%s\n' "$out_w4" | grep -q 'stand      implement — 1/2 steps done' || fail "closer walk mid stand"
wt_s2="$(python3 -c "import json; print(json.load(open('$runw/steps/S2.json'))['worktree'])")"
[[ -f "$wt_s2/S1.txt" ]] || fail "S2 worktree missing merged S1.txt"
git -C "$wt_s2" merge-base --is-ancestor "$s1sha" HEAD \
  || fail "S2 worktree missing S1 commit $s1sha"
git -C "$wt_s2" log -1 --format=%s "$s1sha" | grep -qx 'step S1' \
  || fail "S2 log missing S1 subject"
commit_step_work "$runw" S2
merge_step_branch "$runw" S2
out_w5="$(run_cli complete --run-dir "$runw" --inner-loop parent)"
printf '%s\n' "$out_w5" | grep -q 'completed S2' || fail "closer walk S2: $out_w5"
n_out="$(printf '%s\n' "$out_w5" | grep -c '^completed S2$' || true)"
[[ "$n_out" -eq 1 ]] || fail "closer walk last complete extra outcome: $out_w5"
printf '%s\n' "$out_w5" | grep -q 'residual: current' || fail "closer walk not residual: $out_w5"
assert_absent "$out_w5" 'updated implement -> residual' "last complete printed dest residual outcome"
assert_absent "$out_w5" 'does not auto-dest residual' "last complete still says no auto-dest"
python3 - "$runw" <<'PY'
import json, sys
from pathlib import Path
d = json.loads((Path(sys.argv[1]) / "state.json").read_text())
assert d["phase"] == "residual", d["phase"]
PY
printf 'LAYER: closer-walk OK\n'

# --- same-leaf next / complete wrappers ---
nextw="$root/skills/shiploop/scripts/shiploop-next"
compw="$root/skills/shiploop/scripts/shiploop-complete"
chmod +x "$nextw" "$compw"
runwrap="$tmpdir/wrap/.shiploop"
repowrap="$tmpdir/wrap/repo"
init_git_repo "$repowrap"
run_cli init --prompt "create result.txt containing exactly one line: ok" \
  --run-dir "$runwrap" --bound-plan "$planf" --repo "$repowrap" >/dev/null
out_n="$(python3 "$nextw" --run-dir "$runwrap")"
printf '%s\n' "$out_n" | grep -q 'shiploop next — reprint the packet' || fail "next wrapper banner: $out_n"
printf '%s\n' "$out_n" | grep -q 'shiploop — session harness' || fail "next wrapper missing harness banner"
assert_absent "$out_n" 'DevLoop' "next wrapper banner named a foreign product"
for cmd in update complete complete-step start-step; do
  set +e
  bad="$(python3 "$nextw" "$cmd" --run-dir "$runwrap" 2>&1)"
  rc=$?
  set -e
  [[ "$rc" -eq 2 ]] || fail "next wrapper refuse $cmd want 2: $bad"
done
out_c="$(python3 "$compw" --run-dir "$runwrap")"
printf '%s\n' "$out_c" | grep -q 'shiploop complete — close the increment and print the next packet' \
  || fail "complete wrapper banner: $out_c"
printf '%s\n' "$out_c" | grep -q 'validate-spec: current' || fail "complete wrapper did not advance: $out_c"
printf '%s\n' "$out_c" | grep -q 'invoke /shiploop complete' || fail "complete wrapper packet When done"
for cmd in next update complete complete-step start-step; do
  set +e
  bad="$(python3 "$compw" "$cmd" --run-dir "$runwrap" 2>&1)"
  rc=$?
  set -e
  [[ "$rc" -eq 2 ]] || fail "complete wrapper refuse $cmd want 2: $bad"
done
printf 'LAYER: same-leaf wrappers OK\n'

# --- A3/A13/A14/A15 machine shape + handle/initiation/UI gates ---
runm="$tmpdir/machine/.shiploop"
repom="$tmpdir/machine/repo"
fresh_vs "$runm" "$repom"

printf 'brief only, no machine heading\n' >"$runm/environment.md"
set +e
out_nf="$(run_cli update --run-dir "$runm" --to plan 2>&1)"
rc_nf=$?
set -e
[[ "$rc_nf" -eq 2 ]] || fail "missing machine fence want 2: $out_nf"
printf '%s\n' "$out_nf" | grep -qi 'machine' || fail "missing machine fence message: $out_nf"

write_machine "$runm" '{"kind": "greenfield", "augment": true, "references": [], "tools": [], "mcp": [],
 "mcp_considered": "none(x)", "handles": [], "initiation": "none", "ui": false, "ui_craft": "none(no UI)"}'
set +e
out_ka="$(run_cli update --run-dir "$runm" --to plan 2>&1)"
rc_ka=$?
set -e
[[ "$rc_ka" -eq 2 ]] || fail "greenfield+augment true want 2: $out_ka"

write_machine "$runm" '{"kind": "brownfield", "augment": false, "references": [{"path": "x", "why": "y"}], "tools": [], "mcp": [],
 "mcp_considered": "none(x)", "handles": [], "initiation": "none", "ui": false, "ui_craft": "none(no UI)"}'
set +e
out_bf="$(run_cli update --run-dir "$runm" --to plan 2>&1)"
rc_bf=$?
set -e
[[ "$rc_bf" -eq 2 ]] || fail "brownfield+augment false want 2: $out_bf"

write_machine "$runm" '{"kind": "brownfield", "augment": true, "references": [], "tools": [], "mcp": [],
 "mcp_considered": "none(x)", "handles": [], "initiation": "none", "ui": false, "ui_craft": "none(no UI)"}'
set +e
out_br="$(run_cli update --run-dir "$runm" --to plan 2>&1)"
rc_br=$?
set -e
[[ "$rc_br" -eq 2 ]] || fail "brownfield empty references want 2: $out_br"

write_machine "$runm" '{"kind": "greenfield", "augment": false, "references": [], "tools": [], "mcp": [],
 "mcp_considered": "none(x)",
 "handles": [{"source": "gh", "need": "repo id", "resolve": "ask", "value": ""}],
 "initiation": "none", "ui": false, "ui_craft": "none(no UI)"}'
set +e
out_ask="$(run_cli update --run-dir "$runm" --to plan 2>&1)"
rc_ask=$?
set -e
[[ "$rc_ask" -eq 2 ]] || fail "handle ask blocks plan want 2: $out_ask"
printf '%s\n' "$out_ask" | grep -qi 'blocks dest plan' || fail "handle ask message: $out_ask"

write_machine "$runm" '{"kind": "greenfield", "augment": false, "references": [], "tools": [], "mcp": [],
 "mcp_considered": "none(x)",
 "handles": [{"source": "gh", "need": "repo id", "resolve": "inspect", "value": ""}],
 "initiation": "none", "ui": false, "ui_craft": "none(no UI)"}'
set +e
out_iv="$(run_cli update --run-dir "$runm" --to plan 2>&1)"
rc_iv=$?
set -e
[[ "$rc_iv" -eq 2 ]] || fail "inspect missing value want 2: $out_iv"

write_machine "$runm" '{"kind": "greenfield", "augment": false, "references": [], "tools": [], "mcp": [],
 "mcp_considered": "none(x)",
 "handles": [{"source": "gh", "need": "credential", "resolve": "inspect", "value": "secret"}],
 "initiation": "none", "ui": false, "ui_craft": "none(no UI)"}'
set +e
out_cv="$(run_cli update --run-dir "$runm" --to plan 2>&1)"
rc_cv=$?
set -e
[[ "$rc_cv" -eq 2 ]] || fail "credential inspect with value want 2: $out_cv"

write_machine "$runm" '{"kind": "greenfield", "augment": false, "references": [], "tools": [], "mcp": [],
 "mcp_considered": "none(x)", "handles": [], "initiation": "needed", "ui": false, "ui_craft": "none(no UI)"}'
set +e
out_in="$(run_cli update --run-dir "$runm" --to plan 2>&1)"
rc_in=$?
set -e
[[ "$rc_in" -eq 2 ]] || fail "initiation needed without create want 2: $out_in"

write_machine "$runm" '{"kind": "greenfield", "augment": false, "references": [], "tools": [], "mcp": [],
 "mcp_considered": "none(x)",
 "handles": [{"source": "gh", "need": "repo id", "resolve": "create", "value": ""}],
 "initiation": "none", "ui": false, "ui_craft": "none(no UI)"}'
set +e
out_ic="$(run_cli update --run-dir "$runm" --to plan 2>&1)"
rc_ic=$?
set -e
[[ "$rc_ic" -eq 2 ]] || fail "initiation none with create want 2: $out_ic"

write_machine "$runm" '{"kind": "greenfield", "augment": false, "references": [], "tools": [], "mcp": [],
 "mcp_considered": "none(x)",
 "handles": [{"source": "gh", "need": "repo id", "resolve": "create", "value": ""}],
 "initiation": "done", "ui": false, "ui_craft": "none(no UI)"}'
set +e
out_id="$(run_cli update --run-dir "$runm" --to plan 2>&1)"
rc_id=$?
set -e
[[ "$rc_id" -eq 2 ]] || fail "initiation done with create want 2: $out_id"

write_machine "$runm" '{"kind": "greenfield", "augment": false, "references": [], "tools": [], "mcp": [],
 "mcp_considered": "none(x)", "handles": [], "initiation": "none", "ui": true, "ui_craft": "none(no skill)"}'
set +e
out_ui="$(run_cli update --run-dir "$runm" --to plan 2>&1)"
rc_ui=$?
set -e
[[ "$rc_ui" -eq 2 ]] || fail "ui true + ui_craft none want 2: $out_ui"

write_machine "$runm" '{"kind": "greenfield", "augment": false, "references": [], "tools": [], "mcp": [],
 "mcp_considered": "none(x)", "handles": [], "initiation": "none", "ui": false, "ui_craft": "frontend-design"}'
set +e
out_uf="$(run_cli update --run-dir "$runm" --to plan 2>&1)"
rc_uf=$?
set -e
[[ "$rc_uf" -eq 2 ]] || fail "ui false + named ui_craft want 2: $out_uf"

write_machine "$runm" '{"kind": "greenfield", "augment": false, "references": [], "tools": [], "mcp": ["writer-mcp"],
 "mcp_considered": "none(x)", "handles": [], "initiation": "none", "ui": false, "ui_craft": "none(no UI)"}'
set +e
out_exm="$(run_cli update --run-dir "$runm" --to plan 2>&1)"
rc_exm=$?
set -e
[[ "$rc_exm" -eq 2 ]] || fail "dest plan missing exclusive key want 2: $out_exm"
printf '%s\n' "$out_exm" | grep -qi 'exclusive' || fail "missing exclusive message: $out_exm"

write_machine "$runm" '{"kind": "greenfield", "augment": false, "references": [], "tools": ["alt-cli"], "mcp": ["writer-mcp"],
 "mcp_considered": "none(x)", "handles": [], "initiation": "none", "ui": false, "ui_craft": "none(no UI)",
 "exclusive": [{"artifact": "", "use": "writer-mcp", "dont_use": ["alt-cli"]}]}'
set +e
out_exa="$(run_cli update --run-dir "$runm" --to plan 2>&1)"
rc_exa=$?
set -e
[[ "$rc_exa" -eq 2 ]] || fail "exclusive empty artifact want 2: $out_exa"

write_machine "$runm" '{"kind": "greenfield", "augment": false, "references": [], "tools": ["alt-cli"], "mcp": ["writer-mcp"],
 "mcp_considered": "none(x)", "handles": [], "initiation": "none", "ui": false, "ui_craft": "none(no UI)",
 "exclusive": [{"artifact": "hosted id", "use": "ghost", "dont_use": ["alt-cli"]}]}'
set +e
out_exu="$(run_cli update --run-dir "$runm" --to plan 2>&1)"
rc_exu=$?
set -e
[[ "$rc_exu" -eq 2 ]] || fail "exclusive use not inventoried want 2: $out_exu"
printf '%s\n' "$out_exu" | grep -q 'must be an inventoried tools or mcp name' \
  || fail "inventoried message: $out_exu"

write_machine "$runm" '{"kind": "greenfield", "augment": false, "references": [{"path": "x", "why": "y"}], "tools": [], "mcp": [],
 "mcp_considered": "none(x)", "handles": [], "initiation": "none", "ui": false, "ui_craft": "none(no UI)",
 "exclusive": [{"artifact": "hosted", "use": "ghost", "dont_use": []}]}'
set +e
out_exg="$(run_cli update --run-dir "$runm" --to plan 2>&1)"
rc_exg=$?
set -e
[[ "$rc_exg" -eq 2 ]] || fail "empty inventory exclusive use ghost want 2: $out_exg"
printf '%s\n' "$out_exg" | grep -q 'must be an inventoried tools or mcp name' \
  || fail "empty-inventory inventoried message: $out_exg"

write_machine "$runm" '{"kind": "greenfield", "augment": false, "references": [], "tools": [], "mcp": [],
 "mcp_considered": "none(x)",
 "handles": [{"source": "gh", "need": "repo id", "resolve": "inspect", "value": "abc"}],
 "initiation": "none", "ui": true, "ui_craft": "frontend-design", "exclusive": []}'
set +e
out_uiref="$(run_cli update --run-dir "$runm" --to plan 2>&1)"
rc_uiref=$?
set -e
[[ "$rc_uiref" -eq 2 ]] || fail "ui craft missing reference want 2: $out_uiref"
printf '%s\n' "$out_uiref" | grep -q 'ui_craft' || fail "ui craft gap missing token: $out_uiref"
printf '%s\n' "$out_uiref" | grep -q 'references' || fail "ui craft gap missing references: $out_uiref"

write_machine "$runm" '{"kind": "greenfield", "augment": false, "references": [{"path": "skills/frontend-design/README.md", "why": "distinctive identity and interaction"}], "tools": [], "mcp": [],
 "mcp_considered": "none(x)",
 "handles": [{"source": "gh", "need": "repo id", "resolve": "inspect", "value": "abc"}],
 "initiation": "none", "ui": true, "ui_craft": "frontend-design", "exclusive": []}'
run_cli update --run-dir "$runm" --to plan >/dev/null
printf 'LAYER: machine shape + handle/initiation/UI OK\n'

# --- A7/A12 brownfield existing-app + --force keeps product file ---
applife="$fix/existing-app/app.py"
runlife="$tmpdir/life/.shiploop"
repolife="$tmpdir/life/repo"
mkdir -p "$repolife"
init_git_repo "$repolife"
cp "$applife" "$repolife/app.py"
git -C "$repolife" add app.py
git -C "$repolife" commit -m "session A app" >/dev/null
advance_to_plan "$runlife" "$repolife" "$planf"
run_cli init --force --prompt "add undo to the existing app" \
  --run-dir "$runlife" --bound-plan "$planf" --repo "$repolife" >/dev/null
[[ -f "$repolife/app.py" ]] || fail "--force deleted product app.py"
[[ -f "$repolife/README" ]] || fail "--force deleted seed README"
run_cli update --run-dir "$runlife" --to validate-spec >/dev/null
write_spec "$runlife"
write_machine "$runlife" "{\"kind\": \"brownfield\", \"augment\": true, \"references\": [{\"path\": \"$applife\", \"why\": \"Session A product\"}], \"tools\": [], \"mcp\": [],
 \"mcp_considered\": \"none(x)\", \"handles\": [], \"initiation\": \"none\", \"ui\": false, \"ui_craft\": \"none(no UI)\", \"exclusive\": []}"
run_cli update --run-dir "$runlife" --to plan >/dev/null
python3 - "$runlife/environment.md" "$applife" <<'PY' || fail "brownfield env did not cite existing-app"
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8")
if sys.argv[2] not in text:
    raise SystemExit("existing-app path missing from environment.md")
PY
printf 'LAYER: brownfield existing-app + force keeps app OK\n'

# --- A19 first-bind via blocked → plan, then drift ---
runfb="$tmpdir/firstbind/.shiploop"
repofb="$tmpdir/firstbind/repo"
fresh_vs "$runfb" "$repofb"
write_environment "$runfb"
printf 'done_sentence: %s\ncheckable: false\nask_user: hold for first bind\n' "$DS" >"$runfb/spec.md"
run_cli update --run-dir "$runfb" --to blocked --resume-to plan --reason "hold for bind" >/dev/null
python3 - "$runfb" <<'PY'
import json, sys
from pathlib import Path
d = json.loads((Path(sys.argv[1]) / "state.json").read_text())
assert d["phase"] == "blocked", d["phase"]
assert not d.get("spec_sha256")
assert not d.get("environment_sha256")
PY
write_spec "$runfb"
run_cli update --run-dir "$runfb" --to plan --reason "first bind" >/dev/null
python3 - "$runfb" <<'PY'
import json, sys
from pathlib import Path
d = json.loads((Path(sys.argv[1]) / "state.json").read_text())
assert d["phase"] == "plan", d["phase"]
assert d.get("spec_sha256")
assert d.get("environment_sha256")
PY
run_cli update --run-dir "$runfb" --to blocked --resume-to plan --reason "re-check" >/dev/null
printf 'mutated-env\n' >>"$runfb/environment.md"
set +e
out_fbd="$(run_cli update --run-dir "$runfb" --to plan --reason "drift" 2>&1)"
rc_fbd=$?
set -e
[[ "$rc_fbd" -eq 2 ]] || fail "blocked→plan after env edit want 2: $out_fbd"
printf 'LAYER: blocked→plan first-bind + drift OK\n'

# --- Tools: seed gate is independent of references ---
runtg="$tmpdir/toolsgate/.shiploop"
repotg="$tmpdir/toolsgate/repo"
advance_to_plan "$runtg" "$repotg" "$planf"
write_seed_dag() {
  local run="$1" prompt="$2"
  python3 - "$run" "$DS" "$prompt" <<'PY'
import json, sys
from pathlib import Path
run = Path(sys.argv[1])
ds, prompt = sys.argv[2], sys.argv[3]
(run / "backchain").mkdir(exist_ok=True)
doc = {
  "goal": ds,
  "initial_state": ["repo exists"],
  "steps": [{
    "id": "S1",
    "statement": "write the file",
    "prompt": prompt,
    "produces": ["result.txt exists"],
    "origin": "seed",
    "inputs": [{"need": "repo exists", "from": None}],
  }],
  "parallel_groups": [],
  "unresolved": [],
}
(run / "backchain" / "plan.json").write_text(json.dumps(doc, indent=2) + "\n")
(run / "plan.md").write_text("done_sentence: %s\n" % ds)
PY
}
write_seed_and_discovered_dag() {
  local run="$1" seed_prompt="$2" disc_prompt="$3"
  python3 - "$run" "$DS" "$seed_prompt" "$disc_prompt" <<'PY'
import json, sys
from pathlib import Path
run = Path(sys.argv[1])
ds, seed_prompt, disc_prompt = sys.argv[2], sys.argv[3], sys.argv[4]
(run / "backchain").mkdir(exist_ok=True)
doc = {
  "goal": ds,
  "initial_state": ["repo exists"],
  "steps": [
    {
      "id": "S1",
      "statement": "write the file",
      "prompt": seed_prompt,
      "produces": ["result.txt exists"],
      "origin": "seed",
      "inputs": [{"need": "repo exists", "from": None}],
    },
    {
      "id": "S2",
      "statement": "mid",
      "prompt": disc_prompt,
      "produces": ["mid exists"],
      "origin": "discovered",
      "inputs": [{"need": "result.txt exists", "from": "S1"}],
    },
  ],
  "parallel_groups": [],
  "unresolved": [],
}
(run / "backchain" / "plan.json").write_text(json.dumps(doc, indent=2) + "\n")
(run / "plan.md").write_text("done_sentence: %s\n" % ds)
PY
}
DEFAULT_MC='none(no read-capable session tool matched done-sentence)'
UNTIL_PREFIX='/goal
Do this activity until these conditions are met:
- result.txt exists
'

# --- ui craft citation and early design seed gates ---
runui="$tmpdir/ui-design/.shiploop"
repoui="$tmpdir/ui-design/repo"
fresh_vs "$runui" "$repoui"
uicraft_ref='skills/frontend-design/README.md'
write_machine "$runui" "{\"kind\": \"greenfield\", \"augment\": false, \"references\": [{\"path\": \"$uicraft_ref\", \"why\": \"distinctive identity and interaction\"}], \"tools\": [], \"mcp\": [],
 \"mcp_considered\": \"none(x)\", \"handles\": [], \"initiation\": \"none\", \"ui\": true, \"ui_craft\": \"frontend-design\", \"exclusive\": []}"
run_cli update --run-dir "$runui" --to plan >/dev/null
write_seed_dag "$runui" "${UNTIL_PREFIX}cite ${uicraft_ref}
Tools:
Watch with: none(x)
Use: git
Don't use: none
Assume: test harness"
set +e
out_uidesign="$(run_cli update --run-dir "$runui" --to implement 2>&1)"
rc_uidesign=$?
set -e
[[ "$rc_uidesign" -eq 2 ]] || fail "ui without design seed want 2: $out_uidesign"
printf '%s\n' "$out_uidesign" | grep -qi 'ui.*design.*seed' \
  || fail "ui design seed gap message: $out_uidesign"
python3 - "$runui" "$DS" "$uicraft_ref" <<'PY'
import json, sys
from pathlib import Path
run = Path(sys.argv[1])
ds, ref = sys.argv[2], sys.argv[3]
tools = "Tools:\nWatch with: none(x)\nUse: git\nDon't use: none\nAssume: test harness"
doc = {
  "goal": ds,
  "initial_state": ["repo exists"],
  "steps": [
    {
      "id": "S1", "statement": "design the surface",
      "prompt": "/goal\nDo this activity until these conditions are met:\n- a recorded UI design and interaction model\n\nUse %s for distinctive craft.\n%s" % (ref, tools),
      "produces": ["a recorded UI design and interaction model"],
      "origin": "seed", "inputs": [{"need": "repo exists", "from": None}],
    },
    {
      "id": "S2", "statement": "build the surface",
      "prompt": "/goal\nDo this activity until these conditions are met:\n- result.txt exists\n\nImplement using %s.\n%s" % (ref, tools),
      "produces": ["result.txt exists"], "origin": "seed",
      "inputs": [{"need": "repo exists", "from": None}],
    },
  ],
  "parallel_groups": [], "unresolved": [],
}
(run / "backchain" / "plan.json").write_text(json.dumps(doc, indent=2) + "\n")
(run / "plan.md").write_text("done_sentence: %s\n" % ds)
PY
set +e
out_uidep="$(run_cli update --run-dir "$runui" --to implement 2>&1)"
rc_uidep=$?
set -e
[[ "$rc_uidep" -eq 2 ]] || fail "ui design seed without dependent want 2: $out_uidep"
printf '%s\n' "$out_uidep" | grep -qi 'feed another seed' \
  || fail "ui design dependent gap message: $out_uidep"
python3 - "$runui" "$DS" "$uicraft_ref" <<'PY'
import json, sys
from pathlib import Path
run = Path(sys.argv[1])
ds, ref = sys.argv[2], sys.argv[3]
tools = "Tools:\nWatch with: none(x)\nUse: git\nDon't use: none\nAssume: test harness"
doc = {
  "goal": ds,
  "initial_state": ["repo exists"],
  "steps": [
    {
      "id": "S1", "statement": "design the surface",
      "prompt": "/goal\nDo this activity until these conditions are met:\n- a recorded UI design and interaction model\n\nUse %s for distinctive craft.\n%s" % (ref, tools),
      "produces": ["a recorded UI design and interaction model"],
      "origin": "seed", "inputs": [{"need": "repo exists", "from": None}],
    },
    {
      "id": "S2", "statement": "build the surface",
      "prompt": "/goal\nDo this activity until these conditions are met:\n- result.txt exists\n\nImplement the recorded design using %s.\n%s" % (ref, tools),
      "produces": ["result.txt exists"], "origin": "seed",
      "inputs": [{"need": "a recorded UI design and interaction model", "from": "S1"}],
    },
  ],
  "parallel_groups": [], "unresolved": [],
}
(run / "backchain" / "plan.json").write_text(json.dumps(doc, indent=2) + "\n")
(run / "plan.md").write_text("done_sentence: %s\n" % ds)
PY
run_cli update --run-dir "$runui" --to implement >/dev/null
printf 'LAYER: ui craft citation + early design seed gates OK\n'

write_seed_dag "$runtg" "${UNTIL_PREFIX}/goal no tools header"
set +e
out_tg1="$(run_cli update --run-dir "$runtg" --to implement 2>&1)"
rc_tg1=$?
set -e
[[ "$rc_tg1" -eq 2 ]] || fail "empty-refs no Tools: want 2: $out_tg1"
printf '%s\n' "$out_tg1" | grep -q 'line starting with Tools:' || fail "empty-refs Tools: message: $out_tg1"
write_seed_dag "$runtg" "${UNTIL_PREFIX}See Tools: below
Watch with: ${DEFAULT_MC}"
set +e
out_tg2="$(run_cli update --run-dir "$runtg" --to implement 2>&1)"
rc_tg2=$?
set -e
[[ "$rc_tg2" -eq 2 ]] || fail "mid-line Tools: want 2: $out_tg2"
printf '%s\n' "$out_tg2" | grep -q 'line starting with Tools:' || fail "mid-line Tools: message: $out_tg2"
write_seed_dag "$runtg" "${UNTIL_PREFIX}Tools:
Use: git
Don't use: none"
set +e
out_tg3="$(run_cli update --run-dir "$runtg" --to implement 2>&1)"
rc_tg3=$?
set -e
[[ "$rc_tg3" -eq 2 ]] || fail "Tools: without token want 2: $out_tg3"
printf '%s\n' "$out_tg3" | grep -q "mcp_considered ${DEFAULT_MC}" || fail "missing token message: $out_tg3"
write_seed_dag "$runtg" "${UNTIL_PREFIX}Tools:
Watch with: ${DEFAULT_MC}
Use: git
Don't use: none
Assume: test harness"
run_cli update --run-dir "$runtg" --to implement >/dev/null
printf 'LAYER: Tools: seed gate OK\n'

# --- prompt_until_gaps: dest implement refuses missing /goal, until, produces ---
runug="$tmpdir/untilgaps/.shiploop"
repoug="$tmpdir/untilgaps/repo"
advance_to_plan "$runug" "$repoug" "$planf"
TOOLS_OK="Tools:
Watch with: ${DEFAULT_MC}
Use: git
Don't use: none
Assume: test harness"
write_seed_dag "$runug" "$TOOLS_OK"
set +e
out_ug1="$(run_cli update --run-dir "$runug" --to implement 2>&1)"
rc_ug1=$?
set -e
[[ "$rc_ug1" -eq 2 ]] || fail "until-gaps no /goal want 2: $out_ug1"
printf '%s\n' "$out_ug1" | grep -q 'line starting with /goal' || fail "no /goal message: $out_ug1"
write_seed_dag "$runug" "/goal
${TOOLS_OK}"
set +e
out_ug2="$(run_cli update --run-dir "$runug" --to implement 2>&1)"
rc_ug2=$?
set -e
[[ "$rc_ug2" -eq 2 ]] || fail "until-gaps no UNTIL_HEAD want 2: $out_ug2"
printf '%s\n' "$out_ug2" | grep -F "Do this activity until these conditions are met:" \
  || fail "no until message: $out_ug2"
write_seed_dag "$runug" "/goal
Do this activity until these conditions are met:
- something else
${TOOLS_OK}"
set +e
out_ug3="$(run_cli update --run-dir "$runug" --to implement 2>&1)"
rc_ug3=$?
set -e
[[ "$rc_ug3" -eq 2 ]] || fail "until-gaps missing produces want 2: $out_ug3"
printf '%s\n' "$out_ug3" | grep -q "until-clause must name produces" \
  || fail "missing produces message: $out_ug3"
printf 'LAYER: prompt_until_gaps refusals OK\n'

runiu="$tmpdir/inject-until/.shiploop"
repoiu="$tmpdir/inject-until/repo"
advance_to_plan "$runiu" "$repoiu" "$planf"
install_dag "$runiu" linear.json
run_cli update --run-dir "$runiu" --to implement >/dev/null
run_cli next --run-dir "$runiu" >/dev/null
set +e
out_iu="$(run_cli inject-step --run-dir "$runiu" --statement "mid" --prompt "no goal line" --produces "mid exists" --before S2 2>&1)"
rc_iu=$?
set -e
[[ "$rc_iu" -eq 2 ]] || fail "inject without /goal want 2: $out_iu"
printf '%s\n' "$out_iu" | grep -q 'line starting with /goal' || fail "inject no /goal message: $out_iu"
printf 'LAYER: inject-step until-gate OK\n'

# --- A25 empty prompt refuses dest implement; A27 refs must be cited ---
runpr="$tmpdir/promptref/.shiploop"
repopr="$tmpdir/promptref/repo"
advance_to_plan "$runpr" "$repopr" "$planf"
install_dag "$runpr" missing-prompt.json
set +e
out_mp="$(run_cli update --run-dir "$runpr" --to implement 2>&1)"
rc_mp=$?
set -e
[[ "$rc_mp" -eq 2 ]] || fail "missing-prompt dest implement want 2: $out_mp"
printf '%s\n' "$out_mp" | grep -qi 'prompt' || fail "missing-prompt message: $out_mp"

refpath="$fix/existing-app/README.md"
write_machine "$runpr" "{\"kind\": \"greenfield\", \"augment\": false, \"references\": [{\"path\": \"$refpath\", \"why\": \"practice\"}], \"tools\": [], \"mcp\": [],
 \"mcp_considered\": \"none(x)\", \"handles\": [], \"initiation\": \"none\", \"ui\": false, \"ui_craft\": \"none(no UI)\", \"exclusive\": []}"
# dest plan already happened; hashes bound to prior env. Rebind via blocked → validate-spec → plan.
run_cli update --run-dir "$runpr" --to blocked --resume-to validate-spec --reason "add practice refs" >/dev/null
run_cli update --run-dir "$runpr" --to validate-spec --reason "rebind refs" >/dev/null
write_spec "$runpr"
write_machine "$runpr" "{\"kind\": \"greenfield\", \"augment\": false, \"references\": [{\"path\": \"$refpath\", \"why\": \"practice\"}], \"tools\": [], \"mcp\": [],
 \"mcp_considered\": \"none(x)\", \"handles\": [], \"initiation\": \"none\", \"ui\": false, \"ui_craft\": \"none(no UI)\", \"exclusive\": []}"
run_cli update --run-dir "$runpr" --to plan >/dev/null
install_dag "$runpr" linear.json
set +e
out_cite="$(run_cli update --run-dir "$runpr" --to implement 2>&1)"
rc_cite=$?
set -e
[[ "$rc_cite" -eq 2 ]] || fail "uncited reference dest implement want 2: $out_cite"
printf '%s\n' "$out_cite" | grep -qi 'reference' || fail "uncited reference message: $out_cite"
python3 - "$runpr/backchain/plan.json" "$refpath" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
ref = sys.argv[2]
d = json.loads(p.read_text())
for step in d["steps"]:
    step["prompt"] = (
        step["prompt"]
        + " cite "
        + ref
        + "\nTools:\nWatch with: none(x)\nUse: git\nDon't use: none\nAssume: test harness"
    )
p.write_text(json.dumps(d, indent=2) + "\n")
PY
run_cli update --run-dir "$runpr" --to implement >/dev/null
out_cited="$(run_cli next --run-dir "$runpr")"
printf '%s\n' "$out_cited" | grep -qF "$refpath" || fail "next did not reprint cited reference"
printf 'LAYER: empty prompt + reference citation OK\n'

# --- A27 scope: inject-step's discovered steps are exempt from citation ---
INJ_BIND='/goal
Do this activity until these conditions are met:
- bind exists

no citation needed for a discovered step'
out_inj_nocite="$(run_cli inject-step --run-dir "$runpr" --statement "ad hoc bind" --prompt "$INJ_BIND" --produces "bind exists" --before S2)"
printf '%s\n' "$out_inj_nocite" | grep -q 'injected S' || fail "inject without citation should succeed: $out_inj_nocite"
python3 - "$runpr" "$INJ_BIND" <<'PY'
import json, sys
from pathlib import Path
run = Path(sys.argv[1])
want = sys.argv[2]
dag = json.loads((run / "backchain" / "plan.json").read_text())
new = [s for s in dag["steps"] if s["origin"] == "discovered"]
assert new, "expected a discovered step"
assert all(s["prompt"] == want for s in new), new
PY
printf 'LAYER: inject-step exempt from reference citation OK\n'
complete_ok "$runpr" S1
out_inj_env="$(run_cli next --run-dir "$runpr")"
printf '%s\n' "$out_inj_env" | grep -q 'ad hoc bind' || fail "discovered step not running: $out_inj_env"
printf '%s\n' "$out_inj_env" | grep -q 'mcp-considered: none(x)' \
  || fail "injected-step packet missing frozen envelope: $out_inj_env"
printf '%s\n' "$out_inj_env" | grep -q 'Implement git (paste into /goal with Frozen' \
  || fail "injected-step packet missing Implement git: $out_inj_env"
printf '%s\n' "$out_inj_env" | python3 -c '
import sys
text = sys.stdin.read()
i = text.find("Frozen session environment")
j = text.find("Implement git (paste into /goal with Frozen")
u = text.find("Goal until (this stored prompt is /goal A")
k = text.find("no citation needed for a discovered step")
imp = text.find("Improve (paste as /goal B after produces is true")
assert i != -1 and j != -1 and u != -1 and k != -1 and imp != -1, (i, j, u, k, imp)
assert i < j < u < k < imp, (i, j, u, k, imp)
' || fail "inject envelope not Frozen, Implement git, Goal until, discovered, Improve"
printf 'LAYER: inject-step envelope reprint OK\n'

# --- A16/A18/A22 inject-step ---
runinj="$tmpdir/inject/.shiploop"
repoinj="$tmpdir/inject/repo"
advance_to_plan "$runinj" "$repoinj" "$planf"
install_dag "$runinj" linear.json
run_cli update --run-dir "$runinj" --to implement >/dev/null
run_cli next --run-dir "$runinj" >/dev/null
set +e
out_ib="$(run_cli inject-step --run-dir "$runinj" --statement "mid" --prompt $'/goal\nDo this activity until these conditions are met:\n- mid exists' --produces "mid exists" --before S1 2>&1)"
rc_ib=$?
set -e
[[ "$rc_ib" -eq 2 ]] || fail "inject --before running want 2: $out_ib"
set +e
out_ip="$(run_cli inject-step --run-dir "$runinj" --statement "mid" --prompt "" --produces "mid exists" --before S2 2>&1)"
rc_ip=$?
set -e
[[ "$rc_ip" -eq 2 ]] || fail "inject empty --prompt want 2: $out_ip"
printf '%s\n' '{"done_sentence":"stale","plan_sha256":"deadbeef"}' >"$runinj/plan.json"
out_iok="$(run_cli inject-step --run-dir "$runinj" --statement "mid bind" --prompt $'/goal\nDo this activity until these conditions are met:\n- mid exists' --produces "mid exists" --before S2 --id S3)"
printf '%s\n' "$out_iok" | grep -q 'injected S3' || fail "inject add: $out_iok"
python3 - "$runinj" <<'PY'
import json, hashlib, sys
from pathlib import Path
run = Path(sys.argv[1])
dag = json.loads((run / "backchain" / "plan.json").read_text())
by_id = {s["id"]: s for s in dag["steps"]}
assert by_id["S3"]["origin"] == "discovered", by_id["S3"]
assert by_id["S3"]["prompt"] == (
    "/goal\nDo this activity until these conditions are met:\n- mid exists"
)
assert any(i.get("from") == "S3" and i.get("need") == "mid exists" for i in by_id["S2"]["inputs"])
state = json.loads((run / "state.json").read_text())
assert state["phase"] == "implement", state["phase"]
digest = hashlib.sha256((run / "backchain" / "plan.json").read_bytes()).hexdigest()
assert state["plan_sha256"] == digest
wrapper = json.loads((run / "plan.json").read_text())
assert wrapper.get("plan_sha256") == "deadbeef", wrapper
assert wrapper.get("done_sentence") == "stale", wrapper
for rec_path in sorted((run / "steps").glob("*.json")):
    rec = json.loads(rec_path.read_text())
    if rec.get("plan_sha256"):
        assert rec["plan_sha256"] == digest, rec_path
s1 = json.loads((run / "steps" / "S1.json").read_text())
assert s1.get("status") == "running", s1
PY
[[ ! -f "$runinj/implement.json" ]] || fail "inject-step wrote implement.json"
# hand-edit DAG then inject must refuse
python3 - "$runinj/backchain/plan.json" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
d = json.loads(p.read_text())
d["steps"][0]["statement"] = "hand-edited"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
set +e
out_ih="$(run_cli inject-step --run-dir "$runinj" --statement "after edit" --prompt "/goal no" --produces "x" 2>&1)"
rc_ih=$?
set -e
[[ "$rc_ih" -eq 2 ]] || fail "inject after hand-edit want 2: $out_ih"
printf '%s\n' "$out_ih" | grep -qi 'hash' || fail "inject hash-drift message: $out_ih"

# restore DAG hash by re-reading from a fresh drained session
rundr="$tmpdir/inject-drain/.shiploop"
repodr="$tmpdir/inject-drain/repo"
advance_to_plan "$rundr" "$repodr" "$planf"
install_dag "$rundr" linear.json
run_cli update --run-dir "$rundr" --to implement >/dev/null
run_cli next --run-dir "$rundr" >/dev/null
complete_ok "$rundr" S1
run_cli next --run-dir "$rundr" >/dev/null
complete_ok "$rundr" S2
out_drained="$(run_cli next --run-dir "$rundr")"
printf '%s\n' "$out_drained" | grep -q 'drained — next residual' || fail "pre-inject not drained: $out_drained"
set +e
out_idone="$(run_cli inject-step --run-dir "$rundr" --statement "late" --prompt $'/goal\nDo this activity until these conditions are met:\n- late exists' --produces "late exists" --before S2 2>&1)"
rc_idone=$?
set -e
[[ "$rc_idone" -eq 2 ]] || fail "inject --before done want 2: $out_idone"
out_idrain="$(run_cli inject-step --run-dir "$rundr" --statement "late" --prompt $'/goal\nDo this activity until these conditions are met:\n- late exists' --produces "late exists" --id S9)"
printf '%s\n' "$out_idrain" | grep -q 'injected S9' || fail "inject on drained: $out_idrain"
out_after="$(run_cli next --run-dir "$rundr")"
printf '%s\n' "$out_after" | grep -Fq 'Do this activity until these conditions are met:' \
  || fail "drained inject did not reprint new prompt: $out_after"
printf '%s\n' "$out_after" | grep -Fq 'late exists' \
  || fail "drained inject Next missing produces: $out_after"
assert_absent "$out_after" 'drained — next residual' "session still drained after inject"
python3 - "$rundr" <<'PY'
import json, sys
from pathlib import Path
run = Path(sys.argv[1])
s1 = json.loads((run / "steps" / "S1.json").read_text())
s2 = json.loads((run / "steps" / "S2.json").read_text())
assert s1.get("status") == "complete", s1
assert s2.get("status") == "complete", s2
state = json.loads((run / "state.json").read_text())
assert state["phase"] == "implement", state["phase"]
PY
printf 'LAYER: inject-step add/refuse/drained OK\n'

# --- dest plan exclusive + dest implement parsed Don't use ---
runpb="$tmpdir/exclusive/.shiploop"
repopb="$tmpdir/exclusive/repo"
fresh_vs "$runpb" "$repopb"
write_machine "$runpb" '{"kind": "greenfield", "augment": false, "references": [], "tools": ["git"], "mcp": ["writer-mcp"],
 "mcp_considered": "none(x)", "handles": [], "initiation": "none", "ui": false, "ui_craft": "none(no UI)",
 "exclusive": []}'
run_cli update --run-dir "$runpb" --to plan >/dev/null
printf 'LAYER: dest-plan exclusive [] with mcp nonempty OK\n'

runpboptional="$tmpdir/exclusive-optional/.shiploop"
repopboptional="$tmpdir/exclusive-optional/repo"
fresh_vs "$runpboptional" "$repopboptional"
write_machine "$runpboptional" "{\"kind\": \"greenfield\", \"augment\": false, \"references\": [{\"path\": \"$fix/existing-app/README.md\", \"why\": \"routing source\"}], \"tools\": [], \"mcp\": [],
 \"mcp_considered\": \"none(x)\", \"handles\": [], \"initiation\": \"none\", \"ui\": false, \"ui_craft\": \"none(no UI)\", \"exclusive\": [],
 \"layout\": {\"reserved\": [], \"product\": [\"app/\"]},
 \"routing\": {\"user_entrypoint\": \"none\", \"reserved_routes\": [\"none\"], \"confirmation\": \"none\", \"source\": \"$fix/existing-app/README.md\"}}"
set +e
out_pboptional="$(run_cli update --run-dir "$runpboptional" --to plan 2>&1)"
rc_pboptional=$?
set -e
[[ "$rc_pboptional" -eq 2 ]] || fail "optional layout present but malformed want 2: $out_pboptional"
printf '%s\n' "$out_pboptional" | grep -qi 'layout' \
  || fail "optional layout malformed message: $out_pboptional"
printf 'LAYER: optional layout/routing shape-check OK\n'

run_cli update --run-dir "$runpb" --to blocked --resume-to validate-spec --reason "rebind exclusive rows" >/dev/null
run_cli update --run-dir "$runpb" --to validate-spec --reason "rebind" >/dev/null
write_spec "$runpb"
write_machine "$runpb" '{"kind": "greenfield", "augment": false, "references": [], "tools": ["git", "alt-cli"], "mcp": ["writer-mcp"],
 "mcp_considered": "none(x)", "handles": [], "initiation": "none", "ui": false, "ui_craft": "none(no UI)",
 "exclusive": [{"artifact": "hosted project", "use": "writer-mcp", "dont_use": ["alt-cli"]}]}'
set +e
out_pbmiss="$(run_cli update --run-dir "$runpb" --to plan 2>&1)"
rc_pbmiss=$?
set -e
[[ "$rc_pbmiss" -eq 2 ]] || fail "exclusive nonempty missing references want 2: $out_pbmiss"
printf '%s\n' "$out_pbmiss" | grep -qi 'references' || fail "missing references message: $out_pbmiss"
write_machine "$runpb" '{"kind": "greenfield", "augment": false, "references": [{"path": "x", "why": "y"}], "tools": ["git", "writer-a", "writer-b"], "mcp": [],
 "mcp_considered": "none(x)", "handles": [], "initiation": "none", "ui": false, "ui_craft": "none(no UI)",
 "exclusive": [{"artifact": "a", "use": "writer-a", "dont_use": ["writer-b"]}, {"artifact": "b", "use": "writer-b", "dont_use": ["writer-a"]}]}'
set +e
out_opp="$(run_cli update --run-dir "$runpb" --to plan 2>&1)"
rc_opp=$?
set -e
[[ "$rc_opp" -eq 2 ]] || fail "opposing writers dest plan want 2: $out_opp"
printf '%s\n' "$out_opp" | grep -qi 'opposing writers' || fail "opposing writers message: $out_opp"
write_machine "$runpb" '{"kind": "greenfield", "augment": false, "references": [{"path": "x", "why": "y"}], "tools": ["git", "writer-a", "writer-b"], "mcp": [],
 "mcp_considered": "none(x)", "handles": [], "initiation": "none", "ui": false, "ui_craft": "none(no UI)",
 "exclusive": [{"artifact": "a", "use": "writer-a", "dont_use": []}, {"artifact": "b", "use": "writer-b", "dont_use": []}]}'
set +e
out_single="$(run_cli update --run-dir "$runpb" --to plan 2>&1)"
rc_single=$?
set -e
[[ "$rc_single" -eq 2 ]] || fail "disagreeing exclusive use dest plan want 2: $out_single"
printf '%s\n' "$out_single" | grep -qi 'single exclusive writer' \
  || fail "single exclusive writer message: $out_single"
write_machine "$runpb" '{"kind": "greenfield", "augment": false, "references": [{"path": "x", "why": "y"}], "tools": ["git", "alt-cli"], "mcp": ["writer-mcp"],
 "mcp_considered": "none(x)", "handles": [], "initiation": "none", "ui": false, "ui_craft": "none(no UI)",
 "exclusive": [{"artifact": "hosted project", "use": "writer-mcp", "dont_use": ["alt;cli"]}]}'
set +e
out_semi="$(run_cli update --run-dir "$runpb" --to plan 2>&1)"
rc_semi=$?
set -e
[[ "$rc_semi" -eq 2 ]] || fail "semicolon dont_use token want 2: $out_semi"
refpath="$fix/existing-app/README.md"
write_machine "$runpb" "{\"kind\": \"greenfield\", \"augment\": false, \"references\": [{\"path\": \"$refpath\", \"why\": \"practice\"}], \"tools\": [\"git\", \"alt-cli\"], \"mcp\": [\"writer-mcp\"],
 \"mcp_considered\": \"none(x)\", \"handles\": [], \"initiation\": \"none\", \"ui\": false, \"ui_craft\": \"none(no UI)\",
 \"exclusive\": [{\"artifact\": \"hosted project\", \"use\": \"writer-mcp\", \"dont_use\": [\"alt-cli\"]}],
 \"layout\": {\"reserved\": [\"none\"], \"product\": [\"none\"]},
 \"routing\": {\"user_entrypoint\": \"none\", \"reserved_routes\": [\"none\"], \"confirmation\": \"none\", \"source\": \"$refpath\"}}"
run_cli update --run-dir "$runpb" --to plan >/dev/null
printf 'LAYER: dest-plan exclusive + references OK\n'

write_seed_dag "$runpb" "${UNTIL_PREFIX}cite ${refpath}
Tools:
Watch with: none(x)
Use: alt-cli
Don't use: none
Assume: test harness"
set +e
out_pbdu="$(run_cli update --run-dir "$runpb" --to implement 2>&1)"
rc_pbdu=$?
set -e
[[ "$rc_pbdu" -eq 2 ]] || fail "token only under Use: want 2: $out_pbdu"
printf '%s\n' "$out_pbdu" | grep -qi 'dont_use' || fail "dont_use message: $out_pbdu"
write_seed_dag "$runpb" "${UNTIL_PREFIX}cite ${refpath}
Tools:
Watch with: none(x)
Use: git
Don't use: aws-vault
Assume: test harness"
set +e
out_coll="$(run_cli update --run-dir "$runpb" --to implement 2>&1)"
rc_coll=$?
set -e
[[ "$rc_coll" -eq 2 ]] || fail "wrong Don't use entry want 2: $out_coll"
write_seed_dag "$runpb" "${UNTIL_PREFIX}cite ${refpath}
Tools:
Watch with: none(x)
Use: git
Don't use: alt-cli
Assume: test harness"
set +e
out_usegit="$(run_cli update --run-dir "$runpb" --to implement 2>&1)"
rc_usegit=$?
set -e
[[ "$rc_usegit" -eq 2 ]] || fail "Use: git vs exclusive writer-mcp want 2: $out_usegit"
printf '%s\n' "$out_usegit" | grep -q 'writer-mcp' || fail "designated writer message: $out_usegit"
write_seed_dag "$runpb" "${UNTIL_PREFIX}cite ${refpath}
Tools:
Watch with: none(x)
Use: alt-cli
Don't use: alt-cli
Assume: test harness"
set +e
out_ov="$(run_cli update --run-dir "$runpb" --to implement 2>&1)"
rc_ov=$?
set -e
[[ "$rc_ov" -eq 2 ]] || fail "Use:/Don't use overlap want 2: $out_ov"
printf '%s\n' "$out_ov" | grep -qi 'overlap' || fail "overlap message: $out_ov"
write_seed_dag "$runpb" "${UNTIL_PREFIX}cite ${refpath}
Tools:
Watch with: none(x)
Don't use: alt-cli
Assume: test harness"
set +e
out_nouse="$(run_cli update --run-dir "$runpb" --to implement 2>&1)"
rc_nouse=$?
set -e
[[ "$rc_nouse" -eq 2 ]] || fail "missing Use: line want 2: $out_nouse"
printf '%s\n' "$out_nouse" | grep -q 'Use:' || fail "missing Use: message: $out_nouse"
SEED_OK="${UNTIL_PREFIX}cite ${refpath}
Tools:
Watch with: none(x)
Use: writer-mcp
Don't use: alt-cli
Assume: test harness"
DISC_PREFIX='/goal
Do this activity until these conditions are met:
- mid exists
'
write_seed_and_discovered_dag "$runpb" "$SEED_OK" "${DISC_PREFIX}Tools:
Watch with: none(x)
Use: alt-cli
Don't use: alt-cli"
set +e
out_dov="$(run_cli update --run-dir "$runpb" --to implement 2>&1)"
rc_dov=$?
set -e
[[ "$rc_dov" -eq 2 ]] || fail "discovered Use:/Don't use overlap want 2: $out_dov"
printf '%s\n' "$out_dov" | grep -qi 'overlap' || fail "discovered overlap message: $out_dov"
write_seed_and_discovered_dag "$runpb" "$SEED_OK" "${DISC_PREFIX}Tools:
Watch with: none(x)
Use: git
Don't use: alt-cli"
set +e
out_dgit="$(run_cli update --run-dir "$runpb" --to implement 2>&1)"
rc_dgit=$?
set -e
[[ "$rc_dgit" -eq 2 ]] || fail "discovered Use: git vs writer-mcp want 2: $out_dgit"
printf '%s\n' "$out_dgit" | grep -q 'writer-mcp' || fail "discovered designated writer message: $out_dgit"
write_seed_and_discovered_dag "$runpb" "$SEED_OK" "${DISC_PREFIX}Tools:
Watch with: none(x)
Don't use: alt-cli"
set +e
out_dnu="$(run_cli update --run-dir "$runpb" --to implement 2>&1)"
rc_dnu=$?
set -e
[[ "$rc_dnu" -eq 2 ]] || fail "discovered missing Use: want 2: $out_dnu"
printf '%s\n' "$out_dnu" | grep -q 'Use:' || fail "discovered missing Use: message: $out_dnu"
write_seed_and_discovered_dag "$runpb" "$SEED_OK" "${DISC_PREFIX}Tools:
Watch with: none(x)
Use: writer-mcp
Don't use: alt-cli"
run_cli update --run-dir "$runpb" --to implement >/dev/null
out_pbfz="$(run_cli next --run-dir "$runpb")"
printf '%s\n' "$out_pbfz" | grep -q 'Exclusive: hosted project — use writer-mcp; don'\''t use alt-cli' \
  || fail "Frozen missing Exclusive row: $out_pbfz"
printf '%s\n' "$out_pbfz" | grep -Fq "$blocked_line" \
  || fail "Frozen missing dest-blocked sentence: $out_pbfz"
assert_absent "$out_pbfz" 'Playbook:' "Frozen still prints Playbook:"
assert_absent "$out_pbfz" 'do not implement the product through MCP' \
  "Frozen still forbids MCP writes"
printf 'LAYER: dest-implement parsed Don'\''t use + Frozen Exclusive OK\n'

# --- P0 destination layout/routing + seed Don't write gate ---
runlr="$tmpdir/layout-routing/.shiploop"
repolr="$tmpdir/layout-routing/repo"
fresh_vs "$runlr" "$repolr"
write_machine "$runlr" "{\"kind\": \"greenfield\", \"augment\": false, \"references\": [{\"path\": \"$refpath\", \"why\": \"writer contract\"}], \"tools\": [\"git\", \"alt-cli\"], \"mcp\": [\"writer-mcp\"],
 \"mcp_considered\": \"none(x)\", \"handles\": [], \"initiation\": \"none\", \"ui\": false, \"ui_craft\": \"none(no UI)\",
 \"exclusive\": [{\"artifact\": \"dest artifact\", \"use\": \"writer-mcp\", \"dont_use\": [\"alt-cli\"]}]}"
set +e
out_lr_missing="$(run_cli update --run-dir "$runlr" --to plan 2>&1)"
rc_lr_missing=$?
set -e
[[ "$rc_lr_missing" -eq 2 ]] || fail "exclusive layout/routing missing want 2: $out_lr_missing"
printf '%s\n' "$out_lr_missing" | grep -qiE 'layout|routing' \
  || fail "exclusive layout/routing missing message: $out_lr_missing"

write_machine "$runlr" "{\"kind\": \"greenfield\", \"augment\": false, \"references\": [{\"path\": \"$refpath\", \"why\": \"writer contract\"}], \"tools\": [\"git\", \"alt-cli\"], \"mcp\": [\"writer-mcp\"],
 \"mcp_considered\": \"none(x)\", \"handles\": [], \"initiation\": \"none\", \"ui\": false, \"ui_craft\": \"none(no UI)\",
 \"exclusive\": [{\"artifact\": \"dest artifact\", \"use\": \"writer-mcp\", \"dont_use\": [\"alt-cli\"]}],
 \"layout\": {\"reserved\": [], \"product\": [\"app/\"]},
 \"routing\": {\"user_entrypoint\": \"/app\", \"reserved_routes\": [\"/\"], \"confirmation\": \"GET /app\", \"source\": \"$refpath\"}}"
set +e
out_lr_shape="$(run_cli update --run-dir "$runlr" --to plan 2>&1)"
rc_lr_shape=$?
set -e
[[ "$rc_lr_shape" -eq 2 ]] || fail "empty reserved layout want 2: $out_lr_shape"
printf '%s\n' "$out_lr_shape" | grep -qi 'layout' \
  || fail "empty reserved layout message: $out_lr_shape"

write_machine "$runlr" "{\"kind\": \"greenfield\", \"augment\": false, \"references\": [{\"path\": \"$refpath\", \"why\": \"writer contract\"}], \"tools\": [\"git\", \"alt-cli\"], \"mcp\": [\"writer-mcp\"],
 \"mcp_considered\": \"none(x)\", \"handles\": [], \"initiation\": \"none\", \"ui\": false, \"ui_craft\": \"none(no UI)\",
 \"exclusive\": [{\"artifact\": \"dest artifact\", \"use\": \"writer-mcp\", \"dont_use\": [\"alt-cli\"]}],
 \"layout\": {\"reserved\": [\"runtime/\"], \"product\": [\"app/\"]},
 \"routing\": {\"user_entrypoint\": \"/app\", \"reserved_routes\": [\"/\"], \"confirmation\": \"GET /app\", \"source\": \"not-a-reference\"}}"
set +e
out_lr_source="$(run_cli update --run-dir "$runlr" --to plan 2>&1)"
rc_lr_source=$?
set -e
[[ "$rc_lr_source" -eq 2 ]] || fail "routing source outside references want 2: $out_lr_source"
printf '%s\n' "$out_lr_source" | grep -q 'routing.source' \
  || fail "routing source message: $out_lr_source"

write_machine "$runlr" "{\"kind\": \"greenfield\", \"augment\": false, \"references\": [{\"path\": \"$refpath\", \"why\": \"writer contract\"}], \"tools\": [\"git\", \"alt-cli\"], \"mcp\": [\"writer-mcp\"],
 \"mcp_considered\": \"none(x)\", \"handles\": [], \"initiation\": \"none\", \"ui\": false, \"ui_craft\": \"none(no UI)\",
 \"exclusive\": [{\"artifact\": \"dest artifact\", \"use\": \"writer-mcp\", \"dont_use\": [\"alt-cli\"]}],
 \"layout\": {\"reserved\": [\"runtime/\"], \"product\": [\"app/\"]},
 \"routing\": {\"user_entrypoint\": \"/app\", \"reserved_routes\": [\"/\"], \"confirmation\": \"GET /app\", \"source\": \"$refpath\"}}"
run_cli update --run-dir "$runlr" --to plan >/dev/null
printf 'LAYER: destination layout/routing frozen OK\n'

write_seed_dag "$runlr" "${UNTIL_PREFIX}cite ${refpath}
Tools:
Watch with: none(x)
Use: writer-mcp
Don't use: alt-cli
Assume: test harness"
set +e
out_lr_dontwrite="$(run_cli update --run-dir "$runlr" --to implement 2>&1)"
rc_lr_dontwrite=$?
set -e
[[ "$rc_lr_dontwrite" -eq 2 ]] || fail "missing Don't write want 2: $out_lr_dontwrite"
printf '%s\n' "$out_lr_dontwrite" | grep -Fq "Don't write" \
  || fail "missing Don't write message: $out_lr_dontwrite"

write_seed_dag "$runlr" "${UNTIL_PREFIX}cite ${refpath}
Tools:
Watch with: none(x)
Use: writer-mcp
Don't use: alt-cli
Don't write: runtime/
Assume: test harness"
run_cli update --run-dir "$runlr" --to implement >/dev/null
out_lr_frozen="$(run_cli next --run-dir "$runlr")"
for needle in 'Reserved: runtime/' 'Product: app/' 'Entrypoint: /app' \
  'Don'\''t write product into Reserved.'; do
  printf '%s\n' "$out_lr_frozen" | grep -Fq "$needle" \
    || fail "Frozen missing $needle: $out_lr_frozen"
done
printf 'LAYER: seed Don'\''t write + Frozen layout/routing OK\n'

python3 - "$cli" "$tmpdir/f1-env" <<'PY' || fail "F1 load_environment blanks on missing exclusive"
import importlib.machinery, importlib.util, io, sys
from pathlib import Path
cli = Path(sys.argv[1])
loader = importlib.machinery.SourceFileLoader("shiploop", str(cli))
spec = importlib.util.spec_from_loader("shiploop", loader)
mod = importlib.util.module_from_spec(spec)
loader.exec_module(mod)
run = Path(sys.argv[2])
run.mkdir(parents=True)
(run / "environment.md").write_text(
    "brief\n\n## machine\n```json\n"
    '{"kind": "greenfield", "augment": false, "references": [], "tools": [],'
    ' "mcp": ["writer-mcp"], "mcp_considered": "none(x)", "handles": [],'
    ' "initiation": "none", "ui": false, "ui_craft": "none(no UI)"}'
    "\n```\n"
)
env, gaps = mod.load_environment(run)
assert not gaps, gaps
assert env.get("exclusive") is None
buf = io.StringIO()
old = sys.stdout
sys.stdout = buf
mod.print_frozen_session_env(run)
sys.stdout = old
out = buf.getvalue()
assert "tools:" in out and "mcp: writer-mcp" in out, out
assert "Exclusive: (not recorded in this legacy run)" in out, out
assert "Playbook:" not in out, out
PY
printf 'LAYER: F1 missing exclusive does not blank Frozen OK\n'

bash "$root/test/shiploop-walk-journal.test.sh" \
  || fail "shiploop-walk-journal.test.sh"

printf 'shiploop.test.sh: PASS\n'
