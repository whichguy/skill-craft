#!/usr/bin/env bash
# Hermetic shiploop session-harness tests (no network).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cli="$root/skills/shiploop/scripts/shiploop"
fix="$root/test/fixtures/shiploop"
export SHIPLOOP_BACKCHAIN_ROOT="$fix/backchain-leaf"

fail() {
  printf 'shiploop.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

[[ -f "$root/skills/shiploop/SKILL.md" ]] || fail "missing SKILL.md"
[[ ! -d "$root/skills/shiploop/prompts" ]] || fail "prompts/ must not exist"
grep -q 'kind: script-backed' "$root/skills/shiploop/SKILL.md" || fail "frontmatter kind"
grep -q 'name: shiploop' "$root/skills/shiploop/SKILL.md" || fail "frontmatter name"
grep -q 'shiploop — session harness (not DevLoop)' "$root/skills/shiploop/SKILL.md" || fail "banner"
if grep -q 'DEFINE → PROVE → BUILD' "$root/skills/shiploop/SKILL.md"; then
  fail "SKILL.md must not own DEFINE/PROVE/BUILD"
fi
grep -qi 'not DevLoop' "$root/skills/shiploop/SKILL.md" || fail "must demote DevLoop"
if grep -E 'shiploop capture|devloop-run' "$root/skills/shiploop/references/activities/implement.md"; then
  fail "implement activity still captures /devloop"
fi
[[ -f "$root/skills/shiploop/references/host-matrix.md" ]] || fail "missing host-matrix.md"
[[ -f "$root/skills/shiploop/references/ledger-contract.md" ]] || fail "missing ledger-contract.md"
grep -q 'copied, not imported' "$root/skills/shiploop/references/ledger-contract.md" || fail "ledger-contract copy note"
grep -q 'VALIDATE_SPEC_PATH' "$root/skills/shiploop/references/activities/validate-spec.md" \
  && fail "validate-spec.md must not mention VALIDATE_SPEC_PATH"
for tok in prep "intermediate deploy" cleanup; do
  grep -q "$tok" "$root/skills/shiploop/references/activities/plan.md" || fail "plan.md missing $tok"
done
chmod +x "$cli"

le_docs="$root/docs/LOOP-ENGINEERING.md"
le_skill="$root/skills/devloop/references/loop-engineering.md"
diff -q "$le_docs" "$le_skill" >/dev/null || fail "LOOP-ENGINEERING copies drifted"
grep -q 'ShipLoop session' "$le_docs" || fail "LOOP-ENGINEERING missing ShipLoop session track"
grep -q '/shiploop next' "$le_docs" || fail "LOOP-ENGINEERING missing /shiploop next"
grep -q '/shiploop complete' "$le_docs" || fail "LOOP-ENGINEERING missing /shiploop complete"
grep -q 'research practices' "$le_docs" || fail "LOOP-ENGINEERING missing practices research"
grep -q 'recap.html' "$le_docs" || fail "LOOP-ENGINEERING missing recap.html"
grep -q 'Best-practice research' "$root/skills/shiploop/references/activities/validate-spec.md" \
  || fail "validate-spec.md missing practices job"
grep -q 'best-practice' "$root/skills/shiploop/references/survey.md" \
  || fail "survey.md missing practices research"
grep -q 'practice references' "$root/skills/shiploop/references/activities/plan.md" \
  || fail "plan.md missing practice references in step prompts"
grep -q 'researches applicable practices' "$root/skills/shiploop/README.md" \
  || fail "README missing practices research"
grep -q 'recap.html' "$root/skills/shiploop/README.md" \
  || fail "README missing recap.html"
grep -q '^VERSION = "0.8.0"$' "$cli" || fail "script VERSION is not 0.8.0"
grep -q '^version: 0.8.0$' "$root/skills/shiploop/SKILL.md" || fail "SKILL.md version is not 0.8.0"
grep -q 'init --force --prompt' "$root/skills/shiploop/SKILL.md" \
  || fail "SKILL.md missing three-branch init --force --prompt"
grep -q 'init --force --prompt' "$root/skills/shiploop/README.md" \
  || fail "README missing Session B init --force --prompt"
if grep -E 'ENV_JSON|SPEC_JSON|IMPLEMENT_JSON|goal_line' "$cli" \
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
grep -Eiq 'Never.+invoke' "$root/skills/shiploop/SKILL.md" || fail "SKILL.md missing Never invoke"
[[ -f "$root/skills/shiploop/README.md" ]] || fail "missing skill README"
[[ -f "$root/skills/shiploop/commands/shiploop.md" ]] || fail "missing commands/shiploop.md"
[[ -f "$root/skills/shiploop/commands/shiploop-next.md" ]] || fail "missing commands/shiploop-next.md"
[[ -f "$root/skills/shiploop/commands/shiploop-complete.md" ]] || fail "missing commands/shiploop-complete.md"
[[ -f "$root/skills/shiploop/scripts/shiploop-next" ]] || fail "missing scripts/shiploop-next"
[[ -f "$root/skills/shiploop/scripts/shiploop-complete" ]] || fail "missing scripts/shiploop-complete"
[[ ! -d "$root/skills/steer" ]] || fail "old steer leaf still present"
[[ ! -d "$root/skills/steer-next" ]] || fail "steer-next sibling still present"
[[ ! -d "$root/skills/steer-complete-next" ]] || fail "steer-complete-next sibling still present"

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/shiploop-test.XXXXXX")"
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

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
After /shiploop complete, the host merges the kept branch into session HEAD; the next packet names the next worktree.'

assert_host_flag() {
  local haystack="$1" label="$2"
  while IFS= read -r line; do
    printf '%s\n' "$haystack" | grep -qF "$line" || fail "$label missing host flag line: $line"
  done <<<"$HOST_FLAG_LINES"
}

assert_host_flag "$(cat "$root/skills/shiploop/SKILL.md")" "SKILL.md"
assert_host_flag "$(cat "$root/skills/shiploop/references/turn-packet.md")" "turn-packet.md"

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

assert_absent() {
  local out="$1" pat="$2" msg="$3"
  if printf '%s\n' "$out" | grep -q -- "$pat"; then
    fail "$msg"
  fi
}

run_cli() { python3 "$cli" "$@"; }

commit_step_work() {
  local run="$1" sid="$2"
  local wt
  wt="$(python3 -c "import json; print(json.load(open('$run/steps/$sid.json'))['worktree'])")"
  [[ -n "$wt" && -d "$wt" ]] || fail "commit_step_work: missing worktree for $sid"
  printf '%s\n' "step $sid" >"$wt/${sid}.txt"
  git -C "$wt" add "${sid}.txt"
  git -C "$wt" commit -m "step $sid" >/dev/null
}

merge_step_branch() {
  local run="$1" sid="$2"
  local repo branch
  repo="$(python3 -c "import json; print(json.load(open('$run/state.json'))['repo_root'])")"
  branch="$(python3 -c "import json; print(json.load(open('$run/steps/$sid.json')).get('branch') or '')")"
  [[ -n "$repo" && -n "$branch" ]] || fail "merge_step_branch: missing repo/branch for $sid"
  git -C "$repo" merge --no-ff --no-edit "$branch" >/dev/null
}

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
 "handles": [], "initiation": "none", "ui": false, "ui_craft": "none(no UI in scope)"}
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

