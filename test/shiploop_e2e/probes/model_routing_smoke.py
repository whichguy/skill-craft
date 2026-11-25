#!/usr/bin/env python3
"""Live 3-host smoke runner for ShipLoop harness-to-model routing (Claude, Codex, Antigravity).

Seeds a minimal Python product at `system-test-author` (after the inner loop) so each host crosses
all three consecutive outer profile boundaries with zero Until Loops:

  system-test-author (planning, Model A)
    -> system-test (execution, Model B)
    -> product-acceptance (planning, Model A)
    -> release-plan (pauses here by default, or completes with --full-outer)

This verifies end-to-end across live CLIs that scripts own every boundary, pause/exit cleanly at
profile transitions, warm-`--resume` the same host conversation with the new model/effort, and
record passive `hook=model` + `hook=stop` telemetry in `trace.jsonl`.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
E2E_DIR = ROOT / "test" / "shiploop_e2e"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
if str(E2E_DIR) not in sys.path:
    sys.path.insert(0, str(E2E_DIR))

import run as e2e_run  # noqa: E402
import shiploop_model_routing as model_routing  # noqa: E402
import shiploop_store as store  # noqa: E402

ALL_HOSTS = ("claude", "codex", "antigravity")
SMOKE_STAGES = ("system-test-author", "system-test", "product-acceptance")
DEFAULT_ROUTES: dict[str, dict[str, dict[str, str]]] = {
    "antigravity": {
        "planning": {"model": "gemini-4-neon-high", "effort": "high"},
        "execution": {"model": "gemini-4-carbon-medium", "effort": "medium"},
    },
    "codex": {
        "planning": {"model": "gpt-6.2-astra", "effort": "high"},
        "execution": {"model": "gpt-6.2-sol", "effort": "medium"},
    },
    "claude": {
        "planning": {"model": "sonnet", "effort": "high"},
        "execution": {"model": "haiku", "effort": "low"},
    },
}
CODEX_UNROUTED_DEFAULT = ("gpt-6.2-sol", "medium")

SMOKE_GREET_PY = '''"""Minimal greeting helper for routing smoke checks."""


def greet(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("name must not be blank")
    return f"Hello, {cleaned}!"
'''

SMOKE_TEST_PY = '''import unittest

from greet import greet


class GreetTests(unittest.TestCase):
    def test_greet_trims_name(self) -> None:
        self.assertEqual(greet("  ShipLoop  "), "Hello, ShipLoop!")

    def test_greet_rejects_blank(self) -> None:
        with self.assertRaises(ValueError):
            greet("   ")


if __name__ == "__main__":
    unittest.main()
'''

SMOKE_SPEC_MD = """# Living spec

Seeded minimal specification for model-routing smoke validation.

## Requirements

R-1: `greet.greet(name)` strips whitespace, returns `Hello, <name>!`, and raises `ValueError` on blank input.
"""

SMOKE_ENV_MD = """# Environment

Seeded local Python unittest environment.

## Commands

```sh
python3 -m unittest -v
```
"""

SMOKE_ARCH_MD = """# Architecture

