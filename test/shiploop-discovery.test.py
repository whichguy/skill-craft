#!/usr/bin/env python3
"""Focused contracts and real CLI regressions for platform discovery."""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_discovery as discovery  # noqa: E402
import shiploop_packets as packets  # noqa: E402
import shiploop_protocol as protocol  # noqa: E402
import shiploop_store as store  # noqa: E402


def local_machine() -> dict:
    return {
        "kind": "greenfield",
        "augment": False,
        "references": [],
        "tools": [],
        "mcp": [],
        "mcp_considered": "none(local fixture)",
        "handles": [],
        "initiation": "none",
        "ui": False,
        "ui_craft": "none(local fixture)",
        "exclusive": [],
        "platform_discovery": {
            "version": 1,
            "applicable": False,
            "rationale": "This fixture changes only a local repository artifact.",
            "platforms": [],
        },
    }


def remote_machine() -> dict:
    machine = local_machine()
    machine.update(
        {
            "references": [
                {
                    "path": "docs/platform.md",
                    "why": "Selected writer, interface, and target conventions.",
                }
            ],
            "tools": ["platform-cli"],
            "mcp_considered": "none(local fixture has no MCP reader)",
            "exclusive": [
                {
                    "artifact": "hosted application",
                    "use": "platform-cli",
                    "dont_use": [],
                }
            ],
            "layout": {"reserved": ["generated/"], "product": ["src/"]},
            "routing": {
                "user_entrypoint": "documented hosted application route",
                "reserved_routes": ["generated/"],
                "confirmation": "The selected target renders the expected response.",
                "source": "docs/platform.md",
            },
            "platform_discovery": {
                "version": 1,
                "applicable": True,
                "rationale": "The requested artifact requires an authorized hosted target.",
                "platforms": [
                    {
                        "id": "hosted-dev",
                        "artifact": "hosted application",
                        "writer": "platform-cli",
                        "interfaces": [
                            {
                                "kind": "cli",
                                "name": "platform-cli",
                                "version": "fixture-1",
                                "reference": "docs/platform.md",
                                "status": "ready",
                            }
                        ],
                        "identity": {
                            "expected_role": "development-deployer",
                            "observed_role": "development-deployer",
                            "safe_probe": "Read the selected target role without mutation.",
                            "status": "ready",
                        },
                        "authority": {
                            "required": True,
                            "rationale": "The selected writer needs target-scoped authority.",
                            "status": "observed",
                        },
                        "bootstrap": {
                            "mode": "dag",
                            "step_id": "S1",
                            "prerequisites": ["Committed local baseline exists."],
                            "validation": "The isolated development target is initialized.",
                        },
                        "development_validation": {
                            "decision": "required",
                            "step_id": "S2",
                            "environment": "isolated development target",
                            "expected_outcome": "The required boundary behavior succeeds there.",
                        },
                        "promotion": {
                            "mode": "dag",
                            "target": "authorized publication target",
                            "step_id": "S3",
                            "verification": "The documented entrypoint returns the expected result.",
                        },
                        "revalidate_at": [
                            "cold-resume",
                            "before-external-operation",
                            "before-promotion",
                        ],
                        "blocked_paths": [],
                    }
                ],
            },
        }
    )
    return machine


def platform_dag() -> dict:
    return {
        "steps": [
            {"id": "S1", "activity": "preparation", "inputs": []},
            {"id": "S2", "inputs": [{"need": "target initialized", "from": "S1"}]},
            {
                "id": "S3",
                "activity": "publish",
                "inputs": [{"need": "development validated", "from": "S2"}],
            },
        ]
    }


def platform_lifecycle() -> dict:
    return {"preparation": "dag", "publish": "dag"}


def environment_body(machine: dict) -> str:
    return "Survey fixture.\n\n## machine\n```json\n" + json.dumps(machine) + "\n```\n"


