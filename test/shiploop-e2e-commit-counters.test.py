#!/usr/bin/env python3
"""The harness's `packets` and `commits` blocks of metrics.json (test/shiploop_e2e/counters.py, SPEC rows S-7 and S-11).

`packets`: one entry per packet file of a run, {action, stage, file_bytes, head_bytes}, the head being the bytes ShipLoop first
printed for it as the host recorded the reply. `commits`: the commits a run made in the product repository, by who made them,
with how many carry a lessons section and how many cite an earlier commit. Both are records: absent means unknown (null and a
reason), nothing is scored.

The packet tests read compact extracts of real saved runs (test/fixtures/commit-counters, cut by cut_fixtures.py from a Claude,
a Grok and a Codex run) and never the saved runs themselves. The commit tests build their histories with real git in temporary
repositories (their own HOME, no system or global git config) from real messages of the same runs, and make the ShipLoop-owned
commits with ShipLoop's own functions where one can be called, so a changed subject breaks a test.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import counters  # noqa: E402
import metrics  # noqa: E402

FIXTURES = ROOT / "test" / "fixtures" / "commit-counters"


def tool_log(name: str) -> metrics.ToolLog:
    """The fixture's host events read the one way every run is read: ToolLog.feed, event by event."""
    tools = metrics.ToolLog()
    for number, event in metrics.events(FIXTURES / name / "events.jsonl"):
        tools.feed(event, None, number)
    return tools


def packets_of(name: str, tools: metrics.ToolLog | None = None):
    out = FIXTURES / name
    return counters.packets(out, out / "run", tool_log(name) if tools is None else tools)


def entry(block: list[dict], action_tail: str) -> dict:
    found = [row for row in block if row["action"].endswith(action_tail)]
    assert len(found) == 1, (action_tail, [row["action"] for row in block])
    return found[0]


def reply(name: str, call_tail: str) -> str:
    """The text of the tool result of the call whose id ends with ``call_tail``, as the fixture's events hold it."""
    for _number, event in metrics.events(FIXTURES / name / "events.jsonl"):
        for call_id, shown in metrics.tool_results(event):
            if str(call_id).endswith(call_tail):
                return shown
    raise AssertionError(f"no result for a call ending {call_tail} in {name}")


def size_from(text: str, marker: str, until: str | None = None) -> int:
    """Bytes of ``text`` from the first ``marker`` on (to the end of the ``until`` line when it is given): a second way to
    count a head, by slicing the recorded reply, that shares no code with counters.py."""
    start = text.index(marker)
    if until is None:
        return len(text[start:].encode("utf-8"))
    stop = text.index(until, start) + len(until)
    if text[stop:stop + 1] == "\n":
        stop += 1
    return len(text[start:stop].encode("utf-8"))


def header(path: Path) -> tuple[str, int]:
    """(stage, revision) of the first `ShipLoop navigator | <stage> | revision N` line of a packet file: the line is first in
    some files and sits under a delegation preamble of 11 or 15 lines in others."""
    found = re.search(r"^ShipLoop navigator \| ([\w-]+) \| revision (\d+)", path.read_text(), re.M)
    return found.group(1), int(found.group(2))


NARRATIVE_END = "=== end ShipLoop narrative ==="
STATUS_END = "=== end ShipLoop status ==="


