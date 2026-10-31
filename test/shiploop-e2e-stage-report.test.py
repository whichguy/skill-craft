#!/usr/bin/env python3
"""The stage suite's live report (test/shiploop_e2e/stage_suite/stage_report.py; docs/plans/shiploop-stage-suite.md), over results
roots written by hand: no host, no ShipLoop, no scenario folder. Hermetic: own temp dirs, nothing else read.

- Reading a root: a row per scenario with the counts of each planted id caught and control held, of overshoots and of passes, the
  mean value and the driver; a sample is graded only when its stage-result.json is whole and well-formed; every other sample is
  not run, with the reason (error.txt, a half-written result, a result of the wrong shape, a folder the plan named that is not
  there), counts in the denominator and is never a catch, a hold or a pass; a result that claims a pass its verdicts do not show
  is not one; folders that are not samples (``.logs`` is not read; a name that is not a sample number, ``01`` or a non-ASCII digit
  included, is not counted and is listed as ignored); a result that checked no id, lacks an id the plan names, has a value outside
  0 to 1 or a missing one is not run; the JSON value counts a sample not run as 0; a root that mixes plugin builds says so.
- The plan (live-plan.json): the samples planned and the pass rule give the rule column (met, NOT MET, or ``-`` without a plan).
- The text: the columns, ``-`` for an id a scenario does not have, the not-run lines, a note for a root that mixes drivers.
- compare: per-cell counts and changes for roots of one driver; a refusal naming both drivers when host, backend, model or effort
  differ (SPEC S-12), when a root mixes drivers, or when a root has no graded sample; a scenario in one root only is marked.
- The module reads files only and uses only the standard library, and sits outside the evaluator digest and the qualification snapshot.
"""
from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "test" / "shiploop_e2e"
MODULE = HARNESS / "stage_suite" / "stage_report.py"
sys.path.insert(0, str(HARNESS / "stage_suite"))
sys.path.insert(0, str(HARNESS))
import boundary  # noqa: E402
import stage_report as report  # noqa: E402

BROKEN = ("validate-existing", "broken-works-small-fix")
WRONG = ("validate-existing", "wrong-check")
GOOD = {
    "host": "codex", "backend": None, "model": "gpt-6.1-terra", "effort": "xhigh",
    "verdicts": {"process": True, "accepted": True, "no_overshoot": True, "oracle": True},
    "caught": {"P1": True}, "held": {"C1": True, "C2": True}, "value": 1.0, "pass": True}


def sample(root: Path, scenario: tuple, number: int | str, **changes) -> Path:
    """Write sample `number` of `scenario` under `root` with GOOD and `changes` (a dict value is merged one level, None removes)."""
    document = copy.deepcopy(GOOD)
    for key, value in changes.items():
        if value is None:
            document.pop(key, None)
        elif isinstance(value, dict) and isinstance(document.get(key), dict):
            document[key].update(value)
        else:
            document[key] = value
    folder = Path(root).joinpath(*scenario, str(number))
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "stage-result.json").write_text(json.dumps(document))
    return folder


def plan(root: Path, scenarios: dict) -> None:
    Path(root, "live-plan.json").write_text(json.dumps({"scenarios": scenarios}))


def row(document: dict, scenario: tuple) -> dict:
    return next(item for item in document["scenarios"] if item["id"] == "/".join(scenario))


class Temp(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="stage-report-")
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)

    def root(self, name: str = "root") -> Path:
        path = self.temp / name
        path.mkdir()
        return path


# ------------------------------------------------------------------------------------------------------------------- the counts

