#!/usr/bin/env python3
"""The stage suite's runner (test/shiploop_e2e/stage_suite/stages.py; docs/plans/shiploop-stage-suite.md), no model.

Small scenario sets in temporary folders, on the node-base fixture (plain files); every check that runs code is ``grep`` or
``test``, so the suite needs no other runtime. The render tier builds real ShipLoop runs (about a second each).

- Selectors: the union of the includes, the excludes removed (also when there is no include), a stage, one scenario, each phase
  (an ``improve@`` stage is phase improve and ``spec`` never selects ``improve@spec``), a tag; an unknown selector and a selector
  that selects nothing are usage errors naming it; an exclude that starts like an option (``-handoff`` is not ``-h``) is a selector.
- ``list`` prints one row per scenario (phase, tags, tiers, the counts) and the same data with ``--json``.
- ``verify`` passes a correct scenario; fails (exit 1) when the oracle is too weak to fail a declared bad reference, when a bad
  reference does not fail what its meta.json declares and when the good reference does not pass; reports a failure nobody declared
  as a surprise that is not an error; skips a scenario without the verify tier.
- ``render`` passes a scenario whose planted expectation reaches the packet and a scenario the engine settles by script, fails one
  whose packet check is wrong and one the seed refuses (with the reason, the others still run), skips what the builder cannot
  build yet, reports an id no render check proves as not exercised, leaves the built folders under ``--keep`` (and removes its
  temporary ones otherwise), and leaves the harness's own seed script as it was.
- Exit codes 0 (all passed), 1 (a failure), 2 (usage or schema error, with the text), 3 (nothing selected); the CLI runs from any
  working directory with its stdin closed; ``live``, ``grade`` and ``report`` are named as not built, not stubbed.
- The shipped scenarios (test/shiploop_e2e/stage_cases) verify and render, and the guide's example selectors select something.
- The runner is outside the evaluator digest and the qualification snapshot, as the probes are (test/shiploop-e2e-sdlc-probes.test.py).
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "test" / "shiploop_e2e"
STAGES = HARNESS / "stage_suite" / "stages.py"
sys.path.insert(0, str(HARNESS / "stage_suite"))
sys.path.insert(0, str(HARNESS))
import boundary  # noqa: E402
import run  # noqa: E402
import stage_build as sb  # noqa: E402
import stages  # noqa: E402

GIT_ENV = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "SHIPLOOP_PROGRESS": "off"}
CHILD_SECONDS = 300  # a child that takes longer is stuck (SPEC S-14)

E1 = {"id": "E1", "state": "works", "statement": "PLANTED-E1: src/strings.js holds GOOD", "steps": ["S1"],
      "paths": ["src/strings.js"], "check": "grep -q GOOD src/strings.js"}
E2 = {"id": "E2", "state": "works", "statement": "src/paginate.js exists", "steps": ["S1"], "paths": ["src/paginate.js"],
      "check": "test -f src/paginate.js"}
RECORDS = {"step-plan": {"expectations": [E1, E2]}}

# A scenario that plants P1 (src/strings.js lacks GOOD, so the E1 check of validate-existing fails on the base) and holds C1
# (src/paginate.js is left alone). The oracle proves each against the reference outputs below; the render checks prove them on
# the packet.
GOOD = {
    "stage": "validate-existing", "about": "A works expectation is broken on the base by a small fault.",
    "tags": ["catch", "prep-fix"], "fixture": "node-base", "request_from": "node-fix-bug", "seed_records": RECORDS,
    "planted": [{"id": "P1", "what": "src/strings.js lacks the repair", "signature": "PLANTED-E1"}],
    "controls": [{"id": "C1", "what": "src/paginate.js is left alone"}],
    "render": [{"proves": "P1", "packet_contains": "E1 works[^\\n]*DOES NOT MATCH"},
               {"proves": "C1", "packet_not_contains": "E2 works[^\\n]*DOES NOT MATCH"}],
    "oracle": [{"proves": "P1", "outcome": ["done"]},
               {"proves": "P1", "file": "src/strings.js", "contains": "REPAIRED"},
               {"proves": "C1", "file": "src/paginate.js", "unchanged": True}]}
GOOD_FILES = {
    "reference/good/result.json": json.dumps({"outcome": "done", "summary": "Repaired."}),
    "reference/good/tree/src/strings.js": "// REPAIRED\nmodule.exports = {};\n",
    "reference/bad-unrepaired/result.json": json.dumps({"outcome": "send-back"}),
    "reference/bad-unrepaired/meta.json": json.dumps({"fails": ["P1"], "why": "reports the fault, repairs nothing"}),
    "reference/bad-touched/result.json": json.dumps({"outcome": "done"}),
    "reference/bad-touched/tree/src/strings.js": "// REPAIRED\nmodule.exports = {};\n",
    "reference/bad-touched/tree/src/paginate.js": "module.exports = {};\n",
    "reference/bad-touched/meta.json": json.dumps({"fails": ["C1"]})}
# The fault repaired by repo/: every check of validate-existing matches, so the engine settles the stage by script.
REPAIRED = {
    "stage": "validate-existing", "about": "Nothing is broken, so the engine settles the stage itself.", "tags": ["control"],
    "fixture": "node-base", "request_from": "node-fix-bug", "tiers": ["render"], "seed_records": RECORDS,
    "planted": [{"id": "P1", "what": "the fault is repaired in repo/"}],
    "render": [{"proves": "P1", "settled_by_script": True}, {"proves": "P1", "packet_issued": False},
               {"current_stage": "implement"}]}
REPAIRED_FILES = {"repo/src/strings.js": "// GOOD\nmodule.exports = {};\n"}


def lay(base: Path, files: dict[str, str]) -> Path:
    for name, text in files.items():
        (base / name).parent.mkdir(parents=True, exist_ok=True)
        (base / name).write_text(text)
    return base


def scenario(cases: Path, stage: str, name: str, data: dict | None = None, files: dict | None = None, **changes) -> Path:
    """Write ``<cases>/<stage>/<name>/`` with `data` (default GOOD, `changes` applied; None removes a key) and `files`."""
    data = copy.deepcopy(GOOD if data is None else data)
    data["stage"] = stage
    for key, value in changes.items():
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
    folder = cases / stage / name
    lay(folder, {"scenario.json": json.dumps(data), **(GOOD_FILES if files is None else files)})
    return folder


def cli(*argv: str) -> tuple[int, str, str]:
    """`stages.main` in this process: (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = stages.main(list(argv))
    return code, out.getvalue(), err.getvalue()


def rows(document: str) -> dict[str, dict]:
    return {row["id"]: row for row in json.loads(document)["scenarios"]}


class Temp(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="stages-")
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)
        self.cases = self.temp / "cases"
        self.cases.mkdir()

    def one(self, name: str = "s", files: dict | None = None, **changes) -> Path:
        """A cases folder of its own holding one validate-existing scenario."""
        cases = self.temp / f"cases-{name}"
        scenario(cases, "validate-existing", name, None, files, **changes)
        return cases


