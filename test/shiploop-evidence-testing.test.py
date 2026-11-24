#!/usr/bin/env python3
"""Hermetic tests for evidence-driven test planning, execution, triage, and commit-then-amend fix-forward."""
from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills/shiploop"
sys.path.insert(0, str(PACKAGE / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import shiploop_assumptions as assumptions  # noqa: E402
import shiploop_expectations as expectations  # noqa: E402
import shiploop_inner_fixture as inner  # noqa: E402
import shiploop_item_scope as item_scope  # noqa: E402
import shiploop_knowledge_home as knowledge  # noqa: E402
import shiploop_knowledge_support as knowledge_support  # noqa: E402
import shiploop_lint as lint  # noqa: E402
import shiploop_loop_support as loop_support  # noqa: E402
import shiploop_loops as loops  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_planning_revision as planning_revision  # noqa: E402
import shiploop_prompts as prompts  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_test_loop as test_loop  # noqa: E402


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def _two_step_plan(item: str = "W1", focused_cmd: str = "python3 -B -m unittest -v tests/test_mod.py",
                   reg_cmd: str = "python3 -B -m unittest -v tests/test_reg.py",
                   proof1: str = "python3 -B -c \"import mod; assert mod.fn(1) == 2\"",
                   proof2: str = "python3 -B -c \"import mod; assert mod.fn2(1) == 3\"",
                   follows: list[str] | None = None,
                   extra_targets: list[dict] | None = None) -> dict:
    return {
        "outcome": "done",
        "summary": f"Planned two steps for {item}.",
        "follows": follows if follows is not None else ["R-1"],
        "criteria": [
            {"id": "C1", "text": "fn increments by 1 (R-1). Confirm by: running test_fn1; pass when exit 0.", "confirm": "executed"},
            {"id": "C2", "text": "fn2 increments by 2 (R-1). Confirm by: running test_fn2; pass when exit 0.", "confirm": "executed"},
        ],
        "steps": [
            {"id": "S1", "task": "Implement fn (C1).", "deps": [], "criteria": ["C1"], "paths": ["mod.py"], "proof": proof1, "skills": []},
            {"id": "S2", "task": "Implement fn2 (C2).", "deps": ["S1"], "criteria": ["C2"], "paths": ["mod.py"], "proof": proof2, "skills": []},
        ],
        "paths": ["mod.py", "tests/test_mod.py", "tests/test_reg.py"],
        "expectations": [
            {"id": "E1", "state": "works", "statement": "mod exists", "steps": ["S1"], "paths": ["mod.py"], "check": "test -f mod.py"},
        ],
        "test_commands": [
            {"command": focused_cmd, "suite": "focused", "ids": ["TC-1", "TC-2"], "criteria": ["C1", "C2"]},
            {"command": reg_cmd, "suite": "regression", "ids": ["REG-1"], "criteria": ["C1", "C2"], "minimum": True},
            {"command": "python3 -m py_compile mod.py", "suite": "check"},
        ],
        **({"targets": extra_targets} if extra_targets is not None else {}),
    }


def _two_step_spec(test_cases: list[dict] | None = None) -> dict:
    return {
        "outcome": "done",
        "summary": "Spec cases for C1 and C2.",
        "assumptions": [],
        "test_cases": test_cases or [
            {"id": "TC-1", "criterion": "C1", "requirement": "R-1", "oracle": "fn(1) returns 2",
             "red": "fn(1) returns 1 on base", "green": "fn(1) == 2 passes"},
            {"id": "TC-2", "criterion": "C2", "requirement": "R-1", "oracle": "fn2(1) returns 3",
             "red": "fn2 undefined on base", "green": "fn2(1) == 3 passes"},
        ],
    }


class EvidenceTestingTests(unittest.TestCase):
    def _head(self, run_dir: Path, state: dict) -> str:
        return nav.packet_head(inner.CORE, run_dir, state, nav.packet_path(run_dir, state))

    def _init_repo_run(self) -> tuple[Path, Path, Path]:
        temp = tempfile.TemporaryDirectory(prefix="shiploop-ev-")
        self.addCleanup(temp.cleanup)
        base = Path(temp.name).resolve()
        repo = base / "repo"
        run_dir = repo / "runs" / "r1"
        run_dir.mkdir(parents=True)
        (repo / "tests").mkdir(parents=True)
        _git(repo, "init", "-q")
        _git(repo, "config", "user.email", "ev@example.invalid")
        _git(repo, "config", "user.name", "EV")
        _git(repo, "config", "commit.gpgsign", "false")
        (repo / ".gitignore").write_text("runs/\n__pycache__/\n")
        (repo / "mod.py").write_text("def fn(x):\n    return x\n")
        (repo / "tests" / "test_reg.py").write_text(
            "import unittest\nclass Reg(unittest.TestCase):\n"
            "    def test_reg(self):\n        \"\"\"REG-1 regression\"\"\"\n        self.assertTrue(True)\n"
        )
        (repo / "tests" / "test_mod.py").write_text("import unittest\n")
        home = repo / knowledge.HOME
        home.mkdir(parents=True)
        (home / "spec.md").write_text("## Requirements\n\n### R-1 Compute\n\nBehavior: fn adds 1 and fn2 adds 2.\n\n## Retired\n")
        (home / "architecture.md").write_text("## Stack\n\nPython.\n\n## Decisions\n\n### AD-1 Plain\n\nChoice: mod.py.\n\n## Superseded\n")
        (home / "environment.md").write_text("## Commands\n\n- `python3 -m unittest`: runs unit tests\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "base")
        state = nav.new_state(str(repo), "Build fn and fn2.", improve_skill=str(inner.IMPROVE_CARD),
                              lint_option="off", planning_review="none")
        nav.save(run_dir, state)
        return base, repo, run_dir

    def _complete(self, run_dir: Path, result: dict, *, loop_inner: bool = True) -> dict:
        state = store.read_record(run_dir / "state.md")
        action = nav.current_action(state)["id"]
        stage = nav.current_stage(state)
        payload = dict(result)
        if stage == "plan" and payload.get("outcome") == "done":
            payload.setdefault("assumptions", [])
            queue = payload.get("work_items", state["work_items"])
            payload.setdefault("concerns", inner.no_concerns_map(r["id"] for r in queue))
            payload = inner.fixture_follows(state, payload)
        elif stage == "intake":
            payload = inner.fixture_intake(state, payload)
        elif stage == "spec" and payload.get("outcome") == "done":
            payload = {**inner.fixture_primary(state), **payload}
        elif stage == "test-strategy" and payload.get("outcome") == "done":
            payload = {**inner.fixture_test_layers(), **payload}
        if stage in knowledge.CLOSES:
            knowledge_support.write(state)
        if loop_inner and loops.cursor(state) is not None and payload.get("outcome") != "blocked":
            outcome = "done" if payload.get("outcome") == "done" else "blocked"
            receipt = loop_support.finish_loop(run_dir, outcome=outcome)
            payload = loop_support.with_receipt(payload, receipt)
        fpath = run_dir / "inbox" / f"{action}.md"
        fpath.parent.mkdir(exist_ok=True)
        fpath.write_text(store.dumps(payload, "result"))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            nav.dispatch(inner.CORE, run_dir, state,
                         types.SimpleNamespace(command="complete", action=action, result=str(fpath)))
        return store.read_record(run_dir / "state.md")

    def _finish_improve(self, run_dir: Path) -> dict:
        state = store.read_record(run_dir / "state.md")
        child = state["active_improve"]
        self.assertIsNotNone(child)
        updated = nav.finish_improve(state, child["action_id"], {
            "summary": "Synthetic Improve review passed.",
            "review_refs": ["synthetic://review"],
            "check_refs": ["synthetic://check"],
        })
        return nav.accept_effects(inner.CORE, run_dir, state, updated, action_id=child["action_id"])

    def _advance_to_test(self, repo: Path, run_dir: Path, step_plan: dict | None = None,
                         intake_payload: dict | None = None, ts_payload: dict | None = None) -> dict:
        state = self._complete(run_dir, intake_payload or {"outcome": "done", "summary": "S1."})
        state = self._complete(run_dir, {"outcome": "done", "summary": "Discovered."})
        state = self._complete(run_dir, {"outcome": "done", "summary": "Researched."})
        state = self._complete(run_dir, {"outcome": "done", "summary": "Spec ok."})
        state = self._complete(run_dir, ts_payload or {"outcome": "done", "summary": "Strategy ok."})
        self.assertEqual(nav.current_stage(state), "plan")
        state = self._complete(run_dir, {"outcome": "done", "summary": "Planned.",
                                         "work_items": [{"id": "W1", "title": "Core", "context": "Implement fn and fn2."}]})
        state = self._complete(run_dir, {"outcome": "done", "summary": "Prepared."})
        self.assertEqual(nav.current_stage(state), "step-plan")
        state = self._complete(run_dir, step_plan or _two_step_plan())
        state = self._complete(run_dir, _two_step_spec())
        if nav.current_stage(state) == "validate-existing":
            state = self._complete(run_dir, {"outcome": "done", "summary": "Validated."})
        self.assertEqual(nav.current_stage(state), "implement")
        # S1 implements fn (+1)
        (repo / "mod.py").write_text("def fn(x):\n    return x + 1\n")
        state = self._complete(run_dir, {
            "outcome": "done", "summary": "Implemented fn.", "not_covered": [],
            "learned": ["fn increments input"], "decisions": ["plain return"],
        })
        self.assertEqual(nav.current_stage(state), "test")
        return state

    # --- Sequence 1 & 2: Diff patch, architecture access, added_tests, test_findings, step_proof on product edit ---

    def test_seq1_and_seq2_test_channel_diff_added_tests_findings_and_step_proof_recheck(self) -> None:
        self.assertEqual(knowledge.STAGE_FILES["test"], ("environment.md", "architecture.md"))
        self.assertIn("test", assumptions.OPEN_ITEM_STAGES)
        self.assertIn("test", assumptions.REFLECT_AND_REVISE_PRODUCERS)
        self.assertIn("test", assumptions.PER_STEP_STAGES)

        _base, repo, run_dir = self._init_repo_run()
        state = self._advance_to_test(repo, run_dir)
        test_action = nav.current_action(state)["id"]
        self.assertIn("entry", nav.current_action(state))

        # Write field files + render head: verify product diff patch + architecture.md + head < 20000
        nav.write_field_files(run_dir, state)
        patch_path = run_dir / "fields" / f"{test_action}-product-diff.patch"
        self.assertTrue(patch_path.is_file(), "product diff patch must be written for active test stage")
        patch_text = patch_path.read_text()
        self.assertIn("mod.py", patch_text)
        self.assertIn("+    return x + 1", patch_text)
        head = self._head(run_dir, state)
        self.assertLess(len(head), nav.HEAD_LIMIT)
        self.assertIn(f"RUN/fields/{test_action}-product-diff.patch", head)
        self.assertIn("architecture.md", head)

        # Write TC-1 and boundary test TC-1a; verify when test edits product code cleanly and breaks Proof,
        # step_proof rejects test done, then passes once product code matches Proof and tests!
        (repo / "tests" / "test_mod.py").write_text(
            "import unittest, mod\n"
            "class T(unittest.TestCase):\n"
            "    def test_one(self):\n"
            "        \"\"\"TC-1\"\"\"\n"
            "        self.assertEqual(mod.fn(1), 2)\n"
            "    def test_one_a(self):\n"
            "        \"\"\"TC-1a\"\"\"\n"
            "        self.assertEqual(mod.fn(0), 1)\n"
        )
        # First break fn(1) only when fn(0) still returns 1? Actually Proof checks fn(1)==2; edit mod.py with a dummy
        # edit that makes Proof fail (say Proof requires fn(1)==2, wait if test_TC_1 checks fn(0)==1 while we keep
        # a temporary bad fn(1)==99 and only test_TC_1 checks fn(0)? Easier: edit mod.py cleanly once for TC-1/TC-1a
        # and also test failing step_proof separately via a tiny broken edit!)
        (repo / "mod.py").write_text("def fn(x):\n    return x + 1\n# probe\n")
        # Break Proof separately in check mode: write fn(1)->0 and revert
        (repo / "mod.py").write_text("def fn(x):\n    return 0 if x == 1 else x + 1\n")
        self.assertTrue(nav._test_edited_product_code(run_dir, state, "W1"))
        _writes, proof_refusal, _summary = test_loop.step_proof(run_dir, state, "W1", test_action, count=False, stage="test")
        self.assertIn("did not pass", proof_refusal)
        # Fix mod.py properly (edits product code to add TypeError check without breaking fn(1)==2), submit test done with added_tests + test_findings
        (repo / "mod.py").write_text(
            "def fn(x):\n"
            "    if not isinstance(x, int):\n"
            "        raise TypeError('int required')\n"
            "    return x + 1\n"
        )
        state = self._complete(run_dir, {
            "outcome": "done",
            "summary": "Added TC-1, boundary TC-1a; fixed non-int check in mod.py.",
            "added_tests": [{"id": "TC-1a", "command": "python3 -B -m unittest -v tests/test_mod.py"}],
            "test_findings": [
                {"id": "TF1", "finding": "fn2 in S2 also needs TypeError guard on non-int",
                 "evidence": "tests/test_mod.py TC-1a check", "impact": "amend-remaining",
                 "next_step": "Amend S2 task and C2 to enforce TypeError guard"},
                {"id": "TF2", "finding": "Verify mod.fn integration under CLI runner",
                 "evidence": "probe output", "impact": "system-test",
                 "next_step": "Cover CLI integration at system-test-author"},
            ],
            "mutant_dispositions": [
                {"mutant": "mod.py:3:5", "evidence": "Guard tested only via outer caller",
                 "disposition": "not-exercisable"},
            ],
        })
        # Verify step-proof record WAS executed at test stage because product code changed!
        proof_files = list((run_dir / "tests").glob(f"{test_action}-step-proof*.md"))
        self.assertTrue(proof_files, "step_proof must re-run when test edits product code")
        self.assertEqual(store.read_record(proof_files[-1])["stage"], "test")
        # Verify added_tests registered for both test & document
        reg = test_loop.registered(state, "W1")
        self.assertIn("TC-1a", reg["python3 -B -m unittest -v tests/test_mod.py"])

        # Sequence 1 + Sequence 3: At document(S1), test_findings are shown in P1 head!
        self.assertEqual(nav.current_stage(state), "document")
        doc_head = self._head(run_dir, state)
        self.assertIn("TF1", doc_head)
        self.assertIn("[amend-remaining]", doc_head)

        # Verify Sequence 3: document(S1) submits done WITH replan_remaining!
        # Needs S1 Improve review; finish Improve and ensure S1 committed AND base recaptured AND returned to step-plan!
        head_before_commit = _git(repo, "rev-parse", "HEAD").strip()
        state = self._complete(run_dir, {
            "outcome": "done",
            "summary": "Documented S1 fn TypeError guard; triggering commit-then-amend replan_remaining for S2.",
            "assumptions": [],
            "knowledge": {"spec": "noted fn guard (W1/S1)", "architecture": "unchanged", "environment": "unchanged"},
            "replan_remaining": {
                "reason": "S1 revealed TypeError guard pattern that S2 must follow",
                "affects": ["S2", "C2"],
            },
        })
        # Document has Improve item review
        self.assertIsNotNone(state.get("active_improve"))
        state = self._finish_improve(run_dir)
        head_after_commit = _git(repo, "rev-parse", "HEAD").strip()
        self.assertNotEqual(head_before_commit, head_after_commit, "S1 must be committed before reopening step-plan")
        self.assertEqual(nav.current_stage(state), "step-plan")
        self.assertEqual(state["revisions"].get("W1"), 1)
        self.assertEqual(planning_revision.done_steps(state, "W1"), 1)

        # Amended step-plan packet shows Fix forward rows (S1 marked done: true) + TF1 + TF2!
        sp_head = self._head(run_dir, state)
        self.assertIn("Fix forward: S1 is done (reviewed and committed)", sp_head)
        self.assertIn("TF1", sp_head)
        self.assertIn("replan_remaining", sp_head)

        # Submit amended step-plan keeping S1 marked done: true and amending S2!
        amended_plan = _two_step_plan()
        amended_plan["steps"][0]["done"] = True
        amended_plan["steps"][1]["task"] = "Implement fn2 with TypeError guard (C2)."
        state = self._complete(run_dir, amended_plan)
        self.assertEqual(nav.current_stage(state), "test-spec")
        # Amended test-spec preserves TC-1 (due at done step S1) and updates/keeps TC-2
        state = self._complete(run_dir, _two_step_spec())
        if nav.current_stage(state) == "validate-existing":
            state = self._complete(run_dir, {"outcome": "done", "summary": "Validated amended base."})
        # Now cursor must jump directly to implement S2 (NOT re-run S1!)
        self.assertEqual(nav.current_stage(state), "implement")
        self.assertEqual(nav.step_view(state, "W1").step["id"], "S2")

        # Complete S2 implement -> test -> document; verify replan_remaining is REFUSED on the LAST step S2!
        (repo / "mod.py").write_text(
            "def fn(x):\n    if not isinstance(x, int):\n        raise TypeError('int required')\n    return x + 1\n\n"
            "def fn2(x):\n    if not isinstance(x, int):\n        raise TypeError('int required')\n    return x + 2\n"
        )
        state = self._complete(run_dir, {"outcome": "done", "summary": "Built fn2.", "not_covered": [],
                                         "learned": ["fn2 matches"], "decisions": ["consistent guard"]})
        self.assertEqual(nav.current_stage(state), "test")
        (repo / "tests" / "test_mod.py").write_text(
            "import unittest, mod\n"
            "class T(unittest.TestCase):\n"
            "    def test_one(self):\n        \"\"\"TC-1\"\"\"\n        self.assertEqual(mod.fn(1), 2)\n"
            "    def test_one_a(self):\n        \"\"\"TC-1a\"\"\"\n        self.assertEqual(mod.fn(0), 1)\n"
            "    def test_two(self):\n        \"\"\"TC-2\"\"\"\n        self.assertEqual(mod.fn2(1), 3)\n"
        )
        state = self._complete(run_dir, {"outcome": "done", "summary": "All tests pass."})
        self.assertEqual(nav.current_stage(state), "document")
        # Attempt replan_remaining on final step S2 -> MUST refuse!
        with self.assertRaises(nav.NavigatorError) as caught:
            self._complete(run_dir, {
                "outcome": "done", "summary": "Trying replan on final step.",
                "assumptions": [],
                "knowledge": {"spec": "n/a", "architecture": "n/a", "environment": "n/a"},
                "replan_remaining": {"reason": "no more steps", "affects": ["S2"]},
            })
        self.assertIn("last step", str(caught.exception))

        # Complete S2 document normally -> Improve -> reflect-and-revise -> system-test-author
        state = self._complete(run_dir, {
            "outcome": "done", "summary": "Documented S2.", "assumptions": [],
            "knowledge": {"spec": "documented fn2 (W1/S2)", "architecture": "unchanged", "environment": "unchanged"},
        })
        state = self._finish_improve(run_dir)
        self.assertEqual(nav.current_stage(state), "reflect-and-revise")
        rr_head = self._head(run_dir, state)
        self.assertIn("TF1", rr_head)
        state = self._complete(run_dir, {"outcome": "done", "summary": "Reviewed W1.", "assumptions": [],
                                         "skill": dict(inner.SKILL_NONE)})
        if state.get("active_improve"):
            state = self._finish_improve(run_dir)
        self.assertEqual(nav.current_stage(state), "system-test-author")
        sta_head = self._head(run_dir, state)
        self.assertIn("TF2", sta_head)
        self.assertIn("not-exercisable", sta_head)
        self.assertIn("mod.py:3:5", sta_head)

    # --- Sequence 4: Intake questions -> test-strategy open items -> step-plan targets + inherited regressions ---

    def test_seq4_intake_questions_strategy_open_items_step_plan_targets_and_inherited_regressions(self) -> None:
        _base, repo, run_dir = self._init_repo_run()
        # Intake records an experiment question K8 (providing all K1..K12 categories)
        cats = [({"id": c, "applies": "yes"} if c == "K8" else {"id": c, "applies": "no", "reason": "none"})
                for c in nav.QUESTION_CATEGORIES]
        state = self._complete(run_dir, {
            "outcome": "done", "summary": "S1.",
            "question_categories": cats,
            "questions": [{"id": "Q1", "category": "K8", "question": "Does mod support negative ints?",
                           "changes": "boundary behavior", "route": "experiment",
                           "default": "support negatives", "blocks": "nothing"}],
        })
        state = self._complete(run_dir, {"outcome": "done", "summary": "Disc."})
        state = self._complete(run_dir, {"outcome": "done", "summary": "Res."})
        state = self._complete(run_dir, {"outcome": "done", "summary": "Spec."})
        self.assertEqual(nav.current_stage(state), "test-strategy")
        ts_head = self._head(run_dir, state)
        self.assertIn("Q1", ts_head)
        self.assertIn("negative ints", ts_head)

        # test-strategy leaves open items due at plan and prepare!
        self.assertIn("plan", assumptions.allowed_due_stages("test-strategy"))
        self.assertIn("prepare", assumptions.allowed_due_stages("test-strategy"))
        state = self._complete(run_dir, {
            "outcome": "done", "summary": "Strategy with due items.",
            "assumptions": [
                {"id": "TS1", "assumption": "Negative-int boundary order decided in plan",
                 "disposition": "open", "settle": "Assign W1 order", "reason": "not yet planned", "due_stage": "plan"},
                {"id": "TS2", "assumption": "Harness supports python -m unittest -v",
                 "disposition": "open", "settle": "Verify flag in prepare", "reason": "not yet checked", "due_stage": "prepare"},
            ],
        })
        self.assertEqual(nav.current_stage(state), "plan")
        plan_head = self._head(run_dir, state)
        self.assertIn("TS1", plan_head)
        self.assertNotIn("TS2", plan_head)

        state = self._complete(run_dir, {
            "outcome": "done", "summary": "Planned two items.",
            "assumptions": [
                {"id": "A1", "question": "Q1", "assumption": "mod.fn supports negative integers.",
                 "disposition": "evidenced", "evidence": ["https://example.test/q1"]},
            ],
            "work_items": [
                {"id": "W1", "title": "First", "context": "fn"},
                {"id": "W2", "title": "Second", "context": "fn2"},
            ],
        })
        self.assertEqual(nav.current_stage(state), "prepare")
        prep_head = self._head(run_dir, state)
        self.assertIn("TS2", prep_head)
        self.assertNotIn("TS1", prep_head)  # TS1 settled when plan finished!

        state = self._complete(run_dir, {"outcome": "done", "summary": "Prepared."})
        # Complete W1 cleanly with 1 step and a new target + regression command
        w1_plan = {
            "outcome": "done", "summary": "W1 plan", "follows": ["R-1"],
            "criteria": [{"id": "C1", "text": "fn increments (R-1).", "confirm": "executed"}],
            "steps": [{"id": "S1", "task": "Build fn (C1).", "deps": [], "criteria": ["C1"],
                       "paths": ["mod.py"], "proof": "python3 -B -c 'import mod; assert mod.fn(1)==2'", "skills": []}],
            "paths": ["mod.py", "tests/test_mod.py", "tests/test_reg.py"],
            "expectations": [{"id": "E1", "state": "works", "statement": "mod exists",
                              "steps": ["S1"], "paths": ["mod.py"], "check": "test -f mod.py"}],
            "targets": [{"target": "worker-db", "keeps_state": "yes",
                         "base_state_route": "reset-db.sh"}],
            "test_commands": [
                {"command": "python3 -B -m unittest -v tests/test_mod.py", "suite": "focused", "ids": ["TC-1"], "criteria": ["C1"],
                 "target": "worker-db"},
                {"command": "python3 -B -m unittest -v tests/test_reg.py", "suite": "regression", "ids": ["REG-1"], "criteria": ["C1"],
                 "target": "worker-db", "minimum": True},
                {"command": "python3 -B -m py_compile mod.py", "suite": "check"},
            ],
        }
        state = self._complete(run_dir, w1_plan)
        self.assertEqual(test_loop.stateful_targets(state), {"worker-db": "reset-db.sh"})
        state = self._complete(run_dir, {
            "outcome": "done", "summary": "Spec W1", "assumptions": [],
            "test_cases": [{"id": "TC-1", "criterion": "C1", "requirement": "R-1", "oracle": "fn(1)==2",
                            "red": "fn(1)==1", "green": "fn(1)==2"}],
        })
        if nav.current_stage(state) == "validate-existing":
            state = self._complete(run_dir, {"outcome": "done", "summary": "OK"})
        (repo / "mod.py").write_text("def fn(x):\n    return x + 1\n")
        state = self._complete(run_dir, {"outcome": "done", "summary": "Built", "not_covered": [],
                                         "learned": ["ok"], "decisions": ["ok"]})
        (repo / "tests" / "test_mod.py").write_text(
            "import unittest, mod\nclass T(unittest.TestCase):\n"
            "    def test_one(self):\n        \"\"\"TC-1\"\"\"\n        self.assertEqual(mod.fn(1), 2)\n"
        )
        state = self._complete(run_dir, {"outcome": "done", "summary": "Tested"})
        state = self._complete(run_dir, {"outcome": "done", "summary": "Doc", "assumptions": [],
                                         "knowledge": dict(inner.KNOWLEDGE_NONE)})
        state = self._finish_improve(run_dir)
        state = self._complete(run_dir, {"outcome": "done", "summary": "RR", "assumptions": [], "skill": dict(inner.SKILL_NONE)})
        # Now at W2 step-plan: packet should list W1's passing regression command!
        self.assertEqual(nav.current_stage(state), "step-plan")
        w2_head = self._head(run_dir, state)
        self.assertIn("Inherited passing regression commands from earlier items", w2_head)
        self.assertIn("python3 -B -m unittest -v tests/test_reg.py", w2_head)
        self.assertIn("Never edit product code directly", " ".join(prompts.DUTIES["system-test"].split()))
        self.assertIn("describe('<ID> ...')", " ".join(prompts.DUTIES["test-spec"].split()))


if __name__ == "__main__":
    unittest.main()