class Counts(Temp):
    def setUp(self):
        super().setUp()
        self.root_ = self.root()
        sample(self.root_, BROKEN, 1)
        sample(self.root_, BROKEN, 2, caught={"P1": False}, value=2 / 3, **{"pass": False})
        sample(self.root_, BROKEN, 3, held={"C2": False}, value=2 / 3, **{"pass": False},
               verdicts={"no_overshoot": False})
        self.document = report.read_root(self.root_)
        self.broken = row(self.document, BROKEN)

    def test_each_id_is_counted_over_the_samples(self):
        self.assertEqual(self.broken["samples"], 3)
        self.assertEqual(self.broken["ran"], 3)
        self.assertEqual(self.broken["ids"]["P1"], {"kind": "caught", "k": 2, "n": 3})
        self.assertEqual(self.broken["ids"]["C1"], {"kind": "held", "k": 3, "n": 3})
        self.assertEqual(self.broken["ids"]["C2"], {"kind": "held", "k": 2, "n": 3})
        self.assertEqual(list(self.broken["ids"]), ["P1", "C1", "C2"])  # planted first, then controls, in number order

    def test_overshoots_passes_and_the_mean_value_are_counted(self):
        self.assertEqual(self.broken["overshoot"], {"k": 1, "n": 3})
        self.assertEqual(self.broken["pass"], {"k": 1, "n": 3})
        self.assertAlmostEqual(self.broken["value"], (1 + 2 / 3 + 2 / 3) / 3)

    def test_the_driver_is_host_model_and_effort(self):
        self.assertEqual(self.broken["drivers"], ["codex/gpt-6.1-terra/xhigh"])
        self.assertEqual(self.document["drivers"], ["codex/gpt-6.1-terra/xhigh"])
        self.assertEqual(report.driver_label(("claude", "ollama", "qwen", None)), "claude:ollama/qwen/default")

    def test_the_ids_of_a_root_are_the_union_of_its_scenarios_planted_first(self):
        sample(self.root_, WRONG, 1, caught={"P2": True}, held={"C3": True})
        self.assertEqual(report.read_root(self.root_)["ids"], ["P1", "P2", "C1", "C2", "C3"])

    def test_the_report_is_json_and_a_root_may_be_given_as_text_or_a_path(self):
        again = report.read_root(str(self.root_))
        self.assertEqual(json.loads(json.dumps(again)), again)
        self.assertEqual(again["root"], str(self.root_))


# ------------------------------------------------------------------------------------------------------------ not run, not a pass

