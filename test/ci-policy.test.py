#!/usr/bin/env python3
"""Exercise real Git routing and qualification guards, not a second policy copy."""
import contextlib
import io
import itertools
import json
import os
import re
from pathlib import Path
import subprocess
import tempfile
import unittest

import ci_policy as policy

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ("delayed-setup", "setup-save-boundary", "turn-and-action-correlation", "app-owned-controls")


class CIPolicyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="skill-craft-ci-policy-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        self.write("README.md", "initial\n")
        self.write("code.py", "initial\n")
        self.write(".gitignore", "__pycache__/\nignored/\n")
        self.base = self.commit()

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, stderr=subprocess.PIPE).decode().strip()

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        return self.git("rev-parse", "HEAD")

    def event(self, base=None, head=None):
        return {"pull_request": {"base": {"sha": base or self.base}, "head": {"sha": head or self.git("rev-parse", "HEAD")}}}

    def test_manual_dispatch_requires_quick_or_full(self):
        for tier in ("quick", "full"):
            self.assertEqual(policy.select(self.root, "workflow_dispatch", {}, tier)[0], "full")
        for tier in ("", "smoke"):
            with self.assertRaises(ValueError):
                policy.select(self.root, "workflow_dispatch", {}, tier)

    def test_a_scheduled_run_is_the_full_tier(self):
        tier, reason, base = policy.select(self.root, "schedule", {}, "")
        self.assertEqual((tier, base), ("full", ""))
        self.assertIn("scheduled", reason)

    def test_only_a_release_commit_push_runs_full(self):
        self.write("code.py", "changed\n")
        change = self.commit()
        self.assertEqual(policy.select(self.root, "push", {"before": self.base}, ""),
                         ("quick", "pushed changes", self.base))
        self.write("CHANGELOG.md", "release\n")
        self.git("add", ".")
        self.git("commit", "-qm", "release: demo 1.0.0\n\nSkill-Craft-Release: demo@1.0.0")
        self.assertEqual(policy.select(self.root, "push", {"before": change}, "")[0], "full")
        self.assertTrue(policy.is_release(self.root))
        self.assertFalse(policy.is_release(self.root, change))
        # A release pushed under a later ordinary commit still runs full.
        self.write("code.py", "after the release\n")
        after = self.commit()
        self.assertEqual(policy.select(self.root, "push", {"before": change}, "")[0], "full")
        self.assertEqual(policy.select(self.root, "push", {}, "")[0], "full")
        self.write("code.py", "later again\n")
        self.commit()
        self.assertEqual(policy.select(self.root, "push", {"before": after}, "")[0], "quick")

    def test_push_without_a_known_previous_commit_runs_full(self):
        self.write("code.py", "changed\n")
        self.commit()
        for event in ({}, {"before": "0" * 40}, {"before": "f" * 40}, {"before": "HEAD"}, {"before": 123}):
            self.assertEqual(policy.select(self.root, "push", event, "")[::2], ("full", ""))
        self.assertEqual(policy.select(self.root, "unknown", {}, "")[:1], ("full",))

    def test_pr_diffs_from_the_merge_base_not_unrelated_main_changes(self):
        self.write("code.py", "main moved\n")
        main = self.commit()
        self.git("checkout", "-q", "--detach", self.base)
        self.write("docs/report.md", "explanation\n")
        head = self.commit()
        self.assertEqual(policy.select(self.root, "pull_request", self.event(main, head), ""),
                         ("quick", "pull request changes", self.base))
        self.assertEqual(policy.select(self.root, "pull_request", {}, "")[::2], ("full", ""))
        self.assertEqual(policy.select(self.root, "pull_request", self.event("HEAD", head), "")[0], "full")

    def test_known_ranges_and_exact_infrastructure_policy(self):
        for path in sorted(policy.INFRASTRUCTURE_PATHS):
            with self.subTest(path=path):
                self.git("reset", "--hard", self.base)
                self.write(path, "infrastructure change")
                self.commit()
                self.assertEqual(policy.select(self.root, "push", {"before": self.base}, "")[0], "full")
                self.assertEqual(policy.select(self.root, "pull_request", self.event(), "")[0], "full")
        for path in ("skills/shiploop/scripts/shiploop_protocol.py", "test/shiploop_e2e/state.py"):
            self.git("reset", "--hard", self.base)
            self.write(path, "ordinary runtime change")
            self.commit()
            self.assertEqual(policy.select(self.root, "push", {"before": self.base}, "")[0], "quick")
            self.assertEqual(policy.select(self.root, "workflow_dispatch", {}, "quick")[0], "quick")

    def test_unrelated_history_never_claims_a_narrow_range(self):
        self.git("checkout", "--orphan", "unrelated")
        self.write("other", "unrelated")
        unrelated = self.commit()
        self.git("checkout", "--detach", self.base)
        self.assertEqual(policy.select(self.root, "push", {"before": unrelated}, "")[0], "full")
        self.assertEqual(policy.select(self.root, "pull_request", self.event(unrelated), "")[0], "full")
        for base in (None, "", "0" * 40, "f" * 40, "invalid", unrelated):
            with self.subTest(base=base), self.assertRaisesRegex(ValueError, "push base"):
                policy.boundary_base(self.root, "push", {"before": base}, self.base)

    def test_boundary_validates_merge_candidate_and_exact_push_range(self):
        self.write("code.py", "main")
        main = self.commit()
        self.git("checkout", "--detach", self.base)
        self.write("feature", "feature")
        head = self.commit()
        self.git("checkout", "--detach", main)
        self.git("merge", "--no-ff", "-m", "merge candidate", head)
        candidate = self.git("rev-parse", "HEAD")
        self.assertEqual(policy.boundary_base(self.root, "pull_request", self.event(main, head), candidate), main)
        self.assertEqual(policy.boundary_base(self.root, "push", {"before": self.base}, candidate), self.base)
        for event, expected in ((self.event(head, main), candidate), (self.event(main, head), head)):
            with self.assertRaises(ValueError):
                policy.boundary_base(self.root, "pull_request", event, expected)
        for name in ("schedule", "workflow_dispatch"):
            self.assertIsNone(policy.boundary_base(self.root, name, {}, candidate))
        # Execute the actual workflow command, with the checker replaced by a recording fixture.
        self.write("scripts/check-release-boundary.py", "import sys; print('CHECKED', sys.argv[1:])")
        event_path = self.root / "event.json"
        event_path.write_text(json.dumps({"before": self.base}))
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        job = workflow.split("\n  release-boundary:\n", 1)[1].split("\n  hermetic:\n", 1)[0]
        command = job.split('        run: python3 -B test/ci_policy.py boundary', 1)[1].splitlines()[0]
        shell = 'python3 -B ' + str(ROOT / 'test/ci_policy.py') + ' boundary' + command
        env = dict(os.environ, EXPECTED_SHA=candidate, GITHUB_EVENT_NAME="push", GITHUB_EVENT_PATH=str(event_path))
        result = subprocess.run(["bash", "-e", "-c", shell], cwd=self.root, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(self.base, result.stdout)
        event_path.write_text('{}')
        result = subprocess.run(["bash", "-e", "-c", shell], cwd=self.root, env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('CHECKED', result.stdout)

    def test_stable_node_guard_and_each_setup_step(self):
        guard = ROOT / "test/ci_node_stable.cjs"
        for version in ("v24.1.0", "26.0.0", "v27.0.0-alpha.1", "v27.0.0-beta.2", "v27.0.0-rc.1", "latest", "v01.2.3"):
            result = subprocess.run(["node", "-e", "require(process.argv[1])(process.argv[2])", str(guard), version],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode == 0, version in {"v24.1.0", "26.0.0"})
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        setups = workflow.split('      - uses: actions/setup-node@v7\n')[1:]
        self.assertEqual(len(setups), 3)
        for setup in setups:
            settings, next_step = setup.split('      - name:', 1)
            self.assertIn("node-version: '*'", settings)
            self.assertIn('check-latest: true', settings)
            self.assertIn('run: node test/ci_node_stable.cjs', next_step.split('      - name:', 1)[0])
        self.assertIn("requireStable(process.version)", guard.read_text())

    def test_guard_accepts_only_clean_source_and_declared_bytecode(self):
        self.write("__pycache__/module.pyc", "bytecode")
        with contextlib.redirect_stdout(io.StringIO()):
            policy.guard(self.root, self.base)
        self.write("ignored/result.json", "{}")
        with self.assertRaises(ValueError):
            policy.guard(self.root, self.base)

    def test_guard_rejects_head_tracked_staged_untracked_and_symlink_drift(self):
        for mode in ("head", "tracked", "staged", "untracked", "symlink"):
            with self.subTest(mode=mode):
                self.git("reset", "--hard", self.base)
                self.git("clean", "-fdx")
                if mode == "head":
                    self.write("code.py", "moved")
                    self.commit()
                elif mode in {"tracked", "staged"}:
                    self.write("code.py", "changed")
                    if mode == "staged":
                        self.git("add", "code.py")
                        self.git("restore", "--source=HEAD", "--worktree", "code.py")
                elif mode == "untracked":
                    self.write("new.txt", "output")
                else:
                    (self.root / "__pycache__").mkdir()
                    (self.root / "__pycache__/link.pyc").symlink_to(self.root / "code.py")
                with self.assertRaises((ValueError, subprocess.CalledProcessError)):
                    with contextlib.redirect_stdout(io.StringIO()):
                        policy.guard(self.root, self.base)

    def test_workflow_uses_recorded_merge_candidate_latest_runtimes_and_evidence(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertIn("fetch-depth: 0", workflow)
        self.assertIn("EXPECTED_SHA: ${{ github.sha }}", workflow)
        self.assertIn("ref: ${{ needs.plan.outputs.source_sha }}", workflow)
        self.assertIn("fromJSON(needs.plan.outputs.groups)", workflow)
        # Check every Python setup, rather than accepting one floating block while another stays pinned.
        setups = workflow.split("      - uses: actions/setup-python@v7\n")[1:]
        self.assertEqual(len(setups), 4)
        for setup in setups:
            settings = setup.split("      - ", 1)[0]
            self.assertEqual(re.findall(r"(?m)^          python-version: (.+)$", settings), ["'3.x'"])
            self.assertEqual(re.findall(r"(?m)^          check-latest: (.+)$", settings), ["true"])
        self.assertIn("node-version: '*'", workflow)
        self.assertEqual(workflow.count("check-latest: true"), 7)
        runners = re.findall(r"(?m)^    runs-on: (.+)$", workflow)
        self.assertEqual(len(runners), 5)
        self.assertEqual(set(runners), {"ubuntu-latest"})
        self.assertIn("fail-fast: false", workflow)
        self.assertIn('--output "$RUNNER_TEMP/hermetic-$TEST_GROUP"', workflow)
        # Stand-in host markers, so the state-home guard sees keepalive and Until Loop leaks on CI too.
        self.assertIn("CLAUDECODE: '1'", workflow)
        self.assertIn("CLAUDE_CODE_SESSION_ID: ci-stand-in", workflow)
        self.assertIn("if-no-files-found: error", workflow)
        self.assertIn("uses: actions/upload-artifact@v7", workflow)
        self.assertIn("cancel-in-progress: ${{ github.event_name == 'pull_request' }}", workflow)
        # One weekly drift canary: a floating runtime or runner image (python 3.x, node latest, ubuntu-latest) can break
        # CI with no commit, and a push is otherwise the only thing that finds out. Off the hour, on one weekday.
        self.assertEqual(workflow.count("cron:"), 1)
        self.assertRegex(workflow, r"(?m)^  schedule:\n    - cron: '([1-9]|[1-5][0-9]) \d{1,2} \* \* [0-6]'$")
        self.assertNotIn("secrets.", workflow)
        self.assertNotIn("run-integration", workflow)
        self.assertNotIn("--release-sync", workflow)

    def test_selected_quick_shards_receive_the_planned_range_and_cannot_be_suppressed(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        checks = workflow.split("\n  checks:\n", 1)[1].split("\n  browser-fixtures:\n", 1)[0]
        self.assertIn("needs: plan", checks)
        self.assertIn("needs.plan.outputs.tier == 'quick' && '0' || '1'", checks)
        self.assertIn("name: ${{ needs.plan.outputs.tier }} / ${{ matrix.group }}", checks)
        self.assertIn("fail-fast: false", checks)
        self.assertNotIn("max-parallel", checks)
        self.assertNotIn("continue-on-error", checks)
        self.assertNotIn("\n    if:", checks)
        browser = workflow.split("\n  browser-fixtures:\n", 1)[1].split("\n  release-boundary:\n", 1)[0]
        self.assertIn("needs: plan", browser)
        self.assertNotIn("\n    if:", browser)
        step = checks.split("      - name: Hermetic group\n", 1)[1].split("      - name:", 1)[0]
        commands = "\n".join(line[10:] for line in step.split("        run: |\n", 1)[1].splitlines())
        self.write("test/run-all.sh", 'printf "%s\\n" "$@" > "$RUNNER_TEMP/args"\n')
        for group in ("quick", "quick-1", "quick-2", "core"):
            for base in (self.base, ""):
                result = subprocess.run(["bash", "-eo", "pipefail", "-c", commands], cwd=self.root,
                                        env=dict(os.environ, TEST_GROUP=group, BASE=base, RUNNER_TEMP=str(self.root)),
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, bool(base) or group == "core")
                if result.returncode == 0:
                    args = (self.root / "args").read_text().splitlines()
                    expected = ["--group", group, "--output", str(self.root / ("hermetic-" + group))]
                    if group.startswith("quick"):
                        expected += ["--jobs", "4", "--changed-from", base]
                    self.assertEqual(args, expected)

    def test_planner_cli_schedules_broad_quick_and_keeps_original_full_groups(self):
        event, output = self.root / "event.json", self.root / "output"
        summary = self.root / "summary"
        event.write_text(json.dumps({"before": self.base}))
        self.write("test/shiploop_e2e/run.py", "ordinary harness change")
        head = self.commit()
        env = dict(os.environ, GITHUB_EVENT_PATH=str(event), GITHUB_EVENT_NAME="push",
                   GITHUB_OUTPUT=str(output), GITHUB_STEP_SUMMARY=str(summary))
        result = subprocess.run(["python3", "-B", str(ROOT / "test/ci_policy.py"), "plan",
                                 "--expected-sha", head], cwd=self.root, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        planned = json.loads(result.stdout)
        self.assertEqual(planned["groups"], ["quick-1", "quick-2"])
        self.assertEqual(planned["base"], self.base)
        self.assertEqual(policy.FULL_GROUPS,
                         ["core", "shiploop-1", "shiploop-2", "shiploop-3", "e2e-apparatus"])

    def test_checks_job_turns_git_background_maintenance_off_before_it_runs_the_suites(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        job = workflow.split("\n  checks:\n", 1)[1].split("\n  browser-fixtures:\n", 1)[0]
        setting = "git config --global maintenance.auto false"
        # A commit makes git start a detached `git maintenance run --auto`, which holds objects/maintenance.lock for a
        # moment; fixtures that inventory or copy a tree right after a commit lost the lock to it on CI four times.
        self.assertEqual(job.count(setting), 1)
        self.assertLess(job.index(setting), job.index("bash test/run-all.sh"))
        # Never as GIT_CONFIG_* variables: run-all.sh strips them from every suite and the workspace guards refuse them.
        code = "\n".join(line for line in workflow.splitlines() if not line.lstrip().startswith("#"))
        self.assertNotIn("GIT_CONFIG", code)

    def test_release_boundary_job_sees_full_history_and_the_pr_first_parent(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        job = workflow.split("\n  release-boundary:\n", 1)[1].split("\n  hermetic:\n", 1)[0]
        self.assertIn("fetch-depth: 0", job)
        self.assertIn('ci_policy.py boundary --expected-sha "$EXPECTED_SHA"', job)
        self.assertIn("EXPECTED_SHA: ${{ github.sha }}", job)
        self.assertIn("node-version: '*'", job)
        self.assertNotIn("needs:", job)

    def test_actual_aggregate_commands_reject_every_incomplete_job_state(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        gate = workflow.split("\n  hermetic:\n", 1)[1]
        self.assertIn("needs: [plan, checks, browser-fixtures, release-boundary]", gate)
        self.assertIn("if: ${{ always() }}", gate)
        commands = "\n".join(line[10:] for line in gate.split("        run: |\n", 1)[1].splitlines())
        summary = self.root / "summary"
        for plan, checks, browser, boundary in itertools.product(("success", "failure", "cancelled", "skipped", ""), repeat=4):
            env = dict(os.environ, PLAN_RESULT=plan, CHECKS_RESULT=checks, BROWSER_RESULT=browser, BOUNDARY_RESULT=boundary, TIER="full",
                       SOURCE_SHA=self.base, GITHUB_STEP_SUMMARY=str(summary))
            result = subprocess.run(["bash", "-c", commands], env=env)
            self.assertEqual(result.returncode == 0, plan == checks == browser == boundary == "success",
                             (plan, checks, browser, boundary))

    def test_browser_fixtures_use_recorded_source_and_retain_real_chrome_evidence(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        job = workflow.split("\n  browser-fixtures:\n", 1)[1].split("\n  release-boundary:\n", 1)[0]
        self.assertIn("ref: ${{ needs.plan.outputs.source_sha }}", job)
        self.assertIn('export BROWSER_EXECUTABLE_PATH="$(command -v google-chrome)"', job)
        self.assertIn("--ignore-scripts playwright@latest", job)
        inventory = job.split("        fixture: [", 1)[1].split("]", 1)[0].split(", ")
        self.assertEqual(tuple(inventory), FIXTURES)
        self.assertIn("fail-fast: false", job)
        self.assertIn("name: browser / ${{ matrix.fixture }}", job)
        self.assertIn("FIXTURE: ${{ matrix.fixture }}", job)
        self.assertIn('node "test/fixtures/grok-chat-full-ui/$FIXTURE.cjs" 2>&1 | tee "$RUNNER_TEMP/browser-fixtures/$FIXTURE.log"', job)
        self.assertLess(job.index('node "test/fixtures/grok-chat-full-ui/'), job.index('name: Checkout unchanged'))
        self.assertIn('node --version | tee', job)
        self.assertIn('playwright-version.log', job)
        self.assertIn('ci_policy.py guard --expected-sha "$EXPECTED_SHA"', job)
        self.assertLess(job.index("uses: actions/setup-python@v7"), job.index("run: python3 -B"))
        self.assertIn("name: browser-fixtures-${{ matrix.fixture }}", job)
        self.assertIn("if: ${{ always() }}", job.split("name: Checkout unchanged", 1)[1])
        self.assertIn("if-no-files-found: error", job)
        self.assertNotIn("continue-on-error", job)

    def test_browser_pipeline_propagates_failures_and_retains_each_log(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        job = workflow.split("\n  browser-fixtures:\n", 1)[1].split("\n  release-boundary:\n", 1)[0]
        # Execute the actual step bodies with controlled commands. Implicit
        # Actions bash uses -e only: a successful tee can hide a failed fixture.
        steps = {}
        for name in ("Prepare browser fixture runtime", "Rendered UI evidence regressions"):
            step = job.split("      - name: " + name + "\n", 1)[1].split("\n      - name:", 1)[0]
            body = step.split("        run: |\n", 1)[1]
            commands = "\n".join(line[10:] for line in body.splitlines() if line.startswith("          "))
            shell = (["bash", "--noprofile", "--norc", "-eo", "pipefail"]
                     if "        shell: bash\n" in step else ["bash", "-e"])
            steps[name] = (shell, commands)
        self.assertIn("if: ${{ always() }}", job.split("name: Retain browser fixture evidence", 1)[1])
        binary = self.root / "bin"
        binary.mkdir()
        scripts = {
            "npm": 'printf "install output\\n"\n[ "$PIPELINE_FAILURE" != install ]',
            "google-chrome": 'printf "chrome output\\n"\n[ "$PIPELINE_FAILURE" != chrome ]',
            "node": 'printf "node output %s\\n" "$1"\n[ "$PIPELINE_FAILURE" != "$1" ]',
        }
        for name, body in scripts.items():
            path = binary / name
            path.write_text("#!/bin/sh\n" + body + "\n")
            path.chmod(0o700)
        prepare = "Prepare browser fixture runtime"
        render = "Rendered UI evidence regressions"
        cases = [("install", "install.log"), ("chrome", "chrome-version.log")]
        cases.extend(("test/fixtures/grok-chat-full-ui/" + fixture + ".cjs", fixture + ".log")
                     for fixture in FIXTURES)
        cases.extend(("", fixture + ".log") for fixture in FIXTURES)
        for index, (failure, log) in enumerate(cases):
            with self.subTest(failed_command=failure or "none"):
                runtime = self.root / ("runtime-" + str(index))
                logs = runtime / "browser-fixtures"
                env = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ["PATH"],
                           RUNNER_TEMP=str(runtime), PIPELINE_FAILURE=failure,
                           FIXTURE=Path(log).stem if failure not in ("install", "chrome") else FIXTURES[0],
                           PLAYWRIGHT_MODULE_PATH=str(runtime / "unused-module"))
                results = []
                for name in (prepare, render):
                    shell, commands = steps[name]
                    result = subprocess.run([*shell, "-c", commands], cwd=self.root, env=env,
                                            capture_output=True, text=True)
                    results.append(result)
                    if result.returncode:
                        break
                self.assertEqual(results[-1].returncode != 0, bool(failure),
                                 results[-1].stdout + results[-1].stderr)
                self.assertIn("output", (logs / log).read_text())
                if failure not in ("install", "chrome"):
                    fixture_log = env["FIXTURE"] + ".log"
                    self.assertEqual({path.name for path in logs.glob("*.log")},
                                     {"install.log", "chrome-version.log", "node-version.log",
                                      "playwright-version.log", fixture_log})
                    self.assertIn("node output", (logs / fixture_log).read_text())
                    for version in ("node-version.log", "playwright-version.log"):
                        self.assertIn("node output", (logs / version).read_text())

    def test_plan_cli_records_actual_checkout_and_rejects_wrong_candidate(self):
        event = self.root / "event.json"
        event.write_text(json.dumps({}))
        output, summary = self.root / "output", self.root / "summary"
        env = dict(os.environ, GITHUB_EVENT_PATH=str(event), GITHUB_EVENT_NAME="push", GITHUB_OUTPUT=str(output), GITHUB_STEP_SUMMARY=str(summary))
        command = ["python3", "-B", str(ROOT / "test/ci_policy.py"), "plan", "--expected-sha"]
        result = subprocess.run([*command, self.base], cwd=self.root, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("tier=full", output.read_text())
        self.assertIn('groups=["core",', output.read_text())
        self.assertEqual(json.loads(result.stdout)["source_sha"], self.base)
        self.assertEqual(json.loads(result.stdout)["groups"],
                         ["core", "shiploop-1", "shiploop-2", "shiploop-3", "e2e-apparatus"])
        output.unlink()
        result = subprocess.run([*command, "f" * 40], cwd=self.root, env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
