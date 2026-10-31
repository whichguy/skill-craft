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
  working directory with its stdin closed.
- ``live``, ``grade`` and ``report`` (class LiveSelection and following): ``live`` selects only scenarios with the live tier on
  and says so when none, skips the ones the builder cannot build yet, prints the plan (scenarios x samples, the driver, a cost
  note), builds and launches nothing for ``--dry-run`` (also with the real default host), refuses before it creates anything
  (exit 2, ``Nothing was started.``) for a host whose binary is missing or that is not signed in, an Ollama that is not ready, a
  ``--ref`` without the seed seam, an overlay that does not load, an existing ``--out`` and a misused test-only fake host, and
  takes ``--samples`` over the scenario's default. With the test-only fake host (never a model) it runs real samples as
  subprocesses ``--jobs`` at once, records a sample that crashes or is killed for time as not run (never a pass, the others go
  on), exits 0 / 1 by the ``live.pass`` rule, and ``grade`` and ``report`` (also ``--compare``, refused for different drivers)
  read the results root it left.
  Also: ``--timeout`` must be a finite positive number (nan, inf and 1e400 are refused); the hidden ``live-sample`` command's exit
  codes (pass, fail, refused, crashed, stopped); the plan's ``min(rule, samples)``; no sample starts once ``live`` was told to end;
  the parent's hard limit is ``--timeout`` plus ``SAMPLE_GRACE_SECONDS``; a ledger sweep that could not see or stop a host is
  printed and kept in error.txt; the Signals cases (an ignored SIGHUP stays ignored, two SIGTERMs or a SIGTERM and a SIGINT
  escalate, a host ended only by the sample's own handler, one ended only by the ledger sweep).
- The shipped scenarios (test/shiploop_e2e/stage_cases) verify and render, and the guide's example selectors select something.
- The runner is outside the evaluator digest and the qualification snapshot, as the probes are (test/shiploop-e2e-sdlc-probes.test.py).
"""
from __future__ import annotations

import ast
import contextlib
import copy
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
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
import sessionlog  # noqa: E402
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

    def test_a_render_scenario_with_no_render_check_fails_and_is_never_a_pass(self):
        # A scenario that asks for the render tier and lists no render check would otherwise "pass" having proved nothing.
        cases = self.temp / "no-check-cases"
        scenario(cases, "validate-existing", "no-check", None, {}, tiers=["render"], render=[])
        code, out, err = cli("render", "--json", "--cases-dir", str(cases))
        row = rows(out)["validate-existing/no-check"]
        self.assertEqual((code, err), (1, ""))
        self.assertEqual(row["result"], "fail")
        self.assertIn("the scenario has no render check", row["problems"])
        self.assertEqual((row["checks"], row["tier"]), ([], "render"))
        self.assertEqual(json.loads(out)["total"], {"scenarios": 1, "passed": 0, "failed": 1, "skipped": 0})

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
                             ((), "required")):
            with self.subTest(argv=argv):
                done = process(*argv, *(("--cases-dir", str(self.cases)) if argv else ()), cwd=self.temp)
                self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
                self.assertIn(wanted, done.stderr)
                self.assertEqual(done.stdout, "")

    def test_2_for_grade_and_report_without_their_argument(self):
        for argv, wanted in ((("grade",), "the following arguments are required: OUTPUT"),
                             (("report",), "the following arguments are required: ROOT"),
                             (("report", str(self.temp / "no-such-root")), "is not a folder"),
                             (("live", "--samples", "x"), "invalid int value")):
            with self.subTest(argv=argv):
                done = process(*argv, cwd=self.temp)
                self.assertEqual((done.returncode, done.stdout), (2, ""), done.stderr)
                self.assertIn(wanted, done.stderr)
                self.assertNotIn("Traceback", done.stderr)

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

    def test_the_help_names_the_commands_and_their_options_and_hides_the_sample_subcommand(self):
        for argv in (("--help",), ("-h",), ("verify", "--help"), ("render", "-h"), ("live", "--help"), ("grade", "-h"),
                     ("report", "--help")):
            with self.subTest(argv=argv):
                done = process(*argv, cwd=self.temp)
                self.assertEqual((done.returncode, done.stderr), (0, ""))
                self.assertNotIn("not built yet", done.stdout)
                self.assertNotIn("live-sample", done.stdout)
        top = process("--help", cwd=self.temp).stdout
        for command in ("list", "verify", "render", "live", "grade", "report"):
            self.assertIn(command, top)
        self.assertIn("--keep", process("render", "--help", cwd=self.temp).stdout)
        self.assertNotIn("--keep", process("verify", "--help", cwd=self.temp).stdout)
        live = process("live", "--help", cwd=self.temp).stdout
        for option in ("--samples", "--jobs", "--host", "--model", "--effort", "--backend", "--ref", "--overlay", "--timeout", "--out",
                       "--dry-run", "--cases-dir"):
            self.assertIn(option, live)
        self.assertIn("--compare", process("report", "--help", cwd=self.temp).stdout)

    def test_the_live_commands_exist_and_the_sample_subcommand_is_hidden_but_runs(self):
        self.assertEqual(stages.COMMANDS, ("list", "verify", "render", "live", "grade", "report"))
        self.assertEqual(stages.HIDDEN_COMMANDS, ("live-sample",))
        for name in ("cmd_live", "cmd_grade", "cmd_report", "cmd_live_sample"):
            self.assertTrue(callable(getattr(stages, name)), name)
        done = process("live-sample", "--help", cwd=self.temp)  # reachable by the parent, absent from the interface
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("--sample", done.stdout)


# ---------------------------------------------------------------------------------------------------------------- boundary

# ------------------------------------------------------------------------------------------------------- the shipped scenarios

@unittest.skipUnless(shutil.which("node"), "the shipped scenarios run `node -e` / `node --test` and need node on PATH (install node to "
                     "run this class); the tests on synthetic scenarios still run")
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


# ------------------------------------------------------------------------------------------------------------------ the live tier

def fake_host_script() -> str:
    """The fake host of test/shiploop-e2e-stage-live.test.py (the live-core tests), read from its source: the module is not
    imported, so none of its set-up runs here."""
    tree = ast.parse((ROOT / "test" / "shiploop-e2e-stage-live.test.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(target, "id", None) == "FAKE_HOST" for target in node.targets):
            return textwrap.dedent(node.value.args[0].value)
    raise AssertionError("FAKE_HOST not found in the live tests")


FAKE_ENV = (stages.FAKE_HOST_ENV, stages.FAKE_CONFIG_ENV, stages.TEST_ONLY_ENV)
BROKEN = "validate-existing/broken-works-small-fix"
WRONG = "validate-existing/wrong-check"


def clean_env(**extra: str) -> dict:
    """The environment of a child: ours without the fake-host switches (a test turns them on explicitly), the hermetic git
    settings, and `extra`."""
    env = {key: value for key, value in os.environ.items() if key not in FAKE_ENV}
    return {**env, **GIT_ENV, "SHIPLOOP_KEEPALIVE": "off", **extra}


def process_env(*argv: str, cwd: Path, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", str(STAGES), *argv], cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, timeout=CHILD_SECONDS, check=False, env=env)


class NoLaunch(Catalog):
    """Patches that fail the test when anything is built or launched: the process launcher, the sample, the builder and the
    results-root maker; a ``live-sample`` process raises AssertionError instead of starting, and every other process started
    through subprocess.Popen (the read-only git a --ref check asks) is recorded (``spawned``) and still runs."""

    def setUp(self):
        super().setUp()
        self.spawned: list = []
        real = subprocess.Popen

        def spy(*args, **kwargs):
            argv = args[0] if args else kwargs.get("args")
            if isinstance(argv, list) and "live-sample" in argv:  # a sample is a model-costing process: never run one here
                raise AssertionError(f"a live sample was started: {argv[:5]}")
            self.spawned.append(argv)
            return real(*args, **kwargs)

        patcher = mock.patch("subprocess.Popen", spy)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.guards = {}
        for name, target in (("launch", mock.patch.object(run, "launch")), ("sample", mock.patch.object(stages.stage_live, "run_sample")),
                             ("build", mock.patch.object(sb, "build")), ("root", mock.patch.object(run, "new_output_dir"))):
            self.guards[name] = target.start()
            self.addCleanup(target.stop)
        environment = mock.patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        for key in FAKE_ENV:
            os.environ.pop(key, None)

    def assertNothingStarted(self, git: bool = False):
        for name, guard in self.guards.items():
            with self.subTest(guard=name):
                guard.assert_not_called()
        # no process at all, except the read-only git a --ref check asks
        started = [argv for argv in self.spawned if not (git and isinstance(argv, list) and argv[:1] == ["git"])]
        self.assertEqual(started, [], "a process was started")


class LiveSelection(NoLaunch):
    def test_live_selects_only_the_scenarios_with_the_live_tier_on_and_says_which_are_not(self):
        code, out, err = cli("live", "--dry-run", "--cases-dir", str(self.cases))
        self.assertEqual((code, err), (0, ""))
        self.assertIn("validate-existing/broken: 3 samples", out)
        for sid in ("validate-existing/repaired", "spec/outcome-dropped", "handoff/leftovers"):
            self.assertNotIn(f"  {sid}: ", out)
        self.assertIn("not live (tier off): spec/outcome-dropped, validate-existing/repaired, handoff/leftovers", out)  # stage order
        self.assertNothingStarted()

    def test_a_scenario_the_builder_cannot_build_yet_is_skipped_with_the_reason(self):
        code, out, err = cli("live", "--dry-run", "--cases-dir", str(self.cases))
        self.assertEqual(code, 0, err)
        self.assertNotIn("  improve@spec/missing-outcome: ", out)
        self.assertRegex(out, r"skipped, not buildable yet: improve@spec/missing-outcome \(improve@ scenarios arrive")

    def test_nothing_with_the_live_tier_on_is_exit_3_and_says_so(self):
        for tokens in (("validate-existing/repaired",), ("@outer",), ("improve@spec",)):
            with self.subTest(tokens=tokens):
                code, out, err = cli("live", *tokens, "--dry-run", "--cases-dir", str(self.cases))
                self.assertEqual((code, out), (3, ""))
                self.assertRegex(err, r"nothing selected: none of the \d+ scenarios? selected can run live")
        self.assertIn("off in validate-existing/repaired", cli("live", "validate-existing/repaired", "--cases-dir", str(self.cases))[2])
        self.assertIn("not buildable yet: improve@spec/missing-outcome", cli("live", "improve@spec", "--cases-dir", str(self.cases))[2])
        self.assertNothingStarted()

    def test_an_empty_selection_and_an_unknown_selector_are_the_runners_own(self):
        self.assertEqual(cli("live", "-all", "--cases-dir", str(self.cases))[0], 3)
        code, out, err = cli("live", "bogus", "--cases-dir", str(self.cases))
        self.assertEqual(code, 2)
        self.assertIn("unknown selector 'bogus'", err)
        code, out, err = cli("live", "@inner", "-validate-existing/broken", "--cases-dir", str(self.cases))
        self.assertEqual((code, out), (3, ""))  # an exclude is a selector, not an option
        self.assertNothingStarted()

    def test_the_default_samples_are_the_scenarios_and_samples_overrides_them(self):
        cases = self.temp / "sampled"
        scenario(cases, "validate-existing", "two-of-two", None, None, live={"samples": 2, "pass": 1})
        scenario(cases, "validate-existing", "default", None, None)
        code, out, err = cli("live", "--dry-run", "--json", "--cases-dir", str(cases))
        self.assertEqual(code, 0, err)
        planned = json.loads(out)["scenarios"]
        self.assertEqual(planned["validate-existing/two-of-two"], {"samples": 2, "required": 1, "rule": 1})
        self.assertEqual(planned["validate-existing/default"], {"samples": 3, "required": 3, "rule": "all"})
        code, out, err = cli("live", "--dry-run", "--json", "--samples", "5", "--cases-dir", str(cases))
        planned = json.loads(out)["scenarios"]
        self.assertEqual(planned["validate-existing/two-of-two"], {"samples": 5, "required": 1, "rule": 1})
        self.assertEqual(planned["validate-existing/default"], {"samples": 5, "required": 5, "rule": "all"})
        code, out, err = cli("live", "--dry-run", "--samples", "1", "--cases-dir", str(cases))  # a rule is never above the samples
        self.assertIn("validate-existing/two-of-two: 1 sample, passes when 1 pass", out)
        self.assertNothingStarted()


class PlanArithmetic(Temp):
    def test_the_rule_never_asks_for_more_samples_than_there_are(self):
        """The schema keeps ``live.pass`` within ``live.samples``, but ``--samples`` can lower the samples below the rule."""
        sc = sb.load("validate-existing/s", self.one("s", live={"samples": 4, "pass": 3}))

        def plan(samples):
            return stages._sample_plan(sc, type("Args", (), {"samples": samples})())

        self.assertEqual(plan(None), {"samples": 4, "required": 3, "rule": 3})
        self.assertEqual(plan(2), {"samples": 2, "required": 2, "rule": 3}, "two samples cannot be asked to pass three times")
        self.assertEqual(plan(3), {"samples": 3, "required": 3, "rule": 3})
        self.assertEqual(plan(9), {"samples": 9, "required": 3, "rule": 3})
        everything = sb.load("validate-existing/t", self.one("t", live={"samples": 4, "pass": "all"}))
        self.assertEqual(stages._sample_plan(everything, type("Args", (), {"samples": 2})()), {"samples": 2, "required": 2, "rule": "all"})


class LiveDryRun(NoLaunch):
    def test_dry_run_prints_the_plan_builds_nothing_launches_nothing_and_exits_0(self):
        out_dir = self.temp / "never"
        code, out, err = cli("live", "validate-existing/broken", "--dry-run", "--samples", "2", "--jobs", "2", "--timeout", "90",
                             "--out", str(out_dir), "--cases-dir", str(self.cases))
        self.assertEqual((code, err), (0, ""))
        for wanted in ("live plan: 1 scenario x samples = 2 samples, 2 at once", "validate-existing/broken: 2 samples, passes when 2 pass",
                       "driver: codex/gpt-6.1-terra/xhigh", "timeout: 90 s per sample", f"results root: {out_dir}",
                       "costs money", "dry run: nothing was built and nothing was launched"):
            self.assertIn(wanted, out)
        self.assertFalse(out_dir.exists())
        self.assertNothingStarted()

    def test_a_sample_has_a_finite_timeout_unless_the_command_line_says_otherwise(self):
        code, out, err = cli("live", "validate-existing/broken", "--dry-run", "--cases-dir", str(self.cases))
        self.assertEqual((code, err), (0, ""))
        self.assertIn(f"timeout: {stages.DEFAULT_TIMEOUT} s per sample", out)
        self.assertEqual(stages.DEFAULT_TIMEOUT, 3600)
        document = json.loads(cli("live", "validate-existing/broken", "--dry-run", "--json", "--cases-dir", str(self.cases))[1])
        self.assertEqual(document["timeout"], stages.DEFAULT_TIMEOUT)
        self.assertEqual(cli("live", "validate-existing/broken", "--dry-run", "--timeout", "5", "--cases-dir", str(self.cases))[0], 0)
        self.assertNothingStarted()

    def test_dry_run_with_the_real_default_host_starts_no_process_and_asks_nothing_of_the_host(self):
        with mock.patch.object(stages.hosts.CodexHost, "env", side_effect=AssertionError("the host was asked for its environment")), \
             mock.patch.object(stages.hosts, "ollama_ready", side_effect=AssertionError("the network was asked")), \
             mock.patch.object(stages.shutil, "which", side_effect=AssertionError("the binary was looked for")):
            code, out, err = cli("live", "--dry-run")  # the shipped scenarios, the default host and no other option
        self.assertEqual((code, err), (0, ""))
        self.assertIn("driver: codex/gpt-6.1-terra/xhigh", out)
        self.assertIn(f"results root: {Path(tempfile.gettempdir())}", out)
        self.assertIn("validate-existing/broken-works-small-fix: 3 samples", out)
        self.assertIn("validate-existing/wrong-check: 3 samples", out)
        self.assertNothingStarted()

    def test_dry_run_json_is_one_document_with_the_plan_and_the_human_text_goes_to_stderr(self):
        code, out, err = cli("live", "--dry-run", "--json", "--host", "claude", "--backend", "anthropic", "--model", "m", "--effort", "low",
                             "--cases-dir", str(self.cases))
        document = json.loads(out)
        self.assertEqual(code, 0)
        self.assertTrue(document["dry_run"])
        self.assertEqual(document["driver"], {"host": "claude", "backend": "anthropic", "model": "m", "effort": "low"})
        self.assertIn("live plan", err)
        self.assertNothingStarted()

    def test_the_driver_defaults_are_slices_and_the_options_override_them(self):
        for argv, wanted in ((("--host", "grok"), "grok/grok-4.7/medium"), (("--host", "claude"), "claude:ollama/"),
                             (("--host", "claude", "--backend", "anthropic"), "claude:anthropic/claude-sonnet-5-5/default"),
                             (("--model", "x", "--effort", "low"), "codex/x/low")):
            with self.subTest(argv=argv):
                code, out, err = cli("live", "--dry-run", *argv, "--cases-dir", str(self.cases))
                self.assertEqual((code, err), (0, ""))
                self.assertIn(f"driver: {wanted}", out)

    def test_a_ref_with_the_seed_seam_is_planned_and_an_unknown_ref_is_refused(self):
        code, out, err = cli("live", "--dry-run", "--ref", "HEAD", "--cases-dir", str(self.cases))
        self.assertEqual((code, err), (0, ""))
        self.assertIn("ref: HEAD", out)
        code, out, err = cli("live", "--dry-run", "--ref", "no-such-ref-zzz", "--cases-dir", str(self.cases))
        self.assertEqual((code, out), (2, ""))
        self.assertIn("unknown git ref", err)
        self.assertTrue(err.rstrip().endswith("Nothing was started."))
        self.assertNothingStarted(git=True)


class LiveRefusals(NoLaunch):
    def refused(self, *argv: str, wanted: str, out_dir: Path | None = None) -> str:
        out_dir = out_dir or self.temp / "results"
        code, out, err = cli("live", "validate-existing/broken", *argv, "--out", str(out_dir), "--cases-dir", str(self.cases))
        self.assertEqual(code, 2, err)
        self.assertIn(wanted, err)
        self.assertTrue(err.rstrip().endswith("Nothing was started."), err)
        self.assertNotIn("Traceback", err)
        self.assertFalse(out_dir.exists(), "a refusal creates no results root")
        self.assertNothingStarted()
        return err

    def test_a_ref_whose_navigator_has_no_accept_effects_is_refused_naming_the_reason(self):
        why = "ref old (0123456789ab) has no accept_effects in its navigator, the seed seam a stage scenario is built through"
        with mock.patch.object(stages.stage_live, "ref_seam_gap", return_value=why):
            self.refused("--ref", "old", wanted="has no accept_effects in its navigator")

    def test_a_host_on_ollama_that_does_not_answer_is_refused(self):
        with mock.patch.object(stages.shutil, "which", return_value="/bin/claude"), \
             mock.patch.object(stages.hosts, "ollama_ready", return_value="the Ollama server at http://x does not answer (down)"):
            self.refused("--host", "claude", wanted="--backend ollama: the Ollama server at http://x does not answer")

    def test_an_overlay_that_does_not_load_is_refused(self):
        bad = self.temp / "overlay.json"
        bad.write_text("{}")
        self.refused("--overlay", str(self.temp / "missing.json"), wanted="--overlay")
        self.refused("--overlay", str(bad), wanted="an overlay needs a non-empty `edits` list", out_dir=self.temp / "results-2")

    def test_an_existing_results_root_is_refused_and_left_alone(self):
        taken = self.temp / "taken"
        taken.mkdir()
        (taken / "keep.txt").write_text("x")
        code, out, err = cli("live", "validate-existing/broken", "--out", str(taken), "--cases-dir", str(self.cases))
        self.assertEqual(code, 2)
        self.assertIn("already exists", err)
        self.assertEqual([path.name for path in taken.iterdir()], ["keep.txt"])
        self.assertNothingStarted()

    def test_a_backend_the_host_does_not_have_and_numbers_that_are_not_positive_are_usage_errors(self):
        for argv, wanted in ((("--host", "codex", "--backend", "ollama"), "--backend ollama is a Claude host option"),
                             (("--samples", "0"), "--samples must be a positive number"), (("--jobs", "0"), "--jobs must be a positive number"),
                             (("--timeout", "-5"), "--timeout must be a positive number")):
            with self.subTest(argv=argv):
                code, out, err = cli("live", "validate-existing/broken", *argv, "--cases-dir", str(self.cases))
                self.assertEqual((code, out), (2, ""))  # a usage error comes before the plan
                self.assertIn(wanted, err)
        self.assertNothingStarted()

    def test_a_timeout_that_is_not_finite_is_refused_inf_included(self):
        """nan and inf (and 1e400, which float() reads as inf) pass a plain `<= 0` check and would give a sample no bound: inf is
        refused too, since every sample is bounded (DEFAULT_TIMEOUT) and `--timeout` plus the grace is the parent's kill time."""
        for value in ("nan", "inf", "1e400"):
            with self.subTest(timeout=value):
                code, out, err = cli("live", "validate-existing/broken", "--dry-run", "--timeout", value, "--cases-dir", str(self.cases))
                self.assertEqual((code, out), (2, ""))
                self.assertIn("--timeout must be a positive number", err)
                self.assertRegex(err, r"nan or inf|finite")
        for value in ("0.5", "3600", "1e6"):
            with self.subTest(timeout=value):
                self.assertEqual(cli("live", "validate-existing/broken", "--dry-run", "--timeout", value, "--cases-dir", str(self.cases))[0], 0)
        self.assertNothingStarted()

    def test_the_fake_host_is_refused_without_the_second_switch_and_when_it_is_not_a_file(self):
        script = self.temp / "fake.py"
        script.write_text("")
        for env, wanted in (({stages.FAKE_HOST_ENV: str(script)}, f"{stages.FAKE_HOST_ENV} is a test-only route"),
                            ({stages.FAKE_HOST_ENV: str(script), stages.TEST_ONLY_ENV: "1"}, "test-only route"),
                            ({stages.FAKE_HOST_ENV: str(script), stages.TEST_ONLY_ENV: "yes"}, "test-only route"),
                            ({stages.FAKE_HOST_ENV: str(self.temp / "none.py"), stages.TEST_ONLY_ENV: stages.TEST_ONLY_VALUE}, "is not a file"),
                            ({stages.FAKE_HOST_ENV: str(script), stages.TEST_ONLY_ENV: stages.TEST_ONLY_VALUE,
                              stages.FAKE_CONFIG_ENV: "[1"}, "is not JSON"),
                            ({stages.FAKE_HOST_ENV: str(script), stages.TEST_ONLY_ENV: stages.TEST_ONLY_VALUE,
                              stages.FAKE_CONFIG_ENV: "[1]"}, "must be a JSON object")):
            with self.subTest(env=sorted(env)):
                with mock.patch.dict(os.environ, env):
                    code, out, err = cli("live", "validate-existing/broken", "--cases-dir", str(self.cases))
                self.assertEqual((code, out), (2, ""))  # the driver is resolved before the plan is printed
                self.assertIn(wanted, err)
                self.assertTrue(err.rstrip().endswith("Nothing was started."), err)
        self.assertNothingStarted()

    def test_the_second_switch_alone_changes_nothing(self):
        with mock.patch.dict(os.environ, {stages.TEST_ONLY_ENV: stages.TEST_ONLY_VALUE}):
            code, out, err = cli("live", "validate-existing/broken", "--dry-run", "--cases-dir", str(self.cases))
        self.assertEqual((code, err), (0, ""))
        self.assertIn("driver: codex/", out)
        self.assertNotIn("FAKE HOST", out)


class HostReadiness(Temp):
    """A missing binary and an unsigned host are refusals, not tracebacks: real child processes, a PATH of our own, and no
    credential anywhere (CODEX_HOME is an empty folder)."""

    def child(self, bindir: Path, *argv: str, **env: str) -> tuple[subprocess.CompletedProcess, Path]:
        out_dir = self.temp / "results"
        cases = self.one()
        done = process_env("live", "validate-existing/s", *argv, "--out", str(out_dir), "--cases-dir", str(cases), cwd=self.temp,
                           env=clean_env(PATH=str(bindir), CODEX_HOME=str(self.temp / "codex-home"), **env))
        return done, out_dir

    def assertRefused(self, done: subprocess.CompletedProcess, out_dir: Path, wanted: str):
        self.assertEqual((done.returncode, done.stdout.count("Traceback")), (2, 0), done.stderr)
        self.assertNotIn("Traceback", done.stderr)
        self.assertIn(wanted, done.stderr)
        self.assertTrue(done.stderr.rstrip().endswith("Nothing was started."), done.stderr)
        self.assertFalse(out_dir.exists())

    def test_a_host_binary_that_is_not_found_is_a_refusal(self):
        empty = self.temp / "empty-bin"
        empty.mkdir()
        done, out_dir = self.child(empty)
        self.assertRefused(done, out_dir, "the codex host's binary 'codex' was not found")
        done, out_dir = self.child(empty, "--host-bin", str(self.temp / "nowhere" / "codex"))
        self.assertRefused(done, out_dir, "was not found")

    def test_a_host_that_is_not_signed_in_is_a_refusal_naming_what_is_missing(self):
        bindir = self.temp / "bin"
        bindir.mkdir()
        binary = bindir / "codex"
        binary.write_text("#!/bin/sh\nexit 0\n")
        binary.chmod(0o755)
        (self.temp / "codex-home").mkdir()
        done, out_dir = self.child(bindir)
        self.assertRefused(done, out_dir, "Codex is not signed in")
        self.assertIn("auth.json is missing", done.stderr)
        self.assertEqual(list((self.temp / "codex-home").iterdir()), [], "the host's environment was made in a scratch folder")

    def test_the_readiness_check_prints_no_credential_or_environment(self):
        bindir = self.temp / "bin"
        bindir.mkdir()
        binary = bindir / "codex"
        binary.write_text("#!/bin/sh\nexit 0\n")
        binary.chmod(0o755)
        done, _ = self.child(bindir, OPENAI_API_KEY="sk-secret-0123456789", ANTHROPIC_API_KEY="sk-ant-secret-0123456789")
        self.assertNotIn("secret", done.stdout + done.stderr)


# ------------------------------------------------------------------------------------------------------ live, with the fake host

class FakeRoute(unittest.TestCase):
    """Real `stages.py live` processes with the test-only fake host: no model, no network, a symlinked plugin (this checkout's
    ShipLoop) so nothing is built. Each run builds a scenario for real (about 2 s) and the stop polls every run.POLL_SECONDS (2 s)."""

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="stages-live-")
        cls.tmp = Path(cls.temp.name).resolve()
        cls.script = cls.tmp / "fake_host.py"
        cls.script.write_text(fake_host_script())
        plugin = cls.tmp / "plugin"
        (plugin / "skills").mkdir(parents=True)
        (plugin / "skills" / "shiploop").symlink_to(ROOT / "skills" / "shiploop")
        cls.plugin = plugin
        cls.count = 0

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    SECRET = "sk-ant-test-credential-0123456789abcdef"  # in the child's environment only: it must reach no file of a root

    @classmethod
    def env(cls, config: dict, **extra: str) -> dict:
        return clean_env(ANTHROPIC_API_KEY=cls.SECRET, **{stages.FAKE_HOST_ENV: str(cls.script), stages.TEST_ONLY_ENV: stages.TEST_ONLY_VALUE,
                            stages.FAKE_CONFIG_ENV: json.dumps({"plugin_dir": str(cls.plugin), "linger": 120, **config}), **extra})

    @classmethod
    def live(cls, *argv: str, config: dict, cases: Path | None = None) -> tuple[subprocess.CompletedProcess, Path]:
        cls.count += 1
        root = cls.tmp / f"results-{cls.count}"
        done = process_env("live", *argv, "--out", str(root), *(("--cases-dir", str(cases)) if cases else ()), cwd=cls.tmp,
                           env=cls.env(config))
        return done, root


