#!/usr/bin/env python3
"""Acceptance coverage for ShipLoop cross-run request and knowledge routing.

The public CLI remains the authority under test.  Synthetic navigator state is
used only to make one terminal fixture cheaply; it is not a claim that an LLM
read a prior document or performed an implementation.
"""

from __future__ import annotations

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


OLD_PROMPT = "Create the original checkers board."
NEW_PROMPT = "Add visual dragging while moving a checker."
THIRD_PROMPT = "Add keyboard navigation without changing legal-move rules."


class CrossRunTests(unittest.TestCase):
    """Keep a prior run intact while a later feature starts from new scope."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-cross-run-")
        self.base = Path(self.temp.name)
        self.package = self.base / "relocated ShipLoop package"
        shutil.copytree(
            SOURCE_PACKAGE,
            self.package,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
        )
        self.cli = (self.package / "scripts" / "shiploop").resolve()
        self.policy = (self.package / "references" / "project-knowledge.md").resolve()
        self.repo = self.base / "existing application"
        self.repo.mkdir()
        self.docs = self.repo / "docs"
        self.docs.mkdir()
        self.requirements = self.docs / "requirements.md"
        self.requirements.write_text(
            "# Maintained product requirements\n\n"
            "- Preserve legal checker moves and the existing win condition.\n",
            encoding="utf-8",
        )
        self.readme = self.repo / "README.md"
        self.readme.write_text(
            "# Existing application\n\n"
            "See [maintained requirements](docs/requirements.md).\n",
            encoding="utf-8",
        )
        self.environment = self.repo / "environment.md"
        self.environment.write_text(
            "# Environment\n\nThe existing app is hosted and has a local test command.\n",
            encoding="utf-8",
        )
        self.index = self.repo / "SHIPLOOP.md"
        self.index.write_text(
            "# Project knowledge\n\n"
            "- [Environment](environment.md)\n"
            "- Keep prior delivery records as history, not current scope.\n",
            encoding="utf-8",
        )
        self.other_repo = self.base / "another application"
        self.other_repo.mkdir()
        self.cwd = self.base / "unrelated cwd"
        self.cwd.mkdir()
        self.environment_vars = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _run(
        self, argv: list[str], *, expected: int | None = 0
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            argv,
            cwd=self.cwd,
            env=self.environment_vars,
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

    def _cli(
        self, run_dir: Path, *args: str, expected: int | None = 0
    ) -> subprocess.CompletedProcess[str]:
        return self._run(
            [
                sys.executable,
                "-B",
                str(self.cli),
                *args,
                "--run-dir",
                str(run_dir),
            ],
            expected=expected,
        )

    def _init(
        self,
        run_dir: Path,
        prompt: str = OLD_PROMPT,
        *,
        repo: Path | None = None,
        mode: str = "navigator-v2",
        expected: int | None = 0,
    ) -> subprocess.CompletedProcess[str]:
        return self._cli(
            run_dir,
            "init",
            "--repo",
            str(repo or self.repo),
            "--prompt",
            prompt,
            "--execution-mode=" + mode,
            expected=expected,
        )

    @staticmethod
    def _state(run_dir: Path) -> dict:
        return store.read_record(run_dir / "state.md")

    @staticmethod
    def _snapshot(run_dir: Path) -> dict[str, bytes]:
        """Capture every durable run file, excluding only a transient lock."""
        return {
            path.relative_to(run_dir).as_posix(): path.read_bytes()
            for path in sorted(run_dir.rglob("*"))
            if path.is_file() and path.name != ".lock"
        }

    def _assert_knowledge_locators(self, packet: str) -> None:
        policy = "Cross-run knowledge policy: " + str(self.policy)
        index = "Repository knowledge index (host-authored, if present): " + str(
            self.index.resolve()
        )
        self.assertTrue(self.policy.is_file(), self.policy)
        self.assertEqual(packet.count(policy), 1, packet)
        self.assertEqual(packet.count(index), 1, packet)

    def _assert_requirements_policy(self, packet: str) -> None:
        """Assert a packet exposes its selected policy rather than model behavior."""
        policy = (
            "Maintained requirements policy: "
            + str(self.policy)
            + "#maintained-product-requirements"
        )
        reference_handoff = (
            "Reference handoff policy: "
            + str(self.policy)
            + "#reference-handoffs-and-destinations"
        )
        self.assertTrue(self.policy.is_file(), self.policy)
        self.assertEqual(packet.count(policy), 1, packet)
        self.assertEqual(packet.count(reference_handoff), 1, packet)

    def _submit_blocked(self, packet: str) -> subprocess.CompletedProcess[str]:
        """Use the packet's exact public callback to create a blocked packet."""
        callback = Path(
            packet.split("Write the structured result to: ", 1)[1].splitlines()[0]
        )
        callback.write_text(
            store.dumps(
                {
                    "outcome": "blocked",
                    "summary": "Synthetic blocker retained for packet recovery coverage.",
                },
                "ShipLoop cross-run blocked callback",
            ),
            encoding="utf-8",
        )
        command = shlex.split(
            packet.split("Call this when done:\n", 1)[1].splitlines()[0]
        )
        self.assertEqual(command[0], "python3")
        return self._run([sys.executable, "-B", *command[1:]])

    @staticmethod
    def _complete_state(repo: Path, prompt: str) -> dict:
        """Build a valid terminal navigator fixture without replaying every CLI call."""
        state = navigator.new_state(str(repo), prompt)
        while state["status"] != "done":
            action = navigator.current_action(state)
            result: dict[str, object] = {
                "outcome": "done",
                "summary": "Synthetic completed prior-run result.",
            }
            if action["stage"] == "plan":
                result["work_items"] = [
                    {
                        "id": "OLD",
                        "title": "Original completed board",
                        "context": "Historical scope only.",
                    }
                ]
            if action["stage"] == "document":
                result["choices"] = {"skill_required": False}
            state = navigator.apply(state, action["id"], result)
        return state

    def test_matching_init_is_idempotent_but_changed_prompt_or_repo_is_rejected(self) -> None:
        """A run cannot silently become a different feature or repository."""
        for mode in ("navigator", "navigator-v1", "managed", "legacy"):
            with self.subTest(mode=mode):
                run_dir = self.base / ("run " + mode)
                first = self._init(run_dir, mode=mode)
                before = self._snapshot(run_dir)
                original = self._state(run_dir)

                retry = self._init(run_dir, mode=mode)
                self.assertEqual(retry.returncode, 0, retry.stdout + retry.stderr)
                self.assertEqual(self._snapshot(run_dir), before)

                changed_prompt = self._init(
                    run_dir, NEW_PROMPT, mode=mode, expected=2
                )
                self.assertIn("fresh --run-dir", changed_prompt.stderr)
                self.assertEqual(self._snapshot(run_dir), before)
                self.assertEqual(self._state(run_dir), original)

                changed_repo = self._init(
                    run_dir,
                    mode=mode,
                    repo=self.other_repo,
                    expected=2,
                )
                self.assertIn("fresh --run-dir", changed_repo.stderr)
                self.assertEqual(self._snapshot(run_dir), before)
                self.assertEqual(self._state(run_dir), original)
                self.assertIn(OLD_PROMPT, first.stdout)

    def test_all_navigator_protocols_expose_requirements_policy_after_cold_next(self) -> None:
        """CLI packets expose durable policy locators; this does not simulate reading them."""
        for mode, protocol_version in (
            ("navigator-v1", 1),
            ("navigator-v2", 2),
            ("navigator", 3),
        ):
            with self.subTest(mode=mode):
                run_dir = self.base / (mode + " requirements policy")
                initial = self._init(run_dir, mode=mode)
                self.assertEqual(
                    self._state(run_dir)["navigator_protocol_version"], protocol_version
                )
                self._assert_requirements_policy(initial.stdout)
                self.assertIn("Follow the packet's Reference handoff policy", initial.stdout)
                before = self._snapshot(run_dir)

                cold = self._cli(run_dir, "next")
                self._assert_requirements_policy(cold.stdout)
                self.assertIn("Follow the packet's Reference handoff policy", cold.stdout)
                self.assertEqual(self._snapshot(run_dir), before)

    def test_policy_sections_are_real_in_the_relocated_package(self) -> None:
        """The copied package owns both durable policy anchors; packets do not prove reads."""
        self.assertEqual(
            self.policy,
            (self.package / "references" / "project-knowledge.md").resolve(),
        )
        self.assertNotEqual(
            self.policy,
            (SOURCE_PACKAGE / "references" / "project-knowledge.md").resolve(),
        )
        policy = self.policy.read_text(encoding="utf-8")
        marker = "## Maintained product requirements"
        self.assertIn(marker, policy)
        section = policy.split(marker, 1)[1].split("\n## ", 1)[0]
        self.assertRegex(section, r"(?is)first.{0,120}maintained requirements")
        self.assertIn("docs/requirements.md", section)
        self.assertRegex(section, r"(?is)(?:README.{0,200}link|link.{0,200}README)")
        self.assertRegex(
            section, r"(?is)(?:outside|not|never).{0,160}(?:prior|run|workspace).{0,160}state"
        )
        self.assertIn("## Reference handoffs and destinations", policy)

    def test_successive_new_features_keep_repo_requirements_when_old_run_is_unavailable(self) -> None:
        """Fresh requests retain repository documents, not earlier run state or semantics."""
        old_run = self.base / "unavailable original request"
        old_packet = self._init(old_run, OLD_PROMPT, mode="navigator")
        self._assert_requirements_policy(old_packet.stdout)
        shutil.rmtree(old_run)
        self.assertFalse(old_run.exists())

        requirements = self.requirements.read_bytes()
        readme = self.readme.read_bytes()
        self.assertIn(b"(docs/requirements.md)", readme)
        first_run = self.base / "first incremental feature"
        first_packet = self._init(first_run, NEW_PROMPT, mode="navigator")
        self._assert_requirements_policy(first_packet.stdout)
        first = self._state(first_run)
        self.assertEqual(first["prompt"], NEW_PROMPT)
        self.assertNotIn(OLD_PROMPT, str(first))
        self.assertNotIn(str(old_run), str(first))
        first_files = self._snapshot(first_run)

        third_run = self.base / "third incremental feature"
        third_packet = self._init(third_run, THIRD_PROMPT, mode="navigator")
        self._assert_requirements_policy(third_packet.stdout)
        third = self._state(third_run)
        self.assertEqual(third["prompt"], THIRD_PROMPT)
        self.assertNotIn(OLD_PROMPT, str(third))
        self.assertNotIn(NEW_PROMPT, str(third))
        self.assertNotIn(str(old_run), str(third))
        self.assertEqual(self._snapshot(first_run), first_files)

        for run_dir, prompt in ((first_run, NEW_PROMPT), (third_run, THIRD_PROMPT)):
            with self.subTest(run_dir=run_dir.name):
                cold = self._cli(run_dir, "next")
                self._assert_requirements_policy(cold.stdout)
                self.assertEqual(self._state(run_dir)["prompt"], prompt)
                self.assertEqual(self.requirements.read_bytes(), requirements)
                self.assertEqual(self.readme.read_bytes(), readme)

    def test_completed_navigator_rejects_a_new_request_but_retains_terminal_recovery(self) -> None:
        """A completed old request cannot be replayed as a later feature request."""
        run_dir = self.base / "completed prior run"
        run_dir.mkdir()
        completed = self._complete_state(self.repo.resolve(), OLD_PROMPT)
        navigator.save(run_dir, completed)
        before = self._snapshot(run_dir)

        same = self._init(run_dir)
        self.assertIn("It's all complete.", same.stdout)
        self.assertIn(OLD_PROMPT, same.stdout)
        self.assertEqual(self._snapshot(run_dir), before)

        changed = self._init(run_dir, NEW_PROMPT, expected=2)
        self.assertIn("fresh --run-dir", changed.stderr)
        self.assertEqual(self._snapshot(run_dir), before)
        self.assertEqual(self._state(run_dir)["prompt"], OLD_PROMPT)

    def test_default_repo_run_rejects_new_scope_but_nested_fresh_run_is_distinct(self) -> None:
        """The convenient default path preserves a prior run; an explicit child is new."""
        default_run = self.repo / ".shiploop"
        self._run(
            [
                sys.executable,
                "-B",
                str(self.cli),
                "init",
                "--repo",
                str(self.repo),
                "--prompt",
                OLD_PROMPT,
            ]
        )
        prior = self._complete_state(self.repo.resolve(), OLD_PROMPT)
        navigator.save(default_run, prior)
        prior_files = {
            name: (default_run / name).read_bytes()
            for name in ("state.md", "report.html")
        }
        changed = self._run(
            [
                sys.executable,
                "-B",
                str(self.cli),
                "init",
                "--repo",
                str(self.repo),
                "--prompt",
                NEW_PROMPT,
            ],
            expected=2,
        )
        self.assertIn("fresh --run-dir", changed.stderr)
        self.assertEqual(
            {name: (default_run / name).read_bytes() for name in prior_files},
            prior_files,
        )

        fresh_run = default_run / "runs" / "drag-01"
        fresh_packet = self._init(fresh_run, NEW_PROMPT)
        self._assert_knowledge_locators(fresh_packet.stdout)
        self.assertEqual(
            {name: (default_run / name).read_bytes() for name in prior_files},
            prior_files,
        )
        fresh = self._state(fresh_run)
        old_actions = set(prior["accepted"])
        self.assertEqual(fresh["prompt"], NEW_PROMPT)
        self.assertNotIn(navigator.current_action(fresh)["id"], old_actions)
        self.assertNotEqual(fresh["run_id"], prior["run_id"])

    def test_identical_prompt_new_run_preserves_active_prior_run_and_explicit_recovery(self) -> None:
        """Equal prompt text does not force a new request into an active old run."""
        for mode in ("navigator-v2", "navigator"):
            with self.subTest(mode=mode):
                old_run = self.base / (mode + " active prior request")
                initial = self._init(old_run, NEW_PROMPT, mode=mode)
                old = self._state(old_run)
                self.assertEqual(old["status"], "active")
                old_files = self._snapshot(old_run)

                fresh_run = self.base / (mode + " fresh identical request")
                fresh_packet = self._init(fresh_run, NEW_PROMPT, mode=mode)
                fresh = self._state(fresh_run)
                fresh_files = self._snapshot(fresh_run)
                self._assert_knowledge_locators(fresh_packet.stdout)
                self.assertEqual(fresh["prompt"], old["prompt"])
                self.assertNotEqual(fresh["run_id"], old["run_id"])
                self.assertNotEqual(
                    navigator.current_action(fresh)["id"],
                    navigator.current_action(old)["id"],
                )
                self.assertEqual(fresh["history"], [])
                self.assertEqual(fresh["accepted"], {})
                self.assertEqual(self._snapshot(old_run), old_files)

                recovered = self._cli(old_run, "next")
                self.assertEqual(recovered.stdout, initial.stdout)
                self.assertEqual(self._snapshot(old_run), old_files)
                self.assertEqual(self._snapshot(fresh_run), fresh_files)

    def test_fresh_run_reuses_project_knowledge_locator_without_importing_prior_scope(self) -> None:
        """A new request receives the index, while old run state stays historical."""
        old_run = self.base / "completed original feature"
        old_run.mkdir()
        prior = self._complete_state(self.repo.resolve(), OLD_PROMPT)
        navigator.save(old_run, prior)
        old_snapshot = self._snapshot(old_run)

        new_run = self.base / "incremental drag feature"
        initial = self._init(new_run, NEW_PROMPT)
        self._assert_knowledge_locators(initial.stdout)
        new_before_next = self._snapshot(new_run)
        cold = self._cli(new_run, "next")
        self._assert_knowledge_locators(cold.stdout)
        self.assertEqual(cold.stdout, initial.stdout)
        self.assertEqual(self._snapshot(new_run), new_before_next)
        self.assertEqual(self._snapshot(old_run), old_snapshot)

        fresh = self._state(new_run)
        self.assertEqual(fresh["prompt"], NEW_PROMPT)
        self.assertEqual(fresh["history"], [])
        self.assertEqual(fresh["completed_work_items"], [])
        self.assertEqual(fresh["work_items"][0]["id"], "W1")
        self.assertNotIn("OLD", str(fresh))
        self.assertNotIn(OLD_PROMPT, str(fresh))
        self.assertNotIn(str(old_run), str(fresh))
        self.assertTrue(self.environment.is_file())
        self.assertIn("environment.md", self.index.read_text(encoding="utf-8"))

    def test_missing_prior_run_keeps_repository_knowledge_without_importing_history(self) -> None:
        """Routing survives stale history; this does not prove a host reads documents."""
        prior_run = self.base / "temporary removed history"
        prior_run.mkdir()
        prior = self._complete_state(self.repo.resolve(), OLD_PROMPT)
        navigator.save(prior_run, prior)
        missing_evidence = prior_run / "report.html"
        self.assertTrue(missing_evidence.is_file())
        self.index.write_text(
            self.index.read_text(encoding="utf-8")
            + "- Historical delivery record (may no longer exist): "
            + str(missing_evidence)
            + "\n",
            encoding="utf-8",
        )
        index = self.index.read_bytes()
        environment = self.environment.read_bytes()
        shutil.rmtree(prior_run)
        self.assertFalse(prior_run.exists())
        self.assertTrue(self.index.is_file())
        self.assertTrue(self.environment.is_file())

        later_run = self.base / "later incremental feature"
        packet = self._init(later_run, NEW_PROMPT)
        self._assert_knowledge_locators(packet.stdout)
        later = self._state(later_run)
        self.assertEqual(later["prompt"], NEW_PROMPT)
        self.assertEqual(later["history"], [])
        self.assertEqual(later["accepted"], {})
        self.assertEqual(later["completed_work_items"], [])
        self.assertNotEqual(later["run_id"], prior["run_id"])
        self.assertNotIn(navigator.current_action(later)["id"], prior["accepted"])
        self.assertNotIn(OLD_PROMPT, str(later))
        self.assertNotIn(str(missing_evidence), str(later))
        self.assertFalse(missing_evidence.exists())
        self.assertEqual(self.index.read_bytes(), index)
        self.assertEqual(self.environment.read_bytes(), environment)

    def test_knowledge_locators_survive_active_paused_blocked_and_done_packets(self) -> None:
        """A cold-context host can find durable project knowledge at every state."""
        active_run = self.base / "active run"
        active = self._init(active_run)
        self._assert_knowledge_locators(active.stdout)

        paused = self._cli(
            active_run,
            "pause",
            "--reason",
            "Pause before the current discovery action.",
        )
        self._assert_knowledge_locators(paused.stdout)
        resumed = self._cli(active_run, "resume")
        self._assert_knowledge_locators(resumed.stdout)
        blocked = self._submit_blocked(resumed.stdout)
        self._assert_knowledge_locators(blocked.stdout)
        self.assertIn("Blocked, unfinished:", blocked.stdout)

        # A terminal state is intentionally constructed with the public state
        # schema, then rendered through the public CLI.  The routing assertion
        # is about packet recovery, not an LLM execution simulation.
        terminal_run = self.base / "terminal run"
        terminal_run.mkdir()
        navigator.save(
            terminal_run,
            self._complete_state(self.repo.resolve(), OLD_PROMPT),
        )
        done = self._cli(terminal_run, "next")
        self._assert_knowledge_locators(done.stdout)
        self.assertIn("It's all complete.", done.stdout)

    def test_project_index_is_a_read_only_locator_when_present_or_missing(self) -> None:
        """ShipLoop points at repository knowledge without parsing or creating it."""
        self.index.write_bytes(b"arbitrary project knowledge text; not a command.\n")
        present_index = self.index.read_bytes()
        environment = self.environment.read_bytes()
        present_run = self.base / "present arbitrary index"
        initial = self._init(present_run)
        initial_state = self._state(present_run)
        initial_state_bytes = (present_run / "state.md").read_bytes()
        self._assert_knowledge_locators(initial.stdout)
        cold = self._cli(present_run, "next")
        self._assert_knowledge_locators(cold.stdout)
        self.assertEqual((present_run / "state.md").read_bytes(), initial_state_bytes)
        self.assertEqual(self._state(present_run)["prompt"], initial_state["prompt"])
        self.assertEqual(
            navigator.current_action(self._state(present_run))["id"],
            navigator.current_action(initial_state)["id"],
        )
        self.assertEqual(self.index.read_bytes(), present_index)
        self.assertEqual(self.environment.read_bytes(), environment)

        self.index.unlink()
        missing_run = self.base / "missing project index"
        missing = self._init(missing_run, NEW_PROMPT)
        self._assert_knowledge_locators(missing.stdout)
        self.assertFalse(self.index.exists())
        missing_state_bytes = (missing_run / "state.md").read_bytes()
        missing_cold = self._cli(missing_run, "next")
        self._assert_knowledge_locators(missing_cold.stdout)
        self.assertEqual((missing_run / "state.md").read_bytes(), missing_state_bytes)
        self.assertFalse(self.index.exists())
        self.assertEqual(self.environment.read_bytes(), environment)


if __name__ == "__main__":
    unittest.main()
