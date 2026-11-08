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
        self.assertEqual(hosts.RUN_DEFAULT_HOST, "codex")
        expected = {
            "subject": {"host": "codex", "model": "gpt-6.1-sol", "effort": "high"},
            "reviewer": {"host": "codex", "model": "gpt-6.1-sol", "effort": "high"},
            "judge": {"host": "codex", "model": "gpt-6.1-sol", "effort": "high"},
            "improver": {"host": "codex", "model": "gpt-6.1-sol", "effort": "high"},
        }
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
        self.assertEqual(run.parser().parse_args([]).host, "codex")
        self.assertEqual(step_slice.parser().parse_args([]).host, "codex")
        run_override = run.parser().parse_args(["--host", "claude", "--model", "sonnet-override", "--effort", "high"])
        self.assertEqual((run_override.host, run_override.model, run_override.effort),
                         ("claude", "sonnet-override", "high"))
        overridden = step_slice.parser().parse_args(["--host", "grok", "--model", "grok-override", "--effort", "medium"])
        self.assertEqual((overridden.host, overridden.model, overridden.effort),
                         ("grok", "grok-override", "medium"))

        for args, expected in ((["run", "E1", "--arm", "A"], "codex"),
                               (["run", "E1", "--arm", "A", "--host", "claude"], "claude")):
            with self.subTest(args=args), mock.patch.object(experiment, "run", return_value=0) as launch, \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(experiment.main(args), 0)
            self.assertEqual(launch.call_args.args[3], expected)

    def test_codex_run_defaults_reach_the_real_argv_builder(self):
        args = run.parser().parse_args([])
        args.codex_bin = "fake-codex"
        selected = run.the_host(args)
        self.assertEqual((selected.name, selected.model, selected.effort),
                         ("codex", "gpt-6.1-sol", "high"))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            argv = selected.argv(prompt="hello", prompt_file=root / "prompt.txt", cwd=root,
                                 model=args.model or selected.model, effort=args.effort or selected.effort,
                                 permission_mode=args.permission_mode, max_turns=args.max_turns)
        self.assertEqual(argv[0:2], ["fake-codex", "exec"])
        self.assertEqual(argv[argv.index("-m") + 1], "gpt-6.1-sol")
        self.assertIn('model_reasoning_effort=high', argv)

    def test_explicit_claude_routes_and_recorded_resume_identity_survive_new_defaults(self):
        default_claude = run.the_host(run.parser().parse_args(["--host", "claude"]))
        anthropic_claude = run.the_host(run.parser().parse_args(["--host", "claude", "--backend", "anthropic"]))
        ollama_claude = run.the_host(run.parser().parse_args(["--host", "claude", "--backend", "ollama"]))
        self.assertEqual((default_claude.backend, default_claude.model), ("anthropic", "claude-sonnet-5-5"))
        self.assertEqual((anthropic_claude.backend, anthropic_claude.model), ("anthropic", "claude-sonnet-5-5"))
        self.assertEqual((ollama_claude.backend, ollama_claude.model), ("ollama", hosts.OLLAMA_MODEL))

        argv = ["--resume-run", "/recorded/run"]
        args = run.parser().parse_args(argv)
        self.assertEqual(args.host, "codex", "argparse's new-run default is not an explicit resume choice")
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
        self.assertEqual((driver.name, driver.model, driver.effort), ("codex", "gpt-6.1-sol", "high"))
        for parser in (run.parser(), step_slice.parser()):
            help_text = parser.format_help()
            self.assertIn("gpt-6.1-sol", help_text)
            self.assertNotIn("gpt-6.1-terra", help_text)

    def test_role_specific_overrides_stay_distinct_from_the_subject(self):
        args = argparse.Namespace(host="codex", model="subject-only", effort="low")
        for role in ("reviewer", "judge", "improver"):
            self.assertEqual(iterate.role_profile(args, role), hosts.ROLE_DEFAULTS[role])
            setattr(args, role + "_model", role + "-model")
            setattr(args, role + "_effort", role + "-effort")
        for role in ("reviewer", "judge", "improver"):
            self.assertEqual(iterate.role_profile(args, role),
                             {"host": "codex", "model": role + "-model", "effort": role + "-effort"})
        self.assertEqual(hosts.resolve_role("judge", {"model": "gpt-6-astra", "effort": "high"}),
                         {"host": "codex", "model": "gpt-6-astra", "effort": "high"})
        self.assertEqual(hosts.ROLE_DEFAULTS["judge"]["model"], "gpt-6.1-sol")

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
