#!/usr/bin/env python3
"""No-model tests for the evidence-bound incremental-chain checkpoint."""

from __future__ import annotations

import copy
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import checkpoint
import launch
import calibrate_checks


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class CheckpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="shiploop-incremental-checkpoint-")
        self.root = Path(self.temporary.name)
        self.output_root = self.root / "runs"
        self.run_dir = self.output_root / "trial-a" / "base"
        self.work = self.run_dir / "work"
        self.release = self.root / "released-tree"
        self.review_path = self.output_root / "reviews" / "trial-a" / "base.json"
        self.snapshot_path = self.output_root / "reviews" / "trial-a" / "base-snapshot.json"
        self.inventory_path = self.output_root / "runs.json"
        self.checkpoint_path = self.output_root / "checkpoints" / "trial-a" / "base.json"
        self._make_release()
        self._make_run()
        self.identity = self.row["identity"]
        self._write_inventory()
        self.receipt = checkpoint.inspect_run(
            run_dir=self.run_dir,
            inventory_path=self.inventory_path,
            trial_id="trial-a",
            link="base",
            output_path=self.snapshot_path,
        )
        self._write_review()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _launch_args(self, *, link: str = "base", trial_id: str = "trial-a", resume: bool = False,
                     checkpoint_path: Path | None = None, output_root: Path | None = None) -> argparse.Namespace:
        return argparse.Namespace(
            release_tree=self.release,
            release_commit=self.release_info["head"],
            output_root=output_root or self.output_root,
            inventory=self.inventory_path,
            calibration=self.output_root / "calibration.json",
            trial_id=trial_id,
            link=link,
            checkpoint=checkpoint_path,
            resume=resume,
            dry_run=False,
        )

    def _make_release(self) -> None:
        (self.release / "test/shiploop_e2e/checks").mkdir(parents=True)
        (self.release / "test/shiploop_e2e/run.py").write_text("# released runner\n", encoding="utf-8")
        csv_report = self.release / "test/shiploop_e2e/checks/csv_report.py"
        csv_report.write_bytes((checkpoint.SOURCE_ROOT / "test/shiploop_e2e/checks/csv_report.py").read_bytes())
        git(self.release, "init", "-q")
        # init requires the directory to exist, which the first runner write above created.
        git(self.release, "config", "user.name", "Checkpoint Test")
        git(self.release, "config", "user.email", "checkpoint@example.invalid")
        git(self.release, "add", "-A")
        git(self.release, "commit", "-qm", "release: fixture", "-m",
            "Skill-Craft-Release: skill-craft@0.0.0, shiploop 0.0.0")
        git(self.release, "checkout", "--detach", "HEAD")
        self.release_info = {
            "release_tree": str(self.release.resolve()),
            "head": git(self.release, "rev-parse", "HEAD"),
            "tree": git(self.release, "rev-parse", "HEAD^{tree}"),
            "release_commit": git(self.release, "rev-parse", "HEAD"),
            "release_trailer": "Skill-Craft-Release: skill-craft@0.0.0, shiploop 0.0.0",
        }
        self.csv_report = csv_report.resolve()

    def _make_run(self) -> None:
        self.work.mkdir(parents=True)
        git(self.work, "init", "-q")
        git(self.work, "config", "user.name", "Checkpoint Test")
        git(self.work, "config", "user.email", "checkpoint@example.invalid")
        (self.work / ".gitignore").write_text("ignored-data.txt\n", encoding="utf-8")
        (self.work / "README.md").write_text("pilot product\n", encoding="utf-8")
        (self.work / "link-to-readme").symlink_to("README.md")
        git(self.work, "add", ".gitignore", "README.md", "link-to-readme")
        git(self.work, "commit", "-qm", "base product")
        (self.work / "declared-untracked.txt").write_text("untracked\n", encoding="utf-8")
        (self.work / "ignored-data.txt").write_text("ignored\n", encoding="utf-8")

        prompt_path, prompt_arg, prompt_source_digest, invoked_digest = launch._prompt("base")
        prompt_bytes = (prompt_arg + "\n").encode("utf-8")
        (self.run_dir / "prompt.txt").write_bytes(prompt_bytes)
        selected_run = self.run_dir / ".shiploop-runs/test-run/run"
        selected_run.mkdir(parents=True)
        (selected_run / "state.md").write_text("status: done\n", encoding="utf-8")
        (selected_run / "report.html").write_text("<html>complete</html>\n", encoding="utf-8")
        write_json(self.run_dir / "shiploop-run.json", {"run_dir": str(selected_run.resolve()), "basis": "test"})
        commands, checks = launch._check_commands(self.release, "base")
        self.command = commands[-1]
        checks_path = launch._experiment_checks()
        result = {
            "case": "custom",
            "pass": True,
            "output": str(self.run_dir.resolve()),
            "process": {"returncode": 0},
            "termination": {"engine_status": "done", "engine_stage": "done", "engine_unaccepted_stage": None},
            "shiploop": {"status": "done", "report_html": True, "run_dir": str(selected_run.resolve())},
            "checks": [{"command": command, "pass": True} for command in commands],
        }
        write_json(self.run_dir / "result.json", result)
        write_json(self.run_dir / "metrics.json", {"fixture": "initial metrics"})
        write_json(self.run_dir / "invocation.json", {
            "case": "custom",
            "cwd": str(self.work.resolve()),
            "host": checkpoint.MODEL["host"],
            "model": checkpoint.MODEL["model"],
            "effort": checkpoint.MODEL["effort"],
            "versions": {"source": "checkout", "local_head": self.release_info["head"]},
            "checks": commands,
        })
        source_prompt_path = prompt_path.resolve()
        calibration_path = self.output_root / "calibration.json"
        inputs = calibrate_checks.input_manifest(self.csv_report)
        context = calibrate_checks.source_context()
        write_json(calibration_path, {
            "schema_version": 1,
            "calibration": "incremental-feature-chain-20261101",
            "live_model_calls": 0,
            "summary": {"all_expectations_matched": True, "mismatches": []},
            "context": context,
            "context_after": context,
            "inputs": inputs,
            "inputs_after": copy.deepcopy(inputs),
        })
        check_files = {
            "checks": {"path": str(checks_path), "sha256": checkpoint.sha256_file(checks_path)},
            "csv_report": {"path": str(self.csv_report), "sha256": checkpoint.sha256_file(self.csv_report)},
        }
        calibration = checkpoint.calibration_identity(calibration_path, self.csv_report, check_files)
        self.identity = launch._identity(
            self.release_info, "trial-a", "base",
            {"path": str(source_prompt_path), "source_sha256": prompt_source_digest,
             "invoked_sha256": invoked_digest},
            checks, calibration,
        )
        self.row = {
            "run_id": "trial-a:base",
            "trial_id": "trial-a",
            "link": "base",
            "status": "complete",
            "runner_returncode": 0,
            "output": str(self.run_dir.resolve()),
            "identity": self.identity,
            "result_sha256": checkpoint.sha256_file(self.run_dir / "result.json"),
            "invocation_sha256": checkpoint.sha256_file(self.run_dir / "invocation.json"),
            "prompt_file_sha256": checkpoint.sha256_file(self.run_dir / "prompt.txt"),
            "graded_work_snapshot": checkpoint.work_snapshot(self.work),
            "terminal_artifacts": checkpoint.terminal_artifacts(self.run_dir, result),
        }

    def _write_inventory(self) -> None:
        write_json(self.inventory_path, {"schema": checkpoint.RUNS_SCHEMA, "runs": [self.row]})

    def _make_interrupted_link(self, link: str = "filter") -> tuple[Path, dict[str, Any], dict[str, Any]]:
        run_dir = self.output_root / "trial-a" / link
        work = run_dir / "work"
        run_dir.mkdir(parents=True)
        shutil.copytree(self.work, work, symlinks=True)
        prompt_path, prompt_arg, prompt_source_digest, invoked_digest = launch._prompt(link)
        (run_dir / "prompt.txt").write_text(prompt_arg + "\n", encoding="utf-8")
        commands, checks = launch._check_commands(self.release, link)
        calibration = checkpoint.calibration_identity(
            self.output_root / "calibration.json", checks["files"]["csv_report"]["path"], checks["files"]
        )
        identity = launch._identity(
            self.release_info, "trial-a", link,
            {"path": str(prompt_path.resolve()), "source_sha256": prompt_source_digest,
             "invoked_sha256": invoked_digest}, checks, calibration,
        )
        selected_run = run_dir / ".shiploop-runs/interrupted/run"
        selected_run.mkdir(parents=True)
        (selected_run / "state.md").write_text("stage: implementation\nstatus: active\n", encoding="utf-8")
        write_json(run_dir / "shiploop-run.json", {"run_dir": str(selected_run.resolve()), "basis": "test interruption"})
        result = {
            "case": "custom",
            "pass": False,
            "output": str(run_dir.resolve()),
            "outcome_class": "FAILED",
            "process": {"status": "failed", "returncode": 1, "pass": False,
                        "sessions": [{"status": "failed", "returncode": 1}]},
            "termination": {
                "engine_status": "active", "engine_stage": "implementation", "engine_unaccepted_stage": "implementation",
                "process_status": "failed", "returncode": 1, "sessions": 1,
                "session_stops": ["unknown"],
                "resume_stop": "resumed host failed 3 times in a row with ShipLoop still at revision 1 (last exit code 1)",
            },
            "shiploop": {"status": "active", "report_html": False, "run_dir": str(selected_run.resolve())},
            "checks": [{"command": command, "pass": True} for command in commands],
            "follow_on": {
                "prior": str(self.run_dir.resolve()),
                "start_head": git(self.work, "rev-parse", "HEAD"),
                "prior_case": "custom",
                "prior_pass": True,
            },
        }
        write_json(run_dir / "result.json", result)
        write_json(run_dir / "metrics.json", {"fixture": "interrupted metrics"})
        invocation = {
            "case": "custom", "cwd": str(work.resolve()), "host": checkpoint.MODEL["host"],
            "model": checkpoint.MODEL["model"], "effort": checkpoint.MODEL["effort"],
            "versions": {"source": "checkout", "local_head": self.release_info["head"]},
            "checks": commands, "resumed_run": None,
        }
        write_json(run_dir / "invocation.json", invocation)
        row = {
            "run_id": f"trial-a:{link}", "trial_id": "trial-a", "link": link,
            "status": "failed", "runner_returncode": 1, "output": str(run_dir.resolve()),
            "inventory_path": str(self.inventory_path), "identity": identity,
            "argv": [sys.executable, "run.py", "--prompt", prompt_arg],
            "result_sha256": checkpoint.sha256_file(run_dir / "result.json"),
            "invocation_sha256": checkpoint.sha256_file(run_dir / "invocation.json"),
            "original_invocation_sha256": checkpoint.sha256_file(run_dir / "invocation.json"),
            "prompt_file_sha256": checkpoint.sha256_file(run_dir / "prompt.txt"),
            "graded_work_snapshot": checkpoint.work_snapshot(work),
            "post_run_problems": ["runner exited 1", "result pass is not true"],
            "attempts": [],
            "initial_attempt": {"status": "failed", "result_sha256": checkpoint.sha256_file(run_dir / "result.json"),
                                "invocation_sha256": checkpoint.sha256_file(run_dir / "invocation.json")},
        }
        write_json(run_dir / "events.jsonl", {"fixture": "prior stream"})
        write_json(self.inventory_path, {"schema": checkpoint.RUNS_SCHEMA, "runs": [self.row, row]})
        return run_dir, row, identity

    def _write_review(self) -> None:
        citations = [{"path": "work/README.md", "locator": "file start", "note": "Reviewed product contract."}]
        dimensions = {
            name: {"status": "pass", "evidence": citations}
            for name in checkpoint.DIMENSIONS
        }
        write_json(self.review_path, {
            "reviewer": "operator",
            "trial_id": "trial-a",
            "link": "base",
            "prompt_sha256": self.identity["prompt"]["invoked_sha256"],
            "result_sha256": checkpoint.sha256_file(self.run_dir / "result.json"),
            "checkout_identity_sha256": self.receipt["checkout_identity_sha256"],
            "retrieval_source": {"status": "unknown", "note": "Access trace was unavailable."},
            "follow_on": {"class": "note", "statement": "Deferred filter retained.",
                          "source": "lessons.open_next", "rationale": "Observed label, not an acceptance gate."},
            "dimensions": dimensions,
        })

    def create_checkpoint(self) -> dict:
        return checkpoint.create_checkpoint(
            run_dir=self.run_dir,
            inventory_path=self.inventory_path,
            review_path=self.review_path,
            snapshot_path=self.snapshot_path,
            output_path=self.checkpoint_path,
            trial_id="trial-a",
            link="base",
        )

    def verify_checkpoint(self, expected: dict | None = None) -> dict:
        return checkpoint.verify_checkpoint(
            self.checkpoint_path,
            expected_identity=expected or self.identity,
            output_root=self.output_root,
            inventory_path=self.inventory_path,
        )

    def test_correct_checkpoint_is_accepted(self) -> None:
        manifest = checkpoint.work_snapshot(self.work)
        self.assertTrue(manifest["declared_untracked"])
        self.assertTrue(manifest["ignored"])
        self.assertTrue(any(item["kind"] == "symlink" for item in manifest["tracked"]))
        self.create_checkpoint()
        found = self.verify_checkpoint()
        self.assertEqual(found["review"]["value"]["retrieval_source"]["status"], "unknown")
        self.assertEqual(found["terminal_artifacts"]["report"]["sha256"],
                         checkpoint.sha256_file(self.run_dir / ".shiploop-runs/test-run/run/report.html"))

    def test_missing_result_is_rejected_before_review(self) -> None:
        (self.run_dir / "result.json").unlink()
        with self.assertRaises(checkpoint.CheckpointError):
            checkpoint.inspect_run(run_dir=self.run_dir, inventory_path=self.inventory_path, trial_id="trial-a",
                                   link="base", output_path=self.output_root / "missing-snapshot.json")

    def test_failed_result_is_rejected(self) -> None:
        result = json.loads((self.run_dir / "result.json").read_text())
        result["pass"] = False
        write_json(self.run_dir / "result.json", result)
        with self.assertRaisesRegex(checkpoint.CheckpointError, "pass is not true"):
            checkpoint.inspect_run(run_dir=self.run_dir, inventory_path=self.inventory_path, trial_id="trial-a",
                                   link="base", output_path=self.output_root / "failed-snapshot.json")

    def test_wrong_link_and_prompt_identity_are_rejected(self) -> None:
        self.create_checkpoint()
        wrong_link = copy.deepcopy(self.identity)
        wrong_link["link"] = "filter"
        with self.assertRaisesRegex(checkpoint.CheckpointError, "expected predecessor"):
            self.verify_checkpoint(wrong_link)
        wrong_prompt = copy.deepcopy(self.identity)
        wrong_prompt["prompt"]["invoked_sha256"] = "0" * 64
        with self.assertRaisesRegex(checkpoint.CheckpointError, "expected predecessor"):
            self.verify_checkpoint(wrong_prompt)

    def test_changed_tracked_file_after_review_is_rejected(self) -> None:
        self.create_checkpoint()
        (self.work / "README.md").write_text("changed after review\n", encoding="utf-8")
        with self.assertRaisesRegex(checkpoint.CheckpointError, "manifest changed"):
            self.verify_checkpoint()

    def test_changed_declared_untracked_file_after_review_is_rejected(self) -> None:
        self.create_checkpoint()
        (self.work / "declared-untracked.txt").write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(checkpoint.CheckpointError, "manifest changed"):
            self.verify_checkpoint()

    def test_changed_ignored_file_after_review_is_rejected(self) -> None:
        self.create_checkpoint()
        (self.work / "ignored-data.txt").write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(checkpoint.CheckpointError, "manifest changed"):
            self.verify_checkpoint()

    def test_checkout_change_between_snapshot_and_checkpoint_is_rejected(self) -> None:
        (self.work / "README.md").write_text("changed after inspect\n", encoding="utf-8")
        with self.assertRaisesRegex(checkpoint.CheckpointError, "changed after the pre-review snapshot"):
            self.create_checkpoint()

    def test_terminal_receipt_or_report_change_after_review_is_rejected(self) -> None:
        self.create_checkpoint()
        report = self.run_dir / ".shiploop-runs/test-run/run/report.html"
        report.write_text("changed after review\n", encoding="utf-8")
        with self.assertRaisesRegex(checkpoint.CheckpointError, "terminal receipt or report changed"):
            self.verify_checkpoint()

    def test_wrong_release_and_check_identity_are_rejected(self) -> None:
        self.create_checkpoint()
        wrong_release = copy.deepcopy(self.identity)
        wrong_release["source"]["head"] = "0" * 40
        with self.assertRaisesRegex(checkpoint.CheckpointError, "expected predecessor"):
            self.verify_checkpoint(wrong_release)
        wrong_check = copy.deepcopy(self.identity)
        wrong_check["checks"]["files"]["checks"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(checkpoint.CheckpointError, "expected predecessor"):
            self.verify_checkpoint(wrong_check)

    def test_release_must_match_explicit_release_pin_and_trailer(self) -> None:
        identity = launch.release_identity(self.release, self.release_info["head"])
        self.assertEqual(identity["release_trailer"], self.release_info["release_trailer"])
        with self.assertRaisesRegex(checkpoint.CheckpointError, "--release-commit"):
            launch.release_identity(self.release, "0" * 40)

    def test_increment_refuses_missing_checkpoint_before_model_launch(self) -> None:
        args = self._launch_args(link="filter")
        with self.assertRaises(checkpoint.CheckpointError):
            launch.build_plan(args)

    def test_interrupted_filter_resume_uses_same_output_without_copying_or_replaying_base(self) -> None:
        self.create_checkpoint()
        run_dir, _, _ = self._make_interrupted_link()
        plan = launch.build_plan(self._launch_args(link="filter", resume=True, checkpoint_path=self.checkpoint_path))
        argv = plan["argv"]
        self.assertIn("--resume-run", argv)
        self.assertEqual(argv[argv.index("--resume-run") + 1], str(run_dir.resolve()))
        for forbidden in ("--continue-from", "--prompt", "--check", "--output"):
            self.assertNotIn(forbidden, argv)
        self.assertEqual(plan["resume_state"]["work_snapshot"], checkpoint.work_snapshot(run_dir / "work"))
        self.assertEqual(plan["predecessor"]["run_dir"], str(self.run_dir.resolve()))
        self.assertNotIn("--timeout", argv)
        self.assertNotIn("--max-turns", argv)

    def test_resume_rejects_completed_product_test_failure(self) -> None:
        self.create_checkpoint()
        run_dir, row, _ = self._make_interrupted_link()
        result = json.loads((run_dir / "result.json").read_text())
        result["checks"][0]["pass"] = False
        result["outcome_class"] = "FAILED"
        result["termination"].update({"engine_status": "done", "engine_stage": "done",
                                      "engine_unaccepted_stage": None, "process_status": "exited"})
        result["process"].update({"status": "exited", "returncode": 0,
                                  "sessions": [{"status": "exited", "returncode": 0}]})
        result["shiploop"].update({"status": "done", "report_html": True})
        write_json(run_dir / "result.json", result)
        row["result_sha256"] = checkpoint.sha256_file(run_dir / "result.json")
        write_json(self.inventory_path, {"schema": checkpoint.RUNS_SCHEMA, "runs": [self.row, row]})
        with self.assertRaisesRegex(checkpoint.CheckpointError, "failed host interruption"):
            launch.build_plan(self._launch_args(link="filter", resume=True, checkpoint_path=self.checkpoint_path))

    def test_unfinished_interruption_can_resume_with_failed_or_missing_functional_checks(self) -> None:
        self.create_checkpoint()
        run_dir, row, _ = self._make_interrupted_link()
        result_path = run_dir / "result.json"
        result = json.loads(result_path.read_text())
        result["checks"][0]["pass"] = False
        write_json(result_path, result)
        row["result_sha256"] = checkpoint.sha256_file(result_path)
        write_json(self.inventory_path, {"schema": checkpoint.RUNS_SCHEMA, "runs": [self.row, row]})
        plan = launch.build_plan(self._launch_args(link="filter", resume=True, checkpoint_path=self.checkpoint_path))
        self.assertIn("--resume-run", plan["argv"])

        result = json.loads(result_path.read_text())
        result["checks"] = result["checks"][1:]
        write_json(result_path, result)
        row["result_sha256"] = checkpoint.sha256_file(result_path)
        write_json(self.inventory_path, {"schema": checkpoint.RUNS_SCHEMA, "runs": [self.row, row]})
        plan = launch.build_plan(self._launch_args(link="filter", resume=True, checkpoint_path=self.checkpoint_path))
        self.assertIn("--resume-run", plan["argv"])

    def test_final_checkpoint_still_requires_complete_passing_check_set(self) -> None:
        result = json.loads((self.run_dir / "result.json").read_text())
        result["checks"] = result["checks"][:-1]
        write_json(self.run_dir / "result.json", result)
        self.row["result_sha256"] = checkpoint.sha256_file(self.run_dir / "result.json")
        self._write_inventory()
        with self.assertRaisesRegex(checkpoint.CheckpointError, "complete pinned check set"):
            checkpoint.inspect_run(run_dir=self.run_dir, inventory_path=self.inventory_path, trial_id="trial-a",
                                   link="base", output_path=self.output_root / "missing-check-snapshot.json")

    def test_resume_rejects_owner_blocked_run(self) -> None:
        self.create_checkpoint()
        run_dir, row, _ = self._make_interrupted_link()
        result = json.loads((run_dir / "result.json").read_text())
        result["outcome_class"] = "BLOCKED"
        result["termination"]["engine_status"] = "blocked"
        result["shiploop"]["status"] = "blocked"
        write_json(run_dir / "result.json", result)
        row["result_sha256"] = checkpoint.sha256_file(run_dir / "result.json")
        write_json(self.inventory_path, {"schema": checkpoint.RUNS_SCHEMA, "runs": [self.row, row]})
        with self.assertRaisesRegex(checkpoint.CheckpointError, "failed host interruption"):
            launch.build_plan(self._launch_args(link="filter", resume=True, checkpoint_path=self.checkpoint_path))

    def test_resume_rejects_deliberate_stop(self) -> None:
        self.create_checkpoint()
        run_dir, row, _ = self._make_interrupted_link()
        result = json.loads((run_dir / "result.json").read_text())
        result["outcome_class"] = "STOPPED"
        result["process"]["status"] = "stopped"
        result["termination"]["process_status"] = "stopped"
        result["termination"]["resume_stop"] = "stopped by /tmp/stop"
        write_json(run_dir / "result.json", result)
        row["result_sha256"] = checkpoint.sha256_file(run_dir / "result.json")
        write_json(self.inventory_path, {"schema": checkpoint.RUNS_SCHEMA, "runs": [self.row, row]})
        with self.assertRaisesRegex(checkpoint.CheckpointError, "failed host interruption"):
            launch.build_plan(self._launch_args(link="filter", resume=True, checkpoint_path=self.checkpoint_path))

    def test_resume_rejects_changed_partial_product_work(self) -> None:
        self.create_checkpoint()
        run_dir, _, _ = self._make_interrupted_link()
        (run_dir / "work" / "ignored-data.txt").write_text("edited after interruption\n", encoding="utf-8")
        with self.assertRaisesRegex(checkpoint.CheckpointError, "partial product work changed"):
            launch.build_plan(self._launch_args(link="filter", resume=True, checkpoint_path=self.checkpoint_path))

    def test_resume_archives_original_and_retains_a_failed_resume_attempt(self) -> None:
        self.create_checkpoint()
        run_dir, row, _ = self._make_interrupted_link()
        original_result = (run_dir / "result.json").read_bytes()
        original_invocation = (run_dir / "invocation.json").read_bytes()
        plan_args = self._launch_args(link="filter", resume=True, checkpoint_path=self.checkpoint_path)
        source_run = (self.release / "test/shiploop_e2e/run.py").resolve()
        invocation_resume = run_dir / "invocation-resume-codex-test.json"

        def fake_run(command, *args, **kwargs):
            if len(command) > 2 and Path(command[2]) == source_run:
                write_json(invocation_resume, {
                    "case": "custom", "cwd": str((run_dir / "work").resolve()),
                    "host": checkpoint.MODEL["host"], "model": checkpoint.MODEL["model"],
                    "effort": checkpoint.MODEL["effort"],
                    "versions": {"source": "checkout", "local_head": self.release_info["head"]},
                    "checks": row["identity"]["checks"]["commands"], "resumed_run": str(run_dir),
                })
                result = json.loads((run_dir / "result.json").read_text())
                result["process"]["returncode"] = 1
                result["termination"]["returncode"] = 1
                result["resume_attempt_fixture"] = "failed after host resume"
                result["shiploop"]["status"] = "active"
                write_json(run_dir / "result.json", result)
                write_json(run_dir / "metrics.json", {"fixture": "failed resumed metrics"})
                return subprocess.CompletedProcess(command, 1)
            return self._real_subprocess_run(command, *args, **kwargs)

        self._real_subprocess_run = subprocess.run
        with mock.patch("launch.subprocess.run", side_effect=fake_run):
            exit_code = launch.main([
                "--release-tree", str(self.release), "--release-commit", self.release_info["head"],
                "--output-root", str(self.output_root), "--inventory", str(self.inventory_path),
                "--calibration", str(self.output_root / "calibration.json"),
                "--trial-id", "trial-a", "--link", "filter", "--checkpoint", str(self.checkpoint_path), "--resume",
            ])
        self.assertEqual(exit_code, 1)
        inventory = checkpoint.read_inventory(self.inventory_path)
        final = checkpoint.inventory_row(inventory, "trial-a:filter")
        self.assertEqual(final["status"], "failed")
        self.assertEqual(len(final["attempts"]), 1)
        attempt = final["attempts"][0]
        self.assertEqual(attempt["status_after"], "failed")
        self.assertEqual(final["original_invocation_sha256"], checkpoint.sha256_bytes(original_invocation))
        archive = Path(attempt["archive"]["path"])
        self.assertEqual((archive / "files/result.json").read_bytes(), original_result)
        self.assertEqual((archive / "files/invocation.json").read_bytes(), original_invocation)
        self.assertIsNotNone(attempt["resume_invocation"])
        self.assertEqual(attempt["resume_invocation"]["sha256"], checkpoint.sha256_file(invocation_resume))
        self.assertNotEqual(final["result_sha256"], checkpoint.sha256_bytes(original_result))
        checkpoint.validate_resume_history(final, run_dir, final["identity"])
        (archive / "files/result.json").write_bytes(b"changed archive\n")
        with self.assertRaisesRegex(checkpoint.CheckpointError, "archived resume artifact changed"):
            checkpoint.validate_resume_history(final, run_dir, final["identity"])

    def test_calibration_must_exist_and_pass_before_launch(self) -> None:
        args = self._launch_args(trial_id="trial-calibration")
        args.calibration = self.output_root / "missing-calibration.json"
        with self.assertRaisesRegex(checkpoint.CheckpointError, "calibration file"):
            launch.build_plan(args)
        failed = json.loads((self.output_root / "calibration.json").read_text())
        failed["summary"]["all_expectations_matched"] = False
        write_json(self.output_root / "calibration.json", failed)
        with self.assertRaisesRegex(checkpoint.CheckpointError, "did not pass"):
            launch.build_plan(self._launch_args(trial_id="trial-failed-calibration"))

    def test_changed_calibration_or_checker_manifest_is_rejected(self) -> None:
        checkpoint.validate_source_and_checks(self.identity)
        calibration_path = self.output_root / "calibration.json"
        original = json.loads(calibration_path.read_text())
        changed_input = copy.deepcopy(original)
        changed_input["inputs"]["checks"]["sha256"] = "0" * 64
        changed_input["inputs_after"] = copy.deepcopy(changed_input["inputs"])
        write_json(calibration_path, changed_input)
        with self.assertRaisesRegex(checkpoint.CheckpointError, "input 'checks' changed"):
            launch.build_plan(self._launch_args(trial_id="trial-changed-checker"))
        write_json(calibration_path, original)
        plan = launch.build_plan(self._launch_args(trial_id="trial-after-calibration"))
        calibration_path.write_text(calibration_path.read_text() + " ", encoding="utf-8")
        with self.assertRaisesRegex(checkpoint.CheckpointError, "calibration file changed"):
            checkpoint.validate_source_and_checks(plan["identity"])

    def test_calibration_allows_csv_report_path_difference_when_digest_matches(self) -> None:
        calibration_path = self.output_root / "calibration.json"
        calibration = json.loads(calibration_path.read_text())
        apparatus_csv = (checkpoint.SOURCE_ROOT / "test/shiploop_e2e/checks/csv_report.py").resolve()
        calibration["inputs"]["csv_report"]["path"] = str(apparatus_csv)
        calibration["inputs_after"]["csv_report"]["path"] = str(apparatus_csv)
        write_json(calibration_path, calibration)
        plan = launch.build_plan(self._launch_args(trial_id="trial-csv-path"))
        self.assertEqual(plan["identity"]["checks"]["files"]["csv_report"]["path"], str(self.csv_report))
        self.assertEqual(plan["identity"]["calibration"]["inputs"]["csv_report"]["sha256"],
                         checkpoint.sha256_file(self.csv_report))

    def test_dry_run_argv_is_one_unbounded_released_link(self) -> None:
        args = self._launch_args(trial_id="trial-b")
        plan = launch.build_plan(args)
        argv = plan["argv"]
        self.assertEqual(argv[1], "-I")
        self.assertEqual(argv[2], str(self.release.resolve() / "test/shiploop_e2e/run.py"))
        self.assertIn("--source", argv)
        self.assertEqual(argv[argv.index("--source") + 1], "checkout")
        self.assertEqual(argv[argv.index("--model") + 1], "gpt-6.1-terra")
        self.assertEqual(argv[argv.index("--effort") + 1], "high")
        self.assertNotIn("--timeout", argv)
        self.assertNotIn("--max-turns", argv)
        self.assertNotIn("--max-resumes", argv)
        commands = [argv[index + 1] for index, value in enumerate(argv[:-1]) if value == "--check"]
        self.assertEqual([command.rsplit(" ", 1)[-1] for command in commands[:5]],
                         ["unit", "totals", "invalid", "missing", "empty"])
        self.assertTrue(commands[-1].endswith("checks.py base-scope"))

    def test_unsafe_review_path_is_rejected(self) -> None:
        review = json.loads(self.review_path.read_text())
        review["dimensions"][checkpoint.DIMENSIONS[0]]["evidence"][0]["path"] = "../outside.txt"
        write_json(self.review_path, review)
        with self.assertRaisesRegex(checkpoint.CheckpointError, "unsafe review evidence path"):
            self.create_checkpoint()

    def test_review_without_all_five_explicit_passes_is_rejected(self) -> None:
        review = json.loads(self.review_path.read_text())
        review["dimensions"][checkpoint.DIMENSIONS[-1]]["status"] = "unknown"
        write_json(self.review_path, review)
        with self.assertRaisesRegex(checkpoint.CheckpointError, "unknown, or failed"):
            self.create_checkpoint()

    def test_checkout_change_between_grade_and_inspect_is_rejected(self) -> None:
        (self.work / "README.md").write_text("changed before human review\n", encoding="utf-8")
        with self.assertRaisesRegex(checkpoint.CheckpointError, "changed after grading"):
            checkpoint.inspect_run(run_dir=self.run_dir, inventory_path=self.inventory_path, trial_id="trial-a",
                                   link="base", output_path=self.output_root / "changed-snapshot.json")

    def test_unsafe_source_output_path_is_rejected(self) -> None:
        with self.assertRaisesRegex(checkpoint.CheckpointError, "outside"):
            checkpoint.external_path(checkpoint.SOURCE_ROOT / "unsafe", "test output", (checkpoint.SOURCE_ROOT,))
        args = self._launch_args(output_root=checkpoint.SOURCE_ROOT / "unsafe")
        with self.assertRaisesRegex(checkpoint.CheckpointError, "outside"):
            launch.build_plan(args)

    def test_child_result_must_report_the_reviewed_start_head(self) -> None:
        predecessor = self.create_checkpoint()
        child = self.output_root / "trial-a" / "filter"
        child.mkdir(parents=True)
        child_work = child / "work"
        shutil.copytree(self.work, child_work, symlinks=True)
        (child_work / "increment.py").write_text("filter\n", encoding="utf-8")
        git(child_work, "add", "increment.py")
        git(child_work, "commit", "-qm", "filter increment")
        correct = {"follow_on": {
            "prior": str(self.run_dir),
            "start_head": predecessor["work_snapshot"]["head"],
            "prior_case": "custom",
            "prior_pass": True,
        }}
        self.assertTrue(launch._validate_copied_lineage(correct, child, predecessor)["pass"])
        wrong = copy.deepcopy(correct)
        wrong["follow_on"]["start_head"] = "0" * 40
        self.assertFalse(launch._validate_copied_lineage(wrong, child, predecessor)["pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
