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
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_discovery as discovery  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_navigator_prompts as navigator_prompts  # noqa: E402
import shiploop_navigator_v3_prompts as navigator_v3_prompts  # noqa: E402
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


class InteractionGuidanceTests(unittest.TestCase):
    """Focused contracts for the shared interaction-design guidance locator."""

    ANCHOR = "actors-channels-and-state-ownership"
    REQUIREMENTS_DEFINITION_ANCHOR = "requirements-definition"
    REQUIRED_CLASSIC_STAGES = frozenset(
        (
            "approach",
            "survey",
            "research",
            "research-review",
            "spec",
            "spec-review",
            "sequence",
            "step-plan",
            "step-plan-review",
            "step-plan-revise",
            "improve-plan",
            "quality",
            "handoff",
        )
    )
    REQUIRED_REQUIREMENTS_DEFINITION_STAGES = frozenset(
        (
            "approach",
            "survey",
            "research",
            "research-review",
            "spec",
            "spec-review",
            "step-plan",
            "test-refine",
            "test-author",
        )
    )

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="shiploop-interaction-guide-")
        self.root = Path(self.tmp.name)
        self.repo = self.root / "project"
        self.repo.mkdir()
        self.guide = (
            ROOT / "skills" / "shiploop" / "references" / "behavioral-requirements.md"
        ).resolve()
        self.locator = f"Interaction design guide: {self.guide}#{self.ANCHOR}"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def navigator_state(self, protocol_version: int) -> dict:
        kwargs = {"protocol_version": protocol_version}
        if protocol_version == 3:
            kwargs["improve_skill"] = ""
        return navigator.new_state(
            str(self.repo),
            "Assess the requested interaction boundary.",
            str(self.root / "bound-plan.md"),
            **kwargs,
        )

    def bind_synthetic_v3_child(self, state: dict) -> dict:
        """Use the established synthetic binding fixture without running Improve."""
        child = state["active_improve"]
        self.assertIsNotNone(child)
        child.update(
            {
                "version": 1,
                "contract_marker": (
                    "ShipLoop standalone Improve binding: " + child["binding_id"]
                ),
                "skill": {
                    "skill_card": str(
                        (self.repo / "selected-improve" / "SKILL.md").resolve()
                    ),
                    "runtime_card": str(
                        (self.repo / "until-loop" / "SKILL.md").resolve()
                    ),
                    "runtime_cli": str(
                        (
                            self.repo / "until-loop" / "scripts" / "until-loop"
                        ).resolve()
                    ),
                    "skill_version": "synthetic",
                    "runtime_version": "synthetic",
                },
            }
        )
        navigator.validate(state)
        return state

    def assert_cold_packet_keeps_locator_and_cursor(
        self, state: dict, *, label: str
    ) -> str:
        run_root = self.root / label
        run_root.mkdir()
        navigator.save(run_root, state)
        before_bytes = (run_root / "state.md").read_bytes()
        recovered = store.read_record(run_root / "state.md")
        before_state = deepcopy(recovered)
        before_action = dict(navigator.current_action(recovered))

        packet = navigator.render(None, run_root, recovered)

        self.assertIn(self.locator, packet)
        self.assertEqual(recovered, before_state)
        self.assertEqual(dict(navigator.current_action(recovered)), before_action)
        self.assertEqual((run_root / "state.md").read_bytes(), before_bytes)
        return packet

    def test_interaction_design_guide_has_canonical_heading(self) -> None:
        self.assertTrue(self.guide.is_absolute())
        self.assertTrue(self.guide.is_file())
        self.assertIn(
            "## Actors, channels, and state ownership",
            self.guide.read_text(encoding="utf-8"),
        )

    def test_cold_navigator_packets_keep_interaction_guide_without_cursor_mutation(
        self,
    ) -> None:
        for protocol_version in (1, 2, 3):
            with self.subTest(protocol_version=protocol_version, packet="producer"):
                self.assert_cold_packet_keeps_locator_and_cursor(
                    self.navigator_state(protocol_version),
                    label=f"producer-v{protocol_version}",
                )

        child_state = self.navigator_state(3)
        child_action = dict(navigator.current_action(child_state))
        waiting = navigator.apply(
            child_state,
            child_action["id"],
            {"outcome": "done", "summary": "Synthetic producer result."},
        )
        self.assertIsNotNone(waiting["active_improve"])
        self.assert_cold_packet_keeps_locator_and_cursor(
            waiting, label="pending-v3-improve-child"
        )

    def test_cold_bound_v3_child_keeps_interaction_guidance_without_running_improve(
        self,
    ) -> None:
        """A schema-valid synthetic child binding covers rendering, not execution."""
        state = self.navigator_state(3)
        action = dict(navigator.current_action(state))
        waiting = navigator.apply(
            state,
            action["id"],
            {"outcome": "done", "summary": "Synthetic producer result."},
        )
        packet = self.assert_cold_packet_keeps_locator_and_cursor(
            self.bind_synthetic_v3_child(waiting),
            label="bound-v3-improve-child",
        )

        self.assertIn(self.locator, packet)
        self.assertIn("Selected Improve skill:", packet)
        for term in (
            "actor interactions",
            "channels",
            "state ownership",
            "Carry those locators into the child contract",
        ):
            self.assertIn(term, packet)

    def test_prompt_catalogs_direct_relevant_work_to_interaction_design(self) -> None:
        shared_terms = (
            "interaction design guide",
            "discovery",
            "spec development",
            "global planning",
            "step planning",
            "actors",
            "channels",
            "state ownership",
        )
        for catalog in (navigator_prompts.COMMON, navigator_v3_prompts.COMMON):
            normalized = " ".join(catalog.split()).lower()
            for term in shared_terms:
                self.assertIn(term, normalized)

        for stage in ("discovery", "spec", "plan", "step-plan"):
            self.assertIn("Interaction design guide", navigator_prompts.PROMPTS[stage])
            self.assertIn("Interaction design guide", navigator_v3_prompts.prompt(stage))
            improve = navigator_v3_prompts.improve_prompt(stage)
            for term in ("actor interactions", "channels", "state ownership"):
                self.assertIn(term, improve)

    def test_interaction_guide_has_canonical_shared_and_ui_subsections(self) -> None:
        """The specialized guidance remains nested under the shared interaction anchor."""
        text = self.guide.read_text(encoding="utf-8")
        anchor = text.index("## Actors, channels, and state ownership")
        next_peer_heading = text.index("\n## Behavior model", anchor)
        headings = (
            "Incoming events, connections, and state agreement",
            "UI-specific planning",
            "Review, evidence, and reuse",
        )
        positions = []
        for heading in headings:
            with self.subTest(heading=heading):
                position = text.find("\n### " + heading + "\n", anchor)
                self.assertNotEqual(position, -1)
                self.assertLess(anchor, position)
                self.assertLess(position, next_peer_heading)
                positions.append(position)
        self.assertEqual(positions, sorted(positions))

    def test_v3_step_plan_and_improve_cue_shared_and_ui_interactions(self) -> None:
        """Routing cues name the applicable concerns without testing design quality."""
        producer = navigator_v3_prompts.prompt("step-plan").lower()
        improve = navigator_v3_prompts.improve_prompt("step-plan").lower()
        for prompt_name, prompt in (("producer", producer), ("improve", improve)):
            with self.subTest(prompt=prompt_name):
                for cue in (
                    "incoming/outgoing events",
                    "connection lifecycle",
                    "baseline/delta",
                    "ui-specific planning",
                ):
                    self.assertIn(cue, prompt)
        for cue in ("design guidance", "fallback", "evidence_refs"):
            with self.subTest(cue=cue):
                self.assertIn(cue, producer)

    def test_v3_planning_stages_keep_design_basis_records_stage_local(self) -> None:
        """Require record-routing cues, not an LLM judgment about their substance."""
        required_cues = (
            "Retain a compact Design basis paragraph or exact section links:",
            (
                "For UI, include component/interaction/skin premises, selected design "
                "guidance locator plus identity/version or digest (or named fallback),"
            ),
            "evidence_refs; keep these as ordinary notes, not new result fields.",
        )
        for stage in ("plan", "step-plan"):
            with self.subTest(stage=stage):
                prompt = " ".join(navigator_v3_prompts.prompt(stage).split())
                for cue in required_cues:
                    self.assertIn(cue, prompt)

        implementation_prompt = " ".join(
            navigator_v3_prompts.prompt("implement").split()
        )
        self.assertNotIn(required_cues[0], implementation_prompt)

    @staticmethod
    def _synthetic_improve_record(stage: str) -> dict:
        """A state-machine fixture only; it makes no review-quality claim."""
        return {
            "summary": f"Synthetic Improve completion for {stage}; no runtime executed.",
            "review_refs": [],
            "check_refs": [],
            "lessons": f"Synthetic routing fixture for {stage}.",
        }

    def _finish_synthetic_v3_step(self, state: dict, **extra: object) -> dict:
        """Advance one v3 producer through the pure, explicitly synthetic return."""
        stage = navigator.current_stage(state)
        action = dict(navigator.current_action(state))
        waiting = navigator.apply(
            state,
            action["id"],
            {
                "outcome": "done",
                "summary": f"Synthetic producer result for {stage}.",
                **extra,
            },
        )
        return navigator.finish_improve(
            waiting, action["id"], self._synthetic_improve_record(stage)
        )

    def _v3_step_plan_state(self, work_item: dict[str, str]) -> dict:
        """Reach a real v3 step-plan cursor through its regular producer returns."""
        state = self.navigator_state(3)
        for stage in ("intake", "discovery", "research", "spec", "test-strategy"):
            self.assertEqual(navigator.current_stage(state), stage)
            state = self._finish_synthetic_v3_step(state)

        self.assertEqual(navigator.current_stage(state), "plan")
        state = self._finish_synthetic_v3_step(state, work_items=[work_item])
        for stage in ("prepare", "select-work"):
            self.assertEqual(navigator.current_stage(state), stage)
            state = self._finish_synthetic_v3_step(state)

        self.assertEqual(navigator.current_stage(state), "step-plan")
        return state

    def test_cold_v3_step_plan_and_improve_preserve_ui_and_headless_context(
        self,
    ) -> None:
        """Synthetic receipt routing preserves locators and summaries, not their merit."""
        cases = (
            {
                "id": "UI1",
                "title": "Surface export completion in the existing interface",
                "source": "docs/ui-notifications.md#export-complete",
                "decision": (
                    "UI decision summary: reuse the existing notification component; "
                    "respect reduced motion and show recovered completion once."
                ),
                "design_basis": (
                    "Design guidance: skills/frontend-design/SKILL.md; "
                    "version fixture-v1; digest sha256:0123456789abcdef."
                ),
            },
            {
                "id": "EV1",
                "title": "Accept report-complete events without a user surface",
                "source": "docs/events.md#report-complete",
                "decision": (
                    "Headless decision summary: deduplicate event IDs, retain accepted "
                    "state, and recover the subscription cursor after reconnect."
                ),
            },
        )
        for case in cases:
            with self.subTest(work_item=case["id"]):
                work_item = {
                    "id": case["id"],
                    "title": case["title"],
                    "context": "\n".join(
                        value
                        for value in (
                            case["source"],
                            case["decision"],
                            case.get("design_basis"),
                        )
                        if value
                    ),
                }
                state = self._v3_step_plan_state(work_item)
                run_root = self.root / ("cold-" + case["id"])
                run_root.mkdir()

                navigator.save(run_root, state)
                producer_bytes = (run_root / "state.md").read_bytes()
                recovered = store.read_record(run_root / "state.md")
                self.assertEqual(recovered, state)
                producer_packet = navigator.render(None, run_root, recovered)
                self.assertEqual((run_root / "state.md").read_bytes(), producer_bytes)

                action = dict(navigator.current_action(recovered))
                waiting = navigator.apply(
                    recovered,
                    action["id"],
                    {
                        "outcome": "done",
                        "summary": "Synthetic step-plan decision: " + case["decision"],
                        "evidence_refs": [case["source"]],
                    },
                )
                navigator.save(run_root, waiting)
                pending_bytes = (run_root / "state.md").read_bytes()
                pending = store.read_record(run_root / "state.md")
                pending_packet = navigator.render(None, run_root, pending)
                self.assertEqual((run_root / "state.md").read_bytes(), pending_bytes)

                bound = self.bind_synthetic_v3_child(pending)
                navigator.save(run_root, bound)
                bound_bytes = (run_root / "state.md").read_bytes()
                recovered_bound = store.read_record(run_root / "state.md")
                bound_packet = navigator.render(None, run_root, recovered_bound)
                self.assertEqual((run_root / "state.md").read_bytes(), bound_bytes)

                self.assertEqual(navigator.current_stage(recovered_bound), "step-plan")
                self.assertEqual(
                    recovered_bound["active_improve"]["action_id"], action["id"]
                )
                for packet in (producer_packet, pending_packet, bound_packet):
                    self.assertIn(self.locator, packet)
                    self.assertIn(case["source"], packet)
                    self.assertIn(case["decision"], packet)
                    if case.get("design_basis"):
                        self.assertIn(case["design_basis"], packet)
                self.assertIn("Parent step remains pending", pending_packet)
                self.assertIn("Load the actual Improve skill selected by this host.", pending_packet)
                self.assertIn("Selected Improve skill:", bound_packet)
                self.assertIn("Invoke the selected actual Improve skill for", bound_packet)

    @staticmethod
    def _resolve_behavior_guide(guidance: list[str], behavior_line: str) -> Path:
        """Resolve a packet locator whether its directory was factored out or not."""
        rendered_path = behavior_line.split("read only ", 1)[1].split("#", 1)[0]
        if Path(rendered_path).is_absolute():
            return Path(rendered_path)
        directory_line = next(
            line for line in guidance if line.startswith("Guidance directory: ")
        )
        directory = directory_line.removeprefix("Guidance directory: ")
        return Path(directory) / rendered_path

    def test_classic_protocol_routes_interaction_guidance_for_required_stages(self) -> None:
        self.assertTrue(self.REQUIRED_CLASSIC_STAGES <= set(protocol.BEHAVIOR_SECTIONS))
        core = SimpleNamespace(REF_DIR=self.guide.parent)
        api = {"BEHAVIOR_SECTIONS": protocol.BEHAVIOR_SECTIONS}
        for stage in sorted(self.REQUIRED_CLASSIC_STAGES):
            with self.subTest(stage=stage):
                self.assertIn(self.ANCHOR, protocol.BEHAVIOR_SECTIONS[stage])
                guidance = packets._guidance_lines(core, stage, api)
                behavior_line = next(
                    line
                    for line in guidance
                    if line.startswith("Behavior-model guidance: read only ")
                )
                self.assertIn("#" + self.ANCHOR, behavior_line)
                self.assertEqual(
                    self._resolve_behavior_guide(guidance, behavior_line), self.guide
                )

    def test_classic_protocol_routes_requirements_definition_for_required_stages(
        self,
    ) -> None:
        """Legacy packets retain the anchored guide at existing spec-related nodes."""
        self.assertTrue(
            self.REQUIRED_REQUIREMENTS_DEFINITION_STAGES
            <= set(protocol.BEHAVIOR_SECTIONS)
        )
        self.assertIn(
            "## Requirements definition", self.guide.read_text(encoding="utf-8")
        )
        core = SimpleNamespace(REF_DIR=self.guide.parent)
        api = {"BEHAVIOR_SECTIONS": protocol.BEHAVIOR_SECTIONS}
        for stage in sorted(self.REQUIRED_REQUIREMENTS_DEFINITION_STAGES):
            with self.subTest(stage=stage):
                self.assertIn(
                    self.REQUIREMENTS_DEFINITION_ANCHOR,
                    protocol.BEHAVIOR_SECTIONS[stage],
                )
                guidance = packets._guidance_lines(core, stage, api)
                behavior_line = next(
                    line
                    for line in guidance
                    if line.startswith("Behavior-model guidance: read only ")
                )
                self.assertIn(
                    "#" + self.REQUIREMENTS_DEFINITION_ANCHOR, behavior_line
                )
                self.assertEqual(
                    self._resolve_behavior_guide(guidance, behavior_line), self.guide
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
