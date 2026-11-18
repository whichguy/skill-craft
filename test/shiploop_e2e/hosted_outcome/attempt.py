"""Replay-safe operator entry point. All callbacks run while the target leases are held."""
import fcntl
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import lifecycle
from checks.sf_guard import write_once
from hosted_outcome import binding as b

ATTEMPT_ENV = "HOSTED_OUTCOME_ATTEMPT"


def read(path):
    return b.decoded(path.read_bytes())


def lease_keys(data):
    target = data["target"]
    return sorted({key for selector in (target["org_id"], target["selector"], target["username"])
                   for prefix in (data["namespace"], *data["legacy_prefixes"])
                   for key in lifecycle.lease_keys({"kind": "salesforce", "org": selector, "prefix": prefix})})


def registry(data):
    return lifecycle.leases_dir().resolve() / "hosted-outcome" / data["target"]["org_id"]


def verified(receipt, context, phase):
    return (isinstance(receipt, dict) and receipt.get("verified") is True
            and receipt.get("binding_sha256") == context["binding_sha256"]
            and receipt.get("target") == context["target"] and receipt.get("phase") == phase)


def process_identity(pid, row=None):
    row = lifecycle.table([pid]).get(pid) if row is None else row
    b.require(row is not None, "cannot verify hosted process identity")
    return {key: row[key] for key in ("pid", "pgid", "started")}


def assert_leased(state, record):
    operator = record["operator"]
    b.require(lifecycle.same_leader(operator, lifecycle.table([operator["pid"]]).get(operator["pid"])),
              "hosted build phase operator identity changed")
    for key in record["lease_keys"]:
        path = state.parents[2] / lifecycle._file(key)
        with path.open("rb") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
            except BlockingIOError:
                pass
            else:
                raise ValueError("hosted build phase requires the operator's held leases")
            holder = b.decoded(lock.read())
            b.require(lifecycle._same_file(lock.fileno(), path) and holder.get("operator") == operator
                      and holder.get("pid") == record["pid"] == operator["pid"] and holder.get("case") == b.CASE,
                      "hosted build phase lease identity changed")


def assert_open(state):
    record = read(state / "start.json")
    b.require(not (state / "build-closed.json").exists() and time.time() < record["build_until"],
              "the hosted build phase is closed or expired")
    assert_leased(state, record)
    launch = read(state / "launch.json")
    pid = launch["pid"]
    runner = lifecycle.table([pid]).get(pid)
    b.require(lifecycle.same_leader(launch["runner"], runner) and runner["ppid"] == record["pid"],
              "the hosted build phase has no active operator-owned runner")
    return record


def phase_receipt(state):
    return {"phase": "build-closed", "start_sha256": b.sha((state / "start.json").read_bytes())}


def close_build(state):
    with b.build_lock(state, close=True):
        path = state / "build-closed.json"
        if not path.exists():
            write_once(path, phase_receipt(state))
        b.require(read(path) == phase_receipt(state), "hosted build closure does not match the attempt")


def authorize(path, argv, args):
    """Called by run.py before creating output or setting up a host."""
    data, digest, _ = b.load(path)
    state = b.absolute(os.environ.get(ATTEMPT_ENV))
    b.require(state.parent == registry(data), "invalid hosted attempt state path")
    record = read(state / "start.json")
    b.require(record["pid"] == os.getppid() and record["binding_sha256"] == digest
              and record["argv"] == argv and args.case == b.CASE and args.output == Path(data["product_cwd"]).parent,
              "environment binding does not authorize this invocation")
    b.require(record["lease_keys"] == lease_keys(data) and not (state / "build-closed.json").exists(),
              "hosted launch requires the operator's canonical and legacy leases")
    assert_leased(state, record)
    reset = read(state / "reset.json")
    b.require(verified(reset, record, "reset") and reset.get("empty_noop") is True
              and b.recent(reset.get("checked_at"), 300, time.time()) and time.time() < record["build_until"],
              "hosted launch requires a fresh verified leased no-op reset")
    write_once(state / "launch.json", {"pid": os.getpid(), "runner": process_identity(os.getpid()),
                                       "reset_sha256": b.sha(b.encoded(reset))})
    return data, digest, state


def submitted(state):
    return {path.stem for path in state.glob("*.submitted")}


