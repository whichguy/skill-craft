#!/usr/bin/env python3
"""Create a fresh, frozen generalized-discovery study without running a model.

Initialization copies only local inputs and performs the deterministic fixture
calibration before any arms exist.  The frozen runner is intentionally included
for a later, separately authorized run; its workspace gateway uses macOS
``sandbox-exec``.  This initializer itself does not invoke Codex, a network
client, an installer, or that gateway.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
REFERENCES = REPO / "skills" / "shiploop" / "references"
CAPABILITIES = HERE.parent / "shiploop_capabilities"

FROZEN_SOURCES = {
    "fixtures.py": HERE / "fixtures.py",
    "study_inputs.py": HERE / "study_inputs.py",
    "PUBLIC_CONTRACTS.md": HERE / "PUBLIC_CONTRACTS.md",
    "ORACLE.md": HERE / "ORACLE.md",
    "oracle.py": HERE / "oracle.py",
    "prepare.py": HERE / "prepare.py",
    "runner.py": HERE / "runner.py",
    "receipt_gateway.py": HERE / "receipt_gateway.py",
    "collect.py": HERE / "collect.py",
    "run_trials.py": CAPABILITIES / "run_trials.py",
    "runtime_validation.py": CAPABILITIES / "runtime_validation.py",
    "gateway.py": CAPABILITIES / "gateway.py",
}

LIMITS = {
    "aggregate_active_limit_seconds": 180 * 60,
    "max_arm_launches": 12,
    "parallel": 3,
    "seconds_per_arm": 480,
    "calls_per_arm": 32,
    "exploration_seconds": 360,
    "exploration_calls": 24,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _readable_file(path: Path, label: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"{label} is unavailable") from exc
    if path.is_symlink() or not resolved.is_file():
        raise ValueError(f"{label} must be a regular file")
    try:
        resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"{label} must be readable UTF-8 text") from exc
    return resolved


def _regular_tree(root: Path, label: str) -> None:
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise ValueError(f"{label} contains an unsafe entry: {path}")


def _validate_inputs(study: Path, candidate: Path, plan: Path) -> tuple[Path, Path, Path]:
    if not study.is_absolute():
        raise ValueError("--study must be an absolute path")
    if study.is_symlink():
        raise FileExistsError(f"study path already exists: {study}")
    study = study.resolve()
    if study.exists():
        raise FileExistsError(f"study path already exists: {study}")
    candidate = _readable_file(candidate, "--candidate")
    plan = _readable_file(plan, "--plan")
    if REFERENCES.is_symlink() or not REFERENCES.is_dir():
        raise ValueError("current ShipLoop references are unavailable")
    _regular_tree(REFERENCES, "current ShipLoop references")
    _readable_file(REFERENCES / "research-loop.md", "baseline research-loop.md")
    for name, source in FROZEN_SOURCES.items():
        _readable_file(source, f"required source {name}")
    return study, candidate, plan


def _copy_inputs(study: Path, candidate: Path, plan: Path) -> None:
    frozen, guides = study / "frozen", study / "guides"
    frozen.mkdir(parents=True)
    guides.mkdir()
    for name, source in FROZEN_SOURCES.items():
        shutil.copy2(source, frozen / name)
    shutil.copy2(plan, frozen / "plan.md")
    shutil.copytree(
        REFERENCES,
        guides / "references",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copy2(REFERENCES / "research-loop.md", guides / "baseline.md")
    shutil.copy2(candidate, guides / "candidate.md")
    (study / "arms").mkdir()
    (study / "private").mkdir()
    (study / "reports").mkdir()


def _load_frozen_oracle(path: Path) -> Any:
    name = "shiploop_generalized_frozen_oracle_" + sha256(path)[:12]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError("frozen oracle is unreadable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def _calibrate(study: Path) -> dict[str, Any]:
    """Return a calibration record even if a local fixture check fails."""
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        oracle = _load_frozen_oracle(study / "frozen" / "oracle.py")
        result = oracle.calibrate(study / "frozen" / "fixtures.py", study / "frozen" / "PUBLIC_CONTRACTS.md")
        if not isinstance(result, dict):
            raise ValueError("frozen oracle returned an unsupported calibration")
        return result
    except Exception as exc:
        return {
            "schema": "generalized-discovery-oracle/1",
            "mode": "calibration",
            "passed": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
    finally:
        sys.dont_write_bytecode = previous


def _frozen_manifest(study: Path) -> dict[str, str]:
    roots = (study / "frozen", study / "guides")
    result: dict[str, str] = {}
    for root in roots:
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"frozen input must not be a symlink: {path}")
            if path.is_file():
                result[str(path.relative_to(study))] = sha256(path)
    calibration = study / "private" / "oracle-calibration.json"
    if calibration.is_file() and not calibration.is_symlink():
        result[str(calibration.relative_to(study))] = sha256(calibration)
    if "study.json" in result:
        raise AssertionError("mutable study state must not be frozen")
    return result


def initialize(study: Path, candidate: Path, plan: Path, blind_seed: int = 29017) -> dict[str, Any]:
    """Initialize one empty study and leave failed calibration evidence in place."""
    if isinstance(blind_seed, bool) or not isinstance(blind_seed, int):
        raise ValueError("--blind-seed must be an integer")
    study, candidate, plan = _validate_inputs(study, candidate, plan)
    started = time.time()
    study.mkdir(parents=True)
    _copy_inputs(study, candidate, plan)

    state: dict[str, Any] = {
        "schema": "generalized-discovery-study/1",
        "started_epoch": started,
        "hard_deadline_epoch": started + 90 * 60,
        "closeout_start_epoch": started + 75 * 60,
        **LIMITS,
        "aggregate_active_limit_note": "Coordinator responsibility; the runner does not measure aggregate active time.",
        "blind_order_seed": blind_seed,
        "guide_hashes": {
            "baseline.md": sha256(study / "guides" / "baseline.md"),
            "candidate.md": sha256(study / "guides" / "candidate.md"),
        },
        "hashes": {},
        "status": "initializing",
        "arms": {},
    }
    write_json(study / "study.json", state)

    calibration = _calibrate(study)
    write_json(study / "private" / "oracle-calibration.json", calibration)
    manifest = _frozen_manifest(study)
    manifest_path = study / "frozen-inputs.json"
    write_json(manifest_path, manifest)
    passed = calibration.get("passed") is True
    state["hashes"] = {
        "baseline": state["guide_hashes"]["baseline.md"],
        "candidate": state["guide_hashes"]["candidate.md"],
        "plan": sha256(study / "frozen" / "plan.md"),
        "oracle_calibration": sha256(study / "private" / "oracle-calibration.json"),
        "frozen_inputs_manifest": sha256(manifest_path),
    }
    state["frozen_inputs_manifest"] = "frozen-inputs.json"
    state["status"] = "ready_to_prepare" if passed else "calibration_failed"
    write_json(study / "study.json", state)
    return {
        "study": str(study),
        "status": state["status"],
        "calibration_passed": passed,
        "frozen_inputs_manifest": str(manifest_path),
        "frozen_inputs_sha256": state["hashes"]["frozen_inputs_manifest"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--blind-seed", type=int, default=29017)
    args = parser.parse_args()
    try:
        result = initialize(args.study, args.candidate, args.plan, args.blind_seed)
    except (OSError, ValueError, FileExistsError) as exc:
        print(f"initializer failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["calibration_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