Single-module library `greet.py` tested via standard-library `unittest` (`test_greet.py`).
"""

SMOKE_PROMPT = (
    "Add `greet.greet(name)` returning `Hello, <name>!` (raising `ValueError` on blank input) "
    "with unittest coverage in `test_greet.py`."
)


def _strip_nested_markers(env: Mapping[str, str]) -> dict[str, str]:
    exact = {
        "ANTIGRAVITY_AGENT", "ANTIGRAVITY_CONVERSATION_ID", "ANTIGRAVITY_TRAJECTORY_ID",
        "SHIPLOOP_DRIVE_ROUTING", "SHIPLOOP_DRIVE_HOST", "SHIPLOOP_DRIVE_TARGET",
        "SHIPLOOP_DRIVE_LABEL", "SHIPLOOP_DRIVE_RUN_ID",
    }
    prefixes = ("CLAUDE", "CODEX", "GROK", "CURSOR")
    return {k: v for k, v in env.items() if k not in exact and not k.startswith(prefixes)}


def _build_checkout_package(out_root: Path) -> Path:
    pkg_out = out_root / "pkg"
    if pkg_out.exists():
        shutil.rmtree(pkg_out)
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build-packages.py"), str(pkg_out)],
        cwd=str(ROOT), check=True, capture_output=True, text=True,
    )
    return pkg_out


def _write_smoke_materials(out_root: Path) -> tuple[Path, Path]:
    materials = out_root / "_materials"
    product = materials / "product"
    home_fix = materials / "seed_home"
    product.mkdir(parents=True, exist_ok=True)
    home_fix.mkdir(parents=True, exist_ok=True)
    (product / "README.md").write_text("# greet\nMinimal smoke fixture.\n", encoding="utf-8")
    (product / "greet.py").write_text(SMOKE_GREET_PY, encoding="utf-8")
    (product / "test_greet.py").write_text(SMOKE_TEST_PY, encoding="utf-8")
    (home_fix / "spec.md").write_text(SMOKE_SPEC_MD, encoding="utf-8")
    (home_fix / "environment.md").write_text(SMOKE_ENV_MD, encoding="utf-8")
    (home_fix / "architecture.md").write_text(SMOKE_ARCH_MD, encoding="utf-8")
    return product, home_fix


def _write_gitconfig(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[user]\n\tname = ShipLoop Smoke\n\temail = shiploop-smoke@example.invalid\n", encoding="utf-8")
    return path


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except ValueError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _model_matches(observed_model: Any, observed_effort: Any, expected_model: str, expected_effort: str | None) -> bool:
    obs_m = str(observed_model or "").lower()
    if expected_model.lower() not in obs_m:
        return False
    if expected_effort and not expected_model.endswith(model_routing.EFFORT_SUFFIXES):
        return str(observed_effort or "").lower() == expected_effort.lower()
    return True


def _subsequence_match(events: list[dict[str, Any]], expected: list[tuple[str, str | None, str]]) -> bool:
    idx = 0
    for ev in events:
        if idx >= len(expected):
            break
        exp_model, exp_effort, exp_profile = expected[idx]
        if ev.get("profile") == exp_profile and _model_matches(ev.get("model"), ev.get("effort"), exp_model, exp_effort):
            idx += 1
    return idx == len(expected)


def grade_run(
    host: str,
    run_dir: Path,
    drive_log: Path,
    *,
    mode: str,
    expected_planning: tuple[str, str | None],
    expected_execution: tuple[str, str | None],
    check_boundary_stops: bool = True,
) -> dict[str, Any]:
    """Grade one completed or paused smoke run purely from disk records (`state.md`, `drive.log`, `trace.jsonl`)."""
    norm_host = model_routing.normalize_host(host)
    state_path = run_dir / "state.md"
    state = store.read_record(state_path) if state_path.is_file() else {}
    accepted_stages = [entry.get("stage") for entry in state.get("history", []) if isinstance(entry, dict)]
    stages_ok = all(stage in accepted_stages for stage in SMOKE_STAGES)

    drive_rows = _read_jsonl(drive_log)
    trace_rows = _read_jsonl(run_dir / "trace.jsonl")
    model_rows = [row for row in trace_rows if row.get("kind") == "hook" and row.get("hook") == "model"]
    stop_rows = [row for row in trace_rows if row.get("kind") == "hook" and row.get("hook") == "stop"]

    boundary_stages = [
        str(row.get("why") or "")
        for row in stop_rows
        if row.get("decision") == "allow" and "profile boundary reached" in str(row.get("why") or "")
    ]

    if mode == "routed":
        sessions = [row for row in drive_rows if row.get("session") is not None]
        resumed_ids = [row.get("resumed") for row in sessions[1:3] if isinstance(row.get("resumed"), str) and row.get("resumed")]
        warm_resume_ok = len(sessions) >= 3 and len(resumed_ids) == 2 and len(set(resumed_ids)) == 1
        boundary_stops_ok = (
            (any("at system-test)" in why for why in boundary_stages)
             and any("at product-acceptance)" in why for why in boundary_stages))
            if check_boundary_stops else True
        )
        observed_models_ok = _subsequence_match(
            model_rows,
            [
                (expected_planning[0], expected_planning[1], "planning"),
                (expected_execution[0], expected_execution[1], "execution"),
                (expected_planning[0], expected_planning[1], "planning"),
            ],
        )
        passed = stages_ok and warm_resume_ok and boundary_stops_ok and observed_models_ok
        checks = {
            "stages_ok": stages_ok,
            "warm_resume_ok": warm_resume_ok,
            "boundary_stops_ok": boundary_stops_ok,
            "observed_models_ok": observed_models_ok,
        }
    else:
        has_routing_keys = any("profile" in row or "target" in row for row in drive_rows)
        unrouted_clean = (not has_routing_keys) and (len(boundary_stages) == 0)
        exp_m, exp_e = expected_execution
        observed_models_ok = any(
            _model_matches(ev.get("model"), ev.get("effort"), exp_m, exp_e) for ev in model_rows
        )
        passed = stages_ok and unrouted_clean and observed_models_ok
        checks = {
            "stages_ok": stages_ok,
            "unrouted_clean": unrouted_clean,
            "observed_models_ok": observed_models_ok,
        }

    return {
        "host": norm_host,
        "mode": mode,
        "pass": passed,
        "checks": checks,
        "state_status": state.get("status"),
        "state_stage": state.get("stage"),
        "revision": state.get("revision"),
        "accepted_outer_stages": [s for s in accepted_stages if s in (*SMOKE_STAGES, "release-plan", "release-check", "release", "release-verify", "operations", "handoff")],
        "drive_sessions": len(drive_rows),
        "boundary_stops": boundary_stages,
        "observed_models": [
            {"model": r.get("model"), "effort": r.get("effort"), "stage": r.get("stage"), "profile": r.get("profile")}
            for r in model_rows
        ],
        "run_dir": str(run_dir),
        "drive_log": str(drive_log),
    }


def stage_host(
    *,
    host: str,
    mode: str,
    out_dir: Path,
    pkg_dir: Path,
    product_dir: Path,
    home_fix_dir: Path,
    source: str,
    planning: tuple[str, str | None],
    execution: tuple[str, str | None],
    session_timeout: int,
    max_minutes: int,
) -> dict[str, Any]:
    """Stage an isolated workspace, seeded run, plugin, env, and `shiploop-drive` argv for `host`."""
    norm_host = model_routing.normalize_host(host)
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    work = out_dir / "work"
    runs_out = out_dir / "out"
    ka_home = out_dir / "keepalive"
    work.mkdir(parents=True, exist_ok=True)
    runs_out.mkdir(parents=True, exist_ok=True)
    ka_home.mkdir(parents=True, exist_ok=True)
    gitconfig = _write_gitconfig(out_dir / "gitconfig")

    base_env = _strip_nested_markers(os.environ)
    base_env.update({
        "GIT_CONFIG_GLOBAL": str(gitconfig),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "NO_COLOR": "1",
        "SHIPLOOP_KEEPALIVE_HOME": str(ka_home),
        "SHIPLOOP_PROGRESS": "off",
    })

    plugin_src = pkg_dir / "plugins" / "skill-craft"
    if norm_host == "antigravity":
        stage_root = out_dir / "agy-stage"
        plugin_dest = stage_root / ".agents" / "plugins" / "skill-craft"
        shutil.rmtree(plugin_dest, ignore_errors=True)
        plugin_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(plugin_src, plugin_dest)
        cli = plugin_dest / "skills" / "shiploop" / "scripts" / "shiploop"
        drive_bin = plugin_dest / "skills" / "shiploop" / "scripts" / "shiploop-drive"
        improve = plugin_dest / "skills" / "improve" / "SKILL.md"
        extra = ["--dangerously-skip-permissions", "--add-dir", str(stage_root), "--add-dir", str(out_dir)]
    elif norm_host == "codex":
        codex_home = out_dir / "codex-home"
        shutil.rmtree(codex_home, ignore_errors=True)
        codex_home.mkdir(parents=True, exist_ok=True)
        real_auth = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "auth.json"
        if real_auth.is_file():
            (codex_home / "auth.json").symlink_to(real_auth)
        base_env["CODEX_HOME"] = str(codex_home)
        if source == "checkout":
            subprocess.run(["codex", "plugin", "marketplace", "add", str(pkg_dir)],
                           env=base_env, check=True, capture_output=True, text=True)
            subprocess.run(["codex", "plugin", "add", "skill-craft@whichguy"],
                           env=base_env, check=True, capture_output=True, text=True)
            cli = next((codex_home / "plugins" / "cache").glob("*/skill-craft/*/skills/shiploop/scripts/shiploop"))
            drive_bin = cli.with_name("shiploop-drive")
            improve = cli.parents[2] / "improve" / "SKILL.md"
        else:
            subprocess.run(["codex", "plugin", "marketplace", "add", e2e_run.MARKETPLACE_SOURCE],
                           env=base_env, check=True, capture_output=True, text=True)
            subprocess.run(["codex", "plugin", "add", "skill-craft@whichguy"],
                           env=base_env, check=True, capture_output=True, text=True)
            cli = next((codex_home / "plugins" / "cache").glob("*/skill-craft/*/skills/shiploop/scripts/shiploop"))
            drive_bin = cli.with_name("shiploop-drive")
            improve = cli.parents[2] / "improve" / "SKILL.md"
        extra = ["--dangerously-bypass-approvals-and-sandbox", "--dangerously-bypass-hook-trust", "--skip-git-repo-check"]
        if mode == "unrouted":
            extra += ["-m", execution[0]]
            if execution[1]:
                extra += ["-c", f"model_reasoning_effort={execution[1]}"]
    elif norm_host == "claude":
        staged_plugin = out_dir / "claude-plugin"
        shutil.rmtree(staged_plugin, ignore_errors=True)
        shutil.copytree(plugin_src, staged_plugin)
        cli = staged_plugin / "skills" / "shiploop" / "scripts" / "shiploop"
        drive_bin = cli.with_name("shiploop-drive")
        improve = staged_plugin / "skills" / "improve" / "SKILL.md"
        extra = [
            "--dangerously-skip-permissions",
            "--setting-sources", "project,local",
            "--strict-mcp-config",
            "--plugin-dir", str(staged_plugin),
        ]
        if mode == "unrouted":
            extra += ["--model", execution[0]]
            if execution[1]:
                extra += ["--effort", execution[1]]
    else:
        raise ValueError(f"unsupported smoke host: {host!r}")

    seeded = e2e_run.seed_run(
        cli, work, runs_out, SMOKE_PROMPT, "system-test-author",
        work_item={"id": "W1", "title": "Add greet helper"},
        delegation="inline",
        checks=["python3 -m unittest -v"],
        product=product_dir,
        home_fixture=home_fix_dir,
        exclude=["README.md"],
        planning_review="none",
        improve_skill=str(improve),
        release_slice_mode=True,
    )
    run_dir = Path(seeded["run_dir"]).resolve()
    run_id = store.read_record(run_dir / "state.md")["run_id"]
    drive_log = ka_home / "drive" / run_id / "drive.log"

    routing_path = out_dir / "routing.json"
    argv = [
        sys.executable, str(drive_bin),
        "--host", norm_host,
        "--run-dir", str(run_dir),
        "--max-minutes", str(max_minutes),
        "--session-timeout", str(session_timeout),
    ]
    if mode == "routed":
        routing_cfg = {
            "planning": {norm_host: _route_entry(planning[0], planning[1])},
            "execution": {norm_host: _route_entry(execution[0], execution[1])},
        }
        routing_path.write_text(json.dumps(routing_cfg, indent=2) + "\n", encoding="utf-8")
        argv += ["--routing", str(routing_path)]
    argv += ["--", *extra]

    return {
        "host": norm_host,
        "mode": mode,
        "out_dir": str(out_dir),
        "run_dir": str(run_dir),
        "run_id": run_id,
        "cli": str(cli),
        "drive_log": str(drive_log),
        "routing_path": str(routing_path) if mode == "routed" else None,
        "argv": argv,
        "env": base_env,
        "expected_planning": planning,
        "expected_execution": execution,
    }


def _route_entry(model: str, effort: str | None) -> dict[str, str]:
    entry = {"model": model}
    if effort and not model.endswith(model_routing.EFFORT_SUFFIXES):
        entry["effort"] = effort
    return entry


def _pause_watcher(cli: Path, run_dir: Path, env: dict[str, str], stop_event: threading.Event) -> None:
    while not stop_event.wait(0.5):
        res = subprocess.run([sys.executable, str(cli), "hook-status", "--run-dir", str(run_dir)],
                             env=env, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            continue
        try:
            st = json.loads(res.stdout)
        except ValueError:
            continue
        if st.get("stage") == "release-plan" and st.get("status") == "active":
            subprocess.run([sys.executable, str(cli), "pause", "--run-dir", str(run_dir),
                            "--reason", "model-routing smoke complete (crossed system-test-author -> system-test -> product-acceptance)"],
                           env=env, capture_output=True, text=True, check=False)
            return
        if st.get("status") != "active":
            return


def run_staged(spec: dict[str, Any], *, full_outer: bool = False) -> dict[str, Any]:
    run_dir = Path(spec["run_dir"])
    cli = Path(spec["cli"])
    env = spec["env"]
    stop_event = threading.Event()
    watcher = None
    if not full_outer:
        watcher = threading.Thread(target=_pause_watcher, args=(cli, run_dir, env, stop_event), daemon=True)
        watcher.start()
    started = time.monotonic()
    try:
        proc = subprocess.run(spec["argv"], env=env, capture_output=True, text=True, check=False)
    finally:
        stop_event.set()
        if watcher is not None:
            watcher.join(timeout=5)
    seconds = round(time.monotonic() - started, 2)
    (Path(spec["out_dir"]) / "driver-stdout.log").write_text(proc.stdout + "\n--- stderr ---\n" + proc.stderr, encoding="utf-8")
    verdict = grade_run(
        spec["host"],
        run_dir,
        Path(spec["drive_log"]),
        mode=spec["mode"],
        expected_planning=tuple(spec["expected_planning"]),
        expected_execution=tuple(spec["expected_execution"]),
        check_boundary_stops=True,
    )
    verdict["driver_exit"] = proc.returncode
    verdict["wall_seconds"] = seconds
    return verdict


def _parse_spec(raw: str | None, default: tuple[str, str | None]) -> tuple[str, str | None]:
    if not raw:
        return default
    if "/" in raw:
        model, _, effort = raw.partition("/")
        return model.strip(), (effort.strip() or None)
    return raw.strip(), None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--hosts", default="claude,codex,antigravity",
                        help="comma-separated hosts from claude,codex,antigravity")
    parser.add_argument("--mode", choices=("routed", "unrouted", "both"), default="routed")
    parser.add_argument("--source", choices=("checkout", "marketplace"), default="checkout")
    parser.add_argument("--output", help="directory for smoke outputs (created if absent)")
    parser.add_argument("--timeout-minutes", type=int, default=12)
    parser.add_argument("--session-timeout", type=int, default=300)
    parser.add_argument("--full-outer", action="store_true",
                        help="let each host run all outer stages to `done` instead of pausing at release-plan")
    parser.add_argument("--dry-run", action="store_true",
                        help="stage workspaces and print driver commands without invoking live models")
    parser.add_argument("--antigravity-planning", help="model[/effort], default gemini-4-neon-high")
    parser.add_argument("--antigravity-execution", help="model[/effort], default gemini-4-carbon-medium")
    parser.add_argument("--codex-planning", help="model[/effort], default gpt-6.2-astra/high")
    parser.add_argument("--codex-execution", help="model[/effort], default gpt-6.2-sol/medium")
    parser.add_argument("--claude-planning", help="model[/effort], default sonnet/high")
    parser.add_argument("--claude-execution", help="model[/effort], default haiku/low")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    hosts = [model_routing.normalize_host(h) for h in args.hosts.split(",") if h.strip()]
    unknown = [h for h in hosts if h not in ALL_HOSTS]
    if not hosts or unknown:
        print(f"model_routing_smoke: invalid hosts {unknown or hosts}; expected subset of {ALL_HOSTS}", file=sys.stderr)
        return 2
    modes = ("routed", "unrouted") if args.mode == "both" else (args.mode,)
    out_root = Path(args.output).resolve() if args.output else Path(tempfile.mkdtemp(prefix="shiploop-routing-smoke-")).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    pkg_dir = _build_checkout_package(out_root)
    product_dir, home_fix_dir = _write_smoke_materials(out_root)

    overrides = {
        "antigravity": (
            _parse_spec(args.antigravity_planning, (DEFAULT_ROUTES["antigravity"]["planning"]["model"], DEFAULT_ROUTES["antigravity"]["planning"]["effort"])),
            _parse_spec(args.antigravity_execution, (DEFAULT_ROUTES["antigravity"]["execution"]["model"], DEFAULT_ROUTES["antigravity"]["execution"]["effort"])),
        ),
        "codex": (
            _parse_spec(args.codex_planning, (DEFAULT_ROUTES["codex"]["planning"]["model"], DEFAULT_ROUTES["codex"]["planning"]["effort"])),
            _parse_spec(args.codex_execution, (DEFAULT_ROUTES["codex"]["execution"]["model"], DEFAULT_ROUTES["codex"]["execution"]["effort"])),
        ),
        "claude": (
            _parse_spec(args.claude_planning, (DEFAULT_ROUTES["claude"]["planning"]["model"], DEFAULT_ROUTES["claude"]["planning"]["effort"])),
            _parse_spec(args.claude_execution, (DEFAULT_ROUTES["claude"]["execution"]["model"], DEFAULT_ROUTES["claude"]["execution"]["effort"])),
        ),
    }

    staged: list[dict[str, Any]] = []
    for host in hosts:
        planning, execution = overrides[host]
        for mode in modes:
            cell_out = out_root / f"{host}-{mode}"
            staged.append(stage_host(
                host=host,
                mode=mode,
                out_dir=cell_out,
                pkg_dir=pkg_dir,
                product_dir=product_dir,
                home_fix_dir=home_fix_dir,
                source=args.source,
                planning=planning,
                execution=execution,
                session_timeout=args.session_timeout,
                max_minutes=args.timeout_minutes,
            ))

    if args.dry_run:
        summary = {"dry_run": True, "output": str(out_root), "staged": [
            {k: v for k, v in spec.items() if k != "env"} for spec in staged
        ]}
        (out_root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 0

    with ThreadPoolExecutor(max_workers=len(staged)) as pool:
        results = list(pool.map(lambda s: run_staged(s, full_outer=args.full_outer), staged))

    all_pass = all(r["pass"] for r in results)
    summary = {"dry_run": False, "pass": all_pass, "output": str(out_root), "results": results}
    (out_root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    for r in results:
        tag = "PASS" if r["pass"] else "FAIL"
        print(f"{tag}  {r['host']}/{r['mode']}  wall={r['wall_seconds']}s  checks={r['checks']}  models={len(r['observed_models'])}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
