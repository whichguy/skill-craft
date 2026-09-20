#!/usr/bin/env python3
"""Hermetic public-CLI checks for the native ShipLoop chain pilot adapter.

The fixture creates disposable Git worktrees and invokes the public ShipLoop
chain commands.  It deliberately never launches a model or a host-native agent.
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
                pilot_dir: Path | None = None, hold_step: str | None = None,
                hold_timeout_seconds: int | None = None) -> dict:
        destination = self.pilot_dir if pilot_dir is None else pilot_dir
        args = [
            "prepare", "--pilot-dir", str(destination), "--source-root", str(ROOT),
            "--dispatcher-skill", str(dispatcher), "--ask-agent-skill", str(ASK_AGENT), "--capacity", "2",
        ]
        if hold_step is not None:
            args.extend(["--hold-step", hold_step])
        if hold_timeout_seconds is not None:
            args.extend(["--hold-timeout-seconds", str(hold_timeout_seconds)])
        return self.call(*args, ok=ok)

    def claim(self, *steps: str) -> dict[str, str]:
        claimed = self.call("claim", "--pilot-dir", str(self.pilot_dir), "--steps", *steps)
        self.assertEqual({item["step"] for item in claimed["claims"]}, set(steps))
        return {item["step"]: item["attempt"] for item in claimed["claims"]}

    def claim_a(self) -> str:
        return self.claim("A")["A"]

    def start(self, step: str, attempt: str) -> dict:
        return self.call("start", "--pilot-dir", str(self.pilot_dir), "--step", step, "--attempt", attempt)

    def start_a(self, attempt: str) -> dict:
        return self.start("A", attempt)

    def packet_a(self, attempt: str) -> dict:
        return self.call("packet", "--pilot-dir", str(self.pilot_dir), "--step", "A", "--attempt", attempt)

    def inline_packet(self, assignment: str) -> str:
        self.assertIn(PACKET_MARKER, assignment)
        after_marker = assignment.split(PACKET_MARKER, 1)[1]
        self.assertIn(PACKET_END, after_marker)
        return after_marker.split(PACKET_END, 1)[0] + "\n"

    def launch(self, step: str, attempt: str, *, handle_value: str | None = None,
               handle_path: Path | None = None, ok: bool = True) -> dict:
        handle = self.base / f"{step}-{attempt}-handle.json" if handle_path is None else handle_path
        value = f"native-{step}-{attempt}" if handle_value is None else handle_value
        handle.write_text(json.dumps({"handle": value}) + "\n", encoding="utf-8")
        return self.call("launched", "--pilot-dir", str(self.pilot_dir), "--step", step,
                         "--attempt", attempt, "--handle-file", str(handle), ok=ok)

    def git(self, workspace: Path, *args: str) -> str:
        result = subprocess.run(["git", "-C", str(workspace), *args], text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return result.stdout.strip()

    def accept_a(self, started: dict, attempt: str) -> dict:
        workspace = Path(started["workspace"])
        workspace_record = json.loads(Path(started["caller_workspace_record"]).read_text(encoding="utf-8"))
        packet = json.loads(Path(started["packet"]).read_text(encoding="utf-8"))
        (workspace / "toy" / "add.py").write_text(
            "def add(left: int, right: int) -> int:\n    return left + right\n", encoding="utf-8",
        )
        self.git(workspace, "add", "toy/add.py")
        self.git(workspace, "commit", "-m", "fixture native A contribution")
        commit = self.git(workspace, "rev-parse", "HEAD")
        handoff = workspace / ".shiploop-handoff" / attempt / "handoff.json"
        handoff.parent.mkdir(parents=True)
        result_path = handoff.parent / "result.json"
        worker_result = {
            "schema": "shiploop-native-pilot-worker-result/v2", "step": "A", "attempt": attempt,
            "workspace": str(workspace), "base_commit": workspace_record["base_commit"], "commit": commit,
            "cwd": str(workspace), "git_root": str(workspace), "checks": ["add(-4, 1) == -3"],
            "summary": "Fixture-native A handoff for C launch barrier coverage.",
        }
        result_path.write_text(json.dumps(worker_result, sort_keys=True) + "\n", encoding="utf-8")
        manifest = {
            "schema": "shiploop-chain-handoff/v1", "run_id": packet["run_id"], "step": "A", "attempt": attempt,
            "base_commit": workspace_record["base_commit"], "status": "SUCCEEDED", "commit": commit,
            "summary": "Fixture-native A contribution.",
            "files": [{"path": "result.json", "sha256": hashlib.sha256(result_path.read_bytes()).hexdigest()}],
        }
        handoff.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
        self.call("import-handoff", "--pilot-dir", str(self.pilot_dir), "--step", "A", "--attempt", attempt,
                  "--handoff-manifest", str(handoff), "--confirmed-stopped")
        self.call("prepare-integration", "--pilot-dir", str(self.pilot_dir), "--step", "A", "--attempt", attempt,
                  "--confirmed-stopped")
        return self.call("done", "--pilot-dir", str(self.pilot_dir), "--step", "A", "--attempt", attempt,
                         "--confirmed-stopped")

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
        self.assertNotIn("wait-hold", assignment)
        self.assertFalse((self.pilot_dir / "holds").exists())
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

    def test_opt_in_b_hold_is_disclosed_and_only_b_receives_the_wait_assignment(self) -> None:
        prepared = self.prepare(hold_step="B", hold_timeout_seconds=7)
        hold = prepared["test_only_hold"]
        self.assertEqual(hold["held_step"], "B")
        self.assertEqual(hold["release_step"], "C")
        self.assertEqual(hold["timeout_seconds"], 7)
        self.assertTrue(hold["test_only"])
        self.assertIn("not ShipLoop runtime", hold["purpose"])
        context_path = self.pilot_dir / "context.json"
        context = json.loads(context_path.read_text(encoding="utf-8"))
        self.assertEqual(context["test_only_hold"], hold)
        self.assertEqual(context_path.stat().st_mode & 0o222, 0)

        attempts = self.claim("A", "B")
        a = self.start("A", attempts["A"])
        b = self.start("B", attempts["B"])
        self.assertNotIn("wait-hold", a["inline_native_assignment"])
        self.assertIn("wait-hold", b["inline_native_assignment"])
        self.assertIn('"--step", "B"', b["inline_native_assignment"])
        self.assertIn(f'"--attempt", "{attempts["B"]}"', b["inline_native_assignment"])
        self.assertLess(
            b["inline_native_assignment"].index("Before writing handoff files"),
            b["inline_native_assignment"].index("wait-hold"),
        )
        self.assertLess(
            b["inline_native_assignment"].index("wait-hold"),
            b["inline_native_assignment"].index("Then create"),
        )
        armed = Path(b["test_only_hold"]["armed"])
        self.assertEqual(armed.stat().st_mode & 0o222, 0)

    def test_b_hold_times_out_without_self_release_or_pilot_mutation(self) -> None:
        self.prepare(hold_step="B", hold_timeout_seconds=1)
        attempt = self.claim("B")["B"]
        started = self.start("B", attempt)
        armed = Path(started["test_only_hold"]["armed"])
        release = Path(started["test_only_hold"]["release"])
        events = (self.pilot_dir / "events.jsonl").read_bytes()
        armed_bytes = armed.read_bytes()

        refused = self.call("wait-hold", "--pilot-dir", str(self.pilot_dir), "--step", "B", "--attempt", attempt,
                            ok=False)

        self.assertIn("timed out", refused["stderr"])
        self.assertFalse(release.exists())
        self.assertEqual(armed.read_bytes(), armed_bytes)
        self.assertEqual((self.pilot_dir / "events.jsonl").read_bytes(), events)

    def test_c_launch_releases_held_b_after_bridge_receipt_and_replays_safely(self) -> None:
        self.prepare(hold_step="B", hold_timeout_seconds=20)
        attempts = self.claim("A", "B")
        started_a = self.start("A", attempts["A"])
        started_b = self.start("B", attempts["B"])
        release = Path(started_b["test_only_hold"]["release"])
        self.assertFalse(release.exists())

        self.launch("A", attempts["A"])
        b_launch = self.launch("B", attempts["B"])
        self.assertNotIn("test_only_hold", b_launch)
        self.assertFalse(release.exists(), "A/B launch receipts must not release B's hold")
        waiter = subprocess.Popen(
            [sys.executable, "-B", str(PILOT), "wait-hold", "--pilot-dir", str(self.pilot_dir),
             "--step", "B", "--attempt", attempts["B"]],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.addCleanup(lambda: waiter.terminate() if waiter.poll() is None else None)
        accepted_a = self.accept_a(started_a, attempts["A"])
        self.assertIn("C", accepted_a["ready"])
        self.assertIsNone(waiter.poll(), "B wait-hold returned before C was launched")

        c_attempt = self.claim("C")["C"]
        started_c = self.start("C", c_attempt)
        self.assertNotIn("wait-hold", started_c["inline_native_assignment"])
        c_launch = self.launch("C", c_attempt)
        self.assertEqual(c_launch["test_only_hold"]["held_attempt"], attempts["B"])
        self.assertTrue(release.is_file())
        released = json.loads(release.read_text(encoding="utf-8"))
        self.assertEqual(released["release_step"], "C")
        self.assertEqual(released["held_attempt"], attempts["B"])

        stdout, stderr = waiter.communicate(timeout=10)
        self.assertEqual(waiter.returncode, 0, stderr + stdout)
        waited = json.loads(stdout)
        self.assertEqual(waited["released_by"], "C")
        handle_record = Path(c_launch["handle_record"])
        retained_handle = json.loads(handle_record.read_text(encoding="utf-8"))
        retained_handle["recorded_at"] = "2000-01-01T00:00:00Z"
        handle_record.write_text(
            json.dumps(retained_handle, sort_keys=True, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        retained_bytes = handle_record.read_bytes()
        replay = self.launch("C", c_attempt)
        self.assertEqual(replay["test_only_hold"]["release"], str(release))
        self.assertEqual(handle_record.read_bytes(), retained_bytes)
        source_conflict = self.launch("C", c_attempt, handle_path=self.base / "other-c-handle.json", ok=False)
        self.assertIn("existing native handle record differs", source_conflict["stderr"])
        handle_conflict = self.launch("C", c_attempt, handle_value="other-native-c-handle", ok=False)
        self.assertIn("SHIPLOOP_NATIVE_PILOT_ERROR", handle_conflict["stderr"])
        events = [json.loads(line) for line in (self.pilot_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        c_events = [index for index, event in enumerate(events)
                    if event["kind"] == "native-launch-recorded" and event["step"] == "C"]
        self.assertEqual(len(c_events), 1)
        release_events = [index for index, event in enumerate(events) if event["kind"] == "test-only-hold-released"]
        self.assertEqual(len(release_events), 1)
        self.assertLess(c_events[0], release_events[0])


if __name__ == "__main__":
    unittest.main()
