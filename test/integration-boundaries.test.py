#!/usr/bin/env python3
"""Hermetic regression checks for explicit optional integration boundaries."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
WEATHER = ROOT / "test" / "devloop-gas-weather-native.test.sh"
RUNNER = ROOT / "test" / "run-integration.sh"


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


if __name__ == "__main__":
    unittest.main()