write_wrapper() {
  local run="$1"
  printf '%s\n' "{\"done_sentence\":\"$DS\",\"backchain\":\"$run/backchain/plan.json\"}" >"$run/plan.json"
  printf 'done_sentence: %s\n' "$DS" >"$run/plan.md"
}

init_git_repo() {
  local repo="$1"
  mkdir -p "$repo"
  if git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    return 0
  fi
  git -C "$repo" init >/dev/null
  git -C "$repo" config user.email "shiploop-test@example.com"
  git -C "$repo" config user.name "ShipLoop Test"
  git -C "$repo" config commit.gpgsign false
  printf 'seed\n' >"$repo/README"
  git -C "$repo" add README
  git -C "$repo" commit -m seed >/dev/null
}

install_dag() {
  local run="$1" fixture="$2"
  mkdir -p "$run/backchain"
  cp "$fix/$fixture" "$run/backchain/plan.json"
  write_wrapper "$run"
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

# --- devloop implementer refused; host default ---
set +e
out_dl="$(run_cli init --implementer devloop --run-dir "$tmpdir/nope" 2>&1)"
rc_dl=$?
set -e
[[ "$rc_dl" -eq 2 ]] || fail "devloop implementer want 2 got $rc_dl: $out_dl"
printf 'LAYER: devloop implementer refused OK\n'

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
printf '%s\n' "$out_init" | grep -q 'shiploop — session harness (not DevLoop)' || fail "init missing harness banner"
printf '%s\n' "$out_init" | grep -qF 'Reference only — not the next action.' || fail "look here missing reference-only line"
printf '%s\n' "$out_init" | grep -qF 'Use this prompt as much as possible.' || fail "next prompt missing banner line"
assert_absent "$out_init" 'shiploop update --run-dir' "init When done leaked update argv"
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
printf '%s\n' "$out_vs" | grep -q 'not written yet' || fail "spec not written yet pointer"
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
printf 'LAYER: intake->validate-spec OK\n'

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
run_cli update --run-dir "$run" --to blocked --reason "what is the oracle?" --resume-to validate-spec >/dev/null
out_blk="$(run_cli next --run-dir "$run")"
printf '%s\n' "$out_blk" | grep -q 'blocked: current' || fail "blocked current: $out_blk"
assert_absent "$out_blk" 'more spec prose that must not be dumped later' "reminder dumped spec body"
set +e
out_jumpvs="$(run_cli update --run-dir "$run" --to implement 2>&1)"
rc_jumpvs=$?
set -e
[[ "$rc_jumpvs" -eq 2 ]] || fail "blocked validate-spec resume jumped to implement: $out_jumpvs"
run_cli update --run-dir "$run" --to validate-spec --reason "user answered" >/dev/null
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
 "initiation": "needed", "ui": false, "ui_craft": "none(no UI in scope)"}
