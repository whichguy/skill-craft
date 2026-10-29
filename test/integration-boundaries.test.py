#!/usr/bin/env python3
"""Hermetic regression checks for explicit optional integration boundaries."""

from __future__ import annotations

import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "test" / "run-integration.sh"


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

    def test_optional_runner_lists_without_host_and_rejects_bad_selection(self) -> None:
        empty_env = {"PATH": os.environ["PATH"], "HOME": str(self.fixture / "empty-home")}
        for argv in (["bash", str(RUNNER), "list"], ["bash", str(RUNNER), "--help"]):
            result = invoke(argv, empty_env)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("shiploop-e2e", result.stdout)
            self.assertIn("cursor-imports", result.stdout)
            self.assertIn("marketplace-claude", result.stdout)
            self.assertIn("backchain-chunks", result.stdout)

        result = invoke(["bash", str(RUNNER), "marketplace-codex", "extra"], empty_env)
        self.assertEqual(64, result.returncode, result.stdout + result.stderr)

        chunks_help = invoke(["bash", str(RUNNER), "backchain-chunks", "--help"], empty_env)
        self.assertEqual(0, chunks_help.returncode, chunks_help.stdout + chunks_help.stderr)
        self.assertIn("prepare", chunks_help.stdout)
        self.assertIn("check", chunks_help.stdout)

        result = invoke(["bash", str(RUNNER), "not-a-command"], empty_env)
        self.assertEqual(64, result.returncode)
        self.assertIn("unknown command", result.stderr)

        result = invoke(["bash", str(RUNNER), "list", "extra"], empty_env)
        self.assertEqual(64, result.returncode)

        result = invoke(["bash", str(RUNNER), "cursor-imports"], empty_env)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("missing imported skill", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
