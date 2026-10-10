#!/usr/bin/env python3
"""Measurement 1 of the 2026-10-10 commit spike: how much room each Until Loop contract has.

Question: does the Improve-commit rule (plan section 2.2) fit in the frozen Improve contract, whose
size is capped by shiploop_loop_contract.CONTRACT_BUDGET?

Method (read-only; nothing under skills/ is changed, no model or host CLI is started):
  1. For every saved ShipLoop run under --runs-root whose state has completed Improve children, rebuild
     each child's contract with the REAL builder, shiploop_navigator.improve_start_contract, from the
     saved state, the child's own binding record and its saved opening.md. The rebuilt contract is
     compared with the child's saved start.json (the contract that was actually frozen).
  2. Size every contract with shiploop_loop_contract.compact_bytes / text_bytes (never a second
     serializer).
  3. Apply each candidate wording of the commit rule to the rebuilt contract's authority text (the one
     place the contract talks about committing and callbacks) and re-measure, so escaping and the
     child's real paths are counted.
  4. Size the test-loop and quality-loop contracts from the contract files those loops saved.

Usage:
  PYTHONDONTWRITEBYTECODE=1 python3 measure_contract_headroom.py [--runs-root DIR] [--out FILE]
"""
from __future__ import annotations

import argparse
import copy
import glob
import json
import os
import re
import statistics
import sys
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "skills" / "shiploop" / "scripts"))

import shiploop_loop_contract as lc  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_standalone_improve as standalone  # noqa: E402
import shiploop_store as store  # noqa: E402

# The runs the brief names: 20261008 r1-r3, 20261009 and 20261010 (each has a protocol 4 state).
RUN_DAYS = ("20261008", "20261009", "20261010")
OLD_CALLBACK_CLAUSE = "The child never runs a ShipLoop callback: after the terminal packet the parent runs the return in "
PLAN_SENTENCE = (
    "The child never runs a ShipLoop callback except improve-commit: commit each iteration's changes only with "
    "{command}, message at {path} with a 'Key learnings' section, optional 'Learned-from: <full commit ID> "
    "<what it contributed>' lines.")
LESSON_CLAUSE = "a 'Key learnings' section and optional 'Learned-from: <full commit ID> <what it contributed>' lines"

# Candidate wordings. Each is the text that replaces OLD_CALLBACK_CLAUSE + <parent return path> + "." in the
# authority; {pr} is the parent-return.md path the contract already names, {command}/{path} the real
# improve-commit command line and message path.
VARIANTS = {
    # The plan's authority sentence, verbatim, then the existing "parent runs the return" clause.
    "full_plan_text": (
        PLAN_SENTENCE + " After the terminal packet the parent runs the return in {pr}."),
    # Same rule with the message path stated once (the command already carries --message=<path>).
    "full_path_once": (
        "The child never runs a ShipLoop callback except improve-commit: commit each iteration's changes only with "
        "{command} (the message file has " + LESSON_CLAUSE + "). After the terminal packet the parent runs the "
        "return in {pr}."),
    # Lessons requirement only; assumes the command line is carried somewhere else (it is not today).
    "lessons_only": (
        "The child never runs a ShipLoop callback except improve-commit, whose message has " + LESSON_CLAUSE
        + ". After the terminal packet the parent runs the return in {pr}."),
    # Command lives in parent-return.md (a file the contract already lists as a resource); the contract
    # carries the rule and the pointer, and names that path once. It keeps the plan's "changes only with".
    "pointer_to_parent_return": (
        "The child never runs a ShipLoop callback except improve-commit; its command and the parent return are in "
        "{pr}: commit each iteration's changes only with that command; the message has " + LESSON_CLAUSE
        + ". The parent runs the return after the terminal packet."),
}

# The wordings that restate the plan's authority sentence must keep "commit each iteration's changes only with": without
# "'s changes only", the sentence read next to the contract's "no empty commit" tells a child to commit no-change
# iterations (the Improve card says a no-change review gets no empty commit). A paraphrase that drops it fails here.
for _name in ("full_plan_text", "full_path_once", "pointer_to_parent_return"):
    assert "commit each iteration's changes only with" in VARIANTS[_name], _name + " dropped 'changes only with'"


