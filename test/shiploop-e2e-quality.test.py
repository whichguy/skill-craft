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


if __name__ == "__main__":
    unittest.main()
