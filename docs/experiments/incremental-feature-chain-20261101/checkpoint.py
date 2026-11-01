#!/usr/bin/env python3
"""Create and verify evidence-bound checkpoints for the incremental CSV pilot.

The operator supplies the five semantic judgments. This module checks that every
judgment is an explicit pass tied to retained evidence; it does not grade meaning.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
from typing import Any


SCHEMA = "shiploop-incremental-checkpoint/v1"
RUNS_SCHEMA = "shiploop-incremental-runs/v1"
REVIEW_SNAPSHOT_SCHEMA = "shiploop-incremental-review-snapshot/v1"
DIMENSIONS = (
    "requested_behavior",
    "prior_behavior",
    "decision_handling",
    "knowledge_and_organization",
    "workflow_and_lineage",
)
MODEL = {"host": "codex", "model": "gpt-6.1-terra", "effort": "high"}
EXPERIMENT_DIR = Path(__file__).resolve().parent
SOURCE_ROOT = EXPERIMENT_DIR.parents[2]
CALIBRATION_INPUTS = {
    "checks", "csv_report", "checks_source", "procedural_fixture", "argparse_fixture",
    "test_fixture", "calibrator", "request_base", "request_filter", "request_output",
}
RESUMABLE_HOST_FAILURES = ("resumed host failed ",)


class CheckpointError(ValueError):
    """A checkpoint or its evidence does not satisfy the pilot contract."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(encoded)


def _within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _require_outside(path: Path, label: str, *roots: Path) -> None:
    path = path.resolve()
    for root in roots:
        root = root.resolve()
        if _within(path, root):
            raise CheckpointError(f"{label} must stay outside {root}: {path}")


def external_path(path: str | Path, label: str, forbidden: tuple[Path, ...] = (), *, must_exist: bool = False) -> Path:
    """Resolve an artifact and refuse any path inside a source, subject, or product tree."""
    candidate = Path(path).expanduser()
    try:
        resolved = candidate.resolve(strict=must_exist)
    except OSError as exc:
        raise CheckpointError(f"{label}: cannot resolve {candidate}: {exc}") from exc
    for root in forbidden:
        root = root.resolve()
        if _within(resolved, root):
            raise CheckpointError(f"{label}: must stay outside {root}: {resolved}")
    return resolved


def _git(repo: Path, *args: str, check: bool = True) -> bytes:
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False)
    if check and done.returncode:
        detail = done.stderr.decode("utf-8", "replace").strip()
        raise CheckpointError(f"git {' '.join(args)} failed in {repo}: {detail}")
    return done.stdout


def _git_text(repo: Path, *args: str) -> str:
    return _git(repo, *args).decode("utf-8", "strict").strip()


def _listed_paths(repo: Path, *args: str) -> list[str]:
    raw = _git(repo, *args)
    return [os.fsdecode(item) for item in raw.split(b"\0") if item]


def _file_record(path: Path) -> dict[str, Any]:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {"kind": "missing", "mode": None, "sha256": None}
    mode = stat.S_IMODE(info.st_mode)
    if stat.S_ISLNK(info.st_mode):
        target = os.readlink(path)
        return {"kind": "symlink", "mode": mode, "target": target,
                "target_sha256": sha256_bytes(os.fsencode(target))}
    if stat.S_ISREG(info.st_mode):
        return {"kind": "file", "mode": mode, "sha256": sha256_file(path)}
    raise CheckpointError(f"unsupported special file in product manifest: {path}")


