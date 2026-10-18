#!/usr/bin/env python3
"""The Skill-call record (a Claude Code hook) and the Improve stage's gate on it.

A packet tells the model to invoke the improve skill at every Improve stage, and live runs skipped it: wording does not
enforce that, a record the model does not write can.  These tests run the real route: Claude Code's hook payload (recorded
2026-10-16, test/fixtures/shiploop-keepalive/claude-skill.json) goes to the hook script, the hook appends to the run's
skill-calls.jsonl, and `complete` on an Improve stage reads it.  Runs are real ShipLoop runs in temporary directories; no host
CLI is launched.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
FIXTURES = ROOT / "test" / "fixtures" / "shiploop-keepalive"
CLI = SCRIPTS / "shiploop"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "test"))

import shiploop_keepalive as keepalive  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_skill_calls as skill_calls  # noqa: E402
import shiploop_standalone_improve as bridge  # noqa: E402
import shiploop_store as store  # noqa: E402


def _load(name: str, file: str):
    """A sibling test file as a module (their names have hyphens), for its fixture class."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "test" / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


keepalive_tests = _load("shiploop_keepalive_fixture", "shiploop-keepalive.test.py")
improve_tests = _load("shiploop_improve_cli_fixture", "shiploop-actual-improve-cli.test.py")

IMPROVE_ARGS = navigator.IMPROVE_ARGUMENT_PREFIX


def skill_payload(session: str, skill: str, args: str | None = None, **extra) -> dict:
    """The recorded Skill-tool PostToolUse payload, for ``skill`` called with ``args``."""
    payload = json.loads((FIXTURES / "claude-skill.json").read_text(encoding="utf-8"))
    payload["session_id"] = session
    payload["tool_input"] = {"skill": skill, **({} if args is None else {"args": args})}
    payload.update(extra)
    return payload


def records(run_dir: Path) -> list[dict]:
    return [item for item in skill_calls.read_records(run_dir) if "gate" not in item]


