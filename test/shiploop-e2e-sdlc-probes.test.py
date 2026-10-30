#!/usr/bin/env python3
"""The SDLC probes (test/shiploop_e2e/probes/sdlc_probes.py; docs/shiploop-sdlc-gates-proposal-2026-10-30.md §4), no model.

One temporary output folder plays a finished seeded run. Its work repository has a start commit, then:
- W1/S1, which plants one case of each probe;
- W2/S1, which weakens W1's test;
- one commit made by hand.

Its metrics.json holds the counters and fidelity records P3 reads. Each probe must count its planted cases and nothing that
only looks like one: a docs mention, a test-file swallow, a JavaScript ``|| true``. The same folder, disposed down to its
delivery bundle, must give the same facts, and a folder with neither must report every probe unmeasured, never 0. The
reader must stay out of the grading digest.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "test" / "shiploop_e2e"
sys.path.insert(0, str(HARNESS / "probes"))
sys.path.insert(0, str(HARNESS))
import boundary  # noqa: E402
import delivery  # noqa: E402
import sdlc_probes  # noqa: E402

ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
# Built at run time, so this file never holds a credential-shaped literal for a secret scanner to flag.
FAKE_KEY = "AKIA" + "Q" * 16


def git(tree: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(tree), *args], check=True, capture_output=True, text=True, env=ENV).stdout


def write(tree: Path, files: dict[str, str]) -> None:
    for path, text in files.items():
        (tree / path).parent.mkdir(parents=True, exist_ok=True)
        (tree / path).write_text(text)


def commit(tree: Path, message: str) -> str:
    git(tree, "add", "-A")
    git(tree, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", message)
    return git(tree, "rev-parse", "HEAD").strip()


class Run(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="sdlc-probes-")
        cls.out = Path(cls.temp.name) / "out"
        work = cls.out / "work"
        work.mkdir(parents=True)
        git(work, "init", "-q")
        write(work, {"src/app.py": "def app():\n    return 1\n",
                     "package.json": json.dumps({"name": "x", "dependencies": {"left-pad": "1.0.0"}}),
                     "requirements.txt": "requests==2.32.0\n",
                     "README.md": "# x\n"})
        cls.start = commit(work, "start")
        write(work, {
            "src/game.py": ("import os  # noqa: F401\n\n\ndef game():\n    try:\n        return int('1')\n"
                            "    except ValueError: pass\n    try:\n        os.remove('x')\n    except OSError:\n"
                            "        pass\n    return 1\n"),
            "src/ui.js": "function run(x) {\n  try { x() } catch (e) {}\n  return x || true\n}\n",
            "scripts/build.sh": "#!/bin/sh\nmake build || true\n",
            "src/config.py": f"KEY = '{FAKE_KEY}'\n",
            "test/test_game.py": ("from src.game import game\n\n\ndef test_game():\n    assert game() == 1\n"
                                  "    try:\n        game()\n    except Exception: pass\n"),
            "README.md": "# x\n\nAvoid `# noqa` and `except: pass` in this project.\n",
            "package.json": json.dumps({"name": "x", "dependencies": {"left-pad": "1.0.0", "lodash": "4.17.21"}}),
            "requirements.txt": "requests==2.32.0\nflask>=3\n",
        })
        commit(work, "feat(W1/S1): game")
        write(work, {"test/test_game.py": ("from src.game import game\n\n\ndef test_game():\n    assert game()\n"
                                           "    try:\n        game()\n    except Exception: pass\n")})
        commit(work, "feat(W2/S1): later item")
        write(work, {"src/app.py": "def app():\n    return 2\n"})
        commit(work, "wip by hand")
        (cls.out / "invocation.json").write_text(json.dumps({"seeded": {"start_head": cls.start}}))
        (cls.out / "metrics.json").write_text(json.dumps({
            "commits": {"other": {"n": 1, "with_lessons": 0}},
            "fidelity": {"edits": {"model_commits": [{"event": 41, "tool": "Bash"}],
                                   "script_owned": [{"event": 57, "tool": "Bash"}, {"event": 58, "tool": "Bash"}]}}}))
        cls.found = sdlc_probes.probe(cls.out)
        # The same run after `lifecycle.py dispose`: no work folder, only the delivery bundle.
        cls.disposed = Path(cls.temp.name) / "disposed"
        (cls.disposed / delivery.BUNDLE).parent.mkdir(parents=True)
        git(work, "bundle", "create", "-q", str(cls.disposed / delivery.BUNDLE), "--all")
        shutil.copy(cls.out / "invocation.json", cls.disposed / "invocation.json")
        cls.from_bundle = sdlc_probes.probe(cls.disposed)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def facts(self, name: str, found: dict | None = None) -> list[dict]:
        value = (found or self.found)["probes"][name]
        self.assertIsNotNone(value, (found or self.found)["unmeasured"].get(name))
        self.assertEqual(value["n"], len(value["facts"]))
        return value["facts"]

    def test_p1_counts_the_code_suppression_and_not_the_readme_mention(self):
        self.assertEqual([(f["path"], f["kind"]) for f in self.facts("suppressions")], [("src/game.py", "noqa")])

    def test_p2_names_the_later_item_that_weakened_the_earlier_items_test(self):
        [fact] = self.facts("earlier_test_edits")
        self.assertEqual((fact["path"], fact["created_by"], fact["changed_by"]), ("test/test_game.py", "W1/S1", "W2/S1"))
        self.assertEqual((fact["assertions_removed"], fact["assertions_added"]), (1, 1))

    def test_p3_is_read_from_the_runs_own_counters_and_fidelity_records(self):
        self.assertEqual(self.found["probes"]["model_commits"],
                         {"commits_other": 1, "model_commits": 1, "script_owned_edits": 2})
        self.assertIsNone(self.from_bundle["probes"]["model_commits"])
        self.assertIn("metrics.json", self.from_bundle["unmeasured"]["model_commits"])

    def test_p4_is_listed_as_not_built_never_as_zero(self):
        self.assertIsNone(self.found["probes"]["earlier_ids_in_regressions"])
        self.assertIn("not built", self.found["unmeasured"]["earlier_ids_in_regressions"])

    def test_p5_lists_the_dependencies_each_manifest_gained(self):
        self.assertEqual(sorted((f["manifest"], f["name"]) for f in self.facts("new_dependencies")),
                         [("package.json", "lodash"), ("requirements.txt", "flask")])

    def test_p6_reports_the_credential_format_and_never_its_value(self):
        self.assertEqual([(f["path"], f["format"]) for f in self.facts("secret_like")], [("src/config.py", "aws-access-key")])
        self.assertNotIn(FAKE_KEY, json.dumps(self.found))

    def test_p7_counts_product_code_swallows_only(self):
        kinds = sorted((f["path"], f["kind"]) for f in self.facts("swallowed_errors"))
        self.assertEqual(kinds, [("scripts/build.sh", "or-true"), ("src/game.py", "except-pass"),
                                 ("src/game.py", "except-pass"), ("src/ui.js", "empty-catch")])

    def test_a_disposed_run_gives_the_same_facts_from_its_delivery_bundle(self):
        for name in ("suppressions", "earlier_test_edits", "new_dependencies", "secret_like", "swallowed_errors"):
            with self.subTest(probe=name):
                self.assertEqual(self.facts(name, self.from_bundle), self.facts(name))

    def test_a_run_that_kept_neither_repository_reports_every_probe_unmeasured_never_zero(self):
        empty = Path(self.temp.name) / "empty"
        empty.mkdir()
        nothing = sdlc_probes.probe(empty)
        self.assertTrue(all(value is None for value in nothing["probes"].values()))
        self.assertEqual(set(nothing["unmeasured"]), set(nothing["probes"]))

    def test_the_reader_is_outside_the_evaluator_digest_and_the_qualification_snapshot(self):
        self.assertNotIn(HARNESS / "probes" / "sdlc_probes.py", boundary.evaluator_files(HARNESS))
        self.assertFalse(any(path.parent.name == "probes" for path in boundary.evaluator_files(HARNESS)))


class AddedLines(unittest.TestCase):
    def test_new_line_numbers_follow_each_hunk(self):
        diff = ("diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1,2 +1,3 @@\n x = 1\n+y = 2\n z = 3\n"
                "@@ -10 +11,2 @@\n-old\n+new\n+newer\n")
        self.assertEqual(sdlc_probes.added_lines(diff), [("a.py", 2, "y = 2"), ("a.py", 11, "new"), ("a.py", 12, "newer")])

    def test_a_deleted_file_adds_nothing(self):
        self.assertEqual(sdlc_probes.added_lines("--- a/a.py\n+++ /dev/null\n@@ -1 +0,0 @@\n-x\n"), [])


if __name__ == "__main__":
    unittest.main()
