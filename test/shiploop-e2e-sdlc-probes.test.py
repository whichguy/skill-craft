#!/usr/bin/env python3
"""The SDLC probes (test/shiploop_e2e/sdlc_probes.py; docs/shiploop-sdlc-gates-proposal-2026-10-30.md §4), no model.

One temporary repository plays a finished run. Its start commit is followed by:
- W1/S1, which plants one case of each probe;
- W2/S1, which weakens W1's test;
- one commit made by hand.

Each probe must count its planted cases and nothing that only looks like one: a docs mention, a test-file swallow, a
JavaScript ``|| true``.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
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
        cls.tree = Path(cls.temp.name) / "worktree"
        cls.run_dir = Path(cls.temp.name) / "run"
        cls.tree.mkdir()
        git(cls.tree, "init", "-q")
        write(cls.tree, {"src/app.py": "def app():\n    return 1\n",
                         "package.json": json.dumps({"name": "x", "dependencies": {"left-pad": "1.0.0"}}),
                         "requirements.txt": "requests==2.32.0\n",
                         "README.md": "# x\n"})
        cls.start = commit(cls.tree, "start")
        write(cls.tree, {
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
        cls.w1 = commit(cls.tree, "feat(W1/S1): game")
        write(cls.tree, {"test/test_game.py": ("from src.game import game\n\n\ndef test_game():\n    assert game()\n"
                                               "    try:\n        game()\n    except Exception: pass\n")})
        cls.w2 = commit(cls.tree, "feat(W2/S1): later item")
        write(cls.tree, {"src/app.py": "def app():\n    return 2\n"})
        cls.hand = commit(cls.tree, "wip by hand")
        cls.run_dir.mkdir()
        (cls.run_dir / "commits").mkdir()
        (cls.run_dir / "commits" / "nav-w1.txt").write_text(cls.w1 + "\n")
        (cls.run_dir / "commits" / "nav-w2.txt").write_text(cls.w2 + "\n")
        cls.found = sdlc_probes.probe(cls.tree, cls.start, cls.run_dir, ROOT)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def rows(self, name: str) -> list[dict]:
        self.assertTrue(self.found[name]["kept"], name)
        self.assertEqual(self.found[name]["count"], len(self.found[name]["rows"]))
        return self.found[name]["rows"]

    def test_p1_counts_the_code_suppression_and_not_the_readme_mention(self):
        self.assertEqual([(r["path"], r["kind"]) for r in self.rows("suppressions")], [("src/game.py", "noqa")])

    def test_p2_names_the_later_item_that_weakened_the_earlier_items_test(self):
        [row] = self.rows("earlier_test_edits")
        self.assertEqual((row["path"], row["created_by"], row["changed_by"]), ("test/test_game.py", "W1/S1", "W2/S1"))
        self.assertEqual((row["assertions_removed"], row["assertions_added"]), (1, 1))

    def test_p3_finds_the_one_commit_no_record_names(self):
        self.assertEqual([r["commit"] for r in self.rows("foreign_commits")], [self.hand[:12]])

    def test_p5_lists_the_dependencies_each_manifest_gained(self):
        self.assertEqual(sorted((r["manifest"], r["name"]) for r in self.rows("new_dependencies")),
                         [("package.json", "lodash"), ("requirements.txt", "flask")])

    def test_p6_reports_the_credential_format_and_never_its_value(self):
        self.assertEqual([(r["path"], r["format"]) for r in self.rows("secret_like")], [("src/config.py", "aws-access-key")])
        self.assertNotIn(FAKE_KEY, json.dumps(self.found))

    def test_p7_counts_product_code_swallows_only(self):
        kinds = sorted((r["path"], r["kind"]) for r in self.rows("swallowed_errors"))
        self.assertEqual(kinds, [("scripts/build.sh", "or-true"), ("src/game.py", "except-pass"),
                                 ("src/game.py", "except-pass"), ("src/ui.js", "empty-catch")])

    def test_a_run_whose_history_was_not_kept_reports_not_kept_never_zero(self):
        missing = sdlc_probes.probe(Path(self.temp.name) / "gone", self.start, None, ROOT)
        self.assertTrue(missing and all(value == {"kept": False} for value in missing.values()))
        self.assertEqual(sdlc_probes.probe(self.tree, self.start, None, ROOT)["foreign_commits"], {"kept": False})


class AddedLines(unittest.TestCase):
    def test_new_line_numbers_follow_each_hunk(self):
        diff = ("diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1,2 +1,3 @@\n x = 1\n+y = 2\n z = 3\n"
                "@@ -10 +11,2 @@\n-old\n+new\n+newer\n")
        self.assertEqual(sdlc_probes.added_lines(diff), [("a.py", 2, "y = 2"), ("a.py", 11, "new"), ("a.py", 12, "newer")])

    def test_a_deleted_file_adds_nothing(self):
        self.assertEqual(sdlc_probes.added_lines("--- a/a.py\n+++ /dev/null\n@@ -1 +0,0 @@\n-x\n"), [])


if __name__ == "__main__":
    unittest.main()
