#!/usr/bin/env python3
"""Acceptance coverage for ShipLoop's early readiness packet policies.

Synthetic observations below are host declarations used to exercise the public
navigator callback contract.  They do not classify credentials, execute an
authentication flow, or prove that an executing host follows prompt guidance.
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

import state_home

state_home.isolate()


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PACKAGE = ROOT / "skills" / "shiploop"
SOURCE_SCRIPTS = SOURCE_PACKAGE / "scripts"
if str(SOURCE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SOURCE_SCRIPTS))

import shiploop_navigator as navigator  # noqa: E402
import shiploop_packet_symbols as symbols  # noqa: E402
import shiploop_prompts as prompts  # noqa: E402
import shiploop_store as store  # noqa: E402
from shiploop_packet_view import callback_argv, callback_result_path, packet_file_named  # noqa: E402


ACCESS_POLICY_LABEL = "Access-readiness policy: "
ACCESS_POLICY_ANCHOR = "early-access-readiness"

GENERIC_ACCESS_STORE_BOUNDARY = (
    "For identity or access discovery, use supported non-mutating probes and sanitized "
    "evidence. Normal supported tool-managed authentication and tool configuration metadata "
    "without session material remain allowed. Builders and reviewers must not read, decode, "
    "retain, or report local authentication, session, or credential-store contents."
)
LIFECYCLE_POLICY_LABEL = "Environment lifecycle policy: "
LIFECYCLE_NOTE_LABEL = "Environment lifecycle note (host-authored, if present): "
LIFECYCLE_NOTE = "notes/environment-lifecycle.md"


def _with_packet_file(stdout: str) -> str:
    """The complete packet: its file when stdout printed a ``Full packet:`` pointer.

    An active packet prints a short head, and a paused, blocked, halted or done
    packet longer than the print limit prints the start of its text; either way
    the file holds the whole packet, so it is read instead of stdout (reading both
    would count the printed part twice, as long local temp paths make happen).
    A packet printed whole has no pointer and passes through unchanged.
    """
    packet_file = packet_file_named(stdout)
    if packet_file is not None and packet_file.is_file():
        return packet_file.read_text(encoding="utf-8")
    return stdout


class AuthReadinessNavigatorTests(unittest.TestCase):
    """Check public packets and callbacks without adding an auth executor."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-auth-readiness-")
        self.base = Path(self.temp.name)
        self.package = self.base / "relocated ShipLoop package"
        shutil.copytree(
            SOURCE_PACKAGE,
            self.package,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
        )
        self.cli = (self.package / "scripts" / "shiploop").resolve()
        self.research_loop = (self.package / "references" / "research-loop.md").resolve()
        self.lifecycle_policy = (
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

    def _cli(self, run_dir: Path, *args: str) -> str:
        return _with_packet_file(self._run(
            [
                sys.executable,
                "-B",
                str(self.cli),
                *args,
                "--run-dir",
                str(run_dir),
            ]
        ).stdout)

    def _start(self, run_dir: Path) -> str:
        packet = self._cli(
            run_dir,
            "init",
            "--repo",
            str(self.repo),
            "--prompt",
            "Exercise the early access-readiness packet contract.",
        )
        self.assertEqual(self._state(run_dir)["navigator_protocol_version"], 4)
        return packet

    @staticmethod
    def _state(run_dir: Path) -> dict:
        return store.read_record(run_dir / "state.md")

    @staticmethod
    def _current_action(state: dict) -> dict:
        return dict(navigator.current_action(state))

    def _policy_locator(self) -> str:
        return (
            ACCESS_POLICY_LABEL
            + str(self.research_loop)
            + "#"
            + ACCESS_POLICY_ANCHOR
        )

    def _assert_active_access_boundary(self, packet: str, run_dir: Path) -> None:
        # A producer packet prints the short STAGE_RULES bullet; the full boundary text (probes, sanitized evidence,
        # tool-managed authentication) is kept whole in the run reference file the packet points to (2026-10-11
        # dedupe: COMMON left the packet, reference.md#rules has it).
        flat = " ".join(packet.split())
        self.assertIn("Never read, keep or report credential-store or session contents.", flat)
        self.assertIn("reference#rules", flat)
        self.assertIn(GENERIC_ACCESS_STORE_BOUNDARY, " ".join(self._reference(run_dir).split()))

    @staticmethod
    def _reference(run_dir: Path) -> str:
        reference = run_dir / "reference.md"
        assert reference.is_file(), reference
        return reference.read_text(encoding="utf-8")

    def _assert_access_policy(self, packet: str, run_dir: Path) -> None:
        # Since the 2026-10-11 dedupe a packet prints a policy locator only when its stage text names that policy;
        # every one stays reachable through the run reference file's #policies section, which the packet's
        # "Every other policy and guide" line points to.  Either way the path comes from the selected package.
        packet = symbols.expanded(packet, ("GUIDES", "RUN"))   # a packet prints guides and run files as symbols (2026-10-16)
        reference = self._reference(run_dir)
        policies = reference.split("{#policies}", 1)[1].split("{#workspace}", 1)[0]
        authority_policy = (self.package / "references" / "delivery-authority.md").resolve()
        self.assertTrue(authority_policy.is_file())
        for label, locator, source in (
            (ACCESS_POLICY_LABEL, self._policy_locator(),
             ACCESS_POLICY_LABEL + str((SOURCE_PACKAGE / "references" / "research-loop.md").resolve())),
            ("Delivery-authority policy: ", "Delivery-authority policy: " + str(authority_policy),
             "Delivery-authority policy: " + str(SOURCE_PACKAGE / "references" / "delivery-authority.md")),
            (LIFECYCLE_POLICY_LABEL, LIFECYCLE_POLICY_LABEL + str(self.lifecycle_policy),
             LIFECYCLE_POLICY_LABEL + str((SOURCE_PACKAGE / "references" / "environment-lifecycle.md").resolve())),
        ):
            with self.subTest(policy=label):
                self.assertEqual(policies.count("- " + locator), 1, policies)
                self.assertEqual(packet.count(label), packet.count(locator))  # printed in full or not at all
                self.assertLessEqual(packet.count(locator), 1, packet)
                self.assertNotIn(source, packet)
                self.assertNotIn(source, policies)
        # The environment-lifecycle note is host-authored and belongs to this run.
        note = LIFECYCLE_NOTE_LABEL + str((run_dir / LIFECYCLE_NOTE).resolve())
        self.assertEqual(policies.count("- " + note), 1, policies)
        self.assertEqual(packet.count(LIFECYCLE_NOTE_LABEL), packet.count(note))
        self.assertLessEqual(packet.count(note), 1, packet)
        # The packet points at the reference file for everything it does not print.
        self.assertIn("every other policy and guide, and the rules' long form: "
                      + str(run_dir.resolve() / "reference.md") + " (#policies, #rules, #recovery).", packet)

    def _cold_packet(self, run_dir: Path) -> str:
        before = (run_dir / "state.md").read_bytes()
        packet = self._cli(run_dir, "next")
        self.assertEqual((run_dir / "state.md").read_bytes(), before)
        self._assert_active_access_boundary(packet, run_dir)
        self._assert_access_policy(packet, run_dir)
        return packet

    def _submit(self, run_dir: Path, packet: str, result: dict) -> tuple[str, Path, list[str]]:
        state = self._state(run_dir)
        action = self._current_action(state)
        # The one callback line names the result file in its label and carries the command, which has no --result flag
        # (complete reads RUN/inbox/<action>.md by default).
        command = callback_argv(packet)
        self.assertFalse([arg for arg in command if arg.startswith("--result")], command)
        callback = callback_result_path(packet)
        self.assertEqual(
            callback,
            run_dir.resolve() / "inbox" / f"{action['id']}.md",
        )
        self.assertEqual(command[0], "python3")
        self.assertEqual(Path(command[1]).resolve(), self.cli)
        self.assertEqual(command.count("--action=" + action["id"]), 1)
        callback.write_text(
            store.dumps(result, "Synthetic host declaration"), encoding="utf-8"
        )
        completed = self._run([sys.executable, "-B", *command[1:]])
        return _with_packet_file(completed.stdout), callback, command

    @staticmethod
    def _result(stage: str, *, outcome: str = "done", **extra) -> dict:
        return {
            "outcome": outcome,
            "summary": (  # cites S1, the fixture prompt's one sentence: a done intake must (IN1)
                f"Synthetic host declaration at {stage} (S1); no credential, network, "
                "or setup action was performed."
            ),
            **extra,
        }

    def test_relocated_reference_exposes_the_early_access_heading(self) -> None:
        self.assertTrue(self.research_loop.is_file())
        reference = self.research_loop.read_text(encoding="utf-8")
        self.assertRegex(reference, r"(?m)^#{1,6} Early access readiness\s*$")
        # The shared access-store boundary is generic policy text.
        self.assertIn(GENERIC_ACCESS_STORE_BOUNDARY, " ".join(reference.split()))
        self.assertTrue(self.lifecycle_policy.is_file())

    def test_paused_draft_packet_keeps_the_relocated_policy_without_advancing(self) -> None:
        run_dir = self.base / "paused run"
        packet = self._start(run_dir)
        packet, _callback, _command = self._submit(
            run_dir, packet, self._result("intake")
        )
        active = self._state(run_dir)
        action = self._current_action(active)
        self.assertEqual((action["stage"], active["status"]), ("discovery", "active"))
        draft = run_dir.resolve() / "inbox" / f"{action['id']}.md"
        draft_bytes = (
            b"# Discovery access-readiness draft\n\n"
            b"Host declaration: a user interaction may be needed; no credential or token is recorded.\n"
        )
        draft.write_bytes(draft_bytes)
        reason = "Preserve the non-secret discovery draft while awaiting the user."
        paused_packet = self._cli(run_dir, "pause", "--reason", reason)
        paused = self._state(run_dir)
        paused_bytes = (run_dir / "state.md").read_bytes()
        self.assertEqual((self._current_action(paused)["stage"], paused["status"]), ("discovery", "paused"))
        self.assertEqual(self._current_action(paused)["id"], action["id"])
        self.assertEqual(draft.read_bytes(), draft_bytes)
        self._assert_access_policy(paused_packet, run_dir)
        self.assertNotIn("Call this when done:", paused_packet)

        cold_paused = self._cli(run_dir, "next")
        self.assertEqual((run_dir / "state.md").read_bytes(), paused_bytes)
        self._assert_access_policy(cold_paused, run_dir)
        self.assertNotIn("Call this when done:", cold_paused)

        resumed_packet = self._cli(run_dir, "resume")
        resumed = self._state(run_dir)
        self.assertEqual((self._current_action(resumed)["stage"], resumed["status"]), ("discovery", "active"))
        self.assertEqual(self._current_action(resumed)["id"], action["id"])
        self.assertEqual(draft.read_bytes(), draft_bytes)
        self._assert_access_policy(resumed_packet, run_dir)

    def test_cold_block_resume_uses_fresh_callback_and_preserves_discovery_note(self) -> None:
        run_dir = self.base / "blocked run"
        packet = self._start(run_dir)
        packet, _callback, _command = self._submit(
            run_dir, packet, self._result("intake")
        )
        active = self._state(run_dir)
        blocked_action = self._current_action(active)
        self.assertEqual((blocked_action["stage"], active["status"]), ("discovery", "active"))

        note_ref = "notes/discovery-access-readiness.md"
        note = self.repo / note_ref
        note.parent.mkdir()
        note.write_text(
            "# Discovery access readiness\n\n"
            "Host declaration only; no credential or token is stored here.\n",
            encoding="utf-8",
        )
        cold = self._cold_packet(run_dir)
        blocked_result = self._result(
            "discovery",
            outcome="blocked",
            awaiting={"kind": "service", "service": "the staging identity provider",
                      "check": "curl -fsS https://idp.example.test/health",
                      "no_default": "Discovery cannot read the access policy until the provider answers."},
            evidence_refs=[note_ref],
        )
        blocked_packet, blocked_callback, blocked_command = self._submit(
            run_dir, cold, blocked_result
        )
        blocked = self._state(run_dir)
        fresh_action = self._current_action(blocked)
        self.assertEqual((fresh_action["stage"], blocked["status"]), ("discovery", "blocked"))
        self.assertNotEqual(fresh_action["id"], blocked_action["id"])
        self.assertEqual(blocked["accepted"][blocked_action["id"]], blocked_result)
        self.assertEqual(
            store.read_record(run_dir / "results" / f"{blocked_action['id']}.md")["result"],
            blocked_result,
        )
        self._assert_access_policy(blocked_packet, run_dir)
        self.assertIn(note_ref, blocked_packet)
        self.assertNotIn("Call this when done:", blocked_packet)

        blocked_bytes = (run_dir / "state.md").read_bytes()
        cold_blocked = self._cli(run_dir, "next")
        self.assertEqual((run_dir / "state.md").read_bytes(), blocked_bytes)
        self._assert_access_policy(cold_blocked, run_dir)
        self.assertIn(note_ref, cold_blocked)
        self.assertNotIn("Call this when done:", cold_blocked)

        resumed_packet = self._cli(run_dir, "resume", "--observed", "The health check exits 0 again.")
        resumed = self._state(run_dir)
        resumed_action = self._current_action(resumed)
        self.assertEqual((resumed_action["stage"], resumed["status"]), ("discovery", "active"))
        self.assertEqual(resumed_action["id"], fresh_action["id"])
        self._assert_access_policy(resumed_packet, run_dir)
        self.assertIn(note_ref, resumed_packet)

        resumed_cold = self._cold_packet(run_dir)
        done_packet, _fresh_callback, _fresh_command = self._submit(
            run_dir, resumed_cold, self._result("discovery")
        )
        after_done = self._state(run_dir)
        self.assertEqual((self._current_action(after_done)["stage"], after_done["status"]), ("research", "active"))
        self.assertEqual(after_done["accepted"][blocked_action["id"]], blocked_result)
        self._assert_access_policy(done_packet, run_dir)

        blocked_callback.write_text(
            store.dumps(
                self._result("discovery", summary="Conflicting stale declaration."),
                "Conflicting stale callback",
            ),
            encoding="utf-8",
        )
        before_conflict = (run_dir / "state.md").read_bytes()
        conflicting = self._run([sys.executable, "-B", *blocked_command[1:]], expected=None)
        self.assertNotEqual(
            conflicting.returncode,
            0,
            conflicting.stdout + conflicting.stderr,
        )
        self.assertEqual((run_dir / "state.md").read_bytes(), before_conflict)


if __name__ == "__main__":
    unittest.main()