class ClaudeHeadsTest(unittest.TestCase):
    """r3-battleship-sonnet (ShipLoop 0.58.0): the model piped most replies through head, so most heads are not whole."""

    def setUp(self):
        self.block, self.unmeasured = packets_of("claude")

    def test_a_whole_head_is_counted_from_its_first_line_not_from_the_command_output_before_it(self):
        intake = entry(self.block, "nav-e8451e133ad642eaa4332381529f0402")
        text = reply("claude", "kDXdJA")  # `init` printed two lines of its own, then the head
        self.assertTrue(text.startswith("Workspace root:"))
        self.assertEqual(intake["head_bytes"], size_from(text, "ShipLoop navigator | intake", NARRATIVE_END))
        self.assertLess(intake["head_bytes"], len(text.encode("utf-8")))
        self.assertEqual(intake["stage"], "intake")

    def test_an_improve_childs_second_packet_is_its_own_entry_keyed_by_its_file_name(self):
        improve = entry(self.block, "nav-2c041669205c42629ae9df0195b7bc3f-improve")
        self.assertEqual(improve["stage"], "spec")
        self.assertEqual(improve["head_bytes"], size_from(reply("claude", "15m5ZD"), "ShipLoop navigator | spec", NARRATIVE_END))
        self.assertEqual(len({row["action"] for row in self.block}), len(self.block), "action is the unique key")

    def test_a_head_the_model_cut_after_its_keepalive_line_is_null_not_zero_and_not_the_cut_size(self):
        discovery = entry(self.block, "nav-04d9eb3d91444bd3af6006c7c2dfc7f9")
        self.assertIsNone(discovery["head_bytes"])
        text = reply("claude", "C1ncio")
        self.assertNotIn(STATUS_END, text, "the fixture's reply is the cut one")

    def test_the_done_packet_printed_as_a_pointer_and_a_prefix_is_null(self):
        done = entry(self.block, "nav-885ea92ea8f945bc86085c784a77ba5c")
        self.assertEqual(done["stage"], "done")
        self.assertIsNone(done["head_bytes"])

    def test_a_packet_no_reply_shows_is_null(self):
        self.assertIsNone(entry(self.block, "nav-c0f5c72b6e24473f96badbeb0dcdea9f")["head_bytes"])

    def test_file_bytes_is_the_size_on_disk_and_stage_is_the_files_own_first_line(self):
        folder = FIXTURES / "claude" / "run" / "packets"
        for row in self.block:
            path = folder / (row["action"] + ".md")
            self.assertEqual(row["file_bytes"], path.stat().st_size)
            self.assertEqual(row["stage"], header(path)[0])
        self.assertEqual(len(self.block), len(list(folder.glob("*.md"))), "one entry per packet file")

    def test_entries_follow_the_run_by_revision_and_an_improve_packet_follows_its_producers_packet(self):
        folder = FIXTURES / "claude" / "run" / "packets"

        def key(row):
            return header(folder / (row["action"] + ".md"))[1], row["action"]
        self.assertEqual(self.block, sorted(self.block, key=key))
        self.assertEqual([row["stage"] for row in self.block], ["intake", "discovery", "spec", "implement", "done"])

    def test_the_one_reason_names_the_host_and_counts_what_could_not_be_measured(self):
        self.assertEqual(set(self.unmeasured), {"head_bytes"})
        reason = self.unmeasured["head_bytes"]
        missing = sum(row["head_bytes"] is None for row in self.block)
        self.assertEqual(missing, 3)
        self.assertTrue(reason.startswith("claude: "), reason)
        self.assertIn(f"{missing} of {len(self.block)} packets", reason)

    def test_a_read_of_the_whole_packet_is_not_a_print(self):
        read = reply("claude", "w8VJbk")
        self.assertIn("ShipLoop navigator | intake", read, "the Read returned the file, which holds the head's first line")
        self.assertGreater(len(read.encode("utf-8")), 20000)
        head = entry(self.block, "nav-e8451e133ad642eaa4332381529f0402")["head_bytes"]
        self.assertIsNotNone(head)
        self.assertLess(head, 6000)


class ClaudeWholeHeadsTest(unittest.TestCase):
    """s6-after-spec: replies of `complete` that carry a whole head, and the ways a reply can still not be one."""

    def setUp(self):
        self.block, self.unmeasured = packets_of("claude-wholes")

    def test_the_first_whole_print_counts_when_an_earlier_print_of_the_same_packet_was_cut(self):
        row = entry(self.block, "nav-c4ba9a9058014550990e958165d663fb")
        earlier = reply("claude-wholes", "DkGpNr")  # a grep of the run's output: it names the packet and holds no closing line
        self.assertNotIn(STATUS_END, earlier)
        self.assertEqual(row["head_bytes"], size_from(reply("claude-wholes", "YKoYJ1"), "ShipLoop navigator | ", NARRATIVE_END))

    def test_the_first_of_two_whole_prints_counts_even_when_the_later_one_is_shorter(self):
        # A recovery `next` reprints the head, usually without the milestone narrative the first print carried.
        tools = tool_log("claude")
        first = next(row for row in tools.replies if "ShipLoop navigator | intake" in row["text"] and not row["packet"])
        later = first["text"][:first["text"].index("=== ShipLoop narrative ===")]
        tools.replies.append({"event": 10 ** 6, "packet": False, "text": later})
        block, _ = packets_of("claude", tools)
        self.assertEqual(entry(block, "nav-e8451e133ad642eaa4332381529f0402")["head_bytes"],
                         size_from(first["text"], "ShipLoop navigator | intake", NARRATIVE_END))

    def test_a_head_whose_narrative_is_cut_halfway_is_not_whole(self):
        # `complete ... | head -60`: the status block is intact, the narrative opens and never closes.
        text = reply("claude-wholes", "EuCFqm")
        self.assertIn(STATUS_END, text)
        self.assertIn("=== ShipLoop narrative ===", text)
        self.assertNotIn(NARRATIVE_END, text)
        self.assertIsNone(entry(self.block, "nav-d926cc413ae341c39bf2f3e195cf9780")["head_bytes"])

    def test_a_pipe_elsewhere_in_the_command_does_not_hide_a_whole_head(self):
        # The command ran `lint ... | tail -5` first and an unpiped `complete` last: the reply is lint's lines, then a whole head.
        row = entry(self.block, "nav-2c8e30b02e3c4ee59c364c60e1b25538")
        text = reply("claude-wholes", "rSm2vA")
        self.assertTrue(text.startswith("END lint data"), "the lint output comes first and is not counted")
        self.assertEqual(row["head_bytes"], size_from(text, "ShipLoop navigator | ", STATUS_END))
        self.assertLess(row["head_bytes"], len(text.encode("utf-8")))

    def test_a_call_that_names_a_packet_file_is_never_a_print_even_when_its_reply_holds_a_head(self):
        row = entry(self.block, "nav-7a4ef755a80b4b2c8fa388f037975393")
        self.assertIsNone(row["head_bytes"])

    def test_an_improve_packet_head_is_matched_to_its_own_file(self):
        row = entry(self.block, "nav-e9d64868fba44a7e94414170631e6f7c-improve")
        self.assertIsNotNone(row["head_bytes"])
        self.assertEqual(row["head_bytes"], size_from(reply("claude-wholes", "2erBJt"), "ShipLoop navigator | ", STATUS_END))


