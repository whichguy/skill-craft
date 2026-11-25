#!/usr/bin/env python3
"""ShipLoop harness-to-model routing: stage profiles, selector resolution, host flags, and boundaries."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import shiploop_model_routing as routing  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402


class StageProfileTests(unittest.TestCase):
    def test_every_stage_and_improve_map_to_a_profile(self) -> None:
        self.assertIsNone(stage_spec.stage_profile(None))
        self.assertIsNone(stage_spec.stage_profile(""))
        self.assertEqual(stage_spec.stage_profile("improve"), "planning")
        for name in stage_spec.STAGES:
            profile = stage_spec.stage_profile(name)
            self.assertIn(profile, stage_spec.ACTIVITY_PROFILES, name)
        for name in ("intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare",
                     "step-plan", "test-spec", "reflect-and-revise",
                     "system-test-author", "product-acceptance", "release-plan", "handoff"):
            self.assertEqual(stage_spec.stage_profile(name), "planning", name)
        for name in ("validate-existing", "implement", "test", "document",
                     "system-test", "release-check", "release", "release-verify", "operations"):
            self.assertEqual(stage_spec.stage_profile(name), "execution", name)
        with self.assertRaises(ValueError):
            stage_spec.stage_profile("unknown-stage")


class ModelRoutingResolutionTests(unittest.TestCase):
    def test_flat_and_harness_keyed_resolution(self) -> None:
        cfg = routing.load_config({
            "planning": {
                "agy": {"model": "gemini-4-neon-high"},
                "codex": {"model": "gpt-6.2-astra", "effort": "high"},
                "default": {"model": "opus", "effort": "high"},
            },
            "execution": {
                "antigravity": "gemini-4-carbon-medium",
                "codex": {"model": "gpt-6.2-sol", "effort": "low"},
            },
            "review": {"model": "review-model", "effort": "max"},
            "stages": {"handoff": {"host": "codex", "model": "gpt-6.2-sol", "effort": "medium"}},
        })
        agy_plan = routing.resolve(cfg, "plan", "agy")
        self.assertEqual((agy_plan.host, agy_plan.model, agy_plan.profile),
                         ("antigravity", "gemini-4-neon-high", "planning"))
        agy_exec = routing.resolve(cfg, "implement", "antigravity")
        self.assertEqual((agy_exec.host, agy_exec.model, agy_exec.profile),
                         ("antigravity", "gemini-4-carbon-medium", "execution"))
        codex_plan = routing.resolve(cfg, "spec", "codex")
        self.assertEqual((codex_plan.host, codex_plan.model, codex_plan.effort),
                         ("codex", "gpt-6.2-astra", "high"))
        # Fallback to "default" when harness is absent in planning, and inherit when absent in execution.
        claude_plan = routing.resolve(cfg, "plan", "claude")
        self.assertEqual((claude_plan.model, claude_plan.effort), ("opus", "high"))
        claude_exec = routing.resolve(cfg, "implement", "claude")
        self.assertEqual((claude_exec.host, claude_exec.model, claude_exec.effort), ("claude", None, None))
        # Flat review bucket applies to any host on improve; per-stage host override switches host.
        self.assertEqual(routing.resolve(cfg, "improve", "codex").model, "review-model")
        handoff = routing.resolve(cfg, "handoff", "antigravity")
        self.assertEqual((handoff.host, handoff.model, handoff.effort), ("codex", "gpt-6.2-sol", "medium"))

    def test_flat_config_applies_to_any_harness(self) -> None:
        cfg = routing.load_config(json.dumps({
            "planning": "planner-model",
            "execution": {"model": "exec-model", "effort": "low", "args": ["--fast"]},
            "resume": "fresh",
        }))
        for host in ("antigravity", "codex", "claude"):
            p = routing.resolve(cfg, "plan", host)
            e = routing.resolve(cfg, "implement", host)
            self.assertEqual((p.host, p.model, p.resume), (host, "planner-model", "fresh"))
            self.assertEqual((e.host, e.model, e.effort, e.args, e.resume),
                             (host, "exec-model", "low", ("--fast",), "fresh"))

    def test_host_model_args_avoids_agy_suffix_conflict(self) -> None:
        suffixed = routing.RouteTarget(host="antigravity", profile="planning",
                                       model="gemini-4-neon-high", effort="high")
        self.assertEqual(routing.host_model_args("antigravity", suffixed), ["--model", "gemini-4-neon-high"])
        base = routing.RouteTarget(host="antigravity", profile="planning",
                                   model="gemini-4-argon", effort="high", args=("--sandbox",))
        self.assertEqual(routing.host_model_args("antigravity", base),
                         ["--model", "gemini-4-argon", "--effort", "high", "--sandbox"])
        codex_t = routing.RouteTarget(host="codex", profile="execution", model="gpt-6.2-sol", effort="low")
        self.assertEqual(routing.host_model_args("codex", codex_t),
                         ["-m", "gpt-6.2-sol", "-c", "model_reasoning_effort=low"])
        claude_t = routing.RouteTarget(host="claude", profile="planning", model="opus", effort="high")
        self.assertEqual(routing.host_model_args("claude", claude_t), ["--model", "opus", "--effort", "high"])
        grok_t = routing.RouteTarget(host="grok", profile="planning", model="grok-4.7", effort="high")
        self.assertEqual(routing.host_model_args("grok", grok_t),
                         ["--model", "grok-4.7", "--reasoning-effort", "high"])

    def test_invalid_configs_are_refused(self) -> None:
        for bad in (
            {"unknown": {}},
            {"planning": 123},
            {"planning": {"unknown_host": "x"}},
            {"planning": {"agy": "a", "antigravity": "b"}},
            {"stages": {"nope": "m"}},
            {"resume": "invalid"},
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                routing.load_config(bad)

    def test_active_boundary_and_fail_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "routing.json"
            cfg = routing.load_config({
                "planning": {"antigravity": "gemini-4-neon-high"},
                "execution": {"antigravity": "gemini-4-carbon-medium"},
            })
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            plan_t = routing.resolve(cfg, "plan", "antigravity")
            env = {
                "SHIPLOOP_DRIVE_ROUTING": str(cfg_path),
                "SHIPLOOP_DRIVE_HOST": "antigravity",
                "SHIPLOOP_DRIVE_TARGET": plan_t.target_key,
                "SHIPLOOP_DRIVE_LABEL": plan_t.label,
                "SHIPLOOP_DRIVE_RUN_ID": "run-1",
            }
            self.assertIsNone(routing.active_boundary("spec", "run-1", env))
            boundary = routing.active_boundary("implement", "run-1", env)
            self.assertIsNotNone(boundary)
            self.assertEqual(boundary["stage"], "implement")
            self.assertEqual(boundary["profile"], "execution")
            self.assertIn("gemini-4-carbon-medium", boundary["to_label"])
            # Mismatched run id or missing/invalid routing file fails open (None).
            self.assertIsNone(routing.active_boundary("implement", "other-run", env))
            self.assertIsNone(routing.active_boundary("implement", "run-1", {**env, "SHIPLOOP_DRIVE_ROUTING": "/nonexistent"}))


if __name__ == "__main__":
    unittest.main()
