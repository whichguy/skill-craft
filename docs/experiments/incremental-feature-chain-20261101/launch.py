#!/usr/bin/env python3
"""Launch exactly one reviewed CSV-chain link through the selected released harness."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from typing import Any

import checkpoint


HERE = Path(__file__).resolve().parent
SOURCE_ROOT = HERE.parents[2]
DEFAULT_RELEASE_COMMIT = "9273b4cfda87761f4ad002324b238e6d8f755bfb"
MODEL = dict(checkpoint.MODEL)
PROMPTS = {
    "base": ("01-base.txt", None),
    "filter": ("02-region.txt", "base"),
    "output": ("03-csv-output.txt", "filter"),
}
BASE_MODES = ("unit", "totals", "invalid", "missing", "empty")
LINK_CHECKS = {"base": ("base-scope",), "filter": ("filter",), "output": ("filter", "output")}


def _git(repo: Path, *args: str, check: bool = True) -> str:
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    if check and done.returncode:
        raise checkpoint.CheckpointError(f"git {' '.join(args)} failed in {repo}: {done.stderr.strip()}")
    return done.stdout.strip()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _validate_segment(value: str, label: str) -> None:
    checkpoint._safe_segment(value, label)


def release_identity(release_tree: str | Path, expected_commit: str) -> dict[str, str]:
    if len(expected_commit) != 40 or any(char not in "0123456789abcdef" for char in expected_commit):
        raise checkpoint.CheckpointError("--release-commit must be a full 40-character lowercase Git commit")
    release_tree = Path(release_tree).expanduser().resolve(strict=True)
    top = Path(_git(release_tree, "rev-parse", "--show-toplevel")).resolve()
    if top != release_tree:
        raise checkpoint.CheckpointError(f"release tree must be the checkout root: {release_tree} (Git root: {top})")
    head = _git(release_tree, "rev-parse", "HEAD")
    tree = _git(release_tree, "rev-parse", "HEAD^{tree}")
    status = subprocess.run(["git", "-C", str(release_tree), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
                            capture_output=True, check=False).stdout
    symbolic = _git(release_tree, "symbolic-ref", "-q", "HEAD", check=False)
    if head != expected_commit:
        raise checkpoint.CheckpointError(f"release tree HEAD must equal --release-commit {expected_commit}, found {head}")
    if status or symbolic:
        raise checkpoint.CheckpointError("selected released tree must be clean and detached")
    message = _git(release_tree, "show", "-s", "--format=%B", "HEAD")
    trailers = [line.strip() for line in message.splitlines() if line.startswith("Skill-Craft-Release:")]
    if len(trailers) != 1 or not trailers[0].partition(":")[2].strip():
        raise checkpoint.CheckpointError("selected tree HEAD lacks one non-empty Skill-Craft-Release trailer")
    for required in ("test/shiploop_e2e/run.py", "test/shiploop_e2e/checks/csv_report.py"):
        if not (release_tree / required).is_file():
            raise checkpoint.CheckpointError(f"selected release tree lacks {required}")
    return {"release_tree": str(release_tree), "head": head, "tree": tree,
            "release_commit": expected_commit, "release_trailer": trailers[0]}


def _experiment_checks() -> Path:
    path = HERE / "checks.py"
    if not path.is_file():
        raise checkpoint.CheckpointError(f"experiment checks are missing: {path}")
    return path.resolve(strict=True)


def _paths(release_tree: Path, output_root: Path, trial_id: str, link: str,
           inventory_arg: Path | None, *, resume: bool = False) -> tuple[Path, Path, Path, Path]:
    output_root = checkpoint.external_path(output_root, "external output root", (SOURCE_ROOT, release_tree))
    inventory = checkpoint.external_path(inventory_arg or output_root / "runs.json", "external runs inventory",
                                         (SOURCE_ROOT, release_tree))
    baseline = checkpoint.external_path(output_root / "baselines.jsonl", "external baseline", (SOURCE_ROOT, release_tree))
    output = checkpoint.external_path(output_root / trial_id / link, "run output", (SOURCE_ROOT, release_tree))
    if checkpoint._within(inventory, output) or checkpoint._within(baseline, output):
        raise checkpoint.CheckpointError("inventory and baseline must stay outside the product run directory")
    if resume and not output.is_dir():
        raise checkpoint.CheckpointError(f"--resume needs the existing run output directory: {output}")
    if not resume and output.exists():
        raise checkpoint.CheckpointError(f"run output already exists; raw prior output is preserved: {output}")
    return output_root, inventory, baseline, output


def _prompt(link: str) -> tuple[Path, str, str, str]:
    name, _ = PROMPTS[link]
    path = HERE / name
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    # Match the existing experiment launchers: command substitution removes trailing newlines;
    # run.py then writes one newline into prompt.txt.
    argument = text.rstrip("\n")
    invoked_digest = checkpoint.sha256_bytes((argument + "\n").encode("utf-8"))
    return path, argument, checkpoint.sha256_bytes(raw), invoked_digest


def _check_commands(release_tree: Path, link: str) -> tuple[list[str], dict[str, Any]]:
    check_file = _experiment_checks()
    csv_file = (release_tree / "test/shiploop_e2e/checks/csv_report.py").resolve(strict=True)
    common = [f"python3 {shlex.quote(str(csv_file))} {mode}" for mode in BASE_MODES]
    specific = [f"python3 {shlex.quote(str(check_file))} {mode}" for mode in LINK_CHECKS[link]]
    files = {
        "checks": {"path": str(check_file), "sha256": checkpoint.sha256_file(check_file)},
        "csv_report": {"path": str(csv_file), "sha256": checkpoint.sha256_file(csv_file)},
    }
    return [*common, *specific], {"commands": [*common, *specific], "files": files}


def _identity(release: dict[str, str], trial_id: str, link: str, prompt_info: dict[str, str],
              checks: dict[str, Any], calibration: dict[str, Any]) -> dict[str, Any]:
    return {
        "trial_id": trial_id,
        "link": link,
        "prompt": prompt_info,
        "source": release,
        "checks": checks,
        "calibration": calibration,
        "model": MODEL,
        "source_mode": "checkout",
    }


def _inventory_read(path: Path) -> dict[str, Any]:
    return checkpoint.read_inventory(path)


def _write_inventory(path: Path, inventory: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists():
        raise checkpoint.CheckpointError(f"inventory temporary file already exists: {temporary}")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(inventory, stream, indent=2, ensure_ascii=True)
        stream.write("\n")
    os.replace(temporary, path)


def _append_row(path: Path, row: dict[str, Any]) -> None:
    inventory = _inventory_read(path)
    if any(existing.get("run_id") == row["run_id"] for existing in inventory["runs"] if isinstance(existing, dict)):
        raise checkpoint.CheckpointError(f"inventory already has {row['run_id']}; choose a new trial id")
    inventory["runs"].append(row)
    _write_inventory(path, inventory)


def _replace_row(path: Path, row: dict[str, Any]) -> None:
    inventory = _inventory_read(path)
    found = 0
    for index, existing in enumerate(inventory["runs"]):
        if isinstance(existing, dict) and existing.get("run_id") == row["run_id"]:
            inventory["runs"][index] = row
            found += 1
    if found != 1:
        raise checkpoint.CheckpointError(f"inventory lost or duplicated {row['run_id']} while the run was active")
    _write_inventory(path, inventory)


def _expected_predecessor_identity(release: dict[str, str], trial_id: str, prior_link: str,
                                   calibration_path: Path) -> dict[str, Any]:
    prompt_path, _, source_digest, invoked_digest = _prompt(prior_link)
    prompt_info = {"path": str(prompt_path.resolve()), "source_sha256": source_digest, "invoked_sha256": invoked_digest}
    commands, checks = _check_commands(Path(release["release_tree"]), prior_link)
    del commands
    calibration = checkpoint.calibration_identity(calibration_path, checks["files"]["csv_report"]["path"], checks["files"])
    return _identity(release, trial_id, prior_link, prompt_info, checks, calibration)


def _validate_copied_lineage(result: dict[str, Any], run_dir: Path, predecessor: dict[str, Any]) -> dict[str, Any]:
    expected_head = predecessor["work_snapshot"]["head"]
    expected_tree = predecessor["work_snapshot"]["tree"]
    follow_on = result.get("follow_on") or {}
    errors = []
    if not checkpoint._same_path(follow_on.get("prior", ""), predecessor["run_dir"]):
        errors.append("follow_on.prior differs from checkpoint run")
    if follow_on.get("start_head") != expected_head:
        errors.append("follow_on.start_head differs from reviewed predecessor HEAD")
    if follow_on.get("prior_case") != "custom" or follow_on.get("prior_pass") is not True:
        errors.append("follow_on metadata does not identify the passing custom predecessor")
    child_work = run_dir / "work"
    try:
        final_head = _git(child_work, "rev-parse", "HEAD")
        recorded_tree = _git(child_work, "rev-parse", f"{expected_head}^{{tree}}")
        ancestor = subprocess.run(["git", "-C", str(child_work), "merge-base", "--is-ancestor", expected_head, final_head],
                                  capture_output=True, check=False).returncode == 0
        if recorded_tree != expected_tree:
            errors.append("copied predecessor commit tree differs from reviewed checkpoint")
        if not ancestor:
            errors.append("reviewed predecessor HEAD is not in the completed child history")
    except checkpoint.CheckpointError as exc:
        final_head = None
        errors.append(str(exc))
    return {"pass": not errors, "expected_head": expected_head, "expected_tree": expected_tree,
            "final_head": final_head, "errors": errors}


def _resume_artifact_paths(run_dir: Path) -> list[Path]:
    paths = [run_dir / name for name in ("result.json", "invocation.json", "metrics.json", "shiploop-run.json")]
    paths.extend(sorted(run_dir.glob("invocation-resume-*.json")))
    selected_run = None
    result_path = run_dir / "result.json"
    if result_path.is_file():
        with result_path.open(encoding="utf-8") as stream:
            result = json.load(stream)
        shiploop = result.get("shiploop") or {}
        selected_run = shiploop.get("run_dir")
    if not selected_run and (run_dir / "shiploop-run.json").is_file():
        with (run_dir / "shiploop-run.json").open(encoding="utf-8") as stream:
            selected_run = json.load(stream).get("run_dir")
    if isinstance(selected_run, str) and selected_run:
        selected_dir = Path(selected_run).resolve(strict=True)
        if not checkpoint._within(selected_dir, run_dir.resolve()) or not selected_dir.is_dir():
            raise checkpoint.CheckpointError("selected ShipLoop run is outside the current output during resume archival")
        paths.extend((selected_dir / "state.md", selected_dir / "report.html"))
    found = []
    seen: set[Path] = set()
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        if path.is_symlink():
            raise checkpoint.CheckpointError(f"resume artifact may not be a symlink: {path}")
        if not path.exists():
            continue
        if not path.is_file():
            raise checkpoint.CheckpointError(f"resume artifact must be a regular file: {path}")
        resolved = path.resolve(strict=True)
        if not checkpoint._within(resolved, run_dir.resolve()):
            raise checkpoint.CheckpointError(f"resume artifact escapes the run output: {path}")
        found.append(path)
    return found


def _archive_resume_artifacts(run_dir: Path, archive_dir: Path, release_tree: Path) -> dict[str, Any]:
    archive_dir = checkpoint.external_path(archive_dir, "resume attempt archive",
                                           (SOURCE_ROOT, release_tree, run_dir))
    if archive_dir.exists():
        raise checkpoint.CheckpointError(f"resume attempt archive already exists; preserving it: {archive_dir}")
    archive_dir.mkdir(parents=True, exist_ok=False)
    entries = []
    for source in _resume_artifact_paths(run_dir):
        rel = source.relative_to(run_dir).as_posix()
        destination = archive_dir / "files" / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        before = checkpoint.sha256_file(source)
        shutil.copyfile(source, destination)
        copied = checkpoint.sha256_file(destination)
        after = checkpoint.sha256_file(source)
        if before != copied or after != before:
            raise checkpoint.CheckpointError(f"resume artifact changed while it was archived: {source}")
        entries.append({"source": rel, "archive": destination.relative_to(archive_dir).as_posix(),
                        "sha256": before, "size": source.stat().st_size})
    if not {"result.json", "invocation.json"}.issubset({entry["source"] for entry in entries}):
        raise checkpoint.CheckpointError("resume archive did not preserve the original result and invocation")
    manifest = {"schema": "shiploop-incremental-attempt-archive/v1", "run_dir": str(run_dir),
                "artifacts": entries}
    manifest_path = archive_dir / "manifest.json"
    with manifest_path.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=True)
        stream.write("\n")
    return {"path": str(archive_dir), "manifest": str(manifest_path),
            "manifest_sha256": checkpoint.sha256_file(manifest_path), "artifacts": entries}


def _next_archive_path(output_root: Path, trial_id: str, link: str, attempts: list[dict[str, Any]]) -> tuple[Path, int]:
    number = len(attempts) + 2  # attempt 1 is the original invocation
    parent = output_root / "attempt-archives" / trial_id / link
    while True:
        candidate = parent / f"attempt-{number:03d}"
        if not candidate.exists():
            return candidate, number
        number += 1


def _post_run(row: dict[str, Any], run_dir: Path, release: dict[str, str], identity: dict[str, Any],
              predecessor: dict[str, Any] | None, runner_returncode: int,
              resume_attempt: dict[str, Any] | None = None,
              resume_invocations_before: set[str] | None = None) -> dict[str, Any]:
    row["runner_returncode"] = runner_returncode
    row["finished_at"] = _now()
    row.pop("terminal_artifacts", None)
    result_path = run_dir / "result.json"
    invocation_path = run_dir / "invocation.json"
    prompt_path = run_dir / "prompt.txt"
    result: dict[str, Any] = {}
    problems = []
    for label, path, key in (("result", result_path, "result_sha256"),
                             ("invocation", invocation_path, "invocation_sha256"),
                             ("prompt", prompt_path, "prompt_file_sha256")):
        if path.is_file():
            row[key] = checkpoint.sha256_file(path)
        else:
            problems.append(f"missing {label}")
    if result_path.is_file():
        try:
            result = checkpoint._read_json(result_path, "result")
            row["terminal_artifacts"] = checkpoint.terminal_artifacts(run_dir, result)
        except checkpoint.CheckpointError as exc:
            problems.append(str(exc))
    work = run_dir / "work"
    if (work / ".git").exists():
        try:
            row["graded_work_snapshot"] = checkpoint.work_snapshot(work)
        except checkpoint.CheckpointError as exc:
            problems.append(str(exc))
    else:
        problems.append("missing product work Git repository")
    if predecessor:
        row["copied_start_lineage"] = _validate_copied_lineage(result, run_dir, predecessor)
        if not row["copied_start_lineage"]["pass"]:
            problems.extend(row["copied_start_lineage"]["errors"])
    try:
        checkpoint.validate_source_and_checks(identity)
    except (checkpoint.CheckpointError, OSError) as exc:
        problems.append(f"post-run source/check identity changed: {exc}")
    if runner_returncode != 0:
        problems.append(f"runner exited {runner_returncode}")
    if result.get("pass") is not True:
        problems.append("result pass is not true")
    row["status"] = "complete" if not problems else "failed"
    row["post_run_problems"] = problems
    attempt_summary = {
        "runner_returncode": runner_returncode,
        "status": row["status"],
        "result_sha256": row.get("result_sha256"),
        "invocation_sha256": row.get("invocation_sha256"),
        "metrics_sha256": checkpoint.sha256_file(run_dir / "metrics.json") if (run_dir / "metrics.json").is_file() else None,
        "terminal_artifacts": row.get("terminal_artifacts"),
        "finished_at": row["finished_at"],
    }
    if resume_attempt is None:
        row["original_invocation_sha256"] = row.get("invocation_sha256")
        row["initial_attempt"] = attempt_summary
        row.setdefault("attempts", [])
    else:
        resume_attempt.update(attempt_summary)
        resume_attempt["status_after"] = row["status"]
        resume_invocations_before = resume_invocations_before or set()
        new_invocations = [path for path in run_dir.glob("invocation-resume-*.json")
                           if path.name not in resume_invocations_before]
        if new_invocations:
            latest = max(new_invocations, key=lambda path: (path.stat().st_mtime_ns, path.name))
            invocation = checkpoint._read_json(latest, "latest resume invocation")
            latest_identity = {
                "path": str(latest), "sha256": checkpoint.sha256_file(latest),
                "host": invocation.get("host"), "model": invocation.get("model"),
                "effort": invocation.get("effort"), "versions": invocation.get("versions"),
                "checks": invocation.get("checks"), "cwd": invocation.get("cwd"),
                "resumed_run": invocation.get("resumed_run"),
            }
            resume_attempt["resume_invocation"] = latest_identity
            row["latest_resume_invocation"] = latest_identity
        else:
            resume_attempt["resume_invocation"] = None
            problems.append("source harness wrote no invocation-resume record")
            row["status"] = "failed"
            row["post_run_problems"] = problems
    return row


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    _validate_segment(args.trial_id, "trial id")
    release = release_identity(args.release_tree, args.release_commit)
    resume = bool(getattr(args, "resume", False))
    output_root, inventory_path, baseline_path, output = _paths(release_tree=Path(release["release_tree"]),
                                                                  output_root=args.output_root,
                                                                  trial_id=args.trial_id, link=args.link,
                                                                  inventory_arg=args.inventory, resume=resume)
    prompt_path, prompt_arg, source_digest, invoked_digest = _prompt(args.link)
    prompt_info = {"path": str(prompt_path.resolve()), "source_sha256": source_digest,
                   "invoked_sha256": invoked_digest}
    commands, checks = _check_commands(Path(release["release_tree"]), args.link)
    calibration_arg = getattr(args, "calibration", None) or (output_root / "calibration.json")
    calibration_path = checkpoint.external_path(calibration_arg, "calibration file",
                                                (SOURCE_ROOT, Path(release["release_tree"]), output), must_exist=True)
    calibration = checkpoint.calibration_identity(calibration_path, checks["files"]["csv_report"]["path"], checks["files"])
    identity = _identity(release, args.trial_id, args.link, prompt_info, checks, calibration)
    checkpoint.validate_source_and_checks(identity)
    checkpoint_path = None
    predecessor = None
    if PROMPTS[args.link][1]:
        prior_link = PROMPTS[args.link][1]
        checkpoint_path = checkpoint.external_path(
            args.checkpoint or (output_root / "checkpoints" / args.trial_id / f"{prior_link}.json"),
            "predecessor checkpoint", (SOURCE_ROOT, Path(release["release_tree"])), must_exist=True,
        )
        prior_identity = _expected_predecessor_identity(release, args.trial_id, prior_link, calibration_path)
        predecessor = checkpoint.verify_checkpoint(checkpoint_path, expected_identity=prior_identity,
                                                    output_root=output_root, inventory_path=inventory_path)
    elif args.checkpoint:
        raise checkpoint.CheckpointError("the base link has no predecessor checkpoint")
    argv = [sys.executable, "-I", str(Path(release["release_tree"]) / "test/shiploop_e2e/run.py")]
    if resume:
        inventory = _inventory_read(inventory_path)
        row = checkpoint.inventory_row(inventory, f"{args.trial_id}:{args.link}")
        if row.get("trial_id") != args.trial_id or row.get("link") != args.link or not checkpoint._same_path(row.get("output", ""), output):
            raise checkpoint.CheckpointError("resume inventory row does not identify this trial, link, and output")
        resume_state = checkpoint.validate_resume_candidate(output, row, identity)
        argv.extend(("--resume-run", str(output), "--host", MODEL["host"], "--model", MODEL["model"],
                     "--effort", MODEL["effort"], "--source", "checkout", "--baseline", str(baseline_path)))
        attempts = row.get("attempts") if isinstance(row.get("attempts"), list) else []
        archive_path, attempt_number = _next_archive_path(output_root, args.trial_id, args.link, attempts)
        resume_invocations_before = {path.name for path in output.glob("invocation-resume-*.json")}
    else:
        inventory = _inventory_read(inventory_path)
        run_id = f"{args.trial_id}:{args.link}"
        if any(existing.get("run_id") == run_id for existing in inventory["runs"] if isinstance(existing, dict)):
            raise checkpoint.CheckpointError(f"inventory already has {run_id}; choose a new trial id or pass --resume")
        row = {
            "run_id": run_id,
            "trial_id": args.trial_id,
            "link": args.link,
            "status": "launching",
            "output": str(output),
            "inventory_path": str(inventory_path),
            "identity": identity,
            "argv": [],
            "shell_argv": "",
            "predecessor_checkpoint": None,
            "started_at": None,
            "attempts": [],
        }
        argv.extend(("--prompt", prompt_arg, "--host", MODEL["host"], "--model", MODEL["model"],
                     "--effort", MODEL["effort"], "--source", "checkout", "--baseline", str(baseline_path)))
        if predecessor:
            argv.extend(("--continue-from", predecessor["run_dir"]))
        argv.extend(("--output", str(output)))
        for command in commands:
            argv.extend(("--check", command))
        row["argv"] = argv
        row["shell_argv"] = shlex.join(argv)
        row["predecessor_checkpoint"] = ({"path": str(checkpoint_path), "sha256": checkpoint.sha256_file(checkpoint_path)}
                                         if checkpoint_path else None)
        resume_state = None
        archive_path = None
        attempt_number = None
        resume_invocations_before = set()
    if resume:
        row = dict(row)
    row["latest_argv"] = argv
    row["latest_shell_argv"] = shlex.join(argv)
    if resume:
        row["latest_resume_started_at"] = None
    return {"release": release, "output_root": output_root, "inventory_path": inventory_path,
            "baseline_path": baseline_path, "output": output, "identity": identity, "argv": argv,
            "row": row, "predecessor": predecessor, "resume": resume, "resume_state": resume_state,
            "archive_path": archive_path, "attempt_number": attempt_number,
            "resume_invocations_before": resume_invocations_before,
            "checkpoint_path": checkpoint_path, "calibration_path": calibration_path}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--release-tree", type=Path, required=True, help="clean detached checkout of the selected released tree")
    p.add_argument("--release-commit", default=DEFAULT_RELEASE_COMMIT,
                   help=f"full released commit to pin across the chain (default: {DEFAULT_RELEASE_COMMIT})")
    p.add_argument("--output-root", type=Path, required=True, help="external directory for one trial's raw runs")
    p.add_argument("--inventory", type=Path, help="external runs.json (default: OUTPUT_ROOT/runs.json)")
    p.add_argument("--calibration", type=Path, help="passing checks calibration JSON (default: OUTPUT_ROOT/calibration.json)")
    p.add_argument("--trial-id", required=True, help="one chain identity, such as pilot-a")
    p.add_argument("--link", choices=tuple(PROMPTS), required=True, help="run exactly one link")
    p.add_argument("--checkpoint", type=Path, help="explicit predecessor checkpoint for filter/output")
    p.add_argument("--resume", action="store_true", help="resume this interrupted link in the same source-harness output")
    p.add_argument("--dry-run", action="store_true", help="validate inputs and print safely quoted argv without launching")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        plan = build_plan(args)
        if args.dry_run:
            print(json.dumps({"identity": plan["identity"], "argv": plan["argv"],
                              "shell_argv": shlex.join(plan["argv"])}, indent=2, ensure_ascii=True))
            return 0
        resume_attempt = None
        if plan["resume"]:
            row = plan["row"]
            archive = _archive_resume_artifacts(plan["output"], plan["archive_path"],
                                                Path(plan["release"]["release_tree"]))
            checkpoint.validate_source_and_checks(plan["identity"])
            latest_inventory = _inventory_read(plan["inventory_path"])
            latest_row = checkpoint.inventory_row(latest_inventory, row["run_id"])
            current_state = checkpoint.validate_resume_candidate(plan["output"], latest_row, plan["identity"])
            if (current_state["result_sha256"] != plan["resume_state"]["result_sha256"]
                    or current_state["invocation_sha256"] != plan["resume_state"]["invocation_sha256"]
                    or current_state["work_snapshot"] != plan["resume_state"]["work_snapshot"]):
                raise checkpoint.CheckpointError("interrupted result, invocation, or partial work changed before resume")
            resume_attempt = {
                "number": plan["attempt_number"],
                "kind": "resume",
                "status": "launching",
                "started_at": _now(),
                "archive": archive,
                "before": {
                    "status": latest_row.get("status"),
                    "runner_returncode": latest_row.get("runner_returncode"),
                    "post_run_problems": latest_row.get("post_run_problems", []),
                    "result_sha256": current_state["result_sha256"],
                    "invocation_sha256": current_state["invocation_sha256"],
                    "metrics_sha256": current_state["metrics_sha256"],
                    "work_snapshot_sha256": checkpoint.canonical_digest(current_state["work_snapshot"]),
                },
                "argv": plan["argv"],
                "shell_argv": shlex.join(plan["argv"]),
            }
            row["attempts"] = list(row.get("attempts") or []) + [resume_attempt]
            row["original_invocation_sha256"] = row.get("original_invocation_sha256") or row.get("invocation_sha256")
            row["latest_argv"] = plan["argv"]
            row["latest_shell_argv"] = shlex.join(plan["argv"])
            row["latest_resume_started_at"] = resume_attempt["started_at"]
            row["status"] = "launching"
            _replace_row(plan["inventory_path"], row)
        else:
            checkpoint.validate_source_and_checks(plan["identity"])
            plan["row"]["started_at"] = _now()
            _append_row(plan["inventory_path"], plan["row"])
        print(f"launching {plan['row']['run_id']} -> {plan['output']}", flush=True)
        runner = subprocess.run(plan["argv"], cwd=plan["release"]["release_tree"], check=False)
        final = _post_run(plan["row"], plan["output"], plan["release"], plan["identity"],
                          plan["predecessor"], runner.returncode, resume_attempt,
                          plan["resume_invocations_before"] if plan["resume"] else None)
        _replace_row(plan["inventory_path"], final)
        print(json.dumps({"run_id": final["run_id"], "status": final["status"],
                          "output": final["output"], "post_run_problems": final["post_run_problems"]}, indent=2))
        return 0 if final["status"] == "complete" else 1
    except (checkpoint.CheckpointError, OSError, UnicodeError) as exc:
        print(f"launch refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