class Catalog(Temp):
    """Five scenarios across the phases, for the selectors and the list; verify-only except two."""

    def setUp(self):
        super().setUp()
        scenario(self.cases, "validate-existing", "broken")
        scenario(self.cases, "validate-existing", "repaired", REPAIRED, REPAIRED_FILES)
        scenario(self.cases, "spec", "outcome-dropped", None, None, tiers=["verify"], request_from=None, render=[], tags=["catch"])
        scenario(self.cases, "handoff", "leftovers", None, None, tiers=["verify"], request_from=None, render=[], tags=["control"])
        scenario(self.cases, "improve@spec", "missing-outcome", None, None, tags=["catch", "improve"])
        self.found = sb.discover(self.cases)

    def ids(self, *tokens: str) -> list[str]:
        return [sc.id for sc in stages.select(list(tokens), self.found)]


# ---------------------------------------------------------------------------------------------------------------- selectors

class Selectors(Catalog):
    EVERY = ["spec/outcome-dropped", "validate-existing/broken", "validate-existing/repaired", "handoff/leftovers",
             "improve@spec/missing-outcome"]

    def test_no_selector_and_all_select_every_scenario_in_stage_order_with_improve_stages_last(self):
        self.assertEqual(self.ids(), self.EVERY)
        self.assertEqual(self.ids("all"), self.EVERY)

    def test_a_stage_selects_its_scenarios_and_an_improve_stage_is_its_own(self):
        self.assertEqual(self.ids("validate-existing"), ["validate-existing/broken", "validate-existing/repaired"])
        self.assertEqual(self.ids("spec"), ["spec/outcome-dropped"])
        self.assertEqual(self.ids("improve@spec"), ["improve@spec/missing-outcome"])

    def test_a_scenario_is_selected_by_its_stage_and_name(self):
        self.assertEqual(self.ids("validate-existing/repaired"), ["validate-existing/repaired"])
        self.assertEqual(self.ids("improve@spec/missing-outcome"), ["improve@spec/missing-outcome"])

    def test_each_phase_selects_the_scenarios_of_its_stages(self):
        self.assertEqual(self.ids("@prelude"), ["spec/outcome-dropped"])
        self.assertEqual(self.ids("@inner"), ["validate-existing/broken", "validate-existing/repaired"])
        self.assertEqual(self.ids("@outer"), ["handoff/leftovers"])
        self.assertEqual(self.ids("@improve"), ["improve@spec/missing-outcome"])

    def test_a_tag_selects_the_scenarios_that_carry_it(self):
        self.assertEqual(self.ids("+catch"), ["spec/outcome-dropped", "validate-existing/broken", "improve@spec/missing-outcome"])
        self.assertEqual(self.ids("+control"), ["validate-existing/repaired", "handoff/leftovers"])
        self.assertEqual(self.ids("+prep-fix"), ["validate-existing/broken"])

    def test_includes_are_a_union_without_repeats(self):
        self.assertEqual(self.ids("@outer", "spec", "@outer"), ["spec/outcome-dropped", "handoff/leftovers"])
        self.assertEqual(self.ids("+prep-fix", "+control"),
                         ["validate-existing/broken", "validate-existing/repaired", "handoff/leftovers"])

    def test_an_exclude_removes_from_the_includes(self):
        self.assertEqual(self.ids("@inner", "-validate-existing/repaired"), ["validate-existing/broken"])
        self.assertEqual(self.ids("+catch", "-@improve"), ["spec/outcome-dropped", "validate-existing/broken"])
        self.assertEqual(self.ids("all", "-+control"),
                         ["spec/outcome-dropped", "validate-existing/broken", "improve@spec/missing-outcome"])

    def test_an_exclude_without_an_include_removes_from_all(self):
        self.assertEqual(self.ids("-validate-existing"), ["spec/outcome-dropped", "handoff/leftovers",
                                                           "improve@spec/missing-outcome"])
        self.assertEqual(self.ids("-@inner", "-@improve"), ["spec/outcome-dropped", "handoff/leftovers"])

    def test_the_order_of_the_selectors_does_not_matter(self):
        self.assertEqual(self.ids("-@improve", "@inner", "+catch"), self.ids("+catch", "@inner", "-@improve"))

    def test_excluding_everything_selects_nothing_without_an_error(self):
        self.assertEqual(self.ids("-all"), [])
        self.assertEqual(self.ids("@inner", "-validate-existing"), [])

    def test_an_unknown_selector_is_a_usage_error_naming_it(self):
        for token in ("bogus", "@bogus", "+", "+bad tag", "spec/a/b", "spec/", "-bogus", "-@bogus", "-", "improve@nope", "../x"):
            with self.subTest(token=token):
                with self.assertRaisesRegex(stages.UsageError, "unknown selector"):
                    self.ids(token)

    def test_a_selector_that_selects_nothing_is_a_usage_error_naming_it(self):
        for token in ("+nope", "document", "validate-existing/none", "improve@intake", "release"):
            with self.subTest(token=token):
                with self.assertRaises(stages.UsageError) as caught:
                    self.ids(token)
                self.assertIn(repr(token), str(caught.exception))
                self.assertIn("selects no scenario", str(caught.exception))
        with self.assertRaises(stages.UsageError) as caught:
            self.ids("all", "-+nope")
        self.assertIn("'-+nope'", str(caught.exception))

    def test_all_on_an_empty_folder_selects_nothing_and_a_named_stage_is_an_error(self):
        self.assertEqual(stages.select([], []), [])
        self.assertEqual(stages.select(["all"], []), [])
        with self.assertRaises(stages.UsageError):
            stages.select(["spec"], [])

    def test_the_phase_of_a_scenario(self):
        self.assertEqual({sc.id: stages.phase_of(sc) for sc in self.found},
                         {"spec/outcome-dropped": "prelude", "validate-existing/broken": "inner",
                          "validate-existing/repaired": "inner", "handoff/leftovers": "outer",
                          "improve@spec/missing-outcome": "improve"})


