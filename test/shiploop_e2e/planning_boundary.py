"""Corroborate Plan Improve ownership and the stop recorded by the repository harness.

The proof supports normalized Codex command_execution requests and results. The
command grammar is one literal invocation, optionally through one absolute
/bin/{sh,bash,zsh} -c/-lc wrapper with a single-quoted body. Python may be named
by its literal python3[.minor] name or absolute path. Only the child done route
permits one literal stdin redirection. No expansions, escapes, assignments,
additional commands or script bodies are interpreted.
"""
from __future__ import annotations

from bisect import bisect_right
from hashlib import sha256
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shlex
import stat

import metrics

_HELPER = Path(__file__).resolve().parents[2] / "skills/shiploop-e2e-audit/harness/planning_trace.py"
_SPEC = importlib.util.spec_from_file_location("shiploop_e2e_planning_trace", _HELPER)
planning_trace = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(planning_trace)

_WRAPPER = re.compile(r"/bin/(?:sh|bash|zsh) +-(?:l)?c +'([^'\r\n]*)'")
_SHELL = re.compile(r"""(?:[a-zA-Z0-9_./:@+=, -]|'[a-zA-Z0-9_./:@+=, -]*'|"[a-zA-Z0-9_./:@+=, -]*")*""")
_PYTHON = re.compile(r"(?:/[a-zA-Z0-9_./ -]+/)?python3(?:\.\d+)?")
_ACTION = re.compile(r"nav-[a-f0-9]{32}")
_KNOWN_EVENTS = ("available_commands", "text", "thought", "end", "tool_call", "tool_call_update")
_RECEIPT_LIMIT = 4 * 1024 * 1024


def _mapping(value) -> dict:
    return value if isinstance(value, dict) else {}