```
MD
run_cli update --run-dir "$run" --to plan >/dev/null
printf 'LAYER: handle resolve gates OK\n'

# --- happy spec + thin plan cannot implement ---
out_plan="$(run_cli next --run-dir "$run")"
assert_headings "$out_plan"
assert_absent "$out_plan" '/goal ' "plan packet emitted implement /goal"
printf '%s\n' "{\"done_sentence\":\"$DS\"}" >"$run/plan.json"
printf 'done_sentence: %s\n\nsteps: write file\n' "$DS" >"$run/plan.md"
set +e
out_thin="$(run_cli update --run-dir "$run" --to implement 2>&1)"
rc_thin=$?
set -e
[[ "$rc_thin" -eq 2 ]] || fail "thin plan want 2: $out_thin"
printf 'LAYER: thin plan reject OK\n'

# --- linear DAG implement + /goal + frozen ---
install_dag "$run" linear.json
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
printf '%s\n' "$out_imp" | grep -q 'Finish S1: write the file' || fail "labeled Finish S1 missing"
printf '%s\n' "$out_imp" | grep -q 'S1 worktree — cwd here — write the file' || fail "look here missing S1 statement"
printf '%s\n' "$out_imp" | grep -qx 'Diagnosis' || fail "implement missing Diagnosis"
printf '%s\n' "$out_imp" | grep -q 'stand      implement — 0/2 steps done' || fail "implement stand"
printf '%s\n' "$out_imp" | grep -q 'serving frozen spec' || fail "implement stand missing spec insight"
printf '%s\n' "$out_imp" | grep -A20 '^Diagnosis$' | grep -q 'S1  write the file' || fail "now missing S1"
printf '%s\n' "$out_imp" | grep -A20 '^Diagnosis$' | grep -q '(running)' || fail "now missing running"
printf '%s\n' "$out_imp" | grep -A20 '^Diagnosis$' | grep -q 'S2  confirm the file' || fail "pending missing S2"
printf '%s\n' "$out_imp" | grep -q 'invoke /shiploop complete' || fail "when done missing /shiploop complete"
assert_absent "$out_imp" 'complete-step --' "when done leaked complete-step argv"
assert_absent "$out_imp" '--id S1' "when done leaked --id S1"
printf '%s\n' "$out_imp" | grep -q 'commit on the worktree' || fail "when done missing commit"
printf '%s\n' "$out_imp" | grep -q 'merge --no-ff' || fail "when done missing host merge"
printf '%s\n' "$out_imp" | grep -qx '## Progress' || fail "implement missing Progress"
printf '%s\n' "$out_imp" | grep -Eq '^(Beginning|Continuing) step S1 of 2' \
  || fail "implement Progress missing S1 begin/continue"
printf '%s\n' "$out_imp" | grep -q 'Work in this worktree folder' || fail "implement Progress missing worktree"
printf '%s\n' "$out_imp" | grep -q 'Finish S1:' || fail "implement Progress missing finish S1"
printf '%s\n' "$out_imp" | grep -q 'Do not edit the session checkout' || fail "implement next missing checkout guard"
assert_host_flag "$out_imp" "implement packet"
flag_n="$(printf '%s\n' "$out_imp" | grep -cF 'HOST FLAG — extra folder (do not re-root):' || true)"
[[ "$flag_n" -ge 2 ]] || fail "implement packet should print HOST FLAG in Progress and Next envelope (got $flag_n)"
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
assert_absent "$out_dr" '/goal ' "drained implement still emitted /goal"
assert_absent "$out_dr" 'shiploop update --run-dir' "drained leaked update argv"
run_cli update --run-dir "$run" --to residual >/dev/null
printf 'LAYER: linear drain OK\n'

# --- capture fail-closed (no implement.json in 0.7; receipts are the SoT) ---
[[ ! -f "$run/implement.json" ]] || fail "shiploop must not write implement.json"
set +e
out_cap="$(run_cli capture --run-dir "$run" -- echo hi 2>&1)"
rc_cap=$?
set -e
[[ "$rc_cap" -eq 2 ]] || fail "capture want 2: $out_cap"
printf '%s\n' "$out_cap" | grep -qi 'not a host-session gate' || fail "capture message: $out_cap"
printf 'LAYER: capture fail-closed OK\n'

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

cat >"$repo/REVIEW_CONVERGE.md" <<MD
**Status:** complete
**Plan contract:** \`$planf\`
**Plan hash:** \`$bhash\`

### Round 2 —
review-converge: round 2 —
**Committed:** yes
MD
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
printf 'LAYER: dest done writes recap.html OK\n'
out_done="$(run_cli next --run-dir "$run")"
printf '%s\n' "$out_done" | grep -q 'stop — no update' || fail "done stop: $out_done"
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
cat >"$repo/REVIEW_CONVERGE.md" <<'MD'
**Status:** active
**Plan contract:** `/nope`
MD
write_recap "$run"
run_cli update --run-dir "$run" --to done >/dev/null
python3 - "$run" <<'PY'
import json, sys
from pathlib import Path
d = json.loads((Path(sys.argv[1]) / "state.json").read_text())
assert d["terminal"] == "waived", d
PY
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
printf '%s\n' "$out_tr" | grep -c '^/goal ' | grep -qx 2 || fail "want two /goal lines"
set +e
out_ss="$(run_cli start-step --run-dir "$run2" --id S1 2>&1)"
rc_ss=$?
set -e
[[ "$rc_ss" -eq 2 ]] || fail "double start want 2: $out_ss"
complete_ok "$run2" S1
out_tr2="$(run_cli next --run-dir "$run2")"
printf '%s\n' "$out_tr2" | grep -q 'In flight' || fail "S2 not labeled in-flight"
printf '%s\n' "$out_tr2" | grep -q 'S1: done' || fail "S1 should stay done"
printf '%s\n' "$out_tr2" | grep -c '^/goal ' | grep -qx 1 || fail "reprint should keep one /goal"
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
python3 "$cli" complete-step --run-dir "$run3" --id S1 >/tmp/shiploop-c1.out 2>&1 &
p1=$!
python3 "$cli" complete-step --run-dir "$run3" --id S2 >/tmp/shiploop-c2.out 2>&1 &
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
set +e
out_ef="$(run_cli init --force --run-dir "$runf" --bound-plan "$planf" --repo "$repof" 2>&1)"
rc_ef=$?
set -e
[[ "$rc_ef" -eq 2 ]] || fail "empty --force want 2: $out_ef"
[[ -f "$runf/recap.html" ]] || fail "empty --force wiped recap.html"
[[ -d "$repof/.worktrees/shiploop/$ridf/S1" ]] || fail "empty --force wiped worktree"
run_cli init --force --prompt "fresh" --run-dir "$runf" --bound-plan "$planf" --repo "$repof" >/dev/null
[[ ! -f "$runf/backchain/plan.json" ]] || fail "force left backchain"
[[ ! -f "$runf/recap.html" ]] || fail "force left recap.html"
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
write_wrapper "$runi"
set +e
out_inj="$(run_cli update --run-dir "$runi" --to implement 2>&1)"
rc_inj=$?
set -e
[[ "$rc_inj" -eq 2 ]] || fail "injection --to implement want 2: $out_inj"
printf '%s\n' "$out_inj" | grep -qi 'newline\|control\|devloop\|statement' || fail "injection message: $out_inj"
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
# wrapper step_ids are not SoT: stale list must not hide S2
runsot="$tmpdir/sot/.shiploop"
reposot="$tmpdir/sot/repo"
mkdir -p "$reposot"
advance_to_plan "$runsot" "$reposot" "$planf"
install_dag "$runsot" linear.json
run_cli update --run-dir "$runsot" --to implement >/dev/null
python3 - "$runsot/plan.json" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
d = json.loads(p.read_text())
d["step_ids"] = ["S1"]
p.write_text(json.dumps(d, indent=2) + "\n")
PY
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
    "prompt": "/goal from initial_state to result.txt exists via write the file",
    "produces": "result.txt exists",
    "origin": "seed",
    "inputs": [{"need": "repo exists", "from": None}],
  }],
  "parallel_groups": [],
  "unresolved": [],
}
(run / "backchain" / "plan.json").write_text(json.dumps(doc, indent=2) + "\n")
(run / "plan.json").write_text(json.dumps({"done_sentence": ds}) + "\n")
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
[[ "$rc_mp" -eq 2 ]] || fail "missing plan.json want 2: $out_mp"
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
printf '%s\n' "$out_wt" | grep -q 'merge that branch into the session checkout' \
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

# --- complete before merge is refused ---
runum="$tmpdir/unmerged/.shiploop"
repoum="$tmpdir/unmerged/repo"
advance_to_plan "$runum" "$repoum" "$planf"
install_dag "$runum" linear.json
run_cli update --run-dir "$runum" --to implement >/dev/null
run_cli next --run-dir "$runum" >/dev/null
commit_step_work "$runum" S1
set +e
out_um="$(run_cli complete-step --run-dir "$runum" --id S1 2>&1)"
rc_um=$?
set -e
[[ "$rc_um" -eq 2 ]] || fail "unmerged complete want 2: $out_um"
printf '%s\n' "$out_um" | grep -qi 'merge' || fail "unmerged message: $out_um"
[[ ! -f "$repoum/S1.txt" ]] || fail "unmerged complete wrote S1 into HEAD"
printf 'LAYER: unmerged complete refuse OK\n'

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
out_cwd="$(cd "$wt2s1" && run_cli complete)"
printf '%s\n' "$out_cwd" | grep -q 'completed S1' || fail "cwd worktree did not complete S1: $out_cwd"
python3 - "$run2r" <<'PY'
import json, sys
from pathlib import Path
rec = json.loads((Path(sys.argv[1]) / "steps" / "S1.json").read_text())
assert rec["status"] == "complete", rec
PY
printf 'LAYER: two-running inference OK\n'

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
merge_step_branch "$runw" S1
out_w4="$(run_cli complete --run-dir "$runw")"
printf '%s\n' "$out_w4" | grep -q 'completed S1' || fail "closer walk S1: $out_w4"
printf '%s\n' "$out_w4" | grep -q 'S2: running' || fail "closer walk did not claim S2"
printf '%s\n' "$out_w4" | grep -q 'stand      implement — 1/2 steps done' || fail "closer walk mid stand"
wt_s2="$(python3 -c "import json; print(json.load(open('$runw/steps/S2.json'))['worktree'])")"
[[ -f "$wt_s2/S1.txt" ]] || fail "S2 worktree missing merged S1.txt"
commit_step_work "$runw" S2
merge_step_branch "$runw" S2
out_w5="$(run_cli complete --run-dir "$runw")"
printf '%s\n' "$out_w5" | grep -q 'completed S2' || fail "closer walk S2: $out_w5"
printf '%s\n' "$out_w5" | grep -q 'drained — next residual' || fail "closer walk not drained"
assert_absent "$out_w5" '/goal ' "drained closer still emitted /goal"
out_w6="$(run_cli complete --run-dir "$runw")"
printf '%s\n' "$out_w6" | grep -q 'residual: current' || fail "closer walk not residual: $out_w6"
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
printf '%s\n' "$out_n" | grep -q 'shiploop — session harness (not DevLoop)' || fail "next wrapper missing harness banner"
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

write_machine "$runm" '{"kind": "greenfield", "augment": false, "references": [], "tools": [], "mcp": [],
 "mcp_considered": "none(x)",
 "handles": [{"source": "gh", "need": "repo id", "resolve": "inspect", "value": "abc"}],
 "initiation": "none", "ui": true, "ui_craft": "frontend-design"}'
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
 \"mcp_considered\": \"none(x)\", \"handles\": [], \"initiation\": \"none\", \"ui\": false, \"ui_craft\": \"none(no UI)\"}"
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
 \"mcp_considered\": \"none(x)\", \"handles\": [], \"initiation\": \"none\", \"ui\": false, \"ui_craft\": \"none(no UI)\"}"
# dest plan already happened; hashes bound to prior env. Rebind via blocked → validate-spec → plan.
run_cli update --run-dir "$runpr" --to blocked --resume-to validate-spec --reason "add practice refs" >/dev/null
run_cli update --run-dir "$runpr" --to validate-spec --reason "rebind refs" >/dev/null
write_spec "$runpr"
write_machine "$runpr" "{\"kind\": \"greenfield\", \"augment\": false, \"references\": [{\"path\": \"$refpath\", \"why\": \"practice\"}], \"tools\": [], \"mcp\": [],
 \"mcp_considered\": \"none(x)\", \"handles\": [], \"initiation\": \"none\", \"ui\": false, \"ui_craft\": \"none(no UI)\"}"
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
    step["prompt"] = step["prompt"] + " cite " + ref
p.write_text(json.dumps(d, indent=2) + "\n")
PY
run_cli update --run-dir "$runpr" --to implement >/dev/null
out_cited="$(run_cli next --run-dir "$runpr")"
printf '%s\n' "$out_cited" | grep -qF "$refpath" || fail "next did not reprint cited reference"
printf 'LAYER: empty prompt + reference citation OK\n'

# --- A27 scope: inject-step's discovered steps are exempt from citation ---
out_inj_nocite="$(run_cli inject-step --run-dir "$runpr" --statement "ad hoc bind" --prompt "no citation needed for a discovered step" --produces "bind exists" --before S2)"
printf '%s\n' "$out_inj_nocite" | grep -q 'injected S' || fail "inject without citation should succeed: $out_inj_nocite"
python3 - "$runpr" <<'PY'
import json, sys
from pathlib import Path
run = Path(sys.argv[1])
dag = json.loads((run / "backchain" / "plan.json").read_text())
new = [s for s in dag["steps"] if s["origin"] == "discovered"]
assert new, "expected a discovered step"
assert all(s["prompt"] == "no citation needed for a discovered step" for s in new), new
PY
printf 'LAYER: inject-step exempt from reference citation OK\n'

# --- A16/A18/A22 inject-step ---
runinj="$tmpdir/inject/.shiploop"
repoinj="$tmpdir/inject/repo"
advance_to_plan "$runinj" "$repoinj" "$planf"
install_dag "$runinj" linear.json
run_cli update --run-dir "$runinj" --to implement >/dev/null
run_cli next --run-dir "$runinj" >/dev/null
set +e
out_ib="$(run_cli inject-step --run-dir "$runinj" --statement "mid" --prompt "/goal injected mid" --produces "mid exists" --before S1 2>&1)"
rc_ib=$?
set -e
[[ "$rc_ib" -eq 2 ]] || fail "inject --before running want 2: $out_ib"
set +e
out_ip="$(run_cli inject-step --run-dir "$runinj" --statement "mid" --prompt "" --produces "mid exists" --before S2 2>&1)"
rc_ip=$?
set -e
[[ "$rc_ip" -eq 2 ]] || fail "inject empty --prompt want 2: $out_ip"
out_iok="$(run_cli inject-step --run-dir "$runinj" --statement "mid bind" --prompt "/goal injected mid bind" --produces "mid exists" --before S2 --id S3)"
printf '%s\n' "$out_iok" | grep -q 'injected S3' || fail "inject add: $out_iok"
python3 - "$runinj" <<'PY'
import json, hashlib, sys
from pathlib import Path
run = Path(sys.argv[1])
dag = json.loads((run / "backchain" / "plan.json").read_text())
by_id = {s["id"]: s for s in dag["steps"]}
assert by_id["S3"]["origin"] == "discovered", by_id["S3"]
assert by_id["S3"]["prompt"] == "/goal injected mid bind"
assert any(i.get("from") == "S3" and i.get("need") == "mid exists" for i in by_id["S2"]["inputs"])
state = json.loads((run / "state.json").read_text())
assert state["phase"] == "implement", state["phase"]
digest = hashlib.sha256((run / "backchain" / "plan.json").read_bytes()).hexdigest()
assert state["plan_sha256"] == digest
wrapper = json.loads((run / "plan.json").read_text())
assert wrapper.get("plan_sha256") == digest
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
out_idone="$(run_cli inject-step --run-dir "$rundr" --statement "late" --prompt "/goal late" --produces "late exists" --before S2 2>&1)"
rc_idone=$?
set -e
[[ "$rc_idone" -eq 2 ]] || fail "inject --before done want 2: $out_idone"
out_idrain="$(run_cli inject-step --run-dir "$rundr" --statement "late" --prompt "/goal late discovered" --produces "late exists" --id S9)"
printf '%s\n' "$out_idrain" | grep -q 'injected S9' || fail "inject on drained: $out_idrain"
out_after="$(run_cli next --run-dir "$rundr")"
printf '%s\n' "$out_after" | grep -q '/goal late discovered' || fail "drained inject did not reprint new prompt: $out_after"
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

printf 'shiploop.test.sh: PASS\n'
