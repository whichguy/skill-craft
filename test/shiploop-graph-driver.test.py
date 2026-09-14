#!/usr/bin/env python3
"""Cheap, non-mutating acceptance coverage for ShipLoop's graph dry-run.

The driver must use the real pure managed controller and the same prompt
selection function as live packets.  These tests intentionally provide only
declared scenario expectations; they do not recreate a second route engine.
"""

from __future__ import annotations

import copy
from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SHIPLOOP = ROOT / "skills" / "shiploop"
SCRIPTS = SHIPLOOP / "scripts"
CLI = SCRIPTS / "shiploop"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_dry_run as dry_run  # noqa: E402
import shiploop_packets as packets  # noqa: E402
import shiploop_protocol as protocol  # noqa: E402
import shiploop_store as store  # noqa: E402


EXPECTED_SCENARIOS = {
    "research": (11, "converged"),
    "behavior": (11, "converged"),
    "spec": (11, "converged"),
    "objective": (11, "converged"),
    "step-plan": (9, "converged"),
    "product": (21, "converged"),
    "product-skill": (23, "converged"),
    "product-material-reset": (41, "converged"),
    "product-block-resume": (24, "converged"),
    "product-pause-resume": (24, "converged"),
    "product-repair": (41, "converged"),
    "step-plan-disposition": (11, "converged"),
    "step-plan-repair": (13, "converged"),
    "needs-prerequisite": (1, "needs-prerequisite"),
    "needs-replan": (1, "needs-replan"),
    "stopped": (1, "stopped"),
}


class ForbiddenCore:
    """A graph preview must not need the live run-directory core."""

    def __getattr__(self, name: str):
        raise AssertionError(f"graph dry-run unexpectedly accessed core.{name}")


