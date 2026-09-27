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
        self.assertTrue({"plan", "review", "review-bare"} <= set(s["frames"]))
        self.assertNotIn("Change only what a finding requires", s["frames"]["review-bare"])

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
            # Any frame that wraps {plan} is a review frame, whatever its name (review-bare once got an empty plan).
            m = R.build(Path(d) / "bare", s, {"prune": {"text": "FOCUS", "plans_arm": "v5"}}, frame="review-bare",
                        trials=1, plans_from=src, scenarios=["S01"], runtimes=["GAS"])
            self.assertTrue(m["reviews"])
            self.assertIn("THE PLAN", (Path(d) / "bare" / "prompts" / "S01_GAS_prune_1.txt").read_text())
            with self.assertRaises(ValueError):
                R.build(Path(d) / "none", s, {"prune": {"text": "F", "plans_arm": "missing"}}, frame="review",
                        trials=1, plans_from=src, scenarios=["S01"], runtimes=["GAS"])


class Outputs(unittest.TestCase):
    def test_revised_plan_extraction(self):
        self.assertEqual(R.plan_text("## Findings\nx\n## Revised plan\nY", True), "## Revised plan\nY")
        self.assertEqual(R.plan_text("no section", True), "")
        self.assertEqual(R.plan_text("whole", False), "whole")

    def test_parse_verdict(self):
        ok = '{"tier_chosen": "client-only", "criteria": {"P1": {"evidence": "q", "grade": "met"}}}'
        self.assertEqual(R.parse_verdict("text " + ok)["grades"], {"P1": "met"})
        self.assertIsNone(R.parse_verdict('{"criteria": {"P1": {"evidence": "q", "grade": "great"}}}'))
        self.assertIsNone(R.parse_verdict("not json"))


