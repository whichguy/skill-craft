#!/usr/bin/env python3
"""Focused composition coverage for ShipLoop's immutable planning handoff.

These checks use the real public bridge, pinned Plan Dispatcher package, real
Git worktrees, and a deterministic worker.  They do not claim native/model
qualification.
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


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
WORKER = ROOT / "test" / "fixtures" / "chain-planning-context-worker.py"
MANAGED_WORKTREE_SCHEMA = "shiploop-chain-ask-agent-managed-worktree/v1"
MANAGED_WORKTREE_CAPABILITIES = [
    "helper-managed-worktree",
    "prepared-inspection",
    "returned-commit-delivery",
    "fingerprint-bound-close",
]
GUIDANCE_ROUTES = {
    "Coding decision guide": "coding-guidance.md#select-guidance",
    "Repeatable test-suite guide": "repeatable-test-suites.md#select-or-revalidate-the-harness",
    "Implementation constitution": "testing-and-documentation.md#implementation-constitution",
}

from shiploop_chain_support import digest
import shiploop_chain_support as fixture


class PlanningContextChainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.f = self.new_fixture()

    def new_fixture(self):
        test = fixture.ChainFixture(methodName="runTest")
        self.addCleanup(test.doCleanups)
        test.setUp()
        test.select_dispatcher(fixture.CONTEXT_FIXTURE)
        return test

    def stop_context_worker(self, process: subprocess.Popen[str]) -> None:
        try:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=10)
        finally:
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None and not stream.closed:
                    stream.close()

    def bind(self, test, *, mode: str = "parallel", capacity: int | None = None,
             lifecycle: str = "per-step", ok: bool = True):
        extra = [
            "--graph", str(test.graph),
            "--dispatcher-skill", str(test.dispatcher / "SKILL.md"),
            "--ask-agent-skill", str(test.ask / "SKILL.md"),
            "--worktree-parent", str(test.parent),
            "--mode", mode,
            "--lifecycle", lifecycle,
        ]
        if capacity is not None:
            extra += ["--capacity", str(capacity)]
        return test.call("bind", ok=ok, extra=tuple(extra))

    def managed_identity(self, test) -> dict:
        card = test.ask / "SKILL.md"
        helper = test.ask / "scripts" / "ask_agent_workspace.py"
        version = re.search(r"(?m)^version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", card.read_text())
        self.assertIsNotNone(version)
        result = subprocess.run(
            [sys.executable, "-B", str(helper), "identity", "--skill-card", str(card)],
            text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        identity = json.loads(result.stdout)
        self.assertEqual(identity, {
            "status": "verified",
            "schema": "ask-agent.skill.identity.v1",
            "skill_card": str(card),
            "resolved_skill_card": str(card.resolve()),
            "resolved_helper": str(helper.resolve()),
            "version": version.group(1),
            "skill_card_sha256": digest(card.resolve()),
            "helper_sha256": digest(helper.resolve()),
        })
        return identity

    def managed_capabilities(self, test) -> dict:
        card = test.ask / "SKILL.md"
        helper = test.ask / "scripts" / "ask_agent_workspace.py"
        identity = self.managed_identity(test)
        result = subprocess.run(
            [sys.executable, "-B", str(helper), "capabilities", "--skill-card", str(card)],
            text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        declared = json.loads(result.stdout)
        self.assertEqual(declared, {
            "schema": MANAGED_WORKTREE_SCHEMA,
            "version": identity["version"],
            "capabilities": MANAGED_WORKTREE_CAPABILITIES,
        })
        return declared

    def assert_managed_binding(self, test, binding: dict) -> None:
        identity = self.managed_identity(test)
        self.assertEqual(binding["schema"], "shiploop-chain-binding/v6")
        self.assertEqual(binding["lifecycle"], "per-step")
        self.assertEqual(binding["ask_agent_contract"], self.managed_capabilities(test))
        self.assertEqual(binding["ask_agent_identity"], {
            "schema": "shiploop-chain-ask-agent-identity/v1",
            "method": "helper-v1",
            "logical_skill_card": identity["skill_card"],
            "resolved_skill_card": identity["resolved_skill_card"],
            "resolved_helper": identity["resolved_helper"],
            "version": identity["version"],
            "skill_card_sha256": identity["skill_card_sha256"],
            "helper_sha256": identity["helper_sha256"],
        })
        self.assertIn("scripts/ask_agent_workspace.py", binding["ask_agent"]["files"])

    def planning_inputs(self, test):
        command = [
            sys.executable, "-B", str(CLI), "chain", "planning-inputs",
            "--run-dir", str(test.run), "--action", test.action, "--graph", str(test.graph),
        ]
        result = subprocess.run(command, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return json.loads(result.stdout)

    def binding_and_manifest(self, test):
        binding = fixture.store.read_record(test.run / "chains" / test.action / "binding.md")
        context = binding["planning_context"]
        manifest = json.loads(Path(context["path"]).read_text())
        return binding, context, manifest

    def validate_graph(self, test, graph: dict) -> subprocess.CompletedProcess[str]:
        """Call the selected helper's run-free graph-validation boundary."""
        request = test.write("validate-graph.json", {"graph": graph})
        return subprocess.run(
            [fixture.chain._node_path(), str(test.dispatcher / "scripts" / "dispatch.js"),
             "validate-graph", str(request)],
            text=True, capture_output=True, timeout=30,
        )

    def assert_packet_context(self, test, packet, context, manifest) -> None:
        steps = {row["id"]: row["contract"] for row in json.loads(test.graph.read_text())["steps"]}
        contract = steps[packet["step"]]
        self.assertEqual(packet["task"], contract["task"])
        self.assertEqual(packet["assignment"]["task"], contract["task"])
        self.assertEqual(packet["assignment"]["definition_of_ready"], contract["ready"])
        self.assertEqual(packet["assignment"]["definition_of_done"], contract["done"])
        self.assertNotIn("goal", packet)
        self.assertEqual(packet["planning_context"], context)
        self.assertEqual(packet["planning_brief"], manifest["briefing"])
        self.assertIsInstance(packet["reference_material"], list)
        self.assertTrue(packet["reference_material"])
        for reference in packet["reference_material"]:
            self.assertTrue({"path", "sha256", "roles", "producers", "classification", "required_for"}
                            <= set(reference))
            self.assertEqual(digest(Path(reference["path"])), reference["sha256"])
        self.assertTrue(any(
            Path(reference["path"]).name == "context-code-contract.json"
            for reference in packet["reference_material"]
        ))
        instructions = "\n".join(packet["instructions"]).lower()
        self.assertIn("step contract defines your execution prompt", instructions)
        self.assertIn("key planning reference statements", instructions)
        self.assertIn("do not replace the step definition", instructions)
        self.assertIn("material discoveries", instructions)
        self.assertIn("decision rationale", instructions)
        self.assertIn("unresolved uncertainty", instructions)
        self.assertIn("summary", instructions)
        self.assertIn("declared files", instructions)
        self.assertIn("before affected work", instructions)
        self.assertIn("no new findings", instructions)
        self.assertNotIn("launch the native task", instructions)
        self.assertNotIn("worker launch payload", instructions)
        # Context is passed as immutable references, rather than copying the
        # large planning body into each worker packet.
        self.assertNotIn("Use sibling worker worktrees", json.dumps(packet))

    def assert_worker_guidance(self, packet, package: Path = SCRIPTS.parent) -> None:
        """Follow the actual worker's locators, including the selector's cards."""
        references = package / "references"
        for label, relative in GUIDANCE_ROUTES.items():
            locator = str(references / relative)
            self.assertEqual(packet["instructions"].count(label + ": " + locator), 1)
            path, anchor = locator.split("#", 1)
            body = Path(path).read_text()
            headings = {
                re.sub(r"[^a-z0-9 -]", "", line.lstrip("# ").lower()).replace(" ", "-")
                for line in body.splitlines() if line.startswith("#")
            }
            self.assertIn(anchor, headings, locator)
        selector = (references / "coding-guidance.md").read_text()
        links = re.findall(r"\]\(([^)]+)\)", selector)
        for relative in links:
            path, _, anchor = relative.partition("#")
            card = references / path
            self.assertTrue(card.is_file(), relative)
            if anchor:
                headings = {
                    re.sub(r"[^a-z0-9 -]", "", line.lstrip("# ").lower()).replace(" ", "-")
                    for line in card.read_text().splitlines() if line.startswith("#")
                }
                self.assertIn(anchor, headings, relative)
        self.assertTrue({"platforms/" + name + ".md" for name in (
            "ui", "apps-script", "salesforce", "python", "bash"
        )} <= set(links))
        # Route references; do not paste every platform's implementation advice.
        self.assertNotIn("google.script.run", json.dumps(packet))
        self.assertNotIn("set -euo pipefail", json.dumps(packet))

    def claim(self, test, *steps: str) -> dict[str, str]:
        response = test.call("claim", {"steps": list(steps)})
        return {row["step"]: row["attempt"] for row in response["claims"]}

    def assert_managed_workspace(self, test, packet: dict, value: dict, *, serial: bool) -> None:
        attempt = packet["attempt"]
        self.assertNotIn("workspace", value)
        rows = fixture.chain._events(test.run / "chains" / test.action)
        allocation = fixture.chain._per_step_allocation(rows, attempt)
        self.assertEqual(allocation["adoption"], "ask-agent-managed-workspace")
        managed = allocation["ask_agent_workspace"]
        self.assertEqual(packet["context"]["workspace"], managed["worktree"])
        self.assertEqual(packet["ask_agent_workspace"]["receipt"], managed["receipt"])
        self.assertEqual(packet["ask_agent_workspace"]["worktree"], managed["worktree"])
        self.assertEqual(packet["ask_agent_workspace"]["branch"], managed["branch"])
        self.assertEqual(packet["ask_agent_workspace"]["delivery"], {
            "mode": "commits",
            "commit_base": value["base_commit"],
            "require_complete_linear_range": True,
            "discard": [".shiploop-handoff/" + attempt],
        })
        workspace = Path(packet["context"]["workspace"])
        self.assertTrue(workspace.is_dir())
        self.assertTrue(workspace.is_relative_to(test.parent / "ask-agent"))
        if serial:
            record = test.child_record(attempt)
            self.assertIsNone(record["handle"])
            self.assertEqual(record["executor"], packet["executor"])
            self.assertEqual(packet["executor"]["kind"], "main-context")
            self.assertNotIn("native_handle", packet)

    def check_managed_context(self, packet: dict) -> dict:
        context = packet["ask_agent_workspace"]["check_context"]
        self.assertEqual(context["cwd"], packet["context"]["workspace"])
        environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        result = subprocess.run(
            context["argv"], cwd=context["cwd"], env=environment,
            text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        checked = json.loads(result.stdout)
        self.assertEqual(checked["status"], "verified")
        self.assertEqual(checked["worktree"], context["cwd"])
        return checked

    def start_parallel(self, test, step: str, attempt: str, write_scope: list[str]):
        value = test.start_value(step, attempt, base=test.git(test.target, "rev-parse", "HEAD"))
        value["write_scope"] = write_scope
        output = test.call("start", value)
        self.assertEqual(output["action"], "launch")
        packet = output["packet"]
        test.packets[step] = packet
        self.assert_managed_workspace(test, packet, value, serial=False)
        test.call("launched", {"attempt": attempt, "handle": {
            "host": "planning-context-fixture", "id": step,
        }})
        return packet

    def start_serial(self, test, step: str, attempt: str, write_scope: list[str]):
        value = test.start_value(step, attempt, base=test.git(test.target, "rev-parse", "HEAD"))
        value["write_scope"] = write_scope
        output = test.call("start", value)
        self.assertEqual(output["action"], "execute")
        packet = output["packet"]
        test.packets[step] = packet
        self.assert_managed_workspace(test, packet, value, serial=True)
        return packet

    def read_json_line(self, process: subprocess.Popen[str]) -> dict:
        assert process.stdout is not None and process.stderr is not None
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            self.assertTrue(selector.select(15), "planning-context worker did not reach its barrier")
        line = process.stdout.readline()
        if not line:
            self.fail("planning-context worker stopped: " + process.stderr.read())
        return json.loads(line)

    def launch_context_worker(self, test, step: str):
        packet = test.packets[step]
        self.check_managed_context(packet)
        assignment = {
            "step": step,
            "run_id": packet["run_id"],
            "attempt": packet["attempt"],
            "base_commit": packet["context"]["base_commit"],
            "workspace": packet["context"]["workspace"],
            "packet": packet,
        }
        process = subprocess.Popen(
            [sys.executable, "-B", str(WORKER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
        )
        self.addCleanup(self.stop_context_worker, process)
        assert process.stdin is not None
        process.stdin.write(json.dumps(assignment) + "\n")
        process.stdin.flush()
        ready = self.read_json_line(process)
        self.assertEqual(ready["phase"], "code_ready")
        self.assertEqual(ready["cwd"], assignment["workspace"])
        self.assertEqual(ready["planning_brief"], packet["planning_brief"]["path"])
        self.assertEqual(ready["guidance_references"], {
            label: str(SCRIPTS.parent / "references" / relative.split("#", 1)[0])
            for label, relative in GUIDANCE_ROUTES.items()
        })
        return process

    def finish_context_worker(self, process: subprocess.Popen[str]) -> dict:
        assert process.stdin is not None and process.stderr is not None
        process.stdin.write("release\n")
        process.stdin.flush()
        result = self.read_json_line(process)
        self.assertEqual(process.wait(timeout=15), 0, process.stderr.read())
        self.assertEqual(result["phase"], "completed")
        return result

    def test_failed_barrier_worker_stops_before_fixture_worktree_cleanup(self) -> None:
        observations = []
        state = {}

        class FailedLaunch(PlanningContextChainTests):
            def setUp(inner) -> None:
                super().setUp()
                inner.bind(inner.f, mode="parallel", capacity=1)
                attempt = inner.claim(inner.f, "A")["A"]
                inner.start_parallel(inner.f, "A", attempt, ["context_alpha.py"])
                workspace = Path(inner.f.packets["A"]["context"]["workspace"])
                process_ref = {}

                def observe_cleanup() -> None:
                    process = process_ref["process"]
                    stopped = process.poll() is not None
                    observations.append((stopped, workspace.exists()))
                    inner.assertTrue(stopped, "worker must stop before fixture cleanup")
                    inner.assertTrue(workspace.exists(), "fixture cleanup ran before worker cleanup")

                # This observer is registered before Popen.  The worker's own
                # cleanup must be added immediately after Popen, so it runs
                # first; the fixture cleanup is older still.
                inner.addCleanup(observe_cleanup)
                process = inner.launch_context_worker(inner.f, "A")
                process_ref["process"] = process
                state["process"] = process
                state["workspace"] = workspace

            def runTest(inner) -> None:
                inner.fail("intentional assertion after barrier-worker launch")

        result = unittest.TestResult()
        FailedLaunch().run(result)
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(result.errors, [])
        self.assertIn("intentional assertion after barrier-worker launch", result.failures[0][1])
        self.assertEqual(observations, [(True, True)])
        process = state["process"]
        self.assertIsNotNone(process.poll())
        self.assertTrue(all(
            stream is None or stream.closed
            for stream in (process.stdin, process.stdout, process.stderr)
        ))
        self.assertFalse(state["workspace"].exists())

    def test_partial_nested_fixture_setup_runs_registered_cleanup(self) -> None:
        observed = {}
        original_setup = fixture.ChainFixture.setUp

        def partial_setup(test) -> None:
            original_setup(test)
            observed["fixture"] = test
            observed["base"] = test.base
            raise RuntimeError("intentional partial fixture setup failure")

        class PartialFixtureSetup(PlanningContextChainTests):
            def setUp(inner) -> None:
                with patch.object(fixture.ChainFixture, "setUp", partial_setup):
                    super().setUp()

            def runTest(inner) -> None:
                inner.fail("partial fixture setup unexpectedly completed")

        result = unittest.TestResult()
        PartialFixtureSetup().run(result)
        self.assertEqual(result.failures, [])
        self.assertEqual(len(result.errors), 1)
        self.assertIn("intentional partial fixture setup failure", result.errors[0][1])
        nested = observed["fixture"]
        try:
            self.assertFalse(observed["base"].exists())
        finally:
            nested.doCleanups()

    def collect(self, test, step: str, result: dict, *, expect_prepare: bool = True):
        imported = test.call("import-handoff", {
            "attempt": test.packets[step]["attempt"],
            "confirmed_stopped": True,
            "handoff": {"path": result["handoff"], "sha256": result["sha256"]},
        })
        delivery = imported["ask_agent_delivery"]
        self.assertEqual(delivery["attempt"], test.packets[step]["attempt"])
        self.assertEqual(delivery["source_commit"], result["commit"])
        self.assertEqual(delivery["workspace"], test.packets[step]["context"]["workspace"])
        self.assertEqual(delivery["commits"][-1], result["commit"])
        archived = imported["import"]
        summary = json.loads(Path(archived["handoff"]["archived_path"]).read_text())["summary"]
        self.assertEqual(summary, archived["summary"])
        self.assertIn("Parent: inspect checks.json", summary)
        actions = imported["navigation"]["actions"]
        if expect_prepare:
            prepare = next(action for action in actions if action["action"] == "prepare")
            self.assertIn("retain material findings", prepare["instruction"])
        else:
            self.assertFalse(any(action["action"] == "prepare" for action in actions))
            self.assertTrue(any(action["action"] == "inspect-planning-context" for action in actions))
        return imported

    def assert_supplier_findings_survive_cleanup(self, test, packet):
        self.assertEqual({row["step"] for row in packet["dependencies"]}, {"A", "B"})
        for supplier in packet["dependencies"]:
            self.assertFalse(Path(test.packets[supplier["step"]]["context"]["workspace"]).exists())
            archived_manifest = json.loads(Path(supplier["handoff"]["archived_path"]).read_text())
            archive = next(row for row in supplier["archives"] if row["path"] == "checks.json")
            evidence = json.loads(Path(archive["archived_path"]).read_text())
            self.assertEqual(digest(Path(archive["archived_path"])), archive["sha256"])
            for key in ("finding", "rationale", "uncertainty"):
                self.assertIn(evidence[key], archived_manifest["summary"])
        cold = test.call("packet", {"attempt": packet["attempt"]})["packet"]
        self.assertEqual(cold["dependencies"], packet["dependencies"])

    def verify_context_code(self, workspace: Path, step: str) -> None:
        checks = {
            "A": "from context_alpha import alpha; assert alpha() == 'alpha'",
            "B": "from context_beta import beta; assert beta() == 'beta'",
            "C": "from context_join import joined; assert joined() == 'alpha-beta'",
        }
        result = subprocess.run([sys.executable, "-B", "-c", checks[step]], cwd=workspace,
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def prepare_and_accept(self, test, step: str):
        attempt = test.packets[step]["attempt"]
        workspace = Path(test.packets[step]["context"]["workspace"])
        prepared = test.call("prepare", {"attempt": attempt, "confirmed_stopped": True})
        verify = next(action for action in prepared["navigation"]["actions"] if action["action"] == "verify")
        self.assertIn("Read the imported summary", verify["instruction"])
        integration = prepared["integration"]
        self.verify_context_code(workspace, step)
        binding, _context, _manifest = self.binding_and_manifest(test)
        receipt = fixture.chain._node(binding, "receipt", {"attempt": attempt})
        proof = test.write("context-verified-" + step + ".json", {
            "passed": True,
            "integration": integration,
            "checks": ["code generated from immutable planning reference", "combined target behavior"],
        })
        value = {
            "attempt": attempt,
            "confirmed_stopped": True,
            "integration": integration,
            "verification": {
                "receipt_sha256": receipt["sha256"],
                "passed": True,
                "reason": "Independent context-code behavior verification",
                "evidence": {"path": str(proof), "sha256": digest(proof)},
            },
        }
        accepted = test.call("done", value)
        self.assertEqual(accepted["outcome"], "accepted")
        self.assertEqual(test.git(test.target, "rev-parse", "HEAD"), integration["candidate_commit"])
        self.assertEqual(accepted["cleanup"], {
            "attempt": attempt,
            "cleanup": None,
            "pending": True,
            "deferred": True,
        })
        self.assertTrue(workspace.exists())
        cleaned = test.call("cleanup", {"attempt": attempt, "confirmed_stopped": True})
        self.assertFalse(cleaned["pending"])
        self.assertEqual(cleaned["cleanup"]["close"]["status"], "closed")
        self.assertFalse(workspace.exists())
        return accepted

    def test_readonly_inventory_and_bind_freeze_consolidated_planning_material(self) -> None:
        graph_bytes = self.f.graph.read_bytes()
        before = self.f.run_bytes()
        preview = self.planning_inputs(self.f)
        self.assertEqual(self.f.run_bytes(), before)
        self.assertEqual(preview["view"], "planning-inputs")
        self.assertEqual(preview["missing_required"], [])
        self.assertEqual(preview["manifest"]["graph"], {
            "path": str(self.f.graph.resolve()), "sha256": digest(self.f.graph),
        })
        self.assertIn("chains/" + self.f.action + "/planning-brief.md", preview["planned_files"])
        self.assertIn("chains/" + self.f.action + "/planning-projection.json", preview["planned_files"])
        historical = [row for row in preview["manifest"]["unresolved_refs"]
                      if row["text"] == str(self.f.historical_missing)]
        self.assertEqual(len(historical), 1)
        self.assertEqual(historical[0]["required_for"], [])

        bound = self.bind(self.f)
        binding, context, manifest = self.binding_and_manifest(self.f)
        self.assert_managed_binding(self.f, binding)
        self.assertEqual(bound["planning_context"], context)
        self.assertEqual(manifest["schema"], "shiploop-planning-artifacts/v1")
        self.assertEqual(manifest["source"]["run_id"], self.f.state["run_id"])
        self.assertEqual(manifest["source"]["action_id"], self.f.action)
        self.assertEqual(manifest["graph"], {
            "path": str(self.f.graph.resolve()), "sha256": digest(self.f.graph),
        })
        self.assertEqual(self.f.graph.read_bytes(), graph_bytes)
        artifact_paths = {row["path"] for row in manifest["artifacts"]}
        self.assertTrue(all(str(self.f.run / "results" / (action + ".md")) in artifact_paths
                            for action in self.f.planning_action_ids))
        self.assertTrue(all(
            str(self.f.run / "improve" / action / "receipt.md") in artifact_paths
            for action in self.f.planning_action_ids
        ))
        self.assertTrue(any("improve-receipt" in row["roles"] for row in manifest["artifacts"]))
        self.assertTrue(any("improve-evidence" in row["roles"] for row in manifest["artifacts"]))
        self.assertNotIn(str(self.f.run / "state.md"), artifact_paths)
        brief = Path(manifest["briefing"]["path"])
        self.assertEqual(digest(brief), manifest["briefing"]["sha256"])
        brief_text = brief.read_text()
        self.assertIn("# Planning reference statements", brief_text)
        self.assertIn("sole task prompt", brief_text)
        self.assertIn("Architecture decision", brief_text)
        self.assertIn("Synthetic plan decision", brief_text)
        self.assertIn("Synthetic Improve for plan", brief_text)
        self.assertNotIn(self.f.original_prompt_sentinel, brief_text)
        projection = json.loads((self.f.run / "chains" / self.f.action / "planning-projection.json").read_text())
        self.assertNotIn("prompt", projection)
        self.assertNotIn(self.f.original_prompt_sentinel, json.dumps(projection))
        self.assertNotIn("status", json.dumps(projection))
        self.assertNotIn("active_improve", json.dumps(projection))

    def test_versionless_steps_graph_adapter_keeps_the_original_source_bytes(self) -> None:
        raw = (
            b'{"steps":[{"id":"A","deps":[],"contract":{"task":"Adapter task",'
            b'"ready":["input"],"done":["output"]}}]}\n'
        )
        self.f.graph.write_bytes(raw)
        self.bind(self.f)
        binding, _context, manifest = self.binding_and_manifest(self.f)
        self.assertEqual(self.f.graph.read_bytes(), raw)
        self.assertEqual(manifest["graph"], {
            "path": str(self.f.graph.resolve()), "sha256": digest(self.f.graph),
        })
        self.assertEqual(binding["graph"], {
            "version": 1,
            "steps": [{
                "id": "A", "deps": [],
                "contract": {"task": "Adapter task", "ready": ["input"], "done": ["output"]},
            }],
        })

    def test_graph_preflight_rejects_invalid_graphs_without_binding_then_allows_retry(self) -> None:
        valid = json.loads(self.f.graph.read_text())
        before = self.f.run_bytes()
        invalid_graphs = {
            "unknown dependency": {
                "version": 1,
                "steps": [{
                    "id": "A", "deps": ["missing"],
                    "contract": {"task": "Implement A", "ready": ["input"], "done": ["output"]},
                }],
            },
            "missing contract": {
                "version": 1,
                "steps": [{"id": "A", "deps": []}],
            },
            "empty definition of done": {
                "version": 1,
                "steps": [{
                    "id": "A", "deps": [],
                    "contract": {"task": "Implement A", "ready": ["input"], "done": []},
                }],
            },
        }
        for label, graph in invalid_graphs.items():
            with self.subTest(graph=label):
                public = self.validate_graph(self.f, graph)
                self.assertNotEqual(public.returncode, 0, public.stdout)
                self.assertEqual(self.f.run_bytes(), before)

                self.f.graph = self.f.write("graph.json", graph)
                refused = self.bind(self.f, ok=False)
                self.assertIn("validate-graph", refused.stderr)
                self.assertEqual(self.f.run_bytes(), before)
                self.assertFalse((self.f.run / "chains").exists())

        self.f.graph = self.f.write("graph.json", valid)
        public = self.validate_graph(self.f, valid)
        self.assertEqual(public.returncode, 0, public.stderr + public.stdout)
        preflight = json.loads(public.stdout)
        self.assertEqual(set(preflight), {"ok", "graph_sha256"})
        self.assertTrue(preflight["ok"])
        self.bind(self.f)
        self.assertEqual(preflight["graph_sha256"], self.f.child_state()["graph_sha256"])

    def test_fresh_launch_requires_current_learnings_before_native_dispatch(self) -> None:
        self.bind(self.f, mode="parallel", capacity=1)
        attempt = self.claim(self.f, "A")["A"]
        output = self.f.call("start", self.f.start_value("A", attempt))
        launch = next(action for action in output["navigation"]["actions"]
                      if action["action"] == "launch")
        instruction = launch["instruction"].lower()
        for phrase in ("current learnings", "unchanged", "fresh context", "parent record",
                       "durably outside the worker workspace", "markdown heading", "labeled bullets",
                       "selected ask agent launch contract", "host capabilities", "existing task authorization",
                       "approvals", "declines", "pending", "revoked", "scope", "conditions", "actual source",
                       "separate from advisory learnings", "authority contract"):
            self.assertIn(phrase, instruction)
        cold = self.f.call("packet", {"attempt": attempt})
        self.assertEqual(cold["packet"], output["packet"])
        self.assertFalse(any(action["action"] == "launch" for action in cold["navigation"]["actions"]))

    def test_parallel_and_serial_cold_packets_keep_the_same_consolidated_context(self) -> None:
        self.bind(self.f, mode="parallel", capacity=2)
        binding, context, manifest = self.binding_and_manifest(self.f)
        attempts = self.claim(self.f, "A", "B")
        packet_a = self.start_parallel(self.f, "A", attempts["A"], ["context_alpha.py"])
        packet_b = self.start_parallel(self.f, "B", attempts["B"], ["context_beta.py"])
        for packet in (packet_a, packet_b):
            self.assert_packet_context(self.f, packet, context, manifest)
            self.assert_worker_guidance(packet)
            cold = self.f.call("packet", {"attempt": packet["attempt"]})["packet"]
            self.assertEqual(cold, packet)
            self.assert_worker_guidance(cold)

        serial = self.new_fixture()
        self.bind(serial, mode="serial", capacity=1)
        _binding, serial_context, serial_manifest = self.binding_and_manifest(serial)
        attempt = self.claim(serial, "A")["A"]
        packet = self.start_serial(serial, "A", attempt, ["context_alpha.py"])
        self.assert_packet_context(serial, packet, serial_context, serial_manifest)
        self.assert_worker_guidance(packet)
        cold = serial.call("packet", {"attempt": attempt})["packet"]
        self.assertEqual(cold, packet)
        self.assert_worker_guidance(cold)

    def test_worker_guidance_uses_relocated_package_outside_worker_repository(self) -> None:
        selected = self.f.base / "selected ShipLoop package"
        shutil.copytree(SCRIPTS.parent, selected)
        with patch.object(fixture, "CLI", selected / "scripts" / "shiploop"):
            self.bind(self.f, mode="serial", capacity=1)
            attempt = self.claim(self.f, "A")["A"]
            packet = self.start_serial(self.f, "A", attempt, ["context_alpha.py"])
            self.assert_worker_guidance(packet, selected)
            self.assertNotIn(str(SCRIPTS.parent), json.dumps(packet["instructions"]))
            cold = self.f.call("packet", {"attempt": attempt})["packet"]
            self.assertEqual(cold, packet)
            self.assert_worker_guidance(cold, selected)

    def test_fresh_final_return_binding_is_refused_before_writes(self) -> None:
        for mode in ("parallel", "serial"):
            with self.subTest(mode=mode):
                test = self.new_fixture()
                before = test.run_bytes()
                head = test.git(test.target, "rev-parse", "HEAD")
                worktrees = test.git(test.primary, "worktree", "list", "--porcelain")
                refused = self.bind(test, mode=mode, capacity=1, lifecycle="final-return", ok=False)
                self.assertRegex(refused.stderr.lower(), r"managed|per-step|final-return")
                self.assertEqual(test.run_bytes(), before)
                self.assertEqual(test.git(test.target, "rev-parse", "HEAD"), head)
                self.assertEqual(test.git(test.primary, "worktree", "list", "--porcelain"), worktrees)
                self.assertFalse((test.run / "chains").exists())

    def test_consumer_fixture_stops_before_edits_when_guidance_is_unavailable(self) -> None:
        self.bind(self.f, mode="serial", capacity=1)
        attempt = self.claim(self.f, "A")["A"]
        packet = self.start_serial(self.f, "A", attempt, ["context_alpha.py"])
        self.check_managed_context(packet)
        self.assert_worker_guidance(packet)
        prefix = "Coding decision guide: "
        packet["instructions"] = [
            prefix + str(self.f.base / "unavailable" / "coding-guidance.md") + "#select-guidance"
            if text.startswith(prefix) else text for text in packet["instructions"]
        ]
        workspace = Path(packet["context"]["workspace"])
        assignment = {
            "step": "A", "run_id": packet["run_id"], "attempt": attempt,
            "base_commit": packet["context"]["base_commit"],
            "workspace": str(workspace), "packet": packet,
        }
        result = subprocess.run(
            [sys.executable, "-B", str(WORKER)], input=json.dumps(assignment) + "\n",
            text=True, capture_output=True, timeout=15,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unavailable worker guidance", result.stderr)
        self.assertFalse((workspace / "context_alpha.py").exists())
        self.assertEqual(self.f.git(workspace, "status", "--porcelain"), "")

    def test_parallel_context_workers_derive_code_then_join_and_cleanup(self) -> None:
        self.f.graph = self.f.write("context-graph.json", {
            "version": 1,
            "steps": [
                {"id": "A", "deps": [], "contract": {"task": "Implement the first bounded unit.",
                 "ready": ["Shared planning material is available"], "done": ["Commit verified output"]}},
                {"id": "B", "deps": [], "contract": {"task": "Implement the second bounded unit.",
                 "ready": ["Shared planning material is available"], "done": ["Commit verified output"]}},
                {"id": "C", "deps": ["A", "B"], "contract": {"task": "Join verified supplier output.",
                 "ready": ["A and B are accepted"], "done": ["Commit verified output"]}},
            ],
        })
        self.bind(self.f, mode="parallel", capacity=2)
        _binding, context, manifest = self.binding_and_manifest(self.f)
        attempts = self.claim(self.f, "A", "B")
        packet_a = self.start_parallel(self.f, "A", attempts["A"], ["context_alpha.py"])
        packet_b = self.start_parallel(self.f, "B", attempts["B"], ["context_beta.py"])
        self.assertNotIn("context_alpha.py", packet_a["task"])
        self.assertNotIn("context_beta.py", packet_b["task"])
        self.assert_packet_context(self.f, packet_a, context, manifest)
        self.assert_packet_context(self.f, packet_b, context, manifest)
        worker_a = self.launch_context_worker(self.f, "A")
        worker_b = self.launch_context_worker(self.f, "B")
        result_a = self.finish_context_worker(worker_a)
        result_b = self.finish_context_worker(worker_b)
        self.collect(self.f, "A", result_a)
        self.prepare_and_accept(self.f, "A")
        self.assertNotIn("C", self.f.call("next")["ready"])
        self.collect(self.f, "B", result_b)
        self.prepare_and_accept(self.f, "B")
        self.assertIn("C", self.f.call("next")["ready"])

        attempt_c = self.claim(self.f, "C")["C"]
        packet_c = self.start_parallel(self.f, "C", attempt_c, ["context_join.py"])
        self.assert_packet_context(self.f, packet_c, context, manifest)
        self.assert_supplier_findings_survive_cleanup(self.f, packet_c)
        result_c = self.finish_context_worker(self.launch_context_worker(self.f, "C"))
        self.collect(self.f, "C", result_c)
        self.prepare_and_accept(self.f, "C")
        self.verify_context_code(self.f.target, "C")
        final_head = self.f.git(self.f.target, "rev-parse", "HEAD")
        proof = self.f.write("context-final.json", {
            "passed": True, "commit": final_head,
            "checks": ["A/B fan-out and C join from planning material"],
        })
        finished = self.f.call("finish", {
            "commit": final_head, "confirmed_stopped": True,
            "verification": {"path": str(proof), "sha256": digest(proof)},
        })
        self.assertTrue(finished["complete"])
        self.assertEqual(self.f.git(self.f.primary, "rev-parse", "HEAD"), self.f.initial)
        for packet in (packet_a, packet_b, packet_c):
            self.assertFalse(Path(packet["context"]["workspace"]).exists())

    def test_serial_context_workers_use_artifacts_then_merge_and_cleanup(self) -> None:
        self.f.graph = self.f.write("serial-context-graph.json", {
            "version": 1,
            "steps": [
                {"id": "A", "deps": [], "contract": {"task": "Implement the first bounded unit.",
                 "ready": ["Shared planning material is available"], "done": ["Commit verified output"]}},
                {"id": "B", "deps": [], "contract": {"task": "Implement the second bounded unit.",
                 "ready": ["Shared planning material is available"], "done": ["Commit verified output"]}},
                {"id": "C", "deps": ["A", "B"], "contract": {"task": "Join verified supplier output.",
                 "ready": ["A and B are accepted"], "done": ["Commit verified output"]}},
            ],
        })
        self.bind(self.f, mode="serial", capacity=1)
        _binding, context, manifest = self.binding_and_manifest(self.f)
        packets = []
        for step, scope in (("A", ["context_alpha.py"]), ("B", ["context_beta.py"]),
                            ("C", ["context_join.py"])):
            attempt = self.claim(self.f, step)[step]
            packet = self.start_serial(self.f, step, attempt, scope)
            packets.append(packet)
            self.assert_packet_context(self.f, packet, context, manifest)
            self.assertEqual(packet["executor"]["kind"], "main-context")
            self.assertNotIn("native_handle", packet)
            if step == "C":
                self.assert_supplier_findings_survive_cleanup(self.f, packet)
            result = self.finish_context_worker(self.launch_context_worker(self.f, step))
            self.collect(self.f, step, result)
            self.prepare_and_accept(self.f, step)
            self.verify_context_code(self.f.target, step)

        self.assertTrue(self.f.call("next")["complete"])
        final_head = self.f.git(self.f.target, "rev-parse", "HEAD")
        proof = self.f.write("serial-context-final.json", {
            "passed": True,
            "commit": final_head,
            "checks": ["serial A/B/C code derived from planning artifacts"],
        })
        finished = self.f.call("finish", {
            "commit": final_head,
            "confirmed_stopped": True,
            "verification": {"path": str(proof), "sha256": digest(proof)},
        })
        self.assertTrue(finished["complete"])
        for packet in packets:
            self.assertFalse(Path(packet["context"]["workspace"]).exists())

    def test_changed_required_context_blocks_start_and_acceptance_but_preserves_recovery(self) -> None:
        self.bind(self.f, mode="parallel", capacity=1)
        attempts = self.claim(self.f, "A")
        initial_head = self.f.git(self.f.target, "rev-parse", "HEAD")
        original_contract = self.f.planning_contract.read_bytes()
        self.f.planning_contract.unlink()
        before_worktrees = self.f.git(self.f.target, "worktree", "list", "--porcelain")
        refused = self.f.call("start", self.f.start_value("A", attempts["A"]), ok=False)
        self.assertIn("planning context", refused.stderr)
        self.assertEqual(self.f.git(self.f.target, "worktree", "list", "--porcelain"), before_worktrees)
        self.assertEqual(self.f.child_record(attempts["A"])["status"], "claimed")
        view = self.f.call("next")
        self.assertIn("A", view["planning_blocked_steps"])
        self.assertFalse(view["planning_context_check"]["ok"])
        self.assertTrue(any(row["action"] == "inspect-planning-context"
                            for row in view["navigation"]["actions"]))

        self.f.planning_contract.write_bytes(original_contract)
        packet = self.start_parallel(self.f, "A", attempts["A"], ["context_alpha.py"])
        result = self.finish_context_worker(self.launch_context_worker(self.f, "A"))
        # Import is durable evidence capture, not a new execution or
        # integration gate. It must remain usable even when a required source
        # disappears after the worker has stopped.
        self.f.planning_contract.unlink()
        self.collect(self.f, "A", result, expect_prepare=False)
        prepare_refusal = self.f.call(
            "prepare", {"attempt": attempts["A"], "confirmed_stopped": True}, ok=False
        )
        self.assertIn("planning context", prepare_refusal.stderr)
        self.assertEqual(self.f.git(self.f.target, "rev-parse", "HEAD"), initial_head)
        self.f.planning_contract.write_bytes(original_contract)
        prepared = self.f.call("prepare", {"attempt": attempts["A"], "confirmed_stopped": True})
        binding, _context, _manifest = self.binding_and_manifest(self.f)
        receipt = fixture.chain._node(binding, "receipt", {"attempt": attempts["A"]})
        proof = self.f.write("context-stale-positive.json", {
            "passed": True, "integration": prepared["integration"], "checks": ["candidate prepared before source drift"],
        })
        positive = {
            "attempt": attempts["A"], "confirmed_stopped": True,
            "integration": prepared["integration"],
            "verification": {
                "receipt_sha256": receipt["sha256"], "passed": True,
                "reason": "Would accept the prepared candidate",
                "evidence": {"path": str(proof), "sha256": digest(proof)},
            },
        }
        self.f.planning_contract.unlink()
        refusal = self.f.call("done", positive, ok=False)
        self.assertIn("planning context", refusal.stderr)
        self.assertEqual(self.f.git(self.f.target, "rev-parse", "HEAD"), initial_head)
        self.assertTrue(Path(packet["context"]["workspace"]).exists())
        # Inspection, terminal negative settlement, and retry remain available
        # after a required material fault.  None can turn the stale positive
        # result into a merge.
        self.assertEqual(self.f.call("packet", {"attempt": attempts["A"]})["packet"], packet)
        negative = json.loads(json.dumps(positive))
        negative["verification"]["passed"] = False
        rejected = self.f.call("done", negative)
        self.assertEqual(rejected["outcome"], "rejected")
        retried = self.f.call("retry", {
            "attempt": attempts["A"], "confirmed_stopped": True,
            "reason": "Restore planning material before a new attempt",
        })
        self.assertEqual(retried["retry"]["status"], "retried")
        self.assertEqual(self.f.git(self.f.target, "rev-parse", "HEAD"), initial_head)

    def test_invalid_handoff_is_rejected_before_import_state_then_valid_retry_succeeds(self) -> None:
        self.bind(self.f, mode="parallel", capacity=1)
        attempt = self.claim(self.f, "A")["A"]
        self.start_parallel(self.f, "A", attempt, ["context_alpha.py"])
        result = self.finish_context_worker(self.launch_context_worker(self.f, "A"))
        handoff = Path(result["handoff"])
        valid = handoff.read_bytes()
        malformed = json.loads(valid)
        malformed["status"] = "succeeded"
        handoff.write_text(json.dumps(malformed) + "\n")
        rejected = self.f.call("import-handoff", {
            "attempt": attempt,
            "confirmed_stopped": True,
            "handoff": {"path": str(handoff), "sha256": digest(handoff)},
        }, ok=False)
        self.assertIn("status", rejected.stderr.lower())
        events = fixture.chain_ledger.read_events(
            self.f.run / "chains" / self.f.action / "events"
        )
        kinds = [row["event"]["kind"] for row in events]
        self.assertNotIn("handoff_import_intent", kinds)
        self.assertNotIn("handoff_archived", kinds)
        self.assertFalse((self.f.run / "chains" / self.f.action / "handoffs" / attempt).exists())

        handoff.write_bytes(valid)
        restored = dict(result, sha256=digest(handoff))
        imported = self.collect(self.f, "A", restored)
        self.assertEqual(imported["import"]["status"], "SUCCEEDED")
        self.assertFalse(handoff.exists())

    def test_legacy_failed_import_intent_recovers_only_without_partial_effects(self) -> None:
        def legacy_case(effect: str | None):
            test = self.new_fixture()
            self.bind(test, mode="parallel", capacity=1)
            attempt = self.claim(test, "A")["A"]
            self.start_parallel(test, "A", attempt, ["context_alpha.py"])
            result = self.finish_context_worker(self.launch_context_worker(test, "A"))
            handoff = Path(result["handoff"])
            valid = handoff.read_bytes()
            malformed = json.loads(valid)
            malformed["status"] = "succeeded"
            handoff.write_text(json.dumps(malformed) + "\n")
            bad_handoff = {"path": str(handoff), "sha256": digest(handoff)}

            binding, _context, _manifest = self.binding_and_manifest(test)
            chain_dir = test.run / "chains" / test.action
            rows = fixture.chain._events(chain_dir)
            allocation = fixture.chain._per_step_allocation(rows, attempt)
            packet = fixture.chain._per_step_internal_packet(rows, attempt)
            full = fixture.chain._child_full(binding)
            prior = {
                "attempt": attempt,
                "confirmed_stopped": True,
                "handoff": bad_handoff,
                "expected": {
                    "run_id": packet["run_id"],
                    "step": fixture.chain._step_for_attempt(full, attempt)["id"],
                    "attempt": attempt,
                    "base_commit": allocation["base_commit"],
                    "workspace": allocation["plan"]["path"],
                },
            }
            if effect == "revisited-digest":
                earlier = {**prior, "handoff": {"path": str(handoff), "sha256": result["sha256"]}}
                fixture.chain._append(
                    chain_dir, fixture.chain._event_id("handoff-import-intent", earlier),
                    "handoff_import_intent", earlier,
                )
            fixture.chain._append(
                chain_dir, fixture.chain._event_id("handoff-import-intent", prior),
                "handoff_import_intent", prior,
            )
            error = {**prior, "error": "synthetic legacy invalid-handoff failure"}
            if effect == "unmatched-error":
                error = {**error, "handoff": {"path": str(handoff), "sha256": "0" * 64}}
            fixture.chain._append(
                chain_dir, fixture.chain._event_id("handoff-import-error", error),
                "handoff-import_error", error,
            )

            archive_root = chain_dir / "handoffs" / attempt
            archive_root.mkdir(parents=True, exist_ok=True)
            if effect == "archive":
                (archive_root / "unexpected.txt").write_text("partial archive\n")
            elif effect == "report":
                artifact = Path(packet["outputs"]["artifact"])
                artifact.parent.mkdir(parents=True, exist_ok=True)
                artifact.write_text("partial parent report\n")

            handoff.write_bytes(valid)
            input_value = {
                "attempt": attempt,
                "confirmed_stopped": True,
                "handoff": {"path": str(handoff), "sha256": digest(handoff)},
            }
            return test, attempt, handoff, input_value

        for effect in (None, "revisited-digest"):
            with self.subTest(recovered=effect):
                recovered, attempt, handoff, input_value = legacy_case(effect)
                imported = recovered.call("import-handoff", input_value)
                self.assertEqual(imported["import"]["status"], "SUCCEEDED")
                self.assertFalse(handoff.exists())
                rows = fixture.chain._events(recovered.run / "chains" / recovered.action)
                intents = [row for row in rows if row["event"]["kind"] == "handoff_import_intent"]
                self.assertEqual(len(intents), 3 if effect else 2)
                self.assertEqual(intents[-1]["event"]["data"]["handoff"], input_value["handoff"])
                self.assertEqual(sum(row["event"]["kind"] == "handoff-import_error" for row in rows), 1)

        for effect in ("archive", "report", "unmatched-error"):
            with self.subTest(effect=effect):
                blocked, _attempt, _handoff, input_value = legacy_case(effect)
                before = blocked.run_bytes()
                refused = blocked.call("import-handoff", input_value, ok=False)
                self.assertIn("import", refused.stderr.lower())
                self.assertEqual(blocked.run_bytes(), before)

    def test_legacy_dispatcher_refusal_and_existing_v1_binding_is_readonly(self) -> None:
        context_only = self.new_fixture()
        context_helper = context_only.dispatcher / "scripts" / "dispatch.js"
        context_helper.write_text(context_helper.read_text().replace(
            "    graph_validation: 'execution-graph/v1',\n", ""
        ))
        before = context_only.run_bytes()
        refused = self.bind(context_only, ok=False)
        self.assertIn("does not support graph_validation", refused.stderr)
        self.assertEqual(context_only.run_bytes(), before)
        self.assertFalse((context_only.run / "chains").exists())

        old = self.new_fixture()
        old.select_dispatcher(fixture.LEGACY_FIXTURE)
        before = old.run_bytes()
        extra = (
            "--graph", str(old.graph), "--dispatcher-skill", str(old.dispatcher / "SKILL.md"),
            "--ask-agent-skill", str(old.ask / "SKILL.md"), "--worktree-parent", str(old.parent),
            "--mode", "parallel", "--lifecycle", "per-step",
        )
        refused = old.call("bind", ok=False, extra=extra)
        self.assertIn("cannot resolve dispatcher scripts/planning-context.js", refused.stderr)
        self.assertEqual(old.run_bytes(), before)
        self.assertFalse((old.run / "chains").exists())

        legacy = self.new_fixture()
        graph, graph_source = fixture.chain._freeze_graph(str(legacy.graph))
        dispatcher = fixture.chain._package(
            str(fixture.LEGACY_FIXTURE / "SKILL.md"), "dispatcher",
            ("SKILL.md", "scripts/dispatch.js", "scripts/state.js", "references/protocol.md"),
        )
        ask_agent = fixture.chain._package(
            str(legacy.ask / "SKILL.md"), "Ask-Agent", ("SKILL.md", "references/git-integration.md"),
        )
        chain_dir = legacy.run / "chains" / legacy.action
        chain_dir.mkdir(parents=True)
        dispatcher_run = chain_dir / "dispatcher"
        init = legacy.write("legacy-init.json", {"owner": "legacy-owner", "graph": graph})
        initialized = subprocess.run(
            [fixture.chain._node_path(), dispatcher["files"]["scripts/dispatch.js"]["path"],
             "init", str(dispatcher_run), str(init)],
            text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr + initialized.stdout)
        binding = {
            "schema": "shiploop-chain-binding/v1",
            "run_id": legacy.state["run_id"],
            "action_id": legacy.action,
            "root": str(legacy.run),
            "created_at": "2026-09-19T00:00:00Z",
            "owner": "legacy-owner",
            "capacity": 2,
            "graph": graph,
            "graph_source": graph_source,
            "dispatcher": dispatcher,
            "ask_agent": ask_agent,
            "node": fixture.chain._node_path(),
            "target": fixture.chain._git_identity(legacy.target),
            "worktree_parent": str(legacy.parent),
            "dispatcher_run": str(dispatcher_run),
        }
        raw = fixture.store.dumps(binding, "ShipLoop chain binding")
        state = fixture.store.read_record(legacy.run / "state.md")
        state["chain_bindings"] = dict(state.get("chain_bindings", {}))
        state["chain_bindings"][legacy.action] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        state["revision"] += 1
        fixture.nav.save(legacy.run, state, {
            str((chain_dir / "binding.md").relative_to(legacy.run)): raw,
        })
        before = legacy.run_bytes()
        head = legacy.git(legacy.target, "rev-parse", "HEAD")
        worktrees = legacy.git(legacy.primary, "worktree", "list", "--porcelain")
        history = legacy.call("history")
        pending = legacy.call("pending")
        self.assertIsInstance(history, dict)
        self.assertIsInstance(pending, dict)
        self.assertEqual(legacy.run_bytes(), before)
        self.assertEqual(legacy.git(legacy.target, "rev-parse", "HEAD"), head)
        self.assertEqual(legacy.git(legacy.primary, "worktree", "list", "--porcelain"), worktrees)


if __name__ == "__main__":
    unittest.main(verbosity=2)
