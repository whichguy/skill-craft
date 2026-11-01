#!/usr/bin/env python3
"""Offline calibration for four matched tests-only scope conditions; no model is started."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "test" / "shiploop_e2e"
SUITE = HARNESS / "stage_suite"
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SUITE))
sys.path.insert(0, str(HARNESS))
sys.path.insert(0, str(SCRIPTS))
import shiploop_navigator as navigator  # noqa: E402
import shiploop_store as store  # noqa: E402
import stage_build as sb  # noqa: E402
import stage_live  # noqa: E402
import stage_oracle  # noqa: E402


SCENARIOS = (
    "discovery/original-test-only",
    "discovery/workflow-records-permitted",
    "discovery/workflow-records-prohibited",
    "discovery/original-empty-home",
)
ENV = {**os.environ, "SHIPLOOP_PROGRESS": "off", "SHIPLOOP_KEEPALIVE": "off", "PYTHONDONTWRITEBYTECODE": "1"}


class ScopeDiscoveryCalibration(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="shiploop-scope-discovery-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_request_text_must_be_nonempty_string(self) -> None:
        sc = sb.load(SCENARIOS[0])
        for value in ("", "   ", 7, []):
            with self.subTest(value=value):
                data = copy.deepcopy(sc.data)
                data["request_text"] = value
                problems = sb.validate(data, sc.dir)
                self.assertIn("request_text must be a non-empty string", problems)

    def test_request_text_overrides_only_the_selected_case_prompt(self) -> None:
        sc = sb.load(SCENARIOS[0])
        original_case = sb.step_cases()[sc.data["request_from"]]
        original_prompt = original_case["prompt"]
        built_case = sb._buildable(sc)
        self.assertEqual(
            hashlib.sha256(sc.data["request_text"].encode("utf-8")).hexdigest(),
            "a1565688a29995db56ca3cc4defd24cc3ce0136105d3410e8284232125b92fb9",
        )
        self.assertEqual(sb.load(SCENARIOS[3]).data["request_text"], sc.data["request_text"])
        self.assertEqual(built_case["prompt"], sc.data["request_text"])
        self.assertEqual(built_case["work_item"], original_case["work_item"])
        self.assertEqual(built_case["checks"], original_case["checks"])
        self.assertEqual(sb.step_cases()[sc.data["request_from"]]["prompt"], original_prompt)

    def test_each_literal_request_reaches_the_discovery_run_and_packet(self) -> None:
        for scenario_id in SCENARIOS:
            with self.subTest(scenario=scenario_id):
                sc = sb.load(scenario_id)
                expected = sc.data["request_text"]
                bundle = sb.render(sc, self.root / scenario_id.replace("/", "-"))
                saved_request = (bundle.run_dir / "request.md").read_text(encoding="utf-8")
                self.assertIn(expected, saved_request)
                self.assertIsNotNone(bundle.packet)
                self.assertIn("Original request: RUN/request.md", bundle.packet or "")
                checks = stage_oracle.run_checks(sc.data["render"], bundle)
                self.assertTrue(all(row["pass"] for row in checks), checks)
                tree_check = stage_oracle.run_checks([{"changed_only": []}], bundle)
                self.assertTrue(tree_check[0]["pass"], tree_check[0])

    def test_reference_oracles_distinguish_success_from_block_and_noop(self) -> None:
        selectors = [*SCENARIOS]
        done = subprocess.run(
            [sys.executable, str(SUITE / "stages.py"), "verify", "--json", *selectors],
            cwd=ROOT,
            env=ENV,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        document = json.loads(done.stdout)
        self.assertEqual(document["total"], {"scenarios": len(selectors), "passed": len(selectors), "failed": 0, "skipped": 0})
        self.assertEqual({row["id"] for row in document["scenarios"]}, set(selectors))
        for row in document["scenarios"]:
            self.assertEqual(row["result"], "pass", row)
            self.assertEqual(row["notes"], [], row)

    def test_allowed_scope_oracles_require_the_discovery_environment_artifact(self) -> None:
        for scenario_id in (SCENARIOS[0], SCENARIOS[1], SCENARIOS[3]):
            sc = sb.load(scenario_id)
            p1_file_checks = [check for check in sc.data["oracle"]
                              if check.get("proves") == "P1" and check.get("file") == "docs/shiploop/environment.md"]
            self.assertTrue(p1_file_checks, f"{scenario_id}: P1 must be grounded in the Discovery artifact")
            self.assertTrue(any(check.get("unchanged") is False for check in p1_file_checks), scenario_id)
            planted = [row["id"] for row in sc.data["planted"]]
            controls = [row["id"] for row in sc.data["controls"]]

            for reference, expected_p1 in (("good", True), ("bad-keyword-only-no-record", False)):
                with self.subTest(scenario=scenario_id, reference=reference):
                    bundle, _ = sb.reference_bundle(sc, reference, self.root / f"{sc.name}-{reference}")
                    found = stage_oracle.verdict(
                        planted,
                        controls,
                        stage_oracle.run_checks(sc.data["oracle"], bundle),
                    )
                    self.assertEqual(found["caught"]["P1"], expected_p1, found)
                    self.assertTrue(found["held"]["C1"], found)

    def test_blocker_oracle_accepts_a_concise_documentation_permission_question(self) -> None:
        sc = sb.load("discovery/workflow-records-prohibited")
        bundle, _ = sb.reference_bundle(sc, "good", self.root / "concise-block")
        bundle.result["summary"] = "Permission is needed before continuing."
        bundle.result["awaiting"]["question"] = "May I update docs/shiploop/environment.md?"
        rows = stage_oracle.run_checks(sc.data["oracle"], bundle)
        self.assertTrue(rows)
        self.assertTrue(all(row["pass"] for row in rows), rows)

    def test_builder_and_reference_seed_trees_match_for_both_home_modes(self) -> None:
        for scenario_id in SCENARIOS:
            with self.subTest(scenario=scenario_id):
                sc = sb.load(scenario_id)
                options = sc.data.get("options") or {}
                expects_home = options.get("seed_home", True)
                built = sb.build(sc, self.root / f"build-{sc.name}")
                reference, _ = sb.reference_bundle(sc, "good", self.root / f"reference-{sc.name}")

                for relative in ("docs/shiploop/environment.md", "docs/shiploop/spec.md"):
                    live_seed = built.worktree / relative
                    reference_seed = reference.seed_tree / relative
                    self.assertEqual(live_seed.is_file(), reference_seed.is_file(), relative)
                    if reference_seed.is_file():
                        self.assertEqual(live_seed.read_bytes(), reference_seed.read_bytes(), relative)
                    self.assertEqual(reference_seed.is_file(), expects_home, f"{scenario_id}: {relative}")

    def test_seed_home_option_is_optional_and_strictly_boolean(self) -> None:
        sc = sb.load(SCENARIOS[0])
        self.assertIs((sc.data.get("options") or {}).get("seed_home", True), True)
        for value in (None, 0, 1, "false", [], {}):
            with self.subTest(value=value):
                data = copy.deepcopy(sc.data)
                data["options"]["seed_home"] = value
                problems = sb.validate(data, sc.dir)
                self.assertIn("options.seed_home must be a boolean", problems)
        for value in (True, False):
            with self.subTest(value=value):
                data = copy.deepcopy(sc.data)
                data["options"]["seed_home"] = value
                self.assertNotIn("options.seed_home must be a boolean", sb.validate(data, sc.dir))

    def test_live_path_gives_the_override_to_the_host_and_records_it(self) -> None:
        sc = sb.load(SCENARIOS[0])
        expected = sc.data["request_text"]
        out = self.root / "live-sample"
        out.mkdir()
        worktree = self.root / "worktree"
        worktree.mkdir()
        built = sb.Built(
            run_dir=self.root / "run",
            worktree=worktree,
            cli=self.root / "cli",
            stage="discovery",
            issued=True,
            settled=False,
            current_stage="discovery",
            history_added=[],
            seeded={"action": "scope-action", "run_dir": str(self.root / "run")},
        )
        seen: dict[str, str] = {}

        class StopBeforeModel(RuntimeError):
            pass

        class Host:
            name, model, effort, skill = "codex", "fake-model", "high", "skill-craft:shiploop"
            backend = None
            marketplace = False

            def env(self, home: Path) -> dict:
                return {"HOME": str(home)}

            def install_plugin(self, env: dict, directory: Path) -> str:
                return "fake-plugin"

            def plugin_cli(self, home: Path) -> None:
                return None

            def invoke(self, skill: str, prompt: str) -> str:
                return f"/{skill} {prompt}"

            def argv(self, *, prompt: str, prompt_file: Path, **kwargs) -> list[str]:
                seen["opening"] = prompt
                seen["prompt_file"] = str(prompt_file)
                return ["fake-host"]

            def translator(self):
                return None

        with (
            mock.patch.object(stage_live, "seam_gap", return_value=""),
            mock.patch.object(stage_live.run, "require_installed"),
            mock.patch.object(stage_live.run, "shiploop_cli", return_value=self.root / "cli"),
            mock.patch.object(stage_live.run, "installed_versions", return_value={}),
            mock.patch.object(stage_live.run, "git", return_value="base\n"),
            mock.patch.object(stage_live.sb, "build", return_value=built),
            mock.patch.object(stage_live, "snapshot", return_value={}),
            mock.patch.object(stage_live, "drive", side_effect=StopBeforeModel),
            mock.patch.object(stage_live, "end_recorded_hosts", return_value={}),
            mock.patch.object(stage_live.lifecycle, "cleanup_line", return_value=None),
        ):
            with self.assertRaises(StopBeforeModel):
                stage_live._run_sample(
                    sc,
                    out,
                    host=Host(),
                    model="fake-model",
                    effort="high",
                    plugin_dir=self.root / "plugin",
                    ref=None,
                    overlay=None,
                    timeout=30,
                    permission_mode="default",
                    max_turns=None,
                    max_budget_usd=None,
                    quiet=True,
                    sample=1,
                )

        self.assertIn(expected, seen["opening"])
        self.assertEqual(Path(seen["prompt_file"]).parent, out)
        self.assertEqual((out / "prompt.txt").read_text(encoding="utf-8"), expected + "\n")

    def test_valid_blocked_discovery_is_a_live_terminal(self) -> None:
        sc = sb.load(SCENARIOS[2])
        built = sb.build(sc, self.root / "blocked-terminal")
        before = store.read_record(built.run_dir / "state.md")
        action = dict(navigator.current_action(before))
        result = json.loads((sc.dir / "reference" / "good" / "result.json").read_text(encoding="utf-8"))
        after = navigator.apply(before, action["id"], result)

        self.assertEqual(after["status"], "blocked")
        self.assertTrue(stage_live.accepted_reached(after, action["id"]))
        accepted, source = stage_live.seeded_result(after, action["id"])
        self.assertEqual(source, "accepted")
        self.assertEqual(accepted["outcome"], result["outcome"])
        self.assertEqual(accepted["summary"], result["summary"])
        self.assertEqual(accepted["awaiting"]["question"], result["awaiting"]["question"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
