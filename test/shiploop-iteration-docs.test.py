#!/usr/bin/env python3
"""Focused validation tests for ShipLoop's pre-check documentation stage."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))

import shiploop_iteration_docs as docs  # noqa: E402


class IterationDocumentationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="shiploop-iteration-docs-")
        self.repo = Path(self.tmp.name)
        (self.repo / "README.md").write_text("# Fixture\n\n- local-tools/fixture-skill/SKILL.md\n", encoding="utf-8")
        skill = self.repo / "local-tools" / "fixture-skill"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: fixture-skill\ndescription: Fixture workflow\n---\n# Fixture skill\n", encoding="utf-8")
        (skill / "references.md").write_text("# Reference\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_entrypoint(self, frontmatter: str, body: str = "# Fixture skill\n") -> None:
        (self.repo / "local-tools" / "fixture-skill" / "SKILL.md").write_text(
            frontmatter + "\n" + body,
            encoding="utf-8",
        )

    def payload(self, *, decision: str = "not-needed") -> dict:
        skill = {
            "decision": decision,
            "rationale": "The local fixture skill captures a repeated repository workflow." if decision != "not-needed" else "No reusable workflow exists beyond this selected step.",
            "paths": ["local-tools/fixture-skill/SKILL.md"] if decision != "not-needed" else [],
            "references": ["README.md", "local-tools/fixture-skill/references.md"] if decision != "not-needed" else [],
        }
        if decision != "not-needed":
            skill.update({
                "purpose": "Run the reusable fixture workflow.",
                "when": "When a later step needs the same fixture workflow.",
                "how": "Read the entrypoint and pass the selected repository path.",
                "inputs": "Repository-relative target path.",
                "validation": "The entrypoint and reference are regular local files.",
            })
        return {
            "summary": "The iteration documentation assessment is complete.",
            "documentation": {
                "decision": "updated",
                "rationale": "The README now records the observable fixture workflow.",
                "paths": ["README.md"],
                "references": ["README.md"],
            },
            "reusable_skill": skill,
            "material": False,
            "learnings": "The README and local skill entrypoint remain discoverable for later steps.",
        }

    def test_not_needed_is_explicit_and_has_no_paths(self) -> None:
        normalized = docs.validate_result(self.payload(), self.repo)
        self.assertEqual(normalized["documentation"]["decision"], "updated")
        self.assertEqual(normalized["reusable_skill"]["decision"], "not-needed")

    def test_created_or_reused_skill_needs_actual_entrypoint_and_reference(self) -> None:
        normalized = docs.validate_result(self.payload(decision="reused"), self.repo)
        self.assertEqual(normalized["reusable_skill"]["paths"], ["local-tools/fixture-skill/SKILL.md"])
        bad = self.payload(decision="reused")
        bad["reusable_skill"]["paths"] = []
        with self.assertRaisesRegex(docs.IterationDocumentationError, "actual local SKILL.md"):
            docs.validate_result(bad, self.repo)

    def test_path_escape_symlink_and_secret_are_rejected(self) -> None:
        escaped = self.payload()
        escaped["documentation"]["paths"] = ["../outside.md"]
        with self.assertRaisesRegex(docs.IterationDocumentationError, "repo-relative"):
            docs.validate_result(escaped, self.repo)
        secret = self.payload()
        secret["learnings"] = "token=real-secret-value"
        with self.assertRaisesRegex(docs.IterationDocumentationError, "credentials"):
            docs.validate_result(secret, self.repo)
        link = self.repo / "linked.md"
        link.symlink_to(self.repo / "README.md")
        symlinked = self.payload()
        symlinked["documentation"]["paths"] = ["linked.md"]
        with self.assertRaisesRegex(docs.IterationDocumentationError, "symlink"):
            docs.validate_result(symlinked, self.repo)
        for control in (".git", ".shiploop", ".worktrees"):
            with self.subTest(control_root=control):
                directory = self.repo / control
                directory.mkdir()
                (directory / "record.md").write_text("# Control fixture\n", encoding="utf-8")
                controlled = self.payload()
                controlled["documentation"]["paths"] = [f"{control}/record.md"]
                with self.assertRaisesRegex(docs.IterationDocumentationError, "control files"):
                    docs.validate_result(controlled, self.repo)
        (self.repo / "linked-tools").symlink_to(self.repo / "local-tools", target_is_directory=True)
        ancestor_link = self.payload()
        ancestor_link["documentation"]["paths"] = ["linked-tools/fixture-skill/references.md"]
        with self.assertRaisesRegex(docs.IterationDocumentationError, "symlink"):
            docs.validate_result(ancestor_link, self.repo)

    def test_skill_frontmatter_and_exposure_index_are_required(self) -> None:
        payload = self.payload(decision="created")
        entry = self.repo / "local-tools" / "fixture-skill" / "SKILL.md"
        entry.write_text("---\nname: []\ndescription: {}\n---\n# Empty\n", encoding="utf-8")
        with self.assertRaisesRegex(docs.IterationDocumentationError, "meaningful name"):
            docs.validate_result(payload, self.repo)
        entry.write_text("---\nname: fixture-skill\ndescription: Fixture workflow\n---\n# Fixture\n", encoding="utf-8")
        (self.repo / "README.md").write_text("# Fixture\n", encoding="utf-8")
        with self.assertRaisesRegex(docs.IterationDocumentationError, "exposed local index"):
            docs.validate_result(payload, self.repo)
        entry.write_bytes(b"---\nname: fixture-skill\ndescription: \xff\n---\n# Fixture\n")
        with self.assertRaisesRegex(docs.IterationDocumentationError, "UTF-8"):
            docs.validate_result(payload, self.repo)

    def test_frontmatter_requires_top_level_meaningful_values_and_nonempty_body(self) -> None:
        payload = self.payload(decision="created")
        cases = (
            (
                "quoted-empty-name",
                "---\nname: \" \"\ndescription: Fixture workflow\n---",
                "# Fixture skill\n",
                "meaningful name",
            ),
            (
                "collection-name",
                "---\nname: [fixture-skill]\ndescription: Fixture workflow\n---",
                "# Fixture skill\n",
                "meaningful name",
            ),
            (
                "nested-name",
                "---\nmetadata:\n  name: fixture-skill\ndescription: Fixture workflow\n---",
                "# Fixture skill\n",
                "meaningful name",
            ),
            (
                "quoted-empty-description",
                "---\nname: fixture-skill\ndescription: ''\n---",
                "# Fixture skill\n",
                "meaningful description",
            ),
            (
                "collection-description",
                "---\nname: fixture-skill\ndescription: {}\n---",
                "# Fixture skill\n",
                "meaningful description",
            ),
            (
                "nested-description",
                "---\nname: fixture-skill\ndescription:\n  value: Fixture workflow\n---",
                "# Fixture skill\n",
                "meaningful description",
            ),
            (
                "empty-block-description",
                "---\nname: fixture-skill\ndescription: |+\n---",
                "# Fixture skill\n",
                "meaningful description",
            ),
            (
                "empty-markdown-body",
                "---\nname: fixture-skill\ndescription: Fixture workflow\n---",
                "",
                "body must not be empty",
            ),
        )
        for label, frontmatter, body, message in cases:
            with self.subTest(case=label):
                self.write_entrypoint(frontmatter, body)
                with self.assertRaisesRegex(docs.IterationDocumentationError, message):
                    docs.validate_result(payload, self.repo)

        for indicator in ("|", ">", "|-", ">-", "|+", ">+"):
            with self.subTest(block_style=indicator):
                self.write_entrypoint(
                    "---\nname: fixture-skill\ndescription: "
                    + indicator
                    + "\n  Reusable fixture workflow.\n---",
                )
                normalized = docs.validate_result(payload, self.repo)
                self.assertEqual(normalized["reusable_skill"]["decision"], "created")

    def test_result_text_rejects_all_c0_and_c1_control_characters(self) -> None:
        for label, control in (
            ("c0-start", "\x01"),
            ("c0-delete", "\x1f"),
            ("c1-delete", "\x7f"),
            ("c1-next-line", "\x85"),
            ("c1-control", "\x9f"),
        ):
            with self.subTest(control=label):
                payload = self.payload()
                payload["learnings"] = "Recorded" + control + " learning."
                with self.assertRaisesRegex(docs.IterationDocumentationError, "C0/C1"):
                    docs.validate_result(payload, self.repo)

    def test_skill_assessment_is_bounded_and_selected_is_inspected(self) -> None:
        valid = docs.validate_skill_assessment({
            "inspected": ["local fixture skill"],
            "selected": ["local fixture skill"],
            "rationale": "The local fixture skill fits the recurring operation.",
            "usage": "Use its declared input and limits.",
        })
        self.assertEqual(valid["selected"], ["local fixture skill"])
        with self.assertRaisesRegex(docs.IterationDocumentationError, "subset"):
            docs.validate_skill_assessment({
                "inspected": [], "selected": ["missing"],
                "rationale": "Incorrect selection.", "usage": "Do not use it.",
            })


if __name__ == "__main__":
    unittest.main()