class GoodRun(FakeRoute):
    """Two samples of wrong-check, two at once, by a fake that does the right thing (reference/good)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.done, cls.root = cls.live(WRONG, "--samples", "2", "--jobs", "2",
                                      config={"mode": "act", "reference": "{scenario_dir}/reference/good"})

    def test_it_exits_0_prints_the_plan_each_sample_and_the_matrix(self):
        self.assertEqual((self.done.returncode, self.done.stderr), (0, ""), self.done.stdout[-2000:])
        for wanted in ("live plan: 1 scenario x samples = 2 samples, 2 at once", "TEST-ONLY FAKE HOST", "PASS  validate-existing/wrong-check #1",
                       "PASS  validate-existing/wrong-check #2", "live: every scenario met its pass rule"):
            self.assertIn(wanted, self.done.stdout)
        header = next(line for line in self.done.stdout.splitlines() if line.startswith("scenario"))
        self.assertEqual(header.split(), ["scenario", "ran", "P1", "C1", "C2", "overshoot", "pass", "rule", "driver"])

    def test_the_results_root_holds_a_sample_folder_per_sample_and_the_plan(self):
        for number in (1, 2):
            sample = self.root / "validate-existing" / "wrong-check" / str(number)
            for name in ("stage-result.json", "invocation.json", "seed-export", "export", "sessions.jsonl", "packet-archive"):
                self.assertTrue((sample / name).exists(), (number, name))
            result = json.loads((sample / "stage-result.json").read_text())
            self.assertEqual((result["sample"], result["pass"], result["host"], result["model"]), (number, True, "fake", "fake-model"))
        plan = json.loads((self.root / "live-plan.json").read_text())
        self.assertEqual(plan["scenarios"], {WRONG: {"samples": 2, "required": 2, "planted": ["P1"], "controls": ["C1", "C2"]}})
        self.assertTrue(plan["fake_host"])
        self.assertEqual(plan["driver"]["host"], "fake")
        self.assertTrue((self.root / ".logs").is_dir())

    def test_the_two_samples_were_separate_processes_that_overlapped(self):
        spans = []
        for number in (1, 2):
            rows = sessionlog.read(self.root / WRONG / str(number))
            spans.append((rows[0]["t"], rows[-1]["end"]["t"]))
        self.assertLess(max(spans[0][0], spans[1][0]), min(spans[0][1], spans[1][1]), spans)

    def test_report_prints_the_same_matrix_and_json_the_same_data(self):
        shown = process_env("report", str(self.root), cwd=self.tmp, env=clean_env())
        self.assertEqual((shown.returncode, shown.stderr), (0, ""))
        self.assertIn("validate-existing/wrong-check", shown.stdout)
        self.assertRegex(shown.stdout, r"wrong-check\s+2/2\s+2/2\s+2/2\s+2/2\s+0/2\s+2/2\s+met\s+fake/fake-model/default")
        as_json = process_env("report", str(self.root), "--json", cwd=self.tmp, env=clean_env())
        document = json.loads(as_json.stdout)["report"]
        found = document["scenarios"][0]
        self.assertEqual((found["id"], found["pass"], found["ran"], found["rule"]), (WRONG, {"k": 2, "n": 2}, 2, {"required": 2, "met": True}))
        self.assertEqual(found["ids"]["P1"], {"kind": "caught", "k": 2, "n": 2})
        self.assertEqual(document["drivers"], ["fake/fake-model/default"])

    def test_grade_regrades_one_sample_from_its_files_and_prints_the_verdict(self):
        sample = self.root / WRONG / "1"
        before = json.loads((sample / "stage-result.json").read_text())
        done = process_env("grade", str(sample), cwd=self.tmp, env=clean_env())
        self.assertEqual((done.returncode, done.stderr), (0, ""), done.stdout)
        self.assertIn("PASS: process ok, accepted ok, no_overshoot ok, oracle ok", done.stdout)
        self.assertIn("P1 caught", done.stdout)
        self.assertIn("C1 held", done.stdout)
        self.assertIn("value 1.00", done.stdout)
        after = json.loads((sample / "stage-result.json").read_text())
        self.assertTrue(after["regraded"])
        self.assertEqual({key: after[key] for key in ("verdicts", "caught", "held", "pass")},
                         {key: before[key] for key in ("verdicts", "caught", "held", "pass")})
        as_json = process_env("grade", str(sample), "--json", cwd=self.tmp, env=clean_env())
        self.assertTrue(json.loads(as_json.stdout)["pass"])

    def test_grade_follows_the_files_a_tampered_export_fails_it_with_exit_1(self):
        copy = self.tmp / "tampered"
        if not copy.exists():
            shutil.copytree(self.root / WRONG / "1", copy, symlinks=True)
            (copy / "export" / "src" / "paginate.js").write_text("// edited by the host\n")
        done = process_env("grade", str(copy), cwd=self.tmp, env=clean_env())
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("FAIL", done.stdout)
        self.assertIn("C1 MISSED", done.stdout)

    def test_grade_refuses_what_is_not_a_sample(self):
        for target, wanted in ((self.tmp / "nowhere", "is not a folder"), (self.root, "is not a live sample")):
            with self.subTest(target=target.name):
                done = process_env("grade", str(target), cwd=self.tmp, env=clean_env())
                self.assertEqual((done.returncode, done.stdout), (2, ""))
                self.assertIn(wanted, done.stderr)
                self.assertNotIn("Traceback", done.stderr)

    def test_no_credential_of_the_environment_reaches_the_plan_the_logs_or_a_sample(self):
        self.assertNotIn(self.SECRET, self.done.stdout + self.done.stderr)
        seen = 0
        for path in self.root.rglob("*"):
            if path.is_file() and not path.is_symlink():
                seen += 1
                self.assertNotIn(self.SECRET.encode(), path.read_bytes(), str(path))
        self.assertGreater(seen, 20)

    def test_a_second_live_into_the_same_root_is_refused_and_leaves_the_samples(self):
        done = process_env("live", WRONG, "--dry-run", "--out", str(self.root), cwd=self.tmp, env=self.env({}))
        self.assertEqual(done.returncode, 0)  # a dry run creates nothing, so it does not mind
        done = process_env("live", WRONG, "--out", str(self.root), cwd=self.tmp, env=self.env({}))
        self.assertEqual(done.returncode, 2, done.stdout[-500:])
        self.assertIn("already exists", done.stderr)
        self.assertTrue((self.root / WRONG / "1" / "stage-result.json").is_file())


class FailingRun(FakeRoute):
    """A fake that reports the fact false (reference/bad-fact-false): the sample is graded and fails P1, so the scenario does not
    meet its rule and the command exits 1; report --compare then reads it against the run that passed."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.done, cls.root = cls.live(WRONG, "--samples", "1",
                                      config={"mode": "act", "reference": "{scenario_dir}/reference/bad-fact-false"})
        cls.good, cls.good_root = cls.live(WRONG, "--samples", "1",
                                           config={"mode": "act", "reference": "{scenario_dir}/reference/good"})

    def test_a_graded_failure_is_exit_1_and_fail_not_not_run(self):
        self.assertEqual(self.done.returncode, 1, self.done.stdout[-1500:] + self.done.stderr)
        self.assertIn("FAIL  validate-existing/wrong-check #1", self.done.stdout)
        self.assertNotIn("NOT RUN", self.done.stdout)
        self.assertIn("1 scenario did not meet the pass rule: validate-existing/wrong-check", self.done.stdout)
        result = json.loads((self.root / WRONG / "1" / "stage-result.json").read_text())
        self.assertFalse(result["caught"]["P1"])
        self.assertFalse(result["pass"])
        self.assertRegex(self.done.stdout, r"wrong-check\s+1/1\s+0/1\s+1/1\s+1/1\s+0/1\s+0/1\s+NOT MET")

    def test_compare_shows_the_change_from_the_earlier_root_for_the_same_driver(self):
        self.assertEqual(self.good.returncode, 0, self.good.stdout[-1500:])
        done = process_env("report", str(self.good_root), "--compare", str(self.root), cwd=self.tmp, env=clean_env())
        self.assertEqual((done.returncode, done.stderr), (0, ""), done.stdout)
        self.assertIn("driver (the same in both): fake/fake-model/default", done.stdout)
        self.assertIn("1/1 (was 0/1, +1.00)", done.stdout)
        self.assertIn("1/1 (=)", done.stdout)
        as_json = json.loads(process_env("report", str(self.good_root), "--compare", str(self.root), "--json", cwd=self.tmp,
                                         env=clean_env()).stdout)
        self.assertEqual(as_json["compare"]["scenarios"][0]["cells"]["P1"]["delta"], 1.0)

    def test_compare_refuses_roots_of_different_drivers_naming_both(self):
        other = self.tmp / "other-driver"
        if not other.exists():
            shutil.copytree(self.good_root, other, symlinks=True)
            path = other / WRONG / "1" / "stage-result.json"
            document = json.loads(path.read_text())
            path.write_text(json.dumps({**document, "model": "another-model"}))
        done = process_env("report", str(self.root), "--compare", str(other), cwd=self.tmp, env=clean_env())
        self.assertEqual((done.returncode, done.stdout), (2, ""))
        self.assertIn("fake/fake-model/default", done.stderr)
        self.assertIn("fake/another-model/default", done.stderr)
        self.assertIn(str(self.root), done.stderr)
        self.assertIn(str(other), done.stderr)
        self.assertNotIn("Traceback", done.stderr)


