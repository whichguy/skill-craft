"""No-model checks for ShipLoop E2E role and new-run defaults."""

from __future__ import annotations

import argparse
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import experiment
import hosts
import iterate
import run
import slice as step_slice


class RoleDefaultsTest(unittest.TestCase):
    def test_role_profiles_and_independent_overrides(self):
        self.assertEqual(hosts.RUN_DEFAULT_HOST, "grok")
        expected = {
            "subject": {"host": "grok", "model": "grok-4.6", "effort": "xhigh"},
            "reviewer": {"host": "codex", "model": "gpt-6-astra", "effort": "high"},
            "judge": {"host": "codex", "model": "gpt-6-astra", "effort": "high"},
            "improver": {"host": "codex", "model": "gpt-6.1-sol", "effort": "medium"},
        }
        self.assertEqual(hosts.ROLE_DEFAULTS, expected)
        for role, profile in expected.items():
            with self.subTest(role=role):
                self.assertEqual(hosts.resolve_role(role), profile)
        self.assertEqual(hosts.resolve_role("reviewer", {"model": "custom-model", "effort": "xhigh"}),
                         {"host": "codex", "model": "custom-model", "effort": "xhigh"})
        self.assertEqual(hosts.resolve_role("subject", {"host": "claude"}),
                         {"host": "claude", "model": "claude-sonnet-5-5", "effort": None})
        self.assertEqual(hosts.resolve_role("reviewer", {"host": "claude"}),
                         {"host": "claude", "model": "claude-sonnet-5-5", "effort": None})
        self.assertEqual(hosts.resolve_role("subject", {"host": "claude", "model": "sonnet-override", "effort": "high"}),
                         {"host": "claude", "model": "sonnet-override", "effort": "high"})
        self.assertEqual(expected["subject"], {"host": hosts.RUN_DEFAULT_HOST, **hosts.HOST_DEFAULTS[hosts.RUN_DEFAULT_HOST]})
        self.assertEqual(hosts.ROLE_DEFAULTS, expected, "resolving overrides must not mutate shared defaults")
        with self.assertRaisesRegex(ValueError, "unknown ShipLoop E2E role"):
            hosts.resolve_role("unknown")

    def test_run_slice_and_experiment_parser_defaults_and_overrides(self):
        self.assertEqual(run.parser().parse_args([]).host, "grok")
        self.assertEqual(step_slice.parser().parse_args([]).host, "grok")
        run_override = run.parser().parse_args(["--host", "claude", "--model", "sonnet-override", "--effort", "high"])
        self.assertEqual((run_override.host, run_override.model, run_override.effort),
                         ("claude", "sonnet-override", "high"))
        overridden = step_slice.parser().parse_args(["--host", "grok", "--model", "grok-override", "--effort", "medium"])
        self.assertEqual((overridden.host, overridden.model, overridden.effort),
                         ("grok", "grok-override", "medium"))

        for args, expected in ((["run", "E1", "--arm", "A"], "grok"),
                               (["run", "E1", "--arm", "A", "--host", "claude"], "claude")):
            with self.subTest(args=args), mock.patch.object(experiment, "run", return_value=0) as launch, \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(experiment.main(args), 0)
            self.assertEqual(launch.call_args.args[3], expected)

    def test_grok_driver_defaults_reach_the_real_argv_builder(self):
        args = run.parser().parse_args([])
        args.grok_bin = "fake-grok"
        selected = run.the_host(args)
        self.assertEqual((selected.name, selected.model, selected.effort),
                         ("grok", "grok-4.6", "xhigh"))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            argv = selected.argv(prompt="hello", prompt_file=root / "prompt.txt", cwd=root,
                                 model=args.model or selected.model, effort=args.effort or selected.effort,
                                 permission_mode=args.permission_mode, max_turns=args.max_turns)
        self.assertEqual(argv[0], "fake-grok")
        self.assertEqual(argv[argv.index("--model") + 1], "grok-4.6")
        self.assertEqual(argv[argv.index("--reasoning-effort") + 1], "xhigh")

    def test_codex_run_defaults_reach_the_real_argv_builder(self):
        args = run.parser().parse_args(["--host", "codex"])
        args.codex_bin = "fake-codex"
        selected = run.the_host(args)
        self.assertEqual((selected.name, selected.model, selected.effort),
                         ("codex", "gpt-6.1-sol", "medium"))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            argv = selected.argv(prompt="hello", prompt_file=root / "prompt.txt", cwd=root,
                                 model=args.model or selected.model, effort=args.effort or selected.effort,
                                 permission_mode=args.permission_mode, max_turns=args.max_turns)
        self.assertEqual(argv[0:2], ["fake-codex", "exec"])
        self.assertEqual(argv[argv.index("-m") + 1], "gpt-6.1-sol")
        self.assertIn("model_reasoning_effort=medium", argv)
        self.assertIn('agents.default_subagent_model="gpt-6.1-sol"', argv)
        self.assertIn("agents.default_subagent_reasoning_effort=medium", argv)

    def test_improver_default_and_explicit_high_reach_codex_argv(self):
        agent = hosts.CodexHost("fake-codex")
        args = argparse.Namespace(case="hello", host="codex", model="subject-only", effort="low",
                                  permission_mode="auto", improve_max_turns=None, max_budget_usd=None,
                                  improve_timeout=30)

        def finish(_argv, _cwd, _env, events_path, _stderr, _timeout, **_kwargs):
            events_path.touch()
            return {"status": "exited", "returncode": 0}

        with tempfile.TemporaryDirectory() as folder, \
                mock.patch.object(agent, "env", return_value={}), \
                mock.patch.object(hosts, "host", return_value=agent), \
                mock.patch.object(hosts, "run_agent", side_effect=finish) as launch, \
                mock.patch.object(iterate, "git", side_effect=["base", "", "", "base", "", ""]):
            root = Path(folder)
            for override, effort in ((None, "medium"), ("high", "high")):
                with self.subTest(override=override):
                    args.improver_effort = override
                    iterate.improve(root, [], root / effort, args, prompt="Improve this fixture.")
                    argv = launch.call_args.args[0]
                    self.assertEqual(argv[argv.index("-m") + 1], "gpt-6.1-sol")
                    self.assertIn(f"model_reasoning_effort={effort}", argv)
                    self.assertIn('agents.default_subagent_model="gpt-6.1-sol"', argv)
                    self.assertIn(f"agents.default_subagent_reasoning_effort={effort}", argv)

    def test_codex_resume_sets_child_defaults_from_the_saved_or_overridden_identity(self):
        resume = ["--resume-run", "/recorded/run"]
        examples = (
            ("gpt-6.1-terra", "xhigh", [], "gpt-6.1-terra", "xhigh"),
            ("gpt-6.1-sol", "high", [], "gpt-6.1-sol", "high"),
            ("gpt-6.1-terra", "xhigh", ["--model", "gpt-6-astra", "--effort", "medium"], "gpt-6-astra", "medium"),
        )
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for model, effort, overrides, expected_model, expected_effort in examples:
                with self.subTest(model=model, effort=effort, overrides=overrides):
                    recorded = {"host": "codex", "model": model, "effort": effort}
                    flags = [*resume, *overrides]
                    args = run.parser().parse_args(flags)
                    args.host, args.model, args.effort = run.resume_identity(args, run.host_given(flags), recorded, root)
                    args.codex_bin = "fake-codex"
                    selected = run.the_host(args)
                    argv = selected.argv(prompt="continue", prompt_file=root / "prompt.txt", cwd=root,
                                         model=args.model or selected.model, effort=args.effort or selected.effort,
                                         permission_mode=args.permission_mode, max_turns=args.max_turns, resume="thread-1")
                    self.assertEqual(argv[-3:], ["resume", "thread-1", "continue"])
                    options = argv[:argv.index("resume")]
                    self.assertEqual(options[options.index("-m") + 1], expected_model)
                    self.assertIn(f"model_reasoning_effort={expected_effort}", options)
                    self.assertIn(f'agents.default_subagent_model="{expected_model}"', options)
                    self.assertIn(f"agents.default_subagent_reasoning_effort={expected_effort}", options)

    def test_explicit_claude_routes_and_recorded_resume_identity_survive_new_defaults(self):
        default_claude = run.the_host(run.parser().parse_args(["--host", "claude"]))
        anthropic_claude = run.the_host(run.parser().parse_args(["--host", "claude", "--backend", "anthropic"]))
        ollama_claude = run.the_host(run.parser().parse_args(["--host", "claude", "--backend", "ollama"]))
        self.assertEqual((default_claude.backend, default_claude.model), ("anthropic", "claude-sonnet-5-5"))
        self.assertEqual((anthropic_claude.backend, anthropic_claude.model), ("anthropic", "claude-sonnet-5-5"))
        self.assertEqual((ollama_claude.backend, ollama_claude.model), ("ollama", hosts.OLLAMA_MODEL))

        argv = ["--resume-run", "/recorded/run"]
        args = run.parser().parse_args(argv)
        self.assertEqual(args.host, hosts.RUN_DEFAULT_HOST,
                         "argparse's new-run default is not an explicit resume choice")
        self.assertFalse(run.host_given(argv))
        for host, model, effort in (("claude", "claude-sonnet-5-5", None),
                                    ("codex", "gpt-6.1-terra", "xhigh")):
            with self.subTest(host=host):
                recorded = {"host": host, "model": model, "effort": effort}
                self.assertEqual(run.resume_identity(args, False, recorded, Path("/not-used")),
                                 (host, model, effort))


    def test_packet_driver_and_help_match_the_new_subject(self):
        sys.path.insert(0, str(ROOT / "test/shiploop_e2e/stage_suite"))
        import stages
        args = stages._parser()[0].parse_args(["live", "--dry-run"])
        driver = stages.resolve_driver(args)
        self.assertEqual((driver.name, driver.model, driver.effort), ("grok", "grok-4.6", "xhigh"))
        for parser in (run.parser(), step_slice.parser()):
            help_text = parser.format_help()
            self.assertIn("grok-4.6", help_text)
            self.assertNotIn("grok-4.7", help_text)
            self.assertIn("gpt-6.1-sol", help_text, "Codex stays a selectable host and its profile is still named")

    def test_role_specific_overrides_stay_distinct_from_the_subject(self):
        args = argparse.Namespace(host="codex", model="subject-only", effort="low")
        for role in ("reviewer", "judge", "improver"):
            self.assertEqual(iterate.role_profile(args, role), hosts.ROLE_DEFAULTS[role])
            setattr(args, role + "_model", role + "-model")
            setattr(args, role + "_effort", role + "-effort")
        for role in ("reviewer", "judge", "improver"):
            self.assertEqual(iterate.role_profile(args, role),
                             {"host": "codex", "model": role + "-model", "effort": role + "-effort"})
        self.assertEqual(hosts.resolve_role("judge", {"model": "gpt-6.1-sol", "effort": "high"}),
                         {"host": "codex", "model": "gpt-6.1-sol", "effort": "high"})
        self.assertEqual(hosts.ROLE_DEFAULTS["judge"]["model"], "gpt-6-astra")

    def test_old_codex_resume_launch_keeps_recorded_model_and_effort(self):
        recorded = {"host": "codex", "model": "gpt-6.1-terra", "effort": "xhigh"}
        for extra in ([], ["--host", "codex"]):
            args = run.parser().parse_args(["--resume-run", "/recorded/run", *extra])
            name, model, effort = run.resume_identity(args, bool(extra), recorded, Path("/not-used"))
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                argv = hosts.host(name).argv(prompt="continue", prompt_file=root / "prompt.txt", cwd=root,
                                            model=model, effort=effort, permission_mode="never", max_turns=None,
                                            resume="old-thread")
            self.assertEqual(argv[argv.index("-m") + 1], recorded["model"])
            self.assertIn("model_reasoning_effort=xhigh", argv)


if __name__ == "__main__":
    unittest.main()
