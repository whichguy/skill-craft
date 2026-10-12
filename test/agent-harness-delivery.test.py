#!/usr/bin/env python3
"""Real-Git delivery checks for the agent-harness parent integration boundary."""

from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from typing import Any

from git_fixture import isolate_git_environment


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills/in-parallel/scripts/delivery.py"
SPEC = importlib.util.spec_from_file_location("agent_harness_delivery", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
delivery = importlib.util.module_from_spec(SPEC)
sys.path.insert(0, str(MODULE_PATH.parent))
try:
    SPEC.loader.exec_module(delivery)
finally:
    sys.path.pop(0)


class AgentHarnessDeliveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="agent-harness-delivery-")
        self.root = Path(self.tmp.name).resolve()
        isolate_git_environment(self, self.root / "test-home")
        self.source = self.root / "source"
        self.source.mkdir()
        self._git(self.source, "init", "-q", "--initial-branch=main")
        self._git(self.source, "config", "user.email", "delivery@example.invalid")
        self._git(self.source, "config", "user.name", "Agent Harness Delivery")
        (self.source / ".gitignore").write_text(".claspignore\n*.ignored\n", encoding="utf-8")
        (self.source / "parent.txt").write_text("parent base\n", encoding="utf-8")
        (self.source / "stable.txt").write_text("stable base\n", encoding="utf-8")
        (self.source / "binary.dat").write_bytes(b"base\x00binary\n")
        for number in range(1, 5):
            (self.source / f"worker{number}.txt").write_text(f"worker {number} base\n", encoding="utf-8")
        self._git(self.source, "add", ".gitignore", "parent.txt", "stable.txt", "binary.dat",
                  "worker1.txt", "worker2.txt", "worker3.txt", "worker4.txt")
        self._git(self.source, "commit", "-q", "-m", "fixture base")
        self._git(self.source, "tag", "fixture-baseline")
        self.packet_dir = self.root / "packets"
        self.packet_dir.mkdir()
        self.worktree_serial = 0

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _git(self, cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
        result = subprocess.run(["git", "-C", str(cwd), *args], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, check=False)
        if check and result.returncode:
            self.fail(f"git {' '.join(args)} failed in {cwd}: {result.stderr.decode(errors='replace')}")
        return result

    def _make_dirty_parent(self) -> None:
        (self.source / "parent.txt").write_text("parent staged\n", encoding="utf-8")
        self._git(self.source, "add", "parent.txt")
        (self.source / "parent.txt").write_text("parent staged\nparent unstaged\n", encoding="utf-8")
        (self.source / "caller-note.txt").write_text("caller untracked input\n", encoding="utf-8")
        (self.source / "binary.dat").write_bytes(b"staged\x00binary\x01\n")
        self._git(self.source, "add", "binary.dat")
        (self.source / "binary.dat").write_bytes(b"staged\x00binary\x01\nunstaged\n")
        (self.source / ".claspignore").write_text("ignored deployment rules\n", encoding="utf-8")
        (self.source / "local.ignored").write_text("ignored source input\n", encoding="utf-8")

    def _packet(self, *, worker_id: str, mode: str, write_set: list[str], workspace_kind: str,
                workspace_root: Path, receipt: Path, delivery_mode: str | None = None,
                commit_base: str | None = None, ephemeral_paths: list[str] | None = None,
                inspection: dict[str, Any] | None = None, current_evidence: dict[str, Any] | None = None) -> dict[str, Any]:
        packet_path = self.packet_dir / f"{worker_id}.binding.json"
        result_path = self.packet_dir / f"{worker_id}.verify.json"
        binding: dict[str, Any] = {
            "schema": "ask-agent.task.binding.v1",
            "version": 1,
            "status": "READY_TO_LAUNCH",
            "package": {"skill_card": "/fixture/SKILL.md"},
            "task": {"mode": mode, "delivery_mode": delivery_mode, "write_set": write_set},
            "workspace": {
                "route": workspace_kind,
                "source": str(self.source),
                "root": str(workspace_root),
                "launch_cwd": str(workspace_root),
                "receipt": str(receipt),
                "baseline": str(self.root / f"{worker_id}.baseline.json"),
                "branch": self._git(workspace_root, "branch", "--show-current").stdout.decode().strip()
                if workspace_kind == "worktree" else "main",
            },
        }
        if commit_base is not None:
            binding["workspace"]["commit_base"] = commit_base
        digest = hashlib.sha256(json.dumps(binding, sort_keys=True, separators=(",", ":"),
                                          ensure_ascii=True).encode()).hexdigest()
        binding["binding_sha256"] = digest
        packet_bytes = json.dumps(binding, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        packet_path.write_bytes(packet_bytes)

        if mode == "ephemeral":
            evidence = {"ephemeral_audit": {
                "status": "ephemeral-audit", "findings_only": True,
                "changed_paths": ephemeral_paths or [], "scratch_retained": True,
                "head": self._git(workspace_root, "rev-parse", "HEAD").stdout.decode().strip(),
                "branch": self._git(workspace_root, "branch", "--show-current").stdout.decode().strip(),
            }}
        elif workspace_kind == "current":
            evidence = current_evidence or {
                "status": "ok", "root": str(self.source), "head": self._git(self.source, "rev-parse", "HEAD").stdout.decode().strip(),
                "branch": "main", "changed_paths": [], "write_set": write_set,
                "outside_write_set": [], "verdict": "unchanged",
            }
        else:
            evidence = {"inspection": inspection or {}}
        verified = {
            "status": "READY_FOR_PARENT_ACCEPTANCE", "command": "verify-return",
            "binding_sha256": digest, "workspace_evidence": evidence,
            "native_lifecycle_verified": False, "semantic_acceptance": "pending",
        }
        result_path.write_text(json.dumps(verified, sort_keys=True), encoding="utf-8")
        script_path = self.packet_dir / f"{worker_id}.verify.py"
        script_path.write_text(
            "import json, pathlib, sys\n"
            f"binding = json.loads(pathlib.Path(sys.argv[sys.argv.index('--binding') + 1]).read_text())\n"
            "expected = sys.argv[sys.argv.index('--expected-binding-sha256') + 1]\n"
            f"result = json.loads(pathlib.Path({str(result_path)!r}).read_text())\n"
            "if binding.get('binding_sha256') != expected or result.get('binding_sha256') != expected:\n"
            "    raise SystemExit(3)\n"
            "print(json.dumps(result, sort_keys=True))\n",
            encoding="utf-8",
        )
        prepared: dict[str, Any] = {
            "status": "READY_TO_LAUNCH",
            "packet": {"path": str(packet_path), "sha256": hashlib.sha256(packet_bytes).hexdigest(),
                       "binding_sha256": digest},
        }
        if workspace_kind == "worktree":
            prepared["commands"] = {"verify-return": {
                "argv": [sys.executable, str(script_path), "verify-return", "--binding", str(packet_path),
                         "--expected-binding-sha256", digest],
                "cwd": str(self.source),
            }}
        return {"id": worker_id, "prepared": prepared, "verified": verified}

    def _worktree_worker(self, number: int, *, mode: str = "edit", delivery_mode: str = "commits",
                         relative: str | None = None, value: str | None = None) -> dict[str, Any]:
        self.worktree_serial += 1
        relative = relative or f"worker{number}.txt"
        value = value or f"worker {number} contribution\n"
        worker_root = self.root / f"worker-{number}-{self.worktree_serial}"
        branch = f"delivery-worker-{number}-{self.worktree_serial}"
        self._git(self.source, "worktree", "add", "-q", "-b", branch, str(worker_root), "HEAD")
        receipt = self.root / f"receipt-{number}.json"
        receipt.write_text("{}\n", encoding="utf-8")
        base = self._git(worker_root, "rev-parse", "HEAD").stdout.decode().strip()
        (worker_root / relative).write_text(value, encoding="utf-8")
        if mode == "ephemeral":
            return self._packet(worker_id=f"worker-{number}", mode=mode, write_set=[relative],
                                workspace_kind="worktree", workspace_root=worker_root, receipt=receipt,
                                ephemeral_paths=[relative])
        commits: list[str] = []
        if delivery_mode == "commits":
            self._git(worker_root, "add", relative)
            self._git(worker_root, "commit", "-q", "-m", f"worker {number} contribution")
            commits = [self._git(worker_root, "rev-parse", "HEAD").stdout.decode().strip()]
            patch_result = self._git(worker_root, "diff", "--binary", base, commits[0], "--", relative)
        else:
            patch_result = self._git(worker_root, "diff", "--binary", base, "--", relative)
        patch_path = self.root / f"worker-{number}.patch"
        patch_path.write_bytes(patch_result.stdout)
        workspace = {
            "status": "returned", "receipt": str(receipt), "worktree": str(worker_root),
            "contribution_paths": [relative],
        }
        delivery_record: dict[str, Any] = {
            "mode": delivery_mode, "base": base, "contribution_patch": str(patch_path),
        }
        if delivery_mode == "commits":
            delivery_record.update({"commits": commits, "commit_paths": [relative],
                                    "per_commit_paths": [{"commit": commits[0], "paths": [relative]}],
                                    "residual_paths": []})
        else:
            delivery_record["contribution_paths"] = [relative]
        workspace["delivery"] = delivery_record
        inspection = workspace
        binding_commit_base = base if delivery_mode == "commits" else None
        return self._packet(worker_id=f"worker-{number}", mode=mode, write_set=[relative],
                            workspace_kind="worktree", workspace_root=worker_root, receipt=receipt,
                            delivery_mode=delivery_mode, commit_base=binding_commit_base,
                            inspection=inspection)

    def _move_patch_to_inspection_evidence(self, worker: dict[str, Any], *, conflicting_path: Path | None = None) -> str:
        inspection = worker["verified"]["workspace_evidence"]["inspection"]
        delivery_record = inspection["delivery"]
        actual_path = delivery_record.pop("contribution_patch")
        inspection["evidence"] = {"contribution_patch": actual_path}
        if conflicting_path is not None:
            delivery_record["contribution_patch"] = str(conflicting_path)
        result_path = self.packet_dir / f"{worker['id']}.verify.json"
        result_path.write_text(json.dumps(worker["verified"], sort_keys=True), encoding="utf-8")
        return actual_path

    def _request(self, *, mode: str = "edit", workspace: str = "worktree", integration: str = "apply",
                 checks: list[list[str]] | None = None) -> dict[str, Any]:
        if checks is None:
            checks = [[sys.executable, "-c", "pass"]] if mode == "edit" and integration == "apply" else []
        return {"source": str(self.source), "workspace": workspace, "mode": mode,
                "integration": integration, "checks": checks}

    def test_validate_request_returns_a_detached_normalized_request(self) -> None:
        request = self._request(checks=[[sys.executable, "-c", "pass"]])
        original = copy.deepcopy(request)
        normalized = delivery.validate_request(request)

        self.assertEqual(set(normalized), {"source", "workspace", "mode", "integration", "checks"})
        self.assertEqual(normalized, original)
        self.assertIsNot(normalized, request)
        self.assertIsNot(normalized["checks"], request["checks"])
        self.assertIsNot(normalized["checks"][0], request["checks"][0])
        normalized["checks"][0][2] = "changed"
        self.assertEqual(request, original)
        with self.assertRaises(delivery.DeliveryError) as caught:
            delivery.validate_request({**request, "mode": []})
        self.assertEqual(caught.exception.payload["code"], "invalid_mode")
        self.assertEqual(caught.exception.payload["status"], "BLOCKED")

    def test_fixture_git_environment_isolated_from_host_home_and_external_git_state(self) -> None:
        hostile_home = self.root / "hostile-home"
        hooks = self.root / "hostile-hooks"
        external = self.root / "external-repository"
        external_index = self.root / "external.index"
        hook_sentinel = self.root / "hook-sentinel"
        hostile_home.mkdir()
        hooks.mkdir()
        external.mkdir()

        xdg_git_config = hostile_home / ".config" / "git"
        xdg_git_config.mkdir(parents=True)
        attributes = hostile_home / "attributes"
        attributes.write_text("*.txt text eol=crlf\n", encoding="utf-8")
        hook_sentinel.write_text("untouched\n", encoding="utf-8")
        hook = hooks / "pre-commit"
        hook.write_text(f"#!/bin/sh\nprintf changed > {shlex.quote(str(hook_sentinel))}\n", encoding="utf-8")
        hook.chmod(0o755)
        (hostile_home / ".gitconfig").write_text(
            "[core]\n"
            f"\tattributesFile = {attributes}\n",
            encoding="utf-8",
        )
        (xdg_git_config / "config").write_text(
            "[core]\n"
            f"\thooksPath = {hooks}\n",
            encoding="utf-8",
        )

        self._git(external, "init", "-q", "--initial-branch=main")
        self._git(external, "config", "user.email", "external@example.invalid")
        self._git(external, "config", "user.name", "Disposable External")
        (external / "external.txt").write_text("external baseline\n", encoding="utf-8")
        self._git(external, "add", "external.txt")
        self._git(external, "commit", "-q", "-m", "external baseline")

        external_env = {
            **os.environ,
            "GIT_DIR": str(external / ".git"),
            "GIT_WORK_TREE": str(external),
            "GIT_INDEX_FILE": str(external_index),
        }
        index_setup = subprocess.run(
            ["git", "read-tree", "HEAD"], cwd=external, env=external_env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(index_setup.returncode, 0, index_setup.stderr.decode(errors="replace"))
        external_index_before = external_index.read_bytes()
        git_index_before = (external / ".git" / "index").read_bytes()
        hook_sentinel_before = hook_sentinel.read_bytes()

        probe = r"""
import json, os, subprocess, sys, unittest
from pathlib import Path

root, home, repo = map(Path, sys.argv[1:4])
sys.path.insert(0, str(root / "test"))
sys.path.insert(0, str(root / "skills/in-parallel/scripts"))
from git_fixture import isolate_git_environment

case = unittest.TestCase()
original = os.environ.copy()
try:
    isolate_git_environment(case, home)
    assert not any(key.startswith("GIT_") for key in os.environ), os.environ
    repo.mkdir()
    def git(*args):
        return subprocess.run(["git", "-C", str(repo), *args], env=os.environ.copy(),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    git("init", "-q", "--initial-branch=main")
    git("config", "user.email", "isolated@example.invalid")
    git("config", "user.name", "Isolated Fixture")
    (repo / "sample.txt").write_text("fixture content\n", encoding="utf-8")
    attributes = git("check-attr", "eol", "--", "sample.txt").stdout.decode().strip()
    assert attributes.endswith("eol: unspecified"), attributes
    git("add", "sample.txt")
    git("commit", "-q", "-m", "fixture")
    import delivery
    snapshot = delivery.capture(repo)
    assert snapshot["root"] == str(repo.resolve()), snapshot
    print(json.dumps({"root": snapshot["root"], "attributes": attributes}, sort_keys=True))
finally:
    case.doCleanups()
assert os.environ == original, "fixture environment cleanup did not restore the caller environment"
"""
        hostile_environment = {
            **os.environ,
            "HOME": str(hostile_home),
            "XDG_CONFIG_HOME": str(hostile_home / ".config"),
            "GIT_DIR": str(external / ".git"),
            "GIT_WORK_TREE": str(external),
            "GIT_INDEX_FILE": str(external_index),
        }
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-c", probe, str(ROOT),
             str(self.root / "isolated-home"), str(self.root / "isolated-repository")],
            cwd=self.root, env=hostile_environment, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(result.returncode, 0, f"stdout: {result.stdout}\nstderr: {result.stderr}")
        self.assertIn('"attributes": "sample.txt: eol: unspecified"', result.stdout)
        self.assertEqual(hook_sentinel.read_bytes(), hook_sentinel_before)
        self.assertEqual(external_index.read_bytes(), external_index_before)
        self.assertEqual((external / ".git" / "index").read_bytes(), git_index_before)

    def test_preflight_rejects_malformed_inputs_without_reserving_run(self) -> None:
        baseline = delivery.capture(self.source)
        worker = self._worktree_worker(1)
        valid = self._request()
        cases = [
            ("missing-field", {key: value for key, value in valid.items() if key != "mode"},
             baseline, [worker], "invalid_request_fields"),
            ("enum-type", {**valid, "mode": []}, baseline, [worker], "invalid_mode"),
            ("nul-check", {**valid, "checks": [[sys.executable, "-c", "pass\0"]]},
             baseline, [worker], "invalid_checks"),
            ("checks-required", {**valid, "checks": []}, baseline, [worker], "checks_required"),
            ("baseline-shape", valid, {"schema": delivery.SNAPSHOT_SCHEMA}, [worker], "invalid_baseline"),
            ("workers-shape", valid, baseline, [{"id": "worker-1"}], "invalid_worker"),
        ]
        before_source = delivery.capture(self.source)
        for name, request, supplied_baseline, workers, code in cases:
            with self.subTest(name=name):
                run = self.root / f"run-preflight-{name}"
                result = delivery.deliver(run, request, supplied_baseline, workers)
                self.assertEqual(result["status"], "BLOCKED", result)
                self.assertEqual(result["failure"]["code"], code)
                self.assertFalse(run.exists())
                self.assertTrue(delivery._snapshot_equal(delivery.capture(self.source), before_source))

    def test_nested_baseline_records_block_before_reserving_attempt(self) -> None:
        os.symlink("parent.txt", self.source / "baseline-link")
        (self.source / "worker1.txt").unlink()
        (self.source / "worker2.txt").unlink()
        (self.source / "worker2.txt").mkdir()
        baseline = delivery.capture(self.source)
        file_index = next(i for i, row in enumerate(baseline["files"]) if row["type"] == "file")
        missing_index = next(i for i, row in enumerate(baseline["files"]) if row["type"] == "missing")
        other_index = next(i for i, row in enumerate(baseline["files"]) if row["type"] == "other")
        symlink_index = next(i for i, row in enumerate(baseline["files"]) if row["type"] == "symlink")
        request = self._request(mode="report-only", workspace="current")
        worker_row = {"id": "shape-only", "prepared": {}, "verified": {}}
        cases = [
            ("index-fields", lambda value: value["index_entries"].__setitem__(0, {"path": "parent.txt"})),
            ("duplicate-index-identity",
             lambda value: value["index_entries"].append(copy.deepcopy(value["index_entries"][0]))),
            ("file-size", lambda value: value["files"][file_index].pop("size")),
            ("file-hash", lambda value: value["files"][file_index].update(sha256="z" * 64)),
            ("missing-fields", lambda value: value["files"][missing_index].update(mode=0o644)),
            ("other-mode", lambda value: value["files"][other_index].pop("mode")),
            ("symlink-base64", lambda value: value["files"][symlink_index].update(target_b64="%%%")),
            ("symlink-hash", lambda value: value["files"][symlink_index].update(sha256="0" * 64)),
            ("duplicate-file-path",
             lambda value: value["files"].append(copy.deepcopy(value["files"][file_index]))),
        ]
        cases.append(("invalid-head-length", lambda value: value.update(head="a" * 41)))
        for index, invalid_path in enumerate(("../outside", "/outside", "./file", "dir//file", "dir/")):
            cases.append((f"file-path-{index}",
                          lambda value, path=invalid_path: value["files"][file_index].update(path=path)))
            cases.append((f"index-path-{index}",
                          lambda value, path=invalid_path: value["index_entries"][0].update(path=path)))
        for name, mutate in cases:
            with self.subTest(name=name):
                malformed = copy.deepcopy(baseline)
                mutate(malformed)
                run = self.root / f"run-malformed-baseline-{name}"
                result = delivery.deliver(run, request, malformed, [worker_row])
                self.assertEqual(result["status"], "BLOCKED", result)
                self.assertEqual(result["failure"]["code"], "invalid_baseline")
                self.assertFalse(run.exists())

    def test_captured_file_record_variants_pass_delivery_preflight(self) -> None:
        os.symlink("parent.txt", self.source / "snapshot-link")
        (self.source / "worker1.txt").unlink()
        (self.source / "worker2.txt").unlink()
        (self.source / "worker2.txt").mkdir()
        unusual_names = ("wild*\nname", "C:notes", "back\\slash", "café file.txt")
        for unusual_name in unusual_names:
            (self.source / unusual_name).write_text("valid unusual Git path\n", encoding="utf-8")
        baseline = delivery.capture(self.source)
        kinds = {row["path"]: row["type"] for row in baseline["files"]}

        self.assertEqual(kinds["worker1.txt"], "missing")
        self.assertEqual(kinds["worker2.txt"], "other")
        self.assertEqual(kinds["snapshot-link"], "symlink")
        for unusual_name in unusual_names:
            self.assertEqual(kinds[unusual_name], "file")
        worker = self._packet(
            worker_id="report-only-current", mode="report-only", write_set=[],
            workspace_kind="current", workspace_root=self.source, receipt=self.root / "unused-receipt",
        )

        result = delivery.deliver(
            self.root / "run-file-record-variants",
            self._request(mode="report-only", workspace="current"),
            baseline, [worker],
        )

        self.assertEqual(result["status"], "SUCCEEDED", result)

    def test_corrected_preflight_input_can_use_the_same_run_path(self) -> None:
        baseline = delivery.capture(self.source)
        worker = self._worktree_worker(1)
        run = self.root / "run-corrected-preflight"
        invalid = delivery.deliver(run, self._request(checks=[]), baseline, [worker])
        self.assertEqual(invalid["failure"]["code"], "checks_required")
        self.assertFalse(run.exists())

        result = delivery.deliver(run, self._request(), baseline, [worker])
        self.assertEqual(result["status"], "SUCCEEDED", result)

    def test_relative_run_path_is_blocked_without_creating_a_directory(self) -> None:
        baseline = delivery.capture(self.source)
        worker = self._worktree_worker(1)
        run = Path(os.path.relpath(self.root / "run-relative-preflight", Path.cwd()))

        result = delivery.deliver(run, self._request(), baseline, [worker])

        self.assertEqual(result["status"], "BLOCKED", result)
        self.assertEqual(result["failure"]["code"], "invalid_run_directory")
        self.assertFalse(run.exists())

    def test_capture_rejects_relative_and_non_path_sources_with_delivery_errors(self) -> None:
        for source in (Path("."), None):
            with self.subTest(source=source):
                with self.assertRaises(delivery.DeliveryError) as caught:
                    delivery.capture(source)
                self.assertEqual(caught.exception.payload["code"], "invalid_source")
                self.assertEqual(caught.exception.payload["status"], "BLOCKED")

    def test_deliver_does_not_mutate_caller_arguments(self) -> None:
        request = self._request()
        baseline = delivery.capture(self.source)
        worker = self._worktree_worker(1)
        originals = copy.deepcopy((request, baseline, [worker]))

        result = delivery.deliver(self.root / "run-input-immutability", request, baseline, [worker])

        self.assertEqual(result["status"], "SUCCEEDED", result)
        self.assertEqual((request, baseline, [worker]), originals)

    def test_capture_includes_dirty_binary_index_and_root_ignore_files(self) -> None:
        self._make_dirty_parent()
        snapshot = delivery.capture(self.source)
        cached = base64.b64decode(snapshot["cached_diff_b64"])
        files = {record["path"] for record in snapshot["files"]}
        self.assertIn(b"GIT binary patch", cached)
        self.assertIn(".gitignore", files)
        self.assertIn(".claspignore", files)
        self.assertNotIn("local.ignored", files)
        self.assertIn("caller-note.txt", files)
        self.assertEqual(snapshot["schema"], delivery.SNAPSHOT_SCHEMA)

    def test_three_commit_contributions_apply_as_one_batch_and_preserve_dirty_parent(self) -> None:
        self._make_dirty_parent()
        baseline = delivery.capture(self.source)
        workers = [self._worktree_worker(i, delivery_mode="commits") for i in (1, 2, 3)]
        check = [sys.executable, "-c", "print('delivery check passed')"]
        result = delivery.deliver(self.root / "run-three", self._request(checks=[check]), baseline, workers)

        self.assertEqual(result["status"], "SUCCEEDED", result)
        self.assertEqual(result["integration"]["outcome"], "applied")
        self.assertEqual(result["integration"]["postcondition"]["changed_paths"],
                         ["worker1.txt", "worker2.txt", "worker3.txt"])
        self.assertTrue(result["integration"]["postcondition"]["head_and_index_preserved"])
        after = delivery.capture(self.source)
        for key in ("head", "branch", "index_entries", "cached_diff_b64", "cached_diff_sha256"):
            self.assertEqual(after[key], baseline[key], key)
        for number, worker in enumerate(workers, start=1):
            worker_root = Path(worker["verified"]["workspace_evidence"]["inspection"]["worktree"])
            self.assertEqual((self.source / f"worker{number}.txt").read_text(encoding="utf-8"),
                             (worker_root / f"worker{number}.txt").read_text(encoding="utf-8"))
        self.assertEqual((self.source / "parent.txt").read_text(encoding="utf-8"), "parent staged\nparent unstaged\n")
        self.assertEqual((self.source / ".claspignore").read_text(encoding="utf-8"), "ignored deployment rules\n")
        logs = sorted((self.root / "run-three" / "delivery" / "commands").glob("*.json"))
        records = [json.loads(path.read_text(encoding="utf-8")) for path in logs]
        self.assertEqual(sum(record["label"] == "apply-check-batch" for record in records), 1)
        self.assertEqual(sum(record["label"] == "apply-batch" for record in records), 1)
        self.assertEqual(result["checks"][0]["status"], "PASSED")

    def test_ephemeral_worktree_return_never_imports_scratch_changes(self) -> None:
        baseline = delivery.capture(self.source)
        worker = self._worktree_worker(4, mode="ephemeral")
        result = delivery.deliver(self.root / "run-ephemeral", self._request(mode="ephemeral"), baseline, [worker])
        self.assertEqual(result["status"], "SUCCEEDED", result)
        self.assertEqual(result["integration"]["outcome"], "not-applicable")
        self.assertTrue(delivery._snapshot_equal(delivery.capture(self.source), baseline))
        self.assertFalse(any(record.get("label") == "apply-batch" for record in self._command_records("run-ephemeral")))

    def test_return_only_retains_patch_without_importing(self) -> None:
        baseline = delivery.capture(self.source)
        worker = self._worktree_worker(1, delivery_mode="patch")
        result = delivery.deliver(self.root / "run-return-only", self._request(integration="return-only"), baseline, [worker])
        self.assertEqual(result["status"], "SUCCEEDED", result)
        self.assertEqual(result["integration"]["outcome"], "return-only")
        self.assertTrue(delivery._snapshot_equal(delivery.capture(self.source), baseline))
        self.assertFalse(any(record.get("label") == "apply-batch" for record in self._command_records("run-return-only")))

    def test_multiworker_return_only_keeps_delivery_linked_to_each_binding(self) -> None:
        baseline = delivery.capture(self.source)
        workers = [self._worktree_worker(1, delivery_mode="commits"),
                   self._worktree_worker(2, delivery_mode="patch")]
        result = delivery.deliver(self.root / "run-multi-return-only",
                                  self._request(integration="return-only"), baseline, workers)

        self.assertEqual(result["status"], "SUCCEEDED", result)
        summaries = {worker["id"]: worker for worker in result["workers"]}
        self.assertEqual(set(summaries), {worker["id"] for worker in workers})
        for input_worker in workers:
            worker_id = input_worker["id"]
            inspection = input_worker["verified"]["workspace_evidence"]["inspection"]
            returned = inspection["delivery"]
            summary = summaries[worker_id]["delivery"]
            expected_paths = inspection["contribution_paths"]
            self.assertEqual(summary["worker_id"], worker_id)
            self.assertEqual(summary["binding_sha256"], input_worker["prepared"]["packet"]["binding_sha256"])
            self.assertEqual(summary["binding_sha256"], summaries[worker_id]["binding_sha256"])
            self.assertEqual(summary["mode"], returned["mode"])
            self.assertEqual(summary["base"], returned["base"])
            self.assertEqual(summary["contribution_paths"], expected_paths)
            self.assertEqual(summary["commits"], returned.get("commits", []))
            self.assertEqual(summary["per_commit_paths"], returned.get("per_commit_paths", []))
            self.assertEqual(summary["source_patch_path"], returned["contribution_patch"])
            retained_patch = Path(summary["patch_path"])
            self.assertTrue(retained_patch.is_file())
            self.assertEqual(hashlib.sha256(retained_patch.read_bytes()).hexdigest(), summary["patch_sha256"])

    def test_clean_parent_patch_from_inspection_evidence_supports_apply_and_return_only(self) -> None:
        baseline = delivery.capture(self.source)
        apply_worker = self._worktree_worker(1, delivery_mode="commits")
        apply_patch = self._move_patch_to_inspection_evidence(apply_worker)
        apply_result = delivery.deliver(
            self.root / "run-clean-parent-apply",
            self._request(checks=[[sys.executable, "-c", "pass"]]), baseline, [apply_worker])
        self.assertEqual(apply_result["status"], "SUCCEEDED", apply_result)
        self.assertEqual(apply_result["workers"][0]["delivery"]["source_patch_path"], apply_patch)
        self.assertEqual((self.source / "worker1.txt").read_text(encoding="utf-8"), "worker 1 contribution\n")

        return_baseline = delivery.capture(self.source)
        return_worker = self._worktree_worker(2, delivery_mode="commits")
        return_patch = self._move_patch_to_inspection_evidence(return_worker)
        return_result = delivery.deliver(self.root / "run-clean-parent-return",
                                         self._request(integration="return-only"), return_baseline, [return_worker])
        self.assertEqual(return_result["status"], "SUCCEEDED", return_result)
        self.assertEqual(return_result["workers"][0]["delivery"]["source_patch_path"], return_patch)
        self.assertTrue(delivery._snapshot_equal(delivery.capture(self.source), return_baseline))

        conflict_baseline = delivery.capture(self.source)
        conflict_worker = self._worktree_worker(3, delivery_mode="commits")
        conflict_patch = self._move_patch_to_inspection_evidence(
            conflict_worker, conflicting_path=self.root / "different-patch.patch")
        conflict_result = delivery.deliver(self.root / "run-conflicting-patch-paths",
                                           self._request(integration="return-only"), conflict_baseline,
                                           [conflict_worker])
        self.assertEqual(conflict_result["status"], "BLOCKED", conflict_result)
        self.assertEqual(conflict_result["failure"]["code"], "conflicting_contribution_patch_paths")
        self.assertEqual(conflict_result["failure"]["expected"], str(self.root / "different-patch.patch"))
        self.assertEqual(conflict_result["failure"]["observed"], conflict_patch)

    def test_parent_drift_blocks_integration(self) -> None:
        baseline = delivery.capture(self.source)
        worker = self._worktree_worker(1)
        (self.source / "stable.txt").write_text("parent changed after baseline\n", encoding="utf-8")
        result = delivery.deliver(self.root / "run-drift", self._request(), baseline, [worker])
        self.assertEqual(result["status"], "BLOCKED", result)
        self.assertEqual(result["failure"]["code"], "parent_source_drift")
        self.assertFalse(any(record.get("label") == "apply-batch" for record in self._command_records("run-drift")))

    def test_overlapping_contribution_paths_block_the_batch(self) -> None:
        baseline = delivery.capture(self.source)
        first = self._worktree_worker(1, relative="worker1.txt", value="first worker\n")
        second = self._worktree_worker(2, relative="worker1.txt", value="second worker\n")
        result = delivery.deliver(self.root / "run-conflict", self._request(), baseline, [first, second])
        self.assertEqual(result["status"], "BLOCKED", result)
        self.assertEqual(result["failure"]["code"], "overlapping_contributions")
        self.assertEqual((self.source / "worker1.txt").read_text(encoding="utf-8"), "worker 1 base\n")

    def test_missing_and_tampered_packets_block_without_import(self) -> None:
        for name, mutation in (("missing", "missing"), ("tampered", "tampered")):
            with self.subTest(name=name):
                baseline = delivery.capture(self.source)
                worker = self._worktree_worker(1)
                packet_path = Path(worker["prepared"]["packet"]["path"])
                if mutation == "missing":
                    packet_path.unlink()
                else:
                    packet_path.write_bytes(packet_path.read_bytes() + b" ")
                result = delivery.deliver(self.root / f"run-{name}", self._request(), baseline, [worker])
                self.assertEqual(result["status"], "BLOCKED", result)
                self.assertEqual(result["failure"]["code"], "worktree_return_verification_failed")
                nested_codes = {problem.get("code") for problem in result["failure"]["observed"]}
                expected_inner = "invalid_packet_file" if mutation == "missing" else "packet_hash_mismatch"
                self.assertIn(expected_inner, nested_codes)
                self.assertEqual((self.source / "worker1.txt").read_text(encoding="utf-8"), "worker 1 base\n")

    def test_duplicate_integration_attempt_is_blocked_and_not_replayed(self) -> None:
        baseline = delivery.capture(self.source)
        worker = self._worktree_worker(1)
        run = self.root / "run-duplicate"
        first = delivery.deliver(run, self._request(), baseline, [worker])
        after_first = (self.source / "worker1.txt").read_bytes()
        second = delivery.deliver(run, self._request(), baseline, [worker])
        self.assertEqual(first["status"], "SUCCEEDED", first)
        self.assertEqual(second["status"], "BLOCKED", second)
        self.assertEqual(second["failure"]["code"], "delivery_attempt_already_reserved")
        self.assertEqual((self.source / "worker1.txt").read_bytes(), after_first)

    def test_failed_check_reports_failure_and_keeps_applied_files(self) -> None:
        baseline = delivery.capture(self.source)
        worker = self._worktree_worker(1)
        failed_check = [sys.executable, "-c", "raise SystemExit(17)"]
        result = delivery.deliver(self.root / "run-check-fail", self._request(checks=[failed_check]), baseline, [worker])
        self.assertEqual(result["status"], "FAILED", result)
        self.assertEqual(result["integration"]["outcome"], "applied")
        self.assertEqual(result["failure"]["code"], "delivery_check_failed")
        self.assertEqual((self.source / "worker1.txt").read_text(encoding="utf-8"), "worker 1 contribution\n")

    def test_passing_check_that_changes_parent_file_and_index_fails_delivery(self) -> None:
        baseline = delivery.capture(self.source)
        worker = self._worktree_worker(1)
        mutating_check = [sys.executable, "-c",
                          "from pathlib import Path; Path('stable.txt').write_text('check mutation\\n'); "
                          "import subprocess; subprocess.run(['git', 'add', 'stable.txt'], check=True)"]
        run = self.root / "run-check-mutation"
        result = delivery.deliver(run, self._request(checks=[mutating_check]), baseline, [worker])

        self.assertNotEqual(result["status"], "SUCCEEDED", result)
        self.assertEqual(result["checks"][0]["status"], "PASSED")
        self.assertEqual(result["failure"]["code"], "post_check_source_drift")
        self.assertEqual(result["failure"]["observed"]["changed_paths"], ["stable.txt"])
        self.assertFalse(result["failure"]["observed"]["head_and_index_preserved"])
        postcondition = result["check_postcondition"]
        self.assertFalse(postcondition["exact_snapshot_unchanged"])
        self.assertTrue(Path(postcondition["before_snapshot"]).is_file())
        self.assertTrue(Path(postcondition["after_snapshot"]).is_file())

    def test_current_sequential_edits_validate_union_without_rechecking_old_binding(self) -> None:
        baseline = delivery.capture(self.source)
        first = self._packet(worker_id="current-1", mode="edit", write_set=["worker1.txt"],
                             workspace_kind="current", workspace_root=self.source, receipt=self.root / "r1")
        (self.source / "worker1.txt").write_text("current worker one\n", encoding="utf-8")
        second = self._packet(worker_id="current-2", mode="edit", write_set=["worker2.txt"],
                              workspace_kind="current", workspace_root=self.source, receipt=self.root / "r2")
        (self.source / "worker2.txt").write_text("current worker two\n", encoding="utf-8")
        first["verified"]["workspace_evidence"].update({
            "changed_paths": ["worker1.txt"], "write_set": ["worker1.txt"], "outside_write_set": [],
            "verdict": "changed-within-write-set",
        })
        # The first verification is immutable evidence from collection time; later source changes are expected.
        second["verified"]["workspace_evidence"].update({
            "changed_paths": ["worker2.txt"], "write_set": ["worker2.txt"], "outside_write_set": [],
            "verdict": "changed-within-write-set",
        })
        result = delivery.deliver(self.root / "run-current", self._request(workspace="current"), baseline, [first, second])
        self.assertEqual(result["status"], "SUCCEEDED", result)
        self.assertEqual(result["integration"]["outcome"], "current-workspace-validated")
        self.assertEqual(result["integration"]["applied_paths"], ["worker1.txt", "worker2.txt"])

    def _command_records(self, run_name: str) -> list[dict[str, Any]]:
        directory = self.root / run_name / "delivery" / "commands"
        if not directory.exists():
            return []
        return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(directory.glob("*.json"))]


if __name__ == "__main__":
    unittest.main()
