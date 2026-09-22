#!/usr/bin/env python3
"""Reusable fixture for real-Git code generation/aggregation lifecycle tests.

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

import shiploop_chain_support as fixture

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "test/fixtures/chain-code-worker.py"
# Fresh deterministic bindings exercise the installed managed Ask-Agent package.
# The 0.4 fixture remains available only for explicit rejection coverage.
ASK = ROOT / "skills/ask-agent"
LEGACY_ASK = ROOT / "test/fixtures/ask-agent-v04"

NAVIGATION_OPERATIONS = frozenset({
    "bind", "next", "recover", "claim", "start", "launched", "import-handoff",
    "prepare", "settle", "done", "retry", "packet", "cleanup", "finish", "observe",
})
CALLBACK_BY_ACTION = {
    "claim": "claim",
    "start": "start",
    "prepare-workspace": "start",
    "recover-workspace": "start",
    "launch": "launched",
    "execute": "import-handoff",
    "collect": "import-handoff",
    "resume": "import-handoff",
    "recover-import": "import-handoff",
    "prepare": "prepare",
    "verify": "done",
    "recover-integration": "done",
    "cleanup": "cleanup",
    "finish": "finish",
    "retry": "retry",
}
ATTEMPT_ACTIONS = frozenset({
    "start", "prepare-workspace", "recover-workspace", "launch", "reconcile",
    "execute", "collect", "resume", "recover-import", "prepare", "verify", "recover-integration",
    "cleanup", "retry",
})

CHAIN_MODULES = {
    "A": {
        "path": "chain_add.py",
        "source": "def add(left, right):\n    return left + right\n",
        "check": "from chain_add import add; assert add(-4,1)==-3 and add(2,3)==5",
    },
    "B": {
        "path": "chain_format.py",
        "source": "def normalize(text):\n    return ' '.join(text.strip().lower().split())\n",
        "check": "from chain_format import normalize; assert normalize(' A   B ')== 'a b'",
    },
    "C": {
        "path": "chain_sum.py",
        "source": "from chain_add import add\ndef total(values):\n    result=0\n    for value in values:\n        result=add(result,value)\n    return result\n",
        "check": "from chain_sum import total; assert total([2,3,-1])==4 and total([])==0",
    },
    "J": {
        "path": "chain_report.py",
        "source": "from chain_sum import total\nfrom chain_format import normalize\ndef report(label, values):\n    return f'{normalize(label)}: {total(values)}'\n",
        "check": "from chain_report import report; assert report(' RESULT ',[2,3])=='result: 5'",
    },
}


class PerStepChainFixture(unittest.TestCase):
    def setUp(self):
        self.f = fixture.ChainFixture(methodName="runTest")
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.f.select_dispatcher(fixture.SERIAL_FIXTURE)
        self.assertTrue((ASK / "SKILL.md").is_file())
        self.assertTrue((ASK / "scripts/ask_agent_workspace.py").is_file())
        self.processes = []
        self.addCleanup(self.stop_processes)
        self.packets = {}
        self.source_commits = {}
        self.done_inputs = {}
        self.imports = {}
        self.navigation_trace = []
        self.start_inputs = {}

    def stop_processes(self):
        for proc in self.processes:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if stream:
                    stream.close()

    def call(self, operation, value=None, **kwargs):
        output = self.f.call(operation, value, **kwargs)
        if kwargs.get("ok", True):
            if operation in NAVIGATION_OPERATIONS:
                self.assert_navigation(operation, output)
            elif operation in {"history", "pending"}:
                self.assertNotIn("navigation", output)
        return output

    def expected_next_argv(self, complete=False):
        base = ["python3", str(ROOT / "skills/shiploop/scripts/shiploop")]
        if complete:
            return [*base, "next", "--run-dir", str(self.f.run)]
        return [*base, "chain", "next", "--run-dir", str(self.f.run),
                "--action", self.f.action]

    def assert_navigation(self, operation, output):
        self.assertIn("navigation", output, operation + " must return script-owned navigation")
        navigation = output["navigation"]
        binding = self.binding()
        graph = binding["graph"]
        self.assertIsInstance(graph, dict)
        self.assertIsInstance(graph.get("steps"), list)
        bound_steps = {item["id"] for item in graph["steps"]
                       if isinstance(item, dict) and isinstance(item.get("id"), str)}
        self.assertEqual(len(bound_steps), len(graph["steps"]))
        if isinstance(output.get("attempt"), str):
            self.assertEqual(output["step"], self.f.child_record(output["attempt"])["step"])
        self.assertEqual(set(navigation), {"complete", "actions", "instruction", "next_argv"})
        self.assertIs(type(navigation["complete"]), bool)
        self.assertIsInstance(navigation["instruction"], str)
        self.assertTrue(navigation["instruction"].strip())
        self.assertIsInstance(navigation["actions"], list)
        self.assertEqual(navigation["next_argv"], self.expected_next_argv(navigation["complete"]))
        for action in navigation["actions"]:
            self.assertIsInstance(action, dict)
            self.assertIsInstance(action.get("action"), str)
            self.assertTrue(action["action"])
            self.assertIsInstance(action.get("instruction"), str)
            self.assertTrue(action["instruction"].strip())
            self.assertIsInstance(action.get("required"), list)
            self.assertTrue(all(isinstance(item, str) and item for item in action["required"]))
            semantic = action["action"]
            if semantic in CALLBACK_BY_ACTION:
                self.assertEqual(action.get("operation"), CALLBACK_BY_ACTION[semantic])
            elif semantic == "reconcile":
                self.assertIn(action.get("operation"), (None, "launched"))
            elif semantic in {"return-parent", "blocked", "resume-parent", "blocked-parent", "inspect-planning-context"}:
                self.assertNotIn("operation", action)
            else:
                self.fail("unknown navigation semantic action: " + semantic)
            if semantic in ATTEMPT_ACTIONS:
                self.assertIsInstance(action.get("attempt"), str)
                self.assertTrue(action["attempt"])
            if "attempt" in action:
                self.assertIsInstance(action.get("step"), str)
                self.assertTrue(action["step"])
                self.assertIn(action["step"], bound_steps)
                self.assertEqual(action["step"], self.f.child_record(action["attempt"])["step"])
            else:
                self.assertNotIn("step", action)
            if "steps" in action:
                self.assertEqual(semantic, "claim")
                self.assertIsInstance(action["steps"], list)
                self.assertTrue(all(isinstance(step, str) and step for step in action["steps"]))
                self.assertIsInstance(action.get("max_steps"), int)
                self.assertGreaterEqual(action["max_steps"], 0)
            if "disposition" in action:
                self.assertIn(action["disposition"], {"accepted", "superseded"})
        self.navigation_trace.append({
            "operation": operation,
            "top_level_action": output.get("action"),
            "outcome": output.get("outcome"),
            "complete": navigation["complete"],
            "actions": [{key: item[key] for key in
                         ("action", "operation", "step", "attempt", "steps", "max_steps", "disposition", "required")
                         if key in item} for item in navigation["actions"]],
            "next_argv": navigation["next_argv"],
        })
        return navigation

    def execute_next_from_unrelated_cwd(self, response):
        navigation = response["navigation"]
        self.assertFalse(navigation["complete"])
        result = subprocess.run(navigation["next_argv"], cwd=self.f.primary,
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        refreshed = json.loads(result.stdout)
        self.assertIn("navigation", refreshed)
        self.assertEqual(refreshed["navigation"]["next_argv"], navigation["next_argv"])
        self.assertNotIn("node", " ".join(navigation["next_argv"]).lower())
        return refreshed

    def execute_parent_next_from_unrelated_cwd(self, response):
        navigation = response["navigation"]
        self.assertTrue(navigation["complete"])
        result = subprocess.run(navigation["next_argv"], cwd=self.f.primary,
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("ShipLoop navigator | implement |", result.stdout)
        self.assertIn("State: " + str(self.f.run / "state.md"), result.stdout)
        self.assertIn(self.f.action, result.stdout)
        return result.stdout

    def action_rows(self, response, semantic):
        return [row for row in response["navigation"]["actions"] if row["action"] == semantic]

    def retain_navigation_trace(self, labels):
        configured = os.environ.get("SHIPLOOP_CHAIN_TRACE_DIR")
        trace_dir = (Path(configured).expanduser().resolve()
                     if configured else self.f.base / "navigation-trace")
        trace_dir.mkdir(parents=True, exist_ok=True)
        selected = []
        for label, response in labels:
            navigation = response["navigation"]
            selected.append({
                "label": label,
                "top_level_action": response.get("action"),
                "outcome": response.get("outcome"),
                "top_level_complete": response.get("complete"),
                "navigation_complete": navigation["complete"],
                "actions": [{key: item[key] for key in
                             ("action", "operation", "step", "attempt", "steps", "max_steps", "disposition", "required")
                             if key in item} for item in navigation["actions"]],
                "next_argv": navigation["next_argv"],
            })
        output = trace_dir / "real-git-action-trace.json"
        temporary = output.with_suffix(".tmp")
        temporary.write_text(json.dumps({"test": self.id(), "trace": selected}, indent=2) + "\n")
        temporary.replace(output)
        return output

    def bind(self, *, mode="parallel", capacity=None, single=False, ok=True):
        if single:
            graph = json.loads(self.f.graph.read_text())
            graph["steps"] = graph["steps"][:1]
            self.f.graph.write_text(json.dumps(graph) + "\n")
        extra = [
            "--graph", str(self.f.graph), "--dispatcher-skill", str(self.f.dispatcher / "SKILL.md"),
            "--ask-agent-skill", str(self.f.ask / "SKILL.md"), "--worktree-parent", str(self.f.parent),
            "--mode", mode, "--lifecycle", "per-step",
        ]
        if capacity is not None:
            extra += ["--capacity", str(capacity)]
        return self.call("bind", ok=ok, extra=tuple(extra))

    def use_managed_ask_agent(self):
        """Restore the real managed package after an explicit negative fixture."""
        shutil.rmtree(self.f.ask)
        shutil.copytree(ROOT / "skills/ask-agent", self.f.ask)

    def use_legacy_ask_agent(self):
        """Select 0.4 only to prove fresh managed binding refuses it."""
        shutil.rmtree(self.f.ask)
        shutil.copytree(LEGACY_ASK, self.f.ask)

    def managed_capabilities(self):
        helper = self.f.ask / "scripts/ask_agent_workspace.py"
        result = subprocess.run(
            [sys.executable, "-B", str(helper), "capabilities", "--skill-card", str(self.f.ask / "SKILL.md")],
            text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return json.loads(result.stdout)

    def managed_bind(self, *, mode="parallel", capacity=None, single=False, ok=True):
        self.use_managed_ask_agent()
        return self.bind(mode=mode, capacity=capacity, single=single, ok=ok)

    def managed_start(self, step, attempt, *, serial=False, record_launch=True, base=None):
        """Start a managed attempt; serial work remains helper-owned but has no handle."""
        value = self.f.start_value(step, attempt, base=base or self.head())
        value["write_scope"] = [CHAIN_MODULES[step]["path"]]
        self.assertNotIn("workspace", value)
        self.start_inputs[step] = json.loads(json.dumps(value))
        output = self.call("start", value)
        self.assertEqual(output["action"], "execute" if serial else "launch")
        packet = output["packet"]
        self.packets[step] = packet
        packet_response = self.call("packet", {"attempt": attempt})
        self.last_start_response = output
        self.last_packet_response = packet_response
        self.assertEqual(packet_response["packet"], packet,
                         "managed cold recovery must preserve the one worker packet")
        allocation = fixture.chain._per_step_allocation(self.bridge_events(), attempt)
        self.assertEqual(allocation["adoption"], "ask-agent-managed-workspace")
        managed = allocation["ask_agent_workspace"]
        self.assertEqual(set(managed), {
            "helper", "receipt", "receipt_sha256", "worktree", "branch", "baseline", "prepare", "prepared",
        })
        self.assertEqual(packet["context"]["workspace"], managed["worktree"])
        self.assertEqual(packet["ask_agent_workspace"]["receipt"], managed["receipt"])
        self.assertEqual(packet["ask_agent_workspace"]["worktree"], managed["worktree"])
        self.assertEqual(packet["ask_agent_workspace"]["branch"], managed["branch"])
        self.assertEqual(packet["ask_agent_workspace"]["delivery"], {
            "mode": "commits", "commit_base": value["base_commit"],
            "require_complete_linear_range": True,
            "discard": [".shiploop-handoff/" + attempt],
        })
        record = self.f.child_record(attempt)
        if serial:
            self.assertIsNone(record["handle"])
            self.assertEqual(record["executor"], packet["executor"])
            self.assertEqual(packet["executor"]["kind"], "main-context")
            self.assertNotIn("native_handle", packet)
        elif record_launch:
            self.call("launched", {"attempt": attempt, "handle": {
                "host": "deterministic-process-fixture", "id": step,
            }})
        return packet

    def managed_context_check(self, step):
        """Exercise the packet's public operation-directory check before work."""
        packet = self.packets[step]
        context = packet["ask_agent_workspace"]["check_context"]
        self.assertEqual(context["cwd"], packet["context"]["workspace"])
        environment = {
            key: value for key, value in os.environ.items()
            if not key.startswith("GIT_")
        }
        result = subprocess.run(context["argv"], cwd=context["cwd"], env=environment,
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        checked = json.loads(result.stdout)
        self.assertEqual(checked["status"], "verified")
        self.assertEqual(checked["worktree"], context["cwd"])
        return checked

    def managed_worker_result(self, step, *, commits=1, manifest_commit=None):
        """Make a real committed range plus the normal worker-local handoff."""
        packet = self.packets[step]
        workspace = Path(packet["context"]["workspace"])
        module = CHAIN_MODULES[step]
        path = workspace / module["path"]
        git = ("git", "-c", "user.name=Chain Code Fixture", "-c",
               "user.email=chain@example.invalid", "-C", str(workspace))
        commits_created = []
        if commits == 2:
            path.write_text(module["source"] + "\n# intermediate worker commit\n")
            staged = subprocess.run([*git, "add", module["path"]], text=True,
                                    capture_output=True, timeout=30)
            self.assertEqual(staged.returncode, 0, staged.stderr)
            first = subprocess.run([*git, "commit", "-qm", "Stage " + step], text=True,
                                   capture_output=True, timeout=30)
            self.assertEqual(first.returncode, 0, first.stderr)
            commits_created.append(subprocess.check_output([*git, "rev-parse", "HEAD"], text=True).strip())
        path.write_text(module["source"])
        staged = subprocess.run([*git, "add", module["path"]], text=True,
                                capture_output=True, timeout=30)
        self.assertEqual(staged.returncode, 0, staged.stderr)
        committed = subprocess.run([*git, "commit", "-qm", "Implement " + step], text=True,
                                   capture_output=True, timeout=30)
        self.assertEqual(committed.returncode, 0, committed.stderr)
        head = subprocess.check_output([*git, "rev-parse", "HEAD"], text=True).strip()
        commits_created.append(head)
        handoff = workspace / ".shiploop-handoff" / packet["attempt"] / "handoff.json"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        checks = handoff.parent / "checks.json"
        checks.write_text(json.dumps({
            "passed": True, "cwd": str(workspace), "git_root": str(workspace),
            "commit": head, "fixture_worker": True,
        }) + "\n")
        reported_commit = manifest_commit or head
        manifest = {
            "schema": "shiploop-chain-handoff/v1", "run_id": packet["run_id"],
            "step": step, "attempt": packet["attempt"],
            "base_commit": packet["context"]["base_commit"], "status": "SUCCEEDED",
            "commit": reported_commit, "summary": "Generated and checked " + module["path"],
            "files": [{"path": "checks.json", "sha256": hashlib.sha256(checks.read_bytes()).hexdigest()}],
        }
        handoff.write_text(json.dumps(manifest) + "\n")
        result = {
            "handoff": str(handoff), "sha256": hashlib.sha256(handoff.read_bytes()).hexdigest(),
            "commit": head, "commits": commits_created, "phase": "completed",
        }
        self.source_commits[step] = head
        return result

    def managed_non_success_handoff(self, step, status):
        """Return a stopped BLOCKED/FAILED worker without inventing a commit."""
        self.assertIn(status, {"BLOCKED", "FAILED"})
        packet = self.packets[step]
        workspace = Path(packet["context"]["workspace"])
        handoff = workspace / ".shiploop-handoff" / packet["attempt"] / "handoff.json"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        detail = handoff.parent / "detail.json"
        detail.write_text(json.dumps({"status": status, "stopped": True, "fixture_worker": True}) + "\n")
        manifest = {
            "schema": "shiploop-chain-handoff/v1", "run_id": packet["run_id"],
            "step": step, "attempt": packet["attempt"],
            "base_commit": packet["context"]["base_commit"], "status": status,
            "commit": None, "summary": "Fixture " + status.lower() + " before code changes",
            "files": [{"path": "detail.json", "sha256": hashlib.sha256(detail.read_bytes()).hexdigest()}],
        }
        handoff.write_text(json.dumps(manifest) + "\n")
        return {
            "handoff": str(handoff), "sha256": hashlib.sha256(handoff.read_bytes()).hexdigest(),
            "commit": None, "phase": "completed",
        }

    def managed_collect(self, step, *, commits=1, manifest_commit=None):
        self.managed_context_check(step)
        result = self.managed_worker_result(step, commits=commits, manifest_commit=manifest_commit)
        return self.import_finished(step, result), result

    def head(self):
        return self.f.git(self.f.target, "rev-parse", "HEAD")

    def claim(self, *steps):
        output = self.call("claim", {"steps": list(steps)})
        self.last_claim_response = output
        return {claim["step"]: claim["attempt"] for claim in output["claims"]}

    def start(self, step, attempt, *, serial=False, record_launch=True, base=None):
        """All fresh deterministic starts use the managed helper, never a workspace input."""
        packet = self.managed_start(step, attempt, serial=serial,
                                    record_launch=record_launch, base=base)
        self.assertEqual(self.last_packet_response["packet"], packet,
                         "cold recovery must preserve the helper-owned worker packet")
        self.assertEqual(packet["context"]["base_commit"], base or self.head())
        for external in ("outputs", "report_argv", "report_envelope"):
            self.assertNotIn(external, packet)
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
        return self.import_finished(step, result)

    def import_finished(self, step, result):
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

    def graph_steps(self):
        return tuple(item["id"] for item in self.binding()["graph"]["steps"])

    def expected_worker_steps(self, step):
        graph = self.binding()["graph"]
        dependencies = {item["id"]: tuple(item["deps"]) for item in graph["steps"]}
        required = set()

        def include(item):
            if item in required:
                return
            required.add(item)
            for dependency in dependencies[item]:
                include(dependency)

        include(step)
        return tuple(item["id"] for item in graph["steps"] if item["id"] in required)

    def expected_prepared_steps(self, step):
        required = set(self.accepted_steps()) | set(self.expected_worker_steps(step))
        return tuple(item for item in self.graph_steps() if item in required)

    def accepted_steps(self):
        state = self.f.child_state()
        return tuple(step for step in self.graph_steps()
                     if state["steps"][step]["status"] == "accepted")

    def accepted_contributions(self):
        state = self.f.child_state()
        accepted = self.accepted_steps()
        current = {step: state["steps"][step]["current_attempt"] for step in accepted}
        contributions = {}
        for row in self.bridge_events():
            event = row["event"]
            if event["kind"] == "contribution_recorded":
                data = event["data"]
                if data.get("attempt") in current.values():
                    contributions[data["attempt"]] = data
        self.assertEqual(set(contributions), set(current.values()))
        for step, attempt in current.items():
            self.assertEqual(contributions[attempt]["step"], step)
        return tuple(contributions[current[step]] for step in accepted)

    def assert_contiguous_integrations(self, attempts):
        events = [row["event"]["data"] for row in self.bridge_events()
                  if row["event"]["kind"] == "integration_result"]
        self.assertEqual([event["attempt"] for event in events], list(attempts))
        previous = self.binding()["target"]["head"]
        for event in events:
            self.assertEqual(event["target_before"]["head"], previous)
            self.assertEqual(event["target_after"]["head"], event["integration"]["candidate_commit"])
            previous = event["target_after"]["head"]
        self.assertEqual(self.head(), previous)

    def verify(self, workspace, *, expected_steps):
        expected = tuple(expected_steps)
        self.assertTrue(expected, "verification needs at least one expected contribution")
        self.assertEqual(len(expected), len(set(expected)), "expected contributions must be unique")
        self.assertTrue(set(expected).issubset(CHAIN_MODULES), "unknown expected contribution")
        workspace = Path(workspace)
        for step in expected:
            module = CHAIN_MODULES[step]
            self.assertTrue((workspace / module["path"]).is_file(),
                            "missing expected contribution " + module["path"])
        check = "\n".join(CHAIN_MODULES[step]["check"] for step in expected)
        result = subprocess.run([sys.executable, "-B", "-c", check], cwd=workspace,
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def prepared_input(self, step):
        attempt = self.packets[step]["attempt"]
        prepared = self.call("prepare", {"attempt": attempt, "confirmed_stopped": True})
        integration = prepared["integration"]
        self.verify(Path(self.packets[step]["context"]["workspace"]),
                    expected_steps=self.expected_prepared_steps(step))
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

    def run_deferred_managed_cleanup(self, step, output):
        cleanup = output.get("cleanup")
        if not isinstance(cleanup, dict) or cleanup.get("deferred") is not True:
            return None
        attempt = self.packets[step]["attempt"]
        self.assertEqual(cleanup, {
            "attempt": attempt,
            "cleanup": None,
            "pending": True,
            "deferred": True,
        })
        return self.call("cleanup", {"attempt": attempt, "confirmed_stopped": True})

    def prepare_and_done(self, step, *, close_deferred=True):
        value = self.prepared_input(step)
        integration = value["integration"]
        before = self.f.ledger_bytes()
        output = self.call("done", value)
        self.assertEqual(output["outcome"], "accepted")
        self.assertEqual(output["step"], step)
        self.assertEqual(output["attempt"], value["attempt"])
        self.assertEqual(self.head(), integration["candidate_commit"])
        deferred = isinstance(output.get("cleanup"), dict) and output["cleanup"].get("deferred") is True
        if deferred and close_deferred:
            cleaned = self.run_deferred_managed_cleanup(step, output)
            self.assertIsNotNone(cleaned)
            self.assertFalse(cleaned["pending"])
        workspace = Path(self.packets[step]["context"]["workspace"])
        if deferred and not close_deferred:
            self.assertTrue(workspace.exists())
        else:
            self.assertFalse(workspace.exists())
        after = self.f.ledger_bytes()
        self.assertTrue(all(after.get(k) == v for k, v in before.items()))
        self.verify(self.f.target, expected_steps=self.accepted_steps())
        return output

    def accept_managed_a_with_deferred_cleanup(self):
        self.managed_bind(single=True)
        attempt = self.claim("A")["A"]
        packet = self.managed_start("A", attempt)
        self.managed_context_check("A")
        self.import_finished("A", self.managed_worker_result("A"))
        settled = self.prepare_and_done("A", close_deferred=False)
        self.assertEqual(settled["cleanup"], {
            "attempt": attempt,
            "cleanup": None,
            "pending": True,
            "deferred": True,
        })
        return attempt, packet

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
        self.assertEqual(self.accepted_steps(), self.graph_steps())
        self.verify(self.f.target, expected_steps=self.graph_steps())
        contributions = self.accepted_contributions()
        proof = self.f.write("final-combined.json", {"passed": True, "commit": head,
                            "checks": ["combined generated-code output and all source ancestry"]})
        finished = self.call("finish", {"commit": head, "confirmed_stopped": True,
                  "verification": {"path": str(proof), "sha256": fixture.digest(proof)}})
        self.assertTrue(finished["complete"])
        self.assertEqual(self.f.git(self.f.primary, "rev-parse", "HEAD"), self.f.initial)
        listing = self.f.git(self.f.primary, "worktree", "list", "--porcelain")
        self.assertEqual(listing.count("worktree "), 2, listing)
        for contribution in contributions:
            self.f.git(self.f.target, "merge-base", "--is-ancestor", contribution["source_commit"], head)
        self.assertEqual(self.call("pending")["completion"]["not_done"], [])
        return finished
