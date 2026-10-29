#!/usr/bin/env python3
"""The run trace: what a ShipLoop run did, in order, in one append-only file, and the reader that explains it.

``RUN/trace.jsonl`` gets one JSON line per event, appended as it happens:
- ``command``: every ShipLoop command that names the run: verb, action, exit code, milliseconds, the revision, stage
  and action before and after, the results it accepted, and the refusal text when it exited non-zero;
- ``packet``: every packet ShipLoop printed: action, stage, work item, its characters in the file and as printed, and
  the copy kept as sent (``packets/sent/<sha>.md``), since ``next`` rewrites ``packets/<action>.md`` in place;
- ``hook``: every keepalive stop decision for a session bound to the run, with the text the hook put into the turn.

Skill-tool calls stay in ``skill-calls.jsonl``; the reader merges them.  The trace is evidence, never state:
``state.md`` stays the authority, nothing resumes from the trace, and a failed append never fails a command.

    shiploop trace --run-dir RUN                 # digest: every stage done, current or pending; steps run; recent events
    shiploop trace --run-dir RUN --action ID     # one action: its packets as sent, its commands, refusals and hooks, files
    shiploop trace --run-dir RUN --json          # the whole model, for a program or a model to query
    shiploop trace --run-dir RUN --html [PATH]   # a self-contained page (default RUN/trace.html)

A run saved before the trace existed still reads: its steps come from ``state.md`` and ``timeline.json`` and its
packets are the last copy of each, and the reader says so.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
from typing import Any, Iterable, Mapping, Sequence

import shiploop_store as store

TRACE_FILE = "trace.jsonl"
SENT_DIR = "packets/sent"
PAGE = "trace.html"
SCHEMA = "shiploop-trace/v1"
SKILL_CALLS = "skill-calls.jsonl"
# Past this size the trace stops growing and the reader says so; a long run writes a few megabytes.
TRACE_LIMIT = 32 * 1024 * 1024
TEXT_LIMIT = 4000  # characters of refusal or hook text kept in one line
# The page embeds each packet's text as sent, screened line by line, up to these bounds; past them it names the file.
PAGE_PACKET_LIMIT = 256 * 1024
PAGE_TEXT_LIMIT = 12 * 1024 * 1024
# Commands that only read or display; they are not run activity.
UNTRACED = frozenset(("view", "hook-status", "trace", "graph-dry-run", "-h", "--help"))
# Set by the CLI while a traced command runs on a current run; packets printed at any other time (a routed verb such as
# chain, a test calling emit directly) write nothing.
ACTIVE = False


# ---------------------------------------------------------------------------------------------------------- writer


def _stamp(now: float | None = None) -> dict[str, Any]:
    ts = time.time() if now is None else now
    return {"ts": round(ts, 3), "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))}


def _clip(value: Any, limit: int = TEXT_LIMIT) -> Any:
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + f"… [{len(value) - limit} more characters]"
    return value


def record(root: str | Path, kind: str, **fields: Any) -> bool:
    """Append one event to the run's trace; True when a line was written.  Never raises.

    Only a run directory (one holding ``state.md``) gets a trace, and only through a regular file opened without
    following a symlink and without blocking (a FIFO in its place is refused, never waited on).  One ``write`` on an
    ``O_APPEND`` descriptor keeps concurrent writers (a command and a hook) from interleaving lines.  Callers that are
    not a command on a loaded run check ``current_state`` first.
    """
    try:
        run = Path(root)
        if not (run / "state.md").is_file():
            return False
        path = run / TRACE_FILE
        try:
            if path.stat().st_size >= TRACE_LIMIT:
                return False
        except FileNotFoundError:
            pass
        event = {"v": 1, **_stamp(), "kind": kind,
                 **{key: _clip(value) for key, value in fields.items() if value is not None}}
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(path, flags, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                return False
            os.write(fd, line.encode("utf-8"))
        finally:
            os.close(fd)
        return True
    except (OSError, TypeError, ValueError):
        return False


def current_state(root: str | Path | None) -> dict[str, Any] | None:
    """The saved state of ``root`` when it loads as a current run, else None (never raises).  Nothing writes into a
    retired or unloadable run: it must stay as it was."""
    import shiploop_navigator as navigator

    if root is None:
        return None
    try:
        state = store.read_record(Path(root) / "state.md")
        if not isinstance(state, dict) or navigator.retired_run_reason(state) is not None:
            return None
        navigator.validate(state)
    except (OSError, ValueError, KeyError, TypeError, store.StorageError):
        return None
    return state


def keep_sent(root: str | Path, text: str) -> tuple[str, str]:
    """Keep ``text`` as sent, once per content; returns its short hash and its path relative to the run."""
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    relative = f"{SENT_DIR}/{sha}.md"
    target = Path(root) / relative
    if not target.is_file():
        store.atomic_write_text(target, text)
    return sha, relative


def record_packet(root: str | Path, state: Mapping[str, Any], text: str, printed: str) -> bool:
    """Record one printed packet of ``state`` and keep its text, and the printed head when that is not the whole,
    as sent.  Only while a traced command runs (``ACTIVE``)."""
    if not ACTIVE:
        return False
    try:
        sha, file = keep_sent(root, text)
        whole = printed.startswith(text)
        head = None if whole else keep_sent(root, printed)[1]
    except (OSError, store.StorageError):
        return False
    child = state.get("active_improve") or {}
    stage, action, item = _cursor(state)
    import shiploop_owner_notes as owner_notes

    return record(root, "packet", action=child.get("improve_action") or (action or {}).get("id"),
                  stage="improve" if child else stage, item=item, reviewed=child.get("stage"),
                  status=state.get("status"), rev=state.get("revision"), chars=len(text), printed=len(printed),
                  whole=whole, sha=sha, file=file, head_file=head, notes=owner_notes.quoted_ids(printed) or None)


def cursor_facts(state: Mapping[str, Any]) -> dict[str, Any]:
    """The run position a command event records before and after: revision, stage, action and status."""
    improve = state.get("active_improve")
    stage, action, _ = _cursor(state)
    if improve:
        stage, action = "improve", {"id": improve.get("improve_action")}
    return {"rev": state.get("revision"), "stage": stage, "cursor": (action or {}).get("id"),
            "status": state.get("status")}


def accepted_between(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The history entries ``after`` holds beyond ``before``: what one command accepted."""
    start = len(before.get("history") or [])
    return [{"action": entry.get("action"), "stage": entry.get("stage"), "item": entry.get("workitem"),
             "outcome": entry.get("outcome")} for entry in (after.get("history") or [])[start:]]


