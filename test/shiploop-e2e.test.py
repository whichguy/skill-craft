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
elif mode in ("resume", "stuck"):
    Path(".shiploop").mkdir(exist_ok=True)
    store.write_record(Path(".shiploop/state.md"), {{"status": "active", "stage": "test-refine", "revision": 25}})
print(json.dumps({{"type": "end", "stopReason": "cancelled", "sessionId": "sess-1", "num_turns": 4,
                  "total_cost_usd": 0.01}}))
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
        self.assertIn("is not origin/main", " ".join(run.version_gate(behind, "1.4.0", "0.37.0")))
        self.assertIn("installed skill-craft 1.3.0", " ".join(run.version_gate(self.RELEASED, "1.3.0", "0.37.0")))
        self.assertIn("installed ShipLoop 0.36.0", " ".join(run.version_gate(self.RELEASED, "1.4.0", "0.36.0")))
        for ci in ("failure", "pending"):
            self.assertIn(f"CI is {ci}", " ".join(run.version_gate(dict(self.RELEASED, ci=ci), "1.4.0", "0.37.0")))
        self.assertEqual(run.version_gate(dict(self.RELEASED, ci="unknown"), "1.4.0", "0.37.0"), [])
        pending = dict(self.RELEASED, unreleased=["changes/shiploop/fix.md"])
        self.assertIn("unreleased changes (changes/shiploop/fix.md)", " ".join(run.version_gate(pending, "1.4.0", "0.37.0")))

    def test_card_version_reads_only_the_front_matter(self):
        with tempfile.TemporaryDirectory() as tmp:
            card = Path(tmp) / "SKILL.md"
            card.write_text("---\nname: shiploop\nversion: 0.37.0\n---\nversion: 9.9.9 in the body\n")
            self.assertEqual(run.card_version(card), "0.37.0")
            self.assertIsNone(run.card_version(Path(tmp) / "missing.md"))


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

    def test_reviewer_and_improver_prompts_carry_prior_learnings(self):
        prior = "commit abc1234\nRun 1 learned the graph is fixed.\n"
        self.assertIn("Run 1 learned the graph is fixed.", review.reviewer_prompt(Path("/r"), Path("/s"), prior))
        self.assertNotIn("Learnings recorded", review.reviewer_prompt(Path("/r"), Path("/s")))
        self.assertIn("Run 1 learned the graph is fixed.", iterate.improver_prompt(Path("/w"), [], "base", prior))
        improver = iterate.improver_prompt(Path("/w"), [], "base")
        self.assertIn("adversarial evaluation", improver)
        self.assertIn("mitigated and tested / accepted with the clause that asks for it", improver)
        self.assertIn("**Adversarial evaluation first.**", improver)  # the spec, loaded as the premise


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
            for name, stage, when in (("1-intake.md", "intake", 104.5), ("2-spec.md", "spec", 111.5)):
                path = run_dir / "results" / name
                path.write_text(f'```json\n{{"stage": "{stage}"}}\n```\n')
                os.utime(path, (when, when))
            m = metrics.collect(out, run_dir)
        self.assertEqual(m["turns"], 3)
        self.assertEqual(m["cost_usd"], 3.0)
        self.assertEqual(m["compactions"], 1)
        self.assertEqual(m["truncated_outputs"], 2)
        self.assertEqual(m["script_verifications"], {"records": 0, "passed": 0, "commands": 0})
        self.assertEqual(m["cancelled_tool_calls"], ["git init -b main"])
        self.assertEqual(m["asked_user"], ["Which port?"])
        self.assertEqual(m["improve_children"], 1)
        self.assertEqual(m["shiploop_failures"], [{"verb": "complete", "exit": 2, "line": "error: result refused"}])
        self.assertEqual([(s["stage"], s["turns"]) for s in m["stages"]], [("intake", 2), ("spec", 1)])
        self.assertEqual(m["stages"][0]["cost_share_usd"], 2.0)

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
            # reading ShipLoop's own contract is not building one
            'python3 -c \'import json; p=json.load(open("/x/run/quality/c-contract.json")); print(p["exit_condition"])\'': [],
            'python3 -c \'import json; json.dump({"exit_condition": 1}, open("/x/c.json", "w"))\'': ["hand-built loop contract"],
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
                             {"records": 2, "passed": 1, "commands": 3})

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
        self.assertIn("model_reasoning_effort=xhigh", argv)
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

    def test_resume_run_refuses_a_run_that_is_not_active(self):
        code, finished = self.invoke("grok", "done")
        self.assertEqual(code, 0)
        with self.assertRaisesRegex(SystemExit, "needs an active ShipLoop run"):
            run.main(["--host", "codex", "--codex-bin", str(self.fakes["codex"]),
                      "--resume-run", finished["output"], "--plugin-dir", str(self.plugin)])


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

if __name__ == "__main__":
    unittest.main()
