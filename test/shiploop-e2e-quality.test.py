#!/usr/bin/env python3
"""No-model checks for the delivered-quality record of the ShipLoop E2E harness (batch 1011, group G5).

Two things are tested here, both without a host, a model, a browser, a fixed port or the machine's process table:

* ``--planning-review stage|none`` as an option of a named case (``run.py``), so a ``none`` run keeps its case, its style
  and its baseline key instead of being case ``custom``;
* ``test/shiploop_e2e/quality.py``: the mutation ratio of the delivered tests, the held-out acceptance of a case that
  declares it, the memory writes read from a Claude event stream, and how ``run.py`` gates, orders and records them.

The fake hosts are the ones of ``test/shiploop-e2e.test.py`` (loaded, not copied). Real ``node`` is used only by the classes
that say so, and they skip with a reason that names node when it is not installed.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
FIXTURES = ROOT / "test" / "fixtures" / "quality"


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "test" / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# The fake hosts, the harness cases and the real-listener helpers of the main harness suite. Nothing here is collected
# twice: only classes defined in this file are tests of this file (the loaded module keeps its own classes).
e2e = _load("shiploop_e2e_main_tests", "shiploop-e2e.test.py")
run = e2e.run
hosts = e2e.hosts
listeners = e2e.listeners

try:
    import quality  # noqa: E402
except ModuleNotFoundError as missing:
    if missing.name != "quality":
        raise
    quality = None  # the state a failing test is first run in: only the quality tests may fail, each on an assertion


def needs_quality(cls):
    """Class decorator: while quality.py does not exist every test of the class fails on this assertion, one by one."""
    inner = cls.setUp

    def setUp(self):
        self.assertIsNotNone(quality, "test/shiploop_e2e/quality.py does not exist")
        inner(self)

    cls.setUp = setUp
    return cls


needs_node = unittest.skipUnless(shutil.which("node"), "this class runs the real `node --test` and needs node on PATH "
                                 "(install node to run it); the stand-in tests of the same behaviour still run")


# ---------------------------------------------------------------------------------------------------------------------
# --planning-review on a named case


class PlanningReviewOptionTest(e2e.CaseRunCase):
    """`--planning-review` is appended to the case's prompt, recorded in invocation.json and keyed by the case, not `custom`."""

    def setUp(self):
        super().setUp()
        e2e.isolate_git(self)
        self.card = self.plugin / "skills" / "improve" / "SKILL.md"
        self.card.parent.mkdir(parents=True)
        self.card.write_text("# Improve\n")
        self.hello = json.loads(run.CASES.read_text())["hello"]["prompt"]

    def sentence(self, mode: str) -> str:
        return (f"Start ShipLoop with the run option --planning-review none and --improve-skill {self.card}."
                if mode == "none" else "Start ShipLoop with the run option --planning-review stage.")

    def test_none_on_a_named_case_names_the_option_and_the_improve_card_and_keeps_the_case(self):
        code, result, _printed, out = self.case_main("c-none", "--case", "hello", "--planning-review", "none",
                                                     env={"FAKE_PLANNING_REVIEW": "none"})
        self.assertEqual(code, 0, result)
        self.assertEqual(result["case"], "hello", "a named case stays that case: it is not `custom`")
        self.assertEqual((out / "prompt.txt").read_text().strip(), f"{self.hello} {self.sentence('none')}")
        self.assertIn(self.sentence("none"), self.seen()["argv"][self.seen()["argv"].index("-p") + 1],
                      "the host is given the option")
        invocation = json.loads((out / "invocation.json").read_text())
        self.assertEqual((invocation["planning_review"], invocation["improve_skill"]), ("none", str(self.card)))
        row = self.last_row()
        self.assertEqual((row["case"], row["style"], row["planning_review"]), ("hello", "smoke", "none"),
                         "the baseline row is keyed by the case and its style, and the mode is the engine's")

    def test_stage_names_only_the_option(self):
        _code, _result, _printed, out = self.case_main("c-stage", "--case", "hello", "--planning-review", "stage")
        self.assertEqual((out / "prompt.txt").read_text().strip(), f"{self.hello} {self.sentence('stage')}")
        invocation = json.loads((out / "invocation.json").read_text())
        self.assertEqual((invocation["planning_review"], invocation["improve_skill"]), ("stage", None))

    def test_without_the_option_the_prompt_and_the_record_are_as_before(self):
        _code, _result, _printed, out = self.case_main("c-plain", "--case", "hello")
        self.assertEqual((out / "prompt.txt").read_text().strip(), self.hello)
        invocation = json.loads((out / "invocation.json").read_text())
        self.assertEqual((invocation["planning_review"], invocation["improve_skill"]), (None, None))

    def test_a_custom_prompt_takes_the_option_the_same_way(self):
        _code, result, _printed, out = self.case_main("c-custom", "--prompt", "say hello", "--planning-review", "none")
        self.assertEqual(result["case"], "custom")
        self.assertEqual((out / "prompt.txt").read_text().strip(), f"say hello {self.sentence('none')}")

    def test_none_without_the_improve_card_in_the_plugin_is_refused_before_any_host_starts(self):
        self.card.unlink()
        os.environ["FAKE_MODE"] = "done"
        out = self.tmp / "c-refused"
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as raised:
            run.main(["--host", "claude", "--claude-bin", str(self.fakes["claude"]), "--output", str(out),
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), "--case", "hello",
                      "--planning-review", "none"])
        self.assertIn("--improve-skill", str(raised.exception))
        self.assertFalse(self.log.exists(), "the host must not have started")

    def test_the_choices_are_the_engines_own(self):
        import shiploop_stage_spec as stage_spec
        action = next(a for a in run.parser()._actions if a.dest == "planning_review")
        self.assertEqual(tuple(action.choices), stage_spec.PLANNING_REVIEW_MODES)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            run.parser().parse_args(["--planning-review", "sometimes"])

    def test_a_seeded_run_takes_no_planning_review(self):
        # The harness starts a seeded run itself and records its stages without doing them: the option would change nothing.
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as raised:
            run.main(["--host", "claude", "--claude-bin", str(self.fakes["claude"]), "--output", str(self.tmp / "c-seed"),
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), "--case", "hello",
                      "--seed-at", "step-plan", "--planning-review", "none"])
        self.assertIn("seeded", str(raised.exception))

    def test_a_resume_names_the_runs_own_value_or_none(self):
        choice = run.planning_review_choice
        self.assertEqual(choice(None, {"planning_review": "none"}), "none")
        self.assertEqual(choice("none", {"planning_review": "none"}), "none")
        self.assertIsNone(choice(None, {}))
        self.assertEqual(choice("stage", None), "stage")
        with self.assertRaises(SystemExit) as raised:
            choice("stage", {"planning_review": "none"})
        self.assertIn("none", str(raised.exception))
        with self.assertRaises(SystemExit):
            choice("none", {})  # the run never recorded a value: it cannot be given one now


# ---------------------------------------------------------------------------------------------------------------------
# Shared helpers

TINY = FIXTURES / "tiny-product"
REFERENCE = FIXTURES / "reference_checkers.py"
CHECKERS_IDS = ["red-moves-first", "illegal-keeps-turn", "off-board-keeps-turn", "legal-moves-alternate", "red-jump-mandatory",
                "black-jump-mandatory-and-removal"]
GIT_IDENTITY = ["-c", "user.name=Quality Test", "-c", "user.email=quality@example.invalid"]


class RecordingGroups(set):
    """The harness's live-group registry, remembering every pid ever added."""

    def __init__(self):
        super().__init__()
        self.added: list[int] = []

    def add(self, pid):
        self.added.append(pid)
        super().add(pid)


def no_syntax_check():
    """The stand-in tests need no node, so the catalog's `node --check` is left out of them (MutationNodeTest has it)."""
    return mock.patch.object(quality.JS, "syntax_check", None)


def commit_delivery(work: Path) -> Path:
    """Make `work` a committed git checkout, as a finished run leaves it."""
    for args in (["init", "-q"], ["add", "-A"], [*GIT_IDENTITY, "commit", "-q", "-m", "delivery"]):
        subprocess.run(["git", "-C", str(work), *args], check=True, capture_output=True)
    return work


def tree_digest(root: Path) -> dict:
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file() and ".git" not in path.relative_to(root).parts}


class QualityCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        e2e.isolate_git(self)
        self.groups = RecordingGroups()
        # No test of this file reads the machine's process table: the listener scan sees nothing unless a class scopes it.
        patch = mock.patch.object(listeners, "observe", return_value=[])
        patch.start()
        self.addCleanup(patch.stop)

    def delivery(self, name: str = "work", source: Path = TINY, extra: dict | None = None) -> Path:
        work = self.tmp / name
        shutil.copytree(source, work)
        for relative, text in (extra or {}).items():
            (work / relative).parent.mkdir(parents=True, exist_ok=True)
            (work / relative).write_text(text)
        return commit_delivery(work)

    def mutate(self, command: str = "python3 check.py", name: str = "copy", **kw) -> tuple[dict, Path]:
        copy = self.tmp / name
        if not copy.exists():
            shutil.copytree(TINY, copy)
        spec = {"command": command, **kw.pop("spec", {})}
        kw.setdefault("stop", lambda: None)
        return quality.mutation(copy, spec, groups=self.groups, logs=self.tmp / f"logs-{name}", **kw), copy


# ---------------------------------------------------------------------------------------------------------------------
# The operator catalog


@needs_quality
class MutationOperatorTest(QualityCase):
    """What counts as a place to mutate: operators in code and nowhere else."""

    def found(self, source: str) -> list[tuple]:
        return [(site["op"], site["old"], site["new"]) for site in quality.sites(source)]

    def test_each_operator_finds_its_sites_in_code(self):
        table = {
            "a === b": [("eq-flip", "===", "!==")],
            "a !== b": [("eq-flip", "!==", "===")],
            "a <= b": [("rel-bound", "<=", "<")],
            "a >= b": [("rel-bound", ">=", ">")],
            "a < b": [("rel-bound", "<", "<=")],
            "a > b": [("rel-bound", ">", ">=")],
            "a && b": [("logic-flip", "&&", "||")],
            "a || b": [("logic-flip", "||", "&&")],
            "x = true": [("bool-flip", "true", "false")],
            "x = false": [("bool-flip", "false", "true")],
            "a + b": [("arith-flip", "+", "-")],
            "a - b": [("arith-flip", "-", "+")],
            "i < 10": [("rel-bound", "<", "<="), ("bound-literal", "10", "11")],
            "n >= 5": [("rel-bound", ">=", ">"), ("bound-literal", "5", "6")],
        }
        for source, expected in table.items():
            with self.subTest(source=source):
                self.assertEqual(self.found(source), expected)

    def test_comments_strings_and_templates_hold_no_site(self):
        for source in ("let s = 'a === b'", 'let s = "a && b || true"', "let s = `a < ${b > 1}`", "// a === b && true\n",
                       "/* a < b */", "let s = 'it\\'s a === b'"):
            with self.subTest(source=source):
                self.assertEqual(self.found(source), [])

    def test_syntax_that_resembles_an_operator_is_not_one(self):
        table = {"const f = (x) => x": [], "i++": [], "i--": [], "a+b": [], "x = -1": [], "const trueish = 1": [],
                 "n < 2.5": [("rel-bound", "<", "<=")],  # a number with a fraction is not stepped
                 "a >> 2": [("bound-literal", "2", "3")]}  # the shift is no comparison; the literal after `>` is still stepped
        for source, expected in table.items():
            with self.subTest(source=source):
                self.assertEqual(self.found(source), expected)

    def test_the_tiny_product_has_the_sites_its_tests_are_written_around(self):
        by_file = {name: quality.sites((TINY / name).read_text()) for name in ("lib.js", "other.js", "unused.js")}
        self.assertEqual([(s["op"], s["old"], s["new"], s["line"]) for s in by_file["lib.js"]],
                         [("rel-bound", ">=", ">", 4), ("bound-literal", "18", "19", 4), ("rel-bound", ">", ">=", 6),
                          ("bound-literal", "0", "1", 6), ("logic-flip", "&&", "||", 6), ("rel-bound", "<", "<=", 6),
                          ("bound-literal", "10", "11", 6), ("bool-flip", "false", "true", 9)],
                         "the comment on line 2 and the string on line 3 name operators and are not code")
        self.assertEqual(len(by_file["other.js"]), 2)
        self.assertEqual(len(by_file["unused.js"]), 2)

    def test_the_mask_keeps_length_and_lines(self):
        source = "a // x === y\nb /* c\nd */ e 'f g' h `i\nj`"
        masked = quality.mask(source)
        self.assertEqual(len(masked), len(source))
        self.assertEqual(masked.count("\n"), source.count("\n"))
        self.assertNotIn("===", masked)

    def test_the_mutants_are_taken_round_robin_across_files(self):
        order = quality.round_robin({"a.js": [1, 2, 3], "b.js": [4], "c.js": [5, 6]})
        self.assertEqual([(name, site) for name, site in order], [("a.js", 1), ("b.js", 4), ("c.js", 5), ("a.js", 2), ("c.js", 6),
                                                                  ("a.js", 3)])
        self.assertEqual(quality.round_robin({}), [])

    def test_the_ratio_is_null_when_nothing_was_decided(self):
        self.assertIsNone(quality.ratio(0, 0))
        self.assertEqual(quality.ratio(5, 7), 0.4167)



