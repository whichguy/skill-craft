#!/usr/bin/env bash
# Hermetic steer session-harness tests (no network).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cli="$root/skills/steer/scripts/steer"
fix="$root/test/fixtures/steer"
export STEER_BACKCHAIN_ROOT="$fix/backchain-leaf"

fail() {
  printf 'steer.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

[[ -f "$root/skills/steer/SKILL.md" ]] || fail "missing SKILL.md"
[[ ! -d "$root/skills/steer/prompts" ]] || fail "prompts/ must not exist"
grep -q 'kind: script-backed' "$root/skills/steer/SKILL.md" || fail "frontmatter kind"
grep -q 'name: steer' "$root/skills/steer/SKILL.md" || fail "frontmatter name"
grep -q 'steer — session harness (not DevLoop)' "$root/skills/steer/SKILL.md" || fail "banner"
if grep -q 'DEFINE → PROVE → BUILD' "$root/skills/steer/SKILL.md"; then
  fail "SKILL.md must not own DEFINE/PROVE/BUILD"
fi
grep -qi 'not DevLoop' "$root/skills/steer/SKILL.md" || fail "must demote DevLoop"
if grep -E 'steer capture|devloop-run' "$root/skills/steer/references/activities/implement.md"; then
  fail "implement activity still captures /devloop"
fi
[[ -f "$root/skills/steer/references/host-matrix.md" ]] || fail "missing host-matrix.md"
[[ -f "$root/skills/steer/references/ledger-contract.md" ]] || fail "missing ledger-contract.md"
grep -q 'copied, not imported' "$root/skills/steer/references/ledger-contract.md" || fail "ledger-contract copy note"
grep -q 'VALIDATE_SPEC_PATH' "$root/skills/steer/references/activities/validate-spec.md" \
  && fail "validate-spec.md must not mention VALIDATE_SPEC_PATH"
for tok in prep "intermediate deploy" cleanup; do
  grep -q "$tok" "$root/skills/steer/references/activities/plan.md" || fail "plan.md missing $tok"
done
chmod +x "$cli"

le_docs="$root/docs/LOOP-ENGINEERING.md"
le_skill="$root/skills/devloop/references/loop-engineering.md"
diff -q "$le_docs" "$le_skill" >/dev/null || fail "LOOP-ENGINEERING copies drifted"
grep -q 'Steer session' "$le_docs" || fail "LOOP-ENGINEERING missing Steer session track"
grep -q 'steer-next' "$le_docs" || fail "LOOP-ENGINEERING missing steer-next"
grep -q 'does not rewrite the spec' "$le_docs" || fail "LOOP-ENGINEERING missing no-spec-rewrite"
if grep -qi 'c-plan' <<<"$(sed -n '/^## Compose graph$/,/^## Practices$/p' "$le_docs")"; then
  fail "compose graph must not name c-plan"
fi
grep -q 'emits a `/goal`' "$le_docs" || fail "LOOP-ENGINEERING missing emits a /goal"
grep -Eiq 'Never.+invoke' "$root/skills/steer/SKILL.md" || fail "SKILL.md missing Never invoke"

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/steer-test.XXXXXX")"
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

HEADINGS='## You are here
## Reminder
## Look here
## Next prompt
## When done invoke
## Missing'

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

DS='result.txt contains exactly one line: ok'

write_spec() {
  local run="$1"
  printf '%s\n' "{\"done_sentence\":\"$DS\",\"checkable\":true}" >"$run/spec.json"
  printf 'done_sentence: %s\n' "$DS" >"$run/spec.md"
}

write_wrapper() {
  local run="$1"
  printf '%s\n' "{\"done_sentence\":\"$DS\",\"backchain\":\"$run/backchain/plan.json\"}" >"$run/plan.json"
  printf 'done_sentence: %s\n' "$DS" >"$run/plan.md"
}

install_dag() {
  local run="$1" fixture="$2"
  mkdir -p "$run/backchain"
  cp "$fix/$fixture" "$run/backchain/plan.json"
  write_wrapper "$run"
}

advance_to_plan() {
  local run="$1" repo="$2" planf="$3"
  run_cli init --prompt "create result.txt containing exactly one line: ok" \
    --run-dir "$run" --bound-plan "$planf" --repo "$repo" >/dev/null
  run_cli update --run-dir "$run" --to validate-spec >/dev/null
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
mkdir -p "$repo"
planf="$tmpdir/bound.plan.md"
cat >"$planf" <<'MD'
# Bound

## Review Coverage
filled for later waiver tests
MD
run="$repo/.steer"
out_init="$(run_cli init --prompt "create result.txt containing exactly one line: ok" \
  --run-dir "$run" --bound-plan "$planf" --repo "$repo")"
printf '%s\n' "$out_init" | grep -q 'initialized' || fail "init: $out_init"
assert_headings "$out_init"
printf '%s\n' "$out_init" | grep -q 'intake: current' || fail "map current intake"
printf '%s\n' "$out_init" | grep -q 'validate-spec: todo' || fail "map todo"
printf '%s\n' "$out_init" | grep -E 'spec\.md|plan\.md' >/dev/null || fail "look here spec/plan paths"
printf '%s\n' "$out_init" | grep -q 'steer update --run-dir' || fail "when done update"
printf '%s\n' "$out_init" | grep -q 'steer-next' || fail "when done steer-next"
printf '%s\n' "$out_init" | grep -q 'Ask: create result.txt' || fail "reminder ask"
printf 'LAYER: init packet OK\n'

# --- init reuse vs force ---
out_re="$(run_cli init --run-dir "$run")"
printf '%s\n' "$out_re" | grep -q 'reused' || fail "reuse: $out_re"
run_cli init --force --prompt "second" --run-dir "$run" --bound-plan "$planf" --repo "$repo" >/dev/null
grep -q 'second' "$run/prompt.md" || fail "force did not reset prompt"
run_cli init --force --prompt "create result.txt containing exactly one line: ok" \
  --run-dir "$run" --bound-plan "$planf" --repo "$repo" >/dev/null
printf 'LAYER: reuse vs force OK\n'

# --- init does not adopt ancestor .steer ---
mkdir -p "$tmpdir/tree/child"
python3 "$cli" init --prompt "parent" --run-dir "$tmpdir/tree/.steer" >/dev/null
(
  cd "$tmpdir/tree/child"
  python3 "$cli" init --prompt "child-only" >/dev/null
)
[[ -f "$tmpdir/tree/child/.steer/state.json" ]] || fail "child init missing"
grep -q 'child-only' "$tmpdir/tree/child/.steer/prompt.md" || fail "child used ancestor"
printf 'LAYER: init no ancestor adopt OK\n'

# --- package-root write refuse ---
set +e
out_pkg="$(run_cli init --prompt x --run-dir "$root/skills/steer/.steer" 2>&1)"
rc_pkg=$?
set -e
[[ "$rc_pkg" -eq 2 ]] || fail "package write want 2 got $rc_pkg: $out_pkg"
printf 'LAYER: package-root refuse OK\n'

# --- update requires --run-dir ---
set +e
out_urd="$(run_cli update --to validate-spec 2>&1)"
rc_urd=$?
set -e
[[ "$rc_urd" -ne 0 ]] || fail "update without --run-dir should fail"
printf 'LAYER: update --run-dir required OK\n'

# --- intake -> validate-spec ---
run_cli update --run-dir "$run" --to validate-spec >/dev/null
out_vs="$(run_cli next --run-dir "$run")"
assert_headings "$out_vs"
printf '%s\n' "$out_vs" | grep -q 'intake: done' || fail "intake done"
printf '%s\n' "$out_vs" | grep -q 'validate-spec: current' || fail "vs current"
printf '%s\n' "$out_vs" | grep -q 'not written yet' || fail "spec not written yet pointer"
assert_absent "$out_vs" 'VALIDATE_SPEC_PATH' "packet leaked VALIDATE_SPEC_PATH"
assert_absent "$out_vs" 'missing dep_roots.devloop' "devloop required at validate-spec"
assert_absent "$out_vs" '/goal ' "validate-spec packet emitted implement /goal"
printf 'LAYER: intake->validate-spec OK\n'

# --- empty spec.json rejected ---
printf '%s\n' '{}' >"$run/spec.json"
printf 'body\n' >"$run/spec.md"
set +e
out_es="$(run_cli update --run-dir "$run" --to plan 2>&1)"
rc_es=$?
set -e
[[ "$rc_es" -eq 2 ]] || fail "empty spec want 2: $out_es"
printf 'LAYER: empty spec.json reject OK\n'

# --- labeled done_sentence mismatch ---
printf '%s\n' '{"done_sentence":"alpha","checkable":true}' >"$run/spec.json"
printf 'done_sentence: beta\n' >"$run/spec.md"
set +e
out_mm="$(run_cli update --run-dir "$run" --to plan 2>&1)"
rc_mm=$?
set -e
[[ "$rc_mm" -eq 2 ]] || fail "mismatch want 2: $out_mm"
printf '%s\n' "$out_mm" | grep -qi 'done_sentence' || fail "mismatch message: $out_mm"
printf 'LAYER: labeled mismatch reject OK\n'

# --- checkable false -> blocked ---
printf '%s\n' '{"done_sentence":"need a checkable done","checkable":false,"ask_user":"what is the oracle?"}' >"$run/spec.json"
printf 'done_sentence: need a checkable done\n\nmore spec prose that must not be dumped later\n' >"$run/spec.md"
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

# --- happy spec + thin plan cannot implement ---
write_spec "$run"
run_cli update --run-dir "$run" --to plan >/dev/null
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
printf '%s\n' "$out_imp" | grep -Eiq 'test' || fail "missing test token"
printf '%s\n' "$out_imp" | grep -Eiq 'run' || fail "missing run token"
printf '%s\n' "$out_imp" | grep -Eiq 'fix' || fail "missing fix token"
assert_absent "$out_imp" 'refine the spec' "implement said refine"
assert_absent "$out_imp" 'steps: write file' "dumped plan body"
printf '%s\n' "$out_imp" | grep -q 'S1: running' || fail "S1 not running"
printf '%s\n' "$out_imp" | grep -q 'S2: todo' || fail "S2 should wait"
printf '%s\n' "$out_imp" | grep -q 'complete-step' || fail "when done missing complete-step"
printf '%s\n' "$out_imp" | grep -q -- '--id S1' || fail "when done missing --id S1"
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
run_cli complete-step --run-dir "$run" --id S1 >/dev/null
out_mid="$(run_cli next --run-dir "$run")"
printf '%s\n' "$out_mid" | grep -q 'S1: done' || fail "S1 not done"
printf '%s\n' "$out_mid" | grep -q 'S2: running' || fail "S2 not claimed"
printf '%s\n' "$out_mid" | grep -q '/goal ' || fail "S2 missing /goal"
run_cli complete-step --run-dir "$run" --id S1 >/dev/null 2>&1 && fail "duplicate complete should fail" || true
set +e
out_dup="$(run_cli complete-step --run-dir "$run" --id S1 2>&1)"
rc_dup=$?
set -e
[[ "$rc_dup" -eq 2 ]] || fail "duplicate complete want 2"
run_cli complete-step --run-dir "$run" --id S2 >/dev/null
out_dr="$(run_cli next --run-dir "$run")"
printf '%s\n' "$out_dr" | grep -q -- '--to residual' || fail "drained missing residual"
run_cli update --run-dir "$run" --to residual >/dev/null
printf 'LAYER: linear drain OK\n'

# --- capture fail-closed and does not clobber ---
printf '%s\n' '{"writer":"steer.steps","run_id":"keep","complete":["S1","S2"]}' >"$run/implement.json"
set +e
out_cap="$(run_cli capture --run-dir "$run" -- echo hi 2>&1)"
rc_cap=$?
set -e
[[ "$rc_cap" -eq 2 ]] || fail "capture want 2: $out_cap"
grep -q 'steer.steps' "$run/implement.json" || fail "capture overwrote implement.json"
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
run_cli update --run-dir "$run" --to done >/dev/null
out_done="$(run_cli next --run-dir "$run")"
printf '%s\n' "$out_done" | grep -q 'stop — no update' || fail "done stop: $out_done"
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
run2="$tmpdir/two/.steer"
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
run_cli complete-step --run-dir "$run2" --id S1 >/dev/null
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
run3="$tmpdir/conc/.steer"
repo3="$tmpdir/conc/repo"
mkdir -p "$repo3"
advance_to_plan "$run3" "$repo3" "$planf"
install_dag "$run3" two-root.json
run_cli update --run-dir "$run3" --to implement >/dev/null
run_cli next --run-dir "$run3" >/dev/null
python3 "$cli" complete-step --run-dir "$run3" --id S1 >/tmp/steer-c1.out 2>&1 &
p1=$!
python3 "$cli" complete-step --run-dir "$run3" --id S2 >/tmp/steer-c2.out 2>&1 &
p2=$!
wait "$p1" || fail "concurrent S1"
wait "$p2" || fail "concurrent S2"
python3 - "$run3" <<'PY'
import json, sys
from pathlib import Path
run = Path(sys.argv[1])
impl = json.loads((run / "implement.json").read_text())
assert impl["writer"] == "steer.steps"
assert sorted(impl["complete"]) == ["S1", "S2"], impl
for sid in ("S1", "S2"):
    rec = json.loads((run / "steps" / f"{sid}.json").read_text())
    assert rec["status"] == "complete", rec
PY
printf 'LAYER: concurrent complete-step OK\n'

# --- residual-risk / empty / cycle / unsafe / goal mismatch / inv-7 ---
reject_dag() {
  local name="$1"
  local r="$tmpdir/rej-$name/.steer"
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
runh="$tmpdir/hash/.steer"
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
# restore DAG, mutate spec.json only, next + complete-step must fail
python3 - "$runh/backchain/plan.json" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
d = json.loads(p.read_text())
d["steps"][0]["statement"] = "write the file"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
python3 - "$runh/spec.json" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
d = json.loads(p.read_text())
d["checkable"] = True
d["note"] = "mutated-json"
p.write_text(json.dumps(d) + "\n")
PY
set +e
out_sj="$(run_cli next --run-dir "$runh" 2>&1)"
rc_sj=$?
out_csd="$(run_cli complete-step --run-dir "$runh" --id S1 2>&1)"
rc_csd=$?
set -e
[[ "$rc_sj" -eq 2 ]] || fail "spec.json drift next want 2: $out_sj"
[[ "$rc_csd" -eq 2 ]] || fail "spec.json drift complete-step want 2: $out_csd"
printf 'LAYER: hash drift OK\n'

# --- init --force cannot reuse prior DAG ---
runf="$tmpdir/force/.steer"
repof="$tmpdir/force/repo"
mkdir -p "$repof"
advance_to_plan "$runf" "$repof" "$planf"
install_dag "$runf" linear.json
run_cli update --run-dir "$runf" --to implement >/dev/null
run_cli next --run-dir "$runf" >/dev/null
run_cli init --force --prompt "fresh" --run-dir "$runf" --bound-plan "$planf" --repo "$repof" >/dev/null
[[ ! -f "$runf/backchain/plan.json" ]] || fail "force left backchain"
[[ ! -d "$runf/steps" ]] || [[ -z "$(ls -A "$runf/steps" 2>/dev/null || true)" ]] || fail "force left steps"
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
runi="$tmpdir/inj/.steer"
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
runb="$tmpdir/blk/.steer"
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
run_cli complete-step --run-dir "$runb" --id S1 >/dev/null
run_cli complete-step --run-dir "$runb" --id S2 >/dev/null
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
runm="$tmpdir/miss/.steer"
repom="$tmpdir/miss/repo"
mkdir -p "$repom"
(
  unset STEER_BACKCHAIN_ROOT
  export HOME="$tmpdir/empty-home-miss"
  mkdir -p "$HOME"
  python3 "$cli" init --prompt "x" --run-dir "$runm" --bound-plan "$planf" --repo "$repom" >/dev/null
  python3 "$cli" update --run-dir "$runm" --to validate-spec >/dev/null
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
export STEER_BACKCHAIN_ROOT="$fix/backchain-leaf"
run_cli update --run-dir "$runm" --to implement >/dev/null
printf 'LAYER: backchain missing + refresh OK\n'

# --- plan -> blocked ---
runp="$tmpdir/pblock/.steer"
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
  unset STEER_DEVLOOP_ROOT
  export STEER_BACKCHAIN_ROOT="$fix/backchain-leaf"
  r="$tmpdir/nodev/.steer"
  rp="$tmpdir/nodev/repo"
  mkdir -p "$rp"
  python3 "$cli" init --prompt "x" --run-dir "$r" --bound-plan "$planf" --repo "$rp" >/dev/null
  python3 "$cli" update --run-dir "$r" --to validate-spec >/dev/null
  write_spec "$r"
  python3 "$cli" update --run-dir "$r" --to plan >/dev/null
  install_dag "$r" linear.json
  python3 "$cli" update --run-dir "$r" --to implement >/dev/null
)
printf 'LAYER: no DevLoop sibling OK\n'

# --- replan clears receipts; wrapper step_ids not SoT ---
runr="$tmpdir/replan/.steer"
repor="$tmpdir/replan/repo"
mkdir -p "$repor"
advance_to_plan "$runr" "$repor" "$planf"
install_dag "$runr" linear.json
run_cli update --run-dir "$runr" --to implement >/dev/null
run_cli next --run-dir "$runr" >/dev/null
run_cli complete-step --run-dir "$runr" --id S1 >/dev/null
run_cli update --run-dir "$runr" --to blocked --resume-to plan --reason "replan" >/dev/null
run_cli update --run-dir "$runr" --to plan --reason "replan" >/dev/null
[[ ! -e "$runr/steps/S1.json" ]] || fail "replan left S1 receipt"
# wrapper step_ids are not SoT: stale list must not hide S2
runsot="$tmpdir/sot/.steer"
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
run_cli complete-step --run-dir "$runsot" --id S1 >/dev/null
out_sot="$(run_cli next --run-dir "$runsot")"
printf '%s\n' "$out_sot" | grep -q 'S2: running' || fail "stale wrapper step_ids hid S2"
printf 'LAYER: replan clears receipts OK\n'

# --- string produces still accepted ---
runs="$tmpdir/strprod/.steer"
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
rund="$tmpdir/driftblk/.steer"
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
PY
printf 'LAYER: drift --to blocked OK\n'

# --- clear-step invalidates descendants ---
runc="$tmpdir/desc/.steer"
repoc="$tmpdir/desc/repo"
mkdir -p "$repoc"
advance_to_plan "$runc" "$repoc" "$planf"
install_dag "$runc" linear.json
run_cli update --run-dir "$runc" --to implement >/dev/null
run_cli next --run-dir "$runc" >/dev/null
run_cli complete-step --run-dir "$runc" --id S1 >/dev/null
run_cli next --run-dir "$runc" >/dev/null
run_cli complete-step --run-dir "$runc" --id S2 >/dev/null
run_cli clear-step --run-dir "$runc" --id S1 >/dev/null
[[ ! -e "$runc/steps/S1.json" ]] || fail "S1 receipt remained"
[[ ! -e "$runc/steps/S2.json" ]] || fail "descendant S2 receipt remained"
set +e
out_clr="$(run_cli update --run-dir "$runc" --to residual 2>&1)"
rc_clr=$?
set -e
[[ "$rc_clr" -eq 2 ]] || fail "clear then residual want 2: $out_clr"
printf 'LAYER: clear-step descendants OK\n'

# --- checkable:false cannot --to implement after plan rebind ---
runcf="$tmpdir/checkimpl/.steer"
repocf="$tmpdir/checkimpl/repo"
mkdir -p "$repocf"
advance_to_plan "$runcf" "$repocf" "$planf"
install_dag "$runcf" linear.json
run_cli update --run-dir "$runcf" --to blocked --resume-to plan --reason "rebind uncheckable" >/dev/null
printf '%s\n' '{"done_sentence":"need a checkable done","checkable":false,"ask_user":"what is the oracle?"}' >"$runcf/spec.json"
printf 'done_sentence: need a checkable done\n' >"$runcf/spec.md"
run_cli update --run-dir "$runcf" --to plan --reason "rebind" >/dev/null
set +e
out_cf="$(run_cli update --run-dir "$runcf" --to implement 2>&1)"
rc_cf=$?
set -e
[[ "$rc_cf" -eq 2 ]] || fail "checkable false implement want 2: $out_cf"
printf '%s\n' "$out_cf" | grep -qi 'checkable' || fail "checkable message: $out_cf"
printf 'LAYER: checkable false implement refuse OK\n'

# --- missing frozen files fail closed; --to blocked still works ---
runmf="$tmpdir/missfiles/.steer"
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
runsup="$tmpdir/supplier/.steer"
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
    "writer": "steer.start-step",
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
runsy="$tmpdir/symlink/.steer"
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

printf 'steer.test.sh: PASS\n'
