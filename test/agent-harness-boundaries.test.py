#!/usr/bin/env python3
"""Offline behavioral tests for Agent Harness trust and delivery boundaries."""

from __future__ import annotations

import importlib.util
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
import os
import selectors
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


FIXTURE_PATH = Path(__file__).with_name("agent-harness.test.py")
SPEC = importlib.util.spec_from_file_location("agent_harness_offline_fixture", FIXTURE_PATH)
assert SPEC is not None and SPEC.loader is not None
fixture_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixture_module)

sys.path.insert(0, str(fixture_module.HARNESS.parent))
try:
    import harness
finally:
    sys.path.pop(0)


class HarnessApiValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="harness-api-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def request(self) -> dict:
        return {"objective": "Inspect the fixture", "source": str(self.root),
                "workspace": "current", "mode": "report-only",
                "tasks": [{"id": "inspect", "objective": "Inspect", "expected_result": "A finding"}]}

    def test_normalization_does_not_mutate_or_alias_caller_inputs(self) -> None:
        request = self.request()
        request["checks"] = [[sys.executable, "-c", "print('check')"]]
        original = deepcopy(request)
        normalized, warnings = harness.normalized_request(request)
        self.assertEqual(request, original)
        self.assertEqual(normalized["capacity"], 1)
        self.assertEqual(warnings, [])
        normalized["tasks"][0]["objective"] = "changed copy"
        normalized["checks"][0].append("changed copy")
        self.assertEqual(request, original)
        request["capacity"] = False
        original = deepcopy(request)
        with self.assertRaises(harness.HarnessError):
            harness.normalized_request(request)
        self.assertEqual(request, original)

    def test_invalid_api_arguments_are_rejected_before_opening_a_run(self) -> None:
        cases = [
            ("accept", {"attempt": "../outside", "verification": str(self.root / "proof.json")}, "ATTEMPT_ID"),
            ("collect", {"attempt": "attempt_1", "result": "relative.json"}, "ARGUMENT_PATH"),
            ("launched", {"attempt": "attempt_1", "handle": []}, "NATIVE_HANDLE"),
            ("retry", {"attempt": "attempt_1", "reason": "retry", "confirmed_stopped": "true"}, "RETRY_CONFIRMATION"),
            ("dispatch", {"capacity": 3}, "COMMAND_ARGUMENTS"),
            ("accept", {"attempt": "attempt_1"}, "COMMAND_ARGUMENTS"),
            ([], {}, "COMMAND"),
        ]
        run = self.root / "not-created"
        for command, arguments, code in cases:
            with self.subTest(command=command, arguments=arguments):
                with self.assertRaises(harness.HarnessError) as caught:
                    harness.execute(command, run=run, **arguments)
                self.assertEqual(caught.exception.record["code"], code)
                self.assertTrue(caught.exception.record["rationale"])
                self.assertTrue(Path(caught.exception.record["reference"]).is_file())
                self.assertFalse(run.exists())

    def test_ambiguous_scopes_are_rejected_before_dispatch(self) -> None:
        for scope in (".", "./file", "dir//file", "dir/./file", "dir//", "file\nname",
                      "C:/outside", "C:outside", "//server/share", "dir\\file"):
            request = self.request()
            request.update(workspace="worktree", mode="edit", writers_quiescent=True, integration="return-only")
            request["tasks"][0]["write_set"] = [scope]
            with self.subTest(scope=scope), self.assertRaises(harness.HarnessError) as caught:
                harness.normalized_request(request)
            self.assertEqual(caught.exception.record["code"], "WRITE_PATH")
        request["tasks"][0]["write_set"] = ["dir"]
        request["tasks"].append({"id": "child", "objective": "Edit child", "expected_result": "Updated child", "write_set": ["dir/file"]})
        with self.assertRaises(harness.HarnessError) as caught:
            harness.normalized_request(request)
        self.assertEqual(caught.exception.record["code"], "TASK_SCOPE_OVERLAP")

    def test_scope_comparisons_respect_component_boundaries(self) -> None:
        from harness_paths import is_write_scope, scope_contains, scopes_overlap
        for scope in ("src/", "src/café.txt", "directory with spaces/file.txt"):
            self.assertTrue(is_write_scope(scope), scope)
        for left, right, overlaps in (("src/", "src/café.txt", True),
                                      ("src", "src/child/file.txt", True),
                                      ("src/", "src-other/file.txt", False)):
            self.assertEqual(scopes_overlap(left, right), overlaps)
            self.assertEqual(scopes_overlap(right, left), overlaps)
            self.assertEqual(scope_contains(left, right), overlaps)

    def test_malformed_evidence_produces_structured_refusals(self) -> None:
        for item in ({"path": [], "sha256": "0" * 64}, {"path": str(self.root / "proof"), "sha256": []}):
            with self.subTest(item=item), self.assertRaises(harness.HarnessError):
                harness.evidence(item)

    def test_cli_syntax_errors_are_json_and_do_not_touch_run(self) -> None:
        run = self.root / "not-created"
        for arguments in (["dispatch"], ["dispatch", "--run", str(run), "--extra"],
                          ["dispatch", "--ru", str(run)]):
            with self.subTest(arguments=arguments):
                completed = subprocess.run([sys.executable, "-B", str(fixture_module.HARNESS), *arguments],
                                           text=True, capture_output=True, check=False)
                self.assertEqual(completed.returncode, 2)
                result = json.loads(completed.stderr)
                self.assertEqual(result["code"], "COMMAND_ARGUMENTS")
                self.assertEqual(completed.stdout, "")
                self.assertFalse(run.exists())