class NotRun(Temp):
    def test_a_sample_with_no_result_is_not_run_counts_in_the_denominator_and_is_no_pass(self):
        root = self.root()
        sample(root, WRONG, 1)
        (root / "validate-existing" / "wrong-check" / "2").mkdir()
        found = row(report.read_root(root), WRONG)
        self.assertEqual((found["samples"], found["ran"]), (2, 1))
        self.assertEqual(found["pass"], {"k": 1, "n": 2})
        self.assertEqual(found["ids"]["P1"], {"kind": "caught", "k": 1, "n": 2})
        self.assertEqual(found["not_run"], [{"sample": 2, "reason": "no stage-result.json"}])

    def test_error_txt_says_why_a_sample_was_not_run(self):
        root = self.root()
        folder = sample(root, WRONG, 1)
        (folder / "stage-result.json").unlink()
        (folder / "error.txt").write_text("RuntimeError: the fake host\n was told to crash\n")
        self.assertEqual(row(report.read_root(root), WRONG)["not_run"],
                         [{"sample": 1, "reason": "RuntimeError: the fake host was told to crash"}])

    def test_a_half_written_result_is_not_run(self):
        root = self.root()
        folder = sample(root, WRONG, 1)
        (folder / "stage-result.json").rename(folder / "stage-result.json.partial")
        found = row(report.read_root(root), WRONG)
        self.assertEqual(found["ran"], 0)
        self.assertRegex(found["not_run"][0]["reason"], "half written")

    def test_a_result_that_cannot_be_parsed_or_has_the_wrong_shape_is_not_run(self):
        root = self.root()
        (sample(root, WRONG, 1) / "stage-result.json").write_text('{"verdicts": {"process": tr')
        (sample(root, WRONG, 2) / "stage-result.json").write_text("[1, 2]")
        (sample(root, WRONG, 3) / "stage-result.json").write_text(json.dumps({**GOOD, "verdicts": {"process": True}}))
        (sample(root, WRONG, 4) / "stage-result.json").write_text(json.dumps({**GOOD, "caught": {"P1": "yes"}}))
        (sample(root, WRONG, 5) / "stage-result.json").write_text(json.dumps({**GOOD, "pass": "true"}))
        found = row(report.read_root(root), WRONG)
        self.assertEqual((found["samples"], found["ran"], found["pass"]), (5, 0, {"k": 0, "n": 5}))
        self.assertEqual(sorted(item["sample"] for item in found["not_run"]), [1, 2, 3, 4, 5])
        self.assertEqual(found["drivers"], [])
        self.assertEqual(found["ids"], {})

    def test_a_sample_the_plan_named_with_no_folder_is_not_run(self):
        root = self.root()
        sample(root, WRONG, 1)
        sample(root, WRONG, 3)
        plan(root, {"validate-existing/wrong-check": {"samples": 4, "required": 4}})
        found = row(report.read_root(root), WRONG)
        self.assertEqual((found["samples"], found["ran"]), (4, 2))
        self.assertEqual(found["not_run"], [{"sample": 2, "reason": "no sample folder"}, {"sample": 4, "reason": "no sample folder"}])
        self.assertEqual(found["pass"], {"k": 2, "n": 4})

    def test_a_scenario_the_plan_named_that_has_no_folder_at_all_is_a_row_of_samples_not_run(self):
        root = self.root()
        sample(root, WRONG, 1)
        plan(root, {"validate-existing/wrong-check": {"samples": 1, "required": 1},
                    "validate-existing/broken-works-small-fix": {"samples": 2, "required": 2}})
        found = row(report.read_root(root), BROKEN)
        self.assertEqual((found["samples"], found["ran"], found["pass"]), (2, 0, {"k": 0, "n": 2}))
        self.assertFalse(found["rule"]["met"])

    def test_a_result_that_claims_a_pass_its_fields_do_not_show_is_not_a_pass(self):
        root = self.root()
        sample(root, WRONG, 1, verdicts={"oracle": False})  # pass: true, oracle false
        sample(root, WRONG, 2, caught={"P1": False})
        sample(root, WRONG, 3, held={"C1": False})
        sample(root, WRONG, 4, **{"pass": False})  # pass: false with everything else true
        found = row(report.read_root(root), WRONG)
        self.assertEqual((found["ran"], found["pass"]), (4, {"k": 0, "n": 4}))

    def test_folders_that_are_not_samples_are_not_read(self):
        root = self.root()
        sample(root, WRONG, 1)
        (root / ".logs").mkdir()
        (root / ".logs" / "x").mkdir()
        (root / "validate-existing" / "wrong-check" / "notes").mkdir()
        (root / "validate-existing" / "wrong-check" / ".hidden").mkdir()
        (root / "validate-existing" / "wrong-check" / "7.txt").write_text("x")
        document = report.read_root(root)
        self.assertEqual([item["id"] for item in document["scenarios"]], ["validate-existing/wrong-check"])
        self.assertEqual(row(document, WRONG)["samples"], 1)

    def test_a_root_that_is_not_a_folder_or_holds_no_sample_is_an_error(self):
        with self.assertRaisesRegex(report.ReportError, "is not a folder"):
            report.read_root(self.temp / "missing")
        with self.assertRaisesRegex(report.ReportError, "holds no sample"):
            report.read_root(self.root("empty"))
        (self.temp / "file").write_text("x")
        with self.assertRaisesRegex(report.ReportError, "is not a folder"):
            report.read_root(self.temp / "file")


