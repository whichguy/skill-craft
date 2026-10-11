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

import contextlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import counters  # noqa: E402
import metrics  # noqa: E402
import shiploop_git  # noqa: E402
import shiploop_item_scope  # noqa: E402
import shiploop_knowledge_home as knowledge_home  # noqa: E402
import shiploop_lessons as commit_lessons  # noqa: E402
import shiploop_navigator  # noqa: E402
import shiploop_workspace  # noqa: E402

FIXTURES = ROOT / "test" / "fixtures" / "commit-counters"
CONTRACT = ROOT / "test" / "fixtures" / "commit-contract"  # the message shapes ShipLoop's own grammar is pinned with


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

    def test_a_whole_head_without_the_packets_own_pointer_names_no_file_and_is_not_attributed(self):
        tools = tool_log("claude")
        reply_row = next(row for row in tools.replies if "ShipLoop navigator | intake" in row["text"] and not row["packet"])
        reply_row["text"] = re.sub(r"^Full packet: [^\n]*\n", "", reply_row["text"], flags=re.M)
        block, _ = packets_of("claude", tools)
        self.assertIsNone(entry(block, "nav-e8451e133ad642eaa4332381529f0402")["head_bytes"])
        self.assertEqual({row["action"] for row in block if row["head_bytes"] is not None},
                         {"nav-2c041669205c42629ae9df0195b7bc3f-improve"}, "no other packet is credited with that head")

    def test_a_head_whose_keepalive_line_is_shortened_is_not_whole(self):
        tools = tool_log("claude")
        reply_row = next(row for row in tools.replies if "ShipLoop navigator | intake" in row["text"] and not row["packet"])
        reply_row["text"] = re.sub(r"(Keepalive marker: [^\n]{30})[^\n]*", r"\1", reply_row["text"])
        block, _ = packets_of("claude", tools)
        self.assertIsNone(entry(block, "nav-e8451e133ad642eaa4332381529f0402")["head_bytes"])

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


class WhyAHeadIsNotWholeTest(unittest.TestCase):
    """counters.head_or_why: the head, or the one way a reply is not a whole print of it (the baseline's tallies name them)."""

    @staticmethod
    def from_head(text: str) -> str:
        return text[text.index("ShipLoop navigator | "):]

    def test_a_whole_head_comes_back_with_no_reason_and_the_size_the_packets_block_counts(self):
        text = self.from_head(reply("claude-wholes", "YKoYJ1"))
        head, why = counters.head_or_why(text)
        self.assertIsNone(why)
        self.assertEqual(len(head.encode("utf-8")), size_from(text, "ShipLoop navigator | ", NARRATIVE_END))
        block, _ = packets_of("claude-wholes")
        self.assertEqual(entry(block, "nav-c4ba9a9058014550990e958165d663fb")["head_bytes"], len(head.encode("utf-8")))

    def test_a_reply_that_stops_before_the_closing_line_says_so(self):
        text = self.from_head(reply("claude-wholes", "YKoYJ1"))
        self.assertEqual(counters.head_or_why(text[:text.index(STATUS_END)]), (None, counters.NOT_WHOLE_BEFORE_CLOSING))

    def test_a_reply_that_opens_the_narrative_and_never_closes_it_says_so(self):
        text = self.from_head(reply("claude-wholes", "EuCFqm"))
        self.assertEqual(counters.head_or_why(text), (None, counters.NOT_WHOLE_IN_NARRATIVE))

    def test_a_reply_with_every_line_and_a_shortened_callback_line_says_so(self):
        text = self.from_head(reply("claude-columns", "9nLJam"))
        self.assertEqual(counters.head_or_why(text), (None, counters.NOT_WHOLE_SHORTENED))

    def test_the_reasons_are_three_different_texts(self):
        reasons = {counters.NOT_WHOLE_BEFORE_CLOSING, counters.NOT_WHOLE_IN_NARRATIVE, counters.NOT_WHOLE_SHORTENED}
        self.assertEqual(len(reasons), 3)


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
        text = reply("grok", "10b2365439b8-1")
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
        source = (ROOT / "skills" / "shiploop" / "scripts" / "shiploop_navigator.py").read_text()
        for line in ('f"ShipLoop navigator | {stage} | revision {state[\'revision\']}"', 'f"Full packet: {path}"',
                     'f"Keepalive marker: {KEEPALIVE_MARKER} run='):
            self.assertIn(line, source)

    def test_the_kept_reply_filter_covers_every_pattern_counters_reads(self):
        for sample in ("ShipLoop navigator | discovery | revision 1", "Committed this review's changes as 7e11860aaaaa: a.py.",
                       "ShipLoop committed W1's declared changes as 65cd022aaaaa.",
                       "ShipLoop committed W1's changes (its declared paths and documentation) as 65cd022aaaaa."):
            self.assertTrue(metrics.KEPT_REPLY.search(sample), sample)

    def test_the_work_item_announcement_is_read_in_both_wordings_saved_runs_hold(self):
        # Release 1.27 reworded the line (the item's documentation rides in its commit); saved runs hold the older wording. The
        # regrade reads both, so a reworded announcement is not silently classified by subject alone.
        for line in ("ShipLoop committed W1's declared changes as 65cd022aaaaa.",
                     "ShipLoop committed W1's changes (its declared paths and documentation) as 65cd022aaaaa."):
            found = counters.ITEM_COMMITTED.search(line)
            self.assertIsNotNone(found, line)
            self.assertEqual(found.group("sha"), "65cd022aaaaa")


# ----------------------------------------------------------------------------------------------------------------- commits

MESSAGES = {row["name"]: row["message"] for row in json.loads((FIXTURES / "messages.json").read_text())}
IMPROVE_LINE = "Committed this review's changes as {sha}: {files}."
ITEM_LINE = "ShipLoop committed {item}'s declared changes as {sha}."


