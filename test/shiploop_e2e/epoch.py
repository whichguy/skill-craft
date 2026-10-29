"""A durable, stepwise E2E learning/qualification controller.

init/next/status launch no models. launch and review are explicit model actions.
Every dispatch is recorded before calling the existing runner. An interrupted
dispatch is unknown until reconciled; next/resume never retry it automatically.
Candidate construction belongs to exploration (iterate.py); registration binds
the candidate before this controller compares it with its control.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import boundary
import hosts
import listeners
import promotion
import scorecard

CONTRACT = "shiploop-epoch/1"
LEDGER = "events.jsonl"
SEALED_FILES = ("result.json", "metrics.json", "timeline.jsonl", "invocation.json")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    # Receipts are immutable; a new interpretation is a new ledger event.
    with path.open("x") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


@contextlib.contextmanager
def locked(root: Path):
    with (root / ".epoch.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def events(root: Path) -> list[dict]:
    rows = []
    try:
        lines = (root / LEDGER).read_text().splitlines()
    except OSError as exc:
        raise ValueError(f"no readable epoch ledger: {exc}") from exc
    for index, line in enumerate(lines, 1):
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise ValueError(f"ledger row {index} is incomplete; preserve and reconcile it before continuing") from exc
        if not isinstance(row, dict) or row.get("sequence") != index:
            raise ValueError(f"invalid ledger sequence at row {index}")
        rows.append(row)
    return rows


def append(root: Path, kind: str, **fields) -> dict:
    row = {"sequence": len(events(root)) + 1, "at": time.time(), "kind": kind, **fields}
    with (root / LEDGER).open("a") as handle:
        handle.write(json.dumps(row, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return row


def initialise(root: Path, template: Path) -> dict:
    root = root.resolve()
    checkout = HERE.parents[1]
    if root == checkout or checkout in root.parents:
        raise ValueError("epoch output must be outside the checkout")
    raw = json.loads(template.read_text())
    if raw.get("contract") != "promotion/5":
        raise ValueError("epochs require a promotion/5 registration template")
    cases = raw.get("cases")
    if not isinstance(cases, dict) or not cases:
        raise ValueError("registration needs cases")
    raw.setdefault("registered_at", time.time())
    raw.setdefault("purpose", "product_change")
    raw.setdefault("floors", ["accuracy", "fidelity"])
    raw.setdefault("efficiency", ["tokens", "minutes"])
    raw.setdefault("quality_tolerance", 0.0)
    raw.setdefault("tolerance", 0.10)
    raw.setdefault("budget", {})
    raw.setdefault("qualification", boundary.qualification_snapshot(HERE, list(cases)))
    # Validate before leaving a partially created epoch on malformed input.
    root.mkdir(parents=True, exist_ok=False)
    write_json(root / "registration.json", raw)
    try:
        registration = promotion.load_registration(root / "registration.json")
    except BaseException:
        # Preserve the refused input for diagnosis; never relabel it as ready.
        (root / LEDGER).touch(exist_ok=False)
        append(root, "registration_refused", registration_sha256=digest(root / "registration.json"))
        raise
    (root / LEDGER).touch(exist_ok=False)
    (root / "runs").mkdir()
    (root / "receipts").mkdir()
    write_json(root / "roles.json", hosts.ROLE_DEFAULTS)
    write_json(root / "specification.json", {"sha256": digest(HERE / "SPEC.md"),
                                            "text": (HERE / "SPEC.md").read_text()})
    return append(root, "registered", contract=CONTRACT, registration_sha256=digest(root / "registration.json"),
                  roles_sha256=digest(root / "roles.json"), specification_sha256=digest(root / "specification.json"),
                  attempts=len(registration["attempts"]))


def registration(root: Path) -> dict:
    rows = events(root)
    if not rows or rows[0].get("kind") != "registered":
        raise ValueError("epoch has no accepted registration")
    for name, key in (("registration.json", "registration_sha256"), ("roles.json", "roles_sha256"),
                      ("specification.json", "specification_sha256")):
        if digest(root / name) != rows[0][key]:
            raise ValueError(f"frozen {name} changed; begin a new registration")
    try:
        reg = promotion.load_registration(root / "registration.json")
    except SystemExit as exc:
        raise ValueError(f"frozen qualification inputs changed or registration is invalid: {exc}") from exc
    observed = boundary.qualification_snapshot(HERE, list(reg["cases"]))
    if observed["sha256"] != reg["qualification"]["sha256"]:
        raise ValueError("frozen scorer, specification or requiredness inputs changed; begin a new registration")
    return reg


def attempt_spec(reg: dict, attempt_id: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", attempt_id):
        raise ValueError("attempt ID must be a safe single path component")
    matches = [row for row in reg["attempts"] if row["id"] == attempt_id]
    if len(matches) != 1:
        raise ValueError("attempt is not uniquely registered")
    return matches[0]


def state(root: Path) -> dict:
    reg = registration(root)
    rows = events(root)
    attempts = []
    for spec in reg["attempts"]:
        related = [row for row in rows if row.get("attempt_id") == spec["id"]]
        kinds = {row["kind"] for row in related}
        status = ("reviewed" if "reviewed" in kinds else "recorded" if "recorded" in kinds
                  else "not_launched" if "launch_intent" not in kinds else "unknown_launch")
        reviewed = [row for row in related if row["kind"] == "reviewed"]
        if reviewed:
            receipt = reviewed[-1]
            try:
                compatible = digest(root / receipt["receipt"]) == receipt["receipt_sha256"]
            except (OSError, KeyError):
                compatible = False
            if not compatible:
                status = "recorded"  # a new assessment is required; retain the invalidated old receipt
        if "recorded" in kinds:
            try:
                sealed_run(root, spec["id"])
            except (OSError, ValueError):
                status = "invalid_evidence"
        attempts.append({**spec, "status": status})
    decisions = [row for row in rows if row["kind"] == "decision"]
    discoveries = [row for row in rows if row["kind"] == "discovery_disposition"]
    return {"contract": CONTRACT, "attempts": attempts, "decision": decisions[-1] if decisions else None,
            "discoveries": discoveries, "publication": "not_performed",
            "generalisation": "unobserved unless independently qualified by the registered coverage"}


def next_action(root: Path) -> dict:
    current = state(root)
    if (current["decision"] and current["decision"]["result"]["decision"] in ("PROMOTE", "DROP")
            and all(row["status"] == "reviewed" for row in current["attempts"])):
        return {"action": "complete", "decision": current["decision"]["result"]["decision"],
                "discovery_dispositions": current["discoveries"], "learning_exhausted": False}
    for attempt in current["attempts"]:
        action = {"not_launched": "launch", "unknown_launch": "reconcile", "recorded": "review",
                  "invalid_evidence": "new_registration"}.get(attempt["status"])
        if action:
            return {"action": action, "attempt_id": attempt["id"], "arm": attempt["arm"], "case": attempt["case"]}
    if current["decision"]:
        return {"action": "complete", "decision": current["decision"]["result"]["decision"],
                "discovery_dispositions": current["discoveries"], "learning_exhausted": False}
    return {"action": "decide"}


def launch_intent(root: Path, attempt_id: str, plugin: Path) -> dict:
    import run as runner
    reg = registration(root)
    spec = attempt_spec(reg, attempt_id)
    current = next(row for row in state(root)["attempts"] if row["id"] == attempt_id)
    if current["status"] != "not_launched":
        raise ValueError("attempt already dispatched; reconcile it rather than retry")
    expected = reg["arms"][spec["arm"]]
    if runner.tree_digest(plugin) != expected["shiploop_build"]:
        raise ValueError("plugin bytes differ from the registered ShipLoop build")
    if not (plugin / "skills" / "shiploop" / "SKILL.md").is_file():
        raise ValueError("plugin does not contain the selected ShipLoop skill")
    output = root / "runs" / attempt_id
    if output.exists():
        raise ValueError("attempt output already exists; reconcile its identity")
    return append(root, "launch_intent", attempt_id=attempt_id, arm=spec["arm"], case=spec["case"],
                  output=str(output), plugin=str(plugin.resolve()), driver=expected["driver"],
                  registration_sha256=digest(root / "registration.json"))


def record_run(root: Path, attempt_id: str) -> dict:
    reg = registration(root)
    attempt_spec(reg, attempt_id)
    rows = events(root)
    if any(row["kind"] == "recorded" and row.get("attempt_id") == attempt_id for row in rows):
        raise ValueError("attempt already sealed")
    launches = [row for row in rows if row["kind"] == "launch_intent" and row.get("attempt_id") == attempt_id]
    if not launches:
        raise ValueError("no launch intent exists")
    output = Path(launches[-1]["output"])
    if listeners.case_alive(output):
        raise ValueError("the harness is still running; do not seal partial quality results")
    if not (output / "result.json").is_file():
        raise ValueError("no result receipt; launch remains unknown")
    files = {name: digest(output / name) for name in SEALED_FILES if (output / name).is_file()}
    return append(root, "recorded", attempt_id=attempt_id, output=str(output), files=files,
                  evidence=scorecard.run_receipt(output), started=launches[-1]["at"])


def sealed_run(root: Path, attempt_id: str) -> tuple[Path, dict]:
    records = [row for row in events(root) if row["kind"] == "recorded" and row.get("attempt_id") == attempt_id]
    if len(records) != 1:
        raise ValueError("attempt has no unique sealed receipt")
    record = records[0]
    output = Path(record["output"])
    for name, expected in record["files"].items():
        if digest(output / name) != expected:
            raise ValueError(f"sealed attempt evidence changed: {attempt_id}/{name}")
    observed = scorecard.run_receipt(output)
    if observed.get("unsafe_symlinks"):
        raise ValueError(f"sealed attempt evidence is unbounded: {attempt_id}/unsafe symlinks")
    if observed != record.get("evidence"):
        raise ValueError(f"sealed attempt evidence changed: {attempt_id}/review sources or delivered work")
    return output, record


def launch(root: Path, attempt_id: str, plugin: Path) -> dict:
    import run as runner
    intent = launch_intent(root, attempt_id, plugin)
    driver = intent["driver"]
    argv = ["--case", intent["case"], "--host", driver["host"], "--model", driver["model"],
            "--effort", driver["effort"], "--plugin-dir", intent["plugin"], "--output", intent["output"]]
    # No retries: a crash after dispatch leaves an intent for explicit reconciliation.
    result = runner.main(argv)
    append(root, "runner_returned", attempt_id=attempt_id, returncode=result)
    return record_run(root, attempt_id)


def review_attempt(root: Path, attempt_id: str) -> dict:
    import judge
    import review
    registration(root)
    if next(row for row in state(root)["attempts"] if row["id"] == attempt_id)["status"] == "reviewed":
        raise ValueError("review already recorded; preserve it and use a new assessment")
    output, _ = sealed_run(root, attempt_id)
    spec = attempt_spec(registration(root), attempt_id)
    # Every feedback exposure is retained, even if the reviewer or judge fails.
    exposure = append(root, "exposure", attempt_id=attempt_id, case=spec["case"], kind_of_feedback="detailed_review")
    assessment_id = f"epoch-{exposure['sequence']}"
    roles = json.loads((root / "roles.json").read_text())
    reviewed = review.review(output, **roles["reviewer"], assessment_id=assessment_id)
    judged = judge.judge(output, reviewed, **roles["judge"], assessment_id=assessment_id)
    sealed_run(root, attempt_id)  # Reviews cannot silently change the evidence that they interpret.
    routes = judge.admitted(reviewed, judged)
    receipt = f"receipts/{attempt_id}-{assessment_id}.json"
    write_json(root / receipt, {"review": reviewed, "judge": judged, "routes": routes})
    usable = (reviewed.get("validity") or {}).get("discovery_qualified") is True and (
        judged.get("validity") or {}).get("status") == "valid"
    event = append(root, "reviewed" if usable else "review_incomplete", attempt_id=attempt_id,
                   receipt=receipt, receipt_sha256=digest(root / receipt), routes=routes)
    for route in ("owner_challenges", "harness"):
        for finding in routes.get(route, []):
            append(root, "discovery_disposition", attempt_id=attempt_id, finding_id=finding.get("id"),
                   disposition="owner_decision" if route == "owner_challenges" else "separate_evaluator_experiment",
                   implementation="pending")
    return event


DISPOSITIONS = ("investigate", "defer", "reject", "propose_amendment", "owner_decision", "accept", "reopen")


def disposition(root: Path, attempt_id: str, finding_id: str, value: str, reason: str, owner_decision=None) -> dict:
    """Append an admission/reconsideration decision; this never edits the active spec or implements a finding."""
    registration(root)
    sealed_run(root, attempt_id)
    if value not in DISPOSITIONS or not isinstance(reason, str) or not reason.strip():
        raise ValueError("disposition needs a supported status and a non-empty rationale")
    reviews = [row for row in events(root) if row["kind"] == "reviewed" and row.get("attempt_id") == attempt_id]
    if not reviews:
        raise ValueError("no qualified discovery review is recorded for this attempt")
    receipt = reviews[-1]
    if digest(root / receipt["receipt"]) != receipt["receipt_sha256"]:
        raise ValueError("discovery receipt changed")
    payload = json.loads((root / receipt["receipt"]).read_text())
    findings = payload["review"].get("discoveries", [])
    finding = next((row for row in findings if row.get("id") == finding_id), None)
    if finding is None:
        raise ValueError("finding ID is not in the sealed review")
    admitted = payload.get("routes", {}).get("implementation", [])
    if value == "accept" and finding_id not in {row.get("id") for row in admitted} and not owner_decision:
        raise ValueError("direction-changing acceptance needs an owner-decision reference")
    prior = [row for row in events(root) if row["kind"] == "discovery_disposition"
             and row.get("attempt_id") == attempt_id and row.get("finding_id") == finding_id]
    return append(root, "discovery_disposition", attempt_id=attempt_id, finding_id=finding_id, disposition=value,
                  reason=reason, owner_decision=owner_decision, previous_sequence=prior[-1]["sequence"] if prior else None,
                  implementation="pending", specification_changed=False)


def decide(root: Path) -> dict:
    reg = registration(root)
    by_arm = {"control": [], "candidate": []}
    for attempt in reg["attempts"]:
        try:
            output, _record = sealed_run(root, attempt["id"])
        except (ValueError, OSError):
            continue  # strict promotion reports the missing attempt as unknown
        card = scorecard.score(output, required_case=reg["qualification"]["cases"][attempt["case"]])
        card["attempt_id"] = attempt["id"]
        # Qualification uses the runner's observed start, not the earlier dispatch intent.
        by_arm[attempt["arm"]].append((card, card.get("started")))
    result = promotion.decide(reg, by_arm["control"], by_arm["candidate"])
    # Even an otherwise qualified comparison cannot claim a completed learning cycle without its scoped reviews.
    incomplete = [a["id"] for a in state(root)["attempts"] if a["status"] != "reviewed"]
    if result["decision"] == "PROMOTE" and incomplete:
        result = {**result, "decision": "UNDECIDED", "reasons": ["required discovery review incomplete: " + ", ".join(incomplete)]}
    append(root, "decision", result=result)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "status", "next", "resume", "launch", "record", "reconcile", "review", "decide", "disposition"))
    parser.add_argument("--output", type=Path, required=True, help="external epoch directory")
    parser.add_argument("--registration", type=Path)
    parser.add_argument("--attempt")
    parser.add_argument("--plugin-dir", type=Path)
    parser.add_argument("--finding")
    parser.add_argument("--disposition", choices=DISPOSITIONS)
    parser.add_argument("--reason")
    parser.add_argument("--owner-decision", help="reference to the owner's explicit adoption decision")
    args = parser.parse_args(argv)
    root = args.output.resolve()
    try:
        if args.command == "init":
            if args.registration is None:
                parser.error("init requires --registration")
            result = initialise(root, args.registration)
        elif args.command in ("status", "next", "resume"):
            result = state(root) if args.command == "status" else next_action(root)
        else:
            with locked(root):
                if args.command == "decide":
                    result = decide(root)
                else:
                    if not args.attempt:
                        parser.error(f"{args.command} requires --attempt")
                    if args.command == "disposition":
                        result = disposition(root, args.attempt, args.finding, args.disposition, args.reason, args.owner_decision)
                    elif args.command == "launch":
                        if args.plugin_dir is None:
                            parser.error("launch requires --plugin-dir")
                        result = launch(root, args.attempt, args.plugin_dir)
                    elif args.command in ("record", "reconcile"):
                        result = record_run(root, args.attempt)
                    else:
                        result = review_attempt(root, args.attempt)
        print(json.dumps(result, indent=2))
        return promotion.EXIT.get(result.get("decision"), 0)
    except (ValueError, OSError) as exc:
        print(f"epoch: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
