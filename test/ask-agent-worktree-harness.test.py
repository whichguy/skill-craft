#!/usr/bin/env python3
"""Offline tests for the test-only U18 W1 operator guards."""

from __future__ import annotations

import importlib.util
import copy
import contextlib
import io
import json
import os
from pathlib import Path
import sqlite3
import shutil
import sys
import tempfile
import unittest


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = ROOT / "test/experiments/portable_delegation/usability/worktree-handoff/operator/verify-w1.py"
SPEC = importlib.util.spec_from_file_location("verify_w1", HELPER_PATH)
assert SPEC and SPEC.loader
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


class W1HarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="ask-agent-w1-test-")
        self.root = Path(self.tmp.name)
        self.run = self.root / "run"
        self.prompt = self.root / "prompt.md"
        self.skill = self.root / "skill.md"
        self.reference = self.root / "git-integration.md"
        self.prompt.write_text("prompt fixture\n", encoding="utf-8")
        self.skill.write_text("skill fixture\n", encoding="utf-8")
        self.reference.write_text("Git reference fixture\n", encoding="utf-8")
        self.paths = verify.prepare_fixture(self.run, str(self.prompt), str(self.skill), str(self.reference))
        self.source = Path(self.paths["source"])
        self.inbox = Path(self.paths["inbox"])
        self.baseline = Path(self.paths["source_snapshot"])

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_prepare_has_dirty_layers_and_no_worker_worktrees(self) -> None:
        snap = verify.snapshot(self.source)
        self.assertEqual(snap["branch"], "feature")
        self.assertEqual(snap["files"]["dual.txt"]["content_sha256"], verify._sha256(b"staged layer\nunstaged layer\n"))
        self.assertEqual(snap["files"]["staged-add.txt"]["index"]["stage"], 0)
        self.assertEqual(snap["files"]["deleted.txt"]["type"], "missing")
        self.assertIn("notes.txt", snap["untracked_paths"])
        self.assertFalse((self.run / "w1-code-worker").exists())
        self.assertFalse((self.run / "w1-report-worker").exists())

    def test_preflight_rejects_wrong_cwd_and_hash_drift(self) -> None:
        prompt = self.root / "prompt.md"
        skill = self.root / "skill.md"
        prompt.write_text("prompt v1\n", encoding="utf-8")
        skill.write_text("skill v1\n", encoding="utf-8")
        paths = verify.prepare_fixture(self.root / "hash-run", str(prompt), str(skill))
        source = Path(paths["source"])
        launch = {
            "cwd": str(source),
            "project_path": str(source),
            "argv": ["native", "--project", str(source)],
            "prompt_sha256": paths["frozen_prompt_sha256"],
            "skill_sha256": "wrong",
        }
        with self.assertRaises(verify.ContractError) as context:
            verify.preflight(source, self.root / "hash-run" / "paths.json", self.root, launch, prompt=str(prompt), skill=str(skill))
        self.assertIn("parent cwd", str(context.exception))
        launch["skill_sha256"] = "wrong-again"
        with self.assertRaises(verify.ContractError) as context:
            verify.preflight(source, self.root / "hash-run" / "paths.json", source, launch, prompt=str(prompt), skill=str(skill))
        self.assertIn("skill_sha256", str(context.exception))

    def test_preflight_rejects_baseline_drift(self) -> None:
        (self.source / "notes.txt").write_text("changed inherited input\n", encoding="utf-8")
        launch = {
            "cwd": str(self.source),
            "project_path": str(self.source),
            "argv": ["native", "--cwd", str(self.source)],
            "prompt_sha256": self.paths["frozen_prompt_sha256"],
            "skill_sha256": self.paths["frozen_skill_sha256"],
        }
        with self.assertRaises(verify.ContractError) as context:
            verify.preflight(self.source, self.run / "paths.json", self.source, launch, prompt=str(self.prompt), skill=str(self.skill))
        self.assertIn("baseline drift", str(context.exception))

    def _make_db(self) -> Path:
        db = self.root / "opencode.sqlite"
        connection = sqlite3.connect(db)
        connection.executescript(
            """
            CREATE TABLE session (id TEXT PRIMARY KEY, status TEXT, created_at TEXT, metadata TEXT);
            CREATE TABLE message (id TEXT, session_id TEXT, role TEXT, type TEXT, prompt TEXT,
                                  description TEXT, subagent_type TEXT, background INTEGER,
                                  task_id TEXT, created_at TEXT, reasoning TEXT);
            CREATE TABLE part (id TEXT, session_id TEXT, type TEXT, command TEXT,
                               cwd TEXT, file_path TEXT, status TEXT, output TEXT,
                               created_at TEXT, data TEXT);
            INSERT INTO session VALUES ('s1', 'running', '1', '{"secret":"private"}');
            INSERT INTO message VALUES ('m1', 's1', 'user', 'text', 'inspect pricing', 'pricing handoff', 'general', 0, 't1', '2', NULL);
            INSERT INTO message VALUES ('m2', 's1', 'assistant', 'reasoning', NULL, NULL, NULL, 0, NULL, '3', 'hidden reasoning');
            INSERT INTO part VALUES ('p1', 's1', 'tool', 'git status', '/worker', 'pricing.json', 'completed', 'secret output', '4', '{"secret":true}');
            INSERT INTO part VALUES ('p2', 's1', 'reasoning', NULL, '/worker', NULL, 'completed', NULL, '5', NULL);
            """
        )
        connection.commit()
        connection.close()
        return db

    def test_public_opencode_excludes_private_payloads_and_reasoning(self) -> None:
        db = self._make_db()
        output = self.root / "operator" / "public.json"
        output.parent.mkdir()
        result = verify.public_opencode(db, "s1", output, source=str(self.source), worktree=str(self.root / "worker"), inbox=str(self.inbox))
        self.assertEqual(result["status"], "PROJECTED")
        text = output.read_text(encoding="utf-8")
        self.assertIn("inspect pricing", text)
        self.assertIn("git status", text)
        self.assertIn("pricing.json", text)
        for secret in ("private", "hidden reasoning", "secret output", '"secret"'):
            self.assertNotIn(secret, text)
        payload = json.loads(text)
        fields = [record["fields"] for record in payload["records"]]
        self.assertFalse(any("metadata" in item or "output" in item or item.get("type") == "reasoning" for item in fields))

    def test_public_opencode_rejects_output_inside_inbox(self) -> None:
        db = self._make_db()
        with self.assertRaises(verify.ContractError):
            verify.public_opencode(db, "s1", self.inbox / "public.json", source=str(self.source), worktree=str(self.root / "worker"), inbox=str(self.inbox))

    def test_public_opencode_handles_uri_characters_without_creating_another_database(self) -> None:
        db = self._make_db().rename(self.root / "OpenCode #1%?.sqlite")
        original = db.read_bytes()
        before = set(self.root.iterdir())
        output = self.root / "public.json"
        result = verify.public_opencode(db, "s1", output, source=str(self.source), worktree=str(self.root / "worker"), inbox=str(self.inbox))
        self.assertEqual(result["status"], "PROJECTED")
        self.assertEqual(db.read_bytes(), original)
        self.assertEqual(set(self.root.iterdir()) - before, {output})

    def test_public_opencode_projects_installed_json_backed_shape_without_raw_data(self) -> None:
        db = self.root / "opencode-json.sqlite"
        connection = sqlite3.connect(db)
        connection.executescript(
            """
            CREATE TABLE session (id TEXT, parent_id TEXT, directory TEXT, time_created INTEGER, time_updated INTEGER);
            CREATE TABLE message (id TEXT, session_id TEXT, data TEXT);
            CREATE TABLE part (id TEXT, message_id TEXT, data TEXT);
            """
        )
        connection.execute("INSERT INTO session VALUES (?, ?, ?, ?, ?)", ("s-json", None, str(self.source), 10, 20))
        connection.execute(
            "INSERT INTO message VALUES (?, ?, ?)",
            ("m-json", "s-json", json.dumps({"role": "user", "time": {"completed": 30}, "private": "omit-me"})),
        )
        connection.execute(
            "INSERT INTO part VALUES (?, ?, ?)",
            (
                "p-json",
                "m-json",
                json.dumps({
                    "type": "tool",
                    "tool": "task",
                    "state": {"status": "completed", "input": {
                        "prompt": "review worktree",
                        "description": "handoff review",
                        "subagent_type": "general",
                        "background": True,
                        "task_id": "child-1",
                        "command": "git diff",
                        "workdir": str(self.root / "worker"),
                        "filePath": "pricing.json",
                        "private": "omit-me",
                    }},
                    "output": "omit-tool-output",
                }),
            ),
        )
        connection.commit()
        connection.close()
        output = self.root / "operator" / "json-public.json"
        output.parent.mkdir()
        result = verify.public_opencode(
            db,
            "s-json",
            output,
            source=str(self.source),
            worktree=[str(self.root / "code-worker"), str(self.root / "report-worker")],
            inbox=str(self.inbox),
        )
        self.assertEqual(result["status"], "PROJECTED")
        text = output.read_text(encoding="utf-8")
        self.assertIn("review worktree", text)
        self.assertIn("pricing.json", text)
        self.assertIn("time_created", text)
        self.assertIn("time_updated", text)
        self.assertIn("task_id_present", text)
        self.assertNotIn("omit-me", text)
        self.assertNotIn("omit-tool-output", text)
        payload = json.loads(text)
        self.assertFalse(any("data" in record["fields"] for record in payload["records"]))

    def _good_observations(self, *, workers: list[dict] | None = None, events: list[dict] | None = None) -> dict:
        worker_data = workers or [
            {"id": "code-1", "role": "code", "state": "completed", "returned": True, "tool_states": ["completed"], "worktree": str(self.root / "code-worker"), "changed_files": ["pricing.json"], "inbox_prefix": "code", "required_reports": ["reports/handoff-index.md", "reports/validation.md"], "handoff_index": "reports/handoff-index.md"},
            {"id": "report-1", "role": "report", "state": "completed", "returned": True, "tool_states": ["completed"], "worktree": str(self.root / "report-worker"), "changed_files": ["reports/handoff-index.md", "reports/validation.md"], "inbox_prefix": "report", "required_reports": ["reports/handoff-index.md", "reports/validation.md"], "handoff_index": "reports/handoff-index.md"},
        ]
        for worker in worker_data:
            worker["report_sha256"] = {
                name: verify._sha256_file(self.inbox / worker["inbox_prefix"] / name)
                for name in worker["required_reports"]
                if (self.inbox / worker["inbox_prefix"] / name).is_file()
            }
        return {"workers": worker_data, "parent_tool_states": ["completed"], "events": events or [
            {"kind": "worker_terminal", "worker": "code-1", "timestamp": 1.9},
            {"kind": "worker_return", "worker": "code-1", "timestamp": 2},
            {"kind": "reports_archived", "worker": "code-1", "timestamp": 2.5},
            {"kind": "worktree_removed", "worker": "code-1", "timestamp": 2.6},
            {"kind": "worker_terminal", "worker": "report-1", "timestamp": 2.9},
            {"kind": "worker_return", "worker": "report-1", "timestamp": 3},
            {"kind": "reports_archived", "worker": "report-1", "timestamp": 3.5},
            {"kind": "worktree_removed", "worker": "report-1", "timestamp": 3.6},
            {"kind": "parent_final", "status": "finish", "timestamp": 4},
        ], "parent_state": "finished", "registered_worktrees": [
            {"worker_id": "code-1", "path": str(self.root / "code-worker")},
            {"worker_id": "report-1", "path": str(self.root / "report-worker")},
        ]}

    def _make_inbox(self) -> None:
        for role in ("code", "report"):
            for name in ("handoff-index.md", "validation.md"):
                path = self.inbox / role / "reports" / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"{role} {name}\n", encoding="utf-8")

    def _integrate_pricing(self) -> None:
        (self.source / "pricing.json").write_text('{"currency":"USD","base_price":100,"discount_rate":0.10}\n', encoding="utf-8")

    def test_complete_requires_actual_reports_and_parent_after_returns(self) -> None:
        self._make_inbox()
        self._integrate_pricing()
        result = verify.complete_w1(self.source, self.baseline, self._good_observations(), self.inbox)
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["checks"]["parent_final_after_returns"], "PASS")

    def test_finish_stop_with_pending_worker_is_incomplete(self) -> None:
        self._make_inbox()
        self._integrate_pricing()
        workers = self._good_observations()["workers"]
        workers[1]["state"] = "pending"
        workers[1]["returned"] = False
        result = verify.complete_w1(self.source, self.baseline, {"workers": workers, "parent_status": "finish", "events": [{"kind": "parent_final", "status": "stop", "timestamp": 3}]}, self.inbox)
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertTrue(any("finish/stop" in error or "not terminal" in error for error in result["errors"]))

    def test_missing_worker_or_inbox_is_incomplete(self) -> None:
        self._integrate_pricing()
        workers = [self._good_observations()["workers"][0]]
        result = verify.complete_w1(self.source, self.baseline, self._good_observations(workers=workers), self.inbox)
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertTrue(any("report worker" in error or "durable reports" in error for error in result["errors"]))

    def test_unrelated_code_edit_fails_and_removal_before_consumption_is_detected(self) -> None:
        self._make_inbox()
        self._integrate_pricing()
        workers = self._good_observations()["workers"]
        workers[0]["changed_files"] = ["pricing.json", "dual.txt"]
        result = verify.complete_w1(self.source, self.baseline, self._good_observations(workers=workers), self.inbox)
        self.assertEqual(result["status"], "FAILED")
        self.assertTrue(any("changed files" in error for error in result["errors"]))
        (self.inbox / "report" / "reports" / "validation.md").unlink()
        result = verify.complete_w1(self.source, self.baseline, self._good_observations(), self.inbox)
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertTrue(any("durable reports missing" in error for error in result["errors"]))

    def test_removal_before_archival_is_failed_and_report_symlink_escape_is_rejected(self) -> None:
        self._make_inbox()
        self._integrate_pricing()
        observations = self._good_observations()
        events = observations["events"]
        archive_index = next(index for index, event in enumerate(events) if event["kind"] == "reports_archived" and event["worker"] == "code-1")
        remove_index = next(index for index, event in enumerate(events) if event["kind"] == "worktree_removed" and event["worker"] == "code-1")
        events[archive_index], events[remove_index] = events[remove_index], events[archive_index]
        result = verify.complete_w1(self.source, self.baseline, observations, self.inbox)
        self.assertEqual(result["status"], "FAILED")
        self.assertTrue(any("removed before report archival" in error for error in result["errors"]))

        outside = self.root / "outside.md"
        outside.write_text("must not be treated as an inbox report\n", encoding="utf-8")
        link = self.inbox / "code" / "reports" / "handoff-index.md"
        link.unlink()
        link.symlink_to(outside)
        with self.assertRaises(verify.ContractError):
            verify.complete_w1(self.source, self.baseline, self._good_observations(), self.inbox)

    def test_unexpected_source_artifact_fails(self) -> None:
        self._make_inbox()
        self._integrate_pricing()
        (self.source / "unexpected.txt").write_text("bad\n", encoding="utf-8")
        result = verify.complete_w1(self.source, self.baseline, self._good_observations(), self.inbox)
        self.assertEqual(result["status"], "FAILED")
        self.assertTrue(any("unexpected source artifact" in error for error in result["errors"]))

    def test_supported_launch_shapes_and_conflicting_argv(self) -> None:
        common = {"cwd": str(self.source), "project_path": str(self.source),
                  "prompt_sha256": self.paths["frozen_prompt_sha256"],
                  "skill_sha256": self.paths["frozen_skill_sha256"],
                  "reference_sha256": self.paths["frozen_reference_sha256"]}
        for argv, cwd_only in ((["opencode", str(self.source), "--auto"], False),
                               (["codex", "exec", "-C", str(self.source)], False),
                               (["claude", "-p", "prompt"], True),
                               (["grok", "--prompt", "prompt"], True)):
            with self.subTest(argv=argv):
                launch = {**common, "argv": argv, "argv_cwd_only": cwd_only}
                result = verify.preflight(self.source, self.run / "paths.json", self.source, launch,
                                          prompt=str(self.prompt), skill=str(self.skill), reference=str(self.reference))
                self.assertEqual(result["status"], "READY")
        for argv in (["codex", "-C", str(self.root), "--cwd", str(self.source)],
                     ["opencode", str(self.root), "--prompt", str(self.source)]):
            with self.assertRaises(verify.ContractError):
                verify.preflight(self.source, self.run / "paths.json", self.source,
                                 {**common, "argv": argv, "argv_cwd_only": True},
                                 prompt=str(self.prompt), skill=str(self.skill))
        self.skill.write_text("changed frozen skill")
        with self.assertRaises(verify.ContractError):
            verify.preflight(self.source, self.run / "paths.json", self.source,
                             {**common, "argv": ["opencode", str(self.source)]},
                             prompt=str(self.prompt), skill=str(self.skill))

    def test_public_projection_unknown_schema_cannot_pass_on_ids(self) -> None:
        db = self.root / "unknown.sqlite"
        with sqlite3.connect(db) as conn:
            conn.executescript("CREATE TABLE session(id TEXT); INSERT INTO session VALUES('s1');"
                               "CREATE TABLE message(id TEXT, session_id TEXT);"
                               "CREATE TABLE part(id TEXT, session_id TEXT);")
        result = verify.public_opencode(db, "s1", self.root / "public.json", source=str(self.source),
                                        worktree=str(self.root / "worker"), inbox=str(self.inbox))
        self.assertEqual(result["status"], "UNSUPPORTED")

    def test_completion_rejects_missing_returns_and_pending_parent(self) -> None:
        self._make_inbox()
        self._integrate_pricing()
        good = self._good_observations()
        cases = []
        no_returns = copy.deepcopy(good)
        no_returns["events"] = [event for event in no_returns["events"] if event["kind"] != "worker_return"]
        cases.append(no_returns)
        for state in ("running", "stop", "cancelled"):
            cases.append({**good, "parent_state": state})
        cases.append({**good, "parent_tool_states": ["running"]})
        cases.append({**good, "registered_worktrees": []})
        extra = copy.deepcopy(good)
        extra["workers"].append({**extra["workers"][0], "id": "third", "role": "third"})
        cases.append(extra)
        for case in cases:
            with self.subTest(case=cases.index(case)):
                self.assertNotEqual(verify.complete_w1(self.source, self.baseline, case, self.inbox)["status"], "COMPLETE")

    def test_completion_rejects_archive_after_final_and_changed_report(self) -> None:
        self._make_inbox()
        self._integrate_pricing()
        good = self._good_observations()
        final_first = copy.deepcopy(good)
        final = final_first["events"].pop()
        final_first["events"].insert(6, final)
        self.assertNotEqual(verify.complete_w1(self.source, self.baseline, final_first, self.inbox)["status"], "COMPLETE")
        (self.inbox / "code/reports/validation.md").write_text("changed after archival")
        result = verify.complete_w1(self.source, self.baseline, good, self.inbox)
        self.assertTrue(any("hash" in item for item in result["errors"]))

    def test_nonpricing_index_change_and_foreign_baseline_fail(self) -> None:
        self._make_inbox()
        self._integrate_pricing()
        observations = self._good_observations()
        verify._git(self.source, "add", "dual.txt")
        result = verify.complete_w1(self.source, self.baseline, observations, self.inbox)
        self.assertEqual(result["status"], "FAILED")
        baseline = json.loads(self.baseline.read_text())
        baseline["source_checkout"] = str(self.root / "wrong")
        self.baseline.write_text(json.dumps(baseline))
        result = verify.complete_w1(self.source, self.baseline, observations, self.inbox)
        self.assertTrue(any("checkout/root" in error for error in result["errors"]))

    def test_pricing_commit_allowed_but_branch_switch_rejected(self) -> None:
        self._make_inbox()
        self._integrate_pricing()
        verify._git(self.source, "add", "pricing.json")
        verify._git(self.source, "commit", "--only", "-m", "pricing integration", "--", "pricing.json")
        observations = self._good_observations()
        self.assertEqual(verify.complete_w1(self.source, self.baseline, observations, self.inbox)["status"], "COMPLETE")
        verify._git(self.source, "switch", "-c", "wrong-target")
        result = verify.complete_w1(self.source, self.baseline, observations, self.inbox)
        self.assertTrue(any("branch changed" in error for error in result["errors"]))

    def test_vanished_worktree_still_registered_is_not_removed(self) -> None:
        self._make_inbox()
        self._integrate_pricing()
        worker = self.root / "code-worker"
        verify._git(self.source, "worktree", "add", "--detach", str(worker), "HEAD")
        worker.rename(self.root / "orphaned-worker")
        result = verify.complete_w1(self.source, self.baseline, self._good_observations(), self.inbox)
        self.assertTrue(any("remains in current Git registry" in error for error in result["errors"]))

    def test_ignored_source_artifact_is_still_a_preservation_failure(self) -> None:
        self._make_inbox()
        self._integrate_pricing()
        exclude = Path(verify.snapshot(self.source)["git_common_dir"]) / "info/exclude"
        with exclude.open("a") as stream:
            stream.write("\nignored-w1.tmp\n")
        (self.source / "ignored-w1.tmp").write_text("unapproved worker scratch")
        result = verify.complete_w1(self.source, self.baseline, self._good_observations(), self.inbox)
        self.assertEqual(result["status"], "FAILED")
        self.assertTrue(any("ignored-w1.tmp" in error for error in result["errors"]))

    def test_snapshot_does_not_refresh_source_index_bytes(self) -> None:
        index = Path(verify.snapshot(self.source)["git_dir"]) / "index"
        tracked = self.source / "feature.txt"
        info = tracked.stat()
        os.utime(tracked, ns=(info.st_atime_ns, info.st_mtime_ns + 1_000_000_000))
        before = index.read_bytes()
        verify.snapshot(self.source)
        self.assertEqual(index.read_bytes(), before)

    def test_projection_cannot_overwrite_database_or_prior_evidence(self) -> None:
        db = self._make_db()
        original = db.read_bytes()
        for output in (db, self.root / "already-recorded.json"):
            if output != db:
                output.write_text("earlier evidence")
            with self.subTest(output=output), self.assertRaises(verify.ContractError):
                verify.public_opencode(db, "s1", output, source=str(self.source),
                                       worktree=str(self.root / "worker"), inbox=str(self.inbox))
        self.assertEqual(db.read_bytes(), original)
        self.assertEqual((self.root / "already-recorded.json").read_text(), "earlier evidence")

    def test_cli_output_cannot_pollute_participant_checkout(self) -> None:
        self._make_inbox()
        self._integrate_pricing()
        observations = self.root / "observations.json"
        observations.write_text(json.dumps(self._good_observations()))
        output = self.source / "operator-result.json"
        for args in (["snapshot", "--source", str(self.source), "--output", str(output)],
                     ["complete", "--source", str(self.source), "--baseline", str(self.baseline),
                      "--inbox", str(self.inbox), "--observations", str(observations), "--output", str(output)]):
            with self.subTest(command=args[0]):
                with contextlib.redirect_stdout(io.StringIO()) as captured:
                    self.assertEqual(verify.main(args), 2)
                self.assertEqual(json.loads(captured.getvalue())["status"], "FAILED")
                self.assertFalse(output.exists())

    def test_public_task_metadata_stays_with_each_call(self) -> None:
        db = self.root / "calls.sqlite"
        with sqlite3.connect(db) as conn:
            conn.executescript("CREATE TABLE session(id TEXT); INSERT INTO session VALUES('s1');"
                               "CREATE TABLE message(id TEXT, session_id TEXT, data TEXT);"
                               "CREATE TABLE part(id TEXT, session_id TEXT, data TEXT);")
            conn.execute("INSERT INTO message VALUES(?,?,?)", ("m1", "s1", json.dumps({"role": "assistant"})))
            for ident, data in (("a", {"type": "text", "text": "public launch notice"}),
                                ("b", {"type": "tool", "tool": "task", "state": {"status": "completed", "input": {"prompt": "fresh"}}}),
                                ("c", {"type": "tool", "tool": "task", "state": {"status": "completed", "input": {"prompt": "followup", "task_id": "native-child"}}})):
                conn.execute("INSERT INTO part VALUES(?,?,?)", (ident, "s1", json.dumps(data)))
        result = verify.public_opencode(db, "s1", self.root / "calls.json", source=str(self.source),
                                        worktree=str(self.root / "worker"), inbox=str(self.inbox))
        self.assertNotIn("assignment", result)
        self.assertEqual([(call["id"], call["task_id_present"], call.get("task_id")) for call in result["task_calls"]],
                         [("b", 0, None), ("c", 1, "native-child")])

    def test_completion_requires_distinct_index_and_detail_reports(self) -> None:
        self._make_inbox()
        self._integrate_pricing()
        for reports in (["reports/handoff-index.md"], ["reports/handoff-index.md"] * 2):
            observations = self._good_observations()
            for worker in observations["workers"]:
                worker["required_reports"] = reports
            result = verify.complete_w1(self.source, self.baseline, observations, self.inbox)
            self.assertNotEqual(result["status"], "COMPLETE")

    def test_preflight_requires_frozen_git_reference(self) -> None:
        paths = json.loads((self.run / "paths.json").read_text())
        paths["frozen_reference_sha256"] = None
        (self.run / "paths.json").write_text(json.dumps(paths))
        launch = {"cwd": str(self.source), "project_path": str(self.source),
                  "argv": ["opencode", str(self.source)],
                  "prompt_sha256": paths["frozen_prompt_sha256"],
                  "skill_sha256": paths["frozen_skill_sha256"]}
        with self.assertRaises(verify.ContractError):
            verify.preflight(self.source, self.run / "paths.json", self.source, launch,
                             prompt=str(self.prompt), skill=str(self.skill))

    def test_completion_rejects_replaced_git_identity(self) -> None:
        self._make_inbox()
        self._integrate_pricing()
        old_git_dir = Path(verify.snapshot(self.source)["git_dir"])
        alternate = self.root / "alternate.git"
        verify._run(["git", "clone", "--bare", str(self.source), str(alternate)], self.root)
        verify._run(["git", "--git-dir", str(alternate), "config", "core.bare", "false"], self.root)
        verify._run(["git", "--git-dir", str(alternate), "config", "core.worktree", str(self.source)], self.root)
        shutil.copyfile(old_git_dir / "index", alternate / "index")
        (self.source / ".git").write_text(f"gitdir: {alternate}\n")
        result = verify.complete_w1(self.source, self.baseline, self._good_observations(), self.inbox)
        self.assertNotEqual(result["status"], "COMPLETE")
        self.assertTrue(any("Git directory identity" in error for error in result["errors"]))

    def test_duplicate_or_failed_parent_final_cannot_complete(self) -> None:
        self._make_inbox()
        self._integrate_pricing()
        for duplicate in (False, True):
            observations = self._good_observations()
            if duplicate:
                observations["events"].insert(0, {"kind": "parent_final", "status": "failed", "timestamp": 0})
            else:
                observations["events"][-1]["status"] = "failed"
            self.assertNotEqual(verify.complete_w1(self.source, self.baseline, observations, self.inbox)["status"], "COMPLETE")

    def test_event_order_breaks_equal_timestamp_ties(self) -> None:
        self._make_inbox()
        self._integrate_pricing()
        observations = self._good_observations()
        for event in observations["events"]:
            event["timestamp"] = 1
        self.assertEqual(verify.complete_w1(self.source, self.baseline, observations, self.inbox)["status"], "COMPLETE")

    def test_report_changed_file_cannot_traverse_outside_reports(self) -> None:
        self._make_inbox()
        self._integrate_pricing()
        observations = self._good_observations()
        observations["workers"][1]["changed_files"] = ["reports/../dual.txt"]
        self.assertEqual(verify.complete_w1(self.source, self.baseline, observations, self.inbox)["status"], "FAILED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
