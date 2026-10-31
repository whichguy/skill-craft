#!/usr/bin/env python3
"""AS1: does test-strategy record the deployment as a test target that keeps state?

    python3 test/shiploop_e2e/probes/target_state_declared.py score <sample>
    python3 test/shiploop_e2e/probes/target_state_declared.py verify

From the run's last accepted test-strategy result and its ``targets`` rows (shiploop_test_layers: ``target``,
``keeps_state`` yes or no, ``base_state_route``). ``value`` is 1 when a row for the deployment says ``keeps_state``
"yes"; ShipLoop's own gate then already refused a row with no ``base_state_route``. Only a result whose outcome is
``done`` counts: a send-back or blocked result is a stage that will run again. A row counts as the deployment's when its
``target`` names one (deploy, clasp, remote, the folder, script.google.com, GAS, production, push), or names the web app
or the Apps Script project without also naming the checkout, since the project's own name is in the README and the
prompt. ``value`` is 0 when the done result has no such row, and None when there is no done test-strategy result.
``rows`` lists each row's target, state and route so a reader sees what a 0 declared instead.

This sits in probes/, outside the evaluator digest and the qualification snapshot (like probes/sdlc_probes.py), so adding
it moves neither; an experiment names it by path (experiments.json ``evaluator``). It is read at score time only.
``verify`` plants the records below; it calls no model.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluators"))
import common  # noqa: E402

BINARY = True
_DEPLOYMENT = re.compile(r"deploy|clasp|remote|local[_ -]?target|script\.google|\bgas\b|\bproduction\b|\bpush", re.I)
_PROJECT = re.compile(r"web ?app|apps? ?script", re.I)
_CHECKOUT = re.compile(r"checkout|worktree|working tree|node:test", re.I)


def names_deployment(target: str) -> bool:
    return bool(_DEPLOYMENT.search(target)) or (bool(_PROJECT.search(target)) and not _CHECKOUT.search(target))


def judge(result: dict | None) -> dict:
    if result is None:
        return {"value": None, "why": "no accepted test-strategy result with outcome done"}
    rows = [row for row in result.get("targets") or [] if isinstance(row, dict)]
    seen = [{"target": str(row.get("target", ""))[:120], "keeps_state": row.get("keeps_state"),
             "base_state_route": str(row.get("base_state_route", ""))[:160]} for row in rows]
    hit = [row for row in seen if row["keeps_state"] == "yes" and names_deployment(row["target"])]
    return {"value": int(bool(hit)), "rows": seen, "deployment_rows_keeping_state": len(hit)}


def score(sample: Path) -> dict:
    found = [row for row in common.results(common.run_dir(sample), "test-strategy")
             if (row.get("result") or {}).get("outcome") == "done"]
    return judge((found[-1].get("result") or {}) if found else None)


def _plant(root: Path, name: str, results: list[dict]) -> Path:
    """A sample folder whose run holds these accepted test-strategy results, oldest first, laid out as slice.py leaves one."""
    sample = root / name
    run = sample / "run"
    (run / "results").mkdir(parents=True)
    (sample / "invocation.json").write_text(json.dumps({"seeded": {"run_dir": str(run)}}))
    for number, result in enumerate(results):
        action = f"nav-{name}-{number}"
        path = run / "results" / (action + ".md")
        path.write_text("```shiploop-state\n" + json.dumps({"stage": "test-strategy", "action": action, "result": result})
                        + "\n```\n")
        os.utime(path, (1_700_000_000 + number, 1_700_000_000 + number))  # common.results orders by modification time
    return sample


def verify() -> list[dict]:
    deployment = {"target": "the Apps Script deployment the project is pushed to", "keeps_state": "yes",
                  "base_state_route": "an inventory check of the deployed files before the base run"}
    local = {"target": "node:test on this checkout", "keeps_state": "no", "base_state_route": "n/a"}
    done = {"outcome": "done"}
    cases = [("deployment kept as stateful", [{**done, "targets": [local, deployment]}], 1),
             ("deployment declared stateless", [{**done, "targets": [local, {**deployment, "keeps_state": "no",
                                                                             "base_state_route": "n/a"}]}], 0),
             ("only the checkout declared", [{**done, "targets": [local]}], 0),
             ("a checkout target marked stateful is not the deployment", [{**done, "targets": [
                 {"target": "node:test on this checkout", "keeps_state": "yes", "base_state_route": "git clean"}]}], 0),
             ("the project's own name on a checkout row is not the deployment", [{**done, "targets": [
                 {"target": "Apps Script server files under node:test in this checkout", "keeps_state": "yes",
                  "base_state_route": "git clean"}]}], 0),
             ("a deployment named by its address", [{**done, "targets": [
                 {"target": "GAS runtime on script.google.com", "keeps_state": "yes",
                  "base_state_route": "an inventory check"}]}], 1),
             ("a send-back result does not count", [{"outcome": "send-back", "targets": [deployment]}], None),
             ("the done result after a send-back counts", [{"outcome": "send-back", "targets": [deployment]},
                                                           {**done, "targets": [local]}], 0),
             ("no targets field", [{**done, "summary": "x"}], 0),
             ("no accepted test-strategy result", [], None)]
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for index, (label, results, want) in enumerate(cases):
            got = score(_plant(Path(tmp), f"s{index}", results))
            rows.append({"check": label, "want": want, "got": got["value"], "ok": got["value"] == want})
    return rows


if __name__ == "__main__":
    raise SystemExit(common.cli(sys.modules[__name__], sys.argv[1:]))
