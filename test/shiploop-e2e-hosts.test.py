"""ShipLoop E2E tests grouped by responsibility."""
from __future__ import annotations

import importlib as _component_importlib
import pathlib as _component_pathlib
import sys as _component_sys

_component_test_dir = str(_component_pathlib.Path(__file__).resolve().parent)
if _component_test_dir not in _component_sys.path:
    _component_sys.path.insert(0, _component_test_dir)
_support = _component_importlib.import_module("shiploop-e2e-support")
globals().update({name: value for name, value in vars(_support).items()
                  if not name.startswith("__") and name not in {"_tests_from_namespace", "_tests_from_modules"}})


def load_tests(loader, standard_tests, pattern):
    return _support._tests_from_namespace(loader, __name__, globals(), pattern)




class GrokRunTest(HarnessCase):
    def test_sol_high_is_the_default_subject_and_explicit_hosts_keep_their_profiles(self):
        self.assertEqual(run.parser().parse_args([]).host, "codex")
        self.assertEqual(hosts.HOST_DEFAULTS["codex"], {"model": "gpt-6.1-sol", "effort": "high"})
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

    def test_marketplace_records_the_actual_install_path_without_relaxing_failed_installs(self):
        for name in ("codex", "grok"):
            for passed, path in ((True, "/installed/skill-craft"), (False, None)):
                with self.subTest(host=name, passed=passed):
                    installed = {"pass": passed, "path": path, "loaded": ["installed"] if passed else [],
                                 "source": "whichguy/skill-craft", "version": "1.4.0"}
                    host = argparse.Namespace(name=name, marketplace=True,
                                              install_marketplace=mock.Mock(return_value=installed))
                    versions = {"plugin_version": "1.4.0", "shiploop_version": "0.37.0"}
                    env = {"HOME": "/isolated"}
                    with mock.patch.object(run, "the_host", return_value=host), \
                            mock.patch.object(run, "released_versions", return_value=self.RELEASED), \
                            mock.patch.object(run, "installed_versions", return_value=versions), \
                            contextlib.redirect_stdout(io.StringIO()):
                        selected, plugin, recorded = run.marketplace_preflight(argparse.Namespace(), Path("/out"), env)
                    host.install_marketplace.assert_called_once_with(env)
                    self.assertEqual(selected, Path(path) if path else Path("/out/missing-plugin"))
                    self.assertEqual(plugin["path"], path)
                    self.assertEqual(plugin["pass"], passed)
                    self.assertEqual(bool(recorded["gate"]), not passed)

    def test_marketplace_export_keeps_no_install_record_for_a_host_without_an_installer(self):
        host = argparse.Namespace(name="claude", marketplace=False)
        versions = {"plugin_version": "1.4.0", "shiploop_version": "0.37.0"}
        with mock.patch.object(run, "the_host", return_value=host), \
                mock.patch.object(run, "released_versions", return_value=self.RELEASED), \
                mock.patch.object(run, "export_released", return_value=Path("/export/plugin")), \
                mock.patch.object(run, "installed_versions", return_value=versions), \
                contextlib.redirect_stdout(io.StringIO()):
            selected, plugin, recorded = run.marketplace_preflight(argparse.Namespace(), Path("/out"), {})
        self.assertEqual(selected, Path("/export/plugin"))
        self.assertIsNone(plugin)
        self.assertEqual(recorded["gate"], [])


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
        self.assertTrue(packet.stdout.startswith("Execute the prompt in a fresh context."), packet.stdout[:200])
        self.assertIn("\nShipLoop navigator | step-plan |", packet.stdout)
        self.assertTrue(packet.stdout.endswith("=== end ShipLoop print ===\n"))

    def test_seeded_run_opens_at_the_run_and_writes_no_baseline(self):
        shutil.rmtree(self.plugin / "skills")  # the real skills, and so the real CLI, replace the fixture's stub
        (self.plugin / "skills").symlink_to(ROOT / "skills")
        code, result = self.invoke("claude", "nothing", "--seed-at", "step-plan")
        self.assertEqual(code, 1, result)
        prompt = self.seen()["argv"][1]
        self.assertIn(f'next --run-dir "{result["seeded"]["run_dir"]}"', prompt)
        self.assertIn("stages before step-plan without doing them", prompt)
        self.assertEqual(result["committed"]["start_head"], result["seeded"]["start_head"])
        self.assertNotIn("chain", result)    # the chain grade is retired with the chain (design T §9.1 2c-2)
        self.assertFalse(self.baselines.exists())


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
        self.assertEqual(argv[argv.index("-m") + 1], "gpt-6.1-sol")
        self.assertIn("model_reasoning_effort=high", argv)
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

    def test_a_plugin_build_the_host_failed_to_install_starts_no_host(self):
        # 2026-10-30: a --plugin-dir whose root had no Codex catalog was never enabled, and the host still ran.
        out = self.tmp / "out-codex-failed-install"
        with mock.patch.dict(os.environ, {"FAKE_PLUGIN_FAIL": "1", "FAKE_MODE": "done"}), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as refused:
            run.main(["--host", "codex", "--codex-bin", str(self.fakes["codex"]), "--output", str(out),
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        self.assertIn("so no host is started", str(refused.exception))
        self.assertIn("no marketplace catalog", str(refused.exception))  # the install's own output says why
        self.assertFalse(self.log.exists(), "the host was launched")
        self.assertFalse((out / "result.json").exists())

    def test_only_a_failed_install_check_refuses(self):
        run.require_installed(None, self.plugin)  # Claude: loaded from its argv, graded from its init event
        run.require_installed({"pass": True, "loaded": ["skill-craft@whichguy 9.9.9"]}, self.plugin)
        with self.assertRaises(SystemExit) as refused:
            run.require_installed({"pass": False, "loaded": []}, self.plugin)
        self.assertIn("(loaded: no plugin)", str(refused.exception))

    def test_model_and_effort_toggle_by_flag(self):
        code, result = self.invoke("codex", "done", "--model", "gpt-6-sol", "--effort", "xhigh")
        self.assertEqual(code, 0, result)
        argv = self.seen()["argv"]
        self.assertEqual(argv[argv.index("-m") + 1], "gpt-6-sol")
        self.assertIn("model_reasoning_effort=xhigh", argv)
        self.assertIn('agents.default_subagent_model="gpt-6-sol"', argv)
        self.assertIn("agents.default_subagent_reasoning_effort=xhigh", argv)
        self.assertEqual((result["model"], result["effort"]), ("gpt-6-sol", "xhigh"))

    def test_resume_run_continues_a_stopped_grok_run_on_codex(self):
        code, stopped = self.invoke("grok", "stuck", "--max-resumes", "0")
        self.assertEqual(code, 1)
        out = Path(stopped["output"])
        original = (out / "invocation.json").read_text()
        os.environ["FAKE_MODE"] = "done"
        with contextlib.redirect_stdout(io.StringIO()):
            code = run.main(["--host", "codex", "--allow-host-change", "--codex-bin", str(self.fakes["codex"]), "--resume-run", str(out),
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
        self.assertEqual((codex.model, codex.effort, codex.resumable), ("gpt-6.1-sol", "high", True))

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

    def test_argv_trusts_the_hooks_of_its_throwaway_home_on_a_fresh_and_a_resumed_launch(self):
        # Codex runs a plugin's hooks only once they are trusted, and a fresh CODEX_HOME holds no trust: without the
        # flag the keepalive, the session-end hook and the takeover never run in a Codex round.
        codex = hosts.host("codex", "codex-bin")
        with tempfile.TemporaryDirectory() as temp:
            for resume in (None, "thread-1"):
                argv = codex.argv(prompt="go", prompt_file=Path(temp) / "p.txt", cwd=Path("/w"), model="gpt-6.1-terra",
                                  effort="xhigh", permission_mode="auto", max_turns=10, resume=resume)
                self.assertIn("--dangerously-bypass-hook-trust", argv)
                self.assertLess(argv.index("--dangerously-bypass-hook-trust"), argv.index(resume or "go"))
                if resume:
                    self.assertLess(argv.index("--dangerously-bypass-hook-trust"), argv.index("resume"))

    def test_the_trust_bypass_has_no_hook_to_trust_but_the_installed_plugins(self):
        # The flag is safe only because nothing else is there to run: the throwaway home links auth.json and nothing
        # that carries a hook or a trust record.
        with tempfile.TemporaryDirectory() as temp:
            real = Path(temp) / "real"
            real.mkdir()
            (real / "auth.json").write_text("{}")
            (real / "hooks.json").write_text('{"hooks": {"Stop": []}}')
            (real / "config.toml").write_text("[hooks.state]\n")
            with mock.patch.dict(os.environ, {"CODEX_HOME": str(real)}):
                env = hosts.host("codex").env(Path(temp) / "home")
            self.assertEqual(sorted(path.name for path in Path(env["CODEX_HOME"]).iterdir()), ["auth.json"])

    def test_the_keepalive_block_names_the_hooks_the_plugin_brings_to_codex(self):
        codex, grok = hosts.host("codex"), hosts.host("grok")
        with tempfile.TemporaryDirectory() as temp:
            plugin = Path(temp)
            self.assertFalse(codex.keepalive_install({}, plugin)["installed"])
            (plugin / "hooks").mkdir()
            (plugin / "hooks" / "codex.json").write_text("{}")
            self.assertTrue(codex.keepalive_install({}, plugin)["installed"])
            with mock.patch.object(hosts, "grok_keepalive", return_value={"installed": True}) as installer:
                self.assertEqual(grok.keepalive_install({"HOME": "h"}, plugin), {"installed": True})
                installer.assert_called_once_with({"HOME": "h"}, plugin)
            self.assertIsNone(hosts.host("claude").keepalive_install({}, plugin))

    def test_a_codex_notice_is_a_thought_not_a_tool_call_or_a_turn(self):
        # With hooks on, every launch opens with notices (the trust bypass, a clamped hook timeout); Codex sends them as
        # `error` items. Counted as tool calls they would add turns to every Codex run.
        translate = hosts.host("codex").translator()
        notices = [{"type": "item.completed", "item": {"id": f"item_{n}", "type": "error", "message": text}}
                   for n, text in enumerate(("`--dangerously-bypass-hook-trust` is enabled.",
                                             "clamping SessionEnd hook timeout to 3s in /h/hooks.json"))]
        events = [json.loads(raw) for event in [{"type": "thread.started", "thread_id": "t"}, *notices,
                                                {"type": "turn.completed", "usage": {}}]
                  for raw in translate((json.dumps(event) + "\n").encode())]
        self.assertEqual([e["type"] for e in events], ["available_commands", "thought", "thought", "end"])
        self.assertIn("clamping SessionEnd", events[2]["data"])
        self.assertEqual(events[-1]["num_turns"], 0)

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


class ThrowawayHomeEnvTest(unittest.TestCase):
    """A throwaway HOME has no login keychain, so a CLI that stores a secret there makes macOS show a modal "Keychain Not
    Found" dialog and blocks until someone answers it. The Salesforce CLI does on its first org command (2026-11-01, the
    start-route probe's trials); SF_USE_GENERIC_UNIX_KEYCHAIN keeps its key in <HOME>/.sfdx/key.json instead. The HOME that
    holds the login must never get it: the CLI would stop reading the keychain key and could not decrypt the saved logins."""

    VAR = "SF_USE_GENERIC_UNIX_KEYCHAIN"

    def test_the_codex_and_grok_throwaway_homes_carry_it(self):
        with tempfile.TemporaryDirectory() as temp:
            auth = Path(temp) / "auth.json"
            auth.write_text("{}")
            with mock.patch.dict(os.environ, {"CODEX_HOME": temp}), mock.patch.object(hosts, "GROK_AUTH", auth):
                for name in ("codex", "grok"):
                    home = Path(temp) / f"{name}-home"
                    env = hosts.host(name).env(home)
                    self.assertEqual(env["HOME"], str(home), name)
                    self.assertEqual(env[self.VAR], "true", name)

    def test_the_claude_host_runs_in_the_real_home_and_never_carries_it(self):
        with mock.patch.dict(os.environ):
            os.environ.pop(self.VAR, None)
            for backend in (None, "ollama"):
                env = hosts.host("claude", None, backend).env(Path(tempfile.gettempdir()) / "unused-home")
                self.assertNotIn(self.VAR, env, str(backend))


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


class ClaudeOnOllamaTest(PrintedCase):
    """SPEC "The Claude host can run on Ollama": `--backend ollama` runs Claude Code on a model the local Ollama server
    serves, with ask-ollama's verified route. No credential of the launching session reaches the child, only the coding
    tools do, a run is refused before any model starts when Ollama is not ready, cost is not measured, and the backend is
    part of the driver."""

    SECRETS = {"ANTHROPIC_AUTH_TOKEN": "real-oauth-bearer", "ANTHROPIC_API_KEY": "sk-ant-real-key",
               "CLAUDE_CODE_OAUTH_TOKEN": "real-oauth-token", "CLAUDECODE": "1", "CLAUDE_CODE_SESSION_ID": "parent-session",
               "CLAUDE_EFFORT": "xhigh", "CLAUDE_PROXY_BYPASS": "1", "ANTHROPIC_BASE_URL": "https://api.anthropic.com"}

    def wrapper(self) -> Path:
        """The fake claude behind a script that writes the environment it was given, as the real child would see it."""
        wrapper = self.tmp / "claude-env"
        wrapper.write_text(f'#!/bin/sh\nenv > "{self.tmp / "child-env.txt"}"\nexec "{self.fakes["claude"]}" "$@"\n')
        wrapper.chmod(0o755)
        return wrapper

    def child_env(self) -> dict:
        return dict(line.split("=", 1) for line in (self.tmp / "child-env.txt").read_text().splitlines() if "=" in line)

    def ollama(self, *extra: str, ready: str | None = None, backend: tuple = ("--backend", "ollama")) -> tuple[int, Path, str]:
        os.environ["FAKE_MODE"] = "done"
        out = self.tmp / f"out-ollama-{len(list(self.tmp.glob('out-ollama-*')))}"
        printed = io.StringIO()
        with mock.patch.dict(os.environ, self.SECRETS), mock.patch.object(run.hosts, "ollama_ready", return_value=ready), \
                contextlib.redirect_stdout(printed):
            code = run.main(["--host", "claude", *backend, "--claude-bin", str(self.wrapper()), "--output", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), *extra])
        return code, out, printed.getvalue()

    def test_an_e2e_run_defaults_to_claudes_own_models_and_ollama_is_named(self):
        code, out, printed = self.ollama(backend=())
        self.assertEqual(code, 0, printed)
        result = json.loads((out / "result.json").read_text())
        self.assertEqual((result["backend"], result["model"]), ("anthropic", "claude-sonnet-5-5"))
        env = self.child_env()
        self.assertEqual((env["ANTHROPIC_BASE_URL"], env["ANTHROPIC_AUTH_TOKEN"]),
                         (self.SECRETS["ANTHROPIC_BASE_URL"], self.SECRETS["ANTHROPIC_AUTH_TOKEN"]),
                         "the child keeps the user's Anthropic route; nothing sends it to Ollama")
        argv = json.loads(self.log.read_text())["argv"]
        self.assertEqual(argv[argv.index("--model") + 1], "claude-sonnet-5-5")
        self.assertNotIn("--tools", argv, "the coding-tool allowlist is the Ollama route's")
        self.assertEqual((hosts.HOST_DEFAULTS["claude"]["model"], hosts.HOST_DEFAULTS["grok"]["model"]),
                         ("claude-sonnet-5-5", hosts.GrokHost.model))
        ollama = run.the_host(run.parser().parse_args(["--host", "claude", "--backend", "ollama"]))
        self.assertEqual((ollama.backend, ollama.model), ("ollama", hosts.OLLAMA_MODEL), "--backend ollama names the Ollama route")
        self.assertEqual(hosts.host("claude").backend, "anthropic", "the factory's default and the run's are the same")

    def test_a_regrade_of_a_run_from_before_the_backend_field_stays_anthropic(self):
        _, out, _ = self.ollama(backend=("--backend", "anthropic"))
        for path in out.glob("invocation*.json"):  # as a run recorded before the field existed
            record = json.loads(path.read_text())
            record.pop("backend", None)
            path.write_text(json.dumps(record))
        with contextlib.redirect_stdout(io.StringIO()):
            run.main(["--resume-run", str(out), "--grade-only", "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        self.assertEqual(json.loads((out / "result.json").read_text())["backend"], "anthropic",
                         "the run default must not relabel an Anthropic run as an Ollama one")

    def test_no_credential_of_the_launching_session_reaches_the_child(self):
        code, out, printed = self.ollama()
        self.assertEqual(code, 0, printed)
        env = self.child_env()
        leaked = [name for name, value in env.items() if any(secret in value for secret in self.SECRETS.values() if len(secret) > 1)]
        self.assertEqual(leaked, [], "a token of the parent reached the child")
        self.assertEqual(sorted(k for k in env if k.startswith(("ANTHROPIC", "CLAUDE"))),
                         sorted(["ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY", *hosts.OLLAMA_MODEL_VARS]))
        self.assertEqual((env["ANTHROPIC_BASE_URL"], env["ANTHROPIC_API_KEY"]), (hosts.OLLAMA_URL, "ollama"))
        self.assertEqual({env[name] for name in hosts.OLLAMA_MODEL_VARS}, {hosts.OLLAMA_MODEL})
        self.assertEqual(os.environ.get("ANTHROPIC_AUTH_TOKEN"), None, "the harness's own environment is left as it was")

    def test_only_the_coding_tools_reach_the_child_and_no_connector(self):
        self.ollama()
        argv = json.loads(self.log.read_text())["argv"]
        self.assertEqual(argv[argv.index("--tools") + 1].split(","), list(hosts.OLLAMA_TOOLS))
        self.assertIn("--strict-mcp-config", argv)
        self.assertEqual(argv[argv.index("--model") + 1], hosts.OLLAMA_MODEL)
        for orchestration in ("SendMessage", "CronCreate", "Monitor", "Workflow", "ToolSearch"):
            self.assertNotIn(orchestration, argv[argv.index("--tools") + 1])

    def test_the_backend_is_recorded_and_cost_is_not_measured(self):
        _, out, printed = self.ollama()
        result, invocation = (json.loads((out / name).read_text()) for name in ("result.json", "invocation.json"))
        self.assertEqual((result["backend"], invocation["backend"], result["model"]), ("ollama", "ollama", hosts.OLLAMA_MODEL))
        self.assertIsNone(result["metrics"]["cost_usd"])
        self.assertEqual(result["metrics"]["unmeasured"]["cost_usd"], metrics.OLLAMA_COST)
        self.assertIn(f"host=claude backend=ollama model={hosts.OLLAMA_MODEL}", printed)
        done = next(line for line in printed.splitlines() if "] done  " in line)
        self.assertIn("cost=not measured (Ollama)", done, "the live line shows no Anthropic-priced figure")
        card = scorecard.score(out)
        self.assertEqual(card["driver"], {"host": "claude", "backend": "ollama", "model": hosts.OLLAMA_MODEL, "effort": None})
        self.assertEqual(card["unmeasured"]["efficiency.cost_usd"], metrics.OLLAMA_COST)

    def test_a_run_is_refused_before_any_model_starts_when_ollama_is_not_ready(self):
        with self.assertRaises(SystemExit) as refused:
            self.ollama(ready="the Ollama server at http://127.0.0.1:11434 does not answer (refused)")
        self.assertIn("--backend ollama: the Ollama server", str(refused.exception))
        self.assertFalse((self.tmp / "child-env.txt").exists(), "no host started")
        with self.assertRaises(SystemExit) as budget:
            self.ollama("--max-budget-usd", "5")
        self.assertIn("prices the tokens at Anthropic's rates", str(budget.exception))

    def test_the_backend_is_a_claude_option_and_the_anthropic_route_is_unchanged(self):
        with self.assertRaises(SystemExit):
            hosts.host("grok", None, "ollama")
        with mock.patch.dict(os.environ, self.SECRETS):
            anthropic = hosts.host("claude")
            self.assertEqual(anthropic.env(self.tmp / "home")["ANTHROPIC_AUTH_TOKEN"], "real-oauth-bearer",
                             "the Anthropic route still authenticates as the user, as every Claude run has")
        argv = anthropic.argv(prompt="p", prompt_file=self.tmp / "p.txt", cwd=self.tmp, model="m", effort=None,
                              permission_mode="bypassPermissions", max_turns=None)
        self.assertNotIn("--tools", argv)

    def test_a_resume_keeps_its_runs_backend_and_refuses_another(self):
        args = argparse.Namespace(backend=None)
        self.assertEqual(run.resume_backend(args, {"host": "claude", "backend": "ollama"}), "ollama")
        self.assertEqual(run.resume_backend(args, {"host": "claude"}), "anthropic", "a launch from before the field")
        self.assertIsNone(run.resume_backend(args, {"host": "grok"}))
        with self.assertRaises(SystemExit) as mixed:
            run.resume_backend(argparse.Namespace(backend="anthropic"), {"host": "claude", "backend": "ollama"})
        self.assertIn("mixed-backend run", str(mixed.exception))

    def test_ollama_ready_reads_the_servers_tags(self):
        class Tags(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802 - the stdlib's name
                body = json.dumps({"models": [{"name": hosts.OLLAMA_MODEL}]}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass
        server = http.server.HTTPServer(("127.0.0.1", 0), Tags)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        url = f"http://127.0.0.1:{server.server_address[1]}"
        self.assertIsNone(hosts.ollama_ready(hosts.OLLAMA_MODEL, url))
        self.assertIn("does not list other:cloud (it lists 1 models)", hosts.ollama_ready("other:cloud", url))
        server.shutdown()
        server.server_close()
        self.assertIn("does not answer", hosts.ollama_ready(hosts.OLLAMA_MODEL, url, timeout=1))

    def test_a_run_another_model_served_is_not_attributable_to_its_driver(self):
        _, out, _ = self.ollama()
        metrics_path = out / "metrics.json"
        recorded = json.loads(metrics_path.read_text())
        for served, valid, why in (([hosts.OLLAMA_MODEL], None, None), (["claude-haiku-5-5"], False, "served by another model"),
                                   (None, None, "no result event names the model")):
            with self.subTest(served=served):
                metrics_path.write_text(json.dumps({**recorded, "models_served": served}))
                attribution = scorecard.score(out)["validity"]["attribution"]
                if valid is False:
                    self.assertIs(attribution["valid"], False)
                if why:
                    self.assertTrue(any(why in text for text in attribution["why"]), attribution)
                else:
                    self.assertFalse(any("served" in text or "names the model" in text for text in attribution["why"]))


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
                run.main(["--host", "codex", "--allow-host-change", "--codex-bin", str(self.fakes["codex"]), "--resume-run", str(out),
                          "--baseline", str(self.baselines)])
        self.assertEqual((out / "result.json").read_text(), before)

    def test_a_resumed_run_keeps_the_termination_each_earlier_invocation_recorded(self):
        out = self.stopped_run()
        original = json.loads((out / "result.json").read_text())["termination"]
        os.environ["FAKE_MODE"] = "done"
        with contextlib.redirect_stdout(io.StringIO()):
            run.main(["--host", "codex", "--allow-host-change", "--codex-bin", str(self.fakes["codex"]), "--resume-run", str(out),
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
            run.main(["--host", host, *ANTHROPIC_ROUTE.get(host, ()), f"--{host}-bin", str(self.fakes[host]), "--resume-run", str(out),
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
            run.main(["--host", host, *ANTHROPIC_ROUTE.get(host, ()), f"--{host}-bin", str(self.fakes[host]), "--resume-run", str(out),
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
        self.resume(Path(first["output"]), "codex", other, "--allow-host-change")
        prompt = self.seen()["prompt"]
        self.assertIn(f'python3 "{self.cli}" next --run-dir "', prompt)  # the first host's install, not the new one
        self.assertNotIn(str(other_cli), prompt)


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


class ResumeCommandTest(PrintedCase):
    """The harness prints the exact command that continues the run, before any host spend and again when it is left active.

    invocation.json keeps the host argv but not the harness flags, so a command with only --resume-run would drop the
    run's limits: there is no default --timeout, so it could outlive the task that launched it."""

    def test_no_limit_is_set_unless_one_is_asked_for_and_the_printed_command_names_none(self):
        """Owner 2026-10-24: no turn, spend, time or resume limit by default. The three drivers share the defaults, the
        host argv carries no --max-turns or --max-budget-usd, and the printed command adds none and still round-trips."""
        args = run.parser().parse_args(["--host", "grok", "--model", "m"])
        self.assertEqual((args.max_turns, args.max_budget_usd, args.timeout, args.max_resumes), (None, None, None, None))
        import slice as slice_driver  # the slice driver beside run.py (not the builtin)
        sliced = slice_driver.parser().parse_args([])
        self.assertEqual((sliced.max_turns, sliced.max_budget_usd, sliced.timeout, sliced.max_resumes),
                         (None, None, None, None))
        words = shlex.split(run.resume_command(Path("/o/run"), args))
        for flag in ("--timeout", "--max-resumes", "--max-budget-usd"):
            self.assertNotIn(flag, words)
        again = run.parser().parse_args(words[2:])
        again.resume_run = None
        self.assertEqual(vars(again), vars(args))
        common = dict(prompt="p", cwd=Path("/w"), model="m", effort=None, permission_mode="auto", max_turns=None,
                      max_budget_usd=None)
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("grok", "claude"):
                with self.subTest(host=name):
                    argv = hosts.HOSTS[name]().argv(prompt_file=Path(tmp) / "prompt.txt", **common)
                    self.assertNotIn("--max-turns", argv)
                    self.assertNotIn("--max-budget-usd", argv)

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

    def test_the_printed_command_round_trips_for_a_marketplace_a_checkout_and_a_plugin_dir_run(self):
        """U27: the line is complete for each way a run starts. It parses with the harness's own parser to the arguments the run had
        (`--source checkout` too, which a checkout build the harness made itself has no `--plugin-dir` to imply)."""
        flags = ["--host", "grok", "--model", "m", "--effort", "high", "--timeout", "900", "--max-resumes", "3",
                 "--max-budget-usd", "12.5", "--permission-mode", "bypassPermissions"]
        for kind, extra in (("marketplace", []), ("checkout", ["--source", "checkout"]),
                            ("plugin-dir", ["--plugin-dir", str(self.plugin)]),
                            ("checkout and keep", ["--source", "checkout", "--keep-platform"])):
            with self.subTest(kind=kind):
                args = run.parser().parse_args([*flags, *extra])
                if args.plugin_dir:
                    args.source = "checkout"  # what main does before it prints the line
                printed = run.resume_command(Path("/o/run"), args)
                words = shlex.split(printed)
                self.assertEqual("--source" in words, kind != "marketplace", "a marketplace run is the default and says nothing")
                again = run.parser().parse_args(words[2:])
                self.assertEqual(again.resume_run, Path("/o/run"))
                again.resume_run = None
                self.assertEqual(vars(again), vars(args), "the printed line parses to the arguments the run had, nothing defaulted")
                self.assertEqual(again.source, "marketplace" if kind == "marketplace" else "checkout")

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


if __name__ == "__main__":
    unittest.main()
