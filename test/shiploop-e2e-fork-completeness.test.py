#!/usr/bin/env python3
"""Unit tests for test/shiploop_e2e/fork_completeness.py and its metrics.py wiring."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))

import fork_completeness  # noqa: E402
import metrics  # noqa: E402


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def _fc(ts: str, call_id: str, name: str, args: dict) -> dict:
    return {
        "timestamp": ts,
        "type": "response_item",
        "payload": {"type": "function_call", "call_id": call_id, "name": name, "arguments": json.dumps(args)},
    }


def _fco(ts: str, call_id: str, out: dict) -> dict:
    return {
        "timestamp": ts,
        "type": "response_item",
        "payload": {"type": "function_call_output", "call_id": call_id, "output": json.dumps(out)},
    }


def _exec(ts: str, cmd: str) -> dict:
    return {
        "timestamp": ts,
        "type": "response_item",
        "payload": {"type": "custom_tool_call", "name": "exec", "input": cmd},
    }


class ForkCompletenessTests(unittest.TestCase):
    def test_no_rollouts_or_zero_spawns_returns_none_and_leaves_summary_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.assertIsNone(fork_completeness.collect(out))
            collected = metrics.collect(out)
            self.assertNotIn("fork_completeness", collected)
            _write_jsonl(out / "home/.codex/sessions/rollout-parent.jsonl", [
                {"timestamp": "2026-11-24T19:00:00Z", "type": "session_meta", "payload": {"id": "root-1"}},
                _exec("2026-11-24T19:00:05Z", "python3 shiploop complete"),
            ])
            self.assertIsNone(fork_completeness.collect(out))
            self.assertFalse(any(l.startswith("fork completeness:") for l in metrics.summary_lines(metrics.collect(out))))

    def test_clean_forked_and_fresh_run_ignores_inherited_history_and_prose_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_dir = out / "run"
            wt = out / "worktree"
            for name in ("spec-1", "document-2"):
                p = wt / ".shiploop-improve" / name / "packet.json"
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(json.dumps({"status": "complete"}), encoding="utf-8")

            _write_jsonl(run_dir / "trace.jsonl", [
                {"ts": 1000.0, "kind": "packet", "stage": "improve", "reviewed": "spec"},
                {"ts": 1020.0, "kind": "command", "verb": "complete"},
                {"ts": 1030.0, "kind": "packet", "stage": "improve", "reviewed": "document"},
                {"ts": 1050.0, "kind": "command", "verb": "complete"},
            ])
            _write_jsonl(out / "home/.codex/sessions/rollout-0-parent.jsonl", [
                {"timestamp": "1970-01-01T00:16:30Z", "type": "session_meta", "payload": {"id": "p1"}},
                _fc("1970-01-01T00:16:41Z", "c1", "spawn_agent", {"task_name": "spec_rev", "fork_turns": "all"}),
                _fco("1970-01-01T00:16:41.100Z", "c1", {"task_name": "/root/spec_rev"}),
                _fc("1970-01-01T00:16:42Z", "w1", "wait_agent", {"timeout_ms": 120000}),
                _fco("1970-01-01T00:16:59Z", "w1", {"timed_out": False}),
                _fc("1970-01-01T00:17:11Z", "c2", "spawn_agent", {"task_name": "doc_rev", "fork_turns": "none"}),
                _fco("1970-01-01T00:17:11.100Z", "c2", {"task_name": "/root/doc_rev"}),
                _fc("1970-01-01T00:17:12Z", "w2", "wait_agent", {"timeout_ms": 120000}),
                _fco("1970-01-01T00:17:29Z", "w2", {"timed_out": False}),
            ])
            # Forked child carries pre-fork parent spawn_agent + shiploop complete before thread_settings_applied
            _write_jsonl(out / "home/.codex/sessions/rollout-1-spec.jsonl", [
                {"timestamp": "1970-01-01T00:16:41Z", "type": "session_meta",
                 "payload": {"id": "ch1", "agent_path": "/root/spec_rev", "source": {"subagent": "fork"}}},
                _fc("1970-01-01T00:16:41Z", "old", "spawn_agent", {"task_name": "old"}),
                _exec("1970-01-01T00:16:41Z", "python3 shiploop complete"),
                {"timestamp": "1970-01-01T00:16:41.200Z", "type": "event_msg", "payload": {"type": "thread_settings_applied"}},
                _exec("1970-01-01T00:16:50Z", "cat > review-1.md <<'EOF'\nreview complete without calling shiploop\nEOF"),
                {"timestamp": "1970-01-01T00:16:58Z", "type": "event_msg", "payload": {"type": "task_complete"}},
            ])
            _write_jsonl(out / "home/.codex/sessions/rollout-2-doc.jsonl", [
                {"timestamp": "1970-01-01T00:17:11Z", "type": "session_meta",
                 "payload": {"id": "ch2", "agent_path": "/root/doc_rev", "source": {"subagent": "spawn"}}},
                {"timestamp": "1970-01-01T00:17:11.200Z", "type": "event_msg", "payload": {"type": "thread_settings_applied"}},
                _exec("1970-01-01T00:17:20Z", "python3 shiploop improve-pass"),
                {"timestamp": "1970-01-01T00:17:28Z", "type": "event_msg", "payload": {"type": "task_complete"}},
            ])

            res = fork_completeness.collect(out, run_dir)
            self.assertEqual(res["spawns"], 2)
            self.assertEqual(res["completed"], 2)
            self.assertEqual(res["order_ok"], 2)
            self.assertEqual(res["interrupted"], 0)
            self.assertEqual(res["abandoned"], 0)
            self.assertEqual(res["nested_spawns"], 0)
            self.assertEqual(res["child_completes"], 0)
            self.assertEqual(res["waits"], 2)
            self.assertEqual(res["wait_timeouts"], 0)
            self.assertEqual(res["packets_complete"], 2)
            self.assertEqual(res["packets_total"], 2)
            line = fork_completeness.summary_line(res)
            self.assertEqual(
                line,
                "fork completeness: 2/2 completed (2/2 order_ok, 0 interrupted, 0 abandoned), "
                "waits 2 (0 timeouts), nested_spawns 0, child_completes 0, packets 2/2 complete",
            )
            collected = metrics.collect(out, run_dir)
            self.assertIn("fork_completeness", collected)
            self.assertIn(line, metrics.summary_lines(collected))

    def test_explicit_interrupt_and_recovery_not_counted_as_abandoned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_dir = out / "run"
            _write_jsonl(run_dir / "trace.jsonl", [
                {"ts": 1000.0, "kind": "packet", "stage": "improve", "reviewed": "release-plan"},
                {"ts": 1060.0, "kind": "command", "verb": "complete"},
            ])
            _write_jsonl(out / "home/.codex/sessions/rollout-0-parent.jsonl", [
                {"timestamp": "1970-01-01T00:16:40Z", "type": "session_meta", "payload": {"id": "p1"}},
                _fc("1970-01-01T00:16:41Z", "c1", "spawn_agent", {"task_name": "release_review", "fork_turns": "all"}),
                _fco("1970-01-01T00:16:41.100Z", "c1", {"task_name": "/root/release_review"}),
                _fc("1970-01-01T00:16:42Z", "w1", "wait_agent", {"timeout_ms": 120000}),
                _fco("1970-01-01T00:17:02Z", "w1", {"timed_out": True}),
                _fc("1970-01-01T00:17:03Z", "i1", "interrupt_agent", {"target": "release_review"}),
                _fco("1970-01-01T00:17:03.100Z", "i1", {"previous_status": "running"}),
                _fc("1970-01-01T00:17:05Z", "c2", "spawn_agent", {"task_name": "release_recovery", "fork_turns": "none"}),
                _fco("1970-01-01T00:17:05.100Z", "c2", {"task_name": "/root/release_recovery"}),
                _fc("1970-01-01T00:17:06Z", "w2", "wait_agent", {"timeout_ms": 120000}),
                _fco("1970-01-01T00:17:35Z", "w2", {"timed_out": False}),
            ])
            _write_jsonl(out / "home/.codex/sessions/rollout-1-stall.jsonl", [
                {"timestamp": "1970-01-01T00:16:41Z", "type": "session_meta",
                 "payload": {"id": "ch1", "agent_path": "/root/release_review", "source": {"subagent": "fork"}}},
                {"timestamp": "1970-01-01T00:16:41.200Z", "type": "event_msg", "payload": {"type": "thread_settings_applied"}},
                {"timestamp": "1970-01-01T00:17:03.200Z", "type": "event_msg", "payload": {"type": "turn_aborted"}},
            ])
            _write_jsonl(out / "home/.codex/sessions/rollout-2-recov.jsonl", [
                {"timestamp": "1970-01-01T00:17:05Z", "type": "session_meta",
                 "payload": {"id": "ch2", "agent_path": "/root/release_recovery", "source": {"subagent": "spawn"}}},
                {"timestamp": "1970-01-01T00:17:05.200Z", "type": "event_msg", "payload": {"type": "thread_settings_applied"}},
                {"timestamp": "1970-01-01T00:17:34Z", "type": "event_msg", "payload": {"type": "task_complete"}},
            ])

            res = fork_completeness.collect(out, run_dir)
            self.assertEqual(res["spawns"], 2)
            self.assertEqual(res["completed"], 1)
            self.assertEqual(res["order_ok"], 1)
            self.assertEqual(res["interrupted"], 1)
            self.assertEqual(res["abandoned"], 0)
            self.assertEqual(res["wait_timeouts"], 1)

    def test_detects_abandoned_out_of_order_nested_spawn_and_child_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_dir = out / "run"
            _write_jsonl(run_dir / "trace.jsonl", [
                {"ts": 1000.0, "kind": "packet", "stage": "improve", "reviewed": "plan"},
                {"ts": 1015.0, "kind": "command", "verb": "complete"},  # earlier than child #1 task_complete!
            ])
            _write_jsonl(out / "home/.codex/sessions/rollout-0-parent.jsonl", [
                {"timestamp": "1970-01-01T00:16:40Z", "type": "session_meta", "payload": {"id": "p1"}},
                _fc("1970-01-01T00:16:41Z", "c1", "spawn_agent", {"task_name": "bad1", "fork_turns": "all"}),
                _fco("1970-01-01T00:16:41.100Z", "c1", {"task_name": "/root/bad1"}),
                _fc("1970-01-01T00:16:42Z", "w1", "wait_agent", {"timeout_ms": 120000}),
                _fco("1970-01-01T00:17:00Z", "w1", {"timed_out": False}),
                _fc("1970-01-01T00:17:05Z", "c2", "spawn_agent", {"task_name": "abandoned", "fork_turns": "none"}),
                _fco("1970-01-01T00:17:05.100Z", "c2", {"task_name": "/root/abandoned"}),
            ])
            _write_jsonl(out / "home/.codex/sessions/rollout-1-bad1.jsonl", [
                {"timestamp": "1970-01-01T00:16:41Z", "type": "session_meta",
                 "payload": {"id": "ch1", "agent_path": "/root/bad1", "source": {"subagent": "fork"}}},
                {"timestamp": "1970-01-01T00:16:41.200Z", "type": "event_msg", "payload": {"type": "thread_settings_applied"}},
                _fc("1970-01-01T00:16:45Z", "ns1", "spawn_agent", {"task_name": "nested"}),
                _exec("1970-01-01T00:16:46Z", "python3 '/tmp/scripts/shiploop' complete --action a1"),
                {"timestamp": "1970-01-01T00:16:59Z", "type": "event_msg", "payload": {"type": "task_complete"}},
            ])
            _write_jsonl(out / "home/.codex/sessions/rollout-2-abandoned.jsonl", [
                {"timestamp": "1970-01-01T00:17:05Z", "type": "session_meta",
                 "payload": {"id": "ch2", "agent_path": "/root/abandoned", "source": {"subagent": "spawn"}}},
                {"timestamp": "1970-01-01T00:17:05.200Z", "type": "event_msg", "payload": {"type": "thread_settings_applied"}},
                _exec("1970-01-01T00:17:08Z", "echo still running"),
            ])

            res = fork_completeness.collect(out, run_dir)
            self.assertEqual(res["spawns"], 2)
            self.assertEqual(res["completed"], 1)
            self.assertEqual(res["order_ok"], 0)  # trace complete (1015) preceded child task_complete (1019)
            self.assertEqual(res["interrupted"], 0)
            self.assertEqual(res["abandoned"], 1)
            self.assertEqual(res["nested_spawns"], 1)
            self.assertEqual(res["child_completes"], 1)


if __name__ == "__main__":
    unittest.main()