class CommandLineSelectors(Catalog):
    def test_an_exclude_that_starts_like_an_option_is_still_a_selector(self):
        # -handoff would be -h plus an argument, and -spec an unknown option, to argparse.
        for token, left in (("-handoff", 4), ("-handoff/leftovers", 4), ("-spec", 4), ("-@outer", 4), ("-+control", 3)):
            with self.subTest(token=token):
                code, out, err = cli("list", token, "--json", "--cases-dir", str(self.cases))
                self.assertEqual((code, err), (0, ""), out)
                self.assertEqual(len(rows(out)), left)
                self.assertNotIn("handoff/leftovers" if token != "-spec" else "spec/outcome-dropped", rows(out))

    def test_selectors_and_options_may_be_mixed_in_any_order(self):
        code, out, err = cli("list", "@inner", "--json", "+catch", "--cases-dir", str(self.cases), "-validate-existing/repaired")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(list(rows(out)), ["spec/outcome-dropped", "validate-existing/broken", "improve@spec/missing-outcome"])

    def test_the_values_of_the_options_are_not_selectors(self):
        code, out, err = cli("list", "--cases-dir", str(self.cases), "--json")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(len(rows(out)), 5)


# ------------------------------------------------------------------------------------------------------------------- list

class List(Catalog):
    def test_the_table_has_a_row_per_scenario_with_phase_tags_tiers_and_counts(self):
        code, out, err = cli("list", "--cases-dir", str(self.cases))
        self.assertEqual((code, err), (0, ""))
        lines = out.splitlines()
        self.assertEqual(lines[0].split(), ["scenario", "phase", "tiers", "tags", "planted", "controls", "render", "oracle"])
        broken = next(line for line in lines if line.startswith("validate-existing/broken")).split()
        self.assertEqual(broken, ["validate-existing/broken", "inner", "verify,render,live", "catch,prep-fix", "1", "1", "2", "3"])
        outer = next(line for line in lines if line.startswith("handoff/leftovers")).split()
        self.assertEqual(outer[:4], ["handoff/leftovers", "outer", "verify", "control"])
        self.assertEqual(lines[-1], "total: 5 scenarios")
        self.assertEqual([line.split()[0] for line in lines[1:-1]],
                         ["spec/outcome-dropped", "validate-existing/broken", "validate-existing/repaired", "handoff/leftovers",
                          "improve@spec/missing-outcome"])

    def test_json_is_one_document_with_the_same_data(self):
        code, out, err = cli("list", "+catch", "--json", "--cases-dir", str(self.cases))
        self.assertEqual((code, err), (0, ""))
        document = json.loads(out)
        self.assertEqual((document["command"], document["cases_dir"], document["total"]), ("list", str(self.cases), {"scenarios": 3}))
        self.assertEqual(document["scenarios"][1], {
            "id": "validate-existing/broken", "stage": "validate-existing", "name": "broken", "phase": "inner",
            "tags": ["catch", "prep-fix"], "tiers": ["verify", "render", "live"], "planted": 1, "controls": 1,
            "checks": {"render": 2, "oracle": 3}})
        self.assertEqual(document["scenarios"][2]["phase"], "improve")

    def test_a_selection_lists_only_what_it_selects(self):
        code, out, err = cli("list", "@outer", "--cases-dir", str(self.cases))
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out.splitlines()[-1], "total: 1 scenario")
        self.assertNotIn("validate-existing", out)


