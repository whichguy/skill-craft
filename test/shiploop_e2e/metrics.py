"""Where a ShipLoop E2E run spent its turns, tokens and time.

Reads the output directory the runner wrote: the host event stream
(events.jsonl), its arrival times (timeline.jsonl, one line per non-streaming
event: {"line": n, "t": epoch}) and the ShipLoop run directory. Grok events
carry no timestamps, so stage attribution uses the times the runner stamped
and the times ShipLoop wrote each accepted stage result.

Never returns packet text: ShipLoop CLI output is reduced to the failing line.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re

SHIPLOOP_COMMAND = re.compile(r"shiploop\S*\s+(?P<verb>complete|next|improve-[\w-]+|init|workspace|lint|resume|pause)\b")
# Model-written glue (SPEC S-4, S-5): shell commands that do a mechanical step
# ShipLoop owns. Defined by ShipLoop's own paths and verbs, never by product
# tools, so it means the same thing for every case. A heuristic signal: the
# matching commands are listed so a reviewer can confirm them.
# ShipLoop-owned: its run directory, Improve receipts and its own record files.
# The execution worktree under a workspace root is product space, not ShipLoop's.
SHIPLOOP_OWNED = re.compile(r"(?:\.shiploop-improve|/\.shiploop(?:/|[\"'\s]|$)|\.shiploop-runs/[^/\s\"']+/run\b|"
                            r"/run/(?:state\.md|results|packets|tests|quality)|until-loop|"
                            r"/(?:packet|start)\.json\b|/parent-return\.md\b|-terminal\.json\b)")
# Host tools that put a question to a person (Grok ask_user_question, Claude AskUserQuestion).
ASK_PERSON = re.compile(r"ask_?user", re.I)
# Files the packets ask the model itself to write (its result, evidence notes, Improve
# review evidence, an Improve opening or commit message): writing them is the step, not glue.
# A write to a literal /tmp path (redirect, tee, cp or mv target): shared with every other run (plan P13).
TMP_WRITE = re.compile(r"(?:>>?|\btee\s+(?:-a\s+)?|\b(?:cp|mv)\s+(?:-\S+\s+)*\S+\s+)\s*[\"']?(/tmp/[^\s\"';|&)]+)")


WRITE_TOOL = re.compile(r"write|edit|replace|create", re.I)


def tmp_writes(command: str) -> list[str]:
    """The literal /tmp paths a shell command writes (heredoc bodies are documents, not commands)."""
    return TMP_WRITE.findall(shell_text(command))


MODEL_INPUT = re.compile(r"/inbox/|/run/(?:notes|evidence|scratch)(?:/|$|[\"'\s])|/reviews(?:/|$|[\"'\s])|opening\.md|"
                         r"commit-message\.md|\.shiploop-improve/[^/\s\"']+/nav-[0-9a-f]+/?(?:[\"'\s]|$)")
# `git ... commit|add` as a command: at the start of a line or after ; && || |, optionally after VAR=value.
GLUE_COMMIT = re.compile(r"(?:^|[;&|]\s*)(?:\w+=\S*\s+)*git\b[^\n;&|]*\s(?:commit|add)\b", re.M)
# A redirect needs a path-like target (a slash, dot, $ or ~), so a `>` in prose inside a quoted string ("... > 0 must ...") is not a write.
GLUE_WRITE = re.compile(r"(?:>>?(?=\s+[\"']?[^\s\"']*[/.$~])|\btee\b|\bcp\b|\bmv\b|\bmkdir\b|\brm\b)\s+[^\n;&|]*")
GLUE_CONTRACT = re.compile(r"exit_condition|repeat_condition|required_trivial_reviews")
# Reading ShipLoop's contract is fine; writing one, or feeding one to the Until Loop runtime, is glue.
CONTRACT_WRITE = re.compile(r"json\.dump\(|write_text|open\([^)]*['\"][wa]|[^-<>=]>\s*[^\s=&]|until[-_]loop")


HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n.*?\n\s*\1\s*(?:\n|$)", re.S)


def shell_text(command: str) -> str:
    """The command with heredoc bodies removed: words inside a document are not commands."""
    return HEREDOC.sub("\n", command)


def glue_reasons(command: str) -> list[str]:
    """Why a shell command counts as model-written glue ([] when it does not)."""
    reasons = []
    shell = shell_text(command)
    if GLUE_COMMIT.search(shell):
        reasons.append("git commit/add by the model")
    if any(SHIPLOOP_OWNED.search(m.group(0)) and not MODEL_INPUT.search(m.group(0))
           for m in GLUE_WRITE.finditer(shell)):
        reasons.append("shell write into a ShipLoop-owned path")
    if GLUE_CONTRACT.search(command) and CONTRACT_WRITE.search(command):
        reasons.append("hand-built loop contract")
    return reasons
FAILURE_LINE = re.compile(r"error|refus|reject|required|must|invalid", re.I)
MARKER = re.compile(r"SHIPLOOP-RUN")


def events(path: Path):
    """(line number, event) for every JSON object line."""
    if not path.is_file():
        return
    with path.open(errors="replace") as handle:
        for number, line in enumerate(handle):
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict):
                yield number, event


def timeline(path: Path) -> dict[int, float]:
    stamps: dict[int, float] = {}
    if path.is_file():
        for line in path.read_text(errors="replace").splitlines():
            try:
                item = json.loads(line)
                stamps[int(item["line"])] = float(item["t"])
            except (ValueError, KeyError, TypeError):
                continue
    return stamps


def visible(raw) -> str:
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        for key in ("output_for_prompt", "content", "text"):
            if isinstance(raw.get(key), str):
                return raw[key]
    return ""


def engine_state(run_dir: Path | None) -> dict:
    """ShipLoop's own state.md record, or an empty mapping."""
    if run_dir is None or not (run_dir / "state.md").is_file():
        return {}
    found = STATE_BLOCK.search((run_dir / "state.md").read_text(errors="replace"))
    if not found:
        return {}
    try:
        value = json.loads(found.group("json"))
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def _epoch(text: object) -> float | None:
    """One ShipLoop UTC stamp as epoch seconds, or None when it cannot be read."""
    if not isinstance(text, str):
        return None
    for shape in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            naive = datetime.strptime(text, shape)
        except ValueError:
            continue
        return naive.replace(tzinfo=timezone.utc).timestamp()
    return None