class Hardening(Temp):
    """Roots that were copied, edited by hand or cut short must not read as a pass."""

    def test_a_folder_named_by_a_non_ascii_digit_does_not_crash_the_report_and_is_listed_as_ignored(self):
        root = self.root()
        sample(root, WRONG, 1)
        (root / "validate-existing" / "wrong-check" / "\u00b2").mkdir()
        (root / "validate-existing" / "wrong-check" / "\u0663").mkdir()  # an Arabic-Indic digit: str.isdigit, int() accepts it
        document = report.read_root(root)
        found = row(document, WRONG)
        self.assertEqual((found["samples"], found["ran"]), (1, 1))
        self.assertEqual(sorted(found["ignored"]), ["\u00b2", "\u0663"])
        self.assertIn("ignored: validate-existing/wrong-check/\u00b2 is not a sample folder", report.render(document))

    def test_01_is_not_sample_1_a_second_time_so_a_failure_cannot_vanish_behind_a_pass(self):
        root = self.root()
        sample(root, WRONG, 1)
        sample(root, WRONG, "01", caught={"P1": False}, **{"pass": False})  # the failing one sorts first or last: neither hides it
        found = row(report.read_root(root), WRONG)
        self.assertEqual((found["samples"], found["ran"], found["pass"]), (1, 1, {"k": 1, "n": 1}))
        self.assertEqual(found["ignored"], ["01"])
        self.assertIn("ignored: validate-existing/wrong-check/01", report.render(report.read_root(root)))

    def test_sample_0_and_a_negative_or_signed_name_are_not_samples(self):
        root = self.root()
        sample(root, WRONG, 1)
        for name in ("0", "-1", "+2", "1.0", "x"):
            (root / "validate-existing" / "wrong-check" / name).mkdir()
        found = row(report.read_root(root), WRONG)
        self.assertEqual((found["samples"], found["ran"]), (1, 1))
        self.assertEqual(sorted(found["ignored"]), ["+2", "-1", "0", "1.0", "x"])

    def test_a_result_that_checked_no_id_is_not_run_and_so_is_one_that_lacks_a_planned_id(self):
        root = self.root()
        (sample(root, WRONG, 1) / "stage-result.json").write_text(json.dumps({**GOOD, "caught": {}, "held": {}}))
        sample(root, WRONG, 2)
        found = row(report.read_root(root), WRONG)
        self.assertEqual((found["ran"], found["pass"]), (1, {"k": 1, "n": 2}))
        self.assertEqual(found["not_run"], [{"sample": 1, "reason": "stage-result.json checked no planted or control id"}])
        (sample(root, WRONG, 3) / "stage-result.json").write_text(json.dumps({**GOOD, "caught": {}}))  # held ids only: still a result
        plan(root, {"validate-existing/wrong-check": {"samples": 3, "required": 3, "planted": ["P1", "P2"], "controls": ["C1", "C2"]}})
        found = row(report.read_root(root), WRONG)
        self.assertEqual(found["ran"], 0)
        self.assertEqual([item["reason"] for item in found["not_run"]],
                         ["stage-result.json checked no planted or control id", "stage-result.json lacks the planned id P2",
                          "stage-result.json lacks the planned ids P1, P2"])
        self.assertEqual(found["pass"], {"k": 0, "n": 3})

    def test_a_value_outside_0_to_1_or_missing_makes_the_result_malformed(self):
        root = self.root()
        sample(root, WRONG, 1, value=5)
        sample(root, WRONG, 2, value=-0.1)
        sample(root, WRONG, 3, value=None)
        sample(root, WRONG, 4, value="1.0")
        sample(root, WRONG, 5, value=True)
        sample(root, WRONG, 6, value=float("nan"))
        sample(root, WRONG, 7, value=0)
        found = row(report.read_root(root), WRONG)
        self.assertEqual((found["samples"], found["ran"]), (7, 1))
        self.assertEqual({item["reason"] for item in found["not_run"]}, {"stage-result.json has no value between 0 and 1"})

    def test_the_value_counts_a_sample_that_was_not_run_as_zero(self):
        root = self.root()
        sample(root, WRONG, 1)
        plan(root, {"validate-existing/wrong-check": {"samples": 3, "required": 3}})
        found = row(report.read_root(root), WRONG)
        self.assertEqual((found["ran"], found["samples"], found["pass"]), (1, 3, {"k": 1, "n": 3}))
        self.assertAlmostEqual(found["value"], 1 / 3)
        sample(root, WRONG, 2, value=0.5, caught={"P1": False}, **{"pass": False})
        self.assertAlmostEqual(row(report.read_root(root), WRONG)["value"], 1.5 / 3)

    def test_a_root_that_mixes_plugin_builds_refs_or_overlays_says_so_and_a_clean_root_does_not(self):
        root = self.root()
        build = {"ref": "origin/main", "overlay": None, "local_head": "a" * 40,
                 "versions": {"plugin_version": "1.2.3", "shiploop_version": "4.5.6", "plugin_sha256": "abc123abc123"}}
        sample(root, WRONG, 1, **build)
        sample(root, WRONG, 2, **build)
        document = report.read_root(root)
        self.assertEqual(len(document["builds"]), 1)
        self.assertIn("ref origin/main", document["builds"][0])
        self.assertIn("plugin 1.2.3 abc123abc123", document["builds"][0])
        self.assertNotIn("mixes plugin builds", report.render(document))
        sample(root, WRONG, 3, **{**build, "ref": None, "overlay": {"overlay": "o.json", "modules": ["x"]}, "local_head": "b" * 40})
        document = report.read_root(root)
        self.assertEqual(len(document["builds"]), 2)
        self.assertEqual(len(row(document, WRONG)["builds"]), 2)
        self.assertIn("note: this root mixes plugin builds, refs or overlays: ", report.render(document))

    def test_results_with_no_build_fields_are_one_build_and_compare_still_works_across_builds(self):
        a, b = self.root("a"), self.root("b")
        sample(a, WRONG, 1)
        sample(b, WRONG, 1, ref="origin/main", local_head="c" * 40)
        self.assertEqual(len(report.read_root(a)["builds"]), 1)
        compared = report.compare(a, b)
        self.assertEqual(compared["scenarios"][0]["id"], "validate-existing/wrong-check")


