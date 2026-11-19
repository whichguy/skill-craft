#!/usr/bin/env python3
"""Contracts for the declarative hermetic suite catalog and runner."""

from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock

# This suite and its Python fixtures suppress bytecode writes.
sys.dont_write_bytecode = True


ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = ROOT / "test"
sys.path.insert(0, str(TEST_DIR))
import ci_policy  # noqa: E402
import run_suites  # noqa: E402
import suite_catalog  # noqa: E402

E2E_SPLIT = {"shiploop-e2e-analysis", "shiploop-e2e-hosts", "shiploop-e2e-resources"}


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
        for name in ("suite_catalog.py", "suite_durations.json", "run_suites.py", "ci_summary.py", "run-all.sh"):
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
        # Current main's 97 ShipLoop suites plus four learning-loop contract suites, the SDLC probes, the closed loop's
        # two (2026-10-30), the seed seam suite, the stage suite's three (oracle, builder, runner), the optional UI adapter,
        # the stage suite's live tier's two (live core, report), two opt-in gym adapter suites, the test-writing adequacy suite, and
        # the follow-on chain's delta ledger, its third link and its fourth, the Python-floor suite (2026-10-31),
        # clean-consumer checks, review attribution, ticket semantics and Discovery scope calibration (2026-11-01),
        # the follow-on list's suite, incremental CSV pilot and both user-directory chain calibrations (2026-11-01).
        # Core gains backchain-graph (2026-11-01: Backchain's validator moved out of ShipLoop with its parity tests)
        # and backchain-toolkit (its command line), then native setup and the security harness.
        # Registered predecessors, their runner wiring and intent lifecycle calibration add three (2026-11-02).
        # The corpus summariser adds one (2026-11-03), so a figure can be re-derived by the code that produced it.
        # Grok chat adds one opt-in scenario adapter suite (2026-11-06).
        # Splitting the aggregate adds two; the full Grok case adds four suites (2026-11-07).
        # Roundtable adds one opt-in calibration suite (2026-11-07).
        # Nonblocking recovery adds one real-worktree suite (2026-11-12).
        # Retiring the Closed Loop adapter (3 suites) and all Salesforce/hosted suites (12 ShipLoop + 2 apparatus) brings SHIPLOOP_SUITES to 127.
        self.assertEqual(len(suite_catalog.SHIPLOOP_SUITES), 127)
        # The sport80 skill adds one core suite (2026-11-08): catalogue, CLI, drift and the in-page runtime under Node.
        # It lands beside the planning-score suite, which another session added at the same count (58 and 198), so both together make 59 and 199.
        # The pushpress skill adds one core suite (2026-11-08): card, links, lint and the in-page extractor under Node.
        # The test-harness skill adds one core suite (2026-11-08): its bundled behaviour suite, the packaging contract and a narrow lint.
        # The Ask Agent host command adds one core suite (2026-11-14): detection from exact variable names, and the binding data against the card and the prose.
        # Source-bound CI receipt reporting and the fake-Node browser driver each add one core suite (2026-11-15).
        # The closed-loop skill adds one core suite (2026-11-15): the orchestrator against a fake subject and the real Until Loop runtime.
        # The sport80 skill and its suite left for the fortified-strength repository (2026-11-15), so core is one fewer, 63, and all suites 206.
        # Backchain was retired (owner decision 2026-11-16): backchain-chunks and backchain-toolkit left with it, so core is 61
        # and all suites two fewer; backchain-graph stays, because its library moved into ShipLoop.
        self.assertEqual(len([suite for suite in suite_catalog.SUITES if suite.family == "core"]), 61)
        # Bundled Grok/GAS harness (2 suites), Closed Loop ShipLoop adapter (3 suites), and Salesforce/hosted cases (14 suites) retired (2026-11-19).
        self.assertEqual(len(suite_catalog.SUITES), 190)
        self.assertTrue(all(suite.hermetic for suite in suite_catalog.SUITES))
        self.assertTrue(all(suite.path in suite.argv for suite in suite_catalog.SUITES))
        self.assertTrue(all(suite.argv[0] in {"python3", "node", "bash"} for suite in suite_catalog.SUITES))
        suite_catalog.validate_catalog()

    def test_native_setup_pilot_is_core_and_selected_for_fixture_changes(self) -> None:
        pilot = next(suite for suite in suite_catalog.SUITES if suite.id == "native-setup-pilot")
        self.assertIn(pilot, suite_catalog.select(("core",)))
        self.assertIn(pilot, suite_catalog.select(("all",)))
        changed_fixture = "test/fixtures/native-setup-pilot/cases.json"
        self.assertIn(pilot, suite_catalog.quick((changed_fixture,)))

    def test_the_python_floor_group_is_every_shiploop_suite_except_the_e2e_apparatus(self) -> None:
        # Legacy local selector: use the caller's interpreter, without a repeated CI leg.
        selected = suite_catalog.select(("python-floor",))
        self.assertEqual(selected, tuple(suite for suite in suite_catalog.SHIPLOOP_SUITES
                                         if not suite.id.startswith("shiploop-e2e")))
        self.assertEqual({suite.family for suite in selected}, {"shiploop"})
        self.assertIn("shiploop-python-floor", {suite.id for suite in selected})
        self.assertIn("shiploop-clean-consumer", {suite.id for suite in selected})
        self.assertNotIn("python-floor", ci_policy.FULL_GROUPS)
        self.assertEqual(len(selected), 76)
        covered = Counter(suite.id for group in ci_policy.FULL_GROUPS
                          for suite in suite_catalog.select((group,)))
        self.assertTrue({suite.id for suite in selected} <= set(covered))
        self.assertTrue(all(covered[suite.id] == 1 for suite in selected))

    def test_full_ci_components_are_the_complete_deduplicated_union(self) -> None:
        full = suite_catalog.select(("all",))
        components = suite_catalog.select((
            "core", "shiploop-1", "shiploop-2", "shiploop-3", "e2e-apparatus",
        ))
        self.assertEqual(components, full)
        self.assertEqual(suite_catalog.select(ci_policy.FULL_GROUPS), full)
        # select(groups) deduplicates: flatten the actual CI jobs to expose repeated execution.
        executed = Counter(suite.id for group in ci_policy.FULL_GROUPS
                           for suite in suite_catalog.select((group,)))
        self.assertEqual(executed, Counter(suite.id for suite in suite_catalog.SUITES))
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
            "ask-agent-parallel", "ask-agent-task", "ask-agent-host",
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
        self.assertTrue({"test-groups", "ci-policy", "skill-frontmatter",
                         "shiploop-navigator-v4"} <= baseline)
        self.assertLess(len(baseline), 17)
        cases = {
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

    def test_planning_scoring_fixture_and_helper_changes_select_the_suite(self):
        for name in ["compare.py", "replay.json", "rubric.md"]:
            selected = {s.id for s in suite_catalog.select(["quick"], ["test/experiments/shiploop_spec_discovery/" + name])}
            self.assertIn("planning-score", selected)

    def test_planning_apparatus_tracks_its_entrypoints_and_dependencies(self) -> None:
        planning = {"planning-boundary", "planning-comparison"}
        comparison = {"planning-comparison"}
        self.assertLessEqual(planning, {suite.id for suite in suite_catalog.select(("e2e-apparatus",))})
        cases = {
            "test/shiploop-e2e-planning-boundary.test.py": planning,  # Also the comparison fixture.
            "test/shiploop-e2e-planning-comparison.test.py": comparison,
            "test/shiploop_e2e/metrics.py": planning,
            "test/shiploop_e2e/slice.py": comparison,
            "test/shiploop_e2e/planning_boundary.py": planning,
            "test/shiploop_e2e/planning_comparison.py": comparison,
            "test/shiploop_e2e/planning_evidence.py": comparison,
            "test/shiploop_e2e/planning_trace.py": planning,
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                selected = {suite.id for suite in suite_catalog.quick((path,))}
                self.assertEqual(selected & planning, expected)

    def test_planning_apparatus_is_absent_for_unrelated_shiploop_edits(self) -> None:
        planning = {"planning-boundary", "planning-comparison"}
        for path in ("skills/shiploop/scripts/shiploop_workspace.py",
                     "skills/shiploop/scripts/shiploop_keepalive.py"):
            with self.subTest(path=path):
                self.assertTrue(planning.isdisjoint(suite_catalog.targeted((path,))))

    def test_planning_boundary_timeline_does_not_turn_retained_fixtures_into_hubs(self) -> None:
        fixtures = TEST_DIR / "fixtures/fidelity"
        timeline = next(fixtures.glob("*/.shiploop-runs/*/run/timeline[.]json"))
        path = timeline.relative_to(ROOT).as_posix()
        real = suite_catalog._suite_sources()
        more = {f"fake-observer-{n}": 'name = "timeline.json"\n'
                for n in range(2 * suite_catalog.HUB_REFERENCE_LIMIT)}
        for sources in (real, {**real, **more}):
            with self.subTest(synthetic_references=len(sources) - len(real)):
                with mock.patch.object(suite_catalog, "_suite_sources", return_value=sources):
                    for fixture in (path, "test/fixtures/fidelity/extract.py"):
                        selected = suite_catalog.targeted((fixture,))
                        self.assertEqual(selected, {"shiploop-e2e-fidelity"})
                        self.assertNotIn("planning-boundary", selected)
                        self.assertTrue(selected.isdisjoint(suite_catalog._HUB_SUITE_IDS))

        # The exception is scoped to retained fidelity data. Ordinary sources
        # and other fixtures still reach basename consumers, including planning.
        sources = {"planning-boundary": 'name = "timeline.json"\n',
                   "shiploop-e2e-fidelity": "import synthetic_fidelity_reader\n"}
        with mock.patch.object(suite_catalog, "_suite_sources", return_value=sources):
            for control in ("test/fixtures/synthetic/timeline.json",
                            "skills/shiploop/scripts/timeline.json"):
                self.assertIn("planning-boundary", suite_catalog.targeted((control,)))
            self.assertIn("shiploop-e2e-fidelity", suite_catalog.targeted(
                ("skills/shiploop/scripts/synthetic_fidelity_reader.py",)))

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

    def test_quick_direct_edits_override_only_their_own_exclusion(self) -> None:
        baseline = {s.id for s in suite_catalog.smoke()}
        for suite in suite_catalog.SUITES:
            changed = [suite.path]
            selected = {s.id for s in suite_catalog.quick(changed)}
            old = (baseline | suite_catalog.targeted(changed)) - suite_catalog._FULL_ONLY_IDS
            self.assertLessEqual(old, selected)
            self.assertIn(suite.id, selected)
            self.assertEqual(selected & suite_catalog._FULL_ONLY_IDS,
                             {s.id for s in suite_catalog.SUITES if s.path == suite.path} & suite_catalog._FULL_ONLY_IDS)
        for path in ("test/shiploop_e2e/run.py", "skills/shiploop/scripts/shiploop_workspace.py",
                     "test/fixtures/quality/record.json"):
            self.assertFalse({s.id for s in suite_catalog.quick([path])} & suite_catalog._FULL_ONLY_IDS)

    def test_scoped_runner_cli_lists_the_catalog_selection(self) -> None:
        changed = run_suites.changed_paths(ROOT, "HEAD")
        for group in ("smoke", "affected", "quick-1", "quick-2"):
            command = ["bash", str(ROOT / "test/run-all.sh"), "--group", group, "--list"]
            if group != "smoke":
                command += ["--changed-from", "HEAD"]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual([line.split("\t")[1] for line in result.stdout.splitlines()],
                             [s.id for s in suite_catalog.select([group], changed)])

    def test_original_inventory_commands_and_groups_are_unchanged(self) -> None:
        # All 190 rows after retiring the bundled harness, Closed Loop adapter, and Salesforce suites (2026-11-19).
        import hashlib
        records = [(s.id, s.family, s.path, list(s.argv), sorted(s.groups), s.timeout_seconds, s.hermetic)
                   for s in suite_catalog.SUITES]
        digest = hashlib.sha256(json.dumps(records, separators=(',', ':')).encode()).hexdigest()
        self.assertEqual(digest, "a5d87ecb26697c9e112f7e6467f72617cdd1b974b95fe08edc1b973cbce301fc")

    def test_smoke_affected_union_is_exact_and_full_inventory_is_preserved(self) -> None:
        full = suite_catalog.select(["all"])
        for changed in ([], [s.path for s in full], ["skills/shiploop/scripts/shiploop_prompts.py"]):
            smoke = set(suite_catalog.smoke())
            affected = set(suite_catalog.affected(changed))
            self.assertFalse(smoke & affected)
            self.assertEqual(smoke | affected, set(suite_catalog.quick(changed)))
            self.assertEqual(suite_catalog.select(["smoke", "affected"], changed), suite_catalog.quick(changed))
            self.assertEqual(suite_catalog.select(["all"], changed), full)
            self.assertEqual(suite_catalog.select(["affected"], changed), suite_catalog.affected(changed))
        self.assertEqual(len(suite_catalog.select(["python-floor"])), 76)

    def test_full_only_membership_is_explicit_and_independent_of_timings(self) -> None:
        self.assertEqual(suite_catalog._FULL_ONLY_IDS, {
            "plan-dispatcher-mutants", "shiploop-full-runtime", "shiploop-workspace",
            "shiploop-e2e-test-adequacy", "shiploop-e2e-ticket-sla", "shiploop-e2e-user-directory",
        })
        paths = [suite.path for suite in suite_catalog.SUITES]
        before = suite_catalog.quick(paths)
        with mock.patch.dict(suite_catalog._DURATION_SECONDS, {"test/shiploop-privacy.test.py": 999.0}):
            self.assertEqual(suite_catalog.quick(paths), before)
            with self.assertRaisesRegex(ValueError, "explicit coverage decision: shiploop-privacy"):
                suite_catalog.validate_catalog()
        with mock.patch.dict(suite_catalog._DURATION_SECONDS, {"test/shiploop-workspace.test.py": 1.0}):
            self.assertEqual(suite_catalog.quick(paths), before)

    def test_shiploop_costs_are_required_and_finite(self) -> None:
        path = "test/shiploop-privacy.test.py"
        without = {key: value for key, value in suite_catalog._DURATION_SECONDS.items() if key != path}
        with mock.patch.object(suite_catalog, "_DURATION_SECONDS", without):
            with self.assertRaisesRegex(ValueError, "explicit scheduling costs"):
                suite_catalog.validate_catalog()
        for value in (float("inf"), float("nan"), -1.0):
            with self.subTest(value=value), mock.patch.dict(suite_catalog._DURATION_SECONDS, {path: value}):
                with self.assertRaisesRegex(ValueError, "finite non-negative"):
                    suite_catalog.validate_catalog()

    def test_split_components_count_as_one_consumer_at_the_hub_boundary(self) -> None:
        token = "synthetic_shared_module"
        path = f"test/{token}.py"
        split = {identifier: f"import {token}" for identifier in E2E_SPLIT}
        six = {f"fake-consumer-{index}": f"import {token}" for index in range(6)}
        with mock.patch.object(suite_catalog, "_suite_sources", return_value={**split, **six}):
            self.assertEqual(suite_catalog.targeted([path]), {*split, *six})
        eight = {f"fake-consumer-{index}": f"import {token}" for index in range(8)}
        with mock.patch.object(suite_catalog, "_suite_sources", return_value={**split, **eight}):
            self.assertEqual(suite_catalog.targeted([path]), set(suite_catalog._HUB_SUITE_IDS))

    def test_split_files_preserve_the_aggregate_family_selection(self) -> None:
        for path in ("test/shiploop-e2e.test.py", "test/shiploop-e2e-support.py",
                     *(f"test/{identifier}.test.py" for identifier in E2E_SPLIT)):
            with self.subTest(path=path):
                self.assertEqual(suite_catalog.targeted([path]),
                                 {*suite_catalog._E2E_FAMILY_IDS})
                self.assertGreaterEqual({suite.id for suite in suite_catalog.prompt([path])}, E2E_SPLIT)

    def test_split_support_and_components_are_protected_from_candidate_edits(self) -> None:
        paths = ["test/shiploop-e2e-support.py", *(f"test/{identifier}.test.py" for identifier in E2E_SPLIT)]
        probe = (
            "import sys; sys.path.insert(0, 'test/shiploop_e2e'); import boundary; "
            "assert not any(boundary.candidate_path(path) for path in sys.argv[1:]), sys.argv[1:]"
        )
        checked = subprocess.run([sys.executable, "-B", "-c", probe, *paths], cwd=ROOT,
                                 capture_output=True, text=True, timeout=30)
        self.assertEqual(checked.returncode, 0, checked.stderr)

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
        self.assertIn("--changed-from applies only to --group quick, quick-1, quick-2, prompt or affected", refused.stderr)

    def test_reporting_does_not_add_spurious_catalog_readers(self):
        keepalive = "skills/shiploop/scripts/shiploop_keepalive.py"
        selected = {suite.id for suite in suite_catalog.quick([keepalive])}
        self.assertTrue({"shiploop-e2e-slice", "shiploop-loops", "shiploop-skill-calls",
                         "shiploop-trace"} <= selected)
        for path in (keepalive, "test/shiploop_e2e/LEARNINGS.md",
                     "test/shiploop_e2e/baselines.jsonl", "skills/in-parallel/SKILL.md"):
            with self.subTest(path=path):
                self.assertNotIn("ci-summary", suite_catalog.targeted([path]))

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

    def test_quick_shards_preserve_exact_selection_order_and_floor(self) -> None:
        from unittest.mock import patch
        for changed in ((), ("docs/README.md",), ("test/shiploop_e2e/run.py",),
                        tuple(s.path for s in suite_catalog.SUITES)):
            with self.subTest(changed=changed):
                quick = suite_catalog.quick(changed)
                shards = [suite_catalog.select([g], changed) for g in ("quick-1", "quick-2")]
                self.assertFalse(set(shards[0]) & set(shards[1]))
                self.assertEqual(set(shards[0]) | set(shards[1]), set(quick))
                for shard in shards:
                    self.assertEqual(shard, tuple(s for s in quick if s in shard))
                self.assertEqual(suite_catalog.select(["quick-1", "quick-2"], iter(changed)), quick)
                for group in ("quick-1", "quick-2"):
                    self.assertIn(group, run_suites.parse_args(["--group", group, "--changed-from", "HEAD"])[1])
        self.assertEqual(suite_catalog.planned_quick_groups(["docs/README.md"]), ("quick",))
        broad = ("test/shiploop_e2e/run.py",)
        self.assertEqual(suite_catalog.planned_quick_groups(broad), ("quick-1", "quick-2"))
        baseline = suite_catalog.smoke()
        # Four-worker FIFO: four equal jobs fill one wave; the fifth extends it.
        with patch.object(suite_catalog, "_DURATION_SECONDS", {s.path: 300 for s in baseline}):
            self.assertEqual(suite_catalog.quick_fifo_seconds(baseline[:4]), 300)
            self.assertEqual(suite_catalog.quick_fifo_seconds(baseline[:5]), 600)
        for estimate, expected in ((599.9, ("quick",)), (600, ("quick",)),
                                   (600.1, ("quick-1", "quick-2"))):
            with patch.object(suite_catalog, "quick_fifo_seconds", return_value=estimate):
                self.assertEqual(suite_catalog.planned_quick_groups(broad), expected)
        with patch.object(suite_catalog, "_DURATION_SECONDS", {}):
            self.assertEqual(suite_catalog.quick_fifo_seconds(baseline[:5]), 120)
            self.assertEqual(suite_catalog.quick(broad), suite_catalog.select(["quick-1", "quick-2"], broad))
        # Independent reconstruction of the old three-bin LPT partition.
        loads, members = [0.0] * 3, [set(), set(), set()]
        canonical = suite_catalog.SHIPLOOP_SUITES
        for index, suite in sorted(enumerate(canonical),
                                   key=lambda item: (-suite_catalog._DURATION_SECONDS[item[1].path], item[0])):
            owner = min(range(3), key=lambda i: (loads[i], i))
            members[owner].add(suite.id)
            loads[owner] += suite_catalog._DURATION_SECONDS[suite.path]
        old = tuple(tuple(s for s in canonical if s.id in ids) for ids in members)
        self.assertEqual(suite_catalog.SHIPLOOP_SHARDS, old)
        self.assertEqual(len(suite_catalog.select(["python-floor"])), 76)

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


class CIGitMaintenanceTest(unittest.TestCase):
    """The CI step that turns git's background maintenance off works for a suite the runner starts, without GIT_CONFIG_*.

    A commit makes git start `git maintenance run --auto --quiet --detach`, which holds objects/maintenance.lock for a moment, and
    four fixtures that inventory or copy a tree right after a commit lost the lock to it on CI (2026-10-26 to 2026-11-14).  The
    runner removes GIT_CONFIG_* from every suite on purpose (78594ebb: ask-agent's workspace guard refuses them), so the setting
    is a global one that the workflow's own step makes.  This runs that step's command under a fresh HOME, as on a CI machine,
    and has a child that run_process starts make fixture commits there.
    """

    PROGRAM = textwrap.dedent("""\
        import json, os, subprocess, sys
        repo, launches = sys.argv[1], 0
        for number in range(2):
            trace = os.path.join(repo, f"trace{number}.json")
            subprocess.run(["git", "-C", repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                            "commit", "--allow-empty", "-qm", "fixture"], check=True, env=dict(os.environ, GIT_TRACE2_EVENT=trace))
            events = [json.loads(line) for line in open(trace)]
            launches += sum(1 for e in events if e.get("event") == "child_start" and "maintenance" in (e.get("argv") or []))
        print(launches)
    """)

    def launches(self, root: Path, step: str | None) -> int:
        """Detached maintenance launches over two fixture commits on a machine whose HOME has had `step` run."""
        home, repo = root / "home", root / "repo"
        home.mkdir()
        environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_CONFIG_")}
        environment.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"), GIT_CONFIG_NOSYSTEM="1")
        with mock.patch.dict(os.environ, environment, clear=True):
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            if step is not None:
                subprocess.run(shlex.split(step), check=True)
            program = root / "commits.py"
            program.write_text(self.PROGRAM, encoding="utf-8")
            outcome = run_suites.run_process((sys.executable, "-B", str(program), str(repo)), cwd=root, timeout_seconds=60)
        self.assertEqual(outcome.status, "passed", (outcome.error or "") + outcome.stderr)
        return int(outcome.stdout.strip())

    def test_the_workflows_step_stops_a_fixture_commit_from_starting_maintenance_for_a_suite_the_runner_starts(self) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        steps = re.findall(r"^      - name: Keep git's background maintenance out of the suites\n        run: (.+)$", workflow,
                           re.MULTILINE)
        self.assertEqual(len(steps), 1, "the checks job has no single step with this name")
        with tempfile.TemporaryDirectory(prefix="skill-craft-maintenance-") as name:
            root = Path(name).resolve()
            (root / "without").mkdir()
            (root / "with").mkdir()
            without = self.launches(root / "without", None)
            with_step = self.launches(root / "with", steps[0])
        self.assertGreater(without, 0, "this git starts no background maintenance after a commit, so the step has nothing to stop")
        self.assertEqual(with_step, 0, f"the step `{steps[0]}` left {with_step} of {without} launches")


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
    E2E_SPEC_READERS = {*E2E_SPLIT, "shiploop-navigator-contract", "shiploop-run-review"}

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
            "test/shiploop_e2e/run.py": E2E_SPLIT,
            "test/shiploop_e2e/review.py": E2E_SPLIT,
            "skills/plan-dispatcher/SKILL.md": self.PLAN_DISPATCHER,
            "skills/rubric-eval/SPEC.md": {"rubric-eval"},
            "skills/rubric-eval/suites/architecture-v4/frames/review.txt": {"rubric-eval"},
            "skills/review-coverage/SKILL.md": {"review-coverage"},
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertGreaterEqual(self.selected(path), expected)


class E2EFamilySelectionTest(unittest.TestCase):
    """Harness edits target the whole E2E family; quick runs its light members.

    The harness's modules (run.py, metrics.py, fidelity.py, sessionlog.py, environment.py) have names too common to select by,
    and each family suite reads them through run.py or metrics.py: before, the prefix selected shiploop-e2e alone (and, after
    group G2, shiploop-e2e-reorientation), so an edit of metrics.py skipped the fidelity, runrecord and environment suites.
    The family is pinned as it stands on this branch, so a merged group that adds a suite updates this list on purpose.
    """

    FAMILY = {*E2E_SPLIT, "shiploop-e2e-runrecord", "shiploop-e2e-fidelity", "shiploop-e2e-reorientation",
              "shiploop-e2e-environment", "shiploop-e2e-baseline", "shiploop-e2e-quality",
              "shiploop-e2e-packet-anatomy", "shiploop-e2e-render-diff", "shiploop-e2e-commit-counters", "shiploop-e2e-slice",
              "shiploop-e2e-platform", "shiploop-e2e-status-card",
              "shiploop-e2e-efficiency", "shiploop-e2e-dodges", "shiploop-e2e-owner-page", "shiploop-e2e-experiments",
              "shiploop-e2e-sdlc-probes", "shiploop-e2e-review-attribution", "shiploop-e2e-ticket-semantics",
              "shiploop-e2e-scope-discovery", "shiploop-e2e-stage-oracle", "shiploop-e2e-stage-build", "shiploop-e2e-stages",
              "shiploop-e2e-stage-live", "shiploop-e2e-stage-report",
              "shiploop-e2e-run-trace", "shiploop-e2e-brownfield", "shiploop-e2e-brownfield-tickets", "shiploop-e2e-test-adequacy",
              "shiploop-e2e-delta", "shiploop-e2e-corpus", "shiploop-e2e-incremental-pilot", "shiploop-e2e-ticket-comments", "shiploop-e2e-ticket-sla", "shiploop-e2e-user-chain",
              "shiploop-e2e-user-directory",
              "shiploop-e2e-recovery", "shiploop-e2e-lifecycle", "shiploop-e2e-discovery", "shiploop-e2e-qualification",
              "shiploop-e2e-roles", "shiploop-e2e-roundtable", "shiploop-e2e-epoch", "shiploop-e2e-learning-records", "shiploop-e2e-cycle",
              "shiploop-e2e-predecessor", "shiploop-e2e-predecessor-wiring", "shiploop-e2e-intent-continuity"}

    def test_the_pinned_family_is_every_e2e_suite_in_the_catalog(self) -> None:
        catalog = {suite.id for suite in suite_catalog.SHIPLOOP_SUITES if suite.id.startswith("shiploop-e2e")}
        self.assertEqual(catalog, self.FAMILY)

    def test_an_edit_of_the_harness_targets_the_family_and_quick_runs_its_light_members(self) -> None:
        light_family = {suite.id for suite in suite_catalog.SHIPLOOP_SUITES
                        if suite.id in self.FAMILY and suite_catalog._light(suite)}
        for path in ("test/shiploop_e2e/run.py", "test/shiploop_e2e/metrics.py", "test/shiploop_e2e/fidelity.py",
                     "test/shiploop_e2e/sessionlog.py", "test/shiploop_e2e/environment.py"):
            with self.subTest(path=path):
                self.assertGreaterEqual(suite_catalog.targeted([path]), self.FAMILY)
                selected = {suite.id for suite in suite_catalog.quick([path])}
                self.assertEqual(selected & self.FAMILY, light_family)

    def test_the_measured_adequacy_calibration_is_targeted_but_runs_in_the_full_tier(self) -> None:
        ident = "shiploop-e2e-test-adequacy"
        suite = next(suite for suite in suite_catalog.SHIPLOOP_SUITES if suite.id == ident)
        self.assertGreater(suite_catalog._DURATION_SECONDS[suite.path], suite_catalog.QUICK_MAX_SECONDS)
        self.assertIn(ident, {suite.id for suite in suite_catalog.select(ci_policy.FULL_GROUPS)})
        for path in (suite.path, "test/shiploop_e2e/checks/ticket_test_adequacy.py",
                     "test/shiploop_e2e/checks/ticket_test_variants.py",
                     "test/shiploop_e2e/fixtures/node-tickets-assigned/src/app.js",
                     "test/fixtures/quality/ticket_adequacy_strong.test.js"):
            with self.subTest(path=path):
                self.assertIn(ident, suite_catalog.targeted([path]))
                self.assertEqual(ident in {suite.id for suite in suite_catalog.quick([path])}, path == suite.path)

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

    def test_the_e2e_journal_selects_its_named_suites(self) -> None:
        self.assertEqual(suite_catalog.targeted([self.LEARNINGS]),
                         {*E2E_SPLIT, "release-preflight", "shiploop-actual-improve-cli"})
        baseline = {suite.id for suite in suite_catalog.quick()}
        self.assertEqual({suite.id for suite in suite_catalog.quick([self.LEARNINGS])} - baseline,
                         {*E2E_SPLIT, "release-preflight", "shiploop-actual-improve-cli"})

    def test_the_baseline_data_selects_its_named_suites(self) -> None:
        self.assertEqual(suite_catalog.targeted([self.BASELINES]),
                         {"shiploop-e2e-baseline", "shiploop-e2e-platform", *E2E_SPLIT, "shiploop-e2e-epoch"})

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
        # and an edit to the navigator also selects the seed seam's equivalence test, which no hub rule finds
        self.assertIn("shiploop-seed-seam", suite_catalog.targeted(["skills/shiploop/scripts/shiploop_navigator.py"]))

    def test_a_guidance_document_selects_the_anchor_test(self) -> None:
        for name in self.GUIDANCE_DOCS:
            path = "skills/shiploop/references/" + name
            with self.subTest(path=path):
                selected = suite_catalog.targeted([path])
                self.assertGreaterEqual(selected, {"shiploop-reference-routing", "shiploop-guidance"})


class SuiteEnvironmentIsolationTest(unittest.TestCase):
    """What the runner hands a suite, and what it must never hand it."""

    def test_the_runner_strips_git_context_overrides_from_every_suite(self) -> None:
        """A developer's GIT_CONFIG_* shell setup changed what three suites did, on 2026-11-04.

        `GIT_CONFIG_COUNT=1, GIT_CONFIG_KEY_0=core.quotePath, GIT_CONFIG_VALUE_0=false` in the shell is a common local
        setup.  ask-agent's workspace guard refuses it by design, so ask-agent-parallel, agent-harness-audit and
        install-arbitrary-skill all failed with "prepare refuses Git context environment overrides" -- and all three
        passed once it was unset.  A suite's Git identity and configuration come from its fixture, never from the shell
        that happened to start it.
        """
        import run_suites

        self.assertIn("GIT_CONFIG_COUNT", run_suites._INHERITED_OVERRIDES)
        for key in ("GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0"):
            self.assertIn(key, run_suites._INHERITED_OVERRIDES)
        # The state overrides it already carried must stay.
        for key in ("UNTIL_LOOP_STATE_DIR", "SHIPLOOP_KEEPALIVE_HOME"):
            self.assertIn(key, run_suites._INHERITED_OVERRIDES)

    def test_a_suite_gets_the_state_overrides_and_the_git_overrides_removed(self) -> None:
        import os
        import run_suites
        from unittest import mock

        planted = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.quotePath", "GIT_CONFIG_VALUE_0": "false",
                   "UNTIL_LOOP_STATE_DIR": "/tmp/elsewhere", "PATH": "/usr/bin:/bin"}
        with mock.patch.dict(os.environ, planted, clear=False):
            environment = {key: value for key, value in os.environ.items()
                           if key not in run_suites._INHERITED_OVERRIDES}
        for removed in ("GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0", "UNTIL_LOOP_STATE_DIR"):
            self.assertNotIn(removed, environment)
        self.assertIn("PATH", environment, "everything else is inherited")


@unittest.skipUnless(os.name == "posix", "private process-group contract is POSIX")
class SuiteGroupOwnershipTest(unittest.TestCase):
    """Real children, bounded race gates, and identity-checked fallback cleanup.

    No waitid/procfs dependency: ps exposes birth, group, state and the unique
    argv marker on both supported POSIX hosts. Zombies count as stopped.
    """

    def setUp(self) -> None:
        import threading
        self.threading = threading
        self.temporary = tempfile.TemporaryDirectory(prefix="suite-owner-")
        self.root = Path(self.temporary.name).resolve()
        self.real_popen = subprocess.Popen
        self.real_popen_init = self.real_popen.__init__
        self.owned = []
        self.processes = []
        self.releases = []
        self.threads = []
        self.addCleanup(self._cleanup)
        self.child = self.root / "child.py"
        self.child.write_text(textwrap.dedent('''\
            import json, os, signal, sys, time
            sys.dont_write_bytecode = True
            from pathlib import Path
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            with open(os.devnull, 'wb') as stream:
                os.dup2(stream.fileno(), 1)
                os.dup2(stream.fileno(), 2)
            ready = Path(sys.argv[1])
            temporary = ready.with_suffix('.tmp')
            temporary.write_text(json.dumps({'pid': os.getpid(), 'pgid': os.getpgrp(), 'marker': sys.argv[2]}))
            temporary.replace(ready)
            time.sleep(120)
        '''), encoding="utf-8")
        self.leader = self.root / "leader.py"
        self.leader.write_text(textwrap.dedent('''\
            import os, subprocess, sys, time
            sys.dont_write_bytecode = True
            from pathlib import Path
            child, ready, gate, marker, mode = sys.argv[1:]
            subprocess.Popen([sys.executable, '-B', child, ready, marker + '-child'])
            deadline = time.monotonic() + 45
            while not Path(gate).exists() and time.monotonic() < deadline:
                time.sleep(.01)
            if not Path(gate).exists():
                raise SystemExit(91)
            os.write(1, b'suite-owner-out\\n')
            os.write(2, b'suite-owner-err\\n')
            if mode == 'sleep':
                time.sleep(120)
            else:
                raise SystemExit(int(mode))
        '''), encoding="utf-8")

    def _until(self, predicate, seconds=10):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if predicate():
                return True
            time.sleep(.01)
        return bool(predicate())

    def _identity(self, pid, *, timeout=10):
        # Use the original Popen: race injection targets suite launches only.
        observer = self.real_popen(
            ["ps", "-ww", "-p", str(pid), "-o", "lstart=", "-o", "pgid=", "-o", "stat=", "-o", "args="],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace",
        )
        output, error = observer.communicate(timeout=timeout)
        if observer.returncode != 0 or not output.strip():
            return None
        fields = output.strip().split(None, 7)
        self.assertEqual(len(fields), 8, output + error)
        return (" ".join(fields[:5]), int(fields[5]), fields[6], fields[7])

    def _remember(self, pid, marker, group):
        self.assertIsInstance(pid, int, "actual fixture PID must be numeric")
        self.assertGreater(pid, 0, "actual fixture PID must be positive")
        self.assertIsInstance(group, int, "actual fixture PGID must be numeric")
        self.assertGreater(group, 0, "actual fixture PGID must be positive")
        # Popen can return before ps exposes exec's full argv on macOS.
        # Capture only a fully visible identity, while the launch gate is closed.
        deadline = time.monotonic() + 10
        identity, visible = None, False
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            identity = self._identity(pid, timeout=remaining)
            visible = bool(identity and identity[0] and identity[1] == group
                           and marker in identity[3])
            if visible:
                break
            time.sleep(min(.01, max(0, deadline - time.monotonic())))
        self.assertTrue(visible, "fixture identity visibility deadline expired: %r" % (identity,))
        self.assertIsNotNone(identity, "ready process disappeared before identity capture")
        self.assertTrue(identity[0], "actual fixture birth must be nonempty")
        self.assertIn(marker, identity[3])
        self.assertEqual(identity[1], group)
        record = (pid, marker, identity[0], group)
        self.owned.append(record)
        return record

    def _alive(self, record):
        pid, marker, birth, group = record
        identity = self._identity(pid)
        return bool(identity and identity[0] == birth and identity[1] == group
                    and marker in identity[3] and not identity[2].startswith("Z"))

    def _cleanup(self):
        for release in self.releases:
            release.set()
        try:
            # Never signal a group or an unverified/reused PID in test fallback.
            for record in reversed(self.owned):
                if self._alive(record):
                    try:
                        os.kill(record[0], signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            for thread in self.threads:
                thread.join(15)
            for process in self.processes:
                process.wait(timeout=15)
            self.assertFalse(any(thread.is_alive() for thread in self.threads),
                             "race worker outlived fallback cleanup")
        finally:
            for process in self.processes:
                for stream in (process.stdout, process.stderr):
                    if stream is not None:
                        stream.close()
            self.temporary.cleanup()

    def _command(self, tag, mode):
        marker = self.root.name + "-" + tag
        ready, gate = self.root / (tag + ".json"), self.root / (tag + ".go")
        argv = (sys.executable, "-B", str(self.leader), str(self.child), str(ready), str(gate), marker, str(mode))
        return argv, ready, gate, marker

    def _capture(self, process, ready, marker):
        self.assertIsInstance(process, self.real_popen)
        self.assertGreater(process.pid, 0)
        self.processes.append(process)
        self.assertTrue(self._until(ready.exists), "child readiness deadline expired")
        # The launch gate stays closed through leader and actual-child capture.
        leader = self._remember(process.pid, marker, process.pid)
        record = json.loads(ready.read_text(encoding="utf-8"))
        self.assertGreater(record["pid"], 0)
        self.assertEqual(record["marker"], marker + "-child")
        child = self._remember(record["pid"], record["marker"], process.pid)
        self.assertEqual(record["pgid"], process.pid)
        return leader, child

    def _decoy(self):
        marker = self.root.name + "-decoy"
        ready = self.root / "decoy.json"
        process = self.real_popen([sys.executable, "-B", str(self.child), str(ready), marker],
                                  start_new_session=True)
        self.processes.append(process)
        record = self._remember(process.pid, marker, process.pid)
        self.assertTrue(self._until(ready.exists), "decoy readiness deadline expired")
        observed = json.loads(ready.read_text(encoding="utf-8"))
        self.assertGreater(observed["pid"], 0)
        self.assertEqual(observed, {"pid": process.pid, "pgid": process.pid, "marker": marker})
        self.assertTrue(self._alive(record))
        return record

    def test_completion_ends_closed_pipe_descendants_and_preserves_result_without_waitid(self):
        import contextlib
        import importlib.util
        # Exercise Darwin's libc fallback independently of the caller's waitid capability.
        # Masking waitid on Linux does not exercise the Darwin ABI. Never fake sys.platform.
        @contextlib.contextmanager
        def without_waitid():
            absent = object()
            original = getattr(os, "waitid", absent)
            if original is not absent:
                del os.waitid
            try:
                yield
            finally:
                if original is not absent:
                    os.waitid = original
                elif hasattr(os, "waitid"):
                    del os.waitid
        decoy = self._decoy()
        variants = (False, True) if sys.platform == "darwin" else (False,)
        for missing_waitid in variants:
            capability = without_waitid() if missing_waitid else contextlib.nullcontext()
            with capability:
                name = "_suite_owner_floor_runner"
                spec = importlib.util.spec_from_file_location(name, TEST_DIR / "run_suites.py")
                runner = importlib.util.module_from_spec(spec)
                with mock.patch.dict(sys.modules, {name: runner}):
                    spec.loader.exec_module(runner)
                    for code in (0, 23):
                        with self.subTest(missing_waitid=missing_waitid, code=code):
                            argv, ready, gate, marker = self._command("exit-%s-%s" % (missing_waitid, code), code)
                            captured = []
                            def started(process):
                                captured.extend(self._capture(process, ready, marker))
                                gate.touch()
                            outcome = runner.run_process(argv, cwd=self.root, timeout_seconds=10, on_start=started)
                            self.assertEqual(len(captured), 2, "suite and ready child must both be captured")
                            self.assertTrue(ready.exists())
                            self.assertTrue(all(record[0] > 0 for record in captured))
                            self.assertTrue(self._until(lambda: not self._alive(captured[1]), 10),
                                            "same-group child survived suite completion before fixture fallback")
                            self.assertEqual(outcome.status, "passed" if code == 0 else "failed")
                            self.assertEqual(outcome.returncode, code)
                            self.assertEqual(outcome.stdout, "suite-owner-out\n")
                            self.assertEqual(outcome.stderr, "suite-owner-err\n")
                            self.assertIsNone(outcome.error)
                            self.assertTrue(self._alive(decoy), "unrelated private group was signalled")

    def test_callback_failure_and_serial_interrupt_clean_group_and_keep_exception_identity(self):
        decoy = self._decoy()
        for index, sentinel in enumerate((RuntimeError("callback sentinel"), KeyboardInterrupt("serial sentinel"))):
            with self.subTest(exception=type(sentinel).__name__):
                argv, ready, gate, marker = self._command("callback-%s" % index, "sleep")
                captured = []
                def initialize(process, *args, **kwargs):
                    # Delegate first, preserving the real class and actual Popen.
                    self.real_popen_init(process, *args, **kwargs)
                    actual_argv = args[0] if args else kwargs.get("args")
                    if actual_argv is not None and tuple(actual_argv) == argv:
                        captured.extend(self._capture(process, ready, marker))
                def raises(process):
                    raise sentinel
                def suite(*args, **kwargs):
                    return run_suites.run_process(argv, cwd=self.root, timeout_seconds=10, on_start=raises)
                with mock.patch.object(self.real_popen, "__init__", new=initialize):
                    with mock.patch.object(run_suites, "_run_suite", side_effect=suite):
                        try:
                            list(run_suites._outcomes([object()], jobs=1))
                        except BaseException as caught:
                            self.assertIs(caught, sentinel)
                        else:
                            self.fail("callback exception was swallowed")
                self.assertEqual(len(captured), 2, "constructor hook must capture the real suite and child")
                self.assertTrue(ready.exists())
                self.assertTrue(all(record[0] > 0 for record in captured))
                self.assertTrue(self._until(lambda: not any(self._alive(r) for r in captured), 10),
                                "callback/serial interrupt leaked its actual Popen group before fallback")
                self.assertTrue(self._alive(decoy))

    def _controller(self, selected):
        result, done = [], self.threading.Event()
        self.releases.append(done)
        def consume():
            try:
                list(run_suites._outcomes(selected, jobs=2))
            except BaseException as error:
                result.append(error)
            finally:
                done.set()
        thread = self.threading.Thread(target=consume, daemon=True)
        self.threads.append(thread)
        thread.start()
        return result, done

    def test_parallel_cancellation_covers_actual_popen_registered_after_shutdown(self):
        ready_event, release, worker_done, registered, collect = (self.threading.Event() for _ in range(5))
        self.releases.extend((release, collect))
        sentinel = RuntimeError("cancel before registration")
        argv, ready, gate, marker = self._command("late", "sleep")
        captured, failures = [], []
        decoy = self._decoy()
        def initialize(process, *args, **kwargs):
            self.real_popen_init(process, *args, **kwargs)
            actual_argv = args[0] if args else kwargs.get("args")
            # ps observers and the independent decoy never enter this branch.
            if actual_argv is not None and tuple(actual_argv) == argv:
                captured.extend(self._capture(process, ready, marker))
                gate.touch()
                ready_event.set()
                if not release.wait(45):
                    failures.append("late-launch release deadline expired")
            # Actual on_start registration happens only after __init__ returns.
        def suite(which, on_start=None):
            self.threads.append(self.threading.current_thread())
            if which == 0:
                if not ready_event.wait(15):
                    raise AssertionError("late Popen was not ready")
                raise sentinel
            def started(process):
                if on_start is not None:
                    on_start(process)
                registered.set()
                # Hold before communicate so the fixture's normal timeout
                # cannot clean the old runner's leak and manufacture GREEN.
                if not collect.wait(45):
                    failures.append("late-collection release deadline expired")
            try:
                return run_suites.run_process(argv, cwd=self.root, timeout_seconds=12, on_start=started)
            finally:
                worker_done.set()
        with mock.patch.object(self.real_popen, "__init__", new=initialize), \
                mock.patch.object(run_suites, "_run_suite", side_effect=suite):
            result, done = self._controller([0, 1])
            try:
                self.assertTrue(ready_event.wait(15), "actual late Popen did not start")
                self.assertEqual(len(captured), 2, "late constructor hook must capture suite and ready child")
                self.assertTrue(ready.exists())
                self.assertTrue(all(record[0] > 0 for record in captured))
                # Old dispatcher returns with an empty snapshot. A dispatcher that
                # joins workers is released after one bounded watchdog interval.
                done.wait(1)
                release.set()
                self.assertTrue(registered.wait(15), "late Popen did not finish actual registration")
                self.assertTrue(self._until(lambda: not any(self._alive(r) for r in captured), 10),
                                "late group survived cancellation before collection/timeout/fallback")
                collect.set()
                self.assertTrue(done.wait(15), "dispatcher did not finish cancellation")
                self.assertEqual(len(result), 1)
                self.assertIs(result[0], sentinel)
                self.assertTrue(worker_done.wait(15), "late-registered suite worker survived cancellation")
                self.assertFalse(any(self._alive(r) for r in captured), "late group survived before fallback")
                self.assertEqual(failures, [])
                self.assertTrue(self._alive(decoy))
            finally:
                release.set()
                collect.set()
                # Join before restoring mocks; fallback kills only captured identities.
                for record in captured:
                    if self._alive(record):
                        try:
                            os.kill(record[0], signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                # Join every real thread before either patch is restored, even
                # when an event assertion would fail. Events alone are not joins.
                for thread in self.threads:
                    thread.join(15)
                self.assertFalse(any(thread.is_alive() for thread in self.threads),
                                 "late worker/controller outlived patched scope")
                self.assertTrue(worker_done.is_set(), "late worker did not finish bounded fallback")
                self.assertTrue(done.is_set(), "dispatcher did not finish bounded fallback")

    def test_dispatcher_never_signals_reaped_leader_with_unfinished_future(self):
        reaped, release, worker_done = (self.threading.Event() for _ in range(3))
        self.releases.append(release)
        sentinel = RuntimeError("cancel while completed worker returns")
        processes, unsafe, barriers, failures = [], [], [], []
        marker = self.root.name + "-reaped"
        gate = self.root / "reaped.go"
        script = "import sys,time; sys.dont_write_bytecode=True; from pathlib import Path; "
        script += "gate=Path(sys.argv[1]); deadline=time.monotonic()+45\n"
        script += "while not gate.exists() and time.monotonic()<deadline: time.sleep(.01)\n"
        script += "assert gate.exists(), 'reaped launch gate expired'\nprint('reaped-control')"
        argv = (sys.executable, "-B", "-c", script, str(gate), marker)
        def initialize(process, *args, **kwargs):
            self.real_popen_init(process, *args, **kwargs)
            actual_argv = args[0] if args else kwargs.get("args")
            if actual_argv is not None and tuple(actual_argv) == argv:
                self.assertIsInstance(process, self.real_popen)
                self.assertGreater(process.pid, 0)
                self.processes.append(process)
                self._remember(process.pid, marker, process.pid)
                processes.append(process)
                gate.touch()
        real_killpg = os.killpg
        def observe(group, sig):
            # Suppress the unsafe call: even a mocked recycled identity must
            # never send a real signal. The record is the assertion evidence.
            matches = [p for p in processes if p.pid == group]
            if sig and (not matches or any(p.returncode is not None for p in matches)):
                unsafe.append((group, int(sig)))
                return
            return real_killpg(group, sig)
        def suite(which, on_start=None):
            self.threads.append(self.threading.current_thread())
            if which == 0:
                if not reaped.wait(15):
                    raise AssertionError("completed worker never reached reap barrier")
                raise sentinel
            def started(process):
                self.assertEqual(processes, [process], "constructor must capture actual process before on_start")
                if on_start is not None:
                    on_start(process)
            outcome = run_suites.run_process(argv, cwd=self.root, timeout_seconds=10, on_start=started)
            barriers.append((outcome.status, outcome.returncode, outcome.stdout, processes[-1].returncode))
            reaped.set()
            try:
                if not release.wait(45):
                    failures.append("reaped-future release deadline expired")
                return outcome
            finally:
                worker_done.set()
        with mock.patch.object(self.real_popen, "__init__", new=initialize), \
                mock.patch.object(run_suites, "_run_suite", side_effect=suite), \
                mock.patch.object(os, "killpg", side_effect=observe):
            result, done = self._controller([0, 1])
            try:
                self.assertTrue(reaped.wait(15), "actual Popen never completed")
                self.assertEqual(len(processes), 1, "actual reaped Popen must be observed")
                self.assertGreater(processes[0].pid, 0)
                self.assertTrue(gate.exists())
                self.assertEqual(barriers, [("passed", 0, "reaped-control\n", 0)])
                # Keep the future unfinished until the dispatcher finishes, with
                # bounded release for implementations that join on cancellation.
                done.wait(3)
                release.set()
                self.assertTrue(done.wait(15), "dispatcher cancellation did not finish")
                self.assertEqual(len(result), 1)
                self.assertIs(result[0], sentinel)
                self.assertTrue(worker_done.wait(15), "completed worker did not return")
                self.assertEqual(unsafe, [], "dispatcher signalled after actual leader reap")
                self.assertEqual(failures, [])
            finally:
                release.set()
                for thread in self.threads:
                    thread.join(15)
                self.assertFalse(any(thread.is_alive() for thread in self.threads),
                                 "reaped worker/controller outlived patched scope")
                self.assertTrue(worker_done.is_set())
                self.assertTrue(done.is_set())


    def test_timeout_grace_interrupt_finishes_owned_group_before_escape(self):
        argv, ready, gate, marker = self._command("grace-interrupt", "sleep")
        # Install TERM ignoring before spawning the existing ready child.
        script = self.leader.read_text(encoding="utf-8").replace(
            "import os, subprocess, sys, time",
            "import os, subprocess, sys, time, signal\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)")
        argv = (sys.executable, "-B", "-c", script, *argv[3:])
        sentinel = KeyboardInterrupt("interrupt actual TERM grace once")
        captured, owners, terms, injections = [], [], [], []
        decoy = self._decoy()
        real_wait, real_killpg = run_suites._SuiteProcess.wait, os.killpg
        def started(process):
            owners.append(process)
            captured.extend(self._capture(process, ready, marker))
            gate.touch()
        def signal_group(group, sig):
            result = real_killpg(group, sig)
            if owners and group == owners[0].pid and sig == signal.SIGTERM:
                terms.append(group)
            return result
        def wait(process, timeout=None):
            if owners and process is owners[0] and timeout == 1 and terms and not injections:
                injections.append(process.pid)
                raise sentinel
            return real_wait(process, timeout=timeout)
        def suite(*args, **kwargs):
            return run_suites.run_process(argv, cwd=self.root, timeout_seconds=.1, on_start=started)
        with mock.patch.object(os, "killpg", new=signal_group), \
                mock.patch.object(run_suites._SuiteProcess, "wait", new=wait), \
                mock.patch.object(run_suites, "_run_suite", side_effect=suite):
            try:
                try:
                    list(run_suites._outcomes([object()], jobs=1))
                except BaseException as caught:
                    self.assertIs(caught, sentinel)
                else:
                    self.fail("timeout-grace interrupt was swallowed")
                self.assertEqual(len(captured), 2)
                self.assertTrue(ready.exists())
                self.assertTrue(all(record[0] > 0 for record in captured))
                self.assertEqual(injections, [owners[0].pid])
                self.assertTrue(terms, "injection must follow actual TERM delivery")
                stopped = self._until(lambda: not any(self._alive(r) for r in captured), 10)
                closed = all(s is not None and s.closed for s in (owners[0].stdout, owners[0].stderr))
                self.assertEqual((stopped, closed), (True, True),
                                 "owned group leak or open streams before fixture fallback")
                self.assertTrue(self._alive(decoy))
            finally:
                primary = sys.exc_info()[0] is not None
                errors = []
                for record in reversed(self.owned):
                    try:
                        if self._alive(record):
                            os.kill(record[0], signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    except BaseException as error:
                        errors.append(error)
                for process in self.processes:
                    try:
                        process.wait(timeout=15)
                    except BaseException as error:
                        errors.append(error)
                    finally:
                        for stream in (process.stdout, process.stderr):
                            if stream is not None:
                                try:
                                    stream.close()
                                except BaseException as error:
                                    errors.append(error)
                if errors and not primary:
                    raise errors[0]


    def test_interrupted_real_constructor_cleans_before_registration_serial_and_parallel(self):
        decoy = self._decoy()
        for jobs in (1, 2):
            with self.subTest(jobs=jobs):
                argv, ready, gate, marker = self._command("constructor-%s" % jobs, "sleep")
                sentinel = KeyboardInterrupt("actual constructor interrupt %s" % jobs)
                captured, owners, injections, callbacks, workers = [], [], [], [], []
                def initialize(process, *args, **kwargs):
                    self.real_popen_init(process, *args, **kwargs)
                    actual = args[0] if args else kwargs.get("args")
                    if actual is not None and tuple(actual) == argv and not injections:
                        owners.append(process)
                        captured.extend(self._capture(process, ready, marker))
                        injections.append(process.pid)
                        raise sentinel
                def started(process, on_start):
                    callbacks.append(process.pid)
                    if on_start is not None:
                        on_start(process)
                def suite(which, on_start=None):
                    if jobs == 2:
                        worker = self.threading.current_thread()
                        workers.append(worker)
                        self.threads.append(worker)
                    return run_suites.run_process(
                        argv, cwd=self.root, timeout_seconds=10,
                        on_start=lambda p: started(p, on_start))
                # Patch the original class, never replace it with a factory.
                with mock.patch.object(self.real_popen, "__init__", new=initialize), \
                        mock.patch.object(run_suites, "_run_suite", side_effect=suite):
                    try:
                        try:
                            list(run_suites._outcomes([object()], jobs=jobs))
                        except BaseException as caught:
                            self.assertIs(caught, sentinel)
                        else:
                            self.fail("constructor interrupt was swallowed")
                        self.assertEqual(len(owners), 1)
                        self.assertEqual(len(captured), 2)
                        self.assertTrue(ready.exists())
                        self.assertTrue(all(record[0] > 0 for record in captured))
                        self.assertEqual(injections, [owners[0].pid])
                        self.assertEqual(callbacks, [], "on_start ran after interrupted construction")
                        stopped = self._until(lambda: not any(self._alive(r) for r in captured), 10)
                        closed = all(s is not None and s.closed for s in (owners[0].stdout, owners[0].stderr))
                        self.assertEqual((stopped, closed), (True, True),
                                         "constructor leaked group or streams before fixture fallback")
                        self.assertTrue(self._alive(decoy))
                    finally:
                        primary = sys.exc_info()[0] is not None
                        errors = []
                        # _capture may register identities then raise before
                        # captured.extend receives its return value. Restrict
                        # fallback to this subcase's actual owner groups.
                        owner_groups = {process.pid for process in owners}
                        for record in self.owned:
                            if record[3] not in owner_groups:
                                continue
                            try:
                                if self._alive(record):
                                    os.kill(record[0], signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                            except BaseException as error:
                                errors.append(error)
                        # Even the old dispatcher shuts down without joining;
                        # join the actual pool thread before restoring either patch.
                        for worker in workers:
                            try:
                                worker.join(15)
                                if worker.is_alive():
                                    errors.append(AssertionError("constructor worker outlived patched scope"))
                            except BaseException as error:
                                errors.append(error)
                        for process in owners:
                            try:
                                process.wait(timeout=15)
                            except BaseException as error:
                                errors.append(error)
                            finally:
                                for stream in (process.stdout, process.stderr):
                                    if stream is not None:
                                        try:
                                            stream.close()
                                        except BaseException as error:
                                            errors.append(error)
                        if errors and not primary:
                            raise errors[0]


    @unittest.skipUnless(sys.platform == "darwin", "actual Darwin observer and waitid ABI required")
    def test_darwin_active_owner_cleanup_does_not_reenter_numeric_observer(self):
        import errno
        import warnings
        marker = self.root.name + "-active-owner"
        gate = self.root / "active-owner.go"
        script = "import os,sys,time; from pathlib import Path; gate=Path(sys.argv[1]); deadline=time.monotonic()+45\n"
        script += "while not gate.exists() and time.monotonic()<deadline: time.sleep(.01)\n"
        script += "assert gate.exists(), 'active-owner gate expired'\nos.write(1,b'active-out\\n'); os.write(2,b'active-err\\n')\n"
        owner = run_suites._SuiteProcess(
            [sys.executable, "-B", "-c", script, str(gate), marker],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            start_new_session=True)
        self.processes.append(owner)
        observers, triggers, depths, signals, after_reap = [], [], [], [], []
        depth, enabled = 0, True
        bounded = RuntimeError("bounded second nested numeric observer")
        nested = []
        real_killpg = os.killpg
        numeric = ['/bin/ps', '-A', '-o', 'pid=,pgid=,stat=']
        def signal_group(group, sig):
            if group == owner.pid:
                if owner.returncode is not None:
                    after_reap.append((group, int(sig)))
                    return
                signals.append((group, int(sig)))
                if enabled:
                    raise PermissionError(errno.EPERM, "intentional owner-only EPERM")
            return real_killpg(group, sig)
        def initialize(process, *args, **kwargs):
            nonlocal depth
            actual = args[0] if args else kwargs.get("args")
            if actual is None or list(actual) != numeric:
                return self.real_popen_init(process, *args, **kwargs)
            depth += 1
            depths.append(depth)
            try:
                if depth > 1:
                    nested.append(bounded)
                    raise bounded  # Before real initialization: no second observer fork.
                self.real_popen_init(process, *args, **kwargs)
                observers.append(process)
                self.processes.append(process)
            finally:
                depth -= 1
        with mock.patch.object(self.real_popen, "__init__", new=initialize), \
                mock.patch.object(os, "killpg", new=signal_group):
            try:
                record = self._remember(owner.pid, marker, owner.pid)
                self.assertTrue(self._alive(record))
                self.assertIsNone(owner.returncode)
                with warnings.catch_warnings(record=True) as intentional:
                    warnings.simplefilter("always", ResourceWarning)
                    owner.__del__()  # Strong reference retained; real CPython registration.
                resources = [w for w in intentional if issubclass(w.category, ResourceWarning)]
                self.assertEqual(len(resources), 1)
                self.assertIn(str(owner.pid), str(resources[0].message))
                self.assertTrue(any(p is owner for p in subprocess._active),
                                "real destructor did not register live owner")
                gate.touch()
                readonly_exit_probe = run_suites._exit_probe()
                self.assertTrue(self._until(lambda: readonly_exit_probe(owner.pid), 10),
                                "leader did not exit unreaped before cleanup trigger")
                self.assertIsNone(owner.returncode)
                # Plain base construction invokes real global subprocess._cleanup.
                trigger = self.real_popen([sys.executable, "-B", "-c", "pass"],
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                triggers.append(trigger)
                self.processes.append(trigger)
                trigger.communicate(timeout=10)
                self.assertTrue(depths, "numeric observer branch was not exercised")
                self.assertLessEqual(max(depths), 1, "recursive observer construction before fallback")
                self.assertEqual(nested, [])
                self.assertTrue(signals, "owner-only EPERM injection was not exercised")
                self.assertEqual(owner.cleanup_warnings, [])
                self.assertEqual(owner.returncode, 0, "normal global cleanup did not reap owner")
                self.assertFalse(any(p is owner for p in subprocess._active))
                out, err = owner.communicate(timeout=10)
                self.assertEqual((out, err), ("active-out\n", "active-err\n"))
                with self.assertRaises(ChildProcessError):
                    readonly_exit_probe(owner.pid)
                owner.poll()
                owner.wait(timeout=1)
                self.assertEqual(after_reap, [], "signal attempted after actual reap")
                self.assertTrue(observers)
                self.assertTrue(all(p.returncode is not None for p in observers))
                self.assertTrue(all(s.closed for p in observers for s in (p.stdout, p.stderr) if s is not None))
            finally:
                primary = sys.exc_info()[0] is not None
                enabled = False
                errors = []
                # Even failed identity capture leaves a strong owner reference;
                # release its gate and reap it without an unvalidated PID kill.
                try:
                    gate.touch()
                except BaseException as error:
                    errors.append(error)
                # Disable only this fixture's EPERM injection for fallback;
                # normal owner hooks and global cleanup remain in operation.
                for record in self.owned:
                    try:
                        if self._alive(record):
                            os.kill(record[0], signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    except BaseException as error:
                        errors.append(error)
                for process in [owner, *observers, *triggers]:
                    try:
                        if process is not owner and process.returncode is None:
                            process.kill()
                        process.wait(timeout=15)
                    except BaseException as error:
                        errors.append(error)
                    finally:
                        for stream in (process.stdout, process.stderr):
                            if stream is not None:
                                try:
                                    stream.close()
                                except BaseException as error:
                                    errors.append(error)
                # A normal constructor removes any now-reaped active entry.
                try:
                    final = self.real_popen([sys.executable, "-B", "-c", "pass"],
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    self.processes.append(final)
                    try:
                        final.communicate(timeout=10)
                    finally:
                        if final.returncode is None:
                            final.kill()
                        final.wait(timeout=15)
                        final.stdout.close()
                        final.stderr.close()
                except BaseException as error:
                    errors.append(error)
                if errors and not primary:
                    raise errors[0]



    def test_constructor_interrupt_after_actual_pid_before_child_created_reaps_and_closes(self):
        import inspect
        self.assertEqual(os.name, "posix")
        self.assertGreaterEqual(sys.version_info[:2], (3, 15))
        self.assertTrue(callable(os.waitpid), "native positive-PID teardown requires waitpid")
        self.assertTrue(callable(os.waitstatus_to_exitcode), "supported Python supplies native status conversion")
        execute = self.real_popen._execute_child
        source, first = inspect.getsourcelines(execute)
        assignments = [first + offset for offset, line in enumerate(source)
                       if re.fullmatch(r"\s*self\._child_created\s*=\s*True\s*(?:#.*)?", line.rstrip())]
        self.assertEqual(len(assignments), 1, "resolve exactly one native creation-flag assignment")
        fault_line = assignments[0]
        self.assertIn("self.pid", "".join(source[:fault_line - first]),
                      "installed stdlib must assign the real PID before the fault line")
        decoy = self._decoy()
        marker = self.root.name + "-partial-constructor"
        ready = self.root / "partial-constructor.json"
        # This real child closes its captured descriptors, publishes its actual
        # PID/PGID/marker atomically, ignores TERM, then sleeps for 120 seconds.
        # Pipe closure and normal completion cannot make this regression pass.
        argv = (sys.executable, "-B", str(self.child), str(ready), marker)
        sentinel = KeyboardInterrupt("actual PID assigned before child-created flag")
        owners, records, streams, flags, starts, escaped = [], [], [], [], [], []
        fired = []
        calling_thread = self.threading.get_ident()
        prior_trace = sys.gettrace()

        def trace(frame, event, arg):
            if (not fired and event == "line" and frame.f_code is execute.__code__
                    and frame.f_lineno == fault_line):
                owner = frame.f_locals.get("self")
                if tuple(getattr(owner, "args", ())) == argv:
                    fired.append(self.threading.get_ident())
                    # Hold strong references even if any readiness assertion fails.
                    owners.append(owner)
                    self.processes.append(owner)
                    streams.extend((owner.stdout, owner.stderr))
                    flags.append(owner._child_created)
                    self.assertIsInstance(owner, run_suites._SuiteProcess)
                    self.assertGreater(owner.pid, 0, "fault must follow actual fork PID assignment")
                    self.assertFalse(owner._child_created)
                    records.append(self._remember(owner.pid, marker, owner.pid))
                    self.assertTrue(self._until(ready.exists, 10), "real child readiness deadline expired")
                    self.assertEqual(json.loads(ready.read_text(encoding="utf-8")),
                                     {"pid": owner.pid, "pgid": owner.pid, "marker": marker})
                    self.assertTrue(self._alive(records[0]))
                    self.assertTrue(all(stream is not None and not stream.closed for stream in streams))
                    raise sentinel
            return trace

        def suite(which, on_start=None):
            # Install in the actual caller; this remains correct if later run in
            # a worker. No process-global threading trace hook is installed.
            self.assertEqual(self.threading.get_ident(), calling_thread)
            sys.settrace(trace)
            try:
                return run_suites.run_process(argv, cwd=self.root, timeout_seconds=10,
                                              on_start=lambda process: starts.append(process))
            finally:
                sys.settrace(prior_trace)

        try:
            began = time.monotonic()
            with mock.patch.object(run_suites, "_run_suite", side_effect=suite):
                try:
                    list(run_suites._outcomes([object()], jobs=1))
                except BaseException as error:
                    escaped.append(error)
                    # Snapshot before any test fallback, poll, wait or raw reap.
                    if owners:
                        owner = owners[0]
                        at_escape = (owner.returncode, self._identity(owner.pid),
                                     tuple(stream is not None and stream.closed for stream in streams))
            elapsed = time.monotonic() - began
            self.assertIs(sys.gettrace(), prior_trace)
            self.assertEqual(fired, [calling_thread], "one exact native frame must reach the fault")
            self.assertEqual(len(owners), 1)
            self.assertEqual(len(records), 1, "actual birth/PGID/argv identity must be captured")
            self.assertGreater(records[0][0], 0)
            self.assertEqual(flags, [False], "the real constructor flag must still be false at injection")
            self.assertEqual(len(escaped), 1)
            self.assertIs(escaped[0], sentinel, "constructor must preserve exact KeyboardInterrupt")
            self.assertEqual(starts, [], "on_start cannot run for a partially constructed owner")
            self.assertLess(elapsed, 30, "normal 120-second child exit cannot satisfy cleanup")
            # v3/v4 are expected to remain alive for this entire bounded window.
            # Collect that observation before any assertion can enter fallback.
            ended = self._until(lambda: not self._alive(records[0]), 10)
            decoy_survived = self._alive(decoy)
            self.assertTrue(decoy_survived, "unrelated private group must survive")
            self.assertTrue(ended, "actual partial-constructor child survived 10s before fallback")
            self.assertIsNotNone(at_escape[0], "actual owner must already have its reaped returncode")
            self.assertIsNone(at_escape[1], "child must be absent, not a live process or unreaped zombie, at escape")
            self.assertEqual(at_escape[2], (True, True), "both captured streams must close before escape")
        finally:
            sys.settrace(prior_trace)
            # Test-only fallback AFTER the assertion observations. An unrepaired
            # false-flag Popen cannot safely use its normal wait loop here.
            for owner in owners:
                try:
                    pid = getattr(owner, "pid", None)
                    self.assertIsInstance(pid, int)
                    self.assertGreater(pid, 0)
                    record = records[0] if records else self._remember(pid, marker, pid)
                    if self._alive(record):
                        try:
                            os.kill(pid, signal.SIGKILL)  # exactly the validated owned PID
                        except ProcessLookupError:
                            pass
                    # No waitpid(-1), guessed group, synthetic PID or production
                    # returncode mutation: only actual child status in fallback.
                    deadline = time.monotonic() + 10
                    while True:
                        try:
                            waited, status = os.waitpid(pid, os.WNOHANG)
                        except ChildProcessError:
                            break  # production already reaped this actual child
                        if waited == pid:
                            owner.returncode = os.waitstatus_to_exitcode(status)
                            break
                        if time.monotonic() >= deadline:
                            self.fail("identity-checked partial-owner fallback did not reap actual child")
                        time.sleep(.01)
                finally:
                    for stream in (getattr(owner, "stdout", None), getattr(owner, "stderr", None)):
                        if stream is not None:
                            stream.close()



if __name__ == "__main__":
    unittest.main()
