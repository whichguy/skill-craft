#!/usr/bin/env python3
"""Real concurrent bridge callbacks; deterministic workers, not native agents."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("async_lifecycle_fixture", ROOT / "test/shiploop-chain-lifecycle.test.py")
lifecycle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lifecycle)
fixture = lifecycle.fixture


class AsyncCallbackTests(unittest.TestCase):
    def setUp(self):
        self.life = lifecycle.PerStepChainTests("runTest")
        self.life.setUp()
        self.addCleanup(self.life.doCleanups)
        self.f = self.life.f
        self.callbacks = []
        self.addCleanup(self._stop_callbacks)
        self.callback_sequence = 0

    def _stop_callbacks(self):
        for proc in self.callbacks:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if stream is not None:
                    stream.close()

    def _callback_argv(self, operation, value, label):
        self.callback_sequence += 1
        path = self.f.write(f"async-inputs/{self.callback_sequence}-{label}.json", value)
        return [sys.executable, "-B", str(fixture.CLI), "chain", operation,
                "--run-dir", str(self.f.run), "--action", self.f.action, "--input", str(path)]

    def _public_callback(self, operation, value, *, label, cwd=None):
        return subprocess.run(self._callback_argv(operation, value, label),
                              cwd=cwd or self.f.primary, text=True, capture_output=True, timeout=90)

    def _public_recover(self, *, cwd=None):
        return subprocess.run(
            [sys.executable, "-B", str(fixture.CLI), "chain", "recover",
             "--run-dir", str(self.f.run), "--action", self.f.action],
            cwd=cwd or self.f.primary, text=True, capture_output=True, timeout=90,
        )

    def _gated_callbacks(self, operation, values_by_label, *, cwd=None):
        # Hold the real run lock while both independent callers reach a pipe
        # gate. Release both before collection: no sleeps or mocked lock APIs.
        gate = ("import json,os,sys; "
                "print(json.dumps({'phase':'callback_ready','pid':os.getpid()}),flush=True); "
                "assert sys.stdin.readline().strip() == 'release'; "
                "os.execv(sys.executable,[sys.executable,*sys.argv[1:]])")
        running = {}
        with (self.f.run / ".lock").open("rb") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                for label, value in values_by_label.items():
                    argv = self._callback_argv(operation, value, label)
                    proc = subprocess.Popen([sys.executable, "-c", gate, *argv[1:]],
                                            cwd=cwd or self.f.primary, stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
                    self.callbacks.append(proc)
                    ready = self.life.read_json_line(proc)
                    self.assertEqual(ready, {"phase": "callback_ready", "pid": proc.pid})
                    running[label] = (argv, proc)
                self.assertEqual(len({proc.pid for _, proc in running.values()}), len(running))
                for _, proc in running.values():
                    self.assertIsNone(proc.poll())
                    proc.stdin.write("release\n")
                    proc.stdin.flush()
                    proc.stdin.close()
                    proc.stdin = None
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        # Drain every caller concurrently: a verbose lock holder must not fill
        # its pipe while the parent waits on a different, lock-blocked caller.
        results = {}
        with ThreadPoolExecutor(max_workers=len(running)) as pool:
            output = {label: pool.submit(proc.communicate, timeout=90)
                      for label, (_, proc) in running.items()}
            for label, (argv, proc) in running.items():
                stdout, stderr = output[label].result(timeout=100)
                results[label] = subprocess.CompletedProcess(argv, proc.returncode, stdout, stderr)
        return results

    def test_competing_done_reprepares_loser_and_concurrent_cleanup_preserves_origin(self):
        life, f = self.life, self.f
        graph = json.loads(f.graph.read_text())
        graph["steps"] = graph["steps"][:2]
        f.graph.write_text(json.dumps(graph) + "\n")
        life.bind()
        self.assertEqual(Path(life.binding()["target"]["repo"]), f.target)
        attempts = life.claim("A", "B")
        for step in ("A", "B"):
            life.start(step, attempts[step])
        workers = {step: life.launch(step) for step in ("A", "B")}
        self.assertNotEqual(workers["A"].pid, workers["B"].pid)
        self.assertTrue(all(proc.poll() is None for proc in workers.values()))
        for step, proc in workers.items():
            life.collect(step, proc)
        proofs = {step: life.prepared_input(step) for step in ("A", "B")}
        self.assertEqual({value["integration"]["expected_target"] for value in proofs.values()}, {f.initial})
        before = f.ledger_bytes()
        results = self._gated_callbacks("done", proofs)
        winners = [step for step, result in results.items() if result.returncode == 0]
        self.assertEqual(len(winners), 1, {k: (r.returncode, r.stdout, r.stderr) for k, r in results.items()})
        winner = winners[0]
        loser = next(step for step in results if step != winner)
        accepted = json.loads(results[winner].stdout)
        life.assert_navigation("done", accepted)
        self.assertEqual((accepted["outcome"], accepted["step"], accepted["attempt"]),
                         ("accepted", winner, attempts[winner]))
        self.assertIn("prepared target is stale", results[loser].stderr)
        self.assertEqual(life.head(), proofs[winner]["integration"]["candidate_commit"])
        self.assertEqual(len(f.terminal_events(attempts[winner])), 1)
        self.assertEqual(f.terminal_events(attempts[loser]), [])
        self.assertEqual(sum(row["event"]["kind"] == "integration_result" for row in life.bridge_events()), 1)
        after = f.ledger_bytes()
        self.assertTrue(all(after.get(name) == content for name, content in before.items()))
        refused = self._public_callback("done", proofs[loser], label="stale-replay")
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual(f.ledger_bytes(), after)
        previous = life.head()
        replacement = life.prepared_input(loser)
        self.assertEqual(replacement["integration"]["expected_target"], previous)
        self.assertNotEqual(replacement["integration"]["candidate_commit"], proofs[loser]["integration"]["candidate_commit"])
        self.assertEqual(life.call("done", replacement)["outcome"], "accepted")
        life.assert_contiguous_integrations((attempts[winner], attempts[loser]))
        life.verify(f.target, expected_steps=("A", "B"))
        closes = self._gated_callbacks("cleanup", {
            step: {"attempt": attempt, "confirmed_stopped": True} for step, attempt in attempts.items()
        })
        for step, result in closes.items():
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            output = json.loads(result.stdout)
            life.assert_navigation("cleanup", output)
            self.assertFalse(output["pending"])
            packet = life.packets[step]
            self.assertFalse(Path(packet["context"]["workspace"]).exists())
            close = json.loads((Path(packet["ask_agent_workspace"]["receipt"]).parent / "close.json").read_text())
            self.assertEqual(close["status"], "closed")
            self.assertTrue(close["removed"])
            self.assertEqual(close["decision"], "integrated")
            self.assertEqual(close, output["cleanup"]["close"])
            self.assertEqual(close["worktree"], packet["context"]["workspace"])
        self.assertEqual(sum(row["event"]["kind"] == "cleanup_result" for row in life.bridge_events()), 2)
        life.finish()

    def test_duplicate_callbacks_import_integrate_and_close_exactly_once(self):
        life, f = self.life, self.f
        life.bind(single=True)
        attempt = life.claim("A")["A"]
        packet = life.start("A", attempt)
        worker = life.launch("A")
        returned = life.finish_worker("A", worker)
        workspace = Path(packet["context"]["workspace"])
        before = f.ledger_bytes()
        imported_value = {"attempt": attempt, "confirmed_stopped": True,
                          "handoff": {"path": returned["handoff"], "sha256": returned["sha256"]}}

        def accept_all(operation, value):
            results = self._gated_callbacks(operation, {"first": value, "duplicate": value})
            outputs = []
            for label, result in results.items():
                self.assertEqual(result.returncode, 0, label + ": " + result.stderr + result.stdout)
                output = json.loads(result.stdout)
                life.assert_navigation(operation, output)
                self.assertEqual(output["attempt"], attempt)
                outputs.append(output)
            return outputs

        imported = accept_all("import-handoff", imported_value)
        self.assertEqual(imported[0]["import"], imported[1]["import"])
        life.imports["A"] = imported[0]["import"]
        self.assertFalse(Path(returned["handoff"]).exists())
        proof = life.prepared_input("A")
        accepted = accept_all("done", proof)
        self.assertTrue(all(output["outcome"] == "accepted" for output in accepted))
        self.assertEqual(life.head(), proof["integration"]["candidate_commit"])
        self.assertTrue(workspace.exists(), "done must defer helper cleanup")
        closed = accept_all("cleanup", {"attempt": attempt, "confirmed_stopped": True})
        self.assertTrue(all(output["pending"] is False for output in closed))
        self.assertEqual(closed[0]["cleanup"], closed[1]["cleanup"])
        self.assertFalse(workspace.exists())
        close_path = Path(packet["ask_agent_workspace"]["receipt"]).parent / "close.json"
        close_bytes = close_path.read_bytes()
        self.assertEqual(json.loads(close_bytes)["status"], "closed")

        events = life.bridge_events()
        for kind in ("handoff_import_result", "integration_result", "contribution_recorded", "cleanup_result"):
            rows = [row for row in events if row["event"]["kind"] == kind]
            self.assertEqual(len(rows), 1, kind)
        self.assertEqual(len(f.terminal_events(attempt)), 1)
        after = f.ledger_bytes()
        self.assertTrue(all(after.get(name) == content for name, content in before.items()))
        for operation, value in (("import-handoff", imported_value), ("done", proof),
                                 ("cleanup", {"attempt": attempt, "confirmed_stopped": True})):
            accept_all(operation, value)
            self.assertEqual(f.ledger_bytes(), after, operation + " replay rewrote the ledger")
            self.assertEqual(close_path.read_bytes(), close_bytes)
        life.finish()
        for artifact in life.imports["A"]["archives"]:
            self.assertEqual(fixture.digest(Path(artifact["archived_path"])), artifact["sha256"])

    def test_foreign_cwd_and_wrong_attempt_cannot_redirect_return_or_sibling_cleanup(self):
        life, f = self.life, self.f
        graph = json.loads(f.graph.read_text())
        graph["steps"] = graph["steps"][:2]
        f.graph.write_text(json.dumps(graph) + "\n")
        life.bind()
        attempts = life.claim("A", "B")
        for step in ("A", "B"):
            life.start(step, attempts[step])
        a, b = life.launch("A"), life.launch("B")
        self.assertNotEqual(a.pid, b.pid)
        self.assertIsNone(a.poll())
        self.assertIsNone(b.poll())
        workspaces = {step: Path(life.packets[step]["context"]["workspace"]) for step in ("A", "B")}
        returned = life.finish_worker("A", a)
        self.assertIsNone(b.poll())
        callback = {"attempt": attempts["A"], "confirmed_stopped": True,
                    "handoff": {"path": returned["handoff"], "sha256": returned["sha256"]}}

        def snapshot():
            return (life.head(), f.ledger_bytes(), f.child_state_path().read_bytes(),
                    f.git(f.primary, "worktree", "list", "--porcelain"))

        before = snapshot()
        refused = self._public_callback("import-handoff", {**callback, "attempt": attempts["B"]},
                                        label="wrong-attempt", cwd=workspaces["B"])
        self.assertNotEqual(refused.returncode, 0, refused.stdout)
        self.assertEqual(snapshot(), before)
        self.assertTrue(Path(returned["handoff"]).is_file())

        def accepted_callback(operation, value, label):
            result = self._public_callback(operation, value, label=label, cwd=workspaces["B"])
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            output = json.loads(result.stdout)
            life.assert_navigation(operation, output)
            return output

        imported = accepted_callback("import-handoff", callback, "valid-origin-import")
        life.imports["A"] = imported["import"]
        proof = life.prepared_input("A")
        accepted = accepted_callback("done", proof, "valid-origin-done")
        self.assertEqual(accepted["outcome"], "accepted")
        self.assertEqual(life.head(), proof["integration"]["candidate_commit"])
        self.assertEqual(f.git(f.primary, "rev-parse", "HEAD"), f.initial)

        # This only exercises recovery projection and retention while B's fixture
        # worker is alive; it does not claim a host lookup or native liveness proof.
        b_record = f.child_record(attempts["B"])
        b_handle = b_record["handle"]
        self.assertIsNotNone(b_handle)
        self.assertEqual(b_record["context"]["workspace"], str(workspaces["B"]))
        before = snapshot()
        recovery = self._public_recover(cwd=workspaces["B"])
        self.assertEqual(recovery.returncode, 0, recovery.stderr + recovery.stdout)
        recovered = json.loads(recovery.stdout)
        life.assert_navigation("recover", recovered)
        self.assertEqual(snapshot(), before)
        self.assertIsNone(b.poll())
        self.assertEqual(f.child_state()["steps"]["B"]["current_attempt"], attempts["B"])
        active_b = [item for item in recovered["active"] if item["step"] == "B"]
        self.assertEqual(len(active_b), 1)
        self.assertEqual(active_b[0]["attempt"], attempts["B"])
        self.assertEqual(active_b[0]["handle"], b_handle)
        self.assertEqual(active_b[0]["context"]["workspace"], str(workspaces["B"]))
        b_actions = [item for item in recovered["navigation"]["actions"]
                     if item.get("attempt") == attempts["B"]]
        self.assertEqual(len(b_actions), 1)
        self.assertEqual((b_actions[0]["action"], b_actions[0]["operation"]),
                         ("collect", "import-handoff"))
        for expected in (
            "TaskNotFound",
            "existing parent-pending record",
            "native status unavailable; cannot attest stopped",
            "remaining capacity",
        ):
            self.assertIn(expected, b_actions[0]["instruction"])

        life.verify(f.target, expected_steps=("A",))
        before = snapshot()
        for label, value in (
            ("active-sibling", {"attempt": attempts["B"], "confirmed_stopped": True}),
            ("unstopped-accepted", {"attempt": attempts["A"], "confirmed_stopped": False}),
        ):
            refused = self._public_callback("cleanup", value, label=label, cwd=workspaces["B"])
            self.assertNotEqual(refused.returncode, 0, refused.stdout)
            self.assertEqual(snapshot(), before)
            self.assertTrue(all(path.exists() for path in workspaces.values()))
            self.assertIsNone(b.poll())
        cleaned = accepted_callback("cleanup", {"attempt": attempts["A"], "confirmed_stopped": True},
                                    "accepted-origin-cleanup")
        self.assertFalse(cleaned["pending"])
        self.assertFalse(workspaces["A"].exists())
        self.assertTrue(workspaces["B"].exists())
        self.assertIsNone(b.poll(), "A cleanup must leave its executing sibling alone")
        listing = f.git(f.primary, "worktree", "list", "--porcelain")
        self.assertNotIn("worktree " + str(workspaces["A"]) + "\n", listing)
        self.assertIn("worktree " + str(workspaces["B"]) + "\n", listing)
        life.collect("B", b)
        life.prepare_and_done("B")
        life.assert_contiguous_integrations((attempts["A"], attempts["B"]))
        life.finish()


if __name__ == "__main__":
    unittest.main(verbosity=2)
