#!/usr/bin/env bash
# test-harness-tests.sh — API-free regression suite for test-harness scripts.
# Exit 0 on full pass. No network. No coreutils `timeout` required.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SCRIPTS="$ROOT/scripts"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/th-tests.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

# Every run record goes under TMP, never under the caller's real state directory. The default-run-root tests below
# unset it for the one command they exercise.
export TEST_HARNESS_RUN_ROOT="$TMP/th-runs"

# Wall-clock cap assertions compare time measured from outside the process under test with the cap it advertises. The
# supervisor keeps about 100 ms of design margin at a 1 s cap, and interpreter starts plus scheduling delay under load come
# on top of it, so a strict external bound fails on a busy machine. The property under test is that a 60 s TERM-ignoring
# child or a blocked path resolver is cut off at the cap, so the external bound is the cap plus this slack; the
# supervisor's own monotonic clock is asserted where it records one.
TIMING_SLACK_MS="${TEST_HARNESS_TEST_TIMING_SLACK_MS:-1500}"

# The hang cases need the harness to get through discovery, policy and the first suite run (a dozen process starts) and
# only then hang in the classifier or the report writer. With a 4 s budget a busy machine spends all of it on setup and the
# run ends as STOPPED_TIMEOUT_BUDGET before the hang is reached, so these two cases use a budget with room for setup.
HANG_CAP_SECS="${TEST_HARNESS_TEST_HANG_CAP_SECS:-10}"

PASS=0
FAIL=0
# assert <name> <command...>: PASS when the command succeeds. Many checks below are Python heredocs that abort the whole
# script (set -e) when they fail; the `assert "<name>" true` lines after them only record that the heredoc ran to the end.
assert() {
  local name="$1"; shift
  if "$@"; then
    echo "  PASS  $name"
    PASS=$((PASS + 1))
  else
    echo "  FAIL  $name"
    FAIL=$((FAIL + 1))
  fi
}
assert_eq() {
  local name="$1" got="$2" want="$3"
  if [[ "$got" == "$want" ]]; then
    echo "  PASS  $name"
    PASS=$((PASS + 1))
  else
    echo "  FAIL  $name (got='$got' want='$want')"
    FAIL=$((FAIL + 1))
  fi
}
assert_json_field() {
  local name="$1" json="$2" expr="$3" want="$4"
  local got
  got="$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); v=eval(sys.argv[2]); print(json.dumps(v) if not isinstance(v,str) else v)" "$json" "$expr")"
  assert_eq "$name" "$got" "$want"
}
assert_pid_file_dead() {
  local name="$1" pid_file="$2" pid="" attempts=100
  if [[ -s "$pid_file" ]]; then
    pid="$(cat "$pid_file")"
    while [[ $attempts -gt 0 ]] && kill -0 "$pid" 2>/dev/null; do
      sleep 0.05
      attempts=$((attempts - 1))
    done
  fi
  if [[ -n "$pid" ]] && ! kill -0 "$pid" 2>/dev/null; then
    echo "  PASS  $name"
    PASS=$((PASS + 1))
  else
    echo "  FAIL  $name (pid_file='$pid_file' pid='${pid:-missing}' still alive)"
    FAIL=$((FAIL + 1))
    [[ -z "$pid" ]] || kill -KILL "$pid" 2>/dev/null || true
  fi
}

echo "=== test-harness self-tests ==="
echo "SCRIPTS=$SCRIPTS TMP=$TMP"

# ---------------------------------------------------------------------------
# helpers: mini git repo
# ---------------------------------------------------------------------------
make_repo() {
  local d="$1"
  mkdir -p "$d"
  git -C "$d" init -q
  git -C "$d" config user.email "th@test"
  git -C "$d" config user.name "th"
  echo "hello" > "$d/README.md"
  mkdir -p "$d/src"
  echo "exports.x=1" > "$d/src/app.js"
  git -C "$d" add .
  git -C "$d" commit -qm "init"
}

# ---------------------------------------------------------------------------
echo "--- discover-test-cmd.sh ---"
# ---------------------------------------------------------------------------
DREPO="$TMP/disc"
make_repo "$DREPO"

# makefile with test-fast
cat > "$DREPO/Makefile" <<'MF'
.PHONY: test-fast test
test-fast:
	@echo fast
test:
	@echo fullish
MF
out="$(bash "$SCRIPTS/discover-test-cmd.sh" --repo "$DREPO")"
assert_json_field "discover prefers test-fast" "$out" "d['profile']" "fast"
assert_json_field "discover cmd make test-fast" "$out" "d['cmd']" "make test-fast"

# only generic test → unknown
rm -f "$DREPO/Makefile"
cat > "$DREPO/Makefile" <<'MF'
test:
	@echo generic
MF
out="$(bash "$SCRIPTS/discover-test-cmd.sh" --repo "$DREPO")"
assert_json_field "generic make test → unknown" "$out" "d['profile']" "unknown"

# package.json test:fast
rm -f "$DREPO/Makefile"
cat > "$DREPO/package.json" <<'PJ'
{"scripts":{"test:fast":"echo f","test":"echo t"}}
PJ
out="$(bash "$SCRIPTS/discover-test-cmd.sh" --repo "$DREPO")"
assert_json_field "npm test:fast profile fast" "$out" "d['profile']" "fast"

# package.json only test → unknown
cat > "$DREPO/package.json" <<'PJ'
{"scripts":{"test":"echo t"}}
PJ
out="$(bash "$SCRIPTS/discover-test-cmd.sh" --repo "$DREPO")"
assert_json_field "npm test → unknown" "$out" "d['profile']" "unknown"

# no candidate
EMPTY="$TMP/empty"
make_repo "$EMPTY"
set +e
out="$(bash "$SCRIPTS/discover-test-cmd.sh" --repo "$EMPTY" 2>/dev/null)"
ec=$?
set -e
assert_eq "no candidate exit 2" "$ec" "2"
assert_json_field "no candidate error" "$out" "d.get('error')" "no_deterministic_candidate"

# ---------------------------------------------------------------------------
echo "--- run-suite.sh (timeout + TMPDIR) ---"
# ---------------------------------------------------------------------------
RREPO="$TMP/runrepo"
make_repo "$RREPO"
ROUT="$TMP/runout"

# successful short cmd
set +e
bash "$SCRIPTS/run-suite.sh" --repo "$RREPO" --cmd "echo ok-suite" --out "$ROUT/ok" --timeout-secs 30
ec=$?
set -e
assert_eq "run-suite exit 0" "$ec" "0"
assert "meta.json exists" test -f "$ROUT/ok/meta.json"
assert "stdout captured" grep -q "ok-suite" "$ROUT/ok/stdout.log"
assert "tmpdir pinned exists" test -d "$ROUT/ok/tmp"
assert "run-suite output tree and raw logs are private" python3 -c "
import stat
from pathlib import Path
root=Path('$ROUT/ok')
assert stat.S_IMODE(root.stat().st_mode) == 0o700
assert stat.S_IMODE((root/'tmp').stat().st_mode) == 0o700
for name in ('stdout.log', 'stderr.log', 'meta.json'):
    assert stat.S_IMODE((root/name).stat().st_mode) == 0o600, name
"

# Every caller-controlled artifact target must be opened exclusively. Direct
# files are never truncated, regardless of which creation step collides.
for artifact in stdout.log stderr.log meta.json; do
  artifact_slug="${artifact//./-}"
  precreated_dir="$ROUT/precreated-$artifact_slug"
  mkdir -p "$precreated_dir"
  printf 'sentinel\n' >"$precreated_dir/$artifact"
  set +e
  precreated_out="$(bash "$SCRIPTS/run-suite.sh" --repo "$RREPO" \
    --cmd "printf compromised" --out "$precreated_dir" \
    --timeout-secs 30 2>&1)"
  ec=$?
  set -e
  assert_eq "run-suite rejects pre-existing $artifact" "$ec" "2"
  assert_eq "run-suite leaves pre-existing $artifact untouched" \
    "$(cat "$precreated_dir/$artifact")" "sentinel"
done

# Inject a symlink after the old shell precheck point but before artifact open.
# This is a deterministic regression for check-then-truncating-open races.
COLLISION_HOOK="$TMP/artifact-collision-hook"
mkdir -p "$COLLISION_HOOK"
cat >"$COLLISION_HOOK/sitecustomize.py" <<'PY'
import os

artifact = os.environ.get("TEST_HARNESS_COLLISION_ARTIFACT", "")
target = os.environ.get("TEST_HARNESS_COLLISION_TARGET", "")
if artifact and target and not os.path.lexists(artifact):
    os.symlink(target, artifact)
PY
for artifact in stdout.log stderr.log meta.json; do
  artifact_slug="${artifact//./-}"
  collision_dir="$ROUT/collision-$artifact_slug"
  collision_target="$ROUT/collision-$artifact_slug-target"
  mkdir -p "$collision_dir"
  printf 'sentinel\n' >"$collision_target"
  set +e
  collision_out="$(
    PYTHONPATH="$COLLISION_HOOK" \
    TEST_HARNESS_COLLISION_ARTIFACT="$collision_dir/$artifact" \
    TEST_HARNESS_COLLISION_TARGET="$collision_target" \
      bash "$SCRIPTS/run-suite.sh" --repo "$RREPO" \
        --cmd "printf compromised" --out "$collision_dir" \
        --timeout-secs 30 2>&1
  )"
  ec=$?
  set -e
  assert_eq "run-suite rejects raced $artifact symlink" "$ec" "2"
  assert "run-suite reports exclusive $artifact collision" grep -q \
    "refusing to overwrite pre-existing run artifact: $artifact" \
    <<<"$collision_out"
  assert_eq "run-suite never follows raced $artifact symlink" \
    "$(cat "$collision_target")" "sentinel"
done

# Replacing paths after successful creation must not redirect later writes.
# In particular, meta.json is finalized only after the child exits, so its
# exclusive descriptor must remain open across the whole suite lifecycle.
retained_dir="$ROUT/retained-descriptors"
retained_targets="$ROUT/retained-targets"
mkdir -p "$retained_targets"
for artifact in stdout.log stderr.log meta.json; do
  printf 'sentinel\n' >"$retained_targets/$artifact"
done
set +e
TEST_HARNESS_RETAINED_TARGETS="$retained_targets" \
  bash "$SCRIPTS/run-suite.sh" --repo "$RREPO" \
    --cmd '
      mv "$STDOUT_LOG" "$STDOUT_LOG.retained"
      ln -s "$TEST_HARNESS_RETAINED_TARGETS/stdout.log" "$STDOUT_LOG"
      mv "$STDERR_LOG" "$STDERR_LOG.retained"
      ln -s "$TEST_HARNESS_RETAINED_TARGETS/stderr.log" "$STDERR_LOG"
      if [[ -e "$META" ]]; then mv "$META" "$META.retained"; fi
      ln -s "$TEST_HARNESS_RETAINED_TARGETS/meta.json" "$META"
      printf "retained stdout\n"
      printf "retained stderr\n" >&2
    ' --out "$retained_dir" --timeout-secs 30
ec=$?
set -e
assert_eq "run-suite retains artifact descriptors after path replacement" \
  "$ec" "0"
for artifact in stdout.log stderr.log meta.json; do
  assert_eq "retained $artifact never writes through replacement symlink" \
    "$(cat "$retained_targets/$artifact")" "sentinel"
done
assert "retained stdout descriptor captures child output" grep -q \
  'retained stdout' "$retained_dir/stdout.log.retained"
assert "retained stderr descriptor captures child output" grep -q \
  'retained stderr' "$retained_dir/stderr.log.retained"
assert "retained meta descriptor receives final metadata" python3 -c "
import json
assert json.load(open('$retained_dir/meta.json.retained'))['exit'] == 0
"

# Direct supervisor invocations must not bypass the one-hour outer cap.
set +e
run_suite_cap_out="$(bash "$SCRIPTS/run-suite.sh" --repo "$RREPO" --cmd "true" \
  --out "$ROUT/over-cap" --timeout-secs 3601 2>&1)"
ec=$?
set -e
assert_eq "run-suite rejects --timeout-secs above cap" "$ec" "2"
assert "run-suite reports one-hour cap" grep -q \
  "suite timeout must not exceed 3600 seconds (got '3601')" <<<"$run_suite_cap_out"

set +e
run_suite_env_cap_out="$(TEST_HARNESS_TIMEOUT=3601 bash "$SCRIPTS/run-suite.sh" \
  --repo "$RREPO" --cmd "true" --out "$ROUT/env-over-cap" 2>&1)"
ec=$?
set -e
assert_eq "run-suite rejects TEST_HARNESS_TIMEOUT above cap" "$ec" "2"
assert "run-suite reports env one-hour cap" grep -q \
  "suite timeout must not exceed 3600 seconds (got '3601')" <<<"$run_suite_env_cap_out"

cat > "$RREPO/ignore-term.py" <<'PY'
import os
import signal
import sys
import time
from pathlib import Path

signal.signal(signal.SIGTERM, signal.SIG_IGN)
Path(sys.argv[1]).write_text(str(os.getpid()))
time.sleep(60)
PY

# On timeout, the shell leader exits on TERM while its descendant ignores TERM.
# The supervisor must continue tracking the group and escalate the descendant.
set +e
bash "$SCRIPTS/run-suite.sh" --repo "$RREPO" \
  --cmd 'python3 ignore-term.py "$TMPDIR/timeout-child.pid" & while [[ ! -s "$TMPDIR/timeout-child.pid" ]]; do sleep 0.01; done; wait' \
  --out "$ROUT/hang" --timeout-secs 2
ec=$?
set -e
assert_eq "timeout exit 124" "$ec" "124"
sig="$(python3 -c "import json;print(json.load(open('$ROUT/hang/meta.json'))['error_sig'])")"
assert_eq "timeout error_sig" "$sig" "timeout"
duration_ms="$(python3 -c "import json;print(json.load(open('$ROUT/hang/meta.json'))['duration_ms'])")"
assert "timeout duration stays strictly below advertised cap" \
  test "$duration_ms" -lt 2000
assert_pid_file_dead "timeout TERM-ignoring descendant killed" "$ROUT/hang/tmp/timeout-child.pid"

# A shell can return its own status while leaving a TERM-ignoring background
# child behind. Cleanup must escalate without overwriting the shell status.
set +e
bash "$SCRIPTS/run-suite.sh" --repo "$RREPO" \
  --cmd 'python3 ignore-term.py "$TMPDIR/normal-child.pid" & while [[ ! -s "$TMPDIR/normal-child.pid" ]]; do sleep 0.01; done; exit 7' \
  --out "$ROUT/normal-background" --timeout-secs 30
ec=$?
set -e
assert_eq "normal shell exit retained with background child" "$ec" "7"
assert_eq "normal background meta exit retained" \
  "$(python3 -c "import json;print(json.load(open('$ROUT/normal-background/meta.json'))['exit'])")" "7"
assert_pid_file_dead "normal background descendant killed" "$ROUT/normal-background/tmp/normal-child.pid"

# TMPDIR is visible to child
set +e
bash "$SCRIPTS/run-suite.sh" --repo "$RREPO" \
  --cmd 'python3 -c "import os; open(os.path.join(os.environ[\"TMPDIR\"],\"marker\"),\"w\").write(\"x\")"' \
  --out "$ROUT/tmppin" --timeout-secs 30
ec=$?
set -e
assert_eq "tmpdir write exit 0" "$ec" "0"
assert "child wrote under pinned tmp" test -f "$ROUT/tmppin/tmp/marker"

# The enclosing supervisor must bound setup, suite, audit, report, teardown, and
# all descendants—not merely the child command managed by run-suite.sh.
HARD_SUP_OUT="$TMP/hard-supervisor"
HARD_SUP_PID="$HARD_SUP_OUT/term-resistant.pid"
HARD_SUP_SECRET="harness-emergency-secret-must-not-persist"
mkdir -p "$HARD_SUP_OUT"
hard_started_ms="$(python3 -c 'import time; print(int(time.time() * 1000))')"
set +e
python3 "$SCRIPTS/run-harness-hard-supervisor.py" \
  --timeout-secs 1 --repo "$RREPO" --run-dir "$HARD_SUP_OUT" \
  -- bash -c 'python3 "$1" "$2" & while [[ ! -s "$2" ]]; do sleep 0.01; done; wait' \
    _ "$RREPO/ignore-term.py" "$HARD_SUP_PID" "$HARD_SUP_SECRET"
ec=$?
set -e
hard_finished_ms="$(python3 -c 'import time; print(int(time.time() * 1000))')"
hard_duration_ms=$((hard_finished_ms - hard_started_ms))
assert_eq "hard lifecycle supervisor exits 124" "$ec" "124"
assert "hard lifecycle duration stays near the advertised cap" \
  test "$hard_duration_ms" -lt $((1000 + TIMING_SLACK_MS))
assert "hard lifecycle timeout evidence exists" \
  test -f "$HARD_SUP_OUT/hard-timeout.json"
