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
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import hosts  # noqa: E402
import review  # noqa: E402
import run  # noqa: E402

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
Path(os.environ["FAKE_LOG"]).write_text(json.dumps({{
    "argv": argv, "prompt": prompt, "cwd_listing": os.listdir("."), "home": str(home),
    "auth_is_symlink": (home / ".grok" / "auth.json").is_symlink(),
    "claude_skills": os.environ.get("GROK_CLAUDE_SKILLS_ENABLED")}}))
print(json.dumps({{"type": "available_commands", "tools": [], "commands": ["shiploop", "improve"]}}))
print(json.dumps({{"type": "tool_call", "toolName": "run_terminal_command", "rawInput": {{"command": "shiploop next"}}}}))
for chunk in ("Ship", "ped."):
    print(json.dumps({{"type": "text", "data": chunk}}))
if os.environ.get("FAKE_MODE") == "done":
    product()
print(json.dumps({{"type": "end", "stopReason": "end_turn", "num_turns": 4, "total_cost_usd": 0.01}}))
"""


class HarnessCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.fakes = {}
        for name, body in (("claude", FAKE_CLAUDE), ("grok", FAKE_GROK)):
            path = self.tmp / name
            path.write_text(body)
            path.chmod(path.stat().st_mode | stat.S_IXUSR)
            self.fakes[name] = path
        self.plugin = self.tmp / "build" / "plugins" / "skill-craft"
        (self.plugin / ".claude-plugin").mkdir(parents=True)
        (self.plugin / ".claude-plugin" / "plugin.json").write_text("{}")
        self.log = self.tmp / "fake-log.json"
        os.environ["FAKE_LOG"] = str(self.log)
        self.addCleanup(os.environ.pop, "FAKE_MODE", None)
        auth = self.tmp / "auth.json"
        auth.write_text("{}")
        saved, hosts.GROK_AUTH = hosts.GROK_AUTH, auth
        self.addCleanup(setattr, hosts, "GROK_AUTH", saved)

    def invoke(self, host: str, mode: str, *extra: str) -> tuple[int, dict]:
        os.environ["FAKE_MODE"] = mode
        out = self.tmp / f"out-{host}-{mode}"
        with contextlib.redirect_stdout(io.StringIO()):
            code = run.main(["--host", host, f"--{host}-bin", str(self.fakes[host]), "--output", str(out),
                             "--plugin-dir", str(self.plugin), *extra])
        return code, json.loads((out / "result.json").read_text())

    def seen(self) -> dict:
        return json.loads(self.log.read_text())


class GrokRunTest(HarnessCase):
    def test_grok_is_the_default_host_at_medium_effort(self):
        self.assertEqual(run.parser().parse_args([]).host, "grok")
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

    def test_missing_grok_sign_in_stops_before_launch(self):
        hosts.GROK_AUTH = self.tmp / "absent.json"
        with self.assertRaises(SystemExit):
            self.invoke("grok", "done")
        self.assertFalse(self.log.exists())


class ClaudeRunTest(HarnessCase):
    def test_done_run_invokes_the_namespaced_skill_with_isolated_settings(self):
        code, result = self.invoke("claude", "done")
        self.assertEqual(code, 0, result)
        argv = self.seen()["argv"]
        prompt = json.loads(run.CASES.read_text())["hello"]["prompt"]
        self.assertEqual(argv[:2], ["-p", "/skill-craft:shiploop " + prompt])
        self.assertEqual(argv[argv.index("--model") + 1], "sonnet")
        self.assertEqual(argv[argv.index("--setting-sources") + 1], "project,local")
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
        self.assertIn("the script is the\norchestrator", prompt)
        for key in review.CATEGORIES:
            self.assertIn(key, prompt)


if __name__ == "__main__":
    unittest.main()
