"""The external adapter must preserve the native runner's own argument names."""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).with_name("native_slice.py")
spec = importlib.util.spec_from_file_location("adapter_under_test", MODULE_PATH)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

EXPECTED_HEAD = "a" * 40
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class ForwardingTests(unittest.TestCase):
    def test_native_case_does_not_abbreviate_catalog(self):
        tail = ["--case", "readiness-plan", "--seed-at", "test-strategy",
                "--stop-after", "plan", "--host", "codex", "--model", "gpt-6.1-terra",
                "--effort", "xhigh", "--plugin-dir", "/build/plugin", "--output", "/run/output"]
        args, forwarded = adapter._adapter_args(
            ["--harness-root", "/repo", "--expected-head", EXPECTED_HEAD,
             "--case-catalog", "/corpus/cases.json", "--fixture-root", "/corpus"] + tail)
        self.assertEqual(args.case_catalog, Path("/corpus/cases.json"))
        self.assertEqual(args.expected_head, EXPECTED_HEAD)
        self.assertEqual(forwarded, tail)

    def test_regrade_is_forwarded(self):
        tail = ["--regrade", "/run/slice"]
        _, forwarded = adapter._adapter_args(
            ["--harness-root", "/repo", "--expected-head", EXPECTED_HEAD,
             "--case-catalog", "/corpus/cases.json", "--fixture-root", "/corpus"] + tail)
        self.assertEqual(forwarded, tail)


class GitDiscoveryTests(unittest.TestCase):
    def test_export_does_not_inherit_ancestor_but_owned_repo_still_works(self):
        import os
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary) / "owner"
            owner.mkdir()
            subprocess.run(["git", "-C", str(owner), "init", "-q"], check=True)
            output = owner / "artifacts" / "trial"
            export = output / "export"
            export.mkdir(parents=True)
            owned = output / "work"
            owned.mkdir()
            subprocess.run(["git", "-C", str(owned), "init", "-q"], check=True)

            def top(path):
                return subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"],
                                      capture_output=True, text=True, timeout=10)
            self.assertEqual(Path(top(export).stdout.strip()).resolve(), owner.resolve())
            old = os.environ.get("GIT_CEILING_DIRECTORIES")
            with adapter.isolated_git_discovery(output):
                self.assertNotEqual(top(export).returncode, 0)
                self.assertEqual(Path(top(owned).stdout.strip()).resolve(), owned.resolve())
            self.assertEqual(os.environ.get("GIT_CEILING_DIRECTORIES"), old)

    def test_ceiling_restores_after_failure(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": "/prior-ceiling"}):
            with self.assertRaisesRegex(RuntimeError, "test failure"):
                with adapter.isolated_git_discovery(Path("/new-run")):
                    self.assertIn("/prior-ceiling", os.environ["GIT_CEILING_DIRECTORIES"])
                    raise RuntimeError("test failure")
            self.assertEqual(os.environ["GIT_CEILING_DIRECTORIES"], "/prior-ceiling")


class FrozenHarnessTests(unittest.TestCase):
    def clean_clone(self, destination: Path) -> tuple[Path, str]:
        cloned = subprocess.run(
            ["git", "clone", "--quiet", "--shared", str(REPOSITORY_ROOT), str(destination)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(cloned.returncode, 0, cloned.stderr)
        head = subprocess.run(
            ["git", "-C", str(destination), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(destination), "status", "--porcelain", "--untracked-files=all"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout
        self.assertEqual(status, "")
        return destination, head

    def test_tracked_and_staged_changes_are_rejected_before_slice_import(self):
        for staged in (False, True):
            with self.subTest(staged=staged), tempfile.TemporaryDirectory() as temporary:
                harness, head = self.clean_clone(Path(temporary) / "harness")
                source = harness / adapter.SLICE_RELATIVE
                marker = Path(temporary) / "source-imported"
                source.write_text(
                    "from pathlib import Path\n"
                    f"Path({str(marker)!r}).touch()\n",
                    encoding="utf-8",
                )
                if staged:
                    subprocess.run(
                        ["git", "-C", str(harness), "add", "test/shiploop_e2e/slice.py"],
                        check=True,
                        timeout=10,
                    )
                with self.assertRaisesRegex(SystemExit, "must be clean"):
                    adapter._load_frozen_slice(
                        harness, head, Path(__file__).with_name("cases.json"), Path(__file__).parent
                    )
                self.assertFalse(marker.exists())

    def test_untracked_import_adjacent_input_is_rejected_before_loader(self):
        with tempfile.TemporaryDirectory() as temporary:
            harness, head = self.clean_clone(Path(temporary) / "harness")
            source = harness / adapter.SLICE_RELATIVE
            adjacent = source.parent / "native_setup_pilot_probe.py"
            adjacent.write_text("IMPORT_MARKER = True\n", encoding="utf-8")
            with mock.patch.object(
                adapter.importlib.util,
                "spec_from_file_location",
                wraps=adapter.importlib.util.spec_from_file_location,
            ) as source_loader:
                with self.assertRaisesRegex(SystemExit, "must be clean"):
                    adapter._load_frozen_slice(
                        harness, head, Path(__file__).with_name("cases.json"), Path(__file__).parent
                    )
                source_loader.assert_not_called()




if __name__ == "__main__":
    unittest.main()
