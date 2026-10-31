#!/usr/bin/env python3
"""AS1: does test-strategy record the deployment as a test target that keeps state?

    python3 test/shiploop_e2e/probes/target_state_declared.py score <sample>
    python3 test/shiploop_e2e/probes/target_state_declared.py verify

From the run's last accepted test-strategy result and its ``targets`` rows (shiploop_test_layers: ``target``,
``keeps_state`` yes or no, ``base_state_route``). ``value`` is 1 when a row for the deployment says ``keeps_state``
"yes"; ShipLoop's own gate then already refused a row with no ``base_state_route``. A row counts as the deployment's when
its ``target`` names one (deploy, web app, Apps Script, clasp, remote, the folder). ``value`` is 0 when the result has no
such row, and None when no test-strategy result was accepted. ``rows`` lists each row's target, state and route so a
reader sees what a 0 declared instead.

This sits in probes/, outside the evaluator digest and the qualification snapshot (like probes/sdlc_probes.py), so adding
it moves neither; an experiment names it by path (experiments.json ``evaluator``). It is read at score time only.
``verify`` plants the records below; it calls no model.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluators"))
import common  # noqa: E402

BINARY = True
_DEPLOYMENT = re.compile(r"deploy|web ?app|apps? ?script|clasp|remote|local[_ -]?target|\bproduction\b|\bpush", re.I)


def judge(result: dict | None) -> dict:
    if result is None:
        return {"value": None, "why": "no accepted test-strategy result"}
    rows = [row for row in result.get("targets") or [] if isinstance(row, dict)]
    seen = [{"target": str(row.get("target", ""))[:120], "keeps_state": row.get("keeps_state"),
             "base_state_route": str(row.get("base_state_route", ""))[:160]} for row in rows]
    hit = [row for row in seen if row["keeps_state"] == "yes" and _DEPLOYMENT.search(row["target"])]
    return {"value": int(bool(hit)), "rows": seen, "deployment_rows_keeping_state": len(hit)}


def score(sample: Path) -> dict:
    found = common.results(common.run_dir(sample), "test-strategy")
    return judge((found[-1].get("result") or {}) if found else None)


def _plant(root: Path, name: str, result: dict | None) -> Path:
    """A sample folder whose run holds one accepted test-strategy result (or none), laid out as slice.py leaves one."""
    sample = root / name
    run = sample / "run"
    (run / "results").mkdir(parents=True)
    (sample / "invocation.json").write_text(json.dumps({"seeded": {"run_dir": str(run)}}))
    if result is not None:
        action = "nav-" + name
        (run / "results" / (action + ".md")).write_text(
            "```shiploop-state\n" + json.dumps({"stage": "test-strategy", "action": action, "result": result}) + "\n```\n")
    return sample


def verify() -> list[dict]:
    deployment = {"target": "the Apps Script deployment the project is pushed to", "keeps_state": "yes",
                  "base_state_route": "an inventory check of the deployed files before the base run"}
    local = {"target": "node:test on this checkout", "keeps_state": "no", "base_state_route": "n/a"}
    cases = [("deployment kept as stateful", {"targets": [local, deployment]}, 1),
             ("deployment declared stateless", {"targets": [local, {**deployment, "keeps_state": "no",
                                                                    "base_state_route": "n/a"}]}, 0),
             ("only the checkout declared", {"targets": [local]}, 0),
             ("a checkout target marked stateful is not the deployment", {"targets": [
                 {"target": "node:test on this checkout", "keeps_state": "yes", "base_state_route": "git clean"}]}, 0),
             ("no targets field", {"summary": "x"}, 0),
             ("no accepted test-strategy result", None, None)]
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for index, (label, result, want) in enumerate(cases):
            got = score(_plant(Path(tmp), f"s{index}", result))
            rows.append({"check": label, "want": want, "got": got["value"], "ok": got["value"] == want})
    return rows


if __name__ == "__main__":
    raise SystemExit(common.cli(sys.modules[__name__], sys.argv[1:]))
