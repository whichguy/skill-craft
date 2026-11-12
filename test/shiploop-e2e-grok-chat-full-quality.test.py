#!/usr/bin/env python3
"""Calibrate the independent quality gate; no model, org or browser calls."""
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import importlib.util
import inspect
import io
import json
import os
import re
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "test/shiploop_e2e/checks/grok_chat_full_quality.py"
spec = importlib.util.spec_from_file_location("grok_quality", PATH)
quality = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quality)
ui_fixtures = runpy.run_path(str(ROOT / "test/shiploop-e2e-grok-chat-full-ui.test.py"))
positive_observation = ui_fixtures["positive_observation"]
run_guarded_sf = ui_fixtures["run_guarded_sf"]

BROWSER_BASE_MS = 1794182400000  # 2026-11-09T00:00:00Z
USER_ID = "005000000000001AAA"
TRACE_ID = "7tf000000000001AAA"


def stamp(milliseconds):
    return datetime.fromtimestamp(milliseconds // 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class QualityBudgetTest(unittest.TestCase):
    def test_full_observation_budget_is_2700_in_helper_catalog_and_guide(self):
        cases = json.loads((ROOT / "test/shiploop_e2e/cases.json").read_text())
        guide = (ROOT / "test/shiploop_e2e/GROK_CHAT_FULL.md").read_text()
        budgets = {
            "helper": quality.CHECK_SECONDS,
            "run default": inspect.signature(quality.run).parameters["wait_seconds"].default,
            "full case": cases["grok-chat-salesforce-full"]["platform"]["check_timeout"],
            "public guide": [int(value) for value in re.findall(r"(\d+)-second hosted-check budget", guide)],
        }
        for location, value in budgets.items():
            with self.subTest(location=location):
                self.assertEqual(value, [2700] if location == "public guide" else 2700)

    def test_other_cases_remain_identical_to_owner_budget_change_base(self):
        cases = json.loads((ROOT / "test/shiploop_e2e/cases.json").read_text())
        del cases["grok-chat-salesforce-full"]
        # Canonical catalog excluding only the full case at bb741347a74d170c260bc524379967028ba4d5c6.
        digest = hashlib.sha256(json.dumps(cases, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(digest, "25ae51d25ff04aa420ba36098e7a8e06fe6c832cc797e01c3d8996b86f118796")


class QualityGateTest(unittest.TestCase):
    def setUp(self):
        # Keep fixture clock patches from reaching subprocess's shared time module.
        self.addCleanup(setattr, quality, "time", quality.time)
        quality.time = SimpleNamespace(
            monotonic=time.monotonic, strftime=time.strftime, gmtime=time.gmtime, sleep=time.sleep,
        )
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.product = self.base / "work"
        self.product.mkdir()
        self.platform = self.base / "platform"
        self.platform.mkdir()
        subprocess.run(["git", "-C", str(self.product), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(self.product), "-c", "user.name=Fixture",
                        "-c", "user.email=fixture@example.invalid", "commit", "--allow-empty", "-qm", "fixture"], check=True)
        (self.product / "force-app").mkdir()
        (self.product / "sfdx-project.json").write_text('{"packageDirectories":[{"path":"force-app"}]}\n')
        (self.product / "force-app/Example.cls").write_text("public class Example {}\n")
        self.identity = quality.snapshot(self.product)
        self.directory = self.platform / "grok-chat-quality" / self.identity["sha256"]
        self.directory.mkdir(parents=True)

    def valid(self):
        raw = b"Independent review performed against the registered source.\n"
        (self.directory / "review-evidence.txt").write_bytes(raw)
        return {
            "schema": "shiploop-grok-chat-quality-review/1", "status": "PASS",
            "source_sha256": self.identity["sha256"],
            "reviewer": {"independent": True, "actor": "fixture-reviewer",
                         "execution_id": "fixture-review", "provenance": "calibration fixture"},
            "dimensions": {key: {"status": "PASS", "reason": "Fixture evidence"} for key in quality.DIMENSIONS},
            "findings": [],
            "evidence": [{"path": "review-evidence.txt", "sha256": hashlib.sha256(raw).hexdigest()}],
        }

    def deploy(self, call_id, *, full_package=True, exit_code=0, completed=True):
        metadata = quality.ui.sf_guard.force_app_sha256(self.product)
        rows = [{"ts": stamp(BROWSER_BASE_MS - 2000), "call": call_id,
                 "argv": ["project", "deploy", "start", "--source-dir", "force-app", "--target-org", "de"],
                 "decision": "allowed", "org": "de", "prefix": "SLGrokChat"}]
        if completed:
            rows.append({"ts": stamp(BROWSER_BASE_MS - 1000), "call": call_id,
                         "end": True, "exit": exit_code, "interrupted": False,
                         "source_binding": {"root": str(self.product), "before_sha256": metadata,
                                            "after_sha256": metadata, "full_package": full_package,
                                            "unchanged": True}})
        self.append_calls(*rows)
        return quality.ui._latest_successful_deploy(self.platform)

    def append_calls(self, *rows):
        with (self.platform / "sf-calls.jsonl").open("a") as ledger:
            for row in rows:
                ledger.write(json.dumps(row) + "\n")

    def start_deploy_help(self, call):
        self.append_calls({"call": call, "argv": ["project:deploy:start", "-h"], "decision": "allowed",
                           "org": quality.ui.EXPECTED_ORG, "prefix": quality.ui.PREFIX, "reason": "help"})

    def register_ui(self, number, phase="builder"):
        return quality.ui.register_ui_attempt(self.platform, phase, f"{number:032x}")

    def write_ui(self, deploy, number, *, phase="builder", directory=None, **changes):
        directory = directory or self.register_ui(number, phase)
        value = positive_observation(split_steps=("create-proposal", "stale-proposal"))
        value.update(
            phase=phase, check_id=directory.name, checked_at=stamp(BROWSER_BASE_MS), deployment=deploy,
            source_head=self.identity["head"], candidate_metadata_sha256=deploy["source_binding"]["after_sha256"],
            org={"org_id": quality.ui.EXPECTED_ORG_ID, "lightning_host": value["route_host"], "user_id": USER_ID},
        )
        for call in value["controller_calls"]:
            if "server_request_id" in call:
                call["server_request_id"] += f"-{number}"
                call["request_started_at"] = BROWSER_BASE_MS + call["request_started_at"] * 100 + 0.125
                call["response_completed_at"] = BROWSER_BASE_MS + call["response_completed_at"] * 100 + 0.375
        value.update(changes)
        path = directory / "observation.json"
        path.write_text(json.dumps(value))
        ns = (BROWSER_BASE_MS + number * 1000) * 1_000_000
        os.utime(directory, ns=(ns, ns))
        return path

    def live_requests(self):
        return list((self.directory / "live-acceptance").glob("*/request.json"))

    def live_receipt(self, request):
        identity = request["identity"]
        calls = request["browser_requests"]
        times = {"baseline": stamp(BROWSER_BASE_MS), "expires": stamp(BROWSER_BASE_MS + 60_000)}
        return {
            "schema": quality.LIVE_RECEIPT_SCHEMA, "identity": dict(identity),
            "trace_window": {"org_id": identity["org_id"], "user_id": identity["user_id"],
                             "trace_flag_id": TRACE_ID, **times},
            "joins": [{
                "method": call["method"], "request_id": call["request_id"],
                "request_started_at": call["started_ms"], "response_completed_at": call["completed_ms"],
                "log_id": f"07L{index:012d}AAA", "trace_flag_id": TRACE_ID,
                "org_id": identity["org_id"], "user_id": identity["user_id"], "window": dict(times),
                "native_request_id": "TID:" + call["request_id"],
                "body_sha256": hashlib.sha256(f"fixture-log-{index}".encode()).hexdigest(),
                "log_started_at": stamp(call["started_ms"]), "outcome": "HTTP_200",
                "endpoint": quality.ENDPOINT, "endpoint_kinds": ["HTTPS"],
            } for index, call in enumerate(calls)],
        }

    def run_quality(self, phase="builder", wait_seconds=0):
        output = io.StringIO()
        with redirect_stdout(output):
            code = quality.run(self.product, self.platform, phase, wait_seconds=wait_seconds)
        return code, output.getvalue()

    def public(self, operation, *, code=0, phase="builder"):
        def inventory():
            return {str(p.relative_to(self.base)): (p.lstat().st_mode, p.lstat().st_mtime_ns,
                    os.readlink(p) if p.is_symlink() else p.read_bytes())
                    for p in self.base.rglob("*") if p.is_symlink() or p.is_file()}
        before = inventory()
        result = subprocess.run([sys.executable, "-B", str(PATH), "--repo", str(self.product),
                                 operation, "--json"], capture_output=True, text=True, timeout=10,
                                env={**os.environ, "E2E_PLATFORM_DIR": str(self.platform),
                                     "E2E_CHECK_PHASE": phase})
        after = inventory()
        self.assertEqual([key for key in before if before[key] != after.get(key)], [])
        added = after.keys() - before.keys()
        if operation == "--assess-only":
            self.assertEqual(added, set(), "assessment wrote evidence")
        else:
            self.assertTrue(all(name.startswith("platform/grok-chat-quality/") and name.endswith("/request.json")
                                for name in added), added)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def platform_bytes(self):
        return {str(p.relative_to(self.platform)): p.read_bytes()
                for p in self.platform.rglob("*") if p.is_file()}

    def test_public_prepare_empty_commit_then_scoped_reassessment_preserves_failure(self):
        original = self.base / "result.json"
        original.write_bytes(b'{"pass":false,"failed":"quality"}\n')
        frozen = original.read_bytes()
        a = self.public("--prepare-only")
        request = Path(a["source_request"])
        historical = request.read_bytes()
        self.assertEqual(a["status"], "pending")
        deploy = self.deploy("12345678")
        self.write_ui(deploy, 1)
        subprocess.run(["git", "-C", str(self.product), "-c", "user.name=Fixture",
                        "-c", "user.email=fixture@example.invalid", "commit", "--allow-empty",
                        "-qm", "empty knowledge commit"], check=True)
        b = self.public("--prepare-only")
        self.assertEqual(request.read_bytes(), historical)
        self.assertNotEqual(b["current_source"]["head"], b["historical_source"]["head"])
        self.assertIsNone(b["live_request"])
        self.identity = quality.snapshot(self.product)
        self.write_ui(deploy, 2)
        b = self.public("--prepare-only")
        self.assertIsNotNone(b["live_request"])
        live_path = Path(b["live_request"])
        live = json.loads(live_path.read_bytes())
        live_path.with_name("receipt.json").write_text(json.dumps(self.live_receipt(live)))
        review = self.valid()
        review["status"] = "FAIL"
        (self.directory / "review.json").write_text(json.dumps(review))
        before = self.platform_bytes()
        failed = self.public("--assess-only", code=1)
        self.assertEqual(failed["status"], "FAIL")
        self.assertEqual(self.platform_bytes(), before)
        review["status"] = "PASS"
        (self.directory / "review.json").write_text(json.dumps(review))
        before = self.platform_bytes()
        passed = self.public("--assess-only")
        self.assertEqual(passed["status"], "PASS")
        self.assertEqual(passed["scope"], "current-source-quality-and-live-evidence")
        self.assertEqual(self.platform_bytes(), before)
        self.assertEqual(original.read_bytes(), frozen)
        self.assertEqual(request.read_bytes(), historical)

    def test_public_changed_tracked_untracked_and_ignored_deployable_need_review(self):
        self.public("--prepare-only")
        (self.directory / "review.json").write_text(json.dumps(self.valid()))
        self.deploy("12345678")
        self.write_ui(quality.ui._latest_successful_deploy(self.platform), 1)
        prepared = self.public("--prepare-only")
        path = Path(prepared["live_request"])
        path.with_name("receipt.json").write_text(json.dumps(self.live_receipt(json.loads(path.read_bytes()))))
        self.public("--assess-only")
        subprocess.run(["git", "-C", str(self.product), "add", "sfdx-project.json", "force-app"], check=True)
        for name in ("force-app/Example.cls", "extra.txt", "force-app/ignored.cls"):
            if name.endswith("ignored.cls"):
                (self.product / ".git/info/exclude").write_text("ignored.cls\n")
            target = self.product / name
            previous = target.read_bytes() if target.exists() else None
            target.write_text("changed deployable content\n")
            result = self.public("--prepare-only")
            self.assertNotEqual(result["current_source"]["sha256"], self.identity["sha256"])
            assessment = self.public("--assess-only", code=2)
            self.assertIn("independent-review-pending", assessment["pending"])
            if previous is None:
                target.unlink()
            else:
                target.write_bytes(previous)

    def test_public_malformed_or_unsafe_request_is_preserved_and_invalid(self):
        self.public("--prepare-only")
        path = self.directory / "request.json"
        valid = json.loads(path.read_bytes())
        for value in ("{", json.dumps({**valid, "schema": "wrong"}),
                      json.dumps({**valid, "source": {**valid["source"], "sha256": "0" * 64}})):
            path.write_text(value)
            result = self.public("--prepare-only", code=1)
            self.assertEqual(result["status"], "invalid")
            self.assertEqual(path.read_text(), value)
        path.unlink()
        path.symlink_to(self.product / "sfdx-project.json")
        self.public("--prepare-only", code=1)

    def test_public_newer_failed_incomplete_late_and_overlapping_evidence_withhold_old_credit(self):
        (self.directory / "review.json").write_text(json.dumps(self.valid()))
        deploy = self.deploy("12345678")
        old = self.write_ui(deploy, 1)
        prepared = self.public("--prepare-only")
        path = Path(prepared["live_request"])
        path.with_name("receipt.json").write_text(json.dumps(self.live_receipt(json.loads(path.read_bytes()))))
        self.public("--assess-only")
        self.register_ui(2)
        for changes in (None, {"status": "failed"}):
            if changes:
                self.write_ui(deploy, 2, directory=self.platform / "grok-chat-ui/builder" / f"{2:032x}", **changes)
            # Rewriting old completion does not change latest start order.
            old.write_bytes(old.read_bytes())
            self.assertIsNone(self.public("--prepare-only")["live_request"])
            self.public("--assess-only", code=2)
        self.write_ui(deploy, 3)
        current = self.public("--prepare-only")
        current_path = Path(current["live_request"])
        current_path.with_name("receipt.json").write_text(json.dumps(
            self.live_receipt(json.loads(current_path.read_bytes()))))
        self.public("--assess-only")
        self.deploy("bbbbbbbb", completed=False)
        self.assertIsNone(self.public("--prepare-only")["live_request"])
        self.public("--assess-only", code=2)
        self.deploy("cccccccc")  # B still active: C cannot establish serial remote order.
        self.write_ui(quality.ui._latest_successful_deploy(self.platform), 4)
        self.assertIsNone(self.public("--prepare-only")["live_request"])
        self.public("--assess-only", code=2)

    def test_public_busy_ui_ledger_is_nonblocking(self):
        import fcntl
        self.write_ui(self.deploy("12345678"), 1)
        ledger = self.platform / "grok-chat-ui/builder" / quality.ui.UI_ATTEMPT_LEDGER
        with ledger.open() as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.public("--prepare-only")
        self.assertIsNone(result["live_request"])
        self.assertIn("ui-evidence-busy", result["pending"])

    def test_public_assessment_clears_current_pointer_when_evidence_changes_during_validation(self):
        (self.directory / "review.json").write_text(json.dumps(self.valid()))
        self.write_ui(self.deploy("12345678"), 1)
        prepared = self.public("--prepare-only")
        path = Path(prepared["live_request"])
        path.with_name("receipt.json").write_text(json.dumps(self.live_receipt(json.loads(path.read_bytes()))))
        validator = quality.validate_live_receipt
        def supersede(receipt, request):
            self.register_ui(2)
            return validator(receipt, request)
        with mock.patch.object(quality, "validate_live_receipt", side_effect=supersede):
            with mock.patch.dict(os.environ, {"E2E_PLATFORM_DIR": str(self.platform), "E2E_CHECK_PHASE": "builder"}):
                with redirect_stdout(io.StringIO()) as output:
                    code = quality.main(["--repo", str(self.product), "--assess-only", "--json"])
        self.assertEqual(code, 1)
        result = json.loads(output.getvalue())
        self.assertIn("live-acceptance-evidence-changed", result["errors"])
        self.assertIsNone(result["live_request"])

    def test_publication_race_validates_winner_not_proposed_request(self):
        def competing(path, request):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"schema":"wrong"}')
        with mock.patch.object(quality, "write_request", side_effect=competing):
            with mock.patch.dict(os.environ, {"E2E_PLATFORM_DIR": str(self.platform), "E2E_CHECK_PHASE": "builder"}):
                with redirect_stdout(io.StringIO()) as output:
                    code = quality.main(["--repo", str(self.product), "--prepare-only", "--json"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue())["status"], "invalid")

    def test_assessment_clears_both_current_pointers_when_request_becomes_malformed(self):
        original = self.base / "result.json"
        original.write_bytes(b'{"pass":false,"failed":"original"}\n')
        frozen = original.read_bytes()
        (self.directory / "review.json").write_text(json.dumps(self.valid()))
        self.write_ui(self.deploy("12345678"), 1)
        prepared = self.public("--prepare-only")
        path = Path(prepared["live_request"])
        path.with_name("receipt.json").write_text(json.dumps(self.live_receipt(json.loads(path.read_bytes()))))
        self.assertEqual(self.public("--assess-only")["status"], "PASS")
        before = self.platform_bytes()
        validator = quality.validate_live_receipt

        def corrupt_after_validation(receipt, request):
            errors = validator(receipt, request)
            self.assertEqual(errors, [], 'race must start with valid live proof')
            path.write_bytes(b'{')
            return errors

        with mock.patch.object(quality, "validate_live_receipt", side_effect=corrupt_after_validation) as validate:
            result = quality.assess_current(self.product, self.platform, "builder")
        validate.assert_called_once()
        after = self.platform_bytes()
        self.assertEqual(after, {**before, path.relative_to(self.platform).as_posix(): b'{'})
        self.assertEqual(original.read_bytes(), frozen)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("evidence-changed-during-assessment", result["errors"])
        self.assertEqual((result["live_request"], result["live_identity"]), (None, None))

    def test_accepts_exact_current_joins_and_reuses_review_across_phases(self):
        (self.directory / "review.json").write_text(json.dumps(self.valid()))
        deploy = self.deploy("12345678")
        for number, phase in enumerate(("builder", "final"), 1):
            ui_path = self.write_ui(deploy, number, phase=phase)
            code, output = self.run_quality(phase)
            self.assertEqual(code, 2)
            self.assertEqual(len(self.live_requests()), number)
            request_path = next(path for path in self.live_requests() if json.loads(path.read_text())["phase"] == phase)
            self.assertIn(str(request_path), output)
            request = json.loads(request_path.read_text())
            self.assertEqual(request["identity"]["ui_receipt_sha256"], hashlib.sha256(ui_path.read_bytes()).hexdigest())
            self.assertEqual([call["method"] for call in request["browser_requests"]], [
                "testConnection", "sendMessage", "executePendingMessage", "sendMessage", "sendMessage",
                "executePendingMessage",
            ])
            self.assertTrue(all(call["request_id"].endswith(f"-{number}") for call in request["browser_requests"]))
            # Order is incidental. Exact request ID and one distinct log per join are decisive.
            receipt = self.live_receipt(request)
            receipt["joins"].reverse()
            request_path.with_name("receipt.json").write_text(json.dumps(receipt))
            self.assertEqual(self.run_quality(phase)[0], 0)
            source_request = (self.directory / "request.json").read_bytes()
            if phase == "builder":
                first_request = source_request
            else:
                self.assertEqual(source_request, first_request)

    def test_prior_review_and_deployment_joins_cannot_supply_a_new_deploy(self):
        (self.directory / "review.json").write_text(json.dumps(self.valid()))
        self.write_ui(self.deploy("aaaaaaaa"), 1)
        self.assertEqual(self.run_quality()[0], 2)
        (first,) = self.live_requests()
        original_request = first.read_bytes()
        receipt_a = self.live_receipt(json.loads(original_request))
        first.with_name("receipt.json").write_text(json.dumps(receipt_a))
        self.assertEqual(self.run_quality()[0], 0)

        deploy_b = self.deploy("bbbbbbbb")
        self.assertEqual(self.run_quality()[0], 2)  # The existing UI still points at A.
        self.assertEqual(self.live_requests(), [first])
        self.write_ui(deploy_b, 2)
        self.assertEqual(self.run_quality()[0], 2)
        (second,) = set(self.live_requests()) - {first}
        request_b = json.loads(second.read_bytes())
        self.assertEqual(request_b["identity"]["deployment_call_id"], "bbbbbbbb")
        self.assertEqual(request_b["identity"]["source_sha256"], receipt_a["identity"]["source_sha256"])
        # Even an operator writing A's receipt to B's callback cannot select old evidence.
        second.with_name("receipt.json").write_text(json.dumps(receipt_a))
        code, output = self.run_quality()
        self.assertEqual(code, 1)
        self.assertIn("live-acceptance-identity-mismatch", output)
        self.assertEqual(quality.validate_live_receipt({**receipt_a, "identity": request_b["identity"]}, request_b),
                         ["live-acceptance-request-mismatch"])
        self.assertEqual(first.read_bytes(), original_request)
        self.assertEqual(json.loads(first.with_name("receipt.json").read_bytes()), receipt_a)

    def test_missing_review_is_incomplete_and_retains_request(self):
        code, output = self.run_quality()
        self.assertEqual(code, 2)
        self.assertIn(str(self.directory / "live-acceptance/*/request.json"), output)
        request = json.loads((self.directory / "request.json").read_text())
        self.assertEqual(request["source"]["sha256"], self.identity["sha256"])

    def test_default_budget_expires_with_missing_evidence_still_unknown(self):
        for review_present in (False, True):
            with self.subTest(review_present=review_present):
                if review_present:
                    (self.directory / "review.json").write_text(json.dumps(self.valid()))
                # Jump near the deadline, then exercise the final bounded poll.
                with (mock.patch.object(quality.time, "monotonic", side_effect=[0, 2699, 2700]),
                      mock.patch.object(quality.time, "sleep") as sleep, redirect_stdout(io.StringIO()) as output):
                    code = quality.run(self.product, self.platform, "builder")
                self.assertEqual(code, 2, output.getvalue())
                self.assertIn("live-acceptance-pending", output.getvalue())
                self.assertEqual("independent-review-pending" in output.getvalue(), not review_present)
                sleep.assert_called_once_with(1)
                result = json.loads((self.directory / "check-builder.json").read_text())
                self.assertEqual(result["status"], "UNKNOWN")
                self.assertEqual(result["errors"], [])

    def test_actionable_findings_are_reported_without_ui_or_deployment(self):
        review = self.valid()
        review["findings"].append({"actionable": True, "message": "Missing authorization check"})
        path = self.directory / "review.json"
        for status in ("PASS", "FAIL"):
            with self.subTest(status=status):
                review["status"] = status
                path.write_text(json.dumps(review))
                with mock.patch.object(quality.time, "sleep", side_effect=AssertionError("current review failed")):
                    code, output = self.run_quality(wait_seconds=quality.CHECK_SECONDS)
                self.assertEqual(code, 1)
                self.assertIn("actionable-findings-remain", output)
                if status == "FAIL":
                    self.assertIn("review-not-passed", output)
                self.assertIn(str(path), output)
                self.assertEqual(json.loads(path.read_bytes()), review)

    def test_live_request_can_start_while_source_review_is_pending(self):
        self.write_ui(self.deploy("aaaaaaaa"), 1)
        self.assertEqual(self.run_quality()[0], 2)
        (request_path,) = self.live_requests()
        receipt = self.live_receipt(json.loads(request_path.read_bytes()))
        request_path.with_name("receipt.json").write_text(json.dumps(receipt))
        self.assertEqual(self.run_quality()[0], 2)

    def test_incomplete_or_failed_latest_deploy_blocks_old_ui(self):
        (self.directory / "review.json").write_text(json.dumps(self.valid()))
        self.write_ui(self.deploy("aaaaaaaa"), 1)
        self.assertEqual(self.run_quality()[0], 2)
        (old_request,) = self.live_requests()
        old_request.with_name("receipt.json").write_text(json.dumps(self.live_receipt(json.loads(old_request.read_bytes()))))
        for call_id, fields in (("bbbbbbbb", {"completed": False}), ("cccccccc", {"exit_code": 1}),
                                ("dddddddd", {"full_package": False})):
            with self.subTest(fields=fields):
                deploy = self.deploy(call_id, **fields)
                if deploy:
                    self.write_ui(deploy, int(call_id[0], 16))
                self.assertEqual(self.run_quality()[0], 2)
                self.assertEqual(self.live_requests(), [old_request])

    def test_overlapping_deploys_need_a_subsequent_serial_deploy(self):
        self.deploy("aaaaaaaa", completed=False)
        deploy_b = self.deploy("bbbbbbbb")
        self.write_ui(deploy_b, 1)
        self.assertEqual(self.run_quality()[0], 2)
        self.assertEqual(self.live_requests(), [])
        with (self.platform / "sf-calls.jsonl").open("a") as ledger:
            ledger.write(json.dumps({"call": "aaaaaaaa", "end": True, "exit": 0, "interrupted": False}) + "\n")
        self.assertEqual(self.run_quality()[0], 2)
        self.assertEqual(self.live_requests(), [])
        self.write_ui(self.deploy("cccccccc"), 2)
        self.assertEqual(self.run_quality()[0], 2)
        self.assertEqual(len(self.live_requests()), 1)

    def test_unpinned_deploy_help_preserves_exact_live_request(self):
        deploy = self.deploy("aaaaaaaa")
        self.write_ui(deploy, 1)
        request = quality.live_request(self.product, self.platform, "builder", self.identity)
        self.assertIsNotNone(request)
        self.assertEqual(request["identity"]["deployment_call_id"], deploy["call_id"])

        argv = ["project", "deploy", "start", "--help"]
        run_guarded_sf(self, self.product, self.platform, argv)
        rows = (self.platform / "sf-calls.jsonl").read_text().splitlines()
        start, end = map(json.loads, rows[-2:])
        self.assertEqual(start["argv"], argv)
        self.assertEqual((start["decision"], start["reason"]), ("allowed", "help"))
        self.assertEqual(end["call"], start["call"])
        self.assertIs(end["end"], True)
        self.assertEqual(end["exit"], 0)
        self.assertNotIn("source_binding", end)
        self.assertEqual(quality.live_request(self.product, self.platform, "builder", self.identity), request)

    def test_open_deploy_help_does_not_overlap_real_deployment(self):
        self.start_deploy_help("aaaaaaaa")
        self.assertIsNone(quality.ui._latest_successful_deploy(self.platform))
        deploy = self.deploy("bbbbbbbb")
        self.write_ui(deploy, 1)
        self.assertTrue(quality.deploy_started_without_overlap(self.platform, deploy["call_id"]))
        request = quality.live_request(self.product, self.platform, "builder", self.identity)
        self.assertIsNotNone(request)
        self.assertEqual(request["identity"]["deployment_call_id"], "bbbbbbbb")

    def test_deploy_help_preserves_real_overlap_until_a_serial_deployment(self):
        self.deploy("aaaaaaaa", completed=False)
        self.start_deploy_help("bbbbbbbb")
        overlapping = self.deploy("cccccccc")
        self.write_ui(overlapping, 1)
        self.append_calls({"call": "bbbbbbbb", "end": True, "exit": 0, "interrupted": False},
                          {"call": "aaaaaaaa", "end": True, "exit": 0, "interrupted": False})
        run_guarded_sf(self, self.product, self.platform, ["project", "deploy", "start", "--help"])
        self.assertFalse(quality.deploy_started_without_overlap(self.platform, "cccccccc"))
        self.assertIsNone(quality.live_request(self.product, self.platform, "builder", self.identity))
        selected_after_help = quality.ui._latest_successful_deploy(self.platform)

        serial = self.deploy("dddddddd")
        self.write_ui(serial, 2)
        request = quality.live_request(self.product, self.platform, "builder", self.identity)
        self.assertIsNotNone(request)
        self.assertEqual(request["identity"]["deployment_call_id"], "dddddddd")
        self.assertEqual(selected_after_help, overlapping)

    def test_deploy_help_preserves_newest_ui_attempt_invalidation(self):
        deploy = self.deploy("aaaaaaaa")
        run_guarded_sf(self, self.product, self.platform, ["project", "deploy", "start", "--help"])
        for number, changes in enumerate(({"status": "failed"}, {"chat_turns": []}, {"mode": "observe"}), 1):
            with self.subTest(changes=changes):
                self.write_ui(deploy, number * 2)
                self.assertIsNotNone(quality.live_request(self.product, self.platform, "builder", self.identity))
                self.write_ui(deploy, number * 2 + 1, **changes)
                self.assertIsNone(quality.live_request(self.product, self.platform, "builder", self.identity))
        self.write_ui(deploy, 8)
        self.assertIsNotNone(quality.live_request(self.product, self.platform, "builder", self.identity))
        self.register_ui(9)
        self.assertIsNone(quality.live_request(self.product, self.platform, "builder", self.identity))

    def test_new_failed_or_incomplete_ui_attempt_cannot_fall_back(self):
        (self.directory / "review.json").write_text(json.dumps(self.valid()))
        deploy = self.deploy("aaaaaaaa")
        self.write_ui(deploy, 1)
        self.assertEqual(self.run_quality()[0], 2)
        (old_request,) = self.live_requests()
        old_request.with_name("receipt.json").write_text(json.dumps(self.live_receipt(json.loads(old_request.read_bytes()))))
        for number, changes in enumerate(({"status": "failed"}, {"chat_turns": []}, {"mode": "observe"}), 2):
            with self.subTest(changes=changes):
                self.write_ui(deploy, number, **changes)
                self.assertEqual(self.run_quality()[0], 2)
                self.assertEqual(self.live_requests(), [old_request])
        self.register_ui(5)
        self.assertEqual(self.run_quality()[0], 2)
        self.assertEqual(self.live_requests(), [old_request])

    def test_late_completion_cannot_override_newer_ui_start(self):
        (self.directory / "review.json").write_text(json.dumps(self.valid()))
        deploy = self.deploy("aaaaaaaa")
        for older, newer, failed in ((1, 2, False), (3, 4, True)):
            with self.subTest(failed=failed):
                prior = set(self.live_requests())
                attempt_a = self.register_ui(older)
                attempt_b = self.register_ui(newer)
                if failed:
                    self.write_ui(deploy, newer, directory=attempt_b, status="failed")
                path_a = self.write_ui(deploy, older, directory=attempt_a)
                b_ns = (BROWSER_BASE_MS + newer * 1000) * 1_000_000
                a_ns = b_ns + 1_000_000_000
                os.utime(attempt_b, ns=(b_ns, b_ns))
                os.utime(attempt_a, ns=(a_ns, a_ns))
                # Supply a valid A callback so that choosing A would earn a pass.
                with mock.patch.object(quality, "latest_ui_path", return_value=path_a):
                    self.assertEqual(self.run_quality()[0], 2)
                    (request_a,) = set(self.live_requests()) - prior
                    receipt_a = self.live_receipt(json.loads(request_a.read_bytes()))
                    request_a.with_name("receipt.json").write_text(json.dumps(receipt_a))
                    self.assertEqual(self.run_quality()[0], 0)
                self.assertEqual(self.run_quality()[0], 2)
                self.assertEqual(set(self.live_requests()), prior | {request_a})

    def test_unregistered_and_malformed_ui_evidence_is_nonpass(self):
        (self.directory / "review.json").write_text(json.dumps(self.valid()))
        deploy = self.deploy("aaaaaaaa")
        attempt_a = self.write_ui(deploy, 1)
        self.assertEqual(self.run_quality()[0], 2)
        (request_a,) = self.live_requests()
        request_a.with_name("receipt.json").write_text(json.dumps(self.live_receipt(json.loads(request_a.read_bytes()))))
        self.assertEqual(self.run_quality()[0], 0)

        phase_dir = attempt_a.parent.parent
        ledger = phase_dir / quality.ui.UI_ATTEMPT_LEDGER
        registered = ledger.read_text()
        ledger.unlink()
        self.assertEqual(self.run_quality()[0], 2)
        ledger.write_text(registered)
        unregistered = phase_dir / f"{2:032x}"
        unregistered.mkdir()
        self.write_ui(deploy, 2, directory=unregistered)
        self.assertEqual(self.run_quality()[0], 2)
        (unregistered / "observation.json").unlink()
        unregistered.rmdir()
        for bad_line in ("invalid\n", f"{2:032x}", registered):
            with self.subTest(bad_line=bad_line):
                ledger.write_text(registered + bad_line)
                self.assertEqual(self.run_quality()[0], 2)
        self.assertEqual(self.live_requests(), [request_a])

    def test_wrong_identity_window_request_and_closed_fields_are_rejected(self):
        self.write_ui(self.deploy("aaaaaaaa"), 1)
        self.assertEqual(self.run_quality()[0], 2)
        (request_path,) = self.live_requests()
        request = json.loads(request_path.read_bytes())
        for field in request["identity"]:
            with self.subTest(identity_field=field):
                receipt = self.live_receipt(request)
                receipt["identity"][field] = "f" * len(request["identity"][field])
                self.assertEqual(quality.validate_live_receipt(receipt, request), ["live-acceptance-identity-mismatch"])
        for key, value, reason in (
            ("org_id", "00D000000000002AAA", "trace-window"),
            ("user_id", "005000000000002AAA", "trace-window"),
            ("trace_flag_id", "7tf000000000002AAA", "trace-window"),
            ("baseline", stamp(BROWSER_BASE_MS + 4000), "join-time"),
            ("expires", stamp(BROWSER_BASE_MS + 4000), "join-time"),
        ):
            with self.subTest(window_field=key):
                receipt = self.live_receipt(request)
                receipt["trace_window"][key] = value
                if key in ("baseline", "expires"):
                    for join in receipt["joins"]:
                        join["window"][key] = value
                self.assertEqual(quality.validate_live_receipt(receipt, request), ["live-acceptance-" + reason])
        for key, value, reason in (
            ("method", "beginMessage", "request-mismatch"),
            ("request_id", "another-request", "request-mismatch"),
            ("native_request_id", "TID:another-request", "request-mismatch"),
            ("request_started_at", request["browser_requests"][0]["started_ms"] + 0.125, "request-mismatch"),
            ("response_completed_at", request["browser_requests"][0]["completed_ms"] + 0.125, "request-mismatch"),
            ("log_started_at", stamp(BROWSER_BASE_MS + 4000), "join-time"),
            ("trace_flag_id", "7tf000000000002AAA", "trace-window"),
            ("org_id", "00D000000000002AAA", "trace-window"),
            ("user_id", "005000000000002AAA", "trace-window"),
            ("window", {"baseline": stamp(BROWSER_BASE_MS)}, "trace-window"),
            ("log_id", "invalid", "log-identity"),
            ("body_sha256", "invalid", "callout-unproven"),
            ("outcome", "HTTP_OTHER", "callout-unproven"),
            ("endpoint", "https://example.invalid/v1/responses", "callout-unproven"),
            ("endpoint_kinds", ["UNKNOWN"], "join-schema"),
            ("headers", {}, "join-schema"),
        ):
            with self.subTest(join_field=key):
                receipt = self.live_receipt(request)
                receipt["joins"][0][key] = value
                self.assertEqual(quality.validate_live_receipt(receipt, request), ["live-acceptance-" + reason])

    def test_rejects_five_joins_method_index_and_duplicate_ids(self):
        self.write_ui(self.deploy("aaaaaaaa"), 1)
        self.assertEqual(self.run_quality()[0], 2)
        (request_path,) = self.live_requests()
        request = json.loads(request_path.read_bytes())
        valid = self.live_receipt(request)
        joins = valid["joins"]
        for replacement, reason in (
            (joins[:-1], "six-joins-required"),
            ([{"method": join["method"]} for join in joins], "join-schema"),
            ([joins[0], joins[0], *joins[2:]], "request-mismatch"),
            ([joins[0], {**joins[1], "log_id": joins[0]["log_id"][:15]}, *joins[2:]], "log-identity"),
            ([joins[0], {**joins[1], "native_request_id": joins[0]["native_request_id"]}, *joins[2:]],
             "request-mismatch"),
        ):
            with self.subTest(reason=reason):
                self.assertEqual(quality.validate_live_receipt({**valid, "joins": replacement}, request),
                                 ["live-acceptance-" + reason])

    def test_alias_requires_same_org_configured_resolution(self):
        self.write_ui(self.deploy("aaaaaaaa"), 1)
        self.assertEqual(self.run_quality()[0], 2)
        (request_path,) = self.live_requests()
        request = json.loads(request_path.read_bytes())
        receipt = self.live_receipt(request)
        join = receipt["joins"][0]
        join["endpoint_kinds"] = ["HTTPS", "NAMED_CREDENTIAL"]
        self.assertEqual(quality.validate_live_receipt(receipt, request), ["live-acceptance-join-schema"])
        resolution = {"org_id": quality.ui.EXPECTED_ORG_ID, "user_id": USER_ID,
                      "name": quality.ui.NAMED_CREDENTIAL, "named_credential_id": "0XAn00000000001AAA",
                      "endpoint": "https://api.x.ai", "before_started_at": stamp(BROWSER_BASE_MS),
                      "before_completed_at": stamp(BROWSER_BASE_MS + 1000),
                      "after_started_at": stamp(BROWSER_BASE_MS + 4000),
                      "after_completed_at": stamp(BROWSER_BASE_MS + 5000)}
        for key, value in (("org_id", "00D000000000002AAA"), ("user_id", "005000000000002AAA"),
                           ("name", "Another_Alias"), ("endpoint", "https://example.invalid"),
                           ("before_completed_at", stamp(BROWSER_BASE_MS + 4000)),
                           ("after_started_at", stamp(BROWSER_BASE_MS + 3000))):
            with self.subTest(resolution_field=key):
                join["endpoint_resolution"] = {**resolution, key: value}
                self.assertEqual(quality.validate_live_receipt(receipt, request), ["live-acceptance-endpoint-resolution"])
        join["endpoint_resolution"] = resolution
        self.assertEqual(quality.validate_live_receipt(receipt, request), [])

    def test_pending_live_callback_switches_to_new_deployment(self):
        (self.directory / "review.json").write_text(json.dumps(self.valid()))
        self.write_ui(self.deploy("aaaaaaaa"), 1)

        def deploy_b():
            (request_a,) = self.live_requests()
            self.assertFalse(request_a.with_name("receipt.json").exists())
            self.write_ui(self.deploy("bbbbbbbb"), 2)

        def provide_current_callback():
            requests = {json.loads(path.read_bytes())["identity"]["deployment_call_id"]: path
                        for path in self.live_requests()}
            request_a, request_b = requests["aaaaaaaa"], requests["bbbbbbbb"]
            self.assertFalse(request_a.with_name("receipt.json").exists())
            receipt_b = self.live_receipt(json.loads(request_b.read_bytes()))
            request_b.with_name("receipt.json").write_text(json.dumps(receipt_b))

        events = iter((deploy_b, provide_current_callback))
        with mock.patch.object(quality.time, "sleep", side_effect=lambda _: next(events)()) as sleep:
            self.assertEqual(self.run_quality(wait_seconds=10)[0], 0)
        self.assertEqual(sleep.call_count, 2)
        requests = {json.loads(path.read_bytes())["identity"]["deployment_call_id"]: path
                    for path in self.live_requests()}
        request_a, request_b = requests["aaaaaaaa"], requests["bbbbbbbb"]
        self.assertFalse(request_a.with_name("receipt.json").exists())
        receipt_a = self.live_receipt(json.loads(request_a.read_bytes()))
        request_b.with_name("receipt.json").write_text(json.dumps(receipt_a))
        code, output = self.run_quality()
        self.assertEqual(code, 1)
        self.assertIn("live-acceptance-identity-mismatch", output)
        request = json.loads(request_b.read_bytes())
        self.assertEqual(quality.validate_live_receipt({**receipt_a, "identity": request["identity"]}, request),
                         ["live-acceptance-request-mismatch"])

    def test_pending_live_callback_needs_independent_review_of_changed_source(self):
        directory_a = self.directory
        (directory_a / "review.json").write_text(json.dumps(self.valid()))
        self.write_ui(self.deploy("aaaaaaaa"), 1)

        def change_source():
            self.assertEqual(len(self.live_requests()), 1)
            (self.product / "force-app/Example.cls").write_text("public class Changed {}\n")
            self.identity = quality.snapshot(self.product)
            self.directory = self.platform / "grok-chat-quality" / self.identity["sha256"]

        def deploy_b():
            self.assertEqual(self.live_requests(), [])
            self.write_ui(self.deploy("bbbbbbbb"), 2)

        def provide_current_callback():
            (path,) = self.live_requests()
            request = json.loads(path.read_bytes())
            self.assertEqual(request["identity"]["source_sha256"], self.identity["sha256"])
            path.with_name("receipt.json").write_text(json.dumps(self.live_receipt(request)))

        def review_current_source():
            request = json.loads((self.directory / "request.json").read_bytes())
            self.assertEqual(request["source"], self.identity)
            (self.directory / "review.json").write_text(json.dumps(self.valid()))

        events = iter((change_source, deploy_b, provide_current_callback, review_current_source))
        with mock.patch.object(quality.time, "sleep", side_effect=lambda _: next(events)()) as sleep:
            self.assertEqual(self.run_quality(wait_seconds=10)[0], 0)
        self.assertEqual(sleep.call_count, 4)
        (request_a,) = (directory_a / "live-acceptance").glob("*/request.json")
        self.assertFalse(request_a.with_name("receipt.json").exists())

    def test_late_source_review_and_callback_do_not_interrupt_new_source(self):
        directory_a = self.directory
        self.write_ui(self.deploy("aaaaaaaa"), 1)
        original_requests = {}

        def events():
            (request_a,) = self.live_requests()
            for path in (directory_a / "request.json", request_a):
                original_requests[path] = path.read_bytes()
            review_a = self.valid()
            self.assertFalse((directory_a / "review.json").exists())
            (self.product / "force-app/Example.cls").write_text("public class Changed {}\n")
            self.identity = quality.snapshot(self.product)
            self.directory = self.platform / "grok-chat-quality" / self.identity["sha256"]
            attempt_b = self.register_ui(2)
            yield

            request = json.loads((self.directory / "request.json").read_bytes())
            self.assertEqual(request["source"], self.identity)
            self.assertFalse((attempt_b / "observation.json").exists())
            self.assertEqual(self.live_requests(), [])
            (directory_a / "review.json").write_text(json.dumps(review_a))
            request_a.with_name("receipt.json").write_text(
                json.dumps(self.live_receipt(json.loads(original_requests[request_a]))))
            yield

            self.assertEqual(self.live_requests(), [])
            self.write_ui(self.deploy("bbbbbbbb"), 2, directory=attempt_b)
            (self.directory / "review.json").write_text(json.dumps(self.valid()))
            yield

            (path,) = self.live_requests()
            request = json.loads(path.read_bytes())
            self.assertFalse(path.with_name("receipt.json").exists())
            self.assertEqual(request["identity"]["source_sha256"], self.identity["sha256"])
            self.assertEqual(request["identity"]["deployment_call_id"], "bbbbbbbb")
            path.with_name("receipt.json").write_text(json.dumps(self.live_receipt(request)))
            yield

        timeline = events()
        with mock.patch.object(quality.time, "sleep", side_effect=lambda _: next(timeline)) as sleep:
            code, output = self.run_quality(wait_seconds=10)
        self.assertEqual(code, 0, output)
        self.assertEqual(sleep.call_count, 4)
        for path, original in original_requests.items():
            self.assertEqual(path.read_bytes(), original)
        self.assertFalse((directory_a / "check-builder.json").exists())
        result = json.loads((self.directory / "check-builder.json").read_bytes())
        self.assertEqual(result["source_sha256"], self.identity["sha256"])
        (request_b,) = self.live_requests()
        self.assertEqual(result["live_acceptance_request"], request_b.relative_to(self.platform).as_posix())

    def test_failed_review_arriving_during_live_lookup_is_superseded(self):
        directory_a = self.directory
        review_a = {**self.valid(), "status": "FAIL"}
        self.write_ui(self.deploy("aaaaaaaa"), 1)
        lookup = quality.live_request

        def lookup_and_switch(root, platform, phase, source):
            live = lookup(root, platform, phase, source)
            if source["sha256"] == review_a["source_sha256"]:
                self.assertEqual(live["identity"]["deployment_call_id"], "aaaaaaaa")
                self.assertFalse((directory_a / "review.json").exists())
                (self.product / "force-app/Example.cls").write_text("public class Changed {}\n")
                self.identity = quality.snapshot(self.product)
                self.directory = self.platform / "grok-chat-quality" / self.identity["sha256"]
                (directory_a / "review.json").write_text(json.dumps(review_a))
            return live

        def events():
            (request_a,) = (directory_a / "live-acceptance").glob("*/request.json")
            self.assertFalse(request_a.with_name("receipt.json").exists())
            self.write_ui(self.deploy("bbbbbbbb"), 2)
            yield

            request = json.loads((self.directory / "request.json").read_bytes())
            self.assertEqual(request["source"], self.identity)
            (path,) = self.live_requests()
            request_b = json.loads(path.read_bytes())
            self.assertEqual(request_b["identity"]["source_sha256"], self.identity["sha256"])
            self.assertEqual(request_b["identity"]["deployment_call_id"], "bbbbbbbb")
            (self.directory / "review.json").write_text(json.dumps(self.valid()))
            receipt = self.live_receipt(request_b)
            self.assertEqual(len(receipt["joins"]), 6)
            path.with_name("receipt.json").write_text(json.dumps(receipt))
            yield

        timeline = events()
        with (mock.patch.object(quality, "live_request", side_effect=lookup_and_switch),
              mock.patch.object(quality.time, "sleep", side_effect=lambda _: next(timeline)) as sleep):
            code, output = self.run_quality(wait_seconds=10)
        self.assertEqual(code, 0, output)
        self.assertEqual(sleep.call_count, 2)
        self.assertFalse((directory_a / "check-builder.json").exists())
        result = json.loads((self.directory / "check-builder.json").read_bytes())
        self.assertEqual(result["source_sha256"], self.identity["sha256"])
        self.assertEqual(result["status"], "PASS")
        (request_b,) = self.live_requests()
        self.assertEqual(result["live_acceptance_receipt_sha256"],
                         hashlib.sha256(request_b.with_name("receipt.json").read_bytes()).hexdigest())

    def test_superseded_failures_cannot_extend_the_observation_deadline(self):
        now = 0
        attempts = []

        def lookup_and_switch(_root, platform, _phase, source):
            nonlocal now
            self.assertLess(len(attempts), 3)
            self.identity = source
            self.directory = platform / "grok-chat-quality" / source["sha256"]
            attempts.append(self.directory)
            review = {**self.valid(), "status": "FAIL"}
            (self.product / "force-app/Example.cls").write_text(f"public class Churn{len(attempts)} {{}}\n")
            (self.directory / "review.json").write_text(json.dumps(review))
            if len(attempts) == 1:
                now = quality.CHECK_SECONDS - 3
            return None

        def advance(seconds):
            nonlocal now
            now += seconds

        with (mock.patch.object(quality, "live_request", side_effect=lookup_and_switch),
              mock.patch.object(quality.time, "monotonic", side_effect=lambda: now),
              mock.patch.object(quality.time, "sleep", side_effect=advance) as sleep):
            code, output = self.run_quality(wait_seconds=quality.CHECK_SECONDS)
        self.assertEqual(code, 2, output)
        self.assertIn("source-review-superseded", output)
        self.assertEqual(sleep.call_args_list, [mock.call(2), mock.call(1)])
        self.assertEqual(now, quality.CHECK_SECONDS)
        self.assertEqual(len(set(attempts)), 3)
        self.assertTrue(all(not (path / "check-builder.json").exists() for path in attempts[:-1]))
        result = json.loads((attempts[-1] / "check-builder.json").read_bytes())
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["errors"], [])

    def test_evidence_changed_during_wait_rejects_old_callback(self):
        (self.directory / "review.json").write_text(json.dumps(self.valid()))
        for index, change in enumerate(("ui", "deploy", "source"), 1):
            with self.subTest(change=change):
                first_id = index * 3
                deploy = self.deploy(f"{first_id:08x}")
                self.write_ui(deploy, first_id)

                def provide_stale_callback(_):
                    path = next(path for path in self.live_requests() if not path.with_name("receipt.json").exists())
                    receipt = self.live_receipt(json.loads(path.read_bytes()))
                    path.with_name("receipt.json").write_text(json.dumps(receipt))

                validate = quality.validate_live_receipt

                def change_after_receipt_selected(receipt, request):
                    errors = validate(receipt, request)
                    if change == "ui":
                        self.write_ui(deploy, first_id + 1)
                    elif change == "deploy":
                        self.deploy(f"{first_id + 1:08x}")
                    else:
                        (self.product / "force-app/Example.cls").write_text("public class Changed {}\n")
                    return errors

                with (mock.patch.object(quality.time, "sleep", side_effect=provide_stale_callback) as sleep,
                      mock.patch.object(quality, "validate_live_receipt", side_effect=change_after_receipt_selected)):
                    code, output = self.run_quality(wait_seconds=1)
                sleep.assert_called_once()
                self.assertEqual(code, 1)
                self.assertIn("live-acceptance-evidence-changed", output)

    def test_required_dimensions_and_independent_identity_cannot_be_omitted(self):
        for key in quality.DIMENSIONS:
            review = self.valid()
            del review["dimensions"][key]
            self.assertIn("review-dimensions-incomplete", quality.validate_review(review, self.identity, self.directory))
        review = self.valid()
        review["reviewer"]["independent"] = False
        self.assertIn("independent-reviewer-missing", quality.validate_review(review, self.identity, self.directory))
        for key in ("actor", "execution_id", "provenance"):
            review = self.valid()
            del review["reviewer"][key]
            self.assertIn("independent-reviewer-missing", quality.validate_review(review, self.identity, self.directory))

    def test_ignored_deployable_source_is_included_and_changes_review_identity(self):
        (self.product / ".gitignore").write_text("force-app/Ignored.cls\n")
        before = quality.snapshot(self.product)
        ignored = self.product / "force-app/Ignored.cls"
        ignored.write_text("public class Ignored {}\n")
        after = quality.snapshot(self.product)
        self.assertNotEqual(before["sha256"], after["sha256"])
        self.assertIn("force-app/Ignored.cls", [row["path"] for row in after["files"]])

    def test_symbolic_deployable_source_is_refused(self):
        (self.product / "force-app/Alias").symlink_to(self.platform, target_is_directory=True)
        with self.assertRaises(ValueError):
            quality.snapshot(self.product)

    def test_wrong_source_unknown_status_and_active_findings_fail(self):
        changes = (
            ("source_sha256", "0" * 64, "review-source-mismatch"),
            ("status", "UNKNOWN", "review-not-passed"),
            ("findings", [{"actionable": True, "message": "Missing authorization check"}], "actionable-findings-remain"),
        )
        for field, value, reason in changes:
            review = self.valid()
            review[field] = value
            self.assertIn(reason, quality.validate_review(review, self.identity, self.directory))

    def test_missing_tampered_and_escaping_evidence_fail(self):
        for kind in ("missing", "tampered", "escaping"):
            review = self.valid()
            if kind == "missing":
                (self.directory / "review-evidence.txt").unlink()
            elif kind == "tampered":
                (self.directory / "review-evidence.txt").write_text("Different evidence")
            else:
                review["evidence"][0]["path"] = "../../outside.txt"
            self.assertIn("review-evidence-invalid", quality.validate_review(review, self.identity, self.directory))

    def test_source_mutation_during_review_invalidates_result(self):
        (self.directory / "review.json").write_text(json.dumps(self.valid()))
        changed = dict(self.identity, sha256="1" * 64)
        with mock.patch.object(quality, "snapshot", side_effect=[self.identity, self.identity, changed]):
            code, output = self.run_quality("final")
        self.assertEqual(code, 1)
        self.assertIn("candidate-changed-during-review", output)

    def test_unsupported_phase_stops_before_candidate_or_platform_activity(self):
        with mock.patch.object(quality, "snapshot", side_effect=AssertionError("must not inspect")):
            for phase in ("unknown", "product_at_stop", "review"):
                self.assertEqual(quality.run(self.product, self.platform, phase, wait_seconds=0), 2)

    def test_candidate_outside_run_is_refused(self):
        with tempfile.TemporaryDirectory() as other:
            self.assertEqual(quality.run(Path(other), self.platform, "builder", wait_seconds=0), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