def acceptance_stamps(run_dir: Path | None) -> dict[str, float]:
    """When ShipLoop accepted each action, by action id, from its own timeline.json.

    Advisory, not authoritative: the engine recreates a missing timeline and
    gives a missing historical action the current time, so a stamp can be a
    recovery artefact (not detected: all actions then share one readable stamp).
    An entry that cannot be read is left out rather than guessed, which makes its
    stage report unavailable downstream. Stamps are whole seconds, truncated, so a
    boundary is only good to one second (see per_stage).
    """
    if run_dir is None or not (run_dir / "timeline.json").is_file():
        return {}
    try:
        raw = json.loads((run_dir / "timeline.json").read_text(errors="replace"))
    except ValueError:
        return {}
    accepted = raw.get("accepted") if isinstance(raw, dict) else None
    if not isinstance(accepted, dict):
        return {}
    return {action: when for action, text in accepted.items()
            if isinstance(action, str) and (when := _epoch(text)) is not None}


def stage_results(run_dir: Path | None, state: dict | None = None) -> list[dict]:
    """Accepted actions in ShipLoop's own order, with its own acceptance times.

    The authority is state.md's history -- stage, outcome and action id -- joined
    to timeline.json by action id. Result-file mtimes are deliberately not used:
    rewriting a file would move a boundary the engine never moved, and the order
    history records is the order the graph took. An action whose stamp cannot be
    read carries ``t`` None, so attribution reports it unavailable instead of
    inventing a zero-length window.

    ``state`` lets a caller that already read state.md pass it in, so one
    collection cannot read two different versions of a live run's state.
    """
    history = (engine_state(run_dir) if state is None else state).get("history")
    if not isinstance(history, list):
        return []
    stamps = acceptance_stamps(run_dir)
    rows = []
    for entry in history:
        if not isinstance(entry, dict):
            continue
        action = entry.get("action")
        rows.append({"stage": entry.get("stage") or "?", "outcome": entry.get("outcome"),
                     "work_item": entry.get("workitem"), "action": action if isinstance(action, str) else None,
                     "t": stamps.get(action) if isinstance(action, str) else None})
    return rows


