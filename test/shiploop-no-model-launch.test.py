#!/usr/bin/env python3
"""ShipLoop's package CLI remains a script-only graph controller.

The external E2E harness owns model-process launches.  This boundary test
uses relocated package bytes and executable tripwires so a future direct
transport cannot silently become part of the ordinary ShipLoop flow.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

import package_build


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_TRANSPORTS = (
    "shiploop_context_host.py",
    "shiploop_host.py",
    "shiploop_host_grok.py",
    "shiploop_host_claude.py",
    "shiploop_host_codex.py",
)
# Declared independently: the navigator protocol 1/2, managed and legacy
# runtime that 0.23.0 removed.  Neither package copy may still ship them.
REMOVED_SCRIPTS = (
    "_improve_managed.py", "shiploop_dry_run.py", "shiploop_packets.py", "shiploop_sdlc.py",
    "shiploop_improve_bridge.py", "shiploop_improve_policy.py", "shiploop_contracts.py",
    "shiploop_evidence.py", "shiploop_invalidation.py", "shiploop_report.py",
    "shiploop_artifacts.py", "shiploop_contract_protocol.py", "shiploop_delivery.py",
    "shiploop_discovery.py", "shiploop_history.py", "shiploop_history_policy.py",
    "shiploop_iteration_docs.py", "shiploop_knowledge.py", "shiploop_objectives.py",
    "shiploop_observations.py", "shiploop_outer_work.py", "shiploop_planning.py",
    "shiploop_research.py", "shiploop_revalidation.py", "shiploop_risk.py",
    "shiploop_step_planning.py", "shiploop_system_context.py", "shiploop_system_tests.py",
    "shiploop_until.py", "shiploop_navigator_prompts.py",
)
REMOVED_REFERENCES = (
    "action-protocol.md", "activities", "context-reset.md", "graph-dry-run-example.json",
    "improve-managed-consumer.md", "improve-managed-controller-pin.json",
    "improve-policy-pin.json", "improve-review-policy.md", "ledger-contract.md",
    "navigator-dry-run-example.json", "navigator-v3-dry-run-example.json",
    "objective-loops.md", "outer-work.md",
    "planning-loops.md", "report.md", "research-result-schema.md", "survey.md",
    "turn-packet.md",
)
REMOVED_COMMANDS = ("shiploop-evidence.md", "shiploop-inject.md")
REMOVED_VERBS = ("managed-graph-dry-run", "migrate", "merge-recover")
RETIRED_DOC_MENTIONS = (
    "managed-graph-dry-run", "--execution-mode managed", "navigator-v1", "navigator-v2",
    "shiploop migrate",
)


def read_record(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    prefix = "```shiploop-state\n"
    start = text.index(prefix) + len(prefix)
    end = text.index("\n```", start)
    value = json.loads(text[start:end])
    if not isinstance(value, dict):
        raise AssertionError(f"record is not an object: {path}")
    return value


def historical_context_host_receipt(
    state: dict[str, object], *, repo: Path, run_dir: Path, cli: Path
) -> bytes:
    """Render the retired context-host receipt format without importing it."""
    state_digest = hashlib.sha256(
        json.dumps(state, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    receipt = {
        "schema": "shiploop-context-host/v1",
        "host": "grok",
        "run_id": state["run_id"],
        "repo": str(repo.resolve()),
        "run_dir": str(run_dir.resolve()),
        "cli": str(cli),
        "policy": "inner-loop",
        "network_access": None,
        # This was a completed historical owner, not an active process to resume.
        "status": "ready",
        "thread_id": "historical-owner",
        "need_fresh": False,
        "state_digest": state_digest,
        "turns": [
            {
                "status": "completed",
                "thread_id": "historical-owner",
                "text": "Historical owner already stopped.",
                "usage": None,
            }
        ],
        "reset_boundaries": [],
        "owner_phase": "owner-completed",
    }
    text = "# ShipLoop context host receipt\n\n```shiploop-state\n"
    text += json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
    return (text + "\n```\n").encode("utf-8")


class ShipLoopNoModelLaunchTests(unittest.TestCase):
    package_relative = Path("skills") / "shiploop"
    package_label = "source"

    def package_dir(self) -> Path:
        return ROOT / self.package_relative

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-no-model-launch-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        source_package = self.package_dir()
        self.assertTrue(source_package.is_dir(), f"required {self.package_label} package is missing: {source_package}")
        self.package = self.base / "relocated package" / self.package_label
        shutil.copytree(source_package, self.package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        self.cli = self.package / "scripts" / "shiploop"
        self.repo = self.base / "ordinary repository"
        self.repo.mkdir()
        self.tripwire = self.base / "unexpected-model-launches.log"
        fake_bin = self.base / "model-tripwires"
        fake_bin.mkdir()
        for executable in ("grok", "claude", "codex"):
            path = fake_bin / executable
            path.write_text(
                "#!/bin/sh\nprintf '%s\\n' \"$0\" >> \"$SHIPLOOP_MODEL_LAUNCH_TRIPWIRE\"\nexit 97\n",
                encoding="utf-8",
            )
            path.chmod(path.stat().st_mode | stat.S_IXUSR)
        self.env = {
            **os.environ,
            "PATH": str(fake_bin) + os.pathsep + os.environ.get("PATH", ""),
            "PYTHONDONTWRITEBYTECODE": "1",
            "SHIPLOOP_MODEL_LAUNCH_TRIPWIRE": str(self.tripwire),
        }

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(self.cli), *args],
            cwd=self.repo,
            text=True,
            capture_output=True,
            env=self.env,
            timeout=30,
        )

    def assert_no_model_launch(self) -> None:
        self.assertFalse(
            self.tripwire.exists(),
            self.tripwire.read_text(encoding="utf-8") if self.tripwire.exists() else "",
        )

    def test_package_has_no_model_transports_and_rejects_drive(self) -> None:
        scripts = self.package / "scripts"
        for filename in FORBIDDEN_TRANSPORTS:
            with self.subTest(filename=filename):
                self.assertFalse((scripts / filename).exists())

        rejected = self.run_cli("drive", "--host", "grok")
        self.assertEqual(rejected.returncode, 2, rejected.stdout + rejected.stderr)
        self.assertIn("invalid choice: 'drive'", rejected.stderr)
        self.assert_no_model_launch()

    def test_package_contains_only_the_current_runtime(self) -> None:
        self.assertEqual(len(REMOVED_SCRIPTS), 30)
        for folder, names in (("scripts", REMOVED_SCRIPTS), ("references", REMOVED_REFERENCES),
                              ("commands", REMOVED_COMMANDS)):
            for name in names:
                with self.subTest(removed=folder + "/" + name):
                    self.assertFalse(os.path.lexists(self.package / folder / name))
        for verb in REMOVED_VERBS:
            with self.subTest(verb=verb):
                run_dir = self.base / ("removed-" + verb)
                rejected = self.run_cli(verb, "--run-dir", str(run_dir))
                self.assertEqual(rejected.returncode, 2, rejected.stdout + rejected.stderr)
                self.assertIn(f"invalid choice: '{verb}'", rejected.stderr)
                self.assertFalse(run_dir.exists())
        for card in (self.package / "SKILL.md", *sorted((self.package / "commands").glob("*.md"))):
            text = card.read_text(encoding="utf-8")
            for mention in RETIRED_DOC_MENTIONS:
                with self.subTest(card=card.name, mention=mention):
                    self.assertNotIn(mention, text)
        self.assert_no_model_launch()

    def test_normal_init_and_next_keep_the_same_run_and_action_without_model_launches(self) -> None:
        run_dir = self.base / "run"
        initialized = self.run_cli(
            "init",
            "--run-dir", str(run_dir),
            "--repo", str(self.repo),
            "--prompt", "Create a small offline fixture.",
        )
        self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
        initial = read_record(run_dir / "state.md")
        self.assertEqual(initial["navigator_protocol_version"], 4)
        initial_action = initial["action"]
        self.assertIsInstance(initial_action, dict)
        self.assertIn(initial_action["id"], initialized.stdout)

        continued = self.run_cli("next", "--run-dir", str(run_dir))
        self.assertEqual(continued.returncode, 0, continued.stdout + continued.stderr)
        after = read_record(run_dir / "state.md")
        self.assertEqual(after["run_id"], initial["run_id"])
        self.assertEqual(after["action"], initial_action)
        self.assertIn(initial_action["id"], continued.stdout)
        self.assert_no_model_launch()

    def test_next_ignores_a_stopped_historical_context_host_receipt(self) -> None:
        run_dir = self.base / "historical run"
        initialized = self.run_cli(
            "init",
            "--run-dir", str(run_dir),
            "--repo", str(self.repo),
            "--prompt", "Recover an ordinary saved run.",
        )
        self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
        initial = read_record(run_dir / "state.md")
        self.assertEqual(initial["navigator_protocol_version"], 4)
        initial_action = initial["action"]
        self.assertIsInstance(initial_action, dict)

        receipt_path = run_dir / "context-host.md"
        receipt_bytes = historical_context_host_receipt(
            initial, repo=self.repo, run_dir=run_dir, cli=self.cli
        )
        receipt_path.write_bytes(receipt_bytes)
        self.assertEqual(read_record(receipt_path)["schema"], "shiploop-context-host/v1")

        continued = self.run_cli("next", "--run-dir", str(run_dir))
        self.assertEqual(continued.returncode, 0, continued.stdout + continued.stderr)
        after = read_record(run_dir / "state.md")
        self.assertEqual(after["run_id"], initial["run_id"])
        self.assertEqual(after["action"], initial_action)
        self.assertIn(initial_action["id"], continued.stdout)
        self.assertEqual(receipt_path.read_bytes(), receipt_bytes)
        self.assert_no_model_launch()


class GeneratedShipLoopNoModelLaunchTests(ShipLoopNoModelLaunchTests):
    package_label = "generated"

    def package_dir(self) -> Path:
        # plugins/ is release output; read a build of the current source.
        return package_build.plugins() / "shiploop" / "skills" / "shiploop"


if __name__ == "__main__":
    unittest.main()