assert "hard lifecycle evidence records an elapsed time inside the cap" python3 -c "
import json
doc=json.load(open('$HARD_SUP_OUT/hard-timeout.json'))
assert 0 < doc['elapsed_ms'] < 1000, doc
"
assert "hard lifecycle evidence omits raw command secrets" \
  bash -c '! grep -Fq "$1" "$2"' _ \
    "$HARD_SUP_SECRET" "$HARD_SUP_OUT/hard-timeout.json"
assert "hard lifecycle evidence records only bounded command metadata" python3 -c "
import json
doc=json.load(open('$HARD_SUP_OUT/hard-timeout.json'))
assert 'worker_command' not in doc, doc
assert doc['worker_executable']=='bash', doc
assert doc['worker_argument_count']==6, doc
"
assert_pid_file_dead "hard lifecycle kills TERM-ignoring descendant" "$HARD_SUP_PID"

# The independent failsafe is armed before Path.resolve. Injecting a blocked
# resolver must terminate before the advertised lifecycle cap and never launch
# the worker.
SETUP_BLOCK_HOOK="$TMP/setup-block-hook"
SETUP_BLOCK_MARKER="$TMP/setup-block-worker-started"
mkdir -p "$SETUP_BLOCK_HOOK"
cat >"$SETUP_BLOCK_HOOK/sitecustomize.py" <<'PY'
from pathlib import Path
import time

def blocked_resolve(self, *args, **kwargs):
    time.sleep(60)
    raise AssertionError("setup watchdog failed")

Path.resolve = blocked_resolve
PY
setup_block_started_ms="$(python3 -c 'import time; print(int(time.time() * 1000))')"
set +e
PYTHONPATH="$SETUP_BLOCK_HOOK" \
  python3 "$SCRIPTS/run-harness-hard-supervisor.py" \
    --timeout-secs 1 --repo "$RREPO" --run-dir "$TMP/setup-block-run" \
    -- bash -c 'touch "$1"' _ "$SETUP_BLOCK_MARKER" \
    >"$TMP/setup-block.out" 2>&1
ec=$?
set -e
setup_block_finished_ms="$(python3 -c 'import time; print(int(time.time() * 1000))')"
setup_block_duration_ms=$((setup_block_finished_ms - setup_block_started_ms))
assert_eq "hard lifecycle bounds blocked path setup" "$ec" "124"
assert "blocked path setup finishes near the advertised cap" \
  test "$setup_block_duration_ms" -lt $((1000 + TIMING_SLACK_MS))
assert "blocked path setup never launches worker" \
  test ! -e "$SETUP_BLOCK_MARKER"

# Emergency evidence uses the same exclusive/no-follow discipline. Both a
# direct file and a symlink collision must survive the timeout unchanged.
for evidence_kind in file symlink; do
  evidence_dir="$TMP/hard-evidence-$evidence_kind"
  evidence_path="$evidence_dir/hard-timeout.json"
  evidence_target="$TMP/hard-evidence-$evidence_kind-target"
  mkdir -p "$evidence_dir"
  if [[ "$evidence_kind" == "file" ]]; then
    printf 'sentinel\n' >"$evidence_path"
  else
    printf 'sentinel\n' >"$evidence_target"
    ln -s "$evidence_target" "$evidence_path"
  fi
  set +e
  evidence_out="$(
    python3 "$SCRIPTS/run-harness-hard-supervisor.py" \
      --timeout-secs 1 --repo "$RREPO" --run-dir "$evidence_dir" \
      -- bash -c 'sleep 60' 2>&1
  )"
  ec=$?
  set -e
  assert_eq "hard timeout rejects $evidence_kind evidence collision" \
    "$ec" "124"
  assert "hard timeout reports $evidence_kind evidence refusal" grep -q \
    'refusing to replace timeout evidence at hard-timeout.json' \
    <<<"$evidence_out"
  if [[ "$evidence_kind" == "file" ]]; then
    evidence_observed="$evidence_path"
  else
    evidence_observed="$evidence_target"
  fi
  assert_eq "hard timeout leaves $evidence_kind collision target untouched" \
    "$(cat "$evidence_observed")" "sentinel"
done

# Cancellation must cross every cooperating session boundary. This synthetic
# supervisor deliberately delays forwarding before reaping a TERM-resistant
# leaf, reproducing the run-harness -> run-suite -> nested-supervisor topology.
cat > "$RREPO/nested-forwarder.py" <<'PY'
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

leaf_script, leaf_pid_file, own_pid_file = sys.argv[1:]
Path(own_pid_file).write_text(str(os.getpid()))
leaf = subprocess.Popen(
    [sys.executable, leaf_script, leaf_pid_file],
    start_new_session=True,
)
received_signal = None
received_at = None
sent_to_leaf = False
kill_at = None

def receive(sig, _frame):
    global received_signal, received_at
    if received_signal is None:
        received_signal = sig
        received_at = time.monotonic()

for handled in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
    signal.signal(handled, receive)

while True:
    rc = leaf.poll()
    if rc is not None:
        if received_signal is not None:
            raise SystemExit(128 + received_signal)
        raise SystemExit(rc)
    now = time.monotonic()
    if received_signal is not None and not sent_to_leaf:
        if now - received_at >= 0.15:
            try:
                os.killpg(leaf.pid, received_signal)
            except ProcessLookupError:
                pass
            sent_to_leaf = True
            kill_at = now + 0.15
    elif sent_to_leaf and now >= kill_at:
        try:
            os.killpg(leaf.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    time.sleep(0.01)
PY

run_nested_supervision_case() {
  local signal_name="$1"
  local hard_timeout="$2"
  local expected_exit="$3"
  local case_name="$4"
  python3 - \
    "$SCRIPTS/run-harness-hard-supervisor.py" \
    "$SCRIPTS/run-suite.sh" \
    "$RREPO" \
    "$ROUT/nested-$case_name" \
    "$signal_name" \
    "$hard_timeout" \
    "$expected_exit" <<'PY'
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

supervisor, run_suite, repo, case_root, signal_name, timeout_raw, expected_raw = sys.argv[1:]
case_path = Path(case_root)
suite_out = case_path / "suite"
run_dir = case_path / "outer"
leaf_pid_file = suite_out / "tmp" / "nested-leaf.pid"
forwarder_pid_file = suite_out / "tmp" / "nested-forwarder.pid"
cmd = [
    sys.executable,
    supervisor,
    "--timeout-secs",
    timeout_raw,
    "--repo",
    repo,
    "--run-dir",
    str(run_dir),
    "--",
    "bash",
    run_suite,
    "--repo",
    repo,
    "--cmd",
    (
        'python3 nested-forwarder.py ignore-term.py "$TMPDIR/nested-leaf.pid" '
        '"$TMPDIR/nested-forwarder.pid"'
    ),
    "--out",
    str(suite_out),
    "--timeout-secs",
    "10",
]
started = time.monotonic()
proc = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)
deadline = time.monotonic() + 3
while time.monotonic() < deadline:
    if leaf_pid_file.is_file() and forwarder_pid_file.is_file():
        break
    if proc.poll() is not None:
        break
    time.sleep(0.02)

if signal_name != "NONE" and proc.poll() is None:
    proc.send_signal(getattr(signal, signal_name))

try:
    stdout, stderr = proc.communicate(timeout=7)
except subprocess.TimeoutExpired:
    proc.kill()
    stdout, stderr = proc.communicate()

def read_pid(path):
    try:
        return int(path.read_text())
    except (OSError, ValueError):
        return None

def alive(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True

leaf_pid = read_pid(leaf_pid_file)
forwarder_pid = read_pid(forwarder_pid_file)
dead_deadline = time.monotonic() + 1
while time.monotonic() < dead_deadline and (
    alive(leaf_pid) or alive(forwarder_pid)
):
    time.sleep(0.02)

print(json.dumps({
    "exit": proc.returncode,
    "expected_exit": int(expected_raw),
    "elapsed_ms": int((time.monotonic() - started) * 1000),
    "leaf_pid_recorded": leaf_pid is not None,
    "forwarder_pid_recorded": forwarder_pid is not None,
    "leaf_alive": alive(leaf_pid),
    "forwarder_alive": alive(forwarder_pid),
    "hard_timeout_evidence": (run_dir / "hard-timeout.json").is_file(),
    "stdout_tail": stdout[-400:],
    "stderr_tail": stderr[-400:],
}))
PY
}

nested_int_json="$(run_nested_supervision_case SIGINT 10 130 int)"
assert_json_field "nested SIGINT preserves exit 130" "$nested_int_json" \
  "d['exit']==d['expected_exit']" "true"
assert_json_field "nested SIGINT records both owned processes" "$nested_int_json" \
  "d['leaf_pid_recorded'] and d['forwarder_pid_recorded']" "true"
assert_json_field "nested SIGINT reaps every detached level" "$nested_int_json" \
  "not d['leaf_alive'] and not d['forwarder_alive']" "true"

nested_term_json="$(run_nested_supervision_case SIGTERM 10 143 term)"
assert_json_field "nested SIGTERM preserves exit 143" "$nested_term_json" \
  "d['exit']==d['expected_exit']" "true"
assert_json_field "nested SIGTERM reaps every detached level" "$nested_term_json" \
  "not d['leaf_alive'] and not d['forwarder_alive']" "true"

nested_hup_json="$(run_nested_supervision_case SIGHUP 10 129 hup)"
assert_json_field "nested SIGHUP preserves exit 129" "$nested_hup_json" \
  "d['exit']==d['expected_exit']" "true"
assert_json_field "nested SIGHUP records both owned processes" "$nested_hup_json" \
  "d['leaf_pid_recorded'] and d['forwarder_pid_recorded']" "true"
assert_json_field "nested SIGHUP reaps every detached level" "$nested_hup_json" \
  "not d['leaf_alive'] and not d['forwarder_alive']" "true"

nested_timeout_json="$(run_nested_supervision_case NONE 4 124 timeout)"
assert_json_field "nested hard timeout preserves exit 124" "$nested_timeout_json" \
  "d['exit']==d['expected_exit']" "true"
assert_json_field "nested hard timeout stays near the cap" "$nested_timeout_json" \
  "d['elapsed_ms'] < $((4000 + TIMING_SLACK_MS))" "true"
assert_json_field "nested hard timeout reaps every detached level" "$nested_timeout_json" \
  "not d['leaf_alive'] and not d['forwarder_alive']" "true"
assert_json_field "nested hard timeout writes emergency evidence" "$nested_timeout_json" \
  "d['hard_timeout_evidence']" "true"

# ---------------------------------------------------------------------------
echo "--- porcelain-delta.py ---"
# ---------------------------------------------------------------------------
PREPO="$TMP/porc"
make_repo "$PREPO"
POUT="$TMP/porc-out"
mkdir -p "$POUT"

# baseline clean snapshot
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT" --round 1 --mode snapshot --side pre >/dev/null
assert "pre manifest" test -f "$POUT/round-1/pre/manifest.json"
assert "invoke-baseline write-once" test -f "$POUT/invoke-baseline/manifest.json"

# dirty a tracked file + add untracked
echo "mutated" > "$PREPO/src/app.js"
echo "new" > "$PREPO/src/newfile.js"
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT" --round 1 --mode snapshot --side post >/dev/null
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT" --round 1 --mode diff >/dev/null
assert "delta.json" test -f "$POUT/round-1/delta.json"

# check classifications
python3 - <<PY
import json, sys
d=json.load(open("$POUT/round-1/delta.json"))
by={x["path"]:x for x in d["delta"]}
assert "src/app.js" in by, by
assert by["src/app.js"]["change"]=="content_changed", by["src/app.js"]
assert by["src/app.js"]["dirty_at_pre"] is False or True  # was clean at pre
# app.js was clean at pre (not in pre dirty), so dirty_at_pre False
assert by["src/app.js"]["dirty_at_pre"] is False, by["src/app.js"]
assert "src/newfile.js" in by
assert by["src/newfile.js"]["change"]=="added", by["src/newfile.js"]
print("delta content ok")
PY
assert "content_changed + added classified" true

# Shared-tree restore defaults fail closed: preserve every post state because a
# concurrent write is indistinguishable from suite output.
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT" --round 1 --mode restore >/dev/null
assert_eq "shared restore preserves changed app.js" "$(cat "$PREPO/src/app.js")" "mutated"
assert "shared restore preserves added newfile" test -e "$PREPO/src/newfile.js"
python3 - <<PY
import json
r=json.load(open("$POUT/round-1/restore.json"))
assert r["restore_policy"]=="preserve-shared", r
assert r["preserved_post_state_count"]==2, r
assert r["manual_reconciliation_required"] is True, r
assert {a["action"] for a in r["actions"]}=={"preserve-shared-post-state"}, r
print("shared restore preserves all post state")
PY
assert "shared restore report records manual reconciliation" true

# A harness-owned disposable worktree may restore clean-tracked bytes and
# delete absent-at-pre additions.
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT" --round 1 \
  --mode restore --restore-policy revert-disposable >/dev/null
assert_eq "restored app.js" "$(cat "$PREPO/src/app.js")" "exports.x=1"
assert "deleted newfile" test ! -e "$PREPO/src/newfile.js"

# --- already-M rewrite detection (hash) ---
# make WIP dirty at pre
echo "wip" > "$PREPO/src/app.js"
POUT2="$TMP/porc2"
mkdir -p "$POUT2"
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT2" --round 1 --mode snapshot --side pre >/dev/null
# suite rewrites again
echo "suite-rewrite" > "$PREPO/src/app.js"
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT2" --round 1 --mode snapshot --side post >/dev/null
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT2" --round 1 --mode diff >/dev/null
python3 - <<PY
import json
d=json.load(open("$POUT2/round-1/delta.json"))
by={x["path"]:x for x in d["delta"]}
assert by["src/app.js"]["change"]=="content_changed"
assert by["src/app.js"]["dirty_at_pre"] is True
assert by["src/app.js"]["pre_sha256"] != by["src/app.js"]["post_sha256"]
print("already-M rewrite detected")
PY
assert "already-M content hash delta" true

# Restore is fail-closed for dirty-at-pre paths: keep the exact post bytes.
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT2" --round 1 \
  --mode restore --restore-policy revert-disposable >/dev/null
assert_eq "dirty-pre changed path preserves post bytes" "$(cat "$PREPO/src/app.js")" "suite-rewrite"
python3 - <<PY
import json
r=json.load(open("$POUT2/round-1/restore.json"))
actions={x["path"]:x for x in r["actions"]}
a=actions["src/app.js"]
assert a["action"]=="preserve-dirty-pre-post-state", a
assert a["change"]=="content_changed", a
assert a["post_exists"] is True, a
assert a["manual_reconciliation_required"] is True, a
assert r["preserved_dirty_pre_count"]==1, r
assert r["manual_reconciliation_required"] is True, r
print("dirty-pre changed preservation recorded")
PY
assert "dirty-pre changed restore report records preservation" true

# Dirty-at-pre deletion remains deleted; captured pre bytes must not recreate it.
git -C "$PREPO" checkout -- src/app.js 2>/dev/null || true
echo "dirty-before-delete" > "$PREPO/src/app.js"
POUT2D="$TMP/porc2-deleted"
mkdir -p "$POUT2D"
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT2D" --round 1 --mode snapshot --side pre >/dev/null
rm -f "$PREPO/src/app.js"
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT2D" --round 1 --mode snapshot --side post >/dev/null
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT2D" --round 1 --mode diff >/dev/null
python3 - <<PY
import json
d=json.load(open("$POUT2D/round-1/delta.json"))
a=next(x for x in d["delta"] if x["path"]=="src/app.js")
assert a["dirty_at_pre"] is True, a
assert a["change"]=="deleted", a
print("dirty-pre deletion classified")
PY
assert "dirty-pre deletion delta is explicit" true
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT2D" --round 1 \
  --mode restore --restore-policy revert-disposable >/dev/null
assert "dirty-pre deleted path stays deleted" test ! -e "$PREPO/src/app.js"
python3 - <<PY
import json
r=json.load(open("$POUT2D/round-1/restore.json"))
a=next(x for x in r["actions"] if x["path"]=="src/app.js")
assert a["action"]=="preserve-dirty-pre-post-state", a
assert a["post_exists"] is False, a
assert a["manual_reconciliation_required"] is True, a
assert r["preserved_dirty_pre_count"]==1, r
print("dirty-pre deletion preservation recorded")
PY
assert "dirty-pre deleted restore report records preservation" true

# --- tracked delete of clean file ---
POUT3="$TMP/porc3"
mkdir -p "$POUT3"
# clean tree first
git -C "$PREPO" checkout -- src/app.js 2>/dev/null || true
git -C "$PREPO" clean -fdq
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT3" --round 1 --mode snapshot --side pre >/dev/null
rm -f "$PREPO/src/app.js"
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT3" --round 1 --mode snapshot --side post >/dev/null
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT3" --round 1 --mode diff >/dev/null
python3 - <<PY
import json
d=json.load(open("$POUT3/round-1/delta.json"))
by={x["path"]:x for x in d["delta"]}
assert "src/app.js" in by, by
assert by["src/app.js"]["change"]=="deleted", by["src/app.js"]
print("tracked delete classified")
PY
assert "tracked delete → deleted" true
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT3" --round 1 \
  --mode restore --restore-policy revert-disposable >/dev/null
assert "recreated deleted tracked" test -f "$PREPO/src/app.js"

# --- fix_then_rewrite: round2 pre has fix; suite rewrite is preserved safely ---
POUT4="$TMP/porc4"
mkdir -p "$POUT4"
git -C "$PREPO" checkout -- . 2>/dev/null || true
git -C "$PREPO" clean -fdq
# round 1: suite dirties
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT4" --round 1 --mode snapshot --side pre >/dev/null
echo "bad" > "$PREPO/src/app.js"
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT4" --round 1 --mode snapshot --side post >/dev/null
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT4" --round 1 --mode diff >/dev/null
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT4" --round 1 \
  --mode restore --restore-policy revert-disposable >/dev/null
# skill fix
echo "FIXED" > "$PREPO/src/app.js"
# round 2 pre includes fix
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT4" --round 2 --mode snapshot --side pre >/dev/null
echo "suite-clobber" > "$PREPO/src/app.js"
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT4" --round 2 --mode snapshot --side post >/dev/null
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT4" --round 2 --mode diff >/dev/null
python3 "$SCRIPTS/porcelain-delta.py" --repo "$PREPO" --run-dir "$POUT4" --round 2 \
  --mode restore --restore-policy revert-disposable >/dev/null
assert_eq "fix_then_rewrite preserves post bytes" "$(cat "$PREPO/src/app.js")" "suite-clobber"

# invoke-baseline immutable check
ib1="$(python3 -c "import json;print(json.load(open('$POUT4/invoke-baseline/manifest.json'))['head'])")"
# still exists after round 2
assert "invoke-baseline still present after r2" test -f "$POUT4/invoke-baseline/manifest.json"
assert "invoke head recorded" test -n "$ib1"

# ---------------------------------------------------------------------------
echo "--- classify-side-effects.py ---"
# ---------------------------------------------------------------------------
# Build a synthetic delta
DEL="$TMP/delta.json"
cat > "$DEL" <<'DJ'
{
  "fs_scope": "full",
  "delta": [
    {"path": "src/app.js", "change": "content_changed", "dirty_at_pre": false, "restorable": true},
    {"path": "src/wip.js", "change": "deleted", "dirty_at_pre": true, "restorable": true},
    {"path": "coverage/preexisting.info", "change": "content_changed", "dirty_at_pre": true, "restorable": true},
    {"path": "coverage/lcov.info", "change": "added", "dirty_at_pre": false, "restorable": true},
    {"path": "__pycache__/x.pyc", "change": "added", "dirty_at_pre": false, "restorable": true}
  ],
  "ignored_delta": [
    {"path": "src/generated.cache", "change": "added", "sha256": "abc"}
  ]
}
DJ
COUT="$TMP/se.json"
set +e
python3 "$SCRIPTS/classify-side-effects.py" --delta "$DEL" --profile fast --out "$COUT"
ec=$?
set -e
assert_eq "classifier exits 1 on fail findings" "$ec" "1"
python3 - <<PY
import json
d=json.load(open("$COUT"))
assert d["side_effects_ok"] is False
classes={x["class"] for x in d["delta"]}
assert "UNINTENDED_WRITE" in classes
assert "EXPECTED_ARTIFACT" in classes
# ignored under src → fail
ign=[x for x in d["delta"] if x.get("class")=="IGNORED_WRITE"]
assert ign and ign[0]["disposition"]=="fail"
preserved=next(x for x in d["delta"] if x.get("path")=="src/wip.js")
assert preserved["restore_policy"]=="preserve-post-state", preserved
assert "manual reconciliation required" in preserved["resolution"], preserved
dirty_litter=next(x for x in d["delta"] if x.get("path")=="coverage/preexisting.info")
assert dirty_litter["class"]=="UNINTENDED_WRITE", dirty_litter
assert dirty_litter["disposition"]=="fail", dirty_litter
assert dirty_litter["restore_policy"]=="preserve-post-state", dirty_litter
print("classify ok")
PY
assert "unintended + litter + ignored-src + dirty-pre preservation finding" true

# LIVE_GATE_ON_FAST
export FAKE_LIVE_TEST=1
# monkey: our regex needs *_LIVE_TEST
export FOO_LIVE_TEST=1
set +e
python3 "$SCRIPTS/classify-side-effects.py" --delta "$DEL" --profile fast --out "$TMP/se2.json"
ec=$?
set -e
python3 - <<PY
import json
d=json.load(open("$TMP/se2.json"))
sv=[s for s in d["services"] if s["class"]=="LIVE_GATE_ON_FAST"]
assert sv, d["services"]
print("live gate fail")
PY
assert "LIVE_GATE_ON_FAST under fast" true
unset FOO_LIVE_TEST FAKE_LIVE_TEST

# suspect not hard-fail on provider URL in log alone when... actually it is note
LOG="$TMP/log.txt"
echo "connecting to api.openai.com/v1" > "$LOG"
# empty delta
cat > "$DEL" <<'DJ'
{"fs_scope":"full","delta":[],"ignored_delta":[]}
DJ
set +e
python3 "$SCRIPTS/classify-side-effects.py" --delta "$DEL" --profile fast --log "$LOG" --out "$TMP/se3.json"
ec=$?
set -e
assert_eq "suspect alone exit 0" "$ec" "0"
python3 - <<PY
import json
d=json.load(open("$TMP/se3.json"))
assert d["side_effects_ok"] is True
assert any(s["class"]=="LIVE_CALL_SUSPECT" for s in d["services"])
print("suspect note only")
PY
assert "LIVE_CALL_SUSPECT is note" true

# ECONNREFUSED alone → no service finding
echo "Error: connect ECONNREFUSED 127.0.0.1:9" > "$LOG"
set +e
python3 "$SCRIPTS/classify-side-effects.py" --delta "$DEL" --profile fast --log "$LOG" --out "$TMP/se4.json"
ec=$?
set -e
python3 - <<PY
import json
d=json.load(open("$TMP/se4.json"))
assert d["services"]==[] or all(s["class"]!="LIVE_CALL_SUSPECT" or "ECONN" not in s.get("excerpt","") for s in d["services"])
# our scanner skips ECONN-only lines
assert not any("ECONNREFUSED" in s.get("excerpt","") for s in d["services"])
print("econn skip")
PY
assert "ECONNREFUSED not suspect" true

# ---------------------------------------------------------------------------
echo "--- worktree-fixloop.sh ---"
# ---------------------------------------------------------------------------
WREPO="$TMP/wtrepo"
make_repo "$WREPO"
# launch WIP
echo "launch-wip" > "$WREPO/src/app.js"
WOUT="$TMP/wt-out"
mkdir -p "$WOUT"
enter_json="$(bash "$SCRIPTS/worktree-fixloop.sh" enter --repo "$WREPO" --run-dir "$WOUT" --slug demo)"
WT="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['workspace'])" "$enter_json")"
assert "worktree dir exists" test -d "$WT"
assert_eq "WIP overlay in worktree" "$(cat "$WT/src/app.js")" "launch-wip"
# launch still has wip (not restored)
assert_eq "launch unchanged" "$(cat "$WREPO/src/app.js")" "launch-wip"
# mutate only worktree
echo "fix-in-wt" > "$WT/src/app.js"
# launch bytes still launch-wip
assert_eq "launch still wip after wt edit" "$(cat "$WREPO/src/app.js")" "launch-wip"
exit_json="$(bash "$SCRIPTS/worktree-fixloop.sh" exit --repo "$WREPO" --run-dir "$WOUT")"
assert "fixes.patch written" test -f "$WOUT/fixes.patch"
assert_json_field "worktree kept" "$exit_json" "d.get('kept')" "true"
# clean case
WOUT2="$TMP/wt-out2"
mkdir -p "$WOUT2"
# reset launch
git -C "$WREPO" checkout -- src/app.js
bash "$SCRIPTS/worktree-fixloop.sh" enter --repo "$WREPO" --run-dir "$WOUT2" --slug demo2 >/dev/null
exit_json="$(bash "$SCRIPTS/worktree-fixloop.sh" exit --repo "$WREPO" --run-dir "$WOUT2")"
assert_json_field "clean worktree removed" "$exit_json" "d.get('removed')" "true"

