#!/usr/bin/env python3
"""Hermetic arithmetic and evidence-preservation checks; no model or archive access."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import compare


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((HERE / "replay.json").read_text())

    def test_retained_arithmetic_and_distinct_regression(self):
        result = compare.compare(self.data)
        self.assertEqual((result["valid_grades"], result["attempted_grades"]), (13, 14))
        api, cli = result["pairs"]
        self.assertTrue(api["valid_four_grades"] and cli["valid_four_grades"])
        self.assertEqual(api["confirmed_regressions"], ["verification_closure"])
        self.assertEqual(api["confirmed_gains"], [])
        self.assertEqual(api["dimensions"]["acceptance_actionability"]["comparison"], "judge_disagreement")
        self.assertTrue(all(v["comparison"] == "equal_anchors" for v in cli["dimensions"].values()))
        self.assertTrue(all(v["comparison"] == "equal_anchors" for layers in api["coverage"].values() for v in layers.values()))

    def test_one_anchor_is_a_gain_without_large_threshold(self):
        self.assertEqual(compare.contrast([2, 2], [3, 3]), "gain")
        self.assertEqual(compare.contrast([2, 2], [1, 1]), "regression")

    def test_simultaneous_gain_and_regression_do_not_cancel(self):
        for row in self.data["records"]:
            if row["trial"] == "13": row["dimensions"]["prerequisite_handoff"] = 2
        pair = compare.compare(self.data)["pairs"][0]
        self.assertEqual(pair["confirmed_gains"], ["prerequisite_handoff"])
        self.assertEqual(pair["confirmed_regressions"], ["verification_closure"])

    def test_duplicate_pass_is_rejected(self):
        self.data["records"].append(copy.deepcopy(self.data["records"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate trial/pass"):
            compare.compare(self.data)

    def test_missing_pass_is_unknown_not_tie(self):
        self.data["records"] = [r for r in self.data["records"] if (r["trial"], r["pass"]) != ("14", 2)]
        result = compare.compare(self.data)
        self.assertEqual(result["missing_passes"], [{"trial": "14", "pass": 2}])
        self.assertTrue(all(v["comparison"] == "unknown" for v in result["pairs"][0]["dimensions"].values()))

    def test_invalid_grade_cannot_confirm_pair(self):
        row = next(r for r in self.data["records"] if r["trial"] == "14")
        row["status"] = "invalid"
        self.assertFalse(compare.compare(self.data)["pairs"][0]["valid_four_grades"])

    def test_null_and_disagreement_preserved(self):
        self.assertEqual(compare.contrast([None, None], [0, 0]), "unknown")
        self.assertEqual(compare.contrast([2, 3], [3, 3]), "judge_disagreement")
        self.assertEqual(compare.contrast([3, 3], [3, 3]), "equal_anchors")

    def test_minor_findings_and_qualitative_benefits_survive_ties(self):
        result = compare.compare(self.data)
        self.assertEqual(result["qualitative_observations"], self.data["qualitative_observations"])
        self.assertTrue(any(r["items"] for r in result["pairs"][1]["findings"]["candidate"]))
        self.assertIn("not automatic vetoes", result["pairs"][1]["retention"])

    def test_all_resource_components_remain_visible(self):
        api, cli = compare.compare(self.data)["pairs"]
        self.assertEqual(api["resources"]["disposition"], "observed_resource_tradeoff")
        self.assertAlmostEqual(api["resources"]["deltas"]["uncached_input_tokens"]["percent"], 8.374495967741936)
        self.assertEqual(cli["resources"]["disposition"], "candidate_observed_componentwise_reduction")

    def test_missing_nonfinite_bool_and_zero_resource_values(self):
        row = {k: 0 for k in compare.RESOURCES}
        result = compare.resource_delta(row, row)
        self.assertTrue(all(x["percent"] is None for x in result["deltas"].values()))
        for bad in [None, -1, True, float("nan"), float("inf")]:
            with self.subTest(bad=bad):
                self.assertEqual(compare.resource_delta(row, {**row, "seconds": bad})["disposition"], "unknown")

    def test_invalid_anchor_and_obligation_set_rejected(self):
        row = next(r for r in self.data["records"] if r["status"] == "valid" and r["trial"] == "14")
        for bad in [True, 4, -1, 2.5]:
            with self.subTest(bad=bad):
                row["dimensions"]["acceptance_actionability"] = bad
                with self.assertRaises(ValueError): compare.compare(self.data)
        row["dimensions"]["acceptance_actionability"] = 3
        row["obligations"] = {}
        with self.assertRaisesRegex(ValueError, "obligation IDs differ"):
            compare.compare(self.data)

    def test_clean_external_cli_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            command = [sys.executable, "-B", str(HERE / "compare.py"), str(HERE / "replay.json"), "--output", str(output)]
            run = subprocess.run(command, cwd=directory, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(output.read_text()), compare.compare(self.data))
            before = output.read_bytes()
            run = subprocess.run(command, cwd=directory, capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(output.read_bytes(), before)



if __name__ == "__main__":
    unittest.main()
