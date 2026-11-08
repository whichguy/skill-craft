#!/usr/bin/env python3
"""Acceptance checks for the local formatter and readiness journeys."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parent
STATE_ENV = "NATIVE_SETUP_TARGET"
SANDBOX_CONFIG = {
    "configured": True,
    "profile": "demo",
    "provisioned": True,
    "target": "local-sandbox",
}
SANDBOX_RECEIPT_FIELDS = {
    "authorization_source": "fixture_explicit_permission",
    "format": "native-setup-receipt/1",
    "operations": ["provision", "configure"],
    "task": "local-sandbox-provision-configure",
}


def _target() -> Path:
    raw = os.environ.get(STATE_ENV)
    if not raw:
        raise AssertionError(f"{STATE_ENV} must be supplied by the workflow")
    target = Path(raw).expanduser().resolve()
    if not target.is_dir():
        raise AssertionError(f"{STATE_ENV} must name the provided state directory")
    return target


def _audit_setup_rows(target: Path) -> tuple[bytes, ...]:
    path = target / "audit.jsonl"
    if not path.is_file():
        raise AssertionError("the supplied target has no audit.jsonl")
    rows = []
    for line in path.read_bytes().splitlines(keepends=True):
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("command") == "setup":
            rows.append(line)
    return tuple(rows)


def _cli(*args: str) -> tuple[subprocess.CompletedProcess[str], dict]:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    process = subprocess.run(
        [sys.executable, str(ROOT / "readiness_cli.py"), *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    try:
        result = json.loads(process.stdout)
    except ValueError as error:
        raise AssertionError(f"CLI did not return JSON: {process.stdout!r}") from error
    return process, result


def _canonical_sha256(value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _read_sandbox_state(target: Path) -> tuple[dict, dict]:
    config = json.loads((target / "sandbox.json").read_text(encoding="utf-8"))
    receipt = json.loads((target / "sandbox-receipt.json").read_text(encoding="utf-8"))
    expected_receipt = {
        **SANDBOX_RECEIPT_FIELDS,
        "config_sha256": _canonical_sha256(SANDBOX_CONFIG),
    }
    if config != SANDBOX_CONFIG:
        raise AssertionError(f"unexpected sandbox configuration: {config!r}")
    if receipt != expected_receipt:
        raise AssertionError(f"sandbox receipt does not independently match the configuration: {receipt!r}")
    return config, receipt


class ReadinessAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.target = _target()
        cls.setup_rows_before = _audit_setup_rows(cls.target)

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "target") and hasattr(cls, "setup_rows_before"):
            setup_rows_after = _audit_setup_rows(cls.target)
            if setup_rows_after != cls.setup_rows_before:
                raise AssertionError("acceptance tests must not add sandbox setup events or repair the supplied target")

    def test_R1_formatter_exact_order_newline_and_empty(self) -> None:
        spec = importlib.util.spec_from_file_location("subject_offline_summary", ROOT / "offline_summary.py")
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader if spec else None)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        rows = [
            {"target": "service", "status": "ready"},
            {"target": "external-grant", "status": "owner_authorization"},
        ]
        self.assertEqual(
            module.render_summary(rows),
            "service: ready\nexternal-grant: owner_authorization\n",
        )
        self.assertEqual(module.render_summary([]), "")

    def test_R2_service_journey_completes(self) -> None:
        process, result = _cli("journey", "service")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(result.get("status"), "completed")
        self.assertEqual(result.get("target"), "service")

    def test_R3_sandbox_probe_readback_and_journey_are_separate(self) -> None:
        probe_process, probe = _cli("probe", "sandbox")
        self.assertEqual(probe_process.returncode, 0, probe_process.stderr)
        self.assertEqual(probe.get("status"), "ready")
        self.assertIs(probe.get("receipt_valid"), True)

        _read_sandbox_state(self.target)

        journey_process, journey = _cli("journey", "sandbox")
        self.assertEqual(journey_process.returncode, 0, journey_process.stderr)
        self.assertEqual(journey.get("status"), "completed")
        self.assertEqual(journey.get("target"), "sandbox")

    def test_R4_grant_remains_blocked_and_unchanged(self) -> None:
        grant_before = (self.target / "external-grant.json").read_bytes()
        authorization_before = (self.target / "authorization.json").read_bytes()

        probe_process, probe = _cli("probe", "grant")
        self.assertEqual(probe_process.returncode, 0, probe_process.stderr)
        self.assertEqual(probe.get("status"), "unavailable")
        self.assertEqual(probe.get("action_required"), "owner_authorization")

        journey_process, journey = _cli("journey", "grant")
        self.assertEqual(journey_process.returncode, 3)
        self.assertEqual(journey.get("status"), "blocked")
        self.assertEqual(journey.get("action_required"), "owner_authorization")

        self.assertEqual((self.target / "external-grant.json").read_bytes(), grant_before)
        self.assertEqual((self.target / "authorization.json").read_bytes(), authorization_before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
