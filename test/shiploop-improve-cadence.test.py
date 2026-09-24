#!/usr/bin/env python3
"""Pin the plan-and-end Improve cadence: Improve after plan and after the last work item."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills/shiploop"
CLI = PACKAGE / "scripts/shiploop"
sys.path.insert(0, str(PACKAGE / "scripts"))
import shiploop_navigator as nav  # noqa: E402
import shiploop_standalone_improve as standalone  # noqa: E402
import shiploop_store as store  # noqa: E402

DONE = {"outcome": "done", "summary": "Synthetic declaration; no work executed."}


def receipt(stage):
    return {"summary": "Synthetic Improve completion for " + stage + ".",
            "review_refs": ["synthetic://review/" + stage], "check_refs": ["synthetic://check/" + stage]}


def walk(state, *, plan_items=None, end_final=None, limit=200):
    """Drive the pure navigator to done; return the stages that started an Improve child."""
    reviewed = []
    for _ in range(limit):
        if state["status"] == "done":
            return state, reviewed
        stage, action = nav.current_stage(state), nav.current_action(state)["id"]
        result = dict(DONE, work_items=plan_items) if stage == "plan" and plan_items else DONE
        state = nav.apply(state, action, result)
        if state["active_improve"] is not None:
            reviewed.append((stage, nav._current_work_item(state)))
            final = end_final.pop(0) if stage == "carry-forward" and end_final else None
            state = nav.finish_improve(state, action, receipt(stage), final)
    raise AssertionError("walk did not finish")


class PlanAndEndNavigatorTests(unittest.TestCase):
    def new(self, cadence):
        return nav.new_state("/simulation-only/repo", "Cadence fixture.", protocol_version=3,
                             improve_skill="", improve_cadence=cadence)

    def test_only_plan_and_last_carry_forward_start_improve(self):
        items = [{"id": "W1", "title": "First"}, {"id": "W2", "title": "Second"}]
        state, reviewed = walk(self.new("plan-and-end"), plan_items=items)
        self.assertEqual(reviewed, [("plan", None), ("carry-forward", "W2")])
        self.assertEqual(state["status"], "done")
        self.assertEqual(set(state["improve_results"]),
                         {entry["action"] for entry in state["history"]
                          if entry["stage"] == "plan" or
                          (entry["stage"] == "carry-forward" and entry["workitem"] == "W2")})

    def test_end_review_that_adds_work_moves_to_the_new_last_item(self):
        added = dict(DONE, work_items=[{"id": "W2", "title": "Found by the end review"}])
        _, reviewed = walk(self.new("plan-and-end"), end_final=[added])
        self.assertEqual(reviewed, [("plan", None), ("carry-forward", "W1"), ("carry-forward", "W2")])

    def test_saved_run_without_the_key_keeps_every_stage(self):
        legacy = self.new(None)
        self.assertNotIn("improve_cadence", legacy)
        self.assertEqual(nav.improve_cadence(legacy), "every-stage")
        _, reviewed = walk(legacy)
        self.assertEqual(len(reviewed), 34)

    def test_plan_and_end_state_still_requires_the_plan_review(self):
        state, _ = walk(self.new("plan-and-end"))
        plan = next(e["action"] for e in state["history"] if e["stage"] == "plan")
        broken = dict(state, improve_results={k: v for k, v in state["improve_results"].items() if k != plan})
        with self.assertRaisesRegex(nav.NavigatorError, "every plan result"):
            nav.validate(broken)

    def test_producer_packets_state_the_cadence(self):
        state = self.new("plan-and-end")
        packet = nav.render(__import__("types").SimpleNamespace(
            PACKAGE_ROOT=PACKAGE, REF_DIR=PACKAGE / "references"), Path("/simulation-only/run"), state)
        self.assertIn("Improve cadence: plan-and-end. This result advances directly", packet)
        self.assertNotIn("every producer attempt result is followed by a separate", packet)


class ImproveCadenceCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-cadence-cli-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        (self.base / "product").mkdir()
        self.run = self.base / "run"
        self.env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_CONFIG_GLOBAL": os.devnull}

    def init(self, *args):
        return subprocess.run([sys.executable, "-B", str(CLI), "init", "--repo", str(self.base / "product"),
                               "--run-dir", str(self.run), "--prompt", "Cadence CLI fixture.", *args],
                              cwd=self.base, text=True, capture_output=True, timeout=60, env=self.env)

    def test_new_runs_record_plan_and_end_and_retry_cannot_change_it(self):
        self.assertEqual(self.init().returncode, 0)
        self.assertEqual(store.read_record(self.run / "state.md")["improve_cadence"], "plan-and-end")
        retry = self.init("--improve-cadence", "every-stage")
        self.assertNotEqual(retry.returncode, 0)
        self.assertIn("fixed at init", retry.stderr)


class ReceiptCountTests(unittest.TestCase):
    def test_three_review_refs_are_refused_with_the_fix(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp).resolve()
            refs = []
            for name in ("material", "one", "two"):
                path = workspace / (name + ".md")
                path.write_text(name)
                refs.append(str(path))
            with self.assertRaisesRegex(standalone.StandaloneImproveError,
                                        "got 3; list only the two trivial-streak reviews"):
                standalone._receipt({"summary": "s", "review_refs": refs, "check_refs": [refs[0]]},
                                    workspace, "receipt")


if __name__ == "__main__":
    unittest.main()
