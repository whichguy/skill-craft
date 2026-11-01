#!/usr/bin/env python3
"""ShipLoop's Python floor and its fail-open hooks (portability audit, docs/shiploop-portability-audit-journal.md).

Below the floor the CLI says so in one line and exits 2; a host hook event does nothing and exits 0, so a machine with
an old python3, or none, gets no error on every tool call.  The floor is declared once, in
``shiploop_pyfloor.FLOOR``; the skill card and the CI job must state the same number (the python-floor group's
membership is pinned in test-groups, not here: importing the catalog would make this suite a reader of every path it names).  The interpreter below the floor
is simulated by setting ``sys.version_info`` before the entry script runs (a real Python 3.7.3 gave the same exits and
messages on 2026-10-31); the shell wrappers are run with a stub ``python3`` that records what it was asked to run.
"""

from __future__ import annotations

import ast
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import shiploop_pyfloor  # noqa: E402

FLOOR = "%d.%d" % shiploop_pyfloor.FLOOR
# entry script -> the shiploop-hook arguments it stands for
HOOK_ENTRIES = {
    "shiploop-keepalive-observe": ["observe", "--host", "auto"],
    "shiploop-keepalive-stop": ["stop", "--host", "auto"],
    "shiploop-keepalive-session-end": ["session-end", "--host", "auto"],
    "shiploop-skill-call": ["skill", "--host", "claude"],
}
PAYLOAD = '{"hook_event_name": "PostToolUse", "session_id": "s1", "cwd": "/tmp"}'


def _run_below_floor(script: str, *args: str) -> subprocess.CompletedProcess:
    """Run an entry script as Python 3.8.0 would: ``sys.version_info`` is set before the script's first line."""
    code = ("import runpy, sys\n"
            "sys.version_info = (3, 8, 0, 'final', 0)\n"
            "sys.argv = sys.argv[1:]\n"
            "runpy.run_path(sys.argv[0], run_name='__main__')\n")
    return subprocess.run([sys.executable, "-c", code, str(SCRIPTS / script), *args], input="", text=True,
                          capture_output=True, timeout=60, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))


class BelowTheFloorTest(unittest.TestCase):
    def test_the_cli_entries_state_the_requirement_and_exit_blocked(self) -> None:
        for script, args in (("shiploop", ["--help"]), ("shiploop-drive", ["--help"]),
                             ("shiploop-hook", ["status", "--host", "claude"])):
            with self.subTest(script):
                done = _run_below_floor(script, *args)
                self.assertEqual(done.returncode, 2, done.stderr)
                self.assertEqual(done.stdout, "")
                self.assertEqual(done.stderr, f"error: ShipLoop needs Python {FLOOR} or newer; this python3 is 3.8.0. "
                                 "Put a newer python3 first on PATH.\n")

    def test_a_host_hook_event_does_nothing_and_says_nothing(self) -> None:
        for verb in ("observe", "stop", "skill", "session-end"):
            with self.subTest(verb):
                done = _run_below_floor("shiploop-hook", verb, "--host", "auto")
                self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))

    def test_an_interpreter_at_the_floor_passes_the_guard(self) -> None:
        shiploop_pyfloor.require()
        shiploop_pyfloor.require(hook_event=True)

    def test_every_entry_that_imports_a_shiploop_module_checks_the_floor_first(self) -> None:
        checked = 0
        for path in sorted(SCRIPTS.iterdir()):
            source = path.read_text(errors="ignore") if path.is_file() and path.suffix == "" else ""
            if not source.startswith("#!/usr/bin/env python3"):
                continue
            lines = source.splitlines()
            imports = [n for n, line in enumerate(lines) if line.startswith("import shiploop_")
                       and "shiploop_pyfloor" not in line]
            if not imports:
                continue
            guard = [n for n, line in enumerate(lines) if line.startswith("shiploop_pyfloor.require(")]
            self.assertTrue(guard and guard[0] < imports[0], f"{path.name} imports {lines[imports[0]]!r} before the floor check")
            checked += 1
        self.assertGreaterEqual(checked, 3, "shiploop, shiploop-drive and shiploop-hook")

    def test_the_guard_module_parses_as_python_3_7(self) -> None:
        # It must run on the interpreters it turns away; syntax is the part a later edit could break.
        ast.parse((SCRIPTS / "shiploop_pyfloor.py").read_text(), feature_version=(3, 7))


class HookWrapperTest(unittest.TestCase):
    def test_without_python3_each_wrapper_exits_zero_with_no_output(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            for name in HOOK_ENTRIES:
                with self.subTest(name):
                    done = subprocess.run([str(SCRIPTS / name)], input=PAYLOAD, text=True, capture_output=True, timeout=60,
                                          env={"PATH": empty})
                    self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))

    def test_with_python3_each_wrapper_runs_shiploop_hook_with_its_verb_and_the_payload_on_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stub = Path(tmp) / "bin" / "python3"
            stub.parent.mkdir()
            stub.write_text('#!/bin/sh\nprintf \'%s\\n\' "$@" > "$STUB_ARGV"\ncat > "$STUB_STDIN"\n')
            stub.chmod(0o755)
            for name, hook_args in HOOK_ENTRIES.items():
                with self.subTest(name):
                    argv, stdin = Path(tmp) / f"{name}.argv", Path(tmp) / f"{name}.stdin"
                    done = subprocess.run([str(SCRIPTS / name)], input=PAYLOAD, text=True, capture_output=True, timeout=60,
                                          env={"PATH": f"{stub.parent}:/usr/bin:/bin", "STUB_ARGV": str(argv),
                                               "STUB_STDIN": str(stdin)})
                    self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))
                    self.assertEqual(argv.read_text().splitlines(), [str(SCRIPTS / "shiploop-hook"), *hook_args])
                    self.assertEqual(stdin.read_text(), PAYLOAD)

    def test_the_wrappers_are_executable_shell_scripts_the_hook_manifest_can_name(self) -> None:
        for name in HOOK_ENTRIES:
            path = SCRIPTS / name
            self.assertTrue(path.read_text().startswith("#!/bin/sh\n"), name)
            self.assertTrue(os.access(path, os.X_OK), name)


class FloorIsStatedWhereItIsEnforcedTest(unittest.TestCase):
    def test_the_card_and_the_ci_job_state_the_same_floor(self) -> None:
        card = " ".join((ROOT / "skills/shiploop/SKILL.md").read_text().split())
        self.assertIn(f"needs `python3` {FLOOR} or newer and `git` on PATH", card)
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertIn(f"matrix.group == 'python-floor' && '{FLOOR}'", workflow)


if __name__ == "__main__":
    unittest.main()
