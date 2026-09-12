#!/usr/bin/env python3
"""Pure contracts for ShipLoop's optional system-context research extension."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_research as research  # noqa: E402
import shiploop_step_planning as step_planning  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_system_context as system_context  # noqa: E402


def machine() -> dict:
    """Only frozen identity fields needed by the pure context validator."""
    return {
        "platform_discovery": {
            "applicable": True,
            "platforms": [
                {
                    "id": "delivery",
                    "interfaces": [{"name": "client"}, {"name": "service"}],
                }
            ],
        }
    }


def sources() -> list[dict]:
    return [
        {
            "id": "SRC-PLATFORM",
            "reference": "docs/platform-contract.md",
            "authority": "primary",
            "version_or_observed_at": "fixture-v1",
            "supports": "Frozen selected interface identities and environment role.",
            "limitations": "Does not prove live authority or delivery success.",
        },
        {
            "id": "SRC-CONTRACT",
            "reference": "docs/client-service-contract.md",
            "authority": "primary",
            "version_or_observed_at": "fixture-v1",
            "supports": "The supported invocation envelope and failure behavior.",
            "limitations": "Does not prove the current deployment is reachable.",
        },
        {
            "id": "SRC-CODE",
            "reference": "src/client.py",
            "authority": "local",
            "version_or_observed_at": "fixture-commit",
            "supports": "The current client wrapper and local state handling.",
            "limitations": "Does not replace the primary service contract.",
        },
    ]


def question(
    question_id: str,
    text: str,
    *,
    parents: list[str] | None = None,
    contracts: list[str] | None = None,
) -> dict:
    return {
        "id": question_id,
        "question": text,
        "origin": "prompt and discovery inventory",
        "status": "resolved",
        "answer": "The fixture has a source-backed bounded answer.",
        "sources": ["SRC-CONTRACT"],
        "revalidate": "Recheck if the selected interface version or client wrapper changes.",
        "rationale": "The decision affects the selected client/service boundary.",
        "parents": parents or [],
        "contract_refs": contracts or [],
        "role_refs": ["ROLE-dev"],
        "interface_refs": ["IF-client", "IF-service"],
    }


def evidence(*, unrelated: bool = False) -> dict:
    questions = [
        question(
            "RQ-contract",
            "Which supported service operation and envelope does the client call?",
            contracts=["IC-call"],
        ),
        question(
            "RQ-retry",
            "Who owns retry and duplicate-request handling at that boundary?",
            parents=["RQ-contract"],
            contracts=["IC-call"],
        ),
    ]
    interactions = [
        {
            "id": "IC-call",
            "caller_interface_id": "IF-client",
            "callee_interface_id": "IF-service",
            "role_refs": ["ROLE-dev"],
            "operation": "submit request through the documented envelope",
            "question_refs": ["RQ-contract", "RQ-retry"],
            "source_refs": ["SRC-CONTRACT"],
            "input_output": "JSON request maps to an accepted result or documented error envelope.",
            "state_semantics": "The service preserves idempotency state for a repeated request.",
            "failure_semantics": "Timeout and duplicate outcomes are reported without a second client retry layer.",
            "idiom": "Use the existing async client wrapper and its documented result decoder.",
            "risk": "high",
            "depth_rationale": "High duplicate-effect risk requires the caller, service state, and retry boundary.",
            "status": "resolved",
            "required": True,
            "consumer_steps": ["S1", "S2"],
        }
    ]
    if unrelated:
        questions.append(
            question(
                "RQ-unrelated",
                "Which unrelated maintenance operation is supported?",
                contracts=["IC-unrelated"],
            )
        )
        interactions.append(
            {
                **deepcopy(interactions[0]),
                "id": "IC-unrelated",
                "operation": "perform the unrelated maintenance operation",
                "question_refs": ["RQ-unrelated"],
                "consumer_steps": ["S9"],
                "risk": "low",
                "depth_rationale": "The low-risk operation is isolated from the selected step.",
            }
        )
    return {
        "questions": questions,
        "sources": sources(),
        "system_context": {
            "version": 1,
            "scope": "integrated",
            "rationale": "The selected client/service route changes the requested result.",
            "observations": [
                {
                    "id": "OBS-code",
                    "kind": "code",
                    "status": "observed",
                    "summary": "The current client wrapper owns request serialization.",
                    "source_refs": ["SRC-CODE"],
                    "role_refs": [],
                    "interface_refs": ["IF-client"],
                },
                {
                    "id": "OBS-state",
                    "kind": "state",
                    "status": "observed",
                    "summary": "The service records request identity for duplicate handling.",
                    "source_refs": ["SRC-CONTRACT"],
                    "role_refs": ["ROLE-dev"],
                    "interface_refs": ["IF-service"],
                },
                {
                    "id": "OBS-system",
                    "kind": "system",
                    "status": "observed",
                    "summary": "The client and service are separate selected boundary participants.",
                    "source_refs": ["SRC-PLATFORM"],
                    "role_refs": ["ROLE-dev"],
                    "interface_refs": ["IF-client", "IF-service"],
                },
                {
                    "id": "OBS-role",
                    "kind": "environment-role",
                    "status": "observed",
                    "summary": "The selected development role permits isolated contract validation.",
                    "source_refs": ["SRC-PLATFORM"],
                    "role_refs": ["ROLE-dev"],
                    "interface_refs": [],
                },
            ],
            "roles": [
                {
                    "id": "ROLE-dev",
                    "label": "isolated development delivery role",
                    "status": "observed",
                    "permitted_actions": "Run the documented non-production contract validation.",
                    "isolation": "The fixture has no production data or credential mutation.",
                    "platform_refs": ["delivery"],
                    "source_refs": ["SRC-PLATFORM"],
                    "revalidate": "Recheck before an external operation or promotion.",
                }
            ],
            "interfaces": [
                {
                    "id": "IF-client",
                    "kind": "client",
                    "identity": "selected client wrapper",
                    "survey_ref": {"platform_id": "delivery", "name": "client"},
                    "role_refs": ["ROLE-dev"],
                    "source_refs": ["SRC-PLATFORM", "SRC-CODE"],
                    "idiom": "Use the existing asynchronous wrapper rather than a new RPC layer.",
                    "status": "resolved",
                    "revalidate": "Recheck when the client wrapper or selected interface version changes.",
                },
                {
                    "id": "IF-service",
                    "kind": "service",
                    "identity": "selected service-visible endpoint",
                    "survey_ref": {"platform_id": "delivery", "name": "service"},
                    "role_refs": ["ROLE-dev"],
                    "source_refs": ["SRC-PLATFORM", "SRC-CONTRACT"],
                    "idiom": "Use the documented public operation and result/error envelope.",
                    "status": "resolved",
                    "revalidate": "Recheck when the service operation or version changes.",
                },
            ],
            "interactions": interactions,
        },
    }


class SystemContextTests(unittest.TestCase):
    def test_legacy_research_shape_and_marker_remain_unchanged(self) -> None:
        extended = evidence()
        legacy = {
            "questions": [
                {
                    key: value
                    for key, value in extended["questions"][0].items()
                    if key not in {"parents", "contract_refs", "role_refs", "interface_refs"}
                }
            ],
            "sources": extended["sources"],
        }
        self.assertEqual(research.validate_state(legacy), legacy)
        with self.assertRaisesRegex(research.ResearchError, "unexpected schema"):
            research.validate_state(extended)
        self.assertFalse(system_context.context_current({}))
        with self.assertRaisesRegex(system_context.SystemContextError, "must be 1"):
            system_context.context_current({"system_context_protocol_version": 2})

    def test_extended_research_binds_survey_identity_and_reciprocal_links(self) -> None:
        result = research.validate_state(
            evidence(), machine=machine(), system_context_enabled=True
        )
        self.assertEqual(result["system_context"]["interfaces"][0]["survey_ref"]["name"], "client")
        self.assertEqual(result["questions"][1]["parents"], ["RQ-contract"])
        self.assertEqual(result["questions"][1]["contract_refs"], ["IC-call"])

    def test_invalid_source_survey_reference_and_question_cycle_fail_closed(self) -> None:
        unknown_source = evidence()
        unknown_source["system_context"]["interactions"][0]["source_refs"] = ["SRC-missing"]
        with self.assertRaisesRegex(system_context.SystemContextError, "unknown ID"):
            system_context.validate_research_state(unknown_source, machine())

        invalid_survey_ref = evidence()
        invalid_survey_ref["system_context"]["interfaces"][0]["survey_ref"]["name"] = "missing"
        with self.assertRaisesRegex(system_context.SystemContextError, "frozen surveyed interface"):
            system_context.validate_research_state(invalid_survey_ref, machine())

        cycle = evidence()
        cycle["questions"][0]["parents"] = ["RQ-retry"]
        with self.assertRaisesRegex(system_context.SystemContextError, "acyclic"):
            system_context.validate_research_state(cycle, machine())

    def test_required_unresolved_boundary_is_exposed_without_faking_completion(self) -> None:
        blocked = evidence()
        blocked["questions"][1]["status"] = "blocked"
        blocked["questions"][1]["answer"] = "The retry owner needs an authorized current probe."
        blocked["system_context"]["interactions"][0]["status"] = "blocked"
        self.assertEqual(
            system_context.blocking_ids(blocked, machine()),
            ["interaction:IC-call", "question:RQ-retry"],
        )
        self.assertEqual(
            research.unresolved_ids(
                blocked, machine=machine(), system_context_enabled=True
            ),
            ["RQ-retry", "interaction:IC-call"],
        )

    def test_projection_selects_step_and_direct_consumers_without_full_inventory(self) -> None:
        state = evidence(unrelated=True)
        projection = system_context.project_context(
            state["system_context"], state, machine(), step_id="S1", consumer_ids=["S2"]
        )
        self.assertEqual([row["id"] for row in projection["interactions"]], ["IC-call"])
        self.assertEqual(
            [row["id"] for row in projection["questions"]],
            ["RQ-contract", "RQ-retry"],
        )
        self.assertEqual(projection["direct_consumer_ids"], ["S2"])
        self.assertEqual(projection["evidence_locator"], "research-evidence.md")

    def test_binding_reads_markdown_evidence_and_transition_preserves_identity(self) -> None:
        state = evidence()
        with tempfile.TemporaryDirectory(prefix="shiploop-system-context-") as temp:
            root = Path(temp)
            store.write_record(root / "research-evidence.md", state, title="Fixture evidence")
            binding = system_context.read_evidence_binding(
                root, {"system_context_protocol_version": 1}, machine()
            )
        self.assertEqual(binding["system_context_protocol_version"], 1)
        self.assertEqual(binding["interaction_ids"], ["IC-call"])
        self.assertRegex(binding["context_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            system_context.read_evidence_binding(Path("."), {}, machine()),
            {"legacy": True},
        )

        changed = evidence()
        changed["system_context"]["interactions"][0]["operation"] = "different operation"
        with self.assertRaisesRegex(system_context.SystemContextError, "cannot change operation"):
            system_context.validate_transition(state, changed, machine())

    def test_step_plan_identity_and_review_evidence_bind_selected_context(self) -> None:
        state = evidence(unrelated=True)
        projection = system_context.project_context(
            state["system_context"], state, machine(), step_id="S1", consumer_ids=["S2"]
        )
        digest = "a" * 64
        legacy_identity = {
            "step_sha256": digest,
            "dependency_sha256": digest,
            "enclosing_review_sha256": digest,
            "worktree": "/tmp/shiploop-system-context-fixture",
            "git_baseline": "b" * 40,
            "committed_tree_sha256": digest,
            "worktree_fingerprint": digest,
            "status_sha256": digest,
            "spec_sha256": digest,
            "environment_sha256": digest,
            "behavior_sha256": digest,
            "plan_sha256": digest,
            "knowledge_sha256": digest,
        }
        self.assertEqual(step_planning.validate_context(legacy_identity), legacy_identity)
        versioned_identity = {
            **legacy_identity,
            "research_candidate_sha256": digest,
            "research_certificate_sha256": digest,
            "research_evidence_sha256": digest,
            "system_context_sha256": projection["context_sha256"],
        }
        self.assertEqual(
            step_planning.validate_context(versioned_identity), versioned_identity
        )
        rows = {
            "role_ids": "roles",
            "interface_ids": "interfaces",
            "interaction_ids": "interactions",
            "question_ids": "questions",
            "observation_ids": "observations",
            "source_ids": "sources",
        }
        structured = {
            "context_sha256": projection["context_sha256"],
            **{
                field: [row["id"] for row in projection[projection_field]]
                for field, projection_field in rows.items()
            },
        }
        accepted = step_planning.check_context_evidence(
            {
                "step": "S1 selected from the frozen dependency plan.",
                "implementation": "The current fixture worktree was inspected.",
                "environment": "The local fixture role remains isolated.",
                "dependencies": "S2 is the direct consumer inspected for impact.",
                "system_context": structured,
            },
            system_context=projection,
        )
        self.assertEqual(accepted["system_context"], structured)
        structured["interaction_ids"] = ["IC-unrelated"]
        with self.assertRaisesRegex(step_planning.StepPlanningError, "every and only"):
            step_planning.check_context_evidence(
                {
                    "step": "S1 selected from the frozen dependency plan.",
                    "implementation": "The current fixture worktree was inspected.",
                    "environment": "The local fixture role remains isolated.",
                    "dependencies": "S2 is the direct consumer inspected for impact.",
                    "system_context": structured,
                },
                system_context=projection,
            )


if __name__ == "__main__":
    unittest.main()
