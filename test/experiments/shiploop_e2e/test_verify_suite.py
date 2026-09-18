#!/usr/bin/env python3
"""No-model adversarial checks for the composite nine-case verifier."""
from __future__ import annotations

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

    def review(self, trial: Path, result: dict, *, classification: str = "integrated", correct_binding: bool = True) -> Path:
        material = trial / "review-material.txt"
        material.write_text("independent source and behavior review", encoding="utf-8")
        effect = trial / "effect.txt"
        effect.write_text("independent effect review", encoding="utf-8")
        returned = trial / "return.txt"
        returned.write_text("independent return review", encoding="utf-8")
        record = {
            "schema": suite.REVIEW_SCHEMA,
            "step_id": result["step_id"],
            "trial_id": result["trial_id"],
            "candidate_digest": result["candidate_digest"],
            "baseline_digest": result["baseline_digest"],
            "rationale": "The reviewed application and retained evidence support this classification.",
            "review_owned_checks": [
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

    @staticmethod
    def closure(repo: Path, evidence: Path, _mutated: set[str]) -> dict:
        path = evidence / "fixture-closure.json"
        suite._write_json(path, {"status": "pass", "repo": str(repo)})
        return {"status": "pass", "evidence": [suite._artifact(evidence, path)], "details": "fixture closure pass"}

    @staticmethod
    def row(receipt: dict, check_id: str) -> dict:
        return next(row for row in receipt["checks"] if row["id"] == check_id)

    def verify_ttt(self, env: dict[str, str], *, review: Path | None = None, drivers: Path | None = None) -> dict:
        with patch.object(suite, "_closure_result", self.closure):
            return suite.verify(env, drivers_path=drivers or self.drivers("tic-tac-toe"), review_path=review)

    def test_absent_feature_replays_predecessor_and_can_pass(self) -> None:
        env, trial, _candidate, _baseline, _family, step = self.fixture("ttt-guidance", candidate_mode="good", baseline_mode="guidance-absent")
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        receipt = self.verify_ttt(env, review=self.review(trial, result))

        self.assertEqual(self.row(receipt, "ttt-turn-indicator-and-legal-highlights")["status"], "pass")
        self.assertEqual(self.row(receipt, "previous-behavior-preserved")["status"], "pass")
        self.assertEqual(self.row(receipt, "feature-before-absent-or-already-satisfied")["status"], "pass")
        self.assertEqual(self.row(receipt, "feature-passes-after-when-eligible")["status"], "pass")
        self.assertEqual(self.row(receipt, "incremental-integration-review")["status"], "pass")
        grade = grading.validate_receipt(receipt, trial_id=result["trial_id"], candidate_digest=result["candidate_digest"],
                                         baseline_digest=result["baseline_digest"], required_checks=step["required_checks"],
                                         evidence_root=trial / "verification")
        self.assertEqual(grade["product_status"], "passed")

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
            self.assertEqual(self.row(receipt, "local-only-scope")["status"], "unverified")
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

        self.assertEqual(self.row(receipt, "local-only-scope")["status"], "unverified")
        self.assertIn("review-evidence-required", self.row(receipt, "local-only-scope")["details"]["errors"])

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

        self.assertEqual(self.row(receipt, "local-only-scope")["status"], "unverified")
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

        self.assertEqual(self.row(receipt, "local-only-scope")["status"], "unverified")
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

    def test_catalog_routes_all_nine_cases_through_family_adapters(self) -> None:
        catalog = json.loads((HERE / "scenarios.json").read_text(encoding="utf-8"))

        def fake_cases(family: dict, step: dict) -> list[dict]:
            steps = family["steps"]
            position = next(index for index, value in enumerate(steps) if value["id"] == step["id"])
            return [{"id": f"oracle-{value['id']}", "game": family["id"], "step_id": value["id"],
                     "level": value["kind"], "actions": [{"type": "probe"}]}
                    for value in steps[:position + 1]]

        def fake_evaluate(_case: dict, observations: list[dict]) -> list[dict]:
            if len(observations) != 1:
                raise ValueError("incomplete")
            return [] if observations[0].get("semantic") == "pass" else [{"reason": "fixture"}]

        with patch.object(suite, "_behavior_cases", fake_cases), patch.object(suite, "_evaluate_behavior", fake_evaluate), patch.object(suite, "_closure_result", self.closure):
            drivers = self.drivers("tic-tac-toe", "checkers", "battleship")
            for family in catalog["scenarios"]:
                for step in family["steps"]:
                    with self.subTest(step=step["id"]):
                        env, _trial, _candidate, _baseline, _ignored_family, _ignored_step = self.fixture(step["id"])
                        receipt = suite.verify(env, drivers_path=drivers)
                        semantic = [row for row in receipt["checks"] if row["id"] not in suite.NON_SEMANTIC_CHECKS]
                        self.assertEqual(len(semantic), 1)
                        self.assertEqual(semantic[0]["status"], "pass")
                        self.assertEqual(self.row(receipt, "gas-compatible-local-artifact")["status"], "pass")

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