# ---------------------------------------------------------------------------------------------------------------------
# The mutation run, driven by a stand-in for `node --test` (no node needed)

SURVIVORS = [
    {"file": "lib.js", "line": 6, "op": "rel-bound", "from": ">", "to": ">="},
    {"file": "lib.js", "line": 6, "op": "bound-literal", "from": "0", "to": "1"},
    {"file": "lib.js", "line": 6, "op": "rel-bound", "from": "<", "to": "<="},
    {"file": "lib.js", "line": 6, "op": "bound-literal", "from": "10", "to": "11"},
    {"file": "other.js", "line": 2, "op": "eq-flip", "from": "===", "to": "!=="},
    {"file": "unused.js", "line": 2, "op": "rel-bound", "from": ">", "to": ">="},
    {"file": "unused.js", "line": 2, "op": "bound-literal", "from": "2", "to": "3"},
]


@needs_quality
class MutationRunTest(QualityCase):
    def setUp(self):
        super().setUp()
        patch = no_syntax_check()
        patch.start()
        self.addCleanup(patch.stop)

    def test_a_mutant_the_tests_catch_and_one_they_miss_are_told_apart_and_the_source_is_restored(self):
        before = tree_digest(TINY)
        block, copy = self.mutate()
        self.assertTrue(block["observed"], block)
        self.assertEqual((block["sites"], block["killed"], block["survived"], block["invalid"], block["not_run"], block["timeout"]),
                         (12, 5, 7, 0, 0, 0))
        self.assertEqual((block["ratio"], block["ceiling_hit"], block["operator_id"]), (0.4167, False, "js-1"))
        self.assertEqual(block["killed"] + block["survived"] + block["invalid"] + block["not_run"], block["sites"])
        self.assertEqual(block["baseline"]["tests"], 4)
        self.assertEqual(sorted(block["survivors"], key=lambda s: (s["file"], s["line"], s["op"], s["from"])),
                         sorted(SURVIVORS, key=lambda s: (s["file"], s["line"], s["op"], s["from"])))
        self.assertEqual({name: (row["sites"], row["killed"], row["survived"]) for name, row in block["per_file"].items()},
                         {"lib.js": (8, 4, 4), "other.js": (2, 1, 1), "unused.js": (2, 0, 2)})
        self.assertEqual(tree_digest(copy), before, "every mutated file is back as it was")

    def test_what_the_tests_load_is_proved_by_a_caught_mutant_and_unknown_without_a_coverage_record(self):
        block, _copy = self.mutate()
        self.assertEqual({name: row["loaded_by_tests"] for name, row in block["per_file"].items()},
                         {"lib.js": True, "other.js": True, "unused.js": None},
                         "a file with a confirmed caught mutant shows a sign of a load; with no coverage record the others are unknown, not false")

    def test_a_file_the_coverage_misses_but_a_caught_mutant_proves_is_loaded(self):
        # The saved r1 Checkers run: server.js is run only by a child the tests stop with a signal, so it writes no coverage,
        # and 23 of its 32 mutants were caught. "Never loaded" would have been false.
        with mock.patch.object(quality.JS, "coverage_files", lambda directory, copy: {"other.js"}):
            block, _ = self.mutate()
        self.assertEqual({name: row["loaded_by_tests"] for name, row in block["per_file"].items()},
                         {"lib.js": True, "other.js": True, "unused.js": False})

    def test_test_files_dependencies_docs_and_the_cases_exclusions_are_not_source(self):
        copy = self.tmp / "copy"
        shutil.copytree(TINY, copy)
        for relative in ("docs/shiploop/browser-check.js", "node_modules/dep/index.js", "tests/more.js", "system/probe.js",
                         "price.test.js", "price.spec.mjs", "test-helper.js", "test.js", "lib/checks_test.js", "lib/a-test.cjs"):
            (copy / relative).parent.mkdir(parents=True, exist_ok=True)
            (copy / relative).write_text("const x = a > 1 && b;\n")
        (copy / "latest.js").write_text("const x = a > 1;\n")  # looks like `test` to a careless pattern, and is source
        block, _ = self.mutate(spec={"exclude": ["system", "unused.js"]})
        self.assertEqual(sorted(block["per_file"]), ["latest.js", "lib.js", "other.js"])
        self.assertEqual(block["sites"], 12)

    def test_a_red_baseline_is_not_observed_and_never_a_ratio(self):
        for mode, reason in (("red", "exited 1"), ("zero", "counted no tests"), ("silent", "nothing readable")):
            with self.subTest(mode=mode), mock.patch.dict(os.environ, {"BASELINE": mode}):
                block, _ = self.mutate(name=f"copy-{mode}")
                self.assertFalse(block["observed"])
                self.assertIn(reason, block["reason"])
                self.assertNotIn("ratio", block)
                self.assertNotIn("killed", block)

    def test_a_baseline_that_does_not_finish_is_not_observed(self):
        with mock.patch.dict(os.environ, {"SLOW": "5"}), mock.patch.object(quality, "RUN_CEILING_SECONDS", 1):
            block, _ = self.mutate()
        self.assertFalse(block["observed"])
        self.assertIn("did not finish within the ceiling", block["reason"])

    def test_a_command_that_is_not_there_is_a_red_baseline_not_a_crash(self):
        block, _ = self.mutate(command="no-such-test-runner-xyz --test")
        self.assertFalse(block["observed"])
        self.assertIn("exited 127", block["reason"])

    def test_a_delivery_in_a_language_with_no_catalog_is_not_observed_and_says_what_it_holds(self):
        copy = self.tmp / "py"
        copy.mkdir()
        (copy / "tool.py").write_text("def f(a, b):\n    return a > b\n")
        (copy / "README.md").write_text("# x\n")
        block = quality.mutation(copy, {"command": "python3 -m unittest"}, groups=self.groups, stop=lambda: None, logs=self.tmp / "l")
        self.assertFalse(block["observed"])
        self.assertIn("no delivered source file has an operator catalog", block["reason"])
        self.assertIn(".md 1", block["reason"])
        self.assertIn(".py 1", block["reason"])

    def test_source_with_no_operator_is_not_observed(self):
        copy = self.tmp / "plain"
        copy.mkdir()
        (copy / "a.js").write_text("module.exports = 42;\n")
        block = quality.mutation(copy, {"command": "python3 -c pass"}, groups=self.groups, stop=lambda: None, logs=self.tmp / "l")
        self.assertFalse(block["observed"])
        self.assertIn("no operator applies", block["reason"])

    def test_a_mutant_that_is_not_valid_syntax_is_dropped_from_the_ratio(self):
        checker = "import sys; sys.exit(1 if 'const spin = true' in open(sys.argv[1]).read() else 0)"
        with mock.patch.object(quality.JS, "syntax_check", lambda path: [sys.executable, "-c", checker, str(path)]):
            block, _ = self.mutate(name="copy-invalid")
        self.assertEqual((block["invalid"], block["killed"], block["survived"], block["sites"]), (1, 4, 7, 12))
        self.assertEqual(block["ratio"], 0.3636, "4 of the 11 mutants that are programs")
        self.assertEqual(block["per_file"]["lib.js"]["invalid"], 1)

    def test_two_runs_over_the_same_copy_give_the_same_survivors(self):
        first, _ = self.mutate(name="copy-a")
        second, _ = self.mutate(name="copy-b")
        self.assertEqual(first["survivors"], second["survivors"])
        self.assertEqual({k: first[k] for k in ("sites", "killed", "survived", "ratio")},
                         {k: second[k] for k in ("sites", "killed", "survived", "ratio")})

    def test_a_ceiling_hit_leaves_a_sample_of_every_file_and_counts_the_rest_as_not_run(self):
        ticks = iter(range(1000))
        with mock.patch.object(quality, "PHASE_CEILING_SECONDS", 5):
            block, _ = self.mutate(clock=lambda: next(ticks))  # the phase reads its clock once per mutant: 4 mutants fit
        self.assertTrue(block["ceiling_hit"])
        tested = {name: row["killed"] + row["survived"] for name, row in block["per_file"].items()}
        self.assertEqual(sum(tested.values()), 4)
        self.assertEqual(sorted(tested.values()), [1, 1, 2], "the first mutant of every file ran before a second of any")
        self.assertEqual(block["not_run"], 8)
        self.assertEqual(block["not_run_reasons"], {"the phase ceiling was reached": 8})
        self.assertEqual(block["killed"] + block["survived"] + block["invalid"] + block["not_run"], block["sites"])
        self.assertEqual(sum(row["not_run"] for row in block["per_file"].values()), 8)
        self.assertIsNotNone(block["ratio"], "a ratio over the mutants that did run is recorded beside ceiling_hit")

    def test_a_requested_stop_ends_the_phase_with_no_ratio_and_the_source_intact(self):
        before = tree_digest(TINY)
        asked = []

        def stop():
            asked.append(1)
            return "terminated by SIGTERM" if len(asked) > 3 else None

        block, copy = self.mutate(stop=stop)
        self.assertFalse(block["observed"])
        self.assertIn("terminated by SIGTERM", block["reason"])
        self.assertRegex(block["reason"], r"ended (after \d+ of 12 mutants|during mutant \d+ of 12)")
        self.assertNotIn("ratio", block)
        self.assertEqual(tree_digest(copy), before)

    def test_a_stop_between_a_failing_run_and_its_confirmation_confirms_nothing(self):
        # The first mutant fails; the stop is asked before it is run again. A run the stop itself killed would confirm anything.
        asked = []

        def stop():
            asked.append(1)
            return "stopped by x" if len(asked) == 2 else None  # call 1: before the first mutant; call 2: before its second run

        block, copy = self.mutate(stop=stop)
        self.assertFalse(block["observed"])
        self.assertIn("during mutant 1 of 12", block["reason"])
        self.assertNotIn("kills", block)
        self.assertEqual(tree_digest(copy), tree_digest(TINY))

    def test_a_stop_that_arrives_during_the_last_mutant_discards_the_ratio_too(self):
        # A run the stop killed exits non-zero and would read as a caught mutant: the ratio must not include it.
        asked = []

        def stop():
            asked.append(1)  # asked before each of the 12 mutants, before each of the 5 confirmations, then once more after the last
            return "terminated by SIGTERM" if len(asked) > 12 + 5 else None

        block, _ = self.mutate(stop=stop)
        self.assertFalse(block["observed"])
        self.assertIn("during its last mutant", block["reason"])
        self.assertNotIn("ratio", block)

    def test_line_endings_and_non_ascii_text_survive_a_mutation_run_byte_for_byte(self):
        copy = self.tmp / "crlf"
        copy.mkdir()
        original = "function f(a) {\r\n  return a > 1 && '\u00e9';\r\n}\r\nmodule.exports = { f };\r\n".encode("utf-8")
        (copy / "a.js").write_bytes(original)
        (copy / "check.py").write_text("print('# tests 1\\n# pass 1\\n# fail 0\\n# cancelled 0')\n")
        block = quality.mutation(copy, {"command": "python3 check.py"}, groups=self.groups, stop=lambda: None, logs=self.tmp / "l")
        self.assertTrue(block["observed"], block)
        self.assertEqual(block["sites"], 3)
        self.assertEqual((copy / "a.js").read_bytes(), original)

    def test_every_caught_mutant_is_confirmed_by_a_second_run_and_records_the_first_failing_line(self):
        block, _ = self.mutate()
        self.assertEqual((block["killed"], block["unconfirmed"]), (5, 0))
        self.assertEqual(block["killed"] + block["survived"] + block["invalid"] + block["unconfirmed"] + block["not_run"], block["sites"])
        by_site = {(k["file"], k["from"], k["to"]): k for k in block["kills"]}
        self.assertEqual(len(by_site), 5)
        self.assertEqual(by_site[("lib.js", ">=", ">")]["evidence"], "not ok - an adult is 18 or more")
        self.assertEqual(by_site[("other.js", "+", "-")]["evidence"], "not ok - sum adds")
        self.assertTrue(all(not k["timeout"] and k["port_refusals"] == 0 for k in block["kills"]))
        self.assertEqual(len(self.groups.added), 1 + 12 + 5, "the baseline, each mutant, and one more run for each failure")

    def test_a_failure_that_does_not_repeat_is_unconfirmed_and_stays_out_of_the_ratio(self):
        # Reviewer A: five sweeps of one saved delivery gave 78 of 86 four times and 80 of 86 once, the two extra kills passing 3 of 3 alone.
        with mock.patch.dict(os.environ, {"FLAKY_ONCE": "1"}):
            block, _ = self.mutate()
        self.assertEqual((block["killed"], block["survived"], block["unconfirmed"], block["sites"]), (4, 7, 1, 12))
        self.assertEqual(block["ratio"], 0.3636, "4 of the 11 mutants that were decided")
        (flaky,) = block["unconfirmed_mutants"]
        self.assertEqual((flaky["file"], flaky["from"], flaky["to"]), ("lib.js", ">=", ">"))
        self.assertEqual((flaky["first"]["returncode"], flaky["first"]["evidence"]), (1, "not ok - an adult is 18 or more"))
        self.assertEqual(flaky["second"]["returncode"], 0)
        self.assertEqual(block["per_file"]["lib.js"]["unconfirmed"], 1)
        self.assertNotIn(("lib.js", ">="), {(k["file"], k["from"]) for k in block["kills"]})

    def test_a_hang_is_not_run_twice_and_is_a_kill_that_says_it_timed_out(self):
        copy = self.tmp / "copy"
        shutil.copytree(TINY, copy)
        with no_syntax_check(), mock.patch.dict(os.environ, {"HANG_ON_SPIN": "1"}), mock.patch.object(quality, "RUN_CEILING_SECONDS", 1):
            block = quality.mutation(copy, {"command": "python3 check.py"}, groups=self.groups, stop=lambda: None, logs=self.tmp / "l")
        (hung,) = [k for k in block["kills"] if k["timeout"]]
        self.assertEqual((hung["file"], hung["to"], hung["evidence"]), ("lib.js", "true", "timed out after 1 s"))
        self.assertEqual(len(self.groups.added), 1 + 12 + 4, "the four ordinary failures were run again, the hang was not")

    def test_only_a_confirmed_failure_that_is_not_a_hang_shows_a_sign_of_a_load(self):
        # A hang, or a failure that does not repeat, can come from load or a port collision in a file that never ran.
        copy = self.tmp / "copy"
        shutil.copytree(TINY, copy)

        def fake(argv, cwd, env, log, ceiling, groups):
            spin = "const spin = true" in (cwd / "lib.js").read_text()
            return {"returncode": None if spin else 0, "timeout": spin, "seconds": 0.1,
                    "output": "# tests 4\n# pass 4\n# fail 0\n# cancelled 0\n"}

        with mock.patch.object(quality, "run_once", fake), mock.patch.object(quality.JS, "coverage_files", lambda directory, copy: set()), \
                no_syntax_check():
            block = quality.mutation(copy, {"command": "python3 check.py"}, groups=self.groups, stop=lambda: None, logs=self.tmp / "l")
        self.assertEqual((block["killed"], block["timeout"]), (1, 1))
        self.assertEqual({name: row["loaded_by_tests"] for name, row in block["per_file"].items()},
                         {"lib.js": False, "other.js": False, "unused.js": False},
                         "the only kill was a hang: no sign of a load, not a proof of one")

    def test_a_syntax_check_that_does_not_finish_is_not_run_with_its_reason_and_not_invalid(self):
        hangs = "import sys, time; text = open(sys.argv[1]).read(); time.sleep(5) if 'const spin = true' in text else sys.exit(0)"
        with mock.patch.object(quality.JS, "syntax_check", lambda path: [sys.executable, "-c", hangs, str(path)]), \
                mock.patch.object(quality, "RUN_CEILING_SECONDS", 1):
            block, _ = self.mutate(name="copy-slow-syntax")
        self.assertEqual((block["invalid"], block["not_run"], block["killed"], block["survived"], block["sites"]), (0, 1, 4, 7, 12))
        self.assertEqual(block["not_run_reasons"], {"its syntax check did not finish": 1})
        self.assertEqual(block["per_file"]["lib.js"]["not_run"], 1)
        self.assertEqual(block["ratio"], 0.3636)

    def test_a_syntax_check_that_cannot_start_is_not_run_not_invalid(self):
        with mock.patch.object(quality.JS, "syntax_check", lambda path: ["no-such-syntax-checker-xyz", str(path)]):
            block, _ = self.mutate(name="copy-no-checker")
        self.assertEqual((block["invalid"], block["not_run"], block["killed"]), (0, 12, 0))
        self.assertEqual(block["not_run_reasons"], {"its syntax check could not start": 12})
        self.assertIsNone(block["ratio"])

    def test_page_script_no_operator_reaches_is_named_with_its_lines_beside_the_lines_mutated(self):
        copy = self.tmp / "copy"
        shutil.copytree(TINY, copy)
        (copy / "public").mkdir()
        (copy / "public" / "index.html").write_text("<!doctype html>\n<script src=\"x.js\">\nignored();\nignored();\n</script>\n<script>\nlet a = 1;\na += 2;\n</script>\n"
                                                   "<script type=\"module\">\nb();\n</script>\n")
        (copy / "docs").mkdir()
        (copy / "docs" / "page.html").write_text("<script>\nc();\n</script>\n")  # a ShipLoop record, not the delivery
        (copy / "static.html").write_text("<p>no script</p>\n")
        block, _ = self.mutate()
        self.assertEqual(block["uncovered"], [{"file": "public/index.html", "inline_script_lines": 3}])
        self.assertEqual({name: row["lines"] for name, row in block["per_file"].items()}, {"lib.js": 10, "other.js": 3, "unused.js": 2})

    def test_a_delivery_with_no_inline_page_script_names_none(self):
        block, _ = self.mutate()
        self.assertEqual(block["uncovered"], [])

    def test_the_block_records_its_ceilings_and_the_command(self):
        block, _ = self.mutate()
        self.assertEqual(block["ceilings"], {"run_seconds": quality.RUN_CEILING_SECONDS, "phase_seconds": quality.PHASE_CEILING_SECONDS})
        self.assertEqual(block["command"], "python3 check.py")


    def test_the_cases_source_for_the_command_is_carried_into_the_record(self):
        block, _ = self.mutate(spec={"source": "the request says node --test"})
        self.assertEqual(block["source"], "the request says node --test")


