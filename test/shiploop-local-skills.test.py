#!/usr/bin/env python3
"""Offline regression of the local-skill study apparatus, never a model eval.

Replay immutable observations and corrupt disposable copies to verify the grader.
These checks do not establish new skill creation, selection, or semantic quality.
"""
from pathlib import Path
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
APPARATUS = ROOT / "test/experiments/shiploop_local_skills"
EVIDENCE = APPARATUS / "evidence/2026-09-18"
spec = importlib.util.spec_from_file_location("local_skill_oracle", APPARATUS / "oracle.py")
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)

# Declared here, not derived from the grader or archived summary. b04 deliberately
# preserves the original incident-contract ambiguity; b04r is its clarified rerun.
OBSERVATIONS = (
    ("baseline", "initial", True), ("a02", "reuse", True),
    ("candidate", "initial", True), ("b02", "reuse", True),
    ("b03", "evolve", True), ("b04", "fork", False),
    ("b04r", "fork", True), ("b05", "noop", True),
    ("b06", "relocate", True), ("b07", "reuse", True),
)


class LocalSkillApparatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-local-skills-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.copy_number = 0

    def clone(self, trial):
        self.copy_number += 1
        target = self.base / f"{trial}-{self.copy_number}"
        shutil.copytree(EVIDENCE / trial / "fixture", target / "fixture")
        target.mkdir(exist_ok=True)
        shutil.copyfile(EVIDENCE / trial / "control/before-manifest.json", target / "before.json")
        return target / "fixture", target / "before.json"

    def assert_rejected(self, case, fixture, before, check):
        report = oracle.grade(case, fixture, before)
        self.assertFalse(report["passed"], report)
        self.assertIn(check, [row["name"] for row in report["checks"] if not row["passed"]], report)

    def test_archived_outcomes_replay_from_relocated_copies(self):
        for trial, case, expected in OBSERVATIONS:
            with self.subTest(trial=trial):
                fixture, before = self.clone(trial)
                report = oracle.grade(case, fixture, before)
                self.assertEqual(report["passed"], expected, report)
                if not expected:
                    self.assertEqual(
                        [row["name"] for row in report["checks"] if not row["passed"]],
                        ["exact decision.json"],
                    )

    def test_missing_malformed_and_wrong_decisions_are_rejected(self):
        for mutation in ("missing", "malformed", "old-pass", "wrong-candidate", "wrong-target", "wrong-type"):
            with self.subTest(mutation=mutation):
                fixture, before = self.clone("candidate")
                output = fixture / "output/decision.json"
                if mutation == "missing":
                    output.unlink()
                elif mutation == "malformed":
                    output.write_text("{not-json", encoding="utf-8")
                else:
                    decision = json.loads(output.read_text())
                    if mutation == "old-pass":
                        decision["selected_receipts"][1] = {"check": "integration", "attempt": 1, "status": "pass"}
                        decision["decision"] = "clear"
                    elif mutation == "wrong-candidate":
                        decision["candidate"] = "stale-candidate"
                    elif mutation == "wrong-type":
                        decision["deployment_authorized"] = 0  # Numeric zero is not JSON false.
                    else:
                        decision["target"] = "production"
                    output.write_text(json.dumps(decision), encoding="utf-8")
                self.assert_rejected("initial", fixture, before, "exact decision.json")

    def test_reuse_and_noop_detect_changes_outside_skill_card(self):
        for trial, case, check in (
            ("b02", "reuse", "preexisting local skills preserved"),
            ("b05", "noop", "local skill packages unchanged"),
        ):
            with self.subTest(case=case):
                fixture, before = self.clone(trial)
                helper = fixture / "skills/release-evidence-triage/references/changed.md"
                helper.parent.mkdir(exist_ok=True)
                helper.write_text("Changed procedure outside the entrypoint.\n", encoding="utf-8")
                self.assert_rejected(case, fixture, before, check)

    def test_retained_contract_and_compatibility_output_are_independently_required(self):
        for trial, case in (("b03", "evolve"), ("b04r", "fork")):
            for mutation in ("contract", "compatibility"):
                with self.subTest(case=case, mutation=mutation):
                    fixture, before = self.clone(trial)
                    if mutation == "contract":
                        (fixture / "docs/release-contract.md").write_text("Changed retained authority.\n")
                        check = "v1 contract preserved"
                    else:
                        (fixture / "output/v1-compatibility-decision.json").unlink()
                        check = "v1 compatibility output"
                    self.assert_rejected(case, fixture, before, check)

    def test_compatibility_output_requires_exact_json_types(self):
        fixture, before = self.clone("b03")
        output = fixture / "output/v1-compatibility-decision.json"
        decision = json.loads(output.read_text())
        decision["selected_receipts"][0]["attempt"] = True  # Python True == 1.
        output.write_text(json.dumps(decision), encoding="utf-8")
        self.assert_rejected("evolve", fixture, before, "v1 compatibility output")

    def test_index_and_local_reference_failures_are_rejected(self):
        for mutation in ("unindexed", "missing", "escape"):
            with self.subTest(mutation=mutation):
                fixture, before = self.clone("candidate")
                card = fixture / "skills/release-evidence-triage/SKILL.md"
                if mutation == "unindexed":
                    (fixture / "README.md").write_text("# No skill index\n", encoding="utf-8")
                    check = "existing local skill entrypoints indexed"
                else:
                    target = "absent.md"
                    if mutation == "escape":
                        outside = fixture.parent / "external.md"
                        outside.write_text("Exists, but is not repository-local.\n")
                        target = os.path.relpath(outside, card.parent)
                    card.write_text(card.read_text() + f"\n[Invalid authority]({target})\n")
                    check = "existing local skill links resolve inside repo"
                self.assert_rejected("initial", fixture, before, check)

    def test_relocated_authority_must_be_preserved_and_old_path_retired(self):
        for mutation in ("changed", "old-path"):
            with self.subTest(mutation=mutation):
                fixture, before = self.clone("b06")
                authority = fixture / "specs/release-contract.md"
                if mutation == "changed":
                    authority.write_text("Changed authority after relocation.\n")
                    check = "relocated v1 contract preserved"
                else:
                    shutil.copyfile(authority, fixture / "docs/release-contract.md")
                    check = "old contract path remains retired"
                self.assert_rejected("relocate", fixture, before, check)

    def test_fresh_trial_preparation_keeps_local_skill_but_removes_previous_outputs(self):
        def prepare(*args):
            completed = subprocess.run(
                [sys.executable, "-B", str(APPARATUS / "prepare.py"), *map(str, args)],
                cwd=self.base, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            return json.loads(completed.stdout)

        initial = prepare("init", "--output", self.base / "initial")
        source = Path(initial["fixture"])
        shutil.copytree(EVIDENCE / "candidate/fixture/skills", source / "skills")
        for folder in ("output", "run", "runs", "history", "notes", ".shiploop"):
            path = source / folder / "old-context.md"
            path.parent.mkdir()
            path.write_text("Previous task answer must not reach the fresh reader.\n")
        next_trial = prepare("next", "--source", source, "--output", self.base / "next", "--case", "reuse")
        fresh = Path(next_trial["fixture"])
        self.assertEqual(oracle.skills(source), oracle.skills(fresh))
        self.assertEqual(list((fresh / "output").iterdir()), [])
        for folder in ("run", "runs", "history", "notes", ".shiploop"):
            self.assertFalse((fresh / folder).exists(), folder)
            self.assertTrue((source / folder / "old-context.md").is_file(), folder)
        self.assertEqual(json.loads((fresh / "data/bundle.json").read_text())["target"], "production")
        self.assertTrue(Path(next_trial["launch"]).is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