class GraphDriverTests(unittest.TestCase):
    def api(self) -> dict:
        """Use the actual live prompt maps, never a duplicated prompt fixture."""
        return dict(protocol.__dict__)

    def run_cli(self, cwd: Path, *args: str, script: Path = CLI) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONNOUSERSITE"] = "1"
        return subprocess.run(
            [sys.executable, "-B", str(script), "graph-dry-run", *args],
            cwd=cwd,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def report(self, name: str) -> dict:
        return dry_run.run_scenario(dry_run.scenarios()[name], self.api())

    def test_all_builtin_scenarios_drive_real_expected_paths_and_statuses(self) -> None:
        scenarios = dry_run.scenarios()
        self.assertEqual(set(scenarios), set(EXPECTED_SCENARIOS))
        self.assertEqual(len(scenarios), 16)

        for name, (expected_events, expected_status) in EXPECTED_SCENARIOS.items():
            with self.subTest(name=name):
                scenario = scenarios[name]
                report = dry_run.run_scenario(scenario, self.api())
                self.assertTrue(report["ok"], report.get("error"))
                self.assertTrue(report["simulation_only"])
                self.assertEqual(report["scope"], dry_run.SCOPE)
                self.assertEqual(len(report["events"]), expected_events)
                self.assertEqual(report["simulated_status"], expected_status)

                # The driver compares this independent declared trace against
                # the real controller before it marks a scenario successful.
                self.assertEqual(
                    [row["from"] for row in report["events"]],
                    [step["at"] for step in scenario["steps"]],
                )
                self.assertEqual(
                    [row["expected"] for row in report["events"]],
                    [step.get("expect") for step in scenario["steps"]],
                )
                for row in report["events"]:
                    if row["from"] is not None:
                        self.assertIsInstance(row["prompt"], str)
                        self.assertTrue(row["prompt"].strip())

    def test_material_reset_recovery_and_conditional_skill_routes(self) -> None:
        material = self.report("product-material-reset")
        commits = [row for row in material["events"] if row["from"] == "commit"]
        self.assertEqual(len(commits), 4)
        self.assertEqual(
            [row["to"] for row in commits],
            ["review", "review", "review", "final-verify"],
        )
        # The material pass makes two later trivial passes necessary before the
        # controller releases the fresh final verification action.
        self.assertEqual(
            [step["outcome"] for step in dry_run.scenarios()["product-material-reset"]["steps"]
             if step["at"] == "commit"],
            ["trivial", "material", "trivial", "trivial"],
        )

        blocked = self.report("product-block-resume")["events"]
        self.assertEqual(
            next(row for row in blocked if row["event"] == "blocked")["to"],
            None,
        )
        self.assertEqual(
            next(row for row in blocked if row["event"] == "blocked")["status"],
            "blocked",
        )
        self.assertEqual(
            next(row for row in blocked if row["event"] == "resume")["to"],
            "test-author",
        )

        paused = self.report("product-pause-resume")["events"]
        pause = next(row for row in paused if row["from"] == "carry-forward" and row["paused"])
        self.assertEqual((pause["to"], pause["status"]), ("carry-forward", "active"))
        resume = next(row for row in paused if row["event"] == "resume")
        self.assertEqual((resume["to"], resume["paused"]), ("carry-forward", False))

        repaired = self.report("step-plan-repair")["events"]
        repair = next(row for row in repaired if row["event"] == "repair")
        self.assertEqual((repair["to"], repair["paused"]), ("step-plan-disposition", True))
        self.assertEqual(
            next(row for row in repaired if row["event"] == "resume")["to"],
            "step-plan-disposition",
        )

        ordinary = self.report("product")["events"]
        conditional = self.report("product-skill")["events"]
        self.assertNotIn("skill-validate", [row["from"] for row in ordinary])
        skill_rows = [row for row in conditional if row["from"] == "skill-validate"]
        self.assertEqual(len(skill_rows), 2)
        self.assertTrue(all(row["to"] == "verify" for row in skill_rows))
        self.assertTrue(
            all(
                row["to"] == "skill-validate"
                for row in conditional
                if row["from"] == "iteration-document"
            )
        )

    def test_altered_expected_edge_and_missing_prompt_or_duty_fail(self) -> None:
        altered = copy.deepcopy(dry_run.scenarios()["product"])
        altered["name"] = "wrong-edge"
        altered["steps"][0]["expect"] = "commit"
        report = dry_run.run_scenario(altered, self.api())
        self.assertFalse(report["ok"])
        self.assertIn("expected 'commit'", report["error"])

        no_prompt_api = self.api()
        no_prompt_api["PROMPTS"] = dict(protocol.PROMPTS)
        no_prompt_api["MANAGED_PROMPTS"] = dict(protocol.MANAGED_PROMPTS)
        no_prompt_api["PROMPTS"].pop("test-author")
        no_prompt_api["MANAGED_PROMPTS"].pop("test-author", None)
        missing_prompt = dry_run.run_scenario(
            dry_run.scenarios()["product"], no_prompt_api
        )
        self.assertFalse(missing_prompt["ok"])
        self.assertIn("missing production prompt for test-author", missing_prompt["error"])

        no_duty_api = self.api()
        no_duty_api["PROMPTS"] = dict(protocol.PROMPTS)
        no_duty_api["MANAGED_PROMPTS"] = dict(protocol.MANAGED_PROMPTS)
        no_duty_api["PROMPTS"]["test-author"] = "Return a concise summary only."
        no_duty_api["MANAGED_PROMPTS"].pop("test-author", None)
        missing_duty = dry_run.run_scenario(
            dry_run.scenarios()["product"], no_duty_api
        )
        self.assertFalse(missing_duty["ok"])
        self.assertIn("prompt missing required duty", missing_duty["error"])

    def test_prompt_wording_and_whitespace_are_not_transition_contracts(self) -> None:
        api = self.api()
        api["PROMPTS"] = dict(protocol.PROMPTS)
        api["MANAGED_PROMPTS"] = dict(protocol.MANAGED_PROMPTS)
        api["PROMPTS"]["test-author"] = (
            "\n  Author executable tests\n\nfor every retained CASE; return a summary.  \n"
        )
        api["MANAGED_PROMPTS"].pop("test-author", None)
        report = dry_run.run_scenario(dry_run.scenarios()["product"], api)
        self.assertTrue(report["ok"], report.get("error"))

    def test_shared_stage_instruction_uses_managed_override_and_history_normalization(self) -> None:
        plain_commit = packets.stage_instruction("commit", self.api(), managed=False)
        managed_commit = packets.stage_instruction("commit", self.api(), managed=True)
        self.assertIsInstance(plain_commit, str)
        self.assertIsInstance(managed_commit, str)
        self.assertNotEqual(plain_commit, managed_commit)
        self.assertIn("all recorded review", managed_commit)

        normalized = packets.stage_instruction(
            "objective-review", self.api(), managed=True, history_limit=3
        )
        self.assertIsInstance(normalized, str)
        self.assertIn("--limit 3", normalized)
        self.assertNotIn("--limit 10", normalized)
        self.assertIn("current 3", normalized)

    def test_cli_list_default_custom_json_markdown_and_failures(self) -> None:
        with tempfile.TemporaryDirectory(prefix="shiploop-graph-driver-") as raw:
            root = Path(raw)
            listed = self.run_cli(root, "--list")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertEqual(set(listed.stdout.splitlines()), set(EXPECTED_SCENARIOS))

            default = self.run_cli(root)
            self.assertEqual(default.returncode, 0, default.stdout + default.stderr)
            self.assertIn("SIMULATION ONLY", default.stdout)
            self.assertEqual(default.stdout.count("PASS "), 16)

            valid_path = root / "custom.json"
            valid_path.write_text(
                json.dumps({
                    "name": "one-edge",
                    "profile": "research",
                    "steps": [{"at": "research-review", "expect": "research-plan"}],
                }),
                encoding="utf-8",
            )
            custom = self.run_cli(root, "--script", str(valid_path))
            self.assertEqual(custom.returncode, 0, custom.stdout + custom.stderr)
            self.assertIn("PASS one-edge", custom.stdout)

            as_json = self.run_cli(root, "--scenario", "product-skill", "--format", "json")
            self.assertEqual(as_json.returncode, 0, as_json.stderr)
            parsed = json.loads(as_json.stdout)
            self.assertTrue(parsed["simulation_only"])
            self.assertEqual(parsed["scenarios"][0]["name"], "product-skill")
            self.assertTrue(parsed["scenarios"][0]["ok"])

            markdown = self.run_cli(root, "--scenario", "research", "--format", "markdown")
            self.assertEqual(markdown.returncode, 0, markdown.stderr)
            self.assertIn("### 1. research-review", markdown.stdout)
            self.assertIn("Run history first", markdown.stdout)

            malformed = root / "malformed.json"
            malformed.write_text('{"profile": ', encoding="utf-8")
            bad_json = self.run_cli(root, "--script", str(malformed))
            self.assertEqual(bad_json.returncode, 2)
            self.assertIn("Graph dry-run failed", bad_json.stdout)

            unsupported = root / "unsupported.json"
            unsupported.write_text(
                json.dumps({
                    "profile": "research",
                    "steps": [{
                        "at": "research-review",
                        "event": "sideways",
                        "expect": "research-plan",
                    }],
                }),
                encoding="utf-8",
            )
            rejected = self.run_cli(root, "--script", str(unsupported))
            self.assertEqual(rejected.returncode, 1, rejected.stdout + rejected.stderr)
            self.assertIn("unknown synthetic event: sideways", rejected.stdout)

    def test_protocol_entrypoint_never_discovers_or_mutates_a_live_run(self) -> None:
        def forbidden(*_args, **_kwargs):
            raise AssertionError("graph dry-run attempted live repository or storage work")

        output = StringIO()
        with (
            patch.object(protocol, "repo_for", side_effect=forbidden),
            patch.object(protocol, "git", side_effect=forbidden),
            patch.object(protocol, "persist", side_effect=forbidden),
            patch.object(store, "transaction", side_effect=forbidden),
            patch.object(subprocess, "run", side_effect=forbidden),
            redirect_stdout(output),
        ):
            code = protocol.main(
                ForbiddenCore(), ["graph-dry-run", "--scenario", "product-skill"]
            )
        self.assertEqual(code, 0)
        self.assertIn("PASS product-skill", output.getvalue())

    def test_empty_directory_cli_preserves_existing_shiploop_state_bytes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="shiploop-graph-sentinel-") as raw:
            root = Path(raw)
            sentinel_dir = root / ".shiploop"
            sentinel_dir.mkdir()
            sentinel = sentinel_dir / "state.md"
            original = b"sentinel bytes: no graph dry-run state access\n"
            sentinel.write_bytes(original)

            result = self.run_cli(root, "--scenario", "research", "--format", "json")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(sentinel.read_bytes(), original)
            self.assertEqual({path.name for path in sentinel_dir.iterdir()}, {"state.md"})

    def test_relocated_shiploop_package_runs_without_repository_dependencies(self) -> None:
        with tempfile.TemporaryDirectory(prefix="shiploop-graph-portable-") as raw:
            root = Path(raw)
            portable = root / "portable shiploop package with spaces"
            shutil.copytree(
                SHIPLOOP,
                portable,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
            )
            scratch = root / "empty invocation directory"
            scratch.mkdir()
            environment = dict(os.environ)
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            environment["PYTHONNOUSERSITE"] = "1"
            environment.pop("PYTHONPATH", None)
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(portable / "scripts" / "shiploop"),
                    "graph-dry-run",
                    "--scenario",
                    "product-skill",
                    "--format",
                    "json",
                ],
                cwd=scratch,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertTrue(report["simulation_only"])
            self.assertEqual(report["scenarios"][0]["name"], "product-skill")
            self.assertTrue(report["scenarios"][0]["ok"])


if __name__ == "__main__":
    unittest.main()
