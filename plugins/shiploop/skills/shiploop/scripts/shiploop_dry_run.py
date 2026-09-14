"""In-memory graph driver: real controller and stage prompts, synthetic work.

Nothing here invokes a shell, writes a run, or emits an importable certificate.
Expected paths are authored independently of the controller's routing table.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import _improve_managed as controller
from shiploop_packets import stage_instruction


# These are test expectations, deliberately not derived from PROFILE_STAGES.
CYCLES = {
    **{p: [f"{p}-{s}" for s in ("review", "plan", "apply", "verify", "commit")]
       for p in ("research", "behavior", "spec", "objective")},
    "step-plan": ["step-plan-review", "step-plan-revise", "step-plan-verify", "step-plan-commit"],
    "product": ["review", "improve-plan", "improve-plan-verify", "improve-apply",
                "test-refine", "test-author", "iteration-document", "verify", "carry-forward", "commit"],
}
SCOPE = "Real managed controller routes and shared stage instructions; synthetic work, no live packet context or outer DAG execution."
DUTIES = {
    "review": ["history", "tests"],
    "improve-plan": ["test_plan", "prerequisites"],
    "improve-plan-verify": ["planning-verify", "before Apply"],
    "test-refine": ["cases", "expected outcomes"],
    "test-author": ["executable tests", "case"],
    "iteration-document": ["documentation", "skill"],
    "skill-validate": ["executable examples", "failure"],
    "verify": ["lint", "test"],
    "carry-forward": ["discoveries", "system-test"],
    "commit": ["learnings", "review"],
    "final-verify": ["verify", "case"],
    "step-plan-revise": ["test criteria", "expected outcomes"],
}


def _edge(at, expect, **fields):
    return {"at": at, "event": "done", "expect": expect, **fields}


def _happy(profile, outcomes=("trivial", "trivial"), *, skill=False):
    cycle = list(CYCLES[profile])
    if skill:
        cycle.insert(cycle.index("verify"), "skill-validate")
    final = "final-verify" if profile == "product" else f"{profile}-finalize"
    steps = []
    for turn, outcome in enumerate(outcomes):
        successor = final if turn == len(outcomes) - 1 else cycle[0]
        for at, expect in zip(cycle, cycle[1:] + [successor]):
            row = _edge(at, expect)
            if at.endswith("commit"):
                row["outcome"] = outcome
            if at == "iteration-document" and skill:
                row["flags"] = {"documentation_disposition": "updated", "skill_disposition": "validate"}
            steps.append(row)
    steps.append(_edge(final, None, status="converged"))
    return {"name": profile, "profile": profile, "steps": steps}


def scenarios():
    result = {p: _happy(p) for p in CYCLES}
    result["product-skill"] = _happy("product", skill=True)
    result["product-material-reset"] = _happy("product", ("trivial", "material", "trivial", "trivial"))
    blocked = _happy("product")
    at = "test-author"
    idx = next(i for i, row in enumerate(blocked["steps"]) if row["at"] == at)
    blocked["steps"][idx:idx] = [
        _edge(at, None, event="blocked", status="blocked"),
        {"at": None, "event": "done", "error": "not active"},
        _edge(None, at, event="resume"),
    ]
    result["product-block-resume"] = blocked
    paused = _happy("product")
    at = "carry-forward"
    idx = next(i for i, row in enumerate(paused["steps"]) if row["at"] == at)
    paused["steps"][idx:idx] = [
        _edge(at, at, flags={"disposition": "pause"}, paused=True),
        {"at": at, "event": "done", "error": "paused"},
        _edge(at, at, event="resume"),
    ]
    result["product-pause-resume"] = paused
    repaired = _happy("product")
    prefix = repaired["steps"][:len(CYCLES["product"]) + len(CYCLES["product"]) - 1]
    result["product-repair"] = {"profile": "product", "steps": [
        *prefix, _edge("commit", "review", event="repair"), *_happy("product")["steps"]]}
    disposition = _happy("step-plan")
    disposition["steps"][:0] = [
        _edge("step-plan-review", "step-plan-disposition", flags={"disposition": "required"}),
        _edge("step-plan-disposition", "step-plan-review"),
    ]
    result["step-plan-disposition"] = disposition
    scope_repair = _happy("step-plan")
    scope_repair["steps"][:0] = [
        _edge("step-plan-review", "step-plan-disposition", event="repair",
              flags={"disposition": "required"}, paused=True),
        {"at": "step-plan-disposition", "event": "done", "error": "paused"},
        _edge("step-plan-disposition", "step-plan-disposition", event="resume"),
        _edge("step-plan-disposition", "step-plan-review"),
    ]
    result["step-plan-repair"] = scope_repair
    for status in ("needs-prerequisite", "needs-replan", "stopped"):
        result[status] = {"profile": "research", "steps": [
            _edge("research-review", None, event=status, status=status)]}
    for name, value in result.items():
        value["name"] = name
        for step in value["steps"]:
            if step["at"] in DUTIES:
                step["prompt_contains"] = list(DUTIES[step["at"]])
    return result


def _new_child(profile):
    # The pure API requires these fields. They are test tokens, never Git facts.
    return controller.new_child(controller.new_binding(
        parent_action="simulation-parent", child_action_id="simulation-child", profile=profile,
        input_identity={"simulation_only": True}, policy_digest="0" * 64,
        executor_digest="0" * 64, independent_review={"required": False, "fallback_allowed": False}))


def _apply(child, step, serial):
    phase = child["current_phase"]
    event = step.get("event", "done")
    refs = [f"simulation-only/event-{serial}"]
    if event == "resume":
        return controller.resume(child, reason="Simulated condition resolved", evidence_refs=refs)[0]
    if event in controller.INCOMPLETE_STATUSES:
        return controller.stop(child, event, "Simulated unfinished work", evidence_refs=refs)[0]
    if event not in ("done", "repair"):
        raise ValueError(f"unknown synthetic event: {event}")
    flags = step.get("flags")
    if flags is None:
        flags = {"step-plan-review": {"disposition": "not-required"},
                 "iteration-document": {"documentation_disposition": "not-needed", "skill_disposition": "not-needed"},
                 "carry-forward": {"disposition": "continue"}}.get(phase, {}) if event == "done" else {}
    payload = {"kind": "complete" if event == "done" else "repair", "phase": phase,
               "evidence_refs": refs, "flags": flags}
    if event == "repair":
        payload["reason"] = "Simulated correction requires another review"
    elif phase and phase.endswith("commit"):
        payload.update(audit_commit=f"{serial:040x}", completed_pass={
            "id": f"SIM-{serial}", "outcome": step.get("outcome", "trivial"),
            "verified": True, "commit": f"{serial:040x}", "evidence_ref": refs[0]}, open_findings=[])
    elif phase and (phase.endswith("finalize") or phase == "final-verify"):
        # Never expose these synthetic proof-shaped inputs as delivery evidence.
        output = {"identity_digest": "0" * 64, "simulation_only": True}
        payload.update(output_identity=output, fresh_evidence={
            "binding_sha256": child["binding_sha256"], "action": f"SIM-FINAL-{serial}",
            "identity_digest": output["identity_digest"], "result": "passed", "evidence_ref": refs[0],
            "checks": [{"id": "SIM-CHECK", "result": "passed", "evidence_ref": refs[0]}]})
    return controller.apply(child, payload)[0]


def run_scenario(scenario: dict[str, Any], api: dict[str, Any]):
    """Drive real transitions and compare independently declared expectations."""
    report = {"name": scenario.get("name", "custom"), "simulation_only": True,
              "scope": SCOPE, "ok": False, "events": []}
    try:
        steps = scenario.get("steps")
        if not isinstance(steps, list) or not 1 <= len(steps) <= 1000:
            raise ValueError("scenario needs 1..1000 explicit steps")
        child = _new_child(scenario["profile"])
        for serial, step in enumerate(steps, 1):
            if not isinstance(step, dict) or "at" not in step or not ("expect" in step or "error" in step):
                raise ValueError("each step needs at and expect (or error)")
            if "error" in step and (not isinstance(step["error"], str) or not step["error"].strip()):
                raise ValueError("error must name an expected rejection")
            terms = step.get("prompt_contains", [])
            if not isinstance(terms, list) or not all(isinstance(term, str) and term for term in terms):
                raise ValueError("prompt_contains must be a list of nonempty duty fragments")
            phase = child["current_phase"]
            prompt = stage_instruction(phase, api, managed=True) if phase else None
            row = {"sequence": serial, "from": phase, "event": step.get("event", "done"),
                   "expected": step.get("expect"), "prompt": prompt}
            report["events"].append(row)
            if phase != step["at"]:
                raise ValueError(f"event {serial}: expected current {step['at']!r}, got {phase!r}")
            if phase and not prompt:
                raise ValueError(f"event {serial}: missing production prompt for {phase}")
            for term in terms:
                if not isinstance(term, str) or term.casefold() not in (prompt or "").casefold():
                    raise ValueError(f"event {serial}: prompt missing required duty {term!r}")
            previous = child
            try:
                child = _apply(child, step, serial)
            except controller.ManagedImproveError as exc:
                if not step.get("error") or step["error"].casefold() not in str(exc).casefold():
                    raise
                row["rejected"] = str(exc)
                child = previous
            else:
                if "error" in step:
                    raise ValueError(f"event {serial}: expected rejection, transition was accepted")
            row.update(to=child["current_phase"], status=child["status"], paused=child["paused"])
            row["next_prompt"] = stage_instruction(child["current_phase"], api, managed=True) if child["current_phase"] else None
            if "error" not in step and (child["current_phase"] != step["expect"]
                    or child["status"] != step.get("status", "active")
                    or child["paused"] != step.get("paused", False)):
                raise ValueError(f"event {serial}: expected {step.get('expect')!r}/{step.get('status', 'active')}, "
                                 f"got {child['current_phase']!r}/{child['status']} paused={child['paused']}")
        report.update(ok=True, simulated_status=child["status"])
    except (ValueError, KeyError, TypeError) as exc:
        report["error"] = str(exc)
    return report


def add_arguments(parser):
    selected = parser.add_mutually_exclusive_group()
    selected.add_argument("--scenario", choices=("all", *scenarios()), default="all")
    selected.add_argument("--script", help="JSON file with a profile and explicit expected transition steps")
    parser.add_argument("--format", choices=("summary", "json", "markdown"), default="summary")
    parser.add_argument("--list", action="store_true", help="list built-in graph scenarios")


def run(args, api):
    if args.list:
        print("\n".join(scenarios()))
        return 0
    try:
        if args.script:
            value = json.loads(Path(args.script).read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("scenario must be a JSON object")
            selected = [value]
        else:
            available = scenarios()
            selected = list(available.values()) if args.scenario == "all" else [available[args.scenario]]
        reports = [run_scenario(value, api) for value in selected]
    except (OSError, ValueError) as exc:
        print(f"Graph dry-run failed: {exc}")
        return 2
    if args.format == "json":
        print(json.dumps({"simulation_only": True, "scope": SCOPE, "scenarios": reports}, indent=2))
    else:
        print("SIMULATION ONLY — no implementation, tests, commits or publication executed.\n" + SCOPE)
        for report in reports:
            print(f"\n{'PASS' if report['ok'] else 'FAIL'} {report['name']}: {len(report['events'])} events; "
                  f"simulated status: {report.get('simulated_status', 'mismatch')}")
            if args.format == "markdown":
                for row in report["events"]:
                    print(f"\n### {row['sequence']}. {row['from']} — {row['event']} → {row.get('to', 'ERROR')}\n")
                    if row["prompt"]:
                        print(row["prompt"])
                    if row.get("rejected"):
                        print("\nExpected rejection: " + row["rejected"])
            if report.get("error"):
                print(report["error"])
    return 0 if all(row["ok"] for row in reports) else 1
