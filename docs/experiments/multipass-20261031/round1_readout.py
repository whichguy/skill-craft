#!/usr/bin/env python3
"""Read the live third pass against the predictions the journal fixed before it ran (docs/shiploop-multipass-journal.md, "Round 1").

    python3 round1_readout.py OUTPUT [--json]

OUTPUT is the folder run.py wrote for ``ticket-comments`` (continuing from a saved second pass). Each prediction is scored from the
run's result.json and from the delta block (test/shiploop_e2e/delta.py) only, so the conclusion is the numbers' and not the reader's.
A prediction is ``held``, ``missed`` or ``unknown`` (a part the run did not record). Nothing is written.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "test" / "shiploop_e2e"))
sys.path.insert(0, str(HERE.parents[2] / "skills" / "shiploop" / "scripts"))
import delta  # noqa: E402
import shiploop_knowledge_home as knowledge  # noqa: E402


def verdict(held: bool | None) -> str:
    return "unknown" if held is None else "held" if held else "missed"


def read(out: Path) -> dict:
    result = json.loads((out / "result.json").read_text())
    block = delta.saved(out).get("delta")
    rows: list[dict] = []

    checks = result.get("checks") or []
    failing = [row["command"][:70] for row in checks if not row.get("pass")]
    acceptance = (result.get("quality") or {}).get("acceptance") or {}
    hidden_failing = [row["id"] for row in acceptance.get("checks") or [] if not row.get("pass")]
    rows.append({"n": 1, "prediction": "every check passes: the earlier links' 5, its own 3, its 5 retention checks, and the inherited hidden checks",
                 "observed": f"pass {result.get('pass')}; {len(checks) - len(failing)} of {len(checks)} checks; hidden: "
                             + ("not observed" if not acceptance.get("observed") else f"{len(hidden_failing)} failing {hidden_failing}")
                             + (f"; failing: {failing}" if failing else ""),
                 "verdict": verdict(None if not checks else (not failing and acceptance.get("observed") is True and not hidden_failing))})

    notified = [row for row in checks if "Check comment notices" in row.get("command", "")]
    rows.append({"n": 2, "prediction": "its two comment notices are distinct (the outbox key names the comment)",
                 "observed": "no such check in the result" if not notified else f"the check {'passed' if notified[0]['pass'] else 'FAILED'}",
                 "verdict": verdict(None if not notified else notified[0]["pass"])})

    plan = (block or {}).get("plan") or {}
    tests, follows = plan.get("test_cases") or {}, plan.get("step_plan_follows") or {}
    rows.append({"n": 3, "prediction": "test cases cite no kept requirement; step plans name more kept IDs than new ones",
                 "observed": f"test cases {tests}; follows {follows}" if plan else "plan not readable",
                 "verdict": verdict(None if not plan else (tests.get("preserved") == 0 and tests.get("unknown") == 0
                                                           and follows.get("preserved", 0) > follows.get("delta", 0)))})

    place = (block or {}).get("placement") or {}
    env, arch = place.get("environment.md") or {}, place.get(knowledge.ARCHITECTURE) or {}
    ids = ((block or {}).get("ids") or {}).get(knowledge.ARCHITECTURE) or {}
    grew = (env.get("bytes") or {}).get("final", 0) - (env.get("bytes") or {}).get("prior", 0)
    rows.append({"n": 4, "prediction": "environment.md gains 3+ stray headings and 4+ KiB with no named section changed; architecture.md gains a stray heading or a born-retired entry",
                 "observed": (f"env stray_added {len(env.get('stray_added') or [])}, +{grew / 1024:.1f} KiB, changed_sections {env.get('changed_sections')}; "
                              f"arch stray_added {arch.get('stray_added')}, born_retired {ids.get('born_retired')}") if block else "ledger not readable",
                 "verdict": verdict(None if not block else (len(env.get("stray_added") or []) >= 3 and grew >= 4096 and not env.get("changed_sections")
                                                            and bool(arch.get("stray_added") or ids.get("born_retired"))))})

    final = knowledge.entries(out / "work", knowledge.ARCHITECTURE).get("AD-3")
    rows.append({"n": 5, "prediction": "the mislabelled AD-3 is not repaired by the run (still filed under Superseded at the end)",
                 "observed": "AD-3 is no longer an entry" if final is None else f"AD-3 retired={final.retired}",
                 "verdict": verdict(None if final is None else final.retired)})

    spec = ((block or {}).get("ids") or {}).get("spec.md") or {}
    rows.append({"n": 6, "prediction": "the spec keeps R-1 to R-7 byte for byte, adds R-8 or more, and says 'Basis: current request'",
                 "observed": (f"added {spec.get('added')}, changed {spec.get('changed')}, dropped {spec.get('dropped')}, "
                              f"relative wording {(place.get('spec.md') or {}).get('relative_wording', {}).get('n')}") if block else "ledger not readable",
                 "verdict": verdict(None if not block else (not spec.get("changed") and not spec.get("dropped") and len(spec.get("added") or []) >= 1
                                                            and ((place.get("spec.md") or {}).get("relative_wording") or {}).get("n", 0) >= 1))})
    return {"output": str(out), "delta_line": delta.line(out.name, {"delta": block, "delta_unmeasured": {}}) if block else None, "predictions": rows}


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    report = read(Path(args[0]).expanduser().resolve())
    if "--json" in argv:
        print(json.dumps(report, indent=2))
        return 0
    print(report["delta_line"] or "(no delta block)")
    for row in report["predictions"]:
        print(f"P{row['n']} {row['verdict']:8s} {row['prediction']}\n     observed: {row['observed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
