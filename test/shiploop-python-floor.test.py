#!/usr/bin/env python3
"""ShipLoop's Python floor, the run again on a newer Python, and its fail-open hooks (portability audit,
docs/shiploop-portability-audit-journal.md).

The floor is the oldest Python the scripts' code runs on (3.9), not a support policy, and the card states no version
(owner, 2026-11-18: no artificial mandates).  Below the floor an entry script runs itself again with the newest
``python3`` or ``python3.N`` on PATH that meets it.  Only when there is none does the CLI say so in one line and exit 2, while a host hook event does nothing and
exits 0, so a machine with an old python3, or none, gets no error on every tool call.  The floor is declared once, in
``shiploop_pyfloor.FLOOR``, while CI follows the latest stable Python (the
python-floor group's membership is pinned in test-groups, not here: importing the catalog would make this suite a reader
of every path it names).  The interpreter below the floor is simulated by setting ``sys.version_info`` before the entry
script runs (a real Python 3.7.3 gave the same exits on 2026-10-31); every other interpreter on PATH is a stub shell
script that answers the version query and records what it was asked to run, as is the shell wrappers' ``python3``.
"""

from __future__ import annotations

import ast
from pathlib import Path
import os
import re
import shutil
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
EXITED_AS_STUB = 7  # a stub interpreter's exit status once it ran in place of the entry script