class NotRunSamples(FakeRoute):
    """A sample that crashes or does not finish is recorded as not run, never as a pass, and the others go on."""

    def test_a_sample_that_crashes_is_not_run_and_the_others_are_graded(self):
        done, root = self.live(WRONG, "--samples", "3", "--jobs", "3",
                               config={"mode": "act", "reference": "{scenario_dir}/reference/good", "crash": [1]})
        self.assertEqual(done.returncode, 1, done.stdout[-1500:] + done.stderr)
        self.assertRegex(done.stdout, r"NOT RUN  validate-existing/wrong-check #1: .*RuntimeError: the fake host was told to crash")
        self.assertIn("PASS  validate-existing/wrong-check #2", done.stdout)
        self.assertIn("PASS  validate-existing/wrong-check #3", done.stdout)
        crashed = root / WRONG / "1"
        self.assertFalse((crashed / "stage-result.json").exists())
        self.assertIn("RuntimeError", (crashed / "error.txt").read_text())
        self.assertIn("Traceback", next((root / ".logs").glob("*__1.log")).read_text())
        document = json.loads(process_env("report", str(root), "--json", cwd=self.tmp, env=clean_env()).stdout)["report"]
        found = document["scenarios"][0]
        self.assertEqual((found["samples"], found["ran"], found["pass"]), (3, 2, {"k": 2, "n": 3}))
        self.assertEqual(found["not_run"][0]["sample"], 1)
        self.assertEqual(found["ids"]["P1"], {"kind": "caught", "k": 2, "n": 3})

    def test_a_pass_rule_below_all_is_met_with_a_sample_not_run(self):
        cases = self.tmp / "cases-rule"
        if not cases.exists():
            for name in ("wrong-check",):
                shutil.copytree(sb.SCENARIOS_DIR / "validate-existing" / name, cases / "validate-existing" / name)
            path = cases / "validate-existing" / "wrong-check" / "scenario.json"
            document = json.loads(path.read_text())
            document["live"] = {"samples": 3, "pass": 2}
            path.write_text(json.dumps(document))
        done, root = self.live(WRONG, "--jobs", "3", cases=cases,
                               config={"mode": "act", "reference": "{scenario_dir}/reference/good", "crash": [2]})
        self.assertEqual(done.returncode, 0, done.stdout[-1500:] + done.stderr)
        self.assertIn("NOT RUN  validate-existing/wrong-check #2", done.stdout)
        self.assertIn("live: every scenario met its pass rule", done.stdout)
        self.assertRegex(done.stdout, r"2/3\s+met")