# -------------------------------------------------------------------------------------------------------------------- the rule

class Rule(Temp):
    def test_the_plans_pass_rule_is_met_or_not_met_and_absent_without_a_plan(self):
        root = self.root()
        for number in (1, 2):
            sample(root, WRONG, number)
        sample(root, WRONG, 3, **{"pass": False}, caught={"P1": False})
        self.assertIsNone(row(report.read_root(root), WRONG)["rule"])
        plan(root, {"validate-existing/wrong-check": {"samples": 3, "required": 2}})
        self.assertEqual(row(report.read_root(root), WRONG)["rule"], {"required": 2, "met": True})
        plan(root, {"validate-existing/wrong-check": {"samples": 3, "required": 3}})
        self.assertEqual(row(report.read_root(root), WRONG)["rule"], {"required": 3, "met": False})

    def test_a_malformed_plan_is_ignored(self):
        root = self.root()
        sample(root, WRONG, 1)
        (root / "live-plan.json").write_text("{not json")
        found = row(report.read_root(root), WRONG)
        self.assertIsNone(found["rule"])
        self.assertEqual(found["samples"], 1)
        (root / "live-plan.json").write_text(json.dumps({"scenarios": {"validate-existing/wrong-check": {"samples": "3"}}}))
        self.assertEqual(row(report.read_root(root), WRONG)["samples"], 1)


# -------------------------------------------------------------------------------------------------------------------- the text

class Text(Temp):
    def test_the_matrix_has_a_row_per_scenario_and_a_column_per_id(self):
        root = self.root()
        sample(root, BROKEN, 1)
        sample(root, BROKEN, 2, caught={"P1": False}, **{"pass": False})
        sample(root, WRONG, 1, caught={"P1": True, "P2": True}, held={"C1": True})
        text = report.render(report.read_root(root))
        header = next(line for line in text.splitlines() if line.startswith("scenario"))
        self.assertEqual(header.split(), ["scenario", "ran", "P1", "P2", "C1", "C2", "overshoot", "pass", "rule", "driver"])
        broken = next(line for line in text.splitlines() if line.startswith("validate-existing/broken-works-small-fix"))
        self.assertEqual(broken.split(), ["validate-existing/broken-works-small-fix", "2/2", "1/2", "-", "2/2", "2/2", "0/2", "1/2",
                                          "-", "codex/gpt-6.1-terra/xhigh"])
        wrong = next(line for line in text.splitlines() if line.startswith("validate-existing/wrong-check"))
        self.assertEqual(wrong.split()[1:7], ["1/1", "1/1", "1/1", "1/1", "1/1", "0/1"])

    def test_not_run_samples_and_mixed_drivers_are_named(self):
        root = self.root()
        sample(root, WRONG, 1)
        sample(root, WRONG, 2, model="other-model")
        (root / "validate-existing" / "wrong-check" / "3").mkdir()
        plan(root, {"validate-existing/wrong-check": {"samples": 3, "required": 3}})
        text = report.render(report.read_root(root))
        self.assertIn("not run: validate-existing/wrong-check #3: no stage-result.json", text)
        self.assertIn("note: this root mixes drivers: codex/gpt-6.1-terra/xhigh; codex/other-model/xhigh", text)
        self.assertRegex(text, r"NOT MET")

    def test_the_rule_column_says_met(self):
        root = self.root()
        sample(root, WRONG, 1)
        plan(root, {"validate-existing/wrong-check": {"samples": 1, "required": 1}})
        self.assertRegex(report.render(report.read_root(root)), r"1/1\s+met\s+codex")


