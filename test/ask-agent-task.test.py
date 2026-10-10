#!/usr/bin/env python3
"""Focused real-Git checks for the bounded Ask Agent task wrapper."""

from __future__ import annotations

import json
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "ask-agent"
SCRIPT = SKILL / "scripts" / "ask_agent_task.py"


def git(repo: Path, *args: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
         "-c", "commit.gpgsign=false", *args],
        check=False, capture_output=True, text=True,
    )
    if result.returncode:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")


def git_output(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], check=False, capture_output=True, text=True,
    )
    if result.returncode:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout.strip()


class AskAgentTaskTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="ask-agent-task-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.home = self.base / "home"
        (self.home / ".config").mkdir(parents=True)
        self.repo = self.base / "repo"
        (self.repo / "src").mkdir(parents=True)
        (self.repo / "tests").mkdir()
        (self.repo / "src" / "app.py").write_text("VALUE = 1\n")
        (self.repo / "tests" / "test_app.py").write_text("assert True\n")
        (self.repo / "README.md").write_text("fixture\n")
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "fixture baseline")
        self.other = self.base / "other"
        self.other.mkdir()
        self.store = self.base / "workspace-store"
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        self.env.update({
            "HOME": str(self.home), "XDG_CONFIG_HOME": str(self.home / ".config"),
            "XDG_STATE_HOME": str(self.home / ".state"), "PYTHONDONTWRITEBYTECODE": "1",
        })

    def run_cli(
        self,
        *args: str,
        cwd: Path | None = None,
        packet: dict | None = None,
        raw: str | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict]:
        input_text = raw if raw is not None else (json.dumps(packet) if packet is not None else None)
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), *args],
            cwd=cwd or self.repo, env=self.env, input=input_text,
            capture_output=True, text=True, timeout=90,
        )
        output = result.stdout if result.returncode == 0 else result.stderr
        try:
            return result, json.loads(output)
        except json.JSONDecodeError as exc:
            self.fail(f"wrapper did not return JSON (exit {result.returncode}): {result.stdout!r} {result.stderr!r}: {exc}")

    def request(self, *, workspace: str = "current", mode: str = "edit", **overrides: object) -> dict:
        value = {
            "objective": "Update the fixture value safely",
            "expected_result": "The selected behavior is checked and the handoff lists actual checks",
            "source": str(self.repo), "workspace": workspace, "mode": mode,
            "write_set": ["src/app.py"] if mode in {"edit", "ephemeral"} else [],
        }
        if workspace == "current" and mode == "edit":
            value["exclusive_writer"] = True
        if workspace == "worktree":
            value["writers_quiescent"] = True
            value["store"] = str(self.store)
        value.update(overrides)
        return value

    def prepare(self, request: dict) -> dict:
        result, output = self.run_cli(
            "prepare", "--skill-card", str(SKILL / "SKILL.md"), "--request", "-", packet=request,
        )
        self.assertEqual(result.returncode, 0, output)
        self.assertEqual(output["status"], "READY_TO_LAUNCH")
        self.assertIn("binding", output)
        self.assertEqual(set(output["launch"]) >= {"prompt", "cwd"}, True)
        self.assertEqual(output["payload_sizes"]["prompt_bytes"], len(output["launch"]["prompt"].encode("utf-8")))
        compact = json.dumps(output, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        self.assertEqual(output["payload_sizes"]["stdout_json_bytes"], len(compact))
        return output

    def prepare_packet(self, request: dict, path: Path) -> dict:
        result, output = self.run_cli(
            "prepare", "--skill-card", str(SKILL / "SKILL.md"), "--request", "-", "--packet", str(path),
            packet=request,
        )
        self.assertEqual(result.returncode, 0, output)
        self.assertEqual(output["status"], "READY_TO_LAUNCH")
        self.assertNotIn("binding", output)
        self.assertEqual(Path(output["packet"]["path"]), path.resolve())
        raw_binding = path.read_bytes()
        self.assertEqual(hashlib.sha256(raw_binding).hexdigest(), output["packet"]["sha256"])
        binding = json.loads(raw_binding)
        self.assertEqual(binding["binding_sha256"], output["packet"]["binding_sha256"])
        compact = json.dumps(output, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        self.assertEqual(output["payload_sizes"]["stdout_json_bytes"], len(compact))
        self.assertEqual(output["payload_sizes"]["prompt_bytes"], len(output["launch"]["prompt"].encode()))
        self.assertEqual(output["launch"]["transport"], "packet")
        return output

    def bind_command(
        self, name: str, binding: dict, *, cwd: Path | None = None, expected: str | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict]:
        args = [name, "--binding", "-"]
        if expected is not None:
            args.extend(("--expected-binding-sha256", expected))
        return self.run_cli(*args, cwd=cwd, packet=binding)

    def packet_command(
        self, name: str, packet_path: Path, expected: str, *, cwd: Path | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict]:
        return self.run_cli(name, "--binding", str(packet_path), "--expected-binding-sha256", expected, cwd=cwd)

    def run_generated_command(self, command: dict) -> tuple[subprocess.CompletedProcess[str], dict]:
        result = subprocess.run(
            command["argv"], cwd=Path(command["cwd"]), env=self.env,
            capture_output=True, text=True, timeout=90,
        )
        output_text = result.stdout if result.returncode == 0 else result.stderr
        try:
            return result, json.loads(output_text)
        except json.JSONDecodeError as exc:
            self.fail(f"generated command did not return JSON (exit {result.returncode}): {result.stdout!r} {result.stderr!r}: {exc}")

    def assert_error(self, result: subprocess.CompletedProcess[str], output: dict, code: str) -> None:
        self.assertEqual(result.returncode, 2, output)
        self.assertEqual(output["status"], "ERROR")
        self.assertEqual(output["error"]["code"], code)
        for field in ("expected", "observed", "rationale", "reference", "evidence_paths", "safe_next_step"):
            self.assertIn(field, output["error"])

    def test_packet_prepare_path_with_spaces_and_pinned_round_trip(self) -> None:
        packet_path = self.base / "external packet directory" / "prepared task.json"
        packet_path.parent.mkdir()
        output = self.prepare_packet(self.request(), packet_path)
        binding = json.loads(packet_path.read_text())
        inline = self.prepare(self.request())
        self.assertLess(len(output["launch"]["prompt"]), len(inline["launch"]["prompt"]))
        self.assertIn("Objective: Update the fixture value safely", output["launch"]["prompt"])
        self.assertIn("--expected-binding-sha256", output["launch"]["prompt"])
        self.assertNotIn("Binding JSON", output["launch"]["prompt"])
        self.assertNotIn("binding", output)
        self.assertEqual(output["packet"]["ignored_dependencies_omitted"], [])
        self.assertIsNone(output["packet"]["no_drift_warning"])
        self.assertEqual(set(output["commands"]), {"worker-start", "worker-finish", "verify-return"})
        for name, command in output["commands"].items():
            expected_cwd = binding["workspace"]["source"] if name == "verify-return" else output["launch"]["cwd"]
            self.assertEqual(command["cwd"], expected_cwd)
            self.assertIn("--expected-binding-sha256", command["argv"])
            self.assertEqual(command["argv"][-1], binding["binding_sha256"])
            self.assertEqual(command["argv"][command["argv"].index("--binding") + 1], str(packet_path.resolve()))

        started, start_result = self.run_generated_command(output["commands"]["worker-start"])
        self.assertEqual((started.returncode, start_result["status"]), (0, "WORKER_CONTEXT_READY"), start_result)
        action = start_result["action_packet"]
        self.assertEqual(action["task"], binding["task"])
        self.assertEqual(action["delivery_header"], output["launch"]["delivery_header"])
        self.assertEqual(action["finish_command"], output["commands"]["worker-finish"])
        self.assertIsInstance(action["instructions"], list)
        joined = "\n".join(action["instructions"])
        self.assertIn("one writer", joined)
        self.assertIn("do not delegate", joined)
        self.assertIn("Do not commit", joined)

        finished, finish_result = self.run_generated_command(action["finish_command"])
        self.assertEqual((finished.returncode, finish_result["status"]), (0, "READY_FOR_PARENT_ACCEPTANCE"), finish_result)
        verified, verify_result = self.run_generated_command(output["commands"]["verify-return"])
        self.assertEqual((verified.returncode, verify_result["status"]), (0, "READY_FOR_PARENT_ACCEPTANCE"), verify_result)
        self.assertTrue(packet_path.is_file())

    def test_packet_action_packet_preserves_all_mode_contracts(self) -> None:
        packet_dir = self.base / "mode packets"
        packet_dir.mkdir()
        cases = [
            ("current edit", self.request(), "No commit — edit the current workspace in place",
             ("one writer", "do not delegate", "Do not commit")),
            ("current report-only", self.request(mode="report-only"),
             "Report-only — return findings without filesystem changes", ("make no filesystem changes",)),
            ("worktree report-only", self.request(workspace="worktree", mode="report-only"),
             "Report-only — return findings without filesystem changes", ("make no filesystem changes",)),
            ("ephemeral", self.request(workspace="worktree", mode="ephemeral"),
             "No commit — findings only", ("Do not commit or create a patch", "findings and changed paths only")),
            ("patch", self.request(workspace="worktree", delivery_mode="patch"),
             "Patch — return these changes without committing", ("Do not commit", "return the patch through")),
            ("commits", self.request(workspace="worktree"), "Git commit — return these changes",
             ("commit only the task contribution paths", "Never use git add . or git add -A")),
        ]
        for index, (label, request, header, required_instructions) in enumerate(cases):
            with self.subTest(mode=label):
                output = self.prepare_packet(request, packet_dir / f"{index}.json")
                binding = json.loads(Path(output["packet"]["path"]).read_text())
                start, result = self.run_generated_command(output["commands"]["worker-start"])
                self.assertEqual((start.returncode, result["status"]), (0, "WORKER_CONTEXT_READY"), result)
                action = result["action_packet"]
                self.assertEqual(action["task"], binding["task"])
                self.assertEqual(action["delivery_header"], header)
                instructions = "\n".join(action["instructions"])
                for required in required_instructions:
                    self.assertIn(required, instructions)
                self.assertIn("Preserve inherited changes and unrelated files", instructions)
                self.assertIn("Do not reset, stash, close, merge, or integrate", instructions)
                self.assertIn("If blocked, stop and return the reason with evidence", instructions)
                self.assertEqual(action["finish_command"], output["commands"]["worker-finish"])
                if label == "commits":
                    self.assertIn(binding["workspace"]["commit_base"], instructions)

    def test_packet_destination_allows_external_sibling_of_installed_package_but_rejects_package_git_metadata(self) -> None:
        unrelated_repo = self.base / "unrelated ancestor repository"
        package_root = unrelated_repo / "installed" / "selected package"
        scripts = package_root / "scripts"
        scripts.mkdir(parents=True)
        shutil.copy2(SKILL / "SKILL.md", package_root / "SKILL.md")
        shutil.copy2(SKILL / "scripts" / "ask_agent_task.py", scripts / "ask_agent_task.py")
        shutil.copy2(SKILL / "scripts" / "ask_agent_workspace.py", scripts / "ask_agent_workspace.py")
        git(unrelated_repo, "init", "-q", "-b", "main")
        git(unrelated_repo, "add", ".")
        git(unrelated_repo, "commit", "-qm", "installed package fixture")

        def prepare_installed(packet_path: Path) -> tuple[subprocess.CompletedProcess[str], dict]:
            completed = subprocess.run(
                [sys.executable, "-B", str(scripts / "ask_agent_task.py"), "prepare", "--skill-card",
                 str(package_root / "SKILL.md"), "--request", "-", "--packet", str(packet_path)],
                cwd=self.repo, env=self.env, input=json.dumps(self.request()),
                capture_output=True, text=True, timeout=90,
            )
            text = completed.stdout if completed.returncode == 0 else completed.stderr
            return completed, json.loads(text)

        external_packet = unrelated_repo / "external sibling packet.json"
        result, output = prepare_installed(external_packet)
        self.assertEqual(result.returncode, 0, output)
        self.assertEqual(output["status"], "READY_TO_LAUNCH")
        self.assertTrue(external_packet.is_file())
        self.assertNotIn("binding", output)

        metadata_packet = unrelated_repo / ".git" / "external packet.json"
        result, output = prepare_installed(metadata_packet)
        self.assert_error(result, output, "packet_path_out_of_bounds")
        self.assertFalse(metadata_packet.exists())
        self.assertTrue(any(str(unrelated_repo / ".git") in path for path in output["error"]["evidence_paths"]))

    def test_current_packet_late_write_failure_preserves_actionable_diagnostics(self) -> None:
        spec = importlib.util.spec_from_file_location("ask_agent_task_failure_probe", SCRIPT)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        task_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(task_module)
        packet_path = self.base / "late write failure.json"
        original_write_packet = task_module._write_packet

        def fail_packet_open(path: Path, binding: dict, bound_workspace: dict) -> tuple[bytes, str]:
            with mock.patch.object(task_module.os, "open", side_effect=OSError("injected packet open failure")):
                return original_write_packet(path, binding, bound_workspace)

        with mock.patch.object(task_module, "_write_packet", side_effect=fail_packet_open):
            with self.assertRaises(task_module.TaskError) as caught:
                task_module.prepare_task(self.request(), SKILL / "SKILL.md", packet_path)

        error = caught.exception.payload
        self.assertEqual(error["code"], "packet_write_failed")
        self.assertIn("injected packet open failure", error["observed"])
        self.assertTrue(error["rationale"])
        self.assertEqual(error["reference"], "references/task-interface.md#workspace")
        self.assertIn("exclusively write", error["expected"])
        self.assertIn(str(packet_path), error["evidence_paths"])
        self.assertIn(str(self.repo), error["evidence_paths"])
        self.assertTrue(all(isinstance(path, str) for path in error["evidence_paths"]))
        self.assertIn("receipt and worktree", error["safe_next_step"])
        self.assertFalse(packet_path.exists())

    def test_packet_destinations_are_rejected_before_worktree_creation(self) -> None:
        outside = self.base / "packet errors"
        outside.mkdir()
        existing = outside / "existing.json"
        existing.write_text("keep this file\n")
        symlink_file = outside / "symlink.json"
        symlink_file.symlink_to(outside / "missing-target.json")
        symlink_parent = outside / "source alias"
        symlink_parent.symlink_to(self.repo, target_is_directory=True)
        linked_source = self.base / "linked source"
        git(self.repo, "worktree", "add", "-qb", "packet-boundary-test", str(linked_source))

        cases = [
            ("existing", self.request(workspace="worktree"), existing, "packet_destination_exists"),
            ("symlink file", self.request(workspace="worktree"), symlink_file, "packet_destination_exists"),
            ("source root", self.request(workspace="worktree"), self.repo / "packet.json", "packet_path_out_of_bounds"),
            ("source subdirectory ancestor", self.request(workspace="worktree", mode="report-only", source=str(self.repo / "src")),
             self.repo / "ancestor packet.json", "packet_path_out_of_bounds"),
            ("selected package", self.request(workspace="worktree"), SKILL / "package packet.json", "packet_path_out_of_bounds"),
            ("resolved symlink parent", self.request(workspace="worktree"), symlink_parent / "parent packet.json", "packet_path_out_of_bounds"),
            ("git common metadata", self.request(workspace="worktree", mode="report-only", source=str(linked_source)),
             self.repo / ".git" / "external packet.json", "packet_path_out_of_bounds"),
            ("relative destination", self.request(workspace="worktree"), Path("relative-packet.json"), "invalid_packet_path"),
        ]
        for label, request, path, code in cases:
            with self.subTest(destination=label):
                result, output = self.run_cli(
                    "prepare", "--skill-card", str(SKILL / "SKILL.md"), "--request", "-", "--packet", str(path),
                    packet=request,
                )
                self.assert_error(result, output, code)
                self.assertTrue(output["error"]["rationale"])
                self.assertTrue(output["error"]["evidence_paths"])
                self.assertFalse(self.store.exists())
        self.assertEqual(existing.read_text(), "keep this file\n")

    def test_expected_binding_pin_rejects_valid_replacement_before_other_checks(self) -> None:
        packet_path = self.base / "pinned packet.json"
        output = self.prepare_packet(self.request(), packet_path)
        old_digest = output["packet"]["binding_sha256"]
        original = json.loads(packet_path.read_text())
        replacement = json.loads(json.dumps(original))
        replacement["task"]["objective"] = "A different but internally valid task"
        replacement["binding_sha256"] = hashlib.sha256(
            json.dumps({key: value for key, value in replacement.items() if key != "binding_sha256"},
                       sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest()
        replacement_bytes = json.dumps(replacement, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        packet_path.write_bytes(replacement_bytes)
        self.assertEqual(hashlib.sha256(replacement_bytes).hexdigest(), hashlib.sha256(packet_path.read_bytes()).hexdigest())

        for command_name in ("worker-start", "worker-finish", "verify-return"):
            with self.subTest(command=command_name):
                result, error = self.packet_command(command_name, packet_path, old_digest, cwd=self.other)
                self.assert_error(result, error, "expected_binding_sha256_mismatch")
                self.assertIn("before package or workspace checks", error["error"]["rationale"])

        new_digest = replacement["binding_sha256"]
        started, start_result = self.packet_command("worker-start", packet_path, new_digest, cwd=self.repo)
        self.assertEqual((started.returncode, start_result["status"]), (0, "WORKER_CONTEXT_READY"), start_result)
        self.assertEqual(start_result["action_packet"]["task"], replacement["task"])

        package_replacement = json.loads(json.dumps(original))
        package_replacement["package"]["task_script_sha256"] = "0" * 64
        package_replacement["binding_sha256"] = hashlib.sha256(
            json.dumps({key: value for key, value in package_replacement.items() if key != "binding_sha256"},
                       sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest()
        packet_path.write_bytes(json.dumps(package_replacement, sort_keys=True, separators=(",", ":"),
                                           ensure_ascii=True).encode())
        stale_pin, stale_error = self.packet_command("worker-start", packet_path, old_digest, cwd=self.repo)
        self.assert_error(stale_pin, stale_error, "expected_binding_sha256_mismatch")
        current_pin, package_error = self.packet_command(
            "worker-start", packet_path, package_replacement["binding_sha256"], cwd=self.repo)
        self.assert_error(current_pin, package_error, "package_identity_mismatch")

    def test_packet_preserves_workspace_warnings(self) -> None:
        plain = self.base / "plain report directory"
        plain.mkdir()
        plain_packet = self.base / "plain report.json"
        plain_output = self.prepare_packet(
            self.request(mode="report-only", source=str(plain)), plain_packet)
        self.assertTrue(plain_output["packet"]["no_drift_warning"])
        plain_started, plain_result = self.run_generated_command(plain_output["commands"]["worker-start"])
        self.assertEqual((plain_started.returncode, plain_result["status"]), (0, "WORKER_CONTEXT_READY"), plain_result)
        plain_action = plain_result["action_packet"]
        self.assertEqual(plain_action["no_drift_warning"], plain_output["packet"]["no_drift_warning"])
        self.assertTrue(any("No-drift limitation" in item for item in plain_action["instructions"]))

        (self.repo / ".gitignore").write_text("ignored-inputs/\n")
        git(self.repo, "add", "--", ".gitignore")
        git(self.repo, "commit", "-qm", "Add ignored fixture input rule")
        ignored = self.repo / "ignored-inputs"
        ignored.mkdir()
        (ignored / "dependency.dat").write_text("not copied to worker snapshot\n")
        ignored_packet = self.base / "ignored inputs.json"
        ignored_output = self.prepare_packet(
            self.request(workspace="worktree", mode="report-only"), ignored_packet)
        binding = json.loads(ignored_packet.read_text())
        self.assertEqual(ignored_output["packet"]["ignored_dependencies_omitted"],
                         binding["workspace"]["ignored_dependencies_omitted"])
        self.assertTrue(ignored_output["packet"]["ignored_dependencies_omitted"])
        ignored_started, ignored_result = self.run_generated_command(ignored_output["commands"]["worker-start"])
        self.assertEqual((ignored_started.returncode, ignored_result["status"]), (0, "WORKER_CONTEXT_READY"), ignored_result)
        ignored_action = ignored_result["action_packet"]
        self.assertEqual(ignored_action["ignored_dependencies_omitted"],
                         ignored_output["packet"]["ignored_dependencies_omitted"])
        self.assertTrue(any("omitted from the helper worktree snapshot" in item
                            for item in ignored_action["instructions"]))

    def test_current_edit_is_read_only_at_prepare_and_parent_verifies_scope(self) -> None:
        before = {str(path.relative_to(self.repo)): path.read_bytes() for path in self.repo.rglob("*") if path.is_file()}
        output = self.prepare(self.request())
        after = {str(path.relative_to(self.repo)): path.read_bytes() for path in self.repo.rglob("*") if path.is_file()}
        self.assertEqual(after, before)
        binding = output["binding"]
        self.assertEqual(binding["workspace"]["route"], "current")
        self.assertNotIn("receipt", binding["workspace"])
        self.assertEqual(output["launch"]["cwd"], str(self.repo))
        self.assertIn("No commit — edit the current workspace in place", output["launch"]["prompt"])
        self.assertEqual(output["launch"]["prompt"].count("Binding JSON"), 1)
        self.assertIn("Do not commit, reset, stash", output["launch"]["prompt"])
        self.assertNotIn("SUCCEEDED", output["status"])

        started, start_result = self.bind_command("worker-start", binding)
        self.assertEqual((started.returncode, start_result["status"]), (0, "WORKER_CONTEXT_READY"))
        (self.repo / "src" / "app.py").write_text("VALUE = 2\n")
        finished, finish_result = self.bind_command("worker-finish", binding)
        self.assertEqual((finished.returncode, finish_result["status"]), (0, "READY_FOR_PARENT_ACCEPTANCE"))
        self.assertFalse(finish_result["native_lifecycle_verified"])
        parent_check, parent_result = self.bind_command("verify-return", binding, cwd=self.other)
        self.assertEqual((parent_check.returncode, parent_result["status"]), (0, "READY_FOR_PARENT_ACCEPTANCE"))
        self.assertEqual(parent_result["semantic_acceptance"], "pending")
        self.assertEqual(parent_result["workspace_evidence"]["changed_paths"], ["src/app.py"])

    def test_emitted_assignment_preserves_route_specific_delegation_rules(self) -> None:
        for route in ("current", "worktree"):
            for mode in ("edit", "report-only"):
                with self.subTest(route=route, mode=mode):
                    prompt = self.prepare(self.request(workspace=route, mode=mode))["launch"]["prompt"]
                    if (route, mode) == ("current", "edit"):
                        self.assertIn("do not delegate to further agents", prompt)
                        self.assertNotIn("Any native delegates", prompt)
                    else:
                        self.assertIn("workspace, scope and handoff constraints", prompt)
                        self.assertIn("Collect their terminal results before finishing or returning", prompt)
                    if mode == "report-only":
                        self.assertIn("remain report-only and make no filesystem changes", prompt)

    def test_current_report_only_and_non_git_warning(self) -> None:
        output = self.prepare(self.request(mode="report-only"))
        binding = output["binding"]
        self.assertEqual(binding["task"]["write_set"], [])
        start, start_result = self.bind_command("worker-start", binding)
        finish, finish_result = self.bind_command("worker-finish", binding)
        self.assertEqual((start.returncode, start_result["status"]), (0, "WORKER_CONTEXT_READY"))
        self.assertEqual((finish.returncode, finish_result["status"]), (0, "READY_FOR_PARENT_ACCEPTANCE"))

        plain = self.base / "plain"
        plain.mkdir()
        request = self.request(mode="report-only", source=str(plain))
        no_git = self.prepare(request)
        warning = no_git["binding"]["workspace"].get("no_drift_warning")
        self.assertIn("cannot be fingerprinted", warning)
        start, state = self.bind_command("worker-start", no_git["binding"], cwd=plain)
        finish, result = self.bind_command("worker-finish", no_git["binding"], cwd=plain)
        self.assertEqual((start.returncode, state["status"]), (0, "WORKER_CONTEXT_READY"))
        self.assertEqual(result["workspace_evidence"]["status"], "no-drift-check-available")
        self.assertEqual(finish.returncode, 0)

    def test_write_set_rejects_globs_and_accepts_slash_marked_directory_prefixes(self) -> None:
        glob_request = self.request(write_set=["src/*.py"])
        result, output = self.run_cli("prepare", "--skill-card", str(SKILL / "SKILL.md"), "--request", "-",
                                      packet=glob_request)
        self.assert_error(result, output, "unsupported_write_pattern")

        prepared = self.prepare(self.request(write_set=["src/"]))
        binding = prepared["binding"]
        self.assertEqual(binding["task"]["write_set"], ["src/"])
        (self.repo / "src" / "app.py").write_text("VALUE = 3\n")
        finish, output = self.bind_command("worker-finish", binding)
        self.assertEqual((finish.returncode, output["status"]), (0, "READY_FOR_PARENT_ACCEPTANCE"))

    def test_worktree_preserves_dirty_source_and_returns_only_worker_patch(self) -> None:
        (self.repo / "src" / "app.py").write_text("VALUE = 10\n")
        (self.repo / "local.txt").write_text("keep me\n")
        (self.repo / ".git" / "info" / "exclude").write_text("/.gitignore\n/.claspignore\n")
        (self.repo / ".gitignore").write_text("ignored/\n*.log\ncredentials.private\n")
        (self.repo / ".claspignore").write_text("# local clasp rules\n")
        (self.repo / "ignored" / "pkg").mkdir(parents=True)
        (self.repo / "ignored" / "pkg" / "index.js").write_text("module.exports = 1\n")
        (self.repo / "debug.log").write_text("ignored output\n")
        (self.repo / "credentials.private").write_text("secret\n")
        output = self.prepare(self.request(workspace="worktree", delivery_mode="patch", write_set=["src/app.py"]))
        binding = output["binding"]
        worktree = Path(output["launch"]["cwd"])
        self.assertEqual(binding["task"]["delivery_mode"], "patch")
        self.assertIn("Patch — return these changes without committing", output["launch"]["prompt"])
        self.assertTrue(Path(binding["workspace"]["receipt"]).is_file())
        self.assertEqual(binding["workspace"]["ignored_dependencies_omitted"], ["credentials.private", "debug.log", "ignored/"])
        self.assertIn("debug.log", output["launch"]["prompt"])
        self.assertTrue(any("ignored untracked inputs" in item.lower() for item in output["limitations"]))
        self.assertEqual((self.repo / "src" / "app.py").read_text(), "VALUE = 10\n")
        self.assertEqual((self.repo / "local.txt").read_text(), "keep me\n")
        self.assertEqual((worktree / "src" / "app.py").read_text(), "VALUE = 10\n")
        self.assertEqual((worktree / ".gitignore").read_bytes(), (self.repo / ".gitignore").read_bytes())
        self.assertEqual((worktree / ".claspignore").read_bytes(), (self.repo / ".claspignore").read_bytes())
        self.assertFalse((worktree / "ignored").exists())
        self.assertFalse((worktree / "debug.log").exists())
        self.assertFalse((worktree / "credentials.private").exists())

        started, start_result = self.bind_command("worker-start", binding, cwd=worktree)
        self.assertEqual((started.returncode, start_result["status"]), (0, "WORKER_CONTEXT_READY"))
        (worktree / "src" / "app.py").write_text("VALUE = 11\n")
        finished, finish_result = self.bind_command("worker-finish", binding, cwd=worktree)
        self.assertEqual((finished.returncode, finish_result["status"]), (0, "READY_FOR_PARENT_ACCEPTANCE"))
        inspection = finish_result["workspace_evidence"]["inspection"]
        self.assertEqual(inspection["contribution_paths"], ["src/app.py"])
        self.assertTrue(Path(inspection["evidence"]["contribution_patch"]).is_file())
        self.assertTrue(worktree.is_dir())
        verified, verify_result = self.bind_command("verify-return", binding, cwd=self.other)
        self.assertEqual((verified.returncode, verify_result["status"]), (0, "READY_FOR_PARENT_ACCEPTANCE"))
        self.assertEqual((self.repo / "src" / "app.py").read_text(), "VALUE = 10\n")

    def test_worktree_report_only_and_wrong_worktree_cwd(self) -> None:
        output = self.prepare(self.request(workspace="worktree", mode="report-only"))
        binding = output["binding"]
        result, state = self.bind_command("worker-start", binding, cwd=self.other)
        self.assert_error(result, state, "workspace_helper_rejected")
        start, started = self.bind_command("worker-start", binding, cwd=Path(output["launch"]["cwd"]))
        finish, finished = self.bind_command("worker-finish", binding, cwd=Path(output["launch"]["cwd"]))
        verify, verified = self.bind_command("verify-return", binding, cwd=self.other)
        self.assertEqual((start.returncode, started["status"]), (0, "WORKER_CONTEXT_READY"))
        self.assertEqual((finish.returncode, finished["status"]), (0, "READY_FOR_PARENT_ACCEPTANCE"))
        self.assertEqual((verify.returncode, verified["status"]), (0, "READY_FOR_PARENT_ACCEPTANCE"))

    def test_ephemeral_worktree_returns_only_scoped_findings_audit(self) -> None:
        (self.repo / "src" / "app.py").write_text("inherited parent input\n")
        output = self.prepare(self.request(workspace="worktree", mode="ephemeral"))
        binding = output["binding"]
        worktree = Path(output["launch"]["cwd"])
        self.assertEqual(binding["task"]["delivery_mode"], None)
        self.assertEqual(binding["task"]["write_set"], ["src/app.py"])
        self.assertIn("No commit — findings only", output["launch"]["prompt"])
        self.assertIn("Do not commit or create a patch", output["launch"]["prompt"])

        started, start_result = self.bind_command("worker-start", binding, cwd=worktree)
        self.assertEqual((started.returncode, start_result["status"]), (0, "WORKER_CONTEXT_READY"))
        (worktree / "src" / "app.py").write_text("scratch finding\n")
        finished, finish_result = self.bind_command("worker-finish", binding, cwd=worktree)
        self.assertEqual((finished.returncode, finish_result["status"]), (0, "READY_FOR_PARENT_ACCEPTANCE"))
        self.assertEqual(set(finish_result["workspace_evidence"]), {"ephemeral_audit"})
        audit = finish_result["workspace_evidence"]["ephemeral_audit"]
        self.assertEqual(audit["status"], "ephemeral-audit")
        self.assertTrue(audit["findings_only"])
        self.assertEqual(audit["changed_paths"], ["src/app.py"])
        self.assertEqual(audit["actual_cwd"], str(worktree))
        self.assertTrue(audit["scratch_retained"])
        for forbidden in ("inspection", "delivery", "contribution_patch", "commits", "commit_base"):
            self.assertNotIn(forbidden, audit)

        verified, verify_result = self.bind_command("verify-return", binding, cwd=self.other)
        self.assertEqual((verified.returncode, verify_result["status"]), (0, "READY_FOR_PARENT_ACCEPTANCE"))
        self.assertEqual(verify_result["workspace_evidence"]["ephemeral_audit"]["changed_paths"], ["src/app.py"])
        self.assertNotIn("integration_strategy", verify_result)
        self.assertTrue(worktree.is_dir())
        self.assertTrue(Path(binding["workspace"]["receipt"]).is_file())
        self.assertEqual((self.repo / "src" / "app.py").read_text(), "inherited parent input\n")

    def test_ephemeral_rejects_commit_and_out_of_scope_scratch(self) -> None:
        output = self.prepare(self.request(workspace="worktree", mode="ephemeral"))
        binding = output["binding"]
        worktree = Path(output["launch"]["cwd"])
        started, start_result = self.bind_command("worker-start", binding, cwd=worktree)
        self.assertEqual((started.returncode, start_result["status"]), (0, "WORKER_CONTEXT_READY"))
        (worktree / "src" / "app.py").write_text("committed scratch\n")
        git(worktree, "add", "--", "src/app.py")
        git(worktree, "commit", "-qm", "must not be returned")
        committed, commit_error = self.bind_command("worker-finish", binding, cwd=worktree)
        self.assert_error(committed, commit_error, "ephemeral_git_state_changed")
        self.assertTrue(worktree.is_dir())
        self.assertEqual((self.repo / "src" / "app.py").read_text(), "VALUE = 1\n")

        outside = self.prepare(self.request(workspace="worktree", mode="ephemeral"))
        outside_binding = outside["binding"]
        outside_worktree = Path(outside["launch"]["cwd"])
        (outside_worktree / "README.md").write_text("out of scope scratch\n")
        drift, drift_error = self.bind_command("worker-finish", outside_binding, cwd=outside_worktree)
        self.assert_error(drift, drift_error, "scope_drift")
        self.assertEqual(drift_error["error"]["observed"], ["README.md"])
        self.assertTrue(outside_worktree.is_dir())

    def test_worktree_edit_defaults_to_commits_and_returns_exact_contribution_range(self) -> None:
        output = self.prepare(self.request(workspace="worktree"))
        binding = output["binding"]
        worktree = Path(output["launch"]["cwd"])
        snapshot = binding["workspace"]["snapshot"]
        self.assertEqual(binding["task"]["delivery_mode"], "commits")
        self.assertEqual(binding["workspace"]["commit_base"], snapshot["commit"])
        self.assertFalse(snapshot["source_dirty"])
        self.assertIn("Git commit — return these changes", output["launch"]["prompt"])
        self.assertIn("git -C " + shlex.quote(str(worktree)) + " add -- <exact-path>", output["launch"]["prompt"])
        self.assertIn("git -C " + shlex.quote(str(worktree)) + " commit -m", output["launch"]["prompt"])

        started, start_result = self.bind_command("worker-start", binding, cwd=worktree)
        self.assertEqual((started.returncode, start_result["status"]), (0, "WORKER_CONTEXT_READY"))
        (worktree / "src" / "app.py").write_text("VALUE = 12\n")
        git(worktree, "add", "--", "src/app.py")
        git(worktree, "commit", "-qm", "Implement fixture value update")
        contribution = git_output(worktree, "rev-parse", "HEAD")
        result, finished = self.bind_command("worker-finish", binding, cwd=worktree)
        self.assertEqual((result.returncode, finished["status"]), (0, "READY_FOR_PARENT_ACCEPTANCE"), finished)
        inspection = finished["workspace_evidence"]["inspection"]
        delivery = inspection["delivery"]
        self.assertEqual(delivery["mode"], "commits")
        self.assertEqual(delivery["base"], binding["workspace"]["commit_base"])
        self.assertEqual(delivery["commits"], [contribution])
        self.assertEqual(delivery["commit_paths"], ["src/app.py"])
        self.assertEqual(delivery["residual_paths"], [])
        self.assertNotIn("contribution_patch", delivery)
        self.assertEqual(inspection["contribution_paths"], ["src/app.py"])
        verified, verify_result = self.bind_command("verify-return", binding, cwd=self.other)
        self.assertEqual((verified.returncode, verify_result["status"]), (0, "READY_FOR_PARENT_ACCEPTANCE"))
        self.assertEqual(verify_result["integration_strategy"], {
            "strategy": "eligible cherry-pick", "source_dirty": False,
            "commit_base": binding["workspace"]["commit_base"], "commits": [contribution],
            "parent_target_revalidation_required": True,
        })
        self.assertTrue(worktree.is_dir())
        self.assertTrue(Path(binding["workspace"]["receipt"]).is_file())
        self.assertEqual((self.repo / "src" / "app.py").read_text(), "VALUE = 1\n")

    def test_dirty_parent_commit_delivery_preserves_caller_head_index_and_layers(self) -> None:
        (self.repo / "README.md").write_text("staged parent edit\n")
        git(self.repo, "add", "--", "README.md")
        (self.repo / "src" / "app.py").write_text("unstaged parent edit\n")
        (self.repo / "local.txt").write_text("untracked parent input\n")
        parent_head = git_output(self.repo, "rev-parse", "HEAD")
        parent_branch = git_output(self.repo, "branch", "--show-current")
        staged = git_output(self.repo, "diff", "--cached", "--binary")
        unstaged = git_output(self.repo, "diff", "--binary")
        index_bytes = (self.repo / ".git" / "index").read_bytes()

        output = self.prepare(self.request(workspace="worktree"))
        binding = output["binding"]
        worktree = Path(output["launch"]["cwd"])
        snapshot = binding["workspace"]["snapshot"]
        self.assertTrue(snapshot["source_dirty"])
        started, start_result = self.bind_command("worker-start", binding, cwd=worktree)
        self.assertEqual((started.returncode, start_result["status"]), (0, "WORKER_CONTEXT_READY"))
        (worktree / "src" / "app.py").write_text("VALUE = 13\n")
        git(worktree, "add", "--", "src/app.py")
        git(worktree, "commit", "-qm", "Implement fixture value update")
        contribution = git_output(worktree, "rev-parse", "HEAD")
        finished, finish_result = self.bind_command("worker-finish", binding, cwd=worktree)
        self.assertEqual((finished.returncode, finish_result["status"]), (0, "READY_FOR_PARENT_ACCEPTANCE"), finish_result)
        delivery = finish_result["workspace_evidence"]["inspection"]["delivery"]
        self.assertEqual(delivery["commits"], [contribution])
        self.assertEqual(delivery["residual_paths"], [])
        patch = Path(delivery["contribution_patch"])
        self.assertTrue(patch.is_absolute())
        self.assertTrue(patch.is_file())
        verified, verify_result = self.bind_command("verify-return", binding, cwd=self.other)
        self.assertEqual((verified.returncode, verify_result["status"]), (0, "READY_FOR_PARENT_ACCEPTANCE"))
        self.assertEqual(verify_result["integration_strategy"], {
            "strategy": "preserve-parent patch from commits", "source_dirty": True,
            "commit_base": binding["workspace"]["commit_base"], "commits": [contribution],
            "parent_target_revalidation_required": True,
        })
        self.assertEqual(git_output(self.repo, "rev-parse", "HEAD"), parent_head)
        self.assertEqual(git_output(self.repo, "branch", "--show-current"), parent_branch)
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), index_bytes)
        self.assertEqual(git_output(self.repo, "diff", "--cached", "--binary"), staged)
        self.assertEqual(git_output(self.repo, "diff", "--binary"), unstaged)
        self.assertEqual((self.repo / "local.txt").read_text(), "untracked parent input\n")

    def test_parent_verify_rejects_source_index_drift_after_worker_finish(self) -> None:
        output = self.prepare(self.request(workspace="worktree"))
        binding = output["binding"]
        worktree = Path(output["launch"]["cwd"])
        (worktree / "src" / "app.py").write_text("worker contribution\n")
        git(worktree, "add", "--", "src/app.py")
        git(worktree, "commit", "-qm", "Implement fixture value update")
        finished, finish_result = self.bind_command("worker-finish", binding, cwd=worktree)
        self.assertEqual((finished.returncode, finish_result["status"]), (0, "READY_FOR_PARENT_ACCEPTANCE"))

        (self.repo / "README.md").write_text("source checkout changed after prepare\n")
        git(self.repo, "add", "--", "README.md")
        verified, verify_error = self.bind_command("verify-return", binding, cwd=self.other)
        self.assert_error(verified, verify_error, "source_capture_drift")
        self.assertIn("index_bytes_sha256", verify_error["error"]["observed"]["changed_fields"])
        self.assertTrue(worktree.is_dir())
        self.assertTrue(Path(binding["workspace"]["receipt"]).is_file())
        self.assertEqual((self.repo / "README.md").read_text(), "source checkout changed after prepare\n")

    def test_current_dirty_overlap_wrong_cwd_and_scope_drift(self) -> None:
        (self.repo / "src" / "app.py").write_text("already dirty\n")
        result, output = self.run_cli("prepare", "--skill-card", str(SKILL / "SKILL.md"), "--request", "-",
                                      packet=self.request())
        self.assert_error(result, output, "dirty_write_set_overlap")
        self.assertEqual(output["error"]["observed"], ["src/app.py"])
        self.assertFalse(self.store.exists())

        git(self.repo, "checkout", "--", "src/app.py")
        prepared = self.prepare(self.request())
        binding = prepared["binding"]
        wrong, wrong_output = self.bind_command("worker-start", binding, cwd=self.other)
        self.assert_error(wrong, wrong_output, "wrong_worker_cwd")
        (self.repo / "README.md").write_text("out of scope\n")
        finish, drift = self.bind_command("worker-finish", binding)
        self.assert_error(finish, drift, "scope_drift")
        self.assertIn("README.md", drift["error"]["observed"]["outside_write_set"])

    def test_validation_and_cli_failures_are_structured(self) -> None:
        invalid = [
            ({**self.request(), "source": "relative"}, "invalid_source"),
            ({**self.request(), "source": str(self.base) + "/bad\x00path"}, "invalid_source"),
            ({**self.request(), "write_set": ["/tmp/outside"]}, "invalid_write_set"),
            ({**self.request(), "write_set": ["src/bad\x00path"]}, "invalid_write_set"),
            (self.request(workspace="worktree", store=str(self.base) + "/bad\x00store"), "invalid_store"),
            ({**self.request(), "workspace": "consumer-owned"}, "unsupported_case"),
            ({**self.request(), "mode": "commits"}, "unsupported_case"),
            ({**self.request(), "write_set": ["src/*.py"]}, "unsupported_write_pattern"),
            ({**self.request(mode="report-only"), "write_set": ["README.md"]}, "report_only_write_set"),
            (self.request(workspace="worktree", mode="ephemeral", write_set=[]), "missing_write_set"),
            (self.request(mode="ephemeral"), "ephemeral_requires_worktree"),
            (self.request(delivery_mode="patch"), "ambiguous_delivery_mode"),
            (self.request(workspace="worktree", mode="report-only", delivery_mode="patch"), "ambiguous_delivery_mode"),
            (self.request(workspace="worktree", delivery_mode="bogus"), "invalid_delivery_mode"),
            (self.request(workspace="worktree", mode="ephemeral", delivery_mode="patch"), "ambiguous_delivery_mode"),
            ({**self.request(), "surprise": True}, "unknown_request_field"),
        ]
        for request, code in invalid:
            with self.subTest(code=code, request=request):
                result, output = self.run_cli("prepare", "--skill-card", str(SKILL / "SKILL.md"), "--request", "-",
                                              packet=request)
                self.assert_error(result, output, code)
        invalid_json, invalid_output = self.run_cli("prepare", "--skill-card", str(SKILL / "SKILL.md"),
                                                    "--request", "-", raw="{")
        self.assert_error(invalid_json, invalid_output, "invalid_request")
        bad_args, bad_output = self.run_cli("prepare", packet=self.request())
        self.assert_error(bad_args, bad_output, "invalid_cli")

    def test_binding_and_package_tampering_are_rejected(self) -> None:
        binding = self.prepare(self.request())["binding"]
        altered = json.loads(json.dumps(binding))
        altered["task"]["objective"] = "different task"
        result, output = self.bind_command("worker-start", altered)
        self.assert_error(result, output, "binding_digest_mismatch")

        altered = json.loads(json.dumps(binding))
        altered["package"]["task_script_sha256"] = "0" * 64
        altered["binding_sha256"] = "0" * 64
        altered["binding_sha256"] = hashlib.sha256(
            json.dumps({key: value for key, value in altered.items() if key != "binding_sha256"},
                       sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest()
        result, output = self.bind_command("worker-start", altered)
        self.assert_error(result, output, "package_identity_mismatch")

    def test_prompt_command_runs_from_package_path_with_spaces_and_apostrophe(self) -> None:
        package = self.base / "selected package's copy"
        scripts = package / "scripts"
        scripts.mkdir(parents=True)
        shutil.copy2(SKILL / "SKILL.md", package / "SKILL.md")
        shutil.copy2(SKILL / "scripts" / "ask_agent_workspace.py", scripts / "ask_agent_workspace.py")
        copied_script = scripts / "ask_agent_task.py"
        shutil.copy2(SCRIPT, copied_script)
        completed = subprocess.run(
            [sys.executable, "-B", str(copied_script), "prepare", "--skill-card", str(package / "SKILL.md"),
             "--request", "-"],
            cwd=self.repo, env=self.env, input=json.dumps(self.request(mode="report-only")),
            capture_output=True, text=True, timeout=90,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        output = json.loads(completed.stdout)
        command = re.search(r"Before any task operation, run `([^`]+)`", output["launch"]["prompt"])
        self.assertIsNotNone(command)
        argv = shlex.split(command.group(1))
        self.assertEqual(argv[0], "python3")
        self.assertEqual(Path(argv[1]), copied_script)
        started = subprocess.run(
            argv, cwd=Path(output["launch"]["cwd"]), env=self.env,
            input=json.dumps(output["binding"]), capture_output=True, text=True, timeout=90,
        )
        self.assertEqual(started.returncode, 0, started.stderr)
        self.assertEqual(json.loads(started.stdout)["status"], "WORKER_CONTEXT_READY")


if __name__ == "__main__":
    unittest.main(verbosity=2)
