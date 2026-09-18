#!/usr/bin/env python3
"""Create an honestly labeled synthetic cursor for one real B producer."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT.parent
PACKAGE = STUDY / "package" / "shiploop"

sys.path.insert(0, str(PACKAGE / "scripts"))
import shiploop_navigator as navigator  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def synthetic_result(stage: str, work_items: list[dict[str, str]] | None = None) -> dict[str, object]:
    value: dict[str, object] = {
        "outcome": "done",
        "summary": (
            f"SYNTHETIC ambition-followup B predecessor for {stage}; no producer, "
            "model, semantic review, environment evaluation, or Improve runtime occurred."
        ),
        "evidence_refs": [str(ROOT / "evidence" / "seed-claims.md")],
    }
    if work_items is not None:
        value["work_items"] = work_items
    return value


def main() -> None:
    skill = (PACKAGE / "SKILL.md").read_text(encoding="utf-8")
    if "version: 0.15.2" not in skill:
        raise SystemExit("frozen selected package is not the intended 0.15.2 guide")
    request = (ROOT / "evidence" / "request.md").read_text(encoding="utf-8")
    work_items = [
        {
            "id": "W1",
            "title": "Plan an expressive compact-to-expanded read-only export activity explorer",
            "context": (
                "Read evidence/request.md, evidence/controlled-status-contract.md, "
                "evidence/tooling-facts.md, evidence/producer-boundary.md and the copied "
                "product baseline. Preserve Field Notes' existing components, interaction "
                "boundaries and navy/amber identity. W1 observes only the supplied GET "
                "status contract. Decide whether to evolve the established DOM/CSS path or "
                "conditionally adopt a target-native continuity enhancement after a compatible "
                "probe. Do not claim View Transitions or a package is available; do not add a "
                "framework, package, server, socket, storage, export request, download, selector or W2."
            ),
        },
        {
            "id": "W2",
            "title": "Resolve account-scoped persistent drafts after a storage contract exists",
            "context": (
                "Separate blocked work. The controlled W1 input has no storage or draft API; "
                "do not invent its supplier contract or fold it into the activity explorer."
            ),
        },
    ]
    state = navigator.new_state(
        str(ROOT / "product"),
        request,
        protocol_version=3,
        improve_skill=str(STUDY.parent / "frozen" / "improve" / "SKILL.md"),
    )
    seeded: list[dict[str, str]] = []
    for stage in ("intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare", "select-work"):
        if navigator.current_stage(state) != stage:
            raise SystemExit(f"expected {stage}, got {navigator.current_stage(state)}")
        action = dict(navigator.current_action(state))
        state = navigator.apply(
            state,
            action["id"],
            synthetic_result(stage, work_items if stage == "plan" else None),
        )
        state = navigator.finish_improve(
            state,
            action["id"],
            {
                "kind": "synthetic-fixture-predecessor",
                "claim": "No actual Improve runtime, review, or semantic assessment occurred.",
                "stage": stage,
            },
        )
        seeded.append({"action": action["id"], "stage": stage})
    if navigator.current_stage(state) != "step-plan" or state["active_improve"] is not None:
        raise SystemExit("synthetic cursor did not reach an unbound step-plan producer")
    navigator.save(ROOT / "run", state)
    print(json.dumps({
        "case": ROOT.name,
        "current_action": dict(navigator.current_action(state)),
        "current_stage": navigator.current_stage(state),
        "seeded_predecessors": seeded,
        "state_sha256": digest(ROOT / "run" / "state.md"),
        "synthetic_only_before_producer": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
