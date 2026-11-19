"""Replay-safe operator entry point. All callbacks run while the target leases are held."""
import fcntl
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import lifecycle
from checks.sf_guard import force_app_sha256, write_once
from hosted_outcome import binding as b

ATTEMPT_ENV = "HOSTED_OUTCOME_ATTEMPT"
MAX_CAMPAIGN_SECONDS = 24 * 60 * 60


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
              and reset_retained(reset, record)
              and b.recent(reset.get("checked_at"), 300, time.time()) and time.time() < record["build_until"],
              "hosted launch requires a fresh verified leased no-op reset")
    write_once(state / "launch.json", {"pid": os.getpid(), "runner": process_identity(os.getpid()),
                                       "reset_sha256": b.sha(b.encoded(reset))})
    return data, digest, state


def submitted(state):
    return {path.stem for path in state.glob("*.submitted")}


def settlement(state):
    start = state / "start.json"
    record = read(start) if start.exists() else {}
    if record.get("review_hold") is True:
        paths = [state / "retired.json", state / "retained.json", state / "settled.json"]
        pending = "RETENTION_PENDING"
    else:
        paths = [*sorted(state.glob("reconciled-*.json"), reverse=True), state / "reconciled.json", state / "settled.json"]
        pending = "RECONCILIATION_REQUIRED"
    for path in paths:
        if path.exists():
            return read(path)
    return {"state": pending, "state_dir": str(state), "product_acceptance": "UNKNOWN"}


def submission_evidence(state):
    return {path.name: b.sha(path.read_bytes()) for pattern in ("*.submitted", "*.returned")
            for path in sorted(state.glob(pattern))}


def deployment_evidence(state):
    return {path.name: b.sha(path.read_bytes()) for key in sorted(submitted(state))
            for suffix in (".intent", ".approved", ".reconciled")
            if (path := state / f"{key}{suffix}").is_file()}


def pinned_reference(ref):
    path = b.absolute(ref["path"])
    b.require(path.is_file() and b.sha(path.read_bytes()) == ref["sha256"], "retention proof artifact differs")
    return path


def cleanup_verified(receipt, context, state, *, phase="cleanup"):
    intents = receipt.get("reconciled_intents") if isinstance(receipt, dict) else None
    return (verified(receipt, context, phase) and isinstance(intents, list)
            and len(intents) == len(set(intents)) and set(intents) == submitted(state)
            and {path.stem for path in state.glob("*.returned")} <= set(intents))


def reusable(state, result=None):
    try:
        record = read(state / "start.json")
        result = settlement(state) if result is None else result
        receipt = result["cleanup"]
        held = record.get("review_hold") is True
        if held:
            authority = read(state / "retirement-started.json")
            if (result != read(state / "retired.json") or not retained(state)
                    or receipt.get("retirement") != authority or authority.get("generation_id") != state.name
                    or authority.get("retention_sha256") != read(state / "retained.json")["retention_sha256"]
                    or not all(b.match(b.DIGEST, authority.get(key)) for key in ("plan_sha256", "approval_sha256"))):
                return False
        return (read(state / "build-closed.json") == phase_receipt(state)
                and result["state"] == "SETTLED"
                and cleanup_verified(receipt, record, state, phase="retire" if held else "cleanup")
                and result["local_processes_clear"] is True
                and result["submission_evidence"] == submission_evidence(state)
                and b.sha(b.encoded(receipt)) == result["cleanup_sha256"])
    except (OSError, ValueError, KeyError, TypeError):
        return False


