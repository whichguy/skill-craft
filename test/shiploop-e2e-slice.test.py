#!/usr/bin/env python3
"""Step slices (test/shiploop_e2e/slice.py), no model: the seed, the stop, the grade and the packet archive.

A fake host stands in for the model. It is a script that reprints each packet through the real CLI's `next`, moves the
seeded run through the item's inner loop with the navigator's own API (the seed's pattern), commits a product change
at implement, and then keeps running as a model would. The slice stop must end it once the item's inner loop is over,
must not be resumed, and must report an overrun (a host that accepted an outer stage before the poll saw the stop).
The fake commits its change; a model leaves it assembled and uncommitted, which the slice grades the same way.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import clear  # noqa: E402
import flow  # noqa: E402
import metrics  # noqa: E402
import packets  # noqa: E402
import run  # noqa: E402
import sessionlog  # noqa: E402
import slice as step_slice  # noqa: E402
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
import shiploop_store as store  # noqa: E402

CLI = ROOT / "skills" / "shiploop" / "scripts" / "shiploop"
GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
IDENTITY = ["-c", "user.name=Fake host", "-c", "user.email=fake-host@example.invalid"]

# argv: scripts dir, CLI, run dir, mode (normal | overrun | grow). Prints nothing: the harness reads files only.
FAKE_HOST = textwrap.dedent('''
    import json, subprocess, sys, time
    from pathlib import Path
    scripts, cli, run_dir, mode = sys.argv[1:5]
    pause_at = (sys.argv[5] if len(sys.argv) > 5 else "").split(",")  # stages to stay at once, e.g. "implement,test"
    sys.path.insert(0, scripts)
    import shiploop_navigator as nav, shiploop_stage_spec as spec, shiploop_store as store
    run_dir = Path(run_dir)
    memo = run_dir.parent / "fake-paused.txt"  # a fresh session of the fake does not stay where an earlier one did
    paused = set(memo.read_text().split()) if memo.exists() else set()
    worktree = run_dir.parent / "worktree"
    git = ["git", "-C", str(worktree), "-c", "user.name=Fake host", "-c", "user.email=fake-host@example.invalid"]
    extra_outer = 2 if mode == "overrun" else 0
    while True:
        subprocess.run([sys.executable, cli, "next", f"--run-dir={run_dir}"], capture_output=True)  # emit the packet
        state = store.read_record(run_dir / "state.md")
        stage = nav.current_stage(state)
        past = state["status"] != "active" or state["work_index"] > 0 or stage in spec.OUTER
        if past:
            break
        action = nav.current_action(state)["id"]
        if stage in pause_at and action not in paused:
            paused.add(action)
            memo.write_text("\\n".join(sorted(paused)))
            time.sleep(6)  # a model reading the packet: the probe's poll stops it here
            continue
        extra = {}
        if stage == "step-plan":
            extra["test_commands"] = [{"command": "test -f src/feature.js", "suite": "focused"}]
        if stage == "implement":
            (worktree / "src").mkdir(exist_ok=True)
            (worktree / "src" / "feature.js").write_text("module.exports = 1;\\n")
            subprocess.run([*git, "add", "src/feature.js"], check=True, capture_output=True)
            subprocess.run([*git, "commit", "-qm", "feature"], check=True, capture_output=True)
        if stage == "carry-forward" and mode == "grow":
            extra["work_items"] = [{"id": "W2", "title": "A follow-up the review found"}]
        state = nav.apply(state, action, {"outcome": "done", "summary": "Fake host", **extra})
        if state.get("active_improve") is not None:
            state = nav.finish_improve(state, action, {"summary": "Fake review", "lessons": "x"})
        # An overrun accepts the outer stages before anything is saved, so no poll can see the boundary state first
        # (saving each one let a 2 s poll under load stop the host between them, a flaky overrun test).
        while extra_outer and nav.current_stage(state) in spec.OUTER:
            outer = nav.current_action(state)["id"]
            state = nav.apply(state, outer, {"outcome": "done", "summary": "Fake host overrun"})
            if state.get("active_improve") is not None:
                state = nav.finish_improve(state, outer, {"summary": "Fake review", "lessons": "x"})
            extra_outer -= 1
        nav.save(run_dir, state)
        # late-packet: wait past a poll before the next `next` writes the outer stage's packet, so the slice stop lands
        # between the saved state and its packet (the race a loaded machine hits now and then).
        time.sleep(2.5 if mode == "late-packet" and nav.current_stage(state) in spec.OUTER else 0.02)
    time.sleep(120)  # a model would go on to the next packet; only the slice stop ends this
''')

CASE = {"prompt": "Add src/feature.js exporting 1.", "work_item": {"id": "W1", "title": "Add src/feature.js"},
        "expect_paths": ["src/feature.js"], "checks": ["test -f src/feature.js"]}


class SliceCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-slice-")
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.work = self.out / "work"
        self.work.mkdir()

    def seed(self, fixture: Path | None = None, item: dict | None = None) -> dict:
        return run.seed_run(CLI, self.work, self.out, CASE["prompt"], "step-plan", fixture=fixture,
                            work_item=item or CASE["work_item"], delegation="inline")

    def fake(self, seeded: dict, mode: str, *, pause_at: str = "", clear_at: list[dict] | None = None,
             first: bool = True) -> dict:
        script = self.out / "fake_host.py"
        script.write_text(FAKE_HOST)
        argv = [sys.executable, str(script), str(CLI.parent), str(CLI), seeded["run_dir"], mode, pause_at]
        started = time.time()
        process = step_slice.drive(argv, work=self.work, out=self.out, env=GIT_ENV, run_dir=Path(seeded["run_dir"]),
                                   timeout=90, watch=False, clear_at=clear_at, first=first)
        process["wall"] = time.time() - started
        return process


class SeedTests(SliceCase):
    def test_a_fixture_seed_commits_the_fixture_and_records_the_case_item_inline(self):
        seeded = self.seed(fixture=ROOT / "test/shiploop_e2e/fixtures/node-base")
        self.assertEqual((seeded["stage"], seeded["delegation"]), ("step-plan", "inline"))
        tracked = subprocess.run(["git", "-C", str(self.work), "ls-files"], capture_output=True, text=True).stdout.split()
        self.assertIn("src/paginate.js", tracked)
        state = step_slice.read_state(Path(seeded["run_dir"]))
        self.assertEqual([item["id"] for item in state["work_items"]], ["W1"])
        self.assertEqual(state["work_items"][0]["title"], "Add src/feature.js")
        self.assertFalse(step_slice.slice_complete(state))

    def test_the_default_seed_is_unchanged(self):
        seeded = run.seed_run(CLI, self.work, self.out, CASE["prompt"], "step-plan")
        self.assertEqual(seeded["delegation"], "ask-agent")
        state = step_slice.read_state(Path(seeded["run_dir"]))
        self.assertEqual(state["work_items"][0]["id"], "seeded-request")

    def test_every_step_case_names_a_fixture_that_exists(self):
        cases = json.loads((ROOT / "test/shiploop_e2e/step_cases.json").read_text())
        for name, case in cases.items():
            if not name.startswith("_"):
                with self.subTest(name):
                    self.assertTrue((step_slice.FIXTURES / case["fixture"] / "package.json").is_file())
                    self.assertEqual(case["work_item"]["id"], "W1")
                    self.assertTrue(case["checks"] and case["expect_paths"])


class StopTests(SliceCase):
    def test_the_stop_ends_the_host_after_the_inner_loop_and_the_slice_passes(self):
        seeded = self.seed()
        process = self.fake(seeded, "normal")
        self.assertEqual(process["status"], "slice-complete")
        self.assertLess(process["wall"], 60)  # killed by the poll, not the fake's 120 s sleep or the timeout
        result = step_slice.grade(self.out, Path(seeded["run_dir"]), seeded, CASE, [process])
        self.assertTrue(result["pass"], result)
        self.assertEqual(result["overshoot"], [])
        self.assertEqual(result["item_history"][-1], {"stage": "carry-forward", "outcome": "done"})
        self.assertEqual(result["stage_at_stop"], "system-test-author")

    def test_an_overrun_past_the_stop_fails_no_overshoot(self):
        seeded = self.seed()
        process = self.fake(seeded, "overrun")
        self.assertEqual(process["status"], "slice-complete")
        result = step_slice.grade(self.out, Path(seeded["run_dir"]), seeded, CASE, [process])
        self.assertEqual(result["overshoot"], ["system-test-author", "system-test"])
        self.assertFalse(result["verdicts"]["no_overshoot"])
        self.assertFalse(result["pass"])

    def test_a_carry_forward_that_adds_work_stops_after_the_first_item(self):
        seeded = self.seed()
        process = self.fake(seeded, "grow")
        self.assertEqual(process["status"], "slice-complete")
        result = step_slice.grade(self.out, Path(seeded["run_dir"]), seeded, CASE, [process])
        self.assertEqual(result["queue_growth"], 1)
        self.assertEqual(result["overshoot"], [])
        self.assertTrue(result["verdicts"]["inner_loop"])

    def test_the_archive_and_report_cover_every_packet_the_fake_was_sent(self):
        seeded = self.seed()
        self.fake(seeded, "normal")
        archived = sorted(p.name for p in (self.out / packets.ARCHIVE).iterdir())
        report = packets.write_report(self.out)
        self.assertEqual(report["emissions_source"].split()[0], "packet-archive")
        stages = {row["stage"] for row in report["packets"]}
        inner = {"step-plan", "test-spec", "validate-existing", "implement", "test", "document", "verify", "carry-forward"}
        self.assertTrue(inner <= stages, stages)  # every inner stage printed at least once
        self.assertGreaterEqual(len(archived), len(inner))
        self.assertTrue((self.out / packets.REPORT_MD).is_file())


class AssembledProductTests(SliceCase):
    """The inner loop assembles an item uncommitted (plan-return commits at release), so a slice grades the candidate."""

    def repo(self) -> tuple[Path, str]:
        repo = self.out / "worktree"
        repo.mkdir()
        (repo / "README.md").write_text("x\n")
        (repo / ".gitignore").write_text("node_modules/\n")
        for args in (["init", "-q"], ["add", "-A"], [*IDENTITY, "commit", "-qm", "seed"]):
            subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=GIT_ENV)
        head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        return repo, head

    def write(self, repo: Path, path: str, commit: bool = False) -> None:
        (repo / path).parent.mkdir(parents=True, exist_ok=True)
        (repo / path).write_text("change\n")
        if commit:
            for args in (["add", path], [*IDENTITY, "commit", "-qm", f"add {path}"]):
                subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=GIT_ENV)

    def test_only_shiploop_files_is_not_a_product(self):
        repo, head = self.repo()
        self.write(repo, "docs/shiploop/spec.md", commit=True)
        self.write(repo, ".shiploop-improve/nav-1/opening.md")
        found = step_slice.assembled_product(repo, head, ["src/*.js"])
        self.assertFalse(found["pass"])
        self.assertIn("only ShipLoop's own files", found["reason"])

    def test_an_uncommitted_candidate_is_assembled_and_checked(self):
        repo, head = self.repo()
        self.write(repo, "src/a.js")                  # untracked, as the first live slice left its new test
        self.write(repo, "README.md")                 # a tracked file modified in place
        found = step_slice.assembled_product(repo, head, ["src/a.js", "README.md"])
        self.assertTrue(found["pass"], found)
        self.assertEqual(found["committed_since_seed"], [])
        self.assertEqual(found["uncommitted_product"], ["README.md", "src/a.js"])

    def test_the_checks_see_the_candidate_but_not_ignored_files_or_run_evidence(self):
        repo, head = self.repo()
        self.write(repo, "src/a.js")
        self.write(repo, "node_modules/dep/index.js")
        self.write(repo, ".shiploop-improve/nav-1/opening.md")
        checks = step_slice.checks_on_candidate(repo, self.out, [
            "test -f src/a.js", "test ! -e node_modules", "test ! -e .shiploop-improve", "test -f README.md"])
        self.assertEqual([c["pass"] for c in checks], [True, True, True, True])

    def test_a_missing_expected_path_fails(self):
        repo, head = self.repo()
        self.write(repo, "src/a.js", commit=True)
        found = step_slice.assembled_product(repo, head, ["src/a.js", "test/*.test.js"])
        self.assertFalse(found["pass"])
        self.assertIn("test/*.test.js", found["reason"])


class ArchiveTests(SliceCase):
    def test_a_rewritten_packet_is_archived_once_per_distinct_content(self):
        run_dir = self.out / "run"
        (run_dir / "packets").mkdir(parents=True)
        packet = run_dir / "packets" / "nav-1.md"
        for text, added in (("first", 1), ("first", 0), ("second", 1), ("first", 1)):
            packet.write_text(text)
            self.assertEqual(packets.archive_packets(run_dir, self.out), added, text)
        self.assertEqual(len(list((self.out / packets.ARCHIVE / "nav-1").iterdir())), 3)

    def test_overlap_counts_lines_sent_before(self):
        line = "a line long enough to be counted as repeated text"
        self.assertEqual(packets.overlap_shares([line, line + "\n" + line.upper()]), [0.0, 0.5])


def _stream(path: Path, rows: list[dict]) -> None:
    """A Claude-shaped stream. Each row: {"call": command or {tool input}, "tool": name, "result": text or None}.
    A row whose result is None is a call cut off before its result."""
    lines = []
    for n, row in enumerate(rows):
        call = row["call"]
        lines.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": f"t{n}",
                      "name": row.get("tool", "Bash"), "input": call if isinstance(call, dict) else {"command": call}}]}})
        if row.get("result") is not None:
            lines.append({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{n}",
                                                                    "content": row["result"]}]}})
    path.write_text("".join(json.dumps(x) + "\n" for x in lines))


class ClearMetricTests(unittest.TestCase):
    """clear.redone: only completed state-changing work repeated after the clear counts (SPEC S-6)."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-clear-")
        self.addCleanup(self.temp.cleanup)
        self.events = Path(self.temp.name) / "events.jsonl"

    def redone(self, before: list[dict], after: list[dict]) -> list[dict]:
        _stream(self.events, before)
        clear_line = len(self.events.read_text().splitlines())
        _stream(self.events, before + after)
        return clear.redone(self.events, clear_line)

    WRITE = {"tool": "Write", "call": {"file_path": "/w/src/a.js", "content": "x = 1"}, "result": "ok"}

    def test_a_completed_write_repeated_is_redone_work(self):
        found = self.redone([self.WRITE], [self.WRITE])
        self.assertEqual([f["kind"] for f in found], ["write"])

    def test_an_unfinished_write_repeated_is_not(self):
        self.assertEqual(self.redone([dict(self.WRITE, result=None)], [self.WRITE]), [])

    def test_a_write_with_other_content_is_new_work(self):
        other = {"tool": "Write", "call": {"file_path": "/w/src/a.js", "content": "x = 2"}, "result": "ok"}
        self.assertEqual(self.redone([self.WRITE], [other]), [])

    def test_a_heredoc_write_is_a_write(self):
        heredoc = {"call": "cat > src/a.js <<'EOF'\nx = 1\nEOF\nnpm test", "result": "ok"}
        found = self.redone([heredoc], [heredoc])
        self.assertEqual([f["kind"] for f in found], ["write"])  # the repeated write fails the gate; its test follows a write

    RECORD = {"call": "python3 /p/scripts/shiploop complete --run-dir=/r --action=nav-" + "b" * 32 + " --result=/r/x.md",
              "result": "ShipLoop navigator | test | revision 5"}

    def test_a_test_rerun_after_a_change_is_legitimate_and_without_one_is_redone(self):
        test = {"call": "npm test 2>&1 | tail -3", "result": "pass 9"}
        self.assertEqual(self.redone([test, self.RECORD], [self.WRITE, test]), [])
        self.assertEqual([f["kind"] for f in self.redone([test, self.RECORD], [test])], ["test"])

    def test_a_rerun_of_a_test_whose_result_shiploop_never_recorded_is_verification(self):
        # The 2026-10-11 probe (node-fix-bug, implement:inside, build fbabc74f): one call edited and tested, the kill
        # landed before any callback recorded that result, and the fresh session reran the test to see where it stood.
        # It cannot know a result that only the cleared context saw.
        edit_and_test = {"call": "sed -i '' 's|a|b|' src/paginate.js && npm test 2>&1 | grep -E 'pass|fail'",
                         "result": "pass 9"}
        rerun = {"call": "git diff; node --check src/paginate.js; npm test 2>&1 | grep -E 'pass|fail'",
                 "result": "pass 9"}
        self.assertEqual(self.redone([edit_and_test], [rerun]), [])
        self.assertEqual(self.redone([{"call": "npm test", "result": "pass 9"}], [{"call": "npm test", "result": "ok"}]),
                         [])

    def test_a_script_write_or_a_same_call_write_makes_the_rerun_legitimate(self):
        test = {"call": "npm test 2>&1 | tail -3", "result": "pass 9"}
        python_edit = {"call": "python3 - <<'EOF'\np='t.js';s=open(p).read();open(p,'w').write(s+'x')\nEOF\nnpm test",
                       "result": "pass 10"}
        append_and_test = {"call": "cat >> test/a.test.js <<'EOF'\ntest('x', () => {});\nEOF\nnpm test 2>&1", "result": "ok"}
        self.assertEqual(self.redone([test], [python_edit]), [])
        self.assertEqual(self.redone([test], [append_and_test]), [])

    def test_read_only_orientation_never_counts(self):
        rows = [{"call": "python3 /p/scripts/shiploop next --run-dir /r", "result": "ShipLoop navigator | implement | revision 3"},
                {"call": "cat /r/packets/nav-1.md; git status --short; git diff", "result": "..."}]
        self.assertEqual(self.redone(rows, rows), [])

    def test_a_repeated_callback_for_the_same_action_is_redone(self):
        done = {"call": "python3 /p/scripts/shiploop complete --run-dir=/r --action=nav-" + "a" * 32 + " --result=/r/x.md",
                "result": "ShipLoop navigator | test-green | revision 4"}
        self.assertEqual([f["kind"] for f in self.redone([done], [done])], ["callback"])

    def test_a_redo_is_counted_in_the_window_of_the_clear_it_follows_and_no_other(self):
        def write(name):
            return {"tool": "Write", "call": {"file_path": f"/w/{name}.js", "content": name}, "result": "ok"}
        rows = [write("a"), write("b"), write("a"), write("c")]  # session 3 repeats session 1's write
        _stream(self.events, rows)
        first, second, third = 2, 4, 6                            # each row is a call and its result: the stop lines
        self.assertEqual(clear.redone(self.events, first, second), [])
        self.assertEqual([f["kind"] for f in clear.redone(self.events, second, third)], ["write"])
        self.assertEqual(clear.redone(self.events, third), [])
        # Unbounded (the last clear's window), a repeat after the second clear would also fail the first.
        self.assertEqual([f["kind"] for f in clear.redone(self.events, first)], ["write"])


class ClearTriggerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-clear-trigger-")
        self.addCleanup(self.temp.cleanup)
        self.events = Path(self.temp.name) / "events.jsonl"
        self.state = {"status": "active", "stage": "implement", "action": {"id": "nav-x"}, "revision": 9}

    def stage_of(self, state):
        return state["stage"]

    def test_the_boundary_stops_once_the_stage_is_current_and_inside_waits_for_a_completed_call(self):
        head = {"call": "python3 /p/scripts/shiploop complete --run-dir=/r --action=nav-y", "result":
                "ShipLoop navigator | implement | revision 9"}
        _stream(self.events, [head])
        at = clear.trigger(self.events, self.state, {"stage": "implement", "inside": False}, self.stage_of)
        self.assertEqual((at["stage"], at["action"], at["revision"]), ("implement", "nav-x", 9))
        inside = {"stage": "implement", "inside": True}
        self.assertIsNone(clear.trigger(self.events, self.state, inside, self.stage_of))
        _stream(self.events, [head, {"call": "sed -n 1,5p src/a.js", "result": None}])  # in flight: not yet
        self.assertIsNone(clear.trigger(self.events, self.state, inside, self.stage_of))
        _stream(self.events, [head, {"call": "sed -n 1,5p src/a.js", "result": "..."}])
        self.assertIsNotNone(clear.trigger(self.events, self.state, inside, self.stage_of))
        self.assertIsNone(clear.trigger(self.events, dict(self.state, stage="test-red"), inside, self.stage_of))

    IMPLEMENT_HEAD = {"call": "python3 /p/scripts/shiploop next --run-dir=/r", "result": "ShipLoop navigator | implement | revision 9"}
    IMPROVE_HEAD = {"call": "python3 /p/scripts/shiploop complete --run-dir=/r --action=nav-x",
                    "result": "ShipLoop navigator | improve | revision 10 | the implement result"}
    READ = {"call": "sed -n 1,5p src/a.js", "result": "..."}

    def reviewing(self):
        # The producer's result waits at its Improve stage: the stage is still implement, the Improve child is bound.
        return dict(self.state, active_improve={"action_id": "nav-x", "stage": "implement", "improve_action": "nav-i"})

    def test_an_improve_position_stops_while_the_child_is_bound_and_a_stage_position_does_not(self):
        improve = {"stage": "improve", "inside": False}
        _stream(self.events, [self.IMPROVE_HEAD])
        self.assertIsNone(clear.trigger(self.events, self.state, improve, self.stage_of), "no child, no Improve stage")
        at = clear.trigger(self.events, self.reviewing(), improve, self.stage_of)
        self.assertEqual((at["stage"], at["action"]), ("improve", "nav-i"), "the Improve stage is its own position")
        for inside in (False, True):
            self.assertIsNone(clear.trigger(self.events, self.reviewing(), {"stage": "implement", "inside": inside},
                                            self.stage_of), "the reviewed stage is not current while its review runs")

    def test_inside_an_improve_stage_waits_for_its_packet_and_a_completed_call_that_is_not_shiploops(self):
        inside = {"stage": "improve", "inside": True}
        _stream(self.events, [self.IMPROVE_HEAD])
        self.assertIsNone(clear.trigger(self.events, self.reviewing(), inside, self.stage_of))
        review = {"tool": "Skill", "call": {"skill": "skill-craft:improve"}, "result": None}
        _stream(self.events, [self.IMPROVE_HEAD, review])        # the skill call is in flight
        self.assertIsNone(clear.trigger(self.events, self.reviewing(), inside, self.stage_of))
        _stream(self.events, [self.IMPROVE_HEAD, dict(review, result="Launching skill")])
        self.assertIsNotNone(clear.trigger(self.events, self.reviewing(), inside, self.stage_of))
        ledger = {"call": "python3 /p/scripts/shiploop improve-pass --run-dir=/r --action=nav-i", "result": "ok"}
        _stream(self.events, [self.IMPROVE_HEAD, ledger])
        self.assertIsNone(clear.trigger(self.events, self.reviewing(), inside, self.stage_of), "ShipLoop's own calls never count")

    def test_a_later_clear_counts_only_the_packet_and_calls_that_came_after_the_earlier_stop(self):
        inside = {"stage": "implement", "inside": True}
        _stream(self.events, [self.IMPLEMENT_HEAD, self.READ])
        self.assertIsNotNone(clear.trigger(self.events, self.state, inside, self.stage_of))
        stopped = len(self.events.read_text().splitlines())
        self.assertIsNone(clear.trigger(self.events, self.state, inside, self.stage_of, since=stopped),
                          "the cleared session's packet and call are not the fresh session's")
        _stream(self.events, [self.IMPLEMENT_HEAD, self.READ, self.READ])
        self.assertIsNone(clear.trigger(self.events, self.state, inside, self.stage_of, since=stopped),
                          "a call with no packet shown after the stop")
        _stream(self.events, [self.IMPLEMENT_HEAD, self.READ, self.IMPLEMENT_HEAD])
        self.assertIsNone(clear.trigger(self.events, self.state, inside, self.stage_of, since=stopped), "the packet, no call yet")
        _stream(self.events, [self.IMPLEMENT_HEAD, self.READ, self.IMPLEMENT_HEAD, self.READ])
        self.assertIsNotNone(clear.trigger(self.events, self.state, inside, self.stage_of, since=stopped))

    def test_a_stream_the_harness_cannot_read_stops_at_a_boundary_and_never_inside(self):
        # Grok and Codex events are tool_call / tool_call_update lines, not Claude's message blocks (hosts.CodexTranslator):
        # the calls cannot be read, so an inside position has nothing to wait on. It is accepted, recorded as requested
        # (invocation.json clear_at) and reported unfired; it is not refused, and a boundary is state-based.
        grok = [{"type": "tool_call", "toolCallId": "c1", "toolName": "run_terminal_command",
                 "rawInput": {"command": "sed -n 1,5p src/a.js"}},
                {"type": "tool_call_update", "toolCallId": "c1", "status": "completed",
                 "rawOutput": {"output_for_prompt": "ShipLoop navigator | implement | revision 9"}}]
        self.events.write_text("".join(json.dumps(x) + "\n" for x in grok))
        self.assertIsNotNone(clear.trigger(self.events, self.state, {"stage": "implement", "inside": False}, self.stage_of))
        self.assertIsNone(clear.trigger(self.events, self.state, {"stage": "implement", "inside": True}, self.stage_of))


