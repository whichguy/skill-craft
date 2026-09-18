#!/usr/bin/env python3
"""Frozen, paired decision-driven-probe study adapter.

This adapter deliberately reuses the generalized-discovery runner, receipt
gateway, input validator, and blind collector.  The only study-specific surface
is the fixture module supplied beside this file: it exposes ``CASES``,
``materialize(family, root, mutant=False)``, and ``calibrate()``.

The adapter is not a production ShipLoop scheduler and does not launch a model
until its explicit ``run`` command delegates to the frozen runner.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
GENERALIZED = REPO / "test" / "experiments" / "shiploop_generalized_discovery"
CAPABILITIES = REPO / "test" / "experiments" / "shiploop_capabilities"
REFERENCES = REPO / "skills" / "shiploop" / "references"
BASELINE_PROMPT = HERE / "baseline-prompt.md"
CANDIDATE_PROMPT = HERE / "candidate-prompt.md"
CANDIDATE_CUE = HERE / "candidate-cue.txt"
DELTA_ANCHOR = "install a dependency.  Leave unsupported questions open.\n"

LIMITS = {
    "aggregate_active_limit_seconds": 180 * 60,
    "max_arm_launches": 12,
    "parallel": 3,
    "seconds_per_arm": 480,
    "calls_per_arm": 32,
    "exploration_seconds": 360,
    "exploration_calls": 24,
}
FAMILIES = ("f1", "f2", "f3", "f4")
FROZEN_FILES = {
    "fixtures.py": HERE / "fixtures.py",
    "JUDGE.md": HERE / "JUDGE.md",
    "study.py": HERE / "study.py",
    "study_inputs.py": GENERALIZED / "study_inputs.py",
    "runner.py": GENERALIZED / "runner.py",
    "receipt_gateway.py": GENERALIZED / "receipt_gateway.py",
    "collect.py": GENERALIZED / "collect.py",
    "review_runner.py": GENERALIZED / "review_runner.py",
    # The reused input validator binds these names. The generic oracle is never
    # used to judge this study; the fixture calibration is coordinator-owned.
    "oracle.py": GENERALIZED / "oracle.py",
    "PUBLIC_CONTRACTS.md": GENERALIZED / "PUBLIC_CONTRACTS.md",
    "run_trials.py": CAPABILITIES / "run_trials.py",
    "runtime_validation.py": CAPABILITIES / "runtime_validation.py",
    "gateway.py": CAPABILITIES / "gateway.py",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def readable_file(path: Path, label: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"{label} is unavailable") from exc
    if path.is_symlink() or not resolved.is_file():
        raise ValueError(f"{label} must be a regular file")
    try:
        resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"{label} must be readable UTF-8 text") from exc
    return resolved


def regular_tree(root: Path, label: str) -> None:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"{label} is unavailable")
    for path in root.rglob("*"):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError(f"{label} contains an unsafe entry: {path}")


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def calibration(study: Path) -> dict[str, Any]:
    """Run fixture-owned deterministic calibration, binding frozen bytes."""
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        fixture = load_module(study / "frozen" / "fixtures.py", "shiploop_probe_decisions_frozen_fixtures")
        calibration_root = study / "private" / "fixture-calibration"
        calibration_root.mkdir(exist_ok=True)
        result = fixture.calibrate(calibration_root)
        if isinstance(result, bool):
            result = {"passed": result}
        if not isinstance(result, dict) or result.get("passed") is not True:
            raise ValueError("fixture calibration did not pass")
        value = dict(result)
        value["bindings"] = {
            name: sha256(study / "frozen" / name)
            for name in ("fixtures.py", "PUBLIC_CONTRACTS.md", "oracle.py")
        }
        value.setdefault("schema", "shiploop-probe-decisions-calibration/1")
        return value
    except Exception as exc:
        return {
            "schema": "shiploop-probe-decisions-calibration/1",
            "passed": False,
            "error": f"{type(exc).__name__}: {exc}",
            "bindings": {},
        }
    finally:
        sys.dont_write_bytecode = previous


def frozen_manifest(study: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for root in (study / "frozen", study / "guides"):
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"frozen input must not be a symlink: {path}")
            if path.is_file() and path.suffix != ".pyc" and "__pycache__" not in path.parts:
                result[str(path.relative_to(study))] = sha256(path)
    calibration_path = study / "private" / "oracle-calibration.json"
    if calibration_path.is_file() and not calibration_path.is_symlink():
        result[str(calibration_path.relative_to(study))] = sha256(calibration_path)
    return result


def private_judge_packets(study: Path, calibration_result: dict[str, Any]) -> dict[str, str]:
    """Freeze factual family rubrics for a judge without exposing them to arms."""
    fixtures = load_module(study / "frozen" / "fixtures.py", "shiploop_probe_decisions_frozen_judge_fixtures")
    cases, calibrated = getattr(fixtures, "CASES", None), calibration_result.get("families")
    if not isinstance(cases, dict) or not isinstance(calibrated, dict):
        raise ValueError("fixture cases or calibration families are unavailable")
    root = study / "private" / "judge-packets"
    root.mkdir(exist_ok=True)
    hashes: dict[str, str] = {}
    for family in FAMILIES:
        case, result = cases.get(family), calibrated.get(family)
        if not isinstance(case, dict) or not isinstance(result, dict) or result.get("passed") is not True:
            raise ValueError(f"family {family} lacks a calibrated case")
        task, required, forbidden = case.get("task"), case.get("required"), case.get("forbidden")
        reference = result.get("reference")
        if (not isinstance(task, str) or not isinstance(required, (tuple, list))
                or not isinstance(forbidden, (tuple, list)) or not isinstance(reference, dict)
                or not all(isinstance(item, str) for item in (*required, *forbidden))):
            raise ValueError(f"family {family} has an unsupported judge rubric")
        packet = {
            "schema": "shiploop-probe-decisions-family-judge-packet/1",
            "family": family,
            "task": task,
            "required": list(required),
            "forbidden": list(forbidden),
            "calibrated_reference_observations": reference,
            "calibration_limits": calibration_result.get("limits"),
        }
        path = root / f"{family}.json"
        write_json(path, packet)
        hashes[family] = sha256(path)
    return hashes


def validate_private_judge_packet(study: Path, family: str) -> Path:
    state = json.loads((study / "study.json").read_text(encoding="utf-8"))
    hashes = state.get("judge_packet_hashes")
    if not isinstance(hashes, dict) or family not in hashes:
        raise ValueError("frozen family judge packet is unavailable")
    path = study / "private" / "judge-packets" / f"{family}.json"
    if path.is_symlink() or not path.is_file() or hashes[family] != sha256(path):
        raise ValueError("frozen family judge packet hash mismatch")
    return path


def exact_candidate(baseline: str, cue: str) -> str:
    if baseline.count(DELTA_ANCHOR) != 1:
        raise ValueError("baseline research prompt must contain the unique cue anchor")
    return baseline.replace(DELTA_ANCHOR, DELTA_ANCHOR + cue, 1)


def plan_hashes_match(plan: Path, baseline: Path, candidate: Path) -> None:
    """Honor optional labeled prompt digests already recorded in the frozen plan."""
    for label, path in (("baseline", baseline), ("candidate", candidate)):
        expected: list[str] = []
        for line in plan.read_text(encoding="utf-8").splitlines():
            if label in line.lower() and "sha" in line.lower():
                expected.extend(re.findall(r"\b[a-fA-F0-9]{64}\b", line))
        if expected and any(value.lower() != sha256(path) for value in expected):
            raise ValueError(f"{label} prompt hash does not match the preregistered plan")


def initialize(study: Path, candidate: Path, plan: Path, blind_seed: int = 29017) -> dict[str, Any]:
    if not study.is_absolute() or study.is_symlink() or study.exists():
        raise ValueError("--study must be a new absolute non-symlink path")
    candidate, plan = readable_file(candidate, "--candidate"), readable_file(plan, "--plan")
    baseline_source = readable_file(BASELINE_PROMPT, "baseline research prompt")
    cue_source = readable_file(CANDIDATE_CUE, "candidate cue")
    baseline, cue, candidate_text = (baseline_source.read_text(encoding="utf-8"),
                                     cue_source.read_text(encoding="utf-8"),
                                     candidate.read_text(encoding="utf-8"))
    if candidate_text != exact_candidate(baseline, cue):
        raise ValueError("candidate must equal the baseline with exactly one approved cue insertion")
    plan_hashes_match(plan, baseline_source, candidate)
    regular_tree(REFERENCES, "current ShipLoop references")
    for name, path in FROZEN_FILES.items():
        readable_file(path, f"required source {name}")
    study.mkdir(parents=True)
    frozen, guides = study / "frozen", study / "guides"
    frozen.mkdir()
    guides.mkdir()
    for name, path in FROZEN_FILES.items():
        shutil.copy2(path, frozen / name)
    shutil.copy2(plan, frozen / "plan.md")
    shutil.copytree(REFERENCES, guides / "references", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy2(baseline_source, guides / "baseline-research-prompt.md")
    shutil.copy2(candidate, guides / "candidate-research-prompt.md")
    shutil.copy2(cue_source, guides / "candidate-cue.txt")
    for name in ("arms", "private", "reports"):
        (study / name).mkdir()
    started = time.time()
    state: dict[str, Any] = {
        "schema": "generalized-discovery-study/1",
        "study_kind": "shiploop-probe-decisions/1",
        "started_epoch": started,
        "hard_deadline_epoch": started + 90 * 60,
        "closeout_start_epoch": started + 75 * 60,
        **LIMITS,
        "aggregate_active_limit_note": "Coordinator responsibility; runner has no global native-agent watchdog.",
        "blind_order_seed": blind_seed,
        "guide_hashes": {
            "baseline-research-prompt.md": sha256(guides / "baseline-research-prompt.md"),
            "candidate-research-prompt.md": sha256(guides / "candidate-research-prompt.md"),
        },
        "hashes": {}, "status": "initializing", "arms": {},
    }
    write_json(study / "study.json", state)
    result = calibration(study)
    write_json(study / "private" / "oracle-calibration.json", result)
    judge_hashes: dict[str, str] = {}
    if result.get("passed") is True:
        try:
            judge_hashes = private_judge_packets(study, result)
        except ValueError as exc:
            result = {**result, "passed": False, "judge_packet_error": str(exc)}
            write_json(study / "private" / "oracle-calibration.json", result)
    manifest_path = study / "frozen-inputs.json"
    write_json(manifest_path, frozen_manifest(study))
    state["hashes"] = {
        "baseline": state["guide_hashes"]["baseline-research-prompt.md"],
        "candidate": state["guide_hashes"]["candidate-research-prompt.md"],
        "plan": sha256(frozen / "plan.md"),
        "oracle_calibration": sha256(study / "private" / "oracle-calibration.json"),
        "frozen_inputs_manifest": sha256(manifest_path),
    }
    state["judge_packet_hashes"] = judge_hashes
    state["frozen_inputs_manifest"] = "frozen-inputs.json"
    state["status"] = "ready_to_prepare" if result.get("passed") is True else "calibration_failed"
    write_json(study / "study.json", state)
    return {"study": str(study), "status": state["status"], "calibration_passed": result.get("passed") is True}


def validate(study: Path) -> dict[str, str]:
    module = load_module(study / "frozen" / "study_inputs.py", "shiploop_probe_decisions_frozen_inputs")
    return module.validate_study_inputs(study)


def case_task(fixtures: Any, family: str) -> str:
    cases = getattr(fixtures, "CASES", None)
    if not isinstance(cases, dict) or family not in cases:
        raise ValueError(f"unknown fixture family: {family}")
    case = cases[family]
    task = case.get("task") if isinstance(case, dict) else getattr(case, "task", None)
    if not isinstance(task, str) or not task.strip():
        raise ValueError(f"fixture {family} has no task")
    return task


def prepare_pair(study: Path, family: str, repetition: int = 0) -> list[str]:
    validate(study)
    study = study.resolve()
    state = json.loads((study / "study.json").read_text(encoding="utf-8"))
    arms = state.setdefault("arms", {})
    if family not in FAMILIES:
        raise ValueError(f"unknown family: {family}")
    if repetition not in (0, 1):
        raise ValueError("only one preregistered paired replication is allowed")
    if any(a.get("family") == family and a.get("repetition") == repetition for a in arms.values() if isinstance(a, dict)):
        raise ValueError("pair already prepared; preserve prior evidence")
    if len(arms) + 2 > state["max_arm_launches"]:
        raise ValueError("maximum twelve contexts reached")
    fixtures = load_module(study / "frozen" / "fixtures.py", "shiploop_probe_decisions_frozen_prepare_fixtures")
    task = case_task(fixtures, family)
    order = ("baseline", "candidate") if (int(family[-1]) + repetition) % 2 else ("candidate", "baseline")
    names: list[str] = []
    for variant in order:
        name = f"trial-{len(arms) + 1:02d}"
        root, workspace = study / "arms" / name, study / "arms" / name / "workspace"
        workspace.mkdir(parents=True)
        fixtures.materialize(family, workspace, mutant=False)
        shutil.copytree(study / "guides" / "references", workspace / "guidance")
        research_prompt = study / "guides" / f"{variant}-research-prompt.md"
        shutil.copy2(research_prompt, workspace / "guidance" / "research-prompt.md")
        prompt = f"""Perform only this bounded research producer step for this task:

