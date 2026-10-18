#!/usr/bin/env python3
"""Compare frozen Backchain obligations; never judge authorization or plan quality.

Exit 0: mechanical invariants hold (differences still need semantic review).
Exit 1: invariant or retained-receipt mismatch. Exit 2: baseline binding mismatch.
Exit 3: comparison could not run. No plan or receipt is written by this script.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError(f"non-JSON constant: {value}")


def read_json(data):
    return json.loads(data, object_pairs_hook=unique_object, parse_constant=invalid_constant)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inventory(plan):
    """Read only the fields needed for comparison, not the graph's schema."""
    if not isinstance(plan, dict) or not isinstance(plan.get("steps"), list):
        raise ValueError("comparison needs a plan object with a steps array")
    owners, entries = {}, []
    for step in plan["steps"]:
        if not isinstance(step, dict) or not isinstance(step.get("id"), str):
            raise ValueError("comparison needs string step IDs")
        sid = step["id"]
        if sid in owners:
            raise ValueError(f"ambiguous duplicate step ID: {sid}")
        produces, confirms = step.get("produces"), step.get("confirm", [])
        if not isinstance(produces, list) or not all(isinstance(p, str) for p in produces):
            raise ValueError(f"{sid}: comparison needs a produces string array")
        if not isinstance(confirms, list) or not all(
            isinstance(c, dict) and isinstance(c.get("produces"), str) for c in confirms
        ):
            raise ValueError(f"{sid}: comparison needs confirmation objects with produces text")
        owners[sid] = produces
        entries.extend({"step_id": sid, "confirm_index": i, "confirmation": c}
                       for i, c in enumerate(confirms))
    return owners, entries


def compare(baseline, candidate, mode):
    before_owners, before = inventory(baseline)
    after_owners, after = inventory(candidate)
    errors, differences, used = [], [], set()
    goals_preserved = (("goal_needs" in baseline) == ("goal_needs" in candidate)
                       and canonical(baseline.get("goal_needs")) == canonical(candidate.get("goal_needs")))
    if not goals_preserved:
        errors.append("goal_needs presence/value changed")
    # Prefer the original owner before matching a verbatim move. Consume matches
    # one at a time so repeated confirmation objects cannot hide a deletion.
    for old in before:
        sid, confirm = old["step_id"], old["confirmation"]
        exact = [i for i, new in enumerate(after) if i not in used
                 and confirm["produces"] in after_owners[new["step_id"]]
                 and canonical(new["confirmation"]) == canonical(confirm)]
        same_owner = [i for i in exact if after[i]["step_id"] == sid]
        if mode == "legacy" and confirm["produces"] in after_owners.get(sid, []) and not same_owner:
            errors.append(f"unchanged produce confirmation changed: {sid}.confirm[{old['confirm_index']}]")
        if exact:
            index = (same_owner or exact)[0]
            used.add(index)
            if after[index]["step_id"] != sid:
                differences.append({"kind": "moved_unchanged", "before": old, "after": [after[index]]})
            continue
        present = any(confirm["produces"] in produces for produces in after_owners.values())
        replacements = [new for new in after if new["confirmation"]["produces"] == confirm["produces"]
                        and confirm["produces"] in after_owners[new["step_id"]]]
        differences.append({"kind": ("unchanged_produce_confirmation_changed" if present else "produce_text_absent"),
                            "before": old, "after": replacements})
    described = {canonical(new) for diff in differences for new in diff["after"]}
    differences.extend({"kind": "added", "before": None, "after": [new]}
                       for i, new in enumerate(after) if i not in used and canonical(new) not in described)
    multi_owner = []
    for label, owners in (("baseline", before_owners), ("candidate", after_owners)):
        for produce in dict.fromkeys(p for values in owners.values() for p in values):
            ids = [sid for sid, values in owners.items() if produce in values]
            if len(ids) > 1:
                multi_owner.append({"plan": label, "produces": produce, "step_ids": ids})
    return {"scope": "mechanical preservation only; semantic review required",
            "mode": mode, "goal_needs_preserved": goals_preserved,
            "confirmation_differences": differences, "multi_owner_produces": multi_owner,
            "invariants_passed": not errors, "errors": errors}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--baseline-sha256", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--mode", choices=("legacy", "source-aware"), required=True)
    parser.add_argument("--verify-receipt", help="read-only comparison with a previously saved stdout receipt")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # Reserve exit 2 for the frozen baseline binding, not CLI usage errors.
        return 0 if exc.code == 0 else 3
    try:
        baseline_bytes = Path(args.baseline).read_bytes()
        if sha(baseline_bytes) != args.baseline_sha256:
            print("backchain preservation: frozen baseline SHA-256 mismatch", file=sys.stderr)
            return 2
        candidate_bytes = Path(args.candidate).read_bytes()
        receipt = compare(read_json(baseline_bytes), read_json(candidate_bytes), args.mode)
        receipt.update(baseline_sha256=sha(baseline_bytes), candidate_sha256=sha(candidate_bytes),
                       checker_sha256=sha(Path(__file__).read_bytes()))
        print(json.dumps(receipt, indent=2, ensure_ascii=False, allow_nan=False))
        if args.verify_receipt and canonical(read_json(Path(args.verify_receipt).read_bytes())) != canonical(receipt):
            print("backchain preservation: retained receipt is stale or changed", file=sys.stderr)
            return 1
        return 0 if receipt["invariants_passed"] else 1
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        print(f"backchain preservation: comparison could not run: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
