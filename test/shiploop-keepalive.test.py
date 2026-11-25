#!/usr/bin/env python3
"""ShipLoop keepalive: hook-status, the packet marker, host hooks, install and the driver.

Hook payloads come from recorded host runs (test/fixtures/shiploop-keepalive).
Runs are real ShipLoop runs in temporary directories; no host CLI is launched.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
import shlex
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
FIXTURES = ROOT / "test" / "fixtures" / "shiploop-keepalive"
sys.path.insert(0, str(ROOT / "test"))
import state_home  # noqa: E402

state_home.isolate()

sys.path.insert(0, str(SCRIPTS))

import shiploop_keepalive as keepalive  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_trace as trace  # noqa: E402
from shiploop_packet_view import assert_top_block, head_packet_path  # noqa: E402

RECORDED_HOSTS = ("antigravity", "claude", "codex", "cursor")


def shiploop(*argv: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / "shiploop"), *argv],
                          capture_output=True, text=True, check=False)


def _packet_path_from_stdout(stdout: str) -> Path | None:
    """The packet file to recover when stdout does not contain its complete body."""
    return head_packet_path(stdout)


def _packet_file_text(stdout: str) -> str:
    """The complete packet text, recovered from its file only when stdout is incomplete."""
    path = _packet_path_from_stdout(stdout)
    return path.read_text(encoding="utf-8") if path is not None and path.is_file() else stdout


class KeepaliveTestCase(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="shiploop-keepalive-")
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name).resolve()
        self.repo = self.temp / "repo"
        self.run_dir = self.temp / "run"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True, capture_output=True)  # not the guarded empty non-Git folder
        # No progress observer: `init` would start one detached, and it writes into the run folder every 2 s, so a fast
        # test's cleanup raced it ("Directory not empty", 4 of 7 direct runs on 2026-10-28; run_suites.py sets it too).
        env = {"SHIPLOOP_KEEPALIVE_HOME": str(self.temp / "state"), "HOME": str(self.temp / "home"),
               "XDG_CONFIG_HOME": str(self.temp / "home" / ".config"), "SHIPLOOP_PROGRESS": "off",
               "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        # Hooks here run in the test process: no host process is found, so only time frees a claim (OwnerProcessTests
        # gives the process table).
        no_host = mock.patch.object(keepalive, "host_process", return_value=None)
        no_host.start()
        self.addCleanup(no_host.stop)
        os.environ.pop("SHIPLOOP_KEEPALIVE", None)
        result = shiploop("init", "--run-dir", str(self.run_dir), "--repo", str(self.repo),
                          "--prompt", "Add a greeting script.")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.packet = result.stdout

    def status(self) -> dict:
        result = shiploop("hook-status", "--run-dir", str(self.run_dir))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def marker_line(self) -> str:
        return next(line for line in self.packet.splitlines() if "SHIPLOOP-RUN" in line)

    def payload(self, host: str, event: str, session: str = "session-1") -> dict:
        text = (FIXTURES / f"{host}-{event}.json").read_text(encoding="utf-8")
        text = (text.replace("__SESSION__", session)
                .replace("__MARKER__", self.marker_line())
                .replace("__RUN_DIR__", str(self.run_dir)))
        return json.loads(text)

    def hook(self, event: str, host: str, payload: dict) -> dict | None:
        out = keepalive.run_hook(event, host, json.dumps(payload))
        return json.loads(out) if out else None

    def advance(self) -> None:
        """Move the run's revision the way real work would."""
        for verb in ("pause", "resume"):
            argv = [verb, "--run-dir", str(self.run_dir)] + (["--reason", "test"] if verb == "pause" else [])
            result = shiploop(*argv)
            self.assertEqual(result.returncode, 0, result.stderr)


