#!/usr/bin/env python3
"""Exercise the slice, prospective comparison CLI and installed audit archive consumer."""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "test/shiploop_e2e"
AUDIT = ROOT / "skills/shiploop-e2e-audit/harness"
sys.path[:0] = [str(HARNESS), str(AUDIT)]
import evidence as audit_archive  # noqa: E402
import planning_comparison as comparison  # noqa: E402
import slice as step_slice  # noqa: E402
import shiploop_store as store  # noqa: E402

_SPEC = importlib.util.spec_from_file_location(
    "planning_boundary_fixture", ROOT / "test/shiploop-e2e-planning-boundary.test.py")
fixture_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(fixture_module)

INITIAL = "The producer gives the sole reaper ownership of shutdown."
FINAL = "The review moves shutdown ownership to the coordinator."
LOCATOR = "docs/architecture.md#shutdown"
SUMMARY = "The initial Plan treats shutdown as a separate decision."


class ConsumerTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="plan-comparison-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.fixture = fixture_module.PlanningFixture(self.root / "subject")
        self.add_producer_snapshot()

    def git(self, *args: str) -> str:
        env = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        return subprocess.check_output(
            ["git", "-C", str(self.fixture.workspace), *args], env=env, text=True).strip()

    def add_producer_snapshot(self):
        fixture = self.fixture
        architecture = fixture.workspace / "docs/architecture.md"
        architecture.parent.mkdir()
        architecture.write_text(INITIAL + "\n", encoding="utf-8")
        self.git("init", "-q")
        self.git("add", "--", "docs/architecture.md")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "producer")
        self.seed_head = self.git("rev-parse", "HEAD")
        tree = self.git("write-tree")
        architecture.write_text(FINAL + "\n", encoding="utf-8")

        plan, improve, run_id = fixture_module.PLAN, fixture_module.IMPROVE, fixture_module.RUN
        seed = {"outcome": "done", "summary": SUMMARY, "evidence_refs": [LOCATOR]}
        seed_sha256 = comparison.planning_evidence.seed_digest(seed)
        skill = fixture.runtime.parents[3] / "SKILL.md"
        fixture.receipt.update(version=1, seed_result=seed)
        fixture.receipt["skill"]["skill_card"] = str(skill)
        fixture.state["accepted"][plan] = {"outcome": "done", "summary": FINAL}
        self.expected = comparison.ExpectedPlan(run_id, plan, improve, 8, seed_sha256, str(fixture.workspace), ".")
        bind = fixture.run / "improve" / f"{plan}-bind.md"
        bind.parent.mkdir()
        store.write_record(bind, {"toplevel": str(fixture.workspace), "prefix": ".", "tree": tree,
                                  "result": seed_sha256})
        bind_result = bind.with_name(f"{plan}-bind-result.json")
        bind_result.write_text(json.dumps(seed), encoding="utf-8")

        # Align the synthetic host/engine clocks with the actual bind file clocks.
        # The producer snapshot and packet remain before the synthetic acceptance.
        producer = fixture.trace[0]
        end = round(max(bind.stat().st_ctime, bind_result.stat().st_ctime), 3) + 0.1
        offset = end - producer["ts"]
        fixture.events = [(round(when + offset, 3), event) for when, event in fixture.events]
        for row in fixture.trace:
            row["ts"] = round(row["ts"] + offset, 3)
        producer["ms"] = 400
        packet = ("ShipLoop navigator | improve | revision 8 | the plan result\n"
                  "1. Run the improve skill on the plan result with this argument, at every Improve stage\n"
                  f"   otherwise open {skill} and follow it\n"
                  f"2. When the improve skill has completed, run: shiploop complete --run-dir={fixture.run} "
                  f"--action={improve}\n"
                  f"Keepalive marker: SHIPLOOP-RUN run={run_id} rev=8 dir={fixture.run}\n")
        digest = sha256(packet.encode()).hexdigest()[:16]
        relative = f"packets/sent/{digest}.md"
        (fixture.run / relative).parent.mkdir(parents=True)
        (fixture.run / relative).write_text(packet, encoding="utf-8")
        fixture.trace.insert(0, {"v": 1, "kind": "packet", "stage": "improve", "reviewed": "plan",
                                 "action": improve, "rev": 8, "status": "active", "whole": True,
                                 "ts": round(end - 0.02, 3), "sha": digest, "file": relative,
                                 "chars": len(packet), "printed": len(packet)})
        self.registration = self.root / "expected.json"
        self.registration.write_text(json.dumps(asdict(self.expected)), encoding="utf-8")
        fixture.write()

    def finalize_slice(self) -> dict:
        fixture = self.fixture
        seeded = {"start_head": self.seed_head, "planning_registration": {
            "run_id": self.expected.run_id, "repo": self.expected.repo, "repo_prefix": self.expected.repo_prefix}}
        self.assertEqual(step_slice.finish(fixture.out, fixture.run, seeded, {"work_item": {"id": "W1"}, "checks": []},
                                          [{"status": "slice-complete"}], {"case": "synthetic"}, True, "plan"), 0)
        return json.loads((fixture.out / "slice-result.json").read_text())

    def cli(self, name: str, *args: str) -> tuple[subprocess.CompletedProcess, dict]:
        fixture = self.fixture
        completed = subprocess.run(
            [sys.executable, "-B", str(HARNESS / "planning_comparison.py"),
             "--recording", str(fixture.out), "--run-dir", str(fixture.run), "--cli", str(fixture.cli),
             "--expected", str(self.registration), "--output", str(self.root / name), *args],
            capture_output=True, text=True, cwd=self.root)
        self.assertTrue(completed.stdout, completed.stderr)
        return completed, json.loads(completed.stdout)

    def test_slice_retains_initial_blob_and_comparison_checks_selected_locator(self):
        result = self.finalize_slice()
        self.assertEqual(result["planning_boundary"]["status"], "established", result)
        initial = result["planning_evidence"]
        self.assertEqual(initial["expected"], asdict(self.expected))
        self.assertEqual(initial["capture"]["status"], "captured", initial)
        self.assertEqual(initial["source_sha256"]["trace"],
                         result["planning_boundary"]["sources"]["sha256"]["trace"])
        bundle = self.fixture.out / comparison.BUNDLE_NAME
        manifest = json.loads((bundle / "planning-evidence.json").read_text())
        self.assertIn(INITIAL, (bundle / manifest["entries"][LOCATOR]["sidecar"]).read_text())
        pin = initial["capture"]["manifest_sha256"]
        original = (self.fixture.run / "state.md").read_bytes()
        common = ("--locator", LOCATOR, "--bundle-dir", str(bundle), "--manifest-sha256", pin)
        completed, admitted = self.cli("accepted", *common, "--quote", INITIAL)
        self.assertEqual(completed.returncode, 0, admitted)
        self.assertTrue(admitted["admitted"], admitted)
        self.assertEqual(admitted["quote"]["status"], "matched")
        completed, fresh = self.cli("fresh", "--locator", LOCATOR, "--quote", INITIAL)
        self.assertEqual(completed.returncode, 0, fresh)
        self.assertEqual(fresh["capture"]["status"], "captured")
        self.assertTrue((self.root / "fresh" / comparison.PIN_NAME).is_file())
        completed, refused = self.cli("final-only", *common, "--quote", FINAL)
        self.assertEqual(completed.returncode, 1, refused)
        self.assertEqual(refused["quote"]["status"], "not-found")
        completed, refused = self.cli("different-locator", "--locator", "docs/architecture.md",
                                      "--bundle-dir", str(bundle), "--manifest-sha256", pin, "--quote", INITIAL)
        self.assertEqual(completed.returncode, 1, refused)
        self.assertEqual(refused["quote"]["status"], "unsupported")
        report = self.root / "accepted/planning-comparison.json"
        before = report.read_bytes()
        completed, conflicting = self.cli("accepted", *common, "--quote", FINAL)
        self.assertEqual(completed.returncode, 2, conflicting)
        self.assertEqual(report.read_bytes(), before)
        self.registration.write_text(json.dumps({**asdict(self.expected), "seed_sha256": "0" * 64}))
        completed, refused = self.cli("unregistered-seed", *common, "--quote", INITIAL)
        self.assertEqual(completed.returncode, 1, refused)
        self.assertEqual(refused["quote"]["status"], "invalid")
        self.assertEqual((self.fixture.run / "state.md").read_bytes(), original)

    def test_named_field_and_refusal_of_overshoot_or_incomplete_stop(self):
        completed, result = self.cli("field", "--field", "summary", "--quote", SUMMARY)
        self.assertEqual(completed.returncode, 0, result)
        self.assertEqual(result["quote"]["status"], "matched")
        self.assertIsNone(result["capture"])
        fixture = self.fixture
        after = fixture.events[-1][0]
        fixture.events.extend(fixture_module.shell_pair("later", "cat docs/architecture.md", "later work", after, after))
        fixture.write()
        result = self.finalize_slice()
        self.assertTrue(result["pass"])
        self.assertEqual(result["planning_boundary"]["status"], "overshoot")
        completed, result = self.cli("overshoot", "--field", "summary", "--quote", SUMMARY)
        self.assertEqual(completed.returncode, 1, result)
        self.assertFalse(result["admitted"])
        self.assertEqual(result["boundary"]["status"], "overshoot")
        self.assertIsNone(result["quote"])

        del fixture.events[-3:]  # leave the accepting callback request without its terminal update
        fixture.write()
        completed, result = self.cli("incomplete", "--field", "summary", "--quote", SUMMARY)
        self.assertEqual(completed.returncode, 1, result)
        self.assertFalse(result["admitted"])
        self.assertEqual(result["boundary"]["status"], "incomplete")

    def test_archive_walker_keeps_only_declared_portable_set_and_verifies_offline(self):
        fixture = self.fixture
        result = self.finalize_slice()
        pin = result["planning_evidence"]["capture"]["manifest_sha256"]
        (fixture.out / comparison.BUNDLE_NAME / "state.md").write_text("outside portable set", encoding="utf-8")
        archive = self.root / "archive"
        archived = audit_archive.capture_run_artifacts([fixture.out], archive)
        rows = [row for row in archived["artifacts"] if row["kind"] == "planning-evidence"]
        self.assertEqual(len(rows), 1, archived)
        self.assertEqual(rows[0]["archive_path"], f"planning-evidence/{pin}/planning-evidence.json")
        self.assertEqual(rows[0]["sha256"], pin)
        archived_bundle = (archive / rows[0]["archive_path"]).parent
        self.assertFalse((archived_bundle / "state.md").exists())
        self.assertNotIn("planning-evidence/state.md", [row["relative_path"] for row in archived["artifacts"]])
        audit_archive.inspect_run_artifacts(archived)

        (fixture.out / comparison.PIN_NAME).write_text("0" * 64 + "\n", encoding="ascii")
        refused = audit_archive.capture_run_artifacts([fixture.out], archive)
        self.assertTrue(any(row["reason"] == "planning-evidence-invalid" for row in refused["skipped"]), refused)
        self.assertFalse(any(row["kind"] == "planning-evidence" for row in refused["artifacts"]))
        bundle = fixture.out / comparison.BUNDLE_NAME
        relocated = bundle.rename(self.root / "undeclared-bundle")
        bundle.symlink_to(relocated, target_is_directory=True)
        (fixture.out / comparison.PIN_NAME).write_text(pin + "\n", encoding="ascii")
        refused = audit_archive.capture_run_artifacts([fixture.out], archive)
        self.assertTrue(any(row["reason"] == "planning-evidence-invalid" for row in refused["skipped"]), refused)
        shutil.rmtree(relocated)
        shutil.rmtree(fixture.out)  # removes the worktree, Git object database, run and original bundle
        completed = subprocess.run(
            [sys.executable, "-B", str(AUDIT / "planning_evidence.py"), "verify", "--bundle-dir", str(archived_bundle),
             "--manifest-sha256", pin, "--run-id", self.expected.run_id, "--plan-action", self.expected.plan_action,
             "--improve-action", self.expected.improve_action, "--producer-revision", str(self.expected.producer_revision),
             "--seed-sha256", self.expected.seed_sha256, "--repo", self.expected.repo, "--repo-prefix", ".",
             "--phase", "initial", "--locator", LOCATOR, "--quote", INITIAL],
            cwd=self.root, env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
            capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, (completed.stdout, completed.stderr))
        self.assertEqual(json.loads(completed.stdout)["status"], "matched")


if __name__ == "__main__":
    unittest.main()
