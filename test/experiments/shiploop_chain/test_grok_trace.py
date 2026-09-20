#!/usr/bin/env python3
"""Hermetic checks for the authoritative Grok root-transcript adapter."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GROK = _load("shiploop_grok_trace", "grok_trace.py")
_TRACE_TEST = _load("shiploop_native_trace_tests", "test_trace.py")

TraceError = _GROK.TraceError
build_manifest = _GROK.build_manifest
evaluate_grok_trace = _GROK.evaluate_grok_trace
normalize_root_updates = _GROK.normalize_root_updates
root_terminal = _GROK.root_terminal


ROOT = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
FOREIGN = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


def write_jsonl(path: Path, values: list[dict]) -> None:
    path.write_text("".join(json.dumps(value) + "\n" for value in values), encoding="utf-8")


def record(update: dict, *, session_id: str = ROOT, method: str = "session/update") -> dict:
    return {
        "timestamp": 1,
        "method": method,
        "params": {"sessionId": session_id, "update": update},
    }


def root_updates(events: list[dict], manifest: dict) -> list[dict]:
    """Represent evaluator fixtures in the Grok root ``updates.jsonl`` shape."""
    records: list[dict] = [record({"sessionUpdate": "agent_message_chunk", "content": {"type": "text", "text": "root"}})]
    calls: dict[str, dict] = {}
    for event in events:
        kind = event.get("type")
        if kind == "tool_call":
            call_id = event["toolCallId"]
            calls[call_id] = event
            records.append(record({
                "sessionUpdate": "tool_call",
                "toolCallId": call_id,
                "title": event["toolName"],
                "rawInput": event["rawInput"],
            }))
        elif kind == "tool_call_update":
            call_id = event["toolCallId"]
            update = {
                "sessionUpdate": "tool_call_update",
                "toolCallId": call_id,
                "status": event.get("status"),
            }
            if "rawOutput" in event:
                update["rawOutput"] = event["rawOutput"]
            records.append(record(update))
            call = calls.get(call_id)
            if (call and call["toolName"] == "spawn_subagent" and event.get("status") == "completed"):
                workspace = call["rawInput"]["cwd"]
                step = next(name for name, detail in manifest["steps"].items() if detail["workspace"] == workspace)
                handle = manifest["steps"][step]["handle"]
                records.append(record({
                    "sessionUpdate": "subagent_spawned",
                    "subagent_id": handle,
                    "child_session_id": handle,
                    "parent_session_id": ROOT,
                    "attempt_id": f"at-{step}",
                    "effective_context_source": "new",
                    "description": f"ShipLoop step {step}",
                }))
    return records


class GrokRootTraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.pilot, _ = _TRACE_TEST.make_pilot(self.root)
        self.manifest = build_manifest(self.pilot)
        self.updates_path = self.root / "updates.jsonl"
        self.host_path = self.root / "host.ndjson"
        self.updates = root_updates(_TRACE_TEST.valid_events(self.manifest), self.manifest)
        write_jsonl(self.updates_path, self.updates)
        self.write_host()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_host(self, *, unlabelled: bool = False, child_noise: bool = False,
                   post_terminal_call: str | None = None) -> None:
        values: list[dict] = [
            {"type": "end", "stopReason": "error", "sessionId": FOREIGN},
        ]
        if child_noise:
            values.extend((
                {"type": "tool_call", "sessionId": self.manifest["steps"]["A"]["handle"], "toolName": "write",
                 "toolCallId": "child-write", "rawInput": {"target_file": "/outside/root.py"}},
                {"type": "text", "sessionId": self.manifest["steps"]["A"]["handle"], "text": "child stdout noise"},
            ))
        terminal = {"type": "end", "stopReason": "end_turn"}
        if not unlabelled:
            terminal["sessionId"] = ROOT
        values.append(terminal)
        if post_terminal_call is not None:
            values.append({
                "type": "tool_call", "toolCallId": post_terminal_call,
                "toolName": "write", "rawInput": {"target_file": "/after-root-end.py"},
            })
        write_jsonl(self.host_path, values)

    def evaluate(self) -> dict:
        return evaluate_grok_trace(self.host_path, self.updates_path, ROOT, self.pilot)

    def test_valid_root_transcript_feeds_existing_evaluator(self) -> None:
        result = self.evaluate()
        self.assertTrue(result["passed"], result["errors"])
        self.assertEqual(set(result["subagent_bindings"]), {
            detail["handle"] for detail in self.manifest["steps"].values()
        })
        self.assertTrue(result["root_terminal"]["complete"])

    def test_rejects_foreign_session_record(self) -> None:
        records = copy.deepcopy(self.updates)
        records[0]["params"]["sessionId"] = FOREIGN
        write_jsonl(self.updates_path, records)
        with self.assertRaisesRegex(TraceError, "foreign or unlabelled session"):
            normalize_root_updates(self.updates_path, ROOT, self.manifest)

    def test_rejects_missing_or_wrong_spawn_binding(self) -> None:
        records = copy.deepcopy(self.updates)
        mapping_index = next(index for index, item in enumerate(records)
                             if item["params"]["update"]["sessionUpdate"] == "subagent_spawned")
        with self.subTest("missing"):
            missing = records[:mapping_index] + records[mapping_index + 1:]
            write_jsonl(self.updates_path, missing)
            with self.assertRaisesRegex(TraceError, "lacks host subagent_spawned bindings"):
                normalize_root_updates(self.updates_path, ROOT, self.manifest)
        with self.subTest("wrong-child"):
            wrong = copy.deepcopy(records)
            wrong[mapping_index]["params"]["update"]["child_session_id"] = FOREIGN
            write_jsonl(self.updates_path, wrong)
            with self.assertRaisesRegex(TraceError, "incompatible child session"):
                normalize_root_updates(self.updates_path, ROOT, self.manifest)

    def test_rejects_malformed_and_truncated_transcript(self) -> None:
        with self.subTest("malformed"):
            self.updates_path.write_text("{\n", encoding="utf-8")
            with self.assertRaisesRegex(TraceError, "invalid JSON"):
                normalize_root_updates(self.updates_path, ROOT, self.manifest)
        with self.subTest("truncated-before-fourth-binding"):
            fourth = [index for index, item in enumerate(self.updates)
                      if item["params"]["update"]["sessionUpdate"] == "subagent_spawned"][3]
            write_jsonl(self.updates_path, self.updates[:fourth])
            with self.assertRaisesRegex(TraceError, "lacks host subagent_spawned bindings"):
                normalize_root_updates(self.updates_path, ROOT, self.manifest)

    def test_parent_forbidden_mutation_remains_visible(self) -> None:
        records = copy.deepcopy(self.updates)
        records.insert(1, record({
            "sessionUpdate": "tool_call",
            "toolCallId": "parent-write-outside-handle",
            "title": "write",
            "rawInput": {"target_file": str(self.root / "outside-handle.json"), "content": "blocked"},
        }))
        write_jsonl(self.updates_path, records)
        result = self.evaluate()
        self.assertFalse(result["passed"])
        self.assertTrue(any(error.startswith("parent_authoring:") for error in result["errors"]), result["errors"])

    def test_child_stdout_noise_and_child_tools_do_not_become_parent_events(self) -> None:
        self.write_host(child_noise=True)
        records = copy.deepcopy(self.updates)
        records.insert(1, record({
            "sessionUpdate": "subagent_finished",
            "child_session_id": self.manifest["steps"]["A"]["handle"],
            "output": "child says it wrote an unrelated file",
        }))
        write_jsonl(self.updates_path, records)
        result = self.evaluate()
        self.assertTrue(result["passed"], result["errors"])

    def test_root_terminal_ignores_foreign_end_but_unlabelled_root_cannot_pass(self) -> None:
        terminal = root_terminal(self.host_path, ROOT)
        self.assertTrue(terminal["complete"])
        self.assertEqual(terminal["stop_reason"], "end_turn")
        self.write_host(unlabelled=True)
        terminal = root_terminal(self.host_path, ROOT)
        self.assertFalse(terminal["complete"])
        self.assertEqual(terminal["root_end_count"], 0)
        with self.assertRaisesRegex(TraceError, "root-labelled end_turn"):
            self.evaluate()

    def test_final_turn_completed_is_passive_and_cannot_replace_raw_root_end(self) -> None:
        records = copy.deepcopy(self.updates)
        records.append(record({
            "sessionUpdate": "turn_completed",
            "prompt_id": "prompt-1",
            "stop_reason": "end_turn",
            "elapsed_ms": 1,
        }, method="_x.ai/session/update"))
        write_jsonl(self.updates_path, records)
        self.assertTrue(self.evaluate()["passed"])
        self.write_host(unlabelled=True)
        with self.assertRaisesRegex(TraceError, "root-labelled end_turn"):
            self.evaluate()

    def test_rejects_root_tool_observed_after_root_terminal(self) -> None:
        root_call = next(item["params"]["update"]["toolCallId"] for item in self.updates
                         if item["params"]["update"]["sessionUpdate"] == "tool_call")
        self.write_host(post_terminal_call=root_call)
        with self.assertRaisesRegex(TraceError, "root tool activity after its terminal event"):
            self.evaluate()

    def test_allows_unbound_child_tool_observed_after_root_terminal(self) -> None:
        self.write_host(post_terminal_call="child-tool-after-root-end")
        result = self.evaluate()
        self.assertTrue(result["passed"], result["errors"])


if __name__ == "__main__":
    unittest.main()
