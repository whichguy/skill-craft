#!/usr/bin/env python3
"""Action-bound platform revalidation contracts and CLI regressions."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.machinery
import importlib.util
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

import shiploop_objectives as objectives  # noqa: E402
import shiploop_protocol as protocol  # noqa: E402
import shiploop_revalidation as revalidation  # noqa: E402
import shiploop_store as store  # noqa: E402


def load_action_walk_fixture():
    """Reuse the real public-CLI planning journey without duplicating it."""
    name = "shiploop_revalidation_action_walk_fixture"
    if name in sys.modules:
        return sys.modules[name]
    path = ROOT / "test" / "shiploop-action-walk.test.py"
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    if spec is None:
        raise RuntimeError("could not load ShipLoop action-walk fixture")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def outer_machine(*, promotion: str = "none") -> dict:
    """A valid selected route whose preparation is an outer operation."""
    revalidate_at = ["cold-resume", "before-external-operation"]
    promotion_record: dict[str, object]
    if promotion == "outer-loop":
        revalidate_at.append("before-promotion")
        promotion_record = {
            "mode": "outer-loop",
            "target": "authorized publication target",
            "step_id": None,
            "verification": "The documented entrypoint returns the expected result.",
        }
    else:
        promotion_record = {
            "mode": "none",
            "target": None,
            "step_id": None,
            "verification": "No publication target is selected for this fixture.",
        }
    return {
        "kind": "greenfield",
        "augment": False,
        "references": [{"path": "docs/platform.md", "why": "Selected route."}],
        "tools": ["platform-cli"],
        "mcp": [],
        "mcp_considered": "none(local test fixture)",
        "handles": [],
        "initiation": "none",
        "ui": False,
        "ui_craft": "none(local test fixture)",
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
            "rationale": "The requested artifact needs an authorized hosted target.",
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
                        "mode": "outer-before",
                        "step_id": None,
                        "prerequisites": ["A committed local baseline exists."],
                        "validation": "The isolated development target is initialized.",
                    },
                    "development_validation": {
                        "decision": "not-applicable",
                        "step_id": None,
                        "environment": None,
                        "expected_outcome": "No separate development validation is selected.",
                    },
                    "promotion": promotion_record,
                    "revalidate_at": revalidate_at,
                    "blocked_paths": [],
                }
            ],
        },
    }


def environment_body(machine: dict) -> str:
    return "Fixture environment.\n\n## machine\n```json\n" + json.dumps(machine) + "\n```\n"


def no_risk_policy() -> dict:
    return {
        "risk_policy_version": 1,
        "security": {
            "decision": "not-applicable",
            "rationale": "The fixture has no security-sensitive boundary.",
        },
        "fuzz": {
            "decision": "not-applicable",
            "rationale": "The fixture has no parser or untrusted input surface.",
        },
        "maintenance": {
            "decision": "not-applicable",
            "rationale": "The fixture adds no maintained dependency.",
        },
    }


class RequirementTests(unittest.TestCase):
    def test_marker_is_absent_only_for_legacy_and_explicit_values_fail_closed(self) -> None:
        self.assertFalse(protocol.platform_revalidation_current({}))
        for invalid in (None, False, 0, 1.0, "1", 2):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(protocol.ProtocolError, "platform revalidation protocol version"):
                    protocol.platform_revalidation_current(
                        {"platform_revalidation_protocol_version": invalid}
                    )

    def test_requirements_bind_stage_routes_and_frozen_environment_bytes(self) -> None:
        machine = outer_machine(promotion="outer-loop")
        with tempfile.TemporaryDirectory(prefix="shiploop-revalidation-req-") as tmp:
            run_dir = Path(tmp)
            body = environment_body(machine)
            (run_dir / "environment.md").write_text(body, encoding="utf-8")

            class Core:
                def load_environment(self, _root: Path):
                    return machine, []

            expected_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
            state = {
                "platform_revalidation_protocol_version": 1,
                "platform_discovery_protocol_version": 1,
                "environment_sha256": expected_hash,
            }
            self.assertEqual(
                protocol.platform_revalidation_requirements(
                    Core(), run_dir, state, "prepare"
                ),
                [
                    {
                        "platform_id": "hosted-dev",
                        "trigger": "before-external-operation",
                        "observed_role": "development-deployer",
                        "environment_sha256": expected_hash,
                        "route": "outer-preparation",
                    }
                ],
            )
            self.assertEqual(
                protocol.platform_revalidation_requirements(
                    Core(), run_dir, state, "publish"
                ),
                [
                    {
                        "platform_id": "hosted-dev",
                        "trigger": "before-external-operation",
                        "observed_role": "development-deployer",
                        "environment_sha256": expected_hash,
                        "route": "outer-promotion",
                    },
                    {
                        "platform_id": "hosted-dev",
                        "trigger": "before-promotion",
                        "observed_role": "development-deployer",
                        "environment_sha256": expected_hash,
                        "route": "outer-promotion",
                    },
                ],
            )
            self.assertEqual(
                protocol.platform_revalidation_requirements(
                    Core(), run_dir, {}, "prepare"
                ),
                [],
            )

    def test_validator_rejects_missing_extra_duplicate_stale_secret_and_role_mismatch(self) -> None:
        requirements = [
            {
                "platform_id": "hosted-dev",
                "trigger": "before-external-operation",
                "observed_role": "development-deployer",
                "environment_sha256": "a" * 64,
                "route": "outer-preparation",
            }
        ]
        row = {
            "platform_id": "hosted-dev",
            "trigger": "before-external-operation",
            "action_id": "run-123456789abc",
            "environment_sha256": "a" * 64,
            "observed_role": "development-deployer",
            "status": "ready",
            "evidence": "A non-mutating role observation is recorded in the operator log.",
            "performed_before_operation": True,
        }
        self.assertEqual(
            revalidation.validate_result(
                {"platform_revalidation": [row]},
                requirements,
                action_id="run-123456789abc",
            ),
            [],
        )
        variants = {
            "missing": ({}, "platform_revalidation is required"),
            "duplicate": (
                {"platform_revalidation": [row, dict(row)]},
                "duplicates platform/trigger",
            ),
            "extra": (
                {
                    "platform_revalidation": [
                        row,
                        dict(row, platform_id="unselected-route"),
                    ]
                },
                "unexpected platform/trigger",
            ),
            "stale": (
                {"platform_revalidation": [dict(row, action_id="other-123456789abc")]},
                "action_id must bind the current action",
            ),
            "role": (
                {"platform_revalidation": [dict(row, observed_role="wrong-role")]},
                "observed_role does not match",
            ),
            "not-ready": (
                {"platform_revalidation": [dict(row, status="blocked")]},
                "status must be ready",
            ),
            "secret": (
                {
                    "platform_revalidation": [
                        dict(row, evidence="Authorization: Bearer abcdefghijklmnop")
                    ]
                },
                "evidence must not contain credential-like text",
            ),
            "unhashable-trigger": (
                {"platform_revalidation": [dict(row, trigger=[])]},
                "trigger must be a supported trigger",
            ),
        }
        for name, (result, expected) in variants.items():
            with self.subTest(name=name):
                self.assertIn(
                    expected,
                    "\n".join(
                        revalidation.validate_result(
                            result,
                            requirements,
                            action_id="run-123456789abc",
                        )
                    ),
                )
        non_string_key = dict(row)
        non_string_key[1] = "unexpected"
        self.assertIn(
            "unsupported or non-string keys",
            "\n".join(
                revalidation.validate_result(
                    {"platform_revalidation": [non_string_key]},
                    requirements,
                    action_id="run-123456789abc",
                )
            ),
        )
        self.assertEqual(
            revalidation.validate_result({}, [], action_id="run-123456789abc"), []
        )


class RevalidationCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="shiploop-revalidation-cli-")
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
        self.git("config", "user.name", "Revalidation Test")
        self.git("config", "user.email", "revalidation@example.invalid")
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
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.strip()

    def cli(self, *args: str, code: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=str(self.repo),
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def record(self, name: str, value: dict) -> str:
        path = self.root / name
        store.write_record(path, value)
        return str(path)

    def prepare_action(self) -> tuple[dict, str]:
        self.cli("init", "--repo", str(self.repo), "--prompt", "Prepare a hosted target.")
        state = store.read_record(self.run_dir / "state.md")
        self.assertEqual(state["platform_revalidation_protocol_version"], 1)
        machine = outer_machine()
        body = environment_body(machine)
        (self.run_dir / "environment.md").write_text(body, encoding="utf-8")
        store.write_record(
            self.run_dir / "lifecycle.md",
            {
                "acceptance": ["The isolated target is initialized."],
                "preparation": "outer-before",
                "publish": "none",
                "quality": True,
                "reason": "The selected target needs one bounded preparation operation.",
                "risk_policy": no_risk_policy(),
            },
        )
        store.write_record(
            self.run_dir / "backchain" / "plan.md",
            {
                "goal": "Prepare the selected hosted target.",
                "initial_state": "A committed local baseline exists.",
                "unresolved": [],
                "steps": [
                    {
                        "id": "S1",
                        "activity": "preparation",
                        "inputs": [],
                    }
                ],
            },
        )
        state["environment_sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
        protocol.action(state, "plan", "prepare")
        store.write_record(self.run_dir / "state.md", state, "ShipLoop state")
        return state, body

    @staticmethod
    def attestation(state: dict, environment_body_text: str) -> dict:
        return {
            "platform_id": "hosted-dev",
            "trigger": "before-external-operation",
            "action_id": state["action"]["id"],
            "environment_sha256": hashlib.sha256(
                environment_body_text.encode("utf-8")
            ).hexdigest(),
            "observed_role": "development-deployer",
            "status": "ready",
            "evidence": "A non-mutating target-role observation is recorded in the operator log.",
            "performed_before_operation": True,
        }

    def complete_current(self, payload: dict, name: str, *, code: int = 0) -> subprocess.CompletedProcess[str]:
        state = store.read_record(self.run_dir / "state.md")
        return self.cli(
            "complete",
            "--run-dir",
            str(self.run_dir),
            "--action",
            state["action"]["id"],
            "--result",
            self.record(name, payload),
            code=code,
        )

    def advance_prepare_objective_to_apply(self) -> tuple[dict, dict]:
        initial, body = self.prepare_action()
        attestation = self.attestation(initial, body)
        self.complete_current(
            {
                "summary": "The authorized preparation operation is reported.",
                "evidence": "The isolated target preparation has the expected host-reported outcome.",
                "platform_revalidation": [attestation],
            },
            "prepare.md",
        )
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
        self.complete_current(
            {
                "summary": "Preparation candidate review is complete.",
                "findings": [],
                "assessment": {
                    key: f"Reviewed {key} against the durable preparation candidate."
                    for key in objectives.ASSESSMENT_KEYS
                },
                "history_assessment": "The available full commit history was read before this review.",
                "test_review": "The objective verification will check the retained candidate.",
                "learnings": "The initial host-reported preparation evidence remains the authority.",
            },
            "objective-review.md",
        )
        self.complete_current(
            {
                "summary": "Preparation candidate plan is complete.",
                "addresses": [],
                "body": "# Objective plan\n\nThe initial operation evidence must remain unchanged.\n",
                "learnings": "No candidate change is justified before objective verification.",
            },
            "objective-plan.md",
        )
        return store.read_record(self.run_dir / "state.md"), attestation

    def test_missing_attestation_rejects_real_prepare_callback_without_persisting_result(self) -> None:
        state, _body = self.prepare_action()
        before = (self.run_dir / "state.md").read_bytes()
        result = self.complete_current(
            {
                "summary": "The preparation operation is reported without its required proof.",
                "evidence": "The host reports a preparation outcome.",
            },
            "missing-proof.md",
            code=2,
        )
        self.assertIn("platform_revalidation is required", result.stderr)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), before)
        self.assertFalse((self.run_dir / "results" / f"{state['action']['id']}.md").exists())

    def test_invalid_explicit_marker_blocks_a_cold_cli_read(self) -> None:
        self.cli("init", "--repo", str(self.repo), "--prompt", "Check cold marker validation.")
        state = store.read_record(self.run_dir / "state.md")
        state["platform_revalidation_protocol_version"] = None
        store.write_record(self.run_dir / "state.md", state, "ShipLoop state")
        result = self.cli("next", "--run-dir", str(self.run_dir), code=2)
        self.assertIn("platform revalidation protocol version", result.stderr)

    def test_valid_attestation_persists_under_original_prepare_action(self) -> None:
        state, body = self.prepare_action()
        row = self.attestation(state, body)
        self.complete_current(
            {
                "summary": "The authorized preparation operation is reported.",
                "evidence": "The isolated target preparation has the expected host-reported outcome.",
                "platform_revalidation": [row],
            },
            "valid-proof.md",
        )
        accepted = store.read_record(self.run_dir / "results" / f"{state['action']['id']}.md")
        self.assertEqual(accepted["platform_revalidation"], [row])
        advanced = store.read_record(self.run_dir / "state.md")
        self.assertEqual(advanced["stage"], "objective-review")
        self.assertEqual(
            store.read_record(self.run_dir / advanced["objective"]["candidate"])["platform_revalidation"],
            [row],
        )

    def test_objective_apply_cannot_rewrite_the_original_prepare_attestation(self) -> None:
        state, original = self.advance_prepare_objective_to_apply()
        self.assertEqual(state["stage"], "objective-apply")
        candidate = store.read_record(self.run_dir / state["objective"]["candidate"])
        changed = deepcopy(original)
        changed["action_id"] = state["action"]["id"]
        candidate["platform_revalidation"] = [changed]
        before = (self.run_dir / "state.md").read_bytes()
        result = self.complete_current(
            {
                "summary": "This invalid objective apply attempts to recertify an earlier operation.",
                "candidate": candidate,
                "material": True,
                "addresses": [],
                "resolutions": [],
                "test_changes": "No test change can make an objective-apply callback an external operation.",
                "learnings": "The initial action-bound proof must remain immutable.",
            },
            "rewritten-proof.md",
            code=2,
        )
        self.assertIn("must retain the original action-bound platform revalidation", result.stderr)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), before)
        accepted = store.read_record(self.run_dir / "results" / f"{original['action_id']}.md")
        self.assertEqual(accepted["platform_revalidation"], [original])


class ExternalPreparationFinalizationTests(unittest.TestCase):
    def test_real_prepare_objective_finalization_reuses_the_original_action_proof(self) -> None:
        """Exercise the supported finalization bypass through the public CLI.

        The reusable fixture reaches the genuine planning/sequence bridge first;
        this test changes only its selected survey route and inserts the
        required initial host attestation before the preparation objective.
        """
        action_walk = load_action_walk_fixture()
        fixture = action_walk.ShipLoopActionWalkFixture(methodName="runTest")
        fixture.setUp()
        try:
            fixture.fixture_preparation = "outer-before"
            fixture.machine_markdown = lambda: environment_body(outer_machine())

            def integrated_research_state(revision="initial"):
                """Mirror the selected frozen platform/interface identity.

                This fixture deliberately changes the inherited survey from
                local-only to an applicable hosted route, so its research
                evidence must make the same scoped declaration rather than
                weakening the v1 context validator.
                """
                platform = outer_machine()["platform_discovery"]["platforms"][0]
                platform_id = platform["id"]
                interface_name = platform["interfaces"][0]["name"]
                source_id = "SRC-HOSTED-001"
                role_id = "ROLE-hosted"
                writer_id = "IF-platform-cli"
                operator_id = "IF-operator"
                interaction_id = "IC-prepare"
                return {
                    "questions": [
                        {
                            "id": "RQ-001",
                            "question": "Which selected hosted writer and safe preparation boundary apply to this fixture?",
                            "origin": "prompt discovery: selected hosted preparation route",
                            "status": "resolved",
                            "answer": "Use the surveyed platform-cli writer through the recorded outer preparation route.",
                            "sources": [source_id],
                            "revalidate": "Recheck the selected role and writer before the external operation.",
                            "rationale": "The fixture's preparation route depends on the selected hosted platform.",
                            "parents": [],
                            "contract_refs": [interaction_id],
                            "role_refs": [role_id],
                            "interface_refs": [operator_id, writer_id],
                        }
                    ],
                    "sources": [
                        {
                            "id": source_id,
                            "reference": "fixture hosted platform survey",
                            "authority": "local",
                            "version_or_observed_at": f"fixture-{revision}",
                            "supports": "The selected platform identity, writer, and authorized preparation route.",
                            "limitations": "This fixture record does not prove a live external operation succeeded.",
                        }
                    ],
                    "system_context": {
                        "version": 1,
                        "scope": "integrated",
                        "rationale": "The selected hosted writer and outer preparation operation affect this fixture.",
                        "roles": [
                            {
                                "id": role_id,
                                "label": "authorized hosted fixture role",
                                "status": "observed",
                                "permitted_actions": "Perform the recorded non-mutating readiness observation before the authorized preparation operation.",
                                "isolation": "The fixture uses the selected isolated development target and records no credential values.",
                                "platform_refs": [platform_id],
                                "source_refs": [source_id],
                                "revalidate": "Recheck role identity and authority immediately before external use.",
                            }
                        ],
                        "interfaces": [
                            {
                                "id": operator_id,
                                "kind": "operator",
                                "identity": "fixture host preparation caller",
                                "survey_ref": None,
                                "role_refs": [role_id],
                                "source_refs": [source_id],
                                "idiom": "Use the script-issued preparation callback and retain the original action proof.",
                                "status": "resolved",
                                "revalidate": "Recheck the current action before submitting the preparation result.",
                            },
                            {
                                "id": writer_id,
                                "kind": platform["interfaces"][0]["kind"],
                                "identity": "surveyed hosted platform writer",
                                "survey_ref": {"platform_id": platform_id, "name": interface_name},
                                "role_refs": [role_id],
                                "source_refs": [source_id],
                                "idiom": "Use the surveyed platform-cli writer rather than an overlapping mutation route.",
                                "status": "resolved",
                                "revalidate": "Recheck the selected writer and documented safe probe before external use.",
                            },
                        ],
                        "interactions": [
                            {
                                "id": interaction_id,
                                "caller_interface_id": operator_id,
                                "callee_interface_id": writer_id,
                                "role_refs": [role_id],
                                "operation": "Record the action-bound hosted preparation readiness observation.",
                                "question_refs": ["RQ-001"],
                                "source_refs": [source_id],
                                "input_output": "The current action and frozen environment digest yield a recorded readiness attestation.",
                                "state_semantics": "The accepted result preserves the original action proof for later objective finalization.",
                                "failure_semantics": "A missing or stale safe observation blocks preparation without retrying an external effect.",
                                "idiom": "Use the documented preparation callback and platform revalidation result row.",
                                "risk": "high",
                                "depth_rationale": "External authority and retained action proof require the writer, action state, and finalization boundary.",
                                "status": "resolved",
                                "required": True,
                                "consumer_steps": ["S1", "S2"],
                            }
                        ],
                        "observations": [
                            {
                                "id": "OBS-code",
                                "kind": "code",
                                "status": "observed",
                                "summary": "The fixture uses the script-issued preparation callback and result record.",
                                "source_refs": [source_id],
                                "role_refs": [role_id],
                                "interface_refs": [operator_id],
                            },
                            {
                                "id": "OBS-state",
                                "kind": "state",
                                "status": "observed",
                                "summary": "Preparation retains the original action-bound attestation for later objective finalization.",
                                "source_refs": [source_id],
                                "role_refs": [role_id],
                                "interface_refs": [operator_id, writer_id],
                            },
                            {
                                "id": "OBS-system",
                                "kind": "system",
                                "status": "observed",
                                "summary": "The selected hosted writer is an external preparation boundary.",
                                "source_refs": [source_id],
                                "role_refs": [role_id],
                                "interface_refs": [writer_id],
                            },
                            {
                                "id": "OBS-role",
                                "kind": "environment-role",
                                "status": "observed",
                                "summary": "The selected hosted fixture role is recorded without credential values.",
                                "source_refs": [source_id],
                                "role_refs": [role_id],
                                "interface_refs": [writer_id],
                            },
                        ],
                    },
                }

            fixture.planning_research_state = integrated_research_state
            inherited_manifest = fixture.planning_manifest

            def integrated_planning_manifest(kind):
                manifest = inherited_manifest(kind)
                if kind != "research":
                    return manifest
                manifest = deepcopy(manifest)
                manifest["checks"][1]["argv"] = [
                    sys.executable,
                    "-B",
                    "-c",
                    (
                        "from pathlib import Path; "
                        "research = Path('.shiploop/research.md').read_text(); "
                        "evidence = Path('.shiploop/research-evidence.md').read_text(); "
                        "assert 'RQ-001' in research; assert 'SRC-HOSTED-001' in evidence"
                    ),
                ]
                return manifest

            fixture.planning_manifest = integrated_planning_manifest
            original_dag = fixture.initial_dag

            def selected_dag():
                dag = original_dag()
                for step in dag["steps"]:
                    step["prompt"] += (
                        "\nTools:\nUse: platform-cli\nDon't use: none\n"
                    )
                return dag

            fixture.initial_dag = selected_dag
            original_converge = fixture.converge_objective

            def converge(candidate: dict, **kwargs):
                if (
                    kwargs.get("label") == "preparation-readiness"
                    and fixture.state()["stage"] == "prepare"
                ):
                    current = fixture.state()
                    candidate = dict(
                        candidate,
                        platform_revalidation=[
                            {
                                "platform_id": "hosted-dev",
                                "trigger": "before-external-operation",
                                "action_id": current["action"]["id"],
                                "environment_sha256": hashlib.sha256(
                                    (fixture.run_dir / "environment.md").read_bytes()
                                ).hexdigest(),
                                "observed_role": "development-deployer",
                                "status": "ready",
                                "evidence": "A non-mutating target-role observation is recorded in the operator log.",
                                "performed_before_operation": True,
                            }
                        ],
                    )
                return original_converge(candidate, **kwargs)

            fixture.converge_objective = converge
            state = fixture.bootstrap_to_first_step_plan()
            self.assertEqual(state["stage"], "step-plan")
            binding = state["objective"]["platform_revalidation"]
            source = store.read_record(
                fixture.run_dir / "results" / f"{binding['action_id']}.md"
            )
            preparation = store.read_record(fixture.run_dir / "preparation.md")
            self.assertEqual(
                preparation["platform_revalidation"], source["platform_revalidation"]
            )
            self.assertEqual(
                source["platform_revalidation"][0]["action_id"], binding["action_id"]
            )
        finally:
            fixture.tearDown()


if __name__ == "__main__":
    unittest.main()
