"""No-model checks for ShipLoop E2E role and new-run defaults."""

from __future__ import annotations

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
import run
import slice as step_slice


class RoleDefaultsTest(unittest.TestCase):
    def test_role_profiles_and_independent_overrides(self):
        self.assertEqual(hosts.RUN_DEFAULT_HOST, "codex")
        expected = {
            "subject": {"host": "codex", "model": "gpt-6.1-terra", "effort": "xhigh"},
            "reviewer": {"host": "codex", "model": "gpt-6-astra", "effort": "xhigh"},
            "judge": {"host": "codex", "model": "gpt-6-astra", "effort": "xhigh"},
            "improver": {"host": "codex", "model": "gpt-6.1-sol", "effort": "xhigh"},
        }
        self.assertEqual(hosts.ROLE_DEFAULTS, expected)
        self.assertEqual(hosts.resolve_role("reviewer", {"model": "custom-model", "effort": "high"}),
                         {"host": "codex", "model": "custom-model", "effort": "high"})
        self.assertEqual(hosts.resolve_role("subject", {"host": "claude"}),
                         {"host": "claude", "model": hosts.OLLAMA_MODEL, "effort": None})
        self.assertEqual(hosts.resolve_role("reviewer", {"host": "claude"}),
                         {"host": "claude", "model": "claude-sonnet-5-5", "effort": None})
        self.assertEqual(hosts.resolve_role("subject", {"host": "claude", "model": "sonnet-override", "effort": "high"}),
                         {"host": "claude", "model": "sonnet-override", "effort": "high"})
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
                         ("codex", "gpt-6.1-terra", "xhigh"))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            argv = selected.argv(prompt="hello", prompt_file=root / "prompt.txt", cwd=root,
                                 model=args.model or selected.model, effort=args.effort or selected.effort,
                                 permission_mode=args.permission_mode, max_turns=args.max_turns)
        self.assertEqual(argv[0:2], ["fake-codex", "exec"])
        self.assertEqual(argv[argv.index("-m") + 1], "gpt-6.1-terra")
        self.assertIn('model_reasoning_effort=xhigh', argv)

    def test_explicit_claude_routes_and_recorded_resume_identity_survive_new_defaults(self):
        default_claude = run.the_host(run.parser().parse_args(["--host", "claude"]))
        anthropic_claude = run.the_host(run.parser().parse_args(["--host", "claude", "--backend", "anthropic"]))
        self.assertEqual((default_claude.backend, default_claude.model), ("ollama", hosts.OLLAMA_MODEL))
        self.assertEqual((anthropic_claude.backend, anthropic_claude.model), ("anthropic", "claude-sonnet-5-5"))

        argv = ["--resume-run", "/recorded/run"]
        args = run.parser().parse_args(argv)
        self.assertEqual(args.host, "codex", "argparse's new-run default is not an explicit resume choice")
        self.assertFalse(run.host_given(argv))
        self.assertEqual(run.resume_identity(args, False,
                                             {"host": "claude", "model": "claude-sonnet-5-5", "effort": None},
                                             Path("/not-used")),
                         ("claude", "claude-sonnet-5-5", None))


if __name__ == "__main__":
    unittest.main()
