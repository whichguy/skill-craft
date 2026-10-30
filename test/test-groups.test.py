#!/usr/bin/env python3
"""Contracts for the declarative hermetic suite catalog and runner."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import signal
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


class TestGroupTests(unittest.TestCase):
    def invoke_root(self, root: Path, *args: str, env: dict[str, str] | None = None,
                    timeout: float = 30) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(root / "test" / "run-all.sh"), *args],
            cwd=root, env=env, capture_output=True, text=True, timeout=timeout,
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
                    # PID_DIR: record the pid and hang far longer than the interrupt test waits, so a runner that
                    # waited for its suites instead of stopping them cannot pass by their ending on their own.
                    "if os.environ.get('PID_DIR'):\n"
                    "    import time\n"
                    f"    (Path(os.environ['PID_DIR']) / '{suite.id}').write_text(str(os.getpid()))\n"
                    "    time.sleep(600)\n"
                    # BARRIER_DIR: pass only once BARRIER_COUNT suites have arrived, so passing proves they overlapped.
                    "if os.environ.get('BARRIER_DIR'):\n"
                    "    import time\n"
                    "    barrier = Path(os.environ['BARRIER_DIR'])\n"
                    f"    (barrier / '{suite.id}').touch()\n"
                    "    deadline = time.monotonic() + float(os.environ['BARRIER_SECONDS'])\n"
                    "    while len(list(barrier.iterdir())) < int(os.environ['BARRIER_COUNT']):\n"
                    "        if time.monotonic() > deadline:\n"
                    "            raise SystemExit(9)\n"
                    "        time.sleep(0.01)\n"
                    f"raise SystemExit(7 if os.environ.get('FAIL_SUITE') == '{suite.id}' else 0)\n",
                    encoding="utf-8",
                )
        return root, env, parent

    def test_audited_catalog_counts_and_fixed_commands(self) -> None:
        # Current main's 97 ShipLoop suites plus four learning-loop contract suites, the SDLC probes (2026-10-30) and the
        # seed seam suite.
        self.assertEqual(len(suite_catalog.SHIPLOOP_SUITES), 103)
        self.assertEqual(len([suite for suite in suite_catalog.SUITES if suite.family == "core"]), 53)
        self.assertEqual(len(suite_catalog.SUITES), 158)
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
            "ask-agent-parallel", "ask-agent-task",
            "shiploop-consumer-delivery",
            "shiploop-consumer-delivery-cli",
        } <= names)
        # Design T §9.1 2c-2 retired ShipLoop's chain, so no chain suite or native pilot is in the group.
        self.assertFalse({name for name in names if "shiploop-chain" in name or "native-pilot" in name})
        self.assertNotIn("experiments", suite_catalog.GROUPS)
        with self.assertRaises(ValueError):
            suite_catalog.select(("experiments",))

    def test_in_parallel_group_and_historical_alias_select_the_same_suites(self) -> None:
        selected = suite_catalog.select(("in-parallel",))
        self.assertEqual({suite.id for suite in selected}, {
            "agent-harness", "agent-harness-delivery", "agent-harness-boundaries",
            "agent-harness-audit", "plan-dispatcher-harness", "in-parallel-composition", "in-parallel-queue", "in-parallel-queue-audit",
        })
        self.assertEqual(suite_catalog.select(("agent-harness",)), selected)
        self.assertEqual(suite_catalog.select(("in-parallel", "agent-harness")), selected)

    def test_quick_is_a_light_baseline_plus_the_suites_matching_changed_files(self) -> None:
        baseline = {suite.id for suite in suite_catalog.quick()}
        self.assertEqual(baseline, {suite.id for suite in suite_catalog.select(("quick",))})
        self.assertTrue({"test-groups", "ci-policy", "skill-frontmatter", "shiploop-mock-replay",
                         "shiploop-navigator-v4"} <= baseline)
        self.assertLess(len(baseline), 17)
        cases = {
            "skills/backchain/prompts/revise.prompt.md": {"backchain-chunks"},
            "test/backchain_chunks.py": {"backchain-chunks"},
            "test/fixtures/backchain-chunks/mixed.json": {"backchain-chunks", "marketplace-package"},
            # shiploop-loops reaches the stop hook end to end on a real run (owed-outcome phase A); shiploop-e2e-slice frees
            # the run's keepalive owner at a clear with the plugin's own release_owner.
            "skills/shiploop/scripts/shiploop_keepalive.py": {"shiploop-keepalive", "shiploop-skill-calls", "shiploop-actual-improve-cli", "shiploop-domain-words",
                                                          "shiploop-retired-terms", "shiploop-trace", "shiploop-loops",
                                                          "shiploop-e2e-slice"},
            "skills/shiploop/scripts/shiploop_skill_calls.py": {"shiploop-skill-calls", "shiploop-domain-words", "shiploop-retired-terms"},
            # Every ShipLoop skill path also selects the domain-word lint and the retired-term scan (the skills/shiploop/ row).
            "scripts/release.py": {"release-push", "release-flow", "release-boundary", "release-preflight"},
            "skills/improve/SKILL.md": {"improve", "improve-plugin", "improve-agent", "improve-runtime", "improve-route"},
            "install.sh": {"install-targets", "install-arbitrary-skill", "install-status-uninstall"},
            "test/shiploop-lint.test.py": {"shiploop-lint"},
            "docs/notes.md": set(),
            "skills/in-parallel/scripts/harness.py": {
                "agent-harness", "agent-harness-delivery", "agent-harness-boundaries",
                "agent-harness-audit", "plan-dispatcher-harness", "in-parallel-composition", "in-parallel-queue", "in-parallel-queue-audit",
                "marketplace-package",
            },
            "agents/in-parallel.md": {
                "agent-harness", "agent-harness-delivery", "agent-harness-boundaries",
                "agent-harness-audit", "plan-dispatcher-harness", "in-parallel-composition", "in-parallel-queue", "in-parallel-queue-audit",
                "marketplace-package",
            },
            "skills/shiploop/SKILL.md": {"shiploop-guidance", "shiploop-reference-routing",
                                         "shiploop-delegation", "shiploop-package-integrity",
                                         "shiploop-packet-completeness", "shiploop-step-packets",
                                         "shiploop-reference", "shiploop-packet-recut", "shiploop-head-order",
                                         "shiploop-domain-words", "shiploop-retired-terms"},
            "test/shiploop_consumer_delivery_support.py": {"shiploop-consumer-delivery"},
            # The Run Review leaf: its own suite plus the package build that gates a new leaf.
            "skills/shiploop-run-review/scripts/export.py": {"shiploop-run-review", "marketplace-package"},
            "skills/shiploop-run-review/SKILL.md": {"shiploop-run-review", "marketplace-package"},
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                extra = {suite.id for suite in suite_catalog.quick((path,))} - baseline
                self.assertEqual(extra, expected)

    def test_quick_reaches_the_consumers_of_shared_shiploop_sources(self) -> None:
        # Suites named after nothing in these paths still exercise them; a
        # name match alone left prompt and navigator edits at the baseline.
        cases = {
            "skills/shiploop/scripts/shiploop_navigator.py": {"shiploop-lint", "shiploop-delegation",
                                                              "shiploop-actual-improve-cli"},
            "skills/shiploop/scripts/shiploop_prompts.py": {"shiploop-guidance",
                                                                         "shiploop-quality"},
            "skills/shiploop/references/research-loop.md": {"shiploop-guidance",
                                                            "shiploop-reference-routing"},
            "skills/shiploop/commands/shiploop.md": {"shiploop-delegation"},
            "skills/shiploop/scripts/shiploop": {"shiploop-store", "shiploop-privacy",
                                                 "shiploop-keepalive"},
            "skills/shiploop/scripts/shiploop_protocol.py": {"shiploop-delegation", "shiploop-lint"},
            "skills/shiploop/host-hooks.json": {"shiploop-package-integrity"},
            "skills/shiploop/hooks/opencode-keepalive.js": {"shiploop-package-integrity"},
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertLessEqual(expected, {suite.id for suite in suite_catalog.quick((path,))})

    def test_a_hub_file_selects_its_fixed_set_however_many_suites_reference_it(self) -> None:
        # Assumption: a file most suites reference selects _HUB_SUITE_IDS in place of its consumers, so its selection
        # does not grow with them.  Checked by adding consumers, not by a count ceiling: a ceiling sat exactly at its
        # limit once the packet-source rule joined the hub's selection, and any new rule or suite would trip it with
        # nothing wrong.
        real = suite_catalog._suite_sources()
        for path, token in (("skills/shiploop/scripts/shiploop_navigator.py", "shiploop_navigator"),
                            ("skills/shiploop/scripts/shiploop_store.py", "shiploop_store"),
                            ("skills/shiploop/scripts/shiploop", "scripts/shiploop")):
            with self.subTest(path=path):
                before = suite_catalog.targeted([path])
                more = {f"fake-consumer-{n}": f"import {token}\n" for n in range(2 * suite_catalog.HUB_REFERENCE_LIMIT)}
                with mock.patch.object(suite_catalog, "_suite_sources", return_value={**real, **more}):
                    after = suite_catalog.targeted([path])
                self.assertEqual(after, before)
                self.assertGreaterEqual(after, set(suite_catalog._HUB_SUITE_IDS))

    def test_quick_never_runs_heavy_suites_or_the_apparatus(self) -> None:
        everything = tuple(suite.path for suite in suite_catalog.SUITES)
        selected = suite_catalog.quick(everything)
        self.assertTrue(selected)
        for suite in selected:
            self.assertNotEqual(suite.id, "shiploop-e2e-apparatus")
            self.assertLessEqual(suite_catalog._DURATION_SECONDS.get(suite.path, 0.0),
                                 suite_catalog.QUICK_MAX_SECONDS, suite.id)
        ids = {suite.id for suite in selected}
        self.assertFalse({name for name in ids if "shiploop-chain" in name})
        self.assertIn("shiploop-mock-replay", ids)

    def test_changed_from_lists_quick_suites_and_is_refused_for_other_groups(self) -> None:
        listed = subprocess.run(["bash", str(ROOT / "test/run-all.sh"), "--group", "quick",
                                 "--changed-from", "HEAD", "--list"],
                                cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(listed.returncode, 0, listed.stderr)
        # A local checkout may carry uncommitted edits, which quick counts.
        self.assertEqual([line.split("\t")[1] for line in listed.stdout.splitlines()],
                         [suite.id for suite in suite_catalog.quick(run_suites.changed_paths(ROOT, "HEAD"))])
        listed = subprocess.run(["bash", str(ROOT / "test/run-all.sh"), "--group", "prompt", "--group", "core",
                                 "--changed-from", "HEAD", "--list"],
                                cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertEqual([line.split("\t")[1] for line in listed.stdout.splitlines()],
                         [suite.id for suite in suite_catalog.select(("prompt", "core"),
                                                                     run_suites.changed_paths(ROOT, "HEAD"))])
        refused = subprocess.run(["bash", str(ROOT / "test/run-all.sh"), "--group", "core",
                                  "--changed-from", "HEAD", "--list"],
                                 cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(refused.returncode, 64)
        self.assertIn("--changed-from applies only to --group quick or prompt", refused.stderr)

    def test_changed_paths_include_uncommitted_and_untracked_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            def git(*args: str) -> None:
                subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
                               cwd=repo, check=True, capture_output=True)
            git("init", "-q")
            (repo / "committed.py").write_text("a\n")
            (repo / "staged.md").write_text("a\n")
            (repo / ".gitignore").write_text("ignored.log\n")
            git("add", ".")
            git("commit", "-q", "-m", "base")
            (repo / "committed.py").write_text("b\n")
            (repo / "staged.md").write_text("b\n")
            git("add", "staged.md")
            (repo / "new_module.py").write_text("c\n")
            (repo / "ignored.log").write_text("d\n")
            self.assertEqual(sorted(run_suites.changed_paths(repo, "HEAD")),
                             ["committed.py", "new_module.py", "staged.md"])

    def test_lpt_shards_are_disjoint_exhaustive_and_catalog_ordered(self) -> None:
        canonical = suite_catalog.SHIPLOOP_SUITES
        shards = suite_catalog.SHIPLOOP_SHARDS
        self.assertEqual(sum(map(len, shards)), len(canonical))
        self.assertEqual(set().union(*(set(shard) for shard in shards)), set(canonical))
        for shard in shards:
            members = set(shard)
            self.assertEqual(shard, tuple(suite for suite in canonical if suite in members))
        # The slowest suites are spread, not stacked: no shard holds two of the three longest.
        longest = sorted(canonical, key=lambda suite: suite_catalog._DURATION_SECONDS.get(suite.path, 0.0))[-3:]
        self.assertTrue(all(sum(suite in shard for suite in longest) <= 1 for shard in shards)
                        or len(shards) < 3)

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
            (self.invoke_root, ("--jobs", "0", "--list"), 64),
            (self.invoke_root, ("--jobs", "-2", "--list"), 64),
            (self.invoke_root, ("--jobs", "many", "--list"), 64),
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
        # One job keeps today's order: each suite starts after the previous one is in the receipt.
        result = self.invoke_root(root, "--group", "ask-agent", "--jobs", "1", "--output", str(output), env=env)
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

    TIMING = re.compile(r"^run-all\.sh: \d+ suites in [\d.]+ s wall \(--jobs (\d+)\); slowest: ")

    def test_parallel_jobs_report_what_one_job_reports(self) -> None:
        # Same per-suite output in catalog order, same receipt records, same exit code; only the timing line and the
        # receipt's own path differ.  A failure at the front, in the middle and at the end, and none.
        selected = [suite.id for suite in suite_catalog.select(("ask-agent",))]
        for failing in (None, selected[0], "ask-agent-delivery", selected[-1]):
            with self.subTest(failing=failing):
                runs = {}
                for jobs in ("1", "4"):
                    root, env, parent = self.execution_fixture()
                    if failing:
                        env["FAIL_SUITE"] = failing
                    output = parent / "receipt"
                    result = self.invoke_root(root, "--group", "ask-agent", "--jobs", jobs, "--output", str(output),
                                              env=env)
                    receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
                    timing = [match for line in result.stdout.splitlines() if (match := self.TIMING.match(line))]
                    self.assertEqual([match.group(1) for match in timing], [jobs], result.stdout)
                    self.assertEqual(receipt["jobs"], int(jobs))
                    self.assertGreater(receipt["wall_seconds"], 0)
                    self.assertEqual(sorted((parent / "trace").read_text(encoding="utf-8").splitlines()), sorted(selected))
                    runs[jobs] = (
                        result.returncode,
                        [line for line in result.stdout.splitlines()
                         if not self.TIMING.match(line) and not line.startswith("receipt: ")],
                        result.stderr,
                        [(record["id"], record["status"], record["returncode"]) for record in receipt["completed"]],
                        receipt["status"],
                    )
                self.assertEqual(runs["4"], runs["1"])
                self.assertEqual(runs["1"][0], 1 if failing else 0)
                self.assertEqual([record[0] for record in runs["1"][3]], selected)
                self.assertEqual([record[0] for record in runs["1"][3] if record[1] == "failed"],
                                 [failing] if failing else [])

    # Waits in the parallel-runner tests are generous on purpose: on success each returns as soon as its condition holds,
    # so the headroom costs nothing, and a loaded machine (load average 29 to 46 on 2026-10-26, journal F11) must not
    # turn a correct runner red.  Each test stays discriminating through what it waits for, not through a short limit.
    PATIENCE_SECONDS = 60

    def test_jobs_run_suites_side_by_side_and_one_job_never_overlaps(self) -> None:
        # Each fake suite passes only once BARRIER_COUNT suites have arrived, so a pass proves they overlapped.
        root, env, parent = self.execution_fixture()
        (parent / "barrier").mkdir()
        env.update(BARRIER_DIR=str(parent / "barrier"), BARRIER_COUNT="4", BARRIER_SECONDS=str(self.PATIENCE_SECONDS))
        result = self.invoke_root(root, "--group", "ask-agent", "--jobs", "4", env=env,
                                  timeout=2 * self.PATIENCE_SECONDS)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        # The control: one job at a time, the first suite waits alone and fails; every later one finds two arrivals.
        # Its short wait cannot flake: one job never overlaps, so a longer wait would only make the control slower.
        root, env, parent = self.execution_fixture()
        (parent / "barrier").mkdir()
        env.update(BARRIER_DIR=str(parent / "barrier"), BARRIER_COUNT="2", BARRIER_SECONDS="0.5")
        result = self.invoke_root(root, "--group", "ask-agent", "--jobs", "1", env=env)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(re.findall(r"^FAIL (\S+)$", result.stderr, re.M), [suite_catalog.select(("ask-agent",))[0].id])

    def test_an_interrupted_parallel_run_stops_the_suites_it_started(self) -> None:
        # Each suite leads its own session, so Ctrl-C reaches only the runner; it must stop them. The fake suites sleep
        # ten times PATIENCE_SECONDS, so a runner that waited for them instead fails the wait below.
        jobs = 3
        root, env, parent = self.execution_fixture()
        pids = parent / "pids"
        pids.mkdir()
        env["PID_DIR"] = str(pids)
        runner = subprocess.Popen(
            ["bash", str(root / "test" / "run-all.sh"), "--group", "ask-agent", "--jobs", str(jobs)],
            cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
            # Python installs its Ctrl-C handler only when SIGINT is not ignored, and a background shell ignores it.
            preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_DFL),
        )
        self.addCleanup(lambda: runner.poll() is None and runner.kill())

        def kill_if_alive(pid: int) -> bool:
            """Kill a fake suite that is still running, so a failure here leaves no sleeper behind."""
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                return False
            return True

        deadline = time.monotonic() + self.PATIENCE_SECONDS
        while len(list(pids.iterdir())) < jobs:
            self.assertLess(time.monotonic(), deadline, f"{jobs} suites did not start")
            time.sleep(0.05)
        runner.send_signal(signal.SIGINT)
        try:
            runner.communicate(timeout=self.PATIENCE_SECONDS)
        except subprocess.TimeoutExpired:
            runner.kill()
            for path in pids.iterdir():
                kill_if_alive(int(path.read_text(encoding="utf-8")))
            self.fail(f"the interrupted runner was still waiting for its suites after {self.PATIENCE_SECONDS} s")
        self.assertNotEqual(runner.returncode, 0)
        started = [int(path.read_text(encoding="utf-8")) for path in pids.iterdir()]
        self.assertEqual(len(started), jobs, "a suite started after the interrupt")
        deadline = time.monotonic() + self.PATIENCE_SECONDS
        for pid in started:
            while True:
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    break
                if time.monotonic() > deadline:
                    kill_if_alive(pid)
                    self.fail(f"suite process {pid} outlived the runner")
                time.sleep(0.05)

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


class StateHomeGuardTest(unittest.TestCase):
    """A suite's state never reaches the developer's ~/.local/state, and a suite that leaves any fails.

    On 2026-10-18 a vendor test ran Until Loop's `start` with the host's session ID and no state root of its own, and
    left a placeholder stack (work "w", request "q") in the owner's ~/.local/state/until-loop, which a SessionStart
    hook then offered to a real session as saved work.  The program here makes that same call on the real runtime.
    ShipLoop's keepalive health records leaked the same way (32 of the owner's 170 on 2026-10-26).
    """

    RUNTIME = ROOT / "skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py"
    PROGRAM = textwrap.dedent("""\
        import json, os, subprocess, sys
        contract = {"workspace": os.getcwd(), "work": "w", "exit_condition": "e", "repeat_condition": "r",
                    "context": {"request": "q", "scope": "s", "authority": "a", "environment": "e", "resources": []}}
        env = dict(os.environ, UNTIL_LOOP_SESSION_ID="state-guard")
        if len(sys.argv) > 2:
            env["XDG_STATE_HOME"] = sys.argv[2]
        started = subprocess.run([sys.executable, "-B", sys.argv[1], "start"], input=json.dumps(contract),
                                 env=env, capture_output=True, text=True)
        sys.stderr.write(started.stdout + started.stderr)
        raise SystemExit(started.returncode)
    """)

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="skill-craft-state-guard-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.program = self.root / "starts_a_session.py"
        self.program.write_text(self.PROGRAM, encoding="utf-8")
        # Stand-ins for the developer's own state roots, which the runner's environment would otherwise pass on.
        self.inherited = {name: self.root / name.lower()
                          for name in ("UNTIL_LOOP_STATE_DIR", "SHIPLOOP_KEEPALIVE_HOME", "XDG_STATE_HOME")}
        for path in self.inherited.values():
            path.mkdir(mode=0o700)
        environment = mock.patch.dict(os.environ, {name: str(path) for name, path in self.inherited.items()})
        environment.start()
        self.addCleanup(environment.stop)

    def run_program(self, *args: str) -> run_suites.ProcessOutcome:
        argv = (sys.executable, "-B", str(self.program), str(self.RUNTIME), *args)
        return run_suites.run_process(argv, cwd=self.root, timeout_seconds=60)

    def assert_the_developers_state_is_untouched(self) -> None:
        for path in self.inherited.values():
            self.assertEqual(list(path.iterdir()), [], path)

    def test_a_suite_that_starts_a_session_without_its_own_state_root_fails_and_the_developers_stays_empty(self) -> None:
        outcome = self.run_program()
        self.assertEqual(outcome.returncode, 0, "the runtime accepted the runner's state home: " + outcome.stderr)
        self.assertEqual(outcome.status, "failed")
        self.assertRegex(outcome.error or "", r"until-loop/innerloop-session-[0-9a-f]{64}\.json")
        self.assertIn("UNTIL_LOOP_STATE_DIR", outcome.error or "")
        self.assert_the_developers_state_is_untouched()

    def test_keepalive_health_written_for_the_host_session_fails_the_suite(self) -> None:
        notice = ("import sys; sys.path.insert(0, sys.argv[1]); import shiploop_keepalive as keepalive; "
                  "keepalive.health_notice('/run', {'CLAUDECODE': '1', 'CLAUDE_CODE_SESSION_ID': 'host-session'})")
        argv = (sys.executable, "-B", "-c", notice, str(ROOT / "skills/shiploop/scripts"))
        outcome = run_suites.run_process(argv, cwd=self.root, timeout_seconds=60)
        self.assertEqual(outcome.returncode, 0, outcome.stderr)
        self.assertEqual(outcome.status, "failed")
        self.assertRegex(outcome.error or "", r"shiploop/keepalive/health/claude-[0-9a-f]{32}\.json")
        self.assertIn("CLAUDE_CODE_SESSION_ID", outcome.error or "")
        self.assert_the_developers_state_is_untouched()

    def test_ci_stand_in_markers_let_the_guard_see_a_keepalive_leak(self) -> None:
        """GitHub runners have no host session, so keepalive never wrote there and CI never saw its leaks (round 3)."""
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        markers = dict(re.findall(r"^\s+(CLAUDECODE|CLAUDE_CODE_SESSION_ID): '?([^'\n]+)'?$", workflow,
                                  re.MULTILINE))
        self.assertEqual(set(markers), {"CLAUDECODE", "CLAUDE_CODE_SESSION_ID"})
        notice = ("import sys; sys.path.insert(0, sys.argv[1]); import shiploop_keepalive as keepalive; "
                  "keepalive.health_notice('/run')")
        argv = (sys.executable, "-B", "-c", notice, str(ROOT / "skills/shiploop/scripts"))
        hosts = ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "GROK_AGENT", "GROK_SESSION_ID")
        for given, leaks in (({}, False), (markers, True)):
            environment = {key: value for key, value in os.environ.items() if key not in hosts}
            with self.subTest(markers=sorted(given)), mock.patch.dict(os.environ, {**environment, **given}, clear=True):
                outcome = run_suites.run_process(argv, cwd=self.root, timeout_seconds=60)
                self.assertEqual(outcome.status, "failed" if leaks else "passed", outcome.error or outcome.stderr)
        self.assert_the_developers_state_is_untouched()

    def test_a_suite_that_gives_the_runtime_its_own_state_root_passes(self) -> None:
        own = self.root / "fixture-state"
        outcome = self.run_program(str(own))
        self.assertEqual(outcome.status, "passed", (outcome.error or "") + outcome.stderr)
        self.assertEqual(len(list((own / "until-loop").glob("innerloop-session-*.json"))), 1)
        self.assert_the_developers_state_is_untouched()


class ChildBytecodeTest(unittest.TestCase):
    """A suite never writes bytecode into the tree it runs in, so a sibling suite's `tar` of that tree stays quiet.

    CI run 40813164137 (1961f4c5): sync-plugin-views and native-marketplace-adapters copy the checkout with `tar -cf - .`
    while the first four suites run together at --jobs 4.  Two of those are Python suites that import test/ci_policy.py
    and test/run_suites.py, which created test/__pycache__ on the fresh runner checkout, and GNU tar exited 1 with
    "./test: file changed as we read it".  The runner's own `python3 -B` does not reach the processes it starts, and
    macOS's bsdtar makes no such check, so no local run ever showed it.
    """

    def test_a_suite_that_imports_a_sibling_module_leaves_no_pycache_behind(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-craft-bytecode-") as name:
            root = Path(name).resolve()
            (root / "sibling.py").write_text("VALUE = 1\n", encoding="utf-8")
            program = root / "imports_a_sibling.py"
            program.write_text("import sibling\n", encoding="utf-8")
            # The runner must supply the setting itself: a developer's or a CI job's own value would hide its absence.
            without = {key: value for key, value in os.environ.items() if key != "PYTHONDONTWRITEBYTECODE"}
            with mock.patch.dict(os.environ, without, clear=True):
                outcome = run_suites.run_process((sys.executable, str(program)), cwd=root, timeout_seconds=60)
            self.assertEqual(outcome.status, "passed", (outcome.error or "") + outcome.stderr)
            self.assertEqual(sorted(root.rglob("__pycache__")), [])


class PacketSourceSelectionTest(unittest.TestCase):
    """A ShipLoop prompt or packet source always selects the packet-size suites (owner, 2026-10-25).

    The step-plan template edits of that day (f23cdb20, 58a8f2eb) changed only shiploop_prompts.py.  It is a hub, so the
    quick tier ran the hub's fixed consumers in place of the suites that read it, and two `--changed-from` quick runs did
    not select the packet-size suites; a third, wider run caught a head over its cut.  Each assertion fails on the catalog
    before the packet-source rule.
    """

    SOURCES = (
        "skills/shiploop/scripts/shiploop_prompts.py",
        "skills/shiploop/scripts/shiploop_navigator.py",
        "skills/shiploop/scripts/shiploop_stage_spec.py",
        "skills/shiploop/scripts/shiploop_loops.py",
        "skills/shiploop/scripts/shiploop_narrative.py",
    )
    # The prompt surface selected them before, through _SHIPLOOP_PROMPT_IDS; pinned so it keeps doing so.
    SURFACE = ("skills/shiploop/SKILL.md", "skills/shiploop/references/inner-loop.md",
               "skills/shiploop/commands/shiploop.md")

    def test_the_packet_size_suites_are_the_four_named(self) -> None:
        self.assertEqual(set(suite_catalog.PACKET_SIZE_IDS), {"shiploop-step-packets", "shiploop-packet-recut",
                                                              "shiploop-head-order", "shiploop-packet-completeness"})

    def test_a_packet_source_selects_the_packet_size_suites_in_the_quick_tier(self) -> None:
        for path in (*self.SOURCES, *self.SURFACE):
            with self.subTest(path=path):
                self.assertGreaterEqual({suite.id for suite in suite_catalog.quick([path])},
                                        set(suite_catalog.PACKET_SIZE_IDS))

    def test_a_packet_source_keeps_the_obligation_ledger_and_its_hub(self) -> None:
        # The ledger anchors literal phrases of the packet text; 2.11.0 failed CI there after a rewrap.
        for path in self.SOURCES:
            with self.subTest(path=path):
                self.assertIn("shiploop-packet-obligations", {suite.id for suite in suite_catalog.quick([path])})
        self.assertGreaterEqual(suite_catalog.targeted([self.SOURCES[0]]), set(suite_catalog._HUB_SUITE_IDS))

    def test_the_prompt_group_is_the_packet_suites_plus_the_changed_suites(self) -> None:
        # The four packet-size suites and the obligation ledger: 2.11.0 failed CI on the ledger (a rewrap split an
        # anchored phrase of shiploop_prompts.py across two lines) while the four passed locally.
        # The ids are pinned by name; validate_catalog() refuses one the catalog lacks, so no count is needed here.
        packet = [suite.id for suite in suite_catalog.SUITES
                  if suite.id in {*suite_catalog.PACKET_SIZE_IDS, "shiploop-packet-obligations"}]
        self.assertEqual([suite.id for suite in suite_catalog.select(("prompt",))], packet)
        # A changed suite runs itself; a changed source adds nothing beyond the packet suites, and a suite above
        # QUICK_MAX_SECONDS (shiploop-workspace) stays in the full tier, as in quick.
        changed = ("skills/shiploop/scripts/shiploop_prompts.py", "test/shiploop-guidance.test.py",
                   "test/shiploop-workspace.test.py", "docs/notes.md")
        self.assertEqual({suite.id for suite in suite_catalog.select(("prompt",), changed)},
                         {*packet, "shiploop-guidance"})
        union = {*suite_catalog.quick(changed), *suite_catalog.prompt(changed)}
        self.assertEqual(suite_catalog.select(("quick", "prompt"), changed),
                         tuple(suite for suite in suite_catalog.SUITES if suite in union))

    def test_a_selection_rule_naming_an_unknown_suite_is_refused(self) -> None:
        with mock.patch.object(suite_catalog, "_HUB_SUITE_IDS", (*suite_catalog._HUB_SUITE_IDS, "shiploop-renamed")):
            with self.assertRaisesRegex(ValueError, "unknown suites: shiploop-renamed"):
                suite_catalog.validate_catalog()


class QuickSelectionNameCollisionTest(unittest.TestCase):
    """A file called plan, review or spec says nothing about which suite covers it.

    The quick tier selects suites named after a changed file and suites whose source names it.  Frozen evidence
    and fixtures carry the common names PLAN.md, SPEC.md and review.json, so a push that touched one of them ran
    all eight plan-dispatcher suites, or shiploop-e2e, shiploop-navigator-contract and shiploop-run-review, for
    files none of them reads (445 of the 569 s of one local quick run).  The paths below are real tracked files.
    """

    PLAN_DISPATCHER = {suite.id for suite in suite_catalog.SUITES if suite.id.startswith("plan-dispatcher-")}
    E2E_SPEC_READERS = {"shiploop-e2e", "shiploop-navigator-contract", "shiploop-run-review"}

    def selected(self, *paths: str) -> set[str]:
        return suite_catalog.targeted(paths)

    def test_a_fixture_named_plan_does_not_select_the_plan_dispatcher_suites(self) -> None:
        for path in ("test/experiments/shiploop_entry_recovery/evidence/fixture/PLAN.md",
                     "skills/rubric-eval/suites/architecture-v4/frames/plan.txt",
                     "test/experiments/shiploop_ui_allocation/evidence/existing/notes/plan.md"):
            self.assertFalse(self.selected(path) & self.PLAN_DISPATCHER, path)

    def test_a_fixture_named_spec_does_not_select_the_suites_that_read_the_e2e_spec(self) -> None:
        for path in ("test/experiments/shiploop_repeatable_tests/samples/trial-01/SPEC.md",
                     "test/experiments/shiploop_ui_consumer/SPEC.md",
                     "skills/adversarial-review/SPEC.md"):
            self.assertFalse(self.selected(path) & self.E2E_SPEC_READERS, path)

    def test_a_file_named_review_does_not_select_review_coverage(self) -> None:
        for path in ("test/experiments/shiploop_service_discovery_20260919/evidence/final/review.json",
                     "skills/rubric-eval/suites/architecture-v4/frames/review.txt",
                     "test/shiploop_e2e/review.py"):
            self.assertNotIn("review-coverage", self.selected(path), path)

    def test_the_e2e_spec_still_selects_every_suite_that_reads_it(self) -> None:
        # The real SPEC.md has real readers (shiploop-e2e, shiploop-navigator-contract and shiploop-run-review each
        # open test/shiploop_e2e/SPEC.md), so it is named explicitly instead of by its common file name.
        self.assertGreaterEqual(self.selected("test/shiploop_e2e/SPEC.md"), self.E2E_SPEC_READERS)

    def test_real_code_and_skill_paths_keep_the_suites_they_always_selected(self) -> None:
        cases = {
            "test/shiploop_e2e/run.py": {"shiploop-e2e"},
            "test/shiploop_e2e/review.py": {"shiploop-e2e"},
            "skills/plan-dispatcher/SKILL.md": self.PLAN_DISPATCHER,
            "skills/rubric-eval/SPEC.md": {"rubric-eval"},
            "skills/rubric-eval/suites/architecture-v4/frames/review.txt": {"rubric-eval"},
            "skills/review-coverage/SKILL.md": {"review-coverage"},
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertGreaterEqual(self.selected(path), expected)


class E2EFamilySelectionTest(unittest.TestCase):
    """An edit under test/shiploop_e2e/ runs every suite of the E2E harness family in the quick tier (batch 1011 integration).

    The harness's modules (run.py, metrics.py, fidelity.py, sessionlog.py, environment.py) have names too common to select by,
    and each family suite reads them through run.py or metrics.py: before, the prefix selected shiploop-e2e alone (and, after
    group G2, shiploop-e2e-reorientation), so an edit of metrics.py skipped the fidelity, runrecord and environment suites.
    The family is pinned as it stands on this branch, so a merged group that adds a suite updates this list on purpose.
    """

    FAMILY = {"shiploop-e2e", "shiploop-e2e-runrecord", "shiploop-e2e-fidelity", "shiploop-e2e-reorientation",
              "shiploop-e2e-environment", "shiploop-e2e-baseline", "shiploop-e2e-quality",
              "shiploop-e2e-packet-anatomy", "shiploop-e2e-render-diff", "shiploop-e2e-commit-counters", "shiploop-e2e-slice",
              "shiploop-e2e-chess-salesforce", "shiploop-e2e-battleship-salesforce", "shiploop-e2e-release-slice", "shiploop-e2e-platform",
              "shiploop-e2e-sf-guard", "shiploop-e2e-status-card",
              "shiploop-e2e-efficiency", "shiploop-e2e-dodges", "shiploop-e2e-owner-page", "shiploop-e2e-experiments",
              "shiploop-e2e-sdlc-probes",
              "shiploop-e2e-run-trace", "shiploop-e2e-brownfield", "shiploop-e2e-brownfield-tickets",
              "shiploop-e2e-lifecycle", "shiploop-e2e-discovery", "shiploop-e2e-qualification",
              "shiploop-e2e-roles", "shiploop-e2e-epoch"}

    def test_the_pinned_family_is_every_e2e_suite_in_the_catalog(self) -> None:
        catalog = {suite.id for suite in suite_catalog.SHIPLOOP_SUITES if suite.id.startswith("shiploop-e2e")}
        self.assertEqual(catalog, self.FAMILY)

    def test_an_edit_of_the_harness_runs_the_whole_family_in_the_quick_tier(self) -> None:
        for path in ("test/shiploop_e2e/run.py", "test/shiploop_e2e/metrics.py", "test/shiploop_e2e/fidelity.py",
                     "test/shiploop_e2e/sessionlog.py", "test/shiploop_e2e/environment.py"):
            with self.subTest(path=path):
                self.assertGreaterEqual(suite_catalog.targeted([path]), self.FAMILY)
                self.assertGreaterEqual({suite.id for suite in suite_catalog.quick([path])}, self.FAMILY)

    def test_the_committed_baseline_report_selects_the_suite_that_pins_it(self) -> None:
        # runs.json is the committed output of `run.py --baseline-report`; the baseline suite pins it. Its file name selects nothing.
        for path in ("docs/experiments/baseline-spread-20261009/runs.json",
                     "docs/experiments/baseline-spread-20261009/reduce_fixtures.py"):
            with self.subTest(path=path):
                self.assertIn("shiploop-e2e-baseline", suite_catalog.targeted([path]))

    def test_the_counters_evidence_and_fixtures_select_the_suite_that_pins_them(self) -> None:
        for path in ("docs/experiments/commit-baseline-20261010/baseline.json", "docs/experiments/commit-baseline-20261010/regrade.py",
                     "test/fixtures/commit-counters/grok/events.jsonl", "test/fixtures/commit-counters/messages.json"):
            with self.subTest(path=path):
                self.assertIn("shiploop-e2e-commit-counters", suite_catalog.targeted([path]))

    def test_a_frozen_copy_of_the_cli_entry_in_a_fixture_selects_only_the_suite_that_reads_it(self) -> None:
        # The baseline-report fixtures hold frozen copies of the CLI entry, each a file named shiploop. A name match ran
        # every ShipLoop suite for an edit of one fixture (71 suites, about nineteen minutes of the quick tier).
        path = "test/fixtures/baseline-spread/runs/x/build/plugins/skill-craft/skills/shiploop/scripts/shiploop"
        self.assertLessEqual(suite_catalog.targeted([path]), {"shiploop-e2e-baseline"})
        self.assertIn("shiploop-e2e-baseline", suite_catalog.targeted([path]))

    def test_the_real_cli_entry_still_selects_its_hub_consumers(self) -> None:
        self.assertGreater(len(suite_catalog.targeted(["skills/shiploop/scripts/shiploop"])), 1)

    def test_the_apparatus_is_not_part_of_the_family(self) -> None:
        self.assertNotIn("shiploop-e2e-apparatus", suite_catalog.targeted(["test/shiploop_e2e/run.py"]))


class VendoredRuntimeSelectionTests(unittest.TestCase):
    """F2 of the stop-rule branch: a change under the vendored Until Loop runtime reached the suites that start it only by
    accident of their names, so `installed-skill-invocation` (which starts the runtime from a read-only installed copy)
    and `until-loop-vendor` (which pins its provenance) were red on the branch and not selected by the quick tier."""

    RUNTIME = "skills/improve/runtime/until-loop/"

    def test_an_edit_of_the_runtime_selects_the_suites_that_start_or_pin_it(self) -> None:
        for name in ("scripts/until_loop_ephemeral.py", "ADAPTER.md", "PROVENANCE.json",
                     "references/runtime-ephemeral.md"):
            with self.subTest(path=name):
                selected = suite_catalog.targeted([self.RUNTIME + name])
                self.assertGreaterEqual(selected, {"until-loop-vendor", "installed-skill-invocation", "improve-runtime"})


class SelectionByReaderTest(unittest.TestCase):
    """Three files are selected by the suites that read them, not by a rule wider than their readers (test-economy review
    of 2026-10-17, section 3 rows 1, 3 and 4; each row is one assertion group here, and each fails without its row).

    Row 1: the E2E journal and the baseline data are read by named suites, yet the `test/shiploop_e2e/` prefix ran the whole
    15-suite family for them (102 of 378 harness commits in 30 days touched only such data; the family is about 578 s of
    catalog estimate, its readers of the journal 100 s and of the baseline data 200 s).  Row 3: `shiploop_workspace.py` is
    named by nine suites, one more than HUB_REFERENCE_LIMIT, so the hub set ran in their place and none of the suites that
    drive the module.  Row 4: four guidance documents were named by the 118 s chain-planning-context suite, which the 0.7 s
    anchor test of shiploop-reference-routing made redundant for them (the suite is retired with the chain, 2c-2).
    """

    LEARNINGS = "test/shiploop_e2e/LEARNINGS.md"
    BASELINES = "test/shiploop_e2e/baselines.jsonl"
    WORKSPACE = "skills/shiploop/scripts/shiploop_workspace.py"
    GUIDANCE_DOCS = ("coding-guidance.md", "house-style.md", "service-discovery.md", "repeatable-test-suites.md")

    def test_the_e2e_journal_selects_the_two_suites_that_read_it(self) -> None:
        self.assertEqual(suite_catalog.targeted([self.LEARNINGS]), {"shiploop-e2e", "release-preflight"})
        baseline = {suite.id for suite in suite_catalog.quick()}
        self.assertEqual({suite.id for suite in suite_catalog.quick([self.LEARNINGS])} - baseline,
                         {"shiploop-e2e", "release-preflight"})

    def test_the_baseline_data_selects_the_three_suites_that_read_it(self) -> None:
        self.assertEqual(suite_catalog.targeted([self.BASELINES]),
                         {"shiploop-e2e-baseline", "shiploop-e2e-platform", "shiploop-e2e"})

    def test_a_suite_that_names_either_data_file_is_listed_for_it(self) -> None:
        # The row is the whole selection, so a new reader that only names the file would be missed: it must be added to
        # the row.  This file names both paths (the quick baseline already runs it), so it is not counted as a reader.
        for path in (self.LEARNINGS, self.BASELINES):
            with self.subTest(path=path):
                self.assertLessEqual(suite_catalog._referencing(path) - {"test-groups"}, suite_catalog.targeted([path]))

    def test_the_other_harness_files_stay_on_the_family_prefix(self) -> None:
        # README.md is read through a path helper by shiploop-e2e-baseline, run.py and render_diff.py read cases.json,
        # suites.json and packet_changes.json: no file-name search sees these readers, so the whole family stays selected.
        for name in ("README.md", "cases.json", "suites.json", "packet_changes.json", "run.py", "render_diff.py"):
            with self.subTest(name=name):
                self.assertGreaterEqual(suite_catalog.targeted(["test/shiploop_e2e/" + name]), E2EFamilySelectionTest.FAMILY)

    def test_the_workspace_module_selects_its_domain_suites_and_not_the_hub(self) -> None:
        selected = suite_catalog.targeted([self.WORKSPACE])
        self.assertGreaterEqual(selected, {"shiploop-return-review", "shiploop-handoff", "shiploop-knowledge", "shiploop-workspace"})
        self.assertFalse(selected & set(suite_catalog._HUB_SUITE_IDS), selected & set(suite_catalog._HUB_SUITE_IDS))
        baseline = {suite.id for suite in suite_catalog.quick()}
        self.assertEqual({suite.id for suite in suite_catalog.quick([self.WORKSPACE])} - baseline,
                         {"shiploop-return-review", "shiploop-handoff", "shiploop-knowledge"})

    def test_the_other_hub_modules_keep_the_hub(self) -> None:
        for path in ("skills/shiploop/scripts/shiploop_navigator.py", "skills/shiploop/scripts/shiploop_store.py"):
            with self.subTest(path=path):
                self.assertGreaterEqual(suite_catalog.targeted([path]), set(suite_catalog._HUB_SUITE_IDS))

    def test_a_guidance_document_selects_the_anchor_test(self) -> None:
        for name in self.GUIDANCE_DOCS:
            path = "skills/shiploop/references/" + name
            with self.subTest(path=path):
                selected = suite_catalog.targeted([path])
                self.assertGreaterEqual(selected, {"shiploop-reference-routing", "shiploop-guidance"})


if __name__ == "__main__":
    unittest.main()
