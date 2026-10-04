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
import io
import json
import shutil
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import hosts  # noqa: E402
import iterate  # noqa: E402
import metrics  # noqa: E402
import progress  # noqa: E402
import review  # noqa: E402
import run  # noqa: E402
import fanout  # noqa: E402

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
    store.write_record(Path(".shiploop/state.md"), {{"status": "done"}})
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

# FAKE_MODE: done (product + done run), nothing (exit 0, no work), no-skill (done,
# but no ShipLoop command registered).
FAKE_CLAUDE = f"""#!{sys.executable}
import json, os, sys
from pathlib import Path
{PRODUCT}
argv = sys.argv[1:]
Path(os.environ["FAKE_LOG"]).write_text(json.dumps({{"argv": argv, "cwd_listing": os.listdir(".")}}))
mode = os.environ.get("FAKE_MODE")
plugin = argv[argv.index("--plugin-dir") + 1] if "--plugin-dir" in argv else None
print(json.dumps({{"type": "system", "subtype": "init", "model": "fake-model",
                  "slash_commands": [] if mode == "no-skill" else ["skill-craft:shiploop"],
                  "plugins": [{{"name": "skill-craft", "path": plugin}}] if plugin else []}}))
print(json.dumps({{"type": "assistant", "message": {{"content": [{{"type": "tool_use", "name": "Bash",
                  "input": {{"command": "shiploop next"}}}}]}}}}))
if mode in ("done", "no-skill"):
    product()
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
prompt = Path(argv[argv.index("--prompt-file") + 1]).read_text()
resumed = argv[argv.index("--resume") + 1] if "--resume" in argv else None
with open(os.environ["FAKE_LOG"] + ".sessions", "a") as log:
    log.write(json.dumps({{"resumed": resumed, "prompt": prompt}}) + "\\n")
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
mode = os.environ.get("FAKE_MODE")
if mode == "done" or (mode == "resume" and resumed):
    import shutil
    shutil.rmtree(".shiploop", ignore_errors=True)  # a resumed session finishes the same run
    product()
elif mode == "early" and not resumed:
    pass  # the first session ends before ShipLoop writes any state
elif mode == "early":
    product()
elif mode == "hang":
    print(json.dumps({{"type": "session", "sessionId": "sess-1"}}), flush=True)
    import time
    time.sleep(600)  # killed by --timeout
elif mode in ("resume", "stuck", "anon", "crash-resumed"):
    Path(".shiploop").mkdir(exist_ok=True)
    store.write_record(Path(".shiploop/state.md"), {{"status": "active", "stage": "test-refine", "revision": 25}})
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
            cli = out / "marketplace/plugins/skill-craft/skills/shiploop/scripts/shiploop"
            cli.parent.mkdir(parents=True)
            cli.write_text("#!/bin/sh\n")
            prompt = run.resume_prompt(out, "/r/run", hosts.host("claude"))
            self.assertIn(f'python3 "{cli}" next --run-dir "/r/run"', prompt)
            self.assertNotIn("`shiploop next", prompt)

    def test_without_an_installed_marketplace_build_the_bare_command_remains(self):
        with tempfile.TemporaryDirectory() as temp:
            prompt = run.resume_prompt(Path(temp), "/r/run", hosts.host("claude"))
            self.assertIn("`shiploop next --run-dir \"/r/run\"`", prompt)


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

    def test_interrupt_kills_the_host_mid_chain_and_a_fresh_session_finishes(self):
        code, result = self.invoke("claude", "chain-hang", "--interrupt-at", "chain-launched")
        self.assertEqual(code, 0, {k: result.get(k) for k in ("process", "chain", "recovery", "shiploop")})
        sessions = result["process"]["sessions"]
        self.assertEqual([s["status"] for s in sessions], ["interrupted", "exited"])
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
            text = json.dumps({"schema": "run-review-export/v1", "docs": {"runs": {"grok-1.0.0-hello-20261004": {}}}})
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
        run.store.write_record(state_dir / "state.md", {"status": "done", "stage": "done", "history": []})
        run.store.write_record(state_dir / "results" / "nav-0123456789abcdef.md",
                           {"action": "nav-0123456789abcdef", "stage": "intake", "result": {"outcome": "done"}})
        (state_dir / "timeline.json").write_text(json.dumps({"started": "2026-10-04T10:00:00Z", "accepted": {
            "nav-0123456789abcdef": "2026-10-04T10:03:00Z"}}))
        (out / "metrics.json").write_text(json.dumps({"shiploop_failures": [], "model_glue": []}))
        line = run.review_export(out)
        self.assertEqual(line, f"review export: {(out / 'review-export').resolve()}")
        bundle = json.loads((out / "review-export" / "review-export.json").read_text())
        self.assertEqual([s["min"] for s in next(iter(bundle["docs"]["runs"].values()))["stages"]], [3.0])

    def test_preflight_only_never_exports(self):
        with mock.patch.object(run, "marketplace_preflight", return_value=(self.plugin, None, {"gate": []})), \
                mock.patch.object(run, "review_export") as exporter:
            self.assertEqual(run.main(["--preflight-only", "--host", "claude", "--output", str(self.tmp / "pf")]), 0)
        exporter.assert_not_called()


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
                         stage: str | None = None, inner: dict | None = None) -> None:
    """Write the state.md and timeline.json a run would leave behind.

    ``accepted`` is (action, stage, outcome, epoch-or-None); an action with None
    gets no acceptance stamp, which is how an unreadable or recreated timeline
    looks to the reader.
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

    (run_dir / "timeline.json").write_text(json.dumps(
        {"started": stamp(min((t for *_x, t in accepted if t is not None), default=0)),
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
                         {"records": 0, "passed": 0, "could_not_run": 0, "commands": 0})
        self.assertEqual(m["cancelled_tool_calls"], ["git init -b main"])
        self.assertEqual(m["asked_user"], ["Which port?"])
        self.assertEqual(m["improve_children"], 1)
        self.assertEqual(m["shiploop_failures"], [{"verb": "complete", "exit": 2, "line": "error: result refused"}])
        self.assertEqual([(s["stage"], s["turns"]) for s in m["stages"]], [("intake", 2), ("spec", 1)])
        self.assertEqual([s["outcome"] for s in m["stages"]], ["done", "done"])
        # No cost is apportioned per stage: a share of one total, split by turn
        # count, moves when prices or unrelated work move.
        self.assertTrue(all("cost_share_usd" not in s for s in m["stages"]))

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
                             {"records": 2, "passed": 1, "could_not_run": 0, "commands": 3})

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
        self.assertIn("model_reasoning_effort=max", argv)
        self.assertTrue(result["invoked"]["pass"], result["invoked"])
        self.assertTrue(result["plugin"]["pass"], result["plugin"])
        self.assertTrue(result["committed"]["pass"], result["committed"])
        self.assertEqual(result["cli"]["num_turns"], 2)

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
        rows = [json.loads(line) for line in self.baselines.read_text().splitlines()]
        self.assertEqual(len(rows), 1, "only the original run writes a baseline row; a resume does not")

    def test_resume_run_refuses_a_run_that_is_neither_active_nor_done(self):
        code, finished = self.invoke("grok", "done")
        self.assertEqual(code, 0)
        with mock.patch.object(run, "grade_shiploop", return_value={"status": "paused"}):
            with self.assertRaisesRegex(SystemExit, "needs an active or finished ShipLoop run"):
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
        self.assertEqual((codex.model, codex.effort, codex.resumable), ("gpt-6-luna", "max", True))

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
            self.assertEqual((seen["num_turns"], seen["cost_usd"], seen["commands"]), (4, 0, []))
            self.assertEqual(hosts.final_text(path).strip(), "Done for now.")
            run.write_transcript(path, out / "transcript.md")
            transcript = (out / "transcript.md").read_text()
            self.assertIn("tool  run_terminal_command:", transcript)
            self.assertIn("say   Done for now.", transcript)
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

def collect_stream(stream: list, accepted: list, *, status: str = "done", stage: str | None = None,
                   inner: dict | None = None, first_event: float = 100.0, extra: dict | None = None) -> dict:
    """metrics.collect over a hand-built host stream, one second between events, ShipLoop records beside it."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        run_dir = out / "run"
        (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in stream))
        (out / "timeline.jsonl").write_text("".join(
            json.dumps({"line": n, "t": first_event + n}) + "\n"
            for n, e in enumerate(stream) if e.get("type") not in ("text", "thought")))
        write_engine_records(run_dir, accepted, status=status, stage=stage, inner=inner)
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


class HostCoverageTest(unittest.TestCase):
    """A counter the host's events cannot show is unmeasured, never a zero that passes a comparison."""

    ACCEPTED = [("A1", "intake", "done", 105.0), ("A2", "spec", "done", 113.0)]

    def test_a_host_with_no_per_call_usage_has_no_stage_turns_not_zero_turns(self):
        m = collect_stream(codex_stream(12), self.ACCEPTED)
        self.assertIn("stage_turns", m["unmeasured"])
        self.assertIn("output_tokens", m["unmeasured"])
        self.assertNotIn("model_glue", m["unmeasured"])  # Codex's tool calls are parsed
        self.assertEqual([r["seconds"] for r in m["stages"]], [5.0, 8.0])  # time is still measured
        for row in m["stages"]:
            self.assertIsNone(row["turns"])
            self.assertIsNone(row["output_tokens"])
            self.assertGreater(row["tool_calls"], 0)
        self.assertEqual(m["turns"], 12)  # the session's own total is still reported
        self.assertEqual(m["tokens"], {"input_peak": None, "output_total": None})
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

    def test_a_claude_stream_marks_the_counters_it_cannot_read_as_unmeasured(self):
        stream = claude_stream(["git add -A && git commit -m x", "shiploop complete --run-dir r"] * 3)
        m = collect_stream(stream, self.ACCEPTED)
        for name in ("model_glue", "shiploop_failures", "cancelled_tool_calls", "tmp_writes",
                     "stage_tool_calls", "output_tokens"):
            self.assertIn(name, m["unmeasured"], name)
        self.assertNotIn("stage_turns", m["unmeasured"])
        self.assertEqual(m["model_glue"], [], "the lists stay: they are lower bounds, and the exporter reads them")
        self.assertTrue(all(r["tool_calls"] is None and r["output_tokens"] is None and r["turns"] is not None
                            for r in m["stages"]))
        self.assertIsNone(m["tokens"]["output_total"])
        self.assertIsNone(metrics.count(m, "model_glue"))
        self.assertEqual(metrics.count({"unmeasured": {}, "model_glue": [1, 2]}, "model_glue"), 2)
        first = metrics.summary_lines(m)[0]
        self.assertIn("model glue not measured", first)
        self.assertIn("ShipLoop command failures not measured", first)
        self.assertIn("cancelled tool calls not measured", first)

    def test_a_grok_shaped_stream_measures_every_counter(self):
        stream = [{"type": "usage", "usage": {"input_tokens": 1, "output_tokens": 1}},
                  {"type": "tool_call", "toolCallId": "a", "rawInput": {"command": "git add -A"}}] * 4
        self.assertEqual(collect_stream(stream, self.ACCEPTED)["unmeasured"], {})

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
        self.assertEqual(self.last_row()["termination"], t)
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
    def test_claude_runs_say_which_counters_they_cannot_show_and_never_compare_them_as_zeros(self):
        code, first, printed = self.invoke_printed("claude", "done")
        self.assertEqual(code, 0, first)
        for name in ("model_glue", "shiploop_failures", "cancelled_tool_calls", "tmp_writes"):
            self.assertIsNone(first["metrics"][name], name)
            self.assertIn(name, first["metrics"]["unmeasured"])
        self.assertIn("model glue not measured", printed)
        self.assertEqual(self.last_row()["model_glue"], None)
        code, second, printed = self.invoke_printed("claude", "done")
        self.assertIn("glue not measured -> not measured", printed)


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
                             {"records": 3, "passed": 1, "could_not_run": 1, "commands": 3})

    def test_the_report_and_the_progress_line_show_the_could_not_run_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self.records(tmp)
            out = Path(tmp)
            (out / "events.jsonl").write_text(json.dumps({"type": "usage", "usage": {"input_tokens": 1}}) + "\n")
            write_engine_records(run_dir, [("A1", "intake", "done", 101.0)])
            m = metrics.collect(out, run_dir)
            self.assertIn("script verifications 1/3 passed (1 could not run)", metrics.summary_lines(m)[0])
            self.assertIn("1 could not run", progress.report(out))



if __name__ == "__main__":
    unittest.main()