class TimedOutSamples(FakeRoute):
    """In-process, so the grace and the kill delay can be short: the samples are still subprocesses."""

    def test_a_sample_that_does_not_finish_is_killed_and_not_run_and_at_most_jobs_run_at_once(self):
        real, seen, started = subprocess.Popen, [], []

        def spy(*args, **kwargs):
            process = real(*args, **kwargs)
            if "live-sample" in (args[0] if args else kwargs.get("args")):  # not the `ps` the sweep of a killed sample's host runs
                started.append(process)
                seen.append(sum(1 for item in started if item.poll() is None))
            return process

        env = self.env({"hang_seconds": 600})
        root = self.tmp / "results-timeout"
        with mock.patch.dict(os.environ, env), mock.patch.object(stages, "SAMPLE_GRACE_SECONDS", 1), \
             mock.patch.object(stages, "KILL_SECONDS", 1), mock.patch.object(stages.subprocess, "Popen", spy):
            code, out, err = cli("live", WRONG, "--samples", "3", "--jobs", "2", "--timeout", "1", "--out", str(root))
        self.assertEqual(code, 1, out[-1500:] + err)
        self.assertEqual(len(started), 3)
        self.assertEqual(max(seen), 2, "two at once, never three")
        self.assertEqual(out.count("NOT RUN  validate-existing/wrong-check #"), 3)
        self.assertNotIn("PASS", out)
        for number in (1, 2, 3):
            reason = (root / WRONG / str(number) / "error.txt").read_text()
            self.assertIn("killed", reason)
            self.assertFalse((root / WRONG / str(number) / "stage-result.json").exists())
        document = process_env("report", str(root), "--json", cwd=self.tmp, env=clean_env()).stdout
        found = json.loads(document)["report"]["scenarios"][0]
        self.assertEqual((found["samples"], found["ran"], found["pass"], found["rule"]["met"]), (3, 0, {"k": 0, "n": 3}, False))
        self.assertTrue(all(process.poll() is not None for process in started), "no sample outlives the command")
        shown = process_env("report", str(root), cwd=self.tmp, env=clean_env()).stdout
        self.assertIn("not run: validate-existing/wrong-check #1: killed", shown)


