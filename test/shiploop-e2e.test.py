#!/usr/bin/env python3
"""No-model checks for the ShipLoop E2E harness (test/shiploop_e2e/).

Fake `grok` and `claude` executables stand in for the hosts, so these checks
cover the harness contract (empty start directory, isolated Grok profile,
argv, plugin and invocation grading, review parsing and the premise filter)
without launching a model. Every case passes its host and fake binary
explicitly and supplies a plugin build, so no real host or build is reached.
They say nothing about live ShipLoop behavior.
"""

from __future__ import annotations

import contextlib
import datetime
import importlib.util
import io
import json
import shutil
import os
from pathlib import Path
import re
import shlex
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import hosts  # noqa: E402
import iterate  # noqa: E402
import metrics  # noqa: E402
import progress  # noqa: E402
import review  # noqa: E402
import rollouts  # noqa: E402
import run  # noqa: E402
import fanout  # noqa: E402

# listeners.py is the module the leftover-listener tests are about. Where it does not exist (the state a failing test is first run
# in) only those tests may fail, each on an assertion (needs_listeners), so a missing module never takes the other tests down.
try:
    import listeners  # noqa: E402
except ModuleNotFoundError as missing:
    if missing.name != "listeners":
        raise
    listeners = None

# The real observer, kept before any test patches it: the classes that exercise lsof scope what it sees to their own folder.
REAL_OBSERVE = listeners.observe if listeners else None


def needs_listeners(cls):
    """Class decorator: while listeners.py does not exist every test of the class fails on this assertion, one by one."""
    inner = cls.setUp

    def setUp(self):
        self.assertIsNotNone(listeners, "test/shiploop_e2e/listeners.py does not exist")
        inner(self)

    cls.setUp = setUp
    return cls


def nothing_listens():
    """A patch that makes the machine's process table show no listener, so no test reads it (nothing to patch where listeners.py
    does not exist yet, and the older tests then run as before)."""
    return mock.patch.object(listeners, "observe", return_value=[]) if listeners else contextlib.nullcontext()

# Shared product writer for both fakes: the hello case's files plus a done run.
PRODUCT = f"""
sys.path.insert(0, {str(ROOT / 'skills/shiploop/scripts')!r})
import shiploop_store as store
def product():
    Path("hello.py").write_text('print("Hello, world!")\\n')
    Path("test_hello.py").write_text(
        "import subprocess, sys, unittest\\n"
        "class T(unittest.TestCase):\\n"
        "    def test_it(self):\\n"
        "        out = subprocess.run([sys.executable, 'hello.py'], capture_output=True, text=True).stdout\\n"
        "        self.assertEqual(out.strip(), 'Hello, world!')\\n")
    Path(".shiploop").mkdir()
    # A current run records its planning_review option; FAKE_PLANNING_REVIEW=absent leaves the key out, as a run before 1.22.0 does.
    state = {{"status": "done"}}
    if os.environ.get("FAKE_PLANNING_REVIEW", "stage") != "absent":
        state["planning_review"] = os.environ.get("FAKE_PLANNING_REVIEW", "stage")
    store.write_record(Path(".shiploop/state.md"), state)
    Path(".shiploop/report.html").write_text("<html></html>")
    # A finished run leaves its product committed, as ShipLoop's return does.
    import subprocess
    Path(".gitignore").write_text(".shiploop/\\n")
    ident = ["-c", "user.name=Fake", "-c", "user.email=fake@example.invalid"]
    if not Path(".git").exists():
        subprocess.run(["git", "init", "-q"], check=True)
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", *ident, "commit", "-q", "--allow-empty", "-m", "product"], check=True)
"""

# A TCP server in a process of its own, as a model's `node server.js &` is: its own session (a host's group kill cannot
# reach it), no stdio shared with its parent, and it expires by itself after two minutes. argv[1] is a port file that
# appears, complete, once the server listens ("<pid> <port>"); argv[2] == "ignore-term" makes it ignore SIGTERM. It accepts and
# drops each connection: a listener that never accepts resets some probes once its backlog fills, which made `answers` flaky.
LISTENER_SOURCE = (
    "import os, socket, sys, time\n"
    "s = socket.socket(); s.bind(('127.0.0.1', 0)); s.listen(1)\n"
    "if sys.argv[2:] == ['ignore-term']:\n"
    "    import signal; signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
    "open(sys.argv[1] + '.part', 'w').write('%d %d' % (os.getpid(), s.getsockname()[1]))\n"
    "os.rename(sys.argv[1] + '.part', sys.argv[1])\n"
    "s.settimeout(0.5)\n"
    "end = time.time() + 120\n"
    "while time.time() < end:\n"
    "    try:\n"
    "        s.accept()[0].close()\n"  # accept and drop, so a probe's connect is not queued behind earlier ones and reset
    "    except OSError:\n"
    "        pass\n")

# What both fake hosts can do with a listener: FAKE_LISTEN=<port file> leaves one running from the working directory, as a
# model's backgrounded server does; FAKE_PROBE_PORT=<port file> records, in FAKE_LOG.probe, whether that server still
# answers when the session starts.
LISTEN = f"""
def leak_a_listener():
    portfile = os.environ.get("FAKE_LISTEN")
    if not portfile:
        return
    import subprocess, time
    subprocess.Popen([sys.executable, "-c", {LISTENER_SOURCE!r}, portfile], start_new_session=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(200):
        if os.path.exists(portfile):
            break
        time.sleep(0.05)
def probe_a_port():
    portfile = os.environ.get("FAKE_PROBE_PORT")
    if not portfile or not os.path.exists(portfile):
        return
    import socket
    probe = socket.socket()
    probe.settimeout(2)
    answered = probe.connect_ex(("127.0.0.1", int(open(portfile).read().split()[1]))) == 0
    with open(os.environ["FAKE_LOG"] + ".probe", "a") as log:
        log.write("answers\\n" if answered else "refused\\n")
"""

# FAKE_MODE: done (product + done run), nothing (exit 0, no work), no-skill (done,
# but no ShipLoop command registered).
FAKE_CLAUDE = f"""#!{sys.executable}
import json, os, sys
from pathlib import Path
{PRODUCT}
{LISTEN}
argv = sys.argv[1:]
Path(os.environ["FAKE_LOG"]).write_text(json.dumps({{"argv": argv, "cwd_listing": os.listdir(".")}}))
mode = os.environ.get("FAKE_MODE")
plugin = argv[argv.index("--plugin-dir") + 1] if "--plugin-dir" in argv else None
print(json.dumps({{"type": "system", "subtype": "init", "model": "fake-model", "claude_code_version": "0.0.1-fake",
                  "slash_commands": [] if mode == "no-skill" else ["skill-craft:shiploop"],
                  "plugins": [{{"name": "skill-craft", "path": plugin}}] if plugin else []}}), flush=True)
print(json.dumps({{"type": "assistant", "message": {{"content": [{{"type": "tool_use", "name": "Bash",
                  "input": {{"command": "shiploop next"}}}}]}}}}))
if os.environ.get("FAKE_COMMAND"):  # one more tool call, for a test that needs the run to do something
    print(json.dumps({{"type": "assistant", "message": {{"content": [{{"type": "tool_use", "name": "Bash",
                      "input": {{"command": os.environ["FAKE_COMMAND"]}}}}]}}}}))
leak_a_listener()
if mode in ("done", "no-skill"):
    product()
if mode == "active":
    Path(".shiploop").mkdir(exist_ok=True)
    store.write_record(Path(".shiploop/state.md"), {{"status": "active", "stage": "test-refine", "revision": 25}})
if mode == "chain-hang":
    sys.path.insert(0, {str(ROOT / 'skills/shiploop/scripts')!r})
    import shiploop_chain_ledger as ledger, time
    chain = Path.cwd().parent / ".shiploop-runs" / "seed" / "run" / "chains" / "nav-1"
    child = chain / "child"
    def ledger_events(*rows):
        start = len(ledger.read_events(str(chain / "events")))
        for number, (kind, data) in enumerate(rows, start):
            ledger.append_event(str(chain / "events"), f"e{{number}}", kind, data)
    if "This session ended" not in argv[argv.index("-p") + 1]:
        child.mkdir(parents=True)
        # The run is active while its chain worker is in flight, as a real run's state.md says.
        store.write_record(chain.parent.parent / "state.md", {{"status": "active", "stage": "implement", "revision": 3}})
        store.write_record(chain / "binding.md", {{"dispatcher_run": str(child), "mode": "parallel"}})
        ledger_events(("launched_result", {{"attempt": "A-1"}}), ("launched_result", {{"attempt": "B-1"}}))
        time.sleep(120)  # killed by --interrupt-at long before this ends
    (child / "plan-dispatcher-state.json").write_text(json.dumps({{
        "graph": {{"steps": [{{"id": "A", "deps": []}}, {{"id": "B", "deps": []}}]}},
        "steps": {{"A": {{"status": "accepted"}}, "B": {{"status": "accepted"}}}},
        "attempts": {{"A-1": {{"step": "A", "handle": "h"}}, "B-1": {{"step": "B", "handle": "h"}}}}}}))
    ledger_events(("handoff_import_result", {{"attempt": "A-1"}}), ("handoff_import_result", {{"attempt": "B-1"}}),
                  ("contribution_recorded", {{"attempt": "A-1", "step": "A"}}),
                  ("contribution_recorded", {{"attempt": "B-1", "step": "B"}}))
    product()
if mode == "api-error":
    # What the real CLI wrote when the API refused: subtype stays "success", is_error says otherwise.
    print(json.dumps({{"type": "result", "subtype": "success", "is_error": True, "terminal_reason": "api_error",
                      "api_error_status": None, "stop_reason": "stop_sequence", "num_turns": 3,
                      "total_cost_usd": 0.0, "result": "API Error: Unable to connect to API: SSL certificate has expired"}}))
    sys.exit(1)
print(json.dumps({{"type": "result", "subtype": "success", "num_turns": 3, "total_cost_usd": 0.0,
                  "result": "done"}}))
"""

FAKE_GROK = f"""#!{sys.executable}
import json, os, sys
from pathlib import Path
{PRODUCT}
{LISTEN}
argv = sys.argv[1:]
home = Path(os.environ["HOME"])
registry = home / ".grok" / "fake-plugins.txt"
if argv[:2] == ["plugin", "install"]:
    registry.write_text(f"  skill-craft-1: skill-craft [local: {{Path(argv[2]).resolve()}}]\\n")
    print("Installed 1 plugin(s)")
    sys.exit(0)
if argv[:2] == ["plugin", "list"]:
    print(registry.read_text() if registry.exists() else "")
    sys.exit(0)
os.chdir(argv[argv.index("--cwd") + 1])
probe_a_port()
prompt = Path(argv[argv.index("--prompt-file") + 1]).read_text()
resumed = argv[argv.index("--resume") + 1] if "--resume" in argv else None
with open(os.environ["FAKE_LOG"] + ".sessions", "a") as log:
    log.write(json.dumps({{"resumed": resumed, "prompt": prompt, "pid": os.getpid()}}) + "\\n")
if os.environ.get("FAKE_MODE") == "crash-resumed" and resumed:
    sys.exit(1)  # a resumed session dies without writing any event
Path(os.environ["FAKE_LOG"]).write_text(json.dumps({{
    "argv": argv, "prompt": prompt, "cwd_listing": os.listdir("."), "home": str(home),
    "auth_is_symlink": (home / ".grok" / "auth.json").is_symlink(),
    "claude_skills": os.environ.get("GROK_CLAUDE_SKILLS_ENABLED")}}))
print(json.dumps({{"type": "available_commands", "tools": [], "commands": ["shiploop", "improve"]}}))
print(json.dumps({{"type": "tool_call", "toolName": "run_terminal_command", "rawInput": {{"command": "shiploop next"}}}}))
for chunk in ("Ship", "ped."):
    print(json.dumps({{"type": "text", "data": chunk}}))
leak_a_listener()
mode = os.environ.get("FAKE_MODE")
if mode == "done" or (mode == "resume" and resumed):
    import shutil
    shutil.rmtree(".shiploop", ignore_errors=True)  # a resumed session finishes the same run
    product()
elif mode == "early" and not resumed:
    pass  # the first session ends before ShipLoop writes any state
elif mode == "early":
    product()
elif mode in ("hang", "hang-active") or (mode == "hang-resumed" and resumed):
    if mode == "hang-active":
        Path(".shiploop").mkdir(exist_ok=True)
        store.write_record(Path(".shiploop/state.md"), {{"status": "active", "stage": "test-refine", "revision": 25}})
    print(json.dumps({{"type": "session", "sessionId": "sess-1"}}), flush=True)
    import time
    time.sleep(600)  # killed by --timeout or by a requested stop
elif mode in ("resume", "stuck", "stuck-stop", "hang-resumed", "anon", "crash-resumed"):
    Path(".shiploop").mkdir(exist_ok=True)
    store.write_record(Path(".shiploop/state.md"), {{"status": "active", "stage": "test-refine", "revision": 25}})
    if mode == "stuck-stop":
        (Path.cwd().parent / "stop").write_text("")  # a person asks for a stop as this session ends
end = {{"type": "end", "stopReason": "cancelled", "sessionId": "sess-1", "num_turns": 4, "total_cost_usd": 0.01}}
if mode == "anon":
    del end["sessionId"]  # the host never named its session: there is nothing to resume
print(json.dumps(end))
"""


# A fake Codex CLI: plugin marketplace add / plugin add / plugin list --json, and
# `exec --json ... [resume ID] PROMPT` emitting Codex's JSON event stream.
FAKE_CODEX = f"""#!{sys.executable}
import json, os, sys
from pathlib import Path
{PRODUCT}
argv = sys.argv[1:]
home = Path(os.environ["CODEX_HOME"])
state = home / "fake-plugin.json"
if argv[:3] == ["plugin", "marketplace", "add"]:
    state.write_text(json.dumps({{"marketplace": argv[3]}}))
    sys.exit(0)
if argv[:2] == ["plugin", "add"]:
    root = home / "plugins" / "cache" / "whichguy" / "skill-craft" / "9.9.9"
    (root / "skills" / "shiploop" / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "skills" / "shiploop" / "scripts" / "shiploop").write_text("")
    sys.exit(0)
if argv[:2] == ["plugin", "list"]:
    rows = [{{"pluginId": "skill-craft@whichguy", "name": "skill-craft", "version": "9.9.9",
             "installed": True}}] if state.exists() else []
    print(json.dumps({{"installed": rows}}))
    sys.exit(0)
assert argv[:2] == ["exec", "--json"], argv
os.chdir(argv[argv.index("-C") + 1])
resumed = argv[argv.index("resume") + 1] if "resume" in argv else None
prompt = argv[-1]
Path(os.environ["FAKE_LOG"]).write_text(json.dumps({{"argv": argv, "prompt": prompt, "resumed": resumed,
    "cwd_listing": os.listdir("."), "codex_home": str(home),
    "auth_is_symlink": (home / "auth.json").is_symlink()}}))
def emit(event):
    print(json.dumps(event), flush=True)
emit({{"type": "thread.started", "thread_id": resumed or "codex-thread-1"}})
cli = "python3 /x/skills/shiploop/scripts/shiploop next"
emit({{"type": "item.completed", "item": {{"id": "item_0", "type": "command_execution", "command": cli,
      "aggregated_output": "ShipLoop navigator\\n", "exit_code": 0, "status": "completed"}}}})
if os.environ.get("FAKE_MODE") == "done":
    import shutil
    shutil.rmtree(".shiploop", ignore_errors=True)  # a resumed session finishes the same run
    product()
emit({{"type": "item.completed", "item": {{"id": "item_1", "type": "agent_message", "text": "Shipped."}}}})
if os.environ.get("FAKE_ROLLOUT"):
    # Codex writes per-call usage only to its rollout files under CODEX_HOME, never to the event stream.
    import time
    rollout = home / "sessions" / "2026" / "10" / "04" / "rollout-fake.jsonl"
    rollout.parent.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + ".000Z"
    rollout.write_text("".join(json.dumps({{"timestamp": stamp, "type": "token_usage_record", "payload": {{
        "thread_id": "t", "session_id": "t", "response_id": "r%d" % n,
        "usage": {{"total_tokens": 1000 * (n + 1)}}}}}}) + "\\n" for n in range(2)))
emit({{"type": "turn.completed", "usage": {{"input_tokens": 10, "cached_input_tokens": 5, "output_tokens": 2}}}})
"""

class HarnessCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.fakes = {}
        for name, body in (("claude", FAKE_CLAUDE), ("grok", FAKE_GROK), ("codex", FAKE_CODEX)):
            path = self.tmp / name
            path.write_text(body)
            path.chmod(path.stat().st_mode | stat.S_IXUSR)
            self.fakes[name] = path
        self.plugin = self.tmp / "build" / "plugins" / "skill-craft"
        (self.plugin / ".claude-plugin").mkdir(parents=True)
        (self.plugin / ".claude-plugin" / "plugin.json").write_text("{}")
        # The CLI file a resume prompt names (run.shiploop_cli): a plugin build always carries one.
        self.cli = self.plugin / "skills" / "shiploop" / "scripts" / "shiploop"
        self.cli.parent.mkdir(parents=True)
        self.cli.write_text("")
        self.log = self.tmp / "fake-log.json"
        self.baselines = self.tmp / "baselines.jsonl"  # never the committed file
        os.environ["FAKE_LOG"] = str(self.log)
        self.addCleanup(os.environ.pop, "FAKE_MODE", None)
        auth = self.tmp / "auth.json"
        auth.write_text("{}")
        saved, hosts.GROK_AUTH = hosts.GROK_AUTH, auth
        self.addCleanup(setattr, hosts, "GROK_AUTH", saved)
        codex_home = self.tmp / "real-codex"
        codex_home.mkdir()
        (codex_home / "auth.json").write_text("{}")
        patched = mock.patch.dict(os.environ, {"CODEX_HOME": str(codex_home)})
        patched.start()
        self.addCleanup(patched.stop)
        # No harness case reads the machine's process table: a listener another session (or a leaked server) holds
        # must not change a verdict here. The classes that exercise the real lsof scope what they see to their own folder.
        patch = nothing_listens()
        patch.__enter__()
        self.addCleanup(patch.__exit__, None, None, None)

    def invoke(self, host: str, mode: str, *extra: str) -> tuple[int, dict]:
        os.environ["FAKE_MODE"] = mode
        out = self.tmp / f"out-{host}-{mode}"
        with contextlib.redirect_stdout(io.StringIO()):
            code = run.main(["--host", host, f"--{host}-bin", str(self.fakes[host]), "--output", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), *extra])
        return code, json.loads((out / "result.json").read_text())

    def seen(self) -> dict:
        return json.loads(self.log.read_text())


class GrokRunTest(HarnessCase):
    def test_claude_sonnet_5_5_is_the_default_host_and_grok_stays_at_medium_effort(self):
        self.assertEqual(run.parser().parse_args([]).host, "claude")
        self.assertEqual(hosts.HOST_DEFAULTS["claude"]["model"], "claude-sonnet-5-5")
        self.assertEqual(hosts.HOST_DEFAULTS["grok"]["effort"], "medium")

    def test_done_run_passes_in_an_isolated_profile_from_an_empty_directory(self):
        code, result = self.invoke("grok", "done")
        self.assertEqual(code, 0, result)
        seen = self.seen()
        self.assertEqual(seen["cwd_listing"], [])
        self.assertTrue(seen["prompt"].startswith("/shiploop "), seen["prompt"])
        self.assertTrue(seen["auth_is_symlink"])
        self.assertEqual(seen["claude_skills"], "false")
        self.assertEqual(Path(seen["home"]), Path(result["output"]) / "home")
        argv = seen["argv"]
        self.assertEqual(argv[argv.index("--reasoning-effort") + 1], "medium")
        self.assertEqual(argv[argv.index("--model") + 1], "grok-4.7")
        self.assertTrue(result["plugin"]["pass"], result["plugin"])
        self.assertTrue(result["committed"]["pass"], result["committed"])
        transcript = (Path(result["output"]) / "transcript.md").read_text()
        self.assertIn("tool  run_terminal_command: shiploop next", transcript)
        self.assertIn("say   Shipped.", transcript)

    def test_run_that_does_nothing_fails_the_product_verdicts(self):
        code, result = self.invoke("grok", "nothing")
        self.assertEqual(code, 1)
        self.assertTrue(result["process"]["pass"])
        self.assertTrue(result["invoked"]["pass"])
        self.assertFalse(result["shiploop"]["pass"])
        self.assertFalse(any(check["pass"] for check in result["checks"]))
        self.assertFalse(result["committed"]["pass"])

    def test_missing_grok_sign_in_stops_before_launch(self):
        hosts.GROK_AUTH = self.tmp / "absent.json"
        with self.assertRaises(SystemExit):
            self.invoke("grok", "done")
        self.assertFalse(self.log.exists())


class GrokResumeTest(HarnessCase):
    def sessions(self) -> list[dict]:
        return [json.loads(line) for line in Path(str(self.log) + ".sessions").read_text().splitlines()]

    def test_session_that_ends_with_shiploop_active_is_resumed_until_done(self):
        code, result = self.invoke("grok", "resume")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["process"]["resumes"], 1)
        sessions = self.sessions()
        self.assertEqual([s["resumed"] for s in sessions], [None, "sess-1"])
        self.assertIn(" next --run-dir ", sessions[1]["prompt"])
        self.assertIn("Never end the turn while a ShipLoop command is still running", sessions[1]["prompt"])
        self.assertEqual(result["cli"]["num_turns"], 8)
        self.assertEqual(result["shiploop"]["status"], "done")

    def test_resume_stops_at_the_cap_when_the_run_never_finishes(self):
        code, result = self.invoke("grok", "stuck", "--max-resumes", "2")
        self.assertEqual(code, 1)
        self.assertEqual(result["process"]["resumes"], 2)
        self.assertEqual(len(self.sessions()), 3)
        self.assertEqual(result["shiploop"]["status"], "active")

    def test_session_that_ends_before_the_run_starts_is_resumed(self):
        code, result = self.invoke("grok", "early")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["process"]["resumes"], 1)
        self.assertIn("ended before the ShipLoop run was started", self.sessions()[1]["prompt"])

    def test_no_resume_when_the_run_is_done(self):
        code, result = self.invoke("grok", "done")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["process"]["resumes"], 0)

    def test_keepalive_decisions_are_counted_from_the_isolated_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self.assertEqual(hosts.keepalive_decisions(home), {})
            log = home / ".local" / "state" / "shiploop" / "keepalive" / "decisions.log"
            log.parent.mkdir(parents=True)
            log.write_text('{"decision": "allow"}\n{"decision": "continue"}\n{"decision": "continue"}\n')
            self.assertEqual(hosts.keepalive_decisions(home), {"allow": 1, "continue": 2})


class VersionGateTest(unittest.TestCase):
    RELEASED = {"origin_main": "a" * 40, "local_head": "a" * 40, "catalog_version": "1.4.0",
                "shiploop_version": "0.37.0"}

    def test_marketplace_is_the_default_source_and_a_plugin_dir_means_checkout(self):
        self.assertEqual(run.parser().parse_args([]).source, "marketplace")

    def test_gate_passes_only_when_head_catalog_and_installed_versions_agree(self):
        self.assertEqual(run.version_gate(self.RELEASED, "1.4.0", "0.37.0"), [])
        behind = dict(self.RELEASED, local_head="b" * 40)
        self.assertIn("has commits origin/main", " ".join(run.version_gate(behind, "1.4.0", "0.37.0")))
        # A checkout merely behind main runs: the plugin comes from the marketplace, not the checkout.
        self.assertEqual(run.version_gate(dict(behind, local_behind_main=True), "1.4.0", "0.37.0"), [])
        self.assertIn("installed skill-craft 1.3.0", " ".join(run.version_gate(self.RELEASED, "1.3.0", "0.37.0")))
        self.assertIn("installed ShipLoop 0.36.0", " ".join(run.version_gate(self.RELEASED, "1.4.0", "0.36.0")))
        self.assertIn("CI failed", " ".join(run.version_gate(dict(self.RELEASED, ci="failure"), "1.4.0", "0.37.0")))
        for ci in ("pending", "unknown"):  # optimistic: proceed, cancel if CI then fails
            self.assertEqual(run.version_gate(dict(self.RELEASED, ci=ci), "1.4.0", "0.37.0"), [])
        pending = dict(self.RELEASED, unreleased=["changes/shiploop/fix.md"])
        self.assertIn("unreleased changes (changes/shiploop/fix.md)", " ".join(run.version_gate(pending, "1.4.0", "0.37.0")))

    def test_card_version_reads_only_the_front_matter(self):
        with tempfile.TemporaryDirectory() as tmp:
            card = Path(tmp) / "SKILL.md"
            card.write_text("---\nname: shiploop\nversion: 0.37.0\n---\nversion: 9.9.9 in the body\n")
            self.assertEqual(run.card_version(card), "0.37.0")
            self.assertIsNone(run.card_version(Path(tmp) / "missing.md"))


class ClaudeResumePromptTest(unittest.TestCase):
    def test_a_claude_resume_names_the_run_s_own_marketplace_cli(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            plugin = out / "marketplace/plugins/skill-craft"
            cli = run.shiploop_cli(plugin)
            self.assertEqual(cli, plugin / "skills/shiploop/scripts/shiploop")
            prompt = run.resume_prompt("/r/run", cli)
            self.assertIn(f'python3 "{cli}" next --run-dir "/r/run"', prompt)
            self.assertNotIn("`shiploop next", prompt)

    def test_a_resume_names_the_cli_it_is_given_for_any_build_and_has_no_bare_command(self):
        # A checkout build (v1220 and v1230 Sonnet) keeps its CLI under <output>/build, not <output>/marketplace.
        cli = run.shiploop_cli(Path("/out/build/plugins/skill-craft"))
        prompt = run.resume_prompt("/r/run", cli)
        self.assertIn('python3 "/out/build/plugins/skill-craft/skills/shiploop/scripts/shiploop" next --run-dir "/r/run"',
                      prompt)
        self.assertNotIn("`shiploop next", prompt)

    def test_a_resume_before_any_run_exists_names_no_command(self):
        prompt = run.resume_prompt(None, Path("/p/cli"))
        self.assertIn("ended before the ShipLoop run was started", prompt)
        self.assertNotIn("next --run-dir", prompt)


class ImproveReviewsMetricTest(unittest.TestCase):
    def test_counts_review_passes_per_child_and_the_time_they_span(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp) / "run"
            run_dir.mkdir()
            one = Path(temp) / "worktree" / ".shiploop-improve" / "nav-a" / "nav-1" / "reviews"
            two = Path(temp) / "worktree" / ".shiploop-improve" / "nav-a" / "nav-2" / "reviews"
            for reviews, count in ((one, 3), (two, 1)):
                reviews.mkdir(parents=True)
                for n in range(1, count + 1):
                    note = reviews / f"review-{n}.md"
                    note.write_text("x" * 10)
                    os.utime(note, (1000 + 60 * n, 1000 + 60 * n))
            got = metrics.improve_reviews(run_dir)
            self.assertEqual((got["children"], got["passes"], got["max_passes"]), (2, 4, 3))
            self.assertEqual([(c["passes"], c["seconds"], c["bytes"]) for c in got["per_child"]],
                             [(3, 120.0, 30), (1, 0.0, 10)])

    def test_no_worktree_means_no_children(self):
        self.assertEqual(metrics.improve_reviews(None)["passes"], 0)
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(metrics.improve_reviews(Path(temp) / "run")["children"], 0)


class ClaudeResumeInvokedTest(unittest.TestCase):
    def events(self, command):
        return [{"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": command}}]}}]

    def graded(self, events):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "events.jsonl"
            path.write_text("".join(json.dumps(e) + "\n" for e in events))
            return run.shiploop_cli_ran(path)

    def test_a_claude_tool_use_that_runs_the_shiploop_cli_counts_even_through_a_path_variable(self):
        self.assertTrue(self.graded(self.events('"/p/skills/shiploop/scripts/shiploop" next --run-dir=/r')))
        self.assertTrue(self.graded(self.events(
            'SKILL_ROOT="/p/skills/shiploop"; CLI="$SKILL_ROOT/scripts/shiploop"; "$CLI" next --run-dir=/r')))

    def test_other_claude_commands_do_not_count(self):
        self.assertFalse(self.graded(self.events("ls -la /p/skills")))
        self.assertFalse(self.graded([]))


class ClaudeRunTest(HarnessCase):
    def test_done_run_invokes_the_namespaced_skill_with_isolated_settings(self):
        code, result = self.invoke("claude", "done")
        self.assertEqual(code, 0, result)
        argv = self.seen()["argv"]
        prompt = json.loads(run.CASES.read_text())["hello"]["prompt"]
        self.assertEqual(argv[:2], ["-p", "/skill-craft:shiploop " + prompt])
        self.assertEqual(argv[argv.index("--model") + 1], "claude-sonnet-5-5")
        self.assertEqual(argv[argv.index("--setting-sources") + 1], "project,local")
        self.assertIn("--strict-mcp-config", argv)  # no account connector (claude.ai MCP server) loads into the run
        self.assertEqual(argv[argv.index("--plugin-dir") + 1], str(self.plugin.resolve()))

    def test_unregistered_skill_command_fails_even_when_the_product_is_right(self):
        code, result = self.invoke("claude", "no-skill")
        self.assertEqual(code, 1)
        self.assertFalse(result["invoked"]["pass"])
        self.assertTrue(result["shiploop"]["pass"])

    def test_custom_prompt_uses_only_its_own_checks(self):
        code, result = self.invoke("claude", "done", "--prompt", "do a thing", "--check", "test -f hello.py")
        self.assertEqual(code, 0, result)
        self.assertEqual([c["command"] for c in result["checks"]], ["test -f hello.py"])
        self.assertEqual(self.seen()["argv"][1], "/skill-craft:shiploop do a thing")

    def test_existing_output_directory_is_refused(self):
        (self.tmp / "out-claude-done").mkdir()
        with self.assertRaises(FileExistsError):
            self.invoke("claude", "done")

    def test_output_inside_the_checkout_is_refused(self):
        with self.assertRaises(SystemExit):
            run.new_output_dir(ROOT / "test" / "never-created", "hello")
        self.assertFalse((ROOT / "test" / "never-created").exists())


class SeedTest(HarnessCase):
    """--seed-at: the host starts at step-plan of a real Ask-Agent run; the chain is graded from files."""
    CLI = ROOT / "skills" / "shiploop" / "scripts" / "shiploop"

    def test_seed_reaches_step_plan_on_an_ask_agent_run_the_cli_reads_back(self):
        work = self.tmp / "work"
        work.mkdir()
        seeded = run.seed_run(self.CLI, work, self.tmp, "Build convert.py and stats.py", "step-plan")
        self.assertEqual((seeded["stage"], seeded["delegation"]), ("step-plan", "ask-agent"))
        self.assertEqual(seeded["skipped"][0], "intake")
        self.assertNotIn("step-plan", seeded["skipped"])
        packet = subprocess.run([sys.executable, str(self.CLI), "next", "--run-dir", seeded["run_dir"]],
                                capture_output=True, text=True)
        self.assertEqual(packet.returncode, 0, packet.stderr)
        self.assertTrue(packet.stdout.startswith("ShipLoop navigator | step-plan |"), packet.stdout[:200])

    def test_seeded_run_opens_at_the_run_and_writes_no_baseline(self):
        shutil.rmtree(self.plugin / "skills")  # the real skills, and so the real CLI, replace the fixture's stub
        (self.plugin / "skills").symlink_to(ROOT / "skills")
        code, result = self.invoke("claude", "nothing", "--seed-at", "step-plan")
        self.assertEqual(code, 1, result)
        prompt = self.seen()["argv"][1]
        self.assertIn(f'next --run-dir "{result["seeded"]["run_dir"]}"', prompt)
        self.assertIn("stages before step-plan without doing them", prompt)
        self.assertEqual(result["committed"]["start_head"], result["seeded"]["start_head"])
        self.assertEqual((result["chain"]["pass"], result["chain"]["bindings"]), (False, []))
        self.assertFalse(self.baselines.exists())

    def chain(self, events: list[tuple[str, str]], status: dict[str, str], deps: dict[str, list[str]] | None = None,
              expect: dict | None = None) -> dict:
        """A binding whose ledger holds `events` as (kind, step); contributions name their step."""
        import shiploop_chain_ledger as ledger
        out = self.tmp / "out"
        chain_dir = out / ".shiploop-runs" / "seed" / "run" / "chains" / "nav-1"
        dispatcher = chain_dir / "child"
        dispatcher.mkdir(parents=True)
        run.store.write_record(chain_dir / "binding.md", {"dispatcher_run": str(dispatcher), "mode": "parallel"})
        deps = deps or {step: [] for step in status}
        (dispatcher / "plan-dispatcher-state.json").write_text(json.dumps({
            "graph": {"steps": [{"id": step, "deps": needs} for step, needs in deps.items()]},
            "steps": {step: {"status": s} for step, s in status.items()},
            "attempts": {f"{step}-1": {"step": step, "handle": f"h-{step}"} for step in status}}))
        for number, (kind, step) in enumerate(events):
            data = {"attempt": f"{step}-1", **({"step": step} if kind == "contribution_recorded" else {})}
            ledger.append_event(str(chain_dir / "events"), f"e{number}", kind, data)
        return run.chain_facts(out, expect)

    @staticmethod
    def worked(*steps: str) -> list[tuple[str, str]]:
        """Launch every step together, then import and integrate each."""
        return ([("launched_result", s) for s in steps] + [("handoff_import_result", s) for s in steps]
                + [("contribution_recorded", s) for s in steps])

    def test_chain_passes_when_all_accepted_in_order_once_and_two_ran_together(self):
        events = self.worked("A", "B") + self.worked("J")
        facts = self.chain(events, {"A": "accepted", "B": "accepted", "J": "accepted"},
                           {"A": [], "B": [], "J": ["A", "B"]})
        self.assertTrue(facts["pass"], facts)
        binding = facts["bindings"][0]
        self.assertEqual((binding["max_in_flight"], binding["depth"], binding["native_attempts"]), (2, 2, 3))

    def test_serial_chain_fails(self):
        facts = self.chain(self.worked("A") + self.worked("B"), {"A": "accepted", "B": "accepted"})
        self.assertFalse(facts["pass"])
        self.assertEqual(facts["bindings"][0]["max_in_flight"], 1)

    def test_unaccepted_step_fails_even_after_fan_out(self):
        facts = self.chain(self.worked("A", "B"), {"A": "accepted", "B": "running"})
        self.assertFalse(facts["pass"])

    def test_a_step_launched_before_its_dependency_was_integrated_fails(self):
        events = [("launched_result", "A"), ("launched_result", "B"), ("launched_result", "J"),
                  ("handoff_import_result", "A"), ("handoff_import_result", "B"), ("handoff_import_result", "J"),
                  ("contribution_recorded", "A"), ("contribution_recorded", "B"), ("contribution_recorded", "J")]
        facts = self.chain(events, {"A": "accepted", "B": "accepted", "J": "accepted"},
                           {"A": [], "B": [], "J": ["A", "B"]})
        self.assertFalse(facts["pass"])
        self.assertEqual(facts["bindings"][0]["out_of_order"], ["J"])

    def test_a_step_integrated_twice_or_never_fails(self):
        twice = self.chain(self.worked("A", "B") + [("contribution_recorded", "A")],
                           {"A": "accepted", "B": "accepted"})
        self.assertEqual(twice["bindings"][0]["integrated_twice"], ["A"])
        self.assertFalse(twice["pass"])

    def test_case_expectations_raise_the_bar(self):
        events = self.worked("A", "B") + self.worked("J")
        status = {"A": "accepted", "B": "accepted", "J": "accepted"}
        facts = self.chain(events, status, {"A": [], "B": [], "J": ["A", "B"]},
                           expect={"min_steps": 3, "min_in_flight": 3, "min_depth": 2})
        self.assertFalse(facts["pass"])  # only two ran together
        self.assertEqual(facts["expect"]["min_in_flight"], 3)

    def test_a_retried_worker_stops_counting_as_in_flight(self):
        # Kill-and-resume: A-1 and B-1 are lost (never imported) and retried; their
        # replacements then run one after the other. Only one worker ever really ran
        # after the kill, so the lost attempts must not inflate the count.
        import shiploop_chain_ledger as ledger
        out = self.tmp / "out"
        chain_dir = out / ".shiploop-runs" / "seed" / "run" / "chains" / "nav-1"
        dispatcher = chain_dir / "child"
        dispatcher.mkdir(parents=True)
        run.store.write_record(chain_dir / "binding.md", {"dispatcher_run": str(dispatcher), "mode": "parallel"})
        attempts = {"A-1": "A", "B-1": "B", "A-2": "A", "B-2": "B"}
        (dispatcher / "plan-dispatcher-state.json").write_text(json.dumps({
            "graph": {"steps": [{"id": "A", "deps": []}, {"id": "B", "deps": []}]},
            "steps": {"A": {"status": "accepted"}, "B": {"status": "accepted"}},
            "attempts": {a: {"step": s, "handle": "h"} for a, s in attempts.items()}}))
        events = [("launched_result", "A-1"), ("launched_result", "B-1"), ("retry_result", "A-1"),
                  ("retry_result", "B-1"), ("launched_result", "A-2"), ("handoff_import_result", "A-2"),
                  ("contribution_recorded", "A-2"), ("launched_result", "B-2"), ("handoff_import_result", "B-2"),
                  ("contribution_recorded", "B-2")]
        for number, (kind, attempt) in enumerate(events):
            data = {"attempt": attempt, **({"step": attempts[attempt]} if kind == "contribution_recorded" else {})}
            ledger.append_event(str(chain_dir / "events"), f"e{number}", kind, data)
        facts = run.chain_facts(out)
        self.assertEqual(facts["bindings"][0]["max_in_flight"], 2)  # A-1 and B-1 before the kill
        self.assertEqual(facts["bindings"][0]["max_in_flight_after_retry"], 1)

    def test_chain_in_flight_is_true_only_between_launch_and_import(self):
        self.chain([("launched_result", "A")], {"A": "running"})
        self.assertTrue(run.chain_in_flight(self.tmp / "out"))
        shutil.rmtree(self.tmp / "out")
        self.chain(self.worked("A"), {"A": "accepted"})
        self.assertFalse(run.chain_in_flight(self.tmp / "out"))

    def test_launch_kills_the_session_when_its_stop_condition_holds(self):
        out = self.tmp / "out-stop"
        (out / "work").mkdir(parents=True)
        result = run.launch([sys.executable, "-c", "import time; time.sleep(60)"], out / "work", out, dict(os.environ),
                            120, watch=False, stop_when=lambda: True)
        self.assertEqual(result["status"], "interrupted")
        self.assertLess(result["elapsed_seconds"], 20)

    def test_launch_returns_when_the_host_exits_instead_of_sleeping_out_the_poll_tick(self):
        # The poll loop used to time.sleep(2) between checks, so a session that ended after 0.4 s still held the
        # caller for the whole tick: about 290 s of the 322 s this file took, with fake hosts that exit at once.
        out = self.tmp / "out-exit"
        (out / "work").mkdir(parents=True)
        result = run.launch([sys.executable, "-c", "import time; time.sleep(0.4)"], out / "work", out, dict(os.environ),
                            120, watch=False)
        self.assertEqual(result["status"], "exited")
        self.assertLess(result["elapsed_seconds"], 1.5, result)

    def test_launch_still_enforces_its_deadline_while_the_host_keeps_running(self):
        out = self.tmp / "out-deadline"
        (out / "work").mkdir(parents=True)
        result = run.launch([sys.executable, "-c", "import time; time.sleep(60)"], out / "work", out, dict(os.environ),
                            1, watch=False)
        self.assertEqual(result["status"], "timeout")
        self.assertLess(result["elapsed_seconds"], 10, result)

    def test_launch_polls_its_stop_condition_while_the_host_keeps_running(self):
        out = self.tmp / "out-poll"
        (out / "work").mkdir(parents=True)
        polls = []

        def stop_when():
            polls.append(1)
            return len(polls) >= 2  # false once, then true: the loop must come back for a second look

        result = run.launch([sys.executable, "-c", "import time; time.sleep(60)"], out / "work", out, dict(os.environ),
                            120, watch=False, stop_when=stop_when)
        self.assertEqual(result["status"], "interrupted")
        self.assertEqual(len(polls), 2)
        self.assertLess(result["elapsed_seconds"], 10, result)

    def test_interrupt_kills_the_host_mid_chain_and_a_fresh_session_finishes(self):
        code, result = self.invoke("claude", "chain-hang", "--interrupt-at", "chain-launched")
        self.assertEqual(code, 0, {k: result.get(k) for k in ("process", "chain", "recovery", "shiploop")})
        sessions = result["process"]["sessions"]
        self.assertEqual([s["status"] for s in sessions], ["interrupted", "exited"])
        # The killed session began and never reported: the cost is a lower bound by one session.
        self.assertEqual(result["metrics"]["unreported_sessions"], 1)
        self.assertTrue(result["recovery"]["pass"], result["recovery"])
        self.assertEqual(result["recovery"]["interrupt"]["at"], "chain-launched")
        self.assertIn("This session ended", (Path(result["output"]) / "resume-after-interrupt.txt").read_text()
                      if (Path(result["output"]) / "resume-after-interrupt.txt").exists() else self.seen()["argv"][1])

    def test_without_interrupt_no_recovery_verdict(self):
        code, result = self.invoke("claude", "done")
        self.assertIsNone(result["recovery"])


class ExpectationTest(HarnessCase):
    """Every expectation names its source; a failing run gets a filled mismatch record."""

    def test_every_case_names_the_source_of_its_expectations(self):
        cases = json.loads(run.CASES.read_text())
        for name, case in cases.items():
            self.assertTrue(case.get("checks_source"), name)
            for block in ("chain", "budget"):
                if block in case:
                    self.assertTrue(case[block].get("source"), f"{name}.{block}")
            if "retention" in case:
                self.assertTrue(case.get("retention_source"), name)

    def test_a_failing_run_records_expected_beside_observed_in_mismatch_md(self):
        code, result = self.invoke("claude", "nothing")
        self.assertEqual(code, 1)
        self.assertEqual(result["expectations"]["checks"], json.loads(run.CASES.read_text())["hello"]["checks_source"])
        mismatch = (Path(result["output"]) / "mismatch.md").read_text()
        for section in ("## Expected", "## Observed", "## Triage", "## Decision", "## Verified by"):
            self.assertIn(section, mismatch)
        self.assertIn("**shiploop**: ShipLoop reaches done", mismatch)
        self.assertIn("(source: the request", mismatch)
        self.assertRegex(mismatch, r"\*\*check\*\*: exit [0-9]+(: .+)?\n")  # the failing check's exit and last output line

    def test_a_passing_run_writes_no_mismatch(self):
        code, result = self.invoke("claude", "done")
        self.assertEqual(code, 0, result)
        self.assertFalse((Path(result["output"]) / "mismatch.md").exists())

    def test_budget_is_should_level_and_read_from_the_run_timeline(self):
        run_dir = self.tmp / "run"
        run_dir.mkdir()
        (run_dir / "timeline.json").write_text(json.dumps({
            "started": "2026-10-03T10:00:00Z",
            "accepted": {"a": "2026-10-03T10:05:00Z", "b": "2026-10-03T10:21:30Z"}}))
        budget = {"seeded_minutes": 30, "source": "one session"}
        met = run.budget_facts(budget, True, str(run_dir))
        self.assertEqual((met["level"], met["observed_minutes"], met["pass"]), ("should", 21.5, True))
        over = run.budget_facts({"seeded_minutes": 20, "source": "x"}, True, str(run_dir))
        self.assertFalse(over["pass"])
        self.assertIsNone(run.budget_facts(budget, False, str(run_dir)))  # only seeded runs carry a budget
        interrupted = run.budget_facts(budget, True, str(run_dir), interrupted=True)
        self.assertEqual((interrupted["applies"], interrupted["pass"], interrupted["observed_minutes"]), (False, None, 21.5))


class ReviewParsingTest(unittest.TestCase):
    def test_actionable_keeps_only_material_premise_preserving_findings(self):
        verdict = {
            "learnings": [{"title": "a", "severity": "material", "preserves_premise": True},
                          {"title": "b", "severity": "minor", "preserves_premise": True}],
            "optimizations": [{"title": "c", "severity": "material", "preserves_premise": False}],
            "missing_considerations": [{"title": "d", "severity": "material", "preserves_premise": True}],
        }
        self.assertEqual([(f["title"], f["category"]) for f in review.actionable(verdict)],
                         [("a", "learnings"), ("d", "missing_considerations")])

    def test_last_json_object_prefers_the_final_fenced_block(self):
        text = 'Notes {"x": 1}\n```json\n{"outcome": "old"}\n```\nthen\n```json\n{"outcome": "new"}\n```'
        self.assertEqual(hosts.last_json_object(text), {"outcome": "new"})
        self.assertEqual(hosts.last_json_object('prefix {"a": {"b": 2}} tail'), {"a": {"b": 2}})
        self.assertIsNone(hosts.last_json_object("no json here"))

    def test_final_text_is_grok_text_after_its_last_tool_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            events = Path(tmp) / "events.jsonl"
            events.write_text("\n".join(json.dumps(e) for e in (
                {"type": "text", "data": "thinking aloud"},
                {"type": "tool_call", "toolName": "read_file", "rawInput": {}},
                {"type": "text", "data": "final "}, {"type": "text", "data": "answer"})))
            self.assertEqual(hosts.final_text(events), "final answer")

    def test_reviewer_prompt_states_the_premise_and_the_three_questions(self):
        prompt = review.reviewer_prompt(Path("/tmp/run"), Path("/tmp/skill"))
        # The standing spec is the premise, loaded from the one file, with clause IDs to cite.
        self.assertIn("**S-1 Scripts own the graph and the state.**", prompt)
        self.assertIn("**S-7 Packets are small where they are printed", prompt)
        self.assertIn("Cite its clause IDs", prompt)
        for key in review.CATEGORIES:
            self.assertIn(key, prompt)
        for key in review.HARNESS_QUESTIONS:
            self.assertIn(key, prompt)
        rendered = review.render_markdown({"harness": {"learning_retention": {"answer": "Keep it", "proposals": ["p1"]}}})
        self.assertIn("**Learning retention:** Keep it", rendered)
        self.assertIn("**Evaluation criteria:** not answered", rendered)


class LearningsTest(unittest.TestCase):
    RESULT = {"host": "grok", "model": "grok-4.7", "effort": "medium", "pass": False,
              "process": {"status": "failed", "returncode": 1, "elapsed_seconds": 12.5},
              "shiploop": {"status": "active", "stage": "regression", "report_html": False,
                           "worktree_checks": [{"command": "node --test", "pass": True}]},
              "checks": [{"command": "node --test", "pass": False}],
              "cli": {"num_turns": 150, "cost_usd": 10.88,
                      "truncated_outputs": [{"total_bytes": 36000, "shown_chars": 20467, "call": "x"}]}}
    VERDICT = {"outcome": "Capped before return.",
               "learnings": [{"title": "Return earlier", "evidence": "work/ empty", "proposal": "p",
                              "files": ["skills/shiploop/SKILL.md"], "severity": "material",
                              "preserves_premise": True, "premise_note": "script decides"}],
               "optimizations": [{"title": "Let the model pick stages", "severity": "material",
                                  "preserves_premise": False}],
               "harness": {"further_learning": {"answer": "Compare stage costs", "proposals": ["track per stage"]}}}

    def message(self) -> str:
        verdict = dict(self.VERDICT, actionable=review.actionable(self.VERDICT))
        args = iterate.argparse.Namespace(case="battleship")
        return iterate.learnings_message(2, args, "0123456789ab", self.RESULT, verdict, ["aaa1111", "bbb2222"])

    def test_message_details_outcome_findings_and_prior_learnings(self):
        message = self.message()
        self.assertTrue(message.startswith(
            "test(shiploop): record E2E iteration 2 learnings (battleship, grok medium)\n\n"))
        for text in ("150 turns", "stage regression", "unreturned product in ShipLoop's worktree: 1/1",
                     "host truncated 1 tool outputs", "Evidence: work/ empty", "breaks premise: rejected",
                     "- apply: Return earlier", "Built on the learnings of aaa1111, bbb2222.",
                     "- further learning: Compare stage costs", "  proposal: track per stage",
                     "- evaluation criteria: not answered"):
            self.assertIn(text, message)
        self.assertTrue(message.rstrip().endswith("<shiploop-e2e@example.invalid>"))

    def test_a_cost_the_host_did_not_report_is_not_printed_as_a_dollar_figure(self):
        args = iterate.argparse.Namespace(case="battleship")
        verdict = dict(self.VERDICT, actionable=review.actionable(self.VERDICT))
        message = iterate.learnings_message(2, args, "0123456789ab", dict(self.RESULT, cli={"num_turns": 2189,
                                                                                            "cost_usd": None}),
                                            verdict, [])
        self.assertIn("2189 turns, cost not reported", message)
        self.assertNotIn("$None", message)
        self.assertIn("150 turns, cost $10.88", self.message())

    def test_record_learnings_appends_and_commits_only_the_journal(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            (repo / "test" / "shiploop_e2e").mkdir(parents=True)
            (repo / "test" / "shiploop_e2e" / "LEARNINGS.md").write_text("# ShipLoop E2E learnings\n")
            (repo / "untracked.txt").write_text("stay out")
            for cmd in (["init", "-q", "-b", "main"], ["config", "user.name", "t"],
                        ["config", "user.email", "t@example.invalid"], ["add", "test"],
                        ["commit", "-q", "-m", "base"]):
                subprocess.run(["git", "-C", str(repo), *cmd], check=True)
            stage = Path(tmp) / "stage"
            stage.mkdir()
            iterate.record_learnings(repo, self.message(), stage)
            journal = (repo / "test" / "shiploop_e2e" / "LEARNINGS.md").read_text()
            self.assertIn("## E2E iteration 2 learnings (battleship, grok medium)", journal)
            self.assertNotIn("Co-Authored-By", journal)
            files = subprocess.run(["git", "-C", str(repo), "show", "--name-only", "--format=", "HEAD"],
                                   capture_output=True, text=True, check=True).stdout.split()
            self.assertEqual(files, ["test/shiploop_e2e/LEARNINGS.md"])
            body = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%B"],
                                  capture_output=True, text=True, check=True).stdout
            self.assertIn("Built on the learnings of aaa1111, bbb2222.", body)

    def test_record_learnings_commits_the_run_review_export_in_the_same_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            (repo / "test" / "shiploop_e2e").mkdir(parents=True)
            (repo / "test" / "shiploop_e2e" / "LEARNINGS.md").write_text("# ShipLoop E2E learnings\n")
            for cmd in (["init", "-q", "-b", "main"], ["config", "user.name", "t"],
                        ["config", "user.email", "t@example.invalid"], ["add", "test"],
                        ["commit", "-q", "-m", "base"]):
                subprocess.run(["git", "-C", str(repo), *cmd], check=True)
            stage = Path(tmp) / "stage"
            bundle = stage / "run" / "review-export" / "review-export.json"
            bundle.parent.mkdir(parents=True)
            text = json.dumps({"schema": "run-review-export/v2", "docs": {"runs": {"grok-1.0.0-hello-20261004": {}}}})
            bundle.write_text(text)
            iterate.record_learnings(repo, self.message(), stage)
            files = subprocess.run(["git", "-C", str(repo), "show", "--name-only", "--format=", "HEAD"],
                                   capture_output=True, text=True, check=True).stdout.split()
            evidence = "test/shiploop_e2e/evidence/grok-1.0.0-hello-20261004.json"
            self.assertEqual(files, ["test/shiploop_e2e/LEARNINGS.md", evidence])
            self.assertEqual((repo / evidence).read_text(), text)
            bundle.write_text("not json")  # an unreadable export never blocks the learnings commit
            iterate.record_learnings(repo, self.message(), stage)
            files = subprocess.run(["git", "-C", str(repo), "show", "--name-only", "--format=", "HEAD"],
                                   capture_output=True, text=True, check=True).stdout.split()
            self.assertEqual(files, ["test/shiploop_e2e/LEARNINGS.md"])

    def test_reviewer_and_improver_prompts_carry_prior_learnings(self):
        prior = "commit abc1234\nRun 1 learned the graph is fixed.\n"
        self.assertIn("Run 1 learned the graph is fixed.", review.reviewer_prompt(Path("/r"), Path("/s"), prior))
        self.assertNotIn("Learnings recorded", review.reviewer_prompt(Path("/r"), Path("/s")))
        self.assertIn("Run 1 learned the graph is fixed.", iterate.improver_prompt(Path("/w"), [], "base", prior))
        improver = iterate.improver_prompt(Path("/w"), [], "base")
        self.assertIn("adversarial evaluation", improver)
        self.assertIn("mitigated and tested / accepted with the clause that asks for it", improver)
        self.assertIn("**Adversarial evaluation first.**", improver)  # the spec, loaded as the premise


class FastPlanningRecordTest(unittest.TestCase):
    """The fast-planning decision keeps its evidence in the repository and its SPEC carve-out.

    Existence checks only: no prose is pinned. The option's name, default and values are
    pinned against the code constants where those exist (test/shiploop-navigator-contract.test.py).
    """

    EVIDENCE = ROOT / "docs" / "experiments" / "shiploop-fast-planning-20261004"

    def test_the_evidence_the_journal_cites_is_in_the_repository(self):
        journal = (ROOT / "test" / "shiploop_e2e" / "LEARNINGS.md").read_text()
        self.assertIn("docs/experiments/shiploop-fast-planning-20261004/", journal)
        self.assertIn("docs/shiploop-fast-planning-plan-2026-10-04.md", journal)
        for name in ("README.md", "design-final.json", "report-knobs.txt", "report-pass-value-and-cost.txt",
                     "report-planning-prompts.txt", "attack-quality-kiss.json", "attack-engine-correctness.json",
                     "gate_experiment.py", "gate_experiment.out"):
            self.assertTrue((self.EVIDENCE / name).is_file(), name)
        self.assertTrue((ROOT / "docs" / "shiploop-fast-planning-plan-2026-10-04.md").is_file())
        json.loads((self.EVIDENCE / "design-final.json").read_text())

    def test_spec_s10_names_its_carve_outs(self):
        spec = (ROOT / "test" / "shiploop_e2e" / "SPEC.md").read_text()
        s10 = " ".join(spec[spec.index("**S-10 Loops"):spec.index("**S-11")].split())  # the SPEC is hard-wrapped
        self.assertIn("Except for the carve-outs below, there is no iteration cap", s10)
        for heading in ("**S-10 carve-out, owner decision 2026-10-04**", "**S-10 carve-out, owner decision 2026-10-05**"):
            self.assertIn(heading, s10)
        for option in ("--backchain-passes converge", "--backchain-passes none", "backchain_passes",
                       "--planning-review stage", "--planning-review none", "planning_review"):
            self.assertIn(option, s10)

    def test_the_planning_review_evidence_is_in_the_repository(self):
        evidence = ROOT / "docs" / "experiments" / "shiploop-planning-review-20261005"
        journal = (ROOT / "test" / "shiploop_e2e" / "LEARNINGS.md").read_text()
        self.assertIn("docs/experiments/shiploop-planning-review-20261005/", journal)
        self.assertIn("docs/shiploop-planning-review-plan-2026-10-05.md", journal)
        self.assertTrue((ROOT / "docs" / "shiploop-planning-review-plan-2026-10-05.md").is_file())
        for name in ("README.md", "design-draft.json", "design-final.json", "report-engine.txt",
                     "report-consumers.txt", "report-value.txt", "report-rules-and-wording.txt",
                     "attack-measurement-and-text.json", "attack-engine-correctness.json",
                     "sonnet-plan-review-b1e196d.txt", "e6b-excerpt.md", "probe_judge.py", "probe_judge.out",
                     "passes.py", "passes.out"):
            self.assertTrue((evidence / name).is_file(), name)
        for name in ("design-draft.json", "design-final.json", "attack-measurement-and-text.json",
                     "attack-engine-correctness.json"):
            json.loads((evidence / name).read_text())

    def test_the_statements_the_planning_review_supersedes_say_so(self):
        for name in ("shiploop-fast-planning-plan-2026-10-04.md", "shiploop-delivery-overhead-plan-2026-09-23.md"):
            text = " ".join((ROOT / "docs" / name).read_text().split())
            self.assertIn("Superseded 2026-10-05", text, name)
            self.assertIn("docs/shiploop-planning-review-plan-2026-10-05.md", text, name)

    def test_the_planning_time_evidence_is_in_the_repository(self):
        evidence = ROOT / "docs" / "experiments" / "shiploop-planning-time-20261005"
        journal = (ROOT / "test" / "shiploop_e2e" / "LEARNINGS.md").read_text()
        self.assertIn("docs/experiments/shiploop-planning-time-20261005/", journal)
        for name in ("README.md", "ledger-account-final.json", "stage-clock.md", "grok-medium-improve-children.json",
                     "run-doc-luna-xhigh-v1210.json", "run-doc-grok-medium-v1210.json"):
            self.assertTrue((evidence / name).is_file(), name)
        for name in ("ledger-account-final.json", "grok-medium-improve-children.json",
                     "run-doc-luna-xhigh-v1210.json", "run-doc-grok-medium-v1210.json"):
            json.loads((evidence / name).read_text())

    def test_the_doccheck_evidence_and_the_batch_1008_design_audit_are_in_the_repository(self):
        # The DOCCHECK figures were produced by a classifier that was not kept, so this pins presence and shape: the
        # committed output, the audit entries the journal cites, and the dated note that supersedes the ledger's L11.
        journal = (ROOT / "docs" / "shiploop-batch-1008a-journal-2026-10-08.md").read_text()
        audit = ROOT / "docs" / "experiments" / "batch-1008-design-audit-20261008" / "design-audit.json"
        evidence = ROOT / "docs" / "experiments" / "docheck-20261008" / "evidence.json"
        for path in (audit, evidence):
            self.assertIn(str(path.relative_to(ROOT)), journal)
        entries = {row["key"]: row for row in json.loads(audit.read_text())}
        for key in ("DOCCHECK", "REGISTER", "B6", "REVISE"):
            self.assertEqual(sorted(entries[key]), ["audit", "design", "key", "title"], key)
        data = json.loads(evidence.read_text())
        luna = data["luna_xhigh_1210"]
        self.assertEqual(sum(row["scripts"] for row in luna["inline_scripts_by_purpose"]), luna["inline_scripts"])
        for key in ("end_state", "caveats", "superseded_figure"):
            self.assertTrue(data[key], key)
        ledger_readme = ROOT / "docs" / "experiments" / "shiploop-planning-time-20261005" / "README.md"
        self.assertIn("Superseded 2026-10-08: lever L11", ledger_readme.read_text())

    def test_the_ci_audit_evidence_is_in_the_repository(self):
        evidence = ROOT / "docs" / "experiments" / "ci-audit-20261005"
        for name in ("README.md", "ci-audit-final.json", "name-collision-trace.json", "dump_selection.py"):
            self.assertTrue((evidence / name).is_file(), name)
        for name in ("ci-audit-final.json", "name-collision-trace.json"):
            json.loads((evidence / name).read_text())

    def test_the_gate_experiment_output_is_what_the_script_prints(self):
        script = self.EVIDENCE / "gate_experiment.py"
        done = subprocess.run([sys.executable, "-B", str(script)], capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, (self.EVIDENCE / "gate_experiment.out").read_text())


class ReviewExportTest(HarnessCase):
    def run_printed(self, *extra: str) -> tuple[int, dict, str]:
        os.environ["FAKE_MODE"] = "done"
        out, printed = self.tmp / "out-export", io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = run.main(["--host", "claude", "--claude-bin", str(self.fakes["claude"]), "--output", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), *extra])
        return code, json.loads((out / "result.json").read_text()), printed.getvalue()

    def test_an_export_problem_is_printed_and_never_changes_the_verdict(self):
        # The fake run's state has no timeline.json, so the exporter refuses it.
        code, result, printed = self.run_printed()
        self.assertEqual(code, 0, printed)
        self.assertTrue(result["pass"])
        self.assertRegex(printed, r"review export skipped: missing .*timeline\.json")
        raising = self.tmp / "raising.py"
        raising.write_text("def export_run(out):\n    raise RuntimeError('boom')\n")
        with mock.patch.object(run, "REVIEW_EXPORTER", raising):
            shutil.rmtree(self.tmp / "out-export")
            code, result, printed = self.run_printed()
        self.assertEqual((code, result["pass"]), (0, True))
        self.assertIn("review export skipped: boom", printed)

    def test_a_run_with_shiploop_records_is_exported_into_its_output_directory(self):
        out = self.tmp / "graded"
        state_dir = out / ".shiploop-runs" / "work-1" / "run"
        run.store.write_record(state_dir / "state.md", {"status": "done", "stage": "done", "history": [
            {"action": "nav-0123456789abcdef", "stage": "intake", "outcome": "done"}]})
        run.store.write_record(state_dir / "results" / "nav-0123456789abcdef.md",
                           {"action": "nav-0123456789abcdef", "stage": "intake", "result": {"outcome": "done"}})
        (state_dir / "timeline.json").write_text(json.dumps({"started": "2026-10-04T10:00:00Z", "accepted": {
            "nav-0123456789abcdef": "2026-10-04T10:03:00Z"}}))
        (out / "metrics.json").write_text(json.dumps({"shiploop_failures": [], "model_glue": [], "unmeasured": {}}))
        line = run.review_export(out)
        self.assertEqual(line, f"review export: {(out / 'review-export').resolve()}")
        bundle = json.loads((out / "review-export" / "review-export.json").read_text())
        self.assertEqual([s["min"] for s in next(iter(bundle["docs"]["runs"].values()))["stages"]], [3.0])

    def test_preflight_only_never_exports(self):
        with mock.patch.object(run, "marketplace_preflight", return_value=(self.plugin, None, {"gate": []})), \
                mock.patch.object(run, "review_export") as exporter:
            self.assertEqual(run.main(["--preflight-only", "--host", "claude", "--output", str(self.tmp / "pf")]), 0)
        exporter.assert_not_called()


class ReviewAdviseLineTest(unittest.TestCase):
    def test_the_step_after_the_learnings_commit_names_the_advise_mode_and_the_run_directory(self):
        self.assertEqual(iterate.review_line(2, Path("/out/iter-2/run")),
                         "== iteration 2: update the Run Review page: "
                         "/skill-craft:shiploop-run-review advise /out/iter-2/run")


class HostOutputTest(unittest.TestCase):
    def test_visible_output_and_truncations_use_what_the_model_saw(self):
        raw = {"output": [104, 105], "output_for_prompt": "hi", "truncated": True, "total_bytes": 30000}
        self.assertEqual(run.model_visible_output(raw), "hi")
        with tempfile.TemporaryDirectory() as tmp:
            events = Path(tmp) / "events.jsonl"
            events.write_text("\n".join(json.dumps(e) for e in (
                {"type": "tool_call", "toolCallId": "a", "rawInput": {"command": "shiploop next"}},
                {"type": "tool_call_update", "toolCallId": "a", "status": "completed", "rawOutput": raw},
                {"type": "tool_call", "toolCallId": "b", "rawInput": {"command": "ls"}},
                {"type": "tool_call_update", "toolCallId": "b", "rawOutput": {"output_for_prompt": "x",
                                                                              "truncated": False}})))
            self.assertEqual(run.host_truncations(events),
                             [{"total_bytes": 30000, "shown_chars": 2, "call": "shiploop next"}])
            transcript = Path(tmp) / "t.md"
            run.write_transcript(events, transcript)
            self.assertIn("out   completed hi", transcript.read_text())


class FollowOnTest(HarnessCase):
    def prior_run(self) -> Path:
        prior = self.tmp / "prior"
        work = prior / "work"
        work.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(work)], check=True)
        (work / "prior.txt").write_text("kept\n")
        (work / ".git" / "worktrees" / "stale").mkdir(parents=True)
        (prior / "result.json").write_text(json.dumps({"case": "hello", "pass": True,
                                                        "metrics": {"turns": 40, "cost_usd": 2.5}}))
        return prior

    def test_follow_on_starts_in_a_copy_of_the_earlier_checkout(self):
        prior = self.prior_run()
        code, result = self.invoke("grok", "done", "--continue-from", str(prior), "--prompt", "Add a feature.",
                                   "--check", 'test -f "$PRIOR_WORK/prior.txt" && test -f prior.txt')
        self.assertEqual(code, 0, result)
        self.assertIn("prior.txt", self.seen()["cwd_listing"])
        work = Path(result["output"]) / "work"
        self.assertFalse((work / ".git" / "worktrees").exists())
        self.assertTrue((prior / "work" / ".git" / "worktrees" / "stale").is_dir(), "the earlier run is untouched")
        self.assertEqual(result["follow_on"]["prior_case"], "hello")
        self.assertEqual(result["follow_on"]["prior_turns"], 40)
        self.assertEqual(result["follow_on"]["prior_cost_usd"], 2.5)

    def test_follow_on_case_needs_the_run_it_follows(self):
        with self.assertRaises(SystemExit) as raised:
            self.invoke("grok", "done", "--case", "battleship-scoring")
        self.assertIn("--continue-from", str(raised.exception))

    def test_follow_on_case_checks_regression_feature_and_retention(self):
        cases = json.loads(run.CASES.read_text())
        args = run.parser().parse_args(["--case", "battleship-scoring"])
        name, _, checks, follows = run.load_case(args)
        case = cases[name]
        self.assertEqual(follows, "battleship")
        self.assertEqual(checks, cases["battleship"]["checks"] + case["checks"] + case["retention"])
        self.assertTrue(all("PRIOR_WORK" in check for check in case["retention"]))


class SuiteTest(HarnessCase):
    def use_catalog(self, cases: dict, suites: dict) -> None:
        for attr, data in (("CASES", cases), ("SUITES", suites)):
            path = self.tmp / (attr.lower() + ".json")
            path.write_text(json.dumps(data))
            saved = getattr(run, attr)
            setattr(run, attr, path)
            self.addCleanup(setattr, run, attr, saved)

    def run_suite(self, name: str) -> tuple[int, dict]:
        os.environ["FAKE_MODE"] = "done"
        out = self.tmp / "suite-out"
        with contextlib.redirect_stdout(io.StringIO()):
            code = run.main(["--suite", name, "--host", "grok", "--grok-bin", str(self.fakes["grok"]),
                             "--output", str(out), "--plugin-dir", str(self.plugin),
                             "--baseline", str(self.baselines)])
        return code, json.loads((out / "suite-result.json").read_text())

    def test_follow_on_starts_from_its_predecessor_and_rows_record_the_suite(self):
        self.use_catalog(
            {"first": {"style": "s", "prompt": "p", "checks": ["test -f hello.py"]},
             "second": {"style": "s", "follows": "first", "prompt": "q", "checks": [], "retention": []}},
            {"focus": {"kind": "focused", "style": "s", "cases": ["first", "second"]}})
        code, result = self.run_suite("focus")
        self.assertEqual(code, 0, result)
        self.assertEqual([row["case"] for row in result["cases"]], ["first", "second"])
        second = json.loads((self.tmp / "suite-out" / "second" / "result.json").read_text())
        self.assertEqual(second["follow_on"]["prior"], str((self.tmp / "suite-out" / "first").resolve()))
        rows = [json.loads(line) for line in self.baselines.read_text().splitlines()]
        self.assertEqual([(r["case"], r["style"], r["suite"], r["pass"]) for r in rows],
                         [("first", "s", "focus", True), ("second", "s", "focus", True)])

    def test_follow_on_is_skipped_when_its_predecessor_failed(self):
        self.use_catalog(
            {"first": {"style": "s", "prompt": "p", "checks": ["false"]},
             "second": {"style": "s", "follows": "first", "prompt": "q", "checks": []}},
            {"focus": {"kind": "focused", "style": "s", "cases": ["first", "second"]}})
        code, result = self.run_suite("focus")
        self.assertEqual(code, 1)
        self.assertIn("failed", result["cases"][1]["skipped"])
        self.assertFalse((self.tmp / "suite-out" / "second").exists())

    def test_tmp_writes_and_names_shared_across_runs(self):
        """P13: a literal /tmp path is shared with every other run; the suite names any two that met."""
        self.assertEqual(metrics.tmp_writes("node --test > /tmp/w1.txt 2>&1"), ["/tmp/w1.txt"])
        self.assertEqual(metrics.tmp_writes("python3 x.py | tee /tmp/r.json"), ["/tmp/r.json"])
        self.assertEqual(metrics.tmp_writes('mv out.json "/tmp/improve-done-1.json"'), ["/tmp/improve-done-1.json"])
        self.assertEqual(metrics.tmp_writes("cat /tmp/a.txt"), [])  # a read
        self.assertEqual(metrics.tmp_writes("x > /x/run/scratch/a.txt"), [])  # the run's own scratch
        self.assertEqual(metrics.tmp_writes("python3 - <<'PY'\nopen('/tmp/x','w')\nPY"), [])  # a document
        outs = []
        for name, target in (("a", "/tmp/improve-done-1.json"), ("b", "/tmp/improve-done-1.json"),
                             ("c", "/tmp/other.json")):
            out = self.tmp / name
            out.mkdir()
            (out / "events.jsonl").write_text(json.dumps({"type": "tool_call", "toolCallId": "1", "toolName": "write",
                                                          "rawInput": {"file_path": target, "content": "{}"}}) + "\n")
            outs.append(out)
        self.assertEqual(run.shared_tmp_writes(outs), {"/tmp/improve-done-1.json": ["a", "b"]})

    def test_independent_chains_run_concurrently_and_report_in_suite_order(self):
        cases = {"a": {"style": "s", "prompt": "p", "checks": []},
                 "b": {"style": "t", "prompt": "p", "checks": []},
                 "a2": {"style": "s", "follows": "a", "prompt": "q", "checks": []}}
        self.assertEqual(run.suite_chains(["a", "b", "a2"], cases), [["a", "a2"], ["b"]])
        self.use_catalog(cases, {"wide": {"kind": "breadth", "cases": ["a", "b", "a2"]}})
        started = []
        real_main = run.main

        def spy(argv=None):
            if argv and "--case" in argv:
                started.append(argv[argv.index("--case") + 1])
                self.assertIn("--quiet", argv)  # concurrent live views would interleave
            return real_main(argv)

        with mock.patch.object(run, "main", side_effect=spy):
            code, result = self.run_suite("wide")
        self.assertEqual(code, 0, result)
        self.assertEqual([row["case"] for row in result["cases"]], ["a", "b", "a2"])
        self.assertLess(started.index("a"), started.index("a2"))
        self.assertTrue(all((self.tmp / "suite-out" / name / "result.json").is_file() for name in ("a", "b", "a2")))

    def test_a_batch_gate_runs_first_and_a_failed_gate_stops_the_rest(self):
        cases = {"g": {"style": "s", "prompt": "p", "checks": ["false"]},
                 "a": {"style": "t", "prompt": "p", "checks": []}}
        self.use_catalog(cases, {"b": {"kind": "batch", "gate": ["g"], "cases": ["a"]}})
        code, result = self.run_suite("b")
        self.assertEqual(code, 1)
        self.assertEqual([(r["case"], r.get("skipped")) for r in result["cases"]], [("g", None), ("a", "the gate failed")])
        self.assertFalse((self.tmp / "suite-out" / "a").exists())
        cases["g"]["checks"] = []
        self.use_catalog(cases, {"b": {"kind": "batch", "gate": ["g"], "cases": ["a"]}})
        shutil.rmtree(self.tmp / "suite-out")
        code, result = self.run_suite("b")
        self.assertEqual(code, 0, result)
        self.assertEqual([r["case"] for r in result["cases"]], ["g", "a"])

    def test_committed_suites_name_known_cases_and_breadth_covers_every_focused_style(self):
        cases = json.loads(run.CASES.read_text())
        suites = {k: v for k, v in json.loads(run.SUITES.read_text()).items() if not k.startswith("_")}
        for name, suite in suites.items():
            for case in suite["cases"]:
                self.assertIn(case, cases, name)
                if suite["kind"] == "focused":
                    self.assertEqual(cases[case]["style"], suite["style"], (name, case))
        focused = {s["style"] for s in suites.values() if s["kind"] == "focused" and s["style"] != "smoke"}
        breadth = {cases[c]["style"] for c in suites["breadth"]["cases"]}
        self.assertEqual(breadth, focused)

    def test_case_checks_name_existing_helper_scripts_and_subcommands(self):
        cases = json.loads(run.CASES.read_text())
        for name, case in cases.items():
            for check in case["checks"] + case.get("retention", []):
                for script, sub in re.findall(r'"\$E2E_CHECKS/([\w.]+)" (\w+)', check):
                    with self.subTest(case=name, check=check):
                        path = run.HERE / "checks" / script
                        self.assertTrue(path.is_file())
                        self.assertIn('"' + sub + '":', path.read_text())

    def test_a_second_run_reports_the_change_against_the_previous_row(self):
        self.invoke("grok", "done")
        output = io.StringIO()
        os.environ["FAKE_MODE"] = "done"
        with contextlib.redirect_stdout(output):
            run.main(["--host", "grok", "--grok-bin", str(self.fakes["grok"]), "--output", str(self.tmp / "again"),
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        self.assertIn("baseline  vs", output.getvalue())
        self.assertEqual(len(self.baselines.read_text().splitlines()), 2)

class CheckHygieneTest(unittest.TestCase):
    def test_temperature_unit_check_requires_tests_and_success(self):
        check = json.loads(run.CASES.read_text())["temperature-report"]["checks"][0]
        for name, source, expected in (
            ("no tests", None, False),
            ("passing", "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self): self.assertTrue(True)\n", True),
            ("failing", "import unittest\nclass T(unittest.TestCase):\n    def test_bad(self): self.fail('broken product')\n", False),
        ):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp)
                if source is not None:
                    (work / "test_product.py").write_text(source)
                result = run.run_checks(work, [check])[0]
                self.assertEqual(result["pass"], expected, result["output"])

    def test_temperature_stats_check_rejects_missing_wrong_and_nonconforming_modules(self):
        check = json.loads(run.CASES.read_text())["temperature-report"]["checks"][2]
        correct = (
            "def mean(values):\n"
            "    if not values: raise ValueError('empty')\n"
            "    return sum(values) / len(values)\n"
            "def median(values):\n"
            "    if not values: raise ValueError('empty')\n"
            "    ordered = sorted(values); middle = len(ordered) // 2\n"
            "    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2\n"
        )
        variants = (
            ("missing", None, False),
            ("correct", correct, True),
            ("wrong mean", correct.replace("sum(values) / len(values)", "99"), False),
            ("wrong median", correct.replace("ordered = sorted(values)", "ordered = list(values)"), False),
            ("wrong exception", correct.replace("ValueError", "TypeError"), False),
            ("accepts empty", correct.replace("raise ValueError('empty')", "return 0"), False),
        )
        for name, source, expected in variants:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp)
                if source is not None:
                    (work / "stats.py").write_text(source)
                result = run.run_checks(work, [check])[0]
                self.assertEqual(result["pass"], expected, result["output"])

    def test_checks_run_with_standard_input_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run.run_checks(Path(tmp), ["read line; test -z \"$line\""], timeout=10)[0]
        self.assertTrue(result["pass"], result)  # reading stdin returns at once instead of waiting

    def test_checks_leave_no_untracked_file_behind(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            subprocess.run(["git", "init", "-q", str(work)], check=True)
            (work / "mine.txt").write_text("the user's own file\n")
            results = run.run_checks(work, ["echo log > server.log", "echo page > page.html; false"])
            self.assertEqual([r["pass"] for r in results], [True, False])
            self.assertFalse((work / "server.log").exists())
            self.assertFalse((work / "page.html").exists())
            self.assertTrue((work / "mine.txt").exists(), "files present before the checks are kept")

    def test_scoring_spec_check_accepts_in_place_requirement_updates(self):
        check = json.loads(run.CASES.read_text())["battleship-scoring"]["retention"][3]
        with tempfile.TemporaryDirectory() as tmp:
            prior, work = Path(tmp) / "prior", Path(tmp) / "work"
            for root, extra in ((prior, ""), (work, "Every fire returns shots, hits and accuracy.\n")):
                (root / "docs" / "shiploop").mkdir(parents=True)
                (root / "docs" / "shiploop" / "spec.md").write_text("## R-1 Fire\n" + extra)
            ok = run.run_checks(work, [check], env={"PRIOR_WORK": str(prior)})[0]
            self.assertTrue(ok["pass"], ok["output"])
            (work / "docs" / "shiploop" / "spec.md").write_text("## R-2 Other\nshots and accuracy\n")
            dropped = run.run_checks(work, [check], env={"PRIOR_WORK": str(prior)})[0]
            self.assertFalse(dropped["pass"], "a dropped earlier id still fails")

def write_engine_records(run_dir: Path, accepted: list, *, status: str = "done",
                         stage: str | None = None, inner: dict | None = None,
                         started: float | bool | None = None) -> None:
    """Write the state.md and timeline.json a run would leave behind.

    ``accepted`` is (action, stage, outcome, epoch-or-None); an action with None
    gets no acceptance stamp, which is how an unreadable or recreated timeline
    looks to the reader. ``started`` is the engine's start (default: the first stamp);
    False leaves it out, as in a run from before the pace line.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    state = {"navigator_protocol_version": 4, "status": status,
             "stage": stage or (accepted[-1][1] if accepted else "intake"),
             "history": [{"stage": s, "outcome": o, "workitem": None, "action": a}
                         for a, s, o, _t in accepted]}
    if inner:
        state.update(inner)
    (run_dir / "state.md").write_text("# state\n\n```shiploop-state\n"
                                      + json.dumps(state, indent=2) + "\n```\n")
    # Second precision, which is what the navigator's own _utc_now writes.
    def stamp(epoch: float) -> str:
        return datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    begin = min((t for *_x, t in accepted if t is not None), default=0) if started is None else started
    (run_dir / "timeline.json").write_text(json.dumps(
        {**({} if begin is False else {"started": stamp(begin)}),
         "accepted": {a: stamp(t) for a, _s, _o, t in accepted if t is not None}}, indent=2) + "\n")


class StageAttributionTest(unittest.TestCase):
    """Per-stage attribution reads ShipLoop's own records and never invents timing."""

    def collect(self, accepted: list, *, status: str = "done", stage: str | None = None,
                inner: dict | None = None, events: int = 6) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_dir = out / "run"
            stream = [{"type": "usage", "usage": {"input_tokens": 100, "output_tokens": 1}}
                      for _n in range(events)]
            (out / "events.jsonl").write_text("\n".join(json.dumps(e) for e in stream) + "\n")
            (out / "timeline.jsonl").write_text("\n".join(json.dumps({"line": n, "t": 100.0 + n})
                                                          for n in range(events)) + "\n")
            write_engine_records(run_dir, accepted, status=status, stage=stage, inner=inner)
            return metrics.collect(out, run_dir)

    def test_an_action_without_a_readable_stamp_reports_unavailable_not_zero(self):
        m = self.collect([("A1", "intake", "done", 101.0), ("A2", "spec", "done", None)])
        self.assertEqual(m["stages"][1], {"stage": "spec", "outcome": "done", "timing": "unavailable"})
        self.assertIn("seconds", m["stages"][0])

    def test_without_any_runner_timeline_every_stage_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_dir = out / "run"
            (out / "events.jsonl").write_text(json.dumps(
                {"type": "usage", "usage": {"input_tokens": 1, "output_tokens": 1}}) + "\n")
            write_engine_records(run_dir, [("A1", "intake", "done", 101.0)])
            m = metrics.collect(out, run_dir)
        self.assertEqual(m["stages"], [{"stage": "intake", "outcome": "done", "timing": "unavailable"}])

    def test_the_stage_an_active_run_never_accepted_is_still_attributed(self):
        m = self.collect([("A1", "intake", "done", 101.0)], status="active", stage="spec")
        self.assertEqual([s["stage"] for s in m["stages"]], ["intake", "spec"])
        incomplete = m["stages"][-1]
        self.assertTrue(incomplete["incomplete"])
        self.assertGreater(incomplete["turns"], 0)  # the work after the last acceptance

    def test_an_active_inner_loop_reports_the_items_own_stage(self):
        m = self.collect([("A1", "intake", "done", 101.0)], status="active", stage="inner-loop",
                         inner={"work_index": 0, "work_items": [{"id": "W1", "title": "t"}],
                                "inner_loops": {"W1": {"stage": "implement", "action": None}}})
        self.assertEqual(m["stages"][-1]["stage"], "implement")

    def test_a_finished_run_adds_no_incomplete_row(self):
        m = self.collect([("A1", "intake", "done", 101.0), ("A2", "handoff", "done", 102.0)])
        self.assertTrue(all(not s.get("incomplete") for s in m["stages"]))

    def test_a_stage_after_an_unstamped_one_is_not_credited_with_its_time(self):
        """Its window covers both actions, so attributing it all here would overstate it."""
        m = self.collect([("A1", "intake", "done", 101.0), ("A2", "spec", "done", None),
                          ("A3", "plan", "done", 104.0), ("A4", "prepare", "done", 105.0)])
        timing = [(s["stage"], s.get("timing", "measured")) for s in m["stages"]]
        self.assertEqual(timing, [("intake", "measured"), ("spec", "unavailable"),
                                  ("plan", "unavailable"), ("prepare", "measured")])
        # Attribution resumes from the next known boundary, not from before the gap.
        self.assertEqual(m["stages"][3]["seconds"], 1.0)

    def test_both_stamp_precisions_the_engine_writes_are_read(self):
        """The navigator writes second precision; other records use microseconds."""
        self.assertEqual(metrics._epoch("1970-01-01T00:01:41Z"), 101.0)
        self.assertEqual(metrics._epoch("1970-01-01T00:01:41.500000Z"), 101.5)
        self.assertIsNone(metrics._epoch("not a time"))
        self.assertIsNone(metrics._epoch(None))

    def test_a_stage_row_carries_no_output_token_figure(self):
        # A per-event output count is a streaming snapshot (16 to 17 times below the host's own total on two
        # recorded Claude runs): no stage row carries one.
        m = self.collect([("A1", "intake", "done", 103.0), ("A2", "spec", "done", 105.0)])
        self.assertEqual([r["turns"] for r in m["stages"]], [4, 2])
        self.assertTrue(all("output_tokens" not in row for row in m["stages"]), m["stages"])

    def test_the_committed_baseline_keeps_only_comparable_stage_fields(self):
        rows = [{"stage": "spec", "outcome": "done", "seconds": 1.0, "turns": 2,
                 "tool_calls": 3, "output_tokens": 4},
                {"stage": "plan", "outcome": "done", "timing": "unavailable"},
                {"stage": "implement", "outcome": None, "incomplete": True, "seconds": 5.0, "turns": 6,
                 "tool_calls": 7, "output_tokens": 8}]
        kept = run.baseline_stages(rows)
        self.assertEqual(kept[0], {"stage": "spec", "outcome": "done", "seconds": 1.0, "turns": 2})
        # The markers that say a row is not comparable must survive.
        self.assertEqual(kept[1], {"stage": "plan", "outcome": "done", "timing": "unavailable"})
        self.assertTrue(kept[2]["incomplete"])
        self.assertTrue(all("tool_calls" not in r and "output_tokens" not in r for r in kept))
        self.assertIsNone(run.baseline_stages(None))


class BaselineComparabilityTest(unittest.TestCase):
    """SPEC: a baseline compares only with rows from the same host, model and effort."""

    ROWS = [{"case": "hello", "source": "marketplace", "host": "claude", "model": "m", "effort": "high",
             "turns": 1},
            {"case": "hello", "source": "marketplace", "host": "codex", "model": "m", "effort": "high",
             "turns": 2},
            {"case": "hello", "source": "marketplace", "turns": 3}]  # written before the fields existed

    def rows_file(self, tmp: str) -> Path:
        path = Path(tmp) / "baselines.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in self.ROWS))
        return path

    def test_only_the_same_host_model_and_effort_is_a_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.rows_file(tmp)
            same = run.previous_row(path, "hello", "marketplace", "claude", "m", "high")
            other_host = run.previous_row(path, "hello", "marketplace", "codex", "m", "high")
            other_effort = run.previous_row(path, "hello", "marketplace", "claude", "m", "xhigh")
        self.assertEqual(same["turns"], 1)
        self.assertEqual(other_host["turns"], 2)
        self.assertIsNone(other_effort)  # no row ran that effort: nothing to compare with

    def test_a_row_without_the_identity_fields_is_not_used_as_a_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.rows_file(tmp)
            self.assertIsNone(run.previous_row(path, "hello", "marketplace", None, None, "high"))
            # The legacy row names no host/model/effort, so it matches only an all-None request.
            self.assertEqual(run.previous_row(path, "hello", "marketplace")["turns"], 3)

    def test_the_stage_diff_locates_a_regression_and_refuses_to_guess(self):
        before = [{"stage": "spec", "turns": 10, "seconds": 600}, {"stage": "implement", "turns": 5, "seconds": 60}]
        now = [{"stage": "spec", "turns": 40, "seconds": 2400}, {"stage": "implement", "turns": 5, "seconds": 60}]
        lines = run.stage_diff_lines(before, now)
        self.assertIn("spec 10->40", lines[0])
        self.assertNotIn("implement", lines[0])  # unchanged stages are not noise
        self.assertEqual(run.stage_diff_lines(before, [{"stage": "spec", "timing": "unavailable"}]),
                         ["per-stage comparison unavailable (one run has no measured stage timing)"])
        self.assertEqual(run.stage_diff_lines(before, before), ["no per-stage turn difference"])

    def test_a_partial_comparison_says_how_much_it_covers(self):
        before = [{"stage": "spec", "turns": 10, "seconds": 600}]
        now = [{"stage": "spec", "turns": 40, "seconds": 2400},
               {"stage": "plan", "timing": "unavailable"},
               {"stage": "implement", "timing": "unavailable"}]
        lines = run.stage_diff_lines(before, now)
        self.assertIn("covers 1 of 3 stages (2 not comparable, incomplete or unmeasured on a side: "
                      "implement, plan)", lines[0])
        self.assertIn("spec 10->40", lines[1])

    def test_repeated_visits_to_one_stage_are_summed(self):
        before = [{"stage": "implement", "turns": 3, "seconds": 30}]
        now = [{"stage": "implement", "turns": 4, "seconds": 40} for _n in range(3)]
        self.assertIn("implement 3->12", run.stage_diff_lines(before, now)[0])


class PlanningReviewRowTest(unittest.TestCase):
    """A baseline row records the run's planning_review mode, and a run is compared only with a row of its own mode:
    planning minutes, Improve passes and turns are not the same quantity under stage and none."""

    NOTE = "predates the option"

    def earlier(self, **fields) -> dict:
        return {"date": "2026-10-04T10:00:00+0000", "shiploop_version": "0.52.0", **fields}

    def test_the_mode_is_read_from_a_genuine_state_md_as_written_and_is_not_recorded_when_the_key_is_absent(self):
        fixtures = ROOT / "test" / "fixtures" / "run-review"  # `shiploop init --planning-review <mode>` of the plugin's own CLI
        for mode in ("stage", "none"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / "state.md").write_text((fixtures / f"state-{mode}.md").read_text())
                self.assertEqual(metrics.planning_review(metrics.engine_state(Path(tmp))), mode)
        self.assertEqual([metrics.planning_review(s) for s in (
            {"planning_review": "once"}, {"planning_review": 2}, {}, {"planning_review": None}, metrics.engine_state(None))],
            ["once", "2", "not recorded", "not recorded", "not recorded"])

    def test_the_row_carries_the_mode_and_a_row_built_without_one_says_not_recorded(self):
        result = {"case": "hello", "metrics": {}}
        self.assertEqual(run.baseline_row(result, None, None, "none")["planning_review"], "none")
        self.assertEqual(run.baseline_row(result, None, None, "stage")["planning_review"], "stage")
        self.assertEqual(run.baseline_row(result, None, None)["planning_review"], "not recorded")  # no default mode

    def test_a_row_stands_for_the_mode_it_recorded_and_for_stage_only_when_its_plugin_predates_the_option(self):
        self.assertEqual(run.row_planning_review({"planning_review": "none", "plugin_version": "1.22.0"}), ("none", ""))
        self.assertEqual(run.row_planning_review({"planning_review": "once", "plugin_version": "1.21.0"}), ("once", ""))
        for version in ("1.21.0", "1.20.0", "1.9.0", "0.99.9"):  # numbers, not text: 1.9.0 is before 1.22.0
            with self.subTest(version=version):
                mode, why = run.row_planning_review({"plugin_version": version})
                self.assertEqual(mode, "stage")
                self.assertIn(f"plugin {version} {self.NOTE}", why)
        self.assertEqual(run.row_planning_review({"planning_review": None, "plugin_version": "1.20.0"})[0], "stage")
        for version in (None, "", "1.22.0", "1.22.1", "1.100.0", "2.0.0", "1.22", "dev", "1.21.0-rc.1", 121):
            with self.subTest(version=version):
                mode, why = run.row_planning_review({} if version is None else {"plugin_version": version})
                self.assertEqual(mode, "not recorded")
                self.assertTrue(why.startswith("records no mode and "), why)
        self.assertEqual(run.PLANNING_REVIEW_FIRST_RELEASE, "1.22.0")

    def test_the_report_line_names_why_nothing_was_compared_and_the_last_row_of_the_driver(self):
        line = run.planning_review_line
        self.assertEqual(line("none", self.earlier(planning_review="stage")),
                         "  baseline  not compared across planning_review modes (none vs stage); no earlier row of mode none; "
                         "the last row for this driver is 2026-10-04, ShipLoop 0.52.0")
        self.assertIn("(stage vs none); no earlier row of mode stage;", line("stage", self.earlier(planning_review="none")))
        as_stage = line("none", self.earlier(plugin_version="1.21.0"))
        self.assertIn("(none vs stage); no earlier row of mode none;", as_stage)
        self.assertTrue(as_stage.endswith("; it records no mode, read as stage because plugin 1.21.0 predates the option"), as_stage)
        for fields, why in ((self.earlier(), "no plugin_version places it before the option"),
                            (self.earlier(plugin_version="1.22.0"), "plugin 1.22.0 does not predate the option")):
            unknown = line("stage", fields)
            self.assertIn("(stage vs not recorded); no earlier row of mode stage;", unknown)
            self.assertTrue(unknown.endswith("; it records no mode and " + why), unknown)
        # a run that records no mode matches no row, and says that instead of "no earlier row of mode not recorded"
        self.assertIn("(not recorded vs stage); this run records no mode;", line("not recorded", self.earlier(planning_review="stage")))
        both = line("not recorded", self.earlier(planning_review="not recorded"))
        self.assertIn("(not recorded vs not recorded); this run records no mode;", both)
        self.assertNotIn("no earlier row of mode", both)

    DRIVER = {"case": "hello", "source": "marketplace", "host": "claude", "model": "m", "effort": "high"}

    def scan(self, rows: list[dict], mode: str | None, **driver) -> tuple[dict | None, int]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "baselines.jsonl"
            path.write_text("".join(json.dumps({**self.DRIVER, **row}) + "\n" for row in rows))
            return run.scan_baseline(path, "hello", "marketplace", "claude", "m", "high", mode)

    def test_a_run_is_compared_with_the_last_row_of_its_own_mode_found_past_rows_of_the_other(self):
        stage, none = {"planning_review": "stage"}, {"planning_review": "none"}
        turns = lambda found: found and found["turns"]  # noqa: E731
        self.assertEqual(turns(self.scan([dict(stage, turns=1), dict(none, turns=2)], "stage")[0]), 1)  # not refused as before
        self.assertEqual(turns(self.scan([dict(stage, turns=1), dict(none, turns=2)], "none")[0]), 2)
        rows = [dict(stage, turns=1), dict(none, turns=2), dict(stage, turns=3), dict(none, turns=4)]  # interleaved
        self.assertEqual((turns(self.scan(rows, "none")[0]), turns(self.scan(rows, "stage")[0])), (4, 3))
        self.assertEqual(turns(self.scan(rows[:3], "none")[0]), 2)
        self.assertEqual(self.scan(rows, "stage")[1], 4)  # the count still says how many rows the case and source have
        self.assertEqual(turns(self.scan(rows, None)[0]), 4)  # no mode asked for: the last row of the driver, as before

    def test_no_earlier_row_of_the_runs_mode_finds_nothing_and_an_unrecorded_mode_matches_no_row(self):
        self.assertEqual(self.scan([{"planning_review": "none", "turns": 1}], "stage"), (None, 1))
        self.assertEqual(self.scan([{"planning_review": "stage", "turns": 1}], "once"), (None, 1))
        self.assertEqual(self.scan([{"planning_review": "not recorded", "turns": 1}], "not recorded"), (None, 1))
        self.assertEqual(self.scan([{"turns": 1}], "not recorded"), (None, 1))
        other_driver = [{"planning_review": "stage", "turns": 1, "host": "codex"}]
        self.assertEqual(self.scan(other_driver, "stage"), (None, 1))  # the driver rule is unchanged

    def test_a_row_with_no_mode_is_found_as_stage_only_when_its_plugin_predates_the_option(self):
        none = {"planning_review": "none", "turns": 2}
        old = {"plugin_version": "1.21.0", "turns": 1}
        self.assertEqual(self.scan([old, none], "stage")[0]["turns"], 1)  # the old row is the stage row past the none row
        self.assertEqual(self.scan([old, none], "none")[0]["turns"], 2)
        for fields in ({"turns": 1}, {"turns": 1, "plugin_version": "1.22.0"}, {"turns": 1, "plugin_version": "dev"}):
            self.assertIsNone(self.scan([fields, none], "stage")[0], fields)

    def test_the_version_constant_is_named_once_and_the_readme_says_the_rule(self):
        self.assertEqual(Path(run.__file__).read_text().count('"1.22.0"'), 1)
        readme = " ".join((ROOT / "test" / "shiploop_e2e" / "README.md").read_text().split())
        for phrase in ("not compared across planning_review modes (<this> vs <previous>)",
                       "compared with the last row of its own mode", "no earlier row of mode <this>",
                       "it stands for `stage` only when its recorded `plugin_version` is below 1.22.0",
                       "reads `not recorded` and is compared with no run", "the run's `planning_review` mode"):
            self.assertIn(phrase, readme)


class TerminationRecordTest(unittest.TestCase):
    """Why a run stopped is the harness's to record, and unknown is kept."""

    def facts(self, engine: dict, resume_stop: str | None, stops: list) -> dict:
        sessions = [{"stop": s} for s in stops]  # one entry per launched session, as run.launch reports it
        return run.termination_facts({"status": "exited", "returncode": 0, "sessions": sessions, "resumes": 0},
                                     engine, resume_stop)

    def test_an_abandoned_run_names_the_stage_it_never_accepted(self):
        engine = {"status": "active", "stage": "inner-loop", "work_index": 0,
                  "work_items": [{"id": "W1"}], "inner_loops": {"W1": {"stage": "test-green"}}}
        facts = self.facts(engine, "resume budget spent (8)", ["end_turn"])
        self.assertEqual(facts["engine_status"], "active")
        self.assertEqual(facts["engine_unaccepted_stage"], "test-green")
        self.assertEqual(facts["resume_stop"], "resume budget spent (8)")

    def test_a_missing_reason_is_unknown_and_never_guessed(self):
        facts = self.facts({}, None, [None])
        self.assertEqual(facts["resume_stop"], "unknown")
        self.assertEqual(facts["session_stops"], ["unknown"])
        self.assertEqual(facts["engine_status"], "unknown")
        self.assertEqual(facts["engine_stage"], "unknown")
        self.assertIsNone(facts["engine_unaccepted_stage"])

    def test_a_finished_run_has_no_unaccepted_stage(self):
        facts = self.facts({"status": "done", "stage": "handoff"}, "ShipLoop run is done", ["end_turn"])
        self.assertIsNone(facts["engine_unaccepted_stage"])
        self.assertEqual(facts["engine_stage"], "handoff")


class MetricsTest(unittest.TestCase):
    def test_turns_failures_and_truncations_are_attributed_to_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_dir = out / "loop" / "run"
            (run_dir / "results").mkdir(parents=True)
            (run_dir / "improve" / "child-1").mkdir(parents=True)
            (run_dir / "improve" / "child-1-bind.md").write_text("# bind\n")  # a real run leaves one per child
            stream = [
                {"type": "usage", "usage": {"input_tokens": 1000, "output_tokens": 10}},
                {"type": "tool_call", "toolCallId": "a", "rawInput": {"command": "python3 x/shiploop complete --run-dir r"}},
                {"type": "tool_call_update", "toolCallId": "a", "rawOutput": {
                    "exit_code": 2, "output_for_prompt": "SHIPLOOP-RUN run=x rev=1 dir=/r\nerror: result refused"}},
                {"type": "tool_call_update", "toolCallId": "a", "rawOutput": {"exit_code": 2, "truncated": True}},
                {"type": "usage", "usage": {"input_tokens": 3000, "output_tokens": 20}},
                {"type": "tool_call", "toolCallId": "b", "rawInput": {"command": "node --test"}},
                {"type": "tool_call_update", "toolCallId": "b", "rawOutput": {"exit_code": 0, "truncated": True}},
                {"type": "tool_call", "toolCallId": "c", "rawInput": {"command": "git init -b main"}},
                {"type": "tool_call_update", "toolCallId": "c", "status": "failed", "rawOutput": None, "content": [
                    {"type": "content", "content": {"type": "text",
                                                    "text": "User cancelled the execution for tool `run_terminal_command`"}}]},
                {"type": "tool_call", "toolCallId": "q", "toolName": "ask_user_question",
                 "rawInput": {"question": "Which port?"}},
                {"type": "auto_compact_completed"},
                {"type": "usage", "usage": {"input_tokens": 500, "output_tokens": 5}},
                {"type": "end", "stopReason": "end_turn", "num_turns": 3, "total_cost_usd": 3.0},
            ]
            (out / "events.jsonl").write_text("\n".join(json.dumps(e) for e in stream) + "\n")
            (out / "timeline.jsonl").write_text("\n".join(json.dumps({"line": n, "t": 100.0 + n})
                                                           for n in range(len(stream))) + "\n")
            # Stage boundaries come from ShipLoop's own history and acceptance
            # stamps, joined by action id -- not from result-file mtimes.
            write_engine_records(run_dir, [("A1", "intake", "done", 104.5), ("A2", "spec", "done", 111.5)])
            m = metrics.collect(out, run_dir)
        self.assertEqual(m["turns"], 3)
        self.assertEqual(m["cost_usd"], 3.0)
        self.assertEqual(m["compactions"], 1)
        self.assertEqual(m["truncated_outputs"], 2)
        self.assertEqual(m["script_verifications"],
                         {"records": 0, "passed": 0, "could_not_run": 0, "commands": 0, "red": 0})
        self.assertEqual(m["cancelled_tool_calls"], ["git init -b main"])
        self.assertEqual(m["asked_user"], ["Which port?"])
        self.assertEqual(m["improve_children"], 1)
        self.assertEqual(m["shiploop_failures"], [{"verb": "complete", "exit": 2, "line": "error: result refused"}])
        self.assertEqual([(s["stage"], s["turns"]) for s in m["stages"]], [("intake", 2), ("spec", 1)])
        self.assertEqual([s["outcome"] for s in m["stages"]], ["done", "done"])
        # No cost is apportioned per stage: a share of one total, split by turn
        # count, moves when prices or unrelated work move.
        self.assertTrue(all("cost_share_usd" not in s for s in m["stages"]))

    # What the script prints after any refused callback, as shiploop_protocol.py words it.
    TRAILERS = ("Read the current packet with next; the rejected request did not advance the graph.",
                "The run is still active: fix the result and resubmit in this turn; do not end the turn over a "
                "refused callback.")

    def recorded_failure_line(self, output: str) -> str:
        """The `line` the export keeps for one refused ShipLoop command whose output was ``output``."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            stream = [{"type": "tool_call", "toolCallId": "a",
                       "rawInput": {"command": "python3 x/shiploop complete --run-dir r"}},
                      {"type": "tool_call_update", "toolCallId": "a",
                       "rawOutput": {"exit_code": 2, "output_for_prompt": output}},
                      {"type": "end", "stopReason": "end_turn", "num_turns": 1, "total_cost_usd": 1.0}]
            (out / "events.jsonl").write_text("\n".join(json.dumps(e) for e in stream) + "\n")
            failures = metrics.collect(out, None)["shiploop_failures"]
        self.assertEqual(len(failures), 1, failures)
        return failures[0]["line"]

    def test_a_refusal_is_recorded_by_its_own_line_not_by_the_trailers_after_it(self):
        marker = "SHIPLOOP-RUN run=x rev=1 dir=/r\n"
        refusal = "ShipLoop navigator: result requires outcome and summary: the result is missing \"summary\""
        trailers = "\n".join(self.TRAILERS)
        # Before: the trailer says "rejected", so it was recorded and the export could not name the refusal.
        self.assertEqual(self.recorded_failure_line(marker + refusal + "\n" + trailers + "\n"), refusal)
        # The script's other refusal prefix, and the lines its blocked branch adds after it.
        blocked = "ShipLoop blocked: the run directory is not readable"
        after = ("Request failure: no in-memory result, candidate, or rejected artifact is trusted.\n"
                 "Durable cursor recovery: do not infer a next action from this error; follow the recovery packet.\n")
        self.assertEqual(self.recorded_failure_line(blocked + "\n" + after), blocked)
        # A line that already matched before is still recorded first, wherever the prefix line sits.
        self.assertEqual(self.recorded_failure_line("shiploop: error: unrecognized arguments: x\n" + trailers),
                         "shiploop: error: unrecognized arguments: x")

    def test_where_only_the_trailers_match_the_export_records_what_it_did_before(self):
        self.assertEqual(self.recorded_failure_line("\n".join(self.TRAILERS) + "\n"), self.TRAILERS[0])
        self.assertEqual(self.recorded_failure_line("nothing here names a failure\n"), "")

    def test_the_trailers_the_export_skips_are_the_ones_the_script_prints(self):
        """The skip list copies the script's fixed text; a reworded trailer must fail here, not hide a refusal."""
        source = " ".join((ROOT / "skills/shiploop/scripts/shiploop_protocol.py").read_text().split())
        for text in (*self.TRAILERS[:1], "The run is still active: fix the result and resubmit in this turn;",
                     "Request failure: no in-memory result", "Durable cursor recovery: ", 'f"ShipLoop navigator: {exc}"',
                     'f"ShipLoop blocked: {exc}"'):
            self.assertIn(text, source)
        for line in self.TRAILERS:
            self.assertRegex(line, metrics.TRAILER_LINE)
        self.assertRegex("ShipLoop navigator: x", metrics.REFUSAL_LINE)

    # What a real Claude result event reports as its usage: nested, and the host's own figure.
    CLAUDE_USAGE = {"input_tokens": 96, "cache_creation_input_tokens": 131587, "cache_read_input_tokens": 5194338,
                    "output_tokens": 28419, "output_tokens_details": {"thinking_tokens": 3450},
                    "server_tool_use": {"web_search_requests": 0, "web_fetch_requests": 0},
                    "cache_creation": {"ephemeral_1h_input_tokens": 131587, "ephemeral_5m_input_tokens": 0},
                    "iterations": [{"input_tokens": 2, "output_tokens": 1109, "type": "message"}],
                    "service_tier": "standard", "speed": "standard", "fallback_credit": None}
    # What the Codex translator's end event carried for a 2189-item session (the recorded Luna battleship run).
    CODEX_USAGE = {"input_tokens": 172611340, "cache_read_input_tokens": 167042304, "output_tokens": 1622714,
                   "reasoning_tokens": 1015804}

    @staticmethod
    def read(events: list[dict]) -> tuple[dict, dict]:
        """metrics.collect and run.summarize_events over the same bare host events."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
            return metrics.collect(out), run.summarize_events(out / "events.jsonl")

    def test_unknown_cost_stays_unknown_and_the_hosts_own_usage_is_kept_unsummed(self):
        luna = {"type": "end", "stopReason": "end_turn", "num_turns": 2189, "total_cost_usd": None,
                "usage": self.CODEX_USAGE}
        grok = {"type": "end", "stopReason": "cancelled", "num_turns": 4, "total_cost_usd": 1.0}
        claude = {"type": "result", "subtype": "success", "num_turns": 56, "total_cost_usd": 1.8495976,
                  "usage": self.CLAUDE_USAGE}
        for label, events, want in (
                ("a host that reports no cost", [luna], None),
                ("one session reported a cost and one did not", [grok, luna], None),
                ("every ended session reported", [grok, grok, claude], round(1.0 + 1.0 + 1.8495976, 4)),
                ("no session ended", [{"type": "available_commands", "commands": []}], None)):
            m, cli = self.read(events)
            self.assertEqual((m["cost_usd"], cli.get("cost_usd")), (want, want), label)
        # The host's own usage rides with its session, as written: never summed, never rebuilt.
        m, _ = self.read([luna])
        self.assertEqual(m["sessions"][0]["usage"], self.CODEX_USAGE)
        m, _ = self.read([claude, claude])  # nested usage is kept whole, not added key by key
        self.assertEqual([s["usage"] for s in m["sessions"]], [self.CLAUDE_USAGE, self.CLAUDE_USAGE])
        self.assertIsNone(self.read([grok])[0]["sessions"][0]["usage"])  # none reported: None, not {} or 0
        # One implementation (SPEC S-12): the metrics and the CLI summary both ask metrics.total_cost.
        with mock.patch.object(metrics, "total_cost", return_value=123.0):
            m, cli = self.read([luna])
        self.assertEqual((m["cost_usd"], cli["cost_usd"]), (123.0, 123.0))

    def test_no_token_figure_is_made_from_events_that_do_not_carry_it(self):
        text_only = {"type": "assistant", "message": {"content": [{"type": "text", "text": "x"}]}}
        m, _ = self.read([text_only] * 3)  # Claude messages that report no usage
        self.assertEqual((m["turns"], m["tokens"]), (3, {"input_peak": None}))
        # A host's end-of-session total is not a per-call context figure, and no output total is built.
        m, _ = self.read([{"type": "end", "num_turns": 9, "total_cost_usd": None, "usage": self.CODEX_USAGE}])
        self.assertEqual(m["tokens"], {"input_peak": None})
        # A call that reported its context counts; one that did not neither lowers the peak nor invents a 0.
        m, _ = self.read([{"type": "usage", "usage": {"input_tokens": 1000, "cache_read_input_tokens": 500,
                                                      "output_tokens": 7}},
                          {"type": "usage", "usage": {"output_tokens": 9}}, {"type": "usage"},
                          {"type": "usage", "usage": {"input_tokens": 200}}])
        self.assertEqual((m["turns"], m["tokens"]), (4, {"input_peak": 1500}))

    def test_a_session_killed_before_it_reported_makes_the_cost_a_lower_bound(self):
        init = {"type": "system", "subtype": "init", "model": "m"}
        result = {"type": "result", "subtype": "success", "num_turns": 5, "total_cost_usd": 1.85}
        opened = {"type": "available_commands", "commands": []}
        end = {"type": "end", "stopReason": "end_turn", "num_turns": 5, "total_cost_usd": None}
        for label, events, want in (
                ("Claude: four sessions began and one reported", [init, init, init, init, result], 3),
                ("Claude: the first was killed, the second finished", [init, init, result], 1),
                ("Codex or Grok: two began and one reported", [opened, opened, end], 1),
                ("Grok: killed before any end", [opened], 1),
                ("every session reported", [init, result, opened, end], 0),
                ("an end with no recorded start is never negative", [result, end], 0),
                ("a Claude system event that is not an init is not a start",
                 [{"type": "system", "subtype": "task_started"}, result], 0)):
            m, _ = self.read(events)
            self.assertEqual(m["unreported_sessions"], want, label)
        m, _ = self.read([init, init, result])
        self.assertEqual(metrics.cost_text(m), "$1.85 (lower bound: 1 session(s) never reported)")
        self.assertIn("cost $1.85 (lower bound: 1 session(s) never reported)", metrics.summary_lines(m)[0])
        whole, _ = self.read([init, result])
        self.assertEqual(metrics.cost_text(whole), "$1.85")
        unknown, _ = self.read([opened, opened, end])  # no figure, so nothing for a lower bound to bound
        self.assertEqual(metrics.cost_text(unknown), "not reported")

    NARRATIVE_BODY = ("#### \U0001f6a2 ShipLoop \u2014 Add a flag\n`\u2588\u2591` **Preparation 1/7**\n\n"
                      "**\u25b6\ufe0f Now** \u2014 **spec**: define behavior\n")

    def packet(self, stage: str, rule: str = "Show the user this narrative exactly as written, as Markdown.") -> str:
        return (f"ShipLoop navigator | {stage} | revision 3\nCallback: x\n\n=== ShipLoop narrative ===\n{rule}\n\n"
                f"{self.NARRATIVE_BODY}=== end ShipLoop narrative ===\n")

    def result_record(self, run_dir: Path, name: str, result: dict) -> None:
        body = json.dumps({"action": name, "result": result, "stage": "intake", "workitem": None}, indent=2)
        (run_dir / "results" / f"{name}.md").write_text(f"# ShipLoop navigator result\n\n```shiploop-state\n{body}\n```\n")

    def test_narrative_shown_verbatim_skipped_and_headlines_grok(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_dir = out / "run"
            (run_dir / "results").mkdir(parents=True)
            half = len(self.NARRATIVE_BODY) // 2
            stream = [
                {"type": "tool_call", "toolCallId": "a", "rawInput": {"command": "shiploop init"}},
                {"type": "tool_call_update", "toolCallId": "a", "rawOutput": {"exit_code": 0, "output_for_prompt": self.packet("intake")}},
                # Grok repeats an update; one tool call is one emission.
                {"type": "tool_call_update", "toolCallId": "a", "rawOutput": {"exit_code": 0, "output_for_prompt": self.packet("intake")}},
                {"type": "text", "data": "Starting.\n" + self.NARRATIVE_BODY[:half]},
                {"type": "text", "data": self.NARRATIVE_BODY[half:]},
                {"type": "tool_call", "toolCallId": "b", "rawInput": {"command": "shiploop complete"}},
                {"type": "tool_call_update", "toolCallId": "b", "rawOutput": {"exit_code": 0, "output_for_prompt": self.packet("discovery")}},
                {"type": "text", "data": "Moving on to discovery."},
                {"type": "tool_call", "toolCallId": "c", "rawInput": {"command": "shiploop complete"}},
                {"type": "tool_call_update", "toolCallId": "c", "rawOutput": {"exit_code": 0, "output_for_prompt": self.packet("research")}},
                {"type": "text", "data": "\U0001f6a2 ShipLoop \u2014 Add a flag\nsomething else"},  # heading only
                # The CLI hook shows this one; the model is not asked to.
                {"type": "tool_call", "toolCallId": "d", "rawInput": {"command": "shiploop complete"}},
                {"type": "tool_call_update", "toolCallId": "d", "rawOutput": {"exit_code": 0, "output_for_prompt": self.packet(
                    "spec", rule="The host's status hook already shows the user this narrative; do not repeat it.")}},
            ]
            (out / "events.jsonl").write_text("\n".join(json.dumps(e) for e in stream) + "\n")
            self.result_record(run_dir, "r1", {"outcome": "done", "summary": "s", "headline": "Scope set"})
            self.result_record(run_dir, "r2", {"outcome": "done", "summary": "s"})
            self.result_record(run_dir, "r3", {"outcome": "done", "summary": "Not applicable to this item: x."})
            story = metrics.narrative(out, run_dir)
            report = metrics.summary_lines({**metrics.collect(out, run_dir), "narrative": story})
        self.assertEqual(story, {"emitted": 3, "shown": 2, "verbatim": 1, "skipped": ["discovery"],
                                 "results": 2, "with_headline": 1})
        self.assertIn("narrative shown 2/3 (verbatim 1), skipped at discovery; headlines 1/2 results", report[-1])
        self.assertNotIn("Add a flag", json.dumps(story))

    def test_narrative_reads_claude_tool_results_and_text_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            stream = [
                {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1",
                                                          "content": [{"type": "text", "text": self.packet("intake")}]}]}},
                {"type": "assistant", "message": {"content": [{"type": "text", "text": self.NARRATIVE_BODY.replace("#### ", "")}]}},
                {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t2",
                                                          "content": self.packet("discovery")}]}},
            ]
            (out / "events.jsonl").write_text("\n".join(json.dumps(e) for e in stream) + "\n")
            story = metrics.narrative(out)
        self.assertEqual((story["emitted"], story["shown"], story["verbatim"], story["skipped"]),
                         (2, 1, 1, ["discovery"]))
        self.assertEqual((story["results"], story["with_headline"]), (0, 0))

    def test_run_without_narrative_reports_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "events.jsonl").write_text(json.dumps({"type": "text", "data": "hi"}) + "\n")
            m = metrics.collect(out)
        self.assertEqual(m["narrative"], {"emitted": 0, "shown": 0, "verbatim": 0, "skipped": [],
                                          "results": 0, "with_headline": 0})
        self.assertFalse(any(line.startswith("narrative") for line in metrics.summary_lines(m)))

    def test_glue_is_defined_by_shiploop_paths_and_verbs_not_by_product_tools(self):
        cases = {
            'cd /x/.shiploop-runs/a/worktree && node --test > "/x/.shiploop-runs/a/worktree/out.txt"': [],
            'npm test > report.txt': [],
            'cat > /x/.shiploop-runs/a/run/inbox/r.md <<EOF': [],  # the model's own result file
            'rm -rf "/x/.shiploop-improve"': ["shell write into a ShipLoop-owned path"],
            'mv /x/wt/.shiploop-improve/n/packet.json /x/p.old': ["shell write into a ShipLoop-owned path"],
            'echo x > /x/.shiploop/state.md': ["shell write into a ShipLoop-owned path"],
            'git -C /x/wt commit -F /tmp/m': ["git commit/add by the model"],
            'python3 until_loop.py start --directory /x <<PY\n{"exit_condition": 1}\nPY': ["hand-built loop contract"],
            "python3 - <<'PY'\nd=json.load(open('/x/run/quality/c-contract.json'))\nprint(d['exit_condition'][:500])\nPY": [],
            'python3 /p/shiploop improve-commit --run-dir=/x/run --action=a --message=/x/m.md': [],
            # words inside a heredoc are a document, not commands
            "python3 - << 'PY'\nreport = {'evidence': 'git log shows the commit'}\nPY\n": [],
            'cd /x/wt && WT=/x git -C "$WT" add docs/a.md && git commit -m m': ["git commit/add by the model"],
            'echo "run git commit later"': [],
            # evidence the packets ask the model to record
            'node --test > "/x/.shiploop-runs/a/run/notes/test-green.txt" 2>&1': [],
            'cp /tmp/r.txt /x/wt/.shiploop-improve/n/a/reviews/checks.md': [],
            'echo x > /x/.shiploop-runs/a/run/results/nav-1.md': ["shell write into a ShipLoop-owned path"],
            # a file of the model's own that merely ends like a ShipLoop name
            'python3 /p/shiploop improve-start --action=a --opening=/x/o.md > /tmp/plan-start.json': [],
            'cp /tmp/x.json /x/wt/.shiploop-improve/n/a/start.json': ["shell write into a ShipLoop-owned path"],
            # check output the packet asks the model to record as evidence
            'npm test > /x/.shiploop-runs/a/run/evidence/w1-verify.txt': [],
            # the run's scratch directory is the model's own (P13)
            'python3 -m unittest > /x/.shiploop-runs/a/run/scratch/baseline.txt 2>&1': [],
            # the Improve child's review directory is where P12 asks it to write
            "mkdir -p .shiploop-improve/n/a/reviews": [],
            # the Improve child's own directory, where the model writes its opening file
            'mkdir -p "/x/wt/.shiploop-improve/run1/nav-1"': [],
            'rm -rf "/x/wt/.shiploop-improve"': ["shell write into a ShipLoop-owned path"],
            # reading ShipLoop's own contract is not building one
            'python3 -c \'import json; p=json.load(open("/x/run/quality/c-contract.json")); print(p["exit_condition"])\'': [],
            'python3 -c \'import json; json.dump({"exit_condition": 1}, open("/x/c.json", "w"))\'': ["hand-built loop contract"],
            # making the model's own directories is not a write into a ShipLoop-owned path (batch 1003 / 1.16.1 run)
            "mkdir -p '/x/.shiploop-runs/a/run/notes' && cat > '/x/.shiploop-runs/a/run/notes/w1.md' <<'EOF'\nx\nEOF": [],
            "mkdir -p /x/.shiploop-runs/a/run/evidence": [],
            "mkdir -p /x/.shiploop-runs/a/run/scratch": [],
            # a `>` in prose inside a quoted string is not a redirect, and run/scratch is the model's own
            "python3 -c 'import pathlib; pathlib.Path(\"/x/.shiploop-runs/a/run/scratch/r.json\").write_text(\"each > 0 must pass; see /x/.shiploop-runs/a/run/results\")'": [],
            'echo x > "/x/.shiploop-runs/a/run/state.md"': ["shell write into a ShipLoop-owned path"],
            # json.dumps only formats text for printing
            "python3 - <<'PY'\nd=json.load(open('/x/packet.json'))\nprint(json.dumps(d['exit_condition'], indent=2))\nPY": [],
        }
        for command, reasons in cases.items():
            with self.subTest(command=command):
                self.assertEqual(metrics.glue_reasons(command), reasons)

    def test_verifications_come_from_shiploop_records_not_tool_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            tests = Path(tmp) / "run" / "tests"
            tests.mkdir(parents=True)
            (tests / "nav-1-verify1.md").write_text('{"passed": true, "runs": [{"command": "a"}, {"command": "b"}]}')
            (tests / "nav-2-verify1.md").write_text('{"passed": false, "runs": [{"command": "c"}]}')
            (tests / "nav-2-contract.json").write_text("{}")
            self.assertEqual(metrics.verifications(Path(tmp) / "run"),
                             {"records": 2, "passed": 1, "could_not_run": 0, "commands": 3, "red": 0})

    def test_progress_reports_only_what_is_new_and_never_a_run_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "events.jsonl").write_text("\n".join(json.dumps(e) for e in (
                {"type": "usage", "usage": {"input_tokens": 1, "output_tokens": 1}},
                {"type": "text", "data": "SHIPLOOP-RUN run=x rev=1 dir=/r"})) + "\n")
            first = progress.report(out)
            second = progress.report(out)
        self.assertIn("turns 1", first)
        self.assertNotIn("SHIPLOOP-RUN", first + second)
        self.assertIn("no run state yet", second)

    def test_progress_says_peak_context_n_a_when_no_call_reported_its_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in (
                {"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}},) * 2))
            text = progress.report(out)
        self.assertIn("turns 2, peak context n/a", text)



class CodexRunTest(HarnessCase):
    def test_codex_run_passes_in_an_isolated_codex_home(self):
        code, result = self.invoke("codex", "done")
        self.assertEqual(code, 0, result)
        seen = self.seen()
        self.assertEqual(seen["cwd_listing"], [])
        self.assertTrue(seen["prompt"].startswith("$skill-craft:shiploop "), seen["prompt"])
        self.assertTrue(seen["auth_is_symlink"])
        self.assertEqual(Path(seen["codex_home"]), Path(result["output"]) / "home" / ".codex")
        argv = seen["argv"]
        self.assertEqual(argv[argv.index("-m") + 1], "gpt-6-luna")
        self.assertIn("model_reasoning_effort=xhigh", argv)
        self.assertTrue(result["invoked"]["pass"], result["invoked"])
        self.assertTrue(result["plugin"]["pass"], result["plugin"])
        self.assertTrue(result["committed"]["pass"], result["committed"])
        self.assertEqual(result["cli"]["num_turns"], 2)
        # Codex reports no dollar cost: unknown everywhere, not $0, and its one session reported its end.
        self.assertIsNone(result["cli"]["cost_usd"])
        self.assertIsNone(result["metrics"]["cost_usd"])
        self.assertEqual(result["metrics"]["unreported_sessions"], 0)
        # Truncated outputs are a Grok-only detection: unknown on Codex, not an empty list.
        self.assertIsNone(result["cli"]["truncated_outputs"])

    def test_model_and_effort_toggle_by_flag(self):
        code, result = self.invoke("codex", "done", "--model", "gpt-6-sol", "--effort", "xhigh")
        self.assertEqual(code, 0, result)
        argv = self.seen()["argv"]
        self.assertEqual(argv[argv.index("-m") + 1], "gpt-6-sol")
        self.assertIn("model_reasoning_effort=xhigh", argv)
        self.assertEqual((result["model"], result["effort"]), ("gpt-6-sol", "xhigh"))

    def test_resume_run_continues_a_stopped_grok_run_on_codex(self):
        code, stopped = self.invoke("grok", "stuck", "--max-resumes", "0")
        self.assertEqual(code, 1)
        out = Path(stopped["output"])
        original = (out / "invocation.json").read_text()
        os.environ["FAKE_MODE"] = "done"
        with contextlib.redirect_stdout(io.StringIO()):
            code = run.main(["--host", "codex", "--codex-bin", str(self.fakes["codex"]), "--resume-run", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        result = json.loads((out / "result.json").read_text())
        self.assertEqual(code, 0, result)
        self.assertEqual(result["host"], "codex")
        self.assertEqual(result["resumed_run"]["from_host"], "grok")
        self.assertEqual(result["resumed_run"]["stage"], "test-refine")
        self.assertIn("next --run-dir", self.seen()["prompt"])
        self.assertEqual((out / "invocation.json").read_text(), original)
        self.assertEqual(len(list(out.glob("invocation-resume-codex-*.json"))), 1)
        events = (out / "events.jsonl").read_text()
        self.assertIn('"sessionId": "sess-1"', events)          # the Grok session is kept
        self.assertIn('"sessionId": "codex-thread-1"', events)  # the Codex session is appended
        # The original run ended with its engine active, so it wrote no row (SPEC: a baseline row is a finished
        # run's), and a resume never writes one.
        self.assertFalse(self.baselines.exists(), "neither the unfinished original nor its resume writes a baseline row")

    def test_resume_run_refuses_a_run_that_is_neither_active_nor_done(self):
        code, finished = self.invoke("grok", "done")
        self.assertEqual(code, 0)
        with mock.patch.object(run, "grade_shiploop", return_value={"status": "paused"}):
            with self.assertRaisesRegex(SystemExit, "needs an active, blocked or finished ShipLoop run"):
                run.main(["--host", "codex", "--codex-bin", str(self.fakes["codex"]),
                          "--resume-run", finished["output"], "--plugin-dir", str(self.plugin)])

    def test_resume_run_on_a_finished_run_regrades_it_without_starting_a_host(self):
        code, finished = self.invoke("grok", "done")
        self.assertEqual(code, 0)
        out = Path(finished["output"])
        (out / "result.json").write_text(json.dumps({"case": "stale", "pass": False}))
        self.log.unlink()
        gate = ["local HEAD 0123abc has commits origin/main does not: publish them first"]
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(run, "version_gate", return_value=gate):
            # The regrade starts no host, so a failing version gate (an unpushed branch) must not stop it.
            run.main(["--host", "grok", "--grok-bin", str(self.fakes["grok"]), "--resume-run", str(out),
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        self.assertFalse(self.log.exists(), "no host process was started")
        regraded = json.loads((out / "result.json").read_text())
        self.assertEqual(regraded["case"], finished["case"], "the stale result was replaced")
        self.assertTrue(regraded["process"]["regraded"])
        # Verdicts come from what is on disk: the finished run and the committed product pass. (The fake host's
        # events carry no plugin or CLI evidence, which a real host's events do, so `pass` is not asserted.)
        self.assertTrue(regraded["shiploop"]["pass"], regraded["shiploop"])
        self.assertTrue(regraded["committed"]["pass"], regraded["committed"])
        self.assertTrue(all(c["pass"] for c in regraded["checks"]), regraded["checks"])


class CodexHostTest(unittest.TestCase):
    """Codex runs through the same host interface; its stream is translated to Grok's shape."""

    STREAM = [
        {"type": "thread.started", "thread_id": "thread-1"},
        {"type": "turn.started"},
        {"type": "item.started", "item": {"id": "item_0", "type": "command_execution",
                                          "command": "/bin/zsh -lc 'python3 /x/skills/shiploop/scripts/shiploop next'",
                                          "aggregated_output": "", "exit_code": None, "status": "in_progress"}},
        {"type": "item.completed", "item": {"id": "item_0", "type": "command_execution",
                                            "command": "/bin/zsh -lc 'python3 /x/skills/shiploop/scripts/shiploop next'",
                                            "aggregated_output": "ShipLoop navigator | intake | revision 0\n",
                                            "exit_code": 0, "status": "completed"}},
        {"type": "item.completed", "item": {"id": "item_1", "type": "file_change", "status": "completed",
                                            "changes": [{"path": "/w/convert.py", "kind": "add"}]}},
        {"type": "item.completed", "item": {"id": "item_2", "type": "command_execution",
                                            "command": "git commit -am wip", "aggregated_output": "fatal\n",
                                            "exit_code": 128, "status": "failed"}},
        {"type": "item.completed", "item": {"id": "item_3", "type": "agent_message", "text": "Done for now."}},
        {"type": "turn.completed", "usage": {"input_tokens": 100, "cached_input_tokens": 80,
                                             "output_tokens": 7, "reasoning_output_tokens": 2}},
    ]

    def translated(self) -> list[dict]:
        translate = hosts.host("codex").translator()
        lines = [raw for event in self.STREAM for raw in translate((json.dumps(event) + "\n").encode())]
        return [json.loads(raw) for raw in lines]

    def test_argv_invocation_and_resume_order(self):
        codex = hosts.host("codex", "codex-bin")
        with tempfile.TemporaryDirectory() as temp:
            argv = codex.argv(prompt="$skill-craft:shiploop build it", prompt_file=Path(temp) / "p.txt",
                              cwd=Path("/w"), model="gpt-6-luna", effort="xhigh", permission_mode="auto",
                              max_turns=10)
            resumed = codex.argv(prompt="continue", prompt_file=Path(temp) / "r.txt", cwd=Path("/w"),
                                 model="gpt-6-luna", effort="xhigh", permission_mode="auto", max_turns=10,
                                 resume="thread-1")
        self.assertEqual(argv[:3], ["codex-bin", "exec", "--json"])
        self.assertIn("model_reasoning_effort=xhigh", argv)
        self.assertEqual(argv[argv.index("-m") + 1], "gpt-6-luna")
        self.assertEqual(argv[-1], "$skill-craft:shiploop build it")
        # Codex takes its options before the resume subcommand.
        self.assertEqual(resumed[-3:], ["resume", "thread-1", "continue"])
        self.assertLess(resumed.index("--json"), resumed.index("resume"))
        self.assertEqual(codex.invoke("skill-craft:shiploop", "x"), "$skill-craft:shiploop x")
        self.assertEqual((codex.model, codex.effort, codex.resumable), ("gpt-6-luna", "xhigh", True))

    def test_env_is_an_isolated_codex_home_linking_only_auth(self):
        with tempfile.TemporaryDirectory() as temp:
            real = Path(temp) / "real"
            real.mkdir()
            (real / "auth.json").write_text("{}")
            with mock.patch.dict(os.environ, {"CODEX_HOME": str(real), "CODEX_SECRET": "x"}):
                env = hosts.host("codex").env(Path(temp) / "home")
            codex_home = Path(env["CODEX_HOME"])
            self.assertEqual(codex_home, Path(temp) / "home" / ".codex")
            self.assertEqual((codex_home / "auth.json").resolve(), (real / "auth.json").resolve())
            self.assertNotIn("CODEX_SECRET", env)
            self.assertEqual(env["HOME"], str(Path(temp) / "home"))

    def test_translated_stream_reads_like_grok_for_every_parser(self):
        events = self.translated()
        kinds = [e["type"] for e in events]
        self.assertEqual(kinds, ["available_commands", "tool_call", "tool_call_update", "tool_call",
                                 "tool_call_update", "tool_call", "tool_call_update", "text", "end"])
        self.assertEqual(events[2]["rawOutput"]["exit_code"], 0)
        self.assertEqual(events[3]["rawInput"]["target_file"], "/w/convert.py")
        self.assertEqual(events[6]["status"], "failed")
        end = events[-1]
        self.assertEqual((end["sessionId"], end["num_turns"], end["total_cost_usd"]), ("thread-1", 4, None))
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            path = out / "events.jsonl"
            path.write_text("".join(json.dumps(e) + "\n" for e in events))
            self.assertEqual(run.last_session_id(path), "thread-1")
            self.assertTrue(run.shiploop_cli_ran(path))
            seen = run.summarize_events(path)
            self.assertEqual((seen["num_turns"], seen["cost_usd"], seen["commands"]), (4, None, []))
            self.assertEqual(hosts.final_text(path).strip(), "Done for now.")
            run.write_transcript(path, out / "transcript.md")
            transcript = (out / "transcript.md").read_text()
            self.assertIn("tool  run_terminal_command:", transcript)
            self.assertIn("say   Done for now.", transcript)
            self.assertIn("turns=4 cost=not reported", transcript)  # not "$None"
            collected = metrics.collect(out)
            self.assertEqual(collected["turns"], 4)
            self.assertTrue(any("git commit" in g["command"] for g in collected["model_glue"]))

    def test_turns_add_a_codex_session_to_a_grok_run_it_resumed(self):
        grok = [{"type": "usage", "usage": {"input_tokens": 1}}, {"type": "usage", "usage": {"input_tokens": 2}},
                {"type": "end", "stopReason": "cancelled", "num_turns": 91, "total_cost_usd": 1.0}]
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in grok + self.translated()))
            self.assertEqual(metrics.collect(out)["turns"], 2 + 4)

    def test_every_host_is_selectable_by_name(self):
        self.assertEqual(sorted(hosts.HOSTS), ["claude", "codex", "grok"])
        for name in hosts.HOSTS:
            agent = hosts.host(name)
            self.assertEqual(agent.name, name)
            self.assertEqual(hosts.HOST_DEFAULTS[name], {"model": agent.model, "effort": agent.effort})


class FanoutGradeTest(unittest.TestCase):
    """The live fan-out/fan-in check is graded from stamps and dispatcher state, never by the model."""

    def grade(self, stamps: dict, complete: bool = True, handles: bool = True) -> dict:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dispatch = root / "dispatch.js"
            dispatch.write_text("process.stdout.write(JSON.stringify({complete: %s}))" % str(complete).lower())
            run_dir, marks = root / "run", root / "stamps"
            run_dir.mkdir()
            marks.mkdir()
            attempts = {f"att-{s}": {"step": s, "handle": "h" if handles else None,
                                     **({} if handles else {"executor": {"kind": "main-context"}})} for s in "ABJ"}
            (run_dir / "plan-dispatcher-state.json").write_text(json.dumps({
                "steps": {s: {"current_attempt": f"att-{s}"} for s in "ABJ"}, "attempts": attempts}))
            for step, (start, end) in stamps.items():
                (marks / f"{step}.json").write_text(json.dumps({"step": step, "start": start, "end": end}))
            return fanout.grade(dispatch, run_dir, marks)

    def test_parallel_fan_out_then_fan_in_passes(self):
        result = self.grade({"A": (0, 30), "B": (1, 31), "J": (32, 62)})
        self.assertTrue(result["pass"], result)
        self.assertTrue(result["fan_out_parallel"])
        self.assertEqual(result["fan_out_overlap_seconds"], 29.0)
        self.assertEqual(result["runner"], {"A": "native", "B": "native", "J": "native"})

    def test_sequential_steps_pass_the_order_but_report_no_fan_out(self):
        result = self.grade({"A": (0, 30), "B": (30, 60), "J": (61, 90)}, handles=False)
        self.assertTrue(result["pass"], result)
        self.assertFalse(result["fan_out_parallel"])
        self.assertEqual(result["runner"]["A"], "main-context")

    def test_join_before_both_suppliers_end_fails(self):
        result = self.grade({"A": (0, 30), "B": (1, 45), "J": (40, 70)})
        self.assertFalse(result["fan_in_order"])
        self.assertFalse(result["pass"])

    def test_incomplete_run_fails(self):
        result = self.grade({"A": (0, 30), "B": (1, 31)}, complete=False)
        self.assertFalse(result["pass"])
        self.assertFalse(result["complete"])

def write_stream_run(out: Path, stream: list, accepted: list, *, status: str = "done", stage: str | None = None,
                     inner: dict | None = None, first_event: float = 100.0,
                     rollout_files: list[list[str]] | None = None, started: float | bool | None = None,
                     binds: dict | None = None, timed: bool = True) -> Path:
    """The files of a run in `out`: the host stream with its runner timeline, ShipLoop's records and Codex rollouts.

    ``binds`` maps an action id to the modification time of its Improve child's `improve/<action>-bind.md`;
    ``timed=False`` leaves out the runner's timeline.jsonl. Returns the ShipLoop run directory."""
    for number, lines in enumerate(rollout_files or []):
        write_rollout(out, f"{number}", lines)
    run_dir = out / "run"
    (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in stream))
    if timed:
        (out / "timeline.jsonl").write_text("".join(
            json.dumps({"line": n, "t": first_event + n}) + "\n"
            for n, e in enumerate(stream) if e.get("type") not in ("text", "thought")))
    write_engine_records(run_dir, accepted, status=status, stage=stage, inner=inner, started=started)
    for action, mtime in (binds or {}).items():
        bind = run_dir / "improve" / f"{action}-bind.md"
        bind.parent.mkdir(parents=True, exist_ok=True)
        bind.write_text("bound\n")
        os.utime(bind, (mtime, mtime))
    return run_dir


def collect_stream(stream: list, accepted: list, **kw) -> dict:
    """metrics.collect over a hand-built host stream, one second between events, ShipLoop records beside it.

    ``rollout_files`` are Codex rollouts (one list of lines each) written under the run's own CODEX_HOME;
    the other keywords are write_stream_run's."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        run_dir = write_stream_run(out, stream, accepted, **kw)
        return metrics.collect(out, run_dir)


def codex_stream(commands: int) -> list[dict]:
    """What a Codex session looks like after the harness's translator: tool calls and one `end`, no usage events."""
    translate = hosts.host("codex").translator()
    raw = [{"type": "thread.started", "thread_id": "t1"}]
    raw += [{"type": "item.completed", "item": {"id": f"item_{n}", "type": "command_execution",
                                                "command": f"echo {n}", "aggregated_output": "ok\n",
                                                "exit_code": 0, "status": "completed"}} for n in range(commands)]
    raw.append({"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 5,
                                                    "output_tokens": 2}})
    return [json.loads(line) for event in raw for line in translate((json.dumps(event) + "\n").encode())]


def claude_stream(commands: list[str]) -> list[dict]:
    """A Claude session: tool calls are tool_use blocks, with a per-message usage snapshot."""
    stream = []
    for n, command in enumerate(commands):
        stream.append({"type": "assistant", "message": {
            "id": f"m{n}", "usage": {"input_tokens": 10, "output_tokens": 3},
            "content": [{"type": "tool_use", "id": f"u{n}", "name": "Bash", "input": {"command": command}}]}})
        stream.append({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": f"u{n}", "content": "error: refused"}]}})
    stream.append({"type": "result", "subtype": "success", "is_error": False, "terminal_reason": "completed",
                   "stop_reason": "end_turn", "num_turns": len(commands), "total_cost_usd": 1.0})
    return stream


# Claude calls recorded in the round-1 Sonnet runs, cut to a compact extract (docs/experiments/claude-tool-blocks-20261008).
TOOL_BLOCKS = ROOT / "docs" / "experiments" / "claude-tool-blocks-20261008"


def recorded_calls(*names: str, run: str = "battleship") -> list[dict]:
    """The recorded Claude events (a message's thinking event, its tool_use and the tool_result) of the named calls,
    in the order they were recorded. ``run`` is battleship or checkers."""
    file = f"{run}-sonnet-calls.jsonl"
    manifest = json.loads((TOOL_BLOCKS / "manifest.json").read_text())[file]
    events = [json.loads(line) for line in (TOOL_BLOCKS / file).read_text().splitlines()]
    return [events[n] for n in sorted({n for name in names for n in manifest[name]["lines"]})]


def recorded_command(name: str, run: str = "battleship") -> str:
    """The shell command of one recorded Bash call."""
    return next(b["input"]["command"] for e in recorded_calls(name, run=run) if e["type"] == "assistant"
                for b in e["message"]["content"] if b["type"] == "tool_use")


def with_command(events: list[dict], command: str) -> list[dict]:
    """The same recorded events with the Bash command of their tool_use replaced (its result is kept as recorded)."""
    events = json.loads(json.dumps(events))
    for e in events:
        for b in e["message"]["content"] if e["type"] == "assistant" else []:
            if b["type"] == "tool_use":
                b["input"]["command"] = command
    return events


def with_result(events: list[dict], text: str) -> list[dict]:
    """The same recorded events with the text of their last tool_result replaced."""
    events = json.loads(json.dumps(events))
    last = [b for e in events if e["type"] == "user" for b in e["message"]["content"]][-1]
    last["content"] = text
    return events


CLAUDE_END = {"type": "result", "subtype": "success", "is_error": False, "terminal_reason": "completed",
              "stop_reason": "end_turn", "num_turns": 1, "total_cost_usd": 1.0}


class HostCoverageTest(unittest.TestCase):
    """A counter the host's events cannot show is unmeasured, never a zero that passes a comparison."""

    ACCEPTED = [("A1", "intake", "done", 105.0), ("A2", "spec", "done", 113.0)]

    def test_a_host_with_no_per_call_usage_has_no_stage_turns_not_zero_turns(self):
        m = collect_stream(codex_stream(12), self.ACCEPTED)
        self.assertIn("stage_turns", m["unmeasured"])
        self.assertNotIn("model_glue", m["unmeasured"])  # Codex's tool calls are parsed
        self.assertEqual([r["seconds"] for r in m["stages"]], [5.0, 8.0])  # time is still measured
        for row in m["stages"]:
            self.assertIsNone(row["turns"])
            self.assertGreater(row["tool_calls"], 0)
        self.assertEqual(m["turns"], 12)  # the session's own total is still reported
        self.assertEqual(m["tokens"], {"input_peak": None})  # no output figure is built from events
        self.assertIsNone(m["cost_usd"], "a host that reports no cost has an unknown cost, not $0")
        kept = run.baseline_stages(m["stages"])
        self.assertEqual(kept[0], {"stage": "intake", "outcome": "done", "seconds": 5.0, "turns": None})

    def test_the_stage_a_codex_run_never_accepted_is_attributed_from_its_events(self):
        m = collect_stream(codex_stream(12), self.ACCEPTED[:1], status="active", stage="spec")
        incomplete = [r for r in m["stages"] if r.get("incomplete")]
        self.assertEqual([r["stage"] for r in incomplete], ["spec"])
        self.assertGreater(incomplete[0]["seconds"], 0)
        self.assertGreater(incomplete[0]["tool_calls"], 0)
        self.assertIsNone(incomplete[0]["turns"])

    def test_a_claude_stream_measures_its_tool_calls_and_leaves_the_grok_only_counters_unmeasured(self):
        stream = claude_stream(["git add -A && git commit -m x", "shiploop complete --run-dir r"] * 3)
        m = collect_stream(stream, self.ACCEPTED)
        for name in ("cancelled_tool_calls", "knowledge_reads", "compactions", "truncated_outputs"):
            self.assertIn(name, m["unmeasured"], name)
        for name in ("model_glue", "shiploop_failures", "tmp_writes", "stage_tool_calls"):
            self.assertNotIn(name, m["unmeasured"], name)
        self.assertNotIn("stage_turns", m["unmeasured"])
        self.assertEqual(len(m["model_glue"]), 3, "three git commands by the model")
        self.assertEqual(m["shiploop_failures"], [], "'error: refused' is no ShipLoop refusal line and carries no exit code")
        self.assertEqual([(r["tool_calls"], r["turns"] is not None) for r in m["stages"]], [(3, True), (3, True)])
        self.assertEqual(m["tokens"], {"input_peak": 10})
        self.assertEqual(metrics.count(m, "model_glue"), 3)
        self.assertEqual(metrics.count({"unmeasured": {}, "model_glue": [1, 2]}, "model_glue"), 2)
        first = metrics.summary_lines(m)[0]
        self.assertIn("model glue 3", first)
        self.assertIn("ShipLoop command failures 0", first)
        self.assertIn("cancelled tool calls not measured", first)

    def test_a_grok_shaped_stream_measures_every_counter(self):
        stream = [{"type": "usage", "usage": {"input_tokens": 1, "output_tokens": 1}},
                  {"type": "tool_call", "toolCallId": "a", "rawInput": {"command": "git add -A"}}] * 4
        # Every counter: the detectors read Grok's events. (A context window is a figure Grok never reports, and nothing in
        # its events marks a session start, so the count of sessions that never reported is unmeasured too.)
        self.assertEqual(set(collect_stream(stream, self.ACCEPTED)["unmeasured"]), {"window_tokens", "unreported_sessions"})

    def test_the_baseline_row_carries_unmeasured_counters_as_null_with_their_names(self):
        result = {"case": "hello", "metrics": {"turns": 5, "cost_usd": None, "model_glue": None,
                                               "shiploop_failures": None, "stages": [],
                                               "unmeasured": {"model_glue": "why", "shiploop_failures": "why"}}}
        row = run.baseline_row(result, None, None)
        self.assertIsNone(row["model_glue"])
        self.assertIsNone(row["shiploop_failures"])
        self.assertEqual(row["unmeasured"], ["model_glue", "shiploop_failures"])
        self.assertEqual(run.baseline_row({"case": "hello", "metrics": {}}, None, None)["unmeasured"], [])

    def test_the_costliest_stages_rank_by_minutes_when_the_host_reports_no_turns(self):
        rows = [{"stage": "intake", "seconds": 60.0, "turns": None}, {"stage": "plan", "seconds": 6000.0, "turns": None},
                {"stage": "spec", "seconds": 600.0, "turns": None}]
        m = {"turns": 9, "cost_usd": None, "sessions": [], "compactions": 0, "truncated_outputs": 0,
             "cancelled_tool_calls": [], "shiploop_failures": [], "model_glue": [], "asked_user": [],
             "improve_children": 0, "script_verifications": {"passed": 0, "records": 0}, "stages": rows,
             "unmeasured": {"stage_turns": "x"}}
        costly = metrics.summary_lines(m)[-1]
        self.assertTrue(costly.startswith("costliest stages: plan 100.0m, spec 10.0m, intake 1.0m"), costly)
        self.assertIn("this host reports no per-stage turns", costly)
        self.assertIn("cost not reported", metrics.summary_lines(m)[0])

    def test_progress_prints_minutes_and_the_inner_loop_stage_for_a_host_without_turns(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_dir = out / "run"
            stream = codex_stream(12)
            (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in stream))
            (out / "timeline.jsonl").write_text("".join(
                json.dumps({"line": n, "t": 100.0 + 30 * n}) + "\n" for n in range(len(stream))))
            write_engine_records(run_dir, [("A1", "intake", "done", 190.0)], status="active", stage="inner-loop",
                                 inner={"work_index": 0, "work_items": [{"id": "W1"}],
                                        "inner_loops": {"W1": {"stage": "implement"}}})
            text = progress.report(out)
        self.assertIn("accepted: intake 1.5m", text)
        # The stage still being worked has a row that moves with every poll: it is not listed as accepted.
        self.assertNotIn("implement", next(line for line in text.splitlines() if "accepted:" in line))
        self.assertNotIn("intake 0t", text)
        self.assertIn("peak context n/a", text)
        # The in-progress stage is the item's own, not the navigator's pseudo-label.
        self.assertIn("stage implement", text)
        self.assertNotIn("stage inner-loop", text)


class ClaudeToolBlocksTest(unittest.TestCase):
    """Claude's tool_use and tool_result blocks go through the one classifier Grok's tool_call events do: failures, model
    glue, /tmp writes and per-stage tool calls are measured. The calls are recorded ones, from the round-1 Sonnet runs
    (docs/experiments/claude-tool-blocks-20261008, cut by its extract.py); a few are rewritten, as the test says."""

    def collect(self, events: list[dict], accepted: list | None = None, **kw) -> dict:
        accepted = accepted or [("A1", "intake", "done", 100.0 + len(events) + 2)]
        return collect_stream([*events, CLAUDE_END], accepted, **kw)

    def failures(self, *names: str) -> list[dict]:
        return self.collect(recorded_calls(*names))["shiploop_failures"]

    def test_a_refusal_behind_a_pipe_is_a_shiploop_failure_with_its_verb_and_no_exit(self):
        found = self.failures("refusal-behind-head")
        self.assertEqual([(f["verb"], f["exit"]) for f in found], [("complete", None)], "the host showed no exit code")
        # The result also holds the shell's own "no such file" line before the refusal: the refusal is the line recorded.
        self.assertTrue(found[0]["line"].startswith(
            "ShipLoop navigator: evidence_refs cite files that do not exist: "), found)
        knowledge = self.failures("refusal-knowledge-file")
        self.assertEqual([(f["verb"], f["exit"]) for f in knowledge], [("complete", None)])
        self.assertTrue(knowledge[0]["line"].startswith("ShipLoop navigator: ShipLoop keeps this run's planning knowledge"))

    def test_the_workspace_block_is_a_refusal_line_and_the_script_prints_it(self):
        found = self.failures("workspace-blocked-plan", "workspace-blocked-status")
        self.assertEqual([(f["verb"], f["exit"]) for f in found], [("workspace", None)] * 2)
        self.assertEqual([f["line"] for f in found],
                         ["ShipLoop workspace blocked: return plan has unresolved path dispositions",
                          "ShipLoop workspace blocked: return plan has an invalid status"])
        source = " ".join((ROOT / "skills/shiploop/scripts/shiploop_protocol.py").read_text().split())
        self.assertIn('f"ShipLoop workspace blocked: {exc}"', source, "the prefix is copied from the script's own text")
        self.assertRegex("ShipLoop workspace blocked: x", metrics.REFUSAL_LINE)

    def test_a_prefix_inside_a_line_and_a_failed_command_that_is_not_shiploop_are_not_failures(self):
        refusal = "ShipLoop navigator: result requires outcome and summary"
        for text in ("quoted: " + refusal, "  " + refusal, "# " + refusal):
            with self.subTest(text):
                events = with_result(recorded_calls("sed-a-packet"), "before\n" + text + "\nafter\n")
                self.assertEqual(self.collect(events)["shiploop_failures"], [])
        # Recorded `Exit code 1` results of commands that name no ShipLoop verb: a sed of a SKILL.md, and the model's own
        # helper script failing on a missing file (the body it wrote, earlier, names no verb). A host refusal is no ShipLoop one.
        self.assertEqual(self.failures("exit-1-not-shiploop"), [])
        self.assertEqual(self.failures("write-idone", "run-idone-exit-1"), [])
        self.assertEqual(self.failures("edit-tool-error"), [])

    def test_the_anchored_line_alone_decides_a_refusal_whatever_command_produced_it(self):
        events = with_result(recorded_calls("sed-a-packet"), "ShipLoop navigator: x\nmore\n")
        self.assertEqual(self.collect(events)["shiploop_failures"], [{"verb": "unknown", "exit": None, "line": "ShipLoop navigator: x"}])

    def test_a_nonzero_exit_of_a_shiploop_command_keeps_its_exit_code(self):
        command = ("CLI=/runs/r1/build/plugins/skill-craft/skills/shiploop/scripts/shiploop\n"
                   "python3 $CLI complete --run-dir=/runs/r1/run")
        found = self.collect(with_command(recorded_calls("exit-1-not-shiploop"), command))["shiploop_failures"]
        self.assertEqual([(f["verb"], f["exit"]) for f in found], [("complete", 1)])
        # Through a script the model wrote, whose body names the verb: the exit is kept, the verb is not guessed.
        events = [*recorded_calls("write-and-run-sub"), *with_result(recorded_calls("run-sub-piped"), "Exit code 2\nboom")]
        found = self.collect(events)["shiploop_failures"]
        self.assertEqual([(f["verb"], f["exit"], f["line"]) for f in found], [("unknown", 2, "")])

    def test_one_failure_is_one_tool_result_however_many_refusal_lines_it_holds(self):
        text = "ShipLoop navigator: first\nShipLoop navigator: second\n"
        found = self.collect(with_result(recorded_calls("refusal-knowledge-file"), text))["shiploop_failures"]
        self.assertEqual([f["line"] for f in found], ["ShipLoop navigator: first"])

    def test_a_refusal_is_recorded_from_its_own_line_not_from_an_earlier_line_of_the_models_output(self):
        # An earlier line that names an error ("KeyError", "required") is the model's own script failing, not why ShipLoop
        # refused; failure_line alone would pick it. The line recorded starts at the refusal line.
        refusal = "ShipLoop navigator: result requires outcome and summary"
        text = "Traceback (most recent call last):\nKeyError: 'outcome'\n" + refusal + "\nmore\n"
        found = self.collect(with_result(recorded_calls("sed-a-packet"), text))["shiploop_failures"]
        self.assertEqual([f["line"] for f in found], [refusal])
        # With no refusal line the whole text is read: a nonzero exit of a ShipLoop command keeps its first error line.
        command = "CLI=/runs/r1/build/plugins/skill-craft/skills/shiploop/scripts/shiploop\npython3 $CLI next --run-dir=/runs/r1/run"
        events = with_command(with_result(recorded_calls("sed-a-packet"), "Exit code 1\nKeyError: 'x'\n"), command)
        self.assertEqual([(f["exit"], f["line"]) for f in self.collect(events)["shiploop_failures"]], [(1, "KeyError: 'x'")])

    def test_an_exit_line_quoted_in_the_middle_of_a_result_is_not_the_hosts_exit(self):
        # The host's `Exit code N` is the first line of the result; a result that quotes one later (a document, a log) is
        # not a failed command.
        self.assertEqual(metrics.claude_exit("Exit code 2\nboom"), 2)
        self.assertIsNone(metrics.claude_exit("fine\nExit code 1 means the run is blocked\n"))
        self.assertIsNone(metrics.claude_exit("fine"))
        command = "CLI=/runs/r1/build/plugins/skill-craft/skills/shiploop/scripts/shiploop\npython3 $CLI next --run-dir=/runs/r1/run"
        events = with_command(with_result(recorded_calls("sed-a-packet"), "packet text\nExit code 1 is quoted here\n"), command)
        self.assertEqual(self.collect(events)["shiploop_failures"], [])

    def test_a_host_that_numbers_its_calls_again_in_each_session_has_every_failure_counted(self):
        # Codex ids restart at item_0 in every session (the recorded Luna run v1210 has 1542 tool_call events and 486
        # distinct ids). A failure is counted once per call, so a second call that reuses an id is a failure of its own.
        cli = "python3 x/shiploop next --run-dir r"
        refusal = "ShipLoop navigator: no ShipLoop run directory"
        first = codex_session([codex_command(0, cli, refusal + "\n", 2)])
        second = codex_session([codex_command(0, cli, refusal + "\n", 2)], thread="t2")
        found = collect_stream([*first, *second], [])["shiploop_failures"]
        self.assertEqual([(f["verb"], f["exit"], f["line"]) for f in found], [("next", 2, refusal)] * 2)
        # One call is still one failure when the host repeats its update (Grok), even with an id that came back.
        update = {"type": "tool_call_update", "toolCallId": "g", "status": "completed",
                  "rawOutput": {"exit_code": 2, "output_for_prompt": refusal + "\n"}}
        grok = [{"type": "tool_call", "toolCallId": "g", "rawInput": {"command": cli}}, update, update]
        self.assertEqual(len(collect_stream(grok, [])["shiploop_failures"]), 1)

    def test_the_same_rule_reads_a_grok_and_a_codex_stream(self):
        refusal = "ShipLoop blocked: the run directory is not readable"
        cli = "python3 x/shiploop next --run-dir r | head"
        grok = [{"type": "tool_call", "toolCallId": "a", "rawInput": {"command": cli}},
                {"type": "tool_call_update", "toolCallId": "a", "status": "completed",
                 "rawOutput": {"exit_code": 0, "output_for_prompt": refusal + "\n"}},
                {"type": "tool_call", "toolCallId": "b", "rawInput": {"command": cli}},
                {"type": "tool_call_update", "toolCallId": "b", "status": "completed",
                 "rawOutput": {"exit_code": 0, "output_for_prompt": "fine\n"}}]
        codex = codex_session([codex_command(0, cli, refusal + "\n", 0), codex_command(1, cli, "fine\n", 0)])
        for label, stream in (("grok", grok), ("codex", codex)):
            with self.subTest(label):
                self.assertEqual(collect_stream(stream, [])["shiploop_failures"],
                                 [{"verb": "next", "exit": 0, "line": refusal}])

    def test_a_grok_call_is_read_from_its_final_update_not_the_running_one(self):
        # The shape of a recorded Grok call (v1210, a refused `complete`): running updates carry a placeholder exit 0 and the
        # output so far, the completed update the real exit 2. One call, one failure, with the exit the host reported last.
        cli = "python3 x/shiploop complete --run-dir r"
        refusal = "ShipLoop navigator: result requires outcome and summary"
        stream = [{"type": "tool_call", "toolCallId": "a", "rawInput": {"command": cli}},
                  {"type": "tool_call_update", "toolCallId": "a", "status": "in_progress",
                   "rawOutput": {"exit_code": 0, "output_for_prompt": ""}},
                  {"type": "tool_call_update", "toolCallId": "a", "status": "in_progress",
                   "rawOutput": {"exit_code": 0, "output_for_prompt": refusal + "\n"}},
                  {"type": "tool_call_update", "toolCallId": "a", "status": "completed",
                   "rawOutput": {"exit_code": 2, "output_for_prompt": refusal + "\n"}}]
        self.assertEqual(collect_stream(stream, [])["shiploop_failures"], [{"verb": "complete", "exit": 2, "line": refusal}])

    def test_model_glue_and_tmp_writes_see_through_command_variables(self):
        names = list(json.loads((TOOL_BLOCKS / "manifest.json").read_text())["battleship-sonnet-calls.jsonl"])
        m = self.collect(recorded_calls(*names))
        # Recorded: one git commit by the model (`git -C $WT add` and `commit`); the notes, inbox and scratch writes are
        # what the packets ask for, so they are no glue.
        self.assertEqual([g["reasons"] for g in m["model_glue"]], [["git commit/add by the model"]])
        self.assertEqual(m["tmp_writes"], [])
        for name in ("stage_tool_calls", "model_glue", "tmp_writes", "shiploop_failures"):
            self.assertNotIn(name, m["unmeasured"], name)
        derived = ("RUN=/runs/r1/.shiploop-runs/work-1/run\ncat > $RUN/state.md <<EOF\nx\nEOF\n"
                   "T=/tmp/bs.pid; echo 1 > $T\necho 2 > /tmp/bs.log")
        m = self.collect(with_command(recorded_calls("sed-a-packet"), derived))
        self.assertEqual([g["reasons"] for g in m["model_glue"]], [["shell write into a ShipLoop-owned path"]])
        self.assertEqual(m["tmp_writes"], ["/tmp/bs.log", "/tmp/bs.pid"])

    def test_an_assignment_inside_a_quoted_sh_c_does_not_replace_the_real_one(self):
        command = recorded_command("assignment-shadowed-by-sh-c", run="checkers")
        variables = metrics.shell_variables(command)
        # `R=<run dir>` is assigned first; the quoted sh -c then says `R=$?` and `P=$!`, which are not values.
        self.assertEqual(variables["R"], "/runs/r2/.shiploop-runs/work-1/run")
        self.assertNotIn("P", variables)
        self.assertIn(" /runs/r2/.shiploop-runs/work-1/run/scratch/sub.sh ", " " + metrics.expand_variables(command, variables))
        self.assertEqual(metrics.shell_variables("A=$B/x; B=/y; C=$B/z"), {"B": "/y", "C": "/y/z"},
                         "a value that names a variable not yet assigned is not recorded")

    def test_a_path_through_the_run_directory_to_its_sibling_is_the_product_worktree_not_a_shiploop_path(self):
        # Recorded in Batch 1003 (seat-reservations, v1161-hello): `W=$R/../worktree` then writes under $W. The worktree
        # beside the run directory is product space; before the path was resolved it matched the run directory's prefix.
        run = "/runs/r1/.shiploop-runs/work-1/run"
        sibling = (f"B={run}; W=$B/../worktree; F=$W/docs/shiploop/features/x\n"
                   "cat >> $W/docs/shiploop/environment.md <<'EOF'\nruntime facts\nEOF\n"
                   "printf 'learned' >> $F/plan.md\nrm -rf $B/../worktree/__pycache__")
        self.assertEqual(self.collect(with_command(recorded_calls("sed-a-packet"), sibling))["model_glue"], [])
        # A path that leaves the run directory and comes back into it is still the run directory.
        back = f"B={run}; cat > $B/../run/state.md <<'EOF'\nx\nEOF"
        glue = self.collect(with_command(recorded_calls("sed-a-packet"), back))["model_glue"]
        self.assertEqual([g["reasons"] for g in glue], [["shell write into a ShipLoop-owned path"]])
        self.assertEqual(metrics.expand_variables("$A/b/../c /d/e/f/../../g /h/i/.. /../j", {"A": "/x"}),
                         "/x/c /d/g /h /../j", "a segment is dropped with its `..`; one that leads the path is left as written")
        self.assertEqual(metrics.shell_variables("B=/x/run; W=$B/../worktree")["W"], "/x/worktree")

    def test_compactions_cancelled_calls_and_knowledge_reads_stay_unmeasured_for_claude(self):
        compact = {"type": "system", "subtype": "compact_boundary", "compact_metadata": {"trigger": "auto"}}
        m = self.collect([compact, *recorded_calls("read-packet-whole", "refusal-behind-head")])
        for name in ("compactions", "cancelled_tool_calls", "knowledge_reads", "truncated_outputs"):
            self.assertIn(name, m["unmeasured"], name)
        self.assertEqual((m["cancelled_tool_calls"], m["knowledge_reads"]), ([], []))

    def test_the_run_review_export_shows_a_claude_runs_refusals_and_glue(self):
        # The exporter (skills/shiploop-run-review, unmodified) reads shiploop_failures and model_glue from metrics.json and
        # omits a count only when `unmeasured` names it: a Claude run's refusals and glue now reach the page.
        names = list(json.loads((TOOL_BLOCKS / "manifest.json").read_text())["battleship-sonnet-calls.jsonl"])
        events = [*recorded_calls(*names), CLAUDE_END]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "graded"
            out.mkdir()
            written = write_stream_run(out, events, [("A1", "intake", "done", 110.0), ("A2", "spec", "done", 140.0)])
            (out / ".shiploop-runs" / "work-1").mkdir(parents=True)
            run_dir = written.rename(out / ".shiploop-runs" / "work-1" / "run")  # where the exporter looks for it
            (run_dir / "results").mkdir()
            found = metrics.collect(out, run_dir)
            (out / "metrics.json").write_text(json.dumps(found))
            self.assertTrue(run.review_export(out).startswith("review export: "), run.review_export(out))
            bundle = json.loads((out / "review-export" / "review-export.json").read_text())
        exported = next(iter(bundle["docs"]["runs"].values()))
        self.assertEqual(exported["refusals"], len(found["shiploop_failures"]))
        self.assertGreater(exported["refusals"], 0)
        self.assertEqual(exported["glue"], len(found["model_glue"]))
        for name in ("shiploop_failures", "model_glue"):
            self.assertNotIn(name, exported["unmeasured"], name)
        self.assertEqual([stage["context"]["calls"] for stage in exported["stages"]], [found["stages"][0]["context"]["calls"],
                                                                                       found["stages"][1]["context"]["calls"]])
        self.assertNotIn("visitContext", exported["unmeasured"])

    def test_stage_rows_count_model_calls_and_their_peak_context_not_events(self):
        # Claude writes one event per content block: 30 assistant events here are 16 messages, and a stage's calls are the
        # messages whose first event falls in its window. The context window is the one the result event names.
        ended = dict(CLAUDE_END, modelUsage={"claude-sonnet-5-5": {"contextWindow": 1000000}})
        names = list(json.loads((TOOL_BLOCKS / "manifest.json").read_text())["battleship-sonnet-calls.jsonl"])
        events = [*recorded_calls(*names), ended]
        m = collect_stream(events, [("A1", "intake", "done", 115.0), ("A2", "spec", "done", 130.0),
                                    ("A3", "plan", "done", 200.0)])
        self.assertEqual([r["context"] for r in m["stages"]],
                         [{"calls": 6, "peak": 103290, "peakPct": 10.3}, {"calls": 4, "peak": 184145, "peakPct": 18.4},
                          {"calls": 6, "peak": 231581, "peakPct": 23.2}])
        self.assertEqual([r["turns"] for r in m["stages"]], [11, 9, 10], "turns keep counting events")
        self.assertEqual([r["tool_calls"] for r in m["stages"]], [6, 5, 6])
        self.assertEqual(m["model_calls"], 16)
        self.assertEqual(sum(r["context"]["calls"] for r in m["stages"]), 16, "the last stage ends after the last event")
        self.assertEqual(m["tokens"]["input_peak"], 231581)
        # A call after the last accepted stage is in no window, so the stages hold fewer calls than the run.
        cut = collect_stream(events, [("A1", "intake", "done", 115.0), ("A2", "spec", "done", 130.0)])
        self.assertEqual(sum(r["context"]["calls"] for r in cut["stages"]), 10)
        self.assertEqual(cut["model_calls"], 16)
        # A stage the timeline cannot place has no context, and a run with no window figure has no percentage.
        unplaced = collect_stream([*events[:-1], CLAUDE_END], [("A1", "intake", "done", 115.0)], timed=False)
        self.assertTrue(all("context" not in r for r in unplaced["stages"]), unplaced["stages"])
        self.assertIsNone(collect_stream([*events[:-1], CLAUDE_END], [("A1", "intake", "done", 115.0)])["stages"][0]["context"]["peakPct"])

    def all_calls(self) -> list[dict]:
        return recorded_calls(*json.loads((TOOL_BLOCKS / "manifest.json").read_text())["battleship-sonnet-calls.jsonl"])

    def test_the_tool_use_block_counts_calls_by_tool_and_the_characters_they_returned(self):
        use = self.collect(self.all_calls())["tool_use"]
        self.assertEqual((use["calls"], use["by_tool"], use["result_chars"]), (17, {"Bash": 13, "Edit": 1, "Read": 3}, 5753))
        none = self.collect([{"type": "assistant", "message": {"id": "m1", "usage": {"input_tokens": 1}, "content": [
            {"type": "text", "text": "hello"}]}}])["tool_use"]
        self.assertEqual((none["calls"], none["by_tool"], none["result_chars"], none["scratch_scripts"]), (0, {}, 0, []),
                         "a Claude stream with no tool call is a measured none")

    def test_scratch_scripts_list_what_the_model_wrote_and_how_many_calls_ran_it(self):
        run = "/runs/r1/.shiploop-runs/work-1/run/scratch/"
        found = self.collect(self.all_calls())["tool_use"]["scratch_scripts"]
        # sub.sh is written and run in one call, then run in another; idone.py is run once; istart.sh once (its heredoc
        # holds `improve-start`). The notes and inbox files the model also wrote with heredocs are documents, not scripts.
        self.assertEqual(found, [{"path": run + "idone.py", "bytes": 443, "wraps_shiploop": False, "runs": 1},
                                 {"path": run + "istart.sh", "bytes": 943, "wraps_shiploop": True, "runs": 1},
                                 {"path": run + "sub.sh", "bytes": 548, "wraps_shiploop": True, "runs": 2}])
        # Runs are tool calls: two invocation lines in one call are one run; a path used as an argument or as a
        # `--result=` value, and a script never invoked, are not runs.
        derived = ("RUN=/runs/r1/.shiploop-runs/work-1/run\n$RUN/scratch/sub.sh a b\ncd /x && $RUN/scratch/sub.sh c d\n"
                   "ls -l $RUN/scratch/sub.sh\ncat $RUN/scratch/sub.sh | head -3\n"
                   "python3 $CLI complete --result=$RUN/scratch/sub.sh")
        events = [*recorded_calls("write-and-run-sub"), *with_command(recorded_calls("run-sub-piped"), derived)]
        scripts = self.collect(events)["tool_use"]["scratch_scripts"]
        self.assertEqual([(s["path"].rsplit("/", 1)[1], s["runs"]) for s in scripts], [("sub.sh", 2)])

    def test_a_script_is_listed_only_when_a_call_ran_it_and_outside_scratch_only_when_it_wraps_the_cli(self):
        run = "/runs/r1/.shiploop-runs/work-1/run"
        write = ("RUN=" + run + "\ncat > $RUN/scratch/never.sh <<'EOF'\n#!/bin/sh\necho never run\nEOF\n"
                 "cat > /runs/r1/helper.sh <<'EOF'\n#!/bin/sh\npython3 /runs/r1/build/scripts/shiploop complete --run-dir=$1\nEOF\n"
                 "cat > /runs/r1/plain.sh <<'EOF'\n#!/bin/sh\necho plain\nEOF\n"
                 "/runs/r1/helper.sh a")
        scripts = self.collect(with_command(recorded_calls("sed-a-packet"), write))["tool_use"]["scratch_scripts"]
        # never.sh was written in the scratch folder and never run, plain.sh does not wrap the CLI and lives outside scratch;
        # helper.sh wraps the CLI, so it is listed wherever it lives.
        self.assertEqual([(s["path"], s["wraps_shiploop"], s["runs"]) for s in scripts], [("/runs/r1/helper.sh", True, 1)])
        # Run, the scratch script that does not wrap the CLI is listed too (idone.py in the recorded run).
        ran = write + "\n$RUN/scratch/never.sh\n/runs/r1/plain.sh"
        scripts = self.collect(with_command(recorded_calls("sed-a-packet"), ran))["tool_use"]["scratch_scripts"]
        self.assertEqual([(s["path"].rsplit("/", 1)[1], s["wraps_shiploop"], s["runs"]) for s in scripts],
                         [("never.sh", False, 1), ("helper.sh", True, 1)], "plain.sh is outside scratch and wraps nothing")

    def test_packet_use_counts_printed_heads_reads_and_the_packets_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            events = [*self.all_calls(), CLAUDE_END]
            run_dir = write_stream_run(out, events, [("A1", "intake", "done", 150.0)])
            self.assertIsNone(metrics.collect(out, run_dir)["tool_use"]["packets"]["on_disk"], "no packets folder")
            (run_dir / "packets").mkdir()
            for name, size in (("nav-1.md", 1000), ("nav-2.md", 2500), ("nav-3.md", 40)):
                (run_dir / "packets" / name).write_text("x" * size)
            (run_dir / "packets" / "ignored.json").write_text("{}")
            packets = metrics.collect(out, run_dir)["tool_use"]["packets"]
        # Printed: results that show a packet head (ShipLoop navigator | stage |) from calls that do not name a packet file.
        self.assertEqual(packets["printed"], {"replies": 3, "chars": 322 + 322 + 249})
        self.assertEqual(packets["read"]["read_tool"], [
            {"packet": "nav-b5efb9acc5be4d4a95a7c8ccc924f360", "whole": True, "chars": 323},
            {"packet": "nav-80a00f1aba124ef8923838789237eba9", "whole": False, "chars": 322},
            {"packet": "nav-80a00f1aba124ef8923838789237eba9", "whole": False, "chars": 322}])
        self.assertEqual(packets["read"]["shell"], {"calls": 1, "chars": 399})
        self.assertEqual(packets["on_disk"], {"files": 3, "bytes": 3540})

    def test_other_hosts_have_no_tool_use_block(self):
        grok = [{"type": "usage", "usage": {"input_tokens": 1, "output_tokens": 1}},
                {"type": "tool_call", "toolCallId": "a", "rawInput": {"command": "ls"}}]
        for label, stream in (("grok", grok), ("codex", codex_stream(3))):
            m = collect_stream(stream, [])
            self.assertIsNone(m["tool_use"], label)
            self.assertNotIn("tool_use", m["unmeasured"], "no host but Claude ever had this block: nothing to name")

    def test_the_summary_says_what_the_model_ran_beside_the_glue_count(self):
        lines = metrics.summary_lines(self.collect(self.all_calls()))
        use = next(line for line in lines if line.startswith("tool use (main thread):"))
        for text in ("17 calls (Bash 13, Read 3, Edit 1)", "5,753 result chars", "sub.sh 2 runs (wraps ShipLoop)",
                     "idone.py 1 run", "istart.sh 1 run (wraps ShipLoop)", "not counted in model glue",
                     "3 printed packet replies (893 chars)", "3 packet Reads (1 whole)", "1 shell command on packets (399 chars)"):
            self.assertIn(text, use)
        self.assertFalse(any(line.startswith("tool use") for line in metrics.summary_lines(collect_stream(codex_stream(2), []))))

    def test_progress_names_a_claude_refusal_and_does_not_print_an_exit_that_was_not_shown(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in recorded_calls("refusal-behind-head")))
            text = progress.report(out)
        self.assertIn("ShipLoop complete failed (exit not shown): ShipLoop navigator: evidence_refs cite files", text)
        self.assertNotIn("exit None", text)
        self.assertEqual(metrics.failure_text({"verb": "next", "exit": 2, "line": ""}), "exit 2")
        self.assertEqual(metrics.failure_text({"verb": "next", "exit": None, "line": ""}), "exit not shown")



class StageDiffTest(unittest.TestCase):
    """A stage row that is incomplete or unmeasured is never compared as a whole measurement."""

    def test_an_incomplete_row_on_either_side_is_not_compared_as_a_stage(self):
        cut = [{"stage": "spec", "turns": 10, "seconds": 60}, {"stage": "implement", "incomplete": True,
                                                              "turns": 5, "seconds": 30}]
        whole = [{"stage": "spec", "turns": 10, "seconds": 60}, {"stage": "implement", "turns": 50, "seconds": 600}]
        for before, now in ((cut, whole), (whole, cut)):
            text = "\n".join(run.stage_diff_lines(before, now))
            self.assertNotIn("implement 5->50", text)
            self.assertNotIn("implement 50->5", text)
            self.assertIn("covers 1 of 2 stages (1 not comparable", text)
            self.assertIn("implement", text.split("not comparable")[1])
            self.assertNotIn("only now", text)
            self.assertNotIn("only before", text)

    def test_a_stage_unmeasured_on_the_baseline_is_not_reported_as_new(self):
        before = [{"stage": "spec", "turns": 10, "seconds": 60}, {"stage": "plan", "timing": "unavailable"}]
        now = [{"stage": "spec", "turns": 10, "seconds": 60}, {"stage": "plan", "turns": 8, "seconds": 90}]
        text = "\n".join(run.stage_diff_lines(before, now))
        self.assertNotIn("only now", text)
        self.assertIn("covers 1 of 2 stages", text)  # coverage is stated for the baseline side too
        reverse = "\n".join(run.stage_diff_lines(now, before))
        self.assertNotIn("only before", reverse)
        self.assertIn("covers 1 of 2 stages", reverse)

    def test_a_stage_with_one_unmeasured_visit_is_not_summed_as_if_whole(self):
        spec = {"stage": "spec", "turns": 1, "seconds": 6}
        before = [spec, {"stage": "implement", "turns": 5, "seconds": 60}, {"stage": "implement", "timing": "unavailable"}]
        now = [spec, {"stage": "implement", "turns": 5, "seconds": 60}, {"stage": "implement", "turns": 9, "seconds": 90}]
        text = "\n".join(run.stage_diff_lines(before, now))
        self.assertNotIn("implement 5->14", text)
        self.assertIn("1 not comparable", text)
        self.assertEqual(run.stage_diff_lines([{"stage": "implement", "timing": "unavailable"}], now),
                         ["per-stage comparison unavailable (one run has no measured stage timing)"])

    def test_a_true_one_sided_stage_is_still_reported_with_its_coverage(self):
        before = [{"stage": "spec", "turns": 1, "seconds": 6}, {"stage": "plan", "turns": 1, "seconds": 6}]
        now = [{"stage": "spec", "turns": 1, "seconds": 6}, {"stage": "implement", "turns": 1, "seconds": 6}]
        lines = run.stage_diff_lines(before, now)
        self.assertEqual(lines[0], "per-stage comparison covers 1 of 3 stages")
        self.assertIn("only now: implement", lines)
        self.assertIn("only before: plan", lines)

    def test_a_host_with_no_stage_turns_is_compared_by_minutes_not_called_unchanged(self):
        before = [{"stage": "plan", "turns": None, "seconds": 6000}, {"stage": "spec", "turns": None, "seconds": 600}]
        now = [{"stage": "plan", "turns": None, "seconds": 36000}, {"stage": "spec", "turns": None, "seconds": 600}]
        lines = run.stage_diff_lines(before, now)
        self.assertEqual(lines, ["stage minutes (this host reports no per-stage turns): plan 100->600"])
        self.assertEqual(run.stage_diff_lines(before, before), ["no per-stage minute difference (turns not measured)"])
        mixed = run.stage_diff_lines(before, [{"stage": "plan", "turns": 4, "seconds": 36000},
                                              {"stage": "spec", "turns": 2, "seconds": 600}])
        self.assertEqual(len(mixed), 1)
        self.assertTrue(mixed[0].startswith("stage minutes"), mixed)  # a turn count on one side only is no comparison

    def test_short_stages_show_their_seconds_not_a_rounded_minute(self):
        lines = run.stage_diff_lines([{"stage": "spec", "turns": 3, "seconds": 30}],
                                     [{"stage": "spec", "turns": 4, "seconds": 40}])
        self.assertEqual(lines, ["stage turns: spec 3->4 (0.5->0.7m)"])


class SessionStopTest(unittest.TestCase):
    """The stop reason is the host's own, and an error is never recorded as a success."""

    CLAUDE_API_ERROR = {"type": "result", "subtype": "success", "is_error": True, "terminal_reason": "api_error",
                        "api_error_status": None, "stop_reason": "stop_sequence", "num_turns": 143,
                        "result": "API Error: Unable to connect to API: SSL certificate has expired"}

    def test_a_claude_api_error_is_not_a_success(self):
        stop = metrics.session_stop(self.CLAUDE_API_ERROR)
        self.assertTrue(stop.startswith("error: api_error"), stop)
        self.assertIn("SSL certificate has expired", stop)
        limited = dict(self.CLAUDE_API_ERROR, api_error_status=429, result="You've hit your limit")
        self.assertEqual(metrics.session_stop(limited), "error: api_error 429: You've hit your limit")

    def test_a_normal_claude_stop_and_the_other_hosts_keep_their_own_reason(self):
        ok = {"type": "result", "subtype": "success", "is_error": False, "terminal_reason": "completed",
              "stop_reason": "end_turn"}
        self.assertEqual(metrics.session_stop(ok), "success")
        self.assertEqual(metrics.session_stop({"type": "end", "stopReason": "cancelled"}), "cancelled")
        self.assertEqual(metrics.session_stop({"type": "end", "stopReason": "end_turn"}), "end_turn")
        failed_turn = {"type": "end", "stopReason": "error", "error": "You've hit your usage limit.\nTry later"}
        self.assertEqual(metrics.session_stop(failed_turn), "error: You've hit your usage limit. Try later")

    def test_nothing_reported_stays_unknown_and_a_structured_reason_is_still_text(self):
        self.assertIsNone(metrics.session_stop({"type": "end"}))
        stop = metrics.session_stop({"type": "end", "stopReason": {"kind": "max_turns"}})
        self.assertEqual(stop, '{"kind": "max_turns"}')
        self.assertEqual(run.stopped_line(run.termination_facts(
            {"status": "failed", "returncode": 1, "sessions": [{"stop": stop}], "resumes": 0}, {}, None)).count("max_turns"), 1)

    def test_collect_records_the_error_stop_of_a_claude_session(self):
        m = collect_stream([self.CLAUDE_API_ERROR], [])
        self.assertTrue(m["sessions"][0]["stop"].startswith("error: api_error"), m["sessions"])
        self.assertIn("error: api_error", metrics.summary_lines(m)[0])


class PrintedCase(HarnessCase):
    """A harness case that keeps what run.main printed, so the report can be asserted on."""

    def invoke_printed(self, host: str, mode: str, *extra: str) -> tuple[int, dict, str]:
        os.environ["FAKE_MODE"] = mode
        out = self.tmp / f"out-{host}-{mode}-{len(list(self.tmp.glob('out-*')))}"
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = run.main(["--host", host, f"--{host}-bin", str(self.fakes[host]), "--output", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), *extra])
        return code, json.loads((out / "result.json").read_text()), printed.getvalue()

    def stopped(self, printed: str) -> str:
        return next(line for line in printed.splitlines() if line.startswith("  stopped"))

    def last_row(self) -> dict:
        return json.loads(self.baselines.read_text().splitlines()[-1])


class TerminationThroughMainTest(PrintedCase):
    """Why a run stopped, as run.main records it in result.json, the baseline row and the printed report."""

    def test_a_finished_run_records_why_it_stopped_everywhere_it_is_reported(self):
        code, result, printed = self.invoke_printed("grok", "done")
        self.assertEqual(code, 0, result)
        t = result["termination"]
        self.assertEqual((t["process_status"], t["returncode"], t["sessions"], t["resumes"]), ("exited", 0, 1, 0))
        self.assertEqual((t["session_stops"], t["resume_stop"], t["engine_status"]),
                         (["cancelled"], "ShipLoop run is done", "done"))
        self.assertEqual(self.last_row()["termination"], t)
        self.assertEqual(self.stopped(printed), "  stopped   host exited rc=0; session stops cancelled; "
                                                "no further resume: ShipLoop run is done; engine done")

    def test_the_result_the_baseline_row_and_the_report_are_wired_to_the_same_records(self):
        code, result, printed = self.invoke_printed("grok", "done")
        row = self.last_row()
        self.assertEqual(result["metrics"]["stages"], [])  # the key is there: a comparison reads it
        self.assertEqual(row["stages"], run.baseline_stages(result["metrics"]["stages"]))
        self.assertEqual(row["unmeasured"], sorted(result["metrics"]["unmeasured"]))
        self.assertEqual(row["sessions"], len(result["process"]["sessions"]))
        self.assertIn("  baseline  nothing compared: no earlier row for hello", printed)

    def test_a_run_that_never_finishes_names_the_stage_and_the_spent_budget(self):
        code, result, printed = self.invoke_printed("grok", "stuck", "--max-resumes", "2")
        self.assertEqual(code, 1)
        t = result["termination"]
        self.assertEqual((t["sessions"], t["resumes"], t["resume_stop"]), (3, 2, "resume budget spent (2)"))
        self.assertEqual((t["engine_status"], t["engine_unaccepted_stage"]), ("active", "test-refine"))
        self.assertFalse(self.baselines.exists(), "a run left active is not a baseline, so no row carries its termination")
        self.assertEqual(self.stopped(printed),
                         "  stopped   host exited rc=0; session stops cancelled, cancelled, cancelled; "
                         "no further resume: resume budget spent (2); engine active with test-refine never accepted")

    def test_the_last_permitted_resume_that_finishes_the_run_is_not_called_a_spent_budget(self):
        code, result, _ = self.invoke_printed("grok", "resume", "--max-resumes", "1")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["termination"]["sessions"], 2)
        self.assertEqual(result["termination"]["resume_stop"], "ShipLoop run is done")

    def test_a_run_finished_by_its_only_permitted_session_is_not_called_a_spent_budget(self):
        code, result, _ = self.invoke_printed("grok", "done", "--max-resumes", "0")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["termination"]["resume_stop"], "ShipLoop run is done")

    def test_a_session_that_names_no_host_session_cannot_be_resumed(self):
        code, result, _ = self.invoke_printed("grok", "anon")
        self.assertEqual(code, 1)
        self.assertEqual(result["termination"]["resume_stop"], "no host session id to resume")
        self.assertEqual(result["termination"]["sessions"], 1)

    def test_a_killed_session_is_unknown_and_the_deadline_is_the_stop(self):
        code, result, printed = self.invoke_printed("grok", "hang", "--timeout", "3")
        self.assertEqual(code, 1)
        t = result["termination"]
        self.assertEqual((t["process_status"], t["returncode"]), ("timeout", -9))
        self.assertEqual((t["sessions"], t["session_stops"], t["resume_stop"]),
                         (1, ["unknown"], "run deadline spent"))
        self.assertIn("host timeout rc=-9; session stops unknown", self.stopped(printed))

    def test_session_stops_has_one_entry_per_session_and_unknown_for_a_crashed_one(self):
        code, result, _ = self.invoke_printed("grok", "crash-resumed", "--max-resumes", "2")
        self.assertEqual(code, 1)
        t = result["termination"]
        self.assertEqual(len(result["process"]["sessions"]), 3)
        self.assertEqual((t["sessions"], t["session_stops"]), (3, ["cancelled", "unknown", "unknown"]))
        self.assertEqual((t["process_status"], t["returncode"]), ("failed", 1))
        self.assertEqual(t["resume_stop"], "resume budget spent (2)")

    def test_claude_is_not_resumable_and_its_own_stop_is_recorded(self):
        code, result, _ = self.invoke_printed("claude", "done")
        self.assertEqual(code, 0, result)
        t = result["termination"]
        self.assertEqual((t["resume_stop"], t["session_stops"]), ("host is not resumable", ["success"]))

    def test_a_claude_api_error_is_recorded_as_an_error_not_a_success(self):
        code, result, printed = self.invoke_printed("claude", "api-error")
        self.assertEqual(code, 1)
        t = result["termination"]
        self.assertEqual((t["process_status"], t["returncode"]), ("failed", 1))
        self.assertTrue(t["session_stops"][0].startswith("error: api_error"), t["session_stops"])
        self.assertIn("session stops error: api_error", self.stopped(printed))
        self.assertNotIn("session stops success", printed)


class MeasuredHostPrintingTest(PrintedCase):
    def test_claude_runs_measure_their_tool_calls_and_still_say_which_counters_they_cannot_show(self):
        code, first, printed = self.invoke_printed("claude", "done")
        self.assertEqual(code, 0, first)
        self.assertIsNone(first["metrics"]["cancelled_tool_calls"])
        self.assertIn("cancelled_tool_calls", first["metrics"]["unmeasured"])
        for name in ("model_glue", "shiploop_failures", "tmp_writes"):
            self.assertEqual(first["metrics"][name], 0, name)
            self.assertNotIn(name, first["metrics"]["unmeasured"], name)
        self.assertIn("model glue 0", printed)
        self.assertIn("cancelled tool calls not measured", printed)
        self.assertEqual(self.last_row()["model_glue"], 0)
        code, second, printed = self.invoke_printed("claude", "done")
        self.assertIn("glue 0 -> 0", printed)

    def test_a_claude_row_from_before_the_tool_blocks_were_read_compares_as_not_measured(self):
        code, first, printed = self.invoke_printed("claude", "done")
        row = json.loads(self.baselines.read_text().splitlines()[-1])
        old = dict(row, model_glue=None, shiploop_failures=None, tmp_writes=None,
                   unmeasured=sorted({*row["unmeasured"], "model_glue", "shiploop_failures", "tmp_writes", "stage_tool_calls"}))
        self.baselines.write_text(json.dumps(old) + "\n")
        code, second, printed = self.invoke_printed("claude", "done")
        self.assertIn("glue not measured -> 0", printed)


class ReportedCostThroughMainTest(PrintedCase):
    """What run.main prints for cost: unknown stays unknown, and a killed session makes a lower bound."""

    def line(self, printed: str, prefix: str) -> str:
        return next(ln for ln in printed.splitlines() if ln.startswith(prefix))

    def test_a_host_that_reports_no_cost_says_so_in_the_report_and_never_prints_zero(self):
        code, result, printed = self.invoke_printed("codex", "done")
        self.assertEqual(code, 0, result)
        self.assertIsNone(self.last_row()["cost_usd"])
        process = self.line(printed, "  process")
        self.assertIn("cost=not reported", process)
        self.assertNotIn("$0", process)
        self.assertIn("cost not reported", self.line(printed, "  metrics   turns"))

    def test_a_session_the_run_killed_is_named_beside_the_cost_and_is_not_a_baseline_key(self):
        code, result, printed = self.invoke_printed("claude", "chain-hang", "--interrupt-at", "chain-launched")
        self.assertEqual(code, 0, result)
        note = "(lower bound: 1 session(s) never reported)"
        self.assertIn(f"cost=$0.0 {note}", self.line(printed, "  process"))
        self.assertIn(f"cost $0.0 {note}", self.line(printed, "  metrics   turns"))
        self.assertNotIn("unreported_sessions", run.baseline_row(result, None, None))
        code, result, printed = self.invoke_printed("claude", "done")
        self.assertEqual(result["metrics"]["unreported_sessions"], 0)
        self.assertNotIn("lower bound", printed)


class ResumedRunRecordTest(PrintedCase):
    """A run continued after the harness stopped keeps what it recorded and invents nothing."""

    def stopped_run(self) -> Path:
        code, result, _ = self.invoke_printed("grok", "stuck", "--max-resumes", "0")
        self.assertEqual(code, 1)
        return Path(result["output"])

    def finish_out_of_band(self, out: Path) -> None:
        """The run reaches done while no harness is watching (its parent was killed)."""
        shutil.rmtree(out / "work" / ".shiploop")
        (out / "work" / ".shiploop").mkdir()
        (out / "work" / ".shiploop" / "report.html").write_text("<html></html>")
        run.store.write_record(out / "work" / ".shiploop" / "state.md", {"status": "done"})

    def regrade(self, out: Path, *extra: str) -> tuple[dict, str]:
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            run.main([*extra, "--resume-run", str(out), "--plugin-dir", str(self.plugin),
                      "--baseline", str(self.baselines)])
        return json.loads((out / "result.json").read_text()), printed.getvalue()

    def test_a_regrade_keeps_the_termination_the_original_run_recorded(self):
        out = self.stopped_run()
        original = json.loads((out / "result.json").read_text())["termination"]
        self.finish_out_of_band(out)
        result, printed = self.regrade(out, "--host", "grok", "--grok-bin", str(self.fakes["grok"]))
        t = result["termination"]
        self.assertTrue(t["regraded"])
        self.assertEqual({k: v for k, v in t.items() if k in original}, original)
        self.assertEqual(t["resume_stop"], "resume budget spent (0)")
        self.assertEqual(t["engine_status_at_regrade"], "done")
        self.assertIn("the original record, regraded with engine done", printed)

    def block_out_of_band(self, out: Path) -> None:
        """The run's engine blocked itself on a question for a person, as Luna's did, with no report written."""
        shutil.rmtree(out / "work" / ".shiploop")
        (out / "work" / ".shiploop").mkdir()
        run.store.write_record(out / "work" / ".shiploop" / "state.md",
                               {"status": "blocked", "stage": "test-refine", "status_reason": "waiting for a person"})

    def test_a_blocked_run_is_regraded_without_a_host_and_keeps_the_recorded_identity(self):
        out = self.stopped_run()
        recorded = json.loads((out / "result.json").read_text())
        self.block_out_of_band(out)
        self.log.unlink(missing_ok=True)
        result, printed = self.regrade(out, "--host", "codex", "--codex-bin", str(self.fakes["codex"]))
        self.assertFalse(self.log.exists(), "no host process was started for a blocked run")
        self.assertTrue(result["process"]["regraded"])
        self.assertEqual((result["host"], result["model"], result["effort"]),
                         (recorded["host"], recorded["model"], recorded["effort"]),
                         "a regrade restates the run's recorded host, model and effort, not --host")
        t = result["termination"]
        self.assertEqual((t["regraded"], t["engine_status_at_regrade"]), (True, "blocked"))
        self.assertIn("the original record, regraded with engine blocked", printed)
        self.assertFalse(result["shiploop"]["pass"], "a blocked run never reached done")
        self.assertEqual(result["shiploop"]["status"], "blocked")
        self.assertIn("metrics", result, "the regrade refreshed the metrics block")
        self.assertTrue((out / "metrics.json").is_file())
        self.assertEqual(len(list(out.glob("invocation-resume-*.json"))), 1)
        rows = self.baselines.read_text().splitlines() if self.baselines.exists() else []
        self.assertEqual(rows, [], "the original run was left active and so wrote no baseline row; a regrade writes none")

    def test_a_regrade_with_no_record_says_no_host_ran_and_fabricates_no_exit(self):
        out = self.stopped_run()
        self.finish_out_of_band(out)
        (out / "result.json").unlink()
        result, printed = self.regrade(out, "--host", "grok", "--grok-bin", str(self.fakes["grok"]))
        t = result["termination"]
        self.assertEqual((t["process_status"], t["returncode"], t["sessions"], t["session_stops"]),
                         (run.NOT_OBSERVED, None, 0, []))
        self.assertEqual((t["resume_stop"], t["regraded"], t["engine_status"]), ("not evaluated (regraded)", True, "done"))
        self.assertEqual(result["process"]["sessions"], [])
        self.assertEqual(self.stopped(printed), "  stopped   no host ran (regraded); engine done")
        self.assertIn("no host ran: regraded from what is on disk", printed)
        self.assertNotIn("host exited rc=0", printed)

    def test_a_regrade_without_a_host_flag_keeps_the_host_the_run_recorded(self):
        out = self.stopped_run()
        self.finish_out_of_band(out)
        result, _ = self.regrade(out)  # no --host: the default is Claude, which never ran this
        self.assertEqual(result["host"], "grok")
        self.assertEqual(result["model"], json.loads((out / "invocation.json").read_text())["model"])
        self.assertTrue(result["process"]["regraded"])

    def test_a_regrade_through_the_marketplace_source_never_overwrites_the_finished_result(self):
        code, finished, _ = self.invoke_printed("grok", "done")
        out = Path(finished["output"])
        before = (out / "result.json").read_text()
        gate = ["local HEAD 0123abc has commits origin/main does not: publish them first"]
        refused = {"source": "marketplace", "plugin_version": "9", "shiploop_version": "1", "gate": gate}
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(
                run, "marketplace_preflight", return_value=(self.plugin, None, refused)) as preflight:
            # A different host and no --plugin-dir: the branch that installs from the marketplace.
            run.main(["--host", "codex", "--codex-bin", str(self.fakes["codex"]), "--resume-run", str(out),
                      "--baseline", str(self.baselines)])
        preflight.assert_not_called()  # a regrade starts no host: nothing is installed or gated
        regraded = json.loads((out / "result.json").read_text())
        self.assertTrue(regraded["process"]["regraded"])
        self.assertTrue(regraded["shiploop"]["pass"], regraded["shiploop"])
        self.assertNotEqual((out / "result.json").read_text(), before)  # re-graded, not stubbed

    def test_a_refused_resume_never_overwrites_the_record_of_the_run_it_would_have_continued(self):
        out = self.stopped_run()
        before = (out / "result.json").read_text()
        gate = ["origin/main has unreleased changes (x): run scripts/release.py and push"]
        versions = {"source": "marketplace", "plugin_version": "9", "shiploop_version": "1", "gate": gate}
        os.environ["FAKE_MODE"] = "done"
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(
                run, "marketplace_preflight", return_value=(self.plugin, None, versions)):
            with self.assertRaisesRegex(SystemExit, "version gate"):
                run.main(["--host", "codex", "--codex-bin", str(self.fakes["codex"]), "--resume-run", str(out),
                          "--baseline", str(self.baselines)])
        self.assertEqual((out / "result.json").read_text(), before)

    def test_a_resumed_run_keeps_the_termination_each_earlier_invocation_recorded(self):
        out = self.stopped_run()
        original = json.loads((out / "result.json").read_text())["termination"]
        os.environ["FAKE_MODE"] = "done"
        with contextlib.redirect_stdout(io.StringIO()):
            run.main(["--host", "codex", "--codex-bin", str(self.fakes["codex"]), "--resume-run", str(out),
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        result = json.loads((out / "result.json").read_text())
        self.assertEqual(result["earlier_terminations"], [original])
        self.assertEqual(result["termination"]["resume_stop"], "ShipLoop run is done")
        self.assertEqual(result["termination"]["sessions"], 1)  # this invocation's own sessions


class PluginVerdictCarriedTest(PrintedCase):
    """A run continued or regraded after the harness stopped keeps the plugin verdict of its first launch.

    Only Claude's own events say which plugin loaded. A Grok or Codex run's evidence is the install check made
    before its first process started, so invocation.json records it and a later invocation reads it back."""

    HOSTS = ("claude", "grok", "codex")

    def setUp(self):
        super().setUp()
        # A real build names its version, which the same-host resume branch compares with the catalog's.
        (self.plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": "9.9.9"}))

    def continue_run(self, host: str, out: Path) -> dict:
        """--resume-run on a run directory, graded as the harness would; nothing leaves the temp directory."""
        released = {"origin_main": "a" * 40, "local_head": "a" * 40, "local_behind_main": False,
                    "catalog_version": "9.9.9", "shiploop_version": None, "unreleased": [], "ci": "success"}
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(
                run, "released_versions", return_value=released):
            run.main(["--host", host, f"--{host}-bin", str(self.fakes[host]), "--resume-run", str(out),
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), "--max-resumes", "0"])
        return json.loads((out / "result.json").read_text())

    def ended_while_active(self, host: str) -> tuple[Path, dict]:
        """A first process that ended while ShipLoop was active: the run a resume continues in place."""
        code, first, _ = self.invoke_printed(host, "nothing", "--max-resumes", "0")
        out = Path(first["output"])
        (out / "work" / ".shiploop").mkdir()
        run.store.write_record(out / "work" / ".shiploop" / "state.md",
                               {"status": "active", "stage": "test-refine", "revision": 25})
        return out, first

    def test_a_regrade_keeps_the_plugin_evidence_of_the_first_process(self):
        for host in self.HOSTS:
            with self.subTest(host=host):
                code, first, _ = self.invoke_printed(host, "done")
                self.assertTrue(first["plugin"]["pass"], first["plugin"])
                result = self.continue_run(host, Path(first["output"]))
                self.assertTrue(result["process"]["regraded"])
                self.assertEqual(result["plugin"], first["plugin"])

    def test_a_run_resumed_in_place_keeps_the_plugin_evidence_of_its_first_process(self):
        for host in self.HOSTS:
            with self.subTest(host=host):
                out, first = self.ended_while_active(host)
                self.assertTrue(first["plugin"]["pass"], first["plugin"])
                result = self.continue_run(host, out)
                self.assertEqual(result["resumed_run"]["from_host"], host)
                self.assertNotIn("regraded", result["process"])  # a host did start: this is a resume
                self.assertEqual(result["plugin"], first["plugin"])

    def test_a_host_whose_events_cannot_show_the_plugin_records_its_install_check_at_launch(self):
        for host in self.HOSTS:
            with self.subTest(host=host):
                code, first, _ = self.invoke_printed(host, "done")
                recorded = json.loads((Path(first["output"]) / "invocation.json").read_text())
                # Claude's init event shows the plugin on every launch; the others cannot, so they store it.
                self.assertEqual(recorded["plugin"], None if host == "claude" else first["plugin"])

    def test_a_run_whose_first_launch_recorded_no_plugin_verdict_is_not_given_one(self):
        out, first = self.ended_while_active("grok")
        recorded = json.loads((out / "invocation.json").read_text())
        recorded.pop("plugin", None)  # an invocation.json written before the verdict was kept
        (out / "invocation.json").write_text(json.dumps(recorded))
        result = self.continue_run("grok", out)
        self.assertFalse(result["plugin"]["pass"], "no evidence is a failed plugin check, never a guessed pass")
        self.assertEqual(result["plugin"]["loaded"], [])


# What ShipLoop leaves behind when a run ends before it has returned anything: its empty baseline commit and a
# run directory that is done. The product (a file) never reached the source checkout.
FAKE_CLAUDE_EMPTY_BASELINE = f"""#!{sys.executable}
import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, {str(ROOT / 'skills/shiploop/scripts')!r})
import shiploop_store as store
argv = sys.argv[1:]
plugin = argv[argv.index("--plugin-dir") + 1]
print(json.dumps({{"type": "system", "subtype": "init", "model": "fake-model",
                  "slash_commands": ["skill-craft:shiploop"], "plugins": [{{"name": "skill-craft", "path": plugin}}]}}))
print(json.dumps({{"type": "assistant", "message": {{"content": [{{"type": "tool_use", "name": "Bash",
                  "input": {{"command": "shiploop next"}}}}]}}}}))
subprocess.run(["git", "init", "-q"], check=True)
subprocess.run(["git", "-c", "user.name=ShipLoop", "-c", "user.email=shiploop@example.invalid",
                "-c", "commit.gpgsign=false", "commit", "-q", "--allow-empty",
                "-m", "Empty baseline for the first ShipLoop run"], check=True)
Path(".git/info").mkdir(exist_ok=True)
Path(".git/info/exclude").write_text(".shiploop/\\n")  # the run directory is not a product path
Path(".shiploop").mkdir()
store.write_record(Path(".shiploop/state.md"), {{"status": "done"}})
Path(".shiploop/report.html").write_text("<html></html>")
print(json.dumps({{"type": "result", "subtype": "success", "num_turns": 1, "total_cost_usd": 0.0, "result": "done"}}))
"""


class CommittedVerdictTest(PrintedCase):
    """`committed` means the product is in HEAD, not that HEAD differs from a start that had no commit.

    On a fresh run ShipLoop's first act is an empty baseline commit, so HEAD always differs from "no commit".
    Known limit, not guarded: any file counts as product, so a future ShipLoop that returned only knowledge
    files (docs/shiploop/) to the source checkout before the product would pass early."""

    def repo(self) -> Path:
        repo = self.tmp / "source"
        repo.mkdir()
        self.git(repo, "init", "-q")
        return repo

    def git(self, repo: Path, *args: str) -> str:
        done = subprocess.run(["git", "-C", str(repo), "-c", "user.name=T", "-c", "user.email=t@example.invalid",
                               "-c", "commit.gpgsign=false", *args], check=True, capture_output=True, text=True)
        return done.stdout.strip()

    def verdict(self, repo: Path, start_head: str | None = None) -> dict:
        return run.committed_facts(run.knowledge_facts(repo), start_head)

    def test_a_repository_holding_only_the_empty_baseline_commit_has_no_product(self):
        repo = self.repo()
        self.git(repo, "commit", "-q", "--allow-empty", "-m", "Empty baseline for the first ShipLoop run")
        got = self.verdict(repo)
        self.assertEqual((got["pass"], got["head_files"]), (False, 0))
        self.assertTrue(got["head"], "HEAD exists and differs from a start with no commit: only the files say no")

    def test_one_committed_file_is_product(self):
        repo = self.repo()
        (repo / "hello.py").write_text("print('hi')\n")
        self.git(repo, "add", "--", "hello.py")
        self.git(repo, "commit", "-q", "-m", "product")
        got = self.verdict(repo)
        self.assertEqual((got["pass"], got["head_files"], got["uncommitted"]), (True, 1, []))

    def test_head_must_still_move_past_the_start_and_leave_no_product_path_uncommitted(self):
        repo = self.repo()
        (repo / "hello.py").write_text("print('hi')\n")
        self.git(repo, "add", "--", "hello.py")
        self.git(repo, "commit", "-q", "-m", "product")
        head = self.git(repo, "rev-parse", "HEAD")
        self.assertFalse(self.verdict(repo, start_head=head)["pass"], "HEAD never moved past where the run started")
        (repo / "extra.py").write_text("x = 1\n")
        got = self.verdict(repo)
        self.assertFalse(got["pass"], "a product path is left untracked")
        self.assertEqual((got["head_files"], got["uncommitted"]), (1, ["extra.py"]))

    def test_a_run_that_returned_nothing_fails_committed_in_the_result_the_row_and_the_report(self):
        fake = self.tmp / "claude-empty-baseline"
        fake.write_text(FAKE_CLAUDE_EMPTY_BASELINE)
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        out = self.tmp / "out-empty-baseline"
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = run.main(["--host", "claude", "--claude-bin", str(fake), "--output", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines),
                             "--prompt", "make hello", "--check", "true"])
        result = json.loads((out / "result.json").read_text())
        # Everything else is right: ShipLoop is done, the plugin loaded, the check passes. Only the product is absent.
        self.assertTrue(result["shiploop"]["pass"], result["shiploop"])
        self.assertTrue(result["plugin"]["pass"] and result["invoked"]["pass"], result)
        self.assertTrue(all(c["pass"] for c in result["checks"]), result["checks"])
        self.assertEqual(code, 1, "a run that returned no file to the source checkout is not a pass")
        self.assertFalse(result["pass"])
        self.assertEqual((result["committed"]["pass"], result["committed"]["head_files"]), (False, 0))
        self.assertFalse(self.last_row()["verdicts"]["committed"])
        self.assertIn("0 files in HEAD", next(ln for ln in printed.getvalue().splitlines()
                                              if ln.startswith("  committed")))
        mismatch = (out / "mismatch.md").read_text()
        self.assertIn("**committed**", mismatch)
        self.assertIn("files in HEAD", mismatch)


class RegradeRecordTest(PrintedCase):
    """--resume-run on a finished run starts no host, so it restates the run's own record and invents none.

    The plugin verdict, the process block and the host, model and effort come from what the run recorded; a
    regrade that relabels a run, invents a clean exit or grades a Grok or Codex plugin from Claude's events
    replaces a finished result with a different one although nothing about the run changed."""

    HOSTS = ("claude", "grok", "codex")
    CLI = "python3 /x/skills/shiploop/scripts/shiploop next"

    def setUp(self):
        super().setUp()
        # A real host's events name the installed ShipLoop CLI by path, which is how a regrade sees that the skill
        # was invoked. The shared fakes print the bare command, so these tests use copies that print the path.
        for host in ("claude", "grok"):
            script = self.fakes[host]
            script.write_text(script.read_text().replace('"command": "shiploop next"', f'"command": "{self.CLI}"'))
            self.assertIn(self.CLI, script.read_text())

    def regrade(self, out: Path, *extra: str) -> tuple[dict, str]:
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            run.main([*extra, "--resume-run", str(out), "--plugin-dir", str(self.plugin),
                      "--baseline", str(self.baselines)])
        return json.loads((out / "result.json").read_text()), printed.getvalue()

    def finish_out_of_band(self, out: Path) -> None:
        shutil.rmtree(out / "work" / ".shiploop", ignore_errors=True)
        (out / "work" / ".shiploop").mkdir()
        (out / "work" / ".shiploop" / "report.html").write_text("<html></html>")
        run.store.write_record(out / "work" / ".shiploop" / "state.md", {"status": "done"})

    def test_a_regrade_of_a_finished_run_keeps_its_passing_result_on_every_host(self):
        for host in self.HOSTS:
            with self.subTest(host=host):
                code, first, _ = self.invoke_printed(host, "done")
                self.assertEqual(code, 0, first)
                result, _ = self.regrade(Path(first["output"]), "--host", host, f"--{host}-bin", str(self.fakes[host]))
                self.assertTrue(result["pass"], {k: result[k] for k in ("invoked", "plugin", "process")})
                self.assertTrue(result["process"]["regraded"])
                for key in ("host", "model", "effort", "plugin"):
                    self.assertEqual(result[key], first[key], key)
                # what the host did is what the original run observed, not a clean exit made up for the regrade
                self.assertEqual({k: v for k, v in result["process"].items() if k != "regraded"}, first["process"])

    def test_a_regrade_never_turns_a_failed_host_into_a_pass(self):
        wrapper = self.tmp / "claude-exits-3"  # the run finishes, then the host exits non-zero
        wrapper.write_text(f'#!/bin/sh\n"{self.fakes["claude"]}" "$@"\nexit 3\n')
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)
        os.environ["FAKE_MODE"] = "done"
        out = self.tmp / "out-exit-3"
        with contextlib.redirect_stdout(io.StringIO()):
            code = run.main(["--host", "claude", "--claude-bin", str(wrapper), "--output", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        first = json.loads((out / "result.json").read_text())
        self.assertEqual((code, first["pass"], first["shiploop"]["pass"]), (1, False, True))
        self.assertEqual((first["process"]["status"], first["process"]["returncode"]), ("failed", 3))
        result, printed = self.regrade(out)
        self.assertFalse(result["pass"], "a regrade cannot turn a failed host into a pass")
        self.assertEqual((result["process"]["status"], result["process"]["returncode"], result["process"]["pass"]),
                         ("failed", 3, False))
        self.assertEqual(result["process"]["sessions"], first["process"]["sessions"])
        self.assertEqual(result["process"]["elapsed_seconds"], first["process"]["elapsed_seconds"])
        self.assertEqual((result["termination"]["process_status"], result["termination"]["returncode"]), ("failed", 3))
        self.assertIn("process   FAIL", printed)
        self.assertIn("failed rc=3", (out / "mismatch.md").read_text())

    def test_a_regrade_with_no_record_of_a_host_exit_says_so_and_leaves_that_verdict_out(self):
        code, first, _ = self.invoke_printed("grok", "done")
        out = Path(first["output"])
        (out / "result.json").unlink()  # the harness died with its host: nothing recorded the exit
        result, printed = self.regrade(out)
        self.assertEqual((result["process"]["status"], result["process"]["returncode"], result["process"]["pass"]),
                         ("not observed", None, None))
        self.assertTrue(result["pass"], {k: result[k] for k in ("invoked", "plugin", "committed", "checks")})
        self.assertIn("process   n/a   no host ran: regraded from what is on disk", printed)
        self.assertFalse((out / "mismatch.md").exists(), "an unobserved exit is not a failure")

    def test_a_regrade_keeps_the_host_model_and_effort_the_run_recorded_whatever_the_command_line_says(self):
        code, first, _ = self.invoke_printed("grok", "done")
        result, printed = self.regrade(Path(first["output"]), "--host", "codex", "--codex-bin", str(self.fakes["codex"]),
                                       "--model", "gpt-6-sol", "--effort", "xhigh")
        self.assertEqual((result["host"], result["model"], result["effort"]),
                         (first["host"], first["model"], first["effort"]))
        self.assertEqual((first["host"], first["effort"]), ("grok", "medium"))
        self.assertTrue(result["pass"], {k: result[k] for k in ("invoked", "plugin", "process")})
        self.assertIn("ignoring --host codex, --model gpt-6-sol, --effort xhigh", printed)

    def test_a_run_resumed_on_another_host_is_regraded_as_that_host_with_its_plugin_and_versions(self):
        code, stopped, _ = self.invoke_printed("grok", "stuck", "--max-resumes", "0")
        out = Path(stopped["output"])
        os.environ["FAKE_MODE"] = "nothing"
        with contextlib.redirect_stdout(io.StringIO()):
            run.main(["--host", "codex", "--codex-bin", str(self.fakes["codex"]), "--resume-run", str(out),
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        resumed = json.loads((out / "result.json").read_text())
        self.assertEqual((resumed["host"], resumed["resumed_run"]["from_host"]), ("codex", "grok"))
        self.finish_out_of_band(out)
        result, _ = self.regrade(out)  # no --host: the invocation.json host is grok, the run's own record says codex
        self.assertEqual((result["host"], result["model"], result["effort"]),
                         (resumed["host"], resumed["model"], resumed["effort"]))
        self.assertEqual(result["plugin"], resumed["plugin"])
        self.assertEqual({k: v for k, v in result["versions"].items() if k != "regraded"}, resumed["versions"])
        self.assertTrue(result["process"]["regraded"])


class BaselineAbsentTest(PrintedCase):
    def test_rows_that_name_no_host_say_nothing_was_compared_instead_of_printing_nothing(self):
        self.baselines.write_text(json.dumps({"case": "hello", "source": "checkout", "turns": 3}) + "\n")
        code, result, printed = self.invoke_printed("grok", "done")
        self.assertEqual(code, 0, result)
        self.assertIn("baseline  nothing compared: 1 earlier row(s) for hello, none recorded with grok/", printed)
        self.assertEqual(run.scan_baseline(self.baselines, "hello", "checkout", "grok", "m", "e")[1], 2)

    def test_a_resumed_run_says_it_is_not_a_baseline(self):
        code, stopped, _ = self.invoke_printed("grok", "stuck", "--max-resumes", "0")
        os.environ["FAKE_MODE"] = "done"
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            run.main(["--host", "codex", "--codex-bin", str(self.fakes["codex"]), "--resume-run", stopped["output"],
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        self.assertIn("baseline  nothing compared: a resumed or seeded run is not a baseline", printed.getvalue())

    def test_the_host_flag_is_seen_only_when_it_was_given(self):
        self.assertFalse(run.host_given([]))
        self.assertTrue(run.host_given(["--host", "claude"]))
        self.assertTrue(run.host_given(["--case", "hello", "--host=codex"]))


class PlanningReviewBaselineThroughMainTest(PrintedCase):
    """The committed row and the printed report as run.main writes them, for runs of the same and of different
    planning_review modes. The fake host's state.md records the mode named by FAKE_PLANNING_REVIEW ("absent": none)."""

    def run_with(self, mode: str) -> tuple[dict, str]:
        os.environ["FAKE_PLANNING_REVIEW"] = mode
        self.addCleanup(os.environ.pop, "FAKE_PLANNING_REVIEW", None)
        code, result, printed = self.invoke_printed("grok", "done")
        self.assertEqual(code, 0, result)
        return self.last_row(), printed

    def earlier_row(self, **changes) -> None:
        """Make the last committed row the only one, with `changes` (None removes a key): the row the next run compares with."""
        row = self.last_row()
        for key, value in changes.items():
            row.pop(key, None) if value is None else row.__setitem__(key, value)
        self.baselines.write_text(json.dumps(row) + "\n")

    def test_the_row_records_the_mode_the_runs_state_named_and_not_recorded_when_it_named_none(self):
        self.assertEqual([self.run_with(mode)[0]["planning_review"] for mode in ("none", "stage", "absent")],
                         ["none", "stage", "not recorded"])

    def test_a_second_run_of_the_same_mode_is_compared_and_the_report_names_the_mode(self):
        self.run_with("none")
        _, printed = self.run_with("none")
        self.assertRegex(printed, r"  baseline  vs \d{4}-\d\d-\d\d \(ShipLoop .*, same grok/.*, planning_review none\): turns ")
        self.assertIn("            ", printed.split("planning_review none): turns ")[1])  # the stage lines follow
        self.assertNotIn("not compared across", printed)
        self.assertNotIn("records no mode", printed)  # it recorded one: no rule was used

    def number_rows(self, *turns: int) -> None:
        """Give each committed row a distinctive `turns`, so the printed `turns <earlier> -> <now>` names the row compared with."""
        rows = [json.loads(line) for line in self.baselines.read_text().splitlines()]
        self.assertEqual(len(rows), len(turns))
        self.baselines.write_text("".join(json.dumps(dict(row, turns=n)) + "\n" for row, n in zip(rows, turns)))

    def test_a_run_with_only_rows_of_the_other_mode_compares_nothing_and_says_there_is_no_earlier_row_of_its_mode(self):
        for first, second in (("stage", "none"), ("none", "stage")):
            with self.subTest(first=first, second=second):
                self.baselines.unlink(missing_ok=True)
                self.run_with(first)
                _, printed = self.run_with(second)
                self.assertIn(f"  baseline  not compared across planning_review modes ({second} vs {first}); "
                              f"no earlier row of mode {second}; the last row for this driver is ", printed)
                self.assertNotIn("baseline  vs", printed)
                self.assertNotRegex(printed, r"turns \S+ -> |stage turns|per-stage")  # nothing below the line is compared
        self.assertEqual(len(self.baselines.read_text().splitlines()), 2)  # the run still writes its own row

    def test_a_run_is_compared_with_the_last_row_of_its_own_mode_not_refused_because_the_last_row_has_the_other(self):
        self.run_with("stage")
        _, printed = self.run_with("none")  # the only earlier row is a stage row: nothing to compare
        self.assertIn("no earlier row of mode none", printed)
        self.number_rows(11, 22)
        _, printed = self.run_with("stage")  # [stage, none] then stage: the stage row, found past the none row
        self.assertIn("planning_review stage): turns 11 -> ", printed)
        self.assertNotIn("not compared across", printed)

    def test_two_modes_interleaved_each_pick_their_own_last_row(self):
        for mode in ("stage", "none", "stage", "none"):
            self.run_with(mode)
        self.number_rows(111, 222, 333, 444)
        _, printed = self.run_with("none")
        self.assertIn("planning_review none): turns 444 -> ", printed)
        self.number_rows(111, 222, 333, 444, 555)
        _, printed = self.run_with("stage")
        self.assertIn("planning_review stage): turns 333 -> ", printed)
        self.assertNotIn("not compared across", printed)

    def test_an_earlier_row_with_no_mode_compares_as_stage_only_when_its_plugin_predates_the_option(self):
        self.run_with("stage")
        self.earlier_row(planning_review=None, plugin_version="1.21.0")
        _, printed = self.run_with("stage")
        self.assertIn("planning_review stage): turns ", printed)
        self.assertIn("            the earlier row records no mode, read as stage because plugin 1.21.0 predates the option", printed)
        self.earlier_row(planning_review=None, plugin_version="1.21.0")
        _, printed = self.run_with("none")
        self.assertIn("  baseline  not compared across planning_review modes (none vs stage); no earlier row of mode none; ", printed)
        self.assertIn("; it records no mode, read as stage because plugin 1.21.0 predates the option", printed)
        for version in (None, "1.22.0"):  # no plugin_version, and a release that has the option but wrote no field
            self.earlier_row(planning_review=None, plugin_version=version)
            _, printed = self.run_with("stage")
            self.assertIn("modes (stage vs not recorded); no earlier row of mode stage; ", printed, version)
            self.assertNotIn("baseline  vs", printed, version)

    def test_an_old_row_still_serves_as_the_stage_row_after_a_none_run_has_been_recorded_after_it(self):
        self.run_with("stage")
        self.earlier_row(planning_review=None, plugin_version="1.21.0", turns=555)
        _, printed = self.run_with("none")
        self.assertIn("(none vs stage); no earlier row of mode none; ", printed)
        _, printed = self.run_with("stage")  # [old row, none row] then stage: the old row, read as stage
        self.assertIn("planning_review stage): turns 555 -> ", printed)
        self.assertIn("            the earlier row records no mode, read as stage because plugin 1.21.0 predates the option", printed)

    def test_a_run_whose_state_named_no_mode_is_compared_with_no_row(self):
        self.run_with("stage")
        _, printed = self.run_with("absent")
        self.assertIn("modes (not recorded vs stage); this run records no mode; the last row for this driver is ", printed)
        _, printed = self.run_with("absent")  # two unrecorded modes are not known to match
        self.assertIn("modes (not recorded vs not recorded); this run records no mode; ", printed)
        self.assertNotIn("baseline  vs", printed)


class AttributionEdgeTest(unittest.TestCase):
    """Edge cases of per-stage attribution: seeded stages, an empty history, an unstamped action, a block."""

    USAGE = [{"type": "usage", "usage": {"input_tokens": 10, "output_tokens": 1}} for _n in range(12)]

    def test_a_stage_the_harness_seeded_has_no_timing_and_does_not_bill_the_host_start_up(self):
        # Seeded stages are accepted before the host's first event (t = 100.0).
        m = collect_stream(self.USAGE, [("S1", "intake", "done", 95.0), ("S2", "spec", "done", 96.0),
                                        ("A3", "plan", "done", 110.0)])
        self.assertEqual([(r["stage"], r.get("timing")) for r in m["stages"]],
                         [("intake", "unavailable"), ("spec", "unavailable"), ("plan", None)])
        self.assertEqual(m["stages"][2]["seconds"], 10.0)  # from the first host event, not from the seed
        self.assertGreater(m["stages"][2]["turns"], 0)
        self.assertTrue(all(r.get("seconds", 0) >= 0 for r in m["stages"]))

    def test_a_run_that_stopped_before_its_first_acceptance_still_names_its_stage(self):
        m = collect_stream(self.USAGE, [], status="active", stage="intake")
        self.assertEqual([(r["stage"], r.get("incomplete")) for r in m["stages"]], [("intake", True)])
        self.assertGreater(m["stages"][0]["turns"], 0)
        self.assertGreater(m["stages"][0]["seconds"], 0)

    def test_an_incomplete_row_after_an_unstamped_acceptance_is_unavailable_not_overstated(self):
        m = collect_stream(self.USAGE, [("A1", "intake", "done", 101.0), ("A2", "spec", "done", None)],
                           status="active", stage="plan")
        self.assertEqual(m["stages"][-1], {"stage": "plan", "outcome": None, "incomplete": True,
                                           "timing": "unavailable"})

    def test_without_a_runner_timeline_the_unaccepted_stage_is_still_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "events.jsonl").write_text(json.dumps(self.USAGE[0]) + "\n")
            write_engine_records(out / "run", [("A1", "intake", "done", 101.0)], status="active", stage="spec")
            m = metrics.collect(out, out / "run")
        self.assertEqual([(r["stage"], r.get("incomplete")) for r in m["stages"]],
                         [("intake", None), ("spec", True)])
        self.assertTrue(all(r["timing"] == "unavailable" for r in m["stages"]))

    def test_a_stage_the_engine_accepted_as_blocked_was_not_left_unaccepted(self):
        accepted = [("A1", "intake", "done", 101.0), ("A2", "system-test", "blocked", 104.0)]
        m = collect_stream(self.USAGE, accepted, status="blocked", stage="system-test")
        self.assertFalse(any(r.get("incomplete") for r in m["stages"]))
        engine = {"status": "blocked", "stage": "system-test", "status_reason": "user: a person must look\n at it",
                  "history": [{"stage": "system-test", "outcome": "blocked", "action": "A2"}]}
        t = run.termination_facts({"status": "exited", "returncode": 0, "sessions": [{"stop": "end_turn"}],
                                   "resumes": 0}, engine, "ShipLoop run is blocked")
        self.assertIsNone(t["engine_unaccepted_stage"])
        self.assertEqual((t["engine_stage"], t["engine_status_reason"]), ("system-test", "user: a person must look at it"))
        line = run.stopped_line(t)
        self.assertIn("engine blocked at system-test (user: a person must look at it)", line)
        self.assertNotIn("never accepted", line)

    def test_a_blocked_run_whose_current_stage_was_not_the_blocked_one_still_has_an_unaccepted_stage(self):
        engine = {"status": "blocked", "stage": "plan",
                  "history": [{"stage": "spec", "outcome": "blocked", "action": "A2"}]}
        self.assertEqual(metrics.pending_stage(engine), "plan")

    def test_a_halted_run_names_the_item_s_own_stage(self):
        engine = {"status": "halted", "stage": "inner-loop", "work_index": 0, "work_items": [{"id": "W1"}],
                  "inner_loops": {"W1": {"stage": "test-green"}}, "status_reason": "halted by the user"}
        t = run.termination_facts({"status": "exited", "returncode": 0, "sessions": [{}], "resumes": 0},
                                  engine, "ShipLoop run is halted")
        self.assertEqual((t["engine_stage"], t["engine_unaccepted_stage"]), ("test-green", "test-green"))
        self.assertIn("engine halted with test-green never accepted (halted by the user)", run.stopped_line(t))


class CouldNotRunCountTest(unittest.TestCase):
    """A test attempt that reached no verdict is counted and shown, because it is an environment problem."""

    def records(self, tmp: str) -> Path:
        tests = Path(tmp) / "run" / "tests"
        tests.mkdir(parents=True)
        (tests / "nav-1-verify1.md").write_text('{"passed": false, "disposition": "could-not-run", '
                                                '"runs": [{"command": "a", "status": "timeout"}]}')
        (tests / "nav-1-verify2.md").write_text('{"passed": true, "runs": [{"command": "a"}]}')
        (tests / "nav-2-verify1.md").write_text('{"passed": false, "runs": [{"command": "b"}]}')
        return Path(tmp) / "run"

    def test_could_not_run_records_are_counted_apart_from_failures_and_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(metrics.verifications(self.records(tmp)),
                             {"records": 3, "passed": 1, "could_not_run": 1, "commands": 3, "red": 0})

    def test_the_report_and_the_progress_line_show_the_could_not_run_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self.records(tmp)
            out = Path(tmp)
            (out / "events.jsonl").write_text(json.dumps({"type": "usage", "usage": {"input_tokens": 1}}) + "\n")
            write_engine_records(run_dir, [("A1", "intake", "done", 101.0)])
            m = metrics.collect(out, run_dir)
            self.assertIn("script verifications 1/3 passed (1 could not run)", metrics.summary_lines(m)[0])
            self.assertIn("1 could not run", progress.report(out))


class RedRecordCountTest(unittest.TestCase):
    """A record that passed because its commands ran red is counted apart from the green passes (r1 Battleship: 2 of the
    10 passed records). The count reads what ran (a run whose status is `red`), not what the record expected."""

    def verify(self, records: dict) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            tests = Path(tmp) / "run" / "tests"
            tests.mkdir(parents=True)
            for name, record in records.items():
                (tests / f"{record['action']}-verify1.md").write_text(run.store.dumps(record, "ShipLoop test-loop verification"))
            return metrics.verifications(Path(tmp) / "run")

    def test_records_whose_commands_ran_red_are_counted_apart_from_green_passes(self):
        records = json.loads((TOOL_BLOCKS / "verify-records.json").read_text())
        self.assertEqual(self.verify(records), {"records": 3, "passed": 3, "could_not_run": 0, "commands": 5, "red": 2})
        # The test-author probe accepts red or passed (`expect: a test ran`): one that ran green is a green pass.
        probe = json.loads(json.dumps(records))
        for each in probe["test-author"]["runs"]:
            each["status"], each["exit"] = "passed", 0
        self.assertEqual(self.verify(probe)["red"], 1)

    def test_the_report_names_the_red_records_without_calling_them_expected(self):
        m = collect_stream(codex_stream(1), [])
        m["script_verifications"] = {"records": 10, "passed": 10, "could_not_run": 0, "commands": 20, "red": 2}
        line = metrics.summary_lines(m)[0]
        self.assertIn("script verifications 10/10 passed (2 ran red)", line)
        m["script_verifications"] = {"records": 10, "passed": 9, "could_not_run": 1, "commands": 20, "red": 0}
        self.assertIn("script verifications 9/10 passed (1 could not run)", metrics.summary_lines(m)[0])
        self.assertNotIn("ran red", metrics.summary_lines(m)[0])
        self.assertNotIn("expected", metrics.summary_lines(m)[0])


class RetentionIdCountTest(unittest.TestCase):
    """The scoring case's retention check counts requirement ids the way the engine does (plan R7).

    The check is the catalog's own shell command, run through `run.run_checks`, and the engine's
    `_REQUIREMENT_ID` is the oracle: a spec form the engine accepts must not fail a correct run.
    """

    # A spec records its ids in any of these forms; the engine reads an id anywhere on a line.
    FORMS = {
        "heading": "## R-1 Fire\n## R-2 Board\n",  # the one form the earlier line-start pattern also read
        "bullet": "- R-1 Fire\n- R-2 Board\n",
        "bold bullet": "- **R-1** Fire\n- **R-2** Board\n",
        "table row": "| R-1 | Fire |\n| R-2 | Board |\n",
        "mixed line": "Requirements: R-1 R-1a R-2\n",  # R-1a is not an id: BSD `grep -ow` reads 1 of the 2 here
    }
    NEW = "R-3 Accuracy\nEvery fire returns shots, hits and accuracy.\n"

    @staticmethod
    def retention_check() -> str:
        retention = json.loads(run.CASES.read_text())["battleship-scoring"]["retention"]
        found = [command for command in retention if "ids()" in command]
        assert len(found) == 1, "the requirement-id retention check moved: update this test"
        return found[0]

    @staticmethod
    def earlier_ids(result: dict) -> int:
        """The count the check printed (BSD `wc -l` pads it with spaces, so read it as a number)."""
        found = re.search(r"earlier ids:\s*(\d+);", result["output"])
        assert found, "the check no longer prints its id count: " + result["output"]
        return int(found.group(1))

    def verdict(self, prior_spec: str, current_spec: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            prior, work = Path(tmp) / "prior", Path(tmp) / "work"
            for root, text in ((prior, prior_spec), (work, current_spec)):
                (root / "docs" / "shiploop").mkdir(parents=True)
                (root / "docs" / "shiploop" / "spec.md").write_text(text)
            return run.run_checks(work, [self.retention_check()], env={"PRIOR_WORK": str(prior)})[0]

    def test_a_correct_spec_passes_in_every_form_and_the_count_is_the_engines(self):
        for name, form in self.FORMS.items():
            with self.subTest(form=name):
                engine = run.knowledge_home._REQUIREMENT_ID.findall(form)
                self.assertEqual(len(set(engine)), 2, "the form must hold two ids for the engine")
                result = self.verdict(form, form + self.NEW)
                self.assertTrue(result["pass"], result["output"])
                self.assertEqual(self.earlier_ids(result), 2, "the engine's count, not a pattern's: " + result["output"])

    def test_a_dropped_id_fails_in_every_form_and_is_named(self):
        for name, form in self.FORMS.items():
            with self.subTest(form=name):
                kept = form.replace("R-2", "R-9") if name != "mixed line" else "Requirements: R-1 R-1a R-9\n"
                result = self.verdict(form, kept + self.NEW)
                self.assertFalse(result["pass"], "a dropped earlier id must still fail: " + result["output"])
                self.assertIn("missing: R-2", result["output"])

    def test_a_spec_with_no_ids_still_fails_because_nothing_was_retained(self):
        result = self.verdict("Fire and board.\n", "Fire and board.\n" + self.NEW)
        self.assertFalse(result["pass"], result["output"])
        self.assertEqual(self.earlier_ids(result), 0)

    def test_the_catalog_pattern_is_written_verbatim_and_matches_the_engine_regex(self):
        # Drift guard: the engine's `\b(R-\d+)\b` is the oracle, so a change to either side fails here.
        found = re.search(r"grep -oE '([^']*)' \"\$1/docs/shiploop/spec\.md\"", self.retention_check())
        self.assertIsNotNone(found, "ids() no longer reads the spec with one `grep -oE '<pattern>'`")
        pattern = found.group(1)
        self.assertEqual(pattern, r"\bR-[0-9]+\b", "verbatim, with a real backslash (JSON-escaped in the catalog)")
        samples = ("R-1 R-1a R-2\n", "XR-3 R-4_ R-5\n", "[R-6] (R-7).\n", "R-8R-9\n", "R-10.2 R-007\n",
                   "| R-11 | x |\n- **R-12** y\n## R-13 z\n", "r-1 R- R-x R-\n", "no ids here\n")
        for text in samples:
            with self.subTest(text=text):
                from_grep = subprocess.run(["grep", "-oE", pattern], input=text, capture_output=True,
                                           text=True).stdout.split()
                self.assertEqual(sorted(set(from_grep)),
                                 sorted(set(run.knowledge_home._REQUIREMENT_ID.findall(text))))



def codex_session(items: list[dict], *, end: bool = True, thread: str = "t1") -> list[dict]:
    """One Codex session after the harness's translator; ``end=False`` is a session killed before turn.completed."""
    translate = hosts.host("codex").translator()
    raw = [{"type": "thread.started", "thread_id": thread}]
    raw += [{"type": "item.completed", "item": item} for item in items]
    if end:
        raw.append({"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 5,
                                                        "output_tokens": 2}})
    return [json.loads(line) for event in raw for line in translate((json.dumps(event) + "\n").encode())]


def rollout_line(kind: str, t: float, payload: dict) -> str:
    """One Codex rollout record, stamped the way Codex stamps it (UTC, milliseconds, Z)."""
    stamp = datetime.datetime.fromtimestamp(t, datetime.timezone.utc).isoformat(timespec="milliseconds")
    return json.dumps({"timestamp": stamp.replace("+00:00", "Z"), "type": kind, "payload": payload})


def usage_line(t: float, thread: str, session: str, response: str, total: int, output: int = 100,
               reasoning: int | None = None) -> str:
    return rollout_line("token_usage_record", t, {
        "thread_id": thread, "session_id": session, "response_id": response,
        "usage": {"input_tokens": total - output, "output_tokens": output, "total_tokens": total,
                  **({} if reasoning is None else {"reasoning_output_tokens": reasoning})}})


def count_line(t: float, window: int, total: int, *, after_compaction: bool = False) -> str:
    """The token_count event that follows a call (or, after a compaction, reports the shrunken context)."""
    last = {"input_tokens": 0 if after_compaction else total - 100, "output_tokens": 100, "total_tokens": total}
    return rollout_line("event_msg", t, {"type": "token_count", "info": {
        "model_context_window": window, "last_token_usage": last, "total_token_usage": {"total_tokens": total}}})


def compacted_line(t: float, request: str) -> str:
    return rollout_line("compacted", t, {"message": "", "compaction_response_id": request, "replacement_history": []})


def write_rollout(out: Path, name: str, lines: list[str]) -> Path:
    path = out / "home" / ".codex" / "sessions" / "2026" / "10" / "04" / f"rollout-{name}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    return path


def thread_calls(thread: str, session: str, window: int, calls: list[tuple]) -> list[str]:
    """(time, response id, total, request?) rows as the records Codex writes: a call is a usage record and a
    token_count; a compaction request is a usage record with no token_count, then the compacted record and the
    token_count of the shrunken context."""
    lines = []
    for t, response, total, request in calls:
        lines.append(usage_line(t, thread, session, response, total))
        if request:
            lines += [compacted_line(t + 0.01, response), count_line(t + 0.02, window, 500, after_compaction=True)]
        else:
            lines.append(count_line(t + 0.01, window, total))
    return lines


# Two threads: the root thread (6 calls, 2 compactions) and a sub-agent forked from it (3 calls, 1 compaction).
# The compaction requests carry the heaviest totals (9500, 8000, 12000): a request holds the whole context.
ROOT_THREAD = [(1000, "r1", 1000, False), (1015, "r2", 2000, False), (1020, "r3", 9000, False),
               (1030, "rq1", 9500, True), (1040, "r4", 3000, False), (1050, "r5", 4000, False),
               (1060, "rq2", 8000, True), (1070, "r6", 1500, False)]
SUB_THREAD = [(1025, "s1", 5000, False), (1045, "s2", 6000, False), (1055, "sq1", 12000, True),
              (1065, "s3", 7000, False)]


def two_thread_rollouts() -> list[list[str]]:
    root = [rollout_line("session_meta", 999, {"id": "root"}), *thread_calls("root", "root", 10000, ROOT_THREAD)]
    root.insert(5, count_line(1020.02, 10000, 9000))  # a repeated token_count: not a call
    root.append('{"timestamp": "2026-10-04T')  # the half-written last line of a rollout a live run still writes
    # The sub-agent's file opens with its parent's last compacted record, stamped at the fork: its request is
    # a record in the parent's file, so it is inherited history and not this thread's compaction.
    sub = [rollout_line("session_meta", 1015, {"id": "sub", "forked_from_id": "root"}),
           compacted_line(1015.0, "rq1"), *thread_calls("sub", "root", 20000, SUB_THREAD)]
    return [root, sub]


class RolloutContextTest(unittest.TestCase):
    """The Codex rollout reader: what counts as a call, a compaction and the main thread's peak (R15)."""

    WINDOWS = [[999, 1015], [1015, 1035], [1035, 1055], [1055, 1100], None]

    def read(self, files: list[list[str]], windows=None) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            for number, lines in enumerate(files):
                write_rollout(out, f"{number}", lines)
            return rollouts.rollout_context(out, self.WINDOWS if windows is None else windows)

    def test_a_compaction_request_is_not_a_call_and_never_the_peak(self):
        got = self.read(two_thread_rollouts())
        # 6 root calls; the 8 root usage records minus the two compaction requests, and the repeated token_count
        # neither adds a call nor changes the peak. The requests' 9500 and 8000 are heavier than any call.
        self.assertEqual((got["calls"], got["peak"], got["peakPct"], got["window"]), (6, 9000, 90.0, 10000))
        self.assertEqual(got["compactions"], 2)

    def test_sub_agent_threads_are_reported_apart_from_the_main_thread(self):
        got = self.read(two_thread_rollouts())
        # The sub-agent's own compaction counts for it; the inherited copy of its parent's does not count at all.
        self.assertEqual(got["subagents"], {"calls": 3, "peak": 7000, "compactions": 1})
        self.assertEqual(got["window"], 10000, "the sub-agent's 20000 window is not the main thread's")

    def test_each_stage_window_gets_its_own_calls_peak_and_compactions(self):
        got = self.read(two_thread_rollouts())
        self.assertEqual(got["perStage"], [
            {"calls": 2, "peak": 2000, "peakPct": 20.0, "compactions": 0},  # the call at the window's end counts
            {"calls": 1, "peak": 9000, "peakPct": 90.0, "compactions": 1},  # and not again in the next window
            {"calls": 2, "peak": 4000, "peakPct": 40.0, "compactions": 0},
            {"calls": 1, "peak": 1500, "peakPct": 15.0, "compactions": 1},
            None])  # a stage with no window has no figures, not zeros
        self.assertEqual(sum(w["calls"] for w in got["perStage"] if w), got["calls"])

    def test_a_call_outside_every_window_is_in_the_headline_only(self):
        got = self.read(two_thread_rollouts(), [[999, 1015]])
        self.assertEqual(got["calls"], 6)
        self.assertEqual(got["perStage"], [{"calls": 2, "peak": 2000, "peakPct": 20.0, "compactions": 0}])

    def test_no_rollout_is_unmeasured_with_its_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(rollouts.rollout_context(Path(tmp), []), {"unmeasured": rollouts.NO_ROLLOUTS})
            (Path(tmp) / "home" / ".codex" / "sessions").mkdir(parents=True)  # a home with no rollout in it
            self.assertEqual(rollouts.rollout_context(Path(tmp), []), {"unmeasured": rollouts.NO_ROLLOUTS})
        self.assertIn("rollout-*.jsonl", rollouts.NO_ROLLOUTS)

    def test_rollouts_with_no_main_thread_call_are_unmeasured_not_zero_calls(self):
        sub_only = [rollout_line("session_meta", 1000, {"id": "sub"}), *thread_calls("sub", "root", 20000, SUB_THREAD)]
        self.assertEqual(self.read([sub_only]), {"unmeasured": rollouts.NO_CALLS})
        self.assertEqual(self.read([[rollout_line("session_meta", 1000, {"id": "root"})]]),
                         {"unmeasured": rollouts.NO_CALLS})

    def test_a_window_nobody_reported_is_none_and_gives_no_percentage(self):
        root = [usage_line(1000, "root", "root", "r1", 4000), usage_line(1001, "root", "root", "r2", 5000)]
        got = self.read([root], [[999, 1100]])
        self.assertEqual((got["window"], got["calls"], got["peak"], got["peakPct"]), (None, 2, 5000, None))
        self.assertEqual(got["perStage"], [{"calls": 2, "peak": 5000, "peakPct": None, "compactions": 0}])

    def test_a_resumed_session_is_another_root_thread_whose_calls_and_compactions_add_up(self):
        first = [usage_line(1000, "a", "a", "a1", 1000), *thread_calls("a", "a", 10000, [(1001, "aq", 6000, True)])]
        second = thread_calls("b", "b", 10000, [(2000, "b1", 3000, False), (2001, "bq", 7000, True),
                                               (2002, "b2", 2500, False)])
        got = self.read([first, second], [])
        self.assertEqual((got["calls"], got["peak"], got["compactions"]), (3, 3000, 2))
        self.assertEqual(got["subagents"], {"calls": 0, "peak": None, "compactions": 0})


class MixedHostTurnsTest(unittest.TestCase):
    """Live finding (round 2, Grok resume): a run's events.jsonl can hold turn rows of two shapes, those with a `call`
    key (Claude's assistant messages) and those without (Grok's usage events); per_stage crashed on the mix, after the
    host had finished, so the run got no metrics and no review export."""

    def test_per_stage_counts_the_rows_that_carry_a_call_and_ignores_the_rest(self):
        accepted = [{"stage": "a", "outcome": "done", "t": 105.0}, {"stage": "b", "outcome": "done", "t": 112.0}]
        stamps = {n: 100.0 + n for n in range(21)}
        turns = [{"t": 101.5, "input": 10, "call": True}, {"t": 102.0, "input": 20},
                 {"t": 103.0, "input": 30, "call": False}, {"t": 106.0, "input": 40, "call": True}]
        rows = metrics.per_stage(accepted, turns, {}, stamps, None, context_window=100)
        self.assertEqual([r["context"]["calls"] for r in rows], [1, 1])
        self.assertEqual([r["context"]["peak"] for r in rows], [30, 40])
        self.assertEqual([r["turns"] for r in rows], [3, 1])


class StageWindowsTest(unittest.TestCase):
    """The windows per_stage already derived are one implementation the rollout reader shares."""

    def test_windows_line_up_with_the_stage_rows_and_none_marks_unavailable_timing(self):
        accepted = [{"stage": "seeded", "outcome": "done", "t": 90.0},     # before the host's first event
                    {"stage": "a", "outcome": "done", "t": 105.0},
                    {"stage": "no-stamp", "outcome": "done", "t": None},
                    {"stage": "after-gap", "outcome": "done", "t": 112.0},  # its lower boundary is unknown
                    {"stage": "b", "outcome": "revise", "t": 118.0}]
        stamps = {n: 100.0 + n for n in range(21)}
        windows = metrics.stage_windows(accepted, stamps, "open")
        rows = metrics.per_stage(accepted, [{"t": 101.5, "input": 1}, {"t": 114.0, "input": 1}], {}, stamps, "open")
        self.assertEqual(len(windows), len(rows))
        self.assertEqual([w is None for w in windows], [r.get("timing") == "unavailable" for r in rows])
        self.assertEqual(windows, [None, (99.0, 105.0, 100.0), None, None, (112.0, 118.0, 112.0),
                                   (118.0, 120.0, 118.0)])
        for window, row in zip(windows, rows):
            if window:
                self.assertEqual(row["seconds"], round(window[1] - window[2], 1))
        self.assertEqual(metrics.stage_windows(accepted, {}, "open"), [None] * 6)
        self.assertEqual(metrics.stage_windows([], stamps, None), [])


class CodexRolloutMetricsTest(unittest.TestCase):
    """metrics.collect on a Codex run reads calls, window, peak and compactions from its rollouts, and says
    why when they are absent; the other counters Codex cannot show stay unmeasured."""

    ACCEPTED = [("A1", "intake", "done", 105.0), ("A2", "spec", "done", 113.0)]

    def rollouts(self) -> list[list[str]]:
        root = thread_calls("root", "root", 10000, [(101, "r1", 1000, False), (104.5, "r2", 3000, False),
                                                    (108, "rq", 3500, True), (110, "r3", 2000, False),
                                                    (120, "r4", 500, False)])  # after the last acceptance
        sub = thread_calls("sub", "root", 20000, [(102, "s1", 9000, False)])
        return [root, sub]

    def test_a_codex_run_with_rollouts_has_calls_window_peak_and_compactions(self):
        m = collect_stream(codex_stream(12), self.ACCEPTED, rollout_files=self.rollouts())
        self.assertEqual((m["model_calls"], m["window_tokens"], m["compactions"]), (4, 10000, 1))
        self.assertEqual(m["tokens"], {"input_peak": 3000})
        for name in ("model_calls", "window_tokens", "compactions"):
            self.assertNotIn(name, m["unmeasured"], name)
        # What the Codex stream still cannot show stays unmeasured: the four stage and detector counters.
        self.assertEqual(set(m["unmeasured"]), {"stage_turns", "truncated_outputs", "cancelled_tool_calls",
                                                "knowledge_reads"})
        self.assertEqual([r["context"] for r in m["stages"]], [
            {"calls": 2, "peak": 3000, "peakPct": 30.0, "compactions": 0},
            {"calls": 1, "peak": 2000, "peakPct": 20.0, "compactions": 1}])
        self.assertTrue(all(r["turns"] is None for r in m["stages"]), "stage turns stay unmeasured")
        self.assertIn("compactions 1,", metrics.summary_lines(m)[0])

    def test_a_codex_run_without_rollouts_names_them_as_the_reason(self):
        m = collect_stream(codex_stream(12), self.ACCEPTED)
        self.assertEqual((m["model_calls"], m["window_tokens"], m["compactions"]), (None, None, None))
        self.assertEqual(m["tokens"], {"input_peak": None})
        for name in ("model_calls", "window_tokens", "compactions"):
            self.assertIn(name, m["unmeasured"], name)
        self.assertIn(rollouts.NO_ROLLOUTS, m["unmeasured"]["model_calls"])
        self.assertIn(rollouts.NO_ROLLOUTS, m["unmeasured"]["window_tokens"])
        self.assertTrue(all("context" not in r for r in m["stages"]))
        self.assertEqual(len(m["unmeasured"]), 7)  # the five Codex had, and the two new figures

    def test_rollouts_are_not_read_when_the_host_reported_per_call_usage(self):
        # A Grok or Claude stream measures its own calls; a stray rollout beside it does not change them.
        stream = [{"type": "usage", "usage": {"input_tokens": 1, "output_tokens": 1}}] * 2
        m = collect_stream(stream, self.ACCEPTED, rollout_files=self.rollouts())
        self.assertEqual((m["model_calls"], m["compactions"]), (2, 0), "Grok's own events: no compaction event")
        self.assertTrue(all("context" not in r for r in m["stages"]))

    def test_rollouts_that_hold_no_call_are_unmeasured_with_the_reason(self):
        m = collect_stream(codex_stream(3), self.ACCEPTED, rollout_files=[[rollout_line("session_meta", 1, {})]])
        self.assertIsNone(m["model_calls"])
        self.assertIn(rollouts.NO_CALLS, m["unmeasured"]["model_calls"])


class ModelCallsAndWindowTest(unittest.TestCase):
    """A model call is a Claude message, not an event: `turns` keeps counting events (baselines.jsonl stores that
    definition and run.py compares it across runs), and a window the host did not report is unknown, not 0."""

    @staticmethod
    def message(message_id, text="x"):
        message = {"usage": {"input_tokens": 10}, "content": [{"type": "text", "text": text}]}
        if message_id is not None:
            message["id"] = message_id
        return {"type": "assistant", "message": message}

    @staticmethod
    def result(*windows, num_turns=1):
        return {"type": "result", "subtype": "success", "num_turns": num_turns, "total_cost_usd": 1.0,
                "modelUsage": {f"model-{n}": {"contextWindow": w, "inputTokens": 5}
                               for n, w in enumerate(windows)}}

    def test_three_events_of_one_message_are_one_call_and_three_turns(self):
        m = collect_stream([self.message("m1")] * 3, [])
        self.assertEqual((m["model_calls"], m["turns"]), (1, 3))
        self.assertNotIn("model_calls", m["unmeasured"])

    def test_events_without_an_id_count_one_each_and_a_repeated_id_counts_once(self):
        stream = [self.message("m1"), self.message("m1"), self.message("m2"), self.message(None),
                  self.message(None), self.message(""), self.message("m1")]
        m = collect_stream(stream, [])
        self.assertEqual((m["model_calls"], m["turns"]), (5, 7))  # m1, m2, two with no id, one empty id

    def test_the_window_comes_from_the_result_event(self):
        m = collect_stream([self.message("m1"), self.result(1000000)], [])
        self.assertEqual(m["window_tokens"], 1000000)
        self.assertNotIn("window_tokens", m["unmeasured"])
        # Two sessions of one run that agree on it are one window.
        m = collect_stream([self.message("m1"), self.result(1000000), self.message("m2"), self.result(1000000)], [])
        self.assertEqual(m["window_tokens"], 1000000)

    def test_a_window_nobody_reported_or_that_disagrees_is_null_with_its_reason(self):
        for label, stream in (("no result event", [self.message("m1")]),
                              ("a result without modelUsage", [self.message("m1"),
                                                               {"type": "result", "subtype": "success"}]),
                              ("a bool or zero window", [self.message("m1"), self.result(True, 0)]),
                              ("two models with different windows", [self.message("m1"), self.result(200000, 1000000)])):
            with self.subTest(label):
                m = collect_stream(stream, [])
                self.assertIsNone(m["window_tokens"])
                self.assertIn("context window", m["unmeasured"]["window_tokens"])
                self.assertEqual(m["model_calls"], 1, "the window being unknown does not hide the calls")

    def test_a_grok_stream_counts_its_usage_events_and_has_no_window(self):
        m = collect_stream([{"type": "usage", "usage": {"input_tokens": 1, "output_tokens": 1}}] * 4, [])
        self.assertEqual((m["model_calls"], m["turns"]), (4, 4))
        self.assertIsNone(m["window_tokens"])
        self.assertEqual(set(m["unmeasured"]), {"window_tokens", "unreported_sessions"})  # Grok marks no session start

    def test_a_host_with_no_per_call_usage_has_no_call_count_not_zero_calls(self):
        m = collect_stream(codex_stream(3), [])
        self.assertIsNone(m["model_calls"])
        self.assertIsNone(m["window_tokens"])
        self.assertIn("per-call usage", m["unmeasured"]["model_calls"])
        self.assertEqual(m["turns"], 3, "the session's own total is still reported")


def codex_command(n: int, command: str = "echo ok", output: str = "ok\n", code: int = 0) -> dict:
    return {"id": f"item_{n}", "type": "command_execution", "command": command, "aggregated_output": output,
            "exit_code": code, "status": "completed" if code == 0 else "failed"}


class HostSignalCountersTest(unittest.TestCase):
    """Counters read only from Grok's event shapes are unmeasured on every other host (review 2: compactions,
    truncated_outputs, cancelled_tool_calls, knowledge_reads), never a 0 or a look-alike that reads as a measurement."""

    GROK_ONLY = ("compactions", "truncated_outputs", "cancelled_tool_calls", "knowledge_reads")
    ACCEPTED = [("A1", "intake", "done", 105.0), ("A2", "spec", "done", 113.0)]

    def codex(self) -> dict:
        items = [codex_command(0), codex_command(1, "node --test", "ℹ tests 3\nℹ fail 1\nℹ cancelled 0\n", 1),
                 {"id": "item_2", "type": "file_change", "status": "completed",
                  "changes": [{"path": "/w/docs/shiploop/spec.md", "kind": "update"}]}]
        return collect_stream(codex_session(items), self.ACCEPTED)

    def test_a_codex_failing_test_run_is_not_a_host_refusal_and_a_write_is_not_a_read(self):
        m = self.codex()
        for name in self.GROK_ONLY:
            self.assertIn(name, m["unmeasured"], name)
        self.assertEqual(m["cancelled_tool_calls"], [], "'cancelled 0' in a node --test summary is not a refusal")
        self.assertEqual(m["knowledge_reads"], [], "Codex's file_change is a write, listed as a read")
        self.assertIsNone(m["compactions"])
        self.assertIsNone(m["truncated_outputs"])
        self.assertIsNone(metrics.count(m, "cancelled_tool_calls"))
        self.assertNotIn("model_glue", m["unmeasured"], "Codex's tool calls are still read")
        first = metrics.summary_lines(m)[0]
        for text in ("compactions not measured", "truncated outputs not measured", "cancelled tool calls not measured"):
            self.assertIn(text, first)

    def test_a_claude_run_cannot_show_them_either_with_or_without_tool_calls(self):
        compact = {"type": "system", "subtype": "compact_boundary", "compact_metadata": {"trigger": "auto"}}
        read = {"type": "assistant", "message": {"usage": {"input_tokens": 5}, "content": [
            {"type": "tool_use", "id": "r1", "name": "Read", "input": {"file_path": "/w/docs/shiploop/spec.md"}}]}}
        text_only = {"type": "assistant", "message": {"usage": {"input_tokens": 5},
                                                      "content": [{"type": "text", "text": "hello"}]}}
        for label, stream in (("tool calls", [compact, read, *claude_stream(["ls"])]),
                              ("text only", [text_only, {"type": "result", "subtype": "success", "num_turns": 1}])):
            with self.subTest(label):
                m = collect_stream(stream, self.ACCEPTED)
                for name in self.GROK_ONLY:
                    self.assertIn(name, m["unmeasured"], name)
                self.assertIsNone(m["compactions"])
                self.assertIsNone(m["truncated_outputs"])
                self.assertIn("compactions not measured", metrics.summary_lines(m)[0])

    def test_a_grok_stream_still_counts_each_one(self):
        stream = [
            {"type": "usage", "usage": {"input_tokens": 1000, "output_tokens": 10}},
            {"type": "tool_call", "toolCallId": "a", "toolName": "read_file",
             "rawInput": {"target_file": "/w/docs/shiploop/spec.md"}},
            {"type": "tool_call_update", "toolCallId": "a", "rawOutput": {"exit_code": 0, "truncated": True}},
            {"type": "tool_call", "toolCallId": "c", "rawInput": {"command": "git init -b main"}},
            {"type": "tool_call_update", "toolCallId": "c", "status": "failed", "rawOutput": None, "content": [
                {"type": "content", "content": {"type": "text",
                                                "text": "User cancelled the execution for tool `run_terminal_command`"}}]},
            {"type": "auto_compact_completed"},
            {"type": "end", "stopReason": "end_turn", "num_turns": 1, "total_cost_usd": 1.0}]
        m = collect_stream(stream, self.ACCEPTED)
        self.assertEqual(set(m["unmeasured"]), {"window_tokens", "unreported_sessions"},
                         "every detector reads a Grok stream; its events mark no session start")
        self.assertEqual((m["compactions"], m["truncated_outputs"]), (1, 1))
        self.assertEqual(m["cancelled_tool_calls"], ["git init -b main"])
        self.assertEqual(m["knowledge_reads"], ["docs/shiploop/spec.md"])
        first = metrics.summary_lines(m)[0]
        self.assertIn("compactions 1, truncated outputs 1, cancelled tool calls 1", first)


class HostSignalCountersThroughMainTest(PrintedCase):
    """result.json, the baseline row and the printed line carry null, not 0, for what the host cannot show."""

    def test_claude_and_codex_runs_commit_null_for_the_grok_only_counters(self):
        for host in ("claude", "codex"):
            with self.subTest(host):
                code, result, printed = self.invoke_printed(host, "done")
                self.assertEqual(code, 0, result)
                row = self.last_row()
                for name in HostSignalCountersTest.GROK_ONLY:
                    self.assertIn(name, result["metrics"]["unmeasured"], name)
                for name in ("compactions", "truncated_outputs", "cancelled_tool_calls"):
                    self.assertIsNone(result["metrics"][name], name)
                    self.assertIsNone(row[name], name)
                self.assertIn("compactions not measured", printed)
                self.assertIn("truncated outputs not measured", printed)


class ModelCallsThroughMainTest(PrintedCase):
    """result.json carries the two figures beside the other whole-run scalars; the baseline row does not
    (they are not comparison keys: the row's turns keep the events-based definition)."""

    def test_result_json_carries_calls_and_window_and_the_baseline_row_does_not(self):
        code, result, _ = self.invoke_printed("claude", "done")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["metrics"]["model_calls"], 1)  # the fake's one assistant event
        self.assertIsNone(result["metrics"]["window_tokens"])  # its result event reports no modelUsage
        self.assertIn("window_tokens", result["metrics"]["unmeasured"])
        row = self.last_row()
        for name in ("model_calls", "window_tokens"):
            self.assertNotIn(name, row)
        self.assertIn("window_tokens", row["unmeasured"])
        code, result, _ = self.invoke_printed("codex", "done")
        self.assertIsNone(result["metrics"]["model_calls"])
        self.assertIn("model_calls", result["metrics"]["unmeasured"])
        self.assertIn("rollout", result["metrics"]["unmeasured"]["model_calls"])
        self.assertIn("compactions", result["metrics"]["unmeasured"])

    def test_a_codex_run_whose_home_holds_rollouts_reports_them_in_every_record(self):
        os.environ["FAKE_ROLLOUT"] = "1"
        self.addCleanup(os.environ.pop, "FAKE_ROLLOUT", None)
        code, result, _ = self.invoke_printed("codex", "done")
        self.assertEqual(code, 0, result)
        m = result["metrics"]
        self.assertEqual((m["model_calls"], m["compactions"]), (2, 0))  # 0 is a measurement: the rollouts exist
        self.assertIsNone(m["window_tokens"])  # no token_count record reported one
        self.assertIn("model_context_window", m["unmeasured"]["window_tokens"])
        for name in ("model_calls", "compactions"):
            self.assertNotIn(name, m["unmeasured"], name)
        self.assertEqual(json.loads((Path(result["output"]) / "metrics.json").read_text())["tokens"],
                         {"input_peak": 2000})
        row = self.last_row()
        self.assertEqual(row["compactions"], 0)
        self.assertNotIn("compactions", row["unmeasured"])


class UnknownTurnsTest(unittest.TestCase):
    """A session that never reported its turns leaves the whole-run turns unknown, as it does the cost (review 2)."""

    ACCEPTED = [("A1", "intake", "done", 105.0)]

    def killed(self) -> list[dict]:
        return codex_session([codex_command(n) for n in range(30)], end=False, thread="t1")

    def test_a_codex_session_killed_before_its_end_event_has_no_turn_count(self):
        m = collect_stream(self.killed(), self.ACCEPTED, status="active", stage="spec")
        self.assertIsNone(m["turns"], "30 tool calls and no end event: the host reported no turn count")
        self.assertEqual((m["sessions"], m["unreported_sessions"]), ([], 1))
        self.assertIsNone(m["cost_usd"])
        self.assertIn("turns not reported", metrics.summary_lines(m)[0])
        self.assertEqual(metrics.turns_text(m), "not reported")

    def test_a_killed_session_beside_an_ended_one_makes_the_turns_a_lower_bound(self):
        stream = self.killed() + codex_session([codex_command(n) for n in range(3)], thread="t2")
        m = collect_stream(stream, self.ACCEPTED)
        self.assertEqual(m["turns"], 3)
        self.assertEqual(m["unreported_sessions"], 1)
        self.assertIn("turns 3 (lower bound)", metrics.summary_lines(m)[0])

    def test_an_ended_session_is_a_plain_number_and_a_reported_zero_is_a_measurement(self):
        m = collect_stream(codex_session([codex_command(n) for n in range(4)]), self.ACCEPTED)
        self.assertEqual(m["turns"], 4)
        self.assertNotIn("lower bound", metrics.summary_lines(m)[0].split("cost")[0])
        zero = collect_stream([{"type": "end", "stopReason": "end_turn", "num_turns": 0}], [])
        self.assertEqual(zero["turns"], 0)
        self.assertEqual(metrics.turns_text(zero), "0")

    def test_progress_says_the_turns_are_unknown_and_survives_the_null_counters(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            stream = self.killed()
            (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in stream))
            text = progress.report(out)
            again = progress.report(out)  # the memo it wrote must read back
        self.assertIn("turns not reported", text)
        self.assertNotIn("turns 0", text)
        self.assertIn("not measured on this host", text)
        self.assertNotIn("not measured on this host", again, "said once per run, not on every poll")


class CliSummaryRecordTest(PrintedCase):
    """result.json's `cli` agrees with `termination` and the metrics: the same stop reason, and no turn count that
    nobody reported turned into 0 (review 2: summarize_events)."""

    def test_a_claude_api_error_is_an_error_in_the_cli_record_too(self):
        code, result, printed = self.invoke_printed("claude", "api-error")
        stops = result["termination"]["session_stops"]
        self.assertTrue(stops[0].startswith("error: api_error"), stops)
        self.assertEqual(result["cli"]["stop"], stops[0])
        self.assertEqual([s["stop"] for s in result["cli"]["sessions"]], stops)

    def test_a_normal_stop_and_a_failed_codex_turn(self):
        code, result, printed = self.invoke_printed("claude", "done")
        self.assertEqual((result["cli"]["stop"], result["cli"]["sessions"][0]["stop"]), ("success", "success"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text(json.dumps({"type": "end", "stopReason": "error", "num_turns": 2,
                                        "error": "You've hit your usage limit.\nTry later"}) + "\n")
            seen = run.summarize_events(path)
        self.assertEqual(seen["stop"], "error: You've hit your usage limit. Try later")
        self.assertEqual(seen["sessions"][0]["stop"], seen["stop"])

    def test_the_cli_summary_does_not_turn_a_missing_turn_count_into_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text(json.dumps({"type": "end", "stopReason": "end_turn", "total_cost_usd": None}) + "\n")
            seen = run.summarize_events(path)
        self.assertIsNone(seen["num_turns"])
        self.assertIsNone(seen["cost_usd"])


class SuiteTmpCheckHostTest(HarnessCase):
    """The suite's /tmp collision check reads the writes of every host's runs, Claude's included."""

    @staticmethod
    def claude_writer(out: Path, target: str) -> Path:
        out.mkdir()
        stream = [{"type": "assistant", "message": {"usage": {"input_tokens": 1}, "content": [
            {"type": "tool_use", "id": "u1", "name": "Bash", "input": {"command": f"echo x > {target}"}}]}},
            {"type": "result", "subtype": "success", "num_turns": 1}]
        (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in stream))
        return out

    @staticmethod
    def grok_writer(out: Path, target: str) -> Path:
        out.mkdir()
        stream = [{"type": "usage", "usage": {"input_tokens": 1}},
                  {"type": "tool_call", "toolCallId": "1", "rawInput": {"command": f"echo x > {target}"}}]
        (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in stream))
        return out

    def test_two_claude_runs_that_write_the_same_tmp_name_collide(self):
        outs = [self.claude_writer(self.tmp / name, "/tmp/shared-notes.txt") for name in ("a", "b")]
        self.assertEqual(run.shared_tmp_writes(outs), {"/tmp/shared-notes.txt": ["a", "b"]})

    def test_a_collision_is_found_across_hosts(self):
        outs = [self.claude_writer(self.tmp / "a", "/tmp/shared-notes.txt"),
                self.grok_writer(self.tmp / "b", "/tmp/shared-notes.txt"),
                self.grok_writer(self.tmp / "c", "/tmp/shared-notes.txt"),
                self.claude_writer(self.tmp / "d", "/tmp/own-notes.txt")]
        self.assertEqual(run.shared_tmp_writes(outs), {"/tmp/shared-notes.txt": ["a", "b", "c"]})

    def test_a_claude_suite_names_a_tmp_collision_and_records_no_unchecked_run(self):
        cases = {"first": {"style": "s", "prompt": "p", "checks": []},
                 "second": {"style": "t", "prompt": "p", "checks": []}}
        for attr, data in (("CASES", cases), ("SUITES", {"wide": {"kind": "breadth", "cases": ["first", "second"]}})):
            path = self.tmp / (attr.lower() + ".json")
            path.write_text(json.dumps(data))
            saved = getattr(run, attr)
            setattr(run, attr, path)
            self.addCleanup(setattr, run, attr, saved)
        os.environ["FAKE_MODE"] = "done"
        os.environ["FAKE_COMMAND"] = "echo x > /tmp/shared-notes.txt"
        self.addCleanup(os.environ.pop, "FAKE_COMMAND", None)
        out, printed = self.tmp / "suite-out", io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = run.main(["--suite", "wide", "--host", "claude", "--claude-bin", str(self.fakes["claude"]),
                             "--output", str(out), "--plugin-dir", str(self.plugin),
                             "--baseline", str(self.baselines)])
        self.assertEqual(code, 0, printed.getvalue())
        result = json.loads((out / "suite-result.json").read_text())
        self.assertEqual(result["shared_tmp_writes"], {"/tmp/shared-notes.txt": ["first", "second"]})
        self.assertNotIn("tmp_writes_unmeasured", result)
        self.assertIn("/tmp names written by more than one case", printed.getvalue())
        self.assertNotIn("not checked", printed.getvalue())



class SessionStopSubtypeTest(unittest.TestCase):
    """An error result keeps the subtype the host named, so a turn or budget limit is not a bare 'error' (review 2)."""

    def test_an_error_subtype_is_kept_with_its_first_listed_error(self):
        stop = metrics.session_stop({"type": "result", "subtype": "error_max_turns", "is_error": True,
                                     "errors": ["Reached maximum number of turns (3)"]})
        self.assertEqual(stop, "error: error_max_turns: Reached maximum number of turns (3)")
        self.assertEqual(metrics.session_stop({"type": "result", "subtype": "error_during_execution", "is_error": True}),
                         "error: error_during_execution")
        budget = {"type": "result", "subtype": "error_max_budget_usd", "is_error": True, "terminal_reason": "max_budget"}
        self.assertEqual(metrics.session_stop(budget), "error: error_max_budget_usd max_budget")

    def test_a_success_subtype_with_an_api_error_does_not_repeat_success(self):
        stop = metrics.session_stop({"type": "result", "subtype": "success", "is_error": True,
                                     "terminal_reason": "api_error", "result": "API Error: rate limit"})
        self.assertEqual(stop, "error: api_error: API Error: rate limit")


class ContextTokensTest(unittest.TestCase):
    """A call's context is its input, its cache reads and its cache writes, where the host reports them."""

    CLAUDE_USAGE = {"input_tokens": 3, "cache_creation_input_tokens": 90000, "cache_read_input_tokens": 10000,
                    "output_tokens": 50}

    def test_a_cache_write_is_context(self):
        self.assertEqual(metrics.context_tokens(self.CLAUDE_USAGE), 100003)
        self.assertEqual(metrics.context_tokens({"input_tokens": 3, "cache_read_input_tokens": 10000}), 10003)
        self.assertEqual(metrics.context_tokens({"cache_creation_input_tokens": 7}), 7)

    def test_a_call_with_no_figure_has_no_context(self):
        for usage in (None, {}, {"output_tokens": 5}, {"input_tokens": None}, {"input_tokens": True}):
            self.assertIsNone(metrics.context_tokens(usage), usage)

    def test_the_run_peak_counts_the_cache_write_and_a_stream_without_usage_has_none(self):
        def message(n: int, usage: dict) -> dict:
            return {"type": "assistant", "message": {"id": f"m{n}", "usage": usage,
                                                     "content": [{"type": "text", "text": "x"}]}}
        quiet = {"input_tokens": 3, "cache_read_input_tokens": 50000, "cache_creation_input_tokens": 0}
        stream = [message(0, quiet), message(1, self.CLAUDE_USAGE), message(2, quiet)]
        self.assertEqual(collect_stream(stream, [])["tokens"]["input_peak"], 100003)
        self.assertEqual(collect_stream([{"type": "assistant", "message": {"content": []}}], [])["tokens"],
                         {"input_peak": None})
        self.assertEqual(collect_stream(codex_stream(3), [])["tokens"], {"input_peak": None})


class ResumeCliThroughMainTest(PrintedCase):
    """The prompt that continues a run names the ShipLoop CLI of the plugin the run started on, through run.main.

    A Claude run built from a checkout was continued with a bare `shiploop next` (ClaudeHost.plugin_cli looked only
    under <output>/marketplace); a run continued on another host used the first host's installed copy or nothing."""

    def setUp(self):
        super().setUp()
        (self.plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": "9.9.9"}))
        patched = mock.patch.object(run, "POLL_SECONDS", 0.2, create=True)  # the interrupt test waits on the poll
        patched.start()
        self.addCleanup(patched.stop)

    def resume(self, out: Path, host: str, plugin: Path | None = None, *extra: str) -> None:
        released = {"origin_main": "a" * 40, "local_head": "a" * 40, "local_behind_main": False,
                    "catalog_version": "9.9.9", "shiploop_version": None, "unreleased": [], "ci": "success"}
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(run, "released_versions", return_value=released):
            run.main(["--host", host, f"--{host}-bin", str(self.fakes[host]), "--resume-run", str(out),
                      "--plugin-dir", str(plugin or self.plugin), "--baseline", str(self.baselines),
                      "--max-resumes", "0", *extra])

    def test_a_claude_checkout_run_is_continued_with_its_own_cli_in_the_prompt(self):
        code, first, _ = self.invoke_printed("claude", "active")
        self.assertEqual(first["shiploop"]["status"], "active")
        self.log.unlink()
        os.environ["FAKE_MODE"] = "active"
        self.resume(Path(first["output"]), "claude")
        argv = self.seen()["argv"]
        prompt = argv[argv.index("-p") + 1]
        self.assertIn("This session ended while the ShipLoop run was still active", prompt)
        self.assertIn(f'python3 "{self.cli}" next --run-dir "', prompt)
        self.assertNotIn("`shiploop next", prompt)

    def test_a_resume_inside_the_run_names_the_cli_the_run_started_on(self):
        # The resume loop (a Grok or Codex session that ended while ShipLoop was active) is the third call site that
        # builds this prompt, beside the first resume and the resume after an interrupt.
        code, result, _ = self.invoke_printed("grok", "stuck", "--max-resumes", "1")
        sessions = [json.loads(line) for line in Path(str(self.log) + ".sessions").read_text().splitlines()]
        self.assertEqual(len(sessions), 2)
        self.assertIsNotNone(sessions[1]["resumed"])
        command = f'python3 "{self.cli}" next --run-dir "'
        self.assertIn(command, sessions[1]["prompt"])
        self.assertIn(command, (Path(result["output"]) / "resume-1.txt").read_text())
        self.assertNotIn("`shiploop next", sessions[1]["prompt"])

    def test_a_run_continued_on_another_host_keeps_the_cli_it_started_on(self):
        code, first, _ = self.invoke_printed("grok", "stuck", "--max-resumes", "0")
        other = self.tmp / "other" / "plugins" / "skill-craft"
        (other / ".claude-plugin").mkdir(parents=True)
        (other / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": "9.9.9"}))
        other_cli = run.shiploop_cli(other)
        other_cli.parent.mkdir(parents=True)
        other_cli.write_text("")
        self.log.unlink()
        os.environ["FAKE_MODE"] = "stuck"
        self.resume(Path(first["output"]), "codex", other)
        prompt = self.seen()["prompt"]
        self.assertIn(f'python3 "{self.cli}" next --run-dir "', prompt)  # the first host's install, not the new one
        self.assertNotIn(str(other_cli), prompt)

    def test_the_resume_after_an_interrupt_names_the_cli_the_run_started_on(self):
        code, result, _ = self.invoke_printed("claude", "chain-hang", "--interrupt-at", "chain-launched")
        self.assertEqual(code, 0, result)
        argv = self.seen()["argv"]
        prompt = argv[argv.index("-p") + 1]
        self.assertIn("This session ended while the ShipLoop run was still active", prompt)
        self.assertIn(f'python3 "{self.cli}" next --run-dir "', prompt)

    def test_a_resume_whose_plugin_cli_is_gone_is_refused_before_any_host_starts(self):
        code, first, _ = self.invoke_printed("grok", "stuck", "--max-resumes", "0")
        self.cli.unlink()
        self.log.unlink()
        Path(str(self.log) + ".sessions").unlink()
        os.environ["FAKE_MODE"] = "stuck"
        with self.assertRaisesRegex(SystemExit, "ShipLoop CLI.*is gone"):
            self.resume(Path(first["output"]), "grok")
        self.assertFalse(self.log.exists(), "no host was started")

    def test_a_regrade_never_needs_the_cli(self):
        code, first, _ = self.invoke_printed("grok", "done")
        self.cli.unlink()
        self.resume(Path(first["output"]), "grok")  # done: graded again, no host, no prompt
        self.assertTrue(json.loads((Path(first["output"]) / "result.json").read_text())["process"]["regraded"])


class RunCliTest(unittest.TestCase):
    """run.run_cli: one rule for the CLI a run uses, for the seed and for every resume prompt."""

    def test_claude_loads_its_plugin_dir_so_the_plugin_dir_is_its_cli(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            for plugin in (out / "marketplace/plugins/skill-craft", out / "build/plugins/skill-craft"):
                self.assertEqual(run.run_cli("claude", out, plugin), plugin / "skills/shiploop/scripts/shiploop")

    def test_grok_and_codex_use_the_copy_they_installed_and_fall_back_to_the_plugin_dir(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            build = out / "build/plugins/skill-craft"
            self.assertEqual(run.run_cli("grok", out, build), run.shiploop_cli(build))
            grok_copy = out / "home/.grok/installed-plugins/skill-craft-1234/skills/shiploop/scripts/shiploop"
            grok_copy.parent.mkdir(parents=True)
            grok_copy.write_text("")
            self.assertEqual(run.run_cli("grok", out, build), grok_copy)
            codex_copy = out / "home/.codex/plugins/cache/whichguy/skill-craft/1.0.0/skills/shiploop/scripts/shiploop"
            codex_copy.parent.mkdir(parents=True)
            codex_copy.write_text("")
            self.assertEqual(run.run_cli("codex", out, build), codex_copy)


class StopFileTest(PrintedCase):
    """A requested stop (<output>/stop) ends the host with its records written, and is never a pass."""

    def setUp(self):
        super().setUp()
        patched = mock.patch.object(run, "POLL_SECONDS", 0.2, create=True)
        patched.start()
        self.addCleanup(patched.stop)

    def sessions(self) -> list[dict]:
        return [json.loads(line) for line in Path(str(self.log) + ".sessions").read_text().splitlines()]

    def stop_when_the_host_runs(self, out: Path, session: int = 1) -> None:
        """Create the stop file once the fake host has started its `session`th session (1 = the first)."""
        def ask():
            sessions = Path(str(self.log) + ".sessions")
            for _ in range(400):
                if sessions.exists() and len(sessions.read_text().splitlines()) >= session:
                    break
                time.sleep(0.05)
            (out / "stop").write_text("")
        threading.Thread(target=ask, daemon=True).start()

    def main(self, out: Path, *extra: str) -> tuple[int, dict, str]:
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), mock.patch.object(
                run, "review_export", return_value="review export: fake") as exporter:
            code = run.main(["--host", "grok", "--grok-bin", str(self.fakes["grok"]), "--output", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines),
                             "--timeout", "30", *extra])
        self.exporter = exporter
        return code, json.loads((out / "result.json").read_text()), printed.getvalue()

    def test_the_stop_file_ends_the_host_and_the_records_are_written_without_a_relaunch(self):
        os.environ["FAKE_MODE"] = "hang-active"
        out = self.tmp / "out-stop"
        self.stop_when_the_host_runs(out)
        code, result, printed = self.main(out)
        self.assertEqual(code, 1, "a requested stop is not a finished run: it must never exit 0")
        self.assertEqual((result["process"]["status"], result["process"]["pass"]), ("stopped", None))
        t = result["termination"]
        self.assertEqual((t["process_status"], t["sessions"], t["engine_status"]), ("stopped", 1, "active"))
        self.assertEqual(t["resume_stop"], f"stopped by {out.resolve() / 'stop'}")
        self.assertEqual(len(self.sessions()), 1, "a stopped host is not relaunched")
        self.assertFalse((out / "stop").exists(), "the request is consumed when it is acted on")
        self.assertTrue((out / "metrics.json").is_file())
        self.exporter.assert_called_once()
        self.assertFalse(self.baselines.exists(), "a stopped run is not a baseline")
        self.assertFalse((out / "mismatch.md").exists(), "a requested stop is not a mismatch to explain")
        self.assertRegex(printed, r"(?m)^STOPPED  shiploop e2e case=")
        self.assertIn("host stopped rc=-9", printed)

    def test_a_stop_requested_as_a_session_ends_stops_the_resume_loop_and_reads_as_stopped_everywhere(self):
        os.environ["FAKE_MODE"] = "stuck-stop"
        out = self.tmp / "out-stop-between"
        code, result, printed = self.main(out)
        self.assertEqual(code, 1)
        self.assertEqual(len(self.sessions()), 1, "the loop would otherwise resume up to the cap")
        self.assertEqual(result["termination"]["resume_stop"], f"stopped by {out.resolve() / 'stop'}")
        self.assertFalse((out / "stop").exists())
        self.assertRegex(printed, r"(?m)^STOPPED  shiploop e2e case=")
        # The host ended by itself (exit 0) as the request arrived, yet the run reads as stopped in every record, the
        # same as a killed host (SPEC: a requested stop has no process verdict); the session keeps its own status.
        self.assertEqual((result["process"]["status"], result["process"]["pass"]), ("stopped", None))
        self.assertEqual(result["termination"]["process_status"], "stopped")
        self.assertEqual([s["status"] for s in result["process"]["sessions"]], ["exited"])
        self.assertIn("host stopped rc=0", printed)
        self.assertFalse(self.baselines.exists(), "a stopped run is not a baseline")

    def test_a_stop_during_a_resumed_session_reads_as_stopped_and_is_not_relaunched(self):
        os.environ["FAKE_MODE"] = "hang-resumed"
        out = self.tmp / "out-stop-resumed"
        self.stop_when_the_host_runs(out, session=2)
        code, result, printed = self.main(out, "--timeout", "120")  # a resume needs more than 60 s of the run deadline left
        self.assertEqual(code, 1)
        self.assertEqual(len(self.sessions()), 2, "one session, one resume, and no third launch")
        self.assertEqual((result["process"]["status"], result["process"]["pass"]), ("stopped", None))
        self.assertEqual([s["status"] for s in result["process"]["sessions"]], ["exited", "stopped"])
        self.assertEqual(result["termination"]["resume_stop"], f"stopped by {out.resolve() / 'stop'}")
        self.assertRegex(printed, r"(?m)^STOPPED  shiploop e2e case=")
        self.assertFalse((out / "stop").exists())

    def test_a_stop_before_any_engine_state_exists_writes_no_baseline_row_and_no_resume_command(self):
        # The host was killed before ShipLoop wrote any state, so the engine status is unknown: still not a finished run.
        os.environ["FAKE_MODE"] = "hang"
        out = self.tmp / "out-stop-no-state"
        self.stop_when_the_host_runs(out)
        code, result, printed = self.main(out)
        self.assertEqual(code, 1)
        t = result["termination"]
        self.assertEqual((t["process_status"], t["engine_status"]), ("stopped", "unknown"))
        self.assertFalse(self.baselines.exists(), "the row would be offered as the last comparable row")
        self.assertIn("baseline  nothing compared: the run is not finished", printed)
        self.assertEqual(printed.count("--resume-run"), 1, "only the start line: a run with no engine state cannot be resumed")

    def test_a_stale_stop_file_does_not_stop_a_later_resume(self):
        code, first, _ = self.invoke_printed("grok", "stuck", "--max-resumes", "0")
        out = Path(first["output"])
        (out / "stop").write_text("")  # left over from a stop nobody consumed
        os.environ["FAKE_MODE"] = "done"
        with contextlib.redirect_stdout(io.StringIO()):
            run.main(["--host", "codex", "--codex-bin", str(self.fakes["codex"]), "--resume-run", str(out),
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        result = json.loads((out / "result.json").read_text())
        self.assertEqual(result["termination"]["resume_stop"], "ShipLoop run is done")
        self.assertNotEqual(result["process"]["status"], "stopped")
        self.assertFalse((out / "stop").exists())

    def test_a_stop_never_answers_a_blocked_run(self):
        code, first, _ = self.invoke_printed("grok", "stuck", "--max-resumes", "0")
        out = Path(first["output"])
        shutil.rmtree(out / "work" / ".shiploop")
        (out / "work" / ".shiploop").mkdir()
        run.store.write_record(out / "work" / ".shiploop" / "state.md",
                               {"status": "blocked", "stage": "test-refine", "status_reason": "waiting for a person"})
        (out / "stop").write_text("")
        self.log.unlink(missing_ok=True)
        with contextlib.redirect_stdout(io.StringIO()):
            run.main(["--host", "grok", "--grok-bin", str(self.fakes["grok"]), "--resume-run", str(out),
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        result = json.loads((out / "result.json").read_text())
        self.assertFalse(self.log.exists(), "no host was started for a blocked run")
        self.assertEqual(result["shiploop"]["status"], "blocked")
        self.assertNotEqual(result["termination"].get("process_status"), "stopped")
        self.assertFalse((out / "stop").exists(), "the request was cleared at the start, not acted on")


class GradeOnlyTest(PrintedCase):
    """--resume-run <dir> --grade-only: records from what is on disk, no host, for a run whose harness was killed."""

    def killed_harness_run(self) -> Path:
        code, result, _ = self.invoke_printed("grok", "stuck", "--max-resumes", "0")
        out = Path(result["output"])
        for name in ("result.json", "metrics.json"):  # a task kill gives the harness no chance to write them
            (out / name).unlink()
        shutil.rmtree(out / "review-export", ignore_errors=True)
        self.log.unlink()
        return out

    def grade_only(self, out: Path, *extra: str) -> tuple[int, dict, str]:
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), mock.patch.object(
                run, "review_export", return_value="review export: fake") as exporter:
            code = run.main([*extra, "--resume-run", str(out), "--grade-only", "--plugin-dir", str(self.plugin),
                             "--baseline", str(self.baselines)])
        self.exporter = exporter
        return code, json.loads((out / "result.json").read_text()), printed.getvalue()

    def test_an_active_run_whose_harness_was_killed_is_graded_without_a_host(self):
        out = self.killed_harness_run()
        recorded = json.loads((out / "invocation.json").read_text())
        rows = self.baselines.read_text() if self.baselines.exists() else ""
        code, result, printed = self.grade_only(out)
        self.assertEqual(code, 1, "an unfinished run is not a pass")
        self.assertFalse(self.log.exists(), "no host process was started")
        self.assertTrue((out / "metrics.json").is_file())
        self.exporter.assert_called_once()
        self.assertTrue(result["process"]["regraded"])
        self.assertEqual(result["shiploop"]["status"], "active")
        self.assertEqual((result["host"], result["model"], result["effort"]),
                         (recorded["host"], recorded["model"], recorded["effort"]))
        t = result["termination"]
        self.assertEqual((t["process_status"], t["engine_status"], t["engine_unaccepted_stage"]),
                         (run.NOT_OBSERVED, "active", "test-refine"))
        self.assertEqual(self.baselines.read_text() if self.baselines.exists() else "", rows,
                         "a grade-only writes no baseline row")
        self.assertIn("no host ran (regraded); engine active", printed)

    def test_a_regrade_names_a_refusal_whose_exit_the_host_did_not_show(self):
        # A Claude refusal behind `| head` has no exit; the printed line says so, and does not print "exit None".
        out = self.killed_harness_run()
        (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in recorded_calls("refusal-behind-head")))
        code, result, printed = self.grade_only(out)
        line = next(ln for ln in printed.splitlines() if ln.startswith("  failed    shiploop"))
        self.assertTrue(line.startswith("  failed    shiploop complete exit not shown: ShipLoop navigator: evidence_refs cite"), line)
        self.assertNotIn("exit None", printed)

    def test_a_regrade_prints_no_resume_command_because_its_flags_are_not_the_runs(self):
        # The grading invocation's --timeout is the default (10800 s, above any task limit); presenting it as the exact
        # command that continues the run would send a resume to be killed with no records.
        out = self.killed_harness_run()
        code, result, printed = self.grade_only(out)
        self.assertEqual(result["shiploop"]["status"], "active")
        self.assertNotIn("--resume-run", printed)
        self.assertNotRegex(printed, r"--timeout \d+")
        line = next(ln for ln in printed.splitlines() if ln.startswith("  resume"))
        self.assertIn("printed when the run started", line)
        self.assertIn("--timeout below the launcher's limit", line)

    def test_a_paused_run_is_graded_under_the_flag_and_refused_without_it(self):
        out = self.killed_harness_run()
        shutil.rmtree(out / "work" / ".shiploop")
        (out / "work" / ".shiploop").mkdir()
        run.store.write_record(out / "work" / ".shiploop" / "state.md", {"status": "paused", "stage": "spec",
                                                                        "status_reason": "paused for a person"})
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(SystemExit, "needs an active, blocked or finished"):
                run.main(["--resume-run", str(out), "--plugin-dir", str(self.plugin)])
        code, result, _ = self.grade_only(out)
        self.assertEqual(result["shiploop"]["status"], "paused")
        self.assertFalse(self.log.exists())

    def test_the_flag_needs_a_run_to_grade_and_a_run_with_no_state_is_still_refused(self):
        with self.assertRaisesRegex(SystemExit, "--grade-only needs --resume-run"):
            run.main(["--grade-only", "--host", "grok", "--output", str(self.tmp / "never")])
        self.assertFalse((self.tmp / "never").exists())
        code, result, _ = self.invoke_printed("grok", "nothing", "--max-resumes", "0")
        out = Path(result["output"])
        with self.assertRaisesRegex(SystemExit, "needs an active, blocked or finished"):
            run.main(["--resume-run", str(out), "--grade-only", "--plugin-dir", str(self.plugin)])


class ResumeCommandTest(PrintedCase):
    """The harness prints the exact command that continues the run, before any host spend and again when it is left active.

    invocation.json keeps the host argv but not the harness flags, so a command with only --resume-run would fall
    back to the default --timeout (10800 s), which is above the limit of a launching task."""

    def commands(self, printed: str) -> list[list[str]]:
        lines = [ln for ln in printed.splitlines() if "--resume-run" in ln]
        return [shlex.split(ln[ln.index("python3 "):]) for ln in lines]

    def test_the_start_and_the_end_print_the_exact_command_that_continues_the_run(self):
        code, result, printed = self.invoke_printed("grok", "stuck", "--max-resumes", "0", "--timeout", "900",
                                                    "--permission-mode", "plan", "--max-budget-usd", "12.5")
        found = self.commands(printed)
        self.assertEqual(len(found), 2, "before the host starts, and again for a run left active")
        self.assertEqual(found[0], found[1])
        self.assertLess(printed.index("--resume-run"), printed.index("tool  run_terminal_command"))
        argv = found[0]
        self.assertEqual((argv[0], Path(argv[1])), ("python3", Path(run.__file__).resolve()))
        parsed = run.parser().parse_args(argv[2:])
        self.assertEqual(parsed.resume_run, Path(result["output"]))
        self.assertEqual((parsed.host, parsed.model, parsed.effort), ("grok", "grok-4.7", "medium"))
        self.assertEqual((parsed.timeout, parsed.max_resumes, parsed.max_budget_usd, parsed.permission_mode),
                         (900, 0, 12.5, "plan"))  # each non-default, so dropping any flag from the command fails here
        self.assertEqual(parsed.grok_bin, str(self.fakes["grok"]))
        self.assertEqual(parsed.plugin_dir, self.plugin)

    def test_a_finished_run_prints_it_once_and_a_host_without_an_effort_prints_none(self):
        code, result, printed = self.invoke_printed("claude", "done")
        found = self.commands(printed)
        self.assertEqual(len(found), 1, "nothing to continue at the end")
        self.assertNotIn("--effort", found[0])
        self.assertEqual(run.parser().parse_args(found[0][2:]).host, "claude")

    def test_the_printed_command_continues_the_run_in_place(self):
        code, result, printed = self.invoke_printed("grok", "stuck", "--max-resumes", "0")
        argv = self.commands(printed)[0][2:]
        os.environ["FAKE_MODE"] = "done"
        self.log.unlink()
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(
                run, "released_versions", return_value={
                    "origin_main": "a" * 40, "local_head": "a" * 40, "local_behind_main": False,
                    "catalog_version": None, "shiploop_version": None, "unreleased": [], "ci": "success"}):
            run.main([*argv, "--baseline", str(self.baselines)])
        resumed = json.loads((Path(result["output"]) / "result.json").read_text())
        self.assertEqual(resumed["termination"]["resume_stop"], "ShipLoop run is done")
        self.assertEqual(resumed["output"], result["output"])


class UnfinishedRunBaselineTest(PrintedCase):
    """No baseline row for a run whose engine is still active when the harness ends."""

    def setUp(self):
        super().setUp()
        patched = mock.patch.object(run, "POLL_SECONDS", 0.2, create=True)  # a deadline is noticed on the next poll
        patched.start()
        self.addCleanup(patched.stop)

    def test_a_run_left_active_by_a_spent_resume_budget_writes_no_row(self):
        code, result, printed = self.invoke_printed("grok", "stuck", "--max-resumes", "1")
        self.assertEqual(result["termination"]["engine_status"], "active")
        self.assertFalse(self.baselines.exists())
        self.assertIn("baseline  nothing compared: the run is not finished (its engine is still active)", printed)
        self.assertEqual(printed.count("--resume-run"), 2, "the start line and the end line carry the command")

    def test_a_deadline_ends_with_the_records_leaves_the_run_resumable_and_writes_no_row(self):
        # The README's recipe for a task with a limit: --timeout below it, so the harness finalizes.
        code, result, printed = self.invoke_printed("grok", "hang-active", "--timeout", "2")
        out = Path(result["output"])
        self.assertEqual(code, 1)
        self.assertTrue((out / "metrics.json").is_file())
        self.assertRegex(printed, r"review export")
        t = result["termination"]
        self.assertEqual((t["process_status"], t["resume_stop"], t["engine_status"]),
                         ("timeout", "run deadline spent", "active"))
        self.assertFalse(self.baselines.exists(), "the first segment of a long run is not a baseline")

    def test_a_finished_run_still_writes_its_row(self):
        code, result, _ = self.invoke_printed("grok", "done")
        self.assertEqual(code, 0)
        self.assertEqual(len(self.baselines.read_text().splitlines()), 1)

    def test_a_host_killed_at_the_deadline_before_any_engine_state_writes_no_row(self):
        # The audit's reproduction: the existing `hang` fake, --timeout 3, engine status unknown. It appended a row with
        # process status timeout, which scan_baseline then offered as the last comparable row.
        code, result, printed = self.invoke_printed("grok", "hang", "--timeout", "3")
        t = result["termination"]
        self.assertEqual((t["process_status"], t["engine_status"]), ("timeout", "unknown"))
        self.assertFalse(self.baselines.exists(), "a host the deadline killed is not a finished run")
        self.assertIn("baseline  nothing compared: the run is not finished (the harness ended the host: timeout; "
                      "engine unknown), so it is not a baseline", printed)
        self.assertEqual(printed.count("--resume-run"), 1,
                         "a run with no engine state is refused by --resume-run, so only the start line carries a command")

    def test_a_later_run_is_not_compared_with_the_killed_one(self):
        self.invoke_printed("grok", "hang", "--timeout", "3")
        code, result, printed = self.invoke_printed("grok", "done")
        self.assertEqual(code, 0, result)
        self.assertIn("baseline  nothing compared: no earlier row for hello", printed)

    def test_a_host_that_ends_by_itself_with_no_engine_state_still_writes_its_row(self):
        # Its own exit is the ending the row records, unlike a deadline or a stop the harness imposed.
        code, result, _ = self.invoke_printed("grok", "nothing")
        self.assertEqual((result["termination"]["engine_status"], result["termination"]["process_status"]),
                         ("unknown", "exited"))
        self.assertEqual(len(self.baselines.read_text().splitlines()), 1)


class ClaudeCodeVersionTest(PrintedCase):
    """The host CLI build is recorded with the run: the two Sonnet runs of 2026-10-06 and 2026-10-07 ran one prompt on
    Claude Code 2.1.291 and 2.1.292, a variable no record of the harness named until now (only the init event held it)."""

    def init(self, version=None) -> dict:
        return {"type": "system", "subtype": "init", "model": "m", **({} if version is None else {"claude_code_version": version})}

    def test_the_init_event_s_version_is_recorded_in_the_metrics(self):
        m = collect_stream([self.init("2.1.292"), *claude_stream(["echo a"])], [])
        self.assertEqual(m["claude_code_version"], "2.1.292")

    def test_sessions_on_two_builds_name_both_and_a_host_without_a_version_records_none(self):
        both = collect_stream([self.init("2.1.291"), *claude_stream(["echo a"]), self.init("2.1.292"),
                               *claude_stream(["echo b"])], [])
        self.assertEqual(both["claude_code_version"], "2.1.291, 2.1.292")
        self.assertIsNone(collect_stream([self.init(), *claude_stream(["echo a"])], [])["claude_code_version"])
        self.assertIsNone(collect_stream(codex_stream(2), [])["claude_code_version"])

    def test_a_run_through_main_leaves_the_version_in_metrics_json_and_result_json(self):
        code, result, _ = self.invoke_printed("claude", "done")
        self.assertEqual(json.loads((Path(result["output"]) / "metrics.json").read_text())["claude_code_version"], "0.0.1-fake")
        self.assertEqual(result["metrics"]["claude_code_version"], "0.0.1-fake")
        code, grok, _ = self.invoke_printed("grok", "done")
        self.assertIsNone(grok["metrics"]["claude_code_version"])


class KeepAwakeTest(unittest.TestCase):
    """A host session runs under `caffeinate -d -i` on macOS, so the display stays on for the whole run.

    On 2026-10-07 the display was off from 06:04 to 10:10 (pmset log) and headless Chrome never loaded a page in the
    Grok run's window, 09:25 to 10:12; on 2026-10-06, with the display on, the same host loaded it. The correlation is
    unproven as a cause (a display woken by `caffeinate -u -d` still hung once), so this removes the variable and
    claims nothing more. -i, the earlier hold, keeps the machine from idle-sleeping."""

    ARGV = [sys.executable, "-c", "print('hi')"]

    def test_on_macos_the_session_is_wrapped_to_hold_the_display_and_the_system_awake(self):
        with mock.patch.object(sys, "platform", "darwin"), mock.patch.object(run.shutil, "which", return_value="/usr/bin/caffeinate"):
            self.assertEqual(run.keep_awake(self.ARGV), ["/usr/bin/caffeinate", "-d", "-i", *self.ARGV])

    def test_elsewhere_or_without_the_tool_the_argv_is_unchanged(self):
        with mock.patch.object(sys, "platform", "linux"), mock.patch.object(run.shutil, "which", return_value="/usr/bin/caffeinate"):
            self.assertEqual(run.keep_awake(self.ARGV), self.ARGV)
        with mock.patch.object(sys, "platform", "darwin"), mock.patch.object(run.shutil, "which", return_value=None):
            self.assertEqual(run.keep_awake(self.ARGV), self.ARGV)

    def launched(self, platform: str) -> tuple[list | None, str]:
        """Run one session through run.launch with a recording caffeinate first on PATH."""
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            tool = temp / "bin" / "caffeinate"
            tool.parent.mkdir()
            tool.write_text(f"#!{sys.executable}\nimport json, os, sys\n"
                            "open(os.environ['CAFFEINATE_LOG'], 'w').write(json.dumps(sys.argv[1:]))\n"
                            "args = sys.argv[1:]\nwhile args and args[0].startswith('-'):\n    args = args[1:]\n"
                            "os.execv(args[0], args)\n")
            tool.chmod(tool.stat().st_mode | stat.S_IXUSR)
            out = temp / "out"
            (out / "work").mkdir(parents=True)
            log = temp / "caffeinate.log"
            with mock.patch.dict(os.environ, {"PATH": f"{tool.parent}{os.pathsep}{os.environ['PATH']}",
                                              "CAFFEINATE_LOG": str(log)}), \
                    mock.patch.object(sys, "platform", platform), \
                    nothing_listens():  # launch looks for leftovers; not in the real table
                result = run.launch(self.ARGV, out / "work", out, dict(os.environ), 60, watch=False)
            self.assertEqual((result["status"], result["returncode"]), ("exited", 0))
            return (json.loads(log.read_text()) if log.exists() else None), (out / "events.jsonl").read_text()

    def test_a_session_started_by_launch_runs_under_the_wrapper_on_macos_and_the_host_still_runs(self):
        argv, events = self.launched("darwin")
        self.assertEqual(argv, ["-d", "-i", *self.ARGV])
        self.assertEqual(events.strip(), "hi")

    def test_a_session_started_by_launch_elsewhere_is_not_wrapped_and_still_runs(self):
        argv, events = self.launched("linux")
        self.assertIsNone(argv, "caffeinate was not run")
        self.assertEqual(events.strip(), "hi")


LSOF_LISTENING = """p969
crapportd
u501
f14
n*:58318
f15
n*:58318
p2059
cOllama
u501
f3
n127.0.0.1:11434
p300
cmDNSResponder
u0
f7
n*:5353
p63973
cnode
u501
f12
n*:3457
f13
n[::1]:3457
"""
LSOF_CWD = "p2059\nfcwd\nn/\np63973\nfcwd\nn/Users/dadleet/e2e-runs/20261008/r1-checkers-sonnet/work\n"
PS_COMMANDS = ("  300 /usr/sbin/mDNSResponder\n 2059 /Applications/Ollama.app/Contents/Resources/ollama serve\n"
               "63973 node /Users/dadleet/e2e-runs/20261008/r1-checkers-sonnet/.shiploop-runs/work-1/worktree/server.js\n")


def listener(pid: int, cwd: str | None, argv: str = "", ports: tuple = (3457,)) -> dict:
    return {"pid": pid, "command": argv.split()[0] if argv else "x", "ports": list(ports), "cwd": cwd, "argv": argv}


@needs_listeners
class ListenerParseSelectionTest(unittest.TestCase):
    """Which processes the harness stops: read from lsof's field output, chosen by place, and never the harness itself.

    Pure checks over captured output, so they run on a runner with no lsof (the real-process classes skip there)."""

    def test_lsof_field_output_is_parsed_into_pid_ports_cwd_and_argv(self):
        self.assertEqual(listeners.listeners_of(LSOF_LISTENING, 501),
                         [{"pid": 969, "command": "rapportd", "ports": [58318]},
                          {"pid": 2059, "command": "Ollama", "ports": [11434]},
                          {"pid": 63973, "command": "node", "ports": [3457]}], "own user only; one port listed once")
        self.assertEqual(listeners.cwds_of(LSOF_CWD), {2059: "/", 63973: "/Users/dadleet/e2e-runs/20261008/r1-checkers-sonnet/work"})
        self.assertEqual(listeners.argvs_of(PS_COMMANDS)[63973],
                         "node /Users/dadleet/e2e-runs/20261008/r1-checkers-sonnet/.shiploop-runs/work-1/worktree/server.js")

        def fake_run(argv):
            return LSOF_LISTENING if "-iTCP" in argv else LSOF_CWD if "cwd" in argv else PS_COMMANDS
        with mock.patch.object(listeners, "_run", side_effect=fake_run), mock.patch.object(listeners.os, "getuid", return_value=501):
            seen = {item["pid"]: item for item in listeners.observe()}
        self.assertEqual(sorted(seen), [969, 2059, 63973])
        self.assertEqual((seen[63973]["ports"], seen[63973]["cwd"]),
                         ([3457], "/Users/dadleet/e2e-runs/20261008/r1-checkers-sonnet/work"))
        self.assertTrue(seen[63973]["argv"].endswith("/worktree/server.js"))
        self.assertEqual((seen[969]["cwd"], seen[969]["argv"]), (None, ""), "a process that vanished between the calls has neither")

    def test_a_name_that_is_not_host_and_port_is_not_a_port_and_never_raises(self):
        # lsof prints host:port for a TCP listener; a name without a colon (an all-digit one included) is no endpoint to list.
        odd = "p1\ncx\nu501\nn123\nnno-colon-here\nn*:80\nnhost:notaport\n"
        self.assertEqual(listeners.listeners_of(odd, 501), [{"pid": 1, "command": "x", "ports": [80]}])

    def test_only_a_listener_inside_the_case_folder_on_a_path_boundary_is_selected(self):
        folder = "/e2e/case-1"
        chosen = [listener(10, "/e2e/case-1/work"), listener(11, "/e2e/case-1"),
                  listener(12, "/", "node /e2e/case-1/.shiploop-runs/x/server.js"),
                  listener(13, "/", "node server.js --root=/e2e/case-1/site"), listener(14, "/e2e/case-1/work/deep/er")]
        left = [listener(20, "/e2e/case-10/work"),
                listener(21, "/", "node /e2e/case-10/server.js"), listener(22, "/", "tail -f /e2e/case-1-other/log"),
                listener(23, "/e2e/case-1/work"), listener(24, None, ""), listener(25, "/", "python3 -m http.server"),
                listener(1, "/e2e/case-1/work"), listener(26, "/e2e")]
        got = {item["pid"] for item in listeners.under(chosen + left, folder, protected={23})}
        self.assertEqual(got, {10, 11, 12, 13, 14}, "pid 23 is protected, pid 1 is never touched, siblings and parents are not inside")

    def test_a_folder_reached_through_a_symlink_is_matched_by_either_spelling(self):
        with tempfile.TemporaryDirectory() as temp:
            real = Path(temp).resolve() / "real"
            (real / "case").mkdir(parents=True)
            link = Path(temp) / "link"
            link.symlink_to(real)
            asked = str(link / "case")  # how the output folder was spelled; lsof reports a cwd as the real path
            by_cwd, by_argv = listener(30, str(real / "case" / "work")), listener(31, "/", f"node {asked}/server.js")
            self.assertEqual({i["pid"] for i in listeners.under([by_cwd, by_argv], asked)}, {30, 31})

    def test_the_harness_and_its_ancestors_are_protected(self):
        parents = {500: 400, 400: 300, 300: 1, 600: 1}
        self.assertEqual(listeners.ancestors(parents, 500), {500, 400, 300})
        self.assertEqual(listeners.ancestors(parents, 999), {999}, "a pid with no parent row is only itself")
        with mock.patch.object(listeners, "_run", return_value="  1 0\n 500 400\n 400 300\n 300 1\n"), \
                mock.patch.object(listeners.os, "getpid", return_value=500):
            self.assertEqual(listeners.protected_pids(), {500, 400, 300})
        with mock.patch.object(listeners, "_run", side_effect=listeners.Unobserved("ps not found")), \
                mock.patch.object(listeners.os, "getpid", return_value=500), mock.patch.object(listeners.os, "getppid", return_value=400):
            self.assertEqual(listeners.protected_pids(), {500, 400}, "no process table: at least this process and its parent")

    def test_a_tool_that_cannot_run_is_unobserved_with_its_reason(self):
        with mock.patch.object(listeners.subprocess, "run", side_effect=FileNotFoundError):
            with self.assertRaisesRegex(listeners.Unobserved, "lsof not found"):
                listeners.observe()
        with mock.patch.object(listeners.subprocess, "run",
                               side_effect=listeners.subprocess.TimeoutExpired(["lsof"], listeners.LSOF_TIMEOUT)):
            with self.assertRaisesRegex(listeners.Unobserved, "lsof timed out"):
                listeners.observe()
        failed = subprocess.CompletedProcess(["lsof"], 2, stdout="", stderr="lsof: permission denied\nmore\n")
        with mock.patch.object(listeners.subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(listeners.Unobserved, r"lsof exited 2: lsof: permission denied"):
                listeners.observe()
        none_listening = subprocess.CompletedProcess(["lsof"], 1, stdout="", stderr="")
        with mock.patch.object(listeners.subprocess, "run", return_value=none_listening):
            self.assertEqual(listeners.observe(), [], "exit 1 with no output is a measured none")

    def pass_record(self, *reaped: int, survived: tuple = (), observed: bool = True, reason: str | None = None) -> dict:
        if not observed:
            return {"observed": False, "reason": reason}
        return {"observed": True, "reaped": [dict(listener(pid, "/x"), ended_by="SIGTERM") for pid in reaped],
                "survived": [listener(pid, "/x") for pid in survived]}

    def test_the_passes_of_a_run_merge_and_an_unseen_pass_never_reads_as_none(self):
        self.assertIsNone(listeners.merge_left_behind([]), "a regrade ran no pass")
        self.assertIsNone(listeners.merge_left_behind([None, None]))
        merged = listeners.merge_left_behind([self.pass_record(7), self.pass_record(8, survived=(9,)), self.pass_record(survived=(9,))])
        self.assertIsNotNone(merged)
        self.assertEqual(merged["observed"], True)
        self.assertEqual([i["pid"] for i in merged["reaped"]], [7, 8])
        self.assertEqual([i["pid"] for i in merged["survived"]], [9], "one process seen twice is listed once")
        later = listeners.merge_left_behind([self.pass_record(survived=(9,)), self.pass_record(9)])
        self.assertEqual(([i["pid"] for i in later["reaped"]], later["survived"]), ([9], []), "stopped by a later pass: not a survivor")
        nothing = listeners.merge_left_behind([self.pass_record(), self.pass_record()])
        self.assertEqual(nothing, {"observed": True, "reaped": [], "survived": []}, "two passes that looked and found none")
        blind = listeners.merge_left_behind([self.pass_record(observed=False, reason="lsof not found"),
                                             self.pass_record(observed=False, reason="lsof not found")])
        self.assertEqual(blind, {"observed": False, "reason": "lsof not found"}, "no pass looked: no reaped key to read as none")
        partial = listeners.merge_left_behind([self.pass_record(7), self.pass_record(observed=False, reason="lsof timed out after 30s")])
        self.assertIsNotNone(partial)
        self.assertEqual((partial["observed"], partial["reason"]), (False, "lsof timed out after 30s"))
        self.assertEqual([i["pid"] for i in partial["reaped"]], [7], "what the pass that looked found is kept beside the reason")
        again = listeners.merge_left_behind([partial, self.pass_record(8)])  # a resume merges the earlier record with its own
        self.assertIsNotNone(again)
        self.assertEqual(([i["pid"] for i in again["reaped"]], again["observed"]), ([7, 8], False))

    def test_the_printed_line_names_what_was_stopped_and_what_could_not_be_seen(self):
        self.assertIsNone(listeners.left_behind_line(None))
        self.assertIsNone(listeners.left_behind_line({"observed": True, "reaped": [], "survived": []}), "a clean run prints nothing")
        line = listeners.left_behind_line(listeners.merge_left_behind([self.pass_record(7), self.pass_record(survived=(9,))]))
        self.assertEqual(line, "  left      stopped pid 7 x (port 3457) by SIGTERM; could not stop pid 9 x (port 3457)")
        blind = listeners.left_behind_line({"observed": False, "reason": "lsof not found"})
        self.assertEqual(blind, "  left      not observed: lsof not found")


needs_lsof = unittest.skipUnless(shutil.which("lsof") and shutil.which("ps"),
                                 "the real-process tests need lsof and ps on PATH (the pure parse and selection tests still run)")


def end_quietly(proc: subprocess.Popen) -> None:
    with contextlib.suppress(ProcessLookupError):
        proc.kill()
    proc.wait()
    if proc.stdout:
        proc.stdout.close()


def kill_leaked(portfile: Path) -> None:
    """Stop a listener a fake host left behind (it was reparented, so there is no Popen); it also expires on its own."""
    if portfile.exists():
        with contextlib.suppress(ProcessLookupError):
            os.kill(int(portfile.read_text().split()[0]), 9)


def answers(port: int) -> bool:
    with socket.socket() as probe:
        probe.settimeout(2)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def refuses_soon(port: int, seconds: float = 5.0) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        if not answers(port):
            return True
        time.sleep(0.05)
    return False


def isolate_git(case: unittest.TestCase) -> None:
    """A fake host runs real git: neither the machine's system nor its global config (signing, an lfs filter) may reach it."""
    patched = mock.patch.dict(os.environ, {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
    patched.start()
    case.addCleanup(patched.stop)


class CaseRunCase(PrintedCase):
    """A harness case that runs one named case into its own folder and returns what the run recorded."""

    def case_main(self, name: str, *extra: str, mode: str = "done", host: str = "claude", env: dict | None = None):
        out = self.tmp / name
        os.environ["FAKE_MODE"] = mode
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), mock.patch.dict(os.environ, env or {}):
            code = run.main(["--host", host, f"--{host}-bin", str(self.fakes[host]), "--output", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), *extra])
        return code, json.loads((out / "result.json").read_text()), printed.getvalue(), out

    def reaped(self, result: dict) -> list[int]:
        return [i["pid"] for i in (result.get("left_behind") or {}).get("reaped", [])]


class RealListeners:
    """Mixin: tests that start real servers and let the harness stop them, in a world scoped to the test's own folder."""

    def scope_to_tmp(self) -> None:
        """What lsof shows is only what has its working directory under self.tmp, so no other session's server (or a leaked one
        on this machine) can change a result; the real lsof, ps and signals are still used. The scope is checked here, not by
        listeners.under, and a signal to any pid outside it is refused: a defect in the code under test (or a mutant of it) must
        never be able to stop a process of the machine's user that the test did not start."""
        root = os.path.realpath(self.tmp)

        def in_tmp() -> list[dict]:
            return [item for item in REAL_OBSERVE() if item.get("cwd") and (item["cwd"] == root or item["cwd"].startswith(root + os.sep))]

        real_signal = listeners._signal

        def guarded_signal(pid: int, number: int) -> None:
            if pid not in {item["pid"] for item in in_tmp()}:
                raise AssertionError(f"refusing to signal pid {pid}: it is not a listener under the test's own folder")
            real_signal(pid, number)

        for patcher in (mock.patch.object(listeners, "observe", side_effect=in_tmp),
                        mock.patch.object(listeners, "_signal", side_effect=guarded_signal)):
            patcher.start()
            self.addCleanup(patcher.stop)
        isolate_git(self)

    def serve(self, cwd: Path, *flags: str) -> tuple[subprocess.Popen, int]:
        """A listening server whose working directory is `cwd`, as a model leaves one; killed when the test ends."""
        cwd.mkdir(parents=True, exist_ok=True)
        portfile = self.tmp / f"port-{len(list(self.tmp.glob('port-*')))}"
        proc = subprocess.Popen([sys.executable, "-c", LISTENER_SOURCE, str(portfile), *flags], cwd=cwd, start_new_session=True,
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(end_quietly, proc)
        for _ in range(200):
            if portfile.exists():
                break
            time.sleep(0.05)
        else:
            raise AssertionError("the test's listener never started")
        proc.portfile = portfile
        return proc, int(portfile.read_text().split()[1])


@needs_lsof
@needs_listeners
class ReapTest(RealListeners, unittest.TestCase):
    """listeners.reap with the real lsof, ps and signals, on servers the test starts."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.scope_to_tmp()

    def test_a_folder_with_nothing_under_it_is_a_measured_none(self):
        self.assertEqual(listeners.reap(self.tmp / "empty"), {"observed": True, "reaped": [], "survived": []})

    def test_a_listener_under_the_folder_is_stopped_and_a_sibling_with_the_same_prefix_is_not(self):
        inside, port = self.serve(self.tmp / "case-1" / "work")
        beside, beside_port = self.serve(self.tmp / "case-10" / "work")
        record = listeners.reap(self.tmp / "case-1")
        self.assertEqual([(i["pid"], i["ports"], i["ended_by"]) for i in record.get("reaped", [])], [(inside.pid, [port], "SIGTERM")])
        self.assertEqual(record.get("survived"), [])
        self.assertTrue(refuses_soon(port))
        self.assertTrue(answers(beside_port), "case-10 is not inside case-1")

    def test_a_listener_that_ignores_sigterm_is_killed_after_the_grace(self):
        stubborn, port = self.serve(self.tmp / "case-1", "ignore-term")
        with mock.patch.object(listeners, "GRACE_SECONDS", 0.3):
            record = listeners.reap(self.tmp / "case-1")
        self.assertEqual([(i["pid"], i["ended_by"]) for i in record.get("reaped", [])], [(stubborn.pid, "SIGKILL")])
        self.assertTrue(refuses_soon(port))

    def test_a_listener_that_stays_is_reported_as_survived_and_never_as_reaped(self):
        stays, port = self.serve(self.tmp / "case-1")
        with mock.patch.object(listeners, "_signal"), mock.patch.object(listeners, "GRACE_SECONDS", 0.2), \
                mock.patch.object(listeners, "FORCE_SECONDS", 0.2):
            record = listeners.reap(self.tmp / "case-1")
        self.assertEqual(record.get("reaped"), [])
        self.assertEqual([(i["pid"], i["ports"]) for i in record.get("survived", [])], [(stays.pid, [port])])
        self.assertTrue(answers(port))

    def test_a_world_that_cannot_be_read_is_unobserved_even_for_a_folder_with_a_listener(self):
        with mock.patch.object(listeners, "observe", side_effect=listeners.Unobserved("lsof not found")):
            self.assertEqual(listeners.reap(self.tmp / "case-1"), {"observed": False, "reason": "lsof not found"})


@needs_lsof
@needs_listeners
class LeftBehindThroughMainTest(RealListeners, CaseRunCase):
    """What a host or a check leaves listening is stopped, recorded in result.json and printed (SPEC: a run leaves nothing listening)."""

    def setUp(self):
        super().setUp()
        self.scope_to_tmp()

    def test_a_server_a_host_leaves_running_is_stopped_and_recorded(self):
        for host in ("claude", "grok"):
            with self.subTest(host=host):
                portfile = self.tmp / f"leak-{host}"
                self.addCleanup(kill_leaked, portfile)
                code, result, printed, out = self.case_main(f"case-{host}", host=host, env={"FAKE_LISTEN": str(portfile)})
                pid, port = map(int, portfile.read_text().split())
                self.assertEqual(code, 0, result)
                self.assertIn("left_behind", result)
                left = result.get("left_behind", {})
                self.assertEqual(left.get("observed"), True, left)
                self.assertEqual([(i["pid"], i["ports"], i["ended_by"]) for i in left.get("reaped", [])], [(pid, [port], "SIGTERM")])
                self.assertEqual([i["cwd"] for i in left.get("reaped", [])], [str((out / "work").resolve())])
                self.assertEqual(left.get("survived"), [])
                self.assertTrue(refuses_soon(port), "the server no longer answers")
                self.assertRegex(printed, rf"(?m)^  left      stopped pid {pid} .*\(port {port}\) by SIGTERM$")
                self.assertTrue(result["pass"], "a leftover is a record, not a verdict")

    def test_a_clean_run_records_a_measured_none_and_prints_no_left_line(self):
        code, result, printed, out = self.case_main("case-clean")
        self.assertEqual(result.get("left_behind"), {"observed": True, "reaped": [], "survived": []})
        self.assertNotRegex(printed, r"(?m)^  left ")

    def test_listeners_outside_the_case_folder_are_left_alone(self):
        portfile = self.tmp / "leak"
        self.addCleanup(kill_leaked, portfile)
        elsewhere, elsewhere_port = self.serve(self.tmp / "elsewhere")
        sibling, sibling_port = self.serve(self.tmp / "case-10" / "work")  # shares a name prefix with the case folder
        code, result, printed, out = self.case_main("case-1", env={"FAKE_LISTEN": str(portfile)})
        self.assertEqual(self.reaped(result), [int(portfile.read_text().split()[0])])
        self.assertTrue(answers(elsewhere_port) and answers(sibling_port))

    def test_a_listener_a_check_leaves_is_stopped_after_the_checks(self):
        portfile = self.tmp / "leak-check"
        self.addCleanup(kill_leaked, portfile)
        spawner = ("import os, subprocess, sys, time\n"
                   f"subprocess.Popen([sys.executable, '-c', {LISTENER_SOURCE!r}, {str(portfile)!r}], start_new_session=True,\n"
                   "                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
                   f"while not os.path.exists({str(portfile)!r}):\n    time.sleep(0.05)\n")
        check = f"{shlex.quote(sys.executable)} -c {shlex.quote(spawner)}"
        code, result, printed, out = self.case_main("case-check", "--prompt", "say hello", "--check", check)
        pid, port = map(int, portfile.read_text().split())
        self.assertEqual(self.reaped(result), [pid], "the session ended before the check started it")
        self.assertTrue(refuses_soon(port))
        self.assertTrue(all(c["pass"] for c in result["checks"]), result["checks"])

    def test_launch_reaps_when_its_session_ends_and_returns_the_record(self):
        portfile = self.tmp / "leak-launch"
        self.addCleanup(kill_leaked, portfile)
        out = self.tmp / "case-launch"
        (out / "work").mkdir(parents=True)
        spawner = ("import os, subprocess, sys, time\n"
                   f"subprocess.Popen([sys.executable, '-c', {LISTENER_SOURCE!r}, {str(portfile)!r}], start_new_session=True,\n"
                   "                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
                   f"while not os.path.exists({str(portfile)!r}):\n    time.sleep(0.05)\n")
        session = run.launch([sys.executable, "-c", spawner], out / "work", out, dict(os.environ), 60, watch=False)
        pid, port = map(int, portfile.read_text().split())
        self.assertEqual(session["status"], "exited")
        self.assertEqual(self.reaped(session), [pid])
        self.assertTrue(refuses_soon(port))

    def test_a_regrade_and_grade_only_reap_nothing_and_keep_the_earlier_record(self):
        code, first, _, out = self.case_main("case-done")
        live = listeners.hold_case(out)  # a live host means a live harness: without the lock this folder would look like a leak to other launches
        self.assertIsNotNone(live)
        self.addCleanup(live.close)
        proc, port = self.serve(out / "work")  # something a live host could be serving: a regrade starts no host and must not touch it
        recorded = first.get("left_behind")
        self.assertIsNotNone(recorded, "the run being regraded recorded what it left behind")
        for extra in ((), ("--grade-only",)):
            with contextlib.redirect_stdout(io.StringIO()):
                run.main(["--resume-run", str(out), "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), *extra])
            self.assertTrue(answers(port), f"a regrade {extra} reaped")
            self.assertEqual(json.loads((out / "result.json").read_text()).get("left_behind"), recorded)
        old = json.loads((out / "result.json").read_text())
        old.pop("left_behind", None)  # a result written before the key existed
        (out / "result.json").write_text(json.dumps(old))
        with contextlib.redirect_stdout(io.StringIO()):
            run.main(["--resume-run", str(out), "--grade-only", "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        self.assertNotIn("left_behind", json.loads((out / "result.json").read_text()), "not recorded is not none")
        self.assertTrue(answers(port))

    def test_a_world_that_cannot_be_read_is_recorded_as_unobserved_and_the_run_is_not_failed(self):
        with mock.patch.object(listeners, "observe", side_effect=listeners.Unobserved("lsof not found")):
            code, result, printed, out = self.case_main("case-blind")
        self.assertEqual(code, 0, result)
        self.assertEqual(result.get("left_behind"), {"observed": False, "reason": "lsof not found"})
        self.assertIn("  left      not observed: lsof not found", printed)

    def test_a_resume_stops_what_the_earlier_invocation_left_before_its_host_starts(self):
        code, first, _, out = self.case_main("case-resume", "--max-resumes", "0", mode="stuck", host="grok")
        self.assertEqual(first["shiploop"]["status"], "active")
        orphan, port = self.serve(out / "work")  # a model's server that outlived a killed harness
        self.log.unlink()
        Path(str(self.log) + ".probe").unlink(missing_ok=True)
        os.environ["FAKE_MODE"] = "done"
        released = {"origin_main": "a" * 40, "local_head": "a" * 40, "local_behind_main": False, "catalog_version": None,
                    "shiploop_version": None, "unreleased": [], "ci": "success"}  # a resume on its own install checks main's state
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.dict(os.environ, {"FAKE_PROBE_PORT": str(orphan.portfile)}), \
                mock.patch.object(run, "released_versions", return_value=released):
            run.main(["--host", "grok", "--grok-bin", str(self.fakes["grok"]), "--resume-run", str(out),
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        self.assertEqual(Path(str(self.log) + ".probe").read_text().split(), ["refused"], "gone before the new session began")
        result = json.loads((out / "result.json").read_text())
        self.assertEqual(self.reaped(result), [orphan.pid])


@needs_listeners
class CaseLockTest(unittest.TestCase):
    """A case's harness is alive exactly while it holds an exclusive lock on <output>/.harness-lock; the kernel drops it on any death."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()

    def case(self, name: str) -> Path:
        folder = self.tmp / name
        (folder / "work").mkdir(parents=True)
        (folder / "invocation.json").write_text("{}")
        return folder

    def test_a_case_folder_is_the_nearest_ancestor_with_an_invocation_record_and_a_work_directory(self):
        folder = self.case("case-1")
        self.assertEqual(listeners.case_folder(folder / "work" / "deep" / "server.js"), folder)
        self.assertEqual(listeners.case_folder(folder), folder)
        self.assertIsNone(listeners.case_folder(self.tmp / "elsewhere" / "a"))
        (self.tmp / "half").mkdir()
        (self.tmp / "half" / "invocation.json").write_text("{}")  # a record without a work directory is not a case
        self.assertIsNone(listeners.case_folder(self.tmp / "half" / "x"))

    def test_the_lock_is_held_while_its_file_is_open_and_a_second_holder_gets_none(self):
        folder = self.case("case-1")
        self.assertFalse(listeners.case_alive(folder), "no lock file: no live harness")
        self.assertFalse((folder / ".harness-lock").exists(), "looking creates nothing in a folder the run does not own")
        held = listeners.hold_case(folder)
        self.assertIsNotNone(held)
        self.assertTrue(listeners.case_alive(folder), "a second open file description in this very process sees it held")
        self.assertIsNone(listeners.hold_case(folder), "one harness per case folder; the second gets None, not an exception (main refuses on it)")
        held.close()
        self.assertFalse(listeners.case_alive(folder))
        self.assertIsNone(listeners.hold_case(self.tmp / "no-such-folder"), "never raises")

    def test_the_kernel_drops_the_lock_when_its_holder_is_killed(self):
        folder = self.case("case-1")
        holder = subprocess.Popen([sys.executable, "-c", "import fcntl, sys, time\nf = open(sys.argv[1], 'a')\n"
                                   "fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)\nprint('held', flush=True)\ntime.sleep(60)\n",
                                   str(folder / ".harness-lock")], stdout=subprocess.PIPE, text=True)
        self.addCleanup(end_quietly, holder)
        self.assertEqual(holder.stdout.readline().strip(), "held")
        self.assertTrue(listeners.case_alive(folder))
        holder.kill()
        holder.wait()
        self.assertFalse(listeners.case_alive(folder), "a SIGKILLed harness leaves no lock behind")

    def test_stale_lists_the_listeners_of_ended_cases_other_than_its_own(self):
        alive, ended, own = self.case("alive"), self.case("ended"), self.case("own")
        held = listeners.hold_case(alive)
        self.assertIsNotNone(held)
        self.addCleanup(held.close)
        items = [listener(900001, str(ended / "work"), "node server.js"),
                 listener(900002, str(alive / "work"), "node server.js"),
                 listener(900003, str(own / "work"), "node server.js"),
                 listener(900004, "/", f"node {ended}/.shiploop-runs/x/server.js"),
                 listener(900005, "/", "node unrelated.js"),
                 listener(900006, str(ended / "work"), "node protected.js")]
        with mock.patch.object(listeners, "observe", return_value=items), \
                mock.patch.object(listeners, "protected_pids", return_value={900006}):
            found = listeners.stale(own)
            everything = listeners.stale(None)
        self.assertEqual({(i["pid"], i["case"]) for i in found}, {(900001, str(ended)), (900004, str(ended))},
                         "a live harness, the run's own folder, an unrelated process and a protected pid are not stale")
        self.assertEqual({i["pid"] for i in everything}, {900001, 900003, 900004}, "with no folder of its own, the own case is stale too")


@needs_listeners
class StalePreflightThroughMainTest(CaseRunCase):
    """A launch is refused, whole, while another case leaves a listener and its harness is not alive (SPEC: a run leaves nothing listening)."""

    def setUp(self):
        super().setUp()
        isolate_git(self)
        patched = mock.patch.object(run, "POLL_SECONDS", 0.2, create=True)
        patched.start()
        self.addCleanup(patched.stop)

    def ended_case(self, name: str = "case-old") -> Path:
        folder = self.tmp / name
        (folder / "work").mkdir(parents=True)
        (folder / "invocation.json").write_text("{}")
        return folder

    def leaking(self, folder: Path, pid: int = 900001) -> mock._patch:
        return mock.patch.object(listeners, "observe", return_value=[listener(pid, str(folder / "work"), "node server.js", (3457,))])

    def test_a_launch_is_refused_while_an_ended_case_leaves_a_listener_and_no_host_starts(self):
        ended = self.ended_case()
        with self.leaking(ended), self.assertRaises(SystemExit) as refused:
            self.case_main("case-new")
        for part in ("pid 900001", "port 3457", str(ended), "kill 900001"):
            self.assertIn(part, str(refused.exception))
        self.assertFalse(self.log.exists(), "no host started")
        self.assertFalse((self.tmp / "case-new").exists(), "a refused launch leaves no output folder behind")

    def test_preflight_only_refuses_the_same_way_and_a_clean_machine_passes(self):
        ended = self.ended_case()
        for leaks, want in ((True, 1), (False, 0)):
            printed = io.StringIO()
            with (self.leaking(ended) if leaks else mock.patch.object(listeners, "observe", return_value=[])), \
                    mock.patch.object(run, "marketplace_preflight", return_value=(self.plugin, None, {"gate": []})), \
                    contextlib.redirect_stdout(printed):
                code = run.main(["--preflight-only", "--host", "claude", "--output", str(self.tmp / f"pf-{leaks}")])
            self.assertEqual(code, want, printed.getvalue())
            self.assertEqual("kill 900001" in printed.getvalue(), leaks)

    def test_a_case_whose_harness_is_alive_is_not_stale_even_in_the_same_process(self):
        ended = self.ended_case()
        held = listeners.hold_case(ended)  # what a sibling case of a parallel suite holds
        self.assertIsNotNone(held)
        self.addCleanup(held.close)
        with self.leaking(ended):
            code, result, printed, out = self.case_main("case-new")
        self.assertEqual(code, 0, result)

    def resume_argv(self, out: Path, *extra: str) -> list[str]:
        return ["--host", "grok", "--grok-bin", str(self.fakes["grok"]), "--resume-run", str(out), "--plugin-dir", str(self.plugin),
                "--baseline", str(self.baselines), *extra]

    def test_a_second_harness_for_a_case_whose_harness_is_alive_is_refused_and_touches_nothing(self):
        code, first, _, out = self.case_main("case-live", "--max-resumes", "0", mode="stuck", host="grok")
        self.assertEqual(first["shiploop"]["status"], "active")
        live = listeners.hold_case(out)  # the harness that is running this case
        self.assertIsNotNone(live)
        self.addCleanup(live.close)
        (out / "stop").write_text("")  # its owner has asked it to end
        self.log.unlink()
        reaped: list = []
        released = {"origin_main": "a" * 40, "local_head": "a" * 40, "local_behind_main": False, "catalog_version": None,
                    "shiploop_version": None, "unreleased": [], "ci": "success"}
        with mock.patch.object(listeners, "reap", side_effect=lambda folder: reaped.append(folder)), \
                mock.patch.object(run, "released_versions", return_value=released), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as refused:
            run.main(self.resume_argv(out))
        self.assertIn("another harness is running", str(refused.exception))
        self.assertIn(str(out), str(refused.exception))
        self.assertTrue((out / "stop").exists(), "the stop request belongs to the harness that is running")
        self.assertFalse(self.log.exists(), "no host started")
        self.assertEqual(reaped, [], "the live harness's servers are not this invocation's to stop")

    def test_a_regrade_of_a_case_whose_harness_is_alive_is_not_refused_and_leaves_its_stop_request(self):
        code, first, _, out = self.case_main("case-done")
        live = listeners.hold_case(out)
        self.assertIsNotNone(live)
        self.addCleanup(live.close)
        (out / "stop").write_text("")
        for extra in ((), ("--grade-only",)):
            with contextlib.redirect_stdout(io.StringIO()):
                run.main(self.resume_argv(out, *extra))
            self.assertTrue(json.loads((out / "result.json").read_text())["process"]["regraded"], extra)
            self.assertTrue((out / "stop").exists(), f"a regrade {extra} starts nothing, so it owns no stop request")

    def test_a_regrade_is_never_refused_because_it_starts_nothing(self):
        code, first, _, out = self.case_main("case-done")
        ended = self.ended_case()
        for extra in ((), ("--grade-only",)):
            with self.leaking(ended), contextlib.redirect_stdout(io.StringIO()):
                run.main(["--resume-run", str(out), "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), *extra])
            self.assertTrue(json.loads((out / "result.json").read_text())["process"]["regraded"], extra)

    def test_a_listener_that_cannot_be_looked_for_is_noted_and_the_launch_goes_ahead(self):
        with mock.patch.object(listeners, "observe", side_effect=listeners.Unobserved("lsof not found")):
            code, result, printed, out = self.case_main("case-new")
        self.assertEqual(code, 0, result)
        self.assertIn("stale-listener check skipped: lsof not found", printed)

    def test_the_harness_holds_its_case_lock_while_it_runs_and_drops_it_when_it_ends(self):
        out = self.tmp / "case-lock"
        seen: list[bool] = []

        def watch():
            sessions = Path(str(self.log) + ".sessions")
            for _ in range(400):
                if sessions.exists():
                    break
                time.sleep(0.05)
            seen.append(listeners.case_alive(out))
            (out / "stop").write_text("")

        threading.Thread(target=watch, daemon=True).start()
        code, result, printed, _ = self.case_main("case-lock", "--timeout", "30", mode="hang-active", host="grok")
        self.assertEqual(seen, [True], "alive while the host runs")
        self.assertFalse(listeners.case_alive(out), "dropped when main returns")

    def test_a_suite_refuses_once_before_any_case_starts_and_its_cases_do_not_check_again(self):
        SuiteTest.use_catalog(self, {"a": {"style": "s", "prompt": "p", "checks": []}, "b": {"style": "t", "prompt": "p", "checks": []}},
                              {"wide": {"kind": "breadth", "cases": ["a", "b"]}})
        ended = self.ended_case()
        os.environ["FAKE_MODE"] = "done"
        argv = ["--suite", "wide", "--host", "grok", "--grok-bin", str(self.fakes["grok"]), "--output", str(self.tmp / "suite-out"),
                "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)]
        with self.leaking(ended), contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as refused:
            run.main(argv)
        self.assertIn("kill 900001", str(refused.exception))
        self.assertFalse((self.tmp / "suite-out").exists(), "refused before the suite's folder or any case existed")
        self.assertFalse(self.log.exists())
        # A case the suite starts has been checked by the suite, once: it must not raise inside a worker thread.
        with self.leaking(ended):
            code, result, printed, out = self.case_main("case-in-suite", "--case", "a", "--suite-name", "wide")
        self.assertEqual(code, 0, result)


@needs_lsof
@needs_listeners
class StaleListenerRealTest(RealListeners, CaseRunCase):
    """The same refusal against a real server and the real lsof."""

    def setUp(self):
        super().setUp()
        self.scope_to_tmp()

    def test_a_real_server_an_ended_case_left_refuses_the_launch_and_is_never_stopped_by_the_refusal(self):
        ended = self.tmp / "case-old"
        leaked, port = self.serve(ended / "work")
        # The one state this test is about is a case with no live harness, which another session's real launch would also refuse
        # on: so the case record is written last and the lock taken as soon as the refusal is seen, a window of one scan.
        (ended / "invocation.json").write_text("{}")
        with self.assertRaises(SystemExit) as refused:
            self.case_main("case-new")
        held = listeners.hold_case(ended)
        self.assertIsNotNone(held)
        self.addCleanup(held.close)
        for part in (f"pid {leaked.pid}", f"port {port}", str(ended), f"kill {leaked.pid}"):
            self.assertIn(part, str(refused.exception))
        self.assertTrue(answers(port), "a refusal names the process and leaves it to the owner")
        code, result, _, _ = self.case_main("case-new")
        self.assertEqual(code, 0, result)
        self.assertTrue(answers(port), "the other case's server is not this run's to stop")


class TerminationSignalTest(CaseRunCase):
    """The harness as a task runner meets it: a program that is sent a signal while its host works.

    The harness runs as a real subprocess (python3 run.py), so the signal wiring under __main__ is the one tested, and the test
    process's own handlers are never touched. A fake `lsof` first on PATH shows an empty process table, so no real listener of
    this machine can refuse or change a run."""

    def setUp(self):
        super().setUp()
        isolate_git(self)
        self.home = self.tmp / "home"
        (self.home / ".grok").mkdir(parents=True)
        (self.home / ".grok" / "auth.json").write_text("{}")
        tools = self.tmp / "tools"
        tools.mkdir()
        (tools / "lsof").write_text("#!/bin/sh\nexit 1\n")
        (tools / "lsof").chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home), PATH=f"{tools}{os.pathsep}{os.environ['PATH']}", FAKE_LOG=str(self.log),
                        FAKE_MODE="hang-active", SHIPLOOP_PROGRESS="off")

    # What the task runner's child starts with is not what this test process inherited: a job a shell started in the background
    # has SIGINT ignored (and one under nohup has SIGHUP ignored), and Python installs no Ctrl-C handler for an ignored SIGINT.
    # The harness is started through this, which sets the named signals to their defaults first and keeps the rest as inherited.
    DEFAULT_SIGNALS = ("import os, signal, sys\n[signal.signal(getattr(signal, n), signal.SIG_DFL) for n in sys.argv[1].split(',') if n]\n"
                       "os.execv(sys.executable, [sys.executable] + sys.argv[2:])\n")

    def start(self, name: str, *extra: str, launcher: tuple = (), reset: str = "SIGINT,SIGTERM,SIGHUP") -> tuple[subprocess.Popen, Path]:
        out = self.tmp / name
        proc = subprocess.Popen([*launcher, sys.executable, "-c", self.DEFAULT_SIGNALS, reset, str(run.HERE / "run.py"), "--host", "grok",
                                 "--grok-bin", str(self.fakes["grok"]), "--output", str(out), "--plugin-dir", str(self.plugin),
                                 "--baseline", str(self.baselines), "--timeout", "120", *extra],
                                env=self.env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        # Registered before the harness's own kill, so it runs after it: a harness that is still alive would start another host.
        self.addCleanup(self.kill_hosts)
        self.addCleanup(end_quietly, proc)
        return proc, out

    def kill_hosts(self) -> None:
        """Every host the harness ever started in this test (the fake logs one line per session), whole group, whatever the code
        under test did: a test that fails must not leave an orphan host (each also sleeps for at most 600 s)."""
        sessions = Path(str(self.log) + ".sessions")
        for line in sessions.read_text().splitlines() if sessions.exists() else []:
            with contextlib.suppress(ValueError, KeyError, ProcessLookupError, PermissionError):
                pid = json.loads(line)["pid"]
                if os.getpgid(pid) == pid:  # a host leads the session it was started in; a reused pid does not
                    os.killpg(pid, signal.SIGKILL)

    def host_pid(self) -> int:
        """The fake host's pid, once it is running."""
        sessions = Path(str(self.log) + ".sessions")
        for _ in range(600):
            if sessions.exists() and sessions.read_text().strip():
                break
            time.sleep(0.05)
        else:
            raise AssertionError("the host never started")
        return json.loads(sessions.read_text().splitlines()[0])["pid"]

    @staticmethod
    def kill_pid(pid: int) -> None:
        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, 9)

    @staticmethod
    def gone(pid: int, seconds: float = 5.0) -> bool:
        end = time.time() + seconds
        while time.time() < end:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return True
            time.sleep(0.05)
        return False

    def test_sigterm_kills_the_host_writes_the_records_and_reads_as_stopped(self):
        proc, out = self.start("case-term")
        host = self.host_pid()
        proc.send_signal(signal.SIGTERM)
        printed, _ = proc.communicate(timeout=60)
        self.assertTrue(self.gone(host), "the host does not outlive its harness")
        self.assertEqual(proc.returncode, 1, printed)
        self.assertTrue((out / "result.json").is_file(), printed)
        result = json.loads((out / "result.json").read_text())
        self.assertEqual((result["process"]["status"], result["process"]["pass"]), ("stopped", None))
        self.assertEqual(result["termination"]["resume_stop"], "terminated by SIGTERM")
        self.assertTrue((out / "metrics.json").is_file())
        self.assertFalse(self.baselines.exists(), "a stopped run is not a baseline")
        self.assertEqual(len(Path(str(self.log) + ".sessions").read_text().splitlines()), 1, "a terminated host is not relaunched")
        self.assertRegex(printed, r"(?m)^STOPPED  shiploop e2e case=")

    def test_sighup_ends_the_run_the_same_way_unless_the_launch_ignored_it(self):
        proc, out = self.start("case-hup")
        host = self.host_pid()
        proc.send_signal(signal.SIGHUP)
        printed, _ = proc.communicate(timeout=60)
        self.assertTrue(self.gone(host))
        self.assertEqual(proc.returncode, 1, printed)
        self.assertEqual(json.loads((out / "result.json").read_text())["termination"]["resume_stop"], "terminated by SIGHUP")

    @unittest.skipUnless(shutil.which("nohup"), "needs nohup")
    def test_a_nohup_launch_keeps_its_run_through_a_hangup(self):
        proc, out = self.start("case-nohup", launcher=("nohup",), reset="SIGINT,SIGTERM")  # nohup's own SIGHUP is ignored; keep it so
        host = self.host_pid()
        proc.send_signal(signal.SIGHUP)  # the terminal went away; nohup's whole purpose is that the run does not
        time.sleep(1.5)
        self.assertIsNone(proc.poll(), "the harness ended on a hangup that its launch ignored")
        self.assertFalse(self.gone(host, 0.1), "the host was killed by a hangup that its launch ignored")
        proc.send_signal(signal.SIGTERM)  # an explicit stop still works
        printed, _ = proc.communicate(timeout=60)
        self.assertTrue((out / "result.json").is_file(), printed)
        self.assertEqual(json.loads((out / "result.json").read_text())["termination"]["resume_stop"], "terminated by SIGTERM", printed)

    def test_a_second_signal_ends_the_harness_at_once_even_while_a_check_runs(self):
        marker, pidfile = self.tmp / "check-started", self.tmp / "check-pid"
        proc, out = self.start("case-twice", "--prompt", "say hello", "--check", f"echo $$ > {pidfile}; touch {marker}; exec sleep 20")
        self.host_pid()
        proc.send_signal(signal.SIGTERM)  # ends the host; the harness goes on to its checks
        for _ in range(600):
            if marker.exists():
                break
            time.sleep(0.05)
        self.addCleanup(lambda: pidfile.exists() and self.kill_pid(int(pidfile.read_text())))
        self.assertTrue(marker.exists(), "the harness reached its checks after the first signal")
        proc.send_signal(signal.SIGTERM)  # the person means it
        proc.communicate(timeout=30)
        self.assertEqual(proc.returncode, -signal.SIGTERM)

    def test_ctrl_c_on_a_suite_ends_its_hosts_at_once_and_writes_the_records(self):
        # A suite runs its cases in worker threads and a Ctrl-C reaches only the main thread, which then waits for them: without
        # its own handling the hosts ran on (the review saw them alive 40 s later) because the atexit kill comes after that wait.
        proc, out = self.start("suite-int", "--suite", "smoke")
        host = self.host_pid()
        proc.send_signal(signal.SIGINT)
        try:
            printed, _ = proc.communicate(timeout=45)
        except subprocess.TimeoutExpired:
            self.fail("the suite kept running after a Ctrl-C")
        self.assertTrue(self.gone(host), "the host does not outlive a Ctrl-C of its suite")
        self.assertEqual(proc.returncode, 1, printed)
        self.assertEqual([(r["case"], r["pass"]) for r in json.loads((out / "suite-result.json").read_text())["cases"]], [("hello", False)])
        result = json.loads((out / "hello" / "result.json").read_text())
        self.assertEqual((result["process"]["status"], result["termination"]["resume_stop"]), ("stopped", "terminated by SIGINT"))
        self.assertEqual(len(Path(str(self.log) + ".sessions").read_text().splitlines()), 1, "a terminated host is not relaunched")

    def test_ctrl_c_leaves_no_host_behind(self):
        proc, out = self.start("case-int")
        host = self.host_pid()
        proc.send_signal(signal.SIGINT)
        printed, _ = proc.communicate(timeout=60)
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(self.gone(host), "a Ctrl-C on the harness must not orphan its host")
        self.assertFalse((out / "result.json").exists(), "a Ctrl-C on a single case writes no records (the README says so)")


@needs_listeners
class LiveHostTest(unittest.TestCase):
    """The harness's bookkeeping of the hosts it started, driven without any real signal.

    The poll interval is long here, so a session can only end promptly because the harness killed its group, not because the
    poll loop noticed."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        for patcher in (mock.patch.object(listeners, "observe", return_value=[]), mock.patch.object(run, "POLL_SECONDS", 30, create=True)):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(run.TERMINATION.clear)
        self.addCleanup(run.TERMINATED_BY.clear)
        self.addCleanup(run.end_live_hosts)  # runs first: a failing test leaves no host (each also sleeps for at most 20 s)

    def session(self, name: str) -> tuple[threading.Thread, dict, Path]:
        out = self.tmp / name
        (out / "work").mkdir(parents=True)
        result: dict = {}
        thread = threading.Thread(target=lambda: result.update(run.launch(
            [sys.executable, "-c", "import time; time.sleep(20)"], out / "work", out, dict(os.environ), 60, watch=False)))
        thread.start()
        return thread, result, out

    @staticmethod
    def registered(count: int) -> bool:
        for _ in range(100):
            if len(run.LIVE_HOST_GROUPS) == count:
                return True
            time.sleep(0.05)
        return False

    def test_end_live_hosts_kills_every_registered_group_and_launch_discards_its_own(self):
        threads = [self.session(f"case-{n}") for n in range(2)]
        self.assertTrue(self.registered(2), "each running session is registered")
        groups = sorted(run.LIVE_HOST_GROUPS)
        run.end_live_hosts()
        for thread, result, _ in threads:
            thread.join(timeout=15)
            self.assertFalse(thread.is_alive(), "the session ended at once, not at the next poll")
            self.assertEqual(result["status"], "failed")  # no one asked for a stop: only the groups were killed
        self.assertEqual(run.LIVE_HOST_GROUPS, set(), "a session that ended is no longer registered, so a reused pgid is never signalled")
        for pid in groups:
            with self.assertRaises(ProcessLookupError):
                os.killpg(pid, 0)

    def test_a_termination_ends_a_running_session_at_once_as_stopped_and_starts_no_later_one(self):
        thread, result, out = self.session("case-running")
        self.assertTrue(self.registered(1))
        run.on_termination(signal.SIGTERM, None)
        thread.join(timeout=15)
        self.assertFalse(thread.is_alive(), "the handler killed the group; the 30 s poll did not have to notice")
        self.assertEqual(result.get("status"), "stopped", result)
        self.assertTrue(run.TERMINATION.is_set())
        self.assertEqual(run.TERMINATED_BY, ["SIGTERM"])

    def test_a_session_that_begins_after_the_harness_was_told_to_end_is_ended_at_its_first_poll(self):
        run.TERMINATED_BY.append("SIGTERM")
        run.TERMINATION.set()  # say, during the install, before any host
        later = self.tmp / "case-later"
        (later / "work").mkdir(parents=True)
        started = time.time()
        after = run.launch([sys.executable, "-c", "import time; time.sleep(20)"], later / "work", later, dict(os.environ), 60, watch=False)
        self.assertEqual(after["status"], "stopped")
        self.assertLess(time.time() - started, 10, "it did not run to its end")
        self.assertEqual(run.LIVE_HOST_GROUPS, set())
        self.assertTrue((later / "events.jsonl").is_file(), "the session's files exist so the records can be written")

    def test_a_signal_that_arrives_before_the_host_is_registered_still_ends_it(self):
        real_popen = subprocess.Popen

        def popen_then_signal(*args, **kwargs):
            proc = real_popen(*args, **kwargs)
            run.on_termination(signal.SIGTERM, None)  # the handler runs now and cannot know this group yet
            return proc

        with mock.patch.object(run.subprocess, "Popen", side_effect=popen_then_signal):
            thread, result, out = self.session("case-race")
            thread.join(timeout=15)
        self.assertFalse(thread.is_alive(), "the poll loop must notice the termination and end the group")
        self.assertEqual(result.get("status"), "stopped")


class SignalledHarnessThroughMainTest(CaseRunCase):
    def test_a_suite_told_to_end_starts_no_further_case(self):
        SuiteTest.use_catalog(self, {"a": {"style": "s", "prompt": "p", "checks": []}, "b": {"style": "t", "prompt": "p", "checks": []}},
                              {"wide": {"kind": "breadth", "cases": ["a", "b"]}})
        self.addCleanup(run.TERMINATION.clear)
        self.addCleanup(run.TERMINATED_BY.clear)
        run.TERMINATED_BY.append("SIGTERM")
        run.TERMINATION.set()
        out = self.tmp / "suite-out"
        os.environ["FAKE_MODE"] = "done"
        with contextlib.redirect_stdout(io.StringIO()):
            code = run.main(["--suite", "wide", "--host", "grok", "--grok-bin", str(self.fakes["grok"]), "--output", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        rows = json.loads((out / "suite-result.json").read_text())["cases"]
        self.assertEqual(code, 1)
        self.assertEqual([(r["case"], r.get("skipped")) for r in rows], [("a", "terminated by SIGTERM"), ("b", "terminated by SIGTERM")])
        self.assertFalse(self.log.exists(), "no host started")

    def test_a_batch_suite_told_to_end_skips_its_gate_and_the_cases_behind_it(self):
        SuiteTest.use_catalog(self, {"g": {"style": "s", "prompt": "p", "checks": []}, "a": {"style": "t", "prompt": "p", "checks": []}},
                              {"b": {"kind": "batch", "gate": ["g"], "cases": ["a"]}})
        self.addCleanup(run.TERMINATION.clear)
        self.addCleanup(run.TERMINATED_BY.clear)
        run.TERMINATED_BY.append("SIGTERM")
        run.TERMINATION.set()
        out = self.tmp / "suite-out"
        os.environ["FAKE_MODE"] = "done"
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = run.main(["--suite", "b", "--host", "grok", "--grok-bin", str(self.fakes["grok"]), "--output", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        rows = json.loads((out / "suite-result.json").read_text())["cases"]
        self.assertEqual(code, 1)
        self.assertEqual(rows, [{"case": "g", "pass": False, "skipped": "terminated by SIGTERM", "gate": True},
                                {"case": "a", "skipped": "the gate failed"}])
        self.assertIn("gate failed (g)", printed.getvalue())
        self.assertFalse(self.log.exists(), "no host started, not even the gate's")

    def test_a_signal_as_a_session_ends_stops_the_resume_loop_without_a_phantom_session(self):
        self.addCleanup(run.TERMINATION.clear)
        self.addCleanup(run.TERMINATED_BY.clear)
        calls: list[int] = []

        def host_that_ends_as_the_signal_arrives(argv, work, out, *args, **kwargs):
            calls.append(1)
            for name in ("events.jsonl", "stderr.txt", "timeline.jsonl"):
                (out / name).write_text("")
            run.TERMINATED_BY.append("SIGHUP")
            run.TERMINATION.set()
            return {"status": "exited", "returncode": 0, "elapsed_seconds": 1.0, "stop": None, "left_behind": None}

        with mock.patch.object(run, "launch", side_effect=host_that_ends_as_the_signal_arrives):
            code, result, printed, out = self.case_main("case-between", host="grok")
        self.assertEqual(len(calls), 1, "no second session is started or recorded for a harness that was told to end")
        self.assertEqual(result["termination"]["resume_stop"], "terminated by SIGHUP")
        self.assertEqual((result["process"]["status"], result["process"]["pass"]), ("stopped", None))
        self.assertEqual(len(result["process"]["sessions"]), 1)
        self.assertEqual(code, 1)


class LeftBehindReadmeTest(unittest.TestCase):
    def test_the_readme_says_what_the_harness_does_with_a_leftover_listener(self):
        readme = " ".join((ROOT / "test" / "shiploop_e2e" / "README.md").read_text().split())
        for phrase in ("stops every TCP listener of your user whose working directory or command line lies under the case's output folder",
                       "`left_behind` in `result.json`", "never reads as none", "do not serve a case folder by hand while its run ends"):
            self.assertIn(phrase, readme)
        self.assertNotIn("nothing looks for what the host left behind", readme)

    def test_the_readme_says_when_a_launch_is_refused_and_how_liveness_is_known(self):
        readme = " ".join((ROOT / "test" / "shiploop_e2e" / "README.md").read_text().split())
        for phrase in ("A launch is refused while a listener sits under another case's output folder",
                       "`<output>/.harness-lock`", "no override", "stop it by pid with `kill <pid>`",
                       "A `--resume-run` of a case whose harness is running is refused too",
                       "A harness started before the lock existed holds none, so a launch refuses its listeners as stale while it is still running"):
            self.assertIn(phrase, readme)

    def test_the_operator_contract_in_the_module_docstring_names_signals_left_behind_and_the_refusals(self):
        doc = " ".join(run.__doc__.split())
        for phrase in ("A SIGTERM or SIGHUP to the harness", "`left_behind`", "A launch is refused while", "--resume-run of a case whose harness is running"):
            self.assertIn(phrase, doc)

    def test_the_readme_says_to_run_compared_runs_one_after_the_other_and_what_that_cannot_promise(self):
        readme = " ".join((ROOT / "test" / "shiploop_e2e" / "README.md").read_text().split())
        for phrase in ("Run the runs you compare one after the other", "`--serial` for a suite",
                       "The suite default of 3 parallel chains stays", "no overlap field", "a discipline and not a guarantee"):
            self.assertIn(phrase, readme)

    def test_the_spec_carries_the_rules_this_code_serves(self):
        spec = " ".join((ROOT / "test" / "shiploop_e2e" / "SPEC.md").read_text().split())
        for phrase in ("**A run leaves nothing listening**", "`<output>/.harness-lock`", "`left_behind`",
                       "A SIGTERM to the harness (a task runner's stop, `kill`) is a requested stop too",
                       "**Runs compared on wall time or per-call cost run one after the other**",
                       "a pair whose figures are compared is the exception stated in the bullet "
                       "\"Runs compared on wall time or per-call cost run one after the other\"",
                       "a Ctrl-C on a suite is handled as a SIGTERM",
                       "A `--resume-run` of a case whose harness is running (its lock is held) is refused too; a regrade is not"):
            self.assertIn(phrase, spec)
        self.assertNotIn("bullet after next", spec, "a position breaks when a bullet is added: the bullet is named")

    def test_the_readme_says_what_a_signal_to_the_harness_does(self):
        readme = " ".join((ROOT / "test" / "shiploop_e2e" / "README.md").read_text().split())
        for phrase in ("A SIGTERM or SIGHUP to the harness ends every live host at once", "`terminated by SIGTERM`",
                       "a detached `nohup` launch ignores the hangup", "Only a SIGKILL gives the harness no chance to run anything",
                       "not `iterate.py`", "A Ctrl-C on a suite is handled as a SIGTERM",
                       "a Ctrl-C on a single case ends the hosts as the harness exits and writes no records"):
            self.assertIn(phrase, readme)
        self.assertNotIn("no harness code runs", readme)
        self.assertNotIn("taking the harness and its host with it", readme)


def grok_usage(count: int, output: int = 100, reasoning: int = 40) -> list[dict]:
    """`count` per-call usage events, the shape Grok writes (and the Codex translator does not)."""
    return [{"type": "usage", "usage": {"input_tokens": 1000, "output_tokens": output, "reasoning_tokens": reasoning}}
            for _ in range(count)]


# A planning window: the host's first event is at 1000, the engine starts at 1030, and the first accepted test-spec is 400 s
# after the host began (370 s after the engine did). The implement row is after the window.
PLANNING_ROWS = [("a-intake", "intake", "done", 1160), ("a-spec", "spec", "done", 1250),
                 ("a-ts", "test-spec", "done", 1400), ("a-impl", "implement", "done", 1500)]


class PlanningBlockCase(unittest.TestCase):
    """metrics.collect's `planning` block, built from files a run left behind."""

    def planning(self, rows=PLANNING_ROWS, *, stream=None, started=1030.0, improve=None, binds=None, **kw) -> dict:
        inner = {} if improve is None else {"improve_results": improve}
        m = collect_stream(grok_usage(3) if stream is None else stream, rows, status="active", first_event=1000.0,
                           started=started, inner=inner, binds=binds, **kw)
        return m["planning"]


class PlanningClockTest(PlanningBlockCase):
    def test_the_window_runs_from_the_engine_start_to_the_first_done_test_spec(self):
        plan = self.planning(improve={})
        self.assertEqual(plan["window"], {"closed": True, "through": "test-spec", "seconds": 370.0,
                                          "host_seconds": 400.0, "before_engine_seconds": 30.0})
        self.assertEqual([(r["stage"], r["outcome"], r["seconds"]) for r in plan["stages"]],
                         [("intake", "done", 130.0), ("spec", "done", 90.0), ("test-spec", "done", 150.0)])
        self.assertEqual(plan["unmeasured"].get("window"), None)

    def test_a_revised_test_spec_does_not_close_the_window(self):
        rows = [("a-intake", "intake", "done", 1160), ("a-ts1", "test-spec", "revise", 1300),
                ("a-ts2", "test-spec", "done", 1500)]
        plan = self.planning(rows, improve={})
        self.assertEqual((plan["window"]["closed"], plan["window"]["seconds"]), (True, 470.0))
        self.assertEqual([r["outcome"] for r in plan["stages"]], ["done", "revise", "done"])

    def test_a_run_that_never_reached_test_spec_is_open_and_says_through_which_stage(self):
        plan = self.planning(PLANNING_ROWS[:2], improve={})
        self.assertEqual(plan["window"], {"closed": False, "through": "spec", "seconds": 220.0,
                                          "host_seconds": 250.0, "before_engine_seconds": 30.0})
        self.assertGreater(plan["window"]["seconds"], 0, "an open window is never reported as 0")

    def test_a_run_with_no_accepted_stage_has_no_window_and_says_why(self):
        plan = self.planning([], improve={})
        self.assertIsNone(plan["window"]["seconds"])
        self.assertIn("no stage has been accepted", plan["unmeasured"]["window"])

    def test_an_unstamped_stage_inside_the_window_leaves_its_own_seconds_unknown_not_the_window_shorter(self):
        rows = [("a-intake", "intake", "done", 1160), ("a-spec", "spec", "done", None), ("a-ts", "test-spec", "done", 1400)]
        plan = self.planning(rows, improve={})
        self.assertEqual(plan["window"]["seconds"], 370.0, "the window needs only the start and the end stamp")
        self.assertEqual([r["seconds"] for r in plan["stages"]], [130.0, None, None])

    def test_a_seeded_run_has_no_planning_window(self):
        # The harness recorded the early stages itself, before the host's first event (1000).
        rows = [("a-intake", "intake", "done", 900), ("a-ts", "test-spec", "done", 1400)]
        plan = self.planning(rows, improve={})
        self.assertIsNone(plan["window"]["seconds"])
        self.assertIn("before the host", plan["unmeasured"]["window"])

    def test_a_recreated_timeline_reads_as_unmeasured_never_as_a_zero_window(self):
        # The engine gives every historical action one stamp when it recreates a lost timeline.json.
        rows = [("a-intake", "intake", "done", 1160), ("a-spec", "spec", "done", 1160), ("a-ts", "test-spec", "done", 1160)]
        plan = self.planning(rows, started=1160.0, improve={})
        self.assertIsNone(plan["window"]["seconds"])
        self.assertIn("one stamp", plan["unmeasured"]["window"])

    def test_a_recreated_timeline_with_one_accepted_row_is_unmeasured_not_a_measured_zero(self):
        # One accepted row whose stamp equals the start: not a duration, and an open window is never 0.
        plan = self.planning([("a-intake", "intake", "done", 1160)], started=1160.0, improve={})
        self.assertFalse(plan["window"]["closed"])
        self.assertIsNone(plan["window"]["seconds"])
        self.assertIsNone(plan["window"]["host_seconds"])
        self.assertIn("one stamp", plan["unmeasured"]["window"])
        closed = self.planning([("a-ts", "test-spec", "done", 1160)], started=1160.0, improve={})
        self.assertIsNone(closed["window"]["seconds"])
        self.assertIn("one stamp", closed["unmeasured"]["window"])

    def test_a_timeline_with_no_start_is_unmeasured(self):
        plan = self.planning(improve={}, started=False)
        self.assertIsNone(plan["window"]["seconds"])
        self.assertIn("no start time", plan["unmeasured"]["window"])

    def test_the_host_clock_is_unknown_without_the_runner_timeline_and_the_engine_clock_stands(self):
        plan = self.planning(improve={}, timed=False)
        self.assertEqual((plan["window"]["seconds"], plan["window"]["host_seconds"], plan["window"]["before_engine_seconds"]),
                         (370.0, None, None))
        self.assertIn("runner", plan["unmeasured"]["host_seconds"])


class PlanningImproveSplitTest(PlanningBlockCase):
    def test_improve_seconds_run_from_the_bind_file_to_the_accept_for_an_action_with_an_improve_result(self):
        plan = self.planning(improve={"a-spec": {"summary": "reviewed"}}, binds={"a-spec": 1190.4})
        self.assertEqual([(r["stage"], r["improve_seconds"]) for r in plan["stages"]],
                         [("intake", 0.0), ("spec", 59.6), ("test-spec", 0.0)])
        self.assertEqual(plan["improve"], {"children": 1, "seconds": 59.6})

    def test_producer_seconds_plus_improve_seconds_equal_the_window(self):
        plan = self.planning(improve={"a-spec": {}, "a-ts": {}}, binds={"a-spec": 1190.0, "a-ts": 1300.0})
        self.assertEqual(plan["improve"], {"children": 2, "seconds": 160.0})
        self.assertEqual(plan["producer_seconds"] + plan["improve"]["seconds"], plan["window"]["seconds"])

    def test_a_none_run_has_a_measured_zero_improve_share_in_the_window(self):
        plan = self.planning(improve={})
        self.assertEqual(plan["improve"], {"children": 0, "seconds": 0.0})
        self.assertEqual(plan["producer_seconds"], plan["window"]["seconds"])

    def test_an_improve_result_with_no_bind_file_makes_improve_unknown_not_zero(self):
        plan = self.planning(improve={"a-spec": {}})
        self.assertEqual(plan["improve"], {"children": 1, "seconds": None})
        self.assertIsNone(plan["producer_seconds"])
        self.assertEqual(plan["window"]["seconds"], 370.0)
        self.assertIn("bind", plan["unmeasured"]["improve"])
        self.assertIsNone(next(r for r in plan["stages"] if r["stage"] == "spec")["improve_seconds"])

    def test_a_state_with_no_improve_results_makes_improve_unknown(self):
        plan = self.planning()  # no improve_results key in state.md
        self.assertIsNone(plan["improve"])
        self.assertIn("improve_results", plan["unmeasured"]["improve"])

    def test_an_accept_stamp_within_a_second_below_the_bind_time_is_whole_second_truncation_not_a_negative(self):
        # Accept stamps are truncated to whole seconds; the bind file's mtime is fractional. Seen on a real Sonnet run: -0.33 s.
        plan = self.planning(improve={"a-spec": {}}, binds={"a-spec": 1250.9})
        self.assertEqual(next(r for r in plan["stages"] if r["stage"] == "spec")["improve_seconds"], 0.0)
        self.assertEqual(plan["improve"]["seconds"], 0.0)

    def test_a_stamp_more_than_a_second_below_the_bind_time_is_unmeasured_and_never_reaches_producer_seconds(self):
        plan = self.planning(improve={"a-spec": {}}, binds={"a-spec": 1253.0})
        self.assertIsNone(next(r for r in plan["stages"] if r["stage"] == "spec")["improve_seconds"])
        self.assertIsNone(plan["improve"]["seconds"])
        self.assertIsNone(plan["producer_seconds"])
        self.assertIn("before", plan["unmeasured"]["improve"])


class PlanningTokensTest(PlanningBlockCase):
    ROWS = [("a-intake", "intake", "done", 1002), ("a-ts", "test-spec", "done", 1005), ("a-impl", "implement", "done", 1008)]

    def test_a_grok_window_sums_the_usage_events_inside_the_host_window_and_names_the_clock(self):
        # Events are stamped 1000 to 1009; the window ends at 1005, so events 0 to 5 are inside it.
        plan = self.planning(self.ROWS, stream=grok_usage(10), started=1001.0, improve={})
        self.assertEqual(plan["tokens"], {"output": 600, "reasoning": 240, "clock": "host", "source": "usage events"})

    def test_a_grok_window_that_covers_the_run_equals_the_sum_of_every_usage_event(self):
        plan = self.planning([("a-ts", "test-spec", "done", 1500)], stream=grok_usage(10), started=1001.0, improve={})
        self.assertEqual((plan["tokens"]["output"], plan["tokens"]["reasoning"]), (1000, 400))

    def test_a_grok_run_with_no_runner_timeline_has_unmeasured_tokens(self):
        plan = self.planning(self.ROWS, stream=grok_usage(10), started=1001.0, improve={}, timed=False)
        self.assertIn("runner", plan["tokens"]["unmeasured"])
        self.assertNotIn("output", plan["tokens"])

    def test_an_open_window_has_no_token_figure(self):
        plan = self.planning(self.ROWS[:1], stream=grok_usage(10), started=1001.0, improve={})
        self.assertIn("open", plan["tokens"]["unmeasured"])

    def test_a_claude_run_has_no_window_tokens_and_says_why(self):
        plan = self.planning(self.ROWS, stream=claude_stream(["echo hi"]), started=1001.0, improve={})
        self.assertIn("snapshot", plan["tokens"]["unmeasured"])

    def rollouts(self) -> list[list[str]]:
        root = [usage_line(1001, "root", "root", "r1", 1000, output=100, reasoning=40),
                usage_line(1010, "root", "root", "r2", 2000, output=200, reasoning=80),
                usage_line(1011, "root", "root", "r2", 2000, output=200, reasoning=80),  # the same response repeated
                usage_line(1020, "root", "root", "rq1", 9000, output=50, reasoning=0),   # a compaction request
                compacted_line(1020.01, "rq1"),
                usage_line(1040, "root", "root", "r3", 3000, output=300, reasoning=100),
                usage_line(1060, "root", "root", "r4", 3500, output=400, reasoning=150)]  # after the window
        sub = [usage_line(1030, "sub", "root", "s1", 5000, output=70, reasoning=30)]
        return [root, sub]

    def test_a_codex_window_counts_each_response_once_includes_compaction_requests_and_reports_sub_agents_apart(self):
        rows = [("a-intake", "intake", "done", 1002), ("a-ts", "test-spec", "done", 1050), ("a-impl", "implement", "done", 1100)]
        plan = self.planning(rows, stream=codex_stream(3), started=1001.0, improve={}, rollout_files=self.rollouts())
        # 100 + 200 + 50 (the compaction request) + 300; r2 once; r4 is after the window; the sub-agent's 70 is beside.
        self.assertEqual(plan["tokens"], {"output": 650, "reasoning": 220, "subagent_output": 70, "clock": "host",
                                          "source": "rollout token_usage_records"})

    def test_a_codex_run_with_no_rollouts_has_unmeasured_tokens(self):
        rows = [("a-ts", "test-spec", "done", 1050)]
        plan = self.planning(rows, stream=codex_stream(3), started=1001.0, improve={})
        self.assertIn("rollout", plan["tokens"]["unmeasured"])


class PlanningPlumbingTest(HarnessCase):
    def test_collect_leaves_the_top_level_unmeasured_map_alone(self):
        m = collect_stream(grok_usage(3), PLANNING_ROWS, status="active", first_event=1000.0, started=False)
        self.assertIn("window", m["planning"]["unmeasured"])
        self.assertFalse([name for name in m["unmeasured"] if "planning" in name], m["unmeasured"])

    def test_a_run_written_by_the_harness_carries_the_planning_block_in_metrics_json(self):
        code, result = self.invoke("grok", "done")
        out = Path(result["output"])
        written = json.loads((out / "metrics.json").read_text())
        self.assertIn("planning", written)
        self.assertEqual(set(written["planning"]), {"window", "stages", "improve", "producer_seconds", "tokens", "unmeasured"})
        self.assertNotIn("planning", result["metrics"], "result.json keeps its explicit subset; metrics.json is the evidence")

    def test_summary_lines_name_the_window_the_improve_share_and_the_tokens_right_after_the_counters(self):
        m = collect_stream(grok_usage(10), [("a-intake", "intake", "done", 1002), ("a-spec", "spec", "done", 1003),
                                            ("a-ts", "test-spec", "done", 1005)],
                           status="active", first_event=1000.0, started=1001.0,
                           inner={"improve_results": {"a-spec": {}}}, binds={"a-spec": 1002.0})
        lines = metrics.summary_lines(m)
        self.assertTrue(lines[0].startswith("turns "))
        self.assertEqual(lines[1], "planning window closed at test-spec: 0.1 min engine / 0.1 min host; Improve 0.0 min in 1 child, "
                                   "other 0.1 min; output tokens 600 (40% reasoning, host clock)")

    def test_summary_lines_say_when_the_window_could_not_be_measured(self):
        m = collect_stream(grok_usage(3), PLANNING_ROWS, status="active", first_event=1000.0, started=False)
        self.assertEqual(metrics.summary_lines(m)[1],
                         "planning window not measured: " + m["planning"]["unmeasured"]["window"])

    def test_progress_prints_the_planning_line_once_when_the_window_closes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_stream_run(out, grok_usage(10), PLANNING_ROWS[:1], status="active", first_event=1000.0, started=1030.0,
                             inner={"improve_results": {}})
            self.assertNotIn("planning window", progress.report(out))  # still open: nothing to print
            write_stream_run(out, grok_usage(10), PLANNING_ROWS, status="active", first_event=1000.0, started=1030.0,
                             inner={"improve_results": {}})
            first, second = progress.report(out), progress.report(out)
            self.assertIn("planning window closed at test-spec: 6.2 min engine / 6.7 min host", first)
            self.assertNotIn("planning window", second)


class RecordedRunReproductionTest(unittest.TestCase):
    """The planning block reproduces the figures of recorded runs (validated another way: real-run extracts).

    The extracts under docs/experiments/planning-measures-20261008/ hold the accepted rows, stamps, Improve bind times and
    per-call token rows of three recorded planning windows (no run text); `extract.py` rebuilds them from the run folders.
    The expected figures are the ones the 2026-10-05 planning-time account reported (Luna xhigh: window 374.95 min, 203.35
    in Improve children; Grok `none`: 20.5 min on the engine clock, 22.05 on the host's), recomputed on 2026-10-08."""

    EXTRACTS = ROOT / "docs" / "experiments" / "planning-measures-20261008"

    def planning(self, name: str) -> dict:
        data = json.loads((self.EXTRACTS / f"{name}.json").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_dir = out / "run"
            write_engine_records(run_dir, [(r["action"], r["stage"], r["outcome"], r["t"]) for r in data["rows"]],
                                 status="active", inner={"improve_results": {a: {} for a in data["improve"]}},
                                 started=data["started"])
            for action, mtime in data["improve"].items():
                bind = run_dir / "improve" / f"{action}-bind.md"
                bind.parent.mkdir(parents=True, exist_ok=True)
                bind.write_text("bound\n")
                os.utime(bind, (mtime, mtime))
            first = {"type": "available_commands", "commands": []}
            events, stamps = [first], [data["first_event"]]
            if data["host"] == "grok":
                for t, output, reasoning in data["usage"]:
                    events.append({"type": "usage", "usage": {"output_tokens": output, "reasoning_tokens": reasoning}})
                    stamps.append(t)
            if data["host"] == "claude":
                events.append({"type": "assistant", "message": {"id": "m0", "content": [{"type": "text", "text": "x"}]}})
                stamps.append(data["first_event"] + 1)
            (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
            (out / "timeline.jsonl").write_text("".join(json.dumps({"line": n, "t": t}) + "\n" for n, t in enumerate(stamps)))
            if data["host"] == "codex":
                lines = []
                for number, (t, output, reasoning, thread, request) in enumerate(data["rollouts"]):
                    lines.append(usage_line(t, "root" if thread == "main" else "sub", "root", f"r{number}", output + 1000,
                                            output=output, reasoning=reasoning))
                    if request:
                        lines.append(compacted_line(t + 0.01, f"r{number}"))
                write_rollout(out, "0", lines)
            return metrics.collect(out, run_dir)["planning"]

    def test_the_luna_xhigh_extract_reproduces_374_95_203_35_and_171_6_and_the_five_stage_improve_shares(self):
        plan = self.planning("luna-xhigh-1.21.0")
        window = plan["window"]
        self.assertEqual((window["closed"], round(window["seconds"] / 60, 2), round(window["host_seconds"] / 60, 2)),
                         (True, 374.95, 375.93))
        self.assertEqual((plan["improve"]["children"], round(plan["improve"]["seconds"] / 60, 2),
                          round(plan["producer_seconds"] / 60, 1)), (5, 203.35, 171.6))
        shares = {r["stage"]: round(r["improve_seconds"] / 60, 2) for r in plan["stages"] if r["improve_seconds"]}
        self.assertEqual(shares, {"spec": 44.49, "test-strategy": 61.06, "plan": 56.92, "step-plan": 26.7, "test-spec": 14.17})

    def test_the_luna_xhigh_tokens_include_the_compaction_requests_of_the_window(self):
        tokens = self.planning("luna-xhigh-1.21.0")["tokens"]
        # Leaving the 10 requests of the window out gives 1,116,758: their 37,141 output tokens carry no reasoning.
        self.assertEqual((tokens["output"], tokens["reasoning"], tokens["subagent_output"]), (1153899, 682569, 0))
        self.assertEqual(round(100 * tokens["reasoning"] / tokens["output"], 1), 59.2)

    def test_the_grok_none_extract_reproduces_20_5_engine_22_05_host_and_86986_tokens_at_43_percent_reasoning(self):
        plan = self.planning("grok-none-1.22.0")
        window = plan["window"]
        self.assertEqual((round(window["seconds"] / 60, 2), round(window["host_seconds"] / 60, 2), window["before_engine_seconds"]),
                         (20.5, 22.05, 92.8))
        self.assertEqual(plan["improve"], {"children": 0, "seconds": 0.0})
        self.assertEqual(plan["tokens"], {"output": 86986, "reasoning": 37770, "clock": "host", "source": "usage events"})
        self.assertEqual(round(100 * 37770 / 86986, 1), 43.4)

    def test_the_sonnet_extract_reproduces_6_47_minutes_and_2_57_in_five_improve_children_with_no_token_figure(self):
        plan = self.planning("sonnet-1.23.0")
        self.assertEqual((round(plan["window"]["seconds"] / 60, 2), plan["improve"]["children"],
                          round(plan["improve"]["seconds"] / 60, 2)), (6.47, 5, 2.57))
        self.assertIn("snapshot", plan["tokens"]["unmeasured"])


class SonnetCostDecompositionTest(unittest.TestCase):
    """The Sonnet cost rise of the batch-1007 live pair, rebuilt from the committed export (the folders are outside the repo).

    `inputs` of docs/experiments/batch-1007-live-20261007/cost-decomposition.json holds what cost_decomposition.py read
    from the two run folders; `recomputed` must equal `decompose(inputs)`, so the LEARNINGS entry that cites it can be
    checked by a script run instead of being taken from a model-judged account (journal rule)."""

    DIR = ROOT / "docs" / "experiments" / "batch-1007-live-20261007"

    def setUp(self):
        spec = importlib.util.spec_from_file_location("cost_decomposition", self.DIR / "cost_decomposition.py")
        self.script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.script)
        self.data = json.loads((self.DIR / "cost-decomposition.json").read_text())

    def test_the_recomputed_figures_are_the_arithmetic_on_the_committed_inputs(self):
        self.assertEqual(self.script.decompose(self.data["inputs"]), self.data["recomputed"])

    def test_the_fitted_rates_reproduce_both_recorded_session_costs(self):
        for name, cost in (("old", 6.5405192), ("new", 9.6542784)):
            self.assertAlmostEqual(self.script.cost(self.data["inputs"][name]["usage"]), cost, places=7)
            self.assertLess(self.data["recomputed"][name]["fit_error_usd"], 1e-6)

    def test_the_rise_is_the_sum_of_its_components_and_most_of_it_is_cache_reads_of_the_extra_calls(self):
        r = self.data["recomputed"]
        self.assertAlmostEqual(sum(r["rise_by_component_usd"].values()), r["rise_usd"], places=3)
        self.assertEqual(r["rise_usd"], 3.1138)
        self.assertGreater(r["rise_by_component_usd"]["cache_read_input_tokens"], 0.8 * r["rise_usd"])
        q = r["quadratic"]
        self.assertEqual((q["first_calls_of_the_new_run"], q["extra_calls"]), (133, 34))
        self.assertEqual(q["cache_read_tokens_of_those_calls"] + q["cache_read_tokens_of_extra_calls"],
                         self.data["inputs"]["new"]["usage"]["cache_read_input_tokens"])
        self.assertGreater(q["share_of_the_increase_in_the_extra_calls"], 0.8)

    def test_the_two_runs_are_not_a_controlled_pair(self):
        old, new = self.data["inputs"]["old"], self.data["inputs"]["new"]
        self.assertNotEqual(old["claude_code_version"], new["claude_code_version"])
        self.assertEqual(old["versions"]["plugin_version"], new["versions"]["plugin_version"])
        self.assertNotEqual(old["versions"]["local_head"], new["versions"]["local_head"])

    def test_decompose_splits_the_cache_reads_of_a_longer_run_at_the_length_of_the_shorter(self):
        usage = lambda cr: {"input_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": cr, "output_tokens": 0}  # noqa: E731
        old = {"cost_usd": 1.0, "usage": usage(30), "cache_read_per_call": [10, 20], "context_per_call": [10, 20]}
        new = {"cost_usd": 2.0, "usage": usage(70), "cache_read_per_call": [10, 20, 40], "context_per_call": [10, 20, 40]}
        q = self.script.decompose({"old": old, "new": new})["quadratic"]
        self.assertEqual((q["cache_read_tokens_of_those_calls"], q["cache_read_tokens_of_extra_calls"]), (30, 40))
        self.assertEqual((q["against_the_old_run"], q["share_of_the_increase_in_the_extra_calls"]), (0.0, 1.0))


if __name__ == "__main__":
    unittest.main()