@needs_node
@needs_quality
class MutationNodeTest(QualityCase):
    """The same tiny delivery under the real `node --test`, the real syntax check and the real coverage record."""

    def test_the_real_runner_gives_the_ratio_the_stand_in_gives_and_knows_which_files_the_tests_load(self):
        block, copy = self.mutate(command="node --test")
        self.assertTrue(block["observed"], block)
        self.assertEqual((block["sites"], block["killed"], block["survived"], block["invalid"], block["ratio"]), (12, 5, 7, 0, 0.4167))
        self.assertEqual(block["baseline"]["tests"], 4, "counted by the engine's reader from the real summary")
        self.assertEqual({name: row["loaded_by_tests"] for name, row in block["per_file"].items()},
                         {"lib.js": True, "other.js": True, "unused.js": False},
                         "unused.js is never required: its two sites survive for that reason and the record says so")
        self.assertEqual(tree_digest(copy), tree_digest(TINY))

    def test_the_catalogs_syntax_check_tells_a_program_from_one_that_does_not_parse(self):
        good, bad = self.tmp / "good.js", self.tmp / "bad.js"
        good.write_text("const a = 1;\n")
        bad.write_text("const = ;\n")
        codes = [quality.run_once(quality.JS.syntax_check(path), self.tmp, quality.child_env(), self.tmp / "syntax.log",
                                  quality.RUN_CEILING_SECONDS, self.groups)["returncode"] for path in (good, bad)]
        self.assertEqual(codes[0], 0)
        self.assertNotEqual(codes[1], 0)

    def test_every_group_the_phase_started_is_registered_and_then_forgotten(self):
        block, _ = self.mutate(command="node --test")
        self.assertTrue(block["observed"])
        self.assertEqual(set(self.groups), set(), "every group the phase started was forgotten once its leader was reaped")
        self.assertGreater(len(self.groups.added), 12, "and it had registered each one: baseline, 12 mutants and their syntax checks")



# ---------------------------------------------------------------------------------------------------------------------
# Process safety

def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def gone_soon(pid: int, seconds: float = 5.0) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        if not alive(pid):
            return True
        time.sleep(0.05)
    return False


def kill_quietly(pid: int) -> None:
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.kill(pid, signal.SIGKILL)


# A process that starts a child and sleeps (each for at most 60 s, so a failing test leaves nothing for long); its pids go to argv[1].
PARENT_AND_CHILD = (
    "import os, subprocess, sys, time\n"
    "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
    "open(sys.argv[1], 'w').write('%d %d' % (os.getpid(), child.pid))\n"
    "time.sleep(60)\n")


