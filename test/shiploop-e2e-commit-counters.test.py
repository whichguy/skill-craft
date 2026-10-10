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
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import counters  # noqa: E402
import metrics  # noqa: E402
import shiploop_git  # noqa: E402
import shiploop_knowledge_home as knowledge_home  # noqa: E402
import shiploop_workspace  # noqa: E402

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
        source = (ROOT / "skills" / "shiploop" / "scripts" / "shiploop_navigator.py").read_text()
        for line in ('f"ShipLoop navigator | {stage} | revision {state[\'revision\']}"', 'f"Full packet: {path}"',
                     'f"Keepalive marker: {KEEPALIVE_MARKER} run='):
            self.assertIn(line, source)

    def test_the_kept_reply_filter_covers_every_pattern_counters_reads(self):
        for sample in ("ShipLoop navigator | discovery | revision 1", "Committed this review's changes as 7e11860aaaaa: a.py.",
                       "ShipLoop committed W1's declared changes as 65cd022aaaaa."):
            self.assertTrue(metrics.KEPT_REPLY.search(sample), sample)


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
        prints to announce it: 'improve' (improve-commit) or an item id (the integrate stage's commit)."""
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

    def counted(self, **kwargs):
        out = self.run_folder(**kwargs)
        tools = metrics.ToolLog()
        for number, event in metrics.events(out / "events.jsonl"):
            tools.feed(event, None, number)
        return counters.commits(out, tools)


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
        self.by_shiploop("lib.js", MESSAGES["item"], "W1")                           # the integrate stage's item commit
        self.by_the_model("README.md", MESSAGES["raw-readme"])                       # the model's own commits
        self.by_the_model("notes.md", MESSAGES["raw-with-key-learnings"])
        self.by_the_model("check.md", MESSAGES["improve-six-labels"])                # an Improve child that bypassed improve-commit
        self.by_shiploop("late.md", MESSAGES["leftovers"])                           # leftovers, announced by nothing
        feature = knowledge_home.feature_dir(self.state)
        self.write(feature + "/outcome.md", "## Learned\n- the first lesson\n\n## Key considerations\n- a decision\n\n"
                                            "## Open for the next run\n- a follow-up\n")
        knowledge_home.commit(self.state, "release-verify")                          # the learnings commit, with a body

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

    def test_an_announced_sha_that_is_not_a_commit_of_this_run_names_nothing(self):
        self.replies.append(IMPROVE_LINE.format(sha="0123456789ab", files="x"))
        block, _ = self.counted()
        self.assertEqual((block["improve"]["n"], block["counted"]), (2, 10))

    def test_the_lessons_of_the_learnings_commit_come_from_its_learned_section(self):
        body = self.git("log", "-1", "--format=%B")
        self.assertIn("Learned\n- the first lesson", body)
        self.assertEqual(counters.lessons(body), "- the first lesson")


class ShipLoopOwnedSubjectsTest(unittest.TestCase):
    """The subjects counters.py matches are ShipLoop's, read from ShipLoop's own source."""

    def test_the_leftovers_subject_and_the_two_announcements_are_in_shiploops_source(self):
        scripts = ROOT / "skills" / "shiploop" / "scripts"
        workspace = (scripts / "shiploop_workspace.py").read_text()
        self.assertIn("chore(shiploop): commit files written after the last ", workspace)
        self.assertIn("work item, before the return", workspace)
        navigator = (scripts / "shiploop_navigator.py").read_text()
        self.assertIn("\"Committed this review's changes as \" + head[:12]", navigator)
        self.assertIn("\"'s declared changes as \" + commit[:12]", navigator)
        self.assertIn("\"ShipLoop committed \"", navigator)
        self.assertTrue(counters.LEFTOVERS_SUBJECT.startswith("chore(shiploop): commit files written after the last work item"))

    def test_the_chain_merge_prefix_is_the_one_the_chain_writes(self):
        self.assertIn(f'_PREPARED_MERGE_PREFIX = "{counters.CHAIN_PREFIX}"',
                      (ROOT / "skills" / "shiploop" / "scripts" / "shiploop_chain_git.py").read_text())

    def test_the_lessons_label_of_a_knowledge_commit_is_one_of_the_knowledge_homes_sections(self):
        self.assertIn(counters.LEARNED, knowledge_home.LEARNING_SECTIONS)


class LessonsSectionTest(unittest.TestCase):
    def test_real_messages(self):
        expected = {"improve-six-labels": True, "improve-free-prose": False, "knowledge-with-learned": True,
                    "knowledge-subject-only": False, "item": False, "raw-readme": False, "raw-with-key-learnings": True,
                    "leftovers": False, "baseline": False}
        self.assertEqual(set(expected), set(MESSAGES))
        for name, has in expected.items():
            with self.subTest(name=name):
                self.assertEqual(bool(counters.lessons(MESSAGES[name])), has)

    def test_a_label_with_text_on_its_own_line_and_a_label_followed_by_bullets_both_count(self):
        self.assertEqual(counters.lessons("S\n\nKey learnings: the page needed it too\nRemaining work: none\n"),
                         "the page needed it too")
        self.assertEqual(counters.lessons("S\n\nLearned\n- a\n- b\n\nKey considerations\n- c\n"), "- a\n- b")
        self.assertEqual(counters.lessons("S\n\nKey learnings:\n- one\n\nLearned-from: abcdef1 reused\n"), "- one")

    def test_an_empty_section_a_citation_alone_and_a_label_in_the_middle_of_a_line_do_not_count(self):
        for text in ("S\n\nKey learnings:\nRemaining work: x\n", "S\n\nKey learnings:   \n", "S\n\nLearned-from: abcdef1 reused\n",
                     "S\n\nWe Learned: it\n", "S\n\nLearned\n\nKey considerations\n- c\n", "S\n\nlearned: lower case\n", ""):
            with self.subTest(text=text):
                self.assertEqual(counters.lessons(text), "")


class CitationTest(GitCase):
    """`Learned-from:` lines, with the earlier run's commits behind start_head."""

    def setUp(self):
        super().setUp()
        shiploop_workspace.bootstrap_empty(self.work)
        self.earlier = self.by_the_model("old.md", "An earlier run's commit\n\nKey learnings: the old lesson\n")
        self.start = self.by_the_model("old2.md", "An earlier run's other commit\n")

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


if __name__ == "__main__":
    unittest.main()
