#!/usr/bin/env python3
"""Black-box offline contract tests for the compact Agent Harness CLI.

Every repository and run is disposable.  Native results are explicitly marked
as simulated fixture data; no model or native-agent process is launched.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "skills/in-parallel/scripts/harness.py"
HARNESS_CARD = ROOT / "skills/in-parallel/SKILL.md"
ASK_AGENT_CARD = ROOT / "skills/ask-agent/SKILL.md"
DISPATCHER_CARD = ROOT / "skills/plan-dispatcher/SKILL.md"
DISPATCHER = ROOT / "skills/plan-dispatcher/scripts/dispatch.js"


class AgentHarnessOfflineContractTests(unittest.TestCase):
    """Exercise the public coordinator commands against real temporary Git repos."""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="agent-harness-offline-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.home = self.root / "home"
        (self.home / ".config").mkdir(parents=True)
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        self.env.update({
            "HOME": str(self.home),
            "XDG_CONFIG_HOME": str(self.home / ".config"),
            "GIT_OPTIONAL_LOCKS": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        })
        self.source = self.root / "source"
        self.source.mkdir()
        self._git(self.source, "init", "-q", "--initial-branch=main")
        self._git(self.source, "config", "user.name", "Agent Harness Offline Test")
        self._git(self.source, "config", "user.email", "agent-harness@example.invalid")
        self._git(self.source, "config", "core.excludesFile", os.devnull)
        (self.source / ".gitignore").write_text("build/\n", encoding="utf-8")
        (self.source / ".claspignore").write_text("node_modules/\n", encoding="utf-8")
        (self.source / "caller.txt").write_text("caller baseline\n", encoding="utf-8")
        (self.source / "app.txt").write_text("base application\n", encoding="utf-8")
        self._git(self.source, "add", "--", ".gitignore", ".claspignore", "caller.txt", "app.txt")
        self._git(self.source, "commit", "-q", "-m", "offline fixture baseline")
        (self.root / "runs").mkdir()

    def _git(self, cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["git", "-C", str(cwd), *args], cwd=self.root, env=self.env,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60,
        )
        if check and result.returncode:
            self.fail(
                f"git {' '.join(args)} failed in {cwd}:\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        return result

    def _write_json(self, path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _json_command(self, argv: list[str], *, cwd: Path | None = None) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        completed = subprocess.run(
            argv, cwd=cwd or self.root, env=self.env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=120,
        )
        output = completed.stdout if completed.returncode == 0 else completed.stderr
        try:
            value = json.loads(output)
        except json.JSONDecodeError as exc:
            self.fail(
                f"command did not return JSON ({exc}):\n"
                f"argv={argv!r}\nstdout={completed.stdout}\nstderr={completed.stderr}"
            )
        self.assertIsInstance(value, dict, value)
        return completed, value

    def _harness(self, *args: str, success: bool = True) -> dict[str, Any]:
        completed, value = self._json_command([sys.executable, "-B", str(HARNESS), *args])
        if success:
            self.assertEqual(completed.returncode, 0, value)
            self.assertNotEqual(value.get("status"), "BLOCKED", value)
        else:
            self.assertNotEqual(completed.returncode, 0, value)
            self.assertEqual(value.get("status"), "BLOCKED", value)
        return value

    def _task(self, task_id: str, *, write_set: Iterable[str] | None = None) -> dict[str, Any]:
        selected = list(write_set if write_set is not None else [f"contributions/{task_id}.txt"])
        return {
            "id": task_id,
            "objective": f"Perform the bounded offline fixture task for {task_id}.",
            "expected_result": f"The verified contribution for {task_id} is returned.",
            "write_set": selected,
        }

    def _request(
        self,
        tasks: list[dict[str, Any]],
        *,
        workspace: str = "worktree",
        mode: str = "edit",
        capacity: int | None = None,
        integration: str = "apply",
        checks: list[list[str]] | None = None,
        **overrides: Any,
    ) -> dict[str, Any]:
        request: dict[str, Any] = {
            "objective": "Exercise the compact Agent Harness contract offline.",
            "source": str(self.source),
            "workspace": workspace,
            "mode": mode,
            "tasks": tasks,
            "integration": integration,
            "checks": checks if checks is not None else [],
        }
        if capacity is not None:
            request["capacity"] = capacity
        if workspace == "worktree":
            request["writers_quiescent"] = True
        if workspace == "current" and mode == "edit":
            request["exclusive_writer"] = True
        request.update(overrides)
        return request

    def _init(self, request: Mapping[str, Any], name: str = "run") -> Path:
        run = self.root / "runs" / name
        self._write_json(self.root / f"{name}-request.json", dict(request))
        response = self._harness(
            "init", "--run", str(run), "--request", str(self.root / f"{name}-request.json"),
            "--ask-agent-card", str(ASK_AGENT_CARD), "--dispatcher-card", str(DISPATCHER_CARD),
        )
        self.assertEqual(response.get("status"), "READY", response)
        self.assertTrue((run / "run.json").is_file())
        return run

    def _dispatch(self, run: Path) -> dict[str, Any]:
        return self._harness("dispatch", "--run", str(run))

    def _inject_dispatcher_failure_once(self, operation: str) -> Path:
        """Make the saved Node runtime fail one named Dispatcher call."""
        real_node = shutil.which("node", path=self.env.get("PATH"))
        self.assertIsNotNone(real_node, "the selected Plan Dispatcher requires Node.js")
        wrapper_dir = self.root / f"node-wrapper-{operation}"
        wrapper_dir.mkdir()
        wrapper = wrapper_dir / "node"
        marker = self.root / f"injected-{operation}.marker"
        wrapper.write_text(
            "#!" + sys.executable + "\n"
            "import os, pathlib, sys\n"
            f"real_node = {str(real_node)!r}\n"
            f"operation = {operation!r}\n"
            f"marker = pathlib.Path({str(marker)!r})\n"
            "if len(sys.argv) > 2 and sys.argv[2] == operation and not marker.exists():\n"
            "    marker.write_text('offline injected failure\\n', encoding='utf-8')\n"
            "    print('offline injected Dispatcher failure', file=sys.stderr)\n"
            "    raise SystemExit(71)\n"
            "os.execv(real_node, [real_node, *sys.argv[1:]])\n",
            encoding="utf-8",
        )
        wrapper.chmod(0o755)
        self.env["PATH"] = str(wrapper_dir) + os.pathsep + self.env.get("PATH", "")
        return marker

    def _launches(self, run: Path) -> list[dict[str, Any]]:
        response = self._dispatch(run)
        self.assertEqual(response.get("status"), "LAUNCH_REQUIRED", response)
        launches = response.get("launches")
        self.assertIsInstance(launches, list, response)
        for launch in launches:
            self.assertTrue(launch.get("task"), launch)
            self.assertTrue(launch.get("attempt"), launch)
            self.assertTrue(Path(launch.get("cwd", "")).is_absolute(), launch)
            self.assertTrue(launch.get("prompt"), launch)
            prepared_path = run / "prepared" / f"{launch['attempt']}.json"
            self.assertTrue(prepared_path.is_file(), prepared_path)
            prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
            self.assertEqual(prepared.get("status"), "READY_TO_LAUNCH", prepared)
            for name in ("worker-start", "worker-finish", "verify-return"):
                command = prepared["commands"][name]
                self.assertIsInstance(command["argv"], list, command)
                self.assertTrue(command["argv"], command)
                self.assertTrue(Path(command["cwd"]).is_absolute(), command)
                self.assertEqual(command["argv"][2], name, command)
                expected_cwd = launch["cwd"] if name != "verify-return" else str(self.source)
                self.assertEqual(command["cwd"], expected_cwd, command)
        return launches

    def _prepared(self, run: Path, launch: Mapping[str, Any]) -> dict[str, Any]:
        return json.loads((run / "prepared" / f"{launch['attempt']}.json").read_text(encoding="utf-8"))

    def _prepared_command(self, prepared: Mapping[str, Any], name: str) -> dict[str, Any]:
        command = prepared["commands"][name]
        completed, value = self._json_command(command["argv"], cwd=Path(command["cwd"]))
        self.assertEqual(completed.returncode, 0, value)
        return value

    def _worker(
        self,
        run: Path,
        launch: Mapping[str, Any],
        *,
        edits: Mapping[str, str] | None = None,
        commit: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        prepared = self._prepared(run, launch)
        self.assertEqual(prepared["launch"]["cwd"], launch["cwd"])
        worker_root = Path(launch["cwd"])
        start = self._prepared_command(prepared, "worker-start")
        self.assertEqual(start.get("status"), "WORKER_CONTEXT_READY", start)
        self.assertFalse(start.get("native_lifecycle_verified"), start)
        action_packet = start.get("action_packet")
        self.assertIsInstance(action_packet, dict, start)
        self.assertEqual(action_packet.get("finish_command"), prepared["commands"]["worker-finish"])

        for relative, content in (edits or {}).items():
            path = worker_root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        if commit:
            self.assertTrue(edits, "a fixture commit must contain explicit contribution paths")
            self._git(worker_root, "add", "--", *edits.keys())
            self._git(worker_root, "commit", "-q", "-m", f"offline worker contribution {launch['task']}")
        finish = self._prepared_command(prepared, "worker-finish")
        self.assertEqual(finish.get("status"), "READY_FOR_PARENT_ACCEPTANCE", finish)
        self.assertEqual(finish.get("command"), "worker-finish")
        return start, finish

    def _handle(self, launch: Mapping[str, Any]) -> str:
        # This label makes the test fixture's simulated native handle explicit.
        return f"offline-simulated-native:{launch['attempt']}"

    def _confirm_launch(self, run: Path, launch: Mapping[str, Any]) -> str:
        handle = self._handle(launch)
        response = self._harness(
            "launched", "--run", str(run), "--attempt", str(launch["attempt"]), "--handle", handle,
        )
        self.assertIn(response.get("status"), ("RECORDED_STATUS", "READY"), response)
        return handle

    def _result(
        self,
        launch: Mapping[str, Any],
        handle: str,
        *,
        status: str = "SUCCEEDED",
        level: str = "confirmed",
        evidence: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        contract = launch["result_contract"]
        criteria = [{
            "criterion": item["criterion"],
            "check": f"offline fixture assertion for: {item['criterion']}",
            "observed": f"offline fixture observed: {item['criterion']}",
            "level": level,
        } for item in contract["criteria"]]
        return {
            "native_handle": handle,
            "native_terminal": True,
            "status": status,
            "summary": f"[OFFLINE SIMULATED NATIVE RESULT] fixture result for {launch['task']}.",
            "criteria": criteria,
            "evidence": list(evidence or []),
        }

    def _collect(
        self,
        run: Path,
        launch: Mapping[str, Any],
        result: Mapping[str, Any] | None = None,
        *,
        name: str = "native",
        success: bool = True,
    ) -> dict[str, Any]:
        result_path = self.root / f"{name}-{launch['attempt']}.json"
        self._write_json(result_path, dict(result or self._result(launch, self._handle(launch))))
        return self._harness(
            "collect", "--run", str(run), "--attempt", str(launch["attempt"]), "--result", str(result_path),
            success=success,
        )

    def _verification(self, launch: Mapping[str, Any], *, contents: str | None = None) -> Path:
        path = self.root / "verification-evidence" / f"{launch['attempt']}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents or f"Offline independent check for {launch['task']} passed.\n", encoding="utf-8")
        return path

    def _accept(self, run: Path, launch: Mapping[str, Any], *, evidence: list[dict[str, str]] | None = None) -> dict[str, Any]:
        proof = self._verification(launch)
        verification = self.root / f"verification-{launch['attempt']}.json"
        self._write_json(verification, {
            "passed": True,
            "reason": f"Offline fixture independently inspected the return for {launch['task']}.",
            "evidence": evidence if evidence is not None else [{"path": str(proof), "sha256": self._sha256(proof)}],
        })
        return self._harness(
            "accept", "--run", str(run), "--attempt", str(launch["attempt"]), "--verification", str(verification),
        )

    def _complete(
        self,
        run: Path,
        launch: Mapping[str, Any],
        *,
        edits: Mapping[str, str] | None = None,
        commit: bool = False,
        status: str = "SUCCEEDED",
        level: str = "confirmed",
    ) -> dict[str, Any]:
        handle = self._confirm_launch(run, launch)
        self._worker(run, launch, edits=edits, commit=commit)
        collected = self._collect(run, launch, self._result(launch, handle, status=status, level=level))
        self.assertEqual(collected.get("status"), "AWAITING_VERIFICATION", collected)
        record = json.loads((run / "collected" / f"{launch['attempt']}.json").read_text(encoding="utf-8"))
        self.assertEqual(record.get("native_evidence_kind"), "coordinator_attestation", record)
        self.assertIn("[OFFLINE SIMULATED NATIVE RESULT]", record["result"]["summary"])
        return record

    def _accepted(self, run: Path, launch: Mapping[str, Any], **worker_options: Any) -> dict[str, Any]:
        record = self._complete(run, launch, **worker_options)
        accepted = self._accept(run, launch)
        self.assertEqual(accepted.get("status"), "RECORDED_STATUS", accepted)
        return record

    def _worktree_registered(self, path: Path) -> bool:
        rows = self._git(self.source, "worktree", "list", "--porcelain").stdout.splitlines()
        return "worktree " + str(path) in rows

    def _sha256(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _git_snapshot(self, repo: Path) -> dict[str, Any]:
        head = self._git(repo, "rev-parse", "HEAD").stdout.strip()
        index_path_text = self._git(repo, "rev-parse", "--git-path", "index").stdout.strip()
        index_path = Path(index_path_text)
        if not index_path.is_absolute():
            index_path = repo / index_path
        return {
            "head": head,
            "index_bytes": index_path.read_bytes(),
            "index_entries": self._git(repo, "ls-files", "--stage", "-z").stdout,
            "cached_diff": self._git(repo, "diff", "--cached", "--binary").stdout,
            "status": self._git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout,
        }

    def _byte_inventory(self, root: Path) -> dict[str, bytes | str]:
        inventory: dict[str, bytes | str] = {}
        for path in sorted(root.rglob("*")):
            relative = str(path.relative_to(root))
            if path.is_symlink():
                inventory[relative] = "symlink:" + os.readlink(path)
            elif path.is_file():
                inventory[relative] = path.read_bytes()
        return inventory

    def _make_dirty_parent(self) -> dict[str, Any]:
        (self.source / ".gitignore").write_text("build/\nparent-generated/\n", encoding="utf-8")
        (self.source / ".claspignore").write_text("node_modules/\nparent-private/**\n", encoding="utf-8")
        (self.source / "caller.txt").write_text("caller staged layer\n", encoding="utf-8")
        self._git(self.source, "add", "--", "caller.txt")
        (self.source / "caller.txt").write_text("caller staged layer\ncaller unstaged layer\n", encoding="utf-8")
        (self.source / "caller-note.txt").write_text("untracked caller input\n", encoding="utf-8")
        return self._git_snapshot(self.source)

    def _dispatcher_packet(self, run: Path, attempt: str) -> dict[str, Any]:
        request = self.root / f"packet-{attempt}.json"
        self._write_json(request, {"attempt": attempt})
        node = shutil.which("node")
        self.assertIsNotNone(node, "the selected Plan Dispatcher requires Node.js")
        completed, value = self._json_command([node, str(DISPATCHER), "packet", str(run / "dispatcher"), str(request)])
        self.assertEqual(completed.returncode, 0, value)
        return value["packet"]

    def test_three_commit_workers_merge_dirty_parent_and_preserve_head_and_index(self) -> None:
        before = self._make_dirty_parent()
        parent_inputs = {
            name: (self.source / name).read_bytes()
            for name in (".gitignore", ".claspignore", "caller.txt", "caller-note.txt")
        }
        task_ids = ("alpha", "beta", "gamma")
        tasks = [self._task(name) for name in task_ids]
        check_code = (
            "from pathlib import Path; "
            "assert all((Path('contributions') / f'{name}.txt').read_text() == f'{name}\\n' "
            "for name in ('alpha', 'beta', 'gamma')); print('combined contributions verified')"
        )
        run = self._init(self._request(
            tasks, capacity=3, checks=[[sys.executable, "-c", check_code]],
        ), "three-commit-workers")

        launches = self._launches(run)
        self.assertEqual({row["task"] for row in launches}, set(task_ids))
        self.assertEqual(len({row["attempt"] for row in launches}), 3)
        for launch in launches:
            prepared = self._prepared(run, launch)
            worker_root = Path(launch["cwd"])
            self.assertEqual(worker_root, Path(prepared["launch"]["cwd"]))
            for name, contents in parent_inputs.items():
                self.assertEqual((worker_root / name).read_bytes(), contents, name)
            self.assertEqual((worker_root / "app.txt").read_text(encoding="utf-8"), "base application\n")

        for launch in launches:
            name = launch["task"]
            contribution = f"contributions/{name}.txt"
            record = self._accepted(
                run, launch, edits={contribution: f"{name}\n"}, commit=True,
            )
            self.assertEqual(record["result"]["criteria"][0]["level"], "confirmed")
            self.assertEqual(record["native_evidence_kind"], "coordinator_attestation")
            self.assertEqual(self._prepared(run, launch)["commands"]["verify-return"]["cwd"], str(self.source))

        finished = self._harness("finish", "--run", str(run))
        self.assertEqual(finished.get("status"), "SUCCEEDED", finished)
        self.assertEqual(finished.get("cleanup_status"), "complete", finished)
        self.assertEqual({item["id"] for item in finished["workers"]}, set(task_ids))
        self.assertEqual(finished["integration"]["outcome"], "applied")
        self.assertEqual(set(finished["integration"]["applied_paths"]), {
            f"contributions/{name}.txt" for name in task_ids
        })
        self.assertTrue(finished["integration"]["postcondition"]["head_and_index_preserved"])
        self.assertTrue(finished["integration"]["postcondition"]["worker_files_match"])
        self.assertEqual(finished["native_lifecycle"], "coordinator-attested; experiment host traces are separate evidence")
        for name in task_ids:
            self.assertEqual((self.source / "contributions" / f"{name}.txt").read_text(encoding="utf-8"), f"{name}\n")
        for name, contents in parent_inputs.items():
            self.assertEqual((self.source / name).read_bytes(), contents, name)
        after = self._git_snapshot(self.source)
        for key in ("head", "index_bytes", "index_entries", "cached_diff"):
            self.assertEqual(after[key], before[key], key)
        self.assertIn("caller-note.txt", after["status"])
        for worker in finished["workers"]:
            worktree = Path(worker["worktree"])
            self.assertFalse(worktree.exists(), worker["cleanup"])
            self.assertFalse(self._worktree_registered(worktree), worker["cleanup"])
            self.assertEqual(worker["cleanup"]["worktree_path_status"], "removed")
            self.assertEqual(worker["cleanup"]["historical_worktree_path"], str(worktree))
            self.assertNotIn(str(worktree), finished["retained_locations"])
            self.assertTrue(Path(worker["cleanup"]["evidence_manifest"]).is_file())
            for commit in worker["delivery"]["commits"]:
                self._git(self.source, "cat-file", "-e", f"{commit}^{{commit}}")
            self._git(self.source, "show-ref", "--verify", "refs/heads/" + worker["branch"])

    def test_current_report_only_reserves_three_read_only_launches_and_status_is_read_only(self) -> None:
        tasks = [self._task(name, write_set=[]) for name in ("review-a", "review-b", "review-c")]
        run = self._init(self._request(
            tasks, workspace="current", mode="report-only", capacity=3, integration="apply",
        ), "current-report-only")
        launches = self._launches(run)
        self.assertEqual(len(launches), 3)
        self.assertEqual({item["task"] for item in launches}, {"review-a", "review-b", "review-c"})
        self.assertEqual({item["cwd"] for item in launches}, {str(self.source)})
        for launch in launches:
            prepared = self._prepared(run, launch)
            self.assertEqual(prepared["launch"]["mode"], "report-only")
            self.assertEqual(prepared["commands"]["worker-start"]["cwd"], str(self.source))
            packet = self._dispatcher_packet(run, launch["attempt"])
            self.assertEqual(packet["context"]["workspace"], str(self.source))
            self.assertTrue(packet["context"]["read_only"])
            self.assertEqual(packet["context"]["write_scope"], [])

        before_run, before_source = self._byte_inventory(run), self._byte_inventory(self.source)
        status = self._harness("status", "--run", str(run))
        self.assertEqual(status.get("status"), "RECORDED_STATUS", status)
        self.assertEqual(self._byte_inventory(run), before_run)
        self.assertEqual(self._byte_inventory(self.source), before_source)

    def test_current_edits_are_forced_serial_and_prepared_in_place(self) -> None:
        tasks = [self._task("first", write_set=["one.txt"]), self._task("second", write_set=["two.txt"])]
        run = self._init(self._request(
            tasks, workspace="current", mode="edit", capacity=2,
            checks=[[sys.executable, "-c", "print('current edit fixture check')"]],
        ), "current-edit-serial")
        metadata = json.loads((run / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["request"]["capacity"], 1)
        self.assertEqual(metadata["warnings"][0]["code"], "CURRENT_EDIT_SERIALIZED")
        launches = self._launches(run)
        self.assertEqual(len(launches), 1)
        launch = launches[0]
        prepared = self._prepared(run, launch)
        self.assertEqual(launch["cwd"], str(self.source))
        self.assertEqual(prepared["launch"]["cwd"], str(self.source))
        self.assertEqual(prepared["commands"]["worker-start"]["cwd"], str(self.source))
        self.assertEqual(prepared["commands"]["worker-finish"]["cwd"], str(self.source))
        self.assertEqual(prepared["commands"]["verify-return"]["cwd"], str(self.source))
        self.assertEqual(self._dispatch(run)["status"], "NO_NEW_LAUNCH")

    def test_ephemeral_findings_stay_in_retained_scratch(self) -> None:
        task = self._task("audit", write_set=[".scratch/"])
        run = self._init(self._request(
            [task], workspace="worktree", mode="ephemeral", capacity=1, integration="apply",
        ), "ephemeral-findings")
        launch = self._launches(run)[0]
        handle = self._confirm_launch(run, launch)
        scratch = ".scratch/findings.txt"
        self._worker(run, launch, edits={scratch: "offline finding\n"})
        collected = self._collect(run, launch, self._result(launch, handle))
        self.assertEqual(collected.get("status"), "AWAITING_VERIFICATION", collected)
        record = json.loads((run / "collected" / f"{launch['attempt']}.json").read_text(encoding="utf-8"))
        audit = record["verified"]["workspace_evidence"]["ephemeral_audit"]
        self.assertEqual(audit.get("status"), "ephemeral-audit")
        self.assertTrue(audit.get("findings_only"))
        self.assertTrue(audit.get("scratch_retained"))
        self.assertEqual(audit["changed_paths"], [scratch])
        self.assertTrue((Path(launch["cwd"]) / scratch).is_file())
        self.assertFalse((self.source / scratch).exists())
        self._accept(run, launch)
        finished = self._harness("finish", "--run", str(run))
        self.assertEqual(finished.get("status"), "SUCCEEDED", finished)
        self.assertEqual(finished.get("cleanup_status"), "not-applicable", finished)
        self.assertEqual(finished["integration"]["outcome"], "not-applicable")
        self.assertTrue(Path(launch["cwd"]).is_dir())
        self.assertTrue(self._worktree_registered(Path(launch["cwd"])))
        self.assertFalse((self.source / scratch).exists())

    def test_return_only_keeps_verified_commits_without_importing_them(self) -> None:
        task = self._task("proposal")
        run = self._init(self._request(
            [task], integration="return-only", capacity=1,
        ), "return-only")
        before = self._git_snapshot(self.source)
        launch = self._launches(run)[0]
        path = "contributions/proposal.txt"
        record = self._accepted(run, launch, edits={path: "returned only\n"}, commit=True)
        self.assertEqual(record["native_evidence_kind"], "coordinator_attestation")
        finished = self._harness("finish", "--run", str(run))
        self.assertEqual(finished.get("status"), "SUCCEEDED", finished)
        self.assertEqual(finished.get("cleanup_status"), "not-applicable", finished)
        self.assertEqual(finished["integration"]["outcome"], "return-only")
        self.assertEqual(finished["integration"]["applied_paths"], [])
        self.assertFalse(finished["integration"]["application_attempted"])
        retained_patches = [Path(worker["delivery"]["patch_path"]) for worker in finished["workers"]]
        self.assertTrue(retained_patches, finished["retained_locations"])
        self.assertTrue(all(item.is_file() for item in retained_patches), retained_patches)
        for worker in finished["workers"]:
            self.assertEqual(self._sha256(Path(worker["delivery"]["patch_path"])), worker["delivery"]["patch_sha256"])
        self.assertFalse((self.source / path).exists())
        self.assertEqual(self._git_snapshot(self.source), before)
        worker_root = Path(self._prepared(run, launch)["launch"]["cwd"])
        self.assertEqual((worker_root / path).read_text(encoding="utf-8"), "returned only\n")
        self.assertTrue(self._worktree_registered(worker_root))

    def test_check_failure_or_source_mutation_retains_accepted_worktree(self) -> None:
        cases = (
            ("failing-check", [[sys.executable, "-c", "raise SystemExit(7)"]], "FAILED"),
            ("mutating-check", [[sys.executable, "-c", "from pathlib import Path; Path('late-check.txt').write_text('changed\\n')"]], "FAILED"),
        )
        for name, checks, expected_status in cases:
            with self.subTest(name=name):
                task = self._task(name)
                run = self._init(self._request([task], checks=checks), name)
                launch = self._launches(run)[0]
                self._accepted(run, launch, edits={f"contributions/{name}.txt": f"{name}\n"}, commit=True)
                completed, finished = self._json_command([
                    sys.executable, "-B", str(HARNESS), "finish", "--run", str(run),
                ])
                self.assertNotEqual(completed.returncode, 0, finished)
                self.assertEqual(finished.get("status"), expected_status, finished)
                self.assertFalse(finished.get("delivery_success"), finished)
                self.assertEqual(finished.get("cleanup_status"), "retained", finished)
                worktree = Path(launch["cwd"])
                self.assertTrue(worktree.is_dir())
                self.assertTrue(self._worktree_registered(worktree))
                self.assertEqual(finished["workers"][0]["cleanup"]["worktree_path_status"], "retained")

    def test_changed_worker_after_passing_check_is_visible_as_cleanup_pending(self) -> None:
        name = "changed-worker-after-check"
        run = self.root / "runs" / name
        worker_dir = run / "workspaces" / "attempts"
        check = (
            "from pathlib import Path; root = Path(" + repr(str(worker_dir)) + "); "
            "path = next(root.glob('*/worktree/contributions/late.txt')); "
            "path.write_text('changed after delivery check\\n'); print('worker changed after source checks')"
        )
        task = self._task("late")
        run = self._init(self._request([task], checks=[[sys.executable, "-c", check]]), name)
        launch = self._launches(run)[0]
        self._accepted(run, launch, edits={"contributions/late.txt": "accepted contribution\n"}, commit=True)

        completed, finished = self._json_command([
            sys.executable, "-B", str(HARNESS), "finish", "--run", str(run),
        ])
        self.assertEqual(completed.returncode, 2, finished)
        self.assertEqual(finished.get("status"), "CLEANUP_PENDING", finished)
        self.assertTrue(finished.get("delivery_success"), finished)
        self.assertEqual(finished.get("delivery_status"), "SUCCEEDED", finished)
        self.assertEqual(finished["integration"]["outcome"], "applied")
        self.assertEqual(finished.get("cleanup_status"), "cleanup-pending", finished)
        cleanup = finished["workers"][0]["cleanup"]
        self.assertEqual(cleanup.get("status"), "cleanup-pending", cleanup)
        self.assertTrue(cleanup.get("reason"), cleanup)
        worktree = Path(launch["cwd"])
        self.assertTrue(worktree.is_dir())
        self.assertTrue(self._worktree_registered(worktree))

    def test_false_close_success_is_cleanup_pending_without_replaying_delivery(self) -> None:
        run = self._init(self._request(
            [self._task("false-close")], checks=[[sys.executable, "-c", "print('check passed')"]],
        ), "false-close")
        launch = self._launches(run)[0]
        relative = "contributions/false-close.txt"
        expected = "accepted contribution\n"
        self._accepted(run, launch, edits={relative: expected}, commit=True)
        script = (
            "import sys\n"
            f"sys.path.insert(0, {str(HARNESS.parent)!r})\n"
            "import harness\n"
            "original = harness.Run.command\n"
            "def false_close(self, argv, *args, **kwargs):\n"
            "    if len(argv) > 3 and argv[3] == 'close':\n"
            "        return {'status': 'closed', 'removed': True}\n"
            "    return original(self, argv, *args, **kwargs)\n"
            "harness.Run.command = false_close\n"
            f"raise SystemExit(harness.main(['finish', '--run', {str(run)!r}]))\n"
        )
        completed, finished = self._json_command([sys.executable, "-B", "-c", script])
        self.assertEqual(completed.returncode, 2, finished)
        self.assertEqual(finished["status"], "CLEANUP_PENDING", finished)
        self.assertTrue(finished["delivery_success"], finished)
        self.assertEqual(finished["integration"]["outcome"], "applied")
        cleanup = finished["workers"][0]["cleanup"]
        self.assertEqual(cleanup["helper_outcome"], {"status": "closed", "removed": True})
        self.assertEqual(cleanup["status"], "cleanup-pending")
        self.assertIn("postconditions", cleanup["reason"])
        worktree = Path(launch["cwd"])
        self.assertTrue(worktree.is_dir())
        self.assertTrue(self._worktree_registered(worktree))
        self.assertIn(str(worktree), finished["retained_locations"])
        self.assertTrue(Path(cleanup["evidence_manifest"]).is_file())
        self.assertEqual((self.source / relative).read_text(encoding="utf-8"), expected)
        for commit in finished["workers"][0]["delivery"]["commits"]:
            self._git(self.source, "cat-file", "-e", f"{commit}^{{commit}}")
        before = self._git_snapshot(self.source)
        delivery_path = run / "delivery" / "result.json"
        delivery_bytes = delivery_path.read_bytes()
        repeated = self._harness("finish", "--run", str(run), success=False)
        self.assertEqual(repeated["code"], "DELIVERY_ALREADY_FINAL")
        self.assertEqual(delivery_path.read_bytes(), delivery_bytes)
        self.assertEqual(self._git_snapshot(self.source), before)

    def test_cross_worker_symlink_evidence_retains_all_worktrees_before_close(self) -> None:
        first_task, second_task = self._task("evidence-source"), self._task("evidence-owner")
        check = [sys.executable, "-c",
                 "from pathlib import Path; assert Path('contributions/evidence-source.txt').is_file(); "
                 "assert Path('contributions/evidence-owner.txt').is_file()"]
        run = self._init(self._request([first_task, second_task], capacity=2, checks=[check]),
                         "cross-worker-evidence")
        launches = {launch["task"]: launch for launch in self._launches(run)}
        self._complete(run, launches["evidence-source"],
                       edits={"contributions/evidence-source.txt": "source evidence\n"}, commit=True)
        self._complete(run, launches["evidence-owner"],
                       edits={"contributions/evidence-owner.txt": "owner evidence\n"}, commit=True)

        owner_root = Path(launches["evidence-owner"]["cwd"])
        linked_directory = self.root / "external-worker-evidence"
        linked_directory.symlink_to(owner_root, target_is_directory=True)
        owner_evidence = linked_directory / "app.txt"
        self._accept(run, launches["evidence-source"],
                     evidence=[{"path": str(owner_evidence), "sha256": self._sha256(owner_evidence)}])
        self._accept(run, launches["evidence-owner"])

        completed, finished = self._json_command([
            sys.executable, "-B", str(HARNESS), "finish", "--run", str(run),
        ])
        self.assertEqual(completed.returncode, 2, finished)
        self.assertEqual(finished.get("status"), "CLEANUP_PENDING", finished)
        self.assertTrue(finished.get("delivery_success"), finished)
        self.assertEqual(finished.get("cleanup_status"), "cleanup-pending", finished)
        self.assertIn("another worker tree", finished["cleanup"]["reason"])
        for launch in launches.values():
            worktree = Path(launch["cwd"])
            self.assertTrue(worktree.is_dir())
            self.assertTrue(self._worktree_registered(worktree))

    def test_finish_resumes_after_close_without_replaying_delivery_or_worker_evidence(self) -> None:
        task = self._task("resume-close")
        run = self._init(self._request(
            [task], checks=[[sys.executable, "-c", "assert True; print('resume fixture check')"]],
        ), "resume-after-close")
        launch = self._launches(run)[0]
        self._complete(run, launch, edits={"contributions/resume-close.txt": "resume me\n"}, commit=True)
        worker_evidence = Path(launch["cwd"]) / "app.txt"
        self._accept(run, launch, evidence=[{"path": str(worker_evidence), "sha256": self._sha256(worker_evidence)}])

        interrupt_script = self.root / "interrupt-after-close.py"
        interrupt_script.write_text(
            "import sys\n"
            f"sys.path.insert(0, {str(HARNESS.parent)!r})\n"
            "from pathlib import Path\n"
            "import harness\n"
            f"run_path = Path({str(run)!r})\n"
            "original_save = harness.save\n"
            "def interrupt_final_result(path, value):\n"
            "    if Path(path) == run_path / 'result.json':\n"
            "        raise KeyboardInterrupt('fixture interruption after worker close')\n"
            "    return original_save(path, value)\n"
            "harness.save = interrupt_final_result\n"
            "harness.finish(harness.Run(run_path))\n",
            encoding="utf-8",
        )
        interrupted = subprocess.run(
            [sys.executable, "-B", str(interrupt_script)], cwd=self.root, env=self.env,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=120,
        )
        self.assertNotEqual(interrupted.returncode, 0, interrupted.stdout + interrupted.stderr)
        self.assertFalse((run / "result.json").exists())
        delivery_path = run / "delivery" / "result.json"
        delivery_bytes = delivery_path.read_bytes()
        attempt_path = run / "delivery" / "attempt.json"
        attempt_bytes = attempt_path.read_bytes()
        command_paths = sorted(path.name for path in (run / "delivery" / "commands").glob("*.json"))
        self.assertTrue(command_paths)
        worktree = Path(launch["cwd"])
        self.assertFalse(worktree.exists())
        self.assertFalse(self._worktree_registered(worktree))
        evidence_manifest = run / "delivery" / "cleanup" / f"{launch['attempt']}-evidence.json"
        manifest = json.loads(evidence_manifest.read_text(encoding="utf-8"))
        verifier = next(row for row in manifest["files"] if row["purpose"] == "verification-1")
        retained = Path(verifier["retained_path"])
        self.assertEqual(verifier["path_status"], "preserved")
        self.assertTrue(retained.is_file())
        self.assertEqual(self._sha256(retained), verifier["sha256"])

        finished = self._harness("finish", "--run", str(run))
        self.assertEqual(finished.get("status"), "SUCCEEDED", finished)
        self.assertEqual(finished.get("cleanup_status"), "complete", finished)
        self.assertEqual(delivery_path.read_bytes(), delivery_bytes)
        self.assertEqual(attempt_path.read_bytes(), attempt_bytes)
        self.assertEqual(sorted(path.name for path in (run / "delivery" / "commands").glob("*.json")), command_paths)
        self.assertFalse(worktree.exists())
        self.assertFalse(self._worktree_registered(worktree))
        self.assertEqual(finished["workers"][0]["cleanup"]["worktree_path_status"], "removed")

    def test_unknown_launch_replay_does_not_launch_again_and_unconfirmed_result_is_rejected(self) -> None:
        run = self._init(self._request(
            [self._task("one", write_set=[])], workspace="current", mode="report-only", capacity=1,
        ), "unknown-launch")
        launch = self._launches(run)[0]
        before = sorted(path.name for path in (run / "prepared").glob("*.json"))

        repeated = self._dispatch(run)
        self.assertEqual(repeated.get("status"), "NO_NEW_LAUNCH", repeated)
        self.assertEqual(repeated.get("launches"), [])
        self.assertEqual(sorted(path.name for path in (run / "prepared").glob("*.json")), before)

        retry = self._harness(
            "retry", "--run", str(run), "--attempt", launch["attempt"],
            "--reason", "Offline fixture cannot establish that the unknown worker stopped.",
            "--confirmed-stopped", success=False,
        )
        self.assertEqual(retry.get("status"), "BLOCKED", retry)
        self.assertEqual(sorted(path.name for path in (run / "prepared").glob("*.json")), before)
        self.assertEqual(self._dispatch(run).get("status"), "NO_NEW_LAUNCH")

        result_path = self.root / "unconfirmed-result.json"
        self._write_json(result_path, self._result(launch, self._handle(launch)))
        completed, payload = self._json_command([
            sys.executable, "-B", str(HARNESS), "collect", "--run", str(run),
            "--attempt", launch["attempt"], "--result", str(result_path),
        ])
        self.assertNotEqual(completed.returncode, 0, payload)
        self.assertEqual(payload.get("code"), "NATIVE_COLLECTION_REQUIRED", payload)
        blank = self._harness(
            "launched", "--run", str(run), "--attempt", launch["attempt"], "--handle", "", success=False,
        )
        self.assertEqual(blank.get("code"), "NATIVE_HANDLE", blank)
        self.assertFalse((run / "collected" / f"{launch['attempt']}.json").exists())

    def test_collection_rejects_a_mismatched_native_handle(self) -> None:
        run = self._init(self._request(
            [self._task("one", write_set=[])], workspace="current", mode="report-only", capacity=1,
        ), "mismatched-handle")
        launch = self._launches(run)[0]
        handle = self._confirm_launch(run, launch)
        self._worker(run, launch)
        wrong = self._result(launch, "offline-simulated-native:another-attempt")
        result_path = self.root / "mismatched-handle-result.json"
        self._write_json(result_path, wrong)
        completed, payload = self._json_command([
            sys.executable, "-B", str(HARNESS), "collect", "--run", str(run),
            "--attempt", launch["attempt"], "--result", str(result_path),
        ])
        self.assertNotEqual(completed.returncode, 0, payload)
        self.assertEqual(payload.get("code"), "NATIVE_COLLECTION_REQUIRED", payload)
        self.assertNotEqual(wrong["native_handle"], handle)
        self.assertFalse((run / "collected" / f"{launch['attempt']}.json").exists())

    def test_duplicate_collection_and_repeated_finish_are_refused(self) -> None:
        run = self._init(self._request(
            [self._task("readme", write_set=[])], workspace="current", mode="report-only", capacity=1,
        ), "duplicate-collection")
        launch = self._launches(run)[0]
        self._accepted(run, launch)

        duplicate = self._collect(
            run, launch, self._result(launch, self._handle(launch)), name="duplicate", success=False,
        )
        self.assertEqual(duplicate.get("code"), "RESULT_ALREADY_COLLECTED", duplicate)
        finished = self._harness("finish", "--run", str(run))
        self.assertEqual(finished.get("status"), "SUCCEEDED", finished)
        repeated = self._harness("finish", "--run", str(run), success=False)
        self.assertEqual(repeated.get("code"), "DELIVERY_ALREADY_FINAL", repeated)

    def test_interrupted_dispatch_reuses_saved_preparation_without_a_second_claim(self) -> None:
        marker = self._inject_dispatcher_failure_once("start")
        run = self._init(self._request(
            [self._task("resume", write_set=[])], workspace="current", mode="report-only", capacity=1,
        ), "interrupted-dispatch")

        interrupted = self._harness("dispatch", "--run", str(run), success=False)
        self.assertEqual(interrupted.get("code"), "HELPER_FAILED", interrupted)
        self.assertTrue(marker.is_file())
        prepared_paths = list((run / "prepared").glob("*.json"))
        self.assertEqual(len(prepared_paths), 1, prepared_paths)
        prepared_path = prepared_paths[0]
        prepared_bytes = prepared_path.read_bytes()
        prepared = json.loads(prepared_bytes)

        resumed = self._dispatch(run)
        self.assertEqual(resumed.get("status"), "LAUNCH_REQUIRED", resumed)
        self.assertEqual(len(resumed.get("launches", [])), 1, resumed)
        launch = resumed["launches"][0]
        self.assertEqual(launch["attempt"], prepared_path.stem)
        self.assertEqual(launch["cwd"], prepared["launch"]["cwd"])
        self.assertEqual(launch["prompt"], prepared["launch"]["prompt"])
        self.assertEqual(prepared_path.read_bytes(), prepared_bytes)
        self.assertEqual(len(list((run / "prepared").glob("*.json"))), 1)
        self.assertEqual(self._dispatch(run).get("status"), "NO_NEW_LAUNCH")

    def test_partial_collection_retries_report_publication_without_rewriting_evidence(self) -> None:
        marker = self._inject_dispatcher_failure_once("report")
        run = self._init(self._request(
            [self._task("publish", write_set=[])], workspace="current", mode="report-only", capacity=1,
        ), "partial-collection")
        launch = self._launches(run)[0]
        handle = self._confirm_launch(run, launch)
        self._worker(run, launch)
        result = self._result(launch, handle)
        first = self._collect(run, launch, result, name="partial-collection", success=False)
        self.assertEqual(first.get("code"), "HELPER_FAILED", first)
        self.assertTrue(marker.is_file())

        collected_path = run / "collected" / f"{launch['attempt']}.json"
        artifact_path = run / "dispatcher" / "artifacts" / launch["attempt"] / "result.json"
        self.assertTrue(collected_path.is_file())
        self.assertTrue(artifact_path.is_file())
        collected_bytes = collected_path.read_bytes()
        artifact_bytes = artifact_path.read_bytes()
        saved = json.loads(collected_bytes)
        self.assertEqual(saved["native_evidence_kind"], "coordinator_attestation")
        self.assertIn("[OFFLINE SIMULATED NATIVE RESULT]", saved["result"]["summary"])

        resumed = self._collect(run, launch, result, name="partial-collection")
        self.assertEqual(resumed.get("status"), "AWAITING_VERIFICATION", resumed)
        self.assertEqual(collected_path.read_bytes(), collected_bytes)
        self.assertEqual(artifact_path.read_bytes(), artifact_bytes)
        self._accept(run, launch)
        finished = self._harness("finish", "--run", str(run))
        self.assertEqual(finished.get("status"), "SUCCEEDED", finished)
        self.assertEqual([item["id"] for item in finished["workers"]], [launch["task"]])

    def test_partial_acceptance_retries_settlement_from_saved_verification(self) -> None:
        marker = self._inject_dispatcher_failure_once("settle")
        run = self._init(self._request(
            [self._task("settle", write_set=[])], workspace="current", mode="report-only", capacity=1,
        ), "partial-acceptance")
        launch = self._launches(run)[0]
        self._complete(run, launch)
        verification_path = self._write_passed_verification(launch)
        verified_path = run / "verified" / f"{launch['attempt']}.json"

        interrupted = self._harness(
            "accept", "--run", str(run), "--attempt", launch["attempt"],
            "--verification", str(verification_path), success=False,
        )
        self.assertEqual(interrupted.get("code"), "HELPER_FAILED", interrupted)
        self.assertTrue(marker.is_file())
        self.assertTrue(verified_path.is_file())
        verified_bytes = verified_path.read_bytes()
        self.assertEqual(json.loads(verified_bytes), json.loads(verification_path.read_bytes()))

        resumed = self._harness(
            "accept", "--run", str(run), "--attempt", launch["attempt"],
            "--verification", str(verification_path),
        )
        self.assertEqual(resumed.get("status"), "RECORDED_STATUS", resumed)
        self.assertEqual(verified_path.read_bytes(), verified_bytes)
        finished = self._harness("finish", "--run", str(run))
        self.assertEqual(finished.get("status"), "SUCCEEDED", finished)
        self.assertEqual([item["id"] for item in finished["workers"]], [launch["task"]])

    def test_rejected_terminal_failure_can_retry_and_finish_uses_current_attempt(self) -> None:
        run = self._init(self._request(
            [self._task("recover", write_set=[])], workspace="current", mode="report-only", capacity=1,
        ), "rejected-then-retried")
        failed_launch = self._launches(run)[0]
        failed_record = self._complete(run, failed_launch, status="FAILED")
        self.assertEqual(failed_record["result"]["status"], "FAILED")

        reject_path = self._write_verification(
            failed_launch,
            passed=False,
            reason="Offline fixture rejected the failed attempt; the next attempt will correct its result.",
        )
        rejected = self._harness(
            "accept", "--run", str(run), "--attempt", failed_launch["attempt"],
            "--verification", str(reject_path),
        )
        self.assertEqual(rejected.get("status"), "RECORDED_STATUS", rejected)
        old_collected = run / "collected" / f"{failed_launch['attempt']}.json"
        old_verified = run / "verified" / f"{failed_launch['attempt']}.json"
        self.assertTrue(old_collected.is_file())
        self.assertTrue(old_verified.is_file())
        old_collected_bytes = old_collected.read_bytes()
        old_verified_bytes = old_verified.read_bytes()

        retry = self._harness(
            "retry", "--run", str(run), "--attempt", failed_launch["attempt"],
            "--reason", "The replacement will return a successful result after correcting the failed fixture.",
            "--confirmed-stopped",
        )
        self.assertNotEqual(retry.get("status"), "BLOCKED", retry)
        recovered_launch = self._launches(run)[0]
        self.assertNotEqual(recovered_launch["attempt"], failed_launch["attempt"])
        packet = self._dispatcher_packet(run, recovered_launch["attempt"])
        self.assertEqual(len(packet.get("prior_attempts", [])), 1, packet)
        prior = packet["prior_attempts"][0]
        self.assertEqual(prior["attempt"], failed_launch["attempt"])
        self.assertEqual(prior["status"], "FAILED")
        self.assertEqual(prior["reason"], json.loads(old_verified_bytes)["reason"])
        self.assertIsNotNone(prior["result"])
        self.assertIsNotNone(prior["verification"])

        self._accepted(run, recovered_launch)
        finished = self._harness("finish", "--run", str(run))
        self.assertEqual(finished.get("status"), "SUCCEEDED", finished)
        self.assertEqual([item["id"] for item in finished["workers"]], ["recover"])
        self.assertEqual(len(finished["workers"]), 1)
        self.assertNotIn(failed_launch["attempt"], [item.get("attempt") for item in finished["workers"]])
        self.assertEqual(old_collected.read_bytes(), old_collected_bytes)
        self.assertEqual(old_verified.read_bytes(), old_verified_bytes)

    def test_early_finish_refuses_unaccepted_worker(self) -> None:
        run = self._init(self._request(
            [self._task("pending")], capacity=1,
            checks=[[sys.executable, "-c", "print('early finish fixture check')"]],
        ), "early-finish")
        self._launches(run)
        blocked = self._harness("finish", "--run", str(run), success=False)
        self.assertEqual(blocked.get("code"), "WORKERS_NOT_ACCEPTED", blocked)
        self.assertFalse((run / "result.json").exists())
        self.assertFalse((run / "delivery").exists())

    def test_missing_or_tampered_collection_and_acceptance_evidence_is_refused(self) -> None:
        run = self._init(self._request(
            [self._task("evidence", write_set=[])], workspace="current", mode="report-only", capacity=1,
        ), "evidence-integrity")
        launch = self._launches(run)[0]
        handle = self._confirm_launch(run, launch)
        self._worker(run, launch)

        missing = self.root / "does-not-exist.txt"
        result = self._result(launch, handle, evidence=[{"path": str(missing), "sha256": "0" * 64}])
        result_path = self.root / "missing-evidence-result.json"
        self._write_json(result_path, result)
        completed, payload = self._json_command([
            sys.executable, "-B", str(HARNESS), "collect", "--run", str(run),
            "--attempt", launch["attempt"], "--result", str(result_path),
        ])
        self.assertNotEqual(completed.returncode, 0, payload)
        self.assertEqual(payload.get("code"), "MISSING_EVIDENCE", payload)

        evidence_path = self.root / "native-evidence.txt"
        evidence_path.write_text("original offline observation\n", encoding="utf-8")
        result["evidence"] = [{"path": str(evidence_path), "sha256": self._sha256(evidence_path)}]
        evidence_path.write_text("tampered observation\n", encoding="utf-8")
        self._write_json(result_path, result)
        completed, payload = self._json_command([
            sys.executable, "-B", str(HARNESS), "collect", "--run", str(run),
            "--attempt", launch["attempt"], "--result", str(result_path),
        ])
        self.assertNotEqual(completed.returncode, 0, payload)
        self.assertEqual(payload.get("code"), "EVIDENCE_CHANGED", payload)

        result["evidence"] = [{"path": str(evidence_path), "sha256": self._sha256(evidence_path)}]
        self._write_json(result_path, result)
        collected = self._harness(
            "collect", "--run", str(run), "--attempt", launch["attempt"], "--result", str(result_path),
        )
        self.assertEqual(collected.get("status"), "AWAITING_VERIFICATION", collected)

        no_proof = self.root / "no-acceptance-proof.json"
        self._write_json(no_proof, {"passed": True, "reason": "No pinned proof supplied.", "evidence": []})
        completed, payload = self._json_command([
            sys.executable, "-B", str(HARNESS), "accept", "--run", str(run),
            "--attempt", launch["attempt"], "--verification", str(no_proof),
        ])
        self.assertNotEqual(completed.returncode, 0, payload)
        self.assertEqual(payload.get("code"), "VERIFICATION_EVIDENCE", payload)

        proof_path = self._verification(launch)
        proof_hash = self._sha256(proof_path)
        proof_path.write_text("tampered independent verification\n", encoding="utf-8")
        bad_proof = self.root / "tampered-acceptance-proof.json"
        self._write_json(bad_proof, {
            "passed": True, "reason": "Offline fixture attempted to accept with changed proof.",
            "evidence": [{"path": str(proof_path), "sha256": proof_hash}],
        })
        completed, payload = self._json_command([
            sys.executable, "-B", str(HARNESS), "accept", "--run", str(run),
            "--attempt", launch["attempt"], "--verification", str(bad_proof),
        ])
        self.assertNotEqual(completed.returncode, 0, payload)
        self.assertEqual(payload.get("code"), "EVIDENCE_CHANGED", payload)
        self.assertFalse((run / "verified" / f"{launch['attempt']}.json").exists())

    def test_failed_worker_cannot_be_accepted(self) -> None:
        run = self._init(self._request(
            [self._task("failure", write_set=[])], workspace="current", mode="report-only", capacity=1,
        ), "failed-worker")
        launch = self._launches(run)[0]
        self._complete(run, launch, status="FAILED")
        blocked = self._harness(
            "accept", "--run", str(run), "--attempt", launch["attempt"],
            "--verification", str(self._write_passed_verification(launch)), success=False,
        )
        self.assertEqual(blocked.get("code"), "RESULT_NOT_ACCEPTABLE", blocked)
        self.assertFalse((run / "verified" / f"{launch['attempt']}.json").exists())

    def _write_passed_verification(self, launch: Mapping[str, Any]) -> Path:
        return self._write_verification(launch, passed=True)

    def _write_verification(
        self,
        launch: Mapping[str, Any],
        *,
        passed: bool,
        reason: str | None = None,
    ) -> Path:
        evidence = self._verification(launch)
        path = self.root / f"verification-{launch['attempt']}-{str(passed).lower()}.json"
        self._write_json(path, {
            "passed": passed,
            "reason": reason or f"Offline fixture independently recorded passed={passed} for {launch['task']}.",
            "evidence": [{"path": str(evidence), "sha256": self._sha256(evidence)}],
        })
        return path

    def test_unconfirmed_semantic_criteria_cannot_be_accepted_as_success(self) -> None:
        run = self._init(self._request(
            [self._task("uncertain", write_set=[])], workspace="current", mode="report-only", capacity=1,
        ), "uncertain-criteria")
        launch = self._launches(run)[0]
        self._complete(run, launch, level="unconfirmable")
        record = json.loads((run / "collected" / f"{launch['attempt']}.json").read_text(encoding="utf-8"))
        self.assertEqual(record["result"]["criteria"][0]["level"], "unconfirmable")
        self.assertEqual(record["native_evidence_kind"], "coordinator_attestation")
        blocked = self._harness(
            "accept", "--run", str(run), "--attempt", launch["attempt"],
            "--verification", str(self._write_passed_verification(launch)), success=False,
        )
        self.assertEqual(blocked.get("code"), "RESULT_NOT_ACCEPTABLE", blocked)

    def test_finish_enforces_required_worker_membership_in_collected_records(self) -> None:
        task_ids = ("member-a", "member-b")
        run = self._init(self._request(
            [self._task(name, write_set=[]) for name in task_ids],
            workspace="current", mode="report-only", capacity=2,
        ), "membership")
        launches = self._launches(run)
        for launch in launches:
            self._accepted(run, launch)
        self.assertEqual({launch["task"] for launch in launches}, set(task_ids))
        removed = run / "collected" / f"{launches[0]['attempt']}.json"
        removed.unlink()
        blocked = self._harness("finish", "--run", str(run), success=False)
        self.assertEqual(blocked.get("code"), "DELIVERY_MEMBERSHIP", blocked)
        self.assertFalse((run / "delivery").exists())
        self.assertFalse((run / "result.json").exists())

    def test_malformed_request_and_overlapping_write_sets_are_refused(self) -> None:
        valid = self._request([self._task("valid")])
        malformed_run = self.root / "runs" / "malformed-request"
        self._write_json(self.root / "malformed-request.json", {**valid, "unrecognized": True})
        completed, payload = self._json_command([
            sys.executable, "-B", str(HARNESS), "init", "--run", str(malformed_run),
            "--request", str(self.root / "malformed-request.json"), "--ask-agent-card", str(ASK_AGENT_CARD),
            "--dispatcher-card", str(DISPATCHER_CARD),
        ])
        self.assertNotEqual(completed.returncode, 0, payload)
        self.assertEqual(payload.get("code"), "REQUEST_FIELDS", payload)
        self.assertFalse(malformed_run.exists())

        overlap = self._request([
            self._task("parent", write_set=["src/"]),
            self._task("child", write_set=["src/child.txt"]),
        ])
        overlap_run = self.root / "runs" / "overlapping-write-sets"
        self._write_json(self.root / "overlap-request.json", overlap)
        completed, payload = self._json_command([
            sys.executable, "-B", str(HARNESS), "init", "--run", str(overlap_run),
            "--request", str(self.root / "overlap-request.json"), "--ask-agent-card", str(ASK_AGENT_CARD),
            "--dispatcher-card", str(DISPATCHER_CARD),
        ])
        self.assertNotEqual(completed.returncode, 0, payload)
        self.assertEqual(payload.get("code"), "TASK_SCOPE_OVERLAP", payload)
        self.assertFalse(overlap_run.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