class ClearProbeTests(SliceCase):
    def test_a_clear_at_the_boundary_records_the_stop_and_a_fresh_session_finishes_the_slice(self):
        seeded = self.seed()
        first = self.fake(seeded, "normal", pause_at="implement", clear_at=[{"stage": "implement", "inside": False}])
        self.assertEqual(first["status"], "cleared")
        records = json.loads((self.out / step_slice.CLEAR_RECORD).read_text())
        self.assertEqual(len(records), 1, "clear.json is a list, one record per clear")
        record = records[0]
        self.assertEqual((record["n"], record["stage"], record["inside"]), (1, "implement", False))
        self.assertEqual(record["stopped"]["stage"], "implement")
        self.assertEqual(record["triggered"]["action"], record["stopped"]["action"])
        second = self.fake(seeded, "normal", first=False)  # the fresh session: the fake reads the packet again
        self.assertEqual(second["status"], "slice-complete")
        result = step_slice.grade(self.out, Path(seeded["run_dir"]), seeded, CASE, [first, second])
        self.assertTrue(result["verdicts"]["no_redo"])  # the fake's stream holds no calls: nothing to redo
        self.assertTrue(result["pass"], result["verdicts"])
        self.assertEqual([c["pass"] for c in result["clear"]], [True])

    def test_each_session_ends_at_the_next_position_not_yet_cleared_and_three_clears_give_three_records(self):
        seeded = self.seed()
        specs = clear.parse_spec(["implement", "test", "verify"])
        statuses, first = [], True
        for _ in range(6):                                   # the loop in slice.main: continue while a clear ended the session
            process = self.fake(seeded, "normal", pause_at="implement,test,verify", clear_at=specs, first=first)
            statuses.append(process["status"])
            first = False
            if process["status"] != "cleared":
                break
        self.assertEqual(statuses, ["cleared", "cleared", "cleared", "slice-complete"])
        records = json.loads((self.out / step_slice.CLEAR_RECORD).read_text())
        self.assertEqual([(r["n"], r["stage"], r["stopped"]["stage"]) for r in records],
                         [(1, "implement", "implement"), (2, "test", "test"), (3, "verify", "verify")])
        lines = [r["stopped"]["events_line"] for r in records]
        self.assertEqual(lines, sorted(lines))