def work_snapshot(work: str | Path) -> dict[str, Any]:
    """Record Git lineage plus every copied work file except the root Git database."""
    work = Path(work).resolve(strict=True)
    if not (work / ".git").exists():
        raise CheckpointError(f"product work has no .git: {work}")
    head = _git_text(work, "rev-parse", "HEAD")
    tree = _git_text(work, "rev-parse", "HEAD^{tree}")
    status = _git(work, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    tracked = _listed_paths(work, "ls-files", "-z")
    untracked = _listed_paths(work, "ls-files", "--others", "--exclude-standard", "-z")
    ignored = _listed_paths(work, "ls-files", "--others", "--ignored", "--exclude-standard", "-z")
    all_files: set[str] = set()
    for root, directories, names in os.walk(work, followlinks=False):
        here = Path(root)
        for name in tuple(directories):
            if name == ".git":
                directories.remove(name)
                continue
            child = here / name
            if child.is_symlink():
                all_files.add(child.relative_to(work).as_posix())
                directories.remove(name)
        for name in names:
            child = here / name
            if child.relative_to(work).as_posix() != ".git":
                all_files.add(child.relative_to(work).as_posix())
    classifications = {
        "tracked": set(tracked),
        "declared_untracked": set(untracked),
        "ignored": set(ignored),
    }
    classified = set().union(*classifications.values())
    unknown = sorted(all_files - classified)
    if unknown:
        raise CheckpointError(f"product files were not classified by Git status: {unknown[:5]}")

    def records(paths: set[str]) -> list[dict[str, Any]]:
        found = []
        for rel in sorted(paths):
            relative = PurePosixPath(rel.replace(os.sep, "/"))
            if relative.is_absolute() or any(part in ("", ".", "..") for part in relative.parts):
                raise CheckpointError(f"unsafe Git path in product manifest: {rel!r}")
            candidate = work.joinpath(*relative.parts)
            if not _within(candidate.parent.resolve(), work):
                raise CheckpointError(f"product path escapes its checkout through a parent symlink: {rel!r}")
            found.append({"path": rel, **_file_record(candidate)})
        return found

    return {
        "head": head,
        "tree": tree,
        "status_hex": status.hex(),
        "tracked": records(classifications["tracked"]),
        "declared_untracked": records(classifications["declared_untracked"]),
        "ignored": records(classifications["ignored"]),
    }


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CheckpointError(f"{label}: cannot read JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CheckpointError(f"{label}: expected a JSON object at {path}")
    return value


def terminal_artifacts(run_dir: str | Path, result: dict[str, Any]) -> dict[str, Any]:
    """Hash the terminal receipt and report outside work but retained in this run output."""
    run_dir = Path(run_dir).resolve(strict=True)
    shiploop = result.get("shiploop") or {}
    raw_run = shiploop.get("run_dir")
    if not isinstance(raw_run, str) or not raw_run:
        raise CheckpointError("terminal result has no ShipLoop run directory")
    shiploop_run = Path(raw_run).resolve(strict=True)
    if not _within(shiploop_run, run_dir) or not shiploop_run.is_dir():
        raise CheckpointError("ShipLoop terminal run directory is not retained inside this output")
    receipt_path = run_dir / "shiploop-run.json"
    receipt = _read_json(receipt_path, "ShipLoop terminal identity receipt")
    if not _same_path(receipt.get("run_dir", ""), shiploop_run):
        raise CheckpointError("shiploop-run.json does not identify the result's selected ShipLoop run")
    files = {
        "shiploop_run": receipt_path,
        "state": shiploop_run / "state.md",
        "report": shiploop_run / "report.html",
    }
    found = {}
    for label, path in files.items():
        try:
            resolved = path.resolve(strict=True)
        except OSError as exc:
            raise CheckpointError(f"terminal {label} artifact is missing: {path}") from exc
        if path.is_symlink() or not _within(resolved, run_dir) or not resolved.is_file():
            raise CheckpointError(f"terminal {label} artifact must be a regular retained file: {path}")
        found[label] = {"path": path.relative_to(run_dir).as_posix(), **_file_record(path)}
    return found


def read_inventory(path: str | Path) -> dict[str, Any]:
    path = Path(path).resolve()
    if not path.exists():
        return {"schema": RUNS_SCHEMA, "runs": []}
    value = _read_json(path, "runs inventory")
    if value.get("schema") != RUNS_SCHEMA or not isinstance(value.get("runs"), list):
        raise CheckpointError(f"runs inventory has an unsupported shape: {path}")
    return value


def inventory_row(inventory: dict[str, Any], run_id: str) -> dict[str, Any]:
    rows = [row for row in inventory["runs"] if isinstance(row, dict) and row.get("run_id") == run_id]
    if len(rows) != 1:
        raise CheckpointError(f"runs inventory must contain exactly one row for {run_id!r}; found {len(rows)}")
    return rows[0]


def _same_path(a: str | Path, b: str | Path) -> bool:
    return Path(a).expanduser().resolve() == Path(b).expanduser().resolve()


def _safe_segment(value: str, label: str) -> None:
    if not isinstance(value, str) or not value or value in (".", "..") or not value.replace("-", "").replace("_", "").isalnum():
        raise CheckpointError(f"unsafe {label}: {value!r}")


def _validate_identity_shape(identity: Any) -> None:
    if not isinstance(identity, dict):
        raise CheckpointError("run identity is not an object")
    _safe_segment(identity.get("trial_id"), "trial id")
    _safe_segment(identity.get("link"), "link")
    if identity.get("source_mode") != "checkout" or identity.get("model") != MODEL:
        raise CheckpointError("run identity does not name the fixed checkout source and model profile")
    source = identity.get("source")
    required_source = ("release_tree", "head", "tree", "release_commit", "release_trailer")
    if not isinstance(source, dict) or any(not isinstance(source.get(key), str) or not source[key] for key in required_source):
        raise CheckpointError("run identity has incomplete released-source identity")
    prompt = identity.get("prompt")
    if not isinstance(prompt, dict) or any(not isinstance(prompt.get(key), str) or not prompt[key]
                                           for key in ("path", "source_sha256", "invoked_sha256")):
        raise CheckpointError("run identity has incomplete prompt identity")
    checks = identity.get("checks")
    if (not isinstance(checks, dict) or not isinstance(checks.get("commands"), list)
            or not all(isinstance(command, str) for command in checks["commands"])):
        raise CheckpointError("run identity has incomplete check commands")
    calibration = identity.get("calibration")
    if (not isinstance(calibration, dict)
            or any(not isinstance(calibration.get(key), str) or not calibration[key]
                   for key in ("path", "sha256", "inputs_sha256"))):
        raise CheckpointError("run identity has incomplete calibration identity")


def _calibration_module():
    path = EXPERIMENT_DIR / "calibrate_checks.py"
    if not path.is_file():
        raise CheckpointError(f"calibration script is missing: {path}")
    spec = importlib.util.spec_from_file_location("shiploop_incremental_calibrate_checks", path)
    if spec is None or spec.loader is None:
        raise CheckpointError(f"cannot load calibration script: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _normalize_input_manifest(value: Any, label: str) -> dict[str, dict[str, str]]:
    if not isinstance(value, dict) or set(value) != CALIBRATION_INPUTS:
        raise CheckpointError(f"calibration {label} must contain exactly the ten frozen input labels")
    normalized: dict[str, dict[str, str]] = {}
    for name, item in value.items():
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise CheckpointError(f"calibration input {name!r} must record an absolute path and SHA-256")
        raw_path, digest = item.get("path"), item.get("sha256")
        if not isinstance(raw_path, str) or not Path(raw_path).is_absolute():
            raise CheckpointError(f"calibration input {name!r} path must be absolute")
        if (not isinstance(digest, str) or len(digest) != 64
                or any(char not in "0123456789abcdef" for char in digest)):
            raise CheckpointError(f"calibration input {name!r} has an invalid SHA-256")
        normalized[name] = {"path": str(Path(raw_path).resolve()), "sha256": digest}
    return normalized


def _load_calibration(path: Path) -> dict[str, Any]:
    calibration = _read_json(path, "calibration")
    if (calibration.get("schema_version") != 1
            or calibration.get("calibration") != "incremental-feature-chain-20261101"
            or calibration.get("live_model_calls") != 0):
        raise CheckpointError("calibration does not identify the no-model frozen pilot matrix")
    summary = calibration.get("summary")
    if not isinstance(summary, dict) or summary.get("all_expectations_matched") is not True:
        raise CheckpointError("calibration did not pass all frozen expectations")
    context = calibration.get("context")
    context_after = calibration.get("context_after")
    if (not isinstance(context, dict) or not isinstance(context_after, dict)
            or context != context_after
            or any(not isinstance(context.get(key), str) for key in ("head", "tree", "status"))):
        raise CheckpointError("calibration context changed or is incomplete")
    inputs = _normalize_input_manifest(calibration.get("inputs"), "inputs")
    inputs_after = _normalize_input_manifest(calibration.get("inputs_after"), "inputs_after")
    if inputs != inputs_after:
        raise CheckpointError("calibration input manifest changed while its checks ran")
    return {"inputs": inputs, "inputs_after": inputs_after, "context": context,
            "context_after": context_after, "summary_all_expectations_matched": True}


def calibration_identity(path: str | Path, base_checks: str | Path,
                         check_files: dict[str, Any]) -> dict[str, Any]:
    path = Path(path).expanduser().resolve(strict=True)
    calibration = _load_calibration(path)
    current = _normalize_input_manifest(_calibration_module().input_manifest(Path(base_checks).resolve(strict=True)),
                                        "current input manifest")
    _compare_calibration_inputs(calibration["inputs"], current)
    if calibration["inputs"]["checks"]["sha256"] != check_files["checks"]["sha256"]:
        raise CheckpointError("calibration checks.py digest differs from the launcher check")
    if calibration["inputs"]["csv_report"]["sha256"] != check_files["csv_report"]["sha256"]:
        raise CheckpointError("calibration csv_report.py digest differs from the selected released check")
    return {"path": str(path), "sha256": sha256_file(path),
            "inputs": calibration["inputs"], "inputs_after": calibration["inputs_after"],
            "inputs_sha256": canonical_digest(calibration["inputs"]),
            "context": calibration["context"], "context_after": calibration["context_after"]}


def _compare_calibration_inputs(saved: dict[str, dict[str, str]], current: dict[str, dict[str, str]]) -> None:
    if set(saved) != CALIBRATION_INPUTS or set(current) != CALIBRATION_INPUTS:
        raise CheckpointError("calibration input manifest labels do not match the frozen inventory")
    for label in sorted(CALIBRATION_INPUTS):
        if saved[label]["sha256"] != current[label]["sha256"]:
            raise CheckpointError(f"calibration input {label!r} changed after calibration")
        if label != "csv_report" and saved[label]["path"] != current[label]["path"]:
            raise CheckpointError(f"calibration input {label!r} path changed after calibration")


def validate_calibration(identity: dict[str, Any]) -> None:
    expected = identity.get("calibration") or {}
    release_tree = Path((identity.get("source") or {}).get("release_tree", "")).resolve(strict=True)
    path = external_path(expected.get("path", ""), "calibration file", (SOURCE_ROOT, release_tree), must_exist=True)
    if sha256_file(path) != expected.get("sha256"):
        raise CheckpointError("calibration file changed after launch identity was recorded")
    calibration = _load_calibration(path)
    if (calibration["inputs"] != expected.get("inputs")
            or calibration["inputs_after"] != expected.get("inputs_after")
            or canonical_digest(calibration["inputs"]) != expected.get("inputs_sha256")
            or calibration["context"] != expected.get("context")
            or calibration["context_after"] != expected.get("context_after")):
        raise CheckpointError("calibration content differs from the launch identity")
    csv_report = release_tree / "test/shiploop_e2e/checks/csv_report.py"
    current = _normalize_input_manifest(_calibration_module().input_manifest(csv_report), "current input manifest")
    _compare_calibration_inputs(calibration["inputs"], current)
    files = (identity.get("checks") or {}).get("files") or {}
    for label, check_label in (("checks", "checks"), ("csv_report", "csv_report")):
        if calibration["inputs"][label]["sha256"] != (files.get(check_label) or {}).get("sha256"):
            raise CheckpointError(f"calibration {label} digest differs from the pinned check identity")


def validate_source_and_checks(identity: dict[str, Any]) -> None:
    _validate_identity_shape(identity)
    source = identity.get("source") or {}
    release_tree = Path(source.get("release_tree", "")).resolve(strict=True)
    if not (release_tree / ".git").exists():
        raise CheckpointError(f"pinned release tree has no .git: {release_tree}")
    head = _git_text(release_tree, "rev-parse", "HEAD")
    tree = _git_text(release_tree, "rev-parse", "HEAD^{tree}")
    status = _git(release_tree, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    symbolic = _git(release_tree, "symbolic-ref", "-q", "HEAD", check=False)
    message = _git_text(release_tree, "show", "-s", "--format=%B", "HEAD")
    trailers = [line.strip() for line in message.splitlines() if line.startswith("Skill-Craft-Release:")]
    if (head != source.get("head") or head != source.get("release_commit") or tree != source.get("tree")
            or status or symbolic or len(trailers) != 1 or trailers[0] != source.get("release_trailer")):
        raise CheckpointError("released subject tree changed, is dirty, or is no longer the pinned detached checkout")
    prompt = identity.get("prompt") or {}
    prompt_path = Path(prompt.get("path", "")).resolve(strict=True)
    if not _within(prompt_path, SOURCE_ROOT) or sha256_file(prompt_path) != prompt.get("source_sha256"):
        raise CheckpointError("request prompt file changed or is outside this source checkout")
    files = (identity.get("checks") or {}).get("files")
    if not isinstance(files, dict) or not files:
        raise CheckpointError("check identity must name its pinned source files")
    for label, record in files.items():
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise CheckpointError(f"check identity {label!r} has no file path")
        path = Path(record["path"]).resolve(strict=True)
        if label == "csv_report":
            if not _within(path, release_tree):
                raise CheckpointError("csv_report.py must come from the pinned released tree")
        elif not _within(path, SOURCE_ROOT):
            raise CheckpointError(f"experiment check {label!r} must come from this source checkout")
        if sha256_file(path) != record.get("sha256"):
            raise CheckpointError(f"pinned check file changed after grading: {path}")
    validate_calibration(identity)


def _require_result(run_dir: Path, identity: dict[str, Any], *, require_pass: bool = True) -> tuple[dict, dict, dict]:
    result = _read_json(run_dir / "result.json", "result")
    invocation = _read_json(run_dir / "invocation.json", "invocation")
    prompt_path = run_dir / "prompt.txt"
    if not prompt_path.is_file():
        raise CheckpointError(f"run has no saved prompt: {prompt_path}")
    if result.get("case") != "custom" or invocation.get("case") != "custom":
        raise CheckpointError("pilot links must be actual custom-prompt invocations")
    if not _same_path(result.get("output", ""), run_dir):
        raise CheckpointError("result output path does not identify this run directory")
    if not _same_path(invocation.get("cwd", ""), run_dir / "work"):
        raise CheckpointError("invocation cwd does not identify this run's product work")
    if sha256_file(prompt_path) != identity["prompt"]["invoked_sha256"]:
        raise CheckpointError("saved invocation prompt digest does not match the expected link")
    if invocation.get("host") != MODEL["host"] or invocation.get("model") != MODEL["model"] or invocation.get("effort") != MODEL["effort"]:
        raise CheckpointError("actual invocation host/model/effort does not match the pilot profile")
    versions = invocation.get("versions") or {}
    source = identity["source"]
    if versions.get("source") != "checkout" or versions.get("local_head") != source.get("head"):
        raise CheckpointError("actual invocation did not use the pinned released checkout")
    if invocation.get("checks") != identity["checks"].get("commands"):
        raise CheckpointError("actual invocation checks do not match the pinned check set")
    recorded_checks = result.get("checks")
    if not isinstance(recorded_checks, list) or [item.get("command") for item in recorded_checks if isinstance(item, dict)] != identity["checks"].get("commands"):
        raise CheckpointError("result does not record the complete pinned check set")
    if any(not isinstance(item, dict) or item.get("pass") is not True for item in recorded_checks):
        raise CheckpointError("one or more recorded product checks failed")
    termination = result.get("termination") or {}
    shiploop = result.get("shiploop") or {}
    process = result.get("process") or {}
    complete = (
        termination.get("engine_status") == "done"
        and termination.get("engine_stage") == "done"
        and termination.get("engine_unaccepted_stage") is None
        and shiploop.get("status") == "done"
        and shiploop.get("report_html") is True
        and process.get("returncode") == 0
    )
    if not complete:
        raise CheckpointError("result lacks terminal complete evidence (engine done, report present, process exit 0)")
    terminal_artifacts(run_dir, result)
    if require_pass and result.get("pass") is not True:
        raise CheckpointError("predecessor result pass is not true")
    return result, invocation, {"prompt_sha256": sha256_file(prompt_path)}


def _verify_resume_archive(record: dict[str, Any], run_dir: Path, identity: dict[str, Any],
                           before: dict[str, Any]) -> None:
    archive = record.get("archive") or {}
    release_tree = Path(identity["source"]["release_tree"]).resolve(strict=True)
    output_root = run_dir.parents[1]
    archive_dir = external_path(archive.get("path", ""), "resume attempt archive",
                                (SOURCE_ROOT, release_tree, run_dir), must_exist=True)
    expected_parent = output_root / "attempt-archives" / identity["trial_id"] / identity["link"]
    if not _within(archive_dir, expected_parent.resolve()):
        raise CheckpointError("resume attempt archive is outside this trial/link archive directory")
    manifest_path = external_path(archive.get("manifest", ""), "resume archive manifest",
                                  (SOURCE_ROOT, release_tree, run_dir), must_exist=True)
    if not _within(manifest_path, archive_dir) or sha256_file(manifest_path) != archive.get("manifest_sha256"):
        raise CheckpointError("resume archive manifest changed after the attempt was recorded")
    manifest = _read_json(manifest_path, "resume archive manifest")
    if manifest.get("schema") != "shiploop-incremental-attempt-archive/v1" or not _same_path(manifest.get("run_dir", ""), run_dir):
        raise CheckpointError("resume archive manifest identifies a different run")
    found: dict[str, str] = {}
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise CheckpointError("resume archive has no artifact manifest")
    for item in artifacts:
        if not isinstance(item, dict) or not isinstance(item.get("source"), str) or not isinstance(item.get("archive"), str):
            raise CheckpointError("resume archive contains a malformed artifact record")
        rel = PurePosixPath(item["archive"])
        if rel.is_absolute() or any(part in ("", ".", "..") for part in rel.parts):
            raise CheckpointError("resume archive contains an unsafe artifact path")
        copied = archive_dir.joinpath(*rel.parts)
        if copied.is_symlink() or not copied.is_file() or sha256_file(copied) != item.get("sha256"):
            raise CheckpointError(f"archived resume artifact changed or is missing: {item['source']}")
        found[item["source"]] = item["sha256"]
    for source, key in (("result.json", "result_sha256"), ("invocation.json", "invocation_sha256")):
        if found.get(source) != before.get(key):
            raise CheckpointError(f"resume archive does not preserve the recorded prior {source}")
    if before.get("metrics_sha256") and found.get("metrics.json") != before["metrics_sha256"]:
        raise CheckpointError("resume archive does not preserve the recorded prior metrics")


def validate_resume_history(row: dict[str, Any], run_dir: Path, identity: dict[str, Any]) -> None:
    run_dir = Path(run_dir).resolve(strict=True)
    attempts = row.get("attempts", [])
    if not isinstance(attempts, list):
        raise CheckpointError("runs inventory attempt history is malformed")
    for previous in attempts:
        if not isinstance(previous, dict) or previous.get("kind") != "resume":
            raise CheckpointError("runs inventory contains an unrecognized prior attempt record")
        resume_invocation = previous.get("resume_invocation")
        if not isinstance(resume_invocation, dict):
            raise CheckpointError("previous resume attempt has no retained actual invocation identity")
        before = previous.get("before")
        if not isinstance(before, dict) or previous.get("result_sha256") == before.get("result_sha256"):
            raise CheckpointError("previous resume attempt did not retain a refreshed source-harness result")
        _verify_resume_archive(previous, run_dir, identity, before)
        resume_path = external_path(resume_invocation.get("path", ""), "resume invocation", (SOURCE_ROOT,), must_exist=True)
        if not _within(resume_path, run_dir) or sha256_file(resume_path) != resume_invocation.get("sha256"):
            raise CheckpointError("previous resume invocation changed or is outside this run output")
        actual_resume = _read_json(resume_path, "previous resume invocation")
        resume_versions = actual_resume.get("versions") or {}
        if (actual_resume.get("case") != "custom" or actual_resume.get("host") != MODEL["host"]
                or actual_resume.get("model") != MODEL["model"] or actual_resume.get("effort") != MODEL["effort"]
                or not _same_path(actual_resume.get("cwd", ""), run_dir / "work")
                or actual_resume.get("checks") != identity["checks"]["commands"]
                or resume_versions.get("source") != "checkout"
                or resume_versions.get("local_head") != identity["source"]["head"]):
            raise CheckpointError("previous resume invocation differs from the original pinned link identity")
        resumed_run = actual_resume.get("resumed_run")
        resumed_dir = resumed_run.get("run_dir") if isinstance(resumed_run, dict) else resumed_run
        if isinstance(resumed_dir, str) and not _same_path(resumed_dir, run_dir):
            raise CheckpointError("previous resume invocation identifies a different source-harness run")
    if row.get("latest_resume_invocation") != (attempts[-1].get("resume_invocation") if attempts else None):
        raise CheckpointError("runs inventory latest resume identity differs from its attempt history")


def validate_resume_candidate(run_dir: str | Path, row: dict[str, Any],
                              identity: dict[str, Any]) -> dict[str, Any]:
    """Accept only an unchanged, active run ended by a failed resumable Codex host."""
    run_dir = Path(run_dir).resolve(strict=True)
    _validate_identity_shape(identity)
    if row.get("identity") != identity or row.get("run_id") != f"{identity['trial_id']}:{identity['link']}":
        raise CheckpointError("resume inventory row does not match the original trial/link/release/check/prompt identity")
    if row.get("status") != "failed" or row.get("runner_returncode") == 0:
        raise CheckpointError("only a retained failed, unfinished attempt can be resumed")
    result_path, invocation_path = run_dir / "result.json", run_dir / "invocation.json"
    if not result_path.is_file() or not invocation_path.is_file():
        raise CheckpointError("resume needs the original result and invocation records")
    if row.get("result_sha256") != sha256_file(result_path):
        raise CheckpointError("original result changed after the launcher recorded the interrupted attempt")
    if row.get("invocation_sha256") != sha256_file(invocation_path):
        raise CheckpointError("original invocation changed after the launcher recorded the interrupted attempt")
    if row.get("original_invocation_sha256", row.get("invocation_sha256")) != row.get("invocation_sha256"):
        raise CheckpointError("original invocation identity is no longer the bound first launch")
    if row.get("prompt_file_sha256") != sha256_file(run_dir / "prompt.txt"):
        raise CheckpointError("original saved prompt changed after the launcher recorded the interrupted attempt")
    result = _read_json(result_path, "interrupted result")
    invocation = _read_json(invocation_path, "original invocation")
    if result.get("case") != "custom" or invocation.get("case") != "custom":
        raise CheckpointError("resume is limited to the original custom-prompt invocation")
    if not _same_path(result.get("output", ""), run_dir) or not _same_path(invocation.get("cwd", ""), run_dir / "work"):
        raise CheckpointError("original result or invocation points at a different output/work tree")
    if sha256_file(run_dir / "prompt.txt") != identity["prompt"]["invoked_sha256"]:
        raise CheckpointError("original saved prompt digest differs from the expected link")
    if (invocation.get("host") != MODEL["host"] or invocation.get("model") != MODEL["model"]
            or invocation.get("effort") != MODEL["effort"]):
        raise CheckpointError("original invocation host/model/effort differs from the pinned profile")
    versions = invocation.get("versions") or {}
    if versions.get("source") != "checkout" or versions.get("local_head") != identity["source"]["head"]:
        raise CheckpointError("original invocation did not use the pinned released checkout")
    if invocation.get("checks") != identity["checks"]["commands"]:
        raise CheckpointError("original invocation check commands differ from the pinned identity")
    validate_resume_history(row, run_dir, identity)
    checks = result.get("checks")
    if checks is not None:
        expected_commands = identity["checks"]["commands"]
        recorded_commands = [item.get("command") for item in checks if isinstance(item, dict)] if isinstance(checks, list) else None
        if (recorded_commands is None or len(recorded_commands) != len(checks)
                or any(not isinstance(command, str) for command in recorded_commands)
                or len(set(recorded_commands)) != len(recorded_commands)
                or any(command not in expected_commands for command in recorded_commands)):
            raise CheckpointError("interrupted result contains an invalid or unpinned product-check record")
    termination = result.get("termination") or {}
    process = result.get("process") or {}
    resume_stop = termination.get("resume_stop")
    if (result.get("pass") is not False or result.get("outcome_class") != "FAILED"
            or termination.get("engine_status") != "active"
            or termination.get("process_status") != "failed"
            or process.get("status") != "failed"):
        raise CheckpointError("resume requires a failed host interruption with ShipLoop still active; blocked, stopped, and completed runs are ineligible")
    if not (resume_stop == "no host session id to resume"
            or (isinstance(resume_stop, str) and resume_stop.startswith(RESUMABLE_HOST_FAILURES))):
        raise CheckpointError("only an observed resumable host interruption is eligible for resume")
    session_stops = termination.get("session_stops")
    if not isinstance(session_stops, list) or not session_stops:
        raise CheckpointError("interrupted result lacks its host session termination record")
    if any(any(cap in str(stop) for cap in ("max_turns", "max_budget_usd")) for stop in session_stops):
        raise CheckpointError("a host stop caused by a configured cap cannot be resumed by this pilot")
    sessions = process.get("sessions")
    if (not isinstance(sessions, list) or not sessions
            or not any(isinstance(session, dict) and session.get("status") == "failed" for session in sessions)):
        raise CheckpointError("result does not retain a failed host session")
    snapshot = work_snapshot(run_dir / "work")
    if not isinstance(row.get("graded_work_snapshot"), dict) or snapshot != row["graded_work_snapshot"]:
        raise CheckpointError("partial product work changed after the interrupted attempt was recorded")
    return {
        "result_sha256": row["result_sha256"],
        "invocation_sha256": row["invocation_sha256"],
        "prompt_file_sha256": row["prompt_file_sha256"],
        "metrics_sha256": sha256_file(run_dir / "metrics.json") if (run_dir / "metrics.json").is_file() else None,
        "work_snapshot": snapshot,
        "result": result,
        "invocation": invocation,
    }


def _safe_evidence(run_dir: Path, citation: dict[str, Any]) -> dict[str, Any]:
    rel = citation.get("path")
    locator = citation.get("locator")
    note = citation.get("note")
    if not all(isinstance(value, str) and value.strip() for value in (rel, locator, note)):
        raise CheckpointError("each review citation needs non-empty path, locator, and note strings")
    if "\\" in rel:
        raise CheckpointError(f"unsafe review evidence path: {rel!r}")
    relative = PurePosixPath(rel)
    if relative.is_absolute() or not relative.parts or any(part in ("", ".", "..") for part in relative.parts):
        raise CheckpointError(f"unsafe review evidence path: {rel!r}")
    candidate = run_dir.joinpath(*relative.parts)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise CheckpointError(f"review evidence is missing: {rel}: {exc}") from exc
    if not _within(resolved, run_dir.resolve()) or not resolved.is_file():
        raise CheckpointError(f"review evidence must be a file inside the run output: {rel}")
    if candidate.is_symlink():
        raise CheckpointError(f"review evidence may not be a symlink: {rel}")
    cursor = run_dir
    for part in relative.parts[:-1]:
        cursor = cursor / part
        if cursor.is_symlink():
            raise CheckpointError(f"review evidence may not traverse a symlink: {rel}")
    record = _file_record(candidate)
    if record["kind"] == "missing":
        raise CheckpointError(f"review evidence is missing: {rel}")
    return {"path": rel, "locator": locator.strip(), "note": note.strip(), "file": record}


def validate_review(review: dict[str, Any], run_dir: Path, identity: dict[str, Any], result_sha256: str,
                    checkout_identity_sha256: str) -> tuple[dict, str, list[dict]]:
    reviewer = review.get("reviewer")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise CheckpointError("operator review must name a reviewer")
    if review.get("trial_id") != identity["trial_id"] or review.get("link") != identity["link"]:
        raise CheckpointError("operator review names the wrong trial or link")
    if review.get("prompt_sha256") != identity["prompt"]["invoked_sha256"]:
        raise CheckpointError("operator review is not bound to the actual saved prompt")
    if review.get("result_sha256") != result_sha256:
        raise CheckpointError("operator review is not bound to this result.json")
    if review.get("checkout_identity_sha256") != checkout_identity_sha256:
        raise CheckpointError("operator review is not bound to the pre-review checkout snapshot")
    retrieval = review.get("retrieval_source")
    if not isinstance(retrieval, dict) or retrieval.get("status") not in ("known", "unknown"):
        raise CheckpointError("review must record retrieval_source as known or unknown, separately from the five dimensions")
    if not isinstance(retrieval.get("note"), str) or not retrieval["note"].strip():
        raise CheckpointError("review retrieval_source needs a note, including when its status is unknown")
    dimensions = review.get("dimensions")
    if not isinstance(dimensions, dict) or set(dimensions) != set(DIMENSIONS):
        raise CheckpointError("operator review must explicitly assess all five plan dimensions")
    evidence: list[dict] = []
    retrieval_evidence = retrieval.get("evidence", [])
    if retrieval["status"] == "known":
        if not isinstance(retrieval_evidence, list) or not retrieval_evidence:
            raise CheckpointError("known retrieval_source needs at least one evidence citation")
        evidence.extend({"dimension": "retrieval_source", **_safe_evidence(run_dir, citation)}
                        for citation in retrieval_evidence)
    elif retrieval_evidence not in (None, []):
        if not isinstance(retrieval_evidence, list):
            raise CheckpointError("unknown retrieval_source evidence must be a list when supplied")
        evidence.extend({"dimension": "retrieval_source", **_safe_evidence(run_dir, citation)}
                        for citation in retrieval_evidence)
    follow_on = review.get("follow_on")
    if not isinstance(follow_on, dict) or not all(
        isinstance(follow_on.get(key), str) and follow_on[key].strip()
        for key in ("class", "statement", "source", "rationale")
    ):
        raise CheckpointError("review must record observed follow_on class, statement, source, and rationale")
    for name in DIMENSIONS:
        item = dimensions[name]
        if not isinstance(item, dict) or item.get("status") != "pass":
            raise CheckpointError(f"operator review dimension {name} is absent, unknown, or failed")
        citations = item.get("evidence")
        if not isinstance(citations, list) or not citations:
            raise CheckpointError(f"operator review dimension {name} needs at least one evidence citation")
        evidence.extend({"dimension": name, **_safe_evidence(run_dir, citation)} for citation in citations)
    normalized = json.loads(json.dumps(review, ensure_ascii=True))
    return normalized, canonical_digest(normalized), evidence


def _validate_row_identity(row: dict[str, Any], expected_identity: dict[str, Any]) -> None:
    if row.get("identity") != expected_identity:
        raise CheckpointError("runs inventory identity differs from the expected trial/link/source/check identity")


def _snapshot_for_review(*, run_dir: Path, inventory_path: Path, trial_id: str, link: str) -> dict[str, Any]:
    _safe_segment(trial_id, "trial id")
    _safe_segment(link, "link")
    inventory = read_inventory(inventory_path)
    run_id = f"{trial_id}:{link}"
    row = inventory_row(inventory, run_id)
    if row.get("trial_id") != trial_id or row.get("link") != link or not _same_path(row.get("output", ""), run_dir):
        raise CheckpointError("runs inventory row does not identify this trial, link, and run directory")
    identity = row.get("identity")
    if not isinstance(identity, dict) or identity.get("trial_id") != trial_id or identity.get("link") != link:
        raise CheckpointError("runs inventory row has no matching identity")
    _require_outside(inventory_path, "runs inventory", Path(identity["source"]["release_tree"]))
    validate_resume_history(row, run_dir, identity)
    validate_source_and_checks(identity)
    if row.get("status") != "complete" or row.get("runner_returncode") != 0:
        raise CheckpointError("only a completed, zero-exit runner row can be reviewed")
    _require_result(run_dir, identity)
    result_digest = sha256_file(run_dir / "result.json")
    invocation_digest = sha256_file(run_dir / "invocation.json")
    prompt_digest = sha256_file(run_dir / "prompt.txt")
    if row.get("result_sha256") != result_digest or row.get("invocation_sha256") != invocation_digest:
        raise CheckpointError("result or invocation changed after the launcher recorded grading")
    if row.get("prompt_file_sha256") != prompt_digest:
        raise CheckpointError("saved prompt changed after the launcher recorded grading")
    snapshot = work_snapshot(run_dir / "work")
    if row.get("graded_work_snapshot") != snapshot:
        raise CheckpointError("product files or Git state changed after grading")
    terminal = terminal_artifacts(run_dir, _read_json(run_dir / "result.json", "result"))
    if row.get("terminal_artifacts") != terminal:
        raise CheckpointError("ShipLoop terminal receipt or report changed after grading")
    return {
        "schema": REVIEW_SNAPSHOT_SCHEMA,
        "run_id": run_id,
        "trial_id": trial_id,
        "link": link,
        "run_dir": str(run_dir),
        "inventory": {"path": str(inventory_path), "row_sha256": canonical_digest(row)},
        "identity": identity,
        "files": {"result_sha256": result_digest, "invocation_sha256": invocation_digest,
                  "prompt_file_sha256": prompt_digest},
        "work_snapshot": snapshot,
        "terminal_artifacts": terminal,
        "checkout_identity_sha256": canonical_digest(snapshot),
    }


def inspect_run(*, run_dir: str | Path, inventory_path: str | Path, trial_id: str, link: str,
                output_path: str | Path) -> dict[str, Any]:
    run_dir = external_path(run_dir, "run directory", (SOURCE_ROOT,), must_exist=True)
    inventory_path = external_path(inventory_path, "runs inventory", (SOURCE_ROOT, run_dir), must_exist=True)
    output_path = external_path(output_path, "review snapshot output", (SOURCE_ROOT, run_dir))
    if output_path.exists():
        raise CheckpointError(f"review snapshot already exists; preserving it: {output_path}")
    receipt = _snapshot_for_review(run_dir=run_dir, inventory_path=inventory_path, trial_id=trial_id, link=link)
    release_tree = Path(receipt["identity"]["source"]["release_tree"])
    _require_outside(output_path, "review snapshot output", release_tree)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output_path.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, indent=2, ensure_ascii=True)
            stream.write("\n")
    except FileExistsError as exc:
        raise CheckpointError(f"review snapshot already exists; preserving it: {output_path}") from exc
    return receipt


def _load_review_snapshot(path: Path, *, run_dir: Path, inventory_path: Path, identity: dict[str, Any],
                          row: dict[str, Any]) -> tuple[dict[str, Any], str]:
    receipt = _read_json(path, "pre-review checkout snapshot")
    if receipt.get("schema") != REVIEW_SNAPSHOT_SCHEMA:
        raise CheckpointError("unsupported pre-review checkout snapshot schema")
    if receipt.get("identity") != identity or not _same_path(receipt.get("run_dir", ""), run_dir):
        raise CheckpointError("pre-review snapshot identifies a different run or source/check identity")
    if not _same_path((receipt.get("inventory") or {}).get("path", ""), inventory_path):
        raise CheckpointError("pre-review snapshot names a different runs inventory")
    if (receipt.get("inventory") or {}).get("row_sha256") != canonical_digest(row):
        raise CheckpointError("runs inventory row changed since the pre-review snapshot")
    validate_resume_history(row, run_dir, identity)
    snapshot = receipt.get("work_snapshot")
    if not isinstance(snapshot, dict) or canonical_digest(snapshot) != receipt.get("checkout_identity_sha256"):
        raise CheckpointError("pre-review checkout identity digest is invalid")
    if snapshot != work_snapshot(run_dir / "work"):
        raise CheckpointError("product checkout changed after the pre-review snapshot")
    files = receipt.get("files") or {}
    current_files = {
        "result_sha256": sha256_file(run_dir / "result.json"),
        "invocation_sha256": sha256_file(run_dir / "invocation.json"),
        "prompt_file_sha256": sha256_file(run_dir / "prompt.txt"),
    }
    if files != current_files:
        raise CheckpointError("result, invocation, or actual prompt changed after the pre-review snapshot")
    result, _, _ = _require_result(run_dir, identity)
    if receipt.get("terminal_artifacts") != terminal_artifacts(run_dir, result):
        raise CheckpointError("ShipLoop terminal receipt or report changed after the pre-review snapshot")
    return receipt, sha256_file(path)


def create_checkpoint(
    *, run_dir: str | Path, inventory_path: str | Path, review_path: str | Path, snapshot_path: str | Path,
    output_path: str | Path, trial_id: str, link: str,
) -> dict[str, Any]:
    run_dir = external_path(run_dir, "run directory", (SOURCE_ROOT,), must_exist=True)
    work = run_dir / "work"
    inventory_path = external_path(inventory_path, "runs inventory", (SOURCE_ROOT, run_dir))
    review_path = external_path(review_path, "operator review", (SOURCE_ROOT, run_dir), must_exist=True)
    snapshot_path = external_path(snapshot_path, "pre-review checkout snapshot", (SOURCE_ROOT, run_dir), must_exist=True)
    output_path = external_path(output_path, "checkpoint output", (SOURCE_ROOT, run_dir))
    if output_path.exists():
        raise CheckpointError(f"checkpoint already exists; preserving it: {output_path}")
    inventory = read_inventory(inventory_path)
    run_id = f"{trial_id}:{link}"
    row = inventory_row(inventory, run_id)
    if row.get("trial_id") != trial_id or row.get("link") != link or not _same_path(row.get("output", ""), run_dir):
        raise CheckpointError("runs inventory row does not identify this trial, link, and run directory")
    identity = row.get("identity")
    if not isinstance(identity, dict) or identity.get("trial_id") != trial_id or identity.get("link") != link:
        raise CheckpointError("runs inventory row has no matching identity")
    _safe_segment(trial_id, "trial id")
    _safe_segment(link, "link")
    validate_source_and_checks(identity)
    release_tree = Path(identity["source"]["release_tree"])
    for path, label in ((inventory_path, "runs inventory"), (review_path, "operator review"),
                        (snapshot_path, "pre-review checkout snapshot"), (output_path, "checkpoint output")):
        _require_outside(path, label, release_tree)
    if row.get("status") != "complete" or row.get("runner_returncode") != 0:
        raise CheckpointError("only a completed, zero-exit runner row can be checkpointed")
    _validate_row_identity(row, identity)
    result, invocation, prompt_info = _require_result(run_dir, identity)
    validate_source_and_checks(identity)
    result_digest = sha256_file(run_dir / "result.json")
    invocation_digest = sha256_file(run_dir / "invocation.json")
    if row.get("result_sha256") != result_digest or row.get("invocation_sha256") != invocation_digest:
        raise CheckpointError("result or invocation changed after the launcher recorded grading")
    if row.get("prompt_file_sha256") != prompt_info["prompt_sha256"]:
        raise CheckpointError("saved prompt changed after the launcher recorded grading")
    review_snapshot, review_snapshot_digest = _load_review_snapshot(snapshot_path, run_dir=run_dir,
                                                                    inventory_path=inventory_path,
                                                                    identity=identity, row=row)
    snapshot = review_snapshot["work_snapshot"]
    review = _read_json(review_path, "operator review")
    normalized_review, review_digest, evidence = validate_review(
        review, run_dir, identity, result_digest, review_snapshot["checkout_identity_sha256"]
    )
    checkpoint = {
        "schema": SCHEMA,
        "run_id": run_id,
        "trial_id": trial_id,
        "link": link,
        "run_dir": str(run_dir),
        "inventory": {"path": str(inventory_path), "row_sha256": canonical_digest(row)},
        "identity": identity,
        "files": {
            "result_sha256": result_digest,
            "invocation_sha256": invocation_digest,
            "prompt_file_sha256": prompt_info["prompt_sha256"],
        },
        "terminal": {
            "pass": result.get("pass"),
            "engine_status": (result.get("termination") or {}).get("engine_status"),
            "engine_stage": (result.get("termination") or {}).get("engine_stage"),
            "report_html": (result.get("shiploop") or {}).get("report_html"),
            "process_returncode": (result.get("process") or {}).get("returncode"),
        },
        "work_snapshot": snapshot,
        "terminal_artifacts": review_snapshot["terminal_artifacts"],
        "review_snapshot": {"path": str(snapshot_path), "file_sha256": review_snapshot_digest,
                            "checkout_identity_sha256": review_snapshot["checkout_identity_sha256"]},
        "review": {
            "value": normalized_review,
            "canonical_sha256": review_digest,
            "source_path": str(review_path),
            "source_file_sha256": sha256_file(review_path),
            "evidence": evidence,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output_path.open("x", encoding="utf-8") as stream:
            json.dump(checkpoint, stream, indent=2, ensure_ascii=True)
            stream.write("\n")
    except FileExistsError as exc:
        raise CheckpointError(f"checkpoint already exists; preserving it: {output_path}") from exc
    return checkpoint


def _verify_embedded_review(checkpoint: dict[str, Any], run_dir: Path) -> None:
    section = checkpoint.get("review") or {}
    review = section.get("value")
    if not isinstance(review, dict) or canonical_digest(review) != section.get("canonical_sha256"):
        raise CheckpointError("checkpoint operator review digest is invalid")
    identity = checkpoint["identity"]
    result_sha = checkpoint["files"]["result_sha256"]
    normalized, _, evidence = validate_review(review, run_dir, identity, result_sha,
                                             (checkpoint.get("review_snapshot") or {}).get("checkout_identity_sha256", ""))
    if evidence != section.get("evidence"):
        raise CheckpointError("operator review evidence files changed after review")
    source_path = external_path(section.get("source_path", ""), "operator review source", (SOURCE_ROOT, run_dir), must_exist=True)
    if sha256_file(source_path) != section.get("source_file_sha256"):
        raise CheckpointError("operator review JSON changed after checkpoint creation")


def verify_checkpoint(
    checkpoint_path: str | Path, *, expected_identity: dict[str, Any],
    output_root: str | Path, inventory_path: str | Path,
) -> dict[str, Any]:
    output_root = external_path(output_root, "output root", (SOURCE_ROOT,))
    checkpoint_path = external_path(checkpoint_path, "checkpoint", (SOURCE_ROOT,), must_exist=True)
    inventory_path = external_path(inventory_path, "runs inventory", (SOURCE_ROOT,))
    checkpoint = _read_json(checkpoint_path, "checkpoint")
    if checkpoint.get("schema") != SCHEMA:
        raise CheckpointError(f"unsupported checkpoint schema at {checkpoint_path}")
    if checkpoint.get("identity") != expected_identity:
        raise CheckpointError("checkpoint does not match the expected predecessor link/prompt/trial/release/check identity")
    identity = checkpoint["identity"]
    trial_id, link = identity["trial_id"], identity["link"]
    _safe_segment(trial_id, "trial id")
    _safe_segment(link, "link")
    validate_source_and_checks(identity)
    release_tree = Path(identity["source"]["release_tree"])
    for path, label in ((checkpoint_path, "checkpoint"), (inventory_path, "runs inventory"),
                        (output_root, "output root")):
        _require_outside(path, label, release_tree)
    run_dir = external_path(checkpoint.get("run_dir", ""), "checkpoint run directory", (SOURCE_ROOT,), must_exist=True)
    if _within(checkpoint_path, run_dir) or _within(inventory_path, run_dir):
        raise CheckpointError("checkpoint and runs inventory must stay outside the product run directory")
    if not _same_path(run_dir, output_root / trial_id / link):
        raise CheckpointError("checkpoint run path is outside this trial's expected output location")
    if checkpoint.get("run_id") != f"{trial_id}:{link}" or checkpoint.get("trial_id") != trial_id or checkpoint.get("link") != link:
        raise CheckpointError("checkpoint run identity is inconsistent")
    inventory = read_inventory(inventory_path)
    row = inventory_row(inventory, checkpoint["run_id"])
    if not _same_path(checkpoint["inventory"]["path"], inventory_path) or canonical_digest(row) != checkpoint["inventory"]["row_sha256"]:
        raise CheckpointError("runs inventory row changed or no longer matches the checkpoint")
    validate_resume_history(row, run_dir, identity)
    if row.get("status") != "complete" or row.get("runner_returncode") != 0:
        raise CheckpointError("predecessor inventory does not record a completed successful launch")
    _validate_row_identity(row, expected_identity)
    result, invocation, prompt_info = _require_result(run_dir, expected_identity)
    if result.get("pass") is not True:
        raise CheckpointError("predecessor result pass is not true")
    files = checkpoint.get("files") or {}
    current_files = {
        "result_sha256": sha256_file(run_dir / "result.json"),
        "invocation_sha256": sha256_file(run_dir / "invocation.json"),
        "prompt_file_sha256": prompt_info["prompt_sha256"],
    }
    if current_files != files:
        raise CheckpointError("predecessor result, invocation, or actual prompt changed after review")
    snapshot = work_snapshot(run_dir / "work")
    if snapshot != checkpoint.get("work_snapshot") or snapshot != row.get("graded_work_snapshot"):
        raise CheckpointError("predecessor Git HEAD/tree/status or tracked/untracked file manifest changed after review")
    current_terminal = terminal_artifacts(run_dir, result)
    if current_terminal != checkpoint.get("terminal_artifacts") or current_terminal != row.get("terminal_artifacts"):
        raise CheckpointError("predecessor ShipLoop terminal receipt or report changed after review")
    review_snapshot = checkpoint.get("review_snapshot") or {}
    snapshot_path = external_path(review_snapshot.get("path", ""), "pre-review checkout snapshot", (SOURCE_ROOT, run_dir), must_exist=True)
    if sha256_file(snapshot_path) != review_snapshot.get("file_sha256"):
        raise CheckpointError("pre-review checkout snapshot file changed after review")
    receipt = _read_json(snapshot_path, "pre-review checkout snapshot")
    if (receipt.get("checkout_identity_sha256") != review_snapshot.get("checkout_identity_sha256")
            or receipt.get("checkout_identity_sha256") != canonical_digest(snapshot)
            or receipt.get("work_snapshot") != snapshot
            or receipt.get("terminal_artifacts") != current_terminal):
        raise CheckpointError("pre-review snapshot does not bind this reviewed checkout")
    _verify_embedded_review(checkpoint, run_dir)
    if checkpoint.get("terminal", {}).get("pass") is not True:
        raise CheckpointError("checkpoint does not record a passing result")
    return checkpoint


def _create_cli(args: argparse.Namespace) -> int:
    checkpoint = create_checkpoint(run_dir=args.run_dir, inventory_path=args.inventory, review_path=args.review,
                                   snapshot_path=args.snapshot, output_path=args.output,
                                   trial_id=args.trial_id, link=args.link)
    print(json.dumps({"checkpoint": str(Path(args.output).resolve()), "run_id": checkpoint["run_id"],
                      "work_head": checkpoint["work_snapshot"]["head"]}, indent=2))
    return 0


def _inspect_cli(args: argparse.Namespace) -> int:
    receipt = inspect_run(run_dir=args.run_dir, inventory_path=args.inventory, trial_id=args.trial_id,
                          link=args.link, output_path=args.output)
    print(json.dumps({"snapshot": str(Path(args.output).resolve()), "run_id": receipt["run_id"],
                      "checkout_identity_sha256": receipt["checkout_identity_sha256"]}, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    actions = root.add_subparsers(dest="action", required=True)
    inspect = actions.add_parser("inspect", help="freeze a passing checkout identity before semantic review")
    inspect.add_argument("--run-dir", type=Path, required=True)
    inspect.add_argument("--inventory", type=Path, required=True)
    inspect.add_argument("--trial-id", required=True)
    inspect.add_argument("--link", choices=("base", "filter", "output"), required=True)
    inspect.add_argument("--output", type=Path, required=True)
    create = actions.add_parser("create", help="bind a passing run to an explicit operator review")
    create.add_argument("--run-dir", type=Path, required=True)
    create.add_argument("--inventory", type=Path, required=True)
    create.add_argument("--review", type=Path, required=True)
    create.add_argument("--snapshot", type=Path, required=True)
    create.add_argument("--trial-id", required=True)
    create.add_argument("--link", choices=("base", "filter", "output"), required=True)
    create.add_argument("--output", type=Path, required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return _inspect_cli(args) if args.action == "inspect" else _create_cli(args)
    except CheckpointError as exc:
        print(f"checkpoint refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