@needs_quality
class ProcessSafetyTest(QualityCase):
    """What the quality phase may signal, and what ends it."""

    def read_pids(self, path: Path) -> tuple[int, int]:
        for _ in range(200):
            if path.exists() and path.read_text().count(" "):
                break
            time.sleep(0.05)
        parent, child = map(int, path.read_text().split())
        self.addCleanup(kill_quietly, child)
        self.addCleanup(kill_quietly, parent)
        return parent, child

    def test_a_group_is_ended_whole_while_its_leader_still_leads_it(self):
        pidfile = self.tmp / "pids"
        proc = quality.start([sys.executable, "-c", PARENT_AND_CHILD, str(pidfile)], self.tmp, quality.child_env(),
                             self.tmp / "log", self.groups)
        self.addCleanup(kill_quietly, proc.pid)
        parent, child = self.read_pids(pidfile)
        self.assertEqual(os.getpgid(child), proc.pid, "the child shares the leader's group, so the group kill reaches it")
        self.assertIn(proc.pid, self.groups, "registered at once, so a signal to the harness ends it")
        self.assertTrue(quality.end_group(proc))
        self.assertTrue(gone_soon(child), "the leader's child ended with the group")
        self.assertFalse(alive(parent))

    def test_a_process_that_does_not_lead_its_group_is_never_signalled(self):
        # Started in the test's own group: its pid is not a group id. A killpg on it would signal an unrelated group (or none).
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], stdin=subprocess.DEVNULL)
        self.addCleanup(e2e.end_quietly, proc)
        self.assertNotEqual(os.getpgid(proc.pid), proc.pid)
        with mock.patch.object(os, "killpg") as killpg:
            self.assertFalse(quality.end_group(proc))
        killpg.assert_not_called()
        self.assertTrue(alive(proc.pid))


    def test_every_group_is_registered_while_it_runs_and_forgotten_after(self):
        result = quality.run_once([sys.executable, "-c", "pass"], self.tmp, quality.child_env(), self.tmp / "log", 5, self.groups)
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(len(self.groups.added), 1)
        self.assertEqual(set(self.groups), set())

    def test_a_group_the_phase_started_is_ended_by_the_harness_when_it_is_told_to_end(self):
        # run.end_live_hosts is what a SIGTERM to the harness and the exit hook call; the phase registers in the same set.
        # end_live_hosts signals every pid of the process-global set without a guard: the set is the test's own for its length.
        with mock.patch.object(run, "LIVE_HOST_GROUPS", set()):
            proc = quality.start([sys.executable, "-c", "import time; time.sleep(30)"], self.tmp, quality.child_env(), self.tmp / "log",
                                 run.LIVE_HOST_GROUPS)
            self.addCleanup(kill_quietly, proc.pid)
            self.assertEqual(set(run.LIVE_HOST_GROUPS), {proc.pid})
            run.end_live_hosts()
            self.assertEqual(proc.wait(timeout=10), -signal.SIGKILL)

    def orphans(self, copy: Path) -> list[int]:
        pids = [int(line) for line in (copy / "orphans.txt").read_text().split()]
        for pid in pids:
            self.addCleanup(kill_quietly, pid)
        return pids

    def test_a_test_run_that_leaves_a_helper_in_its_group_leaves_nothing_behind_and_keeps_its_exit_code(self):
        # A run that exits 0 while a helper it started shares its group (a test that unrefs a spawned process): the leader's
        # exit must not drop the group, or the helper is orphaned and no signal to the harness can reach it again.
        copy = self.tmp / "copy"
        shutil.copytree(TINY, copy)
        with mock.patch.dict(os.environ, {"ORPHAN": "1"}):
            result = quality.run_once([sys.executable, "check.py"], copy, quality.child_env(), self.tmp / "log", 30, self.groups)
        (helper,) = self.orphans(copy)
        self.assertEqual((result["returncode"], result["timeout"]), (0, False), "ending the group after the exit does not change the code")
        self.assertTrue(gone_soon(helper), "the helper the run left behind was ended with its group")
        self.assertEqual(set(self.groups), set())

    def test_a_mutation_phase_over_a_test_run_that_leaves_helpers_leaves_none_alive(self):
        copy = self.tmp / "copy"
        shutil.copytree(TINY, copy)
        with no_syntax_check(), mock.patch.dict(os.environ, {"ORPHAN": "1"}):
            block = quality.mutation(copy, {"command": "python3 check.py"}, groups=self.groups, stop=lambda: None, logs=self.tmp / "l")
        self.assertTrue(block["observed"], block)
        helpers = self.orphans(copy)
        self.assertEqual(len(helpers), block["sites"] + 1 + block["killed"], "one per run: the baseline, each mutant and each confirmation")
        self.assertTrue(all(gone_soon(pid) for pid in helpers))

    def test_a_group_whose_leader_has_exited_but_is_not_reaped_is_ended_and_one_already_reaped_is_not(self):
        copy = self.tmp / "copy"
        shutil.copytree(TINY, copy)
        with mock.patch.dict(os.environ, {"ORPHAN": "1"}):
            proc = quality.start([sys.executable, "check.py"], copy, quality.child_env(), self.tmp / "log", self.groups)
            os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOWAIT)  # the leader is a zombie: it pins its group id
        (helper,) = self.orphans(copy)
        self.assertTrue(alive(helper))
        self.assertTrue(quality.end_group(proc), "the zombie leader still pins the group: its helper is ended")
        self.assertTrue(gone_soon(helper))
        with mock.patch.object(os, "getpgid", return_value=proc.pid), mock.patch.object(os, "killpg") as killpg:
            self.assertFalse(quality.end_group(proc), "a leader that was reaped may have its pid reused: nothing is signalled")
        killpg.assert_not_called()

    def test_a_hanging_mutant_is_counted_killed_and_its_whole_group_ends(self):
        copy = self.tmp / "copy"
        shutil.copytree(TINY, copy)
        began = time.monotonic()
        with no_syntax_check(), mock.patch.dict(os.environ, {"HANG_ON_SPIN": "1"}), mock.patch.object(quality, "RUN_CEILING_SECONDS", 1):
            block = quality.mutation(copy, {"command": "python3 check.py"}, groups=self.groups, stop=lambda: None, logs=self.tmp / "l")
        # The hung run and its child would sleep for 60 s on their own: the phase ended them, it did not wait them out.
        self.assertLess(time.monotonic() - began, 30)
        self.assertTrue(block["observed"], block)
        self.assertEqual((block["timeout"], block["killed"], block["survived"]), (1, 5, 7),
                         "the spin mutant hangs: it is killed by the ceiling, as the stand-in's failing test would have killed it")
        self.assertEqual(block["per_file"]["lib.js"]["timeout"], 1)
        leader, child = map(int, (copy / "grandchild.pid").read_text().split())
        self.addCleanup(kill_quietly, child)
        self.assertTrue(gone_soon(child), "the hung run's child went with its group")
        self.assertFalse(alive(leader))
        self.assertFalse(alive(child), "and it went before its own 60 s were up")
        self.assertEqual(set(self.groups), set())
        self.assertEqual((copy / "lib.js").read_text(), (TINY / "lib.js").read_text(), "the hung mutant was undone")



# ---------------------------------------------------------------------------------------------------------------------
# Fixed ports the phase refuses

@needs_quality
class PortGuardTest(QualityCase):
    """A mutant must never listen on a port the case names (the product's default): the phase's children run under a preload that
    refuses it and counts the refusals. No test here binds or connects to a real fixed port; the declared port is whatever
    the stand-in writes into the log, or a free port picked by the test."""

    def setUp(self):
        super().setUp()
        patch = no_syntax_check()
        patch.start()
        self.addCleanup(patch.stop)

    def test_the_catalog_puts_the_preload_in_node_options_beside_what_was_there(self):
        env = quality.js_guard_env([3000, 4000], Path("/x/refusals.log"))
        self.assertIn("--require", env["NODE_OPTIONS"])
        self.assertIn(str(quality.REFUSE_PORTS_PRELOAD), env["NODE_OPTIONS"])
        self.assertEqual((env["SHIPLOOP_E2E_REFUSE_PORTS"], env["SHIPLOOP_E2E_REFUSE_LOG"]), ("3000,4000", "/x/refusals.log"))
        with mock.patch.dict(os.environ, {"NODE_OPTIONS": "--max-old-space-size=100"}):
            self.assertTrue(quality.js_guard_env([1], Path("/x")) ["NODE_OPTIONS"].startswith("--max-old-space-size=100 --require"))
        spaced = quality.js_guard_env([1], Path("/x"), preload=Path("/a dir/refuse ports.cjs"))["NODE_OPTIONS"]
        self.assertIn('"/a dir/refuse ports.cjs"', spaced, "a path with a space is quoted for NODE_OPTIONS")

    def test_every_child_of_the_phase_gets_the_ports_and_its_own_refusal_log(self):
        copy = self.tmp / "copy"
        shutil.copytree(TINY, copy)
        with mock.patch.dict(os.environ, {"DUMP_ENV": "1"}):
            block = quality.mutation(copy, {"command": "python3 check.py"}, groups=self.groups, stop=lambda: None, logs=self.tmp / "l",
                                     ports=[39999])
        self.assertTrue(block["observed"], block)
        options, ports, log = (copy / "env.txt").read_text().split("|")
        self.assertIn(str(quality.REFUSE_PORTS_PRELOAD), options)
        self.assertEqual(ports, "39999")
        self.assertTrue(log.startswith(str(self.tmp / "l")), "each run has a log of its own under the phase's logs")
        self.assertEqual((block["refuse_ports"], block["port_refusals"], block["port_refused"]), ([39999], 0, 0))

    def test_without_declared_ports_no_preload_is_added(self):
        copy = self.tmp / "copy"
        shutil.copytree(TINY, copy)
        with mock.patch.dict(os.environ, {"DUMP_ENV": "1"}):
            quality.mutation(copy, {"command": "python3 check.py"}, groups=self.groups, stop=lambda: None, logs=self.tmp / "l")
        self.assertEqual((copy / "env.txt").read_text().split("|")[1:], ["None", "None"])

    def test_a_delivery_whose_own_tests_touch_a_declared_port_is_not_run(self):
        copy = self.tmp / "copy"
        shutil.copytree(TINY, copy)
        with mock.patch.dict(os.environ, {"REFUSE_BASELINE": "1"}):
            block = quality.mutation(copy, {"command": "python3 check.py"}, groups=self.groups, stop=lambda: None, logs=self.tmp / "l",
                                     ports=[3000])
        self.assertFalse(block["observed"])
        self.assertIn("its tests bind a fixed port; not run", block["reason"])
        self.assertIn("3000", block["reason"])
        self.assertEqual(len(self.groups.added), 1, "only the baseline was started: no mutant ran")
        self.assertNotIn("ratio", block)

    def test_a_mutant_caught_with_a_refusal_keeps_the_marker_and_the_count_and_no_other_run_shares_it(self):
        copy = self.tmp / "copy"
        shutil.copytree(TINY, copy)
        with mock.patch.dict(os.environ, {"REFUSE_ON_ADULT": "1"}):  # the first mutant tried refuses a bind; eleven more run after it
            block = quality.mutation(copy, {"command": "python3 check.py"}, groups=self.groups, stop=lambda: None, logs=self.tmp / "l",
                                     ports=[3000])
        self.assertTrue(block["observed"], block)
        self.assertEqual((block["port_refusals"], block["port_refused"]), (1, 1))
        self.assertEqual((block["killed"], block["survived"]), (5, 7), "the counts are the ordinary ones: the marker is beside them")
        self.assertEqual([(kill["file"], kill["from"], kill["to"], kill["port_refusals"]) for kill in block["kills"] if kill["port_refusals"]],
                         [("lib.js", ">=", ">", 1)], "each run has its own refusal log, so a later run does not inherit the count")
        self.assertEqual(sum(kill["port_refusals"] for kill in block["kills"]), 1)
        self.assertTrue(all(not item.get("port_refusals") for item in block["survivors"]))
        self.assertEqual(block["per_file"]["lib.js"]["port_refusals"], 1)
        self.assertEqual(block["per_file"]["other.js"]["port_refusals"], 0)

    def test_a_product_that_ignores_port_and_meets_the_guard_says_so_instead_of_exited_1(self):
        directory = self.tmp / "checks"
        directory.mkdir()
        (directory / "tmpmod.py").write_text("CHECKS = {'one': lambda base: (True, base)}\n")
        crash = ("import os, sys; open(os.environ['SHIPLOOP_E2E_REFUSE_LOG'], 'a').write('1 listen 3000\\n'); sys.exit(1)")
        block = {"module": "tmpmod", "start": f"{sys.executable} -c \"{crash}\"", "source": "s", "checks": [{"id": "one", "source": "q"}]}
        folder = self.tmp / "accept"
        folder.mkdir()
        result = quality.acceptance(folder, block, groups=self.groups, stop=lambda: None, logs=folder / "logs", checks_dir=directory,
                                    ports=[3000])
        self.assertFalse(result["observed"])
        self.assertIn("exited 1", result["reason"])
        self.assertIn("declared port", result["reason"])
        self.assertIn("1 time", result["reason"])

    def test_the_cases_that_default_to_3000_declare_it(self):
        for name in ("battleship", "battleship-scoring", "checkers"):
            self.assertEqual(run.case_quality(name)["refuse_ports"], [3000], name)
        self.assertNotIn("refuse_ports", run.case_quality("hello"))


