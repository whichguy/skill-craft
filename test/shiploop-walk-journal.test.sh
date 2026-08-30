#!/usr/bin/env bash
# Incremental walk-journal + state-transition tests (no network).
#
# Each CASE is: PRE disk → INVOKE scripts/shiploop → RETURN (rc + stdout) → DISK.
# Glyphs match the session rail: ● done / ▶ running|ready / ○ todo. No ✗ on steps.
#
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

DS='result.txt contains exactly one line: ok'
S1_LINEAR='/goal step S1: write the file; produces result.txt exists; suppliers repo exists from initial_state'
S2_LINEAR='/goal step S2: confirm the file; produces result.txt validated; suppliers result.txt exists from S1'
S1_TWOROOT='/goal step S1: write tests for the file; produces tests exist; suppliers repo exists from initial_state'
S2_TWOROOT='/goal step S2: write the implementation; produces result.txt exists; suppliers repo exists from initial_state'

LAST_RC=0
LAST_OUT=""
LAST_ERR=""

packet_section() {
  local out="$1" start="$2"
  printf '%s\n' "$out" | awk -v s="$start" '
    $0==s {p=1; next}
    p && /^## / {exit}
    p
  '
}

invoke_script() {
  local outf errf
  outf="$(mktemp "${TMPDIR:-/tmp}/shiploop-out.XXXXXX")"
  errf="$(mktemp "${TMPDIR:-/tmp}/shiploop-err.XXXXXX")"
  set +e
  python3 "$cli" "$@" >"$outf" 2>"$errf"
  LAST_RC=$?
  set -e
  LAST_OUT="$(cat "$outf")"
  LAST_ERR="$(cat "$errf")"
  rm -f "$outf" "$errf"
}

assert_rc() {
  local want="$1" msg="$2"
  [[ "$LAST_RC" -eq "$want" ]] || fail \
    "$msg: rc=$LAST_RC want=$want stderr=$(printf '%s' "$LAST_ERR" | tr '\n' ' ') stdout=$(printf '%s' "$LAST_OUT" | head -c 400)"
}

assert_out_has() {
  local needle="$1" msg="$2"
  printf '%s\n' "$LAST_OUT" | grep -Fq -- "$needle" \
    || fail "$msg: stdout missing ${needle}"
}

assert_out_lacks() {
  local needle="$1" msg="$2"
  if printf '%s\n' "$LAST_OUT" | grep -Fq -- "$needle"; then
    fail "$msg: stdout has ${needle}"
  fi
}

assert_err_has() {
  local needle="$1" msg="$2"
  printf '%s\n' "$LAST_ERR" | grep -qiE -- "$needle" \
    || fail "$msg: stderr missing ${needle}: $LAST_ERR"
}

assert_next_has() {
  local needle="$1" msg="$2"
  packet_section "$LAST_OUT" "## Next prompt" | grep -Fq -- "$needle" \
    || fail "$msg: Next prompt missing ${needle}"
}

assert_next_lacks() {
  local needle="$1" msg="$2"
  if packet_section "$LAST_OUT" "## Next prompt" | grep -Fq -- "$needle"; then
    fail "$msg: Next prompt has ${needle}"
  fi
}

assert_no_walk() {
  local msg="$1"
  if printf '%s\n' "$LAST_OUT" | grep -q '^Walk  '; then
    fail "$msg: unexpected Walk rail"
  fi
}

