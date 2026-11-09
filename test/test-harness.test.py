#!/usr/bin/env python3
"""Hermetic checks for the test-harness skill: its own behaviour suite, the packaging contract and a narrow lint.

No network, no model. The bash self-test under skills/test-harness/scripts is the behaviour suite (discovery, scope,
supervision, side-effect classification, redaction, reports). This wrapper runs it in a scratch HOME and TMPDIR so that
nothing it does can land in the caller's home, and adds what that script cannot say about itself: the skill binds its
scripts from the loaded card, runs from any directory, ships no host-specific home directory, and leaves its own tree as
it found it.

The lint is narrow, not a privacy proof. It looks for the shapes of an email address, a home path, a host-specific home
directory used as a default and a few secret formats. Names of people, projects and accounts are not shapes: those need a
denylist kept outside the repository and a person reading the prose.
"""
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "test-harness"
SELF_TEST = SKILL / "scripts" / "test-harness-tests.sh"
JOURNAL = ROOT / "docs" / "test-harness-journal.md"
EVIDENCE = ROOT / "docs" / "evidence" / "test-harness-20261108"

# The self-test reports its own assertion count. A floor, not an exact number, so an added case does not break the
# suite, while an early exit that skips most of it cannot pass.
MINIMUM_ASSERTIONS = 270

SCRIPTS_RUN_BY_THE_CARD = (
    "run-harness.sh", "run-harness-hard-supervisor.py", "run-suite.sh", "discover-test-cmd.sh", "worktree-fixloop.sh",
    "porcelain-delta.py", "classify-side-effects.py", "emit-report.py", "init-run.py", "resolve-scope.py",
    "test-harness-tests.sh",
)

# name -> shape. A shape that matches inside a shipped file is a finding.
SHAPES = {
    "email address": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}"),
    "home path": re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+/"),
    "host home directory": re.compile(r"(?:~|\$HOME|\$\{HOME\}|Path\.home\(\)\s*/)\s*/?\s*[\"']?\.(?:grok|hermes|claude|codex|cursor|opencode)\b"),
    "secret shape": re.compile(
        r"\bsk-[A-Za-z0-9_-]{20,}|\bAKIA[0-9A-Z]{16}\b|\bghp_[A-Za-z0-9]{30,}|\bxox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    ),
}