def claude_events(replies: list[str]) -> list[dict]:
    """Claude-shaped events: one Bash call and its result for each reply, read by the same ToolLog.feed as a real run."""
    events = []
    for index, text in enumerate(replies):
        call_id = f"toolu_{index:04d}"
        events.append({"type": "assistant", "message": {"id": f"msg_{index}", "content": [
            {"type": "tool_use", "id": call_id, "name": "Bash", "input": {"command": f"python3 shiploop step-{index}"}}]}})
        events.append({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": call_id, "content": text}]}})
    return events


class GitCase(unittest.TestCase):
    """A temporary run folder with a real product repository in work/, its own HOME and no system or global git config."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / "run-folder"
        self.work = self.out / "work"
        self.work.mkdir(parents=True)
        home = Path(self.tmp.name) / "home"
        home.mkdir()
        patched = mock.patch.dict(os.environ, {"HOME": str(home), "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                                               "GIT_AUTHOR_NAME": "", "GIT_AUTHOR_EMAIL": ""}, clear=False)
        patched.start()
        self.addCleanup(patched.stop)
        for name in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL"):
            os.environ.pop(name, None)
        self.replies: list[str] = []

    def git(self, *args: str, check: bool = True) -> str:
        done = subprocess.run(["git", "-C", str(self.work), *args], capture_output=True, text=True)
        if check and done.returncode:
            raise AssertionError(f"git {args}: {done.stderr}")
        return done.stdout.strip()

    def head(self) -> str:
        return self.git("rev-parse", "HEAD")

    def write(self, name: str, text: str) -> None:
        path = self.work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def by_shiploop(self, name: str, message: str, kind: str | None = None) -> str:
        """A commit ShipLoop's own function makes (the one every ShipLoop commit goes through); ``kind`` names the line ShipLoop
        prints to announce it: 'improve' (improve-commit) or an item id (the verify stage's commit)."""
        self.write(name, f"{name}: {len(self.replies)}\n")
        message_file = Path(self.tmp.name) / "message.txt"
        message_file.write_text(message)
        committed = shiploop_git.commit_paths(self.work, [name], "", message_file=message_file)
        if kind == "improve":
            self.replies.append(IMPROVE_LINE.format(sha=committed.commit[:12], files=name))
        elif kind:
            self.replies.append(ITEM_LINE.format(item=kind, sha=committed.commit[:12]))
        return committed.commit

    def by_the_model(self, name: str, message: str) -> str:
        """The model's own `git commit`: nothing announces it."""
        self.write(name, f"{name}\n")
        self.git("add", name)
        self.git("-c", "user.name=Model", "-c", "user.email=model@example.invalid", "commit", "-q", "-m", message)
        return self.head()

    def run_folder(self, invocation: dict | None = None, events: bool = True) -> Path:
        base = {"case": "x", "host": "claude", "model": "m", "follow_on": None, "seeded": None}
        if invocation is not False:
            (self.out / "invocation.json").write_text(json.dumps({**base, **(invocation or {})}))
        if events:
            (self.out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in claude_events(self.replies)))
        return self.out

    def counted(self, run_dir: Path | None = None, **kwargs):
        out = self.run_folder(**kwargs)
        tools = metrics.ToolLog()
        for number, event in metrics.events(out / "events.jsonl"):
            tools.feed(event, None, number)
        return counters.commits(out, run_dir, tools)


class ClassifyTest(GitCase):
    """A history in the order of a real run, every ShipLoop-owned commit made by ShipLoop's own function."""

    def setUp(self):
        super().setUp()
        self.baseline = shiploop_workspace.bootstrap_empty(self.work)
        self.state = {"repo": str(self.work), "prompt": "Build a small thing", "run_id": "nav-abcdef123456"}
        self.write("docs/shiploop/README.md", "# Knowledge home\n")
        knowledge_home.commit(self.state, "intake")                                   # subject-only knowledge commit
        self.by_shiploop("spec.md", MESSAGES["improve-six-labels"], "improve")      # an Improve commit with every label
        self.by_shiploop("plan.md", MESSAGES["improve-free-prose"], "improve")      # an Improve commit with no label at all
        self.by_shiploop("lib.js", MESSAGES["item"], "W1")                           # the verify stage's item commit
        self.by_the_model("README.md", MESSAGES["raw-readme"])                       # the model's own commits
        self.by_the_model("notes.md", MESSAGES["raw-with-key-learnings"])
        self.by_the_model("check.md", MESSAGES["improve-six-labels"])                # an Improve child that bypassed improve-commit
        self.by_shiploop("late.md", MESSAGES["leftovers"])                           # leftovers, announced by nothing
        self.write("docs/shiploop/environment.md", "# Environment\n\nnpm test\n")
        lessons = {"learned": "- the first lesson", "considerations": "- a decision", "open_next": "- a follow-up"}
        verified = dict(self.state, history=[{"stage": "release-verify", "outcome": "done", "action": "A-rv"}],
                        accepted={"A-rv": {"outcome": "done", "lessons": lessons}})
        knowledge_home.commit(verified, "release-verify")                            # the lessons commit, with a body

    def test_each_commit_lands_in_the_class_of_who_made_it_and_the_classes_sum_to_the_commits_counted(self):
        block, unmeasured = self.counted()
        self.assertEqual(unmeasured, {})
        self.assertEqual(block["improve"], {"n": 2, "with_lessons": 1, "cited": 0, "cited_earlier_run": 0})
        self.assertEqual(block["script"], {"n": 5, "with_lessons": 1})   # baseline, intake knowledge, item, leftovers, learnings
        self.assertEqual(block["other"], {"n": 3, "with_lessons": 2})
        self.assertEqual(block["counted"], 10)
        self.assertEqual(block["counted"], block["improve"]["n"] + block["script"]["n"] + block["other"]["n"])
        self.assertIsNone(block["start_head"], "a fresh run counts from its first commit")

    def test_the_commit_count_is_the_repositorys_own(self):
        self.assertEqual(len(self.git("rev-list", "--all").split()), 10)

    def test_an_improve_commit_is_the_one_improve_commit_named_not_a_message_with_the_improve_labels(self):
        block, _ = self.counted()
        # The model's commit with all six labels is `other`; the Improve commit with none of them is `improve`.
        self.assertEqual(block["other"]["n"], 3)
        self.assertEqual(block["improve"]["n"], 2)

    def test_a_model_commit_that_borrows_the_knowledge_subject_is_not_a_script_commit(self):
        self.by_the_model("late2.md", "docs(shiploop): record release plan and fix contradictory rollback wording\n")
        block, _ = self.counted()
        self.assertEqual((block["script"]["n"], block["other"]["n"]), (5, 4))

    def test_a_saved_runs_retire_commit_is_still_a_script_commit_by_the_harnesss_own_matcher(self):
        """Consumer contract 4c removed the handoff retire; saved runs still hold its commits, so the harness keeps the
        matcher (counters.RETIRE_SUBJECT) and classifies them as ShipLoop's, not as a knowledge record (X16: the literal
        saved subject)."""
        feature = "docs/shiploop/features/build-a-small-single-player-battleship-450445"
        self.write(feature + "/spec.md", "Adds: R-1.\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "docs(shiploop): record build-a-small-single-player-battleship-450445 knowledge after spec")
        before, _ = self.counted()
        (self.work / feature / "spec.md").unlink()
        self.git("add", "-A")
        subject = ("docs(shiploop): retire build-a-small-single-player-battleship-450445 spec: checked its requirement IDs "
                   "against the living spec")
        self.git("commit", "-qm", subject)
        retired = self.git("rev-parse", "HEAD").strip()
        found, _ = self.historied()
        row = next(row for row in found["commits"] if row["id"] == retired)
        self.assertEqual((row["kind"], row["knowledge"], row["subject"]), ("script", False, subject))
        after, _ = self.counted()
        self.assertEqual((after["script"]["n"], after["script"]["with_lessons"]), (before["script"]["n"] + 1, before["script"]["with_lessons"]))
        self.assertEqual((after["other"]["n"], after["improve"]["n"]), (before["other"]["n"], before["improve"]["n"]))

    def test_a_model_commit_with_a_lookalike_retire_subject_is_not_a_script_commit(self):
        before, _ = self.counted()
        for number, subject in enumerate(("docs(shiploop): retire two words spec: checked its requirement IDs against the living spec",
                                          "docs(shiploop): retire x spec: it is gone",
                                          "docs: retire x spec: checked its requirement IDs against the living spec")):
            self.by_the_model(f"look{number}.md", subject + "\n")
        after, _ = self.counted()
        self.assertEqual((after["script"]["n"], after["other"]["n"]), (before["script"]["n"], before["other"]["n"] + 3))

    def test_a_work_item_commit_whose_reply_was_not_recorded_is_still_the_scripts_by_its_subject(self):
        # The verify stage's reply can be cut by the model's pipe. state.md names the run's work item ids, and the commit's
        # subject is `feat: <id> <title>`; a model commit that starts the same way but names no work item is not the script's.
        self.by_shiploop("w2.js", "feat: W2 Another item\n\nWhat it did.\n")
        self.by_the_model("m.js", "feat: add a thing\n")
        run_dir = self.out / "run"
        run_dir.mkdir()
        (run_dir / "state.md").write_text('# ShipLoop navigator state\n\n```shiploop-state\n{"work_items": [{"id": "W1", '
                                          '"title": "t"}, {"id": "W2", "title": "u"}]}\n```\n')
        block, _ = self.counted(run_dir=run_dir)
        self.assertEqual((block["script"]["n"], block["other"]["n"]), (6, 4))
        without, _ = self.counted()
        self.assertEqual((without["script"]["n"], without["other"]["n"]), (5, 5), "with no run directory only replies name an item")

    def test_an_announced_sha_that_is_not_a_commit_of_this_run_names_nothing(self):
        self.replies.append(IMPROVE_LINE.format(sha="0123456789ab", files="x"))
        block, _ = self.counted()
        self.assertEqual((block["improve"]["n"], block["counted"]), (2, 10))

    def historied(self):
        out = self.run_folder()
        tools = metrics.ToolLog()
        for number, event in metrics.events(out / "events.jsonl"):
            tools.feed(event, None, number)
        return counters.history(out, None, tools)

    def test_the_history_is_the_commits_the_block_counts_each_with_the_class_it_was_counted_in(self):
        block, _ = self.counted()
        found, unmeasured = self.historied()
        self.assertEqual(unmeasured, {})
        rows = found["commits"]
        self.assertEqual(len(rows), block["counted"])
        for kind in ("improve", "script", "other"):
            self.assertEqual(sum(row["kind"] == kind for row in rows), block[kind]["n"], kind)
            self.assertEqual(sum(row["kind"] == kind and bool(commit_lessons.lessons(row["message"])) for row in rows),
                             block[kind]["with_lessons"], kind)
        self.assertIsNone(found["start"], "a fresh run counts from its first commit")

    def test_a_row_names_its_commit_author_subject_and_message_and_whether_the_knowledge_home_made_it(self):
        rows = {row["id"]: row for row in self.historied()[0]["commits"]}
        self.assertEqual(set(rows), set(self.git("rev-list", "--all").split()), "every commit, by its full id")
        models = [row for row in rows.values() if row["kind"] == "other"]
        self.assertEqual([row["author"] for row in models], ["Model"] * 3)
        self.assertTrue(all(row["message"].startswith(row["subject"]) for row in rows.values()))
        self.assertTrue(all(row["author"] and row["author"] != "Model" for row in rows.values() if row["kind"] != "other"),
                        "ShipLoop's own commits carry its identity, not the model's")
        knowledge = [row for row in rows.values() if row["knowledge"]]
        self.assertEqual(len(knowledge), 2, "the intake commit and the learnings commit")
        self.assertTrue(all(row["kind"] == "script" and counters.KNOWLEDGE_SUBJECT.match(row["subject"]) for row in knowledge))
        self.assertEqual(sum(bool(commit_lessons.lessons(row["message"])) for row in knowledge), 1)

    def test_an_unreadable_history_has_the_reason_the_commits_block_has(self):
        import shutil
        shutil.rmtree(self.work)
        out = self.run_folder()
        found, unmeasured = counters.history(out, None, metrics.ToolLog())
        self.assertIsNone(found)
        self.assertEqual((counters.commits(out, None, metrics.ToolLog())), (None, unmeasured))
        self.assertIn("work directory", unmeasured["commits"])

    def test_the_lessons_of_the_learnings_commit_come_from_its_learned_section(self):
        body = self.git("log", "-1", "--format=%B")
        self.assertIn("Learned\n- the first lesson", body)
        self.assertEqual(commit_lessons.lessons(body), "- the first lesson")


class ShipLoopOwnedSubjectsTest(unittest.TestCase):
    """The subjects counters.py matches are ShipLoop's, read from ShipLoop's own source."""

    def test_the_leftovers_subject_and_the_two_announcements_are_in_shiploops_source(self):
        scripts = ROOT / "skills" / "shiploop" / "scripts"
        workspace = (scripts / "shiploop_workspace.py").read_text()
        self.assertIn("chore(shiploop): commit files written after the last ", workspace)
        self.assertIn("work item, before the return", workspace)
        navigator = (scripts / "shiploop_navigator.py").read_text()
        self.assertIn("\"Committed this review's changes as \" + head[:12]", navigator)
        self.assertIn("\"'s changes (its declared paths and documentation) as \"", navigator)
        self.assertIn("\"ShipLoop committed \"", navigator)
        self.assertTrue(counters.LEFTOVERS_SUBJECT.startswith("chore(shiploop): commit files written after the last work item"))

    def test_the_work_item_subject_counters_matches_is_the_one_the_verify_stage_writes(self):
        # The verify stage's reply names the commit, but the model's pipe can cut that reply, and then only the subject tells the
        # script's commit from the model's. The message is built in shiploop_navigator._item_commit: call it with the commit itself
        # replaced and read the message it hands over, so a reworded subject turns the matched work item commits into `other` here
        # and not silently in a run.
        before = {"history": []}
        after = {"history": [{"stage": "verify", "outcome": "done", "workitem": "W1", "summary": "What it did."}],
                 "work_items": [{"id": "W1", "title": "Add the grid"}]}
        with mock.patch.object(shiploop_item_scope, "commit_item", return_value=("", [], [])) as made:
            shiploop_navigator._item_commit(Path("."), before, after)
        self.assertEqual(made.call_count, 1, "the verify row of the history makes one item commit")
        message = made.call_args.args[3]
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "state.md").write_text('# ShipLoop navigator state\n\n```shiploop-state\n{"work_items": [{"id": "W1", '
                                                '"title": "Add the grid"}]}\n```\n')
            prefixes = counters._item_prefixes(Path(tmp))
        self.assertEqual(prefixes, ("feat: W1 ",))
        self.assertTrue(message.startswith(prefixes), f"counters matches {prefixes} and ShipLoop wrote {message.splitlines()[0]!r}")

    def test_the_harness_matches_the_retire_subject_with_its_own_pattern_since_knowledge_home_dropped_it(self):
        self.assertFalse(hasattr(knowledge_home, "is_retire_subject"))
        self.assertNotIn("retire", counters.KNOWLEDGE_SUBJECT.pattern)
        self.assertTrue(counters.RETIRE_SUBJECT.fullmatch("docs(shiploop): retire build-a-small-single-player-battleship-450445 "
                                                          "spec: checked its requirement IDs against the living spec"))
        for other in ("docs(shiploop): retire two words spec: checked its requirement IDs against the living spec",
                      "docs(shiploop): retire x spec: it is gone"):
            self.assertIsNone(counters.RETIRE_SUBJECT.fullmatch(other))
        self.assertFalse(hasattr(counters, "knowledge_home"))

    def test_the_chain_merge_prefix_is_the_one_the_chain_writes(self):
        self.assertIn(f'_PREPARED_MERGE_PREFIX = "{counters.CHAIN_PREFIX}"',
                      (ROOT / "skills" / "shiploop" / "scripts" / "shiploop_chain_git.py").read_text())


class ReaderCase(GitCase):
    """One message at a time in a real repository: was it counted, by the number the `commits` block reports. The model's own commit
    is `other` unless its subject is one only ShipLoop writes, so the three classes are summed."""

    def setUp(self):
        super().setUp()
        shiploop_workspace.bootstrap_empty(self.work)
        self.replies.append("ShipLoop printed nothing about a commit")   # an empty event stream cannot tell the Improve commits
        self.made = 0
        self.known = self.with_lessons()   # the commits already counted: the empty baseline has no lesson

    def with_lessons(self) -> int:
        block = self.counted()[0]
        return sum(block[kind]["with_lessons"] for kind in ("improve", "script", "other"))

    def counts(self, message: str) -> bool:
        self.made += 1
        self.by_the_model(f"m{self.made}.md", message)
        now, before = self.with_lessons(), self.known
        self.known = now
        return now - before == 1


class LessonsReaderTest(ReaderCase):
    """`with_lessons` is the number of commits in which ShipLoop's own reader (skills/shiploop/scripts/shiploop_lessons.py, the reader the
    improve-commit gate uses) finds a lessons section: the harness has no reader of its own, so "has lessons" means one thing
    (SPEC S-12). Each test commits the message and reads the count the block reports."""

    def test_the_harness_counts_exactly_the_shapes_the_gate_reads(self):
        expected = json.loads((CONTRACT / "expected.json").read_text())
        self.assertEqual(sorted(expected), sorted(path.name for path in CONTRACT.glob("*.md") if path.name != "README.md"))
        for name, want in expected.items():
            with self.subTest(shape=name):
                self.assertEqual(self.counts((CONTRACT / name).read_text()), bool(want["lessons"]))

    def test_every_label_the_gate_knows_counts_with_a_colon_and_as_a_heading(self):
        for label in commit_lessons.LESSON_LABELS:
            for text in (f"S\n\n{label}: a lesson\n", f"S\n\n{label.lower()}: a lesson\n", f"S\n\n## {label}\n- a lesson\n"):
                with self.subTest(text=text):
                    self.assertTrue(self.counts(text))

    def test_a_label_that_is_bold_bulleted_or_alone_on_its_line_counts(self):
        for text in ("S\n\n**Key learnings:** a lesson\n", "S\n\n- Key learnings: a lesson\n", "S\n\n* __Lessons__: a lesson\n",
                     "S\n\n> Key learnings: a lesson\n", "S\n\nLessons:\n\nthe label alone, a blank line, the text\n",
                     "S\n\n**Key learnings**\nthe text under a bold label\n"):
            with self.subTest(text=text):
                self.assertTrue(self.counts(text))

    def test_real_messages(self):
        expected = {"improve-six-labels": True, "improve-free-prose": False, "knowledge-with-learned": True,
                    "knowledge-subject-only": False, "item": False, "raw-readme": False, "raw-with-key-learnings": True,
                    "leftovers": False, "baseline": False}
        self.assertEqual(set(expected), set(MESSAGES))
        for name, has in expected.items():
            with self.subTest(name=name):
                self.assertEqual(self.counts(MESSAGES[name]), has)

    def test_a_lesson_that_says_none_counts_because_the_gate_counts_it(self):
        # The script cannot judge a lesson's truth, so `Key learnings: none` is a section (shiploop_lessons: measured, not refused).
        for text in ("S\n\nKey learnings: none\n", "S\n\nKey learnings: None.\n", "S\n\n## Key learnings\n\nnone\n"):
            with self.subTest(text=text):
                self.assertTrue(self.counts(text))

    def test_a_section_with_no_letter_or_digit_in_it_or_no_section_at_all_does_not_count(self):
        for text in ("S\n\nKey learnings:\nRemaining work: x\n", "S\n\nKey learnings:   \n", "S\n\nLearned-from: abcdef1 reused\n",
                     "S\n\nWe Learned: it\n", "S\n", "S. Review: a. Key learnings: all in one paragraph.\n",
                     "S\n\n## Key learnings\n\nCo-Authored-By: T <t@example.invalid>\n",   # a heading that holds only the trailer
                     "S\n\nKey learnings: -\n", "S\n\nKey learnings: ...\n",              # punctuation is not a lesson
                     "S\n\nKey learnings:\n## Next\ntext under another heading\n"):       # the heading ends the empty section
            with self.subTest(text=text):
                self.assertFalse(self.counts(text))

    def test_the_count_follows_the_shared_reader_and_not_a_copy_of_it(self):
        self.assertTrue(self.counts("S\n\nKey learnings: a lesson\n"))
        with mock.patch.object(commit_lessons, "lessons", return_value=""):
            self.assertEqual(self.with_lessons(), 0, "the block asks the shared reader, whatever the message says")
        with mock.patch.object(commit_lessons, "lessons", return_value="x"):
            self.assertEqual(self.with_lessons(), self.counted()[0]["counted"], "every commit has a lesson when the reader says so")

    def test_the_harness_has_no_reader_of_its_own(self):
        for name in ("lessons", "LESSON_LABEL", "LEARNED_FROM", "SECTION_END", "LEARNED", "KEY_LEARNINGS"):
            self.assertFalse(hasattr(counters, name), name)


class CitationTest(GitCase):
    """`Learned-from:` lines, with the earlier run's commits behind start_head."""

    def setUp(self):
        super().setUp()
        shiploop_workspace.bootstrap_empty(self.work)
        self.replies.append("ShipLoop printed nothing about a commit")   # an empty event stream cannot tell the Improve commits
        self.earlier = self.by_the_model("old.md", "An earlier run's commit\n\nKey learnings: the old lesson\n")
        self.start = self.by_the_model("old2.md", "An earlier run's other commit\n")
        self.cited = 0   # what `cites` has counted so far

    def improve(self, name: str, cite: str | None, text: str = "A change\n\nKey learnings: something\n") -> str:
        message = text + (f"{cite}\n" if cite is not None else "")
        return self.by_shiploop(name, message, "improve")

    def test_a_citation_that_resolves_counts_and_one_that_predates_the_run_counts_as_earlier(self):
        mine = self.improve("a1.md", f"Learned-from: {self.earlier} its test pattern")   # an earlier run's commit
        self.improve("a2.md", f"Learned-from: {mine} the guard I added before")           # this run's commit
        self.improve("a3.md", f"Learned-from: {self.earlier[:7]} abbreviated")             # an abbreviated id still resolves
        self.improve("a4.md", "Learned-from: deadbeefdeadbeef a commit nobody made")       # does not resolve
        self.improve("a5.md", "Learned-from: none cited")                                  # not an id
        self.improve("a6.md", f"We reused {self.earlier} here, in prose")                  # not a citation line
        self.improve("a7.md", f"We follow Learned-from: {self.earlier} as the notes say")  # the label is not at a line's start
        block, unmeasured = self.counted(invocation={"follow_on": {"start_head": self.start}})
        self.assertEqual(unmeasured, {})
        self.assertEqual(block["start_head"], self.start)
        self.assertEqual(block["improve"], {"n": 7, "with_lessons": 7, "cited": 3, "cited_earlier_run": 2})
        self.assertEqual(block["counted"], 7, "the two commits before start_head are not this run's")

    def cites(self, cite: str) -> bool:
        """Whether an Improve commit whose message ends with the line ``cite`` raised `cited` by one."""
        self.improve(f"d{len(self.replies)}.md", cite)
        now, before = self.counted()[0]["improve"]["cited"], self.cited
        self.cited = now
        return now - before == 1

    def test_a_citation_is_read_the_way_the_gate_reads_it(self):
        sha = self.earlier
        for cite in (f"Learned-from: `{sha[:8]}` its test pattern", f"Learned-from: {sha[:8]}: its test pattern",
                     f"Learned-from: commit {sha[:8]}, the prefix", f"Learned-from: [{sha[:8]}] bracketed.", f"Learned-from: {sha[:8].upper()}",
                     f"- Learned-from: {sha[:8]} bulleted", f"**Learned-from:** {sha[:8]} bold label", f"learned-from: {sha[:8]} lower case",
                     f"Learned-from: \"{sha}\" quoted, a full id"):
            with self.subTest(cite=cite):
                self.assertTrue(self.cites(cite))

    def test_a_token_that_is_not_a_commit_id_cites_nothing_even_when_git_would_resolve_it(self):
        # The gate refuses everything but 7 to 64 hexadecimal digits; git alone would also resolve a branch, HEAD and a revision
        # expression, so the harness checks the shape first or it would count a name the gate refuses.
        self.git("branch", "notes", self.earlier)
        for cite in ("Learned-from: notes the branch that points at it", "Learned-from: HEAD the last commit", "Learned-from: HEAD~1 its parent",
                     "Learned-from: none cited", f"Learned-from: {self.earlier[:6]} six digits are too few", "Learned-from:",
                     "Learned-from: 0000000 hex digits no commit has", "Learned from: " + self.earlier[:8] + " a space for the hyphen",
                     f"    Learned-from: {self.earlier[:8]} indented, a quotation"):
            with self.subTest(cite=cite):
                self.assertFalse(self.cites(cite))

    def test_the_shape_of_an_id_is_the_gates(self):
        self.assertEqual(counters.COMMIT_ID.pattern, shiploop_git._COMMIT_ID.pattern)

    def test_cited_follows_the_shared_readers_citations_and_not_a_copy_of_them(self):
        self.improve("e1.md", f"Learned-from: {self.earlier} its pattern")
        self.assertEqual(self.counted()[0]["improve"]["cited"], 1)
        with mock.patch.object(commit_lessons, "citations", return_value=[]):
            self.assertEqual(self.counted()[0]["improve"]["cited"], 0)

    def test_a_fresh_run_has_no_earlier_commit_so_none_is_cited_from_before_it(self):
        first = self.improve("b1.md", None)
        self.improve("b2.md", f"Learned-from: {first} the first guard")
        block, _ = self.counted()   # no follow_on: the whole history is the run's
        self.assertEqual(block["improve"]["cited"], 1)
        self.assertEqual(block["improve"]["cited_earlier_run"], 0, "a measured zero: nothing predates a fresh run")
        self.assertEqual(block["counted"], 5, "the baseline, the two earlier commits and the two of this run")

    def test_a_seeded_run_counts_from_the_head_it_was_seeded_at(self):
        self.improve("c1.md", None)
        block, _ = self.counted(invocation={"seeded": {"start_head": self.start}})
        self.assertEqual((block["counted"], block["start_head"]), (1, self.start))


class UnmeasuredTest(GitCase):
    """The whole block is null, with one reason, where the run's repository, starting head or events cannot be read."""

    def check(self, reason_part: str, **kwargs):
        block, unmeasured = self.counted(**kwargs)
        self.assertIsNone(block)
        self.assertEqual(list(unmeasured), ["commits"])
        self.assertIn(reason_part, unmeasured["commits"])

    def test_no_work_directory(self):
        import shutil
        shutil.rmtree(self.work)
        self.check("work directory")

    def test_a_work_directory_that_is_not_a_repository(self):
        self.write("a.txt", "x")
        self.check("not a Git repository")

    def test_no_invocation_record(self):
        shiploop_workspace.bootstrap_empty(self.work)
        self.check("invocation.json", invocation=False)

    def test_a_follow_on_record_that_names_no_starting_head(self):
        shiploop_workspace.bootstrap_empty(self.work)
        self.check("starting head", invocation={"follow_on": {"prior": "x", "start_head": None}})

    def test_a_starting_head_the_repository_does_not_hold(self):
        shiploop_workspace.bootstrap_empty(self.work)
        self.check("not a commit", invocation={"follow_on": {"start_head": "0" * 40}})

    def test_no_event_stream_means_the_improve_commits_cannot_be_told(self):
        shiploop_workspace.bootstrap_empty(self.work)
        self.check("events.jsonl", events=False)

    def test_an_empty_repository_is_a_measured_zero(self):
        subprocess.run(["git", "-C", str(self.work), "init", "-q"], check=True)
        self.replies.append("ShipLoop did nothing yet")
        block, unmeasured = self.counted()
        self.assertEqual(unmeasured, {})
        self.assertEqual(block["counted"], 0)


# ------------------------------------------------------------------------------------------------------ through run.main


def load_harness_tests():
    spec = importlib.util.spec_from_file_location("e2e_harness_tests_for_counters", ROOT / "test" / "shiploop-e2e.test.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


HARNESS = load_harness_tests()
FOUR_KEYS = {"packets", "packets_unmeasured", "commits", "commits_unmeasured"}


class CountersThroughMainTest(HARNESS.PrintedCase):
    """run._main builds the blocks once, writes them to metrics.json only and never lets them change a verdict."""

    def setUp(self):
        super().setUp()
        HARNESS.isolate_git(self)

    def written(self, host="grok", mode="done", *extra):
        code, result, printed = self.invoke_printed(host, mode, *extra)
        out = Path(result["output"])
        return code, result, printed, json.loads((out / "metrics.json").read_text()), out

    def test_metrics_json_carries_the_four_keys_and_neither_result_json_nor_the_baseline_row_does(self):
        for host in ("claude", "grok", "codex"):
            with self.subTest(host=host):
                code, result, printed, written, out = self.written(host)
                self.assertEqual(code, 0, result)
                self.assertTrue(FOUR_KEYS <= set(written))
                self.assertFalse(FOUR_KEYS & set(result["metrics"]), "result.json keeps its explicit subset")
                self.assertFalse(FOUR_KEYS & set(json.loads((out / "result.json").read_text())))
                self.assertFalse(FOUR_KEYS & set(self.last_row()))

    def test_the_wiring_hands_the_builder_the_output_folder_the_run_directory_and_the_tool_log_of_the_run(self):
        # A run_main that passed no ToolLog, or no run directory, would still produce the four keys.
        seen = []
        real = counters.safe_build

        def spy(out, run_dir, tools):
            seen.append((out, run_dir, tools))
            return real(out, run_dir, tools)

        for host in ("claude", "grok", "codex"):
            seen.clear()
            with self.subTest(host=host), mock.patch.object(counters, "safe_build", side_effect=spy):
                _code, result, _printed, _written, out = self.written(host)
                (got_out, got_run_dir, got_tools), = seen
                self.assertEqual(Path(got_out), out)
                self.assertEqual(str(got_run_dir), result["shiploop"]["run_dir"])
                self.assertGreater(len(got_tools.sequence), 0, "the log the run's events filled")

    def test_each_block_is_a_value_or_null_with_the_reason_in_its_sibling_key(self):
        for host in ("claude", "grok", "codex"):
            with self.subTest(host=host):
                _code, _result, _printed, written, _out = self.written(host)
                for block, why in (("packets", "packets_unmeasured"), ("commits", "commits_unmeasured")):
                    self.assertIsInstance(written[why], dict)
                    if written[block] is None:
                        self.assertEqual(list(written[why]), [block], "a null block says why, once")
                        self.assertTrue(written[why][block])

    def test_the_commits_of_the_fake_hosts_run_are_read_from_the_work_repository_it_made(self):
        # The fake host runs real git in work/; whatever it committed is counted, and the classes sum to the commits counted.
        _code, _result, _printed, written, out = self.written("grok")
        block = written["commits"]
        self.assertIsNotNone(block, written["commits_unmeasured"])
        listed = subprocess.run(["git", "-C", str(out / "work"), "rev-list", "--all"], capture_output=True, text=True)
        self.assertEqual(block["counted"], len(listed.stdout.split()))
        self.assertEqual(block["counted"], block["improve"]["n"] + block["script"]["n"] + block["other"]["n"])

    def test_no_existing_metrics_key_changes_when_the_blocks_are_added(self):
        _code, result, _printed, written, out = self.written("grok")
        ledger = Path(result["shiploop"]["run_dir"]) if result["shiploop"].get("run_dir") else None
        collected = metrics.collect(out, ledger)
        for key, value in collected.items():
            self.assertIn(key, written, key)
            if key in ("turns", "cost_usd", "model_calls", "shiploop_failures", "model_glue", "improve_children", "sessions",
                       "unmeasured", "tokens", "compactions"):
                self.assertEqual(written[key], value, key)
        self.assertEqual(set(written) - set(collected), FOUR_KEYS | {"fidelity"})
        self.assertFalse(FOUR_KEYS & set(collected), "collect itself is unchanged: the blocks are built beside it")

    def test_a_builder_failure_is_recorded_and_changes_neither_the_verdict_nor_the_exit_code_nor_the_baseline_row(self):
        _code, clean_result, _printed, _written, _out = self.written("grok")
        clean_row = self.last_row()
        self.baselines.unlink()
        with mock.patch.object(counters, "build", side_effect=RuntimeError("builder broke")):
            code, result, _printed, written, _out = self.written("grok")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["pass"], clean_result["pass"])
        reason = "failed: RuntimeError: builder broke"
        self.assertEqual((written["packets"], written["commits"]), (None, None))
        self.assertEqual((written["packets_unmeasured"], written["commits_unmeasured"]), ({"packets": reason}, {"commits": reason}))
        row = self.last_row()
        for key in ("turns", "cost_usd", "sessions", "model_glue", "stages", "unmeasured"):
            self.assertEqual(row[key], clean_row[key], key)

    def test_grade_only_adds_the_blocks_to_a_run_that_had_none(self):
        _code, _result, _printed, _written, out = self.written("grok")
        metrics_file = out / "metrics.json"
        old = json.loads(metrics_file.read_text())
        for key in FOUR_KEYS:
            del old[key]
        metrics_file.write_text(json.dumps(old))
        with contextlib.redirect_stdout(io.StringIO()):
            HARNESS.run.main(["--resume-run", str(out), "--grade-only", "--baseline", str(self.baselines),
                              "--plugin-dir", str(self.plugin)])
        self.assertTrue(FOUR_KEYS <= set(json.loads(metrics_file.read_text())))


# ------------------------------------------------------------------------------------------------------------- the regrade

EVIDENCE = ROOT / "docs" / "experiments" / "commit-baseline-20261010"


def load_regrade():
    spec = importlib.util.spec_from_file_location("commit_baseline_regrade", EVIDENCE / "regrade.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RegradeTest(unittest.TestCase):
    """docs/experiments/commit-baseline-20261010: the script that regrades the saved runs and the evidence file it wrote."""

    @classmethod
    def setUpClass(cls):
        cls.regrade = load_regrade()
        cls.evidence = json.loads((EVIDENCE / "baseline.json").read_text())

    def row(self, host="claude", model="m", mixed=False, entries=None, commits=None, **more):
        entries = [] if entries is None else entries
        return {"run": "x", "hosts": [host] if not mixed else ["grok", "claude"], "mixed_host": mixed, "host": host, "model": model,
                "effort": None, "entries": entries, "commits": commits,
                "packets": {"n": len(entries), "head_measured": sum(e["head_bytes"] is not None for e in entries)},
                "knowledge_commits": None, **more}

    def test_figures_are_n_median_min_max_and_none_for_nothing_measured(self):
        self.assertIsNone(self.regrade.figures([]))
        self.assertEqual(self.regrade.figures([3, 1, 10, 4]), {"n": 4, "median": 3.5, "min": 1, "max": 10})

    def test_figures_are_the_harnesss_own_stats_with_none_for_nothing_measured(self):
        for values in ([3, 1, 10, 4], [5, 7, 9], [8], [2, 3]):
            stats = self.regrade.run._stats(values, 1)
            self.assertEqual(self.regrade.figures(values), {"n": stats["n"], "median": stats["median"], "min": stats["min"],
                                                            "max": stats["max"]}, values)
        self.assertEqual(self.regrade.figures([2, 3])["median"], 2.5, "a median between two sizes keeps its half byte")

    def test_knowledge_commits_are_read_from_the_history_the_commits_block_is_counted_from(self):
        found = {"commits": [
            {"kind": "script", "knowledge": True, "message": "docs(shiploop): record f knowledge at intake\n"},
            {"kind": "script", "knowledge": True, "message": "docs(shiploop): record f knowledge after release-verify\n\nLearned\n- a lesson\n"},
            {"kind": "script", "knowledge": False, "message": "Empty baseline for the first ShipLoop run\n"},
            {"kind": "other", "knowledge": False, "message": "docs(shiploop): record release plan and fix wording\n"}]}
        self.assertEqual(self.regrade.knowledge_commits(found), {"n": 2, "with_lessons": 1})
        self.assertIsNone(self.regrade.knowledge_commits(None), "a history that could not be read is unknown, not zero")

    def test_a_host_is_labelled_the_one_way_for_the_summary_and_the_tallies(self):
        self.assertEqual(self.regrade.host_label(self.row("grok")), "grok")
        self.assertEqual(self.regrade.host_label(self.row(mixed=True)), "mixed host (grok then claude)")

    def test_a_mixed_host_run_is_summarised_alone_and_an_improve_packet_is_a_row_of_its_own(self):
        entries = [{"action": "nav-a", "stage": "spec", "file_bytes": 100, "head_bytes": 40},
                   {"action": "nav-a-improve", "stage": "spec", "file_bytes": 200, "head_bytes": None}]
        rows = [self.row(entries=entries), self.row("grok", entries=entries), self.row(mixed=True, entries=entries),
                self.row(not_regraded="live", entries=None)]
        summary = self.regrade.summary(rows)
        self.assertEqual(sorted(summary["by_host"]), ["claude", "grok", "mixed host (grok then claude)"])
        self.assertEqual(summary["by_host"]["claude"]["runs"], 1, "the mixed-host run is not Claude's, the unregraded one is no run")
        stages = summary["by_cell"]["claude / m / no effort"]["by_stage"]
        self.assertEqual(sorted(stages), ["spec", "spec [Improve packet]"])
        self.assertEqual(stages["spec"]["head_bytes"]["median"], 40)
        self.assertIsNone(stages["spec [Improve packet]"]["head_bytes"], "nothing measured is None, not 0")

    def test_a_run_whose_harness_is_alive_is_left_alone_and_says_so(self):
        import listeners
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "live"
            folder.mkdir()
            (folder / "invocation.json").write_text(json.dumps({"case": "x", "host": "claude", "model": "m"}))
            held = listeners.hold_case(folder)
            self.assertIsNotNone(held)
            try:
                row = self.regrade.regrade(folder, Path(tmp))
            finally:
                held.close()
        self.assertIn("harness is alive", row["not_regraded"])
        self.assertEqual((row["packets"], row["commits"]), (None, None))

    def test_the_committed_evidence_is_internally_consistent(self):
        evidence = self.evidence
        self.assertEqual(evidence["schema"], "shiploop-e2e-commit-baseline/v1")
        self.assertEqual(evidence["runs"], len(evidence["per_run"]))
        self.assertEqual({row["run"] for row in evidence["per_run"] if row.get("not_regraded")},
                         {item["run"] for item in evidence["not_regraded"]})
        regraded = [row for row in evidence["per_run"] if not row.get("not_regraded")]
        self.assertGreaterEqual(len(regraded), 38)
        for row in regraded:
            commits = row["commits"]
            self.assertEqual(commits["counted"], commits["improve"]["n"] + commits["script"]["n"] + commits["other"]["n"], row["run"])
            for kind in ("improve", "script", "other"):
                self.assertLessEqual(commits[kind]["with_lessons"], commits[kind]["n"], row["run"])
            self.assertLessEqual(commits["improve"]["cited_earlier_run"], commits["improve"]["cited"])
            self.assertLessEqual(commits["improve"]["cited"], commits["improve"]["n"])
            self.assertLessEqual(row["packets"]["head_measured"], row["packets"]["n"], row["run"])
            self.assertLessEqual(row["knowledge_commits"]["with_lessons"], row["knowledge_commits"]["n"], row["run"])
            self.assertLessEqual(row["knowledge_commits"]["n"], commits["script"]["n"], "the knowledge home's commits are script commits")
            self.assertLessEqual(row["knowledge_commits"]["with_lessons"], commits["script"]["with_lessons"], row["run"])
        for host, cell in evidence["summary"]["by_host"].items():
            members = [row for row in regraded if (row["host"] if not row["mixed_host"] else None) == host or
                       (row["mixed_host"] and host.startswith("mixed"))]
            self.assertEqual(cell["runs"], len(members), host)
            self.assertEqual(cell["commits_counted"], sum(row["commits"]["counted"] for row in members), host)
            self.assertEqual(cell["heads_measured"], sum(row["packets"]["head_measured"] for row in members), host)

    def test_the_evidence_copies_no_commit_message_and_no_packet_text(self):
        text = (EVIDENCE / "baseline.json").read_text()
        for needle in ("Key learnings:", "Review:", "ShipLoop navigator |", "Callback for this stage", "docs(shiploop): record"):
            self.assertNotIn(needle, text)

    def test_the_mutation_record_is_committed_with_its_result_and_has_no_survivor(self):
        record = json.loads((EVIDENCE / "mutants-result.json").read_text())
        self.assertEqual(record["survived"], [])
        self.assertEqual(record["not_applicable"], [])
        self.assertEqual(record["killed"], record["mutants"])
        self.assertGreaterEqual(record["mutants"], 30)


def load_tallies():
    spec = importlib.util.spec_from_file_location("commit_baseline_tallies", EVIDENCE / "tallies.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TalliesTest(unittest.TestCase):
    """docs/experiments/commit-baseline-20261010/tallies.py: the head replies and the `other` commits behind findings F2 and F6."""

    @classmethod
    def setUpClass(cls):
        cls.tallies = load_tallies()
        cls.evidence = json.loads((EVIDENCE / "tallies.json").read_text())
        cls.baseline = json.loads((EVIDENCE / "baseline.json").read_text())

    @staticmethod
    def head(name: str, call_tail: str) -> str:
        text = reply(name, call_tail)
        return text[text.index("ShipLoop navigator | "):]

    def test_head_replies_count_every_head_once_by_the_reason_it_is_not_whole_and_skip_a_model_reading_a_packet(self):
        whole = self.head("claude-wholes", "YKoYJ1")
        replies = [{"event": 1, "packet": False, "text": whole},
                   {"event": 2, "packet": False, "text": whole[:whole.index(STATUS_END)]},
                   {"event": 3, "packet": False, "text": self.head("claude-wholes", "EuCFqm")},
                   {"event": 4, "packet": False, "text": self.head("claude-columns", "9nLJam")},
                   {"event": 5, "packet": True, "text": whole},                      # the model reading the packet file
                   {"event": 6, "packet": False, "text": whole + "\n" + whole}]       # two heads in one reply
        tools = metrics.ToolLog()
        tools.replies = replies
        self.assertEqual(self.tallies.head_replies(tools), {
            "heads": 6, "whole": 3,
            "not_whole": {counters.NOT_WHOLE_BEFORE_CLOSING: 1, counters.NOT_WHOLE_IN_NARRATIVE: 1, counters.NOT_WHOLE_SHORTENED: 1}})

    def test_a_commit_is_confirmed_by_gits_own_line_for_its_abbreviated_id_only(self):
        sha = "0123456789abcdef0123456789abcdef01234567"
        for shown in ("[main 0123456] fix the thing", "[feature/x (root-commit) 0123456] first", "[main 0123456789ab] subject"):
            self.assertTrue(self.tallies.confirmed(shown + "\n", sha), shown)
        for shown in ("[main 7654321] another commit", "0123456 is mentioned, not confirmed", "[ok] 0123456"):
            self.assertFalse(self.tallies.confirmed(shown + "\n", sha), shown)

    def test_the_other_commits_are_tallied_by_author_and_by_gits_confirmation_and_no_other_class_is(self):
        rows = [{"kind": "other", "id": "a" * 40, "author": "Jim"}, {"kind": "other", "id": "b" * 40, "author": "Bot"},
                {"kind": "other", "id": "c" * 40, "author": "Jim"}, {"kind": "script", "id": "d" * 40, "author": "Bot"}]
        got = self.tallies.other_commits({"commits": rows}, "[main bbbbbbb] x\n")
        self.assertEqual(got, {"n": 3, "by_author": {"Bot": 1, "Jim": 2}, "git_confirmed": 1})
        self.assertEqual(self.tallies.other_commits(None, ""), None, "a history that could not be read is unknown")

    def test_the_committed_tallies_are_for_the_runs_the_baseline_regraded_and_add_up(self):
        evidence = self.evidence
        regraded = [row for row in self.baseline["per_run"] if not row.get("not_regraded")]
        self.assertEqual([row["run"] for row in evidence["per_run"]], [row["run"] for row in regraded])
        self.assertEqual(evidence["runs"], len(regraded))
        total = evidence["head_replies"]["all"]
        self.assertEqual(total["whole"] + sum(total["not_whole"].values()), total["heads"])
        self.assertEqual(sum(row["head_replies"]["heads"] for row in evidence["per_run"]), total["heads"])
        self.assertEqual(sum(cell["heads"] for cell in evidence["head_replies"]["by_host"].values()), total["heads"])
        other = evidence["other_commits"]["all"]
        self.assertEqual(other["n"], sum(other["by_author"].values()))
        self.assertEqual(other["n"], sum(row["commits"]["other"]["n"] for row in regraded), "the classification is the baseline's")
        self.assertLessEqual(other["git_confirmed"], other["n"])
        self.assertEqual(sum(row["other_commits"]["n"] for row in evidence["per_run"]), other["n"])
        for host, kinds in evidence["commits_by_author"]["by_host"].items():
            members = [row for row in regraded if self.tallies.regrade.host_label(row) == host]
            for kind in ("improve", "script", "other"):
                self.assertEqual(sum(kinds[kind].values()), sum(row["commits"][kind]["n"] for row in members), (host, kind))

    def test_in_claude_runs_no_commit_of_the_other_class_carries_an_identity_a_shiploop_commit_carries(self):
        # The claim that the 32 `other` commits of Claude runs are the model's: ShipLoop commits as its workspace identity there, and
        # the model's own `git commit` falls back to the Git identity of the machine. Grok and Codex runs configure one identity for both.
        by_host = self.evidence["commits_by_author"]["by_host"]
        for host in ("claude", "mixed host (grok then claude)"):
            kinds = by_host[host]
            shiploop = set(kinds["improve"]) | set(kinds["script"])
            self.assertTrue(kinds["other"], host)
            self.assertEqual(set(kinds["other"]) & shiploop, set(), host)

    def test_the_tallies_copy_no_commit_message_no_commit_id_and_no_packet_text(self):
        text = (EVIDENCE / "tallies.json").read_text()
        document = json.loads(text)
        document.pop("harness_head")  # the harness's own commit, a stamp of the code that made the file
        self.assertIsNone(re.search(r"\b[0-9a-f]{40}\b", json.dumps(document)), "no commit id of a run's repository")
        for needle in ("Key learnings:", "ShipLoop navigator |", "Callback for this stage", "docs(shiploop): record"):
            self.assertNotIn(needle, text)


def load_reader_change():
    spec = importlib.util.spec_from_file_location("commit_baseline_reader_change", EVIDENCE / "reader_change.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ReaderChangeTest(unittest.TestCase):
    """docs/experiments/commit-baseline-20261010/reader_change.py: what the change from the harness's own reader to ShipLoop's
    changed in the saved runs' counts, and the committed file that says so."""

    @classmethod
    def setUpClass(cls):
        cls.module = load_reader_change()

    @staticmethod
    def before():
        """A stand-in for the harness's old reader: one label, case-sensitive, to the end of the message."""
        return types.SimpleNamespace(lessons=lambda text: text.partition("Key learnings:")[2].strip(),
                                     LEARNED_FROM=re.compile(r"^Learned-from:[ \t]*(?P<id>[0-9a-fA-F]{7,64})\b", re.M))

    def test_exactly_none_is_the_word_in_any_case_with_punctuation_around_it_and_nothing_else(self):
        for text, want in (("none", True), ("None.", True), ("- NONE", True), ("none new beyond commit d171177", False), ("nothing", False),
                           ("", False), ("none\nnone", False), ("a none", False)):
            with self.subTest(text=text):
                self.assertEqual(self.module.exactly_none(text), want)

    def test_a_message_is_compared_by_both_readers_and_the_section_that_made_the_difference_is_named(self):
        got = self.module.compare("S\n\nKey learning: a lesson\n", self.before())
        self.assertEqual((got["old"], got["new"], got["labels"], got["none"], got["text_differs"]), (False, True, ["Key learning"], False, False))
        got = self.module.compare("S\n\nKey learning:\nRemaining work: x\n\nLessons: a real one\n", self.before())
        self.assertEqual(got["labels"], ["Lessons"], "a section with no text made no difference, so it is not named")
        got = self.module.compare("S\n\nKey learnings: none\n", self.before())
        self.assertEqual((got["old"], got["new"], got["none"]), (True, True, True))
        got = self.module.compare("S\n\nKey learnings: a\n\nprose after the section\n", self.before())
        self.assertEqual((got["old"], got["new"], got["text_differs"]), (True, True, True), "both count it, the text each read differs")
        got = self.module.compare("S\n\nKey learnings: -\n", self.before())
        self.assertEqual((got["old"], got["new"]), (True, False), "a commit the old reader counted and the shared one does not is `lost`")

    def test_the_tally_counts_gained_lost_and_the_commits_with_a_different_text_by_class(self):
        records = [{"kind": "improve", "host": "claude", "old": False, "new": True, "cited_old": 0, "cited_new": 0, "none": False,
                    "text_differs": False, "labels": ["Key learning"]},
                   {"kind": "improve", "host": "claude", "old": True, "new": True, "cited_old": 1, "cited_new": 0, "none": True,
                    "text_differs": True, "labels": ["Key learnings", "Key learnings"]},   # two sections, one commit
                   {"kind": "other", "host": "grok", "old": True, "new": False, "cited_old": 0, "cited_new": 0, "none": False,
                    "text_differs": False, "labels": []}]
        got = self.module.tally(records)
        self.assertEqual(got["improve"], {"n": 2, "old": {"with_lessons": 1, "cited": 1}, "shared": {"with_lessons": 2, "cited": 0},
                                          "gained": 1, "lost": 0, "text_differs": 1, "exactly_none": 1,
                                          "labels": {"Key learning": 1, "Key learnings": 1}})
        self.assertEqual(got["other"]["labels"], {}, "a commit the shared reader does not count names no label")
        self.assertEqual(got["other"]["lost"], 1)
        self.assertEqual(got["script"]["n"], 0)

    def test_the_committed_comparison_is_for_the_runs_and_commits_the_baseline_counts(self):
        evidence = json.loads((EVIDENCE / "reader-change.json").read_text())
        baseline = json.loads((EVIDENCE / "baseline.json").read_text())
        regraded = [row for row in baseline["per_run"] if not row.get("not_regraded")]
        self.assertEqual(evidence["runs"], len(regraded))
        for kind in ("improve", "script", "other"):
            cell = evidence["all"][kind]
            self.assertEqual(cell["n"], sum(row["commits"][kind]["n"] for row in regraded), kind)
            self.assertEqual(cell["shared"]["with_lessons"], sum(row["commits"][kind]["with_lessons"] for row in regraded), kind)
            self.assertEqual(cell["shared"]["cited"], sum(row["commits"].get(kind, {}).get("cited", 0) for row in regraded), kind)
            self.assertEqual(cell["shared"]["with_lessons"] - cell["old"]["with_lessons"], cell["gained"] - cell["lost"], kind)
        for host, kinds in evidence["by_host"].items():
            for kind, cell in kinds.items():
                self.assertEqual(cell["shared"]["with_lessons"] - cell["old"]["with_lessons"], cell["gained"] - cell["lost"], (host, kind))
        self.assertEqual(len(evidence["changed"]), sum(cell["gained"] + cell["lost"] for cell in evidence["all"].values()))
        for kind, cell in evidence["all"].items():
            self.assertGreaterEqual(sum(cell["labels"].values()), cell["shared"]["with_lessons"], "a counted commit names at least one label")
            self.assertTrue(set(cell["labels"]) <= set(commit_lessons.LESSON_LABELS), kind)

    def test_the_committed_comparison_copies_no_commit_message_and_no_commit_id(self):
        text = (EVIDENCE / "reader-change.json").read_text()
        document = json.loads(text)
        document.pop("harness_head")
        self.assertIsNone(re.search(r"\b[0-9a-f]{40}\b", json.dumps(document)), "no commit id of a run's repository")
        for needle in ("Key learnings:", "Review:", "ShipLoop navigator |", "docs(shiploop): record"):
            self.assertNotIn(needle, text)


if __name__ == "__main__":
    unittest.main()