# On-disk snapshot. spec JSON keys:
#   phase, receipts {id: running|complete|none}, files {rel: bool},
#   plan_sha256 / spec_sha256: empty|set,
#   blocked_from, resume_to, history (last history.jsonl event)
assert_disk() {
  local run="$1" msg="$2" spec="$3"
  python3 - "$run" "$msg" "$spec" <<'PY' || fail "$msg"
import json, sys
from pathlib import Path
run = Path(sys.argv[1])
msg = sys.argv[2]
spec = json.loads(sys.argv[3])
state_path = run / "state.json"
if not state_path.is_file():
    sys.exit(f"{msg}: missing state.json")
state = json.loads(state_path.read_text())
if "phase" in spec and state.get("phase") != spec["phase"]:
    sys.exit(f"{msg}: phase {state.get('phase')!r} want {spec['phase']!r}")
for key in ("plan_sha256", "spec_sha256", "environment_sha256"):
    if key not in spec:
        continue
    val = str(state.get(key) or "")
    want = spec[key]
    if want == "empty" and val:
        sys.exit(f"{msg}: {key} set, want empty")
    if want == "set" and not val:
        sys.exit(f"{msg}: {key} empty, want set")
for key in ("blocked_from", "resume_to", "terminal"):
    if key in spec and (state.get(key) or None) != (spec[key] or None):
        sys.exit(f"{msg}: {key}={state.get(key)!r} want {spec[key]!r}")
plan_h = str(state.get("plan_sha256") or "")
for sid, status in (spec.get("receipts") or {}).items():
    path = run / "steps" / f"{sid}.json"
    if status == "none":
        if path.is_file():
            sys.exit(f"{msg}: receipt {sid} exists")
        continue
    if not path.is_file():
        sys.exit(f"{msg}: missing receipt {sid}")
    rec = json.loads(path.read_text())
    if rec.get("status") != status:
        sys.exit(f"{msg}: {sid} status {rec.get('status')!r} want {status!r}")
    if rec.get("plan_sha256") != plan_h:
        sys.exit(f"{msg}: {sid} plan_sha256 mismatch")
for rel, want in (spec.get("files") or {}).items():
    exists = (run / rel).is_file()
    if bool(want) != exists:
        sys.exit(f"{msg}: {rel} exists={exists} want={want}")
if "history" in spec:
    hist = run / "history.jsonl"
    if not hist.is_file():
        sys.exit(f"{msg}: missing history.jsonl")
    last = hist.read_text(encoding="utf-8").splitlines()[-1]
    event = json.loads(last).get("event")
    if event != spec["history"]:
        sys.exit(f"{msg}: last event {event!r} want {spec['history']!r}")
PY
}

assert_walk_journal() {
  local run="$1" msg="$2"
  PACKET="$LAST_OUT" python3 - "$run" "$msg" <<'PY' || fail "$msg"
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
steps = [s for s in dag.get("steps") or [] if isinstance(s, dict) and s.get("id")]
ids = [s["id"] for s in steps]
by_id = {s["id"]: s for s in steps}
plan_h = str(state.get("plan_sha256") or "")
receipts = {}
for sid in ids:
    p = run / "steps" / f"{sid}.json"
    receipts[sid] = json.loads(p.read_text()) if p.is_file() else None

def matches(rec, status):
    return bool(rec) and rec.get("status") == status and rec.get("plan_sha256") == plan_h

def suppliers_ok(step):
    for inp in step.get("inputs") or []:
        if not isinstance(inp, dict):
            return False
        fr = inp.get("from")
        if fr is None:
            continue
        if not matches(receipts.get(str(fr)), "complete"):
            return False
    return True

def klass_of(sid):
    rec = receipts.get(sid)
    if matches(rec, "complete"):
        return "done"
    if matches(rec, "running"):
        return "running"
    if suppliers_ok(by_id.get(sid) or {}):
        return "ready"
    return "todo"

MARK = {"done": "●", "running": "▶", "ready": "▶", "todo": "○"}
pat = re.compile(r"^  ([●▶○]) (\S+)  ")
marks = {}
for line in walk_lines:
    m = pat.match(line)
    if not m:
        sys.exit(f"{msg}: bad walk line {line!r}")
    sid, mark = m.group(2), m.group(1)
    marks[sid] = mark
    want_k = klass_of(sid)
    if mark != MARK[want_k]:
        sys.exit(f"{msg}: {sid} mark {mark!r} want {MARK[want_k]!r} klass={want_k}")
    if f"{sid}: {want_k}" not in line:
        sys.exit(f"{msg}: {sid} line missing '{sid}: {want_k}': {line!r}")
    if re.search(r"\[[xX ]\]", line):
        sys.exit(f"{msg}: checkbox mark leaked: {line!r}")
if list(marks) != ids:
    sys.exit(f"{msg}: walk ids {list(marks)} != dag {ids}")
PY
}

