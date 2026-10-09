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


class UnwrapTest(unittest.TestCase):
    def setUp(self):
        self.fidelity = fidelity_module()

    def test_a_leading_shell_wrapper_is_stripped_in_each_shape_codex_and_models_write(self):
        cases = {
            '/bin/zsh -lc "git commit -m x"': "git commit -m x",
            "/bin/bash -c 'pkill -f node'": "pkill -f node",
            'sh -c "echo a; git add -A"': "echo a; git add -A",
            "zsh -c 'ls'": "ls",
            '/bin/zsh -lc "echo \\"quoted\\" && ls"': 'echo "quoted" && ls',
        }
        for wrapped, inner in cases.items():
            with self.subTest(wrapped=wrapped):
                self.assertEqual(self.fidelity.unwrap_shell(wrapped), inner)

    def test_a_command_that_is_not_one_wrapper_is_returned_as_it_is(self):
        for command in ("git commit -m x", "cd x && bash -c 'ls'", "python3 -c 'print(1)'", "bash script.sh", "echo \"bash -c 'x'\"",
                        '/bin/zsh -lc "unterminated', ""):
            with self.subTest(command=command):
                self.assertEqual(self.fidelity.unwrap_shell(command), command)

    def test_the_unwrap_makes_a_first_position_commit_visible_where_the_frozen_glue_reader_sees_none(self):
        wrapped = '/bin/zsh -lc "git commit -m x"'
        self.assertEqual(metrics.glue_reasons(wrapped), [], "the frozen reader is anchored and does not read inside the wrapper")
        self.assertEqual(self.fidelity.commit_forms(wrapped), ["git commit"])
        self.assertEqual(self.fidelity.commit_forms('/bin/zsh -lc "cd w && git -C w add -A && git -C w commit -q -m y"'),
                         ["git add", "git commit"])
        # The form is the subcommand, not a word of the path or the message.
        self.assertEqual(self.fidelity.commit_forms('git -C /x/add-dir commit -q -m "test: add the thing"'), ["git commit"])
        self.assertEqual(self.fidelity.commit_forms('git -c user.name=a -c user.email=b add -A && git commit -m "add x"'),
                         ["git add", "git commit"])

    def test_real_codex_command_strings_of_the_1_21_0_run(self):
        # Event 731 of v1210-battleship-luna-xhigh feeds a report to the Until Loop runtime through a heredoc whose prose says
        # "; git diff --check passed. Scoped commit": the frozen reader takes that sentence for a commit, the unwrapped one does not.
        long = command_at(CODEX, 731)
        self.assertTrue(long.startswith('/bin/zsh -lc "'))
        self.assertEqual(metrics.glue_reasons(long), ["git commit/add by the model"])
        self.assertEqual(self.fidelity.commit_forms(long), [])
        # Event 82 writes SHIPLOOP.md and docs/shiploop/README.md with heredocs: files of the product, not script-owned.
        self.assertEqual(self.fidelity.shell_edits(command_at(CODEX, 82)), [])
        for number in (82, 731):
            with self.subTest(event=number):
                self.assertEqual(self.fidelity.name_kills(command_at(CODEX, number)), [])


