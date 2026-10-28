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

    def make_result(self, key, callbacks=1, cancelled=False):
        case = chunks.fixtures()[key]
        directory = self.run / key
        work = directory / "output"
        raw = split_plan(case) if key == "mixed" else case["plan"]
        chunks.write(work / "raw-plan.json", raw)
        self.assertTrue(chunks.validate(work / "raw-plan.json", work / "plan.json", work / "validation.json"))
        records = []
        for number in range(1, callbacks + 1):
            record = work / f"review-{number}.json"
            chunks.write(record, {"fixture": "authored apparatus review; not a model execution",
                                  "callback": number, "cycle": "full Backchain review/fix/check"})
            records.append({"path": str(record), "sha256": chunks.digest(record)})
        blocked = case["expected"]["runtime_status"] == "stopped"
        gap = ("The bounded repair cannot alter S2 or its inherited input edge."
               if key == "bounded" else "The necessary split lacks explicit source-aware bounds.")
        recovery = ("Obtain bounds for S2 and its edge, or regenerate the candidate."
                    if key == "bounded" else
                    "Obtain explicit source-aware bounds, or regenerate with a new binding.")
        chunks.write(work / "domain.json", {
            "candidate": {"input_sha256": chunks.digest(directory / "candidate.json"),
                          "output_sha256": chunks.digest(work / "plan.json")},
            "planning_gaps": [gap] if blocked else [],
            "next_action": recovery if blocked else "",
            "review_records": records,
        })
        contract = {"workspace": str(work), "work": "Check the authored fixture plan.",
                    "exit_condition": "A complete authorized plan and evidence are saved.",
                    "repeat_condition": "Continue when authorized; block when authority is missing.",
                    "required_trivial_reviews": 0,
                    "context": {"request": "Synthetic lifecycle apparatus control.", "scope": "fixture only",
                                "authority": "no product actions", "environment": "local", "resources": []},
                    "exit_checks": [{"id": "fixture", "clause": "Fixture candidate exists.", "command": "test -s plan.json"}]}
        chunks.write(work / "start.json", contract)
        cmd = [sys.executable, "-B", str(chunks.LOOP / "scripts/until_loop_ephemeral.py")]
        start = subprocess.run(cmd + ["start", "--receipt", str(work / "terminal.json")],
                               input=json.dumps(contract), text=True, capture_output=True, check=True)
        packet = json.loads(start.stdout)
        chunks.write(work / "packet-1.json", packet)
        for number in range(1, callbacks + 1):
            last = number == callbacks
            final_cancelled = last and blocked and cancelled
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
            if last and not blocked:
                subprocess.run(packet["verify_script"], shell=True, cwd=work, text=True,
                               capture_output=True, check=True)
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

    def test_review_records_cover_every_callback_in_a_multi_callback_run(self):
        case, directory = self.make_result("mixed", callbacks=3)
        work = directory / "output"
        self.assertEqual(chunks.check_case(case, directory), [])
        domain = chunks.read(work / "domain.json")
        domain["review_records"].pop()
        chunks.write(work / "domain.json", domain)
        self.assertIn("missing callback review records", chunks.check_case(case, directory))

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


if __name__ == "__main__":
    unittest.main()
