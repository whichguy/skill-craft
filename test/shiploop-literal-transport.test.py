#!/usr/bin/env python3
"""Exercise the shipped entry command with literal user data, not a parser mock."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/shiploop"
sys.path.insert(0, str(SKILL / "scripts"))
import shiploop_store as store  # noqa: E402


class LiteralTransportTests(unittest.TestCase):
    def test_documented_entry_round_trips_literal_requests(self):
        card = (SKILL / "SKILL.md").read_text()
        example = next(
            line for line in card.splitlines()
            if line.startswith('python3 "$CLI" init ')
        )
        with tempfile.TemporaryDirectory(prefix="shiploop-literal-") as temporary:
            root = Path(temporary).resolve()
            sentinel = root / "must-not-exist"
            values = [
                "--help",
                "--repo=/not-the-selected-repository",
                "Quotes ' and \" and spaces",
                f"Keep $(touch {sentinel}) and `touch {sentinel}` and $PATH literal",
                "First line\r\n第二行 — café\nLast line\n",
            ]
            for index, value in enumerate(values):
                with self.subTest(value=value):
                    repo = root / f"repo {index}"
                    repo.mkdir()
                    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
                    for args in (
                        ("init", "-q"),
                        ("-c", "user.name=Literal Test", "-c", "user.email=literal@example.invalid",
                         "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
                         "commit", "--allow-empty", "-qm", "fixture baseline"),
                    ):
                        result = subprocess.run(
                            ["git", "-C", str(repo), *args], env=env, capture_output=True
                        )
                        self.assertEqual(result.returncode, 0, result.stderr)
                    run = repo / ".shiploop"
                    env.update(CLI=str(SKILL / "scripts/shiploop"), REPO=str(repo), RUN_DIR=str(run))
                    command = re.sub(
                        r"['\"]<user request>['\"]", lambda _: shlex.quote(value), example
                    )
                    result = subprocess.run(
                        ["/bin/sh", "-c", command], cwd=repo, env=env, capture_output=True
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(store.read_record(run / "state.md")["prompt"], value)
                    self.assertEqual((run / "prompt.md").read_bytes(), (value + "\n").encode())
                    self.assertFalse(sentinel.exists(), "literal prompt text executed as shell code")
                    pause = subprocess.run(
                        ["/bin/sh", "-c", 'python3 "$CLI" pause --run-dir "$RUN_DIR" --reason='
                         + shlex.quote(value)],
                        cwd=repo, env=env, capture_output=True,
                    )
                    self.assertEqual(pause.returncode, 0, pause.stderr)
                    paused = store.read_record(run / "state.md")
                    self.assertEqual(paused["paused"], value)
                    self.assertEqual(paused["stage"], "preflight")
                    self.assertFalse(sentinel.exists(), "literal reason executed as shell code")


if __name__ == "__main__":
    unittest.main(verbosity=2)