@needs_quality
class PrintedLineTest(unittest.TestCase):
    """quality.line: the one printed line says what the record says, in the record's words."""

    MUT = {"observed": True, "operator_id": "js-1", "sites": 12, "killed": 5, "survived": 7, "unconfirmed": 0, "ratio": 0.4167,
           "ceiling_hit": False, "timeout": 0, "port_refused": 0, "port_refusals": 0, "uncovered": [],
           "per_file": {"lib.js": {"loaded_by_tests": True}, "unused.js": {"loaded_by_tests": False}}}

    def test_a_file_with_no_sign_of_a_load_is_not_called_never_loaded(self):
        line = quality.line({"mutation": self.MUT})
        self.assertIn("no sign of a load in: unused.js", line)
        self.assertNotIn("never loaded", line)

    def test_unconfirmed_timeouts_refusals_and_unreached_page_script_are_in_the_line_when_there_are_any(self):
        plain = quality.line({"mutation": self.MUT})
        for word in ("unconfirmed", "timeout", "refus", "page script"):
            self.assertNotIn(word, plain)
        mutation = dict(self.MUT, unconfirmed=2, timeout=3, port_refused=1, port_refusals=4,
                        uncovered=[{"file": "public/index.html", "inline_script_lines": 69}])
        line = quality.line({"mutation": mutation})
        self.assertIn("2 unconfirmed", line)
        self.assertIn("3 timeouts", line)
        self.assertIn("4 port refusals", line)
        self.assertIn("page script no operator reaches: public/index.html 69 lines", line)


