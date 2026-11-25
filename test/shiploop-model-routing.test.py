#!/usr/bin/env python3
"""ShipLoop harness-to-model routing: stage profiles, selector resolution, host flags, and boundaries."""

from __future__ import annotations

import importlib.util
import json
import os
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
        # Default prelude-only profile: prelude improves stay planning; inner/outer/unscoped improve stays execution.
        self.assertEqual(stage_spec.stage_profile("improve"), "execution")
        self.assertEqual(stage_spec.stage_profile("improve", reviewed_stage="spec"), "planning")
        self.assertEqual(stage_spec.stage_profile("improve", reviewed_stage="plan"), "planning")
        self.assertEqual(stage_spec.stage_profile("improve", reviewed_stage="document"), "execution")
        self.assertEqual(stage_spec.stage_profile("improve", reviewed_stage="system-test-author"), "execution")
        for name in stage_spec.STAGES:
            profile = stage_spec.stage_profile(name)
            self.assertIn(profile, stage_spec.ACTIVITY_PROFILES, name)
        for name in ("intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare"):
            self.assertEqual(stage_spec.stage_profile(name), "planning", name)
        for name in ("step-plan", "test-spec", "validate-existing", "implement", "test", "document",
                     "reflect-and-revise", "system-test-author", "system-test", "product-acceptance",
                     "release-plan", "release-check", "release", "release-verify", "operations", "handoff"):
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

    def test_default_routing_preset_and_extra_model_detection(self) -> None:
        cfg = routing.load_config("default")
        self.assertEqual(cfg, routing.default_routing())
        for host, exp_plan, exp_exec in (
            ("claude", ("claude-opus-5-5", "high"), ("claude-sonnet-5-5", "high")),
            ("codex", ("gpt-6.2-astra", "high"), ("gpt-6.2-sol", "xhigh")),
            ("antigravity", ("gemini-pro-orchestrator-neon", None), ("gemini-pro-orchestrator-neon", None)),
        ):
            p = routing.resolve(cfg, "plan", host)
            e = routing.resolve(cfg, "implement", host)
            self.assertEqual((p.model, p.effort), exp_plan, host)
            self.assertEqual((e.model, e.effort), exp_exec, host)
            self.assertEqual((p.resume, e.resume), ("fresh", "fresh"), host)
        # Antigravity Orchestrator maps both profiles to one target key -> no driver boundary stop.
        self.assertEqual(routing.resolve(cfg, "plan", "agy").target_key, routing.resolve(cfg, "implement", "agy").target_key)
        # Hosts without built-in defaults return None.
        for other in ("cursor", "opencode", "grok"):
            self.assertIsNone(routing.default_routing(other), other)
        # Pass-through CLI model detection.
        self.assertTrue(routing.extra_sets_model(["--model", "haiku"]))
        self.assertTrue(routing.extra_sets_model(["--model=haiku"]))
        self.assertTrue(routing.extra_sets_model(["-m", "gpt-6.2-sol"]))
        self.assertTrue(routing.extra_sets_model(["-c", "model=o3"]))
        self.assertTrue(routing.extra_sets_model(["--config=model=o3"]))
        self.assertFalse(routing.extra_sets_model(["--dangerously-skip-permissions", "-c", "model_reasoning_effort=high"]))

    def test_plan_reflect_and_improve_opt_in(self) -> None:
        default_cfg = routing.default_routing("codex")
        opt_cfg = routing.load_config({**default_cfg, "plan_reflect_and_improve": True})
        # By default (prelude-only), inner/outer stages + reflect + non-prelude improve stay execution.
        for stage_name, rev_stage in (
            ("step-plan", None),
            ("implement", None),
            ("reflect-and-revise", None),
            ("system-test-author", None),
            ("handoff", None),
            ("improve", "document"),
            ("improve", "system-test-author"),
        ):
            self.assertEqual(
                routing.resolve(default_cfg, stage_name, "codex", reviewed_stage=rev_stage).profile,
                "execution",
                (stage_name, rev_stage),
            )
            exp_prof = "planning" if stage_name in ("reflect-and-revise", "improve") else "execution"
            self.assertEqual(
                routing.resolve(opt_cfg, stage_name, "codex", reviewed_stage=rev_stage).profile,
                exp_prof,
                (stage_name, rev_stage),
            )
        # Prelude stages + prelude improve always stay planning.
        self.assertEqual(routing.resolve(default_cfg, "prepare", "codex").profile, "planning")
        self.assertEqual(routing.resolve(default_cfg, "improve", "codex", reviewed_stage="spec").profile, "planning")
        # from_cli_flags forwards plan_reflect_and_improve and invalid non-bool values fail.
        cli_cfg = routing.from_cli_flags(planning_model="gpt-6.2-astra", execution_model="gpt-6.2-sol", plan_reflect_and_improve=True)
        self.assertIs(cli_cfg["plan_reflect_and_improve"], True)
        with self.assertRaises(ValueError):
            routing.load_config({"planning": "m", "plan_reflect_and_improve": "yes"})


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
            "planning": ("claude-opus-5-5", "high", "claude-opus-5-5"),
            "execution": ("claude-sonnet-5-5", "high", "claude-sonnet-5-5"),
        },
        "codex": {
            "planning": ("gpt-6.2-astra", "high", "gpt-6.2-astra"),
            "execution": ("gpt-6.2-sol", "xhigh", "gpt-6.2-sol"),
        },
        "antigravity": {
            "planning": ("gemini-4-neon-high", "high", "gemini-4-neon-high"),
            "execution": ("gemini-4-carbon-medium", "medium", "gemini-4-carbon-medium"),
        },
    }

    def setUp(self) -> None:
        env_patch = mock.patch.dict(os.environ, {"SHIPLOOP_PROGRESS": "off"})
        env_patch.start()
        self.addCleanup(env_patch.stop)
        tmp = tempfile.TemporaryDirectory(prefix="shiploop-routing-matrix-", ignore_cleanup_errors=True)
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
        include_resume: bool = False,
        include_boundaries: bool = True,
        routed: bool = True,
        plan_reflect_and_improve: bool = False,
    ) -> tuple[Path, Path]:
        run_dir = base / "run"
        drive_log = base / "drive.log"
        run_dir.mkdir(parents=True, exist_ok=True)
        store.write_record(run_dir / "state.md", {
            "run_id": f"nav-{host}",
            "status": "paused",
            "stage": "product-acceptance" if plan_reflect_and_improve else "test-spec",
            "history": [
                {"stage": s, "outcome": "done", "summary": "ok", "workitem": None, "action": f"nav-{i}"}
                for i, s in enumerate(stages)
            ],
        })
        p_m, p_e, p_obs = spec["planning"]
        e_m, e_e, e_obs = spec["execution"]
        if routed and plan_reflect_and_improve:
            sid = f"{host}-thread-optin"
            rows = [
                {"session": 1, "host": host, "resumed": None, "profile": "execution", "model": e_m, "effort": e_e},
                {"session": 2, "host": host, "resumed": sid if include_resume else None, "profile": "planning", "model": p_m, "effort": p_e},
                {"session": 3, "host": host, "resumed": sid if include_resume else None, "profile": "execution", "model": e_m, "effort": e_e},
            ]
            trace_rows = [
                {"kind": "hook", "hook": "model", "host": host, "model": e_obs, "effort": e_e, "stage": "system-test-author", "profile": "execution"},
                *([{"kind": "hook", "hook": "stop", "host": host, "decision": "allow", "why": f"profile boundary reached ({host}:{e_m} -> {host}:{p_m} at improve)"}] if include_boundaries else []),
                {"kind": "hook", "hook": "model", "host": host, "model": p_obs, "effort": p_e, "stage": "improve", "profile": "planning"},
                *([{"kind": "hook", "hook": "stop", "host": host, "decision": "allow", "why": f"profile boundary reached ({host}:{p_m} -> {host}:{e_m} at system-test)"}] if include_boundaries else []),
                {"kind": "hook", "hook": "model", "host": host, "model": e_obs, "effort": e_e, "stage": "system-test", "profile": "execution"},
            ]
        elif routed:
            sid = f"{host}-thread-1"
            rows = [
                {"session": 1, "host": host, "resumed": None, "profile": "planning", "model": p_m, "effort": p_e},
                {"session": 2, "host": host, "resumed": sid if include_resume else None, "profile": "execution", "model": e_m, "effort": e_e},
            ]
            trace_rows = [
                {"kind": "hook", "hook": "model", "host": host, "model": p_obs, "effort": p_e, "stage": "prepare", "profile": "planning"},
                *([{"kind": "hook", "hook": "stop", "host": host, "decision": "allow", "why": f"profile boundary reached ({host}:{p_m} -> {host}:{e_m} at step-plan)"}] if include_boundaries else []),
                {"kind": "hook", "hook": "model", "host": host, "model": e_obs, "effort": e_e, "stage": "step-plan", "profile": "execution"},
            ]
        else:
            rows = [{"session": 1, "host": host, "resumed": None, "exit": 0}]
            trace_rows = [{"kind": "hook", "hook": "model", "host": host, "model": e_obs, "effort": e_e, "stage": "prepare", "profile": "planning"}]
        drive_log.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        (run_dir / "trace.jsonl").write_text("\n".join(json.dumps(r) for r in trace_rows) + "\n", encoding="utf-8")
        return run_dir, drive_log

    def test_routed_grader_accepts_all_three_hosts_and_rejects_broken_runs(self) -> None:
        prelude_stages = ["prepare", "step-plan"]
        for host, spec in self._SPECS.items():
            with self.subTest(host=host):
                run_dir, drive_log = self._write_synthetic_artifacts(
                    self.temp / f"{host}-ok", host=host, spec=spec, stages=prelude_stages, include_resume=False,
                )
                ok = self.probe.grade_run(
                    host, run_dir, drive_log, mode="routed",
                    expected_planning=(spec["planning"][0], spec["planning"][1]),
                    expected_execution=(spec["execution"][0], spec["execution"][1]),
                )
                self.assertTrue(ok["pass"], ok)
                self.assertTrue(ok["checks"].get("fresh_handoff_ok") or ok["checks"].get("single_session_ok"), ok)
                self.assertEqual(len(ok["boundary_stops"]), 1, ok)

        # Opt-in --plan-reflect-and-improve grading (system-test-author -> improve -> system-test, fresh default).
        opt_run, opt_dl = self._write_synthetic_artifacts(
            self.temp / "codex-optin-ok", host="codex", spec=self._SPECS["codex"],
            stages=["system-test-author", "system-test"], plan_reflect_and_improve=True, include_resume=False,
        )
        ok_opt = self.probe.grade_run(
            "codex", opt_run, opt_dl, mode="routed",
            expected_planning=("gpt-6.2-astra", "high"),
            expected_execution=("gpt-6.2-sol", "xhigh"),
            plan_reflect_and_improve=True,
        )
        self.assertTrue(ok_opt["pass"], ok_opt)
        self.assertTrue(ok_opt["checks"]["fresh_handoff_ok"], ok_opt)
        self.assertEqual(len(ok_opt["boundary_stops"]), 2, ok_opt)

        # Explicit warm-resume mode check (--resume-mode warm).
        run_warm, dl_warm = self._write_synthetic_artifacts(
            self.temp / "claude-warm-ok", host="claude", spec=self._SPECS["claude"],
            stages=prelude_stages, include_resume=True,
        )
        ok_warm = self.probe.grade_run(
            "claude", run_warm, dl_warm, mode="routed",
            expected_planning=("claude-opus-5-5", "high"), expected_execution=("claude-sonnet-5-5", "high"),
            resume_mode="warm",
        )
        self.assertTrue(ok_warm["pass"], ok_warm)
        self.assertTrue(ok_warm["checks"]["warm_resume_ok"], ok_warm)

        # Negative routed checks: unexpected warm resume under default fresh mode, missing warm resume under warm mode,
        # or flat unrouted run must fail.
        bad_fresh = self.probe.grade_run(
            "claude", run_warm, dl_warm, mode="routed",
            expected_planning=("claude-opus-5-5", "high"), expected_execution=("claude-sonnet-5-5", "high"),
        )
        self.assertFalse(bad_fresh["pass"])
        self.assertFalse(bad_fresh["checks"]["fresh_handoff_ok"])

        run_no_res, dl_no_res = self._write_synthetic_artifacts(
            self.temp / "claude-no-resume", host="claude", spec=self._SPECS["claude"],
            stages=prelude_stages, include_resume=False,
        )
        bad_res = self.probe.grade_run(
            "claude", run_no_res, dl_no_res, mode="routed",
            expected_planning=("claude-opus-5-5", "high"), expected_execution=("claude-sonnet-5-5", "high"),
            resume_mode="warm",
        )
        self.assertFalse(bad_res["pass"])
        self.assertFalse(bad_res["checks"]["warm_resume_ok"])

        # Single-session Antigravity Orchestrator grading (Neon plan <-> Hydrogen/Carbon execute inside one unbroken session).
        agy_orch = self.temp / "agy-orch"
        orch_run = agy_orch / "run"
        orch_dl = agy_orch / "drive.log"
        orch_run.mkdir(parents=True)
        store.write_record(orch_run / "state.md", {
            "run_id": "nav-agy-orch", "status": "paused", "stage": "test-spec",
            "history": [{"stage": s, "outcome": "done", "summary": "ok", "workitem": None, "action": f"nav-{i}"}
                        for i, s in enumerate(prelude_stages)],
        })
        orch_dl.write_text(
            json.dumps({"session": 1, "host": "antigravity", "resumed": None, "model": "gemini-pro-orchestrator-neon"}) + "\n",
            encoding="utf-8",
        )
        (orch_run / "trace.jsonl").write_text("\n".join([
            json.dumps({"kind": "hook", "hook": "model", "host": "antigravity", "model": "gemini-4-neon-high", "effort": "high", "stage": "prepare"}),
            json.dumps({"kind": "hook", "hook": "model", "host": "antigravity", "model": "gemini-4-hydrogen-high", "effort": "high", "stage": "step-plan"}),
        ]) + "\n", encoding="utf-8")
        ok_orch = self.probe.grade_run(
            "antigravity", orch_run, orch_dl, mode="routed",
            expected_planning=("gemini-pro-orchestrator-neon", None),
            expected_execution=("gemini-pro-orchestrator-neon", None),
        )
        self.assertTrue(ok_orch["pass"], ok_orch)
        self.assertTrue(ok_orch["checks"]["single_session_ok"])
        self.assertTrue(ok_orch["checks"]["target_recorded_ok"])
        self.assertTrue(ok_orch["checks"]["observed_models_ok"])

        # Spurious boundary stop fails single-session Orchestrator check.
        (orch_run / "trace.jsonl").write_text(
            (orch_run / "trace.jsonl").read_text(encoding="utf-8")
            + json.dumps({"kind": "hook", "hook": "stop", "host": "antigravity", "decision": "allow", "why": "profile boundary reached"}) + "\n",
            encoding="utf-8",
        )
        bad_orch = self.probe.grade_run(
            "antigravity", orch_run, orch_dl, mode="routed",
            expected_planning=("gemini-pro-orchestrator-neon", None),
            expected_execution=("gemini-pro-orchestrator-neon", None),
        )
        self.assertFalse(bad_orch["pass"])
        self.assertFalse(bad_orch["checks"]["single_session_ok"])

        run_unrouted, dl_unrouted = self._write_synthetic_artifacts(
            self.temp / "codex-unrouted", host="codex", spec=self._SPECS["codex"], stages=prelude_stages, routed=False,
        )
        ok_unrouted = self.probe.grade_run(
            "codex", run_unrouted, dl_unrouted, mode="unrouted",
            expected_planning=("gpt-6.2-sol", "xhigh"), expected_execution=("gpt-6.2-sol", "xhigh"),
        )
        self.assertTrue(ok_unrouted["pass"], ok_unrouted)

        bad_routed = self.probe.grade_run(
            "codex", run_unrouted, dl_unrouted, mode="routed",
            expected_planning=("gpt-6.2-astra", "high"), expected_execution=("gpt-6.2-sol", "xhigh"),
        )
        self.assertFalse(bad_routed["pass"])
        self.assertFalse(bad_routed["checks"]["fresh_handoff_ok"])
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
                staged_def = self.probe.stage_host(
                    host=host, mode="routed", out_dir=self.temp / "smoke-dry" / f"{host}-default",
                    pkg_dir=pkg, product_dir=product_dir, home_fix_dir=home_fix_dir,
                    source="checkout", planning=(p["model"], p["effort"]), execution=(e["model"], e["effort"]),
                    session_timeout=300, max_minutes=12, use_default_routing=True,
                )
                self.assertEqual(store.read_record(Path(staged_def["run_dir"]) / "state.md")["stage"], "prepare")
                self.assertNotIn("--routing", staged_def["argv"])
                self.assertNotIn("--no-routing", staged_def["argv"])
                self.assertNotIn("--plan-reflect-and-improve", staged_def["argv"])

                staged_ov = self.probe.stage_host(
                    host=host, mode="routed", out_dir=self.temp / "smoke-dry" / f"{host}-override",
                    pkg_dir=pkg, product_dir=product_dir, home_fix_dir=home_fix_dir,
                    source="checkout", planning=(p["model"], p["effort"]), execution=(e["model"], e["effort"]),
                    session_timeout=300, max_minutes=12, use_default_routing=False,
                    plan_reflect_and_improve=True,
                )
                self.assertEqual(store.read_record(Path(staged_ov["run_dir"]) / "state.md")["stage"], "system-test-author")
                self.assertIn("--routing", staged_ov["argv"])
                self.assertTrue(json.loads(Path(staged_ov["routing_path"]).read_text(encoding="utf-8"))["plan_reflect_and_improve"])

            staged_unr = self.probe.stage_host(
                host="codex", mode="unrouted", out_dir=self.temp / "smoke-dry" / "codex-unrouted",
                pkg_dir=pkg, product_dir=product_dir, home_fix_dir=home_fix_dir,
                source="checkout", planning=("gpt-6.2-sol", "xhigh"), execution=("gpt-6.2-sol", "xhigh"),
                session_timeout=300, max_minutes=12,
            )
            self.assertIn("--no-routing", staged_unr["argv"])


if __name__ == "__main__":
    unittest.main()