class TimeoutWiring(FakeRoute):
    """``--timeout`` reaches the sample and the parent's hard limit is built from it: a real `live` with a host that lingers, and
    the call the parent makes to wait for its child, with no constant patched."""

    def test_a_timeout_on_the_command_line_ends_a_lingering_host_and_the_sample_is_graded_with_a_timeout_session(self):
        started = time.monotonic()
        done, root = self.live(WRONG, "--samples", "1", "--timeout", "3", config={"mode": "wait", "linger": 120})
        self.assertLess(time.monotonic() - started, 100, "the host lingers for 120 s: the timeout ended it")
        self.assertEqual(done.returncode, 1, done.stdout[-1500:] + done.stderr)
        self.assertIn("FAIL  validate-existing/wrong-check #1", done.stdout)
        self.assertNotIn("NOT RUN", done.stdout)
        folder = root / WRONG / "1"
        result = json.loads((folder / "stage-result.json").read_text())
        self.assertEqual([session["status"] for session in result["sessions"]], ["timeout"])
        self.assertEqual((result["verdicts"]["process"], result["verdicts"]["accepted"], result["pass"]), (False, False, False))
        self.assertEqual(json.loads((folder / "invocation.json").read_text())["timeout"], 3.0)
        self.assertEqual(json.loads((root / "live-plan.json").read_text())["timeout"], 3.0)

    def test_the_parent_waits_for_its_sample_at_most_the_timeout_plus_the_grace(self):
        waits, argvs = [], []

        class Child:
            pid = 2 ** 22 + 1  # not a process of ours: nothing is signalled in this test

            def wait(self, timeout=None):
                waits.append(timeout)
                return 0

            def poll(self):
                return 0

        def popen(argv, **kwargs):
            argvs.append(argv)
            return Child()

        cases = self.tmp / "cases-hard-limit"
        if not cases.exists():
            scenario(cases, "validate-existing", "s")
        args = type("Args", (), {"host": None, "backend": None, "model": None, "effort": None, "host_bin": None, "ref": None,
                                 "timeout": 3.0})()
        root = self.tmp / "results-hard-limit"
        with mock.patch.object(stages.subprocess, "Popen", popen):
            record = stages.run_one_sample(sb.load("validate-existing/s", cases), 1, root, args, cases, None)
        self.assertEqual(waits, [3.0 + stages.SAMPLE_GRACE_SECONDS])
        self.assertGreater(stages.SAMPLE_GRACE_SECONDS, 3, "the grace is a real allowance for the build, the seed and the exports")
        argv = argvs[0]
        self.assertEqual(argv[argv.index("--timeout") + 1], "3.0")
        self.assertFalse(record["graded"])
        args.timeout = None  # no timeout, no hard limit (the command line always gives one: DEFAULT_TIMEOUT)
        waits.clear()
        with mock.patch.object(stages.subprocess, "Popen", popen):
            stages.run_one_sample(sb.load("validate-existing/s", cases), 2, root, args, cases, None)
        self.assertEqual(waits, [None])


