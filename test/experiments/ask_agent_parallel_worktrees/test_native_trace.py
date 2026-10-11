"""Synthetic fail-closed controls for the offline native evidence auditor."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
import shlex
import sys
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

    def _write_parent_result_case(self) -> tuple[dict, list[dict], list[dict], dict[str, Path]]:
        operator = self.run / "operator"
        binding_dir = operator / "compact-bindings"
        binding_dir.mkdir(exist_ok=True)
        setup_workers = []
        indexed_rows = []
        paths: dict[str, Path] = {}
        archive_report = {
            "run_id": self.manifest["run_id"], "passed": True,
            "checks": {"fixture": True}, "errors": [],
        }
        archive_bytes = (json.dumps(archive_report, sort_keys=True) + "\n").encode("utf-8")
        (operator / "verification.json").write_bytes(archive_bytes)
        (operator / "parent-verification.json").write_bytes(archive_bytes)
        integration_path = operator / "integration-result.json"
        integration = {
            "run_id": self.manifest["run_id"], "status": "INTEGRATED",
            "delivery_mode": "patch", "fixture_verification": {"passed": True},
            "applied_worker_ids": ["1", "2", "3"],
        }
        self._write_json(integration_path, integration)

        for index, task in enumerate(self.manifest["task_assignments"], 1):
            worker_id = str(task["worker_id"])
            binding_path = binding_dir / f"worker-{worker_id}.json"
            binding_content = {"worker_id": worker_id, "task_path": task["path"]}
            canonical = hashlib.sha256(json.dumps(
                binding_content, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            ).encode("utf-8")).hexdigest()
            binding_content["binding_sha256"] = canonical
            binding_bytes = (json.dumps(binding_content, sort_keys=True) + "\n").encode("utf-8")
            binding_path.write_bytes(binding_bytes)
            packet_sha = hashlib.sha256(binding_bytes).hexdigest()
            setup_workers.append({
                "worker_id": worker_id, "worktree": str(self.child_roots[index - 1].resolve()),
                "compact_binding_path": str(binding_path.resolve()),
                "compact_binding_sha256": canonical, "compact_packet_sha256": packet_sha,
            })

            record_refs = {}
            for phase in ("start", "finish"):
                phase_path = operator / "worker-phases" / f"worker-{worker_id}-{phase}" / "attempt.json"
                self._write_json(phase_path, {
                    "run_id": self.manifest["run_id"], "worker_id": worker_id,
                    "phase": phase, "status": "PASSED", "compact_binding_sha256": canonical,
                })
                record_refs[phase] = {"path": str(phase_path.resolve()),
                                      "sha256": hashlib.sha256(phase_path.read_bytes()).hexdigest()}
            return_path = operator / "compact-returns" / f"worker-{worker_id}.json"
            self._write_json(return_path, {
                "run_id": self.manifest["run_id"], "worker_id": worker_id,
                "phase": "verify-return", "status": "PASSED", "binding_sha256": canonical,
            })
            record_refs["verify_return"] = {"path": str(return_path.resolve()),
                                             "sha256": hashlib.sha256(return_path.read_bytes()).hexdigest()}
            indexed_rows.append({
                "worker_id": worker_id, "status": "PARENT_ASSERTED",
                "native_handle": self.child_ids[index - 1], "native_lifecycle": "parent_asserted",
                "binding_sha256": canonical, "packet_sha256": packet_sha,
                "records": record_refs,
            })
            paths[f"worker-{worker_id}-start"] = operator / "worker-phases" / f"worker-{worker_id}-start" / "attempt.json"
            paths[f"worker-{worker_id}-finish"] = operator / "worker-phases" / f"worker-{worker_id}-finish" / "attempt.json"
            paths[f"worker-{worker_id}-return"] = return_path

        self._write_json(operator / "setup-result.json", {
            "status": "PREPARED", "treatment": "compact",
            "compact_startup_contract": "action-packet/v1", "workers": setup_workers,
        })
        index = {
            "schema": "ask-agent.parent-result-index/v1", "run_id": self.manifest["run_id"],
            "status": "PARENT_ASSERTED", "native_lifecycle": "parent_asserted",
            "verification": {
                "source_path": str((operator / "verification.json").resolve()),
                "source_sha256": hashlib.sha256(archive_bytes).hexdigest(),
                "archive_path": str((operator / "parent-verification.json").resolve()),
                "archive_sha256": hashlib.sha256(archive_bytes).hexdigest(),
            },
            "integration": {"path": str(integration_path.resolve()),
                            "sha256": hashlib.sha256(integration_path.read_bytes()).hexdigest()},
            "workers": indexed_rows,
        }
        self._write_json(operator / "parent-result.json", index)
        launches = [
            {"worker_id": str(i), "child_session_id": self.child_ids[i - 1]}
            for i in range(1, 4)
        ]
        return index, self.manifest["task_assignments"], launches, paths

    def test_compact_parent_result_requires_controller_archive_and_typed_handles(self) -> None:
        index, assignments, launches, paths = self._write_parent_result_case()
        archive = self.operator / "parent-verification.json"
        archive_bytes = archive.read_bytes()
        archive.unlink()
        before_controller = native_trace._compact_parent_result_check(
            self.run, self.manifest, assignments, launches, delivery_mode="patch",
        )
        self.assertEqual(before_controller["status"], "INCOMPLETE")
        archive.write_bytes(archive_bytes)

        passed = native_trace._compact_parent_result_check(
            self.run, self.manifest, assignments, launches, delivery_mode="patch",
        )
        self.assertEqual(passed["status"], "PASS", passed["detail"])

        altered = json.loads(json.dumps(index))
        altered["workers"][0]["native_handle"] = "foreign-native-handle"
        self._write_json(self.operator / "parent-result.json", altered)
        wrong_handle = native_trace._compact_parent_result_check(
            self.run, self.manifest, assignments, launches, delivery_mode="patch",
        )
        self.assertEqual(wrong_handle["status"], "FAIL")
        self.assertIn("typed native spawn evidence", wrong_handle["detail"])
        self._write_json(self.operator / "parent-result.json", index)

        for invalid_worker_id in ({"nested": "1"}, ["1"]):
            altered = json.loads(json.dumps(index))
            altered["workers"][0]["worker_id"] = invalid_worker_id
            self._write_json(self.operator / "parent-result.json", altered)
            malformed_id = native_trace._compact_parent_result_check(
                self.run, self.manifest, assignments, launches, delivery_mode="patch",
            )
            self.assertEqual(malformed_id["status"], "FAIL")
            self.assertIn("worker ID", malformed_id["detail"])
        self._write_json(self.operator / "parent-result.json", index)

        duplicate_launches = json.loads(json.dumps(launches))
        duplicate_launches[1]["child_session_id"] = duplicate_launches[0]["child_session_id"]
        duplicate_native = native_trace._compact_parent_result_check(
            self.run, self.manifest, assignments, duplicate_launches, delivery_mode="patch",
        )
        self.assertEqual(duplicate_native["status"], "FAIL")
        self.assertIn("typed native spawn evidence", duplicate_native["detail"])

        indexed_start = paths["worker-1-start"]
        with indexed_start.open("a", encoding="utf-8") as stream:
            stream.write("tampered\n")
        replaced_record = native_trace._compact_parent_result_check(
            self.run, self.manifest, assignments, launches, delivery_mode="patch",
        )
        self.assertEqual(replaced_record["status"], "FAIL")
        self.assertIn("hash differs", replaced_record["detail"])

    def test_compact_v4_setup_marker_requires_matching_treatment_metadata(self) -> None:
        legacy = self._audit()
        self.assertEqual(legacy["native_status"], "PASS")
        self.assertNotIn("compact_v4_treatment_metadata", legacy["checks"])

        legacy_treatment = {
            "treatment": "compact", "version": 3, "verification_output": "summary-v1",
            "delivery_mode": "patch", "workers": 3, "mode": "parallel",
        }
        self._write_json(self.operator / "parent-result.json", {
            "run_id": self.manifest["run_id"], "status": "PARENT_ASSERTED",
        })
        self.assertIsNone(native_trace._compact_v4_treatment_metadata_check(
            self.run, self.manifest, legacy_treatment,
        ), "unversioned historical parent results must not be promoted to the v4 gate")
        self._write_json(self.operator / "parent-result.json", {
            "schema": "ask-agent.parent-result-index/v1",
        })
        new_index_without_treatment = native_trace._compact_v4_treatment_metadata_check(
            self.run, self.manifest, None,
        )
        self.assertEqual(new_index_without_treatment["status"], "FAIL")
        (self.operator / "parent-result.json").unlink()

        self._write_json(self.operator / "setup-result.json", {
            "compact_startup_contract": "action-packet/v1",
        })
        missing = self._audit()
        self.assertEqual(missing["checks"]["compact_v4_treatment_metadata"]["status"], "FAIL")
        self.assertEqual(missing["checks"]["compact_parent_result"]["status"], "FAIL")

        self._write_json(self.operator / "treatment.json", {
            "treatment": "compact", "version": 4, "verification_output": "summary-v1",
            "delivery_mode": "wrong", "workers": 3, "mode": "parallel",
        })
        mismatched = self._audit()
        self.assertEqual(mismatched["checks"]["compact_v4_treatment_metadata"]["status"], "FAIL")
        self.assertIn("matching compact/version/output/delivery metadata",
                      mismatched["checks"]["compact_v4_treatment_metadata"]["detail"])

    def _enable_verification_summary(
        self, *, treatment: dict | None = None, report: dict | None = None,
        stdout: str | None = None, truncated: bool = False, exit_code: int = 0,
    ) -> tuple[dict, dict]:
        treatment = treatment or {
            "treatment": "baseline", "version": 5, "verification_output": "summary-v1",
        }
        self._write_json(self.operator / "treatment.json", treatment)
        self.manifest.setdefault("paths", {})["verification"] = str(
            (self.operator / "verification.json").resolve()
        )
        self._write_json(self.run / "manifest.json", self.manifest)
        script = self.operator / "fixture.py"
        script.write_text("# frozen synthetic fixture verifier\n", encoding="utf-8")
        self.launch["apparatus_sha256"] = {
            "fixture.py": hashlib.sha256(script.read_bytes()).hexdigest(),
        }
        self._write_json(self.operator / "launch.json", self.launch)

        if report is None:
            report = {
                "schema_version": 1,
                "run_id": self.manifest["run_id"],
                "run_path": str(self.run.resolve()),
                "passed": True,
                "checks": {"parent_preserved": True, "pipeline_oracle": True},
                "errors": [],
            }
        report_bytes = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
        saved_report = self.operator / "parent-verification.json"
        saved_report.write_bytes(report_bytes)
        # Model controller.verify_after_exit replacing verification.json after it
        # has retained the parent's exact report bytes.
        self._write_json(self.operator / "verification.json", {
            "schema_version": 1, "run_id": self.manifest["run_id"],
            "run_path": str(self.run.resolve()), "passed": False,
            "checks": {"post_exit_only": False}, "errors": ["fresh post-exit report"],
        })
        self._write_json(self.operator / "post-exit-verification.json", {
            "schema_version": 1, "run_id": self.manifest["run_id"],
            "run_path": str(self.run.resolve()), "passed": True,
            "checks": {"post_exit_only": True}, "errors": [],
        })
        self._write_json(self.operator / "post-exit-result.json", {"status": "PASS", "passed": True})

        checks = report.get("checks", {})
        errors = report.get("errors", [])
        failed_checks = sorted(name for name, value in checks.items() if value is not True)
        summary = {
            "schema": "ask-agent-fixture-verification-summary/v1",
            "run_id": self.manifest["run_id"],
            "passed": not errors and not failed_checks,
            "errors": errors,
            "check_count": len(checks),
            "failed_checks": failed_checks,
            "report_path": str((self.operator / "verification.json").resolve()),
            "report_bytes": len(report_bytes),
            "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
        }
        stdout = stdout if stdout is not None else json.dumps(summary, sort_keys=True, separators=(",", ":"))
        call_id = f"fixture-summary-call-{len(self.updates)}"
        command = shlex.join([
            "python3", "-B", str(script.resolve()), "verify", "--run",
            str(self.run.resolve()), "--summary",
        ])
        self.updates.extend([
            self._update("tool_call", {
                "toolCallId": call_id, "title": "run_terminal_command",
                "rawInput": {"command": command},
            }),
            self._update("tool_call_update", {
                "toolCallId": call_id, "status": "completed",
                "rawOutput": {"type": "Bash", "exit_code": exit_code,
                              "output": stdout, "truncated": truncated},
            }),
        ])
        self._write_updates()
        return summary, report

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

    def test_parent_fixture_summary_matches_archived_complete_report(self) -> None:
        summary, _ = self._enable_verification_summary()

        report = self._audit()

        check = report["checks"]["fixture_verification_summary"]
        self.assertEqual(check["status"], "PASS")
        self.assertEqual(check["complete_output_proof"], "ESTABLISHED")
        self.assertEqual(check["summary"], summary)
        self.assertEqual(check["saved_report_path"], str((self.operator / "parent-verification.json").resolve()))
        self.assertEqual(check["report_sha256"], hashlib.sha256(
            (self.operator / "parent-verification.json").read_bytes()
        ).hexdigest())
        self.assertNotEqual(check["report_sha256"], hashlib.sha256(
            (self.operator / "verification.json").read_bytes()
        ).hexdigest())
        self.assertEqual(len(check["invocations"]), 1)
        self.assertIsNotNone(check["invocations"][0]["call_line"])
        self.assertIsNotNone(check["invocations"][0]["result_line"])
        self.assertEqual(report["native_status"], "PASS")
        self.assertEqual(report["filesystem_result_context"]["status"], "RECOVERED")
        self.assertEqual(report["status"], "RECOVERED")

    def test_compact_cli_result_requires_one_unique_terminal_result(self) -> None:
        call_id = "summary-call"
        terminal = {"line": 12, "update": {
            "sessionUpdate": "tool_call_update", "toolCallId": call_id,
            "status": "completed", "rawOutput": {
                "type": "Bash", "exit_code": 0, "output": "{}", "truncated": False,
            },
        }}
        value, line, error = native_trace._compact_cli_result(
            {"row": {"update": {"toolCallId": call_id}}}, [terminal, terminal | {"line": 13}]
        )
        self.assertIsNone(value)
        self.assertEqual(line, 13)
        self.assertIn("2 terminal native results", error or "")

    def test_compact_cli_result_rejects_terminal_before_invocation(self) -> None:
        call_id = "summary-call"
        terminal = {"line": 12, "update": {
            "sessionUpdate": "tool_call_update", "toolCallId": call_id,
            "status": "completed", "rawOutput": {
                "type": "Bash", "exit_code": 0, "output": "{}", "truncated": False,
            },
        }}
        value, line, error = native_trace._compact_cli_result(
            {"row": {"line": 20, "update": {"toolCallId": call_id}}}, [terminal]
        )
        self.assertIsNone(value)
        self.assertEqual(line, 12)
        self.assertIn("does not follow", error or "")

    def test_compact_v4_prepare_summary_binds_setup_hash_and_producer_interpreter(self) -> None:
        setup_path = self.operator / "setup-result.json"
        script_path = self.operator / "operations.py"
        script_path.write_text("# frozen operations producer\n", encoding="utf-8")
        producer_python = str(Path("/usr/bin/python3").resolve())
        setup = {
            "status": "PREPARED", "run_id": self.manifest["run_id"],
            "treatment": "compact", "delivery_mode": "commits",
            "compact_startup_contract": "action-packet/v1",
            "runtime_python_executable": producer_python,
            "operations_script_sha256": hashlib.sha256(script_path.read_bytes()).hexdigest(),
        }
        setup_bytes = json.dumps(setup, sort_keys=True).encode("utf-8")
        setup_path.write_bytes(setup_bytes)
        value = {
            "schema": "ask-agent.compact-prepare-summary/v1", "status": "PREPARED",
            "run_id": self.manifest["run_id"], "treatment": "compact", "delivery_mode": "commits",
            "setup_path": str(setup_path.resolve()),
            "setup_sha256": hashlib.sha256(setup_bytes).hexdigest(),
            "dispatch_index_path": str((self.operator / "compact-dispatch" / "index.json").resolve()),
            "runtime_python_executable": producer_python,
        }
        call = {
            "tokens": ["python3", "-B", str(script_path.resolve()), "prepare-batch", "--run",
                       str(self.run.resolve()), "--compact"],
            "args": ["prepare-batch", "--run", str(self.run.resolve()), "--compact"],
        }
        errors, runtime = native_trace._compact_v4_prepare_summary_errors(
            self.run, self.manifest, {"delivery_mode": "commits"}, setup, value, call,
        )
        self.assertEqual(errors, [])
        self.assertEqual(runtime, producer_python)
        self.assertNotEqual(runtime, str(Path(sys.executable).resolve()))

        altered_summary = dict(value, setup_sha256="0" * 64)
        errors, _ = native_trace._compact_v4_prepare_summary_errors(
            self.run, self.manifest, {"delivery_mode": "commits"}, setup, altered_summary, call,
        )
        self.assertTrue(errors)

        setup["runtime_python_executable"] = "/opt/homebrew/opt/python@3.14/bin/python3.13"
        setup_path.write_text(json.dumps(setup, sort_keys=True), encoding="utf-8")
        errors, _ = native_trace._compact_v4_prepare_summary_errors(
            self.run, self.manifest, {"delivery_mode": "commits"}, setup, value, call,
        )
        self.assertTrue(errors)

        setup["runtime_python_executable"] = producer_python
        setup_path.write_text(json.dumps(setup, sort_keys=True), encoding="utf-8")
        conflicting = dict(call, tokens=["/usr/bin/python2", "-B", str(script_path.resolve()),
                                         "prepare-batch", "--run", str(self.run.resolve()), "--compact"])
        errors, _ = native_trace._compact_v4_prepare_summary_errors(
            self.run, self.manifest, {"delivery_mode": "commits"}, setup, value, conflicting,
        )
        self.assertTrue(errors)

    def test_compact_v4_dispatch_summary_binds_setup_and_index_bytes(self) -> None:
        setup_path = self.operator / "setup-result.json"
        setup_path.write_bytes(b'{"status":"PREPARED"}\n')
        index_path = self.operator / "compact-dispatch" / "index.json"
        index_path.parent.mkdir()
        index_bytes = b'{"schema":"ask-agent.compact-dispatch/v1"}\n'
        index_path.write_bytes(index_bytes)
        setup_sha = hashlib.sha256(setup_path.read_bytes()).hexdigest()
        value = {
            "schema": "ask-agent.compact-dispatch-summary/v1", "status": "PREPARED",
            "run_id": self.manifest["run_id"], "worker_ids": ["1", "2", "3"],
            "setup_path": str(setup_path.resolve()), "setup_sha256": setup_sha,
            "index_path": str(index_path.resolve()),
            "index_sha256": hashlib.sha256(index_bytes).hexdigest(),
        }
        self.assertEqual(native_trace._compact_v4_dispatch_summary_errors(
            self.run, self.manifest, setup_sha, ["1", "2", "3"], value,
        ), [])
        changed_index = dict(value, index_sha256="0" * 64)
        self.assertTrue(native_trace._compact_v4_dispatch_summary_errors(
            self.run, self.manifest, setup_sha, ["1", "2", "3"], changed_index,
        ))
        index_path.write_bytes(index_bytes + b"tampered")
        self.assertTrue(native_trace._compact_v4_dispatch_summary_errors(
            self.run, self.manifest, hashlib.sha256(setup_path.read_bytes()).hexdigest(),
            ["1", "2", "3"], value,
        ))

    def test_compact_v4_action_packet_binds_worker_assignment_and_target(self) -> None:
        task = self.manifest["task_assignments"][0]
        root = str(self.child_roots[0].resolve())
        binding = {"task": {
            "objective": task["assignment"], "expected_result": "src/step_1.py defines transform(x)=(1+1)*x+1*1 for every integer.",
            "write_set": [task["path"]], "mode": "edit", "delivery_mode": "commits",
        }, "workspace": {"root": root}}
        setup_worker = {"worktree": root}
        self.assertTrue(native_trace._compact_v4_binding_matches(binding, task, setup_worker, "commits"))
        swapped = dict(binding, task=dict(binding["task"], objective=self.manifest["task_assignments"][1]["assignment"],
                                          write_set=["src/step_2.py"]))
        self.assertFalse(native_trace._compact_v4_binding_matches(swapped, task, setup_worker, "commits"))
        foreign_write_set = dict(binding, task=dict(binding["task"], write_set=["foreign.txt"]))
        self.assertFalse(native_trace._compact_v4_binding_matches(foreign_write_set, task, setup_worker, "commits"))
        wrong_target = {"worktree": str(self.child_roots[1].resolve())}
        self.assertFalse(native_trace._compact_v4_binding_matches(binding, task, wrong_target, "commits"))

    def test_compact_v4_commit_projection_checks_patch_bytes_and_containment(self) -> None:
        store = self.run / "workspace-store"
        first = store / "attempts" / "worker-1" / "finish" / "contribution.patch"
        second = store / "attempts" / "worker-1" / "verify-return" / "contribution.patch"
        first.parent.mkdir(parents=True)
        second.parent.mkdir(parents=True)
        first_bytes = b"diff --git a/src/step_1.py b/src/step_1.py\n"
        first.write_bytes(first_bytes)
        second.write_bytes(first_bytes)
        phase_delivery = {"mode": "commits", "base": "a" * 40, "commits": ["b" * 40],
                          "commit_paths": ["src/step_1.py"],
                          "per_commit_paths": [{"commit": "b" * 40, "paths": ["src/step_1.py"]}],
                          "residual_paths": [], "contribution_patch": str(first.resolve())}
        returned_delivery = dict(phase_delivery, contribution_patch=str(second.resolve()))
        finish = {"patch_path": str(first.resolve()), "patch_sha256": hashlib.sha256(first_bytes).hexdigest()}
        self.assertTrue(native_trace._compact_commit_delivery_matches(
            self.run.resolve(), phase_delivery, returned_delivery, finish, True,
        ))
        second.write_bytes(first_bytes + b"tampered")
        self.assertFalse(native_trace._compact_commit_delivery_matches(
            self.run.resolve(), phase_delivery, returned_delivery, finish, True,
        ))
        second.unlink()
        second.symlink_to(first)
        self.assertFalse(native_trace._compact_commit_delivery_matches(
            self.run.resolve(), phase_delivery, returned_delivery, finish, True,
        ))
        outside = self.root / "outside.patch"
        outside.write_bytes(first_bytes)
        self.assertFalse(native_trace._compact_commit_delivery_matches(
            self.run.resolve(), phase_delivery, dict(phase_delivery, contribution_patch=str(outside.resolve())), finish, True,
        ))

    def test_native_worker_and_collection_results_require_unique_later_terminal(self) -> None:
        call_id = "native-phase"
        terminal = {"line": 22, "update": {
            "sessionUpdate": "tool_call_update", "toolCallId": call_id, "status": "completed",
        }}
        result, error = native_trace._unique_terminal_after(call_id, 20, [terminal])
        self.assertEqual(result, terminal)
        self.assertIsNone(error)

        result, error = native_trace._unique_terminal_after(
            call_id, 20, [terminal, terminal | {"line": 23}]
        )
        self.assertIsNone(result)
        self.assertIn("found 2", error or "")

        result, error = native_trace._unique_terminal_after(
            call_id, 20, [terminal | {"line": 19}]
        )
        self.assertIsNone(result)
        self.assertIn("does not follow", error or "")

    def test_parent_collection_requires_completed_typed_task_output_but_allows_partial_rows(self) -> None:
        row = {"task_id": self.child_ids[0], "status": "completed", "exit_code": 0}
        partial = {"update": {
            "status": "completed",
            "rawOutput": {"type": "TaskOutput", "MultiResult": {"results": [row]}},
        }}
        rows, error = native_trace._completed_task_output_rows(partial)
        self.assertEqual(rows, [row])
        self.assertIsNone(error)

        forged_failure = {"update": {
            "status": "failed",
            "rawOutput": {"type": "Other", "results": [row]},
        }}
        rows, error = native_trace._completed_task_output_rows(forged_failure)
        self.assertIsNone(rows)
        self.assertIn("did not complete", error or "")

        untyped_success = {"update": {
            "status": "completed",
            "rawOutput": {"type": "Other", "results": [row]},
        }}
        rows, error = native_trace._completed_task_output_rows(untyped_success)
        self.assertIsNone(rows)
        self.assertIn("typed TaskOutput", error or "")

    def test_compact_parent_collection_rejects_failed_untyped_rows(self) -> None:
        self._write_json(self.operator / "setup-result.json", {"workers": []})
        assignments = self.manifest["task_assignments"]
        launches = [
            {"worker_id": str(index), "child_session_id": child}
            for index, child in enumerate(self.child_ids, 1)
        ]
        collection_call = {
            "line": 10,
            "update": {
                "toolCallId": "collect-call",
                "rawInput": {"task_ids": list(self.child_ids)},
            },
        }
        rows = [
            {"task_id": child, "status": "completed", "exit_code": 0}
            for child in self.child_ids
        ]
        updates_path = self.operator / "native-evidence" / "root-updates.jsonl"

        for status, output, expected_detail in (
            ("failed", {"type": "Other", "results": rows}, "did not complete successfully"),
            ("completed", {"type": "Other", "results": rows}, "typed TaskOutput envelope"),
        ):
            with self.subTest(status=status, output_type=output["type"]):
                terminal = {"line": 11, "update": {
                    "sessionUpdate": "tool_call_update", "toolCallId": "collect-call",
                    "status": status, "rawOutput": output,
                }}
                check = native_trace._compact_parent_return_check(
                    self.run, assignments, [terminal], [collection_call], updates_path,
                    delivery_mode="patch-legacy", launches=launches,
                )
                self.assertEqual(check["status"], "FAIL")
                self.assertIn(expected_detail, check["detail"])

    def test_saved_proof_json_rejects_duplicate_keys(self) -> None:
        path = self.operator / "integration-result.json"
        path.write_text('{"status":"FAILED","status":"NO_INTEGRATION"}\n', encoding="utf-8")

        with self.assertRaises(native_trace.TraceError):
            native_trace._read_json(path, "integration result")

    def test_parent_fixture_summary_rejects_duplicate_invocation(self) -> None:
        self._enable_verification_summary()
        self._enable_verification_summary()

        report = self._audit()

        check = report["checks"]["fixture_verification_summary"]
        self.assertEqual(check["status"], "FAIL")
        self.assertEqual(check["invocation_count"], 2)
        self.assertNotEqual(report["status"], "PASS")

    def test_parent_fixture_summary_rejects_duplicate_json_keys(self) -> None:
        summary, _ = self._enable_verification_summary()
        stdout = json.dumps(summary, sort_keys=True, separators=(",", ":"))
        self.assertIn('"passed":true', stdout)
        call_id = self.updates[-1]["params"]["update"]["toolCallId"]
        terminal = self.updates[-1]["params"]["update"]
        terminal["rawOutput"]["output"] = stdout.replace(
            '"passed":true', '"passed":false,"passed":true', 1
        )
        self._write_updates()

        report = self._audit()

        check = report["checks"]["fixture_verification_summary"]
        self.assertEqual(check["status"], "INCOMPLETE")
        self.assertIn("complete UTF-8 JSON", check["detail"])
        self.assertNotEqual(report["status"], "PASS")
        self.assertTrue(call_id)

    def test_parent_fixture_summary_rejects_nonzero_exit_and_wrong_script_path(self) -> None:
        self._enable_verification_summary(exit_code=1)

        nonzero_report = self._audit()

        nonzero_check = nonzero_report["checks"]["fixture_verification_summary"]
        self.assertEqual(nonzero_check["status"], "INCOMPLETE")
        self.assertIn("nonzero", nonzero_check["detail"])
        self.assertNotEqual(nonzero_report["status"], "PASS")

        changed = NativeTraceTests()
        changed.setUp()
        try:
            changed._enable_verification_summary()
            call = changed.updates[-2]["params"]["update"]
            call["rawInput"]["command"] = call["rawInput"]["command"].replace(
                str(changed.operator / "fixture.py"), str(changed.operator / "other" / "fixture.py")
            )
            changed._write_updates()

            changed_report = changed._audit()

            changed_check = changed_report["checks"]["fixture_verification_summary"]
            self.assertEqual(changed_check["status"], "FAIL")
            self.assertIn("not bound to frozen fixture.py", changed_check["detail"])
            self.assertNotEqual(changed_report["status"], "PASS")
        finally:
            changed.tearDown()

        malformed = NativeTraceTests()
        malformed.setUp()
        try:
            malformed._enable_verification_summary()
            call = malformed.updates[-2]["params"]["update"]
            call["rawInput"]["command"] = shlex.join([
                "python3", "-B", str(malformed.operator / "fixture.py"),
                "verify", "--run", "--summary",
            ])
            malformed._write_updates()

            malformed_report = malformed._audit()

            malformed_check = malformed_report["checks"]["fixture_verification_summary"]
            self.assertEqual(malformed_check["status"], "FAIL")
            self.assertIn("not bound to frozen fixture.py", malformed_check["detail"])
            self.assertNotEqual(malformed_report["status"], "PASS")
        finally:
            malformed.tearDown()

        chained = NativeTraceTests()
        chained.setUp()
        try:
            chained._enable_verification_summary()
            call = chained.updates[-2]["params"]["update"]
            call["rawInput"]["command"] = "echo unrelated; " + call["rawInput"]["command"]
            chained._write_updates()

            chained_report = chained._audit()

            chained_check = chained_report["checks"]["fixture_verification_summary"]
            self.assertEqual(chained_check["status"], "FAIL")
            self.assertIn("standalone python3 invocation", chained_check["detail"])
            self.assertNotEqual(chained_report["status"], "PASS")
        finally:
            chained.tearDown()

    def test_parent_fixture_summary_rejects_wrong_logical_report_path(self) -> None:
        summary, _ = self._enable_verification_summary()
        summary["report_path"] = str((self.operator / "other-verification.json").resolve())
        self.updates[-1]["params"]["update"]["rawOutput"]["output"] = json.dumps(
            summary, sort_keys=True, separators=(",", ":")
        )
        self._write_updates()

        report = self._audit()

        check = report["checks"]["fixture_verification_summary"]
        self.assertEqual(check["status"], "FAIL")
        self.assertIn("differs from the independently audited saved report", check["detail"])
        self.assertNotEqual(report["status"], "PASS")

    def test_parent_fixture_summary_rejects_truncated_output(self) -> None:
        self._enable_verification_summary(truncated=True)

        report = self._audit()

        check = report["checks"]["fixture_verification_summary"]
        self.assertEqual(check["status"], "INCOMPLETE")
        self.assertIn("truncated", check["detail"])
        self.assertNotEqual(report["status"], "PASS")

    def test_parent_fixture_summary_requires_saved_parent_report_after_post_exit(self) -> None:
        self._enable_verification_summary()
        (self.operator / "parent-verification.json").unlink()

        report = self._audit()

        check = report["checks"]["fixture_verification_summary"]
        self.assertEqual(check["status"], "INCOMPLETE")
        self.assertIn("parent-verification.json is unavailable", check["detail"])
        self.assertNotEqual(report["status"], "PASS")

    def test_parent_fixture_summary_uses_archived_report_after_interrupted_post_exit(self) -> None:
        self._enable_verification_summary()
        for name in ("verification.json", "post-exit-verification.json", "post-exit-result.json"):
            (self.operator / name).unlink()
        self._write_json(self.operator / "integrity-result.json", {"passed": True})

        report = self._audit()

        check = report["checks"]["fixture_verification_summary"]
        self.assertEqual(check["status"], "PASS")
        self.assertEqual(check["saved_report_path"], str((self.operator / "parent-verification.json").resolve()))
        self.assertTrue(any(item["path"].endswith("integrity-result.json") for item in check["evidence"]))

    def test_parent_fixture_summary_rejects_failed_or_changed_saved_report(self) -> None:
        failed_report = {
            "schema_version": 1,
            "run_id": self.manifest["run_id"],
            "run_path": str(self.run.resolve()),
            "passed": False,
            "checks": {"parent_preserved": False},
            "errors": ["parent state changed"],
        }
        self._enable_verification_summary(report=failed_report)

        failed_audit = self._audit()

        self.assertEqual(failed_audit["checks"]["fixture_verification_summary"]["status"], "FAIL")
        self.assertNotEqual(failed_audit["status"], "PASS")

        changed = NativeTraceTests()
        changed.setUp()
        try:
            changed._enable_verification_summary()
            saved = changed.operator / "parent-verification.json"
            saved.write_bytes(saved.read_bytes() + b" ")

            changed_audit = changed._audit()

            changed_check = changed_audit["checks"]["fixture_verification_summary"]
            self.assertEqual(changed_check["status"], "FAIL")
            self.assertIn("independently audited saved report", changed_check["detail"])
            self.assertNotEqual(changed_audit["status"], "PASS")
        finally:
            changed.tearDown()

    def test_parent_fixture_summary_rejects_report_identity_and_contradictory_checks(self) -> None:
        wrong_identity = NativeTraceTests()
        wrong_identity.setUp()
        try:
            wrong_identity._enable_verification_summary(report={
                "schema_version": 1,
                "run_id": "different-run",
                "run_path": str(wrong_identity.run.resolve()),
                "passed": True,
                "checks": {"parent_preserved": True},
                "errors": [],
            })

            identity_report = wrong_identity._audit()

            identity_check = identity_report["checks"]["fixture_verification_summary"]
            self.assertEqual(identity_check["status"], "FAIL")
            self.assertIn("run identity differs", identity_check["detail"])
            self.assertNotEqual(identity_report["status"], "PASS")
        finally:
            wrong_identity.tearDown()

        contradictory = NativeTraceTests()
        contradictory.setUp()
        try:
            contradictory._enable_verification_summary(report={
                "schema_version": 1,
                "run_id": contradictory.manifest["run_id"],
                "run_path": str(contradictory.run.resolve()),
                "passed": True,
                "checks": {"parent_preserved": False},
                "errors": [],
            })

            contradictory_report = contradictory._audit()

            contradictory_check = contradictory_report["checks"]["fixture_verification_summary"]
            self.assertEqual(contradictory_check["status"], "FAIL")
            self.assertIn("passed field contradicts", contradictory_check["detail"])
            self.assertNotEqual(contradictory_report["status"], "PASS")
        finally:
            contradictory.tearDown()

    def test_parent_fixture_summary_rejects_boolean_check_count(self) -> None:
        self._enable_verification_summary(report={
            "schema_version": 1,
            "run_id": self.manifest["run_id"],
            "run_path": str(self.run.resolve()),
            "passed": True,
            "checks": {"parent_preserved": True},
            "errors": [],
        })
        terminal = self.updates[-1]["params"]["update"]
        terminal["rawOutput"]["output"] = terminal["rawOutput"]["output"].replace(
            '"check_count":1', '"check_count":true', 1
        )
        self._write_updates()

        report = self._audit()

        check = report["checks"]["fixture_verification_summary"]
        self.assertEqual(check["status"], "FAIL")
        self.assertNotEqual(report["status"], "PASS")

    def test_parent_fixture_summary_requires_explicit_untruncated_marker(self) -> None:
        self._enable_verification_summary()
        self.updates[-1]["params"]["update"]["rawOutput"].pop("truncated")
        self._write_updates()

        report = self._audit()

        check = report["checks"]["fixture_verification_summary"]
        self.assertEqual(check["status"], "INCOMPLETE")
        self.assertIn("explicit untruncated output marker", check["detail"])
        self.assertNotEqual(report["status"], "PASS")

    def test_new_treatment_versions_require_summary_flag_and_legacy_is_labeled(self) -> None:
        for treatment in (
            {"treatment": "compact", "version": 2},
            {"treatment": "baseline", "version": 5},
            {"treatment": "batched", "version": 5},
            {"treatment": "baseline", "version": 5, "verification_output": "summary-v2"},
        ):
            with self.subTest(treatment=treatment):
                case = NativeTraceTests()
                case.setUp()
                try:
                    case._enable_verification_summary(treatment=treatment)

                    report = case._audit()

                    check = report["checks"]["fixture_verification_summary"]
                    self.assertEqual(check["status"], "FAIL")
                    if "verification_output" in treatment:
                        self.assertIn("unknown verification_output", check["detail"])
                    else:
                        self.assertIn("missing verification_output", check["detail"])
                    self.assertNotEqual(report["status"], "PASS")
                finally:
                    case.tearDown()

        self._enable_verification_summary(
            treatment={"treatment": "baseline", "version": 4}
        )

        legacy_report = self._audit()

        legacy_check = legacy_report["checks"]["fixture_verification_summary"]
        self.assertEqual(legacy_check["status"], "LEGACY")
        self.assertEqual(legacy_check["complete_output_proof"], "NOT_MEASURED")
        self.assertIn("parent complete-output proof NOT_MEASURED", legacy_check["detail"])

    def test_summary_output_version_contract_accepts_only_declared_new_versions(self) -> None:
        for treatment in (
            {"treatment": "compact", "version": 2, "verification_output": "summary-v1"},
            {"treatment": "compact", "version": 3, "verification_output": "summary-v1"},
            {"treatment": "baseline", "version": 5, "verification_output": "summary-v1"},
            {"treatment": "batched", "version": 5, "verification_output": "summary-v1"},
        ):
            with self.subTest(treatment=treatment):
                mode, _ = native_trace._fixture_verification_output_mode(treatment)
                self.assertEqual(mode, "summary-v1")

        for treatment in (
            {"treatment": "compact", "version": 1},
            {"treatment": "baseline", "version": 4},
            {"treatment": "packet"},
            {"treatment": "scripted", "version": 4},
            {"treatment": "compact", "version": 1, "verification_output": "summary-v1"},
        ):
            with self.subTest(treatment=treatment):
                mode, detail = native_trace._fixture_verification_output_mode(treatment)
                if treatment.get("verification_output") == "summary-v1":
                    self.assertEqual(mode, "invalid")
                    self.assertIn("summary-v1 is not declared", detail)
                else:
                    self.assertEqual(mode, "legacy")
                    self.assertIn("parent complete-output proof NOT_MEASURED", detail)

    def test_compact_delivery_mode_is_explicit_and_versioned(self) -> None:
        valid = (
            (None, {"treatment": "compact", "version": 2, "delivery_mode": "patch"}, "patch", "PASS"),
            ("commits", {"treatment": "compact", "version": 3, "delivery_mode": "commits"}, "commits", "PASS"),
            ("ephemeral", {"treatment": "compact", "version": 3, "delivery_mode": "ephemeral"}, "ephemeral", "PASS"),
            ("patch", {"treatment": "compact", "version": 4, "delivery_mode": "patch"}, "patch", "PASS"),
            ("commits", {"treatment": "compact", "version": 4, "delivery_mode": "commits"}, "commits", "PASS"),
            ("ephemeral", {"treatment": "compact", "version": 4, "delivery_mode": "ephemeral"}, "ephemeral", "PASS"),
            (None, {"treatment": "compact", "version": 1}, "patch-legacy", "LEGACY"),
        )
        for manifest_mode, treatment, expected_mode, expected_status in valid:
            with self.subTest(manifest_mode=manifest_mode, treatment=treatment):
                manifest = {} if manifest_mode is None else {"delivery_mode": manifest_mode}
                mode, check = native_trace._compact_delivery_mode(manifest, treatment)
                self.assertEqual(mode, expected_mode)
                self.assertEqual(check["status"], expected_status)

        invalid = (
            ({}, {"treatment": "compact", "version": 2}, "patch v2 requires its explicit treatment flag"),
            ({"delivery_mode": "commits"}, {"treatment": "compact", "version": 3, "delivery_mode": "ephemeral"},
             "manifest and treatment mode mismatch"),
            ({}, {"treatment": "compact", "version": 3, "delivery_mode": "commits"},
             "v3 requires explicit manifest delivery mode"),
            ({"delivery_mode": "patch"}, {"treatment": "compact", "version": 3, "delivery_mode": "patch"},
             "v3 is reserved for explicit commits or ephemeral modes"),
        )
        for manifest, treatment, _ in invalid:
            with self.subTest(manifest=manifest, treatment=treatment):
                mode, check = native_trace._compact_delivery_mode(manifest, treatment)
                self.assertIsNone(mode)
                self.assertEqual(check["status"], "FAIL")

    def test_commit_delivery_requires_three_successful_native_git_calls_and_full_sha(self) -> None:
        cwd = str(self.child_roots[0].resolve())
        expected_sha = "a" * 40
        commands = [
            ["git", "-C", cwd, "add", "--", "src/step_1.py"],
            ["git", "-C", cwd, "commit", "-m", "Ask Agent fixture worker 1"],
            ["git", "-C", cwd, "rev-parse", "HEAD"],
        ]
        child_calls = []
        child_updates = []
        for index, (action, command) in enumerate(zip(("add", "commit", "rev-parse"), commands)):
            call_id = f"git-{action}"
            call_line = 3 + index * 2
            result_line = call_line + 1
            child_calls.append({"line": call_line, "tool_call_id": call_id, "command": shlex.join(command)})
            child_updates.append({"line": result_line, "update": {
                "sessionUpdate": "tool_call_update", "toolCallId": call_id, "status": "completed",
                "rawOutput": {"type": "Bash", "exit_code": 0,
                              "output": expected_sha + "\n" if action == "rev-parse" else "",
                              "truncated": False},
            }})
        check, detail = native_trace._compact_native_worker_commit_check(
            child_calls, child_updates, worker="1", cwd=cwd, owned_path="src/step_1.py",
            expected_commit=expected_sha, start_terminal_line=2, finish_call_line=10,
            updates_path=self.session_dir / "updates.jsonl",
        )
        self.assertEqual(check["status"], "PASS")
        self.assertEqual(detail["rev_parse_invocations"], 1)

        child_updates[-1]["update"]["rawOutput"]["output"] = "b" * 40 + "\n"
        mismatch, _ = native_trace._compact_native_worker_commit_check(
            child_calls, child_updates, worker="1", cwd=cwd, owned_path="src/step_1.py",
            expected_commit=expected_sha, start_terminal_line=2, finish_call_line=10,
            updates_path=self.session_dir / "updates.jsonl",
        )
        self.assertEqual(mismatch["status"], "FAIL")
        self.assertIn("full HEAD SHA", mismatch["detail"])

        missing_readback, _ = native_trace._compact_native_worker_commit_check(
            child_calls[:2], child_updates[:2], worker="1", cwd=cwd, owned_path="src/step_1.py",
            expected_commit=expected_sha, start_terminal_line=2, finish_call_line=10,
            updates_path=self.session_dir / "updates.jsonl",
        )
        self.assertEqual(missing_readback["status"], "FAIL")

    def test_ephemeral_delivery_rejects_native_worker_commit_calls(self) -> None:
        commit = {"line": 5, "tool_call_id": "worker-commit",
                  "command": shlex.join(["git", "-C", str(self.child_roots[0].resolve()),
                                          "commit", "-m", "Ask Agent fixture worker 1"])}
        check, detail = native_trace._compact_ephemeral_no_commit_check(
            [commit], "1", self.session_dir / "updates.jsonl"
        )
        self.assertEqual(check["status"], "FAIL")
        self.assertEqual(detail["commit_invocations"], 1)

    def test_ephemeral_findings_bind_exact_oracle_bytes_and_production_records(self) -> None:
        task = self.manifest["task_assignments"][0]
        worker = task["worker_id"]
        worktree = self.child_roots[0]
        module = worktree / task["path"]
        module.parent.mkdir(parents=True)
        module.write_text("def transform(x):\n    return 2 * x + 1\n", encoding="utf-8")
        audit = {
            "status": "ephemeral-audit", "findings_only": True,
            "changed_paths": [task["path"], ".experiment-local/owner.txt"],
            "baseline_fingerprint": "a" * 64, "fingerprint": "b" * 64,
            "head": "c" * 40, "branch": "worker-1", "scratch_retained": True,
            "actual_cwd": str(worktree.resolve()),
        }
        returned_audit = {key: value for key, value in audit.items() if key != "actual_cwd"}
        production = {"workspace_evidence": {"ephemeral_audit": audit}}
        phase = {
            "status": "PASSED", "worker_id": worker,
            "checks": {"production_worker_finish_passed": True, "ephemeral_findings_only": True},
            "ephemeral_audit": audit, "compact_worker_result": production,
        }
        returned = {
            "status": "READY_FOR_PARENT_ACCEPTANCE", "command": "verify-return",
            "workspace_evidence": {"ephemeral_audit": returned_audit},
        }
        return_record = {"status": "PASSED", "exit_code": 0, "result": returned}
        values = [-10**30, -999, -7, -1, 0, 1, 9, 100, 10**30]
        oracle = {"passed": True, "cases": [
            {"input": value, "expected": 2 * value + 1, "actual": 2 * value + 1, "passed": True}
            for value in values
        ]}
        finding = {
            "worker_id": worker, "path": task["path"], "formula": "(1+1)*x+1*1",
            "module_sha256": hashlib.sha256(module.read_bytes()).hexdigest(),
            "oracle": oracle, "ephemeral_audit": returned_audit,
        }
        finding_sha = hashlib.sha256(json.dumps(
            finding, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")).hexdigest()
        setup_worker = {"worktree": str(worktree.resolve())}

        valid, detail = native_trace._ephemeral_finding_valid(
            self.run, task, setup_worker, return_record, phase, finding, finding_sha
        )

        self.assertTrue(valid, detail)
        phase_projection_finding = dict(finding, ephemeral_audit=audit)
        phase_projection_valid, phase_projection_detail = native_trace._ephemeral_finding_valid(
            self.run, task, setup_worker, return_record, phase, phase_projection_finding, finding_sha
        )
        self.assertFalse(phase_projection_valid)
        self.assertIn("assigned task and phase evidence", phase_projection_detail)
        wrong_hash, wrong_hash_detail = native_trace._ephemeral_finding_valid(
            self.run, task, setup_worker, return_record, phase, finding, "0" * 64
        )
        self.assertFalse(wrong_hash)
        self.assertIn("SHA-256", wrong_hash_detail)
        wrong_return = dict(return_record, result={**returned, "workspace_evidence": {}})
        unbound, unbound_detail = native_trace._ephemeral_finding_valid(
            self.run, task, setup_worker, wrong_return, phase, finding, finding_sha
        )
        self.assertFalse(unbound)
        self.assertIn("findings-only", unbound_detail)

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
        self.assertEqual(report["checks"]["fixture_verification_summary"]["status"], "LEGACY")
        self.assertEqual(report["checks"]["fixture_verification_summary"]["complete_output_proof"], "NOT_MEASURED")
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

    def test_probe_parser_ignores_prose_and_accepts_cd_prefixed_commands(self) -> None:
        prose = (
            "Changes / checks: worker-only changed files; checks.py --worker 2 result; "
            "start and finish probe exit status and errors."
        )
        start = (
            "cd /worker/root && python3 /run/operator/fixture.py probe "
            "--run /run --worker 2 --phase start"
        )
        finish = (
            "cd /worker/root && python3 /run/operator/fixture.py probe "
            "--run /run --worker 2 --phase finish"
        )

        self.assertEqual(
            native_trace._explicit_probe_workers(f"{prose}\n{start}\n{finish}"),
            ({"start": "2", "finish": "2"}, None, False),
        )
        self.assertEqual(
            native_trace._explicit_probe_workers(
                f"{prose}\n{start.replace('--phase start', '')}\n{finish}"
            ),
            ({}, "probe command has missing or duplicate worker/phase flags", True),
        )
        self.assertEqual(
            native_trace._explicit_probe_workers(f"{prose}\n{start}\n{finish}\n{start}"),
            ({}, "typed prompt has duplicate start or finish probe commands", True),
        )

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

    def test_compact_v4_packet_allows_owned_path_from_bound_packet_only(self) -> None:
        raw = dict(self.calls[0]["params"]["update"]["rawInput"])
        raw["prompt"] = raw["prompt"].replace("src/step_1.py", "the assigned source module")
        starts = {"1": {"record": {"root": str(self.child_roots[0].resolve())}}}
        worker, issue, conflict = native_trace._bind_spawn_to_probe(raw, self.manifest["task_assignments"], starts)
        self.assertIsNone(worker)
        self.assertTrue(conflict)
        self.assertIn("owned path", issue or "")

        worker, issue, conflict = native_trace._bind_spawn_to_probe(
            raw, self.manifest["task_assignments"], starts, allow_owned_path_omission=True,
        )
        self.assertEqual(worker, "1")
        self.assertIsNone(issue)
        self.assertFalse(conflict)

        raw["prompt"] = raw["prompt"].replace("--worker 1 --phase finish", "--worker 2 --phase finish")
        worker, issue, conflict = native_trace._bind_spawn_to_probe(
            raw, self.manifest["task_assignments"], starts, allow_owned_path_omission=True,
        )
        self.assertIsNone(worker)
        self.assertTrue(conflict)
        self.assertIn("worker IDs disagree", issue or "")

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
