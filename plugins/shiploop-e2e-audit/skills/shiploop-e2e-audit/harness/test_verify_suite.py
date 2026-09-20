#!/usr/bin/env python3
"""No-model adversarial checks for the composite nine-case verifier."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import grading  # noqa: E402
import oracle_games as oracle  # noqa: E402
import verify_suite as suite  # noqa: E402


DRIVER_SOURCE = r'''
import hashlib
import json
from pathlib import Path
import sys

request = json.load(sys.stdin)
repo = Path(request["repo"])
request_sha256 = hashlib.sha256(json.dumps(
    request, sort_keys=True, ensure_ascii=False, separators=(",", ":")
).encode("utf-8")).hexdigest()
mode = (repo / "mode").read_text().strip()
case_id = request["case"]["id"]
if mode == "mutate":
    (repo / "driver-wrote.txt").write_text("unexpected source mutation")

def other(player):
    return "O" if player == "X" else "X"

def winner(board):
    for a, b, c in ((0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)):
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None

def outcome(board):
    return winner(board) or ("draw" if all(board) else "playing")

def wins(board, player):
    out=[]
    for cell, value in enumerate(board):
        if not value:
            candidate=list(board); candidate[cell]=player
            if winner(candidate) == player: out.append(cell)
    return out

def ttt_observations():
    board=[""]*9
    active="X"
    state="playing"
    observations=[]
    for action in request["actions"]:
        if action["type"] == "reset":
            board=[""]*9; active="X"; state="playing"
        elif action["type"] == "move" and state == "playing" and board[action["cell"]] == "":
            board[action["cell"]]=active
            state=outcome(board)
            if state == "playing": active=other(active)
        legal=[index for index,value in enumerate(board) if not value] if state == "playing" else []
        suggestion=(wins(board,active) or wins(board,other(active)) or legal)
        highlights=list(legal)
        if mode == "guidance-absent" and case_id == "ttt-turn-indicator-and-legal-highlights":
            highlights=[]
        if mode == "base-regression" and case_id == "ttt-base-game":
            shown=[""]*9
        else:
            shown=list(board)
        observations.append({"board":shown,"active_player":active,"outcome":state,
                             "legal_highlights":highlights,
                             "recommended_move":suggestion[0] if suggestion else None})
    return observations

if request["family"] == "tic-tac-toe" and not case_id.startswith("oracle-"):
    observations=ttt_observations()
else:
    observations=[{"semantic": "fail" if mode == "generic-fail" else "pass"} for _ in request["actions"]]
print(json.dumps({"schema":"shiploop-e2e-driver-response/1", "request_sha256":request_sha256,
                  "repo":str(repo.resolve()), "observations":observations}))
'''


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CompositeVerifierTests(unittest.TestCase):
    def test_runtime_cache_creation_does_not_change_source_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = root / "app.js"
            app.write_text("const version = 1;\n")
            before = suite.source_fingerprint(root)
            (root / "node_modules").mkdir()
            (root / "node_modules" / "cache").write_text("runtime-only\n")
            after = suite.source_fingerprint(root)
            self.assertIn("node_modules", after["ignored"])
            self.assertEqual(before["digest"], after["digest"])
            app.write_text("const version = 2;\n")
            self.assertNotEqual(after["digest"], suite.source_fingerprint(root)["digest"])

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.driver = self.root / "semantic_driver.py"
        self.driver.write_text(textwrap.dedent(DRIVER_SOURCE), encoding="utf-8")
        self.fixture_count = 0

    def scenario(self, step_id: str) -> tuple[dict, dict]:
        return suite._catalog_context(step_id)

    def fixture(self, step_id: str, *, candidate_mode: str = "good", baseline_mode: str = "good") -> tuple[dict[str, str], Path, Path, Path, dict, dict]:
        family, step = self.scenario(step_id)
        self.fixture_count += 1
        suffix = f"{step_id}-{candidate_mode}-{baseline_mode}-{self.fixture_count}"
        trial = self.root / f"trial-{suffix}"
        candidate = self.root / f"candidate-{suffix}"
        baseline = self.root / f"baseline-{suffix}"
        evidence = trial / "verification"
        trial.mkdir()
        candidate.mkdir()
        baseline.mkdir()
        evidence.mkdir()
        candidate.joinpath("mode").write_text(candidate_mode, encoding="utf-8")
        baseline.joinpath("mode").write_text(baseline_mode, encoding="utf-8")
        candidate.joinpath("app.txt").write_text("candidate", encoding="utf-8")
        baseline.joinpath("app.txt").write_text("baseline", encoding="utf-8")
        incremental = step["kind"] != "create"
        result = {
            "trial_id": trial.name,
            "step_id": step_id,
            "candidate_digest": "c" * 64,
            "baseline_digest": "b" * 64 if incremental else None,
            "required_checks": step["required_checks"],
        }
        trial.joinpath("result.json").write_text(json.dumps(result), encoding="utf-8")
        env = {"SHIPLOOP_E2E_TRIAL": str(trial), "SHIPLOOP_E2E_REPO": str(candidate),
               "SHIPLOOP_E2E_EVIDENCE": str(evidence), "SHIPLOOP_E2E_BASELINE": str(baseline)}
        return env, trial, candidate, baseline, family, step

    def drivers(self, *families: str) -> Path:
        path = self.root / f"drivers-{len(list(self.root.glob('drivers-*.json')))}.json"
        path.write_text(json.dumps({"schema": suite.DRIVER_REGISTRY_SCHEMA,
                                    "drivers": {family: [sys.executable, str(self.driver)] for family in families}}), encoding="utf-8")
        return path

    def relative_drivers(self, *families: str) -> tuple[Path, Path]:
        directory = self.root / f"relative-drivers-{len(list(self.root.glob('relative-drivers-*')))}"
        directory.mkdir()
        adapter = directory / "adapter.py"
        adapter.write_text(textwrap.dedent(DRIVER_SOURCE), encoding="utf-8")
        registry = directory / "drivers.json"
        registry.write_text(json.dumps({
            "schema": suite.DRIVER_REGISTRY_SCHEMA,
            "drivers": {family: [sys.executable, "adapter.py"] for family in families},
        }), encoding="utf-8")
        return registry, adapter

    def review(
        self, trial: Path, result: dict, *, classification: str = "integrated", correct_binding: bool = True,
        workspace_url: bool = False,
    ) -> Path:
        material = trial / "review-material.txt"
        material.write_text("independent source and behavior review", encoding="utf-8")
        effect = trial / "effect.txt"
        effect.write_text("independent effect review", encoding="utf-8")
        returned = trial / "return.txt"
        returned.write_text("independent return review", encoding="utf-8")
        family, step = self.scenario(result["step_id"])
        hosted_case_ids = [case["id"] for case in suite._behavior_cases(family, step)]
        self.assertTrue(hosted_case_ids)
        script_id = "script-test"
        staging_deployment_id = "staging-deployment-test"
        deployment_id = "production-deployment-test"
        version_number = 7
        web_app_url = (
            f"https://script.google.com/a/macros/example.com/s/{deployment_id}/exec"
            if workspace_url else f"https://script.google.com/macros/s/{deployment_id}/exec"
        )

        def write_artifact(name: str, payload: dict) -> tuple[Path, dict[str, str]]:
            path = trial / name
            path.write_text(json.dumps(payload), encoding="utf-8")
            return path, {"path": path.name, "sha256": sha256(path)}

        _staging, staging_ref = write_artifact("staging-receipt.json", {
            "success": True,
            "action": "deploy",
            "environment": "staging",
            "versionNumber": version_number,
            "deploymentId": staging_deployment_id,
            "stagingCandidate": {
                "scriptId": script_id,
                "versionNumber": version_number,
                "deploymentId": staging_deployment_id,
            },
        })
        _request, request_ref = write_artifact("promotion-request.json", {
            "action": "promote",
            "expectedStagingVersion": version_number,
            "expectedStagingDeploymentId": staging_deployment_id,
        })
        _promotion, promotion_ref = write_artifact("promotion-receipt.json", {
            "success": True,
            "action": "promote",
            "sourceEnv": "staging",
            "targetEnv": "prod",
            "versionNumber": version_number,
            "deploymentId": deployment_id,
            "webAppUrl": web_app_url,
        })
        _mapping, mapping_ref = write_artifact("source-mapping.json", {
            "schema": suite.SOURCE_MAPPING_SCHEMA,
            "trial_id": result["trial_id"],
            "candidate_digest": result["candidate_digest"],
            "script_id": script_id,
            "version_number": version_number,
            "deployment_id": deployment_id,
            "web_app_url": web_app_url,
            "rationale": "The retained source snapshot identifies the files deployed by this candidate.",
            "source_files": [{"path": "app.txt", "sha256": hashlib.sha256(b"candidate").hexdigest()}],
        })
        screenshot = trial / "hosted-screen.png"
        screenshot.write_bytes(b"fixture hosted browser screenshot")
        screenshot_ref = {"path": screenshot.name, "sha256": sha256(screenshot)}
        cases = [{
            "id": f"{check_id}-hosted",
            "check_id": check_id,
            "actions": [{"type": "open", "url": web_app_url}, {"type": "interact"}],
            "expected": {"check": check_id},
            "observed": {"check": check_id, "result": "observed"},
            "status": "pass",
            "screenshots": [screenshot_ref],
        } for check_id in hosted_case_ids]
        _trace, trace_ref = write_artifact("hosted-browser-trace.json", {
            "schema": suite.HOSTED_BROWSER_TRACE_SCHEMA,
            "trial_id": result["trial_id"],
            "candidate_digest": result["candidate_digest"],
            "script_id": script_id,
            "version_number": version_number,
            "deployment_id": deployment_id,
            "web_app_url": web_app_url,
            "cases": [{
                "id": case["id"],
                "status": case["status"],
                "actions": case["actions"],
                "observed": case["observed"],
            } for case in cases],
        })
        _deployment, deployment_ref = write_artifact("deployment-observation.json", {
            "schema": suite.DEPLOYMENT_OBSERVATION_SCHEMA,
            "trial_id": result["trial_id"],
            "candidate_digest": result["candidate_digest"],
            "provider": "mcp-gas-deploy",
            "script_id": script_id,
            "version_number": version_number,
            "deployment_id": deployment_id,
            "web_app_url": web_app_url,
            "published": True,
            "staging_receipt": staging_ref,
            "promotion_request": request_ref,
            "promotion_receipt": promotion_ref,
            "source_mapping": mapping_ref,
        })
        _hosted, hosted_ref = write_artifact("hosted-observation.json", {
            "schema": suite.HOSTED_OBSERVATION_SCHEMA,
            "trial_id": result["trial_id"],
            "candidate_digest": result["candidate_digest"],
            "script_id": script_id,
            "version_number": version_number,
            "deployment_id": deployment_id,
            "web_app_url": web_app_url,
            "browser_trace": trace_ref,
            "cases": cases,
        })
        record = {
            "schema": suite.REVIEW_SCHEMA,
            "step_id": result["step_id"],
            "trial_id": result["trial_id"],
            "candidate_digest": result["candidate_digest"],
            "baseline_digest": result["baseline_digest"],
            "rationale": "The reviewed application and retained evidence support this classification.",
            "review_owned_checks": [
                {"id": "authorized-deployment", "status": "pass", "observation": deployment_ref,
                 "evidence": [deployment_ref, staging_ref, request_ref, promotion_ref, mapping_ref]},
                {"id": "hosted-game-behavior", "status": "pass", "observation": hosted_ref,
                 "evidence": [hosted_ref, trace_ref, screenshot_ref]},
                {"id": "local-only-scope", "status": "pass", "evidence": [{"path": effect.name, "sha256": sha256(effect)}]},
                {"id": "run-returned-to-product", "status": "pass", "evidence": [{"path": returned.name, "sha256": sha256(returned)}]},
            ],
        }
        if result["baseline_digest"] is not None:
            record.update(classification=classification, prior_entry_reachable=classification != "replacement",
                          feature_integrated=classification != "replacement",
                          evidence=[{"path": material.name, "sha256": sha256(material)}])
        if not correct_binding:
            record["candidate_digest"] = "x" * 64
        path = trial / "review.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        return path

    def salesforce_review(
        self, trial: Path, candidate: Path, result: dict, *, gas_schema: bool = False,
        semantic_fault: str | None = None, checked_at: str = "2026-09-19T00:00:00Z",
        review_checked_at: str | None = None,
    ) -> Path:
        """Create pinned, offline Salesforce proof fixtures for one review."""
        component = candidate / "force-app" / "main" / "default" / "lwc" / "checkers" / "checkers.js"
        component.parent.mkdir(parents=True, exist_ok=True)
        component.write_text("export default class Checkers {}\n", encoding="utf-8")
        returned = trial / "salesforce-return.txt"
        returned.write_text("independent return review", encoding="utf-8")
        org_id = "00D000000000001AAA"
        instance_url = "https://fixture-dev.my.salesforce.com"
        lightning_host = "fixture-dev.lightning.force.com"
        deployment_id = "0Af000000000001AAA"

        def write_artifact(name: str, payload: dict) -> tuple[Path, dict[str, str]]:
            path = trial / name
            path.write_text(json.dumps(payload), encoding="utf-8")
            return path, {"path": path.name, "sha256": sha256(path)}

        preflight = {
            "schema": suite.SALESFORCE_TARGET_PREFLIGHT_SCHEMA,
            "status": "connected",
            "org_type": "developer",
            "expected_org_id": org_id,
            "observed_org_id": org_id,
            "expected_instance_url": instance_url,
            "observed_instance_url": instance_url,
            "expected_lightning_host": lightning_host,
            "observed_lightning_host": lightning_host,
            "my_domain": "fixture-dev",
            "is_sandbox": False,
            "checked_at": review_checked_at or checked_at,
            "product_cwd": str(candidate.resolve()),
        }
        _preflight, preflight_ref = write_artifact("salesforce-target-preflight.json", preflight)
        launch_payload = {**preflight, "checked_at": checked_at}
        launch_preflight = self.root / f"launch-{trial.name}-salesforce-preflight.json"
        launch_preflight.write_text(json.dumps(launch_payload), encoding="utf-8")
        if review_checked_at is None:
            self.assertEqual(preflight_ref["sha256"], sha256(launch_preflight))
        identity_fields = suite.SALESFORCE_PREFLIGHT_IDENTITY_FIELDS + suite.SALESFORCE_PREFLIGHT_OPTIONAL_IDENTITY_FIELDS
        trial.joinpath("manifest.json").write_text(json.dumps({
            "schema_version": 1,
            "trial_id": result["trial_id"],
            "scenario": {"id": result["step_id"]},
            "salesforce_preflight": {
                "source_path": str(launch_preflight.resolve()),
                "sha256": sha256(launch_preflight),
                "identity": {field: launch_payload[field] for field in identity_fields if field in launch_payload},
                "checked_at": checked_at,
                "product_cwd": str(candidate.resolve()),
            },
        }), encoding="utf-8")
        _raw, raw_ref = write_artifact("salesforce-raw-deploy.json", {
            "status": 0,
            "result": {
                "id": deployment_id,
                "status": "Succeeded",
                "checkOnly": False,
                "details": {"componentFailures": [], "componentSuccesses": [{
                    "componentType": "LightningComponentBundle", "fullName": "checkers", "success": True,
                }]},
            },
        })
        _mapping, mapping_ref = write_artifact("salesforce-source-mapping.json", {
            "schema": suite.SALESFORCE_SOURCE_MAPPING_SCHEMA,
            "trial_id": result["trial_id"],
            "candidate_digest": result["candidate_digest"],
            "org_id": org_id,
            "instance_url": instance_url,
            "deployment_id": deployment_id,
            "rationale": "The retained candidate source files identify the deployed Lightning component.",
            "components": [{
                "path": component.relative_to(candidate).as_posix(),
                "sha256": sha256(component),
                "kind": "lightning-web-component",
                "component_type": "LightningComponentBundle",
                "full_name": "checkers",
            }],
        })
        _receipt, receipt_ref = write_artifact("salesforce-dx-receipt.json", {
            "schema": suite.SALESFORCE_DEPLOYMENT_RECEIPT_SCHEMA,
            "provider": "salesforce-dx",
            "status": "succeeded",
            "job_id": deployment_id,
            "candidate_digest": result["candidate_digest"],
            "org_id": org_id,
            "instance_url": instance_url,
            "raw_deployment_result_sha256": raw_ref["sha256"],
            "component_mapping_sha256": mapping_ref["sha256"],
        })
        deployment_schema = suite.DEPLOYMENT_OBSERVATION_SCHEMA if gas_schema else suite.SALESFORCE_DEPLOYMENT_OBSERVATION_SCHEMA
        deployment_provider = "mcp-gas-deploy" if gas_schema else "salesforce-dx"
        _deployment, deployment_ref = write_artifact("salesforce-deployment.json", {
            "schema": deployment_schema,
            "trial_id": result["trial_id"],
            "candidate_digest": result["candidate_digest"],
            "provider": deployment_provider,
            "status": "succeeded",
            "org_id": org_id,
            "instance_url": instance_url,
            "lightning_host": lightning_host,
            "deployment_id": deployment_id,
            "target_preflight": preflight_ref,
            "raw_deployment_result": raw_ref,
            "deployment_receipt": receipt_ref,
            "source_mapping": mapping_ref,
        })
        family, step = self.scenario(result["step_id"])
        oracle_cases = suite._behavior_cases(family, step)
        screenshot = trial / "salesforce-hosted-screen.png"
        screenshot.write_bytes(b"fixture Lightning screenshot")
        screenshot_ref = {"path": screenshot.name, "sha256": sha256(screenshot)}
        cases = [{
            "id": case["id"],
            "actions": case["actions"],
            "observations": oracle._synthetic_observations(case),
            "status": "pass",
            "screenshots": [screenshot_ref],
        } for case in oracle_cases]
        if semantic_fault == "wrong-board":
            cases[0]["observations"][0]["board"] = [[None] * 8 for _ in range(8)]
        elif semantic_fault == "missing-observations":
            cases[0].pop("observations")
        elif semantic_fault is not None:
            raise ValueError(f"unsupported Salesforce semantic fault: {semantic_fault}")
        trace_cases = [{
            key: deepcopy(case[key])
            for key in ("id", "status", "actions", "observations")
            if key in case
        } for case in cases]
        _trace, trace_ref = write_artifact("salesforce-lightning-browser-trace.json", {
            "schema": suite.SALESFORCE_LIGHTNING_BROWSER_TRACE_SCHEMA,
            "trial_id": result["trial_id"],
            "candidate_digest": result["candidate_digest"],
            "org_id": org_id,
            "instance_url": instance_url,
            "deployment_id": deployment_id,
            "lightning_host": lightning_host,
            "lightning_route": f"https://{lightning_host}/lightning/n/Checkers",
            "authenticated": True,
            "cases": trace_cases,
        })
        _hosted, hosted_ref = write_artifact("salesforce-hosted-observation.json", {
            "schema": suite.SALESFORCE_HOSTED_OBSERVATION_SCHEMA,
            "trial_id": result["trial_id"],
            "candidate_digest": result["candidate_digest"],
            "org_id": org_id,
            "instance_url": instance_url,
            "deployment_id": deployment_id,
            "lightning_host": lightning_host,
            "lightning_route": f"https://{lightning_host}/lightning/n/Checkers",
            "authenticated": True,
            "browser_trace": trace_ref,
            "cases": cases,
        })
        record = {
            "schema": suite.REVIEW_SCHEMA,
            "step_id": result["step_id"],
            "trial_id": result["trial_id"],
            "candidate_digest": result["candidate_digest"],
            "baseline_digest": result["baseline_digest"],
            "rationale": "Pinned Salesforce DX and Lightning artifacts support this result.",
            "review_owned_checks": [
                {"id": "salesforce-authorized-deployment", "status": "pass", "observation": deployment_ref,
                 "evidence": [deployment_ref, preflight_ref, raw_ref, receipt_ref, mapping_ref]},
                {"id": "salesforce-hosted-lightning-behavior", "status": "pass", "observation": hosted_ref,
                 "evidence": [hosted_ref, trace_ref, screenshot_ref]},
                {"id": "salesforce-source-candidate", "status": "pass", "observation": mapping_ref,
                 "evidence": [mapping_ref]},
                {"id": "run-returned-to-product", "status": "pass",
                 "evidence": [{"path": returned.name, "sha256": sha256(returned)}]},
            ],
        }
        path = trial / "salesforce-review.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        return path

    @staticmethod
    def closure(repo: Path, evidence: Path, _mutated: set[str]) -> dict:
        path = evidence / "fixture-closure.json"
        suite._write_json(path, {"status": "pass", "repo": str(repo)})
        return {"status": "pass", "evidence": [suite._artifact(evidence, path)], "details": "fixture closure pass"}

    @staticmethod
    def row(receipt: dict, check_id: str) -> dict:
        return next(row for row in receipt["checks"] if row["id"] == check_id)

    @staticmethod
    def owned_check(record: dict, check_id: str) -> dict:
        return next(row for row in record["review_owned_checks"] if row["id"] == check_id)

    def rewrite_observation(self, review: Path, name: str, mutate) -> dict:
        """Update one pinned observation and every review-level reference to it."""
        record = json.loads(review.read_text(encoding="utf-8"))
        path = review.parent / name
        observation = json.loads(path.read_text(encoding="utf-8"))
        mutate(observation)
        path.write_text(json.dumps(observation), encoding="utf-8")
        digest = sha256(path)

        def update(value) -> None:
            if isinstance(value, dict):
                if value.get("path") == name:
                    value["sha256"] = digest
                for nested in value.values():
                    update(nested)
            elif isinstance(value, list):
                for nested in value:
                    update(nested)

        update(record)
        review.write_text(json.dumps(record), encoding="utf-8")
        return record

    def rewrite_hosted_pair(self, review: Path, mutate_observation, mutate_trace) -> dict:
        """Keep a hosted observation and retained trace internally consistent."""
        record = json.loads(review.read_text(encoding="utf-8"))
        observation_path = review.parent / "hosted-observation.json"
        trace_path = review.parent / "hosted-browser-trace.json"
        observation = json.loads(observation_path.read_text(encoding="utf-8"))
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        mutate_observation(observation)
        mutate_trace(trace)
        trace_path.write_text(json.dumps(trace), encoding="utf-8")
        observation["browser_trace"]["sha256"] = sha256(trace_path)
        observation_path.write_text(json.dumps(observation), encoding="utf-8")
        replacements = {
            trace_path.name: sha256(trace_path),
            observation_path.name: sha256(observation_path),
        }

        def update(value) -> None:
            if isinstance(value, dict):
                if value.get("path") in replacements:
                    value["sha256"] = replacements[value["path"]]
                for nested in value.values():
                    update(nested)
            elif isinstance(value, list):
                for nested in value:
                    update(nested)

        update(record)
        review.write_text(json.dumps(record), encoding="utf-8")
        return record

    def verify_ttt(self, env: dict[str, str], *, review: Path | None = None, drivers: Path | None = None) -> dict:
        with patch.object(suite, "_closure_result", self.closure):
            return suite.verify(env, drivers_path=drivers or self.drivers("tic-tac-toe"), review_path=review)

    def test_absent_feature_replays_predecessor_and_can_pass(self) -> None:
        env, trial, _candidate, _baseline, _family, step = self.fixture("ttt-guidance", candidate_mode="good", baseline_mode="guidance-absent")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        receipt = self.verify_ttt(env, review=self.review(trial, result))

        self.assertEqual(self.row(receipt, "authorized-deployment")["status"], "pass")
        self.assertEqual(self.row(receipt, "hosted-game-behavior")["status"], "pass")
        self.assertEqual(self.row(receipt, "ttt-turn-indicator-and-legal-highlights")["status"], "pass")
        self.assertEqual(self.row(receipt, "previous-behavior-preserved")["status"], "pass")
        self.assertEqual(self.row(receipt, "feature-before-absent-or-already-satisfied")["status"], "pass")
        self.assertEqual(self.row(receipt, "feature-passes-after-when-eligible")["status"], "pass")
        self.assertEqual(self.row(receipt, "incremental-integration-review")["status"], "pass")
        grade = grading.validate_receipt(receipt, trial_id=result["trial_id"], candidate_digest=result["candidate_digest"],
                                         baseline_digest=result["baseline_digest"], required_checks=step["required_checks"],
                                         evidence_root=trial / "verification")
        self.assertEqual(grade["product_status"], "passed")

    def test_workspace_published_url_is_accepted(self) -> None:
        env, trial, _candidate, _baseline, _family, _step = self.fixture("ttt-create")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))

        receipt = self.verify_ttt(env, review=self.review(trial, result, workspace_url=True))

        self.assertEqual(self.row(receipt, "authorized-deployment")["status"], "pass")
        self.assertEqual(self.row(receipt, "hosted-game-behavior")["status"], "pass")

    def test_hosted_create_keeps_its_single_base_case(self) -> None:
        env, trial, _candidate, _baseline, _family, _step = self.fixture("ttt-create")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        review = self.review(trial, result)

        receipt = self.verify_ttt(env, review=review)
        hosted = json.loads((trial / "hosted-observation.json").read_text(encoding="utf-8"))

        self.assertEqual(self.row(receipt, "hosted-game-behavior")["status"], "pass")
        self.assertEqual([case["check_id"] for case in hosted["cases"]], ["ttt-base-game"])

    def test_hosted_feature_replays_all_cumulative_oracle_cases(self) -> None:
        expected = {
            "ttt-guidance": ["ttt-base-game", "ttt-turn-indicator-and-legal-highlights"],
            "ttt-best-move": ["ttt-base-game", "ttt-turn-indicator-and-legal-highlights", "ttt-best-move-hint"],
        }
        for step_id, case_ids in expected.items():
            with self.subTest(step_id=step_id):
                env, trial, _candidate, _baseline, _family, _step = self.fixture(step_id)
                result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
                review = self.review(trial, result)

                receipt = self.verify_ttt(env, review=review)
                hosted = json.loads((trial / "hosted-observation.json").read_text(encoding="utf-8"))

                self.assertEqual(self.row(receipt, "hosted-game-behavior")["status"], "pass")
                self.assertEqual([case["check_id"] for case in hosted["cases"]], case_ids)

    def test_hosted_feature_rejects_missing_or_failing_predecessor_case(self) -> None:
        def omit_base(observation: dict) -> None:
            observation["cases"] = [case for case in observation["cases"] if case["id"] != "ttt-base-game-hosted"]

        def fail_base(observation: dict) -> None:
            for case in observation["cases"]:
                if case["id"] == "ttt-base-game-hosted":
                    case["status"] = "fail"

        for name, mutate, expected_error in (
            ("missing", omit_base, "hosted-cases-do-not-cover-scenario-checks"),
            ("failing", fail_base, "hosted-case-failure-cannot-support-pass"),
        ):
            with self.subTest(name=name):
                env, trial, _candidate, _baseline, _family, _step = self.fixture("ttt-guidance")
                result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
                review = self.review(trial, result)
                self.rewrite_hosted_pair(review, mutate, mutate)

                receipt = self.verify_ttt(env, review=review)

                row = self.row(receipt, "hosted-game-behavior")
                self.assertEqual(row["status"], "unverified")
                self.assertIn(expected_error, row["details"]["errors"])

    def test_hosted_pass_requires_cross_bound_deployment_artifacts(self) -> None:
        cases = {
            "missing-script-id": (
                "deployment-observation.json", lambda observation: observation.__setitem__("script_id", ""),
                "deployment-observation-script_id-invalid", "authorized-deployment",
            ),
            "zero-version": (
                "deployment-observation.json", lambda observation: observation.__setitem__("version_number", 0),
                "deployment-observation-version-number-invalid", "authorized-deployment",
            ),
            "missing-source-mapping": (
                "deployment-observation.json", lambda observation: observation.pop("source_mapping"),
                "source-mapping-reference-invalid", "authorized-deployment",
            ),
            "wrong-deployment-candidate": (
                "deployment-observation.json", lambda observation: observation.__setitem__("candidate_digest", "f" * 64),
                "deployment-observation-candidate_digest-mismatch", "authorized-deployment",
            ),
            "wrong-hosted-candidate": (
                "hosted-observation.json", lambda observation: observation.__setitem__("candidate_digest", "f" * 64),
                "hosted-observation-candidate_digest-mismatch", "hosted-game-behavior",
            ),
        }
        for name, (artifact, mutate, expected_error, check_id) in cases.items():
            with self.subTest(name=name):
                env, trial, _candidate, _baseline, _family, _step = self.fixture("ttt-create")
                result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
                review = self.review(trial, result)
                self.rewrite_observation(review, artifact, mutate)

                receipt = self.verify_ttt(env, review=review)

                row = self.row(receipt, check_id)
                self.assertEqual(row["status"], "unverified")
                self.assertIn(expected_error, row["details"]["errors"])

    def test_hosted_pass_rejects_local_or_dev_urls_and_plain_text_observations(self) -> None:
        for url in ("http://localhost:3000", "https://script.google.com/macros/s/production-deployment-test/dev"):
            with self.subTest(url=url):
                env, trial, _candidate, _baseline, _family, _step = self.fixture("ttt-create")
                result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
                review = self.review(trial, result)
                self.rewrite_observation(review, "hosted-observation.json", lambda observation: observation.__setitem__("web_app_url", url))

                receipt = self.verify_ttt(env, review=review)

                row = self.row(receipt, "hosted-game-behavior")
                self.assertEqual(row["status"], "unverified")
                self.assertIn("published-web-app-url-must-be-script-google-com-exec", row["details"]["errors"])

        env, trial, _candidate, _baseline, _family, _step = self.fixture("ttt-create")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        review = self.review(trial, result)
        record = json.loads(review.read_text(encoding="utf-8"))
        hosted = self.owned_check(record, "hosted-game-behavior")
        effect = self.owned_check(record, "local-only-scope")["evidence"][0]
        hosted["observation"] = dict(effect)
        hosted["evidence"].append(dict(effect))
        review.write_text(json.dumps(record), encoding="utf-8")

        receipt = self.verify_ttt(env, review=review)

        row = self.row(receipt, "hosted-game-behavior")
        self.assertEqual(row["status"], "unverified")
        self.assertIn("hosted-observation-reference-not-json", row["details"]["errors"])

    def test_hosted_identity_must_match_its_trace_and_authorized_deployment(self) -> None:
        def other_remote(record: dict) -> None:
            record.update(
                script_id="other-script",
                version_number=8,
                deployment_id="other-production-deployment",
                web_app_url="https://script.google.com/macros/s/other-production-deployment/exec",
            )

        env, trial, _candidate, _baseline, _family, _step = self.fixture("ttt-create")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        review = self.review(trial, result)
        self.rewrite_hosted_pair(review, other_remote, other_remote)

        receipt = self.verify_ttt(env, review=review)

        row = self.row(receipt, "hosted-game-behavior")
        self.assertEqual(row["status"], "unverified")
        self.assertIn("deployment-hosted-script_id-mismatch", row["details"]["errors"])

        env, trial, _candidate, _baseline, _family, _step = self.fixture("ttt-create")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        review = self.review(trial, result)
        self.rewrite_hosted_pair(
            review,
            lambda _observation: None,
            lambda trace: trace.update(
                deployment_id="trace-only-deployment",
                web_app_url="https://script.google.com/macros/s/trace-only-deployment/exec",
            ),
        )

        receipt = self.verify_ttt(env, review=review)

        row = self.row(receipt, "hosted-game-behavior")
        self.assertEqual(row["status"], "unverified")
        self.assertIn("hosted-browser-trace-deployment_id-mismatch", row["details"]["errors"])

    def test_source_mapping_hash_must_match_the_candidate_file(self) -> None:
        env, trial, candidate, _baseline, _family, _step = self.fixture("ttt-create")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        review = self.review(trial, result)
        candidate.joinpath("app.txt").write_text("changed after source mapping", encoding="utf-8")

        receipt = self.verify_ttt(env, review=review)

        row = self.row(receipt, "authorized-deployment")
        self.assertEqual(row["status"], "unverified")
        self.assertIn("source-mapping-file-digest-mismatch", row["details"]["errors"])

    def test_frozen_legacy_required_checks_remain_gradable(self) -> None:
        env, trial, _candidate, _baseline, _family, _step = self.fixture("ttt-create")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        result["required_checks"] = [
            "local-only-scope",
            "run-returned-to-product",
            "gas-compatible-local-artifact",
            "ttt-base-game",
        ]
        trial.joinpath("result.json").write_text(json.dumps(result), encoding="utf-8")

        receipt = self.verify_ttt(env, review=self.review(trial, result))
        grade = grading.validate_receipt(
            receipt, trial_id=result["trial_id"], candidate_digest=result["candidate_digest"],
            required_checks=result["required_checks"], evidence_root=trial / "verification",
        )

        self.assertEqual([row["id"] for row in receipt["checks"]], result["required_checks"])
        self.assertEqual(self.row(receipt, "local-only-scope")["status"], "pass")
        self.assertEqual(grade["product_status"], "passed")

    def test_duplicate_frozen_required_checks_are_rejected(self) -> None:
        env, trial, _candidate, _baseline, _family, _step = self.fixture("ttt-create")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        result["required_checks"] = ["ttt-base-game", "ttt-base-game"]
        trial.joinpath("result.json").write_text(json.dumps(result), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "unique nonempty strings"):
            self.verify_ttt(env)

    def test_already_satisfied_baseline_is_noncausal_not_feature_success(self) -> None:
        env, trial, _candidate, _baseline, _family, _step = self.fixture("ttt-guidance")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        receipt = self.verify_ttt(env, review=self.review(trial, result))

        self.assertEqual(receipt["composite"]["feature_delta"], "baseline-already-satisfies-feature")
        self.assertEqual(self.row(receipt, "feature-before-absent-or-already-satisfied")["status"], "pass")
        self.assertEqual(self.row(receipt, "feature-passes-after-when-eligible")["status"], "unverified")

    def test_predecessor_regression_fails_preservation(self) -> None:
        env, trial, _candidate, _baseline, _family, _step = self.fixture("ttt-guidance", candidate_mode="base-regression", baseline_mode="guidance-absent")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        receipt = self.verify_ttt(env, review=self.review(trial, result))

        self.assertEqual(self.row(receipt, "previous-behavior-preserved")["status"], "fail")

    def test_material_refactor_and_replacement_have_distinct_nonincremental_outcomes(self) -> None:
        for classification, expected in (("material-refactor", "unverified"), ("replacement", "fail")):
            with self.subTest(classification=classification):
                env, trial, _candidate, _baseline, _family, _step = self.fixture("ttt-guidance", candidate_mode="good", baseline_mode="guidance-absent")
                result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
                receipt = self.verify_ttt(env, review=self.review(trial, result, classification=classification))
                self.assertEqual(self.row(receipt, "incremental-integration-review")["status"], expected)
                self.assertEqual(receipt["incremental_review"]["status"], expected)

    def test_missing_and_stale_reviews_remain_unverified(self) -> None:
        env, trial, _candidate, _baseline, _family, _step = self.fixture("ttt-guidance", baseline_mode="guidance-absent")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        missing = self.verify_ttt(env)
        stale = self.verify_ttt(env, review=self.review(trial, result, correct_binding=False))
        for receipt in (missing, stale):
            self.assertEqual(self.row(receipt, "authorized-deployment")["status"], "unverified")
            self.assertEqual(self.row(receipt, "hosted-game-behavior")["status"], "unverified")
            self.assertEqual(self.row(receipt, "run-returned-to-product")["status"], "unverified")
            self.assertEqual(self.row(receipt, "incremental-integration-review")["status"], "unverified")

    def test_unpinned_reviewer_failure_remains_unverified(self) -> None:
        env, trial, _candidate, _baseline, _family, _step = self.fixture("ttt-guidance", baseline_mode="guidance-absent")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        review = self.review(trial, result)
        record = json.loads(review.read_text(encoding="utf-8"))
        record["review_owned_checks"][0].update(status="fail", evidence=[])
        review.write_text(json.dumps(record), encoding="utf-8")

        receipt = self.verify_ttt(env, review=review)

        self.assertEqual(self.row(receipt, "authorized-deployment")["status"], "unverified")
        self.assertIn("review-evidence-required", self.row(receipt, "authorized-deployment")["details"]["errors"])

    def test_bad_reviewer_evidence_cannot_support_incrementality(self) -> None:
        env, trial, _candidate, _baseline, _family, _step = self.fixture("ttt-guidance", baseline_mode="guidance-absent")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        review = self.review(trial, result)
        record = json.loads(review.read_text(encoding="utf-8"))
        record["evidence"][0]["sha256"] = "0" * 64
        review.write_text(json.dumps(record), encoding="utf-8")
        receipt = self.verify_ttt(env, review=review)

        self.assertEqual(self.row(receipt, "incremental-integration-review")["status"], "unverified")
        self.assertEqual(receipt["incremental_review"]["status"], "unverified")

    def test_review_nested_in_a_product_root_cannot_self_attest(self) -> None:
        env, trial, candidate, _baseline, _family, _step = self.fixture("ttt-guidance", baseline_mode="guidance-absent")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        supplied = self.review(trial, result)
        nested = candidate / "review.json"
        nested.write_bytes(supplied.read_bytes())

        receipt = self.verify_ttt(env, review=nested)

        self.assertEqual(self.row(receipt, "authorized-deployment")["status"], "unverified")
        self.assertEqual(self.row(receipt, "hosted-game-behavior")["status"], "unverified")
        self.assertEqual(self.row(receipt, "run-returned-to-product")["status"], "unverified")
        self.assertEqual(self.row(receipt, "incremental-integration-review")["status"], "unverified")
        assessment = json.loads((trial / "verification" / "review" / "assessment.json").read_text(encoding="utf-8"))
        self.assertEqual(assessment["reason"], "review-inside-product")

    def test_external_review_cannot_use_product_files_as_its_evidence(self) -> None:
        env, trial, candidate, _baseline, _family, _step = self.fixture("ttt-guidance", baseline_mode="guidance-absent")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        supplied = self.review(trial, result)
        record = json.loads(supplied.read_text(encoding="utf-8"))
        evidence_names = ("review-effect.txt", "review-return.txt", "review-material.txt")
        for name in evidence_names:
            path = candidate / name
            path.write_text(f"candidate-owned {name}", encoding="utf-8")
        record["review_owned_checks"][0]["evidence"] = [{
            "path": f"{candidate.name}/review-effect.txt", "sha256": sha256(candidate / "review-effect.txt"),
        }]
        record["review_owned_checks"][1]["evidence"] = [{
            "path": f"{candidate.name}/review-return.txt", "sha256": sha256(candidate / "review-return.txt"),
        }]
        record["evidence"] = [{
            "path": f"{candidate.name}/review-material.txt", "sha256": sha256(candidate / "review-material.txt"),
        }]
        external = self.root / f"external-{trial.name}.json"
        external.write_text(json.dumps(record), encoding="utf-8")

        receipt = self.verify_ttt(env, review=external)

        self.assertEqual(self.row(receipt, "authorized-deployment")["status"], "unverified")
        self.assertEqual(self.row(receipt, "hosted-game-behavior")["status"], "unverified")
        self.assertEqual(self.row(receipt, "run-returned-to-product")["status"], "unverified")
        self.assertEqual(self.row(receipt, "incremental-integration-review")["status"], "unverified")

    def test_missing_adapter_and_mutating_adapter_cannot_produce_a_green_trace(self) -> None:
        env, _trial, _candidate, _baseline, _family, _step = self.fixture("ttt-guidance", baseline_mode="guidance-absent")
        missing = self.verify_ttt(env, drivers=Path(self.root / "does-not-exist.json"))
        self.assertEqual(self.row(missing, "ttt-turn-indicator-and-legal-highlights")["status"], "unverified")

        env, _trial, candidate, _baseline, _family, _step = self.fixture("ttt-guidance", candidate_mode="mutate", baseline_mode="guidance-absent")
        mutated = self.verify_ttt(env)
        self.assertTrue((candidate / "driver-wrote.txt").is_file())
        self.assertEqual(self.row(mutated, "ttt-turn-indicator-and-legal-highlights")["status"], "unverified")
        self.assertTrue(mutated["composite"]["source_drift"])

    def test_relative_adapter_path_is_pinned_to_the_driver_registry(self) -> None:
        env, trial, candidate, _baseline, _family, _step = self.fixture("ttt-guidance", baseline_mode="guidance-absent")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        candidate.joinpath("adapter.py").write_text(
            "from pathlib import Path\nPath('candidate-adapter-ran').write_text('wrong adapter')\n",
            encoding="utf-8",
        )
        drivers, trusted_adapter = self.relative_drivers("tic-tac-toe")

        receipt = self.verify_ttt(env, drivers=drivers, review=self.review(trial, result))

        self.assertFalse((candidate / "candidate-adapter-ran").exists())
        self.assertEqual(self.row(receipt, "ttt-turn-indicator-and-legal-highlights")["status"], "pass")
        adapter_rows = receipt["verifier_inputs"]["adapters"]
        paths = [item["path"] for item in adapter_rows[0]["files"] if item["status"] == "present"]
        self.assertIn(str(trusted_adapter.resolve()), paths)

    def test_verifier_input_drift_invalidates_executable_passes(self) -> None:
        env, trial, _candidate, _baseline, _family, _step = self.fixture("ttt-guidance", baseline_mode="guidance-absent")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        inputs = [{"aggregate_sha256": "a" * 64}, {"aggregate_sha256": "b" * 64}]
        with patch.object(suite, "_closure_result", self.closure), patch.object(suite, "verifier_inputs_manifest", side_effect=inputs):
            receipt = suite.verify(env, drivers_path=self.drivers("tic-tac-toe"), review_path=self.review(trial, result))

        self.assertTrue(receipt["composite"]["verifier_input_drift"])
        self.assertEqual(receipt["verifier_inputs_sha256"], "a" * 64)
        self.assertEqual(self.row(receipt, "ttt-turn-indicator-and-legal-highlights")["status"], "unverified")

    def test_catalog_routes_all_ten_cases_through_family_adapters(self) -> None:
        catalog = json.loads((HERE / "scenarios.json").read_text(encoding="utf-8"))

        def fake_cases(family: dict, step: dict) -> list[dict]:
            steps = family["steps"]
            position = next(index for index, value in enumerate(steps) if value["id"] == step["id"])
            return [{"id": f"oracle-{value['id']}", "game": family.get("oracle_family", family["id"]), "step_id": value["id"],
                     "level": value["kind"], "actions": [{"type": "probe"}]}
                    for value in steps[:position + 1]]

        def fake_evaluate(_case: dict, observations: list[dict]) -> list[dict]:
            if len(observations) != 1:
                raise ValueError("incomplete")
            return [] if observations[0].get("semantic") == "pass" else [{"reason": "fixture"}]

        with patch.object(suite, "_behavior_cases", fake_cases), patch.object(suite, "_evaluate_behavior", fake_evaluate), patch.object(suite, "_closure_result", self.closure):
            drivers = self.drivers("tic-tac-toe", "checkers", "salesforce-checkers", "battleship")
            for family in catalog["scenarios"]:
                for step in family["steps"]:
                    with self.subTest(step=step["id"]):
                        env, _trial, _candidate, _baseline, _ignored_family, _ignored_step = self.fixture(step["id"])
                        receipt = suite.verify(env, drivers_path=drivers)
                        semantic = [row for row in receipt["checks"] if row["id"] not in suite.NON_SEMANTIC_CHECKS]
                        self.assertEqual(len(semantic), 1)
                        self.assertEqual(semantic[0]["status"], "pass")
                        if family.get("platform") == "salesforce-lightning":
                            self.assertNotIn("gas-compatible-local-artifact", step["required_checks"])
                            self.assertEqual(self.row(receipt, "salesforce-authorized-deployment")["status"], "unverified")
                        else:
                            self.assertEqual(self.row(receipt, "gas-compatible-local-artifact")["status"], "pass")

    def test_salesforce_review_requires_bound_platform_proof_and_rejects_gas_schema(self) -> None:
        env, trial, candidate, _baseline, _family, _step = self.fixture("salesforce-checkers-create")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        review = self.salesforce_review(trial, candidate, result)
        with patch.object(suite, "_closure_result", self.closure):
            receipt = suite.verify(env, review_path=review)
        for check_id in (
            "salesforce-authorized-deployment",
            "salesforce-hosted-lightning-behavior",
            "salesforce-source-candidate",
            "run-returned-to-product",
        ):
            self.assertEqual("pass", self.row(receipt, check_id)["status"])

        env, trial, candidate, _baseline, _family, _step = self.fixture("salesforce-checkers-create")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        gas_review = self.salesforce_review(trial, candidate, result, gas_schema=True)
        with patch.object(suite, "_closure_result", self.closure):
            gas_receipt = suite.verify(env, review_path=gas_review)
        self.assertEqual("unverified", self.row(gas_receipt, "salesforce-authorized-deployment")["status"])

        env, trial, candidate, _baseline, _family, _step = self.fixture("salesforce-checkers-create")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        incomplete_review = self.salesforce_review(trial, candidate, result)
        self.rewrite_observation(incomplete_review, "salesforce-deployment.json", lambda value: value.pop("raw_deployment_result"))
        with patch.object(suite, "_closure_result", self.closure):
            incomplete_receipt = suite.verify(env, review_path=incomplete_review)
        self.assertEqual("unverified", self.row(incomplete_receipt, "salesforce-authorized-deployment")["status"])

        env, _trial, _candidate, _baseline, _family, _step = self.fixture("salesforce-checkers-create")
        with patch.object(suite, "_closure_result", self.closure):
            missing_receipt = suite.verify(env)
        self.assertEqual("unverified", self.row(missing_receipt, "salesforce-authorized-deployment")["status"])
        self.assertEqual("unverified", self.row(missing_receipt, "salesforce-hosted-lightning-behavior")["status"])

    def test_salesforce_deployment_requires_the_launch_pinned_preflight(self) -> None:
        env, trial, candidate, _baseline, _family, _step = self.fixture("salesforce-checkers-create")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        missing_pin_review = self.salesforce_review(trial, candidate, result)
        manifest_path = trial / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.pop("salesforce_preflight")
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with patch.object(suite, "_closure_result", self.closure):
            missing_pin_receipt = suite.verify(env, review_path=missing_pin_review)
        missing_pin_row = self.row(missing_pin_receipt, "salesforce-authorized-deployment")
        self.assertEqual("unverified", missing_pin_row["status"])
        self.assertIn("salesforce-launch-manifest-preflight-missing", missing_pin_row["details"]["errors"])

        env, trial, candidate, _baseline, _family, _step = self.fixture("salesforce-checkers-create")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        replaced_preflight_review = self.salesforce_review(
            trial, candidate, result, review_checked_at="2026-09-19T00:01:00Z",
        )
        with patch.object(suite, "_closure_result", self.closure):
            replaced_preflight_receipt = suite.verify(env, review_path=replaced_preflight_review)
        replaced_preflight_row = self.row(replaced_preflight_receipt, "salesforce-authorized-deployment")
        self.assertEqual("unverified", replaced_preflight_row["status"])
        self.assertIn(
            "salesforce-launch-manifest-preflight-sha256-mismatch",
            replaced_preflight_row["details"]["errors"],
        )

        env, trial, candidate, _baseline, _family, _step = self.fixture("salesforce-checkers-create")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        old_but_pinned_review = self.salesforce_review(
            trial, candidate, result, checked_at="2000-01-01T00:00:00Z",
        )
        with patch.object(suite, "_closure_result", self.closure):
            old_but_pinned_receipt = suite.verify(env, review_path=old_but_pinned_review)
        self.assertEqual(
            "pass",
            self.row(old_but_pinned_receipt, "salesforce-authorized-deployment")["status"],
        )

    def test_salesforce_hosted_proof_requires_canonical_oracle_observations(self) -> None:
        for fault, expected_error in (
            ("wrong-board", "salesforce-hosted-case-oracle-failure"),
            ("missing-observations", "salesforce-hosted-case-observations-invalid"),
        ):
            with self.subTest(fault=fault):
                env, trial, candidate, _baseline, _family, _step = self.fixture("salesforce-checkers-create")
                result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
                review = self.salesforce_review(trial, candidate, result, semantic_fault=fault)
                with patch.object(suite, "_closure_result", self.closure):
                    receipt = suite.verify(env, review_path=review)
                row = self.row(receipt, "salesforce-hosted-lightning-behavior")
                self.assertEqual("unverified", row["status"])
                self.assertIn(expected_error, row["details"]["errors"])

    def test_checkers_variant_drift_fails_predecessor_preservation(self) -> None:
        family, step = self.scenario("checkers-guidance")
        evidence = self.root / "variant-evidence"
        evidence.mkdir()
        context = {"family": family, "step": step, "evidence": evidence,
                   "result": {"baseline_digest": "b" * 64}}
        base = {"id": "base", "game": "checkers", "step_id": "checkers-create", "level": "base", "actions": []}
        current = {"id": "current", "game": "checkers", "step_id": "checkers-guidance", "level": "guidance", "actions": []}
        def passed(variant: str) -> dict:
            return {"status": "pass", "evidence": [], "details": "pass",
                    "trace": {"observations": [{"variant": {"capture_priority": variant}}]}}
        matrix = {("base", "before"): passed("any"), ("base", "after"): passed("maximum"),
                  ("current", "before"): passed("any"), ("current", "after"): passed("maximum")}
        rows, _meta = suite._replay_rows(context, [base, current], matrix)
        self.assertEqual(rows["previous-behavior-preserved"]["status"], "fail")


if __name__ == "__main__":
    unittest.main()
