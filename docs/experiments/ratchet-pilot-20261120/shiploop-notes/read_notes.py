#!/usr/bin/env python3
"""Read the deliveries of the owner-notes candidate: what the harness judged, what the stand-in sent, and for each owner
note its rows, the gate at work, whether the model was given its words, what the run did after it, and what the
requester is told.

Usage: ``read_notes.py ROOT [NAME ...] [--json FILE] [--export DIR]``.  ROOT holds one output folder per delivery
(``shiploop-defaults/launch_wave.sh``), the stand-in's record ``<NAME>-requester.json`` beside each, and the build copy
``apparatus-*/skills/shiploop/scripts`` whose own modules read the run (``shiploop_owner_notes.read``, ``ledger``,
``standing``, ``owed_by``, ``item_fate``; ``shiploop_defaults``; ``shiploop_knowledge_home``; ``shiploop_store``).
With no NAME every delivery folder is read; one without ``result.json`` is printed from what its run folder shows so
far, marked "not ended".

For each delivery: (1) the harness's reading: outcome, verdicts, the eight checks, the five start-up checks found by
their command and the end of each failed one's recorded output, times, counts, stage seconds and the list of
defaults; (2) the stand-in: mode, the stage waited for, the row chosen and its class, the note sent and the note
command's reply.  A delivery with no stand-in record, or whose stand-in sent nothing, ends there.  Otherwise, for each
owner note on file: (3) when it was written and what was open; (4) its ledger rows and where it stands; (5) the gate's
refusals in ``trace.jsonl``; (6) whether the model was given its words (the Codex rollout under
``<NAME>/home/.codex/sessions/``, else Claude Code's ``<NAME>/events.jsonl``); (7) the requirement the chosen row
names then and at the end, the commits after the note, and the work items added since; (8) what the requester is
told: the done packet's "Your notes" lines, the report's section, the host's last message.

``--export DIR`` writes, for each delivery with a note sent, ``DIR/<NAME>/`` with ``row.txt``, ``answer.txt``,
``before.md`` and ``after.md`` and nothing about checks, rows or outcomes.  Nothing is written into a delivery's
folder.  Home paths are printed as ``~``.
"""
from __future__ import annotations

import argparse
import datetime
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

VERDICTS = ("invoked", "plugin", "process", "shiploop", "committed")
STARTUP = ("migrate", "restart", "switch", "rollback", "cli")
HOME = os.path.expanduser("~")
TAG = re.compile(r"<[^>]+>")
CODE = ("src/", "bin/")
TESTS = ("test/",)
# The first line of each refusal the gate gives (shiploop_owner_notes.refusal, unreadable, arrived), after the
# command's prefix ("ShipLoop check: " or "ShipLoop navigator: ").
PREFIX = re.compile(r"^ShipLoop (?:check|navigator): ")
GATE = (re.compile(r"^owner notes? N\d+.*? (?:is|are) not accounted for: "),
        re.compile(r'^"notes" is not a list: give it in '),
        re.compile(r'^"notes" has two rows for N\d+'),
        re.compile(r'^"notes" has a row whose "note" is .+, which is not an owner note id \(N<k>\)'),
        re.compile(r'^"notes" in .+ has a row this stage does not owe'),
        re.compile(r"^owner notes? N\d+.*? arrived while this handoff was being completed"),
        re.compile(r", so ShipLoop cannot tell which owner notes this result must account for: "))
SENTENCE = re.compile(r"(.+?[.!?])(?=\s|$)", re.DOTALL)
OWNER_NOTE = re.compile(r"owner note", re.IGNORECASE)
# Session records: what the model was given, and what it wrote (given_to_model.py).
SKIP = {"encrypted_content", "signature", "id", "call_id", "internal_chat_message_metadata_passthrough"}
TOOL_OUTPUTS = ("custom_tool_call_output", "function_call_output", "local_shell_call_output")
CALLS = ("custom_tool_call", "function_call", "local_shell_call")


def tilde(text: object) -> str:
    return str(text).replace(HOME, "~")


def fold(text: str) -> str:
    return " ".join(str(text).split())


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def lines_of(path: Path) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    rows = []
    for line in text.splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def clock(stamp: float | None) -> str | None:
    return datetime.datetime.fromtimestamp(stamp, datetime.UTC).strftime("%Y-%m-%d %H:%M:%SZ") if stamp else None


def epoch(at: object) -> float | None:
    try:
        return datetime.datetime.fromisoformat(str(at)).timestamp()
    except ValueError:
        return None


def git(repo: Path, *args: str) -> str | None:
    """What ``git -C repo`` prints, or None when it fails."""
    try:
        done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8",
                              errors="replace", check=False)
    except OSError:
        return None
    return done.stdout if done.returncode == 0 else None


