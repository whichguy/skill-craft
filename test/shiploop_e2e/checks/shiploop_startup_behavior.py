#!/usr/bin/env python3
"""Grade canonical startup/first-Stop artifacts without executing ShipLoop.

Fresh trace transitions and archived packet bytes establish startup; native
decisions and original launch bounds establish continuation. Observer predicates
only flag uncertainty, never prove shell execution or startup binding.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path

from shiploop_hook_contract import locate_invocation

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills/shiploop/scripts"))
import shiploop_keepalive as observer
import shiploop_store as store

RECEIPT = "shiploop-startup-behavior-receipt.json"
PRINT_END = "=== end ShipLoop print ===\n"


class Verdict(Exception):
    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


def require(condition, message, status="unknown"):
    if not condition:
        raise Verdict(status, message)


def rows(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    require(lines, f"empty artifact: {path}")
    result = []
    for number, line in enumerate(lines, 1):
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise Verdict("unknown", f"unparseable {path}:{number}") from exc
        require(isinstance(row, dict), f"non-object {path}:{number}")
        result.append(row)
    return result


def observation(report, name, path, indices=(), **facts):
    report["observations"][name] = {
        "artifact": str(path), "lines": [index + 1 for index in indices], **facts,
    }


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def paired_update(events, index, stop):
    call = events[index]
    require(isinstance(call.get("rawInput"), dict) and isinstance(call["rawInput"].get("command"), str),
            "tool command provenance is missing")
    identity = call.get("toolCallId")
    require(isinstance(identity, str) and identity, "tool call identity is missing")
    calls = [i for i, event in enumerate(events[:stop])
             if event.get("type") == "tool_call" and event.get("toolCallId") == identity]
    updates = [i for i, event in enumerate(events[:stop])
               if event.get("type") == "tool_call_update" and event.get("toolCallId") == identity]
    require(calls == [index] and len(updates) == 1 and updates[0] > index,
            "command/output pairing is missing or ambiguous")
    update = events[updates[0]]
    output = update.get("rawOutput")
    require(isinstance(output, dict) and output.get("type") == "command_execution"
            and isinstance(output.get("output_for_prompt"), str)
            and output.get("command") == call.get("rawInput", {}).get("command"),
            "unverified Codex command output shape")
    require(update.get("status") in ("completed", "failed") and type(output.get("exit_code")) is int,
            "command exit evidence is missing")
    return updates[0], output["output_for_prompt"]


def packet_text(root, packet):
    relative = packet.get("file")
    require(isinstance(relative, str), "packet file locator is missing")
    path = (root / relative).resolve()
    require(path.is_relative_to(root) and not Path(relative).is_absolute(), "packet leaves its run")
    text = path.read_text(encoding="utf-8")
    printed = text + PRINT_END
    require(packet.get("sha") == hashlib.sha256(text.encode()).hexdigest()[:16]
            and packet.get("chars") == len(text), "packet archive is inconsistent")
    if packet.get("whole") is False:
        head = packet.get("head_file")
        require(isinstance(head, str), "partial packet exposure lacks its archived printed head")
        path = (root / head).resolve()
        require(path.is_relative_to(root) and not Path(head).is_absolute(), "printed head leaves its run")
        printed = path.read_text(encoding="utf-8")
        require(path.stem == hashlib.sha256(printed.encode()).hexdigest()[:16], "printed head archive is inconsistent")
    else:
        require(packet.get("whole") is True, "packet whole/head exposure is unknown")
    require(packet.get("printed") == len(printed) and printed.endswith(PRINT_END),
            "packet exposure is partial or inconsistent")
    return path, printed


def session_intervals(sessions, events):
    require(len(sessions) % 2 == 0, "session end boundary is missing")
    intervals = []
    previous = 0
    for i in range(0, len(sessions), 2):
        start, end = sessions[i:i + 2]
        lo, hi = start.get("events_line"), end.get("events_line")
        require(start.get("row") == "start" and end.get("row") == "end"
                and start.get("n") == end.get("n") == i // 2 + 1
                and start.get("host") == "codex" and number(start.get("t")) and number(end.get("t"))
                and start["t"] < end["t"] and type(lo) is int and type(hi) is int
                and lo == previous and lo < hi <= len(events), "unverified or mixed session intervals")
        ids = {event["sessionId"] for event in events[lo:hi] if "sessionId" in event}
        require(len(ids) == 1 and all(isinstance(value, str) and value for value in ids),
                "missing or mixed Codex session identity")
        session = ids.pop()
        require(events[lo].get("type") == "available_commands" and events[lo].get("sessionId") == session
                and events[hi - 1].get("type") == "end" and events[hi - 1].get("sessionId") == session,
                "unverified normalized Codex process boundaries")
        require(not any(event.get("type") in ("available_commands", "end")
                        for event in events[lo + 1:hi - 1]),
                "original session identity is ambiguous within process boundaries")
        if intervals:
            require(start["t"] >= intervals[-1][1]["t"], "overlapping session times")
        intervals.append((start, end, session))
        previous = hi
    require(previous == len(events) and sessions[0].get("kind") == "first"
            and sessions[0].get("reason") == "start", "first launch or stream coverage is unknown")
    return intervals


def attempt_start(command):
    require(number(command.get("ms")) and command["ms"] >= 0,
            "command attempt duration is missing or invalid")
    # record_command samples rounded monotonic ms before record's rounded wall
    # ts. Account for both millisecond roundings; no tool-event clock is inferred.
    return command["ts"] - command["ms"] / 1000 - 0.001


def position(command, name):
    pair = command.get(name)
    require(isinstance(pair, list) and len(pair) == 2,
            f"command {name} transition is missing or malformed")
    return pair


def absolute_path(value):
    require(isinstance(value, str) and value.strip() and Path(value).is_absolute(),
            "recorded path is missing or not absolute")
    return Path(value)


def identity_object(pairs):
    require(len({key for key, _ in pairs}) == len(pairs), "conflicting explicit run identity keys")
    return dict(pairs)


def invalid_constant(value):
    raise Verdict("unknown", f"nonstandard explicit run identity constant: {value}")


def selected_trace(work, out, invocation):
    require(absolute_path(invocation.get("cwd")).resolve() == work,
            "invocation does not identify checked workdir")
    identity_path = out / "shiploop-run.json"
    if identity_path.exists() or identity_path.is_symlink():
        require(not identity_path.is_symlink(), "explicit run identity is a symlink")
        identity = json.loads(identity_path.read_text(encoding="utf-8"),
                              object_pairs_hook=identity_object, parse_constant=invalid_constant)
        require(isinstance(identity, dict), "explicit run identity is not an object")
        selected = absolute_path(identity.get("run_dir"))
        require(not selected.is_symlink(), "selected run root is a symlink")
        root = selected.resolve()
        require(root.is_dir() and root != work, "selected run root is missing or is checked workdir")
        if not root.is_relative_to(work):
            workspace = store.read_record(root.parent / "workspace.md")
            state = store.read_record(root / "state.md")
            require(isinstance(workspace, dict) and isinstance(state, dict),
                    "managed workspace/state record is not an object")
            require(absolute_path(workspace.get("source_repo")).resolve() == work
                    and absolute_path(workspace.get("run_dir")).resolve() == root,
                    "managed workspace source/run join disagrees with selected identity")
            require(absolute_path(workspace.get("worktree")).resolve()
                    == absolute_path(state.get("repo")).resolve()
                    and isinstance(state.get("run_id"), str) and state["run_id"].strip(),
                    "managed workspace/state repo or run_id join is missing or mismatched")
        trace_path = root / "trace.jsonl"
    else:
        trace_paths = []
        for directory, folders, files in os.walk(work, followlinks=False):
            folders[:] = [name for name in folders if not (Path(directory) / name).is_symlink()]
            if "trace.jsonl" in files:
                trace_paths.append(Path(directory) / "trace.jsonl")
        require(len(trace_paths) == 1, "missing or multiple candidate run traces under checked workdir")
        trace_path = trace_paths[0]
        root = trace_path.parent.resolve()
        require(root.is_relative_to(work) and root != work, "startup run is outside checked workdir")
    require(not trace_path.is_symlink() and trace_path.is_file(), "selected trace is missing or a symlink")
    return trace_path


def print_exposures(printed, tools):
    return [(called, returned) for called, returned, output, code in tools
            if code == 0 and printed in output]


def packet_owners(trace, commands, start, end):
    # emit() prints and records each packet; protocol.main finally appends the
    # outer command, even for workspace's nested init. Hooks may interleave.
    result = []
    for i, packet in enumerate(trace):
        if packet.get("kind") != "packet" or not start < packet["ts"] < end:
            continue
        following = [(j, command) for j, command in commands if j > i]
        require(following, "printed packet has no recorded outer command")
        j, command = following[0]
        require(attempt_start(command) < packet["ts"] <= command["ts"],
                "printed packet cannot be joined to its outer command interval")
        result.append((packet, j, command))
    return result


def possible_binder(command, output):
    # These are the common source observer's pure classification functions.
    # Never call observe/run_status, inspect a package, or evaluate shell text.
    payload = {"tool_input": {"command": command}, "tool_response": output}
    marker = observer.last_marker(payload)
    invoking = observer.invoking_command(payload)
    return (marker is not None and invoking is not None and observer.DRIVING_COMMAND.search(invoking)
            or observer.command_run_dir(payload) is not None)


def additional_startup(work, out, selected, start, end, report):
    """Find a second archived fresh startup in the trial's known run layouts."""
    candidates = set()
    workspace = selected.parent.parent
    managed = workspace if (workspace / "workspace.md").is_file() else selected.parent
    bases = (work, out, managed)
    observation(report, "startup_scan", out, bases=[str(base) for base in bases],
                excluded=[str(out / name) for name in ("home", "build")],
                scope="trial inventory and selected workspace; unselected external roots are not searched")
    for base in bases:
        if base.is_symlink():
            continue
        for directory, folders, files in os.walk(base, followlinks=False):
            folders[:] = [name for name in folders
                          if not (Path(directory) / name).is_symlink()
                          and not (Path(directory) == out and name in {"home", "build"})]
            path = Path(directory) / "trace.jsonl"
            if "trace.jsonl" in files and not path.is_symlink():
                candidates.add(path.resolve())
    for path in sorted(candidates):
        if path == selected.resolve():
            continue
        try:
            other = rows(path)
            packet = other[0]
            command = next(row for row in other if row.get("kind") == "command")
            revision, action = packet.get("rev"), packet.get("action")
            require(all(row.get("v") == 1 and number(row.get("ts")) for row in other)
                    and packet.get("kind") == "packet" and packet.get("stage") == "intake"
                    and packet.get("status") == "active" and type(revision) is int and revision >= 0
                    and isinstance(action, str) and action
                    and command.get("verb") in ("init", "workspace")
                    and command.get("status") == "active" and type(command.get("exit")) is int
                    and command["exit"] == 0
                    and position(command, "rev") == [None, revision]
                    and position(command, "stage") == [None, "intake"]
                    and position(command, "cursor") == [None, action] and not command.get("accepted")
                    and start["t"] + 0.0005 < attempt_start(command)
                    and attempt_start(command) < packet["ts"] <= command["ts"]
                    and command["ts"] + 0.0005 < end["t"],
                    "additional trace is not a verified fresh startup in this session")
            packet_text(path.parent, packet)
        except (Verdict, OSError, ValueError, TypeError, KeyError, IndexError, StopIteration):
            continue  # Unrelated, stale or incomplete app traces do not select a run.
        return path
    return None


