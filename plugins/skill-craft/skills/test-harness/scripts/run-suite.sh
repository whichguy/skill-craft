#!/usr/bin/env bash
# run-suite.sh — run a test command with pinned TMPDIR and portable process-group timeout.
#
# Usage: run-suite.sh --repo <path> --cmd <cmd> --out <run-dir> [--timeout-secs N]
# Exit = suite exit code, or 124 on timeout.
set -euo pipefail
umask 077

REPO=""
CMD=""
OUT=""
TIMEOUT_SECS="${TEST_HARNESS_TIMEOUT:-}"
MAX_TIMEOUT_SECS=3600

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO="${2:-}"; shift 2 ;;
    --cmd) CMD="${2:-}"; shift 2 ;;
    --out) OUT="${2:-}"; shift 2 ;;
    --timeout-secs) TIMEOUT_SECS="${2:-}"; shift 2 ;;
    -h|--help)
      echo "Usage: $0 --repo <path> --cmd <cmd> --out <dir> [--timeout-secs N (max 3600)]" >&2
      exit 0
      ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$REPO" || -z "$CMD" || -z "$OUT" ]]; then
  echo "usage: --repo --cmd --out required" >&2
  exit 1
fi
if [[ ! -d "$REPO" ]]; then
  echo "repo not a directory: $REPO" >&2
  exit 1
fi

# Default timeout: 20m if unset; no direct invocation may exceed one hour.
if [[ -z "$TIMEOUT_SECS" ]]; then
  TIMEOUT_SECS=1200
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

REPO="$(cd "$REPO" && pwd -P)"
mkdir -p "$OUT" "$OUT/tmp"
chmod 700 "$OUT" "$OUT/tmp"
OUT="$(cd "$OUT" && pwd -P)"
TMPDIR_PIN="$OUT/tmp"
STDOUT_LOG="$OUT/stdout.log"
STDERR_LOG="$OUT/stderr.log"
META="$OUT/meta.json"

# Portable process-group supervisor (no coreutils timeout/gtimeout required).
# Starts the suite in its own session/process group; on expiry TERM then KILL the group.
export REPO CMD STDOUT_LOG STDERR_LOG META TMPDIR_PIN TIMEOUT_SECS
EXIT_CODE="$(
python3 - <<'PY'
from datetime import datetime, timezone
import errno
import json
import os
import re
import signal
import subprocess
import sys
import time

repo = os.environ["REPO"]
cmd = os.environ["CMD"]
stdout_log = os.environ["STDOUT_LOG"]
stderr_log = os.environ["STDERR_LOG"]
meta_path = os.environ["META"]
tmpdir = os.environ["TMPDIR_PIN"]
timeout = float(os.environ["TIMEOUT_SECS"])

env = os.environ.copy()
env["TMPDIR"] = tmpdir
env["TEMP"] = tmpdir
env["TMP"] = tmpdir
# Do not override HOME.

supervisor_started = time.monotonic()
started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
# The advertised timeout covers artifact creation, supervision, and teardown.
outer_margin = min(0.25, max(0.05, timeout / 10))
hard_deadline = supervisor_started + max(0.1, timeout - outer_margin)
cleanup_reserve = min(
    7.0,
    max(0.2, (hard_deadline - supervisor_started) / 4),
)
execution_deadline = hard_deadline - cleanup_reserve

def open_exclusive_private(path):
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    return os.open(path, flags, 0o600)

opened = []
try:
    for path in (stdout_log, stderr_log, meta_path):
        try:
            opened.append((path, open_exclusive_private(path)))
        except OSError as exc:
            name = os.path.basename(path)
            if exc.errno in (errno.EEXIST, errno.ELOOP):
                detail = (
                    "refusing to overwrite pre-existing run artifact: "
                    f"{name}"
                )
            else:
                detail = f"unable to create run artifact {name}: {exc}"
            print(f"error: {detail}", file=sys.stderr)
            for _opened_path, opened_fd in opened:
                os.close(opened_fd)
            print(2)
            raise SystemExit(0)
