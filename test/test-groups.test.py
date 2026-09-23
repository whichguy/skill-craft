#!/usr/bin/env python3
"""Contracts for the declarative hermetic suite catalog and runner."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = ROOT / "test"
sys.path.insert(0, str(TEST_DIR))
import ci_policy  # noqa: E402
import run_suites  # noqa: E402
import suite_catalog  # noqa: E402

# Entry points that nothing ran until Phase 1 cataloged them directly.
FORMER_EXPERIMENT_ORPHANS = (
    "test/experiments/shiploop_feature_contracts/test_study.py",
    "test/experiments/shiploop_local_skills/test_packet_routes.py",
    "test/experiments/shiploop_platform_guidance_20260918/apps_script/test/platform_guidance.test.mjs",
    "test/experiments/shiploop_platform_guidance_20260918/python_bash/test_bash_guidance.sh",
    "test/experiments/shiploop_platform_guidance_20260918/python_bash/test_python_guidance.py",
    "test/experiments/shiploop_platform_guidance_20260918/salesforce/run_checks.py",
    "test/experiments/shiploop_requirements/test_study.py",
)


class TestGroupTests(unittest.TestCase):
    def invoke_root(self, root: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(root / "test" / "run-all.sh"), *args],
            cwd=root, env=env, capture_output=True, text=True, timeout=30,
        )

    def invoke_shiploop(self, root: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(root / "test" / "shiploop.test.sh"), *args],
            cwd=root, env=env, capture_output=True, text=True, timeout=30,
        )

    def _copy_runner(self, root: Path) -> None:
        test = root / "test"
        test.mkdir(parents=True)
        for name in ("suite_catalog.py", "run_suites.py", "run-all.sh", "shiploop.test.sh"):
            shutil.copyfile(TEST_DIR / name, test / name)
        for name in ("run-all.sh", "shiploop.test.sh"):
            (test / name).chmod(0o755)

    def list_fixture(self) -> tuple[Path, dict[str, str]]:
        temporary = tempfile.TemporaryDirectory(prefix="skill-craft-list-fixture-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "checkout"
        self._copy_runner(root)
        trace = root / "trace"
        sync = root / "scripts" / "sync-improve-managed.py"
        sync.parent.mkdir()
        sync.write_text(
            "from pathlib import Path\nimport os\nPath(os.environ['TEST_TRACE']).write_text('sync\\n')\n",
            encoding="utf-8",
        )
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

        sync = root / "scripts" / "sync-improve-managed.py"
        sync.parent.mkdir()
        sync.write_text(
            "from pathlib import Path\nimport os, sys\n"
            "with Path(os.environ['TEST_TRACE']).open('a') as stream: stream.write('sync\\n')\n"
            "raise SystemExit(7 if os.environ.get('FAIL_SYNC') else 0)\n",
            encoding="utf-8",
        )
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
        self.assertEqual(len(suite_catalog.SHIPLOOP_SUITES), 101)
        self.assertEqual(len([suite for suite in suite_catalog.SUITES if suite.family == "core"]), 28)
        self.assertEqual(len([suite for suite in suite_catalog.SUITES if suite.family == "experiments"]), 8)
        self.assertEqual(len(suite_catalog.SUITES), 138)
        self.assertTrue(all(suite.hermetic for suite in suite_catalog.SUITES))
        self.assertTrue(all(suite.path in suite.argv for suite in suite_catalog.SUITES))
        self.assertTrue(all(suite.argv[0] in {"python3", "node", "bash"} for suite in suite_catalog.SUITES))
        suite_catalog.validate_catalog()

    def test_full_ci_components_are_the_complete_deduplicated_union(self) -> None:
        full = suite_catalog.select(("all",))
        # The CI matrix is ci_policy.FULL_GROUPS itself, not a second copy.
        self.assertEqual(suite_catalog.select(ci_policy.FULL_GROUPS), full)
        self.assertEqual(full, suite_catalog.SUITES)
        self.assertEqual(len({suite.id for suite in full}), len(full))
        order = ["core", "shiploop", "e2e-apparatus", "experiments"]
        families = [suite.family for suite in full]
        self.assertEqual(families, sorted(families, key=order.index))
        self.assertEqual(list(dict.fromkeys(families)), order)

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
            "shiploop-consumer-delivery-cli", "shiploop-delivery-prompts",
        } <= names)
        self.assertNotIn("ask-agent-worktree-harness", names)
        experiments = suite_catalog.select(("experiments",))
        self.assertEqual(
            [suite.path for suite in experiments],
            ["test/ask-agent-worktree-harness.test.py", *FORMER_EXPERIMENT_ORPHANS],
        )
        self.assertEqual(
            [suite.id for suite in experiments],
            [
                "ask-agent-worktree-harness",
                "experiments-shiploop-feature-contracts-study",
                "experiments-shiploop-local-skills-packet-routes",
                "experiments-shiploop-platform-guidance-20260918-apps-script-test-platform-guidance",
                "experiments-shiploop-platform-guidance-20260918-python-bash-bash-guidance",
                "experiments-shiploop-platform-guidance-20260918-python-bash-python-guidance",
                "experiments-shiploop-platform-guidance-20260918-salesforce-run-checks",
                "experiments-shiploop-requirements-study",
            ],
        )
        self.assertEqual(
            {suite.argv[0] for suite in experiments[1:]}, {"python3", "node", "bash"},
        )

    def test_lpt_shards_are_disjoint_exhaustive_and_catalog_ordered(self) -> None:
        canonical = suite_catalog.SHIPLOOP_SUITES
        shards = suite_catalog.SHIPLOOP_SHARDS
        self.assertEqual(sum(map(len, shards)), len(canonical))
        self.assertEqual(set().union(*(set(shard) for shard in shards)), set(canonical))
        for shard in shards:
            members = set(shard)
            self.assertEqual(shard, tuple(suite for suite in canonical if suite in members))
        self.assertEqual(sum(
            sum(suite.id == "shiploop-action-walk" for suite in shard) for shard in shards
        ), 1)

    def test_list_help_and_invalid_arguments_do_not_execute_or_sync(self) -> None:
        root, env = self.list_fixture()
        for invocation, args, code in (
            (self.invoke_root, ("--list",), 0),
            (self.invoke_root, ("--group", "core", "--list"), 0),
            (self.invoke_root, ("--help",), 0),
            (self.invoke_shiploop, ("--list",), 0),
            (self.invoke_shiploop, ("--shard", "1/3", "--list"), 0),
            (self.invoke_root, ("--group", "unknown"), 64),
            (self.invoke_root, ("--group", ""), 64),
            (self.invoke_root, ("--group",), 64),
            (self.invoke_root, ("--shard", "1/3"), 64),
            (self.invoke_shiploop, ("--group", "core"), 64),
            (self.invoke_shiploop, ("--shard", "4/3"), 64),
            (self.invoke_shiploop, ("--list", "--list"), 64),
            (self.invoke_shiploop, ("--shard", "1/3", "--shard", "2/3"), 64),
        ):
            with self.subTest(args=args):
                result = invocation(root, *args, env=env)
                self.assertEqual(result.returncode, code, result.stdout + result.stderr)
                self.assertFalse((root / "trace").exists())

    def test_root_list_is_flattened_and_shiploop_list_preserves_bare_paths(self) -> None:
        root, env = self.list_fixture()
        listed = self.invoke_root(
            root,
            "--group", "ask-agent",
            "--group", "shiploop-composition",
            "--group", "ask-agent",
            "--group", "experiments",
            "--list",
            env=env,
        )
        self.assertEqual(listed.returncode, 0, listed.stderr)
        rows = [line.split("\t") for line in listed.stdout.splitlines()]
        self.assertTrue(rows)
        self.assertTrue(all(len(row) == 3 for row in rows), listed.stdout)
        self.assertEqual(
            [row[1] for row in rows],
            [suite.id for suite in suite_catalog.select(("ask-agent", "shiploop-composition", "ask-agent", "experiments"))],
        )
        self.assertEqual(len(rows), len({row[1] for row in rows}))

        shiploop = self.invoke_shiploop(root, "--list", env=env)
        self.assertEqual(shiploop.returncode, 0, shiploop.stderr)
        self.assertEqual(shiploop.stdout.splitlines(), [suite.path for suite in suite_catalog.SHIPLOOP_SUITES])
        for index, shard in enumerate(suite_catalog.SHIPLOOP_SHARDS, start=1):
            listed = self.invoke_shiploop(root, "--shard", f"{index}/3", "--list", env=env)
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertEqual(listed.stdout.splitlines(), [suite.path for suite in shard])

    def test_no_smoke_group_or_tier_remains_in_ci_or_catalog(self) -> None:
        self.assertNotIn("smoke", suite_catalog.GROUPS)
        self.assertFalse([suite.id for suite in suite_catalog.SUITES if "smoke" in suite.groups])
        with self.assertRaisesRegex(ValueError, "unknown test group: smoke"):
            suite_catalog.select(("smoke",))
        for relative in (
            "test/suite_catalog.py", "test/run_suites.py", "test/run-all.sh", "test/shiploop.test.sh",
            "test/ci_policy.py", ".github/workflows/ci.yml",
        ):
            with self.subTest(source=relative):
                self.assertNotIn("smoke", (ROOT / relative).read_text(encoding="utf-8").lower())

        root, env = self.list_fixture()
        for invocation, args, message in (
            (self.invoke_root, ("--group", "smoke"), "unknown group: smoke (choose from all, core,"),
            (self.invoke_root, ("--group", "smoke", "--list"), "unknown group: smoke"),
            (self.invoke_root, ("--smoke",), "unrecognized arguments: --smoke"),
            (self.invoke_shiploop, ("--smoke",), "unrecognized arguments: --smoke"),
            (self.invoke_shiploop, ("--smoke", "--list"), "unrecognized arguments: --smoke"),
        ):
            with self.subTest(args=args):
                result = invocation(root, *args, env=env)
                self.assertEqual(result.returncode, 64, result.stdout + result.stderr)
                self.assertIn(message, result.stderr)
                self.assertFalse((root / "trace").exists())
        shiploop_usage = self.invoke_shiploop(root, "--smoke", env=env).stderr
        self.assertIn("--shard N/3", shiploop_usage)

    def test_every_experiment_entry_point_is_reachable(self) -> None:
        entry_points = run_suites.experiment_entry_points(ROOT)
        self.assertTrue(set(FORMER_EXPERIMENT_ORPHANS) <= set(entry_points))
        # Recorded evidence and trial samples are data, not entry points.
        self.assertFalse([path for path in entry_points if {"evidence", "samples", "fixtures", "workspace", "repo"}
                          & set(Path(path).parts)])
        self.assertEqual(run_suites.unreachable_experiments(ROOT), ())
        self.assertEqual(run_suites.catalog_omissions(ROOT), ())

    def loaded_modules(self, suite: suite_catalog.Suite, discovery: suite_catalog.Discovery) -> set[Path]:
        """Ask the wrapper's real loader which module files it would run."""

        if discovery.packages:
            recorder = textwrap.dedent("""
                import json, sys, unittest
                seen = set()
                class Recording(unittest.TestLoader):
                    def loadTestsFromModule(self, module, *args, **kwargs):
                        seen.add(module.__file__)
                        return super().loadTestsFromModule(module, *args, **kwargs)
                Recording().discover(sys.argv[1], pattern=sys.argv[2])
                print(json.dumps(sorted(seen)))
            """)
            argv = ["python3", "-B", "-c", recorder, discovery.directory, discovery.pattern]
        else:
            argv = [*suite.argv, "--list"]
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        listed = json.loads(result.stdout)
        if discovery.packages:
            return {Path(os.path.realpath(path)) for path in listed}
        return {Path(os.path.realpath(ROOT / discovery.directory / f"{name}.py")) for name in listed["modules"]}

    def test_discovery_model_matches_what_each_wrapper_really_loads(self) -> None:
        for wrapper, discovery in suite_catalog.DISCOVERY_ROOTS.items():
            with self.subTest(wrapper=wrapper):
                suite = next(suite for suite in suite_catalog.SUITES if suite.path == wrapper)
                self.assertTrue((ROOT / discovery.directory).is_dir())
                source = (ROOT / wrapper).read_text(encoding="utf-8")
                if discovery.packages:
                    self.assertRegex(source, r"""["']""" + re.escape(Path(discovery.directory).name) + r"""["']""")
                    self.assertRegex(source, r"""\.discover\(.*pattern=["']""" + re.escape(discovery.pattern) + r"""["']""")
                else:
                    # The apparatus row must keep selecting its whole glob.
                    self.assertIn(f'HERE.glob("{discovery.pattern}")', source)
                    self.assertEqual(suite.argv[suite.argv.index("--suite") + 1], "all")
                modeled = run_suites.wrapper_selection(ROOT, discovery)
                self.assertTrue(modeled)
                self.assertEqual(self.loaded_modules(suite, discovery), modeled)

    def test_indirect_entry_points_are_named_along_a_reachable_chain(self) -> None:
        entry_points = run_suites.experiment_entry_points(ROOT)
        direct = {Path(os.path.realpath(ROOT / suite.path)) for suite in suite_catalog.SUITES}
        for discovery in suite_catalog.DISCOVERY_ROOTS.values():
            direct |= run_suites.wrapper_selection(ROOT, discovery)
        for entry, chain in suite_catalog.INDIRECT_ENTRY_POINTS.items():
            with self.subTest(entry=entry):
                self.assertIn(entry, entry_points)
                # The chain starts at a test that is itself cataloged or loaded.
                self.assertIn(Path(os.path.realpath(ROOT / chain[0])), direct)
                for caller, callee in zip(chain, (*chain[1:], entry)):
                    self.assertIn("/".join(Path(callee).parts[-2:]), (ROOT / caller).read_text(encoding="utf-8"))
                # Lying beneath a discovery root alone does not make it reachable.
                with mock.patch.dict(suite_catalog.INDIRECT_ENTRY_POINTS, clear=True):
                    self.assertIn(entry, run_suites.unreachable_experiments(ROOT))

    def test_uncataloged_experiment_runners_are_current_explained_and_needed(self) -> None:
        entry_points = run_suites.experiment_entry_points(ROOT)
        cataloged = {suite.path for suite in suite_catalog.SUITES}
        for path, reason in suite_catalog.UNCATALOGED_EXPERIMENT_RUNNERS.items():
            with self.subTest(path=path):
                self.assertIn(path, entry_points)
                self.assertNotIn(path, cataloged)
                self.assertTrue(reason.strip())
        # Each exemption is load-bearing: without the list exactly these fail.
        exempt = tuple(sorted(suite_catalog.UNCATALOGED_EXPERIMENT_RUNNERS))
        with mock.patch.dict(suite_catalog.UNCATALOGED_EXPERIMENT_RUNNERS, clear=True):
            self.assertEqual(run_suites.unreachable_experiments(ROOT), exempt)
        # A cataloged path cannot also be declared uncataloged, nor exempted
        # silently, and a discovery wrapper only covers anything while cataloged.
        cataloged_path = FORMER_EXPERIMENT_ORPHANS[0]
        for declarations, injected, message in (
            (suite_catalog.UNCATALOGED_EXPERIMENT_RUNNERS, {cataloged_path: "duplicate"},
             "cataloged path is also declared uncataloged"),
            (suite_catalog.INDIRECT_ENTRY_POINTS, {cataloged_path: (FORMER_EXPERIMENT_ORPHANS[1],)},
             "cataloged path is also declared uncataloged"),
            (suite_catalog.UNCATALOGED_EXPERIMENT_RUNNERS, {"test/experiments/new/run_new.py": " "},
             "every uncataloged experiment runner needs a reason"),
            (suite_catalog.DISCOVERY_ROOTS,
             {"test/uncataloged-wrapper.test.py": suite_catalog.Discovery("test/experiments/new", "test_*.py", True)},
             "discovery wrapper is not cataloged: test/uncataloged-wrapper.test.py"),
        ):
            with self.subTest(injected=injected), mock.patch.dict(declarations, injected):
                with self.assertRaisesRegex(ValueError, re.escape(message)):
                    suite_catalog.validate_catalog()

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
            ["sync", *(suite.id for suite in selected)],
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

    def test_unreachable_experiment_entry_point_fails_before_execution(self) -> None:
        root, env, parent = self.execution_fixture()
        experiments = root / "test" / "experiments"
        # Data subtrees and the modules a cataloged wrapper really loads (its
        # top-level ``test_*.py`` and those inside unittest packages) are not orphans.
        for relative in (
            "new_study/evidence/test_recorded.py",
            "new_study/samples/trial-01/test_sample.py",
            "new_study/fixtures/app.test.mjs",
            "shiploop_probe_decisions/test_added_later.py",
            "shiploop_probe_decisions/package/__init__.py",
            "shiploop_probe_decisions/package/test_in_package.py",
        ):
            (experiments / relative).parent.mkdir(parents=True, exist_ok=True)
            (experiments / relative).write_text("# data\n", encoding="utf-8")
        result = self.invoke_root(root, "--group", "core", env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        (parent / "trace").unlink()

        outside = parent / "outside"
        outside.mkdir()
        (outside / "test_linked.py").write_text("# orphan\n", encoding="utf-8")
        (experiments / "linked").symlink_to(outside, target_is_directory=True)
        orphans = (
            "new_study/test_orphan.py", "new_study/tools/check.test.sh", "new_study/web/ui.test.mjs",
            "new_study/run_checks.py", "new_study/web/app.spec.js", "new_study/web/browser-tests.cjs",
            # Beneath a discovery root, yet no wrapper loads them: a nested
            # non-package module and non-Python tests.
            "shiploop_probe_decisions/nested/test_x.py", "shiploop_probe_decisions/check.test.sh",
            "shiploop_probe_decisions/web.test.mjs", "shiploop_probe_decisions/tools/check.test.sh",
        )
        for relative in orphans:
            (experiments / relative).parent.mkdir(parents=True, exist_ok=True)
            (experiments / relative).write_text("# orphan\n", encoding="utf-8")
        result = self.invoke_root(root, "--group", "core", env=env)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(
            [line for line in result.stderr.splitlines() if "unreachable experiment test" in line],
            [f"run-suites: unreachable experiment test: test/experiments/{relative}"
             for relative in sorted(("linked/test_linked.py", *orphans))],
        )
        self.assertFalse((parent / "trace").exists())

    def test_git_ignored_host_local_files_never_block_but_other_files_do(self) -> None:
        root, env, parent = self.execution_fixture()
        # Only the checkout's ignore rules decide; the host's git configuration does not.
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        experiments = root / "test" / "experiments"
        harness = root / "skills" / "harness"
        (root / ".gitignore").write_text("results/\n", encoding="utf-8")
        for path, text in (
            (experiments / "new_study/results/test_run_output.py", "# scratch\n"),
            # Current virtual environment tools write a self-ignoring .gitignore.
            (experiments / "new_study/.venv/.gitignore", "*\n"),
            (experiments / "new_study/.venv/lib/site-packages/pkg/test_util.py", "# scratch\n"),
            (harness / "results/test_linked_output.py", "# scratch\n"),
            (root / "test/local.test.py", "# scratch\n"),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        # A symlinked tree is judged where its files really live.
        (experiments / "harness_link").symlink_to("../../skills/harness", target_is_directory=True)
        # Only the checkout's own repository can ignore a file.  Outside any
        # repository, or inside another one that ignores the whole tree,
        # nothing is ignored and every file counts.
        scratch = "test/experiments/new_study/results/test_run_output.py"
        self.assertIn(scratch, run_suites.experiment_entry_points(root))
        subprocess.run(["git", "init", "-q"], cwd=parent, env=env, check=True)
        (parent / ".gitignore").write_text(f"{root.name}/\n", encoding="utf-8")
        self.assertIn(scratch, run_suites.experiment_entry_points(root))

        subprocess.run(["git", "init", "-q"], cwd=root, env=env, check=True)
        exclude = root / ".git" / "info" / "exclude"
        exclude.parent.mkdir(exist_ok=True)
        with exclude.open("a", encoding="utf-8") as stream:
            stream.write("/test/local.test.py\n")
        result = self.invoke_root(root, "--group", "core", env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        (parent / "trace").unlink()

        # Untracked files that are not ignored, and tracked files under an
        # ignored directory, are repository content and still block.
        orphans = ("harness_link/test_linked.py", "new_study/results/test_tracked.py", "new_study/test_new.py")
        for relative in orphans:
            (experiments / relative).write_text("# orphan\n", encoding="utf-8")
        subprocess.run(["git", "add", "-f", "test/experiments/new_study/results/test_tracked.py"],
                       cwd=root, env=env, check=True)
        result = self.invoke_root(root, "--group", "core", env=env)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(
            [line for line in result.stderr.splitlines() if "unreachable experiment test" in line],
            [f"run-suites: unreachable experiment test: test/experiments/{relative}" for relative in orphans],
        )
        self.assertNotIn("unclassified top-level test", result.stderr)
        self.assertFalse((parent / "trace").exists())

    def test_every_top_level_test_spelling_must_be_classified(self) -> None:
        root, env, parent = self.execution_fixture()
        # Top-level ``run-*`` scripts are repository entrypoints, not tests.
        (root / "test" / "run-extra.sh").write_text("# entrypoint\n", encoding="utf-8")
        result = self.invoke_root(root, "--group", "core", env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        (parent / "trace").unlink()

        spellings = ("test_new.py", "test_new.sh", "new.test.mjs", "new_test.py", "new.spec.js", "new-tests.cjs")
        for name in spellings:
            (root / "test" / name).write_text("# omitted\n", encoding="utf-8")
        result = self.invoke_root(root, "--group", "core", env=env)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(
            [line for line in result.stderr.splitlines() if "unclassified top-level test" in line],
            [f"run-suites: unclassified top-level test: test/{name}" for name in sorted(spellings)],
        )
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
