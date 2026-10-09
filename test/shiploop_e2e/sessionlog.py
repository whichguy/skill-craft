"""``<output>/sessions.jsonl``: the harness's own record of every host launch and every session end.

The host's events cannot give these boundaries: Grok repeats ``available_commands`` (the 2026-10-08 r3 run has 237 of
them in a two-session run), Claude's ``system/init`` and Codex's ``thread.started`` open sessions but say nothing of how
or why one began, and a ``--resume-run`` overwrites ``result.json``, so the session list of the invocation before it is
gone.  So the harness that launches the hosts writes the boundary, in the one place and the one format the readers
(``metrics.fresh_starts``) use.  Append-only, one JSON object per line, never rewritten:

``start``  written BEFORE the host is launched, so a harness that dies keeps the boundary: ``n`` (1-based over the whole
           output folder, across invocations), ``kind`` (``first``: the case prompt; ``fresh``: a new host session with no
           host session id passed, so a cleared context; ``continued``: the host's own ``--resume <id>``), ``reason``
           (``start``, ``resume-run``, ``after-interrupt``, ``resume-loop``), ``host``, ``model``, ``t`` (epoch seconds),
           ``events_line`` (the lines events.jsonl already held, which is the number of the session's first event),
           ``told`` (the CLI and run directory the resume prompt named, stored as VALUES because the Claude host passes
           its prompt in ``-p`` and keeps no prompt file; None where the prompt named no recovery command) and
           ``resumed_session`` (the host session id a ``continued`` launch passed).
``end``    written after the session: ``n``, ``t``, ``events_line`` (the lines events.jsonl holds now), ``status`` and
           ``returncode`` (the launch's own), and ``engine``, the ledger at that moment (metrics.engine_position).  A
           harness killed with its host writes none: the start row stays without one.

Recording is fail-open: a folder that cannot be written never stops a run.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

SESSIONS = "sessions.jsonl"


def _lines(out: Path) -> list[dict] | None:
    """Every readable row in file order, or None when the file does not exist (a run from before this record)."""
    path = Path(out) / SESSIONS
    if not path.is_file():
        return None
    rows: list[dict] = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("row") in ("start", "end") and isinstance(row.get("n"), int):
            rows.append(row)
    return rows


def _append(out: Path, row: dict) -> None:
    try:
        with (Path(out) / SESSIONS).open("a") as handle:
            handle.write(json.dumps(row) + "\n")
    except OSError:
        pass


def start(out: Path, *, kind: str, reason: str, host: str, model: str | None, events_line: int, told: dict | None,
          resumed_session: str | None = None, t: float | None = None) -> dict:
    """Append the ``start`` row of a launch that is about to happen, and return it (the caller closes it with ``end``)."""
    number = 1 + sum(1 for row in _lines(out) or [] if row["row"] == "start")
    row = {"row": "start", "n": number, "kind": kind, "reason": reason, "host": host, "model": model,
           "t": round(time.time() if t is None else t, 3), "events_line": events_line, "told": told,
           "resumed_session": resumed_session}
    _append(out, row)
    return row


def end(out: Path, started: dict, *, events_line: int, status: str, returncode: int | None, engine: dict | None,
        t: float | None = None) -> dict:
    """Append the ``end`` row of the session ``started`` opened, and return it."""
    row = {"row": "end", "n": started["n"], "t": round(time.time() if t is None else t, 3),
           "events_line": events_line, "status": status, "returncode": returncode, "engine": engine}
    _append(out, row)
    return row


def read(out: Path) -> list[dict] | None:
    """The sessions in launch order, each its ``start`` row with its ``end`` row under ``end`` (None while the session has
    none), or None when the folder has no sessions.jsonl: a run from before the record, which is not an empty record."""
    rows = _lines(out)
    if rows is None:
        return None
    ends = {row["n"]: row for row in rows if row["row"] == "end"}
    return [{**row, "end": ends.get(row["n"])} for row in rows if row["row"] == "start"]
