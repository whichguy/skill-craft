from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from grok_adapter import (  # noqa: E402
    GrokAdapterError,
    build_argv,
    inspect_selection,
    observe_control_input_references,
    summarize_events,
)


class GrokAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-e2e-grok-adapter-")
        self.root = Path(self.temp.name)
        self.repo = self.root / "product"
        self.repo.mkdir()
        self.skill_root = self.root / "shiploop"
        (self.skill_root / "scripts").mkdir(parents=True)
        self.skill = self.skill_root / "SKILL.md"
        self.skill.write_text("---\nname: shiploop\n---\n", encoding="utf-8")
        self.cli = self.skill_root / "scripts" / "shiploop"
        self.cli.write_text("#!/bin/sh\n", encoding="utf-8")
        self.prompt = self.root / "prompt.txt"
        self.prompt.write_text("/shiploop create a game\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _fake_grok(self) -> Path:
        fake = self.root / "fake-grok"
        fake.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, pathlib, sys\n"
            "pathlib.Path(os.environ['CAPTURE']).write_text(json.dumps({'argv': sys.argv[1:], 'cwd': os.getcwd()}))\n"
            "if os.environ.get('INVALID') == '1':\n"
            "    print(json.dumps({'unrelated': {'credential': 'not-returned'}}))\n"
            "elif os.environ.get('DUPLICATE') == '1':\n"
            "    print(json.dumps({'skills': [{'name': 'shiploop', 'source': {'path': os.environ['SKILL']}, 'userInvocable': True}, {'name': 'shiploop', 'source': {'path': os.environ['SKILL']}, 'userInvocable': True}]}))\n"
            "else:\n"
            "    print(json.dumps({'unrelated': {'credential': 'not-returned'}, 'nested': [{'name': 'shiploop', 'description': 'selected', 'source': {'path': os.environ['SKILL'], 'type': 'user'}, 'userInvocable': True}], 'agents': [{'name': 'shiploop', 'source': {'path': '/agent-card.md'}, 'userInvocable': None}], 'skills': [{'name': 'shiploop', 'source': {'path': '/not/selected'}, 'userInvocable': True}]}))\n",
            encoding="utf-8",
        )
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        return fake

    def _inspect_env(self, capture: Path, **extra: str) -> dict[str, str]:
        return {**os.environ, "CAPTURE": str(capture), "SKILL": str(self.skill), **extra}

    def test_inspect_selection_uses_repo_cwd_and_returns_only_selected_record(self) -> None:
        capture = self.root / "inspect-capture.json"
        selection = inspect_selection(str(self._fake_grok()), self.repo, self.skill_root, self._inspect_env(capture))

        self.assertEqual("shiploop", selection["skill"])
        self.assertEqual(str(self.skill.resolve()), selection["source"]["realpath"])
        self.assertEqual("user", selection["source"]["type"])
        self.assertTrue(selection["source"]["user_invocable"])
        self.assertNotIn("not-returned", repr(selection))
        self.assertEqual(
            {"argv": ["inspect", "--json"], "cwd": str(self.repo.resolve())},
            json.loads(capture.read_text(encoding="utf-8")),
        )

    def test_inspect_selection_requires_exactly_one_matching_skill(self) -> None:
        capture = self.root / "inspect-capture.json"
        with self.assertRaisesRegex(GrokAdapterError, "exactly one"):
            inspect_selection(
                str(self._fake_grok()),
                self.repo,
                self.skill,
                self._inspect_env(capture, DUPLICATE="1"),
            )

    def test_inspect_selection_does_not_leak_unrelated_inspect_content_in_errors(self) -> None:
        capture = self.root / "inspect-capture.json"
        with self.assertRaises(GrokAdapterError) as raised:
            inspect_selection(
                str(self._fake_grok()),
                self.repo,
                self.skill,
                self._inspect_env(capture, INVALID="1"),
            )
        self.assertNotIn("not-returned", str(raised.exception))

    def test_build_argv_uses_literal_prompt_file_and_safe_default_permission_mode(self) -> None:
        argv = build_argv(
            "/opt/test/grok",
            self.prompt,
            self.repo,
            "grok-4.6",
            37,
        )

        self.assertEqual(
            [
                "/opt/test/grok",
                "--cwd",
                str(self.repo),
                "--prompt-file",
                str(self.prompt),
                "--verbatim",
                "--output-format",
                "streaming-json",
                "--model",
                "grok-4.6",
                "--max-turns",
                "37",
                "--permission-mode",
                "default",
                "--no-auto-update",
            ],
            argv,
        )
        self.assertNotIn("--always-approve", argv)
        self.assertNotIn("bypassPermissions", argv)

    def test_build_argv_supports_explicit_opt_in_and_rejects_bad_turn_limit(self) -> None:
        argv = build_argv(
            "/opt/test/grok",
            self.prompt,
            self.repo,
            "grok-4.6",
            2,
            permission_mode="acceptEdits",
            reasoning_effort="high",
        )
        self.assertEqual("acceptEdits", argv[argv.index("--permission-mode") + 1])
        self.assertEqual("high", argv[argv.index("--reasoning-effort") + 1])
        with self.assertRaisesRegex(GrokAdapterError, "positive integer"):
            build_argv("grok", self.prompt, self.repo, "grok-4.6", 0)

    def test_summarize_events_requires_structured_exact_cli_invocation_and_correlates_completion(self) -> None:
        alias_root = self.root / "shiploop-alias"
        alias_root.symlink_to(self.skill_root, target_is_directory=True)
        aliased_cli = alias_root / "scripts" / "shiploop"
        events = self.root / "events.ndjson"
        records = [
            {"type": "available_commands", "tools": [], "commands": ["/shiploop", "/other"]},
            {
                "type": "tool_call",
                "toolCallId": "read-only",
                "toolName": "read_file",
                "rawInput": {"path": str(self.cli)},
            },
            {
                "type": "tool_call",
                "toolCallId": "invoke-1",
                "toolName": "run_terminal_cmd",
                "rawInput": {"command": f"python3 {self.cli} init --repo {self.repo}"},
            },
            {"type": "tool_call_update", "toolCallId": "invoke-1", "status": "completed", "rawOutput": {"exit_code": 0}},
            {"type": "text", "data": f"I ran python3 {self.cli} complete"},
            {"type": "usage", "usage": {"input_tokens": 12, "output_tokens": 4}},
            {
                "type": "end",
                "stopReason": "end_turn",
                "usage": {"input_tokens": 12, "output_tokens": 4},
                "modelUsage": {"grok-4.6": {"modelCalls": 1}},
            },
            {"type": "future_event", "payload": "ignored"},
        ]
        events.write_text("\n".join(json.dumps(record) for record in records) + "\nnot-json\n", encoding="utf-8")

        summary = summarize_events(events, aliased_cli)

        self.assertTrue(summary["availability"]["observed"])
        self.assertTrue(summary["availability"]["shiploop_command_observed"])
        self.assertEqual(["/shiploop"], summary["availability"]["shiploop_routes"])
        self.assertEqual(["invoke-1"], summary["tool_invocation"]["call_ids"])
        self.assertEqual({"invoke-1": "init"}, summary["tool_invocation"]["subcommands"])
        self.assertEqual(["invoke-1"], summary["tool_completion"]["completed_call_ids"])
        self.assertEqual(
            [
                {
                    "call_id": "invoke-1",
                    "argv_tail": ["init", "--repo", str(self.repo)],
                    "completed": True,
                    "exit_codes": [0],
                }
            ],
            summary["cli_calls"],
        )
        self.assertTrue(summary["shiploop_cli_completed"])
        self.assertTrue(summary["tool_completion"]["cli_tool_completed"])
        self.assertTrue(summary["shiploop_cli_success_observed"])
        self.assertTrue(summary["tool_completion"]["cli_success_observed"])
        self.assertTrue(summary["terminal"]["end_observed"])
        self.assertTrue(summary["usage"]["observed"])
        self.assertEqual(["grok-4.6"], summary["actual_model_keys"])
        self.assertEqual({"future_event": 1}, summary["unknown_event_types"])
        self.assertEqual([9], summary["invalid_json_lines"])

    def test_summarize_events_keeps_noncompleted_status_observational(self) -> None:
        events = self.root / "failed-events.ndjson"
        records = [
            {
                "type": "tool_call",
                "toolCallId": "invoke-2",
                "rawInput": {"argv": ["python3", str(self.cli), "complete"]},
            },
            {"type": "tool_call_update", "toolCallId": "invoke-2", "status": "failed"},
            {"type": "end", "stopReason": "max_turn_requests"},
        ]
        events.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

        summary = summarize_events(events, self.cli)

        self.assertTrue(summary["tool_completion"]["observed"])
        self.assertFalse(summary["tool_completion"]["completed"])
        self.assertFalse(summary["shiploop_cli_success_observed"])
        self.assertFalse(summary["tool_completion"]["cli_exit_code_observed"])
        self.assertEqual({"failed": 1}, summary["tool_completion"]["statuses"])
        self.assertEqual(["max_turn_requests"], summary["terminal"]["end_stop_reasons"])

    def test_interim_exit_placeholders_do_not_supply_terminal_exit_evidence(self) -> None:
        # Grok emits exit_code=0 while a Bash tool is still in_progress. That
        # placeholder must not stand in for a missing or failing final result.
        for status, final_code, expected_codes in (
            (None, None, []),
            ("completed", None, []),
            ("completed", 9, [9]),
            ("failed", 9, [9]),
            ("completed", 0, [0]),
        ):
            with self.subTest(status=status, final_code=final_code):
                records = [
                    {"type": "tool_call", "toolCallId": "call", "rawInput": {
                        "argv": ["python3", str(self.cli), "improve-complete"]}},
                    {"type": "tool_call_update", "toolCallId": "call", "status": "in_progress",
                     "rawOutput": {"exit_code": 0}},
                ]
                if status is not None:
                    records.append({"type": "tool_call_update", "toolCallId": "call", "status": status,
                                    "rawOutput": {} if final_code is None else {"exit_code": final_code}})
                events = self.root / "interim-exit-events.jsonl"
                events.write_text("\n".join(json.dumps(row) for row in records), encoding="utf-8")
                summary = summarize_events(events, self.cli)
                self.assertEqual(summary["cli_calls"][0]["exit_codes"], expected_codes)
                self.assertEqual(summary["cli_calls"][0]["completed"], status == "completed")
                self.assertEqual(summary["shiploop_cli_exit_code_observed"], bool(expected_codes))
                self.assertEqual(summary["shiploop_cli_success_observed"], expected_codes == [0])

    def test_summarize_events_unwraps_stdout_receipts_and_ignores_stderr_json(self) -> None:
        events = self.root / "captured-events.jsonl"
        records = [
            {
                "received_at": "2026-09-17T00:00:00Z",
                "stream": "stderr",
                "line": '{"type":"end","modelUsage":{"not-a-model":{}}}',
                "payload": {"type": "end", "modelUsage": {"not-a-model": {}}},
            },
            {
                "timestamp": "2026-09-17T00:00:01Z",
                "stream": "stdout",
                "line": "tool call",
                "payload": {
                    "type": "tool_call",
                    "toolCallId": "invoke-3",
                    "rawInput": {"argv": ["python3", str(self.cli), "complete"]},
                },
            },
            {
                "received_at": "2026-09-17T00:00:02Z",
                "stream": "stdout",
                "line": "tool update",
                "payload": {
                    "type": "tool_call_update",
                    "toolCallId": "invoke-3",
                    "status": "completed",
                    "rawOutput": {"exitCode": 9},
                },
            },
            {
                "received_at": "2026-09-17T00:00:03Z",
                "stream": "stdout",
                "line": "end",
                "payload": {"type": "end", "modelUsage": {"grok-4.6": {}}},
            },
        ]
        events.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

        summary = summarize_events(events, self.cli)

        self.assertEqual(3, summary["event_count"])
        self.assertEqual(4, summary["capture_receipts"]["count"])
        self.assertEqual(1, summary["capture_receipts"]["ignored_stderr_count"])
        self.assertTrue(summary["shiploop_cli_completed"])
        self.assertTrue(summary["shiploop_cli_exit_code_observed"])
        self.assertFalse(summary["shiploop_cli_success_observed"])
        self.assertTrue(summary["terminal_end_observed"])
        self.assertEqual(["grok-4.6"], summary["actual_model_keys"])
        # A completed host tool update can carry a non-zero command exit.  The
        # adapter records host-tool completion, never a ShipLoop success claim.
        self.assertNotIn("script_success", summary)

    def test_summarize_events_requires_an_execution_position(self) -> None:
        events = self.root / "execution-position-events.ndjson"
        records = [
            {"type": "tool_call", "toolCallId": "cat", "rawInput": {"command": f"cat {self.cli}"}},
            {"type": "tool_call", "toolCallId": "echo", "rawInput": {"command": f"echo {self.cli} next"}},
            {"type": "tool_call", "toolCallId": "grep", "rawInput": {"command": f"grep needle {self.cli}"}},
            {
                "type": "tool_call",
                "toolCallId": "python",
                "rawInput": {"command": f"python3 {self.cli} init --repo {self.repo}"},
            },
            {
                "type": "tool_call",
                "toolCallId": "direct",
                "rawInput": {"argv": [str(self.cli), "next", "--run-dir", str(self.repo / ".shiploop")]},
            },
        ]
        events.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

        summary = summarize_events(events, self.cli)

        self.assertEqual(["direct", "python"], summary["tool_invocation"]["call_ids"])
        self.assertEqual({"direct": "next", "python": "init"}, summary["tool_invocation"]["subcommands"])

    def test_summarize_events_recognizes_direct_and_python_v3_improve_callbacks(self) -> None:
        events = self.root / "v3-improve-callback-events.ndjson"
        run_dir = self.repo / ".shiploop"
        records = [
            {
                "type": "tool_call",
                "toolCallId": "direct-bind",
                "rawInput": {"argv": [str(self.cli), "improve-bind", "--run-dir", str(run_dir),
                                     "--action", "PLAN", "--skill-card", "/tmp/improve/SKILL.md"]},
            },
            {
                "type": "tool_call",
                "toolCallId": "direct-complete",
                "rawInput": {"command": f"{self.cli} improve-complete --run-dir={run_dir} --action=PLAN --result=/tmp/plan-improve.md"},
            },
            {
                "type": "tool_call",
                "toolCallId": "python-complete",
                "rawInput": {"command": f"python3 {self.cli} improve-complete --run-dir={run_dir} --action=PLAN --result=/tmp/plan-improve.md"},
            },
            {
                "type": "tool_call",
                "toolCallId": "cat-mention",
                "rawInput": {"command": f"cat {self.cli} improve-complete"},
            },
            {
                "type": "tool_call",
                "toolCallId": "echo-mention",
                "rawInput": {"command": f"echo {self.cli} improve-complete"},
            },
        ]
        events.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

        summary = summarize_events(events, self.cli)

        self.assertEqual(["direct-bind", "direct-complete", "python-complete"], summary["tool_invocation"]["call_ids"])
        self.assertEqual(
            {
                "direct-bind": "improve-bind",
                "direct-complete": "improve-complete",
                "python-complete": "improve-complete",
            },
            summary["tool_invocation"]["subcommands"],
        )
        self.assertEqual(
            ["improve-bind", "improve-complete", "improve-complete"],
            [call["argv_tail"][0] for call in summary["cli_calls"]],
        )

    def test_summarize_events_keeps_v3_improve_complete_after_supported_python_heredoc(self) -> None:
        events = self.root / "v3-heredoc-complete-events.ndjson"
        run_dir = self.repo / ".shiploop"
        command = (
            "python3 - <<'PY'\n"
            f"print('python3 {self.cli} improve-complete --action=fake')\n"
            "PY\n"
            f"python3 {self.cli} improve-complete --run-dir={run_dir} --action=REAL --result=/tmp/plan-improve.md"
        )
        events.write_text(
            json.dumps({"type": "tool_call", "toolCallId": "v3-heredoc", "rawInput": {"command": command}}),
            encoding="utf-8",
        )

        summary = summarize_events(events, self.cli)

        self.assertEqual(
            [["improve-complete", f"--run-dir={run_dir}", "--action=REAL", "--result=/tmp/plan-improve.md"]],
            [call["argv_tail"] for call in summary["cli_calls"]],
        )

    def test_summarize_events_rejects_unprovable_conditional_pipeline_and_background_callbacks(self) -> None:
        events = self.root / "compound-callback-events.ndjson"
        callback = (
            f"python3 {self.cli} complete --run-dir={self.repo / '.shiploop'} "
            "--action=accepted-action --result=/tmp/accepted-result.json"
        )
        records = [
            {
                "type": "tool_call",
                "toolCallId": "false-and-callback",
                "rawInput": {"command": f"false && {callback}; true"},
            },
            {
                "type": "tool_call",
                "toolCallId": "true-or-callback",
                "rawInput": {"command": f"true || {callback}"},
            },
            {
                "type": "tool_call",
                "toolCallId": "pipeline-callback",
                "rawInput": {"command": f"printf body | {callback}"},
            },
            {
                "type": "tool_call",
                "toolCallId": "background-callback",
                "rawInput": {"command": f"{callback} & wait"},
            },
            {
                "type": "tool_call_update",
                "toolCallId": "false-and-callback",
                "status": "completed",
                "rawOutput": {"exitCode": 0},
            },
            {
                "type": "tool_call_update",
                "toolCallId": "true-or-callback",
                "status": "completed",
                "rawOutput": {"exitCode": 0},
            },
            {
                "type": "tool_call_update",
                "toolCallId": "pipeline-callback",
                "status": "completed",
                "rawOutput": {"exitCode": 0},
            },
            {
                "type": "tool_call_update",
                "toolCallId": "background-callback",
                "status": "completed",
                "rawOutput": {"exitCode": 0},
            },
        ]
        events.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

        summary = summarize_events(events, self.cli)

        self.assertFalse(summary["cli_invocation_observed"])
        self.assertEqual([], summary["cli_calls"])
        self.assertFalse(summary["shiploop_cli_completed"])
        self.assertFalse(summary["shiploop_cli_success_observed"])

    def test_summarize_events_rejects_final_status_masking_and_prior_shell_control(self) -> None:
        events = self.root / "final-status-masking-events.ndjson"
        callback = (
            f"python3 {self.cli} complete --run-dir={self.repo / '.shiploop'} "
            "--action=accepted-action --result=/tmp/accepted-result.json"
        )
        commands = {
            "trailing-true": f"{callback}; true",
            "trailing-exit": f"{callback}; exit 0",
            "early-exit": f"exit 0; {callback}",
            "early-return": f"return 0; {callback}",
            "early-exec": f"exec /usr/bin/true; {callback}",
            "if-control": f"if false; then :; fi; {callback}",
            "function-definition": f"guard() {{ :; }}; {callback}",
            "spaced-function-definition": f"guard () {{ :; }}; {callback}",
        }
        records: list[dict[str, object]] = []
        for call_id, command in commands.items():
            records.extend(
                [
                    {
                        "type": "tool_call",
                        "toolCallId": call_id,
                        "rawInput": {"command": command},
                    },
                    {
                        "type": "tool_call_update",
                        "toolCallId": call_id,
                        "status": "completed",
                        "rawOutput": {"exitCode": 0},
                    },
                ]
            )
        events.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

        summary = summarize_events(events, self.cli)

        self.assertFalse(summary["cli_invocation_observed"])
        self.assertEqual([], summary["cli_calls"])
        self.assertFalse(summary["shiploop_cli_completed"])
        self.assertFalse(summary["shiploop_cli_success_observed"])

    def test_summarize_events_credits_only_the_terminal_cli_from_one_shell_tool(self) -> None:
        events = self.root / "multiple-cli-calls-events.ndjson"
        run_dir = self.repo / ".shiploop"
        workspace_root = self.root / "workspace"
        result_one = self.root / "result-one.json"
        result_two = self.root / "result-two.json"
        command = (
            f"python3 {self.cli} workspace start --repo {self.repo} --workspace-root={workspace_root}; "
            f"python3 {self.cli} complete --run-dir={run_dir} --action=ACT-1 --result {result_one}; "
            f"{self.cli} done --run-dir {run_dir} --action ACT-2 --result={result_two}"
        )
        records = [
            {"type": "tool_call", "toolCallId": "multi", "rawInput": {"command": command}},
            {"type": "tool_call_update", "toolCallId": "multi", "status": "completed", "rawOutput": {"exitCode": 0}},
        ]
        events.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

        summary = summarize_events(events, self.cli)

        self.assertEqual(["multi"], summary["tool_invocation"]["call_ids"])
        self.assertEqual({"multi": "done"}, summary["tool_invocation"]["subcommands"])
        self.assertEqual(
            [
                {
                    "call_id": "multi",
                    "argv_tail": [
                        "done",
                        "--run-dir",
                        str(run_dir),
                        "--action",
                        "ACT-2",
                        f"--result={result_two}",
                    ],
                    "completed": True,
                    "exit_codes": [0],
                },
            ],
            summary["cli_calls"],
        )

    def test_summarize_events_expands_literal_same_command_assignments_without_evaluating_shell(self) -> None:
        events = self.root / "assignment-events.ndjson"
        command = (
            f"SKILL_ROOT='{self.skill_root}'; "
            'CLI="$SKILL_ROOT/scripts/shiploop"; '
            'python3 "$CLI" workspace start --repo /tmp/product --workspace-root /tmp/workspace'
        )
        records = [
            {
                "type": "tool_call",
                "toolCallId": "variable-cli",
                "rawInput": {"command": command},
            },
            {
                "type": "tool_call",
                "toolCallId": "unresolved",
                "rawInput": {"command": 'python3 "$UNKNOWN_CLI" next'},
            },
            {
                "type": "tool_call",
                "toolCallId": "substitution",
                "rawInput": {"command": 'python3 "$(printf nope)" next'},
            },
        ]
        events.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

        summary = summarize_events(events, self.cli)

        self.assertEqual(["variable-cli"], summary["tool_invocation"]["call_ids"])
        self.assertEqual({"variable-cli": "workspace"}, summary["tool_invocation"]["subcommands"])

    def test_summarize_events_splits_safe_multiline_shell_commands(self) -> None:
        events = self.root / "multiline-shell-events.ndjson"
        workspace = self.root / "workspace"
        command = (
            f"CLI='{self.cli}'\n"
            f"REPO='{self.repo}'\n"
            "mkdir -p \"$REPO/generated\"\n"
            "git -C \"$REPO\" status --short\n"
            "# launch after setup\n"
            'python3 "$CLI" workspace start --repo "$REPO" --workspace-root '
            f"'{workspace}'"
        )
        records = [{"type": "tool_call", "toolCallId": "multiline", "rawInput": {"command": command}}]
        events.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

        summary = summarize_events(events, self.cli)

        self.assertEqual(
            [
                {
                    "call_id": "multiline",
                    "argv_tail": [
                        "workspace",
                        "start",
                        "--repo",
                        str(self.repo),
                        "--workspace-root",
                        str(workspace),
                    ],
                    "completed": False,
                    "exit_codes": [],
                }
            ],
            summary["cli_calls"],
        )

    def test_summarize_events_rejects_quoted_comment_and_heredoc_cli_mentions(self) -> None:
        events = self.root / "nonexecutable-cli-mentions-events.ndjson"
        records = [
            {
                "type": "tool_call",
                "toolCallId": "quoted",
                "rawInput": {
                    "command": f'echo "first line\npython3 {self.cli} workspace start\nlast line"'
                },
            },
            {
                "type": "tool_call",
                "toolCallId": "comment",
                "rawInput": {"command": f"# python3 {self.cli} workspace start\necho harmless"},
            },
            {
                "type": "tool_call",
                "toolCallId": "heredoc",
                "rawInput": {
                    "command": f"cat <<'EOF'\npython3 {self.cli} workspace start\nEOF"
                },
            },
        ]
        events.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

        summary = summarize_events(events, self.cli)

        self.assertFalse(summary["cli_invocation_observed"])
        self.assertEqual([], summary["cli_calls"])

    def test_summarize_events_skips_supported_python_heredoc_body_and_keeps_callback(self) -> None:
        events = self.root / "supported-heredoc-events.ndjson"
        run_dir = self.repo / ".shiploop"
        result = self.root / "result.json"
        command = (
            f"WT='{self.repo}'\n"
            'git -C "$WT" status --short\n'
            'node -e "process.exit(0)"\n'
            "python3 - <<'PY'\n"
            f"python3 {self.cli} complete --run-dir=/fake --action=fake --result=/fake\n"
            "print('body contains a fake callback')\n"
            "PY\n"
            f"python3 {self.cli} complete '--run-dir={run_dir}' --action=REAL --result={result}"
        )
        records = [{"type": "tool_call", "toolCallId": "supported-heredoc", "rawInput": {"command": command}}]
        events.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

        summary = summarize_events(events, self.cli)

        self.assertEqual(
            [
                {
                    "call_id": "supported-heredoc",
                    "argv_tail": [
                        "complete",
                        f"--run-dir={run_dir}",
                        "--action=REAL",
                        f"--result={result}",
                    ],
                    "completed": False,
                    "exit_codes": [],
                }
            ],
            summary["cli_calls"],
        )

    def test_summarize_events_rejects_unsupported_python_heredoc_forms(self) -> None:
        events = self.root / "unsupported-heredoc-events.ndjson"
        callback = f"python3 {self.cli} complete --run-dir=/run --action=REAL --result=/result"
        records = [
            {
                "type": "tool_call",
                "toolCallId": "unquoted-delimiter",
                "rawInput": {"command": f"python3 - <<PY\nbody\nPY\n{callback}"},
            },
            {
                "type": "tool_call",
                "toolCallId": "dynamic-delimiter",
                "rawInput": {"command": f"python3 - <<'$DELIM'\nbody\n$DELIM\n{callback}"},
            },
            {
                "type": "tool_call",
                "toolCallId": "mismatch",
                "rawInput": {"command": f"python3 - <<'PY'\nbody\nPYX\n{callback}"},
            },
            {
                "type": "tool_call",
                "toolCallId": "multiple",
                "rawInput": {
                    "command": f"python3 - <<'PY'\nbody\nPY\npython3 - <<'PY'\nbody\nPY\n{callback}"
                },
            },
            {
                "type": "tool_call",
                "toolCallId": "strip-tabs",
                "rawInput": {"command": f"python3 - <<-'PY'\nbody\n\tPY\n{callback}"},
            },
            {
                "type": "tool_call",
                "toolCallId": "compound",
                "rawInput": {"command": f"python3 - <<'PY'; echo no\nbody\nPY\n{callback}"},
            },
        ]
        events.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

        summary = summarize_events(events, self.cli)

        self.assertFalse(summary["cli_invocation_observed"])
        self.assertEqual([], summary["cli_calls"])

    def test_summarize_events_does_not_treat_quoted_or_commented_headers_as_supported(self) -> None:
        events = self.root / "quoted-heredoc-header-events.ndjson"
        records = [
            {
                "type": "tool_call",
                "toolCallId": "quoted-header",
                "rawInput": {
                    "command": f'echo "python3 - <<\'PY\'\npython3 {self.cli} complete\nPY"'
                },
            },
            {
                "type": "tool_call",
                "toolCallId": "commented-header",
                "rawInput": {
                    "command": f"# python3 - <<'PY'\n# python3 {self.cli} complete\n# PY"
                },
            },
        ]
        events.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

        summary = summarize_events(events, self.cli)

        self.assertFalse(summary["cli_invocation_observed"])
        self.assertEqual([], summary["cli_calls"])

    def test_summarize_events_keeps_backslash_newline_in_one_cli_command(self) -> None:
        events = self.root / "continued-shell-events.ndjson"
        command = (
            f"CLI='{self.cli}'\n"
            'python3 "$CLI" \\\n'
            f"  workspace start --repo {self.repo} --workspace-root {self.root / 'workspace'}"
        )
        records = [{"type": "tool_call", "toolCallId": "continued", "rawInput": {"command": command}}]
        events.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

        summary = summarize_events(events, self.cli)

        self.assertEqual(
            ["workspace", "start", "--repo", str(self.repo), "--workspace-root", str(self.root / "workspace")],
            summary["cli_calls"][0]["argv_tail"],
        )

    def test_summarize_events_reports_a_qualified_route_without_guessing_its_source(self) -> None:
        events = self.root / "qualified-command-events.ndjson"
        events.write_text(
            json.dumps(
                {
                    "type": "available_commands",
                    "commands": ["/plugin-name:shiploop"],
                    "tools": [],
                }
            ),
            encoding="utf-8",
        )

        summary = summarize_events(events, self.cli)

        self.assertFalse(summary["shiploop_command_observed"])
        self.assertTrue(summary["qualified_shiploop_command_observed"])
        self.assertEqual(["/plugin-name:shiploop"], summary["availability"]["shiploop_routes"])

    def test_control_input_observer_records_stdout_tool_input_paths_and_nested_fields(self) -> None:
        campaign = self.root / "campaign-control"
        trial = self.root / "trial-output"
        observer = self.root / "observer-source"
        for path in (campaign, trial, observer):
            path.mkdir()
        events = self.root / "control-input-events.ndjson"
        records = [
            {
                "received_at": "2026-09-17T00:00:00Z",
                "stream": "stdout",
                "line": "read control",
                "payload": {
                    "type": "tool_call",
                    "toolCallId": "read-control",
                    "toolName": "read_file",
                    "rawInput": {"target_file": str(campaign / "suite-manifest.json")},
                },
            },
            {
                "received_at": "2026-09-17T00:00:01Z",
                "stream": "stdout",
                "line": "read control update",
                "payload": {
                    "type": "tool_call_update",
                    "toolCallId": "read-control",
                    "status": "completed",
                    "rawOutput": {"exitCode": 0, "content": "never retained"},
                },
            },
            {
                "type": "tool_call",
                "toolCallId": "nested-control",
                "toolName": "run_terminal_cmd",
                "rawInput": {
                    "plan": {"targetFile": str(trial / "manifest.json")},
                    "argv": ["cat", str(observer / "grok_adapter.py")],
                },
            },
        ]
        events.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

        observed = observe_control_input_references(
            events,
            {
                "campaign_control": campaign,
                "trial_output": trial,
                "observer_source": observer,
            },
        )

        self.assertTrue(observed["exposure_observed"])
        self.assertEqual("observed-control-input-reference", observed["status"])
        references = {(row["call_id"], row["field"]): row for row in observed["references"]}
        read_reference = references[("read-control", "rawInput.target_file")]
        self.assertEqual("read_file", read_reference["tool"])
        self.assertEqual(str(campaign / "suite-manifest.json"), read_reference["path"])
        self.assertEqual("attempted-input-reference", read_reference["attempt"])
        self.assertTrue(read_reference["successful_read_observed"])
        self.assertIn(("nested-control", "rawInput.plan.targetFile"), references)
        self.assertIn(("nested-control", "rawInput.argv[1]"), references)
        self.assertNotIn("never retained", json.dumps(observed))

    def test_control_input_observer_detects_shell_paths_without_prefix_or_output_false_positives(self) -> None:
        control = self.root / "campaign-control"
        control.mkdir()
        prefix_collision = self.root / "campaign-control-copy" / "suite-manifest.json"
        events = self.root / "control-shell-events.ndjson"
        records = [
            {
                "type": "tool_call",
                "toolCallId": "shell-control",
                "toolName": "run_terminal_cmd",
                "rawInput": {"command": f"cat {control / 'suite-manifest.json'}"},
            },
            {
                "type": "tool_call",
                "toolCallId": "prefix-collision",
                "toolName": "run_terminal_cmd",
                "rawInput": {"command": f"cat {prefix_collision}"},
            },
            {
                "type": "tool_call",
                "toolCallId": "non-path-input",
                "toolName": "say",
                "rawInput": {"message": f"do not inspect {control}"},
            },
            {"type": "text", "data": f"model mentioned {control}"},
            {
                "type": "tool_call_update",
                "toolCallId": "shell-control",
                "status": "completed",
                "rawOutput": {"exitCode": 0, "content": str(control)},
            },
            {
                "received_at": "2026-09-17T00:00:02Z",
                "stream": "stderr",
                "line": "stderr tool call",
                "payload": {
                    "type": "tool_call",
                    "toolCallId": "stderr-control",
                    "toolName": "read_file",
                    "rawInput": {"target_file": str(control / "stderr.txt")},
                },
            },
        ]
        events.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

        observed = observe_control_input_references(events, {"campaign_control": control})

        self.assertTrue(observed["exposure_observed"])
        self.assertEqual(["shell-control"], [row["call_id"] for row in observed["references"]])
        self.assertEqual("rawInput.command", observed["references"][0]["field"])
        self.assertFalse(observed["references"][0]["successful_read_observed"])
        self.assertIn("Relative, encoded, or unreported accesses", " ".join(observed["limitations"]))

    def test_control_read_interim_exit_is_not_success_evidence(self) -> None:
        control = self.root / "observer"
        control.mkdir()
        for final_code in (None, 2, 0):
            with self.subTest(final_code=final_code):
                records = [
                    {"type": "tool_call", "toolCallId": "read", "toolName": "read_file",
                     "rawInput": {"target_file": str(control / "control.json")}},
                    {"type": "tool_call_update", "toolCallId": "read", "status": "in_progress",
                     "rawOutput": {"exit_code": 0}},
                    {"type": "tool_call_update", "toolCallId": "read", "status": "completed",
                     "rawOutput": {} if final_code is None else {"exit_code": final_code}},
                ]
                events = self.root / "interim-control-read.jsonl"
                events.write_text("\n".join(json.dumps(row) for row in records), encoding="utf-8")
                observed = observe_control_input_references(events, {"observer_source": control})
                self.assertTrue(observed["exposure_observed"])
                self.assertEqual(observed["status"], "observed-control-input-reference")
                reference = observed["references"][0]
                self.assertTrue(reference["completed_status_observed"])
                self.assertEqual(reference["zero_exit_code_observed"], final_code == 0)
                self.assertEqual(reference["successful_read_observed"], final_code == 0)

    def test_control_input_observer_resolves_unrelated_symlink_aliases(self) -> None:
        campaign = self.root / "campaign-control"
        campaign.mkdir()
        alias = self.root / "unrelated-alias"
        alias.symlink_to(campaign, target_is_directory=True)
        events = self.root / "control-alias-events.ndjson"
        events.write_text(
            json.dumps({
                "type": "tool_call",
                "toolCallId": "alias-read",
                "toolName": "read_file",
                "rawInput": {"target_file": str(alias / "suite-manifest.json")},
            }),
            encoding="utf-8",
        )

        observed = observe_control_input_references(events, {"campaign_control": campaign})

        self.assertTrue(observed["exposure_observed"])
        self.assertEqual(str(alias / "suite-manifest.json"), observed["references"][0]["path"])
        self.assertEqual(["campaign_control"], observed["references"][0]["matched_control_roots"])

    def test_control_input_observer_resolves_quoted_shell_alias_with_spaces(self) -> None:
        campaign = self.root / "campaign-control"
        campaign.mkdir()
        alias = self.root / "unrelated alias"
        alias.symlink_to(campaign, target_is_directory=True)
        events = self.root / "control-space-alias-events.ndjson"
        events.write_text(
            json.dumps({
                "type": "tool_call",
                "toolCallId": "quoted-alias",
                "toolName": "run_terminal_cmd",
                "rawInput": {"command": f"cat '{alias / 'suite-manifest.json'}'"},
            }),
            encoding="utf-8",
        )

        observed = observe_control_input_references(events, {"campaign_control": campaign})

        self.assertTrue(observed["exposure_observed"])
        self.assertEqual(str(alias / "suite-manifest.json"), observed["references"][0]["path"])

    def test_control_input_observer_fails_closed_for_empty_or_malformed_stdout_capture(self) -> None:
        control = self.root / "campaign-control"
        control.mkdir()
        events = self.root / "control-malformed-events.ndjson"

        events.write_text("", encoding="utf-8")
        empty = observe_control_input_references(events, {"campaign_control": control})
        self.assertFalse(empty["observation_complete"])
        self.assertEqual("control-input-observation-incomplete", empty["status"])

        events.write_text(
            json.dumps({
                "received_at": "2026-09-17T00:00:00Z",
                "stream": "stdout",
                "line": "not a structured event",
            }),
            encoding="utf-8",
        )
        malformed = observe_control_input_references(events, {"campaign_control": control})
        self.assertFalse(malformed["observation_complete"])
        self.assertEqual([1], malformed["malformed_stdout_event_lines"])
        self.assertEqual("control-input-observation-incomplete", malformed["status"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