class LiveSampleCodes(Catalog):
    """The hidden `live-sample` command's exit codes: the parent reads the files, but a person running one sees these."""

    def code(self, **outcome) -> tuple[int, str, str]:
        driver = type("Driver", (), {"host": object(), "plugin_dir": None})()
        with mock.patch.object(stages.run, "install_termination_handlers"), mock.patch.object(stages, "resolve_driver", return_value=driver), \
             mock.patch.object(stages.stage_live, "run_sample", **outcome) as sample:
            result = cli("live-sample", "validate-existing/broken", str(self.temp / "sample"), "--sample", "2", "--cases-dir", str(self.cases))
        sample.assert_called_once()
        return result

    def test_a_graded_pass_is_0_and_a_graded_fail_is_1_and_either_prints_the_verdict(self):
        code, out, err = self.code(return_value={"pass": True, "value": 1.0})
        self.assertEqual((code, json.loads(out)), (stages.EXIT_PASS, {"scenario": "validate-existing/broken", "sample": 2, "pass": True, "value": 1.0}))
        code, out, err = self.code(return_value={"pass": False, "value": 0.5})
        self.assertEqual((code, json.loads(out)["pass"]), (stages.EXIT_FAIL, False))
        self.assertEqual((stages.EXIT_PASS, stages.EXIT_FAIL), (0, 1))

    def test_a_refusal_is_2_a_stop_is_5_and_a_crash_is_4_with_its_traceback(self):
        code, out, err = self.code(side_effect=SystemExit("the host is not ready. Nothing was started."))
        self.assertEqual((code, out), (stages.EXIT_USAGE, ""))
        self.assertIn("Nothing was started.", err)
        code, out, err = self.code(side_effect=stages.stage_live.SampleStopped("the host was ended: stopped by the operator"))
        self.assertEqual((code, out), (stages.EXIT_STOPPED, ""))
        self.assertIn("stopped: the host was ended", err)
        code, out, err = self.code(side_effect=RuntimeError("the sample raised"))
        self.assertEqual((code, out), (stages.EXIT_CRASH, ""))
        self.assertIn("Traceback", err)
        self.assertIn("RuntimeError: the sample raised", err)
        self.assertEqual((stages.EXIT_USAGE, stages.EXIT_CRASH, stages.EXIT_STOPPED), (2, 4, 5))


class NoSampleOnceTold(NoLaunch):
    def test_no_sample_process_is_started_once_live_was_told_to_end(self):
        stages.STOPPING.set()
        self.addCleanup(stages.STOPPING.clear)
        args = type("Args", (), {"host": None, "backend": None, "model": None, "effort": None, "host_bin": None, "ref": None,
                                 "timeout": 60.0})()
        record = stages.run_one_sample(sb.load("validate-existing/broken", self.cases), 1, self.temp / "results", args, self.cases, None)
        self.assertFalse(record["graded"])
        self.assertIn("`live` was told to end", record["reason"])
        self.assertIn("could not be started", record["reason"])
        self.assertNothingStarted()


class SweepReport(Temp):
    """The ledger sweep of a sample that was killed from outside: what it could not see or could not stop is said, printed and
    kept in the sample's error.txt; a sweep that did its work says nothing."""
    CLEAN = {"observed": True, "stopped": [{"pgid": 7, "role": "host", "ended_by": "SIGKILL", "members": 1}], "survived": [], "gone": [],
             "reused": [], "unverified": [], "protected": []}
    SURVIVED = {**CLEAN, "stopped": [], "survived": [{"pgid": 77, "role": "host", "command": "fake", "members": [{"pid": 78, "command": "x"}]}]}
    UNSEEN = {"observed": False, "reason": "ps timed out after 10s"}

    def sweep(self, record: dict, before: str = "") -> tuple[str, str]:
        folder = Path(tempfile.mkdtemp(prefix="sweep-", dir=self.temp))
        if before:
            (folder / "error.txt").write_text(before)
        err = io.StringIO()
        with mock.patch.object(stages.stage_live, "end_recorded_hosts", return_value=record), contextlib.redirect_stderr(err):
            stages._sweep(folder)
        kept = (folder / "error.txt").read_text() if (folder / "error.txt").exists() else ""
        return err.getvalue(), kept

    def test_a_host_that_survived_is_printed_and_appended_to_error_txt(self):
        printed, kept = self.sweep(self.SURVIVED, "live-sample exited -9: Killed\n")
        self.assertIn("could not stop host group 77", printed)
        self.assertTrue(kept.startswith("live-sample exited -9: Killed\n"), kept)
        self.assertIn("could not stop host group 77", kept)

    def test_a_ledger_that_could_not_be_observed_is_printed_and_kept(self):
        printed, kept = self.sweep(self.UNSEEN)
        self.assertIn("not observed: ps timed out after 10s", printed)
        self.assertIn("not observed: ps timed out after 10s", kept)

    def test_a_sweep_that_stopped_the_host_or_found_nothing_says_nothing(self):
        for record in (self.CLEAN, {**self.CLEAN, "stopped": []}):
            printed, kept = self.sweep(record, "live-sample exited -9\n")
            self.assertEqual((printed, kept), ("", "live-sample exited -9\n"))

    def test_run_one_sample_keeps_why_it_was_not_run_and_then_what_the_sweep_could_not_do(self):
        class Killed:
            pid = 2 ** 22 + 1

            def wait(self, timeout=None):
                return -9

            def poll(self):
                return -9

        cases = self.temp / "cases"
        scenario(cases, "validate-existing", "s")
        args = type("Args", (), {"host": None, "backend": None, "model": None, "effort": None, "host_bin": None, "ref": None,
                                 "timeout": 60.0})()
        err = io.StringIO()
        with mock.patch.object(stages.subprocess, "Popen", lambda argv, **kwargs: Killed()), \
             mock.patch.object(stages.stage_live, "end_recorded_hosts", return_value=self.SURVIVED), contextlib.redirect_stderr(err):
            record = stages.run_one_sample(sb.load("validate-existing/s", cases), 1, self.temp / "results", args, cases, None)
        self.assertFalse(record["graded"])
        self.assertTrue(record["reason"].startswith("live-sample exited -9"), record["reason"])
        kept = (self.temp / "results" / "validate-existing" / "s" / "1" / "error.txt").read_text()
        self.assertTrue(kept.startswith("live-sample exited -9"), kept)
        self.assertIn("could not stop host group 77", kept)
        self.assertIn("could not stop host group 77", err.getvalue())


class EscalateUnit(Temp):
    """``_escalate`` with its exit, its kill and its sweep replaced: what it does to the samples it finds, in what order."""

    class Exit(Exception):
        pass

    def escalate(self, children) -> tuple[list, list, list]:
        killed, swept, said = [], [], io.StringIO()

        def leave(code):
            said.write(f"exit {code}\n")
            raise self.Exit(code)

        self.addCleanup(stages.STOPPING.clear)
        with mock.patch.object(stages, "CHILDREN", children), \
             mock.patch.object(stages.os, "killpg", lambda pid, number: killed.append((pid, number))), \
             mock.patch.object(stages, "_sweep", swept.append), mock.patch.object(stages.os, "_exit", leave), \
             contextlib.redirect_stderr(said), self.assertRaises(self.Exit) as left:
            stages._escalate(signal.SIGTERM)
        self.assertEqual(left.exception.args, (128 + signal.SIGTERM,))
        return killed, swept, [said.getvalue()]

    def test_every_running_sample_is_killed_with_its_group_and_its_ledger_swept_before_live_leaves(self):
        class Fake:
            def __init__(self, pid):
                self.pid = pid

        one, two = Fake(4_000_001), Fake(4_000_002)
        folders = {one: self.temp / "one", two: self.temp / "two"}
        killed, swept, said = self.escalate(dict(folders))
        self.assertEqual(sorted(killed), [(4_000_001, signal.SIGKILL), (4_000_002, signal.SIGKILL)])
        self.assertEqual(sorted(swept), [self.temp / "one", self.temp / "two"], "each sample's ledger is the only way to its host")
        self.assertTrue(stages.STOPPING.is_set())
        self.assertIn("a second signal (SIGTERM)", said[0])

    def test_no_new_sample_can_slip_in_between_the_copy_and_the_stop_flag(self):
        """A worker registers its sample, then reads STOPPING and ends the sample itself when it is set: so the flag must be set
        before the copy of the samples is taken, or a sample registered just after the copy would be left running."""
        seen = []

        class Watching(dict):
            def items(self):
                seen.append(stages.STOPPING.is_set())
                return super().items()

        self.escalate(Watching())
        self.assertEqual(seen, [True])


def ps_field(pid: int, field: str) -> str:
    """One field of ``ps`` for ``pid`` ("" when ps lists none): the same on Linux and macOS, unlike /proc."""
    done = subprocess.run(["ps", "-o", f"{field}=", "-p", str(pid)], capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=30)
    return done.stdout.strip()


def process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return not ps_field(pid, "stat").startswith("Z")  # a zombie ended and is not reaped yet


def parent_of(pid: int) -> int:
    return int(ps_field(pid, "ppid"))


def ignore_sighup() -> None:
    """Child set-up for the case a launch under nohup makes: SIGHUP is ignored, and is handed down to every process below."""
    signal.signal(signal.SIGHUP, signal.SIG_IGN)


def default_sighup() -> None:
    """Child set-up for the signal cases: a run launched under nohup (or any caller that ignores SIGHUP) hands that disposition
    down, and stages.py live deliberately keeps an ignored SIGHUP ignored, so the SIGHUP case would wait for a signal that
    cannot end it.  These cases test the handler, so the child starts with the default."""
    signal.signal(signal.SIGHUP, signal.SIG_DFL)


def default_signals() -> None:
    """``default_sighup`` and the same for SIGINT: a test run started in the background of a non-interactive shell has SIGINT
    ignored, which a child inherits, and `live` keeps an ignored signal ignored."""
    default_sighup()
    signal.signal(signal.SIGINT, signal.default_int_handler)


