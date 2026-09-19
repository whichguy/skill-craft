#!/usr/bin/env python3
"""Repeatable real-Git code generation/aggregation lifecycle tests.

Run: python3 -B test/shiploop-chain-lifecycle.test.py
Workers are explicitly deterministic Python processes, not native/model agents.
Native Ask-Agent qualification uses experiments/shiploop_chain/native_pilot.py.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("legacy_chain_fixture", ROOT / "test/shiploop-chain.test.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
WORKER = ROOT / "test/fixtures/chain-code-worker.py"
ASK = ROOT / "test/fixtures/ask-agent-v04"


class PerStepChainTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.ChainIntegrationTests(methodName="runTest")
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.f.select_dispatcher(fixture.SERIAL_FIXTURE)
        self.f.assert_fixture(ASK)
        shutil.rmtree(self.f.ask)
        shutil.copytree(ASK, self.f.ask)
        self.processes = []
        self.addCleanup(self.stop_processes)
        self.packets = {}
        self.source_commits = {}
        self.done_inputs = {}
        self.imports = {}

    def stop_processes(self):
        for proc in self.processes:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if stream:
                    stream.close()

    def call(self, operation, value=None, **kwargs):
        return self.f.call(operation, value, **kwargs)

    def bind(self, *, mode="parallel", single=False, ok=True):
        if single:
            graph = json.loads(self.f.graph.read_text())
            graph["steps"] = graph["steps"][:1]
            self.f.graph.write_text(json.dumps(graph) + "\n")
        return self.call("bind", ok=ok, extra=(
            "--graph", str(self.f.graph), "--dispatcher-skill", str(self.f.dispatcher / "SKILL.md"),
            "--ask-agent-skill", str(self.f.ask / "SKILL.md"), "--worktree-parent", str(self.f.parent),
            "--mode", mode))

    def head(self):
        return self.f.git(self.f.target, "rev-parse", "HEAD")

    def claim(self, *steps):
        return self.f.claim(list(steps))

    def start(self, step, attempt, *, serial=False, record_launch=True):
        base = self.head()
        names = {"A": "chain_add.py", "B": "chain_format.py", "C": "chain_sum.py", "J": "chain_report.py"}
        value = self.f.start_value(step, attempt, base=base)
        value["write_scope"] = [names[step]]
        if not serial:
            # Emulates Ask-Agent's ordinary worktree preparation with real Git.
            # The bridge must adopt this workspace, not create another.
            before = self.f.git(self.f.target, "worktree", "list", "--porcelain")
            requested = self.call("start", value)
            self.assertEqual(requested["action"], "prepare-workspace")
            self.assertEqual(self.f.git(self.f.target, "worktree", "list", "--porcelain"), before)
            workspace = self.f.parent / ("ask-agent-" + attempt)
            self.f.git(self.f.target, "worktree", "add", "-q", "-b", "ask-agent/" + attempt,
                       str(workspace), base)
            value["workspace"] = str(workspace)
        output = self.call("start", value)
        self.assertEqual(output["action"], "execute" if serial else "launch")
        packet = output["packet"]
        self.packets[step] = packet
        recovered = self.call("packet", {"attempt": attempt})["packet"]
        self.assertEqual(recovered, packet, "cold recovery must preserve the worker-only assignment")
        self.assertEqual(packet["context"]["base_commit"], base)
        for external in ("outputs", "report_argv", "report_envelope"):
            self.assertNotIn(external, packet)
        if not serial:
            self.assertEqual(Path(packet["context"]["workspace"]), workspace)
            if record_launch:
                self.call("launched", {"attempt": attempt, "handle": {
                    "host": "deterministic-process-fixture", "id": step,
                }})
        return packet

    def read_json_line(self, process):
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            self.assertTrue(selector.select(15), "code worker did not reach its barrier")
        line = process.stdout.readline()
        if not line:
            self.fail("code worker stopped: " + process.stderr.read())
        return json.loads(line)

    def launch(self, step):
        packet = self.packets[step]
        proc = subprocess.Popen([sys.executable, "-B", str(WORKER)], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.processes.append(proc)
        assignment = {"step": step, "run_id": packet["run_id"], "attempt": packet["attempt"],
                      "base_commit": packet["context"]["base_commit"],
                      "workspace": packet["context"]["workspace"]}
        proc.stdin.write(json.dumps(assignment) + "\n")
        proc.stdin.flush()
        ready = self.read_json_line(proc)
        self.assertEqual(ready["phase"], "code_ready")
        self.assertEqual(ready["cwd"], assignment["workspace"])
        return proc

    def collect(self, step, proc):
        result = self.finish_worker(step, proc)
        imported = self.call("import-handoff", {"attempt": self.packets[step]["attempt"],
            "confirmed_stopped": True, "handoff": {"path": result["handoff"], "sha256": result["sha256"]}})
        self.imports[step] = imported["import"]
        return imported

    def finish_worker(self, step, proc):
        proc.stdin.write("release\n")
        proc.stdin.flush()
        result = self.read_json_line(proc)
        self.assertEqual(proc.wait(timeout=15), 0, proc.stderr.read())
        self.assertEqual(result["phase"], "completed")
        self.source_commits[step] = result["commit"]
        return result

    def takeover(self):
        binding = self.binding()
        fixture.chain._node(binding, "takeover", {
            "oldOwner": binding["owner"], "newOwner": binding["owner"] + "-replacement",
            "confirmed_stopped": True, "reason": "fixture ownership handoff",
        })

    def assert_owner_refusal(self, operation, value):
        before_head = self.head()
        before_ledger = self.f.ledger_bytes()
        before_child = self.f.child_state_path().read_bytes()
        before_worktrees = self.f.git(self.f.target, "worktree", "list", "--porcelain")
        refused = self.call(operation, value, ok=False)
        self.assertIn("owner", refused.stderr)
        self.assertEqual(self.head(), before_head)
        self.assertEqual(self.f.ledger_bytes(), before_ledger)
        self.assertEqual(self.f.child_state_path().read_bytes(), before_child)
        self.assertEqual(self.f.git(self.f.target, "worktree", "list", "--porcelain"), before_worktrees)
        # Observability stays available to the new dispatcher owner; a stale
        # bridge may not turn a rejected mutation into a view outage.
        self.call("history")
        self.call("pending")
        self.assertEqual(self.f.ledger_bytes(), before_ledger)

    def verify(self, workspace):
        check = """from pathlib import Path
