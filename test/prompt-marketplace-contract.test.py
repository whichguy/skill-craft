#!/usr/bin/env python3
"""Static marketplace-portability contracts for prompt-only skills.

These checks deliberately inspect skill cards only.  They prove that packaged
instructions do not require this author's named agents, home directories, or
model catalog; they do not claim that a host completed a model evaluation.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
PROMPT_LEAVES = (
    "architect",
    "plan-test",
    "compare-prompts",
    "review-fix-bench",
    "improve-system-prompt",
    "c-plan",
    "prompt-align",
    "prompt-audit",
    "prompt-migrate",
    "prompt-refine",
)


def card(leaf: str) -> str:
    return (SKILLS / leaf / "SKILL.md").read_text(encoding="utf-8")


class PromptMarketplaceContractTests(unittest.TestCase):
    def test_owned_prompt_leaves_have_canonical_cards(self) -> None:
        for leaf in PROMPT_LEAVES:
            with self.subTest(leaf=leaf):
                body = card(leaf)
                self.assertIn(f"name: {leaf}", body)
                self.assertIn("kind: prompt-only", body)
                self.assertNotIn("allowed-tools:", body)

    def test_architect_and_plan_test_use_capabilities_not_author_agents(self) -> None:
        architect = card("architect")
        plan_test = card("plan-test")
        for body, forbidden in (
            (architect, "system-architect"),
            (architect, "AskUserQuestion"),
            (architect, "superpowers:"),
            (plan_test, "qa-analyst"),
            (plan_test, "npm test"),
        ):
            self.assertNotIn(forbidden, body)
        self.assertIn("available independent architecture reviewer", architect)
        self.assertIn("available independent test specialist", plan_test)
        self.assertRegex(
            plan_test,
            re.compile(r"detect\s+the\s+target\s+repository's\s+actual\s+test\s+command", re.I),
        )

    def test_benchmark_models_are_host_valid_and_trials_remain_independent(self) -> None:
        body = card("compare-prompts")
        self.assertNotRegex(body, re.compile(r"claude-[A-Za-z0-9_.-]+", re.I))
        self.assertIn("host-default model", body)
        self.assertIn("fresh independent session", body)

    def test_review_fix_bench_requires_explicit_external_runner_inputs(self) -> None:
        body = card("review-fix-bench")
        for forbidden in (
            "plugins/review-suite",
            "REVIEW_SUITE_AGENTS_DIR",
            "plugin.json#dependencies",
            "claude /plugin",
        ):
            self.assertNotIn(forbidden, body)
        for required in ("--target", "--runner", "--fixtures", "--judge", "separately installed"):
            self.assertIn(required, body)
        self.assertIn("No installed runner is bundled", body)
        self.assertIn("blocked prerequisite", body)
        self.assertIn("fresh\nindependent session", body)

    def test_improve_system_prompt_requires_explicit_product_configuration(self) -> None:
        body = card("improve-system-prompt")
        self.assertNotIn("1Y72rigcMUAwRd7bwl3CR57O6ENo5sKTn0xAl2C4HoZys75N5utGfkCUG", body)
        self.assertNotRegex(body, re.compile(r"^model:\s*", re.M))
        self.assertIn("--gas-project", body)
        self.assertIn("authorization preflight", body)
        self.assertIn("product-specific", body)
        self.assertIn("mcp__gas__exec", body)

    def test_prompt_suite_resolves_siblings_and_detects_target_tests(self) -> None:
        for leaf in ("c-plan", "prompt-align", "prompt-audit", "prompt-migrate", "prompt-refine"):
            with self.subTest(leaf=leaf):
                body = card(leaf)
                self.assertRegex(
                    body,
                    re.compile(r"target\s+repository's\s+actual\s+test\s+command"),
                )
                self.assertNotIn("<repo-root>/..", body)
        self.assertNotIn("In this repo:", card("c-plan"))
        for leaf in ("prompt-migrate", "prompt-refine"):
            self.assertRegex(
                card(leaf),
                re.compile(r"current[-\s]+host(?:'s)?\s+(?:skill\s+)?discovery", re.I),
            )
        for leaf in ("prompt-migrate", "prompt-refine"):
            body = card(leaf)
            self.assertNotIn("npm test", body)
            self.assertNotIn("git -C", body)
            self.assertRegex(
                body,
                re.compile(r"only\s+when\s+the\s+user\s+explicitly\s+requests\s+a\s+commit"),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