except BaseException:
    for _opened_path, opened_fd in opened:
        try:
            os.close(opened_fd)
        except OSError:
            pass
    raise

stdout_f = os.fdopen(opened[0][1], "w+b", buffering=0)
stderr_f = os.fdopen(opened[1][1], "w+b", buffering=0)
meta_f = os.fdopen(opened[2][1], "w+b", buffering=0)

# Start in a new session so the whole group can be killed.
try:
    proc = subprocess.Popen(
        ["bash", "-lc", cmd],
        cwd=repo,
        env=env,
        stdout=stdout_f,
        stderr=stderr_f,
        start_new_session=True,  # setsid
    )
except Exception as e:
    stderr_f.write(f"spawn failed: {e}\n".encode())
    exit_code = 127
else:
    pgid = proc.pid
    timed_out = False
    leader_rc = None
    forwarded_signal = None

    def group_alive():
        # Reap the shell leader when possible, then probe the process group. The
        # group can outlive its leader when a background descendant is alive.
        proc.poll()
        try:
            os.killpg(pgid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True

    def signal_group(sig):
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            pass
        except PermissionError:
            # The owned group can disappear between the liveness probe and
            # signal, after which its numeric PGID may refer to another group.
            pass

    def receive_signal(sig, _frame):
        global forwarded_signal
        if forwarded_signal is None:
            forwarded_signal = sig
            signal_group(sig)

    for handled_signal in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(handled_signal, receive_signal)

    def cleanup_group(stop_by):
        if not group_alive():
            return
        signal_group(signal.SIGTERM)
        remaining = max(0.0, stop_by - time.monotonic())
        kill_margin = min(0.25, max(0.05, remaining / 4))
        grace_deadline = min(time.monotonic() + 5, stop_by - kill_margin)
        while time.monotonic() < grace_deadline:
            if not group_alive():
                return
            time.sleep(
                min(0.05, max(0.0, grace_deadline - time.monotonic()))
            )
        if group_alive():
            signal_group(signal.SIGKILL)
            while time.monotonic() < stop_by and group_alive():
                time.sleep(
                    min(0.025, max(0.0, stop_by - time.monotonic()))
                )

    def cleanup_after_forwarded_signal(stop_by):
        # The suite may itself be a supervisor whose children live in another
        # process group. Give its handler time to forward before escalating.
        if not group_alive():
            return
        remaining = max(0.0, stop_by - time.monotonic())
        kill_margin = min(0.25, max(0.05, remaining / 5))
        cooperative_deadline = min(
            time.monotonic() + 1.25,
            stop_by - kill_margin,
        )
        while time.monotonic() < cooperative_deadline:
            if not group_alive():
                return
            time.sleep(
                min(
                    0.05,
                    max(0.0, cooperative_deadline - time.monotonic()),
                )
            )
        if group_alive():
            signal_group(signal.SIGTERM)
        term_deadline = min(
            time.monotonic() + 0.35,
            stop_by - kill_margin,
        )
        while time.monotonic() < term_deadline:
            if not group_alive():
                return
            time.sleep(
                min(0.05, max(0.0, term_deadline - time.monotonic()))
            )
        if group_alive():
            signal_group(signal.SIGKILL)
            while time.monotonic() < stop_by and group_alive():
                time.sleep(
                    min(0.025, max(0.0, stop_by - time.monotonic()))
                )

    try:
        while True:
            rc = proc.poll()
            if forwarded_signal is not None:
                leader_rc = rc
                break
            if rc is not None:
                leader_rc = rc
                break
            if time.monotonic() >= execution_deadline:
                # Close the race where the leader exits at the deadline.
                rc = proc.poll()
                if rc is not None:
                    leader_rc = rc
                    break
                timed_out = True
                cleanup_group(hard_deadline)
                leader_rc = proc.poll()
                if leader_rc is None:
                    signal_group(signal.SIGKILL)
                    try:
                        leader_rc = proc.wait(
                            timeout=max(
                                0.0, hard_deadline - time.monotonic()
                            )
                        )
                    except subprocess.TimeoutExpired:
                        leader_rc = proc.returncode
                break
            time.sleep(0.05)
    finally:
        # A shell may exit normally while leaving background descendants in its
        # session. Sweep the isolated group without touching this supervisor.
        if forwarded_signal is not None:
            cleanup_after_forwarded_signal(
                min(hard_deadline, time.monotonic() + 2.0)
            )
            leader_rc = proc.poll()
        elif not timed_out:
            cleanup_group(hard_deadline)

    if timed_out:
        exit_code = 124
    elif forwarded_signal is not None:
        exit_code = 128 + forwarded_signal
    elif leader_rc is not None and leader_rc < 0:
        exit_code = 128 + (-leader_rc)
    else:
        exit_code = leader_rc if leader_rc is not None else 1

def tail_lines(stream, count=200, limit=262144):
    fd = stream.fileno()
    size = os.fstat(fd).st_size
    start = max(0, size - limit)
    os.lseek(fd, start, os.SEEK_SET)
    data = os.read(fd, min(limit, size - start))
    return data.decode("utf-8", errors="replace").splitlines()[-count:]

passing_signal_prefix = re.compile(r"^\s*(?:PASS\b|ok\b|[✓✔])", re.IGNORECASE)
primary_failure_signal = re.compile(
    r"(?:\bError:|\bERROR\b|\bAssertionError\b|\bTraceback\b|\bpanic:|\bFATAL\b)",
    re.IGNORECASE,
)
named_failure_signal = re.compile(
    r"^\s*(?:FAIL\b|not ok\b|[×✗✕])",
    re.IGNORECASE,
)
secondary_failure_signal = re.compile(
    r"\b(?:failed|failure|timeout|timed out)\b",
    re.IGNORECASE,
)

def failure_signal_rank(line):
    if not line.strip() or passing_signal_prefix.match(line):
        return None
    if primary_failure_signal.search(line):
        return 0
    if named_failure_signal.match(line):
        return 1
    if secondary_failure_signal.search(line):
        return 2
    return None

def select_failure_signature(streams):
    candidates = []
    for source_order, lines in enumerate(streams):
        for line_order, line in enumerate(lines):
            rank = failure_signal_rank(line)
            if rank is not None:
                candidates.append((rank, source_order, line_order, line))
    if not candidates:
        return ""
    return min(candidates)[3].replace("\r", "")[:200]

if exit_code == 124:
    error_sig = "timeout"
elif exit_code != 0:
    error_sig = select_failure_signature(
        (tail_lines(stderr_f), tail_lines(stdout_f))
    )
    if not error_sig:
        error_sig = f"exit_{exit_code}"
else:
    error_sig = "none"

duration_ms = int((time.monotonic() - supervisor_started) * 1000)
meta = {
    "exit": int(exit_code),
    "duration_ms": duration_ms,
    "started_at": started_at,
    "tmpdir": tmpdir,
    "timeout_secs": int(timeout),
    "cmd": cmd,
    "repo": repo,
    "error_sig": error_sig,
}
try:
    meta_f.write((json.dumps(meta, indent=2) + "\n").encode("utf-8"))
    meta_f.flush()
    os.fsync(meta_f.fileno())
except OSError as exc:
    print(f"error: unable to write retained meta.json descriptor: {exc}", file=sys.stderr)
    exit_code = 125
finally:
    stdout_f.close()
    stderr_f.close()
    meta_f.close()

print(exit_code)
PY
)"

if ! [[ "$EXIT_CODE" =~ ^[0-9]+$ ]]; then
  echo "error: suite supervisor returned an invalid exit code" >&2
  exit 125
fi

exit "$EXIT_CODE"
