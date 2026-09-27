#!/usr/bin/env python3
"""Hermetic checks for the rubric-eval and adversarial-review skills; no model calls."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "rubric-eval" / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "adversarial-review" / "scripts"))
import rubric_eval as R  # noqa: E402
import adversarial_review as A  # noqa: E402

SUITE = ROOT / "skills" / "rubric-eval" / "suites" / "architecture"


def verdict(grades, tier="client-only"):
    return {"tier_chosen": tier, "grades": grades, "criteria": {c: {"evidence": "x", "grade": g} for c, g in grades.items()}}


class Extract(unittest.TestCase):
    def test_exact_constant_and_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "m.py"
            p.write_text('X = """\\\nline one {brace}\nline two\n"""\nY = 3\n')
            self.assertEqual(R.extract(p, "X"), "line one {brace}\nline two\n")
            self.assertEqual(R.extract(p), p.read_text())
            with self.assertRaises(ValueError):
                R.extract(p, "Y")
            with self.assertRaises(ValueError):
                R.extract(p, "Z")


class Suite(unittest.TestCase):
    def test_architecture_suite_is_consistent(self):
        s = R.load_suite(SUITE)
        crit = s["rubric"]["criteria"]
        for g, cs in s["rubric"]["groups"].items():
            self.assertTrue(set(cs) <= set(crit), g)
        self.assertTrue(set(s["rubric"]["guardrails"]) <= set(s["rubric"]["groups"]))
        tiers = s["scenarios"]["tiers"]
        for sc in s["scenarios"]["scenarios"]:
            self.assertIn(sc["tier"], tiers, sc["id"])
            self.assertTrue(set(sc["applies"] + sc.get("applies_ui", [])) <= set(crit), sc["id"])
            for rt in sc["runtimes"] + sc.get("runtimes_ext", []):
                self.assertIn(rt, s["scenarios"]["runtimes"], sc["id"])
                self.assertIn(rt, s["scenarios"]["runtime_names"], sc["id"])
        self.assertEqual(set(s["frames"]), {"plan", "review"})

    def test_fill_keeps_braces_in_values(self):
        self.assertEqual(R.fill("a {arm} b {plan}", arm="{x}", plan="{arm}"), "a {x} b {arm}")

    def test_build_writes_every_cell_arm_trial_with_manifest(self):
        s = R.load_suite(SUITE)
        with tempfile.TemporaryDirectory() as d:
            m = R.build(d, s, {"base": {"text": "A {x}", "source": "a"}, "cand": {"text": "B", "source": "b"}},
                        trials=2, scenarios=["S01"])
            files = sorted(p.name for p in (Path(d) / "prompts").glob("*.txt"))
            s01 = next(x for x in s["scenarios"]["scenarios"] if x["id"] == "S01")
            self.assertEqual(len(files), len(s01["runtimes"] + s01.get("runtimes_ext", [])) * 2 * 2)
            self.assertIn("S01_GAS_base_1.txt", files)
            self.assertIn("A {x}", (Path(d) / "prompts" / "S01_GAS_base_1.txt").read_text())
            self.assertEqual(m["arms"]["base"]["sha"], R.sha("A {x}"))
            with self.assertRaises(ValueError):
                R.build(d, s, {"bad_name": {"text": "x"}})

    def test_review_frame_takes_plans_from_another_run(self):
        s = R.load_suite(SUITE)
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "plans"; (src / "out").mkdir(parents=True)
            (src / "out" / "S01_GAS_v5_1.json").write_text(json.dumps({"text": "THE PLAN"}))
            R.build(Path(d) / "rev", s, {"prune": {"text": "FOCUS", "plans_arm": "v5"}}, frame="review",
                    trials=1, plans_from=src, scenarios=["S01"], runtimes=["GAS"])
            p = (Path(d) / "rev" / "prompts" / "S01_GAS_prune_1.txt").read_text()
            self.assertIn("THE PLAN", p); self.assertIn("FOCUS", p)


class Outputs(unittest.TestCase):
    def test_revised_plan_extraction(self):
        self.assertEqual(R.plan_text("## Findings\nx\n## Revised plan\nY", "review"), "## Revised plan\nY")
        self.assertEqual(R.plan_text("no section", "review"), "")
        self.assertEqual(R.plan_text("whole", "plan"), "whole")

    def test_parse_verdict(self):
        ok = '{"tier_chosen": "client-only", "criteria": {"P1": {"evidence": "q", "grade": "met"}}}'
        self.assertEqual(R.parse_verdict("text " + ok)["grades"], {"P1": "met"})
        self.assertIsNone(R.parse_verdict('{"criteria": {"P1": {"evidence": "q", "grade": "great"}}}'))
        self.assertIsNone(R.parse_verdict("not json"))


class Statistics(unittest.TestCase):
    def verdicts(self):
        v = {}
        for i in range(12):
            v[f"S01_GAS_base_{i}"] = verdict({"P1": "partial", "P3": "met", "D1": "met"})
            v[f"S01_GAS_cand_{i}"] = verdict({"P1": "met", "P3": "met", "D1": "met" if i % 4 else "missed"})
        return v

    def test_paired_counts_and_interval(self):
        c = R.paired(self.verdicts(), "cand", "base")
        self.assertEqual(c["n"], 12)
        self.assertEqual(c["won"] + c["lost"], 12)
        self.assertLessEqual(c["low"], c["mean"]); self.assertLessEqual(c["mean"], c["high"])
        self.assertEqual(R.paired(self.verdicts(), "cand", "base"), c)  # deterministic

    def test_decide(self):
        up = {"mean": .03, "low": .01, "high": .05}
        self.assertTrue(R.decide({"overall": up, "proportion": {"mean": 0, "low": -.03, "high": .02}}, ["proportion"])["ship"])
        self.assertFalse(R.decide({"overall": {"mean": .02, "low": -.001, "high": .04}}, [])["ship"])
        d = R.decide({"overall": up, "proportion": {"mean": -.05, "low": -.08, "high": -.03}}, ["proportion"])
        self.assertFalse(d["ship"]); self.assertIn("proportion", d["reasons"][0])


class Findings(unittest.TestCase):
    def good(self):
        return {"change": "c", "reviewer": "grok", "findings": [
            {"id": "F1", "claim": "x", "severity": "high", "category": "regression", "testable": True,
             "experiment": {"type": "scenario", "description": "d", "success": "s"}},
            {"id": "F2", "claim": "y", "severity": "low", "category": "wording", "testable": False}]}

    def test_valid_and_invalid(self):
        self.assertEqual(A.validate(self.good()), [])
        bad = self.good(); bad["findings"][0]["experiment"] = {"type": "vibes"}
        bad["findings"][1]["severity"] = "urgent"
        errs = A.validate(bad)
        self.assertTrue(any("experiment" in e for e in errs)); self.assertTrue(any("severity" in e for e in errs))
        self.assertEqual(A.validate({"findings": []})[:2], ["missing change", "missing reviewer"])

    def test_prompt_and_markdown(self):
        p = A.build_prompt("n", "CHANGE {x}", "EVID", 3)
        self.assertIn("CHANGE {x}", p); self.assertIn("at most 3 findings", p); self.assertIn('{"findings"', p)
        md = A.to_markdown(self.good())
        self.assertIn("F1 (high, regression)", md); self.assertIn("Not testable", md)


if __name__ == "__main__":
    unittest.main(verbosity=1)
