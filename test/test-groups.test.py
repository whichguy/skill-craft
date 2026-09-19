#!/usr/bin/env python3
"""Aggregate-test selection must be explicit, host-free and duplicate-free."""

from pathlib import Path
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "test" / "run-all.sh"
SHIPLOOP_RUNNER = ROOT / "test" / "shiploop.test.sh"
SHIPLOOP_SUITE_COUNT = 93
ACTION_WALK = "test/shiploop-action-walk.test.py"
CI_GROUPS = ("core", "shiploop-1", "shiploop-2", "shiploop-3")
SHIPLOOP_SMOKE = (
    "test/shiploop-no-model-launch.test.py",
    "test/shiploop-navigator-v3.test.py",
    "test/shiploop-packet-bounds.test.py",
    "test/shiploop-navigator-dry-run.test.py",
    "test/shiploop-graph-driver.test.py",
    "test/shiploop-graph-trace.test.py",
)
CORE = {
    "test-groups", "integration-boundaries", "ask-agent-worktree-harness", "skill-interop-hygiene",
    "sync-plugin-views", "native-marketplace-adapters", "skill-frontmatter",
    "marketplace-package", "installed-skill-invocation", "prompt-marketplace-contract",
    "marketplace-host-isolation",
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

    def invoke_shiploop(self, *args, root=ROOT, env=None):
        return subprocess.run(
            ["bash", str(root / "test" / "shiploop.test.sh"), *args],
            cwd=root, env=env, capture_output=True, text=True, timeout=20,
        )

    def shiploop_inventory(self, shard=None):
        args = ["--list"]
        if shard is not None:
            args = ["--shard", shard, "--list"]
        result = self.invoke_shiploop(*args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        suites = result.stdout.splitlines()
        self.assertTrue(suites)
        return suites

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
            if name == "shiploop":
                target.write_text(
                    "#!/bin/sh\n"
                    'suite_name="shiploop"\n'
                    'if [ "${1:-}" = "--shard" ]; then suite_name="shiploop-${2%%/*}"; fi\n'
                    'if [ "${1:-}" = "--smoke" ]; then suite_name="shiploop-smoke"; fi\n'
                    'printf "%s\\n" "$suite_name" >> "$TEST_TRACE"\n'
                    '[ "${FAIL_SUITE:-}" != "$suite_name" ] || exit 7\n'
                )
            else:
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

    def shiploop_fixture(self):
        temp = tempfile.TemporaryDirectory(prefix="skill-craft-shiploop-shard-")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "test").mkdir()
        shutil.copyfile(SHIPLOOP_RUNNER, root / "test" / "shiploop.test.sh")
        (root / "bin").mkdir()
        python = root / "bin" / "python3"
        python.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = \"scripts/sync-improve-managed.py\" ]; then\n"
            "  printf '%s\\n' sync >> \"$TEST_TRACE\"\n"
            "  exit 0\n"
            "fi\n"
            "printf '%s\\n' \"$1\" >> \"$TEST_TRACE\"\n"
            "[ \"${FAIL_SUITE:-}\" != \"$1\" ] || exit 7\n"
        )
        python.chmod(0o755)
        node = root / "bin" / "node"
        shutil.copyfile(python, node)
        node.chmod(0o755)
        env = dict(os.environ)
        env.update(PATH=f"{root / 'bin'}:{env['PATH']}", TEST_TRACE=str(root / "trace"))
        return root, env

    def workflow_step(self, workflow, name):
        marker = f"      - name: {name}\n"
        self.assertEqual(workflow.count(marker), 1)
        lines = workflow[workflow.index(marker):].splitlines()
        step = []
        for index, line in enumerate(lines):
            if index and (
                line.startswith("      - ") or
                (line and len(line) - len(line.lstrip()) < 6)
            ):
                break
            step.append(line)
        return "\n".join(step)

    def workflow_run_commands(self, step):
        run_marker = "        run: |\n"
        self.assertIn(run_marker, step)
        commands = []
        for line in step.split(run_marker, 1)[1].splitlines():
            if not line:
                commands.append(line)
            elif line.startswith("          "):
                commands.append(line[10:])
            else:
                break
        self.assertTrue(commands)
        return "\n".join(commands).strip()

    def git(self, root, *args):
        return subprocess.run(
            ["git", *args], cwd=root, check=True, capture_output=True, text=True,
        )

    def git_checkout_fixture(self):
        temp = tempfile.TemporaryDirectory(prefix="skill-craft-ci-guard-")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.git(root, "init", "--quiet")
        self.git(root, "config", "user.email", "test@example.invalid")
        self.git(root, "config", "user.name", "Test User")
        tracked = root / "tracked.txt"
        tracked.write_text("clean\n")
        self.git(root, "add", "tracked.txt")
        self.git(root, "commit", "--quiet", "-m", "initial")
        return root, tracked

    def run_ci_commands(self, root, commands):
        return subprocess.run(
            ["bash", "-e", "-o", "pipefail"],
            cwd=root, input=commands, capture_output=True, text=True, timeout=20,
        )

    def test_catalog_is_complete_disjoint_and_host_free(self):
        core = self.inventory("core")
        shiploop = self.inventory("shiploop")
        shard_rows = [self.inventory(f"shiploop-{index}") for index in range(1, 4)]
        all_rows = self.inventory()
        self.assertEqual({name for _, name, _ in core}, CORE)
        self.assertEqual([(group, name) for group, name, _ in shiploop], [("shiploop", "shiploop")])
        self.assertEqual(
            [
                [(group, name, command.strip()) for group, name, command in rows]
                for rows in shard_rows
            ],
            [
                [(f"shiploop-{index}", f"shiploop-{index}",
                  f"bash test/shiploop.test.sh --shard {index}/3")]
                for index in range(1, 4)
            ],
        )
        self.assertEqual(all_rows, core + shiploop)
        self.assertNotIn("shiploop-1", [group for group, _, _ in all_rows])
        self.assertNotIn("shiploop-2", [group for group, _, _ in all_rows])
        self.assertNotIn("shiploop-3", [group for group, _, _ in all_rows])
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
        for args in (("--list",), ("--help",), ("--group", "core", "--list"),
                     ("--group", "smoke", "--list")):
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
                            ("smoke", ("--group", "smoke")),
                            ("shiploop", ("--group", "shiploop")),
                            ("shiploop-1", ("--group", "shiploop-1")),
                            ("shiploop-2", ("--group", "shiploop-2")),
                            ("shiploop-3", ("--group", "shiploop-3"))):
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

    def test_smoke_includes_core_and_graph_subset_without_full_walk(self):
        smoke = self.inventory("smoke")
        self.assertEqual(smoke[:-1], self.inventory("core"))
        self.assertEqual(smoke[-1][:2], ["smoke", "shiploop-smoke"])
        self.assertEqual(smoke[-1][2].strip(), "bash test/shiploop.test.sh --smoke")
        result = self.invoke_shiploop("--smoke", "--list")
        self.assertEqual(result.returncode, 0, result.stderr)
        selected = result.stdout.splitlines()
        self.assertEqual(selected, list(SHIPLOOP_SMOKE))
        self.assertEqual(selected, [s for s in self.shiploop_inventory() if s in SHIPLOOP_SMOKE])
        self.assertNotIn(ACTION_WALK, selected)
        self.assertNotIn("shiploop-smoke", [name for _, name, _ in self.inventory()])

    def test_smoke_fails_for_either_core_or_graph_failure(self):
        root, env = self.fixture()
        for failure in ("test-groups", "shiploop-smoke"):
            with self.subTest(failure=failure):
                (root / "trace").unlink(missing_ok=True)
                env["FAIL_SUITE"] = failure
                result = self.invoke("--group", "smoke", root=root, env=env)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertNotIn("run-all.sh: PASS", result.stdout)
                self.assertEqual((root / "trace").read_text().splitlines(),
                                 [row[1] for row in self.inventory("smoke")])

    def test_shiploop_smoke_executes_selected_suites_and_propagates_failure(self):
        root, env = self.shiploop_fixture()
        trace = root / "trace"
        result = self.invoke_shiploop("--smoke", root=root, env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(trace.read_text().splitlines(), ["sync", *SHIPLOOP_SMOKE])
        trace.unlink()
        env["FAIL_SUITE"] = SHIPLOOP_SMOKE[1]
        result = self.invoke_shiploop("--smoke", root=root, env=env)
        self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
        self.assertEqual(trace.read_text().splitlines(), ["sync", *SHIPLOOP_SMOKE[:2]])

    def test_shiploop_shards_partition_the_one_canonical_inventory(self):
        source = SHIPLOOP_RUNNER.read_text()
        self.assertEqual(source.count("suites=("), 1)
        canonical = self.shiploop_inventory()
        shards = [self.shiploop_inventory(f"{index}/3") for index in range(1, 4)]
        self.assertEqual(len(canonical), SHIPLOOP_SUITE_COUNT)
        self.assertEqual(len(set(canonical)), SHIPLOOP_SUITE_COUNT)
        self.assertEqual(sum(map(len, shards)), SHIPLOOP_SUITE_COUNT)
        self.assertEqual(set().union(*map(set, shards)), set(canonical))
        for index, shard in enumerate(shards):
            self.assertEqual(shard, canonical[index::3])
        self.assertEqual(canonical.count(ACTION_WALK), 1)
        self.assertEqual(sum(shard.count(ACTION_WALK) for shard in shards), 1)

    def test_shiploop_list_and_invalid_arguments_have_no_side_effects(self):
        temp = tempfile.TemporaryDirectory(prefix="skill-craft-shiploop-list-")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "test").mkdir()
        shutil.copyfile(SHIPLOOP_RUNNER, root / "test" / "shiploop.test.sh")
        trace = root / "trace"
        env = dict(os.environ)
        env["TEST_TRACE"] = str(trace)
        for args in (("--list",), ("--shard", "1/3", "--list"), ("--smoke", "--list")):
            with self.subTest(args=args):
                result = self.invoke_shiploop(*args, root=root, env=env)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertFalse(trace.exists())
        for args in (
            ("--shard",), ("--shard", "0/3"), ("--shard", "1/2"),
            ("--shard", "4/3"), ("--shard", "1/3", "--shard", "2/3"),
            ("--list", "--list"), ("--wat",),
            ("--smoke", "--smoke"), ("--smoke", "--shard", "1/3"),
            ("--shard", "1/3", "--smoke"),
        ):
            with self.subTest(args=args):
                result = self.invoke_shiploop(*args, root=root, env=env)
                self.assertEqual(result.returncode, 64, result.stdout + result.stderr)
                self.assertFalse(trace.exists())

    def test_shiploop_shard_fixture_executes_only_its_selected_suites(self):
        selected = self.shiploop_inventory("2/3")
        self.assertGreaterEqual(len(selected), 2)
        root, env = self.shiploop_fixture()
        trace = root / "trace"
        result = self.invoke_shiploop("--shard", "2/3", root=root, env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(trace.read_text().splitlines(), ["sync", *selected])

        trace.unlink()
        env["FAIL_SUITE"] = selected[1]
        result = self.invoke_shiploop("--shard", "2/3", root=root, env=env)
        self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
        self.assertEqual(trace.read_text().splitlines(), ["sync", *selected[:2]])

    def test_shiploop_mixed_interpreters_are_sharded_and_fail_closed(self):
        node_suite = "test/shiploop-capability-async.test.cjs"
        canonical = self.shiploop_inventory()
        self.assertEqual(canonical.count(node_suite), 1)
        root, env = self.shiploop_fixture()
        trace = root / "trace"
        for shard in (None, "1/3", "2/3", "3/3"):
            with self.subTest(shard=shard):
                trace.unlink(missing_ok=True)
                selected = self.shiploop_inventory(shard)
                args = () if shard is None else ("--shard", shard)
                result = self.invoke_shiploop(*args, root=root, env=env)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(trace.read_text().splitlines(), ["sync", *selected])

        trace.unlink()
        env["FAIL_SUITE"] = node_suite
        result = self.invoke_shiploop(root=root, env=env)
        self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
        self.assertEqual(trace.read_text().splitlines(),
                         ["sync", *canonical[:canonical.index(node_suite) + 1]])

    def test_action_walk_has_one_aggregate_owner(self):
        entrypoint = (ROOT / "test" / "shiploop.test.sh").read_text()
        self.assertEqual(entrypoint.count("test/shiploop-action-walk.test.py"), 1)
        wrapper = (ROOT / "test" / "shiploop-walk-journal.test.sh").read_text()
        self.assertIn("test/shiploop-action-walk.test.py", wrapper)

    def test_ci_routes_events_and_cancels_only_superseded_pr_runs(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
        triggers = workflow.split("\nconcurrency:\n", 1)[0]
        self.assertIn(
            "on:\n  push:\n    branches: [main]\n  pull_request:\n  workflow_dispatch:\n",
            triggers,
        )
        self.assertNotIn("tags:", triggers)
        self.assertIn(
            "concurrency:\n"
            "  group: ci-${{ github.workflow }}-${{ github.event_name }}-${{ github.event.pull_request.number || github.run_id }}\n"
            "  cancel-in-progress: ${{ github.event_name == 'pull_request' }}\n",
            workflow,
        )

    def test_ci_defaults_to_smoke_and_full_requires_explicit_manual_selection(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
        triggers = workflow.split("\nconcurrency:\n", 1)[0]
        self.assertIn("        type: choice\n", triggers)
        self.assertIn("        default: smoke\n", triggers)
        self.assertIn("        options: [smoke, full]\n", triggers)
        # Keep this small dispatch expression auditable; parse the actual matrix
        # choices rather than execute an independent copy of CI routing code.
        matrix = re.search(
            r"group: \$\{\{ fromJSON\((.*?) && '([^']+)' \|\| '([^']+)'\) \}\}",
            workflow,
        )
        self.assertIsNotNone(matrix)
        self.assertEqual(matrix[1], "github.event_name == 'workflow_dispatch' && inputs.tier == 'full'")
        self.assertEqual(json.loads(matrix[2]), list(CI_GROUPS))
        self.assertEqual(json.loads(matrix[3]), ["smoke"])
        self.assertIn("run-name: CI ${{ inputs.tier || 'smoke' }}", workflow)

    def test_ci_preserves_a_fail_closed_aggregate_check(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
        self.assertIn('bash test/run-all.sh --group "${{ matrix.group }}"', workflow)
        self.assertIn("fail-fast: false", workflow)
        self.assertIn("python-version: '3.12'", workflow)
        self.assertIn("node-version: '22'", workflow)
        self.assertIn("      - name: Plugin views in sync\n", workflow)
        self.assertIn("      - name: Tracked checkout unchanged\n", workflow)
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

    def test_ci_scopes_plugin_parity_and_checkout_guard_after_the_suite(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
        parity = self.workflow_step(workflow, "Plugin views in sync")
        guard = self.workflow_step(workflow, "Tracked checkout unchanged")
        self.assertIn("if: ${{ always() && (matrix.group == 'core' || matrix.group == 'smoke') }}", parity)
        self.assertIn("bash scripts/sync-plugin-views.sh --check", parity)
        self.assertNotIn("git diff", parity)
        self.assertIn("if: ${{ always() }}", guard)
        self.assertNotIn("matrix.group", guard)
        self.assertIn("shell: bash -e -o pipefail {0}", guard)
        self.assertLess(workflow.index("      - name: Hermetic group"),
                        workflow.index("      - name: Plugin views in sync"))
        self.assertLess(workflow.index("      - name: Plugin views in sync"),
                        workflow.index("      - name: Tracked checkout unchanged"))
        self.assertLess(workflow.index("      - name: Tracked checkout unchanged"),
                        workflow.index("\n  hermetic:\n"))

    def test_ci_tracked_checkout_guard_executes_actual_commands(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
        commands = self.workflow_run_commands(
            self.workflow_step(workflow, "Tracked checkout unchanged")
        )
        self.assertEqual(commands.splitlines(), [
            "git diff --exit-code",
            "git diff --cached --exit-code",
        ])

        def clean(root, tracked):
            del root, tracked

        def unstaged(root, tracked):
            del root
            tracked.write_text("unstaged\n")

        def staged(root, tracked):
            tracked.write_text("staged\n")
            self.git(root, "add", "tracked.txt")

        def staged_new(root, tracked):
            del tracked
            (root / "staged-new.txt").write_text("new\n")
            self.git(root, "add", "staged-new.txt")

        def staged_with_working_tree_restored(root, tracked):
            tracked.write_text("staged\n")
            self.git(root, "add", "tracked.txt")
            self.git(root, "restore", "--source=HEAD", "--worktree", "tracked.txt")
            self.assertEqual(tracked.read_text(), "clean\n")

        for name, change, expected in (
            ("clean", clean, 0),
            ("unstaged", unstaged, 1),
            ("staged", staged, 1),
            ("staged-new", staged_new, 1),
            ("staged+working-restored", staged_with_working_tree_restored, 1),
        ):
            with self.subTest(change=name):
                root, tracked = self.git_checkout_fixture()
                change(root, tracked)
                result = self.run_ci_commands(root, commands)
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)

    def test_bootstrap_fixture_pin_does_not_rewrite_the_checkout(self):
        script = (ROOT / "test" / "devloop-run.test.sh").read_text()
        self.assertIn('fixture_pin="$tmpdir/engine-pin-fixture.json"', script)
        self.assertNotIn('fixture_pin="$root/test/fixtures/engine-pin-fixture.json"', script)


if __name__ == "__main__":
    unittest.main()