def _stub_python(path: Path, answer: str, after_query: str = "") -> Path:
    """A stub interpreter at ``path``.  Asked ShipLoop's version query, it appends its path to ``$STUB_RECORD.asked``
    and prints ``answer`` ("3 16").  Run as the interpreter of a script, it writes its path, its arguments and the
    run-again mark to ``$STUB_RECORD`` and its stdin to ``$STUB_RECORD.stdin``, then exits EXITED_AS_STUB."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('#!/bin/sh\n'
                    'if [ "$1" = "-c" ]; then\n'
                    '  printf "%s\\n" "$0" >> "$STUB_RECORD.asked"\n'
                    f'  echo "{answer}"\n'
                    f'  {after_query}exit 0\n'
                    'fi\n'
                    '{ printf "%s\\n" "$0" "$@"; printf "mark=%s\\n" "${SHIPLOOP_PYTHON_REEXEC-unset}"; } > "$STUB_RECORD"\n'
                    '/bin/cat > "$STUB_RECORD.stdin"\n'
                    f'exit {EXITED_AS_STUB}\n')
    path.chmod(0o755)
    return path


def _run_below_floor(script: str, *args: str, version: tuple[int, int, int] = (3, 8, 0), path: str = "",
                     record: Path | None = None, mark: str | None = None, flags: tuple[str, ...] = ("-B",),
                     stdin: str = "") -> subprocess.CompletedProcess:
    """Simulate an unsupported interpreter before the entry script's first line, with ``path`` as the whole PATH and a
    minimal environment (so no PYTHON* variable changes the interpreter options the run again must keep)."""
    code = ("import runpy, sys\n"
            f"sys.version_info = {version + ('final', 0)!r}\n"
            "sys.argv = sys.argv[1:]\n"
            "runpy.run_path(sys.argv[0], run_name='__main__')\n")
    env = {"PATH": path, "HOME": os.environ["HOME"], "XDG_STATE_HOME": os.environ["XDG_STATE_HOME"]}
    if record is not None:
        env["STUB_RECORD"] = str(record)
    if mark is not None:
        env[shiploop_pyfloor.REEXEC_MARK] = mark
    return subprocess.run([sys.executable, *flags, "-c", code, str(SCRIPTS / script), *args], input=stdin, text=True,
                          capture_output=True, timeout=60, env=env)


class StubsCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.record = self.tmp / "record"

    def asked(self) -> list[str]:
        asked = self.record.with_name("record.asked")
        return asked.read_text().splitlines() if asked.exists() else []


class BelowTheFloorWithNoNewerPythonTest(StubsCase):
    """Old interpreters only: a python3 3.8 (asked) and a python3.7 (not asked: its name is below the floor)."""

    def setUp(self) -> None:
        super().setUp()
        _stub_python(self.tmp / "bin" / "python3", "3 8")
        _stub_python(self.tmp / "bin" / "python3.7", "3 7")
        self.path = str(self.tmp / "bin")

    def test_the_cli_entries_state_the_requirement_and_exit_blocked(self) -> None:
        for version in ((3, 7, 3), (3, 8, 0), (3, 8, 20)):
            for script, args in (("shiploop", ["--help"]), ("shiploop-drive", ["--help"]),
                                 ("shiploop-hook", ["status", "--host", "claude"])):
                with self.subTest(script=script, version=version):
                    done = _run_below_floor(script, *args, version=version, path=self.path, record=self.record)
                    self.assertEqual(done.returncode, 2, done.stderr)
                    self.assertEqual(done.stdout, "")
                    actual_version = ".".join(map(str, version))
                    self.assertEqual(len(done.stderr.splitlines()), 1, done.stderr)
                    self.assertTrue(done.stderr.startswith(f"error: ShipLoop needs Python {FLOOR} or newer; this Python ("),
                                    done.stderr)
                    self.assertTrue(done.stderr.endswith(f") is {actual_version}, and no python3 or python3.N on PATH is "
                                                         f"{FLOOR} or newer; install one or put it on PATH.\n"), done.stderr)
                    self.assertFalse(self.record.exists(), "no stub ran in place of the entry script")
        self.assertEqual(set(self.asked()), {str(self.tmp / "bin" / "python3")})

    def test_a_host_hook_event_does_nothing_and_says_nothing(self) -> None:
        for version in ((3, 7, 3), (3, 8, 0), (3, 8, 20)):
            for verb in ("observe", "stop", "skill", "session-end"):
                with self.subTest(verb=verb, version=version):
                    done = _run_below_floor("shiploop-hook", verb, "--host", "auto", version=version, path=self.path,
                                            record=self.record, stdin=PAYLOAD)
                    self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))
                    self.assertFalse(self.record.exists())

    def test_an_empty_path_is_the_same_refusal(self) -> None:
        done = _run_below_floor("shiploop", "--help", path="", record=self.record)
        self.assertEqual(done.returncode, 2, done.stderr)
        self.assertIn("and no python3 or python3.N on PATH is %s or newer" % FLOOR, done.stderr)
        self.assertEqual(self.asked(), [])


class RunsAgainWithTheNewestPythonTest(StubsCase):
    """PATH as on an older Linux: a python3 3.8 first, then newer interpreters.  Each decoy would win if the rule it
    tests were broken: a python3.8 that would answer 3.18, a python3-config that would answer 3.17."""

    def setUp(self) -> None:
        super().setUp()
        first, second = self.tmp / "first", self.tmp / "second"
        _stub_python(first / "python3", "3 8")
        _stub_python(first / "python3.9", "3 9")
        newest = _stub_python(second / "python3.16", "3 16")
        (second / "python3").symlink_to(newest.name)  # one interpreter under two names: asked once, by its first name
        _stub_python(second / "python3.8", "3 18")  # never asked: its name is below the floor
        _stub_python(second / "python3-config", "3 17")  # not an interpreter name
        self.first, self.second = first, second
        self.path = os.pathsep.join((str(first), str(second)))

    def ran(self) -> list[str]:
        return self.record.read_text().splitlines()

    def test_the_cli_runs_again_with_the_newest_and_keeps_its_arguments(self) -> None:
        done = _run_below_floor("shiploop", "--help", path=self.path, record=self.record)
        self.assertEqual(done.returncode, EXITED_AS_STUB, done.stderr)
        self.assertEqual((done.stdout, done.stderr), ("", ""))
        self.assertEqual(self.ran(), [str(self.second / "python3"), "-B", str(SCRIPTS / "shiploop"), "--help", "mark=1"])
        self.assertEqual(self.asked(), [str(self.first / "python3"), str(self.first / "python3.9"),
                                        str(self.second / "python3")])

    def test_every_entry_runs_again_and_a_hook_keeps_its_payload_on_stdin(self) -> None:
        for script, args in (("shiploop-drive", ["--help"]), ("shiploop-hook", ["observe", "--host", "auto"]),
                             ("shiploop-hook", ["status", "--host", "claude"])):
            with self.subTest(script=script, args=args):
                done = _run_below_floor(script, *args, path=self.path, record=self.record, stdin=PAYLOAD)
                self.assertEqual(done.returncode, EXITED_AS_STUB, done.stderr)
                self.assertEqual(self.ran(), [str(self.second / "python3"), "-B", str(SCRIPTS / script), *args, "mark=1"])
                self.assertEqual(self.record.with_name("record.stdin").read_text(), PAYLOAD)

    def test_isolated_mode_is_kept(self) -> None:
        done = _run_below_floor("shiploop", "--help", path=self.path, record=self.record, flags=("-I", "-B"))
        self.assertEqual(done.returncode, EXITED_AS_STUB, done.stderr)
        self.assertEqual(self.ran()[1:3], ["-I", "-B"])

    def test_a_script_already_run_again_looks_no_further(self) -> None:
        """An interpreter that answered the query with a version it does not have cannot make a script run again forever."""
        done = _run_below_floor("shiploop", "--help", path=self.path, record=self.record, mark="1")
        self.assertEqual(done.returncode, 2, done.stderr)
        self.assertIn("ShipLoop started it as the newest Python on PATH (SHIPLOOP_PYTHON_REEXEC is set), so it looks "
                      "no further.", done.stderr)
        hook = _run_below_floor("shiploop-hook", "observe", "--host", "auto", path=self.path, record=self.record,
                                mark="1", stdin=PAYLOAD)
        self.assertEqual((hook.returncode, hook.stdout, hook.stderr), (0, "", ""))
        self.assertFalse(self.record.exists())
        self.assertEqual(self.asked(), [])

    def test_a_newest_python_that_cannot_be_run_is_named(self) -> None:
        broken = _stub_python(self.tmp / "only" / "python3.16", "3 16", after_query='/bin/chmod 644 "$0"; ')
        done = _run_below_floor("shiploop", "--help", path=str(broken.parent), record=self.record)
        self.assertEqual(done.returncode, 2, done.stderr)
        self.assertEqual(len(done.stderr.splitlines()), 1, done.stderr)
        self.assertIn(f"and running {broken} failed: ", done.stderr)
        self.assertFalse(self.record.exists())

    def test_an_interpreter_at_the_floor_clears_the_mark_for_its_children(self) -> None:
        with mock.patch.dict(os.environ, {shiploop_pyfloor.REEXEC_MARK: "1"}):
            shiploop_pyfloor.require()
            self.assertNotIn(shiploop_pyfloor.REEXEC_MARK, os.environ)


class AtTheFloorTest(unittest.TestCase):
    def test_an_interpreter_at_the_floor_passes_the_guard(self) -> None:
        self.assertEqual(shiploop_pyfloor.FLOOR, (3, 9))
        for version in ((3, 9, 0), (3, 9, 6), (3, 15, 1), (4, 0, 0)):
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
        # Refusal compatibility only: old syntax lets unsupported interpreters reach the run again or the clean exit.
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


class TheCardStatesNoVersionTest(unittest.TestCase):
    def test_the_card_asks_for_python3_and_git_only_and_ci_follows_the_latest_python(self) -> None:
        card = " ".join((ROOT / "skills/shiploop/SKILL.md").read_text().split())
        self.assertIn("ShipLoop needs `python3` and `git` on PATH.", card)
        # No version on the card (owner, 2026-11-18: no artificial mandates): a stated version sends the model to check it
        # and stop, as the step of the 2026-11-18 smoke did on Apple's 3.9.6 (docs/experiments/closed-loop-smoke-20261118).
        self.assertNotRegex(card, r"(?i)python ?3\.[0-9]")
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