class HookStatusAndMarkerTests(KeepaliveTestCase):
    def test_hook_status_reports_the_run_without_changing_it(self) -> None:
        before = (self.run_dir / "state.md").read_bytes()
        status = self.status()
        self.assertEqual(status["status"], "active")
        self.assertEqual(status["run_dir"], str(self.run_dir))
        self.assertEqual(status["repo"], str(self.repo))
        self.assertEqual(status["revision"], 0)
        self.assertIn("next --run-dir", status["next"])
        self.assertEqual(status["progress"], "0.0.0")  # no Until Loop yet at intake
        # One derived completion instruction; no raw receipt or second task packet.
        self.assertEqual(set(status), {"run_dir", "run_id", "repo", "status", "status_reason", "awaiting", "stage",
                                       "profile", "reviewed_stage", "action", "revision", "progress", "next", "completion"})
        self.assertEqual((self.run_dir / "state.md").read_bytes(), before)

    def test_ordinary_completion_is_the_existing_callback_and_status_is_lock_free(self) -> None:
        # Holding the writer lock must not make the read-only status wait for it.
        import fcntl
        with (self.run_dir / ".lock").open("w") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            status = self.status()
        callback = next(line for line in self.packet.splitlines() if line.startswith("Callback for this stage"))
        self.assertIn(callback, status["completion"])
        self.assertIn(status["completion"], keepalive._continue_reason(status))
        self.assertIn(status["completion"], keepalive._driver_prompt(status))
        self.assertNotIn(" check ", status["completion"])
        self.assertNotIn("Original request", status["completion"])

    def test_hook_status_for_a_missing_run_is_an_error_answer(self) -> None:
        result = shiploop("hook-status", "--run-dir", str(self.temp / "missing"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("error", json.loads(result.stdout))

    def test_every_packet_carries_the_marker_for_its_revision(self) -> None:
        marker = keepalive.last_marker(self.packet)
        status = self.status()
        self.assertEqual(marker, {"run_id": status["run_id"], "rev": 0, "run_dir": str(self.run_dir)})
        paused = shiploop("pause", "--run-dir", str(self.run_dir), "--reason", "user asked")
        self.assertEqual(keepalive.last_marker(paused.stdout)["rev"], 1)

    def test_marker_keeps_a_run_directory_with_spaces(self) -> None:
        spaced = self.temp / "run with spaces"
        result = shiploop("init", "--run-dir", str(spaced), "--repo", str(self.repo), "--prompt", "Other work.")
        self.assertEqual(keepalive.last_marker(result.stdout)["run_dir"], str(spaced))




class RepeatPacketTests(KeepaliveTestCase):
    """next is the recovery command: every packet is the full packet."""

    def test_plain_next_after_a_packet_is_the_full_packet(self) -> None:
        # The script cannot know whether the host lost the rules since this packet was shown.
        recovered = shiploop("next", "--run-dir", str(self.run_dir)).stdout
        self.assertEqual(recovered, self.packet)
        full = _packet_file_text(recovered)
        self.assertIn("Original request (preserve user scope", full)
        self.assertIn("Recovery command (reprints the current packet from saved state", full)

    def test_the_result_contract_ends_the_required_text_after_the_duties(self) -> None:
        # The printed text of this active, non-checkpoint stage (an intake packet has no active_improve, so the print is
        # the whole packet): the callback leads, then the goal; the result template follows the status and the duties
        # and rules and ends the required text (the print order of the efficiency plan, section 6.1).
        lines = self.packet.splitlines()
        callback = next(i for i, line in enumerate(lines) if line.startswith("Callback for this stage"))
        # The "Write the structured result to:" line is gone (2026-10-11 dedupe): the callback line names the result
        # file, and the result template follows the stage's duties.
        self.assertFalse(any(line.startswith("Write the structured result to: ") for line in lines))
        self.assertIn("with the result written to " + str(self.run_dir / "inbox"), lines[callback])
        self.assertNotIn("--result", lines[callback])  # complete reads that one path by default
        # the top block, in order (the pointers, the callback, the owner rule, then the goal), found by label
        assert_top_block(self, lines, require=("pointer", "packet", "callback", "owner", "goal"))
        contract = next(i for i, line in enumerate(lines) if line == "Result template:")
        guidance = lines.index("Current stage guidance:")
        self.assertLess(callback, guidance)
        self.assertLess(guidance, contract)
        # The template is the fence alone (owner decision D4, 2026-10-17): no "# ShipLoop navigator result" heading.
        self.assertEqual(lines[contract + 1], "```shiploop-state")
        self.assertNotIn("# ShipLoop navigator result", self.packet)
        outcomes = next(i for i, line in enumerate(lines) if line.startswith("Allowed outcomes: "))
        self.assertEqual(sum(line == "Result template:" for line in lines), 1)
        self.assertEqual(sum(line.startswith("Allowed outcomes: ") for line in lines), 1)
        self.assertGreater(outcomes, contract)
        # One Keepalive marker, beside the status block, before the duties.
        markers = [i for i, line in enumerate(lines) if line.startswith("Keepalive marker: ")]
        self.assertEqual(len(markers), 1)
        self.assertLess(callback, markers[0])
        self.assertLess(markers[0], guidance)

        # The packet file is the same text without the end line a print carries.
        full_lines = _packet_file_text(self.packet).splitlines()
        self.assertLess(full_lines.index("Current stage guidance:"), next(
            i for i, line in enumerate(full_lines) if line.startswith("Allowed outcomes: ")))

    def test_every_next_is_the_full_packet_and_writes_no_display_records(self) -> None:
        shiploop("pause", "--run-dir", str(self.run_dir), "--reason", "user asked")
        shiploop("resume", "--run-dir", str(self.run_dir))
        again = shiploop("next", "--run-dir", str(self.run_dir)).stdout
        # Recovery prints the complete body at every size and does not append it twice from the pointer.
        self.assertIsNone(_packet_path_from_stdout(again), again)
        state = store.read_record(self.run_dir / "state.md")
        packet = nav.packet_path(self.run_dir, state).read_text(encoding="utf-8")
        self.assertEqual(again, packet + nav.HEAD_END + "\n")
        self.assertEqual(again.splitlines().count(nav.HEAD_END), 1)
        self.assertIn("Original request (preserve user scope", again)
        repeated = shiploop("next", "--run-dir", str(self.run_dir))
        self.assertEqual(repeated.stdout, again)
        for name in ("rules.md", "last-packet.json"):
            self.assertFalse((self.run_dir / name).exists(), name)


class AwaitingUserTests(KeepaliveTestCase):
    """A run blocked on a reply (a person's answer or observation, or an outside service's return) stops quietly and
    resumes only with that reply."""

    QUESTION = {"kind": "answer", "question": "May this run deploy to org de?", "options": ["yes", "no"],
                "no_default": "A deploy needs the user's grant; no default may stand in for it."}

    def block_on(self, awaiting: dict) -> str:
        action = self.status()["action"]
        path = self.run_dir / "inbox" / (action + ".md")
        path.parent.mkdir(exist_ok=True)
        path.write_text(store.dumps({"outcome": "blocked", "summary": "Needs the deploy decision.",
                                     "awaiting": awaiting}, "test result"))
        result = shiploop("complete", "--run-dir", str(self.run_dir), "--action", action, "--result", str(path))
        self.assertEqual(result.returncode, 0, result.stderr)
        return action

    def test_the_stop_is_quiet_and_only_the_users_reply_resumes(self) -> None:
        self.hook("observe", "claude", self.payload("claude", "observe"))
        blocked = self.block_on(self.QUESTION)
        self.assertEqual(self.status()["awaiting"], "answer")
        self.assertIsNone(self.hook("stop", "claude", self.payload("claude", "stop")))
        self.assertIsNone(keepalive.load_binding("claude", "session-1"))
        packet = shiploop("next", "--run-dir", str(self.run_dir)).stdout
        self.assertIn("Blocked, waiting on the user: Needs the deploy decision.", packet)
        self.assertIn("Question for the user: May this run deploy to org de?", packet)
        self.assertIn('--answer "<their words>"', packet)
        self.assertIn("Waiting on you: May this run deploy to org de? (yes / no)",
                      shiploop("status", "--run-dir", str(self.run_dir)).stdout)
        for argv, message in ((["resume"], "A request to continue does not answer it"),
                              (["resume", "--answer", "Continue."], "Ask the user, then resume with --answer"),
                              (["resume", "--observed", "done"], "waits for --answer")):
            with self.subTest(argv=argv):
                refused = shiploop(*argv, "--run-dir", str(self.run_dir))
                self.assertNotEqual(refused.returncode, 0)
                self.assertIn(message, refused.stderr)
        self.assertEqual(self.status()["status"], "blocked")
        resumed = shiploop("resume", "--run-dir", str(self.run_dir), "--answer", "yes, this run only")
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        decision = store.read_record(self.run_dir / "decisions" / (blocked + ".md"))
        self.assertEqual((decision["kind"], decision["reply"]), ("answer", "yes, this run only"))
        self.assertIn("Reply: yes, this run only",
                      _packet_file_text(shiploop("next", "--run-dir", str(self.run_dir)).stdout))

    def test_a_person_present_wait_takes_their_observation(self) -> None:
        self.block_on({"kind": "present", "steps": ["Sign in and open the Reports page.",
                                                    "Create a report, then reload the page."],
                       "report": "whether the report is listed after the reload",
                       "no_default": "Release acceptance needs a signed-in observation this host cannot make."})
        self.assertIn("Waiting on you: 1. Sign in and open the Reports page",
                      shiploop("status", "--run-dir", str(self.run_dir)).stdout)
        refused = shiploop("resume", "--run-dir", str(self.run_dir), "--answer", "yes")
        self.assertIn("waits for --observed", refused.stderr)
        ok = shiploop("resume", "--run-dir", str(self.run_dir), "--observed", "Board shows; fleet kept after reload.")
        self.assertEqual(ok.returncode, 0, ok.stderr)

    def test_a_wait_without_a_no_default_reason_is_refused(self) -> None:
        """S-14: runs are unattended; prompting the user is the last resort and must say why."""
        action = self.status()["action"]
        path = self.run_dir / "inbox" / (action + ".md")
        path.parent.mkdir(exist_ok=True)
        question = {k: v for k, v in self.QUESTION.items() if k != "no_default"}
        path.write_text(store.dumps({"outcome": "blocked", "summary": "Needs a decision.",
                                     "awaiting": question}, "test result"))
        refused = shiploop("complete", "--run-dir", str(self.run_dir), "--action", action, "--result", str(path))
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("ShipLoop runs unattended: take a stated default", refused.stderr)
        self.assertEqual(self.status()["status"], "active")

    def test_a_blocked_result_must_say_what_it_awaits_and_blocked_by_is_retired(self) -> None:
        """Only a person or an outside service can unblock a run, so a blocked result carries awaiting (N5)."""
        action = self.status()["action"]
        path = self.run_dir / "inbox" / (action + ".md")
        path.parent.mkdir(exist_ok=True)
        before = (self.run_dir / "state.md").read_bytes()
        for label, result, message in (
                ("no awaiting", {"outcome": "blocked", "summary": "x"}, "a blocked result says what it awaits"),
                ("blocked_by with awaiting", {"outcome": "blocked", "summary": "x", "blocked_by": "user",
                                              "awaiting": self.QUESTION}, "blocked_by is retired"),
                ("blocked_by alone", {"outcome": "blocked", "summary": "x", "blocked_by": "external"},
                 "blocked_by is retired")):
            with self.subTest(label):
                path.write_text(store.dumps(result, "test result"))
                refused = shiploop("complete", "--run-dir", str(self.run_dir), "--action", action,
                                   "--result", str(path))
                self.assertNotEqual(refused.returncode, 0)
                self.assertIn(message, refused.stderr)
                self.assertEqual((self.run_dir / "state.md").read_bytes(), before)

    def test_an_outside_service_wait_takes_an_observation_and_names_its_read_only_check(self) -> None:
        """A service wait is not a question for the user: the run waits for the service and resumes on --observed."""
        action = self.block_on({"kind": "service", "service": "the staging org", "check": "curl -fsS https://staging.example.test/health",
                                "no_default": "Nothing can be verified until the org is back."})
        self.assertEqual(self.status()["awaiting"], "service")
        self.assertIsNone(self.hook("stop", "claude", self.payload("claude", "stop")))
        packet = shiploop("next", "--run-dir", str(self.run_dir)).stdout
        self.assertIn("Blocked, waiting on an outside service: Needs the deploy decision.", packet)
        self.assertIn("Waiting on an outside service: the staging org", packet)
        self.assertIn("It is back when this read-only check exits 0: curl -fsS https://staging.example.test/health", packet)
        self.assertIn('--observed "<what the check printed>"', packet)
        self.assertIn("resume only when it exits 0", packet)
        self.assertNotIn("Do not answer it yourself", packet)
        self.assertNotIn("Question for the user", packet)
        # A bare resume names the check to run, not a question to answer.
        for argv, message in ((["resume"], "Run that check; when it exits 0, resume with --observed"),
                              (["resume", "--answer", "yes"], "waits for --observed")):
            with self.subTest(argv=argv):
                refused = shiploop(*argv, "--run-dir", str(self.run_dir))
                self.assertNotEqual(refused.returncode, 0)
                self.assertIn(message, refused.stderr)
        self.assertEqual(self.status()["status"], "blocked")
        resumed = shiploop("resume", "--run-dir", str(self.run_dir), "--observed", "the health check exits 0; the org is up")
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        self.assertEqual(self.status()["status"], "active")
        decision = store.read_record(self.run_dir / "decisions" / (action + ".md"))
        self.assertEqual((decision["kind"], decision["reply"]), ("service", "the health check exits 0; the org is up"))

    def test_a_run_not_waiting_refuses_a_reply_and_awaiting_needs_blocked(self) -> None:
        shiploop("pause", "--run-dir", str(self.run_dir), "--reason", "user asked")
        refused = shiploop("resume", "--run-dir", str(self.run_dir), "--answer", "yes")
        self.assertIn("not waiting on an answer", refused.stderr)
        self.assertEqual(shiploop("resume", "--run-dir", str(self.run_dir)).returncode, 0)
        action = self.status()["action"]
        path = self.run_dir / "inbox" / (action + ".md")
        path.parent.mkdir(exist_ok=True)
        path.write_text(store.dumps({"outcome": "done", "summary": "x (S1)", "awaiting": self.QUESTION}, "test result"))
        done = shiploop("complete", "--run-dir", str(self.run_dir), "--action", action, "--result", str(path))
        self.assertIn("awaiting is allowed only on a blocked result", done.stderr)

class HookDecisionTests(KeepaliveTestCase):
    def test_recorded_payloads_bind_and_continue_in_each_host_format(self) -> None:
        for host in RECORDED_HOSTS:
            with self.subTest(host=host):
                keepalive.release_owner(str(self.run_dir))  # each host on its own
                session = f"{host}-session"
                self.assertEqual(self.hook("observe", host, self.payload(host, "observe", session)),
                                 {} if host == "antigravity" else None)
                self.assertEqual(keepalive.load_binding(host, session)["run_dir"], str(self.run_dir))
                reply = self.hook("stop", host, self.payload(host, "stop", session))
                if host == "cursor":
                    self.assertIn("next --run-dir", reply["followup_message"])
                elif host == "antigravity":
                    self.assertEqual(reply["decision"], "continue")
                    self.assertIn("next --run-dir", reply["reason"])
                else:
                    self.assertEqual(reply["decision"], "block")
                    self.assertIn("next --run-dir", reply["reason"])

    def test_missing_ordinary_callback_keeps_the_same_action_unfinished(self) -> None:
        self.hook("observe", "claude", self.payload("claude", "observe"))
        self.assertEqual(self.hook("stop", "claude", self.payload("claude", "stop"))["decision"], "block")
        with mock.patch.object(keepalive, "DUPLICATE_WINDOW_SECONDS", 0):
            reply = self.hook("stop", "claude", self.payload("claude", "stop"))
            self.assertEqual(reply["decision"], "block")
            status = self.status()
            before = (self.run_dir / "state.md").read_bytes()
            refused = shiploop("complete", "--run-dir", str(self.run_dir), "--action", status["action"])
            self.assertNotEqual(refused.returncode, 0)
            for _ in range(2):
                self.assertEqual(self.hook("stop", "claude", self.payload("claude", "stop"))["decision"], "block")
            self.assertEqual((self.run_dir / "state.md").read_bytes(), before)
            self.assertEqual(self.status()["action"], status["action"])

    def test_running_next_between_two_stops_is_not_progress(self) -> None:
        # Context recovery re-binds the same action without clearing the progress memory.
        # Its missing required callback still leaves the action unfinished.
        self.hook("observe", "claude", self.payload("claude", "observe"))
        with mock.patch.object(keepalive, "DUPLICATE_WINDOW_SECONDS", 0):
            self.assertEqual(self.hook("stop", "claude", self.payload("claude", "stop"))["decision"], "block")
            reread = self.payload("claude", "observe")
            reread["tool_input"]["command"] = f"python3 {SCRIPTS / 'shiploop'} next --run-dir {self.run_dir}"
            self.hook("observe", "claude", reread)
            self.assertIn("last_block_progress", keepalive.load_binding("claude", "session-1"))
            reply = self.hook("stop", "claude", self.payload("claude", "stop"))
        self.assertEqual(reply["decision"], "block")

    def test_each_stop_decision_is_logged_with_its_reason(self) -> None:
        self.hook("observe", "claude", self.payload("claude", "observe"))
        self.hook("stop", "claude", self.payload("claude", "stop"))
        shiploop("pause", "--run-dir", str(self.run_dir), "--reason", "user asked")
        with mock.patch.object(keepalive, "DUPLICATE_WINDOW_SECONDS", 0):
            self.hook("stop", "claude", self.payload("claude", "stop"))
        log = [json.loads(line) for line in (self.temp / "state" / "decisions.log").read_text().splitlines()]
        self.assertEqual([(entry["decision"], entry["why"]) for entry in log],
                         [("continue", "run can move; continuation 1"), ("allow", "run is paused: user asked")])
        self.assertNotIn("session-1", json.dumps(log))

    def test_a_second_registration_in_the_same_moment_repeats_the_decision(self) -> None:
        self.hook("observe", "claude", self.payload("claude", "observe"))
        first = self.hook("stop", "claude", self.payload("claude", "stop"))
        self.assertEqual(self.hook("stop", "claude", self.payload("claude", "stop")), first)

    def test_a_paused_run_ends_the_turn_and_drops_the_binding(self) -> None:
        self.hook("observe", "codex", self.payload("codex", "observe"))
        shiploop("pause", "--run-dir", str(self.run_dir), "--reason", "user asked to stop")
        self.assertIsNone(self.hook("stop", "codex", self.payload("codex", "stop")))
        self.assertIsNone(keepalive.load_binding("codex", "session-1"))

    def stop_command(self, line_prefix: str) -> list[str]:
        """The command a packet line tells the model to run, as its words, with the reason placeholder filled in."""
        text = _packet_file_text(self.packet)
        line = next(row for row in text.splitlines() if row.startswith(line_prefix))
        return [("--reason=user asked to stop" if word.startswith("--reason=") else word)
                for word in shlex.split(line.split(": ", 1)[1].split(" (only when", 1)[0])]

    def test_the_printed_pause_text_runs_through_the_status_hook_and_ends_the_turn(self) -> None:
        import shiploop_status_hook as status_hook
        command = self.stop_command("Pause without consuming the action: ")
        self.assertEqual(status_hook._verb(shlex.join(command)), ("pause", None))
        self.hook("observe", "codex", self.payload("codex", "observe"))
        ran = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        self.assertEqual(self.status()["status"], "paused")
        self.assertIsNone(self.hook("stop", "codex", self.payload("codex", "stop")))
        self.assertIsNone(keepalive.load_binding("codex", "session-1"))

    def test_the_halt_text_is_the_pause_command_with_its_verb_changed_and_it_stops_the_run(self) -> None:
        import shiploop_status_hook as status_hook
        text = _packet_file_text(self.packet)
        self.assertEqual(sum(row == nav.HALT_LINE for row in text.splitlines()), 1)
        self.assertIn("the Pause command with `halt` in place of `pause`", nav.HALT_LINE)
        pause = self.stop_command("Pause without consuming the action: ")
        halt = [("halt" if word == "pause" else word) for word in pause]   # what the printed sentence says to type
        self.assertEqual(status_hook._verb(shlex.join(halt)), ("halt", None))
        self.hook("observe", "codex", self.payload("codex", "observe"))
        ran = subprocess.run(halt, capture_output=True, text=True)
        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        self.assertEqual(self.status()["status"], "halted")
        self.assertIsNone(self.hook("stop", "codex", self.payload("codex", "stop")))

    def test_unbound_sessions_and_session_end_stops_are_allowed(self) -> None:
        self.assertIsNone(self.hook("stop", "claude", self.payload("claude", "stop")))
        self.hook("observe", "claude", self.payload("claude", "observe"))
        ending = {**self.payload("claude", "stop"), "reason": "channel_closed"}
        self.assertIsNone(self.hook("stop", "claude", ending))

    def test_another_hosts_payload_is_left_to_that_host(self) -> None:
        self.assertIsNone(self.hook("observe", "cursor", self.payload("claude", "observe")))
        self.assertEqual(list((self.temp / "state").glob("bindings/*")), [])

    def test_a_shiploop_command_binds_even_when_its_output_was_filtered(self) -> None:
        payload = {"hook_event_name": "PostToolUse", "session_id": "filtered-1",
                   "transcript_path": "/tmp/shiploop-keepalive-fixture", "prompt_id": "p-1",
                   "tool_input": {"command": f"python3 shiploop next --run-dir={self.run_dir} | tail -5"},
                   "tool_response": {"stdout": "=== ShipLoop status === (filtered, no marker)"}}
        self.hook("observe", "claude", payload)
        binding = keepalive.load_binding("claude", "filtered-1")
        self.assertIsNotNone(binding)
        self.assertEqual(binding["run_id"], self.status()["run_id"])
        for query in ("hook-status", "status", "report"):
            payload = {"hook_event_name": "PostToolUse", "session_id": f"reader-{query}",
                       "transcript_path": "/tmp/shiploop-keepalive-fixture", "prompt_id": "p-1",
                       "tool_input": {"command": f"python3 shiploop {query} --run-dir {self.run_dir}"}}
            self.hook("observe", "claude", payload)
            self.assertIsNone(keepalive.load_binding("claude", f"reader-{query}"), query)

    def test_the_improve_stage_commands_bind_and_the_retired_improve_complete_does_not(self) -> None:
        """The Improve stage is driven by `complete` (naming its id), improve-bind, a restart through improve-start and improve-reconcile;
        `improve-complete` is gone, so a command that names it is no driving command."""
        for verb, binds in (("complete --action=nav-i", True), ("improve-bind --action=nav-i --skill-card=/x/SKILL.md", True),
                            ("improve-start --action=nav-i --restart-stopped", True),
                            ("improve-reconcile --action=nav-i --result=/x/r.md", True), ("improve-complete --action=nav-i", False)):
            session = "improve-" + verb.split()[0]
            payload = {"hook_event_name": "PostToolUse", "session_id": session,
                       "transcript_path": "/tmp/shiploop-keepalive-fixture", "prompt_id": "p-1",
                       "tool_input": {"command": f"python3 shiploop {verb} --run-dir={self.run_dir}"},
                       "tool_response": {"stdout": "=== ShipLoop status === (filtered, no marker)"}}
            self.hook("observe", "claude", payload)
            self.assertEqual(keepalive.load_binding("claude", session) is not None, binds, verb)

    def test_marker_copied_from_elsewhere_does_not_bind(self) -> None:
        payload = self.payload("claude", "observe")
        payload["tool_response"]["stdout"] = f"SHIPLOOP-RUN run=nav-0000 rev=0 dir={self.run_dir}"
        self.hook("observe", "claude", payload)
        self.assertIsNone(keepalive.load_binding("claude", "session-1"))

    def test_live_marker_printed_by_a_reading_command_does_not_bind(self) -> None:
        """A session that only reads a packet file or log must not be kept alive for the run."""
        for host, command in (("claude", f"cat {self.run_dir}/packets/next.md"),
                              ("codex", "python3 progress.py out | grep SHIPLOOP")):
            payload = self.payload(host, "observe", f"reader-{host}")
            for key in ("tool_input", "toolInput"):
                if isinstance(payload.get(key), dict):
                    payload[key]["command"] = command
            self.hook("observe", host, payload)
            self.assertIsNone(keepalive.load_binding(host, f"reader-{host}"), host)
        # Callback text in the output of a reading command names the run but must not bind either.
        dump = self.payload("claude", "observe", "dumper")
        dump["tool_input"]["command"] = "python3 - < summarize-events.py"
        dump["tool_response"]["stdout"] = (f"python3 shiploop improve-bind --run-dir={self.run_dir} "
                                           "--action=nav-1 --skill-card=/x/SKILL.md")
        self.hook("observe", "claude", dump)
        self.assertIsNone(keepalive.load_binding("claude", "dumper"))
        # The same live marker from a driving command still binds.
        self.hook("observe", "claude", self.payload("claude", "observe", "driver"))
        self.assertIsNotNone(keepalive.load_binding("claude", "driver"))

    def test_disabled_and_malformed_input_never_reply(self) -> None:
        self.hook("observe", "claude", self.payload("claude", "observe"))
        with mock.patch.dict(os.environ, {"SHIPLOOP_KEEPALIVE": "off"}):
            self.assertIsNone(self.hook("stop", "claude", self.payload("claude", "stop")))
        self.assertEqual(keepalive.run_hook("stop", "claude", "{not json"), "")
        self.assertTrue((self.temp / "state" / "errors.log").exists())

    def test_hook_entry_point_prints_the_host_reply(self) -> None:
        self.hook("observe", "claude", self.payload("claude", "observe"))
        result = subprocess.run([sys.executable, str(SCRIPTS / "shiploop-hook"), "stop", "--host", "claude"],
                                input=json.dumps(self.payload("claude", "stop")), capture_output=True,
                                text=True, env=os.environ.copy(), check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["decision"], "block")


class ProgressAndTurnTests(KeepaliveTestCase):
    """What counts as progress, and how continuations are counted within a turn."""

    def claude_stop(self, active: bool, **extra) -> dict:
        payload = {**self.payload("claude", "stop", "turn-1"), "stop_hook_active": active, **extra}
        with mock.patch.object(keepalive, "DUPLICATE_WINDOW_SECONDS", 0):
            return keepalive.stop("claude", payload)

    def bind_claude(self) -> None:
        self.hook("observe", "claude", self.payload("claude", "observe", "turn-1"))

    def test_a_refused_callback_counts_as_progress(self) -> None:
        self.bind_claude()
        self.assertEqual(self.claude_stop(False)["decision"], "continue")
        refused = shiploop("complete", "--run-dir", str(self.run_dir), "--action", "nav-unknown",
                           "--result", str(self.run_dir / "inbox" / "nav-unknown.md"))
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("do not end the turn over a refused callback", refused.stderr)
        self.assertEqual(self.claude_stop(True)["decision"], "continue")
        self.assertEqual(self.claude_stop(True)["decision"], "continue")

    def test_refusals_without_an_accepted_result_keep_counting_as_progress_with_no_release(self) -> None:
        # Owner 2026-10-24: no run caps.  The 22-continuation release is gone: 23 and more refused callbacks with no
        # accepted result still continue; a required callback stays pending even with unchanged progress.
        self.assertFalse(hasattr(keepalive, "STUCK_CONTINUATIONS"))
        self.hook("observe", "claude", self.payload("claude", "observe"))
        stop = lambda: keepalive.stop("claude", self.payload("claude", "stop"))  # noqa: E731
        with mock.patch.object(keepalive, "DUPLICATE_WINDOW_SECONDS", 0):
            for attempt in range(23 + 5):
                (self.run_dir / "callback-attempts").write_text(str(attempt + 1))
                decision = stop()
                self.assertEqual(decision["decision"], "continue", attempt)
            stalled = stop()  # no new callback: the same required completion is still missing
            self.assertEqual(stalled["decision"], "continue")

    def test_a_running_background_task_is_a_wait_not_a_stop(self) -> None:
        self.bind_claude()
        self.claude_stop(False)
        decision = self.claude_stop(True, background_tasks=[{"id": "deploy"}])
        self.assertEqual(decision["decision"], "continue")
        self.assertIn("background task is still running", decision["reason"])

    def test_a_second_session_is_told_who_owns_the_run(self) -> None:
        self.bind_claude()
        self.claude_stop(False)
        self.hook("observe", "claude", self.payload("claude", "observe", "turn-2"))
        with mock.patch.object(keepalive, "DUPLICATE_WINDOW_SECONDS", 0):
            decision = keepalive.stop("claude", self.payload("claude", "stop", "turn-2"))
        self.assertEqual(decision["decision"], "allow")
        self.assertIn("another session owns this run", decision["notice"])

    def test_each_reported_loop_iteration_is_progress(self) -> None:
        # The innermost Until Loop's iteration number is part of progress: an Improve review's, else the current inner
        # stage's (before 2026-10-28 only Improve passes counted, so a stage loop's reports looked like no progress).
        sys.path.insert(0, str(SCRIPTS))
        import shiploop_loops as loops
        import shiploop_protocol as protocol
        import shiploop_standalone_improve as standalone
        receipt = self.temp / "packet.json"
        receipt.write_text(json.dumps({"status": "active", "progress": {"action_number": 3},
                                       "next_argv": ["python3", "runtime.py", "next", "--state", "s.json"]}))
        with mock.patch.object(standalone, "receipt_path", return_value=receipt):
            self.assertEqual(protocol._loop_iteration(self.run_dir, {"active_improve": {"skill": "card"}}), 3)
        stage_receipt = loops.receipt_path(self.run_dir, "nav-stage")
        stage_receipt.parent.mkdir(parents=True, exist_ok=True)
        stage_receipt.write_text(json.dumps({"status": "complete", "progress": {"action_number": 4}, "next_argv": None}))
        with mock.patch.object(loops, "cursor", return_value=("verify", "nav-stage", "W1")):
            self.assertEqual(protocol._loop_iteration(self.run_dir, {"active_improve": None}), 4)
        self.assertEqual(protocol._loop_iteration(self.run_dir, {"active_improve": None}), 0)  # intake: no loop
        self.assertEqual(self.status()["progress"], "0.0.0")


class OwnerProcessTests(unittest.TestCase):
    """A dead session's claim is taken over at once (owner, 2026-10-28): the owner's host process is recorded when it
    claims, and a claim whose process is gone frees the run without waiting OWNER_STALE_SECONDS. A live owner keeps it."""

    START = "Wed Oct 28 08:14:39 2026"

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="shiploop-keepalive-owner-")
        self.addCleanup(temp.cleanup)
        patcher = mock.patch.dict(os.environ, {"SHIPLOOP_KEEPALIVE_HOME": temp.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.run_dir = "/runs/r"

    @staticmethod
    def row(ppid: int, name: str, age: int, start: str = START) -> dict:
        return {"ppid": ppid, "name": name, "age": age, "start": start}

    def table(self, **rows: dict) -> mock._patch:
        return mock.patch.object(keepalive, "_processes", return_value={int(pid[1:]): row for pid, row in rows.items()})

    def owned_by(self, session: str, process: dict | None) -> None:
        with mock.patch.object(keepalive, "host_process", return_value=process):
            self.assertTrue(keepalive.claim_owner(self.run_dir, "claude", session))

    def found(self, **rows: dict) -> dict | None:
        """host_process() from a hook with pid 101 (age 0) whose parent is pid 100."""
        with self.table(p101=self.row(100, "Python", 0), **rows), \
                mock.patch.object(keepalive.os, "getpid", return_value=101), \
                mock.patch.object(keepalive.os, "getppid", return_value=100):
            return keepalive.host_process()

    def test_the_host_process_is_the_nearest_ancestor_past_launchers(self) -> None:
        # The probe (docs/shiploop-owed-outcome-evidence/host_process_probe.out): Claude Code runs a hook directly, so
        # the hook's parent is the session's `claude`, 2 seconds old at its first hook. A shell launcher may sit between.
        self.assertEqual(self.found(p100=self.row(90, "sh", 0), p90=self.row(70, "Python", 0),
                                    p70=self.row(60, "claude", 2), p60=self.row(1, "zsh", 9000)),
                         {"pid": 70, "start": self.START})

    def test_it_never_guesses_past_a_process_that_started_with_the_hook(self) -> None:
        # An unknown launcher (not a shell) started with the hook: not the host, and nothing above it is looked at.
        self.assertIsNone(self.found(p100=self.row(70, "hook-runner", 1), p70=self.row(1, "claude", 3000)))
        self.assertIsNone(self.found(p100=self.row(90, "sh", 0), p90=self.row(1, "zsh", 9000)))  # only launchers

    def test_a_dead_owners_claim_is_taken_over_at_once(self) -> None:
        self.owned_by("crashed", {"pid": 70, "start": self.START})
        with self.table(p71=self.row(1, "claude", 50)), mock.patch.object(keepalive, "host_process", return_value=None):
            self.assertTrue(keepalive.claim_owner(self.run_dir, "claude", "next"))
        self.assertEqual(keepalive._load_owner(self.run_dir)["owner"], "claude:next")

    def test_a_reused_pid_is_not_the_owner(self) -> None:
        self.owned_by("crashed", {"pid": 70, "start": self.START})
        with self.table(p70=self.row(1, "claude", 50, "Thu Oct 29 09:00:00 2026")), \
                mock.patch.object(keepalive, "host_process", return_value=None):
            self.assertTrue(keepalive.claim_owner(self.run_dir, "claude", "next"))

    def test_a_live_owner_keeps_the_run_however_quiet_and_an_unknown_one_waits_for_time(self) -> None:
        self.owned_by("busy", {"pid": 70, "start": self.START})
        with self.table(p70=self.row(1, "claude", 5000)):
            self.assertFalse(keepalive.claim_owner(self.run_dir, "claude", "next"))
        keepalive.release_owner(self.run_dir)
        self.owned_by("unknown", None)
        with self.table(), mock.patch.object(keepalive, "host_process", return_value=None):
            self.assertFalse(keepalive.claim_owner(self.run_dir, "claude", "next"))  # fresh, process unknown
            with mock.patch.object(keepalive, "OWNER_STALE_SECONDS", 0):
                self.assertTrue(keepalive.claim_owner(self.run_dir, "claude", "next"))  # the time rule still frees it

    def test_the_owner_keeps_its_live_process_and_a_resume_elsewhere_records_the_new_one(self) -> None:
        self.owned_by("owner", {"pid": 70, "start": self.START})
        with self.table(p70=self.row(1, "claude", 5000)), mock.patch.object(keepalive, "host_process") as found:
            self.assertTrue(keepalive.claim_owner(self.run_dir, "claude", "owner"))
            found.assert_not_called()  # a live record is kept, not looked up again on every hook
        resumed = {"pid": 80, "start": "Wed Oct 28 18:00:00 2026"}
        with self.table(p80=self.row(1, "claude", 60)), mock.patch.object(keepalive, "host_process", return_value=resumed):
            self.assertTrue(keepalive.claim_owner(self.run_dir, "claude", "owner"))
        self.assertEqual(keepalive._load_owner(self.run_dir)["process"], resumed)

    def test_a_claim_with_no_process_yet_looks_again_on_its_next_hook(self) -> None:
        self.owned_by("owner", None)  # its first hook came too soon after the host started
        found = {"pid": 70, "start": self.START}
        with mock.patch.object(keepalive, "host_process", return_value=found):
            self.assertTrue(keepalive.claim_owner(self.run_dir, "claude", "owner"))
        self.assertEqual(keepalive._load_owner(self.run_dir)["process"], found)

    def test_a_process_table_that_cannot_be_read_says_nothing_about_a_live_owner(self) -> None:
        # `ps` missing, timed out or hidden by a sandbox gives an empty table: that is unknown, not "the owner is gone".
        self.owned_by("busy", {"pid": 70, "start": self.START})
        with self.table(), mock.patch.object(keepalive, "host_process", return_value=None):
            self.assertIsNone(keepalive.owner_process_alive({"pid": 70, "start": self.START}))
            self.assertFalse(keepalive.claim_owner(self.run_dir, "claude", "next"))
        self.assertEqual(keepalive._load_owner(self.run_dir)["owner"], "claude:busy")

    def test_the_owner_keeps_its_recorded_process_through_a_hook_that_cannot_read_the_table(self) -> None:
        recorded = {"pid": 70, "start": self.START}
        self.owned_by("owner", recorded)
        with self.table(), mock.patch.object(keepalive, "host_process", return_value=None):
            self.assertTrue(keepalive.claim_owner(self.run_dir, "claude", "owner"))
        self.assertEqual(keepalive._load_owner(self.run_dir)["process"], recorded)


class HealthNoticeTests(KeepaliveTestCase):
    """A session that keeps printing packets without ever binding is told its hooks are off."""

    def env(self, session: str) -> dict:
        return {"CLAUDECODE": "1", "CLAUDE_CODE_SESSION_ID": session}

    def test_the_second_unbound_packet_warns_once(self) -> None:
        run = str(self.run_dir)
        self.assertIsNone(keepalive.health_notice(run, self.env("h1")))
        notice = keepalive.health_notice(run, self.env("h1"))
        self.assertIn("keepalive is not active in this claude session", notice)
        self.assertIn(keepalive.HEALTH_REMEDY["claude"], notice)
        self.assertIsNone(keepalive.health_notice(run, self.env("h1")))

    def test_a_bound_session_never_warns(self) -> None:
        self.hook("observe", "claude", self.payload("claude", "observe", "h2"))
        for _ in range(3):
            self.assertIsNone(keepalive.health_notice(str(self.run_dir), self.env("h2")))
        self.assertIsNone(keepalive.health_notice(str(self.run_dir), {}))

    def test_the_cli_prints_the_warning_on_stderr(self) -> None:
        env = {k: v for k, v in os.environ.items()
               if k not in ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "GROK_AGENT", "GROK_SESSION_ID",
                            "ANTIGRAVITY_AGENT", "ANTIGRAVITY_CONVERSATION_ID")}
        env.update(self.env("h3"))
        argv = [sys.executable, str(SCRIPTS / "shiploop"), "next", "--run-dir", str(self.run_dir)]
        first = subprocess.run(argv, capture_output=True, text=True, env=env, check=False)
        second = subprocess.run(argv, capture_output=True, text=True, env=env, check=False)
        self.assertNotIn("keepalive is not active", first.stderr)
        self.assertIn("keepalive is not active in this claude session", second.stderr)
        self.assertEqual(first.stdout, second.stdout)


class ConcurrencyTests(KeepaliveTestCase):
    """Several agents on one run: only the owner is kept alive."""

    def bind(self, host: str, session: str) -> None:
        self.hook("observe", host, self.payload(host, "observe", session))

    def stop_decision(self, host: str, session: str) -> dict:
        return keepalive.stop(host, self.payload(host, "stop", session))

    def test_second_session_on_a_run_is_not_kept_alive(self) -> None:
        self.bind("claude", "owner")
        self.bind("codex", "worker")  # e.g. a chain worker or a second terminal
        worker = self.stop_decision("codex", "worker")
        self.assertEqual((worker["decision"], worker["why"]), ("allow", "another session owns this run"))
        self.assertIn("another session owns this run", worker["notice"])
        self.assertEqual(self.stop_decision("claude", "owner")["decision"], "continue")

    def test_ownership_passes_on_when_the_owners_turn_ends(self) -> None:
        self.bind("claude", "first")
        self.assertEqual(self.stop_decision("claude", "first")["decision"], "continue")
        with mock.patch.object(keepalive, "DUPLICATE_WINDOW_SECONDS", 0):
            self.assertEqual(self.stop_decision("claude", "first")["decision"], "continue")
        keepalive.session_end("claude", {"session_id": "first"})
        self.bind("claude", "second")  # the next session picks the run up
        self.assertEqual(self.stop_decision("claude", "second")["decision"], "continue")

    def test_a_silent_owner_goes_stale(self) -> None:
        self.bind("claude", "crashed")
        with mock.patch.object(keepalive, "OWNER_STALE_SECONDS", 0):
            self.bind("codex", "fresh")
            self.assertEqual(self.stop_decision("codex", "fresh")["decision"], "continue")

    def test_owner_activity_without_a_marker_keeps_the_claim(self) -> None:
        self.bind("claude", "owner")
        plain = self.payload("claude", "observe", "owner")
        plain["tool_response"]["stdout"] = "ran the tests"
        with mock.patch.object(keepalive, "OWNER_STALE_SECONDS", 3600):
            self.hook("observe", "claude", plain)
            self.bind("codex", "late")
            self.assertEqual(self.stop_decision("codex", "late")["why"], "another session owns this run")

    def test_subagent_tool_calls_never_bind(self) -> None:
        payload = {**self.payload("claude", "observe", "child"), "agent_id": "a1", "agent_type": "general"}
        self.hook("observe", "claude", payload)
        self.assertIsNone(keepalive.load_binding("claude", "child"))

    def test_parallel_stops_for_one_session_agree_and_stay_valid(self) -> None:
        self.bind("claude", "owner")
        payload = json.dumps(self.payload("claude", "stop", "owner"))
        with ThreadPoolExecutor(max_workers=12) as pool:
            replies = list(pool.map(lambda _: keepalive.run_hook("stop", "claude", payload), range(12)))
        self.assertEqual({json.loads(reply)["decision"] for reply in replies}, {"block"})
        self.assertEqual(keepalive.load_binding("claude", "owner")["last_block_progress"],
                         self.status()["progress"])
        self.assertFalse((self.temp / "state" / "errors.log").exists())

    def test_parallel_sessions_elect_exactly_one_owner(self) -> None:
        sessions = [f"s{number}" for number in range(10)]
        with ThreadPoolExecutor(max_workers=10) as pool:
            list(pool.map(lambda session: self.bind("claude", session), sessions))
        decisions = [self.stop_decision("claude", session)["decision"] for session in sessions]
        self.assertEqual(decisions.count("continue"), 1)

    def test_plugin_hooks_resolve_the_calling_host(self) -> None:
        for env, payload_host, expected in ((
                {"CURSOR_PLUGIN_ROOT": "/p"}, "cursor", "cursor"),
                ({}, "antigravity", "antigravity"), ({}, "codex", "codex"), ({}, "claude", "claude")):
            with self.subTest(expected=expected), mock.patch.dict(os.environ, env):
                keepalive.release_owner(str(self.run_dir))
                raw_obs = keepalive.run_hook("observe", "auto", json.dumps(self.payload(payload_host, "observe", f"auto-{expected}")))
                if expected == "antigravity":
                    self.assertEqual(raw_obs, "{}")
                else:
                    self.assertEqual(raw_obs, "")
                self.assertIsNotNone(keepalive.load_binding(expected, f"auto-{expected}"))
                reply = self.hook("stop", "auto", self.payload(payload_host, "stop", f"auto-{expected}"))
                if expected == "antigravity":
                    self.assertEqual(reply.get("decision"), "continue")
                else:
                    self.assertIn("followup_message" if expected == "cursor" else "decision", reply)

    def test_antigravity_reactive_subagent_wait_preserves_ownership_and_execution_num_tracks_continuation(self) -> None:
        self.assertEqual(keepalive.detected_host(self.payload("antigravity", "observe")), "antigravity")
        quoted = self.payload("antigravity", "observe", "quoted-1")
        quoted["toolCall"]["args"]["CommandLine"] = f'python3 "{SCRIPTS / "shiploop"}" next --run-dir "{self.run_dir}"'
        self.assertEqual(keepalive.command_run_dir(quoted), str(self.run_dir))
        self.hook("observe", "antigravity", quoted)
        self.assertEqual(keepalive.load_binding("antigravity", "quoted-1")["run_dir"], str(self.run_dir))
        keepalive.release_owner(str(self.run_dir))
        self.hook("observe", "antigravity", self.payload("antigravity", "observe", "parent-1"))
        # Parent yields with fullyIdle=False while invoke_subagent runs: allow without releasing or caching last_decision.
        yielding = {**self.payload("antigravity", "stop", "parent-1"), "fullyIdle": False}
        self.assertEqual(self.hook("stop", "antigravity", yielding), {"decision": "allow"})
        self.assertEqual(keepalive._load_owner(str(self.run_dir)).get("owner"), "antigravity:parent-1")
        self.assertNotIn("last_decision", keepalive.load_binding("antigravity", "parent-1") or {})
        # Subagent observing/stopping on the same run is not kept alive and cannot steal ownership.
        self.hook("observe", "antigravity", self.payload("antigravity", "observe", "child-1"))
        self.assertEqual(self.hook("stop", "antigravity", self.payload("antigravity", "stop", "child-1")),
                         {"decision": "allow"})
        # When parent resumes and hits a real idle turn end within 3s, it still gets continue cleanly.
        resumed_stop = self.hook("stop", "antigravity", self.payload("antigravity", "stop", "parent-1"))
        self.assertEqual(resumed_stop["decision"], "continue")
        # Non-NO_TOOL_CALL terminationReason allows even when active.
        cancelled = {**self.payload("antigravity", "stop", "parent-1"), "terminationReason": "USER_CANCELED"}
        with mock.patch.object(keepalive, "DUPLICATE_WINDOW_SECONDS", 0):
            self.assertEqual(self.hook("stop", "antigravity", cancelled), {"decision": "allow"})
        # executionNum > 0 counts as turn continuation even with continuationActive=False.
        self.assertTrue(keepalive._turn_continued({"executionNum": 1, "continuationActive": False}))
        self.assertFalse(keepalive._turn_continued({"executionNum": 0, "continuationActive": False}))

    def test_antigravity_health_notice_and_nested_skill_gate_exemption(self) -> None:
        env = {"ANTIGRAVITY_AGENT": "1", "ANTIGRAVITY_CONVERSATION_ID": "conv-1"}
        self.assertIsNone(keepalive.health_notice(str(self.run_dir), env))
        notice = keepalive.health_notice(str(self.run_dir), env)
        self.assertIn("keepalive is not active in this antigravity session", notice)
        self.assertIn("shiploop-hook install --host antigravity", notice)
        self.assertEqual(keepalive.skill_gate(str(self.run_dir), {**env, "CLAUDECODE": "1", "CLAUDE_CODE_SESSION_ID": "s"})[0], False)


class SessionEndTests(KeepaliveTestCase):
    """The host ends a session (a /clear, an exit): the run it owned is released at once, so the next session need not
    wait OWNER_STALE_SECONDS (owner, 2026-10-28). A killed session sends nothing; OwnerProcessTests covers that."""

    def bind(self, host: str, session: str) -> str:
        self.hook("observe", host, self.payload(host, "observe", session))
        return keepalive.load_binding(host, session)["run_dir"]

    def test_each_hosts_session_end_releases_the_run_its_session_owned(self) -> None:
        for host in ("claude", "codex", "cursor"):
            with self.subTest(host=host):
                session = f"ending-{host}"
                run_dir = self.bind(host, session)
                self.assertEqual(keepalive._load_owner(run_dir).get("owner"), f"{host}:{session}")
                # As the plugin's hook runs it: the host is read from the payload. Codex's has no turn_id at session
                # end, so it reads as Claude's; the session id is looked up under every host.
                self.hook("session-end", "auto", self.payload(host, "session-end", session))
                self.assertIsNone(keepalive.load_binding(host, session))
                self.assertEqual(keepalive._load_owner(run_dir), {})

    def test_the_next_session_takes_the_run_at_once(self) -> None:
        self.bind("claude", "cleared")
        self.hook("session-end", "auto", self.payload("claude", "session-end", "cleared"))
        self.bind("claude", "after-clear")
        self.assertEqual(self.stop_decision("claude", "after-clear")["decision"], "continue")

    def stop_decision(self, host: str, session: str) -> dict:
        return keepalive.stop(host, self.payload(host, "stop", session))

    def test_another_sessions_end_or_a_subagents_leaves_the_owner_alone(self) -> None:
        run_dir = self.bind("claude", "owner")
        self.bind("codex", "worker")
        self.hook("session-end", "auto", self.payload("codex", "session-end", "worker"))
        self.assertIsNone(keepalive.load_binding("codex", "worker"))
        child = {**self.payload("claude", "session-end", "owner"), "agent_id": "a1", "agent_type": "general"}
        self.hook("session-end", "auto", child)
        self.hook("session-end", "auto", self.payload("claude", "session-end", "never-bound"))
        self.assertEqual(keepalive._load_owner(run_dir).get("owner"), "claude:owner")
        self.assertIsNotNone(keepalive.load_binding("claude", "owner"))

    def session_end_rows(self) -> list[dict]:
        """The run trace's session-end rows (RUN/trace.jsonl), oldest first: the evidence a harness reads."""
        lines = (self.run_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines()
        return [row for row in map(json.loads, lines) if row.get("kind") == "hook" and row.get("hook") == "session-end"]

    def test_release_owner_says_whether_it_removed_a_claim(self) -> None:
        run_dir = str(self.run_dir)
        self.assertFalse(keepalive.release_owner(run_dir))                     # no one owns it
        self.assertFalse(keepalive.release_owner(run_dir, "claude", "ghost"))
        self.assertTrue(keepalive.claim_owner(run_dir, "claude", "owner"))
        self.assertFalse(keepalive.release_owner(run_dir, "claude", "other"))  # another session's claim stays
        self.assertFalse(keepalive.release_owner(run_dir, "codex", "owner"))   # the same id under another host is another
        self.assertEqual(keepalive._load_owner(run_dir).get("owner"), "claude:owner")
        self.assertTrue(keepalive.release_owner(run_dir, "claude", "owner"))
        self.assertFalse(keepalive.release_owner(run_dir, "claude", "owner"))  # already released
        self.assertTrue(keepalive.claim_owner(run_dir, "claude", "owner"))
        self.assertTrue(keepalive.release_owner(run_dir))                      # the driver's release, whoever owns it
        self.assertFalse(keepalive.release_owner(run_dir))

    def test_a_session_end_on_an_owned_run_records_the_release_in_the_trace(self) -> None:
        run_dir = self.bind("claude", "owner")
        self.assertEqual(self.session_end_rows(), [])
        self.hook("session-end", "auto", self.payload("claude", "session-end", "owner"))
        (row,) = self.session_end_rows()
        self.assertEqual((row["decision"], row["released"], row["host"], row["reason"]), ("release", True, "claude", "other"))
        self.assertEqual(row["session"], hashlib.sha256(b"owner").hexdigest()[:12])   # a hash, never the session id
        self.assertEqual(keepalive._load_owner(run_dir), {})
        self.assertIn("session-end → release", trace.event_line({**row, "i": 1}))

    def test_a_session_end_that_freed_nothing_records_released_false(self) -> None:
        run_dir = self.bind("claude", "owner")
        self.bind("codex", "worker")                       # bound to the run, owned by the claude session
        self.hook("session-end", "auto", self.payload("codex", "session-end", "worker"))
        self.assertEqual([(row["host"], row["released"]) for row in self.session_end_rows()], [("codex", False)])
        self.assertEqual(keepalive._load_owner(run_dir).get("owner"), "claude:owner")
        keepalive.release_owner(run_dir)                   # the stop hook (or the driver) freed the run first
        self.hook("session-end", "auto", self.payload("claude", "session-end", "owner"))
        self.assertEqual([(row["host"], row["released"]) for row in self.session_end_rows()],
                         [("codex", False), ("claude", False)])

    def test_the_next_sessions_claim_follows_the_recorded_release(self) -> None:
        self.bind("claude", "cleared")
        self.hook("session-end", "auto", self.payload("claude", "session-end", "cleared"))
        self.bind("claude", "after-clear")
        (row,) = self.session_end_rows()
        self.assertTrue(row["released"])
        self.assertEqual(keepalive._load_owner(str(self.run_dir)).get("owner"), "claude:after-clear")
        self.assertLess(keepalive._load_owner(str(self.run_dir))["seen"] - row["ts"], keepalive.OWNER_STALE_SECONDS)

    def test_a_session_bound_to_no_run_writes_nothing(self) -> None:
        before = (self.run_dir / "trace.jsonl").read_bytes()
        self.hook("session-end", "auto", self.payload("claude", "session-end", "never-bound"))
        self.assertEqual((self.run_dir / "trace.jsonl").read_bytes(), before)


class InstallTests(KeepaliveTestCase):
    def home(self) -> Path:
        return self.temp / "home"

    def test_install_status_uninstall_preserves_other_entries(self) -> None:
        settings = self.home() / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        other = {"type": "command", "command": "python3 /opt/other.py"}
        settings.write_text(json.dumps({"model": "opus", "hooks": {"Stop": [{"hooks": [other]}]}}))
        agy_cfg = self.home() / ".gemini" / "config" / "hooks.json"
        agy_cfg.parent.mkdir(parents=True)
        other_agy = {"Stop": [{"type": "command", "command": "./other.sh"}]}
        agy_cfg.write_text(json.dumps({"other-hook": other_agy}))
        active_hosts = [h for h in keepalive.HOSTS if h not in ("grok", "opencode")]
        for host in active_hosts:
            keepalive.install(host)
            self.assertEqual(keepalive.status(host), "installed", host)
            keepalive.install(host)  # idempotent
        agy_data = json.loads(agy_cfg.read_text())
        self.assertEqual(agy_data["other-hook"], other_agy)
        self.assertIn("observe --host antigravity", agy_data[keepalive.ANTIGRAVITY_HOOK_KEY]["PostToolUse"][0]["hooks"][0]["command"])
        data = json.loads(settings.read_text())
        self.assertEqual(len(data["hooks"]["Stop"]), 2)
        self.assertEqual(data["hooks"]["PostToolUse"][0]["matcher"], "Bash")
        self.assertIn("session-end --host claude", data["hooks"]["SessionEnd"][0]["hooks"][0]["command"])
        cursor = json.loads((self.home() / ".cursor" / "hooks.json").read_text())
        self.assertEqual(cursor["version"], 1)
        self.assertIn("afterShellExecution", cursor["hooks"])
        self.assertIn("session-end --host cursor", cursor["hooks"]["sessionEnd"][0]["command"])
        for host in active_hosts:
            keepalive.install(host, remove=True)
            self.assertEqual(keepalive.status(host), "absent", host)
        self.assertEqual(json.loads(agy_cfg.read_text()), {"other-hook": other_agy})
        self.assertEqual(json.loads(settings.read_text()),
                         {"model": "opus", "hooks": {"Stop": [{"hooks": [other]}]}})
        self.assertFalse((self.home() / ".cursor" / "hooks.json").exists())
        agy_cfg.unlink()
        keepalive.install("antigravity")
        self.assertTrue(agy_cfg.is_file())
        keepalive.install("antigravity", remove=True)
        self.assertFalse(agy_cfg.exists())

    def test_foreign_or_invalid_files_are_refused(self) -> None:
        settings = self.home() / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text("{broken")
        with self.assertRaises(keepalive.InstallError):
            keepalive.install("claude")
        codex = self.home() / ".codex" / "hooks.json"
        codex.parent.mkdir(parents=True)
        codex.write_text("{broken")
        result = subprocess.run([sys.executable, str(SCRIPTS / "shiploop-hook"), "install", "--host", "codex"],
                                capture_output=True, text=True, env=os.environ.copy(), check=False)
        self.assertEqual(result.returncode, 3)
        self.assertEqual(codex.read_text(), "{broken")

    def test_dry_run_writes_nothing(self) -> None:
        report = keepalive.install("claude", dry_run=True)
        self.assertIn("would add", report)
        self.assertFalse((self.home() / ".claude" / "settings.json").exists())

    def test_install_sh_never_writes_host_hook_config(self) -> None:
        result = subprocess.run(["bash", str(ROOT / "install.sh"), "--skill", "shiploop", "--claude-only"],
                                capture_output=True, text=True,
                                env={**os.environ, "CLAUDE_INSTALLED_PLUGINS_JSON": ""}, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(keepalive.status("claude"), "absent")


class SelfInstallTests(KeepaliveTestCase):
    """Grok never runs plugin hooks, so ShipLoop installs its global hooks there itself."""

    GROK = {"GROK_AGENT": "1"}

    def grok_file(self) -> Path:
        return self.temp / "home" / ".grok" / "hooks" / "shiploop-keepalive.json"

    def test_first_command_under_grok_installs_the_hooks_once(self) -> None:
        notice = keepalive.ensure_hooks(self.GROK)
        self.assertIn("installed the grok hooks", notice)
        self.assertEqual(keepalive.status("grok"), "installed")
        self.assertIsNone(keepalive.ensure_hooks(self.GROK))

    def test_other_hosts_and_a_disabled_keepalive_write_nothing(self) -> None:
        self.assertIsNone(keepalive.ensure_hooks({}))
        with mock.patch.dict(os.environ, {"SHIPLOOP_KEEPALIVE": "off"}):
            self.assertIsNone(keepalive.ensure_hooks(self.GROK))
        self.assertFalse(self.grok_file().exists())
        self.assertEqual(keepalive.status("claude"), "absent")

    def test_a_working_copy_is_kept_and_a_missing_one_repaired(self) -> None:
        keepalive.install("grok")
        installed = self.grok_file().read_text()
        other = self.temp / "other-copy" / "shiploop-hook"
        other.parent.mkdir()
        other.write_text("#!/bin/sh\n")
        moved = installed.replace(str(SCRIPTS / "shiploop-hook"), str(other))
        self.grok_file().write_text(moved)
        self.assertIsNone(keepalive.ensure_hooks(self.GROK))
        self.assertEqual(self.grok_file().read_text(), moved)
        other.unlink()
        self.assertIn("updated the grok hooks", keepalive.ensure_hooks(self.GROK))
        self.assertEqual(keepalive.status("grok"), "installed")

    def test_the_cli_reports_the_install_once_on_stderr(self) -> None:
        env = {**os.environ, **self.GROK}
        argv = [sys.executable, str(SCRIPTS / "shiploop"), "next", "--run-dir", str(self.run_dir)]
        first = subprocess.run(argv, capture_output=True, text=True, env=env, check=False)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("ShipLoop keepalive: installed the grok hooks", first.stderr)
        self.assertNotIn("ShipLoop keepalive:", first.stdout)
        second = subprocess.run(argv, capture_output=True, text=True, env=env, check=False)
        self.assertNotIn("ShipLoop keepalive:", second.stderr)
        self.assertEqual(first.stdout, second.stdout)


class MarketplacePackageTests(KeepaliveTestCase):
    """Installing the ShipLoop plugin from a marketplace brings the keepalive hooks."""

    # Generated file, plugin-root variable, recorded payload host, extra env.
    HOST_FILES = (
        ("hooks.json", "CLAUDE_PLUGIN_ROOT", "claude", {}),
        ("hooks.json", "CLAUDE_PLUGIN_ROOT", "grok", {"GROK_PLUGIN_ROOT": "set"}),
        ("codex.json", "PLUGIN_ROOT", "codex", {}),
        ("cursor.json", "CURSOR_PLUGIN_ROOT", "cursor", {}),
    )

    @staticmethod
    def commands(hooks: dict, event: str) -> list[str]:
        found = []
        for group in hooks["hooks"].get(event, []):
            found.extend(item["command"] for item in group.get("hooks", [group]))
        return [command for command in found if "keepalive" in command]

    def test_each_hosts_generated_hooks_run_keepalive_from_the_package(self) -> None:
        sys.path.insert(0, str(ROOT / "test"))
        import package_build

        plugin = package_build.plugins() / "skill-craft"
        for file_name, variable, host, extra in self.HOST_FILES:
            with self.subTest(host=host):
                keepalive.release_owner(str(self.run_dir))
                hooks = json.loads((plugin / "hooks" / file_name).read_text())
                cursor = file_name == "cursor.json"
                observe = self.commands(hooks, "afterShellExecution" if cursor else "PostToolUse")
                stop = self.commands(hooks, "stop" if cursor else "Stop")
                ended = self.commands(hooks, "sessionEnd" if cursor else "SessionEnd")
                self.assertEqual((len(observe), len(stop), len(ended)), (1, 1, 1))
                # Every packet is full, so no host needs a compaction hook.
                self.assertNotIn("SessionStart", hooks["hooks"])
                # Grok does not strip quotes: a quoted command becomes a file name
                # relative to the hooks folder ("command not found").
                for command in (*observe, *stop):
                    self.assertFalse(command.startswith(('"', "'")), command)
                env = {**os.environ, variable: str(plugin), **extra}
                if variable != "CURSOR_PLUGIN_ROOT":
                    env.pop("CURSOR_PLUGIN_ROOT", None)
                if not extra:
                    env.pop("GROK_PLUGIN_ROOT", None)
                session = f"plugin-{host}"
                for command, payload in ((observe[0], self.payload(host, "observe", session)),
                                         (stop[0], self.payload(host, "stop", session))):
                    # Hosts run the command through a shell with the variable set.
                    result = subprocess.run(["bash", "-c", command], input=json.dumps(payload),
                                            capture_output=True, text=True, env=env, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr)
                reply = json.loads(result.stdout)
                text = reply["followup_message"] if cursor else reply["reason"]
                self.assertIn(str(plugin), text)
                self.assertIsNotNone(keepalive.load_binding(host, session))
                ended_run = subprocess.run(["bash", "-c", ended[0]], input=json.dumps(self.payload(host, "session-end", session)),
                                           capture_output=True, text=True, env=env, check=False)
                self.assertEqual((ended_run.returncode, ended_run.stdout), (0, ""), ended_run.stderr)
                self.assertIsNone(keepalive.load_binding(host, session))  # the host ended the session: run released

        # Antigravity native plugin root hooks.json runs with cwd=plugin via relative ./skills/... paths.
        keepalive.release_owner(str(self.run_dir))
        root_hooks = json.loads((plugin / "hooks.json").read_text())
        agy_spec = root_hooks["shiploop"]
        obs_cmd = agy_spec["PostToolUse"][0]["hooks"][0]["command"]
        stop_cmd = agy_spec["Stop"][0]["command"]
        self.assertTrue(obs_cmd.startswith("./skills/shiploop/scripts/"))
        self.assertTrue(stop_cmd.startswith("./skills/shiploop/scripts/"))
        obs_run = subprocess.run(["sh", "-c", obs_cmd], cwd=plugin,
                                 input=json.dumps(self.payload("antigravity", "observe", "plugin-agy")),
                                 capture_output=True, text=True, check=False)
        self.assertEqual((obs_run.returncode, obs_run.stdout.strip()), (0, "{}"), obs_run.stderr)
        stop_run = subprocess.run(["sh", "-c", stop_cmd], cwd=plugin,
                                  input=json.dumps(self.payload("antigravity", "stop", "plugin-agy")),
                                  capture_output=True, text=True, check=False)
        self.assertEqual(stop_run.returncode, 0, stop_run.stderr)
        agy_reply = json.loads(stop_run.stdout)
        self.assertEqual(agy_reply["decision"], "continue")
        self.assertIn(str(self.run_dir), agy_reply["reason"])


class DriverTests(KeepaliveTestCase):
    def drive(self, host: str, runner, **options) -> tuple[int, list[str]]:
        """Drive with a clock that moves ``session_seconds`` (default 60) per host session."""
        lines: list[str] = []
        now = [0.0]

        def timed(argv, **kwargs):
            now[0] += options.get("session_seconds", 60)
            return runner(argv, **kwargs)

        code = keepalive.drive(host, str(self.run_dir), session_timeout=options.get("session_timeout", 60),
                               extra=["--model", "test"], cwd=None, max_minutes=options.get("max_minutes"),
                               out=lines.append, runner=timed, clock=lambda: now[0])
        return code, lines

    @staticmethod
    def done(argv, returncode=0):
        return subprocess.CompletedProcess(argv, returncode, "session output", "")

    def test_stops_and_reports_when_a_session_leaves_the_run_paused(self) -> None:
        calls = []

        def runner(argv, **kwargs):
            calls.append((argv, kwargs["cwd"]))
            shiploop("pause", "--run-dir", str(self.run_dir), "--reason", "needs a decision")
            return self.done(argv)

        code, lines = self.drive("claude", runner)
        self.assertEqual(code, keepalive.EXIT_NEEDS_USER)
        self.assertEqual(len(calls), 1)
        argv, cwd = calls[0]
        self.assertEqual(argv[:2], ["claude", "-p"])
        self.assertEqual(argv[-2:], ["--model", "test"])
        self.assertIn("next --run-dir", argv[2])
        self.assertEqual(cwd, str(self.repo))
        self.assertIn("run is paused after 1 session", lines[-1])

    def test_two_sessions_without_progress_stop_the_driver(self) -> None:
        status = self.status()
        status.pop("completion", None)  # no pending acknowledgement supplied by core
        with mock.patch.object(keepalive, "run_status", return_value=status):
            code, lines = self.drive("grok", lambda argv, **kwargs: self.done(argv))
        self.assertEqual(code, keepalive.EXIT_STUCK)
        self.assertIn("two sessions in a row", lines[-1])

    def test_pending_completion_survives_unchanged_sessions_with_the_shared_instruction(self) -> None:
        calls = []
        status = self.status()
        saved = (self.run_dir / "state.md").read_bytes()
        def runner(argv, **kwargs):
            calls.append(argv)
            self.assertIn(status["completion"], argv[2])
            self.assertEqual(self.status()["action"], status["action"])
            self.assertEqual((self.run_dir / "state.md").read_bytes(), saved)
            if len(calls) == 3:
                shiploop("pause", "--run-dir", str(self.run_dir), "--reason", "owner stop")
            return self.done(argv)
        code, _ = self.drive("claude", runner)
        self.assertEqual((code, len(calls)), (keepalive.EXIT_NEEDS_USER, 3))

    def test_two_timeouts_with_pending_completion_stop_the_driver_and_preserve_work(self) -> None:
        status = self.status()  # real active ordinary action; no mocked status or deadline
        self.assertTrue(status["completion"])
        partial = self.repo / "partial.md"
        partial.write_text("Keep this partial work.\n")
        saved = [path.read_bytes() for path in (self.run_dir / "state.md", partial)]
        calls = []

        def runner(argv, **kwargs):
            calls.append(argv)
            self.assertLessEqual(len(calls), 2, "pending completion must not exempt host timeouts")
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"], output="partial output", stderr="host hung")

        code, lines = self.drive("claude", runner)
        self.assertEqual((code, len(calls)), (keepalive.EXIT_STUCK, 2))
        self.assertIn("two sessions in a row", lines[-1])
        self.assertEqual([path.read_bytes() for path in (self.run_dir / "state.md", partial)], saved)
        self.assertEqual(self.status(), status)
        journal = self.temp / "state" / "drive" / status["run_id"] / "drive.log"
        entries = [json.loads(line) for line in journal.read_text().splitlines()]
        self.assertEqual([entry["exit"] for entry in entries], ["timeout", "timeout"])
        for entry in entries:
            log = Path(entry["log"]).read_text()
            self.assertIn("partial output", log)
            self.assertIn("host hung", log)

    def test_fresh_driver_reads_next_once_before_the_same_action_completion(self) -> None:
        status = self.status()
        same_session = keepalive._continue_reason(status)
        fresh = keepalive._driver_prompt(status)
        recovery = f"First run `{status['next']}` once"
        self.assertTrue(fresh.startswith(recovery), fresh)
        self.assertIn("current action, existing artifacts and exit/repeat conditions", fresh)
        self.assertIn("Continue only its remaining work", fresh)
        self.assertIn(status["completion"], fresh)
        self.assertIn("do not restart, reissue or replay", fresh)
        self.assertLess(fresh.index(recovery), fresh.index(status["completion"]))
        self.assertNotIn(recovery, same_session)
        for host in ("claude", "codex"):
            with self.subTest(host=host):
                argv = keepalive.host_argv(host, fresh, None, [])
                self.assertIn(fresh, argv)
                self.assertNotIn("--resume", argv)
        agy_argv = keepalive.host_argv("antigravity", fresh, None, ["--model", "claude-sonnet-5-5-medium", "--dangerously-skip-permissions"])
        self.assertEqual(agy_argv[-1], f"--print={fresh}")
        self.assertLess(agy_argv.index("--dangerously-skip-permissions"), agy_argv.index(f"--print={fresh}"))

    def test_a_host_that_fails_without_progress_is_reported_at_once(self) -> None:
        code, lines = self.drive("codex", lambda argv, **kwargs: self.done(argv, returncode=1))
        self.assertEqual(code, keepalive.EXIT_STUCK)
        self.assertIn("may have failed to start", lines[-1])

    def test_resuming_hosts_continue_the_bound_session(self) -> None:
        self.hook("observe", "cursor", self.payload("cursor", "observe", "chat-42"))
        prompt = keepalive._continue_reason(self.status())
        seen = []

        def runner(argv, **kwargs):
            seen.append(argv)
            self.advance()
            return self.done(argv)

        code, _ = self.drive("cursor", runner, max_minutes=2)
        self.assertEqual(code, keepalive.EXIT_CAP)
        self.assertEqual(seen[0][:4], ["cursor-agent", "-p", "--resume", "chat-42"])
        self.assertEqual(seen[0][-1], prompt)

    def test_there_is_no_ceiling_by_default(self) -> None:
        # Owner 2026-10-28: runs go on for a very long time; the old default stopped after 20 sessions.
        sessions = []

        def runner(argv, **kwargs):
            sessions.append(argv)
            if len(sessions) <= 20:
                self.advance()
            else:
                shiploop("pause", "--run-dir", str(self.run_dir), "--reason", "owner stop")
            return self.done(argv)

        code, lines = self.drive("claude", runner)
        self.assertEqual((code, len(sessions)), (keepalive.EXIT_NEEDS_USER, 21))
        self.assertIn("run is paused after 21 session", lines[-1])

    def test_max_minutes_cuts_the_last_session_to_the_time_left(self) -> None:
        timeouts = []

        def runner(argv, **kwargs):
            timeouts.append(kwargs["timeout"])
            self.advance()
            return self.done(argv)

        code, lines = self.drive("claude", runner, max_minutes=1, session_seconds=50, session_timeout=60)
        self.assertEqual((code, timeouts), (keepalive.EXIT_CAP, [60, 10]))
        self.assertIn("reached --max-minutes 1 after 2 session(s)", lines[-1])

    def test_the_session_count_flag_is_gone(self) -> None:
        import contextlib
        import io
        with contextlib.redirect_stderr(io.StringIO()) as err, self.assertRaises(SystemExit):
            keepalive.drive_main(["--host", "claude", "--run-dir", str(self.run_dir), "--max-sessions", "2"])
        self.assertIn("--max-sessions", err.getvalue())

    def test_a_second_driver_on_the_same_run_refuses(self) -> None:
        import fcntl
        logs = self.temp / "state" / "drive" / self.status()["run_id"]
        logs.mkdir(parents=True)
        fd = os.open(logs / "driver.lock", os.O_RDWR | os.O_CREAT)
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            code, lines = self.drive("claude", lambda argv, **kwargs: self.fail("must not start a session"))
        finally:
            os.close(fd)
        self.assertEqual(code, keepalive.EXIT_NEEDS_USER)
        self.assertIn("already running", lines[-1])

    def test_each_finished_session_frees_the_run_for_the_next(self) -> None:
        owners = []

        def runner(argv, **kwargs):
            session = f"driven-{len(owners)}"
            self.hook("observe", "claude", self.payload("claude", "observe", session))
            owners.append(keepalive._load_owner(str(self.run_dir)).get("owner"))
            self.advance()
            return self.done(argv)

        self.drive("claude", runner, max_minutes=2)
        self.assertEqual(owners, ["claude:driven-0", "claude:driven-1"])

    def test_session_logs_and_journal_are_kept_outside_the_run(self) -> None:
        self.drive("codex", lambda argv, **kwargs: self.done(argv), max_minutes=2)
        run_id = self.status()["run_id"]
        journal = self.temp / "state" / "drive" / run_id / "drive.log"
        self.assertEqual(len(journal.read_text().splitlines()), 2)
        self.assertFalse(any(path.name.startswith("session-") for path in self.run_dir.rglob("*")))


class ModelTelemetryAndRoutingTests(KeepaliveTestCase):
    def model_rows(self) -> list[dict]:
        lines = (self.run_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines()
        return [row for row in map(json.loads, lines) if row.get("kind") == "hook" and row.get("hook") == "model"]

    def test_hook_status_reports_stage_profile(self) -> None:
        self.assertEqual(self.status()["profile"], "planning")
        # Advance to implement (execution) via stage_spec check
        sys.path.insert(0, str(SCRIPTS))
        import shiploop_stage_spec as stage_spec
        self.assertEqual(stage_spec.stage_profile("implement"), "execution")

    def test_passive_model_telemetry_records_changes_across_hosts(self) -> None:
        # Antigravity: modelName includes effort suffix; repeated model does not duplicate rows.
        agy_obs = {**self.payload("antigravity", "observe", "agy-1"), "modelName": "gemini-4-neon-high"}
        self.hook("observe", "antigravity", agy_obs)
        self.hook("observe", "antigravity", {**agy_obs, "toolCall": {"name": "run_command", "args": {"CommandLine": "ls"}}})
        agy_stop = {**self.payload("antigravity", "stop", "agy-1"), "modelName": "gemini-4-carbon-medium"}
        self.hook("stop", "antigravity", agy_stop)

        # Codex: model on stdin + effort in rollout transcript tail.
        codex_rollout = self.temp / "rollout.jsonl"
        codex_rollout.write_text(json.dumps({"type": "turn_context", "payload": {"model": "gpt-6.2-sol", "effort": "medium"}}) + "\n")
        codex_obs = {**self.payload("codex", "observe", "cx-1"), "model": "gpt-6.2-sol", "transcript_path": str(codex_rollout)}
        self.hook("observe", "codex", codex_obs)

        # Claude: effort on stdin + model in transcript tail.
        claude_transcript = self.temp / "claude.jsonl"
        claude_transcript.write_text(json.dumps({"message": {"role": "assistant", "model": "claude-sonnet-5-5"}}) + "\n")
        claude_obs = {**self.payload("claude", "observe", "cl-1"), "effort": "high", "transcript_path": str(claude_transcript)}
        self.hook("observe", "claude", claude_obs)

        rows = self.model_rows()
        self.assertEqual([(r["host"], r["model"], r["effort"]) for r in rows], [
            ("antigravity", "gemini-4-neon-high", "high"),
            ("antigravity", "gemini-4-carbon-medium", "medium"),
            ("codex", "gpt-6.2-sol", "medium"),
            ("claude", "claude-sonnet-5-5", "high"),
        ])
        self.assertIn("model antigravity gemini-4-neon-high at intake (planning)", trace.event_line({**rows[0], "i": 1}))
        self.assertIn("model codex gpt-6.2-sol/medium at intake (planning)", trace.event_line({**rows[2], "i": 1}))

    def test_boundary_withholds_next_packet_and_allows_stop(self) -> None:
        cfg_path = self.temp / "routing.json"
        cfg_path.write_text(json.dumps({
            "planning": {"antigravity": "gemini-4-neon-high"},
            "execution": {"antigravity": "gemini-4-carbon-medium"},
        }))
        sys.path.insert(0, str(SCRIPTS))
        import shiploop_model_routing as routing
        exec_target = routing.resolve(routing.load_config(cfg_path), "implement", "antigravity")
        env = {
            **os.environ,
            "SHIPLOOP_DRIVE_ROUTING": str(cfg_path),
            "SHIPLOOP_DRIVE_HOST": "antigravity",
            "SHIPLOOP_DRIVE_TARGET": exec_target.target_key,
            "SHIPLOOP_DRIVE_LABEL": exec_target.label,
            "SHIPLOOP_DRIVE_RUN_ID": self.status()["run_id"],
        }
        # Current stage is intake (planning), while assigned session target is execution -> boundary!
        res = subprocess.run([sys.executable, str(SCRIPTS / "shiploop"), "next", "--run-dir", str(self.run_dir)],
                             capture_output=True, text=True, env=env, check=False)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Profile boundary reached", res.stdout)
        self.assertNotIn("Callback for this stage", res.stdout)
        self.hook("observe", "antigravity", self.payload("antigravity", "observe", "agy-b"))
        with mock.patch.dict(os.environ, env):
            decision = keepalive.stop("antigravity", self.payload("antigravity", "stop", "agy-b"))
        self.assertEqual(decision["decision"], "allow")
        self.assertIn("profile boundary reached", decision["why"])

    def test_routed_drive_warm_resumes_and_switches_models_and_hosts(self) -> None:
        # 1. With plan_reflect_and_improve=True, reflect-and-revise switches back to planning.
        routing_cfg = {
            "planning": {"antigravity": {"model": "gemini-4-neon-high"}},
            "execution": {"antigravity": {"model": "gemini-4-carbon-medium"}},
            "plan_reflect_and_improve": True,
        }
        calls = []
        statuses = [
            {"run_dir": str(self.run_dir), "run_id": self.status()["run_id"], "repo": str(self.repo),
             "status": "active", "stage": "plan", "revision": 1, "completion": "c1", "next": "n1"},
            {"run_dir": str(self.run_dir), "run_id": self.status()["run_id"], "repo": str(self.repo),
             "status": "active", "stage": "implement", "revision": 2, "completion": "c2", "next": "n2"},
            {"run_dir": str(self.run_dir), "run_id": self.status()["run_id"], "repo": str(self.repo),
             "status": "active", "stage": "reflect-and-revise", "revision": 3, "completion": "c3", "next": "n3"},
            {"run_dir": str(self.run_dir), "run_id": self.status()["run_id"], "repo": str(self.repo),
             "status": "done", "stage": None, "revision": 4, "completion": "", "next": "n4"},
        ]
        idx = [0]

        def fake_status(_run_dir):
            return dict(statuses[min(idx[0], len(statuses) - 1)])

        def runner(argv, **kwargs):
            calls.append((argv, kwargs.get("env", {})))
            if idx[0] == 0:
                self.hook("observe", "antigravity", self.payload("antigravity", "observe", "agy-warm-1"))
            idx[0] += 1
            return DriverTests.done(argv)

        with mock.patch.object(keepalive, "run_status", side_effect=fake_status):
            code = keepalive.drive("antigravity", str(self.run_dir), session_timeout=60, extra=["--dangerously-skip-permissions"],
                                   cwd=None, routing=routing_cfg, out=lambda _m: None, runner=runner, clock=lambda: 10.0)
        self.assertEqual(code, keepalive.EXIT_DONE)
        self.assertEqual(len(calls), 3)
        self.assertIn("gemini-4-neon-high", calls[0][0])
        self.assertNotIn("--resume", calls[0][0])
        self.assertIn("--resume", calls[1][0])
        self.assertIn("agy-warm-1", calls[1][0])
        self.assertIn("gemini-4-carbon-medium", calls[1][0])
        self.assertIn("--resume", calls[2][0])
        self.assertIn("gemini-4-neon-high", calls[2][0])

        # 2. Default (prelude-only) runs plan -> implement -> handoff without switching back at handoff.
        prelude_cfg = {
            "planning": {"antigravity": {"model": "gemini-4-neon-high"}},
            "execution": {"antigravity": {"model": "gemini-4-carbon-medium"}},
        }
        prelude_statuses = [
            {"run_dir": str(self.run_dir), "run_id": self.status()["run_id"], "repo": str(self.repo),
             "status": "active", "stage": "plan", "revision": 1, "completion": "c1", "next": "n1"},
            {"run_dir": str(self.run_dir), "run_id": self.status()["run_id"], "repo": str(self.repo),
             "status": "active", "stage": "implement", "revision": 2, "completion": "c2", "next": "n2"},
            {"run_dir": str(self.run_dir), "run_id": self.status()["run_id"], "repo": str(self.repo),
             "status": "done", "stage": None, "revision": 3, "completion": "", "next": "n3"},
        ]
        idx[0] = 0
        p_calls = []

        def p_runner(argv, **kwargs):
            p_calls.append(argv)
            idx[0] += 1
            return DriverTests.done(argv)

        with mock.patch.object(keepalive, "run_status", side_effect=lambda _d: dict(prelude_statuses[idx[0]])):
            code = keepalive.drive("antigravity", str(self.run_dir), session_timeout=60, extra=[], cwd=None,
                                   routing=prelude_cfg, out=lambda _m: None, runner=p_runner, clock=lambda: 10.0)
        self.assertEqual((code, len(p_calls)), (keepalive.EXIT_DONE, 2))
        self.assertIn("gemini-4-neon-high", p_calls[0])
        self.assertIn("gemini-4-carbon-medium", p_calls[1])

        # Cross-harness switch: antigravity planning -> codex execution.
        cross_cfg = {
            "planning": {"host": "antigravity", "model": "gemini-4-neon-high"},
            "execution": {"host": "codex", "model": "gpt-6.2-sol", "effort": "medium"},
            "plan_reflect_and_improve": True,
        }
        idx[0] = 0
        cross_calls = []

        def cross_runner(argv, **kwargs):
            cross_calls.append(argv)
            idx[0] += 1
            return DriverTests.done(argv)

        with mock.patch.object(keepalive, "run_status", side_effect=fake_status):
            code = keepalive.drive("antigravity", str(self.run_dir), session_timeout=60, extra=[],
                                   cwd=None, routing=cross_cfg, out=lambda _m: None, runner=cross_runner, clock=lambda: 10.0)
        self.assertEqual(code, keepalive.EXIT_DONE)
        self.assertEqual(cross_calls[0][0], "agy")
        self.assertEqual(cross_calls[1][:2], ["codex", "exec"])
        self.assertIn("gpt-6.2-sol", cross_calls[1])
        self.assertIn("model_reasoning_effort=medium", cross_calls[1])
        self.assertEqual(cross_calls[2][0], "agy")

    def test_hook_status_and_drive_handle_done_stage(self) -> None:
        import contextlib
        import importlib.machinery
        import importlib.util
        import io
        import shiploop_protocol as protocol

        loader = importlib.machinery.SourceFileLoader("shiploop_cli_core", str(SCRIPTS / "shiploop"))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        core = importlib.util.module_from_spec(spec)
        loader.exec_module(core)

        done_state = store.read_record(self.run_dir / "state.md")
        item_ids = [item["id"] for item in done_state["work_items"]]
        done_state["status"] = "done"
        done_state["stage"] = "done"
        done_state["action"]["stage"] = "done"
        done_state["work_index"] = len(item_ids)
        done_state["completed_work_items"] = item_ids
        done_state["inner_loops"] = {item_id: {"stage": "done", "action": None} for item_id in item_ids}
        done_state["revision"] += 1
        store.write_record(self.run_dir / "state.md", done_state)

        buf = io.StringIO()
        with mock.patch.object(nav, "validate", return_value=None), contextlib.redirect_stdout(buf):
            rc = protocol.hook_status(core, ["--run-dir", str(self.run_dir)])
        self.assertEqual(rc, 0)
        st = json.loads(buf.getvalue())
        self.assertEqual((st["status"], st["stage"], st["profile"]), ("done", "done", None))
        with mock.patch.object(keepalive, "run_status", return_value=st):
            code = keepalive.drive("codex", str(self.run_dir), session_timeout=60, extra=[], cwd=None,
                                   out=lambda _m: None,
                                   runner=lambda argv, **kwargs: self.fail("done run must not spawn session"),
                                   clock=lambda: 1.0)
        self.assertEqual(code, keepalive.EXIT_DONE)

    def test_observed_model_preserves_effort_when_later_payload_omits_it(self) -> None:
        rollout = self.temp / "codex-rollout.jsonl"
        rollout.write_text(json.dumps({"type": "turn_context", "payload": {"model": "gpt-6.2-sol", "effort": "medium"}}) + "\n",
                           encoding="utf-8")
        self.hook("observe", "codex", {**self.payload("codex", "observe", "codex-eff-1"),
                                        "model": "gpt-6.2-sol", "transcript_path": str(rollout)})
        # Later turn grows rollout past turn_context or omits transcript_path; same model keeps prior effort.
        rollout.write_text("", encoding="utf-8")
        self.hook("stop", "codex", {**self.payload("codex", "stop", "codex-eff-1"),
                                    "model": "gpt-6.2-sol", "transcript_path": str(rollout)})
        rows = self.model_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["model"], rows[0]["effort"]), ("gpt-6.2-sol", "medium"))

    def test_observed_model_reads_claude_effort_from_assistant_transcript_row(self) -> None:
        transcript = self.temp / "claude-transcript.jsonl"
        transcript.write_text(
            json.dumps({
                "type": "assistant",
                "effort": "high",
                "perTurnEffort": "high",
                "message": {"role": "assistant", "model": "claude-sonnet-5-5", "content": []},
            }) + "\n",
            encoding="utf-8",
        )
        self.hook("observe", "claude", {
            **self.payload("claude", "observe", "claude-eff-1"),
            "transcript_path": str(transcript),
        })
        transcript.write_text(
            json.dumps({
                "type": "assistant",
                "perTurnEffort": "low",
                "message": {"role": "assistant", "model": "claude-haiku-5-5", "content": []},
            }) + "\n",
            encoding="utf-8",
        )
        self.hook("observe", "claude", {
            **self.payload("claude", "observe", "claude-eff-1"),
            "transcript_path": str(transcript),
        })
        transcript.write_text(
            json.dumps({
                "type": "assistant",
                "message": {"role": "assistant", "model": "claude-opus-5-5", "content": []},
            }) + "\n",
            encoding="utf-8",
        )
        self.hook("observe", "claude", {
            **self.payload("claude", "observe", "claude-eff-1"),
            "transcript_path": str(transcript),
        })
        rows = self.model_rows()
        self.assertEqual(
            [(row["model"], row.get("effort")) for row in rows],
            [("claude-sonnet-5-5", "high"), ("claude-haiku-5-5", "low"), ("claude-opus-5-5", None)],
        )

    def test_drive_warm_resume_survives_session_end_binding_cleanup(self) -> None:
        run_id = self.status()["run_id"]
        for host, planning, execution in (
            ("claude", {"model": "sonnet", "effort": "high"}, {"model": "haiku", "effort": "low"}),
            ("codex", {"model": "gpt-6.2-astra", "effort": "high"}, {"model": "gpt-6.2-sol", "effort": "medium"}),
        ):
            routing_cfg = {"planning": {host: planning}, "execution": {host: execution}, "plan_reflect_and_improve": True}
            statuses = [
                {"run_dir": str(self.run_dir), "run_id": run_id, "repo": str(self.repo),
                 "status": "active", "stage": "plan", "revision": 1, "completion": "c1", "next": "n1"},
                {"run_dir": str(self.run_dir), "run_id": run_id, "repo": str(self.repo),
                 "status": "active", "stage": "implement", "revision": 2, "completion": "c2", "next": "n2"},
                {"run_dir": str(self.run_dir), "run_id": run_id, "repo": str(self.repo),
                 "status": "active", "stage": "reflect-and-revise", "revision": 3, "completion": "c3", "next": "n3"},
                {"run_dir": str(self.run_dir), "run_id": run_id, "repo": str(self.repo),
                 "status": "done", "stage": "done", "revision": 4, "completion": "", "next": "n4"},
            ]
            idx = [0]
            calls: list[list[str]] = []
            sid = f"{host}-warm-session-end-1"

            def fake_status(_run_dir):
                return dict(statuses[min(idx[0], len(statuses) - 1)])

            def runner(argv, **kwargs):
                calls.append(argv)
                self.hook("observe", host, self.payload(host, "observe", sid))
                # Simulate Claude/Codex SessionEnd firing on clean exit, unlinking the binding file.
                self.hook("session-end", host, {"session_id": sid, "reason": "other"})
                idx[0] += 1
                return DriverTests.done(argv)

            with mock.patch.object(keepalive, "run_status", side_effect=fake_status):
                code = keepalive.drive(host, str(self.run_dir), session_timeout=60, extra=[], cwd=None,
                                       routing=routing_cfg, out=lambda _m: None, runner=runner, clock=lambda: 10.0)
            self.assertEqual(code, keepalive.EXIT_DONE)
            self.assertEqual(len(calls), 3)
            self.assertNotIn("--resume", calls[0])
            if host == "codex":
                self.assertEqual(calls[1][:3], ["codex", "exec", "resume"])
                self.assertEqual(calls[2][:3], ["codex", "exec", "resume"])
            else:
                self.assertIn("--resume", calls[1])
                self.assertIn("--resume", calls[2])
            self.assertIn(sid, calls[1])
            self.assertIn(sid, calls[2])

    def test_drive_main_applies_built_in_defaults_unless_opted_out(self) -> None:
        import contextlib
        import io
        import shiploop_model_routing as model_routing

        for host in ("claude", "codex", "antigravity"):
            with self.subTest(host=host), mock.patch.object(keepalive, "drive", return_value=0) as m_drive:
                rc = keepalive.drive_main(["--host", host, "--run-dir", str(self.run_dir), "--", "--dangerously-skip-permissions"])
            self.assertEqual(rc, 0)
            self.assertEqual(m_drive.call_args.kwargs["routing"], model_routing.default_routing(host))

        for host in ("cursor", "opencode", "grok"):
            with self.subTest(unrouted_host=host), mock.patch.object(keepalive, "drive", return_value=0) as m_drive:
                rc = keepalive.drive_main(["--host", host, "--run-dir", str(self.run_dir)])
            self.assertEqual(rc, 0)
            self.assertIsNone(m_drive.call_args.kwargs["routing"])

        with mock.patch.object(keepalive, "drive", return_value=0) as m_drive:
            keepalive.drive_main(["--host", "claude", "--run-dir", str(self.run_dir), "--no-routing"])
            self.assertIsNone(m_drive.call_args.kwargs["routing"])

        for extra in (["-m", "gpt-6.2-sol"], ["--model", "haiku"]):
            with mock.patch.object(keepalive, "drive", return_value=0) as m_drive:
                keepalive.drive_main(["--host", "codex", "--run-dir", str(self.run_dir), "--", *extra])
                self.assertIsNone(m_drive.call_args.kwargs["routing"])

        with mock.patch.object(keepalive, "drive", return_value=0) as m_drive:
            keepalive.drive_main(["--host", "antigravity", "--run-dir", str(self.run_dir), "--routing", "default"])
            self.assertEqual(m_drive.call_args.kwargs["routing"], model_routing.load_config(model_routing.DEFAULT_ROUTING))

        for bad_args in (
            ["--host", "claude", "--run-dir", str(self.run_dir), "--no-routing", "--routing", "default"],
            ["--host", "claude", "--run-dir", str(self.run_dir), "--no-routing", "--planning-model", "sonnet"],
            ["--host", "claude", "--run-dir", str(self.run_dir), "--no-routing", "--plan-reflect-and-improve"],
            ["--host", "cursor", "--run-dir", str(self.run_dir), "--plan-reflect-and-improve"],
        ):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                keepalive.drive_main(bad_args)

        with mock.patch.object(keepalive, "drive", return_value=0) as m_drive:
            keepalive.drive_main(["--host", "codex", "--run-dir", str(self.run_dir), "--plan-reflect-and-improve"])
            self.assertEqual(
                m_drive.call_args.kwargs["routing"],
                {**model_routing.default_routing("codex"), "plan_reflect_and_improve": True},
            )


class ThreeHostSmokeMatrixTests(unittest.TestCase):
    """Hermetic 3-host integration matrix exercising real `drive` + `observe`/`stop`/`session-end` + `grade_run`."""

    _SPECS = {
        "claude": {
            "planning": ("claude-opus-5-5", "high", "claude-opus-5-5"),
            "execution": ("claude-sonnet-5-5", "high", "claude-sonnet-5-5"),
        },
        "codex": {
            "planning": ("gpt-6.2-astra", "high", "gpt-6.2-astra"),
            "execution": ("gpt-6.2-sol", "xhigh", "gpt-6.2-sol"),
        },
        "antigravity": {
            "planning": ("gemini-4-neon-high", "high", "gemini-4-neon-high"),
            "execution": ("gemini-4-carbon-medium", "medium", "gemini-4-carbon-medium"),
        },
    }

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory(prefix="shiploop-ka-3host-")
        self.addCleanup(tmp.cleanup)
        self.temp = Path(tmp.name).resolve()
        probe_path = ROOT / "test" / "shiploop_e2e" / "probes" / "model_routing_smoke.py"
        spec = importlib.util.spec_from_file_location("shiploop_model_routing_smoke_probe", probe_path)
        assert spec is not None and spec.loader is not None
        probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(probe)
        self.probe = probe

    def _init_run(self, name: str) -> tuple[Path, Path, Path]:
        base = self.temp / name
        repo = base / "repo"
        run_dir = base / "run"
        ka_home = base / "keepalive"
        repo.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
        env = {
            **os.environ,
            "SHIPLOOP_KEEPALIVE_HOME": str(ka_home),
            "SHIPLOOP_PROGRESS": "off",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        }
        subprocess.run(
            [sys.executable, str(SCRIPTS / "shiploop"), "init",
             "--run-dir", str(run_dir), "--repo", str(repo), "--prompt", "Add greet helper."],
            env=env, capture_output=True, text=True, check=True,
        )
        return run_dir, ka_home, base

    @staticmethod
    def _write_history(state_path: Path, stages: list[str], *, final_status: str = "done") -> None:
        data = store.read_record(state_path)
        data["status"] = final_status
        data["history"] = [
            {"stage": s, "outcome": "done", "summary": "ok", "workitem": None, "action": f"nav-{i}"}
            for i, s in enumerate(stages)
        ]
        store.write_record(state_path, data)

    def _make_payload(self, host: str, event: str, session: str, marker: str, run_dir: Path,
                      *, effort: str | None, obs_model: str, transcript: Path) -> dict:
        raw = (FIXTURES / f"{host}-{event}.json").read_text(encoding="utf-8")
        raw = raw.replace("__SESSION__", session).replace("__MARKER__", marker).replace("__RUN_DIR__", str(run_dir))
        payload = json.loads(raw)
        if host == "antigravity":
            payload["modelName"] = obs_model
        elif host == "codex":
            payload["model"] = obs_model
            transcript.write_text(
                json.dumps({"type": "turn_context", "payload": {"model": obs_model, "effort": effort}}) + "\n",
                encoding="utf-8",
            )
            payload["transcript_path"] = str(transcript)
        elif host == "claude":
            transcript.write_text(
                json.dumps({
                    "type": "assistant",
                    "effort": effort,
                    "perTurnEffort": effort,
                    "message": {"role": "assistant", "model": obs_model, "content": []},
                }) + "\n",
                encoding="utf-8",
            )
            payload["transcript_path"] = str(transcript)
        return payload

    def test_routed_matrix_prelude_only_and_optin_plan_reflect_and_improve(self) -> None:
        import shiploop_model_routing as routing

        # 1. Default prelude-only (prepare -> step-plan): exactly 1 boundary switch on Claude/Codex/explicit-agy.
        for host, spec in self._SPECS.items():
            with self.subTest(prelude_only=host):
                run_dir, ka_home, base = self._init_run(f"{host}-prelude")
                repo = base / "repo"
                env_patch = {
                    "SHIPLOOP_KEEPALIVE_HOME": str(ka_home),
                    "SHIPLOOP_PROGRESS": "off",
                    "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_CONFIG_GLOBAL": os.devnull,
                }
                with mock.patch.dict(os.environ, env_patch), mock.patch.object(keepalive, "host_process", return_value=None):
                    st0 = keepalive.run_status(str(run_dir))
                    run_id = st0["run_id"]
                    marker = f"SHIPLOOP-RUN run={run_id} rev=0 dir={run_dir}"
                    transcript = base / "transcript.jsonl"
                    statuses = [
                        {**st0, "stage": "prepare", "profile": "planning", "revision": 1},
                        {**st0, "stage": "step-plan", "profile": "execution", "revision": 2},
                        {**st0, "stage": "done", "profile": None, "status": "done", "revision": 3, "completion": ""},
                    ]
                    idx = [0]
                    invocations: list[tuple[list[str], dict[str, str]]] = []
                    sid = f"{host}-prelude-thread"

                    def runner(argv, **kwargs):
                        cur = idx[0]
                        invocations.append((argv, kwargs.get("env", {})))
                        prof = "planning" if cur == 0 else "execution"
                        _m_in, effort_in, obs_m = spec[prof]
                        obs_payload = self._make_payload(
                            host, "observe", sid, marker, run_dir,
                            effort=effort_in, obs_model=obs_m, transcript=transcript,
                        )
                        keepalive.run_hook("observe", host, json.dumps(obs_payload))
                        if cur == 0:
                            idx[0] += 1
                            nxt = statuses[idx[0]]
                            stop_payload = self._make_payload(
                                host, "stop", sid, marker, run_dir,
                                effort=effort_in, obs_model=obs_m, transcript=transcript,
                            )
                            with mock.patch.dict(os.environ, kwargs.get("env", {})), \
                                    mock.patch.object(keepalive, "run_status", return_value=nxt):
                                raw_out = keepalive.run_hook("stop", host, json.dumps(stop_payload))
                            if raw_out:
                                self.assertEqual(json.loads(raw_out)["decision"], "allow")
                            if host in ("claude", "codex"):
                                keepalive.run_hook("session-end", host, json.dumps({"session_id": sid, "reason": "other"}))
                        else:
                            idx[0] += 1
                        return subprocess.CompletedProcess(argv, 0, "ok", "")

                    routing_cfg = {
                        "planning": {host: {"model": spec["planning"][0],
                                            **({} if spec["planning"][0].endswith(routing.EFFORT_SUFFIXES) else {"effort": spec["planning"][1]})}},
                        "execution": {host: {"model": spec["execution"][0],
                                             **({} if spec["execution"][0].endswith(routing.EFFORT_SUFFIXES) else {"effort": spec["execution"][1]})}},
                    }
                    with mock.patch.object(keepalive, "run_status", side_effect=lambda _d: dict(statuses[idx[0]])):
                        code = keepalive.drive(host, str(run_dir), session_timeout=60, extra=[], cwd=str(repo),
                                               routing=routing_cfg, out=lambda _m: None, runner=runner, clock=lambda: 5.0)
                    self.assertEqual(code, keepalive.EXIT_DONE)
                    self.assertEqual(len(invocations), 2)
                    self.assertNotIn("--resume", invocations[0][0])
                    if host == "codex":
                        self.assertEqual(invocations[1][0][:3], ["codex", "exec", "resume"])
                    else:
                        self.assertIn("--resume", invocations[1][0])
                    self.assertIn(sid, invocations[1][0])

                    self._write_history(run_dir / "state.md", ["prepare", "step-plan"])
                    verdict = self.probe.grade_run(
                        host,
                        run_dir,
                        ka_home / "drive" / run_id / "drive.log",
                        mode="routed",
                        expected_planning=(spec["planning"][0], spec["planning"][1]),
                        expected_execution=(spec["execution"][0], spec["execution"][1]),
                    )
                    self.assertTrue(verdict["pass"], verdict)
                    self.assertEqual(len(verdict["boundary_stops"]), 1, verdict)

        # 2. Opt-in plan_reflect_and_improve=True (system-test-author -> improve -> system-test, 2 boundary stops).
        for host in ("claude", "codex"):
            with self.subTest(optin=host):
                spec = self._SPECS[host]
                run_dir, ka_home, base = self._init_run(f"{host}-optin")
                repo = base / "repo"
                env_patch = {
                    "SHIPLOOP_KEEPALIVE_HOME": str(ka_home),
                    "SHIPLOOP_PROGRESS": "off",
                    "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_CONFIG_GLOBAL": os.devnull,
                }
                with mock.patch.dict(os.environ, env_patch), mock.patch.object(keepalive, "host_process", return_value=None):
                    st0 = keepalive.run_status(str(run_dir))
                    run_id = st0["run_id"]
                    marker = f"SHIPLOOP-RUN run={run_id} rev=0 dir={run_dir}"
                    transcript = base / "transcript.jsonl"
                    statuses = [
                        {**st0, "stage": "system-test-author", "profile": "execution", "revision": 1},
                        {**st0, "stage": "improve", "reviewed_stage": "system-test-author", "profile": "execution", "revision": 2},
                        {**st0, "stage": "system-test", "profile": "execution", "revision": 3},
                        {**st0, "stage": "done", "profile": None, "status": "done", "revision": 4, "completion": ""},
                    ]
                    idx = [0]
                    invocations: list[tuple[list[str], dict[str, str]]] = []
                    sid = f"{host}-optin-thread"

                    def runner(argv, **kwargs):
                        cur = idx[0]
                        invocations.append((argv, kwargs.get("env", {})))
                        prof = "planning" if cur == 1 else "execution"
                        _m_in, effort_in, obs_m = spec[prof]
                        obs_payload = self._make_payload(
                            host, "observe", sid, marker, run_dir,
                            effort=effort_in, obs_model=obs_m, transcript=transcript,
                        )
                        with mock.patch.dict(os.environ, kwargs.get("env", {})):
                            keepalive.run_hook("observe", host, json.dumps(obs_payload))
                        if cur in (0, 1):
                            idx[0] += 1
                            nxt = statuses[idx[0]]
                            stop_payload = self._make_payload(
                                host, "stop", sid, marker, run_dir,
                                effort=effort_in, obs_model=obs_m, transcript=transcript,
                            )
                            with mock.patch.dict(os.environ, kwargs.get("env", {})), \
                                    mock.patch.object(keepalive, "run_status", return_value=nxt):
                                raw_out = keepalive.run_hook("stop", host, json.dumps(stop_payload))
                            if raw_out:
                                self.assertEqual(json.loads(raw_out)["decision"], "allow")
                            keepalive.run_hook("session-end", host, json.dumps({"session_id": sid, "reason": "other"}))
                        else:
                            idx[0] += 1
                        return subprocess.CompletedProcess(argv, 0, "ok", "")

                    routing_cfg = {**routing.default_routing(host), "plan_reflect_and_improve": True}
                    with mock.patch.object(keepalive, "run_status", side_effect=lambda _d: dict(statuses[idx[0]])):
                        code = keepalive.drive(host, str(run_dir), session_timeout=60, extra=[], cwd=str(repo),
                                               routing=routing_cfg, out=lambda _m: None, runner=runner, clock=lambda: 5.0)
                    self.assertEqual(code, keepalive.EXIT_DONE)
                    self.assertEqual(len(invocations), 3)
                    self._write_history(run_dir / "state.md", ["system-test-author", "system-test"])
                    verdict = self.probe.grade_run(
                        host,
                        run_dir,
                        ka_home / "drive" / run_id / "drive.log",
                        mode="routed",
                        expected_planning=(spec["planning"][0], spec["planning"][1]),
                        expected_execution=(spec["execution"][0], spec["execution"][1]),
                        plan_reflect_and_improve=True,
                    )
                    self.assertTrue(verdict["pass"], verdict)
                    self.assertEqual(len(verdict["boundary_stops"]), 2, verdict)

    def test_unrouted_codex_matrix_control(self) -> None:
        run_dir, ka_home, base = self._init_run("codex-unrouted")
        with mock.patch.dict(os.environ, {"SHIPLOOP_KEEPALIVE_HOME": str(ka_home), "SHIPLOOP_PROGRESS": "off"}), \
                mock.patch.object(keepalive, "host_process", return_value=None):
            st0 = keepalive.run_status(str(run_dir))
            run_id = st0["run_id"]
            marker = f"SHIPLOOP-RUN run={run_id} rev=0 dir={run_dir}"
            transcript = base / "rollout.jsonl"
            payload = self._make_payload(
                "codex", "observe", "cx-unrouted", marker, run_dir,
                effort="medium", obs_model="gpt-6.2-sol", transcript=transcript,
            )
            statuses = [st0, {**st0, "stage": "done", "profile": None, "status": "done", "revision": 1}]
            idx = [0]

            def runner(argv, **kwargs):
                keepalive.run_hook("observe", "codex", json.dumps(payload))
                idx[0] = 1
                return subprocess.CompletedProcess(argv, 0, "ok", "")

            with mock.patch.object(keepalive, "run_status", side_effect=lambda _d: dict(statuses[idx[0]])):
                code = keepalive.drive("codex", str(run_dir), session_timeout=60, extra=["-m", "gpt-6.2-sol"],
                                       cwd=str(base / "repo"), routing=None, out=lambda _m: None, runner=runner,
                                       clock=lambda: 5.0)
            self.assertEqual(code, keepalive.EXIT_DONE)
            self._write_history(run_dir / "state.md", ["prepare", "step-plan"])
            ok = self.probe.grade_run(
                "codex", run_dir, ka_home / "drive" / run_id / "drive.log",
                mode="unrouted", expected_planning=("gpt-6.2-sol", "medium"), expected_execution=("gpt-6.2-sol", "medium"),
            )
            self.assertTrue(ok["pass"], ok)

    def test_default_antigravity_orchestrator_runs_single_session_without_boundary_stops(self) -> None:
        import shiploop_model_routing as routing

        run_dir, ka_home, base = self._init_run("agy-orchestrator")
        repo = base / "repo"
        env_patch = {
            "SHIPLOOP_KEEPALIVE_HOME": str(ka_home),
            "SHIPLOOP_PROGRESS": "off",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        }
        with mock.patch.dict(os.environ, env_patch), mock.patch.object(keepalive, "host_process", return_value=None):
            st0 = keepalive.run_status(str(run_dir))
            run_id = st0["run_id"]
            marker = f"SHIPLOOP-RUN run={run_id} rev=0 dir={run_dir}"
            sid = "agy-orch-thread"
            invocations: list[list[str]] = []
            statuses = [
                {**st0, "stage": "system-test-author", "profile": "planning", "revision": 1},
                {**st0, "stage": "done", "profile": None, "status": "done", "revision": 2, "completion": ""},
            ]
            idx = [0]

            def runner(argv, **kwargs):
                invocations.append(argv)
                with mock.patch.dict(os.environ, kwargs.get("env", {})):
                    for obs_m in ("gemini-4-neon-high", "gemini-4-carbon-medium"):
                        keepalive.run_hook("observe", "antigravity", json.dumps(self._make_payload(
                            "antigravity", "observe", sid, marker, run_dir,
                            effort=None, obs_model=obs_m, transcript=base / "t.jsonl",
                        )))
                    raw_out = keepalive.run_hook("stop", "antigravity", json.dumps(self._make_payload(
                        "antigravity", "stop", sid, marker, run_dir,
                        effort=None, obs_model="gemini-4-neon-high", transcript=base / "t.jsonl",
                    )))
                # Even on execution boundary check inside same Orchestrator config, active_boundary is None; once done -> allow.
                idx[0] = 1
                if raw_out:
                    self.assertEqual(json.loads(raw_out)["decision"], "allow")
                return subprocess.CompletedProcess(argv, 0, "ok", "")

            # Inside session: simulate Neon -> Carbon without boundary stop, then pause/done.
            with mock.patch.object(keepalive, "run_status", side_effect=lambda _d: dict(statuses[idx[0]])):
                # Force stop to see done when idx increments after stop? Patch stop's status cleanly:
                pass
            idx[0] = 0

            def orch_runner(argv, **kwargs):
                invocations.append(argv)
                with mock.patch.dict(os.environ, kwargs.get("env", {})):
                    keepalive.run_hook("observe", "antigravity", json.dumps(self._make_payload(
                        "antigravity", "observe", sid, marker, run_dir,
                        effort=None, obs_model="gemini-4-neon-high", transcript=base / "t.jsonl",
                    )))
                    with mock.patch.object(keepalive, "run_status", return_value={**st0, "stage": "system-test", "profile": "execution", "revision": 2}):
                        exec_stop = json.loads(keepalive.run_hook("stop", "antigravity", json.dumps(self._make_payload(
                            "antigravity", "stop", sid, marker, run_dir,
                            effort=None, obs_model="gemini-4-carbon-medium", transcript=base / "t.jsonl",
                        ))))
                        # Orchestrator has identical planning & execution targets -> stop returns continue, not allow!
                        self.assertEqual(exec_stop["decision"], "continue")
                idx[0] = 1
                return subprocess.CompletedProcess(argv, 0, "ok", "")

            invocations.clear()
            with mock.patch.object(keepalive, "run_status", side_effect=lambda _d: dict(statuses[idx[0]])):
                code = keepalive.drive(
                    "antigravity", str(run_dir), session_timeout=60, extra=[], cwd=str(repo),
                    routing=routing.default_routing("antigravity"), out=lambda _m: None, runner=orch_runner, clock=lambda: 5.0,
                )
            self.assertEqual(code, keepalive.EXIT_DONE)
            self.assertEqual(len(invocations), 1)
            self.assertIn("gemini-pro-orchestrator-neon", invocations[0])
            self._write_history(run_dir / "state.md", ["prepare", "step-plan"])
            verdict = self.probe.grade_run(
                "antigravity", run_dir, ka_home / "drive" / run_id / "drive.log",
                mode="routed",
                expected_planning=("gemini-pro-orchestrator-neon", None),
                expected_execution=("gemini-pro-orchestrator-neon", None),
            )
            self.assertTrue(verdict["pass"], verdict)
            self.assertTrue(verdict["checks"]["single_session_ok"])
            self.assertEqual(len(verdict["boundary_stops"]), 0)

    def test_active_improve_sequence_stage_and_boundary_in_real_state(self) -> None:
        import shiploop_model_routing as routing

        routing_cfg = routing.default_routing("codex")
        exec_target = routing.resolve(routing_cfg, "step-plan", "codex")
        self.assertIsNotNone(exec_target)
        materials_root = self.temp / "active-improve-materials"
        product_dir, home_fix_dir = self.probe._write_smoke_materials(materials_root)

        def _make_run(reviewed: str) -> Path:
            if reviewed == "spec":
                rdir, _ka, _base = self._init_run("active-improve-spec")
                return rdir
            work = self.temp / "active-improve-outer-work"
            runs_out = self.temp / "active-improve-outer-out"
            work.mkdir(parents=True, exist_ok=True)
            runs_out.mkdir(parents=True, exist_ok=True)
            ka_home = self.temp / "active-improve-outer-ka"
            gitconfig = self.temp / "active-improve-gitconfig"
            self.probe._write_gitconfig(gitconfig)
            with mock.patch.dict(os.environ, {
                "GIT_CONFIG_GLOBAL": str(gitconfig),
                "GIT_CONFIG_NOSYSTEM": "1",
                "SHIPLOOP_KEEPALIVE_HOME": str(ka_home),
                "SHIPLOOP_PROGRESS": "off",
            }):
                seeded = self.probe.e2e_run.seed_run(
                    SCRIPTS / "shiploop", work, runs_out, self.probe.SMOKE_PROMPT, reviewed,
                    work_item={"id": "W1", "title": "Add greet helper"},
                    delegation="inline",
                    checks=["python3 -m unittest -v"],
                    product=product_dir,
                    home_fixture=home_fix_dir,
                    exclude=["README.md"],
                    planning_review="stage",
                    release_slice_mode=True,
                )
            return Path(seeded["run_dir"]).resolve()

        for reviewed, expected_default_profile, expect_optin_boundary in (
            ("spec", "planning", True),
            ("system-test-author", "execution", True),
        ):
            with self.subTest(reviewed=reviewed):
                run_dir = _make_run(reviewed)
                state_path = run_dir / "state.md"
                st = store.read_record(state_path)
                run_id = st["run_id"]
                st["planning_review"] = "stage"
                st["stage"] = reviewed
                st["action"] = nav._new_action(reviewed)
                reviewed_aid = st["action"]["id"]
                seed = nav._canonical_result(
                    {"outcome": "done", "summary": "ready for improve", "headline": "ready"},
                    stage=reviewed,
                    delivery_contract="delivery_contract_version" in st,
                )
                st["active_improve"] = {
                    "action_id": reviewed_aid,
                    "stage": reviewed,
                    "binding_id": f"{run_id}/{reviewed_aid}",
                    "workspace": st["repo"],
                    "seed_result": seed,
                    "skill": None,
                    "improve_action": nav._new_action("improve")["id"],
                }
                st["revision"] = int(st.get("revision", 0)) + 1
                store.write_record(state_path, st, "active improve regression")

                st_res = shiploop("hook-status", "--run-dir", str(run_dir))
                self.assertEqual(st_res.returncode, 0, st_res.stdout + st_res.stderr)
                status = json.loads(st_res.stdout)
                self.assertEqual(status["stage"], "improve")
                self.assertEqual(status["reviewed_stage"], reviewed)
                self.assertEqual(status["profile"], expected_default_profile)

                default_routing_path = self.temp / f"{reviewed}-default-routing.json"
                default_routing_path.write_text(json.dumps(routing_cfg), encoding="utf-8")
                env_default = {
                    "SHIPLOOP_DRIVE_ROUTING": str(default_routing_path),
                    "SHIPLOOP_DRIVE_HOST": "codex",
                    "SHIPLOOP_DRIVE_TARGET": exec_target.target_key,
                    "SHIPLOOP_DRIVE_LABEL": exec_target.label,
                    "SHIPLOOP_DRIVE_RUN_ID": run_id,
                }
                with mock.patch.dict(os.environ, env_default):
                    nxt_default = shiploop("next", "--run-dir", str(run_dir))
                self.assertEqual(nxt_default.returncode, 0, nxt_default.stderr)
                if reviewed == "spec":
                    self.assertIn("Profile boundary reached:", nxt_default.stdout)
                    self.assertIn("next stage `improve` (planning)", nxt_default.stdout)
                else:
                    self.assertNotIn("Profile boundary reached:", nxt_default.stdout)

                optin_routing_path = self.temp / f"{reviewed}-optin-routing.json"
                optin_routing_path.write_text(
                    json.dumps({**routing_cfg, "plan_reflect_and_improve": True}),
                    encoding="utf-8",
                )
                env_optin = {**env_default, "SHIPLOOP_DRIVE_ROUTING": str(optin_routing_path)}
                with mock.patch.dict(os.environ, env_optin):
                    nxt_optin = shiploop("next", "--run-dir", str(run_dir))
                self.assertEqual(nxt_optin.returncode, 0, nxt_optin.stderr)
                if expect_optin_boundary:
                    self.assertIn("Profile boundary reached:", nxt_optin.stdout)
                    self.assertIn("next stage `improve` (planning)", nxt_optin.stdout)


if __name__ == "__main__":
    unittest.main()