def stats(values):
    values = sorted(values)
    if not values:
        return None
    return {"n": len(values), "min": values[0], "median": statistics.median(values), "max": values[-1]}


def load_state(path: Path):
    return store.loads(path.read_text(encoding="utf-8"))


def child_binding(record, action):
    """The child's binding exactly as improve-bind stored it (the saved improve_results record carries every field)."""
    return {"version": 1, "action_id": action, "stage": record["stage"], "binding_id": record["binding_id"],
            "workspace": record["workspace"], "seed_result": record.get("seed_result", {}),
            "skill": record["skill"], "contract_marker": standalone._binding_marker(record["binding_id"])}


def find_states(runs_root: Path):
    found = []
    for day in RUN_DAYS:
        found += sorted(glob.glob(str(runs_root / day / "*" / ".shiploop-runs" / "*" / "run" / "state.md")))
    return [Path(p) for p in found]


def apply_variant(contract, name, command, message_path, parent_return):
    """The contract with one candidate wording in place of the existing callback clause."""
    changed = copy.deepcopy(contract)
    authority = changed["context"]["authority"]
    old = OLD_CALLBACK_CLAUSE + parent_return + "."
    if old not in authority:
        raise AssertionError("existing callback clause not found in authority")
    new = VARIANTS[name].format(command=command, path=message_path, pr=parent_return)
    changed["context"]["authority"] = authority.replace(old, new)
    return changed


def lengthen(contract, workspace, run_dir, extra):
    """The contract with the worktree path and the run directory path `extra` characters longer everywhere."""
    text = json.dumps(contract)
    text = text.replace(workspace, workspace + "w" * extra).replace(run_dir, run_dir + "r" * extra)
    return json.loads(text)


def minimal_opening():
    return "\n\n".join("## " + name + "\nx" for name in nav.OPENING_SECTIONS) + "\n"