@needs_node
@needs_quality
class PortGuardNodeTest(QualityCase):
    """The real preload under the real node. The declared port is a free one the test picked and nothing of the test listens on
    it: if the preload failed, a throwaway node process would bind that free port for a moment, never a fixed one."""

    def run_script(self, source: str, port: int) -> tuple[str, int]:
        log = self.tmp / "refusals.log"
        log.write_text("")
        env = quality.child_env(quality.js_guard_env([port], log))
        done = subprocess.run(["node", "-e", source], env=env, capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
        return done.stdout + done.stderr, len(log.read_text().splitlines())

    def test_listening_on_the_declared_port_fails_like_an_address_in_use_in_every_form(self):
        port = quality.free_port()
        forms = {"number": f"{port}", "number and host": f"{port}, '127.0.0.1'", "string": f"'{port}'", "options": f"{{ port: {port} }}",
                 "options and callback": f"{{ port: {port}, host: '127.0.0.1' }}, () => {{}}"}
        for form, arguments in forms.items():
            with self.subTest(form=form):
                out, refusals = self.run_script(
                    f"const s = require('net').createServer(); s.on('error', e => {{ console.log('ERR ' + e.code); }}); s.listen({arguments});", port)
                self.assertIn("ERR EADDRINUSE", out)
                self.assertEqual(refusals, 1)
        out, refusals = self.run_script(
            f"const s = require('http').createServer(); s.on('error', e => console.log('ERR ' + e.code)); s.listen({port});", port)
        self.assertEqual((out.strip(), refusals), ("ERR EADDRINUSE", 1), "an http server listens through net.Server")

    def test_connecting_to_the_declared_port_is_refused_by_net_http_and_fetch(self):
        port = quality.free_port()
        scripts = {
            "net": f"require('net').connect({port}, '127.0.0.1').on('error', e => console.log('ERR ' + e.code));",
            "http": f"require('http').get('http://127.0.0.1:{port}/').on('error', e => console.log('ERR ' + e.code));",
            "fetch": f"fetch('http://127.0.0.1:{port}/').catch(e => console.log('ERR ' + (e.cause && e.cause.code)));",
        }
        for name, script in scripts.items():
            with self.subTest(kind=name):
                out, refusals = self.run_script(script, port)
                self.assertIn("ERR ECONNREFUSED", out)
                self.assertEqual(refusals, 1)

    def test_other_ports_and_ephemeral_listens_are_untouched_and_children_inherit_the_guard(self):
        port = quality.free_port()
        out, refusals = self.run_script("const s = require('net').createServer().listen(0, () => { console.log('LISTENING'); s.close(); });", port)
        self.assertEqual((out.strip(), refusals), ("LISTENING", 0))
        child = (f"require('child_process').spawnSync(process.execPath, ['-e', \"require('net').createServer().on('error', e => "
                 f"console.log('CHILD ' + e.code)).listen({port})\"], {{ stdio: 'inherit' }});")
        out, refusals = self.run_script(child, port)
        self.assertIn("CHILD EADDRINUSE", out)
        self.assertEqual(refusals, 1)


# ---------------------------------------------------------------------------------------------------------------------
# Held-out acceptance

# The failing set each defect of the reference service must give: the exact set, so every check is shown to pass the correct
# service and to fail the defect it reads, and no defect goes unnoticed. offboard-400 is the shape the saved r3 Checkers
# delivery answered (HTTP 400 and {ok, error}, no turn and no winner).
EXPECTED_FAILURES = {
    None: set(),
    "black-first": set(CHECKERS_IDS),
    "illegal-flips-turn": {"red-moves-first", "illegal-keeps-turn", "red-jump-mandatory", "black-jump-mandatory-and-removal"},
    "offboard-400": {"off-board-keeps-turn"},
    "no-alternation": {"legal-moves-alternate", "red-jump-mandatory", "black-jump-mandatory-and-removal"},
    "optional-jump": {"red-jump-mandatory", "black-jump-mandatory-and-removal"},
    "black-optional-jump": {"black-jump-mandatory-and-removal"},
    "no-removal": {"black-jump-mandatory-and-removal"},
}


def checkers_block(defect: str | None, ids: list[str] = CHECKERS_IDS) -> dict:
    return {"module": "checkers_accept", "start": f"{sys.executable} {REFERENCE}" + (f" --defect {defect}" if defect else ""),
            "source": "the case prompt", "checks": [{"id": ident, "source": f"quote for {ident}"} for ident in ids]}


@needs_quality
class AcceptanceCalibrationTest(QualityCase):
    """Each held-out check against a hermetic reference service with one defect switch (a check admitted without this once failed
    4 of 5 good deliveries because it kept firing after the game was over)."""

    def run_defect(self, defect: str | None) -> dict:
        folder = self.tmp / f"accept-{defect}"
        folder.mkdir()
        return quality.acceptance(folder, checkers_block(defect), groups=self.groups, stop=lambda: None, logs=folder / "logs")

    def test_every_check_passes_the_correct_service_and_fails_the_defect_it_reads(self):
        for defect, expected in EXPECTED_FAILURES.items():
            with self.subTest(defect=defect):
                block = self.run_defect(defect)
                self.assertTrue(block["observed"], block)
                self.assertEqual({row["id"] for row in block["checks"] if not row["pass"]}, expected,
                                 {row["id"]: row["note"] for row in block["checks"] if not row["pass"]})
                self.assertEqual(block["passed"], [i for i in CHECKERS_IDS if i not in expected])
        self.assertEqual(set(), set(self.groups), "every server the checks started was ended")

    def test_every_check_is_failed_by_some_defect_and_every_defect_by_some_check(self):
        failing = [failed for defect, failed in EXPECTED_FAILURES.items() if defect]
        self.assertEqual(set().union(*failing), set(CHECKERS_IDS), "a check no defect fails could never fail")
        self.assertTrue(all(failing), "a defect no check fails would go unnoticed")

    def test_the_off_board_item_is_its_own_check_and_the_other_illegal_moves_pass_when_it_fails(self):
        block = self.run_defect("offboard-400")
        rows = {row["id"]: row for row in block["checks"]}
        self.assertTrue(rows["illegal-keeps-turn"]["pass"], "the bundled item once hid the one that discriminates")
        self.assertFalse(rows["off-board-keeps-turn"]["pass"])
        self.assertIn("HTTP 400", rows["off-board-keeps-turn"]["note"])

    def test_the_cases_declared_ids_are_exactly_the_modules_checks(self):
        module = quality.load_checks("checkers_accept", quality.HERE / "checks")
        declared = [item["id"] for item in run.case_quality("checkers")["acceptance"][0]["checks"]]
        self.assertEqual(declared, list(module.CHECKS))
        self.assertEqual(declared, CHECKERS_IDS)
        for item in run.case_quality("checkers")["acceptance"][0]["checks"]:
            self.assertTrue(item["source"], f"{item['id']} quotes the sentence it reads")

    def test_the_battleship_set_was_dropped_and_python_cases_declare_nothing(self):
        for name in ("battleship", "battleship-scoring", "hello", "csv-report", "seat-reservations"):
            self.assertNotIn("acceptance", run.case_quality(name), name)
        self.assertEqual(run.case_quality("battleship-scoring")["mutation"]["command"], "node --test",
                         "a follow-on is measured by the followed case's declaration")


@needs_quality
class AcceptanceRunTest(QualityCase):
    def accept(self, block: dict, **kw) -> dict:
        folder = self.tmp / f"run-{len(list(self.tmp.glob('run-*')))}"
        folder.mkdir()
        kw.setdefault("stop", lambda: None)
        return quality.acceptance(folder, block, groups=self.groups, logs=folder / "logs", **kw)

    def checks_dir(self, source: str) -> Path:
        folder = self.tmp / "checks"
        folder.mkdir(exist_ok=True)
        (folder / "tmpmod.py").write_text(source)
        return folder

    def block(self, start: str, ids=("one",)) -> dict:
        return {"module": "tmpmod", "start": start, "source": "s", "checks": [{"id": i, "source": f"q {i}"} for i in ids]}

    def test_a_server_that_never_listens_leaves_the_checks_unrun_and_its_group_ended(self):
        directory = self.checks_dir("CHECKS = {'one': lambda base: (True, base)}\n")
        with mock.patch.object(quality, "LISTEN_CEILING_SECONDS", 1):
            block = self.accept(self.block(f"{sys.executable} -c 'import time; time.sleep(30)'"), checks_dir=directory)
        self.assertFalse(block["observed"])
        self.assertIn("did not listen", block["reason"])
        self.assertNotIn("checks", block, "a check that did not run has no pass")
        self.assertEqual(set(self.groups), set())

    def test_a_server_that_exits_at_once_is_named_with_its_exit(self):
        directory = self.checks_dir("CHECKS = {'one': lambda base: (True, base)}\n")
        block = self.accept(self.block(f"{sys.executable} -c 'raise SystemExit(3)'"), checks_dir=directory)
        self.assertFalse(block["observed"])
        self.assertIn("exited 3", block["reason"])

    def test_a_server_command_that_is_not_there_is_a_reason_not_a_crash(self):
        directory = self.checks_dir("CHECKS = {'one': lambda base: (True, base)}\n")
        block = self.accept(self.block("no-such-server-binary-xyz"), checks_dir=directory)
        self.assertFalse(block["observed"])
        self.assertIn("could not be started", block["reason"])

    def test_a_declared_check_the_module_lacks_and_a_module_that_is_missing_are_harness_defects_said_so(self):
        directory = self.checks_dir("CHECKS = {}\n")
        block = self.accept(self.block("true", ids=("one", "two")), checks_dir=directory)
        self.assertFalse(block["observed"])
        self.assertIn("has no check for: one, two", block["reason"])
        block = self.accept(dict(self.block("true"), module="absent"), checks_dir=directory)
        self.assertFalse(block["observed"])
        self.assertIn("could not be loaded", block["reason"])

    def test_a_check_that_raises_fails_with_the_exception_and_the_others_still_run(self):
        directory = self.checks_dir("def boom(base):\n    raise RuntimeError('no')\nCHECKS = {'one': boom, 'two': lambda base: (True, 'fine')}\n")
        block = self.accept(dict(self.block(f"{sys.executable} {REFERENCE}", ids=("one", "two"))), checks_dir=directory)
        self.assertTrue(block["observed"], block)
        self.assertEqual([(row["id"], row["pass"]) for row in block["checks"]], [("one", False), ("two", True)])
        self.assertIn("RuntimeError", block["checks"][0]["note"])
        self.assertEqual((block["ids"], block["passed"]), (["one", "two"], ["two"]))

    def test_nothing_but_the_servers_own_command_line_reaches_an_argv(self):
        directory = self.checks_dir("CHECKS = {'secret-id': lambda base: (True, base)}\n")
        argvs = []
        real = subprocess.Popen

        def spy(argv, *args, **kwargs):
            argvs.append(list(argv))
            return real(argv, *args, **kwargs)

        with mock.patch.object(quality.subprocess, "Popen", side_effect=spy):
            block = self.accept(self.block(f"{sys.executable} {REFERENCE}", ids=("secret-id",)), checks_dir=directory)
        self.assertTrue(block["observed"], block)
        self.assertEqual(argvs, [[sys.executable, str(REFERENCE)]], "only the product's server was started")
        self.assertNotIn("secret-id", " ".join(" ".join(a) for a in argvs))
        self.assertNotIn("tmpmod", " ".join(" ".join(a) for a in argvs))

    def test_a_requested_stop_ends_the_checks_without_a_pass_for_the_unrun(self):
        directory = self.checks_dir("CHECKS = {'one': lambda base: (True, 'a'), 'two': lambda base: (True, 'b')}\n")
        asked = []
        block = self.accept(self.block(f"{sys.executable} {REFERENCE}", ids=("one", "two")), checks_dir=directory,
                            stop=lambda: asked.append(1) or ("stopped by x" if len(asked) > 1 else None))
        self.assertFalse(block["observed"])
        self.assertIn("ended after 1 of 2", block["reason"])
        self.assertEqual(set(self.groups), set())

    def test_the_record_keeps_each_checks_source_and_a_short_note(self):
        block = self.accept(checkers_block(None, ids=["red-moves-first"]))
        self.assertEqual(block["source"], "the case prompt")
        row = block["checks"][0]
        self.assertEqual((row["id"], row["source"], row["pass"]), ("red-moves-first", "quote for red-moves-first", True))
        self.assertLessEqual(len(row["note"]), 300)

    def test_two_blocks_of_a_followed_case_merge_the_followed_ones_first(self):
        first = {"observed": True, "source": "a", "ids": ["x"], "passed": ["x"], "checks": [{"id": "x", "pass": True}]}
        second = {"observed": True, "source": "b", "ids": ["y"], "passed": [], "checks": [{"id": "y", "pass": False}]}
        merged = quality.merge_acceptance([first, second])
        self.assertEqual((merged["ids"], merged["passed"], merged["source"]), (["x", "y"], ["x"], "a | b"))
        self.assertFalse(quality.merge_acceptance([first, {"observed": False, "reason": "no server"}])["observed"])
        self.assertIs(quality.merge_acceptance([first]), first)



# ---------------------------------------------------------------------------------------------------------------------
# Facts read from the events

MEMORY_EVENTS = FIXTURES / "memory-write-events.jsonl"


def tool_use_line(name: str, **arg) -> str:
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": name, "input": arg}]}})


@needs_quality
class EventFactsTest(QualityCase):
    def events(self, *lines: str, name: str = "events.jsonl") -> Path:
        path = self.tmp / name
        path.write_text("".join(line + "\n" for line in lines))
        return path

    def test_the_memory_writes_of_the_saved_checkers_run_are_found_in_its_events(self):
        # The real shape: r3-checkers-sonnet lines 599 and 605 (here 2 and 6) wrote feedback_no-broad-pkill.md and MEMORY.md; a Bash
        # call that only reads the folder, the tool results and a Grok-shaped line are not writes.
        found = quality.memory_writes(MEMORY_EVENTS)
        self.assertEqual([(w["tool"], w["line"], Path(w["path"]).name) for w in found],
                         [("Write", 2, "feedback_no-broad-pkill.md"), ("Write", 6, "MEMORY.md")])
        self.assertTrue(all("/.claude/projects/" in w["path"] and "/memory/" in w["path"] for w in found))

    def test_edit_and_multiedit_count_and_a_path_that_only_resembles_the_memory_folder_does_not(self):
        path = self.events(
            tool_use_line("Edit", file_path="/Users/x/.claude/projects/-a-b/memory/MEMORY.md", old_string="a", new_string="b"),
            tool_use_line("MultiEdit", file_path="/Users/x/.claude/projects/-a-b/memory/notes/n.md", edits=[]),
            tool_use_line("Write", file_path="/Users/x/.claude/projects/-a-b/memory-notes/n.md", content="x"),
            tool_use_line("Write", file_path="/Users/x/.claude/projects/-a-b/memory"),
            tool_use_line("Write", file_path="/Users/x/project/memory/n.md", content="x"),
            tool_use_line("Write", file_path="/Users/x/.claude/settings.json", content="x"),
            tool_use_line("Read", file_path="/Users/x/.claude/projects/-a-b/memory/MEMORY.md"),
            tool_use_line("Bash", command="echo hi > /Users/x/.claude/projects/-a-b/memory/shell.md"))
        self.assertEqual([(w["tool"], w["line"]) for w in quality.memory_writes(path)], [("Edit", 1), ("MultiEdit", 2), ("Write", 4)])

    def test_a_run_that_wrote_nothing_there_is_a_measured_empty_list(self):
        path = self.events(tool_use_line("Write", file_path="/work/server.js", content="x"))
        facts, unmeasured = quality.event_facts(path, ["claude"], [])
        self.assertEqual(facts["memory_writes"], [])
        self.assertNotIn("memory_writes", unmeasured)

    def test_events_that_are_absent_or_unreadable_leave_both_facts_null_with_the_reason(self):
        facts, unmeasured = quality.event_facts(self.tmp / "absent.jsonl", ["claude"], [{"module": "checkers_accept"}])
        self.assertEqual(facts, {"memory_writes": None, "held_out_seen": None})
        self.assertEqual(set(unmeasured), {"memory_writes", "held_out_seen"})
        self.assertIn("absent or unreadable", unmeasured["held_out_seen"])
        folder = self.tmp / "isdir.jsonl"
        folder.mkdir()
        facts, unmeasured = quality.event_facts(folder, ["claude"], [{"module": "checkers_accept"}])
        self.assertEqual(facts["held_out_seen"], None, "a directory where the events should be is unreadable, not zero")

    def test_a_run_with_no_claude_session_has_no_memory_measure_and_says_so(self):
        path = self.events(tool_use_line("Write", file_path="/Users/x/.claude/projects/-a/memory/MEMORY.md"))
        facts, unmeasured = quality.event_facts(path, ["grok"], [])
        self.assertIsNone(facts["memory_writes"])
        self.assertIn("grok", unmeasured["memory_writes"])
        facts, unmeasured = quality.event_facts(path, ["grok", "claude"], [])
        self.assertEqual(len(facts["memory_writes"]), 1, "a run Claude finished is read, whoever started it")
        facts, unmeasured = quality.event_facts(path, [], [])
        self.assertIsNone(facts["memory_writes"])
        self.assertIn("no host", unmeasured["memory_writes"])

    def test_held_out_seen_counts_lines_that_name_a_held_out_script_or_the_checks_folder(self):
        blocks = [{"module": "checkers_accept"}]
        path = self.events(json.dumps({"type": "text", "data": "I will read checkers_accept.py"}),
                           json.dumps({"type": "text", "data": "ls /x/test/shiploop_e2e/checks"}),
                           json.dumps({"type": "text", "data": "echo $E2E_CHECKS"}),
                           json.dumps({"type": "text", "data": "nothing of the kind"}))
        facts, unmeasured = quality.event_facts(path, ["grok"], blocks)
        self.assertEqual(facts["held_out_seen"], 3)
        self.assertNotIn("held_out_seen", unmeasured)

    def test_held_out_seen_is_a_measured_zero_when_the_events_name_nothing(self):
        path = self.events(json.dumps({"type": "text", "data": "pgrep -fl run.py"}))
        facts, _ = quality.event_facts(path, ["claude"], [{"module": "checkers_accept"}])
        self.assertEqual(facts["held_out_seen"], 0)

    def test_a_case_with_no_held_out_acceptance_has_nothing_held_out_to_see(self):
        path = self.events(json.dumps({"type": "text", "data": "echo $E2E_CHECKS"}))
        facts, unmeasured = quality.event_facts(path, ["claude"], [])
        self.assertIsNone(facts["held_out_seen"])
        self.assertIn("nothing is held out", unmeasured["held_out_seen"])

    def test_a_saved_run_without_acceptance_declares_no_markers_but_the_shared_ones(self):
        self.assertEqual(quality.held_out_markers([]), ["E2E_CHECKS", "shiploop_e2e/cases.json", "shiploop_e2e/checks"])



# ---------------------------------------------------------------------------------------------------------------------
# The block of a run

@needs_quality
class MeasureBlockTest(QualityCase):
    """quality.measure: the gate, the copy, the delivered folder left alone, and what it records."""

    def setUp(self):
        super().setUp()
        patch = no_syntax_check()
        patch.start()
        self.addCleanup(patch.stop)
        self.out = self.tmp / "out"
        self.out.mkdir()
        self.work = self.delivery("out/work")
        (self.out / "events.jsonl").write_text(MEMORY_EVENTS.read_text())

    def measure(self, spec=None, gate=None, hosts=("claude",), **kw) -> dict:
        spec = {"mutation": {"command": "python3 check.py"}} if spec is None else spec
        return quality.measure(self.out, self.work, spec, gate=gate, hosts_used=list(hosts), groups=self.groups,
                               stop=lambda: None, **kw)

    def test_a_finished_delivery_is_measured_on_a_copy_under_the_output_folder(self):
        block = self.measure()
        self.assertTrue(block["observed"], block)
        self.assertEqual((block["hosts"], block["mixed_host"]), (["claude"], False))
        self.assertEqual((block["mutation"]["sites"], block["mutation"]["ratio"]), (12, 0.4167))
        self.assertNotIn("reason", block)
        self.assertEqual(block["delivered_files"], len([p for p in TINY.rglob("*") if p.is_file()]))
        self.assertTrue((self.out / "quality" / "copy" / "lib.js").is_file())
        self.assertEqual(len(block["memory_writes"]), 2)
        self.assertIsNone(block["held_out_seen"])
        self.assertIn("nothing is held out", block["unmeasured"]["held_out_seen"])
        self.assertEqual(block["left_behind"], {"observed": True, "reaped": [], "survived": []})

    def test_the_delivered_folder_is_not_touched(self):
        before = tree_digest(self.work)
        status = subprocess.run(["git", "-C", str(self.work), "status", "--porcelain"], capture_output=True, text=True).stdout
        times = {str(p): p.stat().st_mtime_ns for p in self.work.rglob("*") if p.is_file() and ".git" not in p.parts}
        self.measure()
        self.assertEqual(tree_digest(self.work), before)
        self.assertEqual(subprocess.run(["git", "-C", str(self.work), "status", "--porcelain"], capture_output=True, text=True).stdout,
                         status)
        self.assertEqual({str(p): p.stat().st_mtime_ns for p in self.work.rglob("*") if p.is_file() and ".git" not in p.parts}, times)
        self.assertFalse((self.work / ".git" / "quality").exists())

    def test_the_gate_reason_is_the_reason_and_nothing_is_copied_or_run(self):
        block = self.measure(gate="ShipLoop is still active (stage implement), so no delivery was returned")
        self.assertEqual((block["observed"], block["reason"]), (False, "ShipLoop is still active (stage implement), so no delivery was returned"))
        self.assertNotIn("mutation", block)
        self.assertFalse((self.out / "quality").exists())
        self.assertEqual(self.groups.added, [], "no process was started")
        self.assertEqual(len(block["memory_writes"]), 2, "the events are read whether or not the delivery was")

    def test_a_case_that_declares_nothing_says_so(self):
        for spec in ({}, None):
            with self.subTest(spec=spec):
                block = quality.measure(self.out, self.work, spec, gate=None, hosts_used=["claude"], groups=self.groups, stop=lambda: None)
                self.assertFalse(block["observed"])
                self.assertIn("declares no quality measures", block["reason"])
                self.assertFalse((self.out / "quality").exists())

    def test_declared_measures_that_all_failed_to_run_give_one_reason_naming_each(self):
        with mock.patch.dict(os.environ, {"BASELINE": "red"}):
            block = self.measure()
        self.assertFalse(block["observed"])
        self.assertIn("none of the declared measures could be taken", block["reason"])
        self.assertIn("mutation: the unmutated copy's test run exited 1", block["reason"])
        self.assertFalse(block["mutation"]["observed"])

    def test_an_earlier_copy_of_a_regrade_is_replaced_not_reused(self):
        (self.out / "quality").mkdir()
        (self.out / "quality" / "stale.txt").write_text("a copy of an earlier phase")
        self.measure()
        self.assertFalse((self.out / "quality" / "stale.txt").exists())

    def test_hosts_come_from_the_launch_records_given_and_a_run_two_hosts_worked_on_is_marked(self):
        block = self.measure(hosts=("grok", "claude"))
        self.assertEqual((block["hosts"], block["mixed_host"]), (["grok", "claude"], True))
        self.assertEqual(len(block["memory_writes"]), 2)

    def test_the_held_out_checks_and_the_mutation_both_run_when_the_case_declares_both(self):
        spec = {"mutation": {"command": "python3 check.py"}, "acceptance": [checkers_block(None, ["red-moves-first", "legal-moves-alternate"])]}
        block = self.measure(spec=spec)
        self.assertTrue(block["acceptance"]["observed"] and block["mutation"]["observed"])
        self.assertEqual(block["acceptance"]["passed"], ["red-moves-first", "legal-moves-alternate"])
        self.assertEqual(block["held_out_seen"], 0, "the events name no held-out script")

    def test_an_error_inside_the_phase_still_reaps_the_copy_folder_and_propagates(self):
        with mock.patch.object(quality, "export_delivery", side_effect=RuntimeError("no git")), \
                mock.patch.object(listeners, "reap", return_value={"observed": True, "reaped": [], "survived": []}) as reap:
            with self.assertRaises(RuntimeError):
                self.measure()
        reap.assert_called_once_with(self.out / "quality")


@e2e.needs_lsof
@needs_quality
class QualityReapTest(e2e.RealListeners, unittest.TestCase):
    """The phase stops the listeners under <output>/quality, and only those: the real lsof and signals, scoped to the test's folder."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.scope_to_tmp()
        patch = no_syntax_check()
        patch.start()
        self.addCleanup(patch.stop)

    def test_a_server_a_test_run_leaves_under_the_copy_is_stopped_and_one_beside_the_delivery_is_not(self):
        out = self.tmp / "out"
        out.mkdir()
        work = out / "work"
        shutil.copytree(TINY, work)
        # check.py is replaced by a version that leaves one server running (its own session, as a model's `node server.js &`)
        # the first time it runs; every later run just reports.
        leak = ("import os, subprocess, sys\n"
                "if not os.path.exists('leaked'):\n"
                "    open('leaked', 'w').close()\n"
                "    portfile = os.path.join(os.getcwd(), 'port')\n"
                f"    subprocess.Popen([sys.executable, '-c', {e2e.LISTENER_SOURCE!r}, portfile], start_new_session=True,\n"
                "                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
                "    import time\n"
                "    while not os.path.exists(portfile): time.sleep(0.02)\n")
        (work / "check.py").write_text(leak + (TINY / "check.py").read_text())
        commit_delivery(work)
        beside, beside_port = self.serve(out / "beside")
        groups = RecordingGroups()
        block = quality.measure(out, work, {"mutation": {"command": "python3 check.py"}}, gate=None, hosts_used=["claude"],
                                groups=groups, stop=lambda: None)
        self.assertTrue(block["observed"], block)
        reaped = block["left_behind"]["reaped"]
        self.assertEqual(len(reaped), 1, block["left_behind"])
        self.assertTrue(reaped[0]["cwd"].startswith(os.path.realpath(out / "quality")), reaped)
        self.assertTrue(e2e.refuses_soon(int((out / "quality" / "copy" / "port").read_text().split()[1])))
        self.assertTrue(e2e.answers(beside_port), "a server under <output> but outside <output>/quality is not the phase's to stop")



# ---------------------------------------------------------------------------------------------------------------------
# Through run.main

EXTRA_PRODUCT = (
    "def extra_product():\n"
    "    import shutil\n"
    "    shutil.copytree(os.environ['FAKE_PRODUCT_SRC'], '.', dirs_exist_ok=True)\n")


def with_product(text: str) -> str:
    """A fake host of the main suite that also delivers the files of $FAKE_PRODUCT_SRC, committed with the rest."""
    marker = "def product():\n"
    assert text.count(marker) == 1, "the fake host's product writer changed shape: update this surgery"
    return text.replace(marker, EXTRA_PRODUCT + marker + "    extra_product()\n", 1)


def quality_cases() -> dict:
    return {
        "q-tiny": {"style": "web-service", "prompt": "Make the tiny product.", "checks": ["true"], "checks_source": "test",
                   "quality": {"mutation": {"command": "python3 check.py", "source": "test"}}},
        "q-none": {"style": "smoke", "prompt": "Say hello.", "checks": ["true"], "checks_source": "test"},
        "q-ref": {"style": "web-service", "prompt": "Serve the reference.", "checks": ["true"], "checks_source": "test",
                  "quality": {"acceptance": [checkers_block(None)]}},
    }


@needs_quality
class QualityThroughMainTest(e2e.CaseRunCase):
    """run.main with the fake hosts delivering a small committed product: the block, its order, its gate and its record."""

    def setUp(self):
        super().setUp()
        e2e.isolate_git(self)
        for name, path in self.fakes.items():
            path.write_text(with_product(path.read_text()))
        patched = mock.patch.dict(os.environ, {"FAKE_PRODUCT_SRC": str(TINY)})
        patched.start()
        self.addCleanup(patched.stop)
        self.cases = self.tmp / "cases.json"
        self.cases.write_text(json.dumps(quality_cases()))
        for patch in (mock.patch.object(run, "CASES", self.cases), no_syntax_check()):
            patch.start()
            self.addCleanup(patch.stop)

    def finished(self, case: str = "q-tiny", host: str = "claude", name: str | None = None, *extra: str):
        return self.case_main(name or f"{case}-{host}", "--case", case, *extra, host=host)

    def regrade(self, out: Path, *extra: str) -> tuple[int, dict, str]:
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), mock.patch.object(run, "review_export", return_value="review export: fake"):
            code = run.main([*extra, "--resume-run", str(out), "--grade-only", "--plugin-dir", str(self.plugin),
                             "--baseline", str(self.baselines)])
        return code, json.loads((out / "result.json").read_text()), printed.getvalue()

    def test_a_finished_delivery_is_measured_and_recorded_in_the_result_the_row_and_the_report(self):
        code, result, printed, out = self.finished()
        self.assertEqual(code, 0, result)
        block = result["quality"]
        self.assertTrue(block["observed"], block)
        self.assertEqual((block["declared"], block["hosts"], block["mixed_host"]), (["mutation"], ["claude"], False))
        self.assertEqual((block["mutation"]["operator_id"], block["mutation"]["sites"], block["mutation"]["ratio"]), ("js-1", 12, 0.4167))
        self.assertEqual(block["memory_writes"], [])
        self.assertTrue(result["pass"], "the verdicts are the same whatever the quality block holds")
        line = next(ln for ln in printed.splitlines() if ln.startswith("  quality"))
        self.assertIn("mutation 5 of 12 caught (ratio 0.4167, js-1, 3 files)", line)
        quality_row = self.last_row()["quality"]
        self.assertEqual(quality_row["mutation"], {"operator_id": "js-1", "sites": 12, "killed": 5, "survived": 7, "ratio": 0.4167,
                                                   "ceiling_hit": False})
        self.assertEqual((quality_row["hosts"], quality_row["mixed_host"], quality_row["observed"]), (["claude"], False, True))
        status = subprocess.run(["git", "-C", str(out / "work"), "status", "--porcelain"], capture_output=True, text=True).stdout
        self.assertEqual(status, "", "the delivered checkout is exactly as it was committed")
        self.assertTrue((out / "quality" / "copy" / "lib.js").is_file())

    def test_the_result_is_written_before_the_phase_and_again_with_the_block(self):
        seen = {}

        def spy(out, work, spec, **kw):
            seen["on_disk"] = json.loads((out / "result.json").read_text())
            seen.update(spec=spec, kw=kw, lock_alive=listeners.case_alive(out), stop_clear=kw["stop"]())
            (out / "stop").write_text("")
            seen["stop_asked"] = kw["stop"]()
            with mock.patch.object(run.TERMINATION, "is_set", return_value=True), mock.patch.object(run, "TERMINATED_BY", ["SIGTERM"]):
                seen["terminated"] = kw["stop"]()
            return {"observed": False, "reason": "spy", "declared": ["mutation"], "hosts": kw["hosts_used"], "mixed_host": False}

        with mock.patch.object(quality, "measure", side_effect=spy):
            code, result, printed, out = self.finished()
        self.assertNotIn("quality", seen["on_disk"], "the record that exists today is on disk before the phase starts")
        self.assertEqual(seen["on_disk"]["case"], "q-tiny")
        self.assertEqual(result["quality"]["reason"], "spy", "and result.json is written again with the block")
        self.assertEqual(seen["spec"], run.case_quality("q-tiny"))
        self.assertIsNone(seen["kw"]["gate"])
        self.assertIs(seen["kw"]["groups"], run.LIVE_HOST_GROUPS, "the phase's children end with the harness's signal handling")
        self.assertTrue(seen["lock_alive"], "the phase runs under the case lock the harness holds")
        self.assertIsNone(seen["stop_clear"])
        self.assertRegex(seen["stop_asked"], r"^stopped by .*q-tiny-claude/stop$")
        self.assertEqual(seen["terminated"], "terminated by SIGTERM")
        self.assertTrue((out / "stop").exists(), "a stop file after the host ended is left for the next resume to remove, as before")
        self.assertEqual(code, 0)

    def test_an_error_in_the_phase_is_recorded_and_changes_neither_the_verdict_nor_the_exit(self):
        with mock.patch.object(quality, "measure", side_effect=RuntimeError("boom")):
            code, result, printed, _ = self.finished()
        self.assertEqual(code, 0)
        self.assertTrue(result["pass"])
        self.assertEqual(result["quality"], {"observed": False, "hosts": ["claude"], "mixed_host": False,
                                             "reason": "the quality phase failed: RuntimeError('boom')"})
        self.assertIn("quality   not observed: the quality phase failed: RuntimeError('boom')", printed)

    def test_each_host_is_measured_the_same_way(self):
        ratios = {}
        for host in ("claude", "grok", "codex"):
            with self.subTest(host=host):
                code, result, _, _ = self.finished(host=host)
                self.assertEqual(code, 0, result)
                block = result["quality"]
                self.assertEqual((block["observed"], block["hosts"], block["mutation"]["ratio"]), (True, [host], 0.4167))
                ratios[host] = block["mutation"]["ratio"]
                if host != "claude":
                    self.assertIsNone(block["memory_writes"], "no Claude session: the detector reads nothing")
                    self.assertIn(host, block["unmeasured"]["memory_writes"])
        self.assertEqual(len(set(ratios.values())), 1)

    def test_a_run_that_returned_no_delivery_records_why_and_starts_nothing(self):
        code, result, printed, out = self.case_main("q-none-delivered", "--case", "q-tiny", mode="nothing")
        block = result["quality"]
        self.assertFalse(block["observed"])
        self.assertIn("ShipLoop did not reach done", block["reason"])
        self.assertNotIn("mutation", block)
        self.assertFalse((out / "quality").exists())
        self.assertEqual(self.last_row()["quality"]["observed"], False, "the row says the declared measure was not taken")

    def test_a_run_whose_engine_is_still_active_is_not_measured(self):
        code, result, _, out = self.case_main("q-active", "--case", "q-tiny", mode="active")
        self.assertFalse(result["quality"]["observed"])
        self.assertIn("ShipLoop is still active (stage test-refine)", result["quality"]["reason"])
        self.assertFalse((out / "quality").exists())

    def test_a_case_that_declares_nothing_and_a_custom_prompt_record_that_and_leave_the_row_alone(self):
        _code, result, _printed, out = self.finished("q-none")
        self.assertEqual(result["quality"]["declared"], [])
        self.assertIn("declares no quality measures", result["quality"]["reason"])
        self.assertNotIn("quality", self.last_row())
        _code, result, _printed, _out = self.case_main("q-custom", "--prompt", "say hello")
        self.assertIn("declares no quality measures", result["quality"]["reason"])
        self.assertNotIn("quality", self.last_row())
        self.assertFalse((out / "quality").exists())

    def test_held_out_acceptance_runs_in_the_harness_process_and_is_recorded_beside_the_mutation(self):
        _code, result, printed, _out = self.finished("q-ref")
        acceptance = result["quality"]["acceptance"]
        self.assertTrue(acceptance["observed"], acceptance)
        self.assertEqual(acceptance["passed"], CHECKERS_IDS)
        self.assertEqual(result["quality"]["held_out_seen"], 0, "the host's events name no held-out script: a measured none")
        self.assertIn("held-out 6 of 6 pass", printed)
        self.assertEqual(self.last_row()["quality"]["acceptance"], {"ids": 6, "passed": 6})
        events = (Path(result["output"]) / "events.jsonl").read_text()
        self.assertNotIn("checkers_accept", events)
        self.assertNotIn("checkers_accept", (Path(result["output"]) / "invocation.json").read_text())

    def test_a_regrade_measures_again_reproduces_the_memory_writes_from_the_events_and_names_both_hosts(self):
        _code, result, _printed, out = self.finished()
        self.assertEqual(result["quality"]["hosts"], ["claude"])
        (out / "quality" / "stale.txt").write_text("from the first phase")
        before = len((out / "events.jsonl").read_text().splitlines())
        with (out / "events.jsonl").open("a") as handle:
            handle.write(MEMORY_EVENTS.read_text())
        (out / "invocation-resume-grok-1791509021.json").write_text(json.dumps({"case": "q-tiny", "host": "grok", "versions": {}}))
        rows = self.baselines.read_text()
        code, regraded, _ = self.regrade(out)
        block = regraded["quality"]
        self.assertTrue(block["observed"], block)
        self.assertEqual((block["hosts"], block["mixed_host"]), (["claude", "grok"], True),
                         "the run's launch records name the hosts, not the flag of this invocation")
        self.assertEqual([(w["tool"], Path(w["path"]).name, w["line"]) for w in block["memory_writes"]],
                         [("Write", "feedback_no-broad-pkill.md", before + 2), ("Write", "MEMORY.md", before + 6)],
                         "computed from events.jsonl, so a regrade gives the same answer whatever the live profile holds")
        self.assertFalse((out / "quality" / "stale.txt").exists())
        self.assertEqual(self.baselines.read_text(), rows, "a regrade writes no baseline row")

    def test_a_regrade_while_another_harness_holds_the_case_takes_no_measure(self):
        _code, _result, _printed, out = self.finished()
        holder = listeners.hold_case(out)
        self.assertIsNotNone(holder)
        self.addCleanup(holder.close)
        code, regraded, _ = self.regrade(out)
        self.assertFalse(regraded["quality"]["observed"])
        self.assertIn("does not hold the case lock", regraded["quality"]["reason"])
        self.assertEqual(regraded["quality"]["memory_writes"], [], "the events are still read")

    def test_a_second_lock_in_one_process_fails_so_the_phase_must_reuse_the_one_it_holds(self):
        folder = self.tmp / "lock"
        folder.mkdir()
        first = listeners.hold_case(folder)
        self.addCleanup(first.close)
        self.assertIsNone(listeners.hold_case(folder), "flock is per open file description: a second acquire in this process fails")
        self.assertTrue(listeners.case_alive(folder))


@needs_quality
class QualityGateTest(unittest.TestCase):
    """run.quality_gate: every reason a delivery is not measured, in the order they are looked at."""

    def gate(self, **kw):
        args = dict(shiploop={"pass": True}, committed={"pass": True}, engine={"status": "done"}, process={"status": "exited"},
                    stop_seen=False, stop_file=Path("/nonexistent/stop"), lock_held=True)
        return run.quality_gate(**{**args, **kw})

    def test_a_finished_returned_delivery_under_the_held_lock_is_measured(self):
        self.assertIsNone(self.gate())

    def test_each_reason(self):
        table = [
            (dict(stop_seen=True), "a stop was requested"),
            (dict(process={"status": "stopped"}), "a stop was requested"),
            (dict(engine={"status": "active", "stage": "implement"}), "ShipLoop is still active (stage implement)"),
            (dict(shiploop={"pass": False, "status": "blocked"}), "ShipLoop did not reach done (blocked)"),
            (dict(shiploop={"pass": False, "reason": "no ShipLoop state.md"}), "ShipLoop did not reach done (no ShipLoop state.md)"),
            (dict(committed={"pass": False}), "not committed"),
            (dict(lock_held=False), "does not hold the case lock"),
        ]
        for change, wanted in table:
            with self.subTest(change=change):
                self.assertIn(wanted, self.gate(**change))

    def test_a_signal_to_the_harness_and_a_stop_file_are_stops(self):
        with mock.patch.object(run.TERMINATION, "is_set", return_value=True), mock.patch.object(run, "TERMINATED_BY", ["SIGHUP"]):
            self.assertIn("terminated by SIGHUP", self.gate())
        with tempfile.TemporaryDirectory() as folder:
            stop = Path(folder) / "stop"
            stop.write_text("")
            self.assertIn(f"stopped by {stop}", self.gate(stop_file=stop))

    def test_the_saved_records_of_round_3_are_gated_as_the_audit_read_them(self):
        # r3-battleship-grok-none: stopped by hand with the engine active and no tracked file (the audit's example of a run that
        # must not be measured); r3-checkers-sonnet: a finished delivery; r2-battleship-grok-none: a regrade whose host the
        # record does not observe and whose delivery is done and committed.
        records = json.loads((FIXTURES / "gate-records.json").read_text())
        gates = {name: self.gate(shiploop=rec["shiploop"], committed=rec["committed"], engine=rec["engine"], process=rec["process"])
                 for name, rec in records.items()}
        self.assertIn("a stop was requested", gates["r3-battleship-grok-none"])
        self.assertIsNone(gates["r3-checkers-sonnet"])
        self.assertIsNone(gates["r2-battleship-grok-none"])
        # the same record without the stop is still not a delivery: the engine is active
        rec = records["r3-battleship-grok-none"]
        self.assertIn("ShipLoop is still active (stage implement)",
                      self.gate(shiploop=rec["shiploop"], committed=rec["committed"], engine=rec["engine"], process={"status": "timeout"}))

    def test_a_stop_outranks_the_other_reasons(self):
        self.assertIn("a stop was requested", self.gate(stop_seen=True, engine={"status": "active"}, shiploop={"pass": False}))


@needs_quality
class CaseQualityTest(unittest.TestCase):
    """run.case_quality: the followed case's declarations first, as load_case orders checks; load_case itself is unchanged."""

    def cases(self, **cases) -> mock._patch:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / "cases.json"
        path.write_text(json.dumps(cases))
        return mock.patch.object(run, "CASES", path)

    def test_the_followed_cases_acceptance_comes_first_and_its_mutation_stands_unless_the_case_names_its_own(self):
        a, b = {"module": "m1", "start": "s", "checks": [{"id": "x"}]}, {"module": "m2", "start": "s", "checks": [{"id": "y"}]}
        with self.cases(base={"quality": {"mutation": {"command": "base"}, "acceptance": [a]}},
                        inherits={"follows": "base", "quality": {"acceptance": [b]}},
                        overrides={"follows": "base", "quality": {"mutation": {"command": "own"}}},
                        plain={}):
            self.assertEqual(run.case_quality("inherits"), {"mutation": {"command": "base"}, "acceptance": [a, b]})
            self.assertEqual(run.case_quality("overrides"), {"mutation": {"command": "own"}, "acceptance": [a]})
            self.assertEqual(run.case_quality("plain"), {})
            self.assertEqual(run.case_quality("missing"), {})

    def test_load_case_still_returns_its_four_values(self):
        args = run.parser().parse_args(["--case", "battleship-scoring"])
        name, prompt, checks, follows = run.load_case(args)
        self.assertEqual((name, follows), ("battleship-scoring", "battleship"))
        self.assertTrue(checks and prompt)


if __name__ == "__main__":
    unittest.main()
