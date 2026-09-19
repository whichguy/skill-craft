#!/usr/bin/env python3
"""Hermetic public-CLI checks for the native ShipLoop chain pilot adapter.

The fixture creates disposable Git worktrees and invokes the public ShipLoop
chain commands.  It deliberately never launches a model or a host-native agent.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
PILOT = ROOT / "test" / "experiments" / "shiploop_chain" / "native_pilot.py"
ASK_AGENT = ROOT / "test" / "fixtures" / "ask-agent-v04" / "SKILL.md"
DISPATCHER_V2 = ROOT / "test" / "fixtures" / "plan-dispatcher-v2" / "SKILL.md"
DISPATCHER_V3 = ROOT / "test" / "fixtures" / "plan-dispatcher-v3" / "SKILL.md"
PACKET_MARKER = "Complete authoritative worker packet (verbatim JSON):\n```json\n"
PACKET_END = "\n```\n\nWork only in the exclusively fixture-prepared caller workspace"
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
import shiploop_navigator as navigator  # noqa: E402
import shiploop_store as store  # noqa: E402

class NativePilotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-native-pilot-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.pilot_dir = self.base / "pilot"

    def call(self, *args: str, ok: bool = True) -> dict:
        completed = subprocess.run(
            [sys.executable, "-B", str(PILOT), *args], text=True, capture_output=True, timeout=45,
        )
        if not ok:
            self.assertNotEqual(completed.returncode, 0, completed.stdout)
            return {"stdout": completed.stdout, "stderr": completed.stderr}
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        value = json.loads(completed.stdout)
        self.assertIsInstance(value, dict)
        return value

    def prepare(self, dispatcher: Path = DISPATCHER_V3, *, ok: bool = True,
                pilot_dir: Path | None = None) -> dict:
        destination = self.pilot_dir if pilot_dir is None else pilot_dir
        return self.call(
            "prepare", "--pilot-dir", str(destination), "--source-root", str(ROOT),
            "--dispatcher-skill", str(dispatcher), "--ask-agent-skill", str(ASK_AGENT), "--capacity", "2", ok=ok,
        )

    def claim_a(self) -> str:
        claimed = self.call("claim", "--pilot-dir", str(self.pilot_dir), "--steps", "A")
        self.assertEqual(len(claimed["claims"]), 1)
        claim = claimed["claims"][0]
        self.assertEqual(claim["step"], "A")
        return claim["attempt"]

    def start_a(self, attempt: str) -> dict:
        return self.call("start", "--pilot-dir", str(self.pilot_dir), "--step", "A", "--attempt", attempt)

    def packet_a(self, attempt: str) -> dict:
        return self.call("packet", "--pilot-dir", str(self.pilot_dir), "--step", "A", "--attempt", attempt)

    def inline_packet(self, assignment: str) -> str:
        self.assertIn(PACKET_MARKER, assignment)
        after_marker = assignment.split(PACKET_MARKER, 1)[1]
        self.assertIn(PACKET_END, after_marker)
        return after_marker.split(PACKET_END, 1)[0] + "\n"

    def test_prepare_v3_transports_the_complete_packet_and_guidance_inline(self) -> None:
        prepared = self.prepare()
        preflight = prepared["dispatcher_preflight"]
        self.assertEqual(
            preflight["capabilities"]["planning_context"],
            "shiploop-planning-artifacts/v1",
        )
        self.assertEqual(
            preflight["capabilities"]["graph_validation"],
            "execution-graph/v1",
        )
        self.assertEqual(Path(preflight["helper"]), DISPATCHER_V3.parent / "scripts" / "dispatch.js")
        context = json.loads((self.pilot_dir / "context.json").read_text())
        self.assertEqual(context["dispatcher_preflight"], preflight)
        self.assertTrue((self.pilot_dir / "run" / "chains" / prepared["action"] / "binding.md").is_file())
        synthetic = json.loads((self.pilot_dir / "evidence" / "synthetic-prerequisites.json").read_text())
        self.assertTrue(synthetic["synthetic"])
        self.assertTrue(synthetic["actions"])
        state_path = self.pilot_dir / "run" / "state.md"
        self.assertEqual(synthetic["state"], str(state_path))
        state = store.read_record(state_path)
        self.assertEqual(state["navigator_protocol_version"], 3)
        self.assertEqual(navigator.current_stage(state), "implement")
        history = {entry["action"] for entry in state["history"]}
        for entry in synthetic["actions"]:
            self.assertIn(entry["action"], history)
            self.assertTrue((self.pilot_dir / "run" / "results" / (entry["action"] + ".md")).is_file())

        attempt = self.claim_a()
        started = self.start_a(attempt)
        self.assertEqual(started["action"], "launch")
        assignment = started["inline_native_assignment"]
        packet = json.loads(Path(started["packet"]).read_text())

        self.assertEqual(self.inline_packet(assignment), json.dumps(
            packet, sort_keys=True, ensure_ascii=False, indent=2,
        ) + "\n")
        self.assertIn("sole execution assignment", assignment)
        self.assertIn("only oracle and handoff mechanics", assignment)
        self.assertNotIn("Implement: ", assignment)
        self.assertIn("planning_context", packet)
        self.assertTrue(packet["reference_material"])
        for instruction in packet["instructions"]:
            self.assertIn(instruction, assignment)

        original_packet = Path(started["packet"]).read_bytes()
        recovered = self.packet_a(attempt)
        self.assertNotIn("inline_native_assignment", recovered)
        self.assertIn("never authorizes a fresh native launch", recovered["next"])
        self.assertEqual(Path(recovered["packet"]).read_bytes(), original_packet)

    def test_v2_is_rejected_by_preflight_before_a_pilot_directory_exists(self) -> None:
        refused = self.prepare(DISPATCHER_V2, ok=False)
        self.assertIn("does not support planning_context", refused["stderr"])
        self.assertIn("no pilot was created", refused["stderr"])
        self.assertFalse(self.pilot_dir.exists())

    def test_context_only_dispatcher_is_rejected_before_a_pilot_directory_exists(self) -> None:
        context_only = self.base / "context-only-dispatcher"
        shutil.copytree(DISPATCHER_V3.parent, context_only)
        helper = context_only / "scripts" / "dispatch.js"
        source = helper.read_text(encoding="utf-8")
        graph_capability = "    graph_validation: 'execution-graph/v1',\n"
        self.assertIn(graph_capability, source)
        helper.write_text(source.replace(graph_capability, "", 1), encoding="utf-8")

        context_only_pilot = self.base / "context-only-pilot"
        refused = self.prepare(
            context_only / "SKILL.md", ok=False, pilot_dir=context_only_pilot,
        )
        self.assertIn("does not support graph_validation", refused["stderr"])
        self.assertIn("no pilot was created", refused["stderr"])
        self.assertFalse(context_only_pilot.exists())

    def test_immediate_start_replay_is_reconcile_not_a_second_native_launch(self) -> None:
        self.prepare()
        attempt = self.claim_a()
        first = self.start_a(attempt)
        self.assertEqual(first["action"], "launch")
        self.assertIn("inline_native_assignment", first)

        original_packet = Path(first["packet"]).read_bytes()
        replay = self.start_a(attempt)
        self.assertEqual(replay["action"], "reconcile")
        self.assertNotIn("inline_native_assignment", replay)
        self.assertIn("does not authorize a fresh native launch", replay["next"])
        self.assertEqual(Path(replay["packet"]).read_bytes(), original_packet)


if __name__ == "__main__":
    unittest.main()
