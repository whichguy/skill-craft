#!/usr/bin/env python3
"""Repeatable real-Git code generation/aggregation lifecycle tests.

Run: python3 -B test/shiploop-chain-lifecycle.test.py
Workers are explicitly deterministic Python processes, not native/model agents.
Native Ask-Agent qualification uses experiments/shiploop_chain/native_pilot.py.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

from shiploop_chain_lifecycle_support import CHAIN_MODULES, PerStepChainFixture
import shiploop_chain_support as fixture


class PerStepChainTests(PerStepChainFixture):
    def test_strict_verifier_requires_every_expected_module(self):
        workspace = self.f.base / "strict-verifier"
        workspace.mkdir()
        for step in ("A", "B", "C"):
            module = CHAIN_MODULES[step]
            (workspace / module["path"]).write_text(module["source"])
        self.verify(workspace, expected_steps=("A", "B", "C"))
        with self.assertRaisesRegex(AssertionError, "chain_report.py"):
            self.verify(workspace, expected_steps=("A", "B", "C", "J"))

    def assert_claim_precedes_pending_attempt(self, response, step, attempt):
        actions = response["navigation"]["actions"]
        claim_index = next(index for index, action in enumerate(actions)
                           if action["action"] == "claim" and action["steps"] == [step])
        pending_indexes = [index for index, action in enumerate(actions)
                           if action.get("attempt") == attempt
                           and action["action"] in {"collect", "prepare", "verify"}]
        self.assertTrue(pending_indexes, "fixture needs a pending sibling observation")
        self.assertLess(claim_index, min(pending_indexes),
                        "a completion must refill ready work before waiting on a sibling")

    def exercise_parallel_completion_order(self, order):
        self.assertIn(order, {"a-first", "b-first", "burst"})
        self.bind()
        attempts = self.claim("A", "B")
        self.start("A", attempts["A"])
        self.start("B", attempts["B"])
        a = self.launch("A")
        b = self.launch("B")
        self.assertIsNone(a.poll())
        self.assertIsNone(b.poll())

        if order == "a-first":
            self.collect("A", a)
            a_done = self.prepare_and_done("A")
            self.assertIsNone(b.poll(), "B must still execute after A releases C")
            self.assert_claim_precedes_pending_attempt(a_done, "C", attempts["B"])
            c_attempt = self.claim("C")["C"]
            self.start("C", c_attempt)
            c = self.launch("C")
            self.assertIsNone(b.poll(), "C must start while B is still executing")
            self.collect("B", b)
            self.prepare_and_done("B")
            self.assertNotIn("J", self.call("next")["ready"])
            self.collect("C", c)
            c_done = self.prepare_and_done("C")
            expected_order = (attempts["A"], attempts["B"], c_attempt)
        elif order == "b-first":
            self.collect("B", b)
            b_done = self.prepare_and_done("B")
            self.assertIsNone(a.poll(), "A must still execute after B returns first")
            self.assertNotIn("C", b_done["ready"])
            self.assertNotIn("J", b_done["ready"])
            self.collect("A", a)
            a_done = self.prepare_and_done("A")
            self.assertEqual([row["steps"] for row in self.action_rows(a_done, "claim")], [["C"]])
            c_attempt = self.claim("C")["C"]
            self.start("C", c_attempt)
            c = self.launch("C")
            self.assertNotIn("J", self.call("next")["ready"])
            self.collect("C", c)
            c_done = self.prepare_and_done("C")
            expected_order = (attempts["B"], attempts["A"], c_attempt)
        else:
            # Both fixture workers reach the deterministic release barrier and
            # return before the parent processes either completion event.
            a_result = self.finish_worker("A", a)
            b_result = self.finish_worker("B", b)
            self.import_finished("A", a_result)
            self.import_finished("B", b_result)
            a_done = self.prepare_and_done("A")
            self.assert_claim_precedes_pending_attempt(a_done, "C", attempts["B"])
            c_attempt = self.claim("C")["C"]
            self.start("C", c_attempt)
            c = self.launch("C")
            self.prepare_and_done("B")
            self.assertNotIn("J", self.call("next")["ready"])
            self.collect("C", c)
            c_done = self.prepare_and_done("C")
            expected_order = (attempts["A"], attempts["B"], c_attempt)

        self.assertEqual([row["steps"] for row in self.action_rows(c_done, "claim")], [["J"]])
        j_attempt = self.claim("J")["J"]
        self.start("J", j_attempt)
        self.complete_step("J")
        self.assert_contiguous_integrations((*expected_order, j_attempt))
        contributions = self.accepted_contributions()
        self.assertEqual({item["step"] for item in contributions}, {"A", "B", "C", "J"})
        self.verify(self.f.target, expected_steps=("A", "B", "C", "J"))
        self.finish()

    def test_parallel_completion_order_a_first_refills_while_b_runs(self):
        self.exercise_parallel_completion_order("a-first")

    def test_parallel_completion_order_b_first_waits_for_a_then_refills(self):
        self.exercise_parallel_completion_order("b-first")

    def test_parallel_completion_burst_refills_before_pending_verification(self):
        self.exercise_parallel_completion_order("burst")

    def test_late_retried_b_success_cannot_mutate_target_or_unlock_join(self):
        self.bind()
        attempts = self.claim("A", "B")
        self.start("A", attempts["A"])
        self.start("B", attempts["B"])
        old_worker = Path(self.packets["B"]["context"]["workspace"])
        a = self.launch("A")
        b = self.launch("B")

        self.collect("A", a)
        a_done = self.prepare_and_done("A")
        self.assert_claim_precedes_pending_attempt(a_done, "C", attempts["B"])
        c_attempt = self.claim("C")["C"]
        self.start("C", c_attempt)
        c = self.launch("C")

        self.collect("B", b)
        old_positive = self.prepared_input("B")
        old_source = self.source_commits["B"]
        rejection_proof = self.f.write("rejected-old-b.json", {
            "passed": False,
            "checks": ["fixture rejects the old B result before replacement"],
        })
        rejected = self.call("done", {
            "attempt": attempts["B"], "confirmed_stopped": True,
            "verification": {
                "receipt_sha256": old_positive["verification"]["receipt_sha256"],
                "passed": False,
                "reason": "Fixture rejects the old B result",
                "evidence": {"path": str(rejection_proof), "sha256": fixture.digest(rejection_proof)},
            },
        })
        self.assertEqual((rejected["outcome"], rejected["step"], rejected["attempt"]),
                         ("rejected", "B", attempts["B"]))
        self.assertNotIn("J", self.call("next")["ready"])
        self.call("retry", {"attempt": attempts["B"], "confirmed_stopped": True,
                              "reason": "Replacement B needs a fresh attempt"})

        replacement = self.claim("B")["B"]
        self.assertNotEqual(replacement, attempts["B"])
        self.start("B", replacement)
        replacement_worker = self.launch("B")

        self.collect("C", c)
        c_done = self.prepare_and_done("C")
        self.assertIsNone(replacement_worker.poll())
        self.assertNotIn("J", c_done["ready"])

        self.collect("B", replacement_worker)
        replacement_positive = self.prepared_input("B")
        replacement_source = self.source_commits["B"]
        self.assertNotEqual(old_source, replacement_source)

        def assert_rejected_without_mutation(value, phrase):
            before_head = self.head()
            before_child = self.f.child_state_path().read_bytes()
            before_ledger = self.f.ledger_bytes()
            before_worktrees = self.f.git(self.f.target, "worktree", "list", "--porcelain")
            before_paths = [Path(line.removeprefix("worktree "))
                            for line in before_worktrees.splitlines() if line.startswith("worktree ")]
            before_status = self.f.git(self.f.target, "status", "--porcelain")
            self.assertTrue(all(path.is_dir() for path in before_paths))
            refused = self.call("done", value, ok=False)
            self.assertIn(phrase, refused.stderr.lower())
            self.assertEqual(self.head(), before_head)
            self.assertEqual(self.f.child_state_path().read_bytes(), before_child)
            self.assertEqual(self.f.ledger_bytes(), before_ledger)
            self.assertEqual(self.f.git(self.f.target, "worktree", "list", "--porcelain"), before_worktrees)
            self.assertTrue(all(path.is_dir() for path in before_paths))
            self.assertEqual(self.f.git(self.f.target, "status", "--porcelain"), before_status)

        wrong_step = json.loads(json.dumps(replacement_positive))
        wrong_step["step"] = "A"
        assert_rejected_without_mutation(wrong_step, "step")
        assert_rejected_without_mutation(old_positive, "stale or retried")
        self.assertNotIn("J", self.call("next")["ready"])

        replacement_done = self.call("done", replacement_positive)
        self.assertEqual((replacement_done["outcome"], replacement_done["step"], replacement_done["attempt"]),
                         ("accepted", "B", replacement))
        self.verify(self.f.target, expected_steps=("A", "B", "C"))
        self.assertIn("J", replacement_done["ready"])
        replacement_cleanup = self.run_deferred_managed_cleanup("B", replacement_done)
        self.assertIsNotNone(replacement_cleanup)
        self.assertFalse(replacement_cleanup["pending"])

        assert_rejected_without_mutation(old_positive, "stale or retried")
        self.assertIn("J", self.call("next")["ready"])
        old_ancestry = subprocess.run(["git", "merge-base", "--is-ancestor", old_source, self.head()],
                                      cwd=self.f.target, capture_output=True, timeout=15)
        self.assertNotEqual(old_ancestry.returncode, 0)

        retained = self.call("cleanup", {"attempt": attempts["B"], "confirmed_stopped": True,
                                          "disposition": "superseded",
                                          "reason": "Replacement B was accepted and integrated"}, ok=False)
        self.assertRegex(retained.stderr.lower(), r"retain|managed|superseded")
        self.assertTrue(old_worker.exists())
        j_attempt = self.claim("J")["J"]
        self.start("J", j_attempt)
        self.complete_step("J")
        self.assert_contiguous_integrations((attempts["A"], c_attempt, replacement, j_attempt))
        proof = self.f.write("late-retried-b-finish.json", {"passed": True, "commit": self.head()})
        blocked = self.call("finish", {
            "commit": self.head(), "confirmed_stopped": True,
            "verification": {"path": str(proof), "sha256": fixture.digest(proof)},
        }, ok=False)
        self.assertRegex(blocked.stderr.lower(), r"retain|cleanup|unfinished|managed")

        def remove_retained_workspace():
            if old_worker.exists():
                self.f.git(self.f.target, "worktree", "remove", "--force", str(old_worker))

        self.addCleanup(remove_retained_workspace)

    def test_parallel_code_fanout_eager_dependent_join_merges_and_removes_all_workers(self):
        trace = []
        bound = self.bind()
        trace.append(("bind", bound))
        initial_claim = self.action_rows(bound, "claim")
        self.assertEqual(len(initial_claim), 1)
        self.assertEqual(initial_claim[0]["steps"], ["A", "B"])
        self.assertEqual(initial_claim[0]["max_steps"], 2)
        self.execute_next_from_unrelated_cwd(bound)
        claims = self.claim("A", "B")
        trace.append(("claim A,B", self.last_claim_response))
        self.assertFalse(self.action_rows(self.last_claim_response, "claim"),
                         "full capacity must suppress another claim grant")
        self.start("A", claims["A"])
        self.assertEqual([row["attempt"] for row in self.action_rows(self.last_start_response, "launch")],
                         [claims["A"]])
        self.assertFalse(self.action_rows(self.last_packet_response, "launch"),
                         "a packet view must not grant a second native launch")
        self.start("B", claims["B"])
        self.assertEqual([row["attempt"] for row in self.action_rows(self.last_start_response, "launch")],
                         [claims["B"]])
        before_replayed_start = self.f.git(self.f.target, "worktree", "list", "--porcelain")
        replayed_start = self.call("start", self.start_inputs["B"])
        self.assertEqual(replayed_start["action"], "reconcile")
        self.assertEqual(replayed_start["packet"], self.packets["B"])
        self.assertEqual(self.f.git(self.f.target, "worktree", "list", "--porcelain"), before_replayed_start)
        recovered = self.call("recover")
        self.assertFalse(self.action_rows(recovered, "launch"),
                         "cold recovery must not grant a fresh native launch")
        self.assertTrue(recovered["navigation"]["actions"])
        self.assertTrue(all(row["action"] == "collect" for row in recovered["navigation"]["actions"]))
        self.assertIn("await any native completion", recovered["navigation"]["instruction"].lower())
        a, b = self.launch("A"), self.launch("B")
        self.assertIsNone(a.poll())
        self.assertIsNone(b.poll())
        self.collect("A", a)
        result = self.prepare_and_done("A")
        trace.append(("done A", result))
        self.assertIn("C", result["ready"])
        self.assertNotIn("J", result["ready"])
        self.assertIsNone(b.poll(), "B must still run when C is released")
        result_actions = result["navigation"]["actions"]
        c_claim_index = next(index for index, row in enumerate(result_actions)
                             if row["action"] == "claim" and row["steps"] == ["C"])
        b_collect_index = next(index for index, row in enumerate(result_actions)
                               if row["action"] == "collect" and row["attempt"] == claims["B"])
        self.assertLess(c_claim_index, b_collect_index,
                        "eligible C must be claimed before the caller is told to await B")
        before_head = self.head()
        before_child = self.f.child_state_path().read_bytes()
        premature = self.call("claim", {"steps": ["J"]}, ok=False)
        self.assertNotEqual(premature.returncode, 0)
        self.assertEqual(self.head(), before_head)
        self.assertEqual(self.f.child_state_path().read_bytes(), before_child)
        c_attempt = self.claim("C")["C"]
        archived = Path(self.imports["A"]["archives"][0]["archived_path"])
        original = archived.read_bytes()
        archived.chmod(0o644)
        archived.write_text("corrupted supplier evidence\n")
        archived.chmod(0o444)
        before = self.f.git(self.f.target, "worktree", "list", "--porcelain")
        refused = self.call("start", self.f.start_value("C", c_attempt, base=self.head()), ok=False)
        self.assertTrue(any(word in refused.stderr.lower() for word in ("archive", "digest")), refused.stderr)
        self.assertEqual(self.f.git(self.f.target, "worktree", "list", "--porcelain"), before)
        archived.chmod(0o644)
        archived.write_bytes(original)
        archived.chmod(0o444)
        self.start("C", c_attempt)
        self.assertEqual(self.packets["C"]["context"]["base_commit"], self.head())
        c = self.launch("C")
        self.assertIsNone(b.poll())
        self.assertIsNone(c.poll())
        self.collect("B", b)
        b_done = self.prepare_and_done("B")
        trace.append(("done B while C active", b_done))
        self.assertFalse(any(row["action"] == "claim" and "J" in row.get("steps", [])
                             for row in b_done["navigation"]["actions"]))
        self.assertNotIn("J", self.call("next")["ready"])
        self.collect("C", c)
        c_done = self.prepare_and_done("C")
        trace.append(("done C", c_done))
        self.assertEqual([row["steps"] for row in self.action_rows(c_done, "claim")], [["J"]])
        self.start("J", self.claim("J")["J"])
        j_done = self.complete_step("J")
        trace.append(("done J", j_done))
        self.assertTrue(j_done["complete"], "top-level completion remains the child graph compatibility view")
        self.assertFalse(j_done["navigation"]["complete"],
                         "the parent return remains blocked until the durable finish receipt")
        self.assertEqual([row["action"] for row in j_done["navigation"]["actions"]], ["cleanup"])
        ready_to_finish = self.call("next")
        self.assertEqual([row["action"] for row in ready_to_finish["navigation"]["actions"]], ["finish"])
        finished = self.finish()
        trace.append(("finish", finished))
        self.assertTrue(finished["navigation"]["complete"])
        self.assertEqual([row["action"] for row in finished["navigation"]["actions"]], ["return-parent"])
        self.execute_parent_next_from_unrelated_cwd(finished)
        trace_path = self.retain_navigation_trace(trace)
        self.assertTrue(trace_path.is_file())
        # All predecessor workspaces are gone; imports and graph views remain usable.
        replay = self.call("done", self.done_inputs["A"])
        self.assertEqual(replay["outcome"], "accepted")
        self.assertEqual((replay["step"], replay["attempt"]), ("A", claims["A"]))
        self.assertEqual(len(self.f.terminal_events(claims["A"])), 1)
        self.call("history")
        self.call("recover")

    def test_navigation_advertises_full_ready_frontier_with_capacity_bound(self):
        bound = self.bind(capacity=1)
        claims = self.action_rows(bound, "claim")
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0]["steps"], ["A", "B"])
        self.assertEqual(claims[0]["max_steps"], 1)
        self.assertEqual(claims[0]["operation"], "claim")
        self.assertIn("every safe listed candidate", claims[0]["instruction"])
        attempt = self.claim("A")["A"]
        start = self.action_rows(self.call("next"), "start")[0]
        self.assertEqual(start["attempt"], attempt)
        self.assertIn("selected Ask-Agent helper", start["instruction"])
        self.assertIn("do not supply a workspace", start["instruction"])
        self.assertNotIn("prepare-workspace", start["instruction"])

    def test_ready_claim_precedes_unknown_native_reconciliation(self):
        self.bind(capacity=2)
        claimed = self.call("claim", {"steps": ["A"]})
        attempt = claimed["claims"][0]["attempt"]
        claim_actions = claimed["navigation"]["actions"]
        start_index = next(index for index, row in enumerate(claim_actions) if row["action"] == "start")
        next_claim_index = next(index for index, row in enumerate(claim_actions) if row["action"] == "claim")
        self.assertLess(start_index, next_claim_index,
                        "an already-reserved start must precede a new ready claim")
        self.start("A", attempt, record_launch=False)
        start_actions = self.last_start_response["navigation"]["actions"]
        launch_index = next(index for index, row in enumerate(start_actions) if row["action"] == "launch")
        claim_index = next(index for index, row in enumerate(start_actions) if row["action"] == "claim")
        self.assertLess(launch_index, claim_index,
                        "an already-reserved start must precede a new ready claim")
        next_response = self.call("next")
        actions = next_response["navigation"]["actions"]
        claim_index = next(index for index, row in enumerate(actions) if row["action"] == "claim")
        reconcile_index = next(index for index, row in enumerate(actions) if row["action"] == "reconcile")
        self.assertLess(claim_index, reconcile_index)
        claim = actions[claim_index]
        self.assertEqual(claim["steps"], ["B"])
        self.assertEqual(claim["max_steps"], 1)

    def test_ready_claim_precedes_preparation_and_verification(self):
        self.bind(capacity=2)
        self.start("A", self.claim("A")["A"])
        self.collect("A", self.launch("A"))
        preparing = self.call("next")["navigation"]["actions"]
        self.assertEqual([row["action"] for row in preparing], ["claim", "prepare"])
        self.assertEqual(preparing[0]["steps"], ["B"])
        self.prepared_input("A")
        verifying = self.call("next")["navigation"]["actions"]
        self.assertEqual([row["action"] for row in verifying], ["claim", "verify"])
        self.assertEqual(verifying[0]["steps"], ["B"])

    def test_navigation_paused_parent_grants_resume_only(self):
        self.bind()
        paused = subprocess.run([sys.executable, "-B", str(fixture.CLI), "pause",
                                 "--run-dir", str(self.f.run), "--reason", "navigation fixture pause"],
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(paused.returncode, 0, paused.stderr + paused.stdout)
        next_response = self.call("next")
        self.assertEqual([row["action"] for row in next_response["navigation"]["actions"]],
                         ["resume-parent"])
        self.assertFalse(any("operation" in row for row in next_response["navigation"]["actions"]))

    def test_navigation_owner_takeover_is_blocked_without_callback(self):
        self.bind()
        self.takeover()
        next_response = self.call("next")
        self.assertEqual([row["action"] for row in next_response["navigation"]["actions"]], ["blocked"])
        self.assertFalse(any("operation" in row for row in next_response["navigation"]["actions"]))

    def test_serial_code_graph_uses_same_integration_and_cleanup_without_native_handles(self):
        self.bind(mode="serial")
        for step in ("A", "B", "C", "J"):
            attempt = self.claim(step)[step]
            start = self.action_rows(self.call("next"), "start")[0]
            self.assertIn("main-context", start["instruction"])
            self.assertIn("Ask-Agent", start["instruction"])
            self.start(step, attempt, serial=True)
            allocation = fixture.chain._per_step_allocation(self.bridge_events(), attempt)
            self.assertEqual(allocation["adoption"], "ask-agent-managed-workspace")
            self.assertIn("ask_agent_workspace", allocation)
            self.assertEqual(allocation["plan"]["path"], self.packets[step]["context"]["workspace"])
            self.complete_step(step)
            self.assertIsNone(self.f.child_record(attempt).get("handle"))
        self.finish()

    def test_serial_managed_preparation_crash_recovers_exact_helper_workspace(self):
        self.bind(mode="serial", single=True)
        attempt = self.claim("A")["A"]
        value = self.f.start_value("A", attempt, base=self.head())
        value["write_scope"] = ["chain_add.py"]
        original = fixture.chain._append

        def crash_before_allocation_receipt(chain_dir, event_id, kind, data, **kwargs):
            if kind == "managed_workspace_preparation_result":
                raise OSError("fixture interruption after helper workspace preparation")
            return original(chain_dir, event_id, kind, data, **kwargs)

        with patch.object(fixture.chain, "_append", side_effect=crash_before_allocation_receipt):
            with self.assertRaises(OSError):
                fixture.chain._per_step_start(self.f.run, self.binding(), value)
        events = self.bridge_events()
        prepared = [row["event"]["data"] for row in events
                    if row["event"]["kind"] == "managed_workspace_preparation_intent"]
        self.assertEqual(len(prepared), 1)
        self.assertFalse(any(row["event"]["kind"] == "managed_workspace_preparation_result"
                             for row in events))
        self.assertEqual(self.f.child_record(attempt)["status"], "claimed")

        output = self.call("start", value)
        self.assertEqual(output["action"], "execute")
        self.packets["A"] = output["packet"]
        allocation = fixture.chain._per_step_allocation(self.bridge_events(), attempt)
        self.assertEqual(allocation["adoption"], "ask-agent-managed-workspace")
        workspace = Path(allocation["plan"]["path"])
        self.assertTrue(workspace.exists())
        self.assertEqual(allocation["plan"]["path"], output["packet"]["context"]["workspace"])
        kinds = [row["event"]["kind"] for row in self.bridge_events()]
        self.assertEqual(kinds.count("managed_workspace_preparation_intent"), 1)
        self.assertEqual(kinds.count("managed_workspace_preparation_result"), 1)
        self.complete_step("A")
        self.finish()

    def test_managed_capability_contract_freezes_selected_helper_delivers_complete_range_and_closes(self):
        graph = json.loads(self.f.graph.read_text())
        graph["steps"] = graph["steps"][:2]
        self.f.graph.write_text(json.dumps(graph) + "\n")
        self.managed_bind(capacity=2)
        binding = self.binding()
        declared = self.managed_capabilities()
        self.assertEqual(binding["schema"], "shiploop-chain-binding/v6")
        self.assertEqual(set(declared), {"schema", "version", "capabilities"})
        self.assertEqual(declared["schema"], "shiploop-chain-ask-agent-managed-worktree/v1")
        self.assertEqual(binding["ask_agent_contract"], declared)
        self.assertTrue({
            "helper-managed-worktree", "prepared-inspection", "returned-commit-delivery",
            "fingerprint-bound-close",
        } <= set(declared["capabilities"]))
        self.assertEqual(set(binding["ask_agent"]["files"]), {
            "SKILL.md", "scripts/ask_agent_workspace.py", "references/git-integration.md",
            "references/workspace-operations.md", "references/native-lifecycle.md",
            "references/result-handoff.md",
        })
        identity = binding["ask_agent_identity"]
        self.assertEqual(identity["method"], "helper-v1")
        self.assertEqual(identity["logical_skill_card"], str(self.f.ask / "SKILL.md"))
        self.assertEqual(identity["resolved_helper"],
                         binding["ask_agent"]["files"]["scripts/ask_agent_workspace.py"]["path"])

        attempts = self.claim("A", "B")
        start_actions = self.action_rows(self.call("next"), "start")
        self.assertEqual({row["attempt"] for row in start_actions}, set(attempts.values()))
        for start in start_actions:
            self.assertIn("selected Ask-Agent helper", start["instruction"])
            self.assertIn("do not supply a workspace", start["instruction"])
            self.assertIn("launch", start["instruction"])
            self.assertNotIn("prepare-workspace", start["instruction"])
            self.assertNotIn("Ask-Agent workspace when already prepared", start["required"])
        base = self.head()
        packet = self.managed_start("A", attempts["A"], base=base)
        b_packet = self.managed_start("B", attempts["B"], base=base)
        self.assertEqual((packet["context"]["base_commit"], b_packet["context"]["base_commit"]),
                         (base, base))
        checked = self.managed_context_check("A")
        self.assertEqual(checked["actual_cwd"], packet["context"]["workspace"])
        self.assertEqual(self.managed_context_check("B")["actual_cwd"],
                         b_packet["context"]["workspace"])

        b_result = self.managed_worker_result("B")
        self.import_finished("B", b_result)
        b_accepted = self.prepare_and_done("B")

        attempt = attempts["A"]
        result = self.managed_worker_result("A", commits=2)
        self.import_finished("A", result)
        archived_handoff = Path(self.imports["A"]["archives"][0]["archived_path"])
        archived_handoff_bytes = archived_handoff.read_bytes()
        self.assertTrue(archived_handoff.is_file())
        self.assertFalse(Path(result["handoff"]).exists(),
                         "the parent import must remove the untracked handoff before W/T/I")
        self.assertTrue(any(row["event"]["kind"] == "handoff_files_removed"
                            for row in self.bridge_events()))
        returned = next(row["event"]["data"] for row in self.bridge_events()
                        if row["event"]["kind"] == "managed_returned_delivery"
                        and row["event"]["data"].get("attempt") == attempt)
        self.assertEqual(returned["intent"], {
            "attempt": attempt, "source_commit": result["commit"],
            "base_commit": packet["context"]["base_commit"],
            "receipt": packet["ask_agent_workspace"]["receipt"],
            "receipt_sha256": packet["ask_agent_workspace"]["receipt_sha256"],
            "workspace": packet["context"]["workspace"],
            "discard": [".shiploop-handoff/" + attempt],
        })
        self.assertEqual(returned["delivery"]["commits"], result["commits"])
        self.assertEqual(returned["delivery"]["source_commit"], result["commit"])
        self.assertEqual(returned["delivery"]["workspace"], packet["context"]["workspace"])
        self.assertIn("delivery", returned["delivery"]["evidence"])

        accepted = self.prepare_and_done("A")
        integration = self.done_inputs["A"]["integration"]
        self.assertEqual(self.head(), integration["candidate_commit"])
        self.assertNotEqual(integration["candidate_commit"], result["commit"])
        parents = self.f.git(self.f.target, "show", "-s", "--format=%P", integration["candidate_commit"]).split()
        self.assertEqual(len(parents), 2, "the worker range must be integrated through a distinct I merge")
        self.assertEqual(set(parents), {
            self.done_inputs["B"]["integration"]["candidate_commit"], result["commit"],
        }, "A's I merge must retain both B's advanced target and A's returned worker range")
        self.f.git(self.f.target, "merge-base", "--is-ancestor", b_result["commit"], integration["candidate_commit"])
        self.f.git(self.f.target, "merge-base", "--is-ancestor", result["commit"], integration["candidate_commit"])
        self.assertEqual(b_accepted["outcome"], "accepted")
        self.assertEqual(accepted["outcome"], "accepted")
        self.assertFalse(Path(packet["context"]["workspace"]).exists())
        self.assertEqual(archived_handoff.read_bytes(), archived_handoff_bytes,
                         "parent archive remains the durable handoff after helper-owned cleanup")
        self.finish()

    def test_managed_parallel_a_first_refills_c_before_b_finishes(self):
        self.managed_bind(capacity=2)
        attempts = self.claim("A", "B")
        t0 = self.head()
        a_packet = self.managed_start("A", attempts["A"], base=t0)
        b_packet = self.managed_start("B", attempts["B"], base=t0)
        self.assertEqual((a_packet["context"]["base_commit"], b_packet["context"]["base_commit"]),
                         (t0, t0))
        b = self.launch("B")
        self.assertIsNone(b.poll())

        self.managed_context_check("A")
        self.import_finished("A", self.managed_worker_result("A"))
        a_done = self.prepare_and_done("A", close_deferred=False)
        a_workspace = Path(a_packet["context"]["workspace"])
        a_integration = self.done_inputs["A"]["integration"]["candidate_commit"]
        self.assertEqual(a_done["cleanup"], {
            "attempt": attempts["A"], "cleanup": None, "pending": True, "deferred": True,
        })
        self.assertTrue(a_workspace.exists())
        self.assertIn(attempts["A"], self.call("pending")["lifecycle"]["cleanup_pending"])
        self.assertIsNone(b.poll(), "B must remain live when A releases C")
        self.assert_claim_precedes_pending_attempt(a_done, "C", attempts["B"])

        c_attempt = self.claim("C")["C"]
        c_packet = self.managed_start("C", c_attempt, base=self.head())
        self.assertEqual(c_packet["context"]["base_commit"], a_integration)
        self.assertEqual([item["step"] for item in c_packet["dependencies"]], ["A"])
        c = self.launch("C")
        self.assertIsNone(b.poll(), "C must start before B finishes")
        self.assertIsNone(c.poll())

        self.collect("B", b)
        self.prepare_and_done("B")
        self.assertIsNone(c.poll(), "C must remain live while B is integrated")
        self.collect("C", c)
        c_done = self.prepare_and_done("C")
        self.assertEqual([row["steps"] for row in self.action_rows(c_done, "claim")], [["J"]])
        self.assertTrue(a_workspace.exists())
        self.assertNotEqual(self.head(), a_integration,
                            "B and C must advance T after A was accepted")

        before_a_cleanup = self.head()
        a_cleanup = self.call("cleanup", {"attempt": attempts["A"], "confirmed_stopped": True})
        self.assertFalse(a_cleanup["pending"])
        self.assertFalse(a_workspace.exists())
        self.assertEqual(self.head(), before_a_cleanup,
                         "closing an unchanged accepted A workspace must not move the target")

        j_attempt = self.claim("J")["J"]
        self.managed_start("J", j_attempt, base=self.head())
        self.import_finished("J", self.managed_worker_result("J"))
        self.prepare_and_done("J")
        self.assert_contiguous_integrations((attempts["A"], attempts["B"], c_attempt, j_attempt))
        self.verify(self.f.target, expected_steps=("A", "B", "C", "J"))
        self.finish()

    def test_managed_parallel_b_stale_t0_candidate_reprepares_at_t1(self):
        self.managed_bind(capacity=2)
        attempts = self.claim("A", "B")
        t0 = self.head()
        a_packet = self.managed_start("A", attempts["A"], base=t0)
        b_packet = self.managed_start("B", attempts["B"], base=t0)
        self.assertEqual((a_packet["context"]["base_commit"], b_packet["context"]["base_commit"]),
                         (t0, t0))

        self.managed_context_check("B")
        self.import_finished("B", self.managed_worker_result("B"))
        stale_b = self.prepared_input("B")
        self.assertEqual(stale_b["integration"]["expected_target"], t0)

        self.managed_context_check("A")
        self.import_finished("A", self.managed_worker_result("A"))
        self.prepare_and_done("A")
        t1 = self.head()
        self.assertNotEqual(t1, t0)

        before_head = self.head()
        before_child = self.f.child_state_path().read_bytes()
        before_ledger = self.f.ledger_bytes()
        refused = self.call("done", stale_b, ok=False)
        self.assertTrue(any(word in refused.stderr.lower() for word in ("target", "stale", "head")),
                        refused.stderr)
        self.assertEqual(self.head(), before_head)
        self.assertEqual(self.f.child_state_path().read_bytes(), before_child)
        self.assertEqual(self.f.ledger_bytes(), before_ledger)
        self.assertTrue(Path(b_packet["context"]["workspace"]).exists())

        reprepared_b = self.prepared_input("B")
        self.assertEqual(reprepared_b["integration"]["expected_target"], t1)
        self.assertNotEqual(reprepared_b["integration"]["candidate_commit"],
                            stale_b["integration"]["candidate_commit"])
        self.verify(Path(b_packet["context"]["workspace"]), expected_steps=("A", "B"))
        b_done = self.call("done", reprepared_b)
        self.assertEqual(b_done["outcome"], "accepted")
        b_cleanup = self.run_deferred_managed_cleanup("B", b_done)
        self.assertIsNotNone(b_cleanup)
        self.assertFalse(b_cleanup["pending"])

        c_attempt = self.claim("C")["C"]
        self.managed_start("C", c_attempt, base=self.head())
        self.import_finished("C", self.managed_worker_result("C"))
        self.prepare_and_done("C")
        j_attempt = self.claim("J")["J"]
        self.managed_start("J", j_attempt, base=self.head())
        self.import_finished("J", self.managed_worker_result("J"))
        self.prepare_and_done("J")
        self.assert_contiguous_integrations((attempts["A"], attempts["B"], c_attempt, j_attempt))
        self.verify(self.f.target, expected_steps=("A", "B", "C", "J"))
        self.finish()

    def test_managed_retried_attempt_fences_late_receipt_replay(self):
        self.managed_bind(single=True)
        old_attempt = self.claim("A")["A"]
        old_packet = self.managed_start("A", old_attempt)
        old_workspace = Path(old_packet["context"]["workspace"])

        def remove_old_workspace():
            if old_workspace.exists():
                self.f.git(self.f.target, "worktree", "remove", "--force", str(old_workspace))

        self.addCleanup(remove_old_workspace)
        self.managed_context_check("A")
        old_result = self.managed_worker_result("A")
        old_request = {
            "attempt": old_attempt,
            "confirmed_stopped": True,
            "handoff": {"path": old_result["handoff"], "sha256": old_result["sha256"]},
        }
        imported = self.import_finished("A", old_result)
        before_duplicate = self.f.ledger_bytes()
        duplicate = self.call("import-handoff", old_request)
        self.assertEqual(duplicate["import"], imported["import"])
        self.assertEqual(self.f.ledger_bytes(), before_duplicate)
        old_positive = self.prepared_input("A")
        receipt = fixture.chain._node(self.binding(), "receipt", {"attempt": old_attempt})
        rejection_proof = self.f.write("managed-retried-old.json", {
            "passed": False, "checks": ["fixture rejects the old receipt before retry"],
        })
        rejected = self.call("done", {
            "attempt": old_attempt,
            "confirmed_stopped": True,
            "verification": {
                "receipt_sha256": receipt["sha256"], "passed": False,
                "reason": "Fixture retires the old managed attempt",
                "evidence": {"path": str(rejection_proof), "sha256": fixture.digest(rejection_proof)},
            },
        })
        self.assertEqual(rejected["outcome"], "rejected")
        retrying = self.call("retry", {"attempt": old_attempt, "confirmed_stopped": True,
                                      "reason": "Replacement managed attempt is required"})
        blocked = self.action_rows(retrying, "blocked")
        self.assertEqual([row["attempt"] for row in blocked], [old_attempt])
        self.assertNotIn("operation", blocked[0])
        self.assertTrue(self.action_rows(retrying, "claim"),
                        "retaining the failed worker must not hide the ready replacement")
        self.assertLess(retrying["navigation"]["actions"].index(self.action_rows(retrying, "claim")[0]),
                        retrying["navigation"]["actions"].index(blocked[0]))
        self.assertFalse(any(row.get("attempt") == old_attempt
                             for row in self.action_rows(retrying, "cleanup")))
        retained_receipt = Path(old_packet["ask_agent_workspace"]["receipt"])
        retained_receipt_bytes = retained_receipt.read_bytes()
        retained_head = self.f.git(old_workspace, "rev-parse", "HEAD")

        def assert_late_refusal(operation, value):
            before_head = self.head()
            before_child = self.f.child_state_path().read_bytes()
            before_ledger = self.f.ledger_bytes()
            before_worktrees = self.f.git(self.f.target, "worktree", "list", "--porcelain")
            refused = self.call(operation, value, ok=False)
            self.assertIn("stale or retried", refused.stderr.lower())
            self.assertEqual(self.head(), before_head)
            self.assertEqual(self.f.child_state_path().read_bytes(), before_child)
            self.assertEqual(self.f.ledger_bytes(), before_ledger)
            self.assertEqual(self.f.git(self.f.target, "worktree", "list", "--porcelain"), before_worktrees)

        assert_late_refusal("import-handoff", old_request)
        assert_late_refusal("done", old_positive)

        replacement = self.claim("A")["A"]
        self.assertNotEqual(replacement, old_attempt)
        self.managed_start("A", replacement)
        self.managed_context_check("A")
        self.import_finished("A", self.managed_worker_result("A"))
        self.prepare_and_done("A")
        assert_late_refusal("import-handoff", old_request)
        assert_late_refusal("done", old_positive)
        self.assertTrue(old_workspace.exists(), "late receipts must not remove the retained old workspace")
        pending = self.call("pending")
        self.assertIn(old_attempt, pending["lifecycle"]["retained_workers"])
        retained_actions = [row for row in pending["lifecycle"]["actions"]
                            if row.get("attempt") == old_attempt]
        self.assertEqual([row["action"] for row in retained_actions], ["blocked"])
        next_response = self.call("next")
        self.assertEqual([row["action"] for row in next_response["navigation"]["actions"]], ["blocked"])
        self.assertIn("incomplete", next_response["navigation"]["instruction"])
        self.assertIn("no non-integrated cleanup", retained_actions[0]["instruction"])
        final_proof = self.f.write("managed-retried-final.json", {
            "passed": True, "commit": self.head(), "checks": ["replacement A integrated"],
        })
        refused_finish = self.call("finish", {
            "commit": self.head(), "confirmed_stopped": True,
            "verification": {"path": str(final_proof), "sha256": fixture.digest(final_proof)},
        }, ok=False)
        self.assertIn("cleanup", refused_finish.stderr.lower())
        self.assertIn("no non-integrated cleanup", refused_finish.stderr)
        self.assertTrue(old_workspace.exists())
        self.assertEqual(retained_receipt.read_bytes(), retained_receipt_bytes)
        self.assertEqual(self.f.git(old_workspace, "rev-parse", "HEAD"), retained_head)

    def test_managed_preparation_crash_replays_one_receipt_without_another_worktree(self):
        self.managed_bind(single=True)
        attempt = self.claim("A")["A"]
        value = self.f.start_value("A", attempt, base=self.head())
        value["write_scope"] = ["chain_add.py"]
        original = fixture.chain._append

        def crash_before_allocation(chain_dir, event_id, kind, data, **kwargs):
            if kind == "allocation_intent":
                raise OSError("fixture interruption after helper preparation")
            return original(chain_dir, event_id, kind, data, **kwargs)

        with patch.object(fixture.chain, "_append", side_effect=crash_before_allocation):
            with self.assertRaises(OSError):
                fixture.chain._per_step_start(self.f.run, self.binding(), value)
        rows = self.bridge_events()
        prepared = next(row["event"]["data"] for row in rows
                        if row["event"]["kind"] == "managed_workspace_preparation_result")
        workspace = Path(prepared["workspace"]["worktree"])
        receipt = prepared["workspace"]["receipt"]
        self.assertTrue(workspace.is_dir())
        self.assertIsNone(fixture.chain._allocation(rows, attempt))
        before_worktrees = self.f.git(self.f.target, "worktree", "list", "--porcelain")
        self.assertEqual(before_worktrees.count("worktree "), 3)

        output = self.call("start", value)
        self.assertEqual(output["action"], "launch")
        self.packets["A"] = output["packet"]
        self.call("launched", {"attempt": attempt, "handle": {
            "host": "deterministic-process-fixture", "id": "A",
        }})
        allocation = fixture.chain._per_step_allocation(self.bridge_events(), attempt)
        self.assertEqual(allocation["ask_agent_workspace"]["receipt"], receipt)
        self.assertEqual(allocation["plan"]["path"], str(workspace))
        self.assertEqual(self.f.git(self.f.target, "worktree", "list", "--porcelain"), before_worktrees)
        kinds = [row["event"]["kind"] for row in self.bridge_events()]
        self.assertEqual(kinds.count("managed_workspace_preparation_intent"), 1)
        self.assertEqual(kinds.count("managed_workspace_preparation_result"), 1)
        self.assertEqual(kinds.count("allocation_intent"), 1)
        self.assertEqual(kinds.count("allocation_result"), 1)

        self.managed_context_check("A")
        self.import_finished("A", self.managed_worker_result("A"))
        self.prepare_and_done("A")
        self.finish()

    def test_managed_prepare_result_crash_recovers_one_receipt_without_second_prepare(self):
        self.managed_bind(single=True)
        attempt = self.claim("A")["A"]
        value = self.f.start_value("A", attempt, base=self.head())
        value["write_scope"] = ["chain_add.py"]
        original = fixture.chain._append

        def crash_before_preparation_receipt(chain_dir, event_id, kind, data, **kwargs):
            if kind == "managed_workspace_preparation_result":
                raise OSError("fixture interruption after helper created the workspace")
            return original(chain_dir, event_id, kind, data, **kwargs)

        with patch.object(fixture.chain, "_append", side_effect=crash_before_preparation_receipt):
            with self.assertRaises(OSError):
                fixture.chain._per_step_start(self.f.run, self.binding(), value)
        rows = self.bridge_events()
        self.assertTrue(any(row["event"]["kind"] == "managed_workspace_preparation_intent" for row in rows))
        self.assertFalse(any(row["event"]["kind"] == "managed_workspace_preparation_result" for row in rows))
        before_worktrees = self.f.git(self.f.target, "worktree", "list", "--porcelain")
        paths = [Path(line.removeprefix("worktree ")) for line in before_worktrees.splitlines()
                 if line.startswith("worktree ")]
        created = [path for path in paths if path not in {self.f.primary, self.f.target}]
        self.assertEqual(len(created), 1)

        output = self.call("start", value)
        self.assertEqual(output["action"], "launch")
        self.packets["A"] = output["packet"]
        self.call("launched", {"attempt": attempt, "handle": {
            "host": "deterministic-process-fixture", "id": "A",
        }})
        allocation = fixture.chain._per_step_allocation(self.bridge_events(), attempt)
        self.assertEqual(Path(allocation["plan"]["path"]), created[0])
        self.assertEqual(self.f.git(self.f.target, "worktree", "list", "--porcelain"), before_worktrees)
        kinds = [row["event"]["kind"] for row in self.bridge_events()]
        self.assertEqual(kinds.count("managed_workspace_preparation_intent"), 1)
        self.assertEqual(kinds.count("managed_workspace_preparation_result"), 1)

        self.managed_context_check("A")
        self.import_finished("A", self.managed_worker_result("A"))
        self.prepare_and_done("A")
        self.finish()

    def test_managed_replay_refuses_tampered_receipts_and_prepared_drift_before_launch(self):
        self.managed_bind(single=True)
        attempt = self.claim("A")["A"]
        packet = self.managed_start("A", attempt, record_launch=False)
        value = self.start_inputs["A"]
        workspace = Path(packet["context"]["workspace"])
        before_head = self.head()
        before_ledger = self.f.ledger_bytes()
        original_events = fixture.chain._events

        helper = Path(self.binding()["ask_agent"]["files"]["scripts/ask_agent_workspace.py"]["path"])
        alternate_store = self.f.parent / "alternate-managed-store"
        clean_env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        prepared_process = subprocess.run(
            [sys.executable, str(helper), "prepare", "--source", str(self.f.primary),
             "--store", str(alternate_store), "--label", "alternate-source", "--writers-quiescent"],
            text=True, capture_output=True, timeout=30, env=clean_env,
        )
        self.assertEqual(prepared_process.returncode, 0, prepared_process.stderr + prepared_process.stdout)
        alternate_prepare = json.loads(prepared_process.stdout)
        alternate_inspect_process = subprocess.run(
            [sys.executable, str(helper), "inspect", "--receipt", alternate_prepare["receipt"], "--phase", "prepared"],
            text=True, capture_output=True, timeout=30, env=clean_env,
        )
        self.assertEqual(alternate_inspect_process.returncode, 0,
                         alternate_inspect_process.stderr + alternate_inspect_process.stdout)
        alternate_inspect = json.loads(alternate_inspect_process.stdout)
        alternate_workspace = Path(alternate_prepare["worktree"])
        before_worktrees = self.f.git(self.f.target, "worktree", "list", "--porcelain")

        def remove_alternate_workspace():
            if alternate_workspace.exists():
                self.f.git(self.f.primary, "worktree", "remove", "--force", str(alternate_workspace))

        self.addCleanup(remove_alternate_workspace)

        def alternate_receipt(record):
            frozen_helper = self.binding()["ask_agent"]["files"]["scripts/ask_agent_workspace.py"]
            return {
                "helper": dict(frozen_helper), "receipt": alternate_prepare["receipt"],
                "receipt_sha256": fixture.digest(Path(alternate_prepare["receipt"])),
                "worktree": alternate_prepare["worktree"], "branch": alternate_prepare["branch"],
                "baseline": alternate_prepare["baseline"], "prepare": alternate_prepare,
                "prepared": alternate_inspect,
            }

        mutations = {
            "helper-mismatch": lambda record: record["helper"].update({"sha256": "0" * 64}),
            "malformed-prepared": lambda record: record.update({"prepared": {"phase": "prepared"}}),
            "prepared-worktree-splice": lambda record: record["prepared"].update({"worktree": str(self.f.primary)}),
            "same-common-dir-alternate-source": lambda record: record.clear() or record.update(alternate_receipt(record)),
        }

        for label, mutate in mutations.items():
            with self.subTest(label=label):
                def tampered_events(*args, **kwargs):
                    rows = json.loads(json.dumps(original_events(*args, **kwargs)))
                    for row in rows:
                        event = row.get("event", {})
                        if event.get("kind") == "allocation_intent":
                            mutate(event["data"]["ask_agent_workspace"])
                    return rows

                with patch.object(fixture.chain, "_events", side_effect=tampered_events):
                    with self.assertRaises(fixture.chain.ChainError):
                        fixture.chain._per_step_start(self.f.run, self.binding(), value)
                self.assertEqual(self.head(), before_head)
                self.assertEqual(self.f.ledger_bytes(), before_ledger)
                self.assertEqual(self.f.git(self.f.target, "worktree", "list", "--porcelain"), before_worktrees)
                self.assertTrue(workspace.exists())
                self.assertEqual(self.f.child_record(attempt)["status"], "launching")

        (workspace / "prepared-drift.txt").write_text("not part of the prepared baseline\n")
        refused = self.call("start", value, ok=False)
        self.assertTrue(any(word in refused.stderr.lower() for word in ("drift", "prepared", "receipt")),
                        refused.stderr)
        self.assertEqual(self.head(), before_head)
        self.assertTrue(workspace.exists())
        (workspace / "prepared-drift.txt").unlink()
        remove_alternate_workspace()
        self.assertFalse(alternate_workspace.exists())

        self.call("launched", {"attempt": attempt, "handle": {
            "host": "deterministic-process-fixture", "id": "A",
        }})
        self.managed_context_check("A")
        self.import_finished("A", self.managed_worker_result("A"))
        self.prepare_and_done("A")
        self.finish()

    def test_managed_delivery_refuses_ignored_worker_output_before_integration(self):
        """Ignored generated output is refused at returned delivery, never after integration.

        Ask-Agent reports it as `ignored_paths` (never as contribution).  ShipLoop's
        cleanup keeps any worktree that still holds ignored files, so accepting the
        delivery would integrate a chain that could never finish.  Removing the
        output and importing again delivers, integrates and cleans up normally.
        """
        graph = json.loads(self.f.graph.read_text())
        graph["steps"] = graph["steps"][:1]
        self.f.graph.write_text(json.dumps(graph) + "\n")
        self.managed_bind(capacity=1)
        self.assertIn("ignored-output-report", self.binding()["ask_agent_contract"]["capabilities"])
        attempts = self.claim("A")
        packet = self.managed_start("A", attempts["A"], base=self.head())
        workspace = Path(packet["context"]["workspace"])
        common = Path(self.f.git(workspace, "rev-parse", "--path-format=absolute", "--git-common-dir").strip())
        (common / "info").mkdir(exist_ok=True)  # a template may omit info/
        with (common / "info" / "exclude").open("a") as stream:
            stream.write("\n__pycache__/\n")
        result = self.managed_worker_result("A")
        generated = workspace / "__pycache__"
        generated.mkdir()
        (generated / "generated.cpython-312.pyc").write_bytes(b"\x00generated")
        target_before = self.head()
        refused = self.call("import-handoff", {"attempt": attempts["A"], "confirmed_stopped": True,
                            "handoff": {"path": result["handoff"], "sha256": result["sha256"]}}, ok=False)
        self.assertIn("ignored generated output (__pycache__/generated.cpython-312.pyc)", refused.stderr)
        self.assertEqual(self.head(), target_before, "refusal must precede any target mutation")
        self.assertFalse(any(row["event"]["kind"] == "managed_returned_delivery" for row in self.bridge_events()))

        shutil.rmtree(generated)
        self.import_finished("A", result)
        accepted = self.prepare_and_done("A")
        self.assertEqual(accepted["outcome"], "accepted")
        self.assertFalse(workspace.exists())
        self.finish()

    def test_managed_returned_delivery_mismatch_refuses_before_target_mutation(self):
        self.managed_bind(single=True)
        attempt = self.claim("A")["A"]
        packet = self.managed_start("A", attempt)
        self.managed_context_check("A")
        result = self.managed_worker_result("A", commits=2, manifest_commit=None)
        # A handoff naming the first commit instead of the actual worker HEAD
        # is a valid Git object but not the complete returned linear range.
        handoff = Path(result["handoff"])
        manifest = json.loads(handoff.read_text())
        manifest["commit"] = result["commits"][0]
        handoff.write_text(json.dumps(manifest) + "\n")
        result["sha256"] = hashlib.sha256(handoff.read_bytes()).hexdigest()
        before_head = self.head()
        before_child = self.f.child_state_path().read_bytes()
        refused = self.call("import-handoff", {"attempt": attempt, "confirmed_stopped": True,
                                                "handoff": {"path": result["handoff"], "sha256": result["sha256"]}},
                            ok=False)
        self.assertIn("delivery", refused.stderr.lower())
        self.assertEqual(self.head(), before_head)
        self.assertEqual(self.f.child_state_path().read_bytes(), before_child)
        self.assertTrue(Path(packet["context"]["workspace"]).exists())
        self.assertFalse(any(row["event"]["kind"] == "managed_returned_delivery"
                             for row in self.bridge_events()))

        workspace = Path(packet["context"]["workspace"])

        def remove_retained_workspace():
            if workspace.exists():
                self.f.git(self.f.target, "worktree", "remove", "--force", str(workspace))

        self.addCleanup(remove_retained_workspace)

    def test_managed_retained_close_stays_pending_then_recovers_after_close_crash_boundary(self):
        self.managed_bind(single=True)
        attempt = self.claim("A")["A"]
        packet = self.managed_start("A", attempt)
        workspace = Path(packet["context"]["workspace"])
        helper = packet["ask_agent_workspace"]["executing_helper"]["path"]
        clean_env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        probe = subprocess.run([sys.executable, helper, "close", "--receipt",
                                packet["ask_agent_workspace"]["receipt"]],
                               text=True, capture_output=True, timeout=30, env=clean_env)
        self.assertEqual(probe.returncode, 0, probe.stderr + probe.stdout)
        retained = json.loads(probe.stdout)
        self.assertEqual((retained["status"], retained["removed"]), ("retained", False))

        self.managed_context_check("A")
        self.import_finished("A", self.managed_worker_result("A"))
        value = self.prepared_input("A")
        original_helper = fixture.chain._ask_agent_workspace

        def retain_close(binding, operation, *arguments):
            if operation == "close":
                return retained
            return original_helper(binding, operation, *arguments)

        with patch.object(fixture.chain, "_ask_agent_workspace", side_effect=retain_close) as managed_helper:
            settled = fixture.chain._per_step_done(self.f.run, self.binding(), value)
            self.assertEqual(settled["outcome"], "accepted")
            self.assertEqual(settled["cleanup"], {
                "attempt": attempt,
                "cleanup": None,
                "pending": True,
                "deferred": True,
            })
            self.assertFalse(any(
                len(call.args) > 1 and call.args[1] == "close"
                for call in managed_helper.call_args_list
            ), "managed done must defer helper close to the cleanup callback")
            pending_close = fixture.chain._per_step_cleanup_attempt(
                self.f.run, self.binding(), attempt, confirmed_stopped=True,
            )
            self.assertEqual(sum(
                len(call.args) > 1 and call.args[1] == "close"
                for call in managed_helper.call_args_list
            ), 1)
        self.assertTrue(pending_close["pending"])
        self.assertTrue(workspace.exists())
        self.assertEqual(self.head(), value["integration"]["candidate_commit"])
        pending = self.call("pending")
        self.assertIn(attempt, pending["lifecycle"]["cleanup_pending"])
        self.assertIn(attempt, pending["lifecycle"]["retained_workers"])

        original_append = fixture.chain._append

        def crash_after_helper_close(chain_dir, event_id, kind, data, **kwargs):
            if kind == "cleanup_result":
                raise OSError("fixture interruption after helper-owned worktree removal")
            return original_append(chain_dir, event_id, kind, data, **kwargs)

        with patch.object(fixture.chain, "_append", side_effect=crash_after_helper_close):
            with self.assertRaises(OSError):
                fixture.chain._per_step_cleanup_attempt(
                    self.f.run, self.binding(), attempt, confirmed_stopped=True,
                )
        self.assertFalse(workspace.exists(), "the injected crash happens after the helper closes its worktree")

        cleaned = self.call("cleanup", {"attempt": attempt, "confirmed_stopped": True})
        self.assertFalse(cleaned["pending"])
        close = cleaned["cleanup"]["close"]
        self.assertEqual((close["status"], close["removed"], close["decision"]), ("closed", True, "integrated"))
        self.assertFalse(workspace.exists())
        kinds = [row["event"]["kind"] for row in self.bridge_events()]
        self.assertEqual(kinds.count("managed_close_inspection"), 1)
        self.assertEqual(kinds.count("cleanup_result"), 1)
        self.finish()

    def test_managed_cleanup_crash_before_inspection_retains_late_drift(self):
        ignore = self.f.target / ".gitignore"
        ignore.write_text("late-managed-ignored.txt\n")
        self.f.git(self.f.target, "add", ".gitignore")
        self.f.git(self.f.target, "commit", "-qm", "Ignore late managed fixture drift")
        attempt, packet = self.accept_managed_a_with_deferred_cleanup()
        workspace = Path(packet["context"]["workspace"])
        integration = self.done_inputs["A"]["integration"]
        original_append = fixture.chain._append

        def crash_before_inspection_event(chain_dir, event_id, kind, data, **kwargs):
            if kind == "managed_close_inspection":
                raise OSError("fixture interruption before managed close inspection is recorded")
            return original_append(chain_dir, event_id, kind, data, **kwargs)

        with patch.object(fixture.chain, "_append", side_effect=crash_before_inspection_event):
            with self.assertRaises(OSError):
                fixture.chain._per_step_cleanup_attempt(
                    self.f.run, self.binding(), attempt, confirmed_stopped=True,
                )
        kinds = [row["event"]["kind"] for row in self.bridge_events()]
        self.assertNotIn("managed_close_inspection", kinds)
        self.assertNotIn("cleanup_intent", kinds)
        self.assertNotIn("cleanup_result", kinds)

        untracked = workspace / "late-managed-untracked.txt"
        ignored = workspace / "late-managed-ignored.txt"
        committed = workspace / "late-managed-committed.txt"
        untracked.write_text("retain untracked late worker change\n")
        ignored.write_text("retain ignored late worker change\n")
        committed.write_text("retain committed late worker change\n")
        self.f.git(workspace, "add", committed.name)
        self.f.git(workspace, "commit", "-qm", "Late managed fixture drift")
        late_commit = self.f.git(workspace, "rev-parse", "HEAD")
        self.assertNotEqual(late_commit, integration["source_commit"])
        self.assertTrue(all(path.exists() for path in (untracked, ignored, committed)))

        retained = self.call("cleanup", {"attempt": attempt, "confirmed_stopped": True})
        self.assertTrue(retained["pending"])
        self.assertTrue(retained["retained"])
        self.assertIsNone(retained["cleanup"])
        self.assertTrue(workspace.exists(), "managed cleanup must retain all unaccepted late worker changes")
        self.assertTrue(all(path.exists() for path in (untracked, ignored, committed)))
        self.assertIn(attempt, self.call("pending")["lifecycle"]["retained_workers"])
        kinds = [row["event"]["kind"] for row in self.bridge_events()]
        self.assertNotIn("managed_close_inspection", kinds)
        self.assertNotIn("cleanup_intent", kinds)
        self.assertNotIn("cleanup_result", kinds)

        # This is a disposable worker fixture. Restore its exact accepted W,
        # then prove normal close can recover without moving the integration target.
        self.f.git(workspace, "reset", "--hard", integration["source_commit"])
        untracked.unlink()
        ignored.unlink()
        before_recovery = self.head()
        cleaned = self.call("cleanup", {"attempt": attempt, "confirmed_stopped": True})
        self.assertFalse(cleaned["pending"])
        self.assertFalse(workspace.exists())
        self.assertEqual(self.head(), before_recovery)
        self.finish()

    def test_managed_cleanup_crash_after_inspection_retains_late_drift(self):
        attempt, packet = self.accept_managed_a_with_deferred_cleanup()
        workspace = Path(packet["context"]["workspace"])
        original_append = fixture.chain._append

        def crash_after_inspection_event(chain_dir, event_id, kind, data, **kwargs):
            recorded = original_append(chain_dir, event_id, kind, data, **kwargs)
            if kind == "managed_close_inspection":
                raise OSError("fixture interruption after managed close inspection is recorded")
            return recorded

        with patch.object(fixture.chain, "_append", side_effect=crash_after_inspection_event):
            with self.assertRaises(OSError):
                fixture.chain._per_step_cleanup_attempt(
                    self.f.run, self.binding(), attempt, confirmed_stopped=True,
                )
        kinds = [row["event"]["kind"] for row in self.bridge_events()]
        self.assertEqual(kinds.count("managed_close_inspection"), 1)
        self.assertNotIn("cleanup_intent", kinds)
        self.assertNotIn("cleanup_result", kinds)

        late = workspace / "late-managed-after-inspection.txt"
        late.write_text("retain post-inspection worker change\n")
        retained = self.call("cleanup", {"attempt": attempt, "confirmed_stopped": True})
        self.assertTrue(retained["pending"])
        self.assertTrue(retained["retained"])
        self.assertIsNone(retained["cleanup"])
        self.assertTrue(workspace.exists())
        self.assertTrue(late.exists())
        kinds = [row["event"]["kind"] for row in self.bridge_events()]
        self.assertEqual(kinds.count("managed_close_inspection"), 1)
        self.assertNotIn("cleanup_intent", kinds)
        self.assertNotIn("cleanup_result", kinds)

        late.unlink()
        before_recovery = self.head()
        cleaned = self.call("cleanup", {"attempt": attempt, "confirmed_stopped": True})
        self.assertFalse(cleaned["pending"])
        self.assertFalse(workspace.exists())
        self.assertEqual(self.head(), before_recovery)
        self.finish()

    def test_managed_blocked_handoff_is_archived_and_retained_without_commit_delivery(self):
        self.managed_bind(single=True)
        attempt = self.claim("A")["A"]
        packet = self.managed_start("A", attempt)
        self.managed_context_check("A")
        stopped = self.managed_non_success_handoff("A", "BLOCKED")
        imported = self.import_finished("A", stopped)
        workspace = Path(packet["context"]["workspace"])
        self.assertEqual(imported["import"]["status"], "BLOCKED")
        self.assertIsNone(imported["import"]["commit"])
        self.assertFalse(Path(stopped["handoff"]).exists())
        self.assertTrue(Path(imported["import"]["archives"][0]["archived_path"]).is_file())
        self.assertFalse(any(row["event"]["kind"] == "managed_returned_delivery"
                             for row in self.bridge_events()))
        receipt = fixture.chain._node(self.binding(), "receipt", {"attempt": attempt})
        proof = self.f.write("managed-blocked.json", {"passed": False, "status": "BLOCKED"})
        rejected = self.call("done", {"attempt": attempt, "confirmed_stopped": True,
                                       "verification": {"receipt_sha256": receipt["sha256"], "passed": False,
                                                        "reason": "Blocked fixture has no code contribution",
                                                        "evidence": {"path": str(proof),
                                                                     "sha256": fixture.digest(proof)}}})
        self.assertEqual(rejected["outcome"], "rejected")
        self.assertEqual(self.head(), self.f.initial)
        self.assertTrue(workspace.exists(), "a rejected managed workspace stays retained for recovery")
        self.assertIn(attempt, self.call("pending")["lifecycle"]["retained_workers"])
        self.call("retry", {"attempt": attempt, "confirmed_stopped": True,
                            "reason": "Blocked managed worker requires a replacement"})
        superseded = self.call("cleanup", {"attempt": attempt, "confirmed_stopped": True,
                                             "disposition": "superseded",
                                             "reason": "Replacement will be handled separately"}, ok=False)
        self.assertIn("retain the superseded Ask-Agent helper-managed workspace", superseded.stderr)
        self.assertTrue(workspace.exists(), "managed superseded cleanup must preserve its helper receipt")

        def remove_retained_workspace():
            if workspace.exists():
                self.f.git(self.f.target, "worktree", "remove", "--force", str(workspace))

        self.addCleanup(remove_retained_workspace)

    def test_current_managed_helper_accepts_060_when_it_declares_capabilities_and_identity(self):
        self.use_managed_ask_agent()
        card = self.f.ask / "SKILL.md"
        import re
        card.write_text(re.sub(r"(?m)^version:.*$", "version: 0.6.0", card.read_text()))
        self.bind(single=True)
        identity = self.binding()["ask_agent_identity"]
        self.assertEqual(identity["version"], "0.6.0")
        self.assertEqual(identity["method"], "helper-v1")
        self.assertEqual(identity["resolved_helper"], str(self.f.ask / "scripts/ask_agent_workspace.py"))
        self.assertEqual(self.binding()["ask_agent_contract"], self.managed_capabilities())
        self.assertEqual(self.f.git(self.f.primary, "worktree", "list", "--porcelain").count("worktree "), 2)

    def test_managed_serial_uses_helper_workspace_and_main_context_without_handle(self):
        self.managed_bind(mode="serial", single=True)
        binding = self.binding()
        self.assertEqual(binding["schema"], "shiploop-chain-binding/v6")
        attempt = self.claim("A")["A"]
        packet = self.start("A", attempt, serial=True)
        allocation = fixture.chain._per_step_allocation(self.bridge_events(), attempt)
        self.assertEqual(allocation["adoption"], "ask-agent-managed-workspace")
        self.assertEqual(allocation["plan"]["path"], packet["context"]["workspace"])
        self.assertEqual(packet["ask_agent_workspace"]["worktree"], packet["context"]["workspace"])
        self.assertIsNone(self.f.child_record(attempt)["handle"])
        self.assertEqual(packet["executor"]["kind"], "main-context")
        self.complete_step("A")
        events = [row["event"] for row in self.bridge_events()]
        self.assertTrue(any(row["kind"] == "managed_returned_delivery"
                            and row["data"].get("attempt") == attempt for row in events))
        self.assertTrue(any(row["kind"] == "managed_close_inspection"
                            and row["data"].get("attempt") == attempt for row in events))
        self.assertFalse(any(row["kind"].startswith("launched_") for row in events))
        self.finish()

    def test_future_managed_version_and_reformatted_prose_bind_through_capabilities(self):
        self.use_managed_ask_agent()
        card = self.f.ask / "SKILL.md"
        helper = self.f.ask / "scripts/ask_agent_workspace.py"
        original_phrase = "The bundled helper owns Git\nworkspace preparation and eligible cleanup;"
        text = card.read_text()
        self.assertIn(original_phrase, text)
        reformatted = re.sub(r"(?m)^version:.*$", "version: 1.2.3", text).replace(
            original_phrase,
            "This helper prepares its workspace\n\nand closes eligible accepted work;",
            1,
        )
        self.assertNotEqual(reformatted, text)
        card.write_text(reformatted)
        helper_text = helper.read_text()
        original_capabilities = '        "capabilities": list(MANAGED_WORKTREE_CAPABILITIES),'
        self.assertIn(original_capabilities, helper_text)
        helper.write_text(helper_text.replace(
            original_capabilities,
            '        "capabilities": list(reversed(MANAGED_WORKTREE_CAPABILITIES)) + ["future-managed-capability"],',
            1,
        ))
        bound = self.bind(single=True)
        self.assertEqual(bound["shiploop_chain"]["lifecycle"], "per-step")
        declared = self.managed_capabilities()
        self.assertEqual(declared["version"], "1.2.3")
        self.assertEqual(declared["capabilities"], [
            "ignored-output-report", "fingerprint-bound-close", "returned-commit-delivery",
            "prepared-inspection", "helper-managed-worktree", "future-managed-capability",
        ])
        self.assertEqual(self.binding()["ask_agent_contract"], declared)
        self.assertEqual(self.f.git(self.f.primary, "worktree", "list", "--porcelain").count("worktree "), 2)

    def test_old_04_and_final_return_fresh_bindings_refuse_before_effects(self):
        self.use_legacy_ask_agent()
        before_run = self.f.run_bytes()
        before_head = self.head()
        before_worktrees = self.f.git(self.f.primary, "worktree", "list", "--porcelain")
        old = self.bind(ok=False)
        # The historical card lacks the current managed package layout and
        # is rejected before a helper can execute.
        self.assertIn("cannot resolve ask-agent references/native-lifecycle.md", old.stderr.lower())
        self.assertEqual(self.f.run_bytes(), before_run)
        self.assertEqual(self.head(), before_head)
        self.assertEqual(self.f.git(self.f.primary, "worktree", "list", "--porcelain"), before_worktrees)
        self.assertFalse((self.f.run / "chains").exists())

        # A complete package with an old version must also fail the numeric
        # floor, even when its capability endpoint exists.
        self.use_managed_ask_agent()
        card = self.f.ask / "SKILL.md"
        card.write_text(re.sub(r"(?m)^version:.*$", "version: 0.4.9", card.read_text()))
        old_version = self.bind(ok=False)
        self.assertIn("requires Ask-Agent 0.6.0 or newer", old_version.stderr)
        self.assertEqual(self.f.run_bytes(), before_run)
        self.assertEqual(self.head(), before_head)
        self.assertEqual(self.f.git(self.f.primary, "worktree", "list", "--porcelain"), before_worktrees)
        self.assertFalse((self.f.run / "chains").exists())

        self.use_managed_ask_agent()
        before_run = self.f.run_bytes()
        final_return = self.f.call("bind", ok=False, extra=(
            "--graph", str(self.f.graph), "--dispatcher-skill", str(self.f.dispatcher / "SKILL.md"),
            "--ask-agent-skill", str(self.f.ask / "SKILL.md"), "--worktree-parent", str(self.f.parent),
            "--mode", "parallel", "--lifecycle", "final-return",
        ))
        self.assertRegex(final_return.stderr.lower(), r"managed|per-step|final-return")
        self.assertEqual(self.f.run_bytes(), before_run)
        self.assertEqual(self.head(), before_head)
        self.assertEqual(self.f.git(self.f.primary, "worktree", "list", "--porcelain"), before_worktrees)
        self.assertFalse((self.f.run / "chains").exists())

    def test_unknown_or_missing_managed_capability_and_identity_refuse_before_effects(self):
        self.use_managed_ask_agent()
        helper = self.f.ask / "scripts/ask_agent_workspace.py"
        before_run = self.f.run_bytes()
        before_head = self.head()
        before_worktrees = self.f.git(self.f.primary, "worktree", "list", "--porcelain")
        helper.write_text(helper.read_text().replace(
            'MANAGED_WORKTREE_CAPABILITIES_SCHEMA = "shiploop-chain-ask-agent-managed-worktree/v1"',
            'MANAGED_WORKTREE_CAPABILITIES_SCHEMA = "unknown-managed-contract/v9"', 1,
        ))
        unknown = self.bind(ok=False)
        self.assertRegex(unknown.stderr.lower(), r"contract|capabilit|managed")
        self.assertEqual(self.f.run_bytes(), before_run)
        self.assertEqual(self.head(), before_head)
        self.assertEqual(self.f.git(self.f.primary, "worktree", "list", "--porcelain"), before_worktrees)
        self.assertFalse((self.f.run / "chains").exists())

        self.use_managed_ask_agent()
        helper = self.f.ask / "scripts/ask_agent_workspace.py"
        helper.write_text(helper.read_text().replace(
            'capabilities_parser = commands.add_parser("capabilities")',
            'capabilities_parser = commands.add_parser("legacy-capabilities")', 1,
        ))
        missing_capabilities = self.bind(ok=False)
        self.assertRegex(missing_capabilities.stderr.lower(), r"capabilit|managed")
        self.assertEqual(self.f.run_bytes(), before_run)
        self.assertEqual(self.head(), before_head)
        self.assertEqual(self.f.git(self.f.primary, "worktree", "list", "--porcelain"), before_worktrees)
        self.assertFalse((self.f.run / "chains").exists())

        self.use_managed_ask_agent()
        card = self.f.ask / "SKILL.md"
        card.write_text(re.sub(r"(?m)^version:.*$", "version: 0.6.0", card.read_text()))
        helper = self.f.ask / "scripts/ask_agent_workspace.py"
        helper.write_text(helper.read_text().replace(
            'identity_parser = commands.add_parser("identity")',
            'identity_parser = commands.add_parser("legacy-identity")', 1,
        ))
        missing_identity = self.bind(ok=False)
        self.assertRegex(missing_identity.stderr.lower(), r"identity|managed|capabilit")
        self.assertEqual(self.f.run_bytes(), before_run)
        self.assertEqual(self.head(), before_head)
        self.assertEqual(self.f.git(self.f.primary, "worktree", "list", "--porcelain"), before_worktrees)
        self.assertFalse((self.f.run / "chains").exists())

    def test_retired_v5_binding_with_removed_package_is_inspection_only(self):
        """Historic bindings survive host-skill rotation but cannot resume execution."""
        self.managed_bind(single=True)
        binding_path = self.f.run / "chains" / self.f.action / "binding.md"
        binding = fixture.store.read_record(binding_path)
        self.assertEqual(binding["schema"], "shiploop-chain-binding/v6")
        binding["schema"] = "shiploop-chain-binding/v5"
        # A retired view must never execute the frozen node or resolve an
        # installed helper.  Both paths are deliberately unavailable here.
        binding["node"] = str(self.f.base / "retired-node-must-not-run")
        raw = fixture.store.dumps(binding, "ShipLoop chain binding")
        state = fixture.store.read_record(self.f.run / "state.md")
        state["chain_bindings"] = dict(state["chain_bindings"])
        state["chain_bindings"][self.f.action] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        state["revision"] += 1
        fixture.nav.save(self.f.run, state, {
            str(binding_path.relative_to(self.f.run)): raw,
        })
        shutil.rmtree(self.f.ask)

        before_run = self.f.run_bytes()
        before_head = self.head()
        before_worktrees = self.f.git(self.f.primary, "worktree", "list", "--porcelain")
        history = self.f.call("history")
        pending = self.f.call("pending")
        self.assertEqual(history["retired_flow"]["binding_schema"], "shiploop-chain-binding/v5")
        self.assertEqual(pending["retired_flow"], history["retired_flow"])
        self.assertIsNone(pending["pending"])
        self.assertEqual(pending["pending_reason"], "retired flow state was not queried")
        self.assertEqual(self.f.run_bytes(), before_run)

        for operation in ("next", "recover"):
            projection = self.f.call(operation)
            self.assertEqual(projection["retired_flow"], history["retired_flow"])
            self.assertEqual(self.f.run_bytes(), before_run)

        bind = self.f.call("bind", ok=False, extra=(
            "--graph", str(self.f.graph), "--dispatcher-skill", str(self.f.dispatcher / "SKILL.md"),
            "--ask-agent-skill", str(self.f.ask / "SKILL.md"), "--worktree-parent", str(self.f.parent),
            "--mode", "parallel", "--lifecycle", "per-step",
        ))
        self.assertRegex(bind.stderr.lower(), r"retired|managed|inspection")
        self.assertEqual(self.f.run_bytes(), before_run)
        self.assertEqual(self.head(), before_head)
        self.assertEqual(self.f.git(self.f.primary, "worktree", "list", "--porcelain"), before_worktrees)

        attempt = "retired-attempt"
        proof = self.f.write("retired-v5-finish.json", {"passed": True, "commit": before_head})
        handoff = self.f.write("retired-v5-handoff.json", {"retired": True})
        for operation, value in (
            ("claim", {"steps": ["A"]}),
            ("start", self.f.start_value("A", attempt)),
            ("launched", {"attempt": attempt, "handle": {"host": "fixture", "id": "retired"}}),
            ("observe", {"attempt": attempt, "occurred_at": "2026-09-20T00:00:00Z"}),
            ("import-handoff", {"attempt": attempt, "confirmed_stopped": True,
                                "handoff": {"path": str(handoff), "sha256": fixture.digest(handoff)}}),
            ("prepare", {"attempt": attempt, "confirmed_stopped": True}),
            ("settle", {"attempt": attempt, "confirmed_stopped": True}),
            ("done", {"attempt": attempt, "confirmed_stopped": True}),
            ("retry", {"attempt": attempt, "confirmed_stopped": True, "reason": "retired fixture"}),
            ("packet", {"attempt": attempt}),
            ("cleanup", {"attempt": attempt, "confirmed_stopped": True}),
            ("finish", {"commit": before_head, "confirmed_stopped": True,
                        "verification": {"path": str(proof), "sha256": fixture.digest(proof)}}),
        ):
            refused = self.f.call(operation, value, ok=False)
            self.assertRegex(refused.stderr.lower(), r"retired|managed|inspection")
            self.assertEqual(self.f.run_bytes(), before_run)
            self.assertEqual(self.head(), before_head)
            self.assertEqual(self.f.git(self.f.primary, "worktree", "list", "--porcelain"), before_worktrees)

    def test_stale_combined_candidate_refuses_merge_then_reprepares(self):
        self.bind()
        attempts = self.claim("A", "B")
        for step in ("A", "B"):
            self.start(step, attempts[step])
            self.collect(step, self.launch(step))
        stale_b = self.prepared_input("B")
        self.prepare_and_done("A")
        after_a = self.head()
        refused = self.call("done", stale_b, ok=False)
        self.assertTrue(any(word in refused.stderr.lower() for word in ("target", "stale", "head")), refused.stderr)
        self.assertEqual(self.head(), after_a)
        self.assertNotEqual(self.f.child_record(attempts["B"])["status"], "accepted")
        self.prepare_and_done("B")
        self.f.git(self.f.target, "merge-base", "--is-ancestor", after_a, self.head())

    def test_parallel_semantic_rejection_cannot_resume_retried_worker(self):
        self.bind()
        attempts = self.claim("A", "B")
        a_packet = self.start("A", attempts["A"], record_launch=False)
        b_packet = self.start("B", attempts["B"])
        a_worker = Path(a_packet["context"]["workspace"])
        b_worker = Path(b_packet["context"]["workspace"])
        missing_handle = self.call("next")
        self.assertEqual([row["attempt"] for row in self.action_rows(missing_handle, "reconcile")],
                         [attempts["A"]])
        self.assertFalse(self.action_rows(missing_handle, "launch"),
                         "a missing recorded handle must reconcile, never create a second launch grant")
        a, b = self.launch("A"), self.launch("B")
        # Each worker remains locally valid.  Together B's support module
        # changes A's behavior only in the prepared combined candidate.
        (a_worker / "chain_add.py").write_text(
            "def add(left, right):\n"
            "    try:\n"
            "        from chain_format import adjust_total\n"
            "    except ImportError:\n"
            "        return left + right\n"
            "    return adjust_total(left + right)\n"
        )
        (b_worker / "chain_format.py").write_text(
            "def normalize(text):\n"
            "    return ' '.join(text.strip().lower().split())\n\n"
            "def adjust_total(total):\n"
            "    return total - 1\n"
        )
        self.verify(a_worker, expected_steps=("A",))
        self.verify(b_worker, expected_steps=("B",))
        self.collect("A", a)
        self.collect("B", b)
        a_value = self.prepared_input("A")
        before_fast_report_head = self.head()
        before_fast_report_ledger = self.f.ledger_bytes()
        fast_report = self.call("done", a_value, ok=False)
        self.assertIn("native launch handle", fast_report.stderr)
        self.assertEqual(self.head(), before_fast_report_head)
        self.assertEqual(self.f.ledger_bytes(), before_fast_report_ledger)
        self.assertFalse(any(row["event"]["kind"] == "integration_result"
                             and row["event"]["data"].get("attempt") == attempts["A"]
                             for row in self.bridge_events()))
        self.call("launched", {"attempt": attempts["A"], "handle": {
            "host": "deterministic-process-fixture", "id": "A",
        }})
        accepted_a = self.call("done", a_value)
        self.assertEqual(accepted_a["outcome"], "accepted")
        self.assertEqual(self.head(), a_value["integration"]["candidate_commit"])
        a_cleanup = self.run_deferred_managed_cleanup("A", accepted_a)
        self.assertIsNotNone(a_cleanup)
        self.assertFalse(a_cleanup["pending"])
        self.assertFalse(a_worker.exists())
        self.verify(self.f.target, expected_steps=("A",))
        after_a = self.head()
        old_b_prepared = self.call("prepare", {"attempt": attempts["B"], "confirmed_stopped": True})
        combined = subprocess.run(
            [sys.executable, "-B", "-c", "from chain_add import add; assert add(2,3)==5"],
            cwd=b_worker, text=True, capture_output=True, timeout=15,
        )
        self.assertNotEqual(combined.returncode, 0, combined.stderr)
        receipt = fixture.chain._node(self.binding(), "receipt", {"attempt": attempts["B"]})
        proof = self.f.write("semantic-conflict-b.json", {
            "passed": False, "integration": old_b_prepared["integration"],
            "checks": ["combined add behavior after B support module is installed"],
        })
        rejected_input = {
            "attempt": attempts["B"], "confirmed_stopped": True,
            "verification": {
                "receipt_sha256": receipt["sha256"], "passed": False,
                "reason": "Combined candidate changes independently verified add behavior",
                "evidence": {"path": str(proof), "sha256": fixture.digest(proof)},
            },
        }
        rejected = self.call("done", rejected_input)
        self.assertEqual(rejected["outcome"], "rejected")
        self.assertEqual((rejected["step"], rejected["attempt"]), ("B", attempts["B"]))
        self.assertEqual(self.head(), after_a)
        self.assertNotIn("J", self.call("next")["ready"])
        conflicting_proof = self.f.write("conflicting-terminal-b.json", {
            "passed": True, "integration": old_b_prepared["integration"],
            "checks": ["structurally exact stale W/T/I proof"],
        })
        conflicting_input = {
            "attempt": attempts["B"], "confirmed_stopped": True,
            "integration": old_b_prepared["integration"],
            "verification": {
                "receipt_sha256": receipt["sha256"], "passed": True,
                "reason": "Conflicting terminal positive replay",
                "evidence": {"path": str(conflicting_proof), "sha256": fixture.digest(conflicting_proof)},
            },
        }
        before_conflict_head = self.head()
        before_conflict_ledger = self.f.ledger_bytes()
        before_conflict_worktrees = self.f.git(self.f.target, "worktree", "list", "--porcelain")
        conflict = self.call("done", conflicting_input, ok=False)
        self.assertIn("terminal", conflict.stderr)
        self.assertEqual(self.head(), before_conflict_head)
        self.assertEqual(self.f.ledger_bytes(), before_conflict_ledger)
        self.assertEqual(self.f.git(self.f.target, "worktree", "list", "--porcelain"), before_conflict_worktrees)
        self.assertFalse(any(row["event"]["kind"] == "integration_result"
                             and row["event"]["data"].get("attempt") == attempts["B"]
                             for row in self.bridge_events()))
        self.call("retry", {"attempt": attempts["B"], "confirmed_stopped": True,
                              "reason": "Repair cross-file semantic conflict"})

        before_head = self.head()
        before_ledger = self.f.ledger_bytes()
        before_worktrees = self.f.git(self.f.target, "worktree", "list", "--porcelain")
        for operation, value in (
            ("prepare", {"attempt": attempts["B"], "confirmed_stopped": True}),
            ("done", rejected_input),
        ):
            refused = self.call(operation, value, ok=False)
            self.assertIn("stale or retried", refused.stderr)
            self.assertEqual(self.head(), before_head)
            self.assertEqual(self.f.ledger_bytes(), before_ledger)
            self.assertEqual(self.f.git(self.f.target, "worktree", "list", "--porcelain"), before_worktrees)

        self.start("B", self.claim("B")["B"])
        self.complete_step("B")
        retained = self.call("cleanup", {"attempt": attempts["B"], "confirmed_stopped": True,
                                          "disposition": "superseded",
                                          "reason": "Replacement independently accepted and integrated"}, ok=False)
        self.assertRegex(retained.stderr.lower(), r"retain|managed|superseded")
        self.assertTrue(b_worker.exists())
        self.start("C", self.claim("C")["C"])
        self.complete_step("C")
        self.start("J", self.claim("J")["J"])
        self.complete_step("J")
        proof = self.f.write("semantic-conflict-retained-finish.json", {
            "passed": True, "commit": self.head(),
        })
        blocked = self.call("finish", {
            "commit": self.head(), "confirmed_stopped": True,
            "verification": {"path": str(proof), "sha256": fixture.digest(proof)},
        }, ok=False)
        self.assertRegex(blocked.stderr.lower(), r"retain|cleanup|unfinished|managed")

        def remove_retained_workspace():
            if b_worker.exists():
                self.f.git(self.f.target, "worktree", "remove", "--force", str(b_worker))

        self.addCleanup(remove_retained_workspace)

    def test_public_owner_takeover_refuses_prepared_candidate_before_integration(self):
        self.bind(single=True)
        attempt = self.claim("A")["A"]
        packet = self.start("A", attempt)
        workspace = Path(packet["context"]["workspace"])
        self.collect("A", self.launch("A"))
        value = self.prepared_input("A")
        self.assertEqual(self.head(), self.f.initial)
        self.assertEqual(value["integration"]["expected_target"], self.f.initial)
        self.assertTrue(workspace.exists())

        # The child accepts a public ownership handoff while the worker is
        # stopped.  The old bridge binding must not integrate its positive
        # W/T/I candidate before the child rejects that stale owner.
        binding = self.binding()
        fixture.chain._node(binding, "takeover", {
            "oldOwner": binding["owner"], "newOwner": binding["owner"] + "-replacement",
            "confirmed_stopped": True, "reason": "fixture ownership handoff",
        })
        before_head = self.head()
        before_ledger = self.f.ledger_bytes()
        before_worktrees = self.f.git(self.f.target, "worktree", "list", "--porcelain")
        for operation, input_value in (
            ("prepare", {"attempt": attempt, "confirmed_stopped": True}),
            ("done", value),
        ):
            refused = self.call(operation, input_value, ok=False)
            self.assertIn("owner", refused.stderr)
            self.assertEqual(self.head(), before_head)
            self.assertEqual(self.f.ledger_bytes(), before_ledger)
            self.assertEqual(self.f.git(self.f.target, "worktree", "list", "--porcelain"), before_worktrees)
        self.assertFalse(any(row["event"]["kind"] == "integration_result"
                             and row["event"]["data"].get("attempt") == attempt
                             for row in self.bridge_events()))

    def test_public_owner_takeover_refuses_serial_start_before_workspace_allocation(self):
        self.bind(mode="serial", single=True)
        attempt = self.claim("A")["A"]
        value = self.f.start_value("A", attempt, base=self.head())
        value["write_scope"] = ["chain_add.py"]
        self.takeover()

        self.assert_owner_refusal("start", value)
        kinds = [row["event"]["kind"] for row in self.bridge_events()]
        self.assertNotIn("serial_workspace_creation_intent", kinds)
        self.assertNotIn("allocation_intent", kinds)
        self.assertNotIn("start_intent", kinds)

    def test_public_owner_takeover_refuses_accepted_cleanup_before_removal(self):
        self.bind(single=True)
        attempt = self.claim("A")["A"]
        packet = self.start("A", attempt)
        worker = Path(packet["context"]["workspace"])
        self.collect("A", self.launch("A"))
        value = self.prepared_input("A")
        helper = fixture.chain._chain_git()
        with patch.object(helper, "remove_worker", side_effect=ValueError("fixture removal refusal")):
            accepted = fixture.chain._settle(self.f.run, self.binding(), value)
        self.assertEqual(accepted["outcome"], "accepted")
        self.assertTrue(worker.exists())

        self.takeover()
        self.assert_owner_refusal("cleanup", {"attempt": attempt, "confirmed_stopped": True})
        self.assertTrue(worker.exists())

    def test_public_owner_takeover_refuses_superseded_cleanup_before_removal(self):
        self.bind(mode="serial", single=True)
        old_attempt = self.claim("A")["A"]
        old_packet = self.start("A", old_attempt, serial=True)
        old_worker = Path(old_packet["context"]["workspace"])
        self.collect("A", self.launch("A"))
        receipt = fixture.chain._node(self.binding(), "receipt", {"attempt": old_attempt})
        proof = self.f.write("owner-retired-rejection.json", {"passed": False, "checks": ["fixture rejection"]})
        rejected = self.call("done", {"attempt": old_attempt, "confirmed_stopped": True,
            "verification": {"receipt_sha256": receipt["sha256"], "passed": False,
                "reason": "Independent fixture rejection", "evidence": {
                    "path": str(proof), "sha256": fixture.digest(proof)}}})
        self.assertEqual(rejected["outcome"], "rejected")
        self.call("retry", {"attempt": old_attempt, "confirmed_stopped": True,
                            "reason": "Replacement needs a fresh stopped workspace"})
        replacement = self.claim("A")["A"]
        self.start("A", replacement, serial=True)
        self.complete_step("A")
        self.assertTrue(old_worker.exists())

        self.takeover()
        self.assert_owner_refusal("cleanup", {"attempt": old_attempt, "confirmed_stopped": True,
                                                "disposition": "superseded",
                                                "reason": "Replacement independently accepted"})
        self.assertTrue(old_worker.exists())

    def test_public_owner_takeover_refuses_finish_before_audit_receipt(self):
        self.bind(single=True)
        attempt = self.claim("A")["A"]
        self.start("A", attempt)
        self.complete_step("A")
        self.takeover()
        proof = self.f.write("owner-finish.json", {"passed": True, "commit": self.head(),
                            "checks": ["combined generated-code output"]})

        self.assert_owner_refusal("finish", {"commit": self.head(), "confirmed_stopped": True,
                                               "verification": {"path": str(proof),
                                                                "sha256": fixture.digest(proof)}})
        kinds = [row["event"]["kind"] for row in self.bridge_events()]
        self.assertNotIn("finish_intent", kinds)
        self.assertNotIn("finish_result", kinds)

    def test_cleanup_failure_does_not_repeat_acceptance_or_task(self):
        self.bind(single=True)
        attempt = self.claim("A")["A"]
        self.start("A", attempt)
        self.collect("A", self.launch("A"))
        value = self.prepared_input("A")
        helper = fixture.chain._chain_git()
        with patch.object(helper, "remove_worker", side_effect=ValueError("fixture removal refusal")):
            output = fixture.chain._settle(self.f.run, self.binding(), value)
        self.assertEqual(output["outcome"], "accepted")
        self.assertEqual(self.f.child_record(attempt)["status"], "accepted")
        head = self.head()
        worker = Path(self.packets["A"]["context"]["workspace"])
        self.assertTrue(worker.exists())
        pending = self.call("pending")
        self.assertIn(attempt, json.dumps(pending))
        cleanup_route = self.call("next")
        self.assertEqual([(row["step"], row["attempt"])
                          for row in self.action_rows(cleanup_route, "cleanup")], [("A", attempt)])
        self.assertFalse(any(row["action"] in {"finish", "start", "launch", "execute", "prepare", "verify"}
                             for row in cleanup_route["navigation"]["actions"]),
                         "an accepted cleanup retry cannot become a new execution or finish grant")
        proof = self.f.write("premature-final.json", {"passed": True, "commit": head})
        self.call("finish", {"commit": head, "confirmed_stopped": True,
                  "verification": {"path": str(proof), "sha256": fixture.digest(proof)}}, ok=False)
        still_pending = self.call("next")
        self.assertEqual([row["attempt"] for row in self.action_rows(still_pending, "cleanup")], [attempt])
        cleaned = self.call("cleanup", {"attempt": attempt, "confirmed_stopped": True})
        self.assertEqual([row["action"] for row in cleaned["navigation"]["actions"]], ["finish"])
        self.assertFalse(worker.exists())
        self.assertEqual(self.head(), head)
        self.assertEqual(len(self.f.terminal_events(attempt)), 1)
        self.finish()

    def test_accepted_dependency_releases_successor_while_cleanup_is_pending(self):
        self.bind()
        attempts = self.claim("A", "B")
        a_packet = self.start("A", attempts["A"])
        self.start("B", attempts["B"])
        a, b = self.launch("A"), self.launch("B")
        self.collect("A", a)
        a_value = self.prepared_input("A")
        helper = fixture.chain._chain_git()
        with patch.object(helper, "remove_worker", side_effect=ValueError("fixture removal refusal")):
            accepted = fixture.chain._settle(self.f.run, self.binding(), a_value)
        self.assertEqual(accepted["outcome"], "accepted")
        self.assertIn(attempts["A"], accepted["lifecycle"]["cleanup_pending"])
        a_worker = Path(a_packet["context"]["workspace"])
        self.assertTrue(a_worker.exists())
        self.assertIn("C", accepted["ready"])
        next_after_accepted = self.call("next")
        next_actions = next_after_accepted["navigation"]["actions"]
        c_claim_index = next(index for index, row in enumerate(next_actions)
                             if row["action"] == "claim" and row["steps"] == ["C"])
        b_collect_index = next(index for index, row in enumerate(next_actions)
                               if row["action"] == "collect" and row["attempt"] == attempts["B"])
        self.assertLess(c_claim_index, b_collect_index)
        self.assertEqual([row["attempt"] for row in self.action_rows(next_after_accepted, "cleanup")],
                         [attempts["A"]])

        c_attempt = self.claim("C")["C"]
        c_packet = self.start("C", c_attempt)
        self.assertTrue(a_worker.exists())
        self.assertEqual([item["step"] for item in c_packet["dependencies"]], ["A"])
        dependency = c_packet["dependencies"][0]
        self.assertEqual(dependency["handoff"]["archived_path"], self.imports["A"]["handoff"]["archived_path"])
        self.assertTrue(Path(dependency["handoff"]["archived_path"]).is_file())
        self.assertNotEqual(dependency["handoff"]["archived_path"],
                            str(a_worker / ".shiploop-handoff" / attempts["A"] / "handoff.json"))

        c = self.launch("C")
        self.assertTrue(a_worker.exists())
        self.assertIn(attempts["A"], self.call("pending")["lifecycle"]["cleanup_pending"])
        self.assertIsNone(b.poll())
        self.assertIsNone(c.poll())
        self.collect("B", b)
        self.prepare_and_done("B")
        self.collect("C", c)
        self.prepare_and_done("C")
        self.start("J", self.claim("J")["J"])
        self.complete_step("J")
        self.assertTrue(a_worker.exists())
        self.assertEqual(len(self.f.terminal_events(attempts["A"])), 1)
        self.assertEqual(sum(row["event"]["kind"] == "integration_result"
                             and row["event"]["data"].get("attempt") == attempts["A"]
                             for row in self.bridge_events()), 1)
        head_before_cleanup = self.head()
        self.call("cleanup", {"attempt": attempts["A"], "confirmed_stopped": True})
        self.assertFalse(a_worker.exists())
        self.assertEqual(self.head(), head_before_cleanup)
        self.finish()

    def test_crash_after_target_update_recovers_without_duplicate_merge(self):
        self.bind(single=True)
        attempt = self.claim("A")["A"]
        self.start("A", attempt)
        self.collect("A", self.launch("A"))
        value = self.prepared_input("A")
        original = fixture.chain._append
        def crash_before_receipt(chain_dir, event_id, kind, data, **kwargs):
            if kind == "integration_result":
                raise OSError("fixture interruption after target update")
            return original(chain_dir, event_id, kind, data, **kwargs)
        with patch.object(fixture.chain, "_append", side_effect=crash_before_receipt):
            with self.assertRaises((OSError, ValueError)):
                fixture.chain._settle(self.f.run, self.binding(), value)
        self.assertEqual(self.head(), value["integration"]["candidate_commit"])
        self.assertNotEqual(self.f.child_record(attempt)["status"], "accepted")
        recovered = self.call("done", value)
        cleaned = self.run_deferred_managed_cleanup("A", recovered)
        self.assertIsNotNone(cleaned)
        self.assertFalse(cleaned["pending"])
        self.assertEqual(len(self.f.terminal_events(attempt)), 1)
        self.assertFalse(Path(self.packets["A"]["context"]["workspace"]).exists())
        self.finish()

    def test_unresolved_integration_blocks_sibling_until_exact_recovery(self):
        self.bind()
        attempts = self.claim("A", "B")
        for step in ("A", "B"):
            self.start(step, attempts[step])
            self.collect(step, self.launch(step))
        a_value = self.prepared_input("A")
        b_value = self.prepared_input("B")
        initial = self.head()
        helper = fixture.chain._chain_git()
        with patch.object(helper, "fast_forward", side_effect=ValueError("fixture target write interruption")):
            with self.assertRaises(fixture.chain.ChainError):
                fixture.chain._settle(self.f.run, self.binding(), a_value)
        self.assertEqual(self.head(), initial)
        self.assertNotEqual(self.f.child_record(attempts["A"])["status"], "accepted")
        events_after_failure = self.bridge_events()
        self.assertTrue(any(row["event"]["kind"] == "integration_intent"
                            and row["event"]["data"]["attempt"] == attempts["A"]
                            for row in events_after_failure))
        self.assertFalse(any(row["event"]["kind"] == "integration_result"
                             and row["event"]["data"]["attempt"] == attempts["A"]
                             for row in events_after_failure))

        before_b = self.f.ledger_bytes()
        for operation, value in (
            ("prepare", {"attempt": attempts["B"], "confirmed_stopped": True}),
            ("done", b_value),
        ):
            refused = self.call(operation, value, ok=False)
            self.assertIn("unresolved integration intent", refused.stderr)
            self.assertEqual(self.head(), initial)
            self.assertEqual(self.f.ledger_bytes(), before_b)
        recovery = self.call("next")
        self.assertEqual(recovery["lifecycle"]["unresolved_integration"]["attempt"], attempts["A"])
        self.assertEqual([item["action"] for item in recovery["navigation"]["actions"]],
                         ["recover-integration"])
        self.assertEqual(recovery["navigation"]["actions"][0]["attempt"], attempts["A"])

        accepted = self.call("done", a_value)
        self.assertEqual(accepted["outcome"], "accepted")
        after_a = self.head()
        child_before_replay = self.f.child_state_path().read_bytes()
        ledger_before_replay = self.f.ledger_bytes()
        replay = self.call("done", a_value)
        self.assertEqual(replay["outcome"], "accepted")
        self.assertEqual(self.head(), after_a)
        self.assertEqual(self.f.child_state_path().read_bytes(), child_before_replay)
        self.assertEqual(self.f.ledger_bytes(), ledger_before_replay)
        self.assertEqual(len(self.f.terminal_events(attempts["A"])), 1)
        a_cleanup = self.run_deferred_managed_cleanup("A", replay)
        self.assertIsNotNone(a_cleanup)
        self.assertFalse(a_cleanup["pending"])

        stale = self.call("done", b_value, ok=False)
        self.assertTrue(any(word in stale.stderr.lower() for word in ("target", "stale", "head")), stale.stderr)
        self.assertEqual(self.head(), after_a)
        self.assertNotEqual(self.f.child_record(attempts["B"])["status"], "accepted")
        self.prepare_and_done("B")
        self.start("C", self.claim("C")["C"])
        self.complete_step("C")
        self.start("J", self.claim("J")["J"])
        self.complete_step("J")
        self.finish()

    def test_rejected_retry_retains_managed_workspace_without_merging_bad_code(self):
        self.bind(single=True)
        old_attempt = self.claim("A")["A"]
        old_packet = self.start("A", old_attempt)
        old_workspace = Path(old_packet["context"]["workspace"])
        proc = self.launch("A")
        # Inject an adversarial result after the worker's self-check. Parent
        # verification must reject the actual code despite its success report.
        (old_workspace / "chain_add.py").write_text("def add(left, right):\n    return left - right\n")
        self.collect("A", proc)
        old_archive = Path(self.imports["A"]["handoff"]["archived_path"])
        old_archive_bytes = old_archive.read_bytes()
        rejected_commit = self.source_commits["A"]
        observed = subprocess.run([sys.executable, "-B", "-c",
            "from chain_add import add; assert add(2,3)==5"], cwd=old_workspace,
            capture_output=True, text=True)
        self.assertNotEqual(observed.returncode, 0)
        receipt = fixture.chain._node(self.binding(), "receipt", {"attempt": old_attempt})
        proof = self.f.write("rejected-code.json", {"passed": False, "stderr": observed.stderr})
        rejected = self.call("done", {"attempt": old_attempt, "confirmed_stopped": True,
            "verification": {"receipt_sha256": receipt["sha256"], "passed": False,
                "reason": "Independent add behavior failed", "evidence": {
                    "path": str(proof), "sha256": fixture.digest(proof)}}})
        self.assertEqual(rejected["outcome"], "rejected")
        self.assertEqual(self.head(), self.f.initial)
        rejected_route = self.call("next")
        self.assertEqual([row["attempt"] for row in self.action_rows(rejected_route, "retry")], [old_attempt])
        self.assertFalse(any(row["action"] in {"prepare", "verify", "recover-import"}
                             for row in rejected_route["navigation"]["actions"]),
                         "a terminal rejected attempt must route to retry before any new candidate work")
        cleanup = {"attempt": old_attempt, "confirmed_stopped": True,
                   "disposition": "superseded", "reason": "Replacement independently accepted"}
        self.call("cleanup", cleanup, ok=False)
        self.call("retry", {"attempt": old_attempt, "confirmed_stopped": True,
                            "reason": "Correct independently observed arithmetic failure"})
        self.start("A", self.claim("A")["A"])
        self.complete_step("A")
        # Managed helpers have no non-integrated close receipt. The old worker
        # remains retained even after its replacement is accepted, rather than
        # letting ShipLoop use the retired caller-worktree cleanup path.
        (old_workspace / "unpreserved.txt").write_text("retain me\n")
        refusal = self.call("cleanup", cleanup, ok=False)
        self.assertRegex(refusal.stderr.lower(), r"retain|managed|superseded")
        self.assertTrue(old_workspace.exists(), refusal.stderr)
        (old_workspace / "unpreserved.txt").unlink()
        self.assertEqual(old_archive.read_bytes(), old_archive_bytes)
        self.assertEqual(self.f.git(self.f.target, "rev-parse", old_packet["ask_agent_workspace"]["branch"]),
                         rejected_commit)
        self.assertNotEqual(subprocess.run(["git", "merge-base", "--is-ancestor", rejected_commit, self.head()],
            cwd=self.f.target, capture_output=True).returncode, 0)
        self.assertEqual(self.f.child_record(old_attempt)["status"], "retried")
        proof = self.f.write("retained-superseded-final.json", {"passed": True, "commit": self.head()})
        blocked_finish = self.call("finish", {
            "commit": self.head(), "confirmed_stopped": True,
            "verification": {"path": str(proof), "sha256": fixture.digest(proof)},
        }, ok=False)
        self.assertRegex(blocked_finish.stderr.lower(), r"retain|cleanup|unfinished|managed")

        def remove_retained_workspace():
            if old_workspace.exists():
                self.f.git(self.f.target, "worktree", "remove", "--force", str(old_workspace))

        self.addCleanup(remove_retained_workspace)

    def test_serial_rejected_retry_shares_managed_retention_boundary(self):
        self.bind(mode="serial", single=True)
        old_attempt = self.claim("A")["A"]
        old_packet = self.start("A", old_attempt, serial=True)
        old_workspace = Path(old_packet["context"]["workspace"])
        self.collect("A", self.launch("A"))
        old_commit = self.source_commits["A"]
        old_allocation = fixture.chain._per_step_allocation(self.bridge_events(), old_attempt)
        self.assertEqual(old_allocation["adoption"], "ask-agent-managed-workspace")
        self.assertEqual(old_packet["executor"]["kind"], "main-context")
        receipt = fixture.chain._node(self.binding(), "receipt", {"attempt": old_attempt})
        proof = self.f.write("serial-retired-rejection.json", {"passed": False,
                            "checks": ["fixture rejection before retry"]})
        rejected = self.call("done", {"attempt": old_attempt, "confirmed_stopped": True,
            "verification": {"receipt_sha256": receipt["sha256"], "passed": False,
                "reason": "Independent fixture rejection", "evidence": {
                    "path": str(proof), "sha256": fixture.digest(proof)}}})
        self.assertEqual(rejected["outcome"], "rejected")
        self.call("retry", {"attempt": old_attempt, "confirmed_stopped": True,
                            "reason": "Replacement uses a fresh serial workspace"})

        replacement = self.claim("A")["A"]
        self.start("A", replacement, serial=True)
        self.complete_step("A")
        self.assertTrue(old_workspace.exists())
        retained = self.call("cleanup", {"attempt": old_attempt, "confirmed_stopped": True,
                                          "disposition": "superseded",
                                          "reason": "Replacement independently accepted and integrated"}, ok=False)
        self.assertRegex(retained.stderr.lower(), r"retain|managed|superseded")
        self.assertTrue(old_workspace.exists())
        self.assertEqual(self.f.git(self.f.target, "rev-parse", old_packet["ask_agent_workspace"]["branch"]), old_commit)
        self.assertNotEqual(subprocess.run(["git", "merge-base", "--is-ancestor", old_commit, self.head()],
            cwd=self.f.target, capture_output=True).returncode, 0)

        def remove_retained_workspace():
            if old_workspace.exists():
                self.f.git(self.f.target, "worktree", "remove", "--force", str(old_workspace))

        self.addCleanup(remove_retained_workspace)

    def test_positive_done_requires_workspace_in_independent_evidence_before_mutation(self):
        self.bind(single=True)
        attempt = self.claim("A")["A"]
        packet = self.start("A", attempt)
        workspace = Path(packet["context"]["workspace"])
        self.collect("A", self.launch("A"))
        correct = self.prepared_input("A")
        proof_path = Path(correct["verification"]["evidence"]["path"])
        original = proof_path.read_bytes()

        def assert_refusal(value, message="workspace"):
            before_head = self.head()
            before_ledger = self.f.ledger_bytes()
            before_child = self.f.child_state_path().read_bytes()
            refused = self.call("done", value, ok=False)
            self.assertIn(message, refused.stderr)
            self.assertEqual(self.head(), before_head)
            self.assertEqual(self.f.ledger_bytes(), before_ledger)
            self.assertEqual(self.f.child_state_path().read_bytes(), before_child)
            self.assertTrue(workspace.exists())

        for supplied_step in ("A", "B"):
            assert_refusal(dict(correct, step=supplied_step), "step")

        missing = json.loads(json.dumps(correct))
        proof = json.loads(original)
        del proof["integration"]["workspace"]
        proof_path.write_text(json.dumps(proof) + "\n")
        missing["verification"]["evidence"]["sha256"] = fixture.digest(proof_path)
        assert_refusal(missing)

        proof_path.write_bytes(original)
        wrong = json.loads(json.dumps(correct))
        proof = json.loads(original)
        proof["integration"]["workspace"] = str(self.f.primary)
        proof_path.write_text(json.dumps(proof) + "\n")
        wrong["verification"]["evidence"]["sha256"] = fixture.digest(proof_path)
        assert_refusal(wrong)

        proof_path.write_bytes(original)
        accepted = self.call("done", correct)
        self.assertEqual(accepted["outcome"], "accepted")
        cleaned = self.run_deferred_managed_cleanup("A", accepted)
        self.assertIsNotNone(cleaned)
        self.assertFalse(cleaned["pending"])
        self.assertFalse(workspace.exists())

    def test_import_handoff_recovers_after_report_and_delete_receipt_crashes(self):
        self.bind()
        attempts = self.claim("A", "B")
        for step in ("A", "B"):
            self.start(step, attempts[step])
        results = {step: self.finish_worker(step, self.launch(step)) for step in ("A", "B")}
        requests = {
            step: {"attempt": attempts[step], "confirmed_stopped": True,
                   "handoff": {"path": results[step]["handoff"], "sha256": results[step]["sha256"]}}
            for step in ("A", "B")
        }
        binding = self.binding()
        append = fixture.chain._append

        def crash_after_report(chain_dir, event_id, kind, data, **kwargs):
            if kind == "handoff_reported":
                raise OSError("fixture interruption after parent report")
            return append(chain_dir, event_id, kind, data, **kwargs)

        with patch.object(fixture.chain, "_append", side_effect=crash_after_report):
            with self.assertRaises(OSError):
                fixture.chain._import_handoff(self.f.run, binding, requests["A"])
        first_receipt = fixture.chain._node(binding, "receipt", {"attempt": attempts["A"]})
        self.assertTrue(Path(results["A"]["handoff"]).exists())
        kinds = [row["event"]["kind"] for row in self.bridge_events()]
        self.assertIn("handoff_archived", kinds)
        self.assertNotIn("handoff_reported", kinds)
        self.assertNotIn("handoff_import_result", kinds)

        replayed_a = self.call("import-handoff", requests["A"])
        self.assertEqual(replayed_a["receipt"]["sha256"], first_receipt["sha256"])
        self.assertFalse(Path(results["A"]["handoff"]).exists())
        events = self.bridge_events()
        self.assertEqual(sum(row["event"]["kind"] == "handoff_reported"
                             and row["event"]["data"].get("attempt") == attempts["A"] for row in events), 1)
        self.assertEqual(sum(row["event"]["kind"] == "handoff_import_result"
                             and row["event"]["data"].get("attempt") == attempts["A"] for row in events), 1)

        def crash_after_delete(chain_dir, event_id, kind, data, **kwargs):
            if kind == "handoff_files_removed":
                raise OSError("fixture interruption after imported file deletion")
            return append(chain_dir, event_id, kind, data, **kwargs)

        with patch.object(fixture.chain, "_append", side_effect=crash_after_delete):
            with self.assertRaises(OSError):
                fixture.chain._import_handoff(self.f.run, binding, requests["B"])
        second_receipt = fixture.chain._node(binding, "receipt", {"attempt": attempts["B"]})
        self.assertFalse(Path(results["B"]["handoff"]).exists())
        events = self.bridge_events()
        self.assertTrue(any(row["event"]["kind"] == "handoff_reported"
                            and row["event"]["data"].get("attempt") == attempts["B"] for row in events))
        self.assertFalse(any(row["event"]["kind"] == "handoff_files_removed"
                             and row["event"]["data"].get("attempt") == attempts["B"] for row in events))

        replayed_b = self.call("import-handoff", requests["B"])
        self.assertEqual(replayed_b["receipt"]["sha256"], second_receipt["sha256"])
        events = self.bridge_events()
        self.assertEqual(sum(row["event"]["kind"] == "handoff_reported"
                             and row["event"]["data"].get("attempt") == attempts["B"] for row in events), 1)
        self.assertEqual(sum(row["event"]["kind"] == "handoff_files_removed"
                             and row["event"]["data"].get("attempt") == attempts["B"] for row in events), 1)
        self.assertEqual(sum(row["event"]["kind"] == "handoff_import_result"
                             and row["event"]["data"].get("attempt") == attempts["B"] for row in events), 1)

    def test_archive_corruption_blocks_prepare_and_final_audit_after_worker_removal(self):
        self.bind(single=True)
        attempt = self.claim("A")["A"]
        self.start("A", attempt)
        self.collect("A", self.launch("A"))
        archived = Path(self.imports["A"]["archives"][0]["archived_path"])
        original = archived.read_bytes()
        archived.chmod(0o644)
        archived.write_text("changed after import\n")
        archived.chmod(0o444)
        self.call("prepare", {"attempt": attempt, "confirmed_stopped": True}, ok=False)
        self.assertEqual(self.head(), self.f.initial)
        archived.chmod(0o644)
        archived.write_bytes(original)
        archived.chmod(0o444)
        self.prepare_and_done("A")
        archived.parent.chmod(0o755)
        archived.unlink()
        archived.parent.chmod(0o555)
        proof = self.f.write("missing-archive-final.json", {"passed": True, "commit": self.head()})
        self.call("finish", {"commit": self.head(), "confirmed_stopped": True,
            "verification": {"path": str(proof), "sha256": fixture.digest(proof)}}, ok=False)
        archived.parent.chmod(0o755)
        archived.write_bytes(original)
        archived.chmod(0o444)
        archived.parent.chmod(0o555)
        self.finish()

    def test_crash_after_child_acceptance_recovers_contribution_once(self):
        self.bind(single=True)
        attempt = self.claim("A")["A"]
        self.start("A", attempt)
        self.collect("A", self.launch("A"))
        value = self.prepared_input("A")
        original = fixture.chain._append
        def crash_before_contribution(chain_dir, event_id, kind, data, **kwargs):
            if kind == "contribution_recorded":
                raise OSError("fixture interruption before contribution publication")
            return original(chain_dir, event_id, kind, data, **kwargs)
        with patch.object(fixture.chain, "_append", side_effect=crash_before_contribution):
            with self.assertRaises((OSError, ValueError)):
                fixture.chain._settle(self.f.run, self.binding(), value)
        self.assertEqual(self.f.child_record(attempt)["status"], "accepted")
        recovered = self.call("done", value)
        cleaned = self.run_deferred_managed_cleanup("A", recovered)
        self.assertIsNotNone(cleaned)
        self.assertFalse(cleaned["pending"])
        self.assertEqual(len(self.f.terminal_events(attempt)), 1)
        self.finish()

    def test_crash_after_removal_recovers_cleanup_receipt(self):
        self.bind(single=True)
        attempt = self.claim("A")["A"]
        self.start("A", attempt)
        self.collect("A", self.launch("A"))
        value = self.prepared_input("A")
        original = fixture.chain._append
        def crash_before_cleanup_receipt(chain_dir, event_id, kind, data, **kwargs):
            if kind == "cleanup_result":
                raise OSError("fixture interruption after worktree removal")
            return original(chain_dir, event_id, kind, data, **kwargs)

        accepted = self.call("done", value)
        self.assertEqual(accepted["outcome"], "accepted")
        workspace = Path(self.packets["A"]["context"]["workspace"])
        self.assertTrue(workspace.exists())
        with patch.object(fixture.chain, "_append", side_effect=crash_before_cleanup_receipt):
            with self.assertRaises((OSError, ValueError)):
                fixture.chain._per_step_cleanup_attempt(
                    self.f.run, self.binding(), attempt, confirmed_stopped=True,
                )
        self.assertFalse(workspace.exists())
        cleaned = self.call("cleanup", {"attempt": attempt, "confirmed_stopped": True})
        self.assertFalse(cleaned["pending"])
        self.assertEqual(len(self.f.terminal_events(attempt)), 1)
        self.finish()


if __name__ == "__main__":
    unittest.main(verbosity=2)
