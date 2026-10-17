"""The run's record of Skill-tool calls, written by a Claude Code hook and read by the Improve stage's gate.

A packet tells the model to invoke the improve skill at every Improve stage, and a model that does not leaves a review the
skill never ran (live runs, 2026-10: 3 of 4 Improve reviews written by a script in the 2.1.0 run, the skill invoked for 1 of
4 stages in the 2.4.0 slice; the wording changes did not move that).  Wording cannot enforce it; a record the model does not
write can.  ``scripts/shiploop-skill-call`` (a PostToolUse hook on the Skill tool) appends one JSON line per call to
``<run dir>/skill-calls.jsonl``; ``complete`` on an Improve stage reads it (``skill_call_gate`` in the navigator).

The hook runs for every Skill call of a bound session, so it is cheap and never raises into the host.  It writes only inside a
run directory the keepalive hooks bound, and only to a regular file it opened without following a symlink.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

RECORD_FILE = "skill-calls.jsonl"
PLUGIN = "skill-craft"  # the one plugin namespace every ShipLoop skill is invoked under (/skill-craft:<leaf>)
# The handoff path is the longest thing a call carries; a record line stays far under a page.
ARGS_LIMIT = 2000
# Quotes and escapes a model may put around a path it copies into the Skill call's argument.
_QUOTING = re.compile(r"""['"`\\]""")


def skill_name(raw: Any) -> str:
    """The skill as the Skill tool names it, without a slash or this plugin's prefix: ``skill-craft:improve`` is ``improve``.

    Another plugin's ``improve`` keeps its prefix, so it is not this skill.
    """
    name = str(raw or "").strip().lstrip("/").strip().lower()
    plugin, _, leaf = name.rpartition(":")
    return leaf.strip() if plugin.strip() in ("", PLUGIN) else name


def _line(record: Mapping[str, Any]) -> bytes:
    return (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def _append(run_dir: Path, record: Mapping[str, Any]) -> None:
    """Append one line to the run's record: a regular file inside the run directory, never a symlink."""
    fd = os.open(run_dir / RECORD_FILE, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o644)
    try:
        os.write(fd, _line(record))
    finally:
        os.close(fd)


def record_call(run_dir: str | Path, tool_input: Any, *, session: str, tool_use_id: Any = None,
                agent_id: Any = None, now: float | None = None) -> bool:
    """Append the call a Skill-tool hook payload describes to the run's record; True when a line was written.

    ``tool_input`` is the Skill tool's own input: ``skill`` and, when the model passed one, ``args``.  A directory that is
    not a ShipLoop run (no ``state.md``) is left alone.
    """
    root = Path(run_dir)
    if not root.is_absolute() or not (root / "state.md").is_file() or not isinstance(tool_input, Mapping):
        return False
    called_as = tool_input.get("skill")
    if not isinstance(called_as, str) or not called_as.strip():
        return False
    args = tool_input.get("args")
    if not isinstance(args, str):
        args = "" if args is None else json.dumps(args, ensure_ascii=False)
    stamp = time.time() if now is None else now
    record: dict[str, Any] = {
        "ts": round(stamp, 6),
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stamp)),
        "skill": skill_name(called_as),
        "called_as": called_as,
        "args": args[:ARGS_LIMIT],
        "session": session,
    }
    if isinstance(tool_use_id, str) and tool_use_id:
        record["tool_use_id"] = tool_use_id
    if isinstance(agent_id, str) and agent_id:
        record["agent_id"] = agent_id
    _append(root, record)
    return True


def read_records(run_dir: str | Path) -> list[dict]:
    """Every readable line of the run's record; a missing file or a damaged line is skipped, never an error."""
    try:
        text = (Path(run_dir) / RECORD_FILE).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    found = []
    for line in text.split("\n"):  # not splitlines(): U+2028 and U+0085 inside an argument are not line ends
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict):
            found.append(item)
    return found


def _plain(text: str) -> str:
    return _QUOTING.sub("", text)


def improve_call_since(run_dir: str | Path, since: float, tokens: Iterable[str]) -> dict | None:
    """The latest improve-skill call made at or after ``since`` whose argument carries one of ``tokens``, else None.

    ``tokens`` are what names this Improve stage in the argument: its handoff path and its action ids.  Quoting around
    them is ignored.
    """
    wanted = [_plain(token) for token in tokens if token]
    for item in reversed(read_records(run_dir)):
        if item.get("skill") != "improve" or not isinstance(item.get("ts"), (int, float)) or item["ts"] < since:
            continue
        args = _plain(str(item.get("args", "")))
        if any(token in args for token in wanted):
            return item
    return None


def note_not_enforced(run_dir: str | Path, action: str, why: str, *, echo: Any = None) -> bool:
    """Say once per run that the Improve invocation was not enforceable here; True when this call said it.

    The note is a ``gate`` line in the record (so a reader of the record sees why it holds no calls) and one line on
    stderr.  The caller holds the run lock, so reading and then appending is safe; it runs after the import was saved.
    """
    if any("gate" in item for item in read_records(run_dir)):
        return False
    stamp = time.time()
    try:
        _append(Path(run_dir), {"ts": round(stamp, 6), "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stamp)),
                                "gate": "not enforced", "action": action, "why": why})
    except OSError:
        return False  # a note must never undo an import that was already saved
    (echo or sys.stderr).write(
        "ShipLoop: invoking the improve skill is not enforced on this host (" + why + "), so the Improve stage's "
        "complete accepts the review on the Improve runtime's own receipt without a recorded Skill call.\n")
    return True
