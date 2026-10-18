#!/usr/bin/env python3
"""Offline acceptance-check sensitivity and actual Until Loop lifecycle controls.

Authored plans and runtime reports here are apparatus fixtures, not live model
evidence. Live native subjects run through run-integration.sh backchain-chunks.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import backchain_chunks as chunks


class PreservationCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="backchain-preservation-cli-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.baseline_path = self.root / "baseline.json"
        self.candidate_path = self.root / "candidate.json"
        self.receipt_path = self.root / "comparison.json"

    def one_step(self, produce="Original response is emitted."):
        return {"goal_needs": [produce], "steps": [{"id": "S1", "produces": [produce],
                "confirm": [{"produces": produce,
                             "by": "Inspect the response; pass when it is emitted.",
                             "level": "execute"}]}]}

    def execute(self, baseline=None, candidate=None, mode="legacy", baseline_bytes=None,
                candidate_bytes=None, baseline_sha=None, verify=None, extra=()):
        if baseline_bytes is not None:
            self.baseline_path.write_bytes(baseline_bytes)
        else:
            chunks.write(self.baseline_path, baseline if baseline is not None else self.one_step())
        if candidate_bytes is not None:
            self.candidate_path.write_bytes(candidate_bytes)
        else:
            candidate_value = (candidate if candidate is not None else
                               baseline if baseline is not None else self.one_step())
            chunks.write(self.candidate_path, candidate_value)
        argv = [sys.executable, "-I", "-B", str(chunks.PRESERVATION),
                "--baseline", str(self.baseline_path), "--baseline-sha256",
                baseline_sha or chunks.digest(self.baseline_path), "--candidate", str(self.candidate_path),
                "--mode", mode]
        if verify is not None:
            argv += ["--verify-receipt", str(verify)]
        argv += list(extra)
        return subprocess.run(argv, capture_output=True, text=True, check=False)

    def receipt(self, result):
        self.assertTrue(result.stdout, result.stderr)
        return json.loads(result.stdout)

    def test_cli_usage_codes_and_bad_json_are_distinct(self):
        helper = str(chunks.PRESERVATION)
        help_result = subprocess.run([sys.executable, "-I", "-B", helper, "--help"],
                                     capture_output=True, text=True, check=False)
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("--baseline-sha256", help_result.stdout)
        missing_args = subprocess.run([sys.executable, "-I", "-B", helper],
                                       capture_output=True, text=True, check=False)
        self.assertEqual(missing_args.returncode, 3)
        invalid_mode = self.execute(mode="invalid")
        self.assertEqual(invalid_mode.returncode, 3)

        missing_candidate = subprocess.run(
            [sys.executable, "-I", "-B", helper,
             "--baseline", str(self.baseline_path),
             "--baseline-sha256", chunks.digest(self.baseline_path),
             "--candidate", str(self.root / "missing.json"), "--mode", "legacy"],
            capture_output=True, text=True, check=False)
        self.assertEqual(missing_candidate.returncode, 3)
        for malformed in (b'{"steps": [], "steps": []}', b'{"steps": [], "n": NaN}'):
            with self.subTest(malformed=malformed):
                result = self.execute(candidate_bytes=malformed)
                self.assertEqual(result.returncode, 3)

    def test_frozen_baseline_hash_mismatch_is_exit_two(self):
        result = self.execute(baseline_sha="0" * 64)
        self.assertEqual(result.returncode, 2)
        self.assertIn("baseline SHA-256 mismatch", result.stderr)

    def test_goal_needs_drop_reorder_empty_and_absence_are_distinct(self):
        baseline = {"goal_needs": ["first", "second"], "steps": []}
        for mutation in ("drop", "reorder", "empty"):
            candidate = copy.deepcopy(baseline)
            if mutation == "drop":
                del candidate["goal_needs"]
            elif mutation == "reorder":
                candidate["goal_needs"].reverse()
            else:
                candidate["goal_needs"] = []
            with self.subTest(mutation=mutation):
                result = self.execute(baseline=baseline, candidate=candidate)
                self.assertEqual(result.returncode, 1)
                self.assertIn("goal_needs presence/value changed", self.receipt(result)["errors"])

        absent = copy.deepcopy(baseline)
        del absent["goal_needs"]
        same_absent = copy.deepcopy(absent)
        result = self.execute(baseline=absent, candidate=same_absent)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.receipt(result)["goal_needs_preserved"])
        empty = copy.deepcopy(absent)
        empty["goal_needs"] = []
        result = self.execute(baseline=absent, candidate=empty)
        self.assertEqual(result.returncode, 1)
        self.assertIn("goal_needs presence/value changed", self.receipt(result)["errors"])

    def test_legacy_requires_exact_unchanged_produce_confirmation_object(self):
        baseline = self.one_step()
        candidate = copy.deepcopy(baseline)
        candidate["steps"][0]["confirm"][0]["by"] = "A paraphrase of the old check."
        result = self.execute(baseline=baseline, candidate=candidate, mode="legacy")
        self.assertEqual(result.returncode, 1)
        receipt = self.receipt(result)
        self.assertIn("unchanged produce confirmation changed: S1.confirm[0]", receipt["errors"])
        result = self.execute(baseline=baseline, candidate=baseline, mode="legacy")
        self.assertEqual(result.returncode, 0)

    def test_in_place_produce_rewrite_is_report_only_in_both_modes_and_new_confirms_are_reported(self):
        baseline = self.one_step("Original response is emitted.")
        del baseline["goal_needs"]
        rewritten = copy.deepcopy(baseline)
        step = rewritten["steps"][0]
        step["produces"] = ["Original response is emitted with compatibility."]
        step["confirm"] = [{"produces": step["produces"][0],
                            "by": "Run compatibility checks; pass when original and compatibility responses emit.",
                            "level": "execute"}]
        for mode in ("legacy", "source-aware"):
            with self.subTest(mode=mode):
                result = self.execute(baseline=baseline, candidate=rewritten, mode=mode)
                self.assertEqual(result.returncode, 0)
                receipt = self.receipt(result)
                self.assertTrue(receipt["invariants_passed"])
                self.assertIn("produce_text_absent", [d["kind"] for d in receipt["confirmation_differences"]])
                self.assertIn("added", [d["kind"] for d in receipt["confirmation_differences"]])

        added = copy.deepcopy(baseline)
        added["steps"][0]["produces"].append("A compatibility diagnostic is emitted.")
        added["steps"][0]["confirm"].append({
            "produces": "A compatibility diagnostic is emitted.",
            "by": "Run diagnostics; pass when the compatibility diagnostic is emitted.", "level": "execute"})
        result = self.execute(baseline=baseline, candidate=added, mode="source-aware")
        self.assertEqual(result.returncode, 0)
        self.assertIn("added", [d["kind"] for d in self.receipt(result)["confirmation_differences"]])

    def test_exact_confirmation_move_and_cross_owner_produces_are_reported(self):
        baseline = {"steps": [
            {"id": "S1", "produces": ["P"], "confirm": [
                {"produces": "P", "by": "Inspect P; pass when present.", "level": "inspect"}]},
            {"id": "S2", "produces": ["Q"], "confirm": [
                {"produces": "Q", "by": "Inspect Q; pass when present.", "level": "inspect"}]},
        ]}
        moved = copy.deepcopy(baseline)
        moved["steps"][0]["produces"] = []
        moved["steps"][0]["confirm"] = []
        moved["steps"][1]["produces"].append("P")
        moved["steps"][1]["confirm"].append(copy.deepcopy(baseline["steps"][0]["confirm"][0]))
        result = self.execute(baseline=baseline, candidate=moved, mode="source-aware")
        self.assertEqual(result.returncode, 0)
        receipt = self.receipt(result)
        move = next(d for d in receipt["confirmation_differences"] if d["kind"] == "moved_unchanged")
        self.assertEqual(move["after"][0]["step_id"], "S2")

        duplicate = copy.deepcopy(baseline)
        duplicate["steps"][1]["produces"].append("P")
        result = self.execute(baseline=baseline, candidate=duplicate, mode="source-aware")
        self.assertEqual(result.returncode, 0)
        receipt = self.receipt(result)
        self.assertIn({"plan": "candidate", "produces": "P", "step_ids": ["S1", "S2"]},
                      receipt["multi_owner_produces"])

    def test_stale_confirmation_is_not_retained_when_its_produce_owner_changes(self):
        baseline = self.one_step("P")
        candidate = copy.deepcopy(baseline)
        candidate["steps"][0]["produces"] = ["Q"]
        # A stale confirmation remains in S1, but S1 no longer owns P.
        for mode in ("legacy", "source-aware"):
            with self.subTest(mode=mode):
                result = self.execute(baseline=baseline, candidate=candidate, mode=mode)
                self.assertEqual(result.returncode, 0)
                receipt = self.receipt(result)
                self.assertTrue(receipt["invariants_passed"])
                self.assertIn("produce_text_absent", [d["kind"] for d in receipt["confirmation_differences"]])

        baseline_two = {"steps": [baseline["steps"][0], {
            "id": "S2", "produces": ["Q"], "confirm": [
                {"produces": "Q", "by": "Inspect Q; pass when present.", "level": "inspect"}]}]}
        moved_with_stale = {"steps": [
            {"id": "S1", "produces": ["Q"], "confirm": [copy.deepcopy(baseline["steps"][0]["confirm"][0])]},
            {"id": "S2", "produces": ["Q", "P"], "confirm": [
                {"produces": "Q", "by": "Inspect Q; pass when present.", "level": "inspect"},
                copy.deepcopy(baseline["steps"][0]["confirm"][0])]},
        ]}
        result = self.execute(baseline=baseline_two, candidate=moved_with_stale, mode="source-aware")
        self.assertEqual(result.returncode, 0)
        receipt = self.receipt(result)
        moved = next(d for d in receipt["confirmation_differences"] if d["kind"] == "moved_unchanged")
        self.assertEqual(moved["after"][0]["step_id"], "S2")
        stale_additions = [d for d in receipt["confirmation_differences"]
                           if d["kind"] == "added" and d["after"][0]["step_id"] == "S1"]
        self.assertTrue(stale_additions)

    def test_mixed_oracle_reports_three_changed_confirms_and_verbatim_moves(self):
        case = chunks.fixtures()["mixed"]
        candidate = split_plan(case)
        result = self.execute(baseline=case["plan"], candidate=candidate, mode="source-aware")
        self.assertEqual(result.returncode, 0)
        receipt = self.receipt(result)
        kinds = [d["kind"] for d in receipt["confirmation_differences"]]
        self.assertEqual(kinds.count("unchanged_produce_confirmation_changed"), 3)
        self.assertEqual(kinds.count("moved_unchanged"), 1)

        s2 = next(s for s in candidate["steps"] if s["id"] == "S2")
        s2["confirm"][0]["by"] = "A paraphrase of the inherited S2 check."
        result = self.execute(baseline=case["plan"], candidate=candidate, mode="source-aware")
        self.assertEqual(result.returncode, 0)
        changed = [d for d in self.receipt(result)["confirmation_differences"]
                   if d["kind"] == "unchanged_produce_confirmation_changed"]
        self.assertTrue(any(d["before"]["step_id"] == "S2" for d in changed))

    def test_preserved_labels_do_not_authorize_recasting_a_legacy_seed_as_a_join(self):
        case = chunks.fixtures()["legacy-edge-free"]
        raw = copy.deepcopy(case["plan"])
        seed = raw["steps"][0]
        seed["statement"] = "The response schema and cache purge results are verified together."
        for sid, produce, check in (
            ("D1", "The response schema lists id and label as strings.",
             "Inspect the schema; pass when id and label are strings."),
            ("D2", "The cache purge operation removes expired entries.",
             "Run cache-purge tests; pass when expired entries are removed."),
        ):
            seed["inputs"].append({"from": sid, "need": produce})
            raw["steps"].append({"id": sid, "statement": produce, "produces": [produce],
                "inputs": [{"from": None, "need": raw["initial_state"][0]}], "origin": "discovered",
                "confirm": [{"produces": produce, "by": check, "level": "execute"}]})
        # The helper preserves goals and confirmation objects, not semantic work
        # ownership. The fixed fixture authority check must still reject this.
        result = self.execute(baseline=case["plan"], candidate=raw, mode="legacy")
        self.assertEqual(result.returncode, 0, result.stderr)
        packaged = chunks.graph.package(raw)
        self.assertTrue(chunks.graph.validate_structure(packaged)["ok"])
        self.assertIn("candidate changed outside the blocked route's monotonic widening boundary",
                      chunks.check_plan(case, packaged, raw))

    def test_receipt_binds_candidate_bytes_and_detects_candidate_or_receipt_tampering(self):
        baseline = self.one_step()
        candidate = copy.deepcopy(baseline)
        first = self.execute(baseline=baseline, candidate=candidate)
        self.assertEqual(first.returncode, 0)
        receipt = self.receipt(first)
        self.assertEqual(receipt["candidate_sha256"], chunks.digest(self.candidate_path))
        self.receipt_path.write_text(first.stdout)
        verified = self.execute(baseline=baseline, candidate=candidate, verify=self.receipt_path)
        self.assertEqual(verified.returncode, 0)

        changed_bytes = self.candidate_path.read_bytes() + b" "
        stale_candidate = self.execute(baseline=baseline, candidate_bytes=changed_bytes,
                                       verify=self.receipt_path)
        self.assertEqual(stale_candidate.returncode, 1)
        self.assertIn("receipt is stale or changed", stale_candidate.stderr)

        chunks.write(self.candidate_path, candidate)
        receipt["candidate_sha256"] = "0" * 64
        chunks.write(self.receipt_path, receipt)
        tampered_receipt = self.execute(baseline=baseline, candidate=candidate, verify=self.receipt_path)
        self.assertEqual(tampered_receipt.returncode, 1)
        self.assertIn("receipt is stale or changed", tampered_receipt.stderr)


def split_plan(case):
    """Independent useful-deliverable oracle for this fixed CSV fixture."""
    plan = copy.deepcopy(case["plan"])
    original = plan["steps"][0]
    conditions = original["produces"]
    roles = [
        ("S1", conditions[0], original["inputs"], "Inspect record fields; pass when id and label are strings."),
        ("D1", conditions[1], [{"from": "S1", "need": conditions[0]}],
         "Run reader fixtures; pass when records have id/label and missing ids are rejected."),
        ("D2", conditions[2], [{"from": "S1", "need": conditions[0]}],
         "Run renderer fixtures; pass when record ids and labels appear without file access."),
        ("D3", conditions[3], [{"from": "D1", "need": conditions[1]},
                               {"from": "D2", "need": conditions[2]}], original["confirm"][3]["by"]),
    ]
    plan["steps"] = [{"id": sid, "statement": condition, "produces": [condition],
                      "inputs": inputs, "origin": "seed" if sid == "S1" else "discovered",
                      "confirm": [{"produces": condition, "by": check, "level": "execute"}]}
                     for sid, condition, inputs, check in roles] + plan["steps"][1:]
    plan["steps"][-2]["inputs"][0]["from"] = "D3"
    plan["parallel_groups"] = []
    return plan


class PlanRegressionTests(unittest.TestCase):
    def setUp(self):
        self.cases = chunks.fixtures()
        self.case = self.cases["mixed"]

    def check(self, raw):
        return chunks.check_plan(self.case, chunks.graph.package(raw), raw)

    def test_cases_cover_all_six_eval_entries_with_concrete_valid_inputs(self):
        catalog = chunks.read(chunks.SKILL / "evals/evals.json")
        evals = catalog["evals"] if isinstance(catalog, dict) else catalog
        ids = {e["id"] for e in evals}
        self.assertEqual({c["eval_id"] for c in self.cases.values()}, set(range(17, 23)))
        self.assertTrue(set(range(17, 23)) <= ids)
        self.assertEqual(len(self.cases), 7)  # eval 22 has two distinct authority routes
        for case in self.cases.values():
            with self.subTest(case=case["id"]):
                self.assertTrue(chunks.graph.validate_structure(case["plan"])["ok"])
                self.assertEqual(chunks.graph.completion_status(case["plan"])["status"], "complete")
                self.assertTrue(case["source"])

    def test_valid_mixed_split_preserves_real_branches(self):
        self.assertEqual(self.check(split_plan(self.case)), [])

    def test_meaningful_integration_can_own_whole_feature_verification(self):
        raw = split_plan(self.case)
        wiring, e2e = raw["steps"][3:5]
        wiring["produces"] += e2e["produces"]
        wiring["confirm"] += e2e["confirm"]
        raw["steps"].remove(e2e)
        self.assertEqual(self.check(raw), [])

    def test_rejects_observed_goal_loss_and_unauthorized_confirmation_rewrite(self):
        raw = split_plan(self.case)
        del raw["goal_needs"]
        self.assertIn("goal_needs presence/value changed", self.check(raw))
        raw = split_plan(self.case)
        raw["steps"][-2]["confirm"][0]["by"] = "A paraphrase of the old check."
        self.assertIn("unauthorized S2 confirmation change", self.check(raw))

    def test_rejects_reordered_goals_duplicate_owner_missing_confirmation_and_false_serialization(self):
        for mutation, message in (
            (lambda p: p["goal_needs"].reverse(), "goal_needs presence/value changed"),
            (lambda p: p["steps"][1]["produces"].append(p["steps"][2]["produces"][0]),
             "lost/duplicated original produce owner"),
            (lambda p: p["steps"][1].update(confirm=[]), "D1 lacks usable exact confirmations"),
            (lambda p: p["steps"][2]["inputs"].append({"from": "D1", "need": p["steps"][1]["produces"][0]}),
             "renderer must consume only record contract"),
            (lambda p: p["steps"][1]["confirm"][0].update(by="Run import-e2e; pass when all cases pass."),
             "D1 confirmation waits for downstream whole-feature implementation"),
            (lambda p: p.update(parallel_groups=[["S1"]]), "revision retained stale parallel_groups"),
        ):
            with self.subTest(message=message):
                raw = split_plan(self.case)
                mutation(raw)
                self.assertIn(message, self.check(raw))

    def test_rejects_unsplit_and_dummy_join(self):
        self.assertIn("independent implementation deliverables remain bundled", self.check(self.case["plan"]))
        raw = split_plan(self.case)
        raw["steps"][3]["produces"].append("Both workers finished.")
        self.assertIn("extra wrapper, duplicate work, or unrequested produce", self.check(raw))

    def test_keep_cases_allow_only_source_grounded_initial_fact_edges(self):
        for key in ("cohesive", "outscope"):
            case = self.cases[key]
            with self.subTest(case=key):
                raw = copy.deepcopy(case["plan"])
                provisional = next(s for s in raw["steps"] if s["id"] == "S4")
                provisional["inputs"].append({"from": None, "need": raw["initial_state"][0]})
                self.assertEqual(chunks.check_plan(case, raw, raw), [])
                provisional["inputs"].reverse()
                self.assertEqual(chunks.check_plan(case, raw, raw), [])
                for field in ("allow_new_edges", "provisional_step_ids"):
                    denied = copy.deepcopy(case)
                    denied["edit_bounds"][field] = False if field == "allow_new_edges" else []
                    self.assertTrue(chunks.check_plan(denied, raw, raw))

    def test_keep_cases_reject_unproven_edges_and_any_other_work_change(self):
        case = self.cases["cohesive"]
        raw = copy.deepcopy(case["plan"])
        next(s for s in raw["steps"] if s["id"] == "S3")["inputs"].append(
            {"from": None, "need": "The request authorizes a new background service."})
        self.assertTrue(chunks.check_plan(case, raw, raw))

        raw = copy.deepcopy(self.cases["outscope"]["plan"])
        next(s for s in raw["steps"] if s["id"] == "S2")["inputs"].append(
            {"from": None, "need": raw["initial_state"][0]})
        self.assertTrue(chunks.check_plan(self.cases["outscope"], raw, raw))

        raw = copy.deepcopy(case["plan"])
        next(s for s in raw["steps"] if s["id"] == "S3")["inputs"].append(
            {"from": "S2", "need": case["plan"]["steps"][1]["produces"][0]})
        self.assertTrue(chunks.check_plan(case, raw, raw))

        raw = copy.deepcopy(case["plan"])
        raw["steps"][0]["statement"] += " Changed."
        self.assertTrue(chunks.check_plan(case, raw, raw))

    def test_legacy_blocked_cases_accept_only_monotonic_seed_widening(self):
        for key in ("legacy", "legacy-edge-free"):
            case = self.cases[key]
            with self.subTest(case=key):
                self.assertEqual(chunks.check_plan(case, case["plan"], case["plan"]), [])
                widened = copy.deepcopy(case["plan"])
                quote = "The response schema lists id and label as strings."
                step = widened["steps"][0]
                step["statement"] += " " + quote
                step["produces"].append(quote)
                step["confirm"].append({"produces": quote,
                    "by": "Inspect the response schema; pass when id and label are declared as strings.",
                    "level": "inspect"})
                self.assertEqual(chunks.check_plan(case, widened, widened), [])

    def test_legacy_encoder_clarification_preserves_original_obligations(self):
        case = self.cases["legacy"]
        raw = copy.deepcopy(case["plan"])
        encoder = raw["steps"][1]
        encoder["statement"] = ("The response encoder uses only the response schema and emits "
                                "id and label matching the response schema.")
        condition = "The response encoder uses only the response schema."
        encoder["produces"].append(condition)
        encoder["confirm"].append({"produces": condition,
            "by": "Inspect the encoder; pass when it requires no cache-purge output.", "level": "inspect"})
        self.assertEqual(chunks.check_plan(case, raw, raw), [])
        # Mechanical preservation accepts this wording; the independent review
        # still must assess statement meaning and source-grounded new obligations.

    def test_legacy_widening_rejects_narrowing_moved_checks_edges_and_false_dependencies(self):
        case = self.cases["legacy"]
        mutations = (
            lambda p: p["steps"][0]["produces"].pop(),
            lambda p: p["steps"][0]["confirm"].pop(),
            lambda p: p["steps"][0]["inputs"].pop(),
            lambda p: p["steps"][0].update(statement="A different deliverable is complete."),
            lambda p: p["steps"][0]["inputs"].append(
                {"from": "S2", "need": p["steps"][1]["produces"][0]}),
        )
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                raw = copy.deepcopy(case["plan"])
                mutate(raw)
                self.assertTrue(chunks.check_plan(case, raw, raw))

        raw = copy.deepcopy(case["plan"])
        moved = raw["steps"][0]["confirm"].pop()
        raw["steps"][1]["confirm"].append(moved)
        self.assertTrue(chunks.check_plan(case, raw, raw))

    def test_blocked_widening_requires_a_new_output_and_usable_check(self):
        case = self.cases["legacy"]
        quote = "The response schema lists id and label as strings."

        def widened():
            raw = copy.deepcopy(case["plan"])
            step = raw["steps"][0]
            step["statement"] += " " + quote
            step["produces"].append(quote)
            step["confirm"].append({"produces": quote,
                "by": "Inspect the response schema; pass when id and label are declared as strings.",
                "level": "inspect"})
            return raw

        raw = widened()
        raw["steps"][0]["confirm"][-1]["by"] = "Inspect the original request."
        self.assertTrue(chunks.check_plan(case, raw, raw))
        raw = widened()
        raw["steps"][0]["confirm"].pop()
        self.assertTrue(chunks.check_plan(case, raw, raw))
        raw = widened()
        duplicate = raw["steps"][0]["produces"][0]
        raw["steps"][0]["produces"].append(duplicate)
        raw["steps"][0]["confirm"].append({"produces": duplicate,
            "by": "Inspect the original request; pass when it names the requirement.",
            "level": "inspect"})
        self.assertTrue(chunks.check_plan(case, raw, raw))

    def test_bounded_blocked_case_keeps_nonprovisional_steps_and_bounds(self):
        case = self.cases["bounded"]
        raw = copy.deepcopy(case["plan"])
        quote = "The response schema lists id and label as strings."
        s1 = next(s for s in raw["steps"] if s["id"] == "S1")
        s1["statement"] += " " + quote
        s1["produces"].append(quote)
        s1["confirm"].append({"produces": quote,
            "by": "Inspect the response schema; pass when id and label are declared as strings.",
            "level": "inspect"})
        self.assertEqual(chunks.check_plan(case, raw, raw), [])

        forbidden = copy.deepcopy(raw)
        forbidden["steps"][1]["statement"] += " Changed."
        self.assertTrue(chunks.check_plan(case, forbidden, forbidden))
        forbidden = copy.deepcopy(raw)
        forbidden["steps"][0]["inputs"].append({"from": None, "need": "Invented authority."})
        self.assertTrue(chunks.check_plan(case, forbidden, forbidden))
        forbidden = copy.deepcopy(raw)
        forbidden["steps"][0]["produces"][0] = "The schema is complete."
        self.assertTrue(chunks.check_plan(case, forbidden, forbidden))
        forbidden = copy.deepcopy(raw)
        forbidden["steps"].append(copy.deepcopy(forbidden["steps"][0]))
        self.assertTrue(chunks.check_plan(case, forbidden, forbidden))

    def test_source_aware_blocked_case_without_bounds_stays_unchanged(self):
        case = self.cases["no-bounds"]
        self.assertEqual(chunks.check_plan(case, case["plan"], case["plan"]), [])
        changed = copy.deepcopy(case["plan"])
        changed["steps"][0]["statement"] += " Changed."
        self.assertTrue(chunks.check_plan(case, changed, changed))

    def test_blocked_plans_may_record_residual_gaps_without_losing_goal_coverage(self):
        for key in ("legacy", "legacy-edge-free", "bounded", "no-bounds"):
            with self.subTest(case=key):
                case = self.cases[key]
                raw = copy.deepcopy(case["plan"])
                raw["unresolved"].append({"step": "S1", "need": "The required split needs edit authority.",
                                          "reason": "residual-risk"})
                self.assertEqual(chunks.check_plan(case, raw, raw), [])
                self.assertEqual(chunks.graph.completion_status(raw)["status"], "incomplete")
                self.assertEqual(chunks.graph.completion_status(raw)["open_goal_needs"], [])
                # Reporting a gap cannot license removing a promised outcome.
                raw["steps"][0]["produces"] = []
                self.assertTrue(chunks.check_plan(case, raw, raw))

    def test_recording_gaps_cannot_erase_old_gaps_or_claim_success(self):
        case = copy.deepcopy(self.cases["legacy-edge-free"])
        gap = {"step": "S1", "need": "The required split needs edit authority.", "reason": "residual-risk"}
        case["plan"]["unresolved"] = [gap]
        raw = copy.deepcopy(case["plan"])
        raw["unresolved"] = []
        self.assertTrue(chunks.check_plan(case, raw, raw))
        raw["unresolved"] = [gap, gap]
        self.assertTrue(chunks.check_plan(case, raw, raw))
        raw["unresolved"] = [gap, dict(gap, step="nonexistent")]
        self.assertIn("invalid final structure/waves", chunks.check_plan(case, raw, raw))
        raw = split_plan(self.case)
        raw["unresolved"] = [gap]
        self.assertIn("incomplete structural goal closure", self.check(raw))

    def test_absent_goal_field_is_not_silently_added(self):
        case = copy.deepcopy(self.cases["cohesive"])
        del case["plan"]["goal_needs"]
        raw = copy.deepcopy(case["plan"])
        raw["goal_needs"] = []
        self.assertIn("goal_needs presence/value changed", chunks.check_plan(case, raw, raw))

class LifecycleRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="backchain-chunk-regression-")
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name) / "run"
        chunks.prepare(self.run, ["mixed", "no-bounds", "bounded", "outscope"])

    def control_contract(self, case, directory):
        work = directory / "output"
        return {"workspace": str(work.resolve()), "work": "Exercise the actual preservation exit check.",
                "exit_condition": "The frozen candidate is mechanically preserved and a fresh callback verifies it.",
                "repeat_condition": "Continue after a failed check; stop incomplete when blocked.",
                "required_trivial_reviews": 0,
                "context": {"request": "Synthetic lifecycle apparatus control.", "scope": "fixture only",
                            "authority": "no product actions", "environment": "local", "resources": []},
                "exit_checks": [chunks.preservation_check(case, directory)]}

    def start_control(self, case, directory):
        work = directory / "output"
        contract = self.control_contract(case, directory)
        chunks.write(work / "start.json", contract)
        command = [sys.executable, "-B", str(chunks.LOOP / "scripts/until_loop_ephemeral.py"),
                   "start", "--receipt", str(work / "terminal.json")]
        started = subprocess.run(command, input=json.dumps(contract), text=True,
                                 capture_output=True, check=True)
        return json.loads(started.stdout)

    def prepare_check(self, case, directory, candidate=None):
        result = chunks.compare_preservation(case, directory, candidate=candidate)
        directory.joinpath("output", "comparison.json").write_text(result.stdout)
        return result

    def verify_packet(self, packet, work):
        return subprocess.run(packet["verify_script"], shell=True, executable="/bin/sh", cwd=work,
                              text=True, capture_output=True, check=False)

    def submit_report(self, packet, report):
        return subprocess.run(packet["done_argv"], input=json.dumps(report), text=True,
                              capture_output=True, check=False)

    def report(self, exit_assessment="satisfied", continuation="allowed"):
        return {"classification": "non-trivial", "exit_assessment": exit_assessment,
                "continuation_assessment": continuation, "evidence": "Authored lifecycle control.",
                "handoff": "Preserve the current fixture and the next issued check."}

    def test_live_request_binds_exact_check_and_per_callback_receipt_outputs(self):
        for key, mode in (("mixed", "source-aware"), ("no-bounds", "legacy")):
            with self.subTest(case=key):
                case = chunks.fixtures()[key]
                directory = self.run / key
                check = chunks.preservation_check(case, directory)
                self.assertEqual(chunks.preservation_mode(case), mode)
                self.assertEqual(check["id"], "backchain-preservation")
                self.assertEqual(check["clause"], "Final candidate-specific domain evidence is saved.")
                self.assertEqual(check["command"],
                                 chunks.shlex.join(chunks.preservation_argv(
                                     case, directory, receipt=directory / "output/comparison.json")))
                argv = chunks.preservation_argv(case, directory, receipt=directory / "output/comparison.json")
                self.assertEqual(argv[:3], [str(Path(sys.executable).resolve()), "-I", "-B"])
                request = (directory / "request.md").read_text()
                check_path = directory / "preservation-check.json"
                self.assertEqual(chunks.read(check_path), check)
                manifest = chunks.read(self.run / "manifest.json")
                self.assertEqual(manifest["cases"][key]["inputs"][str(check_path.relative_to(self.run))],
                                 chunks.digest(check_path))
                self.assertIn(str(check_path), request)
                evidence_path = directory / "evidence-check.json"
                self.assertEqual(chunks.read(evidence_path), chunks.evidence_check(directory))
                self.assertEqual(manifest["cases"][key]["inputs"][str(evidence_path.relative_to(self.run))],
                                 chunks.digest(evidence_path))
                self.assertIn(str(evidence_path), request)
                self.assertIn("do not retype or reconstruct their commands", request)
                self.assertIn("every callback", request)
                self.assertIn("comparison and", request)
                self.assertIn("candidate_snapshot entries", request)
                self.assertIn("run that packet's verify_script unchanged", request)
                self.assertIn("exact original Sx.confirm[n]", request)

    def make_result(self, key, callbacks=1, cancelled=False, residual_gap=False):
        case = chunks.fixtures()[key]
        directory = self.run / key
        work = directory / "output"
        raw = split_plan(case) if key == "mixed" else copy.deepcopy(case["plan"])
        if residual_gap:
            raw["unresolved"].append({"step": "S1", "need": "The required split needs edit authority.",
                                      "reason": "residual-risk"})
        chunks.write(work / "raw-plan.json", raw)
        self.assertEqual(chunks.validate(work / "raw-plan.json", work / "plan.json", work / "validation.json"),
                         not residual_gap)
        blocked = case["expected"]["runtime_status"] == "stopped"
        gap = ("The bounded repair cannot alter S2 or its inherited input edge."
               if key == "bounded" else "The necessary split lacks explicit source-aware bounds.")
        recovery = ("Obtain bounds for S2 and its edge, or regenerate the candidate."
                    if key == "bounded" else
                    "Obtain explicit source-aware bounds, or regenerate with a new binding.")
        domain = {
            "candidate": {"input_sha256": chunks.digest(directory / "candidate.json"),
                          "output_sha256": chunks.digest(work / "plan.json")},
            "planning_gaps": [gap] if blocked else [],
            "next_action": recovery if blocked else "",
            "review_records": [],
        }
        contract = {"workspace": str(work), "work": "Check the authored fixture plan.",
                    "exit_condition": "A complete authorized plan and evidence are saved.",
                    "repeat_condition": "Continue when authorized; block when authority is missing.",
                    "required_trivial_reviews": 0,
                    "context": {"request": "Synthetic lifecycle apparatus control.", "scope": "fixture only",
                                "authority": "no product actions", "environment": "local", "resources": []},
                    "exit_checks": [
                        {"id": "fixture", "clause": "Fixture candidate exists.", "command": "test -s plan.json"},
                        chunks.preservation_check(case, directory),
                        chunks.evidence_check(directory),
                    ]}
        chunks.write(work / "start.json", contract)
        cmd = [sys.executable, "-B", str(chunks.LOOP / "scripts/until_loop_ephemeral.py")]
        start = subprocess.run(cmd + ["start", "--receipt", str(work / "terminal.json")],
                               input=json.dumps(contract), text=True, capture_output=True, check=True)
        packet = json.loads(start.stdout)
        chunks.write(work / "packet-1.json", packet)
        for number in range(1, callbacks + 1):
            last = number == callbacks
            final_cancelled = last and blocked and cancelled
            comparison = chunks.compare_preservation(case, directory)
            self.assertIn(comparison.returncode, (0, 1), comparison.stderr)
            work.joinpath("comparison.json").write_text(comparison.stdout)
            receipt = json.loads(comparison.stdout)
            comparison_snapshot = work / f"comparison-{number}.json"
            comparison_snapshot.write_bytes((work / "comparison.json").read_bytes())
            candidate_snapshot = work / f"candidate-{number}.json"
            candidate_snapshot.write_bytes((work / "plan.json").read_bytes())
            record = work / f"review-{number}.json"
            narrative = []
            for difference in receipt["confirmation_differences"]:
                kind = difference["kind"]
                if isinstance(difference["before"], dict):
                    before = difference["before"]
                    original = f"{before['step_id']}.confirm[{before['confirm_index']}]"
                else:
                    original = "new confirmation"
                if kind == "unchanged_produce_confirmation_changed":
                    narrative.append(f"Audit finding and source map for {original}: synthetic fixture review.")
                elif kind == "produce_text_absent":
                    narrative.append(f"Source-linked old-to-new mapping for {original}: verification obligation retained.")
                elif kind == "moved_unchanged":
                    narrative.append(f"Reviewed moved confirmation from {original}.")
                else:
                    narrative.append("Reviewed added confirmation.")
            chunks.write(record, {
                "fixture": "authored apparatus review; not a model execution",
                "callback": number, "cycle": "full Backchain review/fix/check",
                "narrative": "\n".join(narrative),
            })
            domain["review_records"].append({
                "path": str(record.resolve()), "sha256": chunks.digest(record),
                "comparison": {"path": str(comparison_snapshot.resolve()),
                               "sha256": chunks.digest(comparison_snapshot)},
                "candidate_snapshot": {"path": str(candidate_snapshot.resolve()),
                                       "sha256": chunks.digest(candidate_snapshot)},
            })
            chunks.write(work / "domain.json", domain)
            report = {"classification": "unresolved" if blocked or not last else "non-trivial",
                      "exit_assessment": ("unknown" if final_cancelled else
                                          "unsatisfied" if blocked or not last else "satisfied"),
                      "continuation_assessment": ("cancelled" if final_cancelled else
                                                   "blocked" if last and blocked else
                                                   "allowed"),
                      "evidence": (gap + " "
                                   "retain that gap and recovery." if blocked else
                                   "Authored control only."),
                      "handoff": "Retain the fixture candidate, full callback review and any remaining gap."}
            chunks.write(work / f"report-{number}.json", report)
            checked = subprocess.run(packet["verify_script"], shell=True, cwd=work, text=True,
                                     capture_output=True, check=False)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            done = subprocess.run(packet["done_argv"], input=json.dumps(report), text=True,
                                  capture_output=True, check=True)
            result = json.loads(done.stdout)
            if last:
                (work / "terminal-stdout.json").write_text(done.stdout)
                self.assertEqual(result["status"], "stopped" if blocked else "complete")
            else:
                self.assertEqual(result["status"], "active")
                packet = result
                chunks.write(work / f"packet-{number + 1}.json", packet)
        return case, directory

    def test_actual_runtime_completed_split_and_honest_block_are_accepted(self):
        for key in ("mixed", "bounded", "no-bounds"):
            case, directory = self.make_result(key)
            self.assertEqual(chunks.check_case(case, directory), [])
        self.assertTrue(chunks.check_run(self.run, ["mixed", "bounded", "no-bounds"])["passed"])

    def run_evidence_check(self, directory):
        return subprocess.run(chunks.shlex.split(chunks.evidence_check(directory)["command"]),
                              capture_output=True, text=True, check=False)

    def test_scripted_evidence_check_needs_no_terminal_or_semantic_success(self):
        for key in ("mixed", "bounded"):
            with self.subTest(case=key):
                case, directory = self.make_result(key, residual_gap=(key == "bounded"))
                (directory / "output/terminal.json").unlink()
                (directory / "output/terminal-stdout.json").unlink()
                checked = self.run_evidence_check(directory)
                self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
                self.assertTrue(json.loads(checked.stdout)["passed"])

    def test_scripted_evidence_check_rejects_missing_malformed_and_changed_artifacts(self):
        case, directory = self.make_result("mixed")
        work = directory / "output"
        original = chunks.read(work / "domain.json")
        for mutation in ("missing-review", "dict-path", "comparison-hash", "snapshot-hash", "candidate-hash"):
            with self.subTest(mutation=mutation):
                domain = copy.deepcopy(original)
                record = domain["review_records"][0]
                if mutation == "missing-review":
                    record["path"] = str(work / "missing.md")
                elif mutation == "dict-path":
                    record["path"] = {"path": record["path"]}
                elif mutation == "candidate-hash":
                    domain["candidate"]["output_sha256"] = "0" * 64
                else:
                    key = "comparison" if mutation == "comparison-hash" else "candidate_snapshot"
                    record[key]["sha256"] = "0" * 64
                chunks.write(work / "domain.json", domain)
                checked = self.run_evidence_check(directory)
                self.assertEqual(checked.returncode, 1, checked.stdout + checked.stderr)
                self.assertFalse(json.loads(checked.stdout)["passed"])
        chunks.write(work / "domain.json", original)
        validation = chunks.read(work / "validation.json")
        for key in ("input_sha256", "output_sha256", "validator_sha256"):
            with self.subTest(validation=key):
                changed = dict(validation, **{key: "0" * 64})
                chunks.write(work / "validation.json", changed)
                checked = self.run_evidence_check(directory)
                self.assertEqual(checked.returncode, 1, checked.stdout + checked.stderr)
                self.assertIn("stale or incorrect validation receipt", json.loads(checked.stdout)["failures"])

    def test_evaluator_rejects_changed_or_failed_prepared_evidence_check(self):
        case, directory = self.make_result("mixed")
        work = directory / "output"
        terminal = chunks.read(work / "terminal.json")
        check = next(c for c in terminal["exit_checks"] if c["id"] == chunks.EVIDENCE_CHECK_ID)
        check["command"] = "true"
        result = next(c for c in terminal["last_check_results"] if c["id"] == chunks.EVIDENCE_CHECK_ID)
        result.update(passed=False, exit_code=1)
        chunks.write(work / "terminal.json", terminal)
        chunks.write(work / "terminal-stdout.json", terminal)
        failures = chunks.check_case(case, directory)
        self.assertIn("fixed evidence exit check missing or changed", failures)
        self.assertIn("terminal lacks a passing artifact evidence check", failures)

    def test_failed_goal_check_blocks_false_satisfaction_then_repaired_plan_passes_fresh_action(self):
        case = chunks.fixtures()["mixed"]
        directory = self.run / "mixed"
        work = directory / "output"
        bad = copy.deepcopy(case["plan"])
        del bad["goal_needs"]
        chunks.write(work / "plan.json", bad)
        packet = self.start_control(case, directory)
        failed = self.prepare_check(case, directory)
        self.assertEqual(failed.returncode, 1)
        checked = self.verify_packet(packet, work)
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        rejected = self.submit_report(packet, self.report())
        self.assertEqual(rejected.returncode, 0, rejected.stderr)
        packet = json.loads(rejected.stdout)
        self.assertEqual(packet["status"], "active")
        self.assertEqual(packet["progress"]["action_number"], 2)

        chunks.write(work / "plan.json", case["plan"])
        passed = self.prepare_check(case, directory)
        self.assertEqual(passed.returncode, 0)
        checked = self.verify_packet(packet, work)
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        completed = self.submit_report(packet, self.report())
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["status"], "complete")

    def test_previous_action_check_cannot_satisfy_a_fresh_callback(self):
        case = chunks.fixtures()["no-bounds"]
        directory = self.run / "no-bounds"
        work = directory / "output"
        chunks.write(work / "plan.json", case["plan"])
        packet = self.start_control(case, directory)
        self.assertEqual(self.prepare_check(case, directory).returncode, 0)
        self.assertEqual(self.verify_packet(packet, work).returncode, 0)
        continued = self.submit_report(packet, self.report(exit_assessment="unsatisfied"))
        self.assertEqual(continued.returncode, 0, continued.stderr)
        packet = json.loads(continued.stdout)
        self.assertEqual(packet["status"], "active")
        self.assertEqual(packet["progress"]["action_number"], 2)

        reused = self.submit_report(packet, self.report())
        self.assertNotEqual(reused.returncode, 0)
        error = json.loads(reused.stdout)
        self.assertEqual(error["state_change"], "unchanged")
        self.assertIn("no verify run is recorded for this action", error["error"])
        recovered = subprocess.run(error["next_argv"], capture_output=True, text=True, check=True)
        packet = json.loads(recovered.stdout)
        self.assertEqual(packet["progress"]["action_number"], 2)
        self.assertEqual(self.prepare_check(case, directory).returncode, 0)
        self.assertEqual(self.verify_packet(packet, work).returncode, 0)
        completed = self.submit_report(packet, self.report())
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["status"], "complete")

    def test_git_workspace_rejects_edit_after_verify_before_satisfied_callback(self):
        case = chunks.fixtures()["no-bounds"]
        directory = self.run / "no-bounds"
        work = directory / "output"
        chunks.write(work / "plan.json", case["plan"])
        initialized = subprocess.run(["git", "-C", str(work), "init", "--quiet"],
                                     capture_output=True, text=True, check=False)
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        packet = self.start_control(case, directory)
        self.assertEqual(self.prepare_check(case, directory).returncode, 0)
        checked = self.verify_packet(packet, work)
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

        changed = copy.deepcopy(case["plan"])
        changed["steps"][0]["statement"] += " Edited after verification."
        chunks.write(work / "plan.json", changed)
        rejected = self.submit_report(packet, self.report())
        self.assertNotEqual(rejected.returncode, 0)
        error = json.loads(rejected.stdout)
        self.assertEqual(error["state_change"], "unchanged")
        self.assertIn("workspace changed after the recorded verify run", error["error"])

    def test_actual_runtime_cancelled_missing_authority_is_accepted_incomplete(self):
        case, directory = self.make_result("no-bounds", cancelled=True)
        self.assertEqual(chunks.check_case(case, directory), [])
        terminal = chunks.read(directory / "output/terminal.json")
        self.assertEqual(terminal["status"], "stopped")
        self.assertEqual(terminal["last_report"]["continuation_assessment"], "cancelled")
        terminal["last_report"]["exit_assessment"] = "satisfied"
        chunks.write(directory / "output/terminal.json", terminal)
        chunks.write(directory / "output/terminal-stdout.json", terminal)
        self.assertIn("missing-authority case did not stop incomplete",
                      chunks.check_case(case, directory))

    def test_actual_runtime_honest_block_with_recorded_gap_is_accepted(self):
        case, directory = self.make_result("bounded", residual_gap=True)
        self.assertEqual(chunks.check_case(case, directory), [])
        self.assertEqual(chunks.read(directory / "output/validation.json")["completion"]["status"], "incomplete")

    def test_review_records_cover_every_callback_in_a_multi_callback_run(self):
        case, directory = self.make_result("mixed", callbacks=3)
        work = directory / "output"
        self.assertEqual(chunks.check_case(case, directory), [])
        domain = chunks.read(work / "domain.json")
        domain["review_records"].pop()
        chunks.write(work / "domain.json", domain)
        self.assertIn("missing callback review records", chunks.check_case(case, directory))

    def test_evaluator_rejects_missing_changed_or_repaired_preservation_check(self):
        case, directory = self.make_result("mixed")
        work = directory / "output"
        start = chunks.read(work / "start.json")
        terminal = chunks.read(work / "terminal.json")
        stdout = chunks.read(work / "terminal-stdout.json")
        fixed = chunks.preservation_check(case, directory)

        start["exit_checks"] = [c for c in start["exit_checks"] if c["id"] != fixed["id"]]
        chunks.write(work / "start.json", start)
        self.assertIn("fixed preservation exit check missing or changed",
                      chunks.check_case(case, directory))
        start["exit_checks"].append(fixed)
        chunks.write(work / "start.json", start)

        altered = dict(fixed, command=fixed["command"] + " --changed")
        terminal["exit_checks"] = [altered if c["id"] == fixed["id"] else c
                                   for c in terminal["exit_checks"]]
        stdout["exit_checks"] = copy.deepcopy(terminal["exit_checks"])
        chunks.write(work / "terminal.json", terminal)
        chunks.write(work / "terminal-stdout.json", stdout)
        self.assertIn("fixed preservation exit check missing or changed",
                      chunks.check_case(case, directory))

        terminal["exit_checks"] = [fixed if c["id"] == fixed["id"] else c
                                   for c in terminal["exit_checks"]]
        terminal["check_repairs"] = [{"id": fixed["id"], "old_command": fixed["command"],
                                      "new_command": fixed["command"] + " --loosened"}]
        stdout["exit_checks"] = copy.deepcopy(terminal["exit_checks"])
        stdout["check_repairs"] = copy.deepcopy(terminal["check_repairs"])
        chunks.write(work / "terminal.json", terminal)
        chunks.write(work / "terminal-stdout.json", stdout)
        self.assertIn("preservation exit check was repaired", chunks.check_case(case, directory))

    def test_evaluator_rejects_missing_stale_and_replaced_cycle_receipts(self):
        case, directory = self.make_result("mixed", callbacks=2)
        work = directory / "output"
        self.assertEqual(chunks.check_case(case, directory), [])
        domain = chunks.read(work / "domain.json")
        original = copy.deepcopy(domain)
        del domain["review_records"][0]["comparison"]
        chunks.write(work / "domain.json", domain)
        self.assertIn("callback 1 lacks its comparison path/SHA-256", chunks.check_case(case, directory))

        domain = copy.deepcopy(original)
        ref = domain["review_records"][0]["comparison"]
        receipt_path = Path(ref["path"])
        receipt_bytes = receipt_path.read_bytes()
        stale = chunks.read(receipt_path)
        stale["candidate_sha256"] = "0" * 64
        chunks.write(receipt_path, stale)
        ref["sha256"] = chunks.digest(receipt_path)
        chunks.write(work / "domain.json", domain)
        self.assertIn("callback 1 comparison receipt differs from helper recomputation",
                      chunks.check_case(case, directory))

        receipt_path.write_bytes(receipt_bytes)
        domain = copy.deepcopy(original)
        snapshot_ref = domain["review_records"][0]["candidate_snapshot"]
        snapshot = Path(snapshot_ref["path"])
        snapshot.write_bytes(snapshot.read_bytes() + b" ")
        snapshot_ref["sha256"] = chunks.digest(snapshot)
        chunks.write(work / "domain.json", domain)
        self.assertIn("callback 1 comparison receipt differs from helper recomputation",
                      chunks.check_case(case, directory))

    def test_evaluator_rechecks_final_current_plan_against_saved_comparison(self):
        case, directory = self.make_result("mixed")
        work = directory / "output"
        plan = work / "plan.json"
        plan.write_bytes(plan.read_bytes() + b" ")
        # Even refreshed domain/validation metadata cannot hide a stale comparison.
        domain = chunks.read(work / "domain.json")
        domain["candidate"]["output_sha256"] = chunks.digest(plan)
        chunks.write(work / "domain.json", domain)
        validation = chunks.read(work / "validation.json")
        validation["output_sha256"] = chunks.digest(plan)
        chunks.write(work / "validation.json", validation)
        self.assertIn("current plan no longer matches the retained comparison receipt",
                      chunks.check_case(case, directory))

    def test_missing_receipt_stale_digest_and_overwritten_review_are_rejected(self):
        case, directory = self.make_result("mixed")
        work = directory / "output"
        receipt = (work / "terminal.json").read_bytes()
        (work / "terminal.json").unlink()
        self.assertTrue(chunks.check_case(case, directory))
        (work / "terminal.json").write_bytes(receipt)
        domain = chunks.read(work / "domain.json")
        domain["candidate"]["output_sha256"] = "0" * 64
        chunks.write(work / "domain.json", domain)
        self.assertIn("domain evidence candidate identity mismatch", chunks.check_case(case, directory))
        (work / "review-1.json").write_text("overwritten")
        self.assertIn("missing, overwritten, or outside-workspace review record", chunks.check_case(case, directory))

    def test_review_records_may_use_free_form_markdown(self):
        case, directory = self.make_result("mixed")
        work = directory / "output"
        review = work / "review-1.md"
        review.write_text("# Synthetic review\n\nNarrative review content is assessed independently.\n")
        domain = chunks.read(work / "domain.json")
        domain["review_records"][0].update(path=str(review), sha256=chunks.digest(review))
        chunks.write(work / "domain.json", domain)
        self.assertEqual(chunks.check_case(case, directory), [])

    def test_candidate_identity_allows_metadata_but_checks_both_hashes(self):
        case, directory = self.make_result("outscope")
        work = directory / "output"
        domain = chunks.read(work / "domain.json")
        domain["candidate"].update({"id": "outscope", "input_kind": "existing",
                                    "locator": "candidate.json"})
        chunks.write(work / "domain.json", domain)
        self.assertEqual(chunks.check_case(case, directory), [])
        for key in ("input_sha256", "output_sha256"):
            changed = copy.deepcopy(domain)
            changed["candidate"][key] = "0" * 64
            chunks.write(work / "domain.json", changed)
            self.assertIn("domain evidence candidate identity mismatch",
                          chunks.check_case(case, directory))

    def test_validation_input_hash_is_the_raw_prepackage_candidate(self):
        case, directory = self.make_result("mixed")
        work = directory / "output"
        receipt = chunks.read(work / "validation.json")
        self.assertNotEqual(receipt["input_sha256"], receipt["output_sha256"])
        receipt["input_sha256"] = receipt["output_sha256"]
        chunks.write(work / "validation.json", receipt)
        self.assertIn("stale or incorrect validation receipt", chunks.check_case(case, directory))

    def test_blocked_case_cannot_claim_completion_and_success_cannot_hide_a_gap(self):
        case, directory = self.make_result("no-bounds")
        work = directory / "output"
        terminal = chunks.read(work / "terminal.json")
        terminal["status"] = "complete"
        chunks.write(work / "terminal.json", terminal)
        chunks.write(work / "terminal-stdout.json", terminal)
        self.assertIn("incorrect runtime terminal disposition", chunks.check_case(case, directory))
        case, directory = self.make_result("mixed")
        work = directory / "output"
        domain = chunks.read(work / "domain.json")
        domain["planning_gaps"] = ["A known missing obligation."]
        chunks.write(work / "domain.json", domain)
        self.assertIn("complete claim has open planning gaps", chunks.check_case(case, directory))

    def test_prepare_and_check_fail_closed(self):
        with self.assertRaises(FileExistsError):
            chunks.prepare(self.run, ["mixed"])
        with self.assertRaises(ValueError):
            chunks.prepare(Path(self.temp.name) / "unknown", ["unknown"])
        result = chunks.check_run(self.run)
        self.assertFalse(result["passed"])
        self.assertEqual(set(result["cases"]), {"mixed", "no-bounds", "bounded", "outscope"})
        self.assertTrue(all(r["failures"] for r in result["cases"].values()))

    def test_invalid_json_and_changed_input_are_not_success(self):
        case, directory = self.make_result("mixed")
        (directory / "output/domain.json").write_text('{"partial":')
        self.assertTrue(chunks.check_case(case, directory))
        (directory / "source.md").write_text("new criteria")
        result = chunks.check_run(self.run, ["mixed"])
        self.assertTrue(any("frozen input changed" in s for s in result["cases"]["mixed"]["failures"]))

    def test_prepared_check_is_a_frozen_input(self):
        case, directory = self.make_result("mixed")
        for name in ("preservation-check.json", "evidence-check.json"):
            with self.subTest(file=name):
                check_path = directory / name
                changed = chunks.read(check_path)
                changed["command"] = "true"
                chunks.write(check_path, changed)
                result = chunks.check_run(self.run, ["mixed"])
                self.assertIn(f"frozen input changed: mixed/{name}",
                              result["cases"]["mixed"]["failures"])


if __name__ == "__main__":
    unittest.main()
