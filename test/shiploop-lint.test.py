#!/usr/bin/env python3
"""Hermetic tests for ShipLoop's script-owned advisory lint (phase 1).

Stub ``ruff`` and ``shellcheck`` executables on a temporary PATH stand in for
real tools, so these tests never depend on what the host has installed.
"""
from __future__ import annotations

import atexit
import contextlib
import errno
import io
import json
import os
import re
import select
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest import mock

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills/shiploop"
CLI = PACKAGE / "scripts/shiploop"
sys.path.insert(0, str(PACKAGE / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import shiploop_inner_fixture as inner  # noqa: E402
import shiploop_knowledge_support as knowledge_support  # noqa: E402
import shiploop_lint as lint  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_store as store  # noqa: E402
from shiploop_packet_view import packet_file_named  # noqa: E402

CORE = types.SimpleNamespace(PACKAGE_ROOT=PACKAGE, REF_DIR=PACKAGE / "references")
DONE = {"outcome": "done", "summary": "Synthetic declaration; no work executed."}
# What a blocked result waits on (run-insights plan N5: awaiting replaces blocked_by); an outside service here.
SERVICE_WAIT = {"kind": "service", "service": "the package registry", "check": "true",
                "no_default": "The dependency cannot be installed until the registry is back."}


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

# A controllable "syntax check": fails only on a planted marker, never real JS parsing.
NODE_CHECK_STUB = r'''
import json, os, sys
with open(os.environ["STUB_LOG"], "a") as log:
    log.write(json.dumps(["node"] + sys.argv[1:]) + "\n")
sys.exit(1 if "SYNTAXERR" in open(sys.argv[-1]).read() else 0)
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
    fix_mode = "--fix-dry-run" in argv
    out = []
    for path in files:
        text = open(path).read()
        fixed = text.replace(" FIXME", "") if fix_mode else text
        messages = [{"line": number, "column": 1, "ruleId": "stub/rule", "severity": 2, "message": "stub finding"}
                    for number, line in enumerate(fixed.splitlines(), 1) if "LINTME" in line]
        entry = {"filePath": os.path.abspath(path), "messages": messages}
        if fix_mode and fixed != text:
            entry["output"] = fixed
        out.append(entry)
    print(json.dumps(out))
    sys.exit(1 if any(entry["messages"] for entry in out) else 0)
if name in ("prettier", "black", "gofmt", "clang-format", "terraform"):
    text = sys.stdin.read()
    sys.stdout.write("".join(line.rstrip() + "\n" for line in text.splitlines()))
    sys.exit(0)
if name in ("ktlint", "phpcs", "rubocop"):
    if os.environ.get("STUB_EXIT_OVERRIDE"):
        sys.exit(int(os.environ["STUB_EXIT_OVERRIDE"]))
    suffix = {"ktlint": (".kt", ".kts"), "phpcs": (".php",), "rubocop": (".rb",)}[name]
    found = False
    for path in [arg for arg in argv if arg.endswith(suffix)]:
        for number, line in enumerate(open(path).read().splitlines(), 1):
            if "LINTME" in line:
                print(path + ":" + str(number) + ":1: stub finding")
                found = True
    sys.exit(1 if found else 0)
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
        return lint.lint_pass(self.repo, self.run_dir, action="A1", work_item="W1", stage="document",
                              mode=mode, run_option=mode, base=base, allow_fix=allow_fix,
                              env=env or self.env(), **kwargs)

    def logged(self) -> list:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]


class LintPassTests(Fixture):
    def test_tool_calls_bind_the_original_run_and_preserve_an_injected_runner(self):
        self.commit({"a.py": "x = 1\n"})
        self.base()
        self.edit({"a.py": "x = 2  # lint\n"})
        real = lint.run_argv
        with mock.patch.object(lint, "run_argv", wraps=real) as default:
            report = self.run_pass(mode="report")
        self.assertTrue(report["gating"])
        self.assertGreater(default.call_count, 0)
        for call in default.call_args_list:
            self.assertEqual(call.kwargs["recovery"], lint.capture_io.Recovery(self.run_dir, "A1", "lint"))
        self.assertFalse((self.run_dir / "command-recovery").exists())

        def injected(argv, cwd, timeout, *, input_bytes, env):
            return real(argv, cwd, timeout, input_bytes=input_bytes, env=env)

        with mock.patch.object(lint, "run_argv") as default:
            self.assertTrue(self.run_pass(mode="report", runner=injected)["gating"])
        default.assert_not_called()

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
        self.assertIn("[present at the base; elsewhere in a file changed since the base; L", payload["block"])
        self.assertIn("[new since the base; on a line changed since the base; L", payload["block"])
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

    def test_a_pass_has_no_budget_and_no_file_cap_so_every_changed_file_is_read(self):
        # Owner 2026-10-24: no run caps.  The 120-second pass budget and the 200-file cap are gone: 205 changed files
        # (more than the old cap) are all in scope, and nothing says a budget ran out.
        self.assertFalse(hasattr(lint, "BUDGET_SECONDS") or hasattr(lint, "MAX_FILES"))
        names = ["m" + str(number) + ".py" for number in range(205)]
        self.commit({name: "x = 1\n" for name in names})
        self.base()
        self.edit({name: "y = 2\n" for name in names})
        payload = self.run_pass(mode="report")
        self.assertNotIn("budget", payload["block"])
        self.assertNotIn("-file cap", payload["block"])
        self.assertEqual(payload["counts"]["uncovered"], 0)

    def test_git_plumbing_is_bounded_by_its_own_hang_guards(self):
        seen = []
        real = lint._git

        def spy(top, *args, **kwargs):
            seen.append((args[0], kwargs.get("timeout", lint.GIT_TIMEOUT_SECONDS)))
            return real(top, *args, **kwargs)

        self.commit({"a.py": "x = 1\n", "README.md": "one\n"})
        self.base()
        self.edit({"a.py": "y = 2\n", "README.md": "two\n"})
        with mock.patch.object(lint, "_git", spy):
            self.run_pass(mode="report")
        self.assertTrue(seen)
        guards = (lint.GIT_TIMEOUT_SECONDS, lint.SNAPSHOT_TIMEOUT_SECONDS)
        self.assertTrue(all(timeout in guards for _verb, timeout in seen), seen)
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

    def test_later_verify_entry_is_report_only(self):
        self.commit({"a.py": "x = 1\n"})
        self.base()
        self.edit({"a.py": "y = 2  # fixme\n"})
        payload = self.run_pass(allow_fix=False)
        self.assertIn("auto-fix runs only in ShipLoop's lint gate", payload["block"])
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
            lint.lint_pass(plain, self.run_dir, action="A1", work_item="W1", stage="document",
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
        self.assertIn("Not run by ShipLoop (they may rewrite files or download; the run does not start them, and the handoff lists them for the user):", block)
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
                                 stage="document", mode="fix", run_option="fix",
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
        for after, before in ((timeout, None), (timeout, timeout)):
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
        repeated = lint.unchanged_payload("B1", "document", "W1", "report", payload, prior, "shiploop", self.run_dir)
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


def _packet_file_text(stdout: str) -> str:
    """The complete packet text: the file an active-state head's ``Full packet:``
    line points at, or the stdout itself for a paused/blocked/halted/done print,
    which already carries the full text and prints no such line.
    """
    path = packet_file_named(stdout)
    if path is not None and path.is_file():
        return path.read_text(encoding="utf-8")
    return stdout


# The step plan of every driven run: it changes a.py and adds b.py (owner rules 2026-10-10: each path has an
# expectation, each step lists its skills; inner_fixture.fill adds both).
PATHS = ["a.py", "b.py"]


def complete(run: Path, state: dict, result: dict = DONE, *, loop: bool = True, command: str = "complete") -> str:
    """Submit ``result`` through real dispatch; an inner stage's loop runs through the real runtime unless ``loop`` is
    False (a refusal test that must reach the gate without a receipt, or a result already prepared)."""
    action = nav.current_action(state)["id"]
    stage = nav.current_stage(state)
    if stage == "plan" and result.get("outcome") == "done" and "assumptions" not in result:
        result = dict(result, assumptions=[])
    if stage == "intake":
        result = inner.fixture_intake(state, result)                        # IN1
    if stage == "spec" and result.get("outcome") == "done":
        result = {**inner.fixture_primary(state), **result}                 # run-5 batch F6
    if stage == "test-strategy" and result.get("outcome") == "done":
        result = {**inner.fixture_test_layers(), **result}                  # run-5 batch F1, F3
    if stage == "plan" and result.get("outcome") == "done" and "concerns" not in result:
        queue = result.get("work_items", state["work_items"])
        result = dict(result, concerns=inner.no_concerns_map(
            str(row.get("id")) for row in queue if isinstance(row, dict)))
    if stage == "plan":
        result = inner.fixture_follows(state, result)                       # F3: a work item for each primary one
    if stage == "step-plan" and result.get("outcome") == "done" and "paths" not in result:
        result = dict(result, paths=list(PATHS))
    if loop:
        result = inner.prepare(run, state, result)
    if stage in knowledge_support.knowledge.CLOSES:
        knowledge_support.write(state)
    inbox = run / "inbox"
    inbox.mkdir(exist_ok=True)
    path = inbox / (action + ".md")
    path.write_text(store.dumps(result, "result"))
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        nav.dispatch(CORE, run, state, types.SimpleNamespace(command=command, action=action, result=str(path)))
    return _packet_file_text(buffer.getvalue())


def complete_gated(run: Path, state: dict) -> str:
    """Submit a gate stage as done through the lint gate: resubmit after an auto-fix, waive what remains."""
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
    raise AssertionError("the lint gate kept refusing " + nav.current_stage(state))


def finish_improve(run: Path) -> dict:
    """The Improve stage's complete branch of dispatch (it imports the review): finish the pending child, run the transition hooks, save."""
    state = store.read_record(run / "state.md")
    action = state["active_improve"]["action_id"]
    updated = nav.finish_improve(state, action, {"summary": "Synthetic Improve.", "review_refs": ["synthetic://r"],
                                                 "check_refs": ["synthetic://c"]})
    updated, writes, payload = nav._transition(CORE, run, state, updated)
    nav.save(run, updated, writes)
    nav._lint_finish(run, payload)
    return updated


def settle(run: Path) -> dict:
    """The saved state with any pending Improve child finished."""
    state = store.read_record(run / "state.md")
    while state.get("active_improve"):
        state = finish_improve(run)
    return state


def drive(run: Path, until: str, *, edits: dict | None = None) -> dict:
    """Walk a saved run through real dispatch (so the lint hooks run) to ``until``.

    ``edits`` maps a stage to a callable run just before that stage is completed.  implement writes b.py by default,
    so the item's diff touches code and document is issued (owner decision 7).
    """
    edits = {"implement": lambda: (run.parent / "repo" / "b.py").write_text("z = 1\n"), **(edits or {})}
    state = settle(run)
    for _ in range(200):
        if nav.current_stage(state) == until:
            return state
        stage = nav.current_stage(state)
        if stage in edits:
            edits[stage]()
        if stage in lint.GATE_STAGES:
            complete_gated(run, state)
        else:
            complete(run, state)
        state = settle(run)
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
        self.assertEqual(nav.current_stage(updated), "step-plan")
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

    def test_mode_off_runs_no_linter_but_records_the_item_base(self):
        """lint=off stops linters and auto-fix; the item base is still recorded, since every later gate and the step's
        commit stage read the item's change from it."""
        self.commit({"a.py": "x = 1\n"})
        self.start("off")
        with self.patched_env(), \
                mock.patch.object(lint, "lint_pass", side_effect=AssertionError("no lint pass")):
            state = drive(self.run_dir, "document", edits={"implement": self.edit_item})
        self.assertEqual(self.logged(), [])
        self.assertTrue((self.run_dir / "lint" / "items" / "W1.md").is_file())
        self.assertEqual(list((self.run_dir / "lint").glob("*-inventory.md")), [])  # verify's inventory is retired
        self.assertNotIn("Change inventory", nav.render(CORE, self.run_dir, state))

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
        """The transition's lint hook only captures a new item's base; a capture that fails leaves the base absent and
        the transition stands (the gates then report-only, the commit stage skips with a note)."""
        self.commit({"a.py": "x = 1\n"})
        self.start()
        with self.patched_env():
            state = drive(self.run_dir, "carry-forward")
            action = nav.current_action(state)["id"]
            complete(self.run_dir, state)
            state = store.read_record(self.run_dir / "state.md")
            updated = nav.finish_improve(
                state, action, {"summary": "Synthetic Improve.", "review_refs": ["synthetic://r"],
                                "check_refs": ["synthetic://c"]},
                dict(DONE, work_items=[{"id": "W2", "title": "Review follow-up"}]))
            with mock.patch.object(lint, "capture_base", side_effect=SystemExit(2)):
                writes, payload = nav._lint_transition(CORE, self.run_dir, state, updated)
        self.assertEqual(nav.current_stage(updated), "step-plan")
        self.assertNotIn("lint/items/W2.md", writes)
        self.assertIsNone(payload)

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
        lines = lint.render_lines(self.run_dir, "A1", stage="carry-forward", run_option="report",
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


    def stored_lines(self, edit: dict, *, tools_failed: bool = False, stage: str = "carry-forward") -> tuple:
        """A report-mode pass over ``edit`` (run at a gate stage, document, so its block carries the gate rule), stored
        as the action's own record, and the packet lines ``render_lines`` prints for it at ``stage``, a stage that reads
        that record rather than a gate's: (payload, lines)."""
        self.commit({"a.py": "x = 1\n"})
        self.base()
        self.edit(edit)
        payload = self.run_pass(mode="report")
        if tools_failed:
            payload["counts"]["tool_errors"] = 1
        for relative, text in lint.record_writes(payload).items():
            store.atomic_write_text(self.run_dir / relative, text)
        return payload, lint.render_lines(self.run_dir, "A1", stage=stage, run_option="report", repo=str(self.repo),
                                          command=str(CLI), commands=False)

    def test_a_packet_prints_the_findings_the_verdict_and_the_gate_rule_but_not_the_record_sections(self):
        """Efficiency plan U13 (rev 4 Step 2.2): the scope, coverage, tools, commands and Git plumbing are in the stored
        record, which a command prints whole; the packet keeps what the model acts on."""
        payload, lines = self.stored_lines({"a.py": "x = 1\ny = 2  # lint\n"})
        full = payload["block"]
        packet = "\n".join(lines)
        self.assertEqual(len(lint._parts(full)), 1)
        for section in ("Scope: ", "Coverage:", "Tools on this host: ", "Commands ShipLoop ran (", "Git plumbing for scope ("):
            self.assertIn(section, full)
            self.assertNotIn(section, packet)
        self.assertLess(len(packet), len(full) - 300)
        for kept in ("ShipLoop lint (" + lint.SUPPORTING, "Action A1 | work item", "BEGIN lint data", "Findings (", "END lint data",
                     payload["result_line"], "Rerun after your own edits (report-only): "):
            self.assertIn(kept, packet)
        self.assertIn("Gate: ShipLoop refuses this step's done while a new finding on a line changed since the base", packet)
        # The command the packet prints shows the whole record, through the real CLI path.
        shown = next(line for line in lines if line.startswith("Whole lint record ("))
        command = shown.split("): ", 1)[1]
        self.assertIn("--show --part=1", command)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = lint.main(CORE, ["--run-dir", str(self.run_dir), "--action", "A1", "--show", "--part", "1"])
        self.assertEqual(code, 0)
        self.assertEqual(buffer.getvalue().split("\n", 1)[1], full)

    def test_a_gate_record_prints_the_waiver_shape_and_names_its_pass_in_the_command_that_shows_it(self):
        self.commit({"a.py": "x = 1\n"})
        self.base()
        self.edit({"a.py": "x = 1\ny = 2  # lint\n"})
        payload = lint.lint_pass(self.repo, self.run_dir, action="A1", work_item="W1", stage="implement", mode="report",
                                 run_option="report", base=lint.read_base(self.run_dir, "W1"), allow_fix=False,
                                 env=self.env(), record_name="A1.gate1")
        for relative, text in lint.record_writes(payload).items():
            store.atomic_write_text(self.run_dir / relative, text)
        lines = lint.render_lines(self.run_dir, "A1", stage="implement", run_option="report", repo=str(self.repo),
                                  command=str(CLI), commands=False)
        packet = "\n".join(lines)
        self.assertIn("Latest implement lint gate (pass 1)", packet)
        self.assertIn("lint_waivers as {\"id\": \"<ID>\", \"reason\": \"<why it stays>\"}", packet)
        self.assertNotIn("Git plumbing for scope (", packet)
        self.assertIn("--show --gate=1 --part=1", next(line for line in lines if line.startswith("Whole lint record (")))

    def test_a_pass_whose_tool_failed_and_a_block_of_several_pages_print_whole(self):
        payload, lines = self.stored_lines({"a.py": "x = 1\ny = 2  # lint\n"}, tools_failed=True)
        self.assertIn("Commands ShipLoop ran (", "\n".join(lines))      # a failed tool's output is the diagnosis
        self.assertFalse(any(line.startswith("Whole lint record (") for line in lines))
        self.assertEqual(lint._packet_digest(payload["block"], {"timeouts": 1}), None)
        self.assertEqual(lint._packet_digest("a block of another shape\n", {}), None)
        broken = payload["block"].replace("Findings (", "Findings: (")          # a section whose end is missing is not cut
        self.assertEqual(lint._packet_digest(broken, {}), None)


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
        # prettier is fixable, but this pass is report-only: the fix is previewed, never applied.
        self.assertIn("NOT APPLIED (report-only pass): a.md", payload["block"])
        self.assertEqual((self.repo / "a.md").read_text(), "one\ntwo   \n")

    def test_prettier_fix_is_applied_on_the_lines_this_item_changed(self):
        self.commit({".prettierrc": "{}\n", "a.md": "one\n"})
        write_tool(self.bin, "prettier")
        self.base()
        self.edit({"a.md": "one\ntwo   \n"})
        payload = self.run_pass()
        self.assertEqual((self.repo / "a.md").read_text(), "one\ntwo\n")
        self.assertIn("a.md", payload["applied"])
        # prettier's own finding clears; git diff --check (Tier 0) still reports against the pass's entry
        # snapshot, taken before this fix -- a separate, pre-existing characteristic this change does not alter.
        self.assertFalse([row for row in payload["gating"] if row["message"].startswith("prettier: ")])

    def test_black_fix_is_withheld_when_fixing_is_disabled_this_pass(self):
        self.commit({"pyproject.toml": "[tool.black]\n", "a.py": "x = 1\n"})
        write_tool(self.bin, "black")
        self.base()
        self.edit({"a.py": "x = 1\ny = 2   \n"})
        payload = self.run_pass(mode="report")
        self.assertIn("NOT APPLIED (report-only pass): a.py", payload["block"])
        self.assertEqual((self.repo / "a.py").read_text(), "x = 1\ny = 2   \n")

    def test_gofmt_fix_is_applied_and_findings_no_longer_gate(self):
        self.commit({"go.mod": "module x\n", "a.go": "package main\n"})
        write_tool(self.bin, "gofmt")
        self.base()
        self.edit({"a.go": "package main\nfunc f() {}   \n"})
        payload = self.run_pass()
        self.assertEqual((self.repo / "a.go").read_text(), "package main\nfunc f() {}\n")
        self.assertIn("a.go", payload["applied"])
        self.assertFalse([row for row in payload["gating"] if row["message"].startswith("gofmt: ")])

    def test_clang_format_fix_is_applied(self):
        self.commit({".clang-format": "{}\n", "a.c": "int main() {}\n"})
        write_tool(self.bin, "clang-format")
        self.base()
        self.edit({"a.c": "int main() {}\nint g() {}   \n"})
        payload = self.run_pass()
        self.assertEqual((self.repo / "a.c").read_text(), "int main() {}\nint g() {}\n")
        self.assertIn("a.c", payload["applied"])

    def test_terraform_fmt_fix_is_applied(self):
        self.commit({"a.tf": 'resource "x" "y" {}\n'})
        write_tool(self.bin, "terraform")
        self.base()
        self.edit({"a.tf": 'resource "x" "y" {}\nresource "x" "z" {}   \n'})
        payload = self.run_pass()
        self.assertEqual((self.repo / "a.tf").read_text(), 'resource "x" "y" {}\nresource "x" "z" {}\n')
        self.assertIn("a.tf", payload["applied"])

    def test_ktlint_reports_findings(self):
        self.commit({"a.kt": "fun main() {}\n"})
        write_tool(self.bin, "ktlint")
        self.base()
        self.edit({"a.kt": "fun main() {}\nval x = 1 // LINTME\n"})
        payload = self.run_pass(mode="report")
        self.assertEqual([(row["path"], row["line"]) for row in payload["gating"]], [("a.kt", 2)])

    def test_phpcs_reports_findings(self):
        self.commit({"phpcs.xml": "<ruleset></ruleset>\n", "a.php": "<?php\n"})
        write_tool(self.bin, "phpcs")
        self.base()
        self.edit({"a.php": "<?php\n$x = 1; // LINTME\n"})
        payload = self.run_pass(mode="report")
        self.assertEqual([(row["path"], row["line"]) for row in payload["gating"]], [("a.php", 2)])

    def test_phpcs_fatal_exit_is_a_tool_failure_not_silently_clean(self):
        """PHPCS 3.x's exit 3 is a processing error (bad ruleset, uncaught exception), not a clean scan; it
        must never be read as "no findings"."""
        self.commit({"phpcs.xml": "<ruleset></ruleset>\n", "a.php": "<?php\n"})
        write_tool(self.bin, "phpcs")
        self.base()
        self.edit({"a.php": "<?php\n$x = 1;\n"})
        payload = self.run_pass(mode="report", env=self.env(STUB_EXIT_OVERRIDE="3"))
        self.assertIn("phpcs exited 3", payload["block"])
        self.assertEqual(payload["gating"], [])

    def test_rubocop_reports_findings(self):
        self.commit({".rubocop.yml": "\n", "a.rb": "puts 1\n"})
        write_tool(self.bin, "rubocop")
        self.base()
        self.edit({"a.rb": "puts 1\nx = 1 # LINTME\n"})
        payload = self.run_pass(mode="report")
        self.assertEqual([(row["path"], row["line"]) for row in payload["gating"]], [("a.rb", 2)])

    def test_ruff_and_black_fixes_on_the_same_file_both_apply(self):
        self.commit({"pyproject.toml": "[tool.black]\n", "a.py": "x = 1\n"})
        write_tool(self.bin, "black")
        self.base()
        self.edit({"a.py": "x = 1  # fixme\ny = 2   \n"})
        payload = self.run_pass()
        self.assertEqual((self.repo / "a.py").read_text(), "x = 1\ny = 2\n")
        # One applied entry for a.py, not one per fixer -- a path two fixers both touch must revert once.
        self.assertEqual(payload["applied"].count("a.py"), 1)
        self.assertEqual(payload["patch"].count("--- a/a.py"), 1)  # one consolidated journal entry
        self.assertEqual(payload["block"].count("Revert this file's fix: "), 1)

    def test_eslint_fix_is_applied_via_fix_dry_run(self):
        self.commit({"eslint.config.js": "export default []\n", "a.js": "one\n"})
        write_tool(self.bin, "eslint")
        self.base()
        self.edit({"a.js": "one\nvar x = 1 FIXME\nvar y = 2 LINTME\n"})
        payload = self.run_pass()
        self.assertEqual((self.repo / "a.js").read_text(), "one\nvar x = 1\nvar y = 2 LINTME\n")
        self.assertIn("a.js", payload["applied"])
        self.assertEqual([(row["path"], row["line"]) for row in payload["gating"]], [("a.js", 3)])
        eslint_calls = [argv for argv in self.logged() if argv[0] == "eslint"]
        self.assertEqual(len(eslint_calls), 2)
        self.assertTrue(any("--fix-dry-run" in call for call in eslint_calls))
        self.assertTrue(any("--fix-dry-run" not in call for call in eslint_calls))

    def test_eslint_fix_that_touches_an_unchanged_line_is_withheld(self):
        self.commit({"eslint.config.js": "export default []\n", "a.js": "one FIXME\ntwo\n"})
        write_tool(self.bin, "eslint")
        self.base()
        self.edit({"a.js": "one FIXME\ntwo\nthree\n"})
        payload = self.run_pass()
        self.assertEqual((self.repo / "a.js").read_text(), "one FIXME\ntwo\nthree\n")
        self.assertIn("NOT APPLIED (would change a line this work item did not touch; whole file withheld): "
                      "a.js", payload["block"])

    def test_eslint_fix_is_not_blocked_by_a_pre_existing_syntax_error(self):
        """Mirrors ruff's own baseline comparison: a file node already can't parse never has its otherwise-safe
        eslint fix blamed and withheld for that pre-existing condition."""
        (self.bin / "node").write_text("#!" + sys.executable + "\n" + NODE_CHECK_STUB)
        (self.bin / "node").chmod(0o755)
        self.commit({"eslint.config.js": "export default []\n",
                     "a.js": "// SYNTAXERR already broken\nvar z = 1\n"})
        write_tool(self.bin, "eslint")
        self.base()
        self.edit({"a.js": "// SYNTAXERR already broken\nvar z = 1\nvar x = 1 FIXME\n"})
        payload = self.run_pass()
        self.assertEqual((self.repo / "a.js").read_text(), "// SYNTAXERR already broken\nvar z = 1\nvar x = 1\n")
        self.assertIn("a.js", payload["applied"])

    def test_eslint_fix_is_not_attempted_in_report_mode(self):
        self.commit({"eslint.config.js": "export default []\n", "a.js": "one\n"})
        write_tool(self.bin, "eslint")
        self.base()
        self.edit({"a.js": "one\nvar x = 1 FIXME\n"})
        self.run_pass(mode="report")
        eslint_calls = [argv for argv in self.logged() if argv[0] == "eslint"]
        self.assertEqual(len(eslint_calls), 1)
        self.assertNotIn("--fix-dry-run", eslint_calls[0])

    def test_eslint_and_prettier_fixes_on_the_same_file_both_apply(self):
        self.commit({"eslint.config.js": "export default []\n", ".prettierrc": "{}\n", "a.js": "one\n"})
        write_tool(self.bin, "eslint")
        write_tool(self.bin, "prettier")
        self.base()
        self.edit({"a.js": "one\nvar x = 1 FIXME\nvar y = 2   \n"})
        payload = self.run_pass()
        self.assertEqual((self.repo / "a.js").read_text(), "one\nvar x = 1\nvar y = 2\n")
        # One applied entry for a.js, not one per fixer -- a path two fixers both touch must revert once.
        self.assertEqual(payload["applied"].count("a.js"), 1)
        self.assertEqual(payload["patch"].count("--- a/a.js"), 1)  # one consolidated journal entry
        self.assertEqual(payload["block"].count("Revert this file's fix: "), 1)

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


class CommandCaptureAbortTests(unittest.TestCase):
    def capture_abort(self, process, primary, **kwargs):
        stderr = mock.Mock()
        with mock.patch.object(lint.subprocess, "Popen", return_value=process), \
             contextlib.redirect_stderr(stderr), self.assertRaises(type(primary)) as raised:
            lint.run_argv(["tool"], Path.cwd(), 5, input_bytes=b"original input", **kwargs)
        self.assertIs(raised.exception, primary)
        self.assertEqual(stderr.mock_calls, [])

    @unittest.skipUnless(os.name == "posix", "POSIX child wait and group signal")
    def test_ambiguous_wait_states_skip_signaling(self):
        primary = KeyboardInterrupt("capture aborted")
        for outcome in (ChildProcessError(), OSError("wait failed"), KeyboardInterrupt("wait interrupted"),
                        (4001, 0), (0, 1), (4000, 0x137f)):
            with self.subTest(outcome=outcome):
                process = mock.Mock(pid=4000, returncode=None)
                process.communicate.side_effect = primary
                waitpid = (mock.Mock(side_effect=outcome) if isinstance(outcome, BaseException)
                           else mock.Mock(return_value=outcome))
                with mock.patch.object(lint.signal, "getsignal", return_value=signal.SIG_DFL), \
                     mock.patch.object(lint.os, "waitpid", waitpid), mock.patch.object(lint.os, "killpg") as killpg:
                    self.capture_abort(process, primary)
                waitpid.assert_called_once_with(process.pid, os.WNOHANG)
                killpg.assert_not_called()
                process.poll.assert_not_called()
                process.kill.assert_not_called()
                process.wait.assert_not_called()
                self.assertIsNone(process.returncode)

    @unittest.skipUnless(os.name == "posix", "POSIX child wait and group signal")
    def test_known_returncode_and_nondefault_sigchld_skip_wait_and_signal(self):
        primary = KeyboardInterrupt("capture aborted")
        for code, disposition in ((0, signal.SIG_DFL), (None, lambda *_: None), (None, signal.SIG_IGN)):
            with self.subTest(code=code, disposition=disposition):
                process = mock.Mock(pid=4000, returncode=code)
                process.communicate.side_effect = primary
                with mock.patch.object(lint.signal, "getsignal", return_value=disposition), \
                     mock.patch.object(lint.os, "waitpid") as waitpid, mock.patch.object(lint.os, "killpg") as killpg:
                    self.capture_abort(process, primary)
                waitpid.assert_not_called()
                killpg.assert_not_called()
                process.kill.assert_not_called()
                process.wait.assert_not_called()

    @unittest.skipUnless(os.name == "posix", "POSIX child wait status")
    def test_terminal_wait_status_is_published_without_signaling(self):
        primary = KeyboardInterrupt("capture aborted")
        for status, expected in ((7 << 8, 7), (signal.SIGTERM, -signal.SIGTERM)):
            with self.subTest(status=status):
                process = mock.Mock(pid=4000, returncode=None)
                process.communicate.side_effect = primary
                with mock.patch.object(lint.signal, "getsignal", return_value=signal.SIG_DFL), \
                     mock.patch.object(lint.os, "waitpid", return_value=(process.pid, status)) as waitpid, \
                     mock.patch.object(lint.os, "killpg") as killpg:
                    self.capture_abort(process, primary)
                waitpid.assert_called_once_with(process.pid, os.WNOHANG)
                self.assertEqual(process.returncode, expected)
                killpg.assert_not_called()
                process.kill.assert_not_called()
                process.wait.assert_not_called()

    @unittest.skipUnless(os.name == "posix" and sys.implementation.name == "cpython",
                         "exercise CPython poll with its wait lock held")
    def test_reaped_real_child_with_unpublished_returncode_is_never_signaled(self):
        primary = KeyboardInterrupt("after waitpid before publishing returncode")
        for locked in (False, True):
            with self.subTest(locked=locked), subprocess.Popen(
                    [sys.executable, "-c", ""], start_new_session=True) as process:
                pid, status = os.waitpid(process.pid, 0)
                self.assertEqual((pid, status), (process.pid, 0))
                self.assertIsNone(process.returncode)
                lock = process._waitpid_lock if locked else contextlib.nullcontext()
                with lock:
                    if locked:
                        self.assertIsNone(process.poll())  # ambiguous public poll result
                    with mock.patch.object(process, "communicate", side_effect=primary), \
                         mock.patch.object(process, "poll", wraps=process.poll) as poll, \
                         mock.patch.object(process, "kill") as kill, mock.patch.object(lint.os, "killpg") as killpg, \
                         mock.patch.object(lint.os, "waitpid", wraps=os.waitpid) as waitpid:
                        self.capture_abort(process, primary)
                    waitpid.assert_called_once_with(process.pid, os.WNOHANG)
                    poll.assert_not_called()
                    killpg.assert_not_called()
                    kill.assert_not_called()
                    self.assertIsNone(process.returncode)

    @unittest.skipUnless(os.name == "posix", "private POSIX process group")
    def test_live_owned_group_is_stopped_and_reaped_without_more_capture(self):
        primary = KeyboardInterrupt("capture aborted")
        parent, child = socket.socketpair()
        with parent, child, subprocess.Popen(
                [sys.executable, "-c",
                 "import socket, sys; peer = socket.socket(fileno=int(sys.argv[1])); "
                 "peer.sendall(b'R'); peer.recv(1)", str(child.fileno())],
                start_new_session=True, pass_fds=(child.fileno(),)) as process:
            child.close()
            parent.settimeout(30)  # fixture readiness guard
            try:
                self.assertEqual(parent.recv(1), b"R")
                self.assertEqual((os.getpgid(process.pid), os.getsid(process.pid)), (process.pid, process.pid))
                self.assertNotEqual(process.pid, os.getpgrp())
                real_killpg = os.killpg

                def owned_signal(pgid, sig):
                    self.assertEqual((pgid, sig), (process.pid, signal.SIGKILL))
                    real_killpg(pgid, sig)

                with mock.patch.object(process, "communicate", side_effect=primary) as capture, \
                     mock.patch.object(lint.os, "killpg", side_effect=owned_signal) as killpg, \
                     mock.patch.object(process, "wait", side_effect=subprocess.TimeoutExpired(process.args, 0.2)) as wait:
                    self.capture_abort(process, primary)
                capture.assert_called_once_with(input=b"original input", timeout=5)
                killpg.assert_called_once_with(process.pid, signal.SIGKILL)
                wait.assert_called_once_with(timeout=0.2)
                self.assertEqual(parent.recv(1), b"")
            finally:
                parent.close()
                process.wait(timeout=30)
            self.assertEqual(process.returncode, -signal.SIGKILL)

    @unittest.skipUnless(os.name == "posix", "POSIX child wait and group signal")
    def test_cleanup_failures_preserve_primary_and_do_no_pipe_io(self):
        for primary in (KeyboardInterrupt("capture aborted"), SystemExit(17), RuntimeError("capture failed")):
            for failure in ("signal", "reap"):
                with self.subTest(primary=type(primary).__name__, failure=failure):
                    process = mock.Mock(pid=4000, returncode=None)
                    process.communicate.side_effect = primary
                    process.wait.side_effect = OSError("could not reap")
                    interrupted = KeyboardInterrupt("secondary") if failure == "signal" else None
                    with mock.patch.object(lint.signal, "getsignal", return_value=signal.SIG_DFL), \
                         mock.patch.object(lint.os, "waitpid", return_value=(0, 0)), \
                         mock.patch.object(lint.os, "killpg", side_effect=interrupted) as killpg:
                        self.capture_abort(process, primary)
                    killpg.assert_called_once_with(process.pid, signal.SIGKILL)
                    expected = [mock.call.communicate(input=b"original input", timeout=5)]
                    if failure == "reap":
                        expected.append(mock.call.wait(timeout=0.2))
                    self.assertEqual(process.mock_calls, expected)

    @unittest.skipUnless(os.name == "posix", "POSIX timeout teardown")
    def test_abort_during_timeout_teardown_uses_owned_group_without_retrying_capture(self):
        primary = KeyboardInterrupt("timeout teardown interrupted")
        process = mock.Mock(pid=4000, returncode=None)
        process.communicate.side_effect = [subprocess.TimeoutExpired(["tool"], 5), primary]
        with mock.patch.object(lint.signal, "getsignal", return_value=signal.SIG_DFL), \
             mock.patch.object(lint.os, "waitpid", return_value=(0, 0)), mock.patch.object(lint.os, "killpg") as killpg:
            self.capture_abort(process, primary)
        self.assertEqual(killpg.call_args_list, [mock.call(process.pid, signal.SIGTERM),
                                                mock.call(process.pid, signal.SIGKILL)])
        self.assertEqual(process.mock_calls, [mock.call.communicate(input=b"original input", timeout=5),
                                              mock.call.communicate(timeout=0.2), mock.call.wait(timeout=0.2)])

    @unittest.skipUnless(os.name == "posix", "POSIX recovery exclusion")
    def test_nonempty_input_abort_stays_on_baseline_capture_and_cleanup(self):
        for timed_out in (False, True):
            with self.subTest(timed_out=timed_out), tempfile.TemporaryDirectory() as tmp:
                primary = KeyboardInterrupt("capture aborted")
                process = mock.Mock(pid=4000, returncode=None)
                process.communicate.side_effect = ([subprocess.TimeoutExpired(["tool"], 5), primary]
                                                    if timed_out else primary)
                recovery = lint.capture_io.Recovery(Path(tmp), "A1", "lint")
                with mock.patch.object(lint.subprocess, "Popen", return_value=process) as launch, \
                     mock.patch.object(lint.capture_io, "PipeCapture", side_effect=primary) as capture, \
                     mock.patch.object(lint.capture_io, "close_aborted") as close_aborted, \
                     mock.patch.object(lint.capture_io, "publish") as publish, \
                     mock.patch.object(lint.signal, "getsignal", return_value=signal.SIG_DFL), \
                     mock.patch.object(lint.os, "waitpid", return_value=(0, 0)), \
                     mock.patch.object(lint.os, "killpg") as killpg, self.assertRaises(KeyboardInterrupt) as raised:
                    lint.run_argv(["tool"], Path(tmp), 5, input_bytes=b"original input", recovery=recovery)
                self.assertIs(raised.exception, primary)
                capture.assert_not_called()
                close_aborted.assert_not_called()
                publish.assert_not_called()
                self.assertEqual(list(Path(tmp).iterdir()), [])
                launch.assert_called_once_with(["tool"], cwd=tmp, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE, start_new_session=True)
                expected = [mock.call.communicate(input=b"original input", timeout=5)]
                if timed_out:
                    expected.append(mock.call.communicate(timeout=0.2))
                self.assertEqual(process.mock_calls, [*expected, mock.call.wait(timeout=0.2)])
                self.assertEqual(killpg.call_args_list, [
                    *([mock.call(process.pid, signal.SIGTERM)] if timed_out else []),
                    mock.call(process.pid, signal.SIGKILL),
                ])

    def test_non_posix_abort_preserves_existing_capture_and_timeout_calls(self):
        primary = KeyboardInterrupt("capture aborted")
        for timed_out in (False, True):
            with self.subTest(timed_out=timed_out):
                process = mock.Mock(pid=4000, returncode=None)
                process.communicate.side_effect = ([subprocess.TimeoutExpired(["tool"], 5), primary]
                                                    if timed_out else primary)
                # No POSIX APIs exist on this stand-in.
                with mock.patch.object(lint, "os", types.SimpleNamespace(name="nt", fspath=os.fspath)):
                    self.capture_abort(process, primary, recovery=lint.capture_io.Recovery(Path.cwd(), "A1", "lint"))
                expected = [mock.call.communicate(input=b"original input", timeout=5)]
                if timed_out:
                    expected.extend([mock.call.kill(), mock.call.communicate()])
                self.assertEqual(process.mock_calls, expected)


@unittest.skipUnless(os.name == "posix", "configured POSIX command capture")
class CommandRecoveryTests(unittest.TestCase):
    OUT = b"out\x00\xff\r\n"
    ERR = b"err\x80\x00\n"
    MARKERS = f"import os, signal; os.write(1, {OUT!r}); os.write(2, {ERR!r}); "

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()

    def run_command(self, code, *, timeout=10, input_bytes=b"", run_dir=None):
        recovery = lint.capture_io.Recovery(run_dir or self.root, "nav-fixture", "verify")
        return lint.run_argv([sys.executable, "-B", "-c", code], self.root, timeout,
                             input_bytes=input_bytes, recovery=recovery)

    @contextlib.contextmanager
    def watch_capture(self, before_select):
        """Run the barrier between reads, after any previous bytes were retained."""
        module = lint.capture_io
        default = module.selectors.DefaultSelector
        capture = module.PipeCapture.capture
        current = None

        def observe(reader, **kwargs):
            nonlocal current
            current = reader
            return capture(reader, **kwargs)

        def observing_selector():
            selector = default()
            select_ready = selector.select

            def ready(timeout=None):
                before_select(current)
                return select_ready(timeout)

            selector.select = ready
            return selector

        with mock.patch.object(module.PipeCapture, "capture", observe), \
             mock.patch.object(module.selectors, "DefaultSelector", observing_selector):
            yield

    def abort_after(self, ready, *, code=None, run_dir=None, timeout=10):
        primary = KeyboardInterrupt("primary capture abort")
        captured = []

        def at_barrier(reader):
            if ready(reader):
                captured.append(reader)
                raise primary

        with self.watch_capture(at_barrier), self.assertRaises(KeyboardInterrupt) as raised:
            self.run_command(code or self.MARKERS + "signal.pause()", timeout=timeout, run_dir=run_dir)
        self.assertIs(raised.exception, primary)
        reader, = captured
        self.assertTrue(reader.process.stdout.closed)
        self.assertTrue(reader.process.stderr.closed)
        if reader.process.stdin is not None:
            self.assertTrue(reader.process.stdin.closed)
        self.assertEqual(reader.process.wait(timeout=10), -signal.SIGKILL)
        return reader

    def has_markers(self, reader):
        return (b"".join(reader.chunks["stdout"]), b"".join(reader.chunks["stderr"])) == (self.OUT, self.ERR)

    def attempt(self, root=None):
        attempt, = (self.root if root is None else root).joinpath("command-recovery").iterdir()
        return attempt

    def assert_prefixes(self, attempt, out, err, *, eof=(False, False)):
        self.assertEqual((attempt / "stdout").read_bytes(), out)
        self.assertEqual((attempt / "stderr").read_bytes(), err)
        self.assertEqual(json.loads((attempt / "metadata.json").read_bytes()), {
            "action": "nav-fixture", "operation": "verify", "publication": "complete",
            "streams": {"stdout": {"bytes": len(out), "eof": eof[0]},
                        "stderr": {"bytes": len(err), "eof": eof[1]}},
            "incomplete_capture": not all(eof),
        })

    def test_binary_prefixes_at_capture_barrier_without_abort_io(self):
        stopped = False
        after_abort = []
        read, write = os.read, os.write

        def barrier(reader):
            nonlocal stopped
            stopped = self.has_markers(reader)
            return stopped

        def check_read(fd, size):
            if stopped:
                after_abort.append("read")
            return read(fd, size)

        def check_write(fd, data):
            if stopped and not stat.S_ISREG(os.fstat(fd).st_mode):
                after_abort.append("pipe write")
            return write(fd, data)

        with mock.patch.object(os, "read", side_effect=check_read), \
             mock.patch.object(os, "write", side_effect=check_write):
            self.abort_after(barrier)
        self.assertEqual(after_abort, [])
        self.assert_prefixes(self.attempt(), self.OUT, self.ERR)

    @unittest.skipUnless(hasattr(signal, "pthread_sigmask"), "requires POSIX SIGINT mask control")
    def test_pipe_interrupt_lets_the_child_remove_its_lock_and_exit(self):
        lock = self.root / "workload.lock"
        script = ("import fcntl, time\n"
                  f"path = {str(lock)!r}\n"
                  "with open(path, 'xb') as lock:\n"
                  " fcntl.flock(lock, fcntl.LOCK_EX)\n"
                  f" os.write(1, {self.OUT!r}); os.write(2, {self.ERR!r})\n"
                  " peer.sendall(b'R')\n"
                  " if peer.recv(1) != b'g': sys.exit(1)\n"
                  # Model shutdown work after release, inside the inherited 250 ms grace.
                  " time.sleep(0.1)\n"
                  " os.unlink(path)\n")
        primary = KeyboardInterrupt("runner interrupted during pipe capture")
        for interrupted in (False, True):
            with self.subTest(interrupted=interrupted), self.socket_fixture(script) as (peer, process):
                self.assertEqual(peer.recv(1), b"R")
                self.assertTrue(lock.is_file())
                self.assertEqual(os.getpgid(process.pid), process.pid)
                self.assertNotEqual(process.pid, os.getpgrp())
                released = False

                def interrupt_runner(*_):
                    peer.sendall(b"g")
                    raise primary

                def release(reader):
                    nonlocal released
                    if not released and self.has_markers(reader):
                        released = True
                        if interrupted:
                            signal.raise_signal(signal.SIGINT)
                        else:
                            peer.sendall(b"g")

                def signal_owned_group(pgid, sig):
                    if pgid == process.pid:
                        real_killpg(pgid, sig)

                real_killpg = os.killpg
                previous_handler = signal.signal(signal.SIGINT, interrupt_runner)
                previous_mask = signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGINT})
                try:
                    with mock.patch.object(lint.subprocess, "Popen", return_value=process), \
                         mock.patch.object(os, "killpg", side_effect=signal_owned_group) as killpg, \
                         self.watch_capture(release):
                        if interrupted:
                            with self.assertRaises(KeyboardInterrupt) as raised:
                                self.run_command("unused")
                            self.assertIs(raised.exception, primary)
                        else:
                            self.assertEqual(self.run_command("unused"), ("passed", 0, self.OUT, self.ERR))
                finally:
                    signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
                    signal.signal(signal.SIGINT, previous_handler)
                self.assertTrue(released)
                self.assertEqual(process.returncode, 0)
                self.assertFalse(lock.exists())
                killpg.assert_not_called()
                if interrupted:
                    attempt = self.attempt()
                    self.assert_prefixes(attempt, self.OUT, self.ERR)
                    for path in (attempt.parent, attempt):
                        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
                    for path in attempt.iterdir():
                        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
                else:
                    self.assertFalse((self.root / "command-recovery").exists())

    def test_bound_runner_recovers_through_a_run_alias_but_refuses_a_recovery_symlink(self):
        run = self.root / "runs" / "original"
        run.mkdir(parents=True)
        alias = self.root / "alias"
        alias.symlink_to(run.parent, target_is_directory=True)
        unrelated = self.root / "unrelated"
        unrelated.mkdir()
        sentinel = unrelated / "sentinel"
        sentinel.write_bytes(b"untouched")
        argv = [sys.executable, "-B", "-c", self.MARKERS + "signal.pause()"]
        for substitute in (False, True):
            with self.subTest(substitute=substitute):
                # Use a separate run for the refusal so it starts without an artifact.
                original = run if not substitute else run.with_name("refused")
                original.mkdir(exist_ok=True)
                recovery = original / "command-recovery"
                runner = lint.recovery_runner(alias / original.name, "nav-fixture", "verify")
                primary = KeyboardInterrupt("abort after captured markers")

                def interrupt(reader):
                    if self.has_markers(reader):
                        if substitute:
                            recovery.symlink_to(unrelated, target_is_directory=True)
                        raise primary

                with self.watch_capture(interrupt), self.assertRaises(KeyboardInterrupt) as raised:
                    runner(argv, self.root, 10)
                self.assertIs(raised.exception, primary)
                if substitute:
                    self.assertTrue(recovery.is_symlink())
                    self.assertEqual(list(unrelated.iterdir()), [sentinel])
                    self.assertEqual(sentinel.read_bytes(), b"untouched")
                else:
                    self.assertTrue(recovery.is_dir(), "no recovery in the canonical run")
                    self.assert_prefixes(self.attempt(original), self.OUT, self.ERR)

    def test_normal_tuples_are_byte_exact_including_large_dual_streams(self):
        for status, code, out, err in (("passed", 0, b"", b""), ("failed", 17, self.OUT, self.ERR),
                                        ("passed", 0, self.OUT * 65536, self.ERR * 65536)):
            with self.subTest(status=status, exit=code, size=len(out) + len(err)):
                # Alternate large writes across both pipes and require exact bytes, including invalid UTF-8.
                script = (f"import sys; o, e = sys.stdout.buffer, sys.stderr.buffer\n"
                          f"for _ in range({len(out)//len(self.OUT)}):\n o.write({self.OUT!r}); e.write({self.ERR!r})\n"
                          f"sys.exit({code})")
                self.assertEqual(self.run_command(script), (status, code, out, err))
        self.assertFalse((self.root / "command-recovery").exists())

    def test_empty_input_closes_stdin_but_none_inherits_it(self):
        echo = "import sys; sys.stdout.buffer.write(b'EOF:' + sys.stdin.buffer.read())"
        with (self.root / "inherited").open("w+b") as source:
            source.write(self.OUT)
            source.seek(0)
            # Supply real inherited stdin without changing the test runner's fd 0.
            popen = subprocess.Popen
            def with_inherited_stdin(*args, **kwargs):
                kwargs.setdefault("stdin", source)
                return popen(*args, **kwargs)

            with mock.patch.object(lint.subprocess, "Popen", side_effect=with_inherited_stdin):
                self.assertEqual(self.run_command(echo, input_bytes=b""), ("passed", 0, b"EOF:", b""))
                self.assertEqual(source.tell(), 0)
                self.assertEqual(self.run_command(echo, input_bytes=None), ("passed", 0, b"EOF:" + self.OUT, b""))
        self.assertFalse((self.root / "command-recovery").exists())

    def test_nonempty_input_matches_baseline_for_exit_and_early_closure(self):
        payload = bytes(range(256)) * 8192
        echo = f"import sys; sys.stdout.buffer.write(sys.stdin.buffer.read()); sys.stderr.buffer.write({self.ERR!r})"
        for code, expected in (
            (echo, ("passed", 0, payload, self.ERR)),
            (echo + "; sys.exit(17)", ("failed", 17, payload, self.ERR)),
            ("import os; os.close(0); os.write(1, b'closed')", ("passed", 0, b"closed", b"")),
        ):
            with self.subTest(code=code):
                argv = [sys.executable, "-B", "-c", code]
                self.assertEqual(lint.run_argv(argv, self.root, 10, input_bytes=payload), expected)
                self.assertEqual(self.run_command(code, input_bytes=payload), expected)
        self.assertFalse((self.root / "command-recovery").exists())

    @contextlib.contextmanager
    def socket_fixture(self, script):
        """Supervise a leader and release any pipe holder via the fixture socket."""
        parent, child = socket.socketpair()
        with parent, child:
            parent.settimeout(10)
            process = subprocess.Popen([sys.executable, "-B", "-c",
                                        "import os, signal, socket, sys\n"
                                        "peer = socket.socket(fileno=int(sys.argv[1]))\n" + script,
                                        str(child.fileno())], pass_fds=(child.fileno(),),
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       start_new_session=True, bufsize=0)
            child.close()
            try:
                yield parent, process
            finally:
                parent.close()  # socket EOF releases descendants even if a test assertion failed
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
                process.stdout.close()
                process.stderr.close()

    def test_pipe_eof_does_not_reap_early_or_replace_a_live_leader(self):
        tail = b"from descendant after leader exit"
        with self.socket_fixture("peer.recv(1)\nif os.fork() == 0:\n"
                                 f" peer.sendall(b'R')\n if peer.recv(1): os.write(1, {tail!r})\n"
                                 "os._exit(0)") as (peer, process), contextlib.ExitStack() as events:
            kernel_queue = None
            if not hasattr(os, "waitid"):
                kernel_queue = events.enter_context(contextlib.closing(select.kqueue()))
                kernel_queue.control([select.kevent(process.pid, filter=select.KQ_FILTER_PROC,
                                                    flags=select.KQ_EV_ADD, fflags=select.KQ_NOTE_EXIT)], 0, 0)
            peer.sendall(b"g")
            self.assertEqual(peer.recv(1), b"R")
            if kernel_queue is None:
                deadline = time.monotonic() + 10
                while os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is None:
                    self.assertLess(time.monotonic(), deadline, "leader did not exit")
                    time.sleep(0.01)
            else:
                self.assertEqual(len(kernel_queue.control(None, 1, 10)), 1, "leader did not exit")
            released = []

            def release(reader):
                if not released:
                    self.assertEqual(reader.eof, {"stdout": False, "stderr": False})
                    self.assertIsNone(process.returncode)
                    wait.assert_not_called()
                    poll.assert_not_called()
                    peer.sendall(b"g")
                    released.append(True)

            with mock.patch.object(lint.subprocess, "Popen", return_value=process), \
                 mock.patch.object(process, "poll", wraps=process.poll) as poll, \
                 mock.patch.object(process, "wait", wraps=process.wait) as wait, self.watch_capture(release):
                self.assertEqual(self.run_command("unused"), ("passed", 0, tail, b""))
                wait.assert_called_once()
                poll.assert_not_called()
            self.assertEqual(released, [True])

        with self.socket_fixture("os.close(1)\nos.close(2)\npeer.sendall(b'R')\npeer.recv(1)\nos._exit(23)"
                                 ) as (peer, process):
            wait = process.wait

            def both_pipes_closed(**kwargs):
                self.assertTrue(process.stdout.closed)
                self.assertTrue(process.stderr.closed)
                self.assertEqual(peer.recv(1), b"R")
                self.assertIsNone(process.poll(), "EOF occurred while the leader was still alive")
                peer.sendall(b"g")
                return wait(**kwargs)

            with mock.patch.object(lint.subprocess, "Popen", return_value=process), \
                 mock.patch.object(process, "wait", side_effect=both_pipes_closed) as waiting:
                self.assertEqual(self.run_command("unused"), ("failed", 23, b"", b""))
                waiting.assert_called_once()

    def test_escaped_holder_leaves_one_stream_incomplete(self):
        script = (f"os.write(1, {self.OUT!r})\nos.close(1)\nos.write(2, {self.ERR!r})\n"
                  "if os.fork() == 0:\n"
                  " os.setsid()\n peer.sendall(b'R')\n while peer.recv(1): peer.sendall(b'p')\n os._exit(0)\n"
                  "while True: signal.pause()")
        with self.socket_fixture(script) as (peer, process):
            self.assertEqual(peer.recv(1), b"R")
            with mock.patch.object(lint.subprocess, "Popen", return_value=process):
                self.abort_after(lambda reader: reader.eof["stdout"] and self.has_markers(reader))
            self.assert_prefixes(self.attempt(), self.OUT, self.ERR, eof=(True, False))
            peer.sendall(b"p")
            self.assertEqual(peer.recv(1), b"p")
            peer.shutdown(socket.SHUT_WR)
            self.assertEqual(peer.recv(1), b"")

    def test_timeout_retains_both_streams_through_term_and_kill(self):
        for exits in (True, False):
            with self.subTest(exits_on_term=exits):
                code = ("import os, signal, sys\ndef term(*_):\n os.write(2, b'TERM')\n"
                        + (" sys.exit(9)\n" if exits else "")
                        + f"signal.signal(signal.SIGTERM, term)\nos.write(1, {self.OUT!r})\nsignal.pause()\n"
                          "while True: signal.pause()")
                with mock.patch.object(os, "killpg", wraps=os.killpg) as signals:
                    self.assertEqual(self.run_command(code, timeout=0.7), ("timeout", None, self.OUT, b"TERM"))
                self.assertEqual([call.args[1] for call in signals.call_args_list],
                                 [signal.SIGTERM] if exits else [signal.SIGTERM, signal.SIGKILL])
        self.assertFalse((self.root / "command-recovery").exists())

    def test_abort_during_real_timeout_teardown_retains_continued_capture(self):
        code = ("import os, signal\ndef term(*_): os.write(2, b'TERM')\n"
                f"signal.signal(signal.SIGTERM, term)\nos.write(1, {self.OUT!r})\nwhile True: signal.pause()")
        with mock.patch.object(os, "killpg", wraps=os.killpg) as signals:
            self.abort_after(lambda reader: b"".join(reader.chunks["stderr"]) == b"TERM",
                             code=code, timeout=0.7)
        self.assertEqual([call.args[1] for call in signals.call_args_list], [signal.SIGTERM, signal.SIGKILL])
        self.assert_prefixes(self.attempt(), self.OUT, b"TERM")

    def test_storage_short_writes_and_failures_preserve_capture_abort(self):
        mkdir, write, op = os.mkdir, os.write, os.open
        for fault in ("short", "denied", "zero", "ENOSPC", "interrupted", "symlink"):
            with self.subTest(fault=fault):
                root = self.root / fault
                root.mkdir()
                unrelated = root / "unrelated"
                unrelated.mkdir()
                sentinel = unrelated / "sentinel"
                sentinel.write_bytes(b"untouched")
                if fault == "symlink":
                    (root / "command-recovery").symlink_to(unrelated)
                metadata_fd = None
                writes = []

                def create(name, *args, **kwargs):
                    if fault == "denied" and name == "command-recovery":
                        raise PermissionError(errno.EACCES, "fixture denial")
                    return mkdir(name, *args, **kwargs)

                def open_file(name, *args, **kwargs):
                    nonlocal metadata_fd
                    fd = op(name, *args, **kwargs)
                    if name == ".metadata.tmp":
                        metadata_fd = fd
                    return fd

                def store(fd, data):
                    if not stat.S_ISREG(os.fstat(fd).st_mode):
                        return write(fd, data)
                    writes.append((fd, len(data)))
                    if fault == "zero":
                        return 0
                    if fault == "ENOSPC" and len(writes) == 2:
                        raise OSError(errno.ENOSPC, "fixture disk full")
                    if fault == "interrupted" and fd == metadata_fd:
                        # Interrupt after a real partial metadata write.
                        write(fd, data[:1])
                        raise KeyboardInterrupt("secondary publication abort")
                    return write(fd, data[:2])

                with mock.patch.object(os, "mkdir", side_effect=create), \
                     mock.patch.object(os, "open", side_effect=open_file), \
                     mock.patch.object(os, "write", side_effect=store):
                    self.abort_after(self.has_markers, run_dir=root)
                self.assertEqual(list(unrelated.iterdir()), [sentinel])
                self.assertEqual(sentinel.read_bytes(), b"untouched")
                if fault == "short":
                    self.assertGreater(len(writes), 3)
                    self.assert_prefixes(self.attempt(root), self.OUT, self.ERR)
                elif fault in ("zero", "ENOSPC", "interrupted"):
                    attempt = self.attempt(root)
                    self.assertFalse((attempt / "metadata.json").exists())
                    partial = attempt / (".metadata.tmp" if fault == "interrupted" else "stdout")
                    self.assertEqual(len(partial.read_bytes()), {"zero": 0, "ENOSPC": 2, "interrupted": 1}[fault])
                else:
                    self.assertFalse(writes)
                    self.assertFalse(list((root / "command-recovery").glob("*/metadata.json")))


class InvokerLogTests(unittest.TestCase):
    """A log file is written only when a report cites it: stderr is quoted inline, stdout only when it is a noted copy."""

    def run_tool(self, logs: Path, **kw):
        runner = lambda argv, cwd, timeout, input_bytes=b"", env=None: ("ok", 0, b"out\n", b"")  # noqa: E731
        invoker = lint._Invoker(logs, logs, "t", {}, tool_timeout=10.0, clock=time.monotonic, runner=runner)
        invoker.run(["tool"], what="x", **kw)
        return sorted(path.name for path in logs.iterdir())

    def test_no_stderr_log_and_a_stdout_log_only_for_a_noted_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(self.run_tool(Path(temporary)), [])
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(self.run_tool(Path(temporary), stdout_note="fixed source"), ["t-1.out"])


class GateTests(Fixture):
    """implement's (every step's), test's and document's done, and the step review's import, pass through the lint
    gate."""

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
            self.assertIn("implement is not done while 1 new lint finding on lines this step changed", text)
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
        # Accepted: the step's test stage is next; its review follows its document stage (design T section 8).
        self.assertIsNone(saved["active_improve"])
        self.assertEqual(nav.current_stage(saved), "test")
        # The malformed waiver was refused before any pass ran: two gate passes in all.
        self.assertFalse((self.run_dir / "lint" / (action + ".gate3.md")).exists())
        record = store.read_record(self.run_dir / "lint" / (action + ".gate2.md"))
        self.assertEqual(record["waived"], found)
        self.assertEqual(saved["accepted"][action]["lint_waivers"], [{"id": found[0], "reason": "Kept on purpose."}])

    def check_lint_refusal(self, option: str) -> str:
        """The check's refusal for one new finding under lint ``option``; the file is left as it was."""
        self.commit({"a.py": "x = 1\n"})
        state = self.start(option)
        self.edit({"a.py": "x = 1\ny = 2  # lint\n"})
        with self.patched_env():
            with self.assertRaises(nav.NavigatorError) as refused:
                complete(self.run_dir, state, command="check")
        text = str(refused.exception)
        self.assertIn("implement is not done while 1 new lint finding", text)
        self.assertEqual((self.repo / "a.py").read_text(), "x = 1\ny = 2  # lint\n")
        return text

    def test_in_fix_mode_the_checks_lint_refusal_names_lint_fix_and_edits_nothing(self):
        """D2 (phases B and C plan): the check never edits a file, so where the run's lint option is fix its refusal names
        the advisory verb that applies the gate's own fixes."""
        text = self.check_lint_refusal("fix")
        action = nav.current_action(store.read_record(self.run_dir / "state.md"))["id"]
        self.assertIn("lint --run-dir=" + str(self.run_dir) + " --action=" + action + " --fix", text)

    def test_under_lint_report_the_checks_lint_refusal_names_no_fix(self):
        self.assertNotIn("--fix", self.check_lint_refusal("report"))

    def test_complete_that_takes_the_checks_yes_runs_no_lint_pass(self):
        """D2: a matching yes leaves complete nothing to fix, so it runs no lint pass at all (fix mode included)."""
        self.commit({"a.py": "x = 1\n"})
        state = self.start("fix")
        self.edit({"a.py": "x = 1\ny = 2\n"})
        with self.patched_env():
            result = inner.prepare(self.run_dir, state, DONE)
            complete(self.run_dir, state, result, loop=False, command="check")
            with mock.patch.object(lint, "lint_pass", side_effect=AssertionError("no pass")):
                complete(self.run_dir, state, result, loop=False)
        saved = store.read_record(self.run_dir / "state.md")
        # Accepted: the step's test stage is next; its review follows its document stage (design T section 8).
        self.assertIsNone(saved["active_improve"])
        self.assertEqual(nav.current_stage(saved), "test")

    def test_every_implement_step_is_gated(self):
        """Owner decision 4 (2026-10-10): the lint gate runs on every implement step, not only the last; a finding a
        later step resolves is waived at the earlier step (X5, e8_lint_steps.py, was the import a later step uses).
        Each step is gated on the lines it changed since its own base (design T section 8: a step's iteration starts
        from the commit the step before it left), so S1's waived line, committed with S1, is not S2's finding."""
        self.commit({"a.py": "x = 1\n"})
        nav.save(self.run_dir, nav.new_state(str(self.repo), "Lint gate fixture.", improve_skill="",
                                             lint_option="fix"))
        steps = [{"id": "S1", "task": "Add the helper.", "paths": ["a.py"]},
                 {"id": "S2", "task": "Use it.", "paths": ["a.py"]}]
        with self.patched_env():
            state = drive(self.run_dir, "step-plan")
            complete(self.run_dir, state, dict(DONE, steps=steps, test_commands=[],
                                               test_commands_na="Synthetic fixture.", paths=["a.py"]))
            state = drive(self.run_dir, "implement")
            self.edit({"a.py": "x = 1\ny = 2  # lint\n"})
            with self.assertRaises(nav.NavigatorError) as refused:
                complete(self.run_dir, state)  # S1 is gated although it is not the last step
            self.assertIn("implement is not done while 1 new lint finding", str(refused.exception))
            # The gate sentence the lint pass prints says so too (it said "only the item's last step is gated: an
            # earlier step's findings are reported without auto-fix": false since this decision, U11).
            block = store.read_record(self.run_dir / "lint" / (nav.current_action(state)["id"] + ".gate1.md"))["block"]
            self.assertIn("Gate: ShipLoop refuses this step's done while a new finding on a line changed since the "
                          "base remains.", block)
            self.assertNotIn("last step is gated", block)
            self.assertNotIn("without auto-fix", block)
            found = re.findall(r"^- (L[0-9a-f]{10}) ", str(refused.exception), re.M)
            complete(self.run_dir, state, dict(DONE, lint_waivers=[{"id": found[0], "reason": "S2 resolves it."}]))
            state = drive(self.run_dir, "implement")  # S1's test, document and review, then S2
            self.assertEqual(nav.step_view(state, "W1").step["id"], "S2")
            self.edit({"a.py": "x = 1\ny = 2  # lint\nz = 3  # lint\n"})
            with self.assertRaises(nav.NavigatorError) as refused:
                complete(self.run_dir, state)  # S2 is gated on its own line, and only on it
            self.assertIn("implement is not done while 1 new lint finding", str(refused.exception))
            self.assertRegex(str(refused.exception), r"(?m)^- L[0-9a-f]{10} a\.py:3: ")
            self.edit({"a.py": "x = 1\ny = 2\nz = 3\n"})
            complete(self.run_dir, state)
        self.assertEqual(nav.current_stage(settle(self.run_dir)), "test")
    def test_auto_fix_refuses_once_then_accepts(self):
        self.commit({"a.py": "x = 1\n"})
        state = self.start()
        self.edit({"a.py": "x = 1\ny = 2  # fixme\n"})
        with self.patched_env():
            with self.assertRaisesRegex(nav.NavigatorError, "ShipLoop auto-fixed a.py on lines this step "
                                                            "changed"):
                complete(self.run_dir, state)
            self.assertEqual((self.repo / "a.py").read_text(), "x = 1\ny = 2\n")
            complete(self.run_dir, state)
        self.assertEqual(nav.current_stage(settle(self.run_dir)), "test")

    def test_prettier_auto_fix_refuses_once_then_accepts(self):
        self.commit({".prettierrc": "{}\n", "a.md": "one\n"})
        write_tool(self.bin, "prettier")
        state = self.start()
        self.edit({"a.md": "one\ntwo   \n"})
        with self.patched_env():
            with self.assertRaisesRegex(nav.NavigatorError, "ShipLoop auto-fixed a\\.md on lines this step "
                                                            "changed"):
                complete(self.run_dir, state)
            self.assertEqual((self.repo / "a.md").read_text(), "one\ntwo\n")
            complete(self.run_dir, state)
        self.assertEqual(nav.current_stage(settle(self.run_dir)), "test")

    def test_eslint_auto_fix_refuses_once_then_accepts(self):
        self.commit({"eslint.config.js": "export default []\n", "a.js": "one\n"})
        write_tool(self.bin, "eslint")
        state = self.start()
        self.edit({"a.js": "one\nvar x = 1 FIXME\n"})
        with self.patched_env():
            with self.assertRaisesRegex(nav.NavigatorError, "ShipLoop auto-fixed a\\.js on lines this step "
                                                            "changed"):
                complete(self.run_dir, state)
            self.assertEqual((self.repo / "a.js").read_text(), "one\nvar x = 1\n")
            complete(self.run_dir, state)
        self.assertEqual(nav.current_stage(settle(self.run_dir)), "test")

    def test_test_stage_edits_pass_through_the_same_gate(self):
        """test-green's gate moved to the test stage (2026-10-10): a fix made while the tests run is gated too."""
        self.commit({"a.py": "x = 1\n"})
        state = self.start()
        with self.patched_env():
            self.edit({"b.py": "z = 1\n"})
            complete(self.run_dir, state)
            state = settle(self.run_dir)
            self.assertEqual(nav.current_stage(state), "test")
            self.edit({"a.py": "x = 1\ny = 2  # lint\n"})  # a fix made during the test loop
            with self.assertRaises(nav.NavigatorError) as refused:
                complete(self.run_dir, state)
            self.assertIn("test is not done while 1 new lint finding", str(refused.exception))
            found = re.findall(r"^- (L[0-9a-f]{10}) ", str(refused.exception), re.M)
            complete(self.run_dir, state, dict(DONE, lint_waivers=[{"id": found[0], "reason": "Kept."}]))
        self.assertEqual(nav.current_stage(settle(self.run_dir)), "document")
    def test_document_is_gated_on_the_lines_it_changed_and_only_on_them(self):
        """Design T §8.2a (2b-4b): verify's lint gate moves into the step. Document's done is gated on the lines document
        changed since it began, so a finding implement waived is not document's, and one document adds is refused until
        it is fixed or waived."""
        self.commit({"a.py": "x = 1\n"})
        state = self.start()
        with self.patched_env():
            self.edit({"a.py": "x = 1\ny = 2  # lint\n"})        # implement's finding: complete_gated waives it
            state = drive(self.run_dir, "document", edits={"implement": lambda: None})
            self.edit({"b.py": "z = 1\nw = 4  # lint\n"})        # document's own edit
            with self.assertRaises(nav.NavigatorError) as refused:
                complete(self.run_dir, state)
            text = str(refused.exception)
            self.assertIn("document is not done while 1 new lint finding on lines the document stage changed", text)
            self.assertRegex(text, r"(?m)^- L[0-9a-f]{10} b\.py:2: ")
            self.assertNotRegex(text, r"(?m)^- L[0-9a-f]{10} a\.py:")
            self.edit({"b.py": "z = 1\nw = 4\n"})
            complete(self.run_dir, state)
        self.assertEqual(store.read_record(self.run_dir / "state.md")["active_improve"]["stage"], "document")

    def test_a_step_reviews_edits_are_gated_at_its_import_on_the_lines_the_review_changed(self):
        """Design T §8.2a (2b-4b): the step review's import lints the review's own edits (since its bind snapshot) before
        ShipLoop reruns the step's commands and commits the step."""
        import shiploop_improve_changes as improve_changes
        self.commit({"a.py": "x = 1\n"})
        self.start()
        with self.patched_env():
            state = drive(self.run_dir, "document")
            complete(self.run_dir, state)
            state = store.read_record(self.run_dir / "state.md")
            child = state["active_improve"]
            self.assertEqual(child["stage"], "document")
            for relative, text in improve_changes.bind_writes(self.run_dir, self.repo, child["action_id"]).items():
                store.atomic_write_text(self.run_dir / relative, text)
            self.edit({"a.py": "x = 1\ny = 2  # lint\n"})        # the review's edit
            receipt = {"no_commit": nav.STEP_REVIEW_NO_COMMIT}
            with self.assertRaises(nav.NavigatorError) as refused:
                nav._improve_change_gate(CORE, self.run_dir, state, child["action_id"], child, receipt)
            text = str(refused.exception)
            self.assertIn("step review is not done while 1 new lint finding on lines this review changed", text)
            self.assertRegex(text, r"(?m)^- L[0-9a-f]{10} a\.py:2: ")
            self.edit({"a.py": "x = 1\ny = 2\n"})
            nav._improve_change_gate(CORE, self.run_dir, state, child["action_id"], child, receipt)

    def test_lint_off_and_non_done_outcomes_run_no_gate(self):
        self.commit({"a.py": "x = 1\n"})
        state = self.start("off")
        self.edit({"a.py": "x = 1\ny = 2  # lint\n"})
        with self.patched_env(), mock.patch.object(lint, "lint_pass", side_effect=AssertionError("no pass")):
            complete(self.run_dir, state)
        self.assertEqual(nav.current_stage(settle(self.run_dir)), "test")

    def test_blocked_implement_is_not_linted(self):
        self.commit({"a.py": "x = 1\n"})
        state = self.start()
        self.edit({"a.py": "x = 1\ny = 2  # lint\n"})
        with self.patched_env(), mock.patch.object(lint, "lint_pass", side_effect=AssertionError("no pass")):
            complete(self.run_dir, state, dict(DONE, outcome="blocked", awaiting=SERVICE_WAIT))

    def test_a_pass_that_cannot_run_never_refuses(self):
        self.commit({"a.py": "x = 1\n"})
        state = self.start()
        with self.patched_env(), mock.patch.object(lint, "lint_pass", side_effect=RuntimeError("boom")):
            complete(self.run_dir, state)
        action = nav.current_action(state)["id"]
        record = store.read_record(self.run_dir / "lint" / (action + ".gate1.md"))
        self.assertEqual(record["kind"], "failure")
        self.assertIn("could not run: RuntimeError: boom", record["block"])

    def test_lint_waivers_are_refused_outside_a_done_gate_stage(self):
        waivers = [{"id": "L0123456789", "reason": "r"}]
        self.assertEqual(lint.GATE_STAGES, ("implement", "test", "document"))
        with self.assertRaisesRegex(nav.NavigatorError, "only on a done implement, test, document result"):
            nav._canonical_result(dict(DONE, lint_waivers=waivers), stage="carry-forward")
        # A blocked result carrying them is refused for the fields it must not carry (the refusal names them and says
        # to delete them); the stage-specific sentence above applies to a done result at another stage.
        with self.assertRaisesRegex(nav.NavigatorError, "a blocked result does not carry lint_waivers"):
            nav._canonical_result(dict(DONE, outcome="blocked", awaiting=SERVICE_WAIT, lint_waivers=waivers), stage="implement")
        for stage in lint.GATE_STAGES:
            with self.subTest(stage=stage):
                self.assertEqual(nav._canonical_result(dict(DONE, lint_waivers=waivers), stage=stage)["lint_waivers"],
                                 waivers)

class CoverageLineTests(Fixture):
    """Design T §8.2a, F6: every lint result the model sees prints a coverage line beside it, so a syntax check is never
    read as a lint.  In 36036c every step's gate passed while game.js and server.js read "syntax checked by node --check
    (no catalogued linter)", a line only the stored record held."""

    def start(self, option: str = "fix") -> dict:
        nav.save(self.run_dir, nav.new_state(str(self.repo), "Lint coverage fixture.", improve_skill="",
                                             lint_option=option))
        with self.patched_env():
            return drive(self.run_dir, "implement")

    def patched_env(self):
        return mock.patch.dict(os.environ, {"PATH": str(self.bin) + ":" + SYSTEM_PATH, "STUB_LOG": str(self.log)})

    def test_the_result_is_followed_by_a_coverage_line_naming_each_file_not_linted(self):
        (self.bin / "node").write_text("#!" + sys.executable + "\n" + NODE_CHECK_STUB)
        (self.bin / "node").chmod(0o755)
        self.commit({"a.py": "x = 1\n", "game.js": "var a = 1\n", "server.js": "var s = 1\n",
                     "public/index.html": "<p>a</p>\n", "old.py": "z = 1\n"})
        self.base()
        self.edit({"a.py": "x = 2\n", "game.js": "var a = 2\n", "server.js": "var s = 2\n",
                   "public/index.html": "<p>b</p>\n"})
        (self.repo / "old.py").unlink()     # a deleted file needs no lint and is left out
        payload = self.run_pass(mode="report")
        expected = ("Lint coverage: 1 file linted by ruff; syntax only, not linted: game.js, server.js (syntax checked "
                    "by node --check (no catalogued linter)); not linted: public/index.html (not in scope: no catalogued "
                    "linter for this file type; git diff --check only).")
        self.assertEqual(payload["coverage_line"], expected)
        block = payload["block"].splitlines()
        self.assertEqual(block[block.index(payload["result_line"]) + 1], expected)
        # The packet leaves the per-file Coverage section to the record, and keeps this line beside the verdict.
        for relative, text in lint.record_writes(payload).items():
            store.atomic_write_text(self.run_dir / relative, text)
        packet = "\n".join(lint.render_lines(self.run_dir, "A1", stage="carry-forward", run_option="report",
                                             repo=str(self.repo), command=str(CLI), commands=False))
        self.assertNotIn("\nCoverage:", packet)
        self.assertIn(payload["result_line"] + "\n" + expected, packet)

    def test_the_coverage_line_says_when_a_tool_is_unavailable_timed_out_or_did_not_run(self):
        self.commit({"a.py": "x = 1\n", "eslint.config.js": "export default []\n", ".prettierrc": "{}\n",
                     "b.js": "var b = 1\n"})
        self.base()
        self.edit({"a.py": "x = 2\n"})
        missing = self.run_pass(mode="report", env=self.env(path=str(self.repo / "nothing-here")))
        self.assertIn("syntax only, not linted: a.py (syntax only: no linter available (ruff not found on this "
                      "process's PATH:", missing["coverage_line"])
        slow = Path(self.temp.name) / "slow"
        slow.mkdir()
        (slow / "ruff").write_text("#!" + sys.executable + "\nimport sys, time\nif '--version' in sys.argv:\n"
                                   "    print('ruff 0.0.1')\n    sys.exit(0)\ntime.sleep(30)\n")
        (slow / "ruff").chmod(0o755)
        timed = self.run_pass(mode="report", env=self.env(path=str(slow)), tool_timeout=1.0)
        self.assertRegex(timed["coverage_line"], r"syntax only, not linted: a\.py \(syntax only: ruff [^)]*timed out\)")
        # A file one tool linted while another the repository configures could not run is linted in part.
        self.edit({"a.py": "x = 1\n", "b.js": "var b = 2\n"})
        write_tool(self.bin, "eslint")
        part = self.run_pass(mode="report")
        self.assertIn("Lint coverage: linted in part: b.js (linted by eslint (eslint.config.js); prettier not run: "
                      "prettier not found", part["coverage_line"])
        # Once prettier runs too, the file is linted, and the line names every linter that covered it.
        write_tool(self.bin, "prettier")
        self.assertEqual(self.run_pass(mode="report")["coverage_line"], "Lint coverage: 1 file linted by eslint, prettier.")

    def test_each_gate_refusal_and_a_pass_that_cannot_run_print_the_coverage_line(self):
        self.commit({"a.py": "x = 1\n", "notes.txt": "a\n"})
        state = self.start()
        self.edit({"a.py": "x = 1\ny = 2  # fixme\n", "notes.txt": "b\n"})
        coverage = ("Lint coverage: 1 file linted by ruff; not linted: notes.txt (not in scope: no catalogued linter "
                    "for this file type; git diff --check only).")
        with self.patched_env():
            with self.assertRaises(nav.NavigatorError) as fixed:
                complete(self.run_dir, state)
            self.assertIn("ShipLoop auto-fixed a.py", str(fixed.exception))
            self.assertIn(coverage, str(fixed.exception))
            self.edit({"a.py": "x = 1\ny = 2  # lint\n"})
            with self.assertRaises(nav.NavigatorError) as found:
                complete(self.run_dir, state)
            self.assertIn("implement is not done while 1 new lint finding", str(found.exception))
            self.assertIn(coverage, str(found.exception))
            with mock.patch.object(lint, "lint_pass", side_effect=RuntimeError("boom")):
                complete(self.run_dir, state)
        action = nav.current_action(state)["id"]
        failure = store.read_record(self.run_dir / "lint" / (action + ".gate3.md"))
        self.assertIn("Lint coverage: none: this pass could not run, so no file was linted or syntax-checked.",
                      failure["block"])

    def test_a_gate_stages_packet_says_when_lint_is_off(self):
        off = ("Lint coverage: off (run option lint=off): ShipLoop runs no linter and no lint gate, so nothing this "
               "stage changes is linted. Choose and run this step's static checks yourself.")
        for stage in lint.GATE_STAGES:
            with self.subTest(stage=stage):
                self.assertEqual(lint.command_lines(self.run_dir, "A1", stage=stage, run_option="off", command="x"),
                                 [off])
        self.assertEqual(lint.command_lines(self.run_dir, "A1", stage="carry-forward", run_option="off", command="x"),
                         [])
        self.commit({"a.py": "x = 1\n"})
        self.assertIn(off, nav.render(CORE, self.run_dir, self.start("off")))
        self.assertNotIn("Lint coverage: off", nav.render(CORE, self.run_dir, self.start("fix")))


class PromptContractTests(unittest.TestCase):
    def test_gate_stages_tell_the_model_to_lint_inside_their_loop(self):
        """The pass-or-stop text left with the 17-stage loop (2026-10-10): every inner stage's Until Loop repeats until
        its exit holds, and each gate stage's loop work runs the printed lint command; a finding that must stay goes
        in lint_waivers, which the gate stages alone accept."""
        import shiploop_loops as loops
        import shiploop_prompts as guidance
        for stage in loops.STAGES:
            self.assertNotIn("Pass-or-stop loop", guidance.prompt(stage, delegation=guidance.INLINE))
        # Packet re-cut (2026-10-11): the loop's Work is "do duty items 1-4 of the packet"; running the checks and the
        # lint command is stated once, in the stage's own duty item, and the loop's Repeat rule names the lint finding.
        for stage, run_lint in (("implement", "run the step's Proof (the Step block) and `shiploop lint --action`"),
                                ("test", "run every recorded command, the red-check command and the lint command")):
            with self.subTest(stage=stage):
                work = " ".join(loops.WORK[stage].split())
                self.assertIn("duty items", work)
                self.assertIn("{run}/packets/{action}.md", work)
                packet = " ".join(guidance.prompt(stage, delegation=guidance.INLINE).split())
                self.assertEqual(packet.count(run_lint), 1)
                self.assertIn("`lint_waivers`", packet)
                self.assertIn("lint", " ".join(loops.REPEAT[stage].split()))
        implement = " ".join(guidance.prompt("implement", delegation=guidance.INLINE).split())
        self.assertIn("the same check still fails in the same way after a genuine fix", implement)


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
