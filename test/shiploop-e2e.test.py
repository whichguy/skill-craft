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
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import hosts  # noqa: E402
import iterate  # noqa: E402
import metrics  # noqa: E402
import progress  # noqa: E402
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
    # A finished run leaves its product committed, as ShipLoop's return does.
    import subprocess
    Path(".gitignore").write_text(".shiploop/\\n")
    ident = ["-c", "user.name=Fake", "-c", "user.email=fake@example.invalid"]
    if not Path(".git").exists():
        subprocess.run(["git", "init", "-q"], check=True)
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", *ident, "commit", "-qm", "product"], check=True)
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


class CheckHygieneTest(unittest.TestCase):
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
        self.assertEqual(m["test_runs"], 1)
        self.assertEqual(m["cancelled_tool_calls"], ["git init -b main"])
        self.assertEqual(m["improve_children"], 1)
        self.assertEqual(m["shiploop_failures"], [{"verb": "complete", "exit": 2, "line": "error: result refused"}])
        self.assertEqual([(s["stage"], s["turns"]) for s in m["stages"]], [("intake", 2), ("spec", 1)])
        self.assertEqual(m["stages"][0]["cost_share_usd"], 2.0)

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


if __name__ == "__main__":
    unittest.main()
