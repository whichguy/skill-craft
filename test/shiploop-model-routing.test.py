#!/usr/bin/env python3
"""ShipLoop harness-to-model routing: stage profiles, selector resolution, host flags, and boundaries."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(ROOT / "test"))
import state_home  # noqa: E402

state_home.isolate()

sys.path.insert(0, str(SCRIPTS))

import shiploop_model_routing as routing  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402
import shiploop_store as store  # noqa: E402


class StageProfileTests(unittest.TestCase):
    def test_every_stage_and_improve_map_to_a_profile(self) -> None:
        self.assertIsNone(stage_spec.stage_profile(None))
        self.assertIsNone(stage_spec.stage_profile(""))
        self.assertIsNone(stage_spec.stage_profile("done"))
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
        self.assertIsNone(routing.resolve(cfg, "done", "antigravity"))

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


def _load_smoke_probe():
    path = ROOT / "test" / "shiploop_e2e" / "probes" / "model_routing_smoke.py"
    spec = importlib.util.spec_from_file_location("shiploop_model_routing_smoke_probe", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ModelRoutingSmokeGraderAndStagingTests(unittest.TestCase):
    """Hermetic 3-host smoke grader and staging checks (Claude, Codex, Antigravity) for `--group smoke`."""

    _SPECS = {
        "claude": {
            "planning": ("sonnet", "high", "claude-sonnet-5-5"),
            "execution": ("haiku", "low", "claude-haiku-5-5"),
        },
        "codex": {
            "planning": ("gpt-6.2-astra", "high", "gpt-6.2-astra"),
            "execution": ("gpt-6.2-sol", "medium", "gpt-6.2-sol"),
        },
        "antigravity": {
            "planning": ("gemini-4-neon-high", "high", "gemini-4-neon-high"),
            "execution": ("gemini-4-carbon-medium", "medium", "gemini-4-carbon-medium"),
        },
    }

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory(prefix="shiploop-routing-matrix-")
        self.addCleanup(tmp.cleanup)
        self.temp = Path(tmp.name).resolve()
        self.probe = _load_smoke_probe()

    @staticmethod
    def _write_synthetic_artifacts(
        base: Path,
        *,
        host: str,
        spec: dict[str, tuple[str, str, str]],
        stages: list[str],
        include_resume: bool = True,
        include_boundaries: bool = True,
        routed: bool = True,
    ) -> tuple[Path, Path]:
        run_dir = base / "run"
        drive_log = base / "drive.log"
        run_dir.mkdir(parents=True, exist_ok=True)
        store.write_record(run_dir / "state.md", {
            "run_id": f"nav-{host}",
            "status": "paused",
            "stage": "release-plan",
            "history": [
                {"stage": s, "outcome": "done", "summary": "ok", "workitem": None, "action": f"nav-{i}"}
                for i, s in enumerate(stages)
            ],
        })
        p_m, p_e, p_obs = spec["planning"]
        e_m, e_e, e_obs = spec["execution"]
        if routed:
            sid = f"{host}-thread-1"
            rows = [
                {"session": 1, "host": host, "resumed": None, "profile": "planning", "model": p_m, "effort": p_e},
                {"session": 2, "host": host, "resumed": sid if include_resume else None, "profile": "execution", "model": e_m, "effort": e_e},
                {"session": 3, "host": host, "resumed": sid if include_resume else None, "profile": "planning", "model": p_m, "effort": p_e},
            ]
            trace_rows = [
                {"kind": "hook", "hook": "model", "host": host, "model": p_obs, "effort": p_e, "stage": "system-test-author", "profile": "planning"},
                *([{"kind": "hook", "hook": "stop", "host": host, "decision": "allow", "why": f"profile boundary reached ({host}:{p_m} -> {host}:{e_m} at system-test)"}] if include_boundaries else []),
                {"kind": "hook", "hook": "model", "host": host, "model": e_obs, "effort": e_e, "stage": "system-test", "profile": "execution"},
                *([{"kind": "hook", "hook": "stop", "host": host, "decision": "allow", "why": f"profile boundary reached ({host}:{e_m} -> {host}:{p_m} at product-acceptance)"}] if include_boundaries else []),
                {"kind": "hook", "hook": "model", "host": host, "model": p_obs, "effort": p_e, "stage": "product-acceptance", "profile": "planning"},
            ]
        else:
            rows = [{"session": 1, "host": host, "resumed": None, "exit": 0}]
            trace_rows = [{"kind": "hook", "hook": "model", "host": host, "model": e_obs, "effort": e_e, "stage": "system-test-author", "profile": "planning"}]
        drive_log.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        (run_dir / "trace.jsonl").write_text("\n".join(json.dumps(r) for r in trace_rows) + "\n", encoding="utf-8")
        return run_dir, drive_log

    def test_routed_grader_accepts_all_three_hosts_and_rejects_broken_runs(self) -> None:
        stages = ["system-test-author", "system-test", "product-acceptance"]
        for host, spec in self._SPECS.items():
            with self.subTest(host=host):
                run_dir, drive_log = self._write_synthetic_artifacts(
                    self.temp / f"{host}-ok", host=host, spec=spec, stages=stages,
                )
                ok = self.probe.grade_run(
                    host, run_dir, drive_log, mode="routed",
                    expected_planning=(spec["planning"][0], spec["planning"][1]),
                    expected_execution=(spec["execution"][0], spec["execution"][1]),
                )
                self.assertTrue(ok["pass"], ok)
                self.assertEqual(len(ok["boundary_stops"]), 2, ok)

        # Negative routed checks: unresumed sessions, missing boundaries, or flat unrouted run must fail.
        run_no_res, dl_no_res = self._write_synthetic_artifacts(
            self.temp / "claude-no-resume", host="claude", spec=self._SPECS["claude"], stages=stages, include_resume=False,
        )
        bad_res = self.probe.grade_run(
            "claude", run_no_res, dl_no_res, mode="routed",
            expected_planning=("sonnet", "high"), expected_execution=("haiku", "low"),
        )
        self.assertFalse(bad_res["pass"])
        self.assertFalse(bad_res["checks"]["warm_resume_ok"])

        run_unrouted, dl_unrouted = self._write_synthetic_artifacts(
            self.temp / "codex-unrouted", host="codex", spec=self._SPECS["codex"], stages=stages, routed=False,
        )
        ok_unrouted = self.probe.grade_run(
            "codex", run_unrouted, dl_unrouted, mode="unrouted",
            expected_planning=("gpt-6.2-sol", "medium"), expected_execution=("gpt-6.2-sol", "medium"),
        )
        self.assertTrue(ok_unrouted["pass"], ok_unrouted)

        bad_routed = self.probe.grade_run(
            "codex", run_unrouted, dl_unrouted, mode="routed",
            expected_planning=("gpt-6.2-astra", "high"), expected_execution=("gpt-6.2-sol", "medium"),
        )
        self.assertFalse(bad_routed["pass"])
        self.assertFalse(bad_routed["checks"]["warm_resume_ok"])
        self.assertFalse(bad_routed["checks"]["boundary_stops_ok"])
        self.assertFalse(bad_routed["checks"]["observed_models_ok"])

    def test_dry_run_staging_across_claude_codex_and_antigravity(self) -> None:
        pkg = self.probe._build_checkout_package(self.temp / "smoke-dry")
        product_dir, home_fix_dir = self.probe._write_smoke_materials(self.temp / "smoke-dry")
        orig_run = subprocess.run

        def fake_run(argv, **kwargs):
            if argv and argv[0] == "codex" and argv[1] == "plugin":
                codex_cache = Path(kwargs["env"]["CODEX_HOME"]) / "plugins" / "cache" / "whichguy" / "skill-craft" / "4.18.0"
                shutil.copytree(pkg / "plugins" / "skill-craft", codex_cache, dirs_exist_ok=True)
                return subprocess.CompletedProcess(argv, 0, "ok", "")
            return orig_run(argv, **kwargs)

        with mock.patch.object(self.probe.subprocess, "run", side_effect=fake_run):
            for host in ("claude", "codex", "antigravity"):
                p = self.probe.DEFAULT_ROUTES[host]["planning"]
                e = self.probe.DEFAULT_ROUTES[host]["execution"]
                staged = self.probe.stage_host(
                    host=host, mode="routed", out_dir=self.temp / "smoke-dry" / host,
                    pkg_dir=pkg, product_dir=product_dir, home_fix_dir=home_fix_dir,
                    source="checkout", planning=(p["model"], p["effort"]), execution=(e["model"], e["effort"]),
                    session_timeout=300, max_minutes=12,
                )
                self.assertEqual(store.read_record(Path(staged["run_dir"]) / "state.md")["stage"], "system-test-author")
                self.assertIn("--routing", staged["argv"])


if __name__ == "__main__":
    unittest.main()
