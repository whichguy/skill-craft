#!/usr/bin/env python3
"""No-model checks for test/shiploop_e2e/fidelity.py: the record-only `fidelity` block of metrics.json (SPEC 2026-10-09).

The replay tests read the compact extracts of twelve saved runs under test/fixtures/fidelity (cut by its extract.py from the
run folders of 2026-10-05, 2026-10-07 and 2026-10-08) and two extracts of the 2026-10-06 verify records, never the machine's
run folders. Each events.jsonl keeps its selected events at their original line numbers, so `event 493` below is line 493 of
the saved stream. The real-git and host-stream shapes are the harness's own (Claude tool_use and tool_result blocks, Grok
tool_call and tool_call_update events, Codex through its translator). No test starts a host, a model or a listener, signals a
process, or reads the machine's process table.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import metrics  # noqa: E402

FIXTURES = ROOT / "test" / "fixtures" / "fidelity"
EXPORTER = ROOT / "skills" / "shiploop-run-review" / "scripts" / "export.py"
ENGINE = ROOT / "skills" / "shiploop" / "scripts"

CLAUDE = ("r1-battleship-sonnet", "r2-battleship-sonnet", "r3-battleship-sonnet", "r1-checkers-sonnet", "r2-checkers-sonnet",
          "r3-checkers-sonnet", "v1230-battleship-sonnet")
GROK = ("r1-battleship-grok-none", "r2-battleship-grok-none", "r3-battleship-grok-none", "v1230-battleship-grok-none")
ELEVEN = CLAUDE + GROK
V1220 = ("v1220-battleship-sonnet", "v1220-battleship-grok-medium-none")
CODEX = "v1210-battleship-luna-xhigh"


def fidelity_module():
    import fidelity
    return fidelity


def stage_table_dir(tmp: Path, planning_choice: bool = True) -> Path:
    """A stand-in for <engine scripts>/shiploop_stage_spec.py built from the engine's table as test/fixtures/fidelity/extract.py
    froze it, so a later change to the engine's table cannot move a saved run's declared checks. Without
    PLANNING_CHOICE_STAGES it is the shape of the 1.21.0 table, which the exporter's stage_catalog cannot read."""
    table = json.loads((FIXTURES / "stage_table.json").read_text())
    rows = {name: {"goal": name, **row} for name, row in table["rows"].items()}
    source = ("from types import SimpleNamespace as N\n"
              f"STAGES = {tuple(table['stages'])!r}\n"
              "STAGE_SPEC = {n: N(goal=r['goal'], complete_runs=frozenset(r['complete_runs']), improve=r['improve'] or None,"
              " reads=tuple(r['reads'])) for n, r in " + repr(rows) + ".items()}\n"
              + (f"PLANNING_CHOICE_STAGES = frozenset({table['planning_choice_stages']!r})\n" if planning_choice else ""))
    scripts = tmp / ("scripts" if planning_choice else "scripts-1.21.0")
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / "shiploop_stage_spec.py").write_text(source)
    return scripts


_TABLE_TMP = tempfile.TemporaryDirectory()
unittest.addModuleCleanup(_TABLE_TMP.cleanup)
CURRENT_TABLE = stage_table_dir(Path(_TABLE_TMP.name))
OLD_TABLE = stage_table_dir(Path(_TABLE_TMP.name), planning_choice=False)

_REPLAYS: dict[tuple, dict] = {}


def run_dir_of(alias: str) -> Path:
    return FIXTURES / alias / ".shiploop-runs" / "work-1" / "run"


def replay(alias: str, **kwargs) -> dict:
    """{block, metrics, tools, out, run_dir} for one extract: the ToolLog is the one metrics.collect fills."""
    key = (alias, tuple(sorted(kwargs.items())))
    if key not in _REPLAYS:
        fidelity = fidelity_module()
        out, run_dir = FIXTURES / alias, run_dir_of(alias)
        tools = metrics.ToolLog()
        collected = metrics.collect(out, run_dir, tools=tools)
        options = {"engine_scripts": CURRENT_TABLE, "exporter": EXPORTER, **kwargs}
        _REPLAYS[key] = {"block": fidelity.build(out, run_dir, tools, **options), "metrics": collected, "tools": tools,
                         "out": out, "run_dir": run_dir}
    return _REPLAYS[key]


def command_at(alias: str, number: int) -> str:
    """The command of the tool call at one line of an extract's events.jsonl."""
    for found, event in metrics.events(FIXTURES / alias / "events.jsonl"):
        if found != number:
            continue
        if event.get("type") == "assistant":
            return next(b["input"]["command"] for b in event["message"]["content"] if b.get("type") == "tool_use")
        return event["rawInput"]["command"]
    raise AssertionError(f"{alias} has no event {number}")


def zsh_wrap(script: str) -> str:
    """A script as Codex prints it: the argv of its shell, `/bin/zsh -lc "<script>"`, quotes and backslashes escaped."""
    return '/bin/zsh -lc "' + script.replace("\\", "\\\\").replace('"', '\\"') + '"'


