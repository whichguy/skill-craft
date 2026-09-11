#!/usr/bin/env python3
"""Hermetic tests for ShipLoop's script-owned check and commit evidence."""

from __future__ import annotations

import copy
import importlib.util
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills" / "shiploop" / "scripts" / "shiploop_evidence.py"
SPEC = importlib.util.spec_from_file_location("shiploop_evidence", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
shiploop_evidence = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = shiploop_evidence
SPEC.loader.exec_module(shiploop_evidence)

EvidenceError = shiploop_evidence.EvidenceError
fingerprint = shiploop_evidence.fingerprint
history = shiploop_evidence.history
run_checks = shiploop_evidence.run_checks
validate_commit = shiploop_evidence.validate_commit
validate_manifest = shiploop_evidence.validate_manifest
validate_results = shiploop_evidence.validate_results


def git(repo: Path, *argv: str) -> str:
    return subprocess.check_output(
        ["git", "-C", os.fspath(repo), *argv], text=True, stderr=subprocess.STDOUT
    ).strip()


def commit(repo: Path, subject: str, body: str, *, empty: bool = True) -> str:
    argv = ["git", "-C", os.fspath(repo), "commit"]
    if empty:
        argv.append("--allow-empty")
    argv.extend(["-q", "-m", subject, "-m", body])
    subprocess.check_call(argv)
    return git(repo, "rev-parse", "HEAD")


def evidence_body(
    action_id: str,
    *,
    validation: str = "- python3 test/shiploop-evidence.test.py: PASS",
) -> str:
    return "\n\n".join(
        [
            "Review:\n- Read the previous primary commit and its recorded checks.",
            "Changes:\n- No product files changed; this is an audit-only iteration.",
            f"Validation:\n{validation}",
            "Key learnings:\n- Fresh check evidence must match the checked working tree.",
            f"ShipLoop-Iteration: {action_id}",
        ]
    )


class ShipLoopEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="shiploop-evidence-test.")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.check_call(["git", "init", "-q", os.fspath(self.repo)])
        subprocess.check_call(
            [
                "git",
                "-C",
                os.fspath(self.repo),
                "config",
                "user.email",
                "test@example.invalid",
            ]
        )
        subprocess.check_call(
            [
                "git",
                "-C",
                os.fspath(self.repo),
                "config",
                "user.name",
                "ShipLoop Evidence Test",
            ]
        )
        (self.repo / "tracked.txt").write_text("baseline\n", encoding="utf-8")
        subprocess.check_call(["git", "-C", os.fspath(self.repo), "add", "tracked.txt"])
        subprocess.check_call(
            ["git", "-C", os.fspath(self.repo), "commit", "-qm", "baseline"]
        )
        self.baseline = git(self.repo, "rev-parse", "HEAD")
        self.evidence_dir = self.root / "evidence"

    def manifest(self, *, argv: list[str] | None = None) -> dict:
        return {
            "checks": [
                {
                    "id": "lint-python",
                    "kind": "lint",
                    "argv": [sys.executable, "-c", "raise SystemExit(0)"],
                    "acceptance": [],
                },
                {
                    "id": "test-feature",
                    "kind": "test",
                    "argv": argv or [sys.executable, "-c", "raise SystemExit(0)"],
                    "acceptance": ["feature works"],
                },
            ]
        }

    def assertEvidenceError(self, callback) -> None:
        with self.assertRaises(EvidenceError):
            callback()

    def test_fingerprint_tracks_missing_modes_and_symlink_target_without_following(
        self,
    ) -> None:
        outside = self.root / "outside.txt"
        outside.write_text("outside-one\n", encoding="utf-8")
        (self.repo / "tool.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        (self.repo / "tool.sh").chmod(0o755)
        os.symlink(outside, self.repo / "outside-link")
        subprocess.check_call(
            ["git", "-C", os.fspath(self.repo), "add", "tool.sh", "outside-link"]
        )
        subprocess.check_call(
            [
                "git",
                "-C",
                os.fspath(self.repo),
                "commit",
                "-qm",
                "add executable and link",
            ]
        )
        before = fingerprint(self.repo)
        outside.write_text("outside-two\n", encoding="utf-8")
        self.assertEqual(
            before, fingerprint(self.repo), "fingerprint must not follow link targets"
        )
        os.unlink(self.repo / "outside-link")
        os.symlink("tracked.txt", self.repo / "outside-link")
        self.assertNotEqual(
            before, fingerprint(self.repo), "link target must be fingerprinted"
        )
        os.unlink(self.repo / "outside-link")
        (self.repo / "tool.sh").chmod(0o644)
        self.assertNotEqual(
            before,
            fingerprint(self.repo),
            "missing tracked files and modes are evidence",
        )

    def test_validate_manifest_requires_test_coverage_and_lint_or_noncode_reason(
        self,
    ) -> None:
        manifest = self.manifest()
        self.assertIsInstance(validate_manifest(manifest, ["feature works"]), dict)

        no_lint = copy.deepcopy(manifest)
        no_lint["checks"] = [row for row in no_lint["checks"] if row["kind"] != "lint"]
        self.assertEvidenceError(lambda: validate_manifest(no_lint, ["feature works"]))
        no_lint["lint_not_applicable"] = "noncode planning-only step"
        self.assertIsInstance(validate_manifest(no_lint, ["feature works"]), dict)

        uncovered = copy.deepcopy(manifest)
        self.assertEvidenceError(
            lambda: validate_manifest(uncovered, ["feature works", "other output"])
        )
        wrong_acceptance = copy.deepcopy(manifest)
        wrong_acceptance["checks"][1]["acceptance"] = ["rough paraphrase"]
        self.assertEvidenceError(
            lambda: validate_manifest(wrong_acceptance, ["feature works"])
        )
        duplicate = copy.deepcopy(manifest)
        duplicate["checks"][1]["id"] = "lint-python"
        self.assertEvidenceError(
            lambda: validate_manifest(duplicate, ["feature works"])
        )

    def test_run_checks_writes_logs_and_validate_results_rejects_failed_missing_stale_and_mismatched(
        self,
    ) -> None:
        manifest = self.manifest()
        validate_manifest(manifest, ["feature works"])
        evidence = run_checks(self.repo, manifest, self.evidence_dir, "act-good")
        self.assertTrue(evidence["all_passed"])
        self.assertEqual(evidence["before_fingerprint"], evidence["after_fingerprint"])
        self.assertEqual(
            [row["status"] for row in evidence["checks"]], ["passed", "passed"]
        )
        for row in evidence["checks"]:
            self.assertTrue(Path(row["stdout_log"]).is_file())
            self.assertTrue(Path(row["stderr_log"]).is_file())
            self.assertTrue(Path(row["log_path"]).is_file())
            self.assertEqual(
                stat.S_IMODE(Path(row["stdout_log"]).stat().st_mode), 0o600
            )
            self.assertEqual(
                stat.S_IMODE(Path(row["stderr_log"]).stat().st_mode), 0o600
            )
            self.assertEqual(stat.S_IMODE(Path(row["log_path"]).stat().st_mode), 0o600)
            self.assertRegex(row["started_at"], r"^\d{4}-\d{2}-\d{2}T.*Z$")
            self.assertRegex(row["finished_at"], r"^\d{4}-\d{2}-\d{2}T.*Z$")
            self.assertIsInstance(row["duration_ms"], int)
            self.assertGreaterEqual(row["duration_ms"], 0)
        self.assertEqual(stat.S_IMODE(self.evidence_dir.stat().st_mode), 0o700)
        self.assertIs(
            validate_results(evidence, self.repo, manifest, "act-good"), evidence
        )

        missing = copy.deepcopy(evidence)
        missing["checks"].pop()
        self.assertEvidenceError(
            lambda: validate_results(missing, self.repo, manifest, "act-good")
        )
        mismatched = copy.deepcopy(evidence)
        mismatched["checks"][0]["argv"] = ["not-the-linter"]
        self.assertEvidenceError(
            lambda: validate_results(mismatched, self.repo, manifest, "act-good")
        )
        stale = copy.deepcopy(evidence)
        (self.repo / "tracked.txt").write_text(
            "changed after check\n", encoding="utf-8"
        )
        self.assertEvidenceError(
            lambda: validate_results(stale, self.repo, manifest, "act-good")
        )

        failed = run_checks(
            self.repo,
            self.manifest(argv=[sys.executable, "-c", "raise SystemExit(7)"]),
            self.evidence_dir / "failed",
            "act-failed",
        )
        self.assertFalse(failed["all_passed"])
        self.assertEqual(failed["checks"][1]["exit"], 7)
        self.assertEvidenceError(
            lambda: validate_results(
                failed,
                self.repo,
                self.manifest(argv=[sys.executable, "-c", "raise SystemExit(7)"]),
                "act-failed",
            )
        )

    def test_run_checks_rejects_timeout_and_content_change(self) -> None:
        timeout_manifest = self.manifest(
            argv=[sys.executable, "-c", "import time; time.sleep(2)"]
        )
        timeout_evidence = run_checks(
            self.repo,
            timeout_manifest,
            self.evidence_dir / "timeout",
            "act-timeout",
            timeout=0.05,
        )
        self.assertFalse(timeout_evidence["all_passed"])
        self.assertEqual(timeout_evidence["checks"][1]["status"], "timeout")
        self.assertEvidenceError(
            lambda: validate_results(
                timeout_evidence, self.repo, timeout_manifest, "act-timeout"
            )
        )

        changed_manifest = self.manifest(
            argv=[
                sys.executable,
                "-c",
                "from pathlib import Path; Path('tracked.txt').write_text('mutated by test\\n')",
            ]
        )
        changed_evidence = run_checks(
            self.repo, changed_manifest, self.evidence_dir / "changed", "act-changed"
        )
        self.assertFalse(changed_evidence["all_passed"])
        self.assertTrue(changed_evidence["content_changed"])
        self.assertEvidenceError(
            lambda: validate_results(
                changed_evidence, self.repo, changed_manifest, "act-changed"
            )
        )

    @unittest.skipUnless(
        os.name == "posix", "process-group cancellation is POSIX-specific"
    )
    def test_timeout_cancels_spawned_posix_child_without_writing_outside_fixture(
        self,
    ) -> None:
        marker = self.repo / "child-survived.txt"
        child_code = (
            "from pathlib import Path; import time; time.sleep(0.35); "
            f"Path({os.fspath(marker)!r}).write_text('survived\\n')"
        )
        parent_code = (
            "import subprocess,sys,time; "
            f"subprocess.Popen([sys.executable, '-c', {child_code!r}]); "
            "time.sleep(2)"
        )
        started = time.monotonic()
        evidence = run_checks(
            self.repo,
            self.manifest(argv=[sys.executable, "-c", parent_code]),
            self.evidence_dir / "child-timeout",
            "act-child-timeout",
            timeout=0.05,
        )
        self.assertLess(time.monotonic() - started, 0.8)
        self.assertEqual(evidence["checks"][1]["status"], "timeout")
        time.sleep(0.45)
        self.assertFalse(
            marker.exists(),
            "the timed-out process group must not leave a child running",
        )

    def test_history_returns_full_bodies_and_honors_pagination(self) -> None:
        first_body = "first body line\n\nfull detail one"
        first = commit(self.repo, "first iteration", first_body)
        second_body = "second body line\n\nfull detail two"
        second = commit(self.repo, "second iteration", second_body)
        newest = history(self.repo, limit=1)
        self.assertEqual(
            newest,
            [{"sha": second, "body": "second iteration\n\n" + second_body + "\n"}],
        )
        older = history(self.repo, limit=1, skip=1)
        self.assertEqual(
            older, [{"sha": first, "body": "first iteration\n\n" + first_body + "\n"}]
        )
        multiple = history(self.repo, limit=3)
        self.assertEqual(
            [row["sha"] for row in multiple], [second, first, self.baseline]
        )
        for row in multiple:
            self.assertRegex(row["sha"], re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$"))

    def test_validate_commit_requires_new_head_structured_evidence_and_allows_empty_audit(
        self,
    ) -> None:
        action = "iteration-001"
        valid = commit(self.repo, "ShipLoop audit iteration", evidence_body(action))
        result = validate_commit(self.repo, valid, self.baseline, action)
        self.assertEqual(result["sha"], valid)
        self.assertEqual(result["body"].splitlines()[0], "ShipLoop audit iteration")
        self.assertTrue(
            result["empty"], "allow-empty audit commit is a valid primary commit"
        )

        self.assertEvidenceError(
            lambda: validate_commit(self.repo, valid, valid, action)
        )
        self.assertEvidenceError(
            lambda: validate_commit(self.repo, self.baseline, self.baseline, action)
        )

        later = commit(self.repo, "another iteration", evidence_body("iteration-002"))
        self.assertEvidenceError(
            lambda: validate_commit(self.repo, valid, self.baseline, action)
        )
        self.assertEvidenceError(
            lambda: validate_commit(self.repo, later, valid, action)
        )

    def test_validate_commit_rejects_missing_sections_and_subjective_quality_claims(
        self,
    ) -> None:
        bad = commit(self.repo, "unstructured", "Only a claim, no evidence.")
        self.assertEvidenceError(
            lambda: validate_commit(self.repo, bad, self.baseline, "iteration-bad")
        )

        subjective = commit(
            self.repo,
            "subjective",
            evidence_body(
                "iteration-subjective", validation="- The quality looks good."
            ),
        )
        self.assertEvidenceError(
            lambda: validate_commit(self.repo, subjective, bad, "iteration-subjective")
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
