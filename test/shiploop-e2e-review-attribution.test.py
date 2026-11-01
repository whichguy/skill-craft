#!/usr/bin/env python3
"""Causal E5/SG2 review attribution against Improve bind and pass snapshots."""
from __future__ import annotations

import importlib.util
import json
import shlex
import shutil
import subprocess
import sys
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
                       layout="standard"):
        """Use the real navigator binding and improve-pass CLI to create linked snapshot evidence."""
        helper = ACTUAL.ImproveCommitContractTests("runTest")
        helper.setUp()
        self.addCleanup(helper.tearDown)

        shutil.rmtree(helper.repo)
        helper.repo = helper.base / "worktree"
        helper.repo.mkdir()
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
