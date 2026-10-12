#!/usr/bin/env python3
"""Real-Git boundary comparisons for direct Ask Agent and In Parallel.

Every worker and native result in this file is an offline fixture simulation.
The direct Ask Agent path stops at verified return; only In Parallel runs its
own delivery contract after accepting the simulated result.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
ASK_AGENT_CARD = ROOT / "skills/ask-agent/SKILL.md"
ASK_AGENT_TASK = ROOT / "skills/ask-agent/scripts/ask_agent_task.py"
DISPATCHER_CARD = ROOT / "skills/plan-dispatcher/SKILL.md"
HARNESS = ROOT / "skills/in-parallel/scripts/harness.py"
HARNESS_CARD = ROOT / "skills/in-parallel/SKILL.md"

_FIXTURE_SPEC = importlib.util.spec_from_file_location(
    "agent_harness_offline_fixtures", ROOT / "test/agent-harness.test.py"
)
assert _FIXTURE_SPEC is not None and _FIXTURE_SPEC.loader is not None
_FIXTURES = importlib.util.module_from_spec(_FIXTURE_SPEC)
_FIXTURE_SPEC.loader.exec_module(_FIXTURES)

_PACKAGE_BUILD_SPEC = importlib.util.spec_from_file_location(
    "in_parallel_package_build", ROOT / "test/package_build.py"
)
assert _PACKAGE_BUILD_SPEC is not None and _PACKAGE_BUILD_SPEC.loader is not None
_PACKAGE_BUILD = importlib.util.module_from_spec(_PACKAGE_BUILD_SPEC)
_PACKAGE_BUILD_SPEC.loader.exec_module(_PACKAGE_BUILD)


class InParallelCompositionTests(unittest.TestCase):
    """Reuse fixture helpers explicitly without inheriting their test cases."""

    setUp = _FIXTURES.AgentHarnessOfflineContractTests.setUp
    _git = _FIXTURES.AgentHarnessOfflineContractTests._git
    _write_json = _FIXTURES.AgentHarnessOfflineContractTests._write_json
    _json_command = _FIXTURES.AgentHarnessOfflineContractTests._json_command
    _harness = _FIXTURES.AgentHarnessOfflineContractTests._harness
    _task = _FIXTURES.AgentHarnessOfflineContractTests._task
    _request = _FIXTURES.AgentHarnessOfflineContractTests._request
    _init = _FIXTURES.AgentHarnessOfflineContractTests._init
    _dispatch = _FIXTURES.AgentHarnessOfflineContractTests._dispatch
    _launches = _FIXTURES.AgentHarnessOfflineContractTests._launches
    _prepared = _FIXTURES.AgentHarnessOfflineContractTests._prepared
    _prepared_command = _FIXTURES.AgentHarnessOfflineContractTests._prepared_command
    _worker = _FIXTURES.AgentHarnessOfflineContractTests._worker
    _handle = _FIXTURES.AgentHarnessOfflineContractTests._handle
    _confirm_launch = _FIXTURES.AgentHarnessOfflineContractTests._confirm_launch
    _result = _FIXTURES.AgentHarnessOfflineContractTests._result
    _collect = _FIXTURES.AgentHarnessOfflineContractTests._collect
    _accept = _FIXTURES.AgentHarnessOfflineContractTests._accept
    _verification = _FIXTURES.AgentHarnessOfflineContractTests._verification
    _sha256 = _FIXTURES.AgentHarnessOfflineContractTests._sha256
    _git_snapshot = _FIXTURES.AgentHarnessOfflineContractTests._git_snapshot
    _make_dirty_parent = _FIXTURES.AgentHarnessOfflineContractTests._make_dirty_parent

    current_learnings = "Fixture context: both routes use separately cloned equivalents."
    authorization = "Fixture authority: perform only the declared offline assignment."

    def _source_pair(self, name: str) -> tuple[Path, Path, dict[str, dict[str, object]]]:
        seed = self.source
        snapshots: dict[str, dict[str, object]] = {}
        roots = (self.root / f"{name}-direct-source", self.root / f"{name}-harness-source")
        for label, source in zip(("direct", "harness"), roots):
            completed = subprocess.run(
                ["git", "clone", "-q", "--shared", str(seed), str(source)],
                cwd=self.root, env=self.env, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, check=False, timeout=60,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self._git(source, "config", "user.name", "In Parallel Composition Test")
            self._git(source, "config", "user.email", "in-parallel@example.invalid")
            self._git(source, "config", "core.excludesFile", self.env.get("HOME", "/dev/null") + "/empty-global-ignore")
            self.source = source
            snapshots[label] = self._make_dirty_parent()

        self.source = seed
        self.assertNotEqual(roots[0], roots[1])
        self.assertNotEqual(
            self._git(roots[0], "rev-parse", "--show-toplevel").stdout,
            self._git(roots[1], "rev-parse", "--show-toplevel").stdout,
        )
        for source in roots:
            self._assert_dirty_source(source)
        for key in ("head", "index_entries", "cached_diff", "status"):
            self.assertEqual(snapshots["direct"][key], snapshots["harness"][key], key)
        return roots[0], roots[1], snapshots

    def _assert_dirty_source(self, source: Path) -> None:
        self.assertEqual((source / ".gitignore").read_text(encoding="utf-8"), "build/\nparent-generated/\n")
        self.assertEqual((source / ".claspignore").read_text(encoding="utf-8"), "node_modules/\nparent-private/**\n")
        self.assertEqual((source / "caller.txt").read_text(encoding="utf-8"),
                         "caller staged layer\ncaller unstaged layer\n")
        self.assertEqual((source / "caller-note.txt").read_text(encoding="utf-8"), "untracked caller input\n")
        self.assertEqual(self._git(source, "show", ":caller.txt").stdout,
                         "caller staged layer\n")
        self.assertIn("caller.txt", self._git(source, "diff", "--cached", "--name-only").stdout)
        self.assertIn("caller.txt", self._git(source, "diff", "--name-only").stdout)
        self.assertIn("caller-note.txt", self._git(source, "status", "--porcelain").stdout)

    def _direct_prepare(
        self, source: Path, task: dict[str, object], *, workspace: str, mode: str, name: str,
    ) -> dict[str, object]:
        request: dict[str, object] = {
            "objective": task["objective"],
            "expected_result": task["expected_result"],
            "source": str(source),
            "workspace": workspace,
            "mode": mode,
            "write_set": task["write_set"],
            "current_learnings": self.current_learnings,
            "authorization": self.authorization,
        }
        if workspace == "worktree":
            request.update({
                "writers_quiescent": True,
                "store": str(self.root / f"{name}-direct-store"),
            })
        elif mode == "edit":
            request["exclusive_writer"] = True

        request_path = self.root / f"{name}-direct-request.json"
        packet_path = self.root / f"{name}-direct-packet.json"
        self._write_json(request_path, request)
        completed, prepared = self._json_command([
            sys.executable, "-B", str(ASK_AGENT_TASK), "prepare",
            "--skill-card", str(ASK_AGENT_CARD),
            "--request", str(request_path), "--packet", str(packet_path),
        ])
        self.assertEqual(completed.returncode, 0, prepared)
        self.assertEqual(prepared.get("status"), "READY_TO_LAUNCH", prepared)
        self.assertTrue(packet_path.is_file())
        return prepared

    def _run_command(self, command: dict[str, object]) -> dict[str, object]:
        completed, result = self._json_command(
            command["argv"], cwd=Path(command["cwd"])
        )
        self.assertEqual(completed.returncode, 0, result)
        return result

    def _run_direct_worker(
        self, prepared: dict[str, object], *, edits: dict[str, str] | None = None, commit: bool = False,
    ) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        commands = prepared["commands"]
        start = self._run_command(commands["worker-start"])
        self.assertEqual(start.get("status"), "WORKER_CONTEXT_READY", start)
        self.assertFalse(start.get("native_lifecycle_verified"), start)
        action = start.get("action_packet")
        self.assertIsInstance(action, dict, start)
        self.assertEqual(action.get("finish_command"), commands["worker-finish"])
        worker_root = Path(commands["worker-start"]["cwd"])
        for relative, contents in (edits or {}).items():
            target = worker_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(contents, encoding="utf-8")
        if commit:
            self.assertTrue(edits)
            self._git(worker_root, "add", "--", *edits.keys())
            self._git(worker_root, "commit", "-q", "-m", "offline direct fixture contribution")
        finish = self._run_command(commands["worker-finish"])
        verified = self._run_command(commands["verify-return"])
        self.assertEqual(finish.get("status"), "READY_FOR_PARENT_ACCEPTANCE", finish)
        self.assertEqual(verified.get("status"), "READY_FOR_PARENT_ACCEPTANCE", verified)
        self.assertEqual(finish.get("command"), "worker-finish")
        self.assertEqual(verified.get("command"), "verify-return")
        self.assertFalse(finish.get("native_lifecycle_verified"), finish)
        self.assertFalse(verified.get("native_lifecycle_verified"), verified)
        return start, finish, verified

    def _run_harness_worker(
        self,
        source: Path,
        task: dict[str, object],
        *,
        workspace: str,
        mode: str,
        name: str,
        edits: dict[str, str] | None = None,
        commit: bool = False,
        check: list[str] | None = None,
    ) -> tuple[Path, dict[str, object], dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
        self.source = source
        checks = [[*check]] if check is not None else []
        request = self._request(
            [task], workspace=workspace, mode=mode, capacity=1, integration="apply",
            checks=checks, current_learnings=self.current_learnings,
            authorization=self.authorization,
        )
        run = self._init(request, name=f"{name}-harness-run")
        launches = self._launches(run)
        self.assertEqual(len(launches), 1, launches)
        launch = launches[0]
        self.assertEqual(launch["task"], task["id"])
        if workspace == "worktree":
            self._assert_inherited_worktree_inputs(Path(launch["cwd"]))
        self._confirm_launch(run, launch)  # An explicit simulated native handle.
        start, finish = self._worker(run, launch, edits=edits, commit=commit)
        self.assertFalse(start.get("native_lifecycle_verified"), start)
        collected = self._collect(run, launch, self._result(launch, self._handle(launch)))
        self.assertEqual(collected.get("status"), "AWAITING_VERIFICATION", collected)
        record_path = run / "collected" / f"{launch['attempt']}.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        self.assertEqual(record.get("native_evidence_kind"), "coordinator_attestation", record)
        self.assertIn("[OFFLINE SIMULATED NATIVE RESULT]", record["result"]["summary"])
        self.assertFalse(record["verified"].get("native_lifecycle_verified"), record)
        self._accept(run, launch)
        finished = self._harness("finish", "--run", str(run))
        self.assertEqual(finished.get("status"), "SUCCEEDED", finished)
        return run, launch, start, finish, record["verified"], finished

    def _assert_same_worker_binding(
        self, direct_prepared: dict[str, object], direct_start: dict[str, object],
        run: Path, launch: dict[str, object], batch_start: dict[str, object],
        direct_source: Path, harness_source: Path, *, workspace: str, mode: str,
    ) -> None:
        batch_prepared = self._prepared(run, launch)
        direct_packet = json.loads(Path(direct_prepared["packet"]["path"]).read_text(encoding="utf-8"))
        batch_packet = json.loads(Path(batch_prepared["packet"]["path"]).read_text(encoding="utf-8"))
        self.assertEqual(direct_packet["workspace"]["route"], workspace)
        self.assertEqual(batch_packet["workspace"]["route"], workspace)
        self.assertEqual(direct_packet["task"]["mode"], mode)
        self.assertEqual(batch_packet["task"]["mode"], mode)
        for packet, source in ((direct_packet, direct_source), (batch_packet, harness_source)):
            self.assertEqual(Path(packet["workspace"]["source"]), source)
            self.assertEqual(packet["task"]["current_learnings"], self.current_learnings)
            self.assertEqual(packet["task"]["authorization"], self.authorization)

        keys = ("objective", "expected_result", "mode", "delivery_mode", "write_set",
                "current_learnings", "authorization")
        direct_task = direct_start["action_packet"]["task"]
        batch_task = batch_start["action_packet"]["task"]
        self.assertEqual({key: direct_task.get(key) for key in keys},
                         {key: batch_task.get(key) for key in keys})
        self.assertEqual(direct_start["action_packet"]["delivery_header"],
                         batch_start["action_packet"]["delivery_header"])
        direct_cwd = direct_prepared["launch"]["cwd"]
        batch_cwd = batch_prepared["launch"]["cwd"]
        self.assertEqual(Path(direct_start["action_packet"]["finish_command"]["cwd"]), Path(direct_cwd))
        self.assertEqual(Path(batch_start["action_packet"]["finish_command"]["cwd"]), Path(batch_cwd))
        normalized_direct = [re.sub(r"\b[0-9a-f]{40}\b", "<commit>", line.replace(direct_cwd, "<workspace>"))
                             for line in direct_start["action_packet"]["instructions"]]
        normalized_batch = [re.sub(r"\b[0-9a-f]{40}\b", "<commit>", line.replace(batch_cwd, "<workspace>"))
                            for line in batch_start["action_packet"]["instructions"]]
        self.assertEqual(normalized_direct, normalized_batch)

    def _return_contract(self, result: dict[str, object], *, workspace: str, mode: str) -> dict[str, object]:
        evidence = result["workspace_evidence"]
        if mode == "ephemeral":
            audit = evidence["ephemeral_audit"]
            return {key: audit.get(key) for key in
                    ("status", "findings_only", "scratch_retained", "changed_paths")}
        if workspace == "current":
            return {key: evidence.get(key) for key in
                    ("status", "changed_paths", "outside_write_set", "write_set", "verdict", "head_moved")}
        inspection = evidence["inspection"]
        delivery = inspection["delivery"]
        return {
            "status": inspection.get("status"),
            "contribution_paths": inspection.get("contribution_paths"),
            "delivery_mode": delivery.get("mode"),
            "commit_paths": delivery.get("commit_paths"),
            "contribution_delivery_paths": delivery.get("contribution_paths"),
            "residual_paths": delivery.get("residual_paths"),
            "commit_count": len(delivery.get("commits", [])),
        }

    def _assert_source_preserved(
        self, source: Path, before: dict[str, object], *, allowed_working_paths: set[str] | frozenset[str] = frozenset(),
    ) -> None:
        after = self._git_snapshot(source)
        for key in ("head", "index_bytes", "index_entries", "cached_diff"):
            self.assertEqual(after[key], before[key], key)
        before_paths = {item[3:] for item in before["status"].split("\0") if item}
        after_paths = {item[3:] for item in after["status"].split("\0") if item}
        self.assertEqual(after_paths - before_paths, allowed_working_paths)
        self.assertEqual((source / ".gitignore").read_text(encoding="utf-8"), "build/\nparent-generated/\n")
        self.assertEqual((source / ".claspignore").read_text(encoding="utf-8"), "node_modules/\nparent-private/**\n")
        self.assertEqual((source / "caller.txt").read_text(encoding="utf-8"),
                         "caller staged layer\ncaller unstaged layer\n")
        self.assertEqual((source / "caller-note.txt").read_text(encoding="utf-8"), "untracked caller input\n")

    def _assert_inherited_worktree_inputs(self, root: Path) -> None:
        self.assertEqual((root / ".gitignore").read_text(encoding="utf-8"), "build/\nparent-generated/\n")
        self.assertEqual((root / ".claspignore").read_text(encoding="utf-8"), "node_modules/\nparent-private/**\n")
        self.assertEqual((root / "caller.txt").read_text(encoding="utf-8"),
                         "caller staged layer\ncaller unstaged layer\n")
        self.assertEqual((root / "caller-note.txt").read_text(encoding="utf-8"), "untracked caller input\n")

    def _compare_case(self, *, name: str, mode: str, workspace: str, write_set: list[str],
                      edits: dict[str, str] | None = None, commit: bool = False,
                      check: list[str] | None = None) -> dict[str, object]:
        direct_source, harness_source, snapshots = self._source_pair(name)
        task = self._task("assignment", write_set=write_set)
        direct_prepared = self._direct_prepare(
            direct_source, task, workspace=workspace, mode=mode, name=name,
        )
        direct_start, direct_finish, direct_verified = self._run_direct_worker(
            direct_prepared, edits=edits, commit=commit,
        )
        run, launch, batch_start, batch_finish, batch_verified, finished = self._run_harness_worker(
            harness_source, task, workspace=workspace, mode=mode, name=name,
            edits=edits, commit=commit, check=check,
        )
        self._assert_same_worker_binding(
            direct_prepared, direct_start, run, launch, batch_start,
            direct_source, harness_source, workspace=workspace, mode=mode,
        )
        self.assertEqual(self._return_contract(direct_finish, workspace=workspace, mode=mode),
                         self._return_contract(batch_finish, workspace=workspace, mode=mode))
        self.assertEqual(self._return_contract(direct_verified, workspace=workspace, mode=mode),
                         self._return_contract(batch_verified, workspace=workspace, mode=mode))
        if workspace == "worktree":
            self._assert_inherited_worktree_inputs(Path(direct_prepared["launch"]["cwd"]))
        return {
            "direct_prepared": direct_prepared, "direct_start": direct_start,
            "direct_finish": direct_finish, "direct_verified": direct_verified,
            "batch_start": batch_start, "batch_finish": batch_finish,
            "batch_verified": batch_verified, "finished": finished,
            "direct_source": direct_source, "harness_source": harness_source,
            "snapshots": snapshots, "run": run, "launch": launch,
        }

    def test_current_report_only_assignment_matches_direct_ask_agent(self) -> None:
        values = self._compare_case(
            name="current-report-only", workspace="current", mode="report-only", write_set=[],
        )
        direct_verified, batch_verified = values["direct_verified"], values["batch_verified"]
        self.assertEqual(self._return_contract(direct_verified, workspace="current", mode="report-only")["changed_paths"], [])
        self.assertEqual(self._return_contract(batch_verified, workspace="current", mode="report-only")["changed_paths"], [])
        self._assert_source_preserved(values["direct_source"], values["snapshots"]["direct"])
        self._assert_source_preserved(values["harness_source"], values["snapshots"]["harness"])

    def test_current_edit_assignment_matches_direct_ask_agent(self) -> None:
        relative = "contributions/assignment.txt"
        contents = "equivalent current edit\n"
        check = [sys.executable, "-c", f"from pathlib import Path; assert Path({relative!r}).read_text() == {contents!r}"]
        values = self._compare_case(
            name="current-edit", workspace="current", mode="edit", write_set=[relative],
            edits={relative: contents}, check=check,
        )
        self.assertEqual(self._return_contract(values["direct_verified"], workspace="current", mode="edit")["changed_paths"], [relative])
        self.assertEqual(self._return_contract(values["batch_verified"], workspace="current", mode="edit")["changed_paths"], [relative])
        for source, baseline in ((values["direct_source"], values["snapshots"]["direct"]),
                                 (values["harness_source"], values["snapshots"]["harness"])):
            self._assert_source_preserved(source, baseline, allowed_working_paths={relative})
            self.assertEqual((source / relative).read_text(encoding="utf-8"), contents)

    def test_worktree_edit_returns_commits_and_batch_delivery_preserves_caller_index(self) -> None:
        relative = "contributions/assignment.txt"
        contents = "equivalent isolated edit\n"
        check = [sys.executable, "-c", f"from pathlib import Path; assert Path({relative!r}).read_text() == {contents!r}"]
        values = self._compare_case(
            name="worktree-edit", workspace="worktree", mode="edit", write_set=[relative],
            edits={relative: contents}, commit=True, check=check,
        )
        direct_prepared = values["direct_prepared"]
        direct_verified = values["direct_verified"]
        batch_verified = values["batch_verified"]
        finished = values["finished"]
        direct_delivery = direct_verified["workspace_evidence"]["inspection"]["delivery"]
        batch_delivery = batch_verified["workspace_evidence"]["inspection"]["delivery"]
        direct_packet = json.loads(Path(direct_prepared["packet"]["path"]).read_text(encoding="utf-8"))
        batch_prepared = self._prepared(values["run"], values["launch"])
        batch_packet = json.loads(Path(batch_prepared["packet"]["path"]).read_text(encoding="utf-8"))
        for delivery in (direct_delivery, batch_delivery):
            self.assertEqual(delivery["mode"], "commits")
            self.assertEqual(delivery["commit_paths"], [relative])
            self.assertEqual(delivery["residual_paths"], [])
            self.assertEqual(len(delivery["commits"]), 1)
        self.assertEqual(direct_delivery["base"], direct_packet["workspace"]["commit_base"])
        self.assertEqual(batch_delivery["base"], batch_packet["workspace"]["commit_base"])
        self.assertTrue(direct_packet["workspace"]["snapshot"]["source_dirty"])
        self.assertTrue(batch_packet["workspace"]["snapshot"]["source_dirty"])
        direct_worker = Path(direct_prepared["launch"]["cwd"])
        direct_commit = direct_delivery["commits"][0]
        batch_commit = batch_delivery["commits"][0]
        self._git(direct_worker, "cat-file", "-e", f"{direct_commit}^{{commit}}")
        self.assertEqual(self._git(direct_worker, "show", "--pretty=format:", "--name-only", direct_commit).stdout.strip(), relative)
        self.assertEqual(finished.get("cleanup_status"), "complete", finished)
        self.assertEqual(finished["integration"]["outcome"], "applied", finished)
        self.assertEqual(finished["integration"]["applied_paths"], [relative], finished)
        self.assertIn(batch_commit, finished["retained_locations"])
        # The direct helper verifies and retains a contribution; integration belongs to its caller.
        self.assertFalse((values["direct_source"] / relative).exists())
        self.assertTrue((values["harness_source"] / relative).is_file())
        batch_worker = Path(batch_packet["workspace"]["root"])
        self.assertFalse(batch_worker.exists())
        registered = self._git(values["harness_source"], "worktree", "list", "--porcelain").stdout.splitlines()
        self.assertNotIn("worktree " + str(batch_worker), registered)
        self.assertNotIn(str(batch_worker), finished["retained_locations"])
        self._git(values["harness_source"], "cat-file", "-e", f"{batch_commit}^{{commit}}")
        self._git(values["harness_source"], "show-ref", "--verify",
                  "refs/heads/" + batch_packet["workspace"]["branch"])
        self._assert_source_preserved(values["direct_source"], values["snapshots"]["direct"])
        self._assert_source_preserved(values["harness_source"], values["snapshots"]["harness"],
                                      allowed_working_paths={relative})
        self.assertEqual((values["harness_source"] / relative).read_text(encoding="utf-8"), contents)

    def test_worktree_ephemeral_findings_are_retained_without_import(self) -> None:
        relative = "scratch/findings.txt"
        contents = "offline fixture finding\n"
        values = self._compare_case(
            name="worktree-ephemeral", workspace="worktree", mode="ephemeral", write_set=["scratch/"],
            edits={relative: contents},
        )
        direct_audit = values["direct_verified"]["workspace_evidence"]["ephemeral_audit"]
        batch_audit = values["batch_verified"]["workspace_evidence"]["ephemeral_audit"]
        for audit in (direct_audit, batch_audit):
            self.assertEqual(audit["status"], "ephemeral-audit")
            self.assertTrue(audit["findings_only"])
            self.assertTrue(audit["scratch_retained"])
            self.assertEqual(audit["changed_paths"], [relative])
        self.assertEqual(values["finished"]["integration"]["outcome"], "not-applicable")
        self.assertEqual(values["finished"].get("cleanup_status"), "not-applicable", values["finished"])
        self.assertFalse(values["finished"]["integration"].get("application_attempted", False))
        for source, baseline in ((values["direct_source"], values["snapshots"]["direct"]),
                                 (values["harness_source"], values["snapshots"]["harness"])):
            self.assertFalse((source / relative).exists())
            self._assert_source_preserved(source, baseline)
        self.assertTrue((Path(values["direct_prepared"]["launch"]["cwd"]) / relative).is_file())
        self.assertTrue(Path(values["launch"]["cwd"]).is_dir())

    def test_generated_in_parallel_package_runs_from_an_unrelated_directory(self) -> None:
        generated = _PACKAGE_BUILD.plugins() / "skill-craft" / "skills"
        public_skill = generated / "in-parallel"
        self.assertTrue((public_skill / "SKILL.md").is_file())
        self.assertFalse((generated / "agent-harness").exists())
        self.assertFalse((generated / "ask-parallel").exists())

        isolated = self.root / "copied-installed-skills"
        isolated.mkdir()
        copied = {}
        for name in ("in-parallel", "ask-agent", "plan-dispatcher"):
            source = generated / name
            target = isolated / name
            self.assertTrue((source / "SKILL.md").is_file(), source)
            shutil.copytree(source, target)
            copied[name] = target

        unrelated = self.root / "unrelated-cwd"
        unrelated.mkdir()
        run = self.root / "runs" / "copied-package"
        request_path = self.root / "copied-package-request.json"
        task = self._task("package-probe", write_set=[])
        self._write_json(request_path, self._request(
            [task], workspace="current", mode="report-only", capacity=1,
        ))
        harness_script = copied["in-parallel"] / "scripts/harness.py"
        init, prepared = self._json_command([
            sys.executable, "-B", str(harness_script), "init", "--run", str(run),
            "--request", str(request_path),
            "--ask-agent-card", str(copied["ask-agent"] / "SKILL.md"),
            "--dispatcher-card", str(copied["plan-dispatcher"] / "SKILL.md"),
        ], cwd=unrelated)
        self.assertEqual(init.returncode, 0, prepared)
        self.assertEqual(prepared.get("status"), "READY", prepared)
        metadata = json.loads((run / "run.json").read_text(encoding="utf-8"))
        for role, name in (("harness", "in-parallel"), ("ask_agent", "ask-agent"),
                           ("dispatcher", "plan-dispatcher")):
            self.assertEqual(Path(metadata["packages"][role]["root"]), copied[name])

        dispatched, launch_result = self._json_command(
            [sys.executable, "-B", str(harness_script), "dispatch", "--run", str(run)], cwd=unrelated,
        )
        self.assertEqual(dispatched.returncode, 0, launch_result)
        self.assertEqual(launch_result.get("status"), "LAUNCH_REQUIRED", launch_result)
        launch = launch_result["launches"][0]
        prepared_path = run / "prepared" / f"{launch['attempt']}.json"
        row = json.loads(prepared_path.read_text(encoding="utf-8"))
        self.assertIn(str(copied["ask-agent"] / "scripts/ask_agent_task.py"), row["commands"]["worker-start"]["argv"])
        start = self._run_command(row["commands"]["worker-start"])
        finish = self._run_command(row["commands"]["worker-finish"])
        verified = self._run_command(row["commands"]["verify-return"])
        self.assertEqual(start.get("status"), "WORKER_CONTEXT_READY", start)
        self.assertEqual(finish.get("status"), "READY_FOR_PARENT_ACCEPTANCE", finish)
        self.assertEqual(verified.get("status"), "READY_FOR_PARENT_ACCEPTANCE", verified)
        self.assertEqual(start["action_packet"]["task"]["mode"], "report-only")
        self.assertFalse(start.get("native_lifecycle_verified"), start)


if __name__ == "__main__":
    unittest.main(verbosity=2)