class ClearRecordTests(SliceCase):
    """clear.json is a list; each clear is measured against its own stop, and a clear that never happened is reported."""

    def stream_with_clears(self, rows: list[dict], stops: list[int], asked: list[str] | None = None) -> dict:
        _stream(self.out / "events.jsonl", rows)
        records = [{"n": n, "stage": "implement", "inside": False, "triggered": {}, "stopped": {"stage": "implement",
                    "action": "", "revision": 5, "events_line": line, "last_answered_line": line - 1}}
                   for n, line in enumerate(stops, 1)]
        (self.out / step_slice.CLEAR_RECORD).write_text(json.dumps(records))
        if asked is not None:
            (self.out / "invocation.json").write_text(json.dumps({"clear_at": asked}))
        return self.seed()

    @staticmethod
    def write(name: str) -> dict:
        return {"tool": "Write", "call": {"file_path": f"/w/{name}.js", "content": name}, "result": "ok"}

    def test_a_stream_redoing_a_call_after_the_second_clear_fails_that_clear_only(self):
        seeded = self.stream_with_clears([self.write("a"), self.write("b"), self.write("a"), self.write("c")], [2, 4, 6])
        facts = step_slice.clear_facts(self.out)
        self.assertEqual([f["pass"] for f in facts], [True, False, True])
        self.assertEqual([r["kind"] for r in facts[1]["redone"]], ["write"])
        self.assertEqual([f["n"] for f in facts], [1, 2, 3])
        result = step_slice.grade(self.out, Path(seeded["run_dir"]), seeded, CASE, [{"status": "slice-complete"}])
        self.assertFalse(result["verdicts"]["no_redo"], "one failed clear fails the verdict")
        self.assertEqual([c["pass"] for c in result["clear"]], [True, False, True])

    def test_three_clean_clears_pass_and_a_position_that_never_fired_is_listed_not_hidden(self):
        seeded = self.stream_with_clears([self.write("a"), self.write("b"), self.write("c")], [2, 4, 6],
                                         asked=["implement", "implement:inside", "improve", "verify"])
        result = step_slice.grade(self.out, Path(seeded["run_dir"]), seeded, CASE, [{"status": "slice-complete"}])
        self.assertTrue(result["verdicts"]["no_redo"])
        self.assertEqual(len(result["clear"]), 3)
        self.assertEqual(result["clear_unfired"], ["verify"])

    def test_no_clear_means_no_verdict_and_nothing_unfired_without_a_request(self):
        seeded = self.seed()
        result = step_slice.grade(self.out, Path(seeded["run_dir"]), seeded, CASE, [{"status": "slice-complete"}])
        self.assertNotIn("no_redo", result["verdicts"])
        self.assertEqual((result["clear"], result["clear_unfired"]), ([], []))

    def test_a_record_from_the_one_clear_layout_is_refused_not_read_as_empty(self):
        (self.out / step_slice.CLEAR_RECORD).write_text(json.dumps({"stage": "implement", "inside": False, "stopped": {}}))
        with self.assertRaises(SystemExit) as raised:
            step_slice.clear_facts(self.out)
        self.assertIn("older", str(raised.exception))


