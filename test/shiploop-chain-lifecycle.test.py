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

    def start(self, step, attempt, *, serial=False):
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
            self.call("launched", {"attempt": attempt, "handle": {"host": "deterministic-process-fixture", "id": step}})
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
        proc.stdin.write("release\n")
        proc.stdin.flush()
        result = self.read_json_line(proc)
        self.assertEqual(proc.wait(timeout=15), 0, proc.stderr.read())
        self.assertEqual(result["phase"], "completed")
        self.source_commits[step] = result["commit"]
        imported = self.call("import-handoff", {"attempt": self.packets[step]["attempt"],
            "confirmed_stopped": True, "handoff": {"path": result["handoff"], "sha256": result["sha256"]}})
        self.imports[step] = imported["import"]
        return imported

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
            self.complete_step(step)
            self.assertIsNone(self.f.child_record(attempt).get("handle"))
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
