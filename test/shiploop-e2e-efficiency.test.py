#!/usr/bin/env python3
"""No-model checks for the efficiency plan's measurement (unit U5): the reading path, the clear's orientation, arms.py, the
seeded-defect cases, the generated homes, the audit probes and the plan-stage share.

What the harness measures and nothing it decides, except arms.py, which decides from those numbers by a stated rule:

* ``metrics.reading_path``: where the characters a model took in came from (buckets, files by class, cold and warm), how it ran
  each ShipLoop command (piped, built through a variable, seen by the status display, cut by a pipe), which packet files it
  opened, which gates the run skipped, whether the Improve stages invoked the skill, the quoted knowledge that reached it;
* ``clear.orientation``: what a fresh session read before it changed anything, and how long it took;
* ``arms.py``: hard gates, then bytes, then time, against the control's own A/A spread;
* ``seeded_defects``: the planted-defect cases, each proven to survive a run with no review and to be scored on the final tree;
* ``home_fixtures`` and ``audit_probes``: the long and small knowledge homes, and the audit's size probes on any checkout.

The fixtures under test/fixtures/efficiency/ are compact extracts of two saved runs (see extract.py there): a Claude step slice
on ShipLoop 1.3.0 and a Grok run of 33,833 events. The counts pinned here were taken from the saved runs; the extracts reproduce
them. No test starts a host, reads /Users/dadleet/e2e-runs or a scratchpad, or runs `sf`.
"""

from __future__ import annotations

import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
import arms  # noqa: E402
import audit_probes  # noqa: E402
import clear  # noqa: E402
import home_fixtures  # noqa: E402
import metrics  # noqa: E402
import seeded_defects  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402

FIXTURES = ROOT / "test" / "fixtures" / "efficiency"
NODE = shutil.which("node")


def materialise(name: str, into: Path) -> Path:
    """The saved-run extract ``name`` unpacked under ``into``: its .gz files expanded and the file times it recorded restored."""
    target = into / name
    shutil.copytree(FIXTURES / name, target)
    for packed in list(target.rglob("*.gz")):
        with gzip.open(packed, "rb") as handle:
            packed.with_suffix("").write_bytes(handle.read())
        packed.unlink()
    if (target / "mtimes.json").is_file():
        for relative, when in json.loads((target / "mtimes.json").read_text()).items():
            os.utime(target / relative, (when, when))
    return target


class SavedRuns(unittest.TestCase):
    """The two extracts, unpacked once per class."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="shiploop-efficiency-")
        cls.claude = materialise("claude-step-slice", Path(cls.temp.name))
        cls.grok = materialise("grok-long-run", Path(cls.temp.name))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()


class ClaudeReadingPathTests(SavedRuns):
    """The recorded Claude step slice (node-fix-bug, ShipLoop 1.3.0, 41 tool calls): the reviews' counts, reproduced."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.path = metrics.reading_path(cls.claude)

    def test_every_complete_was_piped_and_all_but_one_named_the_run_directory_through_a_variable(self) -> None:
        complete = self.path["shiploop_commands"]["by_verb"]["complete"]
        self.assertEqual((complete["invocations"], complete["piped"], complete["variable_built"]), (20, 20, 19))
        self.assertEqual(self.path["piped_shiploop_calls"], {"count": 20, "of": 21})
        self.assertEqual(self.path["variable_built_shiploop_calls"]["count"], 19)
        self.assertEqual(self.path["variable_built_shiploop_calls"]["any_variable"], 20)
        self.assertEqual(complete["check_only"], 9)

    def test_the_status_display_could_read_one_command_of_twenty_one(self) -> None:
        self.assertEqual(self.path["shiploop_commands"]["invocations"], 21)
        self.assertEqual(self.path["shiploop_commands"]["hook_visible"], 1)
        self.assertEqual(self.path["shiploop_commands"]["by_verb"]["next"]["hook_visible"], 1)

    def test_a_cut_print_records_how_many_lines_the_model_asked_for(self) -> None:
        prints = self.path["shiploop_print_cut"]["prints"]
        producers = [p for p in prints if p["stage"] != "improve" and p["n"]]
        self.assertEqual([p["n"] for p in producers], [50, 30, 30, 40, 14, 30, 25])
        self.assertEqual(self.path["shiploop_print_cut"]["count"], 11)
        self.assertEqual(self.path["shiploop_print_cut"]["of"], 12)
        self.assertEqual(self.path["shiploop_print_cut"]["median_lines_seen"], 30.0)
        self.assertFalse(self.path["shiploop_print_cut"]["marker_seen"], "the 1.3.0 build prints no closing line")

    def test_the_packet_file_was_opened_in_three_of_eight_producer_stages(self) -> None:
        opens = self.path["packet_file_opens"]
        self.assertEqual((opens["count"], opens["of"]), (3, 8))
        self.assertEqual({r["stage"]: r["mode"] for r in opens["stages"] if r["mode"] != "none"},
                         {"step-plan": "whole", "test-spec": "slice", "carry-forward": "slice"})

    def test_four_gates_did_not_run_and_each_is_named(self) -> None:
        gates = self.path["skipped_gates"]
        self.assertEqual(gates["count"], 4)
        self.assertEqual([g["gate"] for g in gates["gates"] if g["skipped"]], ["base", "mutation", "inventory", "item_commit"])

    def test_the_improve_skill_was_invoked_in_one_of_four_improve_stages(self) -> None:
        improve = self.path["improve_skill_invoked"]
        self.assertEqual((improve["count"], improve["of"]), (1, 4))
        self.assertEqual([s["invoked"] for s in improve["stages"]], [True, False, False, False])

    def test_no_listed_pointer_was_followed(self) -> None:
        pointers = self.path["listed_pointers_followed"]
        self.assertEqual(pointers["count"], 0)
        self.assertGreater(pointers["of"], 10)

    def test_no_next_call_was_warm(self) -> None:
        self.assertEqual(self.path["warm_next_calls"], {"count": 0, "of": 1})

    def test_the_buckets_partition_the_result_characters_and_name_the_files(self) -> None:
        buckets = self.path["buckets"]
        self.assertEqual(sum(b["chars"] for b in buckets.values()), self.path["result_chars"])
        self.assertEqual(sum(b["calls"] for b in buckets.values()), self.path["calls"])
        self.assertEqual((buckets["packet_output"]["calls"], buckets["child_handoffs"]["calls"]), (12, 2))
        classes = self.path["files_by_class"]
        self.assertEqual(set(classes), {"adapter", "child_record", "handoff", "improve_card", "packet_file"})
        self.assertEqual(classes["packet_file"]["calls"], 3)
        self.assertEqual((classes["packet_file"]["whole"], classes["packet_file"]["slice"]), (1, 2))
        self.assertGreater(classes["improve_card"]["chars"], 20_000, "the skill's text arrives as a user message after the call")
        for scope in ("cold", "warm"):
            self.assertEqual(sum(self.path[scope][b]["chars"] for b in buckets) + sum(
                self.path["warm" if scope == "cold" else "cold"][b]["chars"] for b in buckets), self.path["result_chars"])

    def test_the_run_start_is_a_break_and_its_first_call_is_next(self) -> None:
        (start,) = self.path["breaks"]
        self.assertEqual((start["kind"], start["first_call_kind"], start["next_within_12"]), ("start", "next", True))
        self.assertIsNone(self.path["compactions"], "Claude's compactions are not detected")


