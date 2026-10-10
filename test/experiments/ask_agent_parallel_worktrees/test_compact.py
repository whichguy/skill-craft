"""Compact-treatment contract tests using isolated local Git fixtures."""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import quote

import briefs
import fixture
import native_trace
import operations
import test_native_trace as legacy_native_fixture
import worker_phase


class CompactHarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ask-agent-compact-")
        self.run = (Path(self.temp.name) / "run").resolve()
        self.manifest = fixture.prepare_fixture(
            self.run,
            3,
            "parallel",
            source_skill=fixture.default_skill_root(),
            seed_compact_ignore_controls=True,
        )
        self.setup = None

    def tearDown(self):
        self.temp.cleanup()

    def _prepare(self):
        self.setup = operations.prepare_batch(self.run, compact=True)
        return self.setup

    def _worker(self, worker_id):
        return next(item for item in self.setup["workers"] if item["worker_id"] == str(worker_id))

    def _binding_path(self, worker_id):
        return Path(self._worker(worker_id)["compact_binding_path"])

    def _phase(self, worker_id, phase):
        worker = self._worker(worker_id)
        binding_path = self._binding_path(worker_id)
        completed = subprocess.run(
            [sys.executable, "-B", str(Path(worker_phase.__file__).resolve()),
             "--run", str(self.run), "--worker", str(worker_id), "--phase", phase,
             "--compact-binding", str(binding_path)],
            cwd=worker["worktree"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def _finish_all_workers(self):
        for task in self.manifest["task_assignments"]:
            worker_id = task["worker_id"]
            root = Path(self._worker(worker_id)["worktree"])
            self._phase(worker_id, "start")
            module = root / task["path"]
            worker_number = int(worker_id)
            module.write_text(
                "def transform(x):\n"
                f"    return ({worker_number} + 1) * x + {worker_number} * {worker_number}\n",
                encoding="utf-8",
            )
            result = self._phase(worker_id, "finish")
            self.assertEqual(result["status"], "PASSED")
            self.assertEqual(result["checks"]["production_worker_finish_passed"], True)

    def test_compact_pipeline_inherits_controls_returns_only_owned_patches_and_preserves_parent(self):
        self._prepare()
        parent = Path(self.manifest["paths"]["caller"])
        expected_gitignore = (parent / ".gitignore").read_text(encoding="utf-8")
        for worker in self.setup["workers"]:
            root = Path(worker["worktree"])
            self.assertEqual((root / ".gitignore").read_text(encoding="utf-8"), expected_gitignore)
            self.assertEqual((root / ".claspignore").read_text(encoding="utf-8"), "dist/\n")
            self.assertFalse((root / "unrelated-ignored-input.txt").exists())

        dispatch = briefs.build_compact_briefs(self.run)
        self.assertEqual(dispatch["status"], "PREPARED")
        emitted = briefs.emit_compact_worker(self.run, "1")
        emitted_size = len(json.dumps(emitted, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        self.assertLess(emitted_size, 20_000)

        self._finish_all_workers()
        worker_ids = [task["worker_id"] for task in self.manifest["task_assignments"]]
        for worker_id in worker_ids:
            returned = operations.verify_compact_return(self.run, worker_id)
            self.assertEqual(returned["status"], "PASSED")
            self.assertEqual(returned["contribution_paths"], [self._worker(worker_id)["path"]])

        before_integration = fixture.capture_repo_state(parent)
        result = operations.integrate_batch(self.run, worker_ids)
        self.assertEqual(result["status"], "INTEGRATED")
        self.assertEqual(result["applied_worker_ids"], worker_ids)
        self.assertEqual(
            {patch["path"] for patch in result["patches"]},
            {task["path"] for task in self.manifest["task_assignments"]},
        )
        after_integration = fixture.capture_repo_state(parent)
        for field in (
            "head", "index_entries", "index_entries_sha256", "index_tree",
            "index_raw_sha256", "cached_diff_sha256", "unstaged_dirty_diffs",
        ):
            self.assertEqual(after_integration[field], before_integration[field], field)
        self.assertEqual((parent / ".gitignore").read_text(encoding="utf-8"), expected_gitignore)
        self.assertEqual((parent / ".claspignore").read_text(encoding="utf-8"), "dist/\n")
        self.assertEqual((parent / "unrelated-ignored-input.txt").read_text(encoding="utf-8"),
                         "omit from worker snapshot\n")

    def test_compact_assignment_keeps_wrappers_and_required_task_test_separate(self):
        self._prepare()
        briefs.build_compact_briefs(self.run)
        assignment = briefs.emit_compact_worker(self.run, "2")
        prompt = assignment["native_arguments"]["prompt"]

        self.assertIn(
            "Run the start wrapper, required task test, and finish wrapper in separate terminal tool invocations.",
            prompt,
        )
        self.assertIn("Do not combine a wrapper with a test, file operation, echo, diagnostics, or another command",
                      prompt)
        self.assertIn("Run the required task test separately before finish", prompt)
        self.assertIn("the finish wrapper runs its fixture checks itself", prompt)
        self.assertIn("Do not add shell commands or debug output to either wrapper call.", prompt)

    def test_concurrent_compact_worker_starts_do_not_contend_on_caller_index(self):
        self._prepare()
        caller = Path(self.manifest["paths"]["caller"])
        before = fixture.capture_repo_state(caller)
        worker_ids = [task["worker_id"] for task in self.manifest["task_assignments"]]

        with ThreadPoolExecutor(max_workers=len(worker_ids)) as pool:
            results = list(pool.map(self._phase, worker_ids, ["start"] * len(worker_ids)))

        self.assertEqual([result["status"] for result in results], ["PASSED"] * len(worker_ids))
        after = fixture.capture_repo_state(caller)
        for field in (
            "head", "index_entries", "index_tree", "index_raw_sha256",
            "cached_diff_sha256", "unstaged_dirty_diffs", "status",
        ):
            self.assertEqual(after[field], before[field], field)
        index_path = Path(before["index_path"])
        self.assertFalse(index_path.with_name(index_path.name + ".lock").exists())

    def test_integration_requires_every_compact_return_before_applying(self):
        self._prepare()
        parent = Path(self.manifest["paths"]["caller"])
        before = fixture.capture_repo_state(parent)
        self._finish_all_workers()
        worker_ids = [task["worker_id"] for task in self.manifest["task_assignments"]]

        with self.assertRaisesRegex(fixture.FixtureError, "COMPACT_VERIFY_RETURN_REQUIRED"):
            operations.integrate_batch(self.run, worker_ids)

        self.assertFalse((self.run / "operator" / "integration-result.json").exists())
        self.assertFalse((self.run / "operator" / "integration-calls").exists())
        after = fixture.capture_repo_state(parent)
        self.assertEqual(after["working_tree"], before["working_tree"])
        self.assertEqual(after["index_entries"], before["index_entries"])

    def test_verify_return_rejects_replaced_task_script_before_execution(self):
        self._prepare()
        binding_path = self._binding_path("1")
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
        marker = self.run / "operator" / "foreign-task-script-ran.txt"
        sentinel = self.run / "operator" / "foreign-task-script.py"
        sentinel.write_text(
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('ran', encoding='utf-8')\n"
            "print('{}')\n",
            encoding="utf-8",
        )
        binding["package"]["task_script"] = str(sentinel.resolve())
        binding_path.chmod(0o644)
        binding_path.write_text(json.dumps(binding, indent=2) + "\n", encoding="utf-8")

        with self.assertRaisesRegex(fixture.FixtureError, "COMPACT_RETURN_BINDING_INVALID"):
            operations.verify_compact_return(self.run, "1")

        self.assertFalse(marker.exists(), "a substituted task script must be rejected before execution")


class CompactDeliveryModeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ask-agent-compact-delivery-")
        self.addCleanup(self.temp.cleanup)

    def _prepare(self, delivery_mode):
        self.run = (Path(self.temp.name) / delivery_mode).resolve()
        self.manifest = fixture.prepare_fixture(
            self.run, 3, "parallel", source_skill=fixture.default_skill_root(),
            seed_compact_ignore_controls=True, delivery_mode=delivery_mode,
        )
        self.setup = operations.prepare_batch(self.run, compact=True)
        briefs.build_compact_briefs(self.run)
        return self.setup

    def _worker(self, worker_id):
        return next(row for row in self.setup["workers"] if row["worker_id"] == str(worker_id))

    def _phase(self, worker_id, phase):
        worker = self._worker(worker_id)
        completed = subprocess.run(
            [sys.executable, "-B", str(Path(worker_phase.__file__).resolve()),
             "--run", str(self.run), "--worker", str(worker_id), "--phase", phase,
             "--compact-binding", worker["compact_binding_path"]],
            cwd=worker["worktree"], capture_output=True, text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def _edit_worker(self, task, *, commits):
        worker_id = task["worker_id"]
        worker = self._worker(worker_id)
        root = Path(worker["worktree"])
        assignment = briefs.emit_compact_worker(self.run, worker_id)["native_arguments"]["prompt"]
        self._phase(worker_id, "start")
        module = root / task["path"]
        module.write_text(
            "def transform(x):\n"
            f"    return ({int(worker_id)} + 1) * x + {int(worker_id)} * {int(worker_id)}\n",
            encoding="utf-8",
        )
        if commits:
            self.assertIn(f"git -C {worker['worktree']} add -- {task['path']}", assignment)
            self.assertIn(f"git -C {worker['worktree']} commit -m 'Ask Agent fixture worker {worker_id}'", assignment)
            self.assertIn(f"git -C {worker['worktree']} rev-parse HEAD", assignment)
            fixture.git(root, "add", "--", task["path"])
            fixture.git(root, "commit", "-m", f"Ask Agent fixture worker {worker_id}")
            commit = fixture.git(root, "rev-parse", "HEAD")
            self.assertRegex(commit, r"^[0-9a-f]{40,64}$")
        finish = self._phase(worker_id, "finish")
        self.assertTrue(finish["checks"]["production_worker_finish_passed"])
        if commits:
            self.assertEqual(finish["contribution_commits"], [commit])
        return finish

    def test_commit_delivery_uses_default_binding_and_integrates_only_worker_commits(self):
        self._prepare("commits")
        parent = Path(self.manifest["paths"]["caller"])
        before = fixture.capture_repo_state(parent)
        for task in self.manifest["task_assignments"]:
            request = json.loads((self.run / "operator" / "compact-prepare" /
                                  f"worker-{task['worker_id']}.request.json").read_text())
            binding_path = Path(self._worker(task["worker_id"])["compact_binding_path"])
            binding = json.loads(binding_path.read_text())
            self.assertNotIn("delivery_mode", request, "worktree edit must exercise the production default")
            self.assertEqual(binding["task"]["delivery_mode"], "commits")
            self.assertEqual(binding["workspace"]["commit_base"], self._worker(task["worker_id"])["commit_base"])
            self._edit_worker(task, commits=True)
        worker_ids = [task["worker_id"] for task in self.manifest["task_assignments"]]
        for worker_id in worker_ids:
            self.assertEqual(operations.verify_compact_return(self.run, worker_id)["status"], "PASSED")
        result = operations.integrate_batch(self.run, worker_ids, delivery_mode="commits")
        summary = operations.integration_summary(self.run, result)
        self.assertEqual(result["status"], "INTEGRATED")
        self.assertEqual(summary["delivery_mode"], "commits")
        self.assertEqual(summary["worker_ids"], worker_ids)
        self.assertEqual([row["worker_id"] for row in summary["commit_records"]], worker_ids)
        self.assertEqual(result["fixture_verification"]["passed"], True)
        after = fixture.capture_repo_state(parent)
        for field in ("head", "index_entries", "index_tree", "cached_diff_sha256", "unstaged_dirty_diffs"):
            self.assertEqual(after[field], before[field], field)

    def test_ephemeral_mode_returns_findings_without_importing_or_changing_caller(self):
        self._prepare("ephemeral")
        parent = Path(self.manifest["paths"]["caller"])
        before = fixture.capture_repo_state(parent)
        for task in self.manifest["task_assignments"]:
            binding = json.loads(Path(self._worker(task["worker_id"])["compact_binding_path"]).read_text())
            self.assertEqual(binding["task"]["mode"], "ephemeral")
            self.assertIsNone(binding["task"].get("delivery_mode"))
            self._edit_worker(task, commits=False)
        worker_ids = [task["worker_id"] for task in self.manifest["task_assignments"]]
        for worker_id in worker_ids:
            self.assertEqual(operations.verify_compact_return(self.run, worker_id)["status"], "PASSED")
        result = operations.finish_ephemeral(self.run, worker_ids)
        self.assertEqual(result["status"], "NO_INTEGRATION")
        self.assertEqual(set(result), {
            "schema", "status", "delivery_mode", "worker_ids", "result_path", "caller_snapshot_sha256",
        })
        self.assertEqual(result["delivery_mode"], "ephemeral")
        self.assertEqual(result["worker_ids"], worker_ids)
        retained = json.loads((self.run / "operator" / "integration-result.json").read_text())
        self.assertEqual(retained["caller_snapshot_sha256"], operations._canonical_sha256(self.manifest["caller_snapshot"]))
        self.assertNotIn("applied_worker_ids", retained)
        self.assertEqual(fixture.verify_fixture(self.run)["passed"], True)
        after = fixture.capture_repo_state(parent)
        for field in ("head", "index_entries", "index_tree", "working_tree", "status"):
            self.assertEqual(after[field], before[field], field)


class CompactNativeTraceTests(unittest.TestCase):
    def _compact_synthetic_case(self, case):
        run = case.run.resolve()
        operator = run / "operator"
        manifest = case.manifest
        manifest["delivery_mode"] = "patch"
        case._write_json(run / "manifest.json", manifest)
        collection_calls = [
            row["params"]["update"] for row in case.updates
            if row.get("params", {}).get("update", {}).get("title") == "get_command_or_subagent_output"
            and row["params"]["update"].get("sessionUpdate") == "tool_call"
        ]
        self.assertEqual(len(collection_calls), 1)
        self.assertEqual(collection_calls[0]["rawInput"].get("task_ids"), case.child_ids)
        collection_id = collection_calls[0]["toolCallId"]
        collection_terminal = [
            row["params"]["update"] for row in case.updates
            if row.get("params", {}).get("update", {}).get("toolCallId") == collection_id
            and row["params"]["update"].get("sessionUpdate") == "tool_call_update"
        ]
        self.assertEqual(len(collection_terminal), 1)
        raw_output = collection_terminal[0]["rawOutput"]
        self.assertEqual(raw_output.get("type"), "TaskOutput")
        result_rows = raw_output.get("MultiResult", {}).get("results")
        self.assertEqual(
            result_rows,
            [{"task_id": child, "status": "completed", "exit_code": 0}
             for child in case.child_ids],
        )
        package_root = run / "package" / "ask-agent"
        skill_card = package_root / "SKILL.md"
        task_script = package_root / "scripts" / "ask_agent_task.py"
        task_script.parent.mkdir(parents=True, exist_ok=True)
        skill_card.write_text("---\nname: ask-agent\n---\n", encoding="utf-8")
        task_script.write_text("# compact task script synthetic source identity\n", encoding="utf-8")
        manifest["paths"]["package"] = str(package_root.resolve())
        case._write_json(run / "manifest.json", manifest)
        binding_dir = operator / "compact-bindings"
        binding_dir.mkdir()
        setup_workers = []
        entries = []
        launches = []
        child_transcripts = {}
        child_update_rows = {}
        phase_attempts = {}
        wrapper_script = operator / "worker_phase.py"
        wrapper_script.write_text("# compact worker phase synthetic source identity\n", encoding="utf-8")

        for index, task in enumerate(manifest["task_assignments"], 1):
            worker_id = str(task["worker_id"])
            cwd = case.child_roots[index - 1].resolve()
            child_id = case.child_ids[index - 1]
            binding_path = (binding_dir / f"worker-{worker_id}.json").resolve()
            binding_sha = f"synthetic-binding-sha-{worker_id}"
            receipt = str((cwd / ".experiment-local" / "receipt.json").resolve())
            binding_path.write_text("{}\n", encoding="utf-8")
            setup_workers.append({
                "worker_id": worker_id,
                "path": task["path"],
                "worktree": str(cwd),
                "receipt": receipt,
                "compact_binding_path": str(binding_path),
                "compact_binding_sha256": binding_sha,
                "package_identity": {"resolved_skill_card": str(skill_card)},
            })
            prompt_commands = {}
            for phase in ("start", "finish"):
                command = "cd " + shlex.quote(str(cwd)) + " && PYTHONDONTWRITEBYTECODE=1 " + shlex.join([
                    "python3", "-B", os.path.relpath(wrapper_script, cwd),
                    "--run", os.path.relpath(run, cwd), "--worker", worker_id,
                    "--phase", phase, "--compact-binding", str(binding_path),
                ])
                prompt_commands[phase] = command
            args = {
                "description": f"Implement only {task['path']}.",
                "prompt": (f"Implement only {task['path']}.\n"
                           f"Start wrapper: `{prompt_commands['start']}`\n"
                           f"Finish wrapper: `{prompt_commands['finish']}`\n"),
                "cwd": str(cwd),
                "background": True,
            }
            entry = {
                "worker_id": worker_id,
                "native_arguments": args,
                "binding_sha256": binding_sha,
                "prepare_result_path": str((operator / "compact-prepare" / f"worker-{worker_id}.json").resolve()),
            }
            entries.append(entry)
            launches.append({"worker_id": worker_id, "child_session_id": child_id, "cwd": str(cwd)})

            child_dir = case.session_root / quote(str(cwd), safe="") / child_id
            child_dir.mkdir(parents=True, exist_ok=True)
            child_path = child_dir / "updates.jsonl"
            child_transcripts[child_id] = {"retained": {"path": str(child_path.resolve())}}
            child_update_rows[worker_id] = []
            phase_attempts[worker_id] = {}
            for phase in ("start", "finish"):
                label = "compact-worker-start" if phase == "start" else "compact-worker-finish"
                command_name = "worker-start" if phase == "start" else "worker-finish"
                result_status = "WORKER_CONTEXT_READY" if phase == "start" else "READY_FOR_PARENT_ACCEPTANCE"
                inspection_status = "prepared" if phase == "start" else "returned"
                result = {
                    "status": result_status,
                    "binding_sha256": binding_sha,
                    "workspace_evidence": {"inspection": {
                        "status": inspection_status,
                        "worktree": str(cwd),
                        "receipt": receipt,
                        "contribution_paths": [task["path"]] if phase == "finish" else [],
                    }},
                }
                if phase == "finish":
                    result["command"] = "worker-finish"
                command_path = operator / "worker-phases" / f"worker-{worker_id}-{phase}" / "calls" / f"{label}.json"
                command_path.parent.mkdir(parents=True, exist_ok=True)
                command_record = {
                    "argv": [sys.executable, "-B", str(task_script.resolve()), command_name,
                             "--binding", str(binding_path)],
                    "cwd": str(cwd), "exit_code": 0, "status": "COMPLETED",
                    "stdout": json.dumps(result), "json": result,
                }
                case._write_json(command_path, command_record)
                attempt_path = operator / "worker-phases" / f"worker-{worker_id}-{phase}" / "attempt.json"
                attempt_path.parent.mkdir(parents=True, exist_ok=True)
                attempt = {
                    "status": "PASSED", "worker_id": worker_id, "phase": phase, "root": str(cwd),
                    "compact_binding_path": str(binding_path), "compact_binding_sha256": binding_sha,
                    "calls": [{"label": label, "evidence": str(command_path.resolve())}],
                }
                case._write_json(attempt_path, attempt)
                phase_attempts[worker_id][phase] = {"attempt": attempt_path, "command": command_path}
                tool_id = f"compact-child-{worker_id}-{phase}"
                wrapper_result = {
                    "status": "PASSED", "run_id": manifest["run_id"], "worker_id": worker_id,
                    "phase": phase, "root": str(cwd),
                    "evidence": str((operator / "worker-phases" / f"worker-{worker_id}-{phase}"
                                     / "attempt.json").resolve()),
                }
                wrapper_checks = {
                    "phase_passed": True,
                    "fixture_probe_passed": True,
                    "production_worker_start_passed" if phase == "start"
                    else "production_worker_finish_passed": True,
                }
                wrapper_checks["helper_context_verified" if phase == "start" else "worker_check_passed"] = True
                if phase == "finish":
                    wrapper_checks["returned_patch_bound"] = True
                wrapper_result["checks"] = wrapper_checks
                child_update_rows[worker_id].extend([
                    {"method": "session/update", "params": {"sessionId": child_id, "update": {
                        "sessionUpdate": "tool_call", "toolCallId": tool_id,
                        "title": "run_terminal_command", "rawInput": {"command": prompt_commands[phase]},
                    }}},
                    {"method": "session/update", "params": {"sessionId": child_id, "update": {
                        "sessionUpdate": "tool_call_update", "toolCallId": tool_id, "status": "completed",
                        "rawOutput": {"type": "Bash", "exit_code": 0,
                                      "output": json.dumps(wrapper_result), "truncated": False},
                    }}},
                ])
            child_path.write_text(
                "".join(json.dumps(row, sort_keys=True) + "\n" for row in child_update_rows[worker_id]),
                encoding="utf-8",
            )

        setup = {"status": "PREPARED", "treatment": "compact", "delivery_mode": "patch",
                 "workers": setup_workers}
        case._write_json(operator / "setup-result.json", setup)
        case._write_json(operator / "treatment.json", {
            "treatment": "compact", "version": 2, "delivery_mode": "patch",
            "verification_output": "summary-v1",
        })
        dispatch_dir = operator / "compact-dispatch"
        dispatch_dir.mkdir()
        index_rows = []
        for entry in entries:
            path = dispatch_dir / f"worker-{entry['worker_id']}.json"
            case._write_json(path, entry)
            payload = path.read_bytes()
            index_rows.append({"worker_id": entry["worker_id"], "path": str(path.resolve()),
                               "sha256": fixture.sha256_bytes(payload),
                               "binding_sha256": entry["binding_sha256"]})
        index_path = dispatch_dir / "index.json"
        case._write_json(index_path, {"schema": "ask-agent.compact-dispatch/v1",
                                      "run_id": manifest["run_id"], "assignments": index_rows,
                                      "max_emitted_bytes": 20_000})
        briefs_script = operator / "briefs.py"
        operations_script = operator / "operations.py"
        briefs_script.write_text("# compact briefs synthetic source identity\n", encoding="utf-8")
        operations_script.write_text("# compact operations synthetic source identity\n", encoding="utf-8")

        def cli_updates(tool_id, script, args, output):
            command = shlex.join(["python3", "-B", str(script.resolve()), *args])
            return [
                case._update("tool_call", {"toolCallId": tool_id, "title": "run_terminal_command",
                                             "rawInput": {"command": command}}),
                case._update("tool_call_update", {"toolCallId": tool_id, "status": "completed",
                                                    "rawOutput": {"type": "Bash", "exit_code": 0,
                                                                  "output": json.dumps(output, sort_keys=True,
                                                                                       separators=(",", ":")),
                                                                  "truncated": False}}),
            ]

        root_cli = cli_updates("compact-prepare", operations_script,
                               ["prepare-batch", "--run", str(run), "--compact"],
                               {"status": "PREPARED", "treatment": "compact"})
        root_cli += cli_updates("compact-build", briefs_script,
                                ["--run", str(run), "--compact"],
                                {"status": "PREPARED", "worker_ids": [item["worker_id"] for item in entries],
                                 "index_path": str(index_path.resolve())})
        for entry in entries:
            root_cli += cli_updates(
                f"compact-emit-{entry['worker_id']}", briefs_script,
                ["--run", str(run), "--emit-worker", entry["worker_id"]], entry,
            )
        case.updates[0:0] = root_cli
        return_rows = []
        compact_return_dir = operator / "compact-returns"
        compact_return_dir.mkdir()
        for entry in entries:
            worker_id = entry["worker_id"]
            record_path = compact_return_dir / f"worker-{worker_id}.json"
            task = manifest["task_assignments"][int(worker_id) - 1]
            binding_path = Path(next(
                item["compact_binding_path"] for item in setup_workers
                if item["worker_id"] == worker_id
            )).resolve()
            cwd = Path(next(
                item["worktree"] for item in setup_workers if item["worker_id"] == worker_id
            )).resolve()
            production_result = {
                "status": "READY_FOR_PARENT_ACCEPTANCE",
                "command": "verify-return",
                "binding_sha256": entry["binding_sha256"],
                "workspace_evidence": {"inspection": {
                    "status": "returned", "worktree": str(cwd),
                    "receipt": str(next(item["receipt"] for item in setup_workers
                                         if item["worker_id"] == worker_id)),
                    "contribution_paths": [task["path"]],
                    "delivery": {"mode": "patch", "contribution_paths": [task["path"]]},
                }},
            }
            record = {
                "schema": "ask-agent.compact-command/v1", "phase": "verify-return",
                "worker_id": worker_id, "binding_path": str(binding_path),
                "binding_sha256": entry["binding_sha256"],
                "argv": [sys.executable, "-B", str(task_script.resolve()), "verify-return",
                         "--binding", str(binding_path)],
                "cwd": str(Path(manifest["paths"]["caller"]).resolve()),
                "exit_code": 0, "stdout": json.dumps(production_result, sort_keys=True,
                                                        separators=(",", ":")),
                "stderr": "", "status": "PASSED", "result": production_result,
                "evidence_path": str(record_path.resolve()),
            }
            case._write_json(record_path, record)
            returned = {"status": "PASSED", "worker_id": worker_id,
                        "delivery_mode": "patch",
                        "binding_sha256": entry["binding_sha256"],
                        "evidence_path": str(record_path.resolve()),
                        "contribution_paths": [task["path"]]}
            return_rows.extend(cli_updates(
                f"compact-verify-{worker_id}", operations_script,
                ["verify-return", "--run", str(run), "--worker", worker_id], returned,
            ))
        expected_ids = [item["worker_id"] for item in entries]
        integration_path = operator / "integration-result.json"
        case._write_json(integration_path, {
            "schema_version": 1, "run_id": manifest["run_id"],
            "status": "INTEGRATED", "delivery_mode": "patch",
            "integration_strategy": "preserve-parent patch",
            "integration_worker_ids": expected_ids,
            "parent_asserted_collected_worker_ids": expected_ids,
            "applied_worker_ids": expected_ids,
        })
        integration_rows = cli_updates(
            "compact-integration", operations_script,
            ["integrate-batch", "--run", str(run), "--delivery-mode", "patch",
             *[value for worker in expected_ids for value in ("--collected-worker", worker)]],
            {"status": "INTEGRATED", "delivery_mode": "patch",
             "applied_worker_ids": expected_ids, "worker_ids": expected_ids,
             "result_path": str(integration_path.resolve())},
        )
        collection_terminal = max(
            index for index, row in enumerate(case.updates)
            if row.get("params", {}).get("update", {}).get("toolCallId") == "collect-call-1"
            and row["params"]["update"].get("sessionUpdate") == "tool_call_update"
        )
        case.updates[collection_terminal + 1:collection_terminal + 1] = return_rows + integration_rows
        args_by_cwd = {item["native_arguments"]["cwd"]: item["native_arguments"] for item in entries}
        for row in case.updates:
            update = row.get("params", {}).get("update", {})
            if update.get("sessionUpdate") == "tool_call" and update.get("title") == "spawn_subagent":
                cwd = update.get("rawInput", {}).get("cwd")
                if cwd in args_by_cwd:
                    update["rawInput"] = args_by_cwd[cwd]
        case._write_updates()
        starts = {}
        for task in manifest["task_assignments"]:
            worker_id = str(task["worker_id"])
            probe_path = case.probes / f"worker-{worker_id}-start.json"
            starts[worker_id] = {"record": json.loads(probe_path.read_text(encoding="utf-8")),
                                 "path": probe_path}
        root_updates_path = case.session_dir / "updates.jsonl"
        root_updates = native_trace._root_updates(root_updates_path, case.session_id)
        spawn_calls = [row for row in native_trace._updates_for(root_updates, "tool_call")
                       if row["update"].get("title") == "spawn_subagent"]
        return {
            "setup": setup, "entries": entries, "index_rows": index_rows,
            "starts": starts, "root_updates": root_updates, "spawn_calls": spawn_calls,
            "root_updates_path": root_updates_path, "launches": launches,
            "child_transcripts": child_transcripts, "child_update_rows": child_update_rows,
            "phase_attempts": phase_attempts, "operations_script": operations_script,
        }

    def test_compact_child_invocation_accepts_bound_direct_and_exact_cd_forms_only(self):
        with tempfile.TemporaryDirectory(prefix="compact-native-command-") as temp:
            root = Path(temp).resolve()
            run = root / "run"
            cwd = root / "child"
            binding = run / "operator" / "compact-bindings" / "worker-1.json"
            wrapper = run / "operator" / "worker_phase.py"
            base = ["PYTHONDONTWRITEBYTECODE=1", "python3", "-B",
                    os.path.relpath(wrapper, cwd), "--run", os.path.relpath(run, cwd),
                    "--worker", "1", "--phase", "start", "--compact-binding",
                    os.path.relpath(binding, cwd)]
            direct = shlex.join(base)
            parse = native_trace._compact_child_invocation

            self.assertTrue(parse(direct, run, "1", "start", str(cwd), str(binding),
                                  launch_cwd_verified=True))
            self.assertFalse(parse(direct, run, "1", "start", str(cwd), str(binding)))
            prefixed = "cd " + shlex.quote(str(cwd)) + " && " + direct
            self.assertTrue(parse(prefixed, run, "1", "start", str(cwd), str(binding)))

            mutations = []
            wrong_script = list(base); wrong_script[3] = "wrong_worker_phase.py"
            mutations.append(shlex.join(wrong_script))
            wrong_run = list(base); wrong_run[5] = os.path.relpath(root / "other-run", cwd)
            mutations.append(shlex.join(wrong_run))
            wrong_binding = list(base); wrong_binding[-1] = str(root / "other-binding.json")
            mutations.append(shlex.join(wrong_binding))
            wrong_relative_binding = list(base)
            wrong_relative_binding[-1] = os.path.relpath(root / "other-binding.json", cwd)
            mutations.append(shlex.join(wrong_relative_binding))
            wrong_worker = list(base); wrong_worker[7] = "2"
            mutations.append(shlex.join(wrong_worker))
            wrong_phase = list(base); wrong_phase[9] = "finish"
            mutations.append(shlex.join(wrong_phase))
            wrong_env = list(base); wrong_env[0] = "PYTHONDONTWRITEBYTECODE=0"
            mutations.append(shlex.join(wrong_env))
            wrong_python = list(base); wrong_python[1] = "python"
            mutations.append(shlex.join(wrong_python))
            wrong_flag = list(base); wrong_flag[2] = "-c"
            mutations.append(shlex.join(wrong_flag))
            wrong_cwd = "cd " + shlex.quote(str(root / "other-child")) + " && " + direct
            malformed_cd = "cd " + shlex.quote(str(cwd)) + " ; " + direct
            mutations.extend((wrong_cwd, malformed_cd, direct + " && echo extra", direct + " ; echo extra"))
            for command in mutations:
                self.assertFalse(parse(command, run, "1", "start", str(cwd), str(binding),
                                       launch_cwd_verified=True), command)

    def test_compact_finish_accepts_only_known_fixture_test_prefix(self):
        with tempfile.TemporaryDirectory(prefix="compact-native-test-command-") as temp:
            root = Path(temp).resolve()
            run = root / "run"
            cwd = root / "child"
            binding = run / "operator" / "compact-bindings" / "worker-2.json"
            wrapper = run / "operator" / "worker_phase.py"
            wrapper_tokens = ["PYTHONDONTWRITEBYTECODE=1", "python3", "-B",
                              os.path.relpath(wrapper, cwd), "--run", os.path.relpath(run, cwd),
                              "--worker", "2", "--phase", "finish", "--compact-binding",
                              os.path.relpath(binding, cwd)]
            wrapper_command = shlex.join(wrapper_tokens)
            fixture_test = shlex.join([
                "PYTHONDONTWRITEBYTECODE=1", "python3", "-B", "checks.py", "--worker", "2",
            ])
            combined = "cd " + shlex.quote(str(cwd)) + " && " + fixture_test + " && " + wrapper_command
            parse = native_trace._compact_child_invocation

            accepted = parse(combined, run, "2", "finish", str(cwd), str(binding))
            self.assertEqual(accepted, {"fixture_test": True})
            direct = fixture_test + " && " + wrapper_command
            self.assertEqual(parse(direct, run, "2", "finish", str(cwd), str(binding),
                                   launch_cwd_verified=True), {"fixture_test": True})

            rejected = [
                combined.replace("checks.py --worker 2", "checks.py --worker 1"),
                combined.replace("checks.py", "other-checks.py"),
                combined.replace(" && " + wrapper_command, " ; " + wrapper_command),
                combined + " && echo debug",
                combined.replace("cd " + shlex.quote(str(cwd)), "cd " + shlex.quote(str(root / "wrong"))),
            ]
            start_wrapper = wrapper_command.replace("--phase finish", "--phase start")
            rejected.append("cd " + shlex.quote(str(cwd)) + " && " + fixture_test + " && " + start_wrapper)
            duplicate = combined + " && " + wrapper_command
            rejected.append(duplicate)
            for command in rejected:
                self.assertIsNone(parse(command, run, "2", "finish", str(cwd), str(binding),
                                        launch_cwd_verified=True), command)

    def test_compact_finish_accepts_observed_test_output_only_with_one_valid_wrapper_json(self):
        case = legacy_native_fixture.NativeTraceTests()
        case.setUp()
        try:
            synthetic = self._compact_synthetic_case(case)
            worker = "2"
            child_id = case.child_ids[1]
            rows = json.loads(json.dumps(synthetic["child_update_rows"][worker]))
            terminal = next(row["params"]["update"] for row in rows
                            if row["params"]["update"].get("toolCallId") == f"compact-child-{worker}-finish"
                            and row["params"]["update"].get("sessionUpdate") == "tool_call_update")
            call = next(row["params"]["update"] for row in rows
                        if row["params"]["update"].get("toolCallId") == f"compact-child-{worker}-finish"
                        and row["params"]["update"].get("sessionUpdate") == "tool_call")
            wrapper_command = call["rawInput"]["command"].split(" && ", 1)[1]
            cwd = synthetic["launches"][1]["cwd"]
            fixture_test = "PYTHONDONTWRITEBYTECODE=1 python3 -B checks.py --worker 2"
            call["rawInput"]["command"] = (
                "cd " + shlex.quote(cwd) + " && " + fixture_test + " && " + wrapper_command
            )
            wrapper_result = json.loads(terminal["rawOutput"]["output"])
            test_output = (
                "runTest (__main__.FormulaCheck.runTest) ... ok\n\n"
                "----------------------------------------------------------------------\n"
                "Ran 1 test in 0.000s\n\nOK\n"
            )

            def encode_terminal(result=wrapper_result, output_prefix=test_output, **raw_changes):
                raw_output = terminal["rawOutput"]
                raw_output.update({"type": "Bash", "exit_code": 0, "truncated": False})
                raw_output.update(raw_changes)
                payload = output_prefix + json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
                raw_output["output"] = list(payload.encode("utf-8"))

            child_path = Path(synthetic["child_transcripts"][child_id]["retained"]["path"])

            def audit():
                child_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
                                      encoding="utf-8")
                return native_trace._compact_worker_phase_check(
                    case.run, case.manifest["task_assignments"], synthetic["launches"],
                    synthetic["child_transcripts"], synthetic["root_updates_path"],
                )

            encode_terminal()
            passed = audit()
            self.assertEqual(passed["status"], "PASS", passed["detail"])
            self.assertTrue(passed["workers"][1]["phases"]["finish"]["native_result_valid"])

            invalid_prefixes = [
                test_output.replace("... ok", "... FAIL"),
                "diagnostic\n" + test_output,
                test_output + "extra output\n",
            ]
            for prefix in invalid_prefixes:
                encode_terminal(output_prefix=prefix)
                rejected = audit()
                self.assertEqual(rejected["status"], "FAIL", rejected["detail"])
                self.assertFalse(rejected["workers"][1]["phases"]["finish"]["native_result_valid"])

            encode_terminal()
            terminal_text = bytes(terminal["rawOutput"]["output"]).decode("utf-8")
            terminal["rawOutput"]["output"] = list((terminal_text[:-1] + "\n{}\n").encode("utf-8"))
            duplicate_json = audit()
            self.assertEqual(duplicate_json["status"], "FAIL", duplicate_json["detail"])

            ambiguous_json = json.dumps(wrapper_result, sort_keys=True, separators=(",", ":"))
            ambiguous_json = ambiguous_json.replace('"status":"PASSED"',
                                                    '"status":"FAILED","status":"PASSED"', 1)
            terminal["rawOutput"]["output"] = list((test_output + ambiguous_json + "\n").encode("utf-8"))
            duplicate_key = audit()
            self.assertEqual(duplicate_key["status"], "FAIL", duplicate_key["detail"])

            for field, value in (("status", "FAILED"), ("phase", "start"), ("root", "/wrong/root")):
                wrong_result = dict(wrapper_result)
                wrong_result[field] = value
                encode_terminal(wrong_result)
                rejected = audit()
                self.assertEqual(rejected["status"], "FAIL", rejected["detail"])

            encode_terminal()
            raw_output = terminal["rawOutput"]
            raw_output["exit_code"] = 1
            self.assertEqual(audit()["status"], "FAIL")
            raw_output["exit_code"] = 0
            raw_output["truncated"] = True
            self.assertEqual(audit()["status"], "FAIL")
        finally:
            case.tearDown()

    def test_compact_phase_audit_requires_bound_cwd_for_direct_calls_and_rejects_duplicates(self):
        case = legacy_native_fixture.NativeTraceTests()
        case.setUp()
        try:
            synthetic = self._compact_synthetic_case(case)
            worker = synthetic["entries"][0]["worker_id"]
            child_id = case.child_ids[0]
            rows = json.loads(json.dumps(synthetic["child_update_rows"][worker]))
            cwd = synthetic["launches"][0]["cwd"]
            for row in rows:
                update = row.get("params", {}).get("update", {})
                if update.get("sessionUpdate") == "tool_call":
                    tokens = shlex.split(update["rawInput"]["command"])
                    self.assertEqual(tokens[:3], ["cd", cwd, "&&"])
                    update["rawInput"]["command"] = shlex.join(tokens[3:])
            child_path = Path(synthetic["child_transcripts"][child_id]["retained"]["path"])
            child_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
                                  encoding="utf-8")

            check = native_trace._compact_worker_phase_check(
                case.run, case.manifest["task_assignments"], synthetic["launches"],
                synthetic["child_transcripts"], synthetic["root_updates_path"],
                native_cwd_probe_passed=True,
            )
            self.assertEqual(check["status"], "PASS", check["detail"])

            unbound = native_trace._compact_worker_phase_check(
                case.run, case.manifest["task_assignments"], synthetic["launches"],
                synthetic["child_transcripts"], synthetic["root_updates_path"],
            )
            self.assertNotEqual(unbound["status"], "PASS")
            self.assertTrue(any("lacks its start compact wrapper invocation" in item
                                for item in unbound["missing"]))

            original_cwd = synthetic["launches"][0]["cwd"]
            synthetic["launches"][0]["cwd"] = None
            missing_cwd = native_trace._compact_worker_phase_check(
                case.run, case.manifest["task_assignments"], synthetic["launches"],
                synthetic["child_transcripts"], synthetic["root_updates_path"],
                native_cwd_probe_passed=True,
            )
            self.assertEqual(missing_cwd["status"], "FAIL")
            self.assertTrue(any("native cwd differs from compact setup worktree" in item
                                for item in missing_cwd["errors"]))
            synthetic["launches"][0]["cwd"] = original_cwd

            duplicate_rows = json.loads(json.dumps(rows))
            duplicate_pair = [row for row in rows
                              if row.get("params", {}).get("update", {}).get("toolCallId")
                              == "compact-child-1-start"]
            self.assertEqual(len(duplicate_pair), 2)
            duplicate_pair = json.loads(json.dumps(duplicate_pair))
            for row in duplicate_pair:
                row["params"]["update"]["toolCallId"] = "compact-child-1-start-duplicate"
            duplicate_rows.extend(duplicate_pair)
            child_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in duplicate_rows),
                                  encoding="utf-8")
            duplicate = native_trace._compact_worker_phase_check(
                case.run, case.manifest["task_assignments"], synthetic["launches"],
                synthetic["child_transcripts"], synthetic["root_updates_path"],
                native_cwd_probe_passed=True,
            )
            self.assertEqual(duplicate["status"], "FAIL")
            self.assertTrue(any("duplicate start wrapper invocations" in item
                                for item in duplicate["errors"]))
        finally:
            case.tearDown()

    def test_native_compact_evidence_passes_and_rejects_missing_or_mutated_evidence(self):
        case = legacy_native_fixture.NativeTraceTests()
        case.setUp()
        try:
            synthetic = self._compact_synthetic_case(case)
            dispatch, _ = native_trace._compact_dispatch_check(
                case.run, case.manifest["task_assignments"], synthetic["spawn_calls"],
                synthetic["starts"], synthetic["root_updates"], synthetic["root_updates_path"],
            )
            self.assertEqual(dispatch["status"], "PASS", dispatch["detail"])

            collect_calls = [row for row in native_trace._updates_for(synthetic["root_updates"], "tool_call")
                             if row["update"].get("title") == "get_command_or_subagent_output"]
            parent_returns = native_trace._compact_parent_return_check(
                case.run, case.manifest["task_assignments"], synthetic["root_updates"],
                collect_calls, synthetic["root_updates_path"],
                launches=synthetic["launches"],
            )
            self.assertEqual(parent_returns["status"], "PASS", parent_returns["detail"])

            phase_check = native_trace._compact_worker_phase_check(
                case.run, case.manifest["task_assignments"], synthetic["launches"],
                synthetic["child_transcripts"], synthetic["root_updates_path"],
            )
            self.assertEqual(phase_check["status"], "PASS", phase_check["detail"])

            first_child = case.child_ids[0]
            first_rows = synthetic["child_update_rows"]["1"]
            failed_terminal = json.loads(json.dumps(first_rows))
            start_terminal = next(row for row in failed_terminal
                                  if row.get("params", {}).get("update", {}).get("toolCallId")
                                  == "compact-child-1-start"
                                  and row["params"]["update"].get("sessionUpdate") == "tool_call_update")
            start_terminal["params"]["update"]["rawOutput"]["exit_code"] = 7
            child_path = Path(synthetic["child_transcripts"][first_child]["retained"]["path"])
            child_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in failed_terminal),
                                  encoding="utf-8")
            successful_parent_record = json.loads(
                synthetic["phase_attempts"]["1"]["start"]["command"].read_text(encoding="utf-8")
            )
            self.assertEqual(successful_parent_record["exit_code"], 0)
            self.assertEqual(successful_parent_record["json"]["status"], "WORKER_CONTEXT_READY")
            phase_check = native_trace._compact_worker_phase_check(
                case.run, case.manifest["task_assignments"], synthetic["launches"],
                synthetic["child_transcripts"], synthetic["root_updates_path"],
            )
            self.assertEqual(phase_check["status"], "FAIL")
            self.assertTrue(any("terminal result is not a successful bound phase" in item
                                for item in phase_check["errors"]))

            missing_start = [row for row in first_rows
                             if row.get("params", {}).get("update", {}).get("toolCallId")
                             != "compact-child-1-start"]
            child_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in missing_start),
                                  encoding="utf-8")
            self.assertTrue((case.probes / "worker-1-start.json").is_file())
            self.assertTrue(synthetic["phase_attempts"]["1"]["start"]["attempt"].is_file())
            phase_check = native_trace._compact_worker_phase_check(
                case.run, case.manifest["task_assignments"], synthetic["launches"],
                synthetic["child_transcripts"], synthetic["root_updates_path"],
            )
            self.assertEqual(phase_check["status"], "INCOMPLETE")
            self.assertTrue(any("lacks its start compact wrapper invocation" in item
                                for item in phase_check["missing"]))

            child_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in first_rows),
                                  encoding="utf-8")
            production_path = synthetic["phase_attempts"]["1"]["start"]["command"]
            production = json.loads(production_path.read_text(encoding="utf-8"))
            production["json"]["binding_sha256"] = "wrong-binding"
            case._write_json(production_path, production)
            phase_check = native_trace._compact_worker_phase_check(
                case.run, case.manifest["task_assignments"], synthetic["launches"],
                synthetic["child_transcripts"], synthetic["root_updates_path"],
            )
            self.assertEqual(phase_check["status"], "FAIL")
            self.assertTrue(any("production start command or binding evidence does not match" in item
                                for item in phase_check["errors"]))

            root_spawn = next(row for row in case.updates
                              if row.get("params", {}).get("update", {}).get("title") == "spawn_subagent"
                              and row["params"]["update"].get("rawInput", {}).get("cwd")
                              == synthetic["entries"][0]["native_arguments"]["cwd"])
            root_spawn["params"]["update"]["rawInput"]["prompt"] += " altered after emission"
            case._write_updates()
            updated_root = native_trace._root_updates(synthetic["root_updates_path"], case.session_id)
            updated_spawns = [row for row in native_trace._updates_for(updated_root, "tool_call")
                              if row["update"].get("title") == "spawn_subagent"]
            dispatch, _ = native_trace._compact_dispatch_check(
                case.run, case.manifest["task_assignments"], updated_spawns, synthetic["starts"],
                updated_root, synthetic["root_updates_path"],
            )
            self.assertEqual(dispatch["status"], "FAIL")
            self.assertIn("differ from its emitted compact assignment", dispatch["detail"])

            integration_call = next(row for row in case.updates
                                     if row.get("params", {}).get("update", {}).get("toolCallId")
                                     == "compact-integration"
                                     and row["params"]["update"].get("sessionUpdate") == "tool_call")
            integration_terminal = next(row for row in case.updates
                                         if row.get("params", {}).get("update", {}).get("toolCallId")
                                         == "compact-integration"
                                         and row["params"]["update"].get("sessionUpdate") == "tool_call_update")
            case.updates.remove(integration_call)
            case.updates.remove(integration_terminal)
            collection_terminal = max(
                index for index, row in enumerate(case.updates)
                if row.get("params", {}).get("update", {}).get("toolCallId") == "collect-call-1"
                and row["params"]["update"].get("sessionUpdate") == "tool_call_update"
            )
            case.updates[collection_terminal + 1:collection_terminal + 1] = [integration_call]
            case.updates.append(integration_terminal)
            case._write_updates()
            reordered_root = native_trace._root_updates(synthetic["root_updates_path"], case.session_id)
            reordered_collects = [row for row in native_trace._updates_for(reordered_root, "tool_call")
                                  if row["update"].get("title") == "get_command_or_subagent_output"]
            parent_returns = native_trace._compact_parent_return_check(
                case.run, case.manifest["task_assignments"], reordered_root,
                reordered_collects, synthetic["root_updates_path"],
                launches=synthetic["launches"],
            )
            self.assertEqual(parent_returns["status"], "FAIL")
            self.assertIn("integration began before all verify-return commands completed",
                          parent_returns["detail"])
        finally:
            case.tearDown()


if __name__ == "__main__":
    unittest.main()
