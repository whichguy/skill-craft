#!/usr/bin/env python3
"""Hermetic regression checks for explicit optional integration boundaries."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

import current_dispatcher


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "test" / "run-integration.sh"
DISPATCHER_V3 = ROOT / "test" / "fixtures" / "plan-dispatcher-v3" / "SKILL.md"


def invoke(argv: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, env=env, text=True, capture_output=True, check=False)


class IntegrationBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.fixture = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def environment(self, **overrides: str) -> dict[str, str]:
        env = os.environ.copy()
        env.update({
            "HOME": str(self.fixture / "empty-home"),
        })
        env.update(overrides)
        return env

    def git(self, checkout: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(checkout), *args], text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return result.stdout.strip()

    def external_dispatcher_checkout(self) -> tuple[Path, Path]:
        checkout = self.fixture / "dispatcher-checkout"
        package = checkout / "skills" / "plan-dispatcher"
        shutil.copytree(DISPATCHER_V3.parent, package)
        checkout.mkdir(exist_ok=True)
        self.git(checkout, "init", "-q", "-b", "main")
        self.git(checkout, "config", "user.name", "Integration Boundary")
        self.git(checkout, "config", "user.email", "integration-boundary@example.invalid")
        self.git(checkout, "add", ".")
        self.git(checkout, "commit", "-qm", "clean dispatcher fixture")
        self.git(checkout, "remote", "add", "origin", "https://example.invalid/plan-orchestrator.git")
        return checkout, package / "SKILL.md"

    def test_optional_runner_lists_without_host_and_rejects_bad_selection(self) -> None:
        empty_env = {"PATH": os.environ["PATH"], "HOME": str(self.fixture / "empty-home")}
        for argv in (["bash", str(RUNNER), "list"], ["bash", str(RUNNER), "--help"]):
            result = invoke(argv, empty_env)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("shiploop-e2e", result.stdout)
            self.assertIn("cursor-imports", result.stdout)
            self.assertIn("current-dispatcher", result.stdout)
            self.assertIn("marketplace-claude", result.stdout)

        result = invoke(["bash", str(RUNNER), "marketplace-codex", "extra"], empty_env)
        self.assertEqual(64, result.returncode, result.stdout + result.stderr)

        current_help = invoke(["bash", str(RUNNER), "current-dispatcher", "--help"], empty_env)
        self.assertEqual(0, current_help.returncode, current_help.stdout + current_help.stderr)
        self.assertIn("--dispatcher-skill", current_help.stdout)
        self.assertIn("--output", current_help.stdout)

        result = invoke(["bash", str(RUNNER), "not-a-command"], empty_env)
        self.assertEqual(64, result.returncode)
        self.assertIn("unknown command", result.stderr)

        result = invoke(["bash", str(RUNNER), "list", "extra"], empty_env)
        self.assertEqual(64, result.returncode)

        result = invoke(["bash", str(RUNNER), "cursor-imports"], empty_env)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("missing imported skill", result.stdout + result.stderr)

    def test_current_dispatcher_rejects_nonabsolute_or_missing_selection_before_output(self) -> None:
        cases = (
            ("relative/SKILL.md", "--dispatcher-skill must be an absolute path"),
            (str(self.fixture / "missing" / "SKILL.md"), "must be an existing regular file"),
        )
        for index, (dispatcher, expected) in enumerate(cases):
            with self.subTest(dispatcher=dispatcher):
                output = self.fixture / f"current-dispatcher-output-{index}"
                result = invoke(
                    ["bash", str(RUNNER), "current-dispatcher", "--dispatcher-skill", dispatcher,
                     "--output", str(output)],
                    self.environment(),
                )
                self.assertEqual(2, result.returncode, result.stdout + result.stderr)
                self.assertIn(expected, result.stderr)
                self.assertFalse(output.exists())

    def test_current_dispatcher_requires_a_clean_external_checkout_and_external_output(self) -> None:
        checkout, card = self.external_dispatcher_checkout()
        (checkout / "operator-note.txt").write_text("dirty fixture\n", encoding="utf-8")
        output = self.fixture / "dirty-dispatcher-output"
        result = invoke(
            ["bash", str(RUNNER), "current-dispatcher", "--dispatcher-skill", str(card),
             "--output", str(output)],
            self.environment(),
        )
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertIn("must be clean", result.stderr)
        self.assertFalse(output.exists())

        (checkout / "operator-note.txt").unlink()
        result = invoke(
            ["bash", str(RUNNER), "current-dispatcher", "--dispatcher-skill", str(card),
             "--output", str(checkout / "receipt")],
            self.environment(),
        )
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertIn("outside the selected dispatcher checkout", result.stderr)
        self.assertFalse((checkout / "receipt").exists())

    def test_current_dispatcher_package_hashes_detect_drift(self) -> None:
        package = self.fixture / "dispatcher-package"
        shutil.copytree(DISPATCHER_V3.parent, package)
        card = package / "SKILL.md"
        before = current_dispatcher.package_hashes(card)
        card.write_text(card.read_text(encoding="utf-8") + "\n<!-- changed -->\n", encoding="utf-8")
        after = current_dispatcher.package_hashes(card)
        with self.assertRaisesRegex(current_dispatcher.QualificationError, "changed during qualification"):
            current_dispatcher.assert_unchanged("selected dispatcher package", before, after)

    def test_current_dispatcher_retains_pass_and_failure_receipts_for_selected_package(self) -> None:
        external, card = self.external_dispatcher_checkout()
        source = self.fixture / "qualification-source"
        helper = source / "test/current_dispatcher.py"
        helper.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / "test/current_dispatcher.py", helper)
        # Exercise the wrapper's real Git/CLI/log/receipt path cheaply. The real
        # native-pilot composition has its own suite and current-package check.
        pilot = source / "test/experiments/shiploop_chain/test_native_pilot.py"
        pilot.parent.mkdir(parents=True)
        pilot.write_text(
            "import argparse, os\nfrom pathlib import Path\n"
            "p=argparse.ArgumentParser(); p.add_argument('--dispatcher-skill', required=True)\n"
            "a=p.parse_args(); assert Path(a.dispatcher_skill).is_file()\n"
            "print(a.dispatcher_skill)\n"
            "raise SystemExit(int(os.environ.get('QUALIFICATION_FIXTURE_EXIT', '0')))\n"
        )
        self.git(source, "init", "-q", "-b", "main")
        self.git(source, "config", "user.name", "Qualification Fixture")
        self.git(source, "config", "user.email", "qualification@example.invalid")
        self.git(source, "add", ".")
        self.git(source, "commit", "-qm", "source fixture")
        self.git(source, "remote", "add", "origin", "https://example.invalid/skill-craft.git")
        source_head, external_head = self.git(source, "rev-parse", "HEAD"), self.git(external, "rev-parse", "HEAD")
        for child_exit in (0, 7):
            with self.subTest(child_exit=child_exit):
                output = self.fixture / f"qualification-{child_exit}"
                result = invoke(
                    [sys.executable, "-B", str(helper), "--dispatcher-skill", str(card), "--output", str(output)],
                    self.environment(QUALIFICATION_FIXTURE_EXIT=str(child_exit)),
                )
                self.assertEqual(result.returncode, 0 if child_exit == 0 else 2, result.stderr)
                receipt = json.loads((output / "receipt.json").read_text())
                self.assertEqual(receipt["passed"], child_exit == 0)
                selected = receipt["selected_dispatcher"]
                self.assertEqual(Path(selected["skill_card"]), card.resolve())
                self.assertEqual(selected["repository"]["exact_head"], external_head)
                self.assertEqual(selected["package_hashes"]["before"], selected["package_hashes"]["after"])
                identity = receipt["skill_craft_source_identity"]
                self.assertEqual(identity["before"], identity["after"])
                self.assertEqual(identity["before"]["exact_head"], source_head)
                actual = receipt["actual_run"]
                self.assertEqual(actual["exit_code"], child_exit)
                self.assertEqual(actual["argv"][-2:], ["--dispatcher-skill", str(card.resolve())])
                self.assertIn(str(card.resolve()), Path(actual["stdout"]["path"]).read_text())
                self.assertEqual(receipt["execution"]["model_calls"], 0)
                self.assertEqual(receipt["execution"]["native_agent_launches"], 0)
                self.assertEqual(self.git(source, "status", "--porcelain"), "")
                self.assertEqual(self.git(external, "status", "--porcelain"), "")

    def test_current_dispatcher_timeout_kills_a_term_ignoring_descendant(self) -> None:
        child = self.fixture / "term-ignoring-child.py"
        leader = self.fixture / "leader.py"
        marker = self.fixture / "child-pid"
        child.write_text(
            "import os, signal, sys, time\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "open(sys.argv[1], 'w', encoding='utf-8').write(str(os.getpid()))\n"
            "while True: time.sleep(1)\n",
            encoding="utf-8",
        )
        leader.write_text(
            "import subprocess, sys, time\n"
            "child = subprocess.Popen([sys.executable, sys.argv[1], sys.argv[2]])\n"
            "while not __import__('pathlib').Path(sys.argv[2]).exists(): time.sleep(.01)\n"
            "while True: time.sleep(1)\n",
            encoding="utf-8",
        )
        exit_code, timed_out, _, _ = current_dispatcher.run_with_process_group(
            [sys.executable, str(leader), str(child), str(marker)], self.environment(), timeout_seconds=0.2,
        )
        self.assertEqual(124, exit_code)
        self.assertTrue(timed_out)
        child_pid = int(marker.read_text(encoding="utf-8"))
        deadline = time.monotonic() + 2
        while True:
            inspected = subprocess.run(
                ["ps", "-o", "stat=", "-p", str(child_pid)], text=True, capture_output=True, check=False,
            )
            state = inspected.stdout.strip()
            if inspected.returncode != 0 or not state or state.startswith("Z"):
                break
            if time.monotonic() >= deadline:
                self.fail("term-ignoring descendant survived process-group cleanup")
            time.sleep(0.02)


if __name__ == "__main__":
    unittest.main()