def settlement(state):
    paths = [*sorted(state.glob("reconciled-*.json"), reverse=True), state / "reconciled.json", state / "settled.json"]
    for path in paths:
        if path.exists():
            return read(path)
    return {"state": "RECONCILIATION_REQUIRED", "state_dir": str(state), "product_acceptance": "UNKNOWN"}


def submission_evidence(state):
    return {path.name: b.sha(path.read_bytes()) for pattern in ("*.submitted", "*.returned")
            for path in sorted(state.glob(pattern))}


def cleanup_verified(receipt, context, state):
    intents = receipt.get("reconciled_intents") if isinstance(receipt, dict) else None
    return (verified(receipt, context, "cleanup") and isinstance(intents, list)
            and len(intents) == len(set(intents)) and set(intents) == submitted(state)
            and {path.stem for path in state.glob("*.returned")} <= set(intents))


def reusable(state, result=None):
    try:
        record = read(state / "start.json")
        result = settlement(state) if result is None else result
        receipt = result["cleanup"]
        return (read(state / "build-closed.json") == phase_receipt(state)
                and result["state"] == "SETTLED" and cleanup_verified(receipt, record, state)
                and result["local_processes_clear"] is True
                and result["submission_evidence"] == submission_evidence(state)
                and b.sha(b.encoded(receipt)) == result["cleanup_sha256"])
    except (OSError, ValueError, KeyError, TypeError):
        return False


def local_clear(state, out):
    launching = os.path.lexists(out) or any(os.path.lexists(state / name)
                                           for name in ("launching.json", "launch.json", "runner.log"))
    if launching:
        try:
            records = lifecycle.rows(state, strict=True)
        except (OSError, ValueError):
            return False
        if records[0]["kind"] != "startup-protocol" or not lifecycle.startups_clear(state):
            return False
    # Never use lifecycle.cleanup to close a leaderless runner group as unverified.
    # It stays open for explicit re-observation. Only the existing identity-safe stop
    # path may signal a surviving leader after interruption.
    for group in lifecycle.open_groups(state):
        how, detail = lifecycle.stop(group, verify_absence=True)
        if how not in {"gone", "stopped", "reused"}:
            return False
        lifecycle.ended(state, group, how, **detail)
    # The runner has stopped. It can no longer be between spawning and
    # registering a child, but its blocked startup shim may still be alive.
    if launching:
        if not lifecycle.startups_clear(state):
            return False
        try:
            records = lifecycle.rows(state, strict=True)
            hosts = {row["id"] for row in records if row.get("role") == "host" and row["kind"] == "group"}
            if hosts and not hosts <= {row["id"] for row in lifecycle.rows(out, strict=True)
                                       if row["kind"] == "group" and row.get("role") == "host"}:
                return False
        except (OSError, ValueError, KeyError):
            return False
    if out.is_dir() and not lifecycle.cleanup(out, verify_absence=True)["observed"]:
        return False
    now = lifecycle.table()
    for folder in (state, out):
        for group in lifecycle.rows(folder):
            if group.get("kind") != "group":
                continue
            pgid = group["pgid"]
            current = now.get(pgid)
            if (current and current["pgid"] == pgid and group.get("leader")
                    and not lifecycle.same_leader(group["leader"], current)):
                continue  # the current leader is a different process; the recorded group is gone
            if any(row["pgid"] == pgid for row in now.values()) or not lifecycle.group_absent(pgid):
                return False
    return True


def seal(result, receipt, state):
    result.update(state="SETTLED", local_processes_clear=True, cleanup=receipt,
                  cleanup_sha256=b.sha(b.encoded(receipt)), submission_evidence=submission_evidence(state))


def within(cutoff, callback, context):
    """Interrupt a synchronous operator phase at its cutoff in the main thread."""
    remaining = cutoff - time.time()
    if remaining <= 0:
        raise TimeoutError("hosted phase deadline expired")
    b.require(not signal.getitimer(signal.ITIMER_REAL)[0], "hosted phase needs an unused SIGALRM timer")

    def expired(signum, frame):
        raise TimeoutError("hosted phase deadline expired")

    handler = signal.signal(signal.SIGALRM, expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, remaining)
        return callback(context, cutoff)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, handler)


