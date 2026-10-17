"""Test support: a whole run's packets from synthetic results that look like a real run's (multi-step plans, two items).

The offline walk of ``test/shiploop_e2e/packets.py`` records a step plan with no steps, so implement's packet has no Step
line, and it stops at the first outer stage.  ``full_walk`` is the walk the print-order tests need: a two-item run whose first
item has a two-step plan (criteria, test commands of three suites, expectations, paths, follows, step skills) and whose
second has a one-step plan, through every stage of the graph to done, with the Improve stage after each reviewed result,
a mismatch record at validate-existing (the only packet a run issues there), a paused and a halted packet.  No model, no
project work: every result is a declaration, as the dry run's.  ``tokens`` lists, per packet, what its printed head must
hold, written from the fixture (a step's task, a command, an item's title), not from the generator under test.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_expectations as expectations  # noqa: E402
import shiploop_loops as loops  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_prompts as prompts  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402
import shiploop_store as store  # noqa: E402

CASE = {name: case for name, case in json.loads((ROOT / "test/shiploop_e2e/step_cases.json").read_text()).items()
        if not name.startswith("_")}["node-fix-bug"]
SECOND_ITEM = {"id": "W2", "title": "State the last-page rule in the README",
               "context": "The README states the default page size and what the last page holds."}
CHECK = "npm run lint"
FOCUSED = CASE["checks"][0]
PLAN = {
    "criteria": [
        {"id": "C1", "text": "The last partial page is returned. Confirm by: " + FOCUSED + "; pass when exit 0"},
        {"id": "C2", "text": "A regression test covers it. Confirm by: " + FOCUSED + "; pass when it lists TC-1"}],
    "steps": [
        {"id": "S1", "task": "Fix the page count in src/paginate.js", "deps": [], "criteria": ["C1"],
         "paths": ["src/paginate.js"], "skills": []},
        {"id": "S2", "task": "Return the items of the partial last page", "deps": ["S1"], "criteria": ["C1", "C2"],
         "paths": ["src/paginate.js", "src/index.js"], "skills": [{"name": "house-style", "why": "match the module style"}]}],
    "test_commands": [
        {"command": FOCUSED, "suite": "focused", "ids": ["TC-1", "TC-2"], "criteria": ["C1", "C2"]},
        {"command": CHECK, "suite": "check", "criteria": ["C1"]},
        {"command": "npm test", "suite": "regression"}],
    "expectations": [{"id": "E1", "state": "works", "statement": "paginate exists", "steps": ["S1"],
                      "paths": ["src/paginate.js"], "check": "test -e src/paginate.js"}],
    "paths": ["src/paginate.js", "src/index.js", "test/paginate.test.js"],
    "follows": ["R-1"],
}
SECOND_PLAN = {
    "criteria": [{"id": "C1", "text": "The README states the rule. Confirm by: grep -q last README.md; pass when exit 0"}],
    "steps": [{"id": "S1", "task": "Write the last-page rule in README.md", "deps": [], "criteria": ["C1"],
               "paths": ["README.md"], "skills": []}],
    "test_commands": [{"command": "grep -q last README.md", "suite": "check", "criteria": ["C1"]}],
    "expectations": [], "paths": ["README.md"], "follows": ["R-1"],
}
TEST_CASES = [{"id": "TC-1", "criterion": "C1", "requirement": "R-1", "oracle": "the request's example",
               "red": "returns no items", "green": "returns the partial page"},
              {"id": "TC-2", "criterion": "C2", "requirement": "R-1", "oracle": "the regression test's own assertion",
               "red": "the case is absent", "green": "the case passes"}]
LESSONS = "Keep the page count in one place."


def _result(stage: str, item: str | None, first: bool) -> dict[str, Any]:
    """A done result for ``stage`` with the fields the stage's hand-offs carry."""
    result: dict[str, Any] = {"outcome": "done", "summary": "Synthetic declaration; no work executed."}
    if stage == "plan":
        result["work_items"] = [CASE["work_item"], SECOND_ITEM]
    elif stage == "step-plan":
        result.update(PLAN if item == "W1" else SECOND_PLAN)
    elif stage == "test-spec":
        result["test_cases"] = TEST_CASES if item == "W1" else []
    return result


