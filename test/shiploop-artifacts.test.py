"""Behavioral tests for bounded artifact consumers."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/shiploop/scripts"))
import shiploop_artifacts as artifacts
import shiploop_store as store


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def record(self, path, value):
        store.write_record(self.root / path, value)

    def test_catalog_declares_conditional_consumers(self):
        rows = artifacts.catalog()["families"]
        self.assertTrue(all(row["reader"] and row["authority"] for row in rows))
        self.assertTrue(any("outer-work" in row["pattern"] for row in rows))

    def test_archive_content_is_observable_without_restoring_authority(self):
        self.record("knowledge-history/A1.md", {"action": "A1", "kind": "checkpoint", "source": "probe", "current": {"role": "development"}})
        self.assertEqual(artifacts.audit(self.root, "knowledge-history")["records"], ["A1.md"])
        first = artifacts.audit(self.root, "knowledge-history", "A1.md")
        self.record("knowledge-history/A1.md", {"action": "A1", "current": {"role": "test"}})
        second = artifacts.audit(self.root, "knowledge-history", "A1.md")
        self.assertNotEqual(first["sha256"], second["sha256"])
        self.assertEqual(second["content"]["current"]["role"], "test")
        self.assertFalse((self.root / "state.md").exists())

    def test_archive_rejects_escape_symlink_and_oversize(self):
        for kind, record in [("unknown", "A.md"), ("knowledge-history", "../state.md")]:
            with self.assertRaises(artifacts.ArtifactError):
                artifacts.audit(self.root, kind, record)
        (self.root / "knowledge-history").mkdir()
        (self.root / "knowledge-history/A.md").symlink_to(self.root / "state.md")
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.audit(self.root, "knowledge-history", "A.md")
        (self.root / "knowledge-history/B.md").write_text("x" * (artifacts.MAX_BYTES + 1))
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.audit(self.root, "knowledge-history", "B.md")

    def log(self, content):
        log = self.root / "logs/A1/R1/lint.stderr.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_bytes(content)
        self.record("check-attempts/A1-R1.md", {"results": {"action": "A1", "evidence_dir": str(log.parent), "checks": [{"id": "lint", "stderr_log": str(log), "log_path": str(log)}]}})

    def test_log_reader_uses_check_binding_and_returns_failure(self):
        self.log(b"expected 3 but observed 4\n")
        value = artifacts.check_log(self.root, "A1", "R1", "lint")
        self.assertIn("observed 4", value["excerpt"])
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.check_log(self.root, "A1", "R1", "missing")

    def test_sensitive_multiline_binary_and_large_logs_fail_safe(self):
        self.log(b"token:\nprivate-value\n")
        self.assertNotIn("private-value", artifacts.check_log(self.root, "A1", "R1", "lint")["excerpt"])
        self.log(b"binary\x00value")
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.check_log(self.root, "A1", "R1", "lint")

    def test_archive_withholds_multiline_secret(self):
        path = self.root / "legacy-backup" / "prompt.md"
        path.parent.mkdir()
        path.write_text("token:\nprivate-value\n")
        value = artifacts.audit(self.root, "legacy-backup", "prompt.md")
        self.assertEqual(value["content"], "[withheld sensitive archive]")

    def test_real_check_producer_roundtrip_all_streams(self):
        import shiploop_evidence as evidence

        repo = self.root / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        manifest = {"checks": [{"id": "syntax", "kind": "lint", "acceptance": [], "argv": [sys.executable, "-c", "pass"]},
            {"id": "actual-failure", "kind": "test", "acceptance": ["sample"],
            "argv": [sys.executable, "-c", "import sys; print('observed stdout'); print('observed failure', file=sys.stderr); sys.exit(1)"]}]}
        output = evidence.run_checks(repo, manifest, self.root / "logs/A1/R1", "A1", timeout=10)
        self.assertFalse(output["all_passed"])
        self.record("check-attempts/A1-R1.md", {"manifest": manifest, "results": output})
        for stream, expected in (("stdout", "observed stdout"), ("stderr", "observed failure"), ("combined", "observed failure")):
            self.assertIn(expected, artifacts.check_log(self.root, "A1", "R1", "actual-failure", stream)["excerpt"])
        self.log(b"x" * (artifacts.MAX_BYTES + 1))
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.check_log(self.root, "A1", "R1", "lint")


if __name__ == "__main__":
    unittest.main()