def measure_child(root: Path, state, action, record, case_dir: Path):
    child = child_binding(record, action)
    run_state = dict(state, active_improve=child)
    receipt_dir = standalone.receipt_path(child).parent
    opening_path = receipt_dir / "opening.md"
    saved_path = receipt_dir / "start.json"
    if not (opening_path.is_file() and saved_path.is_file()):
        return None, "opening.md or start.json not saved"
    opening = opening_path.read_text(encoding="utf-8")
    contract = nav.improve_start_contract(None, root, run_state, opening)
    saved = json.loads(saved_path.read_text(encoding="utf-8"))
    sections = nav._opening_sections(opening)
    parent_return = str(receipt_dir / "parent-return.md")
    message_path = str(nav.improve_commit_message_path(child))
    package_root = Path(child["skill"]["skill_card"]).parents[1] / "shiploop"
    command = nav._callback(SimpleNamespace(PACKAGE_ROOT=package_root), root, "improve-commit", action=action,
                            message=message_path)
    packet = root / "packets" / (action + "-improve.md")
    printed = None
    if packet.is_file():
        match = re.search(r"then run: (python3 .*?) \. ShipLoop commits exactly", packet.read_text(encoding="utf-8"))
        printed = match.group(1) if match else None
    built = command
    if printed:
        command = printed  # the real packet line wins: a Grok run prints its installed-plugin script path
    total = lc.compact_bytes(contract)
    row = {
        "stage": child["stage"], "action": action,
        "bytes": total, "headroom": lc.CONTRACT_BUDGET - total,
        "saved_bytes": lc.compact_bytes(saved), "identical_to_saved": contract == saved,
        "model_written": sum(lc.text_bytes(body) for body in sections.values()),
        "sections": {name: lc.text_bytes(body) for name, body in sections.items()},
        "fields": {"work": lc.text_bytes(contract["work"]), "exit": lc.text_bytes(contract["exit_condition"]),
                   "repeat": lc.text_bytes(contract["repeat_condition"]),
                   "request": lc.text_bytes(contract["context"]["request"]),
                   "scope": lc.text_bytes(contract["context"]["scope"]),
                   "authority": lc.text_bytes(contract["context"]["authority"]),
                   "environment": lc.text_bytes(contract["context"]["environment"]),
                   "resources": lc.compact_bytes({"r": contract["context"]["resources"]}) - len('{"r":}')},
        "resources": len(contract["context"]["resources"]),
        "workspace_chars": len(child["workspace"]), "run_dir_chars": len(str(root)),
        "workspace_occurrences": json.dumps(contract, separators=(",", ":")).count(child["workspace"]),
        "run_dir_occurrences": json.dumps(contract, separators=(",", ":")).count(str(root)),
        "authority_names_improve_commit_in_opening": "improve-commit" in sections["Authority"],
        "opening_mentions_key_learnings": "key learning" in opening.lower(),
        "frozen_authority_says_child_never_runs_a_callback": "The child never runs a ShipLoop callback" in saved["context"]["authority"],
        "command_chars": len(command), "command_source": "printed packet line" if printed else "built with _callback",
        "packet_saved": packet.is_file(), "packet_prints_improve_commit": printed is not None,
        "built_command_equals_printed": (built == printed) if printed else None,
        "message_path_chars": len(message_path),
    }
    # Candidate wordings, measured in situ on this child's real contract.
    row["variants"] = {}
    for name in VARIANTS:
        changed = apply_variant(contract, name, command, message_path, parent_return)
        row["variants"][name] = lc.compact_bytes(changed) - total
        # A wording that leaves the contract unchanged would report "fits" for nothing (apply_variant not replacing).
        assert row["variants"][name] > 0, name + " added no bytes to " + action
    # The same plan sentence placed in the work string instead of the authority (appended; the old clause stays).
    worked = copy.deepcopy(contract)
    worked["work"] += " " + PLAN_SENTENCE.format(command=command, path=message_path)
    row["variants"]["full_plan_text_in_work"] = lc.compact_bytes(worked) - total
    # The text alone, as the brief asks (text_bytes of the sentence).
    row["plan_sentence_text_bytes"] = lc.text_bytes(PLAN_SENTENCE.format(command=command, path=message_path))
    # The printed allowance (bytes the four opening sections may use together), today and with each wording.
    minimal = nav.improve_start_contract(None, root, run_state, minimal_opening())
    row["allowance"] = {"today": lc.CONTRACT_BUDGET - lc.compact_bytes(minimal)}
    for name in VARIANTS:
        row["allowance"][name] = lc.CONTRACT_BUDGET - lc.compact_bytes(
            apply_variant(minimal, name, command, message_path, str(receipt_dir / "parent-return.md")))
    # Route variant: a delegated (ask-agent) child lists one more resource (host-owner.md).
    delegated = dict(run_state, delegation="ask-agent")
    row["ask_agent_extra_bytes"] = lc.compact_bytes(nav.improve_start_contract(None, root, delegated, opening)) - total
    # Longer paths: lengthen the worktree and run-directory strings everywhere they occur (contract and wording),
    # then re-measure with compact_bytes. A user's checkout path may be longer than the E2E harness's.
    row["longer_paths"] = {}
    for extra in (50, 100):
        sizes = {"today": lc.compact_bytes(lengthen(contract, child["workspace"], str(root), extra))}
        for name in ("full_plan_text", "pointer_to_parent_return"):
            sizes[name] = lc.compact_bytes(lengthen(apply_variant(contract, name, command, message_path, parent_return),
                                                    child["workspace"], str(root), extra))
        row["longer_paths"][str(extra)] = sizes
    row["_case"] = case_dir.name
    return row, None


def loop_contract_sizes(runs_root: Path):
    out = {"test_loop": [], "quality_loop": []}
    for key, pattern in (("test_loop", "tests"), ("quality_loop", "quality")):
        for day in RUN_DAYS:
            for path in sorted(glob.glob(str(runs_root / day / "*" / ".shiploop-runs" / "*" / "run" / pattern
                                             / "nav-*-contract.json"))):
                contract = json.loads(Path(path).read_text(encoding="utf-8"))
                out[key].append({"bytes": lc.compact_bytes(contract), "authority": contract["context"]["authority"]})
    summary = {}
    for key, rows in out.items():
        sizes = [row["bytes"] for row in rows]
        summary[key] = {"bytes": stats(sizes), "headroom": stats([lc.CONTRACT_BUDGET - s for s in sizes]),
                        "authority_forbids_commit": all("commit" in row["authority"].lower() and "Do not commit" in row["authority"]
                                                        for row in rows) if rows else None}
    return summary