def engine(root: Path):
    """The engine's own modules, from the build copy the deliveries run."""
    scripts = sorted(root.glob("apparatus-*/skills/shiploop/scripts"))
    if not scripts:
        sys.exit(f"no apparatus-*/skills/shiploop/scripts under {root}")
    sys.path.insert(0, str(scripts[-1]))
    import shiploop_defaults as defaults
    import shiploop_knowledge_home as knowledge
    import shiploop_owner_notes as owner_notes
    import shiploop_store as store
    return defaults, knowledge, owner_notes, store


# ---------------------------------------------------------------------------------------------------------- 1, 2


def harness(out: Path) -> dict:
    """Item 1 from the harness's files: outcome, verdicts, checks, start-up checks, times and counts."""
    result, metrics, invocation = load(out / "result.json"), load(out / "metrics.json"), load(out / "invocation.json")
    row = {key: result.get(key, invocation.get(key)) for key in ("host", "model", "effort")}
    if not result:
        row.update(ended=False, started=tilde((invocation.get("environment") or {}).get("at") or "not recorded"))
        return row
    span = result.get("span") or {}
    checks = [check for check in result.get("checks") or [] if isinstance(check, dict)]

    def name(check: dict) -> str:
        return " ".join(str(check.get("command") or "").replace('"', "").split()[1:]).split("/")[-1]

    def probe(check: dict) -> str | None:
        found = re.search(r"due_times_probe\.py\W+(" + "|".join(STARTUP) + r")\b", str(check.get("command")))
        return found.group(1) if found else None
    stages = metrics.get("stages") or []
    startup = {}
    for word in STARTUP:
        check = next((check for check in checks if probe(check) == word), None)
        output = str((check or {}).get("output") or "")
        startup[word] = None if check is None else {
            "pass": bool(check.get("pass")), "returncode": check.get("returncode"),
            "output_end": None if check.get("pass") else (tilde(output.rstrip()[-300:]) if output.strip()
                                                          else "no output recorded")}
    row.update(
        ended=True, outcome=result.get("outcome_class"), basis=result.get("outcome_basis"),
        verdicts={key: (result.get(key) or {}).get("pass") for key in VERDICTS},
        checks=[{"check": name(check), "pass": bool(check.get("pass"))} for check in checks], startup=startup,
        started=clock(span.get("started")), ended_at=clock(span.get("ended")), ended_ts=span.get("ended"),
        minutes=round((span["ended"] - span["started"]) / 60, 1) if span.get("started") and span.get("ended") else None,
        turns=metrics.get("turns"), model_calls=metrics.get("model_calls"),
        output_tokens=(metrics.get("tokens") or {}).get("output"), cost_usd=metrics.get("cost_usd"),
        spec_seconds=sum(stage.get("seconds") or 0 for stage in stages if stage.get("stage") == "spec") or None,
        strategy_seconds=sum(stage.get("seconds") or 0 for stage in stages if stage.get("stage") == "test-strategy") or None)
    return row


def stand_in(record: dict) -> dict | None:
    """Item 2 from the stand-in's record; None when there is none."""
    if not record:
        return None
    chosen = (record.get("choice_at_send") or {}).get("chosen")
    printed = record.get("rows_at_send") or []
    line = printed[chosen - 1] if isinstance(chosen, int) and 0 < chosen <= len(printed) else None
    named = re.match(r"\d+\. (R-\d+)\b", line or "")
    note = record.get("note") if isinstance(record.get("note"), dict) else None
    return {"mode": record.get("mode"), "stage_waited_for": record.get("stage_waited_for"),
            "stage_seen_at": record.get("stage_seen_at"), "chosen": chosen, "row": line,
            "requirement": named.group(1) if named else None, "row_class": record.get("row_class"),
            "row_class_note": record.get("row_class_note"), "note_sent": record.get("note_sent"),
            "note_id": (note or {}).get("id"), "note_exit": (note or {}).get("exit"),
            "note_reply": tilde((note or {}).get("output")) if note else None, "ended": record.get("ended")}


def run_folder(out: Path, store) -> tuple[Path | None, int]:
    """The ShipLoop run the harness names, else the one with the longest history; and how many run folders exist."""
    folders = [path.parent for path in out.glob(".shiploop-runs/*/run/state.md")]
    named = Path(str((load(out / "result.json").get("shiploop") or {}).get("run_dir")
                     or load(out / "shiploop-run.json").get("run_dir") or ""))
    if str(named) not in ("", ".") and (named / "state.md").is_file():
        return named, len(folders)

    def length(path: Path) -> int:
        try:
            return len(store.read_record(path / "state.md").get("history") or [])
        except Exception:  # noqa: BLE001 - a state file being written
            return -1
    return (max(folders, key=length) if folders else None), len(folders)