def C(mean, low, high, p=0.01, sm=None):
    """A paired comparison fixture: mean, 95% interval, Wilcoxon p and the scenario mean."""
    return {"mean": mean, "low": low, "high": high, "wilcoxon_p": p, "scenario_mean": mean if sm is None else sm}


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

    def test_scenario_clustering_widens_or_keeps_interval(self):
        v = {}
        for sid, bump in (("S01", "met"), ("S02", "missed"), ("S04", "met")):
            for k in range(6):
                v[f"{sid}_GAS_base_{k}"] = verdict({"P1": "partial"})
                v[f"{sid}_GAS_cand_{k}"] = verdict({"P1": bump})
        cell = R.paired(v, "cand", "base"); clus = R.paired(v, "cand", "base", cluster="scenario")
        self.assertEqual(cell["mean"], clus["mean"])
        self.assertGreaterEqual(clus["high"] - clus["low"], cell["high"] - cell["low"])

    def test_parse_value(self):
        good = ('{"added": [{"item": "Resign button", "for": "games need an exit", "against": "not asked", "verdict": "valuable"}],'
                ' "removed": [{"item": "retry", "for": "reliability", "against": "", "verdict": "loss"}]}')
        self.assertEqual(R.parse_value("x " + good)["added"][0]["verdict"], "valuable")
        self.assertIsNone(R.parse_value('{"added": [{"item": "a", "verdict": "great"}], "removed": []}'))
        self.assertIsNone(R.parse_value('{"added": []}'))
        self.assertGreaterEqual(R._overlap("Resign button and resign result state not requested", "Resign button"), 0.3)

    def test_parse_diff(self):
        good = '{"removed_required": 0, "added_unrequested": 2, "contradictions": 0, "invented_numbers": 1}'
        self.assertEqual(R.parse_diff("x " + good)["added_unrequested"], 2)
        self.assertIsNone(R.parse_diff('{"removed_required": -1, "added_unrequested": 0, "contradictions": 0, "invented_numbers": 0}'))
        self.assertIsNone(R.parse_diff('{"removed_required": 0}'))

    def test_adversarial_fixtures_never_ship(self):
        # From the adversarial review of rubric-eval itself (F1, F3, F7): each of these must not ship.
        up = C(3, 1, 5)
        g = ["safeguards", "proportion"]
        ok = C(0, -1, 1, p=0.9)
        self.assertTrue(R.decide({"overall": up, "safeguards": ok, "proportion": ok}, g, 2.0, scenarios=19)["ship"])
        bad_mean = C(-6, -12, 1, p=0.2)   # interval not wholly below 0, but mean worse than the noise
        self.assertFalse(R.decide({"overall": up, "safeguards": bad_mean, "proportion": ok}, g, 2.0, scenarios=19)["ship"])
        self.assertFalse(R.decide({"overall": up, "proportion": ok}, g, 2.0, scenarios=19)["ship"])  # guardrail missing
        d = R.decide({"overall": up, "safeguards": ok, "proportion": ok}, g, 2.0, scenarios=19,
                     checks=["platform errors rose significantly"])
        self.assertFalse(d["ship"]); self.assertTrue(d["reasons"][0].startswith("blocked"))  # the block leads (F8)
        self.assertFalse(R.decide({"overall": up, "safeguards": ok, "proportion": ok}, g, 2.0, scenarios=1)["ship"])
        self.assertFalse(R.decide({"overall": up, "safeguards": ok, "proportion": ok}, g, None, scenarios=19)["ship"])  # unmeasured judge

    def test_condition_is_recorded_and_checked(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "manifest.json").write_text(json.dumps({"arms": {"base": {}, "cand": {}}}))
            self.assertTrue(R.check_condition(d, "base"))          # no recorded condition: void
            (Path(d) / "manifest.json").write_text(json.dumps({"condition": {"model": "sonnet", "tools": ""},
                                                               "arms": {"base": {"role": "input"}, "cand": {}}}))
            self.assertEqual(R.check_condition(d, "base"), [])
            self.assertTrue(R.check_condition(d, "cand"))          # an input arm that is not the baseline

    def test_mixed_judges_void_the_comparison(self):
        s = R.load_suite(SUITE)
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "judge").mkdir(); (Path(d) / "prompts").mkdir()
            (Path(d) / "manifest.json").write_text(json.dumps({"condition": {"model": "sonnet", "tools": ""}, "arms": {}}))
            for i, (arm, j) in enumerate([("base", "sonnet"), ("cand", "grok")] * 3):
                v = verdict({"P1": "met"}); v["judge_model"] = j
                (Path(d) / "judge" / f"S01_GAS_{arm}_{i}.json").write_text(json.dumps(v))
            r = R.analyze(d, s, "base")
            self.assertTrue(any("more than one judge" in p for p in r["condition_problems"]))

    def test_decide_quality_then_tokens_then_time(self):
        eq = C(0.2, -1.5, 1.8, p=0.6)                          # within the judge's noise of 2 points
        fewer, more, same = C(-900, -1200, -600), C(900, 600, 1200), C(10, -300, 320, p=0.7)
        d = R.decide({"overall": C(4, 1, 7)}, [], 2.0, tokens=more, scenarios=19)
        self.assertEqual((d["winner"], d["decided_by"]), ("arm", "quality"))   # a material difference trumps cost
        d = R.decide({"overall": C(-4, -7, -1)}, [], 2.0, tokens=fewer, scenarios=19)
        self.assertEqual((d["winner"], d["decided_by"]), ("baseline", "quality"))
        d = R.decide({"overall": eq}, [], 2.0, tokens=fewer, seconds=more, scenarios=19)
        self.assertEqual((d["winner"], d["decided_by"]), ("arm", "tokens"))    # tokens outrank time
        d = R.decide({"overall": eq}, [], 2.0, tokens=more, scenarios=19)
        self.assertEqual((d["winner"], d["ship"]), ("baseline", False))
        d = R.decide({"overall": eq}, [], 2.0, tokens=same, seconds=fewer, scenarios=19)
        self.assertEqual((d["winner"], d["decided_by"]), ("arm", "time"))
        d = R.decide({"overall": eq}, [], 2.0, tokens=same, seconds=same, scenarios=19)
        self.assertEqual((d["winner"], d["decided_by"]), ("baseline", "tie"))   # a change must earn its place
        d = R.decide({"overall": C(1, -3, 5, p=0.3)}, [], 2.0, tokens=fewer, scenarios=19)
        self.assertIsNone(d["winner"]); self.assertIn("inconclusive", d["reasons"][0])
        self.assertIsNone(R.decide({"overall": C(4, 1, 7, p=0.2)}, [], 2.0, scenarios=19)["winner"])  # rank test must agree
        self.assertIsNone(R.decide({"overall": C(4, 1, 7, sm=-0.5)}, [], 2.0, scenarios=19)["winner"])  # and agree in direction
        d = R.decide({"overall": eq}, [], 2.0, tokens=fewer, checks=["na rates differ"], scenarios=19)
        self.assertIsNone(d["winner"]); self.assertFalse(d["ship"])            # checks block a cost win too
        d = R.decide({"overall": eq}, [], 2.0, tokens=C(-900, -1200, -600, p=0.3), scenarios=19)
        self.assertEqual(d["decided_by"], "tie")          # a cost win needs the rank test too (review F2)

    def test_near_identical_is_checked_before_a_quality_win(self):
        # Adversarial review F1: a significant difference that lies wholly inside the judge's noise is
        # near-identical, so cost decides it.
        a = C(0.8, 0.2, 1.5, p=0.01)
        d = R.decide({"overall": a}, [], 2.07, tokens=C(-5000, -7000, -3000), scenarios=19)
        self.assertEqual((d["winner"], d["decided_by"]), ("arm", "tokens"))
        d = R.decide({"overall": a}, [], 2.07, tokens=C(5000, 3000, 7000), scenarios=19)
        self.assertEqual((d["winner"], d["decided_by"]), ("baseline", "tokens"))

    def test_scale_kappa_and_wilcoxon(self):
        self.assertEqual(R.score(verdict({"P1": "met", "P3": "partial", "D1": "missed", "D2": "na"})), 50.0)
        self.assertEqual(R.kappa([("met", "met"), ("partial", "partial"), ("missed", "missed")] * 3), 1.0)
        # linear-weighted kappa, checked by hand: po = 5/6, pe = 1/2, kappa = (5/6 - 1/2) / (1/2) = 0.667
        self.assertEqual(R.kappa([("met", "met"), ("met", "partial"), ("missed", "missed")]), 0.667)
        self.assertEqual(R.landis_koch(0.835), "almost perfect"); self.assertEqual(R.landis_koch(0.443), "moderate")
        self.assertLess(R.wilcoxon([1, 2, 3, 4, 5, 6, 7, 8]), 0.05)
        self.assertGreater(R.wilcoxon([1, -2, 3, -4, 5, -6, 7, -8]), 0.5)
        self.assertIsNone(R.wilcoxon([1, 2]))

    def test_build_writes_an_unreviewed_input_baseline(self):
        s = R.load_suite(SUITE)
        with tempfile.TemporaryDirectory() as d:
            plans = Path(d) / "plans" / "out"; plans.mkdir(parents=True)
            (plans / "S01_GAS_v5_1.json").write_text(json.dumps({"text": "PLAN " * 200}))
            run = Path(d) / "rev"
            m = R.build(run, s, {"cand": {"text": "focus", "plans_arm": "v5"}}, frame="review-bare", trials=1,
                        plans_from=Path(d) / "plans", input_arm="none")
            self.assertEqual(m["arms"]["none"]["role"], "input")
            out = json.loads((run / "out" / "S01_GAS_none_1.json").read_text())["text"]
            self.assertEqual(R.words(R.plan_text(out, True)), 203)   # the plan, under "## Revised plan"
            self.assertEqual(R.check_condition(run, "none"), ["manifest records no run condition (model, tools); rerun with this version of `run`"])

    def test_quote_check_lowers_unsupported_grades(self):
        plan = "## Revised plan\nState lives in the **browser tab**; a LockService lock guards writes."
        v = {"criteria": {"P1": {"evidence": "state lives in the browser tab", "grade": "met"},
                          "D1": {"evidence": "LockService lock ... guards writes", "grade": "met"},
                          "D2": {"evidence": "retries with exponential backoff", "grade": "met"},
                          "D3": {"evidence": "a queue absorbs bursts", "grade": "partial"},
                          "D4": {"evidence": "none", "grade": "missed"}}}
        v["grades"] = {c: e["grade"] for c, e in v["criteria"].items()}
        R.verify_quotes(v, plan)
        self.assertEqual(v["grades"], {"P1": "met", "D1": "met", "D2": "partial", "D3": "missed", "D4": "missed"})
        self.assertEqual(v["quote_check"]["unverified"], ["D2", "D3"])
        self.assertEqual((v["criteria"]["D2"]["grade"], v["criteria"]["D2"]["judge_grade"]), ("partial", "met"))
        self.assertTrue(R.quote_found("the player\u2019s board -- hidden", "The player's board: hidden."))  # punctuation

    def test_grok_calls_name_a_tool_allowlist(self):
        # Grok reads `--tools ""` as no restriction (shell and file tools included); every call must name
        # an allowlist and remove the meta-tools that load other tools.
        seen = []
        class Done:
            stdout = '{"text": "ok", "usage": {"input_tokens": 3, "output_tokens": 2}}'
        real = R.subprocess.run
        R.subprocess.run = lambda argv, **kw: (seen.append(argv), Done())[1]
        old_home = R._grok_home
        R._grok_home = lambda: Path(tempfile.gettempdir())
        try:
            r = R.call_full("grok", "hi"); R.call_full("grok", "hi", tools="Read")
        finally:
            R.subprocess.run = real; R._grok_home = old_home
        self.assertEqual((r["text"], r["input_tokens"], r["output_tokens"]), ("ok", 3, 2))
        for argv, allowed in zip(seen, ("todo_write", "read_file,list_dir,grep")):
            self.assertEqual(argv[argv.index("--tools") + 1], allowed)
            self.assertEqual(argv[argv.index("--disallowed-tools") + 1], "search_tool,use_tool")
            self.assertIn("-p", argv); self.assertNotIn("--prompt-file", argv)   # no prompt file on disk
            self.assertNotIn("--always-approve", argv)
        self.assertNotIn("--sandbox", seen[1])      # cannot start here; reads are audited instead

    def test_outside_paths_flags_reads_beyond_the_call_directory(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as cwd:
            log = Path(home) / ".grok" / "sessions" / "x" / "sid1"; log.mkdir(parents=True)
            ev = lambda tool, inp: json.dumps({"params": {"update": {"sessionUpdate": "tool_call", "title": tool, "rawInput": inp}}})
            (log / "updates.jsonl").write_text("\n".join([
                ev("read_file", {"target_file": f"{cwd}/references/a.md"}), ev("read_file", {"target_file": "references/b.md"}),
                ev("grep", {"pattern": "google/script|a/b", "path": "references"}),       # a slash in a pattern is not a path
                ev("list_dir", {"target_directory": "/private/tmp"}), ev("list_dir", {"variant": "ListDir", "target_directory": "../other"}),
                ev("run_terminal_command", {"command": "ls"})]))
            self.assertEqual(R.outside_paths(Path(home), "sid1", cwd), ["../other", "/private/tmp", "tool:run_terminal_command"])
            self.assertIsNone(R.outside_paths(Path(home), "missing", cwd))

    def test_costs_compare_paired_and_against_a_free_input(self):
        vals = {f"S0{i}_GAS_base_1": 1000.0 for i in range(1, 9)} | {f"S0{i}_GAS_cand_1": 700.0 + i for i in range(1, 9)}
        c = R.paired_values(vals, "cand", "base", "scenario")
        self.assertLess(c["high"], 0); self.assertEqual(c["arm_lower"], 8)
        z = R.paired_values(vals, "cand", "base", "scenario", baseline_zero=True)   # an unreviewed plan costs no review
        self.assertGreater(z["low"], 0)


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