class Signals(FakeRoute):
    """A real `live` process with a fake host that waits for two minutes, and a signal to it or to its sample. The host runs in a
    session of its own, so only a handler (or the ledger) can end it: none may outlive the command."""

    def start(self, config: dict | None = None, preexec=default_signals) -> tuple[subprocess.Popen, Path, int]:
        type(self).count += 1
        root = self.tmp / f"results-{self.count}"
        pid_file = self.tmp / f"host-{self.count}.pid"
        process = subprocess.Popen([sys.executable, "-B", str(STAGES), "live", WRONG, "--samples", "1", "--out", str(root)],
                                   cwd=self.tmp, env=self.env({"mode": "wait", "pid_file": str(pid_file), **(config or {})}),
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                   preexec_fn=preexec)
        self.addCleanup(lambda: process.poll() is None and process.kill())
        deadline = time.monotonic() + 120
        while not (pid_file.exists() and pid_file.read_text()) and time.monotonic() < deadline:
            self.assertIsNone(process.poll(), "live ended before the host started")
            time.sleep(0.2)
        host = int(pid_file.read_text())
        self.addCleanup(lambda: process_alive(host) and os.kill(host, signal.SIGKILL))
        return process, root, host

    def test_a_sigterm_to_live_ends_every_sample_and_the_host_under_it(self):
        process, root, host = self.start()
        sample = parent_of(host)
        self.assertTrue(process_alive(sample) and process_alive(host))
        process.send_signal(signal.SIGTERM)
        out, err = process.communicate(timeout=120)
        self.assertEqual(process.returncode, 128 + signal.SIGTERM, out + err)
        self.assertIn("ended by SIGTERM", err)
        self.assertFalse(process_alive(host), "the model host is gone")
        self.assertFalse(process_alive(sample), "the sample's process is gone")
        folder = root / WRONG / "1"
        self.assertFalse((folder / "stage-result.json").exists(), "an ended sample is not graded")
        self.assertTrue((folder / "error.txt").is_file())
        shown = process_env("report", str(root), cwd=self.tmp, env=clean_env()).stdout
        self.assertIn("not run: validate-existing/wrong-check #1", shown)

    def test_a_sighup_does_the_same_and_a_second_sample_that_had_not_started_never_starts(self):
        type(self).count += 1
        root = self.tmp / f"results-{self.count}"
        pid_file = self.tmp / f"host-{self.count}.pid"
        process = subprocess.Popen([sys.executable, "-B", str(STAGES), "live", WRONG, "--samples", "3", "--jobs", "1", "--out", str(root)],
                                   cwd=self.tmp, env=self.env({"mode": "wait", "pid_file": str(pid_file)}),
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                   preexec_fn=default_sighup)
        self.addCleanup(lambda: process.poll() is None and process.kill())
        deadline = time.monotonic() + 120
        while not (pid_file.exists() and pid_file.read_text()) and time.monotonic() < deadline:
            time.sleep(0.2)
        host = int(pid_file.read_text())
        self.addCleanup(lambda: process_alive(host) and os.kill(host, signal.SIGKILL))
        process.send_signal(signal.SIGHUP)
        out, err = process.communicate(timeout=120)
        self.assertEqual(process.returncode, 128 + signal.SIGHUP, out + err)
        self.assertFalse(process_alive(host))
        self.assertEqual(sorted(path.name for path in (root / WRONG).iterdir()), ["1"], "samples 2 and 3 were never started")

    def test_a_sample_killed_from_outside_leaves_no_host_behind(self):
        """SIGKILL gives the sample no chance to end its host, which is in a session of its own: the parent ends it from the
        sample's own ledger (lifecycle), and the sample is not run."""
        process, root, host = self.start()
        os.kill(parent_of(host), signal.SIGKILL)
        out, err = process.communicate(timeout=120)
        self.assertEqual(process.returncode, 1, out + err)
        self.assertRegex(out, r"NOT RUN  validate-existing/wrong-check #1: live-sample exited -9")
        deadline = time.monotonic() + 30
        while process_alive(host) and time.monotonic() < deadline:
            time.sleep(0.2)
        self.assertFalse(process_alive(host), "the orphaned host was ended")
        self.assertFalse((root / WRONG / "1" / "stage-result.json").exists())

    def test_a_sighup_the_launch_ignored_stays_ignored_and_nothing_is_ended(self):
        """nohup keeps a run alive through a hangup by ignoring SIGHUP; `live` takes over only the signals that were not ignored,
        and the samples and hosts below it inherit the ignore."""
        process, root, host = self.start(preexec=ignore_sighup)
        sample = parent_of(host)
        process.send_signal(signal.SIGHUP)
        time.sleep(5)  # well past the 2 s poll of the sample and the pool: a handler would have ended everything by now
        self.assertIsNone(process.poll(), "live went on")
        self.assertTrue(process_alive(sample) and process_alive(host), "the sample and its host went on")
        self.assertEqual(sorted(path.name for path in (root / WRONG).iterdir()), ["1"])
        process.send_signal(signal.SIGTERM)  # and the other signals still end it
        out, err = process.communicate(timeout=120)
        self.assertEqual(process.returncode, 128 + signal.SIGTERM, out + err)
        self.assertFalse(process_alive(host))

    def escapee_start(self) -> tuple[subprocess.Popen, Path, int, int]:
        """A `live` whose host left a process in a session of its own that holds the host's output open: ending the sample takes
        a long time (it is abandoned after its stop grace), so a second signal arrives while the first is still being answered."""
        escapee_file = self.tmp / f"escapee-{self.count + 1}.pid"
        process, root, host = self.start({"escapee": str(escapee_file)})
        deadline = time.monotonic() + 60
        while not (escapee_file.exists() and escapee_file.read_text()) and time.monotonic() < deadline:
            time.sleep(0.1)
        escapee = int(escapee_file.read_text())
        self.addCleanup(lambda: process_alive(escapee) and os.kill(escapee, signal.SIGKILL))
        return process, root, host, escapee

    def assertGone(self, pid: int, why: str, seconds: float = 10) -> None:
        deadline = time.monotonic() + seconds
        while process_alive(pid) and time.monotonic() < deadline:
            time.sleep(0.1)
        self.assertFalse(process_alive(pid), why)

    def test_a_second_sigterm_escalates_at_once_and_leaves_no_sample_or_host_behind(self):
        process, root, host, escapee = self.escapee_start()
        sample = parent_of(host)
        process.send_signal(signal.SIGTERM)
        time.sleep(1.5)
        self.assertIsNone(process.poll(), "the first signal is still being answered: the sample is held up by the escapee")
        started = time.monotonic()
        process.send_signal(signal.SIGTERM)
        out, err = process.communicate(timeout=60)
        self.assertLess(time.monotonic() - started, 20, "the second signal did not wait for the first to finish")
        self.assertEqual(process.returncode, 128 + signal.SIGTERM, out + err)
        self.assertNotIn("Traceback", err)
        self.assertGone(sample, "the sample was killed with its group")
        self.assertGone(host, "the host was ended")
        self.assertTrue(process_alive(escapee), "the process in a session of its own is nobody's but its owner's")

    def test_a_sigint_after_a_sigterm_escalates_too_and_does_not_hang_in_the_pool(self):
        process, root, host, escapee = self.escapee_start()
        sample = parent_of(host)
        process.send_signal(signal.SIGTERM)
        time.sleep(1.5)
        process.send_signal(signal.SIGINT)
        out, err = process.communicate(timeout=60)
        self.assertEqual(process.returncode, 128 + signal.SIGINT, out + err)
        self.assertNotIn("Traceback", err)
        self.assertGone(sample, "the sample was killed with its group")
        self.assertGone(host, "the host was ended")

    def test_a_sighup_after_a_sigterm_counts_as_the_second_signal_and_escalates(self):
        """Pinned, not accidental: any two of SIGTERM, SIGHUP and SIGINT in a row mean "end now" (a hangup that follows a
        terminate is the same operator). The hosts are ended from the ledgers either way, so nothing is left running."""
        process, root, host, escapee = self.escapee_start()
        sample = parent_of(host)
        process.send_signal(signal.SIGTERM)
        time.sleep(1.5)
        process.send_signal(signal.SIGHUP)
        out, err = process.communicate(timeout=60)
        self.assertEqual(process.returncode, 128 + signal.SIGHUP, out + err)
        self.assertNotIn("Traceback", err)
        self.assertGone(sample, "the sample was killed with its group")
        self.assertGone(host, "the host was ended")

    def test_a_second_sigint_after_a_sigint_escalates_too(self):
        process, root, host, escapee = self.escapee_start()
        sample = parent_of(host)
        process.send_signal(signal.SIGINT)
        time.sleep(1.5)
        process.send_signal(signal.SIGINT)
        out, err = process.communicate(timeout=60)
        self.assertEqual(process.returncode, 128 + signal.SIGINT, out + err)
        self.assertNotIn("Traceback", err)
        self.assertGone(sample, "the sample was killed with its group")
        self.assertGone(host, "the host was ended")

    def test_a_second_signal_ends_the_host_of_a_sample_that_cannot_answer_by_the_ledger_sweep_alone(self):
        """A stopped sample (SIGSTOP) runs no handler, so neither the first signal's SIGTERM to it nor its own cleanup ends the
        host, which is in a session of its own. The second signal kills the sample's group, and only the sweep of its ledger
        (inside the escalation) can end the host."""
        process, root, host = self.start()
        sample = parent_of(host)
        os.kill(sample, signal.SIGSTOP)
        self.addCleanup(lambda: process_alive(sample) and os.kill(sample, signal.SIGKILL))
        process.send_signal(signal.SIGTERM)
        time.sleep(1.5)
        self.assertIsNone(process.poll(), "the first signal is still being answered: the stopped sample cannot")
        self.assertTrue(process_alive(host), "nothing has ended the host yet")
        process.send_signal(signal.SIGTERM)
        out, err = process.communicate(timeout=60)
        self.assertEqual(process.returncode, 128 + signal.SIGTERM, out + err)
        self.assertNotIn("Traceback", err)
        self.assertGone(sample, "the sample was killed with its group")
        self.assertGone(host, "the host was ended from the sample's ledger")

    def test_a_sigint_alone_ends_every_sample_the_way_a_sigterm_does(self):
        process, root, host = self.start()
        sample = parent_of(host)
        process.send_signal(signal.SIGINT)
        out, err = process.communicate(timeout=120)
        self.assertEqual(process.returncode, 128 + signal.SIGINT, out + err)
        self.assertIn("ended by SIGINT", err)
        self.assertGone(sample, "the sample is gone")
        self.assertGone(host, "the host is gone")

    def test_a_sample_an_operator_ended_is_not_run_through_the_command_line_too(self):
        done, root = self.live(WRONG, "--samples", "1", config={"mode": "wait", "stop_file": True})
        self.assertEqual(done.returncode, 1, done.stdout[-1500:] + done.stderr)
        self.assertRegex(done.stdout, r"NOT RUN  validate-existing/wrong-check #1: live-sample exited 5: stopped: .*ended before it accepted")
        self.assertIn("not run: validate-existing/wrong-check #1: SampleStopped", done.stdout)
        folder = root / WRONG / "1"
        self.assertFalse((folder / "stage-result.json").exists())
        self.assertFalse((folder / "stop").exists())
        found = json.loads(process_env("report", str(root), "--json", cwd=self.tmp, env=clean_env()).stdout)["report"]["scenarios"][0]
        self.assertEqual((found["ran"], found["pass"]), (0, {"k": 0, "n": 1}))
        graded = process_env("grade", str(folder), cwd=self.tmp, env=clean_env())
        self.assertEqual(graded.returncode, 2, graded.stdout)
        self.assertIn("was not run to the end", graded.stderr)


