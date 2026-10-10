#!/usr/bin/env python3
"""Step slices (test/shiploop_e2e/slice.py), no model: the seed, the stop, the grade and the packet archive.

A fake host stands in for the model. It is a script that reprints each packet through the real CLI's `next`, moves the
seeded run through the item's inner loop with the navigator's own API (the seed's pattern), commits a product change
at implement, and then keeps running as a model would. The slice stop must end it once the item's inner loop is over,
must not be resumed, and must report an overrun (a host that accepted an outer stage before the poll saw the stop).
The fake commits its change; a model leaves it assembled and uncommitted, which the slice grades the same way.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import clear  # noqa: E402
import flow  # noqa: E402
import metrics  # noqa: E402
import packets  # noqa: E402
import run  # noqa: E402
import slice as step_slice  # noqa: E402

CLI = ROOT / "skills" / "shiploop" / "scripts" / "shiploop"
GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
IDENTITY = ["-c", "user.name=Fake host", "-c", "user.email=fake-host@example.invalid"]

# argv: scripts dir, CLI, run dir, mode (normal | overrun | grow). Prints nothing: the harness reads files only.
FAKE_HOST = textwrap.dedent('''
    import json, subprocess, sys, time
    from pathlib import Path
    scripts, cli, run_dir, mode = sys.argv[1:5]
    pause_at = sys.argv[5] if len(sys.argv) > 5 else ""
    paused = set()
    sys.path.insert(0, scripts)
    import shiploop_navigator as nav, shiploop_stage_spec as spec, shiploop_store as store
    run_dir = Path(run_dir)
    worktree = run_dir.parent / "worktree"
    git = ["git", "-C", str(worktree), "-c", "user.name=Fake host", "-c", "user.email=fake-host@example.invalid"]
    extra_outer = 2 if mode == "overrun" else 0
    while True:
        subprocess.run([sys.executable, cli, "next", f"--run-dir={run_dir}"], capture_output=True)  # emit the packet
        state = store.read_record(run_dir / "state.md")
        stage = nav.current_stage(state)
        past = state["status"] != "active" or state["work_index"] > 0 or stage in spec.OUTER
        if past and extra_outer == 0:
            break
        if past:
            extra_outer -= 1
        action = nav.current_action(state)["id"]
        if stage == pause_at and action not in paused:
            paused.add(action)
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
        nav.save(run_dir, state)
        time.sleep(0.02)
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

    def fake(self, seeded: dict, mode: str, *, pause_at: str = "", clear_at: dict | None = None,
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
        self.assertGreaterEqual(len(archived), 17)  # every inner stage reprinted at least once
        report = packets.write_report(self.out)
        self.assertEqual(report["emissions_source"].split()[0], "packet-archive")
        stages = {row["stage"] for row in report["packets"]}
        self.assertTrue({"step-plan", "implement", "carry-forward"} <= stages, stages)
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
        self.assertEqual(sorted(f["kind"] for f in found), ["test", "write"])

    def test_a_test_rerun_after_a_change_is_legitimate_and_without_one_is_redone(self):
        test = {"call": "npm test 2>&1 | tail -3", "result": "pass 9"}
        self.assertEqual(self.redone([test], [self.WRITE, test]), [])
        self.assertEqual([f["kind"] for f in self.redone([test], [test])], ["test"])

    def test_read_only_orientation_never_counts(self):
        rows = [{"call": "python3 /p/scripts/shiploop next --run-dir /r", "result": "ShipLoop navigator | implement | revision 3"},
                {"call": "cat /r/packets/nav-1.md; git status --short; git diff", "result": "..."}]
        self.assertEqual(self.redone(rows, rows), [])

    def test_a_repeated_callback_for_the_same_action_is_redone(self):
        done = {"call": "python3 /p/scripts/shiploop complete --run-dir=/r --action=nav-" + "a" * 32 + " --result=/r/x.md",
                "result": "ShipLoop navigator | test-green | revision 4"}
        self.assertEqual([f["kind"] for f in self.redone([done], [done])], ["callback"])


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


class ClearProbeTests(SliceCase):
    def test_a_clear_at_the_boundary_records_the_stop_and_a_fresh_session_finishes_the_slice(self):
        seeded = self.seed()
        first = self.fake(seeded, "normal", pause_at="implement", clear_at={"stage": "implement", "inside": False})
        self.assertEqual(first["status"], "cleared")
        record = json.loads((self.out / step_slice.CLEAR_RECORD).read_text())
        self.assertEqual(record["stopped"]["stage"], "implement")
        self.assertEqual(record["triggered"]["action"], record["stopped"]["action"])
        second = self.fake(seeded, "normal", first=False)  # the fresh session: the fake reads the packet again
        self.assertEqual(second["status"], "slice-complete")
        result = step_slice.grade(self.out, Path(seeded["run_dir"]), seeded, CASE, [first, second])
        self.assertTrue(result["verdicts"]["no_redo"])  # the fake's stream holds no calls: nothing to redo
        self.assertTrue(result["pass"], result["verdicts"])


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


if __name__ == "__main__":
    unittest.main()