# ------------------------------------------------------------------------------------------------------------------ verify

class Verify(Catalog):
    def test_correct_scenarios_pass_with_every_id_caught_or_held_and_a_scenario_without_the_tier_is_skipped(self):
        code, out, err = cli("verify", "--cases-dir", str(self.cases))
        self.assertEqual((code, err), (0, ""), out)
        self.assertIn("total: 5 scenarios, 4 passed, 0 failed, 1 skipped", out)
        self.assertRegex(out, r"validate-existing/broken\s+verify\s+PASS\s+P1 caught\s+C1 held")
        self.assertRegex(out, r"validate-existing/repaired\s+verify\s+skipped: tier off")
        self.assertRegex(out, r"improve@spec/missing-outcome\s+verify\s+PASS")

    def test_json_names_the_references_and_what_each_fails(self):
        code, out, err = cli("verify", "validate-existing/broken", "--json", "--cases-dir", str(self.cases))
        self.assertEqual((code, err), (0, ""))
        document = json.loads(out)
        self.assertEqual(document["total"], {"scenarios": 1, "passed": 1, "failed": 0, "skipped": 0})
        [row] = document["scenarios"]
        self.assertEqual((row["result"], row["tier"], row["ids"]), ("pass", "verify", {"P1": "caught", "C1": "held"}))
        refs = row["references"]
        self.assertEqual(sorted(refs), ["bad-touched", "bad-unrepaired", "good"])
        self.assertEqual((refs["good"]["pass"], refs["good"]["failed"]), (True, []))
        self.assertEqual((refs["bad-unrepaired"]["declared"], refs["bad-unrepaired"]["failed"]), (["P1"], ["P1"]))
        self.assertEqual((refs["bad-touched"]["declared"], refs["bad-touched"]["failed"]), (["C1"], ["C1"]))
        self.assertEqual((refs["bad-unrepaired"]["surprises"], row["problems"], row["notes"]), ([], [], []))

    def test_verify_runs_no_shiploop_and_builds_nothing(self):
        with mock.patch.object(sb, "build", side_effect=AssertionError("verify builds")), \
                mock.patch.object(sb, "render", side_effect=AssertionError("verify renders")):
            code, out, err = cli("verify", "--cases-dir", str(self.cases))
        self.assertEqual((code, err), (0, ""), out)


class VerifyFailures(Temp):
    def test_an_oracle_too_weak_to_fail_a_declared_bad_reference_fails_the_scenario(self):
        # Only "the file exists" proves P1 now: bad-unrepaired leaves strings.js as it was, which exists, so P1 is caught.
        weak = [{"proves": "P1", "file": "src/strings.js", "exists": True},
                {"proves": "C1", "file": "src/paginate.js", "unchanged": True}]
        cases = self.one("weak", oracle=weak)
        code, out, err = cli("verify", "--json", "--cases-dir", str(cases))
        self.assertEqual((code, err), (1, ""))
        [row] = json.loads(out)["scenarios"]
        self.assertEqual(row["result"], "fail")
        self.assertEqual(row["problems"], ["reference/bad-unrepaired: declared P1 must fail, but the oracle says P1 is caught"])
        self.assertEqual(row["references"]["bad-unrepaired"]["failed"], [])
        text = cli("verify", "--cases-dir", str(cases))
        self.assertEqual(text[0], 1)
        self.assertRegex(text[1], r"validate-existing/weak\s+verify\s+FAIL")
        self.assertIn("  reference/bad-unrepaired: declared P1 must fail", text[1])
        self.assertIn("total: 1 scenario, 0 passed, 1 failed, 0 skipped", text[1])

    def test_a_bad_reference_that_does_not_fail_what_it_declares_fails_the_scenario(self):
        # bad-touched repairs strings.js and touches paginate.js: it fails C1, and declaring P1 as well is wrong.
        files = {**GOOD_FILES, "reference/bad-touched/meta.json": json.dumps({"fails": ["C1", "P1"]})}
        cases = self.one("lying", files=files)
        code, out, err = cli("verify", "--json", "--cases-dir", str(cases))
        self.assertEqual((code, err), (1, ""))
        [row] = json.loads(out)["scenarios"]
        self.assertEqual(row["problems"], ["reference/bad-touched: declared P1 must fail, but the oracle says P1 is caught"])

    def test_the_good_reference_must_pass_the_oracle(self):
        files = {name: text for name, text in GOOD_FILES.items() if name != "reference/good/tree/src/strings.js"}
        cases = self.one("unrepaired-good", files=files)
        code, out, err = cli("verify", "--json", "--cases-dir", str(cases))
        self.assertEqual((code, err), (1, ""))
        [row] = json.loads(out)["scenarios"]
        self.assertEqual(row["result"], "fail")
        self.assertEqual(row["ids"], {"P1": "missed", "C1": "held"})
        self.assertIn("reference/good: the oracle does not pass it (P1 missed)", row["problems"])
        self.assertTrue(any("file failed for P1" in problem and "REPAIRED" in problem for problem in row["problems"]), row["problems"])

    def test_a_failure_nobody_declared_is_a_surprise_and_not_an_error(self):
        # bad-unrepaired now also touches paginate.js, which fails C1 although its meta.json declares P1 only.
        files = {**GOOD_FILES, "reference/bad-unrepaired/tree/src/paginate.js": "module.exports = {};\n"}
        cases = self.one("surprising", files=files)
        code, out, err = cli("verify", "--json", "--cases-dir", str(cases))
        self.assertEqual((code, err), (0, ""))
        [row] = json.loads(out)["scenarios"]
        self.assertEqual((row["result"], row["problems"]), ("pass", []))
        self.assertEqual(row["references"]["bad-unrepaired"]["surprises"], ["C1"])
        self.assertEqual(row["notes"], ["reference/bad-unrepaired also fails C1, which its meta.json does not declare"])
        text = cli("verify", "--cases-dir", str(cases))
        self.assertEqual(text[0], 0)
        self.assertIn("  note: reference/bad-unrepaired also fails C1", text[1])

    def test_a_reference_that_cannot_be_laid_fails_the_scenario_and_the_others_still_run(self):
        files = {**GOOD_FILES, "reference/bad-touched/deleted.txt": "src/no-such-file.js\n"}
        scenario(self.cases, "validate-existing", "broken-reference", None, files)
        scenario(self.cases, "validate-existing", "fine")
        code, out, err = cli("verify", "--json", "--cases-dir", str(self.cases))
        self.assertEqual((code, err), (1, ""))
        found = rows(out)
        self.assertEqual((found["validate-existing/broken-reference"]["result"], found["validate-existing/fine"]["result"]),
                         ("fail", "pass"))
        self.assertTrue(any("no-such-file.js" in problem for problem in found["validate-existing/broken-reference"]["problems"]))