class GrokReadingPathTests(SavedRuns):
    """The recorded Grok run: the S5 snapshot (the first 29,668 events) and the whole file (S6), reproduced."""

    def test_the_first_29668_events_reproduce_the_snapshot_read_counts(self) -> None:
        reads = metrics.reading_path(self.grok, limit_events=29_668)["reads_by_class"]
        self.assertEqual({k: reads[k] for k in ("packet_file", "handoff", "improve_card", "adapter", "entry_card")},
                         {"packet_file": 40, "handoff": 19, "improve_card": 14, "adapter": 12, "entry_card": 8})

    def test_the_whole_run_has_46_packet_file_reads_and_14_compactions(self) -> None:
        path = metrics.reading_path(self.grok)
        reads = path["reads_by_class"]
        self.assertEqual((reads["packet_file"], reads["handoff"], reads["improve_card"], reads["adapter"], reads["entry_card"]),
                         (46, 21, 16, 14, 10))
        self.assertEqual((path["events"], path["calls"], path["compactions"]), (33_833, 1_503, 14))
        self.assertEqual(path["host"], "grok")

    def test_after_the_last_nine_compactions_the_first_call_was_the_entry_card_and_next_followed_after_nine(self) -> None:
        compactions = [b for b in metrics.reading_path(self.grok)["breaks"] if b["kind"] == "compaction"]
        self.assertEqual(len(compactions), 14)
        self.assertEqual([b["first_call_class"] for b in compactions[:5]].count("entry_card"), 0)
        self.assertEqual([b["first_call_class"] for b in compactions[5:]], ["entry_card"] * 9)
        self.assertEqual(sum(b["next_within_12"] for b in compactions), 9)

    def test_the_run_has_four_warm_next_calls_and_one_pipe(self) -> None:
        path = metrics.reading_path(self.grok)
        self.assertEqual(path["warm_next_calls"]["count"], 4)
        self.assertEqual(path["piped_shiploop_calls"]["count"], 1)
        self.assertEqual(path["shiploop_print_cut"]["count"], 0)

    def test_compactions_are_counted_per_100_minutes_of_the_run(self) -> None:
        path = metrics.reading_path(self.grok)
        self.assertAlmostEqual(path["compactions_per_100_min"], 14 * 100.0 / path["run_minutes"], places=1)
        self.assertGreater(path["run_minutes"], 200)

    def test_the_improve_skill_count_is_unknown_without_a_skill_tool_and_the_card_reads_are_counted(self) -> None:
        improve = metrics.reading_path(self.grok)["improve_skill_invoked"]
        self.assertIsNone(improve["count"])
        self.assertIn("Claude only", improve["reason"])
        self.assertGreater(improve["card_reads"], 0)

    def test_a_prefix_reads_only_its_lines(self) -> None:
        path = metrics.reading_path(self.grok, limit_events=1_000)
        self.assertEqual(path["events"], 1_000)
        self.assertLess(path["calls"], 100)

    def test_the_stage_share_of_the_planning_window_is_measured_offline(self) -> None:
        share = metrics.stage_share(self.grok)
        self.assertTrue(share["measured"])
        self.assertEqual((share["window_seconds"], share["through"], share["stage_seconds"]), (4661.0, "test-spec", 612.0))
        self.assertEqual((share["improve_seconds"], share["authoring_seconds"]), (410.6, 201.4))
        self.assertAlmostEqual(share["authoring_share"], 0.0432, places=4)
        self.assertGreater(share["named"]["calls"], 0)
        self.assertLess(share["named"]["span_share"], share["authoring_share"] + 0.01)

    def test_a_run_with_no_run_directory_is_not_measured_and_says_why(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "events.jsonl").write_text("")
            self.assertFalse(metrics.stage_share(Path(temp))["measured"])


