#!/usr/bin/env bash
# Incremental walk-journal + state-transition tests (no network).
# Standalone: bash test/shiploop-walk-journal.test.sh
# Also invoked from test/shiploop.test.sh.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cli="$root/skills/shiploop/scripts/shiploop"
fix="$root/test/fixtures/shiploop"
export SHIPLOOP_BACKCHAIN_ROOT="$fix/backchain-leaf"

fail() {
  printf 'shiploop-walk-journal.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

run_cli() { python3 "$cli" "$@"; }

DS='result.txt contains exactly one line: ok'

S1_LINEAR='/goal step S1: write the file; produces result.txt exists; suppliers repo exists from initial_state'
S2_LINEAR='/goal step S2: confirm the file; produces result.txt validated; suppliers result.txt exists from S1'
S1_TWOROOT='/goal step S1: write tests for the file; produces tests exist; suppliers repo exists from initial_state'
S2_TWOROOT='/goal step S2: write the implementation; produces result.txt exists; suppliers repo exists from initial_state'

packet_section() {
  local out="$1" start="$2"
  printf '%s\n' "$out" | awk -v s="$start" '
    $0==s {p=1; next}
    p && /^## / {exit}
    p
  '
}

walk_section() {
  printf '%s\n' "$1" | awk '
    $0 ~ /^Walk  / {p=1; print; next}
    p && ($0=="" || $0=="Diagnosis" || $0 ~ /^## /) {exit}
    p
  '
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

write_spec() {
  local run="$1"
  printf 'done_sentence: %s\ncheckable: true\n' "$DS" >"$run/spec.md"
  rm -f "$run/spec.json"
}

write_environment() {
  local run="$1"
  cat >"$run/environment.md" <<'MD'
Session survey brief for the test harness.

## machine
```json
{"kind": "greenfield", "augment": false, "references": [], "tools": [], "mcp": [],
 "mcp_considered": "none(no read-capable session tool matched done-sentence)",
 "handles": [], "initiation": "none", "ui": false, "ui_craft": "none(no UI in scope)"}
```
MD
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

host_complete() {
  local run="$1" sid="$2"
  commit_step_work "$run" "$sid"
  merge_step_branch "$run" "$sid"
  if [[ -n "${3:-}" ]]; then
    run_cli complete --run-dir "$run" --id "$sid"
  else
    run_cli complete --run-dir "$run"
  fi
}

assert_phase() {
  local run="$1" want="$2" msg="$3"
  local got
  got="$(python3 -c "import json; print(json.load(open('$run/state.json'))['phase'])")"
  [[ "$got" == "$want" ]] || fail "$msg: phase $got want $want"
}

assert_receipt() {
  local run="$1" sid="$2" status="$3" msg="$4"
  python3 - "$run" "$sid" "$status" "$msg" <<'PY' || fail "$msg"
import json, sys
from pathlib import Path
run, sid, status, msg = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
path = Path(run) / "steps" / f"{sid}.json"
state = json.loads((Path(run) / "state.json").read_text())
plan_h = state.get("plan_sha256") or ""
if status == "none":
    if path.is_file():
        sys.exit(f"{msg}: receipt {sid} exists")
    sys.exit(0)
if not path.is_file():
    sys.exit(f"{msg}: missing receipt {sid}")
rec = json.loads(path.read_text())
if rec.get("status") != status:
    sys.exit(f"{msg}: {sid} status {rec.get('status')!r} want {status!r}")
if rec.get("plan_sha256") != plan_h:
    sys.exit(f"{msg}: {sid} plan_sha256 mismatch")
PY
}

assert_walk_journal() {
  local run="$1" packet="$2" msg="$3"
  PACKET="$packet" python3 - "$run" "$msg" <<'PY' || fail "$msg"
import json, os, re, sys
from pathlib import Path
run = Path(sys.argv[1])
msg = sys.argv[2]
packet = os.environ.get("PACKET") or ""
state = json.loads((run / "state.json").read_text())
phase = state.get("phase")
walk_lines = []
in_walk = False
for line in packet.splitlines():
    if line.startswith("Walk  "):
        in_walk = True
        continue
    if in_walk:
        if not line.strip() or line == "Diagnosis" or line.startswith("## "):
            break
        walk_lines.append(line)
dag_path = run / "backchain" / "plan.json"
if phase != "implement" or not dag_path.is_file():
    if walk_lines:
        sys.exit(f"{msg}: Walk present outside implement ({phase})")
    sys.exit(0)
dag = json.loads(dag_path.read_text())
ids = [s["id"] for s in dag.get("steps") or [] if isinstance(s, dict) and s.get("id")]
plan_h = state.get("plan_sha256") or ""
marks = {}
pat = re.compile(r"^  (\[x\]|\[ \]) (\S+)  ")
for line in walk_lines:
    m = pat.match(line)
    if not m:
        sys.exit(f"{msg}: bad walk line {line!r}")
    marks[m.group(2)] = m.group(1)
    if m.group(1) == "[x]" and f"{m.group(2)}: done" not in line:
        sys.exit(f"{msg}: [x] {m.group(2)} missing S*: done")
    if m.group(1) == "[ ]" and f"{m.group(2)}: done" in line:
        sys.exit(f"{msg}: [ ] {m.group(2)} still says done")
if list(marks) != ids:
    sys.exit(f"{msg}: walk ids {list(marks)} != dag {ids}")
for sid in ids:
    rec_path = run / "steps" / f"{sid}.json"
    rec = json.loads(rec_path.read_text()) if rec_path.is_file() else None
    done = bool(
        rec
        and rec.get("status") == "complete"
        and rec.get("plan_sha256") == plan_h
    )
    want = "[x]" if done else "[ ]"
    if marks.get(sid) != want:
        sys.exit(f"{msg}: {sid} walk {marks.get(sid)!r} want {want} rec={rec}")
PY
}

assert_next_has() {
  local packet="$1" needle="$2" msg="$3"
  packet_section "$packet" "## Next prompt" | grep -Fq -- "$needle" \
    || fail "$msg: Next prompt missing ${needle}"
}

assert_next_lacks() {
  local packet="$1" needle="$2" msg="$3"
  if packet_section "$packet" "## Next prompt" | grep -Fq -- "$needle"; then
    fail "$msg: Next prompt has ${needle}"
  fi
}

assert_no_walk() {
  local packet="$1" msg="$2"
  if printf '%s\n' "$packet" | grep -q '^Walk  '; then
    fail "$msg: unexpected Walk rail"
  fi
}

assert_plan_md_unchanged() {
  local run="$1" want="$2" msg="$3"
  local got
  got="$(python3 -c "import hashlib,pathlib; print(hashlib.sha256(pathlib.Path('$run/plan.md').read_bytes()).hexdigest())")"
  [[ "$got" == "$want" ]] || fail "$msg: plan.md changed"
}

setup_bound_plan() {
  local path="$1"
  cat >"$path" <<'MD'
# Bound

## Review Coverage
None — residual loop waived: walk-journal fixture
MD
}

advance_to_implement() {
  local run="$1" repo="$2" planf="$3" fixture="$4"
  init_git_repo "$repo"
  run_cli init --prompt "create result.txt containing exactly one line: ok" \
    --run-dir "$run" --bound-plan "$planf" --repo "$repo" >/dev/null
  run_cli complete --run-dir "$run" >/dev/null
  write_environment "$run"
  write_spec "$run"
  run_cli complete --run-dir "$run" >/dev/null
  install_dag "$run" "$fixture"
  run_cli complete --run-dir "$run"
}

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/shiploop-walk-journal.XXXXXX")"
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

planf="$tmpdir/bound.plan.md"
setup_bound_plan "$planf"

# --- Scenario L: linear complete walk ---
runL="$tmpdir/L/.shiploop"
repoL="$tmpdir/L/repo"
init_git_repo "$repoL"

out_L0="$(run_cli init --prompt "create result.txt containing exactly one line: ok" \
  --run-dir "$runL" --bound-plan "$planf" --repo "$repoL")"
assert_phase "$runL" intake "L0"
assert_no_walk "$out_L0" "L0"
assert_next_has "$out_L0" "Write the original user ask" "L0"
assert_next_lacks "$out_L0" "/goal step S1:" "L0"

out_L1="$(run_cli complete --run-dir "$runL")"
assert_phase "$runL" validate-spec "L1"
assert_no_walk "$out_L1" "L1"
assert_next_has "$out_L1" "Survey, then practices, then spec" "L1"
assert_next_lacks "$out_L1" "/goal step S1:" "L1"

write_environment "$runL"
write_spec "$runL"
out_L2="$(run_cli complete --run-dir "$runL")"
assert_phase "$runL" plan "L2"
assert_no_walk "$out_L2" "L2"
assert_next_has "$out_L2" "The spec is **frozen**" "L2"
assert_next_lacks "$out_L2" "/goal step S1:" "L2"

install_dag "$runL" linear.json
out_L3="$(run_cli complete --run-dir "$runL")"
assert_phase "$runL" implement "L3"
assert_receipt "$runL" S1 running "L3"
assert_receipt "$runL" S2 none "L3"
assert_walk_journal "$runL" "$out_L3" "L3"
printf '%s\n' "$out_L3" | grep -Fq '[ ] S1  write the file' || fail "L3 walk [ ] S1"
printf '%s\n' "$out_L3" | grep -Fq '[ ] S2  confirm the file' || fail "L3 walk [ ] S2"
printf '%s\n' "$out_L3" | grep -q 'S1: running' || fail "L3 S1: running"
printf '%s\n' "$out_L3" | grep -q 'S2: todo' || fail "L3 S2: todo"
printf '%s\n' "$out_L3" | grep -q 'waiting on S1 write the file' || fail "L3 waiting-on"
assert_next_has "$out_L3" "$S1_LINEAR" "L3"
assert_next_lacks "$out_L3" "$S2_LINEAR" "L3"
assert_next_lacks "$out_L3" "Session steps are drained" "L3"
out_Lh="$(run_cli status --run-dir "$runL" --human)"
printf '%s\n' "$out_Lh" | grep -Fq '[ ] S1  write the file' || fail "L3 status --human missing [ ] S1"
assert_walk_journal "$runL" "$out_Lh" "L3 status --human"
plan_hash_L3="$(python3 -c "import hashlib,pathlib; print(hashlib.sha256(pathlib.Path('$runL/plan.md').read_bytes()).hexdigest())")"

out_L4="$(host_complete "$runL" S1)"
assert_phase "$runL" implement "L4"
assert_receipt "$runL" S1 complete "L4"
assert_receipt "$runL" S2 running "L4"
assert_walk_journal "$runL" "$out_L4" "L4"
printf '%s\n' "$out_L4" | grep -Fq '[x] S1  write the file' || fail "L4 walk [x] S1"
printf '%s\n' "$out_L4" | grep -Fq '[ ] S2  confirm the file' || fail "L4 walk [ ] S2"
printf '%s\n' "$out_L4" | grep -q 'S1: done' || fail "L4 S1: done"
printf '%s\n' "$out_L4" | grep -q 'S2: running' || fail "L4 S2: running"
assert_next_has "$out_L4" "$S2_LINEAR" "L4"
assert_next_lacks "$out_L4" "$S1_LINEAR" "L4"
assert_plan_md_unchanged "$runL" "$plan_hash_L3" "L4"

out_L5="$(host_complete "$runL" S2)"
assert_phase "$runL" implement "L5"
assert_receipt "$runL" S1 complete "L5"
assert_receipt "$runL" S2 complete "L5"
assert_walk_journal "$runL" "$out_L5" "L5"
printf '%s\n' "$out_L5" | grep -Fq '[x] S1  write the file' || fail "L5 walk [x] S1"
printf '%s\n' "$out_L5" | grep -Fq '[x] S2  confirm the file' || fail "L5 walk [x] S2"
assert_next_has "$out_L5" "Session steps are drained" "L5"
assert_next_lacks "$out_L5" "/goal " "L5"
assert_plan_md_unchanged "$runL" "$plan_hash_L3" "L5"

out_L6="$(run_cli complete --run-dir "$runL")"
assert_phase "$runL" residual "L6"
assert_receipt "$runL" S1 complete "L6"
assert_receipt "$runL" S2 complete "L6"
assert_no_walk "$out_L6" "L6"
assert_next_has "$out_L6" "Review-coverage is **waived**" "L6"
assert_next_lacks "$out_L6" "/goal step S" "L6"
printf 'LAYER: L linear complete-walk OK\n'

# --- N reprint (fresh linear, stop at L3/L4/L5) ---
runN="$tmpdir/N/.shiploop"
repoN="$tmpdir/N/repo"
out_N3="$(advance_to_implement "$runN" "$repoN" "$planf" linear.json)"
out_N1="$(run_cli next --run-dir "$runN")"
assert_phase "$runN" implement "N1"
assert_receipt "$runN" S1 running "N1"
assert_walk_journal "$runN" "$out_N1" "N1"
assert_next_has "$out_N1" "$S1_LINEAR" "N1"
assert_next_has "$out_N1" "In flight — do not open a second /goal" "N1"

host_complete "$runN" S1 >/dev/null
out_N2="$(run_cli next --run-dir "$runN")"
assert_receipt "$runN" S1 complete "N2"
assert_receipt "$runN" S2 running "N2"
assert_walk_journal "$runN" "$out_N2" "N2"
printf '%s\n' "$out_N2" | grep -Fq '[x] S1  write the file' || fail "N2 [x] S1"
assert_next_has "$out_N2" "$S2_LINEAR" "N2"
assert_next_has "$out_N2" "In flight — do not open a second /goal" "N2"
assert_next_lacks "$out_N2" "$S1_LINEAR" "N2"

host_complete "$runN" S2 >/dev/null
out_N3d="$(run_cli next --run-dir "$runN")"
assert_walk_journal "$runN" "$out_N3d" "N3"
assert_next_has "$out_N3d" "Session steps are drained" "N3"
assert_next_lacks "$out_N3d" "/goal " "N3"
printf 'LAYER: N reprint OK\n'

# --- D illegal skip / repeat ---
runD="$tmpdir/D/.shiploop"
repoD="$tmpdir/D/repo"
advance_to_implement "$runD" "$repoD" "$planf" linear.json >/dev/null
set +e
out_D1="$(run_cli complete-step --run-dir "$runD" --id S2 2>&1)"
rc_D1=$?
set -e
[[ "$rc_D1" -eq 2 ]] || fail "D1 want 2: $out_D1"
assert_receipt "$runD" S2 none "D1"
out_D1n="$(run_cli next --run-dir "$runD")"
assert_walk_journal "$runD" "$out_D1n" "D1 next"
printf '%s\n' "$out_D1n" | grep -q 'S2: todo' || fail "D1 S2 still todo"

host_complete "$runD" S1 >/dev/null
set +e
out_D2="$(run_cli complete-step --run-dir "$runD" --id S1 2>&1)"
rc_D2=$?
set -e
[[ "$rc_D2" -eq 2 ]] || fail "D2 want 2: $out_D2"
assert_receipt "$runD" S1 complete "D2"
out_D2n="$(run_cli next --run-dir "$runD")"
assert_walk_journal "$runD" "$out_D2n" "D2 next"
printf '%s\n' "$out_D2n" | grep -Fq '[x] S1  write the file' || fail "D2 [x] S1"
printf 'LAYER: D illegal skip/repeat OK\n'

# --- C clear retry / ancestor restart ---
runC1="$tmpdir/C1/.shiploop"
repoC1="$tmpdir/C1/repo"
advance_to_implement "$runC1" "$repoC1" "$planf" linear.json >/dev/null
out_C1="$(run_cli complete --run-dir "$runC1" --clear)"
assert_phase "$runC1" implement "C1"
assert_receipt "$runC1" S1 running "C1"
assert_walk_journal "$runC1" "$out_C1" "C1"
printf '%s\n' "$out_C1" | grep -Fq '[ ] S1  write the file' || fail "C1 [ ] S1"
assert_next_has "$out_C1" "$S1_LINEAR" "C1"
assert_next_lacks "$out_C1" "In flight — do not open a second /goal" "C1"

runC2="$tmpdir/C2/.shiploop"
repoC2="$tmpdir/C2/repo"
advance_to_implement "$runC2" "$repoC2" "$planf" linear.json >/dev/null
host_complete "$runC2" S1 >/dev/null
run_cli clear-step --run-dir "$runC2" --id S1 >/dev/null
out_C2="$(run_cli next --run-dir "$runC2")"
assert_receipt "$runC2" S1 running "C2"
assert_receipt "$runC2" S2 none "C2"
assert_walk_journal "$runC2" "$out_C2" "C2"
printf '%s\n' "$out_C2" | grep -Fq '[ ] S1  write the file' || fail "C2 [ ] S1"
printf '%s\n' "$out_C2" | grep -Fq '[ ] S2  confirm the file' || fail "C2 [ ] S2"
assert_next_has "$out_C2" "$S1_LINEAR" "C2"
assert_next_lacks "$out_C2" "$S2_LINEAR" "C2"
printf 'LAYER: C clear retry OK\n'

# --- P two-root parallel ---
runP="$tmpdir/P/.shiploop"
repoP="$tmpdir/P/repo"
out_P1="$(advance_to_implement "$runP" "$repoP" "$planf" two-root.json)"
assert_receipt "$runP" S1 running "P1"
assert_receipt "$runP" S2 running "P1"
assert_walk_journal "$runP" "$out_P1" "P1"
printf '%s\n' "$out_P1" | grep -Fq '[ ] S1  write tests for the file' || fail "P1 [ ] S1"
printf '%s\n' "$out_P1" | grep -Fq '[ ] S2  write the implementation' || fail "P1 [ ] S2"
assert_next_has "$out_P1" "$S1_TWOROOT" "P1"
assert_next_has "$out_P1" "$S2_TWOROOT" "P1"
n_goals="$(printf '%s\n' "$out_P1" | grep -c '^/goal step ' || true)"
[[ "$n_goals" -eq 2 ]] || fail "P1 want two /goal step lines: $n_goals"

set +e
out_P3="$(run_cli complete --run-dir "$runP" 2>&1)"
rc_P3=$?
set -e
[[ "$rc_P3" -eq 2 ]] || fail "P3 want 2: $out_P3"
printf '%s\n' "$out_P3" | grep -qi 'multiple running' || fail "P3 message: $out_P3"
assert_receipt "$runP" S1 running "P3"
assert_receipt "$runP" S2 running "P3"

commit_step_work "$runP" S1
merge_step_branch "$runP" S1
out_P2="$(run_cli complete --run-dir "$runP" --id S1)"
assert_receipt "$runP" S1 complete "P2"
assert_receipt "$runP" S2 running "P2"
assert_walk_journal "$runP" "$out_P2" "P2"
printf '%s\n' "$out_P2" | grep -Fq '[x] S1  write tests for the file' || fail "P2 [x] S1"
printf '%s\n' "$out_P2" | grep -Fq '[ ] S2  write the implementation' || fail "P2 [ ] S2"
assert_next_has "$out_P2" "$S2_TWOROOT" "P2"
assert_next_has "$out_P2" "In flight — do not open a second /goal" "P2"
assert_next_lacks "$out_P2" "$S1_TWOROOT" "P2"
printf 'LAYER: P parallel OK\n'

# --- I inject ---
runI1="$tmpdir/I1/.shiploop"
repoI1="$tmpdir/I1/repo"
advance_to_implement "$runI1" "$repoI1" "$planf" linear.json >/dev/null
run_cli inject-step --run-dir "$runI1" --statement "mid bind" \
  --prompt "/goal injected mid bind" --produces "mid exists" --before S2 --id S3 >/dev/null
out_I1="$(run_cli next --run-dir "$runI1")"
assert_phase "$runI1" implement "I1"
assert_receipt "$runI1" S1 running "I1"
assert_walk_journal "$runI1" "$out_I1" "I1"
printf '%s\n' "$out_I1" | grep -Fq '[ ] S3  mid bind' || fail "I1 [ ] S3"
printf '%s\n' "$out_I1" | grep -q 'waiting on' || fail "I1 S2 waiting"
printf '%s\n' "$out_I1" | grep -q 'S3' || fail "I1 walk missing S3"
assert_next_has "$out_I1" "$S1_LINEAR" "I1"
# empty inputs ⇒ ready ⇒ claimed running with S1
assert_receipt "$runI1" S3 running "I1"
assert_next_has "$out_I1" "/goal injected mid bind" "I1"

runI2="$tmpdir/I2/.shiploop"
repoI2="$tmpdir/I2/repo"
advance_to_implement "$runI2" "$repoI2" "$planf" linear.json >/dev/null
host_complete "$runI2" S1 >/dev/null
set +e
out_I2="$(run_cli inject-step --run-dir "$runI2" --statement "mid" \
  --prompt "/goal injected after S1" --produces "mid exists" --from S1 --before S2 --id S3 2>&1)"
rc_I2=$?
set -e
[[ "$rc_I2" -eq 2 ]] || fail "I2 want 2: $out_I2"
python3 - "$runI2" <<'PY' || fail "I2 DAG grew"
import json, sys
from pathlib import Path
ids = [s["id"] for s in json.loads((Path(sys.argv[1]) / "backchain" / "plan.json").read_text())["steps"]]
assert ids == ["S1", "S2"], ids
PY
out_I2n="$(run_cli next --run-dir "$runI2")"
assert_walk_journal "$runI2" "$out_I2n" "I2 next"
printf '%s\n' "$out_I2n" | grep -Fq '[x] S1  write the file' || fail "I2 [x] S1"
printf 'LAYER: I inject OK\n'

# --- B blocked resume implement ---
runB="$tmpdir/B/.shiploop"
repoB="$tmpdir/B/repo"
advance_to_implement "$runB" "$repoB" "$planf" linear.json >/dev/null
run_cli update --run-dir "$runB" --to blocked --resume-to implement --reason "host failed" >/dev/null
out_B1="$(run_cli complete --run-dir "$runB" --reason "resume")"
assert_phase "$runB" implement "B1"
assert_receipt "$runB" S1 running "B1"
assert_walk_journal "$runB" "$out_B1" "B1"
printf '%s\n' "$out_B1" | grep -Fq '[ ] S1  write the file' || fail "B1 [ ] S1"
if printf '%s\n' "$out_B1" | grep -Fq '[x] S1'; then
  fail "B1 unexpectedly [x] S1"
fi
assert_next_has "$out_B1" "$S1_LINEAR" "B1"
printf 'LAYER: B blocked resume OK\n'

# --- H hash-mismatch is not done ---
runH="$tmpdir/H/.shiploop"
repoH="$tmpdir/H/repo"
advance_to_implement "$runH" "$repoH" "$planf" linear.json >/dev/null
host_complete "$runH" S1 >/dev/null
python3 - "$runH" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1]) / "steps" / "S1.json"
rec = json.loads(p.read_text())
rec["plan_sha256"] = "deadbeef"
p.write_text(json.dumps(rec, indent=2) + "\n")
PY
out_H1h="$(run_cli status --run-dir "$runH" --human)"
assert_walk_journal "$runH" "$out_H1h" "H1 status --human"
if printf '%s\n' "$out_H1h" | grep -Fq '[x] S1'; then
  fail "H1 [x] S1 after hash mismatch"
fi
if printf '%s\n' "$out_H1h" | grep -q 'S1: done'; then
  fail "H1 S1: done after hash mismatch"
fi
printf '%s\n' "$out_H1h" | grep -q 'S1: ready' || fail "H1 expected S1: ready (mismatch is not done)"
set +e
out_H1="$(run_cli next --run-dir "$runH" 2>&1)"
rc_H1=$?
set -e
[[ "$rc_H1" -eq 2 ]] || fail "H1 next want 2 (kept branch blocks re-claim): $out_H1"
printf '%s\n' "$out_H1" | grep -qi 'already exists\|worktree add failed' \
  || fail "H1 next message: $out_H1"
printf 'LAYER: H hash-mismatch OK\n'

# --- F replan wipes receipts ---
runF="$tmpdir/F/.shiploop"
repoF="$tmpdir/F/repo"
advance_to_implement "$runF" "$repoF" "$planf" linear.json >/dev/null
host_complete "$runF" S1 >/dev/null
run_cli complete --run-dir "$runF" --blocked --reason "replan" --resume-to plan >/dev/null
run_cli complete --run-dir "$runF" --reason "replan" >/dev/null
assert_phase "$runF" plan "F1 dest plan"
assert_receipt "$runF" S1 none "F1 after dest plan"
assert_receipt "$runF" S2 none "F1 after dest plan"
install_dag "$runF" linear.json
out_F1="$(run_cli complete --run-dir "$runF")"
assert_phase "$runF" implement "F1"
assert_receipt "$runF" S1 running "F1"
assert_receipt "$runF" S2 none "F1"
assert_walk_journal "$runF" "$out_F1" "F1"
printf '%s\n' "$out_F1" | grep -Fq '[ ] S1  write the file' || fail "F1 [ ] S1"
if printf '%s\n' "$out_F1" | grep -Fq '[x] S1'; then
  fail "F1 old [x] survived replan"
fi
assert_next_has "$out_F1" "$S1_LINEAR" "F1"
printf 'LAYER: F replan wipe OK\n'

printf 'shiploop-walk-journal.test.sh: PASS\n'