# ------------------------------------------------------------------------------------------------------------------ render

class Render(unittest.TestCase):
    """Real runs, built once for the class (about a second each)."""

    @classmethod
    def setUpClass(cls):
        temp = tempfile.TemporaryDirectory(prefix="stages-render-")
        cls.addClassCleanup(temp.cleanup)
        cls.temp = Path(temp.name)
        # A private HOME and no Git configuration, as test/git_fixture.py does for a test case.
        home = cls.temp / "home"
        (home / ".config").mkdir(parents=True)
        environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        environment.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"), **GIT_ENV)
        isolated = mock.patch.dict(os.environ, environment, clear=True)
        isolated.start()
        cls.addClassCleanup(isolated.stop)
        cls.cases = cls.temp / "cases"
        render = {"tiers": ["render"]}
        scenario(cls.cases, "validate-existing", "broken", None, {}, **render,
                 controls=[*GOOD["controls"], {"id": "C2", "what": "no render check looks at this one"}])
        scenario(cls.cases, "validate-existing", "repaired", REPAIRED, REPAIRED_FILES)
        scenario(cls.cases, "validate-existing", "wrong-packet", None, {}, **render,
                 render=[{"proves": "P1", "packet_contains": "NEVER-IN-A-PACKET"},
                         {"proves": "C1", "packet_not_contains": "E2 works[^\\n]*DOES NOT MATCH"}])
        scenario(cls.cases, "validate-existing", "refused-by-the-engine", None, {}, **render,
                 seed_records={"step-plan": {"expectations": [{**E1, "state": "not-a-state"}]}})
        scenario(cls.cases, "improve@spec", "later", None, GOOD_FILES, render=GOOD["render"])
        scenario(cls.cases, "spec", "verify-only", None, GOOD_FILES, tiers=["verify"], request_from=None, render=[])
        cls.digest = boundary.fingerprint(HARNESS, None)
        cls.seed_script = run.SEED_SCRIPT
        cls.code, cls.out, cls.err = cli("render", "--json", "--cases-dir", str(cls.cases))
        cls.rows = rows(cls.out)

    def test_the_run_fails_as_a_whole_because_two_scenarios_fail_and_the_rest_still_ran(self):
        self.assertEqual((self.code, self.err), (1, ""))
        self.assertEqual({sid: row["result"] for sid, row in self.rows.items()},
                         {"validate-existing/broken": "pass", "validate-existing/repaired": "pass",
                          "validate-existing/wrong-packet": "fail", "validate-existing/refused-by-the-engine": "fail",
                          "improve@spec/later": "skipped", "spec/verify-only": "skipped"})
        self.assertEqual(json.loads(self.out)["total"], {"scenarios": 6, "passed": 2, "failed": 2, "skipped": 2})

    def test_a_planted_expectation_that_reaches_the_packet_is_caught_and_a_control_held(self):
        row = self.rows["validate-existing/broken"]
        self.assertEqual(row["ids"], {"P1": "caught", "C1": "held", "C2": "not exercised"})
        self.assertEqual((row["problems"], row["tier"], row["phase"]), ([], "render", "inner"))
        self.assertEqual(row["stage"], {"issued": True, "settled": False, "current_stage": "validate-existing"})
        self.assertTrue(all(check["pass"] for check in row["checks"]), row["checks"])

    def test_a_stage_the_engine_settles_by_script_passes_with_no_packet(self):
        row = self.rows["validate-existing/repaired"]
        self.assertEqual(row["result"], "pass", row["problems"])
        self.assertEqual(row["ids"], {"P1": "caught"})
        self.assertEqual(row["stage"], {"issued": False, "settled": True, "current_stage": "implement"})

    def test_a_wrong_packet_check_fails_the_scenario_and_misses_the_id_it_proves(self):
        row = self.rows["validate-existing/wrong-packet"]
        self.assertEqual(row["ids"], {"P1": "missed", "C1": "held"})
        self.assertEqual(len(row["problems"]), 1)
        self.assertRegex(row["problems"][0], r"^packet_contains failed for P1: the packet does not match /NEVER-IN-A-PACKET/")

    def test_a_seed_the_engine_refuses_fails_the_scenario_with_the_reason(self):
        row = self.rows["validate-existing/refused-by-the-engine"]
        self.assertEqual((row["result"], row["ids"]), ("fail", {}))
        self.assertEqual(len(row["problems"]), 1)
        self.assertRegex(row["problems"][0], r"^the build failed: .*seed")

    def test_what_the_builder_cannot_build_yet_and_what_has_no_render_tier_are_skipped_not_failed(self):
        self.assertEqual((self.rows["improve@spec/later"]["result"], self.rows["improve@spec/later"]["reason"]),
                         ("skipped", "not buildable yet: improve@ scenarios arrive with wave 2"))
        self.assertEqual((self.rows["spec/verify-only"]["result"], self.rows["spec/verify-only"]["reason"]), ("skipped", "tier off"))

    def test_the_table_names_the_tier_the_result_and_each_id(self):
        code, out, err = cli("render", "validate-existing/wrong-packet", "validate-existing/repaired", "spec",
                             "--cases-dir", str(self.cases))
        self.assertEqual((code, err), (1, ""))
        self.assertRegex(out, r"validate-existing/wrong-packet\s+render\s+FAIL\s+P1 missed\s+C1 held")
        self.assertRegex(out, r"validate-existing/repaired\s+render\s+PASS\s+P1 caught")
        self.assertRegex(out, r"spec/verify-only\s+render\s+skipped: tier off")
        self.assertIn("  packet_contains failed for P1: the packet does not match /NEVER-IN-A-PACKET/", out)
        self.assertIn("total: 3 scenarios, 1 passed, 1 failed, 1 skipped", out)

    def test_keep_leaves_the_built_folder_and_a_second_run_into_it_is_a_usage_error(self):
        keep = self.temp / "kept"
        code, out, err = cli("render", "validate-existing/broken", "--keep", str(keep), "--cases-dir", str(self.cases))
        self.assertEqual((code, err), (0, ""), out)
        built = keep / "validate-existing" / "broken"
        self.assertTrue((built / ".shiploop-runs" / "seed" / "run" / "state.md").is_file())
        self.assertTrue((built / "work").is_dir())
        packets = list((built / ".shiploop-runs" / "seed" / "run" / "packets").glob("*.md"))
        self.assertTrue(any("PLANTED-E1" in path.read_text() for path in packets))
        again = cli("render", "validate-existing/broken", "--keep", str(keep), "--cases-dir", str(self.cases))
        self.assertEqual(again[0], 2)
        self.assertIn("validate-existing/broken already has a folder there", again[2])

    def test_without_keep_nothing_is_left_behind(self):
        scratch = self.temp / "scratch"
        scratch.mkdir()
        with mock.patch.object(tempfile, "tempdir", str(scratch)):
            code, out, err = cli("render", "validate-existing/repaired", "--cases-dir", str(self.cases))
        self.assertEqual((code, err), (0, ""), out)
        self.assertEqual(list(scratch.iterdir()), [])

    def test_the_harnesss_own_seed_and_digest_are_as_they_were(self):
        self.assertIs(run.SEED_SCRIPT, self.seed_script)
        self.assertNotIn("accept_effects", run.SEED_SCRIPT)
        self.assertEqual(boundary.fingerprint(HARNESS, None), self.digest)