def evaluate(work, out, invocation, report):
    require(invocation.get("host") == "codex", "only normalized Codex is verified")
    events_path, sessions_path = out / "events.jsonl", out / "sessions.jsonl"
    events, sessions = rows(events_path), rows(sessions_path)
    intervals = session_intervals(sessions, events)
    start, end, session = intervals[0]
    observation(report, "session", sessions_path, (0, 1), session_id=session,
                events_interval=[start["events_line"], end["events_line"]])

    trace_path = selected_trace(work, out, invocation)
    root = trace_path.parent
    trace = rows(trace_path)
    require(all(row.get("v") == 1 and number(row.get("ts")) for row in trace), "unverified run trace schema")
    require(all(trace[i - 1]["ts"] <= trace[i]["ts"] for i in range(1, len(trace))),
            "trace time order is inconsistent")
    first = trace[0]
    action, revision = first.get("action"), first.get("rev")
    require(first.get("kind") == "packet" and first.get("stage") == "intake"
            and isinstance(action, str) and action and type(revision) is int and revision >= 0,
            "first trace row is not the first intake packet")
    path, printed = packet_text(root, first)
    commands = [(i, row) for i, row in enumerate(trace) if row.get("kind") == "command"]
    require(commands, "startup command trace is missing")
    require(all(isinstance(row.get("verb"), str) and row["verb"]
                and type(row.get("exit")) is int for _, row in commands),
            "command verb/exit evidence is missing or malformed")
    startup_index, startup = commands[0]
    require(sum(row.get("kind") == "packet" for row in trace[:startup_index]) == 1,
            "canonical initial packet is ambiguous")
    require(startup.get("verb") in ("init", "workspace") and startup.get("exit") == 0
            and startup.get("stage") == [None, "intake"] and startup.get("cursor") == [None, action]
            and startup.get("rev") == [None, revision] and not startup.get("accepted"),
            "fresh startup and first trace command cannot be joined")
    require(start["t"] + 0.0005 < attempt_start(startup)
            and start["t"] + 0.001 < first["ts"] <= startup["ts"]
            and startup["ts"] + 0.001 < end["t"],
            "fresh startup timing is outside or tied with original session bounds")
    observation(report, "first_packet", path, action=action, revision=revision, root=str(root))
    observation(report, "startup_trace", trace_path, (startup_index,))

    decisions_path = out / "home/.local/state/shiploop/keepalive/decisions.log"
    decisions = rows(decisions_path)
    session_hash = hashlib.sha256(session.encode()).hexdigest()[:12]
    require(all(number(row.get("at")) for row in decisions), "decision timestamp is missing")
    require(all(decisions[i - 1]["at"] <= decisions[i]["at"] for i in range(1, len(decisions))),
            "decision time order is inconsistent")
    stops = [(i, row) for i, row in enumerate(decisions)
             if first["ts"] - 0.0005 <= row["at"] <= end["t"] + 0.0005
             and row.get("decision") != "release"]
    require(stops, "first stop decision for startup session is missing")
    require(all(row.get("host") == "codex" and row.get("session") == session_hash
                and row.get("decision") in ("allow", "continue") for _, row in stops),
            "mixed or unidentified stop sessions in startup launch")
    decision_index, decision = stops[0]
    observation(report, "first_stop", decisions_path, (decision_index,), session_hash=session_hash,
                decision=decision["decision"], why=decision.get("why"))
    require(len(stops) == 1 or stops[1][1]["at"] > decision["at"], "tied stop decisions")
    require(startup["ts"] + 0.0005 < decision["at"] < end["t"] - 0.0005,
            "first stop cannot be ordered after startup in the original session")
    # Decide the first native allow before inspecting any later tool evidence.
    # An unbound allow legitimately has no run hook. Outer rescue cannot replace it.
    require(decision["decision"] != "allow", "first startup stop allowed termination: "
            + str(decision.get("why")), "fail")
    observation(report, "command_attempts", trace_path, [i for i, _ in commands[1:]])
    for _, command in commands[1:]:
        require(decision["at"] < attempt_start(command),
                "first Stop is not strictly before every later command attempt (tie, pre-Stop or in-flight)")

    boundary = stops[1][1]["at"] if len(stops) > 1 else end["t"]
    hooks = [(i, row) for i, row in enumerate(trace) if row.get("kind") == "hook"
             and row.get("hook") == "stop" and first["ts"] <= row["ts"] < boundary + 0.0005]
    require(len(hooks) <= 1, "first stop trace is ambiguous")
    hook_index, hook = hooks[0] if hooks else (None, None)
    if hook:
        require(hook.get("session") == session_hash, "first stop trace has mixed session identity")
        require(hook.get("host") == "codex" and hook.get("decision") == decision["decision"]
                and hook.get("why") == decision.get("why") and startup_index < hook_index
                and decision["at"] - 0.0005 <= hook["ts"]
                and hook["ts"] + 0.0005 < boundary,
                "first stop trace and decision cannot be uniquely correlated")
    require(hook, "first stop trace is missing")
    observation(report, "continue_hook", trace_path, (hook_index,), session_hash=session_hash)
    extra = additional_startup(work, out, trace_path, start, end, report)
    if extra is not None:
        observation(report, "additional_startup", extra)
    require(extra is None, "additional fresh startup trace in the original session")

    tools = []
    for i, event in enumerate(events[:end["events_line"]]):
        if event.get("type") != "tool_call" or event.get("toolName") != "run_terminal_command":
            continue
        returned, output = paired_update(events, i, end["events_line"])
        update = events[returned]
        code = update["rawOutput"]["exit_code"]
        require(code != 0 or update.get("status") == "completed", "successful command status is inconsistent")
        tools.append((i, returned, output, code))
    owners = packet_owners(trace, commands, start["t"], end["t"])
    exposures = print_exposures(printed, tools)
    require(exposures, "canonical first print has no successful original-session tool exposure")
    initial = [(packet, j, command) for packet, j, command in owners if packet.get("sha") == first["sha"]]
    require(len(exposures) == len(initial)
            and all(packet.get("action") == action and packet.get("rev") == revision
                    and command["exit"] == 0 and packet_text(root, packet)[1] == printed
                    for packet, _, command in initial)
            and initial[0][1] == startup_index
            and all(exposures[i - 1][1] < exposures[i][0] for i in range(1, len(exposures)))
            and all(output.count(printed) == 1 for _, _, output, code in tools if code == 0 and printed in output),
            "first print exposures do not uniquely cover canonical startup/reprint rows")
    called, returned = exposures[0]
    observation(report, "startup", events_path, (called, returned),
                command=events[called]["rawInput"].get("command"))

    for i, returned, output, code in tools:
        if i == called:
            continue
        # Only exact archived output, unique exposure order, exit and a post-Stop
        # outer-command interval can locate an extra possible binder. Counts of
        # regex matches/commands alone establish nothing (notably in heredocs).
        joined = []
        for packet, j, command in owners:
            _, sent = packet_text(root, packet)
            if output.count(sent) != 1 or code != command["exit"]:
                continue
            matching = [(p, k) for p, k, _ in owners if p.get("sha") == packet.get("sha")]
            seen = print_exposures(sent, tools)
            if (len(matching) == len(seen) and (i, returned) in seen
                    and all(seen[n - 1][1] < seen[n][0] for n in range(1, len(seen)))
                    and matching[seen.index((i, returned))][1] == j
                    and all(packet_text(root, p)[1] == sent for p, _ in matching)):
                joined.append(command)
        correlated = (i > exposures[0][1] and len(joined) == 1
                      and decision["at"] < attempt_start(joined[0]))
        if correlated:
            break  # All later tool calls follow a proven post-Stop return.
        if possible_binder(events[i]["rawInput"].get("command"), output):
            observation(report, "binding_uncertainty", events_path, (i, returned),
                        command=events[i]["rawInput"]["command"])
            require(False, "uncorrelated binding-capable tool call could precede the first Stop")

    accepted = []
    for i, command in commands:
        entries = command.get("accepted", [])
        require(isinstance(entries, list) and all(isinstance(entry, dict)
                and isinstance(entry.get("action"), str) and entry["action"] for entry in entries),
                "acceptance entries are malformed or ambiguous")
        accepted.extend((i, command, entry) for entry in entries if entry["action"] == action)
    observation(report, "intake_acceptance", trace_path, [i for i, _, _ in accepted], action=action)
    require(len(accepted) <= 1, "duplicate accepted first intake completion", "fail")
    require(accepted, "accepted first intake completion is missing")
    accepted_index, completed, entry = accepted[0]
    require(completed.get("verb") == "complete" and completed.get("action") == action
            and type(completed.get("exit")) is int and completed["exit"] == 0
            and entry.get("stage") == "intake" and entry.get("outcome") == "done",
            "acceptance is not an unambiguous successful completion of the first intake action")
    require(hook_index < accepted_index and hook["ts"] + 0.0005 < attempt_start(completed),
            "accepted intake attempt cannot be ordered after the first continue hook")
    require(completed["ts"] + 0.001 < end["t"],
            "intake completion is outside or tied with the original session")

    require(len(completed["accepted"]) == 1
            and position(completed, "rev")[0] == revision
            and type(position(completed, "rev")[1]) is int
            and position(completed, "rev")[1] > revision
            and position(completed, "cursor")[1] != action,
            "accepted intake transition is malformed or ambiguous")

    recovery = []
    expected = {"rev": revision, "stage": "intake", "cursor": action}
    for i, command in commands[1:]:
        if i > accepted_index:
            break  # Subsequent app stages may advance normally.
        for name, value in expected.items():
            pair = position(command, name)
            require(pair[0] == value, "pending intake state advanced or reset before acceptance", "fail")
            if i < accepted_index:
                require(pair[1] == value, "pending intake state advanced or reset before acceptance", "fail")
        if i < accepted_index:
            require(command.get("verb") not in {"init", "workspace", "resume", "restart", "reinit", "reset"},
                    "prohibited entry command before original intake acceptance: "
                    + command["verb"], "fail")
            require(not command.get("accepted"), "other work accepted before original intake", "fail")
            if command.get("verb") == "next":
                recovery.append(i)
    observation(report, "same_action_recovery", trace_path, recovery)


def main():
    report = {"schema": "shiploop-startup-behavior/v1", "status": "unknown", "observations": {}}
    receipt = None
    try:
        work = Path.cwd().resolve()
        invocation_path, invocation = locate_invocation(work, None)
        receipt = invocation_path.parent / RECEIPT
        observation(report, "invocation", invocation_path, workdir=str(work), host=invocation.get("host"))
        evaluate(work, invocation_path.parent, invocation, report)
        report.update(status="pass", reason="same-session first-stop continue and exactly one same-action intake acceptance")
    except Verdict as exc:
        report.update(status=exc.status, reason=str(exc))
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, RuntimeError) as exc:
        report.update(status="unknown", reason=f"artifact/correlation gap: {type(exc).__name__}: {exc}")
    if receipt is not None:
        receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"{report['status'].upper()}: {report['reason']}")
    return {"pass": 0, "fail": 1, "unknown": 2}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
