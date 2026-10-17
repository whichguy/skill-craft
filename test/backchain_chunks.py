#!/usr/bin/env python3
"""Prepare native Backchain cases and check retained outputs; never launch a model.

These are fixed regression fixtures, not an open-ended semantic judge. The
mechanical checks complement an independent read of the review and final plan.
Historical outcome campaigns and benchmark populations are deliberately separate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shlex
import sys

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "test/fixtures/backchain-chunks"
SKILL = ROOT / "skills/backchain"
LOOP = ROOT / "skills/improve/runtime/until-loop"
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_backchain_graph as graph  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fixtures():
    return {p.stem: read(p) for p in sorted(FIXTURES.glob("*.json"))}


def source_hashes():
    paths = [Path(__file__).resolve(), Path(graph.__file__).resolve()]
    paths += [p for root in (SKILL, LOOP) for p in root.rglob("*")
              if p.is_file() and "__pycache__" not in p.parts]
    paths += sorted(FIXTURES.glob("*.json"))
    return {str(p): digest(p) for p in sorted(set(paths))}


def validate(input_path, output_path, receipt_path):
    """Package a copy, retaining raw revision and candidate-specific evidence."""
    if len({Path(p).resolve() for p in (input_path, output_path, receipt_path)}) != 3:
        raise ValueError("input, output and receipt must be distinct")
    raw = read(input_path)
    packaged = graph.package(raw)
    write(output_path, packaged)
    structure = graph.validate_structure(packaged)
    receipt = {"input_sha256": digest(input_path), "output_sha256": digest(output_path),
               "structure": structure, "completion": graph.completion_status(packaged, structure),
               "validator_sha256": digest(graph.__file__)}
    write(receipt_path, receipt)
    return structure["ok"] and receipt["completion"]["status"] == "complete"


def packet(case, directory):
    plan = case["plan"]
    result = {
        "interface": "backchain-caller/v1", "action": "review", "stage": "audit",
        "action_id": "chunk-" + case["id"], "owner": "chunk-regression",
        "workflow_stage": "standalone",
        "locator_bases": [{"id": "case", "observed_absolute_locator": str(directory)}],
        "original_request": case["source"],
        "selection": {"skill_locator": str(SKILL / "SKILL.md"),
                      "skill_sha256": digest(SKILL / "SKILL.md")},
        "candidate": {"id": case["id"], "input_kind": "existing", "locator": "candidate.json",
                      "locator_base": "case", "resolved_locator": str(directory / "candidate.json"),
                      "input_sha256": digest(directory / "candidate.json"), "output_sha256": "unavailable"},
        "sources": [{"id": "SRC-1", "locator": "source.md", "locator_base": "case",
                     "resolved_locator": str(directory / "source.md"), "authority": "normative",
                     "provenance": "user-provided", "currentness": "current", "revision": "chunks-v1",
                     "sha256": digest(directory / "source.md")}],
        "requirements": [], "lens_findings": [], "open_questions": [], "prior_findings": [],
        "dependency_neighborhood": {"included_step_ids": [s["id"] for s in plan["steps"]],
            "included_edge_keys": [f'{s["id"]}<-{i["from"] or "null"}'
                                   for s in plan["steps"] for i in s["inputs"]]},
        "evidence": [{"id": "E-1", "claim": plan["initial_state"][0],
                      "source_ids": ["SRC-1"], "verified": True}],
    }
    if case["edit_bounds"] is not None:
        result["edit_bounds"] = case["edit_bounds"]
    return result


def prepare(output, case_ids):
    output = Path(output).resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError("output must be outside the source checkout")
    cases = fixtures()
    selected = case_ids or list(cases)
    if len(set(selected)) != len(selected) or any(k not in cases for k in selected):
        raise ValueError("select unique known cases: " + ", ".join(cases))
    hashes = source_hashes()
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"schema": "backchain-chunks/v1", "source_hashes": hashes, "cases": {}}
    for key in selected:
        case = cases[key]
        directory = output / key
        directory.mkdir()
        work = directory / "output"
        work.mkdir()
        write(directory / "candidate.json", case["plan"])
        (directory / "source.md").write_text(case["source"] + "\n")
        inputs = [directory / "candidate.json", directory / "source.md"]
        if case["route"] == "source-aware":
            caller = packet(case, directory)
            write(directory / "audit-packet.json", caller)
            caller.update(action="repair", stage="revise")
            write(directory / "revise-packet.json", caller)
            inputs += [directory / "audit-packet.json", directory / "revise-packet.json"]
        route = ("Source-aware repair/revise; use the supplied audit and revise packets inside each callback."
                 if case["route"] == "source-aware" else
                 "Compatibility-native elaboration; no source-aware edit authority is supplied.")
        command = " ".join(shlex.quote(str(p)) for p in
                           (sys.executable, Path(__file__).resolve(), "validate", "--input",
                            work / "raw-plan.json", "--output", work / "plan.json",
                            "--receipt", work / "validation.json"))
        request = f"""Use the selected Backchain on the existing candidate after enrichment. {route}