# ------------------------------------------------------------------------------------------------------------- exit codes

def process(*argv: str, cwd: Path) -> subprocess.CompletedProcess:
    """The runner as a process, as a user starts it: its own working directory, stdin closed, a timeout."""
    return subprocess.run([sys.executable, "-B", str(STAGES), *argv], cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, timeout=CHILD_SECONDS, check=False, env={**os.environ, **GIT_ENV})


class ExitCodes(Catalog):
    def test_0_when_everything_selected_passed_and_the_cli_runs_from_any_working_directory(self):
        elsewhere = self.temp / "elsewhere" / "deeper"
        elsewhere.mkdir(parents=True)
        for command in ("list", "verify"):
            with self.subTest(command=command):
                done = process(command, "@outer", "--cases-dir", str(self.cases), cwd=elsewhere)
                self.assertEqual((done.returncode, done.stderr), (0, ""), done.stdout)
                self.assertIn("handoff/leftovers", done.stdout)
        done = process("list", "--json", "--cases-dir", "../../cases", cwd=elsewhere)  # a relative folder is the caller's
        self.assertEqual((done.returncode, done.stderr), (0, ""))
        self.assertEqual(len(rows(done.stdout)), 5)

    def test_1_when_a_scenario_fails(self):
        cases = self.temp / "failing"
        scenario(cases, "validate-existing", "weak", None, None, oracle=[
            {"proves": "P1", "file": "src/strings.js", "exists": True}, {"proves": "C1", "file": "src/paginate.js", "unchanged": True}])
        done = process("verify", "--cases-dir", str(cases), cwd=self.temp)
        self.assertEqual(done.returncode, 1, done.stderr)
        self.assertIn("FAIL", done.stdout)

    def test_2_for_a_usage_error_and_the_message_names_the_selector(self):
        for argv, wanted in ((("verify", "bogus"), "unknown selector 'bogus'"), (("list", "@nope"), "unknown selector '@nope'"),
                             (("list", "+nope"), "selector '+nope' selects no scenario"),
                             (("verify", "-document"), "selector '-document' selects no scenario"),
                             (("list", "--no-such-option"), "unrecognized arguments"),
                             (("verify", "--keep", "x"), "unrecognized arguments"),
                             (("live",), "are not built yet"), (("grade",), "are not built yet"), (("report",), "are not built yet"),
                             ((), "required")):
            with self.subTest(argv=argv):
                done = process(*argv, *(("--cases-dir", str(self.cases)) if argv else ()), cwd=self.temp)
                self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
                self.assertIn(wanted, done.stderr)
                self.assertEqual(done.stdout, "")

    def test_2_for_a_scenario_that_does_not_load_and_the_text_lists_every_problem(self):
        cases = self.temp / "broken-cases"
        scenario(cases, "validate-existing", "unknown-key", None, None, bogus=1)
        scenario(cases, "validate-existing", "no-about", None, None, about=None)
        for argv in (("list",), ("verify", "spec"), ("render", "--keep", str(self.temp / "k"))):
            with self.subTest(argv=argv):
                done = process(*argv, "--cases-dir", str(cases), cwd=self.temp)
                self.assertEqual(done.returncode, 2, done.stdout)
                self.assertIn("2 problems", done.stderr)
                self.assertIn("validate-existing/unknown-key: unknown key 'bogus'", done.stderr)
                self.assertIn("validate-existing/no-about: about is required", done.stderr)
        self.assertFalse((self.temp / "k").exists())

    def test_3_when_nothing_is_selected(self):
        empty = self.temp / "empty"
        empty.mkdir()
        for argv, cases in ((("list",), empty), (("verify", "all"), empty), (("list", "-all"), self.cases),
                            (("verify", "@inner", "-validate-existing"), self.cases), (("list",), self.temp / "no-such-folder")):
            with self.subTest(argv=argv, cases=cases.name):
                done = process(*argv, "--cases-dir", str(cases), cwd=self.temp)
                self.assertEqual((done.returncode, done.stdout), (3, ""), done.stderr)
                self.assertIn("nothing selected", done.stderr)

    def test_3_with_json_prints_an_empty_document_as_well(self):
        code, out, err = cli("verify", "--json", "-all", "--cases-dir", str(self.cases))
        self.assertEqual(code, 3)
        self.assertIn("nothing selected", err)
        self.assertEqual(json.loads(out)["scenarios"], [])

    def test_the_help_names_the_commands_and_says_what_is_not_built_yet(self):
        for argv in (("--help",), ("-h",), ("verify", "--help"), ("render", "-h")):
            with self.subTest(argv=argv):
                done = process(*argv, cwd=self.temp)
                self.assertEqual((done.returncode, done.stderr), (0, ""))
                self.assertRegex(done.stdout, r"live, grade and report are not built yet \(step 3")
        top = process("--help", cwd=self.temp).stdout
        for command in ("list", "verify", "render"):
            self.assertIn(command, top)
        self.assertIn("--keep", process("render", "--help", cwd=self.temp).stdout)
        self.assertNotIn("--keep", process("verify", "--help", cwd=self.temp).stdout)

    def test_asking_for_a_command_that_is_not_built_names_it_and_exits_2(self):
        for name in ("live", "grade", "report"):
            with self.subTest(name=name):
                done = process(name, "validate-existing", cwd=self.temp)
                self.assertEqual((done.returncode, done.stdout), (2, ""))
                self.assertIn(f"asked for '{name}'", done.stderr)
                self.assertRegex(done.stderr, r"live, grade and report are not built yet \(step 3")
                self.assertNotIn("invalid choice", done.stderr)
        code, out, err = cli("live", "@inner")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("not built yet", err)

    def test_the_commands_that_are_not_built_are_not_stubbed(self):
        text = STAGES.read_text()
        for name in ("live", "grade", "report"):
            self.assertNotRegex(text, rf"^def (cmd_)?{name}\b", name)
        self.assertEqual(stages.COMMANDS, ("list", "verify", "render"))


