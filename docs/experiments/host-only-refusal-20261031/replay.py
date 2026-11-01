#!/usr/bin/env python3
"""Replay the host-only drift check's exemption over every archived test record (offline, no model calls).

A system-test verify record that ran the default-suite drift check holds one run per regression command, each with
``host_dependent_ids_shown``. For each such run this asks ``shiploop_test_loop._remote_base`` (the predicate the fix uses)
whether the command tests a hosted runtime, using the run's own state for its state-keeping test-strategy targets.
Reports how many refusals the exemption removes and how many it leaves. Usage: ``python3 replay.py``.
"""
from __future__ import annotations

import collections
import glob
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills" / "shiploop" / "scripts"))
import shiploop_store as store
import shiploop_test_loop as test_loop


def main() -> int:
    scanned = checked = 0
    totals = collections.Counter()
    removed, left, states = [], [], {}
    routes = collections.Counter()
    for path in sorted(glob.glob(os.path.expanduser("~/e2e-runs*/**/.shiploop-runs/*/run/tests/*.md"), recursive=True)):
        if "/slice/" in path or "/test/fixtures/" in path:
            continue
        scanned += 1
        try:
            record = store.read_record(Path(path))
        except (OSError, store.StorageError):
            continue
        runs = [r for r in (record.get("runs") or ()) if isinstance(r, dict) and "host_dependent_ids_shown" in r] \
            if isinstance(record, dict) else []
        if not runs:
            continue
        checked += 1
        run_dir = Path(path).parents[1]
        if run_dir not in states:
            try:
                states[run_dir] = test_loop.stateful_targets(store.read_record(run_dir / "state.md"))
            except (OSError, store.StorageError):
                states[run_dir] = {}
        for run in runs:
            exempt = test_loop._remote_base(run, states[run_dir]) is not None
            route = ("target" if run.get("target") and run["target"] in states[run_dir]
                     else "card" if exempt else "none")
            if exempt:
                routes[route] += 1
            flagged = run.get("status") == test_loop.DRIFT_STATUS
            totals[("flagged" if flagged else "clean", "exempt" if exempt else "checked")] += 1
            label = (str(run_dir).replace(os.path.expanduser("~"), "~")[-70:], route + " | " + (run.get("command") or "")[:60])
            if flagged and exempt:
                removed.append(label)
            if flagged and not exempt:
                left.append(label)
    print(f"test records scanned: {scanned}; records that ran the drift check: {checked}")
    print(f"drift refusals before: {totals[('flagged', 'exempt')] + totals[('flagged', 'checked')]}")
    print(f"  removed by the exemption (hosted-runtime commands): {totals[('flagged', 'exempt')]}")
    print(f"  left (any other command): {totals[('flagged', 'checked')]}")
    print(f"clean drift runs: {totals[('clean', 'exempt')]} would now be skipped, {totals[('clean', 'checked')]} still run")
    print(f"hosted-runtime runs by the way they were recognised: {dict(routes)}")
    for where, command in removed:
        print("  removed:", where, "|", command)
    for where, command in left:
        print("  LEFT:   ", where, "|", command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