def shipped_files():
    """Every file the skill ships, plus the journal and evidence that describe it."""
    paths = [p for p in SKILL.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    paths += [ROOT / "changes" / "test-harness" / name for name in ("initial.md",) if (ROOT / "changes" / "test-harness" / name).is_file()]
    if JOURNAL.is_file():
        paths.append(JOURNAL)
    if EVIDENCE.is_dir():
        paths += [p for p in EVIDENCE.rglob("*") if p.is_file()]
    return sorted(paths)


def scan(paths):
    """Return (findings, files_read, bytes_read). A scan that read nothing must never look clean."""
    findings, files_read, bytes_read = [], 0, 0
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        files_read += 1
        bytes_read += len(text.encode("utf-8"))
        for label, shape in SHAPES.items():
            for match in shape.finditer(text):
                findings.append((path, label, match.group(0)))
    return findings, files_read, bytes_read


def tree_state(root):
    """Every real file under root with its size. Bytecode caches are ignored: CI's own guard allows them, and another
    suite importing a module concurrently could create one between two reads."""
    return {p.relative_to(root).as_posix(): p.stat().st_size for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts}


class SelfTest(unittest.TestCase):
    def test_the_bundled_self_test_passes_in_a_scratch_home(self):
        before = tree_state(SKILL)
        with tempfile.TemporaryDirectory() as scratch:
            home, tmp = Path(scratch) / "home", Path(scratch) / "tmp"
            home.mkdir()
            tmp.mkdir()
            env = {k: v for k, v in os.environ.items() if not k.startswith("TEST_HARNESS_") and k != "XDG_STATE_HOME"}
            env.update(HOME=str(home), TMPDIR=str(tmp), PYTHONDONTWRITEBYTECODE="1", GIT_CONFIG_NOSYSTEM="1")
            run = subprocess.run(["bash", str(SELF_TEST)], env=env, capture_output=True, text=True, timeout=900, check=False)
            tail = (run.stdout + run.stderr)[-1500:]
            self.assertEqual(run.returncode, 0, tail)
            summary = re.search(r"^=== summary: PASS=(\d+) FAIL=(\d+) ===$", run.stdout, re.M)
            self.assertIsNotNone(summary, tail)
            self.assertEqual(summary.group(2), "0", tail)
            self.assertGreaterEqual(int(summary.group(1)), MINIMUM_ASSERTIONS, tail)
            self.assertEqual(list(home.iterdir()), [], "the self-test must not write under the caller's HOME")
        self.assertEqual(tree_state(SKILL), before, "the self-test must leave the skill's own tree as it found it")


class Packaging(unittest.TestCase):
    def card(self):
        return (SKILL / "SKILL.md").read_text(encoding="utf-8")

    def test_the_card_binds_the_scripts_from_the_loaded_skill(self):
        card = self.card()
        self.assertRegex(card, r'(?m)^SKILL_ROOT="/absolute/directory-containing-the-loaded-SKILL\.md"$')
        self.assertNotIn("SKILL_DIR", card, "the card's variable is SKILL_ROOT")
        self.assertIn("TEST_HARNESS_RUN_ROOT", card, "the write root is named apart from the package root")

    def test_every_script_and_reference_the_card_names_exists(self):
        docs = [SKILL / "SKILL.md"] + sorted((SKILL / "references").glob("*.md"))
        for doc in docs:
            text = doc.read_text(encoding="utf-8")
            for rel in set(re.findall(r"(?:(?<![\w/.-])|(?<=SKILL_ROOT/))((?:scripts|references)/[A-Za-z0-9_.-]+\.(?:sh|py|md))", text)):
                self.assertTrue((SKILL / rel).is_file(), f"{doc.name} names {rel}")

    def test_the_scripts_the_card_runs_are_executable(self):
        for name in SCRIPTS_RUN_BY_THE_CARD:
            self.assertTrue(os.access(SKILL / "scripts" / name, os.X_OK), name)

    def test_the_driver_runs_from_an_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as elsewhere:
            run = subprocess.run(["bash", str(SKILL / "scripts" / "run-harness.sh"), "--help"], cwd=elsewhere,
                                 capture_output=True, text=True, timeout=60, check=False)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("Usage: run-harness.sh", run.stdout)
            self.assertIn("fix-loop", run.stdout)

    def test_no_default_names_a_host_or_a_home_directory(self):
        for name in ("run-harness.sh", "run-harness-hard-supervisor.py"):
            text = (SKILL / "scripts" / name).read_text(encoding="utf-8")
            self.assertIn("XDG_STATE_HOME", text, f"{name} computes the default run root")
            self.assertNotRegex(text, r"\.(grok|hermes|claude|codex|cursor)\b", name)


class Hygiene(unittest.TestCase):
    """A narrow lint, proven on seeded leaks so that a clean result cannot mean the scan read nothing."""

    def test_the_lint_finds_each_seeded_shape(self):
        leaks = {
            "email address": "contact " + "someone" + "@" + "example" + ".org",
            "home path": "see " + "/Users/" + "alice" + "/notes.txt",
            "host home directory": 'ROOT="${ROOT:-$HOME/.' + 'grok/skills/x}"',
            "secret shape": "key = " + "sk-" + "A" * 24,
        }
        self.assertEqual(set(leaks), set(SHAPES), "every shape has a seeded leak")
        with tempfile.TemporaryDirectory() as scratch:
            paths = []
            for label, line in leaks.items():
                path = Path(scratch) / (label.replace(" ", "-") + ".txt")
                path.write_text(line + "\n", encoding="utf-8")
                paths.append(path)
            findings, files_read, bytes_read = scan(paths)
        self.assertEqual(files_read, len(leaks))
        self.assertGreater(bytes_read, 0)
        self.assertEqual({label for _path, label, _text in findings}, set(leaks))

    def test_the_lint_reads_every_shipped_file(self):
        paths = shipped_files()
        on_disk = [p for p in SKILL.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
        self.assertGreaterEqual(len(paths), len(on_disk), "the scan list covers the whole skill tree")
        self.assertGreaterEqual(len(on_disk), 20)
        findings, files_read, bytes_read = scan(paths)
        self.assertEqual(files_read, len(paths))
        self.assertGreater(bytes_read, 300_000, "the skill is about 380 KB; a scan that read far less read the wrong files")
        self.assertEqual(findings, [], "\n".join(f"{p.relative_to(ROOT)}: {label}: {text}" for p, label, text in findings[:20]))


if __name__ == "__main__":
    unittest.main()
