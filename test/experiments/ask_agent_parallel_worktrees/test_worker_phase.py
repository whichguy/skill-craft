"""Phase-wrapper tests using synthetic fixture edits, never a native worker."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import fixture
import operations
import worker_phase


class WorkerPhaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ask agent phase ")
        self.run = (Path(self.temp.name) / "run with spaces").resolve()
        self.manifest = fixture.prepare_fixture(
            self.run, 3, "parallel", source_skill=fixture.default_skill_root()
        )
        operations.prepare_batch(self.run)
        self.setup = json.loads((self.run / "operator" / "setup-result.json").read_text())
        self.worker = self.setup["workers"][0]
        self.root = Path(self.worker["worktree"]).resolve()
        self.script = Path(worker_phase.__file__).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def _cli(self, phase, cwd=None):
        command = [sys.executable, "-B", str(self.script), "--run", str(self.run),
                   "--worker", "1", "--phase", phase]
        return subprocess.run(command, cwd=cwd or self.root, capture_output=True, text=True)

    def test_start_and_finish_retain_bound_commands_and_patch_path(self):
        start = self._cli("start")
        self.assertEqual(start.returncode, 0, start.stderr)
        start_result = json.loads(start.stdout)
        self.assertEqual(start_result["status"], "PASSED")
        self.assertEqual(start_result["root"], str(self.root))
        self.assertEqual(start_result["receipt"], self.worker["receipt"])
        self.assertTrue(start_result["checks"]["helper_context_verified"])

        module = self.root / "src" / "step_1.py"
        module.write_text("def transform(x):\n    return 2 * x + 1\n", encoding="utf-8")
        finish = self._cli("finish")
        self.assertEqual(finish.returncode, 0, finish.stderr)
        finish_result = json.loads(finish.stdout)
        self.assertEqual(finish_result["status"], "PASSED")
        self.assertEqual(finish_result["root"], str(self.root))
        self.assertEqual(finish_result["receipt"], self.worker["receipt"])
        self.assertTrue(Path(finish_result["patch_path"]).is_file())
        self.assertEqual(finish_result["patch_sha256"], fixture.sha256_file(Path(finish_result["patch_path"])))
        self.assertTrue(finish_result["checks"]["worker_check_passed"])
        self.assertTrue(finish_result["checks"]["fixture_probe_passed"])
        self.assertTrue(finish_result["checks"]["returned_patch_bound"])

        for phase, expected_labels in (
            ("start", ["check-context", "probe"]),
            ("finish", ["worker-check", "probe", "inspect-returned"]),
        ):
            attempt = self.run / "operator" / "worker-phases" / f"worker-1-{phase}" / "attempt.json"
            record = json.loads(attempt.read_text(encoding="utf-8"))
            self.assertEqual(record["status"], "PASSED")
            self.assertEqual([item["label"] for item in record["calls"]], expected_labels)
            for item in record["calls"]:
                evidence = json.loads(Path(item["evidence"]).read_text(encoding="utf-8"))
                self.assertEqual(evidence["cwd"], str(self.root))
                self.assertIsInstance(evidence["argv"], list)
                self.assertEqual(evidence["status"], "COMPLETED")
                if item["label"] == "probe":
                    self.assertIn("probe", evidence["argv"])
                    self.assertEqual(evidence["argv"][-1], phase)
                if item["label"] == "inspect-returned":
                    self.assertEqual(evidence["argv"][-6:],
                                     ["--phase", "returned", "--delivery-mode", "patch",
                                      "--artifact", ".experiment-local/owner.txt"])
                    self.assertEqual(evidence["json"]["evidence"]["contribution_patch"],
                                     finish_result["patch_path"])

    def test_nonprepared_cwd_fails_and_retains_failure(self):
        result = self._cli("start", cwd=Path(self.manifest["paths"]["caller"]))
        self.assertEqual(result.returncode, 2)
        diagnostic = json.loads(result.stderr)
        self.assertEqual(diagnostic["code"], "WORKTREE_BINDING_INVALID")
        attempt_path = self.run / "operator" / "worker-phases" / "worker-1-start" / "attempt.json"
        attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
        self.assertEqual(attempt["status"], "FAILED")
        self.assertEqual(attempt["calls"], [])

    def test_duplicate_phase_does_not_replace_evidence_or_rerun_probe(self):
        first = self._cli("start")
        self.assertEqual(first.returncode, 0, first.stderr)
        attempt_path = self.run / "operator" / "worker-phases" / "worker-1-start" / "attempt.json"
        before = attempt_path.read_bytes()
        second = self._cli("start")
        self.assertEqual(second.returncode, 2)
        self.assertEqual(json.loads(second.stderr)["code"], "PHASE_ALREADY_ATTEMPTED")
        self.assertEqual(attempt_path.read_bytes(), before)
        probe = self.run / "operator" / "probes" / "worker-1-start.json"
        self.assertTrue(probe.is_file())


if __name__ == "__main__":
    unittest.main()
