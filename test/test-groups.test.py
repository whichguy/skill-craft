#!/usr/bin/env python3
"""Aggregate-test selection must be explicit, host-free and duplicate-free."""

from pathlib import Path
import os
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "test" / "run-all.sh"
CORE = {
    "test-groups", "integration-boundaries", "skill-interop-hygiene",
    "sync-plugin-views", "skill-frontmatter",
    "scaffold-skill", "marketplace-run", "install-targets",
    "install-arbitrary-skill", "hermes-binding", "install-status-uninstall",
    "devloop-run", "evidence-gates", "improve", "improve-plugin", "shiploop-testkit", "review-coverage",
    "dual-body-guard",
}


class TestGroupTests(unittest.TestCase):
    def invoke(self, *args, root=ROOT, env=None):
        return subprocess.run(
            ["bash", str(root / "test" / "run-all.sh"), *args],
            cwd=root, env=env, capture_output=True, text=True, timeout=20,
        )

    def inventory(self, group="all"):
        result = self.invoke("--group", group, "--list")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        rows = [line.split("\t", 2) for line in result.stdout.splitlines()]
        self.assertTrue(rows)
        self.assertTrue(all(len(row) == 3 for row in rows), result.stdout)
        return rows

    def fixture(self):
        temp = tempfile.TemporaryDirectory(prefix="skill-craft-test-groups-")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "test").mkdir()
        shutil.copyfile(RUNNER, root / "test" / "run-all.sh")
        (root / "bin").mkdir()
        # Stub interpreters only in this fixture, never the real suite/runtime.
        for interpreter in ("python3", "node"):
            target = root / "bin" / interpreter
            target.write_text('#!/bin/sh\nexec /bin/bash "$@"\n')
            target.chmod(0o755)
        rows = self.inventory()
        for _, name, command in rows:
            argv = shlex.split(command)
            self.assertIn(argv[0], ("bash", "node", "python3"))
            target = root / argv[1]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                f'#!/bin/sh\nprintf "%s\\n" "{name}" >> "$TEST_TRACE"\n'
                f'[ "${{FAIL_SUITE:-}}" != "{name}" ] || exit 7\n'
            )
        env = dict(os.environ)
        env.update(PATH=f"{root / 'bin'}:{env['PATH']}", TEST_TRACE=str(root / "trace"))
        # A fresh user home prevents installed host state from being a fixture input.
        (root / "empty-home").mkdir()
        env["HOME"] = str(root / "empty-home")
        return root, env

    def test_catalog_is_complete_disjoint_and_host_free(self):
        core = self.inventory("core")
        shiploop = self.inventory("shiploop")
        all_rows = self.inventory()
        self.assertEqual({name for _, name, _ in core}, CORE)
        self.assertEqual([(group, name) for group, name, _ in shiploop], [("shiploop", "shiploop")])
        self.assertEqual(all_rows, core + shiploop)
        names = [name for _, name, _ in all_rows]
        self.assertEqual(len(names), len(set(names)))
        for _, _, command in all_rows:
            self.assertNotIn("weather", command)
            self.assertNotIn("walk-journal", command)
            self.assertNotIn("run-integration", command)
            self.assertNotIn("cursor-imported", command)
        for _, _, command in all_rows:
            self.assertTrue((ROOT / shlex.split(command)[1]).is_file(), command)

    def test_help_and_list_do_not_execute_suites(self):
        root, env = self.fixture()
        for args in (("--list",), ("--help",), ("--group", "core", "--list")):
            with self.subTest(args=args):
                result = self.invoke(*args, root=root, env=env)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse((root / "trace").exists())

    def test_invalid_arguments_fail_before_any_execution(self):
        root, env = self.fixture()
        for args in (("--group",), ("--group", "integration"), ("--wat",), ("core",)):
            with self.subTest(args=args):
                result = self.invoke(*args, root=root, env=env)
                self.assertEqual(result.returncode, 64, result.stdout + result.stderr)
                self.assertFalse((root / "trace").exists())

    def test_default_and_group_selection_execute_each_suite_once(self):
        root, env = self.fixture()
        for group, args in (("all", ()), ("core", ("--group", "core")),
                            ("shiploop", ("--group", "shiploop"))):
            with self.subTest(group=group):
                trace = root / "trace"
                trace.unlink(missing_ok=True)
                result = self.invoke(*args, root=root, env=env)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(trace.read_text().splitlines(), [row[1] for row in self.inventory(group)])

    def test_failure_is_aggregated_without_skipping_later_suites(self):
        root, env = self.fixture()
        env["FAIL_SUITE"] = "test-groups"
        result = self.invoke(root=root, env=env)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL test-groups", result.stderr)
        self.assertNotIn("run-all.sh: PASS", result.stdout)
        self.assertEqual((root / "trace").read_text().splitlines(), [row[1] for row in self.inventory()])

    def test_action_walk_has_one_aggregate_owner(self):
        entrypoint = (ROOT / "test" / "shiploop.test.sh").read_text()
        self.assertEqual(entrypoint.count("test/shiploop-action-walk.test.py"), 1)
        wrapper = (ROOT / "test" / "shiploop-walk-journal.test.sh").read_text()
        self.assertIn("test/shiploop-action-walk.test.py", wrapper)

    def test_ci_preserves_a_fail_closed_aggregate_check(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
        self.assertIn("group: [core, shiploop]", workflow)
        self.assertIn('bash test/run-all.sh --group "${{ matrix.group }}"', workflow)
        self.assertIn("fail-fast: false", workflow)
        self.assertIn("python-version: '3.12'", workflow)
        self.assertIn("node-version: '22'", workflow)
        self.assertIn("always() && matrix.group == 'core'", workflow)
        self.assertIn("git diff --exit-code HEAD", workflow)
        gate = workflow.split("\n  hermetic:\n", 1)[1]
        self.assertIn("if: ${{ always() }}", gate)
        self.assertIn("needs: checks", gate)
        self.assertIn("CHECKS_RESULT: ${{ needs.checks.result }}", gate)
        command = 'test "$CHECKS_RESULT" = success'
        self.assertIn(command, gate)
        for state in ("success", "failure", "cancelled", "skipped", ""):
            result = subprocess.run(["bash", "-c", command], env={"CHECKS_RESULT": state})
            self.assertEqual(result.returncode == 0, state == "success")
        self.assertNotIn("run-integration", workflow)
        self.assertNotIn("secrets.", workflow)

    def test_bootstrap_fixture_pin_does_not_rewrite_the_checkout(self):
        script = (ROOT / "test" / "devloop-run.test.sh").read_text()
        self.assertIn('fixture_pin="$tmpdir/engine-pin-fixture.json"', script)
        self.assertNotIn('fixture_pin="$root/test/fixtures/engine-pin-fixture.json"', script)


if __name__ == "__main__":
    unittest.main()
