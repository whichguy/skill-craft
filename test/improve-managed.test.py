#!/usr/bin/env python3
"""Adversarial coverage for the pure managed Improve controller."""

from __future__ import annotations

import ast
import copy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills" / "improve" / "scripts" / "managed_controller.py"
SPEC = importlib.util.spec_from_file_location("managed_improve_controller", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"could not load {MODULE_PATH}")
managed = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(managed)

POLICY = "a" * 64
EXECUTOR = "b" * 64


def binding(profile: str = "product", *, required_review: bool = False, fallback: bool = False) -> dict:
    return managed.new_binding(
        parent_action="managed-improve",
        child_action_id="MI-001",
        profile=profile,
        input_identity={"candidate": "C-1", "baseline": "d" * 64},
        policy_digest=POLICY,
        executor_digest=EXECUTOR,
        commit_policy="audit-every-iteration",
        independent_review={"required": required_review, "fallback_allowed": fallback},
    )


def refs(phase: str, serial: int) -> list[str]:
    return [f"receipts/{serial:02d}-{phase}.json"]


def completed_pass(serial: int, outcome: str = "trivial", *, review: dict | None = None) -> dict:
    row: dict = {
        "id": f"I-{serial:03d}",
        "outcome": outcome,
        "verified": True,
        "commit": f"{serial:040x}",
        "evidence_ref": f"receipts/pass-{serial:03d}.json",
    }
    if review is not None:
        row["independent_review"] = review
    return row


def fresh(child: dict, serial: int) -> tuple[dict, dict]:
    output = {"identity_digest": f"{serial + 20:064x}", "manifest": f"artifacts/{serial}.json"}
    evidence = {
        "binding_sha256": child["binding_sha256"],
        "action": f"final-check-{serial}",
        "identity_digest": output["identity_digest"],
        "checks": [
            {
                "id": f"CHECK-{serial}",
                "result": "passed",
                "evidence_ref": f"checks/{serial}.json",
            }
        ],
        "evidence_ref": f"results/{serial}.json",
        "result": "passed",
    }
    return output, evidence


def complete(child: dict, serial: int, *, flags: dict | None = None, **extra: object) -> tuple[dict, dict]:
    phase = child["current_phase"]
    assert isinstance(phase, str)
    if flags is None and phase == "carry-forward":
        flags = {"disposition": "continue"}
    event: dict = {
        "kind": "complete",
        "phase": phase,
        "evidence_refs": refs(phase, serial),
        "flags": flags or {},
        **extra,
    }
    return managed.apply(child, event)


def run_product_pass(child: dict, serial: int, outcome: str = "trivial", *, review: dict | None = None) -> tuple[dict, dict]:
    for phase in (
        "review",
        "improve-plan",
        "improve-plan-verify",
        "improve-apply",
        "test-refine",
        "test-author",
    ):
        assert child["current_phase"] == phase
        child, _ = complete(child, serial)
    assert child["current_phase"] == "iteration-document"
    child, _ = complete(
        child,
        serial,
        flags={"documentation_disposition": "updated", "skill_disposition": "not-needed"},
    )
    for phase in ("verify", "carry-forward"):
        assert child["current_phase"] == phase
        child, _ = complete(child, serial)
    assert child["current_phase"] == "commit"
    return complete(
        child,
        serial,
        audit_commit=f"{serial:040x}",
        completed_pass=completed_pass(serial, outcome, review=review),
        open_findings=[],
    )