# a repository folder name with a space and a dot must still give a valid branch name
SPACE_REPO="$TMP/my repo.v2"
make_repo "$SPACE_REPO"
SPACE_RUN="$TMP/wt-space-run"
mkdir -p "$SPACE_RUN"
set +e
space_json="$(bash "$SCRIPTS/worktree-fixloop.sh" enter --repo "$SPACE_REPO" --run-dir "$SPACE_RUN" 2>"$TMP/wt-space.err")"
ec=$?
set -e
assert_eq "fix-loop worktree enter works for a folder name with a space and a dot" "$ec" "0"
assert_json_field "fix-loop branch name is a valid, sanitised ref" "$space_json" "bool(__import__('re').fullmatch(r'test-harness/[A-Za-z0-9_-]+-[0-9a-f]{6}', d['branch']))" "true"
bash "$SCRIPTS/worktree-fixloop.sh" exit --repo "$SPACE_REPO" --run-dir "$SPACE_RUN" >/dev/null

# ---------------------------------------------------------------------------
echo "--- size cap unrestorable ---"
# ---------------------------------------------------------------------------
CREPO="$TMP/caprepo"
make_repo "$CREPO"
# create a >1KB file and set tiny cap
python3 -c "open('$CREPO/src/big.bin','wb').write(b'x'*(20*1024))"
COUT="$TMP/capout"
mkdir -p "$COUT"
python3 "$SCRIPTS/porcelain-delta.py" --repo "$CREPO" --run-dir "$COUT" --round 1 \
  --mode snapshot --side pre --per-file-cap 1000 --total-cap 5000 >/dev/null
python3 - <<PY
import json
m=json.load(open("$COUT/round-1/pre/manifest.json"))
big=[e for e in m["entries"] if e["path"].endswith("big.bin")]
assert big and big[0]["restorable"] is False
print("cap ok")
PY
assert "per-file cap → unrestorable" true

# ---------------------------------------------------------------------------
echo "--- init-run.py ---"
# ---------------------------------------------------------------------------
IR="$TMP/initrun"
python3 "$SCRIPTS/init-run.py" \
  --repo "$PREPO" --run-dir "$IR" --cmd "make test-fast" \
  --profile fast --source makefile --mode once >/dev/null
assert "init manifest exists" test -f "$IR/manifest.json"
python3 - <<PY
import json
m=json.load(open("$IR/manifest.json"))
assert m["cmd"]=="make test-fast"
assert m["profile"]=="fast"
assert m["mode"]=="once"
assert m["rounds_max"]==1
assert m["schema_version"]==1
print("init ok")
PY
assert "init-run fields" true

# ---------------------------------------------------------------------------
echo "--- classify TMPDIR relative ---"
# ---------------------------------------------------------------------------
TRUN="$TMP/tmprel"
mkdir -p "$TRUN/round-1/tmp/nested"
echo x > "$TRUN/round-1/tmp/nested/leak.bin"
# empty delta
cat > "$TRUN/round-1/delta.json" <<'DJ'
{"fs_scope":"full","delta":[],"ignored_delta":[]}
DJ
python3 "$SCRIPTS/classify-side-effects.py" \
  --delta "$TRUN/round-1/delta.json" --profile fast \
  --tmpdir "$TRUN/round-1/tmp" --run-dir "$TRUN" \
  --out "$TRUN/round-1/side-effects.json" >/dev/null
python3 - <<PY
import json
d=json.load(open("$TRUN/round-1/side-effects.json"))
leaks=[x for x in d["delta"] if x.get("class")=="TMPDIR_LEAK"]
assert leaks, d
s=leaks[0]["sample"][0]
assert not s.startswith("/"), s
assert "round-1/tmp" in s or s.endswith("leak.bin"), s
assert "not repo dirt" in leaks[0].get("hint","")
print("tmpdir rel ok", s)
PY
assert "TMPDIR sample run-relative" true

# ---------------------------------------------------------------------------
echo "--- emit-report.py ---"
# ---------------------------------------------------------------------------
# helper: build minimal pass_clean run
build_pass_run() {
  local rd="$1"
  mkdir -p "$rd/round-1"
  python3 "$SCRIPTS/init-run.py" \
    --repo "$PREPO" --run-dir "$rd" --cmd "echo ok" \
    --profile fast --source path --mode once >/dev/null
  cat > "$rd/round-1/meta.json" <<'MJ'
{"exit": 0, "duration_ms": 100, "error_sig": "none", "cmd": "echo ok"}
MJ
  echo "PASS test/foo.test.js" > "$rd/round-1/stdout.log"
  echo "" > "$rd/round-1/stderr.log"
  cat > "$rd/round-1/delta.json" <<'DJ'
{"fs_scope":"full","delta":[],"ignored_delta":[]}
DJ
  cat > "$rd/round-1/side-effects.json" <<'SJ'
{"profile":"fast","fs_scope":"full","delta":[],"services":[],"summary":{"fail":0,"note":0,"ok":0,"total":0},"side_effects_ok":true}
SJ
}

# Failure diagnostics must select a real failure, not a passing assertion whose
# descriptive text happens to contain the word FAIL.  Keep the first Error:
# outside the last 40 lines of the replay, so a selector that only reads the tail cannot find it.
EDIAG_CAPTURE="$TMP/failure-diagnostic-capture"
EDIAG_FIXTURE="$TMP/failure-diagnostic-fixture.sh"
cat > "$EDIAG_FIXTURE" <<'SH'
#!/usr/bin/env bash
printf '  option-parsing edge cases                               ✗\n'
printf '  explicit output-dir override is refused when not writable✗\n'
printf '  passing assertion text mentions FAIL                   ✓\n'
printf '✗ 2/3 suites failed\n'
printf 'PASS duplicate markers increment FAIL\n'
{
  printf 'Error: setup timed out after 1500ms (last: ECONNRESET)\n'
  for n in $(seq 1 45); do
    printf 'PASS replay filler %s\n' "$n"
  done
  printf 'PASS duplicate markers increment FAIL\n'
  for n in $(seq 1 5); do
    printf 'PASS replay tail %s\n' "$n"
  done
  printf 'FAIL explicit output-dir override is refused when not writable\n'
} >&2
exit 1
SH
chmod 700 "$EDIAG_FIXTURE"
set +e
bash "$SCRIPTS/run-suite.sh" \
  --repo "$PREPO" --out "$EDIAG_CAPTURE" --timeout-secs 30 \
  --cmd "bash '$EDIAG_FIXTURE'" >/dev/null 2>&1
ediag_rc=$?
set -e
assert_eq "diagnostic fixture exits non-zero" "$ediag_rc" "1"

EDIAG="$TMP/emit_failure_diagnostics"
build_pass_run "$EDIAG"
cp "$EDIAG_CAPTURE/meta.json" "$EDIAG/round-1/meta.json"
cp "$EDIAG_CAPTURE/stdout.log" "$EDIAG/round-1/stdout.log"
cp "$EDIAG_CAPTURE/stderr.log" "$EDIAG/round-1/stderr.log"
python3 "$SCRIPTS/emit-report.py" --run-dir "$EDIAG" >/dev/null
ediag_json="$(python3 - <<PY
import json
capture = json.load(open("$EDIAG_CAPTURE/meta.json"))
report = json.load(open("$EDIAG/report.json"))
stderr = report["suite"]["control_channels"]["stderr"]
print(json.dumps({
    "capture_sig": capture["error_sig"],
    "report_sig": report["suite"]["error_sig"],
    "result": report["result"],
    "fail_count": report["suite"]["fail_count"],
    "fail_names": sorted(
        case["name"] for case in report["suite"]["cases"]
        if case["status"] == "fail" and case.get("kind") != "rollup"
    ),
    "errorish": stderr["error_shaped_lines"],
    "error_samples": stderr["error_shaped_sample"],
}))
PY
)"
assert_json_field "run-suite diagnostic selects real Error" "$ediag_json" "d['capture_sig'].startswith('Error: setup timed out')" "true"
assert_json_field "report diagnostic selects real Error" "$ediag_json" "d['report_sig'].startswith('Error: setup timed out')" "true"
assert_json_field "diagnostic fixture remains fail-safe" "$ediag_json" "d['result']" "FAIL_SUITE"
assert_json_field "diagnostic named fail count" "$ediag_json" "d['fail_count']" "2"
assert_json_field "diagnostic named failing cases" "$ediag_json" "d['fail_names']" '["explicit output-dir override is refused when not writable", "option-parsing edge cases"]'
assert "diagnostic errorish count nonzero" python3 -c 'import json,sys; assert json.loads(sys.argv[1])["errorish"] >= 2' "$ediag_json"
assert "diagnostic error samples exclude passing FAIL text" python3 -c '
import json,sys
samples=json.loads(sys.argv[1])["error_samples"]
assert all(not line.lstrip().startswith("PASS") for line in samples), samples
' "$ediag_json"