Read these frozen inputs: {', '.join(str(p) for p in inputs)}.
Selected Backchain: {SKILL / 'SKILL.md'}
Selected actual Until Loop: {LOOP / 'ADAPTER.md'}

Backchain standalone Until Loop binding: chunk-regression-{key}
Backchain passes: one

This is a full plan-only dependency review/fix/check workflow using the selected actual
Until Loop runtime and its package-relative reference. Follow its issued actions. Keep
the request, input, normative source and edit authority frozen. Review all scoped work,
including unchanged steps, and run the required technical lens screen. Use the skill's
one-pass exit condition. An unavailable necessary repair must stop incomplete with a
specific recovery action. Do not regenerate or replace a draft inside this binding.

Preserve the exact condition strings when moving existing produces; this fixed-vocabulary
fixture does not require renaming conditions. Choose step IDs, statements, new checks and
graph structure yourself. Original confirmations remain governed by the selected skill.
All product checks are planned, never executed. No product files, Git writes, installs,
advisors, nested agents or external models. Write only under {work} and the runtime's
own temporary state. Do not read memory, prior runs, eval expectations, test fixtures or
the acceptance evaluator. This request and the named raw inputs are self-contained.

Save the start contract as output/start.json before invoking the runtime. Its workspace
is {work}. Use output/terminal.json as the runtime-owned --receipt destination; never
write it yourself. Save every exact stdout packet and submitted report separately. Save
terminal stdout also as output/terminal-stdout.json. Retain one fresh review record for
each callback, including audit findings, lens reads, split/keep rationale, source-linked
old-to-new mappings and the actual post-repair check. Do not overwrite earlier records.
Each active callback is one fresh full Backchain review/fix/check cycle. If an exit-check
repair returns the loop to an active callback, run a fresh full Backchain cycle over the
current artifacts even if the plan is byte-identical; do not make it a check-only callback.
Retain one uniquely named review record for every callback, and include ALL callback records
in domain.review_records with each absolute path and actual SHA-256, not only the latest or
qualifying records.

Save the raw plan as output/raw-plan.json (copy the input if unchanged), then run:
{command}
Keep raw-plan.json as the last actual plan revision before packaging. Do not replace it
with packaged plan.json waves during a later no-change review; the validation receipt's
input_sha256 must continue to match the bytes of raw-plan.json supplied to that invocation.
candidate.input_sha256 always identifies this run's frozen candidate.json bytes, not a
callback input or final candidate. The validation receipt records input_sha256 (raw-plan.json
bytes), output_sha256 (packaged plan.json bytes), structure.ok (structural result),
completion.status (goal-closure result), and validator_sha256 (the selected graph validator's
bytes at {Path(graph.__file__).resolve()}, not this CLI wrapper). A blocked plan may be
structurally valid but incomplete because it honestly records unresolved gaps. This checks
structure and goal closure only, not chunk suitability or product behavior.
The plan-only final candidate is output/plan.json. Before the cycle's done report, save
output/domain.json with candidate: {{input_sha256, output_sha256}}, planning_gaps: [strings],
next_action: string, and review_records: [{{path: absolute record path, sha256: actual hash}}].
The candidate object may retain additional identity metadata, but both digest fields must
identify the frozen candidate.json input and the exact packaged plan.json output.
The output hash is the bytes of plan.json. Use actual results, including unresolved gaps.

Include observable exit checks for retained cycle evidence, final validation and exact
candidate identity in the runtime contract, then run the issued verify_script unchanged
before any satisfied report. Keep semantic judgments in the exit condition. Do not turn
an expected missing-authority stop into success. The external test deadline is 15 minutes;
if reached, stop incomplete and preserve evidence. No invented pass ceiling.

