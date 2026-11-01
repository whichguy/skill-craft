#!/usr/bin/env python3
"""Read the live fourth link against the predictions the journal fixed before it ran (docs/shiploop-multipass-journal.md, "Round 3").

    python3 round3_readout.py OUTPUT PRIOR

OUTPUT is the folder run.py wrote for ``ticket-sla``; PRIOR is the third pass it continued from (``ticket-comments``). Each prediction is scored from
the run's result.json and from the delta block (test/shiploop_e2e/delta.py, recomputed from the run's files with the case's current ``delta.may_change``)
only. A prediction is ``held``, ``missed`` or ``unknown``. Nothing is written.

One correction is shown beside the recorded verdict. The case's retention check for the requirement IDs looked for the previous link's word and failed a
correct delivery (see the journal, Round 3, and the commit that fixed the case). A resume or a regrade replays the checks the run recorded at launch, so
a regrade cannot apply the fix; this script runs the case's CURRENT retention commands on the run's work directory instead and reports every recorded check
whose command has changed, with its recorded verdict and its verdict now. The recorded result.json is not altered.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "test" / "shiploop_e2e"))
sys.path.insert(0, str(HERE.parents[2] / "skills" / "shiploop" / "scripts"))
import delta  # noqa: E402
import run  # noqa: E402
import shiploop_knowledge_home as knowledge  # noqa: E402


def verdict(held: bool | None) -> str:
    return "unknown" if held is None else "held" if held else "missed"


def corrected_checks(out: Path, prior: Path, result: dict) -> list[dict]:
    """Every recorded check whose command differs from the case's current one, re-run now on the run's work directory."""
    cases = json.loads(run.CASES.read_text())
    current = run.load_case(type("Args", (), {"prompt": None, "case": "ticket-sla", "check": None}))[2]
    recorded = result.get("checks") or []
    if len(current) != len(recorded):
        return []
    changed = [i for i, (row, command) in enumerate(zip(recorded, current)) if row.get("command") != command]
    if not changed:
        return []
    rows = run.run_checks(out / "work", [current[i] for i in changed], timeout=300, env={"PRIOR_WORK": str(prior / "work")})
    return [{"index": i, "recorded": bool(recorded[i].get("pass")), "now": bool(row["pass"]), "output": (row.get("output") or "").strip(),
             "recorded_output": (recorded[i].get("output") or "").strip()} for i, row in zip(changed, rows)] if cases else []


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    out, prior = Path(argv[0]).expanduser(), Path(argv[1]).expanduser()
    result = json.loads((out / "result.json").read_text())
    block = delta.saved(out)
    ledger = (block or {}).get("delta") or {}
    checks = result.get("checks") or []
    failing = [i for i, row in enumerate(checks) if not row.get("pass")]
    fixed = corrected_checks(out, prior, result)
    still_failing = [i for i in failing if not any(row["index"] == i and row["now"] for row in fixed)]
    acceptance = (result.get("quality") or {}).get("acceptance") or {}
    hidden = acceptance.get("checks") or []
    hidden_failing = [i for i, row in enumerate(hidden) if not row.get("pass")]

    print(f"{out.name}: recorded pass {result.get('pass')} ({result.get('outcome_class')}); {len(checks) - len(failing)} of {len(checks)} checks recorded passing "
          f"(failing at {failing}); hidden {len(hidden) - len(hidden_failing)} of {len(hidden)} pass")
    for row in fixed:
        print(f"  check {row['index']} changed since the run: recorded {'pass' if row['recorded'] else 'FAIL'} [{row['recorded_output']}], "
              f"now {'pass' if row['now'] else 'FAIL'} [{row['output']}]")
    print("  " + delta.line(out.name, block).split(": ", 1)[1] if ledger else "  (no ledger)")

    ids = ledger.get("ids") or {}
    spec, arch = ids.get("spec.md") or {}, ids.get(knowledge.ARCHITECTURE) or {}
    place = ledger.get("placement") or {}
    env = place.get("environment.md") or {}
    plan = ledger.get("plan") or {}
    tests, follows = plan.get("test_cases") or {}, plan.get("step_plan_follows") or {}
    foot = ledger.get("footprint") or {}
    rows = [
        (1, "it passes: the earlier links' checks, its three, the five retention checks and all 16 hidden checks",
         f"recorded: {len(failing)} failing {failing}; with the corrected check: {len(still_failing)} failing; hidden failing {len(hidden_failing)}",
         verdict(None if not checks else (not still_failing and acceptance.get("observed") is True and not hidden_failing)) +
         ("" if not failing or still_failing else " once the wrong check is corrected (missed as recorded)")),
        (2, "the spec's old escalation requirement is touched (expected_touched of spec.md is not empty)",
         f"expected {spec.get('expected')}, touched {spec.get('expected_touched')}, changed {spec.get('changed')}, unexplained {spec.get('unexplained')}",
         verdict(None if "expected_touched" not in spec else bool(spec["expected_touched"]))),
        (3, "the architecture's old escalation decision is left standing (expected_untouched of architecture.md is not empty)",
         f"expected {arch.get('expected')}, untouched {arch.get('expected_untouched')}, touched {arch.get('expected_touched')}",
         verdict(None if "expected_untouched" not in arch else bool(arch["expected_untouched"]))),
        (4, "at least one earlier test file is modified (prior_tests_modified is not empty)",
         f"{foot.get('prior_tests_modified')}", verdict(None if not foot else bool(foot.get("prior_tests_modified")))),
        (5, "planning reads the old rule: the step plans' follows or the test cases' requirement name at least one kept ID",
         f"test cases {tests}; follows {follows}; delta ids {plan.get('delta_ids')} (the rule it changed, R-7, is counted as a delta ID)",
         verdict(None if not plan else (tests.get("preserved", 0) > 0 or follows.get("preserved", 0) > 0))),
        (6, "the leaks continue: environment.md gains 3 or more stray headings and a new decision is born under Superseded",
         f"env stray_added {len(env.get('stray_added') or [])}; architecture born_retired {arch.get('born_retired')}",
         verdict(None if not env else (len(env.get("stray_added") or []) >= 3 and bool(arch.get("born_retired"))))),
    ]
    for n, prediction, observed, outcome in rows:
        print(f"P{n} {outcome:9s} {prediction}\n     observed: {observed}")
    m = json.loads((out / "metrics.json").read_text()) if (out / "metrics.json").exists() else {}
    print(f"cost: {(result.get('process') or {}).get('elapsed_seconds')} s, model calls {m.get('model_calls')}, tokens processed "
          f"{((m.get('tokens') or {}).get('processed') or 0) / 1e6:.1f} M, gates {json.dumps(m.get('gate_counts'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