# ---------------------------------------------------------------------------------------------------------- the run


def stage_of(row: dict) -> str:
    stage = row.get("stage")
    return str(stage[0] if isinstance(stage, list) and stage else stage)


def accepted_times(run: Path, rows: list[dict]) -> dict:
    """When each action was accepted: the trace's command that accepted it, else timeline.json (to the second)."""
    times = {action: epoch(at) for action, at in (load(run / "timeline.json").get("accepted") or {}).items()}
    for traced in rows:
        for accepted in traced.get("accepted") or ():
            if isinstance(accepted, dict) and accepted.get("action") and traced.get("ts"):
                times[accepted["action"]] = traced["ts"]
    return times


def label(part: dict | None) -> str:
    """A stage as a block names it: stage, work item, outcome, and the action's first hex digits."""
    if not part:
        return "not recorded"
    return " ".join(str(value) for value in (part.get("stage"), part.get("workitem"), part.get("outcome")) if value) + (
        f" ({str(part['action'])[:12]})" if part.get("action") else "")


def written(note: dict, rows: list[dict], history: list[dict], times: dict) -> dict:
    """When the note was written (the trace's ``note`` command, else its ``written_at``), the last accepted action
    before then, and the action open then."""
    wrote = next((row for row in rows if row.get("verb") == "note" and row.get("note") == note["id"]), None)
    moment = wrote["ts"] if wrote and wrote.get("ts") else epoch(note["written_at"])
    if moment is None:
        return {"moment": None, "not_recorded": "the note's written_at does not read as a time"}
    before = [entry for entry in history if times.get(entry.get("action")) is not None
              and times[entry["action"]] <= moment]
    last = before[-1] if before else None
    if wrote:
        action, stage, source = (wrote.get("cursor") or [None])[0], stage_of(wrote), "the trace's note command"
    else:
        earlier = [row for row in rows if row.get("ts") and row["ts"] <= moment and row.get("kind") in ("packet", "command")]
        row = earlier[-1] if earlier else {}
        packet = row.get("kind") == "packet"
        action = row.get("action") if packet else (row.get("cursor") or [None])[-1]
        stage = row.get("stage") if packet else (row.get("stage") or [None])[-1]
        source = "the last trace row before the note" if row else None
    item = next((entry.get("workitem") for entry in history if entry.get("action") == action), None) or next(
        (row.get("item") for row in rows if row.get("kind") == "packet" and row.get("action") == action), None)
    return {"moment": moment, "in_trace": clock(wrote["ts"]) if wrote and wrote.get("ts") else None,
            "last_accepted_before": None if last is None else {
                "stage": last.get("stage"), "workitem": last.get("workitem"), "outcome": last.get("outcome"),
                "action": last.get("action"), "accepted_at": clock(times[last["action"]])},
            "open_then": {"stage": stage, "workitem": item, "action": action, "from": source} if action else None}


def gate_refusal(error: str) -> bool:
    first = PREFIX.sub("", str(error).splitlines()[0] if str(error).strip() else "")
    return any(pattern.search(first) for pattern in GATE)


def gate(rows: list[dict], on_file: list[str]) -> list[dict]:
    """Every command of the trace that ended non-zero with an error naming a note on file (``on_file``, by id as a
    whole word) or starting as the gate's refusal does: when, stage, verb, the note ids it names, whether it is the
    gate's, and its first line."""
    found = []
    for row in rows:
        if row.get("kind") != "command" or row.get("exit") in (0, None):
            continue
        error = str(row.get("error") or "")
        ids = [ident for ident in on_file if re.search(r"\b" + re.escape(ident) + r"\b", error)]
        refusal = gate_refusal(error)
        if refusal or ids:
            found.append({"ts": row.get("ts"), "at": row.get("at"), "stage": stage_of(row), "verb": row.get("verb"),
                          "notes": ids, "gate": refusal,
                          "first_line": tilde(error.splitlines()[0] if error.strip() else "")})
    return found


def last_command(rows: list[dict]) -> dict | None:
    """The trace's last ShipLoop command other than a note (the stand-in's), and whether it was the gate's refusal."""
    command = next((row for row in reversed(rows) if row.get("kind") == "command" and row.get("verb") != "note"), None)
    if command is None:
        return None
    return {"verb": command.get("verb"), "stage": stage_of(command), "exit": command.get("exit"), "at": command.get("at"),
            "gate_refusal": command.get("exit") not in (0, None) and gate_refusal(str(command.get("error") or ""))}