def claude_call(call_id: str, command: str | None = None, tool: str = "Bash", **arg) -> dict:
    block = {"type": "tool_use", "id": call_id, "name": tool, "input": {"command": command, **arg} if command is not None else arg}
    return {"type": "assistant", "message": {"id": "m" + call_id, "content": [block]}}


def claude_result(call_id: str, text: str) -> dict:
    return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": call_id, "content": text}]}}


def write_run(out: Path, events: list, stamps: bool = True, sessions: list | None = None) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    if stamps:
        (out / "timeline.jsonl").write_text("".join(json.dumps({"line": n, "t": 1000.0 + n}) + "\n" for n in range(len(events))))
    if sessions:
        (out / "sessions.jsonl").write_text("".join(json.dumps(s) + "\n" for s in sessions))
    return out


CLI = "/plugin/skills/shiploop/scripts/shiploop"
PACKET = "ShipLoop navigator | implement | revision 7\nCallback for this stage (run once): x\nGoal: g\n"


class CommandShapeTests(unittest.TestCase):
    """How a ShipLoop command was typed: piped, built through a variable, visible to the status display."""

    def invocations(self, command: str) -> list[dict]:
        return metrics.shiploop_invocations(command)

    def test_a_literal_command_is_visible_and_not_piped(self) -> None:
        (found,) = self.invocations(f'python3 "{CLI}" next --run-dir "/runs/a/run"')
        self.assertEqual((found["verb"], found["piped"], found["variable_built"], found["hook_visible"]), ("next", False, False, True))

    def test_a_pipe_into_head_records_the_lines_kept_and_hides_the_command_from_the_display(self) -> None:
        (found,) = self.invocations(f'python3 {CLI} complete --run-dir=/runs/a/run --action=nav-1 2>&1 | head -30')
        self.assertTrue(found["piped"])
        self.assertEqual(found["cut"], {"into": "head", "lines": 30})
        self.assertFalse(found["hook_visible"])

    def test_a_variable_in_the_run_directory_argument_is_variable_built_and_a_variable_elsewhere_is_only_any(self) -> None:
        (built,) = self.invocations(f'R=/runs/a/run\npython3 {CLI} complete --run-dir=$R --action=nav-1')
        (other,) = self.invocations(f'SC={CLI}\npython3 $SC complete --run-dir=/runs/a/run --action=nav-1')
        self.assertEqual((built["variable_built"], built["variable_any"]), (True, True))
        self.assertEqual((other["variable_built"], other["variable_any"]), (False, True))
        self.assertEqual(other["verb"], "complete", "a CLI path held in a variable is still the ShipLoop CLI")

    def test_two_commands_in_one_call_are_two_invocations_and_a_heredoc_body_is_not_a_command(self) -> None:
        command = (f"cat > r.md <<'EOF'\n{CLI} complete is only text here\nEOF\n"
                   f"python3 {CLI} complete --check-only --run-dir=/r --action=a 2>&1 | head -8\n"
                   f"python3 {CLI} complete --run-dir=/r --action=a 2>&1 | tail -20")
        found = self.invocations(command)
        self.assertEqual([(f["check_only"], f["cut"]) for f in found],
                         [(True, {"into": "head", "lines": 8}), (False, {"into": "tail", "lines": 20})])

    def test_a_chain_and_a_quoted_pipe_are_not_pipes_and_a_sed_range_is_a_cut(self) -> None:
        self.assertFalse(self.invocations(f"python3 {CLI} next --run-dir=/r || echo failed")[0]["piped"])
        self.assertFalse(self.invocations(f"python3 {CLI} complete --run-dir=/r --reason='a | b'")[0]["piped"])
        self.assertEqual(metrics.pipe_of("x | sed -n '1,40p'"), {"into": "sed", "lines": 40})
        self.assertEqual(metrics.pipe_of("x | head -n 12"), {"into": "head", "lines": 12})
        self.assertEqual(metrics.pipe_of("x | grep foo"), {"into": "grep", "lines": None})
        self.assertIsNone(metrics.pipe_of("x > out.txt"))

    def test_the_closing_line_constant_is_the_navigators(self) -> None:
        self.assertEqual(metrics.HEAD_END, navigator.HEAD_END)


