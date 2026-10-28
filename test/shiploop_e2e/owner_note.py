#!/usr/bin/env python3
"""``--owner-note-at STAGE``: the harness writes one owner note to the run in the middle of a STAGE step, as its owner would.

``shiploop note`` (skills/shiploop/scripts/shiploop_owner_notes.py) leaves a note the model must see at its next print: a
``complete`` for the current action is held once to show a waiting note, and a step accepted after its packet quoted the
note delivers it (a held callback shows a note but never delivers it, so the next packet quotes it again).
The trace fixtures prove that path; this option makes an E2E run exercise it on a real model. A watcher thread polls the run
every POLL_SECONDS. The first time the run is active, its current action is at STAGE and that action's packet has been
printed (a ``packet`` line for it in RUN/trace.jsonl), it runs ``shiploop note`` with the CLI the run itself uses and records
what happened in <out>/owner-note.json. One note per output folder: a resume that finds the file writes none.

Nothing here is a verdict: ``run_trace.checks`` reads the note's fate from the trace (``owner_note``).
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "skills/shiploop/scripts"))
import shiploop_trace  # noqa: E402

FILE = "owner-note.json"
POLL_SECONDS = 1.0
# Asks for nothing the step does not already do except one citation, so the run's work is the case's own and the trace's
# `cited` says whether the model acted on the note.
TEXT = ("E2E owner note: when you complete this step, cite this note's id in the step's summary and say in one clause that "
        "you read it. Nothing else about the step changes.")
WRITTEN = re.compile(r"^Owner note (N\d+) written", re.M)


def packet_printed(run_dir: Path, action: str) -> bool:
    """Whether the run's trace holds a ``packet`` line for ``action``: its step has started, so a note now is mid-step."""
    try:
        rows = (run_dir / shiploop_trace.TRACE_FILE).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False
    for row in rows:
        try:
            event = json.loads(row)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("kind") == "packet" and event.get("action") == action:
            return True
    return False


def due(run_dir: Path, stage: str) -> dict | None:
    """The step a note is due in now: {stage, action} when the run is active at ``stage`` and that action's packet printed."""
    state = shiploop_trace.current_state(run_dir)
    if not state or state.get("status") != "active":
        return None
    at, action, _ = shiploop_trace._cursor(state)
    action_id = (action or {}).get("id")
    if at != stage or not action_id or not packet_printed(run_dir, action_id):
        return None
    return {"stage": at, "action": action_id}


def write(out: Path, cli: Path, run_dir: Path, step: dict) -> dict:
    """Run ``shiploop note`` once on ``run_dir`` and record it in <out>/owner-note.json."""
    done = subprocess.run([sys.executable, str(cli), "note", "--run-dir", str(run_dir), "--text", TEXT],
                          capture_output=True, text=True, timeout=60)
    found = WRITTEN.search(done.stdout)
    record = {**step, "run_dir": str(run_dir), "written_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "exit": done.returncode, "id": found.group(1) if found else None,
              "output": (done.stdout + done.stderr).strip()[:2000], "text": TEXT}
    (out / FILE).write_text(json.dumps(record, indent=2) + "\n")
    return record


class Watcher:
    """Writes the note once, from a daemon thread, while the host sessions run; ``stop`` ends it."""

    def __init__(self, out: Path, cli: Path, stage: str, find_run: Callable[[], str | None]):
        self.out, self.cli, self.stage, self.find_run = out, cli, stage, find_run
        self.ended = threading.Event()
        self.thread = threading.Thread(target=self._watch, daemon=True)

    def start(self) -> "Watcher":
        if not (self.out / FILE).exists():
            self.thread.start()
        return self

    def stop(self) -> None:
        self.ended.set()
        if self.thread.is_alive():
            self.thread.join(timeout=10)

    def _watch(self) -> None:
        run_dir = None
        while not self.ended.wait(POLL_SECONDS):
            try:
                run_dir = run_dir or self.find_run()
                step = due(Path(run_dir), self.stage) if run_dir else None
                if step:
                    write(self.out, self.cli, Path(run_dir), step)
                    return
            except Exception as exc:  # noqa: BLE001 - a record, never a crash of the run it watches
                (self.out / FILE).write_text(json.dumps({"stage": self.stage, "error": f"{type(exc).__name__}: {exc}"[:500]},
                                                        indent=2) + "\n")
                return
