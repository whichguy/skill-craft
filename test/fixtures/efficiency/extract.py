#!/usr/bin/env python3
"""Rebuild the two compact run folders in this directory from the two saved runs the efficiency plan measured.

Nothing reads those runs at test time; this script is how the committed extracts were made, so a reader can see what was kept and
re-derive them.

    python3 test/fixtures/efficiency/extract.py CLAUDE_RUN_DIR GROK_RUN_DIR

* ``claude-step-slice/``: a Claude Sonnet 5.5 step slice of the node-fix-bug case on ShipLoop 1.3.0 (the run the artifact review of
  2026-10-17 read). Kept whole: events.jsonl (139 events, 41 tool calls), timeline.jsonl, sessions.jsonl, and the ShipLoop run
  under .shiploop-runs/seed/run (state.md, timeline.json, packets/, tests/, lint/). Every absolute path of the saved run is
  rewritten to /fixture/claude-run.
* ``grok-long-run/``: a Grok 4.7 run of 33,833 events, 1,503 tool calls and 14 compactions. Kept: the REAL line numbers (every event
  is one line, so a prefix of N events is the first N lines), the tool calls (the keys the readers look at, commands whole), each tool call's final result as its header (when it printed a packet) padded with `x` to the saved length, so
  every character count is the saved run's, the compaction and session-end markers, and one `usage` marker per model call. Every
  other event is `{}`. Also kept: timeline.jsonl, sessions.jsonl, and the ShipLoop run's state.md, timeline.json and Improve bind
  files (their file times are the saved run's). Every absolute path is rewritten to /fixture/grok-run.

A file over GZIP_OVER bytes is stored gzipped (``<name>.gz``, mtime 0, so the bytes are the same on every run) and the test
unpacks the folder into a temporary directory first; git does not keep file times, so ``mtimes.json`` records the ones a reader
needs (the Improve bind files, whose time to the accept is the child's time) and the unpacking sets them.

The measurements the tests pin (reading counts by class at the first 29,668 events and at all 33,833, the 14 compactions and what
followed them, the 20 piped completes, the four skipped gates) were taken from the saved runs and reproduce from these folders.
"""

from __future__ import annotations

import gzip
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEEP_INPUT = ("command", "target_file", "file_path", "path", "pattern", "offset", "limit", "skill", "args", "question")
GZIP_OVER = 20_000
HEADER = re.compile(r"ShipLoop navigator \| [\w-]+ \|(?: revision \d+)?")


def rewrite(text: str, old: str, new: str) -> str:
    return text.replace(old, new)


def store(path: Path, text: str) -> None:
    """Write ``text`` to ``path``, gzipped (and named so) when it is large."""
    if len(text) > GZIP_OVER:
        with gzip.GzipFile(str(path) + ".gz", "wb", mtime=0) as handle:
            handle.write(text.encode())
    else:
        path.write_text(text)


def claude(source: Path) -> None:
    old = str(source.resolve())
    new = "/fixture/claude-run"
    out = HERE / "claude-step-slice"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for name in ("events.jsonl", "timeline.jsonl", "sessions.jsonl"):
        store(out / name, rewrite((source / name).read_text(), old, new))
    invocation = json.loads((source / "invocation.json").read_text())
    (out / "invocation.json").write_text(json.dumps(
        {"case": invocation["case"], "host": invocation["host"], "model": invocation["model"],
         "seeded": {"stage": "step-plan", "run_dir": f"{new}/.shiploop-runs/seed/run"}}, indent=2) + "\n")
    run = source / ".shiploop-runs" / "seed" / "run"
    target = out / ".shiploop-runs" / "seed" / "run"
    for relative in ("state.md", "timeline.json"):
        target.mkdir(parents=True, exist_ok=True)
        store(target / relative, rewrite((run / relative).read_text(), old, new))
    for folder in ("packets", "tests", "lint"):
        (target / folder).mkdir(parents=True, exist_ok=True)
        for path in sorted((run / folder).glob("*.md")):
            store(target / folder / path.name, rewrite(path.read_text(), old, new))


def grok(source: Path) -> None:
    old = str(source.resolve())
    new = "/fixture/grok-run"
    out = HERE / "grok-long-run"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    names: dict = {}
    lines = []
    with (source / "events.jsonl").open() as handle:
        for raw in handle:
            try:
                event = json.loads(raw)
            except ValueError:
                lines.append("{}")
                continue
            kind = event.get("type")
            if kind == "tool_call":
                names[event.get("toolCallId")] = event.get("toolName")
                given = event.get("rawInput") if isinstance(event.get("rawInput"), dict) else {}
                kept = {k: v for k, v in given.items() if k in KEEP_INPUT}
                lines.append(json.dumps({"type": "tool_call", "toolCallId": event.get("toolCallId"),
                                         "toolName": event.get("toolName"), "rawInput": kept}))
            elif kind == "tool_call_update" and isinstance(event.get("rawOutput"), dict) and event.get("status") == "completed":
                shown = _shown(event["rawOutput"])
                header = HEADER.search(shown)
                head = shown[:header.end() + 80] if header else ""
                lines.append(json.dumps({"type": "tool_call_update", "toolCallId": event.get("toolCallId"), "status": "completed",
                                         "rawOutput": {"output_for_prompt": head + "x" * (len(shown) - len(head))}}))
            elif kind in ("auto_compact_started", "auto_compact_completed", "usage", "end"):
                lines.append(json.dumps({"type": kind}))
            else:
                lines.append("{}")
    store(out / "events.jsonl", rewrite("\n".join(lines) + "\n", old, new))
    for name in ("timeline.jsonl", "sessions.jsonl"):
        store(out / name, rewrite((source / name).read_text(), old, new))
    runs = sorted((source / ".shiploop-runs").glob("*/run"))
    run = runs[0]
    target = out / ".shiploop-runs" / run.parent.name / "run"
    (target / "improve").mkdir(parents=True)
    for relative in ("state.md", "timeline.json"):
        store(target / relative, rewrite((run / relative).read_text(), old, new))
    mtimes = {}
    for path in sorted((run / "improve").glob("*-bind.md")):
        copy = target / "improve" / path.name
        copy.write_text(rewrite(path.read_text(), old, new))
        mtimes[str(copy.relative_to(out))] = path.stat().st_mtime
    (out / "mtimes.json").write_text(json.dumps(mtimes, indent=1) + "\n")
    (out / "invocation.json").write_text(json.dumps({"case": "long-run", "host": "grok"}, indent=2) + "\n")


def _shown(raw: dict) -> str:
    """The text a Grok final update showed the model (the same reading metrics.result_text makes)."""
    for key in ("output_for_prompt",):
        if isinstance(raw.get(key), str) and raw[key]:
            return raw[key]
    for key in ("FileContent", "Content"):
        part = raw.get(key)
        if isinstance(part, dict) and isinstance(part.get("content"), str):
            return part["content"]
        if isinstance(part, str):
            return part
    return raw["stdout"] if isinstance(raw.get("stdout"), str) else ""


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        sys.stderr.write(__doc__)
        return 2
    claude(Path(argv[0]))
    grok(Path(argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