class ResumePromptTests(unittest.TestCase):
    CLI = Path("/p/skills/shiploop/scripts/shiploop")

    def test_names_next_is_the_runs_own_resume_prompt_and_told_says_so(self):
        prompt, told = step_slice.continue_prompt("names-next", "/r/run", self.CLI)
        self.assertEqual(prompt, run.resume_prompt("/r/run", self.CLI))
        self.assertEqual(told, {"cli": str(self.CLI), "run_dir": "/r/run"})
        self.assertIn("next --run-dir", prompt)

    def test_withheld_names_no_command_no_path_and_no_stage(self):
        prompt, told = step_slice.continue_prompt("withheld", "/r/run", self.CLI)
        self.assertEqual(prompt, "Continue the ShipLoop work for the repository in this directory.")
        self.assertIsNone(told, "sessions.jsonl records that the prompt named no recovery command")
        for named in ("next", "/r/run", str(self.CLI), "--run-dir", "complete"):
            self.assertNotIn(named, prompt)

    def test_the_command_line_collects_every_position_and_offers_the_two_conditions(self):
        args = step_slice.parser().parse_args(["--case", "x", "--clear-at", "implement:inside", "--clear-at", "test",
                                               "--clear-at", "improve"])
        self.assertEqual(args.clear_at, ["implement:inside", "test", "improve"])
        self.assertEqual(args.resume_prompt, "names-next", "the default is today's prompt")
        self.assertEqual(step_slice.parser().parse_args(["--resume-prompt", "withheld"]).resume_prompt, "withheld")
        self.assertIsNone(step_slice.parser().parse_args([]).clear_at)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            step_slice.parser().parse_args(["--resume-prompt", "hint"])