def retention_verified(receipt, context, state):
    if not (context.get("review_hold") is True and verified(receipt, context, "retain")
            and receipt.get("generation_id") == state.name and receipt.get("prefix") == context["namespace"]
            and receipt.get("synthetic_label") == context["synthetic_label"]
            and isinstance(receipt.get("deployments"), list) and isinstance(receipt.get("inventory"), dict)
            and isinstance(receipt.get("preserved"), dict) and isinstance(receipt.get("app_work_clearance"), dict)
            and receipt.get("deployment_evidence") == deployment_evidence(state)
            and receipt.get("reconciled_intents") == sorted(submitted(state))
            and {path.stem for path in state.glob("*.returned")} <= submitted(state)):
        return False
    journal = b.absolute(receipt.get("evidence_path"))
    if (journal.parent != state or not journal.name.startswith("operator-retain-")
            or read(b.absolute(journal / "receipt.json")) != receipt):
        return False
    clearance = receipt["app_work_clearance"]
    request = pinned_reference(clearance["request"])
    response = pinned_reference(clearance["receipt"])
    evidence = pinned_reference(clearance["evidence"])
    if (request != journal / "app-work-request.json" or response != journal / "app-work-cleared.json"
            or evidence.is_relative_to(journal) or evidence.is_relative_to(Path(context["output"]))):
        return False
    if not clearance_verified(read(request), read(response), clearance, context, state, receipt):
        return False
    reset = receipt["reset_evidence"]
    if receipt["prelaunch_noop"] is True:
        if reset is not None or receipt["reconciled_intents"] or receipt["deployments"]:
            return False
    elif not (pinned_reference(reset["reset"]) == state / "reset.json"
              and pinned_reference(reset["baseline"]) == state / "operator-baseline.json"
              and read(state / "reset.json")["baseline_sha256"] == reset["baseline"]["sha256"]
              and verified(read(state / "reset.json"), context, "reset")):
        return False
    deployed = {}
    for link in receipt["deployments"]:
        key, remote = link["intent_sha256"], link["deployment_id"]
        if key not in submitted(state) or remote in deployed or not b.sf_id(remote, "0Af"):
            return False
        payload = b.absolute(link["payload_path"])
        intent = read(state / f"{key}.intent")
        if (payload.parent != state or not payload.name.startswith(f"{key}.payload-")
                or read(state / f"{key}.submitted").get("payload") != str(payload)
                or force_app_sha256(payload) != link["source_sha256"] or intent["force_app_sha256"] != link["source_sha256"]
                or b.sha(b.absolute(payload / "sfdx-project.json").read_bytes()) != link["project_sha256"]
                or intent["project_sha256"] != link["project_sha256"]):
            return False
        deployed[remote] = key
    inventory = receipt["inventory"]
    tags, members = inventory["component_sources"], inventory["metadata"]
    return (tags.keys() == members.keys()
            and all(tags[kind].keys() == names.keys() for kind, names in members.items())
            and all(deployed.get(link["deployment_id"]) == link["intent_sha256"]
                    for rows in tags.values() for link in rows.values()))


def clearance_verified(request, response, proof, context, state, receipt):
    return (verified(response, context, "app-work") and response["generation_id"] == state.name
            and all(request[key] == context[key] for key in ("binding_sha256", "target"))
            and request["generation_id"] == state.name and request["action"] == "retain"
            and request["inventory_sha256"] == b.sha(b.encoded(receipt["inventory"]))
            and request["inventory"] == receipt["inventory"] and request["deployments"] == receipt["deployments"]
            and response["pending"] is False
            and response["request_sha256"] == proof["request"]["sha256"]
            and response["evidence"] == proof["evidence"] and response.get("app_url") == receipt["app_url"]
            and request["checked_at"] <= response["checked_at"] <= min(request["cutoff"], receipt["checked_at"]))


def retained(state, result=None):
    """Validate the historical retention seal independently of the latest disposition."""
    try:
        state = b.absolute(state)
        record = read(state / "start.json")
        stored = read(state / "retained.json")
        if result is not None and result != stored:
            return False
        receipt = stored["retention"]
        return (record["state_dir"] == str(state) and stored["state_dir"] == str(state)
                and state.name == b.sha(b.encoded([record["campaign"], record["build"], record["binding_sha256"]]))
                and read(state / "build-closed.json") == phase_receipt(state)
                and stored["state"] == "RETAINED_QUIESCENT" and stored["local_processes_clear"] is True
                and stored["submission_evidence"] == submission_evidence(state)
                and b.sha(b.encoded(receipt)) == stored["retention_sha256"]
                and retention_verified(receipt, record, state))
    except (OSError, ValueError, KeyError, TypeError):
        return False