Parent request: {directory / 'request.md'}
Latest packet / terminal receipt: {work / 'terminal.json'}
Return route: artifacts under {work}, plus the native final answer with actual disposition.
"""
        (directory / "request.md").write_text(request)
        inputs.append(directory / "request.md")
        manifest["cases"][key] = {"eval_id": case["eval_id"],
            "inputs": {str(p.relative_to(output)): digest(p) for p in inputs}}
    write(output / "manifest.json", manifest)
    return manifest


def _normalized_text(value):
    return " ".join(value.split()).casefold()


def _source_contains(case, value):
    return _normalized_text(value) in _normalized_text(case["source"])


def _same_except(before, after, excluded):
    return (isinstance(before, dict) and isinstance(after, dict)
            and before.keys() == after.keys()
            and all(before[key] == after[key] for key in before if key not in excluded))


def _keep_inputs_are_authorized(case, plan):
    """A keep may add only grounded initial-fact edges within exact edit bounds."""
    original = case["plan"]
    if not _same_except(original, plan, {"steps", "parallel_groups"}):
        return False
    if len(plan["steps"]) != len(original["steps"]):
        return False
    bounds = case.get("edit_bounds") or {}
    eligible = (set(bounds.get("provisional_step_ids", []))
                - set(bounds.get("protected_step_ids", []))
                - set(bounds.get("running_or_completed_step_ids", [])))
    initial = set(original["initial_state"])
    for before, after in zip(original["steps"], plan["steps"]):
        if not _same_except(before, after, {"inputs"}):
            return False
        old_inputs, new_inputs = before["inputs"], after["inputs"]
        if not isinstance(new_inputs, list):
            return False
        additions = list(new_inputs)
        for edge in old_inputs:
            if edge not in additions:
                return False
            additions.remove(edge)
        if not additions:
            continue
        if before["id"] not in eligible or bounds.get("allow_new_edges") is not True:
            return False
        known = {item.get("need") for item in old_inputs}
        for item in additions:
            if (not isinstance(item, dict) or item.keys() != {"from", "need"}
                    or item["from"] is not None or not isinstance(item["need"], str)
                    or not item["need"].strip() or item["need"] not in initial
                    or not _source_contains(case, item["need"]) or item["need"] in known):
                return False
            known.add(item["need"])
    return True


def _usable_new_confirmation(entry, produce):
    if not isinstance(entry, dict) or entry.keys() != {"produces", "by", "level"}:
        return False
    by = entry["by"]
    if not isinstance(by, str):
        return False
    method, marker, expected = by.casefold().partition("pass when")
    return (entry["produces"] == produce and bool(method.strip()) and bool(marker) and bool(expected.strip())
            and not by.strip().casefold().startswith("confirm by:")
            and produce.casefold() not in by.casefold()
            and entry["level"] in ("execute", "inspect"))


def _blocked_preserves_obligations(case, plan, allowed_step_ids):
    """Check additive obligation preservation; semantic widening needs independent review."""
    original = case["plan"]
    if not _same_except(original, plan, {"steps", "parallel_groups", "unresolved"}):
        return False
    old_gaps, new_gaps = original["unresolved"], plan["unresolved"]
    if not isinstance(new_gaps, list) or new_gaps[:len(old_gaps)] != old_gaps:
        return False
    # Recording a residual gap does not authorize an implementation change.
    # The graph validator checks entry shape/references; a semantic review must
    # still establish that each added gap is real and grounded in the source.
    if any(gap in new_gaps[:index] for index, gap in enumerate(new_gaps)):
        return False
    if len(plan["steps"]) != len(original["steps"]):
        return False
    original_outputs = {produce for step in original["steps"] for produce in step["produces"]}
    added_outputs = set()
    for before, after in zip(original["steps"], plan["steps"]):
        if before.keys() != after.keys() or before["id"] != after["id"]:
            return False
        if before["id"] not in allowed_step_ids:
            if before != after:
                return False
            continue
        if not _same_except(before, after, {"statement", "produces", "confirm"}):
            return False
        old_produces, new_produces = before["produces"], after["produces"]
        old_confirms, new_confirms = before["confirm"], after["confirm"]
        if (not isinstance(new_produces, list) or new_produces[:len(old_produces)] != old_produces
                or not isinstance(new_confirms, list)
                or new_confirms[:len(old_confirms)] != old_confirms):
            return False
        added_produces = new_produces[len(old_produces):]
        added_confirms = new_confirms[len(old_confirms):]
        if len(added_produces) != len(added_confirms):
            return False
        if after["statement"] != before["statement"] and (
                not isinstance(after["statement"], str) or not after["statement"].strip()
                or not added_produces):
            return False
        for produce in added_produces:
            if (not isinstance(produce, str) or not produce.strip()
                    or produce in original_outputs or produce in added_outputs):
                return False
            added_outputs.add(produce)
            matching = [entry for entry in added_confirms
                        if isinstance(entry, dict) and entry.get("produces") == produce]
            if len(matching) != 1 or not _usable_new_confirmation(matching[0], produce):
                return False
    return True


def check_plan(case, plan, raw):
    failures = []
    def require(ok, message):
        if not ok:
            failures.append(message)
    original = case["plan"]
    for key in ("goal", "goal_needs", "initial_state"):
        require((key in original) == (key in plan) and original.get(key) == plan.get(key),
                f"{key} presence/value changed")
    require(graph.validate_structure(plan)["ok"], "invalid final structure/waves")
    completion = graph.completion_status(plan)
    behavior = case["expected"]["behavior"]
    if behavior == "blocked":
        require(completion["ok"] and not completion["open_goal_needs"],
                "blocked candidate lost declared goal coverage")
    else:
        require(completion["status"] == "complete", "incomplete structural goal closure")
    require(graph.package(raw) == plan, "packaging changed more than parallel_groups")
    if behavior == "keep":
        require(_keep_inputs_are_authorized(case, plan),
                "candidate changed outside the expected keep/authority boundary")
        return failures
    if behavior == "blocked":
        if case["route"] == "legacy":
            allowed = {s["id"] for s in original["steps"] if s["origin"] == "seed"}
        else:
            bounds = case.get("edit_bounds") or {}
            allowed = (set(bounds.get("provisional_step_ids", []))
                       - set(bounds.get("protected_step_ids", []))
                       - set(bounds.get("running_or_completed_step_ids", [])))
        require(_blocked_preserves_obligations(case, plan, allowed),
                "candidate changed outside the blocked route's monotonic widening boundary")
        return failures
    require(raw.get("parallel_groups") == [], "revision retained stale parallel_groups")
    steps = {s["id"]: s for s in plan["steps"]}
    before = {s["id"]: s for s in original["steps"]}
    require(steps.get("S3") == before["S3"], "unrelated help step changed")
    conditions = [p for s in original["steps"] for p in s["produces"]]
    owners = {p: [s for s in plan["steps"] if p in s["produces"]] for p in conditions}
    require(all(len(v) == 1 for v in owners.values()), "lost/duplicated original produce owner")
    for step in plan["steps"]:
        require(all(len([c for c in step.get("confirm", []) if c["produces"] == p
                         and c["by"].strip() and c["level"] in ("execute", "inspect")]) == 1
                    for p in step["produces"]), f'{step["id"]} lacks usable exact confirmations')
    if not all(len(v) == 1 for v in owners.values()):
        return failures
    contract, reader, renderer, wiring = [owners[p][0] for p in before["S1"]["produces"]]
    roles = [contract, reader, renderer, wiring]
    require(len({s["id"] for s in roles}) == 4, "independent implementation deliverables remain bundled")
    def suppliers(step):
        return {i["from"] for i in step["inputs"] if i["from"] is not None}
    require(suppliers(contract) == set(), "record contract has a false dependency")
    require(suppliers(reader) == {contract["id"]}, "reader must consume only record contract")
    require(suppliers(renderer) == {contract["id"]}, "renderer must consume only record contract")
    require(suppliers(wiring) == {reader["id"], renderer["id"]}, "integration must consume both branches")
    e2e = owners[before["S2"]["produces"][0]][0]
    require(all(c in e2e["confirm"] for c in before["S2"]["confirm"]),
            "unauthorized S2 confirmation change")
    # Integration may own its whole-feature check, or supply a distinct check.
    # This asserts useful boundaries rather than a universal step-count quota.
    require(e2e["id"] == wiring["id"] or suppliers(e2e) == {wiring["id"]},
            "whole-feature verification lost its integration supplier")
    require(all(s["produces"] for s in steps.values()) and
            set(p for s in steps.values() for p in s["produces"]) == set(conditions),
            "extra wrapper, duplicate work, or unrequested produce")
    for step in (contract, reader, renderer):
        require(all("import-e2e" not in c["by"] for c in step.get("confirm", [])),
                f'{step["id"]} confirmation waits for downstream whole-feature implementation')
    return failures


def check_case(case, directory):
    """Fail closed on missing, malformed, stale or contradictory retained evidence."""
    work = directory / "output"
    try:
        plan, raw = read(work / "plan.json"), read(work / "raw-plan.json")
        failures = check_plan(case, plan, raw)
        domain = read(work / "domain.json")
        terminal = read(work / "terminal.json")
        stdout = read(work / "terminal-stdout.json")
        start = read(work / "start.json")
        validation = read(work / "validation.json")
        def require(ok, message):
            if not ok:
                failures.append(message)
        expected = case["expected"]["runtime_status"]
        require(terminal == stdout, "terminal receipt differs from retained runtime stdout")
        require(terminal["status"] == expected, "incorrect runtime terminal disposition")
        require(Path(terminal["workspace"]).resolve() == work.resolve(), "terminal workspace mismatch")
        require(terminal["progress"]["required_trivial_reviews"] == 0, "one-pass binding gate changed")
        require(start["required_trivial_reviews"] == 0 and Path(start["workspace"]).resolve() == work.resolve(),
                "start contract changed one-pass binding/workspace")
        candidate = domain["candidate"]
        require(isinstance(candidate, dict)
                and candidate.get("input_sha256") == digest(directory / "candidate.json")
                and candidate.get("output_sha256") == digest(work / "plan.json"),
                "domain evidence candidate identity mismatch")
        require(validation["input_sha256"] == digest(work / "raw-plan.json") and
                validation["output_sha256"] == digest(work / "plan.json") and
                validation["validator_sha256"] == digest(graph.__file__) and
                validation["structure"] == graph.validate_structure(plan) and
                validation["completion"] == graph.completion_status(plan), "stale or incorrect validation receipt")
        report = terminal["last_report"]
        if expected == "complete":
            require(domain["planning_gaps"] == [], "complete claim has open planning gaps")
            require(report["exit_assessment"] == "satisfied" and
                    report["continuation_assessment"] == "allowed", "complete report is not satisfied/allowed")
            checks = terminal["last_check_results"]
            require(bool(checks) and all(c["passed"] is True and c["exit_code"] == 0 for c in checks),
                    "completion lacks successful runtime exit checks")
        else:
            gaps, recovery = domain["planning_gaps"], domain["next_action"]
            require(isinstance(gaps, list) and any(isinstance(g, str) and g.strip() for g in gaps)
                    and isinstance(recovery, str) and bool(recovery.strip()),
                    "missing-authority stop lost its gap/recovery")
            require(report["continuation_assessment"] in ("blocked", "cancelled")
                    and report["exit_assessment"] in ("unsatisfied", "unknown"),
                    "missing-authority case did not stop incomplete")
        records = domain["review_records"]
        require(len(records) == terminal["progress"]["action_number"] >= 1,
                "missing callback review records")
        require(len({r["path"] for r in records}) == len(records), "duplicate review records")
        for entry in records:
            path = Path(entry["path"]).resolve()
            require(work.resolve() in path.parents and digest(path) == entry["sha256"],
                    "missing, overwritten, or outside-workspace review record")
        return failures
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return [f"incomplete/malformed evidence: {exc}"]


def check_run(directory, selected=None):
    directory = Path(directory).resolve()
    manifest = read(directory / "manifest.json")
    source_ok = manifest["source_hashes"] == source_hashes()
    cases = fixtures()
    ids = selected or list(manifest["cases"])
    if any(k not in manifest["cases"] for k in ids):
        raise ValueError("case not prepared in this run")
    results = {}
    for key in ids:
        failures = [] if source_ok else ["source changed since run preparation"]
        for name, sha in manifest["cases"][key]["inputs"].items():
            path = directory / name
            if not path.is_file() or digest(path) != sha:
                failures.append("frozen input changed: " + name)
        failures += check_case(cases[key], directory / key)
        results[key] = {"passed": not failures, "failures": failures}
    return {"passed": all(r["passed"] for r in results.values()), "cases": results,
            "scope": "mechanical fixture and lifecycle checks; independent semantic review still required"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("prepare", help="write frozen inputs and native-agent requests; no model launch")
    p.add_argument("--output", required=True)
    p.add_argument("--case", action="append", choices=list(fixtures()))
    p = subs.add_parser("validate", help="structural packaging check used by each live subject")
    p.add_argument("--input", required=True); p.add_argument("--output", required=True)
    p.add_argument("--receipt", required=True)
    p = subs.add_parser("check", help="check retained native outputs without launching a model")
    p.add_argument("--run", required=True); p.add_argument("--case", action="append")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(args.output, args.case)
            print(json.dumps({"prepared": list(result["cases"]), "output": str(Path(args.output).resolve())}))
            return 0
        if args.command == "validate":
            return 0 if validate(args.input, args.output, args.receipt) else 1
        result = check_run(args.run, args.case)
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"backchain-chunks: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
