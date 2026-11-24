#!/usr/bin/env python3
"""Public CLI boundaries for the opt-in consumer-delivery navigator contract."""

from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills/shiploop"
sys.path.insert(0, str(PACKAGE / "scripts"))
import shiploop_store as store  # noqa: E402


class ConsumerDeliveryCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-consumer-cli-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "product with spaces"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True, capture_output=True)
        self.run = self.repo / ".shiploop"

    def cli(self, *args, package=PACKAGE):
        return subprocess.run(
            [sys.executable, str(package / "scripts/shiploop"), *args],
            cwd=self.repo, text=True, capture_output=True, timeout=30,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def init(self, *args, package=PACKAGE):
        return self.cli("init", "--repo", str(self.repo), "--run-dir", str(self.run),
                        "--prompt", "Improve the existing consumer within authority.",
                        *args, package=package)

    def test_opt_in_persists_and_cold_next_does_not_mutate(self):
        result = self.init("--delivery-contract")
        self.assertEqual(result.returncode, 0, result.stderr)
        state_path = self.run / "state.md"
        before = state_path.read_bytes()
        state = store.loads(before.decode())
        self.assertEqual(state["delivery_contract_version"], 1)
        self.assertEqual(state["navigator_protocol_version"], 4)
        recovered = self.cli("next", "--run-dir", str(self.run))
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        self.assertEqual(before, state_path.read_bytes())
        self.assertIn(state["action"]["id"], recovered.stdout)
        self.assertIn("delivery_assessment", recovered.stdout)

    def test_default_run_stays_unmarked_and_cannot_be_retrofitted(self):
        result = self.init()
        self.assertEqual(result.returncode, 0, result.stderr)
        before = (self.run / "state.md").read_bytes()
        self.assertNotIn("delivery_contract_version", store.loads(before.decode()))
        result = self.init("--delivery-contract")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot retrofit", result.stderr)
        self.assertEqual(before, (self.run / "state.md").read_bytes())

    def test_marked_init_without_flag_cannot_remove_recorded_mode(self):
        result = self.init("--delivery-contract")
        self.assertEqual(result.returncode, 0, result.stderr)
        before = (self.run / "state.md").read_bytes()
        result = self.init()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, (self.run / "state.md").read_bytes())

    def test_next_does_not_accept_initialization_flag(self):
        result = self.cli("next", "--run-dir", str(self.run), "--delivery-contract")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.run.exists())

    def test_copied_package_binds_its_own_cli(self):
        copied = Path(self.temp.name) / "relocated package"
        shutil.copytree(PACKAGE, copied, ignore=shutil.ignore_patterns("__pycache__"))
        result = self.init("--delivery-contract", package=copied)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(copied / "scripts/shiploop"), result.stdout)
        self.assertIn(str(self.repo), result.stdout)
        self.assertNotIn(str(PACKAGE / "scripts/shiploop"), result.stdout)

    def test_multistage_promotions_contract_accepted_through_cli(self):
        import shiploop_concerns as concerns
        import shiploop_consumer_delivery as consumer_delivery
        import shiploop_navigator as navigator
        improve_card = ROOT / "skills/improve/SKILL.md"
        init_res = self.init("--delivery-contract", "--planning-review", "none", "--improve-skill", str(improve_card))
        self.assertEqual(init_res.returncode, 0, init_res.stderr)
        state = store.read_record(self.run / "state.md")
        while navigator.current_stage(state) != "plan":
            action = navigator.current_action(state)["id"]
            state = navigator.apply(state, action, {"outcome": "done", "summary": "Synthetic prelude (S1)."})
        navigator.save(self.run, state)
        plan_action = navigator.current_action(state)["id"]
        no_concerns = {"W1": [{"id": name, "applies": "no", "reason": "Synthetic fixture."} for name in concerns.CONCERN_IDS]}
        plan_result = {
            "outcome": "done",
            "summary": "Planned multi-stage dev->prod delivery.",
            "work_items": [{"id": "W1", "title": "Multi-stage service change"}],
            "assumptions": [],
            "concerns": no_concerns,
            "delivery_assessment": {
                "kind": "contract",
                "contract": {
                    "consumer": "API caller",
                    "target": "prod-api",
                    "behavior": "GET /v2 works in dev and prod",
                    "candidate": "cand-1",
                    "operation": "promote to prod-api",
                    "necessity": "required",
                    "basis": "Multi-stage deployment request",
                    "exclusions": [],
                    "authority": {"status": "approved", "kind": "request", "reference": "Requested dev->prod"},
                    "promotions": [
                        {"stage": "dev", "target": "dev-api", "operation": "deploy to dev-api",
                         "authority": {"status": "approved", "kind": "request", "reference": "Requested dev"}},
                        {"stage": "prod", "target": "prod-api", "operation": "promote to prod-api",
                         "authority": {"status": "approved", "kind": "request", "reference": "Requested dev->prod"}},
                    ],
                    "obligations": [
                        {"id": "eff-dev", "consumer": "API caller", "target": "dev-api", "kind": "effect",
                         "phase": "release", "expected": "dev updated", "required": True},
                        {"id": "id-dev", "consumer": "API caller", "target": "dev-api", "kind": "identity",
                         "phase": "release", "expected": "dev cand-1", "required": True},
                        {"id": "eff-prod", "consumer": "API caller", "target": "prod-api", "kind": "effect",
                         "phase": "release", "expected": "prod updated", "required": True},
                        {"id": "id-prod", "consumer": "API caller", "target": "prod-api", "kind": "identity",
                         "phase": "release", "expected": "prod cand-1", "required": True},
                        {"id": "beh-prod", "consumer": "API caller", "target": "prod-api", "kind": "behavior",
                         "phase": "release-verify", "expected": "GET /v2 OK", "required": True},
                    ],
                },
            },
        }
        inbox = self.run / "inbox" / f"{plan_action}.md"
        inbox.write_text(store.dumps(plan_result, "CLI plan result"), encoding="utf-8")
        done = self.cli("complete", "--run-dir", str(self.run), "--action", plan_action)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        after = store.read_record(self.run / "state.md")
        self.assertEqual([p["stage"] for p in consumer_delivery.project(after)["contract"]["promotions"]], ["dev", "prod"])
        for _ in range(40):
            if navigator.current_stage(after) == "system-test-author" and after.get("active_improve") is None:
                break
            action = navigator.current_action(after)["id"]
            after = navigator.apply(after, action, {"outcome": "done", "summary": "Synthetic inner."})
            if after.get("active_improve") is not None:
                after = navigator.finish_improve(
                    after, action,
                    {"summary": "Synthetic review.", "review_refs": ["synthetic://r"], "check_refs": ["synthetic://c"]},
                )
        self.assertEqual(navigator.current_stage(after), "system-test-author")
        navigator.save(self.run, after)
        packet = self.cli("next", "--run-dir", str(self.run)).stdout
        self.assertIn("Delivery promotions: dev (dev-api; approved) -> prod (prod-api; approved)", packet)


if __name__ == "__main__":
    unittest.main()
