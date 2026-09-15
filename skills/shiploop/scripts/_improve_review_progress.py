"""Pure receipt-derived convergence decisions for Improve review cycles.

The caller supplies declared candidate descriptors and a declared review
classification.  This helper validates the receipt shape and derives only the
mechanical two-consecutive-clean-review rule; it does not inspect a candidate,
run checks, or treat host declarations as semantic proof.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


_REVIEW_FIELDS = frozenset(
    (
        "candidate_before",
        "candidate_after",
        "classification",
        "checks",
        "improvements_complete",
        "open_findings",
    )
)
_RECEIPT_FIELDS = frozenset(("id", "outcome", "review"))
_CLASSIFICATIONS = frozenset(("material", "trivial", "none", "uncertain"))
_CHECK_RESULTS = frozenset(("passed", "failed", "stale", "incomplete"))
_OUTCOMES = frozenset(("done", "repeat", "blocked"))


class ReviewProgressError(ValueError):
    """A review receipt cannot support a convergence decision."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise ReviewProgressError(message)


def _text(value: Any, label: str) -> str:
    _need(isinstance(value, str) and bool(value.strip()), f"{label} must be a nonempty string")
    return value


def _exact_fields(value: Mapping[str, Any], fields: frozenset[str], label: str) -> None:
    missing = fields - set(value)
    extra = set(value) - fields
    _need(not missing and not extra, f"{label} must contain exactly its required fields")


def normalize_review(value: Any) -> dict[str, Any]:
    """Validate and detach one completed review's declarative evidence."""
    _need(isinstance(value, Mapping), "review must be an object")
    _exact_fields(value, _REVIEW_FIELDS, "review")

    candidate_before = _text(value["candidate_before"], "review.candidate_before")
    candidate_after = _text(value["candidate_after"], "review.candidate_after")
    classification = value["classification"]
    _need(
        isinstance(classification, str) and classification in _CLASSIFICATIONS,
        "review.classification is invalid",
    )
    checks = value["checks"]
    _need(
        isinstance(checks, str) and checks in _CHECK_RESULTS,
        "review.checks is invalid",
    )
    improvements_complete = value["improvements_complete"]
    _need(
        type(improvements_complete) is bool,
        "review.improvements_complete must be a boolean",
    )
    open_findings = value["open_findings"]
    _need(isinstance(open_findings, list), "review.open_findings must be a list")
    normalized_findings = [
        _text(finding, f"review.open_findings[{index}]")
        for index, finding in enumerate(open_findings)
    ]
    return {
        "candidate_before": candidate_before,
        "candidate_after": candidate_after,
        "classification": classification,
        "checks": checks,
        "improvements_complete": improvements_complete,
        "open_findings": normalized_findings,
    }


def _normalize_receipt(value: Any) -> tuple[str, str, dict[str, Any] | None]:
    _need(isinstance(value, Mapping), "review receipt must be an object")
    _exact_fields(value, _RECEIPT_FIELDS, "review receipt")
    ident = _text(value["id"], "review receipt.id")
    outcome = value["outcome"]
    _need(
        isinstance(outcome, str) and outcome in _OUTCOMES,
        "review receipt.outcome is invalid",
    )
    review = value["review"]
    if outcome == "done":
        return ident, outcome, normalize_review(review)
    _need(review is None, f"review receipt.review must be null for {outcome}")
    return ident, outcome, None


def _is_eligible(review: dict[str, Any]) -> bool:
    return (
        review["classification"] in {"trivial", "none"}
        and review["checks"] == "passed"
        and review["improvements_complete"]
        and not review["open_findings"]
    )


def decide(receipts: Any) -> dict[str, Any]:
    """Derive readiness from ordered, distinct completed review receipts.

    A candidate discontinuity resets the streak before evaluating the current
    review.  It does not invalidate the current review: a fully eligible review
    on the new candidate begins a new streak at one.
    """
    _need(isinstance(receipts, list), "review receipts must be a list")
    seen_ids: set[str] = set()
    previous_candidate_after: str | None = None
    trivial_streak = 0
    current_eligible = False

    for value in receipts:
        ident, outcome, review = _normalize_receipt(value)
        _need(ident not in seen_ids, f"review receipt ID repeats: {ident}")
        seen_ids.add(ident)

        if outcome != "done":
            trivial_streak = 0
            previous_candidate_after = None
            current_eligible = False
            continue

        assert review is not None
        if (
            previous_candidate_after is not None
            and previous_candidate_after != review["candidate_before"]
        ):
            trivial_streak = 0

        current_eligible = _is_eligible(review)
        if current_eligible:
            trivial_streak += 1
        else:
            trivial_streak = 0
        previous_candidate_after = review["candidate_after"]

    return {
        "ready": current_eligible and trivial_streak >= 2,
        "trivial_streak": trivial_streak,
    }