assert_plan_md_unchanged() {
  local run="$1" want="$2" msg="$3"
  local got
  got="$(python3 -c "import hashlib,pathlib; print(hashlib.sha256(pathlib.Path('$run/plan.md').read_bytes()).hexdigest())")"
  [[ "$got" == "$want" ]] || fail "$msg: plan.md changed"
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

# Host closer pre-work (not an SM transition): commit on the worktree, merge to session HEAD.
host_land() {
  commit_step_work "$1" "$2"
  merge_step_branch "$1" "$2"
}

setup_bound_plan() {
  cat >"$1" <<'MD'
# Bound

## Review Coverage
None — residual loop waived: walk-journal fixture
MD
}

# Drive intake→implement via the script. Caller asserts PRE of the *next* CASE.
setup_to_implement() {
  local run="$1" repo="$2" planf="$3" fixture="$4"
  init_git_repo "$repo"
  invoke_script init --prompt "create result.txt containing exactly one line: ok" \
    --run-dir "$run" --bound-plan "$planf" --repo "$repo"
  assert_rc 0 "setup init"
  invoke_script complete --run-dir "$run"
  assert_rc 0 "setup dest validate-spec"
  write_environment "$run"
  write_spec "$run"
  invoke_script complete --run-dir "$run"
  assert_rc 0 "setup dest plan"
  install_dag "$run" "$fixture"
  invoke_script complete --run-dir "$run"
  assert_rc 0 "setup dest implement"
}

DISK_INTAKE='{"phase":"intake","receipts":{"S1":"none","S2":"none"},"files":{"prompt.md":true,"spec.md":false,"environment.md":false,"plan.md":false,"backchain/plan.json":false},"plan_sha256":"empty","spec_sha256":"empty"}'
DISK_VS='{"phase":"validate-spec","files":{"prompt.md":true,"spec.md":false},"plan_sha256":"empty"}'
DISK_PLAN='{"phase":"plan","files":{"spec.md":true,"environment.md":true,"backchain/plan.json":false},"spec_sha256":"set","plan_sha256":"empty"}'
DISK_IMP_S1RUN='{"phase":"implement","receipts":{"S1":"running","S2":"none"},"files":{"backchain/plan.json":true,"plan.md":true},"plan_sha256":"set","spec_sha256":"set"}'
DISK_IMP_S1DONE='{"phase":"implement","receipts":{"S1":"complete","S2":"running"},"plan_sha256":"set"}'
DISK_IMP_DRAINED='{"phase":"implement","receipts":{"S1":"complete","S2":"complete"},"plan_sha256":"set"}'

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/shiploop-walk-journal.XXXXXX")"
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

planf="$tmpdir/bound.plan.md"
setup_bound_plan "$planf"

# =============================================================================
# L — linear complete walk (each dest/complete is its own CASE)
# =============================================================================
runL="$tmpdir/L/.shiploop"
repoL="$tmpdir/L/repo"
init_git_repo "$repoL"

printf 'CASE L0 INVOKE: shiploop init (no prior run dir)\n'
invoke_script init --prompt "create result.txt containing exactly one line: ok" \
  --run-dir "$runL" --bound-plan "$planf" --repo "$repoL"
assert_rc 0 "L0"
assert_out_has "initialized" "L0 RETURN"
assert_next_has "Write the original user ask" "L0 RETURN"
assert_next_lacks "/goal step S1:" "L0 RETURN"
assert_no_walk "L0 RETURN"
assert_disk "$runL" "L0 DISK" "$DISK_INTAKE"

printf 'CASE L1 PRE: intake, prompt.md only; INVOKE: complete dest validate-spec\n'
assert_disk "$runL" "L1 PRE" "$DISK_INTAKE"
invoke_script complete --run-dir "$runL"
assert_rc 0 "L1"
assert_out_has "updated -> validate-spec" "L1 RETURN"
assert_next_has "Survey, then practices, then spec" "L1 RETURN"
assert_next_lacks "/goal step S1:" "L1 RETURN"
assert_no_walk "L1 RETURN"
assert_disk "$runL" "L1 DISK" "$DISK_VS"

printf 'CASE L2 PRE: validate-spec + host wrote env/spec; INVOKE: complete dest plan\n'
write_environment "$runL"
write_spec "$runL"
assert_disk "$runL" "L2 PRE" '{"phase":"validate-spec","files":{"spec.md":true,"environment.md":true},"spec_sha256":"empty"}'
invoke_script complete --run-dir "$runL"
assert_rc 0 "L2"
assert_out_has "updated -> plan" "L2 RETURN"
assert_next_has "The spec is **frozen**" "L2 RETURN"
assert_next_lacks "/goal step S1:" "L2 RETURN"
assert_no_walk "L2 RETURN"
assert_disk "$runL" "L2 DISK" "$DISK_PLAN"

printf 'CASE L3 PRE: plan + host wrote DAG; INVOKE: complete dest implement + claim S1\n'
install_dag "$runL" linear.json
assert_disk "$runL" "L3 PRE" '{"phase":"plan","files":{"backchain/plan.json":true,"plan.md":true},"plan_sha256":"empty","receipts":{"S1":"none","S2":"none"}}'
invoke_script complete --run-dir "$runL"
assert_rc 0 "L3"
assert_out_has "updated -> implement" "L3 RETURN"
assert_walk_journal "$runL" "L3 RETURN walk"
assert_out_has "▶ S1  write the file" "L3 RETURN"
assert_out_has "○ S2  confirm the file" "L3 RETURN"
assert_out_has "waiting on S1 write the file" "L3 RETURN"
assert_next_has "$S1_LINEAR" "L3 RETURN"
assert_next_lacks "$S2_LINEAR" "L3 RETURN"
assert_disk "$runL" "L3 DISK" "$DISK_IMP_S1RUN"
invoke_script status --run-dir "$runL" --human
assert_rc 0 "L3 status --human"
assert_walk_journal "$runL" "L3 status --human walk"
assert_out_has "▶ S1  write the file" "L3 status --human"
plan_hash_L3="$(python3 -c "import hashlib,pathlib; print(hashlib.sha256(pathlib.Path('$runL/plan.md').read_bytes()).hexdigest())")"

printf 'CASE L4 PRE: S1 running (host landed); INVOKE: complete → S1 done, claim S2\n'
assert_disk "$runL" "L4 PRE before land" "$DISK_IMP_S1RUN"
host_land "$runL" S1
assert_disk "$runL" "L4 PRE after host land (receipt still running)" "$DISK_IMP_S1RUN"
invoke_script complete --run-dir "$runL"
assert_rc 0 "L4"
assert_out_has "completed S1" "L4 RETURN"
assert_walk_journal "$runL" "L4 RETURN walk"
assert_out_has "● S1  write the file" "L4 RETURN"
assert_out_has "▶ S2  confirm the file" "L4 RETURN"
assert_next_has "$S2_LINEAR" "L4 RETURN"
assert_next_lacks "$S1_LINEAR" "L4 RETURN"
assert_disk "$runL" "L4 DISK" "$DISK_IMP_S1DONE"
assert_plan_md_unchanged "$runL" "$plan_hash_L3" "L4 DISK plan.md"

printf 'CASE L5 PRE: S2 running (host landed); INVOKE: complete → drained\n'
assert_disk "$runL" "L5 PRE before land" "$DISK_IMP_S1DONE"
host_land "$runL" S2
invoke_script complete --run-dir "$runL"
assert_rc 0 "L5"
assert_out_has "completed S2" "L5 RETURN"
assert_walk_journal "$runL" "L5 RETURN walk"
assert_out_has "● S1  write the file" "L5 RETURN"
assert_out_has "● S2  confirm the file" "L5 RETURN"
assert_next_has "Session steps are drained" "L5 RETURN"
assert_next_lacks "/goal " "L5 RETURN"
assert_disk "$runL" "L5 DISK" "$DISK_IMP_DRAINED"
assert_plan_md_unchanged "$runL" "$plan_hash_L3" "L5 DISK plan.md"

printf 'CASE L6 PRE: implement drained; INVOKE: complete dest residual\n'
assert_disk "$runL" "L6 PRE" "$DISK_IMP_DRAINED"
invoke_script complete --run-dir "$runL"
assert_rc 0 "L6"
assert_out_has "updated implement -> residual" "L6 RETURN"
assert_no_walk "L6 RETURN"
assert_next_has "Review-coverage is **waived**" "L6 RETURN"
assert_next_lacks "/goal step S" "L6 RETURN"
assert_disk "$runL" "L6 DISK" '{"phase":"residual","receipts":{"S1":"complete","S2":"complete"}}'
printf 'LAYER: L linear complete-walk OK\n'

# =============================================================================
# N — reprint: next does not mutate disk
# =============================================================================
runN="$tmpdir/N/.shiploop"
repoN="$tmpdir/N/repo"
setup_to_implement "$runN" "$repoN" "$planf" linear.json

printf 'CASE N1 PRE: S1 running; INVOKE: next (reprint, In flight)\n'
assert_disk "$runN" "N1 PRE" "$DISK_IMP_S1RUN"
invoke_script next --run-dir "$runN"
assert_rc 0 "N1"
assert_walk_journal "$runN" "N1 RETURN walk"
assert_next_has "$S1_LINEAR" "N1 RETURN"
assert_next_has "In flight — do not open a second /goal" "N1 RETURN"
assert_disk "$runN" "N1 DISK (unchanged)" "$DISK_IMP_S1RUN"

printf 'CASE N2 PRE: S1 complete S2 running; INVOKE: next reprint\n'
host_land "$runN" S1
invoke_script complete --run-dir "$runN"
assert_rc 0 "N2 setup complete S1"
assert_disk "$runN" "N2 PRE" "$DISK_IMP_S1DONE"
invoke_script next --run-dir "$runN"
assert_rc 0 "N2"
assert_walk_journal "$runN" "N2 RETURN walk"
assert_out_has "● S1  write the file" "N2 RETURN"
assert_next_has "$S2_LINEAR" "N2 RETURN"
assert_next_has "In flight — do not open a second /goal" "N2 RETURN"
assert_next_lacks "$S1_LINEAR" "N2 RETURN"
assert_disk "$runN" "N2 DISK (unchanged)" "$DISK_IMP_S1DONE"

printf 'CASE N3 PRE: drained; INVOKE: next reprint\n'
host_land "$runN" S2
invoke_script complete --run-dir "$runN"
assert_rc 0 "N3 setup complete S2"
assert_disk "$runN" "N3 PRE" "$DISK_IMP_DRAINED"
invoke_script next --run-dir "$runN"
assert_rc 0 "N3"
assert_walk_journal "$runN" "N3 RETURN walk"
assert_next_has "Session steps are drained" "N3 RETURN"
assert_next_lacks "/goal " "N3 RETURN"
assert_disk "$runN" "N3 DISK (unchanged)" "$DISK_IMP_DRAINED"
printf 'LAYER: N reprint OK\n'

# =============================================================================
# D — illegal skip / repeat (complete-step override, no packet)
# =============================================================================
runD="$tmpdir/D/.shiploop"
repoD="$tmpdir/D/repo"
setup_to_implement "$runD" "$repoD" "$planf" linear.json

printf 'CASE D1 PRE: S1 running S2 none; INVOKE: complete-step --id S2 (skip)\n'
assert_disk "$runD" "D1 PRE" "$DISK_IMP_S1RUN"
invoke_script complete-step --run-dir "$runD" --id S2
assert_rc 2 "D1"
assert_err_has "not running|suppliers" "D1 RETURN"
assert_disk "$runD" "D1 DISK (unchanged)" "$DISK_IMP_S1RUN"

printf 'CASE D2 PRE: S1 complete; INVOKE: complete-step --id S1 (repeat)\n'
host_land "$runD" S1
invoke_script complete --run-dir "$runD"
assert_rc 0 "D2 setup"
assert_disk "$runD" "D2 PRE" "$DISK_IMP_S1DONE"
invoke_script complete-step --run-dir "$runD" --id S1
assert_rc 2 "D2"
assert_err_has "already complete" "D2 RETURN"
assert_disk "$runD" "D2 DISK (unchanged)" "$DISK_IMP_S1DONE"
printf 'LAYER: D illegal skip/repeat OK\n'

# =============================================================================
# C — clear retry / ancestor restart
# =============================================================================
runC1="$tmpdir/C1/.shiploop"
repoC1="$tmpdir/C1/repo"
setup_to_implement "$runC1" "$repoC1" "$planf" linear.json

printf 'CASE C1 PRE: S1 running; INVOKE: complete --clear (re-claim S1)\n'
assert_disk "$runC1" "C1 PRE" "$DISK_IMP_S1RUN"
invoke_script complete --run-dir "$runC1" --clear
assert_rc 0 "C1"
assert_out_has "cleared S1" "C1 RETURN"
assert_walk_journal "$runC1" "C1 RETURN walk"
assert_out_has "▶ S1  write the file" "C1 RETURN"
assert_next_has "$S1_LINEAR" "C1 RETURN"
assert_out_lacks "In flight — do not open a second /goal" "C1 RETURN"
assert_disk "$runC1" "C1 DISK" "$DISK_IMP_S1RUN"

runC2="$tmpdir/C2/.shiploop"
repoC2="$tmpdir/C2/repo"
setup_to_implement "$runC2" "$repoC2" "$planf" linear.json
host_land "$runC2" S1
invoke_script complete --run-dir "$runC2"
assert_rc 0 "C2 setup"

printf 'CASE C2 PRE: S1 complete S2 running; INVOKE: clear-step S1 then next\n'
assert_disk "$runC2" "C2 PRE" "$DISK_IMP_S1DONE"
invoke_script clear-step --run-dir "$runC2" --id S1
assert_rc 0 "C2 clear-step"
assert_out_has "cleared S1" "C2 clear-step RETURN"
assert_disk "$runC2" "C2 DISK after clear-step (no receipts)" \
  '{"phase":"implement","receipts":{"S1":"none","S2":"none"}}'
invoke_script next --run-dir "$runC2"
assert_rc 0 "C2 next"
assert_walk_journal "$runC2" "C2 next RETURN walk"
assert_out_has "▶ S1  write the file" "C2 next RETURN"
assert_out_has "○ S2  confirm the file" "C2 next RETURN"
assert_next_has "$S1_LINEAR" "C2 next RETURN"
assert_next_lacks "$S2_LINEAR" "C2 next RETURN"
assert_disk "$runC2" "C2 DISK after next" "$DISK_IMP_S1RUN"
printf 'LAYER: C clear retry OK\n'

# =============================================================================
# P — two-root parallel
# =============================================================================
runP="$tmpdir/P/.shiploop"
repoP="$tmpdir/P/repo"
setup_to_implement "$runP" "$repoP" "$planf" two-root.json

printf 'CASE P1 PRE: dest implement claimed both roots; RETURN already in LAST_* from setup\n'
assert_disk "$runP" "P1 DISK" '{"phase":"implement","receipts":{"S1":"running","S2":"running"},"plan_sha256":"set"}'
assert_walk_journal "$runP" "P1 RETURN walk"
assert_out_has "▶ S1  write tests for the file" "P1 RETURN"
assert_out_has "▶ S2  write the implementation" "P1 RETURN"
assert_next_has "$S1_TWOROOT" "P1 RETURN"
assert_next_has "$S2_TWOROOT" "P1 RETURN"
n_goals="$(printf '%s\n' "$LAST_OUT" | grep -c '^/goal step ' || true)"
[[ "$n_goals" -eq 2 ]] || fail "P1 RETURN want two /goal step lines: $n_goals"

printf 'CASE P3 PRE: both running; INVOKE: complete without --id\n'
assert_disk "$runP" "P3 PRE" '{"phase":"implement","receipts":{"S1":"running","S2":"running"}}'
invoke_script complete --run-dir "$runP"
assert_rc 2 "P3"
assert_err_has "multiple running" "P3 RETURN"
assert_disk "$runP" "P3 DISK (unchanged)" '{"phase":"implement","receipts":{"S1":"running","S2":"running"}}'

printf 'CASE P2 PRE: both running, S1 host-landed; INVOKE: complete --id S1\n'
host_land "$runP" S1
assert_disk "$runP" "P2 PRE" '{"phase":"implement","receipts":{"S1":"running","S2":"running"}}'
invoke_script complete --run-dir "$runP" --id S1
assert_rc 0 "P2"
assert_out_has "completed S1" "P2 RETURN"
assert_walk_journal "$runP" "P2 RETURN walk"
assert_out_has "● S1  write tests for the file" "P2 RETURN"
assert_out_has "▶ S2  write the implementation" "P2 RETURN"
assert_next_has "$S2_TWOROOT" "P2 RETURN"
assert_next_has "In flight — do not open a second /goal" "P2 RETURN"
assert_next_lacks "$S1_TWOROOT" "P2 RETURN"
assert_disk "$runP" "P2 DISK" '{"phase":"implement","receipts":{"S1":"complete","S2":"running"}}'
printf 'LAYER: P parallel OK\n'

# =============================================================================
# I — inject
# =============================================================================
runI1="$tmpdir/I1/.shiploop"
repoI1="$tmpdir/I1/repo"
setup_to_implement "$runI1" "$repoI1" "$planf" linear.json

printf 'CASE I1 PRE: S1 running; INVOKE: inject-step S3 --before S2, then next\n'
assert_disk "$runI1" "I1 PRE" "$DISK_IMP_S1RUN"
invoke_script inject-step --run-dir "$runI1" --statement "mid bind" \
  --prompt "/goal injected mid bind" --produces "mid exists" --before S2 --id S3
assert_rc 0 "I1 inject"
assert_out_has "injected S3" "I1 inject RETURN"
assert_disk "$runI1" "I1 DISK after inject (S3 not claimed)" \
  '{"phase":"implement","receipts":{"S1":"running","S2":"none","S3":"none"}}'
invoke_script next --run-dir "$runI1"
assert_rc 0 "I1 next"
assert_walk_journal "$runI1" "I1 next RETURN walk"
assert_out_has "▶ S3  mid bind" "I1 next RETURN"
assert_next_has "$S1_LINEAR" "I1 next RETURN"
assert_next_has "/goal injected mid bind" "I1 next RETURN"
assert_disk "$runI1" "I1 DISK after next" \
  '{"phase":"implement","receipts":{"S1":"running","S2":"none","S3":"running"}}'

runI2="$tmpdir/I2/.shiploop"
repoI2="$tmpdir/I2/repo"
setup_to_implement "$runI2" "$repoI2" "$planf" linear.json
host_land "$runI2" S1
invoke_script complete --run-dir "$runI2"
assert_rc 0 "I2 setup"

printf 'CASE I2 PRE: S2 running; INVOKE: inject --before S2 (refused)\n'
assert_disk "$runI2" "I2 PRE" "$DISK_IMP_S1DONE"
invoke_script inject-step --run-dir "$runI2" --statement "mid" \
  --prompt "/goal injected after S1" --produces "mid exists" --from S1 --before S2 --id S3
assert_rc 2 "I2"
assert_err_has "todo or ready" "I2 RETURN"
python3 - "$runI2" <<'PY' || fail "I2 DISK DAG grew"
import json, sys
from pathlib import Path
ids = [s["id"] for s in json.loads((Path(sys.argv[1]) / "backchain" / "plan.json").read_text())["steps"]]
assert ids == ["S1", "S2"], ids
PY
assert_disk "$runI2" "I2 DISK (unchanged)" "$DISK_IMP_S1DONE"
printf 'LAYER: I inject OK\n'

# =============================================================================
# B — blocked resume implement
# =============================================================================
runB="$tmpdir/B/.shiploop"
repoB="$tmpdir/B/repo"
setup_to_implement "$runB" "$repoB" "$planf" linear.json

printf 'CASE B1a PRE: S1 running; INVOKE: update --to blocked\n'
assert_disk "$runB" "B1a PRE" "$DISK_IMP_S1RUN"
invoke_script update --run-dir "$runB" --to blocked --resume-to implement --reason "host failed"
assert_rc 0 "B1a"
assert_out_has "updated implement -> blocked" "B1a RETURN"
assert_disk "$runB" "B1a DISK" \
  '{"phase":"blocked","resume_to":"implement","blocked_from":"implement","receipts":{"S1":"running"}}'

printf 'CASE B1b PRE: blocked resume_to=implement; INVOKE: complete --reason\n'
assert_disk "$runB" "B1b PRE" '{"phase":"blocked","resume_to":"implement"}'
invoke_script complete --run-dir "$runB" --reason "resume"
assert_rc 0 "B1b"
assert_out_has "updated -> implement" "B1b RETURN"
assert_walk_journal "$runB" "B1b RETURN walk"
assert_out_has "▶ S1  write the file" "B1b RETURN"
assert_out_lacks "● S1" "B1b RETURN"
assert_next_has "$S1_LINEAR" "B1b RETURN"
assert_disk "$runB" "B1b DISK" '{"phase":"implement","receipts":{"S1":"running","S2":"none"},"resume_to":null}'
printf 'LAYER: B blocked resume OK\n'

# =============================================================================
# H — hash-mismatch complete is not ●
# =============================================================================
runH="$tmpdir/H/.shiploop"
repoH="$tmpdir/H/repo"
setup_to_implement "$runH" "$repoH" "$planf" linear.json
host_land "$runH" S1
invoke_script complete --run-dir "$runH"
assert_rc 0 "H setup"

printf 'CASE H1 PRE: S1 complete then tamper plan_sha256; INVOKE: status --human, then next\n'
assert_disk "$runH" "H1 PRE before tamper" "$DISK_IMP_S1DONE"
python3 - "$runH" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1]) / "steps" / "S1.json"
rec = json.loads(p.read_text())
rec["plan_sha256"] = "deadbeef"
p.write_text(json.dumps(rec, indent=2) + "\n")
PY
invoke_script status --run-dir "$runH" --human
assert_rc 0 "H1 status"
assert_walk_journal "$runH" "H1 status RETURN walk"
assert_out_lacks "● S1" "H1 status RETURN"
assert_out_has "S1: ready" "H1 status RETURN"
invoke_script next --run-dir "$runH"
assert_rc 2 "H1 next"
assert_err_has "already exists|worktree add failed" "H1 next RETURN"
printf 'LAYER: H hash-mismatch OK\n'

