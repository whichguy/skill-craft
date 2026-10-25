#!/usr/bin/env python3
"""E6: is the item's step plan sized for one implement iteration: inside its case's step band, with layers apart?

    python3 test/shiploop_e2e/evaluators/e6_step_size.py score <sample>
    python3 test/shiploop_e2e/evaluators/e6_step_size.py verify

From the records only: the sample's last accepted done step-plan result and its case's ``shape`` (step_cases.json):
- ``steps``: ``[min, max]`` on the number of steps (``max`` null: no upper bound);
- ``separate`` (optional): pairs of glob lists no one step may touch both sides of (a component and the org metadata
  that opens it). A step's paths are its own ``paths``, or the item's when it is the item's only step; a step of a
  several-step plan that declares none cannot be judged on separation and counts as apart.
``value`` is 1 when the step count is inside the band and no step joins a separated pair; else 0.
Reported, not decided on: per step its criteria, the requirements they serve (R-<n> and NFR-<n> IDs in their text), and
its product files: paths ShipLoop's path catalog does not class as test, docs or config, a ``-meta.xml`` sidecar counted
with its file and the step's own check (or proof) script left out, the same count arm C's gate makes.
``verify``: the committed excerpts in e6_records/ (run 4's one-step W1 and W3 fail their bands, battleship-1's six
steps and checkers-1's four pass) and planted plans: an over-split bug fix, a one-step fix, a two-step board that joins
its component and tab in one step and one that keeps them apart, and the product-file count.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

sys.path.insert(0, str(common.E2E.parents[1] / "skills" / "shiploop" / "scripts"))
import shiploop_item_scope as item_scope  # noqa: E402

RECORDS = Path(__file__).resolve().parent / "e6_records"
BINARY = True  # every value is 0 or 1, so experiment.py's queue can tell when a verdict can no longer change
REQUIREMENT = re.compile(r"\b(?:NFR|R)-\d+\b")
NOT_PRODUCT = ("test", "docs", "config")


def proof_script(path: str, proof: str) -> bool:
    """A script the step's check runs to prove it (``sh scripts/s1-check.sh``), not product the check exercises."""
    return path in proof and (path.endswith((".sh", ".apex")) or path.startswith("scripts/"))


def product_files(step: dict) -> list[str]:
    """The product files a step changes (see the module docstring)."""
    proof = str(step.get("check") or step.get("proof") or "")
    files = set()
    for path in step.get("paths") or ():
        if isinstance(path, str) and not proof_script(path, proof) and item_scope.classify(path) not in NOT_PRODUCT:
            files.add(path[:-len("-meta.xml")] if path.endswith("-meta.xml") else path)
    return sorted(files)


def _touches(paths: list[str], globs: list[str]) -> bool:
    return any(item_scope._matches(path, pattern) for path in paths for pattern in globs)


def judge(plan: dict, shape: dict) -> dict:
    steps = [step for step in plan.get("steps") or () if isinstance(step, dict)]
    low, high = shape["steps"]
    in_band = len(steps) >= low and (high is None or len(steps) <= high)
    texts = {str(c.get("id")): str(c.get("text") or "") for c in plan.get("criteria") or () if isinstance(c, dict)}
    rows, joined = [], []
    for step in steps:
        paths = list(step.get("paths") or (plan.get("paths") or [] if len(steps) == 1 else []))
        for first, second in shape.get("separate") or ():
            if _touches(paths, first) and _touches(paths, second):
                joined.append(str(step.get("id")))
        named = [texts.get(str(c), "") for c in step.get("criteria") or ()]
        rows.append({"id": step.get("id"), "criteria": len(named),
                     "requirements": len({ref for text in named for ref in REQUIREMENT.findall(text)}),
                     "product_files": len(product_files({**step, "paths": paths})),
                     "declared_paths": bool(step.get("paths"))})
    return {"value": int(in_band and not joined), "steps": len(steps), "band": [low, high], "in_band": in_band,
            "joined_layers": sorted(set(joined)), "max_criteria": max((r["criteria"] for r in rows), default=0),
            "max_product_files": max((r["product_files"] for r in rows), default=0),
            "declared_paths": sum(r["declared_paths"] for r in rows), "per_step": rows}


