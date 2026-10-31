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
from unittest import mock

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


class Dependencies(unittest.TestCase):
    """P5 on small runs: an Apps Script project declares dependencies in appsscript.json, and a repository with no manifest
    this reader can parse is unmeasured, never a measured zero (2026-10-31: the first P5 read only four manifest names)."""

    def run_folder(self, start_files: dict[str, str], run_files: dict[str, str]) -> Path:
        temp = tempfile.TemporaryDirectory(prefix="sdlc-deps-")
        self.addCleanup(temp.cleanup)
        out = Path(temp.name) / "out"
        work = out / "work"
        work.mkdir(parents=True)
        git(work, "init", "-q")
        write(work, start_files)
        start = commit(work, "start")
        write(work, run_files)
        commit(work, "feat(W1/S1): change")
        (out / "invocation.json").write_text(json.dumps({"seeded": {"start_head": start}}))
        return out

    def found(self, out: Path) -> dict:
        return sdlc_probes.probe(out, ROOT)

    def test_an_apps_script_run_that_gains_a_library_and_an_advanced_service_reports_both(self):
        before = {"timeZone": "UTC", "dependencies": {}}
        after = {"timeZone": "UTC", "dependencies": {
            "libraries": [{"userSymbol": "Lib", "libraryId": "1abcLIB", "version": "3"}],
            "enabledAdvancedServices": [{"userSymbol": "Sheets", "serviceId": "sheets", "version": "v4"}]}}
        out = self.run_folder({"appsscript.json": json.dumps(before), "Code.gs": "function a() {}\n"},
                              {"appsscript.json": json.dumps(after)})
        facts = self.found(out)["probes"]["new_dependencies"]["facts"]
        self.assertEqual(sorted((f["manifest"], f["name"]) for f in facts),
                         [("appsscript.json", "library:1abcLIB"), ("appsscript.json", "service:sheets")])

    def test_an_apps_script_manifest_that_did_not_change_is_a_measured_none(self):
        manifest = json.dumps({"timeZone": "UTC", "dependencies": {"libraries": [{"libraryId": "1abcLIB"}]}})
        out = self.run_folder({"appsscript.json": manifest, "Code.gs": "function a() {}\n"},
                              {"Code.gs": "function a() { return 1; }\n"})
        found = self.found(out)
        self.assertEqual(found["probes"]["new_dependencies"], {"n": 0, "facts": []})
        self.assertNotIn("new_dependencies", found["unmeasured"])

    def test_a_repository_with_no_supported_manifest_is_unmeasured_never_none(self):
        out = self.run_folder({"Code.gs": "function a() {}\n"}, {"Code.gs": "function a() { return 1; }\n"})
        found = self.found(out)
        self.assertIsNone(found["probes"]["new_dependencies"])
        self.assertIn("no supported manifest", found["unmeasured"]["new_dependencies"])
        self.assertIn("appsscript.json", found["unmeasured"]["new_dependencies"])

    def test_a_manifest_the_run_added_counts_as_a_supported_manifest(self):
        out = self.run_folder({"README.md": "# x\n"},
                              {"package.json": json.dumps({"dependencies": {"lodash": "4.17.21"}})})
        facts = self.found(out)["probes"]["new_dependencies"]["facts"]
        self.assertEqual([(f["manifest"], f["name"]) for f in facts], [("package.json", "lodash")])