def prior_states(data):
    root = registry(data)
    if not root.exists():
        return []
    states = sorted(root.iterdir())
    b.require(all(not state.is_symlink() and state.is_dir() and b.match(b.DIGEST, state.name)
                  for state in states), "invalid hosted attempt registry")
    return states


def admission(data):
    """Return sealed disjoint retained peers for fresh leased validation by reset."""
    def overlaps(left, right):
        left, right = left.casefold(), right.casefold()
        return left.startswith(right) or right.startswith(left)

    peers = []
    for state in prior_states(data):
        original = read(state / "start.json")
        if data.get("review_hold") is True and original.get("review_hold") is True:
            b.require(not overlaps(data["namespace"], original["namespace"])
                      and not overlaps(" ".join(original["synthetic_label"].split()),
                                       " ".join(data["synthetic_label"].split())),
                      "fresh hosted scope overlaps a registered generation")
        if reusable(state):
            continue
        b.require(data.get("review_hold") is True and retained(state)
                  and not os.path.lexists(state / "retirement-started.json"),
                  "prior hosted attempt needs verified cleanup or quiescent retention")
        result = read(state / "retained.json")
        peer = result["retention"]
        b.require(not any(overlaps(peer["prefix"], prefix) for prefix in data["legacy_prefixes"])
                  and not any(overlaps(data["namespace"], prefix) for prefix in original["legacy_prefixes"]),
                  "fresh hosted scope overlaps a retained generation")
        peers.append({"state_dir": str(state), "retention_sha256": result["retention_sha256"]})
    return peers


def reset_retained(receipt, context):
    return receipt.get("retained_generations", []) == context.get("retained_generations", [])


def seal_retention(result, receipt, state):
    result.update(state="RETAINED_QUIESCENT", local_processes_clear=True, retention=receipt,
                  retention_sha256=b.sha(b.encoded(receipt)), submission_evidence=submission_evidence(state))
    write_once(state / "retained.json", result)


