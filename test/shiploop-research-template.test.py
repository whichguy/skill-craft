#!/usr/bin/env python3
"""Research examples must match the selected validator, not imply readiness."""

from copy import deepcopy
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/shiploop/scripts"
sys.path.insert(0, str(SCRIPTS))

import shiploop_packets as packets  # noqa: E402
import shiploop_protocol as protocol  # noqa: E402
import shiploop_research as research  # noqa: E402
import shiploop_system_context as system_context  # noqa: E402


class ResearchTemplateTests(unittest.TestCase):
    def template(self, stage, *, current=True):
        state = {"system_context_protocol_version": 1} if current else {}
        return packets._planning_template(stage, state, protocol.__dict__)

    def assert_discovery_authoring_note(self, notes, *, machine=False):
        instruction = " ".join(notes)
        for detail in (
            "discovery coverage and reuse decisions",
            "setup-capability stages",
            "experiment fidelity/cleanup",
            "remaining exploration allowance",
        ):
            self.assertIn(detail, instruction)
        self.assertIn("do not add machine keys" if machine else "do not add research_state keys", instruction)

    def test_current_draft_and_apply_examples_validate_but_cannot_converge(self):
        for stage in ("research", "research-apply"):
            with self.subTest(stage=stage):
                template, notes = self.template(stage)
                value = template["research_state"]
                before = deepcopy(value)
                validated = research.validate_state(
                    value, machine={}, system_context_enabled=True
                )
                self.assertEqual(value, before)
                self.assertEqual(set(validated), {"questions", "sources", "system_context"})
                self.assertEqual(
                    {row["kind"] for row in validated["system_context"]["observations"]},
                    {"code", "state", "system", "environment-role"},
                )
                self.assertEqual(
                    research.unresolved_ids(value, machine={}, system_context_enabled=True),
                    ["RQ-1"],
                )
                self.assertIn("not evidence", " ".join(notes))
                self.assertIn("local-only", " ".join(notes))
                self.assertIn("integrated", " ".join(notes))
                self.assert_discovery_authoring_note(notes)

    def test_legacy_draft_and_apply_keep_exact_original_shape(self):
        for stage in ("research", "research-apply"):
            with self.subTest(stage=stage):
                template, notes = self.template(stage, current=False)
                value = template["research_state"]
                self.assertEqual(set(value), {"questions", "sources"})
                self.assertEqual(set(value["questions"][0]), {
                    "id", "question", "origin", "status", "answer", "sources",
                    "revalidate", "rationale",
                })
                research.validate_state(value)
                self.assertEqual(research.unresolved_ids(value), ["RQ-1"])
                self.assert_discovery_authoring_note(notes)

    def test_survey_template_keeps_discovery_detail_in_authored_body(self):
        template, notes = packets._execution_base_template("survey", {}, {})
        self.assertEqual(
            template,
            {
                "summary": "Environment survey drafted.",
                "body": "# Environment\n...\n\n## machine\n```json\n{}\n```",
            },
        )
        self.assert_discovery_authoring_note(notes, machine=True)

    def test_selected_discovery_policy_keeps_setup_authority_and_recovery_boundaries(self):
        text = (SCRIPTS.parent / "references/research-loop.md").read_text()
        section = text.split("## Recursive discovery and experiments\n", 1)[1].split("\n## ", 1)[0]
        normalized = " ".join(section.split())
        # Policy-presence checks complement, rather than claim, model compliance.
        for area in (
            "Message passing", "Client connections", "Service authentication", "Design",
            "Client-side libraries", "Storage", "Caching", "Security considerations",
        ):
            self.assertIn(f"| {area} |", section)
        for boundary in (
            "user's request or current task context authorizes discovery setup",
            "do not ask again for the same bounded setup",
            "An initial catalog is not a ceiling",
            "same authorized account/data scope and grant",
            "do not route around it",
            "acquisition never changes the frozen selected interface, writer, or inventory",
            "13 active minutes or 56 observable actions",
            "ShipLoop does not observe native host tools or kill them",
            "unaccepted draft",
            "accepted candidate remains unchanged",
            "Resuming does not replenish the exploration allowance",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, normalized)

    def test_unknown_version_does_not_silently_get_legacy_example(self):
        with self.assertRaises(system_context.SystemContextError):
            packets._planning_template(
                "research", {"system_context_protocol_version": 2}, protocol.__dict__
            )

    def test_schema_reference_is_selected_for_both_writers_and_anchors_exist(self):
        core = SimpleNamespace(REF_DIR=SCRIPTS.parent / "references")
        path = core.REF_DIR / "research-result-schema.md"
        for stage in ("research", "research-apply"):
            with self.subTest(stage=stage):
                lines = "\n".join(packets._guidance_lines(core, stage, protocol.__dict__))
                self.assertIn("research-result-schema.md#result-shape", lines)
                self.assertIn("#replacement-rules", lines)
        text = path.read_text()
        self.assertIn("## Result shape", text)
        self.assertIn("## Replacement rules", text)

    def test_documented_v1_example_and_mutable_refinement_obey_real_schema(self):
        text = (SCRIPTS.parent / "references/research-result-schema.md").read_text()
        examples = re.findall(r"```json\n(.*?)\n```", text, re.S)
        self.assertEqual(len(examples), 1)
        value = json.loads(examples[0])
        research.validate_state(value, machine={}, system_context_enabled=True)
        self.assertTrue(research.unresolved_ids(value, machine={}, system_context_enabled=True))
        refined = deepcopy(value)
        refined["system_context"]["interfaces"][0]["idiom"] = "An inspected wrapper detail; still blocked on authority."
        refined["system_context"]["interactions"][0]["input_output"] = "A refined envelope detail; not a live success claim."
        system_context.validate_transition(value, refined, {})
        self.assertTrue(system_context.meaningful_change(value, refined, {}))
        for table, key in (("interfaces", "identity"), ("interactions", "operation")):
            changed = deepcopy(value)
            changed["system_context"][table][0][key] = "Different identity"
            with self.subTest(key=key), self.assertRaises(system_context.SystemContextError):
                system_context.validate_transition(value, changed, {})
        broken = deepcopy(value)
        broken["questions"][0]["contract_refs"] = []
        with self.assertRaisesRegex(system_context.SystemContextError, "reciprocal"):
            system_context.validate_research_state(broken, {})


if __name__ == "__main__":
    unittest.main()
