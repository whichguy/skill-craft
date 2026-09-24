#!/usr/bin/env python3
"""Pin the inline Improve / delegated improve-agent split."""
import json
import re
import unittest
from pathlib import Path

import package_build

ROOT = Path(__file__).resolve().parents[1]
# plugins/ is release output; package tests read a build of the current source.
PLUGINS = package_build.plugins()
AGENT = ROOT / "skills" / "improve-agent"
IMPROVE = ROOT / "skills" / "improve"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def flat(path: Path) -> str:
    """Collapse wrapping so phrase checks survive reflowed Markdown."""
    return " ".join(text(path).split())


def anchors(path: Path) -> set[str]:
    slugs = set()
    for line in text(path).splitlines():
        match = re.match(r"^#{1,6} (.+)$", line)
        if match:
            slug = re.sub(r"[^\w\- ]", "", match.group(1).lower()).replace(" ", "-")
            slugs.add(slug)
    return slugs


class ImproveAgentCardTests(unittest.TestCase):
    def test_frontmatter_names_a_prompt_only_leaf(self) -> None:
        front = text(AGENT / "SKILL.md").split("---", 2)[1]
        self.assertRegex(front, r"(?m)^name: improve-agent$")
        self.assertRegex(front, r"(?m)^version: \d+\.\d+\.\d+$")
        self.assertRegex(front, r"(?m)^\s+kind: prompt-only$")

    def test_links_and_anchors_resolve(self) -> None:
        for card in (AGENT / "SKILL.md", AGENT / "README.md", IMPROVE / "SKILL.md", IMPROVE / "README.md"):
            for target in re.findall(r"\]\(([^)\s]+)\)", text(card)):
                if re.match(r"^[a-z]+://", target):
                    continue
                file_part, _, fragment = target.partition("#")
                resolved = (card.parent / file_part) if file_part else card
                self.assertTrue(resolved.exists(), f"{card.name}: missing {target}")
                if fragment:
                    self.assertIn(fragment, anchors(resolved), f"{card.name}: missing anchor {target}")

    def test_assignment_runs_improve_inline_in_the_worker(self) -> None:
        card = flat(AGENT / "SKILL.md")
        self.assertIn("`Run /improve using <selected absolute improve SKILL.md>`, once.", card)
        self.assertIn("ask-agent/consumer-owned-workspace/v1", card)
        for marker in ("workspace_route: consumer-owned", "delivery_mode: in-place",
                       "execution_role: improve-executor", "delegation_owner: parent"):
            self.assertIn(marker, text(AGENT / "SKILL.md"))
        self.assertIn("never fall back to the helper-managed route or a second worktree", card)

    def test_worker_contract_keeps_one_writer_and_parent_ownership(self) -> None:
        card = flat(AGENT / "SKILL.md")
        for phrase in (
            "Be the only candidate writer.",
            "Do not dispatch Improve again, create another worktree, or start reviewer, test-runner or executor agents",
            "Collect any delegate before returning.",
            "Do not execute a parent callback, workspace return, merge,",
            "the parent alone appends to it",
            "scoped commit SHAs or the explicit no-commit or no-change reason",
            "a statement that no parent-owned step was executed",
            "each reported commit SHA exists in the candidate",
            "A worker's completion is not caller delivery.",
        ):
            self.assertIn(phrase, card)


class InlineImproveTests(unittest.TestCase):
    def test_improve_starts_no_agent_by_default(self) -> None:
        card = flat(IMPROVE / "SKILL.md")
        self.assertIn("start no reviewer, test-runner or executor agent", card)
        self.assertIn("`self-review (inline default)`", card)
        self.assertIn("A host's standing permission or preference to start agents does not select one here.", card)
        self.assertNotIn("Scoped independent reviewers and test workers remain available", card)

    def test_executor_contract_moved_to_improve_agent(self) -> None:
        card = text(IMPROVE / "SKILL.md")
        self.assertIn("## Agent-run invocation", card)
        # ShipLoop ask-agent packets still print this marker.
        self.assertIn("`execution_role: improve-executor`", card)
        self.assertNotIn("return the cumulative\n[completion summary]", card)
        self.assertNotIn("This executor assignment applies only", card)

    def test_policy_selects_independent_review_through_the_binding(self) -> None:
        policy = flat(IMPROVE / "references" / "review-policy.md")
        self.assertIn("only when the owner binding selects independent review", policy)
        self.assertNotIn("independent reviewer when available", policy)


class PluginViewTests(unittest.TestCase):
    def test_plugin_view_publishes_one_matching_skill(self) -> None:
        plugin = PLUGINS / "improve-agent"
        claude = json.loads(text(plugin / ".claude-plugin" / "plugin.json"))
        codex = json.loads(text(plugin / ".codex-plugin" / "plugin.json"))
        for field in ("name", "version", "description", "license"):
            self.assertEqual(codex[field], claude[field], field)
        cards = sorted(p.relative_to(plugin).as_posix() for p in plugin.rglob("SKILL.md"))
        self.assertEqual(cards, ["skills/improve-agent/SKILL.md"])
        self.assertEqual(text(plugin / "skills" / "improve-agent" / "SKILL.md"), text(AGENT / "SKILL.md"))


if __name__ == "__main__":
    unittest.main()
