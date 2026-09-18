#!/usr/bin/env python3
"""Optional supervised host execution; graph authority remains ShipLoop state.md.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

from shiploop_host import HostError
import shiploop_navigator as navigator
import shiploop_store as store

CLI = Path(__file__).with_name("shiploop")
INNER_LOOP, OFF = "inner-loop", "off"
POLICIES = frozenset((OFF, INNER_LOOP))
POLICY_ENV = "SHIPLOOP_CONTEXT_RESET"
HOSTS = ("codex", "grok", "claude")


class DriverError(HostError):
    pass


def read_state(run):
    path = run / "state.md"
    if path.is_symlink():
        raise DriverError("state.md must be a regular file")
    state = store.read_record(path)
    navigator.validate(state)
    if state["navigator_protocol_version"] != 3:
        raise DriverError("Context supervision requires an initialized Navigator v3 run")
    return state


def digest(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def selected_policy(explicit, environ, previous=None):
    value = explicit if explicit is not None else environ.get(POLICY_ENV)
    if value is None:
        return previous or INNER_LOOP
    if value not in POLICIES:
        raise DriverError(f"{POLICY_ENV}/--context-reset must be off or inner-loop")
    if previous is not None and value != previous:
        raise DriverError("Policy differs from the saved host receipt; do not silently change an active run")
    return value


@contextmanager
def owner_lock(run):
    path = run / "context-host.lock"
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise DriverError("Another context host owns this run") from exc
        yield
    finally:
        os.close(fd)


def save_receipt(run, receipt):
    path = run / "context-host.md"
    if path.is_symlink():
        raise DriverError("context-host.md cannot be a symlink")
    store.atomic_write_text(path, store.dumps(receipt, title="ShipLoop context host receipt"))


def validate_receipt(receipt):
    if not isinstance(receipt, dict):
        raise DriverError("Host receipt must be an object")
    required = {"schema", "host", "run_id", "repo", "run_dir", "cli", "policy",
                "network_access", "status", "thread_id", "need_fresh", "state_digest",
                "turns", "reset_boundaries"}
    if not required.issubset(receipt) or set(receipt) - required - {"owner_phase"}:
        raise DriverError("Host receipt has missing or unknown fields")
    boundaries = receipt["reset_boundaries"]
    if (receipt["status"] not in ("ready", "running", "uncertain")
            or type(receipt["need_fresh"]) is not bool
            or (receipt["network_access"] is not None and type(receipt["network_access"]) is not bool)
            or not isinstance(receipt["turns"], list)
            or not all(isinstance(turn, dict) for turn in receipt["turns"])
            or not isinstance(boundaries, list)
            or not all(isinstance(key, str) and key for key in boundaries)
            or len(set(boundaries)) != len(boundaries)
            or (receipt["thread_id"] is not None
                and (not isinstance(receipt["thread_id"], str) or not receipt["thread_id"]))
            or not isinstance(receipt["state_digest"], str)
            or len(receipt["state_digest"]) != 64
            or any(c not in "0123456789abcdef" for c in receipt["state_digest"])
            or (receipt["need_fresh"] and not boundaries)):
        raise DriverError("Host receipt has invalid recovery fields")


def owner_transition(before, after):
    """Accept one producer OR one completed Improve owner, never two owners.

    Improve can bind and finish in one model turn, increasing revision twice.
    History acceptance, rather than a fabricated revision, bounds that owner.
    """
    navigator.validate(before)
    navigator.validate(after)
    for key in ("run_id", "repo", "prompt", "bound_plan", "navigator_protocol_version"):
        if before[key] != after[key]:
            raise DriverError("Owner changed run identity or durable request: " + key)
    if before["status"] != "active" or after["revision"] <= before["revision"]:
        raise DriverError("Owner did not advance the saved run")
    action = navigator.current_action(before)["id"]
    if action in before["accepted"] or action in before["improve_results"]:
        raise DriverError("Current action was already accepted")
    # An explicit control stop retains the same action/history. A blocked
    # accepted result is checked below like any other Improve completion.
    if after["status"] in ("paused", "blocked", "halted") and after["history"] == before["history"]:
        if after["accepted"] != before["accepted"] or after["improve_results"] != before["improve_results"]:
            raise DriverError("Control stop changed prior acceptances")
        return None
    if before["active_improve"] is None:
        child = after["active_improve"]
        if (child is None or child["action_id"] != action
                or after["history"] != before["history"]
                or after["accepted"] != before["accepted"]
                or after["improve_results"] != before["improve_results"]
                or after["revision"] != before["revision"] + 1):
            raise DriverError("Producer must submit once and stop before Improve")
        return None
    if (after["active_improve"] is not None
            or len(after["history"]) != len(before["history"]) + 1
            or after["history"][:-1] != before["history"]
            or after["history"][-1]["action"] != action
            or action not in after["improve_results"]
            or set(after["accepted"]) != set(before["accepted"]) | {action}
            or any(after["accepted"].get(k) != v for k, v in before["accepted"].items())
            or any(after["improve_results"].get(k) != v for k, v in before["improve_results"].items())):
        raise DriverError("Improve must complete exactly its current parent action")
    if (navigator.current_stage(before) == "carry-forward"
            and before["active_improve"]["action_id"] == action
            and before["active_improve"]["stage"] == "carry-forward"
            and after["history"][-1]["stage"] == "carry-forward"
            and after["history"][-1]["outcome"] == "done"
            and after["accepted"][action]["outcome"] == "done"
            and after["status"] == "active"
            and after["work_index"] == before["work_index"] + 1
            and (navigator.current_stage(after) == "select-work"
                 or after["stage"] in navigator.graph(after)[2])):
        return before["run_id"] + ":" + action
    return None


def next_packet(cli, run, repo):
    command = [sys.executable, "-B", str(cli), "next", "--run-dir", str(run)]
    result = subprocess.run(command, cwd=repo, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise DriverError("ShipLoop next failed: " + result.stdout + result.stderr)
    return result.stdout


def bootstrap(cli, run, state, packet):
    owner = "the current standalone Improve campaign" if state["active_improve"] else "the current producer action"
    recovery = shlex.join([sys.executable, "-B", str(cli), "next", "--run-dir", str(run)])
    return (
        "You are the sole execution owner for one bounded ShipLoop action.\n"
        f"Repository: {state['repo']}\nRun: {run}\nSelected CLI: {cli}\n"
        f"Recovery command: {recovery}\n"
        f"Execute ONLY {owner} from the current authoritative packet below. "
        "Load its cited instructions and durable requirements. Submit its exact completion callback, "
        "then STOP before executing the returned next owner. This launcher supplies that next owner "
        "in a later turn; this explicit scope overrides general auto-continue guidance. "
        "If Improve is current, complete the actual campaign with its required evidence; never fabricate a receipt. "
        "Do not initialize another run. Keep durable decisions and evidence in the packet's records. "
        "Settle all tools and delegated work before returning. If authority or a required input is missing, "
        "use the packet's blocked/pause path and stop. Do not edit context-host.md or context-host.lock.\n\n"
        + packet
    )


def drive(args, *, transport_factory=None, environ=None):
    environ = os.environ if environ is None else environ
    if environ.get("SHIPLOOP_CONTEXT_HOST_WORKER") == "1":
        raise DriverError("This owner is already supervised; submit its current callback instead of starting another host")
    if args.host not in HOSTS:
        raise DriverError("Unsupported context host: " + args.host)
    if args.allow_network and args.host != "codex":
        raise DriverError("--allow-network is a Codex sandbox option; Grok and Claude retain native host permissions")
    if transport_factory is None:
        if args.host == "codex":
            from shiploop_host_codex import CodexTransport
            transport_factory = CodexTransport
        elif args.host == "grok":
            from shiploop_host_grok import GrokTransport
            transport_factory = GrokTransport
        else:
            from shiploop_host_claude import ClaudeTransport
            transport_factory = ClaudeTransport
    cli = Path(os.path.abspath(os.path.expanduser(args.cli)))
    if cli.resolve(strict=True) != CLI.resolve(strict=True):
        raise DriverError("Use this selected package's bundled ShipLoop CLI (a symlink to it is allowed)")
    run = Path(args.run_dir).expanduser().resolve(strict=True)
    if args.max_turns < 1:
        raise DriverError("--max-turns must be positive")
    with owner_lock(run):
        state = read_state(run)
        repo = str(Path(state["repo"]).resolve(strict=True))
        path = run / "context-host.md"
        if path.is_symlink():
            raise DriverError("context-host.md cannot be a symlink")
        receipt = store.read_record(path) if path.exists() else None
        if receipt is not None:
            validate_receipt(receipt)
        policy = selected_policy(args.context_reset, environ, receipt.get("policy") if receipt else None)
        binding = {"schema": "shiploop-context-host/v1", "host": args.host,
                   "run_id": state["run_id"], "repo": repo, "run_dir": str(run),
                   "cli": str(cli), "policy": policy, "network_access": bool(args.allow_network) if args.host == "codex" else None}
        if receipt:
            if any(receipt.get(k) != v for k, v in binding.items()):
                raise DriverError("Host receipt configuration/identity mismatch")
            if receipt.get("status") != "ready":
                raise DriverError("Uncertain prior owner; inspect its saved task before recovery: "
                                  + str(receipt.get("thread_id")) + "; phase=" + str(receipt.get("owner_phase")))
            if receipt.get("state_digest") != digest(state):
                raise DriverError("Run changed outside the launcher; reconcile its host receipt before recovery")
        else:
            receipt = {**binding, "status": "ready", "thread_id": None, "need_fresh": False,
                       "state_digest": digest(state), "turns": [], "reset_boundaries": []}
            save_receipt(run, receipt)
        if state["status"] != "active":
            return {"status": state["status"], "turns_this_launch": 0,
                    "packet": next_packet(cli, run, repo)}
        # A receipt is uncertain on every exceptional path after claiming an owner.
        host_options = ({"writable_roots": [repo, run], "network_access": args.allow_network}
                        if args.host == "codex" else {})
        with transport_factory(repo, **host_options) as host:
            attached = False
            for count in range(args.max_turns):
                if digest(read_state(run)) != receipt["state_digest"]:
                    raise DriverError("Saved run changed between owners")
                packet = next_packet(cli, run, repo)
                before = read_state(run)
                if digest(before) != receipt["state_digest"]:
                    raise DriverError("Recovery changed the saved run; reconcile before launching an owner")
                receipt["status"] = "running"
                receipt["owner_phase"] = "attaching-task-no-turn-sent"
                save_receipt(run, receipt)
                try:
                    if receipt["thread_id"] is None or receipt["need_fresh"]:
                        receipt["thread_id"] = host.start_thread(repo)
                        receipt["need_fresh"] = False
                        attached = True
                    elif not attached:
                        host.resume_thread(receipt["thread_id"])
                        attached = True
                    receipt["owner_phase"] = "turn-may-have-started"
                    save_receipt(run, receipt)
                    result = host.run_turn(receipt["thread_id"], bootstrap(cli, run, before, packet))
                    receipt["turns"].append(result)
                    if result["status"] != "completed":
                        raise DriverError("Owner turn did not complete: " + str(result.get("error")))
                    after = read_state(run)
                    boundary = owner_transition(before, after)
                    if boundary and policy == INNER_LOOP:
                        if boundary in receipt["reset_boundaries"]:
                            raise DriverError("Refusing to consume an already handled reset boundary")
                        receipt["reset_boundaries"].append(boundary)
                        receipt["need_fresh"] = True
                    receipt["state_digest"] = digest(after)
                    receipt["status"] = "ready"
                    receipt["owner_phase"] = "owner-completed"
                    save_receipt(run, receipt)
                except BaseException:
                    receipt["status"] = "uncertain"
                    save_receipt(run, receipt)
                    raise
                print(json.dumps({"owner_turn": len(receipt["turns"]), "thread_id": receipt["thread_id"],
                                  "stage": navigator.current_stage(after), "status": after["status"],
                                  "reset_pending": receipt["need_fresh"]}), flush=True)
                if after["status"] != "active":
                    return {"status": after["status"], "turns_this_launch": count + 1,
                            "packet": next_packet(cli, run, repo)}
        return {"status": "turn-limit", "turns_this_launch": args.max_turns}


def main(argv=None, *, cli=CLI):
    parser = argparse.ArgumentParser(prog="shiploop drive", description=__doc__)
    parser.add_argument("--run-dir", required=True, help="Existing initialized Navigator v3 run")
    parser.add_argument("--host", choices=HOSTS, required=True)
    parser.add_argument("--context-reset", choices=sorted(POLICIES), default=None,
                        help="New controller default: inner-loop; an existing receipt keeps its saved policy")
    parser.add_argument("--max-turns", type=int, default=1000)
    parser.add_argument("--allow-network", action="store_true", help="Codex shell sandbox: allow network; repeat when resuming")
    args = parser.parse_args(argv)
    args.cli = str(cli)
    try:
        result = drive(args)
        if "packet" in result:
            print(result.pop("packet"))
        print(json.dumps(result))
        return 0 if result["status"] == "done" else 2
    except (HostError, navigator.NavigatorError, store.StorageError, OSError, ValueError) as exc:
        print("ShipLoop context host: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