# ---------------------------------------------------------------------------------------------------------------- boundary

# ------------------------------------------------------------------------------------------------------- the shipped scenarios

class Shipped(unittest.TestCase):
    """verify and render over test/shiploop_e2e/stage_cases itself (about 5 s): a scenario that stopped holding, or a packet
    wording that no longer carries what a scenario's render checks look for, fails here and not only in a by-hand run."""
    ALL = ("validate-existing/all-match", "validate-existing/broken-works-small-fix", "validate-existing/wrong-check")

    def run_json(self, *argv: str) -> dict:
        done = process(*argv, "--json", cwd=Path(tempfile.gettempdir()))
        self.assertEqual(done.returncode, 0, done.stdout[-3000:] + done.stderr)
        return json.loads(done.stdout)

    def test_every_shipped_scenario_verifies(self):
        found = rows(json.dumps(self.run_json("verify")))
        self.assertLessEqual(set(self.ALL), set(found))
        for sid, row in found.items():
            with self.subTest(sid):
                self.assertIn(row["result"], ("pass", "skipped"), row["problems"])
                if row["result"] == "pass":
                    self.assertTrue(row["ids"])
                    self.assertTrue(all(word in ("caught", "held") for word in row["ids"].values()), row["ids"])
        self.assertEqual(found["validate-existing/all-match"]["result"], "skipped")  # render only: nothing to grade
        for sid in ("validate-existing/broken-works-small-fix", "validate-existing/wrong-check"):
            self.assertEqual(found[sid]["result"], "pass")
            self.assertEqual(set(found[sid]["ids"].values()), {"caught", "held"})

    def test_every_shipped_scenario_renders(self):
        found = rows(json.dumps(self.run_json("render")))
        self.assertLessEqual(set(self.ALL), set(found))
        for sid, row in found.items():
            with self.subTest(sid):
                self.assertIn(row["result"], ("pass", "skipped"), row["problems"])
        for sid in self.ALL:
            self.assertEqual(found[sid]["result"], "pass", found[sid]["problems"])
            self.assertNotIn("not exercised", found[sid]["ids"].values())
        self.assertFalse(found["validate-existing/all-match"]["stage"]["issued"])
        self.assertTrue(found["validate-existing/wrong-check"]["stage"]["issued"])

    def test_the_selectors_of_the_guides_example_select_something_today(self):
        document = self.run_json("verify", "@inner", "-validate-existing/all-match", "+catch")
        self.assertEqual(sorted(row["id"] for row in document["scenarios"]),
                         ["validate-existing/broken-works-small-fix", "validate-existing/wrong-check"])
        # and an exclude that selects nothing is the usage error the guide says it is
        done = process("verify", "@inner", "-implement", cwd=Path(tempfile.gettempdir()))
        self.assertEqual(done.returncode, 2)
        self.assertIn("selects no scenario", done.stderr)


