#!/usr/bin/env python3
"""Focused checks for the one-shot ShipLoop evidence helpers."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import run


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
SPEC = importlib.util.spec_from_file_location("shiploop_e2e_evidence", HERE / "evidence.py")
assert SPEC and SPEC.loader
evidence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evidence)

FALLBACK_GIT = Path("/Users/dadleet/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/fallback/git")
GIT = str(FALLBACK_GIT if FALLBACK_GIT.is_file() else shutil.which("git") or "git")


def fenced(value: dict) -> str:
    return "# ShipLoop record\n\n```shiploop-state\n" + json.dumps(value, indent=2, sort_keys=True) + "\n```\n"


class EvidenceTest(unittest.TestCase):
    def git(self, repository: Path, *arguments: str) -> None:
        result = subprocess.run([GIT, "-C", str(repository), *arguments], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))

    def init_repository(self, base: Path) -> Path:
        repository = base / "repository"
        repository.mkdir()
        self.git(repository, "init", "-q")
        self.git(repository, "config", "user.email", "tests@example.invalid")
        self.git(repository, "config", "user.name", "ShipLoop evidence test")
        (repository / "app.py").write_text("VERSION = 1\n", encoding="utf-8")
        (repository / "remove.txt").write_text("remove me\n", encoding="utf-8")
        self.git(repository, "add", "app.py", "remove.txt")
        self.git(repository, "commit", "-qm", "initial")
        return repository

    def test_package_manifest_tracks_external_links_and_rejects_cycles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            package, external = base / "package", base / "external"
            package.mkdir()
            external.mkdir()
            (external / "guide.md").write_text("external guide v1\n", encoding="utf-8")
            (package / "SKILL.md").write_text("# Skill\n\n[shared guide](../external/guide.md)\n", encoding="utf-8")
            (package / "local.md").write_text("local\n", encoding="utf-8")
            (package / ".env").write_text("TOKEN=never-archive\n", encoding="utf-8")
            (package / "__pycache__").mkdir()
            (package / "__pycache__" / "ignored.pyc").write_bytes(b"ignored")
            (package / "linked").symlink_to(external, target_is_directory=True)

            first = evidence.package_manifest(package)
            paths = {row["logical_path"]: row for row in first["files"]}
            self.assertIn("SKILL.md", paths)
            self.assertIn("linked/guide.md", paths)
            self.assertEqual(paths["linked/guide.md"]["provenance"], "outside-package-symlink")
            self.assertTrue(any(row["provenance"] == "outside-package-reference" for row in first["files"]))
            self.assertTrue(paths[".env"]["sensitive"])
            self.assertEqual(first["aggregate_sha256"], hashlib.sha256(json.dumps(first["file_hashes"], ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()).hexdigest())

            (external / "guide.md").write_text("external guide v2\n", encoding="utf-8")
            self.assertNotEqual(first["aggregate_sha256"], evidence.package_manifest(package)["aggregate_sha256"])

            no_skill = base / "no-skill"
            no_skill.mkdir()
            with self.assertRaisesRegex(ValueError, "missing SKILL.md"):
                evidence.package_manifest(no_skill)

            cyclic = base / "cyclic"
            cyclic.mkdir()
            (cyclic / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
            (cyclic / "loop").symlink_to(cyclic, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "cycle"):
                evidence.package_manifest(cyclic)

    def test_repo_snapshots_include_untracked_and_describe_incremental_churn(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = self.init_repository(Path(temporary))
            before = evidence.repo_snapshot(repository, git_bin=GIT)
            (repository / "app.py").write_text("VERSION = 2\n", encoding="utf-8")
            (repository / "remove.txt").unlink()
            (repository / "new.txt").write_text("new feature\n", encoding="utf-8")
            (repository / ".env").write_text("TOKEN=never-archive\n", encoding="utf-8")
            (repository / "scratch.txt").write_text("untracked but useful\n", encoding="utf-8")
            self.git(repository, "add", "-u")
            self.git(repository, "add", "new.txt")
            self.git(repository, "commit", "-qm", "add feature")

            after = evidence.repo_snapshot(repository, git_bin=GIT)
            self.assertIn("scratch.txt", {row["path"] for row in after["files"]})
            env_row = next(row for row in after["files"] if row["path"] == ".env")
            self.assertTrue(env_row["sensitive"])
            self.assertFalse(env_row["tracked"])
            self.assertEqual(len(after["status_sha256"]), 64)
            self.assertEqual(len(after["index"]["sha256"]), 64)
            self.assertTrue(any(row.startswith("100") and "\tapp.py" in row for row in after["index"]["entries"]))

            comparison = evidence.compare_repos(before, after, repository, git_bin=GIT)
            self.assertTrue(comparison["repository_identity_matches"])
            self.assertTrue(comparison["old_head_is_ancestor"])
            self.assertIn("app.py", comparison["changed_paths"])
            self.assertIn("remove.txt", comparison["removed_paths"])
            self.assertIn("new.txt", comparison["added_paths"])
            self.assertIn("scratch.txt", comparison["added_paths"])
            self.assertIn("does not establish", comparison["diagnostic_note"])

    def test_repo_snapshot_binds_ignored_product_source_and_reports_runtime_omissions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repository = self.init_repository(base)
            (repository / ".gitignore").write_text(
                "generated-app.js\n.env\nnode_modules/\n.shiploop/\n", encoding="utf-8"
            )
            self.git(repository, "add", ".gitignore")
            self.git(repository, "commit", "-qm", "ignore local runtime files")
            generated = repository / "generated-app.js"
            generated.write_text("export const version = 1;\n", encoding="utf-8")
            (repository / ".env").write_text("TOKEN=never-copy\n", encoding="utf-8")
            (repository / "node_modules" / "library").mkdir(parents=True)
            (repository / "node_modules" / "library" / "index.js").write_text("module.exports = {};\n", encoding="utf-8")
            (repository / ".shiploop").mkdir()
            (repository / ".shiploop" / "state.md").write_text("runtime state\n", encoding="utf-8")
            external = base / "external-product.js"
            external.write_text("outside tree\n", encoding="utf-8")
            (repository / "linked.js").symlink_to(external)

            before = evidence.repo_snapshot(repository, git_bin=GIT)
            before_digest = run.candidate_digest(before)
            rows = {row["path"]: row for row in before["files"]}
            self.assertEqual(rows["generated-app.js"]["sha256"], hashlib.sha256(generated.read_bytes()).hexdigest())
            self.assertFalse(rows["generated-app.js"]["tracked"])
            self.assertFalse(rows["generated-app.js"]["untracked"])
            self.assertTrue(rows["generated-app.js"]["ignored"])
            self.assertEqual(rows["linked.js"]["kind"], "symlink")
            self.assertNotIn("node_modules/library/index.js", rows)
            self.assertNotIn(".shiploop/state.md", rows)
            skipped = {(row["path"], row["reason"]) for row in before["skipped"]}
            self.assertIn((".git", "git-metadata"), skipped)
            self.assertIn(("node_modules", "runtime-cache-directory"), skipped)
            self.assertIn((".shiploop", "runtime-cache-directory"), skipped)

            frozen = run.freeze_product(repository.resolve(), before, base / "product-copy")
            self.assertIn("generated-app.js", frozen["copied"])
            self.assertEqual((base / "product-copy" / "generated-app.js").read_bytes(), generated.read_bytes())
            self.assertIn({"path": ".env", "reason": "sensitive-content-not-copied"}, frozen["omitted"])
            self.assertIn({"path": "linked.js", "reason": "external-symlink-not-copied"}, frozen["omitted"])
            self.assertFalse((base / "product-copy" / "node_modules").exists())
            self.assertFalse((base / "product-copy" / ".shiploop").exists())

            generated.write_text("export const version = 2;\n", encoding="utf-8")
            after = evidence.repo_snapshot(repository, git_bin=GIT)
            self.assertNotEqual(before_digest, run.candidate_digest(after))
            self.assertEqual(evidence.compare_repos(before, after, repository, git_bin=GIT)["changed_paths"], ["generated-app.js"])

    def test_cache_exclusions_preserve_tracked_inputs_regular_names_and_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repository = self.init_repository(base)
            vendor = repository / "node_modules" / "vendored.js"
            vendor.parent.mkdir()
            vendor.write_text("export const version = 1;\n")
            self.git(repository, "add", str(vendor))
            self.git(repository, "commit", "-qm", "tracked dependency is a product input")
            (repository / ".cache").write_text("ordinary source file\n")
            external = base / "runtime"
            external.mkdir()
            (external / "private").write_text("must not traverse\n")
            (repository / ".until-loop").symlink_to(external, target_is_directory=True)
            index_before = (repository / ".git" / "index").read_bytes()
            first = evidence.repo_snapshot(repository, git_bin=GIT)
            rows = {row["path"]: row for row in first["files"]}
            self.assertTrue(rows["node_modules/vendored.js"]["tracked"])
            self.assertEqual(rows[".cache"]["kind"], "file")
            self.assertEqual(rows[".until-loop"]["kind"], "symlink")
            self.assertNotIn(".until-loop/private", rows)
            vendor.write_text("export const version = 2;\n")
            second = evidence.repo_snapshot(repository, git_bin=GIT)
            self.assertNotEqual(run.candidate_digest(first), run.candidate_digest(second))
            self.assertEqual((repository / ".git" / "index").read_bytes(), index_before)

    def test_runtime_cache_creation_is_reported_without_changing_candidate_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = self.init_repository(Path(temporary))
            (repository / ".gitignore").write_text("node_modules/\n")
            first = evidence.repo_snapshot(repository, git_bin=GIT)
            for name in ("node_modules", ".cache"):
                (repository / name).mkdir()
                (repository / name / "runtime-data").write_text("cache\n")
            second = evidence.repo_snapshot(repository, git_bin=GIT)
            self.assertNotEqual(first["skipped"], second["skipped"])
            self.assertNotEqual(first["status"], second["status"])
            self.assertEqual(first["files"], second["files"])
            self.assertEqual(run.candidate_digest(first), run.candidate_digest(second))
            (repository / "app.py").write_text("VERSION = 2\n")
            self.assertNotEqual(run.candidate_digest(second), run.candidate_digest(evidence.repo_snapshot(repository, git_bin=GIT)))

    def test_unborn_git_repository_has_a_hashable_baseline_without_ancestry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary) / "unborn"
            repository.mkdir()
            self.git(repository, "init", "-q")
            self.git(repository, "config", "user.email", "tests@example.invalid")
            self.git(repository, "config", "user.name", "ShipLoop evidence test")
            before = evidence.repo_snapshot(repository, git_bin=GIT)
            self.assertIsNone(before["head"])
            self.assertTrue(before["unborn"])
            (repository / "app.py").write_text("print('ready')\n", encoding="utf-8")
            self.git(repository, "add", "app.py")
            self.git(repository, "commit", "-qm", "initial")
            after = evidence.repo_snapshot(repository, git_bin=GIT)
            comparison = evidence.compare_repos(before, after, repository, git_bin=GIT)
            self.assertIsNone(comparison["old_head_is_ancestor"])
            self.assertEqual(comparison["ancestry"], "not-applicable-no-baseline-head")
            self.assertEqual(comparison["added_paths"], ["app.py"])

    def test_repo_snapshot_fails_closed_when_git_cannot_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = self.init_repository(Path(temporary))
            with self.assertRaisesRegex(ValueError, "cannot execute git"):
                evidence.repo_snapshot(repository, git_bin=str(repository / "missing-git"))

    def test_capture_and_inspect_archives_only_owned_run_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            campaign, output, outside = base / "campaign", base / "archive", base / "outside"
            run = campaign / "case-a" / ".shiploop"
            (run / "results").mkdir(parents=True)
            (run / "inbox").mkdir()
            outside.mkdir()
            state = {
                "navigator_protocol_version": 4,
                "run_id": "nav-test",
                "repo": "/example/repository",
                "revision": 4,
                "status": "active",
                "action": {"id": "nav-current", "stage": "implement"},
                "history": [{"action": "nav-old", "stage": "plan", "outcome": "done", "workitem": None}],
            }
            (run / "state.md").write_text(fenced(state), encoding="utf-8")
            (run / "workspace.md").write_text(fenced({"schema": "shiploop-workspace", "status": "prepared"}), encoding="utf-8")
            (run / "return-receipt.md").write_text(fenced({"schema": "shiploop-workspace-return-receipt", "outcome": "returned"}), encoding="utf-8")
            (run / "results" / "nav-current.md").write_text("# Result\n", encoding="utf-8")
            (run / "inbox" / "reply.md").write_text("# Reply\n", encoding="utf-8")
            (run / "report.html").write_text("<h1>report</h1>\n", encoding="utf-8")
            (run / "metadata.json").write_text('{"run":"metadata"}\n', encoding="utf-8")
            (outside / "state.md").write_text(fenced({"status": "outside"}), encoding="utf-8")
            (campaign / "escape").symlink_to(outside, target_is_directory=True)
            leaked_state = campaign / "leaked-state" / ".shiploop"
            leaked_result = campaign / "leaked-result" / ".shiploop" / "results"
            leaked_report = campaign / "leaked-report" / ".shiploop"
            leaked_state.mkdir(parents=True)
            leaked_result.mkdir(parents=True)
            leaked_report.mkdir(parents=True)
            leaked_state_secret = "state-bearer-secret"
            leaked_result_secret = "result-xai-secret"
            leaked_report_secret = "report-api-secret"
            (leaked_state / "state.md").write_text(fenced({"status": "active", "note": f"Bearer {leaked_state_secret}"}), encoding="utf-8")
            (leaked_result / "leaked.md").write_text(f"xai-{leaked_result_secret}\n", encoding="utf-8")
            (leaked_report / "report.html").write_text(f'<meta api_key="{leaked_report_secret}">\n', encoding="utf-8")

            capture = evidence.capture_run_artifacts([campaign, base / "not-created-yet"], output)
            state_row = next(row for row in capture["artifacts"] if row["kind"] == "state")
            self.assertTrue(Path(state_row["source_path"]).is_absolute())
            self.assertEqual(state_row["sha256"], hashlib.sha256((run / "state.md").read_bytes()).hexdigest())
            self.assertTrue((output / state_row["archive_path"]).is_file())
            self.assertTrue(any(row["kind"] == "shiploop-metadata" for row in capture["artifacts"]))
            self.assertTrue(any(row["reason"] == "symlink-outside-owned-root" for row in capture["skipped"]))
            self.assertTrue(any(row["reason"] == "missing-root" for row in capture["skipped"]))
            leaked = [row for row in capture["skipped"] if row["reason"] == "credential-shaped-artifact"]
            self.assertEqual(len(leaked), 3)
            self.assertTrue(all(len(row["sha256"]) == 64 for row in leaked))
            archived_text = "\n".join(path.read_text(encoding="utf-8") for path in output.rglob("*") if path.is_file())
            for secret in (leaked_state_secret, leaked_result_secret, leaked_report_secret):
                self.assertNotIn(secret, archived_text)

            inspected = evidence.inspect_run_artifacts(capture)
            self.assertEqual(inspected["states"][0]["state"], state)
            self.assertEqual(inspected["states"][0]["status"], "active")
            self.assertEqual(inspected["states"][0]["run_identity"]["run_id"], "nav-test")
            self.assertEqual(inspected["states"][0]["action_transitions"][0]["stage"], "plan")
            self.assertTrue(inspected["guarded_receipt_presence"]["present"])
            self.assertEqual(inspected["semantic_evidence"], "not-assessed")


if __name__ == "__main__":
    unittest.main()
