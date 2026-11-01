#!/usr/bin/env python3
"""Counterfactual replay of the drift check on a LIVE run's real state (offline, no org, no model).

Usage: python3 -I counterfactual.py <scripts dir of one plugin version> <run dir holding state.md>

Takes the run's real state (test-strategy targets, step-plan rows, system-test-author rows), marks the org-native system
command host_dependent (the one thing the live run did not do), and calls that plugin version's default_suite_drift with a
stub that records every command it is asked to run and answers as if it had run and shown the marked ids.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

scripts, run_dir = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(scripts))
import shiploop_store as store  # noqa: E402
import shiploop_test_loop as tl  # noqa: E402

state = store.read_record(run_dir / "state.md")
result = tl._latest_root_result(state, "system-test-author")
rows = copy.deepcopy(list(result.get("system_commands") or ()))
org = [r for r in rows if r["command"].startswith("sf apex run test")]
if not org:
    print("no org-native system command in this run")
    raise SystemExit(2)
for r in org:
    r["host_dependent"] = True
marked_ids = [i for r in org for i in (r.get("ids") or ())]
asked = []


def run_one(command):
    asked.append(command)
    # as if the command ran and its reporter listed every marked case as passing
    body = "".join(f"✔ {i} (3ms)\n" for i in marked_ids) + f"ℹ tests {len(marked_ids)}\nℹ pass {len(marked_ids)}\nℹ fail 0\nℹ cancelled 0\n"
    return 0, body


drift = tl.default_suite_drift(state, rows, run_one)
plugin = scripts.parent.parent.parent.name if "cache" in str(scripts) else str(scripts)
print(f"plugin {plugin}: stateful targets {sorted(tl.stateful_targets(state))}")
print(f"  marked ids: {len(marked_ids)}  |  commands the check asked to run: {len(asked)}  |  refusals: {len(drift)}")
for c in asked:
    print("  asked:", c[:110])
for d in drift:
    print("  refusal:", d.get("status"), "| shown:", d.get("host_dependent_ids_shown"))