class EvidenceTest(unittest.TestCase):
    def setUp(self):
        self.fidelity = fidelity_module()

    def test_the_classes_of_the_round_1_sonnet_run_split_notes_from_files(self):
        evidence = replay("r1-battleship-sonnet")["block"]["evidence"]
        self.assertEqual(evidence["counts"], {"script": 15, "loop": 7, "file": 1, "note": 12, "sentence": 0, "skipped": 2,
                                              "unclassified": 0})
        self.assertEqual(len(evidence["stages"]), 37)
        self.assertEqual(sum(evidence["counts"].values()), 37)

    def test_the_classes_of_the_round_3_sonnet_run_match_the_audit_once_notes_and_files_are_added(self):
        counts = replay("r3-battleship-sonnet")["block"]["evidence"]["counts"]
        self.assertEqual((counts["script"], counts["loop"], counts["file"] + counts["note"], counts["sentence"]), (14, 7, 12, 3))
        self.assertEqual((counts["file"], counts["note"]), (8, 4))

    def test_every_run_of_eleven_classes_every_accepted_action_once(self):
        expected = {"r1-battleship-sonnet": 37, "r2-battleship-sonnet": 36, "r3-battleship-sonnet": 36, "r1-checkers-sonnet": 36,
                    "r2-checkers-sonnet": 37, "r3-checkers-sonnet": 38, "r1-battleship-grok-none": 27,
                    "r2-battleship-grok-none": 52, "r3-battleship-grok-none": 15, "v1230-battleship-sonnet": 38,
                    "v1230-battleship-grok-none": 47}
        for alias, rows in expected.items():
            with self.subTest(run=alias):
                evidence = replay(alias)["block"]["evidence"]
                self.assertEqual((len(evidence["stages"]), sum(evidence["counts"].values())), (rows, rows))
                self.assertEqual(len({row["action"] for row in evidence["stages"]}), rows)

    def test_the_engines_not_applicable_entries_are_skipped_and_the_prefix_is_the_engines_own(self):
        source = (ENGINE / "shiploop_item_scope.py").read_text()
        self.assertIn(f'NOT_APPLICABLE = "{self.fidelity.NOT_APPLICABLE}"', source)
        for alias, skipped in (("r1-battleship-sonnet", 2), ("r2-battleship-grok-none", 4), ("r3-battleship-sonnet", 0)):
            with self.subTest(run=alias):
                self.assertEqual(replay(alias)["block"]["evidence"]["counts"]["skipped"], skipped)

    def test_a_stage_that_cites_only_its_own_packet_inbox_or_result_is_a_sentence_and_a_note_is_not_a_file(self):
        rows = {r["stage"]: r for r in replay("r3-battleship-sonnet")["block"]["evidence"]["stages"]}
        self.assertEqual(rows["intake"]["class"], "sentence")
        self.assertEqual(rows["intake"]["refs"], {"own": 1, "note": 0, "outside": 0})
        notes = [r for r in replay("r1-battleship-sonnet")["block"]["evidence"]["stages"] if r["class"] == "note"]
        self.assertEqual(len(notes), 12)
        for row in notes:
            self.assertEqual(row["refs"]["outside"], 0)
            self.assertGreaterEqual(row["refs"]["note"], 1)

    def test_a_note_with_a_real_file_beside_it_is_a_file_and_the_note_still_counts_in_refs(self):
        mixed = [r for r in replay("r3-battleship-sonnet")["block"]["evidence"]["stages"]
                 if r["class"] == "file" and r["refs"]["note"] and r["refs"]["outside"]]
        self.assertTrue(mixed, "the audit found notes beside one other file in the round-3 runs")

    def test_script_beats_loop_beats_file_and_the_records_list_keeps_what_the_class_hides(self):
        rows = replay("r3-battleship-sonnet")["block"]["evidence"]["stages"]
        both = [r for r in rows if "improve" in r["records"] and {"verify", "lint", "quality", "backchain"} & set(r["records"])]
        self.assertTrue(both, "a carry-forward with a verify record and an Improve child reads script")
        for row in both:
            self.assertEqual(row["class"], "script")
        loops = [r for r in rows if r["class"] == "loop"]
        self.assertEqual(len(loops), 7)
        for row in loops:
            self.assertEqual(row["records"], ["improve"])
        counts = replay("r3-battleship-sonnet")["block"]["evidence"]["records"]
        self.assertEqual(set(counts), {"verify", "lint", "quality", "backchain", "improve"})
        self.assertEqual(counts["improve"], 8, "7 loop rows and the carry-forward that also carries a verify record")

    def test_an_improve_child_is_found_by_its_receipt_or_by_its_improve_results_entry(self):
        for how in ("receipt", "improve_results", "neither"):
            with self.subTest(how=how), tempfile.TemporaryDirectory() as tmp:
                run_dir = Path(tmp) / "run"
                run_dir.mkdir()
                state = {"status": "done", "history": [{"action": "nav-1", "stage": "spec", "outcome": "done"}],
                         "accepted": {"nav-1": {"outcome": "done", "summary": "s", "evidence_refs": ["/r/run/results/nav-1.md"]}},
                         "improve_results": {"nav-1": {}} if how == "improve_results" else {}}
                if how == "receipt":
                    (run_dir / "improve" / "nav-1").mkdir(parents=True)
                    (run_dir / "improve" / "nav-1" / "receipt.md").write_text("receipt")
                row = self.fidelity.evidence(run_dir, state, None)["stages"][0]
                self.assertEqual((row["class"], row["records"]), (("sentence", []) if how == "neither" else ("loop", ["improve"])))

    def test_a_history_entry_with_no_accepted_result_is_unclassified_not_a_sentence(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = {"status": "active", "history": [{"action": "nav-1", "stage": "spec", "outcome": "done"}], "accepted": {}}
            evidence = self.fidelity.evidence(Path(tmp), state, None)
            self.assertEqual(evidence["counts"]["unclassified"], 1)
            self.assertEqual(evidence["stages"][0]["class"], "unclassified")
            self.assertIsNone(evidence["stages"][0]["refs"])

    def test_a_backchain_check_record_on_the_plan_action_is_listed(self):
        rows = {r["stage"]: r for r in replay("r1-battleship-sonnet")["block"]["evidence"]["stages"]}
        self.assertIn("backchain", rows["plan"]["records"])
        self.assertEqual(rows["plan"]["class"], "script")

    def test_declared_checks_come_from_the_stage_table_and_planning_review_none_reads_planning_as_judgement(self):
        stage = replay("r1-battleship-sonnet")["block"]["evidence"]
        declared = {}
        for row in stage["stages"]:
            declared.setdefault(row["stage"], row["declared"])
        self.assertEqual(declared["test-green"], "script-run")
        self.assertEqual(declared["spec"], "review loop")
        self.assertEqual(declared["intake"], "model judgement")
        none = replay("r1-battleship-grok-none")["block"]["evidence"]
        self.assertEqual({r["declared"] for r in none["stages"] if r["stage"] == "spec"}, {"model judgement"})

    def test_no_saved_run_declared_script_run_without_a_record_and_the_list_names_one_that_does(self):
        for alias in ELEVEN:
            with self.subTest(run=alias):
                self.assertEqual(replay(alias)["block"]["evidence"]["declared_script_run_without_record"], [])
        with tempfile.TemporaryDirectory() as tmp:
            shown = Path(tmp) / "r3-battleship-sonnet"
            self.copy_run("r3-battleship-sonnet", shown)
            record = next((shown / ".shiploop-runs" / "work-1" / "run" / "tests").glob("*-verify1.md"))
            action = record.name.split("-verify")[0]
            for sibling in (shown / ".shiploop-runs" / "work-1" / "run").rglob(f"{action}*"):
                if sibling.is_file() and sibling.parent.name in ("tests", "lint", "quality"):
                    sibling.unlink()
            run_dir = shown / ".shiploop-runs" / "work-1" / "run"
            block = self.fidelity.build(shown, run_dir, metrics.ToolLog(), engine_scripts=CURRENT_TABLE, exporter=EXPORTER)
            stage = next(h["stage"] for h in metrics.engine_state(run_dir)["history"] if h["action"] == action)
            self.assertIn(stage, block["evidence"]["declared_script_run_without_record"])

    def test_a_blocked_stage_without_a_record_is_not_listed(self):
        # v1230 Grok ended blocked at system-test: a blocked system-test has no record by design.
        block = replay("v1230-battleship-grok-none")["block"]
        self.assertEqual(block["evidence"]["declared_script_run_without_record"], [])
        last = block["evidence"]["stages"][-1]
        self.assertEqual((last["stage"], last["outcome"]), ("system-test", "blocked"))

    def test_an_incompatible_stage_table_leaves_declared_unmeasured_with_the_reason_and_the_rest_stays_measured(self):
        block = replay("r1-battleship-sonnet", engine_scripts=OLD_TABLE)["block"]
        self.assertIn("PLANNING_CHOICE_STAGES", block["unmeasured"]["declared"])
        self.assertIsNone(block["evidence"]["declared_script_run_without_record"])
        self.assertTrue(all(row["declared"] is None for row in block["evidence"]["stages"]))
        self.assertEqual(block["evidence"]["counts"]["script"], 15)

    def test_a_missing_stage_table_or_exporter_is_unmeasured_with_a_reason_never_zero(self):
        for label, options, word in (("no table", {"engine_scripts": ROOT / "nowhere"}, "missing"),
                                     ("no exporter", {"exporter": ROOT / "nowhere" / "export.py"}, "exporter"),
                                     ("neither given", {"engine_scripts": None, "exporter": None}, "stage table")):
            with self.subTest(label):
                block = replay("r1-battleship-sonnet", **options)["block"]
                self.assertIn(word, block["unmeasured"]["declared"])
                self.assertIsNone(block["evidence"]["declared_script_run_without_record"])

    def test_the_codex_run_of_the_old_layout_classifies_from_files_alone(self):
        block = replay(CODEX, engine_scripts=OLD_TABLE)["block"]
        counts = block["evidence"]["counts"]
        self.assertEqual((counts["script"], counts["loop"], counts["file"] + counts["note"]), (8, 5, 10))
        self.assertEqual(sum(counts.values()), 23)

    def test_the_block_holds_no_packet_text_and_no_machine_path(self):
        text = json.dumps(replay("r1-battleship-sonnet")["block"])
        self.assertNotIn("/Users/", text)
        self.assertNotIn("Result template:", text)

    @staticmethod
    def copy_run(alias: str, target: Path) -> None:
        import shutil
        shutil.copytree(FIXTURES / alias, target)


class ValidationTest(unittest.TestCase):
    def setUp(self):
        self.fidelity = fidelity_module()

    def test_the_round_3_battleship_records_are_11_records_33_runs_5_commands_2_red_and_6_accepted_ran_stages(self):
        validation = replay("r3-battleship-sonnet")["block"]["validation"]
        self.assertEqual((validation["records"], validation["runs"], validation["distinct_commands"], validation["red"]),
                         (11, 33, 5, 2))
        self.assertEqual(validation["accepted_ran"]["stages"],
                         ["integration-verify", "regression", "static-checks", "test-green", "test-red", "verify"])
        self.assertEqual(validation["by_suite"]["focused"]["runs"], 19)
        self.assertEqual(validation["by_suite"]["regression"]["runs"], 6)
        check = validation["by_suite"]["check"]
        self.assertEqual((check["runs"], check["counts_null"], check["counted"]), (8, 7, 1))
        self.assertEqual(validation["schemas"], ["shiploop-test-loop/v1"])

    def test_the_2026_10_06_audit_is_reproduced_every_focused_and_regression_row_of_v1220_has_null_counts(self):
        for alias, rows in (("v1220-battleship-sonnet", 34), ("v1220-battleship-grok-medium-none", 30)):
            with self.subTest(run=alias):
                validation = self.fidelity.validation(run_dir_of(alias))
                self.assertEqual(validation["tests_ran_unmeasured"], rows)
                self.assertEqual(validation["by_suite"]["focused"]["counted"], 0)
                self.assertEqual(validation["by_suite"]["regression"]["counted"], 0)
        sonnet = self.fidelity.validation(run_dir_of("v1220-battleship-sonnet"))
        self.assertEqual((sonnet["by_suite"]["focused"]["counts_null"], sonnet["by_suite"]["regression"]["counts_null"]), (27, 7))
        grok = self.fidelity.validation(run_dir_of("v1220-battleship-grok-medium-none"))
        self.assertEqual((grok["by_suite"]["focused"]["counts_null"], grok["by_suite"]["regression"]["counts_null"]), (18, 12))

    def test_a_run_with_null_test_counts_says_so_in_unmeasured_and_never_reads_as_a_pass(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name) / "run"
        import shutil
        shutil.copytree(FIXTURES / "v1220-battleship-sonnet", out)
        block = self.fidelity.build(out, out / ".shiploop-runs" / "work-1" / "run", None)
        self.assertEqual(block["validation"]["tests_ran_unmeasured"], 34)
        self.assertIn("counts are null", block["unmeasured"]["validation.counts"])
        self.assertIn("S-9", block["unmeasured"]["validation.counts"])

    def test_check_rows_are_judged_by_exit_code_so_their_null_counts_are_not_unmeasured_tests(self):
        validation = replay("r1-battleship-sonnet")["block"]["validation"]
        self.assertEqual(validation["by_suite"]["check"]["counts_null"], 6)
        self.assertEqual(validation["tests_ran_unmeasured"], 0)
        self.assertNotIn("validation.counts", replay("r1-battleship-sonnet")["block"]["unmeasured"])

    def test_a_counted_row_that_ran_zero_tests_is_listed_not_passed(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        run_dir = Path(tmp.name) / "run"
        (run_dir / "tests").mkdir(parents=True)
        record = {"action": "nav-1", "stage": "test-green", "schema": "shiploop-test-loop/v1", "passed": True,
                  "runs": [{"command": "node --test", "suite": "focused", "counts": {"ran": 0, "failed": 0}, "status": "passed"},
                           {"command": "node --test x", "suite": "focused", "counts": {"ran": 3, "failed": 0}, "status": "passed"}]}
        (run_dir / "tests" / "nav-1-verify1.md").write_text("```shiploop-state\n" + json.dumps(record) + "\n```\n")
        validation = self.fidelity.validation(run_dir)
        self.assertEqual(validation["by_suite"]["focused"]["zero_ran"], 1)
        self.assertEqual(validation["by_suite"]["focused"]["counted"], 2)

    def test_a_record_of_another_schema_or_that_cannot_be_read_is_not_read_and_is_counted_apart(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        run_dir = Path(tmp.name) / "run"
        (run_dir / "tests").mkdir(parents=True)
        (run_dir / "tests" / "nav-1-verify1.md").write_text("```shiploop-state\n" + json.dumps(
            {"schema": "shiploop-test-loop/v2", "runs": [{"command": "x", "suite": "focused", "counts": None}]}) + "\n```\n")
        (run_dir / "tests" / "nav-2-verify1.md").write_text("no fence here\n")
        validation = self.fidelity.validation(run_dir)
        self.assertEqual((validation["records"], validation["unread"], validation["runs"]), (2, 2, 0))
        block = self.fidelity.build(Path(tmp.name), run_dir, None)
        self.assertIn("not read", block["unmeasured"]["validation.unread"])

    def test_the_release_verify_record_names_where_and_what_it_observed(self):
        for alias in ("r1-battleship-sonnet", "r3-checkers-sonnet", "r2-battleship-grok-none"):
            with self.subTest(run=alias):
                self.assertEqual(replay(alias)["block"]["validation"]["release_verify"],
                                 {"where": "returned-result", "kind": "fast-forward-merge"})
        self.assertIsNone(replay("v1230-battleship-sonnet")["block"]["validation"]["release_verify"])

    def test_a_run_directory_with_no_records_has_zero_of_them_and_no_run_directory_is_unmeasured(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        empty = Path(tmp.name) / "run"
        empty.mkdir()
        self.assertEqual(self.fidelity.validation(empty)["records"], 0)
        block = self.fidelity.build(Path(tmp.name), None, None)
        self.assertIsNone(block["validation"])
        self.assertIn("run directory", block["unmeasured"]["validation"])

    def test_the_regex_reader_and_the_json_reader_agree_on_all_eleven_saved_runs_and_the_two_v1220_runs(self):
        for alias in ELEVEN + V1220:
            with self.subTest(run=alias):
                run_dir = run_dir_of(alias)
                regex = metrics.verifications(run_dir)
                validation = self.fidelity.validation(run_dir)
                self.assertEqual(validation["records"], regex["records"])
                self.assertEqual(validation["passed"], regex["passed"])
                self.assertEqual(validation["red"], regex["red"])
                self.assertEqual(validation["could_not_run"], regex["could_not_run"])
                self.assertEqual(validation["runs"], regex["commands"])
                self.assertEqual(validation["unread"], 0)


class EditsTest(unittest.TestCase):
    def setUp(self):
        self.fidelity = fidelity_module()

    def test_the_two_round_1_sed_edits_of_return_plan_are_the_only_script_owned_edits_of_eleven_runs(self):
        found = {}
        for alias in ELEVEN:
            block = replay(alias)["block"]["edits"]
            if block["script_owned"]:
                found[alias] = [(e["event"], e["form"]) for e in block["script_owned"]]
        self.assertEqual(found, {"r1-battleship-sonnet": [(493, "sed -i")], "r1-checkers-sonnet": [(414, "sed -i")]})
        for alias in found:
            for edit in replay(alias)["block"]["edits"]["script_owned"]:
                self.assertTrue(edit["target"].endswith("return-plan.md"), edit)
                self.assertEqual(edit["tool"], "Bash")

    def test_the_python_heredoc_that_rewrote_return_plan_at_event_487_is_a_known_miss(self):
        command = command_at("r1-battleship-sonnet", 487)
        self.assertIn("return-plan.md", command)
        self.assertIn("open(", command)
        self.assertEqual(self.fidelity.shell_edits(command), [])
        self.assertNotIn(487, [e["event"] for e in replay("r1-battleship-sonnet")["block"]["edits"]["script_owned"]])

    def test_sed_in_place_and_redirects_on_script_owned_paths_are_edits_and_notes_inbox_and_the_product_are_not(self):
        run = "/runs/x/.shiploop-runs/work-1/run"
        cases = [
            (f"sed -i '' 's/a/b/' {run}/state.md", ["sed -i"]),
            (f"echo x > {run}/results/nav-1.md", [">"]),
            (f"echo x >> {run}/packets/nav-1.md", [">>"]),
            (f"printf x | tee {run}/tests/nav-1-verify1.md", ["tee"]),
            (f"cp /tmp/a {run}/quality/code-craft.md", ["cp"]),
            (f"mv {run}/lint/a.md /tmp/b", ["mv"]),
            (f"rm {run}/until-loop/innerloop-x.json", ["rm"]),
            (f"perl -pi -e 's/a/b/' {run}/state.md", ["perl -i"]),
            ("sed -i '' 's/a/b/' /runs/x/.shiploop-runs/work-1/return-plan.md", ["sed -i"]),
            (f"echo x > {run}/inbox/nav-1.json", []),
            (f"echo x > {run}/notes/intake.md", []),
            (f"echo x > {run}/scratch/sub.sh", []),
            (f"echo x > {run}/evidence/red.txt", []),
            ("echo x > /runs/x/.shiploop-runs/work-1/worktree/server.js", []),
            ("sed -i '' 's/a/b/' server.js", []),
            (f"rm {run}/notes/a.md > {run}/state.md", [">"]),
            (f"cat {run}/state.md", []),
            (f"grep -n a {run}/state.md > /tmp/out.txt", []),
            ("echo 'a > b' && ls", []),
        ]
        for command, forms in cases:
            with self.subTest(command=command):
                self.assertEqual([e["form"] for e in self.fidelity.shell_edits(command)], forms)

    def test_the_three_workspace_files_are_matched_by_name_after_a_cd_and_a_product_file_is_not(self):
        for name in ("return-plan.md", "return-receipt.md", "workspace.md"):
            with self.subTest(name=name):
                forms = [e["form"] for e in self.fidelity.shell_edits(f"cd $WS && sed -i '' 's/a/b/' {name}")]
                self.assertEqual(forms, ["sed -i"])
        self.assertEqual(self.fidelity.shell_edits("cd w && sed -i '' 's/a/b/' README.md"), [])
        self.assertEqual(self.fidelity.shell_edits("cd w && sed -i '' 's/a/b/' my-return-plan.md.bak"), [])

    def test_variables_the_command_assigns_are_expanded_before_the_owned_set_is_read(self):
        command = 'R=/runs/x/.shiploop-runs/work-1/run; sed -i "" "s/a/b/" $R/state.md'
        self.assertEqual([e["form"] for e in self.fidelity.shell_edits(command)], ["sed -i"])
        self.assertEqual(self.fidelity.shell_edits('R=/runs/x/.shiploop-runs/work-1/run; echo hi > $R/notes/a.md'), [])

    def test_a_heredoc_body_is_a_document_and_not_a_command(self):
        command = "cat > $R/notes/a.md <<'EOF'\nsed -i x /runs/x/.shiploop-runs/work-1/run/state.md\npkill -f node\ngit commit\nEOF"
        self.assertEqual(self.fidelity.shell_edits(command), [])
        self.assertEqual(self.fidelity.name_kills(command), [])
        self.assertEqual(self.fidelity.commit_forms(command), [])

    def test_an_edit_tool_on_a_script_owned_path_is_an_edit_on_claude_grok_and_codex_shapes(self):
        run = "/runs/x/.shiploop-runs/work-1/run"
        shapes = {
            "claude": ("Edit", {"file_path": f"{run}/state.md", "old_string": "a", "new_string": "b"}),
            "grok": ("write", {"path": f"{run}/results/nav-1.md", "content": "x"}),
            "grok-replace": ("search_replace", {"target_file": f"{run}/packets/nav-1.md"}),
            "codex": ("search_replace", {"target_file": f"{run}/backchain/nav-1/until-loop-start-contract.json",
                                         "paths": [f"{run}/backchain/nav-1/until-loop-start-contract.json"]}),
        }
        for shape, (tool, arg) in shapes.items():
            with self.subTest(shape=shape):
                log = metrics.ToolLog()
                log.call(1.0, "c", tool, arg, event=5)
                found = self.fidelity.edits(log)["script_owned"]
                self.assertEqual([(e["event"], e["tool"]) for e in found], [(5, tool)])
        log = metrics.ToolLog()
        log.call(1.0, "c", "write", {"path": f"{run}/inbox/nav-1.json"}, event=5)
        log.call(2.0, "d", "Write", {"file_path": f"{run}/scratch/sub.sh"}, event=6)
        log.call(3.0, "e", "Edit", {"file_path": "/runs/x/.shiploop-runs/work-1/worktree/server.js"}, event=7)
        log.call(4.0, "f", "Read", {"file_path": f"{run}/state.md"}, event=8)
        self.assertEqual(self.fidelity.edits(log)["script_owned"], [])

    def test_a_codex_file_change_naming_one_path_twice_is_one_edit(self):
        block = replay(CODEX, engine_scripts=OLD_TABLE)["block"]["edits"]
        self.assertEqual([(e["event"], e["tool"]) for e in block["script_owned"]], [(1012, "search_replace")])
        self.assertTrue(block["script_owned"][0]["target"].endswith("/until-loop-start-contract.json"))

    def test_name_pattern_kills_are_the_five_of_the_saved_runs_and_a_numeric_pid_kill_is_out_of_scope(self):
        found = {}
        for alias in ELEVEN:
            kills = replay(alias)["block"]["edits"]["name_kills"]
            if kills:
                found[alias] = [(k["event"], k["form"]) for k in kills]
        self.assertEqual(found, {
            "r2-checkers-sonnet": [(571, 'pkill -f "node server.js"')],
            "r3-checkers-sonnet": [(548, 'pkill -f "node server.js"')],
            "r2-battleship-grok-none": [(2838, 'pkill -f "node server.js"')],
            "r3-battleship-grok-none": [(858, 'pkill -f "http-probe.mjs"'), (7711, 'pkill -f "socketserver.TCPServer"')]})
        for command in ("kill 67975 67993", "kill $SERVER_PID", "kill $!", "kill -9 $(cat server.pid)", "echo pkill", "# pkill -f x",
                        "man pkill", "ls | grep killall"):
            with self.subTest(command=command):
                self.assertEqual(self.fidelity.name_kills(command), [])

    def test_the_kill_forms_that_match_by_name(self):
        cases = {
            'pkill -f "node server.js"': ['pkill -f "node server.js"'],
            "a; pkill node": ["pkill node"],
            "a && killall -9 node": ["killall -9 node"],
            "kill $(pgrep -f server.js)": ["kill $(pgrep -f server.js)"],
            "pgrep -f server.js | xargs kill": ["pgrep -f server.js | xargs kill"],
            "sudo pkill -f x": ["pkill -f x"],
            '/bin/zsh -lc "pkill -f node"': ["pkill -f node"],
            "if lsof -i :3000; then pkill -f server.js; fi": ["pkill -f server.js"],
            'pkill -f "http-probe.mjs" 2>/dev/null || true': ['pkill -f "http-probe.mjs"'],
        }
        for command, forms in cases.items():
            with self.subTest(command=command):
                self.assertEqual(self.fidelity.name_kills(command), forms)

    def test_nothing_in_the_detectors_can_signal_a_process(self):
        # The kill detector only reads strings: os.kill, os.killpg and subprocess fail the test if the code under test reaches them.
        def refuse(*args, **kwargs):
            raise AssertionError("the fidelity detectors must not signal or start a process")

        with mock.patch.object(os, "kill", refuse), mock.patch.object(os, "killpg", refuse), \
                mock.patch("subprocess.run", refuse), mock.patch("subprocess.Popen", refuse):
            block = self.fidelity.edits(replay("r2-checkers-sonnet")["tools"])
            self.assertEqual(len(block["name_kills"]), 1)

    def test_model_commit_commands_are_listed_per_call_and_agree_with_the_frozen_glue_reader_on_claude_and_grok(self):
        for alias in ELEVEN:
            with self.subTest(run=alias):
                run = replay(alias)
                listed = [c["event"] for c in run["block"]["edits"]["model_commits"]]
                glue = [g for g in run["metrics"]["model_glue"] if "git commit/add by the model" in g["reasons"]]
                self.assertEqual(len(listed), len(glue), "one meaning of a model commit command: the frozen glue reader's")
                self.assertEqual(len(listed), len(set(listed)))
        forms = replay("r1-battleship-sonnet")["block"]["edits"]["model_commits"]
        self.assertEqual([(c["event"], c["forms"]) for c in forms], [(463, ["git add", "git commit"])])

    def test_the_lists_are_unmeasured_when_the_stream_holds_no_tool_call(self):
        for label, tools in (("empty log", metrics.ToolLog()), ("no log", None)):
            with self.subTest(label):
                block = self.fidelity.build(FIXTURES / "r1-battleship-sonnet", run_dir_of("r1-battleship-sonnet"), tools,
                                            engine_scripts=CURRENT_TABLE, exporter=EXPORTER)
                self.assertIsNone(block["edits"])
                self.assertIsNone(block["refusals"])
                self.assertIn("no tool call", block["unmeasured"]["edits"])
                self.assertIn("no tool call", block["unmeasured"]["refusals"])
                self.assertIsNotNone(block["evidence"], "the parts that read the run folder do not need the stream")

    def test_the_list_says_it_is_a_lower_bound(self):
        self.assertIn("lower bound", replay("r1-battleship-sonnet")["block"]["edits"]["limits"])


class RefusalsTest(unittest.TestCase):
    def setUp(self):
        self.fidelity = fidelity_module()

    def test_the_count_equals_the_number_of_shiploop_failures_on_every_run(self):
        for alias in ELEVEN:
            with self.subTest(run=alias):
                run = replay(alias)
                self.assertEqual(run["block"]["refusals"]["count"], len(run["metrics"]["shiploop_failures"]))
                self.assertEqual(len(run["block"]["refusals"]["items"]), run["block"]["refusals"]["count"])

    def test_the_four_repeats_of_the_saved_runs_are_found_and_nothing_else_repeats(self):
        found = {}
        for alias in ELEVEN:
            refusals = replay(alias)["block"]["refusals"]
            repeats = [item["event"] for item in refusals["items"] if item["repeat_of"] is not None]
            if repeats:
                found[alias] = [(refusals["items"][item["repeat_of"]]["event"], item["event"]) for item in refusals["items"]
                                if item["repeat_of"] is not None]
            self.assertEqual(refusals["repeated"], len(repeats))
        self.assertEqual(found, {"r1-battleship-sonnet": [(447, 449)], "r2-checkers-sonnet": [(237, 239), (384, 410)],
                                 "r3-battleship-grok-none": [(1291, 1325)]})

    def test_each_refusal_names_its_verb_stage_and_line(self):
        items = replay("r2-checkers-sonnet")["block"]["refusals"]["items"]
        self.assertEqual([(i["event"], i["stage"]) for i in items],
                         [(99, "spec"), (237, "plan"), (239, "plan"), (384, "test-author"), (410, "test-author")])
        self.assertTrue(items[1]["line"].startswith("ShipLoop navigator: assumption A3 (open) needs exactly check, consumer, reason"))
        self.assertTrue(all(len(i["line"]) <= 200 for i in items))
        self.assertTrue(all(isinstance(i["verb"], str) for i in items))

    def test_a_refusal_found_by_a_nonzero_exit_without_a_refusal_line_is_counted_with_the_same_number_as_the_failures(self):
        run = replay("r2-battleship-sonnet")
        self.assertEqual(run["block"]["refusals"]["count"], 1)
        self.assertEqual(len(run["metrics"]["shiploop_failures"]), 1)

    def _items(self, lines, stages):
        """Refusals built by hand: a ToolLog fed refusal results at chosen events, joined to the given stage of each."""
        log = metrics.ToolLog()
        for index, line in enumerate(lines):
            log.call(float(index), f"c{index}", "Bash", {"command": "python3 /x/shiploop complete --run-dir r"}, event=10 * index)
            log.result(f"c{index}", line + "\n", 1, event=10 * index + 1)
        with mock.patch.object(self.fidelity, "stage_of", side_effect=lambda *a, **k: stages.pop(0)):
            return self.fidelity.refusals(log, Path("."), None, {})

    def test_a_changed_line_a_different_stage_or_an_unknown_stage_is_no_repeat(self):
        same = "ShipLoop navigator: " + "evidence " * 30
        self.assertEqual([i["repeat_of"] for i in self._items([same, same], ["plan", "plan"])["items"]], [None, 0])
        self.assertEqual([i["repeat_of"] for i in self._items([same, same], ["plan", "spec"])["items"]], [None, None])
        self.assertEqual([i["repeat_of"] for i in self._items([same, same], [None, None])["items"]], [None, None])
        self.assertEqual([i["repeat_of"] for i in self._items([same, same + "x"], ["plan", "plan"])["items"]], [None, None])

    def test_two_refusals_that_differ_only_after_the_200th_character_are_not_a_repeat(self):
        head = "ShipLoop navigator: evidence_refs cite files that do not exist: /runs/x/" + "a" * 150
        first, second = head + "/one.md", head + "/two.md"
        self.assertEqual(first[:200], second[:200])
        items = self._items([first, second], ["plan", "plan"])["items"]
        self.assertEqual([i["repeat_of"] for i in items], [None, None])
        self.assertEqual(items[0]["line"], items[1]["line"], "the recorded line is the 200-character one, like shiploop_failures")

    def test_a_repeat_is_of_the_refusal_just_before_it_and_not_of_an_earlier_one(self):
        same = "ShipLoop navigator: same"
        other = "ShipLoop navigator: other"
        items = self._items([same, other, same], ["plan", "plan", "plan"])["items"]
        self.assertEqual([i["repeat_of"] for i in items], [None, None, None])

    def test_the_stage_is_null_without_a_timeline(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name) / "r2-checkers-sonnet"
        import shutil
        shutil.copytree(FIXTURES / "r2-checkers-sonnet", out)
        (out / "timeline.jsonl").unlink()
        run_dir = out / ".shiploop-runs" / "work-1" / "run"
        tools = metrics.ToolLog()
        metrics.collect(out, run_dir, tools=tools)
        refusals = self.fidelity.refusals(tools, out, run_dir, metrics.engine_state(run_dir))
        self.assertEqual(refusals["count"], 5)
        self.assertEqual({i["stage"] for i in refusals["items"]}, {None})
        self.assertEqual(refusals["repeated"], 0, "a repeat needs a known stage")

    def test_a_refusal_behind_a_model_wrapper_script_is_found_from_the_result_text(self):
        # r3-battleship-sonnet wrapped the CLI in scratch scripts; the refusal at event 318 is read from the result.
        run = replay("r3-battleship-sonnet")
        self.assertEqual([i["event"] for i in run["block"]["refusals"]["items"]], [318])
        self.assertEqual(run["block"]["refusals"]["items"][0]["stage"], "test-green")


class EndStateTest(unittest.TestCase):
    def setUp(self):
        self.fidelity = fidelity_module()

    def test_a_blocked_run_records_blocked_by_awaiting_and_whether_it_stated_why_no_default_would_do(self):
        state = replay("v1230-battleship-grok-none")["block"]["end_state"]
        self.assertEqual((state["status"], state["stage"], state["blocked_by"]), ("blocked", "system-test", "access"))
        self.assertEqual(state["awaiting"], {"kind": "present", "no_default": True})
        self.assertTrue(state["status_reason"].startswith("access:"))
        self.assertIsNone(state["unaccepted_stage"], "the model reported the block and ShipLoop recorded it")
        r1 = replay("r1-battleship-grok-none")["block"]["end_state"]
        self.assertEqual((r1["status"], r1["blocked_by"], r1["awaiting"]), ("blocked", "access", {"kind": "answer", "no_default": True}))

    def test_a_stopped_run_with_an_active_engine_names_the_stage_it_never_accepted_and_claims_nothing(self):
        state = replay("r3-battleship-grok-none")["block"]["end_state"]
        self.assertEqual((state["status"], state["unaccepted_stage"]), ("active", "implement"))
        self.assertEqual((state["blocked_by"], state["awaiting"], state["status_reason"]), (None, None, None))

    def test_a_done_run_reports_the_unverified_entries_and_their_owners(self):
        state = replay("r2-battleship-sonnet")["block"]["end_state"]
        self.assertEqual(state["status"], "done")
        self.assertEqual(state["unverified"]["owners"], ["user"])
        self.assertGreaterEqual(state["unverified"]["entries"], 1)
        empty = replay("r2-checkers-sonnet")["block"]["end_state"]["unverified"]
        self.assertEqual(empty, {"entries": 0, "owners": []}, "an empty list says every request outcome was observed")

    def test_a_run_whose_results_carry_no_unverified_key_is_unmeasured_not_zero(self):
        block = replay("r1-battleship-sonnet")["block"]
        self.assertIsNone(block["end_state"]["unverified"])
        self.assertIn("unverified", block["unmeasured"]["end_state.unverified"])

    def test_no_state_is_unmeasured_with_a_reason(self):
        block = self.fidelity.build(Path("."), None, None)
        self.assertIsNone(block["end_state"])
        self.assertIn("state", block["unmeasured"]["end_state"])


class ImprovePacketsTest(unittest.TestCase):
    QUESTIONS = ("goal", "done_when", "checked_by", "output", "recovery")

    def setUp(self):
        self.fidelity = fidelity_module()

    def test_the_exporter_scores_producer_packets_only_so_the_five_questions_of_an_improve_packet_are_read_here(self):
        source = EXPORTER.read_text()
        self.assertIn("def carried_markers", source)
        for prefix in ("Reviewing the returned", "Recovery command:", "Checked by: the Improve skill"):
            self.assertNotIn(prefix, source, "the exporter scores Improve packets now: delete the harness's IMPROVE_QUESTIONS")

    def test_the_improve_packets_of_the_round_1_shape_lack_goal_and_done_when_and_the_round_3_shape_has_all_five(self):
        round1 = replay("r1-battleship-sonnet")["block"]["improve_packets"]
        self.assertEqual(round1["read"], 8)
        self.assertEqual(round1["carried"], {"goal": 0, "done_when": 0, "checked_by": 8, "output": 8, "recovery": 8})
        self.assertEqual({tuple(m["labels"]) for m in round1["missing"]}, {("goal", "done_when")})
        round3 = replay("r3-battleship-sonnet")["block"]["improve_packets"]
        self.assertEqual((round3["read"], round3["missing"]), (8, []))
        self.assertEqual(set(round3["carried"].values()), {8})

    def test_the_63_improve_packet_files_of_the_saved_runs_split_35_with_all_five_and_28_without_goal_and_done_when(self):
        both = without = 0
        per_run = {}
        for alias in ELEVEN:
            packets = replay(alias)["block"]["improve_packets"]
            if packets is None:
                per_run[alias] = None
                continue
            per_run[alias] = packets["read"]
            without += len(packets["missing"])
            both += packets["read"] - len(packets["missing"])
            for entry in packets["missing"]:
                self.assertEqual(entry["labels"], ["goal", "done_when"])
        self.assertEqual((both + without, both, without), (63, 35, 28))
        self.assertEqual(per_run["r3-battleship-grok-none"], None, "no Improve child ran in that run")
        self.assertEqual(per_run["r2-battleship-grok-none"], 3)

    def test_a_missing_entry_names_the_action_and_its_stage(self):
        missing = replay("r1-battleship-sonnet")["block"]["improve_packets"]["missing"]
        self.assertEqual(len(missing), 8)
        self.assertTrue(all(re.fullmatch(r"nav-[0-9a-f]+", m["action"]) for m in missing))
        self.assertIn("carry-forward", {m["stage"] for m in missing})

    def test_a_run_of_the_old_layout_with_improve_children_but_no_improve_files_is_unmeasured_not_missing(self):
        block = replay(CODEX, engine_scripts=OLD_TABLE)["block"]
        self.assertIsNone(block["improve_packets"])
        self.assertIn("-improve.md", block["unmeasured"]["improve_packets"])

    def test_the_block_holds_the_label_booleans_only_never_the_packet_text(self):
        self.assertNotIn("Reviewing the returned", json.dumps(replay("r3-battleship-sonnet")["block"]))

    def test_the_five_patterns_are_the_engines_own_strings(self):
        navigator = (ENGINE / "shiploop_navigator.py").read_text()
        for prefix in ("Reviewing the returned ", "Goal: ", "Done when (", "Checked by: ", "The opening file holds exactly these headings",
                       "Then run: ", "Recovery command:"):
            with self.subTest(prefix=prefix):
                self.assertIn(prefix, navigator, "the engine's wording moved: update fidelity.IMPROVE_QUESTIONS")
        self.assertEqual([name for name, _ in self.fidelity.IMPROVE_QUESTIONS], list(self.QUESTIONS))

    def test_the_patterns_match_a_line_start_so_prose_that_mentions_a_label_is_not_one(self):
        patterns = dict(self.fidelity.IMPROVE_QUESTIONS)
        self.assertTrue(patterns["done_when"].search("Done when (a done result must meet each):"))
        self.assertFalse(patterns["done_when"].search("The text says Done when (x) later"))
        self.assertTrue(patterns["goal"].search("Reviewing the returned spec result. Goal: Write it."))
        self.assertFalse(patterns["goal"].search("Goal: Write it."), "the producer packet's own Goal line is not the Improve packet's")


class WorkspaceFilesTest(unittest.TestCase):
    def test_the_three_workspace_files_are_the_names_the_engine_writes(self):
        source = (ENGINE / "shiploop_workspace.py").read_text()
        for constant, name in (("MANIFEST", "workspace.md"), ("RETURN_PLAN", "return-plan.md"), ("RETURN_RECEIPT", "return-receipt.md")):
            self.assertRegex(source, rf'(?m)^{constant} = "{re.escape(name)}"$')
        self.assertEqual(set(fidelity_module().WORKSPACE_FILES), {"workspace.md", "return-plan.md", "return-receipt.md"})


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.fidelity = fidelity_module()

    def test_the_block_names_its_schema_the_hosts_and_every_part(self):
        block = replay("r2-battleship-grok-none")["block"]
        self.assertEqual(block["schema"], "shiploop-e2e-fidelity/v1")
        self.assertEqual(block["hosts"], ["grok", "claude"])
        self.assertTrue(block["mixed_host"])
        for part in ("evidence", "validation", "edits", "refusals", "end_state", "improve_packets"):
            self.assertIn(part, block)
        self.assertGreater(block["tool_calls_seen"], 0)
        self.assertFalse(replay("r1-battleship-sonnet")["block"]["mixed_host"])

    def test_a_part_that_raises_is_unmeasured_with_its_reason_and_the_other_parts_still_run(self):
        with mock.patch.object(self.fidelity, "validation", side_effect=RuntimeError("boom in validation")):
            block = self.fidelity.build(FIXTURES / "r1-battleship-sonnet", run_dir_of("r1-battleship-sonnet"), metrics.ToolLog(),
                                        engine_scripts=CURRENT_TABLE, exporter=EXPORTER)
        self.assertIsNone(block["validation"])
        self.assertIn("RuntimeError", block["unmeasured"]["validation"])
        self.assertIn("boom in validation", block["unmeasured"]["validation"])
        self.assertIsNotNone(block["evidence"])
        self.assertIsNotNone(block["end_state"])

    def test_every_known_gap_is_a_reason_string_and_no_part_is_zero_where_it_was_not_measured(self):
        block = self.fidelity.build(Path("."), None, None)
        reasons = {"evidence": "no history", "validation": "run directory", "end_state": "no status", "improve_packets": "-improve.md",
                   "edits": "no tool call", "refusals": "no tool call"}
        for part, word in reasons.items():
            self.assertIsNone(block[part], part)
            self.assertIn(word, block["unmeasured"][part], part)

    def test_the_block_is_json_and_small(self):
        text = json.dumps(replay("r2-battleship-grok-none")["block"])
        json.loads(text)
        self.assertLess(len(text), 60_000)

    def test_lines_print_at_most_five_and_each_says_what_it_did_not_check(self):
        for alias in ELEVEN:
            with self.subTest(run=alias):
                lines = self.fidelity.lines(replay(alias)["block"])
                self.assertLessEqual(len(lines), 5)
                self.assertTrue(all(isinstance(line, str) and line for line in lines))
        lines = self.fidelity.lines(replay("r1-battleship-sonnet")["block"])
        joined = "\n".join(lines)
        self.assertIn("script 15, loop 7, file 1, note 12, sentence 0, skipped 2", lines[0])
        self.assertIn("(records: verify 10, lint ", lines[0])
        self.assertIn(", improve 8)", lines[0], "the precedence hides a review loop behind a script record; the records line shows it")
        self.assertIn("script-owned edits 1", joined)
        self.assertIn("no hit is not proof", joined)
        self.assertNotIn("lower bound", joined, "the report's cost note owns that phrase")
        self.assertIn("repeated 1", joined)

    def test_lines_of_a_block_with_unmeasured_parts_say_unmeasured_and_never_zero(self):
        lines = self.fidelity.lines(self.fidelity.build(Path("."), None, None))
        self.assertLessEqual(len(lines), 5)
        self.assertTrue(any("unmeasured" in line for line in lines))
        self.assertFalse(any(re.search(r"\b(?:edits|kills|refusals) 0\b", line) for line in lines), lines)

    def test_a_block_that_failed_to_build_prints_one_skipped_line(self):
        self.assertEqual(self.fidelity.lines({"schema": "x", "error": "RuntimeError: nope"}), ["skipped: RuntimeError: nope"])

    def test_safe_build_turns_any_exception_into_an_error_block(self):
        with mock.patch.object(self.fidelity, "build", side_effect=ValueError("bad state")):
            block = self.fidelity.safe_build(Path("."), None, None)
        self.assertEqual(block["error"], "ValueError: bad state")
        self.assertEqual(block["schema"], "shiploop-e2e-fidelity/v1")


def load_harness_tests():
    spec = importlib.util.spec_from_file_location("e2e_harness_tests", ROOT / "test" / "shiploop-e2e.test.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


HARNESS = load_harness_tests()


class FidelityThroughMainTest(HARNESS.PrintedCase):
    """run._main builds the block once, writes it to metrics.json only, prints at most five lines and never lets it change a verdict."""

    def setUp(self):
        super().setUp()
        HARNESS.isolate_git(self)
        self.fidelity = fidelity_module()

    def written(self, host="grok", mode="done", *extra):
        code, result, printed = self.invoke_printed(host, mode, *extra)
        out = Path(result["output"])
        return code, result, printed, json.loads((out / "metrics.json").read_text()), out

    def test_metrics_json_carries_the_block_and_result_json_does_not(self):
        for host in ("claude", "grok", "codex"):
            with self.subTest(host=host):
                code, result, printed, written, out = self.written(host)
                self.assertEqual(code, 0, result)
                self.assertEqual(written["fidelity"]["schema"], "shiploop-e2e-fidelity/v1")
                self.assertNotIn("fidelity", result["metrics"], "result.json keeps its explicit subset; metrics.json is the evidence")
                self.assertNotIn("fidelity", json.loads((out / "result.json").read_text()))

    def test_the_report_prints_at_most_five_fidelity_lines_after_the_metrics_lines(self):
        code, result, printed, written, out = self.written("grok")
        lines = [ln for ln in printed.splitlines() if ln.startswith("  fidelity")]
        self.assertTrue(1 <= len(lines) <= 5, printed)
        order = [ln.split()[0] for ln in printed.splitlines() if ln.startswith("  ")]
        self.assertGreater(order.index("fidelity"), max(i for i, name in enumerate(order) if name == "metrics"))

    def test_a_builder_failure_is_recorded_and_changes_neither_the_verdict_nor_the_exit_code_nor_the_baseline_row(self):
        _, clean_result, _, _, _ = self.written("grok")
        clean_row = self.last_row()
        self.baselines.unlink()
        with mock.patch.object(self.fidelity, "build", side_effect=RuntimeError("builder broke")):
            code, result, printed, written, out = self.written("grok")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["pass"], clean_result["pass"])
        self.assertEqual(written["fidelity"], {"schema": "shiploop-e2e-fidelity/v1", "error": "RuntimeError: builder broke"})
        self.assertIn("  fidelity  skipped: RuntimeError: builder broke", printed)
        row = self.last_row()
        for key in ("turns", "cost_usd", "sessions", "model_glue", "stages", "unmeasured"):
            self.assertEqual(row[key], clean_row[key], key)

    def test_the_baseline_row_has_no_fidelity_key(self):
        self.written("grok")
        self.assertNotIn("fidelity", self.last_row())

    def test_grade_only_adds_the_block_to_a_run_that_had_none(self):
        code, result, printed, written, out = self.written("grok")
        metrics_file = out / "metrics.json"
        old = json.loads(metrics_file.read_text())
        del old["fidelity"]
        metrics_file.write_text(json.dumps(old))
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            HARNESS.run.main(["--resume-run", str(out), "--grade-only", "--baseline", str(self.baselines),
                              "--plugin-dir", str(self.plugin)])
        self.assertEqual(json.loads(metrics_file.read_text())["fidelity"]["schema"], "shiploop-e2e-fidelity/v1")
        self.assertIn("  fidelity  ", printed.getvalue())
        self.assertNotIn("fidelity", json.loads((out / "result.json").read_text())["metrics"])

    def test_collect_without_a_tool_log_is_what_progress_calls_and_it_is_unchanged(self):
        code, result, printed, written, out = self.written("grok")
        again = metrics.collect(out, Path(result["shiploop"]["run_dir"]) if result["shiploop"].get("run_dir") else None)
        self.assertNotIn("fidelity", again)


if __name__ == "__main__":
    unittest.main()