# ---------------------------------------------------------------------------------------------------------- 6


def strings(value: object, key: str = "") -> list[str]:
    """Every text a record holds, in order, without its ids, signatures and encrypted content."""
    if key in SKIP:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for name, item in value.items() for text in strings(item, name)]
    if isinstance(value, list):
        return [text for item in value for text in strings(item)]
    return []


def output_text(output: object) -> str:
    """The text of a tool output as the model was given it: its ``text`` parts, or the string itself."""
    if isinstance(output, str):
        return output
    if isinstance(output, list):
        return "\n".join(part if isinstance(part, str) else str(part.get("text") or "") if isinstance(part, dict) else ""
                         for part in output)
    return " ".join(strings(output))


def given(out: Path, words: str, ident: str) -> dict:
    """Whether the model was given ``words`` (folded), and the first output given to it that names ``ident``: from the
    Codex rollouts, else Claude Code's stream-json (given_to_model.py)."""
    naming = re.compile(r"\b" + re.escape(ident) + r"\b")
    rollouts = sorted((out / "home" / ".codex" / "sessions").glob("**/rollout-*.jsonl"))
    printed = outputs = 0
    first = None
    if rollouts:
        source = "Codex rollout" + ("s" if len(rollouts) > 1 else "")
        for path in rollouts:
            for row in lines_of(path):
                payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
                item = payload.get("item") if isinstance(payload.get("item"), dict) else {}
                if row.get("type") == "event_msg" and item.get("type") == "CommandExecution":
                    printed += words in fold(str(item.get("aggregated_output") or ""))
                elif row.get("type") == "response_item" and payload.get("type") in TOOL_OUTPUTS:
                    text = output_text(payload.get("output"))
                    outputs += words in fold(text)
                    if first is None and naming.search(text):
                        first = {"kind": payload.get("type"), "start": tilde(text[:300])}
    elif (out / "events.jsonl").is_file() and any(row.get("type") in ("user", "assistant")
                                                  for row in lines_of(out / "events.jsonl")[:50]):
        source = "Claude Code events.jsonl"
        for row in lines_of(out / "events.jsonl"):
            if row.get("type") != "user":
                continue
            raw = row.get("tool_use_result")
            message = row.get("message") if isinstance(row.get("message"), dict) else {}
            for block in message.get("content") if isinstance(message.get("content"), list) else []:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                text = output_text(block.get("content"))
                printed += words in fold(" ".join(strings(raw))) if isinstance(raw, (dict, str)) else 0
                outputs += words in fold(text)
                if first is None and naming.search(text):
                    first = {"kind": "tool_result", "start": tilde(text[:300])}
    else:
        return {"not_recorded": "no Codex rollout under home/.codex/sessions/ and no Claude Code events.jsonl"}
    return {"source": source, "words": words, "printed_by": printed, "given_in": outputs,
            "summary": f"printed by {printed} commands; given to the model in {outputs} outputs; the model "
                       f"{'was' if outputs else 'was not'} given the note's words", "first_naming_it": first}


# ---------------------------------------------------------------------------------------------------------- 7


def checkout(state: dict, out: Path) -> Path | None:
    """The run's own checkout (state.md's ``repo``), else the folder the host ran in (invocation.json's ``cwd``)."""
    for path in (state.get("repo"), load(out / "invocation.json").get("cwd")):
        if path and git(Path(str(path)), "rev-parse", "--git-dir") is not None:
            return Path(str(path))
    return None


def spec_then(repo: Path, requirement: str, moment: float, knowledge) -> tuple[str | None, str | None]:
    """(the commit, ``requirement``'s entry in it) for the newest commit of the living spec at or before ``moment``'s
    second, with the engine's own entry parser; (None, None) when no commit is that old."""
    spec = knowledge.HOME + "/spec.md"
    for line in (git(repo, "log", "--format=%H %ct", "--", spec) or "").splitlines():
        commit, at = line.split()
        if int(at) <= moment:
            shown = git(repo, "show", f"{commit}:{spec}") or ""
            entry = knowledge._entries(shown, "R").get(requirement) if shown.strip() else None
            return commit, entry.text if entry else None
    return None, None


