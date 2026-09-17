#!/usr/bin/env python3
"""Acceptance coverage for ShipLoop's environment-lifecycle packet policy.

The navigator retains its existing graph and result shape.  These tests use
ordinary synthetic host results only to exercise public API and CLI routing;
they do not perform sandbox setup, code changes, or staging validation.
"""

from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PACKAGE = ROOT / "skills" / "shiploop"
SOURCE_SCRIPTS = SOURCE_PACKAGE / "scripts"
if str(SOURCE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SOURCE_SCRIPTS))

import shiploop_navigator as navigator  # noqa: E402
import shiploop_store as store  # noqa: E402


POLICY_LABEL = "Environment lifecycle policy: "
NOTE_LABEL = "Environment lifecycle note (host-authored, if present): "
LIFECYCLE_NOTE = "notes/environment-lifecycle.md"
PRELUDE = (
    "intake",
    "discovery",
    "research",
    "research-improve",
    "spec",
    "spec-improve",
    "test-strategy",
    "plan",
    "plan-improve",
)
INNER = (
    "step-plan",
    "step-plan-improve",
    "implement",
    "test-refine",
    "test-author",
    "document",
    "skill-validate",
    "verify",
    "product-improve",
    "integrate",
    "carry-forward",
)
INNER_WITHOUT_SKILL_VALIDATE = tuple(
    stage for stage in INNER if stage != "skill-validate"
)
OUTER = (
    "system-test",
    "outer-improve",
    "release-plan",
    "release",
    "release-verify",
    "handoff",
)


