#!/usr/bin/env python3
"""Hermetic tests for ShipLoop's experiment-driven planning loop, intake experiment handoff,
and vertical end-to-end-first slicing with rolling-wave concerns.

Covers Sequences A, B, and C through the real ShipLoop CLI and bundled Until Loop runtime:
- Sequence A: `plan` runs inside its own script-written Until Loop (multi-iteration isolated
  experiments under `RUN/experiments/`, zero-experiment iteration-1 fast path, `Plan Improve`
  preserved under `--planning-review stage`, `--planning-review none` advancing to `prepare`,
  and cached `shiploop check` answers rechecking experiment evidence existence at `complete`).
- Sequence B: `intake` questions with `route: "experiment"` are quoted in `research` and
  `plan` packets, strictly enforced at `plan`'s gate, and linked via optional `"question"` and
  probed `"effect"` fields on `plan` assumptions.
- Sequence C: optional work-item `slice` (`spine | enrich | prerequisite | corrective`),
  rolling-wave `"deferred"` concerns allowed only after `W1`, vertical-first `plan`/`step-plan`
  prompts, and `reflect-and-revise` progressive enrichment into `W2`.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills/shiploop"
CLI = PACKAGE / "scripts/shiploop"
CARD = ROOT / "skills/improve/SKILL.md"
sys.path.insert(0, str(PACKAGE / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import shiploop_assumptions as assumptions  # noqa: E402
import shiploop_concerns as concerns  # noqa: E402
import shiploop_inner_fixture as fx  # noqa: E402
import shiploop_loop_support as loop_support  # noqa: E402
import shiploop_loops as loops  # noqa: E402
import shiploop_narrative as narrative  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_progress_data as progress_data  # noqa: E402
import shiploop_progress_render as progress_render  # noqa: E402
import shiploop_store as store  # noqa: E402


def _git(repo: Path, env: dict[str, str], *argv: str) -> str:
    done = subprocess.run(["git", *argv], cwd=repo, env=env, capture_output=True, text=True, check=True)
    return done.stdout


class PlanningLoopCliBase(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory(prefix="shiploop-planning-loop-")
        self.addCleanup(self._temp.cleanup)
        self.base = Path(self._temp.name).resolve()
        self.env = {**os.environ, "SHIPLOOP_PROGRESS": "off"}

    def init_repo(self, name: str = "repo") -> Path:
        repo = self.base / name
        repo.mkdir()
        (repo / "app.py").write_text("def greet():\n    return 'hi'\n", encoding="utf-8")
        _git(repo, self.env, "init", "-q")
        _git(repo, self.env, "add", ".")
        _git(repo, self.env, "-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit", "-qm", "init")
        return repo

    def cli(self, *argv: object, status: int = 0) -> subprocess.CompletedProcess[str]:
        done = subprocess.run([sys.executable, "-B", str(CLI), *map(str, argv)],
                              cwd=self.base, env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, status, done.stdout + done.stderr)
        return done

    @staticmethod
    def saved(run_dir: Path) -> dict:
        return store.read_record(run_dir / "state.md")

    def init_run(self, repo: Path, name: str = "run", *, planning_review: str = "stage",
                 prompt: str = "Build an API and CLI with a thin working spine first, then enrich.") -> Path:
        run_dir = self.base / name
        extra = ("--improve-skill", CARD) if planning_review == "none" else ()
        self.cli("init", "--repo", repo, "--run-dir", run_dir, f"--prompt={prompt}",
                 "--planning-review", planning_review, "--lint", "off", *extra)
        return run_dir

    def write_result(self, run_dir: Path, result: dict) -> tuple[str, Path]:
        state = self.saved(run_dir)
        action = nav.current_action(state)["id"]
        path = run_dir / "inbox" / (action + ".md")
        path.parent.mkdir(parents=True, exist_ok=True)
        store.write_record(path, result)
        return action, path

    def complete_stage(self, run_dir: Path, result: dict, *, status: int = 0) -> subprocess.CompletedProcess[str]:
        action, path = self.write_result(run_dir, result)
        return self.cli("complete", "--run-dir", run_dir, "--action", action, "--result", path, status=status)

    def advance_to_plan(self, repo: Path, run_dir: Path, *, intake_questions: list[dict] | None = None) -> None:
        """Advance intake -> discovery -> research -> spec -> test-strategy cleanly (pure finish_improve on stage mode)."""
        state = self.saved(run_dir)
        # 1. intake
        intake_res = fx.fixture_intake(state, {"outcome": "done", "summary": "Mapped request."})
        if intake_questions is not None:
            intake_res["question_categories"] = [
                {"id": f"K{n}", "applies": "yes" if n == 1 else "no",
                 **({} if n == 1 else {"reason": "n/a"})}
                for n in range(1, 13)
            ]
            intake_res["questions"] = intake_questions
        self.complete_stage(run_dir, intake_res)
        # 2. discovery
        (repo / "docs" / "shiploop").mkdir(parents=True, exist_ok=True)
        (repo / "docs" / "shiploop" / "environment.md").write_text("# Environment\n\n## Commands\n- python3 -m unittest\n", encoding="utf-8")
        self.complete_stage(run_dir, {"outcome": "done", "summary": "Discovered baseline."})
        # 3. research
        self.complete_stage(run_dir, {"outcome": "done", "summary": "Researched unknowns."})
        # 4. spec
        spec_path = repo / "docs" / "shiploop" / "spec.md"
        spec_path.write_text("# Spec\n\n## R-1\nThin vertical end-to-end spine works.\n\n## R-2\nRich filtering and export.\n", encoding="utf-8")
        self.complete_stage(run_dir, {
            "outcome": "done", "summary": "Defined R-1 and R-2.",
            "primary": ["R-1", "R-2"],
            "defaults": [],
            "evidence_refs": [str(spec_path)],
        })
        state = self.saved(run_dir)
        if state.get("active_improve") is not None:
            state = nav.finish_improve(state, state["active_improve"]["action_id"], {"summary": "Synthetic review."})
            nav.save(run_dir, state)
        # 5. test-strategy
        (repo / "docs" / "shiploop" / "architecture.md").write_text(
            "# Architecture\n\n## Decisions\n\n### AD-1\nUse Python stdlib.\n", encoding="utf-8")
        self.complete_stage(run_dir, {
            "outcome": "done", "summary": "Planned test layers.",
            **fx.fixture_test_layers(),
            "evidence_refs": [str(repo / "docs" / "shiploop" / "environment.md")],
        })
        state = self.saved(run_dir)
        if state.get("active_improve") is not None:
            before = state
            after = nav.finish_improve(state, state["active_improve"]["action_id"], {"summary": "Synthetic review."})
            nav.accept_effects(None, run_dir, before, after, action_id=before["active_improve"]["action_id"])
        self.assertEqual(self.saved(run_dir)["stage"], "plan")


class PlanUntilLoopTests(PlanningLoopCliBase):
    """Sequence A: script-written Until Loop at `plan` driving isolated experiments."""

    def test_plan_contract_determinism_and_isolated_sandbox_scope(self) -> None:
        repo = self.init_repo()
        run_dir = self.init_run(repo)
        self.advance_to_plan(repo, run_dir)
        state = self.saved(run_dir)
        action = state["action"]["id"]
        self.assertEqual(loops.cursor(state), ("plan", action, None))
        contract_file = run_dir / loops.contract_path(action)
        self.assertTrue(contract_file.is_file(), "plan entry must write its loop contract")
        rebuilt = loops.contract(run_dir, state, action)
        self.assertEqual(json.loads(contract_file.read_text(encoding="utf-8")), rebuilt)
        self.assertIn(str(run_dir / "experiments"), rebuilt["work"])
        self.assertIn(str(run_dir / "experiments"), rebuilt["context"]["scope"])
        self.assertIn("Change no product file", rebuilt["context"]["scope"])
        self.assertIn("no iteration limit", rebuilt["repeat_condition"])

    def test_plan_multi_iteration_experiment_loop_parks_at_plan_improve(self) -> None:
        repo = self.init_repo()
        run_dir = self.init_run(repo, planning_review="stage")
        self.advance_to_plan(repo, run_dir)
        state = self.saved(run_dir)
        action = state["action"]["id"]

        # Without running the loop, complete is refused.
        refused = self.complete_stage(run_dir, {
            "outcome": "done", "summary": "Provisional plan.",
            "work_items": [{"id": "W1", "title": "Spine", "slice": "spine", "follows": ["R-1", "R-2"], "context": "End to end."}],
            "concerns": fx.no_concerns_map(["W1"]),
            "assumptions": [],
        }, status=2)
        self.assertIn("the plan loop has not run", refused.stdout + refused.stderr)

        # Start the real bundled Until Loop runtime from ShipLoop's contract.
        contract_file = run_dir / loops.contract_path(action)
        receipt = loops.receipt_path(run_dir, action)
        bound = loops.runtime(state)
        started = subprocess.run(
            [sys.executable, bound["runtime_cli"], "start", "--receipt", str(receipt), "--directory", str(receipt.parent)],
            input=contract_file.read_text(encoding="utf-8"), text=True, capture_output=True, check=True,
        )
        packet = json.loads(started.stdout)
        self.assertEqual(packet["status"], "active")

        # Iteration 1: isolated experiment 1 in RUN/experiments/exp-1/ reveals a material change -> continue loop.
        exp1 = run_dir / "experiments" / "exp-1" / "output.txt"
        exp1.parent.mkdir(parents=True, exist_ok=True)
        exp1.write_text("experiment 1 observed: streaming required\n", encoding="utf-8")
        step1 = subprocess.run(
            list(packet["done_argv"]),
            input=json.dumps({
                "classification": "non-trivial", "exit_assessment": "unsatisfied",
                "continuation_assessment": "allowed",
                "evidence": f"Ran exp-1 saved at {exp1}; one more probe needed.",
                "handoff": "Run exp-2 to verify chunk boundary behaviour.",
            }),
            text=True, capture_output=True, check=True,
        )
        packet2 = json.loads(step1.stdout)
        self.assertEqual(packet2["status"], "active")
        self.assertEqual(packet2["progress"]["action_number"], 2)

        # Iteration 2: isolated experiment 2 confirms refined plan; `shiploop check` says yes; close loop satisfied.
        exp2 = run_dir / "experiments" / "exp-2" / "output.txt"
        exp2.parent.mkdir(parents=True, exist_ok=True)
        exp2.write_text("experiment 2 observed: chunk size 64KB works\n", encoding="utf-8")
        plan_result = {
            "outcome": "done",
            "headline": "Vertical plan clarified by two isolated experiments.",
            "summary": "Clarified architecture from exp-1 and exp-2.",
            "evidence_refs": [str(receipt), str(exp1), str(exp2)],
            "work_items": [
                {"id": "W1", "title": "Thin vertical spine", "slice": "spine", "follows": ["R-1", "AD-1"], "context": "E2E smoke check inside W1."},
                {"id": "W2", "title": "Filtering and export enrichments", "slice": "enrich", "follows": ["R-2"], "context": "Enrich W1 spine."},
            ],
            "concerns": {"W1": fx.no_concerns_map(["W1"])["W1"], "W2": "deferred"},
            "assumptions": [
                {"id": "A1", "assumption": "Streaming chunks work across pipe", "disposition": "probed",
                 "check": "python3 -c 'print(64)'", "evidence": [str(exp1), str(exp2)],
                 "effect": "Switched W1 transport to streaming 64KB chunks."},
            ],
        }
        _, draft_path = self.write_result(run_dir, plan_result)
        checked = self.cli("check", "--run-dir", run_dir, "--action", action, "--result", draft_path)
        self.assertIn("the check says yes for plan", checked.stdout)

        step2 = subprocess.run(
            list(packet2["done_argv"]),
            input=json.dumps({
                "classification": "non-trivial", "exit_assessment": "satisfied",
                "continuation_assessment": "allowed",
                "evidence": f"Both exp-1 ({exp1}) and exp-2 ({exp2}) folded into plan; shiploop check said yes.",
                "handoff": "Plan ready for submission and Plan Improve review.",
            }),
            text=True, capture_output=True, check=True,
        )
        terminal = json.loads(step2.stdout)
        self.assertEqual(terminal["status"], "complete")
        self.assertEqual(terminal["progress"]["action_number"], 2)

        # Submit complete -> accepted and parked at Plan Improve (Improve sequence preserved!).
        self.cli("complete", "--run-dir", run_dir, "--action", action, "--result", draft_path)
        after = self.saved(run_dir)
        self.assertIsNotNone(after["active_improve"])
        self.assertEqual(after["active_improve"]["stage"], "plan")
        self.assertEqual(after["active_improve"]["seed_result"]["assumptions"][0]["effect"],
                         "Switched W1 transport to streaming 64KB chunks.")
        # Product checkout untouched by isolated experiments.
        self.assertEqual(_git(repo, self.env, "status", "--porcelain", "--", "app.py").strip(), "")

    def test_plan_zero_experiment_fast_path_under_planning_review_none(self) -> None:
        repo = self.init_repo()
        run_dir = self.init_run(repo, planning_review="none")
        self.advance_to_plan(repo, run_dir)
        # Packet includes the Until Loop and Experiment sandbox even under --planning-review none.
        pkt = self.cli("next", "--run-dir", run_dir).stdout
        self.assertIn("Until Loop (no iteration limit", pkt)
        self.assertIn("Experiment sandbox: RUN/experiments/<exp-id>/", pkt)

        receipt = loop_support.finish_loop(run_dir, note="zero experiments needed")
        self.assertEqual(json.loads(receipt.read_text(encoding="utf-8"))["progress"]["action_number"], 1)
        self.complete_stage(run_dir, {
            "outcome": "done",
            "headline": "Single-item plan needing zero experiments.",
            "summary": "Evidence already sufficient; no experiments needed.",
            "evidence_refs": [str(receipt)],
            "work_items": [{"id": "W1", "title": "Cohesive change", "follows": ["R-1", "R-2"], "context": "Single slice."}],
            "concerns": fx.no_concerns_map(["W1"]),
            "assumptions": [],
        })
        after = self.saved(run_dir)
        self.assertIsNone(after.get("active_improve"))
        self.assertEqual(after["stage"], "prepare")

    def test_deleted_experiment_output_not_masked_by_cached_check_yes(self) -> None:
        repo = self.init_repo()
        run_dir = self.init_run(repo, planning_review="none")
        self.advance_to_plan(repo, run_dir)
        exp = run_dir / "experiments" / "exp-temp" / "out.txt"
        exp.parent.mkdir(parents=True, exist_ok=True)
        exp.write_text("ok\n", encoding="utf-8")
        receipt = loop_support.finish_loop(run_dir)
        action, draft = self.write_result(run_dir, {
            "outcome": "done", "headline": "Probed.", "summary": "Probed.",
            "evidence_refs": [str(receipt)],
            "work_items": [{"id": "W1", "title": "Work", "follows": ["R-1", "R-2"]}],
            "concerns": fx.no_concerns_map(["W1"]),
            "assumptions": [{"id": "A1", "assumption": "X holds", "disposition": "probed",
                             "check": "echo ok", "evidence": [str(exp)], "effect": "Confirmed X."}],
        })
        self.cli("check", "--run-dir", run_dir, "--action", action, "--result", draft)
        exp.unlink()
        refused = self.cli("complete", "--run-dir", run_dir, "--action", action, "--result", draft, status=2)
        self.assertIn("does not exist", refused.stdout + refused.stderr)


class IntakeExperimentHandoffTests(PlanningLoopCliBase):
    """Sequence B: intake route='experiment' questions carried to research/plan and enforced."""

    def test_intake_experiment_questions_quoted_and_enforced(self) -> None:
        repo = self.init_repo()
        run_dir = self.init_run(repo, planning_review="none")
        questions = [
            {"id": "Q1", "category": "K1", "question": "Does SQLite WAL allow concurrent readers?",
             "changes": "Storage locking architecture", "route": "experiment",
             "default": "Use single connection", "blocks": "plan"},
            {"id": "Q2", "category": "K2", "question": "Which Python version is installed?",
             "changes": "Syntax floor", "route": "research",
             "default": "Python 3.11", "blocks": "spec"},
        ]
        # Advance intake -> discovery -> research and verify research packet quotes Q1 (not Q2).
        state = self.saved(run_dir)
        intake_res = fx.fixture_intake(state, {"outcome": "done", "summary": "Mapped request."})
        intake_res["question_categories"] = [
            {"id": f"K{n}", "applies": "yes" if n <= 2 else "no", **({} if n <= 2 else {"reason": "n/a"})}
            for n in range(1, 13)
        ]
        intake_res["questions"] = questions
        self.complete_stage(run_dir, intake_res)
        (repo / "docs" / "shiploop").mkdir(parents=True, exist_ok=True)
        (repo / "docs" / "shiploop" / "environment.md").write_text("# Environment\n\n## Commands\n- python3 -m unittest\n", encoding="utf-8")
        self.complete_stage(run_dir, {"outcome": "done", "summary": "Discovered baseline."})
        research_pkt = self.cli("next", "--run-dir", run_dir).stdout
        self.assertIn("Q1: Does SQLite WAL allow concurrent readers?", research_pkt)
        self.assertNotIn("Q2: Which Python version", research_pkt)

        # Continue to plan.
        self.complete_stage(run_dir, {"outcome": "done", "summary": "Researched Q2."})
        spec_path = repo / "docs" / "shiploop" / "spec.md"
        spec_path.write_text("# Spec\n\n## R-1\nSpine works.\n", encoding="utf-8")
        self.complete_stage(run_dir, {"outcome": "done", "summary": "Spec.", "primary": ["R-1"],
                                      "defaults": [], "evidence_refs": [str(spec_path)]})
        (repo / "docs" / "shiploop" / "architecture.md").write_text("# Architecture\n\n## Decisions\n", encoding="utf-8")
        self.complete_stage(run_dir, {"outcome": "done", "summary": "Strategy.", **fx.fixture_test_layers(),
                                      "evidence_refs": [str(repo / "docs" / "shiploop" / "environment.md")]})

        plan_pkt = self.cli("next", "--run-dir", run_dir).stdout
        self.assertIn("Q1: Does SQLite WAL allow concurrent readers?", plan_pkt)
        self.assertIn('"question": "<Qid>"', plan_pkt)

        receipt = loop_support.finish_loop(run_dir)
        # Missing Q1 link is refused.
        refused = self.complete_stage(run_dir, {
            "outcome": "done", "headline": "Plan.", "summary": "Plan.",
            "evidence_refs": [str(receipt)],
            "work_items": [{"id": "W1", "title": "Work", "follows": ["R-1"]}],
            "concerns": fx.no_concerns_map(["W1"]),
            "assumptions": [],
        }, status=2)
        self.assertIn("Q1", refused.stdout + refused.stderr)

        # Linking Q1 with saved probe output and effect succeeds.
        probe_out = run_dir / "experiments" / "wal-probe" / "out.txt"
        probe_out.parent.mkdir(parents=True, exist_ok=True)
        probe_out.write_text("WAL concurrent read succeeded\n", encoding="utf-8")
        self.complete_stage(run_dir, {
            "outcome": "done", "headline": "Plan.", "summary": "Plan with WAL verified.",
            "evidence_refs": [str(receipt), str(probe_out)],
            "work_items": [{"id": "W1", "title": "Work", "follows": ["R-1"]}],
            "concerns": fx.no_concerns_map(["W1"]),
            "assumptions": [{"id": "A1", "question": "Q1", "assumption": "SQLite WAL supports concurrent readers",
                             "disposition": "probed", "check": "python3 wal_probe.py",
                             "evidence": [str(probe_out)], "effect": "Enabled WAL mode in W1 storage."}],
        })
        self.assertEqual(self.saved(run_dir)["stage"], "prepare")

    def test_assumption_field_guards(self) -> None:
        with self.assertRaisesRegex(assumptions.AssumptionError, "question is only for a plan assumption"):
            assumptions.canonical([{"id": "A1", "question": "Q1", "assumption": "x", "disposition": "open",
                                    "settle": "s", "reason": "r", "due_stage": "system-test"}], "test-spec")
        with self.assertRaisesRegex(assumptions.AssumptionError, "intake question ID"):
            assumptions.canonical([{"id": "A1", "question": "bad", "assumption": "x", "disposition": "evidenced",
                                    "evidence": ["https://example.test/doc"]}], "plan")
        with self.assertRaisesRegex(assumptions.AssumptionError, "effect is only for a probed assumption at plan"):
            assumptions.canonical([{"id": "A1", "assumption": "x", "disposition": "evidenced",
                                    "evidence": ["https://example.test/doc"], "effect": "nope"}], "plan")
        rows = assumptions.canonical([{
            "id": "A1", "question": "Q1", "assumption": "x", "disposition": "probed",
            "check": "cmd", "evidence": ["https://example.test/out"], "effect": "Confirmed.",
        }], "plan")
        self.assertEqual((rows[0]["question"], rows[0]["effect"]), ("Q1", "Confirmed."))


class VerticalSlicingAndRollingWaveTests(unittest.TestCase):
    """Sequence C: slice metadata, rolling-wave deferred concerns, vertical step-plan & reflect-and-revise."""

    def test_work_item_slice_normalisation(self) -> None:
        rows = nav._normalise_work_items([
            {"id": "W1", "title": "Spine", "slice": "spine", "follows": ["R-1"]},
            {"id": "W2", "title": "Enrich", "slice": "enrich", "follows": ["R-2"]},
            {"id": "W3", "title": "No slice still works"},
        ], allow_empty=False)
        self.assertEqual([r.get("slice") for r in rows], ["spine", "enrich", None])
        with self.assertRaisesRegex(nav.NavigatorError, "slice must be one of"):
            nav._normalise_work_items([{"id": "W1", "title": "Bad", "slice": "horizontal"}], allow_empty=False)

    def test_rolling_wave_concerns_forbid_deferred_on_first_item_and_support_later_items(self) -> None:
        w1_rows = fx.no_concerns_map(["W1"])["W1"]
        # Single-item deferred -> refused.
        with self.assertRaisesRegex(concerns.ConcernError, "cannot defer concerns"):
            concerns.check_plan(concerns.canonical_plan({"W1": "deferred"}), ["W1"])
        # Multi-item with W1 deferred -> refused.
        with self.assertRaisesRegex(concerns.ConcernError, "cannot defer concerns"):
            concerns.check_plan(concerns.canonical_plan({"W1": "deferred", "W2": w1_rows}), ["W1", "W2"])
        # Multi-item with W1 mapped and W2 deferred -> accepted.
        plan_map = concerns.canonical_plan({"W1": w1_rows, "W2": "deferred"})
        concerns.check_plan(plan_map, ["W1", "W2"])
        self.assertEqual(concerns.owned_rows(plan_map, "W2"), [])
        self.assertEqual(concerns.handoff_rows(plan_map, "W2", "test"), [])
        lines = concerns.packet_lines(plan_map, "W2")
        self.assertEqual(len(lines), 1)
        self.assertIn("deferred at plan (rolling-wave enrichment)", lines[0])
        # Step-plan for W2 succeeds with no mapped concerns.
        concerns.check_step_plan([], concerns.owned_rows(plan_map, "W2"), ["S1"], "W2")

    def test_vertical_slice_display_and_reflect_and_revise_enrichment_queue(self) -> None:
        with tempfile.TemporaryDirectory(prefix="shiploop-vertical-") as temp:
            repo = Path(temp).resolve() / "repo"
            repo.mkdir()
            run_dir = Path(temp).resolve() / "run"
            run_dir.mkdir()
            state = nav.new_state(str(repo), "Build full-stack app: spine first, then enrich.",
                                  improve_skill=str(CARD), planning_review="none")
            done = {"outcome": "done", "summary": "Synthetic."}
            # Walk to W1 step-plan with vertical W1 spine + W2 deferred enrich.
            while nav.current_stage(state) != "step-plan":
                stage, action = nav.current_stage(state), nav.current_action(state)["id"]
                extra = {}
                if stage == "plan":
                    extra = {
                        "work_items": [
                            {"id": "W1", "title": "Thin vertical spine", "slice": "spine", "context": "E2E smoke check."},
                            {"id": "W2", "title": "Enrich filters", "slice": "enrich", "context": "Deferred detail."},
                        ],
                        "concerns": {"W1": fx.no_concerns_map(["W1"])["W1"], "W2": "deferred"},
                    }
                state = nav.apply(state, action, {**done, **extra})
            sp_w1 = nav.render(None, run_dir, state)
            self.assertIn("Work item slice: spine", sp_w1)
            self.assertIn("Cut a larger item vertically (end-to-end slice first", sp_w1)
            self.assertNotIn("module or layer boundary", sp_w1)

            # Walk W1 to reflect-and-revise and check progressive enrichment wording + queue update to W2.
            while nav.current_stage(state) != "reflect-and-revise":
                stage, action = nav.current_stage(state), nav.current_action(state)["id"]
                extra = {"steps": [{"id": "S1", "task": "Build spine", "proof": "true"}]} if stage == "step-plan" else {}
                state = nav.apply(state, action, {**done, **extra})
                if state.get("active_improve") is not None:
                    state = nav.finish_improve(state, action, {"summary": "Synthetic review."})
            rr_pkt = nav.render(None, run_dir, state)
            self.assertIn("progressive enrichment: when pending enrichment items (`W2+`) remain", rr_pkt)

            # Replace future queue with sharpened W2 context; non-final reflect-and-revise queue edit starts mid-run Improve.
            rr_action = nav.current_action(state)["id"]
            state = nav.apply(state, rr_action, {
                **done,
                "work_items": [{"id": "W2", "title": "Enrich filters", "slice": "enrich",
                                "context": "Carry W1 E2E smoke as regression baseline."}],
            })
            self.assertIsNotNone(state.get("active_improve"))
            state = nav.finish_improve(state, rr_action, {"summary": "Synthetic mid-run reflection review."})
            self.assertEqual((nav.current_stage(state), nav._current_work_item(state)), ("step-plan", "W2"))
            sp_w2 = nav.render(None, run_dir, state)
            self.assertIn("Work item slice: enrich", sp_w2)
            self.assertIn("deferred at plan (rolling-wave enrichment)", sp_w2)
            self.assertIn("Carry W1 E2E smoke as regression baseline.", sp_w2)


class PlanningLoopStatusAndObservabilityTests(PlanningLoopCliBase):
    """Iterative plan-loop cadence, automatic draft snapshots, live progress/status/story/report, and redaction."""

    def test_snapshots_live_status_progress_story_and_report_across_iterations(self) -> None:
        repo = self.init_repo()
        run_dir = self.init_run(repo, planning_review="none")
        questions = [{
            "id": "Q1", "category": "K1", "question": "Does v1 cap batches at 25?",
            "changes": "Batch size or v2 fallback", "route": "experiment",
            "default": "Single batch", "blocks": "plan",
        }]
        state = self.saved(run_dir)
        intake_res = fx.fixture_intake(state, {"outcome": "done", "summary": "Mapped request."})
        intake_res["question_categories"] = [
            {"id": "K1", "applies": "yes"},
            *[{"id": f"K{n}", "applies": "no", "reason": "n/a"} for n in range(2, 13)],
        ]
        intake_res["questions"] = questions
        self.complete_stage(run_dir, intake_res)
        (repo / "docs" / "shiploop").mkdir(parents=True, exist_ok=True)
        (repo / "docs" / "shiploop" / "environment.md").write_text("# Env\n\n## Commands\n- true\n", encoding="utf-8")
        self.complete_stage(run_dir, {"outcome": "done", "summary": "Discovered repo."})
        self.complete_stage(run_dir, {"outcome": "done", "summary": "Researched."})
        spec_path = repo / "docs" / "shiploop" / "spec.md"
        spec_path.write_text("# Spec\n\n## R-1\nExport records.\n", encoding="utf-8")
        self.complete_stage(run_dir, {"outcome": "done", "summary": "Spec.", "primary": ["R-1"],
                                      "defaults": [], "evidence_refs": [str(spec_path)]})
        (repo / "docs" / "shiploop" / "architecture.md").write_text("# Arch\n\n## Decisions\n", encoding="utf-8")
        self.complete_stage(run_dir, {"outcome": "done", "summary": "Strategy.", **fx.fixture_test_layers(),
                                      "evidence_refs": [str(repo / "docs" / "shiploop" / "environment.md")]})

        pkt = self.cli("next", "--run-dir", run_dir).stdout
        self.assertIn('exit_assessment: "unsatisfied"', pkt)

        state = self.saved(run_dir)
        action = nav.current_action(state)["id"]
        contract = run_dir / loops.contract_path(action)
        receipt = run_dir / loops.terminal_path(action)
        bound = loops.runtime(state)
        started = subprocess.run(
            [sys.executable, bound["runtime_cli"], "start", "--receipt", str(receipt), "--directory", str(receipt.parent)],
            input=contract.read_text(encoding="utf-8"), text=True, capture_output=True, check=True,
        )
        packet1 = json.loads(started.stdout)

        # Iteration 1: write provisional plan draft + sandbox experiment with api_key secret to test redaction.
        exp_dir = run_dir / "experiments" / "probe-v1"
        exp_dir.mkdir(parents=True, exist_ok=True)
        (exp_dir / "decision.md").write_text(
            "# Probe v1\nv1 failed above 25 records api_key=sk_secret_token_987654\n", encoding="utf-8"
        )
        (exp_dir / "meta.json").write_text(json.dumps({
            "question": "Q1", "hypothesis": "v1 fails >25", "outcome": "confirmed cap=25", "plan_changed": True,
        }), encoding="utf-8")
        action, draft = self.write_result(run_dir, {
            "outcome": "done", "headline": "Provisional plan.", "summary": "Draft 1.",
            "evidence_refs": [str(receipt), str(exp_dir / "decision.md")],
            "work_items": [{"id": "W1", "title": "Spine", "slice": "spine", "follows": ["R-1"]},
                           {"id": "W2", "title": "Enrich", "slice": "enrich", "follows": ["R-1"]}],
            "concerns": {"W1": fx.no_concerns_map(["W1"])["W1"], "W2": "deferred"},
            "assumptions": [{"id": "A1", "question": "Q1", "assumption": "v1 caps at 25",
                             "disposition": "probed", "check": "node probe.js",
                             "evidence": [str(exp_dir / "decision.md")], "effect": "Use 25-record chunks."}],
        })
        self.cli("check", "--run-dir", run_dir, "--action", action, "--result", draft)
        self.assertTrue((run_dir / "experiments" / "plan-iter-1.md").is_file())
        snap1_bytes = (run_dir / "experiments" / "plan-iter-1.md").read_text(encoding="utf-8")

        # Close iteration 1 as unsatisfied using real stdin JSON report so iteration 2 begins.
        iter1_done = subprocess.run(
            list(packet1["done_argv"]),
            input=json.dumps({
                "classification": "non-trivial", "exit_assessment": "unsatisfied",
                "continuation_assessment": "allowed",
                "evidence": f"Ran probe-v1 at {exp_dir}",
                "handoff": "Iteration 1 proved v1 cap=25; checking v2 next.",
            }),
            text=True, capture_output=True, check=True,
        )
        packet2 = json.loads(iter1_done.stdout)
        live_snap = progress_data.build_snapshot(run_dir)
        self.assertEqual(live_snap["planning"]["loop"]["action_number"], 2)
        self.assertEqual(live_snap["planning"]["loop"]["summary"], "Iteration 1 proved v1 cap=25; checking v2 next.")
        self.assertEqual(live_snap["planning"]["experiments"][0]["id"], "probe-v1")
        self.assertNotIn("sk_secret_token_987654", json.dumps(live_snap))
        status_text = self.cli("status", "--run-dir", str(run_dir)).stdout
        self.assertIn("Plan loop: iter 2 (active)", status_text)
        self.assertIn("probe-v1", status_text)
        self.assertNotIn(str(run_dir), status_text)
        live_html = progress_render.render(live_snap)
        self.assertIn("Planning &amp; experiments", live_html)
        self.assertIn("Until Loop iter 2 · active", live_html)
        self.assertIn("probe-v1", live_html)
        self.assertNotIn("sk_secret_token_987654", live_html)
        story_ev = next(e for e in live_snap["story"]["events"] if e.get("kind") == "until")
        self.assertEqual(story_ev.get("iteration"), 2)
        self.assertIn("iter 2 ·", story_ev["summary"])
        narr_md = narrative.markdown(nav.narrative_facts(self.saved(run_dir), None, root=run_dir))
        self.assertIn("Until Loop iter 2", narr_md)
        self.assertIn("1 sandbox", narr_md)

        # Iteration 2: revise plan draft and complete loop cleanly.
        action, draft = self.write_result(run_dir, {
            "outcome": "done", "headline": "Vertical plan after probe.", "summary": "Draft 2 with spine+enrich.",
            "evidence_refs": [str(receipt), str(exp_dir / "decision.md")],
            "work_items": [{"id": "W1", "title": "Spine", "slice": "spine", "follows": ["R-1"]},
                           {"id": "W2", "title": "Enrich", "slice": "enrich", "follows": ["R-1"]}],
            "concerns": {"W1": fx.no_concerns_map(["W1"])["W1"], "W2": "deferred"},
            "assumptions": [{"id": "A1", "question": "Q1", "assumption": "v1 caps at 25",
                             "disposition": "probed", "check": "node probe.js",
                             "evidence": [str(exp_dir / "decision.md")], "effect": "Use 25-record chunks."}],
        })
        subprocess.run(
            list(packet2["done_argv"]),
            input=json.dumps({
                "classification": "trivial", "exit_assessment": "satisfied",
                "continuation_assessment": "allowed",
                "evidence": "All checks passed cleanly.",
                "handoff": "Confirmed plan after iteration 2 check.",
            }),
            text=True, capture_output=True, check=True,
        )
        self.cli("complete", "--run-dir", run_dir, "--action", action, "--result", draft)

        self.assertEqual((run_dir / "experiments" / "plan-iter-1.md").read_text(encoding="utf-8"), snap1_bytes)
        self.assertTrue((run_dir / "experiments" / "plan-iter-2.md").is_file())
        self.assertIn("Draft 2 with spine+enrich.", (run_dir / "experiments" / "plan-iter-2.md").read_text(encoding="utf-8"))

        post_snap = progress_data.build_snapshot(run_dir)
        self.assertTrue(post_snap["plan_accepted"])
        self.assertEqual(post_snap["work_items"][0]["slice"], "spine")
        self.assertEqual(post_snap["work_items"][0]["concerns_mode"], "mapped")
        self.assertEqual(post_snap["work_items"][1]["slice"], "enrich")
        self.assertEqual(post_snap["work_items"][1]["concerns_mode"], "deferred")
        post_html = progress_render.render(post_snap)
        self.assertIn("pill-slice", post_html)
        self.assertIn("rolling-wave · concerns deferred", post_html)
        post_status = self.cli("status", "--run-dir", str(run_dir)).stdout
        self.assertIn("Plan:      2 loop iters · 1 experiment probed · slices spine->enrich", post_status)

        report_html = nav._render_report(self.saved(run_dir), run_dir)
        self.assertIn("<h2>Planning experiments &amp; slicing</h2>", report_html)
        self.assertIn("Plan Until Loop iterations: 2; sandboxes: 1; draft snapshots: 2; probed assumptions: 1.", report_html)
        self.assertIn("Use 25-record chunks.", report_html)


if __name__ == "__main__":
    unittest.main()
