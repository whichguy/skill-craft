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
# New bindings always carry the immutable planning-context contract.  Keep the
# old pinned packages named separately: they are fixtures for recovery and
# refusal cases, never implicit candidates for a fresh bind.
LEGACY_FIXTURE = ROOT / "test/fixtures/plan-dispatcher-v1"
LEGACY_SERIAL_FIXTURE = ROOT / "test/fixtures/plan-dispatcher-v2"
CONTEXT_FIXTURE = ROOT / "test/fixtures/plan-dispatcher-v3"
FIXTURE = CONTEXT_FIXTURE
SERIAL_FIXTURE = CONTEXT_FIXTURE
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
        self.git(self.primary, "config", "--local", "user.useConfigOnly", "true")
        self.git(self.primary, "config", "--local", "user.name", "Chain Fixture")
        self.git(self.primary, "config", "--local", "user.email", "chain@example.invalid")
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
        self.original_prompt_sentinel = "ORIGINAL-USER-PROMPT-SENTINEL: never copy this into planning references"
        self.state = nav.new_state(
            str(self.target), self.original_prompt_sentinel, protocol_version=3
        )
        self.planning_dir = self.base / "planning-material"
        self.planning_dir.mkdir()
        self.architecture = self.write_text(
            "planning-material/architecture.md",
            "# Architecture decision\n\n"
            "Use sibling worker worktrees. ShipLoop integrates only independently verified commits.\n",
        )
        self.test_strategy = self.write_text(
            "planning-material/test-strategy.md",
            "# Test strategy\n\n"
            "Exercise independent A/B work, then verify the joined C behavior against both results.\n",
        )
        self.planning_contract = self.write_text(
            "planning-material/context-code-contract.json",
            json.dumps({
                "schema": "chain-planning-context-fixture/v1",
                "steps": {
                    "A": {
                        "path": "context_alpha.py",
                        "source": "def alpha():\n    return 'alpha'\n",
                        "check": "from context_alpha import alpha; assert alpha() == 'alpha'",
                    },
                    "B": {
                        "path": "context_beta.py",
                        "source": "def beta():\n    return 'beta'\n",
                        "check": "from context_beta import beta; assert beta() == 'beta'",
                    },
                    "C": {
                        "path": "context_join.py",
                        "source": "from context_alpha import alpha\nfrom context_beta import beta\ndef joined():\n    return alpha() + '-' + beta()\n",
                        "check": "from context_join import joined; assert joined() == 'alpha-beta'",
                    },
                    "J": {
                        "path": "context_report.py",
                        "source": "from context_join import joined\ndef report():\n    return 'report:' + joined()\n",
                        "check": "from context_report import report; assert report() == 'report:alpha-beta'",
                    },
                },
            }, indent=2) + "\n",
        )
        self.historical_missing = self.planning_dir / "retired-discovery.md"
        self.planning_action_ids = []
        repeated_discovery = False
        # Drive only the pure navigation API, explicitly synthetic Improve
        # receipts. Persist after every accepted action so the planning-context
        # collector sees the same durable history a real run would provide.
        while nav.current_stage(self.state) != "implement":
            aid = nav.current_action(self.state)["id"]
            stage = nav.current_stage(self.state)
            if stage == "discovery" and not repeated_discovery:
                repeated_discovery = True
                value = {
                    "outcome": "repeat",
                    "summary": "Synthetic discovery draft superseded by the reviewed decision.",
                    "evidence_refs": [str(self.historical_missing)],
                }
            else:
                value = {
                    "outcome": "done",
                    "summary": "Synthetic " + stage
                    + " decision: preserve the Architecture decision and reviewed context-code contract.",
                    "evidence_refs": [str(self.architecture), str(self.test_strategy), str(self.planning_contract)],
                }
            if stage == "plan":
                value["work_items"] = [{
                    "id": "feature", "title": "Parallel feature",
                    "context": "Use the reviewed context-code contract and the architecture decision.",
                }]
            self.state = nav.apply(self.state, aid, value)
            improve, improve_writes = self.synthetic_improve_record(aid, stage)
            self.state = nav.finish_improve(self.state, aid, improve)
            self.planning_action_ids.append(aid)
            nav.save(self.run, self.state, improve_writes)
        # Public navigator operations retain this generic run lock. Include it
        # in the synthetic baseline so capability-preflight tests can prove
        # that a legacy helper created no chain-side state.
        (self.run / ".lock").touch()
        self.action = nav.current_action(self.state)["id"]
        self.dispatcher = self.base / "selected-dispatcher"
        self.select_dispatcher(FIXTURE)
        self.ask = self.base / "selected-ask-agent"
        shutil.copytree(ROOT / "skills/ask-agent", self.ask)
        self.graph = self.write("graph.json", {"version": 1, "steps": [
            {"id": name, "deps": deps, "contract": {"task": "Implement " + name,
             "ready": ["Required inputs are available"], "done": [name + " verified and committed"]}}
            for name, deps in (("A", []), ("B", []), ("C", ["A"]), ("J", ["B", "C"]))
        ]})
        self.packets = {}
        self.import_inputs = {}
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

    def write_text(self, name, value):
        p = self.base / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(value)
        return p

    def synthetic_improve_record(self, action, stage):
        """Create the durable standalone-Improve receipt shape used by a real run."""
        prefix = "improve/" + action
        source_text = {
            "review-a.md": "Review A for " + stage + ": preserve the Architecture decision.\n",
            "review-b.md": "Review B for " + stage + ": preserve the context-code contract.\n",
            "check.md": "Check for " + stage + ": planning references are recorded.\n",
        }
        evidence = []
        writes = {}
        for index, source in enumerate(("review-a.md", "review-b.md", "check.md"), start=1):
            archive = prefix + "/evidence/" + f"{index:02d}-" + source
            text = source_text[source]
            writes[archive] = text
            evidence.append({
                "source": source,
                "archive": archive,
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            })
        receipt = {
            "summary": "Synthetic Improve for " + stage + ": retain the reviewed behavior and evidence.",
            "review_refs": ["review-a.md", "review-b.md"],
            "check_refs": ["check.md"],
            "lessons": "Keep the reviewed dependency graph and verify behavior from the planning contract.",
        }
        record = {
            "version": 1,
            "binding_id": self.state["run_id"] + "/" + action,
            "workspace": str(self.target),
            "action_id": action,
            "stage": stage,
            "skill": {
                "skill_card": "synthetic-fixture",
                "runtime_card": "synthetic-fixture",
                "runtime_cli": "synthetic-fixture",
                "skill_version": "1",
                "runtime_version": "1",
            },
            "runtime_phase": "done",
            "identities": {
                "evidence_sha256": {entry["source"]: entry["sha256"] for entry in evidence},
            },
            "evidence": evidence,
            "receipt": receipt,
        }
        writes[prefix + "/receipt.md"] = store.dumps(record, "ShipLoop standalone Improve receipt")
        return record, writes

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
                 "--lifecycle", "per-step"]
        if mode is not None:
            extra += ["--mode", mode]
        if capacity is not None:
            extra += ["--capacity", str(capacity)]
        return self.call("bind", ok=ok, extra=tuple(extra))

    def claim(self, steps):
        output = self.call("claim", {"steps": steps})
        return {c["step"]: c["attempt"] for c in output["claims"]}

    def start_value(self, step, attempt, base=None, resources=None, integration=False):
        del integration
        ready = self.write(f"ready-{attempt}.json", {"ready": True, "synthetic": True})
        value = {"attempt": attempt, "base_commit": base or self.git(self.target, "rev-parse", "HEAD"),
                 "write_scope": [step + ".txt"],
                 "resources": resources or [], "ready_evidence": {"path": str(ready), "sha256": digest(ready)}}
        return value

    def start(self, step, attempt, base=None, resources=None, integration=False):
        value = self.start_value(step, attempt, base, resources, integration)
        self.assertNotIn("workspace", value)
        output = self.call("start", value)
        self.assertEqual(output["action"], "launch")
        self.packets[step] = output["packet"]
        self.assertEqual(output["packet"]["ask_agent_workspace"]["worktree"],
                         output["packet"]["context"]["workspace"])
        self.call("launched", {"attempt": attempt, "handle": {"host": "synthetic", "id": step}})
        return output

    def serial_start(self, step, attempt, base=None, resources=None, integration=False):
        value = self.start_value(step, attempt, base, resources, integration)
        self.assertNotIn("workspace", value)
        output = self.call("start", value)
        self.assertEqual(output["action"], "execute")
        self.packets[step] = output["packet"]
        self.assertEqual(output["packet"]["ask_agent_workspace"]["worktree"],
                         output["packet"]["context"]["workspace"])
        self.assertEqual(output["packet"]["executor"]["kind"], "main-context")
        return output

    def contribute(self, step, *, integration=False):
        packet = self.packets[step]
        repo = Path(packet["context"]["workspace"])
        # Each managed worker starts from the already-integrated target head.
        # The old final-return join worker merged siblings itself; the managed
        # per-step path carries those accepted commits in this inherited base.
        if integration:
            for expected in ("A", "B", "C"):
                self.assertEqual((repo / (expected + ".txt")).read_text(), expected + "\n")
        (repo / (step + ".txt")).write_text(step + "\n")
        self.git(repo, "add", step + ".txt")
        self.git(repo, "commit", "-qm", "Implement " + step)
        source_commit = self.git(repo, "rev-parse", "HEAD")
        handoff_root = repo / ".shiploop-handoff" / packet["attempt"]
        handoff_root.mkdir(parents=True, exist_ok=True)
        checks = handoff_root / "checks.json"
        checks.write_text(json.dumps({
            "passed": True, "cwd": str(repo), "git_root": str(repo), "commit": source_commit,
            "synthetic_managed_worker": True,
        }) + "\n")
        handoff = handoff_root / "handoff.json"
        handoff.write_text(json.dumps({
            "schema": "shiploop-chain-handoff/v1", "run_id": packet["run_id"],
            "step": step, "attempt": packet["attempt"],
            "base_commit": packet["context"]["base_commit"], "status": "SUCCEEDED",
            "commit": source_commit, "summary": "Managed fixture implemented " + step,
            "files": [{"path": "checks.json", "sha256": digest(checks)}],
        }) + "\n")
        import_value = {
            "attempt": packet["attempt"], "confirmed_stopped": True,
            "handoff": {"path": str(handoff), "sha256": digest(handoff)},
        }
        self.import_inputs[step] = json.loads(json.dumps(import_value))
        imported = self.call("import-handoff", import_value)
        self.assertEqual(imported["import"]["status"], "SUCCEEDED")
        prepared = self.call("prepare", {"attempt": packet["attempt"], "confirmed_stopped": True})
        integration_proof = prepared["integration"]
        self.commits[step] = integration_proof["candidate_commit"]
        binding = store.read_record(self.run / "chains" / self.action / "binding.md")
        receipt = chain._node(binding, "receipt", {"attempt": packet["attempt"]})
        proof = self.write(f"verified-{step}.json", {
            "commit": integration_proof["candidate_commit"], "passed": True,
            "integration": integration_proof,
            "checks": ["managed handoff, inherited source ancestry, and candidate integration"],
        })
        return {
            "attempt": packet["attempt"], "confirmed_stopped": True,
            "integration": integration_proof,
            "verification": {
                "receipt_sha256": receipt["sha256"], "passed": True,
                "reason": "Independent fixture checks",
                "evidence": {"path": str(proof), "sha256": digest(proof)},
            },
        }

    def reject_contribution(self, step, status):
        self.assertIn(status, {"FAILED", "BLOCKED"})
        packet = self.packets[step]
        repo = Path(packet["context"]["workspace"])
        handoff_root = repo / ".shiploop-handoff" / packet["attempt"]
        handoff_root.mkdir(parents=True, exist_ok=True)
        detail = handoff_root / "detail.json"
        detail.write_text(json.dumps({"status": status, "stopped": True, "synthetic_managed_worker": True}) + "\n")
        handoff = handoff_root / "handoff.json"
        handoff.write_text(json.dumps({
            "schema": "shiploop-chain-handoff/v1", "run_id": packet["run_id"],
            "step": step, "attempt": packet["attempt"],
            "base_commit": packet["context"]["base_commit"], "status": status, "commit": None,
            "summary": "Managed fixture " + status.lower(),
            "files": [{"path": "detail.json", "sha256": digest(detail)}],
        }) + "\n")
        imported = self.call("import-handoff", {
            "attempt": packet["attempt"], "confirmed_stopped": True,
            "handoff": {"path": str(handoff), "sha256": digest(handoff)},
        })
        self.assertEqual(imported["import"]["status"], status)
        binding = store.read_record(self.run / "chains" / self.action / "binding.md")
        receipt = chain._node(binding, "receipt", {"attempt": packet["attempt"]})
        proof = self.write(f"rejected-{step}-{status}.json", {"passed": False, "status": status})
        return {
            "attempt": packet["attempt"], "confirmed_stopped": True,
            "verification": {
                "receipt_sha256": receipt["sha256"], "passed": False,
                "reason": "Synthetic " + status.lower(),
                "evidence": {"path": str(proof), "sha256": digest(proof)},
            },
        }

    def cleanup_accepted_workers(self):
        """Close every accepted managed workspace before final chain return."""
        for packet in tuple(self.packets.values()):
            attempt = packet["attempt"]
            record = self.child_record(attempt)
            if record.get("status") != "accepted":
                continue
            workspace = Path(packet["context"]["workspace"])
            if workspace.exists():
                cleaned = self.call("cleanup", {"attempt": attempt, "confirmed_stopped": True})
                self.assertFalse(cleaned["pending"])
            self.assertFalse(workspace.exists())

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
        self.cleanup_accepted_workers()
        proof = self.write("combined.json", {"passed": True, "commit": self.commits["A"]})
        value = {"commit": self.commits["A"], "confirmed_stopped": True,
                 "verification": {"path": str(proof), "sha256": digest(proof)}}
        self.call("finish", value)
        return value

    def child_state_path(self):
        binding = store.read_record(self.run / "chains" / self.action / "binding.md")
        directory = Path(binding["dispatcher_run"])
        current = directory / "plan-dispatcher-state.json"
        return current if current.exists() else directory / "state.json"

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

    def test_dispatcher_resumes_legacy_state_in_place_without_a_new_copy(self):
        self.select_dispatcher(SERIAL_FIXTURE)
        self.bind()
        authority = self.child_state_path()
        self.assertEqual(authority.name, "plan-dispatcher-state.json")
        legacy = authority.with_name("state.json")
        authority.rename(legacy)
        self.claim(["A"])
        self.assertEqual(self.child_state_path(), legacy)
        self.assertEqual(self.child_state()["steps"]["A"]["status"], "claimed")
        before = self.run_bytes()
        self.assertEqual(self.call("pending")["pending"][0]["status"], "claimed")
        self.call("next")
        self.assertEqual(self.run_bytes(), before)
        self.assertFalse(authority.exists())

    def test_duplicate_dispatcher_states_refuse_reads_and_mutation_without_fallback(self):
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
                for operation, value in (("pending", None), ("claim", {"steps": ["A"]})):
                    result = self.call(operation, value, ok=False)
                    self.assertRegex(result.stdout + result.stderr,
                                     r"multiple dispatcher state files|both canonical and legacy state files")
                self.assertEqual(self.run_bytes(), before)
                self.assertEqual(self.git(self.target, "rev-parse", "HEAD"), before_head)

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

    def test_legacy_serial_helper_refuses_fresh_context_bind_before_writes(self):
        initial_state = (self.run / "state.md").read_bytes()
        self.select_dispatcher(LEGACY_SERIAL_FIXTURE)
        refused = self.bind(capacity=None, mode="serial", ok=False)
        self.assertIn("planning-context.js", refused.stderr)
        self.assertEqual((self.run / "state.md").read_bytes(), initial_state)
        self.assertFalse((self.run / "chains").exists())

    def test_current_binding_defaults_to_parallel(self):
        self.bind(capacity=None)
        binding_path = self.run / "chains" / self.action / "binding.md"
        binding = store.read_record(binding_path)
        self.assertEqual(binding["schema"], "shiploop-chain-binding/v6")
        self.assertEqual(binding["mode"], "parallel")
        self.assertEqual(binding["capacity"], 2)
        self.assertIn("planning_context", binding)

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
        self.start("J", j, self.git(self.target, "rev-parse", "HEAD"), integration=True)
        self.call("settle", self.contribute("J", integration=True))
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
        before_worktrees = self.git(self.target, "worktree", "list", "--porcelain")
        output = self.call("start", retry)
        self.assertEqual(output["action"], "reconcile")
        self.assertEqual(output["packet"], packet)
        self.assertEqual(self.git(self.target, "worktree", "list", "--porcelain"), before_worktrees)
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

    def test_observe_is_rejected_without_rewriting_prior_event_files(self):
        self.bind()
        a = self.claim(["A"])["A"]
        self.start("A", a)
        self.contribute("A")
        before_events = self.ledger_bytes()
        before_child = self.child_state_path().read_bytes()
        refused = self.call("observe", {"attempt": a, "occurred_at": "2020-01-01T00:00:00Z"}, ok=False)
        self.assertIn("import-handoff", refused.stderr)
        self.assertEqual(self.ledger_bytes(), before_events)
        self.assertEqual(self.child_state_path().read_bytes(), before_child)

    def test_non_implementation_binding_is_rejected(self):
        state = nav.new_state(str(self.target), "Still intake", protocol_version=3)
        nav.save(self.run, state)
        self.action = nav.current_action(state)["id"]
        p = self.call("bind", ok=False, extra=("--graph", str(self.graph),
            "--dispatcher-skill", str(self.dispatcher / "SKILL.md"), "--ask-agent-skill", str(self.ask / "SKILL.md"),
            "--worktree-parent", str(self.parent), "--lifecycle", "per-step"))
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

    def test_failed_and_wrong_commit_finish_proof_preserves_accepted_target(self):
        self.graph = self.write("graph.json", {"steps": [{"id": "A", "deps": [],
            "contract": {"task": "Implement A", "ready": [], "done": ["A verified"]}}]})
        self.bind()
        a = self.claim(["A"])["A"]
        self.start("A", a)
        self.call("settle", self.contribute("A"))
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
        self.call("settle", self.contribute("A"))
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
            "--lifecycle", "per-step"))
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
