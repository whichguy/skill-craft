#!/usr/bin/env python3
"""Offline peek: what does an archived ShipLoop run leave open when it reaches handoff?

Question (owner, 2026-10-31): after a run is delivered and deployed, should ShipLoop reflect on what the run taught and
re-enter from the top with an improvement prompt?  Before designing a gate, read what archived runs leave open at their
end: the text under `Open for the next run` in the release-verify lessons, the open assumption rows, the unverified
list, and how often a run used add-work or send-back.

Nothing here runs a model or changes a run.  The run set is ``ledger.find_runs()`` of
docs/experiments/coverage-ledger-20261031 (archived runs that reached product-acceptance; test-fixture copies and seeded
slices skipped), and each run is read with ShipLoop's own readers: ``shiploop_store.read_record``,
``shiploop_planning_revision.current_actions``, ``shiploop_assumptions.open_items`` and
``shiploop_unverified.current_list``.

Two filters for "has something left open", both reported:

- loose: the lessons' ``open_next`` text is not exactly "none" (or an empty equivalent);
- strict: the text also does not open with a "none" phrase ("None for this request", "No known feature gaps", ...).

Usage: ``python3 -B peek.py [--json OUT] [RUN_DIR ...]``.  The run set grows as other sessions finish runs, so a rerun can
differ from the snapshot in README.md; summarize.py refuses to run when classification.json no longer matches.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
sys.path.insert(0, str(ROOT / "docs" / "experiments" / "coverage-ledger-20261031"))

import ledger  # noqa: E402  (find_runs)
import shiploop_assumptions as assumptions  # noqa: E402
import shiploop_planning_revision as planning_revision  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_unverified as unverified  # noqa: E402

LOOSE_NONE = {"", "none", "none.", "n/a", "nothing", "nothing.", "no open items", "no open items."}
STRICT_NONE = re.compile(r"^\s*(none|no known|no open|no other|no unfinished|nothing|n/a|no further|no remaining)\b",
                         re.IGNORECASE)


def label(path: Path) -> str:
    """The run directory with the home directory shortened to ``~``."""
    return str(path).replace(os.path.expanduser("~"), "~")


def read_run(root: Path) -> dict[str, Any] | None:
    """One run's end-of-run facts, or None when its state cannot be read."""
    try:
        state = store.read_record(root / "state.md")
    except (OSError, store.StorageError):
        return None
    history = [row for row in state.get("history") or () if isinstance(row, Mapping)]
    current = planning_revision.current_actions(state)
    accepted = state.get("accepted") or {}
    action = current.get((None, "release-verify"))
    result = accepted.get(action) if action else None
    lessons = result.get("lessons") if isinstance(result, Mapping) else None
    open_next = " ".join(str(lessons.get("open_next", "")).split()) if isinstance(lessons, Mapping) else None
    try:
        opens = assumptions.open_items(state)
    except Exception:  # a state shape the reader cannot take: reported as unreadable, never as zero
        opens = None
    _action, _stage, listed = unverified.current_list(state)
    return {
        "run": label(root),
        "handoff": any(row.get("stage") == "handoff" and row.get("outcome") == "done" for row in history),
        "has_release_verify": result is not None,
        "open_next": open_next,
        "open_rows": None if opens is None else len(opens),
        "open_rows_with_owner": None if opens is None else sum(1 for item in opens if item.row.get("owner")),
        "unverified_rows": None if listed is None else len(listed),
        "unverified_with_owner": 0 if not listed else sum(1 for row in listed
                                                          if isinstance(row, Mapping) and row.get("owner")),
        "add_work": sum(1 for row in history if row.get("outcome") == "add-work"),
        "send_back": sum(1 for row in history if row.get("outcome") == "send-back"),
    }


def summarize(rows: list[dict[str, Any]], found: int) -> dict[str, Any]:
    with_text = [row for row in rows if row["has_release_verify"] and row["open_next"] is not None]
    loose = [row for row in with_text if row["open_next"].strip().lower() not in LOOSE_NONE]
    strict = [row for row in loose if not STRICT_NONE.match(row["open_next"])]
    listed = [row for row in rows if row["unverified_rows"] is not None]
    return {
        "runs_found": found,
        "readable": len(rows),
        "reached_handoff": sum(1 for row in rows if row["handoff"]),
        "with_release_verify": sum(1 for row in rows if row["has_release_verify"]),
        "open_next_loose": len(loose),
        "open_next_strict": len(strict),
        "runs_with_open_rows": sum(1 for row in rows if row["open_rows"]),
        "open_rows": sum(row["open_rows"] or 0 for row in rows),
        "open_rows_with_owner": sum(row["open_rows_with_owner"] or 0 for row in rows),
        "runs_open_rows_unreadable": sum(1 for row in rows if row["open_rows"] is None),
        "runs_with_unverified": sum(1 for row in listed if row["unverified_rows"]),
        "unverified_rows": sum(row["unverified_rows"] for row in listed),
        "unverified_with_owner": sum(row["unverified_with_owner"] for row in listed),
        "runs_never_listed_unverified": len(rows) - len(listed),
        "runs_with_add_work": sum(1 for row in rows if row["add_work"]),
        "runs_with_send_back": sum(1 for row in rows if row["send_back"]),
        "strict": [{"run": row["run"], "text": row["open_next"]} for row in strict],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--json", help="write the rows and the summary here")
    parser.add_argument("runs", nargs="*", help="run directories (the folder holding state.md); default: every archived run")
    args = parser.parse_args()
    runs = [Path(run) for run in args.runs] or ledger.find_runs()
    rows = [row for row in (read_run(root) for root in runs) if row is not None]
    summary = summarize(rows, len(runs))
    print(f"archived runs found (reached product-acceptance): {summary['runs_found']}; readable: {summary['readable']}")
    print(f"  reached handoff done: {summary['reached_handoff']}")
    print(f"  with a current release-verify result: {summary['with_release_verify']}")
    print(f"  `Open for the next run` is not exactly 'none' (loose): {summary['open_next_loose']}")
    print(f"  ... and does not open with a 'none' phrase (strict): {summary['open_next_strict']}")
    print(f"  runs ending with >= 1 open assumption row: {summary['runs_with_open_rows']} (rows {summary['open_rows']}, "
          f"with a person owner {summary['open_rows_with_owner']}; unreadable {summary['runs_open_rows_unreadable']}); "
          "the reader never closes a plan row, so this is not a signal")
    print(f"  runs whose unverified list is non-empty at the end: {summary['runs_with_unverified']} "
          f"(rows {summary['unverified_rows']}, with an owner {summary['unverified_with_owner']}); "
          f"runs that never listed it: {summary['runs_never_listed_unverified']}")
    print(f"  runs with an add-work: {summary['runs_with_add_work']}; with a send-back: {summary['runs_with_send_back']}")
    print("\n--- strict rows, in run order ---")
    for index, row in enumerate(summary["strict"], 1):
        print(f"{index:>2}. {row['run']}\n    {row['text']}")
    if args.json:
        Path(args.json).write_text(json.dumps({"summary": {key: value for key, value in summary.items() if key != "strict"},
                                               "strict": summary["strict"], "rows": rows}, indent=1, sort_keys=True) + "\n",
                                   encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