class ClassifyTests(unittest.TestCase):
    def test_a_read_of_a_packet_file_whole_and_with_a_range(self) -> None:
        path = "/runs/a/run/packets/nav-" + "a" * 32 + ".md"
        whole = metrics.classify_call("Read", {"file_path": path}, "")
        sliced = metrics.classify_call("read_file", {"target_file": path, "offset": 10, "limit": 50}, "")
        self.assertEqual((whole["bucket"], whole["cls"], whole["mode"], whole["read"]), ("files", "packet_file", "whole", True))
        self.assertEqual((sliced["cls"], sliced["mode"]), ("packet_file", "slice"))

    def test_a_shell_command_that_names_a_packet_file_is_a_read_of_it(self) -> None:
        found = metrics.classify_call("Bash", {"command": "grep -n Goal /runs/a/run/packets/nav-" + "b" * 32 + ".md | head"}, "")
        self.assertEqual((found["bucket"], found["cls"], found["mode"]), ("files", "packet_file", "slice"))

    def test_a_shiploop_print_is_packet_output_and_a_refusal_is_a_message(self) -> None:
        printed = metrics.classify_call("Bash", {"command": f"python3 {CLI} complete --run-dir=/r --action=a"}, PACKET)
        refused = metrics.classify_call("Bash", {"command": f"python3 {CLI} complete --run-dir=/r --action=a"}, "ShipLoop navigator: refused")
        self.assertEqual((printed["bucket"], refused["bucket"]), ("packet_output", "shiploop_messages"))

    def test_the_runtime_a_bare_handoff_and_the_skill_tool(self) -> None:
        self.assertEqual(metrics.classify_call("Bash", {"command": "python3 until_loop_ephemeral.py done --state s"}, "")["bucket"],
                         "runtime_output")
        bare = metrics.classify_call("Bash", {"command": "cd /w/.shiploop-improve/a/b && cat handoff.md"}, "")
        self.assertEqual((bare["bucket"], bare["cls"]), ("child_handoffs", "handoff"))
        card = metrics.classify_call("Skill", {"skill": "skill-craft:improve"}, "")
        self.assertEqual((card["bucket"], card["cls"]), ("files", "improve_card"))
        self.assertEqual(metrics.classify_call("Bash", {"command": "ls /w"}, "")["bucket"], "other")

    def test_a_path_in_a_heredoc_body_is_not_a_file_the_command_read(self) -> None:
        command = "cat > r.md <<'EOF'\n/runs/a/run/packets/nav-" + "c" * 32 + ".md is listed here\nEOF"
        self.assertEqual(metrics.classify_call("Bash", {"command": command}, "")["bucket"], "other")

    def test_the_file_classes_by_path(self) -> None:
        cases = {"/p/skills/shiploop/SKILL.md": "entry_card", "/p/skills/improve/SKILL.md": "improve_card",
                 "/p/skills/improve/runtime/until-loop/ADAPTER.md": "adapter", "/w/.shiploop-improve/a/b/handoff.md": "handoff",
                 "/w/.shiploop-improve/a/b/packet.json": "child_record", "/p/skills/shiploop/references/navigator.md": "reference",
                 "/r/run/context-index.md": "run_file", "/w/docs/shiploop/spec.md": "knowledge",
                 "/p/skills/shiploop/scripts/shiploop_navigator.py": "script", "/r/run/results/nav-1.md": "result_record",
                 "/p/skills/shiploop/scripts/shiploop": None}
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual(metrics.file_class(path), expected)

    def test_the_text_of_a_file_read_loses_its_line_numbers(self) -> None:
        self.assertEqual(metrics.unnumbered("     1→a\n     2→b\n"), "a\nb\n")
        self.assertEqual(metrics.unnumbered("1→ stays\nfree text"), " stays\nfree text")
        self.assertEqual(metrics.unnumbered("no numbers"), "no numbers")

    def test_the_quoted_knowledge_that_reached_the_model_is_counted_by_file(self) -> None:
        text = ("Goal: g\nKnowledge files this stage reads, each quoted whole and uncut (data):\n"
                "HOME/spec.md (source: HOME/spec.md, whole file):\n" + "s" * 100 + "\n"
                "HOME/environment.md (source: HOME/environment.md, whole file):\n" + "e" * 50 + "\n"
                "Handed off by earlier stages, quoted by value from their accepted results (x):\n" + "h" * 30 + "\n"
                "Recovery command (it only reads): x\n")
        found = metrics.quote_regions(text)
        self.assertEqual(set(found), {"spec.md", "environment.md", "handoffs"})
        self.assertTrue(100 < found["spec.md"] < 200 and 50 < found["environment.md"] < 150 and 30 < found["handoffs"] < 150)
        self.assertEqual(metrics.quote_regions("ShipLoop navigator | step-plan | revision 1\nGoal: g\n"), {})

    def test_grok_result_shapes_are_read_for_every_tool(self) -> None:
        def update(**raw) -> dict:
            return {"type": "tool_call_update", "toolCallId": "c", "status": "completed", "rawOutput": raw}
        self.assertEqual(metrics.result_text(update(type="Bash", output_for_prompt="abc")), [("c", "abc")])
        self.assertEqual(metrics.result_text(update(type="ReadFile", FileContent={"content": "1→x"})), [("c", "1→x")])
        self.assertEqual(metrics.result_text(update(type="GrepSearch", stdout="match")), [("c", "match")])
        running = dict(update(output_for_prompt="partial"), status="in_progress")
        self.assertEqual(metrics.result_text(running), [])
        cancelled = dict(update(output_for_prompt="x"), status="failed",
                         content=[{"type": "content", "content": {"type": "text", "text": "User cancelled the execution"}}])
        self.assertEqual(metrics.result_text(cancelled), [])


