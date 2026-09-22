"""Shared synthetic delivery-contract fixture values."""

from __future__ import annotations

def contract(*, candidate: str = "candidate-v1") -> dict:
    """A small private consumer with distinct source/effect/behavior evidence."""
    return {
        "consumer": "private game page",
        "target": "fixture-head",
        "behavior": "a drag visibly follows the selected piece",
        "candidate": candidate,
        "operation": "sync the approved private source target",
        "necessity": "required",
        "basis": "The requested feature must be usable by the existing game user.",
        "exclusions": ["public access", "versioned deployment"],
        "authority": {
            "status": "approved",
            "kind": "repo-policy",
            "reference": "SHIPLOOP.md#private-head-update",
            "approval_ref": "Original request approved the private target update.",
            "target": "fixture-head",
            "operation": "sync the approved private source target",
        },
        "obligations": [
            {
                "id": "pre-drag",
                "consumer": "private game page",
                "target": "fixture-head",
                "kind": "pre-update",
                "phase": "system-test",
                "expected": "existing move checks pass for candidate-v1",
                "required": True,
            },
            {
                "id": "update-effect",
                "consumer": "private game page",
                "target": "fixture-head",
                "kind": "effect",
                "phase": "release",
                "expected": "the approved source update is recorded",
                "required": True,
            },
            {
                "id": "update-identity",
                "consumer": "private game page",
                "target": "fixture-head",
                "kind": "identity",
                "phase": "release",
                "expected": "the target identifies candidate-v1",
                "required": True,
            },
            {
                "id": "visual-drag",
                "consumer": "private game page",
                "target": "fixture-head",
                "kind": "behavior",
                "phase": "release-verify",
                "expected": "a dragged piece visibly follows the pointer",
                "required": True,
            },
        ],
    }

def local_contract() -> dict:
    """A deliberately local-only result that still needs consumer behavior proof."""
    result = contract()
    result["necessity"] = "not-required"
    result["basis"] = "The user explicitly requested local-only verification."
    result["authority"] = {
        "status": "not-required",
        "kind": "request",
        "reference": "Original request says source-only.",
        "target": "fixture-head",
        "operation": "sync the approved private source target",
    }
    result["obligations"] = [
        row for row in result["obligations"]
        if row["kind"] in {"pre-update", "behavior"}
    ]
    return result


