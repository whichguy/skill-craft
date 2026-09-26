#!/usr/bin/env python3
"""ShipLoop keepalive: hook-status, the packet marker, host hooks, install and the driver.

Hook payloads come from recorded host runs (test/fixtures/shiploop-keepalive).
Runs are real ShipLoop runs in temporary directories; no host CLI is launched.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
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

RECORDED_HOSTS = ("claude", "codex", "cursor", "grok")


def shiploop(*argv: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / "shiploop"), *argv],
                          capture_output=True, text=True, check=False)


class KeepaliveTestCase(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="shiploop-keepalive-")
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name).resolve()
        self.repo = self.temp / "repo"
        self.run_dir = self.temp / "run"
        self.repo.mkdir()
        env = {"SHIPLOOP_KEEPALIVE_HOME": str(self.temp / "state"), "HOME": str(self.temp / "home"),
               "XDG_CONFIG_HOME": str(self.temp / "home" / ".config")}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
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

    def test_marker_copied_from_elsewhere_does_not_bind(self) -> None:
        payload = self.payload("claude", "observe")
        payload["tool_response"]["stdout"] = f"SHIPLOOP-RUN run=nav-0000 rev=0 dir={self.run_dir}"
        self.hook("observe", "claude", payload)
        self.assertIsNone(keepalive.load_binding("claude", "session-1"))

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

    def test_an_improve_review_pass_is_part_of_progress(self) -> None:
        sys.path.insert(0, str(SCRIPTS))
        import shiploop_protocol as protocol
        receipt = self.temp / "packet.json"
        receipt.write_text(json.dumps({"progress": {"action_number": 3}}))
        import shiploop_standalone_improve as standalone
        with mock.patch.object(standalone, "receipt_path", return_value=receipt):
            self.assertEqual(protocol._improve_pass({"active_improve": {"skill": "card"}}), 3)
        self.assertEqual(protocol._improve_pass({"active_improve": None}), 0)
        self.assertIn(".", self.status()["progress"])


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
        cursor = json.loads((self.home() / ".cursor" / "hooks.json").read_text())
        self.assertEqual(cursor["version"], 1)
        self.assertIn("afterShellExecution", cursor["hooks"])
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

        plugin = package_build.plugins() / "shiploop"
        for file_name, variable, host, extra in self.HOST_FILES:
            with self.subTest(host=host):
                keepalive.release_owner(str(self.run_dir))
                hooks = json.loads((plugin / "hooks" / file_name).read_text())
                cursor = file_name == "cursor.json"
                observe = self.commands(hooks, "afterShellExecution" if cursor else "PostToolUse")
                stop = self.commands(hooks, "stop" if cursor else "Stop")
                self.assertEqual((len(observe), len(stop)), (1, 1))
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


class DriverTests(KeepaliveTestCase):
    def drive(self, host: str, runner, **options) -> tuple[int, list[str]]:
        lines: list[str] = []
        code = keepalive.drive(host, str(self.run_dir), max_sessions=options.get("max_sessions", 5),
                               session_timeout=60, extra=["--model", "test"], cwd=None,
                               out=lines.append, runner=runner)
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

        code, _ = self.drive("cursor", runner, max_sessions=2)
        self.assertEqual(code, keepalive.EXIT_CAP)
        self.assertEqual(seen[0][:4], ["cursor-agent", "-p", "--resume", "chat-42"])

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

        self.drive("claude", runner, max_sessions=2)
        self.assertEqual(owners, ["claude:driven-0", "claude:driven-1"])

    def test_session_logs_and_journal_are_kept_outside_the_run(self) -> None:
        self.drive("codex", lambda argv, **kwargs: self.done(argv))
        run_id = self.status()["run_id"]
        journal = self.temp / "state" / "drive" / run_id / "drive.log"
        self.assertEqual(len(journal.read_text().splitlines()), 2)
        self.assertFalse(any(path.name.startswith("session-") for path in self.run_dir.rglob("*")))


if __name__ == "__main__":
    unittest.main()
