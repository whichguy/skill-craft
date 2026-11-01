#!/usr/bin/env python3
"""Reading the stage suite's live samples for this round's scorers: each sample folder's result, trees, trace and verdict,
through the suite's own reader (``stage_live.collect_bundle``), so a scorer and the oracle read the same files."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[3]
for folder in ("test/shiploop_e2e/stage_suite", "test/shiploop_e2e", "skills/shiploop/scripts"):
    sys.path.insert(0, str(ROOT / folder))
import stage_build as sb  # noqa: E402
import stage_live  # noqa: E402
import shiploop_trace  # noqa: E402


def folders(root: Path, scenario: str) -> Iterator[Path]:
    """Each sample folder of ``scenario`` under the results root ``root``, in sample order."""
    base = root / scenario
    for path in sorted((p for p in base.iterdir() if p.is_dir()), key=lambda p: (len(p.name), p.name)) if base.is_dir() else ():
        yield path


def read(scenario: str, sample: Path) -> dict:
    """{"sample", "ran", "error", "verdict", "bundle"}: a sample with no stage-result.json did not run (error.txt says why)."""
    verdict_file, error_file = sample / stage_live.RESULT, sample / stage_live.ERROR
    row = {"sample": sample.name, "ran": verdict_file.is_file(), "error": None, "verdict": None, "bundle": None}
    if error_file.is_file():
        row["error"] = error_file.read_text().strip()[:500]
    if not row["ran"]:
        return row
    row["verdict"] = json.loads(verdict_file.read_text())
    row["bundle"] = stage_live.collect_bundle(sb.load(scenario), sample)
    return row


def refusals(trace: list | None, action: str | None = None) -> int:
    """Callbacks the run refused (``shiploop_trace.refused``), optionally of one action."""
    return sum(1 for row in trace or () if shiploop_trace.refused(row) and (action is None or row.get("action") == action))


def tree_files(tree: Path | None) -> dict[str, str]:
    """Relative path -> text of every file of an exported tree (binary files read as empty)."""
    found: dict[str, str] = {}
    if tree is None or not tree.is_dir():
        return found
    for path in sorted(tree.rglob("*")):
        if path.is_file() and ".git" not in path.relative_to(tree).parts:
            try:
                found[path.relative_to(tree).as_posix()] = path.read_text()
            except (UnicodeDecodeError, OSError):
                found[path.relative_to(tree).as_posix()] = ""
    return found