def commits_after(repo: Path | None, moment: float, knowledge) -> dict:
    """The commits of the checkout made after ``moment`` (to the second): how many, and those touching the spec (by
    subject), the code and the tests."""
    if repo is None:
        return {"not_recorded": "neither state.md's repo nor invocation.json's cwd is a git checkout"}
    log = git(repo, "log", "--no-renames", "--format=%x1e%H%x09%ct%x09%s", "--name-only")
    if log is None:
        return {"checkout": tilde(repo), "not_recorded": "git log failed in that checkout"}
    spec = knowledge.HOME + "/spec.md"
    later, same = [], 0
    for chunk in log.split("\x1e")[1:]:
        head, _, rest = chunk.partition("\n")
        _commit, at, subject = (head.split("\t", 2) + ["", ""])[:3]
        files = [path for path in rest.splitlines() if path.strip()]
        same += int(at) == int(moment)
        if int(at) > moment:
            later.append((subject, files))
    return {"checkout": tilde(repo), "spec": spec, "after": len(later), "same_second": same,
            "touching_spec": [tilde(subject[:120]) for subject, files in later if spec in files],
            "touching_src_or_bin": sum(any(path.startswith(CODE) for path in files) for _subject, files in later),
            "touching_test": sum(any(path.startswith(TESTS) for path in files) for _subject, files in later)}


def new_items(state: dict, times: dict, moment: float) -> dict:
    """The work items in the queue at the end that were not there when the note was written.  The queue then is read
    from the run's record: every item a result accepted at or before the note listed in its ``work_items`` (plan,
    carry-forward, add-work), and every item a step accepted by then belongs to."""
    history = state.get("history") or []
    accepted = state.get("accepted") or {}
    before = [entry for entry in history if times.get(entry.get("action")) is not None
              and times[entry["action"]] <= moment]
    known = {entry.get("workitem") for entry in before if entry.get("workitem")}
    for entry in before:
        result = accepted.get(entry.get("action"))
        for row in (result.get("work_items") or []) if isinstance(result, dict) else []:
            if isinstance(row, dict) and row.get("id") is not None:
                known.add(str(row["id"]))
    unknown = [entry.get("action") for entry in history if times.get(entry.get("action")) is None]
    queue = [row for row in state.get("work_items") or [] if isinstance(row, dict)]
    return {"added": [{"id": str(row.get("id")), "title": tilde(row.get("title"))} for row in queue
                      if str(row.get("id")) not in known],
            "untimed_results": len(unknown)}


# ---------------------------------------------------------------------------------------------------------- 8


def last_message(out: Path) -> str | None:
    """The host's last message: the last ``text`` event (Codex, Grok) or the ``result`` event (Claude Code)."""
    text = None
    for event in lines_of(out / "events.jsonl"):
        if event.get("type") == "text" and isinstance(event.get("data"), str) and event["data"].strip():
            text = event["data"]
        elif event.get("type") == "result" and isinstance(event.get("result"), str) and event["result"].strip():
            text = event["result"]
    return tilde(text) if text else None


