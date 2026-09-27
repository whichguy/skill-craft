"""Where a ShipLoop E2E run spent its turns, tokens and time.

Reads the output directory the runner wrote: the host event stream
(events.jsonl), its arrival times (timeline.jsonl, one line per non-streaming
event: {"line": n, "t": epoch}) and the ShipLoop run directory. Grok events
carry no timestamps, so stage attribution uses the times the runner stamped
and the times ShipLoop wrote each accepted stage result.

Never returns packet text: ShipLoop CLI output is reduced to the failing line.
"""

from __future__ import annotations

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
MODEL_INPUT = re.compile(r"/inbox/|/run/notes/|/reviews/|opening\.md|commit-message\.md")
# `git ... commit|add` as a command: at the start of a line or after ; && || |, optionally after VAR=value.
GLUE_COMMIT = re.compile(r"(?:^|[;&|]\s*)(?:\w+=\S*\s+)*git\b[^\n;&|]*\s(?:commit|add)\b", re.M)
GLUE_WRITE = re.compile(r"(?:>>?|\btee\b|\bcp\b|\bmv\b|\bmkdir\b|\brm\b)\s+[^\n;&|]*")
GLUE_CONTRACT = re.compile(r"exit_condition|repeat_condition|required_trivial_reviews")


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
    if GLUE_CONTRACT.search(command):
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


def stage_results(run_dir: Path | None) -> list[dict]:
    """Accepted stage results in the order ShipLoop wrote them."""
    if run_dir is None or not (run_dir / "results").is_dir():
        return []
    accepted = []
    for path in sorted((run_dir / "results").glob("*.md"), key=lambda p: p.stat().st_mtime):
        match = re.search(r'"stage"\s*:\s*"([^"]+)"', path.read_text(errors="replace"))
        accepted.append({"stage": match.group(1) if match else path.stem, "t": path.stat().st_mtime})
    return accepted