# =============================================================================
# F — replan wipes receipts
# =============================================================================
runF="$tmpdir/F/.shiploop"
repoF="$tmpdir/F/repo"
setup_to_implement "$runF" "$repoF" "$planf" linear.json
host_land "$runF" S1
invoke_script complete --run-dir "$runF"
assert_rc 0 "F setup"

printf 'CASE F1a PRE: S1 complete S2 running; INVOKE: complete --blocked --resume-to plan\n'
assert_disk "$runF" "F1a PRE" "$DISK_IMP_S1DONE"
invoke_script complete --run-dir "$runF" --blocked --reason "replan" --resume-to plan
assert_rc 0 "F1a"
assert_out_has "updated -> blocked" "F1a RETURN"
assert_disk "$runF" "F1a DISK" '{"phase":"blocked","resume_to":"plan","receipts":{"S1":"complete","S2":"running"}}'

printf 'CASE F1b PRE: blocked→plan; INVOKE: complete --reason (dest plan clears receipts)\n'
invoke_script complete --run-dir "$runF" --reason "replan"
assert_rc 0 "F1b"
assert_out_has "updated -> plan" "F1b RETURN"
assert_disk "$runF" "F1b DISK" \
  '{"phase":"plan","receipts":{"S1":"none","S2":"none"},"plan_sha256":"empty"}'

printf 'CASE F1c PRE: plan, re-install DAG; INVOKE: complete dest implement\n'
install_dag "$runF" linear.json
assert_disk "$runF" "F1c PRE" '{"phase":"plan","files":{"backchain/plan.json":true},"plan_sha256":"empty"}'
invoke_script complete --run-dir "$runF"
assert_rc 0 "F1c"
assert_out_has "updated -> implement" "F1c RETURN"
assert_walk_journal "$runF" "F1c RETURN walk"
assert_out_has "▶ S1  write the file" "F1c RETURN"
assert_out_lacks "● S1" "F1c RETURN"
assert_next_has "$S1_LINEAR" "F1c RETURN"
assert_disk "$runF" "F1c DISK" "$DISK_IMP_S1RUN"
printf 'LAYER: F replan wipe OK\n'

printf 'shiploop-walk-journal.test.sh: PASS\n'
