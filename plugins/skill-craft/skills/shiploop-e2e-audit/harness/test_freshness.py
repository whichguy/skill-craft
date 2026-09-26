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
    VERSIONS = {"shiploop": "0.18.1", "improve": "0.2.0-rc.2"}

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-e2e-freshness-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.selected = self.root / "selected-shiploop"
        self.selected_improve = self.root / "selected-improve"
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
        # One repository holds skills/, the released plugins/ and the catalog,
        # as skill-craft does; release.py writes all three in one commit.
        self._init(self.source)
        self._write_source_package()
        self._write_catalog()
        self.published_sha = self._commit(self.source, "release")
        shutil.copytree(self.source / "plugins" / "shiploop" / "skills" / "shiploop", self.selected)
        shutil.copytree(self.source / "plugins" / "improve" / "skills" / "improve", self.selected_improve)
        self.source_authority = freshness.Authority(str(self.source), "refs/heads/main")
        source_patch = patch.object(freshness, "SOURCE_AUTHORITY", self.source_authority)
        source_patch.start()
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

    def _write_skill(self, root: Path, name: str, version: str) -> None:
        self._write_file(
            root / "SKILL.md",
            f"---\nname: {name}\nversion: {version}\n---\n# Fixture {name}\n",
        )
        self._write_file(root / "scripts" / name, "#!/bin/sh\nexit 0\n", executable=True)
        self._write_file(root / "references" / "guide.md", "fixture guidance\n")

    def _sync_generated(self, name: str) -> None:
        generated = self.source / "plugins" / name / "skills" / name
        if generated.exists():
            shutil.rmtree(generated)
        shutil.copytree(self.source / "skills" / name, generated, copy_function=shutil.copy2)

    def _write_source_package(self, versions: dict[str, str] | None = None) -> None:
        for name, version in (versions or self.VERSIONS).items():
            self._write_skill(self.source / "skills" / name, name, version)
            self._sync_generated(name)
            self._write_file(
                self.source / "plugins" / name / ".claude-plugin" / "plugin.json",
                json.dumps({"name": name, "version": version}, indent=2) + "\n",
            )
            self._write_file(self.source / "plugins" / name / "README.md", "published wrapper\n")

    def _write_catalog(
        self, *, versions: dict[str, str] | None = None, duplicate: str | None = None,
        omit: str | None = None, malformed: bool = False, sources: dict[str, object] | None = None,
    ) -> None:
        target = self.source / ".claude-plugin" / "marketplace.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        if malformed:
            target.write_text("{not json}\n", encoding="utf-8")
            return
        plugins = []
        for name, version in (versions or self.VERSIONS).items():
            if name == omit:
                continue
            source = (sources or {}).get(name, "./plugins/" + name)
            entry = {"name": name, "version": version, "source": source}
            plugins.append(entry)
            if name == duplicate:
                plugins.append(dict(entry))
        target.write_text(json.dumps({"name": "fixture", "plugins": plugins}, indent=2) + "\n", encoding="utf-8")

    def _replace_catalog(self, **kwargs: object) -> None:
        self._write_catalog(**kwargs)
        self._commit(self.source, "catalog mutation")

    def _add_note(self, name: str) -> None:
        self._write_file(self.source / "changes" / name / "fixture.md", "---\nbump: patch\n---\nA fixture change.\n")

    def inspect(self, *, env: dict[str, str] | None = None) -> dict[str, object]:
        return freshness.inspect_freshness({
            "shiploop": package_manifest(self.selected),
            "improve": package_manifest(self.selected_improve),
        }, self.git, env or self.git_env)

    def test_ready_reads_the_same_repository_catalog_and_matches_all_three_trees(self) -> None:
        receipt = self.inspect()

        self.assertTrue(receipt["ready"], receipt)
        self.assertEqual("ready", receipt["status"])
        self.assertEqual("selected-skill-packages-match-current-publication", receipt["reason"])
        self.assertEqual({"shiploop", "improve"}, set(receipt["skills"]))
        for name, version in self.VERSIONS.items():
            skill = receipt["skills"][name]
            self.assertEqual(name, skill["name"])
            self.assertEqual("matched", skill["comparisons"]["source_to_generated"])
            self.assertEqual("matched", skill["comparisons"]["source_to_published"])
            self.assertEqual("matched", skill["comparisons"]["selected_to_published"])
            self.assertEqual(version, skill["source"]["version"])
            self.assertEqual(version, skill["published"]["version"])
            self.assertEqual(self.published_sha, skill["published"]["head"])
            self.assertEqual(self.published_sha, skill["published"]["pin"]["sha"])
            self.assertEqual("./plugins/" + name, skill["published"]["catalog"]["source_path"])
            self.assertEqual(str(self.source), skill["published"]["authority"]["url"])
        self.assertEqual(0, receipt["model_calls"])

    def test_unreleased_skill_edit_with_a_change_note_is_unpublished(self) -> None:
        # An ordinary commit between releases: skill source and a note, no plugins/.
        self._write_file(self.source / "skills" / "shiploop" / "scripts" / "shiploop", "#!/bin/sh\necho newer\n", executable=True)
        self._add_note("shiploop")
        self._commit(self.source, "new code awaiting release")

        receipt = self.inspect()

        self.assertFalse(receipt["ready"])
        self.assertEqual("unpublished-source", receipt["status"])
        self.assertEqual("source-and-generated-package-differ", receipt["reason"])
        self.assertEqual("0.18.1", receipt["skills"]["shiploop"]["source"]["version"])
        self.assertEqual("0.18.1", receipt["skills"]["shiploop"]["published"]["version"])

    def test_pending_change_note_alone_is_unpublished(self) -> None:
        self._add_note("improve")
        self._commit(self.source, "note awaiting release")

        receipt = self.inspect()

        self.assertFalse(receipt["ready"])
        self.assertEqual("unpublished-source", receipt["status"])
        self.assertEqual("improve-source-has-unreleased-changes", receipt["reason"])
        self.assertEqual("different", receipt["skills"]["improve"]["comparisons"]["source_to_published"])

    def test_unrelated_source_commit_is_still_ready_at_the_new_head(self) -> None:
        self._write_file(self.source / "README.md", "unrelated repository documentation\n")
        self._add_note("shiploop-e2e-audit")
        latest = self._commit(self.source, "unrelated source change")

        receipt = self.inspect()

        self.assertTrue(receipt["ready"], receipt)
        self.assertEqual(latest, receipt["skills"]["shiploop"]["source"]["head"])
        self.assertEqual(latest, receipt["skills"]["shiploop"]["published"]["pin"]["sha"])

    def test_new_release_leaves_the_previous_installation_stale(self) -> None:
        released = dict(self.VERSIONS, shiploop="0.18.2")
        self._write_source_package(released)
        self._write_catalog(versions=released)
        self._commit(self.source, "release: shiploop 0.18.2")

        receipt = self.inspect()

        self.assertFalse(receipt["ready"])
        self.assertEqual("installed-stale", receipt["status"])
        self.assertEqual("selected-package-version-does-not-match-published-package", receipt["reason"])
        self.assertEqual("0.18.2", receipt["skills"]["shiploop"]["published"]["version"])

    def test_catalog_version_that_disagrees_with_the_package_fails_closed(self) -> None:
        self._replace_catalog(versions=dict(self.VERSIONS, shiploop="0.18.0"))

        receipt = self.inspect()

        self.assertFalse(receipt["ready"])
        self.assertEqual("freshness-unverified", receipt["status"])
        self.assertEqual("catalog-version-does-not-match-published-package", receipt["reason"])

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

    def test_selected_improve_rc1_is_stale_against_the_rc2_source_and_catalog_pin(self) -> None:
        skill = self.selected_improve / "SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8").replace("0.2.0-rc.2", "0.2.0-rc.1"), encoding="utf-8")

        receipt = self.inspect()

        self.assertFalse(receipt["ready"])
        self.assertEqual("installed-stale", receipt["status"])
        self.assertEqual("improve-selected-package-version-does-not-match-published-package", receipt["reason"])
        improve = receipt["skills"]["improve"]
        self.assertEqual("0.2.0-rc.1", improve["selected"]["version"])
        self.assertEqual("0.2.0-rc.2", improve["source"]["version"])
        self.assertEqual("0.2.0-rc.2", improve["published"]["catalog"]["version"])
        self.assertEqual(self.published_sha, improve["published"]["pin"]["sha"])

    def test_selected_improve_obsolete_extra_file_is_stale(self) -> None:
        self._write_file(self.selected_improve / "references" / "obsolete.md", "old local guidance\n")

        receipt = self.inspect()

        self.assertFalse(receipt["ready"])
        self.assertEqual("installed-stale", receipt["status"])
        self.assertEqual("improve-selected-package-does-not-match-published-package", receipt["reason"])

    def test_selected_improve_mode_only_divergence_is_stale(self) -> None:
        script = self.selected_improve / "scripts" / "improve"
        script.chmod(script.stat().st_mode & ~(stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))

        receipt = self.inspect()

        self.assertFalse(receipt["ready"])
        self.assertEqual("installed-stale", receipt["status"])
        self.assertEqual("improve-selected-package-does-not-match-published-package", receipt["reason"])

    def test_duplicate_or_malformed_catalog_fails_closed(self) -> None:
        self._replace_catalog(duplicate="shiploop")
        duplicate = self.inspect()
        self.assertFalse(duplicate["ready"])
        self.assertEqual("freshness-unverified", duplicate["status"])
        self.assertEqual("catalog-shiploop-entry-is-missing-or-duplicate", duplicate["reason"])

        self._replace_catalog(malformed=True)
        malformed = self.inspect()
        self.assertFalse(malformed["ready"])
        self.assertEqual("freshness-unverified", malformed["status"])
        self.assertEqual("catalog-is-invalid", malformed["reason"])

    def test_missing_or_duplicate_improve_catalog_entry_fails_closed(self) -> None:
        self._replace_catalog(duplicate="improve")
        duplicate = self.inspect()
        self.assertFalse(duplicate["ready"])
        self.assertEqual("freshness-unverified", duplicate["status"])
        self.assertEqual("catalog-improve-entry-is-missing-or-duplicate", duplicate["reason"])

        self._replace_catalog(omit="improve")
        missing = self.inspect()
        self.assertFalse(missing["ready"])
        self.assertEqual("freshness-unverified", missing["status"])
        self.assertEqual("catalog-improve-entry-is-missing-or-duplicate", missing["reason"])

    def test_external_or_wrong_path_catalog_source_is_invalid(self) -> None:
        git_subdir = {
            "source": "git-subdir", "url": str(self.source),
            "path": "plugins/shiploop", "sha": self.published_sha,
        }
        for label, source in (("git-subdir", git_subdir), ("wrong-path", "./plugins/improve"),
                              ("no-dot-prefix", "plugins/shiploop")):
            with self.subTest(label):
                self._replace_catalog(sources={"shiploop": source})
                receipt = self.inspect()
                self.assertFalse(receipt["ready"])
                self.assertEqual("freshness-unverified", receipt["status"])
                self.assertEqual("catalog-shiploop-entry-is-invalid", receipt["reason"])

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