class ClearSpecTests(unittest.TestCase):
    def test_the_flag_repeats_and_each_position_parses_in_the_order_given(self):
        self.assertEqual(clear.parse_spec(["implement:inside", "test", "improve"]), [
            {"stage": "implement", "inside": True}, {"stage": "test", "inside": False},
            {"stage": "improve", "inside": False}])
        self.assertEqual(clear.parse_spec(["improve:inside"]), [{"stage": "improve", "inside": True}])
        self.assertEqual(clear.parse_spec(None), [])
        self.assertEqual([clear.label(s) for s in clear.parse_spec(["implement:inside", "improve"])],
                         ["implement:inside", "improve"])

    def test_a_malformed_position_is_refused_before_anything_starts(self):
        for text in ("test:outside", ":inside", "", "test:inside:more"):
            with self.subTest(text), self.assertRaises(SystemExit):
                clear.parse_spec([text])


FAKE_CLAUDE = textwrap.dedent('''
    import json, os, subprocess, sys, time
    from pathlib import Path
    cfg = json.loads(Path(os.environ["FAKE_SLICE_CONFIG"]).read_text())
    prompt = sys.argv[sys.argv.index("-p") + 1]
    with open(cfg["prompts"], "a") as handle:
        handle.write(json.dumps(prompt) + "\\n")
    sys.path.insert(0, cfg["scripts"])
    import shiploop_navigator as nav, shiploop_stage_spec as spec, shiploop_store as store
    cli, run_dir = cfg["cli"], Path(cfg["run_dir"])
    worktree = run_dir.parent / "worktree"
    git = ["git", "-C", str(worktree), "-c", "user.name=Fake host", "-c", "user.email=fake-host@example.invalid"]
    memo = run_dir.parent / "fake-holds.json"
    held = json.loads(memo.read_text()) if memo.exists() else {}   # how many sessions have already stayed at each place
    here, count = set(), [0]

    def shown(command, output):
        count[0] += 1
        ident = f"f{os.getpid()}-{count[0]}"
        for event in ({"type": "assistant", "message": {"content": [
                          {"type": "tool_use", "id": ident, "name": "Bash", "input": {"command": command}}]}},
                      {"type": "user", "message": {"content": [
                          {"type": "tool_result", "tool_use_id": ident, "content": output}]}}):
            print(json.dumps(event), flush=True)

    def hold(place, sessions):
        # Stay long enough for the harness poll to end this session: once per session, for `sessions` sessions in all.
        if place in here or held.get(place, 0) >= sessions:
            return False
        here.add(place)
        held[place] = held.get(place, 0) + 1
        memo.write_text(json.dumps(held))
        time.sleep(8)
        return True

    while True:
        printed = subprocess.run([sys.executable, cli, "next", f"--run-dir={run_dir}"], capture_output=True, text=True).stdout
        shown(f"python3 {cli} next --run-dir={run_dir}", printed)
        state = store.read_record(run_dir / "state.md")
        stage = nav.current_stage(state)
        if state["status"] != "active" or state["work_index"] > 0 or stage in spec.OUTER:
            break
        child = state.get("active_improve")
        if child is not None:
            if child["stage"] == cfg["improve_of"] and hold("improve:" + child["action_id"], 1):
                continue
            nav.save(run_dir, nav.finish_improve(state, child["action_id"], {"summary": "Fake review", "lessons": "x"}))
            continue
        action = nav.current_action(state)["id"]
        if stage == "implement" and "read" not in here:
            here.add("read")
            shown("sed -n 1,5p src/paginate.js", "module.exports = {};")
        if stage in cfg["holds"] and hold(stage + ":" + action, cfg["holds"].count(stage)):
            continue
        extra = {}
        if stage == "step-plan":
            extra["test_commands"] = [{"command": "test -f src/feature.js", "suite": "focused"}]
        if stage == "implement":
            (worktree / "src").mkdir(exist_ok=True)
            (worktree / "src" / "feature.js").write_text("module.exports = 1;\\n")
            subprocess.run([*git, "add", "src/feature.js"], check=True, capture_output=True)
            subprocess.run([*git, "commit", "-qm", "feature"], check=True, capture_output=True)
        nav.save(run_dir, nav.apply(state, action, {"outcome": "done", "summary": "Fake host", **extra}))
    time.sleep(120)
''')


