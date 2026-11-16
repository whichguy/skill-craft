#!/usr/bin/env python3
"""ShipLoop's Python floor and its fail-open hooks (portability audit, docs/shiploop-portability-audit-journal.md).

Below the floor the CLI says so in one line and exits 2; a host hook event does nothing and exits 0, so a machine with
an old python3, or none, gets no error on every tool call.  The floor is declared once, in
``shiploop_pyfloor.FLOOR``; the skill card states the minimum, while CI follows the latest stable Python (the python-floor group's
membership is pinned in test-groups, not here: importing the catalog would make this suite a reader of every path it names).  The interpreter below the floor
is simulated by setting ``sys.version_info`` before the entry script runs (a real Python 3.7.3 gave the same exits and
messages on 2026-10-31); the shell wrappers are run with a stub ``python3`` that records what it was asked to run.
"""

from __future__ import annotations

import ast
from pathlib import Path
import os
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

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


def _run_below_floor(script: str, *args: str, version: tuple[int, int, int] = (3, 8, 0)) -> subprocess.CompletedProcess:
    """Simulate an unsupported interpreter before the entry script's first line."""
    code = ("import runpy, sys\n"
            f"sys.version_info = {version + ('final', 0)!r}\n"
            "sys.argv = sys.argv[1:]\n"
            "runpy.run_path(sys.argv[0], run_name='__main__')\n")
    return subprocess.run([sys.executable, "-B", "-c", code, str(SCRIPTS / script), *args], input="", text=True,
                          capture_output=True, timeout=60, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))


class BelowTheFloorTest(unittest.TestCase):
    def test_the_cli_entries_state_the_requirement_and_exit_blocked(self) -> None:
        for version in ((3, 8, 0), (3, 9, 0), (3, 14, 0)):
            for script, args in (("shiploop", ["--help"]), ("shiploop-drive", ["--help"]),
                                 ("shiploop-hook", ["status", "--host", "claude"])):
                with self.subTest(script=script, version=version):
                    done = _run_below_floor(script, *args, version=version)
                    self.assertEqual(done.returncode, 2, done.stderr)
                    self.assertEqual(done.stdout, "")
                    actual_version = ".".join(map(str, version))
                    self.assertEqual(done.stderr, f"error: ShipLoop needs Python {FLOOR} or newer; "
                                     f"this python3 is {actual_version}. Put a newer python3 first on PATH.\n")

    def test_a_host_hook_event_does_nothing_and_says_nothing(self) -> None:
        for version in ((3, 8, 0), (3, 9, 0), (3, 14, 0)):
            for verb in ("observe", "stop", "skill", "session-end"):
                with self.subTest(verb=verb, version=version):
                    done = _run_below_floor("shiploop-hook", verb, "--host", "auto", version=version)
                    self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))

    def test_an_interpreter_at_the_floor_passes_the_guard(self) -> None:
        self.assertEqual(shiploop_pyfloor.FLOOR, (3, 15))
        for version in ((3, 15, 0), (3, 15, 1), (3, 16, 0), (4, 0, 0)):
            with self.subTest(version=version), mock.patch.object(sys, "version_info", version + ("final", 0)):
                self.assertIsNone(shiploop_pyfloor.require())
                self.assertIsNone(shiploop_pyfloor.require(hook_event=True))
        # Also exercise the real interpreter running this suite.
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
        # Refusal compatibility only: old syntax lets unsupported interpreters reach the clean exit.
        # This does not offer Python 3.7 runtime support.
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
        # Keep this a narrow workflow reader; do not import the suite catalog or inventory docs.
        setups = [step for step in re.split(r"(?m)^      - ", workflow)
                  if step.startswith("uses: actions/setup-python@")]
        self.assertGreater(len(setups), 0, "CI must configure Python explicitly")
        for step in setups:
            with self.subTest(setup=step.splitlines()[0]):
                self.assertRegex(step, r"(?m)^          python-version: ['\"]3\.x['\"]\s*$")
                self.assertRegex(step, r"(?m)^          check-latest: true\s*$")
        self.assertNotRegex(workflow, r"matrix\.group\s*==\s*['\"]python-floor['\"]")
        self.assertNotIn("ubuntu-24.04", workflow)


if __name__ == "__main__":
    unittest.main()
