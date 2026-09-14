#!/usr/bin/env python3
"""Focused checks for the opt-in managed graph-trace test helper."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
WALK = ROOT / "test" / "shiploop-managed-walk.test.py"


def load_walk_helpers():
    loader = importlib.machinery.SourceFileLoader(
        "shiploop_graph_trace_walk_helpers", str(WALK)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError(f"could not load {WALK}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return module


WALK_HELPERS = load_walk_helpers()


def node(stage, *, action="A-1", step=None, status="active"):
    return {
        "phase": "implement" if step else "outer",
        "stage": stage,
        "action": action,
        "active_step": step,
        "status": status,
        "paused": False,
        "profile": None,
    }


def frame(parent_stage, *, effective_stage=None, step=None):
    parent = node(parent_stage, action="P-1", step=step)
    effective = node(
        effective_stage or parent_stage,
        action="C-1" if effective_stage else "P-1",
        step=step,
    )
    return {
        "durable_parent": parent,
        "effective": effective,
        "child": effective if effective_stage else None,
        "effective_source": "managed-child" if effective_stage else "parent",
    }


class GraphTraceHelperTests(unittest.TestCase):
    def test_actual_shaped_child_snapshot_preserves_controller_cursor(self):
        child = {
            "profile": "step-plan",
            "status": "active",
            "current_phase": "step-plan-disposition",
            "paused": True,
            "execution": {
                "phase": "step-plan-disposition",
                "stage": "step-plan-disposition",
                "action": "MI-STEP-PLAN-DISPOSITION-001",
                "completed_actions": [],
                "overlay": {"set": {}, "delete": []},
            },
        }
        with tempfile.TemporaryDirectory(prefix="shiploop-child-snapshot-") as tmp:
            run_dir = Path(tmp) / ".shiploop"
            WALK_HELPERS.store.write_record(
                run_dir / "state.md",
                {
                    "phase": "implement",
                    "stage": "managed-improve",
                    "action": {"id": "PARENT-STEP-PLAN-001", "stage": "managed-improve"},
                    "managed_improve": {"receipt": "managed-improve/child.md"},
                },
            )
            WALK_HELPERS.store.write_record(
                run_dir / "managed-improve" / "child.md", {"child": child}
            )
            snapshot = WALK_HELPERS.graph_trace_snapshot(run_dir)
        self.assertEqual(snapshot["child"], {
            "phase": "step-plan-disposition",
            "stage": "step-plan-disposition",
            "action": "MI-STEP-PLAN-DISPOSITION-001",
            "active_step": None,
            "status": "active",
            "paused": True,
            "profile": "step-plan",
        })

    def test_disabled_cli_delegates_without_trace_snapshots(self):
        fixture = object.__new__(WALK_HELPERS.ManagedShipLoopWalkFixture)
        fixture.graph_trace = WALK_HELPERS.ManagedGraphTrace(None)
        expected = object()
        with patch.object(
            WALK_HELPERS.ACTION.ShipLoopActionWalkFixture,
            "cli",
            return_value=expected,
        ) as base_cli, patch.object(
            WALK_HELPERS,
            "graph_trace_snapshot",
            side_effect=AssertionError("disabled tracing must not snapshot"),
        ):
            actual = fixture.cli("next", code=2, cwd=Path("/fixture"))
        self.assertIs(actual, expected)
        base_cli.assert_called_once_with("next", code=2, cwd=Path("/fixture"))

    def test_writer_is_exclusive_and_preserves_rejected_command_output(self):
        with tempfile.TemporaryDirectory(prefix="shiploop-graph-trace-") as tmp:
            path = Path(tmp) / "managed-walk.jsonl"
            self.assertEqual(
                WALK_HELPERS.graph_trace_snapshot(Path(tmp) / "not-initialized"),
                {
                    "durable_parent": None,
                    "effective": None,
                    "child": None,
                    "effective_source": "unavailable",
                },
            )
            trace = WALK_HELPERS.ManagedGraphTrace(path)
            before = frame("managed-improve", effective_stage="step-plan-review", step="S1")
            record = WALK_HELPERS.graph_trace_command_record(
                sequence=1,
                command="complete",
                before=before,
                after=before,
                exit_status=2,
                stdout="Current prompt: resolve the scope disposition.\n",
                stderr="error: stale child action\n",
            )
            trace.append(record)

            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["stdout"], "Current prompt: resolve the scope disposition.\n")
            self.assertEqual(rows[0]["stderr"], "error: stale child action\n")
            self.assertEqual(trace.records, [{
                "type": "command",
                "sequence": 1,
                "after": before,
            }])
            self.assertEqual(rows[0]["transition"], {
                "outcome": "rejected",
                "rejected": True,
                "blocked": False,
                "same_effective_node": True,
            })
            self.assertTrue(rows[0]["synthetic_fixture"])
            self.assertEqual(rows[0]["execution_scope"], "temporary integration fixture")
            self.assertNotIn("argv", rows[0])
            self.assertNotIn("result", rows[0])
            self.assertNotIn("successful_terminal_proof", rows[0])
            with self.assertRaisesRegex(RuntimeError, "already exists"):
                WALK_HELPERS.ManagedGraphTrace(path)

    def test_blocked_and_unchanged_are_distinct(self):
        before = frame("managed-improve", effective_stage="step-plan-disposition", step="S1")
        paused = json.loads(json.dumps(before))
        paused["child"]["paused"] = True
        paused["effective"]["paused"] = True
        blocked = WALK_HELPERS.graph_trace_command_record(
            sequence=1,
            command="repair",
            before=before,
            after=paused,
            exit_status=0,
            stdout="paused\n",
            stderr="",
        )
        unchanged = WALK_HELPERS.graph_trace_command_record(
            sequence=2,
            command="next",
            before=before,
            after=before,
            exit_status=0,
            stdout="Current prompt\n",
            stderr="",
        )
        self.assertEqual(blocked["transition"]["outcome"], "blocked")
        self.assertTrue(blocked["transition"]["blocked"])
        self.assertEqual(unchanged["transition"]["outcome"], "unchanged")
        self.assertTrue(unchanged["transition"]["same_effective_node"])

    def test_terminal_summary_requires_passed_done_walk(self):
        unfinished = frame("handoff")
        with self.assertRaisesRegex(ValueError, "completed walk assertions"):
            WALK_HELPERS.graph_trace_terminal_summary(
                unfinished, command_records=3, walk_assertions_passed=False
            )
        with self.assertRaisesRegex(ValueError, "durable done state"):
            WALK_HELPERS.graph_trace_terminal_summary(
                unfinished, command_records=3, walk_assertions_passed=True
            )
        summary = WALK_HELPERS.graph_trace_terminal_summary(
            frame("done"), command_records=8, walk_assertions_passed=True
        )
        self.assertTrue(summary["successful_terminal_proof"])
        self.assertEqual(summary["terminal"]["durable_parent"]["stage"], "done")

    def test_high_level_order_uses_observed_stage_and_step_ids(self):
        records = [
            {"type": "command", "after": frame("preflight")},
            {"type": "command", "after": frame("approach")},
            {
                "type": "command",
                "after": frame(
                    "managed-improve", effective_stage="step-plan-review", step="S1"
                ),
            },
            {
                "type": "command",
                "after": frame(
                    "managed-improve", effective_stage="step-plan-review", step="S2"
                ),
            },
            {"type": "command", "after": frame("coverage")},
            {"type": "command", "after": frame("quality")},
            {"type": "command", "after": frame("handoff")},
            {"type": "command", "after": frame("done")},
        ]
        WALK_HELPERS.assert_graph_trace_high_level_order(records)

        reversed_steps = [record for record in records if record["after"]["effective"]["active_step"] != "S1"]
        with self.assertRaisesRegex(AssertionError, "S1"):
            WALK_HELPERS.assert_graph_trace_high_level_order(reversed_steps)


if __name__ == "__main__":
    unittest.main()