# PASS_CLEAN
EPC="$TMP/emit_pass"
build_pass_run "$EPC"
# add TMPDIR note via classify path already in SE
python3 - <<PY
import json
from pathlib import Path
p=Path("$EPC/round-1/side-effects.json")
d=json.loads(p.read_text())
d["delta"]=[{"class":"TMPDIR_LEAK","disposition":"note","count":1,
  "sample":["round-1/tmp/x"],"sample_rel":["round-1/tmp/x"],
  "hint":"not repo dirt; optional test cleanup"}]
d["summary"]={"fail":0,"note":1,"ok":0,"total":1}
p.write_text(json.dumps(d))
PY
out="$(python3 "$SCRIPTS/emit-report.py" --run-dir "$EPC" 2>&1)"
echo "$out" | head -1 | grep -q '^test-harness RESULT=PASS_CLEAN' && assert "emit PASS_CLEAN line" true || assert "emit PASS_CLEAN line" false
assert "emit report.json" test -f "$EPC/report.json"
assert "emit results.md" test -f "$EPC/results.md"
assert "emit chat-card.md" test -f "$EPC/chat-card.md"
assert "chat has TMPDIR note" grep -q 'TMPDIR_LEAK' "$EPC/chat-card.md"
assert "chat not-repo-dirt" grep -q 'not repo dirt' "$EPC/chat-card.md"
# no --result flag
grep -nE 'add_argument.*--result' "$SCRIPTS/emit-report.py" >/dev/null 2>&1 \
  && assert "no --result flag" false || assert "no --result flag" true

# BASELINE only — paths must not appear in chat notes
EBL="$TMP/emit_base"
build_pass_run "$EBL"
python3 - <<PY
import json
from pathlib import Path
p=Path("$EBL/round-1/side-effects.json")
d=json.loads(p.read_text())
d["delta"]=[
  {"path":"docs/example/SKILL.md","class":"BASELINE","disposition":"ok","change":"unchanged-baseline"},
  {"path":"tasks/backlog/notes.md","class":"BASELINE","disposition":"ok","change":"unchanged-baseline"},
]
d["summary"]={"fail":0,"note":0,"ok":2,"total":2}
d["side_effects_ok"]=True
p.write_text(json.dumps(d))
PY
python3 "$SCRIPTS/emit-report.py" --run-dir "$EBL" >/dev/null
assert_eq "baseline RESULT PASS_CLEAN" "$(python3 -c "import json;print(json.load(open('$EBL/report.json'))['result'])")" "PASS_CLEAN"
if grep -q 'docs/example/SKILL.md' "$EBL/chat-card.md"; then
  assert "baseline omitted from chat-card" false
else
  assert "baseline omitted from chat-card" true
fi
assert "baseline in results context" grep -q 'Baseline context' "$EBL/results.md"

# FAIL_SUITE
EFS="$TMP/emit_fsuite"
build_pass_run "$EFS"
cat > "$EFS/round-1/meta.json" <<'MJ'
{"exit": 1, "duration_ms": 50, "error_sig": "FAIL foo:42"}
MJ
printf 'line\nFAIL foo:42\nassertion failed: boom\n' > "$EFS/round-1/stderr.log"
echo "" > "$EFS/round-1/stdout.log"
python3 "$SCRIPTS/emit-report.py" --run-dir "$EFS" >/dev/null
assert_eq "FAIL_SUITE result" "$(python3 -c "import json;print(json.load(open('$EFS/report.json'))['result'])")" "FAIL_SUITE"
ex="$(python3 -c "import json;print(json.load(open('$EFS/report.json'))['suite']['first_failure_excerpt'] or '')")"
echo "$ex" | grep -q 'foo:42' && assert "FAIL_SUITE excerpt" true || assert "FAIL_SUITE excerpt" false

# FAIL_SIDE_EFFECTS + once next_steps
ESE="$TMP/emit_side"
build_pass_run "$ESE"
python3 - <<PY
import json
from pathlib import Path
p=Path("$ESE/round-1/side-effects.json")
d=json.loads(p.read_text())
d["delta"]=[{"path":"src/config.json","class":"UNINTENDED_WRITE","disposition":"fail","change":"content_changed"}]
d["summary"]={"fail":1,"note":0,"ok":0,"total":1}
d["side_effects_ok"]=False
p.write_text(json.dumps(d))
PY
python3 "$SCRIPTS/emit-report.py" --run-dir "$ESE" >/dev/null
assert_eq "FAIL_SIDE_EFFECTS result" "$(python3 -c "import json;print(json.load(open('$ESE/report.json'))['result'])")" "FAIL_SIDE_EFFECTS"
ns="$(python3 -c "import json;print(' '.join(json.load(open('$ESE/report.json'))['next_steps']))")"
echo "$ns" | grep -qi 'audit-only' && assert "once next_steps audit-only" true || assert "once next_steps audit-only" false

# INCOMPLETE_RUN
EINC="$TMP/emit_inc"
mkdir -p "$EINC"
set +e
python3 "$SCRIPTS/emit-report.py" --run-dir "$EINC" >/dev/null 2>&1
ec=$?
set -e
assert_eq "INCOMPLETE_RUN exit 2" "$ec" "2"
assert_eq "INCOMPLETE result" "$(python3 -c "import json;print(json.load(open('$EINC/report.json'))['result'])")" "INCOMPLETE_RUN"

# STOPPED_SAME_ERROR
ESE3="$TMP/emit_same"
build_pass_run "$ESE3"
# upgrade to fix-loop rounds_max 5
python3 - <<PY
import json
from pathlib import Path
m=json.loads(Path("$ESE3/manifest.json").read_text())
m["mode"]="fix-loop"
m["rounds_max"]=5
Path("$ESE3/manifest.json").write_text(json.dumps(m,indent=2))
for n in (1,2,3):
    rd=Path("$ESE3") / ("round-%d" % n)
    rd.mkdir(exist_ok=True)
    (rd/"meta.json").write_text(json.dumps({"exit":1,"duration_ms":10,"error_sig":"FAIL same:1"}))
    (rd/"stdout.log").write_text("")
    (rd/"stderr.log").write_text("FAIL same:1\n")
    (rd/"delta.json").write_text(json.dumps({"fs_scope":"full","delta":[],"ignored_delta":[]}))
    (rd/"side-effects.json").write_text(json.dumps({
      "profile":"fast","fs_scope":"full","delta":[],"services":[],
      "summary":{"fail":0,"note":0,"ok":0,"total":0},"side_effects_ok":True
    }))
PY
python3 "$SCRIPTS/emit-report.py" --run-dir "$ESE3" >/dev/null
assert_eq "STOPPED_SAME_ERROR" "$(python3 -c "import json;print(json.load(open('$ESE3/report.json'))['result'])")" "STOPPED_SAME_ERROR"

# meta without SE → INCOMPLETE
EMIS="$TMP/emit_miss"
build_pass_run "$EMIS"
rm -f "$EMIS/round-1/side-effects.json"
python3 "$SCRIPTS/emit-report.py" --run-dir "$EMIS" >/dev/null 2>&1 || true
assert_eq "missing SE INCOMPLETE" "$(python3 -c "import json;print(json.load(open('$EMIS/report.json'))['result'])")" "INCOMPLETE_RUN"

# ---------------------------------------------------------------------------
echo "--- IGNORED_WRITE ambient runs note not fail ---"
# ---------------------------------------------------------------------------
IGN="$TMP/ign_runs"
mkdir -p "$IGN"
cat > "$IGN/delta.json" <<'DJ'
{"fs_scope":"full","delta":[],"ignored_delta":[
  {"path":"skills/example-skill/runs/20260724T/meta.json","change":"added"},
  {"path":"skills/example-skill/src/foo.js","change":"added"},
  {"path":".worktrees/foo/bar","change":"added"}
]}
DJ
python3 "$SCRIPTS/classify-side-effects.py" \
  --delta "$IGN/delta.json" --profile fast --out "$IGN/se.json" >/dev/null || true
python3 - <<PY
import json
d=json.load(open("$IGN/se.json"))
by={x["path"]:x for x in d["delta"] if "path" in x}
assert by["skills/example-skill/runs/20260724T/meta.json"]["disposition"]=="note", by
assert by[".worktrees/foo/bar"]["disposition"]=="note", by
# product-ish under skills/.../src stays fail
assert by["skills/example-skill/src/foo.js"]["disposition"]=="fail", by
print("ignored ambient ok")
PY
assert "ambient runs/ IGNORED_WRITE is note" true

# ignored_write_note_globs in a YAML policy is a list of its own and makes a path note-only (it used to be appended to
# whichever list key came before it, or dropped when none did)
IGNG="$TMP/ign_globs"
mkdir -p "$IGNG"
cat > "$IGNG/policy.yml" <<'YML'
ignored_write_note_globs:
  - "generated-output/"
YML
cat > "$IGNG/delta.json" <<'DJ'
{"fs_scope":"full","delta":[],"ignored_delta":[
  {"path":"src/generated-output/a.txt","change":"added"},
  {"path":"src/other/b.txt","change":"added"}
]}
DJ
python3 "$SCRIPTS/classify-side-effects.py" \
  --delta "$IGNG/delta.json" --profile fast --allowlist "$IGNG/policy.yml" --out "$IGNG/se.json" >/dev/null || true
assert "ignored_write_note_globs in a YAML policy makes a path note-only" python3 -c "
import json
d=json.load(open('$IGNG/se.json'))
by={x['path']:x for x in d['delta'] if 'path' in x}
assert by['src/generated-output/a.txt']['disposition']=='note', by
assert by['src/other/b.txt']['disposition']=='fail', by
"

# ---------------------------------------------------------------------------
echo "--- emit suite cases + control channels ---"
# ---------------------------------------------------------------------------
ECC="$TMP/emit_cases"
build_pass_run "$ECC"
cat > "$ECC/round-1/stdout.log" <<'LOG'
runner start
foo.test.js: all assertions passed
PASS test/foo.test.js
bar detail line
PASS test/bar.test.js
Results: 2 passed, 0 failed
LOG
cat > "$ECC/round-1/stderr.log" <<'LOG'
Usage: helper --help
info: ready
LOG
python3 "$SCRIPTS/emit-report.py" --run-dir "$ECC" >/dev/null
python3 - <<PY
import json
r=json.load(open("$ECC/report.json"))
s=r["suite"]
assert s["pass_count"]==2, s
assert s["case_count"]==2, s["cases"]
names=[c["name"] for c in s["cases"]]
assert "test/foo.test.js" in names and "test/bar.test.js" in names
assert s["cases"][0].get("observation")  # detail before PASS
assert {g["id"] for g in s["case_inventory"]["groups"]}=={"file_suite"}, s["case_inventory"]["groups"]
cc=s["control_channels"]
assert cc["evaluated"] is True
assert cc["stdout"]["bytes"]>0
assert cc["stderr"]["status"]=="noise_on_success"
assert any("exit 0 consistent" in x for x in cc["consistency"])
md=open("$ECC/results.md").read()
assert "## What ran & was verified" in md
assert "## Test cases" in md
assert "test/foo.test.js" in md
assert "## Control channels" in md
assert "stdout" in md and "stderr" in md
assert "## Final result" in md or "## Worked well" in md
card=open("$ECC/chat-card.md").read()
assert "## Final result" in card
assert "## What ran & was verified" in card
assert "## Worked well" in card
assert "## Struggles" in card and "## Dive in" in card
assert "report.html" in card
assert "test/foo.test.js" in card
assert "test/bar.test.js" in card
print("cases+channels ok")
PY
assert "suite cases + control channels in report" true

# story + HTML on pass_clean fixture
python3 - <<PY
import json
from pathlib import Path
r=json.load(open("$ECC/report.json"))
assert "story" in r, r.keys()
st=r["story"]
assert st.get("final_sentence")
assert st.get("worked_well")
assert isinstance(st.get("struggles"), list)
assert st.get("dive_in",{}).get("html")
assert st.get("case_inventory"), st.keys()
inv=st["case_inventory"]
assert inv.get("real_case_count")==2, inv
assert "case_inventory" in r["suite"]
assert Path("$ECC/report.html").is_file()
html=Path("$ECC/report.html").read_text()
assert "What ran" in html and "Worked well" in html and "Struggles" in html and "Dive in" in html
assert "PASS_CLEAN" in html or r["result"] in html
card=Path("$ECC/chat-card.md").read_text()
assert "## Final result" in card and "## What ran & was verified" in card
assert "## Worked well" in card
assert "## Struggles" in card and "## Dive in" in card
assert "report.html" in card
# struggles include TMPDIR note from earlier fixture mutation on EPC - use ECC which has clean SE
# re-emit EPC which has TMPDIR
print("story+html ok")
PY
assert "story + HTML sections" true

# ---------------------------------------------------------------------------
echo "--- emit rollup filter + case inventory narrative ---"
# ---------------------------------------------------------------------------
EROLL="$TMP/emit_rollup"
build_pass_run "$EROLL"
cat > "$EROLL/round-1/stdout.log" <<'LOG'
PASS test_parse_accepts_trailing_comma
PASS test_parse_rejects_unterminated_string
PASS 2 parser tests
PASS test_render_escapes_markup
PASS test_render_handles_empty_input
PASS 2 renderer tests
LOG
: > "$EROLL/round-1/stderr.log"
python3 "$SCRIPTS/emit-report.py" --run-dir "$EROLL" >/dev/null
python3 - <<PY
import json
r=json.load(open("$EROLL/report.json"))
s=r["suite"]
inv=s["case_inventory"]
assert inv["real_case_count"]==4, inv
assert inv["rollup_count"]==2, inv  # "2 parser tests", "2 renderer tests"
assert s["pass_count"]==4, s
names=set(inv["passed_names"])
assert "test_parse_accepts_trailing_comma" in names
assert "2" not in names
# no group rule ships by default: names with no path shape fall into the generic group, and no claim is invented
gids={g["id"] for g in inv["groups"]}
assert gids=={"other"}, gids
assert all(g["verifies"]=="suite-reported case (see name)" for g in inv["groups"]), inv["groups"]
card=open("$EROLL/chat-card.md").read()
assert "## What ran & was verified" in card
assert "Groups — what was verified" in card
assert "Case inventory" in card
assert "test_render_escapes_markup" in card
assert "Other cases" in card
md=open("$EROLL/results.md").read()
assert md.index("## What ran & was verified") < md.index("## Worked well")
html=open("$EROLL/report.html").read()
assert "What ran" in html and "What was verified" in html
print("rollup+inventory ok", inv["pass_count"], "groups", len(inv["groups"]))
PY
assert "rollup filter + case inventory narrative" true

# A runner may emit a width-padded label per suite followed by ✓/✗/SKIP, then a
# leading-status suite rollup. Exercise pass, fail, skip, long labels that use
# the whole pad width, and harmless API-key mentions in skip labels.
ERUNALL="$TMP/emit_runall"
build_pass_run "$ERUNALL"
{
  printf '  %-55s%s\n' "alpha-suite (basic cases and idempotency)" "✓"
  printf '  %-55s%s\n' "beta-suite (a deliberately long label that fills the whole pad width)" "✓"
  printf '  %-55s%s\n' "gamma-suite (set EXAMPLE_API_KEY to enable)" "SKIP"
  printf '  %-55s%s\n' "delta-suite (set OTHER_API_KEY to enable)" "SKIP"
  printf '✓ 2/2 suites passed (2 skipped)\n'
} > "$ERUNALL/round-1/stdout.log"
python3 "$SCRIPTS/emit-report.py" --run-dir "$ERUNALL" >/dev/null

ERUNALL_FAIL="$TMP/emit_runall_fail"
build_pass_run "$ERUNALL_FAIL"
cat > "$ERUNALL_FAIL/round-1/meta.json" <<'MJ'
{"exit": 1, "duration_ms": 100, "error_sig": "suite failed", "cmd": "echo ok"}
MJ
{
  printf '  %-55s%s\n' "alpha-suite (basic cases and idempotency)" "✓"
  printf '  %-55s%s\n' "beta-suite (a deliberately long label that fills the whole pad width)" "✗"
  printf '  %-55s%s\n' "gamma-suite (set EXAMPLE_API_KEY to enable)" "SKIP"
  printf '✗ 1/2 suites failed (failing output saved under /tmp/example)\n'
} > "$ERUNALL_FAIL/round-1/stdout.log"
cat > "$ERUNALL_FAIL/round-1/stderr.log" <<'LOG'
PASS internal_setup
FAIL internal_assertion
RESULT_JSON {"total": 2, "failures": 1, "errors": 0, "skipped": 0}
LOG
python3 "$SCRIPTS/emit-report.py" --run-dir "$ERUNALL_FAIL" >/dev/null
python3 - <<PY
import json

passed=json.load(open("$ERUNALL/report.json"))
pinv=passed["suite"]["case_inventory"]
assert passed["suite"]["pass_count"]==2, passed["suite"]
assert passed["suite"]["fail_count"]==0, passed["suite"]
assert passed["suite"]["skip_count"]==2, passed["suite"]
assert pinv["real_case_count"]==4, pinv
assert pinv["rollup_count"]==1, pinv
assert "2/2 suites passed (2 skipped)" in pinv["module_summaries"], pinv
assert not any("suites passed" in (n or "") for n in pinv["passed_names"]), pinv

