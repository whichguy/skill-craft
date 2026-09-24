#!/usr/bin/env python3
"""Measure rendered packet size, without a model, child runtime, or product work."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scripts-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--packets-dir", type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.scripts_dir.resolve()))
    import shiploop_navigator as navigator
    import shiploop_standalone_improve as bridge

    selected_card = args.scripts_dir.resolve().parents[1] / "improve/SKILL.md"
    skill = bridge.resolve_skill(str(selected_card))
    expected = (
        "intake discovery research spec test-strategy plan prepare select-work step-plan "
        "test-spec baseline test-author test-red implement test-green test-refine regression "
        "document skill-assess skill-validate static-checks verify integrate integration-verify "
        "carry-forward system-test-author system-test product-acceptance release-plan "
        "release-check release release-verify operations handoff"
    ).split()
    if args.packets_dir:
        args.packets_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    with tempfile.TemporaryDirectory(prefix="shiploop-packet-measure-") as temporary:
        root = Path(temporary)
        for label, context in (("normal", "docs/decisions.md: use the established runtime and test examples."),
                               ("oversized", "x" * 2_000_000 + " REQUIRED_TAIL")):
            state = navigator.new_state(str(root), "Implement the requested capability without changing its runtime.",
                                        protocol_version=3, improve_skill=str(selected_card))
            for stage in expected:
                if navigator.current_stage(state) != stage:
                    raise AssertionError("Unexpected traversal at " + stage)
                action = navigator.current_action(state)
                producer = navigator.render(None, root / "run", state)
                result = {"outcome": "done", "summary": "Synthetic measurement fixture; no work executed."}
                if stage == "plan":
                    result["work_items"] = [{"id": "W1", "title": "Requested capability", "context": context}]
                waiting = navigator.apply(state, action["id"], result)
                child = waiting["active_improve"]
                improve = None
                if child is not None:
                    # Only planning checkpoints and the last carry-forward park an Improve child.
                    child.update({"version": 1, "contract_marker": "ShipLoop standalone Improve binding: "
                                  + child["binding_id"], "skill": skill})
                    improve = navigator.render(None, root / "run", waiting)
                rows.append({"case": label, "stage": stage, "producer_characters": len(producer),
                             "improve_characters": None if improve is None else len(improve)})
                if args.packets_dir and label == "normal" and stage in {"discovery", "step-plan", "document", "prepare"}:
                    (args.packets_dir / (stage + ".md")).write_text(producer)
                    if improve is not None:
                        (args.packets_dir / (stage + "-improve.md")).write_text(improve)
                state = waiting
                if child is not None:
                    state = navigator.finish_improve(waiting, action["id"], {
                        "summary": "Synthetic completion; no actual Improve runtime executed.",
                        "lessons": "Retain relevant decision locators.",
                    })
            if state["status"] != "done":
                raise AssertionError("Traversal did not finish")
    report = {"scope": "Pure renderer experiment with synthetic transitions and selected package locators.",
              "scripts_dir": str(args.scripts_dir.resolve()), "rows": rows,
              "semantic_quality": "not measured", "model_tokens": None, "model_latency": None,
              "limits": "Character counts include package and temporary path lengths. No model or child runtime ran."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
