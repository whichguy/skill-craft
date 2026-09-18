"""Regression coverage for portable E2E audit harness binding."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


PACKAGE = Path(__file__).resolve().parents[1]
RESOLVER = PACKAGE / "scripts" / "resolve_harness.py"
SENTINELS = ("run.py", "check_suite.py", "README.md", "scenarios.json", "suites.json")


class HarnessBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop audit package ")
        self.base = Path(self.temp.name).resolve()
        self.git_env = dict(os.environ)
        for key in list(self.git_env):
            if key.startswith("GIT_"):
                self.git_env.pop(key, None)
        self.git_env.update({
            "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.test",
            "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.test",
        })

    def tearDown(self) -> None:
        self.temp.cleanup()

    def add_harness(self, harness: Path) -> None:
        harness.mkdir(parents=True)
        for name in SENTINELS:
            (harness / name).write_text("{}\n" if name.endswith(".json") else "fixture\n", encoding="utf-8")

    def package(self, name: str, *, harness: bool = True) -> Path:
        package = self.base / name / "shiploop-e2e-audit"
        script = package / "scripts" / "resolve_harness.py"
        script.parent.mkdir(parents=True)
        shutil.copy2(RESOLVER, script)
        (package / "SKILL.md").write_text("---\nname: shiploop-e2e-audit\n---\n", encoding="utf-8")
        if harness:
            self.add_harness(package / "harness")
        return package

    def checkout(self, name: str, *, legacy: bool = False) -> Path:
        root = self.base / name
        package = root / "skills" / "shiploop-e2e-audit"
        script = package / "scripts" / "resolve_harness.py"
        script.parent.mkdir(parents=True)
        shutil.copy2(RESOLVER, script)
        (package / "SKILL.md").write_text("---\nname: shiploop-e2e-audit\n---\n", encoding="utf-8")
        self.add_harness(
            root / "test" / "experiments" / "shiploop_e2e"
            if legacy else package / "harness"
        )
        subprocess.run(["git", "init", "-q", str(root)], check=True, env=self.git_env)
        subprocess.run(["git", "-C", str(root), "add", "."], check=True, env=self.git_env)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "fixture"], check=True, env=self.git_env)
        return root.resolve()

    def invoke(self, script: Path, cwd: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(script), *args], cwd=str(cwd),
            check=False, capture_output=True, text=True, env=env,
        )

    def record(self, result: subprocess.CompletedProcess[str]) -> dict[str, object]:
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_copied_package_runs_from_empty_cwd_without_a_source_clone(self) -> None:
        package = self.package("copied package with spaces")
        empty = self.base / "empty working folder"
        empty.mkdir()

        record = self.record(self.invoke(package / "scripts" / "resolve_harness.py", empty))

        self.assertEqual(record["binding_source"], "package")
        self.assertEqual(record["harness"], str((package / "harness").resolve()))
        self.assertEqual(record["package_root"], str(package.resolve()))
        self.assertEqual(record["checkout"], None)
        self.assertEqual(record["head"], None)
        self.assertEqual(record["dirty"], None)
        self.assertEqual(record["path_base"], str(empty.resolve()))
        self.assertEqual(record["selected_skill_file"], str(package / "SKILL.md"))
        self.assertEqual(record["resolved_skill_file"], str((package / "SKILL.md").resolve()))
        self.assertEqual(len(str(record["harness_sha256"])), 64)

    def test_packaged_harness_runs_when_git_is_unavailable(self) -> None:
        package = self.package("copied package")
        empty = self.base / "empty folder"
        empty.mkdir()
        environment = dict(os.environ)
        environment["PATH"] = ""

        record = self.record(self.invoke(
            package / "scripts" / "resolve_harness.py", empty, env=environment,
        ))

        self.assertEqual(record["binding_source"], "package")
        self.assertEqual(record["git"], None)
        self.assertEqual(record["checkout"], None)

    def test_symlinked_package_preserves_selected_card_and_binds_its_harness(self) -> None:
        source = self.package("source package")
        install = self.base / "installed skill" / "shiploop-e2e-audit"
        install.parent.mkdir()
        install.symlink_to(source, target_is_directory=True)
        empty = self.base / "empty folder"
        empty.mkdir()

        record = self.record(self.invoke(install / "scripts" / "resolve_harness.py", empty))

        self.assertEqual(record["binding_source"], "package")
        self.assertEqual(record["package_root"], str(source.resolve()))
        self.assertEqual(record["harness"], str((source / "harness").resolve()))
        self.assertEqual(record["selected_skill_file"], str(install / "SKILL.md"))
        self.assertEqual(record["resolved_skill_file"], str((source / "SKILL.md").resolve()))

    def test_explicit_checkout_wins_over_the_selected_package(self) -> None:
        package = self.package("selected package")
        explicit = self.checkout("explicit checkout")
        unrelated = self.checkout("unrelated checkout")

        record = self.record(self.invoke(
            package / "scripts" / "resolve_harness.py", unrelated,
            "--checkout", "../explicit checkout",
        ))

        self.assertEqual(record["binding_source"], "explicit")
        self.assertEqual(record["checkout"], str(explicit))
        self.assertEqual(record["harness"], str(explicit / "skills" / "shiploop-e2e-audit" / "harness"))
        self.assertEqual(record["package_root"], str(package.resolve()))
        self.assertEqual(record["path_base"], str(explicit))

    def test_invalid_explicit_checkout_never_falls_back_to_the_package(self) -> None:
        package = self.package("selected package")
        empty = self.base / "empty folder"
        empty.mkdir()
        missing = self.base / "missing checkout"

        result = self.invoke(package / "scripts" / "resolve_harness.py", empty, "--checkout", str(missing))

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("explicit checkout is invalid", result.stderr)
        self.assertIn(str(missing), result.stderr)

    def test_unrelated_cwd_source_never_overrides_selected_package(self) -> None:
        package = self.package("selected package")
        unrelated = self.checkout("unrelated source")

        record = self.record(self.invoke(package / "scripts" / "resolve_harness.py", unrelated))

        self.assertEqual(record["binding_source"], "package")
        self.assertEqual(record["package_root"], str(package.resolve()))
        self.assertEqual(record["harness"], str((package / "harness").resolve()))
        self.assertEqual(record["checkout"], None)

    def test_digest_changes_for_stable_files_but_ignores_bytecode_cache(self) -> None:
        package = self.package("package")
        empty = self.base / "empty folder"
        empty.mkdir()
        script = package / "scripts" / "resolve_harness.py"

        first = self.record(self.invoke(script, empty))["harness_sha256"]
        (package / "harness" / "run.py").write_text("changed\n", encoding="utf-8")
        changed = self.record(self.invoke(script, empty))["harness_sha256"]
        cache = package / "harness" / "__pycache__"
        cache.mkdir()
        (cache / "ignored.pyc").write_bytes(b"ignored")
        cached = self.record(self.invoke(script, empty))["harness_sha256"]
        outside = self.base / "outside directory"
        outside.mkdir()
        (package / "harness" / "outside").symlink_to(outside, target_is_directory=True)
        rejected = self.invoke(script, empty)

        self.assertNotEqual(first, changed)
        self.assertEqual(changed, cached)
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("harness contains an unsupported file: outside", rejected.stderr)

    def test_source_metadata_requires_exact_canonical_source_package(self) -> None:
        source = self.checkout("source checkout")
        source_package = source / "skills" / "shiploop-e2e-audit"
        empty = self.base / "empty folder"
        empty.mkdir()

        source_record = self.record(self.invoke(source_package / "scripts" / "resolve_harness.py", empty))
        copied = self.base / "copied tree" / "shiploop-e2e-audit"
        copied.parent.mkdir()
        shutil.copytree(source_package, copied)
        copied_record = self.record(self.invoke(copied / "scripts" / "resolve_harness.py", empty))

        self.assertEqual(source_record["checkout"], str(source))
        self.assertIsInstance(source_record["head"], str)
        self.assertFalse(source_record["dirty"])
        self.assertEqual(copied_record["checkout"], None)
        self.assertEqual(copied_record["head"], None)
        self.assertEqual(copied_record["dirty"], None)

    def test_missing_runtime_sentinel_fails_clearly(self) -> None:
        package = self.package("broken package")
        (package / "harness" / "suites.json").unlink()
        empty = self.base / "empty folder"
        empty.mkdir()

        result = self.invoke(package / "scripts" / "resolve_harness.py", empty)

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("harness is missing required files", result.stderr)
        self.assertIn("suites.json", result.stderr)

    def test_explicit_checkout_supports_the_legacy_harness_location(self) -> None:
        package = self.package("selected package", harness=False)
        legacy = self.checkout("legacy checkout", legacy=True)
        empty = self.base / "empty folder"
        empty.mkdir()

        record = self.record(self.invoke(
            package / "scripts" / "resolve_harness.py", empty, "--checkout", str(legacy),
        ))

        self.assertEqual(record["binding_source"], "explicit")
        self.assertEqual(record["harness"], str(legacy / "test" / "experiments" / "shiploop_e2e"))


if __name__ == "__main__":
    unittest.main()
