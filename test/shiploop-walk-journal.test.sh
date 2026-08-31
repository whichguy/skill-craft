#!/usr/bin/env bash
# Incremental walk-journal + state-transition tests (no network).
#
# Each CASE is: PRE disk → INVOKE scripts/shiploop → RETURN (rc + stdout) → DISK.
# Glyphs match the session rail: ● done / ▶ running|ready / ○ todo. No ✗ on steps.
#
# Standalone: bash test/shiploop-walk-journal.test.sh
# Also invoked from test/shiploop.test.sh.
#
# Isolation: test/shiploop-testkit.sh. Sequential walk CASES share one sandbox
# (PRE of the next CASE is the previous DISK). Independent edges get a new
# sandbox (setup → invoke → assert → teardown). Suite EXIT trap always
# removes leftover git worktrees.
#
# Learnings: dest-plan sample (artifacts/environment.md) must satisfy live
# exclusive_gaps; wrapper lead line is part of the return contract; first=last
# implement needs a one-step DAG; parallel --write on scripts/shiploop is a
# test-killer — pin VERSION in shiploop.test.sh.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cli="$root/skills/shiploop/scripts/shiploop"
fix="$root/test/fixtures/shiploop"
TRANS="$fix/transitions/artifacts"
export SHIPLOOP_BACKCHAIN_ROOT="$fix/backchain-leaf"
# shellcheck source=shiploop-testkit.sh
source "$root/test/shiploop-testkit.sh"

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

assert_next_h2_has() {
  local needle="$1" msg="$2"
  packet_section "$LAST_OUT" "## Next prompt" | grep -Fq -- "$needle" \
    || fail "$msg: H2-bounded Next missing ${needle}"
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

assert_line1() {
  local want="$1" msg="$2"
  local got
  got="$(printf '%s\n' "$LAST_OUT" | awk 'NR==1 { print; exit }')"
  [[ "$got" == "$want" ]] || fail "$msg: line1=${got} want=${want}"
}

assert_no_next_packet() {
  local msg="$1"
  if printf '%s\n' "$LAST_OUT" | grep -Fxq '## Next prompt'; then
    fail "$msg: unexpected ## Next prompt"
  fi
}

WRAP_COMPLETE='shiploop complete — close the increment and print the next packet'
WRAP_NEXT='shiploop next — reprint the packet'

invoke_wrapper() {
  local verb="$1"
  shift
  local wrap="$root/skills/shiploop/scripts/shiploop-${verb}"
  [[ -f "$wrap" ]] || fail "missing wrapper scripts/shiploop-${verb}"
  local outf errf
  outf="$(mktemp "${TMPDIR:-/tmp}/shiploop-wrap-out.XXXXXX")"
  errf="$(mktemp "${TMPDIR:-/tmp}/shiploop-wrap-err.XXXXXX")"
  set +e
  python3 "$wrap" "$@" >"$outf" 2>"$errf"
  LAST_RC=$?
  set -e
  LAST_OUT="$(cat "$outf")"
  LAST_ERR="$(cat "$errf")"
  rm -f "$outf" "$errf"
}

assert_wrapper_then_transition() {
  local run="$1" wrap_line="$2" dest_line="$3" mode="$4" msg="$5"
  assert_rc 0 "$msg"
  assert_line1 "$wrap_line" "$msg"
  LAST_OUT="$(printf '%s\n' "$LAST_OUT" | awk 'NR>1')"
  assert_transition_return "$run" "$dest_line" "$mode" "$msg"
}

assert_when_done_has() {
  local needle="$1" msg="$2"
  packet_section "$LAST_OUT" "## When done invoke" "## Missing" | grep -Fq -- "$needle" \
    || fail "$msg: When done invoke missing ${needle}"
}

assert_when_done_lacks() {
  local needle="$1" msg="$2"
  if packet_section "$LAST_OUT" "## When done invoke" "## Missing" | grep -Fq -- "$needle"; then
    fail "$msg: When done invoke has ${needle}"
  fi
}

assert_session_closer() {
  local msg="$1"
  assert_when_done_has "invoke /shiploop complete" "$msg"
  assert_when_done_lacks "complete-step" "$msg"
}

# Probe every dest that is not the legal forward from current phase.
# kind=illegal → legal_edge is None. kind=resume → blocked dest ≠ resume_to.
probe_illegal_updates() {
  local run="$1" msg="$2"
  local dest kind
  while IFS=$'\t' read -r dest kind; do
    [[ -n "$dest" ]] || continue
    invoke_script update --run-dir "$run" --to "$dest"
    assert_rc 2 "$msg $dest"
    assert_no_next_packet "$msg $dest"
    if [[ "$kind" == resume ]]; then
      assert_err_has "blocked may only resume" "$msg $dest"
    else
      assert_err_has "illegal transition" "$msg $dest"
    fi
  done < <(python3 - "$root/skills/shiploop/references/transitions.json" "$run" <<'PY'
import json, sys
from pathlib import Path
tj = json.loads(Path(sys.argv[1]).read_text())
st = json.loads((Path(sys.argv[2]) / "state.json").read_text())
frm = str(st.get("phase"))
resume = st.get("resume_to")
legal = {e["to"] for e in tj["edges"] if e.get("from") == frm}
for p in tj.get("phases") or []:
    if p == frm:
        continue
    if p not in legal:
        print("%s\tillegal" % p)
    elif frm == "blocked" and p != resume:
        print("%s\tresume" % p)
PY
)
}

# mode: activity | stored
# run dir is required so Next can be compared to activity_body / stored prompts.
assert_transition_return() {
  local run="$1" dest_line="$2" mode="$3" msg="$4"
  assert_rc 0 "$msg"
  assert_line1 "$dest_line" "$msg"
  local n
  n="$(printf '%s\n' "$LAST_OUT" | grep -cx '## Next prompt' || true)"
  [[ "$n" -eq 1 ]] || fail "$msg: ## Next prompt count=$n want=1"
  local first
  first="$(packet_section "$LAST_OUT" "## Next prompt" "## When done invoke" | awk 'NR==1 { print; exit }')"
  [[ "$first" == 'Use this prompt as much as possible.' ]] \
    || fail "$msg: Next first line=${first}"
  local second
  second="$(packet_section "$LAST_OUT" "## Next prompt" "## When done invoke" | awk 'NR==2 { print; exit }')"
  if [[ "$second" == /goal || "$second" == /goal* ]]; then
    [[ "$mode" == stored ]] || fail "$msg: Next body starts with /goal in $mode mode: ${second}"
  fi
  case "$mode" in
    activity)
      CLI="$cli" PACKET="$LAST_OUT" python3 - "$run" "$msg" <<'PY' || fail "$msg"
import os, sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
run = Path(sys.argv[1])
msg = sys.argv[2]
cli = os.environ["CLI"]
packet = os.environ.get("PACKET") or ""
loader = SourceFileLoader("shiploop_cli", cli)
spec = spec_from_loader("shiploop_cli", loader)
mod = module_from_spec(spec)
loader.exec_module(mod)
state = mod.load_state(run)
phase = str(state.get("phase"))
expected = mod.activity_body(phase, run, state)
lines = []
in_next = False
for line in packet.splitlines():
    if line == "## Next prompt":
        in_next = True
        continue
    if in_next and line == "## When done invoke":
        break
    if in_next:
        lines.append(line)
if not lines or lines[0] != "Use this prompt as much as possible.":
    sys.exit(f"{msg}: Next missing Use this prompt lead")
body = "\n".join(lines[1:]).rstrip()
if body != expected:
    sys.exit(f"{msg}: Next body != activity_body({phase})")
PY
      ;;
    stored)
      CLI="$cli" PACKET="$LAST_OUT" python3 - "$run" "$msg" "$UNTIL_HEAD" <<'PY' || fail "$msg"
