#!/usr/bin/env python3
"""What changing the harness's commit counters from its own narrow reader to ShipLoop's shared one changed in the saved runs' counts.

    python3 docs/experiments/commit-baseline-20261010/reader_change.py [--runs /Users/dadleet/e2e-runs]
                                                                       [--baseline docs/experiments/commit-baseline-20261010/baseline.json]
                                                                       [--old-ref 8f3d4cbe]
                                                                       [--out docs/experiments/commit-baseline-20261010/reader-change.json]

Before 2026-10-10 ``test/shiploop_e2e/counters.py`` counted a commit's lessons and citations with a reader of its own (``Key
learnings`` and ``Learned`` only, case-sensitive, no heading form, any ``Word:`` line ending a section, a ``Learned-from`` id at
a line's start); it now imports ``skills/shiploop/scripts/shiploop_lessons.py``, the reader ShipLoop's ``improve-commit`` gate
reads with (SPEC S-12). This script reads the runs ``baseline.json`` regraded, takes each run's commits from ``counters.history`` (the
classification is unchanged), and counts every commit twice: with the old reader, loaded from Git at --old-ref (the file as it was
before the change), and with the shared one. Per class and host it reports how many commits each reader counted, how many the shared
reader gained and lost, how many were counted by both with a different lesson text, and how many counted lessons are exactly
``none`` (a descriptive figure, in no metrics key: the gate counts ``Key learnings: none``). Every changed commit is listed by run,
class and the label that made the difference, never by its text or id.

Read-only like regrade.py (which it reuses): starts no host, no model and no server, and writes nothing but --out. No commit message
and no commit id is copied into the file.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import types
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import regrade  # noqa: E402  (also puts skills/shiploop/scripts and test/shiploop_e2e on the path)
import shiploop_lessons as commit_lessons  # noqa: E402

counters = regrade.counters

SCHEMA = "shiploop-e2e-reader-change/v1"
KINDS = ("improve", "script", "other")


def old_reader(ref: str):
    """The harness's counters.py as it was at ``ref``, run as a module of its own: the reader this change replaced."""
    source = subprocess.run(["git", "-C", str(regrade.ROOT), "show", f"{ref}:test/shiploop_e2e/counters.py"], capture_output=True,
                            text=True, check=True).stdout
    module = types.ModuleType("counters_before_the_shared_reader")
    exec(compile(source, f"{ref}:test/shiploop_e2e/counters.py", "exec"), module.__dict__)  # noqa: S102 - the repository's own history
    return module


def exactly_none(text: str) -> bool:
    """Whether a lesson is the word ``none`` and nothing else, in any case, with punctuation or a bullet around it."""
    return re.sub(r"^[\W_]+|[\W_]+$", "", text).lower() == "none"


def compare(message: str, old) -> dict:
    """What each reader finds in one commit message: the old reader's lessons and ``Learned-from`` ids, the shared reader's lessons
    and citation tokens, and the labels of the sections that gave the shared reader its lessons."""
    before, after = old.lessons(message), commit_lessons.lessons(message)
    labels = [section.label for section in commit_lessons.sections(message, commit_lessons.LESSON_LABELS)
              if re.search(r"[^\W_]", section.body)]
    return {"old": bool(before), "new": bool(after), "labels": labels, "none": exactly_none(after),
            "text_differs": bool(before) and bool(after) and before != after,
            "old_ids": [match.group("id") for match in old.LEARNED_FROM.finditer(message)],
            "new_tokens": [cite.token for cite in commit_lessons.citations(message)]}


def records(folder: Path, row: dict, old) -> list[dict] | None:
    """One record per commit of a run: its class, the run's host label, what both readers counted. None where the history cannot be read."""
    _shiploop, ledger, tools = regrade.read_run(folder)
    found, _why = counters.history(folder, ledger, tools)
    if found is None:
        return None
    work, out = found["work"], []
    for commit in found["commits"]:
        got = compare(commit["message"], old)
        cited_old = [f for f in (old._commit_id(work, token) for token in got["old_ids"]) if f] if commit["kind"] == "improve" else []
        cited_new = [f for f in (counters._cited_commit(work, token) for token in got["new_tokens"]) if f] if commit["kind"] == "improve" else []
        out.append({"run": row["run"], "host": regrade.host_label(row), "kind": commit["kind"], "old": got["old"], "new": got["new"],
                    "labels": got["labels"], "none": got["none"], "text_differs": got["text_differs"],
                    "cited_old": bool(cited_old), "cited_new": bool(cited_new),
                    "learned_from_any_form": bool(re.search(r"learned.?from", commit["message"], re.I))})
    return out


def tally(members: list[dict]) -> dict:
    """Per class: the commits, what each reader counted, what the shared one gained and lost, and the lessons that are exactly none."""
    found = {}
    for kind in KINDS:
        of_kind = [r for r in members if r["kind"] == kind]
        found[kind] = {
            "n": len(of_kind),
            "old": {"with_lessons": sum(r["old"] for r in of_kind), "cited": sum(r["cited_old"] for r in of_kind)},
            "shared": {"with_lessons": sum(r["new"] for r in of_kind), "cited": sum(r["cited_new"] for r in of_kind)},
            "gained": sum(r["new"] and not r["old"] for r in of_kind), "lost": sum(r["old"] and not r["new"] for r in of_kind),
            "text_differs": sum(r["text_differs"] for r in of_kind), "exactly_none": sum(r["new"] and r["none"] for r in of_kind)}
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--runs", type=Path, default=Path.home() / "e2e-runs")
    parser.add_argument("--baseline", type=Path, default=HERE / "baseline.json")
    parser.add_argument("--old-ref", default="8f3d4cbe", help="the Git ref of the harness before the change")
    parser.add_argument("--out", type=Path, default=HERE / "reader-change.json")
    args = parser.parse_args()
    root = args.runs.expanduser().resolve()
    baseline = json.loads(args.baseline.read_text())
    rows = [row for row in baseline["per_run"] if not row.get("not_regraded")]
    old = old_reader(args.old_ref)
    every, by_host, unreadable = [], defaultdict(list), []
    for row in rows:
        found = records(root / row["run"], row, old)
        if found is None:
            unreadable.append(row["run"])
            continue
        every.extend(found)
        by_host[regrade.host_label(row)].extend(found)
    head = subprocess.run(["git", "-C", str(regrade.ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip()
    document = {
        "schema": SCHEMA, "harness_head": head or None, "old_ref": args.old_ref,
        "reads": "the runs baseline.json regraded (read-only); no run file is written",
        "runs": len(rows) - len(unreadable), "history_unreadable": unreadable,
        "all": tally(every), "by_host": {host: tally(members) for host, members in sorted(by_host.items())},
        "changed": [{"run": r["run"], "host": r["host"], "kind": r["kind"], "direction": "gained" if r["new"] else "lost",
                     "labels": r["labels"]} for r in every if r["old"] != r["new"]],
        "learned_from_any_form": sum(r["learned_from_any_form"] for r in every),
    }
    args.out.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n")
    changed = len(document["changed"])
    print(f"{document['runs']} runs, {len(every)} commits; {changed} counted differently; wrote {args.out}")


if __name__ == "__main__":
    main()