failed=json.load(open("$ERUNALL_FAIL/report.json"))
finv=failed["suite"]["case_inventory"]
assert failed["result"]=="FAIL_SUITE", failed
assert failed["suite"]["pass_count"]==1, failed["suite"]
assert failed["suite"]["fail_count"]==1, failed["suite"]
assert failed["suite"]["skip_count"]==1, failed["suite"]
assert finv["real_case_count"]==3 and finv["rollup_count"]==1, finv
assert not any("suites failed" in (n or "") for n in finv["failed_names"]), finv
assert failed["suite"]["suite_summary_source"]=="rollup_stdout", failed["suite"]
assert not any(
    (n or "").startswith("internal_")
    for n in finv["passed_names"] + finv["failed_names"]
), finv
print("suite rollup trailing status + counts ok")
PY

# PASS with TMPDIR struggle
python3 "$SCRIPTS/emit-report.py" --run-dir "$EPC" >/dev/null
python3 - <<PY
import json
r=json.load(open("$EPC/report.json"))
titles=[s["title"] for s in r["story"]["struggles"]]
assert "TMPDIR_LEAK" in titles, titles
card=open("$EPC/chat-card.md").read()
assert "TMPDIR_LEAK" in card and "Struggles" in card
print("struggles on PASS ok")
PY
assert "PASS still lists struggles" true

# FAIL_SUITE struggle blocking
python3 - <<PY
import json
r=json.load(open("$EFS/report.json"))
# re-emit after story support
print("efs result", r["result"])
PY
python3 "$SCRIPTS/emit-report.py" --run-dir "$EFS" >/dev/null
python3 - <<PY
import json
r=json.load(open("$EFS/report.json"))
assert r["result"]=="FAIL_SUITE"
sevs=[s["severity"] for s in r["story"]["struggles"]]
assert "blocking" in sevs, r["story"]["struggles"]
print("fail_suite struggles ok")
PY
assert "FAIL_SUITE has blocking struggles" true

# ---------------------------------------------------------------------------
echo "--- control_policy.py ---"
# ---------------------------------------------------------------------------
set +e
out="$(python3 "$SCRIPTS/control_policy.py" self-test)"
ec=$?
set -e
assert_eq "control_policy self-test exit 0" "$ec" "0"
assert_json_field "control_policy self-test ok" "$out" "d.get('ok')" "true"

# Traceback on green exit → fail disposition (end-to-end via classify)
CP_REPO="$TMP/cpol"
make_repo "$CP_REPO"
CP_RUN="$TMP/cpol-run"
mkdir -p "$CP_RUN/round-1"
python3 "$SCRIPTS/control_policy.py" resolve --repo "$CP_REPO" --run-dir "$CP_RUN" --profile fast >/dev/null
assert "resolved control-policy.json" test -f "$CP_RUN/control-policy.json"
# clean delta
cat > "$CP_RUN/round-1/delta.json" <<'DJ'
{"fs_scope":"full","delta":[],"ignored_delta":[]}
DJ
printf 'PASS ok\n' > "$CP_RUN/round-1/stdout.log"
printf 'Traceback (most recent call last):\n  File "x", line 1\n' > "$CP_RUN/round-1/stderr.log"
echo '{"exit":0,"duration_ms":1,"error_sig":"none"}' > "$CP_RUN/round-1/meta.json"
set +e
python3 "$SCRIPTS/classify-side-effects.py" \
  --delta "$CP_RUN/round-1/delta.json" \
  --profile fast \
  --log "$CP_RUN/round-1/stdout.log" \
  --log "$CP_RUN/round-1/stderr.log" \
  --control-policy "$CP_RUN/control-policy.json" \
  --suite-exit 0 \
  --run-dir "$CP_RUN" \
  --out "$CP_RUN/round-1/side-effects.json"
ec=$?
set -e
assert_eq "traceback on green → classifier fail exit" "$ec" "1"
python3 - <<PY
import json
d=json.load(open("$CP_RUN/round-1/side-effects.json"))
assert d["side_effects_ok"] is False
ctrl=d.get("control") or []
assert any(c.get("class")=="CONTROL_FORBID_HIT" for c in ctrl), ctrl
assert any("Traceback" in (c.get("sample") or "") or "Traceback" in (c.get("needle") or "") for c in ctrl)
print("traceback forbid ok")
PY
assert "CONTROL_FORBID_HIT on Traceback" true
assert "channels_excerpt written" test -f "$CP_RUN/channels_excerpt.md"

# control_require_on_exit 3 missing marker
python3 - <<PY
import json
from pathlib import Path
p=Path("$CP_RUN/control-policy.json")
d=json.loads(p.read_text())
d["control_require_on_exit"]={"3":["EXPECTED MARKER"]}
p.write_text(json.dumps(d, indent=2))
PY
printf '{"code":3}\n' > "$CP_RUN/round-1/stdout.log"
printf 'note: only\n' > "$CP_RUN/round-1/stderr.log"
set +e
python3 "$SCRIPTS/classify-side-effects.py" \
  --delta "$CP_RUN/round-1/delta.json" \
  --profile fast \
  --log "$CP_RUN/round-1/stdout.log" \
  --log "$CP_RUN/round-1/stderr.log" \
  --control-policy "$CP_RUN/control-policy.json" \
  --suite-exit 3 \
  --run-dir "$CP_RUN" \
  --out "$CP_RUN/round-1/side-effects-req.json"
ec=$?
set -e
assert_eq "missing required marker → fail" "$ec" "1"
python3 - <<PY
import json
d=json.load(open("$CP_RUN/round-1/side-effects-req.json"))
assert any(c.get("class")=="CONTROL_REQUIRE_MISS" for c in d.get("control") or []), d
print("require miss ok")
PY
assert "CONTROL_REQUIRE_MISS" true

# redaction: secret in stderr must not appear in chat-card
RED_RUN="$TMP/redact-run"
mkdir -p "$RED_RUN/round-1"
python3 "$SCRIPTS/init-run.py" \
  --repo "$CP_REPO" --run-dir "$RED_RUN" --cmd "true" \
  --profile fast --source explicit --mode once --suite-scope full --habitat host >/dev/null
cat > "$RED_RUN/round-1/delta.json" <<'DJ'
{"fs_scope":"full","delta":[],"ignored_delta":[]}
DJ
cat > "$RED_RUN/round-1/stdout.log" <<'LOG'
PASS
SKIP live check: ANTHROPIC_API_KEY not set
SKIP other check: OPENAI_API_KEY not set
SKIP auth check: ANTHROPIC_AUTH_TOKEN not set
ANTHROPIC_API_KEY=anthropic-secret-value-1234567890
LOG
{
  printf 'Authorization: Bearer %s\n' 'supersecret''tokenvalue12345'
  printf 'OPENAI_API_KEY: sk-%s\n' 'testsecretvalue123456789012345'
  printf '"ANTHROPIC_API_KEY": "sk-%s"\n' 'ant-api03-testvalue123456789012345'
  printf '"OPENAI_API_KEY": "sk-%s"\n' 'proj-testvalue123456789012345'
  printf '"ANTHROPIC_AUTH_TOKEN": "%s"\n' 'auth-token-value-123456789012345'
  printf 'provider diagnostic: sk-%s\n' 'proj-standalonevalue123456789012345'
  printf 'PASS\n'
} > "$RED_RUN/round-1/stderr.log"
echo '{"exit":0,"duration_ms":1,"error_sig":"none"}' > "$RED_RUN/round-1/meta.json"
python3 "$SCRIPTS/control_policy.py" resolve --repo "$CP_REPO" --run-dir "$RED_RUN" --profile fast >/dev/null
python3 "$SCRIPTS/classify-side-effects.py" \
  --delta "$RED_RUN/round-1/delta.json" --profile fast \
  --log "$RED_RUN/round-1/stdout.log" --log "$RED_RUN/round-1/stderr.log" \
  --control-policy "$RED_RUN/control-policy.json" --suite-exit 0 \
  --run-dir "$RED_RUN" --out "$RED_RUN/round-1/side-effects.json" >/dev/null || true
python3 "$SCRIPTS/emit-report.py" --run-dir "$RED_RUN" >/dev/null
python3 - <<PY
import json
from pathlib import Path
card=open("$RED_RUN/chat-card.md").read()
raw=(
    open("$RED_RUN/round-1/stdout.log").read()
    + open("$RED_RUN/round-1/stderr.log").read()
)
openai_secret = "sk-" + "testsecretvalue123456789012345"
anthropic_json_secret = "sk-" + "ant-api03-testvalue123456789012345"
openai_json_secret = "sk-" + "proj-testvalue123456789012345"
auth_token_secret = "auth-token-value-123456789012345"
standalone_project_secret = "sk-" + "proj-standalonevalue123456789012345"
assert "supersecrettokenvalue12345" in raw
assert "anthropic-secret-value-1234567890" in raw
assert openai_secret in raw
for secret in (
    "supersecrettokenvalue12345",
    "anthropic-secret-value-1234567890",
    openai_secret,
    anthropic_json_secret,
    openai_json_secret,
    auth_token_secret,
    standalone_project_secret,
):
    assert secret in raw, secret
    assert secret not in card, card
assert "REDACTED" in card or "Bearer" in card
se=json.load(open("$RED_RUN/round-1/side-effects.json"))
ctrl=se.get("control") or []
assert se["side_effects_ok"] is False, se
assert sum(c.get("class")=="CONTROL_FORBID_HIT" for c in ctrl)>=3, ctrl
assert not any(
    c.get("needle") in {"ANTHROPIC_API_KEY", "OPENAI_API_KEY"}
    for c in ctrl
), ctrl
if Path("$RED_RUN/channels_excerpt.md").is_file():
    ex=open("$RED_RUN/channels_excerpt.md").read()
    for secret in (
        "supersecrettokenvalue12345",
        "anthropic-secret-value-1234567890",
        openai_secret,
        anthropic_json_secret,
        openai_json_secret,
        auth_token_secret,
        standalone_project_secret,
    ):
        assert secret not in ex
print("redaction ok")
PY
assert "credential absent from chat-card" true

# unknown policy key fails closed
BAD="$TMP/bad-policy.yml"
echo "totally_unknown_key: true" > "$BAD"
set +e
python3 "$SCRIPTS/control_policy.py" resolve --repo "$CP_REPO" --run-dir "$TMP/badpol" --profile fast --policy-file "$BAD" >/dev/null 2>"$TMP/badpol.err"
ec=$?
set -e
assert_eq "unknown policy key exit 2" "$ec" "2"

# tests/run.py: fast, full scope, host habitat, whatever else the tree holds
RS="$TMP/rs-skill"
make_repo "$RS"
mkdir -p "$RS/tests" "$RS/scripts"
echo "# run" > "$RS/tests/run.py"
# a helper script and a stray test file: neither may change what discovery returns
echo "# helper" > "$RS/scripts/helper_runtime.py"
echo "# partial" > "$RS/tests/test_partial.py"
out="$(bash "$SCRIPTS/discover-test-cmd.sh" --repo "$RS")"
assert_json_field "run.py discover suite_scope full" "$out" "d.get('suite_scope')" "full"
assert_json_field "run.py discover habitat host" "$out" "d.get('habitat')" "host"
assert_json_field "run.py discover profile fast" "$out" "d['profile']" "fast"
assert_json_field "run.py discover cmd is the plain runner" "$out" "d['cmd']" "python3 tests/run.py"

out_full="$(bash "$SCRIPTS/discover-test-cmd.sh" --repo "$RS" --full)"
assert_json_field "run.py --full suite_scope full" "$out_full" "d.get('suite_scope')" "full"
assert_json_field "run.py --full cmd" "$out_full" "d['cmd']" "python3 tests/run.py"

# ---------------------------------------------------------------------------
echo "--- package scope (porcelain path-prefix) ---"
# ---------------------------------------------------------------------------
# Nested monorepo: dirt at git root must NOT appear under package path-prefix;
# dirt under package must appear and classify as material.
MONO="$TMP/mono"
make_repo "$MONO"
mkdir -p "$MONO/skills/pkg/tests" "$MONO/skills/pkg/src"
echo "pkg" > "$MONO/skills/pkg/README.md"
echo "exports.y=1" > "$MONO/skills/pkg/src/app.js"
echo "pass" > "$MONO/skills/pkg/tests/run.py"
git -C "$MONO" add skills
git -C "$MONO" commit -qm "add package"

# Root dirt (neighbor / monorepo WIP)
echo "root-wip" > "$MONO/ROOT_DIRT.txt"
# Package stays clean for first pin
POUT_PKG="$TMP/porc-pkg"
mkdir -p "$POUT_PKG"
python3 "$SCRIPTS/porcelain-delta.py" \
  --repo "$MONO" --run-dir "$POUT_PKG" --round 1 --mode snapshot --side pre \
  --path-prefix "skills/pkg" >/dev/null
python3 - <<PY
import json
m=json.load(open("$POUT_PKG/round-1/pre/manifest.json"))
assert m.get("fs_scope")=="package", m.get("fs_scope")
assert m.get("audit_prefix")=="skills/pkg", m.get("audit_prefix")
paths=set(m.get("dirty_paths") or [])
assert "ROOT_DIRT.txt" not in paths, paths
# no package dirt either
assert not any(p.startswith("skills/pkg") and "ROOT" in p for p in paths)
print("package prefix ignores root dirt at pre")
PY
assert "package pre ignores monorepo root dirt" true

# suite dirt under package only
echo "suite-mut" > "$MONO/skills/pkg/src/app.js"
echo "new-in-pkg" > "$MONO/skills/pkg/src/newfile.js"
python3 "$SCRIPTS/porcelain-delta.py" \
  --repo "$MONO" --run-dir "$POUT_PKG" --round 1 --mode snapshot --side post \
  --path-prefix "skills/pkg" >/dev/null
python3 "$SCRIPTS/porcelain-delta.py" \
  --repo "$MONO" --run-dir "$POUT_PKG" --round 1 --mode diff \
  --path-prefix "skills/pkg" >/dev/null
python3 - <<PY
import json
d=json.load(open("$POUT_PKG/round-1/delta.json"))
assert d.get("fs_scope")=="package", d
assert d.get("audit_prefix")=="skills/pkg"
by={x["path"]:x for x in d["delta"]}
assert "ROOT_DIRT.txt" not in by, by
assert "skills/pkg/src/app.js" in by, by
assert by["skills/pkg/src/app.js"]["change"]=="content_changed"
assert "skills/pkg/src/newfile.js" in by
assert by["skills/pkg/src/newfile.js"]["change"]=="added"
print("package material delta ok")
PY
assert "package dirty under prefix is material" true

# restore via git_root (not wrong package-relative join)
python3 "$SCRIPTS/porcelain-delta.py" \
  --repo "$MONO" --run-dir "$POUT_PKG" --round 1 --mode restore \
  --path-prefix "skills/pkg" --restore-policy revert-disposable >/dev/null
assert_eq "package restore app.js" "$(cat "$MONO/skills/pkg/src/app.js")" "exports.y=1"
assert "package restore deleted newfile" test ! -e "$MONO/skills/pkg/src/newfile.js"
# root dirt still present (out of scope)
assert "root dirt untouched by package restore" test -f "$MONO/ROOT_DIRT.txt"

# WORK_ROOT == GIT_ROOT still works (regression — no path-prefix)
POUT_FULL="$TMP/porc-full"
mkdir -p "$POUT_FULL"
git -C "$MONO" checkout -- . 2>/dev/null || true
git -C "$MONO" clean -fdq
# leave tree clean for full-scope snapshot
python3 "$SCRIPTS/porcelain-delta.py" \
  --repo "$MONO" --run-dir "$POUT_FULL" --round 1 --mode snapshot --side pre >/dev/null
python3 - <<PY
import json
m=json.load(open("$POUT_FULL/round-1/pre/manifest.json"))
assert m.get("fs_scope")=="full", m.get("fs_scope")
assert (m.get("audit_prefix") or "")==""
assert m.get("git_root")
print("full scope ok")
PY
assert "WORK_ROOT==GIT_ROOT full fs_scope" true

# init-run carries work_root / git_root / audit_prefix
IR_PKG="$TMP/init-pkg"
python3 "$SCRIPTS/init-run.py" \
  --repo "$MONO/skills/pkg" --run-dir "$IR_PKG" --cmd "python3 tests/run.py" \
  --profile fast --source path --mode once \
  --work-root "$MONO/skills/pkg" --git-root "$MONO" --audit-prefix "skills/pkg" >/dev/null
python3 - <<PY
import json
m=json.load(open("$IR_PKG/manifest.json"))
assert m["repo"].endswith("skills/pkg") or m["repo"].endswith("pkg"), m["repo"]
assert m.get("audit_prefix")=="skills/pkg"
assert m.get("git_root")
assert m.get("work_root")
print("init package fields ok")
PY
assert "init-run package fields" true