def told(run: Path, out: Path, ids: list[str]) -> dict:
    """Item 8: the done packet's "Your notes" lines, the report's section, and the host's sentences about notes."""
    done = []
    for path in sorted((run / "packets").glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "\nIt's all complete." in "\n" + text:
            done.append((path.stat().st_mtime, text))
    packet = None
    if done:
        # The block shiploop_owner_notes.done_lines prints: its "Your notes:" line and the "- N<k>: ..." lines under it.
        lines = max(done)[1].splitlines()
        start = next((index for index, line in enumerate(lines) if line.startswith("Your notes:")), None)
        packet = []
        for line in lines[start:] if start is not None else []:
            if packet and not line.startswith("- N"):
                break
            packet.append(line)
    report = run / "report.html"
    section = None
    if report.is_file():
        page = report.read_text(encoding="utf-8", errors="replace")
        at = page.find("<h2>Your notes</h2>")
        if at >= 0:
            end = page.find("<h2>", at + 5)
            section = tilde(fold(html.unescape(TAG.sub(" ", page[at:end if end >= 0 else len(page)])))[:1200])
    message = last_message(out)
    naming = re.compile("|".join(r"\b" + re.escape(ident) + r"\b" for ident in ids) + ("|" if ids else "") + r"note",
                        re.IGNORECASE)
    sentences = [fold(found.group(1)) for found in SENTENCE.finditer(message or "")]
    return {"done_packet_lines": packet if done else None, "report_has_section": section is not None if report.is_file()
            else None, "report_section": section,
            "last_message_sentences": [sentence for sentence in sentences if naming.search(sentence)]
            if message else None}


# ---------------------------------------------------------------------------------------------------------- read


def read(out: Path, modules) -> dict:
    defaults, knowledge, owner_notes, store = modules
    row = {"name": out.name, **harness(out)}
    row["stand_in"] = stand_in(load(out.with_name(out.name + "-requester.json")))
    run, row["run_folders"] = run_folder(out, store)
    row["run"] = tilde(run) if run else None
    if run is None:
        return row
    state = store.read_record(run / "state.md")
    row.update(status=state.get("status"), stage=state.get("stage"), revision=state.get("revision"))
    entries = defaults.recorded(state) or []
    row["defaults"] = [tilde(line) for line in defaults.row_lines(entries)] if entries else []
    sent = (row["stand_in"] or {}).get("note_id")
    if not sent:
        row["notes"] = None
        row["why_no_notes"] = ("no stand-in record" if row["stand_in"] is None else
                               "the stand-in sent nothing: " + str(row["stand_in"].get("ended") or "no reason recorded"))
        return row
    try:
        found = owner_notes.read(run)
    except owner_notes.NoteError as exc:
        row.update(notes=None, why_no_notes=f"the notes folder cannot be read: {exc}")
        return row
    rows = lines_of(run / "trace.jsonl")
    history = state.get("history") or []
    times = accepted_times(run, rows)
    ledger = owner_notes.ledger(state)
    refusals = gate(rows, [note["id"] for note in found])
    spec_at = next((times.get(entry.get("action")) for entry in history
                    if entry.get("stage") == "spec" and entry.get("outcome") == "done"), None)
    end = row.get("ended_ts") or max((traced.get("ts") or 0 for traced in rows), default=None) or None
    repo = checkout(state, out)
    row["end_from"] = "result.json span" if row.get("ended_ts") else "the last trace row (not ended)"
    row["last_command"] = last_command(rows)
    row["gate"] = [{key: value for key, value in refusal.items() if key != "ts"} for refusal in refusals]
    row["notes"] = []
    for note in found:
        ident = note["id"]
        item = {"id": ident, "written_at": note["written_at"], "words": note["text"], "sent_by_stand_in": ident == sent}
        when = written(note, rows, history, times)
        moment = when.pop("moment")
        item.update(when)
        row["notes"].append(item)
        history_rows = ledger.get(ident, [])
        item["ledger"] = [{key: value for key, value in entry.items() if key != "note"}
                          | ({"item_fate": owner_notes.item_fate(state, entry["item"])} if entry.get("item") else {})
                          for entry in history_rows]
        item["standing"] = owner_notes.standing(history_rows)
        item["owed_by"] = owner_notes.owed_by(history_rows) if item["standing"] != "settled" else None
        if moment is None:
            continue
        item["seconds_from_list"] = round(moment - spec_at, 1) if spec_at else None
        item["minutes_to_end"] = round((end - moment) / 60, 1) if end else None
        # 5. The gate's refusals naming this note, before its first row and before the row that settled it.
        first_row = times.get(history_rows[0]["action"]) if history_rows else None
        settling = next((times.get(entry["action"]) for entry in history_rows
                         if entry["did"] in owner_notes.SETTLES), None)
        naming = [refusal for refusal in refusals if ident in refusal["notes"] and (refusal["ts"] or 0) >= moment]
        item["refusals"] = len(naming)
        item["refusals_before_first_row"] = (sum((refusal["ts"] or 0) < first_row for refusal in naming)
                                             if first_row else None)
        item["refusals_before_settled"] = (sum((refusal["ts"] or 0) < settling for refusal in naming)
                                           if settling else None)
        # 6. Whether the model was given its words.
        words = SENTENCE.match(note["text"].strip())
        item["given"] = given(out, fold(words.group(1) if words else note["text"]), ident)
        # 7. What the run did after it.
        requirement = (row["stand_in"] or {}).get("requirement") if ident == sent else None
        item["requirement"] = requirement
        if requirement is None:
            item["entry_when_written_from"] = ("not recorded: the stand-in's chosen row names no requirement"
                                               if ident == sent else "no requirement: not the stand-in's note")
            commit = then = now = None
        elif repo is None:
            item["entry_when_written_from"] = "not recorded: no git checkout"
            commit = then = now = None
        else:
            commit, then = spec_then(repo, requirement, moment, knowledge)
            now = knowledge.entries(repo, "spec.md").get(requirement)
            item["entry_when_written_from"] = (
                f"commit {commit[:7]}, the newest of {knowledge.HOME}/spec.md at or before the note, unverified"
                if then is not None else f"not recorded: no commit of {knowledge.HOME}/spec.md at or before the note"
                if commit is None else f"not recorded: commit {commit[:7]} has no {requirement}")
        item["entry_when_written"] = then
        item["entry_at_end"] = now.text if now else None
        item["entry_at_end_is"] = (None if requirement is None or repo is None else
                                   "gone" if now is None else "retired" if now.retired else "current")
        item["differ"] = None if then is None or now is None else fold(then) != fold(now.text)
        item["commits_after"] = commits_after(repo, moment, knowledge)
        item["new_items"] = new_items(state, times, moment)
    row["told"] = told(run, out, [note["id"] for note in found])
    return row


# ---------------------------------------------------------------------------------------------------------- show


def show(row: dict) -> None:
    print(f"== {row['name']}: {row.get('host')} {row.get('model')} {row.get('effort')}")
    if not row.get("ended"):
        print(f"   not ended (started {row.get('started')}); what the run folder shows so far:")
    else:
        print(f"   1. outcome {row['outcome']} ({row['basis']}) | verdicts {row['verdicts']}")
        print("      checks " + ", ".join(f"{check['check']} {'pass' if check['pass'] else 'FAIL'}"
                                       for check in row["checks"]))
        print("      start-up checks: " + ", ".join(
            f"{probe} {'absent' if found is None else 'pass' if found['pass'] else 'FAIL'}"
            for probe, found in row["startup"].items()))
        for probe, found in row["startup"].items():
            if found and not found["pass"]:
                print(f"         {probe} FAILED (exit {found['returncode']}): ...{fold(found['output_end'])}"
                      if found["output_end"] != "no output recorded" else
                      f"         {probe} FAILED (exit {found['returncode']}): no output recorded")
        print(f"      {row['started']} to {row['ended_at']}, {row['minutes']} minutes | turns {row['turns']}, model calls "
              f"{row['model_calls']}, output tokens {row['output_tokens']}, cost {row['cost_usd']} | spec "
              f"{row['spec_seconds']} s, test-strategy {row['strategy_seconds']} s")
    print(f"      run folders {row['run_folders']}; read {row.get('run')}"
          + (f"; engine {row['status']} at {row['stage']}, revision {row['revision']}" if row.get("run") else ""))
    if row.get("run"):
        print(f"      the list of defaults: {len(row['defaults'])} rows")
        for line in row["defaults"]:
            print(f"         {line}")
    side = row["stand_in"]
    if side is None:
        print("   2. stand-in: no stand-in record")
    else:
        print(f"   2. stand-in: mode {side['mode']}, waited for {side['stage_waited_for']}, seen {side['stage_seen_at']}; "
              f"chosen row {side['chosen']}: {side['row']}")
        print(f"      class {side['row_class']}" + (f" ({side['row_class_note']})" if side["row_class_note"] else "")
              + f"; note sent {side['note_sent']}; note command {side['note_id']}, exit {side['note_exit']}"
              + (f"; ended: {side['ended']}" if side["ended"] else ""))
        for line in (side["note_reply"] or "").splitlines():
            print(f"      | {line}")
    if row.get("run") is None or row.get("notes") is None:
        print(f"   {row.get('why_no_notes') or 'no run folder'}; nothing more is read")
        return
    last = row["last_command"]
    print(f"   the gate: {len(row['gate'])} refusals in the trace; the run is {row['status']}; its last ShipLoop command "
          + (f"{last['verb']} at {last['stage']} (exit {last['exit']})"
             + (", the gate's refusal" if last["gate_refusal"] else "") if last else "not recorded"))
    for refusal in row["gate"]:
        print(f"      {refusal['at']} {refusal['stage']} {refusal['verb']} {refusal['notes']}"
              f"{'' if refusal['gate'] else ' (names a note; not the gate refusal)'}: {refusal['first_line']}")
    for item in row["notes"]:
        show_note(item, row["end_from"])
    show_told(row["told"])


def show_note(item: dict, end_from: str) -> None:
    print(f"   note {item['id']}" + (" (the stand-in's)" if item["sent_by_stand_in"] else "") + f": \"{item['words']}\"")
    if "not_recorded" in item:
        print(f"      not recorded: {item['not_recorded']}")
        return
    last, opened = item["last_accepted_before"], item["open_then"]
    print(f"   3. written {item['written_at']} (in the trace: {item['in_trace'] or 'no note command'}) | open then: "
          + (f"{label(opened)}, from {opened['from']}" if opened else "not recorded in the trace")
          + f" | last accepted before: {label(last)}{', accepted ' + last['accepted_at'] if last else ''}")
    print(f"      {item['seconds_from_list']} s after the list was printed (the spec's first accepted result); "
          f"{item['minutes_to_end']} minutes before the end ({end_from})")
    print(f"   4. ledger: {len(item['ledger'])} rows; stands {item['standing']}"
          + (f", owed by {item['owed_by']}" if item["owed_by"] else ""))
    for entry in item["ledger"]:
        print(f"      step {entry['step']} {entry['stage']}{' ' + entry['workitem'] if entry.get('workitem') else ''}: "
              f"{entry['did']}: {tilde(entry['detail'])}"
              + (f" | item {entry['item']} ({entry['item_fate']})" if entry.get("item") else ""))
    print(f"   5. the gate: {item['refusals']} refusals naming {item['id']} after it was written; before its first row "
          f"was accepted {item['refusals_before_first_row']}, before the row that settled it "
          f"{item['refusals_before_settled']}")
    seen = item["given"]
    if "not_recorded" in seen:
        print(f"   6. given to the model: not recorded ({seen['not_recorded']})")
    else:
        first = seen["first_naming_it"]
        print(f"   6. given to the model ({seen['source']}, words \"{seen['words']}\"): {seen['summary']}")
        print("      the first output given to it that names " + item["id"] + ": "
              + (f"{first['kind']}: \"{fold(first['start'])}\"" if first else "none"))
    print(f"   7. {item['requirement'] or 'requirement'}: when the note was written, {item['entry_when_written_from']}")
    for line in (item["entry_when_written"] or "").splitlines():
        print("         | " + tilde(line))
    if item["requirement"]:
        print(f"      at the end: {item['entry_at_end_is']}; differs from the entry when the note was written: "
              f"{item['differ']}")
        for line in (item["entry_at_end"] or "").splitlines():
            print("         | " + tilde(line))
    commits = item["commits_after"]
    print("      commits after it: " + (f"not recorded ({commits['not_recorded']})" if "not_recorded" in commits else
                                       f"{commits['after']}"
                                       + (f" (and {commits['same_second']} in its second)" if commits["same_second"] else "")
                                       + f"; touching {commits['spec']}: {len(commits['touching_spec'])}; touching src/ "
                                         f"or bin/: {commits['touching_src_or_bin']}; touching test/: "
                                         f"{commits['touching_test']}"))
    for subject in commits.get("touching_spec") or []:
        print(f"         {subject}")
    added = item["new_items"]
    print("      work items at the end that were not there when it was written: "
          + (", ".join(f"{entry['id']} ({entry['title']})" for entry in added["added"]) or "none")
          + (f" ({added['untimed_results']} accepted results have no recorded time)" if added["untimed_results"] else ""))


def show_told(told_: dict) -> None:
    lines = told_["done_packet_lines"]
    print("   8. the done packet: " + ("no done packet" if lines is None else "no \"Your notes\" lines" if not lines
                                     else f"{len(lines)} lines"))
    for line in lines or []:
        print(f"      | {tilde(line)}")
    print("      report.html: " + ("absent" if told_["report_has_section"] is None else
                                   "no section \"Your notes\"" if not told_["report_has_section"] else
                                   f"section \"Your notes\": {told_['report_section']}"))
    sentences = told_["last_message_sentences"]
    print("      the host's last message: " + ("none found" if sentences is None else
                                               f"{len(sentences)} sentences name a note"))
    for sentence in sentences or []:
        print(f"      | {sentence}")


def export(row: dict, folder: Path) -> None:
    """The four files a reader blind to the checks is given, for the stand-in's note: the chosen row as printed, the
    note's words, the requirement's entry when the note was written (its first line says what it is) and at the end."""
    item = next((note for note in row.get("notes") or [] if note.get("sent_by_stand_in")), None)
    side = row.get("stand_in") or {}
    if item is None or "entry_when_written_from" not in item:
        return
    first = (f"{item['requirement']} as the newest commit of the spec at or before {item['id']} ({item['written_at']}) "
             "holds it, unverified:" if item["entry_when_written"] is not None else
             f"{item['requirement']} when {item['id']} was written: {item['entry_when_written_from']}")
    folder.mkdir(parents=True, exist_ok=True)
    for name, body in (("row.txt", side.get("row")), ("answer.txt", item["words"]),
                       ("before.md", f"{first}\n\n{item['entry_when_written']}" if item["entry_when_written"] is not None
                        else first),
                       ("after.md", item["entry_at_end"] if item["entry_at_end"] is not None else item["entry_at_end_is"])):
        (folder / name).write_text(str(body) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("root", type=Path)
    parser.add_argument("names", nargs="*")
    parser.add_argument("--json", type=Path)
    parser.add_argument("--export", type=Path)
    args = parser.parse_args()
    modules = engine(args.root)
    folders = ([args.root / name for name in args.names] if args.names else
               sorted(path for path in args.root.iterdir() if path.is_dir() and (path / "invocation.json").is_file()))
    rows = []
    for folder in folders:
        if not folder.is_dir():
            print(f"== {folder.name}: no folder yet")
            continue
        rows.append(read(folder, modules))
        show(rows[-1])
        if args.export:
            export(rows[-1], args.export / folder.name)
    if args.json:
        args.json.write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
