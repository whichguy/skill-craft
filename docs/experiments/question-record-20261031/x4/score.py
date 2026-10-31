#!/usr/bin/env python3
"""Score X4 (README.md, "X4") with SG1's rule and no judge: a sample is a fault when SG1's ``check_plan`` flags any step
of its step plan, reading "exists at the item base" from the base file list saved by build.py (git mode, so every path
is judged).  An unparseable answer (no shiploop-state block, or no steps) is counted apart.  Writes
../scores-x4-<slug>.json.  Usage: x4/score.py [SUBJECT_SLUG]
"""
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import SKILL_SCRIPTS, envelope_text, state_block  # noqa: E402
from stats import mean, permutation_p  # noqa: E402

sys.path.insert(0, str(SKILL_SCRIPTS))
import shiploop_item_scope as scope  # noqa: E402

TOOL = HERE.parents[1] / "sdlc-gates-20261030" / "sg1_proof_order.py"
_spec = importlib.util.spec_from_file_location("sg1_proof_order", TOOL)
sg1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sg1)


def main() -> None:
    slug = sys.argv[1] if len(sys.argv) > 1 else "terra"
    rows = []
    for packet_file in sorted((HERE / "packets").glob("*.json")):
        name = packet_file.stem
        packet = json.loads(packet_file.read_text())
        present = set(packet["base_files"])
        for out in sorted((HERE / slug).glob(f"{name}-*-s*.json")):
            if out.name.endswith(".meta.json"):
                continue
            arm = out.stem.split("-")[-2]
            result = state_block(envelope_text(out))
            steps = (result or {}).get("steps") if isinstance(result, dict) else None
            if not isinstance(steps, list) or not steps:
                rows.append({"packet": name, "role": packet["role"], "arm": arm, "file": out.name, "parsed": False})
                continue
            checked = sg1.check_plan(result, scope.classify, lambda step, path: path in present)
            proofs = [s.get("proof") for s in steps if isinstance(s, dict)]
            rows.append({"packet": name, "role": packet["role"], "arm": arm, "file": out.name, "parsed": True,
                         "fault": bool(checked["flags"]), "flags": checked["flags"], "judged": checked["judged"],
                         "unjudged": checked["unjudged"], "steps": len(steps), "proofs": proofs})
    report = {"subject": slug, "rows": rows, "arms": {}, "packets": {}, "rule": {}}
    for arm in ("A", "Q"):
        parsed = [r for r in rows if r["arm"] == arm and r["parsed"]]
        report["arms"][arm] = {"n": len([r for r in rows if r["arm"] == arm]), "parsed": len(parsed),
                               "fault_rate": mean(r["fault"] for r in parsed) if parsed else None,
                               "unparseable_share": 1 - len(parsed) / max(1, len([r for r in rows if r["arm"] == arm]))}
    for name in sorted({r["packet"] for r in rows}):
        report["packets"][name] = {arm: {"faults": sum(r.get("fault", False) for r in rows if r["packet"] == name and r["arm"] == arm),
                                         "parsed": sum(r["parsed"] for r in rows if r["packet"] == name and r["arm"] == arm)}
                                   for arm in ("A", "Q")}
    a = [1.0 if r["fault"] else 0.0 for r in rows if r["arm"] == "A" and r["parsed"]]
    q = [1.0 if r["fault"] else 0.0 for r in rows if r["arm"] == "Q" and r["parsed"]]
    # a lower fault rate is the gain: test the share of clean plans
    p = permutation_p([1 - v for v in a], [1 - v for v in q]) if a and q else None
    report["rule"] = {"p_one_sided_fewer_faults": p,
                      "A_has_faults": any(a),
                      "Q adopted": bool(a and q and p is not None and p < 0.05
                                        and report["arms"]["Q"]["unparseable_share"] <= report["arms"]["A"]["unparseable_share"])}
    (HERE.parent / f"scores-x4-{slug}.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"arms": report["arms"], "packets": report["packets"], "rule": report["rule"]}, indent=1))


if __name__ == "__main__":
    main()