class ColumnCutHeadTest(unittest.TestCase):
    def test_a_head_with_every_line_but_a_shortened_callback_line_is_not_whole(self):
        block, unmeasured = packets_of("claude-columns")
        text = reply("claude-columns", "9nLJam")
        self.assertIn(STATUS_END, text, "every line is there: the model cut by column, not by line")
        callback = next(line for line in text.splitlines() if line.startswith("Callback for this stage"))
        self.assertFalse(callback.rstrip().endswith(".md"), "the callback line lost its result path")
        self.assertIsNone(entry(block, "nav-768092291a774d1ebc62b2e7c285b89d")["head_bytes"])
        self.assertIn("1 of 1 packets", unmeasured["head_bytes"])


class GrokHeadsTest(unittest.TestCase):
    """r3-battleship-grok-none: Grok records the reply as `output_for_prompt` after an `exit: N` line, and its own `total_bytes`."""

    def setUp(self):
        self.block, self.unmeasured = packets_of("grok")

    def total_bytes(self, call_tail: str) -> int:
        for _number, event in metrics.events(FIXTURES / "grok" / "events.jsonl"):
            if str(event.get("toolCallId", "")).endswith(call_tail) and isinstance(event.get("rawOutput"), dict):
                return event["rawOutput"]["total_bytes"]
        raise AssertionError(call_tail)

    def test_a_head_that_is_the_whole_output_is_the_size_the_host_counted(self):
        # The host's own byte count of the command's output is an independent check of the head's size.
        for tail, action in (("aa-11", "nav-bdf2efb2038b434c85f324f1d1a1cd05"), ("b3d18-36", "nav-8bd7834ee0234c4190d39b736ca7ddf8")):
            self.assertEqual(entry(self.block, action)["head_bytes"], self.total_bytes(tail), action)

    def test_the_hosts_exit_line_and_a_commands_own_first_lines_are_not_the_head(self):
        row = entry(self.block, "nav-5195c9a34320448ca9037824af1e7c38")
        text = reply("grok", "5439b8-1") if False else reply("grok", "10b2365439b8-1")
        self.assertTrue(text.startswith("exit: 0\nWorkspace root:"))
        # total_bytes counts the command's whole output: its own lines first, then the head. The host's `exit: 0` line is its own.
        own = text[len("exit: 0\n"):text.index("ShipLoop navigator | ")].encode("utf-8")
        self.assertEqual(row["head_bytes"], self.total_bytes("10b2365439b8-1") - len(own))

    def test_every_grok_head_in_the_extract_is_measured_so_nothing_is_unmeasured(self):
        self.assertTrue(all(row["head_bytes"] is not None for row in self.block))
        self.assertEqual(self.unmeasured, {})