def improve_reviews(run_dir: Path | None) -> dict:
    """Review passes per Improve child, from the review notes the run's worktree keeps.

    A child's passes are its review-<n>.md files; seconds is the time between its first and last note, so a long
    child shows where review passes, not stages, spent the run. Used to decide whether repeat passes are wasted.
    """
    root = run_dir.parent / "worktree" / ".shiploop-improve" if run_dir else None
    children = []
    for reviews in sorted(root.glob("*/*/reviews")) if root and root.is_dir() else []:
        notes = sorted(reviews.glob("review-*.md"))
        if notes:
            stamps = [n.stat().st_mtime for n in notes]
            children.append({"child": reviews.parent.name, "passes": len(notes),
                             "seconds": round(max(stamps) - min(stamps), 1),
                             "bytes": sum(n.stat().st_size for n in notes)})
    return {"children": len(children), "passes": sum(c["passes"] for c in children),
            "max_passes": max((c["passes"] for c in children), default=0), "per_child": children}


def session_stop(event: dict) -> str | None:
    """The host's own reason a session ended, or None when it reported none.

    Claude ends an API failure (rate limit, exhausted credits, a model it may not
    use) with subtype "success" and is_error true, so the subtype alone would call
    that stop a success: the error fields come first. A failed Codex turn carries
    its message in ``error``. Grok's ``cancelled`` is one reason for several causes
    (an empty turn, a permission refusal, exhausted credits) and cannot be told
    apart here.
    """
    detail = event.get("error") if isinstance(event.get("error"), str) else None
    if event.get("is_error") is True or detail:
        why = " ".join(str(p) for p in (event.get("terminal_reason"), event.get("api_error_status")) if p)
        said = detail or (event.get("result") if isinstance(event.get("result"), str) else "")
        bits = [b for b in (why, " ".join(said.split())[:100]) if b]
        return "error" + (": " + ": ".join(bits) if bits else "")
    reason = event.get("stopReason") or event.get("subtype")
    if reason is None:
        return None
    return reason if isinstance(reason, str) else json.dumps(reason, sort_keys=True)[:100]


# Why a counter is unmeasured, recorded beside the run so a reader never takes its 0 for a measurement.
NO_PER_CALL_USAGE = ("the host reports no per-call usage events (one total per session), so turns cannot be "
                     "attributed to a stage")
CLAUDE_TOOL_BLOCKS = ("this host's tool calls arrive as Claude tool_use / tool_result blocks, which collect() does "
                      "not read, so a count of 0 is a lower bound and not a measurement")
# What follows from reading only Grok-shaped tool_call events when the stream is Claude's.
CLAUDE_BLIND = ("stage_tool_calls", "shiploop_failures", "model_glue", "tmp_writes")
# Counters read only from an event shape Grok writes. A stream with no per-call usage events (Claude's, or Codex's
# through the translator) is not Grok's, so there a 0 means the signal is missing, not that nothing happened, and a
# list stays empty rather than hold what a look-alike matched (Codex prints "cancelled 0" in a failing node --test
# summary, and its file_change is a write, not a read). Not read for Claude although its SDK names a
# system/compact_boundary event: no recorded run contains one, so its shape is unverified; add the branch when a
# recorded stream shows one. A stream that mixes hosts (a resume on another) is read as the host that wrote usage events.
GROK_SIGNALS = {
    "compactions": "an auto_compact_completed event",
    "truncated_outputs": "rawOutput.truncated on a tool_call_update",
    "cancelled_tool_calls": "a failed tool_call_update saying the user cancelled it, Grok's permission refusal",
    "knowledge_reads": "a read tool call naming a file path",
}


def context_tokens(usage) -> int | None:
    """Tokens one call read as context (input plus cache reads), or None when its event carried no figure."""
    if not isinstance(usage, dict):
        return None
    parts = [usage.get(key) for key in ("input_tokens", "cache_read_input_tokens")]
    numbers = [p for p in parts if isinstance(p, (int, float)) and not isinstance(p, bool)]
    return sum(numbers) if numbers else None


