#!/usr/bin/env python3
"""Focused offline checks for the native-host trace evaluator."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

_TRACE_SPEC = importlib.util.spec_from_file_location("shiploop_native_trace", Path(__file__).with_name("trace.py"))
if _TRACE_SPEC is None or _TRACE_SPEC.loader is None:
    raise RuntimeError("could not load the sibling native trace evaluator")
_TRACE = importlib.util.module_from_spec(_TRACE_SPEC)
_TRACE_SPEC.loader.exec_module(_TRACE)
TraceError = _TRACE.TraceError
build_manifest = _TRACE.build_manifest
evaluate_events = _TRACE.evaluate_events
evaluate_host_trace = _TRACE.evaluate_host_trace


IDS = {
    "A": "11111111-1111-4111-8111-111111111111",
    "B": "22222222-2222-4222-8222-222222222222",
    "C": "33333333-3333-4333-8333-333333333333",
    "J": "44444444-4444-4444-8444-444444444444",
}
ATTEMPTS = {step: f"attempt-{step.lower()}" for step in IDS}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def make_pilot(root: Path) -> tuple[Path, dict[str, str]]:
    pilot = root / "pilot"
    feature = root / "feature"
    feature.mkdir(parents=True)
    source_root = root / "source"
    driver_python = root / "python3"
    write_json(pilot / "context.json", {
        "fixture": {"initiating_feature": str(feature)},
        "selected": {"python": str(driver_python), "source_root": str(source_root)},
    })
    workspaces: dict[str, str] = {}
    for step, identifier in IDS.items():
        attempt = ATTEMPTS[step]
        workspace = root / f"worker-{step.lower()}"
        workspace.mkdir()
        workspaces[step] = str(workspace)
        handle_source = pilot / f"{step}-handle.json"
        write_json(pilot / "workspaces" / f"{step}-{attempt}.json", {
            "step": step, "attempt": attempt, "workspace": str(workspace),
        })
        write_json(pilot / "packets" / f"{step}-{attempt}.json", {
            "step": step, "attempt": attempt, "run_id": "dispatcher-run", "context": {"workspace": str(workspace)},
        })
        write_json(pilot / "handles" / f"{step}-{attempt}.json", {
            "step": step, "attempt": attempt, "handle": identifier, "source": str(handle_source),
        })
        write_json(pilot / "accepted" / f"{step}-{attempt}.json", {
            "step": step, "attempt": attempt, "source_commit": "a" * 40,
        })
    return pilot, workspaces


def tool_call(identifier: str, name: str, raw_input: dict) -> dict:
    return {"type": "tool_call", "toolCallId": identifier, "toolName": name, "rawInput": raw_input}


def tool_update(identifier: str, status: str, raw_output: dict | None = None) -> dict:
    value = {"type": "tool_call_update", "toolCallId": identifier, "status": status}
    if raw_output is not None:
        value["rawOutput"] = raw_output
    return value


def bash_result(command: str, *, exit_code: int = 0, signal: object = None, timed_out: bool = False) -> dict:
    return {
        "type": "Bash",
        "output": [],
        "output_for_prompt": "",
        "exit_code": exit_code,
        "command": command,
        "truncated": False,
        "signal": signal,
        "timed_out": timed_out,
        "description": None,
        "current_dir": "/tmp",
        "output_file": "",
        "total_bytes": 0,
    }


def driver(manifest: dict, action: str, step: str | None = None) -> list[dict]:
    command = [manifest["driver_python"], "-B", manifest["driver_path"], action, "--pilot-dir", manifest["pilot_dir"]]
    if action == "claim":
        command += ["--steps", "A", "B"]
    elif action not in {"show", "finish"}:
        detail = manifest["steps"][step]
        command += ["--step", step, "--attempt", detail["attempt"]]
        if action == "launched":
            command += ["--handle-file", detail["handle_source"]]
        if action == "import-handoff":
            command += ["--handoff-manifest", detail["handoff"], "--confirmed-stopped"]
        if action in {"prepare-integration", "done"}:
            command += ["--confirmed-stopped"]
    identifier = f"driver-{action}-{step or 'all'}"
    rendered = " ".join(command)
    return [tool_call(identifier, "run_terminal_command", {"command": rendered}), tool_update(identifier, "completed", bash_result(rendered))]


def prompt_for(manifest: dict, step: str) -> str:
    detail = manifest["steps"][step]
    return (
        f"You are the fresh native Ask-Agent worker for ShipLoop step {step}, attempt {detail['attempt']}.\n"
        f"Work only in {detail['workspace']}.\n"
        f"Write {detail['handoff']}."
    )


def spawn(manifest: dict, step: str) -> list[dict]:
    detail = manifest["steps"][step]
    identifier = f"spawn-{step}"
    return [
        tool_call(identifier, "spawn_subagent", {
            "cwd": detail["workspace"], "background": True, "prompt": prompt_for(manifest, step),
        }),
        tool_update(identifier, "completed", {"type": "Text", "text": f"Subagent started\nsubagent_id: {detail['handle']}"}),
    ]


def collect(manifest: dict, steps: list[str], number: int) -> list[dict]:
    identifier = f"collect-{number}"
    rows = []
    timing = {
        "A": ("2026-09-19T12:00:01.100Z", "2026-09-19T12:00:07.900Z"),
        "B": ("2026-09-19T12:00:02.100Z", "2026-09-19T12:00:08.900Z"),
        "C": ("2026-09-19T12:00:09.100Z", "2026-09-19T12:00:11.900Z"),
        "J": ("2026-09-19T12:00:12.100Z", "2026-09-19T12:00:13.900Z"),
    }
    for step in steps:
        started, ended = timing[step]
        rows.append({"task_id": manifest["steps"][step]["handle"], "status": "completed", "exit_code": 0,
                     "started": started, "ended": ended})
    return [
        tool_call(identifier, "get_command_or_subagent_output", {"task_ids": [manifest["steps"][step]["handle"] for step in steps], "timeout_ms": 1000}),
        tool_update(identifier, "completed", {"type": "TaskOutput", "MultiResult": {"results": rows}}),
    ]


def valid_events(manifest: dict) -> list[dict]:
    events: list[dict] = [{"type": "available_commands", "tools": ["spawn_subagent"]}]
    events += driver(manifest, "claim")
    events += driver(manifest, "start", "A")
    events += driver(manifest, "start", "B")
    events += spawn(manifest, "A")
    events += spawn(manifest, "B")
    events += driver(manifest, "launched", "A")
    events += driver(manifest, "launched", "B")
    events += collect(manifest, ["A"], 1)
    for action in ("import-handoff", "prepare-integration", "done"):
        events += driver(manifest, action, "A")
    events += driver(manifest, "start", "C")
    events += spawn(manifest, "C")
    events += driver(manifest, "launched", "C")
    events += collect(manifest, ["B"], 2)
    for action in ("import-handoff", "prepare-integration", "done"):
        events += driver(manifest, action, "B")
    events += collect(manifest, ["C"], 3)
    for action in ("import-handoff", "prepare-integration", "done"):
        events += driver(manifest, action, "C")
    events += driver(manifest, "start", "J")
    events += spawn(manifest, "J")
    events += driver(manifest, "launched", "J")
    events += collect(manifest, ["J"], 4)
    for action in ("import-handoff", "prepare-integration", "done"):
        events += driver(manifest, action, "J")
    events += driver(manifest, "finish")
    events.append({"type": "end", "stopReason": "end_turn", "sessionId": "parent-session"})
    return events


class NativeHostTraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.pilot, self.workspaces = make_pilot(self.root)
        self.manifest = build_manifest(self.pilot)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def evaluate(self, events: list[dict]) -> dict:
        return evaluate_events(events, self.manifest)

    def test_accepts_typed_four_worker_graph_with_overlap(self) -> None:
        result = self.evaluate(valid_events(self.manifest))
        self.assertTrue(result["passed"], result["errors"])
        self.assertTrue(result["overlap"]["observed"])
        self.assertTrue(result["overlap"]["passed"])

    def test_rejects_missing_host_terminal_event(self) -> None:
        events = valid_events(self.manifest)[:-1]
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("host trace has no terminal end_turn", "\n".join(result["errors"]))

    def test_rejects_cancelled_host_terminal_event(self) -> None:
        events = valid_events(self.manifest)
        events[-1]["stopReason"] = "cancelled"
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("host terminal event is not end_turn", "\n".join(result["errors"]))

    def test_rejects_forged_retained_handle(self) -> None:
        self.manifest["steps"]["A"]["handle"] = IDS["B"]
        result = self.evaluate(valid_events(build_manifest(self.pilot)))
        self.assertFalse(result["passed"])
        self.assertIn("does not equal retained handle", "\n".join(result["errors"]))

    def test_rejects_prose_only_handle(self) -> None:
        events = valid_events(self.manifest)
        update = next(event for event in events if event.get("toolCallId") == "spawn-A" and event["type"] == "tool_call_update")
        update["rawOutput"] = {"type": "Text", "text": "worker claimed to be started with a handle"}
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("no unique typed subagent_id", "\n".join(result["errors"]))

    def test_rejects_dispatch_before_completed_assignment_receipt(self) -> None:
        events = valid_events(self.manifest)
        update = next(event for event in events if event.get("toolCallId") == "driver-start-B" and event["type"] == "tool_call_update")
        update["status"] = "failed"
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("B start has no completed parent terminal receipt", "\n".join(result["errors"]))

    def test_rejects_nonzero_driver_terminal_result(self) -> None:
        events = valid_events(self.manifest)
        update = next(event for event in events if event.get("toolCallId") == "driver-start-A" and event["type"] == "tool_call_update")
        update["rawOutput"]["exit_code"] = 1
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("A start terminal result exit_code is not zero", "\n".join(result["errors"]))

    def test_rejects_driver_terminal_command_mismatch(self) -> None:
        events = valid_events(self.manifest)
        update = next(event for event in events if event.get("toolCallId") == "driver-start-A" and event["type"] == "tool_call_update")
        update["rawOutput"]["command"] += " --forged"
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("A start terminal result command differs", "\n".join(result["errors"]))

    def test_rejects_missing_driver_terminal_result(self) -> None:
        events = valid_events(self.manifest)
        update = next(event for event in events if event.get("toolCallId") == "driver-start-A" and event["type"] == "tool_call_update")
        del update["rawOutput"]
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("A start terminal result is absent", "\n".join(result["errors"]))

    def test_rejects_non_bash_driver_terminal_result(self) -> None:
        events = valid_events(self.manifest)
        update = next(event for event in events if event.get("toolCallId") == "driver-start-A" and event["type"] == "tool_call_update")
        update["rawOutput"]["type"] = "TaskOutput"
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("A start terminal result is not a Bash result", "\n".join(result["errors"]))

    def test_rejects_terminal_worker_failure_after_success(self) -> None:
        events = valid_events(self.manifest)
        update = next(event for event in events if event.get("toolCallId") == "collect-1" and event["type"] == "tool_call_update")
        update["rawOutput"]["MultiResult"]["results"].append({
            "task_id": self.manifest["steps"]["A"]["handle"], "status": "failed", "exit_code": 1,
        })
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("A has non-success terminal native collection", "\n".join(result["errors"]))

    def test_rejects_terminal_worker_failure_before_success(self) -> None:
        events = valid_events(self.manifest)
        update = next(event for event in events if event.get("toolCallId") == "collect-1" and event["type"] == "tool_call_update")
        update["rawOutput"]["MultiResult"]["results"].insert(0, {
            "task_id": self.manifest["steps"]["A"]["handle"], "status": "failed", "exit_code": 1,
        })
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("A has non-success terminal native collection", "\n".join(result["errors"]))

    def test_rejects_boolean_worker_exit_code(self) -> None:
        events = valid_events(self.manifest)
        update = next(event for event in events if event.get("toolCallId") == "collect-1" and event["type"] == "tool_call_update")
        update["rawOutput"]["MultiResult"]["results"][0]["exit_code"] = False
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("A has non-success terminal native collection", "\n".join(result["errors"]))

    def test_accepts_pending_worker_poll_before_success(self) -> None:
        events = valid_events(self.manifest)
        pending = [
            tool_call("collect-pending-A", "get_command_or_subagent_output", {
                "task_ids": [self.manifest["steps"]["A"]["handle"]], "timeout_ms": 1000,
            }),
            tool_update("collect-pending-A", "completed", {"type": "TaskOutput", "Result": {
                "task_id": self.manifest["steps"]["A"]["handle"], "status": "pending",
            }}),
        ]
        first_collect = next(index for index, event in enumerate(events) if event.get("toolCallId") == "collect-1")
        events[first_collect:first_collect] = pending
        result = self.evaluate(events)
        self.assertTrue(result["passed"], result["errors"])

    def test_ignores_transient_collection_tool_failure_before_retry(self) -> None:
        events = valid_events(self.manifest)
        retry = [
            tool_call("collect-retry-A", "get_command_or_subagent_output", {
                "task_ids": [self.manifest["steps"]["A"]["handle"]], "timeout_ms": 1000,
            }),
            tool_update("collect-retry-A", "failed", {"type": "Text", "text": "temporary host transport failure"}),
        ]
        first_collect = next(index for index, event in enumerate(events) if event.get("toolCallId") == "collect-1")
        events[first_collect:first_collect] = retry
        result = self.evaluate(events)
        self.assertTrue(result["passed"], result["errors"])

    def test_accepts_equivalent_duplicate_completion_collection(self) -> None:
        events = valid_events(self.manifest)
        original = next(event for event in events if event.get("toolCallId") == "collect-1" and event["type"] == "tool_call_update")
        row = dict(original["rawOutput"]["MultiResult"]["results"][0])
        row["status"] = "COMPLETED"
        row["started"] = "2026-09-19T12:00:01.100+00:00"
        row["ended"] = "2026-09-19T12:00:07.900+00:00"
        retry = [
            tool_call("collect-repeat-A", "get_command_or_subagent_output", {
                "task_ids": [self.manifest["steps"]["A"]["handle"]], "timeout_ms": 1000,
            }),
            tool_update("collect-repeat-A", "completed", {"type": "TaskOutput", "Result": row}),
        ]
        first_import = next(index for index, event in enumerate(events)
                            if event.get("toolCallId") == "driver-import-handoff-A")
        events[first_import:first_import] = retry
        result = self.evaluate(events)
        self.assertTrue(result["passed"], result["errors"])

    def test_rejects_conflicting_successful_completion_identity(self) -> None:
        events = valid_events(self.manifest)
        original = next(event for event in events if event.get("toolCallId") == "collect-1" and event["type"] == "tool_call_update")
        row = dict(original["rawOutput"]["MultiResult"]["results"][0])
        row["ended"] = "2026-09-19T12:00:08.900Z"
        retry = [
            tool_call("collect-conflict-A", "get_command_or_subagent_output", {
                "task_ids": [self.manifest["steps"]["A"]["handle"]], "timeout_ms": 1000,
            }),
            tool_update("collect-conflict-A", "completed", {"type": "TaskOutput", "Result": row}),
        ]
        first_import = next(index for index, event in enumerate(events)
                            if event.get("toolCallId") == "driver-import-handoff-A")
        events[first_import:first_import] = retry
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("A has contradictory successful native completion records", "\n".join(result["errors"]))

    def test_rejects_timed_out_driver_terminal_result(self) -> None:
        events = valid_events(self.manifest)
        update = next(event for event in events if event.get("toolCallId") == "driver-start-A" and event["type"] == "tool_call_update")
        update["rawOutput"]["timed_out"] = True
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("A start terminal result timed_out is not false", "\n".join(result["errors"]))

    def test_rejects_signalled_driver_terminal_result(self) -> None:
        events = valid_events(self.manifest)
        update = next(event for event in events if event.get("toolCallId") == "driver-start-A" and event["type"] == "tool_call_update")
        update["rawOutput"]["signal"] = "SIGTERM"
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("A start terminal result signal is not null", "\n".join(result["errors"]))

    def test_rejects_echo_prefixed_driver_command(self) -> None:
        events = valid_events(self.manifest)
        call = next(event for event in events if event.get("toolCallId") == "driver-start-A" and event["type"] == "tool_call")
        call["rawInput"]["command"] = "echo " + call["rawInput"]["command"]
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("terminal command does not use the selected Python executable", "\n".join(result["errors"]))

    def test_rejects_wrong_native_driver_path(self) -> None:
        events = valid_events(self.manifest)
        call = next(event for event in events if event.get("toolCallId") == "driver-start-A" and event["type"] == "tool_call")
        call["rawInput"]["command"] = call["rawInput"]["command"].replace(
            self.manifest["driver_path"], "/forged/native_pilot.py",
        )
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("terminal command does not use the selected native_pilot.py path", "\n".join(result["errors"]))

    def test_rejects_noncanonical_per_step_handle_source(self) -> None:
        record = self.pilot / "handles" / f"B-{ATTEMPTS['B']}.json"
        value = json.loads(record.read_text(encoding="utf-8"))
        value["source"] = str(self.pilot / "A-handle.json")
        write_json(record, value)
        with self.assertRaisesRegex(TraceError, "native handle source for B is not its canonical retained handle path"):
            build_manifest(self.pilot)

    def test_rejects_parent_write_in_worker_workspace(self) -> None:
        events = valid_events(self.manifest)
        events.insert(1, tool_call("write-code", "write", {"target_file": str(Path(self.workspaces["A"]) / "toy/add.py")}))
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("parent write is not limited", "\n".join(result["errors"]))

    def test_rejects_parent_shell_authoring(self) -> None:
        events = valid_events(self.manifest)
        events.insert(1, tool_call("shell-code", "run_terminal_command", {"command": "printf x > toy/add.py"}))
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("parent_authoring", "\n".join(result["errors"]))

    def test_rejects_import_before_typed_collection(self) -> None:
        events = valid_events(self.manifest)
        import_index = next(index for index, event in enumerate(events) if event.get("toolCallId") == "driver-import-handoff-A")
        import_pair = [events.pop(import_index), events.pop(import_index)]
        first_collect = next(index for index, event in enumerate(events) if event.get("toolCallId") == "collect-1")
        events[first_collect:first_collect] = import_pair
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("import-handoff precedes completed native collection", "\n".join(result["errors"]))

    def test_rejects_c_or_j_dispatch_before_own_start_success(self) -> None:
        for step in ("C", "J"):
            with self.subTest(step=step):
                events = valid_events(self.manifest)
                update_index = next(index for index, event in enumerate(events)
                                    if event.get("toolCallId") == f"driver-start-{step}" and event["type"] == "tool_call_update")
                update = events.pop(update_index)
                spawn_index = next(index for index, event in enumerate(events)
                                   if event.get("toolCallId") == f"spawn-{step}" and event["type"] == "tool_call")
                events.insert(spawn_index + 1, update)
                result = self.evaluate(events)
                self.assertFalse(result["passed"])
                self.assertIn(f"{step} start success does not precede native dispatch", "\n".join(result["errors"]))

    def test_rejects_c_collection_before_spawn_receipt(self) -> None:
        events = valid_events(self.manifest)
        update_index = next(index for index, event in enumerate(events)
                            if event.get("toolCallId") == "spawn-C" and event["type"] == "tool_call_update")
        update = events.pop(update_index)
        collection_update_index = next(index for index, event in enumerate(events)
                                       if event.get("toolCallId") == "collect-3" and event["type"] == "tool_call_update")
        events.insert(collection_update_index + 1, update)
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("C collection started before its native dispatch receipt", "\n".join(result["errors"]))

    def test_rejects_j_launched_receipt_after_collection(self) -> None:
        events = valid_events(self.manifest)
        launched_index = next(index for index, event in enumerate(events)
                              if event.get("toolCallId") == "driver-launched-J" and event["type"] == "tool_call")
        launched_pair = [events.pop(launched_index), events.pop(launched_index)]
        collection_update_index = next(index for index, event in enumerate(events)
                                       if event.get("toolCallId") == "collect-4" and event["type"] == "tool_call_update")
        events[collection_update_index + 1:collection_update_index + 1] = launched_pair
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("J launched success does not precede native collection", "\n".join(result["errors"]))

    def test_rejects_sequential_a_b_intervals(self) -> None:
        events = valid_events(self.manifest)
        update = next(event for event in events if event.get("toolCallId") == "collect-2" and event["type"] == "tool_call_update")
        row = update["rawOutput"]["MultiResult"]["results"][0]
        row["started"] = "2026-09-19T12:00:08.100Z"
        row["ended"] = "2026-09-19T12:00:09.100Z"
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("execution intervals are sequential", "\n".join(result["errors"]))

    def test_rejects_a_b_without_precise_interval_telemetry(self) -> None:
        events = valid_events(self.manifest)
        update = next(event for event in events if event.get("toolCallId") == "collect-2" and event["type"] == "tool_call_update")
        row = update["rawOutput"]["MultiResult"]["results"][0]
        row["started"] = "2026-09-19T12:00:02Z"
        row["ended"] = "2026-09-19T12:00:08Z"
        result = self.evaluate(events)
        self.assertFalse(result["passed"])
        self.assertIn("lacks sub-second or monotonic precision", "\n".join(result["errors"]))

    def test_rejects_truncated_raw_json(self) -> None:
        path = self.root / "host.ndjson"
        path.write_text('{"type":"tool_call"\n', encoding="utf-8")
        with self.assertRaises(TraceError):
            evaluate_host_trace(path, self.pilot)


if __name__ == "__main__":
    unittest.main(verbosity=2)