class Boundary(unittest.TestCase):
    def test_the_runner_is_outside_the_evaluator_digest_and_the_qualification_snapshot(self):
        self.assertTrue(STAGES.is_file())
        evaluator, graded = set(boundary.evaluator_files(HARNESS)), set(boundary.oracle_files(HARNESS))
        self.assertNotIn(STAGES, evaluator)
        self.assertNotIn(STAGES, graded)
        self.assertFalse(any(path.parent.name in ("stage_suite", "stage_cases") for path in evaluator | graded))
        snapshot_files = boundary.qualification_snapshot(HARNESS)["files"]
        self.assertFalse([name for name in snapshot_files if "/stage_suite/" in name or "/stage_cases/" in name])
        self.assertFalse([name for name in snapshot_files if name.startswith("test/shiploop-e2e-stage")])

    def test_no_stage_file_is_in_the_top_level_of_the_harness(self):
        self.assertEqual(sorted(path.name for path in HARNESS.iterdir() if path.is_file() and path.name.startswith("stage")), [])

    def test_adding_or_changing_the_runner_leaves_the_digest_where_it_was(self):
        with tempfile.TemporaryDirectory(prefix="stages-boundary-") as temp:
            harness = lay(Path(temp), {"run.py": "x = 1\n", "checks/c.py": "y = 2\n", "SPEC.md": "s\n"})
            before = boundary.fingerprint(harness, None)
            lay(harness, {"stage_suite/stages.py": "z = 3\n", "stage_cases/validate-existing/s/scenario.json": "{}\n"})
            self.assertEqual(boundary.fingerprint(harness, None), before)
            lay(harness, {"stage_suite/stages.py": "z = 4\n"})
            self.assertEqual(boundary.fingerprint(harness, None), before)
            lay(harness, {"run.py": "x = 2\n"})
            self.assertNotEqual(boundary.fingerprint(harness, None)["evaluator"], before["evaluator"])

    def test_the_candidate_may_not_change_the_runner_or_its_test(self):
        for path in ("test/shiploop_e2e/stage_suite/stages.py", "test/shiploop-e2e-stages.test.py"):
            with self.subTest(path=path):
                self.assertFalse(boundary.candidate_path(path))

    def test_the_runner_uses_the_builder_and_the_check_engine_without_copying_them(self):
        text = STAGES.read_text()
        for used in ("sb.discover(", "sb.render(", "sb.reference_bundle(", "stage_oracle.run_checks(", "stage_oracle.verdict("):
            self.assertIn(used, text)
        for copied in ("def run_check", "def validate_checks", "class Bundle", "def build(", "def discover(", "SEED_SCRIPT"):
            self.assertNotIn(copied, text)


if __name__ == "__main__":
    unittest.main()
