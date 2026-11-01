#!/usr/bin/env python3
"""Read a ShipLoop run's records for the four signals of the host-only fix (read-only).

Usage: live_check.py <run output folder>   (finds every state.md below it)

Signals, in the order the stages run:
  1 step plan: a regression test command (suite regression or regression: true) per work item
  2 system-test-author: system_commands rows, and which carry host_dependent: true (with suite and ids)
  3 system-test: every recorded run of a command, and any host-dependent-in-default-suite refusal
  4 the marked row's suite after the run (focused keeps its IDs counted; check loses them)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills" / "shiploop" / "scripts"))
import shiploop_store as store  # noqa: E402
import shiploop_test_loop as tl  # noqa: E402


def stages(state):
    rows = []
    for h in state.get("history", ()):
        rows.append((h.get("stage"), h.get("workitem"), h.get("outcome")))
    return rows


def main(argv):
    out = Path(argv[1]).expanduser()
    found = sorted(p for p in out.rglob("state.md") if "/home/" not in str(p.relative_to(out)).join(["/", ""]))
    if not found:
        print("no state.md under", out)
        return 1
    for state_path in found:
        run = state_path.parent
        print("=" * 100)
        print("run:", str(run).replace(str(Path.home()), "~"))
        state = store.read_record(state_path)
        print("status:", state.get("status"), "| work items:", [i.get("id") for i in state.get("work_items", ())])
        line = []
        for stage, item, outcome in stages(state):
            line.append(f"{stage}{'/' + str(item) if item else ''}:{outcome}")
        print("timeline:", " > ".join(line) if line else "(no history yet)")
        refusals = [x for x in line if x.endswith(("send-back", "refused", "blocked", "failed"))]
        print("send-backs, refusals and blocks in the timeline:", refusals or "none")

        try:
            print("\ntest-strategy targets that keep state (route B):", dict(tl.stateful_targets(state)) or "none declared")
        except Exception as exc:
            print("\ntest-strategy targets: unreadable:", exc)
        print("\n-- signal 1: step-plan test commands")
        for item in state.get("work_items", ()):
            try:
                _action, result = tl._step_plan(state, str(item.get("id")))
            except Exception as exc:  # defensive: read-only report
                print("  ", item.get("id"), "no step plan yet:", exc)
                continue
            for row in result.get("test_commands") or ():
                reg = row.get("suite") == "regression" or row.get("regression")
                print(f"   {item.get('id')}: {'REGRESSION' if reg else row.get('suite'):<10} target={row.get('target')} {row['command'][:110]}")

        print("\n-- signal 2: system-test-author system_commands")
        try:
            res = tl._latest_root_result(state, "system-test-author")
        except Exception as exc:
            res = {}
            print("   none yet:", exc)
        for row in res.get("system_commands") or ():
            print(f"   suite={row.get('suite'):<10} host_dependent={row.get('host_dependent')} ids={len(row.get('ids') or ())} {row['command'][:100]}")
        if not res:
            print("   (system-test-author not accepted yet)")

        print("\n-- signal 3 and 4: system-test records")
        tests = run / "tests"
        seen = 0
        for rec_path in sorted(tests.glob("*.md")) if tests.is_dir() else ():
            try:
                rec = store.read_record(rec_path)
            except Exception:
                continue
            for r in rec.get("runs") or ():
                if not isinstance(r, dict):
                    continue
                if "host_dependent_ids_shown" in r or r.get("status") == tl.DRIFT_STATUS:
                    seen += 1
                    print(f"   {rec_path.name}: status={r.get('status')} shown={r.get('host_dependent_ids_shown')} {str(r.get('command'))[:90]}")
        if not seen:
            print("   no drift-check run recorded (the check skipped every hosted-runtime command, or system-test has not run)")
        drift_status = [x for x in line if "host-dependent" in x]
        print("   refusals naming host-dependent in the timeline:", drift_status or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