class SkillCallHookTests(keepalive_tests.KeepaliveTestCase):
    """The hook: what it records, and everything it must not do."""

    def bind(self, session: str = "session-1") -> None:
        self.hook("observe", "claude", self.payload("claude", "observe", session))
        self.assertIsNotNone(keepalive.load_binding("claude", session))

    def skill(self, session: str, skill: str, args: str | None = None, **extra) -> None:
        self.assertIsNone(self.hook("skill", "claude", skill_payload(session, skill, args, **extra)))

    def test_a_bound_sessions_skill_call_is_recorded_in_its_run(self) -> None:
        self.bind()
        self.skill("session-1", "skill-craft:improve", "ShipLoop Improve: /w/handoff.md")
        found = records(self.run_dir)
        self.assertEqual(len(found), 1)
        record = found[0]
        self.assertEqual((record["skill"], record["called_as"]), ("improve", "skill-craft:improve"))
        self.assertEqual(record["args"], "ShipLoop Improve: /w/handoff.md")
        self.assertEqual(record["session"], "session-1")
        self.assertEqual(record["tool_use_id"], "toolu_01SkillFixtureCall")
        self.assertRegex(record["at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertIsInstance(record["ts"], float)
        self.assertNotIn("agent_id", record)

    def test_skill_names_are_normalised_and_calls_accumulate_in_order(self) -> None:
        self.bind()
        for raw in ("improve", "skill-craft:improve", "/improve", "Improve", "improve-agent"):
            self.skill("session-1", raw, None)
        self.assertEqual([item["skill"] for item in records(self.run_dir)],
                         ["improve", "improve", "improve", "improve", "improve-agent"])
        self.assertEqual([item["args"] for item in records(self.run_dir)], [""] * 5)
        stamps = [item["ts"] for item in records(self.run_dir)]
        self.assertEqual(stamps, sorted(stamps))

    def test_a_subagent_call_is_recorded_with_its_agent_id(self) -> None:
        self.bind()
        self.skill("session-1", "improve", "x", agent_id="agent-7", agent_type="general")
        self.assertEqual(records(self.run_dir)[0]["agent_id"], "agent-7")

    def test_nothing_is_recorded_unless_a_bound_claude_session_called_the_skill_tool(self) -> None:
        self.skill("never-bound", "improve", "x")  # no binding for this session
        self.bind()
        self.skill("another-session", "improve", "x")  # a session that is bound to nothing writes into no run
        other_tool = skill_payload("session-1", "improve", "x", tool_name="Bash")
        self.assertIsNone(self.hook("skill", "claude", other_tool))
        # another host's payload reaches this host's entry only by mistake; its own entry handles it
        codex = {**skill_payload("session-1", "improve", "x"), "turn_id": "t1"}
        self.assertIsNone(self.hook("skill", "claude", codex))
        no_skill = skill_payload("session-1", "improve", "x")
        no_skill["tool_input"] = {"args": "x"}
        self.assertIsNone(self.hook("skill", "claude", no_skill))
        self.assertIsNone(self.hook("skill", "grok", skill_payload("session-1", "improve", "x")))
        with mock.patch.dict(os.environ, {"SHIPLOOP_KEEPALIVE": "off"}):
            self.skill("session-1", "improve", "x")
        self.assertEqual(records(self.run_dir), [])
        self.assertFalse((self.run_dir / skill_calls.RECORD_FILE).exists())

    def test_the_hook_writes_only_a_regular_file_inside_a_run_directory(self) -> None:
        self.bind()
        outside = self.temp / "outside.txt"
        outside.write_text("untouched\n")
        (self.run_dir / skill_calls.RECORD_FILE).symlink_to(outside)
        self.skill("session-1", "improve", "x")  # refused quietly: the record is a symlink
        self.assertEqual(outside.read_text(), "untouched\n")
        (self.run_dir / skill_calls.RECORD_FILE).unlink()
        # a binding that names a directory that is not a run is left alone
        stray = self.temp / "not-a-run"
        stray.mkdir()
        binding = keepalive.load_binding("claude", "session-1")
        keepalive._write_json(keepalive._binding_path("claude", "session-1"), {**binding, "run_dir": str(stray)})
        self.skill("session-1", "improve", "x")
        self.assertEqual(list(stray.iterdir()), [])
        keepalive._write_json(keepalive._binding_path("claude", "session-1"), {**binding, "run_dir": "relative/run"})
        self.skill("session-1", "improve", "x")
        self.assertFalse((self.run_dir / skill_calls.RECORD_FILE).exists())

    def test_the_entry_script_is_silent_fast_and_never_fails_the_call(self) -> None:
        self.bind()
        env = {**os.environ}
        entry = SCRIPTS / "shiploop-skill-call"
        good = subprocess.run([sys.executable, str(entry)], input=json.dumps(
            skill_payload("session-1", "improve", "ShipLoop Improve: /w/handoff.md")), capture_output=True, text=True,
            env=env, check=False)
        self.assertEqual((good.returncode, good.stdout, good.stderr), (0, "", ""))
        self.assertEqual(len(records(self.run_dir)), 1)
        for junk in ("", "{not json", "[]", '{"tool_name": "Skill"}', json.dumps(skill_payload("session-1", "improve", 7))):
            result = subprocess.run([sys.executable, str(entry)], input=junk, capture_output=True, text=True, env=env,
                                    check=False)
            self.assertEqual((result.returncode, result.stdout), (0, ""), junk)
        # a non-string argument is kept as JSON text, not dropped or crashed on
        self.assertEqual(records(self.run_dir)[-1]["args"], "7")

    def test_the_entry_script_survives_a_closed_stdin_and_bytes_that_are_not_text(self) -> None:
        self.bind()
        entry = SCRIPTS / "shiploop-skill-call"
        closed = subprocess.run(f"{shlex.quote(sys.executable)} {shlex.quote(str(entry))} <&-", shell=True,
                                capture_output=True, text=True, check=False)
        self.assertEqual((closed.returncode, closed.stdout, closed.stderr), (0, "", ""))
        strict = subprocess.run([sys.executable, str(entry)], input=b"\xff\xfe{", capture_output=True, check=False,
                                env={**os.environ, "PYTHONIOENCODING": "utf-8:strict"})
        self.assertEqual((strict.returncode, strict.stdout, strict.stderr), (0, b"", b""))
        self.assertEqual(records(self.run_dir), [])

    def test_a_record_line_stays_bounded(self) -> None:
        self.bind()
        self.skill("session-1", "improve", "a" * 50_000)
        self.assertEqual(len(records(self.run_dir)[0]["args"]), skill_calls.ARGS_LIMIT)


class SkillHookRegistrationTests(keepalive_tests.KeepaliveTestCase):
    """What the binding says about the Skill-call hook, and how each route registers it."""

    def home(self) -> Path:
        return self.temp / "home"

    def bound(self) -> dict:
        self.hook("observe", "claude", self.payload("claude", "observe"))
        return keepalive.load_binding("claude", "session-1")

    def test_a_session_bound_by_hooks_that_lack_the_skill_hook_says_so(self) -> None:
        # No ShipLoop hook entry in the Claude settings at all: nothing records Skill calls.
        self.assertFalse(self.bound()["skill_hook"])

    def test_a_settings_install_registers_the_skill_hook_with_the_skill_matcher(self) -> None:
        keepalive.install("claude")
        data = json.loads((self.home() / ".claude" / "settings.json").read_text())
        groups = {group["matcher"]: group["hooks"] for group in data["hooks"]["PostToolUse"]}
        self.assertEqual(set(groups), {"Bash", "Skill"})
        [skill_entry] = groups["Skill"]
        self.assertEqual(shlex.split(skill_entry["command"])[2:], ["skill", "--host", "claude"])
        self.assertEqual(keepalive.status("claude"), "installed")
        self.assertTrue(self.bound()["skill_hook"])
        keepalive.install("claude", remove=True)
        self.assertEqual(keepalive.status("claude"), "absent")

    def test_an_install_from_before_the_skill_hook_is_stale_and_does_not_enforce(self) -> None:
        keepalive.install("claude")
        settings = self.home() / ".claude" / "settings.json"
        data = json.loads(settings.read_text())
        data["hooks"]["PostToolUse"] = [group for group in data["hooks"]["PostToolUse"] if group["matcher"] != "Skill"]
        settings.write_text(json.dumps(data))
        self.assertEqual(keepalive.status("claude"), "stale")
        self.assertFalse(self.bound()["skill_hook"])
        keepalive.install("claude")  # the repair: install again
        self.assertEqual(keepalive.status("claude"), "installed")
        self.assertTrue(self.bound()["skill_hook"])

    def test_other_hosts_install_no_skill_hook(self) -> None:
        for host in ("codex", "cursor", "grok"):
            keepalive.install(host)
            self.assertNotIn("Skill", (self.home() / {"codex": ".codex/hooks.json", "cursor": ".cursor/hooks.json",
                                                      "grok": ".grok/hooks/shiploop-keepalive.json"}[host]).read_text())
            self.assertEqual(keepalive.status(host), "installed")

    def test_the_generated_package_registers_it_for_claude_and_no_other_host(self) -> None:
        import package_build

        plugin = package_build.plugins() / "skill-craft"
        claude = json.loads((plugin / "hooks" / "hooks.json").read_text())
        [skill_group] = [group for group in claude["hooks"]["PostToolUse"] if group["matcher"] == "Skill"]
        self.assertEqual([hook["command"] for hook in skill_group["hooks"]],
                         ["${CLAUDE_PLUGIN_ROOT}/skills/shiploop/scripts/shiploop-skill-call"])
        for other in ("codex.json", "cursor.json"):
            self.assertNotIn("shiploop-skill-call", (plugin / "hooks" / other).read_text(), other)
        script = plugin / "skills" / "shiploop" / "scripts" / "shiploop-skill-call"
        self.assertTrue(os.access(script, os.X_OK))

    def test_a_plugin_package_binds_and_records_through_its_own_scripts(self) -> None:
        import package_build

        scripts = package_build.plugins() / "skill-craft" / "skills" / "shiploop" / "scripts"
        env = {**os.environ}
        observed = subprocess.run([sys.executable, str(scripts / "shiploop-keepalive-observe")],
                                  input=json.dumps(self.payload("claude", "observe")), capture_output=True, text=True,
                                  env=env, check=False)
        self.assertEqual((observed.returncode, observed.stdout), (0, ""), observed.stderr)
        self.assertTrue(keepalive.load_binding("claude", "session-1")["skill_hook"])
        recorded = subprocess.run([sys.executable, str(scripts / "shiploop-skill-call")],
                                  input=json.dumps(skill_payload("session-1", "skill-craft:improve", "x")),
                                  capture_output=True, text=True, env=env, check=False)
        self.assertEqual((recorded.returncode, recorded.stdout), (0, ""), recorded.stderr)
        self.assertEqual([item["skill"] for item in records(self.run_dir)], ["improve"])


class SkillCallRecordTests(unittest.TestCase):
    def test_the_not_enforced_note_is_said_once_per_run(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            first, second = _Echo(), _Echo()
            self.assertTrue(skill_calls.note_not_enforced(run, "nav-a", "no hooks here", echo=first))
            self.assertFalse(skill_calls.note_not_enforced(run, "nav-b", "no hooks here", echo=second))
            self.assertIn("not enforced on this host (no hooks here)", first.text)
            self.assertEqual(second.text, "")
            lines = [json.loads(line) for line in (run / skill_calls.RECORD_FILE).read_text().splitlines()]
            self.assertEqual([(line["gate"], line["action"]) for line in lines], [("not enforced", "nav-a")])

    def test_a_record_survives_characters_that_str_splitlines_would_split_on(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            (run / "state.md").write_text("x")
            skill_calls.record_call(run, {"skill": "improve", "args": "ShipLoop Improve:\u2028/w/handoff.md\x85"},
                                    session="s", now=100.0)
            self.assertEqual(len(skill_calls.read_records(run)), 1)
            self.assertIsNotNone(skill_calls.improve_call_since(run, 0, ["/w/handoff.md"]))

    def test_only_this_plugins_improve_is_the_improve_skill(self) -> None:
        for name in ("improve", "/improve", "Improve", " skill-craft:improve ", "/skill-craft:improve"):
            self.assertEqual(skill_calls.skill_name(name), "improve", name)
        for name in ("evilplugin:improve", "other:skill-craft:improve", "improve-agent", "skill-craft:improve-agent",
                     "improved", ""):
            self.assertNotEqual(skill_calls.skill_name(name), "improve", name)

    def test_matching_ignores_quotes_and_takes_the_latest_call_after_the_start(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            (run / "state.md").write_text("x")
            skill_calls.record_call(run, {"skill": "improve", "args": 'ShipLoop Improve: "/w/a b/handoff.md"'},
                                    session="s", now=100.0)
            skill_calls.record_call(run, {"skill": "grill-me", "args": "/w/a b/handoff.md"}, session="s", now=150.0)
            token = "/w/a b/handoff.md"
            self.assertEqual(skill_calls.improve_call_since(run, 100.0, [token])["ts"], 100.0)
            self.assertIsNone(skill_calls.improve_call_since(run, 100.1, [token]))  # made before the start
            self.assertIsNone(skill_calls.improve_call_since(run, 0, ["/w/other/handoff.md"]))  # another stage's
            self.assertIsNone(skill_calls.improve_call_since(run, 0, []))


class _Echo:
    def __init__(self) -> None:
        self.text = ""

    def write(self, text: str) -> None:
        self.text += text


# What each non-Claude host sets in the shells it runs (any one row entry is enough).  A host started from a Claude Code
# shell inherits Claude's session variables as well and has no Skill tool; its own marker must win.
NESTED_HOST_MARKERS = {
    "grok": ({"GROK_AGENT": "1", "GROK_SESSION_ID": "grok-1"},),
    "codex": ({"CODEX_THREAD_ID": "codex-thread-1"}, {"CODEX_SANDBOX": "seatbelt"}),
    "cursor": ({"CURSOR_PLUGIN_ROOT": "/plugin"},),
    "opencode": ({"OPENCODE": "1"},),
}


class GateFixture(improve_tests.ImproveCliFixture):
    """A run at its first Improve stage, finished, with the real hook available to bind and record."""

    SESSION = "claude-session-1"

    def setUp(self) -> None:
        super().setUp()
        self.keepalive_home = self.base / "keepalive"
        self.claude_home = self.base / "claude-home"
        self.environment.update({"CLAUDECODE": "1", "CLAUDE_CODE_SESSION_ID": self.SESSION,
                                 "SHIPLOOP_KEEPALIVE_HOME": str(self.keepalive_home)})
        self.finish_ephemeral()
        self.completion, _receipt = self.completion_receipt()
        self.handoff = navigator.improve_handoff_path(self.bound)

    def hook_environment(self):
        return mock.patch.dict(os.environ, {"HOME": str(self.claude_home),
                                            "SHIPLOOP_KEEPALIVE_HOME": str(self.keepalive_home)})

    def bind(self, *, hooks_installed: bool = True) -> dict:
        """Bind the Claude session to the run the way the plugin's observe hook does after a driving command."""
        status = keepalive.run_status(str(self.run))
        marker = f"{navigator.KEEPALIVE_MARKER} run={status['run_id']} rev={status['revision']} dir={self.run}"
        payload = json.loads((FIXTURES / "claude-observe.json").read_text(encoding="utf-8")
                             .replace("__SESSION__", self.SESSION).replace("__MARKER__", marker))
        payload["tool_input"]["command"] = f"python3 {CLI} next --run-dir {self.run}"
        with self.hook_environment():
            if hooks_installed:
                keepalive.install("claude")
            keepalive.run_hook("observe", "claude", json.dumps(payload))
            return keepalive.load_binding("claude", self.SESSION)

    def call_skill(self, skill: str, args: str | None) -> None:
        with self.hook_environment():
            reply = keepalive.run_hook("skill", "claude", json.dumps(skill_payload(self.SESSION, skill, args)))
        self.assertEqual(reply, "")

    def complete(self, status: int = 0):
        return self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve, *self.completion,
                           status=status)

    def argument(self) -> str:
        return IMPROVE_ARGS + str(self.handoff)

    def state_bytes(self) -> bytes:
        return (self.run / "state.md").read_bytes()

    def gate_lines(self) -> list[dict]:
        return [item for item in skill_calls.read_records(self.run) if "gate" in item]


class SkillCallGateTests(GateFixture):
    """`complete` on an Improve stage, through the real CLI, with the real hook writing the record."""

    def test_without_a_record_an_ended_loop_is_refused_and_the_named_restart_route_is_accepted(self) -> None:
        """C6/IMP-2: the loop is already complete, so a Skill call now would review nothing; the backstop's named exit is
        improve-start --restart-stopped, then the skill, then complete (submitted through the real gate here)."""
        self.assertTrue(self.bind()["skill_hook"])
        before = self.state_bytes()
        refused = self.complete(status=2).stderr
        self.assertEqual(self.state_bytes(), before)
        first = refused.splitlines()[0]
        self.assertIn("Run the improve skill on this " + self.bound["stage"] + " result first", first)
        self.assertIn("its review loop has already ended", first)
        named_args = re.search(r'args "([^"]+)"', first)[1]
        self.assertEqual(named_args, self.argument())
        self.assertIn('skill "improve"', first)
        restart = shlex.split(re.search(r"start the review again with (.+? --restart-stopped)", first).group(1))
        self.assertEqual(restart[2:], ["improve-start", "--run-dir=" + str(self.run), "--action=" + self.improve,
                                       "--restart-stopped"])
        named = shlex.split(first.rsplit("then run: ", 1)[1])
        self.assertEqual(named[2:], ["complete", "--run-dir=" + str(self.run), "--action=" + self.improve])
        restarted = subprocess.run(restart, text=True, capture_output=True, cwd=self.base, timeout=60,
                                   env=self.environment)
        self.assertEqual(restarted.returncode, 0, restarted.stdout + restarted.stderr)
        self.assertIn("Archived the stopped child", restarted.stderr)
        self.call_skill("improve", named_args)  # the skill runs on the new child
        self.finish_ephemeral(json.loads(bridge.receipt_path(self.bound).read_text(encoding="utf-8")))
        self.completion, _receipt = self.completion_receipt()
        done = subprocess.run(named + self.completion, text=True, capture_output=True, cwd=self.base, timeout=60,
                              env={**self.environment})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        after = store.read_record(self.run / "state.md")
        self.assertIsNone(after["active_improve"])
        self.assertEqual(after["improve_results"][self.action]["runtime_phase"], "complete")
        self.assertEqual(self.gate_lines(), [])  # enforced, so nothing was waved through
        passes = (self.run / "improve" / self.action / "passes.md").read_text(encoding="utf-8")
        rows = [line for line in passes.splitlines() if line.startswith("| " + self.bound["stage"] + " |")]
        self.assertTrue(rows and all(line.endswith("| y |") for line in rows), passes)

    def test_a_restart_is_refused_once_the_ended_loop_has_its_recorded_call(self) -> None:
        self.bind()
        self.call_skill("improve", self.argument())
        refused = self.invoke(CLI, "improve-start", "--run-dir", self.run, "--action", self.improve,
                              "--restart-stopped", status=2).stderr
        self.assertIn("this review is still running", refused)
        self.complete()

    def test_a_call_for_another_stage_or_before_the_stage_started_does_not_count(self) -> None:
        self.bind()
        before = self.state_bytes()
        # Another Improve stage's handoff, and other skills called with this stage's own argument.
        self.call_skill("improve", IMPROVE_ARGS + str(self.handoff.parent.parent / "nav-other0000" / "handoff.md"))
        self.call_skill("improve-agent", self.argument())
        self.call_skill("grill-me", self.argument())
        self.complete(status=2)
        self.assertEqual(self.state_bytes(), before)
        # The right call, but it predates the stage's start (a restart rewrites start.json): refused ...
        self.call_skill("improve", self.argument())
        start = bridge.receipt_path(self.bound).with_name("start.json")
        old = start.stat().st_mtime
        os.utime(start, (old + 120, old + 120))
        self.complete(status=2)
        self.assertEqual(self.state_bytes(), before)
        # ... and the same record counts once the stage started before it.
        os.utime(start, (old, old))
        self.complete()
        self.assertEqual(store.read_record(self.run / "state.md")["improve_results"][self.action]["runtime_phase"],
                         "complete")

    def test_plugin_prefix_and_quoting_around_the_path_still_count(self) -> None:
        self.bind()
        self.call_skill("skill-craft:improve", IMPROVE_ARGS + "'" + str(self.handoff) + "'")
        self.complete()

    def test_the_stage_action_id_alone_names_the_stage(self) -> None:
        self.bind()
        self.call_skill("/improve", "review " + self.improve)
        self.complete()

    def test_a_session_no_hook_bound_is_not_gated_and_the_gap_is_said_once(self) -> None:
        done = self.complete()
        self.assertIn("not enforced on this host (ShipLoop's hooks have not bound this Claude Code session to this run)",
                      done.stderr)
        self.assertEqual([item["gate"] for item in self.gate_lines()], ["not enforced"])
        # Said once for the run: the next Improve stage does not repeat it.
        self.complete_current_stage_through_actual_improve(self.parent_evidence_refs, "Second stage evidence.")
        self.assertEqual(len(self.gate_lines()), 1)

    def test_a_refusal_by_a_later_gate_keeps_its_first_line_and_the_note_waits_for_the_import(self) -> None:
        # The refusal's first line is the fix (parent-return.md says so); the note must not displace it.
        notes = Path(self.completion[self.completion.index("--notes") + 1])
        notes.rename(notes.with_name("notes.moved"))
        refused = self.complete(status=2)
        self.assertNotIn("not enforced", refused.stderr)
        self.assertEqual(self.gate_lines(), [])
        notes.with_name("notes.moved").rename(notes)
        done = self.complete()
        self.assertEqual(done.stderr.count("not enforced"), 1)
        self.assertEqual(len(self.gate_lines()), 1)

    def test_hooks_without_the_skill_hook_do_not_hold_the_run_to_a_record_nothing_writes(self) -> None:
        self.assertFalse(self.bind(hooks_installed=False)["skill_hook"])
        done = self.complete()
        self.assertIn("the hooks that bound this session do not include the Skill-call hook", done.stderr)

    def test_hooks_turned_off_are_not_gated(self) -> None:
        self.bind()
        self.environment["SHIPLOOP_KEEPALIVE"] = "off"
        done = self.complete()
        self.assertIn("SHIPLOOP_KEEPALIVE turns ShipLoop's hooks off", done.stderr)

    def test_a_grok_session_is_not_gated(self) -> None:
        for name in ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID"):
            self.environment.pop(name)
        self.environment.update({"GROK_AGENT": "1", "GROK_SESSION_ID": "grok-1", "HOME": str(self.claude_home)})
        done = self.complete()
        self.assertIn("only Claude Code's hooks record Skill calls", done.stderr)

    def test_codex_or_cursor_started_from_a_bound_claude_shell_is_not_gated(self) -> None:
        # Such a host inherits Claude's session variables, has no Skill tool or Skill-call hook, and so could never
        # satisfy the gate: its own marker wins over the inherited Claude session.
        self.bind()
        inherited = {**self.environment}
        with self.hook_environment():
            self.assertEqual(keepalive.skill_gate(str(self.run), inherited), (True, ""))
            for marker in ("CODEX_THREAD_ID", "CODEX_SANDBOX", "CURSOR_PLUGIN_ROOT", "OPENCODE"):
                with self.subTest(marker=marker):
                    enforce, why = keepalive.skill_gate(str(self.run), {**inherited, marker: "1"})
                    self.assertFalse(enforce)
                    self.assertIn("only Claude Code's hooks record Skill calls", why)
        self.environment["CODEX_THREAD_ID"] = "codex-thread-1"
        done = self.complete()
        self.assertIn("only Claude Code's hooks record Skill calls", done.stderr)
        self.assertNotIn("Run the improve skill on this", done.stderr)

    def test_every_non_claude_host_has_a_nested_marker_that_beats_an_inherited_claude_session(self) -> None:
        # The host list comes from the hook installer's own table, so a host added there fails here until its marker
        # is known (a table row below) and skill_gate reads it.  OpenCode sets OPENCODE=1 in its process at startup
        # and the shells it runs inherit it (a string in the 1.18.31 binary: process.env.OPENCODE="1").
        others = [host for host in keepalive.HOSTS if host != "claude"]
        self.assertEqual(sorted(others), sorted(NESTED_HOST_MARKERS),
                         "a host in keepalive.HOSTS has no known marker for a nested start from a Claude shell")
        self.bind()
        inherited = {**self.environment}
        with self.hook_environment():
            self.assertEqual(keepalive.skill_gate(str(self.run), inherited), (True, ""))
            for host in others:
                for marker in NESTED_HOST_MARKERS[host]:
                    with self.subTest(host=host, marker=sorted(marker)):
                        enforce, why = keepalive.skill_gate(str(self.run), {**inherited, **marker})
                        self.assertFalse(enforce)
                        self.assertIn("only Claude Code's hooks record Skill calls", why)

    def test_a_session_bound_to_another_run_does_not_gate_this_one(self) -> None:
        binding = self.bind()
        with self.hook_environment():
            keepalive._write_json(keepalive._binding_path("claude", self.SESSION),
                                  {**binding, "run_dir": str(self.base / "other-run")})
        done = self.complete()
        self.assertIn("have not bound this Claude Code session to this run", done.stderr)


class ImprovePassGateTests(GateFixture):
    """improve-pass checks the recorded improve-skill call before any runtime done exists (IMP-2): the refusal prints
    first, no done command is printed, and its named exit (the skill, then improve-pass again) is accepted."""

    def setUp(self) -> None:
        improve_tests.ImproveCliFixture.setUp(self)
        self.keepalive_home = self.base / "keepalive"
        self.claude_home = self.base / "claude-home"
        self.environment.update({"CLAUDECODE": "1", "CLAUDE_CODE_SESSION_ID": self.SESSION,
                                 "SHIPLOOP_KEEPALIVE_HOME": str(self.keepalive_home)})
        self.handoff = navigator.improve_handoff_path(self.bound)
        # The shared fixture's repository is not a Git worktree (main's Improve runtime would otherwise end a review on
        # its first unchanged pass); improve-pass needs a measured tree to see that this review changed nothing, so this
        # test makes one and records the review's starting snapshot again.
        import shiploop_improve_changes as improve_changes
        for args in (("init", "-q"), ("add", "-A"), ("-c", "user.name=Fixture", "-c", "user.email=f@example.invalid",
                                                      "commit", "-qm", "fixture")):
            subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True, env=self.environment)
        for relative, text in improve_changes.bind_writes(self.run, self.repo, self.bound["action_id"]).items():
            store.atomic_write_text(Path(self.run) / relative, text)
        reviews = bridge.receipt_path(self.bound).parent / "reviews"
        (reviews / "review-1.md").write_text(
            "---\nclassification: trivial\nexit: satisfied\ncontinuation: allowed\n---\nRead: the result.\n"
            "Found: nothing material.\nChanged: none.\nChecked: the fixture's check passed.\nClass: no change.\n"
            "## Handoff\nNothing open.\n", encoding="utf-8")
        self.pass_argv = [CLI, "improve-pass", "--run-dir", self.run, "--action", self.improve]

    def test_the_skill_call_refusal_prints_before_done_and_its_named_exit_is_accepted(self) -> None:
        self.bind()
        refused = self.invoke(*self.pass_argv, status=2)
        self.assertNotIn(" done --state ", refused.stdout + refused.stderr)
        first = refused.stderr.splitlines()[0]
        self.assertIn("Run the improve skill on this " + self.bound["stage"] + " result first", first)
        named_args = re.search(r'args "([^"]+)"', first)[1]
        self.assertEqual(named_args, self.argument())
        named = shlex.split(first.rsplit("run improve-pass again: ", 1)[1])
        self.assertEqual(named[2:], ["improve-pass", "--run-dir=" + str(self.run), "--action=" + self.improve])
        self.assertFalse((bridge.receipt_path(self.bound).parent / "reviews" / "report-1.json").exists())
        self.call_skill("improve", named_args)
        accepted = subprocess.run(named, text=True, capture_output=True, cwd=self.base, timeout=60,
                                  env=self.environment)
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
        self.assertIn(" done --state ", accepted.stdout)
        self.assertIn("improve skill call recorded", accepted.stdout)

    def test_an_unbound_session_is_not_gated_and_the_pass_says_so(self) -> None:
        accepted = self.invoke(*self.pass_argv)
        self.assertIn("improve skill call not enforced (ShipLoop's hooks have not bound", accepted.stdout)


class SkillCallGateAskAgentTests(GateFixture):
    """The ask-agent route runs the Improve loop in a fresh worker, whose Skill calls this session's hooks never see."""

    delegation = "ask-agent"

    def test_a_bound_session_is_not_gated_when_a_fresh_worker_ran_the_review(self) -> None:
        self.assertTrue(self.bind()["skill_hook"])
        done = self.complete()
        self.assertIn("this review runs in a fresh worker, not in this session (delegation ask-agent)", done.stderr)


if __name__ == "__main__":
    unittest.main()
