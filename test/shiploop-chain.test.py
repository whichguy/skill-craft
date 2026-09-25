#!/usr/bin/env python3
"""Public-CLI composition with real Git and pinned real dispatcher code.

Native handles, worker results and the prerequisite ShipLoop/Improve traversal
are synthetic. This suite does not launch an LLM or qualify host callbacks.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from shiploop_chain_support import (
    CLI,
    ChainFixture,
    SERIAL_FIXTURE,
    digest,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/shiploop/scripts"
sys.path.insert(0, str(SCRIPTS))
import shiploop_navigator as nav
import shiploop_store as store
import shiploop_chain_ledger as chain_ledger
import shiploop_chain as chain


class ChainIntegrationTests(ChainFixture):
    def test_dispatcher_has_one_state_file_and_views_store_no_completion_copy(self):
        self.select_dispatcher(SERIAL_FIXTURE)
        self.bind()
        authority = self.child_state_path()
        self.assertEqual(authority.name, "plan-dispatcher-state.json")
        self.assertFalse((authority.parent / "state.json").exists())
        self.assertNotIn("completion", self.child_state())
        before = self.run_bytes()
        self.assert_completion(self.call("pending"), [], ["A", "B", "C", "J"])
        self.call("history")
        self.call("next")
        self.assertEqual(self.run_bytes(), before)
        self.claim(["A"])
        self.assertEqual(self.child_state()["steps"]["A"]["status"], "claimed")
        self.assertFalse((authority.parent / "state.json").exists())
        # The audit is inspectable, but cannot recreate a missing authority.
        authority.unlink()
        before = self.run_bytes()
        self.call("history")
        self.call("pending", ok=False)
        self.assertEqual(self.run_bytes(), before)

    def test_legacy_dispatcher_state_file_refuses_reads_and_mutation_without_fallback(self):
        self.select_dispatcher(SERIAL_FIXTURE)
        self.bind()
        authority = self.child_state_path()
        self.assertEqual(authority.name, "plan-dispatcher-state.json")
        legacy = authority.with_name("state.json")
        legacy.write_bytes(authority.read_bytes())
        for content in (authority.read_bytes(), b"not JSON\n"):
            with self.subTest(canonical=content[:20]):
                authority.write_bytes(content)
                before = self.run_bytes()
                before_head = self.git(self.target, "rev-parse", "HEAD")
                for operation, value in (("pending", None), ("next", None), ("claim", {"steps": ["A"]})):
                    result = self.call(operation, value, ok=False)
                    self.assertIn("legacy Plan Dispatcher state.json runs are not supported", result.stderr)
                self.assertEqual(self.run_bytes(), before)
                self.assertEqual(self.git(self.target, "rev-parse", "HEAD"), before_head)
        authority.unlink()
        before = self.run_bytes()
        for operation, value in (("pending", None), ("claim", {"steps": ["A"]})):
            result = self.call(operation, value, ok=False)
            self.assertIn("legacy Plan Dispatcher state.json runs are not supported", result.stderr)
        self.assertEqual(self.run_bytes(), before)
        self.assertFalse(authority.exists())

    def test_history_and_pending_are_read_only_current_views(self):
        self.bind()
        before = self.run_bytes()
        history = self.call("history")
        self.assertEqual(history["sequence"], len(history["events"]))
        self.assertEqual([row["event"]["seq"] for row in history["events"]],
                         list(range(1, history["sequence"] + 1)))
        self.assertTrue(all(row["event"]["recorded_at"].endswith("Z") for row in history["events"]))
        self.assertNotIn("completion", history)  # An audit does not validate live child execution.
        pending = self.call("pending")
        self.assertEqual(pending["ready"], ["A", "B"])
        self.assertEqual([(row["id"], row["status"], row["waiting_for"]) for row in pending["pending"]],
                         [("A", "ready", []), ("B", "ready", []),
                          ("C", "waiting", ["A"]), ("J", "waiting", ["B", "C"])])
        self.assertEqual(pending["capacity"], {"limit": 2, "reserved": 0, "available": 2})
        self.assertNotIn("actions", pending)
        self.assertEqual(self.call("pending"), pending)
        self.assertEqual(self.call("history"), history)
        for operation in ("history", "pending"):
            self.call(operation, {}, ok=False)
        self.assertEqual(self.run_bytes(), before)

    def test_pending_tracks_claim_launch_receipt_acceptance_rejection_and_retry(self):
        self.bind()
        attempts = self.claim(["A", "B"])
        pending = self.call("pending")
        self.assertEqual([row["status"] for row in pending["pending"]],
                         ["claimed", "claimed", "waiting", "waiting"])
        self.assertEqual(pending["capacity"]["available"], 0)
        started = self.call("start", self.start_value("A", attempts["A"]))
        self.packets["A"] = started["packet"]
        self.assertEqual(self.call("pending")["pending"][0]["status"], "launching")
        self.call("launched", {"attempt": attempts["A"], "handle": {"host": "synthetic", "id": "A"}})
        self.assertEqual(self.call("pending")["pending"][0]["status"], "running")
        proof = self.contribute("A")
        before = self.run_bytes()
        self.assertEqual(self.call("pending")["pending"][0]["status"], "receipt")
        self.assertEqual(self.call("pending")["pending"][2]["waiting_for"], ["A"])
        self.assertEqual(self.run_bytes(), before)
        self.call("done", proof)
        pending = self.call("pending")
        self.assertEqual([row["id"] for row in pending["pending"]], ["B", "C", "J"])
        self.assertEqual(pending["ready"], ["C"])
        self.assert_completion(pending, ["A"], ["B", "C", "J"])
        self.start("B", attempts["B"], base=self.git(self.target, "rev-parse", "HEAD"))
        self.call("done", self.reject_contribution("B", "BLOCKED"))
        pending = self.call("pending")
        self.assertEqual(pending["pending"][0]["status"], "rejected")
        self.assertEqual(pending["pending"][0]["recovery"], "retry")
        self.assertEqual(pending["pending"][-1]["waiting_for"], ["B", "C"])
        self.call("retry", {"attempt": attempts["B"], "confirmed_stopped": True, "reason": "Fixture retry"})
        self.assertEqual(self.call("pending")["ready"], ["B", "C"])
        events = [row["event"] for row in self.call("history")["events"]]
        self.assertTrue(any(event["kind"] == "settle_result" and event["data"]["outcome"] == "rejected"
                            for event in events))
        self.assertTrue(any(event["kind"] == "retry_result" for event in events))

    def test_serial_pending_reports_local_execution_and_empty_completion(self):
        self.select_dispatcher(SERIAL_FIXTURE)
        self.graph = self.write("graph.json", {"version": 1, "steps": [{"id": "A", "deps": [],
            "contract": {"task": "Implement A", "ready": [], "done": ["A verified"]}}]})
        self.bind(capacity=None, mode="serial")
        attempt = self.claim(["A"])["A"]
        self.serial_start("A", attempt)
        pending = self.call("pending")
        self.assertEqual(pending["pending"][0]["status"], "running")
        self.assertEqual(pending["pending"][0]["recovery"], "resume")
        self.assertEqual(pending["capacity"], {"limit": 1, "reserved": 1, "available": 0})
        proof = self.contribute("A")
        self.assertEqual(self.call("pending")["pending"][0]["recovery"], "verify")
        self.call("done", proof)
        before = self.run_bytes()
        pending = self.call("pending")
        self.assertTrue(pending["complete"])
        self.assertEqual(pending["pending"], [])
        self.assert_completion(pending, ["A"], [])
        self.assertEqual(self.run_bytes(), before)

    def test_history_survives_child_drift_and_views_allow_indexed_past_actions(self):
        self.complete_single_chain()
        self.parent_complete(ok=True)
        # Implement is not an Improve checkpoint: the producer result advances.
        state = store.read_record(self.run / "state.md")
        self.assertNotEqual(nav.current_action(state)["id"], self.action)
        before = self.run_bytes()
        history = self.call("history")
        self.assertTrue(history["shiploop_chain"]["finished"])
        self.assertEqual(self.call("pending")["pending"], [])
        self.call("claim", {"steps": ["A"]}, ok=False)
        self.assertEqual(self.run_bytes(), before)
        with (self.dispatcher / "scripts/dispatch.js").open("a") as handle:
            handle.write("\nthrow new Error('Query must not execute drifted child');\n")
        self.child_state_path().unlink()
        before = self.run_bytes()
        self.assertEqual(self.call("history"), history)
        self.call("pending", ok=False)
        self.assertEqual(self.run_bytes(), before)

    def test_views_refuse_corrupt_ledger_and_never_repair_private_links(self):
        self.bind()
        directory = self.run / "chains" / self.action / "events"
        event = next(directory.glob("*.md"))
        private = directory / ".shiploop-chain-ledger-test.tmp"
        os.link(event, private)
        before = self.run_bytes()
        for operation in ("history", "pending"):
            self.call(operation, ok=False)
        self.assertEqual(self.run_bytes(), before)
        self.assertEqual(event.stat().st_nlink, 2)
        self.call("next")
        self.assertFalse(private.exists())
        self.assertEqual(event.stat().st_nlink, 1)
        with event.open("a") as handle:
            handle.write("malformed tail\n")
        before = self.run_bytes()
        for operation in ("history", "pending"):
            self.call(operation, ok=False)
        self.assertEqual(self.run_bytes(), before)

    def test_views_do_not_recover_parent_transactions_or_create_locks(self):
        self.bind()
        def crash(_phase, _index):
            raise RuntimeError("Synthetic interruption")
        with self.assertRaises(RuntimeError):
            store.transaction(self.run, {"query-probe-1.md": "first", "query-probe-2.md": "second"}, fault=crash)
        before = self.run_bytes()
        for operation in ("history", "pending"):
            self.assertIn("explicit recovery", self.call(operation, ok=False).stderr)
        self.assertFalse((self.run / "query-probe-2.md").exists())
        self.assertEqual(self.run_bytes(), before)
        self.call("next")
        self.assertEqual((self.run / "query-probe-2.md").read_text(), "second")
        lock = self.run / ".lock"
        lock.unlink()
        for operation in ("history", "pending"):
            self.call(operation, ok=False)
        self.assertFalse(lock.exists())
        lock.symlink_to(self.run / "state.md")
        for operation in ("history", "pending"):
            self.assertIn("non-symlink", self.call(operation, ok=False).stderr)
        lock.unlink()
        os.mkfifo(lock)
        for operation in ("history", "pending"):
            self.assertIn("regular", self.call(operation, ok=False).stderr)

    def test_views_preserve_package_path_refusal(self):
        for operation in ("history", "pending"):
            result = subprocess.run([sys.executable, "-B", str(CLI), "chain", operation,
                                     "--run-dir", str(SCRIPTS.parent), "--action", self.action],
                                    text=True, capture_output=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("refusing path inside skill package", result.stderr)

    def test_pending_rejects_malformed_child_snapshots(self):
        self.bind()
        binding = store.read_record(self.run / "chains" / self.action / "binding.md")
        good = self.call("next")
        before = self.run_bytes()
        mutations = [{"revision": value} for value in (None, True, -1, "0", 1.5)]
        mutations += [{"ready": ["missing"]}, {"ready": ["A", "A"]},
                      {"ready": ["A"]}, {"complete": True}, {"accepted": ["A"]},
                      {"ready": ["B"], "active": [{"step": "A", "status": []}]},
                      {"ready": ["B"], "active": [{"step": "A", "status": "running",
                        "attempt": "test-attempt", "recovery": []}]}]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                snapshot = dict(good, **mutation)
                with patch.object(chain, "_node", return_value=snapshot):
                    with self.assertRaises(chain.ChainError):
                        chain._pending_response(self.run, binding)
        del good["revision"]
        with patch.object(chain, "_node", return_value=good):
            with self.assertRaises(chain.ChainError):
                chain._pending_response(self.run, binding)
        self.assertEqual(self.run_bytes(), before)

    def crash_after(self, operation, value, *, boundary="node", node_operation=None):
        self.counter += 1
        request = self.write(f"crash-{self.counter}.json", value)
        if boundary == "node":
            hook = ("original = bridge._node\n"
                    "def crash(binding, operation, *args, **kwargs):\n"
                    "    result = original(binding, operation, *args, **kwargs)\n"
                    f"    if operation == {(node_operation or operation)!r}: os._exit(73)\n"
                    "    return result\n"
                    "bridge._node = crash\n")
        else:
            hook = ("import shiploop_chain_git as chain_git\n"
                    "original = chain_git.fast_forward\n"
                    "def crash(*args, **kwargs):\n"
                    "    original(*args, **kwargs)\n"
                    "    os._exit(73)\n"
                    "chain_git.fast_forward = crash\n")
        bootstrap = "import os, runpy, sys\nimport shiploop_chain as bridge\n" + hook
        bootstrap += "sys.argv = sys.argv[1:]\nrunpy.run_path(sys.argv[0], run_name='__main__')\n"
        p = subprocess.run([sys.executable, "-B", "-c", bootstrap, str(CLI), "chain", operation,
            "--run-dir", str(self.run), "--action", self.action, "--input", str(request)],
            env={**os.environ, "PYTHONPATH": str(SCRIPTS)}, text=True, capture_output=True, timeout=30)
        self.assertEqual(p.returncode, 73, p.stdout + p.stderr)

    def assert_producer_advanced_past_finished_chain(self):
        """Implement parks no Improve child: completion advances and keeps the binding."""
        state = store.read_record(self.run / "state.md")
        self.assertNotEqual(nav.current_stage(state), "implement")
        self.assertNotEqual(nav.current_action(state)["id"], self.action)
        self.assertIsNone(state["active_improve"])
        self.assertNotIn(self.action, state["improve_results"])
        self.assertIn(self.action, state["chain_bindings"])
        self.assertTrue((self.run / "chains" / self.action / "binding.md").is_file())
        cold = subprocess.run(
            [sys.executable, "-B", str(CLI), "next", "--run-dir", str(self.run)],
            cwd=self.primary, text=True, capture_output=True,
        )
        self.assertEqual(cold.returncode, 0, cold.stderr)
        self.assertNotIn("Chain recovery:", cold.stdout)
        self.assertNotIn("Current action: Improve the completed implement result.", cold.stdout)
        return state

    def test_serial_managed_full_diamond_executes_in_main_context_before_finish(self):
        self.select_dispatcher(SERIAL_FIXTURE)
        bound = self.bind(capacity=None, mode="serial")
        self.assert_completion(bound, [], ["A", "B", "C", "J"])
        binding = store.read_record(self.run / "chains" / self.action / "binding.md")
        self.assertEqual(binding["mode"], "serial")
        self.assertEqual(binding["capacity"], 1)
        accepted = []

        for step in ("A", "B", "C", "J"):
            before = self.call("next")
            self.assert_completion(before, accepted, [name for name in ("A", "B", "C", "J")
                                                     if name not in accepted])
            self.assertEqual(before["ready"][0], step)
            attempt = self.claim([step])[step]
            self.assertLessEqual(len(self.call("next")["active"]), 1)
            started = self.serial_start(
                step, attempt, base=self.git(self.target, "rev-parse", "HEAD"),
                integration=step == "J",
            )
            record = self.child_record(attempt)
            self.assertEqual(record["status"], "running")
            self.assertIsNone(record["handle"])
            self.assertEqual(record["executor"], started["packet"]["executor"])
            self.assertEqual(record["executor"]["kind"], "main-context")
            self.assertIsInstance(record["executor"]["id"], str)
            self.assertTrue(record["executor"]["id"])
            self.assertNotIn("native_handle", started["packet"])
            self.assertLessEqual(len(self.call("next")["active"]), 1)
            self.parent_complete()  # Child work is not a parent terminal result.
            settled = self.call("done", self.contribute(step, integration=step == "J"))
            accepted.append(step)
            self.assertEqual(settled["outcome"], "accepted")
            self.assert_completion(settled, accepted, [name for name in ("A", "B", "C", "J")
                                                        if name not in accepted])
            self.assertEqual(self.git(self.target, "rev-parse", "HEAD"), self.commits[step])

        self.assertTrue(self.call("next")["complete"])
        self.parent_complete()  # All child acceptance still cannot complete the navigator action.
        self.assertFalse(any(row["event"]["kind"].startswith("launched_")
                             for row in chain_ledger.read_events(
                                 self.run / "chains" / self.action / "events")))
        records = self.child_state()["attempts"]
        self.assertEqual({record["status"] for record in records.values()}, {"accepted"})
        self.assertTrue(all(record["handle"] is None for record in records.values()))

        proof = self.write("serial-combined.json", {"passed": True, "commit": self.commits["J"]})
        finish = {"commit": self.commits["J"], "confirmed_stopped": True,
                  "verification": {"path": str(proof), "sha256": digest(proof)}}
        self.cleanup_accepted_workers()
        self.call("finish", finish)
        self.assertEqual(self.git(self.target, "rev-parse", "HEAD"), self.commits["J"])
        self.assertEqual(self.git(self.primary, "rev-parse", "HEAD"), self.initial)
        for packet in self.packets.values():
            workspace = Path(packet["context"]["workspace"]).resolve()
            self.assertNotIn(self.target, workspace.parents)
            self.assertTrue(workspace.is_relative_to(self.parent.resolve()))
        self.parent_complete(ok=True)
        self.assert_producer_advanced_past_finished_chain()

    def test_legacy_serial_helper_refuses_fresh_context_bind_before_writes(self):
        initial_state = (self.run / "state.md").read_bytes()
        # A dispatcher package without the planning-context helper is an old release.
        (self.dispatcher / "scripts/planning-context.js").unlink()
        refused = self.bind(capacity=None, mode="serial", ok=False)
        self.assertIn("planning-context.js", refused.stderr)
        self.assertEqual((self.run / "state.md").read_bytes(), initial_state)
        self.assertFalse((self.run / "chains").exists())

    def assert_context_boundary_preserves_chain_mode(self, mode):
        state_path = self.run / "state.md"
        binding_path = self.run / "chains" / self.action / "binding.md"
        before = (state_path.read_bytes(), binding_path.read_bytes())
        self.assertEqual(store.read_record(binding_path)["mode"], mode)
        state = store.read_record(state_path)
        self.assertIsNone(state.get("active_improve"))
        fresh = nav.render(None, self.run, state)
        cold = subprocess.run(
            [sys.executable, "-B", str(CLI), "next", "--run-dir", str(self.run)],
            cwd=self.primary, text=True, capture_output=True,
        )
        self.assertEqual(cold.returncode, 0, cold.stderr)
        rule = (
            "parallel chains retain their capacity and bypass this serial context boundary"
            if mode == "parallel" else
            "serial chains execute in the main context without spawning workers"
        )
        for packet in (fresh, cold.stdout):
            normalized = " ".join(packet.split())
            self.assertIn("Chain recovery:", packet)
            self.assertIn(rule, normalized)
            self.assertIn("Both modes recover the existing attempt, never rerun start.", normalized)
        self.assertEqual((state_path.read_bytes(), binding_path.read_bytes()), before)

    def test_current_binding_defaults_to_parallel(self):
        self.bind(capacity=None)
        binding_path = self.run / "chains" / self.action / "binding.md"
        binding = store.read_record(binding_path)
        self.assertEqual(binding["schema"], "shiploop-chain-binding/v6")
        self.assertEqual(binding["mode"], "parallel")
        self.assertEqual(binding["capacity"], 2)
        self.assertIn("planning_context", binding)

        recovered = self.call("next")
        self.assertEqual(recovered["shiploop_chain"]["mode"], "parallel")
        self.assert_completion(recovered, [], ["A", "B", "C", "J"])
        self.assert_context_boundary_preserves_chain_mode("parallel")

    def test_replay_without_mode_keeps_the_recorded_serial_mode(self):
        self.bind(capacity=1, mode="serial")
        binding_path = self.run / "chains" / self.action / "binding.md"
        recorded = binding_path.read_bytes()
        # Before 0.20.0 an omitted --mode meant parallel and this replay failed.
        replayed = self.bind(capacity=1)
        self.assertEqual(replayed["shiploop_chain"]["mode"], "serial")
        self.assertEqual(binding_path.read_bytes(), recorded)
        self.bind(capacity=1, mode="parallel", ok=False)

    def test_serial_mode_capacity_and_native_launch_are_guarded(self):
        initial_state = (self.run / "state.md").read_bytes()

        self.select_dispatcher(SERIAL_FIXTURE)
        self.bind(capacity=2, mode="serial", ok=False)
        self.assertEqual((self.run / "state.md").read_bytes(), initial_state)
        self.assertFalse((self.run / "chains" / self.action / "dispatcher").exists())
        self.bind(capacity=None, mode="serial")
        binding_path = self.run / "chains" / self.action / "binding.md"
        immutable_binding = binding_path.read_bytes()
        self.bind(capacity=2, mode="parallel", ok=False)
        self.assertEqual(binding_path.read_bytes(), immutable_binding)
        self.call("claim", {"steps": ["A", "B"]}, ok=False)

        a = self.claim(["A"])["A"]
        self.serial_start("A", a)
        before_child = self.child_state_path().read_bytes()
        before_ledger = self.ledger_bytes()
        self.call("launched", {"attempt": a, "handle": {"host": "synthetic", "id": "A"}}, ok=False)
        self.assertEqual(self.child_state_path().read_bytes(), before_child)
        self.assertEqual(self.ledger_bytes(), before_ledger)

    def test_serial_start_replay_and_cold_recover_keep_the_executor_without_a_handle(self):
        self.select_dispatcher(SERIAL_FIXTURE)
        self.bind(capacity=None, mode="serial")
        a = self.claim(["A"])["A"]
        value = self.start_value("A", a)
        first = self.call("start", value)
        self.assertEqual(first["action"], "execute")
        self.packets["A"] = first["packet"]
        record = self.child_record(a)
        self.assertIsNone(record["handle"])
        self.assertEqual(record["executor"], first["packet"]["executor"])
        before_state = self.child_state_path().read_bytes()
        replay = self.call("start", value)
        self.assertEqual(replay["action"], "reconcile")
        self.assertEqual(replay["packet"]["attempt"], a)
        self.assertEqual(self.child_state_path().read_bytes(), before_state)
        start_results = [row["event"] for row in chain_ledger.read_events(
            self.run / "chains" / self.action / "events")
            if row["event"]["kind"] == "start_result"
            and row["event"]["data"].get("attempt") == a]
        self.assertEqual([event["data"]["action"] for event in start_results], ["execute", "reconcile"])
        after_replay_ledger = self.ledger_bytes()

        recovered = self.call("next")
        self.assert_completion(recovered, [], ["A", "B", "C", "J"])
        active = [action for action in recovered["actions"] if action.get("attempt") == a]
        self.assertEqual([action["action"] for action in active], ["resume"])
        self.assertEqual(self.child_state_path().read_bytes(), before_state)
        self.assertEqual(self.ledger_bytes(), after_replay_ledger)
        self.assertIsNone(self.child_record(a)["handle"])
        self.assert_context_boundary_preserves_chain_mode("serial")

    def test_serial_done_reconciles_once_and_preserves_terminal_history(self):
        self.select_dispatcher(SERIAL_FIXTURE)
        self.bind(capacity=None, mode="serial")
        a = self.claim(["A"])["A"]
        self.serial_start("A", a)
        verification = self.contribute("A")
        self.crash_after("done", verification, node_operation="settle")
        accepted_state = self.child_state_path().read_bytes()
        self.assertEqual(self.child_record(a)["status"], "accepted")
        self.assertEqual(self.terminal_events(a), [])

        reconciled = self.call("done", verification)
        self.assertEqual(reconciled["outcome"], "accepted")
        self.assert_completion(reconciled, ["A"], ["B", "C", "J"])
        self.assertEqual(self.child_state_path().read_bytes(), accepted_state)
        self.assertEqual(len(self.terminal_events(a)), 1)

        c = self.claim(["C"])["C"]
        self.serial_start("C", c, base=self.commits["A"])
        before_state = self.child_state_path().read_bytes()
        before_revision = self.child_state()["revision"]
        before_ledger = self.ledger_bytes()
        repeated_done = self.call("done", verification)
        self.assert_completion(repeated_done, ["A"], ["B", "C", "J"])
        self.assertEqual(self.child_state_path().read_bytes(), before_state)
        self.assertEqual(self.child_state()["revision"], before_revision)
        self.assertEqual(self.ledger_bytes(), before_ledger)
        self.assertEqual(len(self.terminal_events(a)), 1)

        conflict = json.loads(json.dumps(verification))
        conflict["verification"]["reason"] = "Conflicting independent proof"
        self.call("done", conflict, ok=False)
        self.assertEqual(self.child_state_path().read_bytes(), before_state)
        self.assertEqual(len(self.terminal_events(a)), 1)

    def test_serial_rejected_and_blocked_receipts_stay_not_done_and_stale_success_cannot_accept_retry(self):
        self.select_dispatcher(SERIAL_FIXTURE)
        self.bind(capacity=None, mode="serial")
        a1 = self.claim(["A"])["A"]
        self.serial_start("A", a1)
        successful = self.contribute("A")
        rejected = json.loads(json.dumps(successful))
        rejected["verification"]["passed"] = False
        first = self.call("done", rejected)
        self.assertEqual(first["outcome"], "rejected")
        self.assert_completion(first, [], ["A", "B", "C", "J"])
        self.assertEqual(self.child_record(a1)["status"], "rejected")
        proof = self.write("unfinished-serial-finish.json", {"passed": True, "commit": self.initial})
        finish = {"commit": self.initial, "confirmed_stopped": True,
                  "verification": {"path": str(proof), "sha256": digest(proof)}}
        self.call("finish", finish, ok=False)
        self.assertEqual(self.git(self.target, "rev-parse", "HEAD"), self.initial)

        self.call("retry", {"attempt": a1, "confirmed_stopped": True, "reason": "Synthetic failed verification"})
        a2 = self.claim(["A"])["A"]
        self.serial_start("A", a2)
        blocked = self.reject_contribution("A", "BLOCKED")
        second = self.call("done", blocked)
        self.assertEqual(second["outcome"], "rejected")
        self.assert_completion(second, [], ["A", "B", "C", "J"])
        self.assertEqual(self.child_record(a2)["status"], "rejected")
        self.call("finish", finish, ok=False)
        self.assertEqual(self.git(self.target, "rev-parse", "HEAD"), self.initial)

        self.call("retry", {"attempt": a2, "confirmed_stopped": True, "reason": "Synthetic blocked receipt"})
        a3 = self.claim(["A"])["A"]
        self.serial_start("A", a3)
        before_state = self.child_state_path().read_bytes()
        self.call("done", successful, ok=False)
        self.assertEqual(self.child_state_path().read_bytes(), before_state)
        self.assertEqual(self.child_record(a3)["status"], "running")
        self.assert_completion(self.call("next"), [], ["A", "B", "C", "J"])

    def test_fanout_eager_successor_join_verified_return_and_parent_guard(self):
        self.assertEqual(set(self.bind()["ready"]), {"A", "B"})
        saved = (self.run / "state.md").read_bytes()
        self.parent_complete()
        self.parent_complete("repeat")
        self.assertEqual((self.run / "state.md").read_bytes(), saved)
        claims = self.claim(["A", "B"])
        self.start("A", claims["A"])
        self.start("B", claims["B"])
        self.assertEqual(len(self.call("next")["active"]), 2)
        verification = self.contribute("A")
        self.assertNotIn("C", self.call("next")["ready"])
        self.call("done", verification)
        now = self.call("next")
        self.assertIn("C", now["ready"])
        self.assertNotIn("J", now["ready"])
        self.assertTrue(any(a["step"] == "B" for a in now["active"]))
        c = self.claim(["C"])["C"]
        self.start("C", c, self.commits["A"])
        self.call("done", self.contribute("C"))
        self.call("done", self.contribute("B"))
        j = self.claim(["J"])["J"]
        self.start("J", j, self.git(self.target, "rev-parse", "HEAD"), integration=True)
        self.call("done", self.contribute("J", integration=True))
        self.assertTrue(self.call("next")["complete"])
        self.parent_complete()  # Child graph completion alone is insufficient.
        proof = self.write("combined-verification.json", {"commit": self.commits["J"], "passed": True,
                           "checks": ["A, B and C contents and exact commit ancestry"]})
        finish = {"commit": self.commits["J"], "confirmed_stopped": True,
                  "verification": {"path": str(proof), "sha256": digest(proof)}}
        self.cleanup_accepted_workers()
        self.call("finish", finish)
        self.call("finish", finish)
        self.assertEqual(self.git(self.target, "rev-parse", "HEAD"), self.commits["J"])
        self.assertEqual(self.git(self.primary, "rev-parse", "HEAD"), self.initial)
        for step, packet in self.packets.items():
            path = Path(packet["context"]["workspace"]).resolve()
            self.assertNotIn(self.target, path.parents)
            self.assertTrue(path.is_relative_to(self.parent.resolve()))
        self.parent_complete(ok=True)
        self.assert_producer_advanced_past_finished_chain()

    def test_missing_binding_and_stale_action_fail_closed(self):
        self.bind()
        binding = self.run / "chains" / self.action / "binding.md"
        binding.rename(binding.with_suffix(".retained"))
        self.parent_complete()
        self.call("next", ok=False)
        self.action = "nav-another-action"
        self.call("claim", {"steps": ["A"]}, ok=False)

    def test_capacity_and_replayed_start_cannot_launch_twice(self):
        self.bind(capacity=1)
        self.call("claim", {"steps": ["A", "B"]}, ok=False)
        a = self.claim(["A"])["A"]
        self.start("A", a)
        self.call("claim", {"steps": ["B"]}, ok=False)
        packet = self.packets["A"]
        retry = {"attempt": a, "base_commit": self.initial, "write_scope": ["A.txt"],
                 "resources": [], "ready_evidence": packet["context"]["ready_evidence"]}
        before_worktrees = self.git(self.target, "worktree", "list", "--porcelain")
        output = self.call("start", retry)
        self.assertEqual(output["action"], "reconcile")
        self.assertEqual(output["packet"], packet)
        self.assertEqual(self.git(self.target, "worktree", "list", "--porcelain"), before_worktrees)
        self.assertEqual(self.call("next")["active"][0]["attempt"], a)

    def test_settlement_requires_native_stoppage_attestation(self):
        self.bind()
        a = self.claim(["A"])["A"]
        self.start("A", a)
        verification = self.contribute("A")
        verification["confirmed_stopped"] = False
        self.call("done", verification, ok=False)
        self.assertNotIn("C", self.call("next")["ready"])
        verification["confirmed_stopped"] = True
        self.call("done", verification)
        self.call("done", verification)  # exact replay is inert

    def test_selected_package_drift_blocks_mutations(self):
        self.bind()
        with (self.ask / "SKILL.md").open("a") as f:
            f.write("\nChanged selected execution guidance.\n")
        self.call("claim", {"steps": ["A"]}, ok=False)

    def test_ordinary_dependent_base_must_include_supplier(self):
        self.bind()
        a = self.claim(["A"])["A"]
        self.start("A", a)
        self.call("done", self.contribute("A"))
        c = self.claim(["C"])["C"]
        ready = self.write("bad-base-ready.json", {"ready": True})
        self.call("start", {"attempt": c, "base_commit": self.initial, "write_scope": ["C.txt"],
             "resources": [], "ready_evidence": {"path": str(ready), "sha256": digest(ready)}}, ok=False)

    def test_import_handoff_replay_does_not_rewrite_prior_event_files(self):
        self.bind()
        a = self.claim(["A"])["A"]
        self.start("A", a)
        self.contribute("A")
        events = self.run / "chains" / self.action / "events"
        before = {p.name: p.read_bytes() for p in events.glob("*.md")}
        replayed = self.call("import-handoff", self.import_inputs["A"])
        self.assertEqual((replayed["attempt"], replayed["import"]["status"]), (a, "SUCCEEDED"))
        for name, content in before.items():
            self.assertEqual((events / name).read_bytes(), content)
        self.assertNotIn("C", self.call("next")["ready"])

    def test_retired_verbs_and_bind_lifecycle_flag_are_not_accepted(self):
        self.bind()
        a = self.claim(["A"])["A"]
        before = self.run_bytes()
        for operation in ("recover", "settle", "observe"):
            refused = self.call(operation, {"attempt": a, "confirmed_stopped": True}, ok=False)
            self.assertIn("invalid choice", refused.stderr)
        refused = self.call("bind", ok=False, extra=(
            "--graph", str(self.graph), "--dispatcher-skill", str(self.dispatcher / "SKILL.md"),
            "--ask-agent-skill", str(self.ask / "SKILL.md"), "--worktree-parent", str(self.parent),
            "--lifecycle", "per-step"))
        self.assertIn("unrecognized arguments: --lifecycle", refused.stderr)
        self.assertEqual(self.run_bytes(), before)

    def test_non_implementation_binding_is_rejected(self):
        state = nav.new_state(str(self.target), "Still intake",
                              delegation="ask-agent")
        nav.save(self.run, state)
        self.action = nav.current_action(state)["id"]
        self.call("bind", ok=False, extra=("--graph", str(self.graph),
            "--dispatcher-skill", str(self.dispatcher / "SKILL.md"), "--ask-agent-skill", str(self.ask / "SKILL.md"),
            "--worktree-parent", str(self.parent)))
        self.assertFalse((self.run / "chains").exists())

    def test_unfinished_chain_blocks_halt_and_improve_import_but_can_pause(self):
        self.bind()
        for verb in ("halt", "improve-complete"):
            argv = [sys.executable, "-B", str(CLI), verb, "--run-dir", str(self.run)]
            if verb == "halt":
                argv += ["--reason", "Synthetic stop"]
            else:
                argv += ["--action", self.action, "--result", str(self.run / "inbox" / (self.action + "-improve.md"))]
            p = subprocess.run(argv, text=True, capture_output=True)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("chain is unfinished", p.stderr + p.stdout)
            # The refusal prints the exact resume callback, not a removed verb.
            self.assertIn("chain next --run-dir " + str(self.run) + " --action " + self.action,
                          p.stderr + p.stdout)
            self.assertNotIn("chain recover", p.stderr + p.stdout)
        p = subprocess.run([sys.executable, "-B", str(CLI), "pause", "--run-dir", str(self.run),
                            "--reason", "Synthetic pause"], text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(set(self.call("next")["ready"]), {"A", "B"})
        self.call("claim", {"steps": ["A"]}, ok=False)

    def test_producer_repeat_after_finished_chain_starts_a_new_implementation(self):
        self.complete_single_chain()
        old_action = self.action
        self.parent_complete("repeat", ok=True)
        state = store.read_record(self.run / "state.md")
        self.assertEqual(nav.current_stage(state), "implement")
        self.assertEqual(state["status"], "active")
        self.assertIsNone(state["active_improve"])
        self.action = nav.current_action(state)["id"]
        self.assertNotEqual(self.action, old_action)
        self.assertIn(old_action, state["chain_bindings"])
        self.assertTrue((self.run / "chains" / old_action / "binding.md").is_file())
        # The archived chain does not block a fresh chain on the new action.
        self.assertEqual(self.bind()["ready"], ["A"])
        state = store.read_record(self.run / "state.md")
        self.assertEqual(set(state["chain_bindings"]), {old_action, self.action})

    def test_producer_blocked_keeps_finished_chain_and_parent_incomplete(self):
        self.complete_single_chain()
        old_action = self.action
        self.parent_complete("blocked", ok=True)
        state = store.read_record(self.run / "state.md")
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(nav.current_stage(state), "implement")
        self.assertIsNone(state["active_improve"])
        self.assertIn(old_action, state["chain_bindings"])
        self.assertTrue((self.run / "chains" / old_action / "binding.md").is_file())

    def test_claim_and_retry_reconcile_after_process_exit_loses_response(self):
        self.bind()
        self.crash_after("claim", {"steps": ["A"]})
        a = self.claim(["A"])["A"]
        self.start("A", a)
        verification = self.contribute("A")
        verification["verification"]["passed"] = False
        self.call("done", verification)
        retry = {"attempt": a, "confirmed_stopped": True, "reason": "Synthetic failed check"}
        self.crash_after("retry", retry)
        self.call("retry", retry)
        self.assertIn("A", self.call("next")["ready"])
        self.assertNotEqual(self.claim(["A"])["A"], a)

    def test_bad_git_result_cannot_accept_or_release_dependency(self):
        self.bind()
        a = self.claim(["A"])["A"]
        self.start("A", a)
        verification = self.contribute("A")
        worker = Path(self.packets["A"]["context"]["workspace"])
        (worker / "unfinished.txt").write_text("dirty after report\n")
        self.call("done", verification, ok=False)
        state = self.call("next")
        self.assertNotIn("C", state["ready"])
        self.assertTrue(any(row["attempt"] == a for row in state["active"]))

    def test_failed_and_wrong_commit_finish_proof_preserves_accepted_target(self):
        self.graph = self.write("graph.json", {"version": 1, "steps": [{"id": "A", "deps": [],
            "contract": {"task": "Implement A", "ready": [], "done": ["A verified"]}}]})
        self.bind()
        a = self.claim(["A"])["A"]
        self.start("A", a)
        self.call("done", self.contribute("A"))
        accepted_target = self.git(self.target, "rev-parse", "HEAD")
        self.assertEqual(accepted_target, self.commits["A"])
        for contents in ({"passed": False, "commit": self.commits["A"]},
                         {"passed": True, "commit": self.initial}, {}):
            proof = self.write("failed-combined.json", contents)
            self.call("finish", {"commit": self.commits["A"], "confirmed_stopped": True,
                "verification": {"path": str(proof), "sha256": digest(proof)}}, ok=False)
            self.assertEqual(self.git(self.target, "rev-parse", "HEAD"), accepted_target)
        proof = self.write("combined.json", {"passed": True, "commit": self.commits["A"]})
        value = {"commit": self.commits["A"], "confirmed_stopped": True,
                 "verification": {"path": str(proof), "sha256": digest(proof)}}
        self.cleanup_accepted_workers()
        self.call("finish", value)
        self.parent_complete(ok=True)

    def test_shared_external_resource_stays_reserved_until_verified_stoppage(self):
        self.bind()
        claims = self.claim(["A", "B"])
        self.start("A", claims["A"], resources=["mcp:shared-database"])
        ready = self.write("ready-B.json", {"ready": True})
        b = {"attempt": claims["B"], "base_commit": self.initial, "write_scope": ["B.txt"],
             "resources": ["mcp:shared-database"],
             "ready_evidence": {"path": str(ready), "sha256": digest(ready)}}

        before_worktrees = self.git(self.target, "worktree", "list", "--porcelain")
        before_ledger = self.ledger_bytes()

        def assert_b_remains_unallocated():
            self.assertEqual(self.git(self.target, "worktree", "list", "--porcelain"), before_worktrees)
            self.assertEqual(self.ledger_bytes(), before_ledger)
            self.assertEqual(self.child_record(claims["B"])["status"], "claimed")
            self.assertIsNone(chain._allocation(
                chain._events(self.run / "chains" / self.action), claims["B"],
            ))

        for resources, error in ((["mcp:duplicate", "mcp:duplicate"], r"duplicate"),
                                 (["   "], r"resource|nonempty")):
            invalid = json.loads(json.dumps(b))
            invalid["resources"] = resources
            refused = self.call("start", invalid, ok=False)
            self.assertRegex(refused.stderr.lower(), error)
            assert_b_remains_unallocated()

        refused = self.call("start", b, ok=False)
        self.assertIn("resource", refused.stderr.lower())
        assert_b_remains_unallocated()
        self.call("done", self.contribute("A"))
        b["base_commit"] = self.git(self.target, "rev-parse", "HEAD")
        started = self.call("start", b)
        self.assertEqual(started["action"], "launch")
        self.assertEqual(started["packet"]["context"]["base_commit"], b["base_commit"])

    def test_bad_worktree_parent_is_rejected_before_durable_binding(self):
        original = (self.run / "state.md").read_bytes()
        invalid = self.primary / ".work-trees"
        invalid.mkdir()
        self.call("bind", ok=False, extra=("--graph", str(self.graph),
            "--dispatcher-skill", str(self.dispatcher / "SKILL.md"),
            "--ask-agent-skill", str(self.ask / "SKILL.md"), "--worktree-parent", str(invalid),
            ))
        self.assertEqual((self.run / "state.md").read_bytes(), original)
        self.assertFalse((self.run / "chains").exists())

    def test_cold_implementation_packet_requires_eligible_parallel_route(self):
        cold = store.read_record(self.run / "state.md")
        before = (self.run / "state.md").read_bytes()
        packet = nav.render(None, self.run, cold)
        self.assertIn(str(SCRIPTS.parent / "references/parallel-chain.md"), packet)
        self.assertIn("Parallel-chain guide", packet)
        self.assertIn("default parallel", packet)
        self.assertIn("observed native slots", packet)
        self.assertEqual((self.run / "state.md").read_bytes(), before)


    def verify_instruction(self, result, attempt):
        # Per-step navigation is the bridge's own projection returned with each
        # mutating callback; the dispatcher's next view carries its own text.
        actions = [action for action in result["navigation"]["actions"]
                   if action.get("attempt") == attempt and action["action"] == "verify"]
        self.assertEqual(len(actions), 1)
        return " ".join(actions[0]["instruction"].split())

    def assert_parent_verify_rule(self, instruction):
        for phrase in (
            "Check the returned per-item receipt against each definition_of_done item",
            "independently rerun or inspect each item's confirmation",
            "Reject when a confirmable item failed or was not confirmed, naming the items",
            "treat it as BLOCKED for planning, not as accepted",
            "goes back to planning (plan revision or replan), not to a blind retry",
            "archived exit-criteria.json handoff file",
        ):
            self.assertIn(phrase, instruction)

    def test_step_packets_carry_exit_criteria_and_verify_carries_parent_rule(self):
        """Exit criteria live in the emitted prompts; the bridge never reruns them."""
        self.bind()
        claims = self.claim(["A", "B"])
        packet = self.start("A", claims["A"])["packet"]
        self.start("B", claims["B"])
        instructions = packet["instructions"]
        rule = chain._exit_criteria_instruction("the assignment's definition_of_done items")
        self.assertEqual(instructions.count(rule), 1)
        joined = " ".join(" ".join(instructions).split())
        for phrase in (
            "Exit criteria: the assignment's definition_of_done items are your exit criteria.",
            "Use the item's `Confirm by:` method when it has one.",
            "Never download, install, or fetch a tool, runtime, or dependency to confirm an item.",
            "leave that check failing and report the discrepancy",
            "After your last edit to any file, rerun every check in one pass; only that pass counts.",
            "change the work, not the check",
            "the same check still failing after 3 genuine fix attempts → FAILED",
            "or reported `unconfirmable` when its text already says `Confirm by: unconfirmable here`, "
            "and none failed → SUCCEEDED",
            "for an item the plan did not already mark `Confirm by: unconfirmable here`",
            "with the existing behavior kept at the conflict point",
            "`confirmed`, `inspected`, `failed`, `not_run`, or `unconfirmable`",
            "declared handoff file exit-criteria.json",
            "List it in the manifest files with its sha256",
        ):
            self.assertIn(phrase, joined)
        # A first attempt carries no prior_attempts feedback.
        self.assertNotIn("prior_attempts", joined)
        # The handoff v1 manifest contract is unchanged; the receipt is a declared file.
        self.assertEqual(packet["handoff"]["required"],
                         ["run_id", "step", "attempt", "base_commit", "status", "commit", "summary", "files"])

        repo = Path(packet["context"]["workspace"])
        (repo / "A.txt").write_text("A\n")
        self.git(repo, "add", "A.txt")
        self.git(repo, "commit", "-qm", "Implement A")
        handoff_root = repo / ".shiploop-handoff" / packet["attempt"]
        handoff_root.mkdir(parents=True, exist_ok=True)
        receipt = handoff_root / "exit-criteria.json"
        receipt.write_text(json.dumps({
            "criteria": [{"criterion": "A.txt holds A", "check": "cat A.txt",
                          "observed": "A", "level": "confirmed"}],
            "discrepancies": [], "recommendations": [],
        }) + "\n")
        handoff = handoff_root / "handoff.json"
        handoff.write_text(json.dumps({
            "schema": "shiploop-chain-handoff/v1", "run_id": packet["run_id"], "step": "A",
            "attempt": packet["attempt"], "base_commit": packet["context"]["base_commit"],
            "status": "SUCCEEDED", "commit": self.git(repo, "rev-parse", "HEAD"),
            "summary": "A confirmed; no discrepancies.",
            "files": [{"path": "exit-criteria.json", "sha256": digest(receipt)}],
        }) + "\n")
        imported = self.call("import-handoff", {
            "attempt": packet["attempt"], "confirmed_stopped": True,
            "handoff": {"path": str(handoff), "sha256": digest(handoff)},
        })
        self.assertEqual(imported["import"]["status"], "SUCCEEDED")
        self.assertIn("exit-criteria.json", json.dumps(imported))
        prepared = self.call("prepare", {"attempt": packet["attempt"], "confirmed_stopped": True})
        self.assert_parent_verify_rule(self.verify_instruction(prepared, packet["attempt"]))

        blocked = self.packets["B"]
        blocked_root = Path(blocked["context"]["workspace"]) / ".shiploop-handoff" / blocked["attempt"]
        blocked_root.mkdir(parents=True, exist_ok=True)
        blocked_receipt = blocked_root / "exit-criteria.json"
        blocked_receipt.write_text(json.dumps({
            "criteria": [{"criterion": "B runs under Node 14", "check": "node --version",
                          "observed": "node: command not found", "level": "unconfirmable"}],
            "discrepancies": [], "recommendations": ["Confirm under Node 14 where it is installed."],
        }) + "\n")
        blocked_handoff = blocked_root / "handoff.json"
        blocked_handoff.write_text(json.dumps({
            "schema": "shiploop-chain-handoff/v1", "run_id": blocked["run_id"], "step": "B",
            "attempt": blocked["attempt"], "base_commit": blocked["context"]["base_commit"],
            "status": "BLOCKED", "commit": None, "summary": "B blocked: Node 14 is absent.",
            "files": [{"path": "exit-criteria.json", "sha256": digest(blocked_receipt)}],
        }) + "\n")
        imported = self.call("import-handoff", {
            "attempt": blocked["attempt"], "confirmed_stopped": True,
            "handoff": {"path": str(blocked_handoff), "sha256": digest(blocked_handoff)},
        })
        self.assertEqual(imported["import"]["status"], "BLOCKED")
        self.assert_parent_verify_rule(self.verify_instruction(imported, blocked["attempt"]))

    def test_serial_per_step_packet_carries_exit_criteria_and_verify_carries_parent_rule(self):
        """Serial chains execute the same per-step packet in the main context."""
        self.select_dispatcher(SERIAL_FIXTURE)
        self.graph = self.write("graph.json", {"version": 1, "steps": [{"id": "A", "deps": [],
            "contract": {"task": "Implement A", "ready": [], "done": ["A verified"]}}]})
        self.bind(capacity=None, mode="serial")
        attempt = self.claim(["A"])["A"]
        packet = self.serial_start("A", attempt)["packet"]
        instructions = packet["instructions"]
        self.assertEqual(instructions.count(chain._exit_criteria_instruction(
            "the assignment's definition_of_done items")), 1)
        self.assertEqual(instructions.count(chain._EXIT_CRITERIA_HANDOFF_INSTRUCTION), 1)
        joined = " ".join(instructions)
        self.assertIn("You are executing this bounded task in the current main conversation.", joined)
        self.assertNotIn("Achieve the definition of done", joined)
        self.assertNotIn("prior_attempts", joined)
        verify = chain._serial_action_instruction("verify")[1]
        self.assertIn(chain._PARENT_VERIFY_RULE, verify)

    def test_retried_step_packet_carries_prior_attempts_and_feedback(self):
        """A retry's real per-step packet carries the dispatcher's prior_attempts and the feedback rule."""
        self.select_dispatcher(SERIAL_FIXTURE)
        self.bind(capacity=None, mode="serial")
        a1 = self.claim(["A"])["A"]
        first = self.serial_start("A", a1)["packet"]
        self.assertNotIn("prior_attempts", first)
        rejected = json.loads(json.dumps(self.contribute("A")))
        rejected["verification"]["passed"] = False
        self.assertEqual(self.call("done", rejected)["outcome"], "rejected")
        self.call("retry", {"attempt": a1, "confirmed_stopped": True, "reason": "criterion 2 failed"})
        a2 = self.claim(["A"])["A"]
        packet = self.serial_start("A", a2)["packet"]
        self.assertEqual([prior["attempt"] for prior in packet["prior_attempts"]], [a1])
        self.assertTrue(packet["prior_attempts"][0]["reason"])
        feedback = chain._prior_attempts_instructions(packet)
        self.assertEqual(len(feedback), 1)
        self.assertEqual(packet["instructions"].count(feedback[0]), 1)

    def test_replaced_instruction_lists_keep_the_prior_attempts_feedback(self):
        """A retried step's prior_attempts data arrives with the instruction to use it."""
        prior = [{"attempt": "A-1", "status": "retried", "reason": "criterion 2 failed",
                  "result": {"path": "results/A-1.json", "sha256": "0" * 64}, "verification": None}]
        feedback = chain._prior_attempts_instructions({"prior_attempts": prior})
        self.assertEqual(len(feedback), 1)
        self.assertIn("This packet's prior_attempts lists this step's earlier attempts", feedback[0])
        self.assertIn("address the named failing items first", feedback[0])
        self.assertIn("archived exit-criteria.json handoff file", feedback[0])
        self.assertEqual(chain._prior_attempts_instructions({"prior_attempts": []}), [])
        self.assertEqual(chain._prior_attempts_instructions({}), [])

class PacketReplayIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-packet-replay-")
        self.addCleanup(self.temp.cleanup)
        self.chain_dir = Path(self.temp.name)
        self.packet = {"attempt": "A-1", "native_handle": None,
                       "payload": {"ordinal": 1, "ready": False}}
        self.saved = chain._per_step_record_internal_packet(
            self.chain_dir, [], "A-1", self.packet)
        self.rows = chain_ledger.read_events(self.chain_dir / "events")
        self.before = self.ledger_bytes()

    def ledger_bytes(self):
        return {p.name: p.read_bytes() for p in (self.chain_dir / "events").glob("*.md")}

    def test_native_handle_replay_preserves_json_type(self):
        for observed, recorded in ((0, False), (False, 0), (1, True), (True, 1)):
            with self.subTest(observed=observed, recorded=recorded):
                packet = {**self.packet, "native_handle": observed}
                with self.assertRaisesRegex(chain.ChainError, "native handle conflicts"):
                    chain._per_step_record_internal_packet(
                        self.chain_dir, self.rows, "A-1", packet, native_handle=recorded)
                exact = chain._per_step_record_internal_packet(
                    self.chain_dir, self.rows, "A-1", packet, native_handle=observed)
                self.assertEqual(exact, self.saved)
                self.assertEqual(self.ledger_bytes(), self.before)

    def test_replayed_assignment_preserves_nested_json_types(self):
        for key, changed in (("ordinal", True), ("ready", 0)):
            with self.subTest(key=key):
                packet = {**self.packet, "payload": {**self.packet["payload"], key: changed}}
                with self.assertRaisesRegex(chain.ChainError, "packet drifted"):
                    chain._per_step_record_internal_packet(
                        self.chain_dir, self.rows, "A-1", packet)
                self.assertEqual(self.ledger_bytes(), self.before)
        exact = chain._per_step_record_internal_packet(
            self.chain_dir, self.rows, "A-1", self.packet)
        self.assertEqual(exact, self.saved)
        self.assertEqual(self.ledger_bytes(), self.before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
