#!/usr/bin/env python3
"""Causal E5/SG2 review attribution against Improve bind and pass snapshots."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "test" / "shiploop_e2e"
sys.path.insert(0, str(HARNESS / "evaluators"))
sys.path.insert(0, str(HARNESS))
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))

import common  # noqa: E402
import e5_regression  # noqa: E402
import experiment  # noqa: E402
import sg2_recall  # noqa: E402
import run  # noqa: E402


def _load_actual_improve_cli_tests():
    path = ROOT / "test" / "shiploop-actual-improve-cli.test.py"
    spec = importlib.util.spec_from_file_location("shiploop_actual_improve_cli_tests", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load runtime fixture helpers from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ACTUAL = _load_actual_improve_cli_tests()
CASE = "node-seeded-early-validation"


class ImproveReviewAttributionTests(unittest.TestCase):
    def runtime_sample(self, *, bound="naive", stage="document", producer_fix=False, loose_test=False,
                       layout="standard", e2e_workspace=False):
        """Use the real navigator binding and improve-pass CLI to create linked snapshot evidence."""
        helper = ACTUAL.ImproveCommitContractTests("runTest")
        helper.setUp()
        self.addCleanup(helper.tearDown)

        if e2e_workspace:
            helper.base = helper.base / "e2e-output"
            helper.base.mkdir()
            helper.repo = helper.base / "work"
        else:
            shutil.rmtree(helper.repo)
            helper.repo = helper.base / "worktree"
        helper.repo.mkdir()
        helper.improve_runtime_baseline = (run.improve_runtime.capture_baseline(helper.repo)
                                           if e2e_workspace else None)
        case = common.case(CASE)
        shutil.copytree(common.FIXTURES / case["fixture"], helper.repo, dirs_exist_ok=True)
        if bound in ("naive", "fixed"):
            shutil.copytree(common.FIXTURES / case["seeded_defect"]["tree"] / bound,
                            helper.repo, dirs_exist_ok=True)
        elif bound != "missing":
            raise ValueError(bound)
        if loose_test:
            shutil.copy2(common.FIXTURES / case["seeded_defect"]["tree"] / "naive" / "test/basket.test.js",
                         helper.repo / "test/basket.test.js")
        if layout == "nested":
            source = helper.repo / "src/basket.js"
            relocated = helper.repo / "src/basket/index.js"
            relocated.parent.mkdir(parents=True, exist_ok=True)
            source.replace(relocated)
        elif layout != "standard":
            raise ValueError(layout)
        helper.product_contract = helper.repo / "product" / "contracts" / "cold-recovery.md"
        helper.product_contract.parent.mkdir(parents=True, exist_ok=True)
        helper.product_contract.write_text("# Product contract\n", encoding="utf-8")
        helper.product_test = helper.repo / "test" / "product_contract_test.py"
        helper.product_test.parent.mkdir(parents=True, exist_ok=True)
        helper.product_test.write_text("def test_contract():\n    assert True\n", encoding="utf-8")

        helper.git("init", "-q")
        helper.git("-c", "user.name=T", "-c", "user.email=t@example.invalid", "add", "-A")
        helper.git("-c", "user.name=T", "-c", "user.email=t@example.invalid", "commit", "-qm", "seed")
        seed_head = helper.git("rev-parse", "HEAD").strip()
        if producer_fix:
            fixed = common.FIXTURES / case["seeded_defect"]["tree"] / "fixed"
            shutil.copytree(fixed, helper.repo, dirs_exist_ok=True)
            helper.git("add", "src/basket.js", "test/basket.test.js")
            helper.git("-c", "user.name=T", "-c", "user.email=t@example.invalid", "commit", "-qm",
                       "feat: implement Basket\n\nKey learnings: validate the assigned limit")

        knowledge = {name: "none: no additional project-specific knowledge" for name in
                     ("spec", "architecture", "environment")}
        steps = [{"id": "S1", "task": "Make the planned change.", "paths": ["src/**"],
                  "criteria": [], "proof": "true", "skills": []}]
        predecessor_extra = {"step-plan": {"paths": ["src/**"], "steps": steps,
                                             "expectations": [{"id": "E1", "state": "absent",
                                                                "statement": "src/basket.js does not exist yet.",
                                                                "steps": ["S1"], "paths": ["src/basket.js"],
                                                                "check": "test ! -e src/basket.js"}]}}
        producer_extra = {"knowledge": knowledge, "assumptions": []} if stage == "document" else {}
        if stage == "step-plan":
            producer_extra = {
                "paths": ["src/basket.js"],
                "steps": [{"id": "S1", "task": "Add the seeded Basket module.",
                           "paths": ["src/basket.js"], "criteria": [], "proof": "true", "skills": []}],
                "expectations": [{"id": "E1", "state": "absent",
                                  "statement": "src/basket.js does not exist yet.",
                                  "steps": ["S1"], "paths": ["src/basket.js"],
                                  "check": "test ! -e src/basket.js"}],
            }
        helper._start_parent_at_stage(stage, [str(helper.product_contract)], producer_extra=producer_extra,
                                      predecessor_extra=predecessor_extra)
        helper.message = ACTUAL.bridge.receipt_path(helper.bound).with_name("commit-message.md")
        helper.message.parent.mkdir(parents=True, exist_ok=True)
        helper.commit_args = [ACTUAL.CLI, "improve-commit", "--run-dir", helper.run,
                              "--action", helper.improve, "--message", helper.message]
        helper.reviews = lambda: ACTUAL.bridge.receipt_path(helper.bound).parent / "reviews"
        helper.REVIEW = ACTUAL.ImprovePassTests.REVIEW

        sample = helper.base / "sample"
        sample.mkdir()
        (sample / "invocation.json").write_text(json.dumps({
            "case": CASE,
            "seeded": {"run_dir": str(helper.run), "start_head": seed_head,
                       "action": helper.action, "item_bases": ["W1"]},
            "delegation": "inline",
        }), encoding="utf-8")
        return helper, sample, seed_head

    def write_review_pass(self, helper, *, edit="fixed", add_test=True, commit=False, description=None,
                          intermediate_test_failure=False):
        ACTUAL.ImprovePassTests.start_ephemeral_child(helper)
        case = common.case(CASE)
        fixed = common.FIXTURES / case["seeded_defect"]["tree"] / "fixed"
        naive = common.FIXTURES / case["seeded_defect"]["tree"] / "naive"
        if edit == "fixed":
            shutil.copy2(fixed / "src/basket.js", helper.repo / "src/basket.js")
            if add_test:
                shutil.copy2(fixed / "test/basket.test.js", helper.repo / "test/basket.test.js")
        elif edit in ("fixed-relocated", "relocate-fixed"):
            target = helper.repo / "src/basket/index.js"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fixed / "src/basket.js", target)
            source = helper.repo / "src/basket.js"
            if source.exists():
                source.unlink()
            if add_test:
                shutil.copy2(fixed / "test/basket.test.js", helper.repo / "test/basket.test.js")
        elif edit == "max-only":
            source = (fixed / "src/basket.js").read_text(encoding="utf-8")
            source = source.replace("module.exports = { Basket };",
                                    "const MAX_ITEMS = 99;\nmodule.exports = { Basket, MAX_ITEMS };")
            (helper.repo / "src/basket.js").write_text(source, encoding="utf-8")
            (helper.repo / "test/basket-max.test.js").write_text(
                "const test = require('node:test');\n"
                "const assert = require('node:assert/strict');\n"
                "const { MAX_ITEMS } = require('../src/basket');\n"
                "test('exports the basket capacity', () => assert.equal(MAX_ITEMS, 99));\n",
                encoding="utf-8")
        elif edit == "naive":
            shutil.copy2(naive / "src/basket.js", helper.repo / "src/basket.js")
        elif edit != "none":
            raise ValueError(edit)
        if intermediate_test_failure:
            (helper.repo / "test/basket-intermediate.test.js").write_text(
                "const test = require('node:test');\n"
                "const assert = require('node:assert/strict');\n"
                "test('temporary unrelated assertion', () => assert.equal(1, 2));\n",
                encoding="utf-8")

        review_dir = helper.reviews()
        review_dir.mkdir(parents=True, exist_ok=True)
        checks = review_dir / "checks.md"
        command = ["node", "--test"]
        result = subprocess.run(command, cwd=helper.repo, capture_output=True, text=True)
        checks.write_text("$ node --test\n" + result.stdout + result.stderr, encoding="utf-8")
        if commit:
            helper.message.write_text(
                "fix: validate the assigned Basket limit\n\n"
                "Key learnings: constructor validation follows assignment.\n"
                "Regression test: test/basket.test.js\n", encoding="utf-8")
        ACTUAL.ImprovePassTests.write_review(
            helper, label="non-trivial" if edit != "none" else "trivial",
            exit="unsatisfied" if edit != "none" else "satisfied",
            found=description or ("the seeded limit-validation defect" if edit == "none" else
                                  "the limit was checked before its assignment"),
            changed="none" if edit == "none" else "src/basket.js and the focused test",
            why="no edit was needed" if edit == "none" else "the review fixes the behavior and checks it",
        )
        out = helper.invoke(*ACTUAL.ImprovePassTests.pass_args(helper)).stdout
        done, complete, _again = ACTUAL.ImprovePassTests.printed(helper, out)
        status = ACTUAL.ImprovePassTests.run_done(helper, done)["status"]
        if edit != "none":
            self.assertEqual(status, "active", out)
            if intermediate_test_failure:
                (helper.repo / "test/basket-intermediate.test.js").unlink()
            ACTUAL.ImprovePassTests.write_review(
                helper, n=2, label="trivial", exit="satisfied", found="nothing else material.",
                changed="none.", why="no further edit is needed.")
            out = helper.invoke(*ACTUAL.ImprovePassTests.pass_args(helper)).stdout
            done, complete, _again = ACTUAL.ImprovePassTests.printed(helper, out)
            status = ACTUAL.ImprovePassTests.run_done(helper, done)["status"]
        self.assertEqual(status, "complete", out)
        helper.run_argv(shlex.split(complete))
        return json.loads((review_dir / "pass-1.json").read_text(encoding="utf-8")), out

    def test_a_step_review_repair_without_a_commit_is_causally_attributed(self):
        helper, sample, _seed = self.runtime_sample()
        passed, _out = self.write_review_pass(helper, commit=False)
        self.assertTrue(passed["changed"])
        self.assertIsNone(passed["commit"])

        e5 = e5_regression.score(sample)
        sg2 = sg2_recall.score(sample)
        self.assertEqual(e5["value"], 1, e5)
        self.assertEqual(e5["review_repair"]["status"], "repaired")
        self.assertTrue(e5["fixes"][0]["passes_after"])
        self.assertTrue(e5["fixes"][0]["fails_before_fix"])
        self.assertEqual(sg2["review_repair"]["value"], 1, sg2)
        self.assertEqual(sg2["review_repair"]["status"], "repaired")

    def test_final_defect_gate_survives_missing_attribution_and_reaches_judge(self):
        helper, sample, _seed = self.runtime_sample()
        self.write_review_pass(helper, edit="none")
        bind = helper.run / "improve" / (helper.action + "-bind.md")
        bind.unlink()

        e5 = e5_regression.score(sample)
        self.assertIsNone(e5["value"], e5)
        self.assertEqual(e5["review_repair"]["status"], "unknown")
        self.assertIs(e5["defect_caught"], False, e5)

        control = [{"value": 0.5, "defect_caught": True} for _ in range(5)]
        candidate = [{"value": 0.9, "defect_caught": True} for _ in range(4)]
        candidate.append({"value": e5["value"], "defect_caught": e5["defect_caught"]})
        report = experiment.judge(control, candidate, gate="defect_caught")
        self.assertEqual(report["gate_rates"], [1.0, 0.8], report)
        self.assertEqual(report["verdict"], "contradicts", report)

    def test_valid_relocated_module_is_probed_and_credited_as_repaired(self):
        helper, sample, _seed = self.runtime_sample(layout="nested")
        self.write_review_pass(helper, edit="fixed-relocated")

        e5 = e5_regression.score(sample)
        sg2 = sg2_recall.score(sample)
        self.assertTrue(e5["defect_caught"], e5)
        self.assertEqual(e5["review_repair"]["status"], "repaired", e5)
        self.assertIsNone(e5["value"], e5)  # unsupported E5 counterfactual layout is unknown
        self.assertEqual(sg2["review_repair"]["status"], "repaired", sg2)
        self.assertEqual(sg2["review_repair"]["value"], 1, sg2)

    def test_valid_relocation_of_a_clean_module_is_not_a_regression(self):
        helper, sample, _seed = self.runtime_sample(bound="fixed", loose_test=True)
        self.write_review_pass(helper, edit="relocate-fixed")

        sg2 = sg2_recall.score(sample)
        self.assertEqual(sg2["value"], 1, sg2)
        self.assertEqual(sg2["review_repair"]["status"], "not_applicable", sg2)
        self.assertEqual(sg2["review_repair"]["repair_count"], 0, sg2)
        self.assertIsNone(sg2["review_repair"]["value"], sg2)

    def test_unrelated_added_export_test_does_not_earn_e5_credit(self):
        helper, sample, _seed = self.runtime_sample()
        self.write_review_pass(helper, edit="max-only")

        e5 = e5_regression.score(sample)
        self.assertEqual(e5["review_repair"]["status"], "repaired", e5)
        self.assertEqual(e5["value"], 0, e5)
        self.assertTrue(e5["fixes"][0]["passes_after"], e5)
        self.assertFalse(e5["fixes"][0]["fails_before_fix"], e5)

    def test_intermediate_public_check_failure_does_not_hide_a_final_repair(self):
        helper, sample, _seed = self.runtime_sample()
        first, _out = self.write_review_pass(helper, intermediate_test_failure=True)
        second = json.loads((helper.reviews() / "pass-2.json").read_text(encoding="utf-8"))
        self.assertTrue(first["changed"])
        self.assertTrue(second["changed"])
        self.assertNotEqual(first["tree"], second["tree"])

        e5 = e5_regression.score(sample)
        self.assertEqual(e5["review_repair"]["status"], "repaired", e5)
        self.assertEqual(e5["value"], 1, e5)
        self.assertTrue(e5["defect_caught"], e5)

    def test_missing_module_at_document_review_is_unknown_not_preimplementation(self):
        helper, sample, _seed = self.runtime_sample(bound="missing", stage="document")
        bound_state = e5_regression.improve_attribution._probe_state(common.case(CASE), helper.repo)
        self.assertIn("MODULE_NOT_FOUND", bound_state["behavior_checks"][0]["output"])
        self.write_review_pass(helper, edit="fixed")
        with mock.patch.object(e5_regression.improve_attribution, "_module_missing", return_value=True):
            e5 = e5_regression.score(sample)
            sg2 = sg2_recall.score(sample)
        self.assertTrue(e5["defect_caught"], e5)
        self.assertEqual(e5["review_repair"]["status"], "unknown", e5)
        self.assertIn("later review stage", e5["review_repair"]["why"])
        self.assertEqual(sg2["value"], 1, sg2)
        self.assertEqual(sg2["review_repair"]["status"], "unknown", sg2)

    def test_missing_module_at_step_plan_is_preimplementation_not_applicable(self):
        helper, sample, _seed = self.runtime_sample(bound="missing", stage="step-plan")
        passed, _out = self.write_review_pass(helper, edit="none")
        self.assertFalse(passed["changed"])
        fixed = common.FIXTURES / common.case(CASE)["seeded_defect"]["tree"] / "fixed"
        shutil.copy2(fixed / "src/basket.js", helper.repo / "src/basket.js")
        shutil.copy2(fixed / "test/basket.test.js", helper.repo / "test/basket.test.js")

        e5 = e5_regression.score(sample)
        self.assertTrue(e5["defect_caught"], e5)
        self.assertEqual(e5["review_repair"]["status"], "not_applicable", e5)
        self.assertEqual(e5["review_repair"]["repair_count"], 0, e5)
        self.assertIsNone(e5["review_repair"]["value"], e5)

    def test_a_committing_review_repair_uses_the_recorded_pass_commit(self):
        helper, sample, _seed = self.runtime_sample(stage="test-strategy")
        passed, _out = self.write_review_pass(helper, commit=True)
        self.assertIsInstance(passed["commit"], str)
        self.assertTrue(passed["changed"])

        e5 = e5_regression.score(sample)
        self.assertEqual(e5["value"], 1, e5)
        self.assertEqual(e5["review_repair"]["status"], "repaired")
        self.assertEqual(e5["fixes"][0]["commit"], passed["commit"])

    def test_a_clean_producer_learning_commit_is_not_a_review_repair(self):
        helper, sample, _seed = self.runtime_sample(producer_fix=True)
        passed, _out = self.write_review_pass(helper, edit="none")
        self.assertFalse(passed["changed"])

        e5 = e5_regression.score(sample)
        sg2 = sg2_recall.score(sample)
        self.assertIsNone(e5["value"], e5)
        self.assertEqual(e5["review_repair"]["status"], "not_applicable")
        self.assertEqual(sg2["value"], 1, sg2)  # the final behavior remains correct
        self.assertIsNone(sg2["review_repair"]["value"], sg2)
        self.assertEqual(sg2["review_repair"]["repair_count"], 0)
        self.assertEqual(sg2["review_repair"]["status"], "not_applicable")

    def test_an_unrepaired_fault_is_zero_even_when_the_review_says_it_found_it(self):
        helper, sample, _seed = self.runtime_sample()
        self.write_review_pass(helper, edit="none", description="the seeded defect is present and should be fixed")

        e5 = e5_regression.score(sample)
        sg2 = sg2_recall.score(sample)
        self.assertEqual(e5["value"], 0, e5)  # an entry defect was missed by the review
        self.assertEqual(e5["review_repair"]["status"], "unrepaired")
        self.assertEqual(sg2["value"], 0, sg2)
        self.assertEqual(sg2["review_repair"]["value"], 0)
        self.assertEqual(sg2["review_repair"]["status"], "unrepaired")

    def test_a_review_fix_without_a_regression_test_gets_no_e5_credit(self):
        helper, sample, _seed = self.runtime_sample()
        self.write_review_pass(helper, add_test=False)

        e5 = e5_regression.score(sample)
        sg2 = sg2_recall.score(sample)
        self.assertEqual(e5["review_repair"]["status"], "repaired")
        self.assertEqual(e5["value"], 0, e5)
        self.assertFalse(e5["fixes"][0]["test"])
        self.assertEqual(sg2["review_repair"]["value"], 1)

    def test_a_review_introducing_the_seeded_defect_is_not_credited(self):
        helper, sample, _seed = self.runtime_sample(bound="fixed", loose_test=True)
        self.write_review_pass(helper, edit="naive")

        e5 = e5_regression.score(sample)
        sg2 = sg2_recall.score(sample)
        self.assertEqual(e5["review_repair"]["status"], "introduced")
        self.assertEqual(sg2["value"], 0, sg2)
        self.assertEqual(sg2["review_repair"]["value"], 0)
        self.assertEqual(sg2["review_repair"]["status"], "introduced")

    def test_missing_or_ambiguous_snapshot_evidence_is_unknown(self):
        helper, sample, _seed = self.runtime_sample()
        self.write_review_pass(helper, edit="none")
        bind = helper.run / "improve" / (helper.action + "-bind.md")
        saved = bind.read_bytes()
        bind.unlink()
        missing = e5_regression.score(sample)
        self.assertIsNone(missing["value"], missing)
        self.assertEqual(missing["review_repair"]["status"], "unknown")
        self.assertIn("bind", missing["review_repair"]["why"])

        bind.write_bytes(saved)
        invocation_path = sample / "invocation.json"
        saved_invocation = invocation_path.read_bytes()
        invocation = json.loads(saved_invocation)
        invocation["case"] = None
        invocation_path.write_text(json.dumps(invocation), encoding="utf-8")
        malformed = sg2_recall.score(sample)
        self.assertIsNone(malformed["value"], malformed)
        self.assertEqual(malformed["review_repair"]["status"], "unknown")
        invocation_path.write_bytes(saved_invocation)

        child = next((helper.repo / ".shiploop-improve").glob("*/start.json")).parent
        duplicate = child.parent / ("implement-" + helper.action[-8:])
        shutil.copytree(child, duplicate)
        ambiguous = e5_regression.score(sample)
        self.assertIsNone(ambiguous["value"], ambiguous)
        self.assertEqual(ambiguous["review_repair"]["status"], "unknown")
        self.assertIn("ambiguous", ambiguous["review_repair"]["why"])

    def test_main_committed_verdict_excludes_only_proven_direct_improve_runtime(self):
        helper, _sample, seed_head = self.runtime_sample(e2e_workspace=True)
        self.assertTrue(helper.improve_runtime_baseline["root_absent"])
        self.assertEqual(helper.improve_runtime_baseline["git_mode"], "non-git")
        self.write_review_pass(helper, commit=False)
        helper.git("-c", "user.name=T", "-c", "user.email=t@example.invalid", "add", "--",
                   "src/basket.js", "test/basket.test.js")
        helper.git("-c", "user.name=T", "-c", "user.email=t@example.invalid", "commit", "-qm", "product")
        out, work = helper.base, helper.repo
        plugin = out / "build" / "plugins" / "skill-craft"
        (plugin / ".claude-plugin").mkdir(parents=True)
        (plugin / ".claude-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
        cli = plugin / "skills" / "shiploop" / "scripts" / "shiploop"
        cli.parent.mkdir(parents=True)
        cli.write_text("", encoding="utf-8")
        (out / "prompt.txt").write_text("fixture\n", encoding="utf-8")
        (out / "events.jsonl").write_text("", encoding="utf-8")
        (out / "timeline.jsonl").write_text("", encoding="utf-8")
        (out / "invocation.json").write_text(json.dumps({
            "case": "hello", "host": "claude", "backend": "anthropic", "model": "fixture", "effort": None,
            "checks": ["true"], "plugin_dir": str(plugin), "plugin": None, "versions": {}, "argv": [],
            "cwd": str(work), "base": {"start_head": seed_head}, "follow_on": None, "seeded": None,
            "planning_review": "none", "improve_runtime_baseline": helper.improve_runtime_baseline,
        }, indent=2) + "\n", encoding="utf-8")

        def grade():
            with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(
                    run, "review_export", return_value="fixture review export"):
                run.main(["--resume-run", str(out), "--grade-only", "--plugin-dir", str(plugin),
                          "--baseline", str(out / "baselines.jsonl")])
            return json.loads((out / "result.json").read_text(encoding="utf-8"))

        positive = grade()
        self.assertTrue(positive["committed"]["pass"], positive["committed"])
        knowledge = positive["shiploop"]["knowledge"]
        runtime_paths = {path for path in knowledge["uncommitted"] if path.startswith(".shiploop-improve/")}
        self.assertTrue(runtime_paths, "the real direct-child receipts remain visible in raw status")
        self.assertEqual(knowledge["runtime_uncommitted"], sorted(runtime_paths))
        self.assertEqual(knowledge["product_uncommitted"], [])
        status = helper.git("status", "--porcelain", "--untracked-files=all").splitlines()
        self.assertEqual(knowledge["git_status"], status)
        self.assertEqual(knowledge["untracked_files"], sum(line.startswith("?? ") for line in status))

        runtime_root = work / ".shiploop-improve"
        child = next(runtime_root.iterdir())
        state = run.metrics.engine_state(Path(helper.run))
        action = next(action for action, record in state["improve_results"].items()
                      if record.get("runtime_phase") == "complete")
        marker = "ShipLoop standalone Improve binding: " + state["improve_results"][action]["binding_id"]
        baseline = helper.improve_runtime_baseline

        def ownership(proof=baseline, selected=state):
            porcelain = helper.git("status", "--porcelain", "--untracked-files=all").splitlines()
            return run.improve_runtime.owned_untracked_paths(work, Path(helper.run), selected, proof, porcelain)

        def rejected(proof=baseline, selected=state):
            owned, reason = ownership(proof, selected)
            self.assertEqual(owned, set())
            self.assertTrue(reason)

        def state_copy():
            return json.loads(json.dumps(state))

        with self.subTest(observer_negative="preexisting root"):
            observed_existing = run.improve_runtime.capture_baseline(work)
            self.assertIs(observed_existing["root_absent"], False)
            rejected(proof=observed_existing)
        with self.subTest(observer_negative="malformed baseline"):
            rejected(proof={**baseline, "observed_at_ns": "unknown"})
        with self.subTest(observer_negative="foreign selected workspace"):
            foreign = out / "foreign-workspace"
            foreign.mkdir()
            selected = state_copy()
            selected["repo"] = str(foreign)
            rejected(selected=selected)
            foreign.rmdir()
        with self.subTest(observer_negative="foreign imported workspace"):
            foreign = out / "foreign-workspace"
            foreign.mkdir()
            selected = state_copy()
            selected["improve_results"][action]["workspace"] = str(foreign)
            rejected(selected=selected)
            foreign.rmdir()
        with self.subTest(observer_negative="foreign run binding"):
            selected = state_copy()
            selected["improve_results"][action]["binding_id"] = "foreign-run/foreign-action"
            rejected(selected=selected)
        with self.subTest(observer_negative="malformed imported result"):
            selected = state_copy()
            selected["improve_results"][action]["runtime_phase"] = "stopped"
            rejected(selected=selected)

        lookalike = runtime_root / "lookalike-child"
        shutil.copytree(child, lookalike)
        try:
            with self.subTest(observer_negative="unbound lookalike child"):
                rejected()
        finally:
            shutil.rmtree(lookalike)

        start_path = child / "start.json"
        start_bytes = start_path.read_bytes()
        try:
            start_data = json.loads(start_bytes)
            start_data["context"]["request"] += "\n" + marker
            start_path.write_text(json.dumps(start_data), encoding="utf-8")
            with self.subTest(observer_negative="ambiguous binding marker"):
                rejected()
        finally:
            start_path.write_bytes(start_bytes)

        packet_path = child / "packet.json"
        packet_bytes = packet_path.read_bytes()
        try:
            packet_path.write_bytes(b"{malformed terminal packet")
            with self.subTest(observer_negative="malformed terminal packet"):
                rejected()
        finally:
            packet_path.write_bytes(packet_bytes)

        pass_path = next((child / "reviews").glob("pass-*.json"))
        pass_bytes = pass_path.read_bytes()
        try:
            pass_path.write_bytes(b"{malformed pass record")
            with self.subTest(observer_negative="malformed pass record"):
                rejected()
        finally:
            pass_path.write_bytes(pass_bytes)

        symlink_target = out / "outside-runtime-target.txt"
        symlink_file = child / "opening.md"
        original_opening = symlink_file.read_bytes()
        symlink_target.write_bytes(original_opening)
        try:
            symlink_file.unlink()
            symlink_file.symlink_to(symlink_target)
            with self.subTest(observer_negative="symlink at a recognized runtime filename"):
                rejected()
        finally:
            symlink_file.unlink(missing_ok=True)
            symlink_file.write_bytes(original_opening)
            symlink_target.unlink(missing_ok=True)

        saved_root = out / "saved-runtime-root"
        runtime_root.rename(saved_root)
        try:
            runtime_root.symlink_to(saved_root, target_is_directory=True)
            with self.subTest(observer_negative="symlink runtime root"):
                rejected()
        finally:
            runtime_root.unlink(missing_ok=True)
            saved_root.rename(runtime_root)

        with self.subTest(observer_negative="runtime path added then removed in reachable history"):
            head = helper.git("rev-parse", "HEAD").strip()
            tracked_path = (child / "start.json").relative_to(work).as_posix()
            branch = "observer-calibration-history"
            with tempfile.TemporaryDirectory(dir=out, prefix="observer-index-") as temporary:
                index = Path(temporary) / "index"
                env = {**helper.environment, "GIT_INDEX_FILE": str(index)}

                def alt_git(*args):
                    return subprocess.run(["git", "-C", str(work), *args], env=env, check=True,
                                          capture_output=True, text=True).stdout.strip()

                alt_git("read-tree", head)
                alt_git("add", "--", tracked_path)
                added_tree = alt_git("write-tree")
                added_commit = alt_git("-c", "user.name=T", "-c", "user.email=t@example.invalid",
                                       "commit-tree", added_tree, "-p", head, "-m", "temporary runtime add")
                alt_git("read-tree", added_commit)
                alt_git("rm", "--cached", "--", tracked_path)
                removed_tree = alt_git("write-tree")
                removed_commit = alt_git("-c", "user.name=T", "-c", "user.email=t@example.invalid",
                                         "commit-tree", removed_tree, "-p", added_commit,
                                         "-m", "temporary runtime removal")
                helper.git("branch", branch, removed_commit)
                try:
                    rejected()
                finally:
                    helper.git("branch", "-D", branch)

        product_path = work / "src" / "basket.js"
        product_bytes = product_path.read_bytes()
        try:
            product_path.write_bytes(product_bytes + b"\n// temporary modified-product control\n")
            modified_facts = run.knowledge_facts(work, run_dir=Path(helper.run), state=state,
                                                 improve_baseline=baseline)
            self.assertFalse(run.committed_facts(modified_facts, seed_head)["pass"])
            self.assertIn("src/basket.js", modified_facts["product_uncommitted"])
        finally:
            product_path.write_bytes(product_bytes)

        index_path = Path(helper.git("rev-parse", "--git-path", "index").strip())
        if not index_path.is_absolute():
            index_path = work / index_path
        index_bytes = index_path.read_bytes()
        try:
            product_path.write_bytes(product_bytes + b"\n// temporary staged-product control\n")
            helper.git("add", "--", "src/basket.js")
            staged_product_facts = run.knowledge_facts(work, run_dir=Path(helper.run), state=state,
                                                       improve_baseline=baseline)
            self.assertFalse(run.committed_facts(staged_product_facts, seed_head)["pass"])
            self.assertIn("src/basket.js", staged_product_facts["product_uncommitted"])
        finally:
            product_path.write_bytes(product_bytes)
            index_path.write_bytes(index_bytes)

        ordinary = work / "ordinary-untracked.txt"
        ordinary.write_text("product dirt\n", encoding="utf-8")
        with_ordinary = grade()
        self.assertFalse(with_ordinary["committed"]["pass"])
        self.assertIn("ordinary-untracked.txt", with_ordinary["shiploop"]["knowledge"]["product_uncommitted"])
        ordinary.unlink()

        child = next((work / ".shiploop-improve").iterdir())
        unknown = child / "unknown-runtime-file.txt"
        unknown.write_text("not an Improve writer artifact\n", encoding="utf-8")
        with_unknown = grade()
        self.assertFalse(with_unknown["committed"]["pass"])
        self.assertEqual(with_unknown["shiploop"]["knowledge"]["runtime_uncommitted"], [])
        self.assertIn(unknown.relative_to(work).as_posix(),
                      with_unknown["shiploop"]["knowledge"]["product_uncommitted"])
        self.assertTrue(with_unknown["shiploop"]["knowledge"]["runtime_uncommitted_reason"])
        unknown.unlink()

        invocation_path = out / "invocation.json"
        original_invocation = invocation_path.read_bytes()
        invocation = json.loads(original_invocation)
        invocation.pop("improve_runtime_baseline")
        invocation_path.write_text(json.dumps(invocation), encoding="utf-8")
        without_baseline = grade()
        self.assertFalse(without_baseline["committed"]["pass"])
        self.assertEqual(without_baseline["shiploop"]["knowledge"]["runtime_uncommitted"], [])
        self.assertTrue(without_baseline["shiploop"]["knowledge"]["runtime_uncommitted_reason"])
        invocation_path.write_bytes(original_invocation)

        staged_path = knowledge["runtime_uncommitted"][0]
        try:
            helper.git("add", "--", staged_path)
            with_staged_runtime = grade()
            self.assertFalse(with_staged_runtime["committed"]["pass"])
            self.assertEqual(with_staged_runtime["shiploop"]["knowledge"]["runtime_uncommitted"], [])
            self.assertIn(staged_path, with_staged_runtime["shiploop"]["knowledge"]["product_uncommitted"])
        finally:
            index_path.write_bytes(index_bytes)

    def test_invalid_final_public_checks_make_both_scores_unknown(self):
        helper, sample, _seed = self.runtime_sample(bound="fixed")
        self.write_review_pass(helper, edit="none")
        (helper.repo / "src/basket.js").write_text("throw new Error('invalid final tree');\n", encoding="utf-8")

        e5 = e5_regression.score(sample)
        sg2 = sg2_recall.score(sample)
        self.assertIsNone(e5["value"], e5)
        self.assertEqual(e5["review_repair"]["status"], "unknown")
        self.assertIn("public checks", e5["review_repair"]["why"])
        self.assertIsNone(e5["defect_caught"], e5)
        self.assertIsNone(sg2["value"], sg2)
        self.assertEqual(sg2["review_repair"]["status"], "unknown")


if __name__ == "__main__":
    unittest.main()