def _expectation_record(run_dir: Path, state: Mapping[str, Any]) -> None:
    """The record validate-existing's entry checks leave: one expectation that holds and one that does not match."""
    item, action = state["work_items"][state["work_index"]]["id"], navigator.current_action(state)["id"]
    rows = [{"id": "E1", "state": "works", "statement": "paginate exists", "steps": ["S1"], "check": "test -e src/paginate.js",
             "matches": True, "summary": "exit 0", "output": "expectations/" + action + "-E1.txt"},
            {"id": "E2", "state": "absent", "statement": "the helper is not there yet", "steps": ["S2"],
             "check": "test ! -e src/helper.js", "matches": False, "summary": "exit 1",
             "output": "expectations/" + action + "-E2.txt"}]
    record = {"schema": expectations.SCHEMA, "work_item": item, "action": action, "place": "base", "base": "0" * 40,
              "checkout": {}, "results": rows}
    store.atomic_write_text(run_dir / expectations.record_path(action), store.dumps(record, "ShipLoop expectation checks"))


def full_walk(case: Mapping[str, Any], delegation: str, work: str, run_dir: Path, *, lint: str = "report",
              planning_review: str = "stage") -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield ``(key, state read back from state.md)`` for every packet of the two-item run; keys are ``NN-<stage>``,
    ``NN-<stage>-improve``, ``NN-paused``, ``NN-halted`` and ``NN-done``."""
    count = 0

    def cold(current: dict[str, Any]) -> dict[str, Any]:
        store.write_record(run_dir / "state.md", current)
        read = store.read_record(run_dir / "state.md")
        if read["status"] == "active" and not read.get("active_improve"):
            try:
                for relative, text in loops.contract_writes(run_dir, read).items():
                    store.atomic_write_text(run_dir / relative, text)
            except loops.LoopError:
                pass
        return read

    state = navigator.new_state(work, case["prompt"], delegation=delegation, lint_option=lint,
                                planning_review=planning_review)
    paused = False
    for _ in range(400):
        if state["status"] == "done":
            count += 1
            yield f"{count:02d}-done", cold(state)
            return
        stage = navigator.current_stage(state)
        action = navigator.current_action(state)
        item = state["work_items"][state["work_index"]]["id"] if stage in stage_spec.INNER else None
        if stage == "validate-existing":
            _expectation_record(run_dir, state)
        count += 1
        yield f"{count:02d}-{stage}", cold(state)
        if stage == "test" and not paused:
            paused = True
            for command, label in (("pause", "paused"), ("halt", "halted")):
                count += 1
                yield f"{count:02d}-{label}", cold(navigator.control(state, command, "Synthetic control event."))
        waiting = navigator.apply(state, action["id"], _result(stage, item, item == "W1"))
        if waiting.get("active_improve") is not None:
            count += 1
            yield f"{count:02d}-{stage}-improve", cold(waiting)
            waiting = navigator.finish_improve(waiting, action["id"], {"summary": "Synthetic review", "lessons": LESSONS})
        state = waiting
    raise AssertionError("the synthetic run did not reach done")


def stage_of(key: str) -> str:
    """``NN-<stage>[-improve]`` -> the stage name (``improve`` suffix kept for an Improve packet)."""
    return key.split("-", 1)[1]


def is_producer(key: str, state: Mapping[str, Any]) -> bool:
    """Whether ``key`` is an active producer packet (not an Improve, paused, halted or done one)."""
    return state["status"] == "active" and state.get("active_improve") is None


def duty_headers(stage: str, delegation: str) -> list[str]:
    """The numbered duty items of ``stage``'s text, each as its first line ("9. **Plan record** in ...")."""
    text = prompts.prompt(stage, delegation=delegation)
    return [line for line in text.splitlines() if re.match(r"^\d+\. \*\*", line)]
