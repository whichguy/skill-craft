#!/usr/bin/env python3
"""Reusable fixture for public-CLI composition tests.

Native handles, worker results and the prerequisite ShipLoop/Improve traversal
are synthetic. This suite does not launch an LLM or qualify host callbacks.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/shiploop/scripts"
sys.path.insert(0, str(SCRIPTS))
import shiploop_navigator as nav
import shiploop_store as store
import shiploop_chain_ledger as chain_ledger
import shiploop_chain as chain

CLI = SCRIPTS / "shiploop"
# Bindings always carry the immutable planning-context contract of this one
# pinned Plan Dispatcher package.
CONTEXT_FIXTURE = ROOT / "test/fixtures/plan-dispatcher-v3"
FIXTURE = CONTEXT_FIXTURE
SERIAL_FIXTURE = CONTEXT_FIXTURE
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ChainFixture(unittest.TestCase):
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
        # A chain is the ask-agent route; an inline run executes steps directly.
        self.state = nav.new_state(
            str(self.target), self.original_prompt_sentinel,
            delegation="ask-agent",
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
            improve_writes = None
            if self.state["active_improve"] is not None:
                # Only an Improve checkpoint parks a child to import.
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
                 "--ask-agent-skill", str(self.ask / "SKILL.md"), "--worktree-parent", str(self.parent)]
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
        self.graph = self.write("graph.json", {"version": 1, "steps": [{"id": "A", "deps": [],
            "contract": {"task": "Implement A", "ready": [], "done": ["A verified"]}}]})
        self.bind()
        a = self.claim(["A"])["A"]
        self.start("A", a)
        self.call("done", self.contribute("A"))
        self.cleanup_accepted_workers()
        proof = self.write("combined.json", {"passed": True, "commit": self.commits["A"]})
        value = {"commit": self.commits["A"], "confirmed_stopped": True,
                 "verification": {"path": str(proof), "sha256": digest(proof)}}
        self.call("finish", value)
        return value

    def child_state_path(self):
        binding = store.read_record(self.run / "chains" / self.action / "binding.md")
        return Path(binding["dispatcher_run"]) / "plan-dispatcher-state.json"

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