def local_clear(state, out, *, stop=True):
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
        if not stop:
            return False
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
    if out.is_dir():
        if stop:
            if not lifecycle.cleanup(out, verify_absence=True)["observed"]:
                return False
        elif lifecycle.open_groups(out):
            return False
    now = lifecycle.table()
    if not stop and any(lifecycle._observer_row(path, now) for path in lifecycle.own_observer_records(out)):
        return False
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
            observation_seconds, teardown_seconds, reset, observe, cleanup, retain=None):
    """Execute one attempt. Callbacks take (context, absolute Unix cutoff).

    Reset verifies the canonical target/user and clean no-op. Observe returns external
    evidence while the deployment is live. Cleanup attests quiescence and reconciles
    every '*.submitted' intent, including those with no remote ID. Cleanup receives
    local_processes_clear from the local teardown check. Callbacks must bound
    any subprocess they start by the phase cutoff. Invoke this entry point in the main
    thread of the attended probe process. A stopped process leaves its attempt pending for operator reconciliation.
    """
    data, digest, receipts = b.load(binding_path, fresh=False)
    held = data.get("review_hold", False)
    target = data["target"]
    identity_root = registry(data)
    b.require(isinstance(campaign, str) and campaign and b.match(r"[0-9a-f]{40}", build),
              "campaign ID and expected marketplace origin/main SHA required")
    state = identity_root / b.sha(b.encoded([campaign, build, digest]))
    operator = process_identity(os.getpid())
    keys = lease_keys(data)
    lease = lifecycle.take(keys, {"pid": os.getpid(), "case": b.CASE, "operator": operator})
    try:
        pending = {"state": "RETENTION_PENDING" if held else "RECONCILIATION_REQUIRED",
                   "state_dir": str(state), "product_acceptance": "UNKNOWN"}
        if state.exists():
            try:
                original = read(state / "start.json")
                b.require(original["binding_sha256"] == digest and original.get("review_hold", False) is held,
                          "hosted replay requires the original binding and hold")
                previous = settlement(state)
                if previous["state"] == "SETTLED" and not reusable(state, previous):
                    return pending
                if held and (previous["state"] == "RETAINED_QUIESCENT" and not retained(state, previous)
                             or (previous["state"] != "SETTLED" and os.path.lexists(state / "retirement-started.json"))):
                    return pending
                return previous
            except (OSError, ValueError, KeyError, TypeError):
                return pending
        peers = admission(data)
        b.require(not held or callable(retain), "review hold requires a retention callback")
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
        b.require(now < build_until < observe_until < deadline <= now + MAX_CAMPAIGN_SECONDS,
                  "deadline must fit a 24-hour window with observation and teardown reserves")
        argv = ["--case", b.CASE, "--environment-binding", str(binding_path), "--host", "codex",
                "--codex-bin", str(codex_bin), "--model", model, "--effort", "medium", "--source", "marketplace",
                "--output", str(out), "--baseline", str(baseline)]
        context = {"campaign": campaign, "build": build, "binding_sha256": digest, "target": target,
                   "pid": os.getpid(), "argv": argv, "state_dir": str(state), "output": str(out),
                   "namespace": data["namespace"], "legacy_prefixes": data["legacy_prefixes"],
                   "operator": operator, "lease_keys": keys, "build_until": build_until, "deadline": deadline}
        if held or "review_hold" in data:
            context["review_hold"] = held
        if held:
            context.update(synthetic_label=data["synthetic_label"], retained_generations=peers)
        state.mkdir(mode=0o700, parents=True)
        write_once(state / "start.json", context)
        if held:
            # The write fsyncs the record and its directory; also pin the new registry links.
            for parent in (state.parent, state.parent.parent, state.parent.parent.parent):
                fd = os.open(parent, os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
        result = dict(pending, runner_exit=None, observations=None, local_processes_clear=False)
        try:
            receipt = within(build_until, reset, context)
            b.require(verified(receipt, context, "reset") and receipt.get("empty_noop") is True
                      and reset_retained(receipt, context)
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
                    if processes_clear and held:
                        finish_retention(result, context, deadline, retain, quiesce_jobs=True)
                    elif processes_clear:
                        receipt = within(deadline, cleanup, {**context, "local_processes_clear": True})
                        if ((state / "reset.json").is_file() and cleanup_verified(receipt, context, state)
                                and b.recent(receipt.get("checked_at"), 300, time.time())):
                            seal(result, receipt, state)
                except (Exception, KeyboardInterrupt) as exc:
                    result["retention_error" if held else "cleanup_error"] = type(exc).__name__
                write_once(state / "settled.json", result)
        return result
    finally:
        lease.close()


def finish_retention(result, context, deadline, retain, *, prelaunch_noop=False, quiesce_jobs=False):
    state = Path(context["state_dir"])
    if not ((state / "reset.json").is_file() or prelaunch_noop):
        return result
    receipt = within(deadline, retain, dict(context, local_processes_clear=True,
                                            reconcile_prelaunch_noop=prelaunch_noop,
                                            retention_quiesce_jobs=quiesce_jobs))
    if (retention_verified(receipt, context, state) and b.recent(receipt.get("checked_at"), 300, time.time())
            and (not prelaunch_noop or receipt.get("prelaunch_noop") is True)):
        seal_retention(result, receipt, state)
    elif isinstance(receipt, dict):
        result["retention_check"] = receipt
    return result


def reconcile(binding_path, state, *, deadline, cleanup, retain=None):
    """Reacquire leases to prove the original hold or settle legacy cleanup."""
    data, digest, _ = b.load(binding_path, fresh=False)
    state = b.absolute(state)
    b.require(state.parent == registry(data), "invalid hosted reconciliation state path")
    keys = lease_keys(data)
    operator = process_identity(os.getpid()) if data.get("review_hold") is True else None
    about = {"pid": os.getpid(), "case": b.CASE}
    if operator:
        about["operator"] = operator
    lease = lifecycle.take(keys, about)
    try:
        context = read(state / "start.json")
        b.require(context["binding_sha256"] == digest and context["target"] == data["target"]
                  and context.get("review_hold", False) is data.get("review_hold", False),
                  "reconciliation requires the original binding")
        result = settlement(state)
        if reusable(state):
            return result
        if context.get("review_hold") is True:
            if time.time() < context["build_until"]:
                closure = state / "build-closed.json"
                b.require(closure.is_file() and read(closure) == phase_receipt(state), "hosted build cutoff not reached")
            if os.path.lexists(state / "retirement-started.json"):
                return {"state": "RETENTION_PENDING", "state_dir": str(state), "product_acceptance": "UNKNOWN",
                        "retention_error": "RETIREMENT_UNRESOLVED"}
            if os.path.lexists(state / "retained.json"):
                b.require(retained(state), "invalid immutable generation proof")
                return read(state / "retained.json")
            b.require(callable(retain), "review hold requires a retention callback")
            result["state"] = "RETENTION_PENDING"
            processes_clear = local_clear(state, Path(context["output"]))
            close_build(state)
            result["local_processes_clear"] = processes_clear
            if processes_clear:
                current = dict(context, pid=os.getpid(), operator=operator, lease_keys=keys)
                return finish_retention(result, current, deadline, retain,
                                        prelaunch_noop=b.no_launch_without_reset(context))
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


def retirement(binding_path, state, *, deadline, plan_retirement, retire=None, approval=None, approval_sha256=None):
    """Plan or explicitly retire a retained generation under its original org lease."""
    data, digest, _ = b.load(binding_path, fresh=False)
    state = b.absolute(state)
    b.require(data.get("review_hold") is True and state.parent == registry(data), "expected held retirement target")
    keys = lease_keys(data)
    operator = process_identity(os.getpid())
    lease = lifecycle.take(keys, {"pid": os.getpid(), "case": b.CASE, "operator": operator})
    try:
        context = read(state / "start.json")
        b.require(context["binding_sha256"] == digest and context["target"] == data["target"] and retained(state),
                  "retirement requires the original binding and sealed generation")
        if reusable(state):
            result = read(state / "retired.json")
            b.require(retire is not None and result["cleanup"]["retirement"]["approval_sha256"] == approval_sha256
                      and b.sha(b.absolute(approval).read_bytes()) == approval_sha256,
                      "generation already retired with a different request")
            return result

        def operation(context, cutoff):
            b.require(local_clear(state, Path(context["output"]), stop=False), "local process proof changed")
            context = dict(context, local_processes_clear=True, pid=os.getpid(), operator=operator, lease_keys=keys)
            if retire is None:
                return plan_retirement(context, cutoff)
            return retire(dict(context, retirement_approval=str(approval),
                               retirement_approval_sha256=approval_sha256), cutoff)

        receipt = within(deadline, operation, context)
        if retire is None and verified(receipt, context, "retirement-plan"):
            return {"state": "RETIREMENT_PLANNED", "state_dir": str(state), "plan": receipt,
                    "plan_sha256": b.sha(b.encoded(receipt))}
        if retire is not None and cleanup_verified(receipt, context, state, phase="retire"):
            result = {"state_dir": str(state), "product_acceptance": "UNKNOWN",
                      "retention_sha256": read(state / "retained.json")["retention_sha256"]}
            seal(result, receipt, state)
            write_once(state / "retired.json", result)
            return result
        return {"state": "RETIREMENT_REFUSED", "state_dir": str(state), "retirement_check": receipt}
    finally:
        lease.close()