class ClearThroughMainTests(unittest.TestCase):
    """slice.main with a fake `claude` that prints Claude-shaped events: the positions, the prompt condition and the
    records as the live battery will produce them. The fake stays at a position for one poll; a fresh process of it
    (the next session) continues from the ledger."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-slice-main-")
        self.addCleanup(self.temp.cleanup)
        self.tmp = Path(self.temp.name).resolve()
        self.plugin = self.tmp / "plugin"
        (self.plugin / "skills").mkdir(parents=True)
        (self.plugin / "skills" / "shiploop").symlink_to(ROOT / "skills" / "shiploop")
        self.out = self.tmp / "slice"
        self.cli = self.plugin / "skills" / "shiploop" / "scripts" / "shiploop"
        self.run_dir = self.out / ".shiploop-runs" / "seed" / "run"
        self.fake = self.tmp / "claude"
        self.fake.write_text(f"#!{sys.executable}\n{FAKE_CLAUDE}")
        self.fake.chmod(0o755)
        self.prompts = self.tmp / "prompts.jsonl"
        self.handlers = {n: signal.getsignal(n) for n in (signal.SIGTERM, signal.SIGHUP)}  # slice.main takes them over
        self.addCleanup(self.restore_signals)

    def restore_signals(self):
        for number, handler in self.handlers.items():
            signal.signal(number, handler)

    def main(self, holds: list[str], *flags: str) -> dict:
        config = self.tmp / "config.json"
        config.write_text(json.dumps({"prompts": str(self.prompts), "scripts": str(CLI.parent), "cli": str(CLI),
                                      "run_dir": str(self.run_dir), "holds": holds, "improve_of": "implement"}))
        case = {**CASE, "fixture": "node-base"}
        with mock.patch.dict(os.environ, {"FAKE_SLICE_CONFIG": str(config)}), \
                mock.patch.object(step_slice, "load_step_case", return_value=case), \
                contextlib.redirect_stdout(io.StringIO()):
            step_slice.main(["--case", "fake", "--host", "claude", "--claude-bin", str(self.fake),
                             "--plugin-dir", str(self.plugin), "--output", str(self.out), "--timeout", "300", "--quiet",
                             *flags])
        return json.loads((self.out / "slice-result.json").read_text())

    def sent(self) -> list[str]:
        return [json.loads(line) for line in self.prompts.read_text().splitlines()]

    def test_three_positions_with_the_prompt_withheld_give_three_records_a_flow_and_the_unfired_one_named(self):
        result = self.main(["implement", "implement"], "--clear-at", "implement", "--clear-at", "implement:inside",
                           "--clear-at", "improve", "--clear-at", "carry-forward:inside", "--resume-prompt", "withheld")
        records = json.loads((self.out / step_slice.CLEAR_RECORD).read_text())
        self.assertEqual([(r["n"], r["stage"], r["inside"], r["stopped"]["stage"]) for r in records],
                         [(1, "implement", False, "implement"), (2, "implement", True, "implement"),
                          (3, "improve", False, "improve")])
        self.assertEqual([s["status"] for s in result["sessions"]], ["cleared", "cleared", "cleared", "slice-complete"])
        self.assertTrue(result["verdicts"]["no_redo"], result["clear"])
        self.assertEqual([c["pass"] for c in result["clear"]], [True, True, True])
        self.assertEqual(result["clear_unfired"], ["carry-forward:inside"])
        # The condition reached the host, three times and never the opening, and the record says nothing was named.
        sent = self.sent()
        self.assertEqual(len(sent), 4)
        self.assertEqual(sent[1:], [step_slice.WITHHELD_PROMPT] * 3)
        self.assertIn("/skill-craft:shiploop", sent[0])
        self.assertEqual([s["told"] for s in sessionlog.read(self.out)][1:], [None, None, None])
        invocation = json.loads((self.out / "invocation.json").read_text())
        self.assertEqual((invocation["clear_at"], invocation["resume_prompt"]),
                         (["implement", "implement:inside", "improve", "carry-forward:inside"], "withheld"))
        flow = json.loads((self.out / "flow.json").read_text())
        self.assertEqual([(c["n"], c["stage"], c["inside"], c["pass"]) for c in flow["clear"]],
                         [(1, "implement", False, True), (2, "implement", True, True), (3, "improve", False, True)])

    def test_the_default_condition_names_next_and_the_record_says_what_it_named(self):
        result = self.main(["implement"], "--clear-at", "implement")
        sent = self.sent()
        self.assertEqual(len(sent), 2)
        self.assertEqual(sent[1], run.resume_prompt(str(self.run_dir), self.cli))
        self.assertEqual(sessionlog.read(self.out)[1]["told"], {"cli": str(self.cli), "run_dir": str(self.run_dir)})
        self.assertEqual(json.loads((self.out / "invocation.json").read_text())["resume_prompt"], "names-next")
        self.assertEqual((len(result["clear"]), result["clear_unfired"]), (1, []))


class FlowTests(SliceCase):
    """flow.py: the sequence the viewer shows, from files only."""

    def claude_stream(self, seeded: dict, rows: list[dict]) -> None:
        """A Claude-shaped event stream: each row is a tool call and its result."""
        lines, stamps = [], []
        for n, row in enumerate(rows):
            lines.append({"type": "assistant", "message": {"content": [
                *([{"type": "text", "text": row["say"]}] if row.get("say") else []),
                {"type": "tool_use", "id": f"t{n}", "name": "Bash", "input": {"command": row["call"]}}]}})
            lines.append({"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": f"t{n}", "content": row.get("result", "")}]}})
        (self.out / "events.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines))
        (self.out / "timeline.jsonl").write_text("".join(json.dumps({"line": i, "t": 1000.0 + i}) + "\n"
                                                         for i in range(len(lines))))

    def test_events_follow_the_last_head_and_scripts_are_flagged(self):
        seeded = self.seed()
        run_dir = Path(seeded["run_dir"])
        step_plan = seeded["action"]
        head = subprocess.run([sys.executable, str(CLI), "next", f"--run-dir={run_dir}"], capture_output=True,
                              text=True).stdout
        self.claude_stream(seeded, [
            {"call": f"python3 shiploop next --run-dir={run_dir}", "result": head, "say": "Starting the plan."},
            {"call": "cat > /x/cycle.sh <<'XEOF'\ncat > $D/reviews/review-1.md <<EOF\nNo change warranted.\nEOF\n"
                     "printf '%s' '{\"classification\":\"trivial\"}'\nXEOF\n/x/cycle.sh A"},
            {"call": "/x/cycle.sh B", "result": "ShipLoop navigator | test-spec | revision 99\n"
                                                 "Callback: shiploop complete --action=nav-" + "f" * 32},
            {"call": "echo after the head"},
        ])
        found = flow.build(self.out)
        by_action = {a["action"]: a for a in found["actions"]}
        mine = by_action[step_plan]["phases"][0]
        self.assertEqual(found["events_source"], "claude")
        self.assertIn("Starting the plan.", [e["body"]["text"] for e in mine["events"] if e["kind"] == "say"])
        self.assertTrue(mine["head"].startswith("ShipLoop navigator | step-plan"))
        flags = mine["flags"]
        self.assertIn("defines-script:cycle.sh", flags)
        self.assertIn("runs-script:cycle.sh", flags)
        self.assertIn("scripted-review", flags)
        self.assertIn("trivial-pass", flags)
        later = by_action["nav-" + "f" * 32]["phases"][0]  # a head names the next action; the run stopped there
        self.assertFalse(by_action["nav-" + "f" * 32]["accepted"])
        self.assertEqual([e["body"]["text"] for e in later["events"] if e["kind"] == "call"], ["echo after the head"])
        self.assertTrue(all(a["seeded"] for a in found["actions"] if a["stage"] in ("intake", "plan")))

    def test_the_improve_stage_is_an_action_row_of_its_own_and_an_old_layout_run_keeps_its_improve_phase(self):
        seeded = self.seed()
        run_dir = Path(seeded["run_dir"])
        state = store.read_record(run_dir / "state.md")
        spec = next(h["action"] for h in state["history"] if h["stage"] == "spec")
        plan = next(h["action"] for h in state["history"] if h["stage"] == "plan")
        stage_id = "nav-" + "c" * 32
        # New layout: the Improve stage has its own id, recorded at import, and its own packet file. Old layout (plan):
        # the Improve child's packet sits beside the producer's as <action>-improve.md.
        state["improve_results"][spec]["improve_action"] = stage_id
        store.write_record(run_dir / "state.md", state)
        packet_dir = run_dir / "packets"
        packet_dir.mkdir(exist_ok=True)
        improve_head = (f"ShipLoop navigator | improve | revision 4 | the spec result\n1. Run the improve skill on the spec result.\n"
                        f"2. When the improve skill has completed, run: python3 shiploop complete --run-dir={run_dir} --action={stage_id}\n")
        (packet_dir / f"{spec}.md").write_text("ShipLoop navigator | spec | revision 3\nproducer\n")
        (packet_dir / f"{stage_id}.md").write_text(improve_head)
        (packet_dir / f"{stage_id}-bind.md").write_text(improve_head.replace("revision 4", "revision 3"))
        (packet_dir / f"{plan}.md").write_text("ShipLoop navigator | plan | revision 5\nproducer\n")
        (packet_dir / f"{plan}-improve.md").write_text("ShipLoop navigator | plan | revision 6 | Improve\nold child\n")
        self.claude_stream(seeded, [{"call": "shiploop next", "result": improve_head},
                                    {"call": "echo review", "say": "Reviewing the spec."}])
        found = flow.build(self.out)
        rows = found["actions"]
        names = [(r["stage"], r["action"]) for r in rows]
        at = names.index(("improve", stage_id))
        self.assertEqual(names[at - 1], ("spec", spec), "the Improve stage is listed right after the action it reviews")
        row = rows[at]
        self.assertEqual((row["reviewed"], row["reviewed_stage"], row["accepted"]), (spec, "spec", True))
        self.assertEqual([p["kind"] for p in row["phases"]], ["improve"])
        self.assertEqual(row["phases"][0]["packet"]["chars"], len(improve_head))
        self.assertIn("Reviewing the spec.", [e["body"]["text"] for e in row["phases"][0]["events"] if e["kind"] == "say"])
        self.assertEqual([p["kind"] for p in rows[at - 1]["phases"]], ["producer"], "the producer has no Improve phase of its own")
        old = next(r for r in rows if r["action"] == plan)
        self.assertEqual([p["kind"] for p in old["phases"]], ["producer", "improve"])
        self.assertNotIn(("improve", plan), names)
        self.assertEqual(sum(1 for r in rows if r["stage"] == "improve"), 1)
        self.assertEqual(found["flow_version"], 2)
        report = packets.build(self.out)
        by_packet = {r["packet"]: r for r in report["packets"]}
        self.assertEqual((by_packet[stage_id]["kind"], by_packet[stage_id]["stage"], by_packet[stage_id]["reviewed_stage"],
                          by_packet[stage_id]["action"]), ("improve", "improve", "spec", spec))
        self.assertEqual(by_packet[f"{stage_id}-bind"]["action"], spec)
        self.assertEqual((by_packet[f"{plan}-improve"]["kind"], by_packet[f"{plan}-improve"]["action"]), ("improve", plan))
        self.assertEqual(by_packet[spec]["kind"], "producer")

    def test_a_fake_host_run_gives_a_flow_and_a_page_that_cannot_be_closed_by_its_data(self):
        seeded = self.seed()
        self.fake(seeded, "normal")
        found = flow.write(self.out)
        self.assertEqual(found["flow_version"], flow.FLOW_VERSION)
        self.assertEqual(found["actions"][-1]["stage"], "system-test-author")  # the ledger names the stop action
        found["prompt"] = "</script><b>not markup</b>"
        page = flow.bundle(self.out / "two.html", [found, found]).read_text()
        self.assertTrue(page.startswith("<!doctype html>"))
        self.assertEqual(page.count("</script>"), 2)  # the data block and the viewer's own script, nothing from the data
        self.assertFalse(flow.bundle(self.out / "a.html", [found], standalone=False).read_text().startswith("<!doctype"))

    def test_the_stop_action_is_named_by_the_ledger_when_the_slice_stopped_before_its_packet(self):
        """A slice stop between the host's save and its next `next` leaves the stop action with no packet; the flow
        names its stage from the ledger's current action, not '?'."""
        seeded = self.seed()
        self.fake(seeded, "late-packet")
        state = step_slice.read_state(Path(seeded["run_dir"]))
        stop = step_slice.navigator.current_action(state)["id"]
        self.assertFalse((Path(seeded["run_dir"]) / "packets" / (stop + ".md")).exists())  # the race this pins
        found = flow.write(self.out)
        self.assertEqual((found["actions"][-1]["action"], found["actions"][-1]["stage"]), (stop, "system-test-author"))


if __name__ == "__main__":
    unittest.main()