class EnvironmentLifecycleNavigatorTests(unittest.TestCase):
    """Exercise durable work-item ordering through the public navigator surface."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-environment-lifecycle-")
        self.base = Path(self.temp.name)
        self.package = self.base / "relocated ShipLoop package"
        shutil.copytree(
            SOURCE_PACKAGE,
            self.package,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
        )
        self.cli = (self.package / "scripts" / "shiploop").resolve()
        self.policy_reference = (
            self.package / "references" / "environment-lifecycle.md"
        ).resolve()
        self.repo = self.base / "ordinary repository"
        self.repo.mkdir()
        self.unrelated_cwd = self.base / "unrelated cwd"
        self.unrelated_cwd.mkdir()
        self.environment = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def _current_action(state: dict) -> dict:
        if (
            state["navigator_protocol_version"] == 2
            and state["stage"] == "inner-loop"
        ):
            owner = state["work_items"][state["work_index"]]["id"]
            return state["inner_loops"][owner]["action"]
        return state["action"]

    def _run(
        self, argv: list[str], *, expected: int | None = 0
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            argv,
            cwd=self.unrelated_cwd,
            env=self.environment,
            text=True,
            capture_output=True,
            timeout=30,
        )
        if expected is not None:
            self.assertEqual(
                completed.returncode,
                expected,
                completed.stdout + completed.stderr,
            )
        return completed

    def _assert_policy(self, packet: str, run_dir: Path) -> None:
        expected = POLICY_LABEL + str(self.policy_reference)
        self.assertEqual(packet.count(expected), 1, expected)
        self.assertEqual(packet.count(POLICY_LABEL), 1, POLICY_LABEL)
        expected_note = NOTE_LABEL + str((run_dir / LIFECYCLE_NOTE).resolve())
        self.assertEqual(packet.count(expected_note), 1, expected_note)
        self.assertEqual(packet.count(NOTE_LABEL), 1, NOTE_LABEL)
        self.assertNotIn(
            POLICY_LABEL
            + str(
                (SOURCE_PACKAGE / "references" / "environment-lifecycle.md").resolve()
            ),
            packet,
        )

    def _cli(self, run_dir: Path, *args: str) -> str:
        packet = self._run(
            [
                sys.executable,
                "-B",
                str(self.cli),
                *args,
                "--run-dir",
                str(run_dir),
            ]
        ).stdout
        self._assert_policy(packet, run_dir)
        return packet

    def _start(self, run_dir: Path, protocol_version: int) -> str:
        args = [
            "init",
            "--repo",
            str(self.repo),
            "--prompt",
            "Exercise durable sandbox, feature, and staging lifecycle ordering.",
        ]
        if protocol_version == 1:
            args.append("--execution-mode=navigator-v1")
        return self._cli(run_dir, *args)

    @staticmethod
    def _state(run_dir: Path) -> dict:
        return store.read_record(run_dir / "state.md")

    @staticmethod
    def _result(stage: str, *, outcome: str = "done", **extra) -> dict:
        return {
            "outcome": outcome,
            "summary": f"Synthetic lifecycle result recorded for {stage}.",
            **extra,
        }

    def _cold_packet(self, run_dir: Path) -> str:
        before = (run_dir / "state.md").read_bytes()
        packet = self._cli(run_dir, "next")
        self.assertEqual((run_dir / "state.md").read_bytes(), before)
        return packet

    def _submit(self, run_dir: Path, packet: str, result: dict) -> str:
        state = self._state(run_dir)
        action = self._current_action(state)
        callback = Path(
            packet.split("Write the structured result to: ", 1)[1].splitlines()[0]
        )
        self.assertEqual(
            callback,
            run_dir.resolve() / "inbox" / f"{action['id']}.md",
        )
        command = shlex.split(
            packet.split("Call this when done:\n", 1)[1].splitlines()[0]
        )
        self.assertEqual(command[0], "python3")
        self.assertEqual(Path(command[1]).resolve(), self.cli)
        self.assertEqual(command.count("--action=" + action["id"]), 1)
        callback.write_text(
            store.dumps(result, "Synthetic environment-lifecycle callback"),
            encoding="utf-8",
        )
        next_packet = self._run([sys.executable, "-B", *command[1:]]).stdout
        self._assert_policy(next_packet, run_dir)
        return next_packet

    def _lifecycle_work_items(self, run_dir: Path) -> list[dict[str, str]]:
        note = run_dir / LIFECYCLE_NOTE
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text(
            "# Environment lifecycle\n\n"
            "This durable note records the preparation, feature, and staging "
            "lifecycle for the selected candidate.\n",
            encoding="utf-8",
        )
        return [
            {
                "id": "PREP",
                "title": "Sandbox preparation",
                "context": (
                    "Complete bounded sandbox preparation and retain its result in "
                    + LIFECYCLE_NOTE
                    + "."
                ),
            },
            {
                "id": "FEATURE",
                "title": "Feature code",
                "context": (
                    "Use the completed preparation record in "
                    + LIFECYCLE_NOTE
                    + " before changing feature code."
                ),
            },
            {
                "id": "STAGE",
                "title": "Candidate staging validation",
                "context": (
                    "Record candidate staging validation in "
                    + LIFECYCLE_NOTE
                    + " before outer verification and release work."
                ),
            },
        ]

    def _reach_plan(self, run_dir: Path, protocol_version: int) -> str:
        packet = self._start(run_dir, protocol_version)
        for stage in PRELUDE:
            state = self._state(run_dir)
            action = self._current_action(state)
            self.assertEqual((action["stage"], state["status"]), (stage, "active"))
            if stage == "plan":
                return packet
            packet = self._submit(
                run_dir,
                self._cold_packet(run_dir),
                self._result(stage),
            )
        self.fail("navigator did not reach the plan action")

    def _start_lifecycle(self, run_dir: Path, protocol_version: int) -> tuple[str, list[dict[str, str]]]:
        self._reach_plan(run_dir, protocol_version)
        work_items = self._lifecycle_work_items(run_dir)
        plan_state = self._state(run_dir)
        plan_action = self._current_action(plan_state)
        packet = self._submit(
            run_dir,
            self._cold_packet(run_dir),
            self._result(
                "plan",
                work_items=work_items,
                evidence_refs=[LIFECYCLE_NOTE],
            ),
        )
        after_plan = self._state(run_dir)
        self.assertEqual(after_plan["accepted"][plan_action["id"]]["work_items"], work_items)
        self.assertEqual(after_plan["work_items"], work_items)
        self.assertEqual(
            [item["id"] for item in after_plan["work_items"]],
            ["PREP", "FEATURE", "STAGE"],
        )
        self.assertTrue(
            all(LIFECYCLE_NOTE in item["context"] for item in after_plan["work_items"])
        )
        self.assertTrue((run_dir / LIFECYCLE_NOTE).is_file())
        self.assertEqual(self._current_action(after_plan)["stage"], "plan-improve")
        packet = self._submit(
            run_dir,
            self._cold_packet(run_dir),
            self._result("plan-improve", evidence_refs=[LIFECYCLE_NOTE]),
        )
        started = self._state(run_dir)
        self.assertEqual((self._current_action(started)["stage"], started["status"]), ("step-plan", "active"))
        self.assertEqual(
            started["work_items"][started["work_index"]]["id"], "PREP"
        )
        return packet, work_items

    def _complete_current_item(
        self,
        run_dir: Path,
        expected_item: str,
        *,
        stages: tuple[str, ...] = INNER_WITHOUT_SKILL_VALIDATE,
        include_note_refs: bool = True,
    ) -> str:
        packet = ""
        for stage in stages:
            state = self._state(run_dir)
            action = self._current_action(state)
            self.assertEqual((action["stage"], state["status"]), (stage, "active"))
            self.assertEqual(
                state["work_items"][state["work_index"]]["id"], expected_item
            )
            result = self._result(stage)
            if include_note_refs:
                result["evidence_refs"] = [LIFECYCLE_NOTE]
            if stage == "document":
                result["choices"] = {"skill_required": False}
            packet = self._submit(run_dir, self._cold_packet(run_dir), result)
        return packet

    def _direct_to_prep(self, protocol_version: int) -> dict:
        state = navigator.new_state(
            str(self.repo),
            "Exercise navigator lifecycle result validation.",
            protocol_version=protocol_version,
        )
        for stage in PRELUDE:
            action = navigator.current_action(state)
            self.assertEqual(action["stage"], stage)
            result = self._result(stage)
            if stage == "plan":
                result["work_items"] = self._lifecycle_work_items(self.base / "api run")
            state = navigator.apply(state, action["id"], result)
        self.assertEqual(navigator.current_stage(state), "step-plan")
        return state

    def test_relocated_package_exposes_the_environment_lifecycle_reference(self) -> None:
        self.assertTrue(self.policy_reference.is_file())

    def test_v1_and_v2_complete_ordered_prep_feature_stage_before_outer_work(self) -> None:
        """Cold CLI packets retain the relocated policy across the full lifecycle."""
        for protocol_version in (1, 2):
            with self.subTest(protocol_version=protocol_version):
                run_dir = self.base / f"lifecycle v{protocol_version} run"
                packet, _work_items = self._start_lifecycle(run_dir, protocol_version)

                packet = self._complete_current_item(run_dir, "PREP")
                after_prep = self._state(run_dir)
                self.assertEqual(after_prep["completed_work_items"], ["PREP"])
                self.assertEqual(
                    after_prep["work_items"][after_prep["work_index"]]["id"],
                    "FEATURE",
                )
                self.assertEqual(self._current_action(after_prep)["stage"], "step-plan")
                self.assertIn(LIFECYCLE_NOTE, packet)

                packet = self._complete_current_item(
                    run_dir, "FEATURE", include_note_refs=False
                )
                after_feature = self._state(run_dir)
                self.assertEqual(after_feature["completed_work_items"], ["PREP", "FEATURE"])
                self.assertEqual(
                    after_feature["work_items"][after_feature["work_index"]]["id"],
                    "STAGE",
                )
                self.assertEqual(self._current_action(after_feature)["stage"], "step-plan")
                self.assertIn(LIFECYCLE_NOTE, packet)

                packet = self._complete_current_item(
                    run_dir, "STAGE", include_note_refs=False
                )
                after_stage = self._state(run_dir)
                self.assertEqual(
                    after_stage["completed_work_items"], ["PREP", "FEATURE", "STAGE"]
                )
                self.assertEqual(
                    (self._current_action(after_stage)["stage"], after_stage["status"]),
                    ("system-test", "active"),
                )
                self.assertEqual(
                    after_stage["accepted"][after_stage["history"][-1]["action"]][
                        "evidence_refs"
                    ],
                    [],
                )
                self.assertIn(LIFECYCLE_NOTE, packet)
                note = run_dir / LIFECYCLE_NOTE
                note_bytes = note.read_bytes()
                cold_system_test = self._cold_packet(run_dir)
                self.assertIn(
                    NOTE_LABEL + str((run_dir / LIFECYCLE_NOTE).resolve()),
                    cold_system_test,
                )
                self.assertTrue(note.is_file())
                self.assertEqual(note.read_bytes(), note_bytes)

                for stage in OUTER:
                    state = self._state(run_dir)
                    self.assertEqual(self._current_action(state)["stage"], stage)
                    cold = self._cold_packet(run_dir)
                    if stage == "release-plan":
                        self.assertEqual(
                            state["accepted"][state["history"][-1]["action"]][
                                "evidence_refs"
                            ],
                            [],
                        )
                        self.assertIn(
                            NOTE_LABEL + str((run_dir / LIFECYCLE_NOTE).resolve()),
                            cold,
                        )
                        self.assertTrue(note.is_file())
                        self.assertEqual(note.read_bytes(), note_bytes)
                    packet = self._submit(
                        run_dir,
                        cold,
                        self._result(stage),
                    )

                final = self._state(run_dir)
                self.assertEqual((final["stage"], final["status"]), ("done", "done"))
                self.assertEqual(
                    [
                        entry["workitem"]
                        for entry in final["history"]
                        if entry["stage"] == "carry-forward"
                    ],
                    ["PREP", "FEATURE", "STAGE"],
                )
                stages = [entry["stage"] for entry in final["history"]]
                stage_complete_index = max(
                    index
                    for index, entry in enumerate(final["history"])
                    if entry["workitem"] == "STAGE"
                )
                for outer_stage in (
                    "system-test",
                    "release-plan",
                    "release",
                    "release-verify",
                ):
                    self.assertGreater(stages.index(outer_stage), stage_complete_index)
                self._assert_policy(packet, run_dir)

    def test_v1_and_v2_blocked_or_paused_prep_resume_the_same_item(self) -> None:
        """A prep blocker cannot advance to feature work before prep completes."""
        for protocol_version in (1, 2):
            with self.subTest(protocol_version=protocol_version):
                run_dir = self.base / f"blocked lifecycle v{protocol_version} run"
                self._start_lifecycle(run_dir, protocol_version)
                active = self._state(run_dir)
                active_action = self._current_action(active)
                self.assertEqual(active_action["stage"], "step-plan")
                self.assertEqual(active["work_items"][active["work_index"]]["id"], "PREP")

                paused_packet = self._cli(
                    run_dir,
                    "pause",
                    "--reason",
                    "Pause the current sandbox preparation without consuming it.",
                )
                paused = self._state(run_dir)
                paused_bytes = (run_dir / "state.md").read_bytes()
                self.assertEqual((paused["status"], self._current_action(paused)["id"]), ("paused", active_action["id"]))
                self.assertNotIn("Call this when done:", paused_packet)
                cold_paused = self._cli(run_dir, "next")
                self.assertNotIn("Call this when done:", cold_paused)
                self.assertEqual((run_dir / "state.md").read_bytes(), paused_bytes)

                resumed_packet = self._cli(run_dir, "resume")
                resumed = self._state(run_dir)
                self.assertEqual((resumed["status"], self._current_action(resumed)["id"]), ("active", active_action["id"]))
                self.assertIn(LIFECYCLE_NOTE, resumed_packet)

                blocked_packet = self._submit(
                    run_dir,
                    self._cold_packet(run_dir),
                    self._result(
                        "step-plan",
                        outcome="blocked",
                        evidence_refs=[LIFECYCLE_NOTE],
                    ),
                )
                blocked = self._state(run_dir)
                resumed_action = self._current_action(blocked)
                self.assertEqual(
                    (blocked["status"], resumed_action["stage"]), ("blocked", "step-plan")
                )
                self.assertNotEqual(resumed_action["id"], active_action["id"])
                self.assertEqual(blocked["work_items"][blocked["work_index"]]["id"], "PREP")
                self.assertNotIn("Call this when done:", blocked_packet)

                blocked_bytes = (run_dir / "state.md").read_bytes()
                cold_blocked = self._cli(run_dir, "next")
                self.assertNotIn("Call this when done:", cold_blocked)
                self.assertEqual((run_dir / "state.md").read_bytes(), blocked_bytes)
                resumed_packet = self._cli(run_dir, "resume")
                resumed = self._state(run_dir)
                self.assertEqual((resumed["status"], self._current_action(resumed)["id"]), ("active", resumed_action["id"]))
                self.assertIn(LIFECYCLE_NOTE, resumed_packet)

                self._submit(
                    run_dir,
                    self._cold_packet(run_dir),
                    self._result("step-plan", evidence_refs=[LIFECYCLE_NOTE]),
                )
                after_resumed_prep = self._state(run_dir)
                self.assertEqual(
                    self._current_action(after_resumed_prep)["stage"],
                    "step-plan-improve",
                )
                self.assertEqual(
                    after_resumed_prep["work_items"][after_resumed_prep["work_index"]]["id"],
                    "PREP",
                )

    def test_public_api_rejects_a_host_chosen_next_stage_from_prep(self) -> None:
        for protocol_version in (1, 2):
            with self.subTest(protocol_version=protocol_version):
                state = self._direct_to_prep(protocol_version)
                action = navigator.current_action(state)
                before = deepcopy(state)
                with self.assertRaisesRegex(
                    navigator.NavigatorError, "result has unsupported fields"
                ):
                    navigator.apply(
                        state,
                        action["id"],
                        self._result(
                            "step-plan",
                            next_stage="FEATURE",
                            evidence_refs=[LIFECYCLE_NOTE],
                        ),
                    )
                self.assertEqual(state, before)
                self.assertEqual(navigator.current_stage(state), "step-plan")

    def test_v1_and_v2_local_only_plan_does_not_invent_lifecycle_setup(self) -> None:
        """A single local item remains a single local item in the existing graph."""
        local_only = [{"id": "LOCAL", "title": "Make one local-only change"}]
        for protocol_version in (1, 2):
            with self.subTest(protocol_version=protocol_version):
                state = navigator.new_state(
                    str(self.repo),
                    "Make a local-only change without a sandbox or staging target.",
                    protocol_version=protocol_version,
                )
                for stage in PRELUDE:
                    action = navigator.current_action(state)
                    result = self._result(stage)
                    if stage == "plan":
                        result["work_items"] = local_only
                    state = navigator.apply(state, action["id"], result)

                self.assertEqual(state["work_items"], local_only)
                self.assertEqual(state["completed_work_items"], [])
                self.assertFalse((self.repo / LIFECYCLE_NOTE).exists())
                self.assertEqual(navigator.current_stage(state), "step-plan")
                for stage in INNER_WITHOUT_SKILL_VALIDATE:
                    action = navigator.current_action(state)
                    self.assertEqual(action["stage"], stage)
                    result = self._result(stage)
                    if stage == "document":
                        result["choices"] = {"skill_required": False}
                    state = navigator.apply(state, action["id"], result)
                self.assertEqual(state["completed_work_items"], ["LOCAL"])
                self.assertEqual(navigator.current_stage(state), "system-test")


if __name__ == "__main__":
    unittest.main()
