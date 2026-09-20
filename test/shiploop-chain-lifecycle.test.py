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
            "--mode", mode,
        ]
        if capacity is not None:
            extra += ["--capacity", str(capacity)]
        return self.call("bind", ok=ok, extra=tuple(extra))

    def head(self):
        return self.f.git(self.f.target, "rev-parse", "HEAD")

    def claim(self, *steps):
        output = self.call("claim", {"steps": list(steps)})
        self.last_claim_response = output
        return {claim["step"]: claim["attempt"] for claim in output["claims"]}

    def start(self, step, attempt, *, serial=False, record_launch=True):
        base = self.head()
        value = self.f.start_value(step, attempt, base=base)
        value["write_scope"] = [CHAIN_MODULES[step]["path"]]
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
        self.start_inputs[step] = json.loads(json.dumps(value))
        output = self.call("start", value)
        self.assertEqual(output["action"], "execute" if serial else "launch")
        self.last_start_response = output
        packet = output["packet"]
        self.packets[step] = packet
        packet_response = self.call("packet", {"attempt": attempt})
        self.last_packet_response = packet_response
        recovered = packet_response["packet"]
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

    def prepare_and_done(self, step):
        value = self.prepared_input(step)
        integration = value["integration"]
        before = self.f.ledger_bytes()
        output = self.call("done", value)
        self.assertEqual(output["outcome"], "accepted")
        self.assertEqual(output["step"], step)
        self.assertEqual(output["attempt"], value["attempt"])
        self.assertEqual(self.head(), integration["candidate_commit"])
        self.assertFalse(Path(self.packets[step]["context"]["workspace"]).exists())
        after = self.f.ledger_bytes()
        self.assertTrue(all(after.get(k) == v for k, v in before.items()))
        self.verify(self.f.target, expected_steps=self.accepted_steps())
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

        assert_rejected_without_mutation(old_positive, "stale or retried")
        self.assertIn("J", self.call("next")["ready"])
        old_ancestry = subprocess.run(["git", "merge-base", "--is-ancestor", old_source, self.head()],
                                      cwd=self.f.target, capture_output=True, timeout=15)
        self.assertNotEqual(old_ancestry.returncode, 0)

        self.call("cleanup", {"attempt": attempts["B"], "confirmed_stopped": True,
                                "disposition": "superseded",
                                "reason": "Replacement B was accepted and integrated"})
        j_attempt = self.claim("J")["J"]
        self.start("J", j_attempt)
        self.complete_step("J")
        self.assert_contiguous_integrations((attempts["A"], c_attempt, replacement, j_attempt))
        self.finish()

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
        replayed_start = self.call("start", self.start_inputs["B"], ok=False)
        self.assertNotEqual(replayed_start.returncode, 0)
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
        self.assertEqual([row["action"] for row in j_done["navigation"]["actions"]], ["finish"])
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
            self.start(step, attempt, serial=True)
            self.assertEqual([row["attempt"] for row in self.action_rows(self.last_start_response, "execute")],
                             [attempt])
            self.assertFalse(self.action_rows(self.last_start_response, "launch"),
                             "serial navigation must not offer a native launch callback")
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