class ToolLogRecordTest(unittest.TestCase):
    """metrics.ToolLog keeps what the fidelity block reads, and nothing else about it changes."""

    def test_a_call_keeps_its_event_number_tool_command_and_paths_in_order(self):
        log = metrics.ToolLog()
        log.call(10.5, "c1", "Bash", {"command": "echo hi"}, event=7)
        log.call(11.0, "c2", "Edit", {"file_path": "/a/b.md", "old_string": "x"}, event=9)
        log.call(12.0, "c3", "write", {"path": "/c/d.md"}, event=11)
        self.assertEqual(log.sequence, [
            {"event": 7, "t": 10.5, "tool": "Bash", "command": "echo hi", "paths": []},
            {"event": 9, "t": 11.0, "tool": "Edit", "command": "", "paths": ["/a/b.md"]},
            {"event": 11, "t": 12.0, "tool": "write", "command": "", "paths": ["/c/d.md"]}])

    def test_a_codex_file_change_names_its_first_path_twice_and_it_is_one_path(self):
        log = metrics.ToolLog()
        log.call(1.0, "item_1", "search_replace", {"target_file": "/w/a.json", "paths": ["/w/a.json", "/w/b.json"]}, event=3)
        self.assertEqual(log.sequence[0]["paths"], ["/w/a.json", "/w/b.json"])

    def test_a_path_field_that_is_not_a_list_of_strings_names_no_path(self):
        log = metrics.ToolLog()
        log.call(1.0, "c", "write", {"paths": "abc", "path": None, "file_path": 3}, event=1)
        log.call(2.0, "d", "write", {"paths": ["/x", 4, "", "/x", "/y"]}, event=2)
        self.assertEqual([c["paths"] for c in log.sequence], [[], ["/x", "/y"]])

    def test_two_calls_that_reuse_one_id_are_both_kept(self):
        # Codex numbers its calls again in each session, so metrics.ToolLog.calls holds the later one only.
        log = metrics.ToolLog()
        log.call(1.0, "item_1", "run_terminal_command", {"command": "ls"}, event=3)
        log.call(9.0, "item_1", "run_terminal_command", {"command": "pwd"}, event=40)
        self.assertEqual([c["event"] for c in log.sequence], [3, 40])
        self.assertEqual(len(log.calls), 1)

    def test_a_call_without_an_event_number_is_still_recorded(self):
        log = metrics.ToolLog()
        log.call(1.0, "c", "Bash", {"command": "ls"})
        self.assertIsNone(log.sequence[0]["event"])

    def test_a_refusal_keeps_its_whole_first_line_beside_the_cut_one_and_failures_keep_their_shape(self):
        log = metrics.ToolLog()
        log.call(1.0, "c1", "Bash", {"command": "python3 /x/shiploop complete --run-dir r"}, event=3)
        line = "ShipLoop navigator: " + "evidence " * 40
        log.result("c1", line + "\nRead the current packet with next; fix it.", 1, event=4)
        self.assertEqual(log.failures, [{"verb": "complete", "exit": 1, "line": line[:200]}])
        self.assertEqual(log.failure_events, [{"event": 4, "line": line.strip()}])
        self.assertGreater(len(line), 200)

    def test_failure_events_stay_in_step_with_failures_for_every_way_a_failure_is_found(self):
        log = metrics.ToolLog()
        log.call(1.0, "c1", "Bash", {"command": "python3 /x/shiploop complete --run-dir r"}, event=3)
        log.call(2.0, "c2", "Bash", {"command": "python3 /x/shiploop next --run-dir r"}, event=5)
        log.call(3.0, "c3", "Bash", {"command": "ls"}, event=7)
        log.result("c1", "ShipLoop navigator: one\n", None, event=4)   # a refusal behind a pipe: no exit shown
        log.result("c2", "boom: required field\n", 2, event=6)         # a nonzero exit of a ShipLoop verb, no refusal line
        log.result("c3", "ShipLoop navigator: not a failure of a ShipLoop call? it is, by its line\n", 0, event=8)
        self.assertEqual(len(log.failures), len(log.failure_events))
        self.assertEqual([f["event"] for f in log.failure_events], [4, 6, 8])

    def test_collect_fills_the_tool_log_it_is_given_and_still_works_without_one(self):
        alias = "r1-battleship-sonnet"
        log = metrics.ToolLog()
        given = metrics.collect(FIXTURES / alias, run_dir_of(alias), tools=log)
        plain = metrics.collect(FIXTURES / alias, run_dir_of(alias))
        self.assertIn(493, [c["event"] for c in log.sequence])
        self.assertEqual(given["shiploop_failures"], plain["shiploop_failures"])
        self.assertEqual(given["model_glue"], plain["model_glue"])
        self.assertEqual(len(log.failures), len(log.failure_events))

    def test_collect_records_no_fidelity_key_so_progress_py_and_the_other_callers_are_unchanged(self):
        alias = "r1-battleship-sonnet"
        self.assertNotIn("fidelity", metrics.collect(FIXTURES / alias, run_dir_of(alias)))


if __name__ == "__main__":
    unittest.main()