{task}

Read guidance/research-prompt.md. Also read
guidance/research-loop.md#recursive-discovery-and-experiments and
guidance/research-loop.md#reuse-before-a-new-mechanism. Work only in
this synthetic workspace. Write REPORT.md with evidence-backed plan
recommendations. For each material premise, distinguish source inspection from
observed behavior. Do not run a whole ShipLoop runtime, Improve, or callbacks.
Do not edit supplied source/configuration, install tools, use a network, or inspect
neighboring/coordinator paths. Safe documented local probes are allowed when useful.
Report only task findings and plan recommendations: do not quote or describe the
supplied guidance, prompt variant, trial, or comparison.

Allowance: 8 minutes and 32 workspace calls. At 6 minutes or 24 calls, stop
exploration and use the reserve to complete REPORT.md. If unresolved, name the
specific prerequisite and plan consequence. Finish with the REPORT.md locator.
"""
        (root / "prompt.md").write_text(prompt, encoding="utf-8")
        inputs = {str(path.relative_to(workspace)): sha256(path) for path in sorted(workspace.rglob("*")) if path.is_file()}
        write_json(root / "input-hashes.json", inputs)
        arms[name] = {"family": family, "variant": variant, "repetition": repetition,
                      "prompt_sha256": sha256(root / "prompt.md"), "input_hashes_sha256": sha256(root / "input-hashes.json")}
        names.append(name)
    state["arms"] = arms
    write_json(study / "study.json", state)
    return names


def delegated(study: Path, command: list[str]) -> int:
    validate(study)
    return subprocess.run([sys.executable, str(study / "frozen" / "runner.py"), "--study", str(study), *command], check=False).returncode


def validate_run_request(study: Path, arms_text: str, parallel: int) -> list[str]:
    validate(study)
    state = json.loads((study / "study.json").read_text(encoding="utf-8"))
    if isinstance(parallel, bool) or not isinstance(parallel, int) or not 1 <= parallel <= 3 or parallel > state.get("parallel", 0):
        raise ValueError("parallel must be between one and the frozen study cap")
    arms = [item for item in arms_text.split(",") if item]
    if not arms or len(arms) != len(set(arms)):
        raise ValueError("requested arm IDs must be nonempty and unique")
    prepared = state.get("arms")
    if not isinstance(prepared, dict):
        raise ValueError("study arms are unavailable")
    for name in arms:
        arm = prepared.get(name)
        if not isinstance(arm, dict):
            raise ValueError(f"requested arm is not prepared: {name}")
        if arm.get("family") not in FAMILIES or arm.get("variant") not in {"baseline", "candidate"} or arm.get("repetition") not in {0, 1}:
            raise ValueError(f"requested arm has an invalid frozen identity: {name}")
        root = study / "arms" / name
        prompt, inputs = root / "prompt.md", root / "input-hashes.json"
        if prompt.is_symlink() or inputs.is_symlink() or not prompt.is_file() or not inputs.is_file():
            raise ValueError(f"requested arm inputs are unavailable: {name}")
        if arm.get("prompt_sha256") != sha256(prompt) or arm.get("input_hashes_sha256") != sha256(inputs):
            raise ValueError(f"requested arm frozen input hash mismatch: {name}")
    return arms


LEAKAGE_PHRASES = (
    "For each consequential uncertainty, name the decision it could change.",
    "Reuse sufficient current evidence; otherwise choose the smallest authorized observation",
    "This selects exploratory probes; required baseline and acceptance checks still apply.",
)
LEAKAGE_IDENTITIES = re.compile(r"\b(?:baseline|candidate)\s+(?:prompt|trial|variant|arm)\b|\b(?:prompt|trial|variant|arm)\s+(?:baseline|candidate)\b|(?:baseline|candidate)-research-prompt", re.I)


def report_leaks(study: Path, family: str, repetition: int) -> list[str]:
    state = json.loads((study / "study.json").read_text(encoding="utf-8"))
    arms = state.get("arms", {})
    findings: list[str] = []
    for name, arm in arms.items():
        if not isinstance(arm, dict) or arm.get("family") != family or arm.get("repetition") != repetition:
            continue
        report = study / "arms" / name / "workspace" / "REPORT.md"
        if not report.is_file() or report.is_symlink():
            continue
        text = report.read_text(encoding="utf-8", errors="replace")
        for phrase in LEAKAGE_PHRASES:
            if phrase in text:
                findings.append(f"{name}: distinctive cue phrase")
                break
        if LEAKAGE_IDENTITIES.search(text):
            findings.append(f"{name}: explicit comparison identity")
    return findings


def ready_judge_input(study: Path, family: str, repetition: int) -> Path:
    packet = validate_private_judge_packet(study, family)
    bundle = study / "blind" / f"{family}-r{repetition}" / "bundle-compact.md"
    if not bundle.is_file() or bundle.is_symlink():
        raise ValueError("neutral blind bundle is unavailable")
    judge = study / "frozen" / "JUDGE.md"
    if not judge.is_file() or judge.is_symlink():
        raise ValueError("frozen independent judge rubric is unavailable")
    target = bundle.with_name("ready-to-evaluate.md")
    if target.exists():
        raise FileExistsError("ready judge input already exists; preserve prior evidence")
    rubric = json.loads(packet.read_text(encoding="utf-8"))
    text = "\n".join((
        "# Ready-to-evaluate blind input", "",
        "This packet intentionally contains no baseline/candidate mapping.",
        "A limited leakage scanner passed before collection; perform the required manual pre-judge audit.", "",
        "## Independent judge rubric", "", judge.read_text(encoding="utf-8").rstrip(), "",
        "## Selected family facts", "", "```json", json.dumps(rubric, indent=2, sort_keys=True), "```", "",
        "## Neutral paired evidence", "", bundle.read_text(encoding="utf-8").rstrip(), "",
    ))
    target.write_text(text, encoding="utf-8")
    return target


def collect(study: Path, family: str, repetition: int = 0) -> int:
    validate(study)
    validate_private_judge_packet(study, family)
    findings = report_leaks(study, family, repetition)
    if findings:
        raise ValueError("report leakage guard refused blind collection; originals are preserved: " + "; ".join(findings))
    print("Limited leakage scan passed; a manual pre-judge audit remains required.", file=sys.stderr)
    result = subprocess.run([sys.executable, str(study / "frozen" / "collect.py"), "--study", str(study), "--family", family, "--repetition", str(repetition), "--compact"], check=False)
    if result.returncode == 0:
        print(ready_judge_input(study, family, repetition))
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("initialize")
    init.add_argument("--study", required=True, type=Path)
    init.add_argument("--candidate", type=Path, default=CANDIDATE_PROMPT)
    init.add_argument("--plan", required=True, type=Path)
    init.add_argument("--blind-seed", type=int, default=29017)
    prep = sub.add_parser("prepare")
    prep.add_argument("--study", required=True, type=Path)
    prep.add_argument("--families", default=",".join(FAMILIES))
    prep.add_argument("--repetition", type=int, default=0)
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--study", required=True, type=Path)
    run = sub.add_parser("run")
    run.add_argument("--study", required=True, type=Path)
    run.add_argument("--arms", required=True)
    run.add_argument("--parallel", type=int, default=3)
    bundle = sub.add_parser("collect")
    bundle.add_argument("--study", required=True, type=Path)
    bundle.add_argument("--family", required=True, choices=FAMILIES)
    bundle.add_argument("--repetition", type=int, default=0)
    args = parser.parse_args(argv)
    try:
        if args.command == "initialize":
            print(json.dumps(initialize(args.study, args.candidate, args.plan, args.blind_seed), indent=2, sort_keys=True))
            return 0
        if args.command == "prepare":
            names: list[str] = []
            for family in args.families.split(","):
                names += prepare_pair(args.study, family, args.repetition)
            print(json.dumps({"prepared": names}, sort_keys=True))
            return 0
        if args.command == "preflight":
            return delegated(args.study, ["--preflight"])
        if args.command == "run":
            arms = validate_run_request(args.study, args.arms, args.parallel)
            return delegated(args.study, ["--arms", ",".join(arms), "--parallel", str(args.parallel)])
        return collect(args.study, args.family, args.repetition)
    except (OSError, ValueError, FileExistsError, json.JSONDecodeError) as exc:
        print(f"study failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
