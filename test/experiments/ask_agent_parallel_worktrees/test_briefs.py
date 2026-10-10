"""Focused tests for binding native arguments and parent-only pipeline oracles."""
import json
import shlex
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import briefs
import fixture
import operations


class BriefPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="ask agent packet ")
        cls.run_path = (Path(cls.temp.name) / "fixture run").resolve()
        cls.manifest = fixture.prepare_fixture(
            cls.run_path, 3, "parallel", source_skill=fixture.default_skill_root()
        )
        operations.prepare_batch(cls.run_path)
        cls.manifest_bytes = (cls.run_path / "manifest.json").read_bytes()
        cls.setup_path = cls.run_path / "operator" / "setup-result.json"
        cls.setup_bytes = cls.setup_path.read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        (self.run_path / "manifest.json").write_bytes(self.manifest_bytes)
        self.setup_path.write_bytes(self.setup_bytes)
        (self.run_path / "operator" / "parent-expected.json").unlink(missing_ok=True)
        (self.run_path / "operator" / "dispatch-packet.json").unlink(missing_ok=True)

    def test_packets_bind_each_worker_and_quote_paths_with_spaces(self):
        before = fixture.capture_repo_state(Path(self.manifest["paths"]["caller"]))
        packets = briefs.build_briefs(self.run_path)
        after = fixture.capture_repo_state(Path(self.manifest["paths"]["caller"]))

        self.assertEqual([item["worker_id"] for item in packets], ["1", "2", "3"])
        self.assertEqual(before["index_entries"], after["index_entries"])
        self.assertEqual(before["working_tree"], after["working_tree"])
        setup = json.loads(self.setup_bytes)
        for packet, worker in zip(packets, setup["workers"]):
            self.assertEqual(set(packet), {"worker_id", "native_arguments"})
            args = packet["native_arguments"]
            prompt = args["prompt"]
            self.assertEqual(args["cwd"], worker["worktree"])
            self.assertTrue(args["background"])
            self.assertEqual(set(args), {"description", "prompt", "cwd", "background"})
            self.assertIn(worker["receipt"], prompt)
            package_root = Path(worker["package_identity"]["resolved_skill_card"]).parent
            self.assertIn(str(package_root), prompt)
            self.assertIn("scripts/ask_agent_workspace.py", prompt)
            self.assertIn("Fresh worker;", prompt)
            self.assertIn("do not rely on parent context", prompt)
            self.assertIn("PYTHONDONTWRITEBYTECODE=1 python3 -B", prompt)
            self.assertIn(f"--worker {packet['worker_id']} --phase start", prompt)
            self.assertIn(f"--worker {packet['worker_id']} --phase finish", prompt)
            probe_lines = [line for line in prompt.splitlines() if "probe" in line.lower()
                           and "--phase" in line]
            self.assertEqual(len(probe_lines), 2)
            for phase, line in zip(("start", "finish"), probe_lines):
                tokens = shlex.split(line.split("`", 2)[1])
                self.assertEqual(tokens[:3], ["cd", worker["worktree"], "&&"])
                script_arg = tokens[tokens.index("-B") + 1]
                self.assertEqual((Path(worker["worktree"]) / script_arg).resolve(),
                                 Path(briefs.__file__).with_name("worker_phase.py").resolve())
                self.assertIn(f"--worker {packet['worker_id']} --phase {phase}", line)
                self.assertIn("--run ../../../..", line)
            self.assertIn("--delivery-mode patch", prompt)
            self.assertIn("--artifact .experiment-local/owner.txt", prompt)
            self.assertIn(f"src/step_{packet['worker_id']}.py", prompt)
            self.assertIn("check-context", prompt)
            self.assertIn("assigned check", prompt)
            self.assertLess(prompt.index("Start probe:"), prompt.index("Finish probe:"))
            self.assertIn("integration remains pending", prompt)
        records = list((self.run_path / "operator" / "prepared-inspection-calls").glob("*/worker-*.json"))
        by_attempt = {}
        for path in records:
            by_attempt.setdefault(path.parent, []).append(path)
        complete_attempt = next(paths for paths in by_attempt.values() if len(paths) == 3)
        for path in complete_attempt:
            record = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(record["exit_code"], 0)
            self.assertIn("--phase", record["argv"])
            self.assertEqual(record["argv"][-1], "prepared")
            self.assertNotIn("--delivery-mode", record["argv"])
            self.assertEqual(record["result"]["status"], "prepared")
            self.assertEqual(record["result"]["changed_paths"], [])
            self.assertEqual(record["result"]["contribution_paths"], [])

    def test_current_worker_file_drift_fails_and_retains_helper_output(self):
        setup = json.loads(self.setup_bytes)
        child = Path(setup["workers"][0]["worktree"])
        owned = child / setup["workers"][0]["path"]
        original = owned.read_bytes()
        try:
            owned.write_bytes(original + b"\n# synthetic inspection mutation\n")
            with self.assertRaises(briefs.BriefError) as caught:
                briefs.build_briefs(self.run_path)
            self.assertEqual(caught.exception.code, "WORKER_PREPARED_INSPECTION_FAILED")
            evidence_path = next(path for path in caught.exception.evidence
                                 if "prepared-inspection-calls" in str(path))
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertNotEqual(evidence["exit_code"], 0)
            self.assertTrue(evidence["stdout"] or evidence["stderr"])
        finally:
            owned.write_bytes(original)

    def test_current_worker_index_drift_fails_and_restores_exact_index_bytes(self):
        setup = json.loads(self.setup_bytes)
        child = Path(setup["workers"][0]["worktree"])
        index = Path(fixture.resolve_git_path(child, fixture.git(child, "rev-parse", "--git-path", "index")))
        original_index = index.read_bytes()
        task_path = setup["workers"][0]["path"]
        other_blob = fixture.git(child, "rev-parse", "HEAD:pipeline.py")
        mode = fixture.git(child, "ls-tree", "HEAD", "pipeline.py").split()[0]
        try:
            fixture.git(child, "update-index", "--cacheinfo", mode, other_blob, task_path)
            with self.assertRaises(briefs.BriefError) as caught:
                briefs.build_briefs(self.run_path)
            self.assertEqual(caught.exception.code, "WORKER_PREPARED_INSPECTION_FAILED")
            evidence_path = next(path for path in caught.exception.evidence
                                 if "prepared-inspection-calls" in str(path))
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertNotEqual(evidence["exit_code"], 0)
        finally:
            index.write_bytes(original_index)

    def test_oversized_packet_fails_before_publication(self):
        with self.assertRaises(briefs.BriefError) as caught:
            briefs.publish_dispatch_packet(self.run_path, [{"prompt": "x" * 20_001}])
        self.assertEqual(caught.exception.code, "DISPATCH_PACKET_TOO_LARGE")
        self.assertGreater(caught.exception.observed["packet_bytes"], 20_000)
        self.assertFalse((self.run_path / "operator" / "dispatch-packet.json").exists())

    def test_cli_publishes_exact_stdout_packet_and_refuses_overwrite(self):
        command = [sys.executable, "-B", str(Path(briefs.__file__).resolve()), "--run", str(self.run_path)]
        first = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        packet_path = self.run_path / "operator" / "dispatch-packet.json"
        original = packet_path.read_bytes()
        self.assertEqual(first.stdout.encode("utf-8"), original)
        self.assertEqual(json.loads(first.stdout), json.loads(original))

        second = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(second.returncode, 2)
        self.assertEqual(packet_path.read_bytes(), original)
        diagnostic = json.loads(second.stderr)
        self.assertEqual(diagnostic["code"], "DISPATCH_PACKET_ALREADY_EXISTS")

    def test_fake_shared_root_fails_closed(self):
        setup = json.loads(self.setup_bytes)
        setup["workers"][0]["worktree"] = self.manifest["paths"]["caller"]
        self.setup_path.write_text(json.dumps(setup), encoding="utf-8")

        with self.assertRaises(briefs.BriefError) as caught:
            briefs.build_briefs(self.run_path)

        self.assertEqual(caught.exception.code, "BRIEF_BINDING_INVALID")
        self.assertIn(self.setup_path, caught.exception.evidence)

    def test_missing_identity_field_fails_closed(self):
        setup = json.loads(self.setup_bytes)
        setup["workers"][1]["package_identity"].pop("resolved_helper")
        self.setup_path.write_text(json.dumps(setup), encoding="utf-8")

        with self.assertRaises(briefs.BriefError) as caught:
            briefs.build_briefs(self.run_path)

        self.assertEqual(caught.exception.code, "BRIEF_PACKAGE_IDENTITY_INVALID")
        self.assertEqual(caught.exception.observed["missing_fields"], ["resolved_helper"])

    def test_parent_oracle_matches_independent_three_worker_calculation_and_is_exclusive(self):
        target = Path(self.manifest["paths"]["caller"])
        before = fixture.capture_repo_state(target)
        evidence = briefs.build_parent_oracle(self.run_path)
        oracle_path = self.run_path / "operator" / "parent-expected.json"
        original = oracle_path.read_bytes()
        oracle = json.loads(original)

        self.assertEqual(oracle["inputs"], [-7, -1, 0, 1, 9, 100])
        self.assertEqual(oracle["order"], ["step_1", "step_2", "step_3"])
        self.assertEqual(oracle["formulas"], {"step_1": "2*x+1", "step_2": "3*x+4", "step_3": "4*x+9"})
        self.assertEqual(oracle["closed_form"], "24*x+37")
        self.assertEqual(oracle["expected_outputs"], [-131, 13, 37, 61, 253, 2437])
        self.assertEqual(evidence["sha256"], fixture.sha256_file(oracle_path))
        self.assertEqual(before["working_tree"], fixture.capture_repo_state(target)["working_tree"])
        with self.assertRaises(briefs.BriefError) as caught:
            briefs.build_parent_oracle(self.run_path)
        self.assertEqual(caught.exception.code, "PARENT_ORACLE_ALREADY_EXISTS")
        self.assertEqual(oracle_path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
