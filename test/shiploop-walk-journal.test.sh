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
TRANS="$fix/transitions/artifacts"
export SHIPLOOP_BACKCHAIN_ROOT="$fix/backchain-leaf"

fail() {
  printf 'shiploop-walk-journal.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

DS='result.txt contains exactly one line: ok'
UNTIL_HEAD='Do this activity until these conditions are met:'
S1_LINEAR='- result.txt exists'
S2_LINEAR='- result.txt validated'
S1_TWOROOT='- tests exist'
S2_TWOROOT='- result.txt exists'

LAST_RC=0
LAST_OUT=""
LAST_ERR=""

packet_section() {
  local out="$1" start="$2" stop="${3:-}"
  printf '%s\n' "$out" | awk -v s="$start" -v e="$stop" '
    $0==s {p=1; next}
    p && e != "" && $0==e {exit}
    p && e == "" && /^## / {exit}
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
  packet_section "$LAST_OUT" "## Next prompt" "## When done invoke" | grep -Fq -- "$needle" \
    || fail "$msg: Next prompt missing ${needle}"
}

assert_next_lacks() {
  local needle="$1" msg="$2"
  if packet_section "$LAST_OUT" "## Next prompt" "## When done invoke" | grep -Fq -- "$needle"; then
    fail "$msg: Next prompt has ${needle}"
  fi
}

# Successful packet: dest/event line + Next body (the transition return value).
assert_transition_return() {
  local dest_line="$1" next_needle="$2" msg="$3"
  assert_rc 0 "$msg"
  printf '%s\n' "$LAST_OUT" | grep -Fxq -- "$dest_line" \
    || fail "$msg: dest line missing exact ${dest_line}"
  assert_next_has "$next_needle" "$msg"
  packet_section "$LAST_OUT" "## Next prompt" "## When done invoke" \
    | grep -Fxq 'Use this prompt as much as possible.' \
    || fail "$msg: Next missing first-line Use this prompt"
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

copy_artifact() {
  local dest="$1" name="$2"
  cp "$TRANS/$name" "$dest"
}

write_spec() {
  copy_artifact "$1/spec.md" spec-checkable.md
  rm -f "$1/spec.json"
}

write_uncheckable_spec() {
  copy_artifact "$1/spec.md" spec-uncheckable.md
  rm -f "$1/spec.json"
}

write_environment() {
  copy_artifact "$1/environment.md" environment.md
}

write_plan_md() {
  copy_artifact "$1/plan.md" plan.md
}

install_dag() {
  local run="$1" fixture="$2"
  mkdir -p "$run/backchain"
  cp "$fix/$fixture" "$run/backchain/plan.json"
  write_plan_md "$run"
}

install_ledger() {
  local repo="$1" name="$2" planf="$3"
  local hash
  hash="$(python3 -c "import hashlib,pathlib; print(hashlib.sha256(pathlib.Path('$planf').read_bytes()).hexdigest())")"
  python3 - "$TRANS/ledger-${name}.md" "$repo/REVIEW_CONVERGE.md" "$planf" "$hash" <<'PY'
from pathlib import Path
import sys
text = Path(sys.argv[1]).read_text(encoding="utf-8")
text = text.replace("__PLAN_CONTRACT__", sys.argv[3]).replace("__PLAN_HASH__", sys.argv[4])
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
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
  copy_artifact "$1" bound-waived.md
}

setup_bound_coverage() {
  copy_artifact "$1" bound-coverage.md
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

setup_to_residual() {
  setup_to_implement "$1" "$2" "$3" "${4:-linear.json}"
  host_land "$1" S1
  invoke_script complete --run-dir "$1"
  assert_rc 0 "setup complete S1"
  host_land "$1" S2
  invoke_script complete --run-dir "$1"
  assert_rc 0 "setup complete S2"
  invoke_script complete --run-dir "$1"
  assert_rc 0 "setup dest residual"
}

assert_index_covers_edges() {
  python3 - "$root/skills/shiploop/references/transitions.json" \
    "$fix/transitions/INDEX.md" <<'PY' || fail "INDEX missing transitions.json edges"
import json, sys
from pathlib import Path
edges = json.loads(Path(sys.argv[1]).read_text())["edges"]
index = Path(sys.argv[2]).read_text()
missing = []
for e in edges:
    needle = f"| {e['from']} | {e['to']} |"
    if needle not in index:
        missing.append(needle)
if missing:
    sys.exit("INDEX.md missing rows: " + "; ".join(missing))
PY
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

[[ -f "$fix/transitions/INDEX.md" ]] || fail "missing transitions/INDEX.md"
[[ -d "$TRANS" ]] || fail "missing transitions/artifacts"
assert_index_covers_edges

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
assert_next_has "$UNTIL_HEAD" "L3 RETURN"
assert_next_has "$S1_LINEAR" "L3 RETURN"
assert_next_lacks "$S2_LINEAR" "L3 RETURN"
assert_next_has "Use this prompt as much as possible." "L3 RETURN"
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
n_goals="$(packet_section "$LAST_OUT" "## Next prompt" "## When done invoke" | grep -c '^/goal$' || true)"
[[ "$n_goals" -eq 2 ]] || fail "P1 RETURN want two /goal lines: $n_goals"

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
  --prompt $'/goal\nDo this activity until these conditions are met:\n- mid exists' \
  --produces "mid exists" --before S2 --id S3
assert_rc 0 "I1 inject"
assert_out_has "injected S3" "I1 inject RETURN"
assert_disk "$runI1" "I1 DISK after inject (S3 not claimed)" \
  '{"phase":"implement","receipts":{"S1":"running","S2":"none","S3":"none"}}'
invoke_script next --run-dir "$runI1"
assert_rc 0 "I1 next"
assert_walk_journal "$runI1" "I1 next RETURN walk"
assert_out_has "▶ S3  mid bind" "I1 next RETURN"
assert_next_has "$S1_LINEAR" "I1 next RETURN"
assert_next_has "$UNTIL_HEAD" "I1 next RETURN"
assert_next_has "- mid exists" "I1 next RETURN"
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
assert_next_has "Stop and ask the user" "B1a RETURN"
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
assert_next_has "Stop and ask the user" "F1a RETURN"
assert_disk "$runF" "F1a DISK" '{"phase":"blocked","resume_to":"plan","receipts":{"S1":"complete","S2":"running"}}'

printf 'CASE F1b PRE: blocked→plan; INVOKE: complete --reason (dest plan clears receipts)\n'
invoke_script complete --run-dir "$runF" --reason "replan"
assert_rc 0 "F1b"
assert_out_has "updated -> plan" "F1b RETURN"
assert_next_has "The spec is **frozen**" "F1b RETURN"
assert_next_lacks "$S1_LINEAR" "F1b RETURN"
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

# =============================================================================
# V — validate-spec ↔ blocked (uncheckable spec artifact, independent folder)
# =============================================================================
runV="$tmpdir/V/.shiploop"
repoV="$tmpdir/V/repo"
init_git_repo "$repoV"
invoke_script init --prompt "create result.txt containing exactly one line: ok" \
  --run-dir "$runV" --bound-plan "$planf" --repo "$repoV"
assert_rc 0 "V setup init"
invoke_script complete --run-dir "$runV"
assert_rc 0 "V setup dest validate-spec"

printf 'CASE V1 PRE: validate-spec + spec-uncheckable.md (no env); INVOKE: complete --blocked\n'
write_uncheckable_spec "$runV"
assert_disk "$runV" "V1 PRE" \
  '{"phase":"validate-spec","files":{"spec.md":true,"environment.md":false}}'
invoke_script complete --run-dir "$runV" --blocked --reason "what is the oracle?" \
  --resume-to validate-spec
assert_rc 0 "V1"
assert_out_has "updated -> blocked" "V1 RETURN"
assert_next_has "Stop and ask the user" "V1 RETURN"
assert_disk "$runV" "V1 DISK" \
  '{"phase":"blocked","resume_to":"validate-spec","blocked_from":"validate-spec","files":{"spec.md":true,"environment.md":false}}'

printf 'CASE V2 PRE: blocked resume_to=validate-spec; INVOKE: complete --reason\n'
assert_disk "$runV" "V2 PRE" '{"phase":"blocked","resume_to":"validate-spec"}'
invoke_script complete --run-dir "$runV" --reason "user answered"
assert_rc 0 "V2"
assert_out_has "updated -> validate-spec" "V2 RETURN"
assert_next_has "Survey, then practices, then spec" "V2 RETURN"
assert_disk "$runV" "V2 DISK" \
  '{"phase":"validate-spec","resume_to":null,"spec_sha256":"empty","plan_sha256":"empty"}'
printf 'LAYER: V validate-spec blocked hatch OK\n'

# =============================================================================
# Q — plan → blocked (independent folder, no DAG)
# =============================================================================
runQ="$tmpdir/Q/.shiploop"
repoQ="$tmpdir/Q/repo"
init_git_repo "$repoQ"
invoke_script init --prompt "create result.txt containing exactly one line: ok" \
  --run-dir "$runQ" --bound-plan "$planf" --repo "$repoQ"
assert_rc 0 "Q setup init"
invoke_script complete --run-dir "$runQ"
assert_rc 0 "Q setup dest vs"
write_environment "$runQ"
write_spec "$runQ"
invoke_script complete --run-dir "$runQ"
assert_rc 0 "Q setup dest plan"

printf 'CASE Q1 PRE: plan, no DAG; INVOKE: complete --blocked --resume-to plan\n'
assert_disk "$runQ" "Q1 PRE" "$DISK_PLAN"
invoke_script complete --run-dir "$runQ" --blocked --reason "no backchain checkout" \
  --resume-to plan
assert_rc 0 "Q1"
assert_out_has "updated -> blocked" "Q1 RETURN"
assert_next_has "Stop and ask the user" "Q1 RETURN"
assert_disk "$runQ" "Q1 DISK" \
  '{"phase":"blocked","resume_to":"plan","blocked_from":"plan","files":{"backchain/plan.json":false}}'
printf 'LAYER: Q plan-to-blocked OK\n'

# =============================================================================
# G — residual → done (waiver artifact, independent folder)
# =============================================================================
runG="$tmpdir/G/.shiploop"
repoG="$tmpdir/G/repo"
setup_to_residual "$runG" "$repoG" "$planf" linear.json

printf 'CASE G1 PRE: residual, waived bound plan, no recap; INVOKE: complete dest done\n'
assert_disk "$runG" "G1 PRE" \
  '{"phase":"residual","receipts":{"S1":"complete","S2":"complete"},"files":{"recap.html":false},"terminal":null}'
invoke_script complete --run-dir "$runG"
assert_rc 0 "G1"
assert_out_has "updated -> done" "G1 RETURN"
assert_next_has "Session closed" "G1 RETURN"
assert_out_has "recap.html" "G1 RETURN Look here"
assert_disk "$runG" "G1 DISK" \
  '{"phase":"done","terminal":"waived","files":{"recap.html":true},"receipts":{"S1":"complete","S2":"complete"}}'
grep -q 'writer: shiploop.recap' "$runG/recap.html" || fail "G1 DISK recap missing writer stamp"
printf 'LAYER: G residual-to-done waiver OK\n'

# =============================================================================
# K — residual → done via ledger-complete.md (no waiver, independent folder)
# =============================================================================
planK="$tmpdir/K.bound.md"
setup_bound_coverage "$planK"
runK="$tmpdir/K/.shiploop"
repoK="$tmpdir/K/repo"
setup_to_residual "$runK" "$repoK" "$planK" linear.json

printf 'CASE K0 PRE: residual, bound-coverage, no ledger; INVOKE: next (Phase B Next)\n'
assert_disk "$runK" "K0 PRE" '{"phase":"residual","terminal":null}'
invoke_script next --run-dir "$runK"
assert_rc 0 "K0"
assert_next_has "run review-coverage Phase B" "K0 RETURN"
assert_next_lacks "Review-coverage is **waived**" "K0 RETURN"
assert_disk "$runK" "K0 DISK (unchanged)" '{"phase":"residual"}'

printf 'CASE K1 PRE: residual, bound-coverage + ledger-complete; INVOKE: complete dest done\n'
assert_disk "$runK" "K1 PRE" '{"phase":"residual","terminal":null,"files":{"recap.html":false}}'
install_ledger "$repoK" complete "$planK"
[[ -f "$repoK/REVIEW_CONVERGE.md" ]] || fail "K1 PRE missing ledger"
invoke_script complete --run-dir "$runK"
assert_rc 0 "K1"
assert_out_has "updated -> done" "K1 RETURN"
assert_next_has "Session closed" "K1 RETURN"
assert_disk "$runK" "K1 DISK" \
  '{"phase":"done","terminal":"success","files":{"recap.html":true}}'
grep -q 'review-coverage complete and landed' "$runK/recap.html" \
  || fail "K1 DISK recap missing complete-and-landed"
printf 'LAYER: K residual-to-done ledger OK\n'

# =============================================================================
# T — residual → halted via ledger-stopped.md (independent folder)
# =============================================================================
planT="$tmpdir/T.bound.md"
setup_bound_coverage "$planT"
runT="$tmpdir/T/.shiploop"
repoT="$tmpdir/T/repo"
setup_to_residual "$runT" "$repoT" "$planT" linear.json

printf 'CASE T1 PRE: residual, ledger-stopped; INVOKE: complete dest halted\n'
assert_disk "$runT" "T1 PRE" '{"phase":"residual","terminal":null}'
install_ledger "$repoT" stopped "$planT"
invoke_script complete --run-dir "$runT"
assert_rc 0 "T1"
assert_out_has "updated -> halted" "T1 RETURN"
assert_next_has "Session terminal: halted" "T1 RETURN"
assert_disk "$runT" "T1 DISK" \
  '{"phase":"halted","terminal":"halted","files":{"recap.html":true}}'
grep -q 'HALTED' "$runT/recap.html" || fail "T1 DISK recap missing HALTED"
printf 'LAYER: T residual-to-halted OK\n'

# =============================================================================
# R — residual → blocked → residual (independent folder)
# =============================================================================
runR="$tmpdir/R/.shiploop"
repoR="$tmpdir/R/repo"
setup_to_residual "$runR" "$repoR" "$planf" linear.json

printf 'CASE R1 PRE: residual; INVOKE: complete --blocked --resume-to residual\n'
assert_disk "$runR" "R1 PRE" '{"phase":"residual","receipts":{"S1":"complete","S2":"complete"}}'
invoke_script complete --run-dir "$runR" --blocked --reason "not green" --resume-to residual
assert_rc 0 "R1"
assert_out_has "updated -> blocked" "R1 RETURN"
assert_next_has "Stop and ask the user" "R1 RETURN"
assert_disk "$runR" "R1 DISK" \
  '{"phase":"blocked","resume_to":"residual","blocked_from":"residual","receipts":{"S1":"complete","S2":"complete"}}'

printf 'CASE R2 PRE: blocked resume_to=residual, steps drained; INVOKE: complete --reason\n'
assert_disk "$runR" "R2 PRE" '{"phase":"blocked","resume_to":"residual"}'
invoke_script complete --run-dir "$runR" --reason "suite green"
assert_rc 0 "R2"
assert_out_has "updated -> residual" "R2 RETURN"
assert_next_has "Review-coverage is **waived**" "R2 RETURN"
assert_disk "$runR" "R2 DISK" \
  '{"phase":"residual","resume_to":null,"receipts":{"S1":"complete","S2":"complete"}}'
printf 'LAYER: R residual blocked resume OK\n'

# =============================================================================
# X — illegal edges (independent folders)
# =============================================================================
runX1="$tmpdir/X1/.shiploop"
repoX1="$tmpdir/X1/repo"
init_git_repo "$repoX1"
invoke_script init --prompt "create result.txt containing exactly one line: ok" \
  --run-dir "$runX1" --bound-plan "$planf" --repo "$repoX1"
assert_rc 0 "X1 setup"

printf 'CASE X1 PRE: intake; INVOKE: complete --blocked (illegal)\n'
assert_disk "$runX1" "X1 PRE" '{"phase":"intake"}'
invoke_script complete --run-dir "$runX1" --blocked --reason "no" --resume-to validate-spec
assert_rc 2 "X1"
assert_err_has "illegal transition" "X1 RETURN"
assert_disk "$runX1" "X1 DISK (unchanged)" '{"phase":"intake"}'

runX2="$tmpdir/X2/.shiploop"
repoX2="$tmpdir/X2/repo"
setup_to_implement "$runX2" "$repoX2" "$planf" linear.json

printf 'CASE X2 PRE: implement mid-walk; INVOKE: update --to done (illegal)\n'
assert_disk "$runX2" "X2 PRE" "$DISK_IMP_S1RUN"
invoke_script update --run-dir "$runX2" --to done
assert_rc 2 "X2"
assert_err_has "illegal transition" "X2 RETURN"
assert_disk "$runX2" "X2 DISK (unchanged)" "$DISK_IMP_S1RUN"
printf 'LAYER: X illegal edges OK\n'

# =============================================================================
# U — setup-once: original ask mentions new repo; S1 prompt must not
# =============================================================================
runU="$tmpdir/U/.shiploop"
repoU="$tmpdir/U/repo"
init_git_repo "$repoU"
invoke_script init --prompt "in a new repo, write result.txt" \
  --run-dir "$runU" --bound-plan "$planf" --repo "$repoU"
assert_rc 0 "U setup init"
invoke_script complete --run-dir "$runU"
assert_rc 0 "U setup vs"
write_environment "$runU"
printf 'done_sentence: in a new repo, result.txt contains exactly one line: ok\ncheckable: true\n' \
  >"$runU/spec.md"
invoke_script complete --run-dir "$runU"
assert_rc 0 "U setup plan"
install_dag "$runU" setup-once.json
printf 'done_sentence: in a new repo, result.txt contains exactly one line: ok\n' >"$runU/plan.md"

printf 'CASE U1 PRE: plan + setup-once.json; INVOKE: complete dest implement\n'
invoke_script complete --run-dir "$runU"
assert_rc 0 "U1"
assert_out_has "updated -> implement" "U1 RETURN"
assert_next_has "$UNTIL_HEAD" "U1 RETURN"
assert_next_has "- result.txt exists" "U1 RETURN"
assert_next_lacks "new repo" "U1 RETURN"
assert_disk "$runU" "U1 DISK" '{"phase":"implement","receipts":{"S1":"running"}}'
printf 'LAYER: U setup-once OK\n'

printf 'shiploop-walk-journal.test.sh: PASS\n'