import os, re, sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
run = Path(sys.argv[1])
msg = sys.argv[2]
until = sys.argv[3]
cli = os.environ["CLI"]
packet = os.environ.get("PACKET") or ""
loader = SourceFileLoader("shiploop_cli", cli)
spec = spec_from_loader("shiploop_cli", loader)
mod = module_from_spec(spec)
loader.exec_module(mod)
state = mod.load_state(run)
classes = mod.classify_steps(run, state)
running = [sid for sid, k in classes.items() if k == "running"]
by_id = mod.steps_by_id(run)
lines = []
in_next = False
for line in packet.splitlines():
    if line == "## Next prompt":
        in_next = True
        continue
    if in_next and line == "## When done invoke":
        break
    if in_next:
        lines.append(line)
if not lines or lines[0] != "Use this prompt as much as possible.":
    sys.exit(f"{msg}: Next missing Use this prompt lead")
rest = "\n".join(lines[1:])
goal_n = sum(1 for ln in rest.splitlines() if re.match(r"^[ \t]*/goal\b", ln))
# Each running id: stored /goal A plus Improve /goal B.
if goal_n != 2 * len(running):
    sys.exit(f"{msg}: /goal lines={goal_n} want={2 * len(running)} running={running}")
if running and until not in rest:
    sys.exit(f"{msg}: Next missing {until!r}")
for sid in running:
    step = by_id.get(sid) or {}
    prompt = str(step.get("prompt") or "")
    if prompt and prompt not in rest:
        sys.exit(f"{msg}: stored prompt for {sid} not contiguous in Next")
    texts = mod.produces_texts(step.get("produces")) or []
    for t in texts:
        if t not in rest:
            sys.exit(f"{msg}: Next missing produces {t!r} for {sid}")
PY
      ;;
    *)
      fail "$msg: unknown return mode $mode"
      ;;
  esac
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
setup_to_plan() {
  local run="$1" repo="$2" planf="$3"
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
}

setup_to_implement() {
  local run="$1" repo="$2" planf="$3" fixture="$4"
  setup_to_plan "$run" "$repo" "$planf"
  install_dag "$run" "$fixture"
  invoke_script complete --run-dir "$run"
  assert_rc 0 "setup dest implement"
}

# stdin is the new prompt body. Must not share python3 - stdin with the program.
set_step_prompt() {
  local run="$1" sid="$2" pf
  pf="$(mktemp "${TMPDIR:-/tmp}/shiploop-prompt.XXXXXX")"
  cat >"$pf"
  python3 - "$run" "$sid" "$pf" <<'PY'
import json, sys
from pathlib import Path
run, sid, pf = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
prompt = pf.read_text()
path = run / "backchain" / "plan.json"
doc = json.loads(path.read_text())
found = False
for step in doc.get("steps") or []:
    if isinstance(step, dict) and step.get("id") == sid:
        step["prompt"] = prompt
        found = True
        break
if not found:
    sys.exit(f"set_step_prompt: no {sid}")
path.write_text(json.dumps(doc, indent=2) + "\n")
PY
  rm -f "$pf"
}

