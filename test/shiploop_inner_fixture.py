"""Synthetic inner-stage results that meet the 8-stage inner loop's script gates, for suites that drive the CLI.

The quality, lint and test-loop suites walk a run through ``complete`` with synthetic results.  Since 2026-10-10 every
inner stage's ``complete`` checks the stage's Until Loop receipt and the stage's own gates (step-plan expectations and
step skills, test-spec cases, carry-forward's skill decision).  ``fill`` adds the fields a correct model would write and
leaves every field the caller set alone; ``loop`` runs the stage's loop through the real runtime
(``shiploop_loop_support.finish_loop``), so no receipt is ever written by hand.
"""

from __future__ import annotations

import contextlib
import io
import shlex
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/shiploop/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import shiploop_assumptions as assumptions  # noqa: E402
import shiploop_concerns as concern_map  # noqa: E402
import shiploop_expectations as expectations  # noqa: E402
import shiploop_knowledge_home as knowledge  # noqa: E402
import shiploop_lint as lint  # noqa: E402
import shiploop_knowledge_support as knowledge_support  # noqa: E402
import shiploop_loop_support as loop_support  # noqa: E402
import shiploop_loops as loops  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_test_loop as test_loop  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills/shiploop"
IMPROVE_CARD = ROOT / "skills/improve/SKILL.md"
CORE = types.SimpleNamespace(PACKAGE_ROOT=PACKAGE, REF_DIR=PACKAGE / "references")
DONE = {"outcome": "done", "summary": "Synthetic declaration; no work executed."}

SKILL_NONE = {"decision": "none", "reason": "Synthetic fixture: no procedure repeated."}
# A done document result's reflection record (design T §9.1 2b-3): nothing to record in a fixture.
KNOWLEDGE_NONE = {"spec": "none: synthetic fixture", "architecture": "none: synthetic fixture",
                  "environment": "none: synthetic fixture"}
# A done release-verify result's lessons (consumer contract 3.4).
LESSONS = {"learned": "Synthetic fixture: nothing learned.", "considerations": "none",
           "open_next": "none"}


def no_concerns_map(item_ids: Iterable[str]) -> dict[str, list[dict[str, str]]]:
    """A done plan's ``concerns`` (build plan S2.2) where no concern applies to any item in ``item_ids``: the
    synthetic fixture default for suites whose intent is not the concern map itself."""
    reason = "Synthetic fixture: no concern applies."
    return {str(item): [{"id": name, "applies": "no", "reason": reason} for name in concern_map.CONCERN_IDS]
            for item in item_ids}


def fixture_test_layers() -> dict[str, Any]:
    """A done test-strategy's test layers (run-5 batch F1, F3) for a synthetic run: one part of the code, whose unit layer
    the fixture's own commands test, every test on the checkout.  The default for suites whose intent is not the layers
    (a run that records test_layers_na needs each step plan with code paths to list its own rows)."""
    return {"test_layers": [{"code": "fixture code", "layer": "unit", "harness": "the fixture's recorded commands",
                          "status": "available", "reason": "synthetic run"}], "targets": []}