# end-to-end: clean package suite under dirty monorepo root → PASS_CLEAN_SCOPED
# Restore package; keep root dirt
echo "still-root-dirty" > "$MONO/ROOT_DIRT.txt"
# trivial green suite that writes nothing under package
mkdir -p "$MONO/skills/pkg/tests"
printf 'import sys; print("ok"); sys.exit(0)\n' > "$MONO/skills/pkg/tests/run.py"
# run-harness against package path
set +e
RH_OUT="$TMP/rh-pkg.out"
bash "$SCRIPTS/run-harness.sh" --repo "$MONO/skills/pkg" --cmd "python3 tests/run.py" \
  --timeout-secs 30 >"$RH_OUT" 2>&1
ec=$?
set -e
python3 - <<PY
import re, pathlib
text=pathlib.Path("$RH_OUT").read_text()
m=re.search(r"test-harness RESULT=(\S+)", text)
assert m, text[-2000:]
assert m.group(1) in ("PASS_CLEAN_SCOPED", "PASS_CLEAN"), m.group(1)
# package scope should yield SCOPED when nested
assert m.group(1)=="PASS_CLEAN_SCOPED", (m.group(1), text[-1500:])
print("nested package RESULT", m.group(1))
PY
assert_eq "nested package green under root dirt exit 0" "$ec" "0"
assert "nested PASS_CLEAN_SCOPED" true

# Dirty under package during suite → FAIL_SIDE_EFFECTS path (material write)
printf 'from pathlib import Path\nPath("src/leaked.txt").write_text("x")\nprint("ok")\n' \
  > "$MONO/skills/pkg/tests/run.py"
set +e
RH_OUT2="$TMP/rh-pkg-dirty.out"
bash "$SCRIPTS/run-harness.sh" --repo "$MONO/skills/pkg" --cmd "python3 tests/run.py" \
  --timeout-secs 30 >"$RH_OUT2" 2>&1
ec=$?
set -e
python3 - <<PY
import re, pathlib
text=pathlib.Path("$RH_OUT2").read_text()
m=re.search(r"test-harness RESULT=(\S+)", text)
assert m, text[-2000:]
assert m.group(1)=="FAIL_SIDE_EFFECTS", (m.group(1), text[-1500:])
print("package side-effect RESULT", m.group(1))
PY
assert_eq "package material write → non-zero exit" "$ec" "1"
assert "package FAIL_SIDE_EFFECTS" true
# cleanup leaked file for tmp hygiene
rm -f "$MONO/skills/pkg/src/leaked.txt"

# ---------------------------------------------------------------------------
echo "--- discover hermetic runners (profile=fast) ---"
# ---------------------------------------------------------------------------
# only tests/run.py → fast
DRPY="$TMP/disc-runpy"
make_repo "$DRPY"
mkdir -p "$DRPY/tests"
echo "# hermetic" > "$DRPY/tests/run.py"
out="$(bash "$SCRIPTS/discover-test-cmd.sh" --repo "$DRPY")"
assert_json_field "discover tests/run.py profile fast" "$out" "d['profile']" "fast"
assert_json_field "discover tests/run.py cmd" "$out" "d['cmd']" "python3 tests/run.py"

# an offline run_*.test.sh wrapper is preferred over run.sh
DINV="$TMP/disc-inv"
make_repo "$DINV"
mkdir -p "$DINV/tests"
echo "# run" > "$DINV/tests/run.sh"
echo "# offline" > "$DINV/tests/run_unit.test.sh"
out="$(bash "$SCRIPTS/discover-test-cmd.sh" --repo "$DINV")"
assert_json_field "discover offline wrapper profile fast" "$out" "d['profile']" "fast"
assert_json_field "discover offline wrapper preferred over run.sh" "$out" "d['cmd']" "bash tests/run_unit.test.sh"

# other run_*.test.sh
DWRAP="$TMP/disc-wrap"
make_repo "$DWRAP"
mkdir -p "$DWRAP/tests"
echo "# offline" > "$DWRAP/tests/run_foo.test.sh"
out="$(bash "$SCRIPTS/discover-test-cmd.sh" --repo "$DWRAP")"
assert_json_field "discover run_*.test.sh profile fast" "$out" "d['profile']" "fast"
assert_json_field "discover run_*.test.sh cmd" "$out" "d['cmd']" "bash tests/run_foo.test.sh"

# docs exist
assert "local-change-gate.md exists" test -f "$(dirname "$SCRIPTS")/references/local-change-gate.md"

# ---------------------------------------------------------------------------
echo "--- resolve-scope.py SSOT ---"
# ---------------------------------------------------------------------------
RS_MONO="$TMP/rs-mono"
make_repo "$RS_MONO"
mkdir -p "$RS_MONO/skills/pkg"
echo "x" > "$RS_MONO/skills/pkg/f.txt"
git -C "$RS_MONO" add skills && git -C "$RS_MONO" commit -qm "pkg"
out="$(python3 "$SCRIPTS/resolve-scope.py" --repo "$RS_MONO/skills/pkg")"
printf '%s' "$out" > "$TMP/rs-nested.json"
assert_json_field "resolve nested nested=true" "$out" "d['nested']" "true"
assert_json_field "resolve nested audit_prefix" "$out" "d['audit_prefix']" "skills/pkg"
assert_json_field "resolve nested suite_rel" "$out" "d['suite_rel']" "skills/pkg"
assert_json_field "resolve nested porc==git" "$out" "d['porc_repo']==d['git_root']" "true"
assert "resolve nested work_root" python3 -c "import json; d=json.load(open('$TMP/rs-nested.json')); assert d['work_root'].endswith('skills/pkg')"

out_root="$(python3 "$SCRIPTS/resolve-scope.py" --repo "$RS_MONO")"
assert_json_field "resolve root nested=false" "$out_root" "d['nested']" "false"
assert_json_field "resolve root empty prefix" "$out_root" "d['audit_prefix']" ""
assert_json_field "resolve root git==work" "$out_root" "d['git_root']==d['work_root']" "true"

# ---------------------------------------------------------------------------
echo "--- worktree-fixloop package-aware ---"
# ---------------------------------------------------------------------------
WT_MONO="$TMP/wt-mono"
make_repo "$WT_MONO"
mkdir -p "$WT_MONO/skills/pkg/src"
echo "clean" > "$WT_MONO/skills/pkg/src/a.txt"
git -C "$WT_MONO" add skills && git -C "$WT_MONO" commit -qm "pkg"
echo "pkg-wip" > "$WT_MONO/skills/pkg/src/a.txt"
echo "root-wip" > "$WT_MONO/ROOT_ONLY.txt"
WT_RUN="$TMP/wt-run"
mkdir -p "$WT_RUN"
enter_json="$(bash "$SCRIPTS/worktree-fixloop.sh" enter --repo "$WT_MONO/skills/pkg" --run-dir "$WT_RUN")"
printf '%s' "$enter_json" > "$TMP/wt-enter.json"
assert_json_field "worktree audit_prefix" "$enter_json" "d['audit_prefix']" "skills/pkg"
assert "worktree suite overlay + no root leak" python3 -c "
import json, pathlib
d=json.load(open('$TMP/wt-enter.json'))
assert d.get('mode') in ('created','reuse'), d
sc=pathlib.Path(d['suite_cwd'])
assert sc.is_dir(), sc
assert (sc/'src'/'a.txt').read_text().strip()=='pkg-wip'
wt=pathlib.Path(d['workspace'])
assert not (wt/'ROOT_ONLY.txt').exists(), 'root dirt leaked into worktree overlay'
assert pathlib.Path('$WT_RUN/scope.json').is_file()
"
bash "$SCRIPTS/worktree-fixloop.sh" exit --repo "$WT_MONO/skills/pkg" --run-dir "$WT_RUN" >/dev/null
assert "worktree package exit" true

set +e
RH_S="$TMP/rh-scope.out"
bash "$SCRIPTS/run-harness.sh" --repo "$WT_MONO/skills/pkg" --cmd "true" --timeout-secs 15 >"$RH_S" 2>&1
set -e
assert "run-harness persists scope.json" python3 -c "
import re, pathlib, json
text=pathlib.Path('$RH_S').read_text()
m=re.search(r'RUN_DIR=(\S+)', text)
assert m, text[-1500:]
scope=json.loads((pathlib.Path(m.group(1))/'scope.json').read_text())
assert scope.get('audit_prefix')=='skills/pkg', scope
assert scope.get('nested') is True
"
# ---------------------------------------------------------------------------
echo "--- supervisor (unintended + attempt + conclusion) ---"
# ---------------------------------------------------------------------------
SUPR="$TMP/sup-run"
mkdir -p "$SUPR/round-1"
python3 - <<PY
import json
from pathlib import Path
rd=Path("$SUPR")
rd.mkdir(parents=True, exist_ok=True)
(rd/"manifest.json").write_text(json.dumps({
  "schema_version":1,"repo":"$TMP","repo_slug":"suptmp","cmd":"echo suite",
  "profile":"fast","source":"explicit","mode":"once","rounds_max":1,
  "assume_fast":False,"flags":["once"],"run_dir":str(rd),
  "work_root":"$TMP","git_root":"$TMP","audit_prefix":"",
  "suite_scope":"full","habitat":"host","started_at":"2026-01-01T00:00:00Z",
})+"\n")
(rd/"round-1").mkdir(exist_ok=True)
(rd/"round-1/stdout.log").write_text("suite: demo — 2 tests\nPASS test_a\nPASS test_b\n")
(rd/"round-1/stderr.log").write_text("WARNING: leftover\n")
(rd/"round-1/meta.json").write_text(json.dumps({"exit":0,"duration_ms":12,"error_sig":"none"})+"\n")
(rd/"round-1/delta.json").write_text(json.dumps({"fs_scope":"full","delta":[],"ignored_delta":[]})+"\n")
(rd/"round-1/side-effects.json").write_text(json.dumps({
  "profile":"fast","fs_scope":"full","delta":[],"services":[],"control":[],
  "summary":{"fail":0,"note":0,"ok":0,"total":0},"side_effects_ok":True,
})+"\n")
PY
python3 "$SCRIPTS/emit-report.py" --run-dir "$SUPR" >/dev/null
assert "supervisor surfaces in report/card/html" python3 -c "
import json
r=json.load(open('$SUPR/report.json'))
s=r.get('supervisor') or {}
assert s.get('what_was_attempted'), s
assert s.get('conclusion',{}).get('summary'), s
card=open('$SUPR/chat-card.md').read()
assert 'Conclusion (supervisor)' in card, card[:800]
assert 'What was attempted' in card, card[:1200]
assert 'Unintended consequences' in card
assert 'Conclusion (supervisor)' in open('$SUPR/results.md').read()
assert 'Supervisor conclusion' in open('$SUPR/report.html').read()
print('ok')
"
printf 'PASS ok\n' > "$SUPR/round-1/stdout.log"
printf 'Traceback (most recent call last):\n  File \"x\"\n' > "$SUPR/round-1/stderr.log"
python3 "$SCRIPTS/emit-report.py" --run-dir "$SUPR" >/dev/null
assert "supervisor flags traceback" python3 -c "
import json
r=json.load(open('$SUPR/report.json'))
titles=[s['title'] for s in (r.get('supervisor') or {}).get('unintended_signals') or []]
assert 'traceback' in titles, titles
print('ok')
"

# Timeout-oriented tests commonly include the noun "timeout" in a passing case
# name. Those explicit result lines are evidence that the timeout behavior was
# exercised successfully, not evidence that the suite itself hung. Real timeout
# prose outside an explicit PASS result must remain suspicious.
cat > "$SUPR/round-1/stdout.log" <<'LOG'
  timeout-supervisor (wall cap and process-group cleanup)✓
PASS slow-dependency (an upstream timeout is cut off without hanging)
LOG
: > "$SUPR/round-1/stderr.log"
python3 "$SCRIPTS/emit-report.py" --run-dir "$SUPR" >/dev/null
assert "supervisor ignores timeout words in explicit pass results" python3 -c "
import json
r=json.load(open('$SUPR/report.json'))
signals=(r.get('supervisor') or {}).get('unintended_signals') or []
assert not any(s.get('title') == 'timeout_signal' for s in signals), signals
print('ok')
"
cat >> "$SUPR/round-1/stdout.log" <<'LOG'
worker timed out after 30 seconds while waiting for a dependency
LOG
python3 "$SCRIPTS/emit-report.py" --run-dir "$SUPR" >/dev/null
assert "supervisor retains real timeout prose beside passed timeout tests" python3 -c "
import json
r=json.load(open('$SUPR/report.json'))
signals=(r.get('supervisor') or {}).get('unintended_signals') or []
timeouts=[s for s in signals if s.get('title') == 'timeout_signal']
assert len(timeouts) == 1, signals
assert 'worker timed out after 30 seconds' in (timeouts[0].get('evidence') or ''), timeouts
print('ok')
"
assert "supervise.py exists" test -f "$SCRIPTS/supervise.py"

# ---------------------------------------------------------------------------
echo "--- run-harness.sh help ---"
# ---------------------------------------------------------------------------
help_out="$(bash "$SCRIPTS/run-harness.sh" --help 2>&1)"
assert "run-harness --help" true
echo "$help_out" | grep -q 'fix-loop' && assert "run-harness --help mentions fix-loop" true \
  || assert "run-harness --help mentions fix-loop" false
echo "$help_out" | grep -q 'hard maximum 3600' \
  && assert "run-harness --help mentions one-hour cap" true \
  || assert "run-harness --help mentions one-hour cap" false

# The public entrypoint must arm its own hard supervisor before validating the
# caller-provided repository path. A DEBUG trap blocks exactly that validation;
# the independent test watchdog only prevents a pre-fix hang from stalling this
# self-test and is not accepted as the expected timeout owner.
PUBLIC_SETUP_BASH_ENV="$TMP/public-setup-bash-env"
PUBLIC_SETUP_MARKER="$TMP/public-setup-worker-started"
cat >"$PUBLIC_SETUP_BASH_ENV" <<'BASH'
block_public_repo_validation() {
  local observed_command="$1"
  local needle='! -d '
  if [[ "$observed_command" == *"$needle"* ]]; then
    trap - DEBUG
    python3 -c 'import time; time.sleep(60)'
  fi
}
if [[ "${TEST_HARNESS_TEST_BLOCK_REPO_VALIDATION:-0}" == "1" \
      && "${TEST_HARNESS_HARD_SUPERVISED:-0}" == "1" ]]; then
  trap 'block_public_repo_validation "$BASH_COMMAND"' DEBUG
fi
BASH
public_setup_json="$(python3 - "$SCRIPTS/run-harness.sh" "$RREPO" \
  "$PUBLIC_SETUP_BASH_ENV" "$PUBLIC_SETUP_MARKER" "$TMP/public-setup-runs" <<'PY'
import json
import os
import signal
import subprocess
import sys
import time

runner, repo, bash_env, marker, run_root = sys.argv[1:]
env = os.environ.copy()
env.update({
    "BASH_ENV": bash_env,
    "TEST_HARNESS_TEST_BLOCK_REPO_VALIDATION": "1",
    "TEST_HARNESS_RUN_ROOT": run_root,
})
started = time.monotonic()
proc = subprocess.Popen(
    [
        "bash", runner, "--repo", repo,
        "--cmd", f"touch {marker}", "--timeout-secs", "1",
    ],
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    start_new_session=True,
)
watchdog_fired = False
try:
    proc.communicate(timeout=2.5)
except subprocess.TimeoutExpired:
    watchdog_fired = True
    os.killpg(proc.pid, signal.SIGKILL)
    proc.communicate()
print(json.dumps({
    "status": proc.returncode,
    "elapsed_ms": int((time.monotonic() - started) * 1000),
    "watchdog_fired": watchdog_fired,
}))
PY
)"
assert_json_field "public entrypoint owns blocked repo-validation timeout" \
  "$public_setup_json" \
  "d['status'] == 124 and not d['watchdog_fired']" "true"
assert_json_field "public blocked repo validation stays near the advertised cap" \
  "$public_setup_json" "d['elapsed_ms'] < $((1000 + TIMING_SLACK_MS))" "true"
assert "public blocked repo validation never launches suite command" \
  test ! -e "$PUBLIC_SETUP_MARKER"

set +e
TEST_HARNESS_TIMEOUT="" TEST_HARNESS_FULL_TIMEOUT="" \
  TEST_HARNESS_RUN_ROOT="$TMP/timeout-cap-runs" \
  bash "$SCRIPTS/run-harness.sh" --repo "$RREPO" --cmd "true" \
    --timeout-secs 3601 >"$TMP/run-harness-cli-cap.out" 2>&1
ec=$?
set -e
assert_eq "run-harness rejects --timeout-secs above cap" "$ec" "2"
assert "run-harness reports CLI one-hour cap" grep -q \
  "suite timeout must not exceed 3600 seconds (got '3601')" \
  "$TMP/run-harness-cli-cap.out"

