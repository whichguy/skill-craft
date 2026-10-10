#!/usr/bin/env python3
"""Two tallies behind the baseline journal's findings F2 and F6, for the runs baseline.json regraded, in one compact evidence file.

    python3 docs/experiments/commit-baseline-20261010/tallies.py [--runs /Users/dadleet/e2e-runs]
                                                                 [--baseline docs/experiments/commit-baseline-20261010/baseline.json]
                                                                 [--out docs/experiments/commit-baseline-20261010/tallies.json]

F2, the heads: every ``ShipLoop navigator |`` head a recorded reply starts (a call that names a packet file is the model reading it and
is skipped), counted whole or by the reason ``counters.head_or_why`` gives for it. F6, the commits: the commits of every run by class
and author (``counters.history``, the classification the commits block counts), and for the ``other`` class how many have git's own
``[branch sha] subject`` line for their abbreviated id in the run's events, which shows the model ran ``git commit`` itself.

Read-only like regrade.py (which it reuses for the run list, the host label and the reading of a run): it opens the runs baseline.json
regraded (the same 38 finished runs, whatever the folder holds since), starts no host, no model and no server, and writes nothing but
--out. No commit id, message or packet text is copied into the file; author names are the Git identities the commits carry.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import regrade  # noqa: E402  (also puts skills/shiploop/scripts and test/shiploop_e2e on the path)

counters = regrade.counters

SCHEMA = "shiploop-e2e-commit-baseline-tallies/v1"
KINDS = ("improve", "script", "other")


def head_replies(tools) -> dict:
    """{heads, whole, not_whole: {reason: n}} over the heads the recorded replies start; the model reading a packet file is no print."""
    counted, why = Counter(), Counter()
    for reply in tools.replies:
        if reply["packet"]:
            continue
        for text in counters.heads(reply["text"]):
            head, reason = counters.head_or_why(text)
            counted["heads"] += 1
            counted["whole"] += head is not None
            if reason:
                why[reason] += 1
    return {"heads": counted["heads"], "whole": counted["whole"], "not_whole": dict(sorted(why.items()))}


def confirmed(events: str, commit_id: str) -> bool:
    """Whether the events hold git's own `[branch sha] subject` line for the commit's abbreviated id (seven digits or more)."""
    return bool(re.search(r"\[[\w./-]+ (?:\(root-commit\) )?" + re.escape(commit_id[:7]), events))


def other_commits(found: dict | None, events: str) -> dict | None:
    """{n, by_author, git_confirmed} for the ``other`` commits of a history; None where the history could not be read."""
    if found is None:
        return None
    rows = [commit for commit in found["commits"] if commit["kind"] == "other"]
    return {"n": len(rows), "by_author": dict(sorted(Counter(commit["author"] for commit in rows).items())),
            "git_confirmed": sum(confirmed(events, commit["id"]) for commit in rows)}


def tally(folder: Path, row: dict) -> dict:
    """One run's heads and commits."""
    _shiploop, ledger, tools = regrade.read_run(folder)
    found, _why = counters.history(folder, ledger, tools)
    events = (folder / "events.jsonl").read_text(errors="replace")
    return {"run": row["run"], "host": regrade.host_label(row), "head_replies": head_replies(tools),
            "other_commits": other_commits(found, events),
            "authors": None if found is None else {kind: dict(sorted(Counter(c["author"] for c in found["commits"] if c["kind"] == kind).items()))
                                                   for kind in KINDS}}


def add(into: dict, part: dict) -> None:
    """Sum a tally's numbers into ``into`` (nested dicts of counts)."""
    for key, value in part.items():
        if isinstance(value, dict):
            add(into.setdefault(key, {}), value)
        else:
            into[key] = into.get(key, 0) + value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--runs", type=Path, default=Path.home() / "e2e-runs")
    parser.add_argument("--baseline", type=Path, default=HERE / "baseline.json")
    parser.add_argument("--out", type=Path, default=HERE / "tallies.json")
    args = parser.parse_args()
    root = args.runs.expanduser().resolve()
    baseline = json.loads(args.baseline.read_text())
    rows = [row for row in baseline["per_run"] if not row.get("not_regraded")]
    per_run = [tally(root / row["run"], row) for row in rows]
    heads_all, heads_host, other_all, other_host = {}, defaultdict(dict), {}, defaultdict(dict)
    authors = defaultdict(lambda: {kind: {} for kind in KINDS})
    for one in per_run:
        add(heads_all, one["head_replies"])
        add(heads_host[one["host"]], one["head_replies"])
        if one["other_commits"] is not None:
            add(other_all, one["other_commits"])
            add(other_host[one["host"]], one["other_commits"])
            for kind in KINDS:
                add(authors[one["host"]][kind], one["authors"][kind])
    head = subprocess.run(["git", "-C", str(regrade.ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip()
    document = {
        "schema": SCHEMA, "harness_head": head or None,
        "reads": "the runs baseline.json regraded (read-only); no run file is written",
        "runs": len(per_run),
        "head_replies": {"all": heads_all, "by_host": dict(sorted(heads_host.items()))},
        "other_commits": {"all": other_all, "by_host": dict(sorted(other_host.items()))},
        "commits_by_author": {"by_host": {host: authors[host] for host in sorted(authors)}},
        "per_run": [{key: value for key, value in one.items() if key != "authors"} for one in per_run],
    }
    args.out.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(per_run)} runs; {heads_all['heads']} heads, {other_all['n']} other commits; wrote {args.out}")


if __name__ == "__main__":
    main()
