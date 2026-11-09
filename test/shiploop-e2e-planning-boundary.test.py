#!/usr/bin/env python3
"""Hermetic controls for the repository's recorded Plan Improve boundary."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent / "shiploop_e2e"))
import metrics  # noqa: E402
import planning_boundary as boundary  # noqa: E402

RUN = "nav-" + "a" * 32
PLAN = "nav-" + "b" * 32
IMPROVE = "nav-" + "c" * 32
PREPARE = "nav-" + "d" * 32
SPEC = "nav-" + "e" * 32
STRATEGY = "nav-" + "f" * 32


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def jsonl(path: Path, rows) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def shell_pair(tool_id: str, command: str, output: str, start: float, end: float) -> list:
    return [
        (start, {"type": "tool_call", "toolCallId": tool_id, "toolName": "run_terminal_command",
                 "status": "pending", "rawInput": {"command": command}}),
        (end, {"type": "tool_call_update", "toolCallId": tool_id, "status": "completed",
               "rawOutput": {"type": "command_execution", "exit_code": 0,
                             "output_for_prompt": output, "command": command}}),
    ]


def engine_command(ts: float, verb: str, action: str, rev: list, stage: list, cursor: list, **extra) -> dict:
    return {"v": 1, "kind": "command", "ts": ts, "verb": verb, "action": action, "rev": rev,
            "stage": stage, "cursor": cursor, "status": "active", "exit": 0, **extra}


class PlanningFixture:
    """The relevant sample-05 shapes with synthetic identities and content."""

    def __init__(self, out: Path):
        self.out = out
        self.run = out / ".shiploop-runs" / "seed" / "run"
        self.run.mkdir(parents=True)
        self.workspace = self.run.parent / "worktree"
        self.cli = out / "install/skills/shiploop/scripts/shiploop"
        self.runtime = self.cli.parents[2] / "improve/runtime/until-loop/scripts/until_loop_ephemeral.py"
        self.child_dir = self.workspace / ".shiploop-improve" / ("plan-" + PLAN[-8:])
        self.child_state = self.run / "until-loop/innerloop-abcd.json"
        self.report = self.child_dir / "reviews/report-2.json"
        self.report.parent.mkdir(parents=True)
        self.report_data = {"classification": "trivial", "exit_assessment": "satisfied",
                            "continuation_assessment": "allowed", "evidence": "Review evidence", "handoff": "Handoff"}
        self.report.write_text(json.dumps(self.report_data, indent=1) + "\n", encoding="utf-8")
        report_canonical = json.dumps(self.report_data, sort_keys=True, separators=(",", ":"))
        self.terminal = json.dumps({"status": "complete", "state_file": str(self.child_state),
                                    "workspace": str(self.workspace), "progress": {"action_number": 2},
                                    "context": {"request": f"ShipLoop standalone Improve binding: {RUN}/{PLAN}\nReview."},
                                    "receipt": str(self.child_dir / "packet.json"), "last_report": self.report_data,
                                    "next_argv": None, "done_argv": None, "report_schema": None},
                                   separators=(",", ":")) + "\n"
        self.receipt = {"binding_id": f"{RUN}/{PLAN}", "workspace": str(self.workspace), "action_id": PLAN,
                        "stage": "plan", "runtime_phase": "complete", "improve_action": IMPROVE,
                        "skill": {"runtime_cli": str(self.runtime)},
                        "identities": {"terminal_packet_sha256": digest(self.terminal.encode()),
                                       "last_report_sha256": digest(report_canonical.encode())},
                        "receipt": {"final_result": {"outcome": "done"}}}
        self.history = [{"action": action, "stage": stage, "outcome": "done", "workitem": None}
                        for action, stage in ((SPEC, "spec"), (STRATEGY, "test-strategy"), (PLAN, "plan"))]
        self.state = {"run_id": RUN, "revision": 9, "status": "active", "stage": "prepare",
                      "action": {"id": PREPARE, "stage": "prepare"}, "repo": str(self.workspace),
                      "history": self.history, "accepted": {PLAN: {"outcome": "done"}},
                      "improve_results": {PLAN: self.receipt}, "completed_work_items": []}
        self.engine_times = {SPEC: "1970-01-01T00:16:39Z", STRATEGY: "1970-01-01T00:16:41Z",
                             PLAN: "1970-01-01T00:16:44Z"}
        self.final_result = self.run / "inbox" / (PLAN + "-final-result.md")
        self.parent_command = (f"/bin/zsh -lc 'python3 {self.cli} complete --run-dir={self.run} "
                               f"--action={IMPROVE} --final-result={self.final_result}'")
        self.child_bare = (f"/usr/bin/python3 {self.runtime} done --state {self.child_state} "
                           f"--action=runtime-action:2 < {self.report}")
        self.child_command = f"/bin/zsh -lc '{self.child_bare}'"
        self.prepare_packet = (f"ShipLoop navigator | prepare | revision 9\n"
                               f"Full packet: {self.run / 'packets' / (PREPARE + '.md')} - open it with a file tool\n"
                               f"Callback for this stage: python3 {self.cli} complete --run-dir={self.run} --action={PREPARE}\n"
                               f"Keepalive marker: SHIPLOOP-RUN run={RUN} rev=9 dir={self.run}\n")
        self.events = [(1000.100, {"type": "available_commands", "sessionId": "thread-1"}),
                       (1001.900, {"type": "text", "data": "Starting the Plan."})]
        self.events.extend(shell_pair("pass", f"python3 {self.cli} improve-pass --run-dir {self.run} --action {IMPROVE}",
                                     "Pass 2 of the plan review is recorded.\n" + self.child_bare + "\n",
                                     1003.600, 1003.810))
        self.events.extend(shell_pair("child", self.child_command, self.terminal, 1004.394, 1004.394))
        self.events.extend(shell_pair("parent", self.parent_command, self.prepare_packet, 1004.665, 1005.040))
        self.trace = [
            engine_command(1002.7, "complete", PLAN, [7, 8], ["plan", "improve"], [PLAN, IMPROVE]),
            engine_command(1003.806, "improve-pass", IMPROVE, [8, 8], ["improve", "improve"], [IMPROVE, IMPROVE]),
            {"v": 1, "kind": "packet", "ts": 1005.029, "stage": "prepare", "action": PREPARE, "rev": 9},
            engine_command(1005.034, "complete", IMPROVE, [8, 9], ["improve", "prepare"], [IMPROVE, PREPARE],
                           accepted=[{"action": PLAN, "stage": "plan", "item": None, "outcome": "done"}]),
        ]
        self.launch_split = None

    def event(self, tool_id: str, kind: str) -> dict:
        return next(event for _, event in self.events if event.get("toolCallId") == tool_id and event["type"] == kind)

    def command(self, tool_id: str, replacement: str) -> None:
        self.event(tool_id, "tool_call")["rawInput"]["command"] = replacement
        self.event(tool_id, "tool_call_update")["rawOutput"]["command"] = replacement

    def write(self) -> None:
        jsonl(self.out / "events.jsonl", (event for _, event in self.events))
        jsonl(self.out / "timeline.jsonl", ({"line": i, "t": when} for i, (when, event) in enumerate(self.events)
                                          if event["type"] not in ("text", "thought")))
        boundaries = [0, len(self.events)] if self.launch_split is None else [0, self.launch_split, len(self.events)]
        launches = []
        for n, (first, last) in enumerate(zip(boundaries, boundaries[1:]), 1):
            told = {"run_dir": str(self.run), "cli": str(self.cli)} if n > 1 else None
            launches += [{"row": "start", "n": n, "kind": "continued" if n > 1 else "first", "events_line": first,
                          "host": "codex", "told": told, "t": self.events[first][0] - 0.001},
                         {"row": "end", "n": n, "events_line": last, "t": self.events[last - 1][0] + 0.001,
                          "status": "interrupted", "returncode": -9}]
        jsonl(self.out / "sessions.jsonl", launches)
        jsonl(self.run / "trace.jsonl", self.trace)
        (self.run / "state.md").write_text("```shiploop-state\n" + json.dumps(self.state) + "\n```\n", encoding="utf-8")
        (self.run / "timeline.json").write_text(json.dumps({"accepted": self.engine_times}), encoding="utf-8")
        (self.out / "invocation.json").write_text(json.dumps({
            "kind": "step-slice", "host": "codex", "plugin": {"pass": True, "path": str(self.cli.parents[3])},
            "seeded": {"run_dir": str(self.run)}, "stop_after": "plan",
        }), encoding="utf-8")

    def read(self, **kwargs) -> dict:
        self.write()
        return boundary.analyze(self.out, self.run, self.cli, **kwargs)


class PlanningBoundaryTest(unittest.TestCase):
    def fixture(self) -> PlanningFixture:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        return PlanningFixture(Path(folder.name).resolve())

    def test_two_sample_shaped_callbacks_conserve_calls_and_leave_timing_in_place(self):
        fixture = self.fixture()
        got = fixture.read(run_id=RUN)
        self.assertEqual(got["status"], "established", got)
        self.assertEqual({row["kind"] for row in got["corrections"]}, {"parent-complete", "bound-child-done"})
        self.assertEqual(got["acceptance"]["prepare_packet_trace_line"], 3)
        self.assertEqual(got["later_calls"], [])
        self.assertEqual(got["sources"]["sha256"]["events"], digest((fixture.out / "events.jsonl").read_bytes()))
        tools = metrics.ToolLog()
        collected = metrics.collect(fixture.out, fixture.run, tools)
        self.assertEqual(collected["planning_boundary"], got)
        self.assertNotIn("stage_tool_calls", collected["unmeasured"])
        accepted = metrics.stage_results(fixture.run)
        timestamps = metrics.timeline(fixture.out / "timeline.jsonl")
        legacy = metrics.per_stage(accepted, [], tools.occurrences, timestamps, "prepare")
        corrected = collected["stages"]
        self.assertEqual([r.get("tool_calls") for r in legacy], [None, 0, 1, 2])
        self.assertEqual([r.get("tool_calls") for r in corrected], [None, 0, 3, 0])
        self.assertEqual(sum(r.get("tool_calls", 0) for r in corrected), len(tools.occurrences))
        self.assertEqual([{k: v for k, v in r.items() if k != "tool_calls"} for r in corrected],
                         [{k: v for k, v in r.items() if k != "tool_calls"} for r in legacy])
        self.assertEqual(corrected[-1]["seconds"], 1.0)
        self.assertEqual(collected["stage_tool_attribution"]["basis"], "timestamp-with-proved-plan-ownership")
        self.assertEqual(len(collected["stage_tool_attribution"]["applied"]), 2)

    def test_later_work_within_the_same_second_and_same_millisecond_is_overshoot(self):
        for label, end, accepted_at, later in (("same second", 1004.994, 1004.990, 1004.998),
                                              ("same millisecond", 1005.040, 1005.034, 1005.040)):
            with self.subTest(label=label):
                fixture = self.fixture()
                fixture.events[-1] = end, fixture.events[-1][1]
                fixture.trace[-2]["ts"] = accepted_at - 0.005
                fixture.trace[-1]["ts"] = accepted_at
                fixture.events += shell_pair("prepare", "python3 -m unittest --help", "ran", later, later)
                got = fixture.read()
                self.assertEqual(got["status"], "overshoot", got)
                self.assertEqual([row["tool_call_id"] for row in got["later_calls"]], ["prepare"])
                self.assertEqual(metrics.collect(fixture.out, fixture.run)["stages"][-1]["tool_calls"], 1)

    def test_actual_later_work_cannot_be_hidden_by_a_replayed_callback(self):
        fixture = self.fixture()
        fixture.events += shell_pair("later", "cat docs/environment.md", "observed", 1005.060, 1005.065)
        fixture.events += shell_pair("replay", fixture.parent_command, fixture.prepare_packet, 1005.080, 1005.150)
        fixture.trace.append(engine_command(1005.140, "complete", IMPROVE, [9, 9], ["prepare", "prepare"],
                                            [PREPARE, PREPARE]))
        got = fixture.read()
        self.assertEqual(got["status"], "overshoot", got)
        self.assertEqual([row["tool_call_id"] for row in got["later_calls"]], ["later", "replay"])
        self.assertEqual({row["tool_call_id"] for row in got["corrections"]}, {"child", "parent"})

    def test_engine_observes_later_prepare_even_without_a_matching_host_tool_row(self):
        fixture = self.fixture()
        fixture.trace.append(engine_command(1005.060, "next", PREPARE, [9, 9], ["prepare", "prepare"],
                                            [PREPARE, PREPARE]))
        got = fixture.read()
        self.assertEqual(got["status"], "overshoot", got)
        self.assertEqual(got["later_trace_lines"], [5])

    def test_unrelated_overlapping_call_is_not_swept_into_plan(self):
        fixture = self.fixture()
        start, end = shell_pair("overlap", "git status --short", "", 1004.900, 1005.060)
        fixture.events.insert(-1, start)
        fixture.events.append(end)
        got = fixture.read()
        self.assertEqual(got["status"], "incomplete", got)
        self.assertEqual([row["tool_call_id"] for row in got["overlapping_calls"]], ["overlap"])
        self.assertEqual({row["tool_call_id"] for row in got["corrections"]}, {"child", "parent"})
        self.assertEqual(metrics.collect(fixture.out, fixture.run)["stages"][-1]["tool_calls"], 1)

    def test_unresolved_overlap_prevents_exact_stop(self):
        fixture = self.fixture()
        start, _ = shell_pair("overlap", "git status --short", "", 1004.900, 1005.060)
        fixture.events.insert(-1, start)
        got = fixture.read()
        self.assertEqual(got["status"], "incomplete", got)
        self.assertEqual([row["result_line"] for row in got["overlapping_calls"]], [None])
        self.assertNotIn("overlap", [row["tool_call_id"] for row in got["corrections"]])

    def test_missing_interim_or_orphan_result_blocks_clean_stop_and_parent_attribution(self):
        for variant in ("missing", "interim", "orphan", "mismatched command", "duplicate terminal"):
            with self.subTest(variant=variant):
                fixture = self.fixture()
                terminal = fixture.events[-1][1]
                if variant == "missing":
                    fixture.events.pop()
                elif variant == "interim":
                    terminal["status"] = "in_progress"
                elif variant == "orphan":
                    terminal["toolCallId"] = "orphan"
                elif variant == "mismatched command":
                    terminal["rawOutput"]["command"] = "echo unrelated"
                else:
                    fixture.events.append((1005.050, terminal.copy()))
                got = fixture.read()
                self.assertEqual(got["status"], "incomplete", got)
                self.assertEqual([row["kind"] for row in got["corrections"]], ["bound-child-done"])

    def test_two_plausible_callbacks_or_an_unresolved_competitor_are_ambiguous(self):
        for completed in (True, False):
            with self.subTest(completed=completed):
                fixture = self.fixture()
                start, end = shell_pair("decoy", fixture.parent_command, fixture.prepare_packet, 1005.0, 1005.050)
                fixture.events.insert(-1, start)
                if completed:
                    fixture.events.append(end)
                got = fixture.read()
                self.assertEqual(got["status"], "incomplete", got)
                self.assertEqual([row["kind"] for row in got["corrections"]], ["bound-child-done"])

    def test_parent_wrong_cli_run_action_or_result_cannot_own_plan(self):
        for original in ("cli", "run", "final_result"):
            with self.subTest(field=original):
                fixture = self.fixture()
                value = str(getattr(fixture, original))
                # Replace an exact token, so each variant changes only one identity.
                command = fixture.parent_command.replace(value + (" " if original != "final_result" else "'"),
                                                         value + "-wrong" + (" " if original != "final_result" else "'"), 1)
                fixture.command("parent", command)
                got = fixture.read()
                self.assertEqual(got["status"], "incomplete", got)
                self.assertEqual([row["kind"] for row in got["corrections"]], ["bound-child-done"])
        fixture = self.fixture()
        fixture.command("parent", fixture.parent_command.replace(IMPROVE, PREPARE))
        self.assertEqual([r["kind"] for r in fixture.read()["corrections"]], ["bound-child-done"])
        self.assertEqual(fixture.read(run_id=PREPARE)["corrections"], [])

    def test_child_wrong_runtime_state_action_report_or_digest_does_not_own_plan(self):
        for field in ("runtime", "child_state", "child_action", "report", "terminal_digest", "report_bytes"):
            with self.subTest(field=field):
                fixture = self.fixture()
                if field == "terminal_digest":
                    fixture.receipt["identities"]["terminal_packet_sha256"] = "0" * 64
                elif field == "report_bytes":
                    fixture.report.write_text('{"classification":"unresolved"}', encoding="utf-8")
                else:
                    value = "runtime-action:2" if field == "child_action" else str(getattr(fixture, field))
                    fixture.command("child", fixture.child_command.replace(value, "wrong:2" if field == "child_action"
                                                                           else value + "-wrong"))
                got = fixture.read()
                self.assertEqual(got["status"], "incomplete", got)
                self.assertEqual([row["kind"] for row in got["corrections"]], ["parent-complete"])

    def test_held_failed_check_only_or_no_transition_does_not_establish_acceptance(self):
        for field, value in (("held", ["N1"]), ("exit", 2), ("check_only", True), ("rev", [8, 8]),
                             ("cursor", [PLAN, PREPARE]), ("accepted", [])):
            with self.subTest(field=field):
                fixture = self.fixture()
                fixture.trace[-1][field] = value
                got = fixture.read()
                self.assertEqual(got["status"], "incomplete", got)
                self.assertEqual(got["corrections"], [])
        fixture = self.fixture()
        final = fixture.event("parent", "tool_call_update")
        final["status"], final["rawOutput"]["exit_code"] = "failed", 2
        self.assertEqual([row["kind"] for row in fixture.read()["corrections"]], ["bound-child-done"])

    def test_mentions_heredocs_compounds_and_check_only_argv_are_unproved(self):
        for wrap in (lambda cmd: f"echo {cmd}", lambda cmd: f"cat <<EOF\n{cmd}\nEOF",
                     lambda cmd: f"{cmd} && true", lambda cmd: cmd[:-1] + " --check-only'",
                     lambda cmd: f"/usr/bin/env {cmd}", lambda cmd: f"helper.sh {cmd}"):
            fixture = self.fixture()
            fixture.command("parent", wrap(fixture.parent_command))
            got = fixture.read()
            self.assertEqual(got["status"], "incomplete", got)
            self.assertEqual([row["kind"] for row in got["corrections"]], ["bound-child-done"])

    def test_unwrapped_literal_callbacks_also_qualify(self):
        fixture = self.fixture()
        fixture.command("parent", fixture.parent_command.removeprefix("/bin/zsh -lc '").removesuffix("'"))
        fixture.command("child", fixture.child_bare)
        self.assertEqual(fixture.read()["status"], "established")

    def test_wrong_plan_transition_and_cleanly_missing_trace_rows_fail_closed(self):
        fixture = self.fixture()
        fixture.trace[-1]["accepted"][0]["action"] = STRATEGY
        self.assertEqual(fixture.read()["corrections"], [])
        for drop in (0, 1, 2, 3):
            with self.subTest(trace_index=drop):
                fixture = self.fixture()
                fixture.trace.pop(drop)
                self.assertEqual(fixture.read()["status"], "incomplete")

    def test_missing_malformed_capped_or_truncated_trace_keeps_time_fallback(self):
        for variant in ("missing", "malformed", "capped", "truncated"):
            with self.subTest(variant=variant):
                fixture = self.fixture()
                fixture.write()
                trace = fixture.run / "trace.jsonl"
                if variant == "missing":
                    trace.unlink()
                elif variant == "capped":
                    with trace.open("r+b") as handle:
                        handle.truncate(boundary.planning_trace.TRACE_LIMIT)
                elif variant == "malformed":
                    with trace.open("ab") as handle:
                        handle.write(b"{\n")
                else:
                    trace.write_bytes(trace.read_bytes()[:-1])
                got = boundary.analyze(fixture.out, fixture.run, fixture.cli)
                self.assertEqual(got["status"], "incomplete", got)
                self.assertEqual(got["corrections"], [])
                # Exercise the normal metric entry point for ordinary damaged traces.
                if variant != "capped":
                    collected = metrics.collect(fixture.out, fixture.run)
                    self.assertEqual(collected["stage_tool_attribution"]["basis"], "timestamp-only")
                    self.assertEqual(collected["stages"][-1]["tool_calls"], 2)

    def test_wrong_launch_span_and_missing_host_clock_prevent_exact_stop(self):
        for name, before, after in (("sessions.jsonl", '"events_line": 8', '"events_line": 7'),
                                    ("timeline.jsonl", '{"line": 7, "t": 1005.04}\n', "")):
            with self.subTest(name=name):
                fixture = self.fixture()
                fixture.write()
                path = fixture.out / name
                old = path.read_text()
                new = old.replace(before, after)
                self.assertNotEqual(new, old)
                path.write_text(new)
                self.assertEqual(boundary.analyze(fixture.out, fixture.run, fixture.cli)["status"], "incomplete")

    def test_missing_stream_does_not_invent_zero_from_remaining_timestamps(self):
        fixture = self.fixture()
        fixture.write()
        (fixture.out / "events.jsonl").unlink()
        measured = metrics.collect(fixture.out, fixture.run)
        self.assertIsNone(measured["stages"][-1]["tool_calls"])
        self.assertEqual(measured["planning_boundary"]["status"], "incomplete")

    def test_partial_event_corruption_preserves_calls_but_makes_stage_counts_unmeasured(self):
        fixture = self.fixture()
        fixture.write()
        intact = metrics.collect(fixture.out, fixture.run)
        stream = fixture.out / "events.jsonl"
        rows = stream.read_bytes().splitlines(keepends=True)
        rows[4] = b"{\n"  # the child's call start, with the surrounding source lines intact
        stream.write_bytes(b"".join(rows))
        tools = metrics.ToolLog()
        measured = metrics.collect(fixture.out, fixture.run, tools)
        self.assertEqual([(call.tool_id, call.key[1]) for call in tools.occurrences.values()],
                         [("pass", 3), ("parent", 7)])
        self.assertEqual([number for number, _ in metrics.events(stream)], [0, 1, 2, 3, 5, 6, 7])
        self.assertEqual(measured["unmeasured"]["stage_tool_calls"],
                         "host event stream has a malformed row at line 5")
        self.assertEqual(measured["stages"],
                         [{**row, "tool_calls": None} if "tool_calls" in row else row for row in intact["stages"]])
        self.assertEqual(measured["planning_boundary"]["status"], "incomplete")

    def test_clean_event_prefix_cannot_hide_rows_recorded_by_runner_or_launch(self):
        for retained in ("runner timestamp", "launch receipt"):
            with self.subTest(retained=retained):
                fixture = self.fixture()
                fixture.write()
                stream = fixture.out / "events.jsonl"
                jsonl(stream, [fixture.events[0][1]])
                if retained == "launch receipt":
                    jsonl(fixture.out / "timeline.jsonl", [{"line": 0, "t": fixture.events[0][0]}])
                measured = metrics.collect(fixture.out, fixture.run)
                self.assertEqual(measured["stages"][-1]["stage"], "prepare")
                self.assertIsNone(measured["stages"][-1]["tool_calls"])
                self.assertIn(retained, measured["unmeasured"]["stage_tool_calls"])
                self.assertEqual(measured["planning_boundary"]["status"], "incomplete")

    def test_missing_call_start_timestamp_preserves_the_call_but_makes_stage_counts_unmeasured(self):
        fixture = self.fixture()
        fixture.write()
        intact = metrics.collect(fixture.out, fixture.run)
        timeline = fixture.out / "timeline.jsonl"
        stamps = [json.loads(row) for row in timeline.read_text().splitlines()]
        jsonl(timeline, (stamp for stamp in stamps if stamp["line"] != 6))
        tools = metrics.ToolLog()
        measured = metrics.collect(fixture.out, fixture.run, tools)
        parent = tools.occurrences[(1, 7, 1)]
        self.assertEqual((parent.tool_id, parent.t), ("parent", None))
        self.assertEqual(measured["unmeasured"]["stage_tool_calls"],
                         "tool call start at event line 7 has no usable runner timestamp")
        self.assertEqual(measured["stages"],
                         [{**row, "tool_calls": None} if "tool_calls" in row else row for row in intact["stages"]])
        self.assertEqual(measured["planning_boundary"]["status"], "incomplete")

    def test_intact_no_tool_stream_measures_zero_without_proving_the_boundary(self):
        fixture = self.fixture()
        fixture.events = [*fixture.events[:2], (1005.040, {"type": "end", "sessionId": "thread-1"})]
        fixture.write()
        measured = metrics.collect(fixture.out, fixture.run)
        self.assertNotIn("stage_tool_calls", measured["unmeasured"])
        self.assertEqual([row.get("tool_calls") for row in measured["stages"]], [None, 0, 0, 0])
        self.assertEqual(measured["planning_boundary"]["status"], "incomplete")

    def test_resume_can_reuse_an_id_without_losing_a_call_or_retargeting_its_result(self):
        fixture = self.fixture()
        fixture.launch_split = 4
        fixture.events.insert(4, (1004.000, {"type": "available_commands", "sessionId": "thread-1"}))
        for kind in ("tool_call", "tool_call_update"):
            fixture.event("child", kind)["toolCallId"] = "pass"
        got = fixture.read()
        self.assertEqual(got["status"], "established", got)
        tools = metrics.ToolLog()
        measured = metrics.collect(fixture.out, fixture.run, tools)
        keys = [key for key, call in tools.occurrences.items() if call.tool_id == "pass"]
        self.assertEqual(keys, [(1, 3, 1), (2, 6, 1)])
        self.assertEqual([tools.occurrence_results[key].line for key in keys], [4, 7])
        self.assertEqual(sum(row.get("tool_calls", 0) for row in measured["stages"]), 3)
        session_path = fixture.out / "sessions.jsonl"
        session_path.write_text(session_path.read_text().replace(str(fixture.cli), str(fixture.cli) + "-wrong"))
        self.assertEqual(boundary.analyze(fixture.out, fixture.run, fixture.cli)["status"], "incomplete")


class OccurrencesAndClocksTest(unittest.TestCase):
    def test_claude_blocks_have_distinct_ordinals_and_results_never_cross_launches(self):
        tools = metrics.ToolLog()
        first = {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "starting"},
            {"type": "tool_use", "name": "Read", "id": "again", "input": {"file_path": "a"}},
            {"type": "tool_use", "name": "Read", "id": "other", "input": {"file_path": "b"}},
        ]}}
        result = {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "other", "content": "b"},
            {"type": "tool_result", "tool_use_id": "again", "content": "a"},
        ]}}
        tools.feed(first, 101.0, 0, launch=1)
        tools.feed(result, 102.0, 1, launch=1)
        tools.feed(result, 103.0, 2, launch=2)  # orphan updates in the new launch
        tools.feed(first, 104.0, 3, launch=2)
        tools.feed(result, 105.0, 4, launch=2)
        self.assertEqual(list(tools.occurrences), [(1, 1, 2), (1, 1, 3), (2, 4, 2), (2, 4, 3)])
        self.assertEqual([(r.line, r.block) for r in tools.occurrence_results.values()], [(2, 1), (2, 2), (5, 1), (5, 2)])
        self.assertEqual(len(tools.occurrence_issues), 2)
        rows = metrics.per_stage([{"stage": "plan", "outcome": "done", "t": 102.0}], [],
                                 tools.occurrences, {0: 101.0, 4: 105.0}, "prepare")
        self.assertEqual([row["tool_calls"] for row in rows], [2, 2])

    def test_seeded_send_back_missing_and_recovered_stamps_keep_declared_windows(self):
        calls = {(2, 9, 1): metrics.CallOccurrence((2, 9, 1), "test", "Bash", "pwd", 132.0)}
        corrections = [{"launch": 2, "start_line": 9, "block": 1, "plan_action": PLAN}]
        stamps = {0: 100.0, 8: 132.0}
        accepted = [{"stage": "spec", "action": SPEC, "outcome": "done", "t": 90.0},
                    {"stage": "plan", "action": STRATEGY, "outcome": "send-back", "t": 102.0},
                    {"stage": "plan", "action": PLAN, "outcome": "done", "t": 130.0}]
        windows = metrics.stage_windows(accepted, stamps, "prepare")
        moves = metrics._stage_tool_moves(accepted, windows, calls, corrections)
        self.assertEqual(moves, {(2, 9, 1): (3, 2)})
        turns = [{"t": 132.0, "input": 7, "call": True}]
        legacy = metrics.per_stage(accepted, turns, calls, stamps, "prepare")
        fixed = metrics.per_stage(accepted, turns, calls, stamps, "prepare", tool_owners={(2, 9, 1): 2})
        self.assertEqual(fixed[0]["timing"], "unavailable")
        self.assertEqual(fixed[1]["outcome"], "send-back")
        self.assertEqual(fixed[2]["seconds"], 28.0)  # includes the runner's wall-clock gap
        self.assertEqual(fixed[3]["context"], legacy[3]["context"])
        self.assertEqual(fixed[3]["turns"], legacy[3]["turns"])
        self.assertEqual([row.get("tool_calls") for row in fixed], [None, 0, 1, 0])
        for unknown_time in (None, 102.0):  # missing and same-stamp recovery
            accepted[-1]["t"] = unknown_time
            windows = metrics.stage_windows(accepted, stamps, "prepare")
            self.assertEqual(metrics._stage_tool_moves(accepted, windows, calls, corrections), {})
        accepted[-1]["t"] = None
        rows = metrics.per_stage(accepted, turns, calls, stamps, "prepare")
        self.assertTrue(all(row.get("timing") == "unavailable" for row in rows[-2:]))


class StrictTraceTest(unittest.TestCase):
    def test_original_lines_and_exact_bytes_even_with_unicode_separator(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "trace.jsonl"
            raw = '{"text":"contains \u2028 in the record"}\n{"x":2}\n'.encode()
            path.write_bytes(raw)
            got = boundary.planning_trace.read_trace(path)
            self.assertEqual(got, {"status": "ok", "sha256": digest(raw), "reason": None, "rows": [
                {"line": 1, "record": {"text": "contains \u2028 in the record"}},
                {"line": 2, "record": {"x": 2}},
            ]})

    def test_missing_invalid_or_nonregular_sources_are_explicit_and_never_partial(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "trace.jsonl"
            self.assertEqual(boundary.planning_trace.read_trace(path)["status"], "unavailable")
            for raw in (b'{}\n{"x":"\xff"}\n', b'{}\n[]\n', b'{}\n\n', b'{}\n{"x":NaN}\n',
                        b'{}\n{"x":1,"x":2}\n', b'{}\n{"x":2}', b'{}\n{"x":1e999}\n'):
                with self.subTest(raw=raw):
                    path.write_bytes(raw)
                    got = boundary.planning_trace.read_trace(path)
                    self.assertEqual((got["status"], got["rows"], got["sha256"]), ("invalid", [], digest(raw)))
            self.assertEqual(boundary.planning_trace.read_trace(path.parent)["status"], "invalid")
            alias = path.with_name("symlink")
            alias.symlink_to(path)
            self.assertEqual(boundary.planning_trace.read_trace(alias)["status"], "invalid")
            fifo = path.with_name("fifo")
            os.mkfifo(fifo)
            self.assertEqual(boundary.planning_trace.read_trace(fifo)["status"], "invalid")


if __name__ == "__main__":
    unittest.main()