def builder(argv, env, log, cutoff, state):
    process, _ = lifecycle.spawn_registered(
        state, "hosted-runner", [sys.executable, "-B", str(b.HERE / "run.py"), *argv],
        cwd=b.HERE, env=env, stdout=log, stderr=subprocess.STDOUT)
    with process:
        try:
            while lifecycle.listeners.unreaped(process.pid) == "running":
                remaining = cutoff - time.time()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(process.args, 0)
                time.sleep(min(0.05, remaining))
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            if lifecycle.listeners.unreaped(process.pid) == "running":
                process.terminate()
                grace = time.monotonic() + 3
                while lifecycle.listeners.unreaped(process.pid) == "running" and time.monotonic() < grace:
                    time.sleep(0.05)
            raise
        finally:
            # The unreaped child pins the original PGID even if its PID has exited.
            lifecycle.listeners.end_group(process.pid)
            process.wait()
        return process.returncode


def execute(binding_path, *, campaign, build, codex_bin, model, baseline, deadline,
            observation_seconds, teardown_seconds, reset, observe, cleanup):
    """Execute one attempt. Callbacks take (context, absolute Unix cutoff).

    Reset verifies the canonical target/user and clean no-op. Observe returns external
    evidence while the deployment is live. Cleanup attests quiescence and reconciles
    every '*.submitted' intent, including those with no remote ID. Cleanup receives
    local_processes_clear from the local teardown check. Callbacks must bound
    any subprocess they start by the phase cutoff. Invoke this entry point in the main
    thread of the attended probe process. A stopped process leaves its attempt pending for operator reconciliation.
    """
    data, digest, receipts = b.load(binding_path, fresh=False)
    target = data["target"]
    identity_root = registry(data)
    b.require(isinstance(campaign, str) and campaign and b.match(r"[0-9a-f]{40}", build),
              "campaign ID and expected marketplace origin/main SHA required")
    state = identity_root / b.sha(b.encoded([campaign, build, digest]))
    operator = process_identity(os.getpid())
    keys = lease_keys(data)
    lease = lifecycle.take(keys, {"pid": os.getpid(), "case": b.CASE, "operator": operator})
    try:
        if state.exists():
            try:
                previous = settlement(state)
                if previous["state"] == "SETTLED" and not reusable(state, previous):
                    return {"state": "RECONCILIATION_REQUIRED", "state_dir": str(state), "product_acceptance": "UNKNOWN"}
                return previous
            except (OSError, ValueError, KeyError, TypeError):
                return {"state": "RECONCILIATION_REQUIRED", "state_dir": str(state), "product_acceptance": "UNKNOWN"}
        b.require(all(reusable(prior) for prior in identity_root.glob("*/")), "prior hosted attempt needs verified cleanup")
        b.require(all(b.recent(stamp, age, time.time()) for stamp, age in receipts.values()), "binding receipts expired")
        out = Path(data["product_cwd"]).parent
        baseline = b.absolute(baseline)
        codex_bin = b.absolute(codex_bin)
        b.require(codex_bin.is_file() and os.access(codex_bin, os.X_OK)
                  and b.match(r"gpt-[0-9.]+-sol", model), "supply the resolved latest SOL ID and executable Codex CLI")
        b.require(not out.exists() and not out.is_symlink() and out not in baseline.parents
                  and b.HERE.parents[1] not in baseline.parents, "fresh output and external campaign baseline required")
        now = time.time()
        build_until = deadline - observation_seconds - teardown_seconds
        observe_until = deadline - teardown_seconds
        b.require(now < build_until < observe_until < deadline <= now + 28800,
                  "deadline must fit the remaining eight hours with observation and teardown reserves")
        argv = ["--case", b.CASE, "--environment-binding", str(binding_path), "--host", "codex",
                "--codex-bin", str(codex_bin), "--model", model, "--effort", "medium", "--source", "marketplace",
                "--output", str(out), "--baseline", str(baseline)]
        context = {"campaign": campaign, "build": build, "binding_sha256": digest, "target": target,
                   "pid": os.getpid(), "argv": argv, "state_dir": str(state), "output": str(out),
                   "namespace": data["namespace"], "legacy_prefixes": data["legacy_prefixes"],
                   "operator": operator, "lease_keys": keys, "build_until": build_until, "deadline": deadline}
        state.mkdir(mode=0o700, parents=True)
        write_once(state / "start.json", context)
        result = {"state": "RECONCILIATION_REQUIRED", "state_dir": str(state), "product_acceptance": "UNKNOWN",
                  "runner_exit": None, "observations": None, "local_processes_clear": False}
        try:
            receipt = within(build_until, reset, context)
            b.require(verified(receipt, context, "reset") and receipt.get("empty_noop") is True
                      and b.recent(receipt.get("checked_at"), 300, time.time()), "leased reset was not independently verified")
            write_once(state / "reset.json", receipt)
            env = {key: value for key, value in os.environ.items() if key in b.ENV_KEYS
                   or key == lifecycle.LEASES_ENV}
            env.update({ATTEMPT_ENV: str(state), "PATH": os.pathsep.join(
                [*data["tool_dirs"], *b.SYSTEM_DIRS])})
            remaining = build_until - time.time()
            b.require(remaining > 0, "builder deadline expired before launch")
            lifecycle.initialize_startup(state)
            write_once(state / "launching.json", {"phase": "launching"})
            with (state / "runner.log").open("xb") as log:
                result["runner_exit"] = builder(argv, env, log, build_until, state)
        except (Exception, KeyboardInterrupt) as exc:
            result["build_error"] = type(exc).__name__
        finally:
            try:
                result["local_processes_clear"] = local_clear(state, out)
                close_build(state)
                if observe is not None and time.time() < observe_until and result["local_processes_clear"] and out.is_dir():
                    result["observations"] = within(observe_until, observe, context)
            except (Exception, KeyboardInterrupt) as exc:
                result["observation_error"] = type(exc).__name__
            finally:
                try:
                    processes_clear = result["local_processes_clear"]
                    close_build(state)
                    if processes_clear:
                        receipt = within(deadline, cleanup, {**context, "local_processes_clear": True})
                        if ((state / "reset.json").is_file() and cleanup_verified(receipt, context, state)
                                and b.recent(receipt.get("checked_at"), 300, time.time())):
                            seal(result, receipt, state)
                except (Exception, KeyboardInterrupt) as exc:
                    result["cleanup_error"] = type(exc).__name__
                write_once(state / "settled.json", result)
        return result
    finally:
        lease.close()


