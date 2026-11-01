#!/usr/bin/env python3
"""Grade recorded Codex startup handoff behavior; never execute or load ShipLoop.

Only one simple Python3 command (optional -B, shell quotes and backslash-newline)
is recognized. No shell evaluation, wrappers, compound commands or substitutions
are supported. The CLI head is opaque, including $CLI; output and trace establish
identity. Normalized Codex has no channel key: only terminal exact text directly
followed by the first end event can expose the requested FINAL checkpoint.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shlex
from pathlib import Path

from shiploop_hook_contract import locate_invocation

CHECKPOINT = "STARTUP_HANDOFF_CHECKPOINT"
RECEIPT = "shiploop-startup-behavior-receipt.json"
MARKER = re.compile(r"SHIPLOOP-RUN run=(\S+) rev=(\d+) dir=([^\r\n]+)")
PRINT_END = "=== end ShipLoop print ===\n"
VARIABLE = re.compile(r"\$(?:[A-Za-z_][A-Za-z_0-9]*|\{[A-Za-z_][A-Za-z_0-9]*\})\Z")


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


def python_command(command):
    """Return opaque head and argv after it, or None outside the bounded form.

    Punctuation is tokenized so a printed marker, pipe or extra callback cannot
    masquerade as a single startup. Quoted punctuation in the prompt is data.
    """
    if not isinstance(command, str) or "$(" in command or "`" in command:
        return None
    command = command.replace("\\\n", "")
    if "\n" in command:
        return None
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>()")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return None
    if any(token and all(char in ";&|<>()" for char in token) for token in tokens):
        return None
    if not tokens or tokens.pop(0) not in ("python3", "/usr/bin/python3"):
        return None
    if tokens and tokens[0] == "-B":
        tokens.pop(0)
    if len(tokens) < 2 or not tokens[0] or tokens[0].startswith("-"):
        return None
    return tokens[0], tokens[1:]


def startup_options(argv):
    offset = 2 if argv[:2] == ["workspace", "start"] else 1 if argv[:1] == ["init"] else 0
    require(offset, "marker was not returned by init or workspace start")
    # The documented forms use these flags. Unknown flags are an explicit gap,
    # not guessed shell/CLI semantics. No selected-package documentation is read.
    valued = {"--repo", "--prompt", "--workspace-root" if offset == 2 else "--run-dir"}
    options = {}
    rest = argv[offset:]
    while rest:
        flag, equal, value = rest.pop(0).partition("=")
        require(flag in valued and flag not in options and (equal or rest),
                "startup flags are outside the supported documented form")
        options[flag] = value if equal else rest.pop(0)
    require(options.get("--prompt"), "startup request is missing")
    require("--repo" in options, "startup repository is not explicit")
    require(offset == 2 or "--run-dir" in options, "init run directory is not explicit")
    return options


def paired_update(events, index, stop):
    call = events[index]
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
    require(update.get("status") == "completed" and output.get("exit_code") == 0,
            "command did not return a successful complete output")
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
        if intervals:
            require(start["t"] >= intervals[-1][1]["t"], "overlapping session times")
        intervals.append((start, end, ids.pop()))
        previous = hi
    require(previous == len(events) and sessions[0].get("kind") == "first"
            and sessions[0].get("reason") == "start", "first launch or stream coverage is unknown")
    return intervals


def evaluate(work, out, invocation, report):
    require(invocation.get("host") == "codex", "only normalized Codex is verified")
    events_path, sessions_path = out / "events.jsonl", out / "sessions.jsonl"
    events, sessions = rows(events_path), rows(sessions_path)
    intervals = session_intervals(sessions, events)
    start, end, session = intervals[0]
    observation(report, "session", sessions_path, (0, 1), session_id=session,
                events_interval=[start["events_line"], end["events_line"]])

    exposures = []
    for i, event in enumerate(events):
        raw = event.get("rawInput")
        if event.get("type") != "tool_call" or not isinstance(raw, dict):
            continue
        parsed = python_command(raw.get("command"))
        if parsed and (parsed[1][:1] == ["init"] or parsed[1][:2] == ["workspace", "start"]):
            exposures.append((i, parsed))
    require(exposures, "no bounded fresh startup command/output exposure")
    call_index, (_, argv) = exposures[0]
    require(call_index < end["events_line"], "startup did not occur in the first launch")
    options = startup_options(argv.copy())
    update_index, output = paired_update(events, call_index, end["events_line"])
    observation(report, "startup", events_path, (call_index, update_index),
                command=events[call_index]["rawInput"]["command"])
    markers = MARKER.findall(output)
    require(len(markers) == 1, "startup run marker is missing or ambiguous")
    run_id, revision, raw_root = markers[0]
    root = Path(raw_root).resolve()
    require(root.is_relative_to(work) and root != work, "startup run is outside checked workdir")
    for flag, expected in (("--repo", work), ("--run-dir", root)):
        value = options.get(flag)
        if value and not VARIABLE.fullmatch(value):
            require((work / value).resolve() == expected, f"startup {flag} disagrees with artifacts")
    workspace_root = options.get("--workspace-root")
    if workspace_root and not VARIABLE.fullmatch(workspace_root):
        require(root.is_relative_to((work / workspace_root).resolve()), "workspace root disagrees with artifacts")
    trace_paths = []
    for directory, folders, files in os.walk(work, followlinks=False):
        folders[:] = [name for name in folders if not (Path(directory) / name).is_symlink()]
        if "trace.jsonl" in files:
            trace_paths.append((Path(directory) / "trace.jsonl").resolve())
    trace_path = root / "trace.jsonl"
    require(trace_paths == [trace_path], "missing or multiple candidate run traces under checked workdir")
    trace = rows(trace_path)
    require(all(row.get("v") == 1 and number(row.get("ts")) for row in trace), "unverified run trace schema")
    require(all(trace[i - 1]["ts"] <= trace[i]["ts"] for i in range(1, len(trace))),
            "trace time order is inconsistent")
    first = trace[0]
    action = first.get("action")
    require(first.get("kind") == "packet" and first.get("stage") == "intake"
            and isinstance(action, str) and action and str(first.get("rev")) == revision,
            "first trace row is not the exposed first intake packet")
    path, text = packet_text(root, first)
    require(text in output and MARKER.findall(text) == markers, "startup output does not expose the complete first print")
    observation(report, "first_packet", path, run_id=run_id, action=action, trace=str(trace_path) + ":1")
    commands = [(i, row) for i, row in enumerate(trace) if row.get("kind") == "command"]
    require(commands, "startup command trace is missing")
    startup_index, startup = commands[0]
    require(startup.get("verb") == argv[0] and startup.get("exit") == 0
            and startup.get("stage") == [None, "intake"] and startup.get("cursor") == [None, action]
            and startup.get("rev") == [None, first.get("rev")]
            and start["t"] <= first["ts"] <= startup["ts"] < end["t"]
            and not startup.get("accepted"), "fresh startup and first trace command cannot be joined")
    observation(report, "startup_trace", trace_path, (startup_index,))

    checkpoints = [i for i, event in enumerate(events) if event.get("type") == "text"
                   and event.get("data") == CHECKPOINT + "\n"]
    require(len(checkpoints) == 1, "exact checkpoint is missing or ambiguous")
    checkpoint = checkpoints[0]
    observation(report, "checkpoint", events_path, (checkpoint,))
    require(call_index < update_index < checkpoint < end["events_line"], "checkpoint/startup launch order is unknown")
    early_tools = [i for i in range(call_index + 1, checkpoint) if events[i].get("type") == "tool_call"]
    observation(report, "before_checkpoint_tools", events_path, early_tools)
    require(not early_tools, "tool call/callback precedes the checkpoint", "fail")
    require(not any(event.get("type") in ("text", "thought") and event.get("data")
                    for event in events[update_index + 1:checkpoint]),
            "additional text/thought prevents unique immediate checkpoint exposure")
    ends = [i for i in range(end["events_line"]) if events[i].get("type") == "end"]
    require(ends and ends[0] == checkpoint + 1 and events[ends[0]].get("sessionId") == session
            and events[ends[0]].get("stopReason") == "end_turn",
            "checkpoint is not terminal text at the actual first Codex turn end")
    observation(report, "first_turn_end", events_path, (ends[0],))

    decisions_path = out / "home/.local/state/shiploop/keepalive/decisions.log"
    decisions = rows(decisions_path)
    session_hash = hashlib.sha256(session.encode()).hexdigest()[:12]
    require(all(number(row.get("at")) for row in decisions), "decision timestamp is missing")
    require(all(decisions[i - 1]["at"] <= decisions[i]["at"] for i in range(1, len(decisions))),
            "decision time order is inconsistent")
    stops = [(i, row) for i, row in enumerate(decisions)
             if start["t"] <= row["at"] <= end["t"] and row.get("decision") != "release"]
    require(stops, "first stop decision for checkpoint session is missing")
    require(all(row.get("host") == "codex" and row.get("session") == session_hash for _, row in stops),
            "mixed or unidentified stop sessions in checkpoint launch")
    decision_index, decision = stops[0]
    require(startup["ts"] < decision["at"], "first stop cannot be ordered after startup")
    observation(report, "first_stop", decisions_path, (decision_index,), session_hash=session_hash,
                decision=decision.get("decision"), why=decision.get("why"))
    require(decision.get("decision") != "allow", "first checkpoint stop allowed termination: "
            + str(decision.get("why")), "fail")
    require(decision.get("decision") == "continue", "unverified first stop decision")
    hooks = [(i, row) for i, row in enumerate(trace) if row.get("kind") == "hook"
             and row.get("hook") == "stop"]
    require(hooks and hooks[0][1].get("session") == session_hash, "first stop trace has missing/mixed session identity")
    hook_index, hook = hooks[0]
    observation(report, "continue_hook", trace_path, (hook_index,), session_hash=hook.get("session"))
    require(hook.get("host") == "codex" and hook.get("decision") == "continue"
            and hook.get("why") == decision.get("why") and startup_index < hook_index
            and decision["at"] - 0.0005 <= hook["ts"] <= end["t"]
            and (len(stops) == 1 or hook["ts"] < stops[1][1]["at"]),
            "first decision and first run hook cannot be uniquely correlated")

    accepted = [(i, row, entry) for i, row in commands for entry in row.get("accepted", [])
                if entry.get("action") == action]
    observation(report, "intake_acceptance", trace_path, [i for i, _, _ in accepted], action=action)
    require(len(accepted) <= 1, "duplicate accepted first intake completion", "fail")
    require(accepted, "accepted first intake completion is missing")
    accepted_index, completed, entry = accepted[0]
    require(hook_index < accepted_index, "intake accepted before first continue stop", "fail")
    require(completed.get("verb") == "complete" and completed.get("action") == action
            and completed.get("exit") == 0 and entry.get("stage") == "intake" and entry.get("outcome") == "done",
            "acceptance is not a successful completion of the first intake action", "fail")
    replays = [i for i, row in commands if startup_index < i < accepted_index
               and row.get("verb") in ("next", "init", "workspace", "resume", "restart", "reinit")]
    observation(report, "pending_replays", trace_path, replays)
    require(not replays, "next/reinit/restart while first intake remains pending", "fail")
    for i, (launched, _, _) in enumerate(intervals[1:], 1):
        if launched.get("reason") == "resume-loop":
            observation(report, "outer_resume", sessions_path, (i * 2,))
            require(launched["t"] >= completed["ts"], "outer resume-loop started with intake pending", "fail")
            require(launched["t"] != completed["ts"], "outer resume and acceptance timestamps tie")

    # Join the accepted callback to the actual continuing tool call through its
    # action and the next packet printed by that command, not a later result.json.
    next_packets = [(i, row) for i, row in enumerate(trace[:accepted_index])
                    if row.get("kind") == "packet" and row.get("action") == completed.get("cursor", [None])[-1]]
    require(next_packets, "accepted callback's returned packet is missing")
    next_index, next_packet = next_packets[-1]
    require(hook_index < next_index < accepted_index and hook["ts"] <= next_packet["ts"] <= completed["ts"] <= end["t"],
            "accepted callback packet cannot be ordered in the checkpoint session")
    next_path, next_text = packet_text(root, next_packet)
    callbacks = []
    for i, event in enumerate(events[:end["events_line"]]):
        parsed = python_command((event.get("rawInput") or {}).get("command")) if event.get("type") == "tool_call" else None
        if not parsed or parsed[1][:1] != ["complete"]:
            continue
        args = parsed[1]
        if not any(args[n:n + 2] == ["--action", action] or args[n] == "--action=" + action for n in range(len(args))):
            continue
        returned, callback_output = paired_update(events, i, end["events_line"])
        if next_text in callback_output:
            callbacks.append((i, returned))
    require(len(callbacks) == 1, "accepted callback tool exposure is missing or ambiguous")
    called, returned = callbacks[0]
    observation(report, "continued_callback", events_path, (called, returned), packet=str(next_path))
    replay_calls = []
    for i in range(update_index + 1, returned):
        event = events[i]
        parsed = python_command((event.get("rawInput") or {}).get("command")) if event.get("type") == "tool_call" else None
        if parsed and (parsed[1][0] in ("next", "init", "resume", "restart", "reinit")
                       or parsed[1][:2] == ["workspace", "start"]):
            replay_calls.append(i)
    observation(report, "pending_replay_calls", events_path, replay_calls)
    require(not replay_calls, "next/reinit/restart tool call before intake acceptance", "fail")
    require(ends[0] < called < returned < end["events_line"],
            "intake completion did not continue in the checkpoint's original session", "fail")
    require(not any(events[i].get("type") == "available_commands" for i in range(ends[0] + 1, returned)),
            "continuation session identity is ambiguous")


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
