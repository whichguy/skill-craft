"""Whole-run apparatus checks with a fake Grok process; never model evidence."""
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout
import run


FAKE_GROK = r'''
import json, os, pathlib, subprocess, sys, uuid
ROOT = pathlib.Path(__file__).parent
SKILL = ROOT / "skill"
IMPROVE = ROOT / "improve"
args = sys.argv[1:]
if args == ["--version"]:
    print("fake-grok integration fixture 1")
    sys.exit(0)
if args == ["inspect", "--json"]:
    print(json.dumps({"skills":[
        {"name":"shiploop","source":{"path":str(SKILL/"SKILL.md"),"type":"user"},"userInvocable":True},
        {"name":"improve","source":{"path":str(IMPROVE/"SKILL.md"),"type":"user"},"userInvocable":True}
    ]}))
    sys.exit(0)
def option(name): return args[args.index(name)+1]
repo=pathlib.Path(option("--cwd"))
prompt=pathlib.Path(option("--prompt-file")).read_text()
(ROOT / "launches.jsonl").open("a").write(json.dumps({"pid":os.getpid(),"prompt":prompt,"argv":args,"cwd":os.getcwd(),"initial_files":sorted(p.name for p in repo.iterdir()),"skill":(SKILL/"SKILL.md").read_text()})+"\n")
observer_drift=os.environ.get("E2E_TEST_OBSERVER_MODEL_DRIFT_PATH")
if observer_drift: pathlib.Path(observer_drift).write_text("fixture observer changed during model run\n")
git=os.environ["E2E_TEST_GIT"]
def g(*a):
    return subprocess.run([git,"-C",str(repo),*a],capture_output=True,text=True,check=True).stdout.strip()
if not (repo/".git").exists():
    g("init")
    (repo/"README.md").write_text("Fixture baseline, not a real game.\n")
    g("add",".")
    g("-c","user.name=Fixture","-c","user.email=fixture@example.invalid","commit","-m","fixture baseline")
before=g("rev-parse","HEAD")
(repo/"game.txt").write_text(prompt)
if os.environ.get("E2E_TEST_IGNORED_APP"):
    (repo/".gitignore").write_text("generated-app.js\n")
    (repo/"generated-app.js").write_text("export const version = 1;\n")
g("add",".")
g("-c","user.name=Fixture","-c","user.email=fixture@example.invalid","commit","-m","fixture product")
after=g("rev-parse","HEAD")
workspace=repo.parent/".shiploop-runs"/("fixture-"+uuid.uuid4().hex)
run_dir=workspace/"run"
run_dir.mkdir(parents=True)
(workspace/"worktree").mkdir()
def record(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text("# Fixture declaration\n\n```shiploop-state\n"+json.dumps(value)+"\n```\n")
sys.path.insert(0,os.environ["E2E_TEST_NAVIGATOR_ROOT"])
import shiploop_navigator as navigator
state=navigator.new_state(str(workspace/"worktree"),prompt,worktree=True,protocol_version=3,improve_skill="")
navigator.save(run_dir,state)
receipt={"summary":"Synthetic Improve receipt; no Improve runtime executed.","review_refs":["synthetic://review"],"check_refs":["synthetic://check"],"lessons":"Synthetic lesson."}
while state["status"] != "done":
    action=navigator.current_action(state)
    result={"outcome":"done","summary":"Synthetic apparatus declaration; no game work."}
    state=navigator.apply(state,action["id"],result)
    if state["active_improve"] is not None: state=navigator.finish_improve(state,action["id"],receipt)
    navigator.save(run_dir,state)
    if os.environ.get("E2E_TEST_PARTIAL"): break
record(workspace/"workspace.md",{"status":"returned","source_repo":str(repo),"source_head":before,"worktree":str(workspace/"worktree"),"run_dir":str(run_dir)})
record(workspace/"return-receipt.md",{"status":"returned","kind":"fast-forward-merge","expected_source":{"head":after}})
print(json.dumps({"type":"available_commands","commands":[{"name":"shiploop"}]}),flush=True)
control_input=os.environ.get("E2E_TEST_CONTROL_INPUT_REFERENCE")
if control_input:
    print(json.dumps({"type":"tool_call","toolCallId":"control-input","toolName":"read_file","rawInput":{"target_file":control_input}}),flush=True)
    print(json.dumps({"type":"tool_call_update","toolCallId":"control-input","status":"completed","rawOutput":{"exitCode":0}}),flush=True)
commands=[["workspace","start","--repo",str(repo),"--workspace-root",str(workspace)]]
if not os.environ.get("E2E_TEST_MISSING_CALLBACKS"):
    commands += [["improve-complete" if row["action"] in state["improve_results"] else "complete","--run-dir="+str(run_dir),"--action="+row["action"],"--result=fixture"] for row in state["history"]]
    if not os.environ.get("E2E_TEST_PARTIAL"):
        commands += [["workspace","return","--workspace-root",str(workspace)]]
for index, command in enumerate(commands):
    call_id="tool"+str(index)
    print(json.dumps({"type":"tool_call","toolCallId":call_id,"kind":"execute","rawInput":{"argv":["python3",str(SKILL/"scripts/shiploop"),*command]}}),flush=True)
    print(json.dumps({"type":"tool_call_update","toolCallId":call_id,"status":"completed","rawOutput":{"exitCode":0}}),flush=True)
if os.environ.get("E2E_TEST_PARTIAL"):
    import time
    time.sleep(30)
print(json.dumps({"type":"end","stopReason":"end_turn","sessionId":str(uuid.uuid4()),"modelUsage":{"fixture-model":{"inputTokens":1}}}),flush=True)
print("fixture stderr retained separately",file=sys.stderr,flush=True)
if os.environ.get("E2E_TEST_DRIFT"): (SKILL/"SKILL.md").write_text("changed during run")
'''


class RunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="shiploop-e2e-run-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.skill = self.root / "skill"
        (self.skill / "scripts").mkdir(parents=True)
        (self.skill / "SKILL.md").write_text("fixture skill revision one")
        (self.skill / "scripts/shiploop").write_text("# nonexecuting fixture locator")
        self.improve = self.root / "improve"
        self.improve.mkdir()
        (self.improve / "SKILL.md").write_text("fixture improve revision one")
        self.grok = self.root / "fake-grok"
        self.grok.write_text("#!" + sys.executable + "\n" + FAKE_GROK)
        self.grok.chmod(0o755)
        self.repo = self.root / "products/game"
        self.git = run.resolve_git(None)
        self.env = patch.dict(os.environ, {"E2E_TEST_GIT": self.git,
                                          "E2E_TEST_NAVIGATOR_ROOT": str(layout.selected_skill_root() / "scripts")})
        self.env.start()
        self.addCleanup(self.env.stop)
        # Run tests exercise the process boundary with a fake Grok. Real Git
        # publication comparisons have their own hermetic fixture suite.
        freshness = patch.object(run, "inspect_freshness", return_value={
            "ready": True, "status": "ready", "reason": "fixture publication matches selection",
        })
        self.freshness = freshness.start()
        self.addCleanup(freshness.stop)

    def invoke(self, step="ttt-create", name="create", *extra):
        output = self.root / "trials" / name
        code = run.main(["run", "--step", step, "--repo", str(self.repo), "--output", str(output),
                         "--model", "fixture-model", "--grok", str(self.grok), "--git", self.git,
                         "--skill-root", str(self.skill), "--timeout", "10", "--max-turns", "8", *extra])
        return code, output, run.read_json(output / "result.json")

    def salesforce_preflight(self, name="salesforce-target", *, product_cwd=None, checked_at=None):
        cwd = self.repo if product_cwd is None else Path(product_cwd)
        receipt = {
            "schema": "shiploop-e2e-salesforce-target-preflight/1",
            "status": "connected",
            "org_type": "developer",
            "expected_org_id": "00D000000000001AAA",
            "observed_org_id": "00D000000000001AAA",
            "expected_instance_url": "https://fixture-dev.my.salesforce.com",
            "observed_instance_url": "https://fixture-dev.my.salesforce.com",
            "expected_lightning_host": "fixture-dev.lightning.force.com",
            "observed_lightning_host": "fixture-dev.lightning.force.com",
            "is_sandbox": False,
            "my_domain": "fixture-dev",
            "checked_at": checked_at or datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "product_cwd": str(cwd.resolve()),
        }
        path = self.root / f"{name}.json"
        path.write_text(json.dumps(receipt), encoding="utf-8")
        return path, receipt

    def test_trial_and_suite_outputs_cannot_modify_selected_skill(self):
        protected_trial = self.skill / "forbidden-trial"
        protected_suite = self.skill / "forbidden-suite"
        trial = run.main([
            "run", "--step", "ttt-create", "--repo", str(self.repo), "--output", str(protected_trial),
            "--model", "fixture-model", "--grok", str(self.grok), "--git", self.git,
            "--skill-root", str(self.skill), "--timeout", "10", "--max-turns", "8",
        ])
        suite = run.main([
            "suite", "--suite", "launch-smoke", "--only", "ttt-create-intake", "--output", str(protected_suite),
            "--model", "fixture-model", "--grok", str(self.grok), "--git", self.git,
            "--skill-root", str(self.skill), "--timeout", "10", "--max-turns", "8",
        ])
        self.assertEqual(2, trial)
        self.assertEqual(2, suite)
        self.assertFalse(protected_trial.exists())
        self.assertFalse(protected_suite.exists())
        self.assertFalse(self.repo.exists())

    def test_product_paths_cannot_overlap_packages_or_source_before_writes(self):
        audit_package = self.root / "audit-package"
        checkout = self.root / "source-checkout"
        audit_package.mkdir()
        checkout.mkdir()
        alias = self.root / "subject-alias"
        alias.symlink_to(self.skill, target_is_directory=True)
        candidates = [self.skill / "product", audit_package / "product",
                      checkout / "product", alias / "product", self.root]
        for index, repo in enumerate(candidates):
            for mode in ("run", "suite"):
                output = self.root / "trials" / f"protected-{index}-{mode}"
                mode_args = (["run", "--step", "ttt-create"] if mode == "run" else
                             ["suite", "--suite", "ttt-full", "--only", "ttt-create"])
                before = sorted(str(path) for path in self.root.rglob("*"))
                with self.subTest(repo=repo, mode=mode), \
                     patch.object(layout, "PACKAGE_ROOT", audit_package), \
                     patch.object(layout, "canonical_source_checkout", return_value=checkout), \
                     patch.object(run, "preflight", side_effect=ValueError("unexpected preflight")) as preflight, \
                     patch.object(run, "capture_process") as launch:
                    code = run.main([*mode_args, "--repo", str(repo), "--output", str(output),
                                     "--model", "fixture", "--skill-root", str(self.skill)])
                self.assertEqual(code, 2)
                self.assertFalse(preflight.called, 'unsafe product reached preflight')
                self.assertFalse(launch.called, 'unsafe product reached model launch')
                self.assertFalse(output.exists())
                self.assertEqual(before, sorted(str(path) for path in self.root.rglob("*")))

    def test_automatically_allocated_product_parent_cannot_modify_selected_skill(self):
        with patch.object(run.tempfile, "tempdir", str(self.skill)):
            with self.assertRaisesRegex(ValueError, "product must be separate"):
                run._new_suite_product_parent(self.root / "campaign", self.root / "observer",
                                              subject_root=self.skill)
        self.assertEqual(sorted(path.name for path in self.skill.iterdir()), ["SKILL.md", "scripts"])

    def observer_fixture(self, name="observer-inputs"):
        root = self.root / name
        root.mkdir()
        (root / "observer.py").write_text("fixture observer revision one\n")
        (root / "settings.json").write_text('{"fixture": 1}\n')
        return root

    def grade(self, output, *, fail=False):
        receipt = run.read_json(output / "verification-template.json")
        evidence_dir = output / "verification"
        evidence_dir.mkdir(exist_ok=True)
        evidence = evidence_dir / "fixture-observations.txt"
        evidence.write_text("Independent synthetic fixture receipt: checks apparatus only, not a game.\n")
        ref = {"path": evidence.name, "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest()}
        for check in receipt["checks"]:
            check.update(status="fail" if fail else "pass", evidence=[ref])
        if receipt.get("baseline_digest"):
            receipt["incremental_review"].update(status="pass", evidence=[ref])
        run.write_json(output / "verification.json", receipt)
        code = run.main(["grade", "--trial", str(output), "--receipt", str(output / "verification.json")])
        return code, run.read_json(output / "result.json")

    def test_whole_chain_is_fresh_and_observes_changed_skill(self):
        code, output, result = self.invoke()
        self.assertEqual(code, 2, result)
        self.assertEqual(result["statuses"]["overall"], "awaiting-independent-verification", result)
        self.assertEqual(result["statuses"]["protocol"], "declared-complete-return-observed", result)
        self.assertTrue(result["host_observations"]["shiploop_cli_completed"])
        self.assertGreater(result["audit"]["native_events"]["tool_call_count"], 0)
        self.assertGreater(result["audit"]["runs"][0]["accepted_stage_counts"]["implement"], 0)
        self.assertTrue((output / "package-inputs/index.json").is_file())
        self.assertIn("fixture stderr", (output / "capture/stderr.log").read_text())
        behavior = run.read_json(output / "behavior.json")
        self.assertNotEqual(behavior.get("capture_status"), "unavailable", behavior)
        self.assertNotIn(str(self.repo), json.dumps(behavior))
        code, graded = self.grade(output)
        self.assertEqual(code, 0, graded)
        old_digest = graded["skill_digest"]
        (self.skill / "SKILL.md").write_text("fixture skill revision TWO")
        code, second, result = self.invoke("ttt-guidance", "feature", "--baseline", str(output / "result.json"))
        self.assertEqual(code, 2, result)
        self.assertNotEqual(result["skill_digest"], old_digest)
        self.assertTrue((second / "product-before/game.txt").is_file())
        self.assertIn("Create a Google Apps Script", (second / "product-before/game.txt").read_text())
        self.assertIn("Add an active-player", (self.repo / "game.txt").read_text())
        launches = [json.loads(line) for line in (self.root / "launches.jsonl").read_text().splitlines()]
        self.assertEqual(len(launches), 2)
        self.assertEqual(launches[0]["initial_files"], [])
        self.assertEqual([entry["cwd"] for entry in launches], [str(self.repo), str(self.repo)])
        self.assertEqual(run.read_json(output / "manifest.json")["launch_cwd"], str(self.repo))
        self.assertIn("game.txt", launches[1]["initial_files"])
        self.assertNotEqual(launches[0]["pid"], launches[1]["pid"])
        self.assertEqual(launches[1]["skill"], "fixture skill revision TWO")
        self.assertFalse(any(flag in launches[1]["argv"] for flag in ("--resume", "--continue")))
        self.assertEqual(launches[1]["prompt"], run.find_step("ttt-guidance")["prompt"])
        code, result = self.grade(second)
        self.assertEqual(code, 0, result)

    def test_create_rejects_preinitialized_repository_before_model_launch(self):
        import subprocess
        self.repo.mkdir(parents=True)
        subprocess.run([self.git, "init", str(self.repo)], check=True, capture_output=True)
        code, _output, result = self.invoke(name="preinitialized")
        self.assertEqual(code, 2)
        self.assertIn("new empty product folder", result["error"])
        self.assertFalse((self.root / "launches.jsonl").exists())

    def test_salesforce_preflight_rejections_happen_before_output_or_launch(self):
        stale = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=16)).isoformat()
        future = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=120)).isoformat()
        mutations = [
            ("missing", None),
            ("identity-mismatch", lambda receipt: receipt.update(observed_org_id="00D000000000002AAA")),
            ("stale", lambda receipt: receipt.update(checked_at=stale)),
            ("future", lambda receipt: receipt.update(checked_at=future)),
            ("wrong-cwd", lambda receipt: receipt.update(product_cwd=str((self.root / "other-product").resolve()))),
            ("secret-field", lambda receipt: receipt.update(access_token="TOP_SECRET")),
            ("nested-sandbox", lambda receipt: receipt.update(is_sandbox={"access_token": "TOP_SECRET"})),
        ]
        for name, mutate in mutations:
            output = self.root / "trials" / f"salesforce-{name}"
            arguments = [
                "run", "--step", "salesforce-checkers-create", "--repo", str(self.repo),
                "--output", str(output), "--model", "fixture-model", "--grok", str(self.grok),
                "--git", self.git, "--skill-root", str(self.skill),
            ]
            if mutate is not None:
                receipt_path, receipt = self.salesforce_preflight(name)
                mutate(receipt)
                receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
                arguments.extend(["--salesforce-preflight", str(receipt_path)])
            stderr = io.StringIO()
            with self.subTest(name=name), \
                    patch.object(layout, "validate_new_external_output") as validate_output, \
                    patch.object(run, "preflight") as preflight, \
                    patch.object(run, "capture_process") as capture, \
                    patch("sys.stderr", stderr):
                code = run.main(arguments)
            self.assertEqual(code, 2)
            self.assertFalse(output.exists())
            self.assertFalse(self.repo.exists())
            validate_output.assert_not_called()
            preflight.assert_not_called()
            capture.assert_not_called()
            self.assertNotIn("TOP_SECRET", stderr.getvalue())
        self.assertFalse((self.root / "launches.jsonl").exists())

    def test_salesforce_preflight_flag_is_rejected_for_other_steps_before_output(self):
        receipt_path, _receipt = self.salesforce_preflight()
        output = self.root / "trials" / "non-salesforce-preflight"
        with patch.object(run, "preflight") as preflight, patch.object(run, "capture_process") as capture:
            code = run.main([
                "run", "--step", "ttt-create", "--repo", str(self.repo), "--output", str(output),
                "--model", "fixture-model", "--grok", str(self.grok), "--git", self.git,
                "--skill-root", str(self.skill), "--salesforce-preflight", str(receipt_path),
            ])
        self.assertEqual(code, 2)
        self.assertFalse(output.exists())
        preflight.assert_not_called()
        capture.assert_not_called()
        self.assertFalse((self.root / "launches.jsonl").exists())

    def test_salesforce_suite_requires_explicit_repo_before_output(self):
        receipt_path, _receipt = self.salesforce_preflight()
        output = self.root / "trials" / "salesforce-suite-without-repo"
        with patch.object(run, "preflight") as preflight, patch.object(run, "capture_process") as capture:
            code = run.main([
                "suite", "--suite", "salesforce-checkers-full", "--output", str(output),
                "--model", "fixture-model", "--salesforce-preflight", str(receipt_path),
                "--skill-root", str(self.skill),
            ])
        self.assertEqual(code, 2)
        self.assertFalse(output.exists())
        self.assertFalse(self.repo.exists())
        preflight.assert_not_called()
        capture.assert_not_called()
        self.assertFalse((self.root / "launches.jsonl").exists())

    def test_salesforce_preflight_is_pinned_for_one_fake_suite_launch(self):
        receipt_path, receipt = self.salesforce_preflight()
        output = self.root / "trials" / "salesforce-suite"
        code = run.main([
            "suite", "--suite", "salesforce-checkers-full", "--repo", str(self.repo),
            "--output", str(output), "--model", "fixture-model", "--grok", str(self.grok),
            "--git", self.git, "--skill-root", str(self.skill), "--timeout", "10", "--max-turns", "8",
            "--salesforce-preflight", str(receipt_path),
        ])
        self.assertEqual(code, 2)
        manifest = run.read_json(output / "trials" / "salesforce-checkers-create" / "manifest.json")
        pinned = manifest["salesforce_preflight"]
        self.assertEqual(pinned["source_path"], str(receipt_path.resolve()))
        self.assertEqual(pinned["sha256"], hashlib.sha256(receipt_path.read_bytes()).hexdigest())
        self.assertEqual(pinned["checked_at"], receipt["checked_at"])
        self.assertEqual(pinned["product_cwd"], str(self.repo.resolve()))
        self.assertEqual(pinned["identity"], {
            key: receipt[key] for key in run._SALESFORCE_PREFLIGHT_IDENTITY_KEYS if key in receipt
        })
        self.assertEqual(set(pinned), {"source_path", "sha256", "identity", "checked_at", "product_cwd"})
        launches = [json.loads(line) for line in (self.root / "launches.jsonl").read_text().splitlines()]
        self.assertEqual(len(launches), 1)
        self.assertEqual(launches[0]["prompt"], run.find_step("salesforce-checkers-create")["prompt"])

    def test_freshness_failures_retain_receipt_without_launching_builder(self):
        for status in ("unpublished-source", "installed-stale", "freshness-unverified"):
            with self.subTest(status=status), patch.object(run, "capture_process") as capture:
                receipt = {"ready": False, "status": status, "reason": "improve fixture " + status}
                self.freshness.return_value = receipt
                code, output, result = self.invoke(name=status)
                self.assertEqual(code, 2)
                self.assertEqual(result["statuses"]["overall"], "blocked-preflight")
                self.assertEqual(run.read_json(output / "freshness.json"), receipt)
                self.assertIn("no model was launched", result["error"])
                capture.assert_not_called()
                self.assertFalse((self.root / "launches.jsonl").exists())

    def test_check_blocks_stale_improve_without_model(self):
        self.repo.mkdir(parents=True)
        self.freshness.return_value = {
            "ready": False, "status": "installed-stale",
            "reason": "improve-selected-package-version-does-not-match-published-package",
        }
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            code = run.main(["check", "--repo", str(self.repo), "--grok", str(self.grok),
                             "--git", self.git, "--skill-root", str(self.skill)])
        checked = json.loads(stdout.getvalue())
        self.assertEqual(code, 2)
        self.assertEqual(checked["freshness"]["status"], "installed-stale")
        self.assertEqual("shiploop", checked["selection"]["skill"])
        self.assertEqual("improve", checked["improve_selection"]["skill"])
        self.assertFalse(checked["live_model_called"])
        self.assertFalse((self.root / "launches.jsonl").exists())

    def test_single_case_suite_blocks_stale_improve_without_launch(self):
        output = self.root / "blocked-suite"
        self.freshness.return_value = {
            "ready": False, "status": "installed-stale",
            "reason": "improve-selected-package-does-not-match-published-package",
        }
        with patch.object(run, "capture_process") as capture:
            code = run.main(["suite", "--suite", "launch-smoke", "--only", "ttt-create-intake", "--output", str(output),
                             "--model", "fixture-model", "--grok", str(self.grok),
                             "--git", self.git, "--skill-root", str(self.skill)])
        self.assertEqual(code, 2)
        cases = run.read_json(output / "suite-result.json")["cases"]
        self.assertEqual(len(cases), 1)
        self.assertEqual(self.freshness.call_count, len(cases))
        self.assertTrue(all(row["status"] == "blocked-preflight" for row in cases))
        capture.assert_not_called()

    def test_publication_is_checked_once_and_bound_before_launch(self):
        _code, output, _result = self.invoke(name="publication-once")
        self.freshness.assert_called_once()
        preflight = run.read_json(output / "manifest.json")["preflight"]
        self.assertEqual(preflight["freshness"]["status"], "ready")
        self.assertEqual("shiploop", preflight["selection"]["skill"])
        self.assertEqual("improve", preflight["improve_selection"]["skill"])
        self.assertEqual({"shiploop", "improve"}, set(preflight["packages"]))
        self.assertEqual({"shiploop", "improve"}, set(preflight["selections"]))
        self.assertEqual(preflight["package"], preflight["packages"]["shiploop"])
        self.assertEqual(preflight["improve_package"], preflight["packages"]["improve"])
        self.assertNotIn("freshness", run.read_json(output / "preflight-after.json"))

    def test_selected_skill_change_after_freshness_blocks_launch(self):
        original = run.capture_run_artifacts

        def change_selected_skill(*args, **kwargs):
            captured = original(*args, **kwargs)
            (self.skill / "SKILL.md").write_text("changed after publication check")
            return captured

        with patch.object(run, "capture_run_artifacts", side_effect=change_selected_skill), \
                patch.object(run, "capture_process") as capture:
            code, _output, result = self.invoke(name="changed-after-freshness")
        self.assertEqual(code, 2)
        self.assertIn("selected ShipLoop changed after freshness check", result["error"])
        capture.assert_not_called()

    def test_selected_improve_change_after_freshness_blocks_launch(self):
        original = run.capture_run_artifacts

        def change_selected_improve(*args, **kwargs):
            captured = original(*args, **kwargs)
            (self.improve / "SKILL.md").write_text("changed after publication check")
            return captured

        with patch.object(run, "capture_run_artifacts", side_effect=change_selected_improve), \
                patch.object(run, "capture_process") as capture:
            code, _output, result = self.invoke(name="changed-improve-after-freshness")
        self.assertEqual(code, 2)
        self.assertIn("selected Improve changed after freshness check", result["error"])
        capture.assert_not_called()

    def test_optional_behavior_export_failure_preserves_original_trial_outcome(self):
        with (patch.object(run, "preflight", side_effect=ValueError("fixture preflight rejection")),
              patch.object(run, "write_trial_behavior", side_effect=AssertionError("fixture export defect"))):
            code, output, result = self.invoke(name="export-failure")
        self.assertEqual(code, 2)
        self.assertEqual(result["error"], "fixture preflight rejection")
        self.assertEqual(result["statuses"]["overall"], "harness-or-environment-error")
        self.assertEqual(run.read_json(output / "behavior.json")["capture_status"], "unavailable")
        self.assertFalse((self.root / "launches.jsonl").exists())

    def test_stable_disposable_observer_inputs_are_bound_to_the_trial(self):
        observer = self.observer_fixture("observer-inputs-verifier")
        with patch.object(run, "OBSERVER_ROOT", observer):
            code, output, result = self.invoke(name="stable-observer")
        self.assertEqual(code, 2, result)
        self.assertTrue(result["observer_stable"])
        self.assertEqual(result["statuses"]["observer"], "stable")
        provenance = run.read_json(output / "observer-provenance.json")
        self.assertEqual(provenance["entry"]["aggregate_sha256"], result["observer_digest"])
        self.assertEqual(provenance["frozen_snapshot"]["package_sha256"], result["observer_digest"])
        self.assertTrue(provenance["phases"]["before_model_launch"]["matches_frozen_snapshot"])
        self.assertEqual({row["logical_path"] for row in provenance["entry"]["files"]}, {"observer.py", "settings.json"})
        contract = run.read_json(output / "manifest.json")["observer_late_grade_contract"]
        self.assertEqual(result["observer_digest"], contract["frozen_sha256"])

    def test_late_grade_rechecks_trusted_observer_root_and_preserves_drift_invalidity(self):
        observer = self.observer_fixture("observer-inputs-late-grade")
        with patch.object(run, "OBSERVER_ROOT", observer):
            _code, output, result = self.invoke(name="late-grade-observer-drift")
            self.assertTrue(result["observer_stable"])
            (observer / "observer.py").write_text("fixture observer revision two\n")
            code, graded = self.grade(output)

        self.assertEqual(code, 2, graded)
        self.assertFalse(graded["observer_stable"])
        self.assertEqual("invalid-trial", graded["statuses"]["overall"])
        self.assertEqual("changed-after-trial-invalid", graded["statuses"]["observer"])
        late = graded["late_grade_observer_observation"]
        self.assertFalse(late["matches_frozen_identity"])
        self.assertEqual(run.harness_manifest(observer)["aggregate_sha256"], late["current"]["aggregate_sha256"])
        self.assertNotEqual(late["frozen_sha256"], late["current"]["aggregate_sha256"])

    def test_late_grade_rejects_missing_or_malformed_frozen_observer_identity(self):
        observer = self.observer_fixture("observer-inputs-late-grade-contract")
        for mutation in ("missing", "malformed"):
            with self.subTest(mutation=mutation), patch.object(run, "OBSERVER_ROOT", observer):
                self.repo = self.root / "products" / f"late-grade-observer-{mutation}"
                _code, output, _result = self.invoke(name=f"late-grade-observer-{mutation}")
                manifest = run.read_json(output / "manifest.json")
                contract = manifest["observer_late_grade_contract"]
                if mutation == "missing":
                    contract.pop("frozen_sha256")
                else:
                    contract["frozen_sha256"] = "not-a-sha256"
                run.write_json(output / "manifest.json", manifest)
                code, graded = self.grade(output)

            self.assertEqual(code, 2, graded)
            self.assertFalse(graded["observer_stable"])
            self.assertEqual("invalid-trial", graded["statuses"]["overall"])
            self.assertEqual("observer-identity-unavailable", graded["statuses"]["observer"])
            self.assertFalse(graded["late_grade_observer_observation"]["identity_complete"])

    def test_recorded_prior_run_reuse_cannot_be_graded_into_success(self):
        _, output, result = self.invoke(name="isolation-failure")
        self.assertEqual(result["isolation"]["status"], "pass")
        result["isolation"] = {"status": "fail", "prior_runs_recovered": [{"run_id": "old"}]}
        run.write_json(output / "result.json", result)
        code, result = self.grade(output)
        self.assertEqual(code, 2)
        self.assertEqual(result["statuses"]["overall"], "run-isolation-failed")

    def test_late_grade_rejects_changed_git_ignored_application_source(self):
        from contextlib import redirect_stderr
        import io
        with patch.dict(os.environ, {"E2E_TEST_IGNORED_APP": "1"}):
            _, output, result = self.invoke(name="ignored-application")
        self.assertEqual(result["statuses"]["overall"], "awaiting-independent-verification")
        self.assertIn("generated-app.js", {row["path"] for row in run.read_json(output / "after.json")["files"]})
        (self.repo / "generated-app.js").write_text("export const version = 2;\n")
        diagnostic = io.StringIO()
        with redirect_stderr(diagnostic):
            code, _ = self.grade(output)
        self.assertEqual(code, 2)
        self.assertIn("stale candidate", diagnostic.getvalue())
        self.assertFalse((output / "grade.json").exists())

    def test_preflight_observer_mutation_blocks_capture_and_model_launch(self):
        observer = self.observer_fixture()
        original_preflight = run.preflight
        first = True

        def mutate_after_preflight(*args, **kwargs):
            nonlocal first
            checked = original_preflight(*args, **kwargs)
            if first:
                first = False
                (observer / "observer.py").write_text("fixture observer revision two\n")
            return checked

        with patch.object(run, "OBSERVER_ROOT", observer), patch.object(run, "preflight", side_effect=mutate_after_preflight):
            code, output, result = self.invoke(name="preflight-observer-drift")
        self.assertEqual(code, 2, result)
        self.assertEqual(result["statuses"]["overall"], "invalid-trial")
        self.assertEqual(result["statuses"]["observer"], "source-changed-before-launch")
        self.assertIn("observer-source-changed before model launch; no model was launched", result["error"])
        self.assertFalse((output / "capture").exists())
        self.assertFalse((self.root / "launches.jsonl").exists())
        provenance = run.read_json(output / "observer-provenance.json")
        phase = provenance["phases"]["after_preflight"]
        self.assertFalse(phase["matches_entry"])
        self.assertEqual(phase["delta_from_entry"]["changed"], ["observer.py"])
        self.assertIn("observer.py", {row["logical_path"] for row in provenance["entry"]["files"]})

    def test_observer_mutation_during_model_or_verifier_cannot_upgrade_a_trial(self):
        observer = self.observer_fixture()
        with patch.object(run, "OBSERVER_ROOT", observer), patch.dict(os.environ, {"E2E_TEST_OBSERVER_MODEL_DRIFT_PATH": str(observer / "observer.py")}):
            code, output, result = self.invoke(name="model-observer-drift")
        self.assertEqual(code, 2, result)
        self.assertTrue((self.root / "launches.jsonl").is_file())
        self.assertFalse(result["observer_stable"])
        self.assertEqual(result["statuses"]["overall"], "invalid-trial")
        self.assertEqual(result["statuses"]["observer"], "changed-during-observation-invalid")
        self.assertEqual(run.read_json(output / "observer-provenance.json")["phases"]["after_observation"]["delta_from_entry"]["changed"], ["observer.py"])
        self.assertEqual(self.grade(output)[0], 2)
        self.assertEqual(run.read_json(output / "result.json")["statuses"]["overall"], "invalid-trial")

        self.repo = self.root / "products/verifier"
        observer = self.observer_fixture("observer-inputs-verifier")
        verifier = self.root / "observer-drifting-verifier.py"
        verifier.write_text('''import hashlib,json,os,pathlib
trial=pathlib.Path(os.environ["SHIPLOOP_E2E_TRIAL"])
evidence=pathlib.Path(os.environ["SHIPLOOP_E2E_EVIDENCE"])
receipt=json.loads((trial/"verification-template.json").read_text())
artifact=evidence/"independent.txt"
artifact.write_text("Synthetic independent observation, apparatus test only.")
ref={"path":artifact.name,"sha256":hashlib.sha256(artifact.read_bytes()).hexdigest()}
for check in receipt["checks"]: check.update(status="pass",evidence=[ref])
pathlib.Path(os.environ["E2E_TEST_OBSERVER_VERIFIER_DRIFT_PATH"]).write_text("fixture observer changed during verifier run\\n")
print(json.dumps(receipt))
''')
        with patch.object(run, "OBSERVER_ROOT", observer), patch.dict(os.environ, {"E2E_TEST_OBSERVER_VERIFIER_DRIFT_PATH": str(observer / "observer.py")}):
            code, output, result = self.invoke("ttt-create", "verifier-observer-drift", "--verifier", json.dumps([sys.executable, str(verifier)]))
        self.assertEqual(code, 2, result)
        self.assertEqual(result["grade"]["product_status"], "passed")
        self.assertFalse(result["observer_stable"])
        self.assertEqual(result["statuses"]["overall"], "invalid-trial")
        self.assertEqual(result["statuses"]["observer"], "changed-during-observation-invalid")
        self.assertEqual(run.read_json(output / "observer-provenance.json")["phases"]["after_verifier"]["delta_from_entry"]["changed"], ["observer.py"])
        self.assertEqual(self.grade(output)[0], 2)
        self.assertEqual(run.read_json(output / "result.json")["statuses"]["overall"], "invalid-trial")

    def test_unverified_or_forged_predecessor_is_not_passed(self):
        _, output, result = self.invoke()
        code, _, blocked = self.invoke("ttt-guidance", "blocked", "--baseline", str(output / "result.json"))
        self.assertEqual(code, 2)
        self.assertIn("predecessor is not independently verified", blocked["error"])
        result["statuses"]["overall"] = "passed"
        run.write_json(output / "result.json", result)
        code, _, forged = self.invoke("ttt-guidance", "forged", "--baseline", str(output / "result.json"))
        self.assertEqual(code, 2)
        self.assertNotEqual(forged["statuses"]["overall"], "passed")
        self.assertEqual(len((self.root / "launches.jsonl").read_text().splitlines()), 1)

    def test_drift_and_regrading_cannot_leave_stale_pass(self):
        with patch.dict(os.environ, {"E2E_TEST_DRIFT": "1"}):
            _, output, result = self.invoke()
        self.assertEqual(result["statuses"]["overall"], "invalid-trial")
        self.assertEqual(self.grade(output)[0], 2)
        code, invalid_failure = self.grade(output, fail=True)
        self.assertEqual(code, 2, invalid_failure)
        self.assertTrue(invalid_failure["grade"]["receipt_valid"])
        self.assertEqual(invalid_failure["grade"]["product_status"], "failed")
        self.assertEqual(invalid_failure["statuses"]["overall"], "invalid-trial")
        # Restore stable apparatus on a separate clean fixture, then invalidate a passing receipt.
        self.repo = self.root / "products/second"
        _, output, _ = self.invoke(name="second")
        self.assertEqual(self.grade(output)[0], 0)
        code, result = self.grade(output, fail=True)
        self.assertEqual(code, 2)
        self.assertTrue(result["grade"]["receipt_valid"])
        self.assertEqual(result["statuses"]["overall"], "product-failed")

    def test_invalid_failed_receipt_marks_trial_invalid_not_product_failed(self):
        _, output, _ = self.invoke(name="invalid-failed-receipt")
        receipt = run.read_json(output / "verification-template.json")
        evidence_dir = output / "verification"
        evidence_dir.mkdir(exist_ok=True)
        failure = evidence_dir / "failure-observations.txt"
        failure.write_text("Synthetic failed-check observation.\n", encoding="utf-8")
        ref = {"path": failure.name, "sha256": hashlib.sha256(failure.read_bytes()).hexdigest()}
        for check in receipt["checks"]:
            check.update(status="fail", evidence=[ref])
        receipt["candidate_digest"] = "stale-candidate-tree-sha"
        run.write_json(output / "verification.json", receipt)

        code = run.main(["grade", "--trial", str(output), "--receipt", str(output / "verification.json")])
        graded = run.read_json(output / "result.json")

        self.assertEqual(code, 2, graded)
        self.assertEqual(graded["grade"]["product_status"], "error")
        self.assertFalse(graded["grade"]["receipt_valid"])
        self.assertEqual(graded["grade"]["required_checks"]["authorized-deployment"]["status"], "fail")
        self.assertEqual(graded["statuses"]["product"], "error")
        self.assertEqual(graded["statuses"]["overall"], "invalid-trial")

        code, corrected = self.grade(output)

        self.assertEqual(code, 0, corrected)
        self.assertTrue(corrected["grade"]["receipt_valid"])
        self.assertEqual(corrected["statuses"]["overall"], "passed")

    def test_malformed_grade_receipt_invalidates_a_previously_passing_trial(self):
        _, output, _ = self.invoke(name="malformed-grade-receipt")
        self.assertEqual(self.grade(output)[0], 0)
        malformed = output / "malformed-receipt.json"
        malformed.write_text("{not JSON\n", encoding="utf-8")

        code = run.main(["grade", "--trial", str(output), "--receipt", str(malformed)])
        graded = run.read_json(output / "result.json")

        self.assertEqual(code, 2, graded)
        self.assertEqual(graded["statuses"]["overall"], "invalid-trial")
        self.assertIn("Expecting", graded["error"])

    def test_verifier_mutation_sensitive_file_and_missing_evidence_rejected(self):
        _, output, _ = self.invoke()
        self.assertEqual(self.grade(output)[0], 0)
        (self.repo / ".env").write_text("LOCAL_FIXTURE_VALUE=changed\n")
        self.assertEqual(run.main(["grade", "--trial", str(output), "--receipt", str(output / "verification.json")]), 2)
        (self.repo / ".env").unlink()
        (output / "verification/fixture-observations.txt").unlink()
        self.assertEqual(run.main(["grade", "--trial", str(output), "--receipt", str(output / "verification.json")]), 2)

    def test_catalog_dependencies_and_budget_boundaries(self):
        families = run.scenarios()
        expected_kinds = {
            "tic-tac-toe": ["create", "feature", "refine"],
            "checkers": ["create", "feature", "refine"],
            "salesforce-checkers": ["create"],
            "battleship": ["create", "feature", "refine"],
        }
        self.assertEqual({family["id"] for family in families}, set(expected_kinds))
        for family in families:
            self.assertEqual([step["kind"] for step in family["steps"]], expected_kinds[family["id"]])
            previous = None
            for step in family["steps"]:
                self.assertEqual(step["depends_on"], previous)
                self.assertEqual(set(step["required_checks"]), {row["id"] for row in step["checks"]})
                previous = step["id"]
        for bad in ("nan", "inf", "0"):
            code = run.main(["run", "--step", "ttt-create", "--repo", str(self.repo), "--output", str(self.root / "unused"), "--model", "fixture", "--timeout", bad])
            self.assertEqual(code, 2)
        self.assertFalse((self.root / "unused").exists())

    def test_runner_forwards_requested_timeout_to_native_background_wait(self):
        code, output, result = self.invoke("ttt-create", "background-wait", "--timeout", "4800")
        self.assertEqual(code, 2, result)
        manifest = run.read_json(output / "manifest.json")
        argv = manifest["argv"]
        self.assertEqual("4800", argv[argv.index("--background-wait-timeout") + 1])
        self.assertEqual("xhigh", argv[argv.index("--reasoning-effort") + 1])
        self.assertEqual("xhigh", manifest["reasoning_effort_requested"])

    def test_runner_records_the_explicit_effort_actually_passed_to_grok(self):
        code, output, result = self.invoke("ttt-create", "explicit-effort", "--reasoning-effort", " high ")
        self.assertEqual(code, 2, result)
        manifest = run.read_json(output / "manifest.json")
        argv = manifest["argv"]
        self.assertEqual("high", argv[argv.index("--reasoning-effort") + 1])
        self.assertEqual("high", manifest["reasoning_effort_requested"])

    def test_partial_boundary_is_observed_without_full_product_pass(self):
        with patch.dict(os.environ, {"E2E_TEST_PARTIAL": "1"}):
            code, output, result = self.invoke("ttt-create", "partial", "--stop-after-stage", "intake")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["statuses"]["overall"], "partial-smoke-passed")
        self.assertEqual(result["statuses"]["product"], "unverified")
        self.assertEqual(result["process"]["termination_reason"], "requested_boundary")
        self.assertFalse(result["process"]["timed_out"])
        self.assertFalse(result["lifecycle"]["return_observed"])
        self.assertFalse(run.full_pass_eligible(result, {"product_status": "passed"}))
        argv = run.read_json(output / "manifest.json")["argv"]
        self.assertEqual(argv[argv.index("--reasoning-effort") + 1], "xhigh")
        observed = result["partial_observation"]
        self.assertTrue(observed["reached"])
        result["partial_observation"] = {**observed, "accepted_after_boundary": 1}
        self.assertFalse(run.partial_pass_eligible(result))
        result["partial_observation"] = observed
        result["process"]["termination_reason"] = None
        result["process"]["exit_code"] = 0
        self.assertFalse(run.partial_pass_eligible(result))
        events = {**result["host_observations"], "cli_calls": []}
        self.assertFalse(run.partial_observation(result["navigation"], events, run.find_step("ttt-create")["prompt"],
                         self.repo, run.read_json(output / "initial-evidence.json"),
                         run.read_json(output / "artifact-index.json"), "intake")["reached"])
        self.assertEqual(self.grade(output)[0], 2)

    def test_control_input_exposure_invalidates_partial_full_and_late_grade(self):
        full_output = self.root / "trials" / "exposed-full"
        with patch.dict(os.environ, {"E2E_TEST_CONTROL_INPUT_REFERENCE": str(full_output / "manifest.json")}):
            code, output, result = self.invoke(name="exposed-full")
        self.assertEqual(code, 2, result)
        self.assertEqual("invalid-trial", result["statuses"]["overall"])
        self.assertTrue(result["control_input_observation"]["exposure_observed"])
        self.assertFalse(run.full_pass_eligible(result, {"product_status": "passed"}))

        # The retained event stream is authoritative for a late grade. A forged
        # cached observation cannot clear a prior or recomputed exposure.
        result["control_input_observation"] = {"exposure_observed": False}
        result["statuses"]["overall"] = "awaiting-independent-verification"
        run.write_json(output / "result.json", result)
        code, graded = self.grade(output)
        self.assertEqual(code, 2, graded)
        self.assertEqual("invalid-trial", graded["statuses"]["overall"])
        self.assertTrue(graded["control_input_observation"]["exposure_observed"])

        self.repo = self.root / "products" / "partial-exposure"
        partial_output = self.root / "trials" / "exposed-partial"
        with patch.dict(os.environ, {
            "E2E_TEST_PARTIAL": "1",
            "E2E_TEST_CONTROL_INPUT_REFERENCE": str(partial_output / "manifest.json"),
        }):
            code, _output, partial = self.invoke("ttt-create", "exposed-partial", "--stop-after-stage", "intake")
        self.assertEqual(code, 2, partial)
        self.assertEqual("invalid-trial", partial["statuses"]["overall"])
        self.assertFalse(run.partial_pass_eligible(partial))

    def test_new_control_input_gate_rejects_removed_roots_on_late_grade(self):
        _code, output, result = self.invoke(name="removed-control-roots")
        manifest = run.read_json(output / "manifest.json")
        manifest.pop("control_roots")
        run.write_json(output / "manifest.json", manifest)
        result["control_input_observation"] = {"exposure_observed": False, "observation_complete": True}
        result["statuses"]["overall"] = "awaiting-independent-verification"
        run.write_json(output / "result.json", result)

        code, graded = self.grade(output)

        self.assertEqual(code, 2, graded)
        self.assertEqual("invalid-trial", graded["statuses"]["overall"])
        self.assertFalse(graded["control_input_observation"]["observation_complete"])
        self.assertEqual("control-input-observation-unavailable", graded["statuses"]["control_input"])

    def test_new_control_input_gate_rejects_removed_contract_on_late_grade(self):
        _code, output, result = self.invoke(name="removed-control-contract")
        manifest = run.read_json(output / "manifest.json")
        manifest.pop("control_input_observer")
        run.write_json(output / "manifest.json", manifest)
        result["control_input_observation"] = {"exposure_observed": False, "observation_complete": True}
        result["statuses"]["overall"] = "awaiting-independent-verification"
        run.write_json(output / "result.json", result)

        code, graded = self.grade(output)

        self.assertEqual(code, 2, graded)
        self.assertEqual("invalid-trial", graded["statuses"]["overall"])
        self.assertFalse(graded["control_input_observation"]["observation_complete"])
        self.assertEqual("control-input-observation-unavailable", graded["statuses"]["control_input"])

    def test_new_control_input_gate_rejects_malformed_retained_events_on_late_grade(self):
        _code, output, result = self.invoke(name="malformed-control-events")
        events = output / "capture" / "events.jsonl"
        events.write_text(events.read_text(encoding="utf-8") + "{malformed\n", encoding="utf-8")
        result["control_input_observation"] = {"exposure_observed": False, "observation_complete": True}
        result["statuses"]["overall"] = "awaiting-independent-verification"
        run.write_json(output / "result.json", result)

        code, graded = self.grade(output)

        self.assertEqual(code, 2, graded)
        self.assertEqual("invalid-trial", graded["statuses"]["overall"])
        self.assertFalse(graded["control_input_observation"]["observation_complete"])
        self.assertEqual("control-input-observation-incomplete", graded["statuses"]["control_input"])

    def test_manual_feature_cases_reuse_original_repo_and_verified_baselines(self):
        launches = []

        def fake_trial(args):
            launches.append(args)
            run.write_json(Path(args.output) / "result.json", {"statuses": {"overall": "passed"}})
            return 0

        with patch.object(run, "run_trial", side_effect=fake_trial):
            create_code = run.main([
                "suite", "--suite", "ttt-full", "--only", "ttt-create",
                "--output", str(self.root / "suite-create"), "--model", "fixture",
            ])
            create = launches[-1]
            guidance_code = run.main([
                "suite", "--suite", "ttt-full", "--only", "ttt-guidance",
                "--repo", create.repo, "--baseline", str(Path(create.output) / "result.json"),
                "--output", str(self.root / "suite-guidance"), "--model", "fixture",
            ])
            guidance = launches[-1]
            best_move_code = run.main([
                "suite", "--suite", "ttt-full", "--only", "ttt-best-move",
                "--repo", create.repo, "--baseline", str(Path(guidance.output) / "result.json"),
                "--output", str(self.root / "suite-best-move"), "--model", "fixture",
            ])
            best_move = launches[-1]

        self.assertEqual([create_code, guidance_code, best_move_code], [0, 0, 0])
        self.assertEqual(len(launches), 3)
        self.assertEqual(len({args.repo for args in launches}), 1)
        self.assertIsNone(create.baseline)
        self.assertEqual(guidance.repo, create.repo)
        self.assertEqual(guidance.baseline, str(Path(create.output) / "result.json"))
        self.assertEqual(best_move.repo, create.repo)
        self.assertEqual(best_move.baseline, str(Path(guidance.output) / "result.json"))
        self.assertEqual([args.step for args in launches], ["ttt-create", "ttt-guidance", "ttt-best-move"])
        self.assertTrue(all(args.reasoning_effort == "xhigh" for args in launches))
        self.addCleanup(shutil.rmtree,
                        run.read_json(self.root / "suite-create" / "suite-execution.json")["product_parent"],
                        ignore_errors=True)

    def test_suite_executor_uses_opaque_external_product_repositories_and_persists_lineage(self):
        launches = []

        def fake_trial(args):
            launches.append(args)
            run.write_json(Path(args.output) / "result.json", {"statuses": {"overall": "passed"}})
            return 0

        output = self.root / "isolated-suite"
        with patch.object(run, "run_trial", side_effect=fake_trial):
            self.assertEqual(run.main([
                "suite", "--suite", "ttt-full", "--only", "ttt-create",
                "--output", str(output), "--model", "fixture",
            ]), 0)

        execution = run.read_json(output / "suite-execution.json")
        product_repo = Path(execution["product_repositories"]["tic-tac-toe"])
        self.addCleanup(shutil.rmtree, execution["product_parent"], ignore_errors=True)
        self.assertTrue(product_repo.is_dir())
        self.assertFalse(product_repo.is_relative_to(output.resolve()))
        self.assertFalse(product_repo.is_relative_to(Path(run.OBSERVER_ROOT).resolve()))
        self.assertEqual({str(product_repo)}, {args.repo for args in launches})
        self.assertTrue(all(Path(args.repo).name != "ttt-full" for args in launches))
        self.assertTrue(all(getattr(args, "control_root") == str(output.resolve()) for args in launches))
        self.assertEqual("ttt-full", run.read_json(output / "suite-manifest.json")["id"])
        self.assertNotIn("product_repositories", run.read_json(output / "suite-manifest.json"))

    def test_suite_rejects_caller_repository_nested_with_campaign_control_root(self):
        cases = [
            (self.root / "campaign-parent" / "product", self.root / "campaign-parent"),
            (self.root / "caller-parent", self.root / "caller-parent" / "campaign"),
        ]
        for repo, output in cases:
            with self.subTest(repo=repo, output=output), patch.object(run, "run_trial") as launch:
                code = run.main([
                    "suite", "--suite", "ttt-full", "--only", "ttt-create", "--repo", str(repo),
                    "--output", str(output), "--model", "fixture",
                ])
            self.assertEqual(code, 2)
            launch.assert_not_called()
            self.assertFalse(output.exists())

    def test_run_rejects_resolved_symlink_ancestor_nesting_before_launch(self):
        real = self.root / "real"
        real.mkdir()
        alias = self.root / "unrelated-alias"
        alias.symlink_to(real, target_is_directory=True)
        cases = [
            (real / "product", alias / "product" / "trial"),
            (alias / "campaign" / "product", real / "campaign"),
        ]
        for repo, output in cases:
            with self.subTest(repo=repo, output=output):
                code = run.main([
                    "run", "--step", "ttt-create", "--repo", str(repo), "--output", str(output),
                    "--model", "fixture", "--grok", str(self.grok), "--git", self.git,
                    "--skill-root", str(self.skill),
                ])
            self.assertEqual(code, 2)
            self.assertFalse(output.exists())
        self.assertFalse((self.root / "launches.jsonl").exists())

    def test_suite_rejects_multiple_cases_before_creating_output_or_launching(self):
        selections = [
            ["suite", "--suite", "launch-smoke"],
            ["suite", "--suite", "ttt-full", "--only", "ttt-create", "--only", "ttt-guidance"],
        ]
        for index, selection in enumerate(selections):
            output = self.root / f"multi-case-{index}"
            stderr = io.StringIO()
            with self.subTest(selection=selection), \
                    patch.object(layout, "validate_new_external_output") as validate_output, \
                    patch.object(run, "preflight") as preflight, \
                    patch.object(run, "capture_process") as capture, \
                    patch.object(run, "run_trial") as launch, \
                    patch("sys.stderr", stderr):
                code = run.main([*selection, "--output", str(output), "--model", "fixture"])
            self.assertEqual(code, 2)
            self.assertIn("use exactly one --only case/step ID and audit its result before continuing", stderr.getvalue())
            self.assertFalse(output.exists())
            validate_output.assert_not_called()
            preflight.assert_not_called()
            capture.assert_not_called()
            launch.assert_not_called()
        self.assertFalse((self.root / "launches.jsonl").exists())

    def test_repeated_same_only_value_still_selects_one_case(self):
        launches = []

        def fake_trial(args):
            launches.append(args)
            run.write_json(Path(args.output) / "result.json", {"statuses": {"overall": "passed"}})
            return 0

        output = self.root / "deduplicated-only"
        with patch.object(run, "run_trial", side_effect=fake_trial):
            code = run.main([
                "suite", "--suite", "ttt-full", "--only", "ttt-create", "--only", "ttt-create",
                "--output", str(output), "--model", "fixture",
            ])
        self.assertEqual(code, 0)
        self.assertEqual(len(launches), 1)
        self.assertEqual(launches[0].step, "ttt-create")
        self.assertEqual(run.read_json(output / "suite-result.json")["selected"], 1)
        self.addCleanup(shutil.rmtree,
                        run.read_json(output / "suite-execution.json")["product_parent"],
                        ignore_errors=True)

    def test_external_verifier_argv_is_run_after_developer_and_bound(self):
        verifier = self.root / "independent fixture verifier.py"
        verifier.write_text('''import hashlib,json,os,pathlib
trial=pathlib.Path(os.environ["SHIPLOOP_E2E_TRIAL"])
evidence=pathlib.Path(os.environ["SHIPLOOP_E2E_EVIDENCE"])
receipt=json.loads((trial/"verification-template.json").read_text())
artifact=evidence/"independent.txt"
artifact.write_text("Synthetic independent observation, apparatus test only.")
ref={"path":artifact.name,"sha256":hashlib.sha256(artifact.read_bytes()).hexdigest()}
for check in receipt["checks"]: check.update(status="pass",evidence=[ref])
print(json.dumps(receipt))
''')
        code, output, result = self.invoke("ttt-create", "external", "--verifier", json.dumps([sys.executable, str(verifier)]))
        self.assertEqual(code, 0, result)
        self.assertTrue((output / "verifier-capture/stdout.log").is_file())
        self.assertEqual(result["grade"]["product_status"], "passed")
        # An edited result cannot reduce the frozen required-check set.
        result["required_checks"] = []
        run.write_json(output / "result.json", result)
        self.assertEqual(run.main(["grade", "--trial", str(output), "--receipt", str(output / "verification.json")]), 2)
        self.assertEqual(run.read_json(output / "result.json")["statuses"]["overall"], "invalid-trial")

    def test_completed_state_without_observed_callbacks_cannot_pass(self):
        with patch.dict(os.environ, {"E2E_TEST_MISSING_CALLBACKS": "1"}):
            _, output, result = self.invoke()
        self.assertEqual(result["statuses"]["protocol"], "declared-complete-return-observed")
        self.assertTrue(result["host_observations"]["shiploop_cli_completed"])
        self.assertFalse(result["lifecycle"]["complete"])
        self.assertGreater(len(result["lifecycle"]["missing_callback_actions"]), 0)
        self.assertEqual(self.grade(output)[0], 2)

    def test_batch_exit_cannot_certify_an_earlier_callback(self):
        _, output, result = self.invoke()
        events = result["host_observations"]
        calls = events["cli_calls"]
        callbacks = [call for call in calls if call["argv_tail"][0] == "complete"]
        returned = next(call for call in calls if call["argv_tail"][:2] == ["workspace", "return"])
        # A failing callback followed by a successful return would expose one tool exit 0.
        callbacks[-1]["call_id"] = returned["call_id"]
        observed = run.lifecycle_observation(events, result["navigation"], run.find_step("ttt-create")["prompt"],
                                             self.repo, run.read_json(output / "initial-evidence.json"))
        self.assertFalse(observed["complete"])
        self.assertTrue(observed["ambiguous_tool_call_ids"])
        self.assertEqual(len(observed["missing_callback_actions"]), 1)


if __name__ == "__main__":
    unittest.main()