def total_cost(sessions: list[dict]) -> float | None:
    """The run's cost: its sessions' own reported costs added, or None unless every ended session reported one.

    A host that reports no cost (Codex) has an unknown cost, not a free run, and a session that ended without
    one makes the rest a part, not a total. The one implementation: the metrics and the CLI summary both call it.
    A session that never ended is not in ``sessions`` at all; ``unreported_sessions`` counts those.
    """
    costs = [s.get("cost_usd") for s in sessions if isinstance(s, dict)]
    if not costs or any(isinstance(c, bool) or not isinstance(c, (int, float)) for c in costs):
        return None
    return round(sum(costs), 4)


def collect(out: Path, run_dir: Path | None = None) -> dict:
    stamps = timeline(out / "timeline.jsonl")
    calls: dict[str, dict] = {}
    shared: set[str] = set()
    turns: list[dict] = []
    sessions, failures, compactions = [], [], 0
    glue: list[dict] = []
    asked: list[str] = []
    truncated: set = set()
    cancelled: list[str] = []
    reads: list[str] = []
    tool_blocks = 0  # Claude tool_use blocks: calls this collector cannot classify
    grok = False  # per-call `usage` events: the one stream shape the Grok-only counters below can be read from
    starts = 0  # sessions the host began, to tell how many never reported an end
    # A session that reports no per-call usage (Codex) contributes its own turn count.
    unreported, calls_in_session = 0, 0
    for number, event in events(out / "events.jsonl"):
        kind = event.get("type")
        t = stamps.get(number)
        if kind in ("usage", "assistant"):
            calls_in_session += 1
        if kind == "available_commands" or (kind == "system" and event.get("subtype") == "init"):
            starts += 1  # Codex and Grok open a session with available_commands, Claude with system/init
        if kind == "usage":
            grok = True
            turns.append({"t": t, "input": context_tokens(event.get("usage"))})
        elif kind == "assistant":  # Claude: one message per turn
            for block in (event.get("message") or {}).get("content") or []:
                tool_blocks += isinstance(block, dict) and block.get("type") == "tool_use"
                if isinstance(block, dict) and block.get("type") == "tool_use" and ASK_PERSON.search(str(block.get("name"))):
                    asked.append(" ".join(str(block.get("input") or "").split())[:160])
            turns.append({"t": t, "input": context_tokens((event.get("message") or {}).get("usage"))})
        elif kind == "tool_call":
            arg = event.get("rawInput") if isinstance(event.get("rawInput"), dict) else {}
            tool = str(event.get("toolName") or event.get("title") or "")
            if ASK_PERSON.search(tool):  # SPEC S-14: an unattended run never asks a person
                asked.append(" ".join(str(arg.get("question") or arg or "").split())[:160])
            command = str(arg.get("command") or "")
            calls[event.get("toolCallId")] = {"t": t, "command": command}
            reasons = glue_reasons(command) if command else []
            shared.update(tmp_writes(command) if command else [])
            if reasons:
                glue.append({"reasons": reasons, "command": " ".join(command.split())[:200]})
            target = arg.get("target_file") or arg.get("file_path") or arg.get("path")
            if target:
                reads.append(str(target))
                if WRITE_TOOL.search(tool) and str(target).startswith("/tmp/"):
                    shared.add(str(target))
        elif kind == "tool_call_update" and event.get("status") == "failed" and "cancelled" in json.dumps(
                event.get("content") or "").lower():
            # Grok's headless permission check refused the call; the turn ends with it.
            cancelled.append(((calls.get(event.get("toolCallId")) or {}).get("command") or "")[:160])
        elif kind == "tool_call_update" and isinstance(event.get("rawOutput"), dict):
            raw = event["rawOutput"]
            if raw.get("truncated"):  # Grok repeats the update; count each call once
                truncated.add(event.get("toolCallId"))
            call = calls.get(event.get("toolCallId")) or {}
            match = SHIPLOOP_COMMAND.search(call.get("command", ""))
            code = raw.get("exit_code")
            if match and code not in (None, 0) and not call.get("failed"):
                call["failed"] = True
                shown = visible(raw)
                line = next((ln for ln in shown.splitlines() if FAILURE_LINE.search(ln) and not MARKER.search(ln)), "")
                failures.append({"verb": match.group("verb"), "exit": code, "line": line.strip()[:200]})
        elif kind == "auto_compact_completed":
            compactions += 1
        elif kind in ("end", "result"):
            # The host's own usage is kept as it wrote it: its shape differs by host (Claude's nests), and
            # a figure built here from per-event snapshots or by summing sessions would not be the host's.
            sessions.append({"stop": session_stop(event), "turns": event.get("num_turns"),
                             "cost_usd": event.get("total_cost_usd"),
                             "usage": event.get("usage") if isinstance(event.get("usage"), dict) else None})
            if not calls_in_session:
                unreported += event.get("num_turns") or 0
            calls_in_session = 0
    # One read of state.md for both the accepted history and the pending stage: a
    # live run rewrites it on every transition, so two reads could disagree.
    state = engine_state(run_dir)
    # Counters this host's events cannot show are recorded as unmeasured with the reason,
    # never as 0: a zero would read as a measurement and pass every comparison.
    unmeasured: dict[str, str] = {}
    if not _timed(turns):
        unmeasured["stage_turns"] = NO_PER_CALL_USAGE
    if not grok:
        unmeasured.update({name: f"only Grok's events carry this signal ({signal}); this host's do not, so a "
                                 f"count of 0 is a missing signal and not a measurement"
                           for name, signal in GROK_SIGNALS.items()})
        cancelled, reads = [], []
    if tool_blocks:
        unmeasured.update({name: CLAUDE_TOOL_BLOCKS for name in CLAUDE_BLIND})
    stages = per_stage(stage_results(run_dir, state), turns, calls, stamps, pending_stage(state), unmeasured)
    improve = run_dir / "improve" if run_dir else None
    return {
        "tmp_writes": sorted(shared),
        "sessions": sessions,
        "turns": len(turns) + unreported,
        # Context only: a call's input side is complete when it is sent. Its output count is a streaming
        # snapshot (about 1/17 of the session's own total on a recorded Claude run), so no output figure is built.
        "tokens": {"input_peak": max((x["input"] for x in turns if x["input"] is not None), default=None)},
        "unmeasured": unmeasured,
        "cost_usd": total_cost(sessions),
        "unreported_sessions": max(0, starts - len(sessions)),
        "compactions": None if "compactions" in unmeasured else compactions,
        "truncated_outputs": None if "truncated_outputs" in unmeasured else len(truncated),
        "cancelled_tool_calls": cancelled,
        "shiploop_failures": failures,
        "script_verifications": verifications(run_dir),
        "model_glue": glue,
        "asked_user": asked,
        # Directories only: each child also leaves a `<name>-bind.md` beside its directory.
        "improve_children": sum(1 for p in improve.iterdir() if p.is_dir()) if improve and improve.is_dir() else 0,
        "improve_reviews": improve_reviews(run_dir),
        "knowledge_reads": sorted({r[r.index("docs/shiploop"):] for r in reads if "docs/shiploop" in r}),
        "narrative": narrative(out, run_dir),
        "stages": stages,
    }


