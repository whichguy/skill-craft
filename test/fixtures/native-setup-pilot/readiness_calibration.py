#!/usr/bin/env python3
"""Calibrate the local readiness fixture with stdlib-only subprocess checks."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

STATE_ENV = "NATIVE_SETUP_TARGET"


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def call(fixture: Path, target: Path, *args: str) -> dict:
    env = {**os.environ, STATE_ENV: str(target)}
    done = subprocess.run([sys.executable, str(fixture / "readiness_cli.py"), *args], cwd=fixture,
                          env=env, capture_output=True, text=True, check=False, timeout=10)
    try:
        result: Any = json.loads(done.stdout)
    except ValueError:
        result = {"unparsed_stdout": done.stdout.strip()}
    return {"argv": ["readiness_cli.py", *args], "returncode": done.returncode, "result": result,
            "stderr": done.stderr.strip()}


def load_formatter(path: Path):
    spec = importlib.util.spec_from_file_location("readiness_offline_summary", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load formatter {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--seed-state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    fixture, seed_state, output = (p.expanduser().resolve() for p in (args.fixture, args.seed_state, args.output))
    if not fixture.is_dir() or not seed_state.is_dir():
        parser.error("fixture and seed-state must be existing directories")
    if output.exists():
        parser.error(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    source_before = {"fixture": tree_hash(fixture), "seed_state": tree_hash(seed_state)}
    checks: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="readiness-calibration-", dir=output.parent) as temporary:
        target = Path(temporary) / "target"
        shutil.copytree(seed_state, target)
        initial_audit = (target / "audit.jsonl").read_text(encoding="utf-8")
        probes = [call(fixture, target, "probe", name) for name in ("service", "sandbox", "grant")]
        checks.append({"check": "initial_probe_states", "pass": (
            probes[0]["returncode"] == 0 and probes[0]["result"].get("status") == "ready"
            and probes[1]["returncode"] == 0 and probes[1]["result"].get("status") == "missing"
            and probes[1]["result"].get("authorized_setup") is True
            and probes[2]["returncode"] == 0 and probes[2]["result"].get("status") == "unavailable"
            and probes[2]["result"].get("authorized") is False), "calls": probes})
        checks.append({"check": "probe_is_read_only", "pass": (target / "audit.jsonl").read_text(encoding="utf-8") == initial_audit
                       and not (target / "sandbox-receipt.json").exists()})

        first_setup = call(fixture, target, "setup", "sandbox")
        sandbox_config = (target / "sandbox.json").read_bytes()
        sandbox_receipt = (target / "sandbox-receipt.json").read_bytes()
        ready_probe = call(fixture, target, "probe", "sandbox")
        second_setup = call(fixture, target, "setup", "sandbox")
        checks.append({"check": "authorized_setup_and_valid_receipt", "pass": (
            first_setup["returncode"] == 0 and first_setup["result"].get("status") == "ready"
            and first_setup["result"].get("changed") is True
            and first_setup["result"].get("receipt_valid") is True
            and ready_probe["result"].get("status") == "ready"
            and ready_probe["result"].get("receipt_valid") is True)})
        checks.append({"check": "setup_is_idempotent", "pass": (
            second_setup["returncode"] == 0 and second_setup["result"].get("status") == "ready"
            and second_setup["result"].get("changed") is False
            and (target / "sandbox.json").read_bytes() == sandbox_config
            and (target / "sandbox-receipt.json").read_bytes() == sandbox_receipt),
            "first_setup": first_setup, "second_setup": second_setup})

        grant_before = (target / "external-grant.json").read_bytes()
        journeys = [call(fixture, target, "journey", name) for name in ("service", "sandbox", "grant")]
        denied_setup = call(fixture, target, "setup", "grant")
        checks.append({"check": "local_journeys_and_unauthorized_grant", "pass": (
            journeys[0]["returncode"] == 0 and journeys[0]["result"].get("status") == "completed"
            and journeys[1]["returncode"] == 0 and journeys[1]["result"].get("status") == "completed"
            and journeys[2]["returncode"] == 3 and journeys[2]["result"].get("status") == "blocked"
            and denied_setup["returncode"] == 2 and denied_setup["result"].get("status") == "denied"
            and (target / "external-grant.json").read_bytes() == grant_before),
            "journeys": journeys, "denied_setup": denied_setup})

        events = [json.loads(line) for line in (target / "audit.jsonl").read_text(encoding="utf-8").splitlines() if line]
        expected_events = [
            {"seq": 1, "command": "setup", "target": "sandbox", "result": "configured"},
            {"seq": 2, "command": "setup", "target": "sandbox", "result": "already_ready"},
            {"seq": 3, "command": "journey", "target": "service", "result": "completed"},
            {"seq": 4, "command": "journey", "target": "sandbox", "result": "completed"},
            {"seq": 5, "command": "journey", "target": "grant", "result": "blocked"},
            {"seq": 6, "command": "setup", "target": "grant", "result": "denied"},
        ]
        checks.append({"check": "secret_free_append_only_audit", "pass": events == expected_events, "events": events})
        receipt = json.loads((target / "sandbox-receipt.json").read_text(encoding="utf-8"))

    formatter = load_formatter(fixture / "offline_summary.py")
    sample_rows = [{"target": "service", "status": "ready"}, {"target": "sandbox", "status": "missing"}]
    expected_format = "service: ready\nsandbox: missing\n"
    observed_format = formatter.render_summary(sample_rows)
    empty_format = formatter.render_summary([])
    format_evidence = {"expected": expected_format, "observed": observed_format,
                       "empty_expected": "", "empty_observed": empty_format,
                       "matches_contract": observed_format == expected_format and empty_format == ""}
    source_after = {"fixture": tree_hash(fixture), "seed_state": tree_hash(seed_state)}
    artifact = {"valid": all(row["pass"] for row in checks) and source_before == source_after,
                "scope": "local synthetic fixture; no model, network, service, account, or credential",
                "source_hashes_before": source_before, "source_hashes_after": source_after,
                "readiness_checks": checks, "sandbox_receipt": receipt,
                "formatter_baseline": format_evidence}
    output.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"valid": artifact["valid"], "readiness_checks": checks,
                      "formatter_baseline": format_evidence, "receipt": str(output)},
                     indent=2, ensure_ascii=False))
    return 0 if artifact["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
