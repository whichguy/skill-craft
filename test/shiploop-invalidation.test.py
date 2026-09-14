#!/usr/bin/env python3
"""Focused pure-model checks for managed ShipLoop evidence invalidation."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_invalidation as invalidation  # noqa: E402


def sha(char: str) -> str:
    return char * 64


def git(char: str) -> str:
    return char * 40


def identity(*, revision: str = "a", fingerprint: str = "b", paths=None) -> dict:
    return {
        "version": 1,
        "revision": git(revision),
        "worktree_fingerprint": sha(fingerprint),
        "paths": paths if paths is not None else {"src/app.py": sha("c")},
    }


def system_case(ident="SYS-PRE-001", owner="SYSOLD", test_id="T-SYS-001") -> dict:
    return {
        "id": ident,
        "phase": "pre_deployment",
        "requirement": "The assembled application reports the exact system output.",
        "expected_outcome": "The exact system output is observable.",
        "environment": "isolated integration fixture",
        "prerequisites": ["BUILD"],
        "test_step": owner,
        "test_id": test_id,
        "deployment_step": None,
    }


def product_step(ident="BUILD", *, activity="implementation", produces=None) -> dict:
    return {
        "id": ident,
        "activity": activity,
        "produces": produces or [f"{ident} product output"],
    }


def product_receipt(commit="d", *, final="e") -> dict:
    return {
        "status": "complete",
        "merged_sha": git(commit),
        "final_head": git(final),
        "contract_done": {"record": "product done"},
        "contract_closure": {"fully_closed": True, "integrated_sha": git(commit)},
    }


def system_receipt(owner="SYSOLD", commit="f") -> dict:
    return {
        "status": "complete",
        "merged_sha": git(commit),
        "contract_done": {
            "step": owner,
            "check_sha256": sha("1"),
            "record": {"envelope": {"verify_action": f"verify-{owner}"}},
        },
        "contract_closure": {"fully_closed": True, "integrated_sha": git(commit)},
    }


def fixture():
    case = system_case()
    catalog = {"version": 1, "phases": {}, "cases": [case]}
    steps = [product_step(), product_step("SYSOLD", activity="system-test-pre")]
    receipts = {"BUILD": product_receipt(), "SYSOLD": system_receipt()}
    baseline = identity()
    snapshot = invalidation.capture_system_proof(
        catalog, steps, receipts, case_id=case["id"], product_identity=baseline
    )
    return catalog, steps, receipts, baseline, snapshot


def impact(*, paths, certainty="known", affected=None, contracts=(), produces=()):
    return {
        "version": 1,
        "certainty": certainty,
        "changes": {
            "artifacts": paths,
            "contracts": list(contracts),
            "produces": list(produces),
        },
        "affected": affected
        or {
            "local_cases": [],
            "system_cases": [],
            "documentation": [],
            "skills": [],
        },
    }


class InvalidationTests(unittest.TestCase):
    def test_snapshot_accepts_a_real_shiploop_action_id_that_starts_with_digits(self):
        catalog, steps, receipts, baseline, _snapshot = fixture()
        receipts["SYSOLD"]["contract_done"]["record"]["envelope"]["verify_action"] = (
            "20260914_system-test-verify"
        )

        snapshot = invalidation.capture_system_proof(
            catalog, steps, receipts, case_id="SYS-PRE-001", product_identity=baseline
        )

        self.assertEqual(
            snapshot["proof"]["verify_action"], "20260914_system-test-verify"
        )
        self.assertEqual(invalidation.validate_snapshot(snapshot), snapshot)

    def test_capture_binds_real_sys_closure_and_all_completed_product_receipts(self):
        catalog, steps, receipts, baseline, snapshot = fixture()
        self.assertEqual(snapshot["case"], catalog["cases"][0])
        self.assertEqual(snapshot["proof"]["test_step"], "SYSOLD")
        self.assertEqual(set(snapshot["products"]), {"BUILD"})
        self.assertEqual(invalidation.validate_snapshot(snapshot), snapshot)

        tampered = deepcopy(snapshot)
        tampered["proof"]["check_sha256"] = sha("2")
        with self.assertRaisesRegex(invalidation.InvalidationError, "digest changed"):
            invalidation.validate_snapshot(tampered)

        bad = deepcopy(receipts)
        bad["SYSOLD"]["contract_closure"]["integrated_sha"] = git("9")
        with self.assertRaisesRegex(invalidation.InvalidationError, "integrated contract closure"):
            invalidation.capture_system_proof(
                catalog, steps, bad, case_id="SYS-PRE-001", product_identity=baseline
            )

    def test_later_corrective_product_merge_stales_the_old_sys_proof_and_reopens_all_known_obligations(self):
        catalog, steps, receipts, baseline, snapshot = fixture()
        current_steps = [*steps, product_step("FIX", produces=["corrected output"])]
        current_receipts = {**receipts, "FIX": product_receipt("7", final="8")}
        current = identity(
            revision="9",
            fingerprint="a",
            paths={"src/app.py": sha("b"), "src/fix.py": sha("c")},
        )
        declaration = impact(
            paths=[
                {"path": "src/app.py", "before_sha256": sha("c"), "after_sha256": sha("b")},
                {"path": "src/fix.py", "before_sha256": None, "after_sha256": sha("c")},
            ],
            # The declaration intentionally tries to narrow obligations.  The
            # decision must remain conservative because actual receipt/path
            # evidence, rather than this host assertion, drove stale status.
            affected={
                "local_cases": [],
                "system_cases": [],
                "documentation": [],
                "skills": [],
            },
        )
        decision = invalidation.assess(
            snapshot,
            catalog,
            current_steps,
            current_receipts,
            product_identity=current,
            impact=declaration,
            known_local_cases=["CASE-LOCAL-1"],
            known_documentation=["README.md"],
            known_skills=["skills/check-output/SKILL.md"],
        )
        self.assertTrue(decision["stale"])
        self.assertEqual(decision["affected"], {
            "local_cases": ["CASE-LOCAL-1"],
            "system_cases": ["SYS-PRE-001"],
            "documentation": ["README.md"],
            "skills": ["skills/check-output/SKILL.md"],
        })
        self.assertEqual(decision["changes"]["receipts"]["added"], ["FIX"])
        self.assertEqual(decision["changes"]["paths"]["added"], ["src/fix.py"])

    def test_receipt_identity_or_actual_fingerprint_drift_is_stale_even_without_a_host_impact_map(self):
        catalog, steps, receipts, baseline, snapshot = fixture()
        changed_receipt = deepcopy(receipts)
        changed_receipt["BUILD"]["merged_sha"] = git("7")
        changed_receipt["BUILD"]["contract_closure"]["integrated_sha"] = git("7")
        decision = invalidation.assess(
            snapshot, catalog, steps, changed_receipt, product_identity=baseline
        )
        self.assertTrue(decision["stale"])
        self.assertEqual(decision["changes"]["receipts"]["changed"], ["BUILD"])

        fprint_only = identity(revision="a", fingerprint="9", paths={})
        empty_baseline = identity(revision="a", fingerprint="b", paths={})
        second_snapshot = invalidation.capture_system_proof(
            catalog, steps, receipts, case_id="SYS-PRE-001", product_identity=empty_baseline
        )
        decision = invalidation.assess(
            second_snapshot, catalog, steps, receipts, product_identity=fprint_only
        )
        self.assertTrue(decision["stale"])
        self.assertTrue(decision["changes"]["worktree_fingerprint_changed"])

    def test_current_frozen_sys_proof_anchor_must_still_match_its_merge_snapshot(self):
        catalog, steps, receipts, baseline, snapshot = fixture()
        rewritten = deepcopy(receipts)
        rewritten["SYSOLD"]["contract_done"]["check_sha256"] = sha("2")
        with self.assertRaisesRegex(invalidation.InvalidationError, "proof anchor changed"):
            invalidation.assess(
                snapshot, catalog, steps, rewritten, product_identity=baseline
            )

    def test_audit_only_revision_change_does_not_invalidate_unchanged_product_evidence(self):
        catalog, steps, receipts, baseline, snapshot = fixture()
        audit_only = identity(
            revision="9",
            fingerprint="b",
            paths={"src/app.py": sha("c")},
        )
        decision = invalidation.assess(
            snapshot, catalog, steps, receipts, product_identity=audit_only
        )
        self.assertFalse(decision["stale"])
        self.assertTrue(decision["changes"]["revision_changed"])

    def test_impact_artifact_declaration_must_match_real_path_digests_and_unknown_scope_is_conservative(self):
        catalog, steps, receipts, baseline, snapshot = fixture()
        current = identity(
            revision="9", fingerprint="a", paths={"src/app.py": sha("b")}
        )
        wrong = impact(paths=[])
        with self.assertRaisesRegex(invalidation.InvalidationError, "do not match actual"):
            invalidation.assess(
                snapshot, catalog, steps, receipts, product_identity=current, impact=wrong
            )
        unknown = impact(
            paths=[{"path": "src/app.py", "before_sha256": sha("c"), "after_sha256": sha("b")}],
            certainty="uncertain",
        )
        decision = invalidation.assess(
            snapshot,
            catalog,
            steps,
            receipts,
            product_identity=current,
            impact=unknown,
            known_local_cases=["CASE-1"],
        )
        self.assertTrue(decision["stale"])
        self.assertIn("uncertain", " ".join(decision["reasons"]))

    def test_observed_repo_paths_allow_spaces_but_reject_escape_or_control_characters(self):
        before = identity(paths={"docs/Release Notes.md": sha("c")})
        after = identity(revision="9", fingerprint="a", paths={"docs/Release Notes.md": sha("b")})
        valid = impact(
            paths=[
                {
                    "path": "docs/Release Notes.md",
                    "before_sha256": sha("c"),
                    "after_sha256": sha("b"),
                }
            ],
            affected={
                "local_cases": [],
                "system_cases": [],
                "documentation": ["docs/Release Notes.md"],
                "skills": [],
            },
        )
        normalized = invalidation.validate_impact_map(
            valid,
            known_documentation=["docs/Release Notes.md"],
            before_identity=before,
            after_identity=after,
        )
        self.assertEqual(
            normalized["changes"]["artifacts"][0]["path"], "docs/Release Notes.md"
        )
        for unsafe in ("/absolute.txt", "docs/../escape.txt", "docs\\escape.txt", "docs/bad\nname.txt"):
            broken = deepcopy(valid)
            broken["changes"]["artifacts"][0]["path"] = unsafe
            with self.subTest(unsafe=unsafe), self.assertRaisesRegex(
                invalidation.InvalidationError, "safe repository-relative path"
            ):
                invalidation.validate_impact_map(
                    broken,
                    known_documentation=["docs/Release Notes.md"],
                    before_identity=before,
                    after_identity=after,
                )

    def test_fingerprint_only_change_requires_uncertain_impact_even_when_path_map_is_present(self):
        before = identity(paths={"scripts/run.sh": sha("c")})
        after = identity(revision="9", fingerprint="a", paths={"scripts/run.sh": sha("c")})
        known = impact(paths=[])
        with self.assertRaisesRegex(invalidation.InvalidationError, "complete fingerprint changed"):
            invalidation.validate_impact_map(
                known, before_identity=before, after_identity=after
            )
        unknown = deepcopy(known)
        unknown["certainty"] = "uncertain"
        self.assertEqual(
            invalidation.validate_impact_map(
                unknown, before_identity=before, after_identity=after
            )["certainty"],
            "uncertain",
        )

    def test_all_required_cases_need_original_merge_time_snapshot(self):
        catalog, steps, receipts, baseline, snapshot = fixture()
        extra = system_case("SYS-PRE-002", "SYSNEW", "T-SYS-002")
        extended = deepcopy(catalog)
        extended["cases"].append(extra)
        extended_steps = [*steps, product_step("SYSNEW", activity="system-test-pre")]
        extended_receipts = {**receipts, "SYSNEW": system_receipt("SYSNEW", "7")}
        with self.assertRaisesRegex(invalidation.InvalidationError, "every required SYS case"):
            invalidation.assess_all(
                {"SYS-PRE-001": snapshot},
                extended,
                extended_steps,
                extended_receipts,
                product_identity=baseline,
            )

    def test_new_equivalent_sys_case_can_revalidate_old_stale_case_without_rewriting_it(self):
        catalog, steps, receipts, baseline, old_snapshot = fixture()
        replacement = system_case("SYS-PRE-002", "SYSNEW", "T-SYS-002")
        current_catalog = deepcopy(catalog)
        current_catalog["cases"].append(replacement)
        current_steps = [
            *steps,
            product_step("FIX", produces=["corrected output"]),
            product_step("SYSNEW", activity="system-test-pre"),
        ]
        current_receipts = {
            **receipts,
            "FIX": product_receipt("7", final="8"),
            "SYSNEW": system_receipt("SYSNEW", "9"),
        }
        current = identity(
            revision="a",
            fingerprint="d",
            paths={"src/app.py": sha("e"), "src/fix.py": sha("f")},
        )
        replacement_snapshot = invalidation.capture_system_proof(
            current_catalog,
            current_steps,
            current_receipts,
            case_id="SYS-PRE-002",
            product_identity=current,
        )
        snapshots = {"SYS-PRE-001": old_snapshot, "SYS-PRE-002": replacement_snapshot}
        decision = invalidation.assess_all(
            snapshots,
            current_catalog,
            current_steps,
            current_receipts,
            product_identity=current,
        )
        self.assertEqual(decision["stale_case_ids"], ["SYS-PRE-001"])
        # A later audit-only commit changes revision provenance, not product
        # content.  It must not make the newly captured replacement stale.
        audit_only = identity(
            revision="b",
            fingerprint="d",
            paths={"src/app.py": sha("e"), "src/fix.py": sha("f")},
        )
        decision = invalidation.assess_all(
            snapshots,
            current_catalog,
            current_steps,
            current_receipts,
            product_identity=audit_only,
        )
        self.assertEqual(decision["stale_case_ids"], ["SYS-PRE-001"])
        proof = invalidation.validate_revalidation(
            {
                "version": 1,
                "product_content_identity_sha256": decision["current_product_content_identity_sha256"],
                "replacements": [
                    {"stale_case_id": "SYS-PRE-001", "replacement_case_id": "SYS-PRE-002"}
                ],
            },
            decision,
            snapshots,
            current_catalog,
        )
        self.assertEqual(proof["replacements"][0]["replacement_case_id"], "SYS-PRE-002")

        broken_catalog = deepcopy(current_catalog)
        broken_catalog["cases"][1]["expected_outcome"] = "weakened outcome"
        with self.assertRaisesRegex(invalidation.InvalidationError, "frozen SYS requirement"):
            invalidation.validate_revalidation(
                {
                    "version": 1,
                    "product_content_identity_sha256": decision["current_product_content_identity_sha256"],
                    "replacements": [
                        {"stale_case_id": "SYS-PRE-001", "replacement_case_id": "SYS-PRE-002"}
                    ],
                },
                decision,
                snapshots,
                broken_catalog,
            )
        broken_environment = deepcopy(current_catalog)
        broken_environment["cases"][1]["environment"] = "a different target"
        with self.assertRaisesRegex(invalidation.InvalidationError, "environment"):
            invalidation.validate_revalidation(
                {
                    "version": 1,
                    "product_content_identity_sha256": decision["current_product_content_identity_sha256"],
                    "replacements": [
                        {"stale_case_id": "SYS-PRE-001", "replacement_case_id": "SYS-PRE-002"}
                    ],
                },
                decision,
                snapshots,
                broken_environment,
            )
        stale_replacement = deepcopy(decision)
        stale_replacement["stale_case_ids"] = ["SYS-PRE-001", "SYS-PRE-002"]
        with self.assertRaisesRegex(invalidation.InvalidationError, "distinct captured replacement"):
            invalidation.validate_revalidation(
                {
                    "version": 1,
                    "product_content_identity_sha256": decision["current_product_content_identity_sha256"],
                    "replacements": [
                        {"stale_case_id": "SYS-PRE-001", "replacement_case_id": "SYS-PRE-002"},
                        {"stale_case_id": "SYS-PRE-002", "replacement_case_id": "SYS-PRE-001"},
                    ],
                },
                stale_replacement,
                snapshots,
                current_catalog,
            )


if __name__ == "__main__":
    unittest.main()
