#!/usr/bin/env python3
"""Hermetic tests for ShipLoop's script-owned advisory lint (phase 1).

Stub ``ruff`` and ``shellcheck`` executables on a temporary PATH stand in for
real tools, so these tests never depend on what the host has installed.
"""
from __future__ import annotations

import atexit
import contextlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills/shiploop"
CLI = PACKAGE / "scripts/shiploop"
sys.path.insert(0, str(PACKAGE / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import shiploop_knowledge_support as knowledge_support  # noqa: E402
import shiploop_lint as lint  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_store as store  # noqa: E402

CORE = types.SimpleNamespace(PACKAGE_ROOT=PACKAGE, REF_DIR=PACKAGE / "references")
DONE = {"outcome": "done", "summary": "Synthetic declaration; no work executed."}


def _system_path() -> str:
    """A PATH directory with only the utilities the fixtures need.

    Host directories such as /usr/bin can carry a packaged ruff or shellcheck,
    so tests that expect a tool to be absent never search them.
    """
    directory = Path(tempfile.mkdtemp(prefix="shiploop-lint-sys-"))
    atexit.register(shutil.rmtree, str(directory), True)
    for name in ("git", "sleep"):
        found = shutil.which(name)
        if found:
            (directory / name).symlink_to(found)
    return str(directory)


SYSTEM_PATH = _system_path()

STUB = r'''
import json, os, re, subprocess, sys, time
argv = sys.argv[1:]
name = os.path.basename(sys.argv[0])
if os.environ.get("STUB_LOG"):
    with open(os.environ["STUB_LOG"], "a") as log:
        log.write(json.dumps([name] + argv) + "\n")
if "--version" in argv:
    print("ruff 0.0.1-stub" if name == "ruff" else "ShellCheck stub\nversion: 0.0.1")
    sys.exit(0)

def cfg():
    text = ""
    for candidate in ("pyproject.toml", "ruff.toml"):
        if os.path.exists(candidate):
            text += open(candidate).read()
    return text

def findings(text, path, unfixable, unsafe):
    out = []
    for number, line in enumerate(text.splitlines(), 1):
        if "def (:" in line:
            out.append((number, "E999", False, "SyntaxError: stub"))
        if "--select" in argv and argv[argv.index("--select") + 1] == "E9":
            continue
        if line.startswith("import ") and "# unused" in line:
            out.append((number, "F401", "F401" not in unfixable, "`x` imported but unused"))
        if line.rstrip().endswith("# fixme"):
            out.append((number, "X100", True, "fixme marker"))
        if "# unsafe" in line:
            out.append((number, "X200", unsafe, "unsafe marker"))
        if "# lint" in line:
            out.append((number, "E101", False, "synthetic finding"))
    return out

def fix(text, unfixable, unsafe):
    lines = []
    for line in text.splitlines(keepends=True):
        if line.startswith("import ") and "# unused" in line and "F401" not in unfixable:
            continue
        if line.rstrip().endswith("# fixme"):
            ending = "\n" if line.endswith("\n") else ""
            core = line.rstrip()[: -len("# fixme")].rstrip()
            line = ("def (:" if "# breaks" in core else core) + ending
        if unsafe and "# unsafe" in line:
            line = line.replace(" # unsafe", "")
        lines.append(line)
    return "".join(lines)

if name == "shellcheck":
    paths = argv[argv.index("--") + 1:] if "--" in argv else ["-"]
    total = 0
    for path in paths:
        text = sys.stdin.read() if path == "-" else open(path).read()
        for number, line in enumerate(text.splitlines(), 1):
            if re.search(r"\bcd ", line) and "||" not in line:
                print(f"{path}:{number}:1: warning: Use cd || exit [SC2164]")
                total += 1
    sys.exit(1 if total else 0)

config = cfg()
unfixable = set(re.findall(r"F\d+", " ".join(a for a in argv if "unfixable" in a)))
promoted = re.findall(r'"(X\d+)"', "".join(re.findall(r"extend-safe-fixes\s*=\s*\[[^\]]*\]", config)))
unsafe = ("--unsafe-fixes" in argv or ("unsafe-fixes = true" in config and "--no-unsafe-fixes" not in argv)
          or "X200" in promoted)
if "--show-settings" in argv:
    print("Resolved settings for: stub")
    if promoted:
        print("linter.safety_table.forced_safe = [")
        for code in promoted:
            print("\tstub-rule (" + code + "),")
        print("]")
    else:
        print("linter.safety_table.forced_safe = []")
    sys.exit(0)
if "--show-files" in argv:
    excluded = set(filter(None, os.environ.get("STUB_EXCLUDE", "").split(",")))
    for path in argv[argv.index("--") + 1:]:
        if path not in excluded:
            print(os.path.abspath(path))
    sys.exit(0)
if argv[-1] == "-":
    path = argv[argv.index("--stdin-filename") + 1]
    text = sys.stdin.read()
    if "--fix" in argv:
        if os.environ.get("STUB_CREATE"):
            os.makedirs(".ruff_cache", exist_ok=True)
            open(".ruff_cache/x", "w").write("cache")
            open("stray.txt", "w").write("stray")
        if os.environ.get("STUB_TOUCH"):
            with open(os.environ["STUB_TOUCH"], "a") as target:
                target.write("# touched\n")
        if os.environ.get("STUB_FIX_SLEEP"):
            subprocess.Popen(["sleep", os.environ["STUB_FIX_SLEEP"]])
            time.sleep(float(os.environ["STUB_FIX_SLEEP"]))
        if os.environ.get("STUB_FIX_EXIT"):
            print("stub fixer failure: boom", file=sys.stderr)
            sys.exit(int(os.environ["STUB_FIX_EXIT"]))
        fixed = fix(text, unfixable, unsafe)
        sys.stdout.write(fixed)
        remaining = findings(fixed, path, unfixable, unsafe)
        for number, code, _fixable, message in remaining:
            print(f"{path}:{number}:1: {code} {message}", file=sys.stderr)
        sys.exit(1 if remaining else 0)
    found = findings(text, path, unfixable, unsafe)
    for number, code, fixable, message in found:
        print(f"{path}:{number}:1: {code}{' [*]' if fixable else ''} {message}")
    sys.exit(1 if found else 0)
paths = argv[argv.index("--") + 1:]
total = 0
for path in paths:
    text = open(path).read()
    if "fix = true" in config and "--no-fix" not in argv:
        open(path, "w").write(fix(text, unfixable, unsafe))
    for number, code, fixable, message in findings(text, path, unfixable, unsafe):
        print(f"{path}:{number}:1: {code}{' [*]' if fixable else ''} {message}")
        total += 1
print(f"Found {total} errors.")
sys.exit(1 if total else 0)
'''


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True).stdout


NODE_STUB = r'''
import json, os, sys
with open(os.environ["STUB_LOG"], "a") as log:
    log.write(json.dumps(["node"] + sys.argv[1:]) + "\n")
if any(arg.startswith("--require") for arg in sys.argv[1:]):
    open(os.environ["STUB_LOG"] + ".preloaded", "w").write("preloaded")
sys.exit(0)
'''


def write_stub(directory: Path, name: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text("#!" + sys.executable + "\n" + STUB)
    path.chmod(0o755)
    return path


DISCOVERED_STUB = r"""
import json, os, sys
argv = sys.argv[1:]
name = os.path.basename(sys.argv[0])
with open(os.environ["STUB_LOG"], "a") as log:
    log.write(json.dumps([name] + argv + ["cwd=" + os.getcwd()]) + "\n")
if name == "eslint":
    files = [arg for arg in argv if arg.startswith("./")]
    out = []
    for path in files:
        messages = [{"line": number, "column": 1, "ruleId": "stub/rule", "severity": 2, "message": "stub finding"}
                    for number, line in enumerate(open(path).read().splitlines(), 1) if "LINTME" in line]
        out.append({"filePath": os.path.abspath(path), "messages": messages})
    print(json.dumps(out))
    sys.exit(1 if any(entry["messages"] for entry in out) else 0)
if name == "prettier":
    text = sys.stdin.read()
    sys.stdout.write("".join(line.rstrip() + "\n" for line in text.splitlines()))
    sys.exit(0)
if name == "tsc":
    found = False
    for root, _dirs, names in os.walk("."):
        for file in names:
            if file.endswith(".ts"):
                path = os.path.normpath(os.path.join(root, file))
                for number, line in enumerate(open(path).read().splitlines(), 1):
                    if "TSBAD" in line:
                        print(path + "(" + str(number) + ",5): error TS2322: stub type error")
                        found = True
    sys.exit(2 if found else 0)
if name == "actionlint":
    for path in [arg for arg in argv if not arg.startswith("-")]:
        for number, line in enumerate(open(path).read().splitlines(), 1):
            if "BAD" in line:
                print(path + ":" + str(number) + ":1: stub workflow finding [syntax-check]")
    sys.exit(0)
if name == "npm":
    for number, line in enumerate(open("notes.txt").read().splitlines(), 1):
        if "BAD" in line:
            print("notes.txt:" + str(number) + ":1 stub project finding")
    sys.exit(1)
sys.exit(0)
"""


def write_tool(directory: Path, name: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text("#!" + sys.executable + "\n" + DISCOVERED_STUB)
    path.chmod(0o755)
    return path


class Fixture(unittest.TestCase):
    """A committed Git repository, a run directory and a stub tool directory."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-lint-")
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name).resolve()
        self.repo = base / "repo"
        self.run_dir = base / "run"
        self.bin = base / "bin"
        self.repo.mkdir()
        self.run_dir.mkdir()
        self.log = base / "stub.log"
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "lint@example.invalid")
        git(self.repo, "config", "user.name", "Lint Test")
        write_stub(self.bin, "ruff")
        write_stub(self.bin, "shellcheck")

    def commit(self, files: dict) -> None:
        for name, text in files.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base", "--allow-empty")

    def base(self) -> dict:
        writes = lint.capture_base(self.run_dir, self.repo, "W1")
        for relative, text in writes.items():
            target = self.run_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        return lint.read_base(self.run_dir, "W1")

    def edit(self, files: dict) -> None:
        for name, text in files.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

    def env(self, path: str = "", **extra: str) -> dict:
        env = {"PATH": (path or str(self.bin)) + ":" + SYSTEM_PATH, "STUB_LOG": str(self.log)}
        env.update(extra)
        return env

    def run_pass(self, *, base: object = "capture", mode: str = "fix", allow_fix: bool = True,
                 env: dict | None = None, **kwargs):
        if base == "capture":
            base = lint.read_base(self.run_dir, "W1")
        return lint.lint_pass(self.repo, self.run_dir, action="A1", work_item="W1", stage="static-checks",
                              mode=mode, run_option=mode, base=base, allow_fix=allow_fix,
                              env=env or self.env(), **kwargs)

    def logged(self) -> list:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]


class LintPassTests(Fixture):
    def test_snapshot_skips_an_ignored_run_directory_inside_the_checkout(self):
        """A literal exclude naming an ignored path makes ``add -A`` fail; the snapshot omits it."""
        self.commit({".gitignore": "runs/\n", "a.py": "x = 1\n"})
        run_dir = self.repo / "runs" / "r1"
        run_dir.mkdir(parents=True)
        (run_dir / "state.md").write_text("run state\n")
        self.edit({"b.py": "y = 2\n"})
        index = self.run_dir / "snapshot.index"
        tree = lint.snapshot_tree(self.repo, run_dir, index)
        names = git(self.repo, "ls-tree", "-r", "--name-only", tree).split()
        self.assertEqual(sorted(names), [".gitignore", "a.py", "b.py"])

    def test_new_findings_are_separated_from_base_debt(self):
        self.commit({"a.py": "x = 1  # lint\n"})
        self.base()
        self.edit({"a.py": "x = 1  # lint\ny = 2  # lint\n"})
        payload = self.run_pass()
        self.assertTrue(payload["block"].startswith("ShipLoop lint (supporting output; not exit-criteria evidence"))
        self.assertIn("[present at the base; elsewhere in a file this item changed; L", payload["block"])
        self.assertIn("[new since the base; on a line this item changed; L", payload["block"])
        self.assertEqual(payload["counts"]["new_on_changed"], 1)
        self.assertEqual(payload["counts"]["at_base"], 1)
        self.assertEqual(payload["exit_code"], lint.EXIT_FINDINGS)
        self.assertIn("linted by ruff (rules F,E9; no project ruff config: --isolated)", payload["block"])

    def test_absent_tool_is_uncovered_with_optional_recommendation(self):
        self.commit({"a.py": "x = 1\n"})
        self.base()
        self.edit({"a.py": "x = 2\n"})
        payload = self.run_pass(env=self.env(path=str(self.repo / "nothing-here")))
        self.assertIn("syntax only: no linter available (ruff not found on this process's PATH:", payload["block"])
        self.assertIn("- Optional: ruff not found on this process's PATH:", payload["block"])
        self.assertEqual(payload["counts"]["uncovered"], 1)
        self.assertEqual(payload["exit_code"], lint.EXIT_FINDINGS)

    def test_declared_but_absent_tool_is_recommended(self):
        self.commit({"a.py": "x = 1\n", "pyproject.toml": "[tool.ruff]\nline-length = 100\n"})
        self.base()
        self.edit({"a.py": "x = 2\n"})
        payload = self.run_pass(env=self.env(path=str(self.repo / "nothing-here")))
        self.assertIn("- Recommended: the repository declares ruff (pyproject.toml), but ruff not found",
                      payload["block"])

    def test_fix_on_changed_lines_is_applied_with_journal_and_mode_kept(self):
        self.commit({"a.py": "x = 1\n"})
        (self.repo / "a.py").chmod(0o755)
        self.base()
        self.edit({"a.py": "x = 1\ny = 2  # fixme\n"})
        payload = self.run_pass()
        self.assertEqual((self.repo / "a.py").read_text(), "x = 1\ny = 2\n")
        self.assertEqual(stat.S_IMODE((self.repo / "a.py").stat().st_mode), 0o755)
        self.assertEqual(payload["applied"], ["a.py"])
        self.assertIn("AUTO-FIX APPLIED: ShipLoop edited 1 file", payload["block"])
        self.assertIn("| -y = 2  # fixme", payload["block"])
        journal = self.run_dir / "lint" / "pending-A1.patch"
        self.assertTrue(journal.is_file())
        self.assertEqual(stat.S_IMODE(journal.stat().st_mode), 0o600)
        exact = self.run_dir / "lint" / "logs" / "A1.patch"
        self.assertEqual(stat.S_IMODE(exact.stat().st_mode), 0o600)
        # The printed revert command restores the pre-fix content.
        subprocess.run(["git", "-C", str(self.repo), "apply", "-R", "--include=a.py", str(exact)], check=True)
        self.assertEqual((self.repo / "a.py").read_text(), "x = 1\ny = 2  # fixme\n")
        # Storing the record consumes the journal.
        for relative, text in lint.record_writes(payload).items():
            store.atomic_write_text(self.run_dir / relative, text)
        self.assertEqual(lint.pending_lines(self.run_dir), [])
        lint.finalize(self.run_dir, payload)
        self.assertFalse(journal.exists())

    def test_fix_touching_an_untouched_line_is_withheld_for_the_whole_file(self):
        self.commit({"a.py": "a = 0  # fixme\n"})
        self.base()
        self.edit({"a.py": "a = 0  # fixme\nb = 1  # fixme\n"})
        payload = self.run_pass()
        self.assertEqual((self.repo / "a.py").read_text(), "a = 0  # fixme\nb = 1  # fixme\n")
        self.assertIn("NOT APPLIED (would change a line this work item did not touch; whole file withheld)",
                      payload["block"])
        self.assertFalse((self.run_dir / "lint" / "pending-A1.patch").exists())

    def test_fixer_that_changes_line_endings_is_withheld(self):
        (self.repo / "a.py").write_bytes(b"x = 1\r\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "crlf")
        self.base()
        (self.repo / "a.py").write_bytes(b"x = 1\r\ny = 2  # fixme\r\n")
        payload = self.run_pass()
        self.assertIn("the fixer changed line endings; whole file withheld", payload["block"])
        self.assertEqual((self.repo / "a.py").read_bytes(), b"x = 1\r\ny = 2  # fixme\r\n")

    def test_file_changed_mid_pass_refuses_the_fix(self):
        self.commit({"a.py": "x = 1\n"})
        self.base()
        self.edit({"a.py": "x = 1\ny = 2  # fixme\n"})
        payload = self.run_pass(env=self.env(STUB_TOUCH=str(self.repo / "a.py")))
        self.assertEqual((self.repo / "a.py").read_text(), "x = 1\ny = 2  # fixme\n# touched\n")
        self.assertIn("file changed since ShipLoop read it; fix refused", payload["block"])
        self.assertEqual(payload["applied"], [])
        # Nothing was written, so no journal remains to warn about later.
        self.assertEqual(list((self.run_dir / "lint").glob("pending-*.patch")), [])
        for relative, text in lint.record_writes(payload).items():
            store.atomic_write_text(self.run_dir / relative, text)
        lint.finalize(self.run_dir, payload)
        self.assertEqual(lint.pending_lines(self.run_dir), [])

    def test_form_feed_lines_keep_the_revert_patch_applicable(self):
        self.commit({"a.py": "import sys\n\x0c\nx = 1\n"})
        self.base()
        self.edit({"a.py": "import sys\n\x0c\nx = 1\ny = 2  # fixme\n"})
        payload = self.run_pass()
        self.assertEqual(payload["applied"], ["a.py"])
        self.assertNotIn("No newline at end of file", payload["block"])
        exact = self.run_dir / "lint" / "logs" / "A1.patch"
        subprocess.run(["git", "-C", str(self.repo), "apply", "-R", "--include=a.py", str(exact)], check=True)
        self.assertEqual((self.repo / "a.py").read_text(), "import sys\n\x0c\nx = 1\ny = 2  # fixme\n")
        self.assertEqual(lint._changed_lines("a\n\x0cb\nc\n", "a\n\x0cb\nc\nd\n"), {4})

    def test_fixer_error_writes_nothing_and_shows_full_stderr(self):
        self.commit({"a.py": "x = 1\n"})
        self.base()
        self.edit({"a.py": "y = 2  # fixme\n"})
        payload = self.run_pass(env=self.env(STUB_FIX_EXIT="2"))
        self.assertEqual((self.repo / "a.py").read_text(), "y = 2  # fixme\n")
        self.assertIn("| stub fixer failure: boom", payload["block"])
        self.assertIn("the fixer exited 2; nothing was written", payload["block"])
        self.assertEqual(payload["counts"]["tool_errors"], 1)

    def test_fixer_timeout_kills_the_group_and_writes_nothing(self):
        self.commit({"a.py": "x = 1\n"})
        self.base()
        self.edit({"a.py": "y = 2  # fixme\n"})
        started = time.monotonic()
        payload = self.run_pass(env=self.env(STUB_FIX_SLEEP="30"), tool_timeout=1.0)
        self.assertLess(time.monotonic() - started, 15)
        self.assertEqual((self.repo / "a.py").read_text(), "y = 2  # fixme\n")
        self.assertIn("timed out (process group killed)", payload["block"])
        self.assertEqual(payload["counts"]["timeouts"], 1)

    def test_whole_pass_budget_reports_skipped_work(self):
        self.commit({"a.py": "x = 1\n"})
        self.base()
        self.edit({"a.py": "y = 2  # lint\n"})
        payload = self.run_pass(budget=0.0)
        self.assertIn("Skipped because the " + str(int(lint.BUDGET_SECONDS)) + "-second pass budget ran out: reading a.py", payload["block"])
        self.assertIn("- a.py: not in scope: the pass budget ran out before this file was read", payload["block"])
        self.assertEqual(payload["counts"]["uncovered"], 1)

    def test_git_plumbing_is_bounded_by_the_remaining_budget(self):
        seen = []
        real = lint._git

        def spy(top, *args, **kwargs):
            seen.append((args[0], kwargs.get("timeout", lint.GIT_TIMEOUT_SECONDS)))
            return real(top, *args, **kwargs)

        self.commit({"a.py": "x = 1\n", "README.md": "one\n"})
        self.base()
        self.edit({"a.py": "y = 2\n", "README.md": "two\n"})
        with mock.patch.object(lint, "_git", spy):
            self.run_pass(mode="report", budget=3.0)
        self.assertTrue(seen)
        self.assertTrue(all(timeout <= 3.0 for _verb, timeout in seen), seen)
        # Every changed text file reads its base blob: discovered linters gate on changed lines.
        self.assertEqual([verb for verb, _timeout in seen].count("cat-file"), 2)

    def test_large_repetitive_diffs_are_not_attributed_line_by_line(self):
        base = "".join("x = 1\n" if n % 7 else "y = 2\n" for n in range(7000))
        current = "".join(line if n % 50 else "z = 3\n" for n, line in enumerate(base.splitlines(True)))
        started = time.monotonic()
        self.assertIsNone(lint._changed_lines(base, current))
        self.assertFalse(lint._hunks_on_changed(base, current, set()))
        self.assertLess(time.monotonic() - started, 2.0)
        self.assertEqual(lint._changed_lines("a\nb\nc\n", "a\nB\nc\nd\n"), {2, 4})

    def test_tool_created_files_are_reported_and_catalogued_cache_removed(self):
        self.commit({"a.py": "x = 1\n"})
        self.base()
        self.edit({"a.py": "y = 2  # fixme\n"})
        payload = self.run_pass(env=self.env(STUB_CREATE="1"))
        self.assertIn("Files created by tools during this pass:", payload["block"])
        self.assertIn("stray.txt", payload["block"])
        self.assertIn("Removed catalogued caches: .ruff_cache", payload["block"])
        self.assertFalse((self.repo / ".ruff_cache").exists())
        self.assertTrue((self.repo / "stray.txt").exists())

    def test_config_fix_true_cannot_rewrite_through_the_check_run(self):
        self.commit({"a.py": "x = 1\n", "pyproject.toml": "[tool.ruff]\nfix = true\n"})
        self.base()
        self.edit({"a.py": "y = 2  # fixme\n"})
        payload = self.run_pass(mode="report")
        self.assertEqual((self.repo / "a.py").read_text(), "y = 2  # fixme\n")
        checks = [argv for argv in self.logged() if argv[0] == "ruff" and "--" in argv and "--show-files" not in argv]
        self.assertTrue(checks and all("--no-fix" in argv for argv in checks), checks)
        self.assertIn("linted by ruff (rules from pyproject.toml)", payload["block"])

    def test_rename_is_rename_aware(self):
        self.commit({"old.sh": "#!/bin/sh\ncd /tmp\necho one\necho two\necho three\n"})
        self.base()
        git(self.repo, "mv", "old.sh", "new.sh")
        self.edit({"new.sh": "#!/bin/sh\ncd /tmp\necho one\necho two\necho three\ncd /var\n"})
        payload = self.run_pass()
        self.assertIn("- R old.sh -> new.sh", payload["block"])
        self.assertIn("new.sh:2:1: warning: Use cd || exit [SC2164]   [present at the base", payload["block"])
        self.assertIn("new.sh:6:1: warning: Use cd || exit [SC2164]   [new since the base", payload["block"])
        self.assertIn("-S warning --norc: no .shellcheckrc; check-only in phase 1", payload["block"])

    def test_empty_or_differently_named_identical_blobs_are_not_mirrors(self):
        self.commit({"pkg/__init__.py": "", "pkg/a/__init__.py": "", "pkg/b/__init__.py": "",
                     "a/const.py": "x = 1\n"})
        self.base()
        self.edit({"pkg/__init__.py": "y = 2  # fixme\n", "pkg/c/__init__.py": "", "b/other.py": "x = 1\n"})
        payload = self.run_pass()
        self.assertNotIn("mirror of", payload["block"])
        self.assertEqual(payload["applied"], ["pkg/__init__.py"])
        self.assertEqual((self.repo / "pkg/__init__.py").read_text(), "y = 2\n")

    def test_identical_blob_twins_are_linted_once_and_never_fixed(self):
        self.commit({"keep.txt": "keep\n"})
        self.base()
        self.edit({"skills/a.py": "y = 2  # fixme\n", "plugins/a.py": "y = 2  # fixme\n"})
        payload = self.run_pass()
        self.assertIn("not in scope: identical to plugins/a.py, linted once", payload["block"])
        self.assertIn("mirror of skills/a.py: fix the source and regenerate", payload["block"])
        self.assertEqual((self.repo / "plugins/a.py").read_text(), "y = 2  # fixme\n")
        self.assertEqual((self.repo / "skills/a.py").read_text(), "y = 2  # fixme\n")
        self.assertEqual(payload["applied"], [])

    def test_whitespace_attribute_makes_a_file_check_only(self):
        self.commit({"a.py": "x = 1\n", ".gitattributes": "a.py -whitespace\n"})
        self.base()
        self.edit({"a.py": "y = 2  # fixme\n"})
        payload = self.run_pass()
        self.assertIn("NOT APPLIED (check-only: -whitespace attribute)", payload["block"])
        self.assertEqual((self.repo / "a.py").read_text(), "y = 2  # fixme\n")

    def test_syntax_regression_withholds_the_fix(self):
        self.commit({"a.py": "x = 1\n"})
        self.base()
        self.edit({"a.py": "y = 2  # breaks  # fixme\n"})
        payload = self.run_pass()
        self.assertIn("the fixed file no longer parses (syntax regression); fix withheld", payload["block"])
        self.assertEqual((self.repo / "a.py").read_text(), "y = 2  # breaks  # fixme\n")

    def test_report_mode_shows_the_would_be_diff_as_not_applied(self):
        self.commit({"a.py": "x = 1\n"})
        self.base()
        self.edit({"a.py": "y = 2  # fixme\n"})
        payload = self.run_pass(mode="report")
        self.assertIn("NOT APPLIED (report-only pass): a.py", payload["block"])
        self.assertIn("| +y = 2", payload["block"])
        self.assertEqual((self.repo / "a.py").read_text(), "y = 2  # fixme\n")

    def test_later_static_checks_entry_is_report_only(self):
        self.commit({"a.py": "x = 1\n"})
        self.base()
        self.edit({"a.py": "y = 2  # fixme\n"})
        payload = self.run_pass(allow_fix=False)
        self.assertIn("auto-fix runs only on the work item's first static-checks entry", payload["block"])
        self.assertEqual(payload["mode"], "report")

    def test_deletion_rules_are_never_auto_applied(self):
        self.commit({"a.py": "x = 1\n"})
        self.base()
        self.edit({"a.py": "import registry  # unused\nx = 1\n"})
        payload = self.run_pass()
        self.assertEqual((self.repo / "a.py").read_text(), "import registry  # unused\nx = 1\n")
        fixers = [argv for argv in self.logged() if "--fix" in argv]
        self.assertTrue(fixers)
        for argv in fixers:
            self.assertIn('lint.extend-unfixable=["F401", "F811", "F841"]', argv)
        self.assertIn("fixable, not applied: deletion-type rule (ruff-classified safe; may remove side-effect code)",
                      payload["block"])

    def test_unsafe_fixes_stay_off_even_when_config_enables_them(self):
        self.commit({"a.py": "x = 1\n", "pyproject.toml": "[tool.ruff]\nunsafe-fixes = true\n"})
        self.base()
        self.edit({"a.py": "z = 3  # unsafe\n"})
        payload = self.run_pass()
        self.assertEqual((self.repo / "a.py").read_text(), "z = 3  # unsafe\n")
        fixers = [argv for argv in self.logged() if "--fix" in argv]
        self.assertTrue(fixers)
        for argv in fixers:
            self.assertIn("--no-unsafe-fixes", argv)
            self.assertIn("lint.extend-safe-fixes=[]", argv)
        self.assertEqual(payload["applied"], [])

    def test_project_config_is_resolved_per_file(self):
        self.commit({"top.py": "a = 1\n", "pkg/ruff.toml": "[lint]\nselect = ['F']\n", "pkg/m.py": "b = 1\n"})
        self.base()
        self.edit({"top.py": "a = 2  # lint\n", "pkg/m.py": "b = 2  # lint\n"})
        payload = self.run_pass(mode="report")
        checks = [argv for argv in self.logged() if argv[0] == "ruff" and "--no-fix" in argv and "--" in argv]
        by_file = {argv[-1]: argv for argv in checks}
        self.assertIn("--isolated", by_file["top.py"])
        self.assertNotIn("--isolated", by_file["pkg/m.py"])
        self.assertIn("linted by ruff (rules from pkg/ruff.toml)", payload["block"])

    def test_repo_config_exclusion_is_reported_not_counted_as_clean(self):
        self.commit({"gen.py": "a = 1\n", "ruff.toml": "extend-exclude = ['gen.py']\n"})
        self.base()
        self.edit({"gen.py": "a = 2  # lint\n"})
        payload = self.run_pass(env=self.env(STUB_EXCLUDE="gen.py"))
        self.assertIn("- gen.py: excluded by repo config (not linted)", payload["block"])
        self.assertEqual(payload["counts"]["new_on_changed"], 0)

    def test_default_exclude_without_project_config_is_uncovered(self):
        """With --isolated only ruff's built-in excludes apply; that is not the repository's choice."""
        self.commit({"dist/y.py": "a = 1\n"})
        self.base()
        self.edit({"dist/y.py": "import os  # lint\na = 2\n"})
        payload = self.run_pass(mode="report", env=self.env(STUB_EXCLUDE="dist/y.py"))
        self.assertIn("- dist/y.py: excluded by ruff's built-in default excludes (not linted; no project ruff "
                      "config)", payload["block"])
        self.assertNotIn("excluded by repo config", payload["block"])
        self.assertEqual(payload["counts"]["uncovered"], 1)
        self.assertEqual(payload["exit_code"], lint.EXIT_FINDINGS)

    def test_each_file_names_its_own_ruff_config(self):
        self.commit({"pyproject.toml": "[tool.ruff]\nline-length = 100\n", "pkg/ruff.toml": "line-length = 90\n",
                     "top.py": "a = 1\n", "pkg/m.py": "b = 1\n"})
        self.base()
        self.edit({"top.py": "a = 2\n", "pkg/m.py": "b = 2\n"})
        block = self.run_pass(mode="report")["block"]
        self.assertIn("- pkg/m.py: linted by ruff (rules from pkg/ruff.toml)", block)
        self.assertIn("- top.py: linted by ruff (rules from pyproject.toml)", block)

    def test_repo_promoted_unsafe_fix_is_withheld(self):
        """ruff merges extend-safe-fixes, so the --config pin alone cannot clear a repository's list."""
        self.commit({"a.py": "x = 1\n", "pyproject.toml": "[tool.ruff.lint]\nextend-safe-fixes = [\"X200\"]\n"})
        self.base()
        self.edit({"a.py": "z = 3  # unsafe\n"})
        payload = self.run_pass()
        self.assertEqual((self.repo / "a.py").read_text(), "z = 3  # unsafe\n")
        self.assertEqual(payload["applied"], [])
        self.assertIn("NOT APPLIED (the repository's ruff config promotes unsafe fixes to safe (extend-safe-fixes: "
                      "X200); fix withheld): a.py", payload["block"])
        settings = [argv for argv in self.logged() if "--show-settings" in argv]
        self.assertEqual(len(settings), 1)
        self.assertIn("--no-unsafe-fixes", settings[0])
        self.assertEqual(settings[0][-1], "./a.py")
        self.assertFalse((self.run_dir / "lint" / "pending-A1.patch").exists())

    def test_project_config_without_promotions_still_fixes(self):
        self.commit({"a.py": "x = 1\n", "pyproject.toml": "[tool.ruff]\nline-length = 100\n"})
        self.base()
        self.edit({"a.py": "x = 1\ny = 2  # fixme\n"})
        payload = self.run_pass()
        self.assertEqual(payload["applied"], ["a.py"])
        self.assertEqual((self.repo / "a.py").read_text(), "x = 1\ny = 2\n")

    def test_forced_safe_parser(self):
        self.assertEqual(lint._forced_safe("x\nlinter.safety_table.forced_safe = []\n"), [])
        self.assertEqual(lint._forced_safe("linter.safety_table.forced_safe = [\n\tnone-comparison (E711),\n]\n"),
                         ["E711"])
        self.assertIsNone(lint._forced_safe("linter.safety_table.forced_safe = [\n\tnone-comparison (E711),\n"))
        self.assertIsNone(lint._forced_safe("no settings here\n"))

    def test_tier0_skips_markdown_markers_jsonc_and_counts_json_regressions(self):
        self.commit({"README.md": "Title\n", "data.json": "{\"a\": 1}\n", "tsconfig.json": "{}\n"})
        self.base()
        self.edit({"README.md": "Title\n=======\n", "data.json": "{\"a\": }\n",
                   "tsconfig.json": "{ // comment\n}\n"})
        payload = self.run_pass()
        self.assertNotIn("conflict marker", payload["block"].split("Findings")[1])
        self.assertIn("- tsconfig.json: not in scope: JSONC name; JSON parse skipped", payload["block"])
        self.assertIn("JSON parse fails now and passed at the base", payload["block"])

    def test_repository_text_is_marked_as_data_and_credentials_are_redacted(self):
        self.commit({"a.py": "x = 1\n"})
        self.base()
        secret = "sk-live-" + "abcdefghijklmnop1234"
        self.edit({"a.py": "API_KEY = \"" + secret + "\"  # fixme\n",
                   "we\nird.py": "y = 1  # lint\n"})
        payload = self.run_pass(mode="report")
        self.assertNotIn(secret, payload["block"])
        self.assertIn("| " + lint.privacy.REDACTED_SENSITIVE_VALUE, payload["block"])
        self.assertIn('- A "we\\nird.py"', payload["block"])
        # A newline in a path never starts an unprefixed packet line.
        self.assertFalse([line for line in payload["block"].splitlines() if line.startswith("ird.py")])
        data = payload["block"].split("BEGIN lint data")[1].split("END lint data")[0]
        self.assertIn("\n| a.py:1:1: X100 [*] fixme marker", data)
        self.assertNotIn("\nCall this when done", data)

    def test_fallback_base_is_report_only_and_says_so(self):
        self.commit({"a.py": "x = 1\n"})
        self.edit({"a.py": "y = 2  # fixme\n"})
        payload = self.run_pass(base=None)
        self.assertIn("Scope is not this work item's: base fell back to HEAD", payload["block"])
        self.assertEqual((self.repo / "a.py").read_text(), "y = 2  # fixme\n")
        self.assertEqual(payload["mode"], "report")

    def test_not_a_git_checkout_cannot_run(self):
        plain = Path(self.temp.name) / "plain"
        plain.mkdir()
        with self.assertRaisesRegex(lint.LintError, "not a Git checkout"):
            lint.lint_pass(plain, self.run_dir, action="A1", work_item="W1", stage="static-checks",
                           mode="fix", run_option="fix", base=None, allow_fix=False, env=self.env())

    def test_only_formatters_and_pre_commit_are_listed_as_not_run(self):
        """Repository linters run; a format script, other make targets and pre-commit do not."""
        self.commit({"a.py": "x = 1\n", "package.json": json.dumps({"scripts": {"lint": "eslint .",
                                                                                  "format": "prettier -w ."}}),
                     "Makefile": "lint:\n\techo lint\nformat-check:\n\techo fc\ncheck: test\n\techo check\n",
                     ".pre-commit-config.yaml": "repos: []\n", "eslint.config.js": "export default []\n"})
        self.base()
        self.edit({"a.py": "x = 2\n"})
        payload = self.run_pass()
        block = payload["block"]
        self.assertIn("Not run by ShipLoop (ask the user before running any of these):", block)
        self.assertIn("| npm run format (package.json scripts.format; not run: only the script named lint runs", block)
        self.assertIn("| make format-check (Makefile; not run: only the lint target runs, first line: echo fc)", block)
        self.assertNotIn("make check", block)
        self.assertNotIn("| npm run lint", block)
        self.assertIn("may download hook environments", block)
        # ruff covers the only changed file, so no project lint script ran; no JS file, so no eslint.
        self.assertFalse(any(argv[0] not in ("ruff", "shellcheck") for argv in self.logged()))


    def test_shiploop_runtime_metadata_is_never_in_scope(self):
        self.commit({"a.py": "x = 1\n"})
        self.base()
        self.edit({"a.py": "x = 2\n", ".shiploop-improve/R1/A7/packet.json": "{}  \n",
                   ".shiploop-improve/.experiments/R1/probe.py": "z = 3  # fixme\n",
                   ".until-loop/working.md": "note   \n", "sub/.shiploop-handoff/1/handoff.json": "{}\n"})
        payload = self.run_pass()
        self.assertIn("Scope: 1 file changed since the base", payload["block"])
        for name in (".shiploop-improve", ".until-loop", ".shiploop-handoff"):
            self.assertNotIn(name, payload["block"])
        self.assertEqual(payload["applied"], [])
        self.assertEqual(payload["exit_code"], lint.EXIT_CLEAN)
        self.assertEqual((self.repo / ".shiploop-improve/.experiments/R1/probe.py").read_text(), "z = 3  # fixme\n")

    def test_a_subdirectory_run_never_lints_or_fixes_outside_it(self):
        self.commit({"svc_a/a.py": "x = 1\n", "svc_b/b.py": "y = 1\n",
                     "svc_a/package.json": json.dumps({"scripts": {"lint": "eslint ."}})})
        base = lint.capture_base(self.run_dir, self.repo / "svc_a", "W1")
        for relative, text in base.items():
            (self.run_dir / relative).parent.mkdir(parents=True, exist_ok=True)
            (self.run_dir / relative).write_text(text)
        self.edit({"svc_a/a.py": "x = 1\nz = 2  # fixme\n", "svc_b/b.py": "y = 1\nw = 2  # fixme\n"})
        payload = lint.lint_pass(self.repo / "svc_a", self.run_dir, action="A1", work_item="W1",
                                 stage="static-checks", mode="fix", run_option="fix",
                                 base=lint.read_base(self.run_dir, "W1"), allow_fix=True, env=self.env())
        self.assertIn("limited to the run's repository svc_a", payload["block"])
        self.assertNotIn("svc_b", payload["block"])
        self.assertEqual(payload["applied"], ["svc_a/a.py"])
        self.assertEqual((self.repo / "svc_b/b.py").read_text(), "y = 1\nw = 2  # fixme\n")
        # ruff covers svc_a/a.py, so the project lint script is not needed.
        self.assertNotIn("npm run lint", payload["block"])

    def test_option_shaped_file_names_are_passed_as_paths(self):
        """node --check must never read a changed file named --require=x.js as an option."""
        (self.bin / "node").write_text("#!" + sys.executable + "\n" + NODE_STUB)
        (self.bin / "node").chmod(0o755)
        self.commit({"keep.txt": "keep\n"})
        self.base()
        self.edit({"--require=x.js": "1;\n", "x.js": "require('fs').writeFileSync('PWNED', '')\n"})
        payload = self.run_pass(mode="report")
        calls = [argv for argv in self.logged() if argv[0] == "node"]
        self.assertIn(["node", "--check", "./--require=x.js"], calls)
        self.assertFalse(any(arg.startswith("--require") for argv in calls for arg in argv))
        self.assertFalse(Path(str(self.log) + ".preloaded").exists())
        self.assertIn("syntax checked by node --check", payload["block"])

    def test_undecodable_path_bytes_never_break_the_record(self):
        blob = subprocess.run(["git", "-C", str(self.repo), "hash-object", "-w", "--stdin"], input=b"x = 1\n",
                              capture_output=True, check=True).stdout.decode().strip()
        subprocess.run([b"git", b"-C", os.fsencode(self.repo), b"update-index", b"--add", b"--cacheinfo",
                        b"100644," + blob.encode() + b",caf\xe9.py"], check=True, capture_output=True)
        git(self.repo, "commit", "-qm", "odd name")
        payload = self.run_pass(base=None, mode="report")
        self.assertIn("caf\\xe9.py", payload["block"])
        for relative, text in lint.record_writes(payload).items():
            text.encode("utf-8")
            store.atomic_write_text(self.run_dir / relative, text)

    def test_syntax_guard_that_does_not_complete_withholds_the_fix(self):
        item = lint._File({"status": "M", "path": "a.py", "old": "a.py"})
        item.data = b"x = 1\n"
        timeout = {"status": "timeout", "exit": None}
        for after, before in ((timeout, None), (timeout, timeout), (None, None)):
            invoker = mock.Mock()
            invoker.run.side_effect = [after, before]
            with self.subTest(after=after, before=before):
                self.assertIn("fix withheld", lint._syntax_regression(invoker, "ruff", item, b"def (:\n"))
        invoker = mock.Mock()
        invoker.run.side_effect = [{"status": "ok", "exit": 1}, {"status": "ok", "exit": 1}]
        self.assertEqual(lint._syntax_regression(invoker, "ruff", item, b"def (:\n"), "")

    def test_credential_shaped_paths_are_redacted_in_stored_and_repeated_coverage(self):
        self.commit({"keep.txt": "keep\n"})
        self.base()
        name = "cfg/api_key=live9f8e7d6c.py"
        self.edit({name: "x = 1\n"})
        payload = self.run_pass(mode="report")
        self.assertNotIn("live9f8e7d6c", "\n".join(payload["coverage_lines"]))
        prior = self.run_dir / "lint" / "A1.md"
        repeated = lint.unchanged_payload("B1", "verify", "W1", "report", payload, prior, "shiploop", self.run_dir)
        self.assertNotIn("live9f8e7d6c", repeated["block"])
        data = repeated["block"].split("BEGIN lint data")[1].split("END lint data")[0]
        self.assertIn("Coverage:", data)

    def test_interrupted_journal_is_adopted_once_by_the_next_pass(self):
        self.commit({"a.py": "x = 1\n"})
        self.base()
        self.edit({"a.py": "x = 2\n"})
        leftover = self.run_dir / "lint" / "pending-nav-old.patch"
        leftover.parent.mkdir(parents=True, exist_ok=True)
        leftover.write_text("--- a/a.py\n+++ b/a.py\n")
        self.assertTrue(lint.pending_lines(self.run_dir))
        payload = self.run_pass(mode="report")
        self.assertFalse(leftover.exists())
        kept = list((self.run_dir / "lint" / "logs").glob("pending-nav-old-interrupted-*.patch"))
        self.assertEqual(len(kept), 1)
        self.assertIn("An interrupted earlier lint pass left a journal, kept at", payload["block"])
        self.assertEqual(lint.pending_lines(self.run_dir), [])


class ToolResolutionTests(Fixture):
    def test_version_manager_shims_are_refused(self):
        shims = Path(self.temp.name) / "home" / ".pyenv" / "shims"
        write_stub(shims, "ruff")
        path, reason = lint.resolve_tool("ruff", self.repo, str(shims), (".pyenv",))
        self.assertIsNone(path)
        self.assertIn("version-manager shim", reason)
        volta = Path(self.temp.name) / "home" / ".volta" / "bin"
        volta.mkdir(parents=True)
        target = Path(self.temp.name) / "volta-shim"
        target.write_text("#!/bin/sh\n")
        target.chmod(0o755)
        (volta / "node").symlink_to(target)
        path, reason = lint.resolve_tool("node", self.repo, str(volta), ())
        self.assertIsNone(path)
        self.assertIn("not run (may download)", reason)

    def test_shim_is_reported_in_the_pass(self):
        shims = Path(self.temp.name) / "home" / ".pyenv" / "shims"
        write_stub(shims, "ruff")
        self.commit({"a.py": "x = 1\n"})
        self.base()
        self.edit({"a.py": "y = 2  # fixme\n"})
        payload = self.run_pass(env=self.env(path=str(shims)))
        self.assertIn("found only as a version-manager shim", payload["block"])
        self.assertFalse(any(argv[0] == "ruff" for argv in self.logged()))

    def test_repository_local_tools_are_refused(self):
        local = self.repo / ".venv" / "bin"
        write_stub(local, "ruff")
        path, reason = lint.resolve_tool("ruff", self.repo, str(local) + ":" + str(self.bin), ())
        self.assertIsNone(path)
        self.assertIn("inside the repository; repo-local, not run", reason)

    def test_relative_path_entries_are_ignored(self):
        path, reason = lint.resolve_tool("ruff", self.repo, "bin:.:" + str(self.bin), ())
        self.assertEqual(path, str(self.bin / "ruff"))

    def test_tools_in_another_work_tree_of_the_repository_are_refused(self):
        self.commit({"a.py": "x = 1\n"})
        venv = self.repo / ".venv" / "bin"
        write_stub(venv, "ruff")
        linked = Path(self.temp.name) / "ws" / "worktree"
        git(self.repo, "worktree", "add", "-q", str(linked))
        roots = lint.repo_roots(linked)
        self.assertIn(os.path.realpath(str(self.repo)), roots)
        path, reason = lint.resolve_tool("ruff", linked, str(venv) + ":" + str(self.bin), (), roots)
        self.assertIsNone(path)
        self.assertIn("inside the repository; repo-local, not run", reason)

    def test_git_is_never_resolved_from_a_relative_or_repository_path(self):
        marker = Path(self.temp.name) / "repo-git-ran"
        fake = self.repo / "git"
        fake.write_text("#!/bin/sh\necho ran >> " + str(marker) + "\nexit 1\n")
        fake.chmod(0o755)
        self.commit({"a.py": "x = 1\n"})
        self.base()
        self.edit({"a.py": "x = 2\n"})
        cwd = os.getcwd()
        os.chdir(str(self.repo))
        self.addCleanup(os.chdir, cwd)
        lint._GIT_EXECUTABLES.clear()
        self.addCleanup(lint._GIT_EXECUTABLES.clear)
        poisoned = ".:" + str(self.repo) + ":" + os.environ.get("PATH", "")
        with mock.patch.dict(os.environ, {"PATH": poisoned}):
            payload = self.run_pass(mode="report", env=self.env(path=".:" + str(self.bin)))
        self.assertFalse(marker.exists())
        tier0 = [line for line in payload["block"].splitlines() if " diff --check " in line]
        self.assertTrue(tier0 and os.path.isabs(tier0[0].split("] ", 1)[1].split(" ", 1)[0]), tier0)


def complete(run: Path, state: dict, result: dict = DONE) -> str:
    action = nav.current_action(state)["id"]
    stage = nav.current_stage(state)
    if stage == "plan" and result.get("outcome") == "done" and "assumptions" not in result:
        result = dict(result, assumptions=[])
    if stage == "step-plan" and result.get("outcome") == "done" and "test_commands" not in result:
        result = dict(result, test_commands=[], test_commands_na="Synthetic fixture; no test commands.",
                      paths=["src/**"])
    if stage in knowledge_support.knowledge.CLOSES:
        knowledge_support.write(state)
    inbox = run / "inbox"
    inbox.mkdir(exist_ok=True)
    path = inbox / (action + ".md")
    path.write_text(store.dumps(result, "result"))
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        nav.dispatch(CORE, run, state, types.SimpleNamespace(command="complete", action=action, result=str(path)))
    return buffer.getvalue()


def complete_implement(run: Path, state: dict) -> str:
    """Submit implement as done through the lint gate: resubmit after an auto-fix, waive what remains."""
    result = DONE
    for _ in range(4):
        try:
            return complete(run, state, result)
        except nav.NavigatorError as exc:
            text = str(exc)
            if "auto-fixed" in text:
                continue
            ids = re.findall(r"^- (L[0-9a-f]{10}(?:-[0-9]+)?) ", text, re.M)
            if not ids:
                raise
            result = dict(DONE, lint_waivers=[{"id": found, "reason": "Fixture keeps it."} for found in ids])
    raise AssertionError("the lint gate kept refusing implement")


def drive(run: Path, until: str, *, edit=None, edit_at: str = "implement") -> dict:
    """Walk a saved run through real dispatch (so the lint hooks run) to ``until``."""
    state = store.read_record(run / "state.md")
    for _ in range(200):
        if nav.current_stage(state) == until and not state.get("active_improve"):
            return state
        stage = nav.current_stage(state)
        if edit is not None and stage == edit_at:
            edit()
        action = nav.current_action(state)["id"]
        if stage in lint.GATE_STAGES:
            complete_implement(run, state)
        else:
            complete(run, state)
        state = store.read_record(run / "state.md")
        if state.get("active_improve"):
            # The improve-complete branch of dispatch: finish the child, run the lint hook, save.
            updated = nav.finish_improve(state, action, {"summary": "Synthetic Improve.",
                                                         "review_refs": ["synthetic://r"],
                                                         "check_refs": ["synthetic://c"]})
            writes, payload = nav._lint_transition(CORE, run, state, updated)
            nav.save(run, updated, writes)
            nav._lint_finish(run, payload)
            state = updated
    raise AssertionError("did not reach " + until)


class HookTests(Fixture):
    def start(self, option: str | None = "fix") -> None:
        state = nav.new_state(str(self.repo), "Lint fixture.", improve_skill="", lint_option=option)
        nav.save(self.run_dir, state)

    def patched_env(self, **extra: str):
        return mock.patch.dict(os.environ, {"PATH": str(self.bin) + ":" + SYSTEM_PATH,
                                            "STUB_LOG": str(self.log), **extra})

    def edit_item(self) -> None:
        self.edit({"a.py": "x = 1\ny = 2  # fixme\n"})

    def test_static_checks_entry_fixes_once_and_next_never_relints(self):
        self.commit({"a.py": "x = 1\n"})
        self.start()
        with self.patched_env():
            state = drive(self.run_dir, "skill-validate", edit=self.edit_item, edit_at="document")
            self.assertTrue((self.run_dir / "lint" / "items" / "W1.md").is_file())
            packet = complete(self.run_dir, state)
            state = store.read_record(self.run_dir / "state.md")
            self.assertEqual(nav.current_stage(state), "static-checks")
            self.assertIn("AUTO-FIX APPLIED", packet)
            self.assertLess(packet.index("Call this when done:"), packet.index("ShipLoop lint (supporting output"))
            self.assertEqual((self.repo / "a.py").read_text(), "x = 1\ny = 2\n")
            self.assertEqual(list((self.run_dir / "lint").glob("pending-*.patch")), [])
            calls = len(self.logged())
            again = nav.render(CORE, self.run_dir, state)
            nav.render(CORE, self.run_dir, state)
            self.assertEqual(len(self.logged()), calls)
            self.assertIn("AUTO-FIX APPLIED", again)
            # Model repairs make the stored record stale; rendering says so without linting.
            self.edit({"a.py": "x = 1\ny = 3\n"})
            self.assertIn("Status: stale. a.py changed after this pass", nav.render(CORE, self.run_dir, state))
            self.assertEqual(len(self.logged()), calls)
            # The bound Until Loop repeats the quality review, so the graph refuses repeat here.
            before = (self.run_dir / "state.md").read_bytes()
            with self.assertRaisesRegex(nav.NavigatorError, "static-checks accepts only done or blocked"):
                complete(self.run_dir, state, dict(DONE, outcome="repeat"))
            self.assertEqual((self.run_dir / "state.md").read_bytes(), before)

    def test_verify_entry_names_the_static_checks_auto_fix(self):
        """The planning-stage Improve completions pass through the hook; complete enters both lint stages."""
        self.commit({"a.py": "x = 1\n"})
        self.start()
        with self.patched_env():
            state = drive(self.run_dir, "static-checks", edit=self.edit_item, edit_at="document")
            self.assertTrue((self.run_dir / "lint" / "items" / "W1.md").is_file())
            action = nav.current_action(state)["id"]
            record = store.read_record(self.run_dir / "lint" / (action + ".md"))
            self.assertEqual(record["applied"], ["a.py"])
            self.assertEqual((self.repo / "a.py").read_text(), "x = 1\ny = 2\n")
            self.assertIn("AUTO-FIX APPLIED", nav.render(CORE, self.run_dir, state))
            state = drive(self.run_dir, "verify")
            verify = store.read_record(self.run_dir / "lint" / (nav.current_action(state)["id"] + ".md"))
        self.assertEqual(verify["stage"], "verify")
        self.assertIn("ShipLoop auto-fixed a.py", verify["block"])

    def test_an_improve_completion_that_starts_a_work_item_captures_its_base(self):
        """The end review may add work items; its completion starts the next item's inner loop."""
        self.commit({"a.py": "x = 1\n"})
        self.start()
        with self.patched_env():
            state = drive(self.run_dir, "carry-forward")
            action = nav.current_action(state)["id"]
            complete(self.run_dir, state)
            state = store.read_record(self.run_dir / "state.md")
            self.assertEqual(state["active_improve"]["action_id"], action)
            updated = nav.finish_improve(
                state, action, {"summary": "Synthetic Improve.", "review_refs": ["synthetic://r"],
                                "check_refs": ["synthetic://c"]},
                dict(DONE, work_items=[{"id": "W2", "title": "Review follow-up"}]))
            writes, payload = nav._lint_transition(CORE, self.run_dir, state, updated)
        self.assertEqual(nav.current_stage(updated), "select-work")
        self.assertIn("lint/items/W2.md", writes)
        self.assertIsNone(payload)

    def test_unconsumed_journal_shows_on_packets_that_skip_the_lint_block(self):
        self.commit({"a.py": "x = 1\n"})
        self.start()
        state = store.read_record(self.run_dir / "state.md")
        journal = self.run_dir / "lint" / "pending-nav-x.patch"
        journal.parent.mkdir(parents=True)
        journal.write_text("--- a/a.py\n+++ b/a.py\n")
        paused = nav.control(state, "pause", "user stop")
        self.assertIn("UNCONSUMED LINT JOURNAL", nav.render(CORE, self.run_dir, paused))

    def test_verify_entry_repeats_an_unchanged_result_word_for_word(self):
        self.commit({"a.py": "x = 1\n"})
        self.start("report")
        with self.patched_env():
            state = drive(self.run_dir, "static-checks", edit=lambda: self.edit({"a.py": "x = 1  # lint\n"}))
            record = store.read_record(self.run_dir / "lint" / (nav.current_action(state)["id"] + ".md"))
            calls = len(self.logged())
            packet = complete(self.run_dir, state)
        self.assertIn("no linter ran. Still, word for word from that record:", packet)
        self.assertIn(record["result_line"], packet)
        self.assertEqual(len(self.logged()), calls)

    def test_mode_off_runs_no_linter_but_records_the_change_inventory(self):
        """lint=off stops linters and auto-fix; the item base and inventory still serve the quality loop."""
        self.commit({"a.py": "x = 1\n"})
        self.start("off")
        with self.patched_env(), \
                mock.patch.object(lint, "lint_pass", side_effect=AssertionError("no lint pass")):
            state = drive(self.run_dir, "static-checks", edit=self.edit_item)
        self.assertEqual(self.logged(), [])
        action = nav.current_action(state)["id"]
        self.assertTrue((self.run_dir / "lint" / "items" / "W1.md").is_file())
        self.assertFalse((self.run_dir / "lint" / (action + ".md")).exists())
        record = store.read_record(self.run_dir / lint.inventory_path(action))
        self.assertEqual(record["status"], "ok")
        self.assertEqual([(row["status"], row["path"]) for row in record["rows"]], [("M", "a.py")])
        packet = nav.render(CORE, self.run_dir, state)
        self.assertIn("ShipLoop lint: off (run option lint=off)", packet)
        self.assertIn("Change inventory for W1", packet)
        self.assertIn("  M a.py", packet)

    def test_a_saved_run_without_the_key_is_refused_not_read_as_off(self):
        # One supported version: an older run without a lint option is refused, never defaulted.
        self.commit({"a.py": "x = 1\n"})
        self.start(None)
        state = store.read_record(self.run_dir / "state.md")
        self.assertEqual(state["lint"], "off")  # new runs always record it
        del state["lint"]
        (self.run_dir / "state.md").write_text(store.dumps(state, "ShipLoop navigator state"))
        before = (self.run_dir / "state.md").read_bytes()
        with self.assertRaisesRegex(nav.NavigatorError, "no recorded lint option.*fresh --run-dir"):
            nav.validate(store.read_record(self.run_dir / "state.md"))
        self.assertEqual((self.run_dir / "state.md").read_bytes(), before)

    def test_hook_exception_never_fails_complete(self):
        self.commit({"a.py": "x = 1\n"})
        self.start()
        with self.patched_env():
            state = drive(self.run_dir, "skill-validate", edit=self.edit_item, edit_at="document")
            expected = nav.apply(state, nav.current_action(state)["id"], DONE)
            with mock.patch.object(lint, "lint_pass", side_effect=SystemExit(2)):
                packet = complete(self.run_dir, state)
        saved = store.read_record(self.run_dir / "state.md")
        # Only the transition changed state: identical except the fresh action ID.
        issued = nav.current_action(saved)["id"]
        self.assertEqual(json.loads(json.dumps(saved).replace(issued, "NEW")),
                         json.loads(json.dumps(expected).replace(nav.current_action(expected)["id"], "NEW")))
        self.assertEqual(nav.current_stage(saved), "static-checks")
        self.assertIn("could not run: SystemExit: 2", packet)
        self.assertEqual((self.repo / "a.py").read_text(), "x = 1\ny = 2  # fixme\n")

    def test_unconsumed_journal_is_surfaced(self):
        journal = self.run_dir / "lint" / "pending-nav-x.patch"
        journal.parent.mkdir(parents=True)
        journal.write_text("--- a/a.py\n+++ b/a.py\n")
        lines = lint.render_lines(self.run_dir, "nav-y", stage="implement", run_option="fix",
                                  repo=str(self.repo), command="shiploop")
        self.assertTrue(any(line.startswith("UNCONSUMED LINT JOURNAL") and "pending-nav-x.patch" in line
                            for line in lines), lines)

    def test_large_blocks_are_paged_losslessly(self):
        self.commit({"a.py": "x = 1\n"})
        self.base()
        self.edit({"a.py": "".join("v%d = %d  # lint\n" % (n, n) for n in range(400))})
        payload = self.run_pass(mode="report")
        for relative, text in lint.record_writes(payload).items():
            store.atomic_write_text(self.run_dir / relative, text)
        lines = lint.render_lines(self.run_dir, "A1", stage="static-checks", run_option="report",
                                  repo=str(self.repo), command=str(CLI))
        parts = lint._parts(payload["block"])
        self.assertGreater(len(parts), 1)
        self.assertIn("Lint block part 1 of " + str(len(parts)), "\n".join(lines))
        shown = []
        for number in range(1, len(parts) + 1):
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = lint.main(CORE, ["--run-dir", str(self.run_dir), "--action", "A1", "--show",
                                        "--part", str(number)])
            self.assertEqual(code, 0)
            shown.append(buffer.getvalue().split("\n", 1)[1])
        self.assertEqual("".join(shown), payload["block"])


class DiscoveredLinterTests(Fixture):
    """Linters the repository configures run on the changed files of their type."""

    def test_eslint_runs_from_node_modules_and_gates_only_changed_lines(self):
        self.commit({".gitignore": "node_modules/\n", "eslint.config.js": "export default []\n",
                     "a.js": "one\nLINTME old\n"})
        write_tool(self.repo / "node_modules" / ".bin", "eslint")
        self.base()
        self.edit({"a.js": "one\nLINTME old\nLINTME new\n"})
        payload = self.run_pass(mode="report")
        block = payload["block"]
        # Fixtures have no node on PATH, so eslint is this file's only coverage.
        self.assertIn("- a.js: linted by eslint (eslint.config.js)", block)
        self.assertEqual([(row["path"], row["line"]) for row in payload["gating"]], [("a.js", 3)])
        self.assertTrue(payload["gating"][0]["id"].startswith("L"))
        self.assertEqual(payload["counts"]["unattributed"], 1)
        eslint = [argv for argv in self.logged() if argv[0] == "eslint"]
        self.assertEqual(len(eslint), 1)
        self.assertIn("./a.js", eslint[0])
        self.assertEqual(eslint[0][-1], "cwd=" + str(self.repo))

    def test_prettier_reports_the_regions_it_would_rewrite(self):
        self.commit({".prettierrc": "{}\n", "a.md": "one\n"})
        write_tool(self.bin, "prettier")
        self.base()
        self.edit({"a.md": "one\ntwo   \n"})
        payload = self.run_pass(mode="report")
        # git diff --check reports the trailing whitespace too; prettier adds its own finding.
        prettier = [row for row in payload["gating"] if row["message"].startswith("prettier: ")]
        self.assertEqual([(row["path"], row["line"]) for row in prettier], [("a.md", 2)])
        self.assertIn("formatting differs from prettier output on lines 2-2; run prettier --write a.md",
                      prettier[0]["message"])

    def test_tsc_project_findings_count_only_in_changed_files(self):
        self.commit({"tsconfig.json": "{}\n", "src/a.ts": "let a = 1;\n", "src/b.ts": "let b = TSBAD;\n"})
        write_tool(self.bin, "tsc")
        self.base()
        self.edit({"src/a.ts": "let a = 1;\nlet c = TSBAD;\n"})
        payload = self.run_pass(mode="report")
        self.assertEqual([(row["path"], row["line"]) for row in payload["gating"]], [("src/a.ts", 2)])
        self.assertNotIn("src/b.ts:", "\n".join(row["path"] for row in payload["gating"]))

    def test_configured_but_missing_linter_is_recommended_and_never_fetched(self):
        self.commit({".yamllint": "extends: default\n", "x.yaml": "a: 1\n"})
        self.base()
        self.edit({"x.yaml": "a: 2\n"})
        payload = self.run_pass(mode="report")
        self.assertIn("Recommended: the repository configures yamllint (.yamllint), but yamllint not found",
                      payload["block"])
        self.assertIn("yamllint not run: yamllint not found", payload["block"])
        self.assertEqual(payload["gating"], [])

    def test_actionlint_runs_whenever_it_is_on_path(self):
        self.commit({".github/workflows/ci.yml": "on: push\n"})
        write_tool(self.bin, "actionlint")
        self.base()
        self.edit({".github/workflows/ci.yml": "on: push\nBAD: 1\n"})
        payload = self.run_pass(mode="report")
        self.assertEqual([(row["path"], row["line"]) for row in payload["gating"]],
                         [(".github/workflows/ci.yml", 2)])
        self.assertIn("linted by actionlint (on PATH)", payload["block"])

    def test_npm_lint_runs_only_for_changed_files_no_other_linter_covers(self):
        self.commit({"package.json": json.dumps({"scripts": {"lint": "stub"}}), "notes.txt": "fine\n",
                     "a.py": "x = 1\n"})
        write_tool(self.bin, "npm")
        self.base()
        self.edit({"a.py": "x = 2\n"})
        self.run_pass(mode="report")
        self.assertFalse([argv for argv in self.logged() if argv[0] == "npm"])
        self.edit({"notes.txt": "fine\nBAD\n"})
        payload = self.run_pass(mode="report")
        self.assertEqual([argv[1:4] for argv in self.logged() if argv[0] == "npm"], [["run", "--silent", "lint"]])
        self.assertEqual([(row["path"], row["line"]) for row in payload["gating"]], [("notes.txt", 2)])
        self.assertIn("- notes.txt: no file-type linter; git diff --check; npm run lint ran (exit 1); it does "
                      "not say which files it covers", payload["block"])

    def test_finding_ids_survive_a_line_shift(self):
        self.commit({"a.py": "x = 1\n"})
        self.base()
        self.edit({"a.py": "x = 1\ny = 2  # lint\n"})
        first = self.run_pass(mode="report")["gating"][0]["id"]
        self.edit({"a.py": "# header\nx = 1\ny = 2  # lint\n"})
        second = self.run_pass(mode="report")["gating"]
        self.assertIn(first, [row["id"] for row in second])


class GateTests(Fixture):
    """implement's done passes through the lint gate."""

    def start(self, option: str = "fix") -> dict:
        nav.save(self.run_dir, nav.new_state(str(self.repo), "Lint gate fixture.", improve_skill="",
                                             lint_option=option))
        with self.patched_env():
            return drive(self.run_dir, "implement")

    def patched_env(self):
        return mock.patch.dict(os.environ, {"PATH": str(self.bin) + ":" + SYSTEM_PATH, "STUB_LOG": str(self.log)})

    def test_new_finding_refuses_done_until_fixed_or_waived(self):
        self.commit({"a.py": "x = 1\n"})
        state = self.start()
        self.edit({"a.py": "x = 1\ny = 2  # lint\n"})
        before = (self.run_dir / "state.md").read_bytes()
        with self.patched_env():
            with self.assertRaises(nav.NavigatorError) as refused:
                complete(self.run_dir, state)
            self.assertEqual((self.run_dir / "state.md").read_bytes(), before)
            text = str(refused.exception)
            self.assertIn("implement is not done while 1 new lint finding on lines this work item changed", text)
            found = re.findall(r"^- (L[0-9a-f]{10}) a\.py:2: ", text, re.M)
            self.assertEqual(len(found), 1, text)
            action = nav.current_action(state)["id"]
            self.assertTrue((self.run_dir / "lint" / (action + ".gate1.md")).is_file())
            packet = nav.render(CORE, self.run_dir, state)
            self.assertIn("Latest implement lint gate (pass 1)", packet)
            self.assertIn("Lint each implementation step (report-only):", packet)
            with self.assertRaisesRegex(nav.NavigatorError, "finding ID the lint gate printed"):
                complete(self.run_dir, state, dict(DONE, lint_waivers=[{"id": "x", "reason": "r"}]))
            complete(self.run_dir, state, dict(DONE, lint_waivers=[{"id": found[0], "reason": "Kept on purpose."}]))
        saved = store.read_record(self.run_dir / "state.md")
        self.assertEqual(nav.current_stage(saved), "test-green")
        # The malformed waiver was refused before any pass ran: two gate passes in all.
        self.assertFalse((self.run_dir / "lint" / (action + ".gate3.md")).exists())
        record = store.read_record(self.run_dir / "lint" / (action + ".gate2.md"))
        self.assertEqual(record["waived"], found)
        self.assertEqual(saved["accepted"][action]["lint_waivers"], [{"id": found[0], "reason": "Kept on purpose."}])

    def test_auto_fix_refuses_once_then_accepts(self):
        self.commit({"a.py": "x = 1\n"})
        state = self.start()
        self.edit({"a.py": "x = 1\ny = 2  # fixme\n"})
        with self.patched_env():
            with self.assertRaisesRegex(nav.NavigatorError, "ShipLoop auto-fixed a.py on lines this work item "
                                                            "changed"):
                complete(self.run_dir, state)
            self.assertEqual((self.repo / "a.py").read_text(), "x = 1\ny = 2\n")
            complete(self.run_dir, state)
        self.assertEqual(nav.current_stage(store.read_record(self.run_dir / "state.md")), "test-green")

    def test_test_green_edits_pass_through_the_same_gate(self):
        self.commit({"a.py": "x = 1\n"})
        state = self.start()
        with self.patched_env():
            complete(self.run_dir, state)  # implement: nothing changed yet
            state = store.read_record(self.run_dir / "state.md")
            self.assertEqual(nav.current_stage(state), "test-green")
            self.edit({"a.py": "x = 1\ny = 2  # lint\n"})  # a fix made during the test loop
            with self.assertRaises(nav.NavigatorError) as refused:
                complete(self.run_dir, state)
            self.assertIn("test-green is not done while 1 new lint finding", str(refused.exception))
            found = re.findall(r"^- (L[0-9a-f]{10}) ", str(refused.exception), re.M)
            complete(self.run_dir, state, dict(DONE, lint_waivers=[{"id": found[0], "reason": "Kept."}]))
        self.assertEqual(nav.current_stage(store.read_record(self.run_dir / "state.md")), "test-refine")

    def test_lint_off_and_non_done_outcomes_run_no_gate(self):
        self.commit({"a.py": "x = 1\n"})
        state = self.start("off")
        self.edit({"a.py": "x = 1\ny = 2  # lint\n"})
        with self.patched_env(), mock.patch.object(lint, "lint_pass", side_effect=AssertionError("no pass")):
            complete(self.run_dir, state)
        self.assertEqual(nav.current_stage(store.read_record(self.run_dir / "state.md")), "test-green")

    def test_blocked_implement_is_not_linted(self):
        self.commit({"a.py": "x = 1\n"})
        state = self.start()
        self.edit({"a.py": "x = 1\ny = 2  # lint\n"})
        with self.patched_env(), mock.patch.object(lint, "lint_pass", side_effect=AssertionError("no pass")):
            complete(self.run_dir, state, dict(DONE, outcome="blocked", blocked_by="external"))

    def test_a_pass_that_cannot_run_never_refuses(self):
        self.commit({"a.py": "x = 1\n"})
        state = self.start()
        with self.patched_env(), mock.patch.object(lint, "lint_pass", side_effect=RuntimeError("boom")):
            complete(self.run_dir, state)
        action = nav.current_action(state)["id"]
        record = store.read_record(self.run_dir / "lint" / (action + ".gate1.md"))
        self.assertEqual(record["kind"], "failure")
        self.assertIn("could not run: RuntimeError: boom", record["block"])

    def test_lint_waivers_are_refused_outside_a_done_implement(self):
        waivers = [{"id": "L0123456789", "reason": "r"}]
        with self.assertRaisesRegex(nav.NavigatorError, "only on a done implement, test-green, regression result"):
            nav._canonical_result(dict(DONE, lint_waivers=waivers), stage="verify")
        with self.assertRaisesRegex(nav.NavigatorError, "only on a done implement, test-green, regression result"):
            nav._canonical_result(dict(DONE, outcome="blocked", blocked_by="external", lint_waivers=waivers), stage="implement")
        self.assertEqual(nav._canonical_result(dict(DONE, lint_waivers=waivers), stage="implement")["lint_waivers"],
                         waivers)


class PromptContractTests(unittest.TestCase):
    def test_test_stages_carry_the_pass_or_stop_loop(self):
        import shiploop_navigator_v3_prompts as guidance
        for stage in ("test-refine", "integration-verify"):
            text = guidance.prompt(stage, delegation=guidance.INLINE)
            self.assertIn("Pass-or-stop loop: this stage is done only when every check it runs passes", text)
            self.assertIn("the same check\nstill failing after 3 genuine fix attempts → outcome blocked", text)
        # test-green and regression run the script-enforced test loop instead.
        for stage in ("verify", "test-green", "regression"):
            self.assertNotIn("Pass-or-stop loop", guidance.prompt(stage, delegation=guidance.INLINE))
        implement = guidance.prompt("implement", delegation=guidance.INLINE)
        self.assertIn("Lint every step: after a step's last edit, run the packet's printed lint command", implement)
        self.assertIn("`lint_waivers`", implement)


class CliTests(Fixture):
    def cli(self, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
        # Host git config (for example git-lfs's global filter on CI runners)
        # must not reach the CLI: workspace start refuses custom filters.
        merged = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
        merged.update(env or {})
        return subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, env=merged)

    def init(self, *extra: str) -> subprocess.CompletedProcess:
        return self.cli("init", "--repo", str(self.repo), "--run-dir", str(self.run_dir / "r"),
                        "--prompt=Lint CLI fixture.", *extra)

    def state(self) -> dict:
        return store.read_record(self.run_dir / "r" / "state.md")

    def test_new_runs_default_to_fix_and_accept_an_explicit_option(self):
        self.assertEqual(self.init().returncode, 0)
        self.assertEqual(self.state()["lint"], "fix")
        other = self.cli("init", "--repo", str(self.repo), "--run-dir", str(self.run_dir / "o"),
                         "--prompt=Other.", "--lint", "off")
        self.assertEqual(other.returncode, 0, other.stderr)
        self.assertEqual(store.read_record(self.run_dir / "o" / "state.md")["lint"], "off")

    def test_lint_mode_needs_an_existing_run_and_a_known_option(self):
        (self.run_dir / "empty").mkdir()
        result = self.cli("lint-mode", "--run-dir", str(self.run_dir / "empty"), "--set", "report")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("lint-mode needs an existing run", result.stderr)
        self.assertFalse((self.run_dir / "empty" / "state.md").exists())
        unknown = self.init("--lint", "strict")
        self.assertNotEqual(unknown.returncode, 0)
        self.assertIn("invalid choice", unknown.stderr)

    def test_lint_mode_changes_the_option_and_is_refused_when_halted(self):
        self.init()
        run = str(self.run_dir / "r")
        result = self.cli("lint-mode", "--run-dir", run, "--set", "report")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.state()["lint"], "report")
        retry = self.init("--lint", "off")
        self.assertNotEqual(retry.returncode, 0)
        self.assertIn("shiploop lint-mode --run-dir", retry.stderr)
        self.cli("halt", "--run-dir", run, "--reason", "user stop")
        refused = self.cli("lint-mode", "--run-dir", run, "--set", "fix")
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("terminal navigator state cannot mutate", refused.stderr)

    def test_workspace_start_forwards_lint_and_refuses_a_changed_retry(self):
        self.commit({"a.py": "x = 1\n"})
        root = Path(self.temp.name) / "workspace"
        args = ("workspace", "start", "--repo", str(self.repo), "--workspace-root", str(root),
                "--prompt", "Lint workspace fixture.")
        started = self.cli(*args, "--lint", "report")
        self.assertEqual(started.returncode, 0, started.stderr)
        self.assertEqual(store.read_record(root / "run" / "state.md")["lint"], "report")
        retry = self.cli(*args, "--lint", "fix")
        self.assertNotEqual(retry.returncode, 0)
        self.assertIn("shiploop lint-mode --run-dir", retry.stderr)
        self.assertEqual(self.cli(*args).returncode, 0)

    def test_lint_verb_exit_codes(self):
        self.commit({"a.py": "x = 1\n"})
        self.init()
        run = str(self.run_dir / "r")
        action = nav.current_action(self.state())["id"]
        env = {"PATH": str(self.bin) + ":" + SYSTEM_PATH}
        wrong = self.cli("lint", "--run-dir", run, "--action", "nav-other", env=env)
        self.assertEqual(wrong.returncode, 3)
        clean = self.cli("lint", "--run-dir", run, "--action", action, env=env)
        self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)
        self.assertIn("ShipLoop never gates on it", clean.stdout)
        self.edit({"a.py": "x = 1  # lint\n"})
        dirty = self.cli("lint", "--run-dir", run, "--action", action, env=env)
        self.assertEqual(dirty.returncode, 1, dirty.stdout + dirty.stderr)
        self.assertIn("Scope is not this work item's", dirty.stdout)
        self.assertTrue((self.run_dir / "r" / "lint" / (action + ".2.md")).is_file())
        self.cli("lint-mode", "--run-dir", run, "--set", "off")
        off = self.cli("lint", "--run-dir", run, "--action", action, env=env)
        self.assertEqual(off.returncode, 3)
        self.assertIn("ShipLoop never gates on this exit code", off.stdout)


if __name__ == "__main__":
    unittest.main()
