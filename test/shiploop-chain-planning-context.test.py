#!/usr/bin/env python3
"""Focused composition coverage for ShipLoop's immutable planning handoff.

These checks use the real public bridge, pinned Plan Dispatcher package, real
Git worktrees, and a deterministic worker.  They do not claim native/model
qualification.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
ASK = ROOT / "test" / "fixtures" / "ask-agent-v04"
WORKER = ROOT / "test" / "fixtures" / "chain-planning-context-worker.py"

_fixture_spec = importlib.util.spec_from_file_location(
    "planning_context_chain_fixture", ROOT / "test" / "shiploop-chain.test.py"
)
fixture = importlib.util.module_from_spec(_fixture_spec)
assert _fixture_spec.loader is not None
_fixture_spec.loader.exec_module(fixture)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PlanningContextChainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.processes: list[subprocess.Popen[str]] = []
        self.addCleanup(self.stop_processes)
        self.f = self.new_fixture()

    def new_fixture(self):
        test = fixture.ChainIntegrationTests(methodName="runTest")
        test.setUp()
        self.addCleanup(test.doCleanups)
        test.select_dispatcher(fixture.CONTEXT_FIXTURE)
        test.assert_fixture(ASK)
        shutil.rmtree(test.ask)
        shutil.copytree(ASK, test.ask)
        return test

    def stop_processes(self) -> None:
        for process in self.processes:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None:
                    stream.close()

    def bind(self, test, *, mode: str = "parallel", capacity: int | None = None, ok: bool = True):
        extra = [
            "--graph", str(test.graph),
            "--dispatcher-skill", str(test.dispatcher / "SKILL.md"),
            "--ask-agent-skill", str(test.ask / "SKILL.md"),
            "--worktree-parent", str(test.parent),
            "--mode", mode,
            "--lifecycle", "per-step",
        ]
        if capacity is not None:
            extra += ["--capacity", str(capacity)]
        return test.call("bind", ok=ok, extra=tuple(extra))

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
        # Context is passed as immutable references, rather than copying the
        # large planning body into each worker packet.
        self.assertNotIn("Use sibling worker worktrees", json.dumps(packet))

    def claim(self, test, *steps: str) -> dict[str, str]:
        response = test.call("claim", {"steps": list(steps)})
        return {row["step"]: row["attempt"] for row in response["claims"]}

    def start_parallel(self, test, step: str, attempt: str, write_scope: list[str]):
        value = test.start_value(step, attempt, base=test.git(test.target, "rev-parse", "HEAD"))
        value["write_scope"] = write_scope
        requested = test.call("start", value)
        self.assertEqual(requested["action"], "prepare-workspace")
        workspace = test.parent / ("ask-agent-" + attempt)
        test.git(test.target, "worktree", "add", "-q", "-b", "ask-agent/" + attempt,
                 str(workspace), value["base_commit"])
        value["workspace"] = str(workspace)
        output = test.call("start", value)
        self.assertEqual(output["action"], "launch")
        packet = output["packet"]
        test.packets[step] = packet
        test.call("launched", {"attempt": attempt, "handle": {
            "host": "planning-context-fixture", "id": step,
        }})
        return packet

    def start_serial(self, test, step: str, attempt: str, write_scope: list[str]):
        value = test.start_value(step, attempt, base=test.git(test.target, "rev-parse", "HEAD"))
        value["write_scope"] = write_scope
        output = test.call("start", value)
        self.assertEqual(output["action"], "execute")
        test.packets[step] = output["packet"]
        return output["packet"]

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
        self.processes.append(process)
        assert process.stdin is not None
        process.stdin.write(json.dumps(assignment) + "\n")
        process.stdin.flush()
        ready = self.read_json_line(process)
        self.assertEqual(ready["phase"], "code_ready")
        self.assertEqual(ready["cwd"], assignment["workspace"])
        self.assertEqual(ready["planning_brief"], packet["planning_brief"]["path"])
        return process

    def finish_context_worker(self, process: subprocess.Popen[str]) -> dict:
        assert process.stdin is not None and process.stderr is not None
        process.stdin.write("release\n")
        process.stdin.flush()
        result = self.read_json_line(process)
        self.assertEqual(process.wait(timeout=15), 0, process.stderr.read())
        self.assertEqual(result["phase"], "completed")
        return result

    def collect(self, test, step: str, result: dict):
        return test.call("import-handoff", {
            "attempt": test.packets[step]["attempt"],
            "confirmed_stopped": True,
            "handoff": {"path": result["handoff"], "sha256": result["sha256"]},
        })

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
        prepared = test.call("prepare", {"attempt": attempt, "confirmed_stopped": True})
        integration = prepared["integration"]
        self.verify_context_code(Path(test.packets[step]["context"]["workspace"]), step)
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
        self.assertFalse(Path(test.packets[step]["context"]["workspace"]).exists())
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
        self.assertEqual(binding["schema"], "shiploop-chain-binding/v4")
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

    def test_parallel_and_serial_cold_packets_keep_the_same_consolidated_context(self) -> None:
        self.bind(self.f, mode="parallel", capacity=2)
        binding, context, manifest = self.binding_and_manifest(self.f)
        attempts = self.claim(self.f, "A", "B")
        packet_a = self.start_parallel(self.f, "A", attempts["A"], ["context_alpha.py"])
        packet_b = self.start_parallel(self.f, "B", attempts["B"], ["context_beta.py"])
        for packet in (packet_a, packet_b):
            self.assert_packet_context(self.f, packet, context, manifest)
            cold = self.f.call("packet", {"attempt": packet["attempt"]})["packet"]
            self.assertEqual(cold, packet)

        serial = self.new_fixture()
        self.bind(serial, mode="serial", capacity=1)
        _binding, serial_context, serial_manifest = self.binding_and_manifest(serial)
        attempt = self.claim(serial, "A")["A"]
        packet = self.start_serial(serial, "A", attempt, ["context_alpha.py"])
        self.assert_packet_context(serial, packet, serial_context, serial_manifest)
        cold = serial.call("packet", {"attempt": attempt})["packet"]
        self.assertEqual(cold, packet)

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
        self.collect(self.f, "A", result)
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

    def test_old_helper_refusal_and_existing_v1_binding_recovery(self) -> None:
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
        self.assertIn("does not support planning_context", refused.stderr)
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
        recovered = legacy.call("recover")
        self.assertNotIn("planning_context", recovered)
        self.assertEqual(recovered["ready"], ["A", "B"])
        self.assertEqual(recovered["shiploop_chain"]["lifecycle"], "final-return")


if __name__ == "__main__":
    unittest.main(verbosity=2)