# ------------------------------------------------------------------------------------------------------------------- compare

class Compare(Temp):
    def pair(self, earlier: dict | None = None, later: dict | None = None) -> tuple[Path, Path]:
        a, b = self.root("a"), self.root("b")
        for number in (1, 2, 3):
            sample(b, WRONG, number, **(earlier or {}))
        sample(a, WRONG, 1, **(later or {}))
        sample(a, WRONG, 2, **(later or {}))
        sample(a, WRONG, 3, **{**(later or {}), "caught": {"P1": False}, "pass": False})
        return a, b

    def test_roots_of_one_driver_give_the_counts_of_each_and_the_change(self):
        a, b = self.pair()
        sample(b, WRONG, 3, caught={"P1": False}, **{"pass": False})
        sample(b, WRONG, 2, caught={"P1": False}, **{"pass": False})
        document = report.compare(a, b)
        self.assertEqual(document["driver"], "codex/gpt-6.1-terra/xhigh")
        cell = document["scenarios"][0]["cells"]["P1"]
        self.assertEqual((cell["a"], cell["b"]), ({"k": 2, "n": 3}, {"k": 1, "n": 3}))
        self.assertAlmostEqual(cell["delta"], 1 / 3, places=3)
        self.assertEqual(document["scenarios"][0]["cells"]["C1"]["delta"], 0)
        self.assertAlmostEqual(document["scenarios"][0]["cells"]["pass"]["delta"], 1 / 3, places=3)
        text = report.render_compare(document)
        self.assertIn("2/3 (was 1/3, +0.33)", text)
        self.assertIn("3/3 (=)", text)

    def test_a_different_model_effort_host_or_backend_is_refused_naming_both_drivers(self):
        for change in ({"model": "gpt-6-astra"}, {"effort": "medium"}, {"host": "grok"}, {"backend": "ollama"}):
            with self.subTest(change=change):
                a, b = self.root(f"a{len(change)}{next(iter(change))}"), self.root(f"b{len(change)}{next(iter(change))}")
                sample(a, WRONG, 1)
                sample(b, WRONG, 1, **change)
                with self.assertRaises(report.DriverMismatch) as caught:
                    report.compare(a, b)
                text = str(caught.exception)
                self.assertIn(str(a), text)
                self.assertIn(str(b), text)
                self.assertIn("codex/gpt-6.1-terra/xhigh", text)
                self.assertRegex(text, r"S-12")

    def test_the_refusal_is_a_report_error_and_names_the_value_that_differs(self):
        a, b = self.root("a"), self.root("b")
        sample(a, WRONG, 1)
        sample(b, WRONG, 1, model="gpt-6-astra")
        with self.assertRaises(report.ReportError) as caught:
            report.compare(a, b)
        self.assertIn("gpt-6-astra", str(caught.exception))
        self.assertIn("gpt-6.1-terra", str(caught.exception))

    def test_a_root_that_mixes_drivers_or_has_no_graded_sample_cannot_be_compared(self):
        a, b = self.root("a"), self.root("b")
        sample(a, WRONG, 1)
        sample(a, WRONG, 2, model="other")
        sample(b, WRONG, 1)
        with self.assertRaises(report.DriverMismatch):
            report.compare(a, b)
        with self.assertRaises(report.DriverMismatch):
            report.compare(b, a)
        empty = self.root("none")
        (empty / "validate-existing" / "wrong-check" / "1").mkdir(parents=True)
        with self.assertRaisesRegex(report.ReportError, "has no graded sample"):
            report.compare(b, empty)
        with self.assertRaisesRegex(report.ReportError, "has no graded sample"):
            report.compare(empty, b)

    def test_a_scenario_in_one_root_only_is_marked_and_has_no_change(self):
        a, b = self.root("a"), self.root("b")
        sample(a, WRONG, 1)
        sample(a, BROKEN, 1)
        sample(b, WRONG, 1)
        document = report.compare(a, b)
        only = next(item for item in document["scenarios"] if item["id"] == "/".join(BROKEN))
        self.assertEqual(only["in"], "a")
        self.assertTrue(all(cell["delta"] is None for cell in only["cells"].values()))
        self.assertIn("(only in the first root)", report.render_compare(document))
        gone = report.compare(b, a)
        self.assertEqual(next(item for item in gone["scenarios"] if item["id"] == "/".join(BROKEN))["in"], "b")
        self.assertIn("(only in the earlier root)", report.render_compare(gone))

    def test_a_sample_not_run_lowers_the_rate_of_its_root(self):
        a, b = self.root("a"), self.root("b")
        for number in (1, 2):
            sample(a, WRONG, number)
            sample(b, WRONG, number)
        (a / "validate-existing" / "wrong-check" / "3").mkdir()
        sample(b, WRONG, 3)
        cell = report.compare(a, b)["scenarios"][0]["cells"]["pass"]
        self.assertEqual((cell["a"], cell["b"]), ({"k": 2, "n": 3}, {"k": 3, "n": 3}))
        self.assertAlmostEqual(cell["delta"], -1 / 3, places=3)

    def test_comparing_a_root_with_itself_changes_nothing(self):
        a = self.root("a")
        sample(a, WRONG, 1)
        sample(a, WRONG, 2, caught={"P1": False}, **{"pass": False})
        document = report.compare(a, a)
        self.assertTrue(all(cell["delta"] == 0 for item in document["scenarios"] for cell in item["cells"].values()))


