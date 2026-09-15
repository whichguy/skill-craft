#!/usr/bin/env python3
"""Packaging and relocation checks for ShipLoop's Improve receipt helper."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SYNC = ROOT / "scripts" / "sync-improve-review-progress.py"
IMPROVE = ROOT / "skills" / "improve"
SHIPLOOP = ROOT / "skills" / "shiploop"


class ReviewProgressPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.maxDiff = None

    def isolated_environment(self, home: Path) -> dict[str, str]:
        environment = {
            key: value
            for key, value in os.environ.items()
            if key not in {"PYTHONHOME", "PYTHONPATH"}
        }
        environment.update(
            {
                "HOME": str(home),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
            }
        )
        return environment

    def run_command(
        self, cwd: Path, environment: dict[str, str], *args: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", *args],
            cwd=cwd,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def markdown_record(self, path: Path) -> dict:
        text = path.read_text(encoding="utf-8")
        start = text.index("```shiploop-state\n") + len("```shiploop-state\n")
        end = text.index("\n```", start)
        return json.loads(text[start:end])

    def write_result(self, path: Path, payload: dict) -> None:
        path.write_text(
            "# Package fixture result\n\n```shiploop-state\n"
            + json.dumps(payload, indent=2, sort_keys=True)
            + "\n```\n",
            encoding="utf-8",
        )

    def copy_bundle_tree(self, parent: Path) -> Path:
        root = parent / "bundle tree with spaces"
        ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
        shutil.copytree(IMPROVE, root / "skills" / "improve", ignore=ignore)
        shutil.copytree(SHIPLOOP, root / "skills" / "shiploop", ignore=ignore)
        (root / "scripts").mkdir(parents=True)
        shutil.copy2(SYNC, root / "scripts" / SYNC.name)
        return root

    def copy_shiploop_alone(self, parent: Path) -> Path:
        package = parent / "isolated ShipLoop package with spaces"
        shutil.copytree(
            SHIPLOOP,
            package,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
        )
        return package

    def complete_current(
        self,
        package: Path,
        workspace: Path,
        run_dir: Path,
        environment: dict[str, str],
        state: dict,
        payload: dict,
    ) -> tuple[subprocess.CompletedProcess[str], dict]:
        action_id = state["action"]["id"]
        result_path = run_dir / "inbox" / f"{action_id}.md"
        self.write_result(result_path, payload)
        completed = self.run_command(
            workspace,
            environment,
            str(package / "scripts" / "shiploop"),
            "complete",
            "--run-dir",
            str(run_dir),
            "--result",
            str(result_path),
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertNotIn("--action", completed.args)
        return completed, self.markdown_record(run_dir / "state.md")

    def test_source_vendor_reference_and_managed_pin_bytes_are_current(self) -> None:
        source_helper = IMPROVE / "scripts" / "review_progress.py"
        bundled_helper = SHIPLOOP / "scripts" / "_improve_review_progress.py"
        source_reference = IMPROVE / "references" / "review-progress.md"
        bundled_reference = SHIPLOOP / "references" / "improve-review-progress.md"

        self.assertEqual(source_helper.read_bytes(), bundled_helper.read_bytes())
        self.assertEqual(source_reference.read_bytes(), bundled_reference.read_bytes())

        managed_source = IMPROVE / "scripts" / "managed_controller.py"
        managed_vendor = SHIPLOOP / "scripts" / "_improve_managed.py"
        managed_contract = IMPROVE / "references" / "managed-consumer.md"
        managed_contract_vendor = SHIPLOOP / "references" / "improve-managed-consumer.md"
        pin = json.loads(
            (SHIPLOOP / "references" / "improve-managed-controller-pin.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(managed_source.read_bytes(), managed_vendor.read_bytes())
        self.assertEqual(managed_contract.read_bytes(), managed_contract_vendor.read_bytes())
        self.assertEqual(
            pin["sha256"], hashlib.sha256(managed_source.read_bytes()).hexdigest()
        )
        self.assertEqual(
            pin["contract_sha256"], hashlib.sha256(managed_contract.read_bytes()).hexdigest()
        )

    def test_default_sync_check_rejects_a_mismatched_bundle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="improve-review-progress-package-") as directory:
            root = self.copy_bundle_tree(Path(directory))
            home = root / "isolated-home"
            home.mkdir()
            environment = self.isolated_environment(home)
            sync = root / "scripts" / SYNC.name

            checked = self.run_command(root, environment, str(sync))
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertIn("bundle verified", checked.stdout)

            bundled_helper = root / "skills" / "shiploop" / "scripts" / "_improve_review_progress.py"
            bundled_helper.write_bytes(bundled_helper.read_bytes() + b"\n")
            mismatch = self.run_command(root, environment, str(sync))
            self.assertNotEqual(mismatch.returncode, 0)
            self.assertIn("bundle differs", mismatch.stderr)

    def test_shiploop_alone_runs_two_review_receipt_callbacks_from_result_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="improve-review-progress-relocation-") as directory:
            parent = Path(directory)
            package = self.copy_shiploop_alone(parent)
            workspace = parent / "product workspace with spaces"
            workspace.mkdir()
            workspace = workspace.resolve()
            run_dir = workspace / "navigator run with spaces"
            home = parent / "isolated-home"
            home.mkdir()
            environment = self.isolated_environment(home)
            cli = package / "scripts" / "shiploop"

            self.assertFalse((parent / "skills" / "improve").exists())
            initialized = self.run_command(
                workspace,
                environment,
                str(cli),
                "init",
                "--repo",
                str(workspace),
                "--run-dir",
                str(run_dir),
                "--review-receipts",
                "--prompt",
                "Exercise the relocated receipt-only Improve navigator path.",
            )
            self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
            self.assertIn("ShipLoop navigator | intake", initialized.stdout)
            self.assertNotIn("--action", initialized.stdout)

            state = self.markdown_record(run_dir / "state.md")
            self.assertEqual(
                (state["navigator_protocol_version"], state["stage"], state["revision"]),
                (2, "intake", 0),
            )
            for expected_stage in ("discovery", "research", "research-improve"):
                _, state = self.complete_current(
                    package,
                    workspace,
                    run_dir,
                    environment,
                    state,
                    {"outcome": "done", "summary": f"Completed {state['stage']}."},
                )
                self.assertEqual(state["stage"], expected_stage)

            candidate = "relocated candidate and scoped context"
            review_result = {
                "outcome": "done",
                "summary": "No worthwhile change after the scoped review.",
                "evidence_refs": ["notes/relocated-review.md"],
                "review": {
                    "candidate_before": candidate,
                    "candidate_after": candidate,
                    "classification": "none",
                    "checks": "passed",
                    "improvements_complete": True,
                    "open_findings": [],
                },
            }
            first, state = self.complete_current(
                package, workspace, run_dir, environment, state, review_result
            )
            self.assertIn("Completed qualifying review streak: 1/2", first.stdout)
            self.assertEqual((state["stage"], state["revision"]), ("research-improve", 4))

            second, state = self.complete_current(
                package, workspace, run_dir, environment, state, review_result
            )
            self.assertIn("ShipLoop navigator | spec", second.stdout)
            self.assertEqual((state["stage"], state["revision"]), ("spec", 5))
            self.assertEqual(len(state["history"]), 5)
            self.assertEqual(len(state["accepted"]), 5)
            self.assertTrue((run_dir / "results").is_dir())
            self.assertFalse((workspace / ".until-loop").exists())
            self.assertFalse((run_dir / ".until-loop").exists())
            self.assertFalse((run_dir / "state.json").exists())
            self.assertFalse(any(package.rglob("__pycache__")))


if __name__ == "__main__":
    unittest.main()
