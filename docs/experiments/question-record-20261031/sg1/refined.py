#!/usr/bin/env python3
"""SG1's replay with rule A refined by one clause (README.md, "SG1 replay"): a test-class path that this step or an
earlier step declares in its `paths` is not flagged, because implement may write it before the step's Proof runs.

The tool is ../../sdlc-gates-20261030/sg1_proof_order.py, loaded unchanged; only its ``check_plan`` result is filtered.
Usage: refined.py SHIPLOOP_SCRIPTS [GLOB ...]   (the same arguments as the tool; prints the same rows, plus `exempted`)
"""
import importlib.util
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[2] / "sdlc-gates-20261030" / "sg1_proof_order.py"
_spec = importlib.util.spec_from_file_location("sg1_proof_order", TOOL)
sg1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sg1)
_original = sg1.check_plan


def refined(plan, classify, exists_at=None):
    result = _original(plan, classify, exists_at)
    declared_so_far: dict[str, set[str]] = {}
    seen: set[str] = set()
    for step in (s for s in plan.get("steps") or () if isinstance(s, dict)):
        seen |= {str(path) for path in step.get("paths") or ()}
        declared_so_far[str(step.get("id"))] = set(seen)
    kept = [flag for flag in result["flags"]
            if not (flag["rule"] == "A" and flag["path"] in declared_so_far.get(str(flag["step"]), set()))]
    return dict(result, flags=kept, exempted=len(result["flags"]) - len(kept))


sg1.check_plan = refined

if __name__ == "__main__":
    scripts = Path(sys.argv[1])
    sg1.replay(scripts, sys.argv[2:] or ["~/e2e-runs/2026*/*"])