set +e
TEST_HARNESS_TIMEOUT=3601 TEST_HARNESS_FULL_TIMEOUT="" \
  TEST_HARNESS_RUN_ROOT="$TMP/timeout-cap-runs" \
  bash "$SCRIPTS/run-harness.sh" --repo "$RREPO" --cmd "true" \
    >"$TMP/run-harness-env-cap.out" 2>&1
ec=$?
set -e
assert_eq "run-harness rejects TEST_HARNESS_TIMEOUT above cap" "$ec" "2"
assert "run-harness reports general env one-hour cap" grep -q \
  "suite timeout must not exceed 3600 seconds (got '3601')" \
  "$TMP/run-harness-env-cap.out"

set +e
TEST_HARNESS_TIMEOUT="" TEST_HARNESS_FULL_TIMEOUT=3601 \
  TEST_HARNESS_RUN_ROOT="$TMP/timeout-cap-runs" \
  bash "$SCRIPTS/run-harness.sh" --repo "$RREPO" --cmd "true" --full \
    >"$TMP/run-harness-full-env-cap.out" 2>&1
ec=$?
set -e
assert_eq "run-harness rejects TEST_HARNESS_FULL_TIMEOUT above cap" "$ec" "2"
assert "run-harness reports full env one-hour cap" grep -q \
  "suite timeout must not exceed 3600 seconds (got '3601')" \
  "$TMP/run-harness-full-env-cap.out"

set +e
TEST_HARNESS_TIMEOUT="" TEST_HARNESS_FULL_TIMEOUT="" \
  TEST_HARNESS_RUN_ROOT="$TMP/timeout-cap-runs" \
  bash "$SCRIPTS/run-harness.sh" --repo "$RREPO" --cmd "true" \
    >"$TMP/run-harness-fast-default.out" 2>&1
ec=$?
set -e
assert_eq "run-harness fast default smoke exit 0" "$ec" "0"
assert "run-harness fast default remains 1200 seconds" grep -q \
  'deadline · total=1200s' "$TMP/run-harness-fast-default.out"
assert "run-harness keeps its complete captured run tree private" python3 -c "
import re
import stat
from pathlib import Path
text=Path('$TMP/run-harness-fast-default.out').read_text()
match=re.search(r'^RUN_DIR=(\\S+)$', text, re.M)
assert match, text[-2000:]
root=Path(match.group(1))
for directory in (root, root/'round-1', root/'round-1/tmp'):
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700, directory
for file in (root/'manifest.json', root/'round-1/stdout.log', root/'round-1/stderr.log'):
    assert stat.S_IMODE(file.stat().st_mode) == 0o600, file
"

# Ambient variables from an ordinary parent shell must not forge the recursion
# guard. The real supervisor replaces the claimed parent PID and capability.
forged_deadline_ms="$(( $(python3 -c 'import time; print(int(time.time() * 1000))') + 600000 ))"
set +e
FORGED_PARENT_PID="$$" \
TEST_HARNESS_HARD_SUPERVISED=1 \
TEST_HARNESS_HARD_SUPERVISOR_PID="$$" \
TEST_HARNESS_HARD_DEADLINE_EPOCH_MS="$forged_deadline_ms" \
TEST_HARNESS_SUITE_DEADLINE_EPOCH_MS="$forged_deadline_ms" \
TEST_HARNESS_HARD_CAPABILITY_FD=9 \
TEST_HARNESS_HARD_CAPABILITY_NONCE=0000000000000000000000000000000000000000000000000000000000000000 \
  bash "$SCRIPTS/run-harness.sh" --repo "$RREPO" \
    --cmd '[[ "$TEST_HARNESS_HARD_SUPERVISOR_PID" != "$FORGED_PARENT_PID" ]]' \
    --timeout-secs 15 >"$TMP/run-harness-forged-parent.out" 2>&1
ec=$?
set -e
assert_eq "forged parent marker is re-supervised" "$ec" "0"
assert "forged parent run reaches a clean report" grep -q \
  'RESULT=PASS_CLEAN' "$TMP/run-harness-forged-parent.out"

# Authentic capabilities may use any normal POSIX descriptor, not only 3..9.
# Hold descriptors open across launch so the supervisor's pipe is forced high.
HIGH_FD_CAPTURE="$TMP/high-capability-fd.txt"
HIGH_FD_OUT="$TMP/run-harness-high-fd.out"
set +e
python3 - "$SCRIPTS/run-harness-hard-supervisor.py" \
  "$SCRIPTS/run-harness.sh" "$RREPO" "$HIGH_FD_CAPTURE" "$HIGH_FD_OUT" \
  "$TMP/high-fd-run" <<'PY'
import os
import shlex
import subprocess
import sys

supervisor, runner, repo, capture, output, run_dir = sys.argv[1:]
holders = []
for _ in range(520):
    read_fd, write_fd = os.pipe()
    os.set_inheritable(read_fd, True)
    os.set_inheritable(write_fd, True)
    holders.extend((read_fd, write_fd))
# A caller may itself supervise this self-test and occupy a low descriptor that
# is not one of our holders. subprocess would otherwise close that descriptor
# before exec, leaving (for example) FD 3 free and defeating the intended
# high-FD setup. Preserve every already-open descriptor in the covered range so
# the nested supervisor really must allocate its capability above 1023.
pass_through = set(holders)
for fd in range(3, max(holders) + 1):
    try:
        os.fstat(fd)
    except OSError:
        continue
    pass_through.add(fd)
command = (
    "printf '%s\\n' \"$TEST_HARNESS_HARD_CAPABILITY_FD\" > "
    + shlex.quote(capture)
)
with open(output, "wb") as stream:
    result = subprocess.run(
        [
            sys.executable, supervisor,
            "--timeout-secs", "15", "--repo", repo, "--run-dir", run_dir,
            "--", "bash", runner, "--repo", repo, "--cmd", command,
            "--timeout-secs", "15",
        ],
        stdout=stream,
        stderr=subprocess.STDOUT,
        pass_fds=tuple(sorted(pass_through)),
        check=False,
    )
for fd in holders:
    os.close(fd)
raise SystemExit(result.returncode)
PY
ec=$?
set -e
assert_eq "authentic high-FD capability is accepted" "$ec" "0"
high_capability_fd="$(cat "$HIGH_FD_CAPTURE" 2>/dev/null || echo 0)"
assert "supervisor regression actually uses FD 1024 or higher" \
  test "$high_capability_fd" -ge 1024

assert "operator-guide exists" test -f "$(dirname "$SCRIPTS")/references/operator-guide.md"
assert "resolve-scope.py exists" test -f "$SCRIPTS/resolve-scope.py"
assert "gate-snippet.md exists" test -f "$(dirname "$SCRIPTS")/references/gate-snippet.md"
assert "self-test-matrix.md exists" test -f "$(dirname "$SCRIPTS")/references/self-test-matrix.md"

# ---------------------------------------------------------------------------
echo "--- discover config tier (.test-harness.yml) ---"
# ---------------------------------------------------------------------------
DCFG="$TMP/disc-cfg"
make_repo "$DCFG"
# Makefile would otherwise win — config must beat it
cat > "$DCFG/Makefile" <<'MF'
test-fast:
	@echo from-make
MF
cat > "$DCFG/.test-harness.yml" <<'YML'
cmd: echo from-config
profile: fast
suite_scope: full
habitat: host
YML
out="$(bash "$SCRIPTS/discover-test-cmd.sh" --repo "$DCFG")"
assert_json_field "discover config source" "$out" "d['source']" "config"
assert_json_field "discover config profile" "$out" "d['profile']" "fast"
assert_json_field "discover config cmd" "$out" "d['cmd']" "echo from-config"
assert_json_field "discover config suite_scope" "$out" "d.get('suite_scope')" "full"
assert_json_field "discover config habitat" "$out" "d.get('habitat')" "host"

# empty cmd does not pin — falls through to makefile
cat > "$DCFG/.test-harness.yml" <<'YML'
# no cmd
profile: full
YML
out="$(bash "$SCRIPTS/discover-test-cmd.sh" --repo "$DCFG")"
assert_json_field "empty config cmd falls to makefile" "$out" "d['source']" "makefile"
assert_json_field "empty config cmd make test-fast" "$out" "d['cmd']" "make test-fast"

# ---------------------------------------------------------------------------
echo "--- control_policy discover keys allowed ---"
# ---------------------------------------------------------------------------
POL_CFG="$TMP/pol-cfg.yml"
cat > "$POL_CFG" <<'YML'
cmd: python3 tests/run.py
profile: fast
suite_scope: full
habitat: host
known_test_artifacts:
  - "*.pyc"
ignored_write_note_globs:
  - "**/runs/**"
YML
POL_RUN="$TMP/pol-cfg-run"
mkdir -p "$POL_RUN"
set +e
out="$(python3 "$SCRIPTS/control_policy.py" resolve \
  --repo "$DCFG" --run-dir "$POL_RUN" --profile fast --policy-file "$POL_CFG" 2>"$TMP/pol-cfg.err")"
ec=$?
set -e
assert_eq "policy with cmd+profile keys exit 0" "$ec" "0"
assert "policy resolve wrote control-policy.json" test -f "$POL_RUN/control-policy.json"

# ---------------------------------------------------------------------------
echo "--- run-harness --mode fix-loop smoke (clean) ---"
# ---------------------------------------------------------------------------
FL_REPO="$TMP/fixloop-clean"
make_repo "$FL_REPO"
# clean green suite
set +e
FL_OUT="$TMP/fl-clean.out"
# Runs are isolated under TMP (see the top of this file), so the worktree lifecycle can be asserted
bash "$SCRIPTS/run-harness.sh" --repo "$FL_REPO" --cmd "true" \
  --mode fix-loop --max-rounds 1 --timeout-secs 30 >"$FL_OUT" 2>&1
ec=$?
set -e
python3 - <<PY
import re, pathlib, json, os
text=pathlib.Path("$FL_OUT").read_text()
m=re.search(r"test-harness RESULT=(\S+)", text)
assert m, text[-2000:]
assert m.group(1) in ("PASS_CLEAN", "PASS_CLEAN_SCOPED"), m.group(1)
rd=re.search(r"RUN_DIR=(\S+)", text)
assert rd, text[-1500:]
run=pathlib.Path(rd.group(1))
assert (run/"scope.json").is_file()
assert (run/"manifest.json").is_file()
man=json.loads((run/"manifest.json").read_text())
assert man.get("mode")=="fix-loop", man
assert man.get("rounds_max")==1, man
# clean worktree should be removed
assert not (run/"worktree").exists(), "worktree should be removed when clean"
print("fix-loop clean RESULT", m.group(1), "run", run)
PY
assert_eq "fix-loop clean exit 0" "$ec" "0"
assert "fix-loop clean PASS_* + worktree removed" true

# A dirty-at-pre path is ambiguous after suite mutation: never rewrite it from
# the pre snapshot and never start a later round that would ratchet post bytes
# into a new baseline.
FL_PRESERVE="$TMP/fixloop-preserve"
make_repo "$FL_PRESERVE"
echo "operator-wip" > "$FL_PRESERVE/src/app.js"
set +e
FL_PRESERVE_OUT="$TMP/fl-preserve.out"
bash "$SCRIPTS/run-harness.sh" --repo "$FL_PRESERVE" \
  --cmd "printf 'suite-post\\n' > src/app.js; false" \
  --mode fix-loop --max-rounds 3 --timeout-secs 30 >"$FL_PRESERVE_OUT" 2>&1
ec=$?
set -e
assert_eq "fix-loop dirty-pre preservation exits fail" "$ec" "1"
python3 - <<PY
import json, pathlib, re
text=pathlib.Path("$FL_PRESERVE_OUT").read_text()
rd=re.search(r"RUN_DIR=(\\S+)", text)
assert rd, text[-2000:]
run=pathlib.Path(rd.group(1))
rounds=sorted(run.glob("round-*/meta.json"))
assert len(rounds)==1, rounds
restore=json.loads((run/"round-1/restore.json").read_text())
assert restore["preserved_dirty_pre_count"]==1, restore
a=restore["preserved_dirty_pre"][0]
assert a["path"]=="src/app.js", a
assert a["action"]=="preserve-dirty-pre-post-state", a
assert (run/"worktree/src/app.js").read_text()=="suite-post\\n"
report=json.loads((run/"report.json").read_text())
finding=next(x for x in report["side_effects"]["fail"] if x.get("path")=="src/app.js")
assert finding["restore_policy"]=="preserve-post-state", finding
assert "manual reconciliation required" in finding["resolution"], finding
assert "manual reconciliation required" in text, text[-2000:]
print("fix-loop stopped after preservation", run)
PY
assert "fix-loop dirty-pre preservation stops without baseline ratchet" true

# --fix-loop alias
set +e
bash "$SCRIPTS/run-harness.sh" --repo "$FL_REPO" --cmd "true" \
  --fix-loop --max-rounds 1 --timeout-secs 15 >"$TMP/fl-alias.out" 2>&1
ec=$?
set -e
assert_eq "fix-loop alias exit 0" "$ec" "0"
grep -q 'RESULT=PASS_CLEAN' "$TMP/fl-alias.out" && assert "fix-loop alias PASS" true \
  || assert "fix-loop alias PASS" false

set +e
bash "$SCRIPTS/run-harness.sh" --repo "$FL_REPO" --cmd "true" \
  --once --timeout-secs 15 >"$TMP/once-alias.out" 2>&1
ec=$?
set -e
assert_eq "once alias exit 0" "$ec" "0"
assert "once alias PASS" grep -q 'RESULT=PASS_CLEAN' "$TMP/once-alias.out"

