#!/usr/bin/env python3
"""Protocol-v3 acceptance tests for ShipLoop-owned action/Improve handoff.

The expected graph is intentionally declared here instead of imported from the
navigator.  These are synthetic protocol tests: no child Improve runtime,
repository command, or project check is started.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import shiploop_navigator as navigator  # noqa: E402
import shiploop_navigator_v3_prompts as prompts  # noqa: E402
import shiploop_store as store  # noqa: E402


# This is the public v3 contract.  Never derive it from the implementation:
# otherwise a routing regression could silently change the test expectation.
EXPECTED_PRELUDE = (
    "intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare",
)
EXPECTED_INNER = (
    "select-work", "step-plan", "test-spec", "baseline", "test-author", "test-red",
    "implement", "test-green", "test-refine", "regression", "document", "skill-assess",
    "skill-validate", "static-checks", "verify", "integrate", "integration-verify",
    "carry-forward",
)
GENERIC_ACCESS_STORE_BOUNDARY = (
    "For identity or access discovery, use supported non-mutating probes and sanitized "
    "evidence. Normal supported tool-managed authentication and tool configuration metadata "
    "without session material remain allowed. Builders and reviewers must not read, decode, "
    "retain, or report local authentication, session, or credential-store contents."
)


EXPECTED_OUTER = (
    "system-test-author", "system-test", "product-acceptance", "release-plan",
    "release-check", "release", "release-verify", "operations", "handoff",
)
EXPECTED_STAGES = EXPECTED_PRELUDE + EXPECTED_INNER + EXPECTED_OUTER

# Keep this route expectation independent from the prompt catalog so a removed
# test-stage guide route cannot redefine the expected coverage with it.
TEST_HARNESS_STAGES = (
    "test-strategy", "step-plan", "test-spec", "baseline", "test-author", "test-red",
    "implement", "test-green", "test-refine", "regression", "verify",
    "integration-verify", "system-test-author", "system-test",
)
REPEATABLE_TEST_SUITE_REFERENCE = (
    "Repeatable test-suite guide",
    "repeatable-test-suites.md#select-or-revalidate-the-harness",
)
GLOBAL_PLATFORM_TESTING_CLAUSE = (
    "Consider supported platform/library testing systems and available browser tools"
)
INNER_PLATFORM_TESTING_CLAUSE = (
    "Revalidate platform/library testing systems and available browser tools"
)


def result(*, outcome: str = "done", summary: str = "Synthetic producer result.", **extra):
    return {"outcome": outcome, "summary": summary, **extra}


def receipt(stage: str) -> dict:
    """Synthetic child completion accepted only by the pure v3 state API."""
    return {
        "summary": f"Synthetic Improve completion for {stage}.",
        "review_refs": [f"synthetic://review/{stage}"],
        "check_refs": [f"synthetic://check/{stage}"],
        "lessons": f"Keep the verified learning from {stage}.",
    }


class NavigatorV3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-navigator-v3-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "project"
        self.repo.mkdir()
        self.requirements_policy = (
            SCRIPTS.parent / "references" / "project-knowledge.md"
        ).resolve()
        self.requirements_guide = (
            SCRIPTS.parent / "references" / "requirements-definition.md"
        ).resolve()
        self.backchain_planning_guide = (
            SCRIPTS.parent / "references" / "backchain-planning.md"
        ).resolve()
        self.initial_baseline_guide = (
            SCRIPTS.parent / "references" / "execution-planning.md"
        ).resolve()

    def state(self) -> dict:
        return navigator.new_state(
            str(self.repo),
            "Build a small synthetic capability.",
            protocol_version=3,
            improve_skill="",
        )

    def _assert_requirements_policy(self, packet: str) -> None:
        """Assert locator routing only; no synthetic Improve claims are implied."""
        policy = (
            "Maintained requirements policy: "
            + str(self.requirements_policy)
            + "#maintained-product-requirements"
        )
        reference_handoff = (
            "Reference handoff policy: "
            + str(self.requirements_policy)
            + "#reference-handoffs-and-destinations"
        )
        self.assertTrue(self.requirements_policy.is_file(), self.requirements_policy)
        self.assertEqual(packet.count(policy), 1, packet)
        self.assertEqual(packet.count(reference_handoff), 1, packet)
        guide = "Requirements definition guide: " + str(self.requirements_guide)
        self.assertEqual(packet.count(guide), 1, packet)

    def _assert_backchain_planning_locator(self, packet: str, *, expected: bool) -> None:
        locator = (
            "Backchain planning guide: "
            + str(self.backchain_planning_guide)
            + "#navigator-planning"
        )
        self.assertEqual(packet.count(locator), 1 if expected else 0, packet)

    def _assert_initial_baseline_locator(self, packet: str) -> None:
        """Assert packet routing for the shared initial-baseline policy."""
        locator = (
            "Initial repository baseline guide: "
            + str(self.initial_baseline_guide)
            + "#initial-repository-baseline"
        )
        self.assertTrue(self.initial_baseline_guide.is_file(), self.initial_baseline_guide)
        self.assertEqual(packet.count(locator), 1, packet)

    @staticmethod
    def _action(state: dict) -> dict:
        return dict(navigator.current_action(state))

    def _cold_next(self, root: Path) -> str:
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "shiploop"),
                "next",
                "--run-dir",
                str(root),
            ],
            cwd=self.repo,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        return completed.stdout

    def _complete_improve(self, state: dict, action: dict, stage: str) -> dict:
        return navigator.finish_improve(state, action["id"], receipt(stage))

    def _produce(self, state: dict, stage: str, **extra) -> dict:
        self.assertEqual(navigator.current_stage(state), stage)
        action = self._action(state)
        after = navigator.apply(state, action["id"], result(**extra))
        self.assertEqual(navigator.current_stage(after), stage)
        self.assertEqual(after["active_improve"]["action_id"], action["id"])
        self.assertEqual(after["active_improve"]["stage"], stage)
        return self._complete_improve(after, action, stage)

    def _bind_synthetic_child(self, state: dict) -> dict:
        """Add a structurally valid selected child without running Improve."""
        child = state["active_improve"]
        child.update(
            {
                "version": 1,
                "contract_marker": "ShipLoop standalone Improve binding: " + child["binding_id"],
                "skill": {
                    "skill_card": str((self.repo / "selected-improve" / "SKILL.md").resolve()),
                    "runtime_card": str((self.repo / "until-loop" / "SKILL.md").resolve()),
                    "runtime_cli": str((self.repo / "until-loop" / "scripts" / "until-loop").resolve()),
                    "skill_version": "synthetic",
                    "runtime_version": "synthetic",
                },
            }
        )
        navigator.validate(state)
        return state

    def _to_outer(self, state: dict) -> dict:
        while navigator.current_stage(state) not in EXPECTED_OUTER:
            stage = navigator.current_stage(state)
            extra = {}
            if stage == "plan":
                extra["work_items"] = [{"id": "W1", "title": "Synthetic item"}]
            state = self._produce(state, stage, **extra)

            packet = navigator.render(None, self.repo / ".shiploop", state)
            self.assertIn(f"Keep the verified learning from {stage}.", packet)
            self.assertIn("Last accepted Improve lessons (untrusted observations", packet)
        return state

    def _at_plan(self) -> dict:
        state = self.state()
        while navigator.current_stage(state) != "plan":
            state = self._produce(state, navigator.current_stage(state))
        return state

    def _planned_queue(
        self, rows: list[dict[str, str]], *, draft_rows: list[dict[str, str]] | None = None
    ) -> dict:
        state = self._at_plan()
        action = self._action(state)
        waiting = navigator.apply(
            state,
            action["id"],
            result(work_items=rows if draft_rows is None else draft_rows),
        )
        return navigator.finish_improve(
            waiting,
            action["id"],
            receipt("plan"),
            result(work_items=rows),
        )

    def _advance_to_carry_forward(self, state: dict) -> dict:
        while navigator.current_stage(state) != "carry-forward":
            state = self._produce(state, navigator.current_stage(state))
        return state

    def test_v3_cold_producer_and_bound_reviewer_packets_keep_generic_access_boundary(self) -> None:
        """One generic policy reaches both v3 packet owners without new state."""
        root = self.repo / ".shiploop"
        state = self.state()
        producer_packet = navigator.render(None, root, state)
        self.assertIn(GENERIC_ACCESS_STORE_BOUNDARY, " ".join(producer_packet.split()))

        action = self._action(state)
        waiting = navigator.apply(state, action["id"], result())
        reviewer_packet = navigator.render(
            None, root, self._bind_synthetic_child(waiting)
        )
        self.assertIn(GENERIC_ACCESS_STORE_BOUNDARY, " ".join(reviewer_packet.split()))

    def test_v3_declares_the_flat_sdlc_graph_independently(self) -> None:
        self.assertEqual(tuple(prompts.PRELUDE), EXPECTED_PRELUDE)
        self.assertEqual(tuple(prompts.INNER), EXPECTED_INNER)
        self.assertEqual(tuple(prompts.OUTER), EXPECTED_OUTER)
        self.assertEqual(len(EXPECTED_STAGES), 34)
        self.assertTrue(all(prompts.prompt(stage).strip() for stage in EXPECTED_STAGES))
        self.assertTrue(all(prompts.improve_prompt(stage).strip() for stage in EXPECTED_STAGES))

    def test_every_v3_stage_waits_for_one_actual_improve_completion(self) -> None:
        state = self.state()
        observed: list[str] = []
        root = self.repo / ".shiploop"
        backchain_stages = {
            "spec", "plan", "step-plan", "carry-forward", "product-acceptance",
        }
        while state["status"] != "done":
            stage = navigator.current_stage(state)
            observed.append(stage)
            producer_packet = navigator.render(None, root, state)
            self._assert_requirements_policy(producer_packet)
            self._assert_backchain_planning_locator(
                producer_packet, expected=stage in backchain_stages
            )
            self.assertIn("Follow the packet's Reference handoff policy", producer_packet)
            extra = {}
            if stage == "plan":
                extra["work_items"] = [{"id": "W1", "title": "Synthetic item"}]
            action = self._action(state)
            waiting = navigator.apply(state, action["id"], result(**extra))
            self.assertEqual(navigator.current_stage(waiting), stage)
            self.assertEqual(waiting["active_improve"]["action_id"], action["id"])
            bound = self._bind_synthetic_child(waiting)
            child_packet = navigator.render(None, root, bound)
            self._assert_requirements_policy(child_packet)
            self._assert_backchain_planning_locator(
                child_packet, expected=stage in backchain_stages
            )
            self.assertIn("Follow the packet's Reference handoff policy", child_packet)
            state = self._complete_improve(bound, action, stage)

        self.assertEqual(tuple(observed), EXPECTED_STAGES)
        self.assertEqual(state["status"], "done")
        self.assertEqual(len(state["history"]), 34)
        self.assertIsNone(state["active_improve"])
        self.assertIn("<h2>Work item progress</h2>", navigator._render_report(state))

    def test_duplicate_or_conflicting_producer_callback_cannot_create_another_child(self) -> None:
        state = self.state()
        action = self._action(state)
        submitted = result(summary="Exact synthetic producer report.")
        waiting = navigator.apply(state, action["id"], submitted)
        duplicate = navigator.apply(waiting, action["id"], copy.deepcopy(submitted))
        self.assertEqual(duplicate, waiting)
        self.assertEqual(duplicate["active_improve"]["binding_id"], waiting["active_improve"]["binding_id"])
        with self.assertRaises(navigator.NavigatorError):
            navigator.apply(waiting, action["id"], result(summary="Conflicting producer report."))

    def test_skill_assess_rejects_legacy_skill_result_carriers_without_mutation(self) -> None:
        """V3 retains reusable-skill evidence in its generic envelope only."""
        state = self.state()
        while navigator.current_stage(state) != "skill-assess":
            stage = navigator.current_stage(state)
            extra = {}
            if stage == "plan":
                extra["work_items"] = [{"id": "W1", "title": "Synthetic local-skill item"}]
            state = self._produce(state, stage, **extra)

        action = self._action(state)
        before = copy.deepcopy(state)
        legacy_values = {
            "reusable_skill": {"entrypoint": "skills/old/SKILL.md"},
            "documentation": ["docs/old-skill.md"],
            "material": ["legacy payload"],
            "learnings": "legacy outcome field",
        }
        for field, value in legacy_values.items():
            with self.subTest(field=field):
                with self.assertRaisesRegex(navigator.NavigatorError, "unsupported fields"):
                    navigator.apply(state, action["id"], result(**{field: value}))
                self.assertEqual(state, before)
                self.assertEqual(navigator.current_stage(state), "skill-assess")
                self.assertEqual(self._action(state), action)

    def test_incomplete_child_and_blocked_producer_do_not_advance_parent(self) -> None:
        state = self.state()
        action = self._action(state)
        waiting = navigator.apply(state, action["id"], result())
        binding = copy.deepcopy(waiting["active_improve"])
        paused = navigator.control(waiting, "pause", "Synthetic interruption.")
        self.assertEqual(paused["active_improve"], binding)
        resumed = navigator.control(paused, "resume", "Resume the saved child.")
        self.assertEqual(resumed["active_improve"], binding)
        self.assertEqual(navigator.current_stage(resumed), "intake")

        blocked_state = self.state()
        blocked_action = self._action(blocked_state)
        waiting_blocked = navigator.apply(
            blocked_state, blocked_action["id"],
            result(outcome="blocked", summary="Synthetic prerequisite missing."),
        )
        self.assertEqual(waiting_blocked["status"], "active")
        self.assertEqual(waiting_blocked["active_improve"]["action_id"], blocked_action["id"])
        blocked = navigator.finish_improve(
            waiting_blocked,
            blocked_action["id"],
            receipt("intake"),
            result(outcome="blocked", summary="Synthetic prerequisite missing."),
        )
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(navigator.current_stage(blocked), "intake")

    def test_cold_recovery_preserves_the_pending_child_binding_without_advancing(self) -> None:
        state = self.state()
        action = self._action(state)
        waiting = navigator.apply(state, action["id"], result())
        with tempfile.TemporaryDirectory(prefix="shiploop-v3-cold-") as temporary:
            root = Path(temporary)
            navigator.save(root, waiting)
            before = (root / "state.md").read_bytes()
            recovered = store.read_record(root / "state.md")
            navigator.validate(recovered)
            self.assertEqual(recovered, waiting)
            self.assertEqual((root / "state.md").read_bytes(), before)
            self.assertEqual(navigator.current_stage(recovered), "intake")
            self.assertEqual(recovered["active_improve"], waiting["active_improve"])

    def test_v3_requirements_policy_routes_through_unbound_and_bound_improve_recovery(self) -> None:
        """Both child forms retain packet locators before and after cold recovery."""
        state = self.state()
        action = self._action(state)
        unbound = navigator.apply(state, action["id"], result())
        self.assertIsNone(unbound["active_improve"]["skill"])
        bound = self._bind_synthetic_child(copy.deepcopy(unbound))

        for name, candidate in (("unbound", unbound), ("bound", bound)):
            with self.subTest(child=name):
                root = Path(self.temp.name) / (name + " requirements recovery")
                root.mkdir()
                current = navigator.render(None, root, candidate)
                self._assert_requirements_policy(current)
                if name == "bound":
                    self.assertIn("Follow the packet's Maintained requirements policy", current)
                    self.assertIn("requirement and test locators", current)

                navigator.save(root, candidate)
                before = (root / "state.md").read_bytes()
                recovered = store.read_record(root / "state.md")
                cold = navigator.render(None, root, recovered)
                self.assertEqual((root / "state.md").read_bytes(), before)
                self.assertEqual(recovered, candidate)
                self._assert_requirements_policy(cold)
                if name == "bound":
                    self.assertIn("Follow the packet's Maintained requirements policy", cold)
                    self.assertIn("requirement and test locators", cold)

    def test_v3_cold_next_retains_requirements_definition_child_context(self) -> None:
        """A recovered Improve packet retains the guide and an existing-spec locator."""
        self.assertTrue(self.requirements_guide.is_file())
        existing_spec = self.repo / "docs" / "existing-spec.md"
        existing_spec.parent.mkdir()
        existing_spec.write_text(
            "# Existing specification\n\n## Response time\n\nPreserve the current bound.\n",
            encoding="utf-8",
        )
        requirement_locator = str(existing_spec) + "#response-time"
        original_request = "Extend the synthetic capability while preserving its response bound."
        state = navigator.new_state(
            str(self.repo),
            original_request,
            protocol_version=3,
            improve_skill="",
        )
        action = self._action(state)
        waiting = navigator.apply(
            state,
            action["id"],
            result(evidence_refs=[requirement_locator]),
        )
        bound = self._bind_synthetic_child(waiting)
        root = Path(self.temp.name) / "cold-requirements-definition-child"
        root.mkdir()
        before_state = copy.deepcopy(bound)
        current = navigator.render(None, root, bound)
        self.assertEqual(bound, before_state)
        navigator.save(root, bound)
        before = (root / "state.md").read_bytes()

        cold = self._cold_next(root)
        recovered = store.read_record(root / "state.md")

        self.assertEqual((root / "state.md").read_bytes(), before)
        self.assertEqual(recovered, bound)
        self.assertEqual(recovered["active_improve"], bound["active_improve"])
        for packet in (current, cold):
            self._assert_requirements_policy(packet)
            self.assertIn(original_request, packet)
            self.assertIn(requirement_locator, packet)
            self.assertIn("Use the packet's Requirements definition guide", packet)

    def test_v3_bound_child_carries_requirement_and_test_locators_through_cold_recovery(self) -> None:
        """Assert structural packet propagation, not that a model interpreted the sources."""
        docs = self.repo / "docs"
        docs.mkdir()
        requirements = docs / "product-rules.md"
        requirements.write_text(
            "# Requirements\n\n## Legal move rules\n\n- Preserve mandatory captures.\n",
            encoding="utf-8",
        )
        self.assertFalse((docs / "requirements.md").exists())
        tests = self.repo / "test"
        tests.mkdir()
        test_cases = tests / "checkers.test.py"
        test_cases.write_text(
            "def test_legal_move_rules():\n    pass\n",
            encoding="utf-8",
        )
        requirement_locator = str(requirements) + "#legal-move-rules"
        test_locator = str(test_cases) + "#test_legal_move_rules"
        run_note = self.repo / ".shiploop" / "notes" / "requirement-review.md"
        run_note.parent.mkdir(parents=True)
        run_note.write_text(
            "# Requirement review\n\n## Capture preservation\n\nRetain the contract source.\n",
            encoding="utf-8",
        )
        run_note_locator = str(run_note) + "#capture-preservation"
        run_note_bytes = run_note.read_bytes()
        work_context = (
            "Preserve mandatory captures; requirements locator: "
            + requirement_locator
            + "; test locator: "
            + test_locator
        )

        state = self.state()
        while navigator.current_stage(state) != "step-plan":
            stage = navigator.current_stage(state)
            extra = {}
            if stage == "plan":
                extra["work_items"] = [
                    {"id": "W1", "title": "Synthetic item", "context": work_context}
                ]
            state = self._produce(state, stage, **extra)
        self.assertEqual(navigator.current_stage(state), "step-plan")

        action = self._action(state)
        waiting = navigator.apply(
            state,
            action["id"],
            result(
                summary="Review the existing requirements and test boundary.",
                evidence_refs=[requirement_locator, test_locator, run_note_locator],
            ),
        )
        bound = self._bind_synthetic_child(copy.deepcopy(waiting))
        before_state = copy.deepcopy(bound)
        root = Path(self.temp.name) / "requirement-locator-child"
        root.mkdir()
        current = navigator.render(None, root, bound)
        self.assertEqual(bound, before_state)
        self._assert_requirements_policy(current)
        self.assertIn("Work item context: " + work_context, current)
        for locator in (requirement_locator, test_locator):
            self.assertEqual(current.count(locator), 2, current)
        self.assertEqual(current.count(run_note_locator), 1, current)
        self.assertEqual(run_note.read_bytes(), run_note_bytes)

        navigator.save(root, bound)
        before = (root / "state.md").read_bytes()
        recovered = store.read_record(root / "state.md")
        cold = navigator.render(None, root, recovered)
        self.assertEqual((root / "state.md").read_bytes(), before)
        self.assertEqual(recovered, bound)
        self._assert_requirements_policy(cold)
        self.assertIn("Work item context: " + work_context, cold)
        for locator in (requirement_locator, test_locator):
            self.assertEqual(cold.count(locator), 2, cold)
        self.assertEqual(cold.count(run_note_locator), 1, cold)
        self.assertEqual(run_note.read_bytes(), run_note_bytes)

    def test_v3_common_and_improve_prompts_preserve_requirements_review_cues(self) -> None:
        """Keep concise review duties without inventing child state or counters."""
        producer = prompts.COMMON
        improve = prompts.improve_prompt("implement")
        for raw_prompt in (producer, improve):
            with self.subTest(prompt="producer" if raw_prompt is producer else "improve"):
                prompt = " ".join(raw_prompt.split())
                self.assertIn("Maintained requirements policy", prompt)
                self.assertIn("Reference handoff policy", prompt)
                self.assertIn("applicable accepted product requirements", prompt)
                self.assertIn("requirement and test locators", prompt)
                self.assertRegex(
                    prompt,
                    r"(?i)(?:do not|never).{0,120}silent(?:ly)? (?:relax|redefine)",
                )
        self.assertIn("preserved and cross-cutting conditions", " ".join(producer.split()))
        self.assertIn("preserve unaffected conditions", " ".join(improve.split()))
        self.assertIn(
            "Requirements definition guide to reconcile existing specs and define "
            "applicable non-functional requirements.",
            " ".join(producer.split()),
        )
        self.assertIn(
            "Requirements definition guide for affected quality criteria and "
            "existing-spec reconciliation.",
            " ".join(improve.split()),
        )
        self.assertIn(
            "non-functional criteria, existing-spec reconciliation",
            prompts.IMPROVE_SCOPES["spec"],
        )

    def test_v3_native_backchain_operations_reuse_selected_until_loop_subcall(self) -> None:
        """Backchain owns dependency work; Until Loop owns its runtime and terminal."""
        operations = {
            "draft": "action `plan` / stage `draft`",
            "audit": "action `review` / stage `audit`",
            "revise": "action `repair` / stage `revise`",
        }
        expected = {
            "spec": ["audit", "revise"],
            "plan": ["draft"],
            "step-plan": ["audit", "revise"],
            "carry-forward": ["audit", "revise"],
            "product-acceptance": ["audit", "revise"],
        }
        for stage in EXPECTED_STAGES:
            with self.subTest(stage=stage):
                producer = " ".join(prompts.prompt(stage).split())
                improve = " ".join(prompts.improve_prompt(stage).split())
                self.assertEqual(
                    [name for name, selector in operations.items() if selector in producer],
                    expected.get(stage, []),
                )
                self.assertEqual(
                    [name for name, selector in operations.items() if selector in improve],
                    [],
                )
        plan = " ".join(prompts.prompt("plan").split())
        audit = " ".join(prompts.prompt("step-plan").split())
        for required in (
            "Backchain standalone Until Loop binding:",
            "selected physical Until Loop root",
            "references/runtime-ephemeral.md",
            "scripts/until_loop_ephemeral.py",
            "references/convergence.md",
            "prompts/convergence-review.prompt.md",
            "Read the Backchain convergence resources",
            "direct natural-language handoff",
            "actual loaded Until Loop card starts its adapter, is the sole CLI caller",
            "old custom Backchain loop",
            "host-judged semantic compatibility",
            "opaque actual Until Loop terminal evidence",
            "only after the child reports `complete`",
            "must not be submitted as a completed parent action",
            "terminal_receipt",
            "planning_gaps",
            "execution_blockers",
            "next_action",
            "two consecutive distinct complete trivial/no-change dependency reviews",
            "The Until Loop child is plan-only",
        ):
            with self.subTest(required=required):
                self.assertIn(required, plan)
        self.assertIn("read-only, one-pass diagnostic", audit)
        self.assertIn("required_trivial_reviews: 2", plan)
        self.assertIn("final candidate identity and domain evidence", plan)
        self.assertIn("one-pass Backchain primitive", " ".join(prompts.improve_prompt("plan").split()))
        self.assertNotIn("Backchain standalone Improve binding:", plan)
        self.assertNotIn("selected physical Improve root", plan)
        self.assertNotIn("convergence_policy.max_passes", plan)
        self.assertNotIn("default maximum of six assessment passes", plan)
        for source in (self.backchain_planning_guide, SCRIPTS.parent / "SKILL.md"):
            with self.subTest(source=source):
                source_text = " ".join(source.read_text(encoding="utf-8").split())
                for requirement in (
                    "`references/convergence.md`",
                    "`prompts/convergence-review.prompt.md`",
                    "sole CLI caller",
                    "old custom Backchain loop",
                ):
                    self.assertIn(requirement, source_text)


    def test_v3_backchain_planning_guidance_is_scoped_to_selected_stages(self) -> None:
        """Producer and actual Improve prompts use the guide only for planning decisions."""
        self.assertTrue(self.backchain_planning_guide.is_file())
        guide = self.backchain_planning_guide.read_text(encoding="utf-8")
        self.assertIn("## Navigator planning", guide)
        navigator_section = guide.split("## Navigator planning\n", 1)[1].split("\n## ", 1)[0]
        self.assertIn("`evidence_refs`", navigator_section)
        self.assertIn("`context`", navigator_section)
        self.assertIn("(#dependency-audit)", navigator_section)
        legacy_carriers = (
            "contract.tests", "coverage_review.dependencies", "context_evidence.dependencies",
            "backchain/plan.md", "step-context",
        )
        for legacy in legacy_carriers:
            self.assertNotIn(legacy, navigator_section)
        planning_stages = {
            "spec", "plan", "step-plan", "carry-forward", "product-acceptance",
        }
        self.assertEqual(prompts.BACKCHAIN_STAGES, frozenset(planning_stages))
        for stage in EXPECTED_STAGES:
            with self.subTest(stage=stage):
                expected = stage in planning_stages
                self.assertEqual(
                    "Backchain planning guide" in prompts.prompt(stage), expected
                )
                self.assertEqual(
                    "Backchain planning guide" in prompts.improve_prompt(stage), expected
                )
                for legacy in legacy_carriers:
                    self.assertNotIn(legacy, prompts.prompt(stage))
                    self.assertNotIn(legacy, prompts.improve_prompt(stage))

    def test_v3_requirements_definition_duties_stay_in_existing_stages(self) -> None:
        """Existing discovery, research, and spec nodes cover the new guide duties."""
        self.assertEqual(tuple(prompts.PRELUDE), EXPECTED_PRELUDE)
        self.assertIn(
            "Locate existing specs and quality policies",
            " ".join(prompts.DUTIES["discovery"].split()),
        )
        self.assertIn(
            "Research consequential quality-target and feasibility unknowns",
            " ".join(prompts.DUTIES["research"].split()),
        )
        self.assertIn(
            "measurable bounds or observable criteria",
            " ".join(prompts.DUTIES["spec"].split()),
        )

    def test_v3_test_strategy_requires_repeatable_harness_revalidation_and_suite_tiers(self) -> None:
        """The global strategy chooses rerunnable coverage before item work starts."""
        strategy = " ".join(prompts.prompt("test-strategy").split())
        for duty in (
            "Read the Repeatable test-suite guide.",
            "Select the major harnesses and suite entry points now",
            "reuse a prior-run harness only after revalidating its current fit",
            "focused, smoke, and full-suite commands",
            "smoke is a bounded subset, never evidence for the full suite",
        ):
            with self.subTest(duty=duty):
                self.assertIn(duty, strategy)

    def test_v3_platform_testing_contract_routes_to_every_test_stage(self) -> None:
        """The global choice and each testing checkpoint retain the same guide route."""
        strategy = " ".join(prompts.prompt("test-strategy").split())
        self.assertIn(GLOBAL_PLATFORM_TESTING_CLAUSE, strategy)
        self.assertIn("by required capability rather than product name", strategy)
        self.assertIn("distinguish inspection from retained assertions", strategy)

        for stage in TEST_HARNESS_STAGES:
            with self.subTest(stage=stage, check="guide route"):
                self.assertIn(REPEATABLE_TEST_SUITE_REFERENCE, prompts.STAGE_REFERENCES[stage])

        step_plan = " ".join(prompts.prompt("step-plan").split())
        self.assertIn(INNER_PLATFORM_TESTING_CLAUSE, step_plan)

        self.assertIn("Link the durable strategy note in ordinary evidence_refs", strategy)
        for stage in ("plan", "step-plan", "test-author", "test-refine", "regression", "system-test-author"):
            with self.subTest(stage=stage, check="saved test strategy consumption"):
                self.assertIn("Run-wide test strategy source", prompts.prompt(stage))
        self.assertIn(
            "originating strategy locator alongside current item-specific test",
            prompts.prompt("carry-forward"),
        )
        self.assertIn("Run-wide test strategy source", prompts.improve_prompt("test-author"))
        decision_stages = {"step-plan", "test-spec", "test-author", "test-refine", "regression"}
        self.assertEqual(prompts.TEST_DECISION_STAGES, decision_stages)
        for stage in decision_stages:
            with self.subTest(stage=stage, check="current item decision carry-forward"):
                instruction = " ".join(prompts.prompt(stage).split())
                self.assertIn("Current item test-decision source", instruction)
                self.assertIn("prior decision locators and any justified revision", instruction)

    def test_v3_remote_test_routes_keep_local_and_remote_evidence_distinct(self) -> None:
        """Route remote test assets without treating a local result as their evidence."""
        strategy = " ".join(prompts.prompt("test-strategy").split())
        for duty in (
            "execution location separately from target location",
            "client checks against a deployed target",
            "remote-resident tests",
            "remote framework",
            "availability, access and deployment prerequisites",
            "define/register, install and invoke remote tests",
            "local pass is not a remote pass",
        ):
            with self.subTest(stage="test-strategy", duty=duty):
                self.assertIn(duty, strategy)

        author = " ".join(prompts.prompt("test-author").split())
        for duty in (
            "remote-resident cases",
            "remote definitions and registration",
            "authorized installation/invocation prerequisites",
        ):
            with self.subTest(stage="test-author", duty=duty):
                self.assertIn(duty, author)

        system_author = " ".join(prompts.prompt("system-test-author").split())
        for duty in (
            "remote-resident definitions and registration",
            "remote framework requires them",
            "authorized installation and invocation",
        ):
            with self.subTest(stage="system-test-author", duty=duty):
                self.assertIn(duty, system_author)

        system_test = " ".join(prompts.prompt("system-test").split())
        for duty in (
            "execution location",
            "remote framework availability",
            "deployed/test revision identity",
            "local pass cannot replace a blocked/unrun required remote check",
            "combined full-suite pass",
        ):
            with self.subTest(stage="system-test", duty=duty):
                self.assertIn(duty, system_test)

    def test_v3_test_lifecycle_and_child_handoff_keep_repeatable_suite_boundaries(self) -> None:
        """Check packet routing and boundaries, without claiming model compliance."""
        test_spec = " ".join(prompts.prompt("test-spec").split())
        for duty in (
            "Specify setup, test/assertions, and teardown together",
            "stateless case needs no setup or teardown",
            "Share expensive setup only with demonstrated noninterference",
            "if in doubt, use per-test isolation",
            "Plan failure cleanup and suite registration.",
        ):
            with self.subTest(stage="test-spec", duty=duty):
                self.assertIn(duty, test_spec)

        test_author = " ".join(prompts.prompt("test-author").split())
        for duty in (
            "Retain tests and fixtures in the repository.",
            "Register each case in the full regression route and applicable focused entry points; decide smoke membership independently without duplicating tests.",
            "verify discovery selects the cases rather than merely recording their paths",
        ):
            with self.subTest(stage="test-author", duty=duty):
                self.assertIn(duty, test_author)

        state = self.state()
        while navigator.current_stage(state) != "test-red":
            stage = navigator.current_stage(state)
            extra = {}
            if stage == "plan":
                extra["work_items"] = [{"id": "W1", "title": "Synthetic item"}]
            state = self._produce(state, stage, **extra)

        action = self._action(state)
        producer_packet = navigator.render(None, self.repo / ".shiploop", state)
        self.assertIn(
            "Do not edit production code to make the test green at this stage.",
            producer_packet,
        )
        waiting = navigator.apply(state, action["id"], result())
        self.assertEqual(navigator.current_stage(waiting), "test-red")
        self.assertEqual(waiting["active_improve"]["action_id"], action["id"])
        bound = self._bind_synthetic_child(waiting)

        handoff = " ".join(
            navigator.render(None, self.repo / ".shiploop", bound).split()
        )
        for duty in (
            "For test plans, authored/refined tests, fixtures, suite wiring or test evidence",
            "harness, case and suite locators",
            "setup/test/teardown (including justified stateless cases)",
            "sharing noninterference, failure cleanup, repeatability, and focused/smoke/full-suite inclusion and cost",
            "authoring and expected RED do not require future production behavior to pass.",
            "remote-resident definitions",
            "framework availability",
            "authorized invocation",
            "execution location",
            "local pass does not satisfy a required remote check",
        ):
            with self.subTest(stage="Improve handoff", duty=duty):
                self.assertIn(duty, handoff)

    def test_v3_initial_baseline_guidance_survives_improve_and_cold_step_plan(self) -> None:
        """Initial-baseline evidence stays in ordinary records without new graph state."""
        self.assertEqual(len(EXPECTED_STAGES), 34)
        self.assertTrue(self.initial_baseline_guide.is_file())
        initial_baseline = str(self.repo / ".shiploop" / "evidence" / "smoke.log")
        prerequisite_context = (
            "Initial baseline failed: "
            + initial_baseline
            + "; repair the affected startup check and rerun it before Feature W1."
        )

        discovery = " ".join(prompts.DUTIES["discovery"].split())
        strategy = " ".join(prompts.DUTIES["test-strategy"].split())
        plan = " ".join(prompts.DUTIES["plan"].split())
        prepare = " ".join(prompts.DUTIES["prepare"].split())
        step_plan = " ".join(prompts.DUTIES["step-plan"].split())
        baseline = " ".join(prompts.DUTIES["baseline"].split())
        for prompt in (discovery, strategy, plan, prepare, step_plan, baseline):
            self.assertIn("Initial repository baseline guide", prompt)
        self.assertIn("first verification activity", discovery)
        self.assertIn("actual execution", discovery)
        self.assertIn("observed initial baseline", strategy)
        self.assertIn("earliest", plan)
        self.assertIn("repair", plan)
        self.assertIn("post-bootstrap characterization", plan)
        self.assertIn("rerun the original initial check", prepare)
        self.assertIn("reuse only when", step_plan)
        self.assertIn("repair or test-bootstrap", baseline)
        for stage in ("discovery", "baseline"):
            improve = " ".join(prompts.improve_prompt(stage).split())
            self.assertIn("Initial repository baseline guide", improve)
            self.assertIn("may not edit product source, tests", improve)

        state = self._produce(self.state(), "intake")
        self.assertEqual(navigator.current_stage(state), "discovery")
        discovery_packet = navigator.render(None, self.repo / ".shiploop", state)
        self._assert_initial_baseline_locator(discovery_packet)
        self.assertIn("first verification activity", " ".join(discovery_packet.split()))

        action = self._action(state)
        waiting = navigator.apply(
            state,
            action["id"],
            result(
                summary="The existing smoke route failed before feature edits.",
                evidence_refs=[initial_baseline],
            ),
        )
        unbound = navigator.render(None, self.repo / ".shiploop", waiting)
        bound = self._bind_synthetic_child(copy.deepcopy(waiting))
        bound_packet = navigator.render(None, self.repo / ".shiploop", bound)
        run_root = self.repo / ".shiploop" / "cold-initial-baseline"
        run_root.mkdir(parents=True)
        navigator.save(run_root, bound)
        before = (run_root / "state.md").read_bytes()
        cold = self._cold_next(run_root)
        self.assertEqual((run_root / "state.md").read_bytes(), before)
        for packet in (unbound, bound_packet, cold):
            self._assert_initial_baseline_locator(packet)
            self.assertIn(initial_baseline, packet)
        for packet in (bound_packet, cold):
            self.assertIn("may not edit product source, tests", " ".join(packet.split()))

        state = self._complete_improve(waiting, action, "discovery")
        for stage in ("research", "spec", "test-strategy"):
            state = self._produce(state, stage)
        self.assertEqual(navigator.current_stage(state), "plan")
        action = self._action(state)
        waiting = navigator.apply(
            state,
            action["id"],
            result(
                evidence_refs=[initial_baseline],
                work_items=[
                    {
                        "id": "R1",
                        "title": "Repair the initial startup baseline",
                        "context": prerequisite_context,
                    },
                    {
                        "id": "W1",
                        "title": "Add the requested feature",
                        "context": "Wait for R1's passing baseline rerun.",
                    },
                ],
            ),
        )
        state = self._complete_improve(waiting, action, "plan")
        state = self._produce(state, "prepare")
        state = self._produce(state, "select-work")
        self.assertEqual(navigator.current_stage(state), "step-plan")
        self.assertEqual(state["work_items"][0]["context"], prerequisite_context)
        cold_root = self.repo / ".shiploop" / "cold-prerequisite-context"
        cold_root.mkdir()
        navigator.save(cold_root, state)
        cold_packet = self._cold_next(cold_root)
        self._assert_initial_baseline_locator(cold_packet)
        self.assertIn(prerequisite_context, cold_packet)

    def test_v3_packets_keep_runtime_and_selected_case_evidence_visible(self) -> None:
        """Synthetic prompt traversal keeps runtime and real-boundary gaps explicit."""
        original_request = (
            "Deliver targetruntime through its requested entry point; localpreview "
            "is a local test route and must not substitute for targetruntime."
        )
        state = navigator.new_state(
            str(self.repo), original_request, protocol_version=3, improve_skill=""
        )
        reconciliation_stages = {
            "verify", "integration-verify", "system-test", "product-acceptance",
            "release-verify", "handoff",
        }
        cold_stages = {"verify", "product-acceptance", "handoff"}
        runtime_stages = {"discovery", "spec", "test-strategy", "product-acceptance"}
        cold_root = Path(self.temp.name) / "cold-evidence-packets"
        cold_root.mkdir()
        while True:
            stage = navigator.current_stage(state)
            if stage in cold_stages:
                navigator.save(cold_root, state)
                before = (cold_root / "state.md").read_bytes()
                recovered = store.read_record(cold_root / "state.md")
                packet = navigator.render(None, cold_root, recovered)
                self.assertEqual((cold_root / "state.md").read_bytes(), before)
                self.assertEqual(recovered, state)
            else:
                packet = navigator.render(None, self.repo / ".shiploop", state)
            normalized_packet = " ".join(packet.split())
            self.assertIn("Requested runtime / entry point / material dependency", normalized_packet)
            self.assertIn("Record local-test-route evidence separately", normalized_packet)
            self.assertIn("Establish compatibility with target-compatible source or local evidence", normalized_packet)
            self.assertIn("#test-cases", normalized_packet)
            self.assertIn("#surface-selection", normalized_packet)
            if stage in runtime_stages:
                self.assertIn("targetruntime", normalized_packet)
                self.assertIn("localpreview", normalized_packet)
            if stage in reconciliation_stages:
                self.assertIn("Selected-case reconciliation", normalized_packet)
                self.assertIn(
                    "passed, failed, blocked, not-run, or justified N/A", normalized_packet
                )
                self.assertIn("Source, HTTP, or DOM structure", normalized_packet)
            if stage == "handoff":
                break
            extra = {}
            if stage == "plan":
                extra["work_items"] = [{"id": "W1", "title": "Synthetic item"}]
            state = self._produce(state, stage, **extra)

    def test_v3_current_and_cold_child_packets_retain_review_note_recovery_context(self) -> None:
        """A selected child retains receipt-reference duties before and after recovery."""
        state = self.state()
        action = self._action(state)
        waiting = self._bind_synthetic_child(
            navigator.apply(state, action["id"], result())
        )
        with tempfile.TemporaryDirectory(prefix="shiploop-v3-improve-notes-") as temporary:
            root = Path(temporary)
            current_packet = navigator.render(None, root, waiting)
            navigator.save(root, waiting)
            before = (root / "state.md").read_bytes()
            recovered = store.read_record(root / "state.md")
            cold_packet = navigator.render(None, root, recovered)

            self.assertEqual((root / "state.md").read_bytes(), before)
            self.assertEqual(recovered["active_improve"], waiting["active_improve"])
            safe_reference = str(
                self.repo / ".until-loop" / "reviews" / "review-one.md"
            )
            for render_state, packet in (("current", current_packet), ("cold", cold_packet)):
                with self.subTest(render_state=render_state):
                    normalized_packet = " ".join(packet.split())
                    self.assertIn("Child workspace: " + str(self.repo), normalized_packet)
                    self.assertIn(
                        "absolute regular single-link non-symlink files under Child workspace above",
                        normalized_packet,
                    )
                    self.assertIn(safe_reference, normalized_packet)
                    self.assertIn(
                        "sibling run/inbox/control paths outside that root", normalized_packet
                    )
                    for detail in (
                        "Ordinary child review notes retain candidate and scope identity",
                        "independent reviewer availability, use, or permitted fallback",
                        "whether reused evidence still applies",
                        "findings, current checks, and limits",
                        "short decision and reference locators for cold recovery",
                        "not a synthetic receipt schema or a new parent validation rule",
                    ):
                        self.assertIn(detail, normalized_packet)

    def test_outer_replan_adds_corrective_work_without_rewinding_completed_work(self) -> None:
        state = self._to_outer(self.state())
        self.assertEqual(state["completed_work_items"], ["W1"])
        for completed_outer_stage in ("system-test-author", "system-test"):
            self.assertEqual(navigator.current_stage(state), completed_outer_stage)
            state = self._produce(state, completed_outer_stage)
        stage = navigator.current_stage(state)
        self.assertEqual(stage, "product-acceptance")
        action = self._action(state)
        waiting = navigator.apply(
            state,
            action["id"],
            result(
                outcome="replan",
                summary="A corrective capability is required.",
                work_items=[{"id": "W2", "title": "Corrective item"}],
            ),
        )
        self.assertEqual(navigator.current_stage(waiting), stage)
        self.assertEqual(waiting["active_improve"]["action_id"], action["id"])
        revised = navigator.finish_improve(waiting, action["id"], receipt(stage))
        self.assertEqual(revised["completed_work_items"], ["W1"])
        self.assertIn("W2", [item["id"] for item in revised["work_items"]])
        self.assertEqual(navigator.current_stage(revised), "select-work")
        self.assertNotEqual(navigator.current_stage(revised), stage)
        packet = navigator.render(None, self.repo.parent / "replan-progress", revised)
        self.assertIn("Outer stages: 0/9 accepted done.", packet)
        self.assertIn(
            "Outer stages pending: system-test-author, system-test, product-acceptance, "
            "release-plan, release-check, release, release-verify, operations, handoff",
            packet,
        )

    def test_v3_plan_omission_keeps_default_w1_compatibility(self) -> None:
        """A v3 plan may omit work_items and retain its initial compatibility item."""
        state = self._at_plan()
        default_items = copy.deepcopy(state["work_items"])
        action = self._action(state)
        waiting = navigator.apply(state, action["id"], result())
        completed = navigator.finish_improve(waiting, action["id"], receipt("plan"))

        self.assertEqual(completed["work_items"], default_items)
        self.assertEqual([item["id"] for item in completed["work_items"]], ["W1"])
        self.assertNotIn("work_items", completed["accepted"][action["id"]])
        self.assertEqual(navigator.current_stage(completed), "prepare")

    def test_v3_plan_final_result_keeps_multiple_items_through_cold_recovery(self) -> None:
        """The actual Improve revision, rather than its draft, owns the durable queue."""
        draft_items = [{"id": "W1", "title": "Draft feature item"}]
        final_items = [
            {"id": "W1", "title": "Feature item"},
            {"id": "W2", "title": "Integration item"},
            {
                "id": "AUDIT",
                "title": "Detached audit item",
                "context": "Revalidate the independent audit after feature integration.",
            },
        ]
        state = self._at_plan()
        action = self._action(state)
        waiting = navigator.apply(state, action["id"], result(work_items=draft_items))
        completed = navigator.finish_improve(
            waiting,
            action["id"],
            receipt("plan"),
            result(work_items=final_items),
        )

        self.assertEqual(
            completed["improve_results"][action["id"]]["seed_result"]["work_items"],
            draft_items,
        )
        self.assertEqual(completed["accepted"][action["id"]]["work_items"], final_items)
        self.assertEqual(completed["work_items"], final_items)

        root = Path(self.temp.name) / "plan-final-result-cold"
        root.mkdir()
        navigator.save(root, completed)
        before = (root / "state.md").read_bytes()
        recovered = store.read_record(root / "state.md")
        cold = self._cold_next(root)

        navigator.validate(recovered)
        self.assertEqual(recovered, completed)
        self.assertEqual(recovered["work_items"], final_items)
        self.assertEqual((root / "state.md").read_bytes(), before)
        self.assertIn("Work items planned: 3", cold)

    def test_v3_carry_forward_omission_retains_all_pending_items(self) -> None:
        """Omitting work_items at carry-forward completes only the current item."""
        rows = [
            {"id": "W1", "title": "Feature item"},
            {"id": "W2", "title": "Integration item"},
            {"id": "W3", "title": "Audit item"},
        ]
        state = self._advance_to_carry_forward(self._planned_queue(rows))
        action = self._action(state)
        waiting = navigator.apply(state, action["id"], result())
        completed = navigator.finish_improve(waiting, action["id"], receipt("carry-forward"))

        self.assertEqual([item["id"] for item in completed["work_items"]], ["W1", "W2", "W3"])
        self.assertEqual(completed["completed_work_items"], ["W1"])
        self.assertEqual(completed["work_index"], 1)
        self.assertNotIn("work_items", completed["accepted"][action["id"]])
        self.assertEqual(navigator.current_stage(completed), "select-work")

    def test_v3_carry_forward_replaces_only_future_queue_and_rejects_prior_ids(self) -> None:
        """An explicit carry-forward array replaces future work; it cannot reuse prior IDs."""
        rows = [
            {"id": "W1", "title": "Feature item"},
            {"id": "W2", "title": "Integration item"},
            {"id": "W3", "title": "Detached audit item"},
        ]
        replacement = [{"id": "NEW", "title": "New audit finding"}]
        state = self._advance_to_carry_forward(self._planned_queue(rows))
        self.assertEqual([item["id"] for item in state["work_items"]], ["W1", "W2", "W3"])
        action = self._action(state)
        waiting = navigator.apply(state, action["id"], result(work_items=replacement))
        revised = navigator.finish_improve(waiting, action["id"], receipt("carry-forward"))

        self.assertEqual([item["id"] for item in revised["work_items"]], ["W1", "NEW"])
        self.assertEqual(
            [item["id"] for item in revised["work_items"][revised["work_index"]:]],
            ["NEW"],
        )
        self.assertEqual(revised["completed_work_items"], ["W1"])
        self.assertEqual(navigator.current_stage(revised), "select-work")

        empty_state = self._advance_to_carry_forward(self._planned_queue(rows))
        empty_action = self._action(empty_state)
        empty_waiting = navigator.apply(
            empty_state, empty_action["id"], result(work_items=[])
        )
        cleared = navigator.finish_improve(
            empty_waiting, empty_action["id"], receipt("carry-forward")
        )
        self.assertEqual([item["id"] for item in cleared["work_items"]], ["W1"])
        self.assertEqual(cleared["completed_work_items"], ["W1"])
        self.assertEqual(navigator.current_stage(cleared), "system-test-author")

        current_state = self._advance_to_carry_forward(self._planned_queue(rows))
        current_action = self._action(current_state)
        current_waiting = navigator.apply(current_state, current_action["id"], result())
        before_current = copy.deepcopy(current_waiting)
        with self.assertRaisesRegex(
            navigator.NavigatorError, "repeats completed or current ID"
        ):
            navigator.finish_improve(
                current_waiting,
                current_action["id"],
                receipt("carry-forward"),
                result(work_items=[{"id": "W1", "title": "Duplicate current item"}]),
            )
        self.assertEqual(current_waiting, before_current)

        completed_state = self._advance_to_carry_forward(self._planned_queue(rows))
        completed_action = self._action(completed_state)
        completed_waiting = navigator.apply(completed_state, completed_action["id"], result())
        completed_state = navigator.finish_improve(
            completed_waiting, completed_action["id"], receipt("carry-forward")
        )
        completed_state = self._advance_to_carry_forward(completed_state)
        self.assertEqual(completed_state["completed_work_items"], ["W1"])
        self.assertEqual(completed_state["work_items"][completed_state["work_index"]]["id"], "W2")
        prior_action = self._action(completed_state)
        prior_waiting = navigator.apply(completed_state, prior_action["id"], result())
        before_prior = copy.deepcopy(prior_waiting)
        with self.assertRaisesRegex(
            navigator.NavigatorError, "repeats completed or current ID"
        ):
            navigator.finish_improve(
                prior_waiting,
                prior_action["id"],
                receipt("carry-forward"),
                result(work_items=[{"id": "W1", "title": "Duplicate completed item"}]),
            )
        self.assertEqual(prior_waiting, before_prior)

    def test_v3_serial_queue_finishes_detached_audit_before_outer_work(self) -> None:
        """Every required queued item has a complete inner lifecycle before outer stages."""
        rows = [
            {"id": "FEATURE", "title": "Feature implementation"},
            {"id": "INTEGRATION", "title": "Feature integration"},
            {
                "id": "AUDIT",
                "title": "Detached independent audit",
                "context": "Run after the feature and integration items are complete.",
            },
        ]
        state = self._planned_queue(rows)
        state = self._produce(state, "prepare")
        self.assertEqual(navigator.current_stage(state), "select-work")
        completed_stages = {item["id"]: [] for item in rows}
        repeated = False
        blocked = False

        while navigator.current_stage(state) in EXPECTED_INNER:
            stage = navigator.current_stage(state)
            item_id = state["work_items"][state["work_index"]]["id"]
            action = self._action(state)
            if item_id == "AUDIT" and stage == "test-red" and not repeated:
                waiting = navigator.apply(
                    state,
                    action["id"],
                    result(outcome="repeat", summary="Repeat the audit RED evidence."),
                )
                state = navigator.finish_improve(
                    waiting, action["id"], receipt(stage)
                )
                self.assertEqual(navigator.current_stage(state), "test-red")
                self.assertEqual(state["work_index"], 2)
                repeated = True
                continue
            if item_id == "AUDIT" and stage == "verify" and not blocked:
                waiting = navigator.apply(
                    state,
                    action["id"],
                    result(outcome="blocked", summary="Audit target is temporarily unavailable."),
                )
                blocked_state = navigator.finish_improve(
                    waiting, action["id"], receipt(stage)
                )
                self.assertEqual(blocked_state["status"], "blocked")
                self.assertEqual(navigator.current_stage(blocked_state), "verify")
                self.assertEqual(blocked_state["work_index"], 2)
                state = navigator.control(
                    blocked_state, "resume", "Audit target became available."
                )
                self.assertEqual(navigator.current_stage(state), "verify")
                self.assertEqual(state["work_index"], 2)
                blocked = True
                continue

            state = self._produce(state, stage)
            completed_stages[item_id].append(stage)
            if item_id == "INTEGRATION" and stage == "carry-forward":
                self.assertEqual(navigator.current_stage(state), "select-work")
                self.assertEqual(
                    state["work_items"][state["work_index"]]["id"], "AUDIT"
                )
                self.assertNotIn(navigator.current_stage(state), EXPECTED_OUTER)

        self.assertTrue(repeated)
        self.assertTrue(blocked)
        for item_id in ("FEATURE", "INTEGRATION", "AUDIT"):
            with self.subTest(item=item_id):
                self.assertEqual(completed_stages[item_id], list(EXPECTED_INNER))
                self.assertEqual(
                    state["inner_loops"][item_id], {"stage": "done", "action": None}
                )
        self.assertEqual(state["completed_work_items"], ["FEATURE", "INTEGRATION", "AUDIT"])
        self.assertEqual(navigator.current_stage(state), "system-test-author")
        self.assertFalse(
            any(entry["stage"] in EXPECTED_OUTER for entry in state["history"])
        )
        audit_outcomes = [
            entry["outcome"] for entry in state["history"] if entry["workitem"] == "AUDIT"
        ]
        self.assertEqual(audit_outcomes.count("repeat"), 1)
        self.assertEqual(audit_outcomes.count("blocked"), 1)

    def test_v3_queue_packet_contracts_are_durable_and_serial(self) -> None:
        """Packets expose the whole durable queue without inventing ready-item selection."""
        root = (Path(self.temp.name) / "queue-packet-contracts").resolve()
        root.mkdir()
        queue_locator = f"Full ordered work queue: {root / 'state.md'}; field work_items."
        proposed_queue_locator = (
            f"Proposed queue awaiting Improve: {root / 'state.md'}; "
            "field active_improve.seed_result.work_items."
        )
        replacement_rule = (
            "Omit work_items to retain the future queue. Supplied work_items replaces "
            "the entire future queue after the current item; it does not append."
        )

        plan = self._at_plan()
        plan_packet = navigator.render(None, root, plan)
        self.assertIn(queue_locator, plan_packet)
        template_text = plan_packet.split("Result template:\n", 1)[1].split(
            "\nCall this when done:", 1
        )[0]
        plan_template = store.loads(template_text)
        self.assertIn("work_items", plan_template)
        self.assertEqual(len(plan_template["work_items"]), 1)
        self.assertEqual(
            set(plan_template["work_items"][0]), {"id", "title", "context"}
        )
        self.assertNotIn(
            "work_items", store.loads(navigator._result_template(plan, "carry-forward"))
        )
        v2 = navigator.new_state(str(self.repo), "Older protocol run.", protocol_version=2)
        self.assertNotIn("work_items", store.loads(navigator._result_template(v2, "plan")))

        plan_action = self._action(plan)
        plan_child = self._bind_synthetic_child(
            navigator.apply(
                plan,
                plan_action["id"],
                result(work_items=[{"id": "DRAFT", "title": "Revised plan item"}]),
            )
        )
        self.assertEqual([item["id"] for item in plan_child["work_items"]], ["W1"])
        self.assertIn(queue_locator, navigator.render(None, root, plan_child))
        self.assertIn(proposed_queue_locator, navigator.render(None, root, plan_child))
        navigator.save(root, plan_child)
        cold_plan_child_packet = self._cold_next(root)
        self.assertIn(queue_locator, cold_plan_child_packet)
        self.assertIn(proposed_queue_locator, cold_plan_child_packet)
        state = navigator.finish_improve(plan_child, plan_action["id"], receipt("plan"))
        state = self._produce(state, "prepare")
        self.assertEqual(navigator.current_stage(state), "select-work")
        select_packet = navigator.render(None, root, state)
        self.assertIn(queue_locator, select_packet)
        self.assertIn(
            "Revalidate the current script-selected work item in queue order.", select_packet
        )
        self.assertNotIn("Select the next ready work item", select_packet)

        select_action = self._action(state)
        select_child = self._bind_synthetic_child(
            navigator.apply(state, select_action["id"], result())
        )
        self.assertIn(queue_locator, navigator.render(None, root, select_child))
        state = navigator.finish_improve(
            select_child, select_action["id"], receipt("select-work")
        )
        state = self._advance_to_carry_forward(state)
        carry_packet = navigator.render(None, root, state)
        self.assertIn(queue_locator, carry_packet)
        self.assertIn(replacement_rule, carry_packet)

        carry_action = self._action(state)
        carry_child = self._bind_synthetic_child(
            navigator.apply(
                state,
                carry_action["id"],
                result(work_items=[{"id": "FOLLOWUP", "title": "Carry-forward item"}]),
            )
        )
        self.assertIn(proposed_queue_locator, navigator.render(None, root, carry_child))
        navigator.save(root, carry_child)
        cold_child_packet = self._cold_next(root)
        self.assertIn(queue_locator, cold_child_packet)
        self.assertIn(proposed_queue_locator, cold_child_packet)
        self.assertIn(replacement_rule, cold_child_packet)

    def test_malformed_bound_skill_fails_with_controlled_recovery_error(self) -> None:
        state = self.state()
        waiting = navigator.apply(state, self._action(state)["id"], result())
        child = waiting["active_improve"]
        child["version"] = 1
        child["contract_marker"] = "ShipLoop standalone Improve binding: " + child["binding_id"]
        child["skill"] = {}
        with self.assertRaisesRegex(navigator.NavigatorError, "Improve skill binding is invalid"):
            navigator.validate(waiting)
        with self.assertRaisesRegex(navigator.NavigatorError, "Improve skill binding is invalid"):
            navigator.render(None, self.repo / ".shiploop", waiting)

        child["skill"] = {
            "skill_card": "/skills/improve/SKILL.md", "runtime_card": "/runtime/SKILL.md",
            "runtime_cli": "relative/runtime", "skill_version": "unversioned",
            "runtime_version": "unversioned",
        }
        with self.assertRaisesRegex(navigator.NavigatorError, "paths must be absolute"):
            navigator.validate(waiting)


if __name__ == "__main__":
    unittest.main(verbosity=2)
