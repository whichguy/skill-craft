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
WEATHER = ROOT / "test" / "devloop-gas-weather-native.test.sh"
RUNNER = ROOT / "test" / "run-integration.sh"
DISPATCHER_V3 = ROOT / "test" / "fixtures" / "plan-dispatcher-v3" / "SKILL.md"


def invoke(argv: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, env=env, text=True, capture_output=True, check=False)


class IntegrationBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.fixture = Path(self.temp.name)
        self.repo = self.fixture / "weather-project"
        self.engine = self.fixture / "devloop-engine"
        self.scratch = self.fixture / "scratch"
        self.repo.mkdir()
        self.engine.mkdir()
        (self.repo / "sentinel").write_text("repo must remain unchanged\n")
        (self.engine / "sentinel").write_text("engine must remain unchanged\n")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def environment(self, **overrides: str) -> dict[str, str]:
        env = os.environ.copy()
        env.update({
            "HOME": str(self.fixture / "empty-home"),
            "DEVLOOP_HOME": str(self.engine),
            "DEVLOOP_WEATHER_REPO": str(self.repo),
            "DEVLOOP_LIVE_WEATHER": "0",
            "GROK_GOAL_SCRATCH": str(self.scratch),
        })
        env.update(overrides)
        return env

    def make_engine(self) -> None:
        scripts = self.engine / "scripts"
        scripts.mkdir()
        (scripts / "devloop_cli.py").write_text("# fixture engine\n")
        (self.engine / "engine-capabilities.json").write_text(
            json.dumps({"transports": ["grok"]})
        )

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

    def assert_preflight_preserves_sentinels(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertEqual("repo must remain unchanged\n", (self.repo / "sentinel").read_text())
        self.assertEqual("engine must remain unchanged\n", (self.engine / "sentinel").read_text())
        self.assertFalse((self.repo / "tests" / "test_weather_contract.py").exists())
        self.assertFalse(self.scratch.exists())

    def test_weather_rejects_missing_or_invalid_selection_before_mutation(self) -> None:
        cases = (
            ({"DEVLOOP_LIVE_WEATHER": ""}, "DEVLOOP_LIVE_WEATHER must be explicitly"),
            ({"DEVLOOP_LIVE_WEATHER": "maybe"}, "DEVLOOP_LIVE_WEATHER must be explicitly"),
            ({"DEVLOOP_HOME": ""}, "DEVLOOP_HOME is required"),
            ({"DEVLOOP_HOME": str(self.fixture / "missing-engine")}, "DEVLOOP_HOME must be an existing"),
            ({"DEVLOOP_WEATHER_REPO": ""}, "DEVLOOP_WEATHER_REPO is required"),
            ({"DEVLOOP_WEATHER_REPO": str(self.fixture / "missing-project")}, "DEVLOOP_WEATHER_REPO must be an existing"),
            ({}, "DEVLOOP_HOME must contain scripts/devloop_cli.py"),
        )
        for overrides, expected in cases:
            with self.subTest(overrides=overrides):
                result = invoke(["bash", str(WEATHER)], self.environment(**overrides))
                self.assertIn(expected, result.stderr)
                self.assert_preflight_preserves_sentinels(result)

    def test_weather_rejects_relative_symlink_and_mode_specific_prerequisites(self) -> None:
        self.make_engine()
        engine_link = self.fixture / "engine-link"
        repo_link = self.fixture / "repo-link"
        engine_link.symlink_to(self.engine, target_is_directory=True)
        repo_link.symlink_to(self.repo, target_is_directory=True)
        cases = (
            ({"DEVLOOP_HOME": "relative-engine"}, "DEVLOOP_HOME must be an existing"),
            ({"DEVLOOP_WEATHER_REPO": "relative-project"}, "DEVLOOP_WEATHER_REPO must be an existing"),
            ({"DEVLOOP_HOME": str(engine_link)}, "DEVLOOP_HOME must be an existing"),
            ({"DEVLOOP_WEATHER_REPO": str(repo_link)}, "DEVLOOP_WEATHER_REPO must be an existing"),
            ({"DEVLOOP_HOME": str(self.engine)}, "offline mode requires"),
        )
        for overrides, expected in cases:
            with self.subTest(overrides=overrides):
                result = invoke(["bash", str(WEATHER)], self.environment(**overrides))
                self.assertIn(expected, result.stderr)
                self.assert_preflight_preserves_sentinels(result)

        result = invoke(
            ["bash", str(WEATHER)],
            self.environment(DEVLOOP_LIVE_WEATHER="1", DEVLOOP_WEATHER_REPO=str(ROOT)),
        )
        self.assertIn("must not be /, this skill-craft checkout, or the home directory", result.stderr)
        self.assert_preflight_preserves_sentinels(result)

        (self.engine / "engine-capabilities.json").unlink()
        result = invoke(["bash", str(WEATHER)], self.environment())
        self.assertIn("DEVLOOP_HOME must contain engine-capabilities.json", result.stderr)
        self.assert_preflight_preserves_sentinels(result)

    def test_optional_runner_lists_without_host_and_rejects_bad_selection(self) -> None:
        empty_env = {"PATH": os.environ["PATH"], "HOME": str(self.fixture / "empty-home")}
        for argv in (["bash", str(RUNNER), "list"], ["bash", str(RUNNER), "--help"]):
            result = invoke(argv, empty_env)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("weather-offline", result.stdout)
            self.assertIn("cursor-imports", result.stdout)
            self.assertIn("current-dispatcher", result.stdout)

        current_help = invoke(["bash", str(RUNNER), "current-dispatcher", "--help"], empty_env)
        self.assertEqual(0, current_help.returncode, current_help.stdout + current_help.stderr)
        self.assertIn("--dispatcher-skill", current_help.stdout)
        self.assertIn("--output", current_help.stdout)

        result = invoke(["bash", str(RUNNER), "not-a-command"], empty_env)
        self.assertEqual(64, result.returncode)
        self.assertIn("unknown command", result.stderr)

        result = invoke(["bash", str(RUNNER), "list", "extra"], empty_env)
        self.assertEqual(64, result.returncode)

        result = invoke(["bash", str(RUNNER), "weather-offline"], empty_env)
        self.assertEqual(2, result.returncode)
        self.assertIn("DEVLOOP_HOME is required", result.stderr)
        self.assertIn("DEVLOOP_WEATHER_REPO is required", result.stderr)

        result = invoke(["bash", str(RUNNER), "cursor-imports"], empty_env)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("missing imported skill", result.stdout + result.stderr)

    def test_runner_sets_each_weather_mode_for_an_isolated_fake_script(self) -> None:
        fake_root = self.fixture / "fake-root"
        fake_test = fake_root / "test"
        fake_test.mkdir(parents=True)
        fake_runner = fake_test / "run-integration.sh"
        shutil.copyfile(RUNNER, fake_runner)
        capture = self.fixture / "mode-capture"
        fake_weather = fake_test / "devloop-gas-weather-native.test.sh"
        fake_weather.write_text(
            "#!/usr/bin/env bash\nset -eu\nprintf '%s' \"$DEVLOOP_LIVE_WEATHER\" > \"$MODE_CAPTURE\"\n"
        )
        env = self.environment(MODE_CAPTURE=str(capture))
        for command, expected in (("weather-offline", "0"), ("weather-live", "1")):
            with self.subTest(command=command):
                capture.unlink(missing_ok=True)
                result = invoke(["bash", str(fake_runner), command], env)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertEqual(expected, capture.read_text())

    def test_offline_runner_propagates_its_mode_to_isolated_fixture(self) -> None:
        self.make_engine()
        common_js = self.repo / "common-js"
        common_js.mkdir()
        (common_js / "weather.gs").write_text(
            "module.exports = { __events__: { doGet: 'handleGet' }, loadNow: true };\n"
            "function handleGet() {\n"
            "  const place = 'San Ramon'; const url = 'https://api.open-meteo.com/v1/forecast?temperature_2m';\n"
            "  const data = UrlFetchApp.fetch(url); return HtmlService.createHtmlOutput(place + data);\n}\n"
        )
        (self.repo / "appsscript.json").write_text(json.dumps({
            "timeZone": "America/Los_Angeles",
            "oauthScopes": ["https://www.googleapis.com/auth/script.external_request"],
        }))
        result = invoke(
            ["bash", str(RUNNER), "weather-offline"],
            self.environment(DEVLOOP_LIVE_WEATHER="1"),
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("live=0", result.stdout)
        self.assertIn(f"repo={self.repo}", result.stdout)
        self.assertIn(f"engine={self.engine}", result.stdout)
        self.assertTrue((self.repo / "tests" / "test_weather_contract.py").is_file())

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
