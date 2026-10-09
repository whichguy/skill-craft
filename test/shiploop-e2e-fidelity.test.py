#!/usr/bin/env python3
"""No-model checks for test/shiploop_e2e/fidelity.py: the record-only `fidelity` block of metrics.json (SPEC 2026-10-09).

The replay tests read the compact extracts of twelve saved runs under test/fixtures/fidelity (cut by its extract.py from the
run folders of 2026-10-05, 2026-10-07 and 2026-10-08) and two extracts of the 2026-10-06 verify records, never the machine's
run folders. Each events.jsonl keeps its selected events at their original line numbers, so `event 493` below is the 0-based line
index 493 of the saved stream (line 494 in an editor). The host-stream shapes are the harness's own (Claude tool_use and
tool_result blocks, Grok tool_call and tool_call_update events, Codex through its translator). No test starts a host, a model or a
listener, signals a process, or reads the machine's process table.

What the extracts can and cannot show (their limits are the tests' limits). extract.py keeps every call whose command or paths
mention a run, workspace, Improve or Until Loop directory, a kill or git, or that writes in place or names a workspace file, and
leaves the rest blank; a call that writes an owned file through a path built in a variable set by an EARLIER call is not recognised
by the extractor (no saved run does it). Results are kept only for refused or failed ShipLoop calls, and a heredoc body over 600
characters is cut, which can lose a ShipLoop verb that only the body named (the Codex run has 9 of its 10 refusals). The figures of
the uncut runs are in the journal; a pin here is a pin on the extract.
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


def stage_table_dir(tmp: Path, planning_choice: bool = True, extra_run: str | None = None) -> Path:
    """A stand-in for <engine scripts>/shiploop_stage_spec.py built from the engine's table as test/fixtures/fidelity/extract.py
    froze it, so a later change to the engine's table cannot move a saved run's declared checks. Without
    PLANNING_CHOICE_STAGES it is the shape of the 1.21.0 table, which the exporter's stage_catalog cannot read."""
    table = json.loads((FIXTURES / "stage_table.json").read_text())
    rows = {name: {"goal": name, **row} for name, row in table["rows"].items()}
    if extra_run:  # a run the harness has no record kind for, declared by test-green
        rows["test-green"]["complete_runs"] = [*rows["test-green"]["complete_runs"], extra_run]
    source = ("from types import SimpleNamespace as N\n"
              f"STAGES = {tuple(table['stages'])!r}\n"
              "STAGE_SPEC = {n: N(goal=r['goal'], complete_runs=frozenset(r['complete_runs']), improve=r['improve'] or None,"
              " reads=tuple(r['reads'])) for n, r in " + repr(rows) + ".items()}\n"
              + (f"PLANNING_CHOICE_STAGES = frozenset({table['planning_choice_stages']!r})\n" if planning_choice else ""))
    scripts = tmp / ("scripts" if planning_choice and not extra_run else "scripts-1.21.0" if not planning_choice else "scripts-extra")
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