class AgentHarnessBoundaryTests(unittest.TestCase):
    """Exercise only adversarial boundaries using the existing offline fixture."""

    def setUp(self) -> None:
        self.fixture = fixture_module.AgentHarnessOfflineContractTests(
            "test_current_report_only_reserves_three_read_only_launches_and_status_is_read_only"
        )
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.assertFalse(
            any(name.startswith("GIT_CONFIG_") for name in self.fixture.env),
            "the isolated fixture must not inject Git configuration overrides",
        )

    def test_utf8_request_and_helper_json_do_not_depend_on_locale(self) -> None:
        f = self.fixture
        request = f._request([f._task("inspect", write_set=[])], workspace="current", mode="report-only")
        request["objective"] = "Inspect résumé 東京"
        request["tasks"][0]["objective"] = request["objective"]
        path = f.root / "locale-request.json"
        path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        run = f.root / "runs" / "locale-run"
        env = {**f.env, "LC_ALL": "C", "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0"}
        for arguments in (
            ["init", "--run", str(run), "--request", str(path),
             "--ask-agent-card", str(fixture_module.ASK_AGENT_CARD),
             "--dispatcher-card", str(fixture_module.DISPATCHER_CARD)],
            ["dispatch", "--run", str(run)],
        ):
            result = subprocess.run([sys.executable, "-B", str(fixture_module.HARNESS), *arguments],
                                    env=env, cwd=f.root, capture_output=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
        self.assertEqual(len(output["launches"]), 1)
        self.assertIn(request["objective"], output["launches"][0]["prompt"])

    def test_unicode_and_spaced_paths_survive_delivery_and_cleanup(self) -> None:
        f = self.fixture
        f.source = f.source.rename(f.root / "workspace café [draft]")
        relative = "notes/résumé.txt"
        expected = "verified Unicode contribution\n"
        check = [sys.executable, "-B", "-c",
                 f"from pathlib import Path; assert Path({relative!r}).read_text(encoding='utf-8') == {expected!r}"]
        run = f._init(f._request([f._task("unicode", write_set=[relative])], checks=[check]),
                      "run with spaces")
        launch, = f._launches(run)
        f._accepted(run, launch, edits={relative: expected}, commit=True)
        finished = f._harness("finish", "--run", str(run))
        self.assertEqual(finished["status"], "SUCCEEDED", finished)
        self.assertEqual(finished["cleanup_status"], "complete", finished)
        self.assertEqual((f.source / relative).read_text(encoding="utf-8"), expected)
        self.assertFalse(Path(launch["cwd"]).exists())

    def test_python_api_and_cli_share_state_and_lock_semantics(self) -> None:
        f = self.fixture
        request = f.root / "api-request.json"
        f._write_json(request, f._request([f._task("inspect", write_set=[])], workspace="current", mode="report-only"))
        run = f.root / "runs" / "api-run"
        output = io.StringIO()
        with patch.dict(os.environ, f.env, clear=True), redirect_stdout(output):
            initialized = harness.execute("init", run=run, request=request,
                                          ask_agent_card=fixture_module.ASK_AGENT_CARD,
                                          dispatcher_card=fixture_module.DISPATCHER_CARD)
            self.assertEqual(initialized["status"], "READY")
            before = {str(p.relative_to(run)): p.read_bytes() for p in run.rglob("*") if p.is_file()}
            observed = harness.execute("status", run=run)
            self.assertEqual(observed["status"], "RECORDED_STATUS")
            self.assertEqual(before, {str(p.relative_to(run)): p.read_bytes() for p in run.rglob("*") if p.is_file()})
            selected = harness.Run(run)
            with selected.lock(), self.assertRaises(harness.HarnessError) as caught:
                harness.execute("dispatch", run=run)
            self.assertEqual(caught.exception.record["code"], "OPERATION_BUSY")
            launched = harness.execute("dispatch", run=run)
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(len(launched["launches"]), 1)
        self.assertEqual(f._dispatch(run)["launches"], [])
        self.assertEqual(f._harness("status", "--run", str(run))["progress"], launched["progress"])

    def test_nonobject_criteria_never_publish_a_collection(self) -> None:
        f = self.fixture
        run = f._init(f._request([f._task("inspect", write_set=[])], workspace="current", mode="report-only"), "malformed-criteria")
        launch = f._launches(run)[0]
        handle = f._confirm_launch(run, launch)
        result = f._result(launch, handle)
        result["criteria"].append(None)
        before_calls = set((run / "calls").iterdir())
        response = f._collect(run, launch, result, success=False)
        self.assertEqual(response["code"], "CRITERIA_MISMATCH")
        self.assertEqual(before_calls, set((run / "calls").iterdir()))
        self.assertFalse((run / "collected" / f"{launch['attempt']}.json").exists())

    def test_concurrent_process_dispatch_is_locked_and_never_duplicates_preparation(self) -> None:
        f = self.fixture
        run = f._init(f._request([f._task("one", write_set=[])], workspace="current",
                                mode="report-only", capacity=1), "concurrent-dispatch")
        # Pause the first real dispatch after execute() acquires its lock. A pipe
        # handshake fixes the interleaving without depending on process speed.
        script = (
            "import json, sys\n"
            f"sys.path.insert(0, {str(fixture_module.HARNESS.parent)!r})\n"
            "import harness\n"
            "original = harness.Run.command\n"
            "paused = False\n"
            "def command(self, *args, **kwargs):\n"
            "    global paused\n"
            "    if not paused:\n"
            "        paused = True\n"
            "        print('dispatch-entered', flush=True)\n"
            "        assert sys.stdin.readline() == 'release\\n'\n"
            "    return original(self, *args, **kwargs)\n"
            "harness.Run.command = command\n"
            f"print(json.dumps(harness.execute('dispatch', run={str(run)!r})))\n"
        )
        first = subprocess.Popen([sys.executable, "-B", "-c", script], cwd=f.root, env=f.env,
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, encoding="utf-8")
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(first.stdout, selectors.EVENT_READ)
                self.assertTrue(selector.select(timeout=15), "First dispatch did not reach the barrier")
            self.assertEqual(first.stdout.readline().strip(), "dispatch-entered")
            before = {str(p.relative_to(run)): p.read_bytes() for p in run.rglob("*") if p.is_file()}
            second = f._harness("dispatch", "--run", str(run), success=False)
            self.assertEqual(second["code"], "OPERATION_BUSY", second)
            self.assertEqual(before, {str(p.relative_to(run)): p.read_bytes()
                                      for p in run.rglob("*") if p.is_file()})
            stdout, stderr = first.communicate("release\n", timeout=120)
            self.assertEqual(first.returncode, 0, stderr)
            launches = json.loads(stdout)["launches"]
            self.assertEqual(len(launches), 1)
            self.assertEqual(launches[0]["task"], "one")
            self.assertEqual(len(list((run / "prepared").glob("*.json"))), 1)
            self.assertEqual(f._dispatch(run)["launches"], [])
        finally:
            if first.poll() is None:
                first.kill()
            first.communicate(timeout=15)

    def test_shared_report_only_mutation_is_rejected_before_acceptance(self) -> None:
        f = self.fixture
        tasks = [f._task(name, write_set=[]) for name in ("reader-a", "reader-b")]
        run = f._init(f._request(
            tasks, workspace="current", mode="report-only", capacity=2, integration="apply",
        ), "shared-report-only-mutation")
        launches = f._launches(run)
        self.assertEqual(len(launches), 2)
        self.assertEqual({item["cwd"] for item in launches}, {str(f.source)})

        handles = {}
        for launch in launches:
            handles[launch["task"]] = f._confirm_launch(run, launch)
            started = f._prepared_command(f._prepared(run, launch), "worker-start")
            self.assertEqual(started.get("status"), "WORKER_CONTEXT_READY", started)

        # Both workers have frozen the same parent snapshot. A changes that
        # shared checkout after start, so B's report would be based on tainted input.
        (f.source / "app.txt").write_text("worker A mutation\n", encoding="utf-8")
        self.assertEqual((f.source / "app.txt").read_text(encoding="utf-8"), "worker A mutation\n")

        for launch in launches:
            prepared = f._prepared(run, launch)
            for name in ("worker-finish", "verify-return"):
                command = prepared["commands"][name]
                completed, response = f._json_command(command["argv"], cwd=Path(command["cwd"]))
                self.assertNotEqual(completed.returncode, 0, (name, response))
                self.assertEqual(response.get("error", {}).get("code"), "scope_drift", (name, response))

            # The second worker can report what it observed, but collect repeats
            # verify-return and the coordinator cannot accept it on the changed tree.
            result = f._result(
                launch,
                handles[launch["task"]],
                status="SUCCEEDED",
            )
            result["summary"] = (
                "[OFFLINE SIMULATED NATIVE RESULT] reader observed worker A mutation."
                if launch["task"] == "reader-b"
                else "[OFFLINE SIMULATED NATIVE RESULT] worker-finish detected shared-source drift."
            )
            packet = f._dispatcher_packet(run, launch["attempt"])
            collected = f._collect(run, launch, result)
            self.assertEqual(collected.get("status"), "AWAITING_VERIFICATION", collected)
            record = json.loads((run / "collected" / f"{launch['attempt']}.json").read_text(encoding="utf-8"))
            self.assertEqual(record["result"]["status"], "FAILED", record)
            self.assertIsNone(record["verified"], record)
            self.assertFalse(collected["filesystem_verified"], collected)
            self.assertIn("scope_drift", json.dumps(record["result"].get("filesystem_failure")), record)

            envelope_path = Path(packet["outputs"]["envelope"])
            artifact_path = Path(packet["outputs"]["artifact"])
            envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
            self.assertEqual(envelope["evidence"]["path"], str(artifact_path))
            report_calls = []
            for call_path in (run / "calls").glob("*.json"):
                call = json.loads(call_path.read_text(encoding="utf-8"))
                argv = call.get("argv", [])
                if len(argv) > 4 and argv[2] == "report":
                    report_calls.append(argv)
            self.assertTrue(report_calls, "collect should publish a Dispatcher report")
            self.assertIn(str(envelope_path), [argv[-1] for argv in report_calls])

            proof = f._verification(launch)
            verification = f.root / f"verification-{launch['attempt']}.json"
            f._write_json(verification, {
                "passed": True,
                "reason": "The fixture tries acceptance after the return check reports drift.",
                "evidence": [{"path": str(proof), "sha256": f._sha256(proof)}],
            })
            rejected = f._harness(
                "accept", "--run", str(run), "--attempt", launch["attempt"],
                "--verification", str(verification), success=False,
            )
            self.assertEqual(rejected.get("code"), "RESULT_NOT_ACCEPTABLE", rejected)

    def test_todo_evidence_can_support_only_coordinator_attested_semantics(self) -> None:
        f = self.fixture
        launch_task = f._task("semantic-claim", write_set=[])
        run = f._init(f._request(
            [launch_task], workspace="current", mode="report-only", capacity=1, integration="apply",
        ), "coordinator-attested-semantics")
        launch = f._launches(run)[0]
        handle = f._confirm_launch(run, launch)
        f._worker(run, launch)

        todo = f._verification(launch, contents="TODO: the semantic claim was not independently proven.\n")
        evidence = [{"path": str(todo), "sha256": f._sha256(todo)}]
        result = f._result(launch, handle, status="SUCCEEDED", evidence=evidence)
        result["summary"] = "[OFFLINE SIMULATED NATIVE RESULT] semantic claim marked confirmed by coordinator."
        collected = f._collect(run, launch, result)
        self.assertEqual(collected.get("status"), "AWAITING_VERIFICATION", collected)
        record = json.loads((run / "collected" / f"{launch['attempt']}.json").read_text(encoding="utf-8"))
        self.assertEqual(record["native_evidence_kind"], "coordinator_attestation")
        self.assertEqual(record["result"]["evidence"], evidence)
        self.assertIn("TODO", todo.read_text(encoding="utf-8"))

        accepted = f._accept(run, launch)
        self.assertEqual(accepted.get("status"), "RECORDED_STATUS", accepted)
        finished = f._harness("finish", "--run", str(run))
        self.assertEqual(finished.get("status"), "SUCCEEDED", finished)
        self.assertEqual(
            finished.get("native_lifecycle"),
            "coordinator-attested; experiment host traces are separate evidence",
        )

    def test_parent_drift_blocks_import_and_delivery_outcome_cannot_be_replayed(self) -> None:
        f = self.fixture
        run = f._init(f._request([f._task("drifted-return")], checks=[[sys.executable, "-c", "assert True"]]), "parent-drift-one-attempt")
        launch = f._launches(run)[0]
        f._accepted(run, launch, edits={"contributions/drifted-return.txt": "verified return\n"}, commit=True)

        (f.source / "app.txt").write_text("unrelated parent drift\n", encoding="utf-8")
        first = f._harness("finish", "--run", str(run), success=False)
        self.assertEqual(first.get("status"), "BLOCKED", first)
        first_result_bytes = (run / "result.json").read_bytes()
        delivery_result_bytes = (run / "delivery" / "result.json").read_bytes()
        self.assertEqual(first["integration"].get("applied_paths"), [])
        self.assertFalse((f.source / "contributions" / "drifted-return.txt").exists())
        self.assertIn(first.get("failure", {}).get("code"), {
            "worktree_return_verification_failed", "parent_source_drift",
        })

        (f.source / "app.txt").write_text("base application\n", encoding="utf-8")
        replay = f._harness("finish", "--run", str(run), success=False)
        self.assertEqual(replay.get("code"), "DELIVERY_ALREADY_FINAL", replay)
        self.assertEqual((run / "result.json").read_bytes(), first_result_bytes)
        self.assertEqual((run / "delivery" / "result.json").read_bytes(), delivery_result_bytes)
        self.assertFalse((f.source / "contributions" / "drifted-return.txt").exists())

    def test_parent_checks_detect_unignored_cache_but_allow_ignored_generated_cache(self) -> None:
        f = self.fixture
        ignored_path = "build/generated-cache.txt"
        ignored_check = [
            sys.executable,
            "-c",
            "from pathlib import Path; p=Path('build/generated-cache.txt'); p.parent.mkdir(parents=True, exist_ok=True); p.write_text('cache')",
        ]
        ignored_run = f._init(f._request(
            [f._task("ignored-cache")], checks=[ignored_check],
        ), "ignored-generated-cache")
        ignored_launch = f._launches(ignored_run)[0]
        f._accepted(ignored_run, ignored_launch,
                    edits={"contributions/ignored-cache.txt": "verified return\n"}, commit=True)
        ignored_result = f._harness("finish", "--run", str(ignored_run))
        self.assertEqual(ignored_result.get("status"), "SUCCEEDED", ignored_result)
        self.assertTrue((f.source / ignored_path).is_file())
        self.assertEqual(f._git(f.source, "check-ignore", "-q", ignored_path).returncode, 0)
        self.assertTrue(ignored_result.get("check_postcondition", {}).get("exact_snapshot_unchanged"))
        self.assertEqual(ignored_result["checks"][0]["status"], "PASSED")

        unignored_path = "unignored-cache/generated.txt"
        unignored_check = [
            sys.executable,
            "-c",
            "from pathlib import Path; p=Path('unignored-cache/generated.txt'); p.parent.mkdir(parents=True, exist_ok=True); p.write_text('cache')",
        ]
        unignored_run = f._init(f._request(
            [f._task("unignored-cache")], checks=[unignored_check],
        ), "unignored-generated-cache")
        unignored_launch = f._launches(unignored_run)[0]
        f._accepted(unignored_run, unignored_launch,
                    edits={"contributions/unignored-cache.txt": "verified return\n"}, commit=True)
        completed, failed = f._json_command([
            sys.executable, "-B", str(fixture_module.HARNESS), "finish", "--run", str(unignored_run),
        ])
        self.assertEqual(completed.returncode, 2, failed)
        self.assertEqual(failed.get("status"), "FAILED", failed)
        self.assertEqual(failed.get("failure", {}).get("code"), "post_check_source_drift", failed)
        self.assertEqual(failed.get("check_postcondition", {}).get("changed_paths"), [unignored_path], failed)
        self.assertTrue((f.source / unignored_path).is_file())
        self.assertEqual(f._git(f.source, "check-ignore", "-q", unignored_path, check=False).returncode, 1)


if __name__ == "__main__":
    unittest.main()