setup_to_residual() {
  setup_to_implement "$1" "$2" "$3" "${4:-linear.json}"
  host_land "$1" S1
  invoke_script complete --run-dir "$1"
  assert_rc 0 "setup complete S1"
  host_land "$1" S2
  invoke_script complete --run-dir "$1"
  assert_rc 0 "setup complete S2 dest residual"
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
DISK_IMP_SOLO_RUN='{"phase":"implement","receipts":{"S1":"running"},"files":{"backchain/plan.json":true,"plan.md":true},"plan_sha256":"set"}'
DISK_IMP_SOLO_DRAINED='{"phase":"implement","receipts":{"S1":"complete"},"plan_sha256":"set"}'

shiploop_suite_begin shiploop-walk-journal
tmpdir="$SUITE_TMP"

[[ -f "$fix/transitions/INDEX.md" ]] || fail "missing transitions/INDEX.md"
[[ -d "$TRANS" ]] || fail "missing transitions/artifacts"
assert_index_covers_edges
grep -Fq '"exclusive": []' "$TRANS/environment.md" \
  || fail "sample environment.md missing exclusive [] (dest-plan pin)"

planf="$SUITE_TMP/bound.plan.md"
setup_bound_plan "$planf"

# =============================================================================
# L — linear complete walk (each dest/complete is its own CASE)
# Shared sandbox: L0 DISK is L1 PRE, …, L6. Teardown after the walk.
# =============================================================================
shiploop_sandbox_open L
runL="$SL_RUN"
repoL="$SL_REPO"
init_git_repo "$repoL"

printf 'CASE L0 INVOKE: shiploop init (no prior run dir)\n'
invoke_script init --prompt "create result.txt containing exactly one line: ok" \
  --run-dir "$runL" --bound-plan "$planf" --repo "$repoL"
assert_transition_return "$runL" \
  "initialized $(python3 -c "from pathlib import Path; print(Path('$runL') / 'state.json')")" \
  activity "L0 RETURN"
assert_session_closer "L0 RETURN"
assert_next_h2_has "Write the original user ask" "L0 RETURN"
assert_next_lacks "/goal step S1:" "L0 RETURN"
assert_no_walk "L0 RETURN"
assert_disk "$runL" "L0 DISK" "$DISK_INTAKE"
probe_illegal_updates "$runL" "L0 illegal"

printf 'CASE L1 PRE: intake, prompt.md only; INVOKE: complete dest validate-spec\n'
assert_disk "$runL" "L1 PRE" "$DISK_INTAKE"
invoke_script complete --run-dir "$runL"
assert_transition_return "$runL" "updated -> validate-spec" activity "L1 RETURN"
assert_session_closer "L1 RETURN"
assert_next_h2_has "Survey, then practices, then spec" "L1 RETURN"
assert_next_h2_has "Deeply research those MCP servers" "L1 RETURN"
assert_next_h2_has "Reuse before add" "L1 RETURN"
assert_next_h2_has "Do not duplicate, conflict with, or arbitrarily add" "L1 RETURN"
assert_next_h2_has "### 2. Best-practice" "L1 RETURN"
assert_next_lacks "/goal step S1:" "L1 RETURN"
assert_no_walk "L1 RETURN"
assert_disk "$runL" "L1 DISK" "$DISK_VS"
probe_illegal_updates "$runL" "L1 illegal"

printf 'CASE L2 PRE: validate-spec + host wrote env/spec; INVOKE: complete dest plan\n'
write_environment "$runL"
write_spec "$runL"
assert_disk "$runL" "L2 PRE" '{"phase":"validate-spec","files":{"spec.md":true,"environment.md":true},"spec_sha256":"empty"}'
invoke_script complete --run-dir "$runL"
assert_transition_return "$runL" "updated -> plan" activity "L2 RETURN"
assert_session_closer "L2 RETURN"
assert_next_h2_has "The spec is **frozen**" "L2 RETURN"
assert_next_lacks "/goal step S1:" "L2 RETURN"
assert_no_walk "L2 RETURN"
assert_disk "$runL" "L2 DISK" "$DISK_PLAN"
probe_illegal_updates "$runL" "L2 illegal"

printf 'CASE L3 PRE: plan + host wrote DAG; INVOKE: complete dest implement + claim S1\n'
install_dag "$runL" linear.json
assert_disk "$runL" "L3 PRE" '{"phase":"plan","files":{"backchain/plan.json":true,"plan.md":true},"plan_sha256":"empty","receipts":{"S1":"none","S2":"none"}}'
invoke_script complete --run-dir "$runL"
assert_transition_return "$runL" "updated -> implement" stored "L3 RETURN"
assert_walk_journal "$runL" "L3 RETURN walk"
assert_out_has "▶ S1  write the file" "L3 RETURN"
assert_out_has "○ S2  confirm the file" "L3 RETURN"
assert_out_has "waiting on S1 write the file" "L3 RETURN"
assert_next_has "$S1_LINEAR" "L3 RETURN"
assert_next_lacks "$S2_LINEAR" "L3 RETURN"
assert_next_has "Implement git (paste into /goal with Frozen" "L3 RETURN"
assert_next_has "Goal until (this stored prompt is /goal A" "L3 RETURN"
assert_next_has "Improve (paste as /goal B after produces is true" "L3 RETURN"
assert_when_done_has "Finish S1: write the file" "L3 RETURN"
assert_when_done_has "Key learnings:" "L3 RETURN"
assert_when_done_has "then invoke /shiploop complete (merges" "L3 RETURN"
assert_when_done_lacks "Finish S2:" "L3 RETURN"
assert_when_done_lacks "complete-step" "L3 RETURN"
assert_disk "$runL" "L3 DISK" "$DISK_IMP_S1RUN"
probe_illegal_updates "$runL" "L3 illegal"
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
assert_transition_return "$runL" "completed S1" stored "L4 RETURN"
assert_walk_journal "$runL" "L4 RETURN walk"
assert_out_has "● S1  write the file" "L4 RETURN"
assert_out_has "▶ S2  confirm the file" "L4 RETURN"
assert_next_has "$S2_LINEAR" "L4 RETURN"
assert_next_lacks "$S1_LINEAR" "L4 RETURN"
assert_when_done_has "Finish S2: confirm the file" "L4 RETURN"
assert_when_done_lacks "Finish S1:" "L4 RETURN"
assert_when_done_lacks "complete-step" "L4 RETURN"
assert_disk "$runL" "L4 DISK" "$DISK_IMP_S1DONE"
assert_plan_md_unchanged "$runL" "$plan_hash_L3" "L4 DISK plan.md"

printf 'CASE L5 PRE: S2 running (host landed); INVOKE: complete → residual\n'
assert_disk "$runL" "L5 PRE before land" "$DISK_IMP_S1DONE"
host_land "$runL" S2
invoke_script complete --run-dir "$runL"
assert_transition_return "$runL" "completed S2" activity "L5 RETURN"
assert_no_walk "L5 RETURN"
assert_out_has "residual: current" "L5 RETURN"
assert_out_lacks "updated implement -> residual" "L5 RETURN"
assert_next_h2_has "Review-coverage is **waived**" "L5 RETURN"
assert_next_lacks "/goal " "L5 RETURN"
assert_next_lacks "Implement git (paste into /goal with Frozen" "L5 RETURN"
assert_next_lacks "Goal until (this stored prompt is /goal A" "L5 RETURN"
assert_next_lacks "Improve (paste as /goal B after produces is true" "L5 RETURN"
assert_session_closer "L5 RETURN"
assert_when_done_lacks "Finish S" "L5 RETURN"
assert_disk "$runL" "L5 DISK" '{"phase":"residual","receipts":{"S1":"complete","S2":"complete"}}'
assert_plan_md_unchanged "$runL" "$plan_hash_L3" "L5 DISK plan.md"

printf 'CASE L6 PRE: residual; INVOKE: next reprint\n'
assert_disk "$runL" "L6 PRE" '{"phase":"residual","receipts":{"S1":"complete","S2":"complete"}}'
invoke_script next --run-dir "$runL"
assert_transition_return "$runL" "next — reprint (residual)" activity "L6 RETURN"
assert_no_walk "L6 RETURN"
assert_session_closer "L6 RETURN"
assert_next_h2_has "Review-coverage is **waived**" "L6 RETURN"
assert_next_lacks "/goal step S" "L6 RETURN"
assert_disk "$runL" "L6 DISK" '{"phase":"residual","receipts":{"S1":"complete","S2":"complete"}}'
probe_illegal_updates "$runL" "L6 illegal"
printf 'LAYER: L linear complete-walk OK\n'
shiploop_sandbox_close
[[ ! -d "$SUITE_TMP/sb-L" ]] || fail "L sandbox leaked after close"

# =============================================================================
# N — reprint: next does not mutate disk
# =============================================================================
shiploop_sandbox_open N
runN="$SL_RUN"
repoN="$SL_REPO"
setup_to_implement "$runN" "$repoN" "$planf" linear.json

printf 'CASE N1 PRE: S1 running; INVOKE: next (reprint, In flight)\n'
assert_disk "$runN" "N1 PRE" "$DISK_IMP_S1RUN"
invoke_script next --run-dir "$runN"
assert_transition_return "$runN" "next — reprint (implement)" stored "N1 RETURN"
assert_walk_journal "$runN" "N1 RETURN walk"
assert_next_has "In flight — do not open a second /goal" "N1 RETURN"
assert_next_has "Implement git (paste into /goal with Frozen" "N1 RETURN"
assert_next_has "Goal until (this stored prompt is /goal A" "N1 RETURN"
assert_next_has "Improve (paste as /goal B after produces is true" "N1 RETURN"
assert_when_done_has "Finish S1: write the file" "N1 RETURN"
assert_when_done_lacks "complete-step" "N1 RETURN"
assert_disk "$runN" "N1 DISK (unchanged)" "$DISK_IMP_S1RUN"

printf 'CASE N2 PRE: S1 complete S2 running; INVOKE: next reprint\n'
host_land "$runN" S1
invoke_script complete --run-dir "$runN"
assert_rc 0 "N2 setup complete S1"
assert_disk "$runN" "N2 PRE" "$DISK_IMP_S1DONE"
invoke_script next --run-dir "$runN"
assert_transition_return "$runN" "next — reprint (implement)" stored "N2 RETURN"
assert_walk_journal "$runN" "N2 RETURN walk"
assert_out_has "● S1  write the file" "N2 RETURN"
assert_next_has "In flight — do not open a second /goal" "N2 RETURN"
assert_next_lacks "$S1_LINEAR" "N2 RETURN"
assert_when_done_has "Finish S2: confirm the file" "N2 RETURN"
assert_when_done_lacks "Finish S1:" "N2 RETURN"
assert_disk "$runN" "N2 DISK (unchanged)" "$DISK_IMP_S1DONE"

printf 'CASE N3 PRE: drained; INVOKE: next reprint\n'
host_land "$runN" S2
invoke_script complete-step --run-dir "$runN" --id S2
assert_rc 0 "N3 setup complete-step S2"
assert_disk "$runN" "N3 PRE" "$DISK_IMP_DRAINED"
invoke_script next --run-dir "$runN"
assert_transition_return "$runN" "next — reprint (implement)" activity "N3 RETURN"
assert_walk_journal "$runN" "N3 RETURN walk"
assert_next_lacks "/goal " "N3 RETURN"
assert_session_closer "N3 RETURN"
assert_disk "$runN" "N3 DISK (unchanged)" "$DISK_IMP_DRAINED"
printf 'LAYER: N reprint OK\n'
shiploop_sandbox_close

# =============================================================================
# D — illegal skip / repeat (complete-step override, no packet)
# =============================================================================
shiploop_sandbox_open D
runD="$SL_RUN"
repoD="$SL_REPO"
setup_to_implement "$runD" "$repoD" "$planf" linear.json

printf 'CASE D1 PRE: S1 running S2 none; INVOKE: complete-step --id S2 (skip)\n'
assert_disk "$runD" "D1 PRE" "$DISK_IMP_S1RUN"
invoke_script complete-step --run-dir "$runD" --id S2
assert_rc 2 "D1"
assert_no_next_packet "D1 RETURN"
assert_err_has "not running|suppliers" "D1 RETURN"
assert_disk "$runD" "D1 DISK (unchanged)" "$DISK_IMP_S1RUN"

printf 'CASE D2 PRE: S1 complete; INVOKE: complete-step --id S1 (repeat)\n'
host_land "$runD" S1
invoke_script complete --run-dir "$runD"
assert_rc 0 "D2 setup"
assert_disk "$runD" "D2 PRE" "$DISK_IMP_S1DONE"
invoke_script complete-step --run-dir "$runD" --id S1
assert_rc 2 "D2"
assert_no_next_packet "D2 RETURN"
assert_err_has "already complete" "D2 RETURN"
assert_disk "$runD" "D2 DISK (unchanged)" "$DISK_IMP_S1DONE"
printf 'LAYER: D illegal skip/repeat OK\n'
shiploop_sandbox_close

# =============================================================================
# C — clear retry / ancestor restart
# =============================================================================
shiploop_sandbox_open C1
runC1="$SL_RUN"
repoC1="$SL_REPO"
setup_to_implement "$runC1" "$repoC1" "$planf" linear.json

printf 'CASE C1 PRE: S1 running; INVOKE: complete --clear (re-claim S1)\n'
assert_disk "$runC1" "C1 PRE" "$DISK_IMP_S1RUN"
invoke_script complete --run-dir "$runC1" --clear
assert_transition_return "$runC1" "cleared S1" stored "C1 RETURN"
assert_walk_journal "$runC1" "C1 RETURN walk"
assert_out_has "▶ S1  write the file" "C1 RETURN"
assert_out_lacks "In flight — do not open a second /goal" "C1 RETURN"
assert_when_done_has "Finish S1: write the file" "C1 RETURN"
assert_when_done_lacks "complete-step" "C1 RETURN"
assert_disk "$runC1" "C1 DISK" "$DISK_IMP_S1RUN"
shiploop_sandbox_close

shiploop_sandbox_open C2
runC2="$SL_RUN"
repoC2="$SL_REPO"
setup_to_implement "$runC2" "$repoC2" "$planf" linear.json
host_land "$runC2" S1
invoke_script complete --run-dir "$runC2"
assert_rc 0 "C2 setup"

printf 'CASE C2 PRE: S1 complete S2 running; INVOKE: clear-step S1 then next\n'
assert_disk "$runC2" "C2 PRE" "$DISK_IMP_S1DONE"
invoke_script clear-step --run-dir "$runC2" --id S1
assert_rc 0 "C2 clear-step"
assert_line1 "cleared S1" "C2 clear-step RETURN"
assert_no_next_packet "C2 clear-step RETURN"
assert_disk "$runC2" "C2 DISK after clear-step (no receipts)" \
  '{"phase":"implement","receipts":{"S1":"none","S2":"none"}}'
invoke_script next --run-dir "$runC2"
assert_transition_return "$runC2" "next — claimed S1 (implement)" stored "C2 next RETURN"
assert_walk_journal "$runC2" "C2 next RETURN walk"
assert_out_has "▶ S1  write the file" "C2 next RETURN"
assert_out_has "○ S2  confirm the file" "C2 next RETURN"
assert_next_lacks "$S2_LINEAR" "C2 next RETURN"
assert_when_done_has "Finish S1: write the file" "C2 next RETURN"
assert_disk "$runC2" "C2 DISK after next" "$DISK_IMP_S1RUN"
printf 'LAYER: C clear retry OK\n'
shiploop_sandbox_close

# =============================================================================
# P — two-root parallel
# =============================================================================
shiploop_sandbox_open P
runP="$SL_RUN"
repoP="$SL_REPO"
setup_to_implement "$runP" "$repoP" "$planf" two-root.json

printf 'CASE P1 PRE: dest implement claimed both roots; RETURN already in LAST_* from setup\n'
assert_disk "$runP" "P1 DISK" '{"phase":"implement","receipts":{"S1":"running","S2":"running"},"plan_sha256":"set"}'
assert_transition_return "$runP" "updated -> implement" stored "P1 RETURN"
assert_walk_journal "$runP" "P1 RETURN walk"
assert_out_has "▶ S1  write tests for the file" "P1 RETURN"
assert_out_has "▶ S2  write the implementation" "P1 RETURN"
assert_next_has "Implement git (paste into /goal with Frozen" "P1 RETURN"
assert_next_has "Goal until (this stored prompt is /goal A" "P1 RETURN"
assert_next_has "Improve (paste as /goal B after produces is true" "P1 RETURN"
assert_when_done_has "Finish S1: write tests for the file" "P1 RETURN"
assert_when_done_has "Finish S2: write the implementation" "P1 RETURN"
assert_when_done_lacks "complete-step" "P1 RETURN"

printf 'CASE P3 PRE: both running; INVOKE: complete without --id\n'
assert_disk "$runP" "P3 PRE" '{"phase":"implement","receipts":{"S1":"running","S2":"running"}}'
invoke_script complete --run-dir "$runP"
assert_rc 2 "P3"
assert_no_next_packet "P3 RETURN"
assert_err_has "multiple running" "P3 RETURN"
assert_disk "$runP" "P3 DISK (unchanged)" '{"phase":"implement","receipts":{"S1":"running","S2":"running"}}'

printf 'CASE P2 PRE: both running, S1 host-landed; INVOKE: complete --id S1\n'
host_land "$runP" S1
assert_disk "$runP" "P2 PRE" '{"phase":"implement","receipts":{"S1":"running","S2":"running"}}'
invoke_script complete --run-dir "$runP" --id S1
assert_transition_return "$runP" "completed S1" stored "P2 RETURN"
assert_walk_journal "$runP" "P2 RETURN walk"
assert_out_has "● S1  write tests for the file" "P2 RETURN"
assert_out_has "▶ S2  write the implementation" "P2 RETURN"
assert_next_has "In flight — do not open a second /goal" "P2 RETURN"
assert_next_lacks "$S1_TWOROOT" "P2 RETURN"
assert_when_done_has "Finish S2: write the implementation" "P2 RETURN"
assert_when_done_lacks "Finish S1:" "P2 RETURN"
assert_disk "$runP" "P2 DISK" '{"phase":"implement","receipts":{"S1":"complete","S2":"running"}}'
printf 'LAYER: P parallel OK\n'
shiploop_sandbox_close

# =============================================================================
# I — inject
# =============================================================================
shiploop_sandbox_open I1
runI1="$SL_RUN"
repoI1="$SL_REPO"
setup_to_implement "$runI1" "$repoI1" "$planf" linear.json

printf 'CASE I1 PRE: S1 running; INVOKE: inject-step S3 --before S2, then next\n'
assert_disk "$runI1" "I1 PRE" "$DISK_IMP_S1RUN"
invoke_script inject-step --run-dir "$runI1" --statement "mid bind" \
  --prompt $'/goal\nDo this activity until these conditions are met:\n- mid exists' \
  --produces "mid exists" --before S2 --id S3
assert_rc 0 "I1 inject"
assert_line1 "injected S3" "I1 inject RETURN"
assert_no_next_packet "I1 inject RETURN"
assert_disk "$runI1" "I1 DISK after inject (S3 not claimed)" \
  '{"phase":"implement","receipts":{"S1":"running","S2":"none","S3":"none"}}'
invoke_script next --run-dir "$runI1"
assert_transition_return "$runI1" "next — claimed S3 (implement)" stored "I1 next RETURN"
assert_walk_journal "$runI1" "I1 next RETURN walk"
assert_out_has "▶ S3  mid bind" "I1 next RETURN"
assert_next_has "- mid exists" "I1 next RETURN"
assert_when_done_has "Finish S1: write the file" "I1 next RETURN"
assert_when_done_has "Finish S3: mid bind" "I1 next RETURN"
assert_disk "$runI1" "I1 DISK after next" \
  '{"phase":"implement","receipts":{"S1":"running","S2":"none","S3":"running"}}'
shiploop_sandbox_close

shiploop_sandbox_open I2
runI2="$SL_RUN"
repoI2="$SL_REPO"
setup_to_implement "$runI2" "$repoI2" "$planf" linear.json
host_land "$runI2" S1
invoke_script complete --run-dir "$runI2"
assert_rc 0 "I2 setup"

printf 'CASE I2 PRE: S2 running; INVOKE: inject --before S2 (refused)\n'
assert_disk "$runI2" "I2 PRE" "$DISK_IMP_S1DONE"
invoke_script inject-step --run-dir "$runI2" --statement "mid" \
  --prompt "/goal injected after S1" --produces "mid exists" --from S1 --before S2 --id S3
assert_rc 2 "I2"
assert_no_next_packet "I2 RETURN"
assert_err_has "todo or ready" "I2 RETURN"
python3 - "$runI2" <<'PY' || fail "I2 DISK DAG grew"
import json, sys
from pathlib import Path
ids = [s["id"] for s in json.loads((Path(sys.argv[1]) / "backchain" / "plan.json").read_text())["steps"]]
assert ids == ["S1", "S2"], ids
PY
assert_disk "$runI2" "I2 DISK (unchanged)" "$DISK_IMP_S1DONE"
printf 'LAYER: I inject OK\n'
shiploop_sandbox_close

# =============================================================================
# B — blocked resume implement
# =============================================================================
shiploop_sandbox_open B
runB="$SL_RUN"
repoB="$SL_REPO"
setup_to_implement "$runB" "$repoB" "$planf" linear.json

printf 'CASE B1a PRE: S1 running; INVOKE: update --to blocked\n'
assert_disk "$runB" "B1a PRE" "$DISK_IMP_S1RUN"
invoke_script update --run-dir "$runB" --to blocked --resume-to implement --reason "host failed"
assert_transition_return "$runB" "updated implement -> blocked" activity "B1a RETURN"
assert_when_done_has "invoke /shiploop complete --reason <answer>" "B1a RETURN"
assert_disk "$runB" "B1a DISK" \
  '{"phase":"blocked","resume_to":"implement","blocked_from":"implement","receipts":{"S1":"running"}}'
probe_illegal_updates "$runB" "B1a illegal"

printf 'CASE B1b PRE: blocked resume_to=implement; INVOKE: complete --reason\n'
assert_disk "$runB" "B1b PRE" '{"phase":"blocked","resume_to":"implement"}'
invoke_script complete --run-dir "$runB" --reason "resume"
assert_transition_return "$runB" "updated -> implement" stored "B1b RETURN"
assert_walk_journal "$runB" "B1b RETURN walk"
assert_out_has "▶ S1  write the file" "B1b RETURN"
assert_out_lacks "● S1" "B1b RETURN"
assert_when_done_has "Finish S1: write the file" "B1b RETURN"
assert_disk "$runB" "B1b DISK" '{"phase":"implement","receipts":{"S1":"running","S2":"none"},"resume_to":null}'
printf 'LAYER: B blocked resume OK\n'
shiploop_sandbox_close

# =============================================================================
# H — hash-mismatch complete is not ●
# =============================================================================
shiploop_sandbox_open H
runH="$SL_RUN"
repoH="$SL_REPO"
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
assert_no_next_packet "H1 next RETURN"
assert_err_has "already exists|worktree add failed" "H1 next RETURN"
printf 'LAYER: H hash-mismatch OK\n'
shiploop_sandbox_close

# =============================================================================
# F — replan wipes receipts
# =============================================================================
shiploop_sandbox_open F
runF="$SL_RUN"
repoF="$SL_REPO"
setup_to_implement "$runF" "$repoF" "$planf" linear.json
host_land "$runF" S1
invoke_script complete --run-dir "$runF"
assert_rc 0 "F setup"

printf 'CASE F1a PRE: S1 complete S2 running; INVOKE: complete --blocked --resume-to plan\n'
assert_disk "$runF" "F1a PRE" "$DISK_IMP_S1DONE"
invoke_script complete --run-dir "$runF" --blocked --reason "replan" --resume-to plan
assert_transition_return "$runF" "updated -> blocked" activity "F1a RETURN"
assert_when_done_has "invoke /shiploop complete --reason <answer>" "F1a RETURN"
assert_disk "$runF" "F1a DISK" '{"phase":"blocked","resume_to":"plan","receipts":{"S1":"complete","S2":"running"}}'

printf 'CASE F1b PRE: blocked→plan; INVOKE: complete --reason (dest plan clears receipts)\n'
invoke_script complete --run-dir "$runF" --reason "replan"
assert_transition_return "$runF" "updated -> plan" activity "F1b RETURN"
assert_session_closer "F1b RETURN"
assert_next_lacks "$S1_LINEAR" "F1b RETURN"
assert_disk "$runF" "F1b DISK" \
  '{"phase":"plan","receipts":{"S1":"none","S2":"none"},"plan_sha256":"empty"}'

printf 'CASE F1c PRE: plan, re-install DAG; INVOKE: complete dest implement\n'
install_dag "$runF" linear.json
assert_disk "$runF" "F1c PRE" '{"phase":"plan","files":{"backchain/plan.json":true},"plan_sha256":"empty"}'
invoke_script complete --run-dir "$runF"
assert_transition_return "$runF" "updated -> implement" stored "F1c RETURN"
assert_walk_journal "$runF" "F1c RETURN walk"
assert_out_has "▶ S1  write the file" "F1c RETURN"
assert_out_lacks "● S1" "F1c RETURN"
assert_when_done_has "Finish S1: write the file" "F1c RETURN"
assert_disk "$runF" "F1c DISK" "$DISK_IMP_S1RUN"
printf 'LAYER: F replan wipe OK\n'
shiploop_sandbox_close

# =============================================================================
# V — validate-spec ↔ blocked (uncheckable spec artifact, independent folder)
# =============================================================================
shiploop_sandbox_open V
runV="$SL_RUN"
repoV="$SL_REPO"
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
assert_transition_return "$runV" "updated -> blocked" activity "V1 RETURN"
assert_when_done_has "invoke /shiploop complete --reason <answer>" "V1 RETURN"
assert_disk "$runV" "V1 DISK" \
  '{"phase":"blocked","resume_to":"validate-spec","blocked_from":"validate-spec","files":{"spec.md":true,"environment.md":false}}'

printf 'CASE V2 PRE: blocked resume_to=validate-spec; INVOKE: complete --reason\n'
assert_disk "$runV" "V2 PRE" '{"phase":"blocked","resume_to":"validate-spec"}'
invoke_script complete --run-dir "$runV" --reason "user answered"
assert_transition_return "$runV" "updated -> validate-spec" activity "V2 RETURN"
assert_session_closer "V2 RETURN"
assert_disk "$runV" "V2 DISK" \
  '{"phase":"validate-spec","resume_to":null,"spec_sha256":"empty","plan_sha256":"empty"}'
printf 'LAYER: V validate-spec blocked hatch OK\n'
shiploop_sandbox_close

# =============================================================================
# Q — plan → blocked (independent folder, no DAG)
# =============================================================================
shiploop_sandbox_open Q
runQ="$SL_RUN"
repoQ="$SL_REPO"
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
assert_transition_return "$runQ" "updated -> blocked" activity "Q1 RETURN"
assert_when_done_has "invoke /shiploop complete --reason <answer>" "Q1 RETURN"
assert_disk "$runQ" "Q1 DISK" \
  '{"phase":"blocked","resume_to":"plan","blocked_from":"plan","files":{"backchain/plan.json":false}}'
printf 'LAYER: Q plan-to-blocked OK\n'
shiploop_sandbox_close

# =============================================================================
# G — residual → done (waiver artifact, independent folder)
# =============================================================================
shiploop_sandbox_open G
runG="$SL_RUN"
repoG="$SL_REPO"
setup_to_residual "$runG" "$repoG" "$planf" linear.json

printf 'CASE G1 PRE: residual, waived bound plan, no recap; INVOKE: complete dest done\n'
assert_disk "$runG" "G1 PRE" \
  '{"phase":"residual","receipts":{"S1":"complete","S2":"complete"},"files":{"recap.html":false},"terminal":null}'
invoke_script complete --run-dir "$runG"
assert_transition_return "$runG" "updated -> done" activity "G1 RETURN"
assert_next_h2_has "Session closed" "G1 RETURN"
assert_when_done_has "stop — no update" "G1 RETURN"
assert_when_done_lacks "invoke /shiploop complete" "G1 RETURN"
assert_out_has "recap.html" "G1 RETURN Look here"
assert_disk "$runG" "G1 DISK" \
  '{"phase":"done","terminal":"waived","files":{"recap.html":true},"receipts":{"S1":"complete","S2":"complete"}}'
grep -q 'writer: shiploop.recap' "$runG/recap.html" || fail "G1 DISK recap missing writer stamp"
probe_illegal_updates "$runG" "G1 illegal"

printf 'CASE G2 PRE: done; INVOKE: next reprint stop, then complete (no forward)\n'
invoke_script next --run-dir "$runG"
assert_transition_return "$runG" "next — reprint (done)" activity "G2 next RETURN"
assert_when_done_has "stop — no update" "G2 next RETURN"
assert_disk "$runG" "G2 DISK (unchanged)" '{"phase":"done","terminal":"waived"}'
invoke_script complete --run-dir "$runG"
assert_rc 2 "G2 complete"
assert_err_has "no forward transition" "G2 complete RETURN"
assert_no_next_packet "G2 complete RETURN"
assert_disk "$runG" "G2 DISK after refused complete" '{"phase":"done","terminal":"waived"}'
printf 'LAYER: G residual-to-done waiver OK\n'
shiploop_sandbox_close

# =============================================================================
# K — residual → done via ledger-complete.md (no waiver, independent folder)
# =============================================================================
planK="$SUITE_TMP/K.bound.md"
setup_bound_coverage "$planK"
shiploop_sandbox_open K
runK="$SL_RUN"
repoK="$SL_REPO"
setup_to_residual "$runK" "$repoK" "$planK" linear.json

printf 'CASE K0 PRE: residual, bound-coverage, no ledger; INVOKE: next (Phase B Next)\n'
assert_disk "$runK" "K0 PRE" '{"phase":"residual","terminal":null}'
invoke_script next --run-dir "$runK"
assert_transition_return "$runK" "next — reprint (residual)" activity "K0 RETURN"
assert_next_h2_has "run review-coverage Phase B" "K0 RETURN"
assert_next_lacks "Review-coverage is **waived**" "K0 RETURN"
assert_session_closer "K0 RETURN"
assert_disk "$runK" "K0 DISK (unchanged)" '{"phase":"residual"}'

printf 'CASE K1 PRE: residual, bound-coverage + ledger-complete; INVOKE: complete dest done\n'
assert_disk "$runK" "K1 PRE" '{"phase":"residual","terminal":null,"files":{"recap.html":false}}'
install_ledger "$repoK" complete "$planK"
[[ -f "$repoK/REVIEW_CONVERGE.md" ]] || fail "K1 PRE missing ledger"
invoke_script complete --run-dir "$runK"
assert_transition_return "$runK" "updated -> done" activity "K1 RETURN"
assert_when_done_has "stop — no update" "K1 RETURN"
assert_disk "$runK" "K1 DISK" \
  '{"phase":"done","terminal":"success","files":{"recap.html":true}}'
grep -q 'review-coverage complete and landed' "$runK/recap.html" \
  || fail "K1 DISK recap missing complete-and-landed"
printf 'LAYER: K residual-to-done ledger OK\n'
shiploop_sandbox_close

# =============================================================================
# T — residual → halted via ledger-stopped.md (independent folder)
# =============================================================================
planT="$SUITE_TMP/T.bound.md"
setup_bound_coverage "$planT"
shiploop_sandbox_open T
runT="$SL_RUN"
repoT="$SL_REPO"
setup_to_residual "$runT" "$repoT" "$planT" linear.json

printf 'CASE T1 PRE: residual, ledger-stopped; INVOKE: complete dest halted\n'
assert_disk "$runT" "T1 PRE" '{"phase":"residual","terminal":null}'
install_ledger "$repoT" stopped "$planT"
invoke_script complete --run-dir "$runT"
assert_transition_return "$runT" "updated -> halted" activity "T1 RETURN"
assert_next_h2_has "Session terminal: halted" "T1 RETURN"
assert_when_done_has "stop — no update" "T1 RETURN"
assert_disk "$runT" "T1 DISK" \
  '{"phase":"halted","terminal":"halted","files":{"recap.html":true}}'
grep -q 'HALTED' "$runT/recap.html" || fail "T1 DISK recap missing HALTED"
probe_illegal_updates "$runT" "T1 illegal"

printf 'CASE T2 PRE: halted; INVOKE: next reprint stop, then complete (no forward)\n'
invoke_script next --run-dir "$runT"
assert_transition_return "$runT" "next — reprint (halted)" activity "T2 next RETURN"
assert_when_done_has "stop — no update" "T2 next RETURN"
invoke_script complete --run-dir "$runT"
assert_rc 2 "T2 complete"
assert_err_has "no forward transition" "T2 complete RETURN"
assert_no_next_packet "T2 complete RETURN"
assert_disk "$runT" "T2 DISK (unchanged)" '{"phase":"halted","terminal":"halted"}'
printf 'LAYER: T residual-to-halted OK\n'
shiploop_sandbox_close

# =============================================================================
# R — residual → blocked → residual (independent folder)
# =============================================================================
shiploop_sandbox_open R
runR="$SL_RUN"
repoR="$SL_REPO"
setup_to_residual "$runR" "$repoR" "$planf" linear.json

printf 'CASE R1 PRE: residual; INVOKE: complete --blocked --resume-to residual\n'
assert_disk "$runR" "R1 PRE" '{"phase":"residual","receipts":{"S1":"complete","S2":"complete"}}'
invoke_script complete --run-dir "$runR" --blocked --reason "not green" --resume-to residual
assert_transition_return "$runR" "updated -> blocked" activity "R1 RETURN"
assert_when_done_has "invoke /shiploop complete --reason <answer>" "R1 RETURN"
assert_disk "$runR" "R1 DISK" \
  '{"phase":"blocked","resume_to":"residual","blocked_from":"residual","receipts":{"S1":"complete","S2":"complete"}}'

printf 'CASE R2 PRE: blocked resume_to=residual, steps drained; INVOKE: complete --reason\n'
assert_disk "$runR" "R2 PRE" '{"phase":"blocked","resume_to":"residual"}'
invoke_script complete --run-dir "$runR" --reason "suite green"
assert_transition_return "$runR" "updated -> residual" activity "R2 RETURN"
assert_session_closer "R2 RETURN"
assert_disk "$runR" "R2 DISK" \
  '{"phase":"residual","resume_to":null,"receipts":{"S1":"complete","S2":"complete"}}'
printf 'LAYER: R residual blocked resume OK\n'
shiploop_sandbox_close

# =============================================================================
# X — illegal edges (independent folders)
# =============================================================================
shiploop_sandbox_open X1
runX1="$SL_RUN"
repoX1="$SL_REPO"
init_git_repo "$repoX1"
invoke_script init --prompt "create result.txt containing exactly one line: ok" \
  --run-dir "$runX1" --bound-plan "$planf" --repo "$repoX1"
assert_rc 0 "X1 setup"

printf 'CASE X1 PRE: intake; INVOKE: complete --blocked (illegal)\n'
assert_disk "$runX1" "X1 PRE" '{"phase":"intake"}'
invoke_script complete --run-dir "$runX1" --blocked --reason "no" --resume-to validate-spec
assert_rc 2 "X1"
assert_no_next_packet "X1 RETURN"
assert_err_has "illegal transition" "X1 RETURN"
assert_disk "$runX1" "X1 DISK (unchanged)" '{"phase":"intake"}'
shiploop_sandbox_close

shiploop_sandbox_open X2
runX2="$SL_RUN"
repoX2="$SL_REPO"
setup_to_implement "$runX2" "$repoX2" "$planf" linear.json

printf 'CASE X2 PRE: implement mid-walk; INVOKE: update --to done (illegal)\n'
assert_disk "$runX2" "X2 PRE" "$DISK_IMP_S1RUN"
invoke_script update --run-dir "$runX2" --to done
assert_rc 2 "X2"
assert_no_next_packet "X2 RETURN"
assert_err_has "illegal transition" "X2 RETURN"
assert_disk "$runX2" "X2 DISK (unchanged)" "$DISK_IMP_S1RUN"
printf 'LAYER: X illegal edges OK\n'
shiploop_sandbox_close

# =============================================================================
# U — setup-once: original ask mentions new repo; S1 prompt must not
# =============================================================================
shiploop_sandbox_open U
runU="$SL_RUN"
repoU="$SL_REPO"
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
assert_transition_return "$runU" "updated -> implement" stored "U1 RETURN"
assert_next_lacks "new repo" "U1 RETURN"
assert_disk "$runU" "U1 DISK" '{"phase":"implement","receipts":{"S1":"running"}}'
printf 'LAYER: U setup-once OK\n'
shiploop_sandbox_close

# =============================================================================
# S — one-step DAG: S1 is both the first and the last implement step
# =============================================================================
shiploop_sandbox_open S
runS="$SL_RUN"
repoS="$SL_REPO"
setup_to_plan "$runS" "$repoS" "$planf"
install_dag "$runS" single.json

printf 'CASE S1 PRE: plan + single.json; INVOKE: complete dest implement (claim first=last)\n'
invoke_script complete --run-dir "$runS"
assert_transition_return "$runS" "updated -> implement" stored "S1 RETURN"
assert_walk_journal "$runS" "S1 RETURN walk"
assert_out_has "▶ S1  write the file" "S1 RETURN"
assert_out_lacks "S2" "S1 RETURN"
assert_next_has "$S1_LINEAR" "S1 RETURN"
assert_next_has "Implement git (paste into /goal with Frozen" "S1 RETURN"
assert_next_has "Goal until (this stored prompt is /goal A" "S1 RETURN"
assert_next_has "Improve (paste as /goal B after produces is true" "S1 RETURN"
assert_when_done_has "Finish S1: write the file" "S1 RETURN"
assert_when_done_lacks "Finish S2:" "S1 RETURN"
assert_when_done_lacks "complete-step" "S1 RETURN"
assert_disk "$runS" "S1 DISK" "$DISK_IMP_SOLO_RUN"

printf 'CASE S2 PRE: S1 running (host landed, only step); INVOKE: complete → residual\n'
host_land "$runS" S1
invoke_script complete --run-dir "$runS"
assert_transition_return "$runS" "completed S1" activity "S2 RETURN"
assert_no_walk "S2 RETURN"
assert_out_has "residual: current" "S2 RETURN"
assert_next_h2_has "Review-coverage is **waived**" "S2 RETURN"
assert_next_lacks "/goal " "S2 RETURN"
assert_next_lacks "Implement git (paste into /goal with Frozen" "S2 RETURN"
assert_next_lacks "Improve (paste as /goal B after produces is true" "S2 RETURN"
assert_next_lacks "$S1_LINEAR" "S2 RETURN"
assert_session_closer "S2 RETURN"
assert_when_done_lacks "Finish S1:" "S2 RETURN"
assert_disk "$runS" "S2 DISK" '{"phase":"residual","receipts":{"S1":"complete"}}'

printf 'CASE S3 PRE: residual; INVOKE: next reprint\n'
invoke_script next --run-dir "$runS"
assert_transition_return "$runS" "next — reprint (residual)" activity "S3 RETURN"
assert_session_closer "S3 RETURN"
assert_next_h2_has "Review-coverage is **waived**" "S3 RETURN"
assert_disk "$runS" "S3 DISK" '{"phase":"residual","receipts":{"S1":"complete"}}'
printf 'LAYER: S single-step first=last OK\n'
shiploop_sandbox_close

# =============================================================================
# Z — host wrappers shiploop-complete / shiploop-next through every stage
# =============================================================================
shiploop_sandbox_open Z
runZ="$SL_RUN"
repoZ="$SL_REPO"
init_git_repo "$repoZ"

printf 'CASE Z0 INVOKE: harness init (wrappers do not wrap init)\n'
invoke_script init --prompt "create result.txt containing exactly one line: ok" \
  --run-dir "$runZ" --bound-plan "$planf" --repo "$repoZ"
assert_transition_return "$runZ" \
  "initialized $(python3 -c "from pathlib import Path; print(Path('$runZ') / 'state.json')")" \
  activity "Z0 RETURN"
assert_session_closer "Z0 RETURN"
assert_disk "$runZ" "Z0 DISK" "$DISK_INTAKE"

printf 'CASE Z1 PRE: intake; INVOKE: wrapper complete dest validate-spec\n'
invoke_wrapper complete --run-dir "$runZ"
assert_wrapper_then_transition "$runZ" "$WRAP_COMPLETE" "updated -> validate-spec" activity "Z1 RETURN"
assert_session_closer "Z1 RETURN"
assert_next_h2_has "Survey, then practices, then spec" "Z1 RETURN"
assert_next_h2_has "Deeply research those MCP servers" "Z1 RETURN"
assert_disk "$runZ" "Z1 DISK" "$DISK_VS"

printf 'CASE Z1n PRE: validate-spec; INVOKE: wrapper next reprint\n'
invoke_wrapper next --run-dir "$runZ"
assert_wrapper_then_transition "$runZ" "$WRAP_NEXT" "next — reprint (validate-spec)" activity "Z1n RETURN"
assert_next_h2_has "Deeply research those MCP servers" "Z1n RETURN"
assert_disk "$runZ" "Z1n DISK (unchanged)" "$DISK_VS"

printf 'CASE Z2 PRE: validate-spec + env/spec; INVOKE: wrapper complete dest plan\n'
write_environment "$runZ"
write_spec "$runZ"
invoke_wrapper complete --run-dir "$runZ"
assert_wrapper_then_transition "$runZ" "$WRAP_COMPLETE" "updated -> plan" activity "Z2 RETURN"
assert_session_closer "Z2 RETURN"
assert_next_h2_has "The spec is **frozen**" "Z2 RETURN"
assert_disk "$runZ" "Z2 DISK" "$DISK_PLAN"

printf 'CASE Z3 PRE: plan + single.json; INVOKE: wrapper complete dest implement\n'
install_dag "$runZ" single.json
invoke_wrapper complete --run-dir "$runZ"
assert_wrapper_then_transition "$runZ" "$WRAP_COMPLETE" "updated -> implement" stored "Z3 RETURN"
assert_next_has "$S1_LINEAR" "Z3 RETURN"
assert_next_has "Implement git (paste into /goal with Frozen" "Z3 RETURN"
assert_next_has "Goal until (this stored prompt is /goal A" "Z3 RETURN"
assert_next_has "Improve (paste as /goal B after produces is true" "Z3 RETURN"
assert_when_done_has "Finish S1: write the file" "Z3 RETURN"
assert_when_done_has "Key learnings:" "Z3 RETURN"
assert_when_done_lacks "complete-step" "Z3 RETURN"
assert_disk "$runZ" "Z3 DISK" "$DISK_IMP_SOLO_RUN"

printf 'CASE Z4 PRE: S1 landed (first=last); INVOKE: wrapper complete → residual\n'
host_land "$runZ" S1
invoke_wrapper complete --run-dir "$runZ"
assert_wrapper_then_transition "$runZ" "$WRAP_COMPLETE" "completed S1" activity "Z4 RETURN"
assert_next_h2_has "Review-coverage is **waived**" "Z4 RETURN"
assert_next_lacks "/goal " "Z4 RETURN"
assert_next_lacks "Implement git (paste into /goal with Frozen" "Z4 RETURN"
assert_next_lacks "Improve (paste as /goal B after produces is true" "Z4 RETURN"
assert_session_closer "Z4 RETURN"
assert_disk "$runZ" "Z4 DISK" '{"phase":"residual","receipts":{"S1":"complete"}}'

printf 'CASE Z5 PRE: residual; INVOKE: wrapper next reprint\n'
invoke_wrapper next --run-dir "$runZ"
assert_wrapper_then_transition "$runZ" "$WRAP_NEXT" "next — reprint (residual)" activity "Z5 RETURN"
assert_session_closer "Z5 RETURN"
assert_next_h2_has "Review-coverage is **waived**" "Z5 RETURN"
assert_disk "$runZ" "Z5 DISK" '{"phase":"residual","receipts":{"S1":"complete"}}'

printf 'CASE Z6 PRE: residual waived; INVOKE: wrapper complete dest done\n'
invoke_wrapper complete --run-dir "$runZ"
assert_wrapper_then_transition "$runZ" "$WRAP_COMPLETE" "updated -> done" activity "Z6 RETURN"
assert_next_h2_has "Session closed" "Z6 RETURN"
assert_when_done_has "stop — no update" "Z6 RETURN"
assert_disk "$runZ" "Z6 DISK" '{"phase":"done","terminal":"waived","files":{"recap.html":true}}'

printf 'CASE Z7 PRE: done; INVOKE: wrapper next reprint stop, wrapper complete refused\n'
invoke_wrapper next --run-dir "$runZ"
assert_wrapper_then_transition "$runZ" "$WRAP_NEXT" "next — reprint (done)" activity "Z7 next RETURN"
assert_when_done_has "stop — no update" "Z7 next RETURN"
invoke_wrapper complete --run-dir "$runZ"
assert_rc 2 "Z7 complete"
assert_err_has "no forward transition" "Z7 complete RETURN"
assert_line1 "$WRAP_COMPLETE" "Z7 complete RETURN"
assert_no_next_packet "Z7 complete RETURN"
assert_disk "$runZ" "Z7 DISK (unchanged)" '{"phase":"done","terminal":"waived"}'
printf 'LAYER: Z wrapper call-chain OK\n'
shiploop_sandbox_close

printf 'shiploop-walk-journal.test.sh: PASS\n'
