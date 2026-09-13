#!/usr/bin/env python3
"""Real-CLI regression coverage for ShipLoop carry-forward knowledge."""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
ACTION_WALK = ROOT / "test" / "shiploop-action-walk.test.py"


def load_action_walk_fixture():
    """Reuse the real planning/execution fixture without duplicating its walk."""
    loader = importlib.machinery.SourceFileLoader(
        "shiploop_action_walk_fixture", str(ACTION_WALK)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError(f"could not load {ACTION_WALK}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return module


ACTION = load_action_walk_fixture()

import shiploop_evidence as evidence  # noqa: E402


class ShipLoopKnowledgeTests(ACTION.ShipLoopActionWalkFixture):
    """Carry-forward gates exercised through fresh public CLI subprocesses."""

    def discovery(
        self,
        *,
        observation,
        disposition,
        identifier="K-FIXTURE-001",
        scope=None,
        domain="test-strategy",
    ):
        return {
            "id": identifier,
            "domain": domain,
            "observation": observation,
            "evidence": "checks/fixture-exact-output.md",
            "scope": ["S1"] if scope is None else scope,
            "disposition": disposition,
            "rationale": "The isolated fixture keeps this observation in the active step.",
            "revalidate": "Repeat the exact-output check after the next scoped repair.",
        }

    def commit_checkpoint(self, sid, checkpoint, carry_learning, *, label):
        wt = self.worktree(sid)
        self.git("add", f"{sid.lower()}.py", cwd=wt)
        primary = self.formatted_commit(
            sid,
            checkpoint["iteration"],
            checkpoint["verification_action"],
            checkpoint["review_learning"],
            checkpoint["apply_learning"],
            carry_learning,
        )
        return self.complete(
            {
                "summary": "The primary commit retains every required checkpoint learning.",
                "commit": primary,
            },
            label=label,
        )

    def repair_rejected_post_inner_objective(self, sid, *, label, defect=False):
        """Abort a bad post-inner candidate and prove its final proof is reset."""
        binding = dict(self.state()["objective"])
        receipt = ACTION.store.read_record(self.run_dir / binding["receipt"])
        interrupted = receipt["current_pass"]
        if defect:
            product = self.worktree(sid) / f"{sid.lower()}.txt"
            product.write_text("broken during post-inner objective\n", encoding="utf-8")
            self.assertNotEqual(self.git("diff", "--", product.name, cwd=self.worktree(sid)), "")
        repair_action = self.action_id()
        self.cli(
            "repair",
            "--action",
            repair_action,
            "--reason",
            "The rejected post-inner candidate and observed product defect require a material inner-loop restart.",
        )
        state = self.state()
        self.assertEqual(state["stage"], "review")
        self.assertNotIn("objective", state)
        rec = self.receipt(sid)
        self.assertEqual(rec["improve_cycles"][-1]["kind"], "post-inner-objective-repair")
        self.assertEqual(rec["improve_cycles"][-1]["interrupted_objective_pass"], interrupted["id"])
        for key in (
            "final_check_action",
            "final_head",
            "contract_done",
            "contract_integration_ready",
            "merge_target",
            "plan_review",
        ):
            self.assertNotIn(key, rec)
        abandoned = ACTION.store.read_record(self.run_dir / binding["receipt"])
        archived = abandoned["abandoned_passes"][-1]
        self.assertEqual(archived["id"], interrupted["id"])
        archive = self.run_dir / ACTION.objectives.abandoned_name(
            binding["loop_id"], interrupted["id"]
        )
        self.assertTrue(archive.is_file())
        self.assertEqual(ACTION.store.read_record(archive), archived)
        if defect:
            product.write_text(self.output_for(sid) + "\n", encoding="utf-8")

    def rerun_inner_after_post_inner_repair(self, sid, *, label):
        """Finish the restarted inner loop before submitting a new outer candidate."""
        self.run_improve_iteration(sid, material=False)
        self.assertEqual(self.state()["stage"], "review")
        self.run_improve_iteration(sid, material=False)
        self.assertEqual(self.state()["stage"], "final-verify")
        final_action = self.action_id()
        self.verify_current(self.manifest_for(sid), label=f"{label}-restarted-final-checks")
        self.complete(
            {
                "summary": "Fresh final checks passed after the material post-inner repair restart.",
                "done_evidence": self.done_evidence(sid),
            },
            action_id=final_action,
            label=f"{label}-restarted-final-verify",
        )
        self.assertEqual(self.state()["stage"], "post-inner")

    def test_carry_forward_checkpoint_is_cold_readable_and_fail_closed(self):
        self.bootstrap_to_first_implementation()
        self.start_step("S1", exercise_failed_and_stale=False)

        # A single first page cannot be represented as a complete review
        # acknowledgment, even when it has the correct current digest.
        partial_review_action = self.action_id()
        self.cli(
            "history", "--action", partial_review_action, "--limit", "10", "--skip", "0", "--full"
        )
        read_path = self.run_dir / "knowledge-reads" / f"{partial_review_action}.md"
        rejected = self.cli(
            "context",
            "--section",
            "knowledge",
            "--offset",
            "999999",
            "--limit",
            "1",
            code=2,
        )
        self.assertIn("offset", rejected.stderr)
        self.assertFalse(read_path.exists())
        partial = self.cli(
            "context", "--section", "knowledge", "--offset", "0", "--limit", "1"
        ).stdout
        digest = re.search(r"Context knowledge; digest ([0-9a-f]+)", partial)
        self.assertIsNotNone(digest, partial)
        self.assertIn("Continue: --offset", partial)
        stale_digest = {
            "summary": "The acknowledgement carries a stale digest.",
            "findings": [],
            "test_review": "The exact-output test remains current.",
            "learnings": "A stale digest cannot certify a review.",
            "knowledge_read": {
                "revision": self.state()["knowledge_revision"],
                "digest": "0" * 64,
                "scope": ["all", "S1"],
            },
        }
        rejected, _ = self.complete(
            stale_digest,
            action_id=partial_review_action,
            code=2,
            label="stale-knowledge-digest",
        )
        self.assertIn("current knowledge_read", rejected.stderr)
        rejected, _ = self.complete(
            {
                "summary": "Only the first bounded knowledge page was read.",
                "findings": [],
                "test_review": "The exact-output test remains current.",
                "learnings": "A partial knowledge page cannot certify a review.",
                "knowledge_read": {
                    "revision": self.state()["knowledge_revision"],
                    "digest": digest.group(1),
                    "scope": ["all", "S1"],
                },
            },
            action_id=partial_review_action,
            code=2,
            label="partial-knowledge-read",
        )
        self.assertIn("every bounded page", rejected.stderr)
        self.assertEqual(self.state()["stage"], "review")

        first = self.run_improve_iteration(
            "S1", material=False, stop_at_carry_forward=True
        )
        first_action = first["carry_action"]
        self.assertEqual(self.state()["stage"], "carry-forward")
        cold_packet = self.cli("next").stdout
        self.assertIn("carry-forward", cold_packet)
        self.assertIn("knowledge", cold_packet)

        missing = self.carry_forward_payload()
        del missing["learnings"]
        rejected, _ = self.complete(
            missing,
            action_id=first_action,
            code=2,
            label="missing-carry-learning-field",
        )
        self.assertIn("unknown or missing fields", rejected.stderr)
        unknown = self.carry_forward_payload()
        unknown["unexpected"] = "must not reach the ledger"
        rejected, _ = self.complete(
            unknown,
            action_id=first_action,
            code=2,
            label="unknown-carry-field",
        )
        self.assertIn("unknown or missing fields", rejected.stderr)

        # The current ledger is byte-bound.  Both a malformed replacement and
        # an otherwise equivalent CRLF rewrite block the checkpoint until the
        # script-maintained bytes are restored.
        ledger_path = self.run_dir / "knowledge.md"
        pristine_ledger = ledger_path.read_bytes()
        for label, drifted in (
            ("corrupt-knowledge-ledger", b"not a ShipLoop knowledge ledger\n"),
            ("crlf-knowledge-ledger", pristine_ledger.replace(b"\n", b"\r\n")),
        ):
            with self.subTest(label=label):
                self.assertNotEqual(drifted, pristine_ledger)
                ledger_path.write_bytes(drifted)
                rejected, _ = self.complete(
                    self.carry_forward_payload(),
                    action_id=first_action,
                    code=2,
                    label=label,
                )
                self.assertIn("knowledge hash drift", rejected.stderr)
                self.assertFalse(
                    (self.run_dir / "results" / f"{first_action}.md").exists()
                )
                ledger_path.write_bytes(pristine_ledger)

        # Reject a credential-looking result before an action result or checkpoint
        # can be retained.  The input fixture is intentionally outside .shiploop.
        secret = self.carry_forward_payload(
            discoveries=[
                self.discovery(
                    observation="The probe exposed sk-proj-0123456789abcdef.",
                    disposition="informational",
                    identifier="K-SECRET-REJECTED",
                )
            ]
        )
        secret["system_test_review"] = {
            "decision": "no-change",
            "evidence": "The credential-rejection fixture does not change the mapped global system-test requirement.",
            "discovery_ids": [],
        }
        secret_result = self.record("secret-carry-forward", secret)
        rejected = self.cli(
            "complete", "--action", first_action, "--result", secret_result, code=2
        )
        self.assertIn("credential secret", rejected.stderr)
        self.assertFalse((self.run_dir / "results" / f"{first_action}.md").exists())
        self.assertFalse(
            (self.run_dir / "knowledge-history" / f"{first_action}.md").exists()
        )
        self.assertEqual(self.state()["stage"], "carry-forward")

        credential_url = self.carry_forward_payload(
            discoveries=[
                dict(
                    self.discovery(
                        observation="The probe route must be described without embedded credentials.",
                        disposition="informational",
                        identifier="K-CREDENTIAL-URL-REJECTED",
                    ),
                    evidence="https://operator:sk-proj-0123456789abcdef@example.invalid/probe",
                )
            ]
        )
        credential_url["system_test_review"] = {
            "decision": "no-change",
            "evidence": "The credential-URL rejection fixture does not change the mapped global system-test requirement.",
            "discovery_ids": [],
        }
        credential_result = self.record("credential-url-carry-forward", credential_url)
        rejected = self.cli(
            "complete", "--action", first_action, "--result", credential_result, code=2
        )
        self.assertIn("credential secret", rejected.stderr)
        self.assertFalse((self.run_dir / "results" / f"{first_action}.md").exists())

        no_change_learning = "No discovery changes the current fixture contract."
        no_change = self.carry_forward_payload(learnings=no_change_learning)
        _, no_change_result = self.complete(
            no_change, action_id=first_action, label="first-no-change"
        )
        after_no_change = self.state()
        self.assertEqual(after_no_change["stage"], "commit")
        self.assertGreater(after_no_change["knowledge_revision"], 0)
        self.assertEqual(after_no_change["knowledge_action_id"], first_action)
        checkpoint_path = self.run_dir / "knowledge-history" / f"{first_action}.md"
        self.assertTrue(checkpoint_path.is_file())
        self.assertTrue((self.run_dir / "knowledge.md").is_file())
        cold_knowledge = self.cli(
            "context", "--section", "knowledge", "--offset", "0", "--limit", "8000"
        ).stdout
        self.assertIn("Context knowledge; digest", cold_knowledge)
        self.assertIn("knowledge_revision", cold_knowledge)

        # A replay of the completed checkpoint is idempotent; it cannot create a
        # second version or a second immutable checkpoint for the same action.
        state_before_replay = (self.run_dir / "state.md").read_bytes()
        checkpoint_before_replay = checkpoint_path.read_bytes()
        self.cli("complete", "--action", first_action, "--result", no_change_result)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), state_before_replay)
        self.assertEqual(checkpoint_path.read_bytes(), checkpoint_before_replay)

        # Even if a hostile late edit also rewrites the local check fingerprint,
        # commit compares the worktree to the carry-forward product fingerprint.
        wt = self.worktree("S1")
        source_path = wt / "s1.py"
        original_source = source_path.read_bytes()
        check_path = self.run_dir / "checks" / f"{first['verification_action']}.md"
        original_check = check_path.read_bytes()
        source_path.write_bytes(original_source + b"# late drift after checkpoint\n")
        tampered_check = ACTION.store.read_record(check_path)
        fingerprint = evidence.fingerprint(wt)
        for key in (
            "before_fingerprint",
            "after_fingerprint",
            "before",
            "after",
        ):
            tampered_check["results"][key] = fingerprint
        ACTION.store.write_record(check_path, tampered_check, title="Tampered checks")
        rejected, _ = self.complete(
            {
                "summary": "Attempt to certify a product tree changed after carry-forward.",
                "commit": first["iteration"]["previous_sha"],
            },
            code=2,
            label="carry-product-fingerprint-drift",
        )
        self.assertIn("worktree changed after carry-forward", rejected.stderr)
        source_path.write_bytes(original_source)
        check_path.write_bytes(original_check)

        # The primary commit cannot omit the checkpoint learning even though its
        # verification and review sections are otherwise structurally valid.
        self.git("add", "s1.py", cwd=wt)
        missing_learning_sha = self.formatted_commit(
            "S1",
            first["iteration"],
            first["verification_action"],
            first["review_learning"],
            first["apply_learning"],
            "A substituted carry-forward learning.",
        )
        rejected, _ = self.complete(
            {
                "summary": "This primary commit omits the recorded checkpoint learning.",
                "commit": missing_learning_sha,
            },
            code=2,
            label="missing-carry-learning",
        )
        self.assertIn("verbatim", rejected.stderr)
        self.assertEqual(self.state()["stage"], "commit")

        self.commit_checkpoint(
            "S1", first, no_change_learning, label="first-primary"
        )
        self.assertEqual(self.state()["stage"], "review")

        # An execution review must acknowledge the bounded knowledge selector;
        # history alone is insufficient.
        review_action = self.action_id()
        self.cli(
            "history", "--action", review_action, "--limit", "10", "--skip", "0", "--full"
        )
        rejected, _ = self.complete(
            {
                "summary": "History was read but knowledge was not acknowledged.",
                "findings": [],
                "test_review": "The exact-output test remains current.",
                "learnings": "History alone cannot replace a current knowledge read.",
            },
            action_id=review_action,
            code=2,
            label="missing-knowledge-read",
        )
        self.assertIn("knowledge", rejected.stderr)
        self.assertEqual(self.state()["stage"], "review")

        repair = self.run_improve_iteration(
            "S1", material=False, stop_at_carry_forward=True
        )
        repair_action = repair["carry_action"]
        self.assertEqual(self.state()["stage"], "carry-forward")
        stale = self.carry_forward_payload(
            learnings="This stale checkpoint must not overwrite the current ledger."
        )
        stale["knowledge_revision"] -= 1
        rejected, _ = self.complete(
            stale,
            action_id=repair_action,
            code=2,
            label="stale-knowledge-revision",
        )
        self.assertIn("stale knowledge revision", rejected.stderr)
        self.assertEqual(self.state()["stage"], "carry-forward")

        current_repair = self.carry_forward_payload(
            learnings="The exact-output fixture needs a current-step repair before convergence.",
            discoveries=[
                self.discovery(
                    observation="The active fixture test must be rerun after a repaired implementation.",
                    disposition="current-step-repair",
                )
            ],
        )
        self.complete(
            current_repair, action_id=repair_action, label="current-step-repair"
        )
        self.assertEqual(self.state()["stage"], "review")
        repaired_receipt = self.receipt("S1")
        self.assertTrue(
            any(
                row.get("kind") == "carry-forward-repair"
                for row in repaired_receipt["improve_cycles"]
            )
        )

        superseding = self.run_improve_iteration(
            "S1", material=False, stop_at_carry_forward=True
        )
        superseding_learning = "The repaired fixture leaves one current test-strategy observation."
        self.complete(
            self.carry_forward_payload(
                learnings=superseding_learning,
                discoveries=[
                    self.discovery(
                        observation="The repaired exact-output test is the current evidence for this fixture.",
                        disposition="informational",
                    )
                ],
            ),
            action_id=superseding["carry_action"],
            label="superseding-discovery",
        )
        ledger = (self.run_dir / "knowledge.md").read_text(encoding="utf-8")
        history = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((self.run_dir / "knowledge-history").glob("*.md"))
        )
        self.assertIn("K-FIXTURE-001", ledger)
        self.assertIn("current evidence", ledger)
        self.assertIn("must be rerun", history)
        self.commit_checkpoint(
            "S1", superseding, superseding_learning, label="superseding-primary"
        )

        # Exact-byte ledger drift must still leave emergency pause/halt paths
        # available for diagnosis instead of turning a damaged run into a trap.
        ledger_path = self.run_dir / "knowledge.md"
        pristine_ledger = ledger_path.read_bytes()
        ledger_path.write_bytes(pristine_ledger.replace(b"\n", b"\r\n"))
        self.cli("pause", "--reason", "Preserve the byte-drift diagnostic.")
        self.assertTrue(self.state().get("paused"))
        self.cli("halt", "--reason", "Stop after recording the byte-drift diagnostic.")
        self.assertEqual(self.state()["stage"], "halted")

    def test_pending_mapping_and_pause_stay_visible_to_the_next_step(self):
        self.bootstrap_to_first_implementation()
        self.start_step("S1", exercise_failed_and_stale=False)
        pending_id = "K-PENDING-001"
        pending_learning = "A cross-step test-strategy concern requires a changed pending step."
        self.run_improve_iteration(
            "S1",
            material=False,
            carry_payload=self.carry_forward_payload(
                learnings=pending_learning,
                discoveries=[
                    self.discovery(
                        observation="The dependent fixture step needs an explicit pending test correction.",
                        disposition="pending-replan",
                        identifier=pending_id,
                        scope=["S2"],
                    )
                ],
            ),
        )
        self.assertEqual(self.state()["stage"], "review")
        self.run_improve_iteration("S1", material=False)
        self.assertEqual(self.state()["stage"], "final-verify")
        final_action = self.action_id()
        self.verify_current(self.manifest_for("S1"), label="pending-final-checks")
        self.complete(
            {
                "summary": "Fresh final checks keep the pending obligation visible.",
                "done_evidence": self.done_evidence("S1"),
            },
            action_id=final_action,
            label="pending-final-verify",
        )
        self.assertEqual(self.state()["stage"], "post-inner")

        # A generic post-inner candidate cannot bypass its own two-pass review;
        # applying this no-change candidate later rejects the unresolved
        # obligation, then repair restarts the normal inner loop.
        no_change = {
            "summary": "No broader revision is proposed.",
            "plan_decision": "no-change",
            "plan_reason": "The original plan is unchanged.",
            "journal": [],
        }
        self.converge_objective(
            no_change,
            label="post-inner",
            final_code=2,
        )
        self.assertIn("pending carry-forward obligations", self.last_objective_final.stderr)
        self.repair_rejected_post_inner_objective("S1", label="pending", defect=True)
        self.rerun_inner_after_post_inner_repair("S1", label="pending")

        unchanged = self.initial_dag()
        base_revision = {
            "summary": "The pending concern needs a mapped plan revision.",
            "plan_decision": "revise",
            "plan_reason": "The pending correction belongs only in remaining work.",
            "plan": self.plan_markdown("\nPending correction remains explicit.\n"),
            "dag": unchanged,
            "journal": [],
        }
        revised = self.initial_dag()
        revised["steps"][1]["statement"] = (
            "Create the dependent artifact after the pending test-strategy correction"
        )
        revised["steps"][1]["contract"]["objective"] = revised["steps"][1][
            "statement"
        ]
        revised["steps"][1]["prompt"] += "\nApply the mapped pending correction."
        self.converge_objective(
            dict(
                base_revision,
                plan=self.plan_markdown("\nPending correction maps to changed S2.\n"),
                dag=revised,
                pending_obligation_map=[{"id": pending_id, "steps": ["S2"]}],
            ),
            label="post-inner",
        )
        self.assertEqual(self.state()["stage"], "merge")
        self.complete(
            {"summary": "Merge the converged step after its pending correction is scheduled."},
            label="pending-merge",
        )
        self.assertEqual(
            (self.state()["active_step"], self.state()["stage"]), ("S2", "step-plan")
        )
        s2_knowledge = self.cli(
            "context", "--section", "knowledge", "--offset", "0", "--limit", "8000"
        ).stdout
        self.assertIn(pending_id, s2_knowledge)
        self.assertIn("scheduled", s2_knowledge)

        self.converge_step_plan("S2")
        self.start_step("S2", exercise_failed_and_stale=False)
        paused = self.run_improve_iteration(
            "S2", material=False, stop_at_carry_forward=True
        )
        pause_id = "K-PAUSE-001"
        self.complete(
            self.carry_forward_payload(
                learnings="The unresolved fixture contract concern requires an explicit pause.",
                discoveries=[
                    self.discovery(
                        observation="The fixture cannot silently change its frozen contract.",
                        disposition="pause",
                        identifier=pause_id,
                        scope=["all"],
                    )
                ],
            ),
            action_id=paused["carry_action"],
            label="pause-checkpoint",
        )
        self.assertTrue(self.state().get("paused"))
        self.assertEqual(self.state()["stage"], "carry-forward")
        self.cli("resume")
        self.assertFalse(self.state().get("paused"))
        rejected, _ = self.complete(
            self.carry_forward_payload(
                learnings="Resume alone must not clear the durable carry-forward blocker."
            ),
            code=2,
            label="resume-bypass",
        )
        self.assertIn("unresolved carry-forward blocker", rejected.stderr)
        resolution_learning = "The pause was clarified without changing the frozen contract."
        self.complete(
            self.carry_forward_payload(
                learnings=resolution_learning,
                resolutions=[
                    {
                        "id": pause_id,
                        "decision": "no-contract-change",
                        "evidence": "checks/fixture-exact-output.md",
                        "reason": "The existing contract remains authoritative.",
                    }
                ],
            ),
            label="pause-safe-resolution",
        )
        self.assertEqual(self.state()["stage"], "commit")
        self.commit_checkpoint(
            "S2", paused, resolution_learning, label="pause-resolution-primary"
        )

    def test_research_obligation_requires_a_transitively_ordered_research_step(self):
        self.bootstrap_to_first_implementation()
        self.start_step("S1", exercise_failed_and_stale=False)
        obligation_id = "K-RESEARCH-PENDING-001"
        self.run_improve_iteration(
            "S1",
            material=False,
            carry_payload=self.carry_forward_payload(
                learnings="A later consumer needs a durable local research report before implementation.",
                discoveries=[
                    self.discovery(
                        observation="The remaining consumer depends on a local research report.",
                        disposition="pending-replan",
                        identifier=obligation_id,
                        scope=["S2"],
                        domain="research",
                    )
                ],
            ),
        )
        self.run_improve_iteration("S1", material=False)
        final_action = self.action_id()
        self.verify_current(self.manifest_for("S1"), label="research-obligation-final-checks")
        self.complete(
            {
                "summary": "Fresh final checks preserve the research obligation.",
                "done_evidence": self.done_evidence("S1"),
            },
            action_id=final_action,
            label="research-obligation-final-verify",
        )
        self.assertEqual(self.state()["stage"], "post-inner")

        base = {
            "summary": "The pending research finding needs a producer before the affected consumer.",
            "plan_decision": "revise",
            "plan_reason": "A report producer must precede the consumer that relies on it.",
            "plan": self.plan_markdown("\nA research producer precedes S2.\n"),
            "journal": [],
            "pending_obligation_map": [{"id": obligation_id, "steps": ["S3"]}],
        }
        unordered = self.initial_dag()
        unordered["steps"].append(
            self.step(
                "S3",
                self.product_research,
                [{"need": self.product_one, "from": "S1"}],
                "Produce the local research report required by the remaining consumer",
                activity="research",
            )
        )
        self.converge_objective(
            dict(base, dag=unordered),
            label="post-inner",
            final_code=2,
        )
        self.assertIn("transitively depend", self.last_objective_final.stderr)
        self.repair_rejected_post_inner_objective("S1", label="research-obligation")
        self.rerun_inner_after_post_inner_repair("S1", label="research-obligation")

        ordered = self.initial_dag()
        research_step = self.step(
            "S3",
            self.product_research,
            [{"need": self.product_one, "from": "S1"}],
            "Produce the local research report required by the remaining consumer",
            activity="research",
        )
        consumer = ordered["steps"][1]
        consumer["inputs"].append(
            {"need": self.product_research, "from": "S3"}
        )
        consumer["statement"] = (
            "Create the dependent verified artifact after consuming the research report"
        )
        consumer["contract"]["objective"] = consumer["statement"]
        consumer["prompt"] += "\nUse the durable S3 research report before implementation."
        ordered["steps"] = [ordered["steps"][0], research_step, consumer]
        post_inner_action = self.action_id()
        _, ordered_result = self.complete(
            dict(base, dag=ordered),
            label="research-obligation-ordered-consumer",
        )
        self.assertEqual(self.state()["stage"], "objective-review")
        self.converge_objective(
            dict(base, dag=ordered),
            label="post-inner",
            started=True,
        )
        self.assertEqual(self.state()["stage"], "merge")
        state_after_mapping = (self.run_dir / "state.md").read_bytes()
        self.cli("complete", "--action", post_inner_action, "--result", ordered_result)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), state_after_mapping)
        self.complete(
            {"summary": "Merge S1 after scheduling the required research producer."},
            label="research-obligation-merge",
        )
        self.assertEqual(
            (self.state()["active_step"], self.state()["stage"]), ("S3", "step-plan")
        )
        self.assertIn(
            obligation_id,
            self.cli(
                "context", "--section", "knowledge", "--offset", "0", "--limit", "8000"
            ).stdout,
        )

        self.converge_step_plan("S3")
        self.finish_step("S3", exercise_failure=False)
        research_cycle = self.receipt("S3")["improve_cycles"][0]
        self.assertEqual(set(research_cycle["review"]["research_review"]), set(self.research_rubric))
        self.assertEqual(
            (self.state()["active_step"], self.state()["stage"]), ("S2", "implement")
        )
        next_plan = ACTION.store.read_record(self.run_dir / "backchain" / "plan.md")
        s2 = next(step for step in next_plan["steps"] if step["id"] == "S2")
        self.assertIn({"need": self.product_research, "from": "S3"}, s2["inputs"])

    def test_legacy_commit_and_finalization_require_explicit_repair(self):
        self.bootstrap_to_first_implementation()
        self.start_step("S1", exercise_failed_and_stale=False)
        checkpoint = self.run_improve_iteration(
            "S1", material=False, stop_at_carry_forward=True
        )
        learning = "The legacy fixture has one explicit carry-forward checkpoint."
        self.complete(
            self.carry_forward_payload(learnings=learning),
            action_id=checkpoint["carry_action"],
            label="legacy-precondition-carry",
        )
        self.assertEqual(self.state()["stage"], "commit")

        # Simulate an older Markdown run that reached a commit/finalization
        # action before the carry-forward protocol existed.  The CLI must not
        # manufacture missing evidence; repair is the only forward path.
        legacy = self.state()
        for key in (
            "carry_forward_protocol_version",
            "knowledge_revision",
            "knowledge_sha256",
            "knowledge_action_id",
        ):
            legacy.pop(key, None)
        ACTION.store.write_record(self.run_dir / "state.md", legacy)
        rejected, _ = self.complete(
            {
                "summary": "Attempt to certify a legacy commit without a checkpoint.",
                "commit": checkpoint["iteration"]["previous_sha"],
            },
            code=2,
            label="legacy-commit",
        )
        self.assertIn("carry-forward checkpoint required", rejected.stderr)
        self.assertIn("use repair", rejected.stderr)

        legacy = ACTION.store.read_record(self.run_dir / "state.md")
        legacy.update(phase="implement", stage="final-verify")
        legacy["action"]["stage"] = "final-verify"
        ACTION.store.write_record(self.run_dir / "state.md", legacy)
        rejected, _ = self.complete(
            {"summary": "Attempt to finalize legacy work without a checkpoint."},
            code=2,
            label="legacy-final-verify",
        )
        self.assertIn("carry-forward checkpoint required", rejected.stderr)

        final_action = self.action_id()
        rejected = self.cli(
            "repair",
            "--action",
            final_action,
            "--reason",
            "Refuse to overwrite unbound carry-forward recovery data.",
            code=2,
        )
        self.assertIn("unbound carry-forward knowledge artifacts", rejected.stderr)
        # A genuine pre-carry-forward run has no overlay artifacts.  Remove the
        # exact test-only artifacts after proving the preservation guard, then
        # exercise repair's safe old-run bootstrap path.
        for name in ("knowledge.md", "knowledge-history", "knowledge-reads"):
            path = self.run_dir / name
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                for child in sorted(
                    path.rglob("*"), key=lambda item: len(item.parts), reverse=True
                ):
                    if child.is_file():
                        child.unlink()
                    else:
                        child.rmdir()
                path.rmdir()
        self.cli(
            "repair",
            "--action",
            final_action,
            "--reason",
            "Restart the legacy finalization under an explicit knowledge ledger.",
        )
        repaired = self.state()
        self.assertEqual(repaired["stage"], "review")
        self.assertEqual(repaired["carry_forward_protocol_version"], 1)
        self.assertTrue((self.run_dir / "knowledge.md").is_file())


if __name__ == "__main__":
    unittest.main()
