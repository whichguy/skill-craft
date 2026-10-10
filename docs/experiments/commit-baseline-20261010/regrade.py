#!/usr/bin/env python3
"""Regrade the saved E2E runs with the harness's packets and commits counters and write one compact evidence file.

    python3 docs/experiments/commit-baseline-20261010/regrade.py [--runs /Users/dadleet/e2e-runs]
                                                                 [--out docs/experiments/commit-baseline-20261010/baseline.json]

Read-only: it opens every run folder under --runs (leaving a run whose harness is alive, which is still being written), reads the events, the ledger and the product repository the way run.py's main
reads them (``run.grade_shiploop`` finds the run directory, ``metrics.collect`` fills a ToolLog from events.jsonl, ``counters.build``
makes the two blocks, git is read through plumbing only), and writes nothing but --out. It does not rewrite a run's metrics.json or
result.json (they are run products and not committed), starts no host, no model and no server, and sends nothing anywhere. The
evidence keeps counts, short ids' absence included: no commit message and no packet text is copied into it.

The file holds, per run, the two blocks' counters, the run's hosts, model and effort read through runrecord (a mixed-host run is
named, and left out of the per-host summary), the runs that could not be regraded with the reason, and a summary per host and per
host+model+effort cell with the per-stage figures of the packets (n, median, min and max of file_bytes and of head_bytes).
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import counters  # noqa: E402
import listeners  # noqa: E402
import metrics  # noqa: E402
import run  # noqa: E402
import runrecord  # noqa: E402

SCHEMA = "shiploop-e2e-commit-baseline/v1"


def figures(values: list[int]) -> dict | None:
    """n, median, min and max of a list of sizes; None for an empty list (nothing measured, not a zero)."""
    return None if not values else {"n": len(values), "median": statistics.median(values), "min": min(values), "max": max(values)}


def knowledge_commits(folder: Path) -> dict | None:
    """The knowledge home's own commits (the subject only ShipLoop writes) among the run's commits, and how many carry a lessons
    section: the one part of ``script`` the plan quotes a share of (91% subject-only). The same constants, the same repository reads
    and the same ``lessons`` as counters.commits; None where counters.commits could not read the repository."""
    work = folder / "work"
    start, why = counters._starting_point(folder, work) if (work / ".git").exists() else (None, "no repository")
    if why:
        return None
    ids = counters._git(work, "rev-list", "--all", *(["--not", start] if start else [])).stdout.decode().split()
    found = [message for message in counters._messages(work, ids).values()
             if counters.KNOWLEDGE_SUBJECT.match(message.split("\n", 1)[0].strip())]
    return {"n": len(found), "with_lessons": sum(bool(counters.lessons(message)) for message in found)}


def regrade(folder: Path, root: Path) -> dict:
    """One run folder's row: its identity and the counters, or why it could not be regraded."""
    launches = runrecord.launches(folder)
    last = launches[-1][1] if launches else {}
    hosts = runrecord.hosts_used(folder)
    row = {"run": str(folder.relative_to(root)), "case": last.get("case"), "hosts": hosts, "mixed_host": runrecord.mixed_host(folder),
           "host": last.get("host"), "model": last.get("model"), "effort": last.get("effort")}
    if listeners.case_alive(folder):  # a read of the lock file: a harness holds it while its run is being written
        row.update(packets=None, commits=None, not_regraded="the run's harness is alive (its case lock is held): the run is not "
                   "finished and its record is still being written")
        return row
    unreadable = runrecord.unreadable(folder)
    if unreadable:
        row.update(packets=None, commits=None, not_regraded=f"launch records cannot be read: {', '.join(unreadable)}")
        return row
    shiploop = run.grade_shiploop(folder)
    ledger = Path(shiploop["run_dir"]) if shiploop.get("run_dir") else None
    row["engine_status"] = shiploop.get("status")
    tools = metrics.ToolLog()
    metrics.collect(folder, ledger, tools=tools)
    built = counters.build(folder, ledger, tools)
    row["commits_unmeasured"] = built["commits_unmeasured"]
    # The reason a head is null is one text with counts in it (the README): it is kept here only when the whole block is null.
    row["packets_unmeasured"] = built["packets_unmeasured"] if built["packets"] is None else {}
    block = built["packets"]
    row["entries"] = block
    row["packets"] = None if block is None else {
        "n": len(block), "head_measured": sum(entry["head_bytes"] is not None for entry in block),
        "file_bytes": sum(entry["file_bytes"] for entry in block),
        "head_bytes": sum(entry["head_bytes"] for entry in block if entry["head_bytes"] is not None)}
    row["commits"] = built["commits"]
    row["knowledge_commits"] = knowledge_commits(folder) if built["commits"] is not None else None
    return row