class DiscoverySchemaTests(unittest.TestCase):
    def test_explicit_local_case_is_required_and_projects_without_remote_facts(self) -> None:
        machine = local_machine()
        self.assertEqual(discovery.validate_machine(machine, required=True), [])
        projection = discovery.cold_projection(machine)
        self.assertEqual(projection["status"], "local-only")
        self.assertFalse(projection["applicable"])
        self.assertNotIn("platforms", projection)

    def test_missing_record_is_legacy_only_when_not_required(self) -> None:
        machine = local_machine()
        machine.pop("platform_discovery")
        self.assertEqual(discovery.validate_machine(machine), [])
        self.assertIn(
            "required for this new run",
            "\n".join(discovery.validate_machine(machine, required=True)),
        )

    def test_selected_writer_interface_and_ordered_routes_are_bound(self) -> None:
        machine = remote_machine()
        self.assertEqual(discovery.validate_machine(machine, required=True), [])
        self.assertEqual(
            discovery.validate_lifecycle(machine, platform_lifecycle(), platform_dag()),
            [],
        )
        self.assertEqual(
            discovery.step_routes(machine, "S2"),
            [{"platform": "hosted-dev", "route": "development-validation"}],
        )

    def test_writer_must_match_selected_interface_and_exclusive_route(self) -> None:
        machine = remote_machine()
        machine["platform_discovery"]["platforms"][0]["interfaces"][0]["name"] = "reader-cli"
        gaps = discovery.validate_machine(machine, required=True)
        self.assertIn("writer must match a selected interfaces[].name", "\n".join(gaps))

        malformed = remote_machine()
        malformed["exclusive"] = [{"artifact": [], "use": "platform-cli"}]
        gaps = discovery.validate_machine(malformed, required=True)
        self.assertIn("artifact/use must be strings", "\n".join(gaps))

    def test_blocked_selected_route_stays_applicable_and_blocks_sequence(self) -> None:
        machine = remote_machine()
        platform = machine["platform_discovery"]["platforms"][0]
        platform["authority"]["status"] = "blocked"
        platform["blocked_paths"] = ["Target authority has not been granted."]
        self.assertEqual(discovery.validate_machine(machine, required=True), [])
        gaps = discovery.validate_lifecycle(machine, platform_lifecycle(), platform_dag())
        self.assertIn("requires observed non-secret authority", "\n".join(gaps))
        self.assertTrue(machine["platform_discovery"]["applicable"])

    def test_blocked_paths_are_empty_without_blocks_and_aggregate_when_blocked(self) -> None:
        machine = remote_machine()
        platform = machine["platform_discovery"]["platforms"][0]
        platform["blocked_paths"] = ["A stale blocked-route explanation."]
        gaps = discovery.validate_machine(machine, required=True)
        self.assertIn("must be empty when no platform route is blocked", "\n".join(gaps))

        platform["authority"]["status"] = "blocked"
        platform["identity"]["status"] = "blocked"
        platform["blocked_paths"] = [
            "The selected route is blocked pending target role and authority."
        ]
        self.assertEqual(discovery.validate_machine(machine, required=True), [])

    def test_platform_discovery_rejects_sensitive_nested_text_without_echoing_it(self) -> None:
        secret = "privacy-secret-123"
        locations = (
            ("interface reference", lambda platform: platform["interfaces"][0], "reference"),
            ("identity probe", lambda platform: platform["identity"], "safe_probe"),
            ("authority rationale", lambda platform: platform["authority"], "rationale"),
            ("bootstrap prerequisite", lambda platform: platform["bootstrap"], "prerequisites"),
            (
                "development outcome",
                lambda platform: platform["development_validation"],
                "expected_outcome",
            ),
            ("promotion verification", lambda platform: platform["promotion"], "verification"),
            ("revalidation marker", lambda platform: platform, "revalidate_at"),
        )
        for label, container, key in locations:
            with self.subTest(location=label):
                machine = remote_machine()
                platform = machine["platform_discovery"]["platforms"][0]
                target = container(platform)
                if key in ("prerequisites", "revalidate_at"):
                    target[key] = [f"api_key={secret}"]
                else:
                    target[key] = f"Authorization: Bearer {secret}"
                gaps = discovery.validate_machine(machine, required=True)
                joined = "\n".join(gaps)
                self.assertIn("sensitive credential material", joined)
                self.assertNotIn(secret, joined)

        machine = remote_machine()
        machine["platform_discovery"]["rationale"] = f"api_key={secret}"
        gaps = discovery.validate_machine(machine, required=True)
        joined = "\n".join(gaps)
        self.assertIn("sensitive credential material", joined)
        self.assertNotIn(secret, joined)

        machine = remote_machine()
        platform = machine["platform_discovery"]["platforms"][0]
        platform["authority"]["status"] = "blocked"
        platform["blocked_paths"] = [f"https://user:{secret}@example.invalid"]
        gaps = discovery.validate_machine(machine, required=True)
        joined = "\n".join(gaps)
        self.assertIn("sensitive credential material", joined)
        self.assertNotIn(secret, joined)

        machine = remote_machine()
        platform = machine["platform_discovery"]["platforms"][0]
        platform[f"api_key={secret}"] = "benign unknown metadata"
        gaps = discovery.validate_machine(machine, required=True)
        joined = "\n".join(gaps)
        self.assertIn("sensitive credential material", joined)
        self.assertNotIn(secret, joined)

    def test_platform_discovery_keeps_non_string_errors_schema_specific(self) -> None:
        machine = remote_machine()
        machine["platform_discovery"]["platforms"][0]["identity"]["safe_probe"] = None
        gaps = discovery.validate_machine(machine, required=True)
        self.assertIn("safe_probe must be a nonempty string", "\n".join(gaps))

    def test_route_order_and_publish_none_are_rejected(self) -> None:
        machine = remote_machine()
        dag = platform_dag()
        dag["steps"][1]["inputs"] = []
        gaps = discovery.validate_lifecycle(machine, platform_lifecycle(), dag)
        self.assertIn("development validation must depend", "\n".join(gaps))

        with self.assertRaisesRegex(protocol.ProtocolError, "forbids a DAG"):
            protocol.validate_lifecycle_steps(
                {"steps": [{"activity": "publish"}]},
                {"preparation": "none", "publish": "none"},
            )

    def test_no_work_routes_use_null_target_or_environment_with_reason(self) -> None:
        machine = remote_machine()
        platform = machine["platform_discovery"]["platforms"][0]
        platform["bootstrap"] = {
            "mode": "none",
            "step_id": None,
            "prerequisites": [],
            "validation": "No target bootstrap is needed for this selected route.",
        }
        platform["development_validation"] = {
            "decision": "not-applicable",
            "step_id": None,
            "environment": None,
            "expected_outcome": "No external development validation route is selected.",
        }
        platform["promotion"] = {
            "mode": "none",
            "target": None,
            "step_id": None,
            "verification": "No publication target is in scope for this increment.",
        }
        platform["revalidate_at"] = ["cold-resume", "before-external-operation"]
        self.assertEqual(discovery.validate_machine(machine, required=True), [])
        self.assertEqual(
            discovery.validate_lifecycle(
                machine,
                {"preparation": "none", "publish": "none"},
                {"steps": [{"id": "S1", "inputs": []}]},
            ),
            [],
        )

    def test_revalidation_markers_are_canonical_and_complete(self) -> None:
        machine = remote_machine()
        platform = machine["platform_discovery"]["platforms"][0]
        platform["revalidate_at"] = ["after delivery"]
        gaps = discovery.validate_machine(machine, required=True)
        text = "\n".join(gaps)
        self.assertIn("unsupported trigger", text)
        self.assertIn("cold-resume", text)
        self.assertIn("before-external-operation", text)

    def test_explicit_null_state_marker_never_downgrades_to_legacy(self) -> None:
        self.assertFalse(protocol.platform_discovery_current({}))
        self.assertFalse(protocol.risk_policy_current({}))
        with self.assertRaisesRegex(protocol.ProtocolError, "platform discovery protocol version"):
            protocol.platform_discovery_current({"platform_discovery_protocol_version": None})
        with self.assertRaisesRegex(protocol.ProtocolError, "risk-policy protocol version"):
            protocol.risk_policy_current({"risk_policy_version": None})

    def test_explicit_legacy_risk_policy_null_is_not_absent(self) -> None:
        lifecycle = {
            "acceptance": ["A named observable acceptance case passes."],
            "preparation": "none",
            "publish": "none",
            "quality": True,
            "reason": "No separate preparation or publication is required.",
            "risk_policy": None,
        }
        with self.assertRaisesRegex(protocol.ProtocolError, "risk_policy is required"):
            protocol.planning_validate_lifecycle(lifecycle)

    def test_cold_projection_bounds_platform_details_and_keeps_page_route(self) -> None:
        machine = remote_machine()
        platform = machine["platform_discovery"]["platforms"][0]
        machine["platform_discovery"]["platforms"] = []
        machine["exclusive"] = []
        for number in range(4):
            row = deepcopy(platform)
            row["id"] = f"hosted-{number}"
            row["artifact"] = f"hosted-{number}-" + ("artifact" * 20)
            row["writer"] = f"platform-cli-{number}"
            row["interfaces"][0]["name"] = row["writer"]
            row["bootstrap"]["step_id"] = "S" + ("9" * 100)
            row["interfaces"].extend(
                deepcopy(row["interfaces"][0]) for _ in range(2)
            )
            machine["platform_discovery"]["platforms"].append(row)
            machine["exclusive"].append(
                {"artifact": row["artifact"], "use": row["writer"], "dont_use": []}
            )

        projection = discovery.cold_projection(machine)
        self.assertEqual(len(projection["platforms"]), 3)
        self.assertEqual(projection["platforms_omitted"], 1)
        first = projection["platforms"][0]
        self.assertEqual(len(first["interfaces"]), 2)
        self.assertEqual(first["interfaces_omitted"], 1)
        self.assertIn("artifact", first["truncated"])
        self.assertIn("step_id", first["bootstrap"]["truncated"])
        self.assertTrue(first["details_in_environment"])
        self.assertNotIn(
            "Read the selected target role without mutation.", json.dumps(projection)
        )

        class PacketCore:
            REF_DIR = ROOT / "skills" / "shiploop" / "references"

            def load_environment(self, _root: Path) -> tuple[dict, list]:
                return machine, []

        with tempfile.TemporaryDirectory(prefix="shiploop-packet-") as tmp:
            packet_root = Path(tmp)
            (packet_root / "environment.md").write_text("fixture", encoding="utf-8")
            lines, error = packets._environment_projection(PacketCore(), packet_root, {})
            self.assertIsNone(error)
            self.assertTrue(
                any(line.startswith("Full environment pages:") for line in lines)
            )
            packet_projection = json.loads(lines[0].split(": ", 1)[1])
            self.assertEqual(
                packet_projection["platform_discovery"]["platforms_omitted"], 1
            )


class DiscoveryCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="shiploop-discovery-cli-")
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.run_dir = self.repo / ".shiploop"
        self.env = dict(
            os.environ,
            PYTHONDONTWRITEBYTECODE="1",
            SHIPLOOP_BACKCHAIN_ROOT=str(ROOT / "test/fixtures/shiploop/backchain-leaf"),
        )
        self.git("init", "-q")
        self.git("config", "user.name", "Discovery Test")
        self.git("config", "user.email", "discovery@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", "/dev/null")
        self.git("commit", "--allow-empty", "-qm", "baseline")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def cli(self, *args: str, code: int = 0, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=str(cwd or self.repo),
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def prepare_survey(self) -> dict:
        self.cli(
            "init", "--repo", str(self.repo), "--execution-mode", "legacy",
            "--prompt", "Survey a generic route.",
        )
        state = store.read_record(self.run_dir / "state.md")
        self.assertEqual(state["platform_discovery_protocol_version"], 1)
        protocol.action(state, "validate-spec", "survey")
        store.write_record(self.run_dir / "state.md", state, "ShipLoop state")
        return state

    def result_path(self, name: str, value: dict) -> str:
        path = self.root / name
        store.write_record(path, value)
        return str(path)

    def complete_survey(self, state: dict, machine: dict, *, code: int = 0) -> subprocess.CompletedProcess[str]:
        result = self.result_path(
            "survey-result.md",
            {"summary": "Survey record prepared.", "body": environment_body(machine)},
        )
        return self.cli(
            "complete",
            "--run-dir",
            str(self.run_dir),
            "--action",
            state["action"]["id"],
            "--result",
            result,
            code=code,
        )

    def converge_survey_objective(self, candidate: dict) -> None:
        """Use the public CLI path to freeze a valid survey after two passes."""
        import shiploop_objectives as objectives

        def complete(value: dict, name: str) -> None:
            self.cli(
                "complete",
                "--run-dir",
                str(self.run_dir),
                "--action",
                store.read_record(self.run_dir / "state.md")["action"]["id"],
                "--result",
                self.result_path(name, value),
            )

        def manifest(name: str) -> str:
            return self.result_path(
                name,
                {
                    "checks": [
                        {
                            "id": "objective-lint",
                            "kind": "lint",
                            "argv": ["/usr/bin/true"],
                            "acceptance": ["objective survey"],
                        },
                        {
                            "id": "objective-acceptance",
                            "kind": "test",
                            "argv": ["/usr/bin/true"],
                            "acceptance": ["objective survey"],
                        },
                    ]
                },
            )

        for number in (1, 2):
            state = store.read_record(self.run_dir / "state.md")
            self.assertEqual(state["stage"], "objective-review")
            self.cli(
                "history",
                "--run-dir",
                str(self.run_dir),
                "--action",
                state["action"]["id"],
                "--limit",
                "10",
                "--skip",
                "0",
                "--full",
            )
            review_learning = f"Survey review {number} inspected durable history and the survey candidate."
            complete(
                {
                    "summary": f"Survey review {number} is complete.",
                    "findings": [],
                    "assessment": {
                        key: f"{key} was inspected against the durable survey candidate."
                        for key in objectives.ASSESSMENT_KEYS
                    },
                    "history_assessment": "All currently available full commit bodies were read before this decision.",
                    "test_review": "A local lint and acceptance check cover the frozen survey candidate.",
                    "learnings": review_learning,
                },
                f"survey-objective-{number}-review.md",
            )
            plan_learning = f"Survey plan {number} retains the valid candidate because no findings are open."
            complete(
                {
                    "summary": f"Survey plan {number} is complete.",
                    "addresses": [],
                    "body": "# Objective plan\n\nNo open findings require a candidate change.\n",
                    "learnings": plan_learning,
                },
                f"survey-objective-{number}-plan.md",
            )
            apply_learning = f"Survey apply {number} retains the exact valid candidate without product changes."
            complete(
                {
                    "summary": f"Survey apply {number} retains the candidate.",
                    "candidate": dict(candidate),
                    "material": False,
                    "addresses": [],
                    "resolutions": [],
                    "test_changes": "The existing objective lint and acceptance checks remain sufficient.",
                    "learnings": apply_learning,
                },
                f"survey-objective-{number}-apply.md",
            )
            verify_action = store.read_record(self.run_dir / "state.md")["action"]["id"]
            self.cli(
                "planning-verify",
                "--run-dir",
                str(self.run_dir),
                "--action",
                verify_action,
                "--manifest",
                manifest(f"survey-objective-{number}-checks.md"),
            )
            complete(
                {"summary": f"Survey objective checks {number} pass."},
                f"survey-objective-{number}-verify.md",
            )
            state = store.read_record(self.run_dir / "state.md")
            self.assertEqual(state["stage"], "objective-commit")
            receipt = store.read_record(self.run_dir / state["objective"]["receipt"])
            message = "\n\n".join(
                (
                    f"Objective survey audit {number}",
                    "Review:\n" + review_learning,
                    "Changes:\n" + plan_learning + "\n" + apply_learning,
                    "Validation:\nThe local lint and acceptance commands passed without source changes.",
                    "Key learnings:\n" + review_learning + "\n" + plan_learning + "\n" + apply_learning,
                    "ShipLoop-Iteration: " + receipt["current_pass"]["id"],
                )
            )
            self.git("commit", "--allow-empty", "--only", "-m", message)
            complete(
                {
                    "summary": f"Survey objective audit {number} is recorded.",
                    "commit": self.git("rev-parse", "HEAD"),
                },
                f"survey-objective-{number}-commit.md",
            )

        state = store.read_record(self.run_dir / "state.md")
        self.assertEqual(state["stage"], "objective-finalize")
        final_action = state["action"]["id"]
        self.cli(
            "planning-verify",
            "--run-dir",
            str(self.run_dir),
            "--action",
            final_action,
            "--manifest",
            manifest("survey-objective-final-checks.md"),
        )
        complete(
            {"summary": "Fresh final survey objective check passes."},
            "survey-objective-finalize.md",
        )

    def test_missing_new_run_decision_rejects_without_state_advance(self) -> None:
        state = self.prepare_survey()
        missing = local_machine()
        missing.pop("platform_discovery")
        before = (self.run_dir / "state.md").read_bytes()
        result = self.complete_survey(state, missing, code=2)
        self.assertIn("platform_discovery is required", result.stderr)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), before)
        self.assertFalse((self.run_dir / "environment.md").exists())

    def test_local_decision_is_accepted_and_cold_recoverable(self) -> None:
        state = self.prepare_survey()
        self.complete_survey(state, local_machine())
        self.converge_survey_objective(
            {"summary": "Survey record prepared.", "body": environment_body(local_machine())}
        )
        accepted = store.read_record(self.run_dir / "state.md")
        self.assertEqual(accepted["stage"], "research")
        unrelated = self.root / "unrelated"
        unrelated.mkdir()
        packet = self.cli("next", "--run-dir", str(self.run_dir), cwd=unrelated).stdout
        self.assertIn("local-only", packet)
        self.assertNotIn("Platform discovery guide:", packet)

    def test_inconsistent_selected_writer_route_is_rejected_without_state_advance(self) -> None:
        state = self.prepare_survey()
        machine = remote_machine()
        platform = machine["platform_discovery"]["platforms"][0]
        platform["writer"] = "other-cli"
        platform["interfaces"][0]["name"] = "other-cli"
        before = (self.run_dir / "state.md").read_bytes()
        result = self.complete_survey(state, machine, code=2)
        self.assertIn("writer/artifact must match", result.stderr)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