class Unmeasured(unittest.TestCase):
    """A probe that cannot measure says so. Independent review, 2026-10-31: a git failure, a malformed manifest and a run with
    no step commits each read as a measured zero, and a non-UTF-8 file stopped the reader."""

    def run_folder(self, start_files: dict, commits: list) -> Path:
        temp = tempfile.TemporaryDirectory(prefix="sdlc-unmeasured-")
        self.addCleanup(temp.cleanup)
        out = Path(temp.name) / "out"
        work = out / "work"
        work.mkdir(parents=True)
        git(work, "init", "-q")
        write(work, start_files)
        start = commit(work, "start")
        for message, files in commits:
            for path, content in files.items():
                (work / path).parent.mkdir(parents=True, exist_ok=True)
                (work / path).write_bytes(content if isinstance(content, bytes) else content.encode())
            commit(work, message)
        (out / "invocation.json").write_text(json.dumps({"seeded": {"start_head": start}}))
        return out

    def found(self, out: Path) -> dict:
        return sdlc_probes.probe(out, ROOT)

    def test_a_failed_git_command_raises_and_leaves_every_git_probe_unmeasured(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(sdlc_probes.GitError):
            sdlc_probes.git(Path(tmp), "log")  # not a repository
        out = self.run_folder({"a.py": "x = 1\n"}, [("feat(W1/S1): c", {"a.py": "x = 2  # noqa\n"})])
        broken = sdlc_probes.GitError("git diff failed (exit 128): fatal: detected dubious ownership")
        with mock.patch.object(sdlc_probes, "git", side_effect=broken):
            found = self.found(out)
        for name in ("suppressions", "earlier_test_edits", "new_dependencies", "secret_like", "swallowed_errors"):
            with self.subTest(probe=name):
                self.assertIsNone(found["probes"][name])
                self.assertIn("GitError", found["unmeasured"][name])

    def test_a_non_utf8_file_in_the_diff_does_not_stop_the_reader(self):
        out = self.run_folder({"a.py": "x = 1\n"}, [("feat(W1/S1): c", {"a.py": "x = 2  # noqa\n", "data.txt": b"caf\xe9\n"})])
        found = self.found(out)
        self.assertEqual(found["probes"]["suppressions"]["n"], 1)
        self.assertNotIn("suppressions", found["unmeasured"])

    def test_a_non_ascii_path_is_reported_by_its_own_name(self):
        out = self.run_folder({"a.py": "x = 1\n"}, [("feat(W1/S1): c", {"caf\u00e9.js": "f(); // eslint-disable-line\n"})])
        self.assertEqual([f["path"] for f in self.found(out)["probes"]["suppressions"]["facts"]], ["caf\u00e9.js"])

    def test_p2_is_unmeasured_when_no_commit_names_its_step(self):
        out = self.run_folder({"README.md": "# x\n"}, [("add tests", {"test/test_a.py": "def test_a():\n    assert 1\n"}),
                                                      ("relax tests", {"test/test_a.py": "def test_a():\n    pass\n"})])
        found = self.found(out)
        self.assertIsNone(found["probes"]["earlier_test_edits"])
        self.assertIn("feat(item/step)", found["unmeasured"]["earlier_test_edits"])

    def test_p2_does_not_report_a_step_that_edits_its_own_test(self):
        out = self.run_folder({"README.md": "# x\n"}, [("feat(W1/S1): tests", {"test/test_a.py": "def test_a():\n    assert 1\n"}),
                                                      ("feat(W1/S1): again", {"test/test_a.py": "def test_a():\n    pass\n"})])
        self.assertEqual(self.found(out)["probes"]["earlier_test_edits"], {"n": 0, "facts": []})

    def test_p5_is_unmeasured_when_a_manifest_does_not_parse(self):
        good = json.dumps({"dependencies": {"a": "1"}})
        for label, start, after in (("at HEAD", good, "{not json"), ("at the start", "{not json", good)):
            with self.subTest(invalid=label):
                found = self.found(self.run_folder({"package.json": start}, [("feat(W1/S1): c", {"package.json": after})]))
                self.assertIsNone(found["probes"]["new_dependencies"])
                self.assertIn("package.json does not parse", found["unmeasured"]["new_dependencies"])

    @unittest.skipUnless(sys.version_info >= (3, 11), "pyproject.toml is read with tomllib (3.11+)")
    def test_p5_reads_dependency_groups_and_poetry_groups(self):
        before = '[project]\nname = "x"\ndependencies = ["requests>=2"]\n'
        after = (before + '\n[dependency-groups]\ndev = ["pytest>=8", {include-group = "lint"}]\n\n'
                 '[tool.poetry.group.docs.dependencies]\nsphinx = "^7"\n')
        found = self.found(self.run_folder({"pyproject.toml": before}, [("feat(W1/S1): c", {"pyproject.toml": after})]))
        self.assertEqual(sorted(f["name"] for f in found["probes"]["new_dependencies"]["facts"]), ["pytest", "sphinx"])

    def test_p5_does_not_take_a_url_requirement_for_a_package_named_git(self):
        after = "requests==2\ngit+https://example.invalid/x/y.git#egg=y\nflask>=3\n"
        found = self.found(self.run_folder({"requirements.txt": "requests==2\n"}, [("feat(W1/S1): c", {"requirements.txt": after})]))
        self.assertEqual([f["name"] for f in found["probes"]["new_dependencies"]["facts"]], ["flask"])

    def test_p5_lists_a_changed_manifest_it_does_not_parse_as_unread_never_as_no_change(self):
        out = self.run_folder({"package.json": json.dumps({"dependencies": {}}), "Cargo.toml": "[dependencies]\n"},
                              [("feat(W1/S1): c", {"Cargo.toml": '[dependencies]\nserde = "1"\n'})])
        self.assertEqual(self.found(out)["probes"]["new_dependencies"]["facts"],
                         [{"manifest": "Cargo.toml", "name": None, "unread": "a manifest this reader does not parse"}])

    def test_p6_counts_a_line_once_when_two_formats_match_and_never_returns_the_value(self):
        key = "sk-" + "ant-" + "a" * 40  # built at run time; both the anthropic and the openai pattern match it
        found = self.found(self.run_folder({"a.py": "x = 1\n"}, [("feat(W1/S1): c", {"config.py": f"K = '{key}'\n"})]))
        self.assertEqual([f["format"] for f in found["probes"]["secret_like"]["facts"]], ["anthropic-key"])
        self.assertNotIn(key, json.dumps(found))


class AddedLines(unittest.TestCase):
    def test_new_line_numbers_follow_each_hunk(self):
        diff = ("diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1,2 +1,3 @@\n x = 1\n+y = 2\n z = 3\n"
                "@@ -10 +11,2 @@\n-old\n+new\n+newer\n")
        self.assertEqual(sdlc_probes.added_lines(diff), [("a.py", 2, "y = 2"), ("a.py", 11, "new"), ("a.py", 12, "newer")])

    def test_a_deleted_file_adds_nothing(self):
        self.assertEqual(sdlc_probes.added_lines("--- a/a.py\n+++ /dev/null\n@@ -1 +0,0 @@\n-x\n"), [])


    def test_a_line_that_starts_with_plus_signs_is_an_added_line_not_a_file_header(self):
        diff = ("--- a/a.js\n+++ b/a.js\n@@ -1 +1,2 @@\n-old\n+++n; // eslint-disable-line no-plusplus\n+++ x\n")
        self.assertEqual(sdlc_probes.added_lines(diff),
                         [("a.js", 1, "++n; // eslint-disable-line no-plusplus"), ("a.js", 2, "++ x")])

    def test_the_no_newline_marker_is_not_a_line(self):
        diff = ("--- a/a.js\n+++ b/a.js\n@@ -1,2 +1,2 @@\n-a\n\\ No newline at end of file\n+b\n"
                "\\ No newline at end of file\n c\n")
        self.assertEqual(sdlc_probes.added_lines(diff), [("a.js", 1, "b")])

    def test_a_quoted_header_path_is_unquoted(self):
        self.assertEqual(sdlc_probes.added_lines('--- a/x\n+++ "b/we ird.js"\n@@ -0,0 +1 @@\n+x\n'), [("we ird.js", 1, "x")])


if __name__ == "__main__":
    unittest.main()