NARRATIVE = re.compile(r"=== ShipLoop narrative ===\n(?P<rule>[^\n]*)\n(?P<body>.*?)=== end ShipLoop narrative ===", re.S)
PACKET_STAGE = re.compile(r"ShipLoop navigator \| (?P<stage>[\w-]+) \|")
STATE_BLOCK = re.compile(r"```shiploop-state\n(?P<json>.*?)\n```", re.S)


def _tool_output(event: dict) -> tuple[str | None, str]:
    """(tool call id, text) of one tool result event, for Claude and Grok streams."""
    if event.get("type") == "tool_call_update" and isinstance(event.get("rawOutput"), dict):
        return event.get("toolCallId"), visible(event["rawOutput"])
    if event.get("type") == "user":
        for block in (event.get("message") or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                content = block.get("content")
                if isinstance(content, list):
                    content = "".join(str(part.get("text") or "") for part in content if isinstance(part, dict))
                return block.get("tool_use_id"), str(content or "")
    return None, ""


def _assistant_text(event: dict) -> str:
    if event.get("type") == "text":  # Grok streams text in chunks
        return str(event.get("data") or "")
    if event.get("type") == "assistant":
        return "".join(str(block.get("text") or "") for block in (event.get("message") or {}).get("content") or []
                       if isinstance(block, dict) and block.get("type") == "text")
    return ""


def _lines(text: str) -> list[str]:
    """Non-blank lines, whitespace-collapsed; a heading's leading marks do not change what it says."""
    return [" ".join(line.lstrip("#").split()) for line in text.splitlines() if line.lstrip("#").strip()]


def narrative(out: Path, run_dir: Path | None = None) -> dict:
    """SPEC S-15: did the model show each milestone narrative ShipLoop asked it to show?

    An emission is a ShipLoop tool result whose narrative section asks the model to
    show it. It counts as shown when the narrative's heading appears in the model's
    text before the next emission, and verbatim when every narrative line does.
    Keeps counts and stage names only, never narrative text.
    """
    emissions: list[dict] = []
    seen: set = set()
    for _, event in events(out / "events.jsonl"):
        call, output = _tool_output(event)
        match = NARRATIVE.search(output) if output else None
        if match and call not in seen and "Show the user" in match.group("rule"):
            seen.add(call)
            stage = PACKET_STAGE.search(output)
            emissions.append({"stage": stage.group("stage") if stage else None,
                              "lines": _lines(match.group("body")), "text": ""})
        elif emissions:
            emissions[-1]["text"] += _assistant_text(event)
    shown = verbatim = 0
    skipped = []
    for emission in emissions:
        said = set(_lines(emission["text"]))
        if emission["lines"] and emission["lines"][0] in said:
            shown += 1
            verbatim += all(line in said for line in emission["lines"])
        else:
            skipped.append(emission["stage"])
    results = with_headline = 0
    for path in sorted((run_dir / "results").glob("*.md")) if run_dir and (run_dir / "results").is_dir() else []:
        block = STATE_BLOCK.search(path.read_text(errors="replace"))
        try:
            result = json.loads(block.group("json"))["result"] if block else None
        except (ValueError, KeyError, TypeError):
            result = None
        # ShipLoop records not-applicable stages itself; only steps the model reported count.
        if not isinstance(result, dict) or str(result.get("summary", "")).startswith("Not applicable to this item"):
            continue
        results += 1
        with_headline += bool(str(result.get("headline") or "").strip())
    return {"emitted": len(emissions), "shown": shown, "verbatim": verbatim, "skipped": skipped,
            "results": results, "with_headline": with_headline}


def verifications(run_dir: Path | None) -> dict:
    """The checks ShipLoop itself ran and recorded (tests/<action>-verify<N>.md), case-agnostic.

    ``could_not_run`` counts the attempts where no command reached a verdict
    about the product (it timed out, could not start, or was skipped on budget).
    Those refuse their stage without being evidence against it, so a run with
    any of them is reporting an environment problem, not a product one.
    """
    records = sorted(run_dir.rglob("*-verify*.md")) if run_dir and run_dir.is_dir() else []
    passed = commands = could_not_run = 0
    for path in records:
        text = path.read_text(errors="replace")
        passed += bool(re.search(r'"passed"\s*:\s*true', text))
        could_not_run += bool(re.search(r'"disposition"\s*:\s*"could-not-run"', text))
        commands += len(re.findall(r'"command"\s*:', text))
    return {"records": len(records), "passed": passed, "could_not_run": could_not_run, "commands": commands}


def current_stage(state: dict) -> str | None:
    """The stage ShipLoop's state names, with a Work Item's inner loop resolved to its own stage.

    While a work item is built the run state's stage is the navigator's pseudo-label
    ``inner-loop``; the stage the run is actually in is the item's.
    """
    stage = state.get("stage")
    if stage != "inner-loop":
        return stage if isinstance(stage, str) else None
    loops, items, index = state.get("inner_loops"), state.get("work_items"), state.get("work_index")
    if not (isinstance(loops, dict) and isinstance(items, list) and isinstance(index, int)):
        return None
    if not 0 <= index < len(items) or not isinstance(items[index], dict):
        return None
    record = loops.get(items[index].get("id"))
    inner = record.get("stage") if isinstance(record, dict) else None
    return inner if isinstance(inner, str) else None


def pending_stage(state: dict) -> str | None:
    """The stage ShipLoop was on when the run stopped without accepting it, if any.

    A run left active, paused or halted stopped somewhere, and that stage is exactly the
    one an attrition question is about, so it must not be dropped. A blocked run whose
    last accepted action is that stage's own ``blocked`` result left nothing unaccepted:
    the model reported the block and ShipLoop recorded it, which is the opposite of a
    host that died mid-stage.
    """
    if state.get("status") in (None, "done"):
        return None
    stage = current_stage(state)
    history = state.get("history")
    last = history[-1] if isinstance(history, list) and history and isinstance(history[-1], dict) else {}
    if stage is not None and last.get("stage") == stage and last.get("outcome") == "blocked":
        return None
    return stage


def _timed(turns: list[dict]) -> bool:
    """Whether any turn carries a runner time, which stage windows need."""
    return any(x["t"] is not None for x in turns)


def per_stage(accepted: list[dict], turns: list[dict], calls: dict, stamps: dict,
              pending: str | None = None, unmeasured: dict | None = None) -> list[dict]:
    """Turns, tool calls and time between one accepted action and the next.

    Needs the runner's timeline; without it only the order and outcome are known.
    An action ShipLoop could not stamp reports ``timing: "unavailable"`` rather
    than a zero-length window, and so does an action accepted before the host's
    first event (a seeded run records its early stages itself, before the host
    starts). When the run stopped without accepting its current stage, a final
    ``incomplete`` row carries the work after the last acceptance, so the stage a
    run died in is still attributed, whatever the host reports.

    A counter the host does not report (``unmeasured`` names it, or a stage
    count that needs per-call usage when the host has none) is ``None`` in the
    row, never 0.

    Limits, not fixed: engine stamps are whole seconds (truncated) while runner times
    carry milliseconds, so the turn that submits a stage's result lands in the next
    stage about a third of the time (stage turns are good to about one per boundary);
    seconds are wall clock and include any interruption gap (a resume, a sleep, a
    credit stop); and an engine that recreated a lost timeline.json gives every
    historical action one stamp, which no check here can tell from a real one.

    No cost is apportioned here: a per-stage share of one total, divided by turn
    count, moves when prices or unrelated work move, so it would not measure the
    stage. Total cost stays whole-run.
    """
    unmeasured = set(unmeasured or ())
    if not _timed(turns):
        unmeasured.add("stage_turns")

    def counted(window: list[dict], tools: list) -> dict:
        return {"turns": None if "stage_turns" in unmeasured else len(window),
                "tool_calls": None if "stage_tool_calls" in unmeasured else len(tools)}

    if not accepted and not pending:
        return []
    if not stamps:
        rows = [{"stage": a["stage"], "outcome": a.get("outcome"), "timing": "unavailable"} for a in accepted]
        if pending:
            rows.append({"stage": pending, "outcome": None, "incomplete": True, "timing": "unavailable"})
        return rows
    start = min(stamps.values())
    rows, previous, since = [], start - 1, start  # the first stamped event belongs to the first stage
    gap = False  # the preceding action had no stamp, so this row's lower boundary is unknown
    for item in accepted:
        base = {"stage": item["stage"], "outcome": item.get("outcome")}
        if item.get("t") is None:
            rows.append({**base, "timing": "unavailable"})
            gap = True
            continue
        if item["t"] < start:
            # Accepted before the host's first event: the harness seeded it, so no host work
            # was done in it. Its stamp is neither a duration nor a boundary for the next stage.
            rows.append({**base, "timing": "unavailable"})
            continue
        if gap:
            # Its window also covers the unstamped action before it, so attributing
            # the whole window here would overstate this stage. Attribution resumes
            # from this known boundary.
            rows.append({**base, "timing": "unavailable"})
            previous = since = item["t"]
            gap = False
            continue
        window = [x for x in turns if x["t"] is not None and previous < x["t"] <= item["t"]]
        tools = [c for c in calls.values() if c["t"] is not None and previous < c["t"] <= item["t"]]
        rows.append({**base, "seconds": round(item["t"] - since, 1), **counted(window, tools)})
        previous = since = item["t"]
    if pending:
        if gap:
            # The last acceptance has no stamp, so its work and this stage's cannot be told apart.
            rows.append({"stage": pending, "outcome": None, "incomplete": True, "timing": "unavailable"})
        else:
            # The newest event of any kind bounds the window, so a host that reports no
            # per-turn events still shows the time and tool calls spent in the stage.
            end = max(max(stamps.values()), since)
            window = [x for x in turns if x["t"] is not None and previous < x["t"] <= end]
            tools = [c for c in calls.values() if c["t"] is not None and previous < c["t"] <= end]
            rows.append({"stage": pending, "outcome": None, "incomplete": True,
                         "seconds": round(end - since, 1), **counted(window, tools)})
    return rows


def money(value) -> str:
    """A cost for a printed line; a host that reports none has an unknown cost, never $0."""
    return "not reported" if value is None else f"${value}"


def cost_text(run_metrics: dict) -> str:
    """The cost for a printed line, saying so when sessions that never reported make it a lower bound.

    A cost that is unknown has nothing for a lower bound to bound, so it says only that it is not reported.
    """
    cost, never = run_metrics.get("cost_usd"), run_metrics.get("unreported_sessions") or 0
    return money(cost) + (f" (lower bound: {never} session(s) never reported)" if never and cost is not None else "")


def count(run_metrics: dict, name: str) -> int | None:
    """How many of a detected thing (a list in the metrics), or None when the host cannot show it.

    A counter that is already a number in the metrics (compactions, truncated outputs) is None there when unmeasured.
    """
    value = run_metrics.get(name)
    if name in (run_metrics.get("unmeasured") or {}) or value is None:
        return None
    return len(value) if isinstance(value, (list, dict)) else value


def stage_text(row: dict) -> str:
    """One stage row for a printed line: turns and minutes where measured, else what is."""
    if row.get("seconds") is None:
        return str(row["stage"])
    minutes = f"{row['seconds'] / 60:.1f}m"
    return f"{row['stage']} {row['turns']}t/{minutes}" if row.get("turns") is not None else f"{row['stage']} {minutes}"


def summary_lines(metrics: dict, top: int = 5) -> list[str]:
    """A few lines for the printed report: the costliest stages and the problems."""

    def shown(name: str) -> str:
        found = count(metrics, name)
        return "not measured" if found is None else str(found)

    lines = [f"turns {metrics['turns']}, cost {cost_text(metrics)}, sessions {len(metrics['sessions'])} "
             f"({', '.join(str(s['stop']) for s in metrics['sessions']) or 'none ended'}), "
             f"compactions {shown('compactions')}, truncated outputs {shown('truncated_outputs')}, "
             f"cancelled tool calls {shown('cancelled_tool_calls')}, "
             f"ShipLoop command failures {shown('shiploop_failures')}, "
             f"script verifications {metrics['script_verifications']['passed']}/{metrics['script_verifications']['records']} passed"
             + (f" ({metrics['script_verifications']['could_not_run']} could not run)"
                if metrics["script_verifications"].get("could_not_run") else "") + ", "
             f"model glue {shown('model_glue')}, asked a person {len(metrics['asked_user'])}, "
             f"Improve children {metrics['improve_children']}"
             + (f" ({metrics['improve_reviews']['passes']} review passes, at most "
                f"{metrics['improve_reviews']['max_passes']} in one child)"
                if metrics.get("improve_reviews", {}).get("passes") else "")]
    story = metrics.get("narrative") or {}
    if story.get("emitted") or story.get("results"):
        lines.append(f"narrative shown {story['shown']}/{story['emitted']} (verbatim {story['verbatim']})"
                     + (f", skipped at {', '.join(str(s) for s in story['skipped'][:5])}" if story["skipped"] else "")
                     + f"; headlines {story['with_headline']}/{story['results']} results")
    timed = [s for s in metrics["stages"] if s.get("seconds") is not None]
    if timed:
        # Turns rank the stages where the host reports them; otherwise minutes do, and the line says so.
        by_turns = all(s.get("turns") is not None for s in timed)
        costly = sorted(timed, key=lambda s: s["turns"] if by_turns else s["seconds"], reverse=True)[:top]
        lines.append("costliest stages: " + ", ".join(stage_text(s) for s in costly)
                     + ("" if by_turns else " (by minutes: this host reports no per-stage turns)"))
    return lines