class SharedHelpersTest(unittest.TestCase):
    """One constant, one window rule and one path reader for the metrics and the fidelity block (review B11, B18)."""

    def test_the_not_applicable_prefix_is_one_constant_and_it_is_the_engines_own(self):
        engine = (ENGINE / "shiploop_item_scope.py").read_text()
        self.assertIn(f'NOT_APPLICABLE = "{metrics.NOT_APPLICABLE}"', engine)
        literal = "Not applicable to this item"
        self.assertEqual((ROOT / "test" / "shiploop_e2e" / "metrics.py").read_text().count(literal), 1,
                         "metrics.py defines the prefix once and the narrative reader uses the constant")
        self.assertNotIn(literal, (ROOT / "test" / "shiploop_e2e" / "fidelity.py").read_text(),
                         "fidelity.py uses metrics.NOT_APPLICABLE and does not repeat the literal")

    def test_the_narrative_reader_still_skips_the_engines_not_applicable_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            (run_dir / "results").mkdir(parents=True)
            for name, summary in (("a.md", "Not applicable to this item: no tests"), ("b.md", "did the work")):
                (run_dir / "results" / name).write_text("```shiploop-state\n" + json.dumps(
                    {"result": {"summary": summary, "headline": "h"}}) + "\n```\n")
            self.assertEqual(metrics.narrative(Path(tmp), run_dir)["results"], 1)

    def test_a_stage_window_holds_its_end_and_not_its_start(self):
        self.assertTrue(metrics.within(5.0, 4.0, 5.0))
        self.assertFalse(metrics.within(4.0, 4.0, 5.0))
        self.assertFalse(metrics.within(5.1, 4.0, 5.0))

    def test_an_event_on_a_stage_boundary_belongs_to_the_stage_that_ends_there(self):
        fidelity = fidelity_module()
        stamps = {1: 10.0, 2: 10.5, 3: 0.0, 4: 25.0}
        windows = [(0.0, 10.0, 0.0), (10.0, 20.0, 10.0)]
        self.assertEqual([fidelity.stage_of(n, stamps, ["a", "b"], windows) for n in (1, 2, 3, 4, 9)], ["a", "b", None, None, None])

    def test_the_target_of_a_call_is_the_first_path_target_paths_names(self):
        log = metrics.ToolLog()
        log.call(1.0, "c1", "Read", {"paths": ["/r/.shiploop-runs/w/run/packets/nav-1.md"]}, event=1)
        self.assertTrue(log.calls["c1"]["packet"])
        self.assertEqual(log.calls["c1"]["file"], "/r/.shiploop-runs/w/run/packets/nav-1.md")
        log.call(2.0, "c2", "Read", {"target_file": "/a/b.md", "paths": ["/c/d.md"]}, event=2)
        self.assertEqual(log.calls["c2"]["file"], "/a/b.md")
        log.call(3.0, "c3", "Bash", {"command": "ls"}, event=3)
        self.assertEqual(log.calls["c3"]["file"], "")


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

    def test_a_wrapper_whose_quoting_is_concatenated_is_unwrapped_by_the_shells_own_rules(self):
        # Review A11: 34 of the 1356 Codex commands of the 1.21.0 run write "..."'...' and were not unwrapped by the regular expression.
        wrapped = "/bin/zsh -lc \"git commit -m x; P=\"'$HOME'"
        self.assertEqual(self.fidelity.unwrap_shell(wrapped), "git commit -m x; P=$HOME")
        self.assertEqual(self.fidelity.commit_forms(wrapped), ["git commit"])
        self.assertEqual(self.fidelity.unwrap_shell("bash -c 'echo a' extra"), "bash -c 'echo a' extra", "more than one script is no wrapper")
        self.assertEqual(self.fidelity.unwrap_shell('bash -c "a" && echo "b"'), 'bash -c "a" && echo "b"')

    def test_a_wrapper_the_shell_cannot_read_is_stripped_by_pattern_when_it_spans_the_command(self):
        # Unbalanced quoting (a model's `it's` inside single quotes): shlex fails, the pattern still finds the wrapper.
        wrapped = "bash -c 'git commit -m it's'"
        self.assertEqual(self.fidelity.unwrap_shell(wrapped), "git commit -m it's")
        self.assertEqual(self.fidelity.commit_forms(wrapped), ["git commit"])
        self.assertEqual(self.fidelity.unwrap_shell("bash -c 'git commit -m it's' && ls"), "bash -c 'git commit -m it's' && ls")

    def test_every_wrapped_command_of_the_codex_extract_is_unwrapped(self):
        # A heredoc body the extractor cut can unbalance the quoting of its wrapper (21 of them), so only the uncut ones are asserted; on the
        # uncut run folder all 1356 wrapped commands of the 1.21.0 run unwrap (checked by the journal's run, not by this test).
        wrapped = [c["command"] for c in replay(CODEX, engine_scripts=OLD_TABLE)["tools"].sequence
                   if c["command"].startswith("/bin/zsh -lc ") and "[body cut]" not in c["command"]]
        self.assertGreater(len(wrapped), 500)
        left = [c[:60] for c in wrapped if self.fidelity.unwrap_shell(c).startswith("/bin/zsh -lc ")]
        self.assertEqual(left, [])
        # and at least one of them is of the concatenated form the regular expression could not read
        self.assertTrue([c for c in wrapped if re.search(r"\"'", c)])

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
        # Review A7: a subcommand that is not add or commit is not a commit form, whatever else the line says.
        for command in ("git worktree add ../w", "git remote add origin x", "git notes add -m x", "git submodule add url y",
                        "git log --grep add", "git diff --stat; git show HEAD -- commit.md", "git commit-tree abc", "git stash",
                        'echo "git commit -m x"', "echo git add"):
            with self.subTest(command=command):
                self.assertEqual(self.fidelity.commit_forms(command), [])
        # Quoted text that says git is no command; a command that follows a quoted string on the same line still is.
        self.assertEqual(self.fidelity.commit_forms('echo "done; git commit -m x"'), [])
        self.assertEqual(self.fidelity.commit_forms('git commit -m "a; git add b"'), ["git commit"])
        # a commit after then, do, else, an opening parenthesis, env, xargs or a variable assignment is found.
        for command, forms in (("if x; then git commit -m y; fi", ["git commit"]), ("for f in a; do git add $f; done", ["git add"]),
                               ("(git add -A)", ["git add"]), ("env GIT_AUTHOR_NAME=a git commit -m x", ["git commit"]),
                               ("echo a | xargs git add", ["git add"]), ("GIT_AUTHOR_NAME=a git commit -m x", ["git commit"]),
                               ("x || git commit -m y", ["git commit"])):
            with self.subTest(command=command):
                self.assertEqual(self.fidelity.commit_forms(command), forms)
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
        self.assertIn(f'NOT_APPLICABLE = "{metrics.NOT_APPLICABLE}"', source)
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

    def run_state(self, history, accepted=None, lint="fix"):
        """A minimal state.md body: one history entry per (action, stage, outcome) and an accepted result for each."""
        return {"status": "done", "lint": lint,
                "history": [{"action": a, "stage": s, "outcome": o, "summary": ""} for a, s, o in history],
                "accepted": accepted if accepted is not None else {
                    a: {"outcome": o, "summary": "did it", "evidence_refs": ["/r/.shiploop-runs/w/worktree/x.md"]}
                    for a, s, o in history}}

    def test_a_stage_declaring_two_scripts_is_listed_when_one_of_them_left_no_record(self):
        # Review A1: test-green and regression declare [lint-gate, test-loop] and static-checks [quality-terminal, test-rerun]; a lint or
        # quality record alone must not satisfy them. The deletion is exactly the review's: only tests/<action>-verify*.md of three stages.
        for alias in ("r3-battleship-sonnet", "r1-battleship-sonnet"):
            with self.subTest(run=alias), tempfile.TemporaryDirectory() as tmp:
                shown = Path(tmp) / alias
                self.copy_run(alias, shown)
                run_dir = shown / ".shiploop-runs" / "work-1" / "run"
                wanted = {"test-green", "regression", "static-checks"}
                actions = {h["action"]: h["stage"] for h in metrics.engine_state(run_dir)["history"] if h["stage"] in wanted}
                self.assertEqual(set(actions.values()), wanted)
                for action in actions:
                    for record in (run_dir / "tests").glob(f"{action}-verify*.md"):
                        record.unlink()
                block = self.fidelity.build(shown, run_dir, metrics.ToolLog(), engine_scripts=CURRENT_TABLE, exporter=EXPORTER)
                evidence = block["evidence"]
                self.assertEqual(sorted(set(evidence["declared_script_run_without_record"])), sorted(wanted))
                rows = [r for r in evidence["stages"] if r["action"] in actions]
                self.assertEqual({r["stage"]: r["lacks"] for r in rows}, {"test-green": ["verify"], "regression": ["verify"],
                                                                         "static-checks": ["verify"]})
                self.assertEqual({r["class"] for r in rows}, {"script"}, "the class still comes from the records that exist")
                self.assertEqual(replay(alias)["block"]["evidence"]["declared_script_run_without_record"], [])

    def test_the_kinds_a_stage_needs_come_from_the_runs_its_table_row_declares(self):
        declared = {"test-green": {"check": "script-run", "runs": ["lint-gate", "test-loop"]},
                    "static-checks": {"check": "script-run", "runs": ["quality-terminal", "test-rerun"]},
                    "test-author": {"check": "script-run", "runs": ["test-probe"]},
                    "test-red": {"check": "script-run", "runs": ["test-red"]},
                    "intake": {"check": "model judgement", "runs": []}}
        run_dir = Path("/nonexistent-run-dir")
        state = self.run_state([("a", "test-green", "done"), ("b", "static-checks", "done"), ("c", "test-author", "done"),
                                ("d", "test-red", "done"), ("e", "intake", "done")])
        rows = {r["stage"]: r for r in self.fidelity.evidence(run_dir, state, declared)["stages"]}
        self.assertEqual({k: (r["needs"], r["lacks"]) for k, r in rows.items()}, {
            "test-green": (["lint", "verify"], ["lint", "verify"]), "static-checks": (["quality", "verify"], ["quality", "verify"]),
            "test-author": (["verify"], ["verify"]), "test-red": (["verify"], ["verify"]), "intake": ([], [])})

    def test_a_run_with_the_lint_option_off_does_not_need_a_lint_gate_record(self):
        declared = {"implement": {"check": "script-run", "runs": ["lint-gate"]}, "test-green": {"check": "script-run", "runs": ["lint-gate", "test-loop"]}}
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            (run_dir / "tests").mkdir(parents=True)
            (run_dir / "tests" / "b-verify1.md").write_text("x")
            # test-green keeps its verify record, so with the lint option on it lacks the gate only; with it off it lacks nothing.
            for lint, listed in (("off", []), ("fix", ["implement", "test-green"]), ("report", ["implement", "test-green"])):
                with self.subTest(lint=lint):
                    state = self.run_state([("a", "implement", "done"), ("b", "test-green", "done")], lint=lint)
                    evidence = self.fidelity.evidence(run_dir, state, declared)
                    self.assertEqual(evidence["declared_script_run_without_record"], listed)
                    if lint == "off":
                        self.assertEqual([r["needs"] for r in evidence["stages"]], [[], ["verify"]])

    def test_a_declared_run_the_reader_does_not_know_is_not_judged_and_is_named(self):
        declared = {"test-green": {"check": "script-run", "runs": ["lint-gate", "future-run"]}}
        with tempfile.TemporaryDirectory() as tmp:
            evidence = self.fidelity.evidence(Path(tmp), self.run_state([("a", "test-green", "done")]), declared)
        self.assertEqual(evidence["declared_script_run_without_record"], [])
        self.assertEqual(evidence["stages"][0]["needs"], None)
        self.assertEqual(evidence["unmapped_runs"], ["future-run"])

    def test_a_stage_table_with_an_unknown_run_is_named_in_the_block_and_those_stages_are_not_judged(self):
        scripts = stage_table_dir(Path(_TABLE_TMP.name), extra_run="future-run")
        block = replay("r1-battleship-sonnet", engine_scripts=scripts)["block"]
        self.assertIn("future-run", block["unmeasured"]["declared.runs"])
        self.assertEqual(block["evidence"]["declared_script_run_without_record"], [])
        self.assertEqual({r["needs"] for r in block["evidence"]["stages"] if r["stage"] == "test-green"}, {None})

    def test_a_skipped_stage_declaring_scripts_is_not_listed_and_the_same_stage_not_skipped_is(self):
        declared = {"test-green": {"check": "script-run", "runs": ["lint-gate", "test-loop"]}}
        with tempfile.TemporaryDirectory() as tmp:
            for summary, listed in (("Not applicable to this item: no tests", []), ("did the work", ["test-green"])):
                with self.subTest(summary=summary):
                    state = self.run_state([("a", "test-green", "done")], accepted={"a": {"outcome": "done", "summary": summary, "evidence_refs": []}})
                    evidence = self.fidelity.evidence(Path(tmp), state, declared)
                    self.assertEqual(evidence["declared_script_run_without_record"], listed)
                    self.assertEqual(evidence["stages"][0]["class"], "skipped" if not listed else "sentence")

    def test_only_the_lint_gate_is_lint_evidence_an_advisory_pass_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            (run_dir / "lint").mkdir(parents=True)
            state = self.run_state([("nav-1", "implement", "done")])
            for name in ("nav-1.md", "nav-1.1.md", "nav-1.2.md", "nav-1-inventory.md"):
                (run_dir / "lint" / name).write_text("advisory")
            row = self.fidelity.evidence(run_dir, state, None)["stages"][0]
            self.assertEqual((row["records"], row["class"]), ([], "file"))
            (run_dir / "lint" / "nav-1.gate1.md").write_text("gate")
            row = self.fidelity.evidence(run_dir, state, None)["stages"][0]
            self.assertEqual((row["records"], row["class"]), (["lint"], "script"))

    def test_a_quality_terminal_record_and_a_backchain_check_are_script_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            (run_dir / "quality").mkdir(parents=True)
            (run_dir / "backchain" / "nav-2").mkdir(parents=True)
            (run_dir / "quality" / "nav-1-terminal.json").write_text("{}")
            (run_dir / "backchain" / "nav-2" / "check-abc.json").write_text("{}")
            state = self.run_state([("nav-1", "static-checks", "done"), ("nav-2", "plan", "done")])
            rows = {r["action"]: r for r in self.fidelity.evidence(run_dir, state, None)["stages"]}
            self.assertEqual((rows["nav-1"]["records"], rows["nav-1"]["class"]), (["quality"], "script"))
            self.assertEqual((rows["nav-2"]["records"], rows["nav-2"]["class"]), (["backchain"], "script"))

    def test_a_ref_is_the_rows_own_only_when_it_names_the_rows_action(self):
        run = "/r/.shiploop-runs/w/run"
        cases = [(f"{run}/packets/nav-1.md", "own"), (f"{run}/packets/nav-1-improve.md", "own"), (f"{run}/inbox/nav-1.json", "own"),
                 (f"{run}/results/nav-1.md", "own"),
                 (f"{run}/results/nav-2.md", "outside"), (f"{run}/inbox/nav-12.json", "note"), (f"{run}/packets/nav-2.md", "outside"),
                 (f"{run}/notes/intake.md", "note"), ("/r/.shiploop-runs/w/worktree/docs/spec.md", "outside")]
        for ref, kind in cases:
            with self.subTest(ref=ref):
                found = self.fidelity._refs({"evidence_refs": [ref]}, "nav-1")
                self.assertEqual({k: v for k, v in found.items() if v}, {kind: 1})

    def test_a_stage_that_cites_another_actions_result_cites_a_file_not_nothing(self):
        # v1230-battleship-sonnet skill-validate cites the result of an earlier action: evidence of an earlier step, so not a sentence.
        rows = [r for r in replay("v1230-battleship-sonnet")["block"]["evidence"]["stages"] if r["stage"] == "skill-validate"]
        self.assertTrue(rows)
        self.assertEqual({r["class"] for r in rows}, {"file"})

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

    def test_the_block_holds_no_packet_text(self):
        text = json.dumps(replay("r1-battleship-sonnet")["block"])
        self.assertNotIn("Result template:", text)
        self.assertNotIn("Reviewing the returned", text)

    def test_the_block_names_the_run_folder_and_the_home_folder_by_a_placeholder_not_by_the_machine(self):
        # Review A9/B: a block that names /Users/<name> is not portable. The saved extracts were already path-rewritten by extract.py, so
        # this runs on a copy whose events and state name the copy's real temporary path, as a live run's do.
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "r1-battleship-sonnet"
            self.copy_run("r1-battleship-sonnet", out)
            real = str(out.resolve())
            for path in list(out.rglob("events.jsonl")) + list(out.rglob("state.md")):
                path.write_text(path.read_text().replace("/runs/r1-battleship-sonnet", real))
            run_dir = out / ".shiploop-runs" / "work-1" / "run"
            tools = metrics.ToolLog()
            metrics.collect(out, run_dir, tools=tools)
            block = self.fidelity.build(out, run_dir, tools, engine_scripts=CURRENT_TABLE, exporter=EXPORTER)
            text = json.dumps(block)
            self.assertNotIn(real, text)
            self.assertNotIn(tmp, text)
            edit = block["edits"]["script_owned"][0]
            self.assertTrue(edit["target"].startswith("<run>/.shiploop-runs/work-1/"), edit["target"])
            self.assertTrue(any("<run>/" in item["line"] for item in block["refusals"]["items"]))
            self.assertNotIn("/Users/", text)

    def test_portable_replaces_the_run_folder_first_and_then_the_home_folder_in_every_string(self):
        out = Path(tempfile.gettempdir()).resolve() / "case-folder"
        home = str(Path.home())
        value = {"a": f"{out}/work/x.md", "b": [f"{home}/skills/s.md", f"{out}"], "c": {"d": f"see {out}/y and {home}/z"}, "n": 3, "none": None}
        self.assertEqual(self.fidelity.portable(value, out), {"a": "<run>/work/x.md", "b": ["~/skills/s.md", "<run>"],
                                                              "c": {"d": "see <run>/y and ~/z"}, "n": 3, "none": None})
        # a run folder given as a relative path names no machine: its resolved form is not replaced (only the home folder is)
        resolved = str(Path("relative-case").resolve())
        self.assertEqual(self.fidelity.portable({"a": f"{resolved}/x", "b": "relative-case/x"}, Path("relative-case")),
                         {"a": f"{resolved}/x".replace(home, "~"), "b": "relative-case/x"})
        # the run folder is usually inside the home folder, and then it must become <run>, not ~/...
        inside = Path(home) / "x-case-folder"
        self.assertEqual(self.fidelity.portable({"a": f"{inside}/work/y", "b": f"{home}/other"}, inside), {"a": "<run>/work/y", "b": "~/other"})

    def test_a_private_prefix_of_the_run_folder_is_replaced_too(self):
        # macOS reports /var/folders/... as /private/var/folders/...; a model's command may carry either.
        out = Path(tempfile.gettempdir()).resolve() / "case-folder"
        plain = str(out)[len("/private"):] if str(out).startswith("/private/") else str(out)
        self.assertEqual(self.fidelity.portable({"a": f"{plain}/x"}, out), {"a": "<run>/x"})

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

    def release_record(self, run_dir: Path, number: int, created_at: str | None, passed, where="returned-result", observed=True):
        record = {"schema": "shiploop-test-loop/v1", "action": "nav-rel", "stage": "release-verify", "passed": passed,
                  "runs": [{"command": "node --test", "suite": "check", "counts": None, "status": "passed" if passed else "failed"}]}
        if created_at:
            record["created_at"] = created_at
        if observed:
            record["observed"] = {"kind": "fast-forward-merge", **({"where": where} if where else {})}
        (run_dir / "tests").mkdir(parents=True, exist_ok=True)
        (run_dir / "tests" / f"nav-rel-verify{number}.md").write_text("```shiploop-state\n" + json.dumps(record) + "\n```\n")

    def test_the_release_verify_record_names_where_what_it_observed_and_its_own_passed(self):
        # Review A2/B1: the engine sets `observed` before it decides `passed`, so `where` alone is not a pass.
        for alias in ("r1-battleship-sonnet", "r3-checkers-sonnet", "r2-battleship-grok-none"):
            with self.subTest(run=alias):
                self.assertEqual(replay(alias)["block"]["validation"]["release_verify"],
                                 {"where": "returned-result", "kind": "fast-forward-merge", "passed": True})
        self.assertIsNone(replay("v1230-battleship-sonnet")["block"]["validation"]["release_verify"])

    def test_a_failed_or_unknown_release_verify_record_is_shown_with_passed_false_or_null(self):
        for passed in (False, None):
            with self.subTest(passed=passed), tempfile.TemporaryDirectory() as tmp:
                run_dir = Path(tmp) / "run"
                self.release_record(run_dir, 1, "2026-10-09T10:00:00Z", passed, where="work-area")
                found = self.fidelity.validation(run_dir)["release_verify"]
                self.assertEqual(found, {"where": "work-area", "kind": "fast-forward-merge", "passed": passed})

    def test_the_release_verify_record_is_the_latest_by_created_at_then_by_number_never_by_file_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            self.release_record(run_dir, 10, "2026-10-09T10:00:00Z", True, where="old")     # verify10 sorts before verify2
            self.release_record(run_dir, 2, "2026-10-09T11:00:00Z", False, where="newest")
            self.assertEqual(self.fidelity.validation(run_dir)["release_verify"]["where"], "newest")
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            self.release_record(run_dir, 10, None, True, where="ten")
            self.release_record(run_dir, 2, None, False, where="two")
            self.assertEqual(self.fidelity.validation(run_dir)["release_verify"]["where"], "ten")

    def test_an_observed_block_with_no_where_is_no_release_verify_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            self.release_record(run_dir, 1, "2026-10-09T10:00:00Z", True, where=None)
            self.assertIsNone(self.fidelity.validation(run_dir)["release_verify"])

    def test_accepted_ran_is_null_with_a_reason_when_no_row_carries_the_key(self):
        # 8 of the 11 saved runs and both v1220 runs come from engines that do not write accepted_ran: not "0 stages".
        for alias in ("r1-battleship-sonnet", "v1230-battleship-grok-none", "r2-checkers-sonnet"):
            with self.subTest(run=alias):
                block = replay(alias)["block"]
                self.assertIsNone(block["validation"]["accepted_ran"])
                self.assertIn("accepted_ran", block["unmeasured"]["validation.accepted_ran"])
        block = replay("r3-battleship-sonnet")["block"]
        self.assertEqual(len(block["validation"]["accepted_ran"]["stages"]), 6)
        self.assertNotIn("validation.accepted_ran", block["unmeasured"])
        grok = self.fidelity.build(FIXTURES / "v1220-battleship-grok-medium-none", run_dir_of("v1220-battleship-grok-medium-none"), None)
        self.assertIsNone(grok["validation"]["accepted_ran"])

    def test_zero_ran_is_null_for_a_suite_with_no_counted_row_and_a_count_otherwise(self):
        # v1220 Sonnet counts 0 of 42 rows and v1220 Grok 0 of 41: "zero-ran 0" would read as a measurement.
        for alias in V1220:
            with self.subTest(run=alias):
                suites = self.fidelity.validation(run_dir_of(alias))["by_suite"]
                self.assertEqual({name: s["zero_ran"] for name, s in suites.items()}, {"check": None, "focused": None, "regression": None})
        suites = replay("r3-battleship-sonnet")["block"]["validation"]["by_suite"]
        self.assertEqual(suites["focused"]["zero_ran"], 0)
        self.assertEqual((suites["check"]["counted"], suites["check"]["zero_ran"]), (1, 0))

    def test_the_validation_line_says_what_was_counted_and_what_was_not(self):
        lines = self.fidelity.lines(replay("r1-battleship-sonnet")["block"])
        self.assertEqual(lines[1], "validation 10 records / 29 runs / 6 commands: test counts unmeasured 0, zero-ran 0 of 23 counted, "
                                   "red 2; release-verify record: returned-result, passed true")
        heads = self.fidelity.build(FIXTURES / "v1220-battleship-sonnet", run_dir_of("v1220-battleship-sonnet"), None)
        self.assertEqual(self.fidelity.lines(heads)[1], "validation 15 records / 42 runs / 6 commands: test counts unmeasured 34, "
                                                         "zero-ran unmeasured (no row counted), red 2")
        r3 = self.fidelity.lines(replay("r3-battleship-sonnet")["block"])[1]
        self.assertIn(", accepted_ran at 6 stages", r3)
        self.assertIn("zero-ran 0 of 26 counted", r3)
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            self.release_record(run_dir, 1, "2026-10-09T10:00:00Z", False, where="work-area")
            block = self.fidelity.build(Path(tmp), run_dir, None)
            self.assertIn("; release-verify record: work-area, passed false", self.fidelity.lines(block)[1])
            self.assertNotIn("release verified", self.fidelity.lines(block)[1])

    def test_a_block_built_where_the_two_readers_disagree_names_both_values(self):
        run = replay("r1-battleship-sonnet")
        self.assertNotIn("validation.readers", run["block"]["unmeasured"])
        real = metrics.verifications(run["run_dir"])
        with mock.patch.object(metrics, "verifications", return_value={**real, "records": real["records"] + 1, "passed": real["passed"] - 1}):
            block = self.fidelity.build(run["out"], run["run_dir"], run["tools"], engine_scripts=CURRENT_TABLE, exporter=EXPORTER)
        note = block["unmeasured"]["validation.readers"]
        self.assertIn(f"records {real['records'] + 1} (metrics.verifications) vs {real['records']} (JSON)", note)
        self.assertIn(f"passed {real['passed'] - 1} (metrics.verifications) vs {real['passed']} (JSON)", note)
        self.assertNotIn("red", note, "only the figures that differ are named")

    def test_the_two_readers_agree_on_every_replay_so_no_run_carries_the_note(self):
        for alias in ELEVEN:
            with self.subTest(run=alias):
                self.assertNotIn("validation.readers", replay(alias)["block"]["unmeasured"])

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

    def test_product_files_named_like_engine_files_are_not_script_owned_and_the_engines_own_directories_are(self):
        # Review A8: the frozen SHIPLOOP_OWNED matches start.json, packet.json, -terminal.json and until-loop anywhere.
        product = "/runs/x/.shiploop-runs/work-1/worktree"
        for path in (f"{product}/test/fixtures/start.json", f"{product}/src/packet.json", f"{product}/logs/run-terminal.json",
                     f"{product}/docs/until-loop.md", f"{product}/docs/shiploop/spec.md"):
            with self.subTest(path=path):
                self.assertEqual(self.fidelity.shell_edits(f"echo x > {path}"), [])
                log = metrics.ToolLog()
                log.call(1.0, "c", "Write", {"file_path": path}, event=1)
                self.assertEqual(self.fidelity.edits(log)["script_owned"], [])
        run = "/runs/x/.shiploop-runs/work-1/run"
        for path in (f"{run}/state.md", f"{run}/quality/nav-1-terminal.json", f"{run}/until-loop/innerloop-a.json",
                     f"{product}/.shiploop-improve/nav-1/nav-2/packet.json", f"{product}/.shiploop-improve/nav-1/nav-2/start.json",
                     "/w/repo/.shiploop/state.md"):
            with self.subTest(path=path):
                self.assertEqual([e["form"] for e in self.fidelity.shell_edits(f"echo x > {path}")], [">"])

    def test_every_path_the_frozen_set_flags_inside_a_run_or_improve_directory_is_flagged_here_too(self):
        run = "/runs/x/.shiploop-runs/work-1/run"
        for path in (f"{run}/state.md", f"{run}/results/nav-1.md", f"{run}/packets/nav-1.md", f"{run}/tests/nav-1-verify1.md",
                     f"{run}/quality/nav-1-terminal.json", f"{run}/until-loop/a.json", f"{run}/backchain/nav-1/until-loop-start-contract.json",
                     "/runs/x/.shiploop-runs/work-1/worktree/.shiploop-improve/nav-1/nav-2/packet.json",
                     "/runs/x/.shiploop-runs/work-1/worktree/.shiploop-improve/nav-1/nav-2/parent-return.md"):
            with self.subTest(path=path):
                self.assertTrue(metrics.SHIPLOOP_OWNED.search(path) and not metrics.MODEL_INPUT.search(path))
                self.assertTrue(self.fidelity.owned_path(path))

    def test_a_heredoc_marker_line_keeps_its_redirect_or_pipe_and_loses_only_the_body(self):
        run = "/runs/x/.shiploop-runs/work-1/run"
        cases = [(f"cat <<'EOF' > {run}/state.md\nbody > {run}/results/x.md\nEOF", [">"]),
                 (f"cat <<EOF | tee {run}/state.md\nbody\nEOF\nls", ["tee"]),
                 (f"cat > {run}/state.md <<'EOF'\nbody\nEOF", [">"]),
                 (f"cat <<'EOF' > {run}/notes/a.md\nsed -i x {run}/state.md\nEOF", [])]
        for command, forms in cases:
            with self.subTest(command=command):
                self.assertEqual([e["form"] for e in self.fidelity.shell_edits(command)], forms)

    def test_a_command_in_parentheses_names_its_target_without_the_parenthesis(self):
        run = "/runs/x/.shiploop-runs/work-1/run"
        found = self.fidelity.shell_edits(f"(echo x > {run}/state.md)")
        self.assertEqual([(e["form"], e["target"]) for e in found], [(">", f"{run}/state.md")])

    def test_perl_in_place_is_found_with_a_digit_flag_and_a_separator_inside_quotes_does_not_split_a_command(self):
        run = "/runs/x/.shiploop-runs/work-1/run"
        self.assertEqual([e["form"] for e in self.fidelity.shell_edits(f"perl -0pi -e 's/a/b/' {run}/state.md")], ["perl -i"])
        self.assertEqual([e["form"] for e in self.fidelity.shell_edits(f"sed -i 's/a;b|c&&d/e/' {run}/state.md")], ["sed -i"])
        self.assertEqual(self.fidelity.shell_edits(f'echo "x; sed -i s/a/b/ {run}/state.md"'), [])

    def test_the_known_misses_are_pinned_so_they_are_not_forgotten(self):
        run = "/runs/x/.shiploop-runs/work-1/run"
        # an edit by interpreter code (the round-1 heredoc), a shell apply_patch or git apply, a relative path after cd:
        self.assertEqual(self.fidelity.shell_edits(f'python3 - <<EOF\nopen("{run}/state.md", "w").write("x")\nEOF'), [])
        self.assertEqual(self.fidelity.shell_edits("git apply x.patch"), [])
        self.assertEqual(self.fidelity.shell_edits(f"apply_patch <<'PATCH'\n*** Update File: {run}/state.md\nPATCH"), [])
        self.assertEqual(self.fidelity.shell_edits(f"cd {run} && sed -i '' s/a/b/ state.md"), [])
        self.assertEqual(self.fidelity.shell_edits(f"cd {run} && echo x > state.md"), [])
        # a kill by numeric pid or by port is not a kill by name:
        for command in ("kill 67975 67993", "lsof -nP -iTCP:65440 -sTCP:LISTEN -t | xargs -r kill", "kill -9 $(lsof -ti :3000)"):
            self.assertEqual(self.fidelity.name_kills(command), [])
        # a ShipLoop verb a wrapper script hides: the refusal is counted from the result text, with the verb `unknown`.
        log = metrics.ToolLog()
        log.call(1.0, "w", "Bash", {"command": "cat > /r/run/scratch/sub.sh <<'EOF'\npython3 /x/shiploop complete \"$@\"\nEOF"}, event=1)
        log.call(2.0, "r", "Bash", {"command": "bash /r/run/scratch/sub.sh nav-1 result.json"}, event=3)
        log.result("r", "ShipLoop navigator: result requires outcome and summary\n", 0, event=4)
        self.assertEqual([(f["verb"], f["exit"]) for f in log.failures], [("unknown", 0)])
        self.assertEqual(self.fidelity.refusals(log, Path("."), None, {})["count"], 1)

    def test_every_glue_write_hit_but_mkdir_and_a_copy_out_of_an_owned_path_is_also_a_script_owned_edit(self):
        # Review B4: model_glue's write reason is frozen and narrower than the edit list; where it fires on a real write it is listed here.
        run = "/runs/x/.shiploop-runs/work-1/run"
        corpus = [f"echo x > {run}/state.md", f"echo x >> {run}/packets/nav-1.md", f"cp /tmp/a {run}/packets/nav-1.md",
                  f"mv {run}/lint/a.md /tmp/b", f"rm {run}/until-loop/x.json", f"printf x | tee {run}/tests/nav-1-verify1.md",
                  f"cat <<'EOF' > {run}/results/nav-1.md\nbody\nEOF", f"cd /w && echo x > {run}/state.md"]
        corpus += [c["command"] for alias in ELEVEN for c in replay(alias)["tools"].sequence if c["command"]]
        checked = 0
        for command in corpus:
            if "shell write into a ShipLoop-owned path" not in metrics.glue_reasons(command):
                continue
            verbs = {m.group(0).split()[0] for m in metrics.GLUE_WRITE.finditer(metrics.shell_text(command))
                     if metrics.SHIPLOOP_OWNED.search(m.group(0)) and not metrics.MODEL_INPUT.search(m.group(0))}
            if verbs <= {"mkdir"}:
                continue
            checked += 1
            self.assertTrue(self.fidelity.shell_edits(command), command[:120])
        # 7 of the 8 constructed commands fire the glue reason (the heredoc-marker redirect is one the frozen reader cannot see, because
        # it drops the rest of the marker line); the saved runs add none, since model_glue is 0 on all of them for this reason.
        self.assertEqual(checked, 7)

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
                        "man pkill", "ls | grep killall",
                        # quoted text is not a command (review A6's false positives)
                        "echo 'a; pkill -f node'", 'echo "x | pkill -f server"', 'git commit -m "fix: stop; pkill -f node no longer used"',
                        "ps aux | grep node | while read p; do echo $p; done", "lsof -ti :3000 | xargs kill"):
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
            "timeout 5 pkill -f server.js": ["pkill -f server.js"],
            "{ pkill -f server.js; }": ["pkill -f server.js"],
            "! pkill -f server.js": ["pkill -f server.js"],
            "echo node | xargs pkill -f": ["pkill -f"],
            "ps aux | grep node | awk '{print $2}' | xargs kill": ["ps aux | grep node | awk '{print $2}' | xargs kill"],
            # Review A6: the form of the saved run v1220-battleship-grok-medium-none, event 8493, verbatim.
            "ps aux | rg 'battleship-chrome' | rg -v rg | awk '{print $2}' | while read p; do kill \"$p\"":
                ["ps aux | rg 'battleship-chrome' | rg -v rg | awk '{print $2}' | while read p; do kill \"$p\""],
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

    def test_a_partly_staged_run_keeps_the_count_it_can_flag_and_says_what_it_cannot(self):
        same = "ShipLoop navigator: " + "evidence " * 30
        found = self._items([same, same, same], ["plan", "plan", None])
        self.assertEqual(found["repeated"], 1)
        self.assertEqual([i["repeat_of"] for i in found["items"]], [None, 0, None])
        log = metrics.ToolLog()
        log.call(1.0, "c", "Bash", {"command": "ls"}, event=1)
        none = self.fidelity.refusals(log, Path("."), None, {})
        self.assertEqual((none["count"], none["repeated"]), (0, 0), "a stream with calls and no refusal is a measured none")

    def test_the_block_notes_a_partly_staged_refusal_list_and_stays_quiet_when_every_refusal_has_a_stage(self):
        run = replay("r2-checkers-sonnet")
        canned = {"count": 3, "repeated": 1, "unstaged": 1, "limits": "", "items": []}
        for unstaged, noted in ((1, True), (0, False)):
            with self.subTest(unstaged=unstaged), mock.patch.object(self.fidelity, "refusals", return_value={**canned, "unstaged": unstaged}):
                block = self.fidelity.build(run["out"], run["run_dir"], run["tools"], engine_scripts=CURRENT_TABLE, exporter=EXPORTER)
                self.assertEqual("refusals.stage" in block["unmeasured"], noted)
        self.assertNotIn("refusals.stage", run["block"]["unmeasured"])
        self.assertNotIn("refusals.repeated", run["block"]["unmeasured"])

    def test_the_refusals_part_says_what_it_cannot_see(self):
        found = self._items(["ShipLoop navigator: a"], ["plan"])
        self.assertIn("a repeat needs", found["limits"])
        self.assertIn("pointer", found["limits"])

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
        self.assertIsNone(refusals["repeated"], "no refusal could be given a stage, so a repeat cannot be told: not 0")
        block = self.fidelity.build(out, run_dir, tools, engine_scripts=CURRENT_TABLE, exporter=EXPORTER)
        self.assertIn("no refusal could be given a stage", block["unmeasured"]["refusals.repeated"])
        self.assertIn("repeated unmeasured", self.fidelity.lines(block)[3])

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

    def end_state_of(self, entries, status="done"):
        """end_state on a state with one accepted result per (outcome, extra keys)."""
        history = [{"action": f"a{i}", "stage": "s", "outcome": o} for i, (o, _) in enumerate(entries)]
        accepted = {f"a{i}": {"outcome": o, "summary": "x", **extra} for i, (o, extra) in enumerate(entries)}
        return self.fidelity.end_state({"status": status, "history": history, "accepted": accepted})

    def test_the_last_unverified_list_wins_over_an_earlier_one(self):
        two = [{"outcome": "a", "owner": "user"}, {"outcome": "b", "owner": "ops"}]
        state = self.end_state_of([("done", {"unverified": two}), ("done", {"unverified": [two[0]]}), ("done", {})])
        self.assertEqual(state["unverified"], {"entries": 1, "owners": ["user"]})
        state = self.end_state_of([("done", {"unverified": [two[0]]}), ("done", {"unverified": two})])
        self.assertEqual(state["unverified"], {"entries": 2, "owners": ["ops", "user"]})

    def test_no_default_is_true_only_when_the_result_states_why_no_default_would_do(self):
        for awaiting, expected in (({"kind": "answer", "no_default": "No default would do: a person must grant it"}, True),
                                   ({"kind": "answer", "no_default": ""}, False), ({"kind": "answer", "no_default": "   "}, False),
                                   ({"kind": "answer"}, False), ({"kind": "present", "no_default": None}, False)):
            with self.subTest(awaiting=awaiting):
                state = self.end_state_of([("blocked", {"blocked_by": "access", "awaiting": awaiting})], status="blocked")
                self.assertEqual(state["awaiting"], {"kind": awaiting["kind"], "no_default": expected})
        self.assertIsNone(self.end_state_of([("blocked", {"blocked_by": "access"})], status="blocked")["awaiting"])

    def test_blocked_by_and_awaiting_are_read_from_the_last_accepted_result(self):
        state = self.end_state_of([("blocked", {"blocked_by": "first", "awaiting": {"kind": "a", "no_default": "x"}}), ("done", {})])
        self.assertEqual((state["blocked_by"], state["awaiting"]), (None, None))

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
        self.assertEqual(per_run["r3-battleship-grok-none"], 0, "no Improve child ran in that run: a measured none")
        self.assertEqual(per_run["r2-battleship-grok-none"], 3)

    def test_a_missing_entry_names_the_action_and_its_stage(self):
        missing = replay("r1-battleship-sonnet")["block"]["improve_packets"]["missing"]
        self.assertEqual(len(missing), 8)
        self.assertTrue(all(re.fullmatch(r"nav-[0-9a-f]+", m["action"]) for m in missing))
        self.assertIn("carry-forward", {m["stage"] for m in missing})

    def test_a_run_of_the_old_layout_with_improve_children_but_no_improve_files_is_unmeasured_not_missing(self):
        block = replay(CODEX, engine_scripts=OLD_TABLE)["block"]
        self.assertIsNone(block["improve_packets"])
        self.assertIn("1.22.0 or earlier", block["unmeasured"]["improve_packets"])

    def test_a_run_with_no_improve_child_has_read_zero_not_unmeasured(self):
        # r3-battleship-grok-none ran planning_review none and stopped before any carry-forward: a measured none (review B16).
        block = replay("r3-battleship-grok-none")["block"]
        self.assertEqual(block["improve_packets"], {"read": 0, "carried": dict.fromkeys(self.QUESTIONS, 0), "missing": []})
        self.assertNotIn("improve_packets", block["unmeasured"])

    def test_improve_children_that_left_no_packet_file_in_a_current_layout_run_are_unmeasured(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            (run_dir / "packets").mkdir(parents=True)
            (run_dir / "packets" / "nav-1.md").write_text("ShipLoop navigator | spec | revision 1\nGoal: x\n")
            state = {"history": [], "improve_results": {"nav-1": {}}}
            with self.assertRaises(self.fidelity.Unmeasured) as raised:
                self.fidelity.improve_packets(run_dir, state)
            self.assertIn("left no packets/<action>-improve.md", str(raised.exception))
            self.assertNotIn("1.22.0", str(raised.exception))
            self.assertEqual(self.fidelity.improve_packets(run_dir, {"history": []})["read"], 0)

    def test_the_old_layout_marker_is_the_exporters_own(self):
        namespace: dict = {}
        source = EXPORTER.read_text()
        found = re.search(r'(?m)^IMPROVE_PACKET = re\.compile\((r"[^"]+"), re\.M\)', source)
        self.assertIsNotNone(found, "the exporter's old-layout marker moved")
        self.assertEqual(self.fidelity.OLD_LAYOUT_MARKER.pattern, eval(found.group(1), namespace))

    def packet_without(self, label: str, how: str) -> tuple[dict, str]:
        """improve_packets of a copy of a real Improve packet (r3-battleship-sonnet) from which `label`'s line was dropped (how "drop") or
        turned into a mid-line mention (how "mention")."""
        source = next((run_dir_of("r3-battleship-sonnet") / "packets").glob("*-improve.md")).read_text()
        pattern = dict(self.fidelity.IMPROVE_QUESTIONS)[label]
        lines = []
        for line in source.splitlines():
            if pattern.search(line):
                if how == "mention":
                    lines.append("The packet text also says " + line)
                continue
            lines.append(line)
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            (run_dir / "packets").mkdir(parents=True)
            (run_dir / "packets" / "nav-1-improve.md").write_text("Some other rule of the packet.\n" + "\n".join(lines) + "\nAnd a closing line.\n")
            return self.fidelity.improve_packets(run_dir, {"history": [{"action": "nav-1", "stage": "spec"}]}), source

    def test_a_packet_missing_one_question_names_exactly_that_one(self):
        # Review A5: the extract keeps only the lines the patterns are built to match, so the replay alone cannot show a pattern
        # that matches everything; a real packet with one label's line dropped, or only mentioned mid-line, can.
        for label in self.QUESTIONS:
            for how in ("drop", "mention"):
                with self.subTest(label=label, how=how):
                    found, _ = self.packet_without(label, how)
                    self.assertEqual(found["missing"], [{"action": "nav-1", "stage": "spec", "labels": [label]}])
                    self.assertEqual({k: v for k, v in found["carried"].items() if v == 0}, {label: 0})

    def test_the_intact_packet_the_negative_cases_start_from_carries_all_five(self):
        source = next((run_dir_of("r3-battleship-sonnet") / "packets").glob("*-improve.md")).read_text()
        for label, pattern in self.fidelity.IMPROVE_QUESTIONS:
            self.assertTrue(pattern.search(source), label)

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

    def test_the_block_names_its_schema_and_every_part_and_not_the_host(self):
        block = replay("r2-battleship-grok-none")["block"]
        self.assertEqual(block["schema"], "shiploop-e2e-fidelity/v1")
        # runrecord.hosts_used is the one reader of which hosts worked on a run (group G4's environment block records it).
        self.assertNotIn("hosts", block)
        self.assertNotIn("mixed_host", block)
        for part in ("evidence", "validation", "edits", "refusals", "end_state", "improve_packets"):
            self.assertIn(part, block)
        self.assertGreater(block["tool_calls_seen"], 0)

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
        reasons = {"evidence": "no history", "validation": "run directory", "end_state": "no status", "improve_packets": "run directory",
                   "edits": "no tool call", "refusals": "no tool call"}
        for part, word in reasons.items():
            self.assertIsNone(block[part], part)
            self.assertIn(word, block["unmeasured"][part], part)

    def test_the_block_is_json_and_a_regression_tripwire_on_its_size(self):
        # 60,000 characters is a tripwire at about 4 times the largest block of the saved runs (15 KB), not a budget: a block
        # that grows past it holds something it should not (packet text, a command).
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
        self.assertIn("script 15, loop 7, file 1, note 12, sentence 0, skipped 2, unclassified 0 (records:", lines[0])
        self.assertTrue(lines[3].startswith("refusals (heuristic, no repeat flagged is not proof) 5, repeated 1: "), lines[3])
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

    def give_the_plugin_a_stage_table(self):
        """The fake plugin build holds a ShipLoop CLI file but no stage table; write the frozen one beside it, as an installed plugin has."""
        import shutil
        shutil.copy(CURRENT_TABLE / "shiploop_stage_spec.py", self.cli.parent / "shiploop_stage_spec.py")

    def test_the_wiring_hands_the_builder_the_tool_log_and_the_stage_table_of_the_run(self):
        # Review A4: a run_main that passed no ToolLog, or no scripts directory, still passed every test.
        self.give_the_plugin_a_stage_table()
        for host in ("claude", "grok", "codex"):
            # Grok and Codex install the plugin into the run's own profile, which the fake host never does: the CLI is the build's.
            with self.subTest(host=host), mock.patch.object(HARNESS.run, "run_cli", return_value=self.cli):
                code, result, printed, written, out = self.written(host)
                block = written["fidelity"]
                self.assertGreater(block["tool_calls_seen"], 0)
                self.assertIsNotNone(block["edits"], block["unmeasured"])
                self.assertIsNotNone(block["refusals"], block["unmeasured"])
                self.assertNotIn("declared", block["unmeasured"], "the stage table beside the CLI was read")

    def test_without_a_stage_table_beside_the_cli_declared_is_unmeasured_and_the_rest_still_runs(self):
        code, result, printed, written, out = self.written("grok")
        self.assertIn("declared", written["fidelity"]["unmeasured"])
        self.assertIsNotNone(written["fidelity"]["edits"])

    def test_the_exporter_the_builder_and_the_run_report_load_come_from_one_helper(self):
        calls = []
        real = self.fidelity.load_exporter
        with mock.patch.object(self.fidelity, "load_exporter", side_effect=lambda path: calls.append(Path(path).name) or real(path)):
            self.give_the_plugin_a_stage_table()
            self.written("grok")
        self.assertIn("export.py", calls)
        self.assertGreaterEqual(calls.count("export.py"), 2, "fidelity.declared_checks and run.review_export both call it")

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
