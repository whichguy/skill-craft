"""Synthetic fail-closed controls for the offline native evidence auditor."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from urllib.parse import quote

import native_trace


class NativeTraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ask-agent-native-trace-")
        self.root = Path(self.temp.name)
        self.run = self.root / "run"
        self.operator = self.run / "operator"
        self.probes = self.operator / "probes"
        self.probes.mkdir(parents=True)
        self.caller = self.run / "caller"
        self.caller.mkdir()
        self.index_path = self.run / "primary" / ".git" / "worktrees" / "caller" / "index"
        self.index_path.parent.mkdir(parents=True)
        self.index_path.write_bytes(b"synthetic git index")
        self.session_root = self.root / "sessions"
        self.session_id = "00000000-0000-4000-8000-000000000001"
        self.session_dir = self.session_root / quote(str(self.caller.resolve()), safe="") / self.session_id
        self.session_dir.mkdir(parents=True)
        self.child_roots = [self.run / f"child-{i}" for i in range(1, 4)]
        for child in self.child_roots:
            child.mkdir()
        assignments = [
            {"worker_id": str(i), "path": f"src/step_{i}.py", "assignment": f"Implement only src/step_{i}.py."}
            for i in range(1, 4)
        ]
        baseline_paths = (
            ".gitignore", "added.txt", "checks.py", "dual.txt", "notes.txt", "pipeline.py",
            "src/__init__.py", "src/step_1.py", "src/step_2.py", "src/step_3.py",
            "tasks/in-progress/prompt-improvements-backlog.md", "unique-ahead-marker.txt",
        )
        self.baseline_files = {path: f"sha256:baseline-{index}" for index, path in enumerate(baseline_paths)}
        self.manifest = {
            "run_id": "run-1",
            "mode": "parallel",
            "workers": 3,
            "worker_ids": ["1", "2", "3"],
            "task_assignments": assignments,
            "paths": {"caller": str(self.caller.resolve())},
            "caller_snapshot": {"working_tree": {"files": dict(self.baseline_files)}},
        }
        self._write_json(self.run / "manifest.json", self.manifest)
        self.launch = {"session_id": self.session_id, "cwd": str(self.caller.resolve()), "started_epoch": 1000.0, "pid": 4321}
        self._write_json(self.operator / "launch.json", self.launch)
        self._write_json(self.operator / "verification.json", {"passed": True, "checks": {"all": True}})

        self.child_ids = [f"00000000-0000-4000-8000-{i:012d}" for i in range(2, 5)]
        self.calls: list[dict] = []
        self.updates: list[dict] = []
        self.observed: list[dict] = []
        next_epoch = 1001.0
        for i, (task, child, cwd) in enumerate(zip(assignments, self.child_ids, self.child_roots), 1):
            call_id = f"spawn-call-{i}"
            other_paths = [item["path"] for item in assignments if item["worker_id"] != str(i)]
            prompt = (
                f"Objective: Implement only {task['path']}. Other workers own {', '.join(other_paths)}.\n"
                f"Run python3 fixture.py probe --run /synthetic/run --worker {i} --phase start.\n"
                f"Run python3 fixture.py probe --run /synthetic/run --worker {i} --phase finish.\n"
            )
            self.calls.append(self._update("tool_call", {
                "toolCallId": call_id,
                "title": "spawn_subagent",
                "rawInput": {
                    "description": f"Worker {i} step transform",
                    "prompt": prompt,
                    "cwd": str(cwd.resolve()),
                    "background": True,
                },
            }))
            self.observed.append(self._observed_event(next_epoch, "tool_call", toolCallId=call_id,
                                                       toolName="spawn_subagent", rawInput={"cwd": str(cwd.resolve())}))
            next_epoch += 1.0
        self.updates.extend(self.calls)
        for i, child in enumerate(self.child_ids, 1):
            self.updates.append(self._update("subagent_spawned", {
                "subagent_id": child,
                "child_session_id": child,
                "parent_session_id": self.session_id,
                "effective_context_source": "new",
                "subagent_type": "general-purpose",
                "description": f"Worker {i} step transform",
            }))
        for i, child in enumerate(self.child_ids, 1):
            self.updates.append(self._update("tool_call_update", {
                "toolCallId": f"spawn-call-{i}", "status": "completed", "rawOutput": {"type": "Text", "text": "completed"},
            }))
            self.observed.append(self._observed_event(next_epoch, "tool_call_update", toolCallId=f"spawn-call-{i}",
                                                       status="completed", rawOutput={"type": "Text", "text": "completed"}))
            next_epoch += 1.0
        collect_id = "collect-call-1"
        self.updates.append(self._update("tool_call", {
            "toolCallId": collect_id, "title": "get_command_or_subagent_output",
            "rawInput": {"task_ids": list(self.child_ids), "timeout_ms": 1000},
        }))
        self.observed.append(self._observed_event(next_epoch, "tool_call", toolCallId=collect_id,
                                                   toolName="get_command_or_subagent_output"))
        next_epoch += 1.0
        for child in self.child_ids:
            self.updates.append(self._update("subagent_finished", {
                "subagent_id": child, "child_session_id": child, "status": "completed", "duration_ms": 40000,
            }))
        result_rows = [{"task_id": child, "status": "completed", "exit_code": 0} for child in self.child_ids]
        self.collection_update = self._update("tool_call_update", {
            "toolCallId": collect_id, "status": "completed",
            "rawOutput": {"type": "TaskOutput", "MultiResult": {"results": result_rows}},
        })
        self.updates.append(self.collection_update)
        self.observed.append(self._observed_event(next_epoch, "tool_call_update", toolCallId=collect_id,
                                                   status="completed", rawOutput={"type": "TaskOutput", "MultiResult": {"results": result_rows}}))
        next_epoch += 1.0
        self.observed.append(self._observed_event(next_epoch, "end", stopReason="end_turn"))
        self._write_updates()
        self._write_observed()
        self._write_json(self.operator / "process-result.json", {"exit_code": 0, "finished_epoch": next_epoch + 1.0})
        for i, (task, child, cwd) in enumerate(zip(assignments, self.child_ids, self.child_roots), 1):
            child_session_dir = self.session_root / quote(str(cwd.resolve()), safe="") / child
            child_session_dir.mkdir(parents=True)
            child_update = {"method": "session/update", "params": {"sessionId": child,
                            "update": {"sessionUpdate": "tool_call", "toolCallId": f"child-call-{i}",
                                       "title": "run_terminal_command", "rawInput": {"command": "true"}}}}
            child_session_dir.joinpath("updates.jsonl").write_text(json.dumps(child_update) + "\n", encoding="utf-8")
            after = f"sha256:child-{i}"
            start_at = i * 2 - 1
            hold_at = i * 2
            finish_at = 10 + i
            for phase in ("start", "finish"):
                working_files = dict(self.baseline_files)
                if phase == "finish":
                    working_files[task["path"]] = after
                record = {
                    "run_id": "run-1", "worker_id": str(i), "phase": phase,
                    "root": str(cwd.resolve()),
                    "recorded_at_utc": f"2026-10-08T12:00:{start_at if phase == 'start' else finish_at:02d}+00:00",
                    "hold_started_at_utc": f"2026-10-08T12:00:{hold_at:02d}+00:00",
                    "hold_finished_at_utc": f"2026-10-08T12:00:{hold_at + 1:02d}+00:00",
                    "working_tree": {"files": working_files},
                    "checks": {"snapshot_ok": True, "dirty_layers_preserved": True,
                               "owned_file_isolated": True, "probe_identity_valid": True},
                    "errors": [],
                }
                self._write_json(self.probes / f"worker-{i}-{phase}.json", record)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _update(self, kind: str, value: dict) -> dict:
        return {"method": "session/update", "params": {"sessionId": self.session_id,
                "update": {"sessionUpdate": kind, **value}}}

    def _observed_event(self, epoch: float, kind: str, **event_fields: object) -> dict:
        return {"observed_epoch": epoch, "elapsed_s": epoch - 1000.0,
                "event": {"type": kind, **event_fields}}

    def _write_json(self, path: Path, value: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def _write_updates(self) -> None:
        self.session_dir.joinpath("updates.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in self.updates), encoding="utf-8"
        )

    def _write_observed(self) -> None:
        self.operator.joinpath("observed.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in self.observed), encoding="utf-8"
        )

    def _audit(self) -> dict:
        return native_trace.audit_run(self.run, session_root=self.session_root)

    def _enable_packet_treatment(self, *, truncate_stdout: bool = False) -> list[dict]:
        if truncate_stdout:
            for call in self.calls:
                raw = call["params"]["update"]["rawInput"]
                raw["prompt"] += " " + ("packet-padding " * 450)
        fields = ("description", "prompt", "cwd", "background")
        packet = [{"worker_id": str(index),
                   "native_arguments": {field: call["params"]["update"]["rawInput"][field]
                                        for field in fields}}
                  for index, call in enumerate(self.calls, 1)]
        self._write_json(self.operator / "treatment.json", {"treatment": "packet"})
        self._write_json(self.operator / "dispatch-packet.json", packet)
        script = self.operator / "briefs.py"
        script.write_text("# synthetic packet generator identity\n", encoding="utf-8")
        stdout = json.dumps(packet, sort_keys=True, separators=(",", ":")) + "\n"
        stdout_bytes = stdout.encode("utf-8")
        command_id = "briefs-command"
        raw_output = {"type": "Bash", "exit_code": 0,
                      "output": list(stdout_bytes), "truncated": False,
                      "total_bytes": len(stdout_bytes)}
        if truncate_stdout:
            marker = b"\n\n... (output truncated) ...\n\n"
            preview_width = 10_000
            if len(stdout_bytes) <= preview_width * 2 + len(marker):
                raise AssertionError("synthetic packet stdout must exceed the retained host head/tail preview")
            output_file = self.session_dir.resolve() / "terminal" / f"{command_id}.log"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_bytes(stdout_bytes)
            self.packet_stdout_path = output_file
            preview = stdout_bytes[:preview_width] + marker + stdout_bytes[-preview_width:]
            raw_output.update({"output": list(preview), "truncated": True,
                               "output_file": str(output_file)})
        self.updates[0:0] = [
            self._update("tool_call", {
                "toolCallId": command_id,
                "title": "run_terminal_command",
                "rawInput": {"command": f"python3 {script.resolve()} --run {self.run.resolve()}"},
            }),
            self._update("tool_call_update", {
                "toolCallId": command_id,
                "status": "completed",
                "rawOutput": raw_output,
            }),
        ]
        self._write_updates()
        return packet

    def _spawn_raw_for_worker(self, worker_id: int) -> dict:
        expected_cwd = str(self.child_roots[worker_id - 1].resolve())
        row = next(row for row in self.updates
                   if row.get("params", {}).get("update", {}).get("title") == "spawn_subagent"
                   and row["params"]["update"].get("rawInput", {}).get("cwd") == expected_cwd)
        return row["params"]["update"]["rawInput"]

    def _packet_terminal_output(self) -> dict:
        row = next(row for row in self.updates
                   if row.get("params", {}).get("update", {}).get("sessionUpdate") == "tool_call_update"
                   and row["params"]["update"].get("toolCallId") == "briefs-command")
        return row["params"]["update"]["rawOutput"]

    def _make_sequential_control(self, *, mode: str = "sequential") -> None:
        self.manifest["mode"] = mode
        self._write_json(self.run / "manifest.json", self.manifest)
        result_rows = self.collection_update["params"]["update"]["rawOutput"]["MultiResult"]["results"]
        sequential_updates: list[dict] = []
        for index, child in enumerate(self.child_ids, 1):
            call_id = f"spawn-call-{index}"
            collect_id = f"sequential-collect-{index}"
            sequential_updates.extend([
                next(row for row in self.updates
                     if row.get("params", {}).get("update", {}).get("toolCallId") == call_id
                     and row["params"]["update"].get("sessionUpdate") == "tool_call"),
                next(row for row in self.updates
                     if row.get("params", {}).get("update", {}).get("sessionUpdate") == "subagent_spawned"
                     and row["params"]["update"].get("subagent_id") == child),
                next(row for row in self.updates
                     if row.get("params", {}).get("update", {}).get("toolCallId") == call_id
                     and row["params"]["update"].get("sessionUpdate") == "tool_call_update"),
                next(row for row in self.updates
                     if row.get("params", {}).get("update", {}).get("sessionUpdate") == "subagent_finished"
                     and row["params"]["update"].get("subagent_id") == child),
                self._update("tool_call", {
                    "toolCallId": collect_id,
                    "title": "get_command_or_subagent_output",
                    "rawInput": {"task_ids": [child], "timeout_ms": 1000},
                }),
                self._update("tool_call_update", {
                    "toolCallId": collect_id,
                    "status": "completed",
                    "rawOutput": {"type": "TaskOutput", "MultiResult": {"results": [result_rows[index - 1]]}},
                }),
            ])
        self.updates = sequential_updates
        self._write_updates()

    def _parent_calculation_command(self, extra_python: str = "") -> str:
        output_path = self.operator / "parent-expected.json"
        caller_source = self.caller / "src" / "step_1.py"
        body = f'''import hashlib, json
from pathlib import Path

inputs = [-1, 0, 2]
formulas = [{{"worker_id": "1", "path": "src/step_1.py", "formula": "2*x + 1"}}]
coeffs = [(2, 1)]

def step(value, a, b):
    return a * value + b

traces = []
outputs = []
for original in inputs:
    value = original
    stages = []
    for worker_id, (a, b) in enumerate(coeffs, start=1):
        value = step(value, a, b)
        stages.append({{"worker_id": str(worker_id), "output": value}})
    traces.append({{"input": original, "stages": stages, "output": value}})
    outputs.append(value)

payload = {{"inputs": inputs, "formulas": formulas, "expected_outputs": outputs, "traces": traces}}
out = Path({json.dumps(str(output_path))})
index = Path({json.dumps(str(self.index_path))})
{extra_python}out.write_text(json.dumps(payload, indent=2) + "\\n")
print("INDEX_SHA256", hashlib.sha256(index.read_bytes()).hexdigest())
print(out.read_text())'''
        return ("python3 - << 'PY'\n" + body + "\nPY\n"
                f"git -C {json.dumps(str(self.caller.resolve()))} rev-parse HEAD\n"
                f"git -C {json.dumps(str(self.caller.resolve()))} status --porcelain=v1")

    def _insert_parent_command(self, command: str) -> None:
        call_id = "parent-calculation-call"
        row = self._update("tool_call", {
            "toolCallId": call_id,
            "title": "run_terminal_command",
            "rawInput": {"command": command},
        })
        index = next(i for i, item in enumerate(self.updates)
                     if item.get("params", {}).get("update", {}).get("title") == "get_command_or_subagent_output")
        self.updates.insert(index, row)
        self._write_updates()

    def test_exact_native_background_run_passes(self) -> None:
        report = self._audit()
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["passed"])
        self.assertEqual(report["native_status"], "PASS")
        self.assertEqual(report["auditor_implementation"]["sha256"],
                         hashlib.sha256(Path(native_trace.__file__).resolve().read_bytes()).hexdigest())
        self.assertEqual(report["metrics"]["launch_spread_s"], 2.0)
        self.assertTrue(all(row["duration_ms"] == 40000 for row in report["metrics"]["native_child_spans"].values()))
        self.assertEqual(report["metrics"]["child_probe_overlap"]["status"], "NOT_OBSERVED")
        self.assertEqual(report["metrics"]["child_task_work_overlap"]["status"], "OBSERVED")
        self.assertIn("not CPU concurrency", report["metrics"]["child_task_work_overlap"]["detail"])
        self.assertEqual(report["checks"]["child_transcript_retention"]["status"], "PASS")

    def test_typed_sequential_dispatch_passes(self) -> None:
        self._make_sequential_control()

        report = self._audit()

        self.assertEqual(report["checks"]["dispatch_mode"]["status"], "PASS")
        self.assertEqual(report["checks"]["sequential_dispatch_order"]["status"], "PASS")
        self.assertEqual(report["status"], "PASS")

    def test_sequential_dispatch_requires_terminal_collection_before_next_spawn(self) -> None:
        self._make_sequential_control()
        terminal = next(row for row in self.updates
                        if row.get("params", {}).get("update", {}).get("toolCallId") == "sequential-collect-1"
                        and row["params"]["update"].get("sessionUpdate") == "tool_call_update")
        self.updates.remove(terminal)
        second_spawn = next(index for index, row in enumerate(self.updates)
                            if row.get("params", {}).get("update", {}).get("toolCallId") == "spawn-call-2"
                            and row["params"]["update"].get("sessionUpdate") == "tool_call")
        self.updates.insert(second_spawn + 1, terminal)
        self._write_updates()

        report = self._audit()

        self.assertEqual(report["checks"]["sequential_dispatch_order"]["status"], "FAIL")
        self.assertNotEqual(report["status"], "PASS")

    def test_parallel_gate_rejects_sequential_control_order(self) -> None:
        self._make_sequential_control(mode="parallel")

        report = self._audit()

        self.assertEqual(report["checks"]["parallel_dispatch_order"]["status"], "FAIL")
        self.assertNotEqual(report["status"], "PASS")

    def test_unknown_manifest_dispatch_mode_cannot_pass(self) -> None:
        self.manifest["mode"] = "serialized-ish"
        self._write_json(self.run / "manifest.json", self.manifest)

        report = self._audit()

        self.assertEqual(report["checks"]["dispatch_mode"]["status"], "FAIL")
        self.assertNotEqual(report["status"], "PASS")

    def test_assignment_binding_ignores_descriptive_label_format(self) -> None:
        description = "Worker 1 step_1 transform"
        self.updates[0]["params"]["update"]["rawInput"]["description"] = description
        self.updates[3]["params"]["update"]["description"] = description
        self._write_updates()

        report = self._audit()

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["checks"]["spawn_argument_bindings"]["status"], "PASS")

    def test_contextual_mentions_of_other_owned_paths_keep_probe_root_binding(self) -> None:
        self._write_updates()

        report = self._audit()

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["checks"]["spawn_argument_bindings"]["status"], "PASS")

    def test_packet_treatment_requires_exact_native_arguments(self) -> None:
        self._enable_packet_treatment()
        self._spawn_raw_for_worker(1)["subagent_type"] = "general-purpose"
        self._write_updates()

        report = self._audit()

        check = report["checks"]["packet_spawn_arguments"]
        self.assertEqual(check["status"], "PASS")
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["evidence"]["dispatch_packet"]["sha256_at_audit"],
                         hashlib.sha256((self.operator / "dispatch-packet.json").read_bytes()).hexdigest())
        self.assertTrue(all(set(item["field_matches"].values()) == {True}
                            for item in check["worker_matches"]))

    def test_packet_generation_excludes_parent_oracle_invocation(self) -> None:
        self._enable_packet_treatment()
        command_id = "parent-oracle-call"
        command = (f"python3 {self.operator / 'briefs.py'} --run {self.run} --parent-oracle")
        call = self._update("tool_call", {
            "toolCallId": command_id,
            "title": "run_terminal_command",
            "rawInput": {"command": command},
        })
        result = self._update("tool_call_update", {
            "toolCallId": command_id,
            "status": "completed",
            "rawOutput": {"type": "Bash", "exit_code": 0, "output": "oracle result", "truncated": False},
        })
        collect_index = next(index for index, row in enumerate(self.updates)
                             if row.get("params", {}).get("update", {}).get("title")
                             == "get_command_or_subagent_output")
        self.updates[collect_index:collect_index] = [call, result]
        self._write_updates()

        report = self._audit()

        self.assertEqual(report["checks"]["packet_spawn_arguments"]["status"], "PASS")
        self.assertEqual(report["status"], "PASS")

    def test_inline_v3_and_labeled_v4_probe_commands_bind(self) -> None:
        v3_prompt = (
            "Check context `python3 fixture.py check-context --run /synthetic/run`; "
            "start probe `python3 fixture.py probe --run /synthetic/run --worker 1 --phase start`; "
            "check source state `python3 fixture.py check-index`; "
            "finish probe `python3 fixture.py probe --run /synthetic/run --worker 1 --phase finish`; "
            "inspect caller tree."
        )
        v4_prompt = (
            "Start probe: `python3 worker_phase.py --run /synthetic/run --worker 1 --phase start`\n"
            "Finish probe: `python3 worker_phase.py --run /synthetic/run --worker 1 --phase finish`\n"
        )

        self.assertEqual(native_trace._explicit_probe_workers(v3_prompt),
                         ({"start": "1", "finish": "1"}, None, False))
        self.assertEqual(native_trace._explicit_probe_workers(v4_prompt),
                         ({"start": "1", "finish": "1"}, None, False))

    def test_inline_duplicate_probe_phase_fails_binding(self) -> None:
        raw = self.updates[0]["params"]["update"]["rawInput"]
        raw["prompt"] = (
            "Implement only src/step_1.py. "
            "Start probe `python3 fixture.py probe --run /synthetic/run --worker 1 --phase start`; "
            "check state; "
            "finish probe `python3 fixture.py probe --run /synthetic/run --worker 1 --phase finish`; "
            "inspect result; "
            "repeat start `python3 fixture.py probe --run /synthetic/run --worker 1 --phase start`."
        )
        self._write_updates()

        report = self._audit()

        self.assertEqual(report["checks"]["spawn_argument_bindings"]["status"], "FAIL")
        self.assertNotEqual(report["status"], "PASS")

    def test_truncated_packet_stdout_is_session_bound_and_retained(self) -> None:
        self._enable_packet_treatment(truncate_stdout=True)

        report = self._audit()

        check = report["checks"]["packet_spawn_arguments"]
        retained = self.operator / "native-evidence" / "dispatch-packet-stdout.log"
        self.assertEqual(check["status"], "PASS")
        self.assertTrue(retained.is_file())
        self.assertEqual(retained.read_bytes(), self.packet_stdout_path.read_bytes())
        self.assertEqual(report["evidence"]["dispatch_packet"]["script_stdout_retention"]["retained_sha256"],
                         hashlib.sha256(retained.read_bytes()).hexdigest())
        self.assertEqual(check["script_stdout_bytes"], len(retained.read_bytes()))

    def test_truncated_packet_stdout_rejects_tampered_tail_preview(self) -> None:
        self._enable_packet_treatment(truncate_stdout=True)
        output = self._packet_terminal_output()
        preview = output["output"]
        preview[-1] ^= 1
        self._write_updates()

        report = self._audit()

        self.assertEqual(report["checks"]["packet_spawn_arguments"]["status"], "FAIL")
        self.assertNotEqual(report["status"], "PASS")

    def test_truncated_packet_stdout_unknown_preview_schema_is_not_pass(self) -> None:
        self._enable_packet_treatment(truncate_stdout=True)
        output = self._packet_terminal_output()
        output["output"] = output["output"][:10_000]
        self._write_updates()

        report = self._audit()

        self.assertEqual(report["checks"]["packet_spawn_arguments"]["status"], "UNKNOWN")
        self.assertNotEqual(report["status"], "PASS")

    def test_truncated_packet_stdout_rejects_unbound_or_wrong_size_file(self) -> None:
        for mutation, expected_status in (
            ("missing-output-file", "FAIL"),
            ("missing-file", "INCOMPLETE"),
            ("wrong-session", "FAIL"),
            ("wrong-size", "FAIL"),
        ):
            with self.subTest(mutation=mutation):
                case = NativeTraceTests()
                case.setUp()
                try:
                    case._enable_packet_treatment(truncate_stdout=True)
                    output = case._packet_terminal_output()
                    if mutation == "missing-output-file":
                        del output["output_file"]
                    elif mutation == "missing-file":
                        case.packet_stdout_path.unlink()
                    elif mutation == "wrong-session":
                        output["output_file"] = str(
                            case.packet_stdout_path.parent.parent / "other-session" / "terminal" /
                            case.packet_stdout_path.name
                        )
                    else:
                        output["total_bytes"] += 1
                    case._write_updates()

                    report = case._audit()

                    self.assertEqual(report["checks"]["packet_spawn_arguments"]["status"], expected_status)
                    self.assertNotEqual(report["status"], "PASS")
                finally:
                    case.tearDown()

    def test_changed_truncated_stdout_cannot_replace_retained_copy(self) -> None:
        self._enable_packet_treatment(truncate_stdout=True)
        first = self._audit()
        self.assertEqual(first["checks"]["packet_spawn_arguments"]["status"], "PASS")
        retained = self.operator / "native-evidence" / "dispatch-packet-stdout.log"
        retained_before = retained.read_bytes()
        source_before = self.packet_stdout_path.read_bytes()
        self.packet_stdout_path.write_bytes(source_before[:-1] + bytes([source_before[-1] ^ 1]))

        second = self._audit()

        check = second["checks"]["packet_spawn_arguments"]
        self.assertEqual(check["status"], "FAIL")
        self.assertEqual(retained.read_bytes(), retained_before)
        self.assertNotEqual(check["source_sha256"], check["retained_sha256"])

    def test_packet_treatment_rejects_any_changed_spawn_field(self) -> None:
        for field in ("prompt", "cwd", "description", "background"):
            with self.subTest(field=field):
                case = NativeTraceTests()
                case.setUp()
                try:
                    case._enable_packet_treatment()
                    raw = case._spawn_raw_for_worker(1)
                    if field in {"prompt", "description"}:
                        raw[field] += " changed"
                    elif field == "cwd":
                        raw[field] = str(case.child_roots[1].resolve())
                    else:
                        raw[field] = False
                    case._write_updates()

                    report = case._audit()

                    self.assertEqual(report["checks"]["packet_spawn_arguments"]["status"], "FAIL")
                    self.assertNotEqual(report["status"], "PASS")
                finally:
                    case.tearDown()

    def test_packet_treatment_missing_packet_is_incomplete(self) -> None:
        self._enable_packet_treatment()
        (self.operator / "dispatch-packet.json").unlink()

        report = self._audit()

        self.assertEqual(report["checks"]["packet_spawn_arguments"]["status"], "INCOMPLETE")
        self.assertNotEqual(report["status"], "PASS")

    def test_packet_file_cannot_be_changed_to_match_spawn_after_script_result(self) -> None:
        packet = self._enable_packet_treatment()
        packet[0]["native_arguments"]["description"] += " changed"
        self._write_json(self.operator / "dispatch-packet.json", packet)
        self._spawn_raw_for_worker(1)["description"] = packet[0]["native_arguments"]["description"]
        child_id = self.child_ids[0]
        receipt = next(row["params"]["update"] for row in self.updates
                       if row.get("params", {}).get("update", {}).get("sessionUpdate") == "subagent_spawned"
                       and row["params"]["update"].get("subagent_id") == child_id)
        receipt["description"] = packet[0]["native_arguments"]["description"]
        self._write_updates()

        report = self._audit()

        check = report["checks"]["packet_spawn_arguments"]
        self.assertEqual(check["status"], "FAIL")
        self.assertIn("stdout differs from dispatch-packet.json", check["detail"])
        self.assertNotEqual(report["status"], "PASS")

    def test_bounded_parent_calculation_with_source_metadata_is_allowed(self) -> None:
        self._insert_parent_command(self._parent_calculation_command())

        report = self._audit()

        self.assertEqual(report["checks"]["parent_independent_source_work"]["status"], "PASS")

    def test_parent_calculation_source_write_is_not_waived(self) -> None:
        source = json.dumps(str(self.caller / "src" / "step_1.py"))
        command = self._parent_calculation_command(
            f"Path({source}).write_text('changed')\n"
        )
        self._insert_parent_command(command)

        report = self._audit()

        self.assertEqual(report["checks"]["parent_independent_source_work"]["status"], "UNKNOWN")

    def test_parent_calculation_output_reassignment_is_not_waived(self) -> None:
        source = json.dumps(str(self.caller / "src" / "step_1.py"))
        command = self._parent_calculation_command(
            f"out = Path({source})\nout.write_text('changed')\n"
        )
        self._insert_parent_command(command)

        report = self._audit()

        self.assertEqual(report["checks"]["parent_independent_source_work"]["status"], "UNKNOWN")

    def test_parent_calculation_rejects_dynamic_calls_and_callbacks(self) -> None:
        for injected in (
            'getattr(index, "read_bytes")()\n',
            'eval("1 + 1")\n',
            'exec("pass")\n',
            '__import__("os")\n',
            'map(print, inputs)\n',
        ):
            with self.subTest(injected=injected):
                command = self._parent_calculation_command(injected)
                self.assertFalse(native_trace._safe_parent_calculation(
                    command, self.run.resolve(), self.caller.resolve()
                ))

    def test_explicit_probe_worker_disagreement_fails_binding(self) -> None:
        prompt = self.updates[0]["params"]["update"]["rawInput"]["prompt"]
        self.updates[0]["params"]["update"]["rawInput"]["prompt"] = prompt.replace(
            "--worker 1 --phase start", "--worker 2 --phase start"
        )
        self._write_updates()

        report = self._audit()

        self.assertEqual(report["checks"]["spawn_argument_bindings"]["status"], "FAIL")
        self.assertFalse(report["passed"])

    def test_reaudit_uses_retained_root_and_child_logs(self) -> None:
        first = self._audit()
        self.assertTrue(first["passed"])
        root_copy = self.operator / "native-evidence" / "root-updates.jsonl"
        self.assertTrue(root_copy.is_file())
        for child, cwd in zip(self.child_ids, self.child_roots):
            (self.session_root / quote(str(cwd.resolve()), safe="") / child / "updates.jsonl").unlink()
        self.session_dir.joinpath("updates.jsonl").unlink()

        second = self._audit()

        self.assertEqual(second["status"], "PASS")
        self.assertEqual(Path(second["evidence"]["root_updates"]["path"]), root_copy.resolve())
        self.assertEqual(second["checks"]["child_transcript_retention"]["status"], "PASS")
        self.assertTrue(all(Path(row["retained"]["path"]).is_file()
                            for row in second["evidence"]["native_evidence_retention"]["children"].values()))

    def test_changed_external_transcripts_do_not_replace_retained_evidence(self) -> None:
        first = self._audit()
        self.assertTrue(first["passed"])
        root_copy = self.operator / "native-evidence" / "root-updates.jsonl"
        root_before = root_copy.read_bytes()
        root_source = self.session_dir / "updates.jsonl"
        root_source.write_bytes(root_source.read_bytes() + b"\n")
        child_sources = []
        child_copies = []
        for child, cwd in zip(self.child_ids, self.child_roots):
            source = self.session_root / quote(str(cwd.resolve()), safe="") / child / "updates.jsonl"
            retained = self.operator / "native-evidence" / "children" / child / "updates.jsonl"
            before = retained.read_bytes()
            source.write_bytes(source.read_bytes() + b"\n")
            child_sources.append((source, retained, before))
            child_copies.append(retained)

        second = self._audit()

        self.assertNotEqual(second["status"], "PASS")
        self.assertEqual(second["checks"]["root_transcript_retention_integrity"]["status"], "FAIL")
        root_check = second["checks"]["root_transcript_retention_integrity"]
        self.assertNotEqual(root_check["source_sha256"], root_check["retained_sha256"])
        self.assertEqual(root_copy.read_bytes(), root_before)
        child_check = second["checks"]["child_transcript_retention"]
        self.assertEqual(child_check["status"], "FAIL")
        self.assertEqual(len(child_check["conflicts"]), len(child_sources))
        for (source, retained, before), conflict in zip(child_sources, child_check["conflicts"]):
            self.assertEqual(retained.read_bytes(), before)
            self.assertEqual(conflict["source_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(conflict["retained_sha256"], hashlib.sha256(before).hexdigest())

    def test_wrong_parent_binding_fails(self) -> None:
        self.updates[3]["params"]["update"]["parent_session_id"] = "other-parent"
        self._write_updates()
        report = self._audit()
        self.assertEqual(report["checks"]["parent_child_identity"]["status"], "FAIL")
        self.assertFalse(report["passed"])

    def test_missing_parent_binding_fails(self) -> None:
        del self.updates[3]["params"]["update"]["parent_session_id"]
        self._write_updates()
        report = self._audit()
        self.assertEqual(report["checks"]["parent_child_identity"]["status"], "FAIL")
        self.assertFalse(report["passed"])

    def test_resumed_context_fails(self) -> None:
        self.updates[3]["params"]["update"]["effective_context_source"] = "resumed"
        self._write_updates()
        report = self._audit()
        self.assertEqual(report["checks"]["fresh_context"]["status"], "FAIL")
        self.assertFalse(report["passed"])

    def test_duplicate_spawn_cwd_fails_probe_binding(self) -> None:
        self.updates[1]["params"]["update"]["rawInput"]["cwd"] = str(self.child_roots[0].resolve())
        self._write_updates()
        report = self._audit()
        self.assertEqual(report["checks"]["cwd_probe_binding"]["status"], "FAIL")
        self.assertFalse(report["passed"])

    def test_missing_collection_does_not_pass_zero_exit(self) -> None:
        self.collection_update["params"]["update"]["rawOutput"]["MultiResult"]["results"].pop()
        self._write_updates()
        report = self._audit()
        self.assertEqual(report["checks"]["parent_collected_all_children"]["status"], "FAIL")
        self.assertFalse(report["passed"])

    def test_zero_exit_without_typed_parent_end_is_false_success(self) -> None:
        self.observed = [row for row in self.observed if row["event"].get("type") != "end"]
        self._write_observed()
        report = self._audit()
        self.assertEqual(report["checks"]["parent_terminal"]["status"], "FAIL")
        self.assertFalse(report["passed"])

    def test_child_narrative_is_not_copied_into_evidence(self) -> None:
        rows = self.collection_update["params"]["update"]["rawOutput"]["MultiResult"]["results"]
        rows[0]["output"] = "unverified generated claim"
        self._write_updates()
        report = self._audit()
        returned = report["evidence"]["child_returns"][self.child_ids[0]][0]
        self.assertNotIn("output", returned)
        self.assertNotIn("unverified generated claim", json.dumps(report))

    def test_recovered_filesystem_state_stays_separate_from_native_pass(self) -> None:
        self._write_json(self.operator / "verification-before-plugin-relocate.json",
                         {"passed": False, "checks": {"worker_snapshots_clean_and_exact_dirty_layers": False}})
        self._write_json(self.operator / "verification.json", {"passed": True, "checks": {"all": True}})
        report = self._audit()
        self.assertEqual(report["status"], "RECOVERED")
        self.assertFalse(report["passed"])
        self.assertEqual(report["native_status"], "PASS")
        self.assertEqual(report["filesystem_result_context"]["status"], "RECOVERED")
        self.assertEqual(report["combined_classification"], "RECOVERED")

    def test_post_exit_filesystem_failure_overrides_earlier_recovery(self) -> None:
        self._write_json(self.operator / "verification-before-plugin-relocate.json",
                         {"passed": False, "checks": {"before": False}})
        self._write_json(self.operator / "parent-verification.json", {"passed": True, "checks": {"parent": True}})
        self._write_json(self.operator / "verification.json", {"passed": False, "checks": {"current": False}})
        self._write_json(self.operator / "post-exit-verification.json",
                         {"passed": False, "checks": {"after_exit": False}})

        report = self._audit()

        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["passed"])
        self.assertEqual(report["native_status"], "PASS")
        self.assertEqual(report["filesystem_result_context"]["status"], "FAIL")
        self.assertEqual(report["filesystem_result_context"]["current_precedence"]["source"], "post_exit")
        self.assertEqual(report["combined_classification"], "FAIL")


if __name__ == "__main__":
    unittest.main()