class WarmNextTests(unittest.TestCase):
    """A `next` is warm when it is not within 12 calls of a break (the run's start, a compaction, a fresh session)."""

    def stream(self, calls_before_next: int) -> list:
        events = []
        for number in range(calls_before_next):
            events += [claude_call(f"c{number}", f"ls /w/{number}"), claude_result(f"c{number}", "x")]
        events += [claude_call("n", f'python3 {CLI} next --run-dir "/runs/a/run"'), claude_result("n", PACKET)]
        return events

    def test_a_next_after_a_long_stretch_of_work_counts_one_warm_call(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = write_run(Path(temp) / "warm", self.stream(20))
            self.assertEqual(metrics.reading_path(out)["warm_next_calls"], {"count": 1, "of": 1})

    def test_a_next_within_twelve_calls_of_the_start_is_cold(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = write_run(Path(temp) / "cold", self.stream(5))
            self.assertEqual(metrics.reading_path(out)["warm_next_calls"], {"count": 0, "of": 1})

    def test_a_fresh_session_the_harness_recorded_is_a_break_and_makes_the_next_after_it_cold(self) -> None:
        events = self.stream(20)
        with tempfile.TemporaryDirectory() as temp:
            sessions = [{"row": "start", "n": 1, "kind": "first", "events_line": 0},
                        {"row": "start", "n": 2, "kind": "fresh", "events_line": 36}]
            out = write_run(Path(temp) / "fresh", events, sessions=sessions)
            path = metrics.reading_path(out)
            self.assertEqual(path["warm_next_calls"], {"count": 0, "of": 1})
            self.assertEqual([b["kind"] for b in path["breaks"]], ["start", "fresh"])
            self.assertEqual(path["breaks"][1]["first_call_kind"], "plain")


class SkippedGateTests(unittest.TestCase):
    def run_dir(self, temp: str, *, base: bool, items: bool, mutation: dict | None = None) -> Path:
        run = Path(temp) / "run"
        (run / "tests").mkdir(parents=True)
        (run / "lint").mkdir()
        fence = lambda record: "```shiploop-state\n" + json.dumps(record) + "\n```\n"  # noqa: E731
        (run / "state.md").write_text(fence({"history": [{"stage": "verify", "outcome": "done", "workitem": "W1"}]}))
        (run / "tests" / "nav-a-base1.md").write_text(fence({"schema": "shiploop-test-base/v1", "skipped": None if base else "no base"}))
        (run / "tests" / "nav-a-mutation1.md").write_text(fence(mutation or {"schema": "x", "mutants": [{"id": 1}]}))
        (run / "tests" / "nav-a-mutation-check-only.md").write_text(fence({"schema": "x", "skipped": "check only is never counted"}))
        (run / "lint" / "nav-a-inventory.md").write_text(fence({"status": "ok" if items else "unavailable", "reason": "no base snapshot"}))
        if items:
            (run / "lint" / "items").mkdir()
            (run / "lint" / "items" / "W1.md").write_text(fence({"tree": "t"}))
        return run

    def test_a_run_that_ran_every_gate_has_none_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            found = metrics.skipped_gates(self.run_dir(temp, base=True, items=True))
        self.assertEqual((found["measured"], found["count"]), (True, 0))

    def test_each_skipped_gate_counts_once_and_the_check_only_record_is_not_a_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            found = metrics.skipped_gates(self.run_dir(temp, base=False, items=False))
        self.assertEqual([g["gate"] for g in found["gates"] if g["skipped"]], ["base", "inventory", "item_commit"])
        self.assertEqual(found["count"], 3, "the mutation record has mutants, so that gate ran")

    def test_a_mutation_check_that_found_no_mutants_is_a_skipped_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            found = metrics.skipped_gates(self.run_dir(temp, base=True, items=True, mutation={"schema": "x", "mutants": []}))
        (mutation,) = [g for g in found["gates"] if g["gate"] == "mutation"]
        self.assertEqual((mutation["skipped"], mutation["reason"]), (1, "no mutants"))

    def test_no_run_directory_is_not_measured(self) -> None:
        self.assertEqual(metrics.skipped_gates(None)["count"], None)
        self.assertFalse(metrics.skipped_gates(Path("/nonexistent/run"))["measured"])


class ImproveSkillTests(unittest.TestCase):
    def test_a_skill_call_between_an_improve_print_and_the_next_stage_print_counts_for_that_stage(self) -> None:
        improve = "ShipLoop navigator | improve | revision 3 | the plan result\nNext command: x\n"
        events = [claude_call("a", f"python3 {CLI} complete --run-dir=/r --action=1"), claude_result("a", improve),
                  claude_call("s", None, tool="Skill", skill="skill-craft:improve", args="x"), claude_result("s", "Launching skill"),
                  claude_call("b", f"python3 {CLI} complete --run-dir=/r --action=2"), claude_result("b", PACKET),
                  claude_call("c", f"python3 {CLI} complete --run-dir=/r --action=3"), claude_result("c", improve),
                  claude_call("d", f"python3 {CLI} complete --run-dir=/r --action=4"), claude_result("d", PACKET)]
        with tempfile.TemporaryDirectory() as temp:
            found = metrics.reading_path(write_run(Path(temp) / "r", events))["improve_skill_invoked"]
        self.assertEqual((found["count"], found["of"]), (1, 2))
        self.assertEqual([s["invoked"] for s in found["stages"]], [True, False])


class OrientationTests(unittest.TestCase):
    """What a fresh session read before it changed anything (clear.orientation), beside the S-6 count of redone work."""

    def test_another_hosts_stream_is_not_measured_and_is_not_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            grok = materialise("grok-long-run", Path(temp))
            found = clear.orientation(grok / "events.jsonl", 100)
        self.assertFalse(found["measured"])
        self.assertIsNone(found["orientation_bytes"])
        self.assertIn("Claude", found["reason"])

    def stream(self, read_chars: int) -> list:
        return [
            claude_call("w0", None, tool="Write", file_path="/w/a.js", content="one"), claude_result("w0", "ok"),
            # --- the clear is here (event 2); the fresh session begins
            claude_call("r1", None, tool="Read", file_path="/p/skills/shiploop/SKILL.md"), claude_result("r1", "x" * read_chars),
            claude_call("n1", f'python3 {CLI} next --run-dir "/runs/a/run"'), claude_result("n1", PACKET),
            claude_call("w1", None, tool="Write", file_path="/w/b.js", content="two"), claude_result("w1", "ok")]

    def test_a_big_card_read_before_the_first_change_is_orientation_and_a_pass_stays_a_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = write_run(Path(temp) / "o", self.stream(79_950))
            found = clear.orientation(out / "events.jsonl", 2)
            self.assertGreaterEqual(found["orientation_bytes"]["total"], 79_950)
            self.assertEqual(found["orientation_bytes"]["by_class"]["entry_card"]["chars"], 79_950)
            self.assertEqual(found["read_only_calls"], 2)
            self.assertEqual(found["first_state_changing_call"]["kinds"], ["write"])
            self.assertEqual(clear.redone(out / "events.jsonl", 2), [], "S-6 counts only repeated state-changing calls")

    def test_the_time_to_the_first_state_changing_call_is_the_seconds_from_the_clear_to_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = write_run(Path(temp) / "t", self.stream(10))
            # events are one second apart: the clear's first event is line 2, the write is line 6
            self.assertEqual(clear.orientation(out / "events.jsonl", 2)["time_to_first_state_changing_call"], 4.0)

    def test_a_session_that_changed_nothing_has_no_first_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = write_run(Path(temp) / "n", self.stream(10)[:6])
            found = clear.orientation(out / "events.jsonl", 2)
            self.assertIsNone(found["first_state_changing_call"])
            self.assertIsNone(found["time_to_first_state_changing_call"])

    def test_a_run_with_no_timeline_has_bytes_and_no_time(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = write_run(Path(temp) / "s", self.stream(10), stamps=False)
            found = clear.orientation(out / "events.jsonl", 2)
            self.assertIsNone(found["time_to_first_state_changing_call"])
            self.assertEqual(found["orientation_bytes"]["total"], 10 + len(PACKET))


def summary(**fields) -> dict:
    base = {"host": "claude", "redone": 0, "refusals": 2, "warm_next_calls": 1, "ingest_chars": 1_000_000,
            "orientation_bytes": 100_000, "improve_skill": {"invoked": 4, "of": 4}, "obligations_lost": [], "spec_flipped": [],
            "seeded_defect_caught": True}
    return {**base, **fields}


class ArmsTests(unittest.TestCase):
    AA = {"s1": {"refusals": 1, "warm_next_calls": 1, "ingest_chars": 50_000, "orientation_bytes": 10_000}}

    def decide(self, candidate: dict, control: dict | None = None, aa: dict | None = AA) -> dict:
        return arms.decide({"s1": control or summary()}, {"s1": candidate}, aa)

    def test_fewer_bytes_beyond_the_spread_and_no_gate_failed_chooses_the_candidate(self) -> None:
        report = self.decide(summary(ingest_chars=700_000, orientation_bytes=95_000))
        self.assertEqual((report["decision"], report["exit"]), ("candidate", 0))

    def test_more_bytes_beyond_the_spread_chooses_the_control(self) -> None:
        report = self.decide(summary(ingest_chars=1_300_000))
        self.assertEqual((report["decision"], report["exit"]), ("control", 0))

    def test_a_difference_inside_the_spread_decides_nothing(self) -> None:
        report = self.decide(summary(ingest_chars=980_000, orientation_bytes=101_000))
        self.assertEqual((report["decision"], report["exit"]), (None, 2))
        self.assertIn("inside the A/A spread", report["reason"])

    def test_byte_metrics_that_disagree_decide_nothing(self) -> None:
        report = self.decide(summary(ingest_chars=800_000, orientation_bytes=150_000))
        self.assertEqual((report["decision"], report["exit"]), (None, 2))
        self.assertIn("disagree", report["reason"])

    def test_without_an_aa_spread_there_is_nothing_to_decide_from(self) -> None:
        report = self.decide(summary(ingest_chars=500_000), aa=None)
        self.assertEqual((report["decision"], report["exit"]), (None, 3))

    def test_each_hard_gate_rejects_the_candidate_however_few_bytes_it_took_in(self) -> None:
        cheap = {"ingest_chars": 1, "orientation_bytes": 1}
        cases = {"redone": {"redone": 1}, "refusals": {"refusals": 9}, "warm_next_calls": {"warm_next_calls": 5},
                 "obligations": {"obligations_lost": ["rules"]}, "spec": {"spec_flipped": ["S-6"]},
                 "improve_skill": {"improve_skill": {"invoked": 3, "of": 4}}, "seeded_defect": {"seeded_defect_caught": False}}
        for gate, change in cases.items():
            with self.subTest(gate=gate):
                report = self.decide(summary(**cheap, **change))
                self.assertEqual((report["decision"], report["exit"]), ("control", 0))
                self.assertEqual({g["gate"] for g in report["gates_failed"]}, {gate})

    def test_a_count_within_control_plus_the_spread_passes_its_gate(self) -> None:
        report = self.decide(summary(refusals=3, warm_next_calls=2, ingest_chars=500_000, orientation_bytes=50_000))
        self.assertEqual(report["gates_failed"], [])
        self.assertEqual(report["decision"], "candidate")

    def test_a_slice_with_no_spread_is_judged_by_the_hard_gates_and_its_counts_are_descriptive(self) -> None:
        report = arms.decide({"g": summary(host="grok")}, {"g": summary(host="grok", refusals=30, ingest_chars=1)}, {})
        self.assertEqual(report["gates_failed"], [])
        self.assertTrue(any("descriptive" in n and "refusals" in n for n in report["notes"]))
        self.assertEqual(report["exit"], 3)
        failed = arms.decide({"g": summary(host="grok")}, {"g": summary(host="grok", redone=2)}, {})
        self.assertEqual((failed["decision"], failed["exit"]), ("control", 0))

    def test_the_improve_skill_gate_binds_claude_only(self) -> None:
        report = arms.decide({"g": summary(host="grok")}, {"g": summary(host="grok", improve_skill=None, ingest_chars=1)}, {})
        self.assertEqual(report["gates_failed"], [])

    def test_the_spread_is_the_difference_between_the_two_control_runs_of_a_slice(self) -> None:
        first = {"s1": summary(refusals=2, ingest_chars=1_000_000), "s2": summary(refusals=5)}
        second = {"s1": summary(refusals=4, ingest_chars=940_000)}
        found = arms.spread(first, second)
        self.assertEqual(found["s1"]["refusals"], 2)
        self.assertEqual(found["s1"]["ingest_chars"], 60_000)
        self.assertNotIn("s2", found)

    def test_the_command_line_prints_the_chosen_arm_and_exits_by_the_decision(self) -> None:
        script = ROOT / "test" / "shiploop_e2e" / "arms.py"
        with tempfile.TemporaryDirectory() as temp:
            def arm(name: str, record: dict) -> Path:
                folder = Path(temp) / name
                folder.mkdir()
                (folder / "s1.summary.json").write_text(json.dumps(record))
                return folder
            control, aa1, aa2 = arm("control", summary()), arm("aa1", summary(ingest_chars=1_000_000, orientation_bytes=100_000)), \
                arm("aa2", summary(ingest_chars=1_050_000, orientation_bytes=110_000))
            better = arm("better", summary(ingest_chars=600_000, orientation_bytes=60_000))
            same = arm("same", summary(ingest_chars=1_010_000, orientation_bytes=100_000))

            def run(candidate: Path):
                return subprocess.run([sys.executable, "-B", str(script), str(control), str(candidate), "--aa", str(aa1), str(aa2)],
                                      capture_output=True, text=True)
            chosen, unchosen = run(better), run(same)
        self.assertEqual(chosen.returncode, 0, chosen.stdout + chosen.stderr)
        self.assertIn("DECISION: candidate", chosen.stdout)
        self.assertEqual(unchosen.returncode, 2, unchosen.stdout + unchosen.stderr)
        self.assertIn("NO DECISION", unchosen.stdout)

    def test_one_fixture_folder_of_two_arms_names_an_arm_and_exits_zero_and_exits_non_zero_inside_the_spread(self) -> None:
        script = ROOT / "test" / "shiploop_e2e" / "arms.py"
        chosen = subprocess.run([sys.executable, "-B", str(script), str(FIXTURES / "arms-chooses")], capture_output=True, text=True)
        inside = subprocess.run([sys.executable, "-B", str(script), str(FIXTURES / "arms-inside-spread")], capture_output=True, text=True)
        self.assertEqual(chosen.returncode, 0, chosen.stdout + chosen.stderr)
        self.assertIn("DECISION: candidate", chosen.stdout)
        self.assertNotEqual(inside.returncode, 0)
        self.assertEqual(inside.returncode, 2, inside.stdout + inside.stderr)
        self.assertIn("inside the A/A spread", inside.stdout)

    def test_a_folder_that_is_not_an_arm_pair_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            done = subprocess.run([sys.executable, "-B", str(ROOT / "test" / "shiploop_e2e" / "arms.py"), temp], capture_output=True, text=True)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("control/", done.stderr)

    def test_a_slice_with_a_clear_probe_is_summarised_with_its_redone_work_and_its_orientation(self) -> None:
        events = OrientationTests.stream(OrientationTests, 79_950)
        with tempfile.TemporaryDirectory() as temp:
            out = write_run(Path(temp) / "probe", events)
            (out / "slice-result.json").write_text(json.dumps({"clear": {
                "stage": "implement", "inside": False, "stopped": {"events_line": 2}, "redone": [], "pass": True}}))
            found = arms.summarise(out)
        self.assertEqual(found["redone"], 0)
        self.assertGreaterEqual(found["orientation_bytes"], 79_950)
        self.assertEqual([c["position"] for c in found["clears"]], ["implement"])
        self.assertEqual(found["clears"][0]["time_to_first_state_changing_call"], 4.0)

    def test_a_slice_output_is_summarised_from_its_own_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = materialise("claude-step-slice", Path(temp))
            found = arms.summarise(out)
        self.assertEqual((found["host"], found["warm_next_calls"], found["piped_shiploop_calls"]), ("claude", 0, 20))
        self.assertEqual(found["improve_skill"], {"invoked": 1, "of": 4})
        self.assertIsNone(found["redone"], "a slice with no clear probe has no redone count, which is not zero")
        self.assertIsNone(found["seeded_defect_caught"])


@unittest.skipUnless(NODE, "node is needed to run the planted-defect probes")
class SeededDefectTests(unittest.TestCase):
    def test_the_three_cases_are_the_three_defects_the_plan_names(self) -> None:
        found = {case["seeded_defect"]["id"] for case in seeded_defects.cases().values()}
        self.assertEqual(found, {"case-insensitive-compare", "numbers-sorted-as-text", "missing-empty-guard"})

    def test_a_run_with_no_review_leaves_each_defect_in_a_tree_that_passes_its_own_checks_and_the_fixed_tree_does_not(self) -> None:
        rows = seeded_defects.verify()
        self.assertEqual(len(rows), 3)
        for row in rows:
            with self.subTest(case=row["case"]):
                self.assertTrue(row["naive_survives_its_checks"], "the case's own checks pass on the unreviewed tree")
                self.assertTrue(row["naive_defect_present"], "and a probe fails on it")
                self.assertTrue(row["fixed_checks_pass"])
                self.assertFalse(row["fixed_defect_present"])

    def test_the_final_tree_of_a_slice_is_scored_by_its_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            for kind, present in (("naive", True), ("fixed", False)):
                out = Path(temp) / kind
                out.mkdir()
                case = seeded_defects.cases()["node-seeded-empty-guard"]
                tree = seeded_defects.reference_tree(case, kind, Path(temp) / "trees")
                shutil.copytree(tree, out / "export")
                (out / "invocation.json").write_text(json.dumps({"case": "node-seeded-empty-guard"}))
                with self.subTest(kind=kind):
                    scored = seeded_defects.score_output(out)
                    self.assertEqual((scored["case"], scored["present"], scored["checks_pass"]), ("node-seeded-empty-guard", present, True))

    def test_a_case_without_a_planted_defect_or_a_folder_without_an_export_has_no_score(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "invocation.json").write_text(json.dumps({"case": "node-fix-bug"}))
            self.assertIsNone(seeded_defects.score_output(Path(temp)))
            (Path(temp) / "invocation.json").write_text(json.dumps({"case": "node-seeded-empty-guard"}))
            self.assertIsNone(seeded_defects.score_output(Path(temp)))

    def test_no_probe_is_one_of_the_commands_a_run_is_graded_by(self) -> None:
        for name, case in seeded_defects.cases().items():
            with self.subTest(case=name):
                self.assertFalse(set(case["seeded_defect"]["probe"]) & set(case["checks"]))
                self.assertTrue(case["checks"] and case["expect_paths"] and case["work_item"]["id"] == "W1")
                self.assertTrue((seeded_defects.FIXTURES / case["fixture"] / "package.json").is_file())

    def test_the_probe_command_line_exits_zero_when_every_case_discriminates(self) -> None:
        done = subprocess.run([sys.executable, "-B", str(ROOT / "test" / "shiploop_e2e" / "seeded_defects.py"), "verify"],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


class HomeFixtureTests(unittest.TestCase):
    def test_the_long_home_is_about_16_14_and_6_kilobytes_and_the_small_one_a_few_hundred_characters(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            long_sizes = home_fixtures.write_home(Path(temp) / "long", "long")
            small_sizes = home_fixtures.write_home(Path(temp) / "small", "small")
            empty = home_fixtures.write_home(Path(temp) / "empty", "empty")
        for name, target in home_fixtures.LONG.items():
            self.assertTrue(target <= long_sizes[name] < target * 1.05, (name, long_sizes[name]))
        for name, target in home_fixtures.SMALL.items():
            self.assertTrue(target <= small_sizes[name] < target * 1.5, (name, small_sizes[name]))
        self.assertEqual(empty, {})

    def test_a_document_is_deterministic_neutral_and_has_the_files_sections(self) -> None:
        import shiploop_knowledge_home as home
        for name in home_fixtures.FILES:
            text = home_fixtures.document(name, 3_000)
            self.assertEqual(text, home_fixtures.document(name, 3_000))
            self.assertIn("## " + home.SECTIONS[name][0], text)
            for word in ("chess", "salesforce", "apex", "battleship", "node", "lightning"):
                self.assertNotIn(word, text.lower())
        self.assertIn("R-1:", home_fixtures.document("spec.md", 500))

    def test_a_long_home_makes_the_packets_larger_and_a_small_one_barely(self) -> None:
        empty, small, long = (home_fixtures.sizes(kind) for kind in ("empty", "small", "long"))
        self.assertEqual(empty["packets"], 33)
        self.assertGreater(long["file_chars"], 1.8 * empty["file_chars"])
        self.assertLess(small["file_chars"], 1.1 * empty["file_chars"])

    def test_a_small_homes_packets_have_the_same_fingerprints_on_every_walk(self) -> None:
        self.assertEqual(home_fixtures.fingerprints("small"), home_fixtures.fingerprints("small"))
        self.assertNotEqual(home_fixtures.fingerprints("small"), home_fixtures.fingerprints("long"))


class AuditProbeTests(unittest.TestCase):
    def test_the_three_probes_run_on_this_checkout(self) -> None:
        found = audit_probes.measure(ROOT, audit_probes.AUDIT_ROOT_LENGTH)
        self.assertEqual(set(found["figures"]), set(audit_probes.AUDITED))
        for name, value in found["figures"].items():
            with self.subTest(figure=name):
                self.assertTrue(0.8 < value / audit_probes.AUDITED[name] < 1.5, value)
        self.assertEqual(found["delivery"]["packets"], 33)
        self.assertEqual(found["handoffs"]["handoffs"], 9)

    def test_the_audited_figures_reproduce_exactly_at_the_audited_commit(self) -> None:
        """375,278 / 276,270 / 79,647 characters at 2686b427, read at the audit's path lengths."""
        commit = "2686b427"
        have = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", commit + "^{commit}"], capture_output=True)
        if have.returncode:
            self.skipTest(f"{commit} is not in this clone's history")
        with tempfile.TemporaryDirectory() as temp:
            archive = subprocess.run(["git", "-C", str(ROOT), "archive", commit, "skills"], capture_output=True, check=True)
            subprocess.run(["tar", "-x", "-C", temp], input=archive.stdout, check=True)
            found = audit_probes.measure(Path(temp), audit_probes.AUDIT_ROOT_LENGTH)
        self.assertEqual(found["figures"], audit_probes.AUDITED)


if __name__ == "__main__":
    unittest.main()