def collect(out: Path, run_dir: Path | None = None) -> dict:
    stamps = timeline(out / "timeline.jsonl")
    calls: dict[str, dict] = {}
    turns: list[dict] = []
    sessions, failures, compactions = [], [], 0
    glue: list[dict] = []
    asked: list[str] = []
    truncated: set = set()
    cancelled: list[str] = []
    reads: list[str] = []
    for number, event in events(out / "events.jsonl"):
        kind = event.get("type")
        t = stamps.get(number)
        if kind == "usage":
            usage = event.get("usage") or {}
            turns.append({"t": t, "input": (usage.get("input_tokens") or 0) + (usage.get("cache_read_input_tokens") or 0),
                          "output": usage.get("output_tokens") or 0})
        elif kind == "assistant":  # Claude: one message per turn
            for block in (event.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use" and ASK_PERSON.search(str(block.get("name"))):
                    asked.append(" ".join(str(block.get("input") or "").split())[:160])
            usage = (event.get("message") or {}).get("usage") or {}
            turns.append({"t": t, "input": (usage.get("input_tokens") or 0) + (usage.get("cache_read_input_tokens") or 0),
                          "output": usage.get("output_tokens") or 0})
        elif kind == "tool_call":
            arg = event.get("rawInput") if isinstance(event.get("rawInput"), dict) else {}
            tool = str(event.get("toolName") or event.get("title") or "")
            if ASK_PERSON.search(tool):  # SPEC S-14: an unattended run never asks a person
                asked.append(" ".join(str(arg.get("question") or arg or "").split())[:160])
            command = str(arg.get("command") or "")
            calls[event.get("toolCallId")] = {"t": t, "command": command}
            reasons = glue_reasons(command) if command else []
            if reasons:
                glue.append({"reasons": reasons, "command": " ".join(command.split())[:200]})
            target = arg.get("target_file") or arg.get("file_path") or arg.get("path")
            if target:
                reads.append(str(target))
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
            sessions.append({"stop": event.get("stopReason") or event.get("subtype"),
                             "turns": event.get("num_turns"), "cost_usd": event.get("total_cost_usd")})
    cost = round(sum(s["cost_usd"] or 0 for s in sessions), 4) if sessions else None
    stages = per_stage(stage_results(run_dir), turns, calls, stamps, cost)
    improve = run_dir / "improve" if run_dir else None
    return {
        "sessions": sessions,
        "turns": len(turns) or sum(s["turns"] or 0 for s in sessions),
        "tokens": {"input_peak": max((x["input"] for x in turns), default=0),
                   "output_total": sum(x["output"] for x in turns)},
        "cost_usd": cost,
        "compactions": compactions,
        "truncated_outputs": len(truncated),
        "cancelled_tool_calls": cancelled,
        "shiploop_failures": failures,
        "script_verifications": verifications(run_dir),
        "model_glue": glue,
        "asked_user": asked,
        "improve_children": len(list(improve.iterdir())) if improve and improve.is_dir() else 0,
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
    """The checks ShipLoop itself ran and recorded (tests/<action>-verify<N>.md), case-agnostic."""
    records = sorted(run_dir.rglob("*-verify*.md")) if run_dir and run_dir.is_dir() else []
    passed = commands = 0
    for path in records:
        text = path.read_text(errors="replace")
        passed += bool(re.search(r'"passed"\s*:\s*true', text))
        commands += len(re.findall(r'"command"\s*:', text))
    return {"records": len(records), "passed": passed, "commands": commands}


def per_stage(accepted: list[dict], turns: list[dict], calls: dict, stamps: dict, cost: float | None) -> list[dict]:
    """Turns, tool calls and time between one accepted stage result and the next.

    Needs the runner's timeline; without it (older runs) only the order is known.
    """
    if not accepted or not stamps:
        return [{"stage": a["stage"]} for a in accepted]
    start = min(stamps.values())
    rows, previous, since = [], start - 1, start  # the first stamped event belongs to the first stage
    total_turns = len([x for x in turns if x["t"] is not None]) or 1
    for item in accepted:
        window = [x for x in turns if x["t"] is not None and previous < x["t"] <= item["t"]]
        tools = [c for c in calls.values() if c["t"] is not None and previous < c["t"] <= item["t"]]
        rows.append({"stage": item["stage"], "seconds": round(item["t"] - since, 1), "turns": len(window),
                     "tool_calls": len(tools), "output_tokens": sum(x["output"] for x in window),
                     "cost_share_usd": round(cost * len(window) / total_turns, 2) if cost else None})
        previous = since = item["t"]
    return rows


def summary_lines(metrics: dict, top: int = 5) -> list[str]:
    """A few lines for the printed report: the costliest stages and the problems."""
    lines = [f"turns {metrics['turns']}, cost ${metrics['cost_usd']}, sessions {len(metrics['sessions'])} "
             f"({', '.join(str(s['stop']) for s in metrics['sessions']) or 'none ended'}), "
             f"compactions {metrics['compactions']}, truncated outputs {metrics['truncated_outputs']}, "
             f"cancelled tool calls {len(metrics['cancelled_tool_calls'])}, "
             f"ShipLoop command failures {len(metrics['shiploop_failures'])}, "
             f"script verifications {metrics['script_verifications']['passed']}/{metrics['script_verifications']['records']} passed, "
             f"model glue {len(metrics['model_glue'])}, asked a person {len(metrics['asked_user'])}, "
             f"Improve children {metrics['improve_children']}"]
    story = metrics.get("narrative") or {}
    if story.get("emitted") or story.get("results"):
        lines.append(f"narrative shown {story['shown']}/{story['emitted']} (verbatim {story['verbatim']})"
                     + (f", skipped at {', '.join(str(s) for s in story['skipped'][:5])}" if story["skipped"] else "")
                     + f"; headlines {story['with_headline']}/{story['results']} results")
    timed = [s for s in metrics["stages"] if "turns" in s]
    if timed:
        costly = sorted(timed, key=lambda s: s["turns"], reverse=True)[:top]
        lines.append("costliest stages: " + ", ".join(f"{s['stage']} {s['turns']}t/{s['seconds'] / 60:.1f}m"
                                                      for s in costly))
    return lines
