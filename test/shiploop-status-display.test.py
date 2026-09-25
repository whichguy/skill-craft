#!/usr/bin/env python3
"""ShipLoop's user-facing status block, status.md, `status` verb and Claude Code hook.

Synthetic protocol tests: runs are built in memory with the pure navigator API;
no Improve runtime, repository command or project check is started.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import shiploop_navigator as navigator  # noqa: E402
import shiploop_navigator_v3_prompts as prompts  # noqa: E402
import shiploop_status_hook as hook  # noqa: E402

BEGIN, END = navigator.STATUS_BEGIN, navigator.STATUS_END
DONE, NOW, TODO = "✓", "▶", "·"
HOOK = SCRIPTS / "shiploop-status-hook"
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


def result(*, outcome: str = "done", summary: str = "Synthetic producer result.", **extra):
    return {"outcome": outcome, "summary": summary, **extra}


def receipt(stage: str) -> dict:
    return {
        "summary": f"Synthetic Improve completion for {stage}.",
        "review_refs": [f"synthetic://review/{stage}"],
        "check_refs": [f"synthetic://check/{stage}"],
        "lessons": f"Keep the verified learning from {stage}.",
    }


def line(block: str, label: str) -> str:
    return next(row for row in block.splitlines() if row.startswith(label + ":"))


class StatusBlockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-status-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "project"
        self.repo.mkdir()

    def state(self) -> dict:
        return navigator.new_state(str(self.repo), "Add a --version flag.", improve_skill="")

    def act(self, state: dict, **extra) -> dict:
        return navigator.apply(state, navigator.current_action(state)["id"], result(**extra))

    def produce(self, state: dict, **extra) -> dict:
        """Accept the current producer, importing its Improve child when it has one."""
        action = navigator.current_action(state)["id"]
        stage = navigator.current_stage(state)
        after = self.act(state, **extra)
        if after.get("active_improve") is None:
            return after
        return navigator.finish_improve(after, action, receipt(stage),
                                        result(**extra) if extra else None)

    def advance_to(self, state: dict, stage: str) -> dict:
        while navigator.current_stage(state) != stage:
            state = self.produce(state)
        return state

    def planned(self, rows: list[dict]) -> dict:
        state = self.advance_to(self.state(), "plan")
        return self.produce(state, work_items=rows)

    ROWS = [{"id": "W1", "title": "Config loader refactor"},
            {"id": "W2", "title": "Add --version flag",
             "context": "Wire --version into cli.py. Keep help text short."}]

    # --- catalog -----------------------------------------------------------

    def test_catalog_covers_every_stage_and_groups_inner_in_order(self) -> None:
        self.assertEqual(set(prompts.STAGE_PURPOSE), set(prompts.STAGES))
        self.assertEqual(tuple(s for _, group in prompts.INNER_GROUPS for s in group), prompts.INNER)
        self.assertEqual([name for name, _ in prompts.INNER_GROUPS],
                         ["Plan", "Tests first", "Build", "Check", "Integrate"])
        for stage, purpose in prompts.STAGE_PURPOSE.items():
            self.assertTrue(purpose and len(purpose) <= 80 and "\n" not in purpose, stage)

    # --- rendering by run position -----------------------------------------

    def test_fresh_intake_block(self) -> None:
        self.assertEqual(navigator.status_block(self.state()), "\n".join([
            BEGIN,
            "Where:     Preparation > intake (1 of 7)",
            f"Run:       Preparation {NOW} | Work items 0/1 {TODO} | Release {TODO}",
            f"Stages:    intake {NOW} discovery {TODO} research {TODO} spec {TODO} "
            f"test-strategy {TODO} plan {TODO} prepare {TODO}",
            "Done:      nothing yet; the run has just started",
            "Next:      intake: " + prompts.STAGE_PURPOSE["intake"],
            END,
        ]))

    def test_preparation_progress_and_parked_then_imported_improve(self) -> None:
        state = self.advance_to(self.state(), "spec")
        block = navigator.status_block(state)
        self.assertIn(f"intake {DONE} discovery {DONE} research {DONE} spec {NOW} test-strategy {TODO}",
                      block)
        self.assertEqual(line(block, "Done"), "Done:      research: Synthetic producer result.")

        action = navigator.current_action(state)["id"]
        parked = self.act(state, summary="Spec drafted with 6 criteria. More detail follows.")
        block = navigator.status_block(parked)
        self.assertEqual(line(block, "Where"), "Where:     Preparation > spec (4 of 7, Improve review)")
        self.assertEqual(line(block, "Done"), "Done:      spec result ready: Spec drafted with 6 criteria.")
        self.assertEqual(line(block, "Next"), "Next:      Improve review of the spec result "
                                              "(the Improve skill runs its own review loop)")

        imported = navigator.finish_improve(parked, action, receipt("spec"))
        block = navigator.status_block(imported)
        self.assertEqual(line(block, "Done"),
                         "Done:      spec (reviewed by Improve): Spec drafted with 6 criteria.")
        self.assertEqual(line(block, "Next"),
                         "Next:      test-strategy: " + prompts.STAGE_PURPOSE["test-strategy"])

    def test_work_item_map_item_plan_and_completed_items(self) -> None:
        state = self.planned(self.ROWS)
        state = self.advance_to(state, "select-work")
        block = navigator.status_block(state)
        self.assertEqual(line(block, "Where"),
                         'Where:     Work items > W1 "Config loader refactor" (1 of 2) > Plan > select-work')
        self.assertEqual(line(block, "Run"),
                         f"Run:       Preparation {DONE} | Work items 0/2 {NOW} | Release {TODO}")
        self.assertEqual(line(block, "Item"),
                         f"Item:      Plan {NOW} | Tests first {TODO} | Build {TODO} | "
                         f"Check {TODO} | Integrate {TODO}")
        self.assertNotIn("Item plan:", block)  # neither a step plan nor item context yet

        state = self.produce(self.advance_to(state, "step-plan"),
                             summary="Split loader into parse and merge; cover both in test_config.py. Then more.")
        state = self.advance_to(state, "test-author")
        block = navigator.status_block(state)
        self.assertEqual(line(block, "Where"),
                         'Where:     Work items > W1 "Config loader refactor" (1 of 2) > Tests first > test-author')
        self.assertEqual(line(block, "Item"),
                         f"Item:      Plan {DONE} | Tests first {NOW} | Build {TODO} | "
                         f"Check {TODO} | Integrate {TODO}")
        self.assertEqual(line(block, "Item plan"),
                         "Item plan: Split loader into parse and merge; cover both in test_config.py.")
        self.assertEqual(line(block, "Next"), "Next:      test-author: " + prompts.STAGE_PURPOSE["test-author"])

        state = self.produce(self.advance_to(state, "carry-forward"),
                             summary="W1 merged into the worktree with 12 tests. Lessons noted.")
        block = navigator.status_block(state)
        self.assertEqual(line(block, "Where"),
                         'Where:     Work items > W2 "Add --version flag" (2 of 2) > Plan > select-work')
        self.assertEqual(line(block, "Done"),
                         "Done:      W1 carry-forward: W1 merged into the worktree with 12 tests.")
        self.assertEqual(line(block, "Completed"),
                         'Completed: 1 item; W1 "Config loader refactor": W1 merged into the worktree with 12 tests')
        # Before W2's step plan, the item context supplies the specific intent.
        self.assertEqual(line(block, "Item plan"), "Item plan: Wire --version into cli.py.")

    def test_release_stages_and_completion(self) -> None:
        state = self.planned(self.ROWS[:1])
        state = self.advance_to(state, "system-test")
        block = navigator.status_block(state)
        self.assertEqual(line(block, "Where"), "Where:     Release > system-test (2 of 9)")
        self.assertEqual(line(block, "Run"),
                         f"Run:       Preparation {DONE} | Work items 1/1 {DONE} | Release {NOW}")
        self.assertTrue(line(block, "Stages").startswith(
            f"Stages:    system-test-author {DONE} system-test {NOW} product-acceptance {TODO}"))
        while state["status"] != "done":
            state = self.produce(state)
        block = navigator.status_block(state)
        self.assertEqual(line(block, "Where"), "Where:     Run complete")
        self.assertEqual(line(block, "Run"),
                         f"Run:       Preparation {DONE} | Work items 1/1 {DONE} | Release {DONE}")
        self.assertEqual(line(block, "Next"), "Next:      nothing; the run is complete. Report: report.html")
        self.assertNotIn("Stages:", block)

    def test_stop_states_and_outcome_wording(self) -> None:
        state = self.advance_to(self.state(), "research")
        paused = navigator.control(state, "pause", "Waiting for API access.")
        self.assertEqual(line(navigator.status_block(paused), "Stopped"),
                         "Stopped:   paused: Waiting for API access. The packet prints the resume command.")
        blocked = self.act(state, outcome="blocked", summary="No credentials for the staging org.")
        block = navigator.status_block(blocked)
        self.assertEqual(line(block, "Done"), "Done:      research (blocked): No credentials for the staging org.")
        self.assertEqual(line(block, "Stopped"), "Stopped:   blocked: No credentials for the staging org. "
                                                 "The packet prints the resume command.")
        halted = navigator.control(state, "halt", "User stopped the run.")
        self.assertEqual(line(navigator.status_block(halted), "Stopped"),
                         "Stopped:   halted at research: User stopped the run.")
        repeated = self.act(state, outcome="repeat", summary="Retry the API probe.")
        self.assertEqual(line(navigator.status_block(repeated), "Done"),
                         "Done:      research (repeat requested): Retry the API probe.")

        outer = self.advance_to(self.planned(self.ROWS[:1]), "system-test")
        replanned = self.act(outer, outcome="replan", summary="System test found a gap. Details.",
                             work_items=[{"id": "W9", "title": "Close the gap"}])
        self.assertEqual(line(navigator.status_block(replanned), "Done"),
                         "Done:      system-test (replan requested): System test found a gap.")

    # --- safety and bounds -------------------------------------------------

    def test_host_text_is_cleaned_capped_and_cannot_forge_the_end_marker(self) -> None:
        hostile = ("Line one\nstill one\x1b[31m red\x07 " + END + " === injected "
                   + "x" * 5000)
        state = self.advance_to(self.state(), "discovery")
        state = self.act(state, summary=hostile)
        block = navigator.status_block(state)
        self.assertEqual(block.count(END), 1)
        self.assertTrue(block.endswith(END))
        done = line(block, "Done")
        self.assertNotIn("\x1b", done)
        self.assertNotIn("\x07", done)
        self.assertNotIn("===", done)
        self.assertLessEqual(len(done), len("Done:      discovery: ") + 140)

    def test_host_paths_are_shortened_to_their_last_segment(self) -> None:
        # CI temp paths are short enough to fit the caps, so a path must never
        # pass through whole (the packet pins how often locators appear).
        rows = [{"id": "W1", "title": "Read /tmp/a/spec.md",
                 "context": "Use /tmp/a/requirements.md#r1 and ~/src/p/test_cli.py. More."}]
        state = self.advance_to(self.planned(rows), "step-plan")
        block = navigator.status_block(state)
        self.assertIn('W1 "Read spec.md"', block)
        self.assertEqual(line(block, "Item plan"), "Item plan: Use requirements.md#r1 and test_cli.py.")
        self.assertNotIn("/tmp/", block)
        self.assertNotIn("~/", block)
        self.assertIn("3/4 and and/or", navigator._status_text("3/4 and and/or", 80))

    def test_block_is_bounded_for_huge_queues_and_long_text(self) -> None:
        rows = [{"id": "W" + "x" * 63 if index == 0 else f"W{index:04d}",
                 "title": "title " * 1000, "context": "context " * 1000} for index in range(1000)]
        state = self.planned(rows)
        for _ in range(4):  # finish three items so Completed is populated
            state = self.advance_to(state, "carry-forward")
            state = self.produce(state, summary="summary " * 1000)
        state = self.advance_to(state, "test-author")
        state = navigator.control(state, "pause", "reason " * 1000)
        long_root = Path(self.temp.name) / ("deep" * 100)
        block = navigator.status_block(state)
        rows_out = block.splitlines()
        self.assertLessEqual(len(rows_out), 11)
        self.assertLess(len(block), 1500)
        self.assertIn("(1 earlier not shown)", block)
        self.assertNotIn(str(long_root), block)
        self.assertNotIn(str(self.repo), block)
        self.assertNotIn("shiploop ", block.replace("ShipLoop status", ""))

    # --- packet placement, status.md and the status verb --------------------

    def test_packet_carries_block_early_and_status_file_matches_cli(self) -> None:
        state = self.advance_to(self.planned(self.ROWS), "test-red")
        root = (Path(self.temp.name) / "run").resolve()
        root.mkdir()
        navigator.save(root, state)
        block = navigator.status_block(state)
        packet = navigator.render(None, root, state)
        self.assertEqual(packet.count(BEGIN), 1)
        self.assertIn(block, packet)
        header = packet.index("ShipLoop navigator | ")
        self.assertLess(header, packet.index(BEGIN))
        self.assertLess(packet.index("Progress snapshot"), packet.index(BEGIN))
        self.assertLess(packet.index(END), hook.WINDOW)
        self.assertEqual((root / "status.md").read_text(encoding="utf-8"),
                         "```text\n" + block + "\n```\n")

        def files() -> dict:
            # The run lock file is created empty by any locked verb; it holds no content.
            return {path: path.read_bytes() for path in root.rglob("*")
                    if path.is_file() and path.name != ".lock"}

        before = files()
        cli = [sys.executable, "-B", str(SCRIPTS / "shiploop")]
        status = subprocess.run(cli + ["status", "--run-dir", str(root)], env=ENV,
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(status.stdout, block + "\n")
        nxt = subprocess.run(cli + ["next", "--run-dir", str(root)], env=ENV,
                             text=True, capture_output=True, timeout=30)
        self.assertEqual(nxt.returncode, 0, nxt.stderr)
        self.assertEqual(files(), before)

    def test_every_dry_run_packet_carries_the_block_inside_the_kept_head(self) -> None:
        for delegation in prompts.DELEGATIONS:
            completed = subprocess.run(
                [sys.executable, "-B", str(SCRIPTS / "shiploop"), "graph-dry-run",
                 "--scenario", "all", "--format", "json", "--delegation", delegation],
                env=ENV, text=True, capture_output=True, timeout=120)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            for scenario in json.loads(completed.stdout)["scenarios"]:
                for event in scenario["events"]:
                    packet = event["prompt"]
                    with self.subTest(delegation=delegation, scenario=scenario["name"],
                                      sequence=event["sequence"]):
                        self.assertEqual(packet.count(BEGIN), 1)
                        self.assertLess(packet.index(END), hook.WINDOW)


class StatusHookTests(unittest.TestCase):
    """The hook shows only a real ShipLoop call's own block; it never fails a call."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="shiploop-status-hook-")
        repo = Path(cls.temp.name) / "project"
        repo.mkdir()
        cls.run_dir = (Path(cls.temp.name) / "run").resolve()
        cls.cli = str(SCRIPTS / "shiploop")
        init = subprocess.run(
            [sys.executable, "-B", cls.cli, "init", f"--repo={repo}", f"--run-dir={cls.run_dir}",
             "--prompt=Add a --version flag."], env=ENV, text=True, capture_output=True, timeout=30)
        assert init.returncode == 0, init.stderr
        cls.packet = init.stdout
        cls.block = cls.packet[cls.packet.index(BEGIN):cls.packet.index(END) + len(END)]
        cls.command = f"python3 {cls.cli} next --run-dir={cls.run_dir}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def payload(self, command: str, stdout: str, **response) -> dict:
        return {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                "tool_input": {"command": command, "description": "x"},
                "tool_response": {"stdout": stdout, "stderr": "", "interrupted": False,
                                  "isImage": False, **response}}

    def run_hook(self, stdin: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([str(HOOK)], input=stdin, env=ENV, text=True,
                              capture_output=True, timeout=30)

    def test_real_calls_emit_the_scripts_own_block(self) -> None:
        wrapper = str(SCRIPTS / "shiploop-complete")
        cases = {
            "next": (self.command, self.packet),
            "status": (f"{self.cli} status --run-dir {self.run_dir}", self.block + "\n"),
            "env-and-quotes": (f'PYTHONDONTWRITEBYTECODE=1 python3 "{self.cli}" next --run-dir "{self.run_dir}"',
                               self.packet),
            "workspace": (f"python3 {self.cli} workspace start --repo=/r --workspace-root=/w --prompt='x'",
                          self.packet),
            "wrapper": (f"{wrapper} --run-dir={self.run_dir} --action=a --result=r",
                        "shiploop complete — close the increment and print the next stdout\n" + self.packet),
            # Claude Code keeps the head of oversized output and persists the rest.
            "truncated": (self.command, (self.packet * 3)[:30000]),
        }
        for label, (command, stdout) in cases.items():
            with self.subTest(label):
                extra = ({"persistedOutputPath": "/tmp/x.txt", "persistedOutputSize": 90000}
                         if label == "truncated" else {})
                completed = self.run_hook(json.dumps(self.payload(command, stdout, **extra)))
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(json.loads(completed.stdout), {"systemMessage": self.block})

    def test_host_payload_shapes(self) -> None:
        """Claude and Codex display; Grok and Cursor are recognized but cannot display."""
        cat = f"cat {self.run_dir}/status.md"
        shapes = {
            "codex": lambda command, out: {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                                           "tool_input": {"command": command},
                                           "tool_response": {"output": out}},
            "grok": lambda command, out: {"hookEventName": "PostToolUse", "toolName": "run_terminal_command",
                                          "toolInput": {"command": command},
                                          "toolResult": {"command": command, "exit_code": 0,
                                                         "output_for_prompt": out}},
            "cursor": lambda command, out: {"hook_event_name": "afterShellExecution",
                                            "command": command, "output": out, "duration": 5},
        }
        expected_host = {"codex": "claude-or-codex", "grok": "grok", "cursor": "cursor"}
        for name, shape in shapes.items():
            with self.subTest(host=name):
                self.assertEqual(hook.status_block(shape(self.command, self.packet)),
                                 (expected_host[name], self.block))
                self.assertIsNone(hook.status_block(shape(cat, self.block)))
                self.assertIsNone(hook.status_block(shape(self.command + " | head", self.packet)))
                completed = self.run_hook(json.dumps(shape(self.command, self.packet)))
                self.assertEqual(completed.returncode, 0, completed.stderr)
                if name == "codex":
                    self.assertEqual(json.loads(completed.stdout), {"systemMessage": self.block})
                else:
                    self.assertEqual(completed.stdout, "")

    def test_lookalike_or_unsafe_calls_stay_silent(self) -> None:
        status_md = f"{self.run_dir}/status.md"
        cases = {
            "cat": self.payload(f"cat {status_md}", self.block),
            "grep": self.payload(f"grep -r 'ShipLoop status' {self.run_dir}", self.block),
            "echo": self.payload("echo '" + self.block + "'", self.block),
            "piped": self.payload(self.command + " | head -50", self.packet),
            "redirect": self.payload(self.command + " 2>&1", self.packet),
            "chained": self.payload(self.command + " && echo ok", self.packet),
            "other-script": self.payload(f"python3 /tmp/scripts/other next", self.packet),
            "not-scripts-dir": self.payload(f"python3 /tmp/shiploop next", self.packet),
            "report-verb": self.payload(f"python3 {self.cli} report --run-dir={self.run_dir}", self.packet),
            "no-header": self.payload(self.command, "noise\n" + self.packet),
            "missing-end": self.payload(self.command, self.packet.replace(END, "")),
            "late-end": self.payload(self.command, self.packet.replace(
                "\n" + BEGIN, "\n" + "x" * hook.WINDOW + "\n" + BEGIN)),
            "two-blocks": self.payload(self.command, self.packet.replace(
                BEGIN, self.block + "\n" + BEGIN, 1)),
            "background": self.payload(self.command, "", backgroundTaskId="b1"),
            "other-tool": dict(self.payload(self.command, self.packet), tool_name="Read"),
        }
        for label, payload in cases.items():
            with self.subTest(label):
                completed = self.run_hook(json.dumps(payload))
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(completed.stdout, "")
        for label, stdin in {"bad-json": "{not json " + BEGIN, "empty": "",
                             "unrelated": json.dumps(self.payload("ls", "a\nb"))}.items():
            with self.subTest(label):
                completed = self.run_hook(stdin)
                self.assertEqual((completed.returncode, completed.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