def score(sample: Path) -> dict:
    sample = Path(sample)
    try:
        name = json.loads((sample / "invocation.json").read_text())["case"]
    except (OSError, ValueError, KeyError):
        return {"value": None, "why": "no invocation.json naming the case"}
    shape = common.case(name).get("shape")
    if not shape:
        return {"value": None, "why": f"case {name} declares no shape"}
    plans = [r for r in common.results(common.run_dir(sample), "step-plan")
             if (r.get("result") or {}).get("outcome") == "done"]
    if not plans:
        return {"value": None, "why": "no accepted done step plan"}
    return {**judge(plans[-1]["result"], shape), "case": name, "action": plans[-1].get("action")}


def _step(ident: str, paths: list[str], criteria: list[str], check: str = "node --test") -> dict:
    return {"id": ident, "deps": [], "criteria": criteria, "paths": paths, "check": check}


def verify() -> list[dict]:
    rows = []
    records = sorted(RECORDS.glob("*.json"))
    if len(records) < 4:
        rows.append({"record": "e6_records", "ok": False, "why": f"expected 4 step-plan excerpts in {RECORDS}"})
    for path in records:
        record = json.loads(path.read_text())
        found = judge(record, common.case(record["case"])["shape"])
        rows.append({"record": path.stem, "case": record["case"], "expect": record["expected_value"], "got": found,
                     "ok": found["value"] == record["expected_value"]})
    criteria = [{"id": "C1", "text": "paginate([1,2,3,4,5],3,2) returns the last page. Serves R-1."}]
    fix = common.case("node-fix-bug")["shape"]
    split = {"criteria": criteria, "steps": [_step(f"S{n}", ["src/paginate.js"], ["C1"]) for n in (1, 2, 3)]}
    found = judge(split, fix)
    rows.append({"record": "planted over-split bug fix", "expect": "value 0", "got": found, "ok": found["value"] == 0})
    found = judge({"criteria": criteria, "steps": [_step("S1", ["src/paginate.js"], ["C1"])]}, fix)
    rows.append({"record": "planted one-step bug fix", "expect": "value 1", "got": found, "ok": found["value"] == 1})
    board = common.case("sf-chess-board-entry")["shape"]
    lwc = "force-app/main/default/lwc/slChessBoard/slChessBoard"
    tab = "force-app/main/default/tabs/SLChess_Board.tab-meta.xml"
    app = "force-app/main/default/applications/SLChess.app-meta.xml"
    joined = {"criteria": [], "steps": [_step("S1", [lwc + ".js", lwc + ".html", tab], []), _step("S2", [app], [])]}
    found = judge(joined, board)
    rows.append({"record": "planted board joining its component and tab", "expect": "value 0, S1 joined", "got": found,
                 "ok": found["value"] == 0 and found["joined_layers"] == ["S1"]})
    apart = {"criteria": [], "steps": [_step("S1", [lwc + ".js", lwc + ".html", lwc + ".js-meta.xml"], []),
                                       _step("S2", [tab, app], [])]}
    found = judge(apart, board)
    rows.append({"record": "planted board with the layers apart", "expect": "value 1", "got": found,
                 "ok": found["value"] == 1})
    counted = product_files(_step("S1", ["force-app/main/default/classes/SLChessEngine.cls",
                                         "force-app/main/default/classes/SLChessEngine.cls-meta.xml",
                                         "test/engine.test.js", "docs/shiploop/spec.md", "scripts/s1-check.sh"],
                                  [], "sh scripts/s1-check.sh"))
    rows.append({"record": "product files: sidecar with its file; test, docs and own proof left out",
                 "expect": ["force-app/main/default/classes/SLChessEngine.cls"], "got": counted,
                 "ok": counted == ["force-app/main/default/classes/SLChessEngine.cls"]})
    counted = product_files(_step("S1", ["server.js"], [], "node -e \"require('./server.js')\""))
    rows.append({"record": "product files: a file the check exercises still counts", "expect": ["server.js"],
                 "got": counted, "ok": counted == ["server.js"]})
    return rows


if __name__ == "__main__":
    raise SystemExit(common.cli(sys.modules[__name__], sys.argv[1:]))
