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

    def fake(self, seeded: dict, mode: str) -> dict:
        script = self.out / "fake_host.py"
        script.write_text(FAKE_HOST)
        argv = [sys.executable, str(script), str(CLI.parent), str(CLI), seeded["run_dir"], mode]
        started = time.time()
        process = step_slice.drive(argv, work=self.work, out=self.out, env=GIT_ENV, run_dir=Path(seeded["run_dir"]),
                                   timeout=90, watch=False)
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


if __name__ == "__main__":
    unittest.main()