class ManagedImproveRouteTests(unittest.TestCase):
    def test_decide_preserves_shiploop_readiness_shape(self) -> None:
        fixtures = (
            ([], [], {"phase": "active", "trivial_streak": 0}),
            ([completed_pass(1)], [], {"phase": "active", "trivial_streak": 1}),
            ([completed_pass(1), completed_pass(2)], [], {"phase": "ready", "trivial_streak": 2}),
            ([completed_pass(1, "material"), completed_pass(2)], [], {"phase": "active", "trivial_streak": 1}),
            ([completed_pass(1), completed_pass(2)], ["F-open"], {"phase": "active", "trivial_streak": 2}),
        )
        for passes, findings, expected in fixtures:
            with self.subTest(passes=passes, findings=findings):
                self.assertEqual(managed.decide(passes, open_findings=findings), expected)

    def test_profile_routes_are_closed_and_separate(self) -> None:
        self.assertEqual(managed.PROFILE_STAGES["research"][0], "research-review")
        self.assertEqual(
            managed.route("research", "research-review")["current_phase"],
            "research-plan",
        )
        with self.assertRaises(managed.ManagedImproveError):
            managed.route("research", "behavior-review")
        with self.assertRaises(managed.ManagedImproveError):
            managed.route("planning", "research-review")

    def test_product_plan_verification_does_not_start_nested_plan_convergence(self) -> None:
        self.assertEqual(
            managed.route("product", "improve-plan-verify")["current_phase"],
            "improve-apply",
        )

    def test_step_plan_disposition_is_explicit_and_restarts_review(self) -> None:
        with self.assertRaises(managed.ManagedImproveError):
            managed.route("step-plan", "step-plan-review")
        self.assertEqual(
            managed.route(
                "step-plan", "step-plan-review", flags={"disposition": "required"}
            )["current_phase"],
            "step-plan-disposition",
        )
        self.assertEqual(
            managed.route("step-plan", "step-plan-disposition")["current_phase"],
            "step-plan-review",
        )

    def test_step_plan_repair_can_require_disposition_without_a_fake_review(self) -> None:
        for phase in managed.PROFILE_STAGES["step-plan"]:
            with self.subTest(phase=phase):
                required = managed.route(
                    "step-plan", phase, "repair", flags={"disposition": "required"}
                )
                self.assertEqual(
                    (required["current_phase"], required["paused"], required["reset_convergence"]),
                    ("step-plan-disposition", True, True),
                )
                not_required = managed.route(
                    "step-plan", phase, "repair", flags={"disposition": "not-required"}
                )
                self.assertEqual(
                    (not_required["current_phase"], not_required["paused"]),
                    ("step-plan-review", False),
                )

        child = managed.new_child(binding("step-plan"))
        child, _ = complete(child, 1, flags={"disposition": "not-required"})
        child, _ = complete(child, 1)
        self.assertEqual(child["current_phase"], "step-plan-verify")
        child, result = managed.apply(
            child,
            {
                "kind": "repair",
                "phase": "step-plan-verify",
                "evidence_refs": ["repairs/scope-change.md"],
                "flags": {"disposition": "required"},
                "reason": "scope change requires the existing disposition callback",
            },
        )
        self.assertEqual(
            (result["current_phase"], child["paused"], child["phase_records"][-1]["kind"]),
            ("step-plan-disposition", True, "repair"),
        )
        self.assertEqual(child["phase_records"][-1]["flags"], {"disposition": "required"})
        self.assertEqual(managed.assert_child(child), child)

        child, resumed = managed.resume(
            child,
            reason="scope disposition is ready for explicit handling",
            evidence_refs=["repairs/scope-disposition-ready.md"],
        )
        self.assertEqual(
            (
                resumed["resumed"],
                child["current_phase"],
                child["paused"],
                child["phase_records"][-1]["kind"],
            ),
            (True, "step-plan-disposition", False, "resume"),
        )
        child, result = complete(child, 2)
        self.assertEqual((result["current_phase"], child["paused"]), ("step-plan-review", False))

        with self.assertRaises(managed.ManagedImproveError):
            managed.resume(
                managed.new_child(binding("step-plan")),
                reason="there is no controller-owned pause to clear",
                evidence_refs=["repairs/no-pause.md"],
            )

        with self.assertRaises(managed.ManagedImproveError):
            managed.apply(
                managed.new_child(binding("product")),
                {
                    "kind": "repair",
                    "phase": "review",
                    "evidence_refs": ["repairs/invalid-flag.md"],
                    "flags": {"disposition": "required"},
                    "reason": "product repair cannot select a disposition",
                },
            )

    def test_product_documentation_and_skill_decisions_are_explicit(self) -> None:
        with self.assertRaises(managed.ManagedImproveError):
            managed.route("product", "iteration-document")
        self.assertEqual(
            managed.route(
                "product",
                "iteration-document",
                flags={"documentation_disposition": "not-needed", "skill_disposition": "validate"},
            )["current_phase"],
            "skill-validate",
        )

    def test_carry_forward_requires_explicit_continue_pause_or_repair(self) -> None:
        with self.assertRaises(managed.ManagedImproveError):
            managed.route("product", "carry-forward")
        self.assertEqual(
            managed.route(
                "product", "carry-forward", flags={"disposition": "continue"}
            )["current_phase"],
            "commit",
        )
        paused = managed.route(
            "product", "carry-forward", flags={"disposition": "pause"}
        )
        self.assertEqual((paused["current_phase"], paused["paused"]), ("carry-forward", True))
        repaired = managed.route(
            "product", "carry-forward", flags={"disposition": "repair"}
        )
        self.assertEqual((repaired["current_phase"], repaired["reset_convergence"]), ("review", True))

    def test_final_phase_cannot_be_skipped_or_entered_without_ready_passes(self) -> None:
        with self.assertRaises(managed.ManagedImproveError):
            managed.route("product", "final-verify", passes=[], open_findings=[])
        with self.assertRaises(managed.ManagedImproveError):
            managed.route("product", "finish")

    def test_commit_admits_final_only_after_two_completed_passes(self) -> None:
        passes = [completed_pass(1), completed_pass(2)]
        self.assertEqual(
            managed.route("objective", "objective-commit", passes=passes, open_findings=[])["current_phase"],
            "objective-finalize",
        )
        self.assertEqual(
            managed.route("objective", "objective-finalize", passes=passes, open_findings=[])["status"],
            "converged",
        )