def fixture_intake(state: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    """A done intake result whose summary cites every sentence of the run's request (IN1, 2026-10-26: a done intake
    that leaves one uncited is refused), as an intake maps each sentence to an outcome, a boundary or a question."""
    import shiploop_request as request  # the scripts are on the path once the fixture is imported
    merged = dict(result)
    count = len(request.sentences(str(state.get("prompt") or "")))
    summary = str(merged.get("summary") or "")
    missing = [n for n in range(1, count + 1) if n not in request.cited(summary)]
    if merged.get("outcome") == "done" and missing and summary.strip():
        merged["summary"] = summary.rstrip() + " (" + ", ".join("S" + str(n) for n in missing) + ")"
    return merged


def fixture_suite(state: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    """A done test-spec result with no cases, at the last work item, with a ``suite_requirements`` row for each primary
    requirement no earlier case names (TS1, 2026-10-26), observed by the run's first recorded test command: a fixture
    whose step plan lists no focused case IDs has no case to name it.  A result with cases is left to TS1."""
    import shiploop_primary as primary  # the scripts are on the path once the fixture is imported
    merged = dict(result)
    commands = primary._recorded_commands(state)
    if merged.get("outcome") != "done" or merged.get("test_cases") or primary.SUITE_FIELD in merged or not commands \
            or not primary._is_last_item(state):
        return merged
    covered = primary.test_spec_coverage(state, merged)
    missing = [ident for ident in primary.primary_ids(state) or () if not covered.get(ident)]
    if missing:
        merged[primary.SUITE_FIELD] = [{"requirement": ident, "command": commands[0]} for ident in missing]
    return merged


def fixture_primary(state: Mapping[str, Any]) -> dict[str, Any]:
    """A done spec's primary requirements (run-5 batch F6) for a synthetic run: R-1, whose entry this writes into the
    living spec when it is missing, as a spec stage writes its requirements before its done."""
    knowledge_support.write_spec(state)
    return {"primary": ["R-1"]}


def executed_criteria(criteria: Any) -> Any:
    """``criteria`` with ``confirm: executed`` on each row that lacks one (run-5 batch F1): the fixture default."""
    if not isinstance(criteria, list):
        return criteria
    return [dict(row, confirm=row.get("confirm", "executed")) if isinstance(row, Mapping) else row for row in criteria]


def test_cases_for(plan: Mapping[str, Any]) -> list[dict[str, str]]:
    """One case per focused id of a step plan, naming the command's first criterion and the fixture's R-1."""
    criteria = [str(row.get("id")) for row in plan.get("criteria") or () if isinstance(row, Mapping)] or ["C1"]
    cases: list[dict[str, str]] = []
    for row in plan.get("test_commands") or ():
        if isinstance(row, Mapping) and row.get("suite") == "focused":
            for ident in row.get("ids") or ():
                if ident not in [case["id"] for case in cases]:
                    cases.append({"id": ident, "criterion": (row.get("criteria") or criteria)[0], "requirement": "R-1",
                                  "oracle": "the focused command", "red": "fails before the change",
                                  "green": "passes after it"})
    return cases


def expectations_for(repo: Path, steps: list[Mapping[str, Any]], run_dir: Optional[Path] = None,
                     work_item: str = "") -> list[dict[str, Any]]:
    """One expectation per step path: works (on the item's lint base, else the checkout) or absent (new), each with
    a read-only check.  The step-plan gate judges presence on the lint base, so a revised plan still calls a file
    the item added absent."""
    base = lint.read_base(Path(run_dir), work_item) if run_dir is not None and work_item else None
    files = expectations._base_files(repo, base)
    rows: list[dict[str, Any]] = []
    for step in steps:
        for path in step.get("paths") or ():
            present = expectations._exists(repo, files, path)
            glob = any(ch in path for ch in "*?[")
            check = "true" if glob else ("test -e " if present else "test ! -e ") + shlex.quote(path)
            rows.append({"id": "E" + str(len(rows) + 1), "state": "works" if present else "absent",
                         "statement": path + (" exists" if present else " is new"), "steps": [str(step["id"])],
                         "paths": [path], "check": check})
    return rows


def fill(state: Mapping[str, Any], stage: str, result: Mapping[str, Any],
         run_dir: Optional[Path] = None) -> dict[str, Any]:
    """``result`` with the fields a done result at ``stage`` needs; the caller's own fields win."""
    result = dict(result)
    if result.get("outcome") != "done":
        return result
    repo = Path(str(state["repo"]))
    if stage == "implement":
        # An inline step's notes (build plan S3.2), which its commit carries; none to record in a fixture.
        result.setdefault("learned", ["none"])
        result.setdefault("decisions", ["none"])
    if stage == "step-plan":
        if "test_commands" not in result:
            result.update(test_commands=[], test_commands_na="Synthetic fixture; no test commands.")
        if "paths" not in result:
            result["paths"] = ["src/**"]
        if result.get("test_commands") and "criteria" not in result:
            result["criteria"] = [{"id": "C1", "text": "Synthetic criterion."}]
        if "criteria" in result:
            result["criteria"] = executed_criteria(result["criteria"])
        if result.get("test_commands") and not any(isinstance(row, Mapping) and row.get("suite") == "check"
                                                   for row in result["test_commands"]):
            result.setdefault("check_na", "Synthetic fixture: these files have no lint, type or build command.")
        result.setdefault("follows", [])
        if "steps" not in result:
            step: dict[str, Any] = {"id": "S1", "task": "Make the planned change.", "paths": list(result["paths"])}
            if result.get("criteria"):
                step["criteria"] = [row["id"] for row in result["criteria"]]
            result["steps"] = [step]
        # Every step records its Proof (implement-step fix plan 4.1); a fixture that is not about it proves nothing.
        result["steps"] = [dict(step, skills=step.get("skills", []), proof=step.get("proof", "true"))
                           if isinstance(step, Mapping) else step for step in result["steps"]]
        if "expectations" not in result:
            result["expectations"] = expectations_for(repo, result["steps"], run_dir, _current_item(state))
    elif stage == "test-spec":
        # The cases live in the result (consumer contract 3.3); no gate reads a test-spec file.
        _action, plan = test_loop._step_plan(state, _current_item(state))
        result.setdefault("test_cases", test_cases_for(plan))
        result = fixture_suite(state, result)
    elif stage == "document":
        result.setdefault("knowledge", dict(KNOWLEDGE_NONE))
    elif stage == "carry-forward":
        result.setdefault("skill", dict(SKILL_NONE))
    if stage in assumptions.OPEN_ITEM_STAGES:
        result.setdefault("assumptions", [])
    return result


def _current_item(state: Mapping[str, Any]) -> str:
    found = loops.cursor(state)
    return found[2] if found else ""


def loop(run_dir: Path, state: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    """``result`` with the current inner action's loop receipt, the loop run through the real runtime.

    done ends the loop satisfied; send-back stops it blocked; blocked needs no receipt (the loop never started).
    Outside an inner stage the result is returned unchanged.
    """
    if loops.cursor(state) is None or result.get("outcome") == "blocked":
        return dict(result)
    outcome = "done" if result.get("outcome") == "done" else "blocked"
    receipt = loop_support.finish_loop(Path(run_dir), outcome=outcome)
    return loop_support.with_receipt(result, receipt)


def prepare(run_dir: Path, state: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    """``fill`` then ``loop``: a result the current inner stage's gates accept (the state must be saved)."""
    found = loops.cursor(state)
    if found is None:
        return dict(result)
    return loop(run_dir, state, fill(state, found[0], result, run_dir))


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


class RunDriver(unittest.TestCase):
    """A Git checkout with one tracked file and a run inside it, walked through the real ``complete`` gates.

    ``implement`` edits ``a.py`` and adds ``new_mod.py`` (the step plan's paths) and an ignored file; every inner
    stage's loop is run through the real runtime unless the test runs it itself (``drive_to`` stops at the stage).
    """

    PATHS = ["a.py", "new_mod.py"]

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="shiploop-inner-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.repo = self.base / "repo"
        self.run_dir = self.repo / "runs" / "r1"   # inside the checkout: must stay out of the inventory
        self.run_dir.mkdir(parents=True)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "inner@example.invalid")
        git(self.repo, "config", "user.name", "Inner Fixture")
        (self.repo / ".gitignore").write_text("ignored.txt\nruns/\n")
        (self.repo / "a.py").write_text("x = 1\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")

    def start(self, improve_skill: str = str(IMPROVE_CARD)) -> None:
        nav.save(self.run_dir, nav.new_state(str(self.repo), "Inner fixture.", improve_skill=improve_skill,
                                             lint_option="off"))

    def state(self) -> dict:
        return store.read_record(self.run_dir / "state.md")

    def action(self) -> str:
        return nav.current_action(self.state())["id"]

    def packet(self) -> str:
        return nav.render(CORE, self.run_dir, self.state())

    def complete(self, result: Mapping[str, Any], *, prepare_inner: bool = True) -> str:
        """Submit ``result`` through ``complete``; ``prepare_inner`` fills and loops an inner stage's result first."""
        state = self.state()
        action = nav.current_action(state)["id"]
        stage = nav.current_stage(state)
        result = dict(result)
        if stage == "plan" and result.get("outcome") == "done":
            result.setdefault("assumptions", [])
            queue = result.get("work_items", state["work_items"])
            result.setdefault("concerns", no_concerns_map(
                str(row.get("id")) for row in queue if isinstance(row, Mapping)))
        if stage == "intake":
            result = fixture_intake(state, result)          # IN1
        if stage == "spec" and result.get("outcome") == "done":
            result = {**fixture_primary(state), **result}   # run-5 batch F6
        if stage == "test-strategy" and result.get("outcome") == "done":
            for key, value in fixture_test_layers().items():   # run-5 batch F1, F3
                result.setdefault(key, value)
        if stage == "step-plan" and result.get("outcome") == "done":
            result.setdefault("paths", list(self.PATHS))
        if stage in assumptions.OPEN_ITEM_STAGES and result.get("outcome") == "done":
            result.setdefault("assumptions", [])
        if stage == "release-verify" and result.get("outcome") == "done":
            result.setdefault("lessons", dict(LESSONS))
        if prepare_inner:
            result = prepare(self.run_dir, state, result)
        if stage in knowledge_support.knowledge.CLOSES:
            knowledge_support.write(state)
        path = self.run_dir / "inbox" / (action + ".md")
        path.parent.mkdir(exist_ok=True)
        path.write_text(store.dumps(result, "result"))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            nav.dispatch(CORE, self.run_dir, state,
                         types.SimpleNamespace(command="complete", action=action, result=str(path)))
        return buffer.getvalue()

    def finish_improve(self) -> None:
        state = self.state()
        action = state["active_improve"]["action_id"]
        updated = nav.finish_improve(state, action, {"summary": "Synthetic Improve.",
                                                     "review_refs": ["synthetic://r"],
                                                     "check_refs": ["synthetic://c"]})
        updated, writes, payload = nav._transition(CORE, self.run_dir, state, updated)
        nav.save(self.run_dir, updated, writes)
        nav._lint_finish(self.run_dir, payload)

    def drive_to(self, stage: str, *, improve_stage: Optional[str] = None) -> dict:
        """Advance with synthetic results; an Improve child at ``improve_stage`` is left pending."""
        for _ in range(200):
            state = self.state()
            child = state.get("active_improve")
            if child is not None:
                if child["stage"] == improve_stage:
                    return state
                self.finish_improve()
                continue
            current = nav.current_stage(state)
            if current == stage and improve_stage is None:
                return state
            if current == "implement":
                (self.repo / "a.py").write_text("x = 2\n")
                (self.repo / "new_mod.py").write_text("def entry(value):\n    return value\n")
                (self.repo / "ignored.txt").write_text("not product\n")
            self.complete(DONE)
        raise AssertionError("did not reach " + stage)


__all__ = ("CORE", "DONE", "IMPROVE_CARD", "KNOWLEDGE_NONE", "LESSONS", "test_cases_for", "RunDriver", "SKILL_NONE", "expectations_for", "fill", "git", "loop",
           "fixture_intake", "fixture_primary", "no_concerns_map", "prepare")