def record_command(root: str | Path, argv: Sequence[str], code: int, started: float, *,
                   before: Mapping[str, Any] | None, after: Mapping[str, Any] | None, error: str | None,
                   note: str | None = None, held: Sequence[str] | None = None) -> bool:
    """Record one ShipLoop command line that named the run: ``before`` and ``after`` are the saved states around it
    (``after`` is None when the command saved nothing it could report).  ``note`` is the owner note a ``note`` command
    wrote, ``held`` the notes a held callback printed; the notes an accepted step delivered come from the two states."""
    verb = argv[0] if argv else ""
    if verb in UNTRACED:
        return False
    first = cursor_facts(before) if before is not None else None
    last = cursor_facts(after) if after is not None else first
    pairs = {name: [(first or {}).get(name), (last or {}).get(name)] for name in ("rev", "stage", "cursor")} if last else {}
    accepted = accepted_between(before, after) if before is not None and after is not None else []
    known = set((before or {}).get("owner_notes") or {})
    delivered = sorted((set((after or {}).get("owner_notes") or {}) - known), key=lambda note: int(note[1:]))
    return record(
        root, "command", verb=verb, action=_flag(argv, "--action"), exit=code,
        ms=round((time.monotonic() - started) * 1000),
        **pairs, status=(last or {}).get("status"), accepted=accepted or None, error=error if code else None,
        note=note, held=list(held) if held else None, delivered=delivered or None,
    )


def record_stop(run_dir: Any, host: str, session: str | None, decision: Mapping[str, Any]) -> bool:
    """Record one keepalive stop decision in the bound run's trace, with the text it put into the turn."""
    if not isinstance(run_dir, str) or not run_dir or current_state(run_dir) is None:
        return False
    return record(run_dir, "hook", hook="stop", host=host, session=session, decision=decision.get("decision"),
                  why=decision.get("why"), text=decision.get("reason") or decision.get("notice"))


def _flag(argv: Sequence[str], name: str) -> str | None:
    for index, value in enumerate(argv):
        if value == name and index + 1 < len(argv):
            return argv[index + 1]
        if value.startswith(name + "="):
            return value.split("=", 1)[1]
    return None


def _cursor(state: Mapping[str, Any]) -> tuple[str | None, Mapping[str, Any] | None, str | None]:
    """The cursor's stage, action and work item, without validating (a display record must not refuse)."""
    import shiploop_navigator as navigator

    try:
        return navigator._active_cursor(state)
    except (KeyError, IndexError, TypeError, ValueError):
        return state.get("stage"), state.get("action"), None


# ---------------------------------------------------------------------------------------------------------- reader


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """The lines of a JSONL file that parse as objects; a partly written last line is skipped."""
    try:
        raw = path.read_bytes()
    except OSError:
        return []
    rows = []
    for line in raw.decode("utf-8", errors="replace").splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _parse(stamp: Any) -> float | None:
    if isinstance(stamp, (int, float)):
        return float(stamp)
    if not isinstance(stamp, str):
        return None
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _iso(ts: float | None) -> str | None:
    return None if ts is None else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def build(root: str | Path, *, now: float | None = None) -> dict[str, Any]:
    """The reader's model of one run: run facts, the plan of every stage, the steps run, and every event in order."""
    import shiploop_navigator as navigator
    import shiploop_prompts as guidance

    run = Path(root)
    state = store.read_record(run / "state.md")
    clock = time.time() if now is None else now
    timeline = navigator.load_timeline(run)
    accepted_at = {action: _parse(stamp) for action, stamp in (timeline.get("accepted") or {}).items()}
    trace_path = run / TRACE_FILE
    traced = trace_path.is_file()
    raw = _read_jsonl(trace_path)
    events: list[dict[str, Any]] = [dict(row) for row in raw if isinstance(row.get("kind"), str)]
    # Refusals and hook text name files by absolute path; RUN reads shorter and matches the rest of the reader.
    for event in events:
        for name in ("error", "text"):
            if isinstance(event.get(name), str):
                event[name] = event[name].replace(str(run) + os.sep, "RUN/").replace(str(run), "RUN")
    for row in _read_jsonl(run / SKILL_CALLS):
        if "gate" in row:
            events.append({"kind": "skill", "ts": row.get("ts"), "at": row.get("at"), "gate": row.get("gate"),
                           "action": row.get("action"), "why": row.get("why")})
        else:
            events.append({"kind": "skill", "ts": row.get("ts"), "at": row.get("at"), "skill": row.get("skill"),
                           "args": row.get("args")})
    # A step no traced command accepted (the run predates the trace, or began before an upgrade) is the one event the
    # timeline recorded for it, so the history never loses a step the trace did not see.
    traced_since = min((float(row.get("ts") or 0) for row in events if row["kind"] in ("command", "packet", "hook")),
                       default=None)
    covered = {row.get("action") for event in events if event["kind"] == "command" for row in event.get("accepted") or []}
    legacy = 0
    for entry in state.get("history") or []:
        ts = accepted_at.get(entry.get("action"))
        if ts is not None and entry.get("action") not in covered:
            legacy += 1
            events.append({"kind": "accepted", "ts": ts, "at": _iso(ts), "action": entry.get("action"),
                           "stage": entry.get("stage"), "item": entry.get("workitem"),
                           "outcome": entry.get("outcome")})
    events.sort(key=lambda row: float(row.get("ts") or 0))

    # Attribute each event to an action: its own, or (``for_action``) the action current when it happened, which is
    # the last packet's.  A command records after the packet it printed, so its new cursor is already current.
    current = None
    seen: set[tuple[Any, Any]] = set()
    for index, event in enumerate(events):
        event["i"] = index
        if event["kind"] == "packet":
            current = event.get("action")
            event["repeat"] = (current, event.get("sha")) in seen
            seen.add((current, event.get("sha")))
        elif not event.get("action"):
            event["for_action"] = current
        cursor = event.get("cursor") if event["kind"] == "command" and event.get("exit") == 0 else None
        if isinstance(cursor, list) and len(cursor) == 2 and cursor[1]:
            current = cursor[1]

    def owner(event: Mapping[str, Any]) -> Any:
        return event.get("action") or event.get("for_action")

    by_action: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        if owner(event):
            by_action[owner(event)].append(event)
    packets = {event.get("action"): event for event in events if event["kind"] == "packet"}

    def tally(action: Any) -> dict[str, int]:
        rows = by_action.get(action, [])
        return {
            "packets": sum(row["kind"] == "packet" for row in rows),
            "reprints": sum(row["kind"] == "packet" and row.get("repeat") for row in rows),
            "refusals": sum(refused(row) for row in rows),
            "hooks": sum(row["kind"] == "hook" for row in rows),
        }

    improve_results = state.get("improve_results") or {}
    history = list(state.get("history") or [])
    first_packet = {}
    for event in events:
        if event["kind"] == "packet" and event.get("action") not in first_packet:
            first_packet[event.get("action")] = float(event.get("ts") or 0)
    started = _parse(timeline.get("started")) or (float(events[0]["ts"]) if events else None)
    steps = []
    previous = started
    for number, entry in enumerate(history, 1):
        action = entry.get("action")
        at = accepted_at.get(action)
        begin = first_packet.get(action, previous)
        result = (state.get("accepted") or {}).get(action) or {}
        steps.append({
            "n": number, "action": action, "stage": entry.get("stage"), "item": entry.get("workitem"),
            "outcome": entry.get("outcome"), "at": _iso(at),
            "seconds": round(at - begin) if at is not None and begin is not None and at >= begin else None,
            "headline": _headline(result, entry.get("summary")), "improve": action in improve_results,
            "result": f"results/{action}.md" if (run / "results" / f"{action}.md").is_file() else None,
            **tally(action),
        })
        if at is not None:
            previous = at

    stage, action, item = _cursor(state)
    improve = state.get("active_improve")
    now_action = (improve or {}).get("improve_action") or (action or {}).get("id")
    last_packet = packets.get(now_action)
    packet_file = (last_packet or {}).get("file")
    if packet_file is None and now_action and (run / "packets" / f"{now_action}.md").is_file():
        packet_file = f"packets/{now_action}.md"
    since = first_packet.get(now_action)
    now_block = None
    if state.get("status") != "done":
        now_block = {
            "stage": "improve" if improve else stage, "item": item, "action": now_action,
            "reviewing": improve.get("stage") if improve else None,
            "purpose": (f"the improve skill is reviewing the {improve.get('stage')} result" if improve
                        else guidance.STAGE_PURPOSE.get(stage or "", "")),
            "since": _iso(since), "packet": packet_file, **tally(now_action),
        }

    plan = _plan(state, accepted_at, improve_results, tally)
    request = request_model(run, state, accepted_at, improve_results)
    notes = notes_model(run, state, events, accepted_at)
    counts = Counter(event["kind"] for event in events)
    commands = [event for event in events if event["kind"] == "command"]
    hooks = [event for event in events if event["kind"] == "hook"]
    last_ts = max([float(event.get("ts") or 0) for event in events]
                  + [stamp for stamp in accepted_at.values() if stamp is not None], default=0)
    size = trace_path.stat().st_size if traced else 0
    # A finished run's elapsed time ends at its last event, not at the moment of reading.
    end = (last_ts or clock) if state.get("status") in ("done", "halted") else clock
    return {
        "schema": SCHEMA,
        "generated": _iso(clock),
        "run": {
            "dir": str(run), "id": state.get("run_id"), "goal": _goal(state, navigator),
            "prompt": state.get("prompt"), "repo": state.get("repo"), "status": state.get("status"),
            "status_reason": state.get("status_reason"), "revision": state.get("revision"),
            "started": _iso(started), "last_event": _iso(last_ts or None),
            "elapsed": round(end - started) if started else None,
            "traced": traced, "traced_since": _iso(traced_since), "untraced_steps": legacy,
            "trace_bytes": size, "capped": size >= TRACE_LIMIT,
            "work_items": len(state.get("work_items") or []), "work_index": state.get("work_index"),
            "cli": str(Path(__file__).resolve().parent / "shiploop"),
        },
        "now": now_block,
        "request": request,
        "notes": notes,
        "plan": plan,
        "steps": steps,
        "events": events,
        "counts": {
            "accepted": len(history), "commands": counts["command"], "packets": counts["packet"],
            "reprints": sum(bool(event.get("repeat")) for event in events),
            "refusals": sum(refused(event) for event in commands),
            "held": sum(bool(event.get("held")) for event in commands),
            "checks_failed": sum(event.get("exit") not in (0, None) and event.get("verb") == "check" for event in commands),
            "continuations": sum(event.get("decision") == "continue" for event in hooks),
            "stops": sum(event.get("decision") == "allow" for event in hooks),
            "skills": counts["skill"],
        },
    }