def reconcile(binding_path, state, *, deadline, cleanup):
    """Reacquire the target leases for cleanup only, using the supplied cleanup cutoff."""
    data, digest, _ = b.load(binding_path, fresh=False)
    state = b.absolute(state)
    b.require(state.parent == registry(data), "invalid hosted reconciliation state path")
    lease = lifecycle.take(lease_keys(data), {"pid": os.getpid(), "case": b.CASE})
    try:
        context = read(state / "start.json")
        b.require(context["binding_sha256"] == digest and context["target"] == data["target"],
                  "reconciliation requires the original binding")
        result = settlement(state)
        if reusable(state):
            return result
        def recover(context, cutoff):
            processes_clear = local_clear(state, Path(context["output"]))
            close_build(state)
            b.require(processes_clear, "attempt process cleanup remains unverified")
            reset_missing = not (state / "reset.json").is_file()
            prelaunch_noop = reset_missing and b.no_launch_without_reset(context)
            b.require(not reset_missing or prelaunch_noop, "missing reset proof after possible launch or baseline freeze")
            receipt = cleanup({**context, "local_processes_clear": True, "reconcile_prelaunch_noop": prelaunch_noop},
                              cutoff)
            b.require(not prelaunch_noop or (isinstance(receipt, dict) and receipt.get("empty_noop") is True
                                           and receipt.get("prelaunch_noop") is True),
                      "operator cleanup has not verified a prelaunch no-op")
            return receipt

        receipt = within(deadline, recover, context)
        b.require(cleanup_verified(receipt, context, state) and b.recent(receipt.get("checked_at"), 300, time.time()),
                  "operator cleanup has not reconciled every submitted deployment")
        seal(result, receipt, state)
        path = state / "reconciled.json"
        if path.exists():
            path = state / f"reconciled-{len(list(state.glob('reconciled-*.json'))) + 1:08d}.json"
        write_once(path, result)
        return result
    finally:
        lease.close()
