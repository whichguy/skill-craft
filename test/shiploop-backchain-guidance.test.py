#!/usr/bin/env python3
"""Regression coverage for ShipLoop's native Backchain guidance routing."""

from __future__ import annotations

from pathlib import Path
import re
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
REF_DIR = SCRIPTS.parent / "references"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_packets as packets  # noqa: E402
import shiploop_objectives as objectives  # noqa: E402
import shiploop_protocol as protocol  # noqa: E402


EXPECTED = {
    "spec": ("owner-binding", "outcomes"),
    "spec-review": ("owner-binding", "outcomes"),
    "spec-plan": ("owner-binding", "outcomes"),
    "spec-apply": ("owner-binding", "outcomes"),
    "sequence": ("owner-binding", "outcomes", "sequence", "dependency-audit"),
    "step-plan": ("owner-binding", "step-plans", "dependency-audit"),
    "step-plan-review": ("owner-binding", "step-plans", "dependency-audit"),
    "step-plan-revise": ("owner-binding", "step-plans", "dependency-audit"),
    "improve-plan": ("owner-binding", "step-plans", "dependency-audit"),
    "implement": ("owner-binding", "step-plans"),
    "improve-apply": ("owner-binding", "step-plans"),
    "post-inner": ("owner-binding", "replanning", "dependency-audit"),
    "coverage": ("owner-binding", "replanning", "dependency-audit"),
    "quality": ("owner-binding", "replanning", "dependency-audit"),
}
DOCUMENT_SECTIONS = frozenset(
    (
        "owner-binding",
        "outcomes",
        "sequence",
        "dependency-audit",
        "step-plans",
        "replanning",
        "provenance",
    )
)
SPEC_STAGES = ("spec", "spec-review", "spec-plan", "spec-apply")
OBJECTIVE_BACKCHAIN = {
    kind: EXPECTED[kind]
    for kind in ("sequence", "post-inner", "coverage", "quality")
}


