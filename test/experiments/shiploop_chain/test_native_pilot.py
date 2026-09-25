#!/usr/bin/env python3
"""Hermetic public-CLI checks for the managed native ShipLoop chain pilot.

The fixture invokes the public ShipLoop chain commands against the current
Ask-Agent helper package. It deliberately never launches a model or a
host-native agent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import venv

import native_pilot as pilot


ROOT = Path(__file__).resolve().parents[3]
PILOT = ROOT / "test" / "experiments" / "shiploop_chain" / "native_pilot.py"
ASK_AGENT = ROOT / "skills" / "ask-agent" / "SKILL.md"
DISPATCHER_V3 = ROOT / "test" / "fixtures" / "plan-dispatcher-v3" / "SKILL.md"
DEFAULT_DISPATCHER = DISPATCHER_V3


def skill_card_version(card: Path) -> str:
    for line in card.read_text(encoding="utf-8").splitlines():
        if line.startswith("version: "):
            return line.removeprefix("version: ").strip()
    raise AssertionError(f"{card} has no version front-matter")


ASK_AGENT_VERSION = skill_card_version(ASK_AGENT)
PACKET_MARKER = "Complete authoritative worker packet (verbatim JSON):\n```json\n"
PACKET_END = "\n```\n\nWork only in the selected Ask-Agent helper-managed workspace"
WORKER_SOURCES = {
    "A": "def add(left: int, right: int) -> int:\n    return left + right\n",
    "B": "def normalize(text: str) -> str:\n    return ' '.join(text.lower().split())\n",
    "C": "def aggregate(values: list[int]) -> int:\n    return sum(values)\n",
    "J": "def composed_output(values: list[int]) -> str:\n    return f'result {sum(values)}'\n",
}
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
import shiploop_navigator as navigator  # noqa: E402
import shiploop_store as store  # noqa: E402


def default_dispatcher() -> Path:
    """Return the V3 fixture unless this test module was explicitly invoked with a card."""
    return DEFAULT_DISPATCHER


def dispatcher_from_cli(argv: list[str]) -> tuple[Path, list[str]]:
    """Consume only the qualification selector before handing remaining flags to unittest."""
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--dispatcher-skill")
    args, remaining = parser.parse_known_args(argv)
    if args.dispatcher_skill is None:
        return DISPATCHER_V3, remaining
    selected = Path(args.dispatcher_skill)
    if not selected.is_absolute():
        raise ValueError("--dispatcher-skill must be an absolute path")
    if selected.name != "SKILL.md" or selected.is_symlink() or not selected.is_file():
        raise ValueError("--dispatcher-skill must name an existing regular SKILL.md")
    return selected.resolve(), remaining


class NativePilotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-native-pilot-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.pilot_dir = self.base / "pilot"
        self.python_executable = sys.executable

    def call(self, *args: str, ok: bool = True) -> dict:
        completed = subprocess.run(
            [self.python_executable, "-B", str(PILOT), *args], text=True, capture_output=True, timeout=45,
        )
        if not ok:
            self.assertNotEqual(completed.returncode, 0, completed.stdout)
            return {"stdout": completed.stdout, "stderr": completed.stderr}
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        value = json.loads(completed.stdout)
        self.assertIsInstance(value, dict)
        return value

    def prepare(self, dispatcher: Path | None = None, ask_agent: Path = ASK_AGENT, *, ok: bool = True,
                pilot_dir: Path | None = None, hold_step: str | None = None,
                hold_timeout_seconds: int | None = None) -> dict:
        destination = self.pilot_dir if pilot_dir is None else pilot_dir
        selected_dispatcher = default_dispatcher() if dispatcher is None else dispatcher
        args = [
            "prepare", "--pilot-dir", str(destination), "--source-root", str(ROOT),
            "--dispatcher-skill", str(selected_dispatcher), "--ask-agent-skill", str(ask_agent), "--capacity", "2",
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
        return self.complete_started_step("A", started, attempt)

    def complete_started_step(self, step: str, started: dict, attempt: str) -> dict:
        workspace = Path(started["workspace"])
        workspace_record = json.loads(Path(started["ask_agent_workspace_record"]).read_text(encoding="utf-8"))
        packet = json.loads(Path(started["packet"]).read_text(encoding="utf-8"))
        path = workspace / "toy" / {"A": "add.py", "B": "format.py", "C": "aggregate.py", "J": "composed.py"}[step]
        path.write_text(WORKER_SOURCES[step], encoding="utf-8")
        self.git(workspace, "add", str(path.relative_to(workspace)))
        self.git(workspace, "commit", "-m", f"fixture native {step} contribution")
        commit = self.git(workspace, "rev-parse", "HEAD")
        handoff = workspace / ".shiploop-handoff" / attempt / "handoff.json"
        handoff.parent.mkdir(parents=True)
        result_path = handoff.parent / "result.json"
        worker_result = {
            "schema": "shiploop-native-pilot-worker-result/v3", "step": step, "attempt": attempt,
            "workspace": str(workspace), "base_commit": workspace_record["base_commit"], "commit": commit,
            "cwd": str(workspace), "git_root": str(workspace), "checks": [f"fixture {step} code behavior"],
            "summary": f"Fixture-native {step} handoff for managed cleanup coverage.",
        }
        result_path.write_text(json.dumps(worker_result, sort_keys=True) + "\n", encoding="utf-8")
        manifest = {
            "schema": "shiploop-chain-handoff/v1", "run_id": packet["run_id"], "step": step, "attempt": attempt,
            "base_commit": workspace_record["base_commit"], "status": "SUCCEEDED", "commit": commit,
            "summary": f"Fixture-native {step} contribution.",
            "files": [{"path": "result.json", "sha256": hashlib.sha256(result_path.read_bytes()).hexdigest()}],
        }
        handoff.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
        self.call("import-handoff", "--pilot-dir", str(self.pilot_dir), "--step", step, "--attempt", attempt,
                  "--handoff-manifest", str(handoff), "--confirmed-stopped")
        self.call("prepare-integration", "--pilot-dir", str(self.pilot_dir), "--step", step, "--attempt", attempt,
                  "--confirmed-stopped")
        return self.call("done", "--pilot-dir", str(self.pilot_dir), "--step", step, "--attempt", attempt,
                         "--confirmed-stopped")

    def test_managed_start_accepts_interpreter_alias_and_rejects_other_commands(self) -> None:
        environment = self.base / "python environment"
        venv.EnvBuilder(with_pip=False, symlinks=True).create(environment)
        self.python_executable = str(environment / "bin" / "python")
        self.prepare()
        context = json.loads((self.pilot_dir / "context.json").read_text())
        self.assertNotEqual(self.python_executable, context["selected"]["python"])
        self.assertEqual(Path(self.python_executable).resolve(), Path(context["selected"]["python"]))
        attempt = self.claim_a()
        started = self.start_a(attempt)
        packet = json.loads(Path(started["packet"]).read_text())
        command = packet["ask_agent_workspace"]["check_context"]["argv"]
        self.assertNotEqual(command[0], self.python_executable)
        self.assertEqual(Path(command[0]).resolve(), Path(context["selected"]["python"]))

        # The complete real helper packet must still reject a different executable
        # or altered command arguments after accepting an alias of the frozen one.
        other = self.base / "different-python"
        other.write_text("different executable fixture\n")
        for replacement in ([str(other), *command[1:]], [*command[:-1], "wrong-receipt"]):
            with self.subTest(argv=replacement):
                changed = json.loads(json.dumps(packet))
                changed["ask_agent_workspace"]["check_context"]["argv"] = replacement
                with self.assertRaisesRegex(pilot.PilotError, "helper context-check command"):
                    pilot.managed_workspace_from_packet(
                        self.pilot_dir, context, "A", attempt, changed,
                        packet["context"]["base_commit"],
                    )

    def test_prepare_freezes_the_selected_dispatcher_and_managed_helper_packet(self) -> None:
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
        selected_dispatcher = default_dispatcher().resolve()
        self.assertEqual(Path(preflight["helper"]), selected_dispatcher.parent / "scripts" / "dispatch.js")
        ask_preflight = prepared["ask_agent_preflight"]
        self.assertEqual(ask_preflight["capabilities"]["schema"], "shiploop-chain-ask-agent-managed-worktree/v1")
        self.assertEqual(ask_preflight["capabilities"]["version"], ASK_AGENT_VERSION)
        self.assertTrue({
            "helper-managed-worktree", "prepared-inspection", "returned-commit-delivery",
            "fingerprint-bound-close",
        }.issubset(set(ask_preflight["capabilities"]["capabilities"])))
        self.assertEqual(Path(ask_preflight["helper"]), ASK_AGENT.parent / "scripts" / "ask_agent_workspace.py")
        self.assertEqual(ask_preflight["identity"]["status"], "verified")
        self.assertEqual(ask_preflight["identity"]["version"], ASK_AGENT_VERSION)
        context = json.loads((self.pilot_dir / "context.json").read_text())
        self.assertEqual(context["schema"], "shiploop-native-chain-pilot/v3")
        self.assertEqual(Path(context["selected"]["dispatcher_skill"]), selected_dispatcher)
        self.assertEqual(context["dispatcher_preflight"], preflight)
        self.assertEqual(context["ask_agent_preflight"], ask_preflight)
        self.assertTrue((self.pilot_dir / "run" / "chains" / prepared["action"] / "binding.md").is_file())
        synthetic = json.loads((self.pilot_dir / "evidence" / "synthetic-prerequisites.json").read_text())
        self.assertTrue(synthetic["synthetic"])
        self.assertTrue(synthetic["actions"])
        state_path = self.pilot_dir / "run" / "state.md"
        self.assertEqual(synthetic["state"], str(state_path))
        state = store.read_record(state_path)
        self.assertEqual(state["navigator_protocol_version"], navigator.PROTOCOL_VERSION)
        self.assertEqual(navigator.current_stage(state), "implement")
        history = {entry["action"] for entry in state["history"]}
        for entry in synthetic["actions"]:
            self.assertIn(entry["action"], history)
            self.assertTrue((self.pilot_dir / "run" / "results" / (entry["action"] + ".md")).is_file())

        attempt = self.claim_a()
        started = self.start_a(attempt)
        self.assertEqual(started["action"], "launch")
        assignment = started["inline_native_assignment"]
        self.assertIn("## Current learnings\n\n- Verified facts:", assignment)
        self.assertIn("\n- Unresolved:", assignment)
        self.assertIn("Planning prerequisites are synthetic fixture inputs", assignment)
        self.assertIn("Current learnings", started["next"])
        self.assertIn("Extend its formatted", started["next"])
        self.assertIn("keep the embedded worker packet unchanged", started["next"])
        self.assertIn("existing parent record", started["next"])
        self.assertIn("durably outside the worker workspace", started["next"])
        for phrase in ("selected Ask Agent launch contract", "host capabilities", "existing task authorization",
                       "approvals", "declines", "pending", "revoked", "scope", "conditions", "actual source",
                       "separate from advisory learnings", "authority contract"):
            self.assertIn(phrase, started["next"])
        packet = json.loads(Path(started["packet"]).read_text())
        workspace_record = json.loads(Path(started["ask_agent_workspace_record"]).read_text())

        self.assertEqual(self.inline_packet(assignment), json.dumps(
            packet, sort_keys=True, ensure_ascii=False, indent=2,
        ) + "\n")
        self.assertIn("sole execution assignment", assignment)
        self.assertIn("only oracle and handoff mechanics", assignment)
        self.assertIn("helper-managed workspace", assignment)
        self.assertIn("Do not create, adopt, replace, or remove a worktree.", assignment)
        self.assertNotIn("Implement: ", assignment)
        self.assertNotIn("wait-hold", assignment)
        self.assertFalse((self.pilot_dir / "holds").exists())
        self.assertIn("planning_context", packet)
        self.assertTrue(packet["reference_material"])
        for instruction in packet["instructions"]:
            self.assertIn(instruction, assignment)
        self.assertNotIn("caller_workspace_record", started)
        self.assertEqual(workspace_record["schema"], "shiploop-native-pilot-managed-workspace/v1")
        self.assertEqual(workspace_record["workspace"], packet["context"]["workspace"])
        self.assertEqual(workspace_record["receipt"], packet["ask_agent_workspace"]["receipt"])
        self.assertEqual(workspace_record["receipt_sha256"], packet["ask_agent_workspace"]["receipt_sha256"])
        self.assertEqual(started["ask_agent_workspace"], packet["ask_agent_workspace"])
        self.assertTrue(Path(workspace_record["receipt"]).is_file())
        self.assertTrue(Path(workspace_record["workspace"]).is_dir())
        self.assertEqual(
            packet["ask_agent_workspace"]["selected_package"]["helper_sha256"],
            ask_preflight["identity"]["helper_sha256"],
        )

        original_packet = Path(started["packet"]).read_bytes()
        recovered = self.packet_a(attempt)
        self.assertNotIn("inline_native_assignment", recovered)
        self.assertIn("never authorizes a fresh native launch", recovered["next"])
        self.assertEqual(Path(recovered["packet"]).read_bytes(), original_packet)
        self.assertEqual(recovered["ask_agent_workspace_record"], started["ask_agent_workspace_record"])

    def test_cli_dispatcher_selector_is_explicit_and_preserves_unittest_arguments(self) -> None:
        selected_package = self.base / "selected-dispatcher"
        shutil.copytree(DISPATCHER_V3.parent, selected_package)
        selected_card = selected_package / "SKILL.md"

        selected, remaining = dispatcher_from_cli([
            "--dispatcher-skill", str(selected_card), "-k", "selected_dispatcher",
        ])
        self.assertEqual(selected, selected_card.resolve())
        self.assertEqual(remaining, ["-k", "selected_dispatcher"])
        default, default_remaining = dispatcher_from_cli(["-k", "selected_dispatcher"])
        self.assertEqual(default, DISPATCHER_V3)
        self.assertEqual(default_remaining, ["-k", "selected_dispatcher"])

    def test_dispatcher_without_planning_context_is_rejected_before_a_pilot_directory_exists(self) -> None:
        old_dispatcher = self.base / "old-dispatcher"
        shutil.copytree(DISPATCHER_V3.parent, old_dispatcher)
        helper = old_dispatcher / "scripts" / "dispatch.js"
        source = helper.read_text(encoding="utf-8")
        context_capability = "    planning_context: planningContext.SCHEMA,\n"
        self.assertIn(context_capability, source)
        helper.write_text(source.replace(context_capability, "", 1), encoding="utf-8")
        refused = self.prepare(old_dispatcher / "SKILL.md", ok=False)
        self.assertIn("does not support planning_context", refused["stderr"])
        self.assertIn("no pilot was created", refused["stderr"])
        self.assertFalse(self.pilot_dir.exists())

    def test_helper_without_full_capability_set_is_rejected_before_a_pilot_directory_exists(self) -> None:
        legacy = self.base / "legacy-ask-agent"
        shutil.copytree(ASK_AGENT.parent, legacy)
        card = legacy / "SKILL.md"
        card_text = card.read_text(encoding="utf-8")
        self.assertIn(f"version: {ASK_AGENT_VERSION}", card_text)
        card.write_text(card_text.replace(f"version: {ASK_AGENT_VERSION}", "version: 0.4.0", 1),
                        encoding="utf-8")
        helper = legacy / "scripts" / "ask_agent_workspace.py"
        helper_text = helper.read_text(encoding="utf-8")
        declared = '        "capabilities": list(MANAGED_WORKTREE_CAPABILITIES),'
        self.assertIn(declared, helper_text)
        helper.write_text(helper_text.replace(
            declared,
            '        "capabilities": [item for item in MANAGED_WORKTREE_CAPABILITIES '
            'if item != "ignored-output-report"],', 1,
        ), encoding="utf-8")
        refused = self.prepare(ask_agent=card, ok=False)
        self.assertIn("required managed-worktree capabilities: ignored-output-report", refused["stderr"])
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

    def test_finish_drains_deferred_helper_cleanup_after_eager_refill(self) -> None:
        self.prepare()
        attempts = self.claim("A", "B")
        started_a = self.start("A", attempts["A"])
        started_b = self.start("B", attempts["B"])
        self.launch("A", attempts["A"])
        self.launch("B", attempts["B"])

        accepted_a = self.complete_started_step("A", started_a, attempts["A"])
        self.assertTrue(accepted_a["cleanup_pending"])
        c_attempt = self.claim("C")["C"]
        started_c = self.start("C", c_attempt)
        self.launch("C", c_attempt)

        accepted_b = self.complete_started_step("B", started_b, attempts["B"])
        accepted_c = self.complete_started_step("C", started_c, c_attempt)
        self.assertTrue(accepted_b["cleanup_pending"])
        self.assertTrue(accepted_c["cleanup_pending"])

        j_attempt = self.claim("J")["J"]
        started_j = self.start("J", j_attempt)
        self.launch("J", j_attempt)
        accepted_j = self.complete_started_step("J", started_j, j_attempt)
        self.assertTrue(accepted_j["cleanup_pending"])

        finished = self.call("finish", "--pilot-dir", str(self.pilot_dir))
        self.assertTrue(finished["complete"])
        self.assertTrue(finished["trace"]["zero_owned_worktrees"])
        self.assertTrue(finished["trace"]["deferred_cleanup_after_safe_refill"])
        self.assertEqual(finished["trace"]["deferred_cleanup_attempts"], ["A", "B", "C", "J"])
        for started in (started_a, started_b, started_c, started_j):
            self.assertFalse(Path(started["workspace"]).exists())
        self.assertTrue((self.pilot_dir / "results" / "finish.json").is_file())

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
        self.assertTrue(accepted_a["cleanup_pending"])
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
    try:
        DEFAULT_DISPATCHER, unittest_argv = dispatcher_from_cli(sys.argv[1:])
    except ValueError as exc:
        print(f"test_native_pilot: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    unittest.main(argv=[sys.argv[0], *unittest_argv])
