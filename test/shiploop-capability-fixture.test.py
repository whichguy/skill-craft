#!/usr/bin/env python3
"""Focused public-contract regressions for the capability-study r2 fixture."""

from __future__ import annotations

from contextlib import redirect_stdout
import http.client
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "test" / "experiments" / "shiploop_capabilities"
FIXTURES = EXPERIMENTS / "fixtures"
if str(FIXTURES) not in sys.path:
    sys.path.insert(0, str(FIXTURES))
if str(EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS))

from app import (  # noqa: E402
    AUTHORITATIVE_RECEIPTS_ENV,
    DEFAULT_ACTOR_TOKENS,
    FIXTURE_REVISION,
    Store,
    default_state,
    start_server,
    write_state,
)
import fixture_setup  # noqa: E402
import grade  # noqa: E402


_NO_BODY = object()


class CapabilityFixtureContractTests(unittest.TestCase):
    """Use a real loopback server; fixture worker tests intentionally stay thin."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="shiploop-capability-fixture-r2-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        write_state(self.workspace / "state.json", default_state())
        self.receipt_dir = self.root / "coordinator-receipts"
        self.receipt_dir.mkdir()
        self.receipt_path = self.receipt_dir / "service-http-receipts.jsonl"
        self.actor_tokens = {
            **DEFAULT_ACTOR_TOKENS,
            "red-readonly-token": {"actor": "red", "scopes": ["checkers:read"]},
        }
        self.environment = patch.dict(
            os.environ,
            {AUTHORITATIVE_RECEIPTS_ENV: str(self.receipt_path)},
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.running = None
        self._start_server()
        self.addCleanup(self._stop_server)

    def _start_server(self) -> None:
        self.store = Store(
            self.workspace,
            service_config={"requiredScope": "checkers:write", "cacheTtlSeconds": 0},
            actor_tokens=self.actor_tokens,
            observation_dir=self.workspace / "runtime-observations",
        )
        self.running = start_server(self.store)

    def _stop_server(self) -> None:
        if self.running is not None:
            self.running.stop()
            self.running = None

    def _request(
        self,
        method: str,
        route: str,
        *,
        body: object = _NO_BODY,
        token: str | None = None,
    ) -> tuple[int, dict[str, object]]:
        assert self.running is not None
        connection = http.client.HTTPConnection("127.0.0.1", self.running.server.server_port, timeout=3)
        headers: dict[str, str] = {}
        encoded: str | None = None
        if body is not _NO_BODY:
            encoded = json.dumps(body, separators=(",", ":"))
            headers["Content-Type"] = "application/json"
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        try:
            connection.request(method, route, body=encoded, headers=headers)
            response = connection.getresponse()
            raw = response.read()
        finally:
            connection.close()
        payload = json.loads(raw)
        self.assertIsInstance(payload, dict)
        return response.status, payload

    def _state(self) -> dict[str, object]:
        status, payload = self._request("GET", "/api/state")
        self.assertEqual(200, status)
        return payload

    def _fresh_public_state(self) -> dict[str, object]:
        """Avoid relying on a cache held by the server that processed the request."""

        self._stop_server()
        self._start_server()
        return self._state()

    @staticmethod
    def _move_body(actor: object, *, key: str) -> dict[str, object]:
        return {
            "actor": actor,
            "from": "b2",
            "to": "c3",
            "expectedVersion": 1,
            "idempotencyKey": key,
        }

    def _authoritative_receipts(self) -> list[dict[str, object]]:
        if not self.receipt_path.exists():
            return []
        return [json.loads(line) for line in self.receipt_path.read_text(encoding="utf-8").splitlines()]

    def test_malformed_actor_json_is_400_and_a_fresh_public_reader_sees_no_write(self) -> None:
        before = self._state()
        for label, actor in (("list", []), ("object", {})):
            with self.subTest(label=label):
                status, payload = self._request(
                    "POST",
                    "/api/move",
                    body=self._move_body(actor, key=f"malformed-actor-{label}"),
                    token="red-fixture-token",
                )
                self.assertEqual(400, status)
                self.assertEqual("invalid_actor", payload.get("error"))
                self.assertEqual(before, self._fresh_public_state())

        for label, body in (("array", []), ("string", "not-an-object"), ("null", None)):
            with self.subTest(label=label):
                status, payload = self._request(
                    "POST", "/api/move", body=body, token="red-fixture-token"
                )
                self.assertEqual(400, status)
                self.assertEqual("invalid_json", payload.get("error"))
                self.assertEqual(before, self._fresh_public_state())

    def test_normalization_precedes_auth_and_workspace_logs_redact_untrusted_values(self) -> None:
        before = self._state()
        secret_actor = "private-actor-value"
        secret_coordinate = "private-coordinate-value"
        secret_key = "private-idempotency-value"
        secret_extra = "private-extra-body-value"

        status, payload = self._request(
            "POST",
            "/api/move",
            body={
                "actor": "red",
                "from": secret_coordinate,
                "to": "c3",
                "expectedVersion": 1,
                "idempotencyKey": secret_key,
                "untrustedExtra": secret_extra,
            },
        )
        self.assertEqual(400, status)
        self.assertEqual("invalid_coordinate", payload.get("error"))
        self.assertEqual(before, self._fresh_public_state())

        status, payload = self._request(
            "POST",
            "/api/move",
            body={
                "actor": secret_actor,
                "from": "b2",
                "to": "c3",
                "expectedVersion": 1,
                "idempotencyKey": secret_key,
                "untrustedExtra": secret_extra,
            },
        )
        self.assertEqual(400, status)
        self.assertEqual("invalid_actor", payload.get("error"))
        self.assertEqual(before, self._fresh_public_state())

        self._stop_server()
        events = (self.workspace / "runtime-observations" / "events.jsonl").read_text(encoding="utf-8")
        for secret in (secret_actor, secret_coordinate, secret_key, secret_extra):
            self.assertNotIn(secret, events)
        self.assertIn('"error": "invalid_coordinate"', events)
        self.assertIn('"error": "invalid_actor"', events)

    def test_scope_denial_has_an_allowlisted_external_receipt_and_unchanged_persistence(self) -> None:
        before = self._state()
        status, payload = self._request(
            "POST",
            "/api/move",
            body=self._move_body("red", key="scope-denied-visible-key"),
            token="red-readonly-token",
        )
        self.assertEqual(403, status)
        self.assertEqual("scope_required", payload.get("error"))
        self.assertEqual(before, self._fresh_public_state())

        status, meta = self._request("GET", "/api/meta")
        self.assertEqual(200, status)
        self.assertEqual(
            {"configured": True, "available": True, "error": None},
            meta.get("authoritativeHttpReceipt"),
        )
        receipt = next(
            record
            for record in self._authoritative_receipts()
            if record.get("status") == 403 and record.get("error") == "scope_required"
        )
        self.assertEqual(
            {
                "event",
                "receipt_id",
                "method",
                "route",
                "actor_class",
                "status",
                "error",
                "version_before",
                "version_after",
            },
            set(receipt),
        )
        self.assertRegex(str(receipt["receipt_id"]), r"^http-\d{6}$")
        self.assertEqual("POST", receipt["method"])
        self.assertEqual("/api/move", receipt["route"])
        self.assertEqual("red", receipt["actor_class"])
        self.assertEqual(1, receipt["version_before"])
        self.assertEqual(1, receipt["version_after"])
        serialized = json.dumps(receipt, sort_keys=True)
        self.assertNotIn("scope-denied-visible-key", serialized)
        self.assertNotIn("red-readonly-token", serialized)
        self.assertNotIn("Authorization", serialized)

    def test_unavailable_configured_receipt_is_exposed_without_the_path(self) -> None:
        self._stop_server()
        unsafe_path = self.workspace / "runtime-observations" / "wrong-place.jsonl"
        with patch.dict(os.environ, {AUTHORITATIVE_RECEIPTS_ENV: str(unsafe_path)}):
            store = Store(self.workspace)
            try:
                status = store.meta()["authoritativeHttpReceipt"]
            finally:
                store.close()
        self.assertEqual(
            {
                "configured": True,
                "available": False,
                "error": "receipt_path_inside_state_workspace",
            },
            status,
        )
        self.assertNotIn(str(unsafe_path), json.dumps(status, sort_keys=True))

    def test_case_layout_clears_ambient_receipts_until_explicitly_configured(self) -> None:
        self._stop_server()
        implicit = fixture_setup.create_case("TEST", self.root / "case-implicit-receipt")
        running = implicit.start()
        try:
            with urlopen(running.url + "/api/meta", timeout=2) as response:  # noqa: S310 - loopback fixture
                meta = json.loads(response.read())
        finally:
            running.stop()
        self.assertEqual(
            {"configured": False, "available": False, "error": None},
            meta["authoritativeHttpReceipt"],
        )

        explicit_path = self.root / "case-layout-explicit-receipts.jsonl"
        explicit = fixture_setup.create_case("TEST", self.root / "case-explicit-receipt")
        running = explicit.start(authoritative_receipt_path=explicit_path)
        try:
            with urlopen(running.url + "/api/meta", timeout=2) as response:  # noqa: S310 - loopback fixture
                meta = json.loads(response.read())
        finally:
            running.stop()
        self.assertEqual(
            {"configured": True, "available": True, "error": None},
            meta["authoritativeHttpReceipt"],
        )

    def test_create_case_rejects_nonempty_workspace(self) -> None:
        workspace = self.root / "case-with-old-artifacts"
        workspace.mkdir()
        (workspace / "old-receipt.json").write_text("old", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            fixture_setup.create_case("TEST", workspace)

    def test_grader_clears_ambient_receipt_paths_until_a_run_explicitly_sets_one(self) -> None:
        self._stop_server()
        sentinel = self.root / "ambient-receipt-sentinel.jsonl"
        intentional = self.root / "intentional-grader-receipt.jsonl"
        worker_root = self.root / "ambient-worker-tests"
        tests = worker_root / "tests"
        tests.mkdir(parents=True)
        shutil.copy2(FIXTURES / "test_app.py", tests / "test_app.py")
        with patch.dict(os.environ, {AUTHORITATIVE_RECEIPTS_ENV: str(sentinel)}):
            scored = grade.run_checks(
                FIXTURES / "app.py",
                self.root / "ambient-http-oracle",
                selected=("black_followup",),
            )
            worker = grade.run_worker_tests(
                tests_root=worker_root,
                app_path=FIXTURES / "app.py",
                app_relative="app.py",
                command_template=None,
            )
            intentional_run = grade.run_checks(
                FIXTURES / "app.py",
                self.root / "intentional-http-oracle",
                selected=("black_followup",),
                authoritative_receipt_path=intentional,
            )
        self.assertTrue(scored["passed"], scored)
        self.assertTrue(worker["passed"], worker)
        self.assertTrue(intentional_run["passed"], intentional_run)
        self.assertFalse(sentinel.exists())
        self.assertTrue(intentional.exists())

    def test_scored_http_stale_check_accepts_a_response_without_current_version_metadata(self) -> None:
        status, first = self._request(
            "POST",
            "/api/move",
            body=self._move_body("red", key="stale-baseline"),
            token="red-fixture-token",
        )
        self.assertEqual(200, status)
        self.assertEqual(2, first.get("version"))
        stale = {
            "actor": "black",
            "from": "g7",
            "to": "f6",
            "expectedVersion": 1,
            "idempotencyKey": "stale-omits-current-version",
        }
        status, payload = self._request("POST", "/api/move", body=stale, token="black-fixture-token")
        self.assertEqual(409, status)
        self.assertEqual("version_mismatch", payload.get("error"))
        self.assertNotIn("currentVersion", payload)

        self._stop_server()
        scored = grade.run_checks(
            FIXTURES / "app.py",
            self.root / "stale-public-oracle",
            selected=("stale_version",),
        )
        self.assertTrue(scored["passed"], scored)
        self.assertTrue(scored["scored"], scored)
        self.assertEqual("loopback_http", scored["transport"])

    def test_http_calibration_detects_every_baked_mutant_and_the_test_gate_rejects_bad_reference(self) -> None:
        self._stop_server()
        mutants_dir = self.root / "mutants"
        mutants = {
            name: fixture_setup.materialize_mutant(name, mutants_dir / f"{name}.py")
            for name in fixture_setup.MUTANTS
        }
        receipt = self.root / "evidence-grade-calibration.json"
        argv = [str(grade.__file__), "--mode", "calibration", "--output", str(receipt)]
        for name in fixture_setup.MUTANTS:
            argv.extend(("--mutant", f"{name}={mutants[name]}"))
        with patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()):
            self.assertEqual(0, grade.main())
        calibration = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertTrue(calibration["passed"], calibration)
        self.assertTrue(calibration["evidence_grade"], calibration)
        self.assertEqual("evidence_grade_passed", calibration["verdict"])
        self.assertTrue(calibration["reference_valid"], calibration)
        self.assertFalse(calibration["invalid_reference"], calibration)
        self.assertEqual("loopback_http", calibration["baseline"]["transport"])
        self.assertEqual(set(fixture_setup.MUTANTS), set(calibration["mutants"]))
        self.assertTrue(all(item["detected"] for item in calibration["mutants"].values()), calibration)
        self.assertEqual(set(fixture_setup.MUTANTS), set(calibration["expected_families"]))
        self.assertTrue(calibration["source_validation"]["valid"], calibration)
        self.assertFalse(calibration["workspace_retention"]["retained_after_run"])
        self.assertEqual("temporary_cleaned", calibration["workspace_retention"]["disposition"])
        bindings = calibration["input_bindings"]
        self.assertEqual("public_spec", bindings["spec"]["kind"])
        self.assertEqual("fixture_setup", bindings["fixture_setup"]["kind"])
        self.assertEqual(64, len(bindings["reference"]["sha256"]))
        self.assertEqual(set(fixture_setup.MUTANTS), set(bindings["mutants"]))
        self.assertTrue(all(item["source_sha256"] for item in calibration["mutants"].values()))

        worker_root = self.root / "worker-tests"
        tests = worker_root / "tests"
        tests.mkdir(parents=True)
        shutil.copy2(FIXTURES / "test_app.py", tests / "test_app.py")
        bad_reference = self.root / "bad-reference.py"
        source = (FIXTURES / "app.py").read_text(encoding="utf-8")
        changed = source.replace(
            "return Outcome(200, response)",
            "return Outcome(500, {\"error\": \"internal_error\"})",
            1,
        )
        self.assertNotEqual(source, changed)
        bad_reference.write_text(changed, encoding="utf-8")
        gate = grade.grade_test(
            reference=bad_reference,
            mutants={"wrong_actor": mutants["wrong_actor"]},
            tests_root=worker_root,
            app_relative="app.py",
            command_template=None,
        )
        self.assertFalse(gate["passed"], gate)
        self.assertFalse(gate["score_valid"], gate)
        self.assertEqual("invalid_reference", gate["verdict"])
        self.assertEqual({}, gate["mutants"])

    def test_selector_calibration_is_diagnostic_not_evidence_grade(self) -> None:
        self._stop_server()
        diagnostic = grade.grade_calibration(FIXTURES / "app.py", self.root / "selector-diagnostic")
        self.assertFalse(diagnostic["passed"], diagnostic)
        self.assertFalse(diagnostic["evidence_grade"], diagnostic)
        self.assertTrue(diagnostic["diagnostic_passed"], diagnostic)
        self.assertEqual("diagnostic_selector_calibration", diagnostic["verdict"])
        self.assertEqual(
            "reference_runtime_defect_selector",
            diagnostic["mutants"]["wrong_actor"]["source_kind"],
        )
        self.assertEqual(
            diagnostic["input_bindings"]["reference"]["sha256"],
            diagnostic["mutants"]["wrong_actor"]["source_sha256"],
        )

    def test_test_gate_rejects_partial_unknown_and_aliased_mutant_sources(self) -> None:
        self._stop_server()
        mutants_dir = self.root / "selection-mutants"
        mutants = {
            name: fixture_setup.materialize_mutant(name, mutants_dir / f"{name}.py")
            for name in fixture_setup.MUTANTS
        }
        worker_root = self.root / "selection-worker-tests"
        tests = worker_root / "tests"
        tests.mkdir(parents=True)
        shutil.copy2(FIXTURES / "test_app.py", tests / "test_app.py")
        common = {
            "reference": FIXTURES / "app.py",
            "tests_root": worker_root,
            "app_relative": "app.py",
            "command_template": None,
        }

        partial = grade.grade_test(mutants={"wrong_actor": mutants["wrong_actor"]}, **common)
        self.assertFalse(partial["passed"], partial)
        self.assertFalse(partial["score_valid"], partial)
        self.assertEqual("incomplete_mutant_set", partial["verdict"])
        self.assertIn("duplicate", partial["source_validation"]["missing_families"])

        unknown = grade.grade_test(mutants={"not_a_family": mutants["wrong_actor"]}, **common)
        self.assertFalse(unknown["passed"], unknown)
        self.assertFalse(unknown["score_valid"], unknown)
        self.assertEqual("invalid_mutant_set", unknown["verdict"])
        self.assertEqual(["not_a_family"], unknown["source_validation"]["unexpected_families"])

        aliases = dict(mutants)
        aliases["stale"] = mutants["duplicate"]
        duplicate = grade.grade_test(mutants=aliases, **common)
        self.assertFalse(duplicate["passed"], duplicate)
        self.assertFalse(duplicate["score_valid"], duplicate)
        self.assertEqual("invalid_mutant_set", duplicate["verdict"])
        self.assertTrue(any("aliases" in error for error in duplicate["source_validation"]["errors"]))

        reference_alias = dict(mutants)
        reference_alias["wrong_actor"] = FIXTURES / "app.py"
        reference_equal = grade.grade_test(mutants=reference_alias, **common)
        self.assertFalse(reference_equal["passed"], reference_equal)
        self.assertFalse(reference_equal["score_valid"], reference_equal)
        self.assertEqual("invalid_mutant_set", reference_equal["verdict"])
        self.assertTrue(
            any("equals the reference" in error for error in reference_equal["source_validation"]["errors"])
        )

    def test_reference_and_generated_metadata_are_explicitly_r2(self) -> None:
        self.assertEqual("fixture-r2", FIXTURE_REVISION)
        case_root = self.root / "case"
        fixture_setup.create_case("TEST", case_root)
        manifest = json.loads((case_root / "fixture-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("fixture-r2", manifest["fixtureContractRevision"])
        self.assertEqual("inspection-only-untrusted", manifest["workspaceObservations"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