# ---------------------------------------------------------------------------------------------------------------------- module

class Module(unittest.TestCase):
    def test_it_reads_files_only_and_uses_only_the_standard_library(self):
        tree = ast.parse(MODULE.read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        self.assertEqual(imported - set(sys.stdlib_module_names), set())
        self.assertFalse(imported & {"subprocess", "run", "stage_live", "stage_build", "hosts", "stage_oracle"}, imported)

    def test_it_is_outside_the_evaluator_digest_and_the_qualification_snapshot(self):
        self.assertTrue(MODULE.is_file())
        evaluator, graded = set(boundary.evaluator_files(HARNESS)), set(boundary.oracle_files(HARNESS))
        self.assertNotIn(MODULE, evaluator | graded)
        snapshot_files = boundary.qualification_snapshot(HARNESS)["files"]
        self.assertFalse([name for name in snapshot_files if "/stage_suite/" in name or "/stage_cases/" in name])
        self.assertFalse([name for name in snapshot_files if name.startswith("test/shiploop-e2e-stage")])
        self.assertFalse(boundary.candidate_path("test/shiploop_e2e/stage_suite/stage_report.py"))
        self.assertFalse(boundary.candidate_path("test/shiploop-e2e-stage-report.test.py"))

    def test_adding_the_module_leaves_the_digest_where_it_was(self):
        with tempfile.TemporaryDirectory(prefix="stage-report-boundary-") as temp:
            harness = Path(temp) / "shiploop_e2e"
            (harness / "checks").mkdir(parents=True)
            for name, text in {"run.py": "x = 1\n", "checks/c.py": "y = 2\n", "SPEC.md": "s\n"}.items():
                (harness / name).write_text(text)
            before = boundary.fingerprint(harness, None)
            (harness / "stage_suite").mkdir()
            (harness / "stage_suite" / "stage_report.py").write_text("z = 3\n")
            self.assertEqual(boundary.fingerprint(harness, None), before)

    def test_no_stage_file_is_in_the_top_level_of_the_harness(self):
        self.assertEqual(sorted(path.name for path in HARNESS.iterdir() if path.is_file() and path.name.startswith("stage")), [])


if __name__ == "__main__":
    unittest.main()
