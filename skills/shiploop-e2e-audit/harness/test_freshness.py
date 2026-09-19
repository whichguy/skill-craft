"""Hermetic Git-fixture coverage for the evaluator freshness preflight."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from evidence import package_manifest  # noqa: E402
import freshness  # noqa: E402


class FreshnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-e2e-freshness-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.catalog = self.root / "catalog"
        self.selected = self.root / "selected"
        self.git = shutil.which("git")
        if self.git is None:
            self.skipTest("git is unavailable")
        self.git_env = dict(os.environ)
        for key in tuple(self.git_env):
            if key.startswith("GIT_"):
                self.git_env.pop(key, None)
        self.git_env.update({
            "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.test",
            "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.test",
        })
        self._init(self.source)
        self._write_source_package()
        self.published_sha = self._commit(self.source, "published skill")
        self._call(self.source, "tag", "v0.18.1")
        self._init(self.catalog)
        self._write_catalog(self.published_sha, ref="v0.18.1")
        self._commit(self.catalog, "published catalog")
        shutil.copytree(self.source / "plugins" / "shiploop" / "skills" / "shiploop", self.selected)
        self.source_authority = freshness.Authority(str(self.source), "refs/heads/main")
        self.catalog_authority = freshness.Authority(str(self.catalog), "refs/heads/main")
        source_patch = patch.object(freshness, "SOURCE_AUTHORITY", self.source_authority)
        catalog_patch = patch.object(freshness, "CATALOG_AUTHORITY", self.catalog_authority)
        source_patch.start()
        catalog_patch.start()
        self.addCleanup(catalog_patch.stop)
        self.addCleanup(source_patch.stop)

    def _call(self, repo: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [self.git, *arguments], cwd=repo, env=self.git_env,
            check=True, capture_output=True, text=True,
        )

    def _init(self, repo: Path) -> None:
        subprocess.run([self.git, "init", "-q", "-b", "main", str(repo)], env=self.git_env, check=True)

    def _commit(self, repo: Path, message: str) -> str:
        self._call(repo, "add", "-A")
        self._call(repo, "commit", "-qm", message)
        return self._call(repo, "rev-parse", "HEAD").stdout.strip()

    @staticmethod
    def _write_file(path: Path, content: str, *, executable: bool = False) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if executable:
            path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def _write_skill(self, root: Path) -> None:
        self._write_file(
            root / "SKILL.md",
            "---\nname: shiploop\nversion: 0.18.1\n---\n# Fixture ShipLoop\n",
        )
        self._write_file(root / "scripts" / "shiploop", "#!/bin/sh\nexit 0\n", executable=True)
        self._write_file(root / "references" / "guide.md", "fixture guidance\n")

    def _sync_generated(self) -> None:
        generated = self.source / "plugins" / "shiploop" / "skills" / "shiploop"
        if generated.exists():
            shutil.rmtree(generated)
        shutil.copytree(self.source / "skills" / "shiploop", generated, copy_function=shutil.copy2)

    def _write_source_package(self) -> None:
        self._write_skill(self.source / "skills" / "shiploop")
        self._sync_generated()
        self._write_file(
            self.source / "plugins" / "shiploop" / ".claude-plugin" / "plugin.json",
            json.dumps({"name": "shiploop", "version": "0.18.1"}, indent=2) + "\n",
        )
        self._write_file(self.source / "plugins" / "shiploop" / "README.md", "published wrapper\n")

    def _write_catalog(self, pin: str, *, ref: str | None = "main", duplicate: bool = False, malformed: bool = False) -> None:
        target = self.catalog / ".claude-plugin" / "marketplace.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        if malformed:
            target.write_text("{not json}\n", encoding="utf-8")
            return
        source: dict[str, str] = {
            "source": "git-subdir",
            "url": str(self.source),
            "path": "plugins/shiploop",
            "sha": pin,
        }
        if ref is not None:
            source["ref"] = ref
        entry = {"name": "shiploop", "version": "0.18.1", "source": source}
        plugins = [entry, dict(entry)] if duplicate else [entry]
        target.write_text(json.dumps({"name": "fixture", "plugins": plugins}, indent=2) + "\n", encoding="utf-8")

    def _replace_catalog(self, **kwargs: object) -> None:
        self._write_catalog(self.published_sha, **kwargs)
        self._commit(self.catalog, "catalog mutation")

    def inspect(self, *, env: dict[str, str] | None = None) -> dict[str, object]:
        return freshness.inspect_freshness(package_manifest(self.selected), self.git, env or self.git_env)

    def test_ready_accepts_a_tagged_catalog_ref_and_matches_all_three_trees(self) -> None:
        receipt = self.inspect()

        self.assertTrue(receipt["ready"], receipt)
        self.assertEqual("ready", receipt["status"])
        self.assertEqual("selected-package-matches-current-publication", receipt["reason"])
        self.assertEqual("matched", receipt["comparisons"]["source_to_generated"])
        self.assertEqual("matched", receipt["comparisons"]["source_to_published"])
        self.assertEqual("matched", receipt["comparisons"]["selected_to_published"])
        self.assertEqual("0.18.1", receipt["source"]["version"])
        self.assertEqual("0.18.1", receipt["published"]["version"])
        self.assertEqual(self.published_sha, receipt["published"]["pin"]["sha"])
        self.assertEqual(0, receipt["model_calls"])

    def test_same_version_source_code_change_is_unpublished(self) -> None:
        self._write_file(self.source / "skills" / "shiploop" / "scripts" / "shiploop", "#!/bin/sh\necho newer\n", executable=True)
        self._sync_generated()
        self._commit(self.source, "new code without release")

        receipt = self.inspect()

        self.assertFalse(receipt["ready"])
        self.assertEqual("unpublished-source", receipt["status"])
        self.assertEqual("source-plugin-is-not-published", receipt["reason"])
        self.assertEqual("0.18.1", receipt["source"]["version"])
        self.assertEqual("0.18.1", receipt["published"]["version"])

    def test_unrelated_source_commit_does_not_require_a_repin(self) -> None:
        self._write_file(self.source / "README.md", "unrelated repository documentation\n")
        latest = self._commit(self.source, "unrelated source change")

        receipt = self.inspect()

        self.assertTrue(receipt["ready"], receipt)
        self.assertEqual(latest, receipt["source"]["head"])
        self.assertEqual(self.published_sha, receipt["published"]["pin"]["sha"])

    def test_wrapper_metadata_drift_is_unpublished(self) -> None:
        self._write_file(self.source / "plugins" / "shiploop" / ".claude-plugin" / "plugin.json", json.dumps({
            "name": "shiploop", "version": "0.18.1", "description": "new wrapper metadata",
        }, indent=2) + "\n")
        self._commit(self.source, "metadata changed without release")

        receipt = self.inspect()

        self.assertFalse(receipt["ready"])
        self.assertEqual("unpublished-source", receipt["status"])
        self.assertEqual("source-plugin-is-not-published", receipt["reason"])

    def test_source_and_generated_mismatch_is_unpublished(self) -> None:
        self._write_file(self.source / "skills" / "shiploop" / "references" / "guide.md", "canonical changed only\n")
        self._commit(self.source, "source generated mismatch")

        receipt = self.inspect()

        self.assertFalse(receipt["ready"])
        self.assertEqual("unpublished-source", receipt["status"])
        self.assertEqual("source-and-generated-package-differ", receipt["reason"])

    def test_installed_selection_with_same_version_but_new_bytes_is_stale(self) -> None:
        self._write_file(self.selected / "scripts" / "shiploop", "#!/bin/sh\necho stale\n", executable=True)

        receipt = self.inspect()

        self.assertFalse(receipt["ready"])
        self.assertEqual("installed-stale", receipt["status"])
        self.assertEqual("selected-package-does-not-match-published-package", receipt["reason"])

    def test_installed_mode_only_divergence_is_stale(self) -> None:
        script = self.selected / "scripts" / "shiploop"
        script.chmod(script.stat().st_mode & ~(stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))

        receipt = self.inspect()

        self.assertFalse(receipt["ready"])
        self.assertEqual("installed-stale", receipt["status"])
        self.assertEqual("selected-package-does-not-match-published-package", receipt["reason"])

    def test_duplicate_or_malformed_catalog_fails_closed(self) -> None:
        self._replace_catalog(duplicate=True)
        duplicate = self.inspect()
        self.assertFalse(duplicate["ready"])
        self.assertEqual("freshness-unverified", duplicate["status"])
        self.assertEqual("catalog-shiploop-entry-is-missing-or-duplicate", duplicate["reason"])

        self._replace_catalog(malformed=True)
        malformed = self.inspect()
        self.assertFalse(malformed["ready"])
        self.assertEqual("freshness-unverified", malformed["status"])
        self.assertEqual("catalog-is-invalid", malformed["reason"])

    def test_remote_failure_and_ambient_git_redirection_fail_closed_or_are_neutralized(self) -> None:
        redirected = dict(self.git_env)
        redirected.update({
            "GIT_DIR": str(self.root / "not-a-repository"),
            "GIT_WORK_TREE": str(self.root / "not-a-worktree"),
            "GIT_INDEX_FILE": str(self.root / "not-an-index"),
            "GIT_OBJECT_DIRECTORY": str(self.root / "not-an-object-store"),
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(self.root / "not-alternates"),
        })
        self.assertTrue(self.inspect(env=redirected)["ready"])

        missing = freshness.Authority(str(self.root / "missing-source"), "refs/heads/main")
        with patch.object(freshness, "SOURCE_AUTHORITY", missing):
            failed = self.inspect()
        self.assertFalse(failed["ready"])
        self.assertEqual("freshness-unverified", failed["status"])
        self.assertEqual("remote-head-query-failed", failed["reason"])


if __name__ == "__main__":
    unittest.main()