# Deadline arithmetic is deterministic without a production clock override.
set +e
python3 - "$SCRIPTS/run-harness-hard-supervisor.py" <<'PY'
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("hard_supervisor", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
second = 1_000_000_000
assert module.remaining_seconds(4600 * second, now_ns=1000 * second) == 3600
assert module.remaining_seconds(4600 * second, now_ns=4597 * second) == 3
assert module.remaining_seconds(4600 * second, now_ns=4600 * second) == 0
assert module.finalization_reserve_seconds(15) == 1
assert module.finalization_reserve_seconds(1200) == 60
assert module.finalization_reserve_seconds(3600) == 60
PY
ec=$?
set -e
assert_eq "deadline and finalization reserve arithmetic" "$ec" "0"
assert "production clock cannot be replaced by an ambient epoch file" python3 -c "
from pathlib import Path
assert 'TEST_HARNESS_TEST_EPOCH_FILE' not in Path('$SCRIPTS/run-harness.sh').read_text()
"

# A real two-round failure keeps one absolute deadline; later rounds never
# regain the original per-run budget.
set +e
bash "$SCRIPTS/run-harness.sh" --repo "$FL_REPO" --cmd "false" \
  --mode fix-loop --max-rounds 2 --timeout-secs 15 \
  >"$TMP/fl-time-budget.out" 2>&1
ec=$?
set -e
assert_eq "fix-loop shared real deadline stops on repeated failure" "$ec" "2"
assert "fix-loop later round does not reset timeout" python3 -c "
import pathlib, re
text=pathlib.Path('$TMP/fl-time-budget.out').read_text()
values=[int(x) for x in re.findall(r'run · round [12] timeout=([0-9]+)s', text)]
assert len(values)==2, (values, text[-2000:])
assert 0 < values[1] <= values[0] < 15, values
"

# once still default (no --mode)
set +e
bash "$SCRIPTS/run-harness.sh" --repo "$FL_REPO" --cmd "true" \
  --timeout-secs 15 >"$TMP/once-default.out" 2>&1
ec=$?
set -e
assert_eq "once default exit 0" "$ec" "0"
assert "once default mode in manifest" python3 -c "
import re, pathlib, json
text=pathlib.Path('$TMP/once-default.out').read_text()
rd=re.search(r'RUN_DIR=(\S+)', text)
man=json.loads((pathlib.Path(rd.group(1))/'manifest.json').read_text())
assert man['mode']=='once'
assert man['rounds_max']==1
"

# Phase 7 must still emit an evidence-backed INCOMPLETE_RUN when classification
# crashes or returns success without its required JSON artifact.
INJECTED_CLASSIFIER="$TMP/injected-classifier.py"
cat > "$INJECTED_CLASSIFIER" <<'PY'
import os
import signal
import sys
import time
from pathlib import Path

mode = os.environ.get("INJECTED_CLASSIFIER_MODE")
if mode == "hang":
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    Path(os.environ["INJECTED_CLASSIFIER_PID"]).write_text(str(os.getpid()))
    time.sleep(60)
    raise SystemExit(0)
if mode == "fail":
    print("injected classifier crash", file=sys.stderr)
    raise SystemExit(2)
if mode == "missing":
    print("injected classifier omitted output")
    raise SystemExit(0)
if mode == "invalid":
    out = Path(sys.argv[sys.argv.index("--out") + 1])
    out.write_text("[]\n")
    print("injected classifier wrote non-object JSON")
    raise SystemExit(0)
raise SystemExit(3)
PY

set +e
CLASS_FAIL_OUT="$TMP/classifier-failure.out"
INJECTED_CLASSIFIER_MODE=fail TEST_HARNESS_CLASSIFIER="$INJECTED_CLASSIFIER" \
  bash "$SCRIPTS/run-harness.sh" --repo "$FL_REPO" --cmd "true" \
    --timeout-secs 15 >"$CLASS_FAIL_OUT" 2>&1
ec=$?
set -e
assert_eq "classifier execution failure exits incomplete" "$ec" "2"
assert "classifier execution failure emits report evidence" python3 -c "
import json, pathlib, re
text=pathlib.Path('$CLASS_FAIL_OUT').read_text()
rd=re.search(r'RUN_DIR=(\S+)', text)
assert rd, text[-2000:]
run=pathlib.Path(rd.group(1))
report=json.loads((run/'report.json').read_text())
failure=report.get('classifier_failure') or {}
assert report['result']=='INCOMPLETE_RUN', report['result']
assert failure.get('reason')=='classifier_exit_2', failure
assert failure.get('exit')==2, failure
assert 'injected classifier crash' in failure.get('stderr_excerpt',''), failure
assert 'classifier_failure:classifier_exit_2' in report.get('annotations',[]), report
assert (run/'round-1/classifier-failure.json').is_file()
assert (run/'chat-card.md').is_file() and (run/'results.md').is_file()
assert 'test-harness RESULT=INCOMPLETE_RUN' in text, text[-2000:]
"

set +e
CLASS_MISSING_OUT="$TMP/classifier-missing.out"
INJECTED_CLASSIFIER_MODE=missing TEST_HARNESS_CLASSIFIER="$INJECTED_CLASSIFIER" \
  bash "$SCRIPTS/run-harness.sh" --repo "$FL_REPO" --cmd "true" \
    --timeout-secs 15 >"$CLASS_MISSING_OUT" 2>&1
ec=$?
set -e
assert_eq "missing classifier JSON exits incomplete" "$ec" "2"
assert "missing classifier JSON emits report evidence" python3 -c "
import json, pathlib, re
text=pathlib.Path('$CLASS_MISSING_OUT').read_text()
rd=re.search(r'RUN_DIR=(\S+)', text)
assert rd, text[-2000:]
run=pathlib.Path(rd.group(1))
report=json.loads((run/'report.json').read_text())
failure=report.get('classifier_failure') or {}
assert report['result']=='INCOMPLETE_RUN', report['result']
assert failure.get('reason')=='classifier_output_missing', failure
assert failure.get('exit')==0, failure
assert failure.get('output_exists') is False, failure
assert 'missing_classifier_output' in report.get('annotations',[]), report
assert 'classifier_failure:classifier_output_missing' in report.get('annotations',[]), report
assert (run/'chat-card.md').is_file() and (run/'results.md').is_file()
assert 'test-harness RESULT=INCOMPLETE_RUN' in text, text[-2000:]
"

set +e
CLASS_INVALID_OUT="$TMP/classifier-invalid.out"
INJECTED_CLASSIFIER_MODE=invalid TEST_HARNESS_CLASSIFIER="$INJECTED_CLASSIFIER" \
  bash "$SCRIPTS/run-harness.sh" --repo "$FL_REPO" --cmd "true" \
    --timeout-secs 15 >"$CLASS_INVALID_OUT" 2>&1
ec=$?
set -e
assert_eq "invalid classifier JSON exits incomplete" "$ec" "2"
assert "invalid classifier JSON emits report evidence" python3 -c "
import json, pathlib, re
text=pathlib.Path('$CLASS_INVALID_OUT').read_text()
rd=re.search(r'RUN_DIR=(\S+)', text)
assert rd, text[-2000:]
run=pathlib.Path(rd.group(1))
report=json.loads((run/'report.json').read_text())
failure=report.get('classifier_failure') or {}
assert report['result']=='INCOMPLETE_RUN', report['result']
assert failure.get('reason')=='classifier_output_invalid', failure
assert failure.get('exit')==0, failure
assert failure.get('output_exists') is True, failure
assert json.loads((run/'round-1/side-effects.json').read_text())==[]
assert 'missing_classifier_output' in report.get('annotations',[]), report
assert 'classifier_failure:classifier_output_invalid' in report.get('annotations',[]), report
assert (run/'round-1/classifier-failure.json').is_file()
assert (run/'chat-card.md').is_file() and (run/'results.md').is_file()
assert 'test-harness RESULT=INCOMPLETE_RUN' in text, text[-2000:]
"

# A successful suite followed by a TERM-resistant classifier is still enclosed
# by the same wall clock and cannot hang the harness after tests complete.
CLASS_HANG_PID="$TMP/classifier-hang.pid"
CLASS_HANG_OUT="$TMP/classifier-hang.out"
class_hang_started_ms="$(python3 -c 'import time; print(int(time.time() * 1000))')"
set +e
INJECTED_CLASSIFIER_MODE=hang INJECTED_CLASSIFIER_PID="$CLASS_HANG_PID" \
  TEST_HARNESS_CLASSIFIER="$INJECTED_CLASSIFIER" \
  bash "$SCRIPTS/run-harness.sh" --repo "$FL_REPO" --cmd "true" \
    --timeout-secs "$HANG_CAP_SECS" >"$CLASS_HANG_OUT" 2>&1
ec=$?
set -e
class_hang_finished_ms="$(python3 -c 'import time; print(int(time.time() * 1000))')"
class_hang_duration_ms=$((class_hang_finished_ms - class_hang_started_ms))
assert_eq "hanging classifier exits through hard timeout" "$ec" "124"
assert "hanging classifier stays near the enclosing cap" \
  test "$class_hang_duration_ms" -lt $((HANG_CAP_SECS * 1000 + TIMING_SLACK_MS))
assert_pid_file_dead "hanging classifier process is reaped" "$CLASS_HANG_PID"
assert "hanging classifier records hard-timeout evidence" python3 -c "
import json, pathlib, re
text=pathlib.Path('$CLASS_HANG_OUT').read_text()
rd=re.search(r'RUN_DIR=(\\S+)', text)
assert rd, text[-2000:]
doc=json.loads((pathlib.Path(rd.group(1))/'hard-timeout.json').read_text())
assert doc['stop']=='hard_timeout', doc
assert doc['timeout_secs']==$HANG_CAP_SECS, doc
"

# Report generation is inside the same supervisor. Exercise it from a copied
# skill so the production emitter remains untouched.
REPORT_HANG_SKILL="$TMP/report-hang-skill"
mkdir -p "$REPORT_HANG_SKILL"
cp -R "$ROOT/." "$REPORT_HANG_SKILL/"
cat >"$REPORT_HANG_SKILL/scripts/emit-report.py" <<'PY'
import os
from pathlib import Path
import signal
import time

signal.signal(signal.SIGTERM, signal.SIG_IGN)
Path(os.environ["REPORT_HANG_PID"]).write_text(str(os.getpid()))
time.sleep(60)
PY
REPORT_HANG_PID="$TMP/report-hang.pid"
REPORT_HANG_OUT="$TMP/report-hang.out"
report_hang_started_ms="$(python3 -c 'import time; print(int(time.time() * 1000))')"
set +e
REPORT_HANG_PID="$REPORT_HANG_PID" \
  bash "$REPORT_HANG_SKILL/scripts/run-harness.sh" \
    --repo "$FL_REPO" --cmd "true" --timeout-secs "$HANG_CAP_SECS" \
    >"$REPORT_HANG_OUT" 2>&1
ec=$?
set -e
report_hang_finished_ms="$(python3 -c 'import time; print(int(time.time() * 1000))')"
report_hang_duration_ms=$((report_hang_finished_ms - report_hang_started_ms))
assert_eq "hanging report exits through hard timeout" "$ec" "124"
assert "hanging report stays near the enclosing cap" \
  test "$report_hang_duration_ms" -lt $((HANG_CAP_SECS * 1000 + TIMING_SLACK_MS))
assert_pid_file_dead "hanging report process is reaped" "$REPORT_HANG_PID"

# A failing once-mode run operates in the caller's shared working tree. It
# must preserve both clean-at-pre rewrites and absent-at-pre additions because
# either could be concurrent WIP from an operator or another agent.
ONCE_SHARED="$TMP/once-shared-preserve"
make_repo "$ONCE_SHARED"
set +e
ONCE_SHARED_OUT="$TMP/once-shared-preserve.out"
bash "$SCRIPTS/run-harness.sh" --repo "$ONCE_SHARED" \
  --cmd "printf 'post-state\\n' > src/app.js; printf 'new-state\\n' > src/newfile.js; false" \
  --timeout-secs 30 >"$ONCE_SHARED_OUT" 2>&1
ec=$?
set -e
assert_eq "once shared preservation exits fail" "$ec" "1"
assert_eq "once shared preserves changed tracked bytes" "$(cat "$ONCE_SHARED/src/app.js")" "post-state"
assert_eq "once shared preserves added file bytes" "$(cat "$ONCE_SHARED/src/newfile.js")" "new-state"
assert "once shared reconciliation leaves index untouched" git -C "$ONCE_SHARED" diff --cached --quiet
python3 - <<PY
import json, pathlib, re
text=pathlib.Path("$ONCE_SHARED_OUT").read_text()
rd=re.search(r"RUN_DIR=(\\S+)", text)
assert rd, text[-2000:]
run=pathlib.Path(rd.group(1))
restore=json.loads((run/"round-1/restore.json").read_text())
assert restore["restore_policy"]=="preserve-shared", restore
assert restore["preserved_post_state_count"]==2, restore
assert restore["manual_reconciliation_required"] is True, restore
assert {a["action"] for a in restore["actions"]}=={"preserve-shared-post-state"}, restore
assert "manual reconciliation required" in text, text[-2000:]
print("once shared post state preserved", run)
PY
assert "once shared preserve-all policy is reported" true

# An explicit command is fast by default, but --full must remain authoritative.
# Otherwise a deliberate live/full command is mislabeled fast and the
# side-effect classifier reports LIVE_GATE_ON_FAST.
set +e
TEST_HARNESS_TIMEOUT="" TEST_HARNESS_FULL_TIMEOUT="" \
  bash "$SCRIPTS/run-harness.sh" --repo "$FL_REPO" --cmd "true" --full \
  >"$TMP/explicit-full.out" 2>&1
ec=$?
set -e
assert_eq "explicit --cmd --full exit 0" "$ec" "0"
assert "explicit --cmd --full profile full" python3 -c "
import re, pathlib, json
text=pathlib.Path('$TMP/explicit-full.out').read_text()
rd=re.search(r'RUN_DIR=(\S+)', text)
run=pathlib.Path(rd.group(1))
discover=json.loads((run/'discover.json').read_text())
manifest=json.loads((run/'manifest.json').read_text())
assert discover['profile']=='full', discover
assert manifest['profile']=='full', manifest
"
grep -q 'deadline · total=3600s' "$TMP/explicit-full.out" \
  && assert "explicit --cmd --full defaults to one-hour outer timeout" true \
  || assert "explicit --cmd --full defaults to one-hour outer timeout" false

# ---------------------------------------------------------------------------
echo "--- emit-report RESULT_JSON + tagged control channel ---"
# ---------------------------------------------------------------------------
out="$(
  python3 - <<PY
import importlib.util, json
p = "$SCRIPTS/emit-report.py"
spec = importlib.util.spec_from_file_location("emit_report", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
stdout = 'RESULT_JSON {"total": 10, "failures": 0, "errors": 0, "skipped": 1, "skip_details": []}\n'
stderr = (
    ("[run] x\n" * 20)
    + ("[test] y\n" * 20)
)
parsed = m.parse_suite_logs(stdout, stderr, 0)
print(json.dumps({
  "pass": parsed.get("pass_count"),
  "fail": parsed.get("fail_count"),
  "skip": parsed.get("skip_count"),
  "source": parsed.get("suite_summary_source"),
  "status": (parsed.get("control_channels") or {}).get("stderr", {}).get("status"),
  "has_excerpt": "product_excerpt" in (parsed.get("control_channels") or {}),
}))
PY
)"
assert_json_field "RESULT_JSON pass_count" "$out" "d['pass']" "9"
assert_json_field "RESULT_JSON fail_count" "$out" "d['fail']" "0"
assert_json_field "RESULT_JSON skip_count" "$out" "d['skip']" "1"
assert_json_field "RESULT_JSON source" "$out" "d['source']" "result_json"
assert_json_field "stderr control_ok" "$out" "d['status']" "control_ok"
assert_json_field "no tool-specific excerpt block is produced" "$out" "d['has_excerpt']" "false"
# ---------------------------------------------------------------------------
echo "--- default run root (outside the repository under test, no host-named directory) ---"
# ---------------------------------------------------------------------------
DRR_HOME="$TMP/drr-home"
DRR_XDG="$TMP/drr-xdg"
DRR_OVERRIDE="$TMP/drr-override"
mkdir -p "$DRR_HOME" "$DRR_XDG" "$DRR_OVERRIDE"

# Neither override set: $HOME/.local/state/test-harness/runs
set +e
env -u TEST_HARNESS_RUN_ROOT -u XDG_STATE_HOME HOME="$DRR_HOME" \
  bash "$SCRIPTS/run-harness.sh" --repo "$RREPO" --cmd "true" --timeout-secs 30 \
  >"$TMP/drr-home.out" 2>&1
ec=$?
set -e
assert_eq "default run root: run exits 0" "$ec" "0"
assert "default run root is \$HOME/.local/state/test-harness/runs" python3 -c "
import pathlib, re
text=pathlib.Path('$TMP/drr-home.out').read_text()
m=re.search(r'^RUN_DIR=(\\S+)$', text, re.M)
assert m, text[-1500:]
run=pathlib.Path(m.group(1)).resolve()
root=(pathlib.Path('$DRR_HOME')/'.local'/'state'/'test-harness'/'runs').resolve()
assert run.parent.parent == root, (run, root)
assert (run/'manifest.json').is_file()
"
assert "default run root creates only .local under HOME (no host-named directory)" python3 -c "
import pathlib
names={p.name for p in pathlib.Path('$DRR_HOME').iterdir()}
assert names == {'.local'}, names
"

# XDG_STATE_HOME moves it
set +e
env -u TEST_HARNESS_RUN_ROOT HOME="$DRR_HOME" XDG_STATE_HOME="$DRR_XDG" \
  bash "$SCRIPTS/run-harness.sh" --repo "$RREPO" --cmd "true" --timeout-secs 30 \
  >"$TMP/drr-xdg.out" 2>&1
ec=$?
set -e
assert_eq "XDG_STATE_HOME run exits 0" "$ec" "0"
assert "XDG_STATE_HOME moves the default run root" python3 -c "
import pathlib, re
text=pathlib.Path('$TMP/drr-xdg.out').read_text()
m=re.search(r'^RUN_DIR=(\\S+)$', text, re.M)
assert m, text[-1500:]
run=pathlib.Path(m.group(1)).resolve()
root=(pathlib.Path('$DRR_XDG')/'test-harness'/'runs').resolve()
assert run.parent.parent == root, (run, root)
"

# TEST_HARNESS_RUN_ROOT beats both
set +e
env HOME="$DRR_HOME" XDG_STATE_HOME="$DRR_XDG" TEST_HARNESS_RUN_ROOT="$DRR_OVERRIDE" \
  bash "$SCRIPTS/run-harness.sh" --repo "$RREPO" --cmd "true" --timeout-secs 30 \
  >"$TMP/drr-override.out" 2>&1
ec=$?
set -e
assert_eq "TEST_HARNESS_RUN_ROOT run exits 0" "$ec" "0"
assert "TEST_HARNESS_RUN_ROOT overrides the default and XDG_STATE_HOME" python3 -c "
import pathlib, re
text=pathlib.Path('$TMP/drr-override.out').read_text()
m=re.search(r'^RUN_DIR=(\\S+)$', text, re.M)
assert m, text[-1500:]
run=pathlib.Path(m.group(1)).resolve()
assert run.parent.parent == pathlib.Path('$DRR_OVERRIDE').resolve(), run
"

# The hard supervisor computes the same default (it is the process that names the run directory).
set +e
python3 - "$SCRIPTS/run-harness-hard-supervisor.py" <<'PY'
import importlib.util
import os
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("hard_supervisor_run_root", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
os.environ["HOME"] = "/nonexistent-home"
os.environ.pop("XDG_STATE_HOME", None)
assert module.default_run_root() == Path("/nonexistent-home/.local/state/test-harness/runs")
os.environ["XDG_STATE_HOME"] = ""
assert module.default_run_root() == Path("/nonexistent-home/.local/state/test-harness/runs")
os.environ["XDG_STATE_HOME"] = "/nonexistent-state"
assert module.default_run_root() == Path("/nonexistent-state/test-harness/runs")
PY
ec=$?
set -e
assert_eq "hard supervisor default run root follows XDG_STATE_HOME, else ~/.local/state" "$ec" "0"

# ---------------------------------------------------------------------------
echo "=== summary: PASS=$PASS FAIL=$FAIL ==="
if [[ "$FAIL" -ne 0 ]]; then
  exit 1
fi
exit 0
