#!/usr/bin/env python3
"""Public-CLI composition with real Git and pinned real dispatcher code.

Native handles, worker results and the prerequisite ShipLoop/Improve traversal
are synthetic. This suite does not launch an LLM or qualify host callbacks.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/shiploop/scripts"
sys.path.insert(0, str(SCRIPTS))
import shiploop_navigator as nav
import shiploop_store as store
import shiploop_chain_ledger as chain_ledger
import shiploop_chain as chain

CLI = SCRIPTS / "shiploop"
FIXTURE = ROOT / "test/fixtures/plan-dispatcher-v1"
SERIAL_FIXTURE = ROOT / "test/fixtures/plan-dispatcher-v2"
_improve_spec = importlib.util.spec_from_file_location(
    "chain_actual_improve_fixture", ROOT / "test/shiploop-actual-improve-cli.test.py")
_improve_fixture = importlib.util.module_from_spec(_improve_spec)
_improve_spec.loader.exec_module(_improve_fixture)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ChainIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.assert_fixture(FIXTURE)
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-chain-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.primary = self.base / "primary"
        self.primary.mkdir()
        self.git(self.primary, "init", "-q", "-b", "main")
        (self.primary / "README.md").write_text("fixture\n")
        self.git(self.primary, "add", "README.md")
        self.git(self.primary, "commit", "-qm", "baseline")
        self.initial = self.git(self.primary, "rev-parse", "HEAD")
        self.parent = self.base / ".work-trees/project"
        self.parent.mkdir(parents=True)
        self.target = self.parent / "initiating-feature"
        self.git(self.primary, "worktree", "add", "-q", "-b", "feature", str(self.target))
        self.run = self.base / "run"
        self.run.mkdir()
        self.state = nav.new_state(str(self.target), "Implement a bounded parallel feature", protocol_version=3)
        # Drive only the pure navigation API, explicitly synthetic Improve receipts.
        while nav.current_stage(self.state) != "implement":
            aid = nav.current_action(self.state)["id"]
            value = {"outcome": "done", "summary": "Synthetic prerequisite fixture"}
            if nav.current_stage(self.state) == "plan":
                value["work_items"] = [{"id": "feature", "title": "Parallel feature"}]
            self.state = nav.apply(self.state, aid, value)
            self.state = nav.finish_improve(self.state, aid, {"summary": "Synthetic prerequisite Improve"})
        self.action = nav.current_action(self.state)["id"]
        nav.save(self.run, self.state)
        self.dispatcher = self.base / "selected-dispatcher"
        self.select_dispatcher(FIXTURE)
        self.ask = self.base / "selected-ask-agent"
        shutil.copytree(ROOT / "skills/ask-agent", self.ask)
        self.graph = self.write("graph.json", {"steps": [
            {"id": name, "deps": deps, "contract": {"task": "Implement " + name,
             "ready": ["Required inputs are available"], "done": [name + " verified and committed"]}}
            for name, deps in (("A", []), ("B", []), ("C", ["A"]), ("J", ["B", "C"]))
        ]})
        self.packets = {}
        self.commits = {}
        self.counter = 0

    def assert_fixture(self, fixture):
        provenance = json.loads((fixture / "PROVENANCE.json").read_text())
        for relative, expected in provenance["files_sha256"].items():
            self.assertEqual(digest(fixture / relative), expected, "Pinned dispatcher drift: " + relative)

    def select_dispatcher(self, fixture):
        self.assert_fixture(fixture)
        if self.dispatcher.exists():
            shutil.rmtree(self.dispatcher)
        shutil.copytree(fixture, self.dispatcher)

    def git(self, repo, *args):
        p = subprocess.run(["git", "-c", "user.name=Chain Fixture", "-c",
                            "user.email=chain@example.invalid", "-C", str(repo), *args],
                           text=True, capture_output=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout.strip()

    def write(self, name, value):
        p = self.base / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value) + "\n")
        return p

    def call(self, operation, value=None, *, ok=True, extra=()):
        argv = [sys.executable, "-B", str(CLI), "chain", operation,
                "--run-dir", str(self.run), "--action", self.action, *extra]
        if value is not None:
            self.counter += 1
            argv += ["--input", str(self.write(f"inputs/{self.counter}.json", value))]
        p = subprocess.run(argv, text=True, capture_output=True, timeout=30)
        if not ok:
            self.assertNotEqual(p.returncode, 0, p.stdout)
            return p
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        return json.loads(p.stdout)

    def bind(self, capacity=2, *, mode=None, ok=True):
        extra = ["--graph", str(self.graph), "--dispatcher-skill", str(self.dispatcher / "SKILL.md"),
                 "--ask-agent-skill", str(self.ask / "SKILL.md"), "--worktree-parent", str(self.parent),
                 "--lifecycle", "final-return"]
        if mode is not None:
            extra += ["--mode", mode]
        if capacity is not None:
            extra += ["--capacity", str(capacity)]
        return self.call("bind", ok=ok, extra=tuple(extra))

    def claim(self, steps):
        output = self.call("claim", {"steps": steps})
        return {c["step"]: c["attempt"] for c in output["claims"]}

    def start_value(self, step, attempt, base=None, resources=None, integration=False):
        ready = self.write(f"ready-{attempt}.json", {"ready": True, "synthetic": True})
        value = {"attempt": attempt, "base_commit": base or self.initial,
                 "write_scope": ["A.txt", "B.txt", "C.txt"] if integration else [step + ".txt"],
                 "resources": resources or [], "ready_evidence": {"path": str(ready), "sha256": digest(ready)}}
        if integration:
            value["integration"] = True
        return value

    def start(self, step, attempt, base=None, resources=None, integration=False):
        value = self.start_value(step, attempt, base, resources, integration)
        output = self.call("start", value)
        self.assertEqual(output["action"], "launch")
        self.packets[step] = output["packet"]
        self.call("launched", {"attempt": attempt, "handle": {"host": "synthetic", "id": step}})
        return output

    def serial_start(self, step, attempt, base=None, resources=None, integration=False):
        value = self.start_value(step, attempt, base, resources, integration)
        output = self.call("start", value)
        self.assertEqual(output["action"], "execute")
        self.packets[step] = output["packet"]
        return output

    def contribute(self, step, *, integration=False):
        packet = self.packets[step]
        repo = Path(packet["context"]["workspace"])
        if integration:
            for dependency in ("B", "C"):
                self.git(repo, "merge", "--no-ff", "-m", "Integrate " + dependency, self.commits[dependency])
            for expected in ("A", "B", "C"):
                self.assertEqual((repo / (expected + ".txt")).read_text(), expected + "\n")
        else:
            (repo / (step + ".txt")).write_text(step + "\n")
            self.git(repo, "add", step + ".txt")
            self.git(repo, "commit", "-qm", "Implement " + step)
        commit = self.git(repo, "rev-parse", "HEAD")
        self.commits[step] = commit
        artifact = Path(packet["outputs"]["artifact"])
        artifact.write_text(json.dumps({"commit": commit, "checks": ["fixture contents verified"], "synthetic_native": True}) + "\n")
        envelope = dict(packet["report_envelope"])
        envelope["status"] = "SUCCEEDED"
        envelope["evidence"] = {"path": str(artifact), "sha256": digest(artifact)}
        Path(packet["outputs"]["envelope"]).write_text(json.dumps(envelope) + "\n")
        p = subprocess.run(packet["report_argv"], text=True, capture_output=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr)
        receipt = json.loads(p.stdout)
        proof = self.write(f"verified-{step}.json", {"commit": commit, "passed": True,
             "native_stopped": "synthetic fixture attestation", "checks": ["file contents and ancestry"]})
        return {"attempt": packet["attempt"], "confirmed_stopped": True,
                "verification": {"receipt_sha256": receipt["sha256"], "passed": True,
                  "reason": "Independent fixture checks", "evidence": {"path": str(proof), "sha256": digest(proof)}}}

    def reject_contribution(self, step, status):
        self.assertIn(status, {"FAILED", "BLOCKED"})
        packet = self.packets[step]
        artifact = Path(packet["outputs"]["artifact"])
        artifact.write_text(json.dumps({"status": status, "checks": ["synthetic failure fixture"]}) + "\n")
        envelope = dict(packet["report_envelope"])
        envelope["status"] = status
        envelope["evidence"] = {"path": str(artifact), "sha256": digest(artifact)}
        Path(packet["outputs"]["envelope"]).write_text(json.dumps(envelope) + "\n")
        report = subprocess.run(packet["report_argv"], text=True, capture_output=True, timeout=30)
        self.assertEqual(report.returncode, 0, report.stderr)
        receipt = json.loads(report.stdout)
        proof = self.write(f"rejected-{step}-{status}.json", {"passed": False, "status": status})
        return {"attempt": packet["attempt"], "confirmed_stopped": True,
                "verification": {"receipt_sha256": receipt["sha256"], "passed": False,
                  "reason": "Synthetic " + status.lower(),
                  "evidence": {"path": str(proof), "sha256": digest(proof)}}}

    def parent_complete(self, outcome="done", *, ok=False):
        p = self.run / "inbox" / (self.action + ".md")
        store.write_record(p, {"outcome": outcome, "summary": "Synthetic chain integration complete"})
        result = subprocess.run([sys.executable, "-B", str(CLI), "complete", "--run-dir", str(self.run),
                                 "--action", self.action, "--result", str(p)], text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def complete_single_chain(self):
        self.graph = self.write("graph.json", {"steps": [{"id": "A", "deps": [],
            "contract": {"task": "Implement A", "ready": [], "done": ["A verified"]}}]})
        self.bind()
        a = self.claim(["A"])["A"]
        self.start("A", a)
        self.call("settle", self.contribute("A"))
        proof = self.write("combined.json", {"passed": True, "commit": self.commits["A"]})
        value = {"commit": self.commits["A"], "confirmed_stopped": True,
                 "verification": {"path": str(proof), "sha256": digest(proof)}}
        self.call("finish", value)
        return value

    def child_state_path(self):
        binding = store.read_record(self.run / "chains" / self.action / "binding.md")
        return Path(binding["dispatcher_run"]) / "state.json"

    def child_state(self):
        return json.loads(self.child_state_path().read_text())

    def child_record(self, attempt):
        return self.child_state()["attempts"][attempt]

    def ledger_bytes(self):
        events = self.run / "chains" / self.action / "events"
        return {path.name: path.read_bytes() for path in sorted(events.glob("*.md"))}

    def terminal_events(self, attempt):
        events = self.run / "chains" / self.action / "events"
        return [row["event"] for row in chain_ledger.read_events(events)
                if row["event"]["kind"] == "settle_result"
                and row["event"]["data"].get("attempt") == attempt]

    def assert_completion(self, response, done, not_done):
        self.assertEqual(response["completion"], {"done": done, "not_done": not_done})

    def run_bytes(self):
        return {str(path.relative_to(self.run)): path.read_bytes()
                for path in self.run.rglob("*") if path.is_file()}

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
        self.start("B", attempts["B"])
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
        self.graph = self.write("graph.json", {"steps": [{"id": "A", "deps": [],
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
        old_action = self.action
        self.import_synthetic_improve("repeat")
        state = store.read_record(self.run / "state.md")
        self.assertNotEqual(nav.current_action(state)["id"], old_action)
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
        self.call("recover")
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
        self.call("recover")
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

    def import_synthetic_improve(self, outcome):
        # Reuse the actual child-runtime test apparatus, not a fabricated terminal receipt.
        fixture = _improve_fixture.ImproveCliFixture()
        fixture.base, fixture.repo, fixture.run = self.base, self.target, self.run
        fixture.environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        fixture.action = self.action
        fixture.parent_evidence_refs = []
        fixture.bind_current()
        fixture.finish_ephemeral()
        fixture.completion_receipt(final_result={"outcome": outcome,
            "summary": "Synthetic review disposition after verified chain"})
        return fixture.invoke(
            CLI, "improve-complete", "--run-dir", self.run, "--action", self.action,
            "--result", fixture.completion_path)

    def test_serial_v2_full_diamond_executes_in_main_context_before_finish(self):
        self.select_dispatcher(SERIAL_FIXTURE)
        bound = self.bind(capacity=None, mode="serial")
        self.assert_completion(bound, [], ["A", "B", "C", "J"])
        binding = store.read_record(self.run / "chains" / self.action / "binding.md")
        self.assertEqual(binding["mode"], "serial")
        self.assertEqual(binding["capacity"], 1)
        target_before_finish = self.git(self.target, "rev-parse", "HEAD")
        accepted = []

        for step in ("A", "B", "C", "J"):
            before = self.call("next")
            self.assert_completion(before, accepted, [name for name in ("A", "B", "C", "J")
                                                     if name not in accepted])
            self.assertEqual(before["ready"][0], step)
            attempt = self.claim([step])[step]
            self.assertLessEqual(len(self.call("next")["active"]), 1)
            if step == "C":
                started = self.serial_start(step, attempt, base=self.commits["A"])
            elif step == "J":
                started = self.serial_start(step, attempt, integration=True)
            else:
                started = self.serial_start(step, attempt)
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
            self.assertEqual(self.git(self.target, "rev-parse", "HEAD"), target_before_finish)

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
        self.call("finish", finish)
        self.assertEqual(self.git(self.target, "rev-parse", "HEAD"), self.commits["J"])
        self.assertEqual(self.git(self.primary, "rev-parse", "HEAD"), self.initial)
        for packet in self.packets.values():
            workspace = Path(packet["context"]["workspace"]).resolve()
            self.assertNotIn(self.target, workspace.parents)
            self.assertEqual(workspace.parent, self.parent)
        self.parent_complete(ok=True)

    def test_v1_serial_start_refuses_without_native_fallback(self):
        initial_state = (self.run / "state.md").read_bytes()
        self.bind(capacity=None, mode="serial")
        binding = store.read_record(self.run / "chains" / self.action / "binding.md")
        self.assertEqual(binding["mode"], "serial")
        a = self.claim(["A"])["A"]
        self.call("start", self.start_value("A", a), ok=False)
        self.assertNotEqual((self.run / "state.md").read_bytes(), initial_state)
        record = self.child_record(a)
        self.assertEqual(record["status"], "claimed")
        self.assertIsNone(record["handle"])
        self.assertNotIn("executor", record)
        self.assertFalse((Path(binding["dispatcher_run"]) / "inbox" / (a + ".json")).exists())
        kinds = [row["event"]["kind"] for row in chain_ledger.read_events(
            self.run / "chains" / self.action / "events")]
        self.assertIn("start_error", kinds)
        self.assertNotIn("start_result", kinds)
        self.assertFalse(any(kind.startswith("launched_") for kind in kinds))

    def test_legacy_v1_binding_defaults_to_parallel(self):
        self.bind(capacity=None)
        binding_path = self.run / "chains" / self.action / "binding.md"
        legacy_binding = store.read_record(binding_path)
        self.assertEqual(legacy_binding["mode"], "parallel")
        self.assertEqual(legacy_binding["capacity"], 2)
        legacy_binding["schema"] = "shiploop-chain-binding/v1"
        legacy_binding.pop("mode")
        legacy_text = store.dumps(legacy_binding, "ShipLoop chain binding")
        state = store.read_record(self.run / "state.md")
        state["chain_bindings"] = dict(state["chain_bindings"])
        state["chain_bindings"][self.action] = hashlib.sha256(legacy_text.encode("utf-8")).hexdigest()
        state["revision"] += 1
        nav.save(self.run, state, {str(binding_path.relative_to(self.run)): legacy_text})

        recovered = self.call("recover")
        self.assertEqual(recovered["shiploop_chain"]["mode"], "parallel")
        self.assert_completion(recovered, [], ["A", "B", "C", "J"])

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

        recovered = self.call("recover")
        self.assert_completion(recovered, [], ["A", "B", "C", "J"])
        active = [action for action in recovered["actions"] if action.get("attempt") == a]
        self.assertEqual([action["action"] for action in active], ["resume"])
        self.assertEqual(self.child_state_path().read_bytes(), before_state)
        self.assertEqual(self.ledger_bytes(), after_replay_ledger)
        self.assertIsNone(self.child_record(a)["handle"])

    def test_serial_done_alias_reconciles_once_and_preserves_terminal_history(self):
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
        repeated_settle = self.call("settle", verification)
        self.assert_completion(repeated_settle, ["A"], ["B", "C", "J"])
        self.assertEqual(self.child_state_path().read_bytes(), before_state)
        self.assertEqual(self.child_state()["revision"], before_revision)
        self.assertEqual(self.ledger_bytes(), before_ledger)
        self.assertEqual(len(self.terminal_events(a)), 1)
        repeated_done = self.call("done", verification)
        self.assert_completion(repeated_done, ["A"], ["B", "C", "J"])
        self.assertEqual(self.child_state_path().read_bytes(), before_state)
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
        observed = self.call("observe", {"attempt": claims["A"], "occurred_at": "2026-09-18T12:00:00Z"})
        self.assertNotIn("C", self.call("next")["ready"])
        self.call("settle", verification)
        now = self.call("next")
        self.assertIn("C", now["ready"])
        self.assertNotIn("J", now["ready"])
        self.assertTrue(any(a["step"] == "B" for a in now["active"]))
        c = self.claim(["C"])["C"]
        self.start("C", c, self.commits["A"])
        self.call("settle", self.contribute("C"))
        self.call("settle", self.contribute("B"))
        j = self.claim(["J"])["J"]
        self.start("J", j, integration=True)
        self.call("settle", self.contribute("J", integration=True))
        self.assertTrue(self.call("next")["complete"])
        self.parent_complete()  # Child graph completion alone is insufficient.
        proof = self.write("combined-verification.json", {"commit": self.commits["J"], "passed": True,
                           "checks": ["A, B and C contents and exact commit ancestry"]})
        finish = {"commit": self.commits["J"], "confirmed_stopped": True,
                  "verification": {"path": str(proof), "sha256": digest(proof)}}
        self.call("finish", finish)
        self.call("finish", finish)
        self.assertEqual(self.git(self.target, "rev-parse", "HEAD"), self.commits["J"])
        self.assertEqual(self.git(self.primary, "rev-parse", "HEAD"), self.initial)
        for step, packet in self.packets.items():
            path = Path(packet["context"]["workspace"]).resolve()
            self.assertNotIn(self.target, path.parents)
            self.assertEqual(path.parent, self.parent)
        self.parent_complete(ok=True)
        state = store.read_record(self.run / "state.md")
        self.assertEqual(nav.current_stage(state), "implement")
        self.assertIsNotNone(state["active_improve"])

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
        output = self.call("start", retry)
        self.assertNotEqual(output["action"], "launch")
        self.assertEqual(self.call("recover")["active"][0]["attempt"], a)

    def test_settlement_requires_native_stoppage_attestation(self):
        self.bind()
        a = self.claim(["A"])["A"]
        self.start("A", a)
        verification = self.contribute("A")
        verification["confirmed_stopped"] = False
        self.call("settle", verification, ok=False)
        self.assertNotIn("C", self.call("next")["ready"])
        verification["confirmed_stopped"] = True
        self.call("settle", verification)
        self.call("settle", verification)  # exact replay is inert

    def test_selected_package_drift_blocks_mutations(self):
        self.bind()
        with (self.ask / "SKILL.md").open("a") as f:
            f.write("\nChanged selected execution guidance.\n")
        self.call("claim", {"steps": ["A"]}, ok=False)

    def test_ordinary_dependent_base_must_include_supplier(self):
        self.bind()
        a = self.claim(["A"])["A"]
        self.start("A", a)
        self.call("settle", self.contribute("A"))
        c = self.claim(["C"])["C"]
        ready = self.write("bad-base-ready.json", {"ready": True})
        self.call("start", {"attempt": c, "base_commit": self.initial, "write_scope": ["C.txt"],
             "resources": [], "ready_evidence": {"path": str(ready), "sha256": digest(ready)}}, ok=False)

    def test_report_observation_does_not_rewrite_prior_event_files(self):
        self.bind()
        a = self.claim(["A"])["A"]
        self.start("A", a)
        self.contribute("A")
        events = self.run / "chains" / self.action / "events"
        before = {p.name: p.read_bytes() for p in events.glob("*.md")}
        self.call("observe", {"attempt": a, "occurred_at": "2020-01-01T00:00:00Z"})
        for name, content in before.items():
            self.assertEqual((events / name).read_bytes(), content)
        self.assertNotIn("C", self.call("next")["ready"])

    def test_non_implementation_binding_is_rejected(self):
        state = nav.new_state(str(self.target), "Still intake", protocol_version=3)
        nav.save(self.run, state)
        self.action = nav.current_action(state)["id"]
        p = self.call("bind", ok=False, extra=("--graph", str(self.graph),
            "--dispatcher-skill", str(self.dispatcher / "SKILL.md"), "--ask-agent-skill", str(self.ask / "SKILL.md"),
            "--worktree-parent", str(self.parent), "--lifecycle", "final-return"))
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
        p = subprocess.run([sys.executable, "-B", str(CLI), "pause", "--run-dir", str(self.run),
                            "--reason", "Synthetic pause"], text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(set(self.call("recover")["ready"]), {"A", "B"})
        self.call("claim", {"steps": ["A"]}, ok=False)

    def test_improve_repeat_archives_chain_without_blocking_new_implementation(self):
        self.complete_single_chain()
        self.parent_complete(ok=True)
        old_action = self.action
        self.import_synthetic_improve("repeat")
        state = store.read_record(self.run / "state.md")
        self.assertEqual(nav.current_stage(state), "implement")
        self.action = nav.current_action(state)["id"]
        self.assertNotEqual(self.action, old_action)
        self.assertIn(old_action, state["chain_bindings"])
        self.parent_complete(ok=True)

    def test_improve_done_can_refine_returned_candidate_then_advance(self):
        self.complete_single_chain()
        self.parent_complete(ok=True)
        (self.target / "A.txt").write_text("A\nImproved\n")
        self.import_synthetic_improve("done")
        state = store.read_record(self.run / "state.md")
        self.assertNotEqual(nav.current_stage(state), "implement")

    def test_improve_blocked_keeps_finished_chain_and_parent_incomplete(self):
        self.complete_single_chain()
        self.parent_complete(ok=True)
        self.import_synthetic_improve("blocked")
        state = store.read_record(self.run / "state.md")
        self.assertNotEqual(state["status"], "complete")
        self.assertEqual(nav.current_stage(state), "implement")

    def test_claim_and_retry_reconcile_after_process_exit_loses_response(self):
        self.bind()
        self.crash_after("claim", {"steps": ["A"]})
        a = self.claim(["A"])["A"]
        self.start("A", a)
        verification = self.contribute("A")
        verification["verification"]["passed"] = False
        self.call("settle", verification)
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
        self.call("settle", verification, ok=False)
        state = self.call("next")
        self.assertNotIn("C", state["ready"])
        self.assertTrue(any(row["attempt"] == a for row in state["active"]))

    def test_failed_and_wrong_commit_finish_proof_then_post_return_crash(self):
        self.graph = self.write("graph.json", {"steps": [{"id": "A", "deps": [],
            "contract": {"task": "Implement A", "ready": [], "done": ["A verified"]}}]})
        self.bind()
        a = self.claim(["A"])["A"]
        self.start("A", a)
        self.call("settle", self.contribute("A"))
        for contents in ({"passed": False, "commit": self.commits["A"]},
                         {"passed": True, "commit": self.initial}, {}):
            proof = self.write("failed-combined.json", contents)
            self.call("finish", {"commit": self.commits["A"], "confirmed_stopped": True,
                "verification": {"path": str(proof), "sha256": digest(proof)}}, ok=False)
            self.assertEqual(self.git(self.target, "rev-parse", "HEAD"), self.initial)
        proof = self.write("combined.json", {"passed": True, "commit": self.commits["A"]})
        value = {"commit": self.commits["A"], "confirmed_stopped": True,
                 "verification": {"path": str(proof), "sha256": digest(proof)}}
        self.crash_after("finish", value, boundary="git")
        self.assertEqual(self.git(self.target, "rev-parse", "HEAD"), self.commits["A"])
        self.parent_complete()  # Git effect alone is not a reconciled finish receipt.
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
        self.call("start", b, ok=False)
        self.call("settle", self.contribute("A"))
        self.assertEqual(self.call("start", b)["action"], "launch")

    def test_bad_worktree_parent_is_rejected_before_durable_binding(self):
        original = (self.run / "state.md").read_bytes()
        invalid = self.primary / ".work-trees"
        invalid.mkdir()
        self.call("bind", ok=False, extra=("--graph", str(self.graph),
            "--dispatcher-skill", str(self.dispatcher / "SKILL.md"),
            "--ask-agent-skill", str(self.ask / "SKILL.md"), "--worktree-parent", str(invalid),
            "--lifecycle", "final-return"))
        self.assertEqual((self.run / "state.md").read_bytes(), original)
        self.assertFalse((self.run / "chains").exists())

    def test_cold_implementation_packet_carries_optional_chain_route(self):
        cold = store.read_record(self.run / "state.md")
        before = (self.run / "state.md").read_bytes()
        packet = nav.render(None, self.run, cold)
        self.assertIn(str(SCRIPTS.parent / "references/parallel-chain.md"), packet)
        self.assertIn("explicitly selected parallel chain", packet)
        self.assertEqual((self.run / "state.md").read_bytes(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