def refused(event: Mapping[str, Any]) -> bool:
    """A command that exited non-zero, other than a check (``shiploop check``), which reports and never completes, and a
    callback held once for owner notes, which refuses nothing the model submitted."""
    return (event.get("kind") == "command" and event.get("exit") not in (0, None) and event.get("verb") != "check"
            and not event.get("held"))


def notes_model(run: Path, state: Mapping[str, Any], events: Sequence[Mapping[str, Any]],
                accepted_at: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every owner note: its text (screened), when it was written, and where it stands: waiting (no print has shown
    it), shown (a packet quoted it whole, or a held callback printed it) or delivered (by which step, and whether that
    step's summary cites its id)."""
    import shiploop_owner_notes as owner_notes

    done = owner_notes.delivered(state)
    steps = {entry.get("action"): index for index, entry in enumerate(state.get("history") or [], 1)}
    results = state.get("accepted") or {}
    quoted_in: dict[str, list[Any]] = defaultdict(list)
    held_in: dict[str, list[Any]] = defaultdict(list)
    for event in events:
        for note_id in (event.get("notes") or []) if event["kind"] == "packet" else []:
            if event.get("action") not in quoted_in[note_id]:
                quoted_in[note_id].append(event.get("action"))
        for note_id in (event.get("held") or []) if event["kind"] == "command" else []:
            held_in[note_id].append(event.get("action"))
    # What the current action's prints showed, from the record the hold reads (the trace may lack a line).
    shown = owner_notes.read_shown(run)
    for key, into in (("packet", quoted_in), ("held", held_in)):
        for note_id in shown.get(key) or []:
            if shown["action"] not in into[note_id]:
                into[note_id].append(shown["action"])
    rows = []
    for note in owner_notes.notes(run):
        note_id, action = note["id"], done.get(note["id"])
        summary = str((results.get(action) or {}).get("summary") or "") if action else ""
        rows.append({
            "id": note_id, "at": note["written_at"], "text": _screened(note["text"]), "chars": len(note["text"]),
            "file": note["file"], "state": "delivered" if action else
            "shown" if quoted_in.get(note_id) or held_in.get(note_id) else "waiting",
            "quoted_in": quoted_in.get(note_id, []), "held_in": held_in.get(note_id, []), "delivered_by": action,
            "step": steps.get(action), "delivered_at": _iso(accepted_at.get(action)) if action else None,
            "cited": bool(re.search(r"\b" + note_id + r"\b", summary)) if action else None,
        })
    return rows


def _headline(result: Mapping[str, Any], summary: Any) -> str:
    text = result.get("headline") or result.get("summary") or summary or ""
    text = " ".join(str(text).split())
    if not result.get("headline"):
        cut = text.find(". ")
        text = text[:cut + 1] if 0 < cut < 160 else text
    return text[:160] + ("…" if len(text) > 160 else "")


def _goal(state: Mapping[str, Any], navigator: Any, limit: int = 140) -> str:
    """The request's title, cut at a word boundary."""
    try:
        text = navigator._title_from_prompt(state.get("prompt") or "")
    except (TypeError, ValueError, AttributeError):
        text = " ".join(str(state.get("prompt") or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"


# ---------------------------------------------------------------------------------------------------------- request

# The planning stages that expand the request, in order; each item's step-plan expands its work item.
EXPANDING = ("intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare")
# Intake cites S<n> at the start of each sentence's clause; hosts word the rest differently.  Seen on real runs:
# "S4 outcome: …", "S1: outcome = …", "S1: Outcome: …", "S2: outcome - …", "S1: outcome is …", "S1: Deliver …",
# "S3 (paraphrase): boundary = …", "S1 (paraphrase): Outcome 1: …", "S1 maps to …".
_SENTENCE_READING = re.compile(
    r"(?:^|(?<=\s))S(\d+)(?:\s+(?P<kind>[a-z][a-z /-]{0,30}?):\s"
    r"|\s*\((?:[^()]|\([^()]{0,200}\)){0,600}\)\s*:\s|\s*:\s|\s+maps\s+to\s)")
# The kind a clause opens with when it does not come before the colon ("outcome = …", "Boundary - …", "Outcome 1: …").
_READING_KIND = re.compile(r"(?i)(outcomes?|boundar(?:y|ies)|open questions?|questions?|defaults?|assumptions?|"
                           r"constraints?)(?:\s+\d+)?(?:\s*\([^()]{0,40}\))?\s*(?:[:=–-]|is\b)\s*")
_REQUIREMENT = re.compile(r"^###\s+(R-\d+)\.?\s*(.*)$")
SPEC_LIMIT = 256 * 1024          # bytes of the living spec the reader reads
FIELD_LIMIT = 2000               # characters of one expanded field the model keeps
ANSWER_LIMIT = 8 * 1024          # bytes of one owner answer


def sentence_readings(summary: str) -> dict[int, list[dict[str, str]]]:
    """Intake's summary split by request sentence: S<n> -> [{kind, text}], kind ``reading`` when the clause names
    none.  A paraphrase of the sentence in parentheses is dropped (the sentence is shown beside it).  Text intake did
    not tie to a sentence is not returned; the stage's summary keeps it."""
    marks = list(_SENTENCE_READING.finditer(summary or ""))
    readings: dict[int, list[dict[str, str]]] = defaultdict(list)
    for index, mark in enumerate(marks):
        end = marks[index + 1].start() if index + 1 < len(marks) else len(summary)
        text, kind = summary[mark.end():end].strip().rstrip("|").rstrip(), mark.group("kind")
        if kind is None:
            lead = _READING_KIND.match(text)
            kind, text = (lead.group(1).lower(), text[lead.end():]) if lead else ("reading", text)
            kind = kind[:-3] + "y" if kind.endswith("ies") else kind.rstrip("s")
        readings[int(mark.group(1))].append({"kind": " ".join(kind.split()), "text": text})
    return dict(readings)


def _screened(text: str) -> str:
    """``text`` with each line the credential screen flags replaced by the redaction marker."""
    import shiploop_privacy as privacy

    return "\n".join(privacy.REDACTED_SENSITIVE_VALUE if privacy.sensitive_text(line) else line
                     for line in text.split("\n"))


def _bounded_text(path: Path, limit: int) -> str | None:
    """A regular file's text up to ``limit`` bytes, screened line by line; None when it is missing or not regular."""
    try:
        if path.is_symlink() or not path.is_file():
            return None
        with path.open("rb") as handle:
            raw = handle.read(limit + 1)
    except OSError:
        return None
    return _screened(raw[:limit].decode("utf-8", errors="replace"))


def requirements(path: Path) -> list[dict[str, Any]]:
    """The living spec's requirements (``### R-n. Title`` and the lines under it), with the section each sits in."""
    text = _bounded_text(path, SPEC_LIMIT)
    found: list[dict[str, Any]] = []
    section, current = "", None
    for line in (text or "").splitlines():
        match = _REQUIREMENT.match(line)
        if match:
            current = {"id": match.group(1), "title": match.group(2).strip(), "section": section, "body": []}
            found.append(current)
        elif line.startswith("#"):
            section = line.lstrip("#").strip() if line.startswith("## ") else section
            current = None
        elif current is not None:
            current["body"].append(line)
    for each in found:
        each["body"] = _clip("\n".join(each["body"]).strip(), FIELD_LIMIT)
    return found


def request_model(run: Path, state: Mapping[str, Any], accepted_at: Mapping[str, Any],
                  improve_results: Mapping[str, Any]) -> dict[str, Any]:
    """The request as the owner wrote it beside the request as planning has expanded it so far.

    Original: the verbatim prompt and its sentences S1..Sn (``request.md``).  Expanded, from the current accepted
    results only (a reconciled planning result is superseded): intake's reading of each sentence, each planning
    stage's headline and summary, the living spec's requirements, the work items with their step plans, the plan's
    assumptions, and the owner's answers to questions the run waited on.
    """
    import shiploop_knowledge_home as knowledge
    import shiploop_planning_revision as planning_revision
    import shiploop_request as request_file

    prompt = str(state.get("prompt") or "")
    results = state.get("accepted") or {}
    try:
        current = planning_revision.current_actions(state)
    except (KeyError, TypeError, ValueError):
        current = {}
    stages = []
    for stage in EXPANDING:
        action = current.get((None, stage))
        result = results.get(action) or {}
        stages.append({
            "stage": stage, "action": action, "state": "accepted" if action else "pending",
            "headline": _headline(result, None) if action else None,
            "summary": _clip(" ".join(str(result.get("summary") or "").split()), FIELD_LIMIT) if action else None,
            "at": _iso(accepted_at.get(action)) if action else None, "improve": action in improve_results,
        })
    planning = set(EXPANDING) | {"step-plan"}
    live = set(current.values())
    superseded = [entry.get("action") for entry in state.get("history") or []
                  if entry.get("stage") in planning and entry.get("outcome") == "done" and entry.get("action") not in live]
    intake = results.get(current.get((None, "intake"))) or {}
    readings = sentence_readings(str(intake.get("summary") or ""))
    plan = results.get(current.get((None, "plan"))) or {}
    items = []
    for row in state.get("work_items") or []:
        step_plan = results.get(current.get((row.get("id"), "step-plan"))) or {}
        steps = step_plan.get("steps") if isinstance(step_plan.get("steps"), list) else []
        items.append({"id": row.get("id"), "title": row.get("title"), "context": _clip(row.get("context") or "", FIELD_LIMIT),
                      "steps": [{"id": step.get("id"), "task": _clip(str(step.get("task") or ""), 600),
                                 "deps": step.get("deps") or []} for step in steps if isinstance(step, dict)]})
    assumptions = [{"id": each.get("id"), "assumption": _clip(str(each.get("assumption") or ""), 600),
                    "disposition": each.get("disposition")}
                   for each in plan.get("assumptions") or [] if isinstance(each, dict)]
    answers = []
    for path in sorted((run / "decisions").glob("*.md")) if (run / "decisions").is_dir() else []:
        text = _bounded_text(path, ANSWER_LIMIT)
        if text is not None:
            answers.append({"file": f"decisions/{path.name}", "action": path.stem, "text": text.strip()})
    home = Path(str(state.get("repo") or "")) / knowledge.HOME
    sentences = request_file.sentences(prompt)
    return {
        "original": {"text": prompt, "chars": len(prompt), "file": request_file.REQUEST_FILE,
                     "sentences": [{"n": index, "text": text, "readings": readings.get(index, [])}
                                   for index, text in enumerate(sentences, 1)]},
        "expanded": {
            "through": next((each["stage"] for each in reversed(stages) if each["state"] == "accepted"), None),
            "stages": stages, "mapped": sum(1 for index in range(1, len(sentences) + 1) if readings.get(index)),
            "requirements": requirements(home / "spec.md"), "spec_file": str(home / "spec.md"),
            "architecture_file": str(home / "architecture.md"),
            "work_items": items if any(key[1] == "plan" for key in current) else [],
            "assumptions": assumptions, "answers": answers, "superseded": len(superseded),
        },
    }


def _plan(state: Mapping[str, Any], accepted_at: Mapping[str, Any], improve_results: Mapping[str, Any],
          tally: Any) -> list[dict[str, Any]]:
    """Every stage of the run as a slot: done, current, reopened (run before, then invalidated) or pending."""
    import shiploop_navigator as navigator
    import shiploop_prompts as guidance

    prelude, inner, outer = navigator.graph(state)
    try:
        done, _ = navigator._accepted_done(state)
    except (KeyError, TypeError, ValueError):
        done = {}
    stage, _, owner = _cursor(state)
    finished = state.get("status") == "done"
    runs: dict[tuple[Any, str], list[str]] = defaultdict(list)
    outcomes: dict[tuple[Any, str], Counter] = defaultdict(Counter)
    for entry in state.get("history") or []:
        key = (entry.get("workitem") if entry.get("stage") in inner else None, entry.get("stage"))
        runs[key].append(entry.get("action"))
        outcomes[key][entry.get("outcome")] += 1
    current_key = None if finished else ((owner, stage) if stage in inner else (None, stage))
    results = state.get("accepted") or {}
    groups = {node: name for name, nodes in guidance.INNER_GROUPS for node in nodes}

    def slot(item: str | None, node: str) -> dict[str, Any]:
        key = (item, node)
        action = done.get(key)
        ran = runs.get(key, [])
        if key == current_key:
            state_name = "current"
        elif action or (finished and ran):
            state_name = "done"
        elif ran:
            state_name = "reopened"
        else:
            state_name = "pending"
        latest = action or (ran[-1] if ran else None)
        result = results.get(latest) or {}
        tallied = Counter()
        for each in ran:
            tallied.update(tally(each))
        # implement is accepted once per step of the item's current step plan, so its count is steps, not reruns.
        plan_steps = (results.get(done.get((item, "step-plan"))) or {}).get("steps") if node == "implement" else None
        return {
            "stage": node, "state": state_name, "group": groups.get(node), "action": latest,
            "at": _iso(accepted_at.get(latest)) if latest else None, "outcome": result.get("outcome"),
            "headline": _headline(result, None) if result else None, "runs": len(ran),
            "sent_back": outcomes[key]["send-back"],
            "steps": len(plan_steps) if isinstance(plan_steps, list) else None,
            "improve": any(each in improve_results for each in ran),
            "purpose": guidance.STAGE_PURPOSE.get(node, ""), **dict(tallied),
        }

    rows = [{"label": "Preparation", "phase": "preparation", "item": None,
             "slots": [slot(None, node) for node in prelude]}]
    items = state.get("work_items") or []
    planned = any(key[1] == "plan" for key in done)
    for index, row in enumerate(items if planned else []):
        rows.append({"label": f"{row.get('id')} {row.get('title', '')}".strip(), "phase": "work", "item": row.get("id"),
                     "position": f"item {index + 1} of {len(items)}",
                     "slots": [slot(row.get("id"), node) for node in inner]})
    if not planned:
        rows.append({"label": "Work items", "phase": "work", "item": None, "slots": [],
                     "note": "set by the plan stage"})
    rows.append({"label": "Release", "phase": "release", "item": None, "slots": [slot(None, node) for node in outer]})
    for row in rows:
        row["done"] = sum(each["state"] == "done" for each in row["slots"])
    return rows


# ---------------------------------------------------------------------------------------------------------- digest

_MARK = {"done": "✓", "current": "▶", "reopened": "↺", "pending": "·"}


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" + ("" if number == 1 else "s")


def _clock(stamp: Any) -> str:
    ts = _parse(stamp)
    return time.strftime("%H:%M:%SZ", time.gmtime(ts)) if ts is not None else "--:--:--"


def _ago(stamp: Any, now: float) -> str:
    ts = _parse(stamp)
    return "" if ts is None else _span(max(0.0, now - ts)) + " ago"


def _span(seconds: float | None) -> str:
    if seconds is None:
        return "?"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m{seconds % 60:02d}s"
    return f"{seconds // 3600}h{seconds % 3600 // 60:02d}m"


def _short(action: Any) -> str:
    return str(action)[:12] + "…" if isinstance(action, str) and len(action) > 13 else str(action or "-")


def _one_line(text: Any, limit: int = 110) -> str:
    flat = " ".join(str(text or "").split())
    return flat[:limit] + ("…" if len(flat) > limit else "")


def event_line(event: Mapping[str, Any]) -> str:
    """One event as one line of the digest."""
    kind = event.get("kind")
    head = f"{_clock(event.get('at') or event.get('ts'))}  {kind:<9}"
    if kind == "command":
        text = f"{event.get('verb')} {_short(event.get('action')) if event.get('action') else ''}".rstrip()
        text += f" → exit {event.get('exit')}"
        for row in event.get("accepted") or []:
            text += f" · accepted {(row.get('item') + ' ') if row.get('item') else ''}{row.get('stage')} ({row.get('outcome')})"
        rev = event.get("rev") or [None, None]
        if rev[0] != rev[1] and rev[1] is not None and not event.get("accepted"):
            stage = event.get("stage") or [None, None]
            text += f" · now {stage[1]} r{rev[1]}"
        if event.get("note"):
            text += f" · wrote owner note {event['note']}"
        if event.get("delivered"):
            text += " · delivered owner note" + ("s " if len(event["delivered"]) > 1 else " ") + ", ".join(event["delivered"])
        if event.get("held"):
            text += " · held for owner note" + ("s " if len(event["held"]) > 1 else " ") + ", ".join(event["held"])
        elif event.get("exit"):
            text += " · " + ("check: " if event.get("verb") == "check" else "refused: ") + _one_line(event.get("error") or "(no message recorded)")
        return f"{head}{text} · {event.get('ms')} ms"
    if kind == "packet":
        where = f"{(event.get('item') + ' ') if event.get('item') else ''}{event.get('stage')}"
        if event.get("reviewed"):
            where += f" (reviewing {event.get('reviewed')})"
        sent = "reprint, same text" if event.get("repeat") else f"RUN/{event.get('file')}"
        printed = "printed whole" if event.get("whole") else f"printed head {event.get('printed'):,}"
        return f"{head}{where} {_short(event.get('action'))} {event.get('chars', 0):,} chars, {printed} → {sent}"
    if kind == "hook":
        text = f"{event.get('hook')} → {event.get('decision')} ({event.get('why')})"
        if event.get("text"):
            text += f": “{_one_line(event.get('text'), 140)}”"
        return head + text
    if kind == "skill":
        if event.get("gate"):
            return f"{head}gate {event.get('gate')}: {_one_line(event.get('why'))}"
        return f"{head}{event.get('skill')} “{_one_line(event.get('args'), 90)}”"
    if kind == "accepted":
        return f"{head}{(event.get('item') + ' ') if event.get('item') else ''}{event.get('stage')} ({event.get('outcome')})"
    return head + _one_line(json.dumps({k: v for k, v in event.items() if k not in ("v", "ts", "at", "kind", "i")}))


def digest(model: Mapping[str, Any], *, last: int = 15, now: float | None = None) -> str:
    """The text a model or a terminal reads: where the run is, every stage's state, the steps run, recent events."""
    clock = time.time() if now is None else now
    run, counts = model["run"], model["counts"]
    lines = ["=== ShipLoop trace ==="]
    lines.append(f"Run:      {run['goal']}  (run {str(run.get('id'))[:12]}, revision {run['revision']}, {run['status']})")
    if run.get("status_reason") and run["status"] != "active":
        lines.append(f"Stopped:  {_one_line(run['status_reason'], 200)}")
    lines.append(f"Time:     started {run.get('started') or '?'} · elapsed {_span(run.get('elapsed'))}"
                 + (f" · last event {_ago(run.get('last_event'), clock)}" if run.get("last_event") else ""))
    now_block = model.get("now")
    if now_block:
        where = f"{(now_block['item'] + ' ') if now_block.get('item') else ''}{now_block['stage']}"
        lines.append(f"Now:      {where} · action {now_block.get('action')}"
                     + (f" · first packet {_ago(now_block.get('since'), clock)}" if now_block.get("since") else "")
                     + (f" · {now_block['refusals']} refused" if now_block.get("refusals") else ""))
        if now_block.get("purpose"):
            lines.append(f"          {_one_line(now_block['purpose'], 150)}")
        if now_block.get("packet"):
            lines.append(f"Packet:   RUN/{now_block['packet']}")
    lines.extend(notes_summary(model.get("notes") or []))
    lines.extend(request_summary(model["request"]))
    lines.append("")
    lines.append("Plan (✓ done · ▶ current · ↺ reopened · · pending; ×N accepted N "
                 "times, (N steps) implement's steps, ↩N sent back, +I Improve reviewed, !N refused):")
    for row in model["plan"]:
        label = _one_line(row["label"], 26)
        if not row["slots"]:
            lines.append(f"  {label:<27} ({row.get('note', 'none')})")
            continue
        if all(slot["state"] == "pending" for slot in row["slots"]):
            lines.append(f"  {label:<27} {len(row['slots'])} stages pending")
            continue
        chips = []
        for slot in row["slots"]:
            chip = _MARK[slot["state"]] + slot["stage"]
            if slot.get("steps") is not None:
                chip += f"({_count(slot['steps'], 'step')})"
            elif slot["runs"] - slot.get("sent_back", 0) > 1:
                chip += f"×{slot['runs'] - slot.get('sent_back', 0)}"
            if slot.get("sent_back"):
                chip += f"↩{slot['sent_back']}"
            if slot["improve"]:
                chip += "+I"
            if slot.get("refusals"):
                chip += f"!{slot['refusals']}"
            chips.append(chip)
        lines.append(f"  {label:<27} " + " ".join(chips))
    steps = model["steps"]
    shown = steps[-last:] if last else steps
    lines.append("")
    lines.append(f"Steps run ({len(shown)} of {len(steps)} shown):" if steps else "Steps run: none yet")
    for step in shown:
        extras = [part for part in (
            _span(step["seconds"]) if step.get("seconds") is not None else None,
            f"{step['refusals']} refused" if step.get("refusals") else None,
            _count(step["reprints"], "reprint") if step.get("reprints") else None,
            "Improve" if step.get("improve") else None) if part]
        where = f"{(step['item'] + ' ') if step.get('item') else ''}{step['stage']}"
        lines.append(f"  #{step['n']:<3} {_clock(step.get('at'))}  {where:<28} {step['outcome']:<9}"
                     + (f" ({', '.join(extras)})" if extras else "") + f"  {_one_line(step['headline'], 90)}")
    events = model["events"]
    lines.append("")
    if not run["traced"]:
        lines.append("Events: this run has no trace.jsonl (it predates the trace): the events below are the accepted "
                     "steps timeline.json stamped and the Skill calls; packets/ holds only the last copy of each packet.")
    elif run.get("untraced_steps"):
        lines.append(f"Events: the trace began at {run['traced_since']}; {_count(run['untraced_steps'], 'accepted step')} "
                     "before it come from state.md and timeline.json, with the last copy of each packet.")
    lines.append(f"Recent events ({min(last, len(events)) if last else len(events)} of {len(events)}):")
    for event in (events[-last:] if last else events):
        lines.append("  " + event_line(event))
    lines.append("")
    if run["traced"]:
        lines.append(f"Totals:   {counts['accepted']} accepted · {_count(counts['commands'], 'command')} · "
                     f"{counts['refusals']} refused · {_count(counts['checks_failed'], 'check')} failed · "
                     + (f"{_count(counts['held'], 'callback')} held for owner notes · " if counts.get("held") else "")
                     + f"{_count(counts['packets'], 'packet')} ({_count(counts['reprints'], 'reprint')}) · "
                     f"{_count(counts['continuations'], 'hook continuation')} · {_count(counts['skills'], 'skill call')}")
    else:
        # Not measured is not zero: a run before the trace recorded no commands, refusals, packets or hook stops.
        lines.append(f"Totals:   {counts['accepted']} accepted · {_count(counts['skills'], 'skill call')} · commands, refusals, "
                     "packets and hook stops not recorded")
    if run.get("capped"):
        lines.append(f"Note:     the trace reached {TRACE_LIMIT // (1024 * 1024)} MB and stopped growing.")
    lines.append("More:     --action <id> for one action · --json for every field · --html for the page "
                 f"(RUN/{PAGE}) · the owner leaves a note with `note --run-dir RUN --text …`")
    lines.append(f"RUN:      {run['dir']}")
    lines.append("=== end ShipLoop trace ===")
    return "\n".join(lines) + "\n"


def notes_summary(notes: Sequence[Mapping[str, Any]]) -> list[str]:
    """One digest line for the owner's notes, when there are any: each one's id and where it stands."""
    if not notes:
        return []
    parts = []
    for note in notes:
        if note["state"] == "delivered":
            cited = " (cited)" if note.get("cited") else " (not cited in its summary)"
            parts.append(f"{note['id']} delivered" + (f" #{note['step']}" if note.get("step") else "") + cited)
        else:
            parts.append(f"{note['id']} " + ("shown, not delivered yet" if note["state"] == "shown" else "waiting for a packet"))
    return [f"Notes:    {_count(len(notes), 'owner note')} · " + " · ".join(parts)]


def request_summary(request: Mapping[str, Any]) -> list[str]:
    """Two digest lines: the original request, and how far planning has expanded it."""
    original, expanded = request["original"], request["expanded"]
    steps = sum(len(item["steps"]) for item in expanded["work_items"])
    parts = [f"through {expanded['through']}" if expanded["through"] else "not expanded yet",
             f"intake read {expanded['mapped']} of {_count(len(original['sentences']), 'sentence')}",
             _count(len(expanded["requirements"]), "requirement"),
             _count(len(expanded["work_items"]), "work item") + (f", {_count(steps, 'step')}" if steps else ""),
             _count(len(expanded["assumptions"]), "assumption"), _count(len(expanded["answers"]), "owner answer")]
    if expanded["superseded"]:
        parts.append(f"{expanded['superseded']} superseded")
    return [f"Request:  original {original['chars']:,} chars, {_count(len(original['sentences']), 'sentence')} "
            f"(RUN/{original['file']}): “{_one_line(original['text'], 90)}”",
            "Expanded: " + " · ".join(parts),
            "          --request shows the original beside the expansion"]


def request_digest(model: Mapping[str, Any]) -> str:
    """The original request beside everything planning made of it, sentence by sentence and stage by stage."""
    request = model["request"]
    original, expanded = request["original"], request["expanded"]
    # The sentences joined are the verbatim request, so it is not printed twice; RUN/request.md keeps its layout.
    lines = ["=== ShipLoop trace: request ===",
             f"Original, sentence by sentence (joined, the verbatim RUN/{original['file']}; {original['chars']:,} chars), "
             "each followed by how intake read it:"]
    if not original["sentences"]:
        lines.append("  (empty)")
    for sentence in original["sentences"]:
        lines.append(f"  S{sentence['n']:<3} {sentence['text']}")
        for reading in sentence["readings"]:
            lines.append(f"       → {reading['kind']}: {reading['text']}")
        if not sentence["readings"]:
            lines.append("       → " + ("no clause of intake's summary cites it" if expanded["through"]
                                       else "intake not accepted yet"))
    lines += ["", "Planning, in order (current results; ✓ accepted, · pending):"]
    for stage in expanded["stages"]:
        if stage["state"] != "accepted":
            lines.append(f"  · {stage['stage']}")
            continue
        lines.append(f"  ✓ {stage['stage']:<14} {stage['headline']}" + ("  (+I)" if stage["improve"] else ""))
        if stage["stage"] != "intake" or not expanded["mapped"]:  # a mapped intake summary is the readings above
            lines.append(f"    {'':<14} {_one_line(stage['summary'], 400)}")
    lines += ["", f"Requirements ({len(expanded['requirements'])}, living spec {expanded['spec_file']}):"]
    for requirement in expanded["requirements"]:
        lines.append(f"  {requirement['id']:<6} {requirement['title']}  [{requirement['section']}]")
    if not expanded["requirements"]:
        lines.append("  none yet")
    lines += ["", f"Work items ({len(expanded['work_items'])}):"]
    for item in expanded["work_items"]:
        lines.append(f"  {item['id']:<4} {item['title']}")
        lines.append(f"       {_one_line(item['context'], 300)}")
        for step in item["steps"]:
            after = f" (after {', '.join(step['deps'])})" if step["deps"] else ""
            lines.append(f"       {step['id']:<4} {_one_line(step['task'], 160)}{after}")
    if not expanded["work_items"]:
        lines.append("  set by the plan stage")
    lines += ["", f"Assumptions ({len(expanded['assumptions'])}):"]
    for assumption in expanded["assumptions"]:
        lines.append(f"  {assumption['id'] or '-':<4} {assumption['disposition'] or '':<10} {_one_line(assumption['assumption'], 150)}")
    lines += ["", f"Owner answers ({len(expanded['answers'])}):"]
    for answer in expanded["answers"]:
        lines.append(f"  RUN/{answer['file']}: {_one_line(answer['text'], 300)}")
    if not expanded["answers"]:
        lines.append("  none")
    if expanded["superseded"]:
        lines += ["", f"Superseded: {_count(expanded['superseded'], 'earlier planning result')} replaced by a later "
                      "one (send-back or reconciliation); the run's history keeps them."]
    lines.append("=== end ShipLoop trace ===")
    return "\n".join(lines) + "\n"


def find_action(model: Mapping[str, Any], wanted: str) -> str | None:
    """The one action id that is ``wanted`` or that ``wanted`` starts or ends (at least 6 characters), with or without
    its ``nav-`` prefix (the digest prints ``nav-7d0f97f9…``; a reader copies the hex)."""
    known = {step["action"] for step in model["steps"]}
    known |= {event.get("action") for event in model["events"] if event.get("action")}
    known |= {event.get("for_action") for event in model["events"] if event.get("for_action")}
    if model.get("now") and model["now"].get("action"):
        known.add(model["now"]["action"])
    if wanted in known:
        return wanted
    if len(wanted) < 6:
        return None
    matches = sorted(action for action in known if action and (action.startswith(wanted) or action.endswith(wanted)
                                                                or action.split("-", 1)[-1].startswith(wanted)))
    return matches[0] if len(matches) == 1 else None


def action_digest(model: Mapping[str, Any], action: str) -> str:
    """One action: what it was, every packet as sent, every command and hook while it was current, and its files."""
    run = Path(model["run"]["dir"])
    step = next((row for row in model["steps"] if row["action"] == action), None)
    events = [event for event in model["events"] if (event.get("action") or event.get("for_action")) == action]
    lines = [f"=== ShipLoop trace: action {action} ==="]
    if step:
        where = f"{(step['item'] + ' ') if step.get('item') else ''}{step['stage']}"
        lines.append(f"Step:     #{step['n']} {where}, {step['outcome']} at {step.get('at') or '?'}"
                     + (" · Improve reviewed" if step.get("improve") else ""))
        lines.append(f"Result:   {_one_line(step['headline'], 200)}")
    elif model.get("now") and model["now"].get("action") == action:
        lines.append(f"Step:     current: {model['now']['stage']} ({model['now'].get('purpose', '')})")
    else:
        lines.append("Step:     not an accepted step (an Improve stage, a reopened step, or a refused action)")
    packets = [event for event in events if event["kind"] == "packet"]
    lines.append(f"Packets sent: {len(packets)}")
    for event in packets:
        lines.append("  " + event_line(event))
    others = [event for event in events if event["kind"] != "packet"]
    lines.append(f"Commands, hooks and skill calls: {len(others)}")
    for event in others:
        lines.append("  " + event_line(event))
        if event["kind"] == "command" and event.get("exit") and event.get("error"):
            for row in str(event["error"]).splitlines()[:12]:
                lines.append("      " + row)
        if event["kind"] == "hook" and event.get("text"):
            lines.append("      " + _one_line(event["text"], 600))
    files = [f"packets/{action}.md", f"inbox/{action}.md", f"results/{action}.md", f"notes/{action}.md",
             f"commits/{action}.txt", f"loops/{action}-terminal.json", f"improve/{action}"]
    present = [name for name in files if (run / name).exists()]
    lines.append("Files:    " + (", ".join("RUN/" + name for name in present) if present else "none"))
    lines.append("=== end ShipLoop trace ===")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------------------------------------- page


def page_texts(root: str | Path, model: Mapping[str, Any]) -> dict[str, str]:
    """Each packet's text as sent, keyed by its file, screened line by line for credentials, within the page bounds."""
    run = Path(root)
    files = [event.get("file") for event in model["events"] if event["kind"] == "packet" and event.get("file")]
    files += [event.get("head_file") for event in model["events"] if event["kind"] == "packet" and event.get("head_file")]
    # An action the trace never saw a packet for keeps its last copy in packets/<action>.md.
    sent = {event.get("action") for event in model["events"] if event["kind"] == "packet"}
    files += [f"packets/{path.name}" for path in sorted((run / "packets").glob("*.md")) if path.stem not in sent]
    texts: dict[str, str] = {}
    total = 0
    for relative in dict.fromkeys(files):
        try:
            too_large = (run / relative).stat().st_size > PAGE_PACKET_LIMIT
        except OSError:
            continue
        text = None if too_large else _bounded_text(run / relative, PAGE_PACKET_LIMIT)
        if text is None:
            continue
        if total + len(text) > PAGE_TEXT_LIMIT:
            break
        texts[relative] = text
        total += len(text)
    return texts


def render_html(root: str | Path, model: Mapping[str, Any]) -> str:
    """The self-contained page: the template with the model and the packet texts inlined."""
    from shiploop_trace_page import DATA_MARK, PAGE  # only the page needs the template, not every command or hook

    data = dict(model)
    data["texts"] = page_texts(root, model)
    data["events"] = [{**event, **{name: _screened(event[name]) for name in ("text", "error")
                                   if isinstance(event.get(name), str)}} for event in model["events"]]
    # Every "<" escaped: "</script>" or "<!--<script>" in a prompt must not end or re-open the script element.
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return PAGE.replace(DATA_MARK, payload, 1)


def write_html(root: str | Path, path: str | Path | None = None, *, now: float | None = None) -> Path:
    """Build the model and write the page (default RUN/trace.html); returns where it went."""
    target = Path(path) if path else Path(root) / PAGE
    store.atomic_write_text(target, render_html(root, build(root, now=now)))
    return target


def source_key(root: str | Path) -> tuple[Any, ...]:
    """What the page is built from, cheaply: the trace's size, the state's and the Skill record's change times."""
    key = []
    for name in (TRACE_FILE, "state.md", SKILL_CALLS):
        try:
            info = (Path(root) / name).stat()
            key.append((info.st_size, info.st_mtime_ns))
        except OSError:
            key.append(None)
    return tuple(key)


# ---------------------------------------------------------------------------------------------------------- CLI


def main(argv: Sequence[str] | None = None, *, core: Any = None) -> int:
    """``shiploop trace``: read the run's trace; never writes run state (``--html`` writes only the page)."""
    parser = argparse.ArgumentParser(prog="shiploop trace", description="read what a ShipLoop run did, in order")
    parser.add_argument("--run-dir", required=True)
    shape = parser.add_mutually_exclusive_group()
    shape.add_argument("--json", action="store_true", help="print the whole model as JSON")
    shape.add_argument("--html", nargs="?", const="", metavar="PATH",
                       help="write the self-contained page (default RUN/trace.html) and print its path")
    shape.add_argument("--action", help="one action: its packets as sent, commands, hooks and files (id, or 6+ "
                                        "characters of its start or end)")
    shape.add_argument("--request", action="store_true",
                       help="the original request beside its expansion by every planning stage so far")
    parser.add_argument("--last", type=int, default=15, help="how many steps and events the digest lists (0: all)")
    args = parser.parse_args(argv)
    root = Path(args.run_dir).expanduser().resolve()
    if not (root / "state.md").is_file():
        print(f"error: no ShipLoop run at {root} (no state.md); check --run-dir", file=sys.stderr)
        return 2
    try:
        if args.html is not None:
            if not args.html and current_state(root) is None:
                print(f"ShipLoop trace: {root} is retired or cannot be loaded, so nothing is written into it; "
                      "name a page outside it with --html PATH", file=sys.stderr)
                return 2
            print(write_html(root, args.html or None))
            return 0
        model = build(root)
    except (OSError, ValueError, KeyError, TypeError, store.StorageError) as exc:
        print(f"ShipLoop trace: the run could not be read: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(model, ensure_ascii=False, indent=1))
        return 0
    if args.request:
        print(request_digest(model), end="")
        return 0
    if args.action:
        action = find_action(model, args.action)
        if action is None:
            print(f"ShipLoop trace: no single action matches {args.action!r}; the digest lists them", file=sys.stderr)
            return 2
        print(action_digest(model, action), end="")
        return 0
    print(digest(model, last=max(0, args.last)), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
