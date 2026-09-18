#!/usr/bin/env python3
"""No-model checks for the decision-driven probe study adapter."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("shiploop_probe_decisions_study_test", HERE / "study.py")
assert SPEC and SPEC.loader
study = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(study)


FIXTURE = '''\
from pathlib import Path

CASES = {name: {"task": "Investigate " + name, "required": ("required " + name,), "forbidden": ("forbidden " + name,)} for name in ("f1", "f2", "f3", "f4")}

def materialize(family, root, mutant=False):
    (root / "README.md").write_text("synthetic " + family + "\\n")
    (root / "probe.py").write_text("print('safe')\\n")
    return {"family": family, "mutant": mutant}

def calibrate(root):
    root.mkdir(parents=True, exist_ok=True)
    (root / "calibration.json").write_text('{"checked": true}\\n')
    return {"passed": True, "fixture": "synthetic", "limits": "synthetic only", "families": {name: {"passed": True, "reference": {"observation": "reference " + name}} for name in CASES}}
'''


class StudyAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-probe-study-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixture = self.root / "fixtures.py"
        self.fixture.write_text(FIXTURE)
        self.baseline = self.root / "baseline.md"
        self.cue = self.root / "cue.txt"
        self.candidate = self.root / "candidate.md"
        self.baseline.write_text("Header\ninstall a dependency.  Leave unsupported questions open.\nTail\n")
        self.cue.write_text("Cue sentence.\n")
        self.candidate.write_text(study.exact_candidate(self.baseline.read_text(), self.cue.read_text()))
        self.plan = self.root / "plan.md"
        self.plan.write_text("# Preregistered plan\n")
        self.old_files = study.FROZEN_FILES
        self.old_prompts = study.BASELINE_PROMPT, study.CANDIDATE_PROMPT, study.CANDIDATE_CUE
        study.FROZEN_FILES = {**study.FROZEN_FILES, "fixtures.py": self.fixture}
        self.addCleanup(self.restore_files)

    def restore_files(self) -> None:
        study.FROZEN_FILES = self.old_files
        study.BASELINE_PROMPT, study.CANDIDATE_PROMPT, study.CANDIDATE_CUE = self.old_prompts

    def initialize(self) -> Path:
        target = self.root / "study"
        study.BASELINE_PROMPT, study.CANDIDATE_PROMPT, study.CANDIDATE_CUE = self.baseline, self.candidate, self.cue
        result = study.initialize(target, self.candidate, self.plan)
        self.assertEqual(result["status"], "ready_to_prepare")
        self.assertEqual(study.validate(target), study.validate(target))
        return target

    def test_freezes_prompts_references_helpers_and_calibration(self) -> None:
        target = self.initialize()
        manifest = (target / "frozen-inputs.json").read_text()
        self.assertIn("guides/baseline-research-prompt.md", manifest)
        self.assertIn("guides/candidate-research-prompt.md", manifest)
        self.assertIn("guides/references/research-loop.md", manifest)
        self.assertIn("frozen/runner.py", manifest)
        self.assertIn("frozen/fixtures.py", manifest)
        self.assertIn("guides/candidate-cue.txt", manifest)
        self.assertTrue((target / "private" / "fixture-calibration" / "calibration.json").is_file())

    def test_private_family_judge_packets_bind_exact_calibrated_case_rules(self) -> None:
        target = self.initialize()
        state = json.loads((target / "study.json").read_text())
        self.assertEqual(set(state["judge_packet_hashes"]), {"f1", "f2", "f3", "f4"})
        first = json.loads(study.validate_private_judge_packet(target, "f1").read_text())
        second = json.loads(study.validate_private_judge_packet(target, "f2").read_text())
        self.assertEqual(first["task"], "Investigate f1")
        self.assertEqual(first["required"], ["required f1"])
        self.assertEqual(first["forbidden"], ["forbidden f1"])
        self.assertEqual(first["calibrated_reference_observations"], {"observation": "reference f1"})
        self.assertNotEqual(first["task"], second["task"])

    def test_private_packet_reconstruction_rejects_packet_and_mutable_state_tamper(self) -> None:
        target = self.initialize()
        packet = study.validate_private_judge_packet(target, "f1")
        altered = json.loads(packet.read_text())
        altered["task"] = "coordinated tamper"
        packet.write_text(json.dumps(altered))
        state_path = target / "study.json"
        state = json.loads(state_path.read_text())
        state["judge_packet_hashes"]["f1"] = study.sha256(packet)
        state_path.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError, "contents do not match"):
            study.validate_private_judge_packet(target, "f1")

    def test_prepares_matched_pairs_and_caps_preregistered_replications(self) -> None:
        target = self.initialize()
        prepared = []
        for family in ("f1", "f2", "f3", "f4"):
            prepared.extend(study.prepare_pair(target, family))
        self.assertEqual(prepared, [f"trial-{number:02d}" for number in range(1, 9)])
        state = __import__("json").loads((target / "study.json").read_text())
        self.assertEqual({entry["variant"] for entry in state["arms"].values()}, {"baseline", "candidate"})
        self.assertTrue(all((target / "arms" / name / "workspace" / "guidance" / "research-prompt.md").is_file() for name in prepared))
        self.assertTrue(all((target / "arms" / name / "workspace" / "guidance" / "research-loop.md").is_file() for name in prepared))
        self.assertEqual(len(study.prepare_pair(target, "f1", 1)), 2)
        self.assertEqual(len(study.prepare_pair(target, "f2", 1)), 2)
        with self.assertRaisesRegex(ValueError, "maximum twelve contexts"):
            study.prepare_pair(target, "f3", 1)

    def test_mutated_frozen_input_blocks_preparation(self) -> None:
        target = self.initialize()
        (target / "guides" / "candidate-research-prompt.md").write_text("changed\n")
        with self.assertRaisesRegex(ValueError, "hash"):
            study.prepare_pair(target, "f1")

    def test_candidate_must_be_exact_single_cue_insertion(self) -> None:
        self.candidate.write_text(self.candidate.read_text() + "unexpected\n")
        with self.assertRaisesRegex(ValueError, "exactly one approved cue"):
            self.initialize()

    def test_optional_preregistered_prompt_hash_must_match(self) -> None:
        self.plan.write_text("baseline SHA-256: " + "0" * 64 + "\n")
        with self.assertRaisesRegex(ValueError, "baseline prompt hash"):
            self.initialize()

    def test_run_request_rejects_rogue_duplicate_and_tampered_arm_inputs(self) -> None:
        target = self.initialize()
        arms = study.prepare_pair(target, "f1")
        with self.assertRaisesRegex(ValueError, "not prepared"):
            study.validate_run_request(target, "rogue-arm", 1)
        with self.assertRaisesRegex(ValueError, "unique"):
            study.validate_run_request(target, f"{arms[0]},{arms[0]}", 1)
        with self.assertRaisesRegex(ValueError, "parallel"):
            study.validate_run_request(target, arms[0], 0)
        (target / "arms" / arms[0] / "input-hashes.json").write_text("{}\n")
        with self.assertRaisesRegex(ValueError, "frozen input hash mismatch"):
            study.validate_run_request(target, arms[0], 1)

    def test_prepared_completed_pair_collects_a_blind_bundle_without_a_model(self) -> None:
        target = self.initialize()
        arms = study.prepare_pair(target, "f1")
        receipts = []
        for name in arms:
            arm = target / "arms" / name
            workspace, run = arm / "workspace", arm / "run"
            (workspace / "REPORT.md").write_text(f"# Report {name}\n", encoding="utf-8")
            run.mkdir()
            (run / "metadata.json").write_text(json.dumps({
                "completion": {"status": "completed"}, "fixture_edits": {},
                "contexts": [{"exit_code": 0, "termination_reason": None, "elapsed_seconds": 1}],
                "observed_actions": {"observed_unique": 1},
                "gateway_ledger": {"records": [{"phase": "exploration"}]},
            }), encoding="utf-8")
            receipts.append({"arm": name, "event": "workspace_call", "is_error": False,
                             "request": {"name": "workspace", "arguments": {"operation": "list", "path": ""}},
                             "result": {"call": 1, "entries": ["README.md"]}})
        (target / "receipts.jsonl").write_text("".join(json.dumps(row) + "\n" for row in receipts), encoding="utf-8")
        self.assertEqual(study.collect(target, "f1"), 0)
        self.assertTrue((target / "blind" / "f1-r0" / "bundle-compact.md").is_file())
        judge_input = target / "blind" / "f1-r0" / "ready-to-evaluate.md"
        text = judge_input.read_text(encoding="utf-8")
        self.assertIn("Independent blind research-decision review", text)
        self.assertIn("neutral_bundle_sha256", text)
        self.assertIn("Investigate f1", text)
        self.assertIn("# Report", text)
        self.assertNotIn("baseline/candidate mapping", text.replace("contains no baseline/candidate mapping", ""))

    def test_leakage_scan_rejects_comparison_identity_but_not_ordinary_candidate_word(self) -> None:
        target = self.initialize()
        arms = study.prepare_pair(target, "f1")
        report = target / "arms" / arms[0] / "workspace" / "REPORT.md"
        report.write_text("The candidate implementation needs a local check.\n")
        self.assertEqual(study.report_leaks(target, "f1", 0), [])
        report.write_text("The candidate trial said to inspect this.\n")
        self.assertTrue(study.report_leaks(target, "f1", 0))


if __name__ == "__main__":
    unittest.main()