def _digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def _file(path: Path, limit: int) -> bytes:
    """A bounded, stable regular file below a caller-bound directory."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError("unsupported evidence file")
        data = handle.read(limit + 1)
        after = os.fstat(handle.fileno())
        named = path.lstat()
        if (len(data) != before.st_size or before.st_mtime_ns != after.st_mtime_ns
                or before.st_ctime_ns != after.st_ctime_ns
                or (named.st_dev, named.st_ino) != (before.st_dev, before.st_ino)):
            raise ValueError("evidence changed during read")
        return data


def registered_cli(out: Path, run_dir: Path) -> Path | None:
    """Recover the installed CLI locator from a recorded normalized Codex slice."""
    try:
        invocation = planning_trace._parse_object(_file(out / "invocation.json", _RECEIPT_LIMIT).decode("utf-8"))
    except (OSError, ValueError, RecursionError):
        return None
    plugin = _mapping(invocation.get("plugin"))
    install = plugin.get("path")
    if (invocation.get("kind") != "step-slice" or invocation.get("host") != "codex"
            or _mapping(invocation.get("seeded")).get("run_dir") != str(run_dir)
            or plugin.get("pass") is not True or not isinstance(install, str) or not Path(install).is_absolute()):
        return None
    return Path(install) / "skills/shiploop/scripts/shiploop"


def _shell(command: str) -> tuple[list[str], str | None] | None:
    body = command.strip(" ")
    wrapper = _WRAPPER.fullmatch(body)
    if wrapper:
        body = wrapper[1]
    argv_text, redirect, stdin_text = body.partition("<")
    if not _SHELL.fullmatch(argv_text) or not _SHELL.fullmatch(stdin_text):
        return None
    argv, stdin = shlex.split(argv_text), shlex.split(stdin_text)
    if not argv or (redirect and len(stdin) != 1):
        return None
    return argv, stdin[0] if redirect else None


def _shiploop(parsed, cli: Path, verb: str, flags: dict) -> bool:
    if parsed is None:
        return False
    argv, stdin = parsed
    if _PYTHON.fullmatch(argv[0]):
        argv = argv[1:]
    if stdin is not None or argv[:2] != [str(cli), verb]:
        return False
    args = iter(argv[2:])
    found = {}
    for token in args:
        key, equal, value = token.partition("=")
        if not equal:
            value = next(args, None)
        if key not in flags or key in found or value != flags[key]:
            return False
        found[key] = value
    return found == flags


def _number(value) -> bool:
    return type(value) is int or (type(value) is float and math.isfinite(value))


def _launches(rows: list[dict], count: int, stamps: dict[int, float], run_dir: Path, cli: Path) -> list[int] | None:
    """Verify adjacent closed launch spans cover exactly the retained host stream."""
    if not rows or len(rows) % 2:
        return None
    starts = []
    next_line = 0
    previous_end = -math.inf
    for offset in range(0, len(rows), 2):
        first, last = (row["record"] for row in rows[offset:offset + 2])
        n = len(starts) + 1
        start, end = first.get("events_line"), last.get("events_line")
        opened, closed = first.get("t"), last.get("t")
        told = first.get("told")
        if (first.get("row") != "start" or last.get("row") != "end"
                or type(first.get("n")) is not int or first["n"] != n
                or type(last.get("n")) is not int or last["n"] != n or first.get("host") != "codex"
                or type(start) is not int or type(end) is not int or not next_line == start <= end <= count
                or not _number(opened) or not _number(closed) or not previous_end <= opened <= closed
                or not isinstance(last.get("status"), str) or type(last.get("returncode")) is not int
                or (told is not None and (_mapping(told).get("cli") != str(cli)
                                          or _mapping(told).get("run_dir") != str(run_dir)))):
            return None
        if any(not opened <= stamps[line] <= closed for line in range(start + 1, end + 1) if line in stamps):
            return None
        starts.append(start)
        next_line = end
        previous_end = closed
    return starts if next_line == count else None


def _stamps(rows: list[dict], events: dict[int, dict]) -> dict[int, float] | None:
    expected = [line for line, event in events.items() if event.get("type") not in ("text", "thought")]
    stamps = {}
    previous = -math.inf
    for row in rows:
        record = row["record"]
        line, when = record.get("line"), record.get("t")
        if type(line) is not int or not _number(when) or when < previous or line + 1 in stamps:
            return None
        stamps[line + 1] = previous = when
    return stamps if list(stamps) == expected else None


def _facts(record: dict, verb: str, action: str, stages: list[str]) -> bool:
    return (record.get("verb") == verb and record.get("action") == action and record.get("stage") == stages
            and type(record.get("exit")) is int and record["exit"] == 0 and record.get("status") == "active"
            and not any(record.get(key) for key in ("held", "check_only", "crashed", "error")))


def _command_rows(trace: list[dict]) -> list[dict]:
    rows = []
    for row in trace:
        record = row["record"]
        if type(record.get("v")) is not int or record["v"] != 1 or not _number(record.get("ts")):
            raise ValueError("unknown engine trace record version or timestamp")
        kind = record.get("kind")
        if kind == "command":
            if (not isinstance(record.get("verb"), str) or type(record.get("exit")) is not int
                    or any(not isinstance(record.get(key), list) or len(record[key]) != 2
                           for key in ("rev", "stage", "cursor"))
                    or any(value is not None and (type(value) is not int or value < 0) for value in record["rev"])
                    or any(value is not None and not isinstance(value, str)
                           for key in ("stage", "cursor") for value in record[key])
                    or ("accepted" in record and (not isinstance(record["accepted"], list)
                                                 or any(not isinstance(item, dict) for item in record["accepted"])))):
                raise ValueError(f"malformed engine command at trace line {row['line']}")
            rows.append(row)
        elif kind not in ("packet", "hook"):
            raise ValueError(f"unknown engine record at trace line {row['line']}")
    return rows


def _identity(call: metrics.CallOccurrence, result: metrics.CallResult | None) -> dict:
    launch, line, block = call.key
    return {"launch": launch, "start_line": line, "block": block, "tool_call_id": call.tool_id,
            "result_line": result.line if result else None, "result_block": result.block if result else None,
            "tool": call.tool, "command_sha256": _digest(call.command.encode("utf-8", errors="surrogatepass"))
            if call.command else None}


def _outputs(log: metrics.ToolLog, events: dict) -> tuple[list[tuple], list[str]]:
    """Normalized successful shell command pairs only. A result repeats the exact request command."""
    commands, problems = [], []
    for key, call in log.occurrences.items():
        result = log.occurrence_results.get(key)
        request = events[key[1]]
        if (not isinstance(request.get("rawInput"), dict) or not isinstance(request.get("toolName"), str)
                or not request["toolName"] or request.get("status") != "pending"):
            problems.append(f"malformed tool request at event line {key[1]}")
            continue
        if not result or key in log.ambiguous_occurrences:
            continue
        output = events[result.line]["rawOutput"]
        expected = call.tool == "run_terminal_command"
        if not isinstance(output.get("type"), str) or (output["type"] == "command_execution") != expected:
            problems.append(f"tool result type differs at event line {result.line}")
        elif expected:
            shown, exit_code = output.get("output_for_prompt"), output.get("exit_code")
            if (not call.command or request["rawInput"].get("command") != call.command
                    or output.get("command") != call.command
                    or not isinstance(shown, str) or type(exit_code) is not int):
                problems.append(f"shell result lacks matching command/exit/output at event line {result.line}")
            elif result.status == "completed" and exit_code == 0 and not output.get("truncated"):
                parsed = _shell(call.command)
                if parsed is not None:
                    commands.append((call, result, parsed, shown))
    return commands, problems


def _brackets(command: tuple, row: dict, stamps: dict[int, float]) -> bool:
    call, result, _, _ = command
    return call.t <= row["record"]["ts"] <= stamps[result.line]


def _packet_output(shown: str, root: Path, run_id: str, cursor: str, revision: int) -> bool:
    lines = shown.split("\n")
    return (f"ShipLoop navigator | prepare | revision {revision}" in lines
            and f"Keepalive marker: SHIPLOOP-RUN run={run_id} rev={revision} dir={root}" in lines
            and any(line.startswith(f"Full packet: {root / 'packets' / (cursor + '.md')} - ") for line in lines))


def _competing_parent(log: metrics.ToolLog, parent: tuple, accept: dict, stamps: dict[int, float],
                      cli: Path, flags: dict) -> bool:
    selected, terminal, _, _ = parent
    when = accept["record"]["ts"]
    for key, call in log.occurrences.items():
        if key == selected.key or call.tool != "run_terminal_command" or call.t > when:
            continue
        result = log.occurrence_results.get(key)
        if result is not None and stamps[result.line] < when:
            continue
        parsed = _shell(call.command)
        if _shiploop(parsed, cli, "complete", flags):
            return True
        if (parsed is None and key[1] < terminal.line and (result is None or result.line > selected.key[1])):
            return True
    return False


def _child_proof(commands: list[tuple], trace: list[dict], stamps: dict[int, float], root: Path, cli: Path,
                 plan: str, improve: str, receipt: dict, acceptance: dict, parent: tuple | None) -> list[dict]:
    workspace = root.parent / "worktree"
    runtime = str(cli.parents[2] / "improve/runtime/until-loop/scripts/until_loop_ephemeral.py")
    identities = _mapping(receipt.get("identities"))
    if (_mapping(receipt.get("skill")).get("runtime_cli") != runtime
            or receipt.get("workspace") != str(workspace) or receipt.get("runtime_phase") != "complete"):
        return []
    child_dir = workspace / ".shiploop-improve" / ("plan-" + plan[-8:])
    rev = acceptance["record"]["rev"][0]
    prior_passes = [row for row in trace if row["line"] < acceptance["line"]
                    and _facts(row["record"], "improve-pass", improve, ["improve", "improve"])
                    and row["record"]["rev"] == [rev, rev] and row["record"]["cursor"] == [improve, improve]]
    pass_commands = [cmd for cmd in commands if _shiploop(cmd[2], cli, "improve-pass",
                                                         {"--run-dir": str(root), "--action": improve})]
    passes = []
    for row in prior_passes:
        matched = [cmd for cmd in pass_commands if _brackets(cmd, row, stamps)]
        if len(matched) == 1 and sum(_brackets(matched[0], other, stamps) for other in prior_passes) == 1:
            passes.append((matched[0], row["line"]))

    matches = []
    for call, result, (argv, stdin), output in commands:
        if (len(argv) != 6 or not _PYTHON.fullmatch(argv[0]) or argv[1:4] != [runtime, "done", "--state"]
                or stamps[result.line] > acceptance["record"]["ts"]
                or (parent is not None and result.line >= parent[0].key[1])):
            continue
        try:
            packet_bytes = output.encode("utf-8")
            terminal_sha = _digest(packet_bytes)
            if terminal_sha != identities.get("terminal_packet_sha256"):
                continue
            packet = planning_trace._parse_object(output)
            progress = _mapping(packet.get("progress")).get("action_number")
            request = _mapping(packet.get("context")).get("request")
            state_path = Path(argv[4])
            action = re.fullmatch(r"--action=[a-zA-Z0-9_-]+:([1-9][0-9]*)", argv[5])
            if (packet.get("status") != "complete" or packet.get("state_file") != str(state_path)
                    or state_path.parent != root / "until-loop"
                    or not re.fullmatch(r"innerloop-[a-zA-Z0-9_-]+\.json", state_path.name)
                    or packet.get("workspace") != str(workspace)
                    or packet.get("receipt") != str(child_dir / "packet.json")
                    or not isinstance(request, str)
                    or request.split("\n", 1)[0] != f"ShipLoop standalone Improve binding: {receipt['binding_id']}"
                    or type(progress) is not int or not action or action[1] != str(progress)
                    or any(packet.get(key) is not None for key in ("next_argv", "done_argv", "report_schema"))):
                continue
            report_path = child_dir / "reviews" / f"report-{progress}.json"
            if stdin != str(report_path):
                continue
            rendered = (argv, stdin)
            bound = [(cmd, line) for cmd, line in passes if cmd[1].line < call.key[1]
                     and f"Pass {progress} of the plan review is recorded." in cmd[3]
                     and sum(_shell(line) == rendered for line in cmd[3].split("\n") if " < " in line) == 1]
            if len(bound) != 1:
                continue
            if any(path.is_symlink() for path in (workspace, child_dir.parent, child_dir, report_path.parent)):
                continue
            report_bytes = _file(report_path, _RECEIPT_LIMIT)
            report = planning_trace._parse_object(report_bytes.decode("utf-8"))
            canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
            if report != packet.get("last_report") or _digest(canonical.encode("utf-8")) != identities.get("last_report_sha256"):
                continue
        except (OSError, ValueError, RecursionError):
            continue
        matches.append({**_identity(call, result), "kind": "bound-child-done", "plan_action": plan,
                        "improve_action": improve, "runtime_cli": runtime, "child_state": str(state_path),
                        "child_action": argv[5].split("=", 1)[1], "report": str(report_path),
                        "report_sha256": _digest(report_bytes), "terminal_sha256": terminal_sha,
                        "pass_result_line": bound[0][0][1].line, "pass_trace_line": bound[0][1]})
    return matches


def analyze(out: Path, run_dir: Path, cli: Path, *, run_id: str | None = None,
            tools: metrics.ToolLog | None = None) -> dict:
    """Read the registered run and return proved call ownership and recorded-stop status.

    Corrections identify calls independently of the stop verdict. A caller may
    supply its ToolLog; its occurrence projection must agree with the strict
    sources. Established covers the retained stream and the engine trace, with
    no guarantee about unlogged effects or work outside the observed process.
    """
    out, root, cli = Path(out), Path(run_dir), Path(cli)
    sources = {"out": str(out), "run_dir": str(root), "cli": str(cli), "run_id": run_id, "sha256": {}}
    reasons, corrections, later, overlapping = [], [], [], []
    diagnostic = {"schema": "shiploop-planning-boundary/v1", "status": "incomplete",
                  "reasons": reasons, "sources": sources, "corrections": corrections,
                  "acceptance": None, "later_calls": later, "overlapping_calls": overlapping}

    def incomplete(reason: str) -> dict:
        reasons.append(reason)
        return diagnostic

    if not all(path.is_absolute() for path in (out, root, cli)):
        return incomplete("registered output, run and CLI locators must be absolute")
    if tuple(cli.parts[-4:]) != ("skills", "shiploop", "scripts", "shiploop"):
        return incomplete("registered CLI has no supported installed package locator")
    inputs = {"events": out / "events.jsonl", "timeline": out / "timeline.jsonl",
              "sessions": out / "sessions.jsonl", "trace": root / "trace.jsonl"}
    raw = {}
    for name, path in inputs.items():
        parsed = planning_trace.read_trace(path)
        sources["sha256"][name] = parsed["sha256"]
        if parsed["status"] != "ok":
            reasons.append(f"{name} {parsed['status']}: {parsed['reason']}")
        raw[name] = parsed["rows"]
    if reasons:
        return diagnostic

    try:
        state_bytes = _file(root / "state.md", planning_trace.TRACE_LIMIT)
        sources["sha256"]["state"] = _digest(state_bytes)
        state_blocks = metrics.STATE_BLOCK.findall(state_bytes.decode("utf-8"))
        if len(state_blocks) != 1:
            return incomplete("saved engine state must have one state record")
        state = planning_trace._parse_object(state_blocks[0])
        trace = _command_rows(raw["trace"])
    except (OSError, ValueError, RecursionError) as exc:
        return incomplete(f"invalid engine evidence: {exc}")

    stored_id = state.get("run_id")
    if (not isinstance(stored_id, str) or not _ACTION.fullmatch(stored_id)
            or (run_id is not None and run_id != stored_id)):
        return incomplete("saved engine state does not identify the registered run")
    sources["run_id"] = stored_id
    events = {row["line"]: row["record"] for row in raw["events"]}
    if any(event.get("type") not in _KNOWN_EVENTS for event in events.values()):
        return incomplete("unsupported event in the normalized host stream")
    stamps = _stamps(raw["timeline"], events)
    if stamps is None:
        return incomplete("host timeline does not cover the normalized event stream in source order")
    starts = _launches(raw["sessions"], len(events), stamps, root, cli)
    if starts is None:
        return incomplete("launch receipts do not bind a closed normalized Codex stream")

    log = metrics.ToolLog()
    for line, event in events.items():
        log.observe(event, stamps.get(line), line - 1, bisect_right(starts, line - 1))
    if tools is not None:
        if (tools.occurrences != log.occurrences or tools.occurrence_results != log.occurrence_results
                or tools.occurrence_issues != log.occurrence_issues
                or tools.ambiguous_occurrences != log.ambiguous_occurrences):
            return incomplete("provided tool log does not match the registered event stream")
        log = tools
    commands, problems = _outputs(log, events)
    reasons.extend(problems)
    reasons.extend(f"event line {line}: {issue}" for line, issue in log.occurrence_issues)
    unresolved = [key[1] for key in log.occurrences if key not in log.occurrence_results]
    if unresolved:
        reasons.append("tool calls lack terminal results at event lines " + ", ".join(map(str, unresolved)))

    history = state.get("history")
    if not isinstance(history, list) or any(not isinstance(row, dict) for row in history):
        return incomplete("saved engine history is unavailable")
    accepted = [(i, row) for i, row in enumerate(history) if row.get("stage") == "plan" and row.get("outcome") == "done"]
    if len(accepted) != 1:
        return incomplete("one accepted done Plan is required")
    index, accepted_plan = accepted[0]
    plan = accepted_plan.get("action")
    receipt = _mapping(_mapping(state.get("improve_results")).get(plan)) if isinstance(plan, str) else {}
    improve = receipt.get("improve_action")
    if (not isinstance(plan, str) or not _ACTION.fullmatch(plan) or not isinstance(improve, str)
            or not _ACTION.fullmatch(improve) or improve == plan or receipt.get("action_id") != plan
            or accepted_plan.get("workitem") is not None
            or _mapping(_mapping(state.get("accepted")).get(plan)).get("outcome") != "done"
            or receipt.get("stage") != "plan" or receipt.get("binding_id") != f"{stored_id}/{plan}"
            or receipt.get("runtime_phase") != "complete"):
        return incomplete("the accepted Plan lacks its matching completed Improve binding")
    expected = [{"action": plan, "stage": "plan", "item": None, "outcome": "done"}]
    transitions = [row for row in trace if _facts(row["record"], "complete", improve, ["improve", "prepare"])
                   and row["record"].get("accepted") == expected and row["record"]["cursor"][0] == improve
                   and isinstance(row["record"]["cursor"][1], str) and _ACTION.fullmatch(row["record"]["cursor"][1])
                   and row["record"]["cursor"][1] not in (plan, improve)
                   and all(type(rev) is int for rev in row["record"]["rev"])
                   and row["record"]["rev"][1] == row["record"]["rev"][0] + 1]
    if len(transitions) != 1:
        return incomplete("the engine trace lacks one genuine Plan Improve acceptance transition")
    accept = transitions[0]
    rev_before, revision = accept["record"]["rev"]
    _, cursor = accept["record"]["cursor"]
    diagnostic["acceptance"] = {"trace_line": accept["line"], "plan_action": plan, "improve_action": improve,
                                "revision_before": rev_before, "revision_after": revision, "prepare_action": cursor}

    producers = [row for row in trace if row["line"] < accept["line"]
                 and _facts(row["record"], "complete", plan, ["plan", "improve"])
                 and row["record"]["cursor"] == [plan, improve] and not row["record"].get("accepted")
                 and all(type(rev) is int for rev in row["record"]["rev"])
                 and row["record"]["rev"][1] == row["record"]["rev"][0] + 1]
    if len(producers) != 1:
        return incomplete("the engine trace lacks one matching Plan producer transition")
    producer = producers[0]
    previous = producer["record"]["rev"][1]
    previous_ts = producer["record"]["ts"]
    for row in trace:
        if producer["line"] < row["line"] <= accept["line"]:
            record = row["record"]
            before, after = record["rev"]
            if (record["ts"] < previous_ts or before != previous or type(after) is not int
                    or after not in (before, before + 1) or record["stage"][0] != "improve"
                    or record["cursor"][0] != improve
                    or (row is not accept and (record["stage"][1] != "improve" or record["cursor"][1] != improve
                                               or record.get("accepted")))):
                return incomplete("the engine trace has a transition gap within Plan Improve")
            previous = after
            previous_ts = record["ts"]

    flags = {"--run-dir": str(root), "--action": improve}
    if "final_result" in _mapping(receipt.get("submission")) or "final_result" in _mapping(receipt.get("receipt")):
        flags["--final-result"] = str(root / "inbox" / f"{plan}-final-result.md")
    parents = [command for command in commands if _shiploop(command[2], cli, "complete", flags)
               and _brackets(command, accept, stamps)]
    parent = None
    if (len(parents) == 1 and _packet_output(parents[0][3], root, stored_id, cursor, revision)
            and not _competing_parent(log, parents[0], accept, stamps, cli, flags)):
        parent = parents[0]
        corrections.append({**_identity(parent[0], parent[1]), "kind": "parent-complete",
                            "plan_action": plan, "improve_action": improve, "trace_line": accept["line"],
                            "final_result": flags.get("--final-result")})
    else:
        reasons.append("the accepting callback has no unique exact successful host request/result")

    children = _child_proof(commands, trace, stamps, root, cli, plan, improve, receipt, accept, parent)
    if len(children) == 1:
        corrections.extend(children)
    else:
        reasons.append("the bound Until Loop completion has no unique exact report and terminal receipt proof")

    later_trace = [row["line"] for row in trace if row["line"] > accept["line"]
                   and row["record"]["stage"][0] not in (None, "plan", "improve")
                   and isinstance(row["record"]["rev"][0], int) and row["record"]["rev"][0] >= revision]
    diagnostic["later_trace_lines"] = later_trace
    if later_trace or history[index + 1:]:
        reasons.append("the engine recorded work after the accepted Plan")
        diagnostic["status"] = "overshoot"
    if any(row["line"] > accept["line"] for row in trace) and not later_trace:
        reasons.append("an engine command follows the accepting trace row with uncertain ownership")
    if any(row["line"] > accept["line"] and row["record"]["kind"] == "packet" for row in raw["trace"]):
        reasons.append("an unbound engine packet follows the accepting trace row")
    if parent is not None:
        start, end = parent[0].key[1], parent[1].line
        prepare_packets = [row["line"] for row in raw["trace"] if producer["line"] < row["line"] < accept["line"]
                           and row["record"].get("kind") == "packet" and row["record"].get("stage") == "prepare"
                           and row["record"].get("action") == cursor and row["record"].get("rev") == revision
                           and stamps[start] <= row["record"]["ts"] <= accept["record"]["ts"]]
        if len(prepare_packets) == 1:
            diagnostic["acceptance"]["prepare_packet_trace_line"] = prepare_packets[0]
        else:
            reasons.append("the accepting callback lacks a unique matching Prepare packet trace")
        for key, call in log.occurrences.items():
            result = log.occurrence_results.get(key)
            if key[1] > end:
                later.append(_identity(call, result))
            elif key != parent[0].key and (result is None or result.line > start):
                overlapping.append(_identity(call, result))
        if later:
            reasons.append("recorded tool calls follow the accepting callback result")
            diagnostic["status"] = "overshoot"
        if overlapping:
            reasons.append("tool activity overlaps the accepting callback or remains unresolved")
        if parent[0].key[0] != len(starts):
            reasons.append("a later host launch follows the accepting callback")

    if (state.get("stage") != "prepare" or _mapping(state.get("action")).get("id") != cursor
            or state.get("revision") != revision or state.get("status") != "active"
            or state.get("active_improve") or state.get("completed_work_items")):
        reasons.append("saved engine position differs from the recorded Prepare entry")
    if not reasons:
        diagnostic["status"] = "established"
    return diagnostic