class ManagedImproveEvidenceTests(unittest.TestCase):
    def test_material_pass_resets_before_two_later_trivial_passes_converge(self) -> None:
        child = managed.new_child(binding())
        child, result = run_product_pass(child, 1, "material")
        self.assertEqual(
            result,
            {"status": "active", "current_phase": "review", "paused": False, "trivial_streak": 0},
        )
        child, result = run_product_pass(child, 2, "trivial")
        self.assertEqual(result["trivial_streak"], 1)
        self.assertEqual(child["current_phase"], "review")
        child, result = run_product_pass(child, 3, "trivial")
        self.assertEqual(result["current_phase"], "final-verify")
        output, evidence = fresh(child, 3)
        child, result = complete(child, 3, output_identity=output, fresh_evidence=evidence)
        self.assertEqual(result["status"], "converged")
        self.assertEqual([row["outcome"] for row in child["passes"]], ["material", "trivial", "trivial"])

    def test_commit_requires_complete_current_evidence_and_rejects_repeated_commit(self) -> None:
        child = managed.new_child(binding())
        for phase in (
            "review", "improve-plan", "improve-plan-verify", "improve-apply", "test-refine", "test-author"
        ):
            child, _ = complete(child, 1)
        child, _ = complete(
            child,
            1,
            flags={"documentation_disposition": "updated", "skill_disposition": "not-needed"},
        )
        child, _ = complete(child, 1)
        child, _ = complete(child, 1)
        with self.assertRaises(managed.ManagedImproveError):
            complete(
                child,
                1,
                audit_commit="a" * 39,
                completed_pass=completed_pass(1),
                open_findings=[],
            )
        child, _ = complete(
            child,
            1,
            audit_commit=f"{1:040x}",
            completed_pass=completed_pass(1),
            open_findings=[],
        )
        # Reach the second pass's commit and prove a duplicate commit cannot be
        # counted even if a caller presents a distinct pass ID.
        for phase in (
            "review", "improve-plan", "improve-plan-verify", "improve-apply", "test-refine", "test-author"
        ):
            child, _ = complete(child, 2)
        child, _ = complete(
            child,
            2,
            flags={"documentation_disposition": "updated", "skill_disposition": "not-needed"},
        )
        child, _ = complete(child, 2)
        child, _ = complete(child, 2)
        duplicate = completed_pass(2)
        duplicate["commit"] = f"{1:040x}"
        with self.assertRaises(managed.ManagedImproveError):
            complete(
                child,
                2,
                audit_commit=f"{1:040x}",
                completed_pass=duplicate,
                open_findings=[],
            )

    def test_missing_evidence_or_generic_done_cannot_advance(self) -> None:
        child = managed.new_child(binding())
        with self.assertRaises(managed.ManagedImproveError):
            managed.apply(child, {"kind": "complete", "phase": "review", "evidence_refs": [], "flags": {}})
        with self.assertRaises(managed.ManagedImproveError):
            managed.apply(
                child,
                {"kind": "complete", "phase": "review", "evidence_refs": ["r"], "flags": {}, "done": True},
            )

    def test_required_reviewer_requires_performed_or_explicit_fallback(self) -> None:
        child = managed.new_child(binding(required_review=True, fallback=False))
        for phase in (
            "review", "improve-plan", "improve-plan-verify", "improve-apply", "test-refine", "test-author"
        ):
            child, _ = complete(child, 1)
        child, _ = complete(child, 1, flags={"documentation_disposition": "updated", "skill_disposition": "not-needed"})
        child, _ = complete(child, 1)
        child, _ = complete(child, 1)
        with self.assertRaises(managed.ManagedImproveError):
            complete(child, 1, audit_commit="1" * 40, completed_pass=completed_pass(1), open_findings=[])

        allowed = managed.new_child(binding(required_review=True, fallback=True))
        allowed, _ = run_product_pass(
            allowed,
            1,
            review={"status": "unavailable", "fallback": "self-review", "reason": "reviewer offline", "evidence_ref": "reviews/self-1.md"},
        )
        self.assertEqual(allowed["current_phase"], "review")

    def test_incomplete_status_is_never_a_certificate(self) -> None:
        child = managed.new_child(binding())
        child, result = managed.stop(child, "needs-prerequisite", "missing fixture", evidence_refs=["blockers/F-1.md"])
        self.assertEqual(result["status"], "needs-prerequisite")
        with self.assertRaises(managed.ManagedImproveError):
            managed.terminal_certificate(child)

    def test_repair_resets_epoch_and_resume_restores_the_same_child_phase(self) -> None:
        child = managed.new_child(binding())
        child, _ = complete(child, 1)
        self.assertEqual(child["current_phase"], "improve-plan")
        child, result = managed.apply(
            child,
            {
                "kind": "repair",
                "phase": "improve-plan",
                "evidence_refs": ["repairs/R-1.md"],
                "flags": {},
                "reason": "current plan evidence changed",
            },
        )
        self.assertEqual((result["current_phase"], child["passes"]), ("review", []))
        child, _ = managed.stop(child, "blocked", "waiting for access", evidence_refs=["blockers/B-1.md"])
        self.assertEqual(child["status"], "blocked")
        child, result = managed.resume(child, reason="access restored", evidence_refs=["blockers/B-1-resolved.md"])
        self.assertEqual((result["resumed"], child["status"], child["current_phase"]), (True, "active", "review"))

    def test_pause_keeps_active_child_at_carry_forward_until_continue(self) -> None:
        child = managed.new_child(binding())
        for phase in (
            "review", "improve-plan", "improve-plan-verify", "improve-apply", "test-refine", "test-author"
        ):
            child, _ = complete(child, 1)
        child, _ = complete(child, 1, flags={"documentation_disposition": "updated", "skill_disposition": "not-needed"})
        child, _ = complete(child, 1)
        self.assertEqual(child["current_phase"], "carry-forward")
        child, result = complete(child, 1, flags={"disposition": "pause"})
        self.assertEqual((result["current_phase"], child["paused"]), ("carry-forward", True))

        with self.assertRaises(managed.ManagedImproveError):
            complete(child, 1, flags={"disposition": "continue"})

        forged = copy.deepcopy(child)
        forged["phase_records"].append(
            {
                "sequence": len(forged["phase_records"]) + 1,
                "kind": "complete",
                "phase": "carry-forward",
                "evidence_refs": ["receipts/forged-pause-bypass.json"],
                "flags": {"disposition": "continue"},
            }
        )
        forged["current_phase"] = "commit"
        forged["paused"] = False
        forged["execution"]["phase"] = "commit"
        with self.assertRaises(managed.ManagedImproveError):
            managed.assert_child(forged)

        repaired, repair_result = managed.apply(
            copy.deepcopy(child),
            {
                "kind": "repair",
                "phase": "carry-forward",
                "evidence_refs": ["repairs/paused-carry-forward.md"],
                "flags": {},
                "reason": "an authorized repair supersedes the paused continuation",
            },
        )
        self.assertEqual(
            (repair_result["current_phase"], repaired["paused"]),
            ("review", False),
        )

        child, resumed = managed.resume(
            child,
            reason="carry-forward blocker was resolved",
            evidence_refs=["blockers/carry-forward-resolved.md"],
        )
        self.assertEqual(
            (resumed["resumed"], child["current_phase"], child["paused"]),
            (True, "carry-forward", False),
        )
        child, result = complete(child, 1, flags={"disposition": "continue"})
        self.assertEqual((result["current_phase"], child["paused"]), ("commit", False))

    def test_open_findings_after_verified_commit_keep_the_child_active(self) -> None:
        child = managed.new_child(binding())
        for phase in (
            "review", "improve-plan", "improve-plan-verify", "improve-apply", "test-refine", "test-author"
        ):
            child, _ = complete(child, 1)
        child, _ = complete(child, 1, flags={"documentation_disposition": "updated", "skill_disposition": "not-needed"})
        child, _ = complete(child, 1)
        child, _ = complete(child, 1)
        child, result = complete(
            child,
            1,
            audit_commit=f"{1:040x}",
            completed_pass=completed_pass(1),
            open_findings=["F-open"],
        )
        self.assertEqual(result["current_phase"], "review")
        self.assertEqual(child["open_findings"], ["F-open"])

    def test_final_phase_requires_shaped_fresh_evidence_not_a_done_claim(self) -> None:
        child = managed.new_child(binding())
        child, _ = run_product_pass(child, 1)
        child, _ = run_product_pass(child, 2)
        self.assertEqual(child["current_phase"], "final-verify")
        with self.assertRaises(managed.ManagedImproveError):
            complete(child, 2, output_identity={"identity_digest": "c" * 64}, fresh_evidence={"done": True})


