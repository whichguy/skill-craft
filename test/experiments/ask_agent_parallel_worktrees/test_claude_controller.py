"""Synthetic Claude transport and transcript-capture checks; no model calls."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import claude_briefs
import claude_controller
import claude_hooks
import prompts


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


class ClaudePromptTests(unittest.TestCase):
    def test_parent_prompt_maps_host_and_cli_paths_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix="claude run ") as temp:
            run = Path(temp) / "experiment run"
            run.mkdir(parents=True)
            run = run.resolve()
            common = prompts.make_compact_prompt(run, 3, "parallel", "commits")
            transformed, mapping = claude_controller.transform_parent_prompt(
                common, run, 3, "parallel", "commits",
            )

        self.assertNotIn("Grok", transformed)
        self.assertIn("Claude Code Sonnet-medium parent", transformed)
        self.assertIn("run_in_background", transformed)
        self.assertIn("claude_briefs.py", transformed)
        self.assertIn("SUCCESS TERMINAL BOUNDARY", transformed)
        self.assertIn("worker-start", transformed)
        self.assertIn("worker-finish", transformed)
        self.assertEqual(mapping["schema"], "ask-agent.claude-parent-prompt-map/v1")
        self.assertEqual(len(mapping["replacements"]), 4)
        self.assertEqual(mapping["source_sha256"], digest(common.encode("utf-8")))
        self.assertEqual(mapping["transformed_sha256"], digest(transformed.encode("utf-8")))

    def test_cli_errors_include_rationale_direct_evidence_and_recovery(self):
        with tempfile.TemporaryDirectory(prefix="claude cli error ") as temp:
            run = Path(temp) / "missing run"
            commands = (
                (claude_controller.main, ["prepare", "--run", str(run)]),
                (claude_briefs.main, ["--run", str(run), "--emit-worker", "1"]),
            )
            for invoke, arguments in commands:
                stream = io.StringIO()
                with contextlib.redirect_stderr(stream):
                    status = invoke(arguments)
                self.assertEqual(status, 2)
                result = json.loads(stream.getvalue())
                self.assertEqual(result["rationale_ref"], "CONTRACT.md#claude-native-evidence")
                self.assertEqual(result["evidence"]["run"]["path"], str(run.resolve()))
                self.assertEqual(result["evidence"]["manifest"]["path"], str((run / "manifest.json").resolve()))
                self.assertIn("operator_launch", result["evidence"])
                self.assertIn("settings", result["evidence"])
                self.assertIn("hooks", result["evidence"])
                self.assertIn("new run directory", result["recovery"])

    def test_agent_conversion_preserves_common_prompt_and_binds_every_bash_call(self):
        with tempfile.TemporaryDirectory(prefix="worker root ") as temp:
            worktree = Path(temp) / "worker 1"
            worktree.mkdir()
            common_prompt = "The complete common prompt, including exact commit proof commands."
            common_arguments = {
                "description": "Implement only step one.",
                "prompt": common_prompt,
                "cwd": str(worktree),
                "background": True,
            }
            result = claude_briefs.agent_arguments(common_arguments)

        self.assertEqual(set(result), {"description", "subagent_type", "run_in_background", "prompt"})
        self.assertEqual(result["description"], common_arguments["description"])
        self.assertEqual(result["subagent_type"], "general-purpose")
        self.assertIs(result["run_in_background"], True)
        self.assertTrue(result["prompt"].endswith("\n\n" + common_prompt))
        self.assertIn("cd '", result["prompt"])
        self.assertIn("&&", result["prompt"])
        self.assertIn("each exact emitted commit-proof command", result["prompt"])
        self.assertIn("remaining command unchanged", result["prompt"])
        self.assertNotIn('"cwd"', result)

    def test_hook_settings_are_run_local_and_cover_required_lifecycle(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            settings = claude_hooks.settings_object(
                root / "hooks", script_path=root / "claude_hooks.py", python_path=sys.executable,
            )
        self.assertEqual(set(settings["hooks"]), set(claude_hooks.HOOK_EVENTS))
        for rows in settings["hooks"].values():
            command = rows[0]["hooks"][0]["command"]
            self.assertIn("--record", command)
            self.assertIn(str(root / "hooks"), command)


class ClaudeCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="claude capture ")
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name) / "run"
        self.operator = self.run / "operator"
        self.native = self.operator / "claude-native"
        self.hooks = self.native / "hooks"
        self.common = self.operator / "compact-dispatch"
        self.claude_dispatch = self.operator / "claude-dispatch"
        self.worker_root = self.run / "worker 1"
        self.worker_root.mkdir(parents=True)
        self.common.mkdir(parents=True)
        self.claude_dispatch.mkdir(parents=True)
        self.hooks.mkdir(parents=True)
        self.session = "session-abc"
        self.agent_id = "agent-1"
        self.tool_use_id = "toolu-1"
        self.worker_id = "1"
        self.parent_transcript = self.run / "parent.jsonl"
        self.worker_transcript = self.run / "child.jsonl"
        self.parent_transcript.write_text('{"role":"parent"}\n', encoding="utf-8")
        self.worker_transcript.write_text('{"role":"worker"}\n', encoding="utf-8")
        self._write_inputs()

    def _write_inputs(self):
        self.run.mkdir(parents=True, exist_ok=True)
        write_json(self.run / "manifest.json", {"run_id": "run-1", "workers": 1})
        write_json(self.operator / "launch.json", {"session_id": self.session})
        write_json(self.operator / "process-result.json", {"exit_code": 0})
        common_args = {
            "description": "Implement only step one.",
            "prompt": "common assignment text",
            "cwd": str(self.worker_root),
            "background": True,
        }
        common_path = self.common / "worker-1.json"
        common_record = {"worker_id": self.worker_id, "native_arguments": common_args}
        write_json(common_path, common_record)
        common_bytes = common_path.read_bytes()
        agent_args = claude_briefs.agent_arguments(common_args)
        assignment = {
            "schema": "ask-agent.claude-dispatch-assignment/v1",
            "worker_id": self.worker_id,
            "source_assignment_path": str(common_path.resolve()),
            "source_assignment_sha256": digest(common_bytes),
            "source_prompt_sha256": digest(common_args["prompt"].encode()),
            "prompt_sha256": digest(agent_args["prompt"].encode()),
            "agent_arguments": agent_args,
        }
        assignment_path = self.claude_dispatch / "worker-1.json"
        write_json(assignment_path, assignment)
        assignment_bytes = assignment_path.read_bytes()
        write_json(self.claude_dispatch / "index.json", {
            "schema": "ask-agent.claude-dispatch-index/v1",
            "run_id": "run-1",
            "assignments": [{
                "worker_id": self.worker_id,
                "assignment_path": str(assignment_path.resolve()),
                "sha256": digest(assignment_bytes),
                "source_assignment_path": str(common_path.resolve()),
                "source_assignment_sha256": digest(common_bytes),
                "source_prompt_sha256": assignment["source_prompt_sha256"],
                "prompt_sha256": assignment["prompt_sha256"],
            }],
        })
        self.agent_arguments = agent_args
        events = [
            {
                "type": "assistant",
                "session_id": self.session,
                "message": {"content": [{
                    "type": "tool_use", "id": self.tool_use_id,
                    "name": "Agent", "input": agent_args,
                }]},
            },
            {
                "type": "system", "subtype": "task_started", "session_id": self.session,
                "task_id": self.agent_id, "tool_use_id": self.tool_use_id,
            },
            {
                "type": "system", "subtype": "task_notification", "session_id": self.session,
                "task_id": self.agent_id, "tool_use_id": self.tool_use_id, "status": "completed",
            },
        ]
        (self.operator / "stdout.jsonl").write_text(
            "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8",
        )
        self._hook({
            "hook_event_name": "SessionStart", "session_id": self.session,
            "transcript_path": str(self.parent_transcript),
        })
        self._hook({
            "hook_event_name": "SubagentStart", "session_id": self.session,
            "agent_id": self.agent_id, "agent_type": "general-purpose",
            "transcript_path": str(self.parent_transcript),
        })
        self._hook({
            "hook_event_name": "SubagentStop", "session_id": self.session,
            "agent_id": self.agent_id, "agent_type": "general-purpose",
            "transcript_path": str(self.parent_transcript),
            "agent_transcript_path": str(self.worker_transcript),
        })
        self._hook({
            "hook_event_name": "SessionEnd", "session_id": self.session,
            "transcript_path": str(self.parent_transcript),
        })

    def _hook(self, payload):
        raw = (json.dumps(payload) + "\n").encode("utf-8")
        claude_hooks.record_hook(self.hooks, raw_input=raw, observed_epoch=1.0)

    def test_capture_exports_session_bound_parent_and_child_with_mapping(self):
        result = claude_controller.capture(self.run)
        self.assertTrue(result["passed"], result)
        index_path = self.native / "transcript-index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        self.assertEqual(index["schema"], "ask-agent.claude-transcript-index/v1")
        self.assertEqual([row["kind"] for row in index["rows"]], ["parent", "worker"])
        worker = index["rows"][1]
        self.assertEqual(worker["worker_id"], self.worker_id)
        self.assertEqual(worker["agent_id"], self.agent_id)
        self.assertEqual(worker["task_id"], self.agent_id)
        self.assertEqual(worker["tool_use_id"], self.tool_use_id)
        self.assertEqual(Path(worker["source_path"]), self.worker_transcript.resolve())
        self.assertEqual(Path(worker["retained_path"]).read_bytes(), self.worker_transcript.read_bytes())
        self.assertEqual(result["transcript_index_sha256"], digest(index_path.read_bytes()))
        self.assertTrue((self.native / "capture_result.json").is_file())

    def test_missing_subagent_stop_is_a_retained_failure(self):
        stop = next(self.hooks.glob("*.json"))
        for path in list(self.hooks.glob("*.json")):
            record = json.loads(path.read_text())
            if record["payload"]["hook_event_name"] == "SubagentStop":
                path.unlink()
                break
        result = claude_controller.capture(self.run)
        self.assertFalse(result["passed"])
        self.assertIn("SubagentStart/Stop IDs", result["error"])
        self.assertTrue((self.native / "capture_result.json").exists())
        self.assertTrue((self.operator / "capture-attempt").is_dir())
        self.assertEqual(result["rationale_ref"], "CONTRACT.md#claude-native-evidence")
        self.assertEqual(result["evidence"]["manifest"]["path"], str((self.run / "manifest.json").resolve()))
        self.assertTrue(result["evidence"]["operator_launch"]["exists"])
        self.assertTrue(result["evidence"]["hooks"]["exists"])
        self.assertTrue(result["evidence"]["capture_attempt"]["exists"])
        self.assertIn("new run directory", result["recovery"])

    def test_duplicate_agent_id_is_ambiguous_and_retained(self):
        self._hook({
            "hook_event_name": "SubagentStop", "session_id": self.session,
            "agent_id": self.agent_id, "agent_type": "general-purpose",
            "transcript_path": str(self.parent_transcript),
            "agent_transcript_path": str(self.worker_transcript),
        })
        result = claude_controller.capture(self.run)
        self.assertFalse(result["passed"])
        self.assertIn("duplicate", result["error"].lower())

    def test_replayed_session_record_is_rejected(self):
        self._hook({
            "hook_event_name": "SessionEnd", "session_id": "other-session",
            "transcript_path": str(self.parent_transcript),
        })
        result = claude_controller.capture(self.run)
        self.assertFalse(result["passed"])
        self.assertIn("replayed or belongs to another session", result["error"])

    def test_capture_attempt_is_immutable_on_replay(self):
        result = claude_controller.capture(self.run)
        self.assertTrue(result["passed"], result)
        capture_path = self.native / "capture_result.json"
        index_path = self.native / "transcript-index.json"
        before = (capture_path.read_bytes(), index_path.read_bytes())
        with self.assertRaisesRegex(claude_controller.ClaudeControllerError, "already exists"):
            claude_controller.capture(self.run)
        self.assertEqual((capture_path.read_bytes(), index_path.read_bytes()), before)

    def test_native_bash_display_label_can_differ_from_command(self):
        command, label = "python3 -B /trial/operator/operations.py prepare-batch --run /trial", "Prepare batch"
        events = [
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "bash", "name": "Bash", "input": {"command": command, "description": label}}]}},
            {"type": "system", "subtype": "task_started", "task_type": "local_bash", "tool_use_id": "bash", "task_id": "task", "description": label},
            {"type": "system", "subtype": "task_notification", "tool_use_id": "bash", "task_id": "task", "status": "completed", "summary": label},
        ]
        filtered, starts = claude_controller.filter_local_bash_task_events(events)
        self.assertEqual(filtered, events[:1])
        self.assertEqual(starts["bash"]["command"], command)
        events[2]["summary"] = "wrong task"
        with self.assertRaisesRegex(ValueError, "does not match"):
            claude_controller.filter_local_bash_task_events(events)

    def test_typed_local_bash_and_display_only_agent_description_binding(self):
        lines = (self.operator / "stdout.jsonl").read_text().splitlines()
        agent_event = json.loads(lines[0])
        observed_args = agent_event["message"]["content"][0]["input"]
        self.assertTrue(self.agent_arguments["description"].endswith("."))
        observed_args["description"] = observed_args["description"].rstrip(".")
        lines[0] = json.dumps(agent_event)
        self.assertTrue(claude_controller.agent_arguments_match(observed_args, self.agent_arguments))
        with self.subTest("changed prompt remains mismatched"):
            changed = json.loads(json.dumps(observed_args))
            changed["prompt"] += " altered"
            self.assertFalse(claude_controller.agent_arguments_match(changed, self.agent_arguments))
        with self.subTest("extra arguments remain mismatched"):
            extra = json.loads(json.dumps(observed_args))
            extra["unexpected"] = True
            self.assertFalse(claude_controller.agent_arguments_match(extra, self.agent_arguments))

        command = (
            "python3 -B /Users/dadleet/.codex/visualizations/2026/10/08/01a11b38-d078-77c2-a7fd-4af1d1bd5e5f/"
            "ask-agent-encapsulation/sonnet-harness/live-r1/campaign/commit3-a/operator/operations.py prepare-batch "
            "--run /Users/dadleet/.codex/visualizations/2026/10/08/01a11b38-d078-77c2-a7fd-4af1d1bd5e5f/"
            "ask-agent-encapsulation/sonnet-harness/live-r1/campaign/commit3-a --compact"
        )
        bash_tool_id = "toolu-local-bash"
        bash_task_id = "task-local-bash"
        lines.extend(json.dumps(event) for event in (
            {
                "type": "assistant", "session_id": self.session,
                "message": {"content": [{
                    "type": "tool_use", "id": bash_tool_id,
                    "name": "Bash", "input": {"command": command},
                }]},
            },
            {
                "type": "system", "subtype": "task_started", "session_id": self.session,
                "task_type": "local_bash", "task_id": bash_task_id,
                "tool_use_id": bash_tool_id, "description": command, "is_backgrounded": False,
            },
            {
                "type": "system", "subtype": "task_notification", "session_id": self.session,
                "task_id": bash_task_id, "tool_use_id": bash_tool_id,
                "status": "completed", "summary": command,
            },
        ))
        (self.operator / "stdout.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = claude_controller.capture(self.run)
        self.assertTrue(result["passed"], result)
        index = json.loads((self.native / "transcript-index.json").read_text(encoding="utf-8"))
        worker = next(row for row in index["rows"] if row["kind"] == "worker")
        self.assertEqual(worker["agent_description"], observed_args["description"])
        self.assertEqual(index["worker_count"], 1)

    def test_parent_stream_agent_arguments_must_match_frozen_prompt_mapping(self):
        lines = (self.operator / "stdout.jsonl").read_text().splitlines()
        event = json.loads(lines[0])
        event["message"]["content"][0]["input"]["prompt"] += " altered"
        lines[0] = json.dumps(event)
        (self.operator / "stdout.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = claude_controller.capture(self.run)
        self.assertFalse(result["passed"])
        self.assertIn("Claude Agent tool input", result["error"])


if __name__ == "__main__":
    unittest.main()
