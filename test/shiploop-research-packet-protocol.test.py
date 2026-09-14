#!/usr/bin/env python3
"""Public-CLI regression coverage for versioned research result packets.

The tests deliberately compose the established planning-loop fixture instead of
inheriting its test case: each case begins with real intake, approach, and
survey actions, then writes only the result file named by the packet's exact
completion callback.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import runpy
import shlex
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLANNING_TEST_MODULE = runpy.run_path(str(ROOT / "test" / "shiploop-planning.test.py"))
store = PLANNING_TEST_MODULE["store"]


class ResearchPacketProtocolTests(unittest.TestCase):
    """Exercise versioned research packets through the printed CLI callback."""

    QUESTION_FIELDS = {
        "id",
        "question",
        "origin",
        "status",
        "answer",
        "sources",
        "revalidate",
        "rationale",
        "parents",
        "contract_refs",
        "role_refs",
        "interface_refs",
    }
    CONTEXT_FIELDS = {
        "version",
        "scope",
        "rationale",
        "observations",
        "roles",
        "interfaces",
        "interactions",
    }
    ROLE_FIELDS = {
        "id",
        "label",
        "status",
        "permitted_actions",
        "isolation",
        "platform_refs",
        "source_refs",
        "revalidate",
    }
    OBSERVATION_FIELDS = {
        "id",
        "kind",
        "status",
        "summary",
        "source_refs",
        "role_refs",
        "interface_refs",
    }

    def setUp(self) -> None:
        planning_fixture = PLANNING_TEST_MODULE["PlanningLoopTests"]
        self.fixture = planning_fixture()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def _research_packet(self) -> str:
        packet = self.fixture.cli("next").stdout
        self.assertIn("Result template", packet)
        self.assertIn("Call this when done: ", packet)
        self.assertIn("research-result-schema.md#result-shape", packet)
        self.assertIn("#replacement-rules", packet)
        return packet

    def _template(self, packet: str) -> dict:
        result_section = packet.split("Result template", 1)[1]
        fence = "```shiploop-state"
        self.assertIn(fence, result_section)
        payload = result_section.split(fence, 1)[1].split("```", 1)[0].strip()
        return json.loads(payload)

    def _assert_versioned_research_template(self, packet: str, template: dict) -> None:
        """The versioned packet must expose a fillable shape, not legacy rows."""
        self.assertIn("examples, not evidence", packet)
        self.assertIn("local-only", packet)
        self.assertIn("integrated", packet)
        for detail in (
            "discovery coverage and reuse decisions",
            "setup-capability stages",
            "experiment fidelity/cleanup",
            "remaining exploration allowance",
            "do not add research_state keys",
        ):
            self.assertIn(detail, packet)
        self.assertEqual(set(template["research_state"]), {
            "questions",
            "sources",
            "system_context",
        })
        state = template["research_state"]
        self.assertEqual(len(state["questions"]), 1)
        self.assertEqual(set(state["questions"][0]), self.QUESTION_FIELDS)
        self.assertEqual(state["questions"][0]["status"], "open")

        context = state["system_context"]
        self.assertEqual(set(context), self.CONTEXT_FIELDS)
        self.assertEqual(context["scope"], "local-only")
        self.assertEqual(len(context["roles"]), 1)
        self.assertEqual(set(context["roles"][0]), self.ROLE_FIELDS)
        self.assertEqual(len(context["observations"]), 4)
        self.assertEqual(
            {row["kind"] for row in context["observations"]},
            {"code", "state", "system", "environment-role"},
        )
        for row in context["observations"]:
            self.assertEqual(set(row), self.OBSERVATION_FIELDS)
        self.assertEqual(context["interfaces"], [])
        self.assertEqual(context["interactions"], [])

    def _fixture_result(
        self,
        template: dict,
        *,
        revision: str,
        research_state: dict | None = None,
        for_apply: bool = False,
    ) -> dict:
        """Fill the packet's own result slots with source-backed local evidence."""
        payload = copy.deepcopy(template)
        state = copy.deepcopy(research_state or self.fixture.research_state(revision))
        self.assertEqual(set(payload["research_state"]), set(state))
        for key, value in state.items():
            payload["research_state"][key] = value
        payload.update(
            summary="The local fixture records source-backed, deterministic research evidence.",
            body=self.fixture.research_body(revision),
        )
        if for_apply:
            payload.update(
                material=False,
                resolutions=[
                    {
                        "id": "R-T-OPEN",
                        "evidence": "The complete retained evidence keeps the unresolved decision visible.",
                    }
                ],
                test_changes="The candidate check continues to assert the durable research evidence.",
                learnings="Unresolved research evidence remains a convergence blocker after an apply.",
            )
        return payload

    def _exact_callback(self, packet: str) -> tuple[list[str], Path]:
        line = next(
            row
            for row in packet.splitlines()
            if row.startswith("Call this when done: ")
        )
        callback = shlex.split(line.removeprefix("Call this when done: "))
        action = self.fixture.state()["action"]["id"]
        self.assertEqual(callback[callback.index("--action") + 1], action)
        result_path = Path(callback[callback.index("--result") + 1])
        self.assertEqual(
            result_path.resolve(),
            (self.fixture.run_dir / "inbox" / f"{action}.md").resolve(),
        )
        return callback, result_path

    def _submit_packet(
        self, packet: str, payload: dict, *, code: int = 0
    ) -> subprocess.CompletedProcess[str]:
        callback, result_path = self._exact_callback(packet)
        store.write_record(result_path, payload, title="Research packet protocol result")
        process = subprocess.run(
            callback,
            cwd=self.fixture.repo,
            capture_output=True,
            text=True,
            env=self.fixture.env,
        )
        self.assertEqual(process.returncode, code, process.stdout + process.stderr)
        return process

    def _bootstrap_research(self) -> tuple[str, dict]:
        self.fixture.bootstrap_to_research()
        state = self.fixture.state()
        self.assertEqual(state["system_context_protocol_version"], 1)
        packet = self._research_packet()
        template = self._template(packet)
        self._assert_versioned_research_template(packet, template)
        return packet, template

    def _blocked_owner_apply_route(self) -> tuple[str, dict, dict]:
        packet, template = self._bootstrap_research()
        blocked_owner_state = self.fixture.research_state(
            "owner-decision",
            status="blocked",
            answer="The owner must decide whether the local runtime probe may run.",
        )
        self._submit_packet(
            packet,
            self._fixture_result(
                template,
                revision="owner-blocked-initial",
                research_state=blocked_owner_state,
            ),
        )
        self.fixture.assert_cursor("validate-spec", "research-review")
        self.fixture.history()
        self.fixture.complete(
            {
                "summary": "The review keeps the missing owner decision visible as a trivial wording pass.",
                "findings": [
                    {
                        "id": "R-T-OPEN",
                        "severity": "trivial",
                        "summary": "Retain the blocked owner decision for the local runtime probe.",
                    }
                ],
                "coverage_review": self.fixture.coverage_review("research"),
                "test_review": "The candidate check asserts the complete durable local evidence.",
                "learnings": "A missing owner decision remains visible through the complete replacement.",
            },
            label="open-research-review",
        )
        self.fixture.assert_cursor("validate-spec", "research-plan")
        self.fixture.complete(
            {
                "summary": "The plan retains the blocked owner decision instead of faking completion.",
                "body": "# Research plan\n\nKeep RQ-001 blocked until its owner decision is recorded.\n",
                "addresses": ["R-T-OPEN"],
            },
            label="open-research-plan",
        )
        self.fixture.assert_cursor("validate-spec", "research-apply")
        apply_packet = self._research_packet()
        apply_template = self._template(apply_packet)
        self._assert_versioned_research_template(apply_packet, apply_template)
        return apply_packet, apply_template, blocked_owner_state

    def test_versioned_template_can_reach_behavior_after_two_trivial_passes(self) -> None:
        packet, template = self._bootstrap_research()
        self._submit_packet(packet, self._fixture_result(template, revision="initial"))
        self.fixture.assert_cursor("validate-spec", "research-review")

        self.fixture.run_iteration("research", "R-T-01", material=False)
        self.assertEqual(self.fixture.planning("research")["streak"], 1)
        self.fixture.run_iteration("research", "R-T-02", material=False)
        self.fixture.assert_cursor("validate-spec", "research-finalize")
        self.fixture.finalize("research")
        self.fixture.assert_cursor("validate-spec", "behavior")

    def test_scope_rejections_do_not_advance_and_corrected_packet_succeeds(self) -> None:
        packet, template = self._bootstrap_research()
        accepted = self._fixture_result(template, revision="corrected")
        state_path = self.fixture.run_dir / "state.md"
        before = state_path.read_bytes()
        for malformed in (
            ["local-only"],
            {"scope": "local-only"},
            None,
            "untrusted-scope",
        ):
            with self.subTest(value_type=type(malformed).__name__):
                rejected = copy.deepcopy(accepted)
                rejected["research_state"]["system_context"]["scope"] = malformed
                process = self._submit_packet(packet, rejected, code=2)
                diagnostic = process.stdout + process.stderr
                self.assertIn("system_context.scope", diagnostic)
                self.assertIn("expected a string enum value", diagnostic)
                self.assertIn("integrated", diagnostic)
                self.assertIn("local-only", diagnostic)
                self.assertNotIn("untrusted-scope", diagnostic)
                self.assertNotIn("Traceback", diagnostic)
                self.assertEqual(state_path.read_bytes(), before)
                self.fixture.assert_cursor("validate-spec", "research")
                self.assertFalse((self.fixture.run_dir / "research-evidence.md").exists())

        self._submit_packet(packet, accepted)
        self.fixture.assert_cursor("validate-spec", "research-review")
        self.assertTrue((self.fixture.run_dir / "research-evidence.md").is_file())

    def test_apply_packet_is_versioned_and_blocked_owner_decision_cannot_converge(self) -> None:
        packet, template, blocked_owner_state = self._blocked_owner_apply_route()
        payload = self._fixture_result(
            template,
            revision="owner-blocked-apply",
            research_state=blocked_owner_state,
            for_apply=True,
        )
        self._submit_packet(packet, payload)
        self.fixture.assert_cursor("validate-spec", "research-verify")

        self.fixture.finish_iteration(
            "research",
            "A missing owner decision remains visible through the complete replacement.",
            "Unresolved research evidence remains a convergence blocker after an apply.",
        )
        receipt = self.fixture.planning("research")
        self.assertEqual(receipt["streak"], 0)
        self.assertEqual(receipt["research_state"]["questions"][0]["status"], "blocked")
        self.fixture.assert_cursor("validate-spec", "research-review")

    def test_cataloged_probe_evidence_persists_without_claiming_service_access(self) -> None:
        packet, template = self._bootstrap_research()
        environment_path = self.fixture.run_dir / "environment.md"
        frozen_environment = environment_path.read_bytes()
        blocked_state = self.fixture.research_state(
            "cataloged-service-blocked",
            status="blocked",
            answer=(
                "The task-local MCP server was acquired and cataloged, but the "
                "required service operation remains blocked pending authorized access."
            ),
        )
        probe = blocked_state["sources"][0]
        probe.update(
            reference="fixture task-local MCP probe receipt",
            authority="probe",
            version_or_observed_at="fixture-mcp-catalog-1",
            supports=(
                "The task-local MCP server was acquired and cataloged; its "
                "required service operation remained blocked."
            ),
            limitations=(
                "Catalog evidence does not prove service access, deployment, "
                "or an authorized operation."
            ),
        )
        body = self.fixture.research_body("cataloged-service-blocked") + (
            "\n## Capability probe\n\nThe local reader was acquired and cataloged; "
            "the required service operation remains blocked.\n"
            "\n## Exploration allowance\n\nUsed 13 active minutes and 56 actions; "
            "remaining two minutes/eight actions are for recording and cleanup. "
            "Next gap: establish authorized target access.\n"
        )
        self._submit_packet(
            packet,
            self._fixture_result(
                template,
                revision="cataloged-service-blocked",
                research_state=blocked_state,
            ) | {"body": body},
        )
        initial = self.fixture.planning("research")["research_state"]
        self.assertEqual(initial["questions"][0]["status"], "blocked")
        self.assertEqual(initial["sources"][0]["authority"], "probe")
        self.assertIn("acquired and cataloged", initial["sources"][0]["supports"])
        self.assertIn("does not prove service access", initial["sources"][0]["limitations"])

        # A valid candidate is checkpointed before pausing the returned action.
        # Neither a temporary reader nor a pause may rewrite the frozen survey.
        retained = {
            name: (self.fixture.run_dir / name).read_bytes()
            for name in ("research.md", "research-evidence.md", "environment.md")
        }
        reason = "Exploration allowance reached; target access remains blocked. No automatic refill."
        self.fixture.cli("pause", "--run-dir", str(self.fixture.run_dir), "--reason", reason)
        self.assertEqual(self.fixture.state()["paused"], reason)
        self.assertIn(reason, self.fixture.cli("next").stdout)
        self.fixture.cli("resume", "--run-dir", str(self.fixture.run_dir))
        self.fixture.cli("next")
        for name, raw in retained.items():
            self.assertEqual((self.fixture.run_dir / name).read_bytes(), raw)
        self.assertEqual(environment_path.read_bytes(), frozen_environment)
        self.assertEqual(self.fixture.planning("research")["research_state"], initial)
        self.fixture.assert_cursor("validate-spec", "research-review")

        self.fixture.run_iteration(
            "research",
            "R-MCP-BLOCKED",
            material=False,
            candidate_body=body,
            research_state=blocked_state,
        )
        receipt = self.fixture.planning("research")
        self.assertEqual(receipt["research_state"]["questions"][0]["status"], "blocked")
        self.assertEqual(receipt["research_state"]["sources"][0]["authority"], "probe")
        self.assertEqual(receipt["streak"], 0)
        self.fixture.assert_cursor("validate-spec", "research-review")

    def test_unaccepted_inbox_draft_survives_pause_without_becoming_a_candidate(self) -> None:
        packet, _template = self._bootstrap_research()
        _callback, inbox = self._exact_callback(packet)
        action_id = self.fixture.state()["action"]["id"]
        before = {
            name: ((self.fixture.run_dir / name).read_bytes()
                   if (self.fixture.run_dir / name).exists() else None)
            for name in ("research.md", "research-evidence.md", "environment.md")
        }
        # Deliberately incomplete: no research_state. Pause must not parse/import it.
        draft = {
            "summary": "Unaccepted partial discovery draft; required work remains.",
            "body": "# Partial research\nUsed 56 actions; eight reserved. Target access is unresolved.\n",
        }
        store.write_record(inbox, draft, title="Unaccepted discovery draft")
        raw_draft = inbox.read_bytes()
        reason = f"Unaccepted draft: {inbox}; eight reserved actions remain. Next gap: target access."
        self.fixture.cli("pause", "--run-dir", str(self.fixture.run_dir), "--reason", reason)
        paused_packet = self.fixture.cli("next").stdout
        self.assertIn(str(inbox), paused_packet)
        self.assertIn("Unaccepted draft", paused_packet)
        self.fixture.cli("resume", "--run-dir", str(self.fixture.run_dir))
        resumed = self._research_packet()
        self.assertIn(action_id, resumed)
        self.assertEqual(inbox.read_bytes(), raw_draft)
        for name, raw in before.items():
            path = self.fixture.run_dir / name
            self.assertEqual(path.read_bytes() if path.exists() else None, raw)
        self.fixture.assert_cursor("validate-spec", "research")


if __name__ == "__main__":
    unittest.main()