def heading_anchor(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\s+#+$", "", value)
    value = re.sub(r"[^\w\s-]", "", value)
    return re.sub(r"-+", "-", re.sub(r"\s+", "-", value)).strip("-")


class BackchainGuidanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.core = SimpleNamespace(
            VERSION="test",
            PACKAGE_ROOT=SCRIPTS.parent,
            REF_DIR=REF_DIR,
        )

    @staticmethod
    def backchain_lines(lines: list[str]) -> list[str]:
        return [
            line
            for line in lines
            if line.startswith("Backchain guidance: read only ")
        ]

    @staticmethod
    def anchors(line: str) -> tuple[str, ...]:
        return tuple(re.findall(r"#([a-z0-9-]+)", line))

    def assert_backchain_line(self, line: str, sections: tuple[str, ...]) -> None:
        rendered_path = line.split(" read only ", 1)[1].split("#", 1)[0]
        document = Path(rendered_path)
        if not document.is_absolute():
            document = REF_DIR / document
        self.assertTrue(document.is_file(), document)
        self.assertFalse(document.is_symlink(), document)
        self.assertEqual(document.resolve(), (REF_DIR / "backchain-planning.md").resolve())
        self.assertEqual(self.anchors(line), sections)

    def api(self, *, objective: bool = False, step_plan: bool = False) -> dict:
        return {
            "BACKCHAIN_SECTIONS": protocol.BACKCHAIN_SECTIONS,
            "planning": SimpleNamespace(is_current=lambda _state: True),
            "objectives": SimpleNamespace(
                is_objective_stage=lambda stage: objective
                and stage.startswith("objective-")
            ),
            "is_step_plan_stage": lambda stage: step_plan and stage == "step-plan",
            "repo_for": lambda _root, _state: ROOT,
        }

    def render(self, state: dict, api: dict, objective_info: dict) -> str:
        with (
            patch.object(packets, "_step_info", return_value=({}, None)),
            patch.object(packets, "_objective_info", return_value=(objective_info, None)),
            patch.object(packets, "_environment_projection", return_value=([], None)),
            patch.object(packets, "_platform_revalidation_packet", return_value=([], [], None)),
            patch.object(packets, "_action_orientation_lines", return_value=([], None)),
            patch.object(packets, "_check_commands", return_value=[]),
            patch.object(packets, "_planning_template", return_value=(None, [])),
            patch.object(
                packets,
                "_execution_template",
                return_value=({"candidate": "example"}, []),
            ),
            patch.object(packets, "_commit_packet_lines", return_value=([], None)),
        ):
            return packets.render(self.core, ROOT / ".shiploop-fixture", state, api)

    def test_mapping_and_document_anchors_are_exact_and_package_owned(self) -> None:
        self.assertEqual(protocol.BACKCHAIN_SECTIONS, EXPECTED)
        document = REF_DIR / "backchain-planning.md"
        self.assertTrue(document.is_file(), document)
        self.assertFalse(document.is_symlink(), document)
        document.resolve().relative_to(REF_DIR.resolve())
        anchors = {
            heading_anchor(match.group(2))
            for match in re.finditer(
                r"(?m)^(#{1,6})\s+(.+?)\s*$",
                document.read_text(encoding="utf-8"),
            )
        }
        self.assertTrue(DOCUMENT_SECTIONS <= anchors)
        self.assertTrue(
            {section for sections in EXPECTED.values() for section in sections}
            <= anchors
        )
        # Spec authors acceptance evidence before sequence creates any step
        # contracts.  This tests routing only, not whether prose proves plan
        # quality or invents future execution artifacts.
        for stage in SPEC_STAGES:
            with self.subTest(spec_stage=stage):
                self.assertEqual(
                    protocol.BACKCHAIN_SECTIONS[stage],
                    ("owner-binding", "outcomes"),
                )

    def test_guidance_maps_only_the_current_stage_or_named_objective_kind(self) -> None:
        api = self.api()
        for stage, sections in EXPECTED.items():
            with self.subTest(stage=stage):
                # Keep the pre-existing three-argument call valid for normal
                # stages while adding the optional objective selector.
                lines = packets._guidance_lines(self.core, stage, api)
                selected = self.backchain_lines(lines)
                self.assertEqual(len(selected), 1)
                self.assert_backchain_line(selected[0], sections)

        for kind in objectives.KINDS:
            expected = OBJECTIVE_BACKCHAIN.get(kind)
            for stage in objectives.STAGES:
                with self.subTest(objective_kind=kind, objective_stage=stage):
                    selected = self.backchain_lines(
                        packets._guidance_lines(
                            self.core, stage, api, objective_kind=kind
                        )
                    )
                    if expected is None:
                        self.assertEqual(selected, [])
                    else:
                        self.assertEqual(len(selected), 1)
                        self.assert_backchain_line(selected[0], expected)

        self.assertEqual(
            self.backchain_lines(
                packets._guidance_lines(self.core, "objective-review", api)
            ),
            [],
        )
        for stage, kind in (("research-review", None), ("objective-review", "research")):
            with self.subTest(stage=stage, objective_kind=kind):
                kwargs = {} if kind is None else {"objective_kind": kind}
                self.assertEqual(
                    self.backchain_lines(
                        packets._guidance_lines(self.core, stage, api, **kwargs)
                    ),
                    [],
                )

    def test_rendered_objective_kinds_and_nested_step_plan_keep_one_owner_callback(self) -> None:
        for kind in objectives.KINDS:
            base_stage = objectives.BASE_STAGES[kind]
            expected = OBJECTIVE_BACKCHAIN.get(kind)
            for stage in objectives.STAGES:
                with self.subTest(objective_kind=kind, objective_stage=stage):
                    objective_instruction = f"OBJECTIVE-{kind}-{stage}-ONLY"
                    base_instruction = f"BASE-{kind}-{base_stage}-MUST-NOT-APPEAR"
                    api = self.api(objective=True)
                    api["PROMPTS"] = {
                        stage: objective_instruction,
                        base_stage: base_instruction,
                    }
                    packet = self.render(
                        {
                            "phase": "validate-spec",
                            "stage": stage,
                            "revision": 1,
                            "action": {"id": f"{kind}-{stage}"},
                            "completed_actions": {},
                            "prompt": f"Render the bound {kind} objective.",
                            "history_policy": {"version": 2, "required_limit": 7},
                        },
                        api,
                        {
                            "objective_binding": {
                                "kind": kind,
                                "base_stage": base_stage,
                                "loop_id": f"{kind}-loop",
                            },
                            "objective_receipt": {"current_pass": {}},
                            "objective_open_ids": [],
                        },
                    )
                    self.assertIn(f"Stage: {stage}", packet)
                    self.assertIn(objective_instruction, packet)
                    self.assertNotIn(base_instruction, packet)
                    selected = self.backchain_lines(packet.splitlines())
                    if expected is None:
                        self.assertEqual(selected, [])
                    else:
                        self.assertEqual(len(selected), 1)
                        self.assert_backchain_line(selected[0], expected)
                    self.assertEqual(packet.count("Call this when done:"), 1)

        nested_state = {
            "phase": "implement",
            "stage": "step-plan",
            "revision": 1,
            "action": {"id": "nested-step-plan"},
            "completed_actions": {},
            "prompt": "Render the nested step plan.",
            "active_step": "S1",
            "history_policy": {"version": 2, "required_limit": 7},
        }
        nested_api = self.api(step_plan=True)
        nested_api["step_planning"] = SimpleNamespace(RUBRIC=())
        nested_packet = self.render(nested_state, nested_api, {})
        self.assertIn("Stage: step-plan", nested_packet)
        self.assertIn("Objective: draft the selected step plan", nested_packet)
        nested_guidance = self.backchain_lines(nested_packet.splitlines())
        self.assertEqual(len(nested_guidance), 1)
        self.assert_backchain_line(nested_guidance[0], EXPECTED["step-plan"])
        self.assertEqual(nested_packet.count("Call this when done:"), 1)

    def test_step_plan_body_remains_existing_markdown_body_not_a_result_schema(self) -> None:
        body = packets._STEP_PLAN_BODY
        self.assertIsInstance(body, str)
        self.assertNotIn("```shiploop-state", body)
        self.assertNotIn("Result format:", body)
        # These are structural content slots used by the current packet body;
        # they are not a claim that a phrase check establishes plan quality.
        for marker in (
            "## Execution microplan",
            "## Backward dependency check",
            "## Test criteria before code",
            "## Documentation and remaining risks",
            "Local ID",
            "Work + output",
            "Needs",
            "Source",
            "Evidence",
            "Case mapping",
        ):
            self.assertIn(marker, body)

        api = {"step_planning": SimpleNamespace(RUBRIC=())}
        expected_keys = {
            "step-plan": {"summary", "body", "skill_assessment"},
            "improve-plan": {"summary", "body", "skill_assessment"},
            "step-plan-revise": {
                "summary",
                "body",
                "addresses",
                "resolutions",
                "material",
                "test_changes",
                "learnings",
                "skill_assessment",
            },
        }
        for stage, keys in expected_keys.items():
            with self.subTest(stage=stage):
                template, _ = packets._step_plan_template(stage, {}, api, {})
                self.assertIsNotNone(template)
                assert template is not None
                self.assertEqual(set(template), keys)
                self.assertIs(template["body"], body)
                self.assertFalse(
                    {"backchain", "dependency_audit", "replanning"} & set(template)
                )


if __name__ == "__main__":
    unittest.main()
