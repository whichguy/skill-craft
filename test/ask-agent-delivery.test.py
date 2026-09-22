#!/usr/bin/env python3
"""Real-Git delivery-mode tests for the Ask Agent workspace helper."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from typing import Any, Iterable


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "skills/ask-agent/scripts/ask_agent_workspace.py"


class AskAgentDeliveryTests(unittest.TestCase):
    """Exercise delivery proof and real integration against disposable repositories."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="ask-agent-delivery-test-")
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.store = self.root / "workspace-store"
        self.invoke_from = self.root / "unrelated-invocation"
        self.invoke_from.mkdir()
        self._init_source()
        self._acceptance_count = 0

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _git(
        self,
        directory: Path,
        *args: str,
        input_text: str | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["git", *args],
            cwd=directory,
            input=input_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if check and result.returncode:
            self.fail(
                "Git command failed:\n"
                f"  cwd: {directory}\n"
                f"  argv: git {' '.join(args)}\n"
                f"  stdout: {result.stdout}\n"
                f"  stderr: {result.stderr}"
            )
        return result

    def _git_bytes(
        self,
        directory: Path,
        *args: str,
        check: bool = True,
    ) -> subprocess.CompletedProcess[bytes]:
        result = subprocess.run(
            ["git", *args],
            cwd=directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if check and result.returncode:
            self.fail(
                "Git command failed:\n"
                f"  cwd: {directory}\n"
                f"  argv: git {' '.join(args)}\n"
                f"  stdout: {result.stdout.decode(errors='replace')}\n"
                f"  stderr: {result.stderr.decode(errors='replace')}"
            )
        return result

    def _init_source(self) -> None:
        self.source.mkdir()
        self._git(self.source, "init", "-q", "--initial-branch=main")
        self._git(self.source, "config", "user.email", "ask-agent-delivery@example.invalid")
        self._git(self.source, "config", "user.name", "Ask Agent Delivery Test")
        (self.source / "app.txt").write_text("base application\n", encoding="utf-8")
        (self.source / "inherited.txt").write_text("base inherited input\n", encoding="utf-8")
        (self.source / "stable.txt").write_text("stable input\n", encoding="utf-8")
        self._git(self.source, "add", "app.txt", "inherited.txt", "stable.txt")
        self._git(self.source, "commit", "-q", "-m", "initial")

    def _helper(self, *args: str) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONNOUSERSITE"] = "1"
        result = subprocess.run(
            [sys.executable, "-B", str(HELPER), *args],
            cwd=self.invoke_from,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            self.fail(
                "workspace helper did not emit exactly one JSON result:\n"
                f"  argv: {' '.join(args)}\n"
                f"  returncode: {result.returncode}\n"
                f"  stdout: {result.stdout}\n"
                f"  stderr: {result.stderr}\n"
                f"  JSON error: {error}"
            )
        self.assertIsInstance(payload, dict)
        return result, payload

    def _success(self, *args: str) -> dict[str, Any]:
        result, payload = self._helper(*args)
        self.assertEqual(result.returncode, 0, f"helper failed: {payload}\nstderr: {result.stderr}")
        self.assertNotEqual(payload.get("status"), "error", payload)
        return payload

    def _error(self, *args: str) -> dict[str, Any]:
        result, payload = self._helper(*args)
        self.assertNotEqual(result.returncode, 0, payload)
        self.assertEqual(payload.get("status"), "error", payload)
        self.assertIsInstance(payload.get("error"), str, payload)
        return payload

    def _prepare(self, label: str) -> dict[str, Any]:
        prepared = self._success(
            "prepare",
            "--source",
            str(self.source),
            "--store",
            str(self.store),
            "--label",
            label,
            "--writers-quiescent",
        )
        self.assertEqual(prepared.get("status"), "prepared", prepared)
        self.assertTrue(Path(prepared["receipt"]).is_file(), prepared)
        self.assertTrue(Path(prepared["worktree"]).is_dir(), prepared)
        return prepared

    def _inspect(
        self,
        prepared: dict[str, Any],
        *,
        mode: str | None = None,
        artifacts: Iterable[str] = (),
        discard: Iterable[str] = (),
        commit_base: str | None = None,
        commits: Iterable[str] = (),
        expect_success: bool = True,
    ) -> dict[str, Any]:
        args = ["inspect", "--receipt", prepared["receipt"], "--phase", "returned"]
        for path in artifacts:
            args.extend(["--artifact", path])
        for path in discard:
            args.extend(["--discard", path])
        if mode is not None:
            args.extend(["--delivery-mode", mode])
        if commit_base is not None:
            args.extend(["--commit-base", commit_base])
        for commit in commits:
            args.extend(["--commit", commit])
        return self._success(*args) if expect_success else self._error(*args)

    def _commit(self, worker: Path, paths: Iterable[str], message: str) -> str:
        selected = list(paths)
        self.assertTrue(selected)
        # `-A` is constrained to the named worker contribution paths so staged
        # deletions work without broad staging of inherited files.
        self._git(worker, "add", "-A", "--", *selected)
        self._git(worker, "commit", "-q", "-m", message)
        return self._git(worker, "rev-parse", "HEAD").stdout.strip()

    def _source_snapshot(self) -> dict[str, bytes | str]:
        index = Path(self._git(self.source, "rev-parse", "--git-path", "index").stdout.strip())
        if not index.is_absolute():
            index = self.source / index
        return {
            "head": self._git(self.source, "rev-parse", "HEAD").stdout.strip(),
            "raw_index": index.read_bytes(),
            "cached": self._git_bytes(self.source, "diff", "--cached", "--binary").stdout,
            "working": self._git_bytes(self.source, "diff", "--binary").stdout,
            "status": self._git_bytes(self.source, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout,
        }

    def _make_dirty_source(self) -> None:
        (self.source / "inherited.txt").write_text("caller staged\n", encoding="utf-8")
        self._git(self.source, "add", "inherited.txt")
        (self.source / "inherited.txt").write_text("caller staged\ncaller unstaged\n", encoding="utf-8")
        (self.source / "caller-note.txt").write_text("caller untracked input\n", encoding="utf-8")

    def _acceptance(self, fingerprint: str, *, decision: str, artifacts: list[dict[str, str]]) -> Path:
        self._acceptance_count += 1
        path = self.root / f"acceptance-{self._acceptance_count}.json"
        path.write_text(
            json.dumps(
                {
                    "schema": "ask-agent.acceptance.v1",
                    "inspection_fingerprint": fingerprint,
                    "decision": decision,
                    "workers_stopped": True,
                    "completion_reference": "native worker return collected by test",
                    "acceptance_reference": "parent integration or report consumption verified by test",
                    "artifacts": artifacts,
                    "discard": [],
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_patch_delivery_applies_only_worker_delta_to_dirty_parent(self) -> None:
        self._make_dirty_source()
        before = self._source_snapshot()
        prepared = self._prepare("dirty patch")
        worker = Path(prepared["worktree"])
        (worker / "app.txt").write_text("base application\nworker patch contribution\n", encoding="utf-8")
        report = worker / "reports" / "handoff.md"
        report.parent.mkdir()
        report.write_text("worker report\n", encoding="utf-8")

        inspected = self._inspect(prepared, mode="patch", artifacts=["reports/handoff.md"])

        self.assertEqual(inspected["contribution_paths"], ["app.txt"])
        self.assertEqual(inspected["delivery"]["mode"], "patch")
        patch = Path(inspected["delivery"]["contribution_patch"])
        self.assertTrue(patch.is_file())
        self.assertIn(b"app.txt", patch.read_bytes())
        self.assertNotIn(b"inherited.txt", patch.read_bytes())
        evidence = json.loads(Path(inspected["delivery_evidence"]).read_text(encoding="utf-8"))
        self.assertEqual(evidence["mode"], "patch")
        self.assertEqual(evidence["contribution_paths"], ["app.txt"])

        self._git(self.source, "apply", "--check", "--binary", str(patch))
        self._git(self.source, "apply", "--binary", str(patch))

        self.assertEqual(
            (self.source / "app.txt").read_text(encoding="utf-8"),
            "base application\nworker patch contribution\n",
        )
        self.assertEqual(
            (self.source / "inherited.txt").read_text(encoding="utf-8"),
            "caller staged\ncaller unstaged\n",
        )
        self.assertEqual((self.source / "caller-note.txt").read_text(encoding="utf-8"), "caller untracked input\n")
        after = self._source_snapshot()
        self.assertEqual(after["head"], before["head"])
        self.assertEqual(after["raw_index"], before["raw_index"])
        self.assertEqual(after["cached"], before["cached"])

    def test_patch_delivery_keeps_private_checkpoint_separate_from_dirty_caller_handoff(self) -> None:
        for overlaps_product_file in (False, True):
            with self.subTest(overlaps_product_file=overlaps_product_file):
                suffix = "overlap" if overlaps_product_file else "unrelated"
                self.source = self.root / f"source-private-checkpoint-{suffix}"
                self.store = self.root / f"workspace-store-private-checkpoint-{suffix}"
                self._init_source()

                (self.source / "inherited.txt").write_text("caller staged unrelated input\n", encoding="utf-8")
                self._git(self.source, "add", "inherited.txt")
                (self.source / "inherited.txt").write_text(
                    "caller staged unrelated input\ncaller unstaged unrelated input\n",
                    encoding="utf-8",
                )
                (self.source / "caller-note.txt").write_text("caller untracked input\n", encoding="utf-8")
                if overlaps_product_file:
                    (self.source / "app.txt").write_text(
                        "base application\ncaller staged scoped context\n",
                        encoding="utf-8",
                    )
                    self._git(self.source, "add", "app.txt")
                    (self.source / "app.txt").write_text(
                        "base application\ncaller staged scoped context\ncaller unstaged scoped context\n",
                        encoding="utf-8",
                    )

                before = self._source_snapshot()
                self.assertIn(b"+caller staged unrelated input", before["cached"])
                self.assertIn(b"+caller unstaged unrelated input", before["working"])
                if overlaps_product_file:
                    self.assertIn(b"+caller staged scoped context", before["cached"])
                    self.assertIn(b"+caller unstaged scoped context", before["working"])
                protected_inputs = {
                    "inherited.txt": "caller staged unrelated input\ncaller unstaged unrelated input\n",
                    "caller-note.txt": "caller untracked input\n",
                    "stable.txt": "stable input\n",
                }
                prepared = self._prepare(f"private checkpoint {suffix}")
                worker = Path(prepared["worktree"])
                inherited_app = (worker / "app.txt").read_text(encoding="utf-8")
                worker_app = inherited_app.replace(
                    "base application\n",
                    "base application\nworker scoped fix\n",
                    1,
                )
                (worker / "app.txt").write_text(worker_app, encoding="utf-8")
                self._git(
                    worker,
                    "commit",
                    "--only",
                    "-q",
                    "-m",
                    "Improve private scoped checkpoint",
                    "--",
                    "app.txt",
                )
                checkpoint = self._git(worker, "rev-parse", "HEAD").stdout.strip()
                self.assertEqual(
                    self._git(worker, "show", "--format=", "--name-only", checkpoint).stdout.splitlines(),
                    ["app.txt"],
                )
                self.assertEqual(self._source_snapshot(), before)

                inspected = self._inspect(prepared, mode="patch")
                self.assertEqual(inspected["delivery"]["mode"], "patch")
                self.assertEqual(inspected["contribution_paths"], ["app.txt"])
                self.assertNotIn("commits", inspected["delivery"])
                self.assertNotIn(checkpoint, json.dumps(inspected["delivery"], sort_keys=True))
                patch = Path(inspected["delivery"]["contribution_patch"])
                patch_text = patch.read_text(encoding="utf-8")
                self.assertIn("+worker scoped fix\n", patch_text)
                self.assertNotIn("inherited.txt", patch_text)
                self.assertNotIn("+caller staged unrelated input\n", patch_text)
                self.assertNotIn("-caller staged unrelated input\n", patch_text)
                if overlaps_product_file:
                    self.assertNotIn("+caller staged scoped context\n", patch_text)
                    self.assertNotIn("-caller staged scoped context\n", patch_text)
                    self.assertNotIn("+caller unstaged scoped context\n", patch_text)
                    self.assertNotIn("-caller unstaged scoped context\n", patch_text)

                self._git(self.source, "apply", "--check", "--binary", str(patch))
                self._git(self.source, "apply", "--binary", str(patch))

                self.assertEqual((self.source / "app.txt").read_text(encoding="utf-8"), worker_app)
                for path, expected in protected_inputs.items():
                    self.assertEqual((self.source / path).read_text(encoding="utf-8"), expected)
                after = self._source_snapshot()
                self.assertEqual(after["head"], before["head"])
                self.assertEqual(after["raw_index"], before["raw_index"])
                self.assertEqual(after["cached"], before["cached"])

    def test_commit_delivery_accepts_exact_clean_range_and_applies_cherry_pick(self) -> None:
        prepared = self._prepare("clean commits")
        worker = Path(prepared["worktree"])
        base = self._git(self.source, "rev-parse", "HEAD").stdout.strip()
        (worker / "app.txt").write_text("base application\nworker committed contribution\n", encoding="utf-8")
        contribution = self._commit(worker, ["app.txt"], "worker contribution")

        patch_view = self._inspect(prepared, mode="patch")

        inspected = self._inspect(
            prepared,
            mode="commits",
            commit_base=base,
            commits=[contribution],
        )

        delivery = inspected["delivery"]
        self.assertEqual(delivery["mode"], "commits")
        self.assertEqual(delivery["base"], base)
        self.assertEqual(delivery["commits"], [contribution])
        self.assertEqual(delivery["commit_paths"], ["app.txt"])
        self.assertEqual(delivery["residual_paths"], [])
        self.assertEqual(delivery["per_commit_paths"], [{"commit": contribution, "paths": ["app.txt"]}])
        self.assertEqual(patch_view["fingerprint"], inspected["fingerprint"])
        self.assertNotEqual(patch_view["delivery_evidence"], inspected["delivery_evidence"])
        self.assertEqual(Path(patch_view["delivery_evidence"]).name, "patch.json")
        self.assertEqual(Path(inspected["delivery_evidence"]).name, "commits.json")
        self.assertEqual(inspected["evidence"]["delivery"], inspected["delivery_evidence"])
        evidence = json.loads(Path(inspected["delivery_evidence"]).read_text(encoding="utf-8"))
        self.assertEqual(evidence["commits"], [contribution])

        self._git(self.source, "cherry-pick", "-x", contribution)
        self.assertEqual(
            (self.source / "app.txt").read_text(encoding="utf-8"),
            "base application\nworker committed contribution\n",
        )
        acceptance = self._acceptance(inspected["fingerprint"], decision="integrated", artifacts=[])
        closed = self._success("close", "--receipt", prepared["receipt"], "--acceptance", str(acceptance))
        self.assertEqual(closed["status"], "closed", closed)
        self.assertFalse(worker.exists(), closed)

    def test_commit_delivery_accepts_rename_with_rename_detection_enabled(self) -> None:
        self._git(self.source, "config", "diff.renames", "true")
        prepared = self._prepare("clean rename")
        worker = Path(prepared["worktree"])
        base = self._git(self.source, "rev-parse", "HEAD").stdout.strip()
        self._git(worker, "mv", "app.txt", "renamed-app.txt")
        self._git(worker, "commit", "-q", "-m", "rename app")
        contribution = self._git(worker, "rev-parse", "HEAD").stdout.strip()

        inspected = self._inspect(
            prepared,
            mode="commits",
            commit_base=base,
            commits=[contribution],
        )

        self.assertEqual(inspected["delivery"]["commit_paths"], ["app.txt", "renamed-app.txt"])
        self.assertEqual(inspected["contribution_paths"], ["app.txt", "renamed-app.txt"])

    def test_commit_delivery_requires_complete_ordered_exact_range(self) -> None:
        self._git(self.source, "commit", "--allow-empty", "-q", "-m", "advance source history")
        wrong_base = self._git(self.source, "rev-parse", "HEAD^").stdout.strip()
        prepared = self._prepare("two commit range")
        worker = Path(prepared["worktree"])
        base = self._git(self.source, "rev-parse", "HEAD").stdout.strip()
        (worker / "app.txt").write_text("base application\nfirst contribution\n", encoding="utf-8")
        first = self._commit(worker, ["app.txt"], "first contribution")
        (worker / "second.txt").write_text("second contribution\n", encoding="utf-8")
        second = self._commit(worker, ["second.txt"], "second contribution")

        valid = self._inspect(
            prepared,
            mode="commits",
            commit_base=base,
            commits=[first, second],
        )
        self.assertEqual(valid["delivery"]["commits"], [first, second])
        self.assertEqual(
            valid["delivery"]["per_commit_paths"],
            [
                {"commit": first, "paths": ["app.txt"]},
                {"commit": second, "paths": ["second.txt"]},
            ],
        )

        omitted = self._inspect(
            prepared,
            mode="commits",
            commit_base=base,
            commits=[second],
            expect_success=False,
        )
        self.assertIn("complete base-to-HEAD contribution range", omitted["error"])

        reordered = self._inspect(
            prepared,
            mode="commits",
            commit_base=base,
            commits=[second, first],
            expect_success=False,
        )
        self.assertIn("final contribution SHA must equal the worker HEAD", reordered["error"])

        incorrect_base = self._inspect(
            prepared,
            mode="commits",
            commit_base=wrong_base,
            commits=[first, second],
            expect_success=False,
        )
        self.assertIn("base must equal the prepared source HEAD", incorrect_base["error"])

        abbreviated = self._inspect(
            prepared,
            mode="commits",
            commit_base=base,
            commits=[first[:12], second],
            expect_success=False,
        )
        self.assertIn("exact full Git commit SHA", abbreviated["error"])

        (self.source / "post-worker-head.txt").write_text("separate target advance\n", encoding="utf-8")
        extra = self._commit(self.source, ["post-worker-head.txt"], "post-worker target advance")
        extra_head = self._inspect(
            prepared,
            mode="commits",
            commit_base=base,
            commits=[first, second, extra],
            expect_success=False,
        )
        self.assertIn("final contribution SHA must equal the worker HEAD", extra_head["error"])

    def test_commit_delivery_rejects_dirty_inherited_snapshot(self) -> None:
        self._make_dirty_source()
        before = self._source_snapshot()
        prepared = self._prepare("dirty commit")
        worker = Path(prepared["worktree"])
        base = self._git(self.source, "rev-parse", "HEAD").stdout.strip()
        (worker / "app.txt").write_text("base application\nworker attempted commit\n", encoding="utf-8")
        contribution = self._commit(worker, ["app.txt"], "attempted contribution")

        error = self._inspect(
            prepared,
            mode="commits",
            commit_base=base,
            commits=[contribution],
            expect_success=False,
        )

        self.assertIn("clean inherited snapshot", error["error"])
        after = self._source_snapshot()
        self.assertEqual(after, before)

    def test_delivery_modes_reject_mismatched_or_empty_commit_arguments(self) -> None:
        prepared = self._prepare("delivery argument guards")
        base = self._git(self.source, "rev-parse", "HEAD").stdout.strip()

        missing_mode = self._inspect(
            prepared,
            commit_base=base,
            expect_success=False,
        )
        self.assertIn("require an explicit --delivery-mode commits", missing_mode["error"])

        patch_commit_argument = self._inspect(
            prepared,
            mode="patch",
            commit_base=base,
            expect_success=False,
        )
        self.assertIn("patch delivery does not accept commit arguments", patch_commit_argument["error"])

        empty_commits = self._inspect(
            prepared,
            mode="commits",
            commit_base=base,
            expect_success=False,
        )
        self.assertIn("requires at least one explicit --commit SHA", empty_commits["error"])

    def test_commit_delivery_rejects_uncommitted_residual_deliverable(self) -> None:
        prepared = self._prepare("residual deliverable")
        worker = Path(prepared["worktree"])
        base = self._git(self.source, "rev-parse", "HEAD").stdout.strip()
        (worker / "app.txt").write_text("base application\ncommitted part\n", encoding="utf-8")
        contribution = self._commit(worker, ["app.txt"], "committed part")
        (worker / "uncommitted-deliverable.txt").write_text("must not be omitted\n", encoding="utf-8")

        error = self._inspect(
            prepared,
            mode="commits",
            commit_base=base,
            commits=[contribution],
            expect_success=False,
        )

        self.assertIn("residual staged, unstaged, or untracked deliverables", error["error"])
        self.assertIn("uncommitted-deliverable.txt", error["error"])

    def test_commit_delivery_rejects_committed_artifact_and_transient_paths(self) -> None:
        base = self._git(self.source, "rev-parse", "HEAD").stdout.strip()
        artifact_prepared = self._prepare("committed artifact")
        artifact_worker = Path(artifact_prepared["worktree"])
        (artifact_worker / "app.txt").write_text("base application\ncommitted code\n", encoding="utf-8")
        report = artifact_worker / "reports" / "handoff.md"
        report.parent.mkdir()
        report.write_text("committed report is not a report artifact\n", encoding="utf-8")
        artifact_commit = self._commit(artifact_worker, ["app.txt", "reports/handoff.md"], "code and report")
        artifact_error = self._inspect(
            artifact_prepared,
            mode="commits",
            artifacts=["reports/handoff.md"],
            commit_base=base,
            commits=[artifact_commit],
            expect_success=False,
        )
        self.assertIn("artifacts or discard paths", artifact_error["error"])

        transient_prepared = self._prepare("transient commit")
        transient_worker = Path(transient_prepared["worktree"])
        (transient_worker / "app.txt").write_text("base application\nfinal code\n", encoding="utf-8")
        (transient_worker / "scratch.txt").write_text("transient committed scratch\n", encoding="utf-8")
        first = self._commit(transient_worker, ["app.txt", "scratch.txt"], "code plus scratch")
        self._git(transient_worker, "rm", "-q", "scratch.txt")
        self._git(transient_worker, "commit", "-q", "-m", "remove scratch")
        second = self._git(transient_worker, "rev-parse", "HEAD").stdout.strip()
        transient_error = self._inspect(
            transient_prepared,
            mode="commits",
            commit_base=base,
            commits=[first, second],
            expect_success=False,
        )
        self.assertIn("outside the final worker contribution", transient_error["error"])
        self.assertIn("scratch.txt", transient_error["error"])

    def test_report_only_archives_report_and_rejects_changed_inherited_input(self) -> None:
        prepared = self._prepare("report only")
        worker = Path(prepared["worktree"])
        report = worker / "reports" / "review.md"
        report.parent.mkdir()
        report.write_text("review findings\n", encoding="utf-8")
        inspected = self._inspect(prepared, mode="report-only", artifacts=["reports/review.md"])
        self.assertEqual(inspected["delivery"]["mode"], "report-only")
        self.assertEqual(inspected["delivery"]["contribution_paths"], [])
        acceptance = self._acceptance(
            inspected["fingerprint"],
            decision="report-consumed",
            artifacts=[{"path": "reports/review.md", "purpose": "review findings"}],
        )
        closed = self._success("close", "--receipt", prepared["receipt"], "--acceptance", str(acceptance))
        self.assertEqual(closed["status"], "closed", closed)
        archived = Path(closed["archived_artifacts"][0]["archive"])
        self.assertEqual(archived.read_text(encoding="utf-8"), "review findings\n")
        self.assertFalse(worker.exists(), closed)

        unsafe_prepared = self._prepare("report inherited edit")
        unsafe_worker = Path(unsafe_prepared["worktree"])
        (unsafe_worker / "inherited.txt").write_text("analysis must not alter input\n", encoding="utf-8")
        error = self._inspect(
            unsafe_prepared,
            mode="report-only",
            artifacts=["inherited.txt"],
            expect_success=False,
        )
        self.assertIn("cannot classify edits to inherited repository inputs", error["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