p=Path('.')
if (p/'chain_add.py').exists():
 from chain_add import add
 assert add(-4,1)==-3 and add(2,3)==5
if (p/'chain_format.py').exists():
 from chain_format import normalize
 assert normalize(' A   B ')== 'a b'
if (p/'chain_sum.py').exists():
 from chain_sum import total
 assert total([2,3,-1])==4 and total([])==0
if (p/'chain_report.py').exists():
 from chain_report import report
 assert report(' RESULT ',[2,3])=='result: 5'
"""
        result = subprocess.run([sys.executable, "-B", "-c", check], cwd=workspace,
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def prepared_input(self, step):
        attempt = self.packets[step]["attempt"]
        prepared = self.call("prepare", {"attempt": attempt, "confirmed_stopped": True})
        integration = prepared["integration"]
        self.verify(Path(self.packets[step]["context"]["workspace"]))
        # Read the immutable child receipt through its public helper.
        binding = fixture.store.read_record(self.f.run / "chains" / self.f.action / "binding.md")
        immutable = fixture.chain._node(binding, "receipt", {"attempt": attempt})
        proof = self.f.write("verified-" + step + "-" + integration["candidate_commit"] + ".json", {"passed": True, "integration": integration,
              "checks": ["actual generated Python behavior, original source ancestry, target identity"]})
        value = {"attempt": attempt, "confirmed_stopped": True,
                 "integration": integration,
                 "verification": {"receipt_sha256": immutable["sha256"], "passed": True,
                                  "reason": "Independent behavior checks on combined candidate",
                                  "evidence": {"path": str(proof), "sha256": fixture.digest(proof)}}}
        self.done_inputs[step] = value
        return value

    def prepare_and_done(self, step):
        value = self.prepared_input(step)
        integration = value["integration"]
        before = self.f.ledger_bytes()
        output = self.call("done", value)
        self.assertEqual(output["outcome"], "accepted")
        self.assertEqual(self.head(), integration["candidate_commit"])
        self.assertFalse(Path(self.packets[step]["context"]["workspace"]).exists())
        after = self.f.ledger_bytes()
        self.assertTrue(all(after.get(k) == v for k, v in before.items()))
        self.verify(self.f.target)
        return output

    def binding(self):
        return fixture.store.read_record(self.f.run / "chains" / self.f.action / "binding.md")

    def bridge_events(self):
        return fixture.chain._events(self.f.run / "chains" / self.f.action)

    def complete_step(self, step):
        proc = self.launch(step)
        self.collect(step, proc)
        return self.prepare_and_done(step)

    def finish(self):
        head = self.head()
        self.verify(self.f.target)
        proof = self.f.write("final-combined.json", {"passed": True, "commit": head,
                            "checks": ["combined generated-code output and all source ancestry"]})
        finished = self.call("finish", {"commit": head, "confirmed_stopped": True,
                  "verification": {"path": str(proof), "sha256": fixture.digest(proof)}})
        self.assertTrue(finished["complete"])
        self.assertEqual(self.f.git(self.f.primary, "rev-parse", "HEAD"), self.f.initial)
        listing = self.f.git(self.f.primary, "worktree", "list", "--porcelain")
        self.assertEqual(listing.count("worktree "), 2, listing)
        for commit in self.source_commits.values():
            self.f.git(self.f.target, "merge-base", "--is-ancestor", commit, head)
        self.assertEqual(self.call("pending")["completion"]["not_done"], [])
        return finished

    def test_parallel_code_fanout_eager_dependent_join_merges_and_removes_all_workers(self):
        self.bind()
        claims = self.claim("A", "B")
        self.start("A", claims["A"])
        self.start("B", claims["B"])
        a, b = self.launch("A"), self.launch("B")
        self.assertIsNone(a.poll())
        self.assertIsNone(b.poll())
        self.collect("A", a)
        result = self.prepare_and_done("A")
        self.assertIn("C", result["ready"])
        self.assertNotIn("J", result["ready"])
        self.assertIsNone(b.poll(), "B must still run when C is released")
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
        self.prepare_and_done("B")
        self.assertNotIn("J", self.call("next")["ready"])
        self.collect("C", c)
        self.prepare_and_done("C")
        self.start("J", self.claim("J")["J"])
        self.complete_step("J")
        self.finish()
        # All predecessor workspaces are gone; imports and graph views remain usable.
        replay = self.call("done", self.done_inputs["A"])
        self.assertEqual(replay["outcome"], "accepted")
        self.assertEqual(len(self.f.terminal_events(claims["A"])), 1)
        self.call("history")
        self.call("recover")

    def test_serial_code_graph_uses_same_integration_and_cleanup_without_native_handles(self):
        self.bind(mode="serial")
        for step in ("A", "B", "C", "J"):
            attempt = self.claim(step)[step]
            self.start(step, attempt, serial=True)
            plan = fixture.chain._per_step_allocation(self.bridge_events(), attempt)["plan"]
            self.assertIn("worker_instance", plan)
            self.complete_step(step)
            self.assertIsNone(self.f.child_record(attempt).get("handle"))
        self.finish()

    def test_serial_creation_intent_recovers_exact_workspace_after_allocation_crash(self):
        self.bind(mode="serial", single=True)
        attempt = self.claim("A")["A"]
        value = self.f.start_value("A", attempt, base=self.head())
        value["write_scope"] = ["chain_add.py"]
        original = fixture.chain._append
        helper = fixture.chain._chain_git()

        # The creation intent must survive an interruption before Git changes
        # anything.  Its exact replay may allocate the still-absent path.
        with patch.object(helper, "allocate", side_effect=OSError("fixture interruption before Git allocation")):
            with self.assertRaises(OSError):
                fixture.chain._per_step_start(self.f.run, self.binding(), value)
        events = self.bridge_events()
        creation = next(row["event"]["data"] for row in events
                        if row["event"]["kind"] == "serial_workspace_creation_intent")
        self.assertIsNone(fixture.chain._allocation(events, attempt))
        workspace = Path(creation["plan"]["path"])
        self.assertFalse(workspace.exists())
        self.assertEqual(self.call("pending")["lifecycle"]["serial_creation_pending"], [attempt])

        conflicting = json.loads(json.dumps(value))
        conflicting["resources"] = ["different"]
        refused = self.call("start", conflicting, ok=False)
        self.assertIn("creation replay", refused.stderr)
        self.assertFalse(workspace.exists())

        def crash_before_allocation_receipt(chain_dir, event_id, kind, data, **kwargs):
            if kind == "allocation_intent":
                raise OSError("fixture interruption after serial worktree allocation")
            return original(chain_dir, event_id, kind, data, **kwargs)

        # The persisted intent has no path yet, so its first replay allocates;
        # it must not mistake an absent path for an allocated recovery.
        with patch.object(helper, "recover_allocation", side_effect=AssertionError("initial allocation must not recover")):
            with patch.object(fixture.chain, "_append", side_effect=crash_before_allocation_receipt):
                with self.assertRaises(OSError):
                    fixture.chain._per_step_start(self.f.run, self.binding(), value)
        events = self.bridge_events()
        self.assertIsNone(fixture.chain._allocation(events, attempt))
        self.assertTrue(workspace.exists())
        before_worktrees = self.f.git(self.f.target, "worktree", "list", "--porcelain")
        pending = self.call("pending")
        self.assertEqual(pending["lifecycle"]["serial_creation_pending"], [attempt])
        self.assertTrue(any(item.get("action") == "recover-workspace" and item.get("attempt") == attempt
                            for item in self.call("next")["actions"]))
        retry = self.call("retry", {"attempt": attempt, "confirmed_stopped": True,
                                    "reason": "Do not orphan an unrecorded workspace"}, ok=False)
        self.assertIn("serial workspace creation", retry.stderr)
        self.assertEqual(self.f.child_record(attempt)["status"], "claimed")
        refused = self.call("start", conflicting, ok=False)
        self.assertIn("creation replay", refused.stderr)
        self.assertEqual(self.f.git(self.f.target, "worktree", "list", "--porcelain"), before_worktrees)

        output = self.call("start", value)
        self.assertEqual(output["action"], "execute")
        self.packets["A"] = output["packet"]
        self.assertEqual(self.f.git(self.f.target, "worktree", "list", "--porcelain"), before_worktrees)
        allocation = fixture.chain._per_step_allocation(self.bridge_events(), attempt)
        self.assertEqual(allocation["plan"]["path"], str(workspace))
        self.assertIn("worker_instance", allocation["plan"])
        kinds = [row["event"]["kind"] for row in self.bridge_events()]
        self.assertLess(kinds.index("serial_workspace_creation_intent"), kinds.index("allocation_intent"))
        self.complete_step("A")
        self.finish()

    def test_unsupported_ask_agent_version_refused_before_any_worker(self):
        shutil.rmtree(self.f.ask)
        shutil.copytree(ROOT / "skills/ask-agent", self.f.ask)
        # Current release fixture is 0.3.x; explicitly mutate only copied test data.
        card = self.f.ask / "SKILL.md"
        text = card.read_text()
        import re
        card.write_text(re.sub(r"(?m)^version:.*$", "version: 0.3.1", text))
        refused = self.bind(ok=False)
        self.assertIn("Ask-Agent", refused.stderr)
        self.assertIn("0.4", refused.stderr)
        self.assertEqual(self.f.git(self.f.primary, "worktree", "list", "--porcelain").count("worktree "), 2)

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
        self.verify(a_worker)
        self.verify(b_worker)
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
        self.assertFalse(a_worker.exists())
        self.verify(self.f.target)
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
        self.call("cleanup", {"attempt": attempts["B"], "confirmed_stopped": True,
                                "disposition": "superseded",
                                "reason": "Replacement independently accepted and integrated"})
        self.assertFalse(b_worker.exists())
        self.start("C", self.claim("C")["C"])
        self.complete_step("C")
        self.start("J", self.claim("J")["J"])
        self.complete_step("J")
        self.finish()

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
        proof = self.f.write("premature-final.json", {"passed": True, "commit": head})
        self.call("finish", {"commit": head, "confirmed_stopped": True,
                  "verification": {"path": str(proof), "sha256": fixture.digest(proof)}}, ok=False)
        self.call("cleanup", {"attempt": attempt, "confirmed_stopped": True})
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
        self.call("done", value)
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
        self.assertTrue(any(item.get("action") == "recover-integration" and item.get("attempt") == attempts["A"]
                            for item in recovery["actions"]))

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

    def test_rejected_retry_can_retire_old_workspace_without_merging_bad_code(self):
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
        cleanup = {"attempt": old_attempt, "confirmed_stopped": True,
                   "disposition": "superseded", "reason": "Replacement independently accepted"}
        self.call("cleanup", cleanup, ok=False)
        self.call("retry", {"attempt": old_attempt, "confirmed_stopped": True,
                            "reason": "Correct independently observed arithmetic failure"})
        self.call("cleanup", cleanup, ok=False)
        self.start("A", self.claim("A")["A"])
        self.complete_step("A")
        # Even a superseded attempt must retain unpreserved local work.
        (old_workspace / "unpreserved.txt").write_text("retain me\n")
        refusal = self.call("cleanup", cleanup, ok=False)
        self.assertTrue(old_workspace.exists(), refusal.stderr)
        (old_workspace / "unpreserved.txt").unlink()
        append = fixture.chain._append
        def crash_after_retirement(chain_dir, event_id, kind, data, **kwargs):
            if kind == "superseded_cleanup_result":
                raise OSError("fixture interruption after superseded removal")
            return append(chain_dir, event_id, kind, data, **kwargs)
        with patch.object(fixture.chain, "_append", side_effect=crash_after_retirement):
            with self.assertRaises((OSError, ValueError)):
                fixture.chain._per_step_cleanup_superseded(
                    self.f.run, self.binding(), old_attempt, cleanup["reason"])
        self.assertFalse(old_workspace.exists())
        self.call("cleanup", cleanup)
        self.assertEqual(old_archive.read_bytes(), old_archive_bytes)
        self.assertEqual(self.f.git(self.f.target, "rev-parse", "ask-agent/" + old_attempt), rejected_commit)
        self.assertNotEqual(subprocess.run(["git", "merge-base", "--is-ancestor", rejected_commit, self.head()],
            cwd=self.f.target, capture_output=True).returncode, 0)
        self.call("cleanup", cleanup)  # Idempotent retirement, never acceptance.
        self.assertEqual(self.f.child_record(old_attempt)["status"], "retried")
        self.finish()

    def test_serial_rejected_retry_retires_old_workspace_without_merging_bad_code(self):
        self.bind(mode="serial", single=True)
        old_attempt = self.claim("A")["A"]
        old_packet = self.start("A", old_attempt, serial=True)
        old_workspace = Path(old_packet["context"]["workspace"])
        self.collect("A", self.launch("A"))
        old_commit = self.source_commits["A"]
        old_plan = fixture.chain._per_step_allocation(self.bridge_events(), old_attempt)["plan"]
        self.assertNotIn("worker", old_plan)
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
        retired = self.call("cleanup", {"attempt": old_attempt, "confirmed_stopped": True,
                                         "disposition": "superseded",
                                         "reason": "Replacement independently accepted and integrated"})
        self.assertFalse(old_workspace.exists())
        self.assertFalse(retired["pending"])
        self.assertEqual(self.f.git(self.f.target, "rev-parse", old_plan["branch"]), old_commit)
        self.assertNotEqual(subprocess.run(["git", "merge-base", "--is-ancestor", old_commit, self.head()],
            cwd=self.f.target, capture_output=True).returncode, 0)
        self.finish()

    def test_positive_done_requires_workspace_in_independent_evidence_before_mutation(self):
        self.bind(single=True)
        attempt = self.claim("A")["A"]
        packet = self.start("A", attempt)
        workspace = Path(packet["context"]["workspace"])
        self.collect("A", self.launch("A"))
        correct = self.prepared_input("A")
        proof_path = Path(correct["verification"]["evidence"]["path"])
        original = proof_path.read_bytes()

        def assert_refusal(value):
            before_head = self.head()
            before_ledger = self.f.ledger_bytes()
            before_child = self.f.child_state_path().read_bytes()
            refused = self.call("done", value, ok=False)
            self.assertIn("workspace", refused.stderr)
            self.assertEqual(self.head(), before_head)
            self.assertEqual(self.f.ledger_bytes(), before_ledger)
            self.assertEqual(self.f.child_state_path().read_bytes(), before_child)
            self.assertTrue(workspace.exists())

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
        self.call("done", value)
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
        with patch.object(fixture.chain, "_append", side_effect=crash_before_cleanup_receipt):
            with self.assertRaises((OSError, ValueError)):
                fixture.chain._settle(self.f.run, self.binding(), value)
        self.assertFalse(Path(self.packets["A"]["context"]["workspace"]).exists())
        self.call("cleanup", {"attempt": attempt, "confirmed_stopped": True})
        self.assertEqual(len(self.f.terminal_events(attempt)), 1)
        self.finish()


if __name__ == "__main__":
    unittest.main(verbosity=2)