class ManagedImproveCertificateTests(unittest.TestCase):
    def test_terminal_certificate_binds_child_and_rejects_stale_or_tampered_forms(self) -> None:
        child = managed.new_child(binding())
        child, _ = run_product_pass(child, 1)
        child, _ = run_product_pass(child, 2)
        self.assertEqual(child["current_phase"], "final-verify")
        output, evidence = fresh(child, 2)
        child, _ = complete(child, 2, output_identity=output, fresh_evidence=evidence)
        cert = managed.terminal_certificate(child)
        self.assertEqual(managed.assert_terminal_certificate(child, cert), cert)
        self.assertEqual(managed.assert_certificate(child["binding"], cert), cert)

        tampered = copy.deepcopy(cert)
        tampered["evidence_refs"].append("unbound/evidence")
        with self.assertRaises(managed.ManagedImproveError):
            managed.assert_terminal_certificate(child, tampered)

        stale_binding = binding()
        stale_binding["parent_action"] = "other-parent"
        with self.assertRaises(managed.ManagedImproveError):
            managed.assert_certificate(stale_binding, cert)

    def test_child_replay_rejects_tampered_cursor_or_pass_counter(self) -> None:
        child = managed.new_child(binding())
        child, _ = complete(child, 1)
        tampered = copy.deepcopy(child)
        tampered["current_phase"] = "verify"
        with self.assertRaises(managed.ManagedImproveError):
            managed.assert_child(tampered)
        tampered = copy.deepcopy(child)
        tampered["passes"] = [completed_pass(1)]
        with self.assertRaises(managed.ManagedImproveError):
            managed.assert_child(tampered)

    def test_execution_projection_is_allowed_but_cannot_change_phase(self) -> None:
        child = managed.new_child(binding())
        child["execution"]["stage"] = "legacy-review"
        child["execution"]["completed_actions"] = ["A-1"]
        child["execution"]["overlay"] = {"legacy": {"stage": "review"}}
        self.assertEqual(managed.assert_child(child)["execution"]["stage"], "legacy-review")
        child["execution"]["phase"] = "verify"
        with self.assertRaises(managed.ManagedImproveError):
            managed.assert_child(child)

    def test_controller_stays_pure_and_has_no_runtime_backend_import(self) -> None:
        tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        self.assertFalse(imported & {"os", "pathlib", "subprocess", "sys", "socket"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