class CodexHeadsTest(unittest.TestCase):
    """v1210-battleship-luna-xhigh: the translated tool_call_update carries `output_for_prompt` with no exit line."""

    def setUp(self):
        self.block, self.unmeasured = packets_of("codex")

    def test_a_head_followed_by_output_the_model_chained_ends_at_its_own_closing_line(self):
        intake = entry(self.block, "nav-9ba67ad41a6a46f4b4bf8e5fae7c4e87")
        plain, chained = reply("codex", "item_9"), reply("codex", "item_18")
        self.assertEqual(intake["head_bytes"], size_from(plain, "ShipLoop navigator | intake", NARRATIVE_END))
        self.assertIn("drwx------", chained, "the second print is followed by an `ls` the model chained")
        self.assertEqual(size_from(chained, "ShipLoop navigator | intake", NARRATIVE_END), intake["head_bytes"])

    def test_codex_heads_are_measured(self):
        self.assertTrue(all(row["head_bytes"] is not None for row in self.block))
        self.assertEqual(self.unmeasured, {})


class UnreadableRunsTest(unittest.TestCase):
    def test_a_run_without_a_packets_folder_is_null_with_the_reason_and_not_an_empty_list(self):
        out = FIXTURES / "claude"
        block, unmeasured = counters.packets(out, out / "no-such-run", tool_log("claude"))
        self.assertIsNone(block)
        self.assertEqual(set(unmeasured), {"packets"})
        self.assertIn("packets", unmeasured["packets"])

    def test_a_run_with_no_run_directory_is_null_with_the_reason(self):
        block, unmeasured = counters.packets(FIXTURES / "claude", None, tool_log("claude"))
        self.assertIsNone(block)
        self.assertIn("run directory", unmeasured["packets"])

    def test_a_host_that_recorded_no_reply_leaves_every_head_null_and_says_so_once(self):
        block, unmeasured = packets_of("claude", metrics.ToolLog())
        self.assertEqual([row["head_bytes"] for row in block], [None] * len(block))
        self.assertEqual(len(unmeasured), 1)

    def test_an_empty_packets_folder_is_a_measured_empty_list(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "run" / "packets").mkdir(parents=True)
            block, unmeasured = counters.packets(Path(tmp), Path(tmp) / "run", metrics.ToolLog())
        self.assertEqual((block, unmeasured), ([], {}))


class ToolLogRepliesTest(unittest.TestCase):
    def test_a_result_the_host_repeats_for_one_call_is_kept_once(self):
        tools = metrics.ToolLog()
        events = list(metrics.events(FIXTURES / "grok" / "events.jsonl"))
        (call_number, call), (update_number, update) = events[2], events[3]
        tools.feed(call, None, call_number)
        tools.feed(update, None, update_number)
        tools.feed(update, None, update_number)  # Grok repeats an update for one call
        self.assertEqual(len(tools.replies), 1)

    def test_only_replies_that_hold_a_head_or_a_commit_line_are_kept(self):
        tools = metrics.ToolLog()
        tools.call(0, "x", "Bash", {"command": "ls"})
        tools.result("x", "total 0\n", 0)
        self.assertEqual(tools.replies, [])

    def test_the_kept_replies_say_whether_their_call_named_a_packet_file(self):
        tools = tool_log("claude")
        named = [row for row in tools.replies if row["packet"]]
        printed = [row for row in tools.replies if not row["packet"]]
        self.assertEqual(len(named), 1, "the Read of the whole intake packet")
        self.assertEqual(len(printed), 5)


class ShipLoopOwnedTextTest(unittest.TestCase):
    """The harness reads ShipLoop's own words; a reworded line must fail here and not turn every head into null."""

    def test_the_closing_lines_and_the_head_markers_are_the_ones_shiploop_prints(self):
        import shiploop_narrative
        import shiploop_navigator
        self.assertEqual(counters.NARRATIVE_END, shiploop_narrative.END)
        self.assertEqual(counters.NARRATIVE_BEGIN, shiploop_narrative.BEGIN)
        self.assertEqual(counters.STATUS_END, shiploop_navigator.STATUS_END)
        self.assertEqual(counters.STATUS_BEGIN, shiploop_navigator.STATUS_BEGIN)
        source = (ROOT / "skills" / "shiploop" / "scripts" / "shiploop_navigator.py").read_text()
        for line in ('f"ShipLoop navigator | {stage} | revision {state[\'revision\']}"', 'f"Full packet: {path}"',
                     'f"Keepalive marker: {KEEPALIVE_MARKER} run='):
            self.assertIn(line, source)

    def test_the_kept_reply_filter_covers_every_pattern_counters_reads(self):
        for sample in ("ShipLoop navigator | discovery | revision 1", "Committed this review's changes as 7e11860aaaaa: a.py.",
                       "ShipLoop committed W1's declared changes as 65cd022aaaaa."):
            self.assertTrue(metrics.KEPT_REPLY.search(sample), sample)


if __name__ == "__main__":
    unittest.main()
