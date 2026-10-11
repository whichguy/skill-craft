"""Synthetic inner-stage results that meet the 8-stage inner loop's script gates, for suites that drive the CLI.

The quality, lint and test-loop suites walk a run through ``complete`` with synthetic results.  Since 2026-10-10 every
inner stage's ``complete`` checks the stage's Until Loop receipt and the stage's own gates (step-plan expectations and
step skills, test-spec ids, carry-forward's skill decision).  ``fill`` adds the fields a correct model would write and
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
from typing import Any, Mapping, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/shiploop/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
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


def _focused_ids(result: Mapping[str, Any]) -> list[str]:
    return [ident for row in result.get("test_commands") or () if isinstance(row, Mapping)
            and row.get("suite") == "focused" for ident in row.get("ids") or ()]


def write_test_spec(state: Mapping[str, Any], ids: list[str]) -> Path:
    """The run's test spec with one ``### <ID>`` case per focused id (appended when the file exists)."""
    path = Path(str(state["repo"])) / knowledge.feature_dir(state) / "test-spec.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = path.read_text(encoding="utf-8") if path.is_file() else "# Test spec\n\n"
    for ident in ids:
        if "### " + ident + "\n" not in text:
            text += "### " + ident + "\n\nSynthetic case.\n\n"
    path.write_text(text, encoding="utf-8")
    return path


def fill(state: Mapping[str, Any], stage: str, result: Mapping[str, Any],
         run_dir: Optional[Path] = None) -> dict[str, Any]:
    """``result`` with the fields a done result at ``stage`` needs; the caller's own fields win."""
    result = dict(result)
    if result.get("outcome") != "done":
        return result
    repo = Path(str(state["repo"]))
    if stage == "step-plan":
        if "test_commands" not in result:
            result.update(test_commands=[], test_commands_na="Synthetic fixture; no test commands.")
        if "paths" not in result:
            result["paths"] = ["src/**"]
        if result.get("test_commands") and "criteria" not in result:
            result["criteria"] = [{"id": "C1", "text": "Synthetic criterion."}]
        if result.get("test_commands") and not any(isinstance(row, Mapping) and row.get("suite") == "check"
                                                   for row in result["test_commands"]):
            result.setdefault("check_na", "Synthetic fixture: these files have no lint, type or build command.")
        if "steps" not in result:
            step: dict[str, Any] = {"id": "S1", "task": "Make the planned change.", "paths": list(result["paths"])}
            if result.get("criteria"):
                step["criteria"] = [row["id"] for row in result["criteria"]]
            result["steps"] = [step]
        result["steps"] = [dict(step, skills=step.get("skills", [])) if isinstance(step, Mapping) else step
                           for step in result["steps"]]
        if "expectations" not in result:
            result["expectations"] = expectations_for(repo, result["steps"], run_dir, _current_item(state))
    elif stage == "test-spec":
        _action, plan = test_loop._step_plan(state, _current_item(state))
        write_test_spec(state, _focused_ids(plan))
    elif stage == "carry-forward":
        result.setdefault("skill", dict(SKILL_NONE))
    return result


def _current_item(state: Mapping[str, Any]) -> str:
    found = loops.cursor(state)
    return found[2] if found else ""


def loop(run_dir: Path, state: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    """``result`` with the current inner action's loop receipt, the loop run through the real runtime.

    done ends the loop satisfied; revise stops it blocked; blocked needs no receipt (the loop never started).
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
        if stage == "step-plan" and result.get("outcome") == "done":
            result.setdefault("paths", list(self.PATHS))
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


__all__ = ("CORE", "DONE", "IMPROVE_CARD", "RunDriver", "SKILL_NONE", "expectations_for", "fill", "git", "loop",
           "prepare", "write_test_spec")
