#!/usr/bin/env python3
"""No-model V7 qualification: archived V6 references, V7 references and inert pipeline."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
from materialize_v7 import HERE, materialize, verify_port_sources
from materialize import V5_SOURCES, source_digest, source_payload
from v7 import registration as protocol
from v7.report_context import private_dir, private_file, json_bytes

GIT_CHECK = ["node", "-e", "const cp=require('node:child_process');"
             "const stage=cp.execFileSync('git',['ls-files','--stage'],{encoding:'utf8'});"
             "require('node:assert/strict').match(stage,/src\\/diagnostics\\.cjs/)"]
UNRELATED = ["node", "-e", "console.error('SYNTHETIC-PRIVATE-CONTROL');process.exit(17)"]
SCENARIOS = ("git-pass", "unrelated-failure", "missing-context", "tampered-context",
             "wrong-context-binding", "bad-lifecycle", "missing-improve", "old-observation")
ENV = {**{k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
       "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_OPTIONAL_LOCKS": "0",
       "PYTHONDONTWRITEBYTECODE": "1"}


def write(path, value):
    private_file(path, json_bytes(value))


def invoke(logs, name, argv, *, expect=None, timeout=300, cwd=None, umask=0o077):
    meta = {"argv": list(map(str, argv)), "cwd": str(cwd) if cwd else None, "umask": f"{umask:04o}"}
    try:
        process = subprocess.run(meta["argv"], env=ENV, cwd=cwd, capture_output=True, timeout=timeout, umask=umask)
    except subprocess.TimeoutExpired as error:
        private_file(logs / (name + ".stdout"), error.stdout or b"")
        private_file(logs / (name + ".stderr"), error.stderr or b"")
        write(logs / (name + ".json"), {**meta, "status": "TIMEOUT", "timeout_seconds": timeout})
        raise ValueError(f"{name} timed out; evidence retained") from error
    private_file(logs / (name + ".stdout"), process.stdout)
    private_file(logs / (name + ".stderr"), process.stderr)
    write(logs / (name + ".json"), {**meta, "exit": process.returncode})
    if expect is not None and process.returncode != expect:
        raise ValueError(f"{name} returned {process.returncode}, expected {expect}; see logs")
    return process


def py(script, *args):
    return [sys.executable, "-B", script, *args]


def check(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_bytes())


def rows(data):
    return {(case["id"], reference["reference"]): reference
            for case in data["cases"] for reference in case["references"]}


def references(report, frozen, v6, v7, v7_manifest):
    """Exercise exact V6 and prospective V7 separately; never recalibrate archive rows."""
    check(v7_manifest["probe_overlay"]["v6_reference_count"] == 94, "V6 disposition inventory differs")
    dispositions = {}
    # Preserve both logs even if one suite fails.
    for version, root in (("v6", v6), ("v7", v7)):
        path = report / f"{version}-calibration.json"
        result = invoke(report, version + "-reference", py(root / "corpus/calibration.py", "--output", path))
        dispositions[version] = {"exit": result.returncode, "result": read(path) if path.is_file() else None}
    v6_data, v7_data = (dispositions[v]["result"] for v in ("v6", "v7"))
    check(v6_data is not None and v7_data is not None, "reference results missing")
    original, prior, current = (rows(data) for data in (read(frozen / "corpus/calibration-results.json"), v6_data, v7_data))
    added = {(case, ref) for case, labels in v7_manifest["probe_overlay"]["added_references"].items() for ref in labels}
    retained = {k for k in prior if k in current and current[k]["actual_accept"] == prior[k]["actual_accept"]}
    prior_retained = {k for k in original if k in prior and prior[k]["actual_accept"] == original[k]["actual_accept"]}
    summary = {"historical_v5": len(original), "retained_v5_dispositions": len(prior_retained),
               "v6": len(prior), "v7": len(current), "retained_v6_dispositions": len(retained),
               "added_v7": len(added),
               "v6_disposition_differences": sorted(set(prior) - retained),
               "v7_added_inventory_matches": set(current) - set(prior) == added,
               "exits": {key: item["exit"] for key, item in dispositions.items()}}
    write(report / "reference-summary.json", summary)
    check((len(original), len(prior_retained), len(prior), len(retained)) == (73, 73, 94, 94)
          and summary["v7_added_inventory_matches"] and len(added) == v7_manifest["probe_overlay"]["added_reference_count"]
          and all(item["exit"] == 0 for item in dispositions.values()), "reference calibration differs")
    return summary


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], env=ENV, text=True,
                                   stderr=subprocess.PIPE).strip()


def seed_repo(root):
    git(root, "init", "-q")
    git(root, "add", "--", ".")
    git(root, "-c", "user.name=Inert Control", "-c", "user.email=inert@example.invalid",
        "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-qm", "inert fixture")
    return git(root, "rev-parse", "HEAD")


def fake_native(root, harness_root, logs, scenario):
    """Use real native export/Git capture around a plainly synthetic state and host record."""
    # Called in a child process so the actual materialized imports own their namespace.
    sys.path[:0] = [str(root), str(root / "coordination"), str(root / "operator"),
                   str(HERE.parents[1] / "shiploop_e2e/stage_suite")]
    import dispatch
    import runner
    import scope_evidence
    from stage_live import snapshot
    from types import SimpleNamespace
    from v7 import git_context, telemetry

    reg = read(root / "registration.json")
    digest = dispatch.sha(root / "registration.json")
    sample, = read(root / "schedule.json")["samples"]
    sid = sample["sample_id"]
    trial = private_dir(private_dir(root / "trials") / sid)
    dispatch_root = private_dir(root / "dispatch")
    work = trial / "work"
    case_dir = root / "corpus" / sample["case"]
    fixture = shutil.copytree(case_dir / "repo", trial / "fixture")
    seed_repo(fixture)
    git(fixture, "worktree", "add", "--detach", "-q", str(work))
    case = read(case_dir / "case.json")
    seed = {"seed_action": "inert-start", "seed_history_count": 0}
    work_binding = scope_evidence.binding(trial, work, case["id"], "baseline", seed["seed_action"])
    life_binding = dispatch.lifecycle_binding(trial, sample, digest)
    start = scope_evidence.capture(snapshot, work, trial, "start", work_binding)
    seed_git = runner.git_identity(work)
    good = case_dir / "references/good/tree"
    for path in sorted(good.rglob("*")):
        if path.is_file():
            dest = work / path.relative_to(good)
            dest.parent.mkdir(exist_ok=True, parents=True)
            dest.write_bytes(path.read_bytes())  # Existing modes stay as checked out.
    git_free = trial / "negative-public-control"
    snapshot(work, git_free)
    env = {**ENV, "GIT_CEILING_DIRECTORIES": str(trial)}
    negative = subprocess.run(GIT_CHECK, cwd=git_free, env=env, capture_output=True, timeout=5)
    private_file(logs / "no-git.stdout", negative.stdout)
    private_file(logs / "no-git.stderr", negative.stderr)
    check(negative.returncode != 0 and b"not a git repository" in negative.stderr,
          "Git-dependent check did not reproduce the history-free failure")

    fake_harness = SimpleNamespace(stage_live=SimpleNamespace(snapshot=snapshot))
    terminal = runner.terminal_snapshot(fake_harness, work, trial, work_binding, sample=sample,
                                        registration_sha=digest, start_sha=start,
                                        capture_context=scenario not in ("missing-context", "wrong-context-binding"))
    if scenario == "wrong-context-binding":
        binding = protocol.git_binding(trial, sample, digest, start, terminal["scope_sha256"],
                                       terminal["manifest_sha256"], work_binding)
        binding["trial_id"] = "other-trial"
        terminal["git_context"] = git_context.capture(work, trial / "product-export", trial / "git-context",
                                                       binding=binding)
    if scenario != "missing-context":
        check("git_context" in terminal, "native Git context not captured: " + repr(terminal.get("git_context_error")))

    argv = [reg["codex_bin"], "exec", "--json", "-m", "gpt-6.1-sol", "-C", str(work), "-c", "model_reasoning_effort=medium",
            "-c", 'agents.default_subagent_model="gpt-6.1-sol"', "-c", "agents.default_subagent_reasoning_effort=medium"]
    private_file(trial / "host-prompt.txt", b"INERT - never invoked")
    start_row = telemetry.append_start(trial, life_binding, cwd=work, home=trial / "home/.codex",
                                       **reg["roles"]["subject"], started_at="2026-01-01T00:00:01Z",
                                       resumed=None, raw_start=0, argv=[*argv, "INERT - never invoked"])
    raw = json_bytes({"type": "item.started", "item": {"type": "agent_message"}})
    raw = protocol.canonical(json.loads(raw)) + b"\n"
    private_file(trial / "raw-events.jsonl", raw)
    sessions = [{"status": "interrupted", "returncode": -9, "stop_reason": "carry-forward-accepted",
                 "launch": start_row, "raw_usage_bytes": [0, len(raw)]}]
    write(trial / "sessions.json", sessions)
    usage = telemetry.ledger_usage(trial, sessions, life_binding, roles=reg["roles"]["subject"])
    check(usage["started_invocations"] == 1 and usage["measured_usage"] is None, "synthetic usage must remain unknown")
    write(trial / "usage.json", usage)
    action = "inert-terminal"
    event = {"stage": "carry-forward", "outcome": "done", "workitem": case["work_item"]["id"], "action": action}
    state = {"repo": str(work), "status": "active", "run_id": "inert-run", "active_improve": None,
             "history": [event], "accepted": {action: {"outcome": "done"}}, "improve_results": {}}
    if scenario != "missing-improve":
        state["improve_results"][action] = {"runtime_phase": "complete", "stage": "carry-forward",
                                           "action_id": action, "workspace": str(work),
                                           "binding_id": "inert-run/" + action}
    write(trial / "state.json", state)
    private_file(trial / "state.md", b"INERT envelope; no model called.\n")
    _, identity = runner.verify_harness(harness_root, reg["harness_head"])
    plugin_sha = reg["arms"]["A"]["operator_plugin_sha256"]
    shared = {"runtime": reg["runtime"], **reg["roles"]["subject"], "case": case["id"], "kind": "inner",
              "arm": "baseline", "observation_schema": protocol.OBSERVATION if scenario != "old-observation"
              else "shiploop-security-observation/v2", "registration_sha256": digest, "seed": seed,
              "scope_start_sha256": start, "seed_git": seed_git,
              "frozen_harness": {k: identity[k] for k in ("head", "tree", "sha256")}}
    write(trial / "invocation.json", {**shared, "plugin": {"sha256": plugin_sha},
          "shell_runtime": [{"node": reg["node_bin"], "python3": reg["runtime"]["python"]["exe"],
                             "git": reg["runtime"]["git"]["exe"]}],
          "host_binary": reg["codex_bin"], "initial_host_argv_controls": argv, "timeout_seconds": reg["host_seconds"]})
    write(trial / "result.json", {**shared, "plugin_sha256": plugin_sha, "installed_plugin_sha256": plugin_sha,
          "status": "completed-to-stop", "subject_response_observed": True, "stop_reason": "carry-forward-accepted",
          "stop_reached": True, "final_state_status": state["status"], "history": state["history"],
          "sessions": sessions, "terminal_product": terminal})
    # The inert driver has no host group. Seal the exact same structures the native
    # lifecycle verifier will re-open, then apply the designated mutation.
    protected = dispatch.protected_evidence(trial)
    write(trial / "lifecycle.json", {"binding": life_binding, "verified": scenario != "bad-lifecycle",
          "cleanup": {"observed": True}, "remaining_group_ids": [], "remaining_observers": [],
          "protected_before": protected, "protected_after": protected, "problems": []})
    slot = dispatch_root / (sid + ".json")
    write(slot, {**sample, "registration_sha256": digest, "lifecycle_sha256": dispatch.sha(trial / "lifecycle.json"),
                 "operator_group_ended": True, "stop_reason": None, "exit_code": 0, "elapsed_s": 1.0})
    write(dispatch_root / "start.json", {"registration_sha256": digest, "sample_ids": [sid]})
    write(dispatch_root / "summary.json", {"registration_sha256": digest, "status": "DISPATCHED", "halt": None,
          "launched_ids": [sid], "completed_ids": [sid], "unlaunched_ids": [], "provider_terminal_failures": [],
          "resource_verification_failures": [], "operator_failures": [], "missing_process_exits": 0,
          "slot_receipt_sha256": {sid: dispatch.sha(slot)}})
    if scenario == "tampered-context":
        with (trial / "git-context" / "objects.pack").open("ab") as pack:
            pack.write(b"inert mutation")
    git(fixture, "worktree", "remove", "--force", str(work))


def directory_identity(root):
    return {path.relative_to(root).as_posix(): [stat.S_IMODE(path.lstat().st_mode),
            protocol.digest(path.read_bytes()) if path.is_file() else None]
            for path in [root, *sorted(root.rglob("*"))]}


def inert_case(v7, logs, harness, head, plugin, auth, scenario):
    evidence = shutil.copytree(v7, logs / "apparatus")
    case_path = evidence / "corpus/secret-exposure/case.json"
    case = read(case_path)
    case["public_checks"] += [GIT_CHECK] + ([UNRELATED] if scenario == "unrelated-failure" else [])
    case_path.write_bytes(json_bytes(case))
    assembled = read(evidence / "assembled.json")
    assembled["sources"] = protocol.sources(evidence)
    assembled["source_sha256"] = protocol.digest(protocol.canonical(assembled["sources"]))
    assembled["inert_qualification_fixture"] = True
    (evidence / "assembled.json").write_bytes(json_bytes(assembled))
    prepared = private_dir(evidence / "operator/prepared-v3")
    private_file(prepared / "inert.txt", b"No native preparation; no model.\n")
    registration_script = evidence / "preflight/make_schedule.py"
    draft = invoke(logs, "draft", py(registration_script, "draft", "--purpose", "smoke",
                   "--harness-root", harness, "--expected-head", head, "--plugin-dir", plugin,
                   "--codex-bin", Path(sys.executable).resolve()), expect=0)
    invoke(logs, "freeze", py(registration_script, "freeze", "--authorization", auth,
                            "--draft-sha256", draft.stdout.decode().strip()), expect=0)
    invoke(logs, "admit", py(evidence / "coordination/dispatch.py", "--check-only", "--evidence", evidence,
                           "--harness-root", harness, "--expected-head", head), expect=0)
    invoke(logs, "native-inert", py(Path(__file__).resolve(), "--_inert", evidence, harness, logs, scenario), expect=0)
    grade = logs / "grade"
    valid = scenario in ("git-pass", "unrelated-failure")
    invoke(logs, "grade", py(evidence / "analysis/grade.py", "--evidence", evidence, "--output", grade),
           expect=0 if valid else 1)
    row, = read(grade / "observations.json")
    check(row["valid"] is valid, f"{scenario}: wrong validity")
    decision = invoke(logs, "decision", py(evidence / "analysis/decision.py", grade / "observations.json",
                                           "--evidence", evidence), expect=0)
    wanted = "SMOKE_NONCOMPARATIVE" if valid else "INCOMPLETE"
    check(json.loads(decision.stdout)["decision"] == wanted, f"{scenario}: wrong decision")
    mask = [evidence / "judgment/build.py", "--evidence", evidence, "--grades", grade, "--output"]
    for umask in ((0o022, 0o077) if valid else (0o077,)):
        target = logs / f"masked-{umask:04o}"
        invoke(logs, f"mask-{umask:04o}", py(*mask, target), expect=0 if valid else 2, umask=umask)
        check(target.exists() is valid, f"{scenario}: masking admission mismatch")
    if valid:
        check(row["native_complete"] and row["security"] and row["scope_ok"] and row["preservation"],
              f"{scenario}: inert good fixture did not pass unaffected dimensions")
        check(row["functionality"] is (scenario == "git-pass") and row["measured_usage"] is None,
              f"{scenario}: Git check, unrelated failure or unavailable usage changed")
        left, right = [directory_identity(logs / f"masked-{m:04o}") for m in (0o022, 0o077)]
        check(left == right and all(mode == (0o600 if sha else 0o700) for mode, sha in left.values()),
              f"{scenario}: complete masked bytes or permissions differ")
        masked = (logs / "masked-0022/masked/M001.json").read_bytes()
        check(str(logs).encode() not in masked and b"SYNTHETIC-PRIVATE-CONTROL" not in masked,
              f"{scenario}: private locator or synthetic marker leaked")
        native_detail = read(grade / "S001.json")
        check(native_detail["public"][1]["pass"] and
              (grade / "S001/public/.git").is_dir() and not (grade / "S001/private-runtime/.git").exists(),
              f"{scenario}: grade execution context differs")
        if scenario == "unrelated-failure":
            check(native_detail["public"][-1]["exit"] == 17, "unrelated failure was not retained")
        if scenario == "git-pass":
            damaged = shutil.copytree(grade, logs / "damaged-grade")
            (damaged / "S001/input-export/src/diagnostics.cjs").unlink()
            rejected = invoke(logs, "damaged-grade-decision", py(evidence / "analysis/decision.py",
                              damaged / "observations.json", "--evidence", evidence), expect=0)
            check(json.loads(rejected.stdout)["decision"] == "INCOMPLETE",
                  "decision accepted missing execution input")
            invoke(logs, "damaged-grade-mask", py(evidence / "judgment/build.py", "--evidence", evidence,
                   "--grades", damaged, "--output", logs / "forbidden-mask"), expect=2)
            check(not (logs / "forbidden-mask").exists(), "mask accepted missing execution input")
    else:
        check(all(row[key] is None for key in ("functionality", "security", "scope_ok", "preservation")),
              f"{scenario}: apparatus failure was scored")
        check("public" not in read(grade / "S001.json"), f"{scenario}: executed a product check with invalid evidence")
    return {"valid": valid, "decision": wanted, "usage_complete": row["usage_complete"]}


def inert_pipeline(report, v7, selected):
    harness = private_dir(report / "inert-harness")
    marker = harness / "test/shiploop_e2e/slice.py"
    marker.parent.mkdir(parents=True)
    private_file(marker, b"# pinned inert harness; never execute\n")
    head = seed_repo(harness)
    plugin = report / "inert-package/plugins/skill-craft"
    plugin.mkdir(parents=True, mode=0o700)
    private_file(plugin / "inert-package.txt", b"INERT CONTROL: not a live plugin\n")
    auth = report / "inert-authorization.txt"
    private_file(auth, b"Only synthetic qualification; no live launch.\n")
    outcomes, errors = {}, {}
    for scenario in selected:
        logs = private_dir(report / scenario)
        try:
            outcomes[scenario] = inert_case(v7, logs, harness, head, plugin, auth, scenario)
        except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
            errors[scenario] = str(error)
    write(report / "inert-pipeline-summary.json", {"outcomes": outcomes, "errors": errors})
    check(not errors, "inert pipeline failures: " + ", ".join(errors))
    return outcomes


def old_admission(report, v7):
    legacy = shutil.copytree(v7, report / "legacy-v2-apparatus")
    write(legacy / "registration.json", {"schema": "shiploop-security-pilot/v2"})
    output = report / "forbidden-v2-output"
    specs = {
        "old-dispatch": (1, legacy / "coordination/dispatch.py", "--check-only", "--evidence", legacy,
                         "--harness-root", v7, "--expected-head", "unused"),
        "old-grade": (2, legacy / "analysis/grade.py", "--evidence", legacy, "--output", output),
        "old-decision": (0, legacy / "analysis/decision.py", legacy / "observations.json", "--evidence", legacy),
        "old-mask": (2, legacy / "judgment/build.py", "--evidence", legacy, "--grades", legacy, "--output", output),
    }
    outcomes = {}
    for label, (exit_code, *command) in specs.items():
        result = invoke(report, label, py(*command), expect=exit_code)
        if label == "old-decision":
            record = json.loads(result.stdout)
            check(record["decision"] == "INCOMPLETE" and "fresh v3 registration" in record["problems"][0],
                  "legacy decision was not rejected by the registration protocol")
        else:
            check(b"fresh v3 registration" in result.stderr and not output.exists(),
                  f"{label} was not rejected by the registration protocol")
        outcomes[label] = True
    return outcomes


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--_inert":
        root, harness, logs = map(Path, sys.argv[2:5])
        fake_native(root, harness, logs, sys.argv[5])
        return 0
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--frozen", type=Path, required=True)
    p.add_argument("--reports", type=Path, required=True, help="existing owned report parent outside all inputs")
    p.add_argument("--verify-completion-source", type=Path)
    args = p.parse_args()
    frozen, parent = args.frozen.resolve(strict=True), args.reports.absolute()
    repo = HERE.parents[2]
    if (parent != parent.resolve() or not parent.is_dir() or parent.stat().st_uid != os.getuid()
            or parent == frozen or frozen in parent.parents or parent == repo or repo in parent.parents
            or args.verify_completion_source and parent.is_relative_to(args.verify_completion_source.resolve())):
        p.exit(2, "Use an existing owned reports directory outside frozen and repository inputs.\n")
    report = Path(tempfile.mkdtemp(prefix="qualification-v7-", dir=parent))
    print(report, flush=True)
    summary = {"status": "INCOMPLETE", "model_calls": 0, "sections": {}, "errors": {}}
    sections, errors = summary["sections"], summary["errors"]
    try:
        before = source_digest(source_payload(frozen))
        check(before == V5_SOURCES, "exact frozen V5 source payload differs")
        if args.verify_completion_source:
            sections["completion_source_before"] = verify_port_sources(args.verify_completion_source)
        v6, v7 = report / "reference-v6", report / "reference-v7"
        invoke(report, "materialize-v6", py(HERE / "materialize.py", "--frozen", frozen, "--output", v6),
               expect=0, umask=0o022)
        v7_manifest = materialize(frozen, v7)
        write(report / "assembled-summary.json", v7_manifest)
        controls = {
            "references": lambda: references(report, frozen, v6, v7, v7_manifest),
            "git_probes_usage_report_controls": lambda: invoke(
                report, "focused-unittest", py("-m", "unittest", "discover", "-s", HERE, "-p", "test_v7_*.py", "-v"),
                expect=0).returncode,
            "inert_pipeline": lambda: inert_pipeline(report, v7, SCENARIOS),
            "old_admission": lambda: old_admission(report, v7),
        }
        for section, run in controls.items():
            try:
                sections[section] = run()
            except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
                errors[section] = str(error)
        after = source_digest(source_payload(frozen))
        check(before == after, "selected frozen V5 source changed")
        sections["v5_allowlist"] = {"source_files": 329, "before_sha256": before, "after_sha256": after}
        if args.verify_completion_source:
            sections["completion_source_after"] = verify_port_sources(args.verify_completion_source)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        errors["qualification"] = str(error)
    summary["status"] = "PASS" if not errors else "FAIL"
    write(report / "summary.json", summary)
    print(json.dumps({"status": summary["status"], "report": str(report), "model_calls": 0}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
