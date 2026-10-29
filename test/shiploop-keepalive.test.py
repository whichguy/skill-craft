#!/usr/bin/env python3
"""ShipLoop keepalive: hook-status, the packet marker, host hooks, install and the driver.

Hook payloads come from recorded host runs (test/fixtures/shiploop-keepalive).
Runs are real ShipLoop runs in temporary directories; no host CLI is launched.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
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
sys.path.insert(0, str(SCRIPTS))

import shiploop_keepalive as keepalive  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_store as store  # noqa: E402
from shiploop_packet_view import assert_top_block, head_packet_path  # noqa: E402

RECORDED_HOSTS = ("claude", "codex", "cursor", "grok")


def shiploop(*argv: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / "shiploop"), *argv],
                          capture_output=True, text=True, check=False)


def _packet_path_from_stdout(stdout: str) -> Path | None:
    """The ``Full packet: <path>`` locator an active-state head prints, if any."""
    return head_packet_path(stdout)


def _packet_file_text(stdout: str) -> str:
    """The complete packet text: the referenced file for an active-state head,
    or the stdout itself for a paused/blocked/halted/done print, which already
    carries the full text and prints no ``Full packet:`` line.
    """
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
        # No progress observer: `init` would start one detached, and it writes into the run folder every 2 s, so a fast
        # test's cleanup raced it ("Directory not empty", 4 of 7 direct runs on 2026-10-28; run_suites.py sets it too).
        env = {"SHIPLOOP_KEEPALIVE_HOME": str(self.temp / "state"), "HOME": str(self.temp / "home"),
               "XDG_CONFIG_HOME": str(self.temp / "home" / ".config"), "SHIPLOOP_PROGRESS": "off"}
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
        text = text.replace("__SESSION__", session).replace("__MARKER__", self.marker_line())
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
        # The whole answer: the owed-report fields of 1.18.0 (loop, callback, delegation) are gone
        # (docs/shiploop-trims-plan-2026-10-28.md, T1).
        self.assertEqual(set(status), {"run_dir", "run_id", "repo", "status", "status_reason", "awaiting", "stage",
                                       "action", "revision", "progress", "next"})
        self.assertEqual((self.run_dir / "state.md").read_bytes(), before)

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
        # Round 2: a packet at most PRINT_LIMIT prints whole; the "Full packet:" pointer is only for a larger one.
        self.assertIsNone(_packet_path_from_stdout(again), again)
        self.assertLessEqual(len(again), nav.PRINT_LIMIT)
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
                self.assertIsNone(self.hook("observe", host, self.payload(host, "observe", session)))
                self.assertEqual(keepalive.load_binding(host, session)["run_dir"], str(self.run_dir))
                reply = self.hook("stop", host, self.payload(host, "stop", session))
                if host == "cursor":
                    self.assertIn("next --run-dir", reply["followup_message"])
                else:
                    self.assertEqual(reply["decision"], "block")
                    self.assertIn("next --run-dir", reply["reason"])

    def test_no_progress_since_the_last_refusal_lets_the_turn_end(self) -> None:
        self.hook("observe", "claude", self.payload("claude", "observe"))
        self.assertEqual(self.hook("stop", "claude", self.payload("claude", "stop"))["decision"], "block")
        with mock.patch.object(keepalive, "DUPLICATE_WINDOW_SECONDS", 0):
            reply = self.hook("stop", "claude", self.payload("claude", "stop"))
            self.assertIn("no progress", reply["systemMessage"])
            self.advance()
            self.assertEqual(self.hook("stop", "claude", self.payload("claude", "stop"))["decision"], "block")

    def test_running_next_between_two_stops_is_not_progress(self) -> None:
        # The refusal says to run `next`; doing only that re-binds the run, which must not reset the stop's memory
        # (docs/shiploop-owed-outcome-evidence/rebind_repro.out showed it did: the turn was never released).
        self.hook("observe", "claude", self.payload("claude", "observe"))
        with mock.patch.object(keepalive, "DUPLICATE_WINDOW_SECONDS", 0):
            self.assertEqual(self.hook("stop", "claude", self.payload("claude", "stop"))["decision"], "block")
            reread = self.payload("claude", "observe")
            reread["tool_input"]["command"] = f"python3 {SCRIPTS / 'shiploop'} next --run-dir {self.run_dir}"
            self.hook("observe", "claude", reread)
            self.assertIn("last_block_progress", keepalive.load_binding("claude", "session-1"))
            reply = self.hook("stop", "claude", self.payload("claude", "stop"))
        self.assertIn("no progress", reply["systemMessage"])

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
        self.assertIsNone(self.hook("stop", "grok", self.payload("grok", "stop")))
        self.hook("observe", "grok", self.payload("grok", "observe"))
        ending = {**self.payload("grok", "stop"), "reason": "channel_closed"}
        self.assertIsNone(self.hook("stop", "grok", ending))

    def test_another_hosts_payload_is_left_to_that_host(self) -> None:
        # Grok also runs ~/.cursor/hooks.json; its events must not bind as Cursor.
        self.assertIsNone(self.hook("observe", "cursor", self.payload("grok", "observe")))
        self.assertEqual(list((self.temp / "state").glob("bindings/*")), [])

    def test_a_shiploop_command_binds_even_when_its_output_was_filtered(self) -> None:
        payload = {"hookEventName": "PostToolUse", "sessionId": "filtered-1",
                   "toolInput": {"command": f"python3 shiploop next --run-dir={self.run_dir} | tail -5"},
                   "toolResult": "=== ShipLoop status === (filtered, no marker)"}
        self.hook("observe", "grok", payload)
        binding = keepalive.load_binding("grok", "filtered-1")
        self.assertIsNotNone(binding)
        self.assertEqual(binding["run_id"], self.status()["run_id"])
        for query in ("hook-status", "status", "report"):
            payload = {"hookEventName": "PostToolUse", "sessionId": f"reader-{query}",
                       "toolInput": {"command": f"python3 shiploop {query} --run-dir {self.run_dir}"}}
            self.hook("observe", "grok", payload)
            self.assertIsNone(keepalive.load_binding("grok", f"reader-{query}"), query)

    def test_the_improve_stage_commands_bind_and_the_retired_improve_complete_does_not(self) -> None:
        """The Improve stage is driven by `complete` (naming its id), improve-bind, a restart through improve-start and improve-reconcile;
        `improve-complete` is gone, so a command that names it is no driving command."""
        for verb, binds in (("complete --action=nav-i", True), ("improve-bind --action=nav-i --skill-card=/x/SKILL.md", True),
                            ("improve-start --action=nav-i --restart-stopped", True),
                            ("improve-reconcile --action=nav-i --result=/x/r.md", True), ("improve-complete --action=nav-i", False)):
            session = "improve-" + verb.split()[0]
            payload = {"hookEventName": "PostToolUse", "sessionId": session,
                       "toolInput": {"command": f"python3 shiploop {verb} --run-dir={self.run_dir}"},
                       "toolResult": "=== ShipLoop status === (filtered, no marker)"}
            self.hook("observe", "grok", payload)
            self.assertEqual(keepalive.load_binding("grok", session) is not None, binds, verb)

    def test_marker_copied_from_elsewhere_does_not_bind(self) -> None:
        payload = self.payload("claude", "observe")
        payload["tool_response"]["stdout"] = f"SHIPLOOP-RUN run=nav-0000 rev=0 dir={self.run_dir}"
        self.hook("observe", "claude", payload)
        self.assertIsNone(keepalive.load_binding("claude", "session-1"))

    def test_live_marker_printed_by_a_reading_command_does_not_bind(self) -> None:
        """A session that only reads a packet file or log must not be kept alive for the run."""
        for host, command in (("claude", f"cat {self.run_dir}/packets/next.md"),
                              ("grok", f"tail -50 {self.run_dir}/../events.jsonl"),
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

    def grok_stop(self, active: bool, **extra) -> dict:
        payload = {**self.payload("grok", "stop", "turn-1"), "stopHookActive": active, **extra}
        with mock.patch.object(keepalive, "DUPLICATE_WINDOW_SECONDS", 0):
            return keepalive.stop("grok", payload)

    def bind_grok(self) -> None:
        self.hook("observe", "grok", self.payload("grok", "observe", "turn-1"))

    def test_a_refused_callback_counts_as_progress(self) -> None:
        self.bind_grok()
        self.assertEqual(self.grok_stop(False)["decision"], "continue")
        refused = shiploop("complete", "--run-dir", str(self.run_dir), "--action", "nav-unknown",
                           "--result", str(self.run_dir / "inbox" / "nav-unknown.md"))
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("do not end the turn over a refused callback", refused.stderr)
        self.assertEqual(self.grok_stop(True)["decision"], "continue")
        self.assertEqual(self.grok_stop(True)["decision"], "allow")

    def test_refusals_without_an_accepted_result_keep_counting_as_progress_with_no_release(self) -> None:
        # Owner 2026-10-24: no run caps.  The 22-continuation release is gone: 23 and more refused callbacks with no
        # accepted result still continue, and the named exit (an unchanged progress counter) still allows the stop.
        self.assertFalse(hasattr(keepalive, "STUCK_CONTINUATIONS"))
        self.hook("observe", "claude", self.payload("claude", "observe"))
        stop = lambda: keepalive.stop("claude", self.payload("claude", "stop"))  # noqa: E731
        with mock.patch.object(keepalive, "DUPLICATE_WINDOW_SECONDS", 0):
            for attempt in range(23 + 5):
                (self.run_dir / "callback-attempts").write_text(str(attempt + 1))
                decision = stop()
                self.assertEqual(decision["decision"], "continue", attempt)
            stalled = stop()  # no new refused callback: no progress, so the turn may end
            self.assertEqual((stalled["decision"], stalled["why"]), ("allow", "no progress"))

    def test_a_running_background_task_is_a_wait_not_a_stop(self) -> None:
        self.bind_grok()
        self.grok_stop(False)
        decision = self.grok_stop(True, backgroundTasks=[{"id": "deploy"}])
        self.assertEqual(decision["decision"], "continue")
        self.assertIn("background task is still running", decision["reason"])

    def test_grok_continuations_are_counted_per_turn_and_warned_near_the_cap(self) -> None:
        self.bind_grok()
        reasons = []
        for index in range(7):
            (self.run_dir / "callback-attempts").write_text(str(index + 1))
            decision = self.grok_stop(index > 0)
            self.assertEqual(decision["decision"], "continue")
            reasons.append(decision["reason"])
        self.assertNotIn("of grok's 8", reasons[4])
        self.assertIn("continuation 6 of grok's 8", reasons[5])
        (self.run_dir / "callback-attempts").write_text("99")
        fresh = self.grok_stop(False)
        self.assertIn("continuation 1/8", fresh["why"])

    def test_a_second_session_is_told_who_owns_the_run(self) -> None:
        self.bind_grok()
        self.grok_stop(False)
        self.hook("observe", "grok", self.payload("grok", "observe", "turn-2"))
        with mock.patch.object(keepalive, "DUPLICATE_WINDOW_SECONDS", 0):
            decision = keepalive.stop("grok", self.payload("grok", "stop", "turn-2"))
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
        return {"GROK_AGENT": "1", "GROK_SESSION_ID": session}

    def test_the_second_unbound_packet_warns_once(self) -> None:
        run = str(self.run_dir)
        self.assertIsNone(keepalive.health_notice(run, self.env("h1")))
        notice = keepalive.health_notice(run, self.env("h1"))
        self.assertIn("keepalive is not active in this grok session", notice)
        self.assertIn("restart Grok", notice)
        self.assertIsNone(keepalive.health_notice(run, self.env("h1")))

    def test_a_bound_session_never_warns(self) -> None:
        self.hook("observe", "grok", self.payload("grok", "observe", "h2"))
        for _ in range(3):
            self.assertIsNone(keepalive.health_notice(str(self.run_dir), self.env("h2")))
        self.assertIsNone(keepalive.health_notice(str(self.run_dir), {}))

    def test_the_cli_prints_the_warning_on_stderr(self) -> None:
        env = {**os.environ, **self.env("h3")}
        argv = [sys.executable, str(SCRIPTS / "shiploop"), "next", "--run-dir", str(self.run_dir)]
        first = subprocess.run(argv, capture_output=True, text=True, env=env, check=False)
        second = subprocess.run(argv, capture_output=True, text=True, env=env, check=False)
        self.assertNotIn("keepalive is not active", first.stderr)
        self.assertIn("keepalive is not active in this grok session", second.stderr)
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
            self.assertEqual(self.stop_decision("claude", "first")["why"], "no progress")
        self.bind("claude", "second")  # the next session picks the run up
        self.assertEqual(self.stop_decision("claude", "second")["decision"], "continue")

    def test_a_silent_owner_goes_stale(self) -> None:
        self.bind("claude", "crashed")
        with mock.patch.object(keepalive, "OWNER_STALE_SECONDS", 0):
            self.bind("grok", "fresh")
            self.assertEqual(self.stop_decision("grok", "fresh")["decision"], "continue")

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
                {"GROK_PLUGIN_ROOT": "/p"}, "grok", "grok"), ({"CURSOR_PLUGIN_ROOT": "/p"}, "cursor", "cursor"),
                ({}, "codex", "codex"), ({}, "claude", "claude")):
            with self.subTest(expected=expected), mock.patch.dict(os.environ, env):
                keepalive.release_owner(str(self.run_dir))
                self.hook("observe", "auto", self.payload(payload_host, "observe", f"auto-{expected}"))
                self.assertIsNotNone(keepalive.load_binding(expected, f"auto-{expected}"))
                reply = self.hook("stop", "auto", self.payload(payload_host, "stop", f"auto-{expected}"))
                self.assertIn("followup_message" if expected == "cursor" else "decision", reply)


class SessionEndTests(KeepaliveTestCase):
    """The host ends a session (a /clear, an exit): the run it owned is released at once, so the next session need not
    wait OWNER_STALE_SECONDS (owner, 2026-10-28). A killed session sends nothing; OwnerProcessTests covers that."""

    def bind(self, host: str, session: str) -> str:
        self.hook("observe", host, self.payload(host, "observe", session))
        return keepalive.load_binding(host, session)["run_dir"]

    def test_each_hosts_session_end_releases_the_run_its_session_owned(self) -> None:
        for host in ("claude", "codex", "cursor", "grok"):
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


class InstallTests(KeepaliveTestCase):
    def home(self) -> Path:
        return self.temp / "home"

    def test_install_status_uninstall_preserves_other_entries(self) -> None:
        settings = self.home() / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        other = {"type": "command", "command": "python3 /opt/other.py"}
        settings.write_text(json.dumps({"model": "opus", "hooks": {"Stop": [{"hooks": [other]}]}}))
        for host in keepalive.HOSTS:
            keepalive.install(host)
            self.assertEqual(keepalive.status(host), "installed", host)
            keepalive.install(host)  # idempotent
        data = json.loads(settings.read_text())
        self.assertEqual(len(data["hooks"]["Stop"]), 2)
        self.assertEqual(data["hooks"]["PostToolUse"][0]["matcher"], "Bash")
        self.assertIn("session-end --host claude", data["hooks"]["SessionEnd"][0]["hooks"][0]["command"])
        cursor = json.loads((self.home() / ".cursor" / "hooks.json").read_text())
        self.assertEqual(cursor["version"], 1)
        self.assertIn("afterShellExecution", cursor["hooks"])
        self.assertIn("session-end --host cursor", cursor["hooks"]["sessionEnd"][0]["command"])
        plugin = (self.home() / ".config" / "opencode" / "plugins" / "shiploop-keepalive.js").read_text()
        self.assertIn(json.dumps(str(SCRIPTS / "shiploop-hook")), plugin)
        for host in keepalive.HOSTS:
            keepalive.install(host, remove=True)
            self.assertEqual(keepalive.status(host), "absent", host)
        self.assertEqual(json.loads(settings.read_text()),
                         {"model": "opus", "hooks": {"Stop": [{"hooks": [other]}]}})
        self.assertFalse((self.home() / ".cursor" / "hooks.json").exists())
        self.assertFalse((self.home() / ".grok" / "hooks" / "shiploop-keepalive.json").exists())

    def test_foreign_or_invalid_files_are_refused(self) -> None:
        plugin = self.home() / ".config" / "opencode" / "plugins" / "shiploop-keepalive.js"
        plugin.parent.mkdir(parents=True)
        plugin.write_text("// someone else's plugin\n")
        with self.assertRaises(keepalive.InstallError):
            keepalive.install("opencode")
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
        code, lines = self.drive("grok", lambda argv, **kwargs: self.done(argv))
        self.assertEqual(code, keepalive.EXIT_STUCK)
        self.assertIn("two sessions in a row", lines[-1])

    def test_a_host_that_fails_without_progress_is_reported_at_once(self) -> None:
        code, lines = self.drive("opencode", lambda argv, **kwargs: self.done(argv, returncode=1))
        self.assertEqual(code, keepalive.EXIT_STUCK)
        self.assertIn("may have failed to start", lines[-1])

    def test_resuming_hosts_continue_the_bound_session(self) -> None:
        self.hook("observe", "cursor", self.payload("cursor", "observe", "chat-42"))
        seen = []

        def runner(argv, **kwargs):
            seen.append(argv)
            self.advance()
            return self.done(argv)

        code, _ = self.drive("cursor", runner, max_minutes=2)
        self.assertEqual(code, keepalive.EXIT_CAP)
        self.assertEqual(seen[0][:4], ["cursor-agent", "-p", "--resume", "chat-42"])

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
        self.drive("codex", lambda argv, **kwargs: self.done(argv))
        run_id = self.status()["run_id"]
        journal = self.temp / "state" / "drive" / run_id / "drive.log"
        self.assertEqual(len(journal.read_text().splitlines()), 2)
        self.assertFalse(any(path.name.startswith("session-") for path in self.run_dir.rglob("*")))


if __name__ == "__main__":
    unittest.main()