class WhoEndsTheHost(FakeRoute):
    """One sample at a time through ``run_one_sample`` (a real `live-sample` process and a fake host that waits): which of the two
    cleanups ends the host. The host is in a session of its own, so a signal to the sample does not reach it."""

    def run_it(self, ended_by: str, sweeps: list) -> tuple[dict, int, Path]:
        """Start the sample, end its process by ``ended_by`` (SIGTERM: its handler runs; SIGKILL: nothing can run) and return the
        parent's record, the host's pid and the sample folder."""
        type(self).count += 1
        root = self.tmp / f"results-{self.count}"
        pid_file = self.tmp / f"host-{self.count}.pid"
        cases = self.tmp / f"cases-{self.count}"
        cases.mkdir()
        shutil.copytree(sb.SCENARIOS_DIR / "validate-existing" / "wrong-check", cases / "validate-existing" / "wrong-check")
        args = type("Args", (), {"host": None, "backend": None, "model": None, "effort": None, "host_bin": None, "ref": None,
                                 "timeout": 300.0})()
        box: dict = {}
        real = stages.stage_live.end_recorded_hosts

        def spy(folder):
            found = real(folder)
            sweeps.append(found)
            return found

        with mock.patch.dict(os.environ, self.env({"mode": "wait", "pid_file": str(pid_file)})), \
             mock.patch.object(stages.stage_live, "end_recorded_hosts", spy):
            worker = threading.Thread(target=lambda: box.update(record=stages.run_one_sample(
                sb.load(WRONG, cases), 1, root, args, cases, None)), daemon=True)
            worker.start()
            deadline = time.monotonic() + 120
            while not (pid_file.exists() and pid_file.read_text()) and time.monotonic() < deadline:
                time.sleep(0.2)
            host = int(pid_file.read_text())
            self.addCleanup(lambda: process_alive(host) and os.kill(host, signal.SIGKILL))
            os.kill(parent_of(host), getattr(signal, ended_by))
            worker.join(120)
        self.assertFalse(worker.is_alive(), "the sample's record came back")
        return box["record"], host, root / WRONG / "1"

    def test_a_sample_told_to_end_ends_its_host_with_its_own_handler_and_the_parent_has_nothing_to_sweep(self):
        sweeps: list = []
        record, host, folder = self.run_it("SIGTERM", sweeps)
        self.assertFalse(process_alive(host), "the host is gone")
        self.assertEqual(sweeps, [], "the sample exited by itself (5: stopped), so the parent did not sweep: the handler did the work")
        self.assertIn("exited 5", record["reason"])
        self.assertFalse((folder / "stage-result.json").exists())
        ended = [row for row in lifecycle_rows(folder) if row.get("kind") == "ended" and row.get("role") == "host"]
        self.assertEqual([row["how"] for row in ended], ["session ended"], "the sample's own launch recorded the end of the host group")

    def test_a_sample_that_was_killed_leaves_its_host_to_the_ledger_sweep_alone(self):
        sweeps: list = []
        record, host, folder = self.run_it("SIGKILL", sweeps)
        self.assertFalse(process_alive(host), "the host is gone")
        self.assertEqual(len(sweeps), 1, "the parent swept the ledger of the killed sample")
        self.assertEqual([item["pgid"] for item in sweeps[0]["stopped"]], [host], "and it is the sweep that stopped the host")
        self.assertIn("exited -9", record["reason"])
        self.assertEqual([row["how"] for row in lifecycle_rows(folder) if row.get("kind") == "ended" and row.get("role") == "host"],
                         ["stopped"])


def lifecycle_rows(folder: Path) -> list[dict]:
    import lifecycle
    return lifecycle.rows(folder)


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
        for used in ("sb.discover(", "sb.render(", "sb.reference_bundle(", "stage_oracle.run_checks(", "stage_oracle.verdict(",
                     "stage_live.run_sample(", "stage_live.grade_sample(", "stage_report.read_root(", "stage_report.compare(",
                     "run.new_output_dir("):
            self.assertIn(used, text)
        for copied in ("def run_check", "def validate_checks", "class Bundle", "def build(", "def discover(", "SEED_SCRIPT",
                       "def run_sample", "def grade_sample", "def read_root", "def compare", "def new_output_dir", "def launch("):
            self.assertNotIn(copied, text)


class Documents(unittest.TestCase):
    """The prose that describes the stage suite says what is so: the worked example lists every output it ships, and every
    place that lists what the evaluator digest binds names the trees ``boundary`` reads."""

    def test_the_guide_lists_every_bad_output_of_its_worked_example_and_counts_them(self):
        example = HARNESS / "stage_cases" / "validate-existing" / "broken-works-small-fix" / "reference"
        bad = sorted(path.name for path in example.iterdir() if path.name.startswith("bad-"))
        self.assertGreaterEqual(len(bad), 6)
        text = (HARNESS / "stage_cases" / "README.md").read_text()
        for name in bad:
            self.assertIn(f"| `{name}` |", text, f"the guide's table has a row for {name}")
        words = {4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}
        self.assertIn(f"and {words[len(bad)]} outputs that each fail something", text)
        self.assertNotIn("four outputs that each fail something", text)

    def test_every_list_of_what_the_digest_binds_names_the_checks_fixtures_and_evaluators_trees(self):
        trees = ("checks", "fixtures", "evaluators")
        self.assertEqual([tree for tree in trees if not (HARNESS / tree).is_dir()], [])
        graded = {path.relative_to(HARNESS).parts[0] for path in boundary.oracle_files(HARNESS)}
        self.assertEqual(graded, {"checks", "fixtures"})
        documents = {
            "stage_cases/README.md": (HARNESS / "stage_cases" / "README.md").read_text(),
            "shiploop_e2e/README.md": (HARNESS / "README.md").read_text(),
            "docs/plans/shiploop-stage-suite.md": (ROOT / "docs" / "plans" / "shiploop-stage-suite.md").read_text(),
        }
        for name, text in documents.items():
            flat = " ".join(text.split())
            with self.subTest(name):
                self.assertIn("`checks/`, `fixtures/` and `evaluators/` trees", flat)

    def test_the_plan_does_not_call_the_merged_seam_unmerged_or_unreleased(self):
        flat = " ".join((ROOT / "docs" / "plans" / "shiploop-stage-suite.md").read_text().split())
        self.assertIn("475ab9a6", flat)
        self.assertIn("shiploop 1.23.3", flat)
        for stale in ("PR #28 is not merged", "PR #28, not yet merged", "ships in the next release", "shipped in the next release"):
            self.assertNotIn(stale, flat)


if __name__ == "__main__":
    unittest.main()
