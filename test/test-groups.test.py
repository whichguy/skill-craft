#!/usr/bin/env python3
"""Contracts for the declarative hermetic suite catalog and runner."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = ROOT / "test"
sys.path.insert(0, str(TEST_DIR))
import ci_policy  # noqa: E402
import run_suites  # noqa: E402
import suite_catalog  # noqa: E402


class TestGroupTests(unittest.TestCase):
    def invoke_root(self, root: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(root / "test" / "run-all.sh"), *args],
            cwd=root, env=env, capture_output=True, text=True, timeout=30,
        )

    def _copy_runner(self, root: Path) -> None:
        test = root / "test"
        test.mkdir(parents=True)
        for name in ("suite_catalog.py", "run_suites.py", "run-all.sh"):
            shutil.copyfile(TEST_DIR / name, test / name)
        (test / "run-all.sh").chmod(0o755)

    def list_fixture(self) -> tuple[Path, dict[str, str]]:
        temporary = tempfile.TemporaryDirectory(prefix="skill-craft-list-fixture-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "checkout"
        self._copy_runner(root)
        trace = root / "trace"
        env = dict(os.environ, TEST_TRACE=str(trace))
        return root, env

    def execution_fixture(self) -> tuple[Path, dict[str, str], Path]:
        """Create a complete catalog-shaped checkout with harmless test stubs."""

        temporary = tempfile.TemporaryDirectory(prefix="skill-craft-runner-fixture-")
        self.addCleanup(temporary.cleanup)
        parent = Path(temporary.name)
        root = parent / "checkout"
        self._copy_runner(root)
        trace = parent / "trace"
        env = dict(os.environ, TEST_TRACE=str(trace))

        for suite in suite_catalog.SUITES:
            target = root / suite.path
            target.parent.mkdir(parents=True, exist_ok=True)
            if suite.argv[0] == "bash":
                target.write_text(
                    "#!/usr/bin/env bash\n"
                    f"printf '%s\\n' '{suite.id}' >> \"$TEST_TRACE\"\n"
                    f"[[ \"${{FAIL_SUITE:-}}\" != '{suite.id}' ]]\n",
                    encoding="utf-8",
                )
                target.chmod(0o755)
            elif suite.argv[0] == "node":
                target.write_text(
                    "const fs = require('fs');\n"
                    f"fs.appendFileSync(process.env.TEST_TRACE, '{suite.id}\\n');\n"
                    f"process.exit(process.env.FAIL_SUITE === '{suite.id}' ? 7 : 0);\n",
                    encoding="utf-8",
                )
            else:
                target.write_text(
                    "from pathlib import Path\nimport json, os\n"
                    f"with Path(os.environ['TEST_TRACE']).open('a') as stream: stream.write('{suite.id}\\n')\n"
                    f"if os.environ.get('CHECK_RECEIPT_FOR') == '{suite.id}':\n"
                    "    receipt = json.loads(Path(os.environ['CHECK_RECEIPT_PATH']).read_text(encoding='utf-8'))\n"
                    "    assert receipt['status'] == 'running'\n"
                    "    assert len(receipt['completed']) == int(os.environ['CHECK_RECEIPT_COUNT'])\n"
                    "    if receipt['completed']:\n"
                    "        log = Path(os.environ['CHECK_RECEIPT_ROOT']) / receipt['completed'][-1]['stdout_log']\n"
                    "        assert log.is_file()\n"
                    f"raise SystemExit(7 if os.environ.get('FAIL_SUITE') == '{suite.id}' else 0)\n",
                    encoding="utf-8",
                )
        return root, env, parent

    def test_audited_catalog_counts_and_fixed_commands(self) -> None:
        self.assertEqual(len(suite_catalog.SHIPLOOP_SUITES), 44)
        self.assertEqual(len([suite for suite in suite_catalog.SUITES if suite.family == "core"]), 29)
        self.assertEqual(len(suite_catalog.SUITES), 74)
        self.assertTrue(all(suite.hermetic for suite in suite_catalog.SUITES))
        self.assertTrue(all(suite.path in suite.argv for suite in suite_catalog.SUITES))
        self.assertTrue(all(suite.argv[0] in {"python3", "node", "bash"} for suite in suite_catalog.SUITES))
        suite_catalog.validate_catalog()

    def test_full_ci_components_are_the_complete_deduplicated_union(self) -> None:
        full = suite_catalog.select(("all",))
        components = suite_catalog.select((
            "core", "shiploop-1", "shiploop-2", "shiploop-3", "e2e-apparatus",
        ))
        self.assertEqual(components, full)
        self.assertEqual(suite_catalog.select(ci_policy.FULL_GROUPS), full)
        self.assertEqual(len({suite.id for suite in full}), len(full))
        self.assertEqual(full[-1].family, "e2e-apparatus")
        self.assertEqual({suite.family for suite in full}, {"core", "shiploop", "e2e-apparatus"})

    def test_component_unions_are_catalog_ordered_and_current_ask_agent_is_distinct(self) -> None:
        combined = suite_catalog.select(("ask-agent", "shiploop-composition", "ask-agent"))
        self.assertEqual(
            combined,
            tuple(suite for suite in suite_catalog.SUITES if {
                "ask-agent", "shiploop-composition"
            } & suite.groups),
        )
        names = {suite.id for suite in suite_catalog.select(("ask-agent",))}
        self.assertTrue({
            "ask-agent-workspace", "ask-agent-delivery", "ask-agent-managed-harness",
            "experiments-shiploop-chain-native-pilot", "shiploop-chain-handoff",
            "shiploop-chain-async", "shiploop-consumer-delivery",
            "shiploop-consumer-delivery-cli",
        } <= names)
        self.assertNotIn("experiments", suite_catalog.GROUPS)
        with self.assertRaises(ValueError):
            suite_catalog.select(("experiments",))

    def test_lpt_shards_are_disjoint_exhaustive_and_catalog_ordered(self) -> None:
        canonical = suite_catalog.SHIPLOOP_SUITES
        shards = suite_catalog.SHIPLOOP_SHARDS
        self.assertEqual(sum(map(len, shards)), len(canonical))
        self.assertEqual(set().union(*(set(shard) for shard in shards)), set(canonical))
        for shard in shards:
            members = set(shard)
            self.assertEqual(shard, tuple(suite for suite in canonical if suite in members))
        self.assertEqual(sum(
            sum(suite.id == "shiploop-chain-lifecycle" for suite in shard) for shard in shards
        ), 1)

    def test_list_help_and_invalid_arguments_do_not_execute(self) -> None:
        root, env = self.list_fixture()
        for invocation, args, code in (
            (self.invoke_root, ("--list",), 0),
            (self.invoke_root, ("--group", "core", "--list"), 0),
            (self.invoke_root, ("--help",), 0),
            (self.invoke_root, ("--group", "unknown"), 64),
            (self.invoke_root, ("--group", ""), 64),
            (self.invoke_root, ("--group",), 64),
            (self.invoke_root, ("--group", "experiments", "--list"), 64),
            # The retired ShipLoop facade dialect has no hidden spelling left.
            (self.invoke_root, ("--smoke", "--list"), 64),
            (self.invoke_root, ("--shard", "1/3", "--list"), 64),
            (self.invoke_root, ("--shiploop-entrypoint", "--list"), 64),
        ):
            with self.subTest(args=args):
                result = invocation(root, *args, env=env)
                self.assertEqual(result.returncode, code, result.stdout + result.stderr)
                self.assertFalse((root / "trace").exists())

    def test_root_list_is_flattened(self) -> None:
        root, env = self.list_fixture()
        self.assertFalse((TEST_DIR / "shiploop.test.sh").exists())
        listed = self.invoke_root(
            root,
            "--group", "ask-agent",
            "--group", "shiploop-composition",
            "--group", "ask-agent",
            "--list",
            env=env,
        )
        self.assertEqual(listed.returncode, 0, listed.stderr)
        rows = [line.split("\t") for line in listed.stdout.splitlines()]
        self.assertTrue(rows)
        self.assertTrue(all(len(row) == 3 for row in rows), listed.stdout)
        self.assertEqual(
            [row[1] for row in rows],
            [suite.id for suite in suite_catalog.select(("ask-agent", "shiploop-composition", "ask-agent"))],
        )
        self.assertEqual(len(rows), len({row[1] for row in rows}))

    def test_execution_continues_after_failure_and_persists_incremental_receipt(self) -> None:
        root, env, parent = self.execution_fixture()
        output = parent / "receipt"
        env["FAIL_SUITE"] = "ask-agent-workspace"
        env.update(
            CHECK_RECEIPT_FOR="ask-agent-delivery",
            CHECK_RECEIPT_PATH=str(output / "receipt.json"),
            CHECK_RECEIPT_ROOT=str(output),
            CHECK_RECEIPT_COUNT="1",
        )
        selected = suite_catalog.select(("ask-agent",))
        result = self.invoke_root(root, "--group", "ask-agent", "--output", str(output), env=env)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(
            (parent / "trace").read_text(encoding="utf-8").splitlines(),
            [suite.id for suite in selected],
        )
        receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual([record["id"] for record in receipt["selected"]], [suite.id for suite in selected])
        self.assertEqual([record["id"] for record in receipt["completed"]], [suite.id for suite in selected])
        self.assertEqual(receipt["completed"][0]["status"], "failed")
        self.assertTrue((output / receipt["completed"][0]["stdout_log"]).is_file())
        self.assertIn("dirty_diff_sha256", receipt["source"])

    def test_output_must_be_new_and_external_and_coverage_fails_before_execution(self) -> None:
        root, env, parent = self.execution_fixture()
        inside = root / "receipt"
        result = self.invoke_root(root, "--group", "core", "--output", str(inside), env=env)
        self.assertEqual(result.returncode, 64, result.stdout + result.stderr)
        self.assertFalse((parent / "trace").exists())
        self.assertFalse(inside.exists())

        (root / "test" / "unclassified.test.py").write_text("# omitted\n", encoding="utf-8")
        result = self.invoke_root(root, "--group", "core", env=env)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("unclassified top-level test", result.stderr)
        self.assertFalse((parent / "trace").exists())

    def test_timeout_kills_a_child_after_its_leader_exits_but_holds_pipes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-craft-timeout-pipes-") as name:
            root = Path(name)
            program = root / "leader_exits.py"
            program.write_text(textwrap.dedent("""\
                import subprocess
                import sys
                subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
            """), encoding="utf-8")
            started = time.monotonic()
            outcome = run_suites.run_process((sys.executable, str(program)), cwd=root, timeout_seconds=0.1)
            self.assertEqual(outcome.status, "timed_out")
            self.assertLess(time.monotonic() - started, 4)

    def test_timeout_escalates_from_term_to_kill_for_a_real_child(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-craft-timeout-term-") as name:
            root = Path(name)
            program = root / "ignores_term.py"
            program.write_text(textwrap.dedent("""\
                import subprocess
                import sys
                import time
                child = "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)"
                subprocess.Popen([sys.executable, "-c", child])
                time.sleep(60)
            """), encoding="utf-8")
            started = time.monotonic()
            outcome = run_suites.run_process((sys.executable, str(program)), cwd=root, timeout_seconds=0.1)
            self.assertEqual(outcome.status, "timed_out")
            self.assertLess(time.monotonic() - started, 4)

    def test_bootstrap_fixture_pin_does_not_rewrite_the_checkout(self) -> None:
        script = (ROOT / "test" / "devloop-run.test.sh").read_text(encoding="utf-8")
        self.assertIn('fixture_pin="$tmpdir/engine-pin-fixture.json"', script)
        self.assertNotIn('fixture_pin="$root/test/fixtures/engine-pin-fixture.json"', script)


if __name__ == "__main__":
    unittest.main()