def older_saved_contracts(runs_root: Path, rebuilt_costs):
    """Supplement: the Improve contracts older runs (20261003-20261007) froze, sized as saved (never rebuilt).

    These come from earlier builders, so they show only how big a model-written opening can get (Luna wrote
    far larger ones than Sonnet and Grok), not today's fixed text. `rebuilt_costs` are the added bytes of the
    full and pointer wordings (the medians measured on today's contracts).
    """
    by_model = {}
    for day in ("20261003", "20261004", "20261005", "20261006", "20261007"):
        found = []
        for dirpath, _dirs, files in os.walk(runs_root / day):  # glob's ** skips the hidden .shiploop-runs directory
            if "start.json" in files and "/.shiploop-improve/" in dirpath + "/" and "/home/" not in dirpath:
                found.append(os.path.join(dirpath, "start.json"))  # "/home/": a host home's copy of plugin fixtures
        for path in sorted(found):
            case = Path(path.split("/.shiploop-runs")[0])
            invocation = json.loads((case / "invocation.json").read_text(encoding="utf-8")) \
                if (case / "invocation.json").is_file() else {}
            contract = json.loads(Path(path).read_text(encoding="utf-8"))
            match = re.search(r"on the (\S+) result\.$", contract["context"]["request"])
            key = (invocation.get("host") or "unknown") + " " + str(invocation.get("model") or "?")
            by_model.setdefault(key, []).append((lc.compact_bytes(contract), match.group(1) if match else "?",
                                                 str(Path(path).relative_to(runs_root)).split("/.shiploop-runs")[0]))
    out = {}
    for key, rows in sorted(by_model.items()):
        sizes = [size for size, _stage, _run in rows]
        out[key] = {"n": len(rows), "runs": len({run for _s, _st, run in rows}), "bytes": stats(sizes),
                    "over_budget_as_saved": sum(1 for v in sizes if v > lc.CONTRACT_BUDGET),
                    "headroom_below_full_wording": sum(1 for v in sizes if lc.CONTRACT_BUDGET - v < rebuilt_costs["full_plan_text"]),
                    "headroom_below_pointer_wording": sum(1 for v in sizes if lc.CONTRACT_BUDGET - v < rebuilt_costs["pointer_to_parent_return"]),
                    "largest_by_stage": {stage: max(size for size, st, _r in rows if st == stage)
                                         for stage in sorted({st for _s, st, _r in rows})}}
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-root", default="/Users/dadleet/e2e-runs")
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent / "contract-headroom.json"))
    args = parser.parse_args()
    runs_root = Path(args.runs_root)

    rows, unusable, per_run = [], [], []
    for state_path in find_states(runs_root):
        root = state_path.parent
        case_dir = state_path.parents[3]
        state = load_state(state_path)
        invocation = json.loads((case_dir / "invocation.json").read_text(encoding="utf-8")) \
            if (case_dir / "invocation.json").is_file() else {}
        used = 0
        for action, record in state.get("improve_results", {}).items():
            try:
                row, why = measure_child(root, state, action, record, case_dir)
            except Exception as exc:  # a saved run this builder cannot rebuild is reported, never skipped silently
                row, why = None, type(exc).__name__ + ": " + str(exc)[:160]
            if row is None:
                unusable.append({"run": str(state_path.relative_to(runs_root)), "action": action, "why": why})
                continue
            row["run"] = str(state_path.relative_to(runs_root)).split("/.shiploop-runs")[0]
            row["host"] = invocation.get("host")
            row["planning_review"] = state.get("planning_review")
            row["delegation"] = state.get("delegation")
            rows.append(row)
            used += 1
        per_run.append({"run": str(state_path.relative_to(runs_root)).split("/.shiploop-runs")[0],
                        "host": invocation.get("host"), "model": invocation.get("model"),
                        "planning_review": state.get("planning_review"), "delegation": state.get("delegation"),
                        "children_in_state": len(state.get("improve_results", {})), "children_measured": used})

    if not rows:  # name the first reason, so a builder change that breaks every rebuild is not read as "no data"
        raise SystemExit("no Improve child could be rebuilt; first reason: "
                         + (json.dumps(unusable[0]) if unusable else "no saved run with Improve children under " + str(runs_root)))
    stages = {}
    for stage in sorted({row["stage"] for row in rows}):
        group = [row for row in rows if row["stage"] == stage]
        entry = {
            "n": len(group), "runs": len({row["run"] for row in group}),
            "bytes": stats([r["bytes"] for r in group]),
            "headroom": stats([r["headroom"] for r in group]),
            "model_written_bytes": stats([r["model_written"] for r in group]),
            "fixed_bytes": stats([r["bytes"] - r["model_written"] for r in group]),
            "allowance_today": stats([r["allowance"]["today"] for r in group]),
            "resources": stats([r["resources"] for r in group]),
            "workspace_chars": stats([r["workspace_chars"] for r in group]),
            "command_chars": stats([r["command_chars"] for r in group]),
            "request_bytes": stats([r["fields"]["request"] for r in group]),
            "environment_bytes": stats([r["fields"]["environment"] for r in group]),
            "authority_bytes": stats([r["fields"]["authority"] for r in group]),
            "variants": {},
            "longer_paths": {},
        }
        for extra in ("50", "100"):
            for name in ("today", "full_plan_text", "pointer_to_parent_return"):
                sizes = [r["longer_paths"][extra][name] for r in group]
                entry["longer_paths"][extra + "_" + name] = {
                    "bytes_max": max(sizes), "children_over_budget": sum(1 for v in sizes if v > lc.CONTRACT_BUDGET),
                    "min_headroom": lc.CONTRACT_BUDGET - max(sizes)}
        for name in list(VARIANTS) + ["full_plan_text_in_work"]:
            deltas = [r["variants"][name] for r in group]
            over = [r for r in group if r["bytes"] + r["variants"][name] > lc.CONTRACT_BUDGET]
            entry["variants"][name] = {
                "added_bytes": stats(deltas),
                "children_over_budget": len(over),
                "min_headroom_after": min(r["headroom"] - r["variants"][name] for r in group),
                "median_headroom_after": statistics.median([r["headroom"] - r["variants"][name] for r in group]),
                # The delegated route lists one more resource (host-owner.md); no saved run used it, so its cost is the
                # real builder's bytes for that row added to each child.
                "children_over_budget_ask_agent": sum(
                    1 for r in group if r["bytes"] + r["ask_agent_extra_bytes"] + r["variants"][name] > lc.CONTRACT_BUDGET),
                "min_headroom_after_ask_agent": min(
                    r["headroom"] - r["ask_agent_extra_bytes"] - r["variants"][name] for r in group),
                "allowance_after_median": statistics.median([r["allowance"].get(name, r["allowance"]["today"]) for r in group]),
            }
        stages[stage] = entry

    everything = {
        "bytes": stats([r["bytes"] for r in rows]), "headroom": stats([r["headroom"] for r in rows]),
        "model_written_bytes": stats([r["model_written"] for r in rows]),
        "fixed_bytes": stats([r["bytes"] - r["model_written"] for r in rows]),
        "children_over_budget_today": sum(1 for r in rows if r["headroom"] < 0),
        "plan_sentence_text_bytes": stats([r["plan_sentence_text_bytes"] for r in rows]),
        "command_chars": stats([r["command_chars"] for r in rows]),
        "message_path_chars": stats([r["message_path_chars"] for r in rows]),
        "ask_agent_extra_bytes": stats([r["ask_agent_extra_bytes"] for r in rows]),
        "workspace_occurrences": stats([r["workspace_occurrences"] for r in rows]),
        "run_dir_occurrences": stats([r["run_dir_occurrences"] for r in rows]),
        "identical_to_saved": sum(1 for r in rows if r["identical_to_saved"]),
        "different_from_saved": [{"run": r["run"], "action": r["action"], "rebuilt": r["bytes"], "saved": r["saved_bytes"]}
                                 for r in rows if not r["identical_to_saved"]],
        "frozen_authority_says_child_never_runs_a_callback": sum(1 for r in rows if r["frozen_authority_says_child_never_runs_a_callback"]),
        "opening_authority_names_improve_commit": sum(1 for r in rows if r["authority_names_improve_commit_in_opening"]),
        "opening_mentions_key_learnings": sum(1 for r in rows if r["opening_mentions_key_learnings"]),
        "command_source": {
            "printed_packet_line": sum(1 for r in rows if r["packet_prints_improve_commit"]),
            "built_with_callback": sum(1 for r in rows if not r["packet_prints_improve_commit"])},
        "built_command_equals_printed": {
            "equal": sum(1 for r in rows if r["built_command_equals_printed"] is True),
            "different_script_path_on_grok": sum(1 for r in rows if r["built_command_equals_printed"] is False)},
        "parent_packet_prints_improve_commit_by_stage": {
            stage: {"printed": sum(1 for r in rows if r["stage"] == stage and r["packet_prints_improve_commit"]),
                    "packet_saved_without_it": sum(1 for r in rows if r["stage"] == stage and r["packet_saved"]
                                                   and not r["packet_prints_improve_commit"]),
                    "no_packet_saved": sum(1 for r in rows if r["stage"] == stage and not r["packet_saved"])}
            for stage in sorted({r["stage"] for r in rows})},
        "opening_section_bytes": {name: stats([r["sections"][name] for r in rows]) for name in nav.OPENING_SECTIONS},
    }
    by_stage_count = {}
    for r in rows:
        by_stage_count.setdefault(r["planning_review"], {}).setdefault(r["stage"], 0)
        by_stage_count[r["planning_review"]][r["stage"]] += 1
    everything["children_by_planning_review_and_stage"] = by_stage_count

    result = {
        "budget": {"CONTRACT_BUDGET": lc.CONTRACT_BUDGET, "STATE_LIMIT": lc.STATE_LIMIT,
                   "STATE_OVERHEAD": lc.STATE_OVERHEAD, "REPORT_RESERVE": lc.REPORT_RESERVE},
        "builders": [
            {"symbol": "shiploop_navigator.improve_start_contract", "used_for": "every Improve child (spec, test-strategy, plan, step-plan, "
             "test-spec, system-test-author, release-plan, carry-forward); the plan stage adds a planning exit and repeat clause",
             "called_from": ["_improve_start", "improve_opening_allowance"], "commit_text": "Commit policy ... no empty commit ... The child never runs a ShipLoop callback"},
            {"symbol": "shiploop_test_loop._contract (via build_contract; listing_problem sizes it)", "used_for": "test-green, regression and the other test-loop stages",
             "commit_text": "Do not commit, push, install or download anything"},
            {"symbol": "shiploop_quality.build_contract", "used_for": "static-checks quality loop", "commit_text": "Do not commit, push, install or download anything"},
        ],
        "dataset": {"runs": per_run, "children_measured": len(rows), "children_unusable": unusable},
        "improve_all_stages": everything,
        "improve_by_stage": stages,
        "other_loops_from_saved_contract_files": loop_contract_sizes(runs_root),
        "older_runs_saved_improve_contracts": older_saved_contracts(runs_root, {
            "full_plan_text": int(statistics.median([r["variants"]["full_plan_text"] for r in rows])),
            "pointer_to_parent_return": int(statistics.median([r["variants"]["pointer_to_parent_return"] for r in rows]))}),
        "variant_text": {name: text for name, text in VARIANTS.items()},
        "children": [[r["run"], r["stage"], r["bytes"], r["model_written"], r["resources"],
                      r["workspace_chars"], r["command_chars"], r["variants"]["full_plan_text"],
                      r["variants"]["lessons_only"], r["variants"]["pointer_to_parent_return"]] for r in rows],
        "children_columns": ["run", "stage", "bytes", "model_written", "resources", "workspace_chars", "command_chars",
                             "added_full_plan_text", "added_lessons_only", "added_pointer"],
    }
    Path(args.out).write_text(json.dumps(result, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"children": len(rows), "unusable": len(unusable), "out": args.out}))


if __name__ == "__main__":
    main()