def totals(members: list[dict]) -> dict:
    """The counters of a group of runs: packets and heads, and the commits by class."""
    entries = [entry for row in members for entry in (row["entries"] or [])]
    commits = [row["commits"] for row in members if row["commits"] is not None]
    by_class = {"improve": defaultdict(int), "script": defaultdict(int), "other": defaultdict(int)}
    for block in commits:
        for kind in by_class:
            for key, value in block[kind].items():
                by_class[kind][key] += value
    return {
        "runs": len(members),
        "runs_with_packets_block": sum(row["packets"] is not None for row in members),
        "packets": len(entries),
        "heads_measured": sum(entry["head_bytes"] is not None for entry in entries),
        "runs_with_any_head_measured": sum(bool(row["packets"] and row["packets"]["head_measured"]) for row in members),
        "file_bytes": figures([entry["file_bytes"] for entry in entries]),
        "head_bytes": figures([entry["head_bytes"] for entry in entries if entry["head_bytes"] is not None]),
        "runs_with_commits_block": len(commits),
        "commits_counted": sum(block["counted"] for block in commits),
        "commits": {kind: dict(sorted(counts.items())) for kind, counts in by_class.items()},
        "knowledge_commits": {"n": sum(row["knowledge_commits"]["n"] for row in members if row["knowledge_commits"]),
                              "with_lessons": sum(row["knowledge_commits"]["with_lessons"] for row in members
                                                  if row["knowledge_commits"])},
    }


def by_stage(members: list[dict]) -> dict:
    entries = [entry for row in members for entry in (row["entries"] or [])]
    # An Improve child's second packet (`<action>-improve`) has its own structure: it is a row of its own, not part of its stage's.
    def label(entry: dict) -> str:
        return (entry["stage"] or "(no stage)") + (" [Improve packet]" if entry["action"].endswith("-improve") else "")
    found = {}
    for stage in sorted({label(entry) for entry in entries}):
        of_stage = [entry for entry in entries if label(entry) == stage]
        found[stage] = {"packets": len(of_stage), "file_bytes": figures([e["file_bytes"] for e in of_stage]),
                        "head_bytes": figures([e["head_bytes"] for e in of_stage if e["head_bytes"] is not None])}
    return found


def summary(rows: list[dict]) -> dict:
    """Per host, and per host+model+effort cell with the per-stage figures, over the rows that were regraded. A run two hosts worked
    on belongs to no host: it is summarised alone, under the hosts that worked on it."""
    hosts: dict[str, list[dict]] = defaultdict(list)
    cells: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row.get("not_regraded"):
            continue
        if row["mixed_host"]:
            hosts["mixed host (" + " then ".join(row["hosts"]) + ")"].append(row)
            continue
        hosts[row["host"]].append(row)
        cells[f"{row['host']} / {row['model']} / {row['effort'] or 'no effort'}"].append(row)
    return {"by_host": {name: totals(members) for name, members in sorted(hosts.items())},
            "by_cell": {name: {**totals(members), "by_stage": by_stage(members)} for name, members in sorted(cells.items())}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--runs", type=Path, default=Path.home() / "e2e-runs")
    parser.add_argument("--out", type=Path, default=HERE / "baseline.json")
    args = parser.parse_args()
    root = args.runs.expanduser().resolve()
    folders, notes = run.run_folders([root])
    rows = [regrade(folder, root) for folder in folders]
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip()
    document = {
        "schema": SCHEMA,
        "harness_head": head or None,  # the commit the counters code was at (a working tree change is not in it)
        "reads": "the saved runs under --runs (read-only); no metrics.json or result.json is rewritten",
        "notes": notes, "runs": len(rows), "not_regraded": [{"run": row["run"], "why": row["not_regraded"]} for row in rows
                                                                if row.get("not_regraded")],
        "summary": summary(rows),
        "per_run": [{key: value for key, value in row.items() if key != "entries"} for row in rows],
    }
    args.out.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(rows)} runs; {sum(bool(row.get('not_regraded')) for row in rows)} not regraded; wrote {args.out}")


if __name__ == "__main__":
    main()
