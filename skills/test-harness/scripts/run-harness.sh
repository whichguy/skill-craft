#!/usr/bin/env bash
# run-harness.sh — unified mechanical driver for once + fix-loop modes.
#
# Usage:
#   run-harness.sh --repo <WORK_ROOT> [--mode once|fix-loop] [--cmd …] [--full]
#     [--assume-fast] [--timeout-secs N] [--max-rounds N]
#
# Defaults: --mode once (rounds_max=1, no worktree).
# --mode fix-loop (or --fix-loop): default max-rounds 5; worktree isolation;
#   mechanical round loop with restore-on-fail. Product fixes remain agent-owned
#   (re-invoke after editing worktree); plumbing must never be hand-rolled.
#
# Package scope:
#   WORK_ROOT  = path passed as --repo (suite identity)
#   GIT_ROOT   = git rev-parse --show-toplevel from WORK_ROOT
#   AUDIT_PREFIX = relpath GIT_ROOT → WORK_ROOT when nested
# Suite: --repo "$SUITE_CWD" (WORK_ROOT once; suite_cwd under worktree on fix-loop)
# Porcelain: --repo "$PORC_REPO" + optional --path-prefix from scope.json
set -euo pipefail
umask 077

ORIGINAL_ARGS=("$@")
RUN_HARNESS_SOURCE="${BASH_SOURCE[0]}"
if [[ "$RUN_HARNESS_SOURCE" == */* ]]; then
  BOOTSTRAP_SCRIPTS_DIR="${RUN_HARNESS_SOURCE%/*}"
else
  BOOTSTRAP_SCRIPTS_DIR="."
fi
HARD_SUPERVISOR_SCRIPT="$BOOTSTRAP_SCRIPTS_DIR/run-harness-hard-supervisor.py"
REPO=""
CMD=""
FULL=0
ASSUME_FAST=0
TIMEOUT_SECS="${TEST_HARNESS_TIMEOUT:-}"
MAX_TIMEOUT_SECS=3600
MODE="once"
MAX_ROUNDS=""   # empty → default by mode (once=1, fix-loop=5)
MODE_EXPLICIT=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO="${2:-}"; shift 2 ;;
    --cmd) CMD="${2:-}"; shift 2 ;;
    --full) FULL=1; shift ;;
    --assume-fast) ASSUME_FAST=1; shift ;;
    --timeout-secs) TIMEOUT_SECS="${2:-}"; shift 2 ;;
    --max-rounds|--rounds-max) MAX_ROUNDS="${2:-}"; shift 2 ;;
    --mode)
      MODE="${2:-}"
      MODE_EXPLICIT=1
      shift 2
      ;;
    --fix-loop)
      MODE="fix-loop"
      MODE_EXPLICIT=1
      shift
      ;;
    --once)
      MODE="once"
      MODE_EXPLICIT=1
      shift
      ;;
    -h|--help)
      cat <<EOF
Usage: run-harness.sh --repo <WORK_ROOT> [options]

Unified driver: once (audit) or fix-loop (worktree + restore-on-fail rounds).

Options:
  --repo <path>           WORK_ROOT (suite cwd / package path; required)
  --mode once|fix-loop   Default: once
  --once                 Alias for --mode once
  --fix-loop             Alias for --mode fix-loop
  --cmd <str>             Explicit suite command (skips discover)
  --full                  Prefer full-profile discover targets
  --assume-fast           Treat unknown profile as fast; allow fix-loop
  --timeout-secs N        Suite timeout (default fast=1200, full=3600;
                          hard maximum 3600; override within that limit with
                          \$TEST_HARNESS_TIMEOUT or \$TEST_HARNESS_FULL_TIMEOUT)
  --max-rounds N          Rounds budget (once default 1; fix-loop default 5)
  --rounds-max N          Alias for --max-rounds

Modes:
  once       Single round in WORK_ROOT; no worktree.
  fix-loop   Enter disposable worktree; each round: pre → suite → post →
             classify; on pass emit+exit worktree; on fail restore and
             continue until budget. Product edits are agent-owned (re-invoke).

Discovery: --cmd, then .test-harness.yml/json cmd, then Makefile / package.json /
path tiers (no AGENTS.md prose). Package --repo may be a skill subdir
(PASS_CLEAN_SCOPED when nested FS audit is clean).
EOF
      exit 0
      ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ "$MODE" != "once" && "$MODE" != "fix-loop" ]]; then
  echo "error: --mode must be once or fix-loop (got: $MODE)" >&2
  exit 2
fi

banner() { echo "▸ test-harness · $*"; }

harness_hard_supervisor_active() {
  local pid="${TEST_HARNESS_HARD_SUPERVISOR_PID:-}"
  local deadline="${TEST_HARNESS_HARD_DEADLINE_EPOCH_MS:-}"
  local capability_fd="${TEST_HARNESS_HARD_CAPABILITY_FD:-}"
  local capability_nonce="${TEST_HARNESS_HARD_CAPABILITY_NONCE:-}"
  local now_ms remaining
  [[ "${TEST_HARNESS_HARD_SUPERVISED:-0}" == "1" ]] || return 1
  [[ "$pid" =~ ^[1-9][0-9]*$ && ${#pid} -le 10 ]] || return 1
  [[ "$deadline" =~ ^[1-9][0-9]*$ && ${#deadline} -le 16 ]] || return 1
  [[ "$capability_fd" =~ ^[0-9]+$ && ${#capability_fd} -le 10 ]] || return 1
  (( capability_fd >= 3 && capability_fd <= 2147483647 )) || return 1
  [[ "$capability_nonce" =~ ^[0-9a-f]{64}$ ]] || return 1
  [[ "$PPID" == "$pid" ]] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  python3 - "$capability_fd" "$capability_nonce" <<'PY' || return 1
import os
import stat
import sys

fd = int(sys.argv[1])
expected = (sys.argv[2] + "\n").encode("ascii")
try:
    mode = os.fstat(fd).st_mode
    if not stat.S_ISFIFO(mode) or os.get_blocking(fd):
        raise SystemExit(1)
    actual = os.read(fd, len(expected))
except OSError:
    raise SystemExit(1)
if actual != expected:
    raise SystemExit(1)
PY
  now_ms="$(python3 -c 'import time; print(int(time.time() * 1000))')"
  remaining=$((deadline - now_ms))
  (( remaining > 0 && remaining <= MAX_TIMEOUT_SECS * 1000 ))
}

harness_now_epoch() {
  local now
  now="$(date +%s)"
  if ! [[ "$now" =~ ^[0-9]+$ ]]; then
    echo "error: current epoch must be a non-negative integer (got '$now')" >&2
    return 2
  fi
  printf '%s\n' "$now"
}

stop_timeout_budget() {
  local round_no="$1"
  local observed_epoch="$2"
  python3 - "$RUN_DIR/terminal.json" "$round_no" "$TIMEOUT_SECS" \
    "$HARNESS_STARTED_EPOCH" "$HARNESS_DEADLINE_EPOCH" "$observed_epoch" <<'PY'
import json
import sys
from pathlib import Path

out, round_no, timeout_secs, started_epoch, deadline_epoch, observed_epoch = sys.argv[1:]
Path(out).write_text(json.dumps({
    "stop": "timeout_budget_exhausted",
    "detail": "harness-wide timeout budget exhausted before the next suite run",
    "round": int(round_no),
    "timeout_secs": int(timeout_secs),
    "started_epoch": int(started_epoch),
    "deadline_epoch": int(deadline_epoch),
    "observed_epoch": int(observed_epoch),
}, indent=2) + "\n")
PY
  banner "deadline · exhausted before round $round_no suite → emit STOPPED_TIMEOUT_BUDGET"
  emit_and_exit "$USED_WORKTREE"
}

# ---------------------------------------------------------------------------
# resolve_scope — SSOT via resolve-scope.py; persist to $RUN_DIR later
# ---------------------------------------------------------------------------
resolve_scope() {
  SCOPE_JSON="$(python3 "$SKILL_DIR/scripts/resolve-scope.py" --repo "$REPO")"
  eval "$(python3 -c '
import json,sys,shlex
d=json.loads(sys.argv[1])
def e(k,v):
    if v is None: v=""
    print(f"{k}={shlex.quote(str(v))}")
e("WORK_ROOT", d["work_root"])
e("GIT_ROOT", d.get("git_root") or "")
e("AUDIT_PREFIX", d.get("audit_prefix") or "")
e("PORC_REPO", d["porc_repo"])
e("SLUG", d["slug"])
' "$SCOPE_JSON")"
  REPO="$WORK_ROOT"
}

# ---------------------------------------------------------------------------
# discover_cmd — --cmd or discover-test-cmd.sh; write discover.json
# ---------------------------------------------------------------------------
discover_cmd() {
  SOURCE="explicit"
  PROFILE="fast"
  if [[ -z "$CMD" ]]; then
    banner "discover · $SLUG"
    DISC_ARGS=(--repo "$WORK_ROOT")
    [[ $FULL -eq 1 ]] && DISC_ARGS+=(--full)
    set +e
    DISC_JSON="$(bash "$SKILL_DIR/scripts/discover-test-cmd.sh" "${DISC_ARGS[@]}")"
    DEC=$?
    set -e
    if [[ $DEC -ne 0 ]]; then
      echo "$DISC_JSON" >"$RUN_DIR/discover.json" || true
      echo "error: no deterministic test command; pass --cmd" >&2
      exit 2
    fi
    echo "$DISC_JSON" | tee "$RUN_DIR/discover.json" >/dev/null
    CMD="$(python3 -c "import json,sys; print(json.load(sys.stdin)['cmd'])" <<<"$DISC_JSON")"
    PROFILE="$(python3 -c "import json,sys; print(json.load(sys.stdin)['profile'])" <<<"$DISC_JSON")"
    SOURCE="$(python3 -c "import json,sys; print(json.load(sys.stdin)['source'])" <<<"$DISC_JSON")"
  else
    if [[ $FULL -eq 1 ]]; then
      PROFILE="full"
    fi
    python3 -c '
import json,sys
cmd,profile=sys.argv[1:3]
print(json.dumps({
  "cmd": cmd, "profile": profile, "source": "explicit",
  "suite_scope": "full", "habitat": "host",
}))
' "$CMD" "$PROFILE" >"$RUN_DIR/discover.json"
    SOURCE="explicit"
  fi

  if [[ $ASSUME_FAST -eq 1 && "$PROFILE" == "unknown" ]]; then
    PROFILE="fast"
  fi

  # unknown profile → force once (no automatic fix-loop without --assume-fast)
  if [[ "$MODE" == "fix-loop" && "$PROFILE" == "unknown" && $ASSUME_FAST -eq 0 ]]; then
    banner "profile unknown · demoting fix-loop → once (pass --assume-fast to allow)"
    MODE="once"
  fi

  SUITE_SCOPE="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('suite_scope','full'))" "$RUN_DIR/discover.json" 2>/dev/null || echo full)"
  HABITAT="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('habitat','host'))" "$RUN_DIR/discover.json" 2>/dev/null || echo host)"
}

# ---------------------------------------------------------------------------
# init_run — manifest + control policy + allowlist path
# ---------------------------------------------------------------------------
init_run() {
  if [[ -z "$MAX_ROUNDS" ]]; then
    if [[ "$MODE" == "fix-loop" ]]; then
      ROUNDS_MAX=5
    else
      ROUNDS_MAX=1
    fi
  else
    ROUNDS_MAX="$MAX_ROUNDS"
  fi
  if ! [[ "$ROUNDS_MAX" =~ ^[1-9][0-9]*$ ]]; then
    echo "error: --max-rounds must be a positive integer" >&2
    exit 2
  fi

  FLAGS=()
  [[ "$MODE" == "once" ]] && FLAGS+=(--flag once)
  [[ $ASSUME_FAST -eq 1 ]] && FLAGS+=(--flag assume_fast --assume-fast)
  [[ "$PROFILE" == "unknown" ]] && FLAGS+=(--flag profile_unknown_defaulted)
  [[ -n "$AUDIT_PREFIX" ]] && FLAGS+=(--flag package_scoped)
  FLAGS+=(--flag "suite_scope_${SUITE_SCOPE}" --flag "habitat_${HABITAT}")

  banner "init · $SLUG mode=$MODE rounds_max=$ROUNDS_MAX"
  INIT_ARGS=(
    --repo "$WORK_ROOT"
    --run-dir "$RUN_DIR"
    --cmd "$CMD"
    --profile "$PROFILE"
    --source "$SOURCE"
    --mode "$MODE"
    --rounds-max "$ROUNDS_MAX"
    --suite-scope "$SUITE_SCOPE"
    --habitat "$HABITAT"
    --work-root "$WORK_ROOT"
    --git-root "${GIT_ROOT:-$WORK_ROOT}"
    --audit-prefix "$AUDIT_PREFIX"
  )
  python3 "$SKILL_DIR/scripts/init-run.py" \
    "${INIT_ARGS[@]}" \
    "${FLAGS[@]}" >/dev/null

  banner "control-policy · resolve"
  POLICY_FILE=""
  for root in "$WORK_ROOT" ${GIT_ROOT:+"$GIT_ROOT"}; do
    for cand in "$root/.test-harness.yml" "$root/test/harness-allowlist.yml" "$root/.test-harness.json"; do
      if [[ -f "$cand" ]]; then
        POLICY_FILE="$cand"
        break 2
      fi
    done
  done
  set +e
  if [[ -n "$POLICY_FILE" ]]; then
    python3 "$SKILL_DIR/scripts/control_policy.py" resolve \
      --repo "$WORK_ROOT" \
      --run-dir "$RUN_DIR" \
      --profile "$PROFILE" \
      --policy-file "$POLICY_FILE"
  else
    python3 "$SKILL_DIR/scripts/control_policy.py" resolve \
      --repo "$WORK_ROOT" \
      --run-dir "$RUN_DIR" \
      --profile "$PROFILE"
  fi
  POL_EC=$?
  set -e
  if [[ $POL_EC -ne 0 ]]; then
    echo "error: control policy resolve failed (exit $POL_EC)" >&2
    exit 2
  fi

  ALLOWLIST=""
  for root in "$WORK_ROOT" ${GIT_ROOT:+"$GIT_ROOT"}; do
    for cand in "$root/.test-harness.yml" "$root/test/harness-allowlist.yml" "$root/.test-harness.json"; do
      if [[ -f "$cand" ]]; then
        ALLOWLIST="$cand"
        break 2
      fi
    done
  done

  if [[ -n "$AUDIT_PREFIX" ]]; then
    banner "package-scope · audit_prefix=$AUDIT_PREFIX git_root=$GIT_ROOT"
  fi
}

# ---------------------------------------------------------------------------
# porcelain — always PORC_REPO + optional path-prefix from scope
# ---------------------------------------------------------------------------
porcelain() {
  # usage: porcelain <round> snapshot pre|post | porcelain <round> diff | porcelain <round> restore
  local round="$1"
  local mode="$2"
  shift 2
  local -a base=(
    python3 "$SKILL_DIR/scripts/porcelain-delta.py"
    --repo "$PORC_REPO"
    --run-dir "$RUN_DIR"
    --round "$round"
    --mode "$mode"
  )
  if [[ -n "$AUDIT_PREFIX" ]]; then
    base+=(--path-prefix "$AUDIT_PREFIX")
  fi
  if [[ "$mode" == "snapshot" ]]; then
    local side="$1"
    "${base[@]}" --side "$side" >/dev/null
  elif [[ "$mode" == "restore" ]]; then
    local restore_policy="${1:-preserve-shared}"
    "${base[@]}" --restore-policy "$restore_policy" >/dev/null
  else
    "${base[@]}" >/dev/null
  fi
}

# ---------------------------------------------------------------------------
# one_round N — pre → remaining-budget check → suite → post → diff → classify
# sets: SUITE_EC, ROUND_PASS (0|1)
# ---------------------------------------------------------------------------
one_round() {
  local N="$1"
  banner "baseline · round $N"
  porcelain "$N" snapshot pre

  local now_epoch round_timeout_secs
  now_epoch="$(harness_now_epoch)"
  round_timeout_secs=$((HARNESS_DEADLINE_EPOCH - now_epoch))
  if [[ $round_timeout_secs -le 0 ]]; then
    stop_timeout_budget "$N" "$now_epoch"
  fi

  banner "run · round $N timeout=${round_timeout_secs}s cwd=$SUITE_CWD"
  set +e
  bash "$SKILL_DIR/scripts/run-suite.sh" \
    --repo "$SUITE_CWD" \
    --cmd "$CMD" \
    --out "$RUN_DIR/round-$N" \
    --timeout-secs "$round_timeout_secs"
  SUITE_EC=$?
  set -e

  banner "audit · round $N"
  porcelain "$N" snapshot post
  porcelain "$N" diff

  local -a CLASS_ARGS=(
    --delta "$RUN_DIR/round-$N/delta.json"
    --profile "$PROFILE"
    --log "$RUN_DIR/round-$N/stdout.log"
    --log "$RUN_DIR/round-$N/stderr.log"
    --tmpdir "$RUN_DIR/round-$N/tmp"
    --run-dir "$RUN_DIR"
    --out "$RUN_DIR/round-$N/side-effects.json"
    --control-policy "$RUN_DIR/control-policy.json"
    --suite-exit "$SUITE_EC"
  )
  if [[ -n "$ALLOWLIST" ]]; then
    CLASS_ARGS+=(--allowlist "$ALLOWLIST")
  fi
  if [[ "$HABITAT" == "container" ]]; then
    banner "audit · habitat=container → side_effects unaudited for FS"
  fi

  local class_stdout="$RUN_DIR/round-$N/classifier.stdout.log"
  local class_stderr="$RUN_DIR/round-$N/classifier.stderr.log"
  local class_output="$RUN_DIR/round-$N/side-effects.json"
  local class_failure="$RUN_DIR/round-$N/classifier-failure.json"
  local class_ec class_reason=""
  rm -f "$class_output" "$class_failure"
  set +e
  python3 "$CLASSIFIER_SCRIPT" "${CLASS_ARGS[@]}" >"$class_stdout" 2>"$class_stderr"
  class_ec=$?
  set -e

  if [[ $class_ec -ne 0 && $class_ec -ne 1 ]]; then
    class_reason="classifier_exit_$class_ec"
  elif [[ ! -s "$class_output" ]]; then
    class_reason="classifier_output_missing"
  elif ! python3 -c '
import json, sys
with open(sys.argv[1]) as f:
    doc = json.load(f)
if not isinstance(doc, dict):
    raise ValueError("classifier output must be a JSON object")
' "$class_output" 2>>"$class_stderr"; then
    class_reason="classifier_output_invalid"
  fi

  [[ ! -s "$class_stdout" ]] || cat "$class_stdout"
  [[ ! -s "$class_stderr" ]] || cat "$class_stderr" >&2

  if [[ -n "$class_reason" ]]; then
    python3 - "$class_failure" "$class_ec" "$class_reason" "$CLASSIFIER_SCRIPT" \
      "$class_output" "$class_stdout" "$class_stderr" <<'PY' || true
import json
import sys
from pathlib import Path

out, exit_code, reason, classifier, expected, stdout_log, stderr_log = sys.argv[1:]

def excerpt(path):
    p = Path(path)
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")[-2000:]

Path(out).write_text(json.dumps({
    "phase": "classify",
    "reason": reason,
    "exit": int(exit_code),
    "classifier": classifier,
    "expected_output": expected,
    "output_exists": Path(expected).is_file(),
    "stdout_log": stdout_log,
    "stderr_log": stderr_log,
    "stdout_excerpt": excerpt(stdout_log),
    "stderr_excerpt": excerpt(stderr_log),
}, indent=2) + "\n")
PY
    banner "audit · round $N classifier incomplete ($class_reason) → emit INCOMPLETE_RUN"
    emit_and_exit "${USED_WORKTREE:-0}"
  fi

  read -r MAT FAIL NOTE < <(python3 - <<PY
import json
from pathlib import Path
d=json.loads(Path("$RUN_DIR/round-$N/delta.json").read_text())
se=json.loads(Path("$RUN_DIR/round-$N/side-effects.json").read_text())
mat=sum(1 for x in d.get("delta",[]) if x.get("change")!="unchanged-baseline")
print(mat, se.get("summary",{}).get("fail",0), se.get("summary",{}).get("note",0))
PY
)
  banner "audit · round $N material=$MAT fail=$FAIL note=$NOTE"

  ROUND_PASS=0
  if [[ $SUITE_EC -eq 0 ]]; then
    local side_ok
    side_ok="$(python3 -c "
import json
from pathlib import Path
se=json.loads(Path('$RUN_DIR/round-$N/side-effects.json').read_text())
print('1' if se.get('side_effects_ok', se.get('summary',{}).get('fail',1)==0) else '0')
")"
    if [[ "$side_ok" == "1" ]]; then
      ROUND_PASS=1
    fi
  fi
}

# ---------------------------------------------------------------------------
# emit_and_exit — report + optional worktree exit + process exit code
# ---------------------------------------------------------------------------
emit_and_exit() {
  local used_worktree="${1:-0}"
  banner "report"
  set +e
  python3 "$SKILL_DIR/scripts/emit-report.py" --run-dir "$RUN_DIR"
  EM_EC=$?
  set -e

  RESULT="$(python3 -c "import json;print(json.load(open('$RUN_DIR/report.json'))['result'])" 2>/dev/null || echo INCOMPLETE_RUN)"
  banner "report · RESULT=$RESULT"

  if [[ "$used_worktree" == "1" ]]; then
    banner "worktree · exit"
    bash "$SKILL_DIR/scripts/worktree-fixloop.sh" exit \
      --repo "$WORK_ROOT" --run-dir "$RUN_DIR" >/dev/null || true
  fi

  if [[ -f "$RUN_DIR/chat-card.md" ]]; then
    echo ""
    echo "----- chat-card.md (paste into chat) -----"
    cat "$RUN_DIR/chat-card.md"
    echo "----- end chat-card.md -----"
  fi
  echo "RUN_DIR=$RUN_DIR"
  if [[ -f "$RUN_DIR/report.html" ]]; then
    echo "HTML:  $RUN_DIR/report.html"
  fi
  echo "Inspect:"
  echo "  less '$RUN_DIR/results.md'"
  local last_round
  last_round="$(python3 -c "
from pathlib import Path
rd=Path('$RUN_DIR')
ns=sorted(int(p.name.split('-')[1]) for p in rd.glob('round-*') if p.is_dir() and p.name.split('-')[1].isdigit())
print(ns[-1] if ns else 1)
")"
  echo "  less '$RUN_DIR/round-$last_round/stdout.log'"
  echo "  less '$RUN_DIR/round-$last_round/stderr.log'"

  case "$RESULT" in
    PASS_CLEAN|PASS_CLEAN_SCOPED) exit 0 ;;
    INCOMPLETE_RUN|STOPPED_*) exit 2 ;;
    *) exit 1 ;;
  esac
}

# ============================== main =======================================
# Enclose every workspace operation beneath a real process-group wall clock.
# Explicit timeouts are exact. An undiscovered default starts under the global
# one-hour ceiling; the worker later applies its 1,200s fast or 3,600s full
# cooperative budget, including a finalization reserve.
if ! harness_hard_supervisor_active; then
  HARD_TIMEOUT_SECS="$TIMEOUT_SECS"
  if [[ -z "$HARD_TIMEOUT_SECS" ]]; then
    if [[ $FULL -eq 1 ]]; then
      HARD_TIMEOUT_SECS="${TEST_HARNESS_FULL_TIMEOUT:-3600}"
    else
      HARD_TIMEOUT_SECS="$MAX_TIMEOUT_SECS"
    fi
  fi
  if ! [[ "$HARD_TIMEOUT_SECS" =~ ^[1-9][0-9]*$ ]]; then
    echo "error: suite timeout must be a positive integer (got '$HARD_TIMEOUT_SECS')" >&2
    exit 2
  fi
  if (( ${#HARD_TIMEOUT_SECS} > 4 )) \
    || { (( ${#HARD_TIMEOUT_SECS} == 4 )) && [[ "$HARD_TIMEOUT_SECS" > "$MAX_TIMEOUT_SECS" ]]; }; then
    echo "error: suite timeout must not exceed $MAX_TIMEOUT_SECS seconds (got '$HARD_TIMEOUT_SECS')" >&2
    exit 2
  fi
  exec python3 "$HARD_SUPERVISOR_SCRIPT" \
    --timeout-secs "$HARD_TIMEOUT_SECS" \
    --repo "$REPO" \
    -- bash "$0" "${ORIGINAL_ARGS[@]}"
fi

# Physical skill-root resolution and caller-controlled repository validation are
# worker setup. Keep both beneath the already-authenticated hard supervisor.
SKILL_DIR="$(cd "$BOOTSTRAP_SCRIPTS_DIR/.." && pwd -P)"
CLASSIFIER_SCRIPT="${TEST_HARNESS_CLASSIFIER:-$SKILL_DIR/scripts/classify-side-effects.py}"
if [[ -z "$REPO" || ! -d "$REPO" ]]; then
  echo "error: --repo required and must be a directory" >&2
  exit 2
fi

resolve_scope

TS="$(date -u +%Y%m%dT%H%M%SZ)"
RAND="$(openssl rand -hex 3 2>/dev/null || python3 -c 'import secrets;print(secrets.token_hex(3))')"
# Run root: $TEST_HARNESS_RUN_ROOT, else the user's state directory (outside every repository under test).
# The nesting is deliberate: $HOME is expanded only when neither override is set. The hard supervisor computes the same default.
RUN_DIR="${TEST_HARNESS_INTERNAL_RUN_DIR:-${TEST_HARNESS_RUN_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/test-harness/runs}/${SLUG}/${TS}-${RAND}}"
mkdir -p "$RUN_DIR"
# Persist scope once for all rounds / operators / agent re-invokes
printf '%s\n' "$SCOPE_JSON" >"$RUN_DIR/scope.json"

discover_cmd
if [[ -z "$TIMEOUT_SECS" ]]; then
  if [[ "$PROFILE" == "full" ]]; then
    TIMEOUT_SECS="${TEST_HARNESS_FULL_TIMEOUT:-3600}"
  else
    TIMEOUT_SECS=1200
  fi
fi
if ! [[ "$TIMEOUT_SECS" =~ ^[1-9][0-9]*$ ]]; then
  echo "error: suite timeout must be a positive integer (got '$TIMEOUT_SECS')" >&2
  exit 2
fi
if (( ${#TIMEOUT_SECS} > 4 )) \
  || { (( ${#TIMEOUT_SECS} == 4 )) && [[ "$TIMEOUT_SECS" > "$MAX_TIMEOUT_SECS" ]]; }; then
  echo "error: suite timeout must not exceed $MAX_TIMEOUT_SECS seconds (got '$TIMEOUT_SECS')" >&2
  exit 2
fi

init_run

banner "discover · $CMD ($PROFILE scope=$SUITE_SCOPE habitat=$HABITAT)"

USED_WORKTREE=0
SUITE_CWD="$WORK_ROOT"
RESTORE_POLICY="preserve-shared"

if [[ "$MODE" == "fix-loop" ]]; then
  if [[ -z "$GIT_ROOT" ]]; then
    banner "fix-loop · no git root; running in WORK_ROOT (no worktree)"
  else
    banner "worktree · enter"
    ENTER_JSON="$(bash "$SKILL_DIR/scripts/worktree-fixloop.sh" enter \
      --repo "$WORK_ROOT" --run-dir "$RUN_DIR")"
    SUITE_CWD="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['suite_cwd'])" "$ENTER_JSON")"
    PORC_REPO="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['workspace'])" "$ENTER_JSON")"
    USED_WORKTREE=1
    RESTORE_POLICY="revert-disposable"
    banner "worktree · suite_cwd=$SUITE_CWD audit_root=$PORC_REPO"
  fi
fi

HARNESS_STARTED_EPOCH="$(harness_now_epoch)"
SUITE_DEADLINE_MS="${TEST_HARNESS_SUITE_DEADLINE_EPOCH_MS:-}"
if ! [[ "$SUITE_DEADLINE_MS" =~ ^[1-9][0-9]*$ && ${#SUITE_DEADLINE_MS} -le 16 ]]; then
  echo "error: hard supervisor did not provide a valid suite deadline" >&2
  exit 2
fi
FINALIZATION_RESERVE_SECS=$((TIMEOUT_SECS / 20))
(( FINALIZATION_RESERVE_SECS < 1 )) && FINALIZATION_RESERVE_SECS=1
(( FINALIZATION_RESERVE_SECS > 60 )) && FINALIZATION_RESERVE_SECS=60
REQUESTED_SUITE_DEADLINE_EPOCH=$((HARNESS_STARTED_EPOCH + TIMEOUT_SECS - FINALIZATION_RESERVE_SECS))
SUPERVISOR_SUITE_DEADLINE_EPOCH=$((SUITE_DEADLINE_MS / 1000))
if (( REQUESTED_SUITE_DEADLINE_EPOCH < SUPERVISOR_SUITE_DEADLINE_EPOCH )); then
  HARNESS_DEADLINE_EPOCH="$REQUESTED_SUITE_DEADLINE_EPOCH"
else
  HARNESS_DEADLINE_EPOCH="$SUPERVISOR_SUITE_DEADLINE_EPOCH"
fi
banner "deadline · total=${TIMEOUT_SECS}s finalize_reserve=${FINALIZATION_RESERVE_SECS}s epoch=$HARNESS_DEADLINE_EPOCH"

N=1
while [[ $N -le $ROUNDS_MAX ]]; do
  NOW_EPOCH="$(harness_now_epoch)"
  ROUND_TIMEOUT_SECS=$((HARNESS_DEADLINE_EPOCH - NOW_EPOCH))
  if [[ $ROUND_TIMEOUT_SECS -le 0 ]]; then
    stop_timeout_budget "$N" "$NOW_EPOCH"
  fi
  one_round "$N"
  if [[ $ROUND_PASS -eq 1 ]]; then
    banner "round $N · would pass → emit"
    emit_and_exit "$USED_WORKTREE"
  fi
  # Fail path: shared working trees are evidence-only and preserve every post
  # state; only a harness-owned disposable worktree may be reverted.
  banner "round $N · reconcile policy=$RESTORE_POLICY (suite exit=$SUITE_EC)"
  porcelain "$N" restore "$RESTORE_POLICY"
  PRESERVED_POST_STATE="$(python3 -c "
import json
from pathlib import Path
r=json.loads(Path('$RUN_DIR/round-$N/restore.json').read_text())
print(int(r.get('preserved_post_state_count', r.get('preserved_dirty_pre_count', 0)) or 0))
")"
  if [[ "$PRESERVED_POST_STATE" -gt 0 ]]; then
    banner "round $N · preserved $PRESERVED_POST_STATE post-state path(s); manual reconciliation required → emit FAIL"
    emit_and_exit "$USED_WORKTREE"
  fi
  if [[ $N -ge $ROUNDS_MAX ]]; then
    banner "round $N · budget exhausted → emit FAIL"
    emit_and_exit "$USED_WORKTREE"
  fi
  banner "round $N · fail; continuing (product fixes are agent-owned — re-invoke after edits)"
  N=$((N + 1))
done

# unreachable safety
emit_and_exit "$USED_WORKTREE"
